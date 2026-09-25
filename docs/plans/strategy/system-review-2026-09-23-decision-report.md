# Weekly Research-System Review — Resolution Packet

**Review date:** 2026-09-23 (scheduled `weekly-system-review`, autonomous run)

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md` (3,414 lines)

**Scope:** all 66 OPEN observations at review time. 64 carried forward from the
2026-09-15 packet (52 minus one now-ACTIONED item, `2026-09-11-repowise-post-commit-dirties-tracked-files`,
plus 13 logged 2026-09-15-later through 2026-09-18), one SKILL-lane item self-applied
during this review (no longer OPEN, see Skills Pass), and two logged during this
review's own gate-liveness spot check and process audit. See the Completeness Ledger.

**Decision owner:** Stephen

**Operating rule (unchanged since 2026-08-09):** approval authorizes a bounded
verify-then-fix campaign on a reviewed branch. It does not authorize direct changes to
`main`, silent gate weakening, or acceptance without the named controls.

**Autonomous-run constraint:** this run self-applied exactly one item — the sole
SKILL-lane observation (`2026-09-17-worktree-sweep-needs-squash-aware-and-attribute-aware-checks`)
— and made one mechanically-verified, diff-first RECORD correction (a stale
self-contradiction inside `2026-09-08-claude-hooks-lack-lf-attribute`, see Skills Pass
note and the log entry itself). Every other OPEN observation is lane GATE, INVARIANT,
PROCESS, or RECORD requiring new tooling or an owner scope decision, so this packet is
report-only for everything else, exactly as the autonomous-run rule intends.

**Continuity with 2026-09-15:** the prior packet (commit `a471ee95`, branch
`docs/system-review-2026-09-15`) was never opened as a pull request and carries no
decision record in the eight days since — see Campaign H, item 4, and the new
observation `2026-09-23-review-packet-never-reached-the-owner`. This review re-verified
every one of its 52 mapped observations against current `log.md` by direct read (not by
trusting the prior packet's table) and found exactly one status change: Campaign C's
Repowise finding is now ACTIONED (PRs #293/#294). Everything else the 2026-09-15 packet
named is still open in the same shape. **This packet is opened as a PR** (see final
section) specifically to close the gap that new observation describes.

## How to use this packet

Choose one box per campaign. An approved campaign first re-resolves every mapped
observation against current HEAD and the owning repository:

1. already compliant or superseded → record evidence, mark ACTIONED/DECLINED, archive;
2. still valid and in scope → implement the named mechanism with its negative control;
3. contradicted or owned elsewhere → record the exact owner/blocker and keep only that
   bounded remainder open.

## Decision summary

| Campaign | OPEN items | Recommended resolution | Decision |
|---|---:|---|---|
| A. Branch/commit-state trust under concurrency | 5 | One pre-commit branch-admission gate + a PreToolUse branch-drift hook | `[x]` approved |
| B. Working-tree CRLF byte integrity | 2 (+1 self-corrected) | `.gitattributes` half is DONE (verified); add a `--worktree` byte-check mode | `[x]` approved |
| C. CI/workflow & hook-path liveness | 7 | One CI-liveness + hooksPath-resolution campaign | `[x]` approved |
| D. Hook/gate negative-control debt | 6 | Wire selftests into pytest/CI; hardened mutation-check tool; fix/retire the dead `.codex` installer | `[x]` approved |
| E. Gate 6 SPEC route/admission binding gaps | 16 | Continue under the existing 06s Phase 4/5 D5-scope process (tracking only) | `[x]` approved — lessons folded into skills |
| F. Brief/handoff/dispatch hygiene | 6 | Extend `manager_dispatch_check`/dispatch-readiness with five named assertions | `[x]` approved |
| G. External-review-producer dependency | 1 | Distinguish quota/untriggered states in merge admission | `[x]` approved, bundled with I's clean-signal fix |
| H. Observation-log record-keeping (meta) | 4 | Mechanical duplicate-resolution lint + cross-repo review-scope decision + PR-per-review convention | `[x]` approved — one review, all repos |
| I. Review/certification-ladder process discipline (new) | 7 | Fold five named lessons into `research-assurance-triage`/`contract-first-tdd`/dispatch checklists (tracking only) | `[x]` approved — +1 on head accepted |
| — Non-TDL residual (MathUni/Counting Lives/codex_workflow) | 11 | Report-only; folds into Campaign H's scope decision | `[x]` into the all-repo review |
| — TDL residual carried forward | 1 | Continue tracking `2026-08-22-retired-procedure-kept-live-imperatives`'s open enumerable-contract limb | `[x]` keep tracking |

### Owner decisions (Stephen, 2026-09-25)

1. **Delivery:** one PR per campaign, each on its own branch and worktree off
   `main`. This PR stays the decision record and carries the Campaign
   B-adjacent `sync_agent_skills.py` LF fix plus the reviewed skill edit.
2. **Codex clean signal (G + I):** accept a Codex +1 reaction as terminal only
   when it was created after the candidate head's push and no Codex review names
   another commit. A reaction carries no commit oid, so this binding is weaker
   than a review oid, and the implementing PR must say so. Negative control: a
   stale +1 from an earlier head still blocks. Quota and untriggered heads get
   distinct named states.
3. **Cross-repo scope (H):** one `weekly-system-review` covering all repos. It
   reads MathUni, Counting Lives and codex_workflow read-only and dispositions
   their OPEN items in the same packet. SKILL and RECORD self-application stays
   limited to trees the run can reach.

Total: 5+2+7+6+16+6+1+4+7 = 54 (campaigns A–I, TDL) + 1 (TDL residual) + 11 (non-TDL) = **66**.

---

## A — Branch/commit-state trust under concurrency

*(Unchanged from 2026-09-15; re-verified all five IDs still OPEN, no new items.)*

**Problem.** Five observations converge on one shape: a session's belief about its own
branch, its own commit's success, or its own test run's outcome is a stale snapshot,
not a live fact, and nothing re-checks it before the next irreversible action.

- `2026-09-08-concurrent-session-branch-switch` — a second session sharing the same
  working directory moved HEAD to `main`; the next commit landed there despite an
  earlier branch check.
- `2026-09-08-blocked-commit-reported-exit-zero` — a pre-commit-blocked commit was
  reported "completed (exit code 0)."
- `2026-09-10-agent-command-slips-this-session` — three execution slips (a no-op edit,
  an empty heredoc that hung a commit chain, a process-kill filter that hit its own
  shell), each caught only by checking state after the fact.
- `2026-09-13-own-timeout-read-as-failure` — a shell `timeout` wrapper killed a
  legitimately slow background pytest run; exit 143 read as a test failure.
- `2026-09-14-commit-during-test-run-stashed-the-tree-under-tests` — a docs-only
  commit's pre-commit stash reverted the working tree to base bytes while eight
  background test groups were still reading from it; ~40 minutes of compute discarded.

**Recommended mechanism:** a `.githooks/pre-commit` branch-admission check refusing a
commit on `main` unless an explicit override env var is set; a `PreToolUse` hook on
Write/Edit/Bash-commit comparing the current branch against the branch recorded at
session start; skill-guidance lines confirming commits by `HEAD` before/after (never
exit status), never wrapping a background bound-test run in a shell `timeout`, and
never committing in a worktree while tests are reading from it.

**Controls:** commit attempted on `main` is refused; commit on a feature branch
succeeds; a branch switched underneath a running session is caught before the next
write; a killed background run is reported as killed, not failed.

**Note:** `2026-09-09-the-branch-moved-under-a-running-session` is the same shape,
logged from a MathUni session (non-TDL section). Worth deciding once, not twice.

**Decision:** `[ ]`

---

## B — Working-tree CRLF byte integrity

**Problem.** `git status` and `.gitattributes` normalize at the *index*, not the
working tree, so a CRLF rewrite of a tracked hook script can be present on disk,
executable, and invisible to every git-native check.

- `2026-09-08-shell-rewrite-crlf-on-tracked-hook` — a Git Bash redirect reintroduced
  CRLF into `.githooks/post-commit`; `git status --porcelain` read clean, and
  `git checkout HEAD --` was a no-op against it.
- `2026-09-08-name-only-ignores-content-flags` — `git diff --name-only --ignore-cr-at-eol`
  silently discards the content flag, so a CRLF-drift classification over 2,072 files
  concluded every file had genuine edits.

**Already done, verified live today (not a recommendation any more):** the
2026-09-15 packet's top recommendation for this campaign — pin `.claude/hooks/**`,
`.codex/hooks/**`, `.githooks/**` and `.claude/settings.json` to `text eol=lf` — is
already in `.gitattributes` (lines 63–71) via PR #274, merged 2026-09-08. This review
also found and **corrected** a stale self-contradiction inside
`2026-09-08-claude-hooks-lack-lf-attribute`'s own body: a sentence saying the
`.gitattributes` gap "remains OPEN and unfixed" had been written between PR #273 and
PR #274 and was never updated after #274 landed nine hours later. Both of that
observation's findings are genuinely closed; see the corrected log entry.

**Still open:** a `--worktree` mode for `tools/check_crlf_byte_surface.py` that reads
working-tree bytes directly (not index-normalized) — verified today, the tool has no
such flag yet (`argparse` setup at `tools/check_crlf_byte_surface.py:160` has no
`--worktree` option). Skill-guidance line: after any shell rewrite of a tracked hook
script, re-read its bytes; repair with `rm` + `git checkout`, never `git checkout`
alone.

**Controls:** `git check-attr eol -- .claude/hooks/<script>.sh` resolves `lf` (already
verified passing); the `--worktree` mode, once built, catches a CRLF-rewritten hook
that `git status` calls clean.

**Decision:** `[ ]`

---

## C — CI/workflow & hook-path liveness

**Problem.** A gate's presence in the tree, or its exit code, is not evidence it ran,
ran against the right scope, or against the right hook files.

- `2026-08-18-broad-repo-ci-remains-disabled` — `ci.yml` is still `disabled_manually`;
  only a narrow ARS-scoped file list gets CI-level regression detection.
- `2026-09-08-staged-only-lint-hides-untouched-file-debt` — the pre-commit ruff gate
  lints staged files only; 71 ruff errors sat on `main` while every commit reported
  "hooks passed."
- `2026-09-08-workflow-disabled-state-is-invisible-to-the-repo` — a `windows-store-lock`
  CI lane added 2026-08-02 has never once executed; `disabled_manually` lives only in
  the GitHub API.
- `2026-09-08-advisory-lane-is-a-scoped-green-tick` — the re-enabled CI's pytest lane is
  `continue-on-error`; a green `CI` check now attests lint only.
- `2026-09-08-disabled-ci-let-a-checkout-breaking-defect-live-three-months` — the first
  live CI run found a real three-month-old defect (a bare gitlink with no
  `.gitmodules`).
- `2026-09-08-git-add-dash-A-swept-in-generated-metadata` — Repowise's post-commit
  updater repeatedly rewrote tracked `.claude/CLAUDE.md`/`.repowise-workspace.yaml`
  (the sibling observation `2026-09-11-repowise-post-commit-dirties-tracked-files` is
  now **ACTIONED** — PR #293/#294, merged 2026-09-17 — see below).
- **New this week:** `2026-09-17-worktree-scoped-hookspath-runs-main-checkout-hooks` —
  each of the four `.claude/worktrees/*` desktop-session worktrees sets
  `core.hooksPath` in `config.worktree` to an *absolute* path pointing at the main
  checkout's `.githooks`, overriding CLAUDE.md's documented relative path. A commit
  made from one of these worktrees runs the main checkout's hook bytes, not the
  branch's. This is why the Repowise fix above didn't fully land where expected: PR
  #294, committed from worktree `magical-bardeen-05956b` after #293 had merged, still
  ran a full Repowise update and rewrote the tracked metadata files, because the
  worktree's hooks resolved to a stale main-checkout snapshot rather than the current
  branch. `install-git-hooks.py` confirms a hook is *live*, not that it is *this
  branch's* hook — the two claims were conflated.

**Recommended mechanism:**
- `manager_dispatch_check` sibling to the existing hook-liveness assertion: query
  `gh api repos/:owner/:repo/actions/workflows` and fail on any tracked workflow whose
  `state` is not `active`.
- A periodic or pre-dispatch whole-repo `ruff check .` assertion, visible even when
  `ci.yml` is down.
- A watchdog on the `continue-on-error` pytest lane (N green → restore the gate; N
  red-with-no-progress → flag decay).
- A pre-commit assertion that the index contains no `mode-160000` entry without a
  matching `.gitmodules` stanza.
- **New, high priority:** extend `install-git-hooks.py` (and `manager_dispatch_check`'s
  `hook-gate`) to resolve the *effective* `core.hooksPath` with `--show-scope` and print
  which directory will actually run; warn or fail when a linked/session worktree
  resolves hooks outside its own toplevel. Negative control: a fixture worktree with an
  absolute `config.worktree` override must trip the check. Separately, find out what
  writes this override when a desktop session creates its worktree.

**Controls:** workflow-liveness check fails when a tracked workflow's live state isn't
`active`; whole-repo ruff assertion fails on `main`'s current 71 errors until fixed;
gitlink check fails on a `mode-160000` entry with no `.gitmodules`; the hooksPath
check fails on the exact `magical-bardeen-05956b`-shaped fixture.

**Decision:** `[ ]`

---

## D — Hook/gate negative-control debt

**Problem.** A negative control that exists but is invoked by nothing, a test harness
whose own execution model can silently corrupt its evidence, or an installer that was
never checked against the exact incident the project already had — none of these are a
live control.

- `2026-09-15-notation-guard-selftest-never-wired` — `.claude/hooks/notation-guard.sh
  --selftest` (7 cases) is never invoked by pytest or CI; 864 live fires since
  2026-08-06 with zero denies, consistent with either a clean corpus or a silently
  regressed deny path.
- `2026-09-11-mutation-harness-stale-bytecode` — a same-size mutant written and
  restored within one second left CPython executing stale cached `.pyc` bytecode.
- `2026-09-10-captured-pipes-deadlock-on-backgrounded-children` —
  `subprocess.run(capture_output=True)` deadlocks on Windows when the tested hook
  backgrounds a grandchild that inherits the pipe handles.
- `2026-09-13-basetemp-longpath` — a deep `--basetemp` under parallel pytest breaks the
  bound Gate 6 fixture past Windows' 260-char path limit, and the fixture swallows
  git's stderr so the real cause reads as an anonymous failure.
- `2026-09-17-hook-test-outside-ci-rotted-after-a-gate-was-added` — a pre-commit hook
  test pinning the exact list of main-checkout Python invocations a linked-worktree
  commit makes went stale when PR #280 added Gate 1b and never updated the list;
  neither `test_pre_commit_hook.py` nor `test_post_commit_repowise_hook.py` is in any
  CI selection, so nothing noticed until a manual neighbouring-suite run. Half-fixed
  (PR #294 updates the list; the CI-wiring half awaits Stephen's decision on which
  Windows job should carry both suites).
- **New this week, found during this review's gate-liveness spot check:**
  `2026-09-23-codex-installer-recreates-the-dead-git-hooks-bug` —
  `.codex/hooks/install-git-hooks.py` still copies `git-commit-msg.sh` straight into
  `.git/hooks/commit-msg`, the exact directory `core.hooksPath=.githooks` makes git
  ignore — the identical failure shape as the 47-day-dead contract-validator incident
  that `.claude/hooks/install-git-hooks.py`'s own docstring records and was rewritten
  to prevent. Nobody re-audited the `.codex/` sibling when the `.claude/` side was
  fixed. It also installs a materially weaker validator (no BOM check, no
  PXX-placeholder check) than the live `.githooks/commit-msg`. No current caller exists
  in the tree, but the file is the Codex environment's apparent setup entrypoint and
  the observation log records many Codex sessions. Secondary finding from the same
  check: `dispatch-readiness-guard.sh` is live-wired (1,567 fires in
  `hook-receipts.log`, including a historical manual `decision=deny`) but has zero
  automated test coverage and fails open on error, per its own header comment.

**Recommended mechanism:**
- Add `tests/tools/test_notation_guard_hook.py` in the shape of
  `test_admin_bypass_guard_hook.py`, or wire `--selftest` into CI.
- Promote per-session mutation scripts to a committed `tools/mutation_check.py`:
  disable bytecode caching every run, require each mutant anchor exactly once,
  re-run and hash-verify the restored baseline.
- Hook-testing guidance: capture backgrounded hook output to files, not pipes, under a
  hard timeout; keep `--basetemp` short and have `_bound_fixture` capture git's stderr.
- Delete or fix `.codex/hooks/install-git-hooks.py` and `.codex/hooks/git-commit-msg.sh`
  (delegate to the fixed `.claude/` verifier, or delete both in favour of
  `.githooks/commit-msg`); add a repo-wide lint failing on any tracked file that writes
  to a literal `.git/hooks` path, so a third copy of this bug can't reappear unnoticed.
- Add `tests/tools/test_dispatch_readiness_guard_hook.py` (real subprocess invocation,
  envelope with/without the Dispatch Readiness block, fail-open-on-malformed-JSON
  assertion).

**Controls:** `test_notation_guard_hook.py` red on a W₁ mention, green on
outside-papers/exclusion cases; `mutation_check.py`'s baseline-after-restore check
fails loudly on a reproduced stale-bytecode scenario; a hook test with a backgrounded
grandchild completes under timeout; the bound fixture's error names the 260-char limit;
a planted `.git/hooks`-writing installer trips the new repo-wide lint;
`test_dispatch_readiness_guard_hook.py` denies a Task Prompt bus write missing the
Dispatch Readiness block and allows one that has it.

**Decision:** `[ ]`

---

## E — Gate 6 SPEC route/admission binding gaps (tracking only)

**Problem.** Sixteen INVARIANT/GATE observations from 2026-09-08 through 2026-09-17,
all produced during active 06s Gate 6 Phase 2–4a′ construction, share one shape: an
admission or evaluator boundary checks less than its role name or contract claims, so
a route-level check "protects" something admission would actually let through
unchecked.

`2026-09-08-cli-token-assertion-vacuous`,
`2026-09-11-deduplication-dropped-a-behavioural-default` *(ACTIONED for its own fix via
`ca76d1a`; the process lesson remains open)*, `2026-09-12-negative-control-refused-upstream`,
`2026-09-13-evaluator-trusts-recorded-evidence`, `2026-09-13-refusal-after-durable-mutation`,
`2026-09-14-producer-reviewer-rule-binds-a-caller-chosen-field`,
`2026-09-14-historical-ledger-replay-never-checked-against-current-code`,
`2026-09-14-focused-packet-omitted-the-currency-workflow-contracts`,
`2026-09-14-scored-assay-park-has-no-revisit-requirements`,
`2026-09-14-w11-role-names-invisible-to-admission`,
`2026-09-15-route-check-outside-admission-lock`,
`2026-09-15-fixture-authority-content-accepted-as-the-real-bar`, and four new this week:
`2026-09-15-removed-guard-made-a-dead-branch-live` (removing an input guard turned a
harmless dead branch live; half-fixed by PR #292, the route-generic contract test is
still unwritten), `2026-09-16-borrowed-provenance-derivation-carried-its-unasserted-claims`
(copying a merged derivation copied its unasserted claims too; half-fixed by PR #292 for
one of two routes), `2026-09-16-hash-bound-rule-reference-is-not-rule-evaluation` (the
Assay bar binds a rule by hash but nothing evaluates it — a topology pass with
zero-value integer axes is admitted as mechanical PROMOTE), and
`2026-09-17-cross-route-evidence-restated-a-subset-of-the-owning-routes-check` (a route
consuming another route's evidence re-implemented a weaker subset of that route's own
completion check instead of calling it — fixed in #297 by extracting a shared
evaluator).

**Why this campaign stays tracking-only:** this cluster is not stale backlog — it is
the live output of the 06s Phase 2–4a′ process, already flowing through Stephen's D5
scope-decision mechanism inside the 06s plan (several entries explicitly say "needs
Stephen's scoped exception under D5," and four of sixteen already show partial fixes
landed mid-week via the normal PR ladder). Routing it through this packet as a fresh
dispatch would duplicate a review ladder already running.

**Generalizable process lessons to fold into skill guidance (bundle with Campaign D or
F's edits, not dispatched separately):**
- `research-assurance-triage`/`contract-first-tdd` should require, for every negative
  control: name the exact layer expected to refuse, the machine-checkable signal that
  identifies it, and what was held constant so nothing upstream could refuse first
  (`2026-09-12-negative-control-refused-upstream`).
- The same skills should require a field-by-field correspondence table between a
  generator's construction rules and an evaluator's binding checks, one negative
  control per row (`2026-09-13-evaluator-trusts-recorded-evidence`), and a
  per-multi-effect-action list of which refusal must precede which first irreversible
  effect (`2026-09-13-refusal-after-durable-mutation`).
- **New:** when a change removes an input guard, list every branch whose safety
  depended on it and add a negative test for each before merging
  (`2026-09-15-removed-guard-made-a-dead-branch-live`).
- **New:** when a route reuses another route's provenance derivation or evidence,
  write a test comparing each borrowed field against the record it names, or call the
  owning route's own completion evaluator directly rather than restating a subset of it
  (`2026-09-16-borrowed-provenance-derivation-carried-its-unasserted-claims`,
  `2026-09-17-cross-route-evidence-restated-a-subset-of-the-owning-routes-check`).
- **New:** a hash-bound reference to a rule is provenance, not enforcement — when a
  record names an algorithm by hash, find and exercise the code that runs it before
  trusting the binding (`2026-09-16-hash-bound-rule-reference-is-not-rule-evaluation`).

**Recommended disposition:** no new mechanism from this packet. Confirm the 06s plan's
own D5 process continues absorbing these, and fold the five lessons above into the next
`research-assurance-triage`/`contract-first-tdd` revision.

**Decision:** `[ ]` (acknowledge tracking-only status; no build to approve here)

---

## F — Brief/handoff/dispatch hygiene

*(Unchanged from 2026-09-15; re-verified all six IDs still OPEN, no new items.)*

**Problem.** Six observations share a "the brief said X, the enforcement mechanism
actually does Y, and the gap surfaced only after dispatch" shape, plus one
formatter-collateral review-hygiene finding in the same "trust but verify the
artifact" family.

- `2026-09-12-brief-role-vocabulary-vs-inherited-authority` — a brief's role words
  ("authorized producer") were never mapped to the actual enforcing code before
  dispatch.
- `2026-09-14-brief-assumed-historical-records-fit-the-new-route` — a brief required
  binding historical evidence whose field sources are unrecorded and unverifiable.
- `2026-09-14-phase-brief-inherits-an-unscoped-action-list` — a phase brief inherited a
  30-action list from a superseded plan with no record of which subset current
  decisions still require.
- `2026-09-14-handoff-cited-at-a-path-only-an-unmerged-pr-contains` — a dispatch cited
  a handoff path that exists only on an open PR branch.
- `2026-09-14-review-fix-overwrote-a-concurrent-sessions-jira-record` — a
  review-resolution pass replaced a Jira description without re-reading its current
  state, overwriting another session's already-dispatched update.
- `2026-09-08-formatter-collateral-needs-a-semantics-proof` — a one-line edit
  triggered a 20:1 noise-ratio reformat; "formatters are semantics-preserving" was
  assumed rather than checked (false for one of 15 files: docstring whitespace changed
  the AST).

**Recommended mechanism:** a `manager_dispatch_check`/dispatch-readiness question
asking whether the brief cites the enforcement locus for every role word and the
concrete field sources for every historical record it requires; require any
not-yet-merged handoff path to name its branch/PR; a Jira/record-edit skill-guidance
line to re-read `updated` timestamps before whole-field replacement; a reusable
AST-equivalence helper for formatter/codemod collateral.

**Controls:** a dispatch-readiness check flags a brief using unmapped role vocabulary;
a handoff citation missing its branch/PR is flagged before dispatch; a Jira edit warns
when `updated` is newer than the session's last read; the AST-equivalence helper
distinguishes the 14 benign files from the 1 real one in the motivating case.

**Decision:** `[ ]`

---

## G — External-review-producer dependency

*(Unchanged from 2026-09-15.)*

`2026-09-11-required-review-producer-is-quota-limited` — merge admission's
thread-finality gate cannot distinguish "Codex is still reviewing" from "Codex hit its
usage quota and will never review this head automatically." Related but distinct new
finding this week, filed under Campaign I: `2026-09-17-merge-admission-cannot-see-a-clean-codex-review`
— even when Codex *does* respond with a clean signal (a +1 reaction, not a review
object), thread finality never recognizes it as terminal, and PR #292 was merged over
that exact red gate as a precedent.

**Recommended mechanism:** give `tools/check_merge_admission.py` thread-finality a
distinct, named state for a quota/usage-limit response versus an untriggered head.
Consider folding in Campaign I's clean-signal fix (below) as the same piece of work,
since both touch `evaluate_thread_finality`.

**Controls:** a synthetic quota-response fixture resolves to a named "quota" state;
an untriggered head resolves to a distinct "untriggered" state.

**Decision:** `[ ]`

---

## H — Observation-log record-keeping (meta)

**Problem.** Four observations about the review process itself.

- `2026-09-08-reconciliation-stamped-a-borrowed-resolution` — the 2026-09-08 Phase 0
  reconciliation pass copy-pasted at least six of twelve resolution stamps onto the
  wrong, unrelated observations.
- `2026-09-01-completeness-ledger-missed-six-live-items` — the 2026-08-25 backlog
  handoff's stated "every item is accounted for" claim was itself wrong, by six items.
- `2026-09-08-single-repo-review-scope-orphans-other-repos-observations` — the only
  scheduled review is TDL-scoped, but the shared log carries live MathUni, Counting
  Lives, and codex_workflow observations with no autonomous review path of their own.
- **New this week:** `2026-09-23-review-packet-never-reached-the-owner` — the
  2026-09-15 packet (commit `a471ee95`, 52 items, 8 campaigns) was committed to branch
  `docs/system-review-2026-09-15` and never opened as a pull request. `gh pr list`
  finds none, past or present. No decision commit references any of its campaign
  letters in the eight days since. `last-review-date.txt` was updated regardless, so
  the review's own bookkeeping cannot distinguish "delivered and awaiting decision"
  from "written and never seen." This review found the gap only by searching git log
  for the commit message, not through any completeness check the process already had.

**Recommended mechanism:**
- A cheap lint over `log.md` flagging an identical `**Status:**`/resolution sentence
  appearing on two different observation IDs.
- A computed, not assembled, completeness check for any future backlog-triage handoff:
  derive the covered-ID set from the handoff's own tables, diff against a fresh
  independent scan of `log.md`, require the diff to be empty before publishing.
- **New:** every System Review that produces a report-only packet opens a pull request
  for it and records the PR URL in the run summary — a bare commit on an unmerged
  branch is not a delivered deliverable. Before writing a new packet, search for the
  prior one (`gh pr list --search "system-review in:title"` plus a git-log fallback)
  and treat "packet exists, no PR, no decision record since" as its own finding.
- Owner decision needed on cross-repo scope: either schedule an equivalent
  `weekly-system-review`-style task rooted in each of MathUni and Counting Lives, or
  make one review session capable of processing all repos' OPEN items in one pass.

**Controls:** the duplication lint fires on a planted pair of identical resolution
stamps and stays silent on two independently-written ones; the computed completeness
check fails when a handoff omits an in-window, in-scope observation; **this packet
itself is the positive control for the new PR-per-review rule** — see the final
section.

**Decision:** `[ ]`

---

## I — Review/certification-ladder process discipline (new campaign)

**Problem.** Seven PROCESS/GATE observations from 2026-09-15 through 2026-09-18, all
from the same 06s Phase 4a′/4b PR review ladder, share a distinct shape from Campaign
E: not "admission checks less than it claims" but "the process *around* review,
certification, and merge admission has a blind spot that let a real defect or cost
through before anyone decided it was acceptable."

- `2026-09-15-spec-authority-column-divergence-filed-as-known-limit` — an accepted
  spec's actor assignment diverged in construction and was filed as a PR "known limit"
  rather than surfaced to Stephen as a decision; Codex caught it, costing a code change
  and full re-certification that one design-pass question would have avoided.
- `2026-09-16-automated-review-rounds-plateau-in-count-not-kind` — three review rounds
  each returned exactly 5 findings, 4 of them P1, from a shrinking set of finding
  families — convergence in an automated reviewer is measured in kind and
  reachability, not count. **Already partly self-corrected**: a written stopping rule
  adopted mid-week turned round 4 (2 findings, neither meeting the rule) into
  dispositions only, with no round 5.
- `2026-09-16-red-run-exit-code-shared-with-missing-pytest` — a fresh worktree venv
  with no pytest installed made every test group exit 1 within a second; that looked
  like the *expected* red run until the impossible one-second timings gave it away.
- `2026-09-17-closed-intent-enum-sized-to-one-subphase` — a closed action-intent
  record's enum was sized to exactly one sub-phase's actions, forcing a
  merged-schema-version decision in every later sub-phase that extends it.
- `2026-09-17-bounded-action-table-expectation-duplicated` — one "single explicit
  bounded expectation" existed as two full literal copies in unrelated phase test
  files; both went stale silently until the most expensive (≈2-hour) regression
  packet caught it.
- `2026-09-17-merge-admission-cannot-see-a-clean-codex-review` — Codex's "no issues"
  signal is a +1 reaction, not a review object, so thread finality never recognizes a
  clean PR as terminal; PR #292 was merged over exactly this red gate as precedent,
  training the operator to bypass it.
- `2026-09-18-design-probe-used-a-different-entry-point-than-the-public-path` — a
  design-pass admission probe submitted through the bound coordinator directly
  (fixed test clock), while the public route builds its own coordinator with the real
  clock; the probe's finding didn't transfer, costing a 15-minute run and a fix.

**Why a new campaign rather than folding into E or F:** these are not admission-boundary
gaps (E) or brief/handoff citation gaps (F) — they are about the review/certify/merge
loop's own instruments (exit codes, review-round stopping conditions, closed-schema
sizing, reviewer-signal modeling, probe entry points) silently reading as something
other than what they measured. Same underlying lesson as Cross-Cutting Principle 11
("verify the instrument measures the property") applied to process instruments instead
of test oracles.

**Recommended disposition:** tracking-only, same reasoning as Campaign E — this is live
06s Phase 4 output, several items already show partial self-correction mid-week (the
review-round stopping rule, in particular, is worth promoting to a written convention
regardless of 06s's own fate). Fold these lessons into
`research-assurance-triage`/`contract-first-tdd`/dispatch-readiness on the same pass as
Campaign E's:
- A written review-stopping rule (06s §5.0 or CONVENTIONS): once a round opens no new
  finding family, a later finding gets code in the same PR only if it is a defect in
  code the previous round added, or a false durable claim reachable on the planned
  owner path; everything else becomes a known limit or follow-up, paired with a
  per-round ledger.
- A runner rule: confirm each test group actually ran (junitxml `tests >= 1`, or a
  matching final summary line) before trusting an exit code; a red run is evidence
  only when the expected assertion/refusal text appears in the failure.
- A design-pass checklist line: diff every implemented actor/role binding against the
  spec's authority column and surface divergence as a decision before construction,
  not as a PR "known limit."
- A closed-record checklist line: when a design pass creates a closed enum, state the
  full list it will need to cover across all planned sub-phases up front.
- A merge-admission fix (shared with Campaign G): model a producer's non-review
  terminal signal (a stale-head-gated reaction) as a distinct accepted state, not
  silent BLOCKED-forever.

**Decision:** `[ ]` (acknowledge tracking-only status; approve promoting the
review-stopping rule to a written convention if desired — it is the one item here with
a demonstrated payoff, roughly 3 hours of packet-and-certify cost avoided on its first
use)

---

## Non-TDL residual (report-only — 11 items)

*(Unchanged from 2026-09-15 — no working-tree access to MathUni, Counting Lives, or
codex_workflow from this TDL-rooted session. Re-verified all 11 IDs still OPEN in
`log.md`.)*

**MathUni (4):** `2026-08-11-handover-prescribed-an-unexecuted-tool-path` ·
`2026-09-09-1980-page-pointers-name-no-result` ·
`2026-09-10-copied-pattern-dropped-its-hardest-won-rule` ·
`2026-09-09-the-branch-moved-under-a-running-session`.

**Counting Lives (4):** `01KZM0EKJS03PPDST105X7C29H` · `01KZM8H06Q2B64N30R4HM3RC1N`
*(reopened 2026-09-08 — see note below)* · `01KZM9RKTTKKTBAMEPZAT10VN4` *(reopened
2026-09-08, same note)* · `01M1C0H0KJEP3R27W3B9FWP4W6`.

**codex_workflow (3):** `01M044JXYSPP0VXH15TEZVCNA3` · `01M0641MDF9GV509T49SWED57V` ·
`01M06KPH7CQRRPFGGXW67HT0Y4`.

**Note on the two reopened Counting Lives items:** both carry a body note that the
2026-09-08 Phase 0 reconciliation pass closed them with a resolution copy-pasted from
an unrelated observation (the exact defect Campaign H's
`2026-09-08-reconciliation-stamped-a-borrowed-resolution` describes) and were reopened
rather than re-closed on borrowed evidence. They need a real verification pass in the
Counting Lives vault, which is out of scope from this TDL-rooted session — folds into
Campaign H's cross-repo scope decision.

---

## TDL residual carried forward (1 item)

*(Unchanged from 2026-09-15.)*

`2026-08-22-retired-procedure-kept-live-imperatives` (status: `OPEN — ESCALATED, OWNER
DECISION REQUIRED`) — the retirement-quoting contract limb is built and bound
(`tools/check_retired_imperatives.py`, pre-commit Gate 2, watched failure confirmed).
The enumerable-contract limb remains untouched. No new action recommended beyond
continuing to track it.

**Also noted, not in the 66-count:** `01KZK2BCXT7EKFZ6ZM2AMKFXJR` (status `ESCALATED`,
RECORD) still carries its 2026-09-08 "Supersession check" recommending **CLOSE AS
SUPERSEDED**; needs only Stephen's one-line confirmation.

---

## Completeness ledger

Every OPEN observation mapped to exactly one group above. Method: grep-counted
`**Status:** OPEN` occurrences in `log.md` before and after this session's edits (65 →
66, after −1 SKILL self-applied, +1 new GATE, +1 new PROCESS), then read every OPEN
observation's full text directly (not assembled from the 2026-09-15 packet's table) and
placed each in exactly one row below. Cross-checked: 5+2+7+6+16+6+1+4+7 = 54, +1 TDL
residual +11 non-TDL = 66.

| Group | Count | IDs |
|---|---:|---|
| A | 5 | 2026-09-08-concurrent-session-branch-switch · 2026-09-08-blocked-commit-reported-exit-zero · 2026-09-10-agent-command-slips-this-session · 2026-09-13-own-timeout-read-as-failure · 2026-09-14-commit-during-test-run-stashed-the-tree-under-tests |
| B | 2 | 2026-09-08-shell-rewrite-crlf-on-tracked-hook · 2026-09-08-name-only-ignores-content-flags |
| C | 7 | 2026-08-18-broad-repo-ci-remains-disabled · 2026-09-08-staged-only-lint-hides-untouched-file-debt · 2026-09-08-workflow-disabled-state-is-invisible-to-the-repo · 2026-09-08-advisory-lane-is-a-scoped-green-tick · 2026-09-08-disabled-ci-let-a-checkout-breaking-defect-live-three-months · 2026-09-08-git-add-dash-A-swept-in-generated-metadata · 2026-09-17-worktree-scoped-hookspath-runs-main-checkout-hooks |
| D | 6 | 2026-09-15-notation-guard-selftest-never-wired · 2026-09-11-mutation-harness-stale-bytecode · 2026-09-10-captured-pipes-deadlock-on-backgrounded-children · 2026-09-13-basetemp-longpath · 2026-09-17-hook-test-outside-ci-rotted-after-a-gate-was-added · 2026-09-23-codex-installer-recreates-the-dead-git-hooks-bug |
| E | 16 | 2026-09-08-cli-token-assertion-vacuous · 2026-09-11-deduplication-dropped-a-behavioural-default · 2026-09-12-negative-control-refused-upstream · 2026-09-13-evaluator-trusts-recorded-evidence · 2026-09-13-refusal-after-durable-mutation · 2026-09-14-producer-reviewer-rule-binds-a-caller-chosen-field · 2026-09-14-historical-ledger-replay-never-checked-against-current-code · 2026-09-14-focused-packet-omitted-the-currency-workflow-contracts · 2026-09-14-scored-assay-park-has-no-revisit-requirements · 2026-09-14-w11-role-names-invisible-to-admission · 2026-09-15-route-check-outside-admission-lock · 2026-09-15-fixture-authority-content-accepted-as-the-real-bar · 2026-09-15-removed-guard-made-a-dead-branch-live · 2026-09-16-borrowed-provenance-derivation-carried-its-unasserted-claims · 2026-09-16-hash-bound-rule-reference-is-not-rule-evaluation · 2026-09-17-cross-route-evidence-restated-a-subset-of-the-owning-routes-check |
| F | 6 | 2026-09-12-brief-role-vocabulary-vs-inherited-authority · 2026-09-14-brief-assumed-historical-records-fit-the-new-route · 2026-09-14-phase-brief-inherits-an-unscoped-action-list · 2026-09-14-handoff-cited-at-a-path-only-an-unmerged-pr-contains · 2026-09-14-review-fix-overwrote-a-concurrent-sessions-jira-record · 2026-09-08-formatter-collateral-needs-a-semantics-proof |
| G | 1 | 2026-09-11-required-review-producer-is-quota-limited |
| H | 4 | 2026-09-08-reconciliation-stamped-a-borrowed-resolution · 2026-09-01-completeness-ledger-missed-six-live-items · 2026-09-08-single-repo-review-scope-orphans-other-repos-observations · 2026-09-23-review-packet-never-reached-the-owner |
| I | 7 | 2026-09-15-spec-authority-column-divergence-filed-as-known-limit · 2026-09-16-automated-review-rounds-plateau-in-count-not-kind · 2026-09-16-red-run-exit-code-shared-with-missing-pytest · 2026-09-17-closed-intent-enum-sized-to-one-subphase · 2026-09-17-bounded-action-table-expectation-duplicated · 2026-09-17-merge-admission-cannot-see-a-clean-codex-review · 2026-09-18-design-probe-used-a-different-entry-point-than-the-public-path |
| Non-TDL: MathUni | 4 | 2026-08-11-handover-prescribed-an-unexecuted-tool-path · 2026-09-09-1980-page-pointers-name-no-result · 2026-09-10-copied-pattern-dropped-its-hardest-won-rule · 2026-09-09-the-branch-moved-under-a-running-session |
| Non-TDL: Counting Lives | 4 | 01KZM0EKJS03PPDST105X7C29H · 01KZM8H06Q2B64N30R4HM3RC1N · 01KZM9RKTTKKTBAMEPZAT10VN4 · 01M1C0H0KJEP3R27W3B9FWP4W6 |
| Non-TDL: codex_workflow | 3 | 01M044JXYSPP0VXH15TEZVCNA3 · 01M0641MDF9GV509T49SWED57V · 01M06KPH7CQRRPFGGXW67HT0Y4 |
| TDL residual | 1 | 2026-08-22-retired-procedure-kept-live-imperatives |
| **Total** | **66** | |

---

## Skills pass

One OPEN observation was lane-tagged SKILL this week
(`2026-09-17-worktree-sweep-needs-squash-aware-and-attribute-aware-checks`) —
**self-applied**: added a "Worktree Sweep" section to
`.agents/skills/using-git-worktrees-extras/SKILL.md` (squash-merge classification by
`headRefOid` rather than remote branch presence, all-`D`-status shells read as empty
not dirty, Windows read-only-directory removal order, ignored-cache allowlisting,
re-check-before-removing), synced to `.claude/skills/`
(`tools/sync_agent_skills.py --check` passes, byte-identical). The section explicitly
recommends — but does not build — a committed `tools/sweep_worktrees.py`; that stays a
GATE-lane follow-up pending Stephen's approval, not self-applied.

Cross-checked the full available-skills list against all 66 items:

- Several PROCESS/GATE items in Campaigns E, F, and I name `research-assurance-triage`,
  `contract-first-tdd`, or dispatch-readiness as the target for their suggested
  mechanism, rather than proposing a new skill. Folded into those campaigns rather than
  listed separately.
- **Repeat simplification candidate from 2026-09-15, still unresolved:** `task-observer`
  remains independently listed and invocable alongside `research-observer`, which
  explicitly supersedes it (this scheduled task's own instructions and the global
  `CLAUDE.md` trigger both already point at `research-observer`). Recommend removing
  `task-observer` from the active skill set, or making it a one-line redirect stub,
  once Stephen confirms nothing still invokes it by name. Raising this a second time
  because it is a genuine "what can we remove" candidate the simplification sweep is
  supposed to surface repeatedly until it's actioned, not a new finding.
- No skill this week showed the surface-form-vs-semantic-property gap (Principle 6) or
  an unenforced governed-set claim (Principle 7) that wasn't already captured in
  Campaign E's or I's clusters.

## Gate-liveness spot check

Picked two `.claude/hooks/*.sh` scripts with zero references under `tests/`:
`dispatch-readiness-guard.sh` and `git-commit-msg.sh`. `dispatch-readiness-guard.sh` is
live-wired in `.claude/settings.json` and has fired 1,567 times per `hook-receipts.log`
(including one historical `decision=deny` from a 2026-07-28 manual probe), but has no
automated test and fails open on error per its own header comment — logged as part of
`2026-09-23-codex-installer-recreates-the-dead-git-hooks-bug` (Campaign D).

Tracing `git-commit-msg.sh`'s installation path led to a second, more serious finding:
`.claude/hooks/git-commit-msg.sh` is not itself installed anywhere (dead weight, no
caller), but a **second copy** exists at `.codex/hooks/git-commit-msg.sh`, installed by
`.codex/hooks/install-git-hooks.py` — which copies it straight into `.git/hooks/commit-msg`,
the exact directory `core.hooksPath=.githooks` makes git ignore. This is the identical
failure shape as the documented 47-day-dead contract-validator incident that
`.claude/hooks/install-git-hooks.py` was rewritten to prevent — the `.codex/` sibling
was never given the same fix. No current caller of the Codex installer exists in the
tree, so this is a latent trap rather than an active defect, but the repo's own
observation log records many Codex-environment sessions. Logged as
`2026-09-23-codex-installer-recreates-the-dead-git-hooks-bug` (Campaign D). This is a
stronger finding than a routine missing-test gap: it is a live recurrence, in an
unaudited location, of an incident the project's own `CLAUDE.md` and hook docstrings
already name as a solved problem.

## Coverage question

"Did anything go wrong this week that no gate, contract, or invariant caught?" — 23 of
this week's 66 OPEN items are exactly this question, asked and answered in the course
of live 06s Gate 6 Phase 4 work (Campaigns E and I). No additional invention was needed
beyond the two gate-liveness gaps found above (the `.codex` installer and the
`dispatch-readiness-guard.sh` test gap) and the one process gap found while
re-verifying the prior packet's own delivery (Campaign H, item 4).

## This review's actions taken

1. Logged `2026-09-23-codex-installer-recreates-the-dead-git-hooks-bug` (GATE) and
   `2026-09-23-review-packet-never-reached-the-owner` (PROCESS) to `log.md`, per the
   Gate-Liveness Spot Check and this packet's own continuity check above.
2. **Self-applied** the one SKILL-lane observation: added a "Worktree Sweep" section to
   `.agents/skills/using-git-worktrees-extras/SKILL.md`; synced and verified
   byte-identical against `.claude/skills/`. Marked ACTIONED in `log.md`.
3. **Self-applied** one low-risk, mechanically-verified RECORD correction: fixed a
   stale self-contradiction inside `2026-09-08-claude-hooks-lack-lf-attribute` (a
   sentence claiming the `.gitattributes` gap was unfixed, written before PR #274
   landed and never updated after). Verified live against `.gitattributes` and
   `gh pr view 274` before touching it.
4. Re-verified all 52 observations from the 2026-09-15 packet directly against current
   `log.md` (not by trusting that packet's table); found one status change
   (`2026-09-11-repowise-post-commit-dirties-tracked-files` → ACTIONED) and folded it
   in with its own caveat (Campaign C).
5. Read and classified all 14 observations logged since the 2026-09-15 packet (13
   pre-existing + this review's 1 new SKILL item, now 0 remaining SKILL items) into
   Campaigns C, D, E, and the new Campaign I.
6. Wrote this packet. No other hooks, contracts, or gate/invariant/process-lane
   observations were self-applied — all remain report-only pending Stephen's decision,
   per the autonomous-run rule.
7. `last-review-date.txt` updated to `2026-09-23`.
8. **Unlike 2026-09-15, this packet is opened as a pull request** — directly acting on
   this week's own `2026-09-23-review-packet-never-reached-the-owner` finding rather
   than repeating it.

## Next steps

Check a box per campaign above (or reply with campaign letters to approve/defer/decline)
and this packet's mapped observations get re-resolved against current HEAD and
dispatched the same way the 2026-08-09 and 2026-08-26 packets were.
