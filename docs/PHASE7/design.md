# Incremental ingestion design

Primary live streaming path: hospital.streaming uses the native Snowpipe Streaming SDK, a stable named channel, retained source JSONL and server-committed offset tokens. Events are sent as rows directly to BRONZE.ADMISSION_EVENTS. A native Snowflake Stream tracks new Bronze rows, and a suspended-by-default one-minute Task calls a transactional version MERGE into Silver. See native_streaming.md for exact setup, recovery, monitoring and 24-hour instructions. Local JSONL files are replay storage, not staged-file ingestion in this mode. Gold refresh is explicitly scheduled dbt, not row-triggered SQL.

The following describes the retained batch/micro-batch alternative. Both paths share the same source contract and Bronze/Silver/Gold objects; do not run overlapping source campaigns together.

Source is the shared hospital generator: immutable JSON arrays contain admission UPSERT state events. Initial load and producer micro-batches use the same stage, Bronze and Silver objects. Bronze stores the unmodified VARIANT plus actual load timestamp and source filename. SQL supports CSV/JSON design through generated CSV files; JSON is the live ingestion format.

Ingestion equivalent: Python uploads content-addressed files with PUT and COPY INTO FORCE=FALSE. This requires no cloud notification configuration. It is a scheduled micro-batch equivalent, not a claim of native continuous Snowpipe. Source manifests, batch directories, local atomic checkpoint.json and Snowflake COPY load history together support recovery. Files must not be mutated. Snowflake load-history deduplication is bounded; do not rely on indefinite history. Silver remains idempotent even when Bronze reloads.

CDC: validate payloads, retain invalid rows in SILVER.QUARANTINED_EVENTS, choose one winner per admission, then MERGE only a strictly newer (event_version,event_time,event_id). Replay rescans retained Bronze for a simple teaching implementation; this is correct but not a production-scale incremental scanner.

| Case | Rule/window | Outcome | Reason |
|---|---|---|---|
| exact duplicate | indefinite within retained Bronze | one Silver admission | state grain differs from event grain |
| late valid higher version | no age cutoff | update | avoid dropping clinical state corrections |
| late lower version | no age cutoff | retain Bronze, no overwrite | version is source authority |
| out of order | compare version/time/id | deterministic winner | arrival time is unreliable |
| invalid record | any time | quarantine view with reason | Gold must remain valid |

Latency is measured separately as event_time -> loaded_at and send/ingest_time -> loaded_at. Synthetic old event times intentionally include lateness and should not be interpreted as transport delays. p50/p95 and events/minute are computed in stream_metrics.sql. Row throughput in run logs is current Silver state per run, not a count of newly ingested records; use stream_metrics for ingestion throughput.

Reconciliation: sent physical event rows match Bronze physical rows after load-history-aware retries. Bronze valid rows minus duplicate/superseded rows match unique Silver keys; invalid count is separate. Silver and Gold admission counts should agree; dim row count can exceed patient count. Both-direction all-column comparisons use synthetic batch baseline, not a missing historical Phase 5 warehouse.

Restart: stop producer, preserve directories/checkpoint, restart with same --out and remaining duration. If crash happens after COPY and before checkpoint, same batch is retried; load history skips files and version MERGE is idempotent. Export COPY_HISTORY and producer log plus unique batch counts after restart.
