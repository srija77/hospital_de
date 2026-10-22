# Hospital admissions: Snowflake capstone, Phases 7–10

One deterministic hospital dataset feeds Bronze, version-aware Silver, dbt history and Gold, monitoring, benchmarks and protected deployment. Phase 9 and 10 are the main teaching modules.

Native row streaming is now implemented with Snowpipe Streaming named channels. See [native streaming setup and demonstration](docs/PHASE7/native_streaming.md). Python sends events directly to the existing Bronze table; a Snowflake Stream/Task maintains Silver; an optional DEV dbt refresh loop updates Gold. The older staged micro-batch producer remains a separate batch teaching option.

**Short standalone demo:** [governance_demo/](governance_demo/README.md) covers data governance, privacy, CI/CD and monitoring on one patients table.

Start with [setup](docs/SETUP.md), [dataset scenarios](docs/DATA_SCENARIOS.md), [acceptance traceability](docs/traceability.csv) and [validation status](docs/VALIDATION.md). All eight supplied references are retained in references/. The deliverable PDFs are authoritative when the interactive guides differ.

Quick local run (Python 3.12/3.13; no Snowflake):
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m hospital.core generate --profile demo
python -m hospital.core local-demo
python -m unittest discover -s tests -v
python -m hospital.validate
Copy-Item dbt/profiles.example.yml dbt/profiles.yml
dbt parse --project-dir dbt --profiles-dir dbt --target dev --no-partial-parse
python -m hospital.core report --input examples/benchmarks_synthetic.json --out artifacts/example-report
```

The example chart is marked SYNTHETIC_EXAMPLE and is not a measured benchmark. Runtime/scan/cost fields in generated benchmark metadata stay null. Local dashboard JSON is a reference calculation at the fixed fixture clock; live dashboard SQL uses CURRENT_TIMESTAMP.

Run python -m hospital.verify for the complete local verification, both dbt targets, rendered diagrams and all four draft report/code pairs. Logs and exit codes are saved under artifacts/validation/. Draft packages are under artifacts/submissions/draft/.

Live sequence after administrator bootstrap and environment credentials:
The commands below demonstrate the batch foundation. For native streaming, bootstrap with load --skip-events and follow native_streaming.md so events are not preloaded twice.
```powershell
python -m hospital.live migrate
python -m hospital.live load --data data/demo
python -m hospital.dbt_run build
python -m hospital.live sql --file sql/monitoring/monitoring_queries.sql
python -m hospital.live sql --file sql/monitoring/alert_procedure.sql
python -m hospital.live sql --file sql/monitoring/seed_demo_scenarios.sql
python -m hospital.live sql --file sql/monitoring/detect_alerts.sql
python -m hospital.live sql --file sql/ingestion/reconcile_phase5.sql
python -m hospital.benchmark --experiment rewrite
python -m hospital.core report --input artifacts/measurements.json
```

Recordings: docs/PHASE7/recording_script.md, docs/PHASE8/recording_script.md, docs/PHASE9/recording_script.md, docs/PHASE10/recording_script.md. Each has commands, expected observations, recovery and screenshot assignments.

The implementation uses a deliberately small checksum migration runner instead of schemachange: append-only VNNN scripts, checksum verification and Snowflake deployment history. GitHub concurrency serializes deployments; migrations must be restart-safe because Snowflake DDL is not transactional.

PROD changes run only in the protected main workflow. Setup/security grants are privileged bootstrap activities, not the normal production change path. Separate users and keys are required. No account deployment, external notification, 24-hour proof or 30% improvement is claimed by local checks. Exact submissions are phase7_report.pdf + phase7_code.zip through phase10_report.pdf + phase10_code.zip; use hospital.package after collecting actual evidence.
