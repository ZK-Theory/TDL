# ARS Gate 7 prep handoff: the scope note, the opening condition and the intake refresh

**For:** the Gate 7 prep, planning and documentation session (06s §7), worktree
`.claude/worktrees/gate7-prep-docs-5202cf`, and any session that resumes it.

**Capability status:** Gate 6 is CLOSED (P-058, "06s Gate 6 Phase 5 is closed", PR #381 `df5ba1ec`; the
post-merge frozen-checkout replay is PR #386 `bb9d91d4`; P-061 is PR #387 `3fa437a1`). Gate 7 is NOT open. This
track produces documents and reviews only.

**Base:** cut from origin/main at `3fa437a1` (2026-10-21). Any resume must confirm ancestry from `3fa437a1`.

**Predecessor:** `handoffs/01M4ZCC87J9P0GYGYJVWN3SECP-wp6-phase5-handoff.md` (Phase 5). Its live-run mechanics do
not carry over: nothing in this track runs live.

## Background

TDL's Agentic Research System (ARS) closed Gate 6 on 2026-10-21. Stephen recorded the closure in P-058 ("06s Gate
6 Phase 5 is closed") via PR #381 (`df5ba1ec`). PR #386 (`bb9d91d4`) recorded the post-merge frozen-checkout
replay. PR #387 (`3fa437a1`) recorded P-061. Jira KAN-12 and KAN-103 are Done.

The live run:

- A fresh store, `C:/Users/steph/TDL-ARS-G6-Control` (91 events), was bound to M2
  `4d867d85574dcf90300f059ab1fd52324be3c85a`.
- A SPEC-01 Assay reached a mechanical PARK. It was independently outcome-reviewed, and Stephen resolved it at
  `decide_spec_01` as PARK, with revisit triggers R1 to R6 and the rule.
- The Task and the ProjectUseDecision were accepted. The ProjectUseDecision is `retain_experimental_benchmark`,
  with no scientific claim.
- Replay, backup and an evidence-only restore all passed; the final independent evidence review returned PASS WITH
  FINDINGS.
- SPEC-02 ran nothing.

Stephen has triggered the Gate 7 documentation track (06s §7). Gate 7 is "Legacy research integration". Its first
named subjects are the suspended legacy papers P01-A (JRSS-A) and P01-B (JRSS-B). Both stay `legacy_owned` under
P-026 and P-034 until per-item W9 ownership transitions.

Stephen on the opening condition (2026-10-21): "SCALE-01 was replaced/superseded by the gate 6 run and we can
change the opening condition since we have run the system up to the promotion/park/kill point (i think). At this
point we could run SCALE-01 but I'm not sure it adds anything."

Stephen controls dispatch, CodeRabbit, merges, every live store and provider operation, and every acceptance.

## Hard boundaries

- Documents and reviews only: no implementation, migration, dispatch, pilot or compute.
- No write to any ARS store, including `C:/Users/steph/TDL-ARS-G6-Control` and the scratch stores.
- Do not touch `papers/P01-A-JRSSA/`, `papers/P01-B-JRSSB/`, `.apm/` state or the vault Discovery `_backlog.md`.
- No Jira create, transition or edit until Stephen approves a Jira plan.
- Never edit an accepted decision in place; propose old→new wording for Stephen's acceptance.

## Read first (primary authority; briefs never replace these)

- `implementation/06s-gate6-delivery-replan-and-gate7-integration.md`: §7 (G7-A, G7-B, G7-C), §8 capability
  reporting, §9 Jira rules.
- `handoffs/07-w9-gate7-legacy-integration-authoring-brief.md`: §3 intake manifest, §4 constraints.
- `implementation/06l-wp6-7-legacy-consolidation-sequencing.md`: §4 authority and path rules, §5 Steps 0 to 7, §6.
- `handoffs/14-wp6-gate6-7-handover.md` (planning clashes G7-A must reconcile) and `16-wp6-gate6-7-jira-plan.md`.
- `03-decisions-and-open-questions.md`: P-026, P-031, P-032, P-033, P-034, P-050, P-057, P-058 (closure and known
  limits), P-060, P-061.
- `00-master-transition-plan.md` §8; `04-parallel-specification-and-foundation-pilot-plan.md` §4 (no Gate 7
  section yet).
- `implementation/06s-phase5-runbook.md` §1, §3, §6: what the live run did and did not exercise.
- The W0 manifest and addendum under `transition/`; `docs/plans/strategy/P01-Claim-Trace-Audit-2026-07-17.md`;
  `docs/plans/strategy/APM-Failure-Inventory-to-ARS-Invariants-2026-07-17.md`.
- Branch `docs/ars-gate7-legacy-integration-brief` for prior drafts. As of 2026-10-21 no
  `design/09-migration-and-pilot.md` exists in any commit.

## Known issues the plan must handle

1. **Opening condition.** 06l Step 1 and handoff 07 (§1, §5) gate Gate 7 opening on "Gate 6 pilot-promotion
   evidence"; handoff 07 also says the machinery is proven on SCALE-01 first. In fact Gate 6 closed on a PARK with
   no PROMOTE, P-050 removed SCALE-01 from Gate 6 closure, and 06s §7 asks only for "Gate 6 closure evidence" plus
   a separate owner authorization. Verify from P-058 and the runbook which lifecycle actions ran live (through
   `decide_spec_01` PARK, closure and result) and which were only assembled and tested on scratch or excluded
   (PROMOTE→SPEC-02, revisit and retry; OR-008 to OR-011 were `intentional_exclusions` per P-061). Propose old→new
   wording replacing the pilot-promotion bar with one the record meets, with rationale. Recommend on SCALE-01
   (drop as an opening condition, or run it). Stephen decides.
2. **Intake manifest currency.** Refresh handoff 07 §3:
   - add P-061's SPEC-01 continuation as Gate 7+ intake (a new route-package version admitting OR-009 to OR-011, a
     retry Assay with its own Task and Attempt, SPEC-02 v1.2.0 plus R6 drafted outside the repo, the R4 crosswalk
     documentation task authorized only when the later gate opens, the R5 PCA-spectrum threshold
     pre-registration; OD-1 to OD-8 binding);
   - add the P-058 follow-ups: public writers for the governing scientific-review record and the verify-restore
     payload;
   - note P-060 (the 06t pin split): activatable now Gate 6 is integrated, explicitly not a Gate 7 prerequisite;
     list it as a separate standalone job for Stephen;
   - re-check each legacy P01 item against current main and the vault Computational-Log: T1.41 double-null panel;
     the Markov-2 α=1 W₂-only recompute; the §3 park set; H1 to H9; T1.20; H3.
