"""One-command local verification and reproducible instructor artifacts."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from hospital.live import ROOT


def main():
    os.chdir(ROOT)
    out=ROOT/'artifacts/validation'
    out.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'dbt/profiles.example.yml',ROOT/'dbt/profiles.yml')
    dbt=Path(sys.executable).parent/('dbt.exe' if os.name=='nt' else 'dbt')
    commands=[['-m','unittest','discover','-s','tests','-v'],['-m','hospital.validate'],
              ['-m','hospital.sql_check'],['-m','hospital.core','generate','--profile','demo'],
              ['-m','hospital.core','local-demo'],
              ['-m','hospital.streaming','--source','data/demo','--out','artifacts/native-stream-simulator','--max-events','20','--interval-seconds','0'],
              ['-m','hospital.core','report','--input','examples/benchmarks_synthetic.json','--out','artifacts/example-report'],
              ['-m','hospital.diagrams'],['-m','pip','check']]
    full=[[sys.executable]+c for c in commands]
    for target in ('dev','prod'):
        full.append([str(dbt),'parse','--project-dir','dbt','--profiles-dir','dbt','--target',target,'--no-partial-parse'])
    for phase in (7,8,9,10):
        full.append([sys.executable,'-m','hospital.package','--phase',str(phase),'--draft'])
    results=[]
    for i,cmd in enumerate(full):
        env=dict(os.environ,PYTHONIOENCODING='utf-8',DBT_SEND_ANONYMOUS_USAGE_STATS='false',RUN_SNOWFLAKE_TESTS='false')
        result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',env=env)
        log=out/f'{i+1:02}.log'
        log.write_text(result.stdout+result.stderr,encoding='utf-8')
        results.append({'command':cmd,'exit_code':result.returncode,'log':str(log.relative_to(ROOT))})
        print(f'{i+1}/{len(full)}: {"PASS" if result.returncode==0 else "FAIL"} '+ ' '.join(cmd[1:]),flush=True)
        if result.returncode:
            print(result.stdout+result.stderr)
    (out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    raise SystemExit(int(any(r['exit_code'] for r in results)))


if __name__=='__main__':
    main()
