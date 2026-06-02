---
name: sensitivity-comparison-review
description: Use when producing or reviewing sensitivity-analysis or comparison result JSONs — to confirm they retain every field needed for the comparison tables and figures that consume them.
---

# Sensitivity / Comparison Review

Use this for the Output / Provenance lane, focused on comparison and
sensitivity-analysis JSONs. The failure mode is a result file that validates as
well-formed but silently drops a field a downstream comparison table needs, so the
table cannot be built without re-running the analysis.

## Core Check

1. **Downstream-field inventory.** List every field the comparison tables and
   figures consume (e.g. test statistic T, dimension d, mean, p-value,
   per-cell identifiers).
2. **Field presence.** Confirm each is present in the result JSON for every arm /
   cell / probe being compared — not just the headline arm.
3. **Comparability.** Fields are on the same scale and computed the same way across
   arms; per-arm identifiers let rows be matched.
4. **No silent narrowing.** A schema change that drops a field is caught — prefer a
   `schema` contract with explicit `required_keys` over informal review.

## Output Format

Field-by-field **PRESENT / MISSING** across arms, and whether the comparison
table can be built from the JSON as-is.

## Pressure Scenario

LM-sensitivity JSONs dropped the T/d/mean fields needed for the comparison table;
the analysis had to be re-run to recover them.

## Related Skills & Contracts

- Pairs with `result-provenance-review` and `schema-contract-design` (mechanize the
  field requirement as a contract).
- Enforcing contracts: the `*-output-json-validation` dispatch contracts.
