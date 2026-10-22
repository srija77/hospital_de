"""Resumable immutable micro-batches using the SAME admission event contract."""
import argparse
import json
import time
from datetime import datetime,timezone
from pathlib import Path
from hospital.core import generate,write_data
from hospital.live import connection,load


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--minutes',type=float,default=1440)
    p.add_argument('--interval-seconds',type=float,default=60)
    p.add_argument('--admissions-per-batch',type=int,default=100)
    p.add_argument('--live',action='store_true')
    p.add_argument('--out',default='data/stream')
    args=p.parse_args()
    if args.interval_seconds<=0 or args.minutes<=0:
        p.error('Positive interval and duration required')
    root=Path(args.out)
    root.mkdir(parents=True,exist_ok=True)
    checkpoint=root/'checkpoint.json'
    state=json.loads(checkpoint.read_text()) if checkpoint.exists() else {'next_batch':0,'started_at':datetime.now(timezone.utc).isoformat()}
    state.pop('completed_at',None)
    deadline=time.monotonic()+args.minutes*60
    while time.monotonic()<deadline:
        i=state['next_batch']
        batch=root/f'batch_{i:06}'
        if not (batch/'manifest.json').exists():
            data=generate(seed=42+i,admissions=args.admissions_per_batch)
            # Fixed patient keys; new admission IDs for each micro-batch.
            for a in data['admissions']:
                a['admission_id']+=i*args.admissions_per_batch
            for e in data['admission_events']:
                e['admission_id']+=i*args.admissions_per_batch
                e['payload']['admission_id']=e['admission_id']
                e['event_id']=f'B{i}_'+e['event_id']
                e['ingest_time']=datetime.now(timezone.utc).isoformat()
                # Event time models source lateness; preserve version precedence.
                from datetime import timedelta
                e['event_time']=(datetime.now(timezone.utc)-timedelta(minutes=120 if e['event_version']==1 else 1)).isoformat()
            write_data(data,batch)
        started=time.monotonic()
        if args.live:
            with connection('dev') as c:
                load(c,batch)
        with (root/'producer_runs.jsonl').open('a') as log:
            log.write(json.dumps({'batch':i,'sent_records':len(json.loads((batch/'admission_events.json').read_text())),
                'completed_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-started,'live':args.live})+'\n')
        state['next_batch']=i+1
        temporary=checkpoint.with_suffix('.tmp')
        temporary.write_text(json.dumps(state))
        temporary.replace(checkpoint)
        time.sleep(max(0,args.interval_seconds-(time.monotonic()-started)))
    state['completed_at']=datetime.now(timezone.utc).isoformat()
    checkpoint.write_text(json.dumps(state))


if __name__=='__main__':
    main()
