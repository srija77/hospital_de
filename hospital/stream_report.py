"""Measured stream CSV/chart plus coverage check; never invent missing run evidence."""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from hospital.live import connection,ROOT


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--stream',default='data/stream24')
    p.add_argument('--out',default='artifacts/stream24')
    a=p.parse_args()
    source=Path(a.stream)
    out=Path(a.out)
    out.mkdir(parents=True,exist_ok=True)
    log=[json.loads(line) for line in (source/'producer_runs.jsonl').read_text().splitlines()]
    if not log or not all(r['live'] for r in log):
        raise ValueError('Requires actual live producer batches')
    state=json.loads((source/'checkpoint.json').read_text())
    end=state.get('completed_at',max(r['completed_at'] for r in log))
    hours=(datetime.fromisoformat(end)-datetime.fromisoformat(state['started_at'])).total_seconds()/3600
    unique={r['batch']:r for r in log}
    expected=sum(r['sent_records'] for r in unique.values())
    with connection('dev') as c:
        start=state['started_at']
        cursor=c.cursor().execute((ROOT/'sql/ingestion/stream_metrics.sql').read_text())
        # SQL report includes all rows in this dedicated teaching environment.
        rows=cursor.fetchall()
        bronze=c.cursor().execute('SELECT COUNT(*) FROM BRONZE.ADMISSION_EVENTS').fetchone()[0]
        silver=c.cursor().execute('SELECT COUNT(*) FROM SILVER.ADMISSIONS').fetchone()[0]
    with (out/'minute_metrics.csv').open('w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['minute','events_per_minute','p50_seconds','p95_seconds'])
        w.writerows(rows)
    max_value=max([float(r[3] or 0) for r in rows]+[1])
    max_throughput=max([float(r[1]) for r in rows]+[1])
    points=[]
    epoch_start=datetime.fromisoformat(state['started_at']).timestamp()
    elapsed=max(1,datetime.fromisoformat(end).timestamp()-epoch_start)
    for idx,r in enumerate(rows):
        x=60+max(0,r[0].timestamp()-epoch_start)/elapsed*840
        points.append((x,260-float(r[2] or 0)/max_value*200,260-float(r[3] or 0)/max_value*200,520-float(r[1])/max_throughput*200))
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="600"><rect width="100%" height="100%" fill="white"/><text x="20" y="20">Actual stream: p50 blue / p95 red (seconds); events per minute green below</text>',
         f'<text x="20" y="50">Latency axis 0 to {max_value:.1f} seconds; throughput axis 0 to {max_throughput:.0f} events/minute</text>',
         '<line x1="60" y1="260" x2="900" y2="260" stroke="gray"/><line x1="60" y1="520" x2="900" y2="520" stroke="gray"/>',
         f'<text x="60" y="555">UTC time: {state["started_at"]} to {end}</text>',
         '<text x="60" y="580">Horizontal spacing follows elapsed time; inspect CSV for missing minute bins and restart gaps.</text>']
    for column,color in [(1,'blue'),(2,'red'),(3,'green')]:
        svg.append('<polyline fill="none" stroke="'+color+'" points="'+' '.join(f'{r[0]:.1f},{r[column]:.1f}' for r in points)+'"/>')
    svg.append('</svg>')
    (out/'stream_metrics.svg').write_text(''.join(svg))
    summary={'evidence':'MEASURED_LIVE','elapsed_hours':hours,'coverage_24h':hours>=24,
             'unique_batches':len(unique),'sent_physical_events':expected,'bronze':bronze,'silver':silver,
             'physical_count_match':expected==bronze,
             'warning':'Dedicated initially-empty teaching environment required; inspect full minute gaps and restart evidence'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))


if __name__=='__main__':
    main()