3. **P-033.** It requires full live capability (live transports, parity, live-grader policy, evaluated profiles)
   before any R2 research dispatch under ARS. Determine whether it binds Gate 7's compute items (T1.41, the
   Markov-2 recompute) and what that implies for sequencing. Surface it; do not resolve it.
4. **Stale wording.** Handoff 14's clashes, the WP6.7 "hold" wording, and handoff 07 statements that predate P-050
   and P-057.

## First deliverable (stop for Stephen's decision before drafting G7-A to G7-C)

A current-state scope note under `implementation/` with the next free 06-series letter, containing:

- a status table of every Gate 7 input with source pointer and verified state;
- the proposed scope and order of G7-A, G7-B, G7-C and of the later 06l Steps 1 to 7;
- the opening-condition proposal and the SCALE-01 recommendation;
- the refreshed intake manifest;
- the P-033 question;
- a proposed Jira plan (KAN-22, KAN-23 to KAN-26, KAN-60, KAN-21; new issues only if needed);
- the explicit owner decisions needed, each with a recommendation.

Present it to Stephen in chat with a short summary, then stop. Do not draft W9 or the Gate 7 definition until he
accepts the scope.

## After acceptance (later turns, on Stephen's word)

- Draft G7-A (W0 addendum and bounded delta review), G7-B (`design/09-migration-and-pilot.md`) and G7-C (the
  Gate 7 section in 04-plan §4, intake manifest by pointer, old→new P-026, P-034 and WP6.7 wording).
- Each document gets an independent adversarial review by a distinct agent session (`adversarial-design-review`),
  then reconciliation, then Stephen's acceptance of the exact revision.
- Review-then-merge: push and open PRs only when Stephen asks. He handles CodeRabbit and merges.

## Conventions

- Branches are `docs/<desc>`.
- Commits are `[DECISION] P06: …` or `[PIPELINE] SYS: …`, written to a BOM-free temp file and passed with
  `git commit -F`, ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never `--no-verify`.
- Never compose prose through shell heredocs or `python -c`; use Write and Edit.
- End each substantive turn with the matching vault entry (`vault/04-Methods/Computational-Log.md`, newest first,
  for any `[DECISION]`), plus a daily note if there is commentary worth keeping.
- Invoke the research-observer skill at session start.
