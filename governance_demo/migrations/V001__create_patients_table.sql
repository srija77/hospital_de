-- Runs inside GOV_DEMO_DEV or GOV_DEMO_PROD (the deploy script picks the database).
CREATE SCHEMA IF NOT EXISTS CLINICAL COMMENT = 'Curated patient data for consumers';
CREATE SCHEMA IF NOT EXISTS GOVERNANCE COMMENT = 'Tags, policies and access mappings';

CREATE TABLE IF NOT EXISTS CLINICAL.PATIENTS (
    PATIENT_ID      NUMBER        NOT NULL,
    FULL_NAME       VARCHAR,
    EMAIL           VARCHAR,
    PHONE           VARCHAR,
    DATE_OF_BIRTH   DATE,
    AADHAAR_NUMBER  VARCHAR,
    INSURANCE_ID    VARCHAR,
    BRANCH          VARCHAR,
    DIAGNOSIS       VARCHAR,
    BILL_AMOUNT     NUMBER(12, 2),
    ADMITTED_ON     DATE
) COMMENT = 'One row per patient admission. Synthetic demo data.';
