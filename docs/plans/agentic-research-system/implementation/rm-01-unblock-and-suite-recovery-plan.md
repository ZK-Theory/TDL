# RM-01: Unblock and Suite Recovery Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. Write one failing
> public-seam test before each production change. Read
> `../handoffs/26-research-system-suite-red-briefing.md` in full before
> starting — it is the reproduced factual baseline this plan builds on.

**Status:** PROPOSED — dispatch blocked on gates G-RM-1, G-RM-2, G-RM-3
(see rm-00 §3) and on the handoff-26 Defect 1–2 fixes landing on `main`.
**Goal:** Make `tests/research_system` green and affordable on `main`; close the
WP6.1 event-schema currency gap in the direction P-043 fixes (producer emits);
bring `research_system` into the repo's automated quality accounting; and wire a
smoke gate so the producer/schema divergence class fails at the introducing PR.
**Architecture:** The generated WP6.1 event schemas are the accepted, stricter
authority; the runtime producer rises to meet them. The command-submission path
derives `command_schema_id`, `command_schema_version`, and
`command_schema_sha256` from the registered command schema actually used to
validate the submitted command — computed at submit time from registry state,
never caller-supplied, never hard-coded.
**Tech stack:** Python 3.13, frozen dataclasses, jsonschema, pytest, ruff;
existing `research_system.command` / `research_system.store` modules.
**Owner authorization:** P-043 (pending formal entry; direction accepted
2026-07-28). The WP6.1 acceptance record for this repair is written against the
WP6.1 catalogue, not the RM lane.

## Global constraints

- All standing constraints of rm-00 §5 apply.
- Branch `pipe/rm-01-append-path-currency` from approved `main` **after** the
  handoff-26 Defect 1–2 fixes are merged. Verify before branching:
  `git log --oneline -5` must show the schema-registry fix commit. If it has not
  landed, only Task C (config accounting) may proceed, on its own branch
  `pipe/rm-01-quality-accounting`; Tasks A/B/D wait.
- **Do not modify** `research_system/schema_registry.py` (owned by the in-flight
  handoff-26 agent until its PR merges), the WP6.3 accepted-byte files (rm-00
  §5.4), or any file under `.research-system/schemas/core/events/` — the
  generated schemas are the fixed target, not the adjustable variable. If a
  generated event schema itself proves defective (not merely strict), stop
  Partial and escalate; do not relax it.
- No new CLI surface, no provider-related code, no eval-corpus change. The P0
  invariants (37 fixtures / 14 blocked / 122 results / candidate blocked) are
  untouched by this plan; if any task changes them, stop Partial.

## File map

**Modify (Task A):**

~~~text
research_system/command/service.py        # expected producer seam
research_system/store/ledger.py           # only if append-time envelope assembly lives here
tests/research_system/unit/test_command_service.py
~~~

**Create (Task B):**

~~~text
docs/plans/agentic-research-system/implementation/rm-01a-suite-inventory-<date>.md
~~~

**Modify (Task C):**

~~~text
pyproject.toml
~~~

**Create (Task D):**

~~~text
tests/research_system/smoke/test_append_path_smoke.py
~~~

The Task A file map is the *expected* seam. First action of Task A is to confirm
where the event envelope is assembled (`CommandService.submit` →
`ledger.append` per handoff 26). If assembly happens elsewhere, report the
actual seam in the PR description and proceed only if the change stays within
`research_system/command/` + `research_system/store/`; otherwise stop Partial.

## Obligation register

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| R1-1 | P-043 / handoff 26 Defect 3 | Producer emits the three `command_schema_*` fields; schemas not relaxed | Task A |
| R1-2 | handoff 26 | 88 files repo-wide require `command_schema_sha256`; fix must cover every producing path, not just `TaskCreated` | Task A Step 3 sweep + Task D matrix |
| R1-3 | handoff 26 | Full-suite inventory past test 74 has never been observed; record it once affordable | Task B |
| R1-4 | Report 1 F1-A (verified in pyproject.toml:96,103) | `research_system` absent from coverage and ruff first-party | Task C |
| R1-5 | Observer log Obs. 137 | Append-path divergence needs a pre-merge signal with a negative control | Task D; gate G-RM-6 for wiring location |
| R1-6 | rm-00 O-RM-10 | No collision with the in-flight `schema_registry.py` agent | Global constraints |
| R1-7 | Vault discipline | `[PIPELINE]` entry in Pipeline-Overview; session daily note if judgement calls arise | Close-out |

## Research assurance requirements

