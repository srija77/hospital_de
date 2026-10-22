"""Deterministic hospital fixtures, reference CDC and honest benchmark reporting."""
import argparse
import csv
import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from html import escape

ANCHOR = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)


def stamp(dt):
    return dt.isoformat()


def parse(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def generate(seed=42, patients=100, admissions=1000, duplicate_rate=.1,
             late_rate=.1, invalid_rate=.02, patient_update_rate=.2, failures=True):
    if patients < 2 or admissions < 4:
        raise ValueError('At least 2 patients and 4 admissions required for scenarios')
    for rate in (duplicate_rate, late_rate, invalid_rate, patient_update_rate):
        if not 0 <= rate <= 1:
            raise ValueError('Rates must be between zero and one')
    rng = random.Random(seed)
    ps, ads, events = [], [], []
    for i in range(1, patients + 1):
        p = dict(patient_id=i, patient_name=f'Patient {i:06}', email=f'p{i}@example.invalid',
                 phone=f'555{i:07}', date_of_birth=f'{1950+i%50}-01-01',
                 city='Chennai', updated_at=stamp(ANCHOR-timedelta(days=800)))
        ps.append(p)
        if i == 1 or rng.random() < patient_update_rate:
            ps.append(dict(p, city='Bengaluru', updated_at=stamp(ANCHOR-timedelta(days=15))))
    for i in range(1, admissions + 1):
        start = ANCHOR-timedelta(days=rng.randrange(730))
        a = dict(admission_id=i, patient_id=1 if i == 1 else rng.randint(1, patients),
                 admit_date=start.date().isoformat(), discharge_date=(start+timedelta(days=3)).date().isoformat(),
                 department=rng.choice(['Cardiology', 'Emergency', 'Orthopedics']),
                 admission_type=rng.choice(['Urgent', 'Elective']), bill_amount=rng.randint(100, 50000),
                 status='Discharged', updated_at=stamp(ANCHOR-timedelta(hours=1)))
        ads.append(a)
        for v in (1, 2):
            payload = dict(a, bill_amount=a['bill_amount'] if v == 2 else 100,
                           updated_at=stamp(ANCHOR-timedelta(hours=3-v)))
            e = dict(event_id=f'E{i:07}V{v}', admission_id=i, event_type='UPSERT',
                     event_time=payload['updated_at'], event_version=v, source_system='SYNTHETIC_HOSPITAL',
                     payload=payload, ingest_time=stamp(ANCHOR+timedelta(seconds=i*2+v)))
            if i == 1 or rng.random() < late_rate:
                if v == 1:
                    e['ingest_time'] = stamp(ANCHOR+timedelta(hours=2, seconds=i))
            events.append(e)
            if (i == 1 and v == 2) or rng.random() < duplicate_rate:
                events.append(dict(e))
        if i == 2 or rng.random() < invalid_rate:
            bad = dict(events[-1], event_id=f'INVALID{i}', event_version=3,
                       payload=dict(a, bill_amount=-100))
            events.append(bad)
    rng.shuffle(events)
    runs = [dict(run_id='SYNTHETIC_SUCCESS_1', pipeline_name='hospital_demo', model_name='silver',
                 started_at=stamp(ANCHOR-timedelta(minutes=3)), finished_at=stamp(ANCHOR-timedelta(minutes=2)),
                 status='SUCCESS', rows_processed=admissions, error_message='SYNTHETIC_EXAMPLE')]
    if failures:
        runs.append(dict(runs[0], run_id='SYNTHETIC_FAILURE_1', status='FAILED', rows_processed=0,
                         error_message='SYNTHETIC_EXAMPLE: controlled demo failure'))
    dq = [dict(check_id=i, check_name='nonnegative_bill', table_name='admissions',
               check_timestamp=stamp(ANCHOR), status=s, failed_row_count=n, severity='ERROR',
               details='SYNTHETIC_EXAMPLE: invalid events quarantined')
          for i, s, n in [(1, 'PASS', 0), (2, 'FAIL', 1)]]
    fresh = [dict(dataset_name=name, last_successful_load=stamp(ANCHOR-timedelta(minutes=age)),
                  expected_interval_minutes=60, freshness_status=status, row_count=admissions,
                  last_checked_at=stamp(ANCHOR)) for name, age, status in
             [('SYNTHETIC_FRESH', 5, 'FRESH'), ('SYNTHETIC_STALE', 180, 'STALE'),
              ('SYNTHETIC_FAILED', 240, 'FAILED')]]
    benchmark = [dict(benchmark_id='SYNTHETIC_EXAMPLE', workload_name='department',
                      run_timestamp=stamp(ANCHOR), configuration_name='SYNTHETIC_EXAMPLE',
                      elapsed_seconds=None, bytes_scanned=None, rows_returned=None,
                      warehouse_name=None, credits_used=None, cache_state='NOT_EXECUTED')]
    return dict(patients=ps, admissions=ads, admission_events=events, pipeline_run_log=runs,
                data_quality_results=dq, data_freshness=fresh, benchmark_metadata=benchmark)


def valid_event(e):
    try:
        p = e['payload']
        return (e['event_type'] == 'UPSERT' and int(e['event_version']) > 0
                and int(e['admission_id']) == int(p['admission_id'])
                and int(p['patient_id']) > 0 and float(p['bill_amount']) >= 0
                and p['status'] in ('Admitted', 'Discharged')
                and (not p.get('discharge_date') or p['discharge_date'] >= p['admit_date']))
    except (KeyError, TypeError, ValueError):
        return False


def event_key(e):
    # Identical precedence in Silver SQL; arrival time never supersedes a version.
    return int(e['event_version']), e['event_time'], e['event_id']


def reduce_events(events, state=None):
    state = dict(state or {})
    rejected = []
    for e in events:
        if not valid_event(e):
            rejected.append(e)
            continue
        k = e['admission_id']
        if k not in state or event_key(e) > event_key(state[k]):
            state[k] = e
    return state, rejected


def patient_history(patients):
    grouped = {}
    for p in patients:
        grouped.setdefault(p['patient_id'], {})[p['updated_at']] = p
    result = []
    for pid, versions in sorted(grouped.items()):
        ordered = sorted(versions.values(), key=lambda p: p['updated_at'])
        for idx, p in enumerate(ordered):
            result.append(dict(p, patient_key=f"{pid}|{p['updated_at']}", valid_from=p['updated_at'],
                               valid_to=ordered[idx+1]['updated_at'] if idx+1 < len(ordered) else None,
                               is_current=idx+1 == len(ordered)))
    return result


def freshness(rows, now):
    output = []
    for r in rows:
        age = (now-parse(r['last_successful_load'])).total_seconds()/60 if r['last_successful_load'] else None
        output.append(dict(r, actual_age_minutes=age,
                           detected_status='STALE' if age is None or age > r['expected_interval_minutes'] else 'FRESH'))
    return output


def durations(runs):
    previous, out = {}, []
    for r in sorted(runs, key=lambda r: r['started_at']):
        key = r['pipeline_name'], r['model_name']
        duration = (parse(r['finished_at'])-parse(r['started_at'])).total_seconds() if r['finished_at'] else None
        prior = previous.get(key)
        out.append(dict(r, duration_seconds=duration, previous_success_seconds=prior,
                        change_pct=change(prior, duration)))
        if r['status'] == 'SUCCESS' and duration is not None:
            previous[key] = duration
    return out


def change(before, after):
    return None if before is None or after is None or before <= 0 else round((after-before)/before*100, 2)


def alert_conditions(data, now):
    return {'failures': [r for r in data['pipeline_run_log'] if r['status'] == 'FAILED'
                         and parse(r['finished_at']) >= now-timedelta(hours=24)],
            'stale': [r for r in freshness(data['data_freshness'], now) if r['detected_status'] == 'STALE']}


def write_data(data, target):
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    for name, rows in data.items():
        (target/f'{name}.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
        with (target/f'{name}.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows({k: json.dumps(v, sort_keys=True) if isinstance(v, dict) else v
                              for k, v in r.items()} for r in rows)
    with (target/'admission_events.jsonl').open('w', encoding='utf-8') as f:
        for e in data['admission_events']:
            f.write(json.dumps(e, sort_keys=True)+'\n')
    checksums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(target.iterdir()) if p.name != 'manifest.json' and p.is_file()}
    (target/'manifest.json').write_text(json.dumps(checksums, indent=2), encoding='utf-8')


