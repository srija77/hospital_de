"""Optional DEV Gold refresh process; native ingestion/Silver run independently."""
import argparse
import subprocess
import sys
import time
from filelock import FileLock
from hospital.live import ROOT


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--live',action='store_true',required=True)
    p.add_argument('--minutes',type=float,default=10)
    p.add_argument('--interval-seconds',type=float,default=60)
    a=p.parse_args()
    if a.minutes<=0 or a.interval_seconds<1:
        p.error('Use a positive duration and an interval of at least one second')
    folder=ROOT/'artifacts/streaming'
    folder.mkdir(parents=True,exist_ok=True)
    with FileLock(str(folder/'gold_refresh.lock'),timeout=0):
        deadline=time.monotonic()+a.minutes*60
        while time.monotonic()<deadline:
            started=time.monotonic()
            result=subprocess.run([sys.executable,'-m','hospital.dbt_run','--env','dev','build'],cwd=ROOT)
            if result.returncode:
                raise SystemExit(result.returncode)
            time.sleep(min(max(0,a.interval_seconds-(time.monotonic()-started)),max(0,deadline-time.monotonic())))


if __name__=='__main__':
    main()
