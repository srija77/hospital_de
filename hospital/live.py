"""Explicit live Snowflake commands. Never logs credentials or connection dictionaries."""
import argparse
import hashlib
import io
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def connection(env='dev', role=None):
    import snowflake.connector
    conf = json.loads((ROOT/'config/config.example.json').read_text())[env]
    return snowflake.connector.connect(account=os.environ['SNOWFLAKE_ACCOUNT'],
        user=os.environ['SNOWFLAKE_USER'], private_key_file=os.environ['SNOWFLAKE_PRIVATE_KEY_PATH'],
        role=role or conf['role'], database=conf['database'], warehouse=conf['warehouse'],
        session_parameters={'QUERY_TAG': 'hospital_capstone', 'TIMEZONE': 'UTC'})


def sql_file(conn, path):
    # Connector splitter respects quoted SQL and $$ procedure bodies.
    output = []
    for cursor in conn.execute_stream(io.StringIO(Path(path).read_text(encoding='utf-8'))):
        output.append(dict(query_id=cursor.sfqid, rows=cursor.fetchall() if cursor.description else []))
    return output


def require_prod_pipeline(env):
    if env == 'prod' and (os.environ.get('GITHUB_ACTIONS') != 'true' or
                           os.environ.get('GITHUB_REF') != 'refs/heads/main'):
        raise PermissionError('PROD writes require the protected main deployment workflow')


def migrate(conn, folder=ROOT/'migrations'):
    conn.cursor().execute('CREATE SCHEMA IF NOT EXISTS CONTROL')
    conn.cursor().execute('CREATE TABLE IF NOT EXISTS CONTROL.MIGRATION_HISTORY '
                          '(VERSION VARCHAR, CHECKSUM VARCHAR, APPLIED_AT TIMESTAMP_TZ, STATUS VARCHAR)')
    for path in sorted(Path(folder).glob('V*.sql')):
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        prior = conn.cursor().execute('SELECT CHECKSUM,STATUS FROM CONTROL.MIGRATION_HISTORY WHERE VERSION=%s',
                                      (path.name,)).fetchall()
        if prior:
            if any(row[0] != checksum for row in prior):
                raise ValueError('Applied migration changed: '+path.name)
            if any(row[1] == 'SUCCESS' for row in prior):
                continue
        conn.cursor().execute('INSERT INTO CONTROL.MIGRATION_HISTORY VALUES (%s,%s,CURRENT_TIMESTAMP(),%s)',
                              (path.name, checksum, 'STARTED'))
        sql_file(conn, path)
        conn.cursor().execute("UPDATE CONTROL.MIGRATION_HISTORY SET STATUS='SUCCESS',APPLIED_AT=CURRENT_TIMESTAMP() WHERE VERSION=%s AND CHECKSUM=%s",
                              (path.name, checksum))


def record_run(conn, run_id, started, status, count, error=None, model='bronze_silver', finished=None):
    conn.cursor().execute('INSERT INTO MONITORING.PIPELINE_RUN_LOG VALUES '
                          '(%s,%s,%s,%s,%s,%s,%s,%s)',
                          (run_id, 'hospital_load', model, started, finished or datetime.now(timezone.utc), status, count, error))


