# Weekly Research-System Review — Resolution Packet

**Review date:** 2026-11-10. The scheduled `weekly-system-review` task ran on time (Tuesday, from about 08:40Z).

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md`. After this review it holds 298 entries, 12 of
them OPEN (OPEN, ESCALATED or PARTIALLY, per the lint).

**Scope:** every OPEN observation in the shared log, across the five trees named by the 2026-09-25 and 2026-10-02 owner
decisions: TDL, MathUni, the Counting Lives vault, codex_workflow and zktheoryweb. The other four trees were read only.
None of them has a commit or changed file since the last review, and no OPEN entry targets them. No tree outside the
five appears in the log, so there is no scope finding.

**Decision owner:** Stephen

**Operating rule (unchanged since 2026-08-09):** approval authorizes a bounded verify-then-fix campaign on a reviewed
branch. It does not authorize direct changes to `main`, silent gate weakening, or acceptance without the named
controls.

> **Act today: `main` is red.** PR #420 (WP9.3-1) merged at 09:04Z by admin bypass, while its suite was red on an
> earlier head and still running on the merged one. `main` at `23f8f737` fails two tests,
> `test_submission_lock_yields_the_acquired_composite_lease` and `test_submission_lock_retries_writer_lock_contention`.
> Both breaks are in tests that build `CommandService` by hand. On your go-ahead after this review, the fix is open as
> PR #422 (Group A1). Unfixed, tonight's nightly goes red and opens an issue, and so does every PR that selects either
> file. See Group A.

**What this review changed.**
- **Record (observation log):**
  - **Closed 13 entries on verified evidence.** Each had met its close condition. Every PR named was checked for base
    `main` and a merge commit on `origin/main`. One of the 13 carries a deferred limb, so its status is DEFERRED. See
    "This review's closures".
  - **Added dated Progress notes** to the nine carried entries that stay open.
  - **Logged five observations.** Three are OPEN (Groups A, B and F). Two, on the SKILL lane, were applied in this
    review.
  - **Archived** the 20 entries that the 2026-11-03 review and its campaign closed, to `archive/log-2026-11-10.md`.
- **Skill (applied, outside git):** research-observer, two edits. Step 1 now states the `--intake` option and the
  landed-by-content report as standing, since #417 and #419 are on `main`. Step 3 now asks whether a gate sits on the
  path its files take, and says to read the receipt log with `grep -a`. Backup:
  `~/.claude/skill-updates/2026-11-10/research-observer/SKILL.md.before`.
- **Not changed:** any repo skill, and anything on the GATE, INVARIANT or PROCESS lanes. Nothing in the other trees.
  Everything below is a recommendation.

The pre-review log is at `~/.claude/skill-updates/2026-11-10/log/log.md.before`.

## Where last week's packet stands

You approved the 2026-11-03 packet (PR [#412](https://github.com/ZK-Theory/TDL/pull/412)) as recommended on 2026-11-08.
The campaign PRs #416 to #419 all merged that night, each with base `main` and a merge commit on `origin/main`.
Re-resolved against `origin/main` (`23f8f737`):

| Group | Decision | Built | State now |
|---|---|---|---|
| A. Make the suite lane required | approve A1+A2 | #419 (A2) | A2 is in `CONVENTIONS.md`. A1, your ruleset edit, is not made: ruleset 20822054 was last updated 2026-09-11. The first bypass after the A2 lock left `main` red (Group A) |
| B. Observation-log lint precision | approve B1–B3 | #417 | Done; both entries closed. Every lint finding in this review was true |
| C. Design-note evidence discipline | approve C1–C3 | #416, #419 | C1 done (two entries closed), C2 merged the twin, C3's test is carried to WP9.3-2 (Group C) |
| D. Negative-control construction | approve D1–D3 | #416 | Done; three entries closed |
| E. Catalogue and plan interfaces | approve E1–E2 | #416, #419 | The skill line is done. E1's test waits on WP9.3-2. The 06v paths addendum is now due, since #411 merged on 2026-11-09 (Group C) |
| F. Controls and lints no lane runs | approve F1–F3 | #417, #418 | Done; two entries closed. The register lint reports 0 stranded |
| G. Results-reminder scope | approve | #418 | Done; 13 `silent` receipts so far |
| H. Deferrals with no landing record | (a) new file | #417, #419 | Done; `--intake` reports 5 deferrals, 0 without a row |
| Closures, research-observer edit, S5 | keep, keep, approve | — | Kept. S5 done: only `weekly-system-review` remains under `~/.claude/scheduled-tasks/` |

## How to use this packet

Tick one box per group. An approved group first re-resolves each mapped observation against current `main`. If an
observation is already compliant or superseded, record the evidence and close it. If it is still valid, build the named
mechanism with its negative control.

## Decision summary

| Group | OPEN | Recommended resolution | Decision |
|---|---:|---|---|
| A. `main` is red after a bypass merge | 1 | Fix the test today; add a control for the hand-built service; reinstate the bypass audit | `[ ]` approve A1–A3 · `[ ]` A1+A2 only · `[ ]` defer |
| B. The suite lane: required, and its flake owned | 3 | Your ruleset edit; triage the writer-lock conflict; keep the nightly issue's recurrence visible | `[ ]` approve B1–B3 · `[ ]` B2+B3 first, B1 after triage · `[ ]` defer |
| C. Items carried to W9 packages | 3 | Mark the three DEFERRED to their intake rows; write the 06v paths addendum now | `[ ]` approve C1+C2 · `[ ]` C2 only · `[ ]` defer |
| D. Design-note claim discipline, round 2 | 3 | Three skill lines, author and reviewer side; settle the stranded findings file | `[ ]` approve D1–D4 · `[ ]` some (name which) · `[ ]` defer |
| E. Format drift on `main` | 1 | A changed-files-only rule; no mass reformat | `[ ]` (b) rule only · `[ ]` (a) reformat with a pin census · `[ ]` defer |
| F. Results no-overwrite on the commit path | 1 | A pre-commit refusal of a staged rewrite of a tracked result | `[ ]` approve (rewrites) · `[ ]` approve (rewrites, deletions, renames) · `[ ]` defer |
| This review's 13 closures | — | Keep them closed | `[ ]` keep · `[ ]` reopen (name which) |
| The two research-observer edits | — | Keep them | `[ ]` keep · `[ ]` revert |
| S6. One claims checklist for the two design skills | — | Write each lesson once | `[ ]` approve · `[ ]` decline |
| S7. The task prompt restates step 1 | — | Point it at the skill | `[ ]` approve · `[ ]` decline |

Total: 1 + 3 + 3 + 3 + 1 + 1 = **12**.

---

## A — `main` is red after a bypass merge (1)

`2026-11-10-bypass-merge-skipped-a-red-suite-and-left-main-red` (new).

**What happened.**
- PR #420 (WP9.3-1, 48 files, no gate file) merged on 2026-11-10 at 09:04:21Z as `23f8f737`. The rule-suite API records
  it as `bypass` by stephendor, with no merge-queue run.
- Its last commit, `441f3f09` (nine lines in the WP9.3-1 record), is dated 09:02:48Z. At the merge, these checks on the
  merged head were still running: `contract-and-session-currency` and `admission-controls`, which the ruleset requires,
  and all eight suite shards.
- The suite run on the earlier head `663388f8` had finished red at 08:56Z. Shard 8 reported "new failure (not in
  baseline)": `test_submission_lock_yields_the_acquired_composite_lease`, with
  `AttributeError: 'CommandService' object has no attribute 'binding_check'`.
- The two pushes after it (`2f215881`, a test-counting change, and `441f3f09`) did not touch that test. Their suite runs
  were cancelled or still running. I ran the test on `23f8f737`, and it fails.
- The same run's shards 3, 4, 6 and 7 were cancelled, so they reported nothing. Running every test file that builds
  `CommandService` by hand on `23f8f737` found a second failure with the same cause:
  `test_command_lock_retry.py::test_submission_lock_retries_writer_lock_contention` (2 failed, 133 passed).
- The PR states no reason for the bypass. No agent receipt in the WP9.3-1 worktree shows a merge attempt at 09:04, and
  `admin-bypass-guard.sh` refuses agent bypasses, so the merge was probably made outside an agent session. I did not
  establish that.

**Defect.**
- **The test.** It builds `CommandService` with `object.__new__` and copies `__init__`'s defaults by hand; its comment
  notes that #208 added four of them. #420 added `self.binding_check` in `__init__`, and `_recheck_binding`
  (`research_system/command/service.py:1890`) reads it. Production builds the service through `__init__`, so this is a
  test break. But `main` is red.
- **The merge path.** This is the first bypass since A2 was locked, and it skipped a red suite. Of the two updates to
  `main` since #419 merged, #411 went through the queue and #420 did not. You declined the bypass audit on 2026-11-08
  because bypasses had become rare. That still holds, but the one that happened went unseen. Requiring `suite-verdict`
  (B1) would not have stopped it: the bypass skips required checks too.

**Proposed action.**
- **A1.** Fix forward today: add `service.binding_check = None` to both tests' hand-copied defaults, merged through the
  queue. You approved this after the review, and it is open as PR #422.
- **A2.** Remove the hand copy's failure mode. Build the service through `__init__`, or add a control that compares the
  attribute names of the hand-built service with those of one built normally.
- **A3.** Reinstate the bypass audit. For each bypassed update to `main`, it checks that the required checks and
  `suite-verdict` were green on the merged head and that the PR states a reason, and reports any that fail.

**Controls.** A1: both tests pass on the fix and fail on `23f8f737`. A2: an attribute added to `__init__` and not to
the copy fails the control. A3: a fixture of this merge (`23f8f737`, checks in progress, prior head red, no reason) is
reported. A merge through the queue is not.

**Recommended decision:** approve A1–A3. A1 is urgent: the next scheduled run is tonight (cron 01:30 UTC; recent runs
have started between 07:00Z and 08:35Z). The WP9.3-1 record covers CI on `e13bf197` and does not mention the
`663388f8` failure.

**Decision:** `[ ]` approve A1–A3 · `[ ]` A1+A2 only · `[ ]` defer

---

## B — The suite lane: required, and its flake owned (3)

`2026-10-02-full-suite-red-on-main-unseen`, `2026-10-03-shared-seam-change-merged-without-its-dependents`,
`2026-11-10-nightly-writer-lock-flake-closes-its-own-issue-untriaged` (new).

**Where it stands.** Ruleset 20822054 still requires only contract-and-session-currency,
require-active-currency-workflow, merge-admission and admission-controls (readback 2026-11-10). `suite-verdict`
succeeded on all four merge-queue runs since #416 (latest 42649213332, for #411). It also succeeded on five of the seven
scheduled nights from 2026-11-03 to 2026-11-09.

**Defect: an intermittent failure nobody owns.**
- The two red nights, 2026-11-03 (run 41600884072, shard 8) and 2026-11-08 (run 42459480856, shard 2), both ran at
  `44b6f2b5`. That commit passed on at least eight other nights.
- Each failed one test, a different one each night, with the same error: the store's own refusal during lock cleanup,
  `ConflictError('writer lock name was replaced during exact generation deletion')`, raised at
  `research_system/store/anchor.py:1731`. The tests were
  `test_wp6_1_scope_task_authority.py::test_cross_store_revocation_wins_first_rejects_without_domain_mutation_and_retries`
  and `test_wp6_2_t2_runtime.py::test_t2_authority_lock_revocation_wins_and_rechecks_authority[AuthorizeProviderIssue]`.
- The `nightly-verdict` job opened issues #413 and #414 and closed each itself the next night. No one else commented.
- The full-suite entry's 2026-10-15 Progress note listed "one intermittent writer-lock conflict", and nothing since has
  given it an owner. No one has asked whether it is a test race or a store defect. Since the error is the store's own
  refusal, a production writer might meet it.
- The baseline cannot hold it: the lane fails when a listed entry passes.

**Proposed action.**
- **B1.** Your ruleset edit: add `suite-verdict` to the required checks (unchanged from last week's A1).
- **B2.** Triage the conflict: run the two tests in a loop on Windows, measure the rate, capture the interleaving,
  decide between a test race and a store defect, and record the answer. `tda-diagnosing-computational-defects` fits.
- **B3.** Keep the recurrence visible. The `nightly-verdict` job's close comment lists the node ids that failed on red
  nights in the last 14 days, or the issue stays open when one node id failed twice in that window.

**Controls.** B1: the ruleset readback lists `suite-verdict`, and the next queue entry reports it as required. B3: a
fixture of two red nights a week apart on one node id leaves the issue open, or reports "2 red nights in 14 days".

**Recommended decision:** approve B1–B3, with B1 now. The flake hit two full nightly runs in ten; a queue entry runs only
its affected selection, and a false red costs a re-queue of about ten minutes. Group A shows what the lane catches.

**Decision:** `[ ]` approve B1–B3 · `[ ]` B2+B3 first, B1 after triage · `[ ]` defer

---

## C — Items carried to W9 packages (3)

| Entry | Carried item | Where it waits |
|---|---|---|
| `2026-10-28-catalogue-precondition-unrepresentable-in-closed-schema` | A precondition-to-field test (E1) | WP9.3-2; row in `gate7-intake-deferrals.md` §2 |
| `2026-10-29-note-cited-a-truncated-row-range-and-built-an-owner-point-on-it` | The §12.3 fixture-table test (C3) | WP9.3-2; row in §2 |
| `2026-10-28-shared-location-named-but-never-defined` | A dated 06v addendum with a "W9 paths" table (E2) | 06v, "after #411 merges"; row in §2 |

Each entry's skill limb is on `main` (#416). WP9.3-1 merged today; WP9.3-2 has not started.

**Defect.** None new. The three carry no work for this week, but each review re-notes them. The 06v addendum is now
due: #411 merged on 2026-11-09, and `git grep -n "W9 paths" docs/plans` finds only the intake row and last week's
packet.

**Proposed action.**
- **C1.** Set each entry's status to DEFERRED, naming its row in the Gate 7+ intake list §2. The `--intake` check then
  guards it, and it leaves the weekly OPEN count. Its row closes when its package lands the item.
- **C2.** Write the 06v "W9 paths" addendum now: the evidence area (P-081) and any other location two W9 packages share.
  The shared-location entry closes when it merges.

**Controls.** C1: `--intake` reports 8 deferrals, 0 without a row. C2: the paths table names the P-081 path verbatim.

**Recommended decision:** approve C1 and C2.

**Decision:** `[ ]` approve C1+C2 · `[ ]` C2 only · `[ ]` defer

---

## D — Design-note claim discipline, round 2 (3)

From the WP9.3 note's last revisions and WP9.3-1's implementation. Each instance is resolved on `main`: the
enforcement claim by the note's revision 6 (#411), and the other two by your 2026-11-09 rulings, built in #420 and
recorded in `transition/w9/wp9-3-1-record.md` §3. The 2026-11-08 bullets cover each lesson only in part.

| Entry | The lesson | Nearest existing text |
|---|---|---|
| `2026-11-08-enforcement-impossibility-claim-cited-one-function` | A claim that code cannot enforce X cites every path that reaches the seam, not one function's docstring | `writing-plans-extras` "Caller-Inventory Closure" (author side); nothing on the reviewer side |
| `2026-11-09-design-note-encoding-never-run-through-the-unchanged-assigner` | A probe covers the revision it ran on. A revision that adds or changes an encoded field re-runs it | "Probes", in both skills, which covers a changed shape only |
| `2026-11-09-design-note-wiring-claims-named-the-wrong-construction-site` | An "X passes Y to Z" claim cites where production builds Z and shows the builder holds Y | `writing-plans-extras` "Interface Verification", which asks for signatures only |

**Proposed action.**
- **D1.** Enforcement claims. Extend `adversarial-design-review` "Absence claims": a claim that code cannot enforce X,
  or that X is recorded rather than proved, needs a census of the call paths that reach the seam (every production
  constructor and the admission it goes through). Add the matching clause to `writing-plans-extras` "Caller-Inventory
  Closure".
- **D2.** Probe currency. Add one sentence to both "Probes" bullets: a probe result covers the revision it ran on, and
  a revision that adds or changes an encoded field re-runs it.
- **D3.** Wiring claims. In `writing-plans-extras` "Interface Verification", each "X passes Y to Z" cites Z's production
  construction sites and shows the builder holds Y, and the package boundary lists every file such a claim touches. Add
  a matching "Wiring claims" bullet to `adversarial-design-review`. For the two W9 runtimes, the AST construction census
  on `main` (#420, `test_w9_wp9_3_censuses.py`) already checks this mechanically.
- **D4.** The stranded findings file. `6dcc2f61` (`transition/w9/wp9-3-writer-version-findings.md`, 179 lines) is on the
  local branch `claude/w9-writer-version-enforcement-94f88a` only. Its substance is on `main` (WP9.3 note §9.1, the
  P-081 item 3 amendment) and in a PR #411 comment (issuecomment-6726327810). Land the file in a docs PR, or accept the
  comment as its record. The reachability lint reports it every week until one happens.

**Controls.** D1 to D3 are text. Their evidence is the next W9 design-note review: no "cannot enforce" claim without a
path census, no probe credited across a revision that changed encodings, and no wiring claim without a construction
site. D4: the reachability lint goes silent on `6dcc2f61`.

**Size.** `adversarial-design-review` is 319 lines (302 last week, 262 the week before). D1 to D3 add about ten lines.
S6 proposes a way to stop the growth.

**Recommended decision:** approve D1–D4. These are PROCESS-lane entries, so this run did not apply them.

**Decision:** `[ ]` approve D1–D4 · `[ ]` some (name which) · `[ ]` defer

---

## E — Format drift on `main` (1)

`2026-11-09-main-holds-files-ruff-format-would-change`.

**Defect.** The entry says a directory-wide `ruff format` pulled three unrelated files into a commit. On `main` at
`2d9aeddc`, with the locked ruff 0.14.9 (`.pre-commit-config.yaml` pins the same version):
- `ruff format --check .` would reformat 250 of 942 files. 43 of them are under `research_system/` or
  `tests/research_system/`.
- At least 16 of the 250 are named in `contracts/` or `.research-system/`.
- CI runs `ruff check .` and no format check. The pre-commit hook formats staged files only.

**Proposed action.**
- **(a)** A one-off reformat PR. It first takes a census of the bytes that contracts and accepted packs pin, and
  excludes those files. Then CI checks `ruff format --check` on the rest.
- **(b)** No mass reformat. Add one line to `.claude/rules/python.md`: format the files you changed, never a directory,
  and check `git diff --stat` before committing. The entry closes on that line.

**Recommended decision:** (b). The pre-commit hook reformats each file a commit touches, so the drift shrinks as work
proceeds. A mass reformat changes 250 files' history and risks pinned bytes, for no change in behaviour.

**Decision:** `[ ]` (b) rule only · `[ ]` (a) reformat with a pin census · `[ ]` defer

---

## F — Results no-overwrite on the commit path (1)

`2026-11-10-results-no-overwrite-misses-the-path-results-take` (new, from this review's spot check).

**Defect.**
- `.claude/hooks/results-no-overwrite.sh` is live. It has 5,420 receipts since 2026-07-28, all `allow`, and 24
  controls in `tests/tools/test_results_no_overwrite_hook.py`, which admission-controls runs (`ci.yml` line 188). They
  passed in this review.
- Its matcher is `Write|Edit|MultiEdit`. Its own header says result scripts write through Python and nothing in the
  hook can intercept them. The skill-prose-controls register (lines 127 and 252) has listed the script-side extension
  as open since July.
- Last week's fix for the twin reminder (#418) put a results check at commit time, but `commit-msg` reads additions
  only (`--diff-filter=A`). A script that rewrites a date-suffixed result, committed under any prefix, passes every
  gate.
- No overwrite is known to have happened, and no results have been added since 2026-07-18.

**Proposed action.** In `.githooks/pre-commit`, refuse a staged modification of a tracked `results/**/*.{json,npy,npz}`
file, and write a receipt. Choose whether deletions and renames are refused too. A superseding result goes in a new
date-suffixed file, so the rule needs no escape hatch.

**Controls.** A staged edit of a committed results JSON blocks the commit. A new date-suffixed file passes. The receipt
records both.

**Recommended decision:** approve, for rewrites. Your call on deletions and renames.

**Decision:** `[ ]` approve (rewrites) · `[ ]` approve (rewrites, deletions, renames) · `[ ]` defer

---

## This review's closures

Each closing Status names its evidence, and the previous Status is kept as a `Prior status:` line. They stay in full
text until the next review. If you disagree with any, tick "reopen" and I will restore it from the backup.

| Entry | Status | Evidence |
|---|---|---|
| `2026-10-27-merge-queue-never-entered-every-main-update-bypasses` | ACTIONED | #419 `14a81b84`: `CONVENTIONS.md`, queue by default; the bypass audit declined. The later #420 bypass is Group A |
| `2026-10-27-stacked-pr-merged-into-a-dead-base-reads-as-delivered` | ACTIONED | #417 `9aa359c7`: `_gh_pr_state` reads `baseRefName`; `test_a_pr_merged_into_another_base_is_not_delivered` |
| `2026-11-03-log-lint-judges-delivery-by-hash-and-pr-state` | ACTIONED | #417: `landed_by_content`, state-field-only close conditions, `after #N` preconditions; every finding this week true |
| `2026-10-27-design-note-chose-an-unprobed-shape` | ACTIONED | #416 `c0b28191`: "Probes" in `adversarial-design-review` 1.3.0 and `writing-plans-extras` 1.3.0 |
| `2026-10-28-obligation-restated-open-though-accepted-text-fixed-it` | ACTIONED | #416: "Owner points on rules"; "Rules the owner may already have fixed" |
| `2026-10-28-byte-identity-controls-bypass-their-guard-despite-checklist` | ACTIONED | #416: `assert_byte_identity` in `tests/research_system/contracts/byte_identity.py` |
| `2026-10-28-authority-guard-tests-ran-only-as-the-owner` | ACTIONED | #416: `NON_OWNER_ACTOR_ID`; `contract-first-tdd` 1.6.0 line 156. Limb 3 was outside approved D2 |
| `2026-10-29-negative-control-vehicle-becomes-production-in-a-later-package` | ACTIONED | #416: `contract-first-tdd` 1.6.0 line 157 |
| `2026-11-03-review-lints-built-but-run-by-no-lane` | ACTIONED | #418 `4307bd6a`: `ci.yml` lines 206 and 223; #417 `KNOWN` list; 0 stranded |
| `2026-11-03-gate-controls-outside-the-hook-glob-run-in-no-lane` | ACTIONED | #418: `test_every_tools_and_contracts_test_runs_in_a_workflow`; `ci.yml` lines 206 to 211 |
| `2026-11-03-results-vault-reminder-blind-to-script-written-results` | ACTIONED | #418: `.githooks/commit-msg` lines 80 to 99; 13 `silent` receipts |
| `2026-11-03-gate7-intake-deferrals-have-no-landing-record` | ACTIONED | #419: `gate7-intake-deferrals.md`; #417: `--intake`, 5 checked, 0 without a row |
| `2026-10-27-note-departed-from-a-carried-owner-item-silently` | DEFERRED | #416 skill limb; the lint deferred to Gate 7+ intake, row in §1 (#419) |

