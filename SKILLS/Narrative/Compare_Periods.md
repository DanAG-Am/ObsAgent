# Compare Periods

## Purpose

Compare portfolio KPIs across monthly and annual periods, calculate month-over-month (MoM) and year-on-year (YoY) variations, and determine whether the
latest trend is increasing, decreasing, or stable.

Use this skill only after the requested period, metric, filters, comparison baseline, and reporting unit are known. The skill compares verified query results;
it does not independently reaggregate, recalculate derived ratios, or invent missing observations.

## Procedure: period conventions

- The time dimension is `vintage`, represented as an integer in `YYYYMM` format.
- Month-over-month (MoM) compares period `M` with the immediately preceding period `M-1`.
- Year-on-year (YoY) compares period `M` with the period 12 months earlier.
- For vintage curves, comparisons must use the same `MOB` or MOB range. For snapshots, no common MOB is needed unless it was requested.
- Additive measures may be summed over all qualifying rows.
- Derived rates and ratios must be calculated by the query tool from their original numerators and denominators. Do not calculate a ratio from displayed or
  rounded period values.
- Period boundaries and filters must remain identical across the current period and every baseline period.

## Required inputs

Request clarification if any of these is absent:

1. **Metric or KPI**: for example `operating_margin`, `delinquency_rate_amount`, `revenue_per_account`, or `accounts`.
2. **Base period**: the latest or requested `YYYYMM`.
3. **Comparison periods**: the immediately previous month and/or the same month in the previous year.
4. **Filters**: product, channel, strategy, strategy segment, age band, score band, and/or MOB range.
5. **Comparison unit**: absolute change, percentage change, or both.
6. **Trend window**: default to the latest 3 or 6 available periods only when no window was specified.
7. **Minimum-volume threshold**: apply the repository standard or the user/request threshold if one is supplied.

Use only catalog values for dimensions. If no filter was requested, analyze the full portfolio represented by the snapshot.

## Procedure: query contract

Use the existing portfolio query tools rather than SQL:

```json
{
  "tool": "portfolio_kpis",
  "filters": {
    "vintage": { "from": 202401, "to": 202412 },
    "mob": { "from": 0, "to": 12 },
    "product": [],
    "channel": [],
    "strategy": [],
    "strategy_segment": [],
    "age_band": [],
    "score_band": []
  }
}
```

For several periods, return one verified result per period under the same filters. For a vintage comparison, use `vintage_comparison` or an equivalent
verified tool with a common MOB. Never vary only the metric denominator between periods.

The response to use must contain:

- the query/tool name;
- normalized filters;
- result rows;
- metric definitions and formula version;
- numerator and denominator fields;
- snapshot ID and refreshed-at timestamp;
- warnings and data-quality status.

## Calculation rules

For every period result `P`, retain both the metric value and its numerator/denominator where applicable.

### Absolute change

```text
absolute_change = current_value - baseline_value
```

Use the same unit as the metric. For percentage/rate metrics, an absolute change can be expressed in percentage points, not percent relative change.
For example, a rate changing from 4.0% to 5.0% is `+1.0 percentage point`.

### Month-over-month variation

```text
MoM absolute change = current_value - previous_month_value
MoM percent change  = (current_value - previous_month_value) / previous_month_value * 100
```

### Year-on-year variation

```text
YoY absolute change = current_value - same_month_previous_year_value
YoY percent change  = (current_value - same_month_previous_year_value) / same_month_previous_year_value * 100
```

For a positive baseline, use the standard signed formula above. For a negative or zero baseline,
percentage-change interpretation is not reliable: report the absolute change and mark the percentage change `N/A`
with `zero_baseline` or `negative_baseline`. Do not silently invert the sign.
Label the result clearly:

- `MoM +2.5%`
- `YoY -1.2%`
- `+1.0 percentage point`
- `+120.00 MXN`

Do not mix percentage-point change with percentage change.

## Trend calculation

Use the ordered, valid observations for the selected window. Sort by `vintage` ascending.

1. Remove missing, null, invalid, or non-comparable observations.
2. Keep at least three valid observations before calling a trend directional. Record if fewer periods are available.
3. Compare the first and last values:

```text
window_absolute_change = latest_value - earliest_value
window_percent_change  = (latest_value - earliest_value) / earliest_value * 100
```

4. Count consecutive month-to-month movements among valid observations.
5. Use the following classification:

