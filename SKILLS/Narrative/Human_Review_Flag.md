# Human Review Flag

## Purpose

Determine whether a report or individual result must be held for human review
before publication. This skill is a control gate, not an anomaly classifier
and not a replacement for number verification.

Apply the flag after verified anomalies and period comparisons exist, and
before `Generate_Narrative` or report publication. A report may be drafted
while under review, but it must not be represented as final or approved.

## Required inputs

- anomaly objects and their `severity`, `confidence`, and
  `human_review_required` fields;
- period-comparison objects and their warnings;
- number-verification status;
- snapshot ID, refreshed-at timestamp, and data-quality status;
- minimum-volume threshold and actual numerator/denominator;
- applicable regulatory threshold metadata;
- report recipient and publication mode.

Never infer human-review status from prose or an unverified displayed value.
Use structured source objects only.

## Procedure: mandatory review triggers

Set `human_review_required = true` when any of the following is true:

1. one or more anomalies have `severity = critical`;
2. a result has `confidence = low`;
3. the anomaly or report severity is `review_required`;
4. a severe, suspected, or verified fraud or claims result exists;
5. an approved regulatory threshold is breached;
6. a denominator is zero or unknown;
7. actual population or denominator is below the minimum-volume threshold;
8. data quality is incomplete, invalid, duplicated, or below a policy limit;
9. peer coverage or observation count is insufficient;
10. z-score and IQR methods conflict;
11. a metric or regulatory threshold is unsupported or unavailable;
12. number verification fails or cannot complete;
13. filters or MOB ranges are incompatible or missing;
14. the source or refreshed snapshot is absent or stale beyond policy.

Human review may be added for a high-severity finding only when the
regulatory, legal, or report policy requires it. It must not be removed merely
to improve report brevity.

## Confidence assessment

Use source confidence rather than stylistic certainty:

| Confidence | Meaning | Review action |
|---|---|---|
| `high` | verified metric, adequate population, valid denominator, reliable snapshot | no review unless another trigger exists |
| `medium` | usable with minor limitations or source warnings | review optionally by policy |
| `low` | incomplete, conflicting, unsupported, or small-sample evidence | mandatory review |

Do not convert `medium` confidence into `low` solely for a negative finding.
Use the report or domain policy to decide whether medium confidence requires
review.

When confidence is missing, set it to `low` and record `missing_confidence`
in warnings. Do not assume `high`.

## Review scope

Identify both report-level and finding-level scope:

```text
report_level_review = any report-wide trigger
finding_level_review = trigger(s) associated with one anomaly
```

Finding-level review must include:

- metric;
- period;
- domain;
- filters;
- observed value;
- denominator and volume;
- severity;
- confidence;
- failed or unavailable evidence;
- approved threshold or source, if applicable.

Report-level review must include:

- each triggering finding;
- snapshot and freshness;
- number-verification status;
- all unresolved warnings;
- publication or recipient context.

## Severity and review behavior

| Condition | Review priority |
|---|---|
| Critical regulatory breach or severe verified loss | `urgent` |
| Low confidence or unsupported result | `high` |
| Critical anomaly with full evidence | `high` |
| Review-required result | `high` |
| Low denominator or data-quality issue | `high` |
| High anomaly without a mandatory trigger | `standard` |
| Medium or low anomaly with valid evidence | `standard` only if policy requires |

The reviewer should verify:

- source metric and formula;
- period and filters;
- numerator and denominator;
- peer and MOB comparability;
- z-score/IQR method and thresholds;
- regulatory source and jurisdiction;
- number-verification output;
- publication risk and recipient.

## Safeguards: publication gate

Before publication:

1. if a mandatory trigger is present, set `publication_status = held`;
2. place a visible review flag in the report's beginning;
3. include the exact triggering reasons;
4. preserve, rather than rewrite, the verified metrics;
5. draft with non-final labels such as `pending review`;
6. do not present review-held results as approved or compliant;
7. never publish unsupported fraud, claims, or regulatory conclusions.

Only an authorized reviewer may change a held result to
`human_reviewed = true` and supply an approval status. The narrative skill
must not silently self-clear a flag.

If publication is not manual or a human reviewer is unavailable:

- set `release_authority = none`;
- retain `human_review_required = true`;
- stop the report at the review-held stage.

## Required output

Return a report-level review object:

```json
{
  "human_review_required": false,
  "publication_status": "draft | held | ready",
  "release_authority": "human_reviewer | none",
  "priority": "none | standard | high | urgent",
  "confidence": "high | medium | low",
  "triggers": [
    {
      "code": "critical_anomaly",
      "finding_id": "source finding identifier",
      "metric": "metric_name",
      "period": "YYYYMM",
      "reason": "verified trigger reason",
      "severity": "critical",
      "confidence": "high"
    }
  ],
  "review_scope": [
    {
      "finding_id": "source finding identifier",
      "metric": "metric_name",
      "period": "YYYYMM",
      "group_by": "channel",
      "group_value": "catalog value",
      "reason_codes": [],
      "snapshot_id": "snapshot identifier",
      "refreshed_at": "ISO-8601 timestamp"
    }
  ],
  "number_verification": {
    "status": "passed | failed | unavailable",
    "failed_checks": [],
    "warnings": []
  },
  "human_review_decision": {
    "human_reviewed": false,
    "reviewer": null,
    "decision": "pending | approved | rejected | returned_for_revision",
    "reviewed_at": null,
    "comments": []
  },
  "warnings": [],
  "snapshot_id": "snapshot identifier",
  "refreshed_at": "ISO-8601 timestamp"
}
```

The report draft must include a prominent control label, for example:

> Human review required — this report contains a critical regulatory breach
> and will remain held until a reviewer authorizes publication.

Use actual triggers rather than this example text.

## Narrative behavior

When a mandatory review trigger exists:

- include the review reason prominently;
- retain the exact finding and confidence;
- do not make the review flag visually or linguistically weak;
- state that publication is held or awaiting review;
- avoid unapproved recommendations or enforcement actions;
- keep critical findings at the beginning of the report;
- include regulatory source and jurisdiction only if verified.

## Human review decision rules

The reviewer may:

- approve the report for publication;
- reject it;
- return it for revision;
- request source, denominator, or regulatory validation.

Approval does not:

- erase source warnings;
- change the metric result;
- convert `low` confidence to `high`;
- create a missing threshold;
- validate unsupported fraud or claims fields.

If revised:

1. rerun number verification;
2. rerun anomaly detection if the source or metric changed;
3. recalculate report-level review triggers;
4. update the snapshot metadata;
5. preserve the audit trail of the prior decision.

## Forbidden behavior

Do not:

- self-approve a report or clear a mandatory review flag;
- publish a critical anomaly as normal;
- hide low confidence;
- replace missing evidence with reviewer assumptions;
- infer a regulatory breach from z-score or IQR alone;
- downgrade `critical` or `review_required` solely for brevity;
- omit denominator, volume, or data-quality warnings;
- claim legal or regulatory compliance;
- use example trigger text or numbers as report facts.

## Quality checklist

Before drafting or publication:

1. every mandatory trigger is represented as a code and reason;
2. critical findings force report review;
3. low-confidence results force report review;
4. report and finding scope are both clear;
5. number verification is complete;
6. population and denominator warnings are included;
7. publication status is `draft` or `held`, not falsely `ready`;
8. snapshot ID and refresh time are present;
9. no unsupported threshold or compliance claim is included;
10. no human decision is invented;
11. the report is routed to a reviewer or visibly held;
12. critical findings remain at the beginning.