# Native streaming: exact setup, demonstration and recovery

The primary event path is now:

```text
Python synthetic event source -> Snowpipe Streaming SDK named channel
    -> BRONZE.ADMISSION_EVENTS -> Snowflake Stream -> one-minute Task
    -> version-aware Silver MERGE -> scheduled dbt build -> Gold
```

Python sends individual rows through the native API. JSONL stays on the producer host only as retained replay source; it is not PUT to a stage in this mode. The PIPE definition uses COPY syntax with DATA_SOURCE(TYPE=>'STREAMING'), not staged-file COPY execution. Native ingestion buffers internally, so row visibility is asynchronous and actual latency must be measured. Silver updates approximately once per scheduled minute when changes exist. Gold updates on the separate dbt refresh interval. This is continuous row ingestion with incremental downstream processing, not a promise that every layer changes instantly.

The same patient records, admission IDs, versions, duplicate events and invalid examples from the shared generator are used. Batch bootstrap loads patients, admission snapshots and example metadata only. Native events land in the existing Bronze table and feed the existing dbt models; no unrelated dataset is created.

## 1. Local replay demonstration: no credentials

Activate the project venv, then:

```powershell
python -m pip install -r requirements.txt
python -m hospital.core generate --profile demo --out data/demo
python -m hospital.streaming --source data/demo --out data/native-local --max-events 20 --interval-seconds 0
python -m hospital.streaming --source data/demo --out data/native-local --max-events 20 --interval-seconds 0
```

Expected: first run committed_offset=19; second run=39, with 40 unique source offsets in local_rows.jsonl. Use a new output directory for a fresh exercise. Output explicitly says LOCAL_SIMULATOR, not live Snowflake evidence. The simulator tests source order/checkpoints; it does not simulate Snowflake networking, service durability or SQL compilation.

## 2. Live prerequisites

- Existing administrator bootstrap and HOSPITAL_DEV migrations, supported Snowpipe Streaming account/network connectivity and the installed snowpipe-streaming 1.9.0 SDK.
- DEV user with DE_ENGINEER, separate from PROD credentials. Keep its private key outside the repository.
- Existing SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER and SNOWFLAKE_PRIVATE_KEY_PATH environment variables. Add SNOWFLAKE_URL with your account connection endpoint, e.g. https://organization-account.snowflakecomputing.com. Use the connection endpoint supplied by Snowflake, not app.snowflake.com.
- Authorized account administrator executes sql/security/native_streaming_privileges.sql to grant EXECUTE TASK to DE_ENGINEER. The DEV role already owns its database/schemas and has warehouse USAGE. The pipe owner can ingest; analysts receive no new privileges.
- Explicitly approved live ingestion/compute budget before starting the producer, resuming a task or starting the dbt refresh loop. No paid service is started by local validation.

## 3. Prepare one initially-empty DEV campaign

Preserve earlier demo evidence first. A fresh dataset is important: loading a full fixture's events and then streaming them again would intentionally duplicate physical Bronze rows. The task's source cursor also must not be reset during a campaign.

If no native task/CDC stream exists yet:

```powershell
python -m hospital.live migrate
python -m hospital.live sql --file sql/ingestion/reset_dev_demo.sql
python -m hospital.core generate --profile demo --out data/native-source
python -m hospital.live load --data data/native-source --skip-events
python -m hospital.dbt_run build
python -m hospital.live sql --file sql/monitoring/monitoring_queries.sql
python -m hospital.live sql --file sql/ingestion/native_streaming_setup.sql
python -m hospital.live sql --file sql/ingestion/native_streaming_task.sql
```

Expected before streaming: Bronze events=0, Silver admissions=0, Gold fact=0; the patient dimension has 120 historical rows. The default snapshot is also initialized. SQL native setup adds SOURCE_PUBLISHED_AT metadata to Bronze; it does not modify the original event fields in RAW. CREATE PIPE/STREAM/TASK scripts are DEV-specific, opt-in setup, not automatically applied to PROD migrations.

