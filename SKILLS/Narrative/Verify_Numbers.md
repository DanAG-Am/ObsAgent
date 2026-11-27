# Verify Numbers

## Purpose

Verify that every numeric statement in a drafted report matches a calculated
and traceable source result. Number verification is a final control between
drafting and publication.

This skill checks values and units. It does not recalculate portfolio ratios,
change a narrative's classification, or accept a number solely because it
appears in the original source text.

## Required inputs

- complete drafted narrative text;
- additive query results or source objects;
- period-comparison objects;
- anomaly objects;
- highlighted-finding objects;
- metric definitions and formula versions;
- numerator and denominator fields;
- approved display and rounding policy.

No numeric claim may be marked as verified without all applicable source
metadata.

## Procedure: verification scope

Extract and verify:

1. headline and title numbers;
2. executive-summary numbers;
3. section text numbers;
4. table and chart labels;
5. recommendation numbers;
6. footnotes and methodology numbers;
7. MoM and YoY changes;
8. trend windows and observation counts;
9. z-scores, IQR fences, peer averages, and thresholds;
10. numerator, denominator, population, and count values;
11. percentages and percentage points;
12. dates represented as `YYYYMM` or ISO-8601.

Report text that contains no numeric claim is valid as a qualitative statement,
provided it does not imply an unsupported magnitude or trend.

## Source precedence

Use only these source types, in descending precedence:

1. verified query/tool output;
2. approved period-comparison object;
3. approved anomaly object;
4. highlighted-finding evidence.

When sources conflict, mark the narrative number `unverified` and do not
choose a value by preference or majority. Return the conflicting source
values to the number-verification failure list.

Never use:

- a number derived from the narrative itself;
- an average of displayed ratios;
- a rate reconstructed from rounded text;
- an example value;
- an assumed threshold or baseline;
- an inferred population or denominator;
- a number copied from an incompatible filter or MOB range.

## Value matching

For each numeric claim, identify:

- metric name;
- period;
- filters;
- group or segment;
- numerator and denominator;
- unit;
- source field;
- rounding or formatting applied.

A match requires:

- the same metric and unit;
- the same period and segment;
- the same filters and MOB range;
- a source value equal within the approved rounding tolerance.

If no approved rounding policy exists, apply these defaults only for display:

| Unit | Maximum display difference |
|---|---|
| percentage/rate | source value rounded to the displayed decimal places |
| percentage points | source absolute change rounded to the displayed decimal places |
| currency/amount | approved scale and displayed decimal places |
| counts | exact integer match |
| z-score | displayed decimal places |
| IQR fence | displayed decimal places |
| YYYYMM/date | exact match |

The verifier must never round a source, then use the rounded value as source
truth for downstream arithmetic. It compares only the formatted narrative
representation against the unrounded source using the display tolerance.

## Claim classes

### Actual metric value

An actual value is valid only if a source object exposes the metric for the
claimed period and scope.

Examples of source fields:

- `base_value`;
- `candidate.value`;
- `baseline.mean`;
- `base_period`;
- period-query `result_rows`.

### Absolute change

Verify both the sign and value:

```text
absolute_change = current_value - baseline_value
```

For rates, verify percentage points rather than relative percent. For amounts,
verify the source currency and scale. Never change a negative change into a
positive narrative phrase.

### Percentage change

Verify against the source period-comparison object:

- `mom.percent_change`;
- `yoy.percent_change`;
- `trend.window_percent_change`.

Require the stated baseline period and valid baseline. If the source marks
percentage change `null` or `N/A`, reject a percentage statement. If the
source baseline is zero or negative and the narrative provides a percentage,
mark it `unverified` unless an approved metric-specific convention exists.

### Trend

Verify:

- `trend.direction`;
- `window_start` and `window_end`;
- `valid_observation_count`;
- `window_absolute_change`;
- `window_percent_change`;
- `latest_movement`.

Do not verify a trend if fewer than three valid observations exist. Do not
accept a count of movements that differs from the ordered source window.

### Z-score

Verify:

- peer mean;
- standard deviation;
- z-score;
- threshold;
- direction;
- status.

Reject the claim if the narrative uses a z-score when the peer population,
standard deviation, threshold, or source method is unavailable.

### IQR

Verify:

- Q1;
- Q3;
- IQR;
- lower fence;
- upper fence;
- outlier direction;
- status.

Reject an IQR claim when the percentile convention differs from the source
implementation or when the peer count is below the approved minimum.

### Regulatory threshold

Verify:

- threshold value;
- operator;
- jurisdiction or scope;
- effective date;
- source;
- status;
- observed metric and period.

