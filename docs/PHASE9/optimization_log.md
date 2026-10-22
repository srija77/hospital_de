# Optimization experiment log

Preflight: freeze generated benchmark fixture; stop streaming and model writes. Generate benchmark profile, migrate/load/build in DEV. Use a dedicated warehouse and record its original size. Inspect Query Profile and save baseline artifact. The runner measures three workloads before any experiment change and flushes baseline to disk before applying that change.

To move from the demo profile to benchmark scale, preserve earlier evidence and intentionally reset the synthetic DEV data first. Different generation profiles/seeds can change payloads under the same event IDs, so do not mix profiles in existing Silver state. Exact preparation (the reset deletes teaching DEV data and is context-guarded):

```powershell
python -m hospital.live sql --file sql/ingestion/reset_dev_demo.sql
python -m hospital.core generate --profile benchmark --out data/benchmark
python -m hospital.live load --data data/benchmark
python -m hospital.dbt_run build
```

Use a fresh measurements JSON path after changing profiles. Never use the reset for PROD or during a running benchmark. The reset retains monitoring history and policies/grants, but clears target load metadata so immutable files can be loaded again. Snapshot observation history is retained; snapshot_demo uses a unique alias when new evidence is needed.

1. Query rewrite: python -m hospital.benchmark --experiment rewrite --repeats 3. Before converts dates to strings for a year-prefix filter and uses broad projection in the join; after uses typed range predicates and narrow filtered inputs. The former can obstruct date pruning; Query Profile must establish actual scan differences. Snowflake may make these equally efficient; no gain promised. Rollback is selecting the original query; no objects change.
2. Warehouse: after budget owner explicitly approves, grant OPERATE/MODIFY only on the dedicated DEV warehouse as needed, then python -m hospital.benchmark --experiment warehouse --size SMALL --allow-paid --repeats 3. Before and after use identical original SQL; only warehouse size changes. Runner restores original size in finally. If killed forcefully, authorized operator restores captured original size. Capture resize, metering intervals and attribution after latency; minimum billing/idle can outweigh runtime savings.
3. Physical layout: only after larger fixture and Query Profile pruning review, python -m hospital.benchmark --experiment layout --profile-reviewed --repeats 3. Count guard requires >=100,000 admissions. Original SQL stays identical except table identifier. After reads a transient sorted CTAS copy ordered by admit_date, a prompt-permitted layout alternative. Runner drops the copy in finally. CTAS setup time/credits must be documented separately from query cost. An original size threshold alone is not evidence clustering helps.

Optional actual clustering: on a separately budget-approved benchmark copy, record SYSTEM$CLUSTERING_INFORMATION before/after and profile partition pruning; apply CLUSTER BY only if appropriate. Automatic clustering can incur cost and might not reorganize small data promptly. Record maintenance credits and stop/drop the copy. Do not cluster production automatically.

Use sql/optimization/optimization_scripts.sql as the ordered change/rollback reference. To repeat pairs, use a fresh --out path per frozen dataset/session; do not mix artifacts from different data volumes or warehouse cache policies. Default is three repeats, result cache disabled, identical warm-up each variant, warehouse cache uncontrolled and recorded. Check the saved result_hash values; inequality aborts the experiment. Review compilation/queue time in query history separately.

Cost refresh: python -m hospital.cost_refresh --input artifacts/measurements.json after ACCOUNT_USAGE attribution appears. If permission is denied, keep credits NULL and use cost_evidence.sql through an authorized monitoring reader; do not distribute broad ACCOUNT_USAGE grants merely for the lab.

Record each attempt:
| Timestamp | Experiment | Baseline query IDs | Changed variable/command | Result IDs | Runtime/scan/cost conclusion | Rollback verified |
|---|---|---|---|---|---|---|
| [fill from execution] | [fill] | [fill] | [fill] | [fill] | [fill] | [fill] |

At least three real experiments and a >=30% gain remain live acceptance gates. A failed optimization is useful evidence but does not waive the PDF performance gate.
