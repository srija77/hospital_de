"""Local structural validation; not a Snowflake SQL compiler or security audit."""
import csv
import re
from pathlib import Path
import yaml
from hospital.live import ROOT


def validate(root=ROOT):
    errors=[]
    def check(condition,message):
        if not condition:
            errors.append(message)
    for name in ['ci','deploy']:
        path=root/f'.github/workflows/{name}.yml'
        obj=yaml.load(path.read_text(),Loader=yaml.BaseLoader)
        check('on' in obj and 'jobs' in obj,f'{name}: missing triggers/jobs')
        check(obj.get('permissions',{}).get('contents')=='read',f'{name}: permissions')
    deploy=yaml.load((root/'.github/workflows/deploy.yml').read_text(),Loader=yaml.BaseLoader)
    check(deploy['on']['push']['branches']==['main'],'deploy trigger must restrict main')
    check(deploy['jobs']['prod']['environment']=='production','PROD environment required')
    check(deploy['jobs']['prod']['needs']=='dev','DEV must gate PROD')
    migrations=list((root/'migrations').glob('*.sql'))
    check(bool(migrations),'No migrations')
    for path in migrations:
        check(bool(re.fullmatch(r'V\d{3}__[a-z_]+\.sql',path.name)),f'Invalid migration name: {path.name}')
        statement_text=re.sub(r'--[^\n]*','',path.read_text()).strip()
        check(statement_text.endswith(';'),f'Missing SQL terminator: {path}')
    schema=yaml.safe_load((root/'dbt/models/schema.yml').read_text())
    check(len(schema['models'])>=2,'Missing fact/dimension definitions')
    check(all(m['config']['contract']['enforced'] for m in schema['models']),'Contracts missing')
    check(len(list((root/'dbt/tests').glob('*.sql')))>=2,'Custom business tests missing')
    check(bool(list((root/'dbt/snapshots').glob('*.sql'))),'Snapshot missing')
    for path in (root/'dbt/models').rglob('*.sql'):
        text=path.read_text()
        check('HOSPITAL_DEV.' not in text and 'HOSPITAL_PROD.' not in text,f'Hardcoded model database: {path}')
    for part in ['grants','masking_policies','pii_tags','environment_setup','masking_policy_test']:
        check((root/f'sql/security/{part}.sql').exists(),'Missing security SQL: '+part)
    trace=root/'docs/traceability.csv'
    check(trace.exists(),'Missing traceability')
    if trace.exists():
        with trace.open(encoding='utf-8',newline='') as handle:
            rows=list(csv.DictReader(handle))
        for phase in ['9','10']:
            check(len([r for r in rows if r['phase']==phase])>=13,'Incomplete Phase '+phase)
        for row in rows:
            for item in row['implementation'].split(';'):
                check((root/item).exists(),'Missing traceability asset: '+item)
    # Scan authored text, excluding generated artifacts and supplied references.
    for folder in ['hospital','sql','config','migrations','.github','dbt','tests']:
        for path in (root/folder).rglob('*'):
            if path.suffix not in ('.py','.sql','.json','.yml') or any(x in path.parts for x in ['target','logs','__pycache__']):
                continue
            text=path.read_text(encoding='utf-8')
            check(not re.search(r'-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----',text),'Private key found: '+str(path))
            check(not re.search(r'(?i)(?:password|token)\s*[:=]\s*[\x27\x22][A-Za-z0-9_+/=-]{16,}',text),'Possible literal credential: '+str(path))
    if errors:
        raise ValueError('\n'.join(errors))
    from hospital.sql_check import validate_sql
    validate_sql()
    return 'Local workflow, migration, dbt definition, secret-pattern and traceability checks passed'


if __name__=='__main__':
    print(validate())
