# Skill-Suite ARS-Readiness Plan — Executable Task Briefs

**Date:** 2026-07-02
**Author:** Fable 5 session (skill-suite build-out + ARS assessment)
**Executor:** Opus or Sonnet, one brief per session/worktree
**Source:** ARS fit assessment delivered 2026-07-02 (session report), grounded in
`docs/plans/agentic-research-system/design/` W1–W8 accepted specs. The improvements
below are bridge work: they make the current dual-tree skill suite consumable by the
future ARS context compiler (W3 §13.2), change gates (P-018/W6 §11), and parity model
(W7 §14) without pre-implementing any of those systems.

**Standing guidance (not tasks):**

- `SKILL-INDEX.md` (authoring tree only) stays an interim routing aid — ARS has no
  skill-registry concept; W3's procedural-memory selection supersedes it. Do not
  extend it beyond a routing table.
- Skills reference locked conventions (`CONVENTIONS.md`, `papers/shared/notation.md`);
  they never restate them. Restatement is drift surface and token weight.
- Any content change to a skill bumps its `metadata.version` (after SKL-1 lands).

**Shared execution rules (apply to every brief):**

- Branch `pipe/<brief-slug>` on a worktree under `.apm/worktrees/`; immediately
  `Copy-Item "c:\Users\steph\TDL\.env" "<worktree>\.env"`. Push and open a PR for
  CodeRabbit review; merge only after the review concludes. Worktree removal is
  manual, never post-merge.
- Skills are edited in the `.agents` authoring tree ONLY, then mirrored with
  `uv run python tools/sync_agent_skills.py`; both `--check` and `--check-guides`
  must exit 0 before commit. Never edit the `.claude` mirror directly.
- Never `--no-verify`. Nothing is written under `results/` by any of these tasks —
  that tree is for real, provenance-tracked compute only.
- Commit prefix `[PIPELINE] Infrastructure:` with the Co-Authored-By trailer;
  vault action: Pipeline-Overview entry (top-of-page) + daily-note line.

---

# Task Brief: SKL-1 Machine-readable skill metadata + suite checker

## Target paper / project
infrastructure

## Recommended model
Sonnet — mechanical, schema-driven; all judgment is pinned below.

## Goal
Every skill in `SYNC_SKILLS` carries a machine-readable `metadata:` frontmatter
block, validated by a new checker tool, so a future ARS context compiler can consume
the suite as versioned procedural memory (W3 §13.2: name, version, applicability,
compatibility, review state).

## Non-goals
Do NOT rewrite any skill description or body prose. Do NOT touch skills matched by
`EXCLUDE_PATTERNS`. Do NOT build a skill registry, index generator, or selection
mechanism. Do NOT modify `tools/sync_agent_skills.py` beyond zero lines (the checker
is a separate tool).

## Assurance lanes
None touched (workflow infrastructure). Research-assurance triage: not lane-bearing;
no enforcement contract required — the checker itself is the enforcement artifact.

## Required upstream contracts
- Existing: none apply.
- Needed before implementation: none.
- Not applicable because: no mathematical, statistical, or provenance logic; the
  deliverable is metadata plus a deterministic validator.

## Pinned metadata schema
Nest under `metadata:` (the agentskills.io frontmatter spec supports a metadata map;
top-level custom keys risk parser strictness — verify per step 1 below):

```yaml
metadata:
  version: "1.0.0"          # semver string; bump on any content change
  tier: core | specialist | optional | domain
  lanes: []                  # subset of: topology, stochastic-null,
                             # statistical-panel, representation,
                             # output-provenance, paper-claim
  roles: []                  # subset of: orchestrator, manager, implementer,
                             # verifier, claim-reviewer, operator  (W4 §8)
  runtime: agnostic          # all SYNC_SKILLS skills are runtime-agnostic
```

