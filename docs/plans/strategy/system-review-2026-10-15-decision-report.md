# Weekly Research-System Review — Resolution Packet

**Review date:** 2026-10-15. This review was due on Tuesday 2026-10-13. The scheduled run did not happen
(see Group B), so a side session started it by hand from a Gate 6 Phase 5 session.

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md`. After this review it
holds 226 entries, 26 of them OPEN (OPEN, ESCALATED or PARTIALLY, per the lint). One of the 26
was logged by a concurrent session while this packet was being written (Group I).

**Scope:** every OPEN observation in the shared log, across the five trees named by the 2026-09-25
and 2026-10-02 owner decisions: TDL, MathUni, the Counting Lives vault, codex_workflow and
zktheoryweb. The non-TDL trees were read only. Every OPEN item belongs to one of the five trees, so
there is no scope finding. MathUni and Counting Lives have no OPEN items.

**Decision owner:** Stephen

**Operating rule (unchanged since 2026-08-09):** approval authorizes a bounded verify-then-fix
campaign on a reviewed branch. It does not authorize direct changes to `main`, silent gate
weakening, or acceptance without the named controls.

**Phase 5 boundary.** A windowed certification runs in `C:/Users/steph/TDL-g6-p5` at 02:00 on
2026-10-16. This review did not touch that worktree, the `.codex/tmp/g6-p5` evidence folder or any
`TDL-ARS-*` root, and ran no heavy tests. Group C's runner work should start only after that
certification has produced its `results.json`.

**What this review changed.**
- **Record (observation log):**
  - **Closed six entries** whose own Progress notes named a PR and said "close when it merges".
    Each of those PRs is on `origin/main`, and each Status names its merge commit. Their decisions were
    made on the 2026-10-06 packet.
  - **Closed one duplicate**, as the log itself asked.
  - **Added dated Progress notes** to six entries.
  - **Logged six observations:** five from this review's evidence and the coverage question, and one
    SKILL item. All six are OPEN.
- **Staged, not applied:** one skill edit, `tda-resource-preflight` 1.2.0 (Group G).
- **Not changed:** anything on the GATE, INVARIANT or PROCESS lanes, any repo file other than this
  packet, and anything in the other trees. Everything below is a recommendation.

## Where last week's packet stands

The 2026-10-06 packet (PR [#332](https://github.com/ZK-Theory/TDL/pull/332), 15 OPEN in nine
groups) was decided the same day. Its campaigns were built and merged on 2026-10-06 and 2026-10-07:

| Group | PRs | Merge commits | State now |
|---|---|---|---|
| A. Stranded work | [#334](https://github.com/ZK-Theory/TDL/pull/334), [#335](https://github.com/ZK-Theory/TDL/pull/335), [#336](https://github.com/ZK-Theory/TDL/pull/336), [#342](https://github.com/ZK-Theory/TDL/pull/342) | `eba3fe69`, `ae79bcf5`, `e5ed3f45`, `06d36821` | stranded-work entry closed; the two residual limbs carry forward (Group H) |
| B. Suite lanes | [#329](https://github.com/ZK-Theory/TDL/pull/329), [#337](https://github.com/ZK-Theory/TDL/pull/337), [#344](https://github.com/ZK-Theory/TDL/pull/344) | `252ca9a9`, `266e96d7`, `9f49af60` | pin entry closed; **the lane is red 9 of 9 nights and not required** (Group A) |
| C. Triage fixes | [#325](https://github.com/ZK-Theory/TDL/pull/325), [#328](https://github.com/ZK-Theory/TDL/pull/328), [#338](https://github.com/ZK-Theory/TDL/pull/338), [#341](https://github.com/ZK-Theory/TDL/pull/341) | `ddf1da77`, `2b7facb0`, `e5179b57`, `d4d5aa00` | both entries closed |
| D. `identity.py` race | [#333](https://github.com/ZK-Theory/TDL/pull/333), [#340](https://github.com/ZK-Theory/TDL/pull/340) | `8d6a5dd8`, `c0d31c34` | closed |
| E. Branch-set mergeability | [#340](https://github.com/ZK-Theory/TDL/pull/340) | `c0d31c34` | closed (the edit only; the tool was not built) |
| F. Codex hook parity | — | — | DEFERRED by you on 2026-10-06 (Codex no longer in use) |
| G. Two record closures | — | — | both closed before this review |
| zktheoryweb | — | — | unchanged (Non-TDL section) |
| codex_workflow | — | — | unchanged (Non-TDL section) |

**One thing went wrong in the record.** Every PR above merged on 2026-10-06 or 2026-10-07. Yet seven
entries whose Progress notes said "close when #N merges" were still OPEN on 2026-10-15. One also
still called #342 "open". The review closed six of them on their recorded conditions and kept the
seventh open, because its condition (the lane becomes required) is not met. This is the third time
the record and the fix have diverged, and Group B proposes the mechanical fix.

The six closures, each checked with `git merge-base --is-ancestor <commit> origin/main`:

| Entry | Its recorded close condition | Evidence |
|---|---|---|
| `2026-10-03-tests-and-live-store-bound-to-machine-state` | #341 merges | `d4d5aa00` |
| `2026-10-03-tamper-tests-pinned-to-check-order` | #338 merges | `e5179b57` |
| `2026-10-05-parked-fix-branches-drift-out-of-mergeability` | #340 merges | `c0d31c34`; skill at 1.5.0 |
| `2026-10-06-race-fix-verified-with-three-runs-flakes-one-in-five` | #333 and #340 merge | `8d6a5dd8`, `c0d31c34` |
| `2026-10-06-owner-decided-work-stranded-on-local-branches` | #334, #336 merge; #335 decided | `eba3fe69`, `e5ed3f45`; P-060 in `06d36821` |
| `2026-10-06-review-skill-edit-broke-a-pack-pinned-skill` | #337 merges | `266e96d7`; Gate 0 printed `pack pins: 12 checked, 0 drifted` |

The duplicate: `2026-10-07-fresh-store-premise-never-run-through-the-genuine-cli` is DECLINED as a
duplicate of `2026-10-07-every-spec-test-monkeypatched-the-foundation-seam`. The 2026-10-07
scratch-spec entry asked for that merge, and both log finding B-1 of the 4c boundary review.

If you disagree with any closure, tick "reopen" in the Decision summary and I will restore its
OPEN status. The pre-review log is at `~/.claude/skill-updates/2026-10-15/log/log.md.before`.

## How to use this packet

Tick one box per group. An approved group first re-resolves each mapped observation against current
HEAD. If an observation is already compliant or superseded, record the evidence and close it. If it
is still valid, build the named mechanism with its negative control. If another tree or process
owns it, record the owner and keep only that remainder open.

## Decision summary

| Group | OPEN | Recommended resolution | Decision |
|---|---:|---|---|
| A. The nightly suite lane: red 9 of 9 nights, unseen (new) | 4 | Make the three local-only commits fetchable; triage S-014; add a contract reachability check; keep the lane advisory until 3 green nights | `[ ]` approve 1–4 · `[ ]` 1–2 only · `[ ]` defer |
| B. Signals that never reached you (new) | 3 | Findings inbox for failing scheduled runs; a review-staleness line at session start; lint the "close when #N merges" conditions | `[ ]` approve 1–3 · `[ ]` 3 only · `[ ]` defer |
| C. The Gate 6 certification runner as committed infrastructure | 7 | One committed `tools/` runner with five record contracts, after Phase 5's certification | `[ ]` approve · `[ ]` approve, after Gate 6 closes · `[ ]` defer |
| D. Fresh-store seam: confirm closure | 2 | Close both on #348 and #351; the CI portability failure moves to Group A | `[ ]` close both · `[ ]` keep open |
| E. CI glue controls | 2 | `per_page=100` with an unordered-runs test; a shared bash-step harness | `[ ]` approve both · `[ ]` watchdog only · `[ ]` defer |
| F. Primary-checkout git guard | 1 | Extend `commit_state_guard` to refuse HEAD moves in the primary checkout | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| G. Long-run launch path | 2 | Apply the staged `tda-resource-preflight` 1.2.0; close the scheduled-run entry on it | `[ ]` approve · `[ ]` defer |
| H. Two residual plan limbs | 2 | Defer both to Gate 7 intake under P-060 | `[ ]` defer both · `[ ]` build now · `[ ]` decline both |
| I. Amended decision's headline property unmechanized (new, concurrent) | 1 | Route the code gap to the Phase 5 session; add a `contract-first-tdd` checklist line | `[ ]` approve both · `[ ]` route only · `[ ]` defer |
| Non-TDL: zktheoryweb | 1 | Unchanged from last week: make the Zotero refresh opt-in | `[ ]` route to a zktheoryweb session · `[ ]` defer |
| Non-TDL: codex_workflow | 1 | Unchanged; kept open by your 2026-10-02 decision | `[ ]` keep open · `[ ]` decline |
| This review's seven closures | — | Keep them closed | `[ ]` keep · `[ ]` reopen (name which) |

Total: 4 + 3 + 7 + 2 + 2 + 1 + 2 + 2 + 1 + 1 + 1 = **26**.

---

## A — The nightly suite lane: red 9 of 9 nights, unseen (4)

**Defect.** #329 added `research-system-suite.yml` so that "a red full suite [is] a recorded state …
visible the day it lands". It runs, and it is red:

| Nightly (UTC) | SHA | Shards failing | Failures outside the baseline |
|---|---|---|---|
| 2026-10-07 | `9f49af60` | 3, 5, 6, 7, 8 | 135 |
| 2026-10-08 to 2026-10-14 (7 runs) | `bbdcb068` | 3, 5, 6, 7, 8 | 137–138 |
| 2026-10-15 (run 38690057772) | `bbdcb068` | 2, 3, 5, 6, 7, 8 | 138 |

The lane has never passed on a schedule. #348 to #354 merged during those nights with the advisory
lane red. A one-time follow-up task diagnosed it on 2026-10-12, but its report stayed in its session
(Group B). The families:

| Family | Tests | Cause | Entry |
|---|---:|---|---|
| S-014 physical preflight | ~121 | `release_tranche.py:570`: five predicates fail together on the hosted runner and pass locally. Undiagnosed. | `2026-10-15-s014-preflight-fails-on-every-ci-runner` (new) |
| Git objects CI cannot fetch | 12 | Accepted contracts pin `b1863e33`, `e7c30ef7` and `fe0b8bae`, which sit only on your local branches `codex/review-wp61-stage2-r10`, `review/ars-wp6-2-threshold-protocol-r1` and `review/ars-wp6-3-tda-pack-r1` | `2026-10-15-accepted-contracts-pin-commits-on-local-only-branches` (new) |
| Windows permissions | 2 | `test_store.py` expects a `PermissionError` the runner never raises | carried under the full-suite entry |
| Fresh-store test portability | 2 | `test_fresh_store_public_procedure.py`: "a branch named 'main' already exists" in the runner's clone | carried under the full-suite entry |
| Intermittent | 1 | writer-lock conflict, once | carried under the full-suite entry |

The two carried entries, `2026-10-02-full-suite-red-on-main-unseen` and
`2026-10-03-shared-seam-change-merged-without-its-dependents`, both close "when the lane is required".
The PR-time selection half works: it caught #338's helper-signature break on its first day.

**Read this before any branch sweep.** Those three local branches are now load-bearing. A prune
followed by `git gc` would make three owner-acceptance records unverifiable on every machine,
including this one. #336's reachability check flags the three commits as stranded (this review's
lint, exit 1). That is a true positive, not a lint fault, and it is the first time that check has
fired on live data.

**Proposed action.**
1. **Owner decision:** make the three objects fetchable. Tags on the remote work, because a
   full-history checkout fetches tags. A pushed archive branch also works. Either publishes refs,
   which is your call.
2. Diagnose S-014 on the runner. A `workflow_dispatch` run can print the preflight's inputs. Then
   make the fixtures self-contained, or mark the family `live_store` with a recorded reason.
3. Add a contract test, or a Gate 0 extension beside #337's pin check, that resolves every commit
   pinned under `.research-system/` and fails when one is not on a remote-tracking ref or tag.
4. Fix the three small families: a runner-aware denial for `test_store.py` and a clone fixture that
   does not assume `main` is free. Keep the lane advisory until three consecutive green nights. Then
   make it required (a ruleset edit), and add the `ci.yml` schedule watch the 2026-10-12 run judged
   ready.

**Controls.**
- (2) The diagnosis names the missing input, and the fixed test fails when that input is withdrawn.
- (3) A fixture contract pinning a local-only commit is refused, and one pinning a commit on
  `origin/main` passes.
- (4) The lane's own baseline controls from #329 are unchanged. The baseline list may only shrink.

**Recommended decision:** approve 1–4. Item 1 is the cheapest and removes a real durability risk.

**Decision:** `[ ]` approve 1–4 · `[ ]` approve 1–2 only · `[ ]` defer

---

## B — Signals that never reached you (3, new)

**Defect.** Three ways this fortnight's findings failed to reach a surface you read:
- `2026-10-15-report-only-run-findings-never-reached-the-log`. The 2026-10-12 one-time task
  `research-system-lane-required-followup` diagnosed Group A completely. It then wrote "I didn't
  write [the two observations] because this run is report-only". Logging is not acting, and the
  observer protocol permits it.
- `2026-10-15-weekly-review-missed-its-run-without-signal`. `weekly-system-review` has no run for
  Tuesday 2026-10-13. Its `lastRunAt` reads 2026-10-15T07:06Z with no session in its run list. A Gate
  6 session noticed the stale `last-review-date.txt` through the CLAUDE.md instruction, and deferred
  it.
- `2026-10-15-close-conditions-met-but-entries-left-open`. The six closures above: "close when #N
  merges" notes have no reader present at the merge.

**Proposed action.**
1. A failing scheduled run of an advisory lane opens or updates one GitHub issue that a green run
   closes. Add one line to every scheduled-task prompt: new findings are appended to the log even in
   report-only runs.
2. A SessionStart line beside `hook_currency.py` prints the review date, and warns when it is more
   than 8 days old.
3. `observation_log_lint.py --reachability` reports OPEN entries whose "close when #N merges"
   condition is met, using `gh pr view`.

**Controls.**
- (1) A forced failing `workflow_dispatch` opens the issue, and a green run closes it.
- (2) A fixture date 9 days old warns, and one 2 days old does not.
- (3) A fixture entry naming a merged PR is reported, and one naming an open PR is not.

**Recommended decision:** approve 1–3. Item 3 is small and would have produced this review's
closures as a list.

**Decision:** `[ ]` approve 1–3 · `[ ]` approve 3 only · `[ ]` defer

---

## C — The Gate 6 certification runner as committed infrastructure (7)

**Defect.** Every Gate 6 sub-phase certifies with a session-local runner: `certify_4b2b_v2.py`,
then `certify_prep.py` and `prep_controls.py` in `.codex/tmp/` scratch. Each defect below was found
in a run and fixed in that run's copy only:

| Entry | Defect | Fixed in the scratch copy? |
|---|---|---|
| `2026-10-06-certification-runner-lives-in-a-dead-session-scratchpad` | Each sub-phase rebuilds or hunts for the runner | — |
| `2026-10-07-certification-selection-narrower-than-ci-missed-pr-regressions` | 45 hand-picked nodes missed all seven tests #349 broke | no |
| `2026-10-07-resumable-control-records-keyed-without-the-sha` | A re-run at a new head returned the old head's records as holding | yes |
| `2026-10-08-mutation-control-held-on-an-environment-failure` | A Git timeout counted as "control holds" | yes |
| `2026-10-15-runner-recorded-interrupted-groups-as-results` | Ctrl-C wrote eight result files that the resume then trusted | no |
| `2026-10-07-mutation-control-exposed-a-clause-no-admissible-input-reaches` | "Control did not fire" was nearly a closing state | procedure only |
| `2026-10-15-handoff-one-worktree-conflicts-with-clean-sha-runner` | Cleanliness is checked only at the unattended 02:00 start | no |

Today's `2026-10-15-runner-recorded-interrupted-groups-as-results` affects the Phase 5 prep packet
`results.json` directly. Its eight interrupted groups need re-running before that file is relied
on.

**Proposed action.** After the 2026-10-16 certification has produced its `results.json`, promote one
runner to `tools/certify_packet.py`. It takes a group spec and writes resumable per-group JUnit and
results, with five record contracts, each with its own control:
1. Selection is a superset of every node in touched test files, every test file importing a changed
   module, and the architecture tests of changed packages, derived from `git diff --name-only`.
2. Records are keyed by SHA, selection hash and mutation text, and reuse is refused on any
   mismatch.
3. An interrupted group (exit 2, or a log ending in `KeyboardInterrupt`) leaves no result.
4. A control holds only on its recorded expected failure, and an environment failure is
   inconclusive. A non-firing control must be dispositioned as redundant or missing a test.
5. Cleanliness and HEAD are checked at launch as well as at window start.

Also add one line to the Gate 6 handoff template: a frozen run worktree and a separate docs
location.

**Controls.**
- (1) A collect file omitting one node of a touched test file is refused.
- (2) An invocation with a new SHA while an old record exists executes instead of resuming.
- (3) Interrupt a group mid-run, resume it, and it re-runs.
- (4) An injected environment error reports "inconclusive".
- (5) A dirty tree fails at launch.

**Recommended decision:** approve, starting after the Phase 5 certification. No change to the
runner the 02:00 window uses.

**Decision:** `[ ]` approve (after the 2026-10-16 certification) · `[ ]` approve, but only after Gate 6
closes · `[ ]` defer

---

## D — Fresh-store seam: confirm closure (2)

**Evidence.** `tests/research_system/integration/test_fresh_store_public_procedure.py` (#348,
`e0bf729b`) runs the genuine `ars` CLI from a non-linked scratch clone through reserve, re-pin,
init, first binding and spec status. It patches no foundation, binding or seeding seam, and its
docstring names both entries as its subject:
- `2026-10-07-every-spec-test-monkeypatched-the-foundation-seam`;
- `2026-10-07-scratch-spec-stores-bound-by-hand-written-fixtures`.

Grant activation through the public CLI landed in #351 (`968746ce`), and #354 records Phase 5 prep
construction as complete. The one gap is portability: two of that file's tests fail on the CI runner
(Group A, item 4).

**Proposed action.** Close both as ACTIONED on #348 and #351. Their CI portability goes to Group A.

**Recommended decision:** close both.

**Decision:** `[ ]` close both · `[ ]` keep open

---

## E — CI glue controls (2)

- `2026-10-07-watchdog-liveness-reads-one-unordered-run`. Unchanged: `ci.yml:222` still fetches
  `per_page=1`. It has produced five false failures, one of them on `main`. On 2026-10-07 you
  deferred the fix to this review.
- `2026-10-06-workflow-step-tested-by-string-not-by-running`. `238fd54d` fixed the instance. The
  shared harness is not built, and a private `_bash()` helper now appears in ten `tests/tools` files.

**Proposed action.**
1. Change the fetch to `per_page=100`. Add a unit test where the newest run is not first, a negative
   control where a payload of only the stale run still fails, and a policy test that the liveness
   fetch never uses `per_page=1`.
2. Add one `tests/tools` helper that extracts a workflow step and runs it under GitHub's
   `bash --noprofile --norc -eo pipefail` with the tools stubbed. Use it for every step that
   branches on exit codes.

**Controls.**
- (1) As stated in item 1.
- (2) The pre-`238fd54d` step script, run through the helper, fails the way CodeRabbit described.

**Recommended decision:** approve both. `ci.yml` is a code-owned gate file, so item 1 is your
review.

**Decision:** `[ ]` approve both · `[ ]` watchdog only · `[ ]` defer

---

## F — Primary-checkout git guard (1)

`2026-10-06-read-command-carried-a-checkout-into-the-primary-checkout`, unchanged.
`commit_state_guard.py` already tracks HEAD moves (`BRANCH_MOVERS`), but it refuses only commits. A
detach in `C:\Users\steph\TDL` is still allowed.

**Proposed action.** In the same hook, refuse a HEAD-moving `checkout`/`switch`/`reset`/`rebase`
whose repository is the primary checkout, unless an explicit override is given.

**Control.** A detach attempt against a scratch clone configured as "primary" is refused. The same
command in a linked worktree is allowed.

**Recommended decision:** approve.

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## G — Long-run launch path (2)

- `2026-10-07-scheduled-run-cannot-use-the-terminal-tab-it-prescribes`. The memory index now records
  the 110-minute WMI detach. No scheduled prompt template exists to change.
- `2026-10-15-preflight-skill-contradicts-the-wmi-detach-evidence` (new, SKILL).
  `tda-resource-preflight` item 4 still says WMI-launched children "died within seconds".

**Proposed action.** Apply the staged `tda-resource-preflight` 1.2.0. The files are
`~/.claude/skill-updates/2026-10-15/tda-resource-preflight/proposed.diff` (60 lines), with its
`SKILL.md.base`, which is byte-identical to `main`. It does three things:
- it records both WMI outcomes and requires a status file for any detached run;
- it adds item 5, the runner record contracts from Group C, as skill text;
- it adds one checklist line.

Then close both entries.

The skill is not pack-pinned: `git grep "tda-resource-preflight/SKILL.md" .research-system/` finds
nothing. Apply it on a branch, mirrored to `.claude/skills`.

**Control.** `sync_agent_skills.py --check` reports the skill IDENTICAL and pack pins unchanged.

**Recommended decision:** approve.

**Decision:** `[ ]` approve · `[ ]` defer

---

## H — Two residual plan limbs (2)

- `2026-08-12-file-map-frozen-since-wp1`. Limb 2 is now owned by P-060 (#342, `06d36821`) and waits
  for Gate 6 to close. Limb 1, a plan file-map amendment on supersession, has never been started.
- `2026-08-22-retired-procedure-kept-live-imperatives`. The gate limb merged in #334 (`eba3fe69`). The
  enumerable-contract limb has never been started. It asks that exact registries, configurations and
  discriminated results enumerate their members, required and prohibited fields, and completeness
  negatives before an implementation slice opens.

Both are planning-review rules for future plans, not defects in a live artefact. They have carried
for eight weeks.

**Proposed action.** Mark both DEFERRED to Gate 7+ intake, with the planning-template work, citing
P-060 for limb 2. DEFERRED drops them out of the weekly ledger without claiming a fix.

**Recommended decision:** defer both.

**Decision:** `[ ]` defer both to Gate 7+ intake · `[ ]` build now · `[ ]` decline both

---

## I — An amended decision's headline property shipped unmechanized (1, new)

`2026-10-15-amended-decision-property-left-unmechanized` was logged by a concurrent session (the
fresh-context delta review of `e5179b57..100730e0`) while this packet was being written. This review
did not re-verify it.

**Defect.** P5-7 was amended to "one Task spans SOURCE to closure". The construction mechanized the
amendment's listed refusals, but not its headline property. Nothing in
`research_system/discovery/spec_source.py::verify_source_production` requires the SOURCE Task to name
the Candidate the observation derives. So a separate SOURCE Task is still admitted, which the entry
reproduced with a temporary test.

**Proposed action.**
1. Route the code gap to the Phase 5 session as a delta-assurance finding under P-058. The fix
   refuses unless the Candidate is in the Task's `portfolio_refs`, with a negative control built from
   the reproduction. Whether it blocks the 2026-10-16 bounded live run is that session's call and
   yours.
2. Add one `contract-first-tdd` checklist line: each headline sentence of the governing decision has a
   negative control, not only its enumerated refusals. The skill is not pack-pinned.

**Control.** (1) The entry's decoy-source reproduction becomes a committed test that is refused after
the fix and admitted at `100730e0`.

**Recommended decision:** approve both.

**Decision:** `[ ]` approve both · `[ ]` route the code gap only · `[ ]` defer

---

## Non-TDL: zktheoryweb (1) — read-only verification

`2026-10-05-build-mutates-tracked-zotero-cache`. Re-verified on 2026-10-15: `astro.config.mjs` still
calls `fetchZoteroLibrary()` in `astro:build:start` with no flag, and `origin/main` (`1cb805b`) has
no change since last week. Last week's proposal stands: make the refresh opt-in with
`ZOTERO_REFRESH=1` or `NETLIFY=true`, and add a build-guards test that the cache bytes are unchanged
without the flag.

**Decision:** `[ ]` route to a zktheoryweb session as proposed · `[ ]` defer

## Non-TDL: codex_workflow (1) — read-only verification

`01M044JXYSPP0VXH15TEZVCNA3`. Re-verified on 2026-10-15: the installed copy is still `1.1.2` and not
a git repo, and `end_of_session.md` still runs closure "once after every substantive Medium or
Heavy" deployment. No change.

**Decision:** `[ ]` keep open (as decided) · `[ ]` decline

---

## Completeness ledger

Computed, not assembled. Every OPEN id comes from `observation_log_lint.parse` over the live log
after this review's edits, and the table is checked with
`tools/observation_log_lint.py <log> --packet <this file>`.

| Group | Count | IDs |
|---|---:|---|
| A | 4 | 2026-10-02-full-suite-red-on-main-unseen · 2026-10-03-shared-seam-change-merged-without-its-dependents · 2026-10-15-accepted-contracts-pin-commits-on-local-only-branches · 2026-10-15-s014-preflight-fails-on-every-ci-runner |
| B | 3 | 2026-10-15-report-only-run-findings-never-reached-the-log · 2026-10-15-weekly-review-missed-its-run-without-signal · 2026-10-15-close-conditions-met-but-entries-left-open |
| C | 7 | 2026-10-06-certification-runner-lives-in-a-dead-session-scratchpad · 2026-10-07-certification-selection-narrower-than-ci-missed-pr-regressions · 2026-10-07-resumable-control-records-keyed-without-the-sha · 2026-10-08-mutation-control-held-on-an-environment-failure · 2026-10-15-runner-recorded-interrupted-groups-as-results · 2026-10-07-mutation-control-exposed-a-clause-no-admissible-input-reaches · 2026-10-15-handoff-one-worktree-conflicts-with-clean-sha-runner |
| D | 2 | 2026-10-07-every-spec-test-monkeypatched-the-foundation-seam · 2026-10-07-scratch-spec-stores-bound-by-hand-written-fixtures |
| E | 2 | 2026-10-07-watchdog-liveness-reads-one-unordered-run · 2026-10-06-workflow-step-tested-by-string-not-by-running |
| F | 1 | 2026-10-06-read-command-carried-a-checkout-into-the-primary-checkout |
| G | 2 | 2026-10-07-scheduled-run-cannot-use-the-terminal-tab-it-prescribes · 2026-10-15-preflight-skill-contradicts-the-wmi-detach-evidence |
| H | 2 | 2026-08-12-file-map-frozen-since-wp1 · 2026-08-22-retired-procedure-kept-live-imperatives |
| I | 1 | 2026-10-15-amended-decision-property-left-unmechanized |
| Non-TDL: zktheoryweb | 1 | 2026-10-05-build-mutates-tracked-zotero-cache |
| Non-TDL: codex_workflow | 1 | 01M044JXYSPP0VXH15TEZVCNA3 |
| **Total** | **26** | |

---

## Lint and ledger check

| When | Tool | Result |
|---|---|---|
| Before this review's edits | `observation_log_lint.py --reachability .` at `100730e0` (= `origin/main`) | `219 observation(s): 26 OPEN`; reachability 27 hashes, 0 stranded; exit 0 |
| After the edits | same | `225 observation(s): 25 OPEN`, then `226 … 26 OPEN` after a concurrent append; reachability 33 hashes, **3 stranded** (`b1863e33`, `e7c30ef7`, `fe0b8bae`); exit 1 |
| After the edits, `--packet` on this file | `observation_log_lint.py <log> --packet <this file>` | see the PR's test plan |

The three stranded hashes are the subject of the new Group A entry. They are not a record error, so
they stay cited and flagged until item 1 makes them reachable.

The edit was made by a script that refused to write unless five checks held:
- the log matched its backup's SHA-256;
- the id order was unchanged, with the six new entries appended at the end;
- the OPEN set changed by exactly the seven closures and six additions;
- every untouched entry was byte-identical apart from trailing whitespace;
- the lint's non-reachability checks came back clean.

## Skills pass

**Inventory.**
- `sync_agent_skills.py --check` reports every synced skill IDENTICAL, and `pack pins: 12 checked, 0
  drifted`.
- Last week's four staged edits are all applied: `contract-first-tdd` 1.3.0,
  `tda-large-workflow-supervision` 1.5.0 and `tda-skill-authoring-workbench` 1.1.0 via #340, and the
  global `research-observer` pin row. The 2026-10-06 staging folder is consumed.
- The Counting Lives legacy observation store now carries `CANONICAL-ROOT.txt`, as last week
  recommended.
- `~/.Codex/skill-observations/last-review-date.txt` still reads 2026-08-06. It is historical and
  pending archival, as before.

**Cross-check of every OPEN group against the skills:**
- **A:** `tda-skill-authoring-workbench` and Gate 0 now check skill pins. Nothing checks commit pins,
  so the proposal is mechanical (A3), not skill text.
- **B:** the global `research-observer` already says to log silently and immediately. The 2026-10-12
  run read "report-only" as a ban on logging. Rather than more skill text, B1 puts a line in the
  scheduled prompts, which are where that run's instructions came from.
- **C:** `tda-resource-preflight` item 4 describes the runner, but none of the five record
  contracts. Staged as item 5 (Group G), as text until C builds the mechanism.
- **D:** no skill change.
- **E:** `contract-first-tdd` covers negative controls in general, so the CI-glue rule belongs in a
  test helper, not in prose.
- **F:** `tda-agent-safety-guardrails` covers git rules. Its text is not the gap: the slip was not a
  decision, so only the hook helps.
- **G:** `tda-resource-preflight` contradicts newer evidence. Staged.
- **H:** `writing-plans-extras` is the natural home for the two planning rules if you choose "build
  now".
- **I:** `contract-first-tdd` asks for negative controls per refusal, but not per headline
  invariant. A checklist line is proposed (I2). It is not staged, because the entry arrived after
  the staging pass.

**Simplification sweep ("what can we remove?").**
- The two one-time scheduled tasks `pr333-heavy-regression` and
  `research-system-lane-required-followup` are disabled and finished. They can be deleted.
- The `anthropic-skills:task-observer` plugin listing is still a third observer entry, unchanged and
  not editable from here.
- The `_bash()` helper is duplicated across ten `tests/tools` files (Group E, item 2 removes nine).

**Self-applied:** nothing. The one SKILL item is staged, because the repo skill needs a branch and
mirror.

## Gate-liveness spot check

1. **Gate 0's pack-pin check (#337), first watched since its merge.**
   - Positive signal: `pack pins: 12 checked, 0 drifted` in this review's `--check` run.
   - Negative controls: `test_an_edit_to_a_pinned_skill_fails_and_names_the_pin` and
     `test_a_pin_whose_skill_is_missing_fails` in `tests/tools/test_sync_agent_skills.py`.
   - It is wired at `.githooks/pre-commit:295`, and `install-git-hooks.py` confirms the active hook
     directory.

   Healthy. (`install-git-hooks.py` also warned that this worktree's `config.worktree` points hooks
   at the main checkout. That is known and archived, and the main checkout is level with
   `origin/main`, so this packet's commit ran current hook bytes.)
2. **The `research-system-suite` nightly lane (#329).**
   - It fires daily: the positive execution signal exists, about 6 hours after its 01:30 cron.
   - Its baseline controls work: each failing shard fails at the "Hold the shard to the
     known-failures baseline" step, naming each new failure.
   - But its verdict has been red for 9 of 9 nights, and no surface carried that to anyone.

   The gate is alive. Its watcher is missing (Groups A and B).

Also seen firing: #336's reachability check, on the three local-only commits (Group A). That is its
first watched true positive on live data.

No destructive probe was run.

## Coverage question

"Did anything go wrong this week that no gate, contract or invariant caught?" Yes:

| What went wrong | Caught by | Observation |
|---|---|---|
| Accepted contracts pin commits only on local branches | the nightly lane, but nobody read it | `2026-10-15-accepted-contracts-pin-commits-on-local-only-branches` (A) |
| 121 tests fail on every clean runner | the nightly lane, but nobody read it | `2026-10-15-s014-preflight-fails-on-every-ci-runner` (A) |
| A diagnosis of both stayed in a session transcript | this review, by reading the transcript | `2026-10-15-report-only-run-findings-never-reached-the-log` (B) |
| The weekly review skipped a week | a CLAUDE.md read in another session | `2026-10-15-weekly-review-missed-its-run-without-signal` (B) |
| Six entries stayed open after their PRs merged | this review, by hand | `2026-10-15-close-conditions-met-but-entries-left-open` (B) |
| Interrupted groups recorded as results | the Phase 5 session, by hand | `2026-10-15-runner-recorded-interrupted-groups-as-results` (C) |

None is a numerical or statistical failure, so none is an invariant-battery item.

## This review's actions

1. Found the previous packet (#332) and re-resolved its nine groups against `origin/main`
   (`100730e0`). Every campaign PR is merged.
2. Ran `git fetch origin` and the lint with `--reachability`, before and after the edits.
3. Read nightly runs 37587028766, 37744738018 and 38690057772, and the 2026-10-12 follow-up
   session's report.
4. Verified the non-TDL items read-only: zktheoryweb's build hook and `origin/main`, the
   codex_workflow installed copy, and the Counting Lives store marker.
5. Closed seven entries (six on their recorded conditions, one duplicate), added six Progress
   notes and logged six observations, through the checked script. Backup:
   `~/.claude/skill-updates/2026-10-15/log/log.md.before`.
6. Staged one skill edit (`tda-resource-preflight` 1.2.0).
7. Updated `last-review-date.txt` to `2026-10-15`.
8. Opened this packet as a PR.

---

## Outcome (2026-10-17)

On 2026-10-15 you approved every group and asked for the gate, invariant and process items to be resolved
too. The campaign ran on 2026-10-15 to 2026-10-17. Every PR below is merged unless marked.

| Group | Resolution | PRs (merge commit) |
|---|---|---|
| A | Five pinned review commits published as `pin/*` tags; the pinned-commit check runs in admission-controls; the S-014 root cause (an 8.3 short-name TEMP on the hosted runner) is fixed | #357 (`78324490`), #358 (`6a25b362`) |
| B | The nightly-verdict issue (it opened #367 on the first red night); the review-staleness line at session start; `--close-conditions` in the lint | #359 (`0f8be24f`), #360 (`335b7eeb`), #357 |
| C | `tools/certify_packet.py` with its five record contracts | #362 (`6f6227f7`), #364 (`0f037415`) |
| D | Both fresh-store entries closed on #348 and #351 | — |
| E | Watchdog reads a 7-day window; the shared workflow-step harness | #359 |
| F | The primary-checkout guard, then scoped to this project's checkout (review F1/F3) | #360, #373 (`12453e72`) |
| G | `tda-resource-preflight` 1.2.0, `tda-handoff` 1.4.0 | #361 (`dae9f197`) |
| H | Both residual limbs deferred to Gate 7+ intake | — |
| I | Routed to the Phase 5 session; `contract-first-tdd` 1.4.0 checklist line | #361 |
| zktheoryweb | The Zotero refresh is opt-in | zktheoryweb #23, **open** |
| codex_workflow | Deferred: Codex is no longer in use | — |

Follow-ups found during the campaign:
- Squash-merged PR commits now count as delivered: #371 (`01e50428`).
- The guard's scope: #373.
- The CI-parity fixture and the live-step rules: #374 (`bfb38d25`).
- Two publish-refusal tests had passed on the live store's breakage. They now pin their own foundation: #372 (`1dc06d54`), from another session. My duplicate #369 was closed.
- Deterministic test citations: #370 (`9987a39c`).

**Declined on evidence:** narrowing the affected-tests pin clause. On the L5 diff the narrowed rule selected 90
files, the same as the current rule (93 with helper propagation). The over-selection came from a hub code change, not
the pin clause. `--partial-reason` remains the remedy for owner-accepted narrower scopes.

**Nightly lane:**

| Night | Failures outside the baseline |
|---|---:|
| 2026-10-15 | 138 |
| 2026-10-16 | 2 |
| 2026-10-17 | 2, the two tests #372 fixed; that run predates the merge |

Dispatch run 39044280842 checks merged `main`.

**Observation log:** 6 OPEN, down from 34 at the 2026-10-17 restart. 44 closed entries were archived to
`archive/log-2026-10-17.md`. The lint reports 0 stranded commits and no unmet close conditions. Still open:

| Entry | Waiting on |
|---|---|
| `2026-10-02-full-suite-red-on-main-unseen`, `2026-10-03-shared-seam-change-merged-without-its-dependents` | three green scheduled nights, then your ruleset edit making the lane required |
| `2026-10-05-build-mutates-tracked-zotero-cache` | zktheoryweb #23 |
| `2026-10-15-amended-decision-property-left-unmechanized` | the Phase 5 session; `spec_source.py` is unchanged on `main` |
| `2026-10-17-cli-tests-read-the-committed-foundation-unpinned` | a decision on an autouse sentinel that refuses an unpinned canonical foundation |
| `2026-10-17-merge-admission-waiver-has-no-mechanism` | a decision on a head-scoped owner waiver for thread-finality; it loosens a required gate |
