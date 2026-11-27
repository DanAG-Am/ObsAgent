# Generate Narrative

## Purpose

Draft an executive explanation from verified, already calculated portfolio
metrics. The language model explains results; it does not calculate,
recalculate, aggregate, infer, or invent figures.

Use the period-comparison and anomaly objects produced by the other skills,
plus the original query metadata. Tailor clarity, emphasis, and
recommendations to the named recipient.

## Required inputs

Request clarification if any required input is absent:

1. one or more verified metric results;
2. period and source context;
3. recipient (`executive`, `board`, `risk_analyst`, `operations`,
   `regulator`, or `general`);
4. report objective or decision to support;
5. filters and segment context;
6. comparisons and anomalies already calculated;
7. warnings.

Never accept a metric, change, trend, anomaly, threshold, or denominator that
was not returned by a query or calculation skill.

## Procedure: recipient profiles

Adapt wording and depth without changing facts.

| Recipient | Tone | Length | Emphasis |
|---|---|---|---|
| Executive | direct, concise, decision-oriented | brief | outcome, material magnitude, recommendation |
| Board | calm, strategic, governed | concise | portfolio risk, direction, control implications |
| Risk analyst | precise, evidence-led | detailed | numerators, denominators, peers, confidence |
| Operations | practical, action-led | concise to detailed | segment, cause to investigate, next check |
| Regulator | formal, neutral, auditable | detailed | policy scope, threshold, source, exact dates |
| General | plain, accessible | concise | what changed and why it matters |

For all recipients:

- use direct, natural language;
- avoid promotional or speculative language;
- avoid unexplained jargon;
- distinguish correlation and causation;
- do not recommend an intervention unless the evidence supports it.

Do not convert a calm analytical tone into certainty. Use "indicates",
"suggests", or "appears" only when the evidence is incomplete.

## Narrative assembly

Create the explanation in this order:

1. **Portfolio state**
   State the period and high-level result.
2. **Primary finding**
   Give the exact metric, value, unit, segment, and filters.
3. **Comparison**
   Include verified absolute and relative MoM or YoY changes.
4. **Trend**
   State the ordered window and trend direction.
5. **Anomaly**
   Explain z-score, IQR, or regulatory evidence separately.
6. **Decision implication**
   Describe what a recipient should examine or decide.
7. **Confidence and controls**
   Include denominator, volume, data-quality, and threshold context.

Skip a section only when no verified input exists for it. Do not substitute a
zero or `N/A` for missing content.

## Exact-value rules

- Copy metric values only from verified query outputs.
- Do not round source values unless formatting is specified.
- Preserve units and show:
  - percentage rates with `%`;
  - percentage-point differences with `percentage points`;
  - amounts with the approved currency and scale;
  - counts as counts.
- Distinguish:
  - absolute change;
  - percentage change;
  - percentage-point change.
- Distinguish amount-based and account-based delinquency.
- Do not average period rates or ratios.
- Do not combine unlike denominators.
- Do not convert a rate into an amount.
- Do not describe a statistical outlier as fraud, claims, or delinquency without
  an approved metric for that domain.

For empty or unavailable results:

- state `No result is available`;
- state the missing dimension or quality issue;
- do not fill the gap with a comparable but unrequested metric.

## Comparison language

Use verified period-comparison objects:

- lead with the current period and actual value;
- state absolute change first where applicable;
- state MoM and YoY only if both baseline observations exist;
- classify `up`, `down`, or `flat` exactly as produced;
- state a trend only for at least three valid ordered observations;
- for a zero or negative percentage baseline, state `N/A` and explain that
  percent change was not meaningful.

Examples of suitable wording:

- "The operating margin was 120 million MXN in 202412, an increase of 10
  million MXN from 202411."
- "The delinquency amount rate was 4.8%, up 0.6 percentage points MoM and
  1.1 percentage points YoY."
- "Revenue increased 3.2% MoM on a positive prior-month baseline."
- "The latest six-month window is increasing; the result increased in five of
  five non-tied month-to-month movements."

The final examples are templates only. Do not add any number not supplied by
the verified result.

## Anomaly language

Use verified anomaly objects:

- name the metric, population, period, and group;
- state observed value and peer baseline;
- report z-score, IQR fences, or regulatory status only for applied methods;
- distinguish an operational candidate from a confirmed breach;
- include severity and warnings;
- do not describe a statistical anomaly as misconduct, fraud, or a claims
  breach unless the corresponding approved metric and evidence support it.

