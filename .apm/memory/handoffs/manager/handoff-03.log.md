---
agent: manager
outgoing: 3
incoming: 4
handoff: 3
stage: 1
---

# Manager Handoff 3 (Manager 3 → Manager 4)

## Summary

This Manager 3 instance picked up from Manager 2's handoff with T1.37 paused
mid-Task (corrective stop after User caught a math defect post-merge in T1.36).
Manager 2 had deferred the design of a math-correctness enforcement mechanism as
the major upcoming work item; Manager 3's session was entirely devoted to that
work plus landing the related corrective fix on main.

**Stages coordinated:** Stage 1 throughout (Stage 0 essentially Done apart from
T0.3 paused; no Stage 2/3/4 work this session).

**Tasks reviewed:** None. No Worker reports were processed this session — the
T1.37 work remained paused throughout. The Worker (tda-agent instance 1) staged
their own Handoff log + bus prompt for the future instance 2 mid-session.

**Dispatch cycles completed:** Zero formal Task Bus dispatches. The User
explicitly chose Manager-implements over Worker-dispatched for the contracts
framework infrastructure work.

**Significant actions taken (all by Manager 3 inline; not Worker-dispatched):**

- **Math-correctness contracts framework designed end-to-end** through extended
  collaborative discussion with the User. Four contract kinds locked (formula,
  schema, invariant, output_validation), no extension without retirement. One
  contract → one binding test. Hook runs all bindings on every commit.
  Ambiguities surface for review. Pre-regs generate fresh contracts. Project-
  wide scope. Hard-enforced from day one. Six authorship triggers covering the
  full lifecycle (Plan, pre-reg, Manager pre-dispatch coverage check, hook as
  forcing function, Spec amendment, in-chat post-hoc finding). Contracts
  authored upstream of the implementing agent — never by the agent that will
  write the code.

- **`contracts/` framework directory at repo root** (NOT under `.apm/`) so it
  travels with worktrees through normal git semantics and survives replacement
  of APM as the coordination system. Six T1.36-targeted contracts authored as
  the worked example exercising all four kinds:
  `stochastic-tests/monte-carlo-permutation-p-value.yaml`,
  `stochastic-tests/monte-carlo-permutation-p-value-legacy.yaml`,
  `stage1-output-schemas/stage1-aggregate-output-cell.yaml`,
  `stage1-output-schemas/stage1-output-json-validation.yaml`,
  `topology-invariants/frozen-loadings-null-threading.yaml`,
  `topology-invariants/frozen-loadings-transform-only.yaml`. Plus
  `contracts/manifests/T1.36.yaml` grouping them.

- **Validator + pre-commit hook implemented.**
  `.claude/hooks/contract_binding_check.py` (440 LOC) runs four gates:
  meta-schema validation, AST-checked binding existence + one-to-one
  enforcement, pytest invocation of all active bindings, JSON schema validation
  of staged output files via `wrapper_key` descent + positive-filter
  `file_dispatch`. `.claude/hooks/git-pre-commit.sh` shell wrapper invokes via
  `uv run`. `install-git-hooks.py` updated to register `pre-commit` alongside
  the existing `commit-msg` hook. Hook installed at `.git/hooks/pre-commit` and
  is now active on every commit.

- **Smoke pass surfaced and fixed two framework design issues** during Phase B:
  *(1)* Persisted JSONs wrap the `aggregate_combined()` return value under a
  `result` field alongside metadata (`phase`, `run_params`, `dataset`). The
  schema-kind contract validates the bare return value; output-validation needs
  to descend. Added `wrapper_key` field to the `output_validation` block of the
  meta-schema; validator + test honor it. *(2)* `applies_to_glob` caught more
  than just cell-schema files (BIC curves, intrinsic-d, landscape sensitivity
  sweeps, pre-reg manifests, stratified-Markov legacy mass output). Made
  `file_dispatch` a positive filter — only filenames matching a dispatch
  pattern are validated; unmatched files are ignored. Pre-fix legacy Stage-1
  JSONs are deliberately not in dispatch scope (the T1.2 cascade-recompute
  work handles those).

- **`pending: true` field** added to the meta-schema. Contracts authored on a
  feature branch whose binding test is not yet on the base branch can be
  marked pending — they pass gate 1 (meta-schema validation) but skip gates
  2–4. Three contracts were marked pending during the worked-example pass
  because their bindings lived in the T1.37 worktree; flags cleared in the
  corrective-fix commit (`9c81311`) once the regression test file landed on
  main.

