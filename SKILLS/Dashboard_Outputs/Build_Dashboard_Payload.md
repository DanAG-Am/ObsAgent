# Build Dashboard Payload

## Purpose

Build a structured JSON payload for the interactive web dashboard from
verified portfolio query results and outputs produced by the analytical
skills.

The payload organizes KPI cards, charts, tables, comparisons, anomaly
findings, narrative sections, filters, and data-quality metadata so the
frontend can render the requested dashboard.

This skill prepares presentation-ready data; it does not query the
repository independently, aggregate records, recalculate metrics, infer
missing values, or invent visualizations and observations.

Use only results that have already been validated by the portfolio query
tools and the applicable analytical skills.

## Procedure: supported data scope

The dashboard may present the portfolio dimensions and measures
supported by the repository and the verified upstream results,
including:

-   portfolio KPIs, such as revenue, operating margin, accounts,
    utilization, expenses, and delinquency;
-   time information, including `vintage` in `YYYYMM` format and `MOB`
    where applicable;
-   segment dimensions, such as product, channel, strategy, strategy
    segment, age band, and score band;
-   period comparisons produced by `Compare Periods`;
-   anomaly findings produced by `Detect Anomalies`;
-   executive explanations produced by `Generate Narrative`.

Include a metric or dimension only when it is present in the verified
source result and approved for the requested dashboard.

The current repository catalog does not confirm dedicated fraud or
claims measures. Do not create fraud or claims cards, charts, or tables
unless the corresponding validated fields and approved metrics are
supplied by the upstream result.

## Required inputs

Request clarification or return a validation error if information
required to build the requested dashboard is absent:

1.  **Dashboard objective**: the question, report, or decision the
    dashboard must support.
2.  **Reporting period**: the requested `YYYYMM` period or date range.
3.  **Metrics and dimensions**: the KPIs and grouping dimensions to
    display.
4.  **Filters**: selected product, channel, strategy, strategy segment,
    age band, score band, and/or MOB range.
5.  **Verified query results**: result rows, metric definitions, units,
    numerators and denominators where applicable.
6.  **Analytical outputs**: period-comparison and anomaly objects when
    those sections are requested.
7.  **Narrative output**: the generated narrative when an explanatory
    section is requested.
8.  **Data context**: snapshot ID, refreshed-at timestamp, warnings, and
    data-quality status.
9.  **Display preferences**: requested cards, charts, tables, ordering,
    and level of detail, when specified.

Do not assume a filter, metric, period, chart type, or dashboard section
that materially changes the requested result. If no segment filter is
requested, preserve the full portfolio represented by the verified
snapshot.

## Procedure: input validation

Before assembling the payload:

1.  Confirm that every metric and dimension exists in the verified
    source result or approved metric catalog.
2.  Confirm that all results use the same snapshot context, reporting
    period, and normalized filters unless the dashboard explicitly
    compares different periods.
3.  Confirm that units, metric definitions, and formula versions are
    available.
4.  Preserve numerator and denominator metadata for derived rates and
    ratios.
5.  Confirm that period-comparison objects use comparable periods,
    filters, and MOB ranges.
6.  Confirm that anomaly objects include their method, peer population,
    severity, warnings, and human-review status.
7.  Confirm that narrative text comes from the verified narrative output
    and does not introduce unsupported values.
8.  Preserve null, missing, unavailable, and not-applicable values as
    distinct states where the source provides that distinction.
9.  Carry forward source warnings and data-quality status.

Do not convert a missing value into zero. Do not treat an empty result
as proof that the metric is zero or that no anomaly exists.

## Procedure: payload assembly

Build the dashboard payload as a presentation layer over the verified
outputs.

### KPI cards

For each requested KPI card, include:

-   metric identifier and display label;
-   verified value and unit;
-   reporting period;
-   numerator and denominator, when applicable;
-   comparison values and changes only when supplied by
    `Compare Periods`;
-   status or warning only when supplied by an approved upstream result.

