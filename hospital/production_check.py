"""Read-only deploy verification. No PII output."""
from hospital.live import connection

def main():
    with connection('prod') as c:
        assert c.cursor().execute('SELECT RELEASE_VERSION FROM GOLD.RELEASE_INFO').fetchone()[0]
        assert c.cursor().execute('SELECT COUNT(*) FROM GOLD.FCT_ADMISSIONS').fetchone()[0]>0
        policies=c.cursor().execute("SELECT REF_COLUMN_NAME FROM TABLE(INFORMATION_SCHEMA.POLICY_REFERENCES(REF_ENTITY_NAME=>'HOSPITAL_PROD.GOLD.DIM_PATIENTS',REF_ENTITY_DOMAIN=>'TABLE')) WHERE POLICY_KIND='MASKING_POLICY'").fetchall()
        assert {x[0].upper() for x in policies} >= {'PATIENT_NAME','EMAIL','PHONE','DATE_OF_BIRTH'}
        print('PROD release, row count and four masking policy attachments verified')

if __name__=='__main__':
    main()
