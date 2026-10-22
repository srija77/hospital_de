# Alerting plan and reproducible tests

| Scenario | Condition / threshold | Default channel / responder | Message and action |
|---|---|---|---|
| Pipeline failure | >=1 FAILED run in last 24 hours | MONITORING.ALERT_EVENTS / instructor or designated on-call | Pipeline, failed timestamp, error code; inspect run/query history, fix cause, replay batch |
| Stale data | age > expected interval; NULL success also stale | MONITORING.ALERT_EVENTS / instructor or designated on-call | Dataset, last load, actual age, expected threshold; check ingestion/warehouse and recover missing batch |

Setup detection:
```powershell
python -m hospital.live sql --file sql/monitoring/monitoring_queries.sql
python -m hospital.live sql --file sql/monitoring/alert_procedure.sql
python -m hospital.live sql --file sql/monitoring/seed_demo_scenarios.sql
python -m hospital.live sql --file sql/monitoring/detect_alerts.sql
```
Query ALERT_EVENTS. Expected at least FAILURE|SYNTHETIC_FAILURE_1 and STALE|SYNTHETIC_STALE|... entries, with current detected_at and actionable text. Run detect_alerts twice: the same incident keys must not multiply. This proves detection/persistence even without an external integration.

Controlled true failure:
```powershell
python -m hospital.live fail
python -m hospital.live sql --file sql/monitoring/detect_alerts.sql
```
The first process must exit nonzero due to an actual Snowflake divide-by-zero; a UUID run log row must exist. If authentication fails before connection, this is not the intended controlled test. Save the real query ID from query history plus matching run UUID and ALERT_EVENTS row.

Scheduled mechanism: administrator grants CREATE ALERT on HOSPITAL_DEV.MONITORING, EXECUTE ALERT on account and warehouse USAGE to DE_ENGINEER as narrowly needed. Execute alert_definitions.sql in DEV. Alerts are created suspended. After explicit scheduling approval run ALTER ALERT ... RESUME and EXECUTE ALERT ... for both objects in Snowsight. Verify INFORMATION_SCHEMA.ALERT_HISTORY condition/action results and the durable event row. Suspend both after demonstration. Scheduled alert execution may incur warehouse cost.

Recovery: successful load/build updates actual freshness; for the synthetic stale row only, run UPDATE MONITORING.DATA_FRESHNESS SET LAST_SUCCESSFUL_LOAD=CURRENT_TIMESTAMP(),FRESHNESS_STATUS='FRESH',LAST_CHECKED_AT=CURRENT_TIMESTAMP() WHERE DATASET_NAME='SYNTHETIC_STALE';. Re-query FRESHNESS_DASHBOARD and document historical alert retained. No production model write is involved.

Optional external delivery: authorized admin configures TYPE=EMAIL notification integration and verified ALLOWED_RECIPIENTS, grants integration USAGE, then tests SYSTEM$SEND_EMAIL. To use email in the scheduled action, promote a reviewed procedure change that calls the integration after persistence. Capture verified inbox delivery and alert execution history before asserting email was delivered. Default implementation intentionally claims only durable SQL detection.

Evidence to capture: stale freshness row, failure UUID/query history, both corresponding ALERT_EVENTS rows, scheduled history if enabled, exact query IDs/timestamps, recipient definition and recovery screenshot.
