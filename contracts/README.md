# Contracts — math-correctness enforcement framework

This directory holds machine-checkable contracts that pin the mathematical
intent of code in this repository against its implementation. Contracts
exist because **prose specifications are interpretable**: a reader (human
or LLM agent) can read a precisely-written methodological prescription
and still implement code whose numerical behaviour diverges from what
the prose said. Contracts close that gap by stating the claim in a
structured form, binding it to a test, and refusing commits that break
the binding.

The framework is intentionally APM-agnostic. The contracts directory is
a tracked top-level directory; everything here travels with worktrees
through normal git semantics. If the project changes coordination
systems, only the `manifests/` naming convention is APM-flavoured;
everything else moves unchanged.

## Layout

```text
contracts/
├── README.md                            # this file
├── schema/
│   └── contract.schema.yaml             # meta-schema: validates every contract
├── <topic>/                             # contracts grouped by semantic topic
│   └── <contract-id>.yaml               # one contract per file
└── manifests/
    └── <scope-id>.yaml                  # optional groupings — list contracts in scope
                                         # for a given task / PR / feature
```

Each contract is one YAML file. The filename stem MUST equal the
contract's `id` field. Topic directories group by domain (e.g.,
`stochastic-tests/`, `stage1-output-schemas/`, `topology-invariants/`,
`regression-specs/`) — not by task or stage. A single contract is
referenced by many tasks if many tasks rely on the same claim.

## The four kinds

The contract grammar is locked to four kinds. Adding a fifth requires
retiring an existing one — this is a deliberate cap to prevent the
grammar from becoming its own interpretation problem.

| Kind | Pins | Example |
|---|---|---|
| `formula` | A mathematical expression, its variables, and derived invariants | The Monte Carlo permutation p-value formula `p = (r + 1) / (n + 1)` with the floor invariant `p_min = 1 / (n + 1)` |
| `schema` | The required (and conditionally-required) keys of a function return value, JSON output, or data structure | The Stage-1 aggregate output cell schema with 14 required keys |
| `invariant` | A non-formulaic claim about code behaviour — typically a relationship between inputs, outputs, or internal state | "When `frozen_models` is passed to `_markov_shuffle`, it is forwarded to `ngram_embed` for use in `.transform()` calls" |
| `output_validation` | A glob-pattern dispatch from output files to schema contracts — runtime validation of result files against their declared schemas | All JSONs under `results/trajectory_tda_*/stage1/**/*.json` validate against the stage1 aggregate output schema |

## Authoring a contract

Every contract has a `binding`: a one-to-one link from the contract to a
single pytest test function. The binding is what the pre-commit hook
runs. If the binding fails, the commit is blocked.

`binding.must_assert` should enumerate distinct rejection cases using
lettered clauses: `(a) ...; (b) ...; (c) ...`. The hardening coverage gate
counts these clauses and compares them with negative assertion cases in the
bound test and local validators it calls. This is intentionally heuristic,
but it makes under-specified bindings visible before review.

Formula invariants must be mechanically grounded. Use `expression` for crisp
mathematical relationships such as `n_converged + convergence_failures == B`,
`0 <= p <= 1`, or `n == 711`. Use `enforced_by` for procedural invariants
that cannot honestly be represented as a compact expression, such as seeded
reproducibility, ordering conventions, engine-literal choices, or object
identity checks. Exactly one of `expression` or `enforced_by` should appear
on each `formula.invariants[]` item; during the retrofit this XOR rule is a
warn-mode hardening gate rather than a meta-schema failure.

Pinned literals should carry provenance. `formula.variables.<name>` entries
and `schema_def.required_keys[]` items may set `derivation` to cite where a
constant, count, range, or bound came from: a result JSON path, a
`sample_provenance.fitted` reference, or a published formula. This keeps
contract literals traceable instead of free-typed.

Authorship triggers (when contracts get written):

1. **Plan authoring / amendment** — when a new task is added to the
   Plan that involves numerical / statistical / topological work,
   contracts must be authored as part of the Plan task.
2. **Pre-registration authoring** — when a pre-reg is filed in the
   vault, the parameter values + decision rules emit contract content.
3. **Manager pre-dispatch coverage check** — before each Task Prompt,
   the Manager verifies contract coverage of the work to be done.
4. **Pre-commit hook (forcing function)** — if covered code changes
   without contracts, the hook blocks the commit with a diagnostic.
5. **Spec amendment** — Spec changes propagate to contracts in the
   same edit cycle.
