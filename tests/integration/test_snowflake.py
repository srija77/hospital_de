import os
import unittest
from hospital.live import connection,sql_file,ROOT


@unittest.skipUnless(os.environ.get('RUN_SNOWFLAKE_TESTS')=='true','Requires explicit live DEV configuration')
class SnowflakeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.conn=connection('dev')

    def tearDown(self):
        self.conn.close()

    def test_no_duplicate_silver_keys(self):
        rows=self.conn.cursor().execute('SELECT ADMISSION_ID FROM SILVER.ADMISSIONS GROUP BY ADMISSION_ID HAVING COUNT(*)>1').fetchall()
        self.assertEqual(rows,[])

    def test_count_grains(self):
        counts=self.conn.cursor().execute('SELECT (SELECT COUNT(*) FROM BRONZE.ADMISSION_EVENTS),'
            '(SELECT COUNT(*) FROM SILVER.ADMISSIONS),(SELECT COUNT(*) FROM GOLD.FCT_ADMISSIONS)').fetchone()
        self.assertGreater(counts[0],counts[1])
        self.assertEqual(counts[1],counts[2])

    def test_anchor_precedence_and_quarantine(self):
        winner=self.conn.cursor().execute('SELECT EVENT_VERSION FROM SILVER.ADMISSIONS WHERE ADMISSION_ID=1').fetchone()
        self.assertEqual(winner[0],2)
        invalid=self.conn.cursor().execute("SELECT COUNT(*) FROM SILVER.QUARANTINED_EVENTS WHERE RAW:event_id::STRING='INVALID2'").fetchone()[0]
        self.assertGreater(invalid,0)

    def test_full_synthetic_batch_reconciliation(self):
        results=sql_file(self.conn,ROOT/'sql/ingestion/reconcile_phase5.sql')
        self.assertEqual(len(results),6)
        self.assertTrue(all(r['rows']==[] for r in results[-4:]),'Gold differs from synthetic baseline')

    def test_scd_history(self):
        rows=self.conn.cursor().execute('SELECT CITY,IS_CURRENT FROM GOLD.DIM_PATIENTS WHERE PATIENT_ID=1 ORDER BY VALID_FROM').fetchall()
        self.assertEqual(rows,[('Chennai',False),('Bengaluru',True)])


if __name__=='__main__':
    unittest.main()
