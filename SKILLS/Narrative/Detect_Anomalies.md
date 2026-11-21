# Detect Anomalies

## Purpose

Identify statistically unusual or policy-breaching observations in portfolio
data, especially for:

- **fraud**;
- **delinquency**;
- **claims**.

Use only verified aggregate or record-level results from the analytical query
tools. This skill does not infer missing fields, calculate ratios from
displayed values, or define business thresholds from assumptions.

## Procedure: supported data scope

The current repository model contains portfolio, delinquency, charge-off,
utilization, expense, revenue, vintage, MOB, product, channel, strategy,
strategy-segment, age-band, and score-band fields.

The current catalog does **not** confirm dedicated fraud or claims measures.
Therefore:

- analyze fraud only when a validated `fraud_*`, incident, loss, or transaction
  field is supplied by the snapshot and approved in the metric catalog;
- analyze claims only when validated `claim_*`, claim count, claim amount,
  reserve, or paid-loss fields are supplied;
- for `delinquency`, use
  `delinquency_rate_amount` or `delinquency_rate_accounts`;
- never treat charge-offs or recoveries as fraud or claims;
- never invent a fraud, claims, or regulatory field or threshold.

If a requested fraud or claims metric is absent, return `unavailable` rather
than a false anomaly.

## Required inputs

Request clarification if any of these is absent:

1. metric or domain (`fraud`, `delinquency`, or `claims`);
2. grouping dimension or peer population;
3. observation period and filters;
4. comparison method (`z-score`, `IQR`, `regulatory threshold`, or a
   combination);
5. minimum population or denominator;
6. materiality threshold, where applicable;
7. approved regulatory threshold and source, for regulatory checks.

Default to IQR when no method is specified only for a multi-segment peer
comparison with at least four valid observations. For time-series data, use
z-score or a controlled rolling baseline with the requested peer period.

Use the existing `anomaly_candidates` tool for IQR over deterministic group
KPI results:

```json
{
  "tool": "anomaly_candidates",
  "metric": "delinquency_rate_amount",
  "group_by": "channel",
  "method": "iqr",
  "minimum_accounts": 1000,
  "filters": {}
}
```

The tool response must include the metric definition, numerators,
denominators, snapshot ID, refreshed timestamp, warnings, and data-quality
status.

## Procedure: observation eligibility

Before testing:

1. remove null, non-numeric, invalid, or non-comparable observations;
2. retain the same filters and denominator definition across the peer set;
3. exclude observations below the minimum population or denominator;
4. keep separate amount-based and account-based delinquency rates;
5. keep separate gross and net charge-off measures;
6. use unrounded values for calculations;
7. mark a denominator of zero as non-comparable.

For derived rates, calculate from original numerator and denominator fields.
Do not calculate a rate from displayed period values or rounded rows.

## Z-score method

Use z-score when the peer population is sufficiently large and approximately
numeric and continuous.

```text
mean = arithmetic mean of valid peer values
standard_deviation = population standard deviation of the peer values
z_score = (observation_value - mean) / standard_deviation
```

For a small sample, use the sample standard deviation only if explicitly
approved and report the convention.

Minimum requirements:

- at least 30 observations for a population z-score;
- use at least 10 observations only when the result is labeled exploratory;
- never run z-score on fewer than 3 valid observations.
- standard deviation must be greater than zero.

Default threshold:

- `|z-score| >= 3.0`: extreme anomaly;
- `2.0 <= |z-score| < 3.0`: significant deviation;
- below `2.0`: no statistical anomaly.

An alternate threshold must be supplied and recorded. Z-score is
direction-sensitive:

- positive z-score: unusually high;
- negative z-score: unusually low.

Example output:

```text
Channel X delinquency amount rate = 8.2%, peer mean = 4.1%, z-score = 3.4.
It is an extreme high deviation.
```

Do not report negative or low anomalies as positive in narrative text.

## IQR method

Use IQR for skewed peer distributions or when a robust, non-parametric
comparison is preferred.

```text
Q1 = 25th percentile
Q3 = 75th percentile
IQR = Q3 - Q1
lower_fence = Q1 - 1.5 * IQR
upper_fence = Q3 + 1.5 * IQR
```

Minimum requirements:

- at least 4 valid observations;
- at least 8 observations is preferred for stable percentiles;
- if the percentile algorithm is not specified, report its convention.

Default classification:

- below `lower_fence`: low IQR outlier;
- above `upper_fence`: high IQR outlier;
- otherwise: not an IQR outlier.

The repository IQR implementation currently uses deterministic split-median
quartiles and requires at least 4 observations. Preserve that implementation
unless an approved query tool supplies a different percentile algorithm.

Do not report an observation outside a fence if:

- it is below minimum volume;
- its denominator is zero or unknown;
- the peer set is incomplete or not comparable;
- `IQR == 0` without a documented policy for the zero-IQR edge case.

## Regulatory thresholds

A regulatory check is valid only when all of the following are available:

- metric name and exact definition;
- jurisdiction or portfolio scope;
- threshold value;
- operator (`>`, `>=`, `<`, `<=`, `==`);
- effective date and source;
- approved grace or reporting period;
- escalation and human-review process.

Never invent a regulatory limit. Do not use another jurisdiction's limit for
the portfolio. Do not treat a value below a floor or above a ceiling as a
threshold breach without the approved operator.

Classification:

