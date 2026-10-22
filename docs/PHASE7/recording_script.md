# Phase 7 instructor recording, 25 minutes plus separate 24-hour run

For the current native streaming lab, use the complete recording sequence in native_streaming.md. This file preserves the earlier staged-file micro-batch alternative. scripts/stream_producer.py now invokes native streaming; python -m hospital.producer continues to invoke the legacy file loader.

Prerequisites: completed SETUP, DEV credentials, activated venv, empty dedicated teaching dataset or documented prior batch IDs. Do not combine an existing benchmark fixture with fresh stream IDs without resetting the teaching DEV environment.

00:00–03:00 explain same batch and micro-batch layers; open design.md and DATA_SCENARIOS.md. Show E0000001V2 twice, late E0000001V1 and INVALID2 using data/demo/admission_events.json. Explain that source event version supersedes arrival order.

03:00–07:00 run:
```powershell
python -m hospital.core generate --profile demo
python -m hospital.live migrate
python -m hospital.live load
python -m hospital.live load
```
Expected: two successful run UUIDs, same Silver count 1,000; second COPY skips already-loaded files. Screenshot COPY/query history and Silver count. Bronze exceeds 2,000 because duplicate/invalid events are retained.

07:00–12:00 open sql/ingestion/silver.sql. Query SILVER.ADMISSIONS WHERE ADMISSION_ID=1 (version 2) and QUARANTINED_EVENTS WHERE ADMISSION_ID=2 (negative-bill record). Execute reconciliation.sql; show source count 1,000 and unique Silver count 1,000, then explain each Bronze difference. Run python -m unittest discover -s tests -v for replay/order reference checks.

12:00–17:00 separate live micro-batch setup, preserving same table architecture. Use an initially empty teaching environment to reconcile physical counts:
```powershell
python -m hospital.producer --live --minutes 3 --interval-seconds 10 --admissions-per-batch 10 --out data/stream-demo
```
Use a second terminal to query COUNT(*) FROM BRONZE.ADMISSION_EVENTS while it grows. Stop with Ctrl+C between batches, inspect checkpoint.json and restart with the same --out. Screenshot before/after and logs. This is ONLY a short recovery demo.

Before the first streaming command above, export the earlier batch evidence and deliberately run python -m hospital.live sql --file sql/ingestion/reset_dev_demo.sql to obtain the required initially-empty teaching DEV state. Do not reset between a stop/restart. After the short producer finishes, run python -m hospital.dbt_run build and then reconciliation.sql so Gold reflects the streamed batches.

17:00–22:00 open stream_metrics.sql and execute; explain event versus transport latency, p50/p95, and minute throughput. Screenshot actual query output. Never reuse these few minutes as the 24-hour submission.

22:00–25:00 explain full-run procedure below, reconciliation and student exercise: replay a lower version then higher version and prove no duplicate admission keys.

Full 24-hour run: use dedicated DEV, initial schemas, patients and same pipeline; run python -m hospital.producer --live --minutes 1440 --interval-seconds 60 --admissions-per-batch 100 --out data/stream24. Keep the host awake and retain terminal logs. At a planned hour stop/restart using same output directory and remaining minutes; record exact restart times. Do not delete checkpoints or claim uninterrupted processing during downtime. Collect producer_runs.jsonl, checkpoint, manifests, COPY history, hourly Bronze counts, restart timestamps and actual SQL metrics. Run python -m hospital.stream_report --stream data/stream24 --out artifacts/stream24 after the full elapsed period. The script saves measured CSV and chart, and reports whether elapsed coverage reaches 24 hours; it does not manufacture missing minutes. Explain any gap/spike and reconcile unique batch manifests to Bronze.

Before starting a new 24-hour campaign, preserve previous evidence and run the explicit DEV reset once; use a new --out directory. At completion run dbt build and both reconciliation SQL scripts. Do not reset or change output directory during the planned restart. Source total equals the sum of unique batch sent_records, not duplicate retry log lines. A clean context is essential because these teaching campaigns reuse admission IDs beginning at 1.

Troubleshooting: authentication/role errors -> check DE_ENGINEER and key outside repo; COPY zero rows on retry is expected; missing batch -> preserve file and retry; old state -> inspect precedence/quarantine; Bronze count mismatch -> compare filenames, checksums and load history. Screenshot tasks: Bronze growth, version winner, quarantine, restart recovery, full 24-hour chart and reconciliation. Student delivers signed contribution and exact phase7_report.pdf / phase7_code.zip.
