import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock,patch
from hospital.core import benchmark_report
from hospital.live import migrate,ROOT
from hospital.package import code_zip,draft_pdf


class OperationsTests(unittest.TestCase):
    def test_migration_rejects_checksum_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'V001__one.sql'
            p.write_text('SELECT 1;')
            conn=MagicMock()
            conn.cursor.return_value.execute.return_value.fetchall.return_value=[('different-hash','SUCCESS')]
            with self.assertRaisesRegex(ValueError,'Applied migration changed'):
                migrate(conn,d)

    def test_unapplied_migration_executes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'V001__one.sql'
            p.write_text('SELECT 1;')
            conn=MagicMock()
            conn.cursor.return_value.execute.return_value.fetchall.return_value=[]
            with patch('hospital.live.sql_file') as execute:
                migrate(conn,d)
                execute.assert_called_once_with(conn,p)

    def test_fast_query_improvement_does_not_pass_slowest_gate(self):
        rows=[]
        for work,b,a in [('slow',100,95),('fast',10,1)]:
            for variant,t in [('before',b),('after',a)]:
                rows.append(dict(experiment='rewrite',workload=work,variant=variant,elapsed_seconds=t,
                                 credits_used=None,evidence='MEASURED',query_id=f'test-fixture-{work}-{variant}'))
        with tempfile.TemporaryDirectory() as d:
            benchmark_report(rows,d)
            self.assertIn('pair: NOT MET',(Path(d)/'benchmark_report.md').read_text())

    def test_draft_reports_and_packaged_layout(self):
        specs=json.loads((ROOT/'config/submissions.json').read_text())['phases']
        with tempfile.TemporaryDirectory() as d:
            for phase in (7,8,9,10):
                spec=specs[str(phase)]
                pdf=Path(d)/spec['report']
                draft_pdf(pdf,phase,spec['sections'])
                self.assertTrue(pdf.read_bytes().startswith(b'%PDF-'))
                zpath=Path(d)/spec['code']
                code_zip(zpath,phase)
                with zipfile.ZipFile(zpath) as z:
                    names=z.namelist()
                    self.assertIn('README.md',names)
                    self.assertFalse(any(n.endswith(('profiles.yml','.p8','.pem')) for n in names))
                    self.assertIn({7:'producer/stream_producer.py',8:'dbt_project/snapshots/patient_snapshot.sql',
                                   9:'alerts/alert_definitions.sql',10:'.github/workflows/deploy.yml'}[phase],names)


if __name__=='__main__':
    unittest.main()
