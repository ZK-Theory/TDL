# Weekly Research-System Review — Decision Report

**Review date:** 2026-07-26  
**Scope:** TDL research system, including skills, hooks/gates, contracts,
mathematical invariants, ARS/process, and records  
**Source:** `C:\Users\steph\.claude\skill-observations\log.md`  
**Status:** Decision packet for Stephen; no gate, invariant, contract, or
workflow-design recommendation below has been self-applied.

## Executive summary

The autonomous part of the review applied 22 SKILL/low-risk RECORD observations
to 11 synchronized skills. Forty-three observations remain OPEN. They are not
one undifferentiated approval queue:

- **Four concrete decisions are ready now** and have bounded implementation
  shapes.
- **Ten observations appear already remediated** and need evidence-based closure,
  not new design.
- **Fourteen TDL design items need separate scoped reviews** before implementation.
- **Twelve MathUni items belong in that repository**, not TDL.
- **Three items remain deliberately deferred** because the correct ownership or
  enforcement surface is unresolved.

## Decisions ready for Stephen

### D1 — Approve structured dispatch-state verification

**Observations:** 58, 65, 70, 73, 74, 80  
**Problem:** dispatches and handoffs can carry stale task state, incomplete scope,
unmaterialized contracts, and rootless paths as authoritative prose.

**Proposed action:** approve the existing
[`proposal-dispatch-state-verification.md`](system-review-2026-07-21/proposal-dispatch-state-verification.md).
Add a machine-checkable state manifest to task prompts and extend
`manager_dispatch_check` / `dispatch-readiness-guard` to verify:

1. claimed deliverables do not already exist;
2. blockers remain live;
3. every `planned_contracts[].id` is materialized;
4. every input declares `worktree` or `proj_root`;
5. every output path is trackable.

**Required controls:** existing-deliverable, missing-contract, wrong-root, and
gitignored-output fixtures.

**Decision requested:** `[ ] APPROVE BLOCKING GATE` · `[ ] APPROVE WARNING FIRST`
· `[ ] DEFER`

### D2 — Approve collision-resistant observation IDs

**Observation:** 69  
**Problem:** parallel sessions produced duplicate observation numbers 58, 59,
and 85; `max+1` is not concurrency-safe.

**Proposed action:** approve Option A in
[`proposal-observation-log-ids.md`](system-review-2026-07-21/proposal-observation-log-ids.md):
new observations use a timestamp/ULID identifier; historical integer IDs remain
unchanged and receive suffix annotations only where ambiguity matters.

**Decision requested:** `[ ] APPROVE ULID/TIMESTAMP` · `[ ] REQUIRE LOCKING HELPER`
· `[ ] DEFER`

### D3 — Approve a merge-seam gate

**Observation:** 84  
**Problem:** two individually green PRs composed into failing tests on `main`.

**Proposed action:** choose one option from
[`proposal-merge-seam-gate.md`](system-review-2026-07-21/proposal-merge-seam-gate.md).
The lowest-cost starting point is requiring branches to be current with `main`
before merge; the strongest option is a merge queue/prospective-merge test.

**Decision requested:** `[ ] REQUIRE UP-TO-DATE BRANCH` · `[ ] MERGE QUEUE`
· `[ ] MAIN-PUSH DETECTION ONLY` · `[ ] DEFER`

### D4 — Approve controls for the two unwatched hook gates

**Observations:** 121, 122  
**Problem:** `install-git-hooks.py` and `mirror-tree-guard.sh` lack paired
negative controls and durable evidence that configuration became execution.

**Proposed action:**

- `install-git-hooks.py`: fixture tests for missing active directory, missing
  hook, and non-executable tracked hook; retain a successful path-resolution
  receipt.
- `mirror-tree-guard.sh`: hermetic allow/deny tests for POSIX and Windows paths,
  linked-worktree prefixes, and malformed-input fail-open; retain a bounded
  execution receipt in the hook harness.

**Decision requested:** `[ ] APPROVE BOTH` · `[ ] TESTS ONLY, NO RECEIPTS`
· `[ ] DEFER`

## Verify and close before designing more work

These observations describe defects whose apparent remediation is already
present in current files or in the observation itself. The next action is a
bounded verification run followed by `ACTIONED`, not another proposal.

| Observations | Closure evidence required |
|---|---|
| 90 | Run the sync-state stale-hash negative control and prove identical-tree success rechecks recorded hashes. |
| 92 | Run the named-target Lean build negative control; prove bare/default-target success cannot certify acceptance. |
| 94 | Confirm tracked `.githooks/post-commit` is active and record one safe positive execution signal. |
| 108 | Exercise linked-worktree pre-commit routing and prove no worktree-local venv bootstrap occurs. |
| 112 | Confirm the current validation-scope policy is present in global/project instructions and close the PROCESS observation. |
| 113, 119 | Re-run the MathUni validator self-tests that already claim near-miss, absent-input, and malformed-input coverage. |
| 102 | Verify the stale `update_unlocks.py` caution was corrected in its owning plan/record. |
| 106 | Verify branch ancestry—not only branch name—is now required by the active startup/dispatch instructions. |
| 114 | Verify the token-efficiency audit procedure now freezes the full evidence universe and excludes inherited fork history. |

