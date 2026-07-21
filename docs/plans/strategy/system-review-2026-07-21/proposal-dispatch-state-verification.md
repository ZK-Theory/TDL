# Proposal: verify on-disk state before dispatch / handoff / acceptance

**Status:** PROPOSAL — awaiting Stephen's approval (ARS gate change; not self-applied)
**Date:** 2026-07-21 · **Source:** weekly system review, skill-observations 58, 65, 68, 70, 73, 74, 76, 79, 80
**Owner decision required:** yes (gate + skill-guidance change)

## Problem

The single largest recurring failure cluster in the observation log: a dispatch,
handoff, or pre-registration prompt states things about the world as **facts**
that are already stale by execution time, and an agent acts on the assertion
instead of checking. Recurrences confirm it is systemic, not incidental:

- **58 → 80:** a task-prompt's "not dispatched / open" state was stale; the
  deliverable was already on disk. Correct move was to convert the author lane
  to review-only, not re-dispatch. It recurred verbatim.
- **68 → 73:** pre-reg `planned_contracts` reached the Worker unmaterialised;
  the extraction-agent rescue worked, then the *same* thing happened again.
- **65:** a dispatch prompt's claims about reference files are assertions, not
  findings — scope must be verified before trusting it.
- **70:** a Handoff prompt's "standing facts" and "blockers" decay fastest —
  the blocker must be verified before inheriting the plan built on it.
- **74:** pre-reg input paths carry no root declaration — a Worker cannot tell a
  committed file from a `PROJ_ROOT`-only intermediate until the script crashes.
- **76:** an owner-touchpoint precondition buried in a sub-plan's prose never
  surfaced into the gate checklist.
- **79:** brief-mandated output paths can be gitignored — trackability must be
  verified before authoring.

The common shape: **self-attestation of state** with **no re-validation trigger**
— exactly the two failure mechanisms the project's own failure inventory names.

## Proposed mechanism

Add a **state-verification step** to the dispatch/acceptance gates, driven by an
explicit machine-checkable manifest in each Task Prompt rather than prose:

1. **Extend `manager_dispatch_check` / `dispatch-readiness-guard`** (`.claude/hooks`)
   to require, and then verify on disk, for every dispatched Task:
   - each claimed **deliverable**: does the file already exist at the stated
     path? (if yes → the lane is review-only, not a fresh dispatch — obs 58/80);
   - each claimed **blocker**: is it still true right now? (re-run the one-line
     check that established it — obs 70);
   - each **planned_contract**: is it materialised in `contracts/`? (obs 68/73);
   - each **input path**: is its root declared (committed vs `PROJ_ROOT`-only)
     and does it resolve? (obs 74);
   - each **output path**: is it git-trackable, not gitignored? (obs 79).
2. **A negative control** proving the gate fires: a fixture Task Prompt whose
   deliverable already exists on disk must be blocked/flagged, not dispatched.
3. **Skill propagation** (a short "verify state on disk before acting" step) to
   `pre-reg-to-dispatch`, `tda-handoff`, `tda-task-brief-from-plan`,
   `apm-communication` — pointing at the gate, not restating it.

## Owner decision points

- Is the Task-Prompt state manifest (deliverables/blockers/contracts/inputs/
  outputs as structured fields) acceptable as a required dispatch input?
- Should the gate **block** (exit 1) on a stale-state finding, or **warn**?
- Scope: apply to all dispatches, or only result-bearing (assurance-lane) ones?

## Non-goals

Not a re-litigation of any specific past dispatch. Not a change to the ARS
review ladder. Purely: convert "the prompt says X about the world" into "the
gate checked X on disk before anyone acted".
