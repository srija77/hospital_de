# Reference review and acceptance decisions

Native streaming update: hospital.streaming and the native Stream/Task SQL now implement direct Snowpipe Streaming into the shared Bronze table. The earlier staged-equivalent limitation below describes the retained legacy path. Use PHASE7/native_streaming.md for the primary native demonstration and 24-hour campaign; live acceptance evidence is still pending.

Read all four PDFs and four interactive guides from C:\Users\Bharani Kumar\Downloads\Phase 7 to 10.zip before completing implementation. Originals and extracted text are in references/. Each PDF is one page. PDF requirements take precedence over abbreviated guide lists.

Mandatory exact paired submission names: phase7_report.pdf/phase7_code.zip, phase8_report.pdf/phase8_code.zip, phase9_report.pdf/phase9_code.zip, phase10_report.pdf/phase10_code.zip. Package aliases preserve producer/, bronze_ingest/, silver_merge.sql, dbt_project/snapshots/, monitoring_queries.sql, alerts/, optimization_scripts.sql, grants.sql and masking_policies.sql as listed in the PDFs.

Phase 7: real 24-hour charts with p50/p95 and events/minute, restart proof and complete count explanation are outstanding live gates. Manual staged PUT/COPY with immutable files is the prompt-authorized Snowpipe equivalent; it is scheduled by the producer loop, not native Snowpipe auto-ingest. Obtain mentor acceptance if native Snowpipe is mandatory for the cohort.

Phase 8: a real timestamp snapshot is supplied in addition to source-effective SCD2 history. Source history reconstructs pre-existing versions; snapshot records observed changes across two runs. All Gold columns are compared bidirectionally with clearly labelled synthetic baselines because real Phase 5/Phase 2 artifacts are absent. No claim of genuine Phase 5 parity is made.

Phase 9: PDF says runtime improvement >=30%; guide allows runtime or cost. Use stricter runtime gate. Record three workloads before changes, rank actual medians to identify the slowest, and do not claim a passing gate from synthetic examples. Query rewriting, warehouse sizing and sorted physical-layout copy are separate experiments; clustering is conditional on larger data and Query Profile evidence. Prompt permits alternate layout/query optimization if clustering is not useful.

Phase 10: no ordinary manual production writes, including incident fixes. Bootstrap/grant administration is separately privileged and audited. Forward corrective migrations go through PR and protected deployment. Signed contribution, actual masks/denials, PR/merge/deploy screenshots, teammate runbook test and timed demo are human/live gates, not locally certified.

docs/traceability.csv enumerates all 13 deliverables per PDF and paths, checks and evidence to collect. Report templates follow exact PDF page order. No screenshot or signature is generated as execution proof.
