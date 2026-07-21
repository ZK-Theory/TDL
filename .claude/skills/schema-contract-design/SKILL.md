---
name: schema-contract-design
description: Use when adding a new math-correctness contract to contracts/ - formula, schema, invariant, or output_validation - to author it correctly against the meta-schema, wire its binding test, and manage the pending lifecycle.
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - output-provenance
  roles:
    - implementer
  runtime: agnostic
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
   (>=20 chars, the diagnostic message). Enumerate actual rejection cases as
   `(a) ...; (b) ...` only when the binding test exposes matching negative
   validator cases, so the claim-to-assertion coverage gate can count them. For
   positive-only invariants, use an unlettered sentence or bullets: lettered
   positive properties are parsed as rejection cases and create a false coverage
   requirement. The
   pre-commit hook runs this test. **Assert VALUE and TYPE, not key presence:**
   the binding test must go red if the producer emits the wrong type or wrong
   value for a contracted field (a `level` that is `{}` instead of `str|null`; a
   sample count that is `>0` instead of the pinned `711`; a gate predicate left
   undefined). A check that only confirms a key exists, a structure is
   well-formed, or a value is "positive" is presence-only and is NOT enforcement.
   - **Make literals equality-checkable.** Any value the contract pins (a token
     like `family = "quasibinomial"`, an exact count, a formula string) must be
     emitted by the producer as that exact literal so the validator can
     equality-check it. A literal that lives only in a contract `description` is
     documentation, not a guard — encode it where the binding test reads it.
   - **Pin the tolerance/predicate.** If the contract has a calibration or
     decision gate, define the predicate and any tolerance explicitly in the
     `expression` (e.g. `calibrated == abs(x - alpha) <= calibration_tolerance`,
     `calibration_tolerance == 0.03`); never leave "approximately" unquantified.
   - **Fixtures must not depend on gitignored intermediates.** A binding test's
     fixture must be constructible from committed files alone — reading a
     gitignored `PROJ_ROOT` intermediate (e.g. hashing a large results file to
     build a valid-payload skeleton) turns the shared, all-bindings pre-commit
     gate into a cross-task landmine: any Worker committing in a fresh worktree
     trips on another task's absent input. Use a fixed literal (a 64-hex
     placeholder digest, a stub value) for the skeleton needed by negative/
     rejection cases, and gate any assertion that needs the real file behind
     `if PATH.exists(): ... else: pytest.skip(...)` — mirroring the skip pattern
     already used for committed-results tests. A binding test must be runnable
     from a bare checkout with only committed files present.
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
- A `test_mcbif_employment_contract.py` binding test's valid-payload fixture
  called `_sha256()` on a gitignored `results/...` intermediate. In a fresh
  worktree the file was absent, so the fixture raised `FileNotFoundError`
  (hard fail, not a skip) and blocked an unrelated task's commit through the
  shared pre-commit contract gate.

## Related Skills & Contracts

- Pairs with every audit skill (they identify what to mechanize) and
  `sensitivity-comparison-review` (schema completeness for comparison JSONs).
- Meta-schema: `contracts/schema/contract.schema.yaml`. Gate: `contract_binding_check.py`.
## Content-addressed and relational contract checks

- Classify rules as shape-local, cross-field relational, or external-authority equality. Put shape in strict schema; bind every relational/external rule to a semantic validator and negative fixtures.
- Generate heterogeneous arrays from the union of recursively normalized record shapes and validate the entire source contract before content-addressing it.
- Check owned paths and recursive registry discovery before adding manifests or validators; do not widen shared or production surfaces beyond lane authority.
- Keep candidates immutable and `proposed`; derive review and acceptance from independent records bound to the candidate's computed identity.
- Compute repository identity from exact bytes before parsing. Enforce encoding/EOL, calculate Git blob and raw-byte SHA-256, then parse and validate those same bytes.
- Prefer Git's own `hash-object` modes for blob portability tests; avoid general-purpose SHA-1 APIs where scanners prohibit them.
- For large generated payloads, transport bounded chunks with a unique temporary end marker, remove it in the final chunk, then prove byte identity, parseability, schema validity, and canonical hash.

Before delivery, verify that the contract is structurally closed, relationally enforced, ownership-compliant, acyclic in its acceptance dependencies, and byte-identical to its canonical source.
