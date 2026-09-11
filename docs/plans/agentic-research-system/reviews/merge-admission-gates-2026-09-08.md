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
| `tools/check_merge_admission.py` | Pure evaluators for thread finality, platform ordering, queue disposition and merge-group size; every absent, malformed, truncated or untrusted input raises rather than passes |
| `.github/merge-admission.yml` | Review producers, the trusted platform producer (check run, workflow file, app), the filesystem/concurrency path list, and the merge-group entry limit |
| `.github/workflows/merge-admission.yml` | Captures the snapshot, dequeues on review changes, sizes merge groups, and runs the gates on every admission-relevant event (Windows runner) |
| `tests/tools/test_merge_admission.py` | Negative and positive controls, including the recorded PR #262 candidate |
| `tests/tools/test_ci_platform_policy.py` | Locks the Windows-only CI decision and the bash-shell requirement for Windows runners |
| `tests/tools/fixtures/pr262_merge_candidate_snapshot.json` | The real GitHub evidence for `af680b81` (GraphQL plus the REST file listing), last re-captured 2026-09-11 |

### thread-finality

Evidence must describe the exact candidate (`headRefOid` is compared to the
candidate SHA, and a head that moved mid-evaluation aborts the run). Every
configured review producer must have submitted a review whose `commit.oid` is
the candidate; a producer short of that blocks rather than passes. Any
unresolved, non-outdated thread blocks.

Evidence invalidation is structural rather than a stored timestamp: the workflow
re-runs on `pull_request_review_comment`, `pull_request_review`, `pull_request`
and `merge_group`, replacing the check conclusion on the head SHA each time. A
thread published after an earlier clean run flips the check back to failure.
`evidence_is_stale()` states the same rule directly and is exercised against the
PR #262 window.

