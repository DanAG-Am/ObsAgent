# Render Excel

## Purpose

Generate an Excel workbook (`.xlsx`) from verified portfolio query
results and analytical outputs.

The workbook presents the requested information in organized worksheets,
with formulas, dynamic tables, and conditional formatting where
appropriate.

This skill is responsible for rendering and formatting the workbook. It
does not query the repository, aggregate records, recalculate portfolio
KPIs, infer missing values, or change the results produced by upstream
analytical skills.

Use only verified inputs and preserve their metric definitions, units,
filters, reporting periods, and data-quality warnings.

## Procedure: supported workbook content

The workbook may contain the following sections when they are requested
and supported by verified inputs:

-   executive summary and KPI results;
-   detailed portfolio data;
-   period comparisons, including MoM and YoY results;
-   trend observations;
-   anomaly findings;
-   narrative explanations and recommendations;
-   filters, metric definitions, and data-quality metadata.

Include only metrics and dimensions present in the approved catalog and
supplied by verified source results.

Do not create fraud or claims worksheets unless the corresponding
validated metrics are supplied by the upstream tools and approved in the
metric catalog.

## Required inputs

Request clarification or return a validation error if required
information is absent:

1.  **Report objective**: the purpose and intended use of the workbook.
2.  **Reporting period**: the requested `YYYYMM` period or date range.
3.  **Verified data**: query results and the fields required for the
    requested worksheets.
4.  **Metric definitions**: labels, units, formulas, numerators, and
    denominators where applicable.
5.  **Filters**: normalized product, channel, strategy, strategy
    segment, age band, score band, and/or MOB selections.
6.  **Analytical outputs**: period comparisons and anomaly results when
    requested.
7.  **Narrative output**: executive summary and explanations when
    requested.
8.  **Workbook preferences**: requested worksheets, ordering,
    formatting, and level of detail.
9.  **Data metadata**: warnings and data-quality status.
10. **Access status**: confirmation that the requesting user is
    authorized to receive the included data and that the applicable
    access policy has been applied.

Do not assume a reporting period, filter, metric, or worksheet that
materially changes the requested output.

## Procedure: input validation

Before creating the workbook:

1.  Confirm that the source results are valid and come from the expected
    query or analytical tools.
2.  Confirm that metric names, dimensions, units, and definitions are
    available.
3.  Preserve source context and do not mix incompatible results.
4.  Confirm that filters and reporting periods are consistent across
    worksheets.
5.  Preserve numerator and denominator fields for derived rates and
    ratios.
6.  Confirm that comparison and anomaly objects contain their required
    metadata.
7.  Confirm that the data is authorized for the requesting user.
8.  Identify null values, missing observations, incomplete coverage, and
    other source warnings.
9.  Validate worksheet names and ensure that the workbook does not
    exceed supported Excel naming or structural constraints.

Do not convert missing values to zero or treat an empty query result as
a valid zero-valued result.

## Procedure: workbook generation

### Worksheet organization

Create worksheets according to the report objective and requested level
of detail.

A typical workbook may contain:

  -----------------------------------------------------------------------
  Worksheet                           Purpose
  ----------------------------------- -----------------------------------
  Executive Summary                   Presents the main KPIs,
                                      comparisons, and key findings

  Portfolio Data                      Contains the detailed verified
                                      query results

  Period Comparison                   Presents MoM, YoY, and trend
                                      results

  Anomalies                           Presents verified anomaly
                                      candidates and their severity

  Definitions & Metadata              Documents metric definitions,
                                      filters, source context, and
                                      warnings
  -----------------------------------------------------------------------

These are suggested worksheet names, not mandatory tabs. Create only the
worksheets supported by the requested report and available data.

Use clear, consistent worksheet names. If a worksheet is not applicable,
omit it instead of creating a misleading empty sheet.

### Dynamic tables

For detailed datasets:

-   use structured Excel tables when appropriate;
-   use descriptive column headers;
-   preserve the source column identifiers or provide an explicit
    mapping to display labels;
-   enable filters on tabular data;
-   keep headers identifiable when scrolling, where supported;
-   preserve all requested rows unless an explicit row limit is applied;
-   document any truncation or excluded data.

Dynamic table ranges should expand when new rows are added within the
workbook. Do not imply that a table automatically refreshes from the
source repository unless a refresh connection has actually been
configured.

### Formulas

Use Excel formulas only for workbook-level presentation or calculations
explicitly required by the workbook specification.

Examples include:

-   totals or subtotals over displayed additive values;
-   counts of displayed records;
-   simple worksheet-level checks;
-   references between cells or worksheets.

Do not recalculate authoritative portfolio metrics, derived rates, MoM,
YoY, trends, or anomaly statistics in Excel. Use the verified values
produced by upstream tools.

For derived rates, preserve the verified numerator and denominator and
display the source-calculated result. Do not calculate a ratio from
rounded displayed values.

Formulas must:

-   reference the correct worksheet ranges;
-   avoid unintended hardcoded assumptions;
-   handle empty or zero-denominator cases according to the metric
    contract;
