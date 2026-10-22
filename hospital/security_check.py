"""Live assertions using distinct users. Denied writes affect zero rows even if misgranted."""
import json
import os
from pathlib import Path


def connect(identity, role):
    import snowflake.connector
    return snowflake.connector.connect(account=os.environ['SNOWFLAKE_ACCOUNT'],
        user=os.environ[f'SNOWFLAKE_{identity}_USER'],
        private_key_file=os.environ[f'SNOWFLAKE_{identity}_KEY_PATH'],
        role=role,warehouse='HOSPITAL_DEV_WH' if identity=='ENGINEER' else 'HOSPITAL_PROD_WH',
        database='HOSPITAL_DEV' if identity=='ENGINEER' else 'HOSPITAL_PROD')


def denied(conn,sql):
    from snowflake.connector.errors import ProgrammingError
    try:
        conn.cursor().execute(sql).fetchall()
    except ProgrammingError as e:
        role_denial=sql.startswith('USE ROLE ') and any(s in str(e).lower() for s in ('not assigned','not authorized','does not exist'))
        if e.errno not in (2003,3001) and e.sqlstate!='42501' and not role_denial:
            raise
        return {'statement':sql,'denied':True,'error_code':e.errno}
    raise AssertionError('Operation unexpectedly allowed: '+sql)


def main():
    # Distinct identities prevent higher-role access from invalidating the test.
    users=[os.environ[f'SNOWFLAKE_{r}_USER'] for r in ['ADMIN','ANALYST','ENGINEER']]
    if len(set(users))!=3:
        raise ValueError('Use three separate test users')
    result=[]
    query='SELECT PATIENT_ID,PATIENT_NAME,EMAIL,PHONE,DATE_OF_BIRTH FROM GOLD.DIM_PATIENTS WHERE PATIENT_ID=1 AND IS_CURRENT'
    with connect('ADMIN','DE_ADMIN') as c:
        c.cursor().execute('USE SECONDARY ROLES NONE')
        actual=c.cursor().execute(query).fetchone()
        assert actual[1:] == ('Patient 000001','p1@example.invalid','5550000001',__import__('datetime').date(1951,1,1))
        # Object existence is established separately from expected-denial errors.
        for table in ['BRONZE.PATIENTS','SILVER.PATIENT_VERSIONS','GOLD.FCT_ADMISSIONS']:
            c.cursor().execute('SELECT 1 FROM '+table+' LIMIT 1').fetchall()
        result.append({'role':'DE_ADMIN','real_values_verified':True})
    with connect('ANALYST','DE_ANALYST') as c:
        c.cursor().execute('USE SECONDARY ROLES NONE')
        masked=c.cursor().execute(query).fetchone()
        assert masked[1:] == ('MASKED','***@***','**********',None)
        result.append({'role':'DE_ANALYST','masked_values_verified':True})
        for sql in ['UPDATE GOLD.FCT_ADMISSIONS SET BILL_AMOUNT=BILL_AMOUNT WHERE 1=0',
                    'SELECT RAW FROM BRONZE.PATIENTS LIMIT 1',
                    'SELECT EMAIL FROM SILVER.PATIENT_VERSIONS LIMIT 1',
                    'SELECT * FROM INTERMEDIATE.INT_PATIENT_HISTORY LIMIT 1',
                    'UPDATE HOSPITAL_DEV.SILVER.ADMISSIONS SET BILL_AMOUNT=BILL_AMOUNT WHERE 1=0']:
            result.append(denied(c,sql))
        # Analyst must also be unable to activate privileged roles.
        for role in ['DE_ADMIN','DE_DEPLOYER','DE_ENGINEER']:
            result.append(denied(c,'USE ROLE '+role))
    with connect('ENGINEER','DE_ENGINEER') as c:
        c.cursor().execute('USE SECONDARY ROLES NONE')
        c.cursor().execute('USE WAREHOUSE HOSPITAL_DEV_WH')
        result.append(denied(c,'UPDATE HOSPITAL_PROD.GOLD.FCT_ADMISSIONS SET BILL_AMOUNT=BILL_AMOUNT WHERE 1=0'))
        for role in ['DE_ADMIN','DE_DEPLOYER']:
            result.append(denied(c,'USE ROLE '+role))
    Path('artifacts/security').mkdir(parents=True,exist_ok=True)
    Path('artifacts/security/assertions.json').write_text(json.dumps(result,indent=2))
    print('Live masking and allowed/denied assertions passed')


if __name__=='__main__':
    main()