- **Corrective fix lifted from worktree to main.** The tda-agent Worker fixed
  the T1.36 math defect in-flight on
  `.apm/worktrees/run-headline-batch-frozen-pca-rerun/` (uncommitted, working-
  tree state only). The worktree branch was BEHIND main on the Serena removal
  (`424ff81`), so direct `git merge` would have regressed. Manager 3 created a
  fresh branch (`pipe/stage1-pvalue-denominator-fix`) off the contracts-
  framework-augmented main, cherry-copied the three corrective files
  (`_battery_core.py`, `run_stage1_battery.py`, `test_stage1_battery_core_regressions.py`),
  cleared the three `pending` flags, and committed under the contract gate.
  Hook fired on the commit; all six contracts now active and all four gates
  pass. Deliberately did NOT bring across: the worktree's job-01 through
  job-04 frozen JSONs (statistically invalid under buggy denominator), smoke
  output, `job_logs/` runtime files.

- **PyYAML + jsonschema added as core deps** (not dev) so the pre-commit hook
  works for every developer regardless of `--extra dev`. `uv.lock` refreshed;
  `pot` re-installed via `uv sync --extra wasserstein`.

- **Three commits landed on main this session:**
  - `bb1b0a1` [PIPELINE] P01: Math-correctness contracts framework with
    pre-commit hook gating (15 files, +1493 lines).
  - `9c81311` [PIPELINE] P01: Stage-1 W2 p-value denominator + LM schema
    corrective fix (6 files, +224 / -45).
  - `686508a` [PIPELINE] APM: tracker — contracts framework + Stage-1
    corrective fix landed (1 file, +3 / -1).

- **Vault entries filed** under the locked reverse-chronological convention:
  - `04-Methods/Computational-Log.md` — one new `[PIPELINE] + [DECISION]`
    entry at the top covering both commits, with the formal lock on the
    framework as the canonical math-correctness mechanism, the corrected
    `(r + 1) / (B + 1)` Monte Carlo formula, and the LM aggregate schema.
  - `04-Methods/Pipeline-Overview.md` — new `Recent Pipeline Changes` log
    section inserted between intro and Stage 1, three reverse-chronological
    entries covering today's two commits plus yesterday's frozen-loadings
    threading (`7e7ffcb`) which had not been recorded.
  - `CONVENTIONS.md` — two new ALWAYS rules (upstream contract authorship;
    Monte Carlo p-value denominator discipline) and two new NEVER rules (hook
    bypass; self-authored contracts).

## Working Context

### Tracked Worker Handoffs

| Agent | Handoff Stage | Current-Stage logs loaded | Notes |
|---|---|---|---|
| tda-agent | 1 (staged, not processed) | task-01-37.log.md, task-01-37.jobs.md | Worker authored own Handoff log + bus prompt mid-session at User's behest. Files written: `.apm/bus/tda-agent/handoff.md` (3038 bytes) + `.apm/memory/handoffs/tda-agent/handoff-01.log.md` (5302 bytes). Per APM §3.1 Report Processing, formal processing only happens when instance 2 submits its first report — Manager 3 did not process. Manager 4 should expect instance 2 to declare itself in its first Task Report; at that point increment the Worker instance number in the Tracker. Previous-Stage same-agent dependencies for tda-agent become cross-agent for instance 2. |

No other Worker Handoffs detected or processed this session. panel-statistics-
agent, academic-writing-agent, and reproducibility-agent remain on their
pre-existing instance numbers.

### Version Control State

Base branch: `main` at `686508a` (last commit: tracker update).

Active branches and worktrees:

| Branch | Worktree | Status | Commits ahead of main | Notes |
|---|---|---|---|---|
| `pipe/two-machine-check` | `.apm/worktrees/pipe-two-machine-check` | Paused | 1 | T0.3 paused awaiting User's `canary_machine2_2026-05-07.json`. Only gates §5 reproducibility prose in P01-B; does not block Stage 1. Unchanged this session. |
| `run/headline-batch-frozen-pca-rerun` | `.apm/worktrees/run-headline-batch-frozen-pca-rerun` | Paused — behind main | -3 commits | T1.37 paused; branch now BEHIND main on Serena removal (`424ff81`) + contracts framework (`bb1b0a1`) + corrective fix (`9c81311`) + tracker update (`686508a`). Reissue requires either rebase onto current main OR removing + recreating the worktree from current main. Working tree retains 4 superseded job JSONs + job_logs/ + smoke output (all generated under buggy denominator; statistically invalid; do not bring across). |
| `run/tier3-regression` | `.apm/worktrees/run-tier3-regression` | Retained (historical) | 1 | T1.21 diagnostic commit `ddc7efb`. Branch retained as historical record; not for new work. Unchanged this session. |

Branches deleted this session: `pipe/contracts-framework` (after fast-forward
merge to main), `pipe/stage1-pvalue-denominator-fix` (after fast-forward merge
to main).

Orphan worktree directories on disk (low priority cleanup):
- `.apm/worktrees/run-stage1-headline-batch/` — orphan from T1.2 batch session
  (file lock from 2026-05-25).
