# Handover: Gate 5 Orchestration — ARS Foundation Acceptance

**For:** a fresh Claude Fable 5 session in `C:\Users\steph\TDL` (branch `main`)
**Role:** Gate 5 orchestrating Manager for the Agentic Research System (ARS) P0
foundation. You dispatch and verify; Workers implement. You perform all merges.
**Effort routing:** run at **high** effort for routine orchestration (register checks,
merge mechanics, verification). Step up to **xhigh** for exactly two activities:
authoring each WP5 dispatch plan, and anything touching the WP5.6 bounded review.
Workers dispatch on **Opus 4.8 / xhigh** (the proven WP4.8/WP4.9 regime).

---

## 1. Read before acting (in this order)

1. `CONVENTIONS.md` (repo root — canonical; never via the vault path)
2. `docs/plans/agentic-research-system/implementation/05-wp5-gate5-foundation-acceptance-plan.md`
   — **the governing scope plan for everything you do**; authored 2026-07-10
3. `docs/plans/agentic-research-system/implementation/04a-wp4-8-verdict-derivation-and-release-evidence-plan.md`
   — obligation register O1–O16 (§ "Obligation register")
4. `docs/plans/agentic-research-system/implementation/04b-wp4-9-corpus-restore-to-spec-plan.md`
   — register R1–R12; also the model dispatch-plan format you must reproduce
5. `docs/plans/agentic-research-system/05-p0-materialization-and-foundation-implementation-plan.md`
   — §4.4 (release tranche), §5 (checkpoints 5–7), §6 (assurance), §7/§7.2 (retention,
   backup/restore extension, live-grader threshold clause)
6. `docs/plans/agentic-research-system/04-parallel-specification-and-foundation-pilot-plan.md`
   §4 — Gate 5 and Gate 6 definitions
7. `docs/plans/agentic-research-system/design/06-evaluation-observability-and-audit.md`
   — S-014/S-015/S-016 rows (~lines 207–209); grader tuples D,T,O,P / D,T / D,T,O,H
8. `docs/plans/agentic-research-system/design/07-runtime-adapters-and-policy-parity.md`
   — W7 parity semantics (semantic, field-by-field, fail-closed; one row per normalized
   control; missing critical control blocks; aggregate percentages diagnostic only)
9. `docs/plans/agentic-research-system/reviews/adversarial-wp4-full-review-2026-07-07.md`
   — the depth/pattern standard for the WP5.6 bounded review

## 2. Verified state as of 2026-07-10 (do not re-derive; spot-check if suspicious)

- **Gate ladder:** Gates 1–3 accepted (P-029/P-030 etc.); Gate 4 exit approved
  2026-07-01 and its execution **closed out 2026-07-10** on `main`; you are running the
  Gate 5 campaign. Gate 6 (greenfield paper preflight) only after Gate 5 acceptance.
- **All WP4 tranches merged:** PR #69 (honest-state fixes), PR #70 (WP4.8 verdict
  derivation + release evidence), PR #71 (WP4.9 corpus restore-to-spec). Every merge
  went through review-then-merge with CodeRabbit concluded pre-merge.
- **Invariants verified on merged `main`** (these are stop conditions — see §5):
  - `eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake`
    → `blocked_fixture_count: 14`, `fixture_count: 37`,
    `fixtures_with_uncalibrated_mutations: 0`, `mutation_calibration: "calibrated"`
  - `eval run --coverage ... --transport fake` → `candidate_status: "blocked"`,
    `result_count: 122`
  - `uv run --no-sync pytest tests/research_system -q --no-cov` → 338 passed
- **Register state:** O1–O9, O13 delivered. O10 partially closed
  (`release_gate_decision: rgd` registered in
  `.research-system/config/id-kind-registry.yaml`; WP1-reviewer confirmation folds into
  WP5.6). **Open Gate 5 dependencies: O11, O12, O14, O16, R8. Owner-gated: O15, R12.**
- The corpus is at spec: F-036 restored at r2 with three named executed mutations;
  F-021 sizing rows bound; threshold/calibration/variant registries load-bearing.
  The 14 blocked fixtures are blocked by M/H grader authority **by design**.

## 3. The Gate 5 work-package structure (details in the scope plan — this is a map)

