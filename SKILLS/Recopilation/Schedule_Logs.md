# Schedule and Execution Logs

## Purpose

Schedule and execute recurring or manual data-extraction processes. Each
execution must record the date, status, files processed, source snapshot
information, and outcome in an auditable execution history.

This skill coordinates scheduling and logging. It does not transform CSV
data; that work belongs to `Download_CSV`, `Validate_CSV_schema`,
`Validate_Data_Quality`, and later analytical skills.

## Required inputs

Request clarification if any required input is missing:

1. extraction source or endpoint identifier;
2. schedule frequency or one-time execution time;
3. timezone for all scheduled dates;
4. destination for downloaded files;
5. authentication configuration reference;
6. retry limit and timeout;
7. execution-log destination;
8. file retention and overwrite policy;
9. concurrency policy;
10. source snapshot or reporting-period rule, when applicable.

Never invent a schedule, source, credential, destination, or retention rule.
Use only approved source and scheduler configurations.

## Procedure: schedule registration

Register the extraction as an identified job with explicit metadata:

```json
{
  "job_id": "stable-job-identifier",
  "source": "approved source identifier",
  "schedule": "cron or approved scheduler expression",
  "timezone": "America/Mexico_City",
  "enabled": true,
  "timeout_seconds": 3600,
  "max_retries": 3,
  "destination": "approved directory or storage identifier",
  "log_destination": "approved execution-log location",
  "last_run": null,
  "next_run": null
}
```

The scheduler may be cron, a platform scheduler, or an application scheduler.
The configured timezone must remain fixed with the job. Do not execute an
ambiguous local time or silently interpret a DST transition.

Before registration:

1. validate the source and destination;
2. verify authentication availability without reading or logging secrets;
3. confirm the schedule expression and timezone;
4. confirm overlap and retry behavior;
5. initialize the execution-log destination;
6. perform a manual smoke execution when a new job is created.

## Procedure: execution

For every scheduled or manual run:

1. create a unique `execution_id`;
2. record `started_at` before starting work;
3. acquire the configured job lock;
4. determine the source snapshot or reporting period;
5. execute `Download_CSV` or `Fetch_From_Storage`;
6. pass completed files to `Validate_CSV_schema`;
7. pass schema-valid files to `Validate_Data_Quality`;
8. record every file attempted and its final status;
9. set the final execution status;
10. record `completed_at` and `duration_seconds`;
11. schedule or skip retries according to policy.

Use one execution record per run. Do not create a separate top-level record
for each file. Link file outcomes to the same `execution_id`.

## Procedure: Python execution log

Example in-process logging structure:

```python
import uuid
from datetime import datetime, timezone


execution = {
    "execution_id": str(uuid.uuid4()),
    "job_id": "stable-job-identifier",
    "started_at": datetime.now(timezone.utc).isoformat(),
    "completed_at": None,
    "status": "running",
    "scheduled_at": None,
    "trigger": "schedule | manual | retry",
    "files_processed": [],
    "warnings": [],
    "errors": [],
    "snapshot_id": None,
    "refreshed_at": None,
}
```

The example is a schema template, not an instruction to invent values. Fill
each field only from the scheduler, source, or completed operation.

Persist the running state before work starts. Update it only as confirmed
operations complete. A running record must remain visible after a process
crash.

## Execution statuses

Use these status values consistently:

- `running`: the execution is active;
- `success`: every required file completed and validation succeeded;
- `partial`: required work succeeded for some files but at least one failed;
- `failed`: no required file was successfully completed;
- `skipped`: no extraction ran because the policy or precondition prevented it;
- `cancelled`: the execution was stopped before required work completed;
- `unconfirmed`: the service did not provide enough evidence to determine status.

Do not label an execution `success` until required downloads or storage reads,
schema checks, and quality checks have their confirmed statuses.

## File processing log

Record each file independently inside the execution:

```json
{
  "file_name": "source file name",
  "source": "approved source identifier",
  "destination": "approved destination or storage reference",
  "status": "success | partial | failed | skipped | unconfirmed",
  "bytes": 0,
  "sha256": "checksum",
  "schema_status": "passed | failed | skipped | unconfirmed",
  "quality_status": "passed | warning | failed | skipped | unconfirmed",
  "started_at": "ISO-8601 timestamp",
  "completed_at": "ISO-8601 timestamp",
  "error": null
}
```

