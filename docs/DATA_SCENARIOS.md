# Shared synthetic data and exact demonstration records

Fixed seed 42, clock 2026-01-15 12:00 UTC. Demo: 100 patients/1,000 admissions. Benchmark: 100,000 patients/500,000 admissions; generation uses memory proportional to events, so use a machine with several GB RAM or select explicit --admissions/--patients. The mandatory layout guard requires >=100,000 admissions. Changing size alone does not guarantee meaningful performance differences.

Verified demo counts: 120 patient-version rows, 1,000 batch admissions, 2,191 physical event rows, 20 invalid events, 171 exact valid-event duplicates and 1,000 distinct superseded versions. Count bridge: 2,191 = 20 + 171 + 1,000 + 1,000 current admissions. Gold count in the local demo is a reference prediction; live Gold must be checked separately.

Patients: seven requested fields, fake names, example.invalid email domains, 555 phone numbers. Patient 1 always has Chennai and Bengaluru versions at anchor minus 800 days and minus 15 days. Its name/email/phone/DOB remain Patient 000001, p1@example.invalid, 5550000001 and 1951-01-01. Use patient_id=1 for history and two-role masking evidence.

Admissions: all ten requested fields. Each source admission represents the final version-2 batch state. admission_id=1 always belongs to patient 1. Both source and winning event payload have matching final updated_at. Gold fact grain is one row/admission; dimension grain is one patient/version. Actual earlier Phase 2/5 models were not supplied; names/grain must be reconciled with those artifacts before claiming historical project acceptance.

Events: all eight requested fields. E0000001V2 is duplicated exactly; E0000001V1 arrives logically two hours late, after version 2. INVALID2 has version 3 and bill_amount=-100 and is quarantined. Ordering is version, event_time, event_id; ingest time never supersedes event precedence. Same-version conflicting payloads with the same event_id are outside the generator contract and must be quarantined by an added source integrity rule before extending this lab. Event type UPSERT represents the current admission state; DELETE semantics are not implemented.

Rates are configurable (--duplicate-rate, --late-rate, --invalid-rate, --patient-update-rate). Guaranteed anchor cases remain even at rate 0; rates govern additional random cases. --no-failures suppresses synthetic failure logs. All generated files have deterministic manifests. The streaming producer uses the same schema and patients, offsets admission IDs by micro-batch and stamps actual send time.

Keep one fixture seed/profile per retained state. To switch size or seed, preserve evidence and use the explicitly guarded synthetic DEV reset in PHASE9/optimization_log.md. Same-ID payload changes at identical version/time are not corrections; corrections must increase source version. Streaming starts in a dedicated initially-empty DEV dataset and must not collide with an existing demo or benchmark fixture.

Pipeline logs: SYNTHETIC_SUCCESS_1 and SYNTHETIC_FAILURE_1 are interface fixtures, not actual executions. Live load and dbt_run produce UUID run records from real execution timestamps. python -m hospital.live fail causes a genuine Snowflake divide-by-zero and records its error code before returning nonzero.

Freshness: fixed-clock SYNTHETIC_FRESH (5 minutes), SYNTHETIC_STALE (180) and SYNTHETIC_FAILED (240). For live recording seed_demo_scenarios.sql resets clearly named examples relative to execution; actual Bronze/Silver/Gold load markers use real successful completion timestamps. A failed load does not advance successful freshness.

Quality results: check 1 PASS and check 2 FAIL are labelled fixtures. Actual dbt tests are captured in run_results.json; they must be retained as evidence. Source negative bills are excluded before Gold. The contract failure uses --vars '{"break_contract": true}' to cast the fact bill to VARCHAR against NUMBER(18,2).

Benchmark metadata generated with the dataset has null execution values and SYNTHETIC_EXAMPLE configuration. examples/benchmarks_synthetic.json has explicitly illustrative UI numbers only. Measured JSON is produced solely by hospital.benchmark, with real query IDs and query history; credits stay null until actual query attribution is available.
