# Select Template

## Purpose

Select an appropriate report template based on the requested report
objective, audience, content, and output format.

The selected template defines the document's structure and presentation
conventions, such as section order, visual hierarchy, typography,
colors, and layout.

This skill selects and returns a compatible template configuration. It
does not generate report content, calculate metrics, render PDF or Excel
files, or publish the final artifact.

Use only templates available in the approved template catalog or
supplied by the configured template repository.

## Procedure: supported template criteria

Evaluate templates using the following criteria:

-   **Report objective**: the purpose of the report and the decision it
    supports.
-   **Recipient**: executive, board, risk analyst, operations,
    regulator, or general audience.
-   **Report type**: portfolio overview, period comparison, anomaly
    analysis, operational report, or another supported type.
-   **Content requirements**: KPI cards, charts, tables, narrative,
    methodology, and metadata.
-   **Output format**: PDF, Excel, or another supported format.
-   **Branding**: approved logo, colors, typography, and organizational
    style guide.
-   **Level of detail**: brief executive presentation or detailed
    analytical documentation.
-   **Template availability**: whether the template exists and is
    compatible with the requested output.

Do not select a template based only on its name when its supported
structure or format is unknown.

## Required inputs

Request clarification or return a validation error if required
information is absent:

1.  **Report objective**: the question or decision the report should
    support.
2.  **Recipient**: `executive`, `board`, `risk_analyst`, `operations`,
    `regulator`, or `general`.
3.  **Report type**: the requested report category or content.
4.  **Output format**: `pdf`, `xlsx`, or another supported format.
5.  **Content requirements**: requested sections, charts, tables, and
    level of detail.
6.  **Branding requirements**: approved organization style guide or
    branding configuration, when applicable.
7.  **Template catalog**: available template identifiers, descriptions,
    supported formats, and versions.

If the objective, recipient, or output format materially affects
template selection and is not supplied, request clarification.

## Procedure: template discovery

Retrieve the available templates from the configured catalog or
repository.

For each candidate template, inspect:

-   template identifier and name;
-   description and intended use;
-   supported report types;
-   supported recipients or audiences;
-   supported output formats;
-   available sections and layout components;
-   branding and style configuration;
-   version and availability status.

Do not invent template identifiers or assume a template exists because a
similar name is known.

If the catalog cannot be accessed, return `template_catalog_unavailable`
rather than selecting an unverified template.

## Procedure: selection rules

Evaluate candidate templates in the following order:

1.  **Format compatibility**: exclude templates that do not support the
    requested output format.
2.  **Objective alignment**: prioritize templates designed for the
    report's primary purpose.
3.  **Audience alignment**: select a structure and level of detail
    appropriate for the intended recipient.
4.  **Content coverage**: confirm that the template supports all
    required sections or components.
5.  **Branding compatibility**: prefer templates that follow the
    approved branding requirements.
6.  **Availability and version**: select an active, supported template
    version.

Choose the candidate that best satisfies the required criteria.

If several candidates are equally suitable, use the approved default
template for the report type and format, if one exists. Otherwise,
return the candidates and request a selection.

Do not silently omit required content to make an incompatible template
appear suitable.

## Procedure: recipient profiles

Use the following recipient profiles to guide selection when the
template catalog contains matching options:

  -----------------------------------------------------------------------
  Recipient               Preferred structure     Level of detail
  ----------------------- ----------------------- -----------------------
  Executive               concise summary, key    brief
                          KPIs, findings, and     
                          decisions               

  Board                   portfolio position,     concise
                          risk direction, and     
                          oversight               

  Risk analyst            metrics, definitions,   detailed
                          numerators,             
                          denominators, peer      
                          comparisons, and        
                          warnings                

  Operations              segment findings,       concise to detailed
                          practical checks, and   
                          next steps              

  Regulator               formal sections,        detailed
                          methodology, source     
                          evidence, and audit     
                          metadata                

  General                 plain-language          concise
                          explanation and key     
                          results                 
  -----------------------------------------------------------------------

These profiles guide selection; they do not change or reinterpret the
underlying data.

## Procedure: compatibility validation

