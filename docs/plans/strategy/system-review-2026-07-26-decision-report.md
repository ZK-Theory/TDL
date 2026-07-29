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
- **Seven TDL observations have now received evidence-based closure**; three
  MathUni-owned observations from the original closure table were excluded.
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

**Decision (2026-07-28, Stephen):** `[ ] APPROVE BLOCKING GATE` · `[x] APPROVE WARNING FIRST`
· `[ ] DEFER`

### D2 — Approve collision-resistant observation IDs

**Observation:** 69  
**Problem:** parallel sessions produced duplicate observation numbers 58, 59,
and 85; `max+1` is not concurrency-safe.

**Proposed action:** approve Option A in
[`proposal-observation-log-ids.md`](system-review-2026-07-21/proposal-observation-log-ids.md):
new observations use a timestamp/ULID identifier; historical integer IDs remain
unchanged and receive suffix annotations only where ambiguity matters.

**Decision (2026-07-28, Stephen):** `[x] APPROVE ULID/TIMESTAMP` · `[ ] REQUIRE LOCKING HELPER`
· `[ ] DEFER`

### D3 — Approve a merge-seam gate

**Observation:** 84  
**Problem:** two individually green PRs composed into failing tests on `main`.

**Proposed action:** choose one option from
[`proposal-merge-seam-gate.md`](system-review-2026-07-21/proposal-merge-seam-gate.md).
The lowest-cost starting point is requiring branches to be current with `main`
before merge; the strongest option is a merge queue/prospective-merge test.

**Decision (2026-07-28, Stephen):** `[x] REQUIRE UP-TO-DATE BRANCH` · `[ ] MERGE QUEUE`
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

**Decision (2026-07-28, Stephen):** `[x] APPROVE BOTH` · `[ ] TESTS ONLY, NO RECEIPTS`
· `[ ] DEFER`

## Decisions recorded — 2026-07-28

All four decisions are made; implementation is now four separate bounded tasks,
none of them started.

| | Decision | Rationale |
|---|---|---|
| D1 | **Warning first** | Five new checks straight to blocking would halt legitimate dispatches before any false-positive evidence exists. Promote to blocking once the warning stream is clean. |
| D2 | **ULID/timestamp** | Removes the race rather than coordinating around it. |
| D3 | **Require up-to-date branch** | Lowest-cost option available immediately as branch protection. A merge queue would cost a suite run per merge — currently 72 minutes for `tests/research_system` alone. |
| D4 | **Approve both** | Receipts are what distinguish "configured" from "executed", which is the gap that let a hook sit in `.git/hooks` for 47 days doing nothing. |

### Evidence added since the review

- **D2 is not confined to the observation log.** On 2026-07-28 a handoff was
  written as `27-…` while `27-wp6-3-pack-implementation-brief.md` already
  existed on `main`; the collision was caught by chance and renumbered to 28.
  Whatever identifier scheme is adopted should cover handoff numbering too.
- **D4 has a live instance.** `install-git-hooks.py`, one of the two gates in
  scope, crashes when run from a linked worktree: it derives paths from
  `REPO_ROOT` while `core.hooksPath` points into the main checkout, raising
  `ValueError: '…\.githooks\pre-commit' is not in the subpath of
  '…worktrees\<name>'`. The hooks themselves run correctly — verified by
  actual commits — but the verifier that exists to prove liveness cannot run
  from a worktree, which is where much of the work happens. Worth folding into
  the D4 fixture set as a path-resolution control.

### Not covered by this report

Observations 133–136 were logged on 2026-07-28, after the review ran.
135 and 133 are implemented in PR #181; 134 in PRs #176 and #179; 136
(a hand-enumerated schema set that went stale) is open and unassigned.

## Evidence-based closure completed — 2026-07-29

The original table mixed seven TDL closures with three MathUni-owned
observations. Per Stephen's 2026-07-29 scope ruling, observations 102, 113, and
119 were not inspected or changed here. The seven TDL observations were
re-resolved individually against `main` at
`07335de6198ca340b08254d1390e2131b8c8dd71`; the two missing remediations were
implemented and verified on branch `codex/system-review-evidence-closures`.

| Observation | Disposition | Current closure evidence |
|---|---|---|
| 90 | **ACTIONED** | `--verify-state` re-hashes recorded state even when the two skill trees are identical. The matching-state, stale-state, and EOL-invariance controls passed; a live run verified all 68 recorded hashes. |
| 92 | **ACTIONED** | The acceptor passes `manifest.import_modules` as named build targets. Controls proved that named targets are built, a bare no-target “Nothing to build” result is rejected, and an already-built named target remains admissible. |
| 94 | **ACTIONED previously** | Archived on 2026-07-27. `core.hooksPath=.githooks`; `.githooks/post-commit` is tracked; `.git/hooks/post-commit` is absent; and `.repowise/.update.log` records positive firings through `ee38ea596788b9ebb74a54362cf7f5a5803dab14`. |
| 106 | **ACTIONED on closure branch** | `AGENTS.md` now requires both the symbolic branch and `git merge-base --is-ancestor <expected-base> HEAD` before writes in stacked/dependent work. |
| 108 | **ACTIONED on closure branch** | `.githooks/pre-commit` now invokes the populated main-checkout interpreter directly instead of `uv run`. A Git-Bash linked-worktree control starts without `.venv`, routes both Python gates through the main interpreter, and proves no worktree-local `.venv` appears. |
| 112 | **ACTIONED** | The active global Codex instructions contain the validation ladder: exact affected tests first; package expansion only for a named dependency/risk trigger; full suite only for an explicit gate, cross-cutting change, or final-head confidence; package suites may not be called “focused.” |
| 114 | **ACTIONED** | Commit `ced019081c77c69087ce847ffb897695a97b1297` on `codex/token-efficiency-audit-fresh-head` contains the lineage-aware census procedure, complete byte-prefix/hash manifest, and child-local boundary logic excluding inherited parent history. Its frozen replay reported zero hash, parse, lineage, or component-identity failures across 480 retained JSONL files. |

Focused validation on the closure branch: seven direct controls passed;
`.githooks/pre-commit` passed Git-Bash syntax validation; touched-file
`git diff --check` passed. No package or full suite was run because the direct
controls passed and no wider dependency trigger was present.

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
