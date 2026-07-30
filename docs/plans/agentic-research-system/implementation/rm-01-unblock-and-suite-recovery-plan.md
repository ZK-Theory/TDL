# RM-01: Suite Recovery and Quality Accounting Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. Read
> `../handoffs/26-research-system-suite-red-briefing.md` (defect briefing),
> `../handoffs/28-research-system-suite-baseline-inventory.md` (the measured
> baseline) and `../reviews/adversarial-rm-lane-plan-suite-review-2026-07-29.md`
> §M-9 before starting. **This plan no longer contains the P-043 repair** —
> that is [06h](06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md).

**Status:** REVISED 2026-07-29 (revision 2). The adversarial review returned
`reject` on revision 1: its Task A was unexecutable (C-1) and its baseline was
stale (M-9). Task A has moved to 06h; the baseline method is rebuilt below.
Dispatch blocked on **G-RM-3** (fresh review of the revised suite) and on **06h
merged**. Close-out blocked on **G-RM-7**.
**Goal:** Establish what the `tests/research_system` suite actually contains at
dispatch head, measure the effect of 06h against it truthfully, bring
`research_system` into the repo's automated quality accounting, and wire a smoke
gate so the producer/schema divergence class fails at the introducing PR.
**Owner authorization:** P-044 (accepted 2026-07-28; G-RM-3 and plan-specific
dependencies remain open).

## What changed in revision 2, and why

| Revision 1 | Revision 2 | Driver |
|---|---|---|
| Task A implemented the P-043 producer-emits repair | Removed; 06h owns it | Review C-1: `SchemaRegistry` retains no bytes or path, and the plan forbade the registry change needed to expose them — the plan reached its own Partial stop |
| Handoff 28's 1,515-test tree was the comparator | A fresh dispatch-head collection manifest is the comparator; the 156 handoff-28 nodes are preserved as a named historical cohort | Review M-9: the reviewer counted **1,561 tests** at the review subject; three new modules and material WP6.3 tests landed between `97f447f` and then. Comparing a post-fix run to a different test universe cannot separate new failures from the P-043 delta |
| Exit criterion was a green suite | Green is not claimed while R1-3b is knowingly red | Review M-9: revision 1 promised green while deliberately allowing a known red |
| `pyproject.toml:96,103` cited for the coverage/lint edits | `pyproject.toml:106,113` | Verified 2026-07-29; revision 1's line numbers were stale — the same drift class M-9 raises |

## Global constraints

- All standing constraints of rm-00 §5 apply.
- Branch `pipe/rm-01-suite-recovery` from approved `main` **after 06h has
  merged**; confirm with `git log --oneline -10` before branching. Copy `.env`
  into the worktree immediately.
- **Environment.** A fresh worktree `.venv` is an empty stub and the main-repo
  interpreter lacks `jsonschema`. Provision with
  `uv sync --all-extras --no-install-package petls`, then run pytest via
  `uv run --no-sync`. Do not pipe long background runs through `tail` — output
  buffers until exit.
- **Do not modify** any file under `.research-system/schemas/core/**`, the
  WP6.3 accepted-byte files, or `research_system/schema_registry.py` (06h owns
  it under G-RM-9). This plan changes no production behaviour except
  `pyproject.toml` accounting and one new test module.
- No new CLI surface, no provider-related code, no eval-corpus change. The P0
  invariants (37 fixtures / 14 blocked / 122 results / candidate blocked) are
  untouched; if any task moves them, stop Partial.

## File map

**Create (Task A):**

~~~text
docs/plans/agentic-research-system/implementation/rm-01a-dispatch-head-collection-manifest-<date>.md
~~~

**Task A preflight (read-only, per R1-3a):**

`a681180` repaired the submit-signature guard before this revision, and that
commit is an ancestor of the current plan head. Reverify the guard at dispatch
head; RM-01 owns no signature-guard edit.

**Create (Task B):**

~~~text
docs/plans/agentic-research-system/implementation/rm-01b-post-fix-suite-delta-<date>.md
~~~

**Modify (Task C):**

~~~text
pyproject.toml
~~~

