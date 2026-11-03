# Weekly Research-System Review — Resolution Packet

**Review date:** 2026-11-03. The scheduled `weekly-system-review` task ran on time (Tuesday, 08:43Z).

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md`. After this review it holds 289 entries, 19 of
them OPEN (OPEN, ESCALATED or PARTIALLY, per the lint).

**Scope:** every OPEN observation in the shared log, across the five trees named by the 2026-09-25 and 2026-10-02 owner
decisions: TDL, MathUni, the Counting Lives vault, codex_workflow and zktheoryweb. The other trees were read only. Two
OPEN entries belonged to zktheoryweb; both are fixed there and closed in this review. MathUni, Counting Lives and
codex_workflow have no new observation material and no OPEN entry. No tree outside the five appears, so there is no
scope finding.

**Decision owner:** Stephen

**Operating rule (unchanged since 2026-08-09):** approval authorizes a bounded verify-then-fix campaign on a reviewed
branch. It does not authorize direct changes to `main`, silent gate weakening, or acceptance without the named
controls.

**What this review changed.**
- **Record (observation log):**
  - **Closed 20 entries on verified evidence.** Eighteen had met close conditions, each re-checked against `origin/main`
    (`44b6f2b5`). Two zktheoryweb entries were fixed by stephendor/zktheoryweb#29. Two of the 20 carry a deferred limb,
    so their status is DEFERRED, not ACTIONED. See "This review's closures".
  - **Added dated Progress notes** to the 14 entries that stay open.
  - **Logged six observations.** Five are OPEN (Groups B, F, G and H). One, on the SKILL lane, was applied in this
    review.
  - **Archived** the 12 entries the 2026-10-27 review and campaign closed, to `archive/log-2026-11-03.md`.
- **Skill (applied, outside git):** step 1 of research-observer's weekly review now runs
  `tools/check_register_reachability.py`, which you approved for it on 2026-10-27 (Group B item 2). It also says how to
  resolve a stranded-hash finding whose content landed through another PR. Backup:
  `~/.claude/skill-updates/2026-11-03/research-observer/SKILL.md.before`.
- **Not changed:** any repo skill, and anything on the GATE, INVARIANT or PROCESS lanes. Nothing in the other trees.
  Everything below is a recommendation.

The pre-review log is at `~/.claude/skill-updates/2026-11-03/log/log.md.before`.

## Where last week's packet stands

You decided the 2026-10-27 packet (PR [#397](https://github.com/ZK-Theory/TDL/pull/397), 25 OPEN in eight groups) the
same day. The follow-up PRs all merged on 2026-10-27. Re-resolved against `origin/main` (`44b6f2b5`):

| Group | Decision | Built | State now |
|---|---|---|---|
| A. Lane required: the queue question | deferred | — | **Changed in practice.** Ten of the 13 updates to `main` since #397 passed through the merge queue. The precondition is now fully observed; only your ruleset edit remains (Group A below) |
| B. Stranded W11 record | approve 1–3 | #398, #400, #403 | Done. The register on `main` records limb 1 and KAN-84. The reachability lint is built; its first findings were never recorded (Group F) |
| C. Design review: open the artefact | approve skill text; defer the lint | #403 (#399 re-landed) | Done; five entries closed. The lint widening went to "the next Gate 7 planning pass", which has no record (Group H) |
| D. Verifier and fixture controls | approve 1–3 | #400, #401, #403 | Done; five entries closed. The commit-literal lint runs in no lane (Group F) |
| E. Record currency | approve E1–E5 | #400, #401, #403 | Done. E1's contract was deferred to Gate 7+ intake, which has no record (Group H) |
| F. Agent-guidance corrections | close both | — | Closed; archived this review |
| G. Live-run dispatch hygiene | approve | #403 | Done; two entries closed |
| H. Gate precision and liveness | approve both | #402 | Done. The hook glob leaves 14 other control files unrun (Group F). The advisory's precision went from 35 of 282 to 11 of 11 |
| Carried S1, S2, S4 | approve | — | All three done: the two one-time tasks are unregistered, the four Codex entries are DECLINED and archived, and the two `.bak` files are in `archive/` |

**One delivery failure, caught the same day.** #399 merged into its stacked base after that base had already merged as
#397, so its commits reached no path to `main`. The campaign caught it by hand and re-landed the work as #403. The
close-conditions lint would have counted #399 as delivered (Group B).

## How to use this packet

Tick one box per group. An approved group first re-resolves each mapped observation against current `main`. If an
observation is already compliant or superseded, record the evidence and close it. If it is still valid, build the named
mechanism with its negative control.

## Decision summary

| Group | OPEN | Recommended resolution | Decision |
|---|---:|---|---|
| A. Make the suite lane required | 3 | Your ruleset edit now; record queue-by-default as the practice | `[ ]` approve A1+A2 · `[ ]` A1 only · `[ ]` defer |
| B. Observation-log lint precision | 2 | Judge delivery by base branch and by content; read close-when clauses only where they state closure | `[ ]` approve B1–B3 · `[ ]` some (name which) · `[ ]` defer |
| C. Design-note evidence discipline | 5 | Four skill bullets, author and reviewer side; merge one duplicate | `[ ]` approve C1–C3 · `[ ]` C1 and C2 only · `[ ]` defer |
| D. Negative-control construction | 3 | A shared byte-identity helper; a non-owner fixture; one checklist line | `[ ]` approve D1–D3 · `[ ]` some (name which) · `[ ]` defer |
| E. Catalogue and plan interfaces | 2 | A precondition-home test with WP9.3-2; a W9 paths table after #411 | `[ ]` approve E1–E2 · `[ ]` defer |
| F. Controls and lints no lane runs | 2 | Derive the policy from every tools/contracts test; wire the commit-literal lint; rule on two branches | `[ ]` approve F1–F3 · `[ ]` F3 only · `[ ]` defer |
| G. Results-reminder scope | 1 | A commit-time advisory for results committed under another prefix | `[ ]` approve · `[ ]` defer |
| H. Deferrals with no landing record | 1 | One Gate 7+ intake list that planning sessions read | `[ ]` (a) new file · `[ ]` (b) 04-plan §4 · `[ ]` defer |
| This review's 20 closures | — | Keep them closed | `[ ]` keep · `[ ]` reopen (name which) |
| The research-observer step-1 edit | — | Keep it | `[ ]` keep · `[ ]` revert |
| S5. Three unregistered task directories | — | Remove them | `[ ]` approve · `[ ]` decline |

Total: 3 + 2 + 5 + 3 + 2 + 2 + 1 + 1 = **19**.

---

## A — Make the suite lane required (3)

`2026-10-02-full-suite-red-on-main-unseen`, `2026-10-03-shared-seam-change-merged-without-its-dependents`,
`2026-10-27-merge-queue-never-entered-every-main-update-bypasses`.

**Where it stands.** You deferred Group A on 2026-10-27, but the practice changed that day. The rule-suite API lists 13
updates to `main` from #397 (2026-10-27, 15:24Z) to #410 (2026-10-29):
- ten passed the ruleset through the merge queue (`result: pass`);
- three were owner bypasses: `f8a118a7` (#403, the re-landed skill PR), `1f0d8281` (#409) and `44b6f2b5` (#410), the
  last two docs-only decision PRs.

`suite-verdict` succeeded on every leg of the 2026-10-20 precondition:
- eight merge-queue runs, for PRs #401, #402 and #404 to #408 (latest run 40768222633). The queue entry for #408 took
  about nine minutes from queue to merge;
- six consecutive scheduled nights, 2026-10-28 to 2026-11-02 (latest run 41408890425), all at `44b6f2b5` from 10-29;
- PRs, as recorded last week.

Ruleset 20822054 still requires only contract-and-session-currency, require-active-currency-workflow, merge-admission
and admission-controls. Its `merge_queue` rule and its one bypass actor (the admin role, `pull_request` mode) are
unchanged.

**Defect.** The lane that would have caught the 195 failures of 2026-10-02 is green and runs on every queue entry, but
nothing requires it. A queue entry whose suite went red would still merge.

**Proposed action.**
- **A1.** You add `suite-verdict` to the ruleset's required checks. Agent sessions never write rulesets
  (`admin-bypass-guard.sh`). The first two entries close when the readback lists it.
- **A2.** Record option (a) from last week as the practice: ordinary merges go through the queue, and a bypass carries
  a reason. The third entry closes on that record. Last week's A1 bypass audit is then optional, because bypasses are
  rare again (three of 13); I recommend declining it.

**Controls.** The ruleset readback lists `suite-verdict`. The next queue entry reports `suite-verdict` as a required
check. No destructive probe: a red suite will show the refusal the first time it happens.

**Recommended decision:** approve A1 and A2.

**Decision:** `[ ]` approve A1+A2 · `[ ]` A1 only · `[ ]` defer

---

## B — Observation-log lint precision (2)

`2026-10-27-stacked-pr-merged-into-a-dead-base-reads-as-delivered`,
`2026-11-03-log-lint-judges-delivery-by-hash-and-pr-state` (new).

**Defect.** `tools/observation_log_lint.py` judges delivery by an identifier, not by what arrived. This review:
- `--reachability` reported four stranded commits, and **all four were false**. Each was a review commit on a
  never-pushed local `review/*` branch whose one file another PR carried byte-identical: #405, #406, and open PR #411.
- `--close-conditions` reported 21 met conditions. Two were false:
  - on the 2026-10-02 entry, the matched clause names #385 as a precondition (also noted last week);
  - on the stacked-PR entry, it read a quoted sentence about #399 from the Issue paragraph.
- The 19 true ones were true by luck. The lint still reads only a PR's `state`, so a PR merged into a dead base (#399)
  counts as delivered.

Every finding had to be re-verified by hand. A lint whose findings are routinely false teaches its reader to dismiss
them.

**Proposed action.**
- **B1.** Count a PR as delivered only when it merged with base `main`, or its merge commit is an ancestor of
  `origin/main`. Report anything else as "merged into <base>, not main".
- **B2.** For an unpublished cited commit, compare each file it changes with `origin/main` and with open PR heads.
  Report "landed by content in <ref>" when every blob matches.
- **B3.** Read close-when clauses only from Status, Progress and Resolution paragraphs, and let a clause mark a PR as a
  precondition so that the PR is not judged as the condition.

**Controls.**
- B1: a fixture state `{MERGED, base: docs/x}` is not met; `{MERGED, base: main}` is.
- B2: a fixture commit whose one file is byte-identical on main is "landed"; one whose file differs is "stranded".
- B3: a fixture entry that quotes a close-when clause in its Issue paragraph is not judged.

**Recommended decision:** approve B1–B3. They are one small PR to `tools/` with its tests.

**Decision:** `[ ]` approve B1–B3 · `[ ]` some (name which) · `[ ]` defer

---

## C — Design-note evidence discipline (5)

From the WP9.2 and WP9.3 review chain (2026-10-27 to 2026-10-29). **Every instance is fixed**, on `main` (#405) or in
open PR #411. Each lesson recurs a shape the 2026-10-27 skill text covers only in part.

| Entry | The lesson |
|---|---|
| `2026-10-27-design-note-chose-an-unprobed-shape` | When the chosen shape differs from the probed prototype, re-run the probe on the chosen shape; every probe case asserts its message |
| `2026-10-27-note-departed-from-a-carried-owner-item-silently` | Enumerate every register sentence naming the package ("Carried to WP9.2 …") and give each a keep or depart disposition |
| `2026-10-28-obligation-restated-open-though-accepted-text-fixed-it` | Before asking the owner to decide a rule, search the accepted texts (annex `derivation_rules`, contracts, register) for it |
| `2026-10-29-note-cited-a-truncated-row-range-and-built-an-owner-point-on-it` | Read a set from the parsed artefact (a YAML or JSON load), never from a line range read by eye |
| `2026-10-29-cited-a-list-from-a-truncated-read` | The author-side twin of the previous entry: an absence claim needs a read to the end of the enclosing item |

**Proposed action.**
- **C1.** Four bullets in `adversarial-design-review` "Claims About Another Artefact": probes, absence claims, owner-point
  rules and carried obligations. Matching author-side lines go in `writing-plans-extras`, under "Claims About Artefacts
  the Plan Does Not Own" and in the "Forward-Obligation Scan" step (`grep -n "<package>"
  03-decisions-and-open-questions.md`). Neither skill is pack-pinned.
- **C2.** Merge the two truncated-read entries into one, since they record one incident.
- **C3.** The §12.3 fixture-to-row table as a contract test, landing with WP9.3-2's PR (LR-020 is a WP9.3-2 row). Defer
  the carried-obligation lint to the intake list in Group H.

**Controls.** C1 is text. Its evidence is the next W9 design-note review: no absence claim without a parsed list, and
no owner point on a rule the accepted texts already fix. C3's control is the three-fixture reading of LR-020, which the
test must fail.

**Size.** `adversarial-design-review` is 302 lines. Last week's packet said the consolidation would shrink it; it grew
from 262, because the one subsection now carries nine lessons. C1 adds about 16 lines.

**Recommended decision:** approve C1–C3.

**Decision:** `[ ]` approve C1–C3 · `[ ]` C1 and C2 only · `[ ]` defer

---

## D — Negative-control construction (3)

| Entry | Instance | Open general control |
|---|---|---|
| `2026-10-28-byte-identity-controls-bypass-their-guard-despite-checklist` | Fixed in #406: one guard, `_is_derived_envelope`, that every control calls | The prose rule (`contract-first-tdd` 1.5.0) was already on `main` and failed once. A shared helper |
| `2026-10-28-authority-guard-tests-ran-only-as-the-owner` | Fixed in #408: `_non_owner_genesis` (actor-b), one refusal, one acceptance | A non-owner fixture in `tests/research_system/factories.py` and a checklist line |
| `2026-10-29-negative-control-vehicle-becomes-production-in-a-later-package` | Planned in #411: each control removes its row by monkeypatch | A checklist line: a control asserts its vehicle's precondition first |

**Proposed action.**
- **D1.** `assert_byte_identity(predicate, committed, refusals)` in `tests/research_system/contracts/`. The W9 envelope,
  W9 catalogue and W11 catalogue tests move onto it. Skip the lint: the helper is the artifact.
- **D2.** A `non_owner_grant` fixture, plus a `contract-first-tdd` line: a guard keyed on actor class or role is tested
  with a non-owner, because the owner short-circuits the classification.
- **D3.** A `contract-first-tdd` line: a control that relies on an absence asserts that absence before it acts.

**Controls.** D1: the helper fails when its predicate is weakened to an object comparison, and when it is called with a
pretty-printed or CRLF copy that the predicate accepts. D2: the non-owner refusal test fails when the guard is deleted.

**Recommended decision:** approve D1–D3, in WP9.3-1's PR or a small PR of their own.

**Decision:** `[ ]` approve D1–D3 · `[ ]` some (name which) · `[ ]` defer

---

## E — Catalogue and plan interfaces (2)

- `2026-10-28-catalogue-precondition-unrepresentable-in-closed-schema`. LR-016's precondition named data that no
  persisted payload could hold. It passed three review rounds, the verifier and O-8. Open PR #411 gives the instance a
  home (WP9.3 note §10.5, P-081 "derived ownership"). **E1:** a precondition-to-field table in
  `test_w9_expected_catalogue.py`, landing with WP9.3-2's PR. Its control is LR-016 at `7979e85a`, which must fail.
- `2026-10-28-shared-location-named-but-never-defined`. 06v named "the W9 evidence area" six times without a path.
  #411 proposes one (§11.1, owner point D) and P-081 records it. **E2:** after #411 merges, a "W9 paths" table in 06v,
  plus a `writing-plans-extras` line: a shared location gets its path at its first mention.

**Recommended decision:** approve E1 and E2. Both entries close when their artefacts merge.

**Decision:** `[ ]` approve E1–E2 · `[ ]` defer

---

## F — Controls and lints that no lane runs (2)

`2026-11-03-review-lints-built-but-run-by-no-lane`, `2026-11-03-gate-controls-outside-the-hook-glob-run-in-no-lane`
(both new).

**Defect.**
- **The three lints from #400 run nowhere.** #400 said the CI wiring would follow with Group H; #402 wired Group H only.
  No workflow, hook or review step runs `check_test_commit_literals.py`, `check_register_reachability.py` or
  `check_cited_decisions.py`, and no workflow runs their controls (`tests/tools/test_review_campaign_lints.py`).
- **Their first findings were never recorded.** #400's body said two branches "need an owner ruling". No log entry,
  packet or register entry recorded them, and there has been no ruling. The register lint still reports both today:
  - `codex/gate6-spec01-spec02-real-run` holds 41 register lines `main` lacks. Its tip `94f8bc1f` is the head of PR
    #258, which was closed unmerged;
  - `codex/review-missed-prs-241-243-base` (tip `ee3a0307`, on origin, no PR) holds 13.
- **Fourteen gate-control files run in no lane.** #402 derived the hook-control list from `tests/tools/test_*hook*.py`,
  so controls named after what they check are still invisible. Of the 45 files in `tests/tools/` and
  `tests/contracts/`, 15 run in no workflow, and one of those runs at pre-commit through a contract binding. The other
  14 include:
  - both control files of the pre-commit contract gate, `test_contract_hardening_gates.py` and
    `test_staged_contract_gate.py`. CI's `test_pre_commit_hook.py` uses a stand-in validator, so CI never runs the real
    one;
  - `test_w9_segmentation.py`, which tests the reference tool of the accepted segmentation contract (P-068).

  The full list is in the observation.

Nothing is red. This review ran the contract-gate, lint and results-reminder controls locally: 24 passed. They are
unwatched.

**Proposed action.**
- **F1.** Widen the policy test in `tests/tools/test_ci_platform_policy.py` to every `tests/tools/test_*.py` and
  `tests/contracts/test_*.py`. Each file runs in a named lane, or is listed in an exemption map with its reason. Add the
  14 files to admission-controls, or exempt them. Measure the lane's runtime before and after; the three files run here
  took 11 seconds.
- **F2.** Run `check_test_commit_literals.py` in admission-controls; it is clean today. The register lint is now in the
  review's step 1 (applied). It reads local branches, so CI would see only the remote ones.
- **F3.** Your ruling on the two branches: land each one's register content, or add the branch to the lint's KNOWN list
  with a reason.

**Controls.** F1: a new `tests/tools/test_x.py` that no workflow names fails the policy test. F2: the lint's own
negative controls in `test_review_campaign_lints.py` run in the same lane. F3: the register lint goes silent on both
branches.

`ci.yml` and the policy test are code-owned gate files, so F1 and F2 are your review.

**Recommended decision:** approve F1–F3.

**Decision:** `[ ]` approve F1–F3 · `[ ]` F3 only · `[ ]` defer

---

## G — Results-reminder scope (1)

`2026-11-03-results-vault-reminder-blind-to-script-written-results` (new, from this review's spot check).

**Defect.** `.claude/hooks/results-vault-reminder.sh` is live: it has 1,284 receipts and a control in admission-controls.
It has never advised in production, which is consistent with no file being added under `results/` since 2026-07-18.
The problem is coverage, for when result-bearing compute resumes:
- its matcher is `Write`, but results come from scripts run through Bash or PowerShell, as all 478 earlier JSON files
  did;
- at commit time, `prepare-commit-msg` exits early when a message is already prefixed, so `git commit -F` under
  `[PIPELINE]` gets no reminder;
- `commit-msg` checks only that a prefix is present.

**Proposed action.** A commit-time advisory, with a receipt: when a staged addition is under `results/` and the prefix
is not `[RESULT]`, `[NEGATIVE]` or `[DATA]`, print the vault reminder.

**Controls.** A staged `results/x_2026-11-03.json` under `[PIPELINE]` prints the reminder; under `[RESULT]` it is
silent.

**Recommended decision:** approve, as a small change. Waiting for compute to resume would need a reminder of its own.

**Decision:** `[ ]` approve · `[ ]` defer

---

## H — Deferrals with no landing record (1)

`2026-11-03-gate7-intake-deferrals-have-no-landing-record` (new).

**Defect.** Four approved deferrals route a limb to "Gate 7+ intake" or "the next Gate 7 planning pass":
- the plan file-map amendment, limb 1 of `2026-08-12-file-map-frozen-since-wp1`;
- the enumerable-contract planning rule, `2026-08-22-retired-procedure-kept-live-imperatives`;
- the supersession-currency contract, `2026-10-22-superseded-md-lags-reclassifying-results`;
- widening `check_retired_imperatives.py`, `2026-10-22-gate-definition-restates-owning-matrix-narrowly`.

No document in `docs/plans/` names any of them. You opened Gate 7 on 2026-10-22 (#391, P-063), and its planning passes
are happening now without them. The observation log is their only record, and planning sessions do not read it.

**Proposed action.** One intake list that planning sessions read, with a row per deferred limb: observation id, limb,
decision date and owning artefact. The weekly review checks that every log entry deferring to an intake has a row.
Choose where it lives:
- **(a)** a new file, `docs/plans/agentic-research-system/implementation/gate7-intake-deferrals.md`, linked from
  `04-plan` §4;
- **(b)** a section in `04-plan` §4.

06u is a dated scope note, so it should not be rewritten to hold a running list.

**Controls.** The weekly review's check reports a DEFERRED entry naming an intake that has no row. Its control is
today's four entries.

**Recommended decision:** (a).

**Decision:** `[ ]` (a) new file · `[ ]` (b) 04-plan §4 · `[ ]` defer

---

## This review's closures

Each closing Status names its evidence, and the previous Status is kept as a `Prior status:` line. They stay in full
text until the next review. If you disagree with any, tick "reopen" and I will restore it from the backup.

| Entry | Status | Evidence |
|---|---|---|
| `2026-10-21-owner-action-prompt-pack-has-no-already-done-precheck` | ACTIONED | #403 `f8a118a7`: `tda-large-workflow-supervision` 1.7.0 |
| `2026-10-21-gate7-brief-restated-superseded-and-closed-items` | ACTIONED | #400 `4a5a1300` (`check_cited_decisions.py`); #403 (`tda-task-brief-from-plan` 1.5.0) |
| `2026-10-21-jira-connector-errors-still-write-late` | ACTIONED | #403: `tda-large-workflow-supervision` 1.7.0 |
| `2026-10-22-superseded-md-lags-reclassifying-results` | DEFERRED | #401 `633ed58e` fixed `SUPERSEDED.md`; the contract waits on Group H |
| `2026-10-22-additive-addendum-leaves-unrederived-rows-stale` | ACTIONED | #403: `writing-plans-extras` 1.2.0, `tda-handoff` 1.5.0 |
| `2026-10-22-w11-owner-acceptance-stranded-on-unmerged-branch` | ACTIONED | #398 `f20061e4` (the register); #400 (the lint); #403 (the brief line) |
| `2026-10-22-reviewer-prescribed-identifiers-copied-unverified` | ACTIONED | #403: `adversarial-design-review` 1.2.0, "Prescribed corrections" |
| `2026-10-22-gate-definition-restates-owning-matrix-narrowly` | DEFERRED | #403 "Restated rules"; the lint widening waits on Group H |
| `2026-10-23-segmentation-contract-written-without-target-census` | ACTIONED | #403: "Selectors and parsers"; `schema-contract-design` 1.1.0 |
| `2026-10-23-respec-addendum-missed-materialized-fixture` | ACTIONED | #403: "Catalogue IDs" |
| `2026-10-23-schema-fixtures-used-one-placeholder-id-for-every-ref` | ACTIONED | #403: `schema-contract-design` 1.1.0, real-kind fixtures |
| `2026-10-23-accepted-tool-and-schema-claim-same-shape-without-a-binding-test` | ACTIONED | #403: `schema-contract-design` 1.1.0, producer-to-consumer binding |
| `2026-10-24-design-note-routed-commands-to-a-generic-path-without-reading-its-preparer` | ACTIONED | #403: "Precedent fidelity"; `writing-plans-extras` 1.2.0 |
| `2026-10-24-verifier-pin-chosen-by-its-subject` | ACTIONED | #403: `schema-contract-design` 1.1.0, pinned expected side |
| `2026-10-24-squash-merge-strands-sha-pinned-controls` | ACTIONED | #400 (`check_test_commit_literals.py`, 0 problems); #403 (`contract-first-tdd` 1.5.0) |
| `2026-10-27-gate-pass-set-wider-than-accepted-identity` | ACTIONED | #401: `test_w11_byte_identity_refuses_a_re_encoding_a_line_ending_or_a_new_created_at`; #403 |
| `2026-10-27-hook-control-tests-run-by-no-lane` | ACTIONED | #402 `7b132ee8`: `ci.yml` lines 193–196 and the derived list |
| `2026-10-27-research-context-advisory-fires-mostly-outside-the-repo` | ACTIONED | #402: all 11 advisories since the merge were for TDL files |
| `2026-10-27-phase3-promote-silently-drops-curated-connections` | CLOSED | Duplicate of an entry closed on stephendor/zktheoryweb#29 (`fab7c46`): the drop guard and six tests |
| `2026-10-27-handoff-prompt-assumed-exporter-emits-nodes` | ACTIONED | stephendor/zktheoryweb#29: `docs/phase3-pipeline.md`, "A `site:` block alone emits nothing" |

Every PR named above was checked for base `main` and a merge commit on `origin/main`, because of #399.

## Simplification sweep

- **Carried S1, S2 and S4 are done** (see the first table). Nothing is carried from last week.
- **S5 (new).** Three task directories are on disk but not registered as scheduled tasks:
  `~/.claude/scheduled-tasks/pr333-heavy-regression`, `research-system-lane-required-followup` and `weekly-skill-review`.
  Only `weekly-system-review` is registered. Remove the three. Deleting them is outside this run's remit.
- **No skill is proposed for removal.** `task-observer` stays as the fallback for environments without
  research-observer. No skill is superseded by a mechanism built this week.
- **Size watch.** `adversarial-design-review` is 302 lines (Group C).

---

## Completeness ledger

Computed, not assembled. Every OPEN id comes from `observation_log_lint.parse` over the live log after this review's
edits, and the table is checked with `tools/observation_log_lint.py <log> --packet <this file>`.

| Group | Count | IDs |
|---|---:|---|
| A | 3 | 2026-10-02-full-suite-red-on-main-unseen · 2026-10-03-shared-seam-change-merged-without-its-dependents · 2026-10-27-merge-queue-never-entered-every-main-update-bypasses |
| B | 2 | 2026-10-27-stacked-pr-merged-into-a-dead-base-reads-as-delivered · 2026-11-03-log-lint-judges-delivery-by-hash-and-pr-state |
| C | 5 | 2026-10-27-design-note-chose-an-unprobed-shape · 2026-10-27-note-departed-from-a-carried-owner-item-silently · 2026-10-28-obligation-restated-open-though-accepted-text-fixed-it · 2026-10-29-note-cited-a-truncated-row-range-and-built-an-owner-point-on-it · 2026-10-29-cited-a-list-from-a-truncated-read |
| D | 3 | 2026-10-28-byte-identity-controls-bypass-their-guard-despite-checklist · 2026-10-28-authority-guard-tests-ran-only-as-the-owner · 2026-10-29-negative-control-vehicle-becomes-production-in-a-later-package |
| E | 2 | 2026-10-28-catalogue-precondition-unrepresentable-in-closed-schema · 2026-10-28-shared-location-named-but-never-defined |
| F | 2 | 2026-11-03-review-lints-built-but-run-by-no-lane · 2026-11-03-gate-controls-outside-the-hook-glob-run-in-no-lane |
| G | 1 | 2026-11-03-results-vault-reminder-blind-to-script-written-results |
| H | 1 | 2026-11-03-gate7-intake-deferrals-have-no-landing-record |
| **Total** | **19** | |

---

## Lint and ledger check

| When | Tool | Result |
|---|---|---|
| Before this review's edits | `observation_log_lint.py --reachability . --close-conditions .` at `44b6f2b5` | `283 observation(s): 34 OPEN`. Reachability: 55 hashes, 4 stranded, all false (Group B). Close conditions: 21 checked, 21 met, 19 true and 2 false |
| After the edits | same | `289 observation(s): 19 OPEN`. Reachability: 26 hashes, 0 stranded. Close conditions: 2 checked, 2 met, both the false positives carried in Group B |
| After the edits, `--packet` on this file | `observation_log_lint.py <log> --packet <this file>` | see the PR's test plan |
| The three #400 lints, run by hand | `check_test_commit_literals.py`, `check_register_reachability.py`, `check_cited_decisions.py` | 0 problems; 3 findings for 2 branches (Group F); notes on older handoffs only |

The main edit was made by a script that refused to write unless:
- the log matched its backup's SHA-256, and was CRLF throughout (as written back);
- the id order was unchanged, with the six new entries appended at the end;
- the OPEN set changed by exactly the 20 closures and five additions;
- every entry not named in the edit was unchanged apart from trailing whitespace;
- the lint's non-reachability checks came back clean.

One later replacement corrected a single sentence in a new entry. I had called `94f8bc1f` local only, but it is the head
of the closed PR #258.

**Archival.** The 12 entries the 2026-10-27 review and campaign closed moved verbatim to `archive/log-2026-11-03.md`,
each with a stub in `log.md`. This review's 20 closures stay in full text until the next review.

## Skills pass

**Inventory.**
- One commit changed repo skills between the reviews: #403 (seven skills). `sync_agent_skills.py --check` shows every
  synced skill IDENTICAL and `pack pins: 12 checked, 0 drifted`.
- This review edits no repo skill, so the mirror is untouched.
- The one applied edit is to research-observer, a global skill outside git with no repo mirror. `git grep
  "research-observer" .research-system/` is empty, so no pack pins it.

**Cross-check of every OPEN group against the skills.**
- **A, B, F, G:** no skill change. The fixes are a ruleset edit, a lint, CI wiring and a hook.
- **C:** `adversarial-design-review`, `writing-plans-extras`.
- **D:** `contract-first-tdd`, plus test helpers.
- **E:** `writing-plans-extras`, plus a contract test.
- **H:** research-observer, which would gain the intake-row check once the list exists.

No OPEN entry is on the SKILL lane. Every skill line proposed above comes from a PROCESS, GATE, INVARIANT or RECORD
entry, so an autonomous run leaves it to you. The one SKILL-lane item, the review's step 1, was logged and applied in
this review.

**Compliance against the active cross-cutting principles.** The research-observer edit applies Principle 9 (a gate is
a measured claim with a watched failure): the review now runs a lint you approved for it. It also follows the rule that
metadata is suspicion and content is verdict: a stranded hash is resolved by comparing content. It adds, weakens and
removes no gate.

## Gate-liveness spot check

Two gates no packet has named before:

1. **The pre-commit contract gate** (`.githooks/pre-commit` calls `run_staged_contract_gate.py`, which runs
   `.claude/hooks/contract_binding_check.py`).
   - Negative controls: `test_staged_runner_propagates_candidate_validator_failure` and 11 hardening tests. **No CI lane
     runs them** (Group F). CI's `test_pre_commit_hook.py` uses a stand-in validator.
   - Positive signal: none recorded. The gate writes no receipt.
   - `install-git-hooks.py`: every required hook present and executable in `.githooks`; `core.hooksPath` is `.githooks`.
2. **`.claude/hooks/results-vault-reminder.sh`** (advisory, PostToolUse on `Write`).
   - Negative control: `test_results_vault_reminder_receipt_records_advise_and_silent`, run by admission-controls.
   - Positive signal: 1,284 receipts, all `silent`. It has never advised in production, which fits no results having
     been written since July. Its scope misses script-written results (Group G).

The controls ran locally in this review: **24 passed**. No destructive probe was run.

**Gates seen firing on live data this week:**
- **The merge queue and ruleset:** ten `pass` evaluations (Group A).
- **The register-reachability lint**, run by hand: three true findings for two branches whose register content `main`
  lacks (Group F).
- **The research-context advisory:** 11 advisories since #402, all for TDL worktree files.
- **SessionStart:** the review-staleness line ("last ran 2026-10-27 (7 days ago)") and the hook-currency line.

## Coverage question

"Did anything go wrong this week that no gate, contract or invariant caught?" Yes:

| What went wrong | Caught by | Observation |
|---|---|---|
| A stacked PR (#399) merged into a dead base; twelve close conditions would have read it as delivered | the campaign, by hand (`git merge-base --is-ancestor`) | `2026-10-27-stacked-pr-merged-into-a-dead-base-reads-as-delivered` (B) |
| Every reachability finding, and two close-condition findings, were false | this review, by comparing blobs | `2026-11-03-log-lint-judges-delivery-by-hash-and-pr-state` (B) |
| Three approved lints ran nowhere for a week, and their first findings sat in a PR body | this review, re-resolving the campaign | `2026-11-03-review-lints-built-but-run-by-no-lane` (F) |
| The contract gate's controls, and twelve other control files, run in no CI lane | this review's spot check | `2026-11-03-gate-controls-outside-the-hook-glob-run-in-no-lane` (F) |
| Four approved deferrals have no record at their destination, and Gate 7 is open | this review, closing an entry | `2026-11-03-gate7-intake-deferrals-have-no-landing-record` (H) |
| The W9 chain's nine defects in candidate notes and tests | independent reviewers, during the week | logged at the time (C, D, E) |
| A byte-identity control written beside its guard, after the prose rule was on `main` | the WP9.2-1 reviewer's mutation run | `2026-10-28-byte-identity-controls-bypass-their-guard-despite-checklist` (D) |

None is a numerical or statistical failure, so none is a new invariant-battery item. Two INVARIANT-lane entries (Group
E's LR-016 entry and Group C's truncated-read entry) propose contract tests, not battery checks.

## This review's actions

1. Found the previous packet (#397) and its follow-ups (#398, #400 to #403). Re-resolved them against `origin/main`
   (`44b6f2b5`), checking each PR's base and merge-commit ancestry.
2. Ran `git fetch origin` and the lint with `--reachability . --close-conditions .`, before and after the edits.
3. Ran the three #400 lints by hand.
4. Read ruleset 20822054, the rule-suite evaluations since 2026-10-27, and the suite lane's merge-queue and scheduled
   runs.
5. Compared each "stranded" review commit's file with `origin/main` and with #411's branch: all byte-identical.
6. Re-resolved the W9-chain entries against `main` and open PR #411, and the zktheoryweb entries against
   stephendor/zktheoryweb#29 (read only).
7. Checked MathUni, Counting Lives and codex_workflow for new observation material (none) and the scheduled-task list
   (S1 done).
8. Closed 20 entries, added 14 Progress notes, logged six observations and archived 12, through a checked script.
   Backup: `~/.claude/skill-updates/2026-11-03/log/log.md.before`.
9. Edited research-observer's review step 1, with a dated backup.
10. Ran both spot-checked gates' controls and the review lints' controls (24 passed), and `install-git-hooks.py`.
11. Updated `last-review-date.txt` to `2026-11-03`.
12. Opened this packet as a PR, from the linked worktree `.claude/worktrees/system-review-2026-11-03`.