## TDL items requiring scoped design review

These are real recommendations, but approving them as a single batch would
combine unrelated authority and scientific risks.

| Observations | Theme | Required next artifact |
|---|---|---|
| 86–87 | Anti-anchoring equality obligations and machine-diffable constant pins | One contract-design review covering anchor/equality identity and negative controls. |
| 88 | Mid-session branch changes masquerading as content corruption | Decide whether branch-state snapshots belong in tooling or session procedure. |
| 91 | External-credential liveness | A non-secret provider-readiness preflight and expiry/failure receipt design. |
| 100 | Canonical transition ownership before path scoping | WP6.2 authority review; freeze owner and identities before dispatch. |
| 101, 103, 104 | Exact-byte Windows validation fixtures | Consolidate into one canonical clone recipe: full Git history, `core.autocrlf=false`, `core.longpaths=true`, external venv, clean-root proof. |
| 105 | Research-value gate for assurance controls | ARS owner decision on when an orthogonal control becomes blocking scope. |
| 110 | Repeated nonzero last-call token telemetry | Independent telemetry invariant: cumulative advance, fork-history exclusion, and duplicate-record rejection. |
| 111 | Contradictory enum boundary accepted by exact materialization | Contract-authority review: exact-byte reproduction cannot override relational inconsistency. |
| 117 | ProviderCommand/v2 source-preimage and provider identity | Shared live-issue binding object plus near-miss controls for projection, model selector, and timeout. |
| 120 | `HEAD`-based byte proof cannot certify staged bytes | Decide whether tests accept explicit revision/index or mandate post-commit certification. |

## MathUni observations — route to the owning repository

**Observations:** 96, 97, 98, 99, 109, 113, 115, 118, 119, plus the
MathUni-specific part of 102 and 107.

These concern syllabus/lesson validators, unit-ID fan-out, mathematical lesson
review, console encoding, drift tests, stale-base PR reachability, and
`.gitattributes`. They should be copied into one MathUni gate-review issue or
decision packet and verified against that repository's current head. TDL should
retain the cross-cutting lessons, but it should not implement MathUni gates.

Recommended order:

1. close already-fixed validator controls (113, 119);
2. add merged-head reachability protection (118);
3. review control coverage across every lint branch (115);
4. handle ID/source migration gates (96–97);
5. define the human mathematical-correctness rubric (98, 109);
6. resolve console encoding and line-ending policy (99, 107).

## Explicit deferrals

| Observation | Reason |
|---|---|
| 64 | `apm-communication` has intentional environment-specific copies outside the synchronized skill manifest. Editing it autonomously would violate the dual-tree rule; decide its canonical source first. |
| 77 | The skill trigger is already correct. The failure is activation/liveness, so adding more prose would not fix it; address through hook/dispatcher design only if D1 does not subsume it. |
| 107 | The named record is in MathUni and was unavailable in the TDL-only review; route it with the MathUni packet. |

## Coverage answer

Yes. This week included failures caught by inspection or external review rather
than by a gate/contract/invariant: exact materialization preserving a
contradictory enum (111), lesson drift missed by every mechanical gate (109),
duplicate token telemetry (110), incomplete gate self-tests (115, 119), stale
PR-base reachability (118), and byte-proof namespace confusion (120). Each is
represented above; no additional unlogged coverage gap was identified during
the 2026-07-26 review.

## Applied changes and validation

The autonomous review changed 11 synchronized skills and refreshed
`tools/skill_sync_state.json`; it did not stage or commit anything.

- 18/18 `test_sync_agent_skills.py` tests passed.
- `sync_agent_skills.py --check` passed.
- `sync_agent_skills.py --check-guides` passed.
- Active Git hook-path verification passed.
- Touched-file `git diff --check` passed.
- Repository-wide `git diff --check` remains red only on pre-existing trailing
  whitespace in `.claude/CLAUDE.md`.

## Recommended immediate response

Stephen can make the review actionable with four short choices:

1. D1: blocking gate, warning-first, or defer;
2. D2: timestamp/ULID, locking helper, or defer;
3. D3: up-to-date branch, merge queue, detection-only, or defer;
4. D4: tests plus receipts, tests only, or defer.

Once those choices are recorded, implementation should be dispatched as
separate bounded tasks; the remaining TDL table should go through scoped design
reviews, and the MathUni list should move to its owning repository.
