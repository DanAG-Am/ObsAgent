# Validate Data Quality

## Purpose

Assess the completeness, uniqueness, validity, range, consistency, coverage,
and analytical reliability of schema-valid CSV data.

Identify null values, duplicate records, out-of-range values, invalid
dates and categorical values, inconsistent aggregates, low coverage,
unusable denominators, and source drift.

This skill assesses and reports quality; it does not repair source values,
fill nulls, remove duplicates, alter aggregates, or create missing observations.

The current local CSV screening tool implements only selected checks: it
counts identical full rows and internal MOB gaps within the observed vintage
range, in addition to structural and reconciliation checks. It does not apply
business-key duplicate rules, validate expected coverage, or certify aggregate
quality. In the panel, a user-supplied minimum is applied only at one selected
MOB; it is not a validated business threshold.

## Required inputs

Request clarification if any required input is missing:

1. schema-passed CSV file or data snapshot;
2. canonical column contract;
3. row-grain definition;
4. duplicate identity and key policy;
5. approved numeric ranges and thresholds;
6. minimum population or denominator threshold;
7. approved vintage and MOB coverage;
8. categorical catalog values;
9. expected row count or snapshot period;
10. available source metadata.

Never invent a range, duplicate policy, catalog label, coverage threshold, or
business rule. Use source policy or return `policy_required`.

## Procedure: quality scope

Assess all canonical columns and derived analytical invariants:

### Dimensions

- `VINTAGE`;
- `MOB`;
- `STRATEGY`;
- `STRATEGY_SEGMENT`;
- `PRODUCT`;
- `CHANNEL`;
- `AGE_TAG`;
- `SCORE_TAG`.

### Additive measures

- `ACCOUNTS`;
- `CREDITLINESAMTS`;
- `ENRACCTS`;
- `OVER30ACCTS`;
- `OVER30AMTS`;
- `GCLAMTS`;
- `NCLAMTS`;
- `RECOVERYAMTS`;
- `ENRAMTS`;
- `REVENUE`;
- `EXPENSES_ACQ`;
- `EXPENSES_ECM_VAR`;
- `EXPENSES_ECM_FIX`;
- `EXPENSES_TOTAL`.

Assess quality at both row level and aggregate snapshot level.

## Procedure: null and missing values

Check every required column for:

- blank strings;
- whitespace-only strings;
- CSV null representations;
- missing row values;
- null-like source tokens;
- missing observations for an expected vintage/MOB combination.

Distinguish:

- `null`: value is missing;
- `zero`: value is present and equal to zero;
- `empty result`: no source row matched an aggregate query;
- `not_applicable`: a rule does not apply to the observation.

Never replace null with zero. Never treat an empty result or no-match query
as a missing numeric row when the source did not include an observation.

Calculate missing-value metrics:

```text
missing_count
missing_rate = missing_count / total_observation_count
```

For derived rates, preserve numerator and denominator coverage. A non-empty
numerator with a zero denominator is a quality issue, not a numeric ratio.

## Procedure: duplicate records

Apply the approved grain:

```text
VINTAGE
STRATEGY
STRATEGY_SEGMENT
PRODUCT
CHANNEL
AGE_TAG
SCORE_TAG
MOB
```

A duplicate is a second or later record that matches every identity key in
the approved duplicate policy.

Report:

- exact duplicate count;
- duplicate key fields;
- conflicting duplicate values;
- total row impact;
- whether duplicates are identical or contradictory.

Do not remove duplicates in this skill. Contradictory duplicate records must
be rejected or flagged according to the source policy.

## Procedure: out-of-range values

Apply structural and approved policy ranges.

### Core range rules

- `VINTAGE`: valid integer `YYYYMM`;
- `MOB`: non-negative integer;
- count measures: non-negative;
- portfolio amounts: non-negative;
- `REVENUE`: non-negative unless an approved source contract allows otherwise;
- denominators: non-negative and not necessarily required to be non-zero;
- categorical values: non-empty and in the approved catalog when a catalog is
  available.

### Derived cross-field checks

Check for logical inconsistencies:

- `OVER30ACCTS > ENRACCTS`;
- `OVER30AMTS > ENRAMTS`;
- `GCLAMTS > ENRAMTS` if the approved policy requires it;
- `RECOVERYAMTS > GCLAMTS` if the approved policy requires it;
- `ENRACCTS > ACCOUNTS` if the source contract requires enrolled accounts
  to be a subset of accounts;
- `CREDITLINESAMTS < ENRAMTS` if the source contract defines enrolled amount
  as a utilization subset;
- `EXPENSES_TOTAL` does not reconcile with approved component expenses;
- duplicate totals produce a value inconsistent with the source grain.

Do not assume a relationship is invalid without an approved business rule.
Cross-field issues with no policy must be flagged as `policy_required`, not
invented as failures.

## Procedure: statistical outliers

Statistical outlier checks are limited to screening. They do not prove fraud,
delinquency deterioration, claims, or misconduct.

