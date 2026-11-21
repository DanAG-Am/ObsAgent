# Highlight Findings

## Purpose

Rank anomalies by verified severity and place the highest-priority findings at
the beginning of every report. The skill does not recalculate metrics or
upgrade an anomaly's evidence; it only orders and summarizes already verified
findings.

Use this skill after `Detect_Anomalies` and before `Generate_Narrative`.
The highlighted findings must remain traceable to the structured anomaly
objects and original snapshot.

## Required inputs

- one or more structured anomaly objects;
- each anomaly's `severity`, `confidence`, and `human_review_required`;
- regulatory, z-score, IQR, and volume evidence;
- metric, domain, period, group, filters, and snapshot metadata;
- report recipient and report objective.

Ignore a result that is not a verified anomaly unless it is explicitly
classified as `review_required`. Never promote ordinary, missing, or
unsupported values into highlighted findings.

## Procedure: severity ranking

Apply this descending priority order:

| Priority | Severity | Placement |
|---:|---|---|
| 1 | `critical` | first |
| 2 | `review_required` | first or immediately after critical findings |
| 3 | `high` | high-priority section |
| 4 | `medium` | standard finding section |
| 5 | `low` | lower-priority or appendix |

`review_required` is ranked second because low volume, missing data,
unsupported metrics, or conflicting evidence may require immediate control
attention even though the severity has not been confirmed.

Do not reinterpret a `review_required` object as `critical`, `high`, or
another severity. Preserve both fields:

```text
severity = review_required
human_review_required = true
```

## Deterministic tie-breakers

Within the same severity, rank findings in this order:

1. approved regulatory breach;
2. human review is required;
3. extreme z-score result;
4. IQR high or low outlier;
5. lower confidence;
6. lower denominator or population, where the metric exposes one;
7. larger absolute deviation or magnitude, only if the source object supplies it;
8. latest period;
9. domain and metric alphabetically;
10. group value alphabetically.

The tie-breakers are evidence-ordering controls, not new anomaly classifications.
Do not rank by an absolute deviation that was not supplied or cannot be
verified. Do not compare unlike metrics or denominators at this step.

When both low confidence and severe evidence conflict, keep the higher
severity but place a prominent review warning next to the finding.

## Report placement

Place all highlighted anomalies at the beginning of the report in this order:

1. report title or `Executive Summary`;
2. `Key Findings` or `Top Findings`;
3. ranked anomalies;
4. period comparisons and trend context;
5. remaining narrative or supporting detail;
6. methodology and snapshot controls.

For a recipient profile:

- **Executive**: show at most the five highest-priority findings;
- **Board**: show critical and review-required findings first;
- **Risk analyst**: show every verified finding, with evidence columns;
- **Operations**: show findings affecting actionable segments first;
- **Regulator**: show all regulatory breaches and review-required findings;
- **General**: show the top three findings in plain language.

No anomaly may be moved below unrelated portfolio context merely because the
recipient is brief. Lower-ranked findings may be omitted only through an
explicit recipient limit, not hidden because they are inconvenient.

## Finding format

Assign a zero-padded rank to each retained finding:

```json
{
  "rank": 1,
  "finding_id": "stable-source-object-id",
  "domain": "fraud | delinquency | claims",
  "metric": "metric_name",
  "period": "YYYYMM",
  "group_by": "channel",
  "group_value": "catalog value",
  "severity": "critical",
  "confidence": "high",
  "human_review_required": true,
  "headline": "verified concise finding",
  "evidence": {
    "observed_value": 0,
    "numerator": null,
    "denominator": null,
    "z_score_status": "not_applicable | not_anomaly | anomaly",
    "iqr_status": "not_applicable | not_anomaly | anomaly",
    "regulatory_status": "threshold_unavailable | within_threshold | approaching | breach"
  },
  "warnings": [],
  "snapshot_id": "snapshot identifier",
  "refreshed_at": "ISO-8601 timestamp"
}
```

Each headline must use only verified fields. Keep the headline brief:

- one observed metric;
- one period;
- one segment or peer population;
- the result and reason for priority.

Examples of structure, not values:

- "Delinquency rate is a high IQR outlier in [group] for [period]."
- "Approved regulatory threshold is breached for [metric] in [period]."
- "Fraud exposure requires human review because [specific verified reason]."

Never copy example values into a report.

## Consolidation and deduplication

Do not merge different metrics, periods, MOB ranges, or domains. Duplicate only
an identical source finding when the same metric, period, group, filters, and
method identify the same observation.

When duplicates exist:

1. retain one source object;
2. keep the highest severity;
3. keep the highest confidence;
4. keep `human_review_required = true` if either object requires review;
5. merge non-conflicting warnings;
6. do not merge conflicting snapshot or source metadata.

## Safeguards: volume and confidence

A finding may rank ahead of a lower-severity finding only by the severity
ranking, not merely because its volume is high. Within a severity, use
confidence and evidence tie-breakers.

Downgrade the *presentation confidence*, not the source severity, when:

- the peer count is insufficient;
- the denominator is zero or below minimum volume;
- snapshot coverage is incomplete;
- methods conflict;
- no regulatory threshold source is available;
- the metric is unsupported or unavailable.

State `confidence` as provided or `low` only through a verification rule.
Never describe a review finding as conclusive.

## Required output

Send the ranked list to `Generate_Narrative` in this order:

```json
{
  "highlighted_findings": [],
  "omitted_by_recipient_limit": [],
  "report_order": [
    "executive_summary",
    "key_findings",
    "trends",
    "remaining_sections",
    "controls"
  ],
  "snapshot_id": "snapshot identifier",
  "refreshed_at": "ISO-8601 timestamp"
}
```

The `omitted_by_recipient_limit` field must include any findings not shown due
to recipient length limits, along with their rank and reason. It must not be
used to suppress critical or review-required findings for brief recipient
profiles.

## Forbidden behavior

Do not:

- rank findings from display text instead of source objects;
- recalculate a z-score, IQR fence, threshold, or variation;
- promote ordinary values to anomalies;
- omit critical or regulatory findings to meet a recipient limit;
- reorder findings by tone or opinion;
- hide low volume or missing-source warnings;
- mix unlike denominators in a tie-break;
- use the example data in a final report;
- place ordinary trends before critical findings.

## Quality checklist

Before the report is drafted:

1. every finding has a source anomaly object;
2. each severity is valid;
3. critical findings are first;
4. review-required findings follow critical findings;
5. tie-breakers use only supplied evidence;
6. identical observations are deduplicated;
7. different periods or MOB ranges remain separate;
8. regulatory evidence is not inferred;
9. omitted findings are recorded;
10. snapshot ID and refresh time are included;
11. `Key Findings` appears before trends and supporting sections;
12. no placeholder or example value remains.