| WP | Scope | Closes | Branch |
|---|---|---|---|
| WP5.1 | Grading-integrity: real producer/grader family identities so the cross-family independence branch in `graders.validate_grader_result` is reachable; `current_policy_revision` sourced from canonical `.research-system/evals/retention-policy.yaml` via `validate_retention_policy`, not `registry.policy_revision` | O14, O16 | `pipe/ars-gate5-grading-integrity` |
| WP5.2 | Execute the `execution_stage: gate5` rows of `p0-variant-matrix.yaml` (fake-claude/fake-codex, twice-run byte equality); wire real W7 parity evidence via `research_system/adapters/parity.py` so `parity_status` stops being the fail-closed sentinel | R8, O11 | `pipe/ars-gate5-variant-parity` |
| WP5.3 | Publish `ReleaseGateDecision` as a canonical W2 event; retire sentinel `canonical_event_ref="unpublished:p0"`; `eval release` rejects unresolvable refs | O12 | `pipe/ars-gate5-release-event` |
| WP5.4 | Release tranche S-014 (backup/restore + machine move; needs the 05-plan §7 deletion-verification extension to registered backup/restore topology), S-015 (supersession-cycle atomic rejection), S-016 (R3 provider outage; lands blocked-by-design via its H grader — that is a pass condition) | 05-plan §4.4/§7 | `pipe/ars-gate5-release-tranche` |
| WP5.5 | Owner-decision batch — produces `[DECISION]` vault entries, no code until decided | O15, R12, D-G5-1/3 | n/a |
| WP5.6 | Bounded independent review + integrated acceptance run → one canonical `ReleaseGateDecision` → Stephen's recorded acceptance = Gate 5 | O10 residual | n/a |

**DAG:** WP5.1 → (WP5.2 ∥ WP5.3 ∥ WP5.4) → WP5.6, with WP5.5 parallel throughout.
Dispatch WP5.4 first among the parallel three (long pole). Worktrees under
`.apm/worktrees/`, concurrency cap 3–4.

## 4. Owner decisions — surface, never guess (D-G5-1..4, scope plan §6)

- **D-G5-1 — M/H posture at Gate 5.** (a) accept foundation with explicit capability
  restriction (recommended; spec-consistent), or (b) live-grader threshold policy first.
  **Must be decided before WP5.6 dispatch.**
- **D-G5-2 — `DeleteEvidenceObject`** (O15): name is specified (04-plan:517); payload
  schema + emitted event are not. Design anchor: `DeleteEvidenceObject →
  EvidenceDeletionPending` (`replay.py:90` consumes it; nothing emits it). Decide before
  or during WP5.4; if deferred, S-014 scopes around it and O15 stays open with the
  restriction recorded.
- **D-G5-3 — invariant re-baselines.** WP5.2 and WP5.4 change the invariant values.
  Expected direction: `fixture_count 37→40`, `blocked_fixture_count 14→15` (S-016's H
  row), `result_count` recomputed from materialized packages plus variant rows. Each
  dispatch plan pre-registers exact new values; owner approval of the plan approves the
  re-baseline. Silent drift is a stop condition.
- **D-G5-4 — R12 confirmation.** Two provider-specific F-021 sizing rows (the
  no-wildcard rule at `fixture_package.py:231-241` forbids one provider-spanning row)
  were flagged in the PR #71 body; **merge is not a recorded confirmation**. Get a
  one-line `[DECISION]` recorded.

**Your first action after reading §1: confirm with Stephen that the scope plan itself
is approved, and put D-G5-1 and D-G5-4 in front of him. No WP5 dispatch before scope
approval. WP5.1 needs no D-G5 decision and can be authored (xhigh) immediately after.**

## 5. Stop conditions and invariant discipline

- `blocked_fixture_count: 14`, `candidate_status: "blocked"`, `result_count: 122`,
  `fixture_count: 37` hold until a dispatched, owner-approved plan explicitly retires
  them (old → new value, why, recomputation method, smoke asserting new values).
- `candidate_status` stays `"blocked"` through every WP5 tranche; only the WP5.6
  acceptance run may change it, and only if D-G5-1 and the full acceptance set permit.
- Failures at any point produce revision or stop — **the acceptance set is never
  weakened** (04-plan §4 Gate 5 wording; enforce it in Task Review).