**Create (Task D):**

~~~text
tests/research_system/smoke/test_append_path_smoke.py
~~~

## Obligation register

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| R1-1 | P-043 / handoff 26 Defect 3 | Producer emits the three `command_schema_*` fields; schemas not relaxed | **Moved to 06h Task 2.** RM-01 measures its effect, it does not implement it |
| R1-2 | handoff 26 | Every producing path covered, not just `TaskCreated` | **Moved to 06h Task 4** (producer coverage matrix). RM-01 Task D smoke-tests the outcome |
| R1-3 | handoff 28 + review M-9 | The 156 Defect-3 cases must be shown to move together, against a *current* universe | Task A manifest + Task B delta |
| R1-3a | handoff 28 §"NOT Defect 3" (2) | Stale signature guard pinned `CommandService.submit` return as `Receipt`; actual is `Receipt \| T2Receipt` | **Discharged before this revision by `a681180`.** Task A reverifies the annotation and guard at dispatch head; it does not edit them |
| R1-3b | handoff 28 §"NOT Defect 3" (1) | `test_every_core_schema_declares_closed_object_contract` red because `receipt-v2.schema.json` is absent from a hand-written 13-name literal | **G-RM-7** (hoisted to rm-00 §3 per review M-1). Blocks any "green" claim |
| R1-4 | Report 1 F1-A (verified: `pyproject.toml:106,113`) | `research_system` absent from coverage and ruff first-party | Task C |
| R1-5 | Observer log Obs. 137 | Append-path divergence needs a pre-merge signal with a negative control | Task D; G-RM-6 for wiring location |
| R1-6 | rm-00 O-RM-10 (closed) | Defects 1-2 landed via PR #176/#179 | Historical |
| R1-7 | Review M-9 | The delta must compare both the preserved cohort **and** the full current universe | Task B |
| R1-8 | Vault discipline | `[PIPELINE]` entry in Pipeline-Overview; daily note if judgement calls arise | Close-out |

## Research assurance requirements

- **Lanes:** Output/Provenance only. No stochastic operation; no seeds.
- **Machine-checkable claims:**
  - **collection currency** — the manifest is generated from the dispatch head
    itself, by a recorded command, before any production mutation;
  - **cohort integrity** — the 156 historical node IDs are preserved verbatim
    and each is resolvable (or explicitly recorded as removed/renamed, with the
    commit that did it) in the current universe;
  - **divergence detection** — Task D's smoke fails when a required
    `command_schema_*` field is removed from an emitted envelope.
- **Human-review-only:** does the delta record let a reader who was not present
  distinguish "P-043 worked" from "the universe changed underneath us"?
- **Partial criteria:** any P0 invariant drift; the smoke gate cannot run under
  60 s; more than a handful of the 156 cohort nodes prove unresolvable, which
  would mean the cohort is no longer a usable comparator and the plan needs
  revision rather than improvisation.

## Task A: Dispatch-head collection manifest (before anything else)

The first-ever complete baseline exists (handoff 28: tree `97f447f`, 1:12:45,
1,515 tests, every non-pass attributed). **Do not re-derive it.** But it is no
longer the comparator: the review's read-only collection at `6e7d0e0` found
**1,561 tests**. This task establishes the true comparator.

- [ ] **Preflight (per R1-3a; read-only).** Confirm
  `CommandService.submit` and
  `test_command_service_submit_preserves_public_signature_and_guard_metadata`
  both require `Receipt | T2Receipt`, and record the fixing commit
  (`a681180`) in the collection manifest. This repair already precedes 06h and
  is not RM-01 work. If either assertion has regressed at dispatch head, stop
  Partial and restore the prerequisite before dispatching 06h; do not hide an
  ordering defect inside this post-06h plan.
- [ ] **Step 1 — Collect read-only at dispatch head**, before any production
  mutation, with bytecode/cache/coverage writes disabled:

~~~powershell
uv run --no-sync python -m pytest tests/research_system --collect-only -q -o "addopts=" -p no:cacheprovider -p no:cov
~~~

