-- Authorized administrator only, after explicit budget approval for dedicated DEV.
USE ROLE SYSADMIN;
GRANT MODIFY ON WAREHOUSE HOSPITAL_DEV_WH TO ROLE DE_ENGINEER;
-- Cleanup immediately after experiment:
-- REVOKE MODIFY ON WAREHOUSE HOSPITAL_DEV_WH FROM ROLE DE_ENGINEER;