Do not calculate a new KPI, percentage, average, or comparison while
assembling the card.

### Charts

For each requested chart, include:

-   a stable chart identifier;
-   chart type;
-   title and optional description;
-   metric identifier and unit;
-   category or time field for the horizontal axis;
-   value field for the vertical axis;
-   ordered data points from the verified result;
-   legend or series definitions when multiple series are present.

Use the chart type requested by the dashboard specification. If it is
not specified, select a chart type only when the data structure clearly
supports it; otherwise request clarification.

For time-series charts, preserve chronological order. For vintage
curves, keep the MOB scope comparable. Do not connect missing
observations as if they were measured values, and do not create
interpolated points unless an approved upstream process supplies them.

### Tables

For each requested table, include:

-   a stable table identifier and title;
-   column identifiers and display labels;
-   units and formatting hints where applicable;
-   rows copied from the verified query result;
-   sorting and pagination metadata only when requested or supported by
    the frontend contract.

Do not silently omit rows or columns that are material to the requested
analysis. If the dashboard needs a limited display, preserve the applied
limit and indicate that the table is truncated.

### Comparisons and anomalies

Include period-comparison and anomaly results as received from their
respective skills.

-   Preserve MoM and YoY absolute and percentage changes as separate
    fields.
-   Preserve percentage-point changes separately from percentage
    changes.
-   Preserve trend direction, observation window, and valid observation
    count.
-   Preserve anomaly method, direction, severity, confidence, and
    human-review requirement.
-   Do not reinterpret a statistical anomaly as confirmed fraud, claims,
    misconduct, or a regulatory breach.

If a comparison or anomaly result was not requested or is unavailable,
omit that section or mark it unavailable according to the frontend
contract. Do not fabricate an empty success result.

### Narrative and warnings

Include the verified narrative sections and recommendations when
supplied.

Keep warnings visible and machine-readable. At minimum, retain warnings
about low volume, missing observations, denominator problems, incomplete
coverage, incompatible comparisons, unavailable metrics, and required
human review whenever they appear in the upstream results.

## Procedure: output contract

Return a JSON object that the dashboard frontend can render without
recalculating analytical values.

The following is the proposed logical structure. Field names should
remain consistent with the consuming frontend contract.

``` json
{
  "dashboard_id": "stable dashboard identifier",
  "title": "dashboard title",
  "objective": "requested dashboard objective",
  "period": {
    "from": "YYYYMM",
    "to": "YYYYMM"
  },
  "filters": {},
  "metadata": {
    "snapshot_id": "snapshot identifier",
    "refreshed_at": "ISO-8601 timestamp",
    "data_quality_status": "status returned by source",
    "warnings": []
  },
  "kpi_cards": [
    {
      "metric": "metric_name",
      "label": "display label",
      "value": null,
      "unit": "metric unit",
      "period": "YYYYMM",
      "numerator": null,
      "denominator": null,
      "comparison": null,
      "status": null
    }
  ],
  "charts": [
    {
      "id": "chart identifier",
      "type": "bar | line | pie | other supported type",
      "title": "chart title",
      "description": null,
      "x_key": "category_or_period",
      "series": [
        {
          "data_key": "metric_value",
          "label": "series label",
          "unit": "metric unit"
        }
      ],
      "data": []
    }
  ],
  "tables": [
    {
      "id": "table identifier",
      "title": "table title",
      "columns": [],
      "rows": []
    }
  ],
  "comparisons": [],
  "anomalies": [],
  "narrative": null,
  "warnings": []
}
```

The example defines the payload shape, not actual dashboard data.
Replace placeholders only with values supplied by verified inputs.
Optional sections may be omitted when they were not requested or no
verified result exists.

## Data formatting rules

-   Preserve the source value and its unit.
-   Do not round values during payload construction. Apply display
    formatting only as a presentation hint, without changing the
    underlying value.
-   Keep percentages, percentage points, currency amounts, and counts
    distinct.
-   Preserve `null` when the source value is unavailable or not
    applicable.