Before returning the selected template:

1.  Confirm that the template is active and available.
2.  Confirm that its output format matches the request.
3.  Confirm that it supports the required report sections.
4.  Confirm that the intended recipient is compatible with its
    structure.
5.  Confirm that required branding assets and style settings are
    available.
6.  Confirm that the template version is recorded.
7.  Identify required sections that cannot be represented by the
    template.

If a required component is unsupported, return a compatibility warning
or request another template. Do not silently discard the component.

## Procedure: output contract

Return a structured template-selection result:

``` json
{
  "status": "selected | needs_clarification | unavailable | incompatible",
  "template": {
    "template_id": "template identifier",
    "name": "template name",
    "version": "template version",
    "output_format": "pdf | xlsx",
    "report_type": "report category",
    "description": "template purpose"
  },
  "selection_context": {
    "objective": "report objective",
    "recipient": "executive | board | risk_analyst | operations | regulator | general",
    "content_requirements": [],
    "branding": "approved branding identifier"
  },
  "supported_sections": [],
  "unsupported_sections": [],
  "warnings": [],
  "alternatives": []
}
```

The example is a schema template, not a real selection result. Populate
template fields only from the available catalog. Omit unavailable
optional fields rather than inventing them.

## Selection explanation

Provide a concise explanation of why the template was selected.

The explanation should identify:

1.  how the template matches the report objective;
2.  why its structure is suitable for the intended recipient;
3.  whether it supports the requested output format;
4.  any required sections or branding elements that are unsupported.

When no template is selected, explain whether clarification, catalog
access, or a compatible alternative is required.

## Safeguards

-   Select only templates from the approved catalog or configured
    repository.
-   Do not invent or fabricate template names, IDs, versions, or
    capabilities.
-   Do not select an inactive or unsupported template.
-   Do not expose internal template paths or repository credentials.
-   Do not use unapproved logos, fonts, colors, or branding assets.
-   Do not change the meaning or priority of analytical findings through
    template selection.
-   Do not remove required warnings, methodology, or audit metadata to
    fit a layout.
-   Preserve the selected template version so the rendered artifact can
    be reproduced.

## Error handling

Return a structured status when:

-   the template catalog is unavailable;
-   no template supports the requested output format;
-   no template matches the report objective;
-   multiple templates are equally suitable and no default exists;
-   the requested recipient or report type is not supported;
-   required branding assets are missing;
-   required sections cannot be represented.

Distinguish between:

-   **Catalog unavailable**: the configured template source cannot be
    accessed;
-   **Template unavailable**: the requested or required template does
    not exist or is inactive;
-   **Incompatible**: a candidate exists but does not support the
    requested format or content;
-   **Needs clarification**: required selection criteria are missing or
    multiple candidates remain equally suitable;
-   **Selected**: one compatible template has been identified and
    validated.

Do not return `selected` when compatibility has not been confirmed.

## Required output

Return:

1.  the selection status;
2.  the selected template identifier, name, and version, when available;
3.  the supported output format;
4.  the report objective and recipient used for selection;
5.  supported and unsupported sections;
6.  the selection explanation;
7.  alternative templates, if relevant;
8.  warnings or clarification requirements.

The result must be sufficient for the downstream rendering skill to
retrieve and apply the exact selected template.

## Forbidden behavior

Do not:

-   generate PDF or Excel files in this skill;
-   create report content or calculate metrics;
-   invent templates or template capabilities;
-   select an incompatible format;
-   silently omit required report sections;
-   use unapproved branding assets;
-   modify verified analytical results or narrative conclusions;
-   claim that a template was selected without confirming its
    availability and compatibility.

## Quality checklist

Before returning the selection result, verify that:

1.  the report objective is understood;
2.  the recipient and output format are known;
3.  the template comes from the approved catalog;
4.  the template is active and its version is recorded;
5.  the template supports the requested report type and format;
6.  required content sections are supported;
7.  branding requirements are satisfied;
8.  unsupported sections and warnings are disclosed;
9.  the selection explanation is consistent with the criteria;
10. the downstream rendering skill can identify and retrieve the exact
    template.