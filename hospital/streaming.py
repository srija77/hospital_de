"""Native Snowpipe Streaming; durable shared source + server offsets govern replay.

No credentials or SDK client is needed in the default local simulator.
"""
import argparse
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from filelock import FileLock


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def save_state(path, state):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(path)


def prepare_state(source, target, live=False):
    source, target = Path(source), Path(target)
    signature = digest(source/'admission_events.jsonl')
    manifest = digest(source/'manifest.json')
    expected = json.loads((source/'manifest.json').read_text()).get('admission_events.jsonl')
    if expected != signature:
        raise ValueError('Event source does not match its generated manifest')
    mode = 'SNOWPIPE_STREAMING' if live else 'LOCAL_SIMULATOR'
    path = target/'stream_state.json'
    if path.exists():
        state = json.loads(path.read_text())
        if (state['source_sha256'], state['manifest_sha256'], state['mode']) != (signature, manifest, mode):
            raise ValueError('Source or mode changed: preserve the original source and channel identity')
    else:
        state = dict(stream_id=uuid.uuid4().hex, source_sha256=signature, manifest_sha256=manifest,
                     mode=mode, committed_offset=-1, started_at=now(), database='HOSPITAL_DEV',
                     pipe='ADMISSION_EVENTS_STREAM_PIPE')
        save_state(path, state)
    return state


def recovery_offset(server_token, checkpoint, source_count):
    remote = -1 if server_token is None else int(server_token)
    if remote < checkpoint:
        raise ValueError('Server offset is behind local checkpoint: channel was reset/lost; investigate before replay')
    if remote < -1 or remote >= source_count:
        raise ValueError('Server offset is outside the retained source')
    return remote


class LocalChannel:
    """Durable simulator only, never presented as Snowflake ingestion evidence."""
    def __init__(self, path):
        self.path = Path(path)
        self.offset = -1
        if self.path.exists():
            with self.path.open(encoding='utf-8') as f:
                for line in f:
                    record = json.loads(line)
                    if record['offset'] != self.offset+1:
                        raise ValueError('Local simulator ledger is not contiguous')
                    self.offset = record['offset']

    def get_latest_committed_offset_token(self):
        return None if self.offset == -1 else str(self.offset)

    def append_row(self, row, offset_token=None):
        offset = int(offset_token)
        if offset != self.offset+1:
            raise ValueError('Non-contiguous simulator append')
        with self.path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(dict(offset=offset, row=row))+'\n')
            f.flush()
            os.fsync(f.fileno())
        self.offset = offset

    def wait_for_commit(self, checker, timeout_seconds=None):
        if not checker(self.get_latest_committed_offset_token()):
            raise TimeoutError('Simulator offset not committed')

    def get_channel_status(self):
        return SimpleNamespace(rows_error_count=0, latest_committed_offset_token=self.get_latest_committed_offset_token())


def pump(source, channel, state, target, max_events=None, interval=1, commit_every=10, minutes=None):
    """Append rows continuously; persist checkpoints only after server commit confirmation."""
    source, target = Path(source), Path(target)
    with source.open(encoding='utf-8') as f:
        count = sum(1 for _ in f)
    remote = recovery_offset(channel.get_latest_committed_offset_token(), state['committed_offset'], count)
    if channel.get_channel_status().rows_error_count:
        raise RuntimeError('Channel has rejected rows; inspect Snowflake error tables before advancing')
    # A server-ahead offset is expected if a crash followed commit but preceded local checkpoint.
    state['committed_offset'] = remote
    save_state(target/'stream_state.json', state)
    sent, last = 0, remote
    deadline = time.monotonic()+minutes*60 if minutes is not None else float('inf')

    def acknowledge():
        started = time.monotonic()
        channel.wait_for_commit(lambda token: token is not None and int(token) >= last, timeout_seconds=60)
        status = channel.get_channel_status()
        if status.rows_error_count:
            raise RuntimeError('Streaming rejected rows: checkpoint not advanced; inspect errors')
        state.update(committed_offset=last, last_confirmed_at=now())
        save_state(target/'stream_state.json', state)
        with (target/'commits.jsonl').open('a', encoding='utf-8') as log:
            log.write(json.dumps(dict(evidence=state['mode'], committed_offset=last,
                acknowledged_at=now(), commit_wait_seconds=time.monotonic()-started))+'\n')
        print(f"{state['mode']}: committed source offset {last}", flush=True)

    try:
        with source.open(encoding='utf-8') as f:
            for offset, line in enumerate(f):
                if offset <= remote:
                    continue
                if (max_events is not None and sent >= max_events) or time.monotonic() >= deadline:
                    break
                started = time.monotonic()
                event = json.loads(line)
                # RAW remains the original dictionary (VARIANT), not a JSON-encoded string.
                row = dict(RAW=event, SOURCE_FILE=f"snowpipe-streaming://{state['stream_id']}/{offset}",
                           SOURCE_PUBLISHED_AT=now())
                channel.append_row(row, offset_token=str(offset))
                last, sent = offset, sent+1
                if sent % commit_every == 0:
                    acknowledge()
                if interval:
                    time.sleep(max(0, interval-(time.monotonic()-started)))
    except KeyboardInterrupt:
        print('Stopping; confirming buffered rows before exit', flush=True)
    if last > state['committed_offset']:
        acknowledge()
    state['source_exhausted'] = state['committed_offset'] == count-1
    save_state(target/'stream_state.json', state)
    return dict(evidence=state['mode'], appended_this_run=sent, committed_offset=state['committed_offset'],
                source_records=count, source_exhausted=state['source_exhausted'])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', default='data/demo')
    p.add_argument('--out', default='data/native-stream')
    p.add_argument('--live', action='store_true')
    p.add_argument('--interval-seconds', type=float, default=1)
    p.add_argument('--commit-every', type=int, default=10)
    p.add_argument('--max-events', type=int)
    p.add_argument('--minutes', type=float)
    a = p.parse_args()
    if a.interval_seconds < 0 or a.commit_every < 1 or (a.max_events is not None and a.max_events < 1) or (a.minutes is not None and a.minutes <= 0):
        p.error('Use nonnegative interval and positive commit/max-event/duration values')
    target = Path(a.out)
    target.mkdir(parents=True, exist_ok=True)
    # OS-level lock is released on process exit/crash; one writer per named channel.
    with FileLock(str(target/'producer.lock'), timeout=0):
        state = prepare_state(a.source, target, a.live)
        client = None
        try:
            if a.live:
                from snowflake.ingest.streaming import StreamingIngestClient
                props = dict(account=os.environ['SNOWFLAKE_ACCOUNT'], user=os.environ['SNOWFLAKE_USER'],
                    private_key_file=os.environ['SNOWFLAKE_PRIVATE_KEY_PATH'], role='DE_ENGINEER',
                    url=os.environ['SNOWFLAKE_URL'])
                client = StreamingIngestClient(client_name='hospital_capstone', db_name='HOSPITAL_DEV',
                    schema_name='BRONZE', pipe_name=state['pipe'], properties=props)
                channel, _ = client.open_channel('HOSPITAL_'+state['stream_id'].upper())
            else:
                channel = LocalChannel(target/'local_rows.jsonl')
            result = pump(Path(a.source)/'admission_events.jsonl', channel, state, target,
                          a.max_events, a.interval_seconds, a.commit_every, a.minutes)
            print(json.dumps(result))
        finally:
            if client is not None:
                client.close(wait_for_flush=True, timeout_seconds=60)


if __name__ == '__main__':
    main()