def load(conn, directory, controlled_failure=False, include_events=True):
    run_id, started = str(uuid.uuid4()), datetime.now(timezone.utc)
    count = 0
    try:
        if controlled_failure:
            # Genuine Snowflake execution failure, not a fabricated status row.
            conn.cursor().execute('SELECT 1/0 AS CONTROLLED_PIPELINE_FAILURE')
        for name in ['patients', 'admissions', 'admission_events', 'pipeline_run_log',
                     'data_quality_results', 'data_freshness', 'benchmark_metadata']:
            if name == 'admission_events' and not include_events:
                continue
            path = Path(directory)/f'{name}.json'
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            # Content-addressed prefix keeps immutable names across retries.
            uri = path.resolve().as_posix().replace("'", "''")
            conn.cursor().execute(f"PUT 'file://{uri}' @BRONZE.HOSPITAL_STAGE/{digest}/ AUTO_COMPRESS=TRUE OVERWRITE=FALSE")
            cur = conn.cursor().execute(f"COPY INTO BRONZE.{name.upper()} (RAW,SOURCE_FILE) "
                f"FROM (SELECT $1,METADATA$FILENAME FROM @BRONZE.HOSPITAL_STAGE/{digest}/) "
                f"FILES=('{name}.json.gz') FILE_FORMAT=(FORMAT_NAME='BRONZE.JSON_ARRAY') ON_ERROR=ABORT_STATEMENT FORCE=FALSE")
            cur.fetchall()
        sql_file(conn, ROOT/'sql/ingestion/silver.sql')
        count = conn.cursor().execute('SELECT COUNT(*) FROM SILVER.ADMISSIONS').fetchone()[0]
        record_run(conn, run_id, started, 'SUCCESS', count)
        for dataset, table in [('BRONZE.ADMISSION_EVENTS', 'BRONZE.ADMISSION_EVENTS'), ('SILVER.ADMISSIONS', 'SILVER.ADMISSIONS')]:
            row_count = conn.cursor().execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            conn.cursor().execute('MERGE INTO MONITORING.DATA_FRESHNESS t USING (SELECT %s DATASET_NAME) s '
                'ON t.DATASET_NAME=s.DATASET_NAME WHEN MATCHED THEN UPDATE SET '
                "LAST_SUCCESSFUL_LOAD=CURRENT_TIMESTAMP(),FRESHNESS_STATUS='FRESH',ROW_COUNT=%s,LAST_CHECKED_AT=CURRENT_TIMESTAMP() "
                "WHEN NOT MATCHED THEN INSERT VALUES(s.DATASET_NAME,CURRENT_TIMESTAMP(),60,'FRESH',%s,CURRENT_TIMESTAMP())",
                (dataset, row_count, row_count))
        return dict(run_id=run_id, rows=count)
    except Exception as exc:
        # Store only error class/code; connector messages could contain sensitive SQL.
        record_run(conn, run_id, started, 'FAILED', count, f'{type(exc).__name__}: code={getattr(exc,"errno",None)}')
        raise


def refresh_gold(conn):
    count = conn.cursor().execute('SELECT COUNT(*) FROM GOLD.FCT_ADMISSIONS').fetchone()[0]
    conn.cursor().execute("MERGE INTO MONITORING.DATA_FRESHNESS t USING (SELECT 'GOLD.FCT_ADMISSIONS' DATASET_NAME) s "
        'ON t.DATASET_NAME=s.DATASET_NAME WHEN MATCHED THEN UPDATE SET LAST_SUCCESSFUL_LOAD=CURRENT_TIMESTAMP(),'
        "FRESHNESS_STATUS='FRESH',ROW_COUNT=%s,LAST_CHECKED_AT=CURRENT_TIMESTAMP() WHEN NOT MATCHED THEN "
        "INSERT VALUES(s.DATASET_NAME,CURRENT_TIMESTAMP(),60,'FRESH',%s,CURRENT_TIMESTAMP())", (count,count))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['migrate','sql','load','fail','gold-refresh'])
    p.add_argument('--env', choices=['dev','prod'], default='dev')
    p.add_argument('--file')
    p.add_argument('--data', default='data/demo')
    p.add_argument('--skip-events', action='store_true', help='Bootstrap patients/batch baseline before native streaming')
    args = p.parse_args()
    require_prod_pipeline(args.env)
    with connection(args.env) as conn:
        if args.command == 'migrate':
            migrate(conn)
        elif args.command == 'sql':
            print(json.dumps(sql_file(conn,args.file),default=str))
        elif args.command == 'gold-refresh':
            refresh_gold(conn)
        else:
            print(json.dumps(load(conn,args.data,args.command=='fail',include_events=not args.skip_events)))


if __name__ == '__main__':
    main()
