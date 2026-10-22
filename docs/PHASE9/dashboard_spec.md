# Four-section Snowsight dashboard

Prerequisites: live migrate/load + dbt build, monitoring_queries.sql executed after Gold exists. Run alert_procedure.sql once and seed_demo_scenarios.sql for labelled examples. Select HOSPITAL_DEV, DE_ENGINEER and HOSPITAL_DEV_WH. Native Snowsight dashboard availability may depend on account UI; four saved SQL worksheets displayed together are an acceptable monitoring interface.

Create four query tiles/worksheets:
1. SELECT DATASET_NAME,LAST_SUCCESSFUL_LOAD,EXPECTED_INTERVAL_MINUTES,ACTUAL_AGE_MINUTES,DETECTED_STATUS FROM MONITORING.FRESHNESS_DASHBOARD ORDER BY DATASET_NAME;
2. SELECT * FROM MONITORING.ROW_COUNT_DASHBOARD;
3. SELECT * FROM MONITORING.FAILURE_DASHBOARD ORDER BY FAILURE_TIMESTAMP DESC;
4. SELECT PIPELINE_NAME,MODEL_NAME,STARTED_AT,FINISHED_AT,DURATION_SECONDS,PREVIOUS_SUCCESS_SECONDS,CHANGE_PCT,STATUS FROM MONITORING.RUNTIME_DASHBOARD ORDER BY STARTED_AT DESC;

Use table visualizations for timestamps/messages; optional bar chart for runtime. Refresh at recording start, after seeding scenarios, after the controlled failure and after recovery. Screenshot all four sections with account/database/role and actual visible time. Distinguish SYNTHETIC_* rows from real hospital_load UUIDs.

Freshness: actual pipeline rows should be fresh after successful execution; SYNTHETIC_STALE is about 180 minutes old against 60-minute interval. Raw stored freshness_status is descriptive fixture state; DETECTED_STATUS is calculated now and is authoritative.

Counts: Bronze includes two versions/admission, duplicates and invalid events. Silver has one winner per admission; Gold fact has the same admission grain. Gold dimension has version grain and is not compared to Bronze event counts. BRONZE_SILVER_DIFFERENCE includes superseded valid versions in addition to duplicates and quarantine; do not describe the whole difference as duplicates. Latest success includes actual hospital_load and hospital_native_stream runs, not synthetic logs. During native streaming, Gold can lag Silver until the next successful scheduled dbt refresh.

Failures: seeded SYNTHETIC_FAILURE_1 is labelled. python -m hospital.live fail creates a genuine failed Snowflake query and a UUID error record. FAILED rows in last 24h count by pipeline.

Runtime: first run has no comparison. Later matching pipeline/model success gives a previous duration. A failed run can compare its duration against previous success but must be interpreted as a failed operation. Percentages with zero previous duration are NULL.
