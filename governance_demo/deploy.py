"""Deploy the governance demo to Snowflake: apply pending migrations, then (optionally) load data.

    python governance_demo/deploy.py --env dev --load-data

Auth comes from environment variables: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER and either
SNOWFLAKE_PRIVATE_KEY_PATH (key pair, used by CI) or SNOWFLAKE_PASSWORD.
PROD is only deployed from GitHub Actions.
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

from generate_data import write as write_csv

HERE = Path(__file__).resolve().parent


def connect(env):
    import snowflake.connector
    params = dict(account=os.environ['SNOWFLAKE_ACCOUNT'], user=os.environ['SNOWFLAKE_USER'],
                  role=os.environ.get('SNOWFLAKE_ROLE', 'GOV_DEPLOYER'), warehouse='GOV_DEMO_WH',
                  database=f'GOV_DEMO_{env.upper()}', session_parameters={'QUERY_TAG': f'gov_demo_deploy_{env}'})
    if os.environ.get('SNOWFLAKE_PRIVATE_KEY_PATH'):
        params['private_key_file'] = os.environ['SNOWFLAKE_PRIVATE_KEY_PATH']
    else:
        params['password'] = os.environ['SNOWFLAKE_PASSWORD']
    return snowflake.connector.connect(**params)


def migrate(conn):
    cur = conn.cursor()
    cur.execute('CREATE SCHEMA IF NOT EXISTS CONTROL')
    cur.execute('CREATE TABLE IF NOT EXISTS CONTROL.MIGRATION_HISTORY (VERSION VARCHAR, CHECKSUM VARCHAR, '
                'STATUS VARCHAR, APPLIED_AT TIMESTAMP_LTZ, APPLIED_BY VARCHAR)')
    for path in sorted((HERE / 'migrations').glob('V*.sql')):
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        prior = cur.execute('SELECT CHECKSUM, STATUS FROM CONTROL.MIGRATION_HISTORY WHERE VERSION = %s',
                            (path.name,)).fetchall()
        if any(status == 'SUCCESS' for _, status in prior):
            if any(old != checksum for old, _ in prior):
                raise SystemExit(f'{path.name} was already applied and has since been edited. '
                                 'Never change an applied migration; add a new V file instead.')
            print('  skip   ', path.name)
            continue
        print('  apply  ', path.name)
        cur.execute('DELETE FROM CONTROL.MIGRATION_HISTORY WHERE VERSION = %s', (path.name,))
        cur.execute("INSERT INTO CONTROL.MIGRATION_HISTORY VALUES (%s, %s, 'STARTED', CURRENT_TIMESTAMP(), CURRENT_USER())",
                    (path.name, checksum))
        conn.execute_string(path.read_text(encoding='utf-8'))
        cur.execute("UPDATE CONTROL.MIGRATION_HISTORY SET STATUS = 'SUCCESS', APPLIED_AT = CURRENT_TIMESTAMP() "
                    'WHERE VERSION = %s', (path.name,))


def load(conn):
    csv_path = write_csv()
    cur = conn.cursor()
    cur.execute('TRUNCATE TABLE CLINICAL.PATIENTS')
    cur.execute(f"PUT 'file://{csv_path.as_posix()}' @CLINICAL.%PATIENTS OVERWRITE = TRUE")
    result = cur.execute("COPY INTO CLINICAL.PATIENTS FROM @CLINICAL.%PATIENTS "
                         "FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '\"') "
                         "PURGE = TRUE").fetchall()
    print('  loaded ', sum(row[3] for row in result), 'rows into CLINICAL.PATIENTS')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', choices=['dev', 'prod'], default='dev')
    parser.add_argument('--load-data', action='store_true')
    args = parser.parse_args()
    if args.env == 'prod' and os.environ.get('GITHUB_ACTIONS') != 'true':
        sys.exit('PROD is deployed only by the GitHub Actions pipeline.')
    conn = connect(args.env)
    try:
        print(f'Deploying to GOV_DEMO_{args.env.upper()}')
        migrate(conn)
        if args.load_data:
            load(conn)
    finally:
        conn.close()
    print('Done')


if __name__ == '__main__':
    main()
