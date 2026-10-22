import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from hospital.core import generate,write_data
from hospital.streaming import prepare_state,pump,recovery_offset,LocalChannel


class MemoryChannel:
    def __init__(self, offset=None, fail_commit=False, reject=False):
        self.offset=offset
        self.pending=[]
        self.appended=[]
        self.fail_commit=fail_commit
        self.reject=reject

    def get_latest_committed_offset_token(self):
        return self.offset

    def append_row(self,row,offset_token=None):
        self.appended.append((row,offset_token))
        self.pending.append(offset_token)

    def wait_for_commit(self,checker,timeout_seconds=None):
        if self.fail_commit:
            raise TimeoutError('Simulated connection/commit interruption')
        self.offset=self.pending[-1]
        assert checker(self.offset)

    def get_channel_status(self):
        return SimpleNamespace(rows_error_count=1 if self.reject and self.pending else 0)


class StreamingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source=Path(self.temp.name)/'source'
        self.out=Path(self.temp.name)/'stream'
        self.out.mkdir()
        write_data(generate(patients=5,admissions=12),self.source)
        self.state=prepare_state(self.source,self.out)
        self.events=self.source/'admission_events.jsonl'

    def test_native_row_envelope_preserves_variant(self):
        channel=MemoryChannel()
        result=pump(self.events,channel,self.state,self.out,max_events=9,interval=0,commit_every=4)
        self.assertEqual(result['committed_offset'],8)
        self.assertEqual(len(channel.appended),9)
        first=json.loads(self.events.read_text().splitlines()[0])
        self.assertEqual(channel.appended[0][0]['RAW'],first)
        self.assertIsInstance(channel.appended[0][0]['RAW'],dict)
        self.assertTrue(channel.appended[0][0]['SOURCE_FILE'].startswith('snowpipe-streaming://'))

    def test_server_ahead_recovers_crash_after_commit(self):
        self.state['committed_offset']=3
        channel=MemoryChannel(offset='7')
        result=pump(self.events,channel,self.state,self.out,max_events=2,interval=0)
        self.assertEqual([r[1] for r in channel.appended],['8','9'])
        self.assertEqual(result['committed_offset'],9)

    def test_commit_timeout_never_advances_checkpoint(self):
        with self.assertRaises(TimeoutError):
            pump(self.events,MemoryChannel(fail_commit=True),self.state,self.out,max_events=4,interval=0,commit_every=4)
        self.assertEqual(json.loads((self.out/'stream_state.json').read_text())['committed_offset'],-1)

    def test_rejected_rows_fail_without_advancing(self):
        with self.assertRaisesRegex(RuntimeError,'rejected'):
            pump(self.events,MemoryChannel(reject=True),self.state,self.out,max_events=2,interval=0,commit_every=2)
        self.assertEqual(self.state['committed_offset'],-1)

    def test_lost_or_invalid_channel_offsets_fail_closed(self):
        for server,local,count in [(None,2,100),('1',4,100),('100',2,100),('-2',-1,100)]:
            with self.assertRaises(ValueError):
                recovery_offset(server,local,count)

    def test_source_or_mode_cannot_change_on_resume(self):
        with self.assertRaises(ValueError):
            prepare_state(self.source,self.out,live=True)
        with self.events.open('a') as f:
            f.write('{}\n')
        with self.assertRaises(ValueError):
            prepare_state(self.source,self.out)

    def test_local_restart_does_not_duplicate_offsets(self):
        ledger=self.out/'local_rows.jsonl'
        pump(self.events,LocalChannel(ledger),self.state,self.out,max_events=5,interval=0)
        resumed=prepare_state(self.source,self.out)
        pump(self.events,LocalChannel(ledger),resumed,self.out,max_events=5,interval=0)
        records=[json.loads(line) for line in ledger.read_text().splitlines()]
        self.assertEqual([r['offset'] for r in records],list(range(10)))
        self.assertEqual(resumed['committed_offset'],9)

    def test_end_of_source_does_not_loop_old_events(self):
        channel=MemoryChannel()
        result=pump(self.events,channel,self.state,self.out,interval=0,commit_every=10)
        self.assertTrue(result['source_exhausted'])
        self.assertEqual(len(channel.appended),result['source_records'])


if __name__=='__main__':
    unittest.main()