6. **In-chat / post-hoc finding** — when a defect is caught or a new
   requirement is raised, contracts are authored to encode the
   constraint going forward.

Contracts are authored **upstream of the Worker** (Planner, Manager, or
a dedicated extraction agent) — never by the same agent that will write
the implementation, because the same misreading that produces wrong
code would produce a wrong contract. The contract is reviewed by the
User before it is committed.

## How the hook gates a commit

The pre-commit hook performs four checks in order. If any check fails,
the commit is blocked with a diagnostic.

1. **Validate every contract** under `contracts/**/*.yaml` (excluding
   `schema/` and `manifests/`) against `schema/contract.schema.yaml`.
   Catches malformed contracts.
2. **Verify binding presence** — for each contract, the
   `binding.test_file` exists and contains a function named
   `binding.test_function`. Catches contract-vs-code drift.
3. **Run all bindings** — `pytest` against every contract's binding
   test function. Catches contract-vs-implementation drift, including
   the T1.36-class defect where API-surface tests pass but the
   mathematical contract is violated.
4. **Validate output JSONs in commit** — for each `.json` file staged
   in the commit that matches an `output_validation` contract's glob,
   validate the JSON against the referenced schema contract. Catches
   schema-truncation defects at write time. The strengthened hardening
   layer also checks declared value types and simple `[lo, hi]` bounds,
   including null-allowed forms such as `float | null`.

The original four gates remain hard-enforced. New hardening gates run in
warn mode by default so the existing contract tree can be retrofitted without
blocking unrelated commits. Run `.claude/hooks/contract_binding_check.py
--enforce` or set `RA_CONTRACT_GATES=enforce` to make the hardening gates
blocking once the retrofit backlog is cleared.

## Hardening gates

The warn-mode hardening layer reports:

1. **Qualitative-language lint** â€” gate-bearing fields must not rely on
   phrases like "approximately", "roughly", "reasonable", or "within
   tolerance" unless a pinned number appears nearby.
2. **Invariant-enforcement completeness** â€” each formula invariant should
   have exactly one of `expression` or `enforced_by`.
3. **Claim-to-assertion coverage** â€” lettered `must_assert` clauses are
   counted against negative assertion cases in the bound test and local
   validators it calls. Schema contracts also warn when a declared required
   key is not referenced as a string literal in the binding module.
4. **Strengthened JSON validation** â€” output JSON validation checks required
   key values against declared type strings: `float`, `int`, `str`, `bool`,
   `list[...]`, `dict[str, ...]`, and null-allowed unions such as
   `float | null`. It also checks simple numeric range hints written as
   `[lo, hi]` in the type or description.
5. **Pending-debt detection** â€” a `pending:true` contract warns when its
   binding test already exists on the current branch.

During the retrofit period the hardening gates run in warn mode (exit 0) and
do not block commits; enforcement is planned for T0.17 once the backlog is
remediated, gated behind `--enforce` / `RA_CONTRACT_GATES=enforce`. Never use
`git commit --no-verify` — the pre-commit hooks (Ruff lint/format) must run.

## Pending contracts

A contract may set `pending: true` at the top level. When pending, the
contract still validates against the meta-schema (gate 1) but its
binding existence (gate 2), pytest invocation (gate 3), and output JSON
validation (gate 4) are skipped. Use this to land a contract whose
binding test is authored on a feature branch that has not yet merged to
the base branch — the contract is on file, but the hook does not block
on artefacts that legitimately do not exist yet. Clear `pending` (delete
the field) the moment the binding test is available on the base branch.
The pending-debt hardening gate surfaces contracts that appear ready to flip.

## Adding a new topic directory

Topic directories are created on demand. To add a new topic:

1. Create `contracts/<new-topic>/`.
2. Add the first contract.
3. Update this README's example topic list above.

## Retiring a contract

A contract that no longer applies (e.g., the implementation it
constrains has been removed) is moved to `contracts/_retired/` rather
than deleted, with a brief note added to the YAML's `description`
field explaining why and when. The hook does not load contracts from
`_retired/`.

## Cross-references to project documentation

- Methodological mandates: `CLAUDE.md` § "Methodological Mandates" and
  the per-domain `CLAUDE.md` files.
- Notation conventions (paper-facing, different concern): `papers/shared/notation.md`.
- APM rules covering contract authoring: `CLAUDE.md` `APM_RULES { }` block.
- Vault entries documenting framework decisions: see
  `04-Methods/Computational-Log.md` in the Obsidian vault.