Examples:

- "The channel's delinquency amount rate is 8.2%, compared with a peer mean of
  4.1% and an upper IQR fence of 7.5%; it is a high IQR outlier."
- "The fraud-loss ratio has an approved threshold breach, but the underlying
  metric and jurisdiction are required in the verified result."
- "The low observed value is not a breach: it remains within the approved
  regulatory threshold."

Again, these are templates. No placeholder or example value may enter a final
report.

## Tone transformations

### Executive

Use:

- "Outcome"
- "Why it matters"
- "Decision"

Keep the primary paragraph under 100 words. Include one material action only
when it is evidence-based and approved.

### Board

Use:

- "Portfolio position"
- "Risk direction"
- "Oversight and control"

Avoid operational detail unless it changes portfolio or regulatory risk.

### Risk analyst

Include:

- exact formula or metric definition;
- numerator and denominator;
- peer count and peer definition;
- method thresholds and thresholds source;
- confidence and warning severity.

### Operations

Name the segment and period, state the deviation, and identify a permitted
verification action:

- "Review the segment's denominator and volume";
- "Validate source coverage".

Do not infer root causes or assign blame.

### Regulator

Use formal, factual phrasing:

- "The reported metric..."
- "The applicable threshold..."
- "The data-quality status..."
- "The result is classified..."

Include effective date and source for threshold findings. Do not assert
compliance where a threshold, jurisdiction, or source is unavailable.

### General

Replace internal terminology with plain definitions:

- "delinquency rate" → "share of enrolled balances/accounts more than 30 days
  overdue";
- "IQR outlier" → "value outside the expected middle-range band";
- "z-score" → "number of standard deviations from the peer average".

Keep the plain-language definition linked to the exact verified metric.

## Safeguards: recommendation rules

Recommendations must be proportionate to evidence:

- for normal results: no special action;
- for a low-confidence or volume-limited result: validate coverage;
- for a medium or high statistical anomaly: investigate peer comparability;
- for a critical anomaly or regulatory breach: report its evidence and limitations;
- for unsupported fraud or claims metrics: report unavailable and do not
  recommend enforcement action.

Use action language that is reversible and review-oriented:
"investigate", "validate", "review", and "escalate" are preferred to
"terminate", "penalize", or "approve" unless the recipient authority and
policy explicitly permit it.

## Required output

Return the narrative and machine-readable metadata:

```json
{
  "recipient": "executive | board | risk_analyst | operations | regulator | general",
  "objective": "decision or report objective",
  "title": "brief editorial title",
  "executive_summary": "highest-priority verified explanation",
  "sections": [
    {
      "heading": "Portfolio position | Trend | Anomaly | Controls",
      "text": "verified narrative text",
      "metric_names": ["metric_name"],
      "periods": ["YYYYMM"]
    }
  ],
  "recommendations": ["review-oriented action"],
  "confidence": "high | medium | low",
  "warnings": []
}
```

The `title` and `executive_summary` must contain no unsupported numbers.
Preserve all source numbers only in `sections` or a source-controlled
appendix. The narrative must remain reproducible: a number verifier should
be able to trace every numeric statement to a source object.

## Forbidden behavior

Do not:

- calculate or re-aggregate figures;
- use example values;
- estimate a missing baseline;
- add causal explanations not supported by data;
- compare different filters or MOB ranges;
- present a low IQR or z-score as no risk;
- present a threshold breach as a confirmed operational root cause;
- replace a missing threshold with an assumed one;
- hide low-volume or low-quality warnings;
- state that an anomaly is fraud or a claim without the approved domain metric;
- claim regulatory compliance without approved jurisdictional evidence;
- repeat every metric without prioritizing the decision.

## Quality checklist

Before returning the narrative, verify that:

1. every metric name exists in the verified source;
2. every period is valid and in `YYYYMM`;
3. every numeric statement matches a verified result;
4. MoM, YoY, and trend baselines are identified;
5. anomaly method and direction are not conflated;
6. regulatory status is only asserted with source evidence;
7. filters and MOB ranges are explicit;
8. volume and data-quality warnings are included;
9. the recipient tone is consistent;
10. recommendations match the evidence;
11. source limitations and warnings are present;
12. no placeholder, example, or invented number remains.