def benchmark_report(records, out):
    """Pair within experiment/workload; medians across repeats, never invent credits."""
    import statistics
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    groups = {}
    for r in records:
        groups.setdefault((r['experiment'], r['workload']), {}).setdefault(r['variant'], []).append(r)
    lines = ['# Benchmark report', '', 'Negative change means improvement. Missing values are N/A.',
             'Synthetic examples are NOT verified Snowflake results.', '',
             '| Workload / experiment | Before runtime | After runtime | Runtime change % | Before cost | After cost | Cost change % |',
             '|---|---:|---:|---:|---:|---:|---:|']
    bars, summary, acceptance = [], [], []
    for (exp, work), variants in sorted(groups.items()):
        before, after = variants.get('before', []), variants.get('after', [])
        def median(rows, key):
            vals = [r[key] for r in rows if r.get(key) is not None]
            return statistics.median(vals) if vals else None
        b, a = median(before, 'elapsed_seconds'), median(after, 'elapsed_seconds')
        bc, ac = median(before, 'credits_used'), median(after, 'credits_used')
        measured = bool(before and after) and all(r.get('evidence') == 'MEASURED' and r.get('query_id') for r in before+after)
        pct = change(b, a)
        fmt = lambda v: 'N/A' if v is None else f'{v:.2f}'
        lines.append(f'| {work} / {exp} | {fmt(b)} | {fmt(a)} | {fmt(pct)} | {fmt(bc)} | {fmt(ac)} | {fmt(change(bc, ac))} |')
        conclusion = 'improved' if pct is not None and pct < 0 else 'did not improve or is unmeasured'
        lines += ['', f'{exp}/{work}: {conclusion}; evidence={"MEASURED" if measured else "UNVERIFIED / SYNTHETIC_EXAMPLE"}.', '']
        if measured and b is not None and a is not None:
            acceptance.append((b, pct))
        summary.append(dict(experiment=exp, workload=work, runtime_change_pct=pct, measured=measured))
        bars.append((f'{exp}/{work}', b, a))
    # Criterion is evaluated against the baseline-slowest measured workload, not any fast query.
    slowest = max(acceptance, default=None, key=lambda pair: pair[0])
    result = 'UNVERIFIED' if slowest is None else ('PASS' if slowest[1] is not None and slowest[1] <= -30 else 'NOT MET')
    lines += [f'30% improvement in baseline-slowest measured pair: {result}.',
              'Review repetition count, equivalence, cache conditions and warehouse evidence before accepting results.']
    (out/'benchmark_report.md').write_text('\n'.join(lines), encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    scale = max([v for _, b, a in bars for v in (b, a) if v is not None] or [1]) or 1
    evidence_label = 'MEASURED RECORDS' if records and all(r.get('evidence') == 'MEASURED' and r.get('query_id') for r in records) else 'UNVERIFIED / SYNTHETIC_EXAMPLE'
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{100+len(bars)*70}" role="img" aria-label="Benchmark runtime seconds"><rect width="100%" height="100%" fill="white"/><text x="20" y="25">{evidence_label}: seconds, blue before / green after; missing values omitted.</text>']
    for i, (name, b, a) in enumerate(bars):
        y = 65+i*70
        svg.append(f'<text x="10" y="{y}">{escape(name)}</text>')
        for offset, value, color in [(0, b, '#2563eb'), (24, a, '#15803d')]:
            if value is not None:
                svg.append(f'<rect x="300" y="{y-15+offset}" width="{value/scale*550}" height="18" fill="{color}"/><text x="860" y="{y+offset}">{value:.3f}</text>')
    svg.append('</svg>')
    (out/'runtime.svg').write_text(''.join(svg), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    gen = sub.add_parser('generate')
    gen.add_argument('--profile', choices=['demo', 'benchmark'], default='demo')
    gen.add_argument('--seed', type=int, default=42)
    gen.add_argument('--patients', type=int)
    gen.add_argument('--admissions', type=int)
    for flag, default in [('duplicate-rate', .1), ('late-rate', .1), ('invalid-rate', .02), ('patient-update-rate', .2)]:
        gen.add_argument('--'+flag, type=float, default=default)
    gen.add_argument('--no-failures', action='store_true')
    gen.add_argument('--out', default='data/demo')
    demo = sub.add_parser('local-demo')
    demo.add_argument('--out', default='artifacts/local')
    report = sub.add_parser('report')
    report.add_argument('--input', required=True)
    report.add_argument('--out', default='artifacts/report')
    args = parser.parse_args()
    if args.command == 'generate':
        data = generate(seed=args.seed, patients=args.patients or (100 if args.profile == 'demo' else 100000),
                        admissions=args.admissions or (1000 if args.profile == 'demo' else 500000),
                        duplicate_rate=args.duplicate_rate, late_rate=args.late_rate,
                        invalid_rate=args.invalid_rate, patient_update_rate=args.patient_update_rate,
                        failures=not args.no_failures)
        write_data(data, args.out)
        print(json.dumps({k: len(v) for k, v in data.items()}))
    elif args.command == 'local-demo':
        data = generate()
        state, rejected = reduce_events(data['admission_events'])
        target = Path(args.out)
        target.mkdir(parents=True, exist_ok=True)
        result = dict(evidence='LOCAL_REFERENCE_ONLY', bronze=len(data['admission_events']), silver=len(state),
                      gold=len(state), quarantined=len(rejected), alerts=alert_conditions(data, ANCHOR),
                      durations=durations(data['pipeline_run_log']))
        valid = [e for e in data['admission_events'] if valid_event(e)]
        result['duplicate_valid_events'] = len(valid)-len({e['event_id'] for e in valid})
        result['superseded_distinct_versions'] = len({e['event_id'] for e in valid})-len(state)
        result['count_bridge_verified'] = result['bronze'] == (result['silver']+result['quarantined']+
            result['duplicate_valid_events']+result['superseded_distinct_versions'])
        (target/'dashboard.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({k: result[k] for k in ('evidence', 'bronze', 'silver', 'gold', 'quarantined')}))
    else:
        benchmark_report(json.loads(Path(args.input).read_text(encoding='utf-8')), args.out)


if __name__ == '__main__':
    main()
