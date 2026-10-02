# Weekly Research-System Review — Resolution Packet

**Review date:** 2026-09-29 (scheduled `weekly-system-review`, autonomous run). Re-resolved on
2026-10-02, after PRs #299–#307 merged and Codex reviewed this packet (see "Follow-up 2026-10-02").

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md`. On 2026-10-02 it held
193 entries, 25 of them OPEN.

**Scope:** every OPEN observation in the shared log. The 2026-09-25 owner decision named four
trees: TDL, MathUni, the Counting Lives vault and codex_workflow. Since then the log has also
picked up zktheoryweb, so this packet covers five; see "Non-TDL: zktheoryweb". The non-TDL trees
were read only.

**Decision owner:** Stephen

**Operating rule (unchanged since 2026-08-09):** approval authorizes a bounded
verify-then-fix campaign on a reviewed branch. It does not authorize direct changes to
`main`, silent gate weakening, or acceptance without the named controls.

**What this review changed.**
- *On 2026-09-29:* logged four observations, archived 43 entries that were already closed,
  staged one skill edit outside the repo (not applied; see Campaign J), and wrote this packet.
- *On 2026-10-02:*
  - flipped the 35 "fix in review" observations to ACTIONED, each against its PR's merge
    commit (see the next section);
  - logged one observation (Campaign S);
  - folded in the seven observations other sessions logged after 2026-09-29 (four of them OPEN);
  - answered Codex's eight review threads on this PR.

It made no skill edit: no open SKILL-lane item was free of an owner decision. It changed nothing
on the GATE, INVARIANT or PROCESS lanes, and nothing in the other trees. Everything below is a
recommendation.

## Where last week's packet stands

The 2026-09-23 packet (PR [#299](https://github.com/ZK-Theory/TDL/pull/299)) reached its owner:
all nine campaigns were decided on 2026-09-25 and built the same day as PRs #300–#307. That is
the positive control for `2026-09-23-review-packet-never-reached-the-owner`. A packet opened as
a PR was decided in two days. The 2026-09-15 packet, committed without a PR, went unseen for
eight.

**All nine PRs merged on 2026-09-30.** Their 35 observations are now ACTIONED. Each Status line
names its own mechanism and its PR's merge commit. Each was re-checked against `origin/main` on
2026-10-02. Campaign I's six lessons, for example, are present in `contract-first-tdd`,
`tda-task-brief-from-plan`, `tda-large-workflow-supervision` and `using-git-worktrees-extras`.

| PR | Campaign | Obs | Merge commit | Left open |
|---|---|---:|---|---|
| [#304](https://github.com/ZK-Theory/TDL/pull/304) | G + I (admission) | 2 | `8f25994d` | a clean +1 is read only when the sweep fires (Campaign M) |
| [#300](https://github.com/ZK-Theory/TDL/pull/300) | A | 5 | `812cc0f9` | the guard's mutation run, left to you in the PR; round-3 follow-ups |
| [#301](https://github.com/ZK-Theory/TDL/pull/301) | B | 2 | `5f8d1bbb` | none. The main-checkout CRLF repair was verified done on 2026-09-29 |
| [#302](https://github.com/ZK-Theory/TDL/pull/302) | C | 4 | `db46d7ad` | the desktop app writes the absolute `core.hooksPath`. Four old worktrees still carry it, and `goofy-saha-aedb62`, created 2026-10-02, has it too |
| [#303](https://github.com/ZK-Theory/TDL/pull/303) | D | 6 | `91640089` | round-3 follow-ups (`mutation_check.py`, the `.git/hooks` writer lint) |
| [#305](https://github.com/ZK-Theory/TDL/pull/305) | F + I | 9 | `9ea15760` | round-3 follow-ups (`check_brief_paths.py`, `planned_outputs`) |
| [#306](https://github.com/ZK-Theory/TDL/pull/306) | H | 4 | `c4962d5d` | round-3 follow-ups (lint edge cases that silently drop entries) |
| [#307](https://github.com/ZK-Theory/TDL/pull/307) | E lessons + I | 3 | `54808984` | your `CONVENTIONS.md` decision on the stopping rule; the cost carve-out (Campaign J) |
| [#299](https://github.com/ZK-Theory/TDL/pull/299) | decision record | — | `e2f3a3c8` | — |

Every "left open" item above is tracked: in a campaign below, or in
`2026-09-30-system-review-prs-stopping-rule-follow-ups` (Campaign R). Nothing was closed by
moving it out of sight.

**Merged, not yet live where you work.** The main checkout `C:\Users\steph\TDL` is still on
local `main` at `8e14d1da`, 13 commits behind `origin/main`. Commits made there run the
pre-merge `.githooks`, and sessions rooted there load the pre-merge harness hooks. So #300's
refusal of commits on `main` is not in force in the one checkout that sits on `main`. See
Campaign S.

## How to use this packet

Tick one box per group unless the group says its boxes combine. An approved group first
re-resolves each mapped observation against current HEAD and the owning tree. If it is already
compliant or superseded, record the evidence, mark it ACTIONED or DECLINED, and archive it. If it
is still valid and in scope, build the named mechanism with its negative control. If another
tree or process owns it, record the exact owner and keep only that remainder open.

## Decision summary

| Group | OPEN | Recommended resolution | Decision |
|---|---:|---|---|
| R. System-review follow-ups (round 3) | 1 | One follow-up PR, one commit per item, starting with #302's legacy `.git/hooks` case | `[ ]` approve · `[ ]` defer |
| S. Merged gates not live in the main checkout (new) | 1 | Fast-forward the main checkout now; add a hook-currency check | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| Q. Full research_system suite red on `main` | 1 | A nightly sharded full-suite lane with a shrink-only baseline, after the triage task | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| J. Test cost and long-run evidence | 2 | Budgets you set; the runner fails over budget; amend the merged stopping rule; apply the staged skill edit | `[ ]` 4–5 now, 1–3 with the budget table · `[ ]` 4–5 only · `[ ]` defer · `[ ]` decline |
| K. `run_git` names its cause | 1 | One message change per cause and a test for each, on its own PR | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| L. Codex hook parity | 1 | A probe from a Codex session, then a single source or deliberate removal | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| M. Sweep cadence | 1 | Correct the header claim and pick a route (boxes combine) | `[ ]` (a) · `[ ]` (b) · `[ ]` (c) · `[ ]` (b) + (c) · `[ ]` defer |
| N. `results-no-overwrite` watched failure | 1 | Add a hook suite to `admission-controls` | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| O. Observer-skill hygiene | 2 | The lint mandate is satisfied since #306 merged; decide on tracking the observer skill and on demoting `task-observer` | `[ ]` approve both · `[ ]` approve one (name it) · `[ ]` defer · `[ ]` decline |
| P. Gate 6 store items filed as codex_workflow | 2 | Re-home them to the 06s D5 process as DEFERRED, like Campaign E | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| Non-TDL: Counting Lives | 4 | Instances verified fixed; keep one checklist carrier and one preflight | `[ ]` build both · `[ ]` close two instances, keep two carriers · `[ ]` defer |
| Non-TDL: MathUni | 4 | Close one as applied; one convention decision; two after porting | `[ ]` approve · `[ ]` defer |
| Non-TDL: codex_workflow | 1 | Unchanged; closure freshness binding | `[ ]` keep open · `[ ]` decline |
| Non-TDL: zktheoryweb (new tree) | 2 | Instances fixed; no CI exists to host the checks; decide whether the review covers this tree | `[ ]` add to scope · `[ ]` keep out of scope |
| TDL residual | 1 | Keep tracking the enumerable-contract limb | `[ ]` keep tracking |

Total: 1 + 1 + 1 + 2 + 1 + 1 + 1 + 1 + 2 + 2 + 4 + 4 + 1 + 2 + 1 = **25**.

---

## R — System-review follow-ups, round 3 (1)

**Defect.** `2026-09-30-system-review-prs-stopping-rule-follow-ups`. You accepted the
automated-review stopping rule for #299–#307 on 2026-09-30. Of the 39 round-3 Codex threads, 17
became known limits, one became an owner decision, and 21 became follow-ups. The entry lists
every follow-up by PR. Two of them were already done in #303's merge commit `a1b401ca`. Ten more
came from Codex's review of the three merge commits. The rest are real defects that stay active
work, as the rule says. Three of them deserve to go first:
- **#302:** an unset `core.hooksPath` with legacy `.git/hooks` still passes the new hook check.
  That is the 47-day dead-hook class.
- **#306:** the lint has silent-loss paths. An unterminated fence drops every later entry, a
  `**Status:**` inside a fenced example is read as the real status, and a standalone `ESCALATED`
  is outside the OPEN set. That last one is why `01KZK2BCXT7EKFZ6ZM2AMKFXJR` and Observation 155
  never reach a ledger.
- **#300:** a detached A→B switch passes the HEAD re-read, and `git -c core.hooksPath=… commit`
  is not treated like `--no-verify`.

**Proposed action.** One PR, `pipe/system-review-followups`, with one commit per item and a
negative control per commit that fails on the parent. Workflow-file items go in their own PR, per
#304's `git.instructions.md` rule. Decide whether ESCALATED and PARTIALLY count as open before
the lint change, because the answer changes what every later ledger must cover.

**Controls.** Each commit's control fails on its parent, as with the round 1–2 fixes. For the lint
items, a fixture log with an unterminated fence must still yield every entry, or fail loudly.

**Recommended decision:** approve, #302's item first.

**Decision:** `[ ]` approve · `[ ]` defer

---

## S — Merged gates not live in the main checkout (1, new)

**Defect.** `2026-10-02-merged-gates-not-live-in-the-main-checkout`. On 2026-10-02 the main
checkout was 13 commits behind `origin/main`, with `.git/refs/heads/main` last written on
2026-09-17. Git resolves `core.hooksPath=.githooks` relative to the checkout, so commits made
there run the pre-merge hooks. `grep -c TDL_ALLOW_MAIN_COMMIT .githooks/pre-commit` returns 0
there and 4 on `origin/main`. The harness hooks come from `$CLAUDE_PROJECT_DIR`, so every session
rooted there lacks `commit-state-guard`. Neither liveness check notices: `install-git-hooks.py`
and `hook-gate` confirm a hook is wired and in-tree, not that it is the merged version. The
checkout also carries uncommitted Repowise edits to `.claude/CLAUDE.md` and
`.repowise-workspace.yaml`.

**Proposed action.** (1) Now, as your action: fast-forward the main checkout (`git pull
--ff-only`, after restoring or setting aside the two Repowise-owned files), then run
`install-git-hooks.py`. (2) A currency check at SessionStart (beside `handoff-surface`) and in
`hook-gate`. It warns when `HEAD..origin/main` contains a commit that touches `.githooks/`,
`.claude/hooks/` or `.claude/settings.json`, and names the count and the files.

**Controls.** Negative: a fixture checkout one hook-touching commit behind its remote must warn.
Positive: each session start prints the hook-tree commit in force.

**Recommended decision:** approve. Do (1) today; it is what puts last week's gates in force.

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## Q — Full research_system suite red on `main` (1)

**Defect.** `2026-10-02-full-suite-red-on-main-unseen`. The schema-validator-reuse PR (#310)
had to certify every research_system file. In that run, 23 files failed, 195 tests in all, and
they failed identically on the parent `54808984`: 1,001 tests compared, with no failure unique to
either side. No lane has run the full suite since the unfiltered CI lane was removed on
2026-09-11. Five failure families were found: path length, foreign worktree paths in fixtures,
skill-reference drift after #307, stale byte and hash pins, and possibly real behaviour changes.
A triage task was spawned (`task_69dfb1dc`).

**Proposed action.** After the triage lands, add a nightly sharded full-suite lane in the
02:00–11:00 window, with a recorded known-failure baseline that can only shrink. A new failure
fails the lane on the day it lands. This interacts with J: the lane is affordable only once
per-test cost is under budget, so set J's budgets with this lane in mind.

**Controls.** Negative: a failure outside the baseline fails the lane, and a baseline entry that
now passes fails until it is removed (stale-entry detection, as in MathUni's ratchet). Positive:
each night records pass, fail and baseline counts.

**Recommended decision:** approve, sequenced after the triage task.

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## J — Test cost and long-run evidence (2)

**Defect.** The SPEC route's public tests replay the whole lineage through the CLI, so each
sub-phase made every test longer. By 4b-2b a single group took 4h24m and a certification packet
took most of a day. The cost was disclosed as a "known limit" in #291, #297 and #298 and in
4b-2b's draft. It was never escalated. CI runs none of these tests, no test is marked `slow`,
and the per-PR review stopping rule sends anything that isn't a latest-round defect to known
limits.

- `2026-09-26-test-cost-normalised-as-a-known-limit`: the process failure itself. You stopped
  the certification on 2026-09-26; your directive is in memory (`feedback_test_runtime_escalate.md`).
- `2026-09-25-harness-background-runs-die-with-the-session`: harness background runs die when
  the session restarts. The resumable runner the entry proposes worked on 2026-09-26: a restart
  lost two minutes, not the run. The later entry reframes "make long runs survive" as part of how
  the cost was normalised, so decide the two together.

**Proposed action.**
1. You set wall-time budgets per test group and per certification packet, in the table below.
   The certification runner fails a group that exceeds its budget.
2. A test-time rise across sub-phases goes into each PR's decision table.
3. Profile before scaling out; build shared route prefixes once and copy the store; aim
   mutation controls at focused tests.
4. **Amend the merged stopping rule.** #307 merged on 2026-09-30 without a cost carve-out:
   `tda-large-workflow-supervision` on `main` still says "Everything else becomes a recorded
   known limit or a follow-up", and the 09-26 entry names that rule as a path that normalised
   the cost. Add one sentence in a follow-up skill PR: a test or packet time that grew since the
   previous PR is never a known limit; it goes to the PR's decision table.
5. **Apply the staged skill edit.** `tda-resource-preflight` triggers only on research compute,
   so no test packet ever invoked it, although your directive says to invoke it before any packet
   over 30 minutes. The staged edit is in
   `~/.claude/skill-updates/2026-09-29/tda-resource-preflight/` (`SKILL.md` and
   `proposed.diff`, 68 lines). Its base is still byte-identical to `main`'s copy. It adds test
   groups, certification packets and mutation-control batteries to the trigger; adds a "Long Test
   Runs" section (time one test alone and profile it before scale-out; growth goes to the decision
   table; a budget fails rather than being noted; resumable runners only after that decision, with
   environment failures classified and re-queued); adds a completion-checklist line; and bumps the
   version to 1.1.0. On approval, copy it into `.agents/skills/tda-resource-preflight/SKILL.md`
   and run `tools/sync_agent_skills.py` and `--check`.

**Budget table (you fill this; items 1–3 cannot be built until it is filled):**

| Scope | Budget (wall time) | Applies to |
|---|---|---|
| Single test | ____ | any test in a certification packet |
| Test group | ____ | each runner group |
| Certification packet | ____ | one sub-phase's full packet |
| Nightly full suite (Campaign Q) | ____ | all shards together |

**Controls.** Negative: a runner fixture whose group exceeds its recorded budget must exit
non-zero and name the group. Positive: every packet records each group's measured time beside its
budget and the previous PR's time.

**Recommended decision:** approve 4 and 5 now; they are text, and they match a directive you have
already given. Approve 1–3 when the budget table is filled.

**Decision:** `[ ]` approve 4–5 now and 1–3 once the budget table is filled · `[ ]` approve 4–5
only · `[ ]` defer · `[ ]` decline

---

## K — `run_git` names its cause (1)

**Defect.** `2026-09-26-git-unavailable-error-hides-its-cause`.
`research_system/git_execution.py::run_git` raises one message,
`ConfigurationError(unavailable_message)`, through three separate paths:
- the executable is missing (`_GIT_EXECUTABLE is None`, an early branch at line 155);
- an `OSError`, including "not a physical file";
- a `subprocess.TimeoutExpired` (10 seconds).

The cause is chained only as `__cause__`, which the public CLI does not print. On 2026-09-26
eleven certification groups failed in the same second with "Git inspection is unavailable", about
four hours of wall time were relaunched, and nothing recorded the cause. Re-verified on 2026-10-02:
no merged PR touched `git_execution.py`, so this is unchanged on `main`.

**Proposed action.** Append the cause to the message: "(timed out after 10s)", "(OSError: …)",
"(executable not found)". It goes on its own PR, outside any Gate 6 sub-phase. Classifying
environment failures in the runner belongs to Campaign J.

**Controls.** Negative: three tests, one per branch, each asserting its own distinct message:
- force `TimeoutExpired`;
- force `OSError`;
- set `_GIT_EXECUTABLE` to `None` (monkeypatched) and expect "executable not found".

With all three, an implementation that drops any distinction fails. Positive: the existing
refusal tests still match on the message prefix.

**Recommended decision:** approve. It is small, useful on its own, and makes the next burst
diagnosable.

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## L — Codex hook parity (1)

**Defect.** `2026-09-25-codex-live-hooks-are-stale-sibling-copies`. `.codex/hooks.json` wires
four scripts from `.codex/hooks/`, and each is an older copy of a `.claude/hooks/` script.
`.codex/hooks/notation-guard.sh` is 68 lines against 174 and still calls `python3`, which does not
resolve on this machine. Whether Codex runs these hooks at all can't be seen from Claude Code. The
follow-up entry (Campaign R) also carries `.codex/hooks.json`'s absolute paths.

**Proposed action.** From a Codex session, write a W₁ line to a scratch `papers/` file and watch
what happens. The result decides the route:
- **Outcome A, Codex runs the hooks:** point `.codex/hooks.json` at the `.claude/hooks` scripts,
  with an adapter only where the payload differs. Add a test that every script it names is a
  `.claude/hooks` script or byte-identical to one.
- **Outcome B, Codex ignores `.codex/hooks.json`:** delete the Codex wiring and the copies, and
  record that Codex sessions have no harness-hook enforcement. That boundary then belongs in
  `tda-agent-safety-guardrails`.

Either way, give `tda-agent-safety-guardrails` a line on the Codex hook wiring; today it names
none.

**Controls, conditional on the probe outcome:**
- *Outcome A.* Negative: the identity test fails on today's tree, where the four copies differ.
  Positive: after repointing, the Codex probe shows a deny carrying the current hook's message.
- *Outcome B.* Before anything is deleted, show that the wiring is ignored. The probe write is
  admitted, and a sentinel hook wired the same way, which only appends a line to a scratch file,
  leaves no trace. After deletion, a test asserts that `.codex/hooks.json` names no hook script,
  so a later re-wiring is a deliberate change rather than a silent copy.

**Recommended decision:** approve. The probe needs a Codex session, so it is a task for you or a
Codex worker, not an autonomous one.

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## M — Merge-admission sweep cadence (1, from the gate-liveness spot check)

**Defect.** `2026-09-29-sweep-cron-runs-at-two-percent-of-its-stated-cadence`. The sweep's header
promises an exposure window of "typically 5-10 minutes", and you chose the sweep on 2026-09-11 on
that basis. Since it went live it has run 111 times in 17.8 days: 6.2 runs a day against the 288
a `*/5` cron asks for. The shortest gap between runs was 106 minutes, the median 233, the longest
420. Every run succeeded, and the logic tests are sound; nothing measures how often it fires.

**#304 has merged (`8f25994d`, 2026-09-30) and made this matter more.** The sweep now carries
Codex's clean `+1` and its quota reply, because reactions and comments trigger no workflow. On
`main` the header still says "5-10 minutes", and `merge-admission.yml` has no `issue_comment`
trigger, so a PR that Codex finds clean now waits hours for admission. Per #304's own
`git.instructions.md` rule, the fix goes in its own workflow PR.

**Routes** (they combine; tick more than one if you want both):
- **(a)** Accept an hours-long window, correct the header, and rely on the merge queue's
  queue-time thread check for queued PRs.
- **(b)** Add a trigger that does fire for Codex's comments. Adding `issue_comment` alone would
  fail: `merge-admission.yml` resolves its target from `github.event.pull_request.number` and
  `.head.sha`, neither of which exists in an issue-comment payload, so every run would exit with
  "could not resolve a pull request number". The route must:
  - run only for PR comments (`github.event.issue.pull_request` set);
  - resolve the PR number from `github.event.issue.number`;
  - look up the PR's *current* head through the API rather than from the event;
  - add `github.event.issue.number` to the concurrency key, so comment runs and PR-event runs for
    one PR share a group.

  The cron stays as a backstop.
- **(c)** Add a cadence watchdog, in the `ars-artefact-currency-watchdog` pattern, that fails
  when the newest sweep run is older than a stated bound.

**Controls.**
- For (b): a fixture `issue_comment` payload on a PR resolves to that PR's number and current
  head and re-evaluates admission. A comment on a plain issue is ignored. Two events for the same
  PR share one concurrency group.
- For (c): a run-list fixture whose newest entry is older than the bound fails, and every run
  reports the measured gap.
- For any route: the header states the measured window, not the intended one.

**Recommended decision:** (b) + (c), with the header correction, in one workflow PR. (b) cuts the
window for the common case, and (c) watches the cadence itself.

**Decision:** `[ ]` (a) · `[ ]` (b) · `[ ]` (c) · `[ ]` (b) + (c) · `[ ]` defer

---

## N — `results-no-overwrite` watched failure (1, from the gate-liveness spot check)

**Defect.** `2026-09-29-results-no-overwrite-never-watched-to-fail`. This hook enforces an APM
lock: results are never overwritten. Since 2026-07-28 it has fired 2,026 times, every one
`decision=allow`, and no test names it. #303 merged with controls for `notation-guard` and
`dispatch-readiness-guard`. That leaves this as the only deny-capable `.claude/hooks` PreToolUse
guard with no automated deny case, which was re-verified on `main` on 2026-10-02. It fails open on
any error, so a regression in its Python block would look like the same stream of allows.

Its matcher is `Write|Edit|MultiEdit` (`.claude/settings.json:17`). It denies Edit and MultiEdit
on an existing results file, a Write to an existing `.npy` or `.npz`, and a Write whose content
differs from an existing `.json`. Result scripts that write through Python are outside its scope,
and nothing records that.

**Proposed action.** Add `tests/tools/test_results_no_overwrite_hook.py` in the shape of
`test_admin_bypass_guard_hook.py`, run through the real receipt wrapper, in the `admission-controls`
lane beside #303's suites. Record the script-side scope limit in the hook header.

**Controls.** Negative, four deny cases, each asserting its deny reason:
- Edit on an existing results JSON;
- MultiEdit on an existing results JSON, so losing the MultiEdit branch fails a test;
- Write to an existing `.npy`;
- Write of differing content to an existing `.json`.

Positive: a new date-suffixed file, a byte-identical rewrite and a path outside `results/` are
allowed, and a malformed payload fails open with the stderr warning.

**Recommended decision:** approve, as a follow-up to #303 (same pattern, same lane).

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## O — Observer-skill hygiene (2)

**Defects.**
- `2026-09-29-review-instructions-landed-before-their-tool-merged`. On 2026-09-25 the global
  `research-observer` skill and the `weekly-system-review` task were edited to require
  `tools/observation_log_lint.py` while that tool existed only on #306's branch.
  - **The immediate defect is gone.** #306 merged on 2026-09-30 (`c4962d5d`), and the tool on
    `main` is byte-identical to the branch copy this review ran on 2026-09-29.
  - **The structural cause remains.** The instruction files are outside version control, so their
    edits still ship before the mechanisms they mandate.
- `2026-09-29-task-observer-still-triggers-beside-research-observer`. Raised by the 2026-09-15
  and 2026-09-23 packets, logged now. `task-observer`'s description still says "Invoke at the
  start of ANY session", beside `research-observer`, which supersedes it. The global `CLAUDE.md`
  keeps `task-observer` as the fallback for environments without `research-observer`, so deleting
  it would break that fallback.

**Proposed action.** (1) Give `research-observer` an authoring copy under `.agents/skills/` and
the sync manifest, so its edits ride the same PR as the tools they require. Or decide explicitly
to keep it global, and record that its edits need the matching mechanism merged first. (2) Rewrite
`task-observer`'s description so it triggers only where `research-observer` is unavailable, after
a dated backup, and keep the file.

**Controls.** (1) The next scheduled run finds every tool its instructions name at that path on
the ref it runs from. (2) After the edit, the Claude Code skill list has a single session-start
observer trigger.

**Recommended decision:** approve both.

**Decision:** `[ ]` approve both · `[ ]` approve one (name it) · `[ ]` defer · `[ ]` decline

---

## P — Gate 6 store items filed as codex_workflow (2)

**Defect.** Earlier packets listed `01M0641MDF9GV509T49SWED57V` (object rollback vs identity
census on empty directories) and `01M06KPH7CQRRPFGGXW67HT0Y4` (recovery marker presence bypassing
transaction authority) as codex_workflow items, because they were logged from a Codex session.
Both targets are TDL `research_system` store contracts: `ObjectStore`, at
`research_system/store/objects.py:224`, and the authority-registration recovery marker. The
2026-09-08 Phase 0 reconciliation found no direct control for either. It kept them "for a
separately authorized bounded test". Their owner is the 06s Gate 6 D5 process, the same as
Campaign E's sixteen items, which were DEFERRED there on 2026-09-25.

**Proposed action.** Set both to `DEFERRED — owned by the 06s Gate 6 D5 process`, as with Campaign
E, and name them in the next 06s sub-phase brief's intake list.

**Controls.** None at this step; this is a routing correction. The D5 sub-phase that picks them up
owns their negative controls:
- an empty identity directory after rollback, with an exact retry in a fresh process;
- a Windows-junction or POSIX-symlink marker redirect.

**Recommended decision:** approve.

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## Non-TDL: Counting Lives (4) — read-only verification

| Observation | Verified 2026-09-29 | Remaining | Carrier if instances close |
|---|---|---|---|
| `01KZM0EKJS03PPDST105X7C29H` (CPI note kept superseded chronology) | **Instance fixed.** `02 - Sources/literature-notes/Bureau of the Budget – CPI Indexing Decision 1969.md` now separates 1969 (CPI adjustment, farm threshold 70→85%) from 1981 (farm/non-farm and sex-of-head distinctions removed), with page fields for both (Fisher pp. 24–33, 42–44). Ledger row `R-CH01-05` is `closed` | The rule that a dated threshold claim needs a page-located basis | the checklist carrier, `01KZM8H0…` |
| `01KZM8H06Q2B64N30R4HM3RC1N` (outline drifts from redrafted scenes) | Ch01's instance was corrected in-session. No outline-to-scene reconciliation rule exists in `CONVENTIONS.md` or `00 - Dashboard/Redraft Campaign Ledger.md` | The trigger itself | **stays open as the checklist carrier** |
| `01KZM9RKTTKKTBAMEPZAT10VN4` (scene naming drift) | **Instance fixed.** Ch01's five sections use `S{N} - Title - Subtitle.md`, and `Index.md` lists them as flat strings, as `CONVENTIONS.md:182–196` requires | No check compares filenames, H1s and `Index.md` | the checklist carrier, `01KZM8H0…` |
| `01M1C0H0KJEP3R27W3B9FWP4W6` (non-live citekeys presented as draft-ready) | The ledger has a manual "Citation rule" and a per-chapter pass (`R-CH01-12`: 23 citekeys resolved against `08 - Bibliography/Counting Lives.bib`). No scripted preflight exists anywhere in the vault | The mechanical preflight | **stays open as the preflight carrier** |

The **chapter-close checklist** has three parts:
- outline-to-scene reconciliation;
- a filename, H1 and `Index.md` comparison;
- a page-located basis for any dated claim.

The **citation preflight** is a read-only pass over each chapter's Longform scenes, checked
against the Better BibTeX export. Its negative control is a planted placeholder key.

The two items the 2026-09-08 pass closed on borrowed text (`01KZM8H0…`, `01KZM9RK…`) now have the
real verification they were reopened for: the instances are fixed, and the mechanism is missing.

**Decision:**
- `[ ]` build both in a Counting Lives session, with all four staying open until built;
- `[ ]` close `01KZM0EK…` and `01KZM9RK…` on this evidence, add their checklist parts to
  `01KZM8H0…`, and keep `01KZM8H0…` (checklist) and `01M1C0H0…` (preflight) open;
- `[ ]` defer.

## Non-TDL: MathUni (4) — read-only verification

MathUni `origin/main` is `40d8d83` (the PR #32 merge). The local checkout sits on the merged
branch `gate/close-four-authoring-loop-gaps`.

| Observation | Verified 2026-09-29 | Recommendation |
|---|---|---|
| `2026-08-11-handover-prescribed-an-unexecuted-tool-path` | **Applied.** `docs/plans/2026-08-11-s2-content.md:69–71` requires the source map to record "how the extract was actually taken, filled in after the extraction, never in advance". The S1–S4 content builds that needed it are done | Close as ACTIONED on this evidence; carry the column into the next content-plan template |
| `2026-09-09-1980-page-pointers-name-no-result` | `scripts/check_citations.py` keeps `NO-RESULT-CITED` as its own status, so the unverifiable fraction stays visible (the entry's "if acceptable" branch). The convention itself was never decided; `LESSON-RUBRIC.md` Gate 1.12 is unchanged | **Your convention decision:** accept bare page pointers, or require a searchable anchor (a result id or a quoted phrase of three or more words) |
| `2026-09-09-the-branch-moved-under-a-running-session` | MathUni has no `.claude/hooks`, so no branch-drift guard | #300 has merged: port `commit-state-guard` to MathUni's own `.claude/settings.json` (#300's PR notes this) |
| `2026-09-10-copied-pattern-dropped-its-hardest-won-rule` | The canvas-drift list now gets `--baseline` in CI (`.github/workflows/quality-gates.yml:166`). There is no shared `scripts/ratchet.py`, and `tests/test_allowlist_ratchets.py` does not require `--baseline` wiring for each list | Build the shared helper and the completeness assertion in a MathUni session |

**Decision:** `[ ]` approve (close the handover item; the rest as recommended) · `[ ]` defer

## Non-TDL: codex_workflow (1) — read-only verification

`01M044JXYSPP0VXH15TEZVCNA3`: a deployment closure went stale after the same run resumed.
codex_workflow `1.1.2`'s `end_of_session.md` still runs closure "once after every substantive
Medium or Heavy" task. It has no binding to Git HEAD or the ledger tail, and no staleness marker.
Unchanged and still valid.

**Decision:** `[ ]` keep open for a codex_workflow session · `[ ]` decline

## Non-TDL: zktheoryweb (2) — read-only verification, new tree

Two OPEN entries logged on 2026-09-30 target `C:\Projects\zktheoryweb`, which the 2026-09-25
scope decision did not name. I read them and checked that tree read-only on 2026-10-02.

| Observation | Verified 2026-10-02 | Remaining |
|---|---|---|
| `2026-09-30-open-ended-security-override-crossed-a-major` | **Instance fixed.** `package.json` `overrides` no longer pins `vite` (only `"yaml": "$yaml"` remains) | The two proposed checks: an override must resolve inside its owner's declared range, and every CSP hash must be present. Neither exists |
| `2026-09-30-client-bundle-rule-held-only-by-tree-shaking` | **Instance fixed.** `src/lib/bibliographyFormat.ts` exists, so the client island no longer imports the data-bearing module | The post-build check: a bundle-content or size budget on `dist/_astro/*.js`. Not present |

The repo has **no `.github/workflows/`**, so the proposed "CI step" mechanisms have no host. They
would have to run in the Netlify build command or an `npm` script that the build invokes.

**Decision:**
- `[ ]` add zktheoryweb to the review scope, and route both mechanisms to a zktheoryweb session,
  with the build-hosted checks as the host decision;
- `[ ]` keep it out of scope, and have its sessions disposition their own entries.

## TDL residual (1)

`2026-08-22-retired-procedure-kept-live-imperatives` (OPEN — ESCALATED, owner decision required).
The retirement-quoting limb is built and bound (pre-commit Gate 2); the enumerable-contract limb is
untouched. No change since 2026-09-23.

Also noted, not in the OPEN count, because a standalone `ESCALATED` falls outside the lint's OPEN
set (see Campaign R): `01KZK2BCXT7EKFZ6ZM2AMKFXJR` still carries its 2026-09-08 recommendation to
**close as superseded**. It needs only your one-line confirmation. This is the third packet to
raise it.

**Decision:** `[ ]` keep tracking · `[ ]` confirm `01KZK2BC…` closed as superseded

---

## Completeness ledger

Computed, not assembled. Every OPEN id comes from `observation_log_lint.parse` over the live log
on 2026-10-02, after the 35 merged-campaign entries were flipped to ACTIONED. It is checked with
`tools/observation_log_lint.py <log> --packet <this file>` (see "Lint and ledger check").

| Group | Count | IDs |
|---|---:|---|
| R | 1 | 2026-09-30-system-review-prs-stopping-rule-follow-ups |
| S | 1 | 2026-10-02-merged-gates-not-live-in-the-main-checkout |
| Q | 1 | 2026-10-02-full-suite-red-on-main-unseen |
| J | 2 | 2026-09-25-harness-background-runs-die-with-the-session · 2026-09-26-test-cost-normalised-as-a-known-limit |
| K | 1 | 2026-09-26-git-unavailable-error-hides-its-cause |
| L | 1 | 2026-09-25-codex-live-hooks-are-stale-sibling-copies |
| M | 1 | 2026-09-29-sweep-cron-runs-at-two-percent-of-its-stated-cadence |
| N | 1 | 2026-09-29-results-no-overwrite-never-watched-to-fail |
| O | 2 | 2026-09-29-review-instructions-landed-before-their-tool-merged · 2026-09-29-task-observer-still-triggers-beside-research-observer |
| P | 2 | 01M0641MDF9GV509T49SWED57V · 01M06KPH7CQRRPFGGXW67HT0Y4 |
| Non-TDL: Counting Lives | 4 | 01KZM0EKJS03PPDST105X7C29H · 01KZM8H06Q2B64N30R4HM3RC1N · 01KZM9RKTTKKTBAMEPZAT10VN4 · 01M1C0H0KJEP3R27W3B9FWP4W6 |
| Non-TDL: MathUni | 4 | 2026-08-11-handover-prescribed-an-unexecuted-tool-path · 2026-09-09-1980-page-pointers-name-no-result · 2026-09-09-the-branch-moved-under-a-running-session · 2026-09-10-copied-pattern-dropped-its-hardest-won-rule |
| Non-TDL: codex_workflow | 1 | 01M044JXYSPP0VXH15TEZVCNA3 |
| Non-TDL: zktheoryweb | 2 | 2026-09-30-open-ended-security-override-crossed-a-major · 2026-09-30-client-bundle-rule-held-only-by-tree-shaking |
| TDL residual | 1 | 2026-08-22-retired-procedure-kept-live-imperatives |
| **Total** | **25** | |

---

## Lint and ledger check

| When | Tool | Result |
|---|---|---|
| 2026-09-29, before this review's edits | copy from `origin/pipe/observation-log-lint` (#306, `f00970b8`) | `181 observation(s): 51 OPEN`, no findings |
| 2026-09-29, after four new entries and the archival | same copy | `185 observation(s): 55 OPEN`, no findings; `--packet` matched 55/55 |
| 2026-10-02, after the 35 flips and one new entry | `tools/observation_log_lint.py` on `main` (byte-identical to the copy above) | `193 observation(s): 25 OPEN`, no findings; `--packet` matches 25/25 |

Negative control: the same `--packet` check fails against the 2026-09-23 packet's ledger. It
names the observations that ledger lacks and the ACTIONED and DEFERRED items it still lists.

The 35 flips were made by a script that refused to write unless:
- every pending "fix in review: PR #NNN" entry had a mapping, and nothing else did;
- each entry's PR number matched its mapping;
- the order of ids was unchanged;
- the OPEN set shrank by exactly those 35;
- the lint came back clean.

The pre-flip log is at `~/.claude/skill-updates/2026-10-02/log.md.before-flip`.

## Skills pass

**Inventory.** 63 repo skills are authored in `.agents/skills/` and mirrored to `.claude/skills/`,
and `sync_agent_skills.py --check` passes with every mirror `IDENTICAL` (re-run on 2026-10-02 after
merging `main`). Entries outside the sync manifest:
- present only in `.agents/skills/`:
  - `SKILL-INDEX.md`;
  - the nine `apm-N-*` skills;
  - the four `source-command-*` Codex slash-command shims (`source-command-apm-2-initiate-manager`,
    `-6-handoff-manager`, `-7-handoff-worker` and `-8-summarize-session`);
  - `writing-skills-extras`;
- present in both trees but maintained separately per runtime: `apm-communication`.

Each skill directory among them matches `EXCLUDE_PATTERNS` in `tools/sync_agent_skills.py`. Also checked: the global
`research-observer` and `task-observer`, and the plugin skills in the session list.

**Cross-check of every OPEN group against every relevant skill:**
- **J:** `tda-resource-preflight`'s trigger covers only research compute (staged edit, Campaign J).
  `tda-large-workflow-supervision` merged its stopping rule without the cost carve-out (Campaign J,
  item 4). `tda-acceleration-benchmarking` is already cross-referenced from the preflight skill; no
  change.
- **Q:** no skill owns "a lane that runs the whole suite". This is CI design, not skill prose.
- **K:** `tda-diagnosing-computational-defects` and `executing-plans-extras`. The lesson about
  environment versus test failures belongs in the runner (J), not in new prose.
- **L:** `tda-agent-safety-guardrails` names no Codex hook wiring. Add the line when L resolves;
  writing it before the probe would repeat an unverified claim.
- **N:** `result-provenance-review` covers no-overwrite behaviour, but not the hook's scope. The hook
  header is the right place for that.
- **O and S:** `research-observer`, `tda-skill-authoring-workbench` (dual-tree mechanics) and
  `using-git-worktrees-extras` (checkout currency) bear on these.
- **R:** last week's skill edits are now on `main`. They include `contract-first-tdd` 1.1.0,
  `tda-task-brief-from-plan` 1.4.0, `tda-large-workflow-supervision`, `executing-plans-extras` and
  `using-git-worktrees-extras`. The round-3 `contract-first-tdd` gaps are in R's list.
- **Counting Lives, MathUni and zktheoryweb:** fixes belong in those trees.
  `anthropic-skills:chapter-session` is the likely home for the Counting Lives checklist. Nothing
  was applied from here.

**Simplification sweep ("what can we remove?").** One candidate, now logged:
`2026-09-29-task-observer-still-triggers-beside-research-observer` (Campaign O). No other skill's
trigger overlaps an existing one closely enough to merge.

**Self-applied:** none. No SKILL-lane item was open without an owner decision.

**Compliance of the staged edit with the cross-cutting principles:**
- Principle 10, establish a baseline before varying a cause: time one test alone before scaling
  out.
- Principle 9: a budget is a gate that can fail.
- Principle 4 (WSL/background compute): no `&`, `nohup` or `Start-Process` detachment.

## Gate-liveness spot check

I picked two gates nobody had recently watched fail:
1. **`merge-admission-sweep.yml`**. It has a positive signal: every run prints its verdict line.
   It has logic-level negative controls: ten sweep tests in `tests/tools/test_merge_admission.py`.
   But its **cadence** is claimed and never measured, and the measurement contradicts the claim by
   about 40×. This is Campaign M.
2. **`.claude/hooks/results-no-overwrite.sh`**. It has a positive signal (2,026 receipts) and **no
   negative control**: zero denies on record, and no test, still true after #303. This is
   Campaign N.

Both are findings, not probes; no destructive probe was run.

Checked in passing and healthy on 2026-09-29:
- the main checkout's `core.hooksPath` is the relative `.githooks` at local scope, and this
  review's linked worktree resolves the same;
- no tracked hook file has a CR byte on disk;
- every tracked workflow's API state is `active`.

The 2026-10-02 follow-up adds Campaign S. Those same hooks are wired correctly but are not the
merged version, which no current liveness check asks about.

## Coverage question

"Did anything go wrong that no gate, contract or invariant caught?" Yes, several times. Each case
is logged under the lane of the mechanism that should own it.

| What went wrong | Caught by | Observation |
|---|---|---|
| Test groups grew to hours and a packet to a day; disclosed in four PRs, never escalated | You, by hand (2026-09-26) | `2026-09-26-test-cost-normalised-as-a-known-limit` (J) |
| Eleven groups lost to an undiagnosable "Git inspection is unavailable" burst | Nothing; the cause is unrecoverable | `2026-09-26-git-unavailable-error-hides-its-cause` (K) |
| A harness restart killed a run and left no partial evidence | By hand | `2026-09-25-harness-background-runs-die-with-the-session` (J) |
| Codex runs months-old hook copies | By hand, during #303 | `2026-09-25-codex-live-hooks-are-stale-sibling-copies` (L) |
| The sweep ran at 2% of its stated cadence for 17 days | This review, by hand | `2026-09-29-sweep-cron-runs-at-two-percent-of-its-stated-cadence` (M) |
| The review's mandated lint was missing on `main` | This review, at step 2 | `2026-09-29-review-instructions-landed-before-their-tool-merged` (O) |
| 195 research_system tests red on `main`, with no lane running them | By hand, certifying #310 (2026-10-02) | `2026-10-02-full-suite-red-on-main-unseen` (Q) |
| The merged gates were not live in the main checkout two days after merge | This follow-up, by hand | `2026-10-02-merged-gates-not-live-in-the-main-checkout` (S) |
| A `>=` security override crossed a major; a data-bearing module reached the client bundle | By hand, in zktheoryweb | the two zktheoryweb entries |

None is a numerical or statistical failure, so none is an invariant-battery item.

## This review's actions

**2026-09-29 (scheduled run)**
1. Found the previous packet (PR #299), confirmed every campaign had been decided, and re-resolved
   each one against the live state of its PR.
2. Ran the lint (from #306's branch) before and after this review's edits: clean both times.
3. Verified the 11 non-TDL residuals read-only against MathUni, Counting Lives and codex_workflow.
   Two of them turned out to be TDL `research_system` items (Campaign P).
4. Logged four observations: two GATE, one PROCESS and one SKILL.
5. Staged one skill edit outside the repo (`~/.claude/skill-updates/2026-09-29/tda-resource-preflight/`),
   not applied.
6. Archived the 43 entries that were already ACTIONED, CLOSED or DECLINED and still held full text,
   the first archival pass since 2026-09-01. The full text moved verbatim to
   `archive/log-2026-09-29.md`, with a one-line stub left under each id. `log.md` went from 3,587 to
   2,367 lines; the id order and the OPEN set were unchanged, and the lint stayed clean. The
   pre-archival log is at `~/.claude/skill-updates/2026-09-29/log.md.before`. Nothing was
   re-dispositioned.
7. Updated `last-review-date.txt` to `2026-09-29`.
8. Opened this packet as PR #308.

**2026-10-02 (follow-up after the merges and Codex's review)**
1. Re-resolved the nine merged PRs. The 35 "fix in review" entries were flipped to ACTIONED with
   per-entry mechanism text and merge commits, after their skill lessons were confirmed on
   `origin/main`. The "left open" remainders are routed to Campaigns M, R, J and S.
2. Logged `2026-10-02-merged-gates-not-live-in-the-main-checkout` (Campaign S).
3. Folded in the seven entries other sessions logged after 2026-09-29. Four are OPEN: R, Q and two
   zktheoryweb entries. Three were already ACTIONED by their sessions: two in zktheoryweb, and one
   in TDL (#304's apostrophe fix, `2026-09-30-workflow-script-broke-on-an-apostrophe-no-test-could-see`).
4. Answered Codex's eight review threads on this PR: Counting Lives carriers (no checklist work
   dropped), conditional controls for both Codex-probe outcomes, a combinable (b) + (c) box for M,
   the payload handling (b) needs, a third `run_git` control, MultiEdit in N, the `source-command-*`
   exclusions, and a budget table gating J's items 1–3.
5. Merged `origin/main` into this branch and re-ran `sync_agent_skills.py --check` and the ledger
   check.
