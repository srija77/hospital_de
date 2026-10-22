"""Measure exact paired workloads; no preassigned speedup or inferred query credits."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from hospital.live import ROOT, connection

def workloads():
    text = (ROOT/'sql/optimization/benchmark_queries.sql').read_text()
    parts = re.split(r'-- workload:([a-z_]+):(before|after)\s*\n',text)
    return {(parts[i],parts[i+1]):parts[i+2].strip().rstrip(';') for i in range(1,len(parts),3)}

def fingerprint(rows):
    return hashlib.sha256(json.dumps(sorted([list(map(str,r)) for r in rows]),sort_keys=True).encode()).hexdigest()

def measure(conn, sql, experiment, workload, variant, output):
    conn.cursor().execute("ALTER SESSION SET USE_CACHED_RESULT=FALSE")
    cur = conn.cursor().execute(sql)
    rows = cur.fetchall()
    qid = cur.sfqid
    stats = conn.cursor().execute(
        "SELECT START_TIME,TOTAL_ELAPSED_TIME,BYTES_SCANNED,ROWS_PRODUCED,WAREHOUSE_NAME,WAREHOUSE_SIZE "
        "FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT=>100)) WHERE QUERY_ID=%s", (qid,)).fetchone()
    if not stats:
        raise RuntimeError('Query history not available; retry collection before reporting')
    rec = dict(experiment=experiment,workload=workload,variant=variant,query_id=qid,query_text=sql,
               run_timestamp=stats[0].isoformat(),elapsed_seconds=stats[1]/1000,
               bytes_scanned=stats[2],rows_returned=len(rows),warehouse_name=stats[4],
               warehouse_size=stats[5],credits_used=None,evidence='MEASURED',
               cache_state='RESULT_CACHE_OFF;WAREHOUSE_CACHE_UNCONTROLLED',
               result_hash=fingerprint(rows))
    output.append(rec)
    print(f"{experiment}/{workload}/{variant}: query={qid}, seconds={rec['elapsed_seconds']:.3f}, bytes={stats[2]}",flush=True)
    conn.cursor().execute('INSERT INTO MONITORING.BENCHMARK_METADATA VALUES '
        '(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (qid,workload,stats[0],experiment+':'+variant,rec['elapsed_seconds'],stats[2],len(rows),
         stats[4],None,rec['cache_state'],qid,sql,stats[5],experiment,variant,'MEASURED'))
    return rec

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--experiment',choices=['rewrite','warehouse','layout'],required=True)
    p.add_argument('--repeats',type=int,default=3)
    p.add_argument('--allow-paid',action='store_true',help='Explicit approval to resize this dedicated DEV warehouse')
    p.add_argument('--size',choices=['SMALL','MEDIUM'],default='SMALL')
    p.add_argument('--profile-reviewed',action='store_true')
    p.add_argument('--out',default='artifacts/measurements.json')
    args=p.parse_args()
    if args.repeats<1:
        p.error('repeats must be positive')
    if args.experiment=='warehouse' and not args.allow_paid:
        p.error('Warehouse experiment requires explicit --allow-paid configuration after budget approval')
    if args.experiment=='layout' and not args.profile_reviewed:
        p.error('Review Query Profile and benchmark scale, then use --profile-reviewed')
    path=Path(args.out)
    path.parent.mkdir(parents=True,exist_ok=True)
    results=json.loads(path.read_text()) if path.exists() else []
    queries=workloads()
    with connection('dev') as conn:
        original=conn.cursor().execute("SHOW WAREHOUSES LIKE 'HOSPITAL_DEV_WH'").fetchone()
        original_size=str(original[3]).upper().replace('-','')
        original_size={'2XLARGE':'XXLARGE','3XLARGE':'XXXLARGE','4XLARGE':'X4LARGE',
                       '5XLARGE':'X5LARGE','6XLARGE':'X6LARGE'}.get(original_size,original_size)
        if original_size not in ('XSMALL','SMALL','MEDIUM','LARGE','XLARGE','XXLARGE','XXXLARGE','X4LARGE','X5LARGE','X6LARGE'):
            raise ValueError('Unexpected warehouse size')
        if args.experiment=='layout':
            count=conn.cursor().execute('SELECT COUNT(*) FROM GOLD.FCT_ADMISSIONS').fetchone()[0]
            if count<100000:
                raise ValueError('Layout experiment requires benchmark data >=100000 admissions')
        try:
            hashes={}
            for variant in ['before','after']:
                if variant=='after':
                    # Persist baseline to disk BEFORE any change.
                    path.write_text(json.dumps(results,indent=2),encoding='utf-8')
                    if args.experiment=='warehouse':
                        conn.cursor().execute(f'ALTER WAREHOUSE HOSPITAL_DEV_WH SET WAREHOUSE_SIZE={args.size}')
                    elif args.experiment=='layout':
                        conn.cursor().execute('CREATE TRANSIENT TABLE GOLD.BENCH_ADMISSIONS AS SELECT * FROM GOLD.FCT_ADMISSIONS ORDER BY ADMIT_DATE')
                for work in ['department','billing','patient_join']:
                    selected=variant if args.experiment=='rewrite' else 'before'
                    fact='GOLD.BENCH_ADMISSIONS' if variant=='after' and args.experiment=='layout' else 'GOLD.FCT_ADMISSIONS'
                    query=queries[work,selected].replace('GOLD.FCT_ADMISSIONS',fact)
                    # Warm up both variants identically; measured repetitions follow.
                    conn.cursor().execute('ALTER SESSION SET USE_CACHED_RESULT=FALSE')
                    conn.cursor().execute(query).fetchall()
                    for _ in range(args.repeats):
                        rec=measure(conn,query,args.experiment,work,variant,results)
                        if work in hashes and hashes[work]!=rec['result_hash']:
                            raise AssertionError('Paired workloads returned different results: '+work)
                        hashes[work]=rec['result_hash']
                        path.write_text(json.dumps(results,indent=2),encoding='utf-8')
        finally:
            if args.experiment=='warehouse':
                conn.cursor().execute(f'ALTER WAREHOUSE HOSPITAL_DEV_WH SET WAREHOUSE_SIZE={original_size}')
            if args.experiment=='layout':
                conn.cursor().execute('DROP TABLE IF EXISTS GOLD.BENCH_ADMISSIONS')

if __name__=='__main__':
    main()
