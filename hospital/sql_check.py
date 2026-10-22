"""Snowflake-dialect parser checks; unsupported commands still require live compilation."""
import json
import logging
from hospital.live import ROOT
import sqlglot
from sqlglot import exp


def validate_sql():
    logging.getLogger('sqlglot').setLevel(logging.ERROR)
    errors=[]
    unsupported=[]
    count=0
    files=sorted((ROOT/'sql').rglob('*.sql'))+sorted((ROOT/'migrations').glob('*.sql'))
    for p in files:
        try:
            statements=sqlglot.parse(p.read_text(encoding='utf-8'),read='snowflake')
            count+=len(statements)
            if any(isinstance(s,exp.Command) for s in statements):
                unsupported.append(p.relative_to(ROOT).as_posix())
        except sqlglot.errors.ParseError as e:
            errors.append({'file':p.relative_to(ROOT).as_posix(),'error':str(e)})
    result=dict(files=len(files),statements=count,unsupported_commands=unsupported,errors=errors,
                scope='Local syntax only; command fallbacks and all Snowflake semantics require live validation')
    if errors:
        raise ValueError(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    print(json.dumps(validate_sql(),indent=2))