-   remain understandable and auditable;
-   be checked for formula errors before delivery.

If a formula is not necessary or its inputs are unavailable, use the
verified source value or omit the formula.

### Conditional formatting

Apply conditional formatting only when the rule is defined by the report
specification or an approved business rule.

Examples of suitable uses include:

-   highlighting positive and negative changes;
-   emphasizing values outside approved thresholds;
-   identifying missing or invalid values;
-   visually distinguishing anomaly severity;
-   highlighting low-volume or data-quality warnings.

Do not invent thresholds or use colors to imply a regulatory breach or
confirmed risk without approved evidence.

For comparison metrics, distinguish percentage changes from
percentage-point changes. Use labels and number formats that preserve
this distinction.

### Formatting and readability

-   Use a consistent corporate style when a corporate style guide is
    supplied.
-   Apply clear worksheet titles and column headers.
-   Use appropriate number formats for percentages, percentage points,
    currency, and counts.
-   Preserve source precision in the underlying cell values.
-   Use readable column widths and appropriate alignment.
-   Keep important warnings visible.
-   Avoid decorative formatting that obscures the meaning of the data.
-   Include the reporting period and relevant snapshot context in the
    workbook.

## Procedure: output contract

Generate a valid `.xlsx` workbook and return its file reference and
generation metadata.

The following is the proposed logical metadata structure. It describes
the generation result and is not a replacement for the binary Excel
workbook.

``` json
{
  "status": "success | failed | partial",
  "file_name": "report_name.xlsx",
  "file_type": "xlsx",
  "report_period": {
    "from": "YYYYMM",
    "to": "YYYYMM"
  },
  "worksheets": [
    {
      "name": "Executive Summary",
      "row_count": 0,
      "column_count": 0,
      "description": "Worksheet purpose"
    }
  ],
  "features": {
    "structured_tables": true,
    "formulas": true,
    "conditional_formatting": true
  },
  "metadata": {
    "filters": {},
    "warnings": []
  },
  "errors": [],
  "file_reference": "generated workbook reference"
}
```

The example is a schema template, not a real generation result. Set
feature flags according to what was actually generated. Do not claim
that formulas, tables, or conditional formatting were added if they were
not.

## Safeguards: data quality and access

-   Include only data authorized for the requesting user.
-   Respect the output of `apply_access_policy`; do not bypass filtering
    or masking of sensitive columns.
-   Do not include raw personal or sensitive fields unless explicitly
    authorized and required.
-   Preserve source warnings, missing-value states, and data-quality
    status.
-   Do not combine incompatible snapshots or filters.
-   Do not hide low-volume or denominator warnings.
-   Do not present example values as real portfolio results.
-   Keep the workbook traceable to its source results.

If access authorization or masking cannot be confirmed, do not generate
the workbook for distribution.

## Error handling

Return a structured failure or partial status when:

-   required inputs are missing;
-   source data is invalid or unavailable;
-   metric definitions or units are missing;
-   access policy has not been applied or cannot be verified;
-   the workbook cannot be created or saved;
-   a worksheet, formula, or formatting operation fails;
-   the generated workbook cannot be reopened or validated.

Distinguish between:

-   **No data**: the verified query returned no qualifying observations;
-   **Unavailable**: a requested metric or analytical output is
    unsupported or not supplied;
-   **Validation error**: the input does not meet the workbook contract;
-   **Generation error**: the workbook could not be created or
    validated;
-   **Partial**: some requested sections were generated, but one or more
    sections could not be completed.

Do not report success if the `.xlsx` file is missing, corrupted, or
cannot be opened.

## Required output

Return:

1.  the generated `.xlsx` file reference;
2.  the generation status;
3.  the list of worksheets created;
4.  the reporting period and normalized filters;
5.  warnings, omitted sections, and generation errors.

The workbook must be usable by the recipient and traceable to its
verified source data.

## Forbidden behavior

Do not:

-   query or reaggregate portfolio data in this skill;
-   recalculate authoritative metrics or analytical results;
-   invent values, thresholds, formulas, or worksheet content;
-   convert null or unavailable values to zero;
-   mix incompatible periods, filters, or snapshots;
-   apply conditional formatting that implies unsupported risk or
    compliance conclusions;
-   expose sensitive fields or bypass `apply_access_policy`;
-   claim that the workbook is dynamic or refreshable from the
    repository unless that behavior is implemented;
-   report successful generation without validating the output file.

## Quality checklist

Before returning the workbook, verify that:

1.  the report objective and reporting period are explicit;
2.  all included data comes from verified source results;
3.  metric definitions, units, and filters are preserved;
4.  worksheet names and ordering are valid;
5.  tables contain the intended headers and data ranges;
6.  formulas reference valid cells and contain no errors;
7.  conditional formatting uses approved rules;
8.  percentages, percentage points, currency, and counts are formatted
    correctly;
9.  missing values and warnings remain visible;
10. access policy has been applied;
11. the workbook opens and contains the expected worksheets;
12. warnings and generation status are included.