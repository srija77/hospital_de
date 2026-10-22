-- Authorized security administrator only; DEV suspended alerts are opt-in.
USE ROLE SECURITYADMIN;
GRANT EXECUTE ALERT ON ACCOUNT TO ROLE DE_ENGINEER;
-- Schema ownership already permits CREATE ALERT; warehouse USAGE exists from bootstrap.
-- After exercise suspend alerts, then:
-- REVOKE EXECUTE ALERT ON ACCOUNT FROM ROLE DE_ENGINEER;
