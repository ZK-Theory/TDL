---
name: schema-contract-design
description: Use when adding a new math-correctness contract to contracts/ — formula, schema, invariant, or output_validation — to author it correctly against the meta-schema, wire its binding test, and manage the pending lifecycle.
---

# Schema / Contract Design

Use this when a research-assurance check has stabilized enough to mechanize as a
`contracts/` artifact. This is the "how to add enforcement" companion to the
audit skills — the audit skill finds the issue, this skill turns the recurring
check into a binding contract.

## Procedure

1. **Pick the kind.** `formula` (a mathematical expression + invariants),
   `schema` (required/forbidden keys on a return value or JSON), `invariant` (a
   non-formulaic condition-consequence), or `output_validation` (dispatch a glob
   of result files to schema contracts).
2. **Author the file** under `contracts/<topic>/<id>.yaml`. `id` is kebab-case and
   MUST equal the filename stem. Required keys: `id`, `kind`, `description`
   (>=20 chars), `spec_citation` (with `source`), `binding`. Include exactly the
   one kind-specific block. `additionalProperties: false` — no extra top-level keys.
3. **Write the binding.** `binding.test_file` (repo-relative), `binding.test_function`
   (unique across ALL contracts — one-to-one rule), `binding.must_assert` (>=20
   chars, the diagnostic message). The pre-commit hook runs this test. **Assert
   VALUE and TYPE, not key presence:** the binding test must go red if the
   producer emits the wrong type or wrong value for a contracted field (a
   `level` that is `{}` instead of `str|null`; a sample count that is `>0`
   instead of the pinned `711`; a gate predicate left undefined). A check that
   only confirms a key exists, a structure is well-formed, or a value is
   "positive" is presence-only and is NOT enforcement.
   - **Make literals equality-checkable.** Any value the contract pins (a token
     like `family = "quasibinomial"`, an exact count, a formula string) must be
     emitted by the producer as that exact literal so the validator can
     equality-check it. A literal that lives only in a contract `description` is
     documentation, not a guard — encode it where the binding test reads it.
   - **Pin the tolerance/predicate.** If the contract has a calibration or
     decision gate, define the predicate and any tolerance explicitly in the
     `expression` (e.g. `calibrated == abs(x - alpha) <= calibration_tolerance`,
     `calibration_tolerance == 0.03`); never leave "approximately" unquantified.
4. **Pending lifecycle.** If the binding test is not yet on the base branch, set
   `pending: true` — gate 1 (meta-schema) still runs; gates 2-4 are skipped.
   Remove `pending` as soon as the test lands.
5. **For output_validation,** set `applies_to_glob` and `schema_contracts` (and
   `file_dispatch` when multiple schemas could apply, `wrapper_key` when the JSON
   wraps the structure under a named field).
6. **Manifest.** Add the contract to the relevant `contracts/manifests/<scope>.yaml`.
7. **Verify.** Run `uv run python .claude/hooks/contract_binding_check.py --validate-only`.

## Output Format

The contract YAML + the manifest entry + a one-line note of pending status.

## Pressure Scenarios

- A schema dropped fields (T/d/mean) needed for downstream comparison tables; a
  schema contract with explicit `required_keys` would have failed the commit.
- A PR #31 CodeRabbit batch exposed a cluster of presence-only escapes: a false
  `735/353` sample count living in contract prose, `level: {}` instead of
  `null`, free-form `params` instead of literal tokens, an "any-positive"
  sample check instead of the pinned `711/342`, and a calibration gate
  referencing an undefined `calibrated` predicate / unquantified tolerance — all
  passed the binding tests. Tightening to value+type assertions and pinned
  literals closes the gap. See `[[Enforcement-must-assert-value-not-key-presence]]`.

## Related Skills & Contracts

- Pairs with every audit skill (they identify what to mechanize) and
  `sensitivity-comparison-review` (schema completeness for comparison JSONs).
- Meta-schema: `contracts/schema/contract.schema.yaml`. Gate: `contract_binding_check.py`.