- [ ] **Step 2 — Record** `rm-01a-dispatch-head-collection-manifest-<date>.md`:
  the exact commit, the full node-ID list with its total, and the delta in test
  *count* versus handoff 28's 1,515 and the review's 1,561, with the modules
  responsible named. Confirm `git status` is unchanged by collection.
- [ ] **Step 3 — Preserve the historical cohort.** Extract the 156 Defect-3
  node IDs from handoff 28 into a named section of the same document. For each,
  record whether it resolves in the current universe; anything unresolvable
  gets the commit that removed or renamed it. This is what makes Task B's claim
  falsifiable.
- [ ] **Step 4 — Commit.** `[PIPELINE] P00: dispatch-head collection manifest and preserved Defect-3 cohort`.

## Task B: Post-06h delta run

- [ ] After 06h has merged, run the full tree once at the exact head, in the
  provisioned worktree venv, `run_in_background` with file logging (not piped
  through `tail`); expect roughly an hour:

~~~powershell
uv run --no-sync python -m pytest tests/research_system -q -o "addopts=" -p no:cacheprovider -p no:cov --no-header -rf --durations=15
~~~

- [ ] Write `rm-01b-post-fix-suite-delta-<date>.md` reporting **both**
  comparisons (R1-7): (a) the preserved 156-node cohort — handoff 28 predicts
  all 156 move together, which is the falsifiable prediction under test; and
  (b) the full current universe against Task A's manifest, so failures in the
  ~46 tests that did not exist at `97f447f` cannot be mistaken for P-043
  residue in either direction.
- [ ] Any red outside both accounts is a distinct defect: isolate it, file it
  as a named follow-up, do not fold it into 06h.
- [ ] **Do not claim the suite is green.** R1-3b is knowingly red pending
  G-RM-7; state that explicitly in the record and the PR.
- [ ] Commit: `[PIPELINE] P00: post-06h suite delta against dispatch-head manifest`.

## Task C: Quality accounting

- [ ] In `pyproject.toml`: add `research_system` to `known-first-party`
  (**line 106**) and append `--cov=research_system` to `addopts`
  (**line 113**). Verify the line numbers before editing — revision 1 cited
  96/103, which were already stale.
- [ ] Run `uv run --no-sync ruff check research_system` and fix import-order
  fallout mechanically. No logic changes; if a fix would change behaviour, stop
  and report it instead.
- [ ] Commit: `[PIPELINE] P00: bring research_system under coverage and first-party accounting`.

## Task D: Append-path smoke gate

- [ ] Create `tests/research_system/smoke/test_append_path_smoke.py`: for a
  representative command set — at minimum one command per event family wired by
  06h, plus `TaskCreated` — submit through `CommandService` and validate each
  appended event against its generated schema. Target under 60 s total; use one
  shared registry instance (the Defect-1 fix makes this possible).
- [ ] **Negative control (required):** strip one `command_schema_*` field from
  an otherwise valid envelope and assert validation fails. The control proves
  the gate can fire; a gate never watched to fail is not a gate.
- [ ] Wire per **G-RM-6** (Stephen chooses: quality-gate command list vs
  `.githooks` pre-push). Until decided, the test runs in the normal pytest
  tree. **Never install anything into `.git/hooks`** — `core.hooksPath` is
  `.githooks` and `.git/hooks` is silently ignored.
- [ ] Commit: `[PIPELINE] P00: append-path smoke gate with negative control`.

## Close-out

- Targeted verification, exactly:

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/smoke/test_append_path_smoke.py tests/research_system/unit/test_release_publication.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system
~~~

  The full tree runs once, as Task B — not again at close-out.
- Update the RM-01 row in `docs/plans/agentic-research-system/README.md` in the
  same PR (O-RM-18).
- Vault: top-of-page `[PIPELINE]` entry in `04-Methods/Pipeline-Overview.md`
  naming the manifest and delta records and the smoke gate. No
  Computational-Log entry (no numerical research result).
- PR description lists: the collection-manifest totals and their drift from
  both prior counts, the cohort result, any newly isolated defects with
  dispositions, and the **open G-RM-7 decision** — stated as open, not as
  resolved by the Worker.
