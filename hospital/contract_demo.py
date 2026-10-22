"""Avoid shell-specific JSON argument quoting in the dbt contract demonstration."""
import json
import subprocess
from pathlib import Path


def main():
    common=['--project-dir','dbt','--profiles-dir','dbt','--target','dev','--select','fct_admissions']
    failed=subprocess.run(['dbt','run']+common+['--vars',json.dumps({'break_contract':True})],capture_output=True,text=True)
    output=failed.stdout+failed.stderr
    print(output)
    Path('artifacts/contract').mkdir(parents=True,exist_ok=True)
    Path('artifacts/contract/failure.log').write_text(output,encoding='utf-8')
    if failed.returncode==0:
        raise AssertionError('Deliberate contract mismatch unexpectedly succeeded')
    if 'contract' not in output.lower():
        raise AssertionError('Failure was not identified as a dbt contract failure; investigate before proceeding')
    fixed=subprocess.run(['dbt','build']+common,capture_output=True,text=True)
    print(fixed.stdout+fixed.stderr)
    Path('artifacts/contract/correction.log').write_text(fixed.stdout+fixed.stderr,encoding='utf-8')
    raise SystemExit(fixed.returncode)


if __name__=='__main__':
    main()
