# Merge-admission gates: thread finality and platform-evidence ordering

**Date:** 2026-09-08
**Observations closed:** `01M0PWSR73ABY48X8YW7KQX6Q6`, `01M0Q0WXJSCX5WJ69H2G9DG4E3`
**Approval:** Stephen, 2026-09-08 — "gate at the candidate", "invalidate on new
thread", "Linux-before-acceptance for fs/concurrency PRs". Both observations had
been parked as ESCALATED — OWNER-ONLY since 2026-08-26 because the enforcement
surface is the GitHub merge surface rather than a bounded repository candidate.

## What was wrong

**Thread finality (PR #262).** The candidate `af680b81` was admitted on a
clean-thread readback taken at 07:28:14Z. At 07:40:23Z `chatgpt-codex-connector`
published five review threads; the merge landed 89 seconds later. Those five
threads are still `isResolved: false, isOutdated: false` today. The P-049
ruleset required thread resolution, but nothing re-derived thread state at the
merge moment, so the requirement was satisfied by evidence that had expired.

**Platform ordering (PR #263).** The first head was accepted against 148
Windows-reachable controls while 13 decisive POSIX controls were skipped. The
required Ubuntu workflow then failed 14 tests, and an isolated Linux run found
35 failures from a path-derived guard defect. Review acceptance was recorded
before the platform evidence that would have contradicted it existed.

## What was built

| Artifact | Role |
|---|---|
| `tools/check_merge_admission.py` | Two pure evaluators over one evidence snapshot; every absent, malformed, or truncated input raises rather than passes |
| `.github/merge-admission.yml` | Producer logins, the Linux check-run name, and the explicit filesystem/concurrency path list |
| `.github/workflows/merge-admission.yml` | Captures the snapshot and runs both gates on every admission-relevant event |
| `tests/tools/test_merge_admission.py` | Negative controls, including the recorded PR #262 candidate |
| `tests/tools/fixtures/pr262_merge_candidate_snapshot.json` | The real GraphQL evidence for `af680b81`, captured 2026-09-08 |

### thread-finality

Evidence must describe the exact candidate (`headRefOid` is compared to the
candidate SHA, and a head that moved mid-evaluation aborts the run). Every
configured review producer must have submitted a review whose `commit.oid` is
the candidate; a producer short of that blocks rather than passes. Any
unresolved, non-outdated thread blocks.

Evidence invalidation is structural rather than a stored timestamp: the workflow
re-runs on `pull_request_review_thread` (created/resolved/unresolved),
`pull_request_review`, `pull_request` and `merge_group`, replacing the check
conclusion on the head SHA each time. A thread published after an earlier clean
run flips the check back to failure. `evidence_is_stale()` states the same rule
directly and is exercised against the PR #262 window.

### platform-order

Applies only when the candidate touches a configured filesystem or concurrency
path. When it does, `lint-and-test` must be COMPLETED and SUCCESS on the
candidate, and every `APPROVED` review on that candidate must have been
submitted after that job concluded.

## Watched failures

Both rules were mutation-tested on 2026-09-08: neutralising the live-thread
filter and the approval-ordering comparison fails
`test_recorded_pr262_candidate_is_refused_admission`,
`test_cli_blocks_on_the_recorded_candidate`, and
`test_approval_before_linux_evidence_is_refused`. Restoring them returns 22/22.

The strongest negative control is not a probe PR: the committed snapshot is the
actual evidence GitHub held at the moment PR #262 merged, and both gates refuse
it. A probe PR would demonstrate the same rule against synthetic data while
consuming a live merge cycle. Paired positive controls (removing exactly the
five threads; approving after a green Linux run) confirm neither gate is vacuous.

## Owner actions still required

1. **Add `merge-admission` to the P-049 ruleset's required status checks.** Until
   that is done the workflow reports but does not block. This is a repository
   settings change and was not made from this session.
2. **Confirm the sensitive-path list.** `.github/merge-admission.yml` lists the
   store package plus lock/anchor/durability/layout/atomic/concurrency filename
   patterns. It is deliberately narrow; broadening it turns the ordering rule
   into a repo-wide one, which is not what was approved.

## Known limits

- Acceptance is observed as a GitHub `APPROVED` review. Independent reviews
  recorded as `COMMENTED` (the usual shape in this repo) are invisible to the
  ordering gate; the reviewer-side obligation from observation
  `01M0Q0WXJSCX5WJ69H2G9DG4E3` — report `PLATFORM-EVIDENCE-PENDING` rather than
  ACCEPT — remains a skill-level rule in `tda-large-workflow-supervision`.
- Connections are queried at `first: 100`; a larger PR trips the truncation
  guard and blocks rather than admitting on a partial page.
- For `pull_request` events the gate is checked out from the base SHA, so a
  candidate cannot relax the gate that admits it. The ruleset requirement in
  owner action 1 is what makes that non-bypassable.