For a NEW campaign after previous native streaming, first stop both producer and Gold loop, preserve evidence and use Snowsight:

```sql
USE ROLE DE_ENGINEER;
USE DATABASE HOSPITAL_DEV;
ALTER TASK SILVER.PROCESS_ADMISSION_EVENTS SUSPEND;
DROP STREAM IF EXISTS BRONZE.ADMISSION_EVENTS_CDC;
```

Only then use the explicit DEV reset and setup commands above, with a new producer output directory. The reset rejects an existing native CDC stream to prevent accidental loss of checkpoint meaning. Keep old named channels/pipe and source evidence for retention review; never drop/recreate them to repair an active campaign.

## 4. Start live streaming and downstream refresh

After task execution privilege and budget approval, resume Silver in Snowsight:

```sql
USE ROLE DE_ENGINEER;
USE DATABASE HOSPITAL_DEV;
ALTER TASK SILVER.PROCESS_ADMISSION_EVENTS RESUME;
```

Terminal 1, activated venv with DEV credentials:

```powershell
python -m hospital.streaming --live --source data/native-source --out data/native-live --interval-seconds 1 --commit-every 10 --minutes 10
```

Terminal 2, optional automated DEV Gold refresh (also uses warehouse compute):

```powershell
python -m hospital.transform_loop --live --minutes 10 --interval-seconds 60
```

Terminal 3 / Snowsight: execute sql/monitoring/native_streaming_queries.sql and refresh the four monitoring dashboard queries. The task writes actual successful/failed run records and advances Silver/actual Bronze freshness as part of processing. Initial Gold may be empty; the next successful dbt refresh updates it after Silver catches up. A dbt failure stops the refresh loop and is logged by the existing wrapper.

The source is finite: it stops cleanly on exhaustion instead of silently replaying old events. --minutes and --max-events cap each invocation. The configured row interval is a target maximum rate; network/commit waits can reduce throughput. commit_every controls confirmation/checkpoint cadence, not file batches. The SDK receives append_row for each event.

Expected observations: native Bronze count grows; committed offsets appear in the producer; Silver maintains one row/admission; invalid events remain in quarantine; lower versions cannot overwrite newer ones; Gold catches up on dbt refresh. After the entire source finishes, all 2,191 events should reconcile to 1,000 Silver/Gold admissions, with the previously documented invalid/duplicate/superseded bridge. During a partial source run, not every admission's winning version may have arrived, so final baseline reconciliation is not yet expected.

## 5. Restart without loss

Stop Terminal 1 with Ctrl+C, save current stream_state.json and commits.jsonl, then rerun the SAME command with the SAME --source and --out. The named channel is derived from the persistent stream_id.

Recovery reads Snowflake's latest committed offset and resumes at the next source record. A remote offset ahead of the local checkpoint is handled: a crash may occur after Snowflake commit but before local checkpoint write. A remote offset behind a previously confirmed local checkpoint fails closed because the channel may have been deleted/reset. Source hashes and mode changes also fail closed. A process lock prevents two local writers to the same channel. Do not copy an active state directory to another producer host.

The SDK may buffer rows before they commit. The application waits for a confirmed token and checks rejected-row counts before writing a checkpoint. Exactly-once restart behavior is conditional on retained unmodified source, stable channel/pipe identity, account retention and a single writer. It does not remove business duplicate events with different source offsets; Silver handles those.

## 6. Latency, errors and evidence

LOADED_AT is server-side pipe processing time; SOURCE_PUBLISHED_AT is the sender attempt timestamp. Native monitoring SQL calculates p50/p95 send-to-server-processing latency and events per minute. Synchronize producer clocks and document skew. RAW event_time preserves synthetic historical lateness and is not transport latency. commits.jsonl records actual wait durations for commit confirmation, separately from server-processing timing; it is not a claim of per-row query-visibility latency.