## Simplification sweep

- **S6 (new). One claims checklist for the two design skills.** `adversarial-design-review` "Claims About Another
  Artefact" has 14 bullets, and the skill grew from 262 to 319 lines in two weeks. `writing-plans-extras` restates most
  of them from the author's side, so each lesson is written twice, and Group D would add three more pairs. Move the
  shared checklist into one reference file, `adversarial-design-review/references/claims-checklist.md`, with an author
  line and a reviewer line per claim type, and have both skills link to it. `tools/sync_agent_skills.py` copies a
  skill's whole directory, so a `references/` file syncs. Neither skill is pack-pinned. The edit is structural, so it
  would be staged for your review.
- **S7 (new). The task prompt restates step 1.** The `weekly-system-review` task's step 2 copies research-observer's
  step-1 commands and has drifted: it omits `--close-conditions` and `--intake`. Replace it with a pointer to the
  skill's step 1. The task file is yours.
- **No skill is proposed for removal.** No mechanism built this week supersedes one. The research-observer edits
  removed two conditionals rather than adding steps.

---

## Completeness ledger

Computed, not assembled. Every OPEN id comes from `observation_log_lint.parse` over the live log after this review's
edits, and the table is checked with `tools/observation_log_lint.py <log> --packet <this file>`.

| Group | Count | IDs |
|---|---:|---|
| A | 1 | 2026-11-10-bypass-merge-skipped-a-red-suite-and-left-main-red |
| B | 3 | 2026-10-02-full-suite-red-on-main-unseen · 2026-10-03-shared-seam-change-merged-without-its-dependents · 2026-11-10-nightly-writer-lock-flake-closes-its-own-issue-untriaged |
| C | 3 | 2026-10-28-catalogue-precondition-unrepresentable-in-closed-schema · 2026-10-29-note-cited-a-truncated-row-range-and-built-an-owner-point-on-it · 2026-10-28-shared-location-named-but-never-defined |
| D | 3 | 2026-11-08-enforcement-impossibility-claim-cited-one-function · 2026-11-09-design-note-encoding-never-run-through-the-unchanged-assigner · 2026-11-09-design-note-wiring-claims-named-the-wrong-construction-site |
| E | 1 | 2026-11-09-main-holds-files-ruff-format-would-change |
| F | 1 | 2026-11-10-results-no-overwrite-misses-the-path-results-take |
| **Total** | **12** | |

