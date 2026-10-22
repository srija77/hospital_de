import unittest
from hospital.live import require_prod_pipeline
from hospital.benchmark import workloads
from hospital.validate import validate
from unittest.mock import patch


class ProjectTests(unittest.TestCase):
    def test_project_assets(self):
        self.assertIn('passed',validate())

    def test_workload_pairs(self):
        queries=workloads()
        self.assertEqual(len(queries),6)
        for name in ['department','billing','patient_join']:
            for variant in ['before','after']:
                self.assertIn('SELECT',queries[name,variant].upper())

    def test_prod_guard(self):
        with patch.dict('os.environ',{'GITHUB_ACTIONS':'false','GITHUB_REF':'refs/heads/main'}):
            with self.assertRaises(PermissionError):
                require_prod_pipeline('prod')
        require_prod_pipeline('dev')


if __name__=='__main__':
    unittest.main()