Task MERGE, cursor consumption and Silver telemetry commit together in one transaction. If processing fails, the transaction rolls back, the failure is logged and the stream remains available for retry. Check TASK_HISTORY, MONITORING.PIPELINE_RUN_LOG, QUARANTINED_EVENTS and SDK channel status. Rejected ingestion rows cause a nonzero producer exit; investigate Snowflake streaming error details and source rows before restarting. Do not suppress errors or advance a local checkpoint manually.

Screenshot actual SDK progress/server token, growing Bronze, task runs, version-2 winner for admission 1, INVALID2 quarantine, restart offsets, four dashboard tiles and actual Gold catch-up. Local simulator output is never a substitute for this evidence.

## 7. Full 24-hour campaign

Complete the short live rehearsal first. Then prepare a fresh campaign using the reset protocol, generate enough source and bootstrap with --skip-events:

```powershell
python -m hospital.core generate --profile demo --patients 500 --admissions 50000 --out data/native24-source
python -m hospital.live load --data data/native24-source --skip-events
```

Recreate the CDC cursor/setup as above, resume the approved task and run:

```powershell
python -m hospital.streaming --live --source data/native24-source --out data/native24 --interval-seconds 1 --commit-every 10 --minutes 1440
```

This produces over 100,000 retained events, enough for a 24-hour campaign at at most one row/second. Keep the host awake. Plan a recorded stop/restart with the same source/channel and remaining minutes; account for actual downtime. Export native minute metrics, offsets, task logs, source manifests and hourly counts across the entire real period. At 24 hours the source may not be exhausted, especially after commit waits, so compare Bronze against the confirmed SOURCE_FILE offset prefix rather than the entire source. To compare the full batch baseline, drain the remaining source, allow Silver to consume pending changes, then run dbt build and both-direction reconciliation.

The older hospital.stream_report consumes legacy micro-batch producer logs; do not use it for native offset evidence. Use native_streaming_queries.sql CSV exports, commits.jsonl and actual screenshots for this mode. No full 24-hour native evidence has yet been collected.

## 8. Instructor recording, 20 minutes plus separate 24-hour evidence

00:00–03:00 explain SDK row ingestion, retained replay source, Snowflake Stream cursor, one-minute Task and dbt refresh. Open the updated architecture PNG.

03:00–06:00 show prepared empty DEV events/patient dimension, explicit pipe/CDC/task setup and suspended task. Explain permissions and approved compute, then resume task.

06:00–10:00 start the producer and optional Gold loop with commands above. Show offsets every 10 rows and query growing Bronze/task history/Silver. No staged files are used for event transport.

10:00–14:00 stop/restart the same producer output. Show previous and next committed offsets, unchanged source hash, duplicate/late handling and quarantine. Explain why channel deletion is not recovery.

14:00–17:00 show actual latency/freshness/count/failure/runtime queries and Gold catch-up. Describe failure handling and demonstrate the existing controlled failure lab separately when needed.

17:00–20:00 suspend the task after stopping producer/Gold loop, preserve evidence and explain the separate real 24-hour campaign. Student exercise: recover after a simulated commit timeout locally, then prove a server-ahead checkpoint resume in the test suite. Do not claim live fault/restart proof from mocks.

## Official API references

- [Named-channel SDK tutorial](https://docs.snowflake.com/en/user-guide/snowpipe-streaming/snowpipe-streaming-high-performance-getting-started)
- [Python channel append, commit and offset API](https://docs.snowflake.com/en/user-guide/snowpipe-streaming-sdk-python/reference/latest/api/snowflake/ingest/streaming/streaming_ingest_channel/index)
- [Streaming pipe transformations](https://docs.snowflake.com/en/sql-reference/sql/create-pipe)

Implemented and tested locally. Native Snowflake connectivity, pipe/task SQL compilation, measured latency and full-run evidence remain unverified until the account and approved budget are supplied.
