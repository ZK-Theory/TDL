# WP6 Plan-Suite Adversarial Review — Agent Prompt

**Created:** 2026-07-17
**Purpose:** Self-contained brief for an independent adversarial review of the merged
WP6 planning suite. Paste this file (or point a fresh agent at it) as the opening
instruction of a new session. Retained in `handoffs/` as review provenance.
**Routing guidance (house policy):** fresh context, no access to the authoring
session; cross-family reviewer preferred (Codex xhigh or equivalent) per D-006/P-029.
If the repository's `adversarial-design-review` skill is available in your session,
load it before starting.

---

## Your role

You are the independent adversarial reviewer for the ARS WP6 planning suite. You did
not author it. Your job is to attack it for material errors, authority leaks,
unenforceable claims, missing controls, and cross-document inconsistencies — and to
deliver a severity-graded findings report with a complete disposition table. Findings
produce **revision or stop** recommendations; they never weaken an acceptance set.

**Process context you must know:** the suite was merged to `main` by owner decision
without its own review gate (PRs #110, #113, #114 were merged directly). This review
is the compensating control. Its verdict governs whether the WP6.1/WP6.2 dispatch
plans may be approved for execution as written, not whether the merge happens — it
already has.

## Review subject (exact)

Review these files as they stand on `main` at commit `2695087` (the PR #114 merge).
If `main` has advanced past that commit in a way that touches these files, record the
drift as your first finding and review the current state.

1. `docs/plans/agentic-research-system/implementation/06-wp6-gate6-readiness-and-integration-plan.md` — WP6 master plan
2. `docs/plans/agentic-research-system/implementation/06a-wp6-1-runtime-task-lifecycle-plan.md` — WP6.1 runtime Task lifecycle
3. `docs/plans/agentic-research-system/implementation/06b-wp6-2-live-capability-plan.md` — WP6.2 live capability
4. `docs/plans/agentic-research-system/03-decisions-and-open-questions.md` — §"Post-Gate-5 owner directions recorded 2026-07-16" (P-031–P-034) only
5. `docs/plans/agentic-research-system/implementation/README.md` — WP6 index section only
6. `CONVENTIONS.md` — §"ARS Foundation Governance" (context for consistency checks; its two locks are Owner decisions, not review subjects)

## Fixed ground (do not re-litigate)

- Accepted designs W1–W8 and 06c, decisions P-001–P-030, and the Gate 3/4/5 review
  record. These are the measuring stick, not the subject.
- Stephen's accepted directions P-031–P-034 (wording confirmed 2026-07-17). Attack the
  suite's **implementation** of these decisions — gaps, contradictions, unenforceable
  renderings — not the decisions themselves.
- The Gate 5 acceptance decision (2026-07-17, merge `f49a27f`): D-G5-1(a) M/H
  restriction, D-G5-2/O15 deferral, G5.3-B(a) attribution, candidate `blocked`,
  `gate5_authorized=false`. Recorded in the vault Computational-Log 2026-07-17 entry
  and mirrored in `CONVENTIONS.md` §ARS Foundation Governance.

## Governing references (read before attacking)

- `04-parallel-specification-and-foundation-pilot-plan.md` §4 (Gate 6), §6 (pilot
  operating model), §7 (stop rules) — P-031 amends the pilot boundary here.
- `implementation/05-wp5-gate5-foundation-acceptance-plan.md` — §2 acceptance
  criteria, §6 owner record, §7 invariant re-baseline rule (the D-G5-3 process WP6
  inherits).
- Design sections cited by the suite: W2 §§10–21; W4 §§8–20 (esp. §10 profiles, §16
  provider boundary, §17 outage); W5 §§7–20, 26; W7 §§7–20; W8 §§7–21; 06c.
- `reviews/adversarial-p0-plan-suite-review-2026-07-01.md` and
  `reviews/adversarial-wp4-full-review-2026-07-07.md` — the depth and format bar.

## Attack surface (work through all ten; report null results explicitly)

1. **Gate A mapping accuracy.** The master plan maps blockers A2–A8 to WP6.1–WP6.4.
   Verify each claim about the current foundation against the live tree
   (`research_system/` — e.g., the reducers' actual event coverage, the parity module,
   the authority resolver, `foundation.yaml`). A mapping row that overstates or
   understates the implemented state is a finding.
2. **Owner-touchpoint hoisting (the Observation-76 pattern).** Diff the master plan's
   §8 exit checklist against every owner-gated precondition stated anywhere in 06a and
   06b prose ("Stephen's approval/acceptance", "pre-registered ... approved",
   "owner-gated"). Any precondition living only in sub-plan prose is an authority
   leak, even if every sub-plan is individually sound.
3. **WP6.2 security and cost boundary.** Attack T2's credential rule (no credential
   material in any event, receipt, object, or fixture; grep-based binding test), the
   cost-grant fail-closed exhaustion, the no-live-call-before-T2 rule, and S-016
   outage semantics preservation. Are these machine-checkable as stated, and are the
   stop conditions complete? Is there any path where a live call precedes the cost
   boundary or a threshold comparison defaults to pass?
4. **Gate 5 acceptance-condition consistency.** Does any WP6 wording silently weaken
   D-G5-1(a), O15 deferral, or the blocked-candidate state — in particular WP6.2 T7's
   M/H unblock mechanics ("evidence-driven, never administrative") and its
   pre-registration requirements?
5. **P-031 pilot amendment coherence.** Check the amended pilot boundary against
   P-026's text and 04-plan §4/§6: is the amendment's rendering in the suite complete
   and non-contradictory (pilot preflight predicates unchanged; the first ARS paper
   inheriting the paper-pilot criteria)? Identify any 04-plan or README sentence that
   still asserts the old boundary and is not superseded by a dated record.
6. **W11/WP6.5 scope soundness.** Does the planned portfolio/Discovery specification
   conflict with the W1 portfolio catalogue boundary ("portfolio state cannot declare
   a result accepted"), W2 `obj` records, P-004 exclusive ownership, or P-021
   non-shared paths — especially the vault-projection contract and the per-item
   ownership transitions for active Discovery items?
7. **Invariant re-baseline mechanics.** WP6.1 T8 and WP6.2 T7 pre-register invariant
   changes per the D-G5-3 process. Is the wording enforceable (exact old → new values
   in the dispatching plan revision, owner approval before execution, drift as stop
   condition), and is any invariant-changing task missing that requirement?
8. **Binding-test adequacy.** For every machine-checkable claim in the master plan §6
   and every per-task binding test in 06a/06b: is it an enforcement artifact by the
   CONVENTIONS locks (value-and-type, atomic rejection, fail-closed) rather than a
   description? Name each test that could pass while the claimed property fails.
9. **Dependency DAG correctness.** Both plans' DAGs and sequencing prose: hunt for
   premature-dispatch readings, missing edges (e.g., WP6.4's dependence on WP6.3;
   WP6.6 on WP6.1 *and* accepted W11), and any parallelism that violates exclusive
   heavy-compute or worktree-concurrency rules.
10. **Register integrity.** P-031–P-034 entries: protocol-complete (status, decision,
    rationale, evidence, affected specifications, migration consequence)? Any
    affected-specification list missing a spec the decision actually touches? Any
    contradiction between the register text and the suite's rendering of it?

## Verification obligations

- Every finding cites file and line and quotes the live text; verify against the
  working tree, never from memory or this prompt.
- Claims about the implemented foundation are verified in `research_system/` source,
  not inferred from plan prose.
- A referenced artifact that does not exist where the suite says it does is a
  finding, not a guess.
- Research-assurance lanes: declare them (expected: Output/Provenance primary;
  Topology/Stochastic only where WP6.3/threshold-calibration content is judged).

## Constraints

- Read-only except your review report. Do not edit the reviewed files, do not
  implement anything, do not run research computation. `uv run --no-sync` for any
  verification commands; do not resync the environment.
- Do not consult or reconstruct the authoring session's reasoning; the documents
  stand or fall as written.

## Output contract

Write `docs/plans/agentic-research-system/reviews/adversarial-wp6-plan-suite-review-<YYYY-MM-DD>.md` containing:

1. **Header:** review date, reviewed commit, reviewer identity/family/context basis
   (state independence honestly per P-022).
2. **Findings**, severity-graded per house convention — Critical (C-n), Major (M-n),
   Minor (m-n), Informational (i-n) — each with: location, quoted evidence, why it is
   a defect, and the exact required change or stop.
3. **Attack-surface disposition table:** all ten surfaces above with outcome
   (findings | clean) — null results stated, not implied.
4. **Decision disposition:** for each of P-031–P-034 and D-G6-1..5, whether the
   suite renders it faithfully.
5. **Verdict:** `accept` | `accept_with_required_changes` | `reject`, with the exact
   condition set that must clear before the WP6.1/WP6.2 dispatch plans may be
   approved.

Do not soften findings for consistency with the merge having already happened; the
merge is not evidence of correctness.