---

## Lint and ledger check

| When | Tool | Result |
|---|---|---|
| Before this review's edits | `observation_log_lint.py --reachability . --close-conditions . --intake <list>` at `2d9aeddc` | `293 observation(s): 22 OPEN`. Reachability: 25 hashes, 1 stranded (`6dcc2f61`, true), 1 not a commit here (in an entry archived since). Close conditions: 12 checked, 12 met, all true. Intake: 4 checked, 0 without a row |
| After the edits | same, at `23f8f737` | `298 observation(s): 12 OPEN`. Reachability: 27 hashes, 1 stranded (`6dcc2f61`, carried in D4). Close conditions: 0 naming PRs (9 name none). Intake: 5 checked, 0 without a row |
| Register reachability | `check_register_reachability.py --repo .` | 347 unmerged branches, 0 stranded, 0 pending in open PRs |
| After the edits, `--packet` on this file | `observation_log_lint.py <log> --packet <this file>` | see the PR's test plan |

The main edit was made by a script that refused to write unless:
- the log matched its backup's SHA-256 and was CRLF throughout (as written back);
- the id order was unchanged, with the new entries appended at the end;
- the OPEN set changed by exactly the 13 closures and the new OPEN entries;
- every entry not named in the edit was unchanged apart from trailing whitespace;
- the lint's non-reachability checks came back clean.

