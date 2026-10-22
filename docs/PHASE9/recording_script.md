# Phase 9 instructor recording, 50 minutes

Pre-record prerequisites: activated venv; DEV credentials; setup/load/build complete; dbt docs generated from live account; benchmark data generated in a dedicated frozen DEV session if doing all experiments. Rehearse warehouse/layout budgets, permissions, scheduled-alert grants and external notification status. Open four Snowsight dashboard worksheets using dashboard_spec.md. Keep artifacts/measurements.json from this dataset only. No synthetic result can stand in for live benchmark proof.

00:00–04:00 explain hospital morning briefing, source -> Bronze -> Silver -> dbt -> Gold. Open observability_design_doc.md. Show DATA_SCENARIOS patient 1 and admission 1, explain same data powers the whole capstone.

04:00–09:00 run actual telemetry:
```powershell
python -m hospital.live load
python -m hospital.dbt_run build
python -m hospital.live sql --file sql/monitoring/monitoring_queries.sql
```
Expected: UUID successful runs, actual freshness rows, Bronze>Silver, Silver=Gold, runtime previous success after repeated run. Open/refresh all four dashboard queries; capture dashboard_all_four.png with role/database/time visible.

09:00–14:00 introduce stale scenario:
```powershell
python -m hospital.live sql --file sql/monitoring/alert_procedure.sql
python -m hospital.live sql --file sql/monitoring/seed_demo_scenarios.sql
python -m hospital.live sql --file sql/monitoring/detect_alerts.sql
```
Query freshness for SYNTHETIC_STALE: age about 180 > threshold 60. Query ALERT_EVENTS WHERE ALERT_TYPE='STALE'. Read last load, age, threshold, action and recipient aloud. Screenshot stale_alert.png. If configured, execute/resume STALE_DATA_ALERT and capture ALERT_HISTORY; otherwise state SQL detection/persistence channel and do not claim scheduled firing/email.

14:00–20:00 genuine controlled failure:
```powershell
python -m hospital.live fail
python -m hospital.live sql --file sql/monitoring/detect_alerts.sql
```
Expected first command nonzero, actual divide-by-zero query in history, failed UUID in run log and failure event. Query failure tile and ALERT_EVENTS WHERE ALERT_TYPE='FAILURE'. Distinguish seeded SYNTHETIC_FAILURE_1 from genuine UUID. Screenshot failure_alert.png plus query history. Repeat detection; incident count should not double. Recover with python -m hospital.live load; freshness advances but historical failure remains. If alerts enabled, capture actual action success and suspend at end.

20:00–25:00 lineage:
```powershell
dbt docs generate --project-dir dbt --profiles-dir dbt
dbt docs serve --project-dir dbt --port 8080
```
Open graph separately for fct_admissions and dim_patients, expand all upstream dbt nodes. Capture lineage_fct_admissions.png and lineage_dim_patients.png. Show Bronze source_file manifest and MERGE query ID for pre-dbt hops. Run lineage.sql if available and explain metadata latency/gaps; do not fabricate an upstream node or screenshot.

25:00–32:00 benchmark first:
```powershell
python -m hospital.benchmark --experiment rewrite --repeats 3 --out artifacts/measurements.json
```
The runner measures before for ALL three workloads and persists before changing query text. During rehearsal retain baseline screenshot/history; during recording show the file/query timestamps proving order. Inspect three before medians, rank slowest and show query profile for it. Then show after pairs and hashes. No data generation/model writes during measurements.

32:00–38:00 warehouse sizing (only explicitly budget-approved):
```powershell
python -m hospital.benchmark --experiment warehouse --size SMALL --allow-paid --repeats 3 --out artifacts/measurements.json
```
Show original/changed/restored size and same logical SQL. Explain speed versus credits/idle billing. If approval is absent, stop this paid segment and mark it pending; never imply it ran. Query history and metering are evidence, not an assumed cost ratio.

38:00–43:00 layout:
```powershell
python -m hospital.benchmark --experiment layout --profile-reviewed --repeats 3 --out artifacts/measurements.json
```
Requires >=100k fact rows and reviewed profile. Show original/copy table scan pruning. The copy is ordered by admit_date and dropped afterward. Explain why clustering may be unhelpful for this dataset; preserve an unchanged/slower result honestly. If insufficient scale, regenerate benchmark BEFORE starting the entire benchmark session, not between pairs.

43:00–48:00 cost/report:
```powershell
python -m hospital.cost_refresh --input artifacts/measurements.json
python -m hospital.core report --input artifacts/measurements.json --out artifacts/report
```
If attribution not yet available/authorized, report N/A and save warehouse metering separately. Open report table and runtime.svg, explain signed percentage, each experiment and 30% criterion. Show PASS only if real comparable values meet it; otherwise NOT MET/UNVERIFIED and plan another measured attempt.

48:00–50:00 cleanup and student exercise: suspend alerts, verify warehouse restored and BENCH_ADMISSIONS absent, preserve files. Student diagnoses one stale dataset, proves both detection paths and explains the largest measured optimization. Assign screenshots above, actual measurements JSON, query histories, signed contribution and exact phase9_report.pdf/phase9_code.zip.

Troubleshooting: no dashboard rows -> successful live load/build and views after Gold; stale seeded row absent -> rerun relative-time seed; failure not logged -> connection failed before SQL, fix authentication; alert no action -> inspect privileges/history/suspension; history empty -> retry within retention, do not substitute invented numbers; no speedup -> profile scans/queue/cache and use benchmark scale; layout cleanup on forced termination -> drop only GOLD.BENCH_ADMISSIONS; cost unavailable -> leave NULL. Every screenshot must come from your account and current run.
