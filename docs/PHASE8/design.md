# Transformation design and test catalog

stg_admissions and stg_patients use source() and expose typed Silver columns. int_patient_history computes source-effective non-overlapping periods and a stable MD5 surrogate key from patient ID and effective timestamp. int_admissions assigns the historical patient key at admission date. Gold grain is one admission and one patient/version.

Both Gold models use incremental MERGE over current source state. The fact deliberately re-merges keys rather than filtering by admit_date: an old admission can receive a new CDC correction. The dimension also re-merges all history so previous current rows close when a later version arrives. Source deletions are unsupported; a reviewed full backfill design is necessary to remove obsolete rows.

patient_snapshot is an additional true dbt timestamp snapshot of the latest observed patient. Run at two snapshot_as_of cutoffs to demonstrate actual snapshot history. The Gold dimension reconstructs already-existing source history, while the snapshot demonstrates ongoing observation; their effective dates need not be identical.

Contracts enforce exact fact and dimension column names and types. break_contract casts bill_amount to VARCHAR while the contract requires NUMBER(18,2). It must fail live before claiming contract evidence.

| Model | Column/test | Type | Risk |
|---|---|---|---|
| fct_admissions | admission_id unique/not_null | schema | duplicate/missing admissions |
| fct_admissions | patient_key not_null + relationship dim_patients | schema | orphan/historically unresolved patients |
| fct_admissions | patient_id not_null | schema | missing natural key |
| dim_patients | patient_key unique/not_null | schema | duplicate versions |
| dim_patients | patient_id not_null | schema | anonymous history |
| fct_admissions | nonnegative_stay | custom | discharge precedes admission |
| fct_admissions | nonnegative_billing | custom | negative charges |
| dim_patients | no_history_overlap | custom | exactly one current patient row |

The current-row custom test checks current cardinality; source-effective intervals are constructed with LEAD and tested locally for contiguous boundaries. Extend to same-day timestamp grain before accepting intraday patient changes.

Lineage: dbt docs generate and dbt docs serve --port 8080; capture one actual graph per Gold table. Silver source descriptions and ingestion query history bridge the dbt graph to Bronze and source manifests.

Reconciliation SQL compares all columns of both Gold objects in both directions to independent, labelled synthetic batch views. Real Phase 5 tables and Phase 2 ERD were not supplied. Replace the comparison sources and match the existing star schema before claiming genuine historical project parity.
