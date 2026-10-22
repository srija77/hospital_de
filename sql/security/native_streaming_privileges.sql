-- Authorized SECURITYADMIN only; account execution privilege for DEV task owner.
USE ROLE SECURITYADMIN;
GRANT EXECUTE TASK ON ACCOUNT TO ROLE DE_ENGINEER;
-- DE_ENGINEER owns DEV schemas and has HOSPITAL_DEV_WH usage from bootstrap.
-- No new privileges are granted to DE_ANALYST or on PROD.
