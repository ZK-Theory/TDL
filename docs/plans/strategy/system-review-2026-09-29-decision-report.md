# Weekly Research-System Review — Resolution Packet

**Review date:** 2026-09-29 (scheduled `weekly-system-review`, autonomous run)

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md` (185 entries, 55 OPEN
after this review's four new observations)

**Scope:** every OPEN observation in the shared log, across all four trees the log carries
(owner decision 2026-09-25): TDL, MathUni, the Counting Lives vault and codex_workflow. The
non-TDL trees were read only.

**Decision owner:** Stephen

**Operating rule (unchanged since 2026-08-09):** approval authorizes a bounded
verify-then-fix campaign on a reviewed branch. It does not authorize direct changes to
`main`, silent gate weakening, or acceptance without the named controls.

**What this run changed.** It logged four observations, staged one skill edit outside the
repo (not applied; see Campaign J), and wrote this packet. It made no skill edit, because no
open SKILL-lane item was free of an owner decision. It left the other lanes (GATE, INVARIANT,
PROCESS) and the other trees untouched: everything below is a recommendation.

## Where last week's packet stands

The 2026-09-23 packet (PR [#299](https://github.com/ZK-Theory/TDL/pull/299)) reached its owner:
all nine campaigns were decided on 2026-09-25 and built the same day as PRs #300–#307. That is
the positive control for `2026-09-23-review-packet-never-reached-the-owner`. A packet opened as
a PR was decided in two days, where the 2026-09-15 packet committed without one went unseen for
eight.

**None of the eight implementing PRs has merged.** All are `BLOCKED` by `merge-admission`, and
nothing has moved since 2026-09-26 17:40Z. That was the evening the 06s 4b-2b certification
was stopped. The 35 observations these PRs carry therefore stay OPEN ("fix in review"). No new
campaign decision is needed for them; they need their review ladders finished. State at
2026-09-29 ~22:00Z:

| PR | Campaign | Obs | Head | Unresolved live threads | Blocker | Next action |
|---|---|---:|---|---:|---|---|
| [#304](https://github.com/ZK-Theory/TDL/pull/304) | G + I (admission) | 2 | `6963dff4` | 4 | thread finality | disposition 4 threads; **merge first**; see Campaign M before merging |
| [#300](https://github.com/ZK-Theory/TDL/pull/300) | A | 5 | `357d473f` | 11 | thread finality | disposition 11 threads; your mutation run of `commit-state-guard` |
| [#301](https://github.com/ZK-Theory/TDL/pull/301) | B | 2 | `796b6b3f` | 3 | thread finality | disposition 3 threads. The one-time main-checkout CRLF repair is **done**: no tracked hook in `.githooks/` or `.claude/hooks/` has a CR byte on disk today |
| [#302](https://github.com/ZK-Theory/TDL/pull/302) | C | 4 | `b129b6a0` | 1 | thread finality | disposition 1 thread. **Still pending:** all four `.claude/worktrees/*` still carry `core.hooksPath=C:\Users\steph\TDL\.githooks` at worktree scope |
| [#303](https://github.com/ZK-Theory/TDL/pull/303) | D | 6 | `500e03ff` | 0 | "review producers have not reached a terminal state": **no Codex review was ever requested** | comment `@codex review`; code-owner review of `ci.yml` |
| [#305](https://github.com/ZK-Theory/TDL/pull/305) | F + I | 9 | `6f30cfea` | 8 | thread finality | disposition 8 threads |
| [#306](https://github.com/ZK-Theory/TDL/pull/306) | H | 4 | `f00970b8` | 7 | thread finality | disposition 7 threads; **merge early**: it adds two new files, conflicts with nothing, and the weekly review depends on it (Campaign O) |
| [#307](https://github.com/ZK-Theory/TDL/pull/307) | E lessons + I | 3 | `ad146fde` | 1 | thread finality | disposition 1 thread; add the cost carve-out in Campaign J to its stopping rule; your `CONVENTIONS.md` decision |
| [#299](https://github.com/ZK-Theory/TDL/pull/299) | decision record | — | `0578b487` | 3 | — | disposition 3 threads (Codex found no new issue on the head); merge as the record |

Revised merge order: **#304, #306**, then #300–#303 (their `.githooks/pre-commit` hunks
need sequential rebases), then #305, #307 and #299.

## How to use this packet

Tick one box per group. An approved group first re-resolves each mapped observation against
current HEAD and the owning tree. Already compliant or superseded: record the evidence, mark it
ACTIONED or DECLINED, and archive it. Still valid and in scope: build the named mechanism with
its negative control. Owned elsewhere: record the exact owner and keep only that remainder open.

## Decision summary

| Group | OPEN | Recommended resolution | Decision |
|---|---:|---|---|
| R. Approved campaigns A–I, in review | 35 | Finish the ladders; merge in the revised order above | `[ ]` proceed · `[ ]` re-scope |
| J. Test cost and long-run evidence (new) | 2 | You set wall-time budgets; the runner fails over budget; carve cost out of #307's stopping rule; apply the staged preflight skill edit | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| K. `run_git` names its cause (new) | 1 | One-line message change and a test, on its own PR | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| L. Codex hook parity (new) | 1 | A probe from a Codex session, then a single source or an identity test | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| M. Sweep cadence (new, spot check) | 1 | Correct the header claim (in #304) and pick a route | `[ ]` (a) · `[ ]` (b) · `[ ]` (c) · `[ ]` defer |
| N. `results-no-overwrite` watched failure (new, spot check) | 1 | Add a hook suite to `admission-controls` | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| O. Observer-skill hygiene (new) | 2 | Make the lint mandate conditional until #306 merges; demote `task-observer`'s trigger | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| P. Gate 6 store items filed as codex_workflow | 2 | Re-home them to the 06s D5 process as DEFERRED, like Campaign E | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| Non-TDL: Counting Lives | 4 | Instances verified fixed; one chapter-close checklist; one citation preflight | `[ ]` approve · `[ ]` defer |
| Non-TDL: MathUni | 4 | Close one as applied; one convention decision; two after #300 | `[ ]` approve · `[ ]` defer |
| Non-TDL: codex_workflow | 1 | Unchanged; closure freshness binding | `[ ]` keep open · `[ ]` decline |
| TDL residual | 1 | Keep tracking the enumerable-contract limb | `[ ]` keep tracking |

Total: 35 + 2 + 1 + 1 + 1 + 1 + 2 + 2 + 4 + 4 + 1 + 1 = **55**.

---

## R — Approved campaigns A–I, in review (35)

Decided on 2026-09-25 and not re-litigated here. The completeness ledger maps each observation
to its PR, computed from each entry's own `Status:` line ("fix in review: PR #NNN"). Each flips
to ACTIONED with its PR's merge commit.

One cross-campaign finding came out of this review: #304 moves Codex's clean `+1` onto the
merge-admission sweep, and the sweep runs about every four hours, not every five minutes
(Campaign M). Settle M before or with #304.

**Decision:** `[ ]` proceed in the revised order · `[ ]` re-scope (name which PR)

---

## J — Test cost and long-run evidence (2, new)

**Defect.** The SPEC route's public tests replay the whole lineage through the CLI, so each
sub-phase made every test longer. By 4b-2b a single group took 4h24m and a certification
packet took most of a day. The cost was disclosed as a "known limit" in #291, #297 and #298 and
in 4b-2b's draft, and never escalated. Three things kept any alarm from firing: CI runs none of
these tests, no test is marked `slow`, and the per-PR review stopping rule sends anything that
is not a latest-round defect to known limits.

- `2026-09-26-test-cost-normalised-as-a-known-limit`: the process failure itself. You stopped
  the certification on 2026-09-26. Your directive is already recorded in memory
  (`feedback_test_runtime_escalate.md`).
- `2026-09-25-harness-background-runs-die-with-the-session`: harness background runs die when
  the session restarts, and WMI- or `Start-Process`-detached children die within seconds. The
  resumable runner the entry proposes worked on 2026-09-26: a restart lost two minutes, not the
  run. But the later entry reframes "make long runs survive" as part of how the cost was
  normalised, so decide the two together.

**Proposed action.**
1. You set wall-time budgets per test group and per certification packet. The certification
   runner fails a group that exceeds its budget.
2. A test-time rise across sub-phases goes into each PR's decision table.
3. Profile before scaling out; build shared route prefixes once and copy the store; aim
   mutation controls at focused tests.
4. **Amend #307 before it merges.** Its stopping rule ("Everything else becomes a recorded
   known limit or a follow-up") has no cost carve-out, yet the 09-26 entry names that rule as
   one of the paths that normalised the cost. Add one sentence: a test or packet time that
   grew since the previous PR is never a known limit; it goes to the PR's decision table.
5. **Apply the staged skill edit.** `tda-resource-preflight`'s description lists only research
   compute, so no test packet ever triggered it, although your directive says to invoke it
   before any packet over 30 minutes. The staged edit at
   `~/.claude/skill-updates/2026-09-29/tda-resource-preflight/` (`SKILL.md` and
   `proposed.diff`, 68 lines) does four things: it adds test groups, certification packets and
   mutation-control batteries to the trigger; adds a "Long Test Runs" section (time one test
   alone and profile it before scale-out; growth goes to the decision table; a budget fails, it
   is not a note; resumable runners only after that decision, with environment failures
   classified and re-queued); adds a completion-checklist line; and bumps the version to
   1.1.0. On approval, copy it into `.agents/skills/tda-resource-preflight/SKILL.md` and run
   `tools/sync_agent_skills.py` and `--check`.

**Controls.** Negative: a runner fixture whose group exceeds its budget must exit non-zero and
name the group. Positive: every packet records each group's measured time next to its budget,
and the previous PR's time for comparison.

**Recommended decision:** approve items 4 and 5 now; they are text, and they align with a
directive you have already given. Approve 1–3 once you have picked the budget numbers.

**Decision:** `[ ]` approve all · `[ ]` approve 4–5 only · `[ ]` defer · `[ ]` decline

---

## K — `run_git` names its cause (1, new)

**Defect.** `2026-09-26-git-unavailable-error-hides-its-cause`. `research_system/git_execution.py::run_git`
raises one message, `ConfigurationError(unavailable_message)`, for a missing executable, an
`OSError` and a `subprocess.TimeoutExpired` (a 10-second limit). The cause is chained only as
`__cause__`, which the public CLI does not print. On 2026-09-26, eleven certification groups
failed in the same second with "Git inspection is unavailable", about four hours of wall time
were relaunched, and nothing recorded which cause it was. Verified unchanged on `main` today
(lines 155–217).

**Proposed action.** Append the cause class to the message ("… (timed out after 10s)",
"… (OSError: …)", "… (executable not found)"), on its own PR, outside any Gate 6 sub-phase.
Classifying environment failures in the runner is in Campaign J.

**Controls.** Negative: a test that forces `TimeoutExpired`, and one that forces `OSError`,
each asserting its own distinct message text. Positive: the existing refusal tests still match
on the message prefix.

**Recommended decision:** approve. It is small, it has an independent value, and it makes the
next burst diagnosable.

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## L — Codex hook parity (1, new)

**Defect.** `2026-09-25-codex-live-hooks-are-stale-sibling-copies`. `.codex/hooks.json` wires
four scripts from `.codex/hooks/`, and each is an older copy of a `.claude/hooks/` script.
`.codex/hooks/notation-guard.sh` is 68 lines against 174. It still calls `python3`, which does
not resolve on this machine, so if it fires under Codex it denies every write. Whether Codex
runs these hooks at all can't be seen from Claude Code. Found during #303 and deliberately not
rewritten blind.

**Proposed action.** From a Codex session, write a W₁ line to a scratch `papers/` file and
observe the result. Then either point `.codex/hooks.json` at the `.claude/hooks` scripts
(adding an adapter where the payload differs) or delete the Codex wiring. Add a test that every
script `.codex/hooks.json` names is a `.claude/hooks` script or byte-identical to one. When
resolved, give `tda-agent-safety-guardrails` a line on the Codex hook wiring; it names none
today.

**Controls.** Negative: the identity test fails on today's tree, where four copies differ.
Positive: the Codex-session probe shows a deny with the current hook's message.

**Recommended decision:** approve. The first step needs a Codex session, so it is a task for
you or a Codex worker, not an autonomous one.

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## M — Merge-admission sweep cadence (1, new, from the gate-liveness spot check)

**Defect.** `2026-09-29-sweep-cron-runs-at-two-percent-of-its-stated-cadence`. The sweep's
header promises an exposure window of "typically 5-10 minutes", and you chose the sweep on
2026-09-11 on that basis. Since it went live it has run 111 times in 17.8 days: 6.2 runs a day
against the 288 that `*/5` asks for. The shortest gap between runs was 106 minutes, the median
233 and the longest 420. Every run succeeded, and the logic tests are sound. Nothing measures
how often it fires. **#304 raises the stakes:** it makes the sweep the carrier of Codex's clean
`+1` and its quota reply, because reactions and comments trigger no workflow. After #304, a PR
Codex finds clean waits hours for admission, and #304 keeps the "5-10 minutes" line.

**Routes.**
- (a) Accept an hours-long window, correct the header, and rely on the merge queue's
  queue-time thread check for queued PRs.
- (b) Add triggers that do fire (`issue_comment` covers Codex's quota comment and `@codex
  review`; `pull_request_review` already exists), keeping the cron as a backstop.
- (c) Add a cadence watchdog in the `ars-artefact-currency-watchdog` pattern that fails when
  the newest sweep run is older than a stated bound.

**Controls.** For (c): a run-list fixture whose newest entry is older than the bound must fail,
and every run reports the measured gap. For (b): a fixture `issue_comment` event must drive a
re-evaluation. For any route: the header states the measured window, not the intended one.

**Recommended decision:** (b) plus the header correction, folded into #304 before it merges,
because #304 is what makes the latency matter. Choose (c) as well if you want the cadence
itself watched.

**Decision:** `[ ]` (a) · `[ ]` (b) · `[ ]` (c) · `[ ]` defer

---

## N — `results-no-overwrite` watched failure (1, new, from the gate-liveness spot check)

**Defect.** `2026-09-29-results-no-overwrite-never-watched-to-fail`. This hook enforces an
APM_RULES lock (results are never overwritten). Since 2026-07-28 it has fired 2,026 times, all
`decision=allow`, and no test names it. #303 gives `notation-guard` and
`dispatch-readiness-guard` their controls. Once #303 merges, this becomes the only
deny-capable `.claude/hooks` PreToolUse guard with no automated deny case. It fails open on
any error, so a regression in its Python block would look like the same stream of allows. It
also covers only agent Write and Edit; result scripts writing through Python are out of its
scope, and nothing records that.

**Proposed action.** Add `tests/tools/test_results_no_overwrite_hook.py` in the shape of
`test_admin_bypass_guard_hook.py`, run through the real receipt wrapper, and place it in the
`admission-controls` lane beside #303's suites. Record the script-side scope limit in the hook
header.

**Controls.** Negative: three deny cases (Edit on an existing results JSON, Write to an
existing `.npy`, Write of differing content), each asserting the deny reason. Positive: a new
date-suffixed file, a byte-identical rewrite, and a path outside `results/` are allowed, and a
malformed payload fails open with the stderr warning.

**Recommended decision:** approve, as a follow-up to #303 (same pattern, same lane).

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## O — Observer-skill hygiene (2, new)

**Defects.**
- `2026-09-29-review-instructions-landed-before-their-tool-merged`. On 2026-09-25 at 18:33 the
  global `research-observer` skill and the `weekly-system-review` task were edited to require
  `tools/observation_log_lint.py`. That file exists only on #306's unmerged branch. Neither
  instruction file is under version control, so the instruction shipped at once and the tool
  is still waiting on review. This run extracted the tool from `origin/pipe/observation-log-lint`
  to run it, and so checked its own ledger with an unreviewed version of the check.
- `2026-09-29-task-observer-still-triggers-beside-research-observer`. The 2026-09-15 and
  2026-09-23 packets both raised this, and neither logged it. `task-observer`'s description
  still says "Invoke at the start of ANY session", beside `research-observer`, which
  supersedes it. The global `CLAUDE.md` keeps `task-observer` as the fallback for environments
  without `research-observer`, so deleting it would break that fallback.

**Proposed action.** (1) Merge #306 early; until then, make the two instructions conditional
("from `main`, or from `origin/pipe/observation-log-lint` until #306 merges"). Consider giving
`research-observer` an authoring copy under `.agents/skills/` and the sync manifest, so its
edits ride the same PR as the tools they require. (2) Rewrite `task-observer`'s description so
it triggers only where `research-observer` is unavailable, after a dated backup, and keep the
file.

**Controls.** (1) The next scheduled run finds the lint at the path it names on the ref it runs
from. (2) After the edit, the Claude Code skill list shows one session-start observer trigger.

**Recommended decision:** approve both. Merging #306 closes (1) on its own.

**Decision:** `[ ]` approve both · `[ ]` approve (1) only · `[ ]` defer · `[ ]` decline

---

## P — Gate 6 store items filed as codex_workflow (2)

**Defect.** Earlier packets listed `01M0641MDF9GV509T49SWED57V` (object rollback vs identity
census on empty directories) and `01M06KPH7CQRRPFGGXW67HT0Y4` (recovery marker presence
bypassing transaction authority) as codex_workflow items, because they were logged from a
Codex session. Both targets are TDL `research_system` store contracts: `ObjectStore`, at
`research_system/store/objects.py:224`, and the authority-registration recovery marker. The
2026-09-08 Phase 0 reconciliation found no direct control for either and kept them "for a
separately authorized bounded test". Their owner is the 06s Gate 6 D5 process, the same as
Campaign E's sixteen items, which were DEFERRED there on 2026-09-25.

**Proposed action.** Set both to `DEFERRED — owned by the 06s Gate 6 D5 process`, as with
Campaign E, and name them in the next 06s sub-phase brief's intake list.

**Controls.** None at this step; this is a routing correction. The D5 sub-phase that picks them
up owns their negative controls: an empty identity directory after rollback plus an exact retry
in a fresh process, and a Windows-junction or POSIX-symlink marker redirect.

**Recommended decision:** approve.

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## Non-TDL: Counting Lives (4) — read-only verification

| Observation | Verified 2026-09-29 | Remaining | Recommendation |
|---|---|---|---|
| `01KZM0EKJS03PPDST105X7C29H` (CPI note kept superseded chronology) | **Instance fixed.** `02 - Sources/literature-notes/Bureau of the Budget – CPI Indexing Decision 1969.md` now separates 1969 (CPI adjustment, farm threshold 70→85%) from 1981 (farm/non-farm and sex-of-head distinctions removed), with page fields for both (Fisher pp. 24–33, 42–44). Ledger row `R-CH01-05` is `closed` | The general rule for dated threshold claims needing a page-located basis before prose is complete | Fold into the chapter-close checklist below; close this entry on it |
| `01KZM8H06Q2B64N30R4HM3RC1N` (outline drifts from redrafted scenes) | Ch01's instance was corrected in-session. No outline-to-scene reconciliation rule exists in `CONVENTIONS.md` or `00 - Dashboard/Redraft Campaign Ledger.md` | The trigger itself | One **chapter-close checklist** in the Redraft Campaign Ledger: outline-to-scene reconciliation, filename/H1/Index comparison, dated-claim basis |
| `01KZM9RKTTKKTBAMEPZAT10VN4` (scene naming drift) | **Instance fixed.** Ch01's five sections use `S{N} - Title - Subtitle.md`, and `Index.md` lists them as flat strings, as `CONVENTIONS.md:182–196` requires | No check compares filenames, H1s and `Index.md` | The same checklist |
| `01M1C0H0KJEP3R27W3B9FWP4W6` (non-live citekeys presented as draft-ready) | The ledger has a manual "Citation rule" and a per-chapter pass (`R-CH01-12`: 23 citekeys resolved against `08 - Bibliography/Counting Lives.bib`). No scripted preflight exists anywhere in the vault | The mechanical preflight | A read-only citekey preflight over each chapter's Longform scenes against the Better BibTeX export, with a planted placeholder key as its negative control |

The two items the 2026-09-08 pass closed on borrowed text (`01KZM8H0…`, `01KZM9RK…`) now have
the real verification they were reopened for: the instances are fixed, and the mechanism is
missing.

**Decision:** `[ ]` approve the checklist and preflight (a Counting Lives session builds them) ·
`[ ]` close the three instance items on this evidence and keep only the preflight · `[ ]` defer

## Non-TDL: MathUni (4) — read-only verification

MathUni `origin/main` is `40d8d83` (the PR #32 merge). The local checkout sits on the merged
branch `gate/close-four-authoring-loop-gaps`.

| Observation | Verified 2026-09-29 | Recommendation |
|---|---|---|
| `2026-08-11-handover-prescribed-an-unexecuted-tool-path` | **Applied.** `docs/plans/2026-08-11-s2-content.md:69–71` requires the source map to record "how the extract was actually taken, filled in after the extraction, never in advance". The S1–S4 content builds that needed it are done | Close as ACTIONED on this evidence; carry the column into the next content-plan template |
| `2026-09-09-1980-page-pointers-name-no-result` | `scripts/check_citations.py` keeps `NO-RESULT-CITED` as its own status, so the unverifiable fraction stays visible (the entry's "if acceptable" branch). The convention itself was never decided; `LESSON-RUBRIC.md` Gate 1.12 is unchanged | **Your convention decision:** accept bare page pointers, or require a searchable anchor (a result id or a quoted phrase of three or more words) |
| `2026-09-09-the-branch-moved-under-a-running-session` | MathUni has no `.claude/hooks`, so no branch-drift guard | The same decision as Campaign A: port #300's `commit-state-guard` to MathUni once #300 merges |
| `2026-09-10-copied-pattern-dropped-its-hardest-won-rule` | The canvas-drift list now gets `--baseline` in CI (`.github/workflows/quality-gates.yml:166`). There is no shared `scripts/ratchet.py`, and `tests/test_allowlist_ratchets.py` does not require `--baseline` wiring for each list | Build the shared helper and the completeness assertion in a MathUni session |

**Decision:** `[ ]` approve (close the handover item; the rest as recommended) · `[ ]` defer

## Non-TDL: codex_workflow (1) — read-only verification

`01M044JXYSPP0VXH15TEZVCNA3` (a deployment closure went stale after the same run resumed).
codex_workflow `1.1.2`'s `end_of_session.md` still runs closure "once after every substantive
Medium or Heavy" task, with no binding to Git HEAD or the ledger tail and no staleness marker.
Unchanged, and still valid.

**Decision:** `[ ]` keep open for a codex_workflow session · `[ ]` decline

## TDL residual (1)

`2026-08-22-retired-procedure-kept-live-imperatives` (OPEN — ESCALATED, owner decision
required). The retirement-quoting limb is built and bound (pre-commit Gate 2); the
enumerable-contract limb is untouched. No change since 2026-09-23.

Also noted, not in the OPEN count: `01KZK2BCXT7EKFZ6ZM2AMKFXJR` (`ESCALATED`) still carries its
2026-09-08 recommendation to **close as superseded**. It needs only your one-line confirmation.
This is the third packet to raise it.

**Decision:** `[ ]` keep tracking · `[ ]` confirm `01KZK2BC…` closed as superseded

---

## Completeness ledger

Computed, not assembled: every OPEN id comes from `observation_log_lint.parse` over the live
log, and group R's rows come from each entry's own "fix in review: PR #NNN" status. Checked with
`observation_log_lint.py <log> --packet <this file>` (see "Lint and ledger check").

| Group | Count | IDs |
|---|---:|---|
| R · #300 (A) | 5 | 2026-09-08-blocked-commit-reported-exit-zero · 2026-09-08-concurrent-session-branch-switch · 2026-09-10-agent-command-slips-this-session · 2026-09-13-own-timeout-read-as-failure · 2026-09-14-commit-during-test-run-stashed-the-tree-under-tests |
| R · #301 (B) | 2 | 2026-09-08-name-only-ignores-content-flags · 2026-09-08-shell-rewrite-crlf-on-tracked-hook |
| R · #302 (C) | 4 | 2026-09-08-workflow-disabled-state-is-invisible-to-the-repo · 2026-09-08-disabled-ci-let-a-checkout-breaking-defect-live-three-months · 2026-09-08-git-add-dash-A-swept-in-generated-metadata · 2026-09-17-worktree-scoped-hookspath-runs-main-checkout-hooks |
| R · #303 (D) | 6 | 2026-09-10-captured-pipes-deadlock-on-backgrounded-children · 2026-09-11-mutation-harness-stale-bytecode · 2026-09-13-basetemp-longpath · 2026-09-15-notation-guard-selftest-never-wired · 2026-09-17-hook-test-outside-ci-rotted-after-a-gate-was-added · 2026-09-23-codex-installer-recreates-the-dead-git-hooks-bug |
| R · #304 (G/I) | 2 | 2026-09-11-required-review-producer-is-quota-limited · 2026-09-17-merge-admission-cannot-see-a-clean-codex-review |
| R · #305 (F/I) | 9 | 2026-09-08-formatter-collateral-needs-a-semantics-proof · 2026-09-12-brief-role-vocabulary-vs-inherited-authority · 2026-09-14-brief-assumed-historical-records-fit-the-new-route · 2026-09-14-phase-brief-inherits-an-unscoped-action-list · 2026-09-14-handoff-cited-at-a-path-only-an-unmerged-pr-contains · 2026-09-14-review-fix-overwrote-a-concurrent-sessions-jira-record · 2026-09-15-spec-authority-column-divergence-filed-as-known-limit · 2026-09-17-closed-intent-enum-sized-to-one-subphase · 2026-09-18-design-probe-used-a-different-entry-point-than-the-public-path |
| R · #306 (H) | 4 | 2026-09-01-completeness-ledger-missed-six-live-items · 2026-09-08-single-repo-review-scope-orphans-other-repos-observations · 2026-09-08-reconciliation-stamped-a-borrowed-resolution · 2026-09-23-review-packet-never-reached-the-owner |
| R · #307 (I) | 3 | 2026-09-16-automated-review-rounds-plateau-in-count-not-kind · 2026-09-16-red-run-exit-code-shared-with-missing-pytest · 2026-09-17-bounded-action-table-expectation-duplicated |
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
| TDL residual | 1 | 2026-08-22-retired-procedure-kept-live-imperatives |
| **Total** | **55** | |

---

## Lint and ledger check

`observation_log_lint.py` over the log, before this review's edits: `181 observation(s): 51
OPEN`, no findings (no duplicate ids, no closing stamp without evidence, no identical borrowed
text). After the four new entries: `185 observation(s): 55 OPEN`, no findings. The `--packet`
check against this file is recorded in the PR description.

The tool is not on `main`. Both runs used `tools/observation_log_lint.py` taken from
`origin/pipe/observation-log-lint` (#306 head `f00970b8`), an unreviewed version (Campaign O).

## Skills pass

**Inventory.** 63 repo skills authored in `.agents/skills/` and mirrored to `.claude/skills/`.
`sync_agent_skills.py --check` passes: every mirror is `IDENTICAL`. The unmirrored set
(`apm-*`, `apm-communication`, `writing-skills-extras`, `SKILL-INDEX.md`) matches
`EXCLUDE_PATTERNS`. Also checked: the global `research-observer` and `task-observer`, and the
plugin skills in the session list.

**Cross-check of every OPEN group against every relevant skill:**
- J → `tda-resource-preflight`. Its trigger covers only research compute, so test packets
  never invoked it (staged edit, Campaign J). `tda-large-workflow-supervision`: #307's stopping
  rule lacks the cost carve-out (Campaign J, item 4). `tda-acceleration-benchmarking`: already
  cross-referenced from the preflight skill; no change.
- K → `tda-diagnosing-computational-defects`, `executing-plans-extras`: the lesson about
  environment versus test failures belongs in the runner (J), not in new skill prose.
- L → `tda-agent-safety-guardrails` says nothing about `.codex/hooks.json`. Add a line when L
  resolves; writing it before the Codex probe would repeat an unverified claim.
- N → `result-provenance-review` covers no-overwrite behaviour but not the hook's scope; the
  hook header is the right place (Campaign N).
- O → `research-observer` and `tda-skill-authoring-workbench` (dual-tree mechanics) bear on the
  option to track the observer skill in the repo.
- R → last week's skill edits (`using-git-worktrees-extras` on #299; `contract-first-tdd`,
  `research-assurance-triage` and `tda-large-workflow-supervision` on #307; the
  `tda-task-brief-from-plan` and `executing-plans-extras` edits on #305 and #300) are all
  unmerged. `main`'s copies predate them. Until they merge, sessions load the old guidance.
- Counting Lives and MathUni → their fixes belong in those trees (`anthropic-skills:chapter-session`
  is the likely home for the Counting Lives chapter-close checklist). Nothing was applied from
  here.

**Simplification sweep ("what can we remove?").** One candidate, now logged
(`2026-09-29-task-observer-still-triggers-beside-research-observer`, Campaign O). No other
skill's trigger overlaps an existing one closely enough to merge.

**Self-applied:** none. No SKILL-lane item was open without an owner decision behind it.

**Cross-cutting-principle compliance of the staged edit:** it follows Principle 10 (establish a
baseline before varying a cause: time one test alone before scale-out) and Principle 9 (a
budget is a gate that can fail). It also respects Principle 4's rule on WSL/background compute
(no `&`, `nohup` or `Start-Process` detachment).

## Gate-liveness spot check

I picked two gates nobody has recently watched fail.

1. **`merge-admission-sweep.yml`** has a positive signal (every run prints its verdict line) and
   logic-level negative controls (ten sweep tests in `tests/tools/test_merge_admission.py`). Its **cadence** is claimed and
   never measured, and the measurement contradicts the claim by about 40×: Campaign M,
   `2026-09-29-sweep-cron-runs-at-two-percent-of-its-stated-cadence`.
2. **`.claude/hooks/results-no-overwrite.sh`** has a positive signal (2,026 receipts) and
   **no negative control**: zero denies on record, no test, and #303 doesn't cover it. Campaign
   N, `2026-09-29-results-no-overwrite-never-watched-to-fail`.

Both are findings, not probes. No destructive probe was run.

Checked in passing, and healthy: the main checkout's `core.hooksPath` is the relative
`.githooks` at local scope, and this review's linked worktree resolves the same. No tracked hook
file has a CR byte on disk. Every tracked workflow's API state is `active`.

## Coverage question

"Did anything go wrong this week that no gate, contract or invariant caught?" Yes, six times.
Each is logged under the lane of the mechanism that should own it. None is a numerical or
statistical failure, so none is an invariant-battery item.

| What went wrong | Caught by | Observation |
|---|---|---|
| Test groups grew to hours and a packet to a day, disclosed in four PRs and never escalated | You, by hand (2026-09-26) | `2026-09-26-test-cost-normalised-as-a-known-limit` (J) |
| Eleven groups lost to an undiagnosable "Git inspection is unavailable" burst | Nothing; the cause is unrecoverable | `2026-09-26-git-unavailable-error-hides-its-cause` (K) |
| A harness restart killed a run and left no partial evidence | By hand | `2026-09-25-harness-background-runs-die-with-the-session` (J) |
| Codex runs months-old hook copies | By hand, during #303 | `2026-09-25-codex-live-hooks-are-stale-sibling-copies` (L) |
| The sweep ran at 2% of its stated cadence for 17 days | This review, by hand | `2026-09-29-sweep-cron-runs-at-two-percent-of-its-stated-cadence` (M) |
| The review's mandated lint was missing on `main` | This run, at step 2 | `2026-09-29-review-instructions-landed-before-their-tool-merged` (O) |

## This review's actions

1. Found the previous packet (PR #299), confirmed every campaign had been decided, and
   re-resolved each one against the live state of its PR: head, unresolved threads, blocker,
   and the owner actions still pending or done.
2. Ran the lint (from #306's branch) before and after this review's edits: clean both times.
3. Verified the 11 non-TDL residuals read-only against MathUni, Counting Lives and
   codex_workflow, and found that two of them are TDL `research_system` items (Campaign P).
4. Logged four observations: two GATE (spot check), one PROCESS (coverage), and one SKILL (the
   simplification candidate raised twice before without a log entry).
5. Staged one skill edit outside the repo (`~/.claude/skill-updates/2026-09-29/tda-resource-preflight/`),
   not applied.
6. Updated `last-review-date.txt` to `2026-09-29`.
7. Opened this packet as a pull request.
