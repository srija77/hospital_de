"""Observe two real snapshot states without resetting existing snapshot history."""
import json
import subprocess
from datetime import datetime,timezone
from hospital.live import connection


def main():
    alias='PATIENT_SNAPSHOT_DEMO_'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    common=['--project-dir','dbt','--profiles-dir','dbt','--target','dev']
    subprocess.run(['dbt','run']+common+['--select','stg_patients'],check=True)
    for cutoff in ['2025-12-30','2099-01-01']:
        subprocess.run(['dbt','snapshot']+common+['--select','patient_snapshot','--vars',
            json.dumps({'snapshot_alias':alias,'snapshot_as_of':cutoff})],check=True)
    with connection('dev') as c:
        rows=c.cursor().execute(f'SELECT PATIENT_ID,CITY,DBT_VALID_FROM,DBT_VALID_TO FROM INTERMEDIATE.{alias} WHERE PATIENT_ID=1 ORDER BY DBT_VALID_FROM').fetchall()
        assert len(rows)==2 and rows[0][3] is not None and rows[1][3] is None
        print(json.dumps({'table':alias,'rows':rows},default=str))
    print('Retain this actual snapshot history for evidence; remove only the named DEV demo table after review')


if __name__=='__main__':
    main()
