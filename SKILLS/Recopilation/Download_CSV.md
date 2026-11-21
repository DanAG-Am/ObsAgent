# Download CSV

## Purpose

Download CSV files from approved system endpoints using Python's
`requests` library. Support authenticated and unauthenticated sources while
preserving the original response, reporting failures explicitly, and
preparing the file for schema and data-quality validation.

This skill only retrieves files. It does not interpret, transform, aggregate,
or silently repair CSV content.

## Required inputs

Request clarification if any required input is missing:

1. approved HTTPS endpoint;
2. destination path or file name;
3. authentication mode, if required;
4. token source and header scheme, if required;
5. request timeout and maximum file size;
6. expected content type or file extension;
7. checksum or version identifier, when the source provides one.

Never invent an endpoint, token, query parameter, or authentication scheme.
Use only approved system sources and catalogued endpoint values.

## Procedure: HTTP request

Use `requests` with an explicit timeout and a session:

```python
import os
from pathlib import Path

import requests


def download_csv(
    url: str,
    destination: Path,
    token: str | None = None,
    timeout: tuple[float, float] = (10.0, 120.0),
) -> Path:
    headers = {"Accept": "text/csv, application/csv"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with requests.Session() as session:
        response = session.get(
            url,
            headers=headers,
            timeout=timeout,
            stream=True,
        )
        response.raise_for_status()

        temporary = destination.with_suffix(destination.suffix + ".part")
        completed = False
        try:
            with temporary.open("wb") as csv_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        csv_file.write(chunk)
            temporary.replace(destination)
            completed = True
        finally:
            if not completed:
                temporary.unlink(missing_ok=True)

    return destination
```

Token values must come from a secret manager or environment variable, for
example `os.environ["CSV_API_TOKEN"]`. Never place tokens in source code,
command-line arguments, logs, report output, or committed configuration.

## Procedure: response handling

1. Validate that the URL uses HTTPS unless an approved internal exception
   exists.
2. Set `Accept` to a CSV media type.
3. Send the token using the endpoint's approved header scheme.
4. Use `stream=True` for potentially large files.
5. Call `raise_for_status()` before writing the response.
6. Write binary chunks to a temporary `.part` file.
7. Replace the destination only after the download completes.
8. Record status code, final URL, byte count, source, and retrieval time.
9. Pass the completed file to `Validate_CSV_schema`.

Follow redirects only when allowed by the endpoint policy. Do not send
authorization headers to a different host after a redirect without explicit
approval.

## Authentication

Supported authentication must be explicit:

```python
headers = {"Authorization": f"Bearer {os.environ['CSV_API_TOKEN']}"}
```

For another approved scheme, use its documented header or request mechanism.
Do not put access tokens in query strings because URLs can be logged or
retained by intermediaries.

If authentication fails:

- report `401` or `403` explicitly;
- do not retry with a different token or guessed scheme;
- do not fall back to unauthenticated access;
- do not write an authentication error page as a CSV file.

## Procedure: retries and failures

Retry only transient failures such as connection resets, timeouts, `429`, and
selected `5xx` responses. Use bounded retries with exponential backoff and
respect `Retry-After` when supplied.

Do not retry:

- `400` invalid request;
- `401` unauthenticated;
- `403` unauthorized;
- `404` missing endpoint;
- malformed or non-CSV responses.

Classify failures as:

- `authentication_failed`;
- `authorization_failed`;
- `endpoint_not_found`;
- `rate_limited`;
- `timeout`;
- `connection_failed`;
- `server_error`;
- `invalid_content`;
- `file_too_large`;
- `storage_failed`.

Expose the failure class and endpoint identifier to the caller. Never return
an empty or success-shaped file after a failed request.

## Safeguards: content and storage

- Require a successful HTTP status before saving.
- Reject HTML, JSON error payloads, and other non-CSV content.
- Validate `Content-Type` when supplied, but do not rely on it alone.
- Enforce the configured maximum file size using `Content-Length` and the
  streamed byte count.
- Use a temporary file and atomic replacement.
- Do not overwrite an existing valid file until the new download completes.
- Record checksum, byte count, source URL or endpoint ID, and retrieval time
  when available.
- Preserve the downloaded bytes; normalization belongs to later skills.
- Close the response and session on every path.

For retrying or resuming a partial download, use an approved range-download
protocol. Never treat a partial `.part` file as complete.

## Required output

Return a download result:

```json
{
  "status": "downloaded | failed | rejected",
  "path": "local destination path",
  "source": "approved endpoint identifier",
  "url": "endpoint URL without credentials",
  "http_status": 200,
  "content_type": "text/csv",
  "bytes": 0,
  "sha256": "checksum",
  "retrieved_at": "ISO-8601 timestamp",
  "authentication": "bearer | approved_scheme | none",
  "warnings": [],
  "error": null
}
```

Do not return tokens, cookies, authorization headers, or sensitive response
headers in the result. If the file is rejected, return the reason and do not
mark the download as complete.

## Forbidden behavior

Do not:

- hard-code credentials or expose tokens;
- send tokens in URLs;
- disable TLS verification;
- use unbounded retries;
- follow unapproved cross-host redirects;
- save an HTTP error page as a CSV;
- overwrite a valid file with an incomplete download;
- treat a partial file as successful;
- silently ignore non-2xx responses;
- invent endpoint parameters or authentication schemes;
- transform or clean the CSV during download;
- log request headers, tokens, cookies, or response bodies containing secrets.

## Quality checklist

Before returning the result:

1. endpoint and authentication mode are approved;
2. HTTPS and TLS verification are enabled;
3. timeout and file-size limits are applied;
4. transient retry behavior is bounded;
5. authentication failures are explicit;
6. HTTP status and content are validated;
7. the file was written atomically;
8. byte count and checksum are recorded when available;
9. no credentials appear in logs or output;
10. the destination is complete and readable;
11. schema validation is the next processing step;
12. snapshot or retrieval metadata is preserved.