# Detect fraud

## Purpose
Use the C4.5 fraud detector to classify transaction records using the existing
fraud-detection training pipeline.

## Required inputs
- One or more transaction objects containing every model feature.
- Numeric values for `Time`, `V1` through `V28`, and `Amount`.
- The local labeled training dataset at `database/creditcard.csv`.

## Procedure
Call `detectar_fraude` with up to 20 feature-complete transactions. The tool
trains the configured C4.5 tree from the training split on first use and then
returns the classification, score, threshold, and decision path for each row.
The optional `Class` label is not an input feature and must not be used to score
a transaction.

## Forbidden behavior
- Do not invent, infer, or silently omit transaction feature values.
- Do not claim a model prediction or score confirms fraud or proves legitimacy.
- Do not describe the model as independently validated for operational decisions.
- Do not use portfolio aggregates or synthetic examples as fraud evidence.
- If the training dataset or required variables are unavailable, report the
  explicit tool error instead of presenting a successful detection.