Do not use a generic file-name label if the actual name is unavailable.
Preserve the source file reference and destination separately.

## Safeguards: concurrency and idempotency

- Permit only one active execution per job unless overlap is explicitly
  approved;
- use a lock with expiration for crash recovery;
- derive stable snapshot or file identifiers from source metadata;
- prevent duplicate ingestion of the same immutable file;
- retry at file granularity when safe;
- do not rerun the entire source after one file has already completed;
- do not delete or overwrite a source file merely for a retry;
- use a separate temporary or staging path when an incomplete download may
  exist.

Before retrying, confirm whether the previous operation completed. Mark an
outcome `unconfirmed` rather than assuming success or failure.

## Procedure: retries

Retry only failures that are safe and supported by the source policy.
Recommended retry order:

1. connection or timeout failure;
2. bounded transient HTTP `429` or `5xx`;
3. storage service temporary failure;
4. partial file validation failure only after a complete re-download.

Do not retry:

- invalid authentication;
- authorization denial;
- non-approved endpoint or source;
- malformed or unsupported file format;
- permanent validation failure;
- missing configuration.

Use the retry limit configured by the job. Record:

- attempt number;
- retry type;
- scheduled retry time;
- previous `execution_id`;
- result or final error;
- whether an existing file was reused or downloaded again.

Use exponential backoff and respect source retry headers. Never retry an
indefinite number of times.

## Safeguards: log integrity and privacy

- append execution records through a reliable log destination;
- preserve timestamps in UTC and optionally include the configured timezone;
- make log records immutable after completion;
- retain successful and failed execution history;
- protect logs according to the applicable access policy;
- do not store passwords, access tokens, cookies, or authorization headers;
- do not store response bodies or CSV row contents unless explicitly approved;
- do not expose internal storage paths or source credentials in public reports;
- use stable identifiers instead of secrets in log fields.

The execution log is an audit record, not a backup of the downloaded data.

## Required output

Return a structured extraction execution result:

```json
{
  "execution_id": "execution identifier",
  "job_id": "job identifier",
  "scheduled_at": "ISO-8601 timestamp or null",
  "started_at": "ISO-8601 timestamp",
  "completed_at": "ISO-8601 timestamp",
  "duration_seconds": 0,
  "trigger": "schedule | manual | retry",
  "status": "success | partial | failed | skipped | cancelled | unconfirmed",
  "attempt": 1,
  "previous_execution_id": null,
  "source": "approved source identifier",
  "snapshot_id": "snapshot identifier or null",
  "refreshed_at": "ISO-8601 timestamp or null",
  "files_processed": [],
  "retry": {
    "scheduled": false,
    "retry_at": null,
    "attempt_limit": 0
  },
  "warnings": [],
  "errors": []
}
```

Each file status must be confirmed by its corresponding download, storage,
schema, or quality operation. The example schema template is not a real
execution result.

## Forbidden behavior

Do not:

- run an extraction without an approved source and schedule;
- execute overlapping jobs unless overlap is configured;
- hide partial or failed file outcomes;
- mark a running or unconfirmed operation as successful;
- log access tokens or secrets;
- overwrite execution history;
- silently retry permanent errors;
- transform or repair CSV contents in this skill;
- delete source files solely for successful reprocessing;
- guess a reporting period or source snapshot;
- claim that a process completed when only a request was submitted.

## Quality checklist

Before returning the execution result:

1. the execution identifier and job identifier are present;
2. the schedule and timezone are confirmed;
3. started and completed timestamps are recorded;
4. trigger type and attempt number are explicit;
5. every processed file has a confirmed status;
6. partial, failed, and unconfirmed outcomes are preserved;
7. retry behavior is bounded and idempotent;
8. concurrency and overlap were controlled;
9. authentication secrets are absent from the log;
10. schema and quality outcomes are linked to each file;
11. source snapshot metadata is included when available;
12. the execution history remains auditable.