**`origin/main` moved during the review.** #420 merged at 09:04Z, after the main edit. Four Progress notes that called
#420 open were corrected by hand, and the Group A observation was appended by a second checked script. Everything in
this packet is re-resolved against `23f8f737`.

**Archival.** The 20 entries the 2026-11-03 review and its campaign closed moved verbatim to `archive/log-2026-11-10.md`,
each with a stub in `log.md`. This review's 13 closures stay in full text until the next review. DEFERRED entries stay
in the log, since the `--intake` check reads them.

## Skills pass

**Inventory.**
- One commit changed repo skills between the reviews: #416 (`adversarial-design-review` 1.3.0, `contract-first-tdd`
  1.6.0, `writing-plans-extras` 1.3.0). #420 changed none. `sync_agent_skills.py --check` at `23f8f737` shows every
  synced skill IDENTICAL and `pack pins: 12 checked, 0 drifted`.
- This review edits no repo skill, so the mirror is untouched.
- The applied edits are to research-observer, a global skill outside git with no repo mirror. No pack pins it.

**Cross-check of every OPEN group against the skills.**
- **A:** `contract-first-tdd` could carry A2's rule (a test that builds a production object with `object.__new__` also
  compares its attributes with a normal build). `tda-agent-safety-guardrails` covers agent bypasses only, and this one
  did not come from an agent session.