- `.apm/worktrees/pipe-ngram-embed-frozen-loadings/` — orphan from T1.36 session
  (file lock from 2026-05-26).

Both are git-untracked; safe to `rm -rf` manually when locks release. Do not
block coordination.

Pending merges: none.

### Dispatch Patterns Observed

- Strict sequential dispatch remains the User's preference (T1.36 → T1.37 → then
  T1.33/T1.34/T1.35). T1.33, T1.34, T1.35 remain Ready but **held** per User
  direction. The contracts framework adds a new pre-dispatch step (Trigger 3:
  Manager pre-dispatch coverage check) — Manager 4 should run this check before
  every Task Prompt construction.

- Manager-implements vs Worker-dispatched: for infrastructure work the User
  has shown preference for Manager-implements (chose this for the contracts
  framework Phase B). For scientific code work (computational tasks, prose,
  regression specs) Workers remain the right home.

- Multi-terminal compute is User-confirmed (per prior Manager sessions); not
  exercised in M3 because no dispatch cycles ran.

## Working Notes

### User preferences and communication patterns

- **Depth-first collaborative design.** When the User says "this is more
  complex than X, let's address Y broadly," they want full structured
  exploration, not a single quick proposal. The contracts framework
  emerged over five+ rounds of structured AskUserQuestion + back-and-forth
  before any code was written. Resist the temptation to short-circuit; the
  design quality benefits from the dialogue.

- **Concrete artefacts before generalisation.** When the User says "let me
  see what this looks like," produce a real example (worked-example contracts)
  before extending the framework. They iterate against artefacts they can
  read, not against abstract specifications.

- **Hard-enforce from day one** rather than soft phase-in. The User explicitly
  chose this for the hook gating. Their reasoning: a soft phase-in allows the
  next math defect to slip through during the transition window.

- **Sequential dispatch is the active preference.** Even though parallel
  worktree-based dispatch is supported, the User has chosen to dispatch
  one task at a time. Don't propose parallel dispatch unless the User asks.

- **Recompute-from-cache is the cascade default.** The User chose this over
  full re-run for the T1.2 cascade ("most defensive for the academic record").
  Apply the same pattern for future cascades unless they direct otherwise.

- **Don't clear runtime bus files without confirmation.** Early in this session
  the User explicitly stopped me from clearing the handoff bus while they were
  working with another agent on the same problem. Default: surface what you're
  about to do for risky/destructive operations even if APM convention says go
  ahead.

- **Tone:** terse, technical, well-structured. Bullet lists + tables work
  better than prose paragraphs for status updates. Code references should use
  Markdown link syntax `[label](path)` for VSCode IDE integration.

### Decisions made and approaches tried

- **Framework location: `contracts/` at repo root**, not `.apm/contracts/`,
  precisely so the framework survives replacement of APM. Topic-based
  organisation (`stochastic-tests/`, `stage1-output-schemas/`,
  `topology-invariants/`, etc.) rather than task-based — contracts are
  reusable across tasks via the optional `manifests/<scope-id>.yaml`
  groupings (the only APM-flavoured part of the layout; easily replaceable).

- **Pre-Worker extraction agent (not Worker self-extraction).** The User and I
  settled on this because the same misreading that produces wrong code would
  produce a wrong contract — recursive failure. Contracts must originate
  upstream of the Worker. Manager 4: when authoring T1.37 contracts, you ARE
  the extraction agent. Don't delegate contract authorship to the Worker who
  will implement T1.37.

- **One-to-one binding rule** locked. A single test cannot be referenced by
  multiple contracts. When the same mathematical claim applies to two distinct
  code paths (e.g., new `_battery_core.aggregate_combined` AND legacy
  `run_stage1_battery._aggregate_combined`), author twin contracts (e.g.,
  `monte-carlo-permutation-p-value` + `monte-carlo-permutation-p-value-legacy`).

- **`must_assert` is descriptive prose**, not programmatic. The hook can't
  verify the bound test actually asserts what `must_assert` says — only that
  it passes. Human review during contract authoring is the gate. A future
  enhancement could scan test source for keywords from `must_assert`.

- **PyYAML + jsonschema in core deps**, not dev. The hook must work for every
  developer regardless of `--extra dev` install state. They're tiny + ubiquitous
  + not specific to development.

- **Worktree files copied selectively** rather than merged: T1.37 worktree's
  job-01 through job-04 frozen JSONs are statistically invalid (buggy denominator)
  and were NOT brought across. Only the corrective code + tests came over.
  The pattern: when a worktree branch is behind main, create a fresh branch
  off current main, then `cp` only the specific files needed; commit on the
  fresh branch; merge.

### Coordination insights