- **Regulatory breach**: the observation meets the approved breach operator;
- **Approaching threshold**: within an approved buffer of a threshold;
- **Within threshold**: below/inside the approved bound;
- **Threshold unavailable**: no approved threshold exists.

If both a statistical and regulatory test apply:

- report each method independently;
- an approved threshold breach is never overwritten by z-score or IQR;
- a statistical outlier that is within all thresholds remains an
  operational anomaly candidate;
- suppress neither result due solely to a low population.

## Fraud anomalies

For fraud, use only an approved fraud incidence, fraud loss, fraud case, or
transaction-risk measure.

Evaluate:

1. segment concentration;
2. repeated change over time;
3. peer deviation by channel, product, strategy, age band, or score band;
4. absolute fraud exposure and the rate denominator;
5. z-score/IQR against comparable peers;
6. approved fraud or AML regulatory threshold, if supplied.

Requirements:

- report both counts and amounts where available;
- do not infer fraud intent from a delinquency or charge-off result;
- do not compare raw fraud counts across unequal populations;
- route suspected or severe fraud for human review.

## Delinquency anomalies

Use:

- `delinquency_rate_amount` for overdue amount / enrolled amount;
- `delinquency_rate_accounts` for overdue accounts / enrolled accounts;
- `gross_chargeoff_rate` or `net_chargeoff_rate` when charge-offs are explicitly
  requested.

Evaluate the same peer population and MOB range. For vintage curves, compare
only observations with a common MOB or MOB range.

Flag as materially anomalous only when one or more of these are true:

- z-score or IQR threshold is exceeded;
- an approved regulatory threshold is breached;
- the absolute change is at or above an approved materiality threshold.

Do not use a low charge-off or delinquency result as a proof of portfolio
health when coverage or denominator is poor.

## Claims anomalies

For claims, use only validated claim count, claim amount, paid loss, incurred
loss, reserve, or claims-ratio fields.

Evaluate:

1. claim frequency;
2. claim severity;
3. paid or incurred-loss ratios;
4. segment and period concentration;
5. z-score/IQR against comparable peers;
6. approved insurer or regulatory thresholds.

Do not interpret synthetic product, channel, or credit observations as
insurance claims. No claims analysis may proceed unless the metric is present
and the denominator is defined.

## Safeguards: anomaly severity

Classify severity only after volume and data quality are considered:

| Class | Criteria |
|---|---|
| Critical | approved regulatory breach or severe, verified fraud/claims exposure |
| High | extreme z-score, IQR fence breach, or major approved threshold proximity |
| Medium | significant z-score, low/other IQR outlier, or material change |
| Low | weak statistical deviation without policy or materiality breach |
| Review required | unsupported metric, low volume, missing data, or insufficient peers |

Always apply human-review safeguards for critical anomalies, severe counts or
losses, low denominators, low data quality, or conflicting methods.

## Required output

Return a structured anomaly result:

```json
{
  "domain": "fraud | delinquency | claims",
  "metric": "metric_name",
  "filters": {},
  "group_by": "channel",
  "baseline": {
    "period": "YYYYMM",
    "peer_count": 0,
    "mean": null,
    "standard_deviation": null,
    "q1": null,
    "q3": null,
    "iqr": null
  },
  "candidate": {
    "group_value": "catalog value",
    "period": "YYYYMM",
    "value": 0,
    "numerator": null,
    "denominator": null
  },
  "methods": {
    "z_score": {
      "z_score": null,
      "threshold": null,
      "status": "not_applicable | not_anomaly | anomaly",
      "direction": "high | low | none"
    },
    "iqr": {
      "lower_fence": null,
      "upper_fence": null,
      "status": "not_applicable | not_anomaly | anomaly",
      "direction": "high | low | none"
    },
    "regulatory": {
      "threshold": null,
      "operator": null,
      "source": null,
      "effective_date": null,
      "status": "threshold_unavailable | within_threshold | approaching | breach"
    }
  },
  "severity": "critical | high | medium | low | review_required",
  "confidence": "high | medium | low",
  "warnings": [],
  "human_review_required": false,
  "snapshot_id": "snapshot identifier",
  "refreshed_at": "ISO-8601 timestamp"
}
```

## Narrative rules

Lead with the observation and domain, then explain:

1. the exact metric and peer population;
2. the value and whether it is high or low;
3. z-score, IQR, and/or threshold evidence;
4. numerator, denominator, volume, and period;
5. data-quality or missing-threshold warnings;
6. recommended human review.

Example:

> The [Channel] had a delinquency amount rate of 8.2% against a peer mean of
> 4.1%, a z-score of 3.4, and an upper IQR fence of 7.5%. It is an extreme
> high statistical outlier and requires human review. This description uses
> only verified snapshot values.

Do not use the example numbers unless they appear in verified results.

## Forbidden behavior

Do not invent fraud or claims fields, regulatory thresholds, peer baselines,
or jurisdiction rules. Do not calculate rates from rounded text, treat
charge-offs as fraud or claims, or infer misconduct from a statistical
outlier.

Do not suppress low-volume, denominator, or data-quality warnings.

## Quality checklist

Before returning an anomaly result:

1. the domain and metric are in the approved catalog;
2. the peer population and filters are comparable;
3. the period and MOB scope are explicit;
4. the z-score or IQR method is documented;
5. regulatory evidence includes jurisdiction, source, and effective date;
6. volume and denominator warnings are included;
7. severity and confidence are consistent;
8. snapshot ID and refresh time are present.