- **B:** `tda-diagnosing-computational-defects` fits B2's triage. No skill change.
- **C:** `writing-plans-extras` already has the shared-locations line. No change.
- **D:** `adversarial-design-review`, `writing-plans-extras` (S6 would change both).
- **E:** `.claude/rules/python.md` (a rules file, not a skill).
- **F:** no skill change; the fix is a hook.

No OPEN entry is on the SKILL lane. Every skill line proposed above comes from a PROCESS, GATE or INVARIANT entry, so an
autonomous run leaves it to you. The two SKILL-lane items, both in research-observer's review procedure, were logged and
applied in this review.

**Compliance against the active cross-cutting principles.** Both research-observer edits extend Principle 9 (a gate is
a measured claim with a watched failure). The step-3 line adds coverage to the measurement, and the `grep -a` line
follows Principle 11 (an adopted oracle must discriminate): a reader that silently prints nothing cannot tell "never
ran" from "unreadable". The step-1 edit follows "instructions ship after their mechanisms" in reverse: once the
mechanism is on `main`, the conditional goes. Nothing adds, weakens or removes a gate.

## Gate-liveness spot check

Two gates no packet has named before:

1. **`.claude/hooks/results-no-overwrite.sh`** (PreToolUse deny, on `Write`, `Edit` and `MultiEdit`).
   - Negative controls: 24 tests in `test_results_no_overwrite_hook.py`, run by admission-controls (`ci.yml` line 188).
   - Positive signal: 5,420 receipts since 2026-07-28, all `allow`. It has never denied in production, which fits no
     results having been written since July.
   - It does not sit on the path results take (Group F).
