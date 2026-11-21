# Render PDF

## Purpose

Generate a PDF report from verified portfolio query results and approved
analytical outputs.

The PDF presents the requested information in a readable, structured,
and distribution-ready document. It may include an executive summary,
KPI highlights, tables, charts, comparisons, anomaly findings, narrative
explanations, and supporting metadata.

This skill is responsible for rendering and validating the PDF artifact.
It does not query the repository, aggregate records, recalculate
portfolio metrics, infer missing values, or modify analytical
conclusions produced by upstream skills.

Use only verified inputs and preserve their metric definitions, units,
reporting periods, filters, and data-quality warnings.

## Procedure: supported report content

The PDF may include the following sections when requested and supported
by verified inputs:

-   title page or report header;
-   executive summary;
-   portfolio KPI overview;
-   detailed tables;
-   charts and trend visualizations;
-   period comparisons, including MoM and YoY;
-   anomaly findings;
-   narrative explanations and recommendations;
-   methodology, metric definitions, filters, and data-quality notes;
-   source and snapshot metadata.

Include only metrics and dimensions present in the approved catalog and
supplied by verified source results.

Do not create fraud or claims sections unless corresponding validated
metrics are supplied by upstream tools and approved in the metric
catalog.

## Required inputs

Request clarification or return a validation error if required
information is absent:

1.  **Report objective**: the purpose and decision the PDF should
    support.
2.  **Report title**: the requested title or an approved title generated
    from the report objective.
3.  **Reporting period**: the requested `YYYYMM` period or date range.
4.  **Verified data**: query results and fields required for the
    requested sections.
5.  **Metric definitions**: labels, units, formulas, numerators, and
    denominators where applicable.
6.  **Filters**: normalized product, channel, strategy, strategy
    segment, age band, score band, and/or MOB selections.
7.  **Analytical outputs**: period comparisons and anomaly results when
    requested.
8.  **Narrative output**: executive summary and explanations when
    requested.
9.  **Template and style**: selected template, page size, orientation,
    branding, and formatting rules.
10. **Data metadata**: snapshot ID, refreshed-at timestamp, warnings,
    and data-quality status.
11. **Access status**: confirmation that the requesting user is
    authorized to receive the included data and that the applicable
    access policy has been applied.

Do not assume a reporting period, filter, metric, or section that
materially changes the requested output.

## Procedure: input validation

Before rendering:

1.  Confirm that source results are valid and come from the expected
    query or analytical tools.
2.  Confirm that metric names, dimensions, units, and definitions are
    available.
3.  Confirm that all included results use a consistent snapshot unless
    the report explicitly compares snapshots.
4.  Confirm that filters and reporting periods are consistent across
    sections.
5.  Preserve numerator and denominator metadata for derived rates and
    ratios.
6.  Confirm that comparison and anomaly objects contain their required
    metadata.
7.  Confirm that narrative text comes from a verified narrative output.
8.  Identify null values, missing observations, incomplete coverage, and
    source warnings.
9.  Confirm that the selected template is compatible with the requested
    report type.
10. Confirm that access policy has been applied and the data is
    authorized for the intended audience.

Do not convert missing values to zero or treat an empty query result as
a valid zero-valued result.

## Procedure: PDF assembly

### Document structure

Organize the report according to its objective and selected template.

A typical structure may contain:

1.  **Cover or report header**: title, reporting period, generation
    date, and intended audience where appropriate.
2.  **Executive summary**: the highest-priority verified findings.
3.  **Portfolio overview**: KPI cards or a compact KPI table.
4.  **Detailed analysis**: requested charts, tables, comparisons, and
    trends.
5.  **Anomalies and risk findings**: verified findings, severity,
    confidence, and review status.
6.  **Recommendations**: only recommendations supplied by or supported
    by the verified narrative output.
7.  **Methodology and metadata**: definitions, filters, source snapshot,
    refresh timestamp, and data-quality warnings.

These sections are suggestions, not mandatory pages. Include only
sections relevant to the requested report and available inputs.

### Tables

For each table:

-   use descriptive column headers;
-   preserve source values and units;
-   keep percentage changes and percentage-point changes distinct;
-   use consistent number formats;
-   repeat table headers across pages when supported;
-   avoid splitting a row across pages when possible;
-   keep related labels and values together;
-   indicate when displayed data is truncated or limited.

Do not silently omit material rows or columns.

### Charts and visualizations

Charts must use verified data points and the requested metric
definitions.

For each chart:

-   include a descriptive title;
-   identify the metric and unit;
-   label axes and categories;
-   include a legend when multiple series are present;
-   preserve chronological order for time-series data;
-   keep comparable MOB ranges for vintage comparisons;
-   identify missing or unavailable observations where relevant.

Do not interpolate missing points, invent data, or use visual scales
that misrepresent the source values.

### Narrative and recommendations

Use the verified narrative output when it is supplied.