GitHub has no `pull_request_review_thread` Actions trigger — actionlint caught
the first draft, which used one and was rejected at workflow validation. A newly
published thread still retriggers, because it arrives as a review comment and
the review carrying it fires `pull_request_review` (Codex's five threads on
PR #262 came with a submitted review at `07:40:23Z`). No event exposes thread
state changes made without a comment, and the two directions differ:

- **Resolving** a thread moves the check from failure to success, so it cannot
  admit silently. Re-run the check once the threads carry a disposition.
- **Reopening** a resolved thread moves it from success to blocked, and *that is
  silent*. An earlier version of this record claimed thread-state changes only
  moved failure to success; Codex review 3988790015 showed the reverse case. The
  merge queue re-checks threads when it builds a queue commit, which covers
  reopens before queueing. `merge-admission-sweep.yml` covers the rest: every 5
  minutes it lists open pull requests, and for any with a live thread it dequeues
  a queued entry and re-runs a currently green admission check, so the success is
  replaced on the same commit. The window is the cron interval plus GitHub's
  scheduling delay, typically 5–10 minutes.

### platform-order

Applies only when the candidate touches a configured filesystem or concurrency
path, where a rename's **source** path counts as touched. The project supports
Windows only (decided 2026-09-11), so the platform evidence is
`windows-store-lock`. When the gate applies:

- `windows-store-lock` must be COMPLETED and SUCCESS on the **pull request
  head**, and each reviewer's latest `APPROVED` review of the candidate must have
  been submitted after it concluded. Reviewers approve the head, so ordering is
  judged there.
- Inside a merge queue, the **merge-group commit's** run must also pass. Its run
  necessarily postdates approval, so no ordering is applied to it.
- The check run is trusted only when its check suite belongs to the
  `github-actions` app and its workflow run's file is `.github/workflows/ci.yml`.
  A same-named run from anywhere else is refused, not ignored.
- A candidate that changes `.github/workflows/ci.yml` is refused outright: a
  `pull_request` run executes the candidate's own copy, so the file-path check
  would pass while the job had been rewritten.

Changed paths come from the REST files listing, which carries
`previous_filename`; GraphQL `files` omits rename sources. The listing's length
must equal GraphQL's `changedFiles`, so a truncated listing fails closed.

`synchronize` starts this gate alongside CI, and no event fires when CI later
completes. So the workflow asks `platform-status` first: `not-applicable` and
`ready` proceed at once; `pending` polls every 30s for up to 40 minutes, which
outlasts `windows-store-lock`'s 30-minute ceiling. Only platform-sensitive
candidates ever wait. An exhausted budget fails closed.

### queue-disposition and merge-group-size

A merge-group run evaluates review state once, when the queue commit is built.
Later review events re-run the gate on the pull request head only, so a thread
opened on a queued pull request would never reach the queue commit's green
check. On `pull_request_review` and `pull_request_review_comment`, a queued pull
request is therefore removed with `dequeuePullRequest`; re-queueing rebuilds and
re-evaluates it. Cost, accepted 2026-09-11: any review event on a queued pull
request removes it.

Admission evaluates the one pull request named in a merge-group ref. On
`merge_group`, the gate compares `base...head` and refuses a queue commit with
more squash commits than `merge_queue.max_entries` (1), re-deriving the P-049
ruleset's one-entry build and merge limit from the commit itself.

A `workflow_dispatch` must run on the pull request's own branch: its check
lands on `github.sha`, so the evidence head is required to equal it.

### Review round 1 (Codex, 2026-09-10)

Six findings on `91539a9`. One (`pull_request_review_comment` trigger) was
already fixed in `e7c1d15`. Four were fixed with negative and positive controls:
waiting on a running Linux lane, merge-group platform evidence, superseded
approvals, and dispatch binding. The sixth — reviews recorded as `COMMENTED`
escaping the ordering rule — was a design question; Stephen decided on
2026-09-10 that an `APPROVED` review is the only acceptance record for
platform-sensitive pull requests (see Known limits).

### Review round 2 (Codex, 2026-09-11)

Six findings on `082b934`, after `main` (#277–#281) was merged into the branch.

- **3988684679** — the gate waited on `lint-and-test`, which #277 had split away.
  Stephen decided the project supports Windows only: the Linux test lanes were
  removed and the gate was retargeted to `windows-store-lock`, keeping the
  ordering rule rather than dropping it.
- **3988684687** — approvals necessarily precede the queue commit's CI, so the
  round-1 fix rejected every queued candidate. Its positive test used an
  impossible event order. Ordering now uses the head run; the queue run must
  separately pass.
- **3988684692** — Stephen chose auto-dequeue over a manual check.
- **3988684695** — rename sources now count as touched paths.
- **3988684699** — the ruleset already enforced one-entry groups; the gate now
  re-derives it.
- **3988684703** — platform evidence is trusted by producer, and a candidate
  editing the producer workflow is refused.

### Review round 3 (Codex, 2026-09-11)

Three more findings on `082b934`, posted while round 2 was being fixed.

- **3988789995** — `research_system/authority.py` performs control-store
  publication: staged writes, `fsync`, and an atomic `os.rename` of the stage onto
  the final root (checked at `authority.py:1784`). It was added to
  `sensitive_paths`.
- **3988790007** — the candidate controls the gate's own workflow YAML. This
  cannot be closed in the repository, so Stephen chose a ruleset-required
  workflow pinned to `main` (owner action 1).
- **3988790015** — reopening a thread is silent; the record's earlier claim
  otherwise was wrong. Stephen chose a 5-minute sweep (`merge-admission-sweep.yml`)
  over relying on the queue-time check alone.

### Review round 4 (Codex, 2026-09-11)

Two findings on `e805a3c`.

- **3990012209** — a re-run leaves every attempt in the rollup. Commit `2146780`
  carries a FAILURE and a later CANCELLED `merge-admission` run side by side.
  Treating duplicate trusted runs as ambiguous would have blocked a sensitive
  candidate permanently after any re-run. The current attempt is now the trusted
  run with the highest check-run `databaseId`, since ids increase with creation.
  The sweep had the mirror defect, re-running an old success behind a newer
  failure, and now judges only the latest attempt.
- **3990012219** — job-level permissions set unlisted scopes to none, and the
  admission job did not list `actions`. The token could therefore be denied
  `checkSuite.workflowRun`, rejecting every genuine run. The job now grants
  `actions: read`, and a null `workflowRun` is reported as a permission problem.
  Whether `GITHUB_TOKEN` really returns the field is first shown by a live run
  from `main`.

### Review round 5 and the ruleset decision (2026-09-11)

The ruleset-required workflow chosen in round 3 proved unavailable on the Free
plan (see owner action 1). Stephen then decided:

- **Protect gate files through code ownership, with admin bypass.**
- **Require Codex as the only review producer.** CodeRabbit reviewed only 1 of
  the 4 PRs merged before this change. The other 3 got "manual review required
  for this OSS repository". CodeRabbit threads still block when they exist.
- **Run the admission and policy controls in a new required Windows job.**
- **Merge this PR before changing the ruleset.**

Codex findings on `0c39378`:

- **3990242343** — the new controls never ran in CI once the `test` lane was
  removed. The new `admission-controls` job now runs them.
- **3990242353** — `research_system/operations/backups.py` publishes with fsync
  and a Windows `os.rename` branch (checked, `backups.py:622-624`). It was added
  to `sensitive_paths`.
- **3990242357** — the sweep refused beyond 50 open PRs, which silently disabled
  it. It now paginates with `--paginate --slurp`, and the page chain must be
  consistent. Before relying on this, it was verified against GitHub: 262 merged
  PRs over 11 pages matched `totalCount`, with nested connections truncated on
  144 of them.

## Watched failures

Every rule is mutation-tested.

- **2026-09-08.** Neutralising the live-thread filter and the approval-ordering
  comparison failed `test_recorded_pr262_candidate_is_refused_admission`,
  `test_cli_blocks_on_the_recorded_candidate`, and the approval-ordering control
  (now `test_approval_before_platform_evidence_is_refused`).
- **2026-09-10.** Inverting the latest-approval comparison failed the
  supersession control (now
  `test_a_reapproval_after_green_platform_supersedes_the_early_one`). Removing
  the platform-commit oid check failed
  `test_a_snapshot_for_the_wrong_platform_commit_is_refused`.
- **2026-09-11.** Each of the seven new rules was neutralised in turn, and every
  mutant was caught:

  | Mutant | Failing controls |
  |---|---|
  | Rename source ignored | 1 |
  | Listing-completeness check skipped | 1 |
  | Producer identity unchecked | 3 |
  | Producer workflow edit allowed | 1 |
  | Queue-commit run not required | 2 |
  | Never dequeue | 2 |
  | Merge-group size unbounded | 1 |

  The tool was restored byte-identical, verified by sha256. The gate suite then
  passed 61/61, and the gate, policy and currency controls together passed
  75/75.
- **2026-09-11, rounds 3–4, clean re-run of all 15 mutants.** An earlier run
  was contaminated by stale bytecode. CPython trusts a cached `.pyc` when the
  source size and whole-second mtime match, so the same-size `>`→`<` mutant,
  restored within one second, kept running. The restored baseline then failed
  exactly that mutant's tests, which exposed it. The same effect could just as
  easily have let a mutant reuse the previous mutant's code and pass for the
  wrong reason. The harness now clears `__pycache__` and disables bytecode
  before every run. Clean results:

  | Mutant | Failing controls |
  |---|---|
  | Rename source ignored | 1 |
  | Listing-completeness check skipped | 1 |
  | Producer identity unchecked | 4 |
  | Producer workflow edit allowed | 1 |
  | Queue-commit run not required | 2 |
  | Never dequeue | 2 |
  | Merge-group size unbounded | 1 |
  | Sweep skips every pull request | 6 |
  | Sweep counts outdated threads | 1 |
  | Sweep never dequeues | 2 |
  | Sweep re-runs failing checks | 3 |
  | Sweep trusts any workflow | 1 |
  | Sweep prints an empty line when idle | 1 |
  | Platform gate picks the oldest attempt | 3 |
  | Sweep picks the oldest attempt | 2 |

  15/15 caught. The tool was restored byte-identical (sha256), and the restored
  baseline passes 84/84.

The strongest negative control is not a probe PR: the committed snapshot is the
actual evidence GitHub held at the moment PR #262 merged, and both gates refuse
it. A probe PR would demonstrate the same rule against synthetic data while
consuming a live merge cycle. Paired positive controls (removing exactly the
five threads; approving after a green Linux run) confirm neither gate is vacuous.

## Owner actions still required

1. **Update the P-049 ruleset after this PR merges** (decided 2026-09-11).
   Three changes are needed:
   - require the `merge-admission` and `admission-controls` status checks, from
     the GitHub Actions app;
   - require review from code owners;
   - add a bypass actor: the repository admin role, `bypass_mode: pull_request`.
     P-049 has **no bypass actors today** (`current_user_can_bypass: never`), so
     without one, code-owner review would block every gate-file PR outright,
     because PRs are opened under the owner's own account.

   Every agent acts through the owner's admin login, so the bypass is kept
   deliberate by `.claude/hooks/admin-bypass-guard.sh` (Stephen, 2026-09-11). It
   refuses `gh pr merge --admin`, direct merges that skip the queue, and writes to
   rulesets or branch protection from Claude Code sessions. The owner runs those
   in their own terminal. It does not cover Codex sessions, which do not read
   `.claude/settings.json`.

   **Why not a required workflow.** On a same-repository pull request, GitHub runs
   the pull request's own copy of the workflow file, so a candidate could replace
   the gate's steps with a no-op that still reports green (Codex review
   3988790007). The first plan was an organization ruleset requiring the
   workflow from `main`, but GitHub offers ruleset workflows "at the organization
   or enterprise level" only, and organization rulesets only "for customers on
   GitHub Team or GitHub Enterprise plans". ZK-Theory is on Free. Push rulesets
   that restrict file paths are limited to private and internal repositories, and
   TDL is public.

   **What replaces it.** The gate files are owned in `.github/CODEOWNERS`, so
   editing them needs code-owner review. Because PRs here are opened under the
   owner's own account, that means a deliberate admin bypass, which GitHub
   records. The gap that remains is recorded under Known limits.

   **Sequencing.** The change is applied after merge because the gate cannot pass
   on this PR (it is checked out from `main`, which lacks the tool until merge).
   Until it is applied, the workflow reports but does not block.
2. **Confirm the sensitive-path list.** `.github/merge-admission.yml` lists the
   store package plus lock/anchor/durability/layout/atomic/concurrency filename
   patterns. It is deliberately narrow; broadening it turns the ordering rule
   into a repo-wide one, which is not what was approved.

## Known limits

- **Decided 2026-09-10: `APPROVED` is the acceptance record.** For a pull request
  touching platform-sensitive paths, review acceptance means a GitHub `APPROVED`
  review; a verdict posted in a `COMMENTED` review does not count. Stephen chose
  this over parsing verdict tokens out of comment bodies, which would rest on
  reviewers typing an exact string, and over treating every human review as
  acceptance, which would block on routine questions. It is locked in
  `CONVENTIONS.md`. The gate enforces ordering for the record it can see; the
  convention is what puts acceptance into that record.
- **No CI coverage on POSIX.** The POSIX-only branches in
  `research_system/store/` (`anchor.py`, `identity.py`, `writer.py`) are no
  longer executed by any CI lane, and no lane runs the unfiltered pytest suite.
  Both follow directly from the 2026-09-11 Windows-only decision and are recorded
  in `CONVENTIONS.md`.
- **Dequeue is not yet verified live.** The call's input shape was confirmed by
  schema introspection, and the job grants `contents: write` and
  `pull-requests: write`. Whether `GITHUB_TOKEN` is allowed to dequeue will
  first be shown by a real queued pull request. If it isn't, the step fails
  loudly rather than silently keeping the entry.
- Connections are queried at `first: 100`; a larger PR trips the truncation
  guard and blocks rather than admitting on a partial page.
- For `pull_request` events the gate is checked out from the base SHA, so a
  candidate cannot relax the gate that admits it. The ruleset requirement in
  owner action 1 is what makes that non-bypassable.