- **The contracts framework changes the Manager review surface.** Previously a
  successful Task Review meant "tests pass + canary completes." Now it also
  means "contracts cover the code path + bindings pass + JSONs validate." When
  reviewing a T1.37 reissue report (or any computational report), explicitly
  check that the produced JSONs conform to the cell-schema contract before
  accepting Success.

- **Manager 3 made no formal dispatches.** This is unusual but appropriate for
  a session focused on building enforcement infrastructure. Manager 4 should
  expect to resume normal dispatch flow — T1.37 reissue is the immediate
  candidate, followed by T1.33/T1.34/T1.35 (still Ready, still held).

- **T1.37 reissue requires worktree decision.** The `run/headline-batch-frozen-pca-rerun`
  branch is now 4 commits behind main. Two clean options:
  - *Rebase the branch onto current main* (preserves branch identity; preserves
    the staged Worker Handoff continuity). Some merge complexity if the
    worktree's uncommitted superseded JSONs are still in the working tree.
  - *Remove the worktree + branch entirely; create a fresh `run/headline-batch-frozen-pca-rerun-v2`
    off current main.* Clean slate; preserves nothing from the prior dispatch.
    Worker Handoff prompt still applies (it's about resumption logic, not
    branch identity).

  My read: rebase if the User wants to preserve T1.37's dispatch history;
  recreate if they want a clean slate. Either way, surface as a User-decision
  point.

- **Smoke testing the framework against a real task is essential.** The two
  design refinements (`wrapper_key`, positive-filter `file_dispatch`) only
  surfaced because we ran the validator against the actual T1.36 output JSONs.
  Manager 4: when T1.37 contracts are authored, run the validator with
  `--all-jsons` against the produced outputs before declaring the framework
  generalises. Expect further refinements.

- **Other Stage-1 output shapes need their own schema contracts** but were
  deliberately deferred. BIC curves, intrinsic-d, landscape sensitivity sweeps,
  pre-reg manifests, and the legacy stratified-Markov mass output all have
  distinct shapes and are currently excluded from `file_dispatch` positive
  filtering. Authoring those schemas is a clean future expansion — one
  schema-kind contract per output type, add to dispatch.

- **The T1.2 cascade is a tracked open item.** Recompute corrected p-values
  from the preserved `.npz` null-diagram caches at PROJ_ROOT + draft
  methodological-disclosure paragraph for P01-A §3.3 / §4.3. Can run in
  parallel with T1.37 reissue; doesn't share a worktree. Small Python script
  + Academic Writing Agent dispatch for the paragraph. Not yet formally
  scoped as a Plan task.

### Files added or modified this session

**Committed to main:**
- `bb1b0a1`: `contracts/` (9 files), `.claude/hooks/contract_binding_check.py`
  (new, 440 LOC), `.claude/hooks/git-pre-commit.sh` (new), `.claude/hooks/install-git-hooks.py`
  (modified), `tests/trajectory_tda/test_stage1_output_json_validation.py`
  (new, 154 LOC), `pyproject.toml` (modified, +5 lines), `uv.lock` (modified,
  +90 lines).
- `9c81311`: `trajectory_tda/scripts/stage1/_battery_core.py` (modified, +59 / -42),
  `trajectory_tda/scripts/run_stage1_battery.py` (modified, +51 / -3),
  `tests/trajectory_tda/test_stage1_battery_core_regressions.py` (new, 156 LOC),
  3 contract YAMLs lost their `pending: true` line.
- `686508a`: `.apm/tracker.md` (1 row updated + 1 working note added).

**Vault writes:**
- `04-Methods/Computational-Log.md` — new [PIPELINE] + [DECISION] entry at top.
- `04-Methods/Pipeline-Overview.md` — new `Recent Pipeline Changes` section
  with 3 reverse-chronological entries.
- `CONVENTIONS.md` — 2 new ALWAYS rules + 2 new NEVER rules at tops of
  respective sections.

**Local/untracked (not committed; left for User direction):**
- `.apm/memory/handoffs/manager/handoff-02.log.md` — M2's handoff log
  (untracked, gitignored under Option B implicitly).
- `.apm/memory/handoffs/tda-agent/handoff-01.log.md` — Worker-authored handoff
  log (same).
- `.apm/session-summary.md` — M2's session summary (same).
- `papers/shared/literature/` — paper work outside this session's scope.

### Two open scope-decision items still deferred from M2

1. `claude-code-lsp-enforcement-kit/` directory at project root — separate kit
   (not under `.apm`/`.claude`/`.codex`, so out of scope for the Serena
   removal). Still pushes agents toward Serena/cclsp via README + detection
   code. User to decide whether to remove.
2. `~/.claude/rules/lsp-first.md` (global user rule loaded into every Claude
   Code session in this repo) — still directs LSP-MCP use including
   Serena-equivalent tools. User to decide whether to disable or scope.

Both flagged across two Manager handoffs now; Manager 4 may want to surface
again if they remain unresolved at session start.