- Aggregate parity percentages are diagnostic only; one missing critical control blocks.
- No scenario/executor may construct a passing terminal record (WP4 O5 precedent);
  executors derive observed evidence from stimulus only, never from `expected/`
  (anti-anchoring is binding); incoherent oracle → `fixture_error` + report to corpus,
  never bend the executor.

## 6. Workflow discipline (non-negotiable; enforced by hooks where possible)

- **Review-then-merge:** CodeRabbit review must conclude **before** merge, every PR.
  Merge via `gh pr merge` — never FF-push a local merge (marks the PR merged-on-arrival
  and CodeRabbit bails; hit on PR #54). Inline findings need
  `gh api repos/stephendor/TDL/pulls/<N>/comments` — `gh pr view --json comments`
  misses them.
- **Workers commit on their own branches and never merge; Manager merges to `main`.**
  Main working directory stays on `main`.
- **Worktree `.env` (mandatory):** after `git worktree add`, immediately
  `Copy-Item "c:\Users\steph\TDL\.env" "<worktree>\.env"` — without it
  `uv run --env-file .env` fails silently.
- **Worktree removal is manual-only** (explicit "sweep worktrees" trigger), and only
  for worktrees whose PRs are closed AND CodeRabbit concluded. Currently
  sweep-eligible: `.apm/worktrees/ars-p0-wp4-8-verdict-derivation`, the WP4.9
  worktree, three stale detached Codex worktrees.
- **Pre-dispatch (hook-enforced):** research-assurance triage per APM_RULES —
  classify lanes, name governing decisions/contracts, decide machine-checkable vs
  human-review-only, attach enforcement artifacts (binding tests, smoke assertions,
  schema checks). Passing software tests is not sufficient for research Tasks.
- **Dispatch plans follow the 04b format:** header (Goal/Status/Global Constraints),
  obligation register, research-assurance table, numbered tasks with exact
  files/interfaces/steps/commit messages, invariant smoke with exact expected outputs.
- **Commits:** `[PIPELINE] P00: <desc>` + Co-Authored-By trailer; multi-line messages
  via BOM-free temp file (`[IO.File]::WriteAllText` with `UTF8Encoding($false)`) and
  `git commit -F`; never `--no-verify`.
- **Vault:** every Task ends with the matching entry in
  `vault/04-Methods/Computational-Log.md` (junction to the real vault), **top-of-page
  reverse-chronological**, Referent/Supersedes lines when closing issues or changing
  prior analyses. Pre-registration entries **before** outcome-contingent runs.
  Read-reconcile-place before writing: parallel sessions may have touched the page.
  `vault_observe` is never a write path.
- **Quality gates per task:** `uv run ruff check research_system tools/ars
  tests/research_system` and `uv run pytest tests/research_system -q --no-cov`.

## 7. Machine-local facts (as of 2026-07-10)

- **`.venv` is handle-blocked for `uv sync`** (open handles across site-packages from
  long-lived MCP-server sessions; `cfgv` dist-info RECORD already damaged by partial
  attempts). **Use `uv run --no-sync` everywhere** — it is fully functional (338 tests
  pass under it). Durable fix pending: stop MCP sessions, delete `.venv`, fresh
  `uv sync`. Do not kill running processes to force this.
- Fresh worktrees have their own sync behavior; still copy `.env` (see §6).
- Windows 11 / PowerShell 5.1; no `&&` chaining in PowerShell; Bash tool available
  for POSIX syntax.

## 8. WP5.6 independence requirement

The bounded review must be **fresh-context**: a separate session that reads the plans,
registers, and code cold from disk — no shared conversation state with the sessions
that authored the dispatch plans or the implementations (correlated review is a failure
class this project's own fixture catalogue encodes). CodeRabbit provides the external
second family on each PR; the bounded review is in addition, at the depth of the
2026-07-07 WP4 full review. Its findings are dispositioned as revision or stop, never
as a relaxed criterion.

## 9. Definition of done

Gate 5 exits when the checklist at the end of the scope plan (§10) is fully checked:
WP5.1–5.4 merged through the gate; D-G5-1/2/4 recorded as `[DECISION]` entries; all
re-baselines pre-registered and approved; one canonically published
`ReleaseGateDecision` from the integrated acceptance run with any capability
restrictions explicit; bounded review delivered and dispositioned; **Stephen's recorded
acceptance**. Then, and only then, Gate 6 planning may begin.
