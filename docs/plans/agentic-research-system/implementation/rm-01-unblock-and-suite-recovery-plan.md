# RM-01: Suite Recovery and Quality Accounting Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. Read handoffs 26/28,
> the accepted 06h close-out, and RR-M3. This plan performs no “pre-06h”
> measurement after 06h has merged. Read PR198-F3 from the PR #198 pre-merge
> review before starting.

**Integrated owner:** WP6.1 / KAN-65 under P-047. This is not a separate RM
delivery or completion lane.

**Status:** REVISED 2026-08-05. G-RM-3 is closed for the accepted plan bytes.
The historical pre-06h comparison cannot now be recreated because its mandated
freeze was not recorded before implementation; that limb is superseded. The
current-universe accounting, append-path family manifest, negative controls,
quality configuration, and live smoke gate remain required WP6.1/Gate 6 work.
Dispatch is blocked on
merged/accepted 06h. Close-out is blocked on G-RM-7.

**Goal:** account for the complete current universe without inventing a missing
pre-change baseline, bring `research_system` under quality accounting, and
install a live append-path family manifest and smoke control at the WP6.1 final
candidate. The absent historical freeze is a non-reconstructible evidence gap,
not something to repair with post-change evidence.

## Global constraints

- Branch `pipe/rm-01-suite-recovery` from approved `main` after 06h merge.
- Verify 06h acceptance subject, merge commit, pre-change commit, producer
  matrix, and baseline/cohort record identities before any run.
- Do not modify core schemas, WP6.2/WP6.3 accepted bytes,
  `schema_registry.py`, or command/replay production code.
- Production behavior changes are limited to `pyproject.toml` accounting and
  the smoke test/gate registration selected by G-RM-6.

## File map

**Read, never regenerate as a post-change baseline:**

~~~text
docs/plans/agentic-research-system/implementation/06h-prechange-producer-matrix-<date>.md
docs/plans/agentic-research-system/implementation/06h-prechange-suite-baseline-<date>.md
~~~

**Create:**

~~~text
docs/plans/agentic-research-system/implementation/rm-01-post-06h-suite-delta-<date>.md
tests/research_system/smoke/append_path_family_manifest.yaml
tests/research_system/smoke/test_append_path_smoke.py
~~~

**Modify:**

~~~text
pyproject.toml
the G-RM-6-selected quality-gate list or .githooks/pre-push
docs/plans/agentic-research-system/implementation/README.md
~~~

## Obligation register

| ID | Obligation | Disposition |
|---|---|---|
| R1-1 | P-043 producer triple | implemented/reviewed by 06h; measured here |
| R1-2 | all command producers including T2 | consume accepted 06h matrix; smoke representative families |
| R1-3 | same 156 nodes observed pre/post | 06h baseline + Task B |
| R1-3a | public signature guard remains current | Task A read-only verification |
| R1-3b | known closed-schema literal defect | G-RM-7; blocks green claim |
| R1-4 | `research_system` in coverage/first-party accounting | Task C by config keys, not volatile line numbers |
| R1-5 | append divergence fails before merge | Task D + liveness negative |
| R1-7 | cohort and full universe both reported | Task B |
| R1-8 | README/vault status current | close-out |
| R1-9 | every production family landed before merge is in the live smoke gate | Task D final-candidate reconciliation + merge-order matrix |

## Research assurance

- **Machine-checkable:** complete current node/family universe; explicit
  producer-family ownership; smoke negative; config-key presence.
- **Human review:** whether the final WP6.1 candidate accounts for every live
  append path without claiming the missing historical comparison.
- **Partial:** any reconstructed or relabelled pre-change evidence; an
  unclassified current family; P0 invariant movement; smoke exceeding the
  approved gate budget.

## Task A: record the historical evidence gap and current subject

Before test execution, record that the required pre-06h freeze and 156-node
cohort were not committed before the production change and therefore cannot be
reconstructed. Bind the exact current WP6.1 candidate and the accepted P-043,
P-045 and G-RM-3 records. Do not create a post-change collection and label it
pre-change.

## Task B: exact current-universe run and accounting

Collect the post-06h node universe, then run the full tree once at the exact
head:

~~~powershell
uv run --no-sync python -m pytest tests/research_system --collect-only -q -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync python -m pytest tests/research_system -q -o "addopts=" -p no:cacheprovider -p no:cov --no-header -rf --durations=15
~~~

Write `rm-01-current-suite-accounting-<date>.md` with:

- current commit, commands, interpreters, node totals and outcomes;
- every current producer and append-path family with its owning test/gate;
- the exact 156-node cohort outcome at both subjects;
- a separate account for every post-only test;
- whether the handoff-28 “move together” prediction held; and
- distinct defects not attributable to P-043.

Do not claim green while G-RM-7 remains open.

## Task C: quality accounting

Edit by semantic key, not line number:

- add `research_system` to Ruff `known-first-party`;
- add `--cov=research_system` to pytest `addopts`.

Reparse `pyproject.toml` after the edit and assert both keys exactly once. Run
`ruff check research_system`; mechanical import-order fixes only.

## Task D: append-path smoke gate

Create a machine-readable family manifest and sub-60-second smoke test covering
generic core, T2, guarded release, and every other accepted production
command/event family present at the **final candidate head**, not the earlier
dispatch head. Each row binds command/event schema IDs and versions, production
submit/builder symbols, reducer, positive test and missing-triple negative.
Submit through production services and validate emitted events against
registered schemas.

Immediately before merge, update the branch onto current `main`, regenerate a
read-only inventory from the accepted runtime bindings and producer matrix, and
fail if any landed production family is absent from the smoke manifest. A
commandless/bootstrap path requires an explicit non-command disposition; it
cannot disappear from the inventory.

06i/06j are not RM-01 dispatch prerequisites. Final ownership is:

| Merge order | Reconciliation owner |
|---|---|
| 06i/06j is already on `main` before RM-01 final candidate | RM-01 consumes its published cases, updates the manifest and runs the gate |
| RM-01 is already on `main` before a successor final candidate | that successor updates and runs the installed manifest/gate before merge |
| candidates overlap and neither is yet on `main` | whichever candidate merges second updates onto current `main`, reconciles all landed families and reruns the gate |

No plan may close or merge using only its original dispatch-head family set.

Required liveness control: remove one required `command_schema_*` field from an
otherwise valid command-originated event and prove the gate fails. Include a
T2-specific missing-triple control and a planted unmanifested-family fixture
that proves completeness reconciliation fails. G-RM-6 chooses installation in
the quality-gate command list or `.githooks/pre-push`; never `.git/hooks`.

## Close-out

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/smoke/test_append_path_smoke.py tests/research_system/unit/test_release_publication.py tests/research_system/unit/test_wp6_2_t2_runtime.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system
~~~

Record the final `main` SHA, manifest hash, family count and successor-case
inputs consumed. The full tree is Task B and is not repeated. Update
`docs/plans/agentic-research-system/implementation/README.md`, not the
higher-level ARS README. The PR and vault entry name both exact subjects,
cohort/full-universe results, smoke liveness, distinct defects, and open
G-RM-7 status.
