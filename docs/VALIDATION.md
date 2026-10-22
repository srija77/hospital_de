# Validation and remaining acceptance gates

Validated locally on Windows / Python 3.13.3 with stable dbt-core 1.12.6 and dbt-snowflake 1.12.3. GitHub's Ubuntu/Python 3.12 jobs are supplied but not executed here. Run python -m hospital.verify to reproduce all local checks and generate logs under artifacts/validation/.

| Check | Executed result | Scope |
|---|---|---|
| Unit/structural/operational tests | 22 passed, 5 live tests skipped (27 discovered) | Reproducibility, replay/order/quarantine, history, freshness, duration, alerts, percentages, missing/zero values, report fixtures, migration checksum rejection, ZIP/PDF packaging, workflow/asset checks |
| dbt parse DEV and PROD | Passed without credentials | Model/snapshot/test graph and configuration, not live SQL/data tests |
| Snowflake-dialect local SQL parser | 26 files / 160 statements, zero parse errors | Six files contain unsupported-command fallbacks; no claim of live compilation |
| Python compileall | Passed | hospital/, tests/, scripts/ syntax |
| Dependency compatibility | pip check passed | Installed local environment |
| Demo generation/reference pipeline | Passed | 120 patient versions; 1,000 admissions; 2,191 events; 20 invalid; 171 duplicate valid events; 1,000 superseded versions; 1,000 winners |
| Larger reference CDC smoke | Passed | 20,000 natural patients / 24,068 versions; 100,000 admissions; 222,094 events; 2,083 quarantined; all 100,000 winners at version 2. In-memory local check, not a Snowflake benchmark |
| Example report and chart | Generated | SYNTHETIC_EXAMPLE; NOT a measured performance result |
| Architecture/role/ingestion diagrams | Rendered SVG and PNG | Authored diagrams, not execution evidence |
| Exact-name draft packages | Four PDF/ZIP pairs generated | DRAFT PDFs with no fabricated screenshots/signatures |
| PDF traceability | 52 mapped deliverables; 13 each phase | Real paths checked; live/human evidence pending |
| Secret-pattern checks | Passed for authored source and ZIP allowlist | No private keys/literal password-token patterns found; not a comprehensive secret scanner |

Local parser fallbacks: reset_dev_demo.sql, alert_definitions.sql, environment_setup.sql, masking_policies.sql, user_setup.example.sql and V001__hospital_foundation.sql. Live Snowflake remains authoritative for these commands and every permission/data check.

No Snowflake credentials were configured. No account objects, paid warehouse experiment, clustering, scheduled alert, email or GitHub deployment was executed. No remote repository was supplied/configured, and this workspace initially had no Git metadata. Report unit-test inputs are test fixtures; they are not actual Snowflake measurement evidence.

Remaining manual/live stages:
1. Authorized Snowflake bootstrap, native masking/tag entitlement, separate key-pair identities and recursive grants/PUBLIC review.
2. DEV migrate/load/build, five opt-in integration tests, real snapshot two-observation proof, contract failure/correction, actual dbt docs lineage and synthetic-baseline reconciliation. Replace baseline with real Phase 5 when supplied.
3. Current four-section dashboard and both genuine failure/stale detections, scheduled-alert history if used, verified inbox only if external delivery is claimed.
4. Frozen benchmark dataset, baseline-first three workloads, three isolated experiments with explicit budget approval, actual attribution/metering evidence and >=30% runtime improvement in the baseline-slowest workload. This gate is UNVERIFIED, not promised.
5. GitHub remote/main protections/environment approvals/secrets, actual reviewed PR -> merge -> DEV -> approved PROD, release marker and masking/denied-write proof.
6. Full 24-hour stream metrics/restart/reconciliation, real screenshots, signed contributions, teammate runbook drill and timed 15-minute presentation.

Use docs/DELIVERABLE_COVERAGE.md and docs/traceability.csv for acceptance review; final reports must include actual evidence and exact required page order.
