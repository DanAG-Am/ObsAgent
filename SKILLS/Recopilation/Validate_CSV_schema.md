# Validate CSV Schema

## Purpose

Verify that downloaded or retrieved CSV files satisfy the structural and
schema contract before aggregation or analytical use.

Check encoding, delimiter, header names, data types, date representation,
numeric values, and required columns. Files that cannot meet the contract
must be rejected or accompanied by warnings.

This skill validates structure and types; it does not repair or normalize
source data silently. Semantic and row-quality checks belong to
`Validate_Data_Quality`.

## Required inputs

Request clarification if any required input is missing:

1. CSV file path or storage reference;
2. approved encoding;
3. approved delimiter;
4. required and optional column list;
5. column data-type contract;
6. accepted `VINTAGE` date format;
7. numeric locale and decimal separator;
8. maximum file size and maximum row length;
9. missing-value and duplicate-row policy;
10. source metadata when available.

Never infer a required schema or silently rename source columns.

## Procedure: canonical source contract

The repository's known portfolio CSV contract is the following.

### Required text and categorical columns

| Column | Data type | Rule |
|---|---|---|
| `STRATEGY` | string | non-empty after trimming |
| `STRATEGY_SEGMENT` | string | non-empty after trimming |
| `PRODUCT` | string | non-empty after trimming |
| `CHANNEL` | string | non-empty after trimming |
| `AGE_TAG` | string | non-empty after trimming |
| `SCORE_TAG` | string | non-empty after trimming |

Categorical values must be preserved as source values and are not merged,
mapped, or case-normalized during this schema validation step.

### Required integer columns

| Column | Data type | Rule |
|---|---|---|
| `VINTAGE` | integer | exactly `YYYYMM` |
| `MOB` | integer | zero or greater |
| `ACCOUNTS` | integer | zero or greater |
| `ENRACCTS` | integer | zero or greater |
| `OVER30ACCTS` | integer | zero or greater |

### Required numeric columns

| Column | Data type | Rule |
|---|---|---|
| `CREDITLINESAMTS` | decimal number | zero or greater |
| `OVER30AMTS` | decimal number | zero or greater |
| `GCLAMTS` | decimal number | zero or greater |
| `NCLAMTS` | decimal number | zero or greater |
| `RECOVERYAMTS` | decimal number | zero or greater |
| `ENRAMTS` | decimal number | zero or greater |
| `REVENUE` | decimal number | zero or greater |
| `EXPENSES_ACQ` | decimal number | zero or greater |
| `EXPENSES_ECM_VAR` | decimal number | zero or greater |
| `EXPENSES_ECM_FIX` | decimal number | zero or greater |
| `EXPENSES_TOTAL` | decimal number | zero or greater |

If an imported CSV contains an additional known column, it may be retained
but must not override or replace a required canonical column.

## Procedure: encoding and delimiter

Before parsing:

1. inspect the byte sequence for valid UTF-8 or UTF-8 with BOM;
2. reject invalid UTF-8 when UTF-8 is the approved encoding;
3. reject embedded NUL bytes;
4. detect candidate delimiters only from the approved delimiter set;
5. verify a consistent delimiter across data rows;
6. reject files with more than one plausible header match;
7. strip a UTF-8 BOM from the parsed header only.

Default repository convention:

- encoding: UTF-8 or UTF-8 with BOM;
- delimiter: comma `,`;
- header: first row;
- quoted fields: supported;
- quote character: double quote `"`;
- newline: LF or CRLF.

Alternate encodings and delimiters are allowed only when explicitly supplied
by the source contract. Do not guess a legacy encoding or delimiter.

For a semicolon or pipe-delimited source, validate the same header and type
contract after delimiter recognition.

## Procedure: header validation

Parse the header before data:

1. remove only the UTF-8 BOM;
2. reject empty or duplicate column names;
3. reject leading or trailing whitespace in column names;
4. compare headers against the exact canonical required names;
5. report missing and unexpected columns separately;
6. require the header to contain every required column;
7. reject additional unnamed or blank columns;
8. do not case-fold or alias headers during validation.

`VINTAGE` and `VINTAGE ` are different headers. Whitespace or a naming mismatch
is a schema violation, not an automatic correction.

## Procedure: row structure

Every physical data row must satisfy:

- the correct field count;
- no embedded structural newline without CSV quoting;
- no NUL or control-character corruption;
- a non-empty value for every required field;
- no extra field beyond the header;
- no unclosed quoted field.

Use `csv.DictReader` or an equivalent standards-compliant parser. Do not
split rows with raw string operations.

Record the physical file row number and logical record number for every
rejection or review finding.

## Procedure: data types

### Strings

- verify that text fields are decodable strings;
- reject a required text field that is empty after trimming;
- preserve the original string in source metadata;
- report unmapped categorical values to data-quality review.

### Integer values

An integer is valid only when:

- the complete string is numeric;
- the representation has no decimal point;
- the representation has no thousands separator;
- leading `+` is not accepted unless the source contract allows it;
- the value is within the platform or schema range;
- the value is not `NaN`, `Infinity`, or a float representation.

Examples:

- valid: `202401`, `0`, `125`;
- invalid: `2024-01`, `2024.01`, `1,200`, `12.0`, `NaN`.

### Numeric values

The default numeric locale uses:

- decimal point `.`;
- no thousands separator;
- no currency symbol;
- no unit suffix;
- no blanks in numeric strings;
- `NaN` and `Infinity` rejected.

Valid numeric forms may use an optional leading sign when the metric contract
allows negative values. The repository requires most amount fields to be
non-negative.

## Procedure: date formats

The repository source stores the vintage as an integer `YYYYMM`, not a free
text date.

Validate `VINTAGE` with:

```text
length = 6
characters = ASCII digits
month = 01 through 12
year = within the approved source range
```

For example:

- valid: `202401`, `202412`;
- invalid: `2024-01`, `202413`, `202400`, `24-01`, `2024.01`.

Do not convert `VINTAGE` during schema validation unless a separate approved
normalization step explicitly requests conversion.

If the source provides a real calendar date column, it is optional only under
an explicitly approved source contract and must not replace `VINTAGE`.

## Procedure: numerical range checks

Apply only structural range checks in this skill:

- integer and decimal values must be parseable;
- `MOB` must be at least zero;
- count columns must be at least zero;
- portfolio amount columns must be at least zero;
- `REVENUE` must be zero or greater;
- invalid values must not be coerced to zero or discarded.

Approved business or statistical ranges, negative/positive outliers, and
cross-column business rules belong to `Validate_Data_Quality`.

Do not reject a valid zero. A value of zero is not a missing value.

## Rejection and review rules

### Reject immediately

Reject the file if:

- the file cannot be decoded;
- a delimiter or quote structure is invalid;
- the header is duplicate or malformed;
- required columns are missing;
- required columns are duplicated;
- a row has the wrong field count;
- an integer or numeric field is unparsable;
- `VINTAGE` is not a valid `YYYYMM` integer;
- `MOB` or a count column is negative;
- a required amount is negative unless that field is explicitly allowed;
- row-size or file-size limits are exceeded;
- the file contains a structural binary or NUL corruption;
- required values are missing.

### Flag limitations

Report warnings if:

- unexpected optional columns are present;
- an unmapped or low-frequency categorical label appears;
- numeric values are present but unusually structured for the source;
- the encoding or delimiter is alternate and not included in the source
  contract;
- duplicate records are detected but the duplicate policy is not explicit;
- the row count or vintage coverage differs materially from expectation;
- zero denominators or near-zero values are widespread;
- a known required field has a low but non-zero missing-value rate.

Schema review findings do not automatically invalidate the file.

## Safeguards: no silent repair

- do not rename, reorder, or alias columns;
- do not strip zeros or leading numeric zeros;
- do not trim source categorical values during schema parsing;
- do not convert invalid strings to integers or decimals;
- do not fill missing values;
- do not drop duplicate rows;
- do not infer a currency or unit;
- do not parse a date as `VINTAGE` when the contract is only integer `YYYYMM`;
- do not publish a snapshot while required validation fails.

Preserve the original downloaded bytes and source metadata. Normalization,
canonical values, and additive aggregation happen only in later stages.

## Required output

Return a structured schema-validation result:

```json
{
  "status": "passed | rejected | warning",
  "file": "local path or storage reference",
  "encoding": "utf-8 | utf-8-sig | alternate",
  "delimiter": ", | ; | \\t | pipe | unknown",
  "header": ["COLUMN_NAME"],
  "required_columns": ["COLUMN_NAME"],
  "missing_columns": [],
  "unexpected_columns": [],
  "row_count": 0,
  "valid_row_count": 0,
  "rejected_row_count": 0,
  "issues": [
    {
      "code": "missing_column | invalid_encoding | invalid_delimiter | invalid_type | invalid_vintage | negative_value | missing_value",
      "severity": "error | warning",
      "row": null,
      "column": null,
      "value": null,
      "message": "specific validation message"
    }
  ],
  "warnings": []
}
```

Do not include raw secrets or sensitive sample values. Reject or redact
invalid values before placing them in logs.

## Forbidden behavior

Do not:

- silently rename or map column names;
- split CSV rows with unapproved string parsing;
- accept a different delimiter without a source contract;
- decode with a replacement character instead of rejecting invalid bytes;
- convert invalid numeric values to zero;
- fill missing values;
- remove duplicate or negative rows during validation;
- treat a zero as missing;
- infer a date from an invalid `VINTAGE`;
- publish a rejected file;
- mix structural validation with corrective normalization;
- report a file as passed while required rows or columns are invalid.

## Quality checklist

Before returning the validation result:

1. encoding and delimiter are explicitly confirmed;
2. every required canonical column is present;
3. header names have no duplicate or whitespace defects;
4. every row has the expected field count;
5. integer and numeric values parse under the approved locale;
6. `VINTAGE` follows valid `YYYYMM`;
7. `MOB`, counts, and required amounts are non-negative;
8. missing and zero values are distinguished;
9. rejected rows are counted and identified;
10. review findings are separate from rejection findings;
11. the original file is preserved without silent repair;
12. available source metadata is retained.