- **Lanes:** Output/Provenance only. No stochastic operation; no seeds.
- **Machine-checkable claims:**
  - producer truthfulness → the emitted `command_schema_sha256` equals the
    SHA-256 of the exact schema bytes the registry validated the command
    against (test recomputes independently from the file);
  - fail-closed → a command whose schema is unregistered fails at submit, it
    does not append an event with absent/null fields;
  - no caller override → a submitted payload attempting to supply
    `command_schema_*` values is rejected or ignored in favor of
    registry-derived values (pick per existing envelope discipline; test either
    way);
  - divergence detection → Task D smoke fails when a required field is removed
    from the emitted envelope (negative control).
- **Human-review-only:** does the seam place schema-identity derivation at the
  single point every producer flows through, or does it patch one path?
- **Partial criteria:** generated-schema defect discovered; seam outside
  command/store; any P0 invariant drift; any need to edit
  `schema_registry.py`.

## Task A: Producer emits command-schema identity (P-043)

- [ ] **Step 1 — Failing public-seam test.** In
  `test_command_service.py`, add a test that submits a valid command through
  the real `CommandService` and asserts the appended event validates against
  its generated schema (`ars://core/event/TaskCreated` at minimum) **and** that
  `command_schema_sha256` matches an independently recomputed hash of the
  registered command schema file. This must fail on current `main` with the
  three-required-properties error quoted in handoff 26.
- [ ] **Step 2 — Run red.**

~~~powershell
C:/Users/steph/TDL/.venv/Scripts/python.exe -m pytest -q tests/research_system/unit/test_command_service.py -o "addopts=" -p no:cacheprovider -p no:cov
~~~

  Record the failing assertion. A collection error is not the required red.
- [ ] **Step 3 — Implement minimally.** Derive the triple at submit time from
  the registry entry used for command validation. Sweep every event-producing
  call site (`grep -rn "ledger.append"` and any event-factory helpers) and
  route all of them through the single derivation point. Do not special-case
  event types.
- [ ] **Step 4 — Green + no-regression slice.** Re-run Step 2 target plus
  `tests/research_system/unit/test_adapter_parity.py` (handoff 26 says its 16
  setup errors trace to Defects 2→3; after Defect 2's external fix and this
  task, it should collect and run). Record results either way.
- [ ] **Step 5 — Commit.** Subject: `[PIPELINE] P00: emit command-schema identity on the append path (P-043)`.

## Task B: Full-suite inventory (first-ever complete run)

- [ ] Run the entire `tests/research_system` tree to completion with the
  handoff-26 direct-interpreter command; use `run_in_background`/checkpointed
  logging, expect >1 h even after the N+1 fix.
- [ ] Write `rm-01a-suite-inventory-<YYYY-MM-DD>.md`: pass/fail/error per
  module, durations, and a defect list with one-line reproductions. Every
  still-red test gets a disposition: fixed here (only if trivially within Task
  A's seam), filed as a named follow-up, or explained.
- [ ] This inventory is evidence, not a gate: RM-01 closes with the inventory
  *recorded*, not necessarily all-green; remaining reds become owner-visible
  follow-ups in the PR description and the README row.

## Task C: Quality accounting

- [ ] In `pyproject.toml`: append `--cov=research_system` to `addopts`
  (line 103) and add `research_system` to `known-first-party` (line 96).
- [ ] Run `uv run --no-sync ruff check research_system` and fix any
  import-order fallout mechanically (no logic changes).
- [ ] Commit: `[PIPELINE] P00: bring research_system under coverage and first-party accounting`.

## Task D: Append-path smoke gate

- [ ] Create `tests/research_system/smoke/test_append_path_smoke.py`: for a
  representative command set (at minimum one command per event family listed in
  `.research-system/schemas/core/events/`), submit through `CommandService`
  and validate each appended event against its generated schema. Target
  runtime: under 60 s total (use one shared registry instance — the Defect-1
  fix makes this possible).
- [ ] **Negative control (required):** a fixture that strips one
  `command_schema_*` field from an otherwise valid envelope and asserts
  validation fails. The control proves the gate can fire.
- [ ] Wire per G-RM-6 (Stephen chooses: quality-gate command list in plan docs
  vs `.githooks` pre-push). Until decided, the test runs in the normal pytest
  tree — never install anything into `.git/hooks`.
- [ ] Commit: `[PIPELINE] P00: append-path smoke gate with negative control`.

## Close-out

- Update the lane row in `docs/plans/agentic-research-system/README.md` (RM-01
  status) in the same PR (O-RM-18).
- Vault: top-of-page `[PIPELINE]` entry in `04-Methods/Pipeline-Overview.md`
  naming P-043, the seam, and the inventory location; Computational-Log entry
  not required (no numerical result).
- PR description lists: actual seam found, sweep results, inventory summary,
  remaining reds with dispositions.
