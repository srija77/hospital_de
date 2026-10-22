-- Live demo script. Run in Snowsight, top to bottom, after the pipeline has deployed DEV.
-- Secondary roles OFF so each USE ROLE shows exactly what that role sees.
USE SECONDARY ROLES NONE;
USE WAREHOUSE GOV_DEMO_WH;
USE DATABASE GOV_DEMO_DEV;

------------------------------------------------------------------------------------------
-- PART 1: SENSITIVE DATA. Same query, three roles, three different answers.
------------------------------------------------------------------------------------------
USE ROLE GOV_ADMIN;     -- data steward: everything, all 200 rows
SELECT FULL_NAME, EMAIL, PHONE, DATE_OF_BIRTH, AADHAAR_NUMBER, BRANCH, DIAGNOSIS
FROM CLINICAL.PATIENTS ORDER BY PATIENT_ID LIMIT 5;

USE ROLE GOV_DOCTOR;    -- clinician: Chennai rows only, identity visible, Aadhaar partly masked
SELECT FULL_NAME, EMAIL, PHONE, DATE_OF_BIRTH, AADHAAR_NUMBER, BRANCH, DIAGNOSIS
FROM CLINICAL.PATIENTS ORDER BY PATIENT_ID LIMIT 5;

USE ROLE GOV_ANALYST;   -- analyst: all rows, identity masked, birth year only
SELECT FULL_NAME, EMAIL, PHONE, DATE_OF_BIRTH, AADHAAR_NUMBER, BRANCH, DIAGNOSIS
FROM CLINICAL.PATIENTS ORDER BY PATIENT_ID LIMIT 5;

-- Row counts per role (row access policy)
USE ROLE GOV_ANALYST; SELECT BRANCH, COUNT(*) AS PATIENTS FROM CLINICAL.PATIENTS GROUP BY BRANCH;
USE ROLE GOV_DOCTOR;  SELECT BRANCH, COUNT(*) AS PATIENTS FROM CLINICAL.PATIENTS GROUP BY BRANCH;

-- Analysts can still do useful, de-identified analytics
USE ROLE GOV_ANALYST;
SELECT BRANCH, DIAGNOSIS, YEAR(DATE_OF_BIRTH) AS BIRTH_YEAR, COUNT(*) AS PATIENTS, ROUND(AVG(BILL_AMOUNT)) AS AVG_BILL
FROM CLINICAL.PATIENTS GROUP BY ALL ORDER BY PATIENTS DESC LIMIT 10;

-- Masked data cannot be bypassed by copying it: the copy holds masked values
-- (an analyst has no CREATE rights here, so this is shown, not run)
-- CREATE TABLE MY_COPY AS SELECT * FROM CLINICAL.PATIENTS;

------------------------------------------------------------------------------------------
-- PART 2: DATA GOVERNANCE. What is sensitive, who owns it, what protects it, who used it.
------------------------------------------------------------------------------------------
USE ROLE GOV_ADMIN;

-- Tags on the table and on each column
SELECT * FROM TABLE(INFORMATION_SCHEMA.TAG_REFERENCES('GOV_DEMO_DEV.CLINICAL.PATIENTS', 'TABLE'));
SELECT COLUMN_NAME, TAG_NAME, TAG_VALUE
FROM TABLE(INFORMATION_SCHEMA.TAG_REFERENCES_ALL_COLUMNS('GOV_DEMO_DEV.CLINICAL.PATIENTS', 'TABLE'))
ORDER BY COLUMN_NAME;

-- Which policies protect the table (masking via tag, plus the row policy)
SELECT POLICY_NAME, POLICY_KIND, REF_COLUMN_NAME, TAG_NAME, POLICY_STATUS
FROM TABLE(INFORMATION_SCHEMA.POLICY_REFERENCES(REF_ENTITY_NAME => 'GOV_DEMO_DEV.CLINICAL.PATIENTS', REF_ENTITY_DOMAIN => 'TABLE'));

-- Who may see which branch (change access by editing data, not code)
SELECT * FROM GOVERNANCE.BRANCH_ACCESS;

-- Account-wide inventory and audit (ACCOUNT_USAGE views can lag by up to ~2-3 hours)
SELECT OBJECT_DATABASE, OBJECT_NAME, COLUMN_NAME, TAG_NAME, TAG_VALUE
FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
WHERE TAG_NAME = 'PII_TYPE' AND OBJECT_DELETED IS NULL ORDER BY 1, 2, 3;

SELECT QUERY_START_TIME, USER_NAME, f.value:"objectName"::STRING AS OBJECT_READ
FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY, LATERAL FLATTEN(BASE_OBJECTS_ACCESSED) f
WHERE f.value:"objectName"::STRING ILIKE 'GOV_DEMO_%.CLINICAL.PATIENTS'
ORDER BY QUERY_START_TIME DESC LIMIT 20;

-- Auto-detect sensitive columns (Snowflake classification). Run as a role that sees unmasked rows.
USE ROLE ACCOUNTADMIN;
CALL SYSTEM$CLASSIFY('GOV_DEMO_DEV.CLINICAL.PATIENTS', NULL);

------------------------------------------------------------------------------------------
-- PART 3: CI/CD. What the pipeline deployed, when, and by whom.
------------------------------------------------------------------------------------------
USE ROLE GOV_ADMIN;
SELECT * FROM GOV_DEMO_DEV.MONITORING.DEPLOYMENTS ORDER BY VERSION;
SELECT * FROM GOV_DEMO_PROD.MONITORING.DEPLOYMENTS ORDER BY VERSION;

------------------------------------------------------------------------------------------
-- PART 4: MONITORING. Data quality, who touched PII, and an alert.
------------------------------------------------------------------------------------------
USE ROLE GOV_ADMIN;
SELECT * FROM MONITORING.DATA_QUALITY_CHECKS;                 -- all PASS
SELECT * FROM MONITORING.PII_ACCESS_LOG ORDER BY QUERY_START_TIME DESC LIMIT 20;  -- appears after ~1-3 h

-- Break the data on purpose, then let the alert catch it
USE ROLE GOV_DEPLOYER;
INSERT INTO CLINICAL.PATIENTS (PATIENT_ID, BRANCH, BILL_AMOUNT) VALUES (1, 'Mumbai', -500);
SELECT * FROM MONITORING.DATA_QUALITY_CHECKS;                 -- three rules FAIL
EXECUTE ALERT MONITORING.DATA_QUALITY_ALERT;                  -- wait a few seconds
SELECT * FROM MONITORING.ALERT_LOG ORDER BY ALERT_TIME DESC;   -- failures logged

-- Clean up
DELETE FROM CLINICAL.PATIENTS WHERE BRANCH = 'Mumbai';
TRUNCATE TABLE MONITORING.ALERT_LOG;

-- To run the alert every hour for real (uses warehouse credits):
-- ALTER ALERT MONITORING.DATA_QUALITY_ALERT RESUME;
SHOW ALERTS IN SCHEMA MONITORING;
