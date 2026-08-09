# System Review 2026-08-09 — Campaign A Closeout

**Campaign:** Dispatch and state currency

**Decision:** Approved by Stephen on 2026-08-09

**Candidate branch:** `codex/system-review-2026-08-09-a-dispatch`

**Base:** `9736c900fd4f72e84b2208eeff0dcfb2a2b44106`

**Result:** 13 of 13 mapped observations resolved

## Observable change

The dispatch guard now binds a parallel task to the worktree that owns its
branch and re-resolves all state that can decay between planning and execution.
The task-state manifest covers deliverables, blockers, planned contracts,
rooted inputs, trackable outputs, independent lanes, production registries,
derived-field preimages and semantics, and authoritative sources for required
fields. During the existing warning-first calibration, stale or incomplete
state is made explicit without silently changing the approved enforcement
policy. Branch/worktree ownership is blocking because a duplicate writer is
never a valid calibration case.

## Observation dispositions

| Observation | Disposition | Evidence |
|---|---|---|
| 58 | ACTIONED — already covered and retained | Existing-deliverable predicates in `check_state_manifest` warn when a claimed missing deliverable is already complete. |
| 65 | ACTIONED — already covered and retained | Rooted input checks and manifest-backed file claims replace unverified prompt assertions. |
| 70 | ACTIONED — already covered and retained | Per-blocker predicates re-resolve inherited blockers against the current workspace. |
| 73 | ACTIONED — already covered and retained | `planned_contracts` checks resolve every named contract before dispatch. |
| 74 | ACTIONED — already covered and retained | Every input carries `root: worktree|proj_root`; the guard resolves the declared root. |
| 77 | ACTIONED — current trigger contract retained | `writing-plans-extras` claims ARS/TDL plan decomposition; repository skill routing requires loading matching skills before task work. No duplicate trigger prose was added. |
| 80 | ACTIONED — expanded in this campaign | Independent `lanes` carry a completion predicate and next gate; a completed lane warns to skip author dispatch and advance. |
| 88 | ACTIONED — current currency rules plus expanded ownership check | Review skills already require current-HEAD reconciliation; the dispatch guard now also rejects a workspace that does not own the branch. |
| 100 | ACTIONED — expanded in this campaign | `registries` require the exact source symbol and an explicit `writable` or `certified_unchanged` disposition. |
| 124 | ACTIONED — already covered and retained | Blockers are represented as individually executable predicates, so a stored verdict is not consumed as one undifferentiated conclusion. |
| 140 | ACTIONED — expanded in this campaign | Every schema `required_field` names its authoritative source and an executable resolution check. |
| 01KYY7DWPYBAQX3P9Q422TDZH0 | ACTIONED — expanded in this campaign | Parallel dispatch is blocking unless the resolved workspace is the branch-owning worktree; an equal-commit detached checkout is rejected. |
| 01KZ1V1SERAEPB2ASJDMXRJ80F | ACTIONED — expanded in this campaign | Registry dependency closure, derived-field preimages/semantics, and required-field sources are all explicit manifest sections. |

## Controls and validation

- Positive owner control: a parallel workspace equal to the branch owner passes.
- Negative owner control: a detached duplicate path at the same logical task
  identity fails and reports both the requested workspace and actual owner.
- Positive manifest control: complete/incomplete lanes, a real registry symbol,
  a derived-field preimage, and a resolved required-field source are classified
  independently.
- Near-miss controls: malformed lane predicate, missing registry symbol, invalid
  registry disposition, empty field semantics, and failed required-field
  resolution all produce explicit warnings.
- Targeted test result: `30 passed` across
  `tests/provenance/test_manager_dispatch_check.py` and
  `tests/tools/test_sync_agent_skills.py`.
- Dual-tree result: `tools/sync_agent_skills.py --check` reports every authored
  `.agents/skills` file byte-identical to its `.claude/skills` mirror.
- Guide and patch hygiene: `--check-guides` and `git diff --check` pass.

## Simplification disposition

No new skill or parallel dispatch checker was created. The change extends the
existing task-state manifest and its existing authoring skills. Repeated prose
was avoided where repository-level skill routing or current review-currency
rules already supply the control.
