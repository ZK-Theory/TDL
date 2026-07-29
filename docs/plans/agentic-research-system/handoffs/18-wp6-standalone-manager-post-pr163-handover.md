# WP6 standalone manager handover after premature PR #163 merge

## Purpose of next session

Continue central management of WP6 as a **standalone task set, not APM**. The
first vertical action is to resolve the governance breach created when PR #163
was merged before its mandatory CodeRabbit review concluded. Do not begin later
WP6 implementation until the exact recovery path is agreed and executed.

## Active paper/project

- Repository: `stephendor/TDL`
- Programme: Agentic Research System, WP6
- Jira project: Topology (`KAN`)
- Active issue: [KAN-55](https://nexusstephen.atlassian.net/browse/KAN-55)
- WP6 tracker: [KAN-53](https://nexusstephen.atlassian.net/browse/KAN-53)

## Current state

- PR [#163](https://github.com/stephendor/TDL/pull/163), `[PIPELINE] P00: add
  WP6.2 T3/T4 live-issue binding contract`, was merged at
  `2026-07-25T22:32:53Z`.
- The merge was premature: the repository requires CodeRabbit review to
  conclude before every PR merge. Opening a PR automatically requests that
  review when budget is available; Stephen monitors it.
- No recovery mutation has been authorized or performed.
- KAN-55 is correctly **In Progress**, not Done. Its composite T1b-M/T1b-H
  evidence and the formal `06b/06` gates remain incomplete.
- Hard stop remains in force: no provider issue, claim, or runtime grant.

## Workflow system

`standalone`

This is not an APM task set. Do not initialize an APM manager, create `.apm`
records, or use numbered APM handoff procedures.

## Packet predecessor

- Whole-WP6 predecessor:
  `C:\Users\steph\.codex\worktrees\00c6\TDL\docs\plans\agentic-research-system\handoffs\17-wp6-plan-whole-handover.md`
- T3/T4 authoring brief:
  `docs/plans/agentic-research-system/handoffs/13-wp6-2-t3-t4-live-issue-binding-contract-brief.md`

## Files and artifacts

- PR head/wrapper: `26881e0a8a6fd8d2b05046cceb88e9a5c5e0e656`
- Accepted candidate, direct parent of wrapper:
  `7cd8afe8b47e9d75b6848d0e84e14362c227a4da`
- Accepted candidate tree: `5e090d486f9d6f91d270f78851f5ad523549253f`
- Premature merge commit on `origin/main`:
  `1c41f3186ff0b154601fd461334186f8059b520e`
- PR branch: `codex/wp6-2-t3-t4-live-issue-contract` (retained)
- PR size: 30 changed paths, 4,758 additions, 0 deletions; below the
  100-path CodeRabbit cap.
- Static independent review task:
  `019f9b61-4fd6-7253-b24c-8b1bac696a38`
- Static review turn:
  `019f9b61-5aa6-7080-9a25-3807ae31ed50`

## Commands run at handover

```powershell
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
gh pr view 163 --json number,state,url,baseRefName,headRefName,headRefOid,mergedAt,mergeCommit,title
gh pr view 163 --json changedFiles,additions,deletions
git cat-file -p 26881e0a8a6fd8d2b05046cceb88e9a5c5e0e656
git rev-parse '7cd8afe8b47e9d75b6848d0e84e14362c227a4da^{tree}'
git merge-base --is-ancestor 7cd8afe8b47e9d75b6848d0e84e14362c227a4da origin/main
git merge-base --is-ancestor 26881e0a8a6fd8d2b05046cceb88e9a5c5e0e656 origin/main
```

## Contracts and validation

- Author evidence: 84/84 focused tests; 4/4 affected checks; 4/4
  catalogue/identity checks; 102/102 contract gates; 220/220 and 27/27
  immutable checks; scoped diff check.
- Final independent static review verdict: **accept**, no findings. It verified
  byte-bound reservation authority, seven paired substitutions, and no changed
  prior surfaces at the exact candidate/wrapper state above.
- Codacy passed.
- This evidence does **not** substitute for the mandatory CodeRabbit gate or
  broader WP6 acceptance.
- Do not rerun these batteries without a changed candidate or new evidence.

## Results and provenance

- Both the accepted candidate and wrapper are ancestors of current
  `origin/main`.
- The current manager checkout is clean and detached:
  - worktree: `C:\Users\steph\.codex\worktrees\aeb7\TDL`
  - `HEAD`: `ac50847fb49f27d412adc45fc2e0a2e10b80c2d2`
  - `origin/main`: `1c41f3186ff0b154601fd461334186f8059b520e`
- Jira comments already present:
  - KAN-55 `10095`: PR created; mergeability/Codacy pending.
  - KAN-55 `10096`: reported integration complete; now incomplete as a
    governance account because it omits the premature merge.
  - KAN-55 `10097`: corrected status back to In Progress.
  - KAN-53 `10098`: records integration while retaining KAN-55 In Progress;
    also needs later clarification after the recovery decision.

## Decisions

- CodeRabbit review is a mandatory pre-merge gate.
- Stephen triggers and monitors CodeRabbit; in normal operation the PR-open
  event triggers it automatically when budget is available.
- The manager must not trigger, poll, schedule, or automate CodeRabbit unless
  Stephen explicitly asks in the current task.
- The prior static accept cannot waive the CodeRabbit gate.
- Established repository precedent for a premature gated merge is revert and
  re-route through a CodeRabbit-gated PR, but that is not authorization to
  mutate this history.

## Open risks

1. `origin/main` presently contains code that bypassed the required pre-merge
   review gate.
2. Because the original branch commits are already ancestors of `main`,
   recovery is not as simple as reopening PR #163. A revert/reapplication
   topology must be designed against the exact current graph.
3. Reverting or creating recovery PRs changes shared repository state and
   requires Stephen's explicit approval of the exact recovery sequence.
4. Jira comments `10096` and `10098` currently overstate clean integration and
   should be corrected after the recovery decision, without marking KAN-55
   Done.
5. Later WP6 gates remain unsatisfied regardless of this contract's static
   acceptance.

## Suggested skills

- `research-observer` at session start, per repository instructions.
- `tda-large-workflow-supervision` for continued standalone WP6 coordination.
- `github:github` only for exact PR/branch inspection or mutations explicitly
  authorized by Stephen.
- `atlassian-rovo:triage-issue` only when Jira inspection or correction is in
  scope.
- `coderabbit:code-review` is not a replacement for the repository's hosted
  CodeRabbit PR review gate.

## Next actions

1. Read this handover and the predecessor packet; verify the exact current
   Git graph and PR #163 state without changing anything.
2. Present Stephen with the smallest safe recovery topology. The default
   precedent to evaluate is:
   - a clean revert PR for the premature merge;
   - CodeRabbit conclusion on that PR before merge;
   - a separate reapplication PR from the resulting main state;
   - CodeRabbit conclusion on the reapplication PR before merge.
   Account for whether the hosted reviewer can review each PR and preserve the
   accepted candidate bytes wherever the topology permits.
3. Obtain explicit authorization for the exact shared-state mutations.
4. Execute only the approved recovery, using focused graph/diff validation.
5. Correct KAN-55 and KAN-53 comments to record the breach and recovery outcome.
6. Resume the WP6 critical path only after repository governance is restored.

## Rotation evidence

- Handover task started `2026-07-25T23:45:05+01:00`.
- Initial estimate: 10 minutes.
- Exact-state checkpoint completed in under 2 minutes.
- Rotation reason: the outgoing manager incorrectly treated the rule against
  operating CodeRabbit as if CodeRabbit were not a required merge gate. Stephen
  identified this as a context-quality failure and requested a fresh manager.

## Branch and integration state

- No branch is attached to this handover checkout.
- No files have been staged, committed, pushed, or included in a PR by this
  handover action.
- This document is an untracked, non-ignored local coordination artifact in the
  current worktree.
- Do not attach this stale checkout to the PR branch or use it for recovery
  implementation. Create/open a correctly rooted task at the exact intended
  starting commit once the recovery sequence is authorized.

## Do not do

- Do not call this an APM task set or start an APM manager.
- Do not merge any recovery or WP6 PR before CodeRabbit has concluded.
- Do not trigger or poll CodeRabbit unless Stephen explicitly asks.
- Do not rewrite `main`, force-push, delete the retained branch, or revert the
  merge without explicit authorization.
- Do not claim KAN-55 or WP6 complete.
- Do not repeat accepted validation without a concrete trigger.
- Do not treat a Jira comment or Full-draft marker as workflow closure.
- Avoid security-testing vocabulary in delegated review prompts when neutral
  wording such as “schema conformance and data-integrity invariants” expresses
  the task; earlier wording caused a cybersecurity false positive.

## Sensitive information

No credentials, secrets, tokens, or private data are included in this packet.