- **Increasing**: the latest value is higher than the earliest and at least 60% of the non-tied month-to-month movements are upward.
- **Decreasing**: the latest value is lower than the earliest and at least 60% of the non-tied month-to-month movements are downward.
- **Stable**: neither directional threshold is met, or the latest value differs from the earliest by less than the metric's materiality threshold.
- **Insufficient data**: fewer than three valid ordered observations.

For a two-period result, report only `up`, `down`, or `flat`; do not label it a trend.

### Practical trend tie-breaking

- Ties between consecutive values are neither upward nor downward. Exclude ties from the upward/downward percentage denominator.
- A trend with 60% or more upward movements and net upward change is increasing.
- A trend with 60% or more downward movements and net downward change is decreasing.
- Mixed or flat movement with no net material change is stable.
- State the exact window, observation count, and latest movement so the result can be audited.

## Zero and missing baselines

- If the current or baseline observation is missing or not comparable: state `N/A` for its variation and do not infer a value.
- If the baseline denominator is zero:
  - for a derived rate or ratio, the query must return `null`, `0`, or an explicit `zero-denominator` warning according to the metric contract;
  - do not divide in the narrative skill;
  - calculate absolute change only if the metric value is valid;
  - state that percent change is `N/A (zero baseline denominator)`.
- If a numeric baseline value is zero but a metric contract permits a meaningful absolute and relative value:
  - report absolute change;
  - report percent change as `N/A (zero baseline)`;
  - never assume a 100% or infinite increase.
- If the baseline value is negative, report the signed absolute change and set percentage change to `N/A (negative baseline)` unless a
  product-specific growth convention was approved.
- If the numerator and denominator are zero, use the metric's zero-denominator behavior and do not manufacture a rate.

## Safeguards: data quality and volume

- Do not compare periods with incompatible filters or different MOB ranges.
- Warn when `accounts`, `enrolled_accounts`, or another metric's denominator is below the minimum-volume threshold.
- Warn for missing vintages, duplicate observations, null values, invalid values, and low coverage.
- Do not compare populated and non-populated subsets as if they were like-for-like.
- Hand off critical, severe, or low-confidence variations for human review.
- Include the snapshot ID and refreshed-at timestamp in every report output.

## Required output

Return a period-comparison object for downstream narrative generation:

```json
{
  "metric": "metric_name",
  "filters": {},
  "base_period": "YYYYMM",
  "base_value": 0,
  "mom": {
    "baseline_period": "YYYYMM",
    "baseline_value": 0,
    "absolute_change": 0,
    "percent_change": null,
    "status": "up | down | flat | N/A"
  },
  "yoy": {
    "baseline_period": "YYYYMM",
    "baseline_value": 0,
    "absolute_change": 0,
    "percent_change": null,
    "status": "up | down | flat | N/A"
  },
  "trend": {
    "window": ["YYYYMM"],
    "window_start": "YYYYMM",
    "window_end": "YYYYMM",
    "values": [0],
    "direction": "increasing | decreasing | stable | insufficient_data",
    "window_absolute_change": 0,
    "window_percent_change": null,
    "latest_movement": "up | down | flat",
    "valid_observation_count": 0
  },
  "units": "metric unit or percentage points",
  "warnings": [],
  "snapshot_id": "snapshot identifier",
  "refreshed_at": "ISO-8601 timestamp"
}
```

## Narrative handoff

In the narrative, lead with:

1. the metric and period;
2. the actual and absolute change;
3. MoM and/or YoY percentage change;
4. the trend direction and window;
5. materiality, volume, and data-quality warnings.

Example:

> In 202412, the delinquency amount rate was 4.8%, up 0.6 percentage points MoM and up 1.1 percentage points YoY. It is increasing over the latest
> six available months, with 5 of 5 valid consecutive movements upward. Population coverage is sufficient.

Do not use the example numbers unless they are present in the verified result.

## Forbidden behavior

Do not compare periods with incompatible filters or MOB ranges, calculate
ratios from displayed rows, invent a baseline or observation, mix percentage
points with percentage change, or hide zero-denominator and volume warnings.

Do not present a trend with fewer than three valid observations, and do not
use example values in a final report.

## Quality checklist

Before returning the result:

1. the metric and unit are confirmed;
2. current and baseline periods are valid `YYYYMM` values;
3. filters and MOB ranges are identical;
4. derived values come from verified query tools;
5. zero and missing baselines are handled explicitly;
6. trend observations are ordered and valid;
7. volume and data-quality warnings are included;
8. snapshot ID and refresh time are present.