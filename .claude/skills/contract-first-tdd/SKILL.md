---
name: contract-first-tdd
description: Use when implementing or fixing result-bearing TDL code — a pipeline seam, a null model, a statistical calculation, new output fields, a paper-result script, or provenance hardening — before any implementation code is written.
metadata:
  version: "1.0.0"
  tier: core
  lanes:
    - output-provenance
  roles:
    - implementer
  runtime: agnostic
---

# Contract-First TDD

Ordinary red-green-refactor TDD with a contract layer in front: one behaviour
slice at a time, tested through the public or scientific interface, with the
governing contract resolved before result-bearing code exists. Do NOT use this
to author a math-correctness contract for code you are about to implement —
the implementing agent never authors its own contract (locked 2026-05-27 in
`CONVENTIONS.md`); contracts arrive from upstream via `schema-contract-design`.

## The Scientific Interface

In TDL an interface is not just a function signature. It includes:

- input data stage and sample stage (eligible / complete-case / fitted)
- embedding assumptions and frozen-loadings status
- random seed handling
- null-model order k
- landmark count L and distance metric (with order)
- output schema and provenance fields
- error modes (fail fast — never silently truncate, coerce, or drop)
- performance expectations
- contract binding

Tests exercise this interface — the seam callers actually cross — not private
internals, so they survive refactors.

## Procedure

1. Read the domain vocabulary and every governing contract before writing code.
2. Identify the public or scientific seam the behaviour crosses.
3. Classify: is this result-bearing, mathematical, statistical, null-model, or
   provenance-related? (`research-assurance-triage`)
4. If yes: require the upstream contract, or record an explicit
   "contract not applicable because …" note. Never proceed on "probably fine".
5. Write ONE failing test for ONE behaviour. Watch it fail.
6. Implement the minimal code to green.
7. Next behaviour slice. Refactor only while green.
8. Where a value is contract-pinned, assert the **exact value and type** —
   `n == 711`, `family == "quasibinomial"`, `level` is `str` or `null` never
   `{}` — not key presence, not "> 0". Add a negative case for each
   `must_assert` clause.
9. Run the contract binding check, integration checks, and the result-schema /
   provenance checks if outputs changed.

## Guardrails

- Producers emit contract-pinned fields as exact literal tokens, never
  free-form prose — a literal living only in a contract description is
  documentation, not a guard.
- Result files are date-suffixed and never overwrite an existing file.
- No speculative generalisation; implement the slice the test demands.
- Seeds specified and recorded for anything stochastic.

## Completion Checklist

- [ ] Assurance lane classified.
- [ ] Contract requirement resolved BEFORE implementation (existing /
      requested upstream / documented N/A).
- [ ] One behaviour per cycle; each test seen red before green.
- [ ] Tests cross the public/scientific interface, not private internals.
- [ ] Exact value/type assertions for contract-pinned fields, with negative
      cases.
- [ ] Contract binding + validation commands run green.
- [ ] Output schema / provenance checks run if outputs changed.
- [ ] No speculative generalisation added.

## Escalate Or Stop When

- The needed contract does not exist — request upstream authorship (Planner,
  Manager pre-dispatch, pre-registration, or a dedicated extraction step);
  do not author it yourself.
- A green suite conflicts with a contract or a known benchmark — treat as a
  defect and switch to `tda-diagnosing-computational-defects`.
- The implementation would trigger long stochastic compute — run
  `tda-resource-preflight` before launch.

## Related Skills

`schema-contract-design` (contract authoring, upstream of this skill) ·
`research-assurance-triage` · `tda-diagnosing-computational-defects` ·
`result-provenance-review` · `tda-resource-preflight`.
## High-assurance negative controls

- Perturb each named public producer seam before observation; mutating only a produced dictionary or digest proves serialization sensitivity, not provenance.
- For content-addressed evidence, retain every identity-preimage field, recompute identity at construction, and rebuild release evidence from authoritative execution inputs.
- Diagnose byte mismatches against the task base, attributes, raw hashes, and out-of-tree regeneration before rewriting; separate inherited EOL baselines from semantic drift.
- Put required CLI authority inputs in the parser contract and help surface; test missing-argument parse failure separately from invalid supplied values.
- Test immutable writers under identical and conflicting races. Arbitration keys must match the logical revision key, with exactly one visible value under conflict.
- Attack capabilities after normal binding, across instances, and under replay/reuse; validate instance ownership and consumption at the protected seam.
- Capture long test partitions independently so one timeout cannot erase completed evidence.
- For decorated public APIs, test both runtime signatures and source-visible defaults/annotations; hidden parameters must be optional yet fail closed.