2. **`.claude/hooks/admin-bypass-guard.sh`** (PreToolUse, on Bash and PowerShell).
   - Negative controls: `test_admin_bypass_guard_hook.py`, run by admission-controls (`ci.yml` line 171).
   - Positive signal: 8,660 receipts, all `allow`. It has never refused, which fits no agent session having tried a
     bypass.
   - It guards agent sessions only. The #420 bypass left no agent receipt (Group A).

The three control files run here, these two plus `test_commit_msg_hooks.py`, passed: **58 tests**.
`install-git-hooks.py` reports every required hook present and executable in `.githooks`. No destructive probe was run.

**The receipt log needs `grep -a`.** Line 38966 (about 2026-10-28T23:08Z) starts with 67 NUL bytes, so a plain
`grep | uniq -c` tally printed "Binary file matches" and no counts. Read that way, every hook would show no receipts.
Research-observer's step 3 now says to use `grep -a`. The log is left as found, since it is the gates' only durable
evidence.

**Gates seen firing on live data this week:**
- **The suite lane** caught #420's broken test on `663388f8` ("new failure (not in baseline)"), and the nightly
  reported the writer-lock conflict twice.
- **The merge queue and ruleset:** four `pass` evaluations and three bypasses (#417, #412, #420).
- **The commit-msg results reminder** (#418): 13 `silent` receipts in two worktrees.
- **The observation-log lint:** 12 met close conditions and one stranded commit, all true.
- **SessionStart:** the hook-currency warning that this checkout was 6 commits behind `origin/main`, one of which
  changes `.githooks/commit-msg`. This review fast-forwarded `main` and committed from a worktree at `23f8f737`.

## Coverage question

"Did anything go wrong this week that no gate, contract or invariant caught?" Yes:

| What went wrong | Caught by | Observation |
|---|---|---|
| #420 merged by bypass past a red suite, and `main` fails two tests | the suite caught the test; nothing checked the bypass. Found by this review | `2026-11-10-bypass-merge-skipped-a-red-suite-and-left-main-red` (A) |
| An intermittent writer-lock conflict turned two nights red, and each issue closed itself | the nightly caught each night; nothing kept the count | `2026-11-10-nightly-writer-lock-flake-closes-its-own-issue-untriaged` (B) |
| Three WP9.3 note claims (an enforcement claim, a payload encoding, two wiring sites) were wrong after many review rounds | WP9.3-1's implementation and issue #415 | the three Group D entries |
| A directory-wide format pulled unrelated files into a commit | the session, by hand | `2026-11-09-main-holds-files-ruff-format-would-change` (E) |
| A script rewriting a result would pass every gate (no incident) | this review's spot check | `2026-11-10-results-no-overwrite-misses-the-path-results-take` (F) |
| A plain grep of the receipt log reads as zero receipts | this review | `2026-11-10-gate-spot-check-misread-receipts-and-skipped-path-coverage` (applied) |

None is a numerical or statistical failure, so none is a new invariant-battery item. A2 proposes a structural control
for a test, not a battery check.

## This review's actions

1. Found the previous packet (#412) and its campaign (#416 to #419). Re-resolved them against `origin/main`, checking
   each PR's base and merge-commit ancestry. Fast-forwarded the main checkout from `44b6f2b5` to `2d9aeddc`.
2. Ran `git fetch origin`, the observation-log lint with `--reachability`, `--close-conditions` and `--intake`, and the
   register-reachability lint, before and after the edits.
3. Read ruleset 20822054, the rule-suite evaluations, and the suite lane's scheduled, queue and PR runs. Read issues #413
   to #415 and the failing shard logs.
4. Re-resolved #420 when it merged during the review, and ran the failing test on `23f8f737`.
5. Measured `ruff format --check .` on `main` and checked the unformatted files against `contracts/` and
   `.research-system/`.
6. Checked MathUni, Counting Lives, codex_workflow and zktheoryweb for new material (none), and the scheduled-task list
   (S5 done).
7. Closed 13 entries, added nine Progress notes, logged five observations and archived 20, through checked scripts.
   Backup: `~/.claude/skill-updates/2026-11-10/log/log.md.before`.
8. Edited research-observer's review steps 1 and 3, with a dated backup.
9. Ran both spot-checked gates' controls and the commit-msg controls (58 passed), and `install-git-hooks.py`.
10. Updated `last-review-date.txt` to `2026-11-10`.
11. Opened this packet as a PR, from the linked worktree `.claude/worktrees/system-review-2026-11-10`.
