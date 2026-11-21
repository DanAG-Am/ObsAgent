# Publish Report

## Purpose

Save the generated report in the designated repository and distribute it
to the intended recipients through an authorized email or internal
communication channel.

This skill manages report publication and delivery. It does not generate
the report contents, recalculate metrics, modify analytical findings, or
decide who is authorized to access sensitive information.

Use only finalized report artifacts produced by the rendering actions,
such as `render_excel`, `render_pdf`, or another approved
report-generation process.

## Procedure: supported publication channels

The report may be published through the following destinations when they
are configured and authorized:

-   **Repository**: save the final report in the designated repository
    or document storage location.
-   **Email**: send the report or an authorized report link to the
    specified recipients.
-   **Internal channel**: distribute the report through an approved
    internal communication channel.

A destination must be explicitly configured and available. Do not assume
that a repository, email service, or internal channel is connected.

## Required inputs

Request clarification or return a validation error if required
information is absent:

1.  **Generated report**: the final report file or a valid reference to
    it.
2.  **Report metadata**: title, report type, reporting period, and file
    format.
3.  **Repository destination**: the configured repository and target
    path or folder.
4.  **Publication mode**: save only, distribute only when already
    stored, or save and distribute.
5.  **Recipients**: approved email addresses and/or internal channel
    identifiers.
6.  **Distribution message**: subject and message body for email, or the
    corresponding message for an internal channel.
7.  **Access policy**: confirmation that the report is authorized for
    the intended recipients.
8.  **Publication context**: snapshot ID, refreshed-at timestamp, and
    any relevant warnings.
9.  **Delivery preferences**: attachment or secure link, where supported
    and authorized.

Do not invent recipient addresses, channel identifiers, repository
paths, or publication permissions.

## Procedure: pre-publication validation

Before publishing:

1.  Confirm that the report file exists and can be opened.
2.  Confirm that the file format matches the requested report type.
3.  Confirm that the report is finalized and is not an incomplete
    intermediate artifact.
4.  Validate the report title, period, and metadata.
5.  Confirm that the repository destination is configured and
    accessible.
6.  Validate every recipient and destination against the approved
    distribution request.
7.  Confirm that access policy has been applied and that the report
    contains no unauthorized sensitive information.
8.  Check whether the report already exists at the target destination.
9.  Preserve the source snapshot ID, refreshed-at timestamp, and
    warnings.
10. Confirm that the requested publication and delivery actions are
    supported by the available integrations.

If the report is invalid, incomplete, or unauthorized, stop publication
and return the relevant error.

## Procedure: repository storage

Save the finalized artifact in the designated repository.

The storage process should:

-   use the configured repository and target location;
-   preserve the requested file name and extension where possible;
-   avoid overwriting an existing report unless overwrite behavior is
    explicitly authorized;
-   preserve the report's original contents;
-   record the final repository path or file reference;
-   record the publication timestamp and result.

If a file with the same name already exists, follow the repository's
approved versioning or conflict policy. Do not silently overwrite an
existing report.

A successful storage result must confirm that the file was saved and
provide a usable reference to the stored artifact.

## Procedure: distribution

Distribute the report only after the publication request and recipient
permissions have been validated.

### Email distribution

When email is requested:

-   use only the supplied and authorized recipient addresses;
-   use the requested subject and message body;
-   attach the report or include a secure repository link according to
    the approved delivery method;
-   preserve the intended recipient list;
-   record the sending result for each recipient or delivery operation;
-   do not claim delivery if the email service reports only that a
    message was accepted or queued.

Do not expose recipients to one another through the `To` or `CC` fields
when the distribution policy requires separate or hidden delivery. Use
`BCC` or individual messages only when supported and explicitly
appropriate.

### Internal channel distribution

When an internal channel is requested:

-   use only the configured channel identifier;
-   verify that the channel is an approved destination;
-   publish the authorized report attachment or secure link;
-   include the requested contextual message;
-   record the channel and publication result.

Do not post confidential reports in public or unapproved channels.

### Distribution status

Track each destination independently. A report may be stored
successfully while one or more delivery attempts fail.

Do not mark the entire publication process as fully successful when a
required destination has failed.

## Procedure: recipient and publication log

Maintain an auditable record of the publication operation.

The log should include:

-   report identifier and file name;
-   report type and reporting period;
-   repository destination and stored file reference;
-   destination type (`repository`, `email`, or `internal_channel`);
-   intended recipient address or channel identifier, subject to access
    restrictions;
-   publication or delivery timestamp;
-   operation status;
-   error details when an operation fails;
-   snapshot ID and refreshed-at timestamp.

Record only the recipient information necessary for audit and delivery.
Protect the log according to the applicable access policy.

Do not record passwords, access tokens, or other authentication secrets.