A z-score or IQR result is not evidence of a regulatory breach. The verifier
must mark `regulatory_status = breach` only when the source object contains
approved threshold evidence.

## Unit and wording checks

Verify that wording preserves the unit:

- `4.8%` is a rate;
- `+0.6 percentage point` is an absolute rate change;
- `+3.2%` is relative change;
- `120 million MXN` is an amount;
- `1,200 accounts` is a count;
- `3.4` is a z-score only if the context says z-score.

Reject statements that:

- add percentage signs to percentage-point changes;
- omit percentage signs from rate values;
- describe counts as rates;
- describe rates as currency;
- mix amount and account delinquency;
- compare unlike denominators or populations;
- combine overlapping periods as an independent period.

## Calendar and period checks

Every period must:

- use valid integer `YYYYMM` format;
- be consistent with source vintage;
- include a baseline period for comparisons;
- use the same MOB or MOB range for vintage comparisons;
- use exactly 12 months earlier for YoY;
- use the immediately prior month for MoM.

Reject text that uses an unverified period or reverses a baseline.

## Narrative extraction rules

Map each text number to a source object before deciding pass/fail:

1. locate the numeric token and adjacent unit;
2. locate the nearest metric name;
3. locate the nearest period;
4. locate the nearest segment or peer population;
5. find the matching source field;
6. compare value, sign, unit, period, and scope;
7. record the matched field or failure code.

Do not treat year references, rankings, bullet numbers, report sections, or
ISO refresh dates as calculated metrics unless the narrative presents them as
such. Those values must still match source metadata when presented.

## Verification statuses

For each numeric claim:

| Status | Meaning |
|---|---|
| `verified` | source match is exact or within approved rounding |
| `rounded_match` | source match is valid but requires display rounding |
| `unverified` | no source match or conflicting scope |
| `mismatched` | a source exists, but value, sign, unit, or period differs |
| `missing_source` | source object does not expose the claim |
| `unsupported_claim` | claim refers to an unapproved metric or threshold |

Overall report status:

- `passed`: every numeric claim is verified or rounded-match;
- `failed`: one or more mismatches or unsupported claims;
- `unavailable`: source objects are incomplete;

Never collapse `failed` and `unavailable` together.

## Required output

Return a machine-readable verification object:

```json
{
  "status": "passed | failed | unavailable",
  "verified_claim_count": 0,
  "failed_claim_count": 0,
  "claims": [
    {
      "text": "exact quoted numeric claim",
      "metric": "metric_name",
      "period": "YYYYMM",
      "value": 0,
      "unit": "percent | percentage_points | currency | count | ratio",
      "source_field": "object.field",
      "status": "verified | rounded_match | unverified | mismatched | missing_source | unsupported_claim",
      "expected_value": 0,
      "differences": []
    }
  ],
  "failed_checks": [],
  "warnings": []
}
```

The verifier must include exact source fields for every failed or unverified
claim. Do not present a proposed replacement value unless it is directly
traceable to source data.

## Safeguards: failure handling

When verification fails:

1. do not describe the report as verified;
2. return the exact mismatched text;
3. identify source field and expected value;
4. mark `status = failed`;
5. require the narrative to be corrected or held;
6. rerun verification after any draft change.

If sources are unavailable:

1. set `status = unavailable`;
2. do not invent or estimate values;
3. do not describe the report as verified.

## Safeguards: correction loop

After a mismatch:

- correct only with the source object's actual value;
- do not alter the metric or baseline silently;
- preserve period and segment context;
- rerun extraction and matching;
- retain a record of prior failed text and correction.

A corrected draft is not passed until all claims are verified again.

## Forbidden behavior

Do not:

- accept an example as evidence;
- invent a baseline or threshold;
- verify an arithmetic result through a rounded displayed ratio;
- average period or segment values;
- mark missing source as zero;
- hide unit differences;
- ignore sign differences;
- accept percentage change for a negative or zero baseline;
- label a rounded approximation as exact;
- confirm regulatory compliance without a verified threshold;
- recalculate and silently overwrite an upstream source;
- publish a failed or unavailable verification result.

## Quality checklist

Before returning verification:

1. every title and summary number was checked;
2. every table, chart, and footnote number was checked;
3. every period and baseline is valid;
4. every unit and sign matches;
5. every anomaly value traces to a source object;
6. every threshold has jurisdiction and source metadata;
7. every failed value includes an expected source field;
8. rounded values have an approved display tolerance;
9. failed claims and unavailable sources remain clearly marked;
10. no source-derived result was modified in place.