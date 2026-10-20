# Weekly Research-System Review — Resolution Packet

**Review date:** 2026-10-20. The scheduled `weekly-system-review` task ran on time (Tuesday, 07:43Z), so last week's
missed run did not recur.

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md`. After this review it holds 242 entries, 7 of
them OPEN (OPEN, ESCALATED or PARTIALLY, per the lint).

**Scope:** every OPEN observation in the shared log, across the five trees named by the 2026-09-25 and 2026-10-02 owner
decisions: TDL, MathUni, the Counting Lives vault, codex_workflow and zktheoryweb. The other trees were read only. All 7
OPEN entries belong to TDL, so there is no scope finding. zktheoryweb's one entry closed this review (its PR merged).
MathUni and Counting Lives have no entries, and neither has an observation file newer than the last review.
codex_workflow's entry is DEFERRED.

**Decision owner:** Stephen

**Operating rule (unchanged since 2026-08-09):** approval authorizes a bounded verify-then-fix campaign on a reviewed
branch. It does not authorize direct changes to `main`, silent gate weakening, or acceptance without the named
controls.

**What this review changed.**
- **Record (observation log):**
  - **Closed two entries** whose close conditions were met. Each Status names the merge commit. See "This review's
    closures".
  - **Added dated Progress notes** to five entries.
  - **Logged four observations.** Three are OPEN. The fourth, a SKILL item, was applied and closed in the same edit.
- **Skill (applied):** the global `research-observer` skill (step 1 of the System Review), three edits. See "Skills
  pass".
- **Not changed:** anything on the GATE, INVARIANT or PROCESS lanes. No repo file changed except this packet, and
  nothing in the other trees. Everything below is a recommendation.

The pre-review log is at `~/.claude/skill-updates/2026-10-20/log/log.md.before`. The skill's previous text is at
`~/.claude/skill-updates/2026-10-20/research-observer/SKILL.md.before`.

## Where last week's packet stands

You decided the 2026-10-15 packet (PR [#356](https://github.com/ZK-Theory/TDL/pull/356), 26 OPEN in eleven groups) on
the same day, and the campaign closed on 2026-10-17. Its outcome is recorded in PR
[#378](https://github.com/ZK-Theory/TDL/pull/378), which merged today. Re-resolved against `origin/main` (`f6a8ae85`):

| Group | What it built | State now |
|---|---|---|
| A. Suite lane | `pin/*` tags for the five pinned commits, S-014 fix, pinned-commit check | Lane green three scheduled nights running (Group A below) |
| B. Signals | nightly-verdict issue, review-staleness line, `--close-conditions` | All three fired this week (Gate-liveness section) |
| C. Certification runner | `tools/certify_packet.py` (#362 `6f6227f7`, #364 `0f037415`) | On `main` |
| D. Fresh-store seam | both entries closed on #348 and #351 | Closed |
| E. CI glue | watchdog window and the shared step harness (#359 `0f8be24f`) | On `main` |
| F. Primary-checkout guard | #360 `335b7eeb`, scoped by #373 `12453e72` | On `main` |
| G. Long-run launch path | `tda-resource-preflight` 1.2.0, `tda-handoff` 1.4.0 (#361 `dae9f197`) | On `main`; the 2026-10-15 staging is byte-identical to `main`, so it is consumed |
| H. Residual plan limbs | deferred to Gate 7+ intake | DEFERRED |
| I. Amended decision property | `contract-first-tdd` 1.4.0 line (#361); code gap routed | The code gap was decided on 2026-10-15 (Group C below) |
| zktheoryweb | Zotero refresh opt-in (zktheoryweb #23) | Merged 2026-10-17; entry closed this review |
| codex_workflow | — | DEFERRED |

The 2026-10-17 outcome left six entries open. This review re-resolved each one:

| Entry | Outcome-table "waiting on" | Found today |
|---|---|---|
| `2026-10-02-full-suite-red-on-main-unseen` | three green nights, then your ruleset edit | Three green nights are done. The ruleset edit needs a check name that does not exist yet (Group A) |
| `2026-10-03-shared-seam-change-merged-without-its-dependents` | the same | the same (Group A) |
| `2026-10-05-build-mutates-tracked-zotero-cache` | zktheoryweb #23 | Merged 2026-10-17 15:15Z as `0153661`. **Closed** |
| `2026-10-15-amended-decision-property-left-unmechanized` | the Phase 5 session | You had already decided it, on 2026-10-15 (Group C) |
| `2026-10-17-cli-tests-read-the-committed-foundation-unpinned` | an autouse-sentinel decision | Built and merged as #379 (`f6a8ae85`) today. **Closed** |
| `2026-10-17-merge-admission-waiver-has-no-mechanism` | your waiver decision | Unchanged, and the guidance has drifted (Group B) |

## How to use this packet

Tick one box per group. An approved group first re-resolves each mapped observation against current `main`. If an
observation is already compliant or superseded, record the evidence and close it. If it is still valid, build the named
mechanism with its negative control.

## Decision summary

| Group | OPEN | Recommended resolution | Decision |
|---|---:|---|---|
| A. Making the research_system lane required | 3 | Add one `suite-verdict` job, then require that one check | `[ ]` approve 1–3 · `[ ]` 1 only · `[ ]` defer |
| B. Merge-admission guidance after #376 | 2 | Decline the waiver; correct `git.instructions.md:51` to match CONVENTIONS | `[ ]` option 1 · `[ ]` option 2 · `[ ]` guidance only |
| C. Amended-decision entry: close on your known-limit decision | 1 | Close it | `[ ]` close · `[ ]` defer code control to Gate 7 · `[ ]` keep open |
| D. Close-conditions lint across trees | 1 | Repo-qualified PR references in the lint | `[ ]` approve · `[ ]` defer |
| This review's two closures | — | Keep them closed | `[ ]` keep · `[ ]` reopen (name which) |
| The `research-observer` skill edit | — | Keep it | `[ ]` keep · `[ ]` revert |
| Simplification (no OPEN entries) | — | S1–S4 below | `[ ]` approve S1–S4 · `[ ]` approve some (name which) · `[ ]` defer |

Total: 3 + 2 + 1 + 1 = **7**.

---

## A — Making the research_system lane required (3)

**Where the lane stands.** All three scheduled nights since the campaign are green, every shard, at `12453e72`:

| Night | Run | Result |
|---|---|---|
| 2026-10-18 | 39103065738 | green; nightly-verdict closed issue #367 |
| 2026-10-19 | 39209681257 | green |
| 2026-10-20 | 39379034019 | green (finished 08:00Z, during this review) |

The first half of the close condition, three consecutive green scheduled nights, is met. #377 to #379 merged at 06:22Z
today, after the 2026-10-20 run had started at 06:12Z. So the 2026-10-21 night is the first scheduled run to include #379's foundation
sentinel.

**Defect (new, `2026-10-20-suite-lane-has-no-stable-required-check-name`).** The second half is your ruleset edit, and
as the workflow stands it cannot be made safely. On a pull request the lane reports `ci-tools`, `select`, and either
`suite (1)` to `suite (8)` or, when the PR touches no research_system test, one skipped check named `suite`. PR #378,
docs only, shows exactly that: `suite skipping`.
- Requiring the eight shard names would leave every docs-only PR, this one included, waiting forever on checks that
  never report.
- Requiring `suite` would never be satisfied by a PR that selects tests.
- A failed `select` also skips `suite`. Read naively, that looks the same as "nothing selected".

**Proposed action.**
1. In its own PR (git.instructions: workflow edits go in their own PR), add a `suite-verdict` job with
   `needs: [ci-tools, select, suite]` and `if: always()`. It passes only if `ci-tools` and `select` succeeded, and
   `suite` either succeeded or was skipped because the selection count was 0.
2. After `suite-verdict` has run green on one PR and one scheduled night, add `suite-verdict` to ruleset 20822054 as a
   required check. This is your edit: agent sessions never write rulesets (`admin-bypass-guard.sh`).
3. Close the three entries, naming the ruleset change.

**Controls.**
- (1) An empty selection gives `suite-verdict` success.
- (1) One failing shard gives failure.
- (1) A `ci-tools` failure gives failure.
- (1) A `select` failure gives failure, not "nothing selected".
- (2) The ruleset readback lists `suite-verdict`.

**Cost to weigh.** Once the lane is required, every PR that touches research_system code waits for its affected shards.
Shards have a 300-minute timeout, and the heaviest took about 57 minutes on the operator machine. On a hub change the
selection can be most of the suite: the L5 diff selected 90 files. `--partial-reason` remains the remedy for a narrower
scope you accept.

**Recommended decision:** approve 1–3.

**Decision:** `[ ]` approve 1–3 · `[ ]` approve 1 only (build the verdict job, decide the ruleset later) · `[ ]` defer

---

## B — Merge-admission guidance after #376 (2)

**Defect.**
- `2026-10-17-merge-admission-waiver-has-no-mechanism`. This is unchanged. The thread-finality check reads no waiver
  record, so "record an owner waiver" leads nowhere.
- `2026-10-20-git-guidance-still-requires-codex-after-producer-removal` (new). #376 (`3a14a97c`) removed Codex as the
  required producer. It updated `CONVENTIONS.md`, `.github/merge-admission.yml` and the gate. It did not update
  `.claude/instructions/git.instructions.md:51`, which still says "Merge admission needs Codex to reach a terminal
  state on the exact head". That line tells agents to comment `@codex review` and to record an owner waiver.
  `.claude/CLAUDE.md` points sessions to that file for git workflow.

**Why the two go together.** With no producer configured, the only refusal left is thread finality: an unresolved,
non-outdated review thread. Resolving the thread clears it, even when the reply declines the finding. The quota case
that prompted the waiver can no longer occur. The usage-limit message at `tools/check_merge_admission.py:292`, which
also offers a waiver, is dormant while `review_producers` is `[]`.

**Options.**
1. **Decline the waiver and correct the guidance (recommended).** Rewrite line 51:
   - no review producer is required (CONVENTIONS, 2026-10-17);
   - thread finality blocks on every unresolved, non-outdated thread, whoever wrote it;
   - the remedy is to reply and resolve the thread, and you resolve any thread whose finding you decline;
   - there is no waiver path, and agent sessions never bypass.

   In the same PR, drop "or record an owner waiver" from the dormant message at `:292`. Optionally, add a policy test
   in `tests/tools/test_ci_platform_policy.py` that fails when the guidance names a required producer that
   `review_producers` does not list.
2. **Build the waiver.** Thread finality would accept a head-scoped owner waiver, as the entry proposes. Then rewrite
   line 51 to describe it. This loosens a required gate.

**Controls.**
- (1) The policy test fails on a fixture with `review_producers: []` and guidance naming Codex.
- (2) The entry's three controls: a waiver for the current head passes; a waiver for an earlier head is refused; a
  waiver from a non-owner is refused.

`check_merge_admission.py` and `merge-admission.yml` are code-owned gate files, so either option is your review.

**Recommended decision:** option 1. It closes both entries, and it removes a remedy the gate no longer needs rather than
building one.

**Decision:** `[ ]` option 1: decline the waiver, correct the guidance · `[ ]` option 2: build the waiver, then correct
the guidance · `[ ]` correct the guidance only, defer the waiver

---

## C — Amended-decision entry: close on your known-limit decision (1)

`2026-10-15-amended-decision-property-left-unmechanized`. The entry has two limbs, and both are dispositioned:
- **The checklist line:** `contract-first-tdd` 1.4.0, #361 (`dae9f197`).
- **The code control:** delta-review finding m-1 is the same defect. On 2026-10-15 you dispositioned it as "**Known
  limit.** … No code change, so no M3". That is in P-058's disposition table in
  `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`, merged in #355 (`30dfd2d4`). Runbook §4
  step 4 holds the property with a verify line before `observe_source`. Phase 5 rehearsal 3 checked it read-only.
  `spec_source.py` is unchanged since #349 by that decision.

The two 2026-10-17 Progress notes and the 2026-10-17 outcome table said the gap was "open with the Phase 5 session". That
was stale: the decision predates both. This review fixed the record and the skill step that let it happen (see "Skills
pass").

**Proposed action.** Close as ACTIONED, citing #361 for the checklist limb and P-058 m-1 for the code limb. If you want
a code control after Gate 6 closes (refuse unless the derived Candidate is in the Task's `portfolio_refs`), choose
"defer" instead. That records it for Gate 7 intake.

**Recommended decision:** close.

**Decision:** `[ ]` close · `[ ]` defer the code control to Gate 7+ intake · `[ ]` keep open

---

## D — Close-conditions lint across trees (1)

`2026-10-20-close-conditions-lint-blind-to-cross-repo-prs` (new). `--close-conditions` resolves `#N` in the TDL
repository only.
- The zktheoryweb entry named its PR by URL, so the lint counted it under "names no PR" and did not judge it. The entry
  stayed open for three days after the PR merged.
- The reverse failure is also possible. A bare `#23` in that entry would have been checked against TDL's own PR #23.

**Proposed action.** Parse `owner/repo#N` and GitHub pull URLs in close-when clauses, and resolve each with
`gh pr view N --repo owner/repo`. When an entry's Target or Environment names another tree, report a bare `#N` as
ambiguous. Let `--pr-states` take repo-qualified keys.

**Controls.**
- A zktheoryweb-qualified clause is reported when its PR is MERGED and not when it is OPEN.
- A bare `#N` under a zktheoryweb Target is reported as ambiguous.

Until this lands, the `research-observer` skill tells the review to check cross-tree conditions by hand (applied this
review).

**Recommended decision:** approve. It is small, `tools/` only, and not a gate file.

**Decision:** `[ ]` approve · `[ ]` defer

---

## This review's closures

| Entry | Close condition | Evidence |
|---|---|---|
| `2026-10-17-cli-tests-read-the-committed-foundation-unpinned` | #379 merges | `f6a8ae85` on `origin/main`. The lint reported this condition as met. The negative control is `test_an_unpinned_cli_call_fails_with_the_sentinel_message` |
| `2026-10-05-build-mutates-tracked-zotero-cache` | zktheoryweb PR 23 merges | Squash commit `0153661` on zktheoryweb `origin/main`. There `astro.config.mjs` calls `zoteroBuildStart(process.env, …)`. Verified read-only |

If you disagree with either, tick "reopen" and I will restore OPEN from the backup.

## Simplification (no OPEN entries)

These are removals for you to approve. This run did not do them: deleting tasks and worktrees is outside an autonomous
review's remit.

- **S1.** Delete the two finished one-time scheduled tasks, `pr333-heavy-regression` and
  `research-system-lane-required-followup`. Both are disabled and done. Last week's packet recommended the same.
- **S2.** Mark DECLINED and archive the four DEFERRED entries whose subject is Codex:
  - `155` (Codex app control plane);
  - `01KZKNM7DPMJWTB8D83JQGXCJM` (Codex `computer-use` plugin);
  - `01M044JXYSPP0VXH15TEZVCNA3` (codex_workflow closure);
  - `2026-09-25-codex-live-hooks-are-stale-sibling-copies`.

  You stopped using Codex (2026-10-06 Group F, and #376 on 2026-10-17). Also archive the legacy
  `~/.Codex/skill-observations` store, whose `last-review-date.txt` still reads 2026-08-06. The other 21 full-text
  DEFERRED entries are unchanged: 19 are held by the Gate 6 D5 process and 2 by Gate 7+ intake.
- **S3.** "Sweep worktrees" (your trigger, per CLAUDE.md). Twelve linked worktrees are on branches whose PRs have
  merged: #186, #193, #277, #284, #345, #370, #371, #372, #373, #374, #376 and #379. Three have no PR:
  - `diag/s014-runner-paths` is a throwaway diagnostic, one commit;
  - `claude/recursing-poincare-92f774` has no commits ahead of `main`;
  - `repo/06q-section4-retirement` has five local-only commits from 2026-09-08. Its work landed as #334 from
    `repo/06q-retirement-gate`. Confirm that before removing it.

  Check CodeRabbit on each PR first, as CLAUDE.md requires.
- **S4.** Move `log.md.bak-2026-09-08` and `log.md.bak-2026-09-09` (357 KB) from the observation store root into
  `archive/`. Each review now keeps its own dated backup under `skill-updates/`.

---

## Completeness ledger

Computed, not assembled. Every OPEN id comes from `observation_log_lint.parse` over the live log after this review's
edits, and the table is checked with `tools/observation_log_lint.py <log> --packet <this file>`.

| Group | Count | IDs |
|---|---:|---|
| A | 3 | 2026-10-02-full-suite-red-on-main-unseen · 2026-10-03-shared-seam-change-merged-without-its-dependents · 2026-10-20-suite-lane-has-no-stable-required-check-name |
| B | 2 | 2026-10-17-merge-admission-waiver-has-no-mechanism · 2026-10-20-git-guidance-still-requires-codex-after-producer-removal |
| C | 1 | 2026-10-15-amended-decision-property-left-unmechanized |
| D | 1 | 2026-10-20-close-conditions-lint-blind-to-cross-repo-prs |
| **Total** | **7** | |

---

## Lint and ledger check

| When | Tool | Result |
|---|---|---|
| Before this review's edits | `observation_log_lint.py --reachability . --close-conditions .` at `f6a8ae85` (= `origin/main`) | `238 observation(s): 6 OPEN`. Reachability: 9 hashes, 0 stranded, 1 not a TDL commit (zktheoryweb). One close condition met (#379). Exit 1 |
| After the edits | same | `242 observation(s): 7 OPEN`. Reachability: 13 hashes, 0 stranded. Close conditions: 0 met, 4 name no PR. Exit 0 |
| After the edits, `--packet` on this file | `observation_log_lint.py <log> --packet <this file>` | see the PR's test plan |

The edit was made by a script that refused to write unless five checks held:
- the log matched its backup's SHA-256;
- the id order was unchanged, with the four new entries appended at the end;
- the OPEN set changed by exactly the two closures and three additions;
- every untouched entry was byte-identical apart from trailing whitespace;
- the lint's non-reachability checks came back clean.

One Progress note was then updated by hand when the 2026-10-20 night finished green.

**Archival.** No closed entry remains in full text from before this review. The 2026-10-17 campaign archived all 44 to
`archive/log-2026-10-17.md`. This review's two closures, and its applied SKILL entry, stay in full text until the next
review so that you can reopen them.

## Skills pass

**Inventory.**
- `sync_agent_skills.py --check`: all 63 synced skills IDENTICAL; `pack pins: 12 checked, 0 drifted`.
- Since the last review, two commits changed skills: #361 (`tda-resource-preflight`, `contract-first-tdd`, `tda-handoff`)
  and #374 (`tda-large-workflow-supervision`). Both reached `.agents/skills` and `.claude/skills` together.
- The 2026-10-15 staging folder is consumed: its `tda-resource-preflight` 1.2.0 is byte-identical to `main`.
- The `.agents/skills` entries outside the sync manifest are the APM command skills, `writing-skills-extras` and
  `SKILL-INDEX.md`. This review did not touch them.

**Cross-check of every OPEN group against the skills.**
- **A:** no skill change. The fix is a workflow job. `tda-codebase-design` and `contract-first-tdd` already say that a
  seam change is verified by its callers, and the PR-time selection enforces it.
- **B:** no skill names Codex as a required reviewer; the stale text is in `.claude/instructions/git.instructions.md`.
  It is not applied here, because its wording depends on the waiver decision.
- **C:** `contract-first-tdd` 1.4.0 already carries the headline-invariant line.
- **D:** the `research-observer` skill now says the lint does not judge cross-tree conditions (applied).

**Applied (SKILL lane, global `research-observer`, not pack-pinned, not in git):**
1. Step 1 runs `--close-conditions .` alongside `--reachability .`. #357 has been on `main` since 2026-10-17, so the
   rule "instructions ship after their mechanisms" holds.
2. The "Close conditions are linted" paragraph drops "once #357 is on `main`". It now says that conditions on another
   tree's PR are counted, not judged, and must be checked by hand until Group D lands.
3. Step 1 gains "Re-resolve against the decision record too". Before restating an item as waiting on a session or a
   decision, search `03-decisions-and-open-questions.md`, `CONVENTIONS.md` and the raising review for its finding id.
   (Obs `2026-10-20-progress-notes-restated-a-decided-item-as-pending`, ACTIONED.)

Compliance against the active cross-cutting principles: edit 3 extends Principle 8 (re-resolve each stated state against
its source before planning from it) from commits to decisions. No edit adds or weakens a gate.

**Simplification sweep.** See S1–S4 above. No skill is proposed for removal this week. Every synced skill is IDENTICAL
and none is superseded by a mechanism built this week.

## Gate-liveness spot check

Two gates that no packet has named since the 2026-07-26 one (`admin-bypass-guard.sh` was built after it):

1. **`.claude/hooks/admin-bypass-guard.sh`.** This is the guard CONVENTIONS relies on: agents never take the P-049
   bypass.
   - Positive signal: 5,284 receipts in `.claude/hooks/hook-receipts.log`, all `allow`, from 2026-09-12 to today.
   - Negative control: `tests/tools/test_admin_bypass_guard_hook.py`. Parametrized denials, a fail-closed test on a
     guard error, and a wiring test through the receipt wrapper. It runs in the required `admission-controls` lane
     (`ci.yml:170`) with skip refusal.
   - Healthy. It has never denied in production, but its denials are exercised on every PR.
2. **`.claude/hooks/mirror-tree-guard.sh`.** This guard protects the dual-tree skill sync.
   - Positive signal: 3,322 receipts, including 4 production `deny` decisions (the latest on 2026-08-02) and 2 visible
     fail-opens, both on 2026-07-28.
   - Negative controls: three tests in `tests/tools/test_system_review_hook_gates.py`, run by `ci.yml:185`.
   - Healthy.

Both test files ran locally in this review: **48 passed**. No destructive probe was run.

**Mechanisms from last week's campaign, seen firing on live data:**
- **nightly-verdict:** opened #367 on the red 2026-10-16 night, commented on 2026-10-17, and closed it on the green
  2026-10-18 night. That is a full open, update and close cycle.
- **The review-staleness SessionStart line** printed "last ran 2026-10-15 (5 days ago)" at this session's start.
- **`--close-conditions`** reported #379's met condition: a true positive. It missed the zktheoryweb condition
  (Group D).
- **`--reachability`:** 0 stranded across 13 hashes.

## Coverage question

"Did anything go wrong this week that no gate, contract or invariant caught?" Yes:

| What went wrong | Caught by | Observation |
|---|---|---|
| An entry stayed OPEN three days after its zktheoryweb PR merged | this review, by hand | `2026-10-20-close-conditions-lint-blind-to-cross-repo-prs` (D) |
| `git.instructions.md` still requires Codex after #376 | this review, by hand | `2026-10-20-git-guidance-still-requires-codex-after-producer-removal` (B) |
| An entry was recorded as waiting on a session for five days after you had decided it | this review, by hand | `2026-10-20-progress-notes-restated-a-decided-item-as-pending` (ACTIONED) |
| The ruleset edit the lane's close condition names has no check it could require (not yet harmful) | this review, by reading the workflow and #378's checks | `2026-10-20-suite-lane-has-no-stable-required-check-name` (A) |

None is a numerical or statistical failure, so none is an invariant-battery item.

## This review's actions

1. Found the previous packet (#356) and its outcome (#378), and re-resolved both against `origin/main` (`f6a8ae85`).
2. Ran `git fetch origin` and the lint with `--reachability . --close-conditions .`, before and after the edits.
3. Read the nightly runs for 2026-10-18 to 2026-10-20, issue #367, ruleset 20822054 and the checks on #378.
4. Verified the non-TDL items read-only: zktheoryweb's `origin/main` (`0153661`, `astro.config.mjs`), and that MathUni
   and the Counting Lives vault have no new observation files.
5. Closed two entries on their met conditions, added five Progress notes, and logged four observations (one applied and
   closed), through the checked script. Backup: `~/.claude/skill-updates/2026-10-20/log/log.md.before`.
6. Applied three edits to the global `research-observer` skill. Backup:
   `~/.claude/skill-updates/2026-10-20/research-observer/SKILL.md.before`.
7. Ran both spot-checked gates' negative-control tests (48 passed).
8. Updated `last-review-date.txt` to `2026-10-20`.
9. Opened this packet as a PR.
