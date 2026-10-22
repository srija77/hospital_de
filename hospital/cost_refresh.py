"""Fill only Snowflake-attributed query credits after account-usage latency."""
import argparse
import json
from pathlib import Path
from hospital.live import connection


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',default='artifacts/measurements.json')
    a=p.parse_args()
    path=Path(a.input)
    records=json.loads(path.read_text())
    with connection('dev') as c:
        for r in records:
            if r.get('evidence')!='MEASURED' or not r.get('query_id'):
                continue
            stats=c.cursor().execute('SELECT CREDITS_ATTRIBUTED_COMPUTE FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY WHERE QUERY_ID=%s',
                                     (r['query_id'],)).fetchone()
            if stats and stats[0] is not None:
                r['credits_used']=float(stats[0])
                r['cost_basis']='QUERY_ATTRIBUTION_HISTORY.CREDITS_ATTRIBUTED_COMPUTE (excludes idle)'
                c.cursor().execute('UPDATE MONITORING.BENCHMARK_METADATA SET CREDITS_USED=%s WHERE QUERY_ID=%s',
                                   (r['credits_used'],r['query_id']))
    path.write_text(json.dumps(records,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
