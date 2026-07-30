# RM-01: Suite Recovery and Quality Accounting Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. Read handoffs 26/28,
> the accepted 06h close-out, and RR-M3. This plan performs no “pre-06h”
> measurement after 06h has merged.

**Status:** REVISED 2026-07-30 (revision 3). Dispatch is blocked on G-RM-3 and
merged/accepted 06h. Close-out is blocked on G-RM-7.

**Goal:** run the exact post-06h suite against the independently reviewed
pre-06h manifest and preserved 156-node cohort created by 06h Task 0, account
for current-universe additions/removals/renames, bring `research_system` under
quality accounting, and install a live append-path smoke control.

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

## Research assurance

- **Machine-checkable:** accepted baseline identity; exact pre/post commits;
  preserved node IDs; explicit add/remove/rename accounting; smoke negative;
  config-key presence.
- **Human review:** whether the evidence supports a 06h delta rather than a
  test-universe substitution.
- **Partial:** missing/late pre-change record; cohort identity cannot be
  reconstructed; accepted 06h subject differs; P0 invariant moves; smoke
  exceeds the approved gate budget.

## Task A: validate predecessor evidence

Before any test execution:

1. Verify 06h Task 0 records are committed before the first 06h production
   change and bind the exact accepted pre-change commit.
2. Verify the records contain the full node list, the handoff-28 156-node
   cohort, interpreter/command, clean-status evidence, and producer matrix.
3. Verify the public `CommandService.submit` annotation and its guard agree at
   both pre- and post-06h subjects. If not, stop Partial; do not repair history
   inside RM-01.
4. Record the exact 06h merge/acceptance identities in the delta report.

No collection in this task may be labelled “pre-06h”.

## Task B: exact post-06h run and delta

Collect the post-06h node universe, then run the full tree once at the exact
head:

~~~powershell
uv run --no-sync python -m pytest tests/research_system --collect-only -q -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync python -m pytest tests/research_system -q -o "addopts=" -p no:cacheprovider -p no:cov --no-header -rf --durations=15
~~~

Write `rm-01-post-06h-suite-delta-<date>.md` with:

- pre/post commits, commands, interpreters, node totals and outcomes;
- every pre-universe addition, removal and rename;
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

Create a sub-60-second smoke test covering at least generic core, T2, guarded
release, and each command/event family accepted in 06i/06j once those plans
land. Submit through production services and validate emitted events against
registered schemas.

Required liveness control: remove one required `command_schema_*` field from an
otherwise valid command-originated event and prove the gate fails. Include a
T2-specific missing-triple control. G-RM-6 chooses installation in the
quality-gate command list or `.githooks/pre-push`; never `.git/hooks`.

## Close-out

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/smoke/test_append_path_smoke.py tests/research_system/unit/test_release_publication.py tests/research_system/unit/test_wp6_2_t2_runtime.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system
~~~

The full tree is Task B and is not repeated. Update
`docs/plans/agentic-research-system/implementation/README.md`, not the
higher-level ARS README. The PR and vault entry name both exact subjects,
cohort/full-universe results, smoke liveness, distinct defects, and open
G-RM-7 status.
