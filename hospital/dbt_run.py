"""Record actual dbt subprocess duration and failure without logging secrets."""
import argparse
import subprocess
import uuid
import json
from pathlib import Path
from datetime import datetime,timezone
from hospital.live import connection,record_run,refresh_gold,require_prod_pipeline

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--env',choices=['dev','prod'],default='dev')
    p.add_argument('args',nargs=argparse.REMAINDER)
    a=p.parse_args()
    require_prod_pipeline(a.env)
    start=datetime.now(timezone.utc)
    result=subprocess.run(['dbt']+ (a.args or ['build'])+
        ['--project-dir','dbt','--profiles-dir','dbt','--target',a.env],check=False)
    finished=datetime.now(timezone.utc)
    run_id=str(uuid.uuid4())
    with connection(a.env) as c:
        count=c.cursor().execute('SELECT COUNT(*) FROM GOLD.FCT_ADMISSIONS').fetchone()[0] if result.returncode==0 else 0
        record_run(c,run_id,start,'SUCCESS' if result.returncode==0 else 'FAILED',
                   count,None if result.returncode==0 else 'dbt returned nonzero',model='dbt_build',finished=finished)
        artifact=Path('dbt/target/run_results.json')
        manifest_path=Path('dbt/target/manifest.json')
        if artifact.exists() and datetime.fromtimestamp(artifact.stat().st_mtime,timezone.utc)>=start:
            results=json.loads(artifact.read_text())
            nodes=json.loads(manifest_path.read_text()).get('nodes',{}) if manifest_path.exists() else {}
            for r in results.get('results',[]):
                uid=r['unique_id']
                if not uid.startswith('test.'):
                    continue
                deps=nodes.get(uid,{}).get('depends_on',{}).get('nodes',[])
                table=next((n for n in deps if n.startswith('model.')),'unknown')
                status='PASS' if r['status']=='pass' else ('FAIL' if r['status'] in ('fail','error') else 'WARN')
                c.cursor().execute('INSERT INTO MONITORING.DATA_QUALITY_RESULTS VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                    (run_id+'|'+uid,uid,table,finished,status,r.get('failures'),'ERROR',
                     'MEASURED_DBT_RESULT; status='+r['status']))
        if result.returncode==0:
            refresh_gold(c)
    raise SystemExit(result.returncode)

if __name__=='__main__':
    main()
