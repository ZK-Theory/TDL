---
name: schema-contract-design
description: Use when adding a new math-correctness contract to contracts/ - formula, schema, invariant, or output_validation - to author it correctly against the meta-schema, wire its binding test, and manage the pending lifecycle.
---

# Schema / Contract Design

Use this when a research-assurance check has stabilized enough to mechanize as a
`contracts/` artifact. This is the "how to add enforcement" companion to the
audit skills: the audit skill finds the issue, this skill turns the recurring
check into a binding contract.

## Procedure

1. **Pick the kind.** `formula` (a mathematical expression + invariants),
   `schema` (required/forbidden keys on a return value or JSON), `invariant` (a
   non-formulaic condition-consequence), or `output_validation` (dispatch a glob
   of result files to schema contracts).
2. **Author the file** under `contracts/<topic>/<id>.yaml`. `id` is kebab-case and
   MUST equal the filename stem. Required keys: `id`, `kind`, `description`
   (>=20 chars), `spec_citation` (with `source`), `binding`. Include exactly the
   one kind-specific block. `additionalProperties: false` means no extra top-level
   keys.
3. **Ground each formula invariant.** Every `formula.invariants[]` item should
   have exactly one of `expression` or `enforced_by`. Use `expression` for crisp
   mathematical relationships; use `enforced_by` for procedural assertions named
   in the binding test. Do not put both on the same invariant.
4. **Trace pinned literals.** When a variable or required schema key contains a
   fixed count, constant, range, or bound, add `derivation` with the source:
   result JSON path, sample provenance reference, or published formula.
5. **Write the binding.** `binding.test_file` (repo-relative), `binding.test_function`
   (unique across ALL contracts by the one-to-one rule), `binding.must_assert`
   (>=20 chars, the diagnostic message). Enumerate rejection cases as `(a) ...;
   (b) ...` so the claim-to-assertion coverage gate can count them. The
   pre-commit hook runs this test.
6. **Pending lifecycle.** If the binding test is not yet on the base branch, set
   `pending: true`; gate 1 (meta-schema) still runs, while gates 2-4 are skipped.
   Remove `pending` as soon as the test lands. The pending-debt gate warns when
   the binding exists but the contract remains pending.
7. **For output_validation,** set `applies_to_glob` and `schema_contracts` (and
   `file_dispatch` when multiple schemas could apply, `wrapper_key` when the JSON
   wraps the structure under a named field). Schema key types may use `float`,
   `int`, `str`, `bool`, `list[...]`, `dict[str, ...]`, and null-allowed forms
   such as `float | null`; simple `[lo, hi]` bounds are checked by the hardened
   JSON gate.
8. **Manifest.** Add the contract to the relevant `contracts/manifests/<scope>.yaml`.
9. **Verify.** Run `uv run python .claude/hooks/contract_binding_check.py --validate-only`.
   New hardening gates warn by default during retrofit; use `--enforce` only when
   intentionally testing the future blocking mode.

## Output Format

The contract YAML + the manifest entry + a one-line note of pending status.

## Pressure Scenario

A schema dropped fields (T/d/mean) needed for downstream comparison tables; a
schema contract with explicit `required_keys` would have failed the commit.

## Related Skills & Contracts

- Pairs with every audit skill (they identify what to mechanize) and
  `sensitivity-comparison-review` (schema completeness for comparison JSONs).
- Meta-schema: `contracts/schema/contract.schema.yaml`. Gate: `contract_binding_check.py`.