## Procedure: output contract

Return a structured publication result:

``` json
{
  "status": "success | partial | failed",
  "report": {
    "report_id": "report identifier",
    "file_name": "report_name.pdf",
    "file_type": "pdf | xlsx",
    "period": {
      "from": "YYYYMM",
      "to": "YYYYMM"
    },
    "snapshot_id": "snapshot identifier",
    "refreshed_at": "ISO-8601 timestamp"
  },
  "repository": {
    "status": "saved | failed | skipped",
    "destination": "repository path or identifier",
    "file_reference": "stored report reference"
  },
  "distribution": [
    {
      "destination_type": "email | internal_channel",
      "recipient": "authorized recipient or channel",
      "status": "sent | accepted | failed | skipped",
      "timestamp": "ISO-8601 timestamp",
      "message_reference": null,
      "error": null
    }
  ],
  "publication_log_id": "log identifier",
  "warnings": [],
  "errors": []
}
```

The example is a schema template, not a real publication result. Use
only statuses confirmed by the repository or delivery service. Omit
unavailable references rather than inventing them.

## Status and retry rules

Use the following status conventions:

-   **Success**: all required storage and distribution operations
    completed successfully according to their service responses.
-   **Partial**: the report was stored or delivered to some
    destinations, but at least one required operation failed or remains
    incomplete.
-   **Failed**: no required publication operation completed
    successfully.
-   **Skipped**: a destination was intentionally not used because it was
    not requested or was not applicable.

Retry only failed operations when the integration supports safe retries.
Before retrying, check whether the previous operation may already have
completed to avoid duplicate reports or messages.

Do not resend a report to all recipients merely because one destination
failed.

## Safeguards: access, privacy, and auditability

-   Publish only finalized reports.
-   Respect `apply_access_policy` and the authorization of each intended
    recipient.
-   Do not distribute reports containing sensitive fields to
    unauthorized users or channels.
-   Do not broaden the recipient list without explicit authorization.
-   Use secure repository links or approved attachments according to the
    distribution policy.
-   Do not expose authentication secrets in report metadata, messages,
    or logs.
-   Preserve the report's source snapshot and refresh context.
-   Keep an auditable record of storage and distribution outcomes.
-   Do not claim that a recipient opened or read a report unless the
    delivery system provides that evidence.

If recipient authorization or destination permissions cannot be
verified, do not distribute the report.

## Error handling

Return a structured error when:

-   the generated report is missing, corrupted, or unsupported;
-   the repository destination is unavailable;
-   the target file conflicts with an existing artifact and no approved
    conflict policy applies;
-   a recipient address or channel identifier is invalid;
-   access permissions cannot be verified;
-   the email or internal communication service fails;
-   the report cannot be saved or a delivery result cannot be confirmed.

Distinguish between:

-   **Validation error**: the report or publication request is
    incomplete or invalid;
-   **Access denied**: the user or recipient is not authorized;
-   **Storage error**: the repository operation failed;
-   **Delivery error**: a distribution operation failed;
-   **Partial publication**: some required operations succeeded and
    others failed;
-   **Unconfirmed**: the service did not provide enough evidence to
    determine the final operation status.

Do not report a successful delivery when the service only confirms that
a request was submitted or queued.

## Required output

Return:

1.  the overall publication status;
2.  the report identifier, file name, and format;
3.  the repository path or stored file reference;
4.  the status of each distribution destination;
5.  the recipient or channel record for each attempted delivery;
6.  the publication timestamp and log identifier;
7.  warnings and errors;
8.  the source snapshot ID and refreshed-at timestamp.

The result must make it possible to audit where the report was saved and
which distribution operations were attempted and completed.

## Forbidden behavior

Do not:

-   generate or modify report contents in this skill;
-   publish an unvalidated or incomplete report;
-   invent repository paths, recipients, channels, or delivery statuses;
-   overwrite existing files without explicit authorization;
-   distribute reports to unapproved recipients or channels;
-   bypass access policy or expose sensitive data;
-   claim that a queued message was delivered or read;
-   hide failed destinations behind an overall success status;
-   retry successful operations in a way that creates duplicate reports
    or messages;
-   store authentication secrets in publication logs.

## Quality checklist

Before returning the publication result, verify that:

1.  the report file exists and is valid;
2.  the report type, period, and metadata are correct;
3.  the repository destination is authorized;
4.  existing-file conflicts follow the approved policy;
5.  recipient addresses and channel identifiers are validated;
6.  access policy has been applied;
7.  each storage and delivery operation has a confirmed status;
8.  partial failures are represented accurately;
9.  recipient and publication logs are recorded securely;
10. no authentication secrets are stored;
11. snapshot ID, refresh time, and publication timestamp are present;
12. the final result contains usable report references and audit
    information.