-   Preserve the intended recipient's tone and level of detail.
-   Keep numerical statements traceable to verified source results.
-   Distinguish observed changes from causal explanations.
-   Include recommendations only when supported by the evidence and
    approved workflow.
-   Preserve human-review requirements and relevant warnings.

Do not generate a new analytical conclusion while rendering the
document.

### Page layout and formatting

-   Use the selected template's typography, spacing, colors, and visual
    hierarchy.
-   Use consistent margins, headers, and footers.
-   Select portrait or landscape orientation according to the content.
-   Keep tables and charts readable at the final page size.
-   Avoid clipping, overlapping, or content outside page boundaries.
-   Add page numbers when appropriate.
-   Use consistent date, currency, percentage, and count formats.
-   Keep important warnings visible.
-   Include report period and source context in the document.

## Procedure: output contract

Generate a valid PDF file and return its file reference and generation
metadata.

The following is the proposed logical metadata structure. It describes
the generation result and is not a replacement for the PDF file.

``` json
{
  "status": "success | failed | partial",
  "file_name": "report_name.pdf",
  "file_type": "pdf",
  "report_title": "report title",
  "report_period": {
    "from": "YYYYMM",
    "to": "YYYYMM"
  },
  "template_id": "selected template identifier",
  "page_count": 0,
  "sections": [
    {
      "name": "Executive Summary",
      "status": "rendered | skipped | failed"
    }
  ],
  "metadata": {
    "snapshot_id": "snapshot identifier",
    "refreshed_at": "ISO-8601 timestamp",
    "filters": {},
    "warnings": []
  },
  "errors": [],
  "file_reference": "generated PDF reference"
}
```

The example is a schema template, not a real generation result. Use only
statuses and metadata confirmed by the rendering process. Do not claim
that a section was rendered if it was omitted or failed.

## Safeguards: data quality and access

-   Include only data authorized for the requesting user and intended
    audience.
-   Respect the output of `apply_access_policy`; do not bypass filtering
    or masking of sensitive columns.
-   Do not include raw personal or sensitive fields unless explicitly
    authorized and required.
-   Preserve source warnings, missing-value states, and data-quality
    status.
-   Do not combine incompatible snapshots or filters.
-   Do not hide low-volume or denominator warnings.
-   Do not present example values as real portfolio results.
-   Keep the PDF traceable to its source snapshot and refresh timestamp.
-   Do not embed hidden or unauthorized data in document metadata,
    annotations, or attachments.

If access authorization or masking cannot be confirmed, do not generate
the PDF for distribution.

## Error handling

Return a structured failure or partial status when:

-   required inputs are missing;
-   source data is invalid or unavailable;
-   metric definitions or units are missing;
-   the selected template is unavailable or incompatible;
-   access policy has not been applied or cannot be verified;
-   the PDF cannot be created or saved;
-   a chart, table, font, image, or layout operation fails;
-   the generated PDF cannot be reopened or validated.

Distinguish between:

-   **No data**: the verified query returned no qualifying observations;
-   **Unavailable**: a requested metric or analytical output is
    unsupported or not supplied;
-   **Validation error**: the input does not meet the PDF contract;
-   **Template error**: the selected template cannot be used;
-   **Generation error**: the PDF could not be created or validated;
-   **Partial**: some requested sections were rendered, but one or more
    sections could not be completed.

Do not report success if the PDF file is missing, corrupted, or cannot
be opened.

## Required output

Return:

1.  the generated `.pdf` file reference;
2.  the generation status;
3.  the report title and reporting period;
4.  the selected template identifier;
5.  the sections rendered or omitted;
6.  the page count;
7.  the snapshot ID and refreshed-at timestamp;
8.  warnings, omitted sections, and generation errors.

The PDF must be readable by the intended recipient and traceable to its
verified source data.

## Forbidden behavior

Do not:

-   query or reaggregate portfolio data in this skill;
-   recalculate authoritative metrics or analytical results;
-   invent values, thresholds, chart observations, or recommendations;
-   convert null or unavailable values to zero;
-   mix incompatible periods, filters, or snapshots;
-   distort values through misleading chart scales or formatting;
-   expose sensitive fields or bypass `apply_access_policy`;
-   claim that a PDF was generated without validating the output file;
-   present template examples or placeholder values as real portfolio
    data.

## Quality checklist

Before returning the PDF, verify that:

1.  the report objective, title, and reporting period are explicit;
2.  all included data comes from verified source results;
3.  metric definitions, units, and filters are preserved;
4.  the selected template is compatible with the report;
5.  all requested sections are rendered or their omission is documented;
6.  tables have readable headers, values, and page breaks;
7.  charts use valid data and clearly labeled axes;
8.  narrative statements match verified outputs;
9.  percentages, percentage points, currency, and counts are formatted
    correctly;
10. missing values and warnings remain visible;
11. access policy has been applied;
12. the PDF opens and renders without clipping or corruption;
13. snapshot ID, refresh time, and generation status are included.