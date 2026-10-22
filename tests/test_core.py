import copy
import json
import random
import tempfile
import unittest
from pathlib import Path
from hospital.core import (generate,reduce_events,freshness,durations,alert_conditions,
    change,benchmark_report,patient_history,write_data,ANCHOR)


class HospitalTests(unittest.TestCase):
    def setUp(self):
        self.data=generate(patients=10,admissions=30)

    def test_reproducible(self):
        self.assertEqual(self.data,generate(patients=10,admissions=30))
        self.assertNotEqual(self.data,generate(seed=43,patients=10,admissions=30))

    def test_files_reproducible(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            write_data(self.data,a)
            write_data(self.data,b)
            self.assertEqual((Path(a)/'manifest.json').read_bytes(),(Path(b)/'manifest.json').read_bytes())

    def test_rates_validate(self):
        with self.assertRaises(ValueError):
            generate(invalid_rate=1.5)

    def test_duplicate_out_of_order_and_replay(self):
        events=self.data['admission_events']
        state,rejected=reduce_events(events)
        self.assertEqual(len(state),30)
        self.assertGreater(len(rejected),0)
        self.assertTrue(all(e['event_version']==2 for e in state.values()))
        reverse,_=reduce_events(list(reversed(events)))
        replay,_=reduce_events(events+events,state)
        self.assertEqual(state,reverse)
        self.assertEqual(state,replay)
        middle=len(events)//2
        checkpoint,_=reduce_events(events[:middle])
        resumed,_=reduce_events(events[middle:],checkpoint)
        self.assertEqual(state,resumed)

    def test_source_silver_reconciliation(self):
        state,_=reduce_events(self.data['admission_events'])
        # Compare every source admission field, not counts alone.
        self.assertEqual({a['admission_id']:a for a in self.data['admissions']},
                         {k:e['payload'] for k,e in state.items()})

    def test_quarantine_high_version_cannot_overwrite(self):
        good=next(e for e in self.data['admission_events'] if e['admission_id']==1 and e['event_version']==2)
        bad=copy.deepcopy(good)
        bad['event_version']=99
        bad['payload']['bill_amount']=-1
        state,rejected=reduce_events([good,bad])
        self.assertEqual(state[1],good)
        self.assertEqual(rejected,[bad])

    def test_history(self):
        history=[p for p in patient_history(self.data['patients']) if p['patient_id']==1]
        self.assertEqual(len(history),2)
        self.assertEqual(history[0]['valid_to'],history[1]['valid_from'])
        self.assertFalse(history[0]['is_current'])
        self.assertTrue(history[1]['is_current'])

    def test_freshness(self):
        result=freshness(self.data['data_freshness'],ANCHOR)
        self.assertEqual([r['actual_age_minutes'] for r in result],[5,180,240])
        self.assertEqual([r['detected_status'] for r in result],['FRESH','STALE','STALE'])
        missing=dict(self.data['data_freshness'][0],last_successful_load=None)
        self.assertEqual(freshness([missing],ANCHOR)[0]['detected_status'],'STALE')

    def test_freshness_boundary(self):
        r=dict(self.data['data_freshness'][0],expected_interval_minutes=5)
        self.assertEqual(freshness([r],ANCHOR)[0]['detected_status'],'FRESH')

    def test_alerts(self):
        alerts=alert_conditions(self.data,ANCHOR)
        self.assertEqual(len(alerts['failures']),1)
        self.assertEqual(len(alerts['stale']),2)
        self.data['pipeline_run_log']=[]
        self.data['data_freshness']=self.data['data_freshness'][:1]
        self.assertEqual(alert_conditions(self.data,ANCHOR),{'failures':[],'stale':[]})

    def test_duration_previous_success(self):
        r=self.data['pipeline_run_log'][0]
        rows=[r,dict(r,run_id='2',started_at='2026-01-15T12:01:00+00:00',finished_at='2026-01-15T12:03:00+00:00')]
        result=durations(rows)
        self.assertEqual(result[0]['duration_seconds'],60)
        self.assertEqual(result[1]['previous_success_seconds'],60)
        self.assertEqual(result[1]['change_pct'],100)

    def test_percentages(self):
        self.assertEqual(change(10,7),-30)
        for b,a in [(0,5),(None,5),(10,None),(0,0)]:
            self.assertIsNone(change(b,a))

    def test_actual_measurement_report(self):
        rows=[dict(experiment='rewrite',workload='admissions',variant=v,elapsed_seconds=t,
                   credits_used=c,evidence='MEASURED',query_id=q)
              for v,t,c,q in [('before',10,2,'actual-query-1'),('after',7,1,'actual-query-2')]]
        with tempfile.TemporaryDirectory() as d:
            benchmark_report(rows,d)
            report=(Path(d)/'benchmark_report.md').read_text()
            self.assertIn('-30.00',report)
            self.assertIn('-50.00',report)
            self.assertIn('pair: PASS',report)
            self.assertTrue((Path(d)/'runtime.svg').exists())

    def test_synthetic_report_not_measured(self):
        rows=[dict(experiment='example',workload='a',variant=v,elapsed_seconds=t,
                   credits_used=None,evidence='SYNTHETIC_EXAMPLE') for v,t in [('before',10),('after',1)]]
        with tempfile.TemporaryDirectory() as d:
            benchmark_report(rows,d)
            self.assertIn('pair: UNVERIFIED',(Path(d)/'benchmark_report.md').read_text())

    def test_missing_measurements_report(self):
        rows=[dict(experiment='missing',workload='a',variant='before',elapsed_seconds=0,credits_used=None)]
        with tempfile.TemporaryDirectory() as d:
            benchmark_report(rows,d)
            self.assertIn('N/A',(Path(d)/'benchmark_report.md').read_text())


if __name__=='__main__':
    unittest.main()
