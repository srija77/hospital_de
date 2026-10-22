# Phase 8 instructor recording, 30 minutes

Prerequisites: DEV initial fixture loaded; dbt/profiles.yml copied; DE_ENGINEER credentials; no PROD target.

For an already-built or repeated lab, run python -m hospital.snapshot_demo instead of the two manual snapshot commands. It creates a uniquely named DEV snapshot using two real observations, verifies old/new history and prints the exact table to screenshot; existing snapshot history is preserved. This also avoids PowerShell JSON quoting differences.

00:00–05:00 open dbt project, explain source(), ref(), three layers, grain and why old admissions cannot use an admission-date watermark. On a fresh DEV environment run dbt run --project-dir dbt --profiles-dir dbt --select stg_patients to prepare the snapshot source. Reserve the full build until after the two snapshot observations below. A credential-free dbt parse is structural evidence only.

05:00–12:00 first observe patient 1 with a true dbt snapshot on a fresh snapshot table:
```powershell
dbt snapshot --project-dir dbt --profiles-dir dbt --vars '{"snapshot_as_of":"2025-12-30"}'
dbt snapshot --project-dir dbt --profiles-dir dbt --vars '{"snapshot_as_of":"2099-01-01"}'
```
The first command must precede the initial default snapshot run. Do not rewind an existing snapshot. After the two observations run python -m hospital.dbt_run build; expected models/snapshot/tests pass. Now query both GOLD.DIM_PATIENTS and INTERMEDIATE.PATIENT_SNAPSHOT WHERE PATIENT_ID=1 and capture actual old/new rows plus target/run_results.json. Source latest change is 2025-12-31, so the first cutoff observes the old version.

12:00–18:00 deliberate contract failure:
```powershell
dbt run --project-dir dbt --profiles-dir dbt --select fct_admissions --vars '{"break_contract":true}'
dbt build --project-dir dbt --profiles-dir dbt --select fct_admissions
```
PowerShell 5 may strip embedded JSON quotes for native commands; if so put vars in a local YAML file and use its contents, or use the supplied scripts/phase8_demo.ps1. Expected first nonzero contract/type error, second success. Save both logs/screenshots. Do not mark failure intentional if it was actually a connection error.

18:00–23:00 run dbt docs generate --project-dir dbt --profiles-dir dbt; dbt docs serve --project-dir dbt --port 8080. Open graph, expand upstream sources of each Gold object, capture lineage_graph.png. Explain that source-to-Silver history comes from ingestion SQL/query IDs.

23:00–27:00 python -m hospital.live sql --file sql/ingestion/reconcile_phase5.sql. Four differences must be empty for both Gold objects. Label SYNTHETIC teaching baseline in screenshot and report; real Phase 5 remains pending until supplied.

27:00–30:00 student exercise: introduce an orphan patient key locally, explain which test should fail; show incremental rerun leaves admission count unchanged. Troubleshooting: missing sources -> run Phase 7; contract mismatches -> inspect generated schema and casts; null keys -> inspect effective-date windows; snapshot one row -> first cutoff was skipped. Preserve exact phase8_report.pdf/phase8_code.zip names and signed contribution.