Tier assignments: the 10 skills in the manifest's "TDL-adapted engineering + workflow"
group = `core`; the 8 "Tier-2 specialist" = `specialist`; the 8 "Tier-3 optional" =
`optional`; everything else in `SYNC_SKILLS` (domain/coordination + RA layers +
adversarial-design-review) = `domain`. Lanes/roles: derive from each skill's stated
scope; when in doubt, fewer lanes (a lane tag asserts the skill is part of that
lane's review path).

## Inputs
- `tools/sync_agent_skills.py` (read-only: the `SYNC_SKILLS` set is the roster)
- Every `SKILL.md` under the `.agents` authoring tree for skills in `SYNC_SKILLS`
- `docs/plans/agentic-research-system/design/03-context-memory-and-retrieval.md`
  §13.2 and `design/04-agent-roles-and-model-routing.md` §8 (taxonomy source,
  read-only)

## Expected outputs
- `metadata:` block added to all `SYNC_SKILLS` skill frontmatters (authoring tree),
  mirrored to the Claude tree via the sync tool
- `tools/check_skill_metadata.py` — validates, for every `SYNC_SKILLS` skill:
  metadata block present; `version` parses as semver; `tier`/`lanes`/`roles`/`runtime`
  values within the pinned vocabularies; frontmatter still has `name` + `description`
  and description ≤ 1024 chars. WARN (not fail) when a SKILL.md exceeds 200 lines or
  1,600 words (token-weight guard for W3's R2/R3 context ceilings). Exit 0 clean,
  1 on violations, 2 on framework error — same convention as the sync tool.
- `tests/tools/test_check_skill_metadata.py` — TDD, red before green; cover: missing
  block, bad enum value, bad semver, oversize warning (not error), clean pass.

## Acceptance criteria (machine-checkable)
1. `uv run python tools/check_skill_metadata.py` exits 0 over the full suite.
2. `uv run python tools/sync_agent_skills.py --check` exits 0 (trees identical).
3. `uv run pytest tests/tools/ -q` passes.
4. `uv run ruff check .` and `uv run ruff format --check` clean on changed files.
5. Frontmatter-compatibility verification (see step 1) recorded in the PR body.

## Validation commands
```
uv run python tools/check_skill_metadata.py
uv run python tools/sync_agent_skills.py --check
uv run python tools/sync_agent_skills.py --check-guides
uv run pytest tests/tools/ -q
```

## Procedure notes
1. **Verify before relying (external-inference rule):** confirm added `metadata:`
   frontmatter does not break skill loading — after syncing ONE pilot skill
   (suggest `tda-light-task-triage`), confirm the skill still lists/loads in a
   Claude Code session and Codex still reads the authoring tree. Only then roll out
   to the remaining skills.
2. Roll out mechanically; do not reflow surrounding prose.
3. Checker gets the standard research-context header comment (`.claude/rules/python.md`).

## Provenance requirements
No result artifacts. Deliverables are committed files on the task branch.

## Runtime constraints
No long compute. Wall time ≈ 1–2 h. No-overwrite rules for results N/A.

## Paper-claim constraints
None — no paper content may be touched.

## Suggested skills
`tda-skill-authoring-workbench` (dual-tree mechanics) · `contract-first-tdd`
(checker via TDD) · `commit-log` / `vault-sync` at close.

## Stop conditions
- The pilot skill fails to load with a `metadata:` block → STOP, report the exact
  parser behaviour, propose an alternative placement; do not roll out.
- Any skill's frontmatter is malformed before editing → fix only if trivial;
  otherwise report.

---

# Task Brief: SKL-2 Tier-1 pressure-test fixtures (the four validation scenarios)

## Target paper / project
infrastructure (fixtures exercise P01-A/P01-B-shaped content but produce no research
results)

## Recommended model
Opus — judgment-heavy: scenario design fidelity and verdicting are the work.

## Goal
The four validation scenarios from the Priority-1 skill plan are actually run as
fresh-context pressure tests against the live tier-1 skills, with outcomes recorded
as fixture documents — the suite's first change-gate fixtures in the sense of
ARS P-018 — and tier-1 skills amended only where a scenario fails.

## Non-goals
No real data compute — scenarios are prompt-level simulations with synthetic/quoted
values. No `results/` writes. No pytest harness for skill invocation (out of scope;
these are documentation fixtures). If a scenario exposes a *code* defect, file it as
a finding — do NOT fix pipeline code in this task.

## Assurance lanes
None produced (no result artifacts). Scenario *content* deliberately simulates
Stochastic-Null / Statistical-Panel / Paper-Claim defects; that content stays inside
fixture documents clearly labelled as synthetic test material.

## Required upstream contracts
- Existing: none apply. Needed: none.
- Not applicable because: no result-bearing computation; the fixtures ARE the
  enforcement artifact this task creates.

## Pinned scenarios and pass conditions (from the Priority-1 plan)
1. **P-value denominator bug.** Chain: `tda-diagnosing-computational-defects` →
   `contract-first-tdd` → `tda-statistical-analysis-review`. PASS iff the agent
   insists on a red-capable command, distinguishes `pvalue_null_draws` from
   `effect_null_pairs`, and refuses to close on a generic passing test.
2. **New Markov-2 null battery.** Chain: `tda-task-brief-from-plan` →
   `tda-resource-preflight` → `contract-first-tdd` → `tda-statistical-analysis-review`.
   PASS iff the produced brief states Markov order k, B, L, frozen-loadings
   assumptions, worker count, checkpointing, p-value formula, output schema, and
   paper target.
3. **P01-B methods-section review.** Chain: `tda-peer-review-panel` →
   `tda-statistical-analysis-review` → `tda-literature-verification`. PASS iff the
   review keeps applied P01-A findings out of P01-B and runs separate
   methodology/statistical/reproducibility passes.
4. **Perplexity literature lead.** Chain: `tda-literature-verification`. PASS iff
   the source is treated as a lead, verified via authoritative metadata, routed to
   Zotero + literature note, and paper-tagged before any prose use.

## Inputs
- The ten tier-1 SKILL.md files (authoring tree)
- The scenario definitions above (self-contained)
- `C:\Users\steph\.claude\plugins\...superpowers...\writing-skills\SKILL.md`
  methodology (RED → GREEN → REFACTOR) as process reference, if available

## Expected outputs
- `tests/skills/fixtures/tier1/scenario-0<N>-<slug>.md` (4 files): scenario prompt
  verbatim, expected behaviours, model/agent configuration used, observed behaviour
  summary, verdict PASS/FAIL per pass condition, date, and any rationalizations
  observed verbatim (they seed counters).
- `tests/skills/fixtures/tier1/README.md`: what these fixtures are, how to re-run
  one, and the P-018 framing (any future change to a tier-1 skill re-runs the
  affected scenario).
- Skill amendments ONLY for failed scenarios: add self-test prompts or explicit
  counters to the failing skill (authoring tree → sync). Version-bump if SKL-1 has
  landed.

## Acceptance criteria
1. Four fixture files exist with explicit per-condition verdicts.
2. Each scenario was actually executed against a fresh-context agent (transcript
   evidence summarized in the fixture; no verdict from reading the skill alone).
3. Any FAIL has either a skill amendment (re-run shows PASS) or a documented
   escalation.
4. Sync `--check` exits 0; no manifest changes.

## Validation commands
```
uv run python tools/sync_agent_skills.py --check
Get-ChildItem tests/skills/fixtures/tier1
```

## Provenance requirements
Fixture files record date + model used. No result JSONs.

## Runtime constraints
4 subagent runs + possible re-runs; wall time ≈ 2–4 h. No parallel-compute rules
apply (no stochastic compute).

## Paper-claim constraints
Fixture content must be unmistakably synthetic — never cite fixture numbers as
project results anywhere.

## Suggested skills
`tda-skill-authoring-workbench` · the four scenario chains above (as subjects) ·
`commit-log` / `vault-sync` at close.

## Stop conditions
- A scenario cannot be made to run without real data → simplify to quoted synthetic
  values; if still blocked, record the scenario as NOT-RUN with the blocker.
- A failure implicates a locked convention rather than a skill → STOP, surface as a
  User decision.

---

# Task Brief: SKL-3 Direction-aware sync (three-way mirror state)

## Target paper / project
infrastructure

## Recommended model
Sonnet — the design is pinned; implementation is TDD against a stated contract.

## Goal
`tools/sync_agent_skills.py` detects a mirror-side edit and refuses to overwrite it,
instead of silently restoring the authoring tree's content — closing the failure
class hit live on 2026-07-02 (the `commit-log` BOM note sat newer on the mirror; a
blind sync would have destroyed it). This is the bridge step toward W7 §14 ("a richer
destination cannot be overwritten by a poorer source; divergence produces a report
and blocks"), NOT the W7 parity engine.

## Non-goals
No semantic/parity diffing, no git dependency inside the tool, no changes to
classification, exclusion, lint, `--check-guides`, or `mirror_skill()` file-copy
semantics. Do NOT auto-port mirror edits back to the authoring tree.

## Assurance lanes
None (workflow infrastructure). Enforcement artifact = the tool's own tests.

## Required upstream contracts
- Existing: none apply. Needed: none.
- Not applicable because: no research logic; deterministic file-state tooling.

## Pinned design
- New committed state file `tools/skill_sync_state.json`: mapping
  `skill → {relative_path → sha256}`, recorded after every successful mirror of that
  skill and after verified-identical checks.
- In the update path, for each differing skill classify per file:
  - dst hash == recorded state hash → mirror untouched since last sync → safe to
    overwrite (normal UPDATED path).
  - dst hash != recorded state AND dst hash != src hash → **MIRROR_EDITED**: print
    an error naming the skill and files, instruct "port the change to the authoring
    tree and re-run, or re-run with --force-mirror to discard the mirror edit",
    skip the skill, final exit 1.
  - dst missing → CREATED path (unchanged behaviour).
- `--check` reports `MIRROR_EDITED` rows distinctly from `DIVERGED`.
- New flag `--force-mirror`: proceeds with overwrite for MIRROR_EDITED skills and
  records fresh state.
- Bootstrap: if the state file is absent, first successful run writes it from the
  current (verified in-step) trees; absent state + divergent trees → treat every
  divergent skill as MIRROR_EDITED (fail safe, require human direction).

## Inputs
- `tools/sync_agent_skills.py`, `tests/tools/test_sync_agent_skills.py` (current
  5 tests must keep passing)

## Expected outputs
- Updated tool (docstring updated to describe three-way semantics)
- `tools/skill_sync_state.json` (bootstrapped, committed)
- Extended tests: MIRROR_EDITED detection; bootstrap behaviour; `--force-mirror`;
  state refresh after successful mirror; existing Windows open-handle regressions
  still green. TDD — each new test seen red first.

## Acceptance criteria (machine-checkable)
1. `uv run pytest tests/tools/test_sync_agent_skills.py -q` — all pass (old + new).
2. A manual repro: edit a mirror-side SKILL.md, run sync → exit 1, no overwrite,
   MIRROR_EDITED named; `--force-mirror` → overwrites and exits 0. Record in PR body.
3. `--check` and `--check-guides` exit 0 on the clean tree; ruff clean.

## Validation commands
```
uv run pytest tests/tools/test_sync_agent_skills.py -q
uv run python tools/sync_agent_skills.py --check
uv run ruff check tools/ tests/tools/
```

## Provenance requirements
State file is committed alongside the change; no result artifacts.

## Runtime constraints
No long compute. Wall time ≈ 2–3 h.

## Paper-claim constraints
None.

## Suggested skills
`contract-first-tdd` · `tda-skill-authoring-workbench` · `tda-diagnosing-computational-defects`
(if existing tests behave unexpectedly) · `commit-log` / `vault-sync` at close.

## Stop conditions
- Preserving all existing exit-code/output behaviour proves impossible under the
  pinned design → STOP and report the conflict; do not weaken the fail-safe
  classifier.
- Worktree interaction (state file diverging across worktrees) raises a design
  question → note it in the PR; do not invent per-worktree state.

---

# Task Brief: SKL-4 Prose-controls register + mirror-write guard hook

## Target paper / project
infrastructure

## Recommended model
Opus for the audit/register (judgment about what counts as a control and whether it
is enforced); the hook slice is Sonnet-executable.

## Goal
Every control-like assertion living in skill prose is enumerated and classified in a
register (enforced / enforceable / judgment-only), and exactly one new enforcement
artifact is implemented: a PreToolUse hook that blocks agent `Write`/`Edit` into the
Claude-side mirror skill tree. Rationale: ARS reviews cite prose-carried controls as
the anti-pattern (the `apm-communication` bus-ownership case); machine-checkable
controls belong in hooks/contracts, skills teach judgment.

## Non-goals
Implement ONLY the mirror-write guard. Every other "enforceable" finding is a
register entry with a proposed artifact — not built here. No contract file changes.
No edits to skill prose (the register references, it does not rewrite).

## Assurance lanes
None directly; the register's classifications reference Output-Provenance and
Paper-Claim lane controls but create no lane artifacts.

## Required upstream contracts
- Existing: pre-commit contract gates, `results-no-overwrite.sh`, notation-guard,
  dispatch-readiness-guard (the register must map controls onto these accurately —
  read the hook scripts, do not assume).
- Needed: none. Not applicable for new contracts: the one implemented control is a
  hook, and hooks are the correct artifact class for tool-call boundaries.

## Inputs
- All SKILL.md files for `SYNC_SKILLS` skills (authoring tree)
- `.claude/hooks/*` and `.claude/settings.json` (current enforcement inventory)
- `.claude/instructions/hook-enforcement.instructions.md`

## Expected outputs
- `docs/plans/skills/skill-prose-controls-register_2026-07-XX.md`: one row per
  control-like assertion — skill, quoted assertion, classification
  (enforced-by:<artifact> / enforceable:<proposed artifact> / judgment-only),
  and for `enforceable` a one-line implementation sketch.
- `.claude/hooks/mirror-tree-guard.sh` + a `PreToolUse` `Write|Edit` entry in
  `.claude/settings.json`: deny when the target path resolves inside the Claude-side
  skill tree (match both `/` and `\` separators and worktree paths), with a denial
  message naming the authoring tree and the sync tool. Plain-file writes by the sync
  tool itself are unaffected (it writes via Python, not agent tools).
- One-paragraph addition to `.claude/instructions/hook-enforcement.instructions.md`
  documenting the new hook.

## Acceptance criteria
1. Register covers every `SYNC_SKILLS` skill (a skill with no control-like prose
   gets an explicit "none" row — coverage must be checkable).
2. Hook manual test recorded in the PR body: an agent `Edit` against a mirror-tree
   SKILL.md is denied with the expected message; an `Edit` against the authoring
   tree succeeds; `uv run python tools/sync_agent_skills.py` still mirrors.
3. Hook script passes `bash -n` (syntax) and follows the existing hooks' JSON
   permissionDecision output convention (read a current hook first).
4. Sync `--check` exits 0; no skill content changed.

## Validation commands
```
bash -n .claude/hooks/mirror-tree-guard.sh
uv run python tools/sync_agent_skills.py --check
```

## Provenance requirements
No result artifacts. Register is a committed document.

## Runtime constraints
No long compute. Wall time ≈ 2–3 h.

## Paper-claim constraints
None.

## Suggested skills
`tda-agent-safety-guardrails` (the audit's subject-matter frame) ·
`tda-skill-authoring-workbench` · `hookify:writing-rules` or existing hook scripts
as pattern reference · `commit-log` / `vault-sync` at close.

## Stop conditions
- The hook risks blocking a legitimate write path that cannot be distinguished by
  path (none is known — but if found, STOP and report rather than widening the
  allow condition silently).
- The audit finds a control that is *believed* enforced but the hook/contract does
  not actually cover it → that is a finding for the register marked
  `enforceable (gap)`, and if it guards result immutability or claim validity,
  surface it to the User immediately rather than waiting for the register to land.

---

# Sequencing and dispatch notes

Recommended order: **SKL-1 → SKL-3 → SKL-4 → SKL-2.**

- SKL-1 first: metadata + checker give every later task a stable roster and version
  field to bump.
- SKL-3 second: both it and SKL-1 touch `tools/`, keep them serial to avoid
  conflicts; SKL-3's state file should be built over the post-SKL-1 trees.
- SKL-4 third: its register can use SKL-1's lane metadata as a cross-check.
- SKL-2 last: judgment-heavy, benefits from a stable suite; its fixture README can
  reference the checker and versions.

No brief depends on ARS P0 and none pre-implements W3/W6/W7 machinery — every
deliverable stands on its own in the current dual-tree system. All four are
independent of paper work and safe to run between research tasks.