Use a preconfigured method:

- IQR for skewed or non-normal distributions;
- z-score for sufficiently large, approximately normal distributions;
- source-approved thresholds for regulatory or business limits.

Record method, sample size, mean or quartiles, threshold, and direction.
Do not use schema text or narrative language as the result.

An outlier is never removed automatically. It remains in the source and is
classified for review or analytical exclusion only under approved policy.

## Procedure: coverage and completeness

Measure:

- row count;
- expected versus observed vintages;
- observed MOB coverage;
- categorical coverage;
- account and denominator coverage;
- missing vintage/MOB combinations;
- duplicate-key coverage;
- available source coverage information.

Coverage may be incomplete but not invalid. Escalate when:

- a required vintage, MOB, segment, or denominator is missing;
- data stops before the expected reporting period;
- expected dates exist outside the source snapshot;
- a small population makes a derived rate unstable;
- the denominator is zero or below the minimum-volume threshold;
- multiple required periods have insufficient rows.

Do not fill missing observations or connect non-comparable trend points.

## Procedure: consistency checks

Check for source drift and internal consistency:

1. stable column names and data types;
2. stable categorical labels;
3. stable row grain;
4. stable units and currency scale;
5. additive totals match the aggregate grain;
6. repeated vintage/MOB observations do not change unexpectedly;
7. denominator definitions remain unchanged between periods.

If the source version or contract changes, label the file
`schema_changed` or `definition_changed` and require review.

## Safeguards: severity and status

Assign issue severity independently of the quality status:

| Severity | Meaning |
|---|---|
| `error` | required contract or data invariants fail |
| `warning` | usable data with a material limitation |
| `review` | policy, source, or interpretation is unavailable |
| `info` | expected state or low-risk data note |

Use overall status:

- `passed`: required checks pass and no material issue exists;
- `warning`: usable but with documented quality limitations;
- `rejected`: required checks fail or the snapshot may not be published;
- `policy_required`: source policy or result is unresolved.

A `warning` does not justify silently filtering, dropping, or normalizing rows.

## Safeguards: remediation rules

Allowed remediation is limited to traceable, approved transformations:

- canonicalize only approved categorical mappings;
- parse only approved date representations;
- reject or quarantine invalid rows;
- de-duplicate only by an explicit policy;
- exclude low-volume observations only by an explicit analytical rule;
- document every changed or excluded row.

Do not:

- fill nulls with zero;
- impute missing KPIs;
- interpolate time-series gaps;
- merge labels with no catalog mapping;
- infer product, channel, vintage, MOB, age, or score;
- alter source numerators or denominators;
- publish a snapshot while required quality checks fail.

## Required output

Return a structured data-quality result:

```json
{
  "status": "passed | warning | rejected | policy_required",
  "file": "local path or storage reference",
  "row_count": 0,
  "valid_row_count": 0,
  "missing_row_count": 0,
  "duplicate_row_count": 0,
  "rejected_row_count": 0,
  "coverage": {
    "observed_vintages": [],
    "missing_vintages": [],
    "observed_mob_values": [],
    "missing_mob_values": [],
    "categorical_coverage": {}
  },
  "metrics": {
    "null_count": 0,
    "null_rate": 0,
    "duplicate_rate": 0,
    "out_of_range_count": 0,
    "zero_denominator_count": 0,
    "below_minimum_volume_count": 0
  },
  "issues": [
    {
      "code": "null_value | duplicate_record | out_of_range | invalid_category | zero_denominator | missing_vintage | missing_mob | inconsistent_total | policy_required",
      "severity": "error | warning | review | info",
      "row": null,
      "column": null,
      "value": null,
      "count": 0,
      "rate": null,
      "message": "specific quality finding"
    }
  ],
  "warnings": []
}
```

Do not report an issue code if the underlying source evidence is unavailable.
Distinguish source fields with no observations from fields with observed
zeros.

## Forbidden behavior

Do not:

- replace nulls or missing observations with zero;
- drop duplicate records automatically;
- remove outliers without approved policy;
- infer an invalid date or categorical label;
- recalculate a rate from a rounded displayed value;
- compare incomparable periods or MOB ranges;
- invent business thresholds or catalog values;
- merge duplicate keys by silent summing;
- alter numerator or denominator semantics;
- publish a snapshot with unresolved required quality failures;
- suppress low-volume or low-coverage warnings;
- label statistical outliers as fraud or claims.

## Quality checklist

Before returning the quality result:

1. row grain and duplicate identity are explicit;
2. all required dimensions and measures were assessed;
3. null and zero values are distinguished;
4. duplicate records are counted and not silently removed;
5. out-of-range and cross-field violations are traceable;
6. vintage and MOB coverage are reported;
7. denominators and minimum-volume limits are considered;
8. categorical values are compared only with an approved catalog;
9. available source drift is assessed;
10. issue severity and overall status are consistent;
11. unresolved policy findings are reported;
12. source rows and available metadata remain intact.