-   Preserve the original `YYYYMM` vintage representation unless the
    frontend contract explicitly requires a separate display label.
-   Keep stable metric, chart, table, and dimension identifiers so the
    frontend can map values consistently.
-   Keep category labels aligned with the catalog values returned by the
    source.
-   Do not place explanatory text inside numeric fields.
-   Do not duplicate a derived value under different names if the
    distinction is not defined by the source contract.

## Safeguards: access, privacy, and data quality

-   Build the payload only from data the requesting user is authorized
    to receive.
-   Treat `apply_access_policy` as the responsibility for filtering or
    masking sensitive columns according to the user's profile. This
    skill must not replace or bypass that access-control action.
-   Do not add raw personal or sensitive fields to the dashboard unless
    they are explicitly authorized and required.
-   Do not expose internal source records or fields that are not needed
    by the requested dashboard.
-   Preserve warnings and data-quality status from the source.
-   Do not combine results from different snapshots as if they
    represented one consistent view.
-   Do not compare incompatible filters, periods, populations, or MOB
    ranges.
-   Do not infer that a metric is healthy merely because no anomaly
    object was returned.
-   Keep critical findings and human-review requirements visible to the
    dashboard consumer.

If access authorization or masking status cannot be confirmed, do not
publish the payload. Return an access-validation error for the workflow
to handle.

## Error and unavailable-result handling

Return a structured error or warning when:

-   a required metric or dimension is not in the approved catalog;
-   the requested period or filters are missing or invalid;
-   the source query failed or returned an invalid result;
-   required snapshot metadata is absent;
-   the requested comparison or anomaly output is unavailable;
-   the result contains incompatible snapshots or filters;
-   access policy has not been applied or cannot be verified.

Distinguish between:

-   **Unavailable**: the requested metric or analytical output is not
    supplied or supported;
-   **No data**: the verified query returned no qualifying observations;
-   **Missing value**: an expected field or observation is null or
    absent;
-   **Validation error**: the input does not meet the payload contract;
-   **Access denied**: the user is not authorized to receive the
    requested data.

Do not replace any of these states with zero or an empty chart that
implies a valid result.

## Required output

Return the dashboard payload and its generation status. The workflow
should be able to identify:

-   whether payload construction succeeded;
-   the dashboard identifier and objective;
-   the reporting period and normalized filters;
-   the KPI cards, charts, and tables included;
-   the analytical sections included;
-   the snapshot ID and refreshed-at timestamp;
-   warnings, validation errors, and access status.

A successful payload must be traceable to its verified source results.

## Forbidden behavior

Do not:

-   query, aggregate, or recalculate portfolio metrics in this skill;
-   invent metric values, labels, dimensions, periods, or chart
    observations;
-   convert missing or unavailable values to zero;
-   mix snapshots or incompatible filters;
-   calculate MoM, YoY, trend, anomaly, or derived-rate values again;
-   mix percentage-point changes with percentage changes;
-   suppress data-quality, volume, or human-review warnings;
-   expose sensitive fields or bypass `apply_access_policy`;
-   claim that no anomaly exists merely because no anomaly result was
    supplied;
-   present example or placeholder values as real portfolio data.

## Quality checklist

Before returning the payload, verify that:

1.  the dashboard objective and reporting period are explicit;
2.  every metric and dimension is supported by the verified source;
3.  filters and snapshot context are consistent;
4.  KPI values and units match the source;
5.  derived metrics retain their numerator and denominator metadata;
6.  charts use valid fields and correctly ordered observations;
7.  tables preserve the requested rows and columns;
8.  comparison and anomaly objects are passed through without
    recalculation;
9.  narrative text and recommendations come from verified outputs;
10. missing, unavailable, and invalid results are clearly distinguished;
11. access policy has been applied and sensitive fields are not exposed;
12. warnings, data-quality status, snapshot ID, and refresh time are
    present;
13. the payload follows the consuming frontend's JSON contract. \`\`\`