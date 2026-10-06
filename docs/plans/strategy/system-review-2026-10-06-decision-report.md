# Weekly Research-System Review — Resolution Packet

**Review date:** 2026-10-06 (scheduled `weekly-system-review`, autonomous run).

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md`. After this review it
holds 203 entries, 15 of them OPEN (OPEN, ESCALATED or PARTIALLY, per the lint since #317).

**Scope:** every OPEN observation in the shared log, across the five trees named by the
2026-09-25 and 2026-10-02 owner decisions: TDL, MathUni, the Counting Lives vault, codex_workflow
and zktheoryweb. The non-TDL trees were read only. Every OPEN item belongs to one of the five
trees, so there is no scope finding. MathUni and Counting Lives have no OPEN items.

**Decision owner:** Stephen

**Operating rule (unchanged since 2026-08-09):** approval authorizes a bounded
verify-then-fix campaign on a reviewed branch. It does not authorize direct changes to
`main`, silent gate weakening, or acceptance without the named controls.

**What this review changed.**
- **Applied (SKILL lane):** one rule in the global `research-observer` skill. When an OPEN item
  says a limb is built, bound or waiting on you, the review checks that the named commit is on
  `origin/main` or heads an open PR before repeating the claim. See Group A for why.
- **Applied (RECORD lane):** the memory index's CONVENTIONS lines, which still described the
  pre-2026-07-18 hardlink, and its companion memory.
- **Logged:** four observations. Two are OPEN: stranded branches (PROCESS) and the pinned-skill
  edit (GATE). Two are ACTIONED: the two fixes above.
- **Annotated:** added a dated review note to the two entries whose cited commits are not on
  `main`.
- **Archived:** 57 closed entries that still held full text. They moved to
  `archive/log-2026-10-06.md` with a stub under each id; `log.md` went from 2,622 to 1,769 lines.
- **Staged, not applied:** four skill edits, in `~/.claude/skill-updates/2026-10-06/`. Each comes
  from a GATE, INVARIANT or PROCESS item, which an autonomous run may not apply.
- **Not changed:** anything on the GATE, INVARIANT or PROCESS lanes, and anything in the other
  trees. Everything below is a recommendation.

## Where last week's packet stands

The 2026-09-29 packet (PR [#308](https://github.com/ZK-Theory/TDL/pull/308)) reached you and was
decided on 2026-10-02. Its campaigns were built and merged between 2026-10-03 and 2026-10-06.
Of its 25 OPEN items:
- **19 are ACTIONED.** Each Status line names its PR and merge commit.
- **2 are DEFERRED** to the 06s D5 process (Campaign P).
- **4 are still OPEN:**
  - Q, the full suite, in progress (Group B);
  - L, Codex hook parity, with no decision found (Group F);
  - the codex_workflow item, which you decided to keep open (non-TDL section);
  - the TDL residual (Group A).

| PR | Campaign | Merge commit | State |
|---|---|---|---|
| [#311](https://github.com/ZK-Theory/TDL/pull/311) | J (test cost) | `cfb89656` | merged; runner budget enforcement stays with the 06s process under P-058 |
| [#312](https://github.com/ZK-Theory/TDL/pull/312) | M (sweep cadence) | `f8acf21c` | merged; comment-triggered runs now fire in seconds |
| [#313](https://github.com/ZK-Theory/TDL/pull/313) | K (`run_git` cause) | `06f9a7a1` | merged |
| [#314](https://github.com/ZK-Theory/TDL/pull/314), [#316](https://github.com/ZK-Theory/TDL/pull/316) | N (`results-no-overwrite`) | `3600b33d`, `7d834f4c` | merged |
| [#315](https://github.com/ZK-Theory/TDL/pull/315) | S (hook currency) | `e1807d0e` | merged; it printed its positive signal at this run's start |
| [#317](https://github.com/ZK-Theory/TDL/pull/317), [#318](https://github.com/ZK-Theory/TDL/pull/318) | R (round-3 follow-ups) | `4a588ce8`, `2f8069f4` | merged |
| #320–#324, #326, #327, #330 | Q triage | various, 2026-10-06 | merged |
| [#325](https://github.com/ZK-Theory/TDL/pull/325), [#328](https://github.com/ZK-Theory/TDL/pull/328), [#329](https://github.com/ZK-Theory/TDL/pull/329) | Q triage and lane | — | **open**; see Groups B and C |

The non-TDL closures were spot-checked read-only:
- MathUni PRs #33, #34 and #35 (`37aa314e`, `80b98eb4` and `4d057729`) are on MathUni's
  `origin/main`.
- zktheoryweb PR #20 (`9359394`) is on its `main`.
- Counting Lives' `citation_preflight.py` sits beside the vault.

**Three things to know before you merge anything:**
1. #325, #328 and #329 each show a red `merge-admission`. The cause is the same in all three: the
   check's verdict line reads "chatgpt-codex-connector has not reviewed or reacted on this head".
   Each needs an `@codex review` on its current head.
2. #328 partly re-introduces the pattern its own observation warns about (Group C).
3. The `.apm/worktrees/06s-acceptance` worktree holds the only copy of Group A's branch. Leave it
   out of the next worktree sweep until Group A is decided.

## How to use this packet

Tick one box per group unless the group says its boxes combine. An approved group first
re-resolves each mapped observation against current HEAD and the owning tree. If it is already
compliant or superseded, record the evidence, mark it ACTIONED or DECLINED, and archive it. If it
is still valid and in scope, build the named mechanism with its negative control. If another
tree or process owns it, record the exact owner and keep only that remainder open.

## Decision summary

| Group | OPEN | Recommended resolution | Decision |
|---|---:|---|---|
| A. Owner-decided work stranded on local branches (new) | 3 | Land the 06q fence and gate and the 06t proposal as PRs; add a reachability check to the lint | `[ ]` approve 1–3 · `[ ]` 1–2 only · `[ ]` defer · `[ ]` decline |
| B. research_system suite lanes | 3 | Merge #329 last; make it required after its week; add a pack-pin check to Gate 0 | `[ ]` approve 1–4 · `[ ]` 1–2 and 4, no Gate 0 check · `[ ]` defer |
| C. Triage test fixes in review | 2 | Merge #325; before merging #328, split its three widened loops; keep the admission-check limb open | `[ ]` approve 1–3 · `[ ]` merge both as they stand · `[ ]` defer |
| D. Race in `identity.py` and race-test evidence | 1 | Fix the path comparison with 50-run evidence; apply the staged `contract-first-tdd` edit | `[ ]` approve both · `[ ]` fix only · `[ ]` defer |
| E. Branch-set mergeability at handback | 1 | Apply the staged `tda-large-workflow-supervision` edit; build the tool only if needed | `[ ]` edit + tool · `[ ]` edit only · `[ ]` defer · `[ ]` decline |
| F. Codex hook parity (carried) | 1 | A probe from a Codex session, then a single source or deliberate removal | `[ ]` approve · `[ ]` defer · `[ ]` decline |
| G. Record hygiene: two closures | 2 | Close both on the evidence below | `[ ]` close both · `[ ]` close one (name it) · `[ ]` keep open |
| Non-TDL: zktheoryweb | 1 | Make the Zotero refresh opt-in; a build test proves the cache is untouched | `[ ]` route as proposed · `[ ]` pre-commit check instead · `[ ]` defer |
| Non-TDL: codex_workflow | 1 | Unchanged; you decided on 2026-10-02 to keep it open | `[ ]` keep open · `[ ]` decline |

Total: 3 + 3 + 2 + 1 + 1 + 1 + 2 + 1 + 1 = **15**.

---

## A — Owner-decided work stranded on local branches (3, new)

**Defect.** `2026-10-06-owner-decided-work-stranded-on-local-branches`. On 2026-09-08 you
decided to land the 06q §4 retirement fence "as a separate follow-up PR after #271 merges". #271
merged that evening. Two commits never left the local branch `repo/06q-section4-retirement`:
- the fence, `8fb7c9a`;
- the retired-imperatives gate built with it, `526790b`: `tools/check_retired_imperatives.py`,
  contract `retired-plan-imperatives-quoted`, run by pre-commit Gate 2.

The branch has no upstream, no remote branch and no PR. On `origin/main` (`4003421a`):
- `tools/check_retired_imperatives.py` does not exist;
- no contract names `retired-plan-imperatives-quoted`;
- 06q still has only its banner above line 7's live "**Authority:** sole active Gate 6 recovery
  and closure plan. Do not create a 06s or another master plan."

The 06t pin-binding proposal from the same day (`e4ca91a`) is only on the local branch
`docs/06t-pin-binding-proposal`, which was never pushed. Its log entry calls it "on Stephen's
desk". Last week's packet repeated "the retirement-quoting limb is built and bound (pre-commit
Gate 2)" as current state. I did not check that claim last week. I have now changed the review
skill so the next review does (see "This review's actions").

Two observations carry the unbuilt remainders and move here with it:
- `2026-08-22-retired-procedure-kept-live-imperatives` (ESCALATED). Its gate limb is the
  stranded `526790b`. Its enumerable-contract limb was never started.
- `2026-08-12-file-map-frozen-since-wp1` (PARTIALLY). Limb 2 is the stranded 06t proposal.
  Limb 1, a plan file-map amendment on supersession, was never started.

**Proposed action.**
1. Rebase `8fb7c9a` and `526790b` onto current `main` in a fresh worktree. Re-run R1/R2 against
   today's plan set: 06s and later documents changed after 2026-09-08, so R1 may flag new
   supersession claims. Then open the PR.
2. Push `e4ca91a` and open it as a PR for your decision. The amendment window it relies on is
   still open: `.research-system/contracts/artefact-authority-interface.v1.yaml` line 3 reads
   `candidate_state: proposed`.
3. Add a reachability check to `tools/observation_log_lint.py`. It resolves every commit hash an
   OPEN, ESCALATED or PARTIALLY entry names, and reports any that is neither reachable from
   `origin/main` nor an open PR's head.
4. Keep the two never-started limbs tracked under their entries: the enumerable-contract limb
   and the file-map amendment.

**Controls.**
- (1) R2's recorded watched failure re-run on the rebased branch: unquote one line of 06q §4 and
  expect `[R2-unquoted]`, exit 1; restore it and expect a clean exit.
- (3) A fixture entry naming a commit on a local-only branch is reported. One naming a commit on
  `main`, or on an open PR's head, is not.

**Recommended decision:** approve 1–3. Items 1 and 2 carry out decisions you have already
made, four weeks late.

**Decision:** `[ ]` approve 1–3 · `[ ]` approve 1–2 only · `[ ]` defer · `[ ]` decline (the
fence and the proposal are abandoned; both limbs close as DECLINED)

---

## B — research_system suite lanes (3)

**Defect.**
- `2026-10-02-full-suite-red-on-main-unseen` (Campaign Q). Eight triage PRs merged today
  (#320–#324, #326, #327 and #330). #325 and #328 are still open, and #329's description expects
  three known failures once all of them land. #329 adds `research-system-suite.yml`:
  - Windows only, and advisory for its first week;
  - nightly at 01:30 UTC, and on PRs for the affected files;
  - eight duration-balanced shards;
  - a shrink-only known-failure list of three WP6.3 tests (your option B, `ed70f296`).
- `2026-10-03-shared-seam-change-merged-without-its-dependents` is #329's PR-time selector:
  dependents through the import graph of both trees, every test when a `conftest.py` changes,
  and every contract test and pack loader when a `.research-system`-pinned path changes.
- `2026-10-06-review-skill-edit-broke-a-pack-pinned-skill` (new, from the coverage question).
  #307, Campaign I of the 2026-09-23 review, added eight lines to `research-assurance-triage`,
  which the WP6.3 pack pins by git blob. The pack became unconsumable and 48 tests went red. No
  gate saw it at PR time, and #326 relocated the text on 2026-10-06. Gate 0
  (`sync_agent_skills.py --check`) compares the two skill trees, not the pins. Six skills are
  pinned.

**Proposed action.**
1. Merge #329 last, after #325 and #328, as its own merge-order note says, once Codex has
   reviewed its head.
2. Build the two follow-ups you set on 2026-10-05: the lane becomes required after its advisory
   week, and `ci.yml` watches the nightly schedule's age. The race in Group D will flake that
   lane, so fix D before the lane becomes required.
3. Add a pin check to `sync_agent_skills.py --check`. It reads every `repository_path`/`git_blob`
   pin under `.research-system/` and fails when a synced skill's blob differs from its pin,
   naming the pin and the owner decision required.
4. Apply the staged companion text: `tda-skill-authoring-workbench` 1.1.0 and a row in
   `research-observer`'s routing table. Both say to check for a pin before editing a skill. I
   checked that no staged edit touches a pinned skill.

**Controls.**
- (1)–(2): #329's own controls. Its mutation runs turned the tool controls red, including all 9
  real culprit seams, and its baseline fails on any listed entry that passes.
- (3): a fixture tree whose pinned skill has one extra line fails Gate 0, and the unedited tree
  passes.

**Close-out.**
- Q and the shared-seam entry close when #329 has merged and the lane is required.
- The pinned-skill entry closes when the Gate 0 check merges, or when you decline it and rely on
  #329 alone.

**Recommended decision:** approve 1–4.

**Decision:** `[ ]` approve 1–4 · `[ ]` approve 1, 2 and 4, without the Gate 0 check · `[ ]` defer

---

## C — Triage test fixes in review (2)

**Defects and their PRs.**
- `2026-10-03-tests-and-live-store-bound-to-machine-state`. #325 covers limb (2):
  - test stores get their own approved foundation;
  - `test_foundation_origin_witness_contract` is marked `live_store`, per your 2026-10-05
    decision;
  - a missing manifest schema root raises `ConfigurationError` instead of a raw
    `FileNotFoundError`.

  Two parts stay open. **Limb (1)** is not in #325: an admission check refusing an approved
  `schema_root` or code root under `.codex/worktrees`, `.claude/worktrees`, `.apm/worktrees` or a
  temp directory. And **the live store's approved restore binding still points into the deleted
  547f worktree**, which P-058 keeps unchanged.
- `2026-10-03-tamper-tests-pinned-to-check-order`. #328 rewrites the control-plane tamper so that
  only the hash chain can catch it. It also splits two Discovery guard tests the way the
  observation asks: assert the generic refusal, isolate the driver with `_isolate_discovery_driver`,
  then assert the specific guard.

  In three other loops it does the opposite. It adds `event schema validation failed` to the
  accepted alternatives:
  - the assay verdict, about line 2797;
  - the spike cross-namespace `DecisionProposed` and `ReviewRequested` cases, lines 4684 and 4690;
  - the spike verdict, line 4730.

  That widening is what the observation says would hide the lost coverage. I searched #328's head
  as text and ran no tests. `invalid Discovery review request` (`review_decision.py:164`) appears
  only inside that widened alternation, so after #328 no test shows that guard firing.
  `invalid Discovery review verdict` keeps one sole-message test, at line 2698.

  The rule is already written down. `contract-first-tdd` says "A negative control names the layer
  that must refuse". So this is a written rule that was not followed, and the fix is a mechanical
  control rather than more prose.

**Proposed action.**
1. Merge #325. Keep limb (1) open under the entry as a follow-up admission check.
2. Before merging #328, split the three widened loops the way #328 already splits the other two,
   or record for each case why the specific guard cannot be reached.
3. Add the observation's mutation control to #328's evidence. Delete each named semantic guard in
   turn (`review_decision.py:164`, `:250` and `:283`) and show that a test fails.

**Controls.**
- (1) A fixture approval pointing into `.codex/worktrees` is rejected.
- (3) Each deleted guard turns at least one named test red.

**Recommended decision:** approve 1–3.

**Decision:** `[ ]` approve 1–3 · `[ ]` merge both as they stand (record that three Discovery
guards lose direct coverage) · `[ ]` defer

---

## D — Race in `identity.py` and race-test evidence (1)

**Defect.** `2026-10-06-race-fix-verified-with-three-runs-flakes-one-in-five`. #324 merged on
three green runs. The same test then failed 4 of 20 isolated runs.
`research_system/store/identity.py:254–261` compares `resolved` with
`origin_witness_path(...).resolve(strict=False)`. On Windows the two sides can differ in the
extended-length `\\?\` form while another thread creates the file. **No open branch touches
`identity.py`**: none of #325, #328 and #329 changes it. So once #329's nightly lane runs, this
test will fail intermittently there as an unlisted failure.

**Proposed action.**
1. A fix PR. Resolve both sides of the comparison through the same `_require_physical_path`
   resolver, or compare file identity once the file exists. Evidence: 50 of 50 isolated runs
   green, and the parent failing at least once in the same 50.
2. Apply the staged `contract-first-tdd` 1.3.0 edit,
   `~/.claude/skill-updates/2026-10-06/contract-first-tdd/proposed.diff` (41 lines). A race test
   reports passes out of N isolated runs. With no failures in N runs, the 95% upper bound on the
   failure rate is 1 − 0.05^(1/N): 63% at N = 3, about 6% at N = 50. The edit adds a checklist
   line and a self-test question. The skill is not pack-pinned, and its staged base is
   byte-identical to `main`.

**Controls.** (1) as stated. (2) After the copy, `sync_agent_skills.py --check` passes and the
mirror is identical.

**Recommended decision:** approve both, with the fix landing before #329's lane becomes required.

**Decision:** `[ ]` approve both · `[ ]` approve the fix only · `[ ]` defer

---

## E — Branch-set mergeability at handback (1)

**Defect.** `2026-10-05-parked-fix-branches-drift-out-of-mergeability`. Nine branches pushed
green on 2026-10-03 were no longer all mergeable on 2026-10-05: two conflicted with `main`, and
two sibling pairs conflicted with each other. Only a `git merge-tree` sweep showed it.
`tda-large-workflow-supervision` says "declare merge order/bases" but nothing about re-checking
at handback.

**Proposed action.**
1. Apply the staged `tda-large-workflow-supervision` 1.5.0 edit,
   `~/.claude/skill-updates/2026-10-06/tda-large-workflow-supervision/proposed.diff` (36 lines).
   At handback, check every branch against the current base and every pair against each other
   with `git merge-tree --write-tree`. Record a merge order for each conflicting pair, and re-run
   the binding tests where a merge touches pinned or shared surfaces. It also adds a checklist
   line.
2. Optional: `tools/branch_set_mergeability.py`.

**Controls.** For (2): two branches editing one hunk are reported. For (1):
`sync_agent_skills.py --check` stays identical.

**Recommended decision:** the edit only. Build the tool when the next parallel handback needs
it. The triage PRs already carry merge-order notes by hand.

**Decision:** `[ ]` edit + tool · `[ ]` edit only · `[ ]` defer · `[ ]` decline

---

## F — Codex hook parity (1, carried from Campaign L)

**Defect.** `2026-09-25-codex-live-hooks-are-stale-sibling-copies`, unchanged.
`.codex/hooks.json` still wires four old copies by absolute path. Nothing under `.codex/` has
changed since #303. I found no decision on Campaign L in the repo, in the 2026-10-05 daily note
or in the log.

**Proposed action.** As last week. From a Codex session, write a W₁ line to a scratch `papers/`
file and watch what happens.
- **Outcome A, Codex runs the hooks:** point `.codex/hooks.json` at the `.claude/hooks` scripts,
  and add an identity test.
- **Outcome B, Codex ignores them:** first show the wiring is ignored, with a sentinel hook that
  leaves no trace. Then delete the wiring and the copies, record the boundary in
  `tda-agent-safety-guardrails`, and add a test that `.codex/hooks.json` names no hook script.

**Controls.** As in the 2026-09-29 packet, conditional on the outcome.

**Recommended decision:** approve. The probe needs a Codex session.

**Decision:** `[ ]` approve · `[ ]` defer · `[ ]` decline

---

## G — Record hygiene: two closures (2)

Both entered the ledger because #317 made ESCALATED and PARTIALLY count as open.

- `01KZK2BCXT7EKFZ6ZM2AMKFXJR` (ESCALATED since 2026-08-09). This is the fourth packet to
  recommend closing it as superseded, and the first where it is in the ledger. Re-verified on
  2026-10-06:
  - G-RM-8 is decided: `06h-g-rm-8-grandfather-decision-3c75d3d-2026-08-09.json`.
  - `research_system/projection/grandfather.py` is pinned to that decision file.
  - A search for `no_prior_store`, `no-prior-store` and `NO_STORE` across `research_system/`,
    `contracts/` and `.research-system/` returns nothing. The option list it targeted has no
    consumer.
- `01KZW7B1GJ6VSA0Y0X74WJ0S5Y` (PARTIALLY ACTIONED since 2026-08-18). Its unbuilt half was
  re-filed as `2026-08-18-broad-repo-ci-remains-disabled`. That entry was ACTIONED on 2026-09-25:
  `ci.yml` is active and the whole-repo lint is clean. The pytest remainder is now Group B.
  Nothing is left that this entry owns.

**Proposed action.** Close `01KZK2BC…` as DECLINED (superseded), citing the evidence above.
Close `01KZW7B1…` as ACTIONED, pointing to the re-filed entry and to `archive/log-2026-08-18.md`.

**Controls.** None; this is a record correction. The lint checks that each closing stamp names
an artifact.

**Recommended decision:** close both.

**Decision:** `[ ]` close both · `[ ]` close one (name it) · `[ ]` keep open

---

## Non-TDL: zktheoryweb (1) — read-only verification

`2026-10-05-build-mutates-tracked-zotero-cache`. Verified on 2026-10-06:
- `astro.config.mjs:20–31` calls `fetchZoteroLibrary()` in `astro:build:start` on every build.
  With credentials present, that rewrites the tracked `src/data/zotero-library.json`.
- The repo has no git hooks: `core.hooksPath` is unset and `.git/hooks` holds only samples. It
  has no CI workflows.
- The instance itself was handled: the refresh was committed as its own PR (#22, `c4baff5`).

**Proposed action (zktheoryweb session).** Make the prefetch opt-in: `ZOTERO_REFRESH=1`, or
Netlify's `NETLIFY=true`, since that build output is never committed. Keep
`npm run fetch:zotero` for deliberate refreshes. **Control:** a `scripts/build-guards.test.ts`
case runs the build hook without the flag and asserts that the cache bytes are unchanged.

**Decision:** `[ ]` route to a zktheoryweb session as proposed · `[ ]` prefer the entry's
pre-commit check instead · `[ ]` defer

## Non-TDL: codex_workflow (1) — read-only verification

`01M044JXYSPP0VXH15TEZVCNA3`. Your 2026-10-02 decision was to keep it open until a session works
in the codex_workflow source repo. Re-verified on 2026-10-06:
- the installed copy is still `1.1.2` and is not a git repo;
- `end_of_session.md` line 3 still runs closure "once after every substantive Medium or Heavy"
  task, with no freshness binding.

No change.

**Decision:** `[ ]` keep open (as decided) · `[ ]` decline

---

## Completeness ledger

Computed, not assembled. Every OPEN id comes from `observation_log_lint.parse` over the live log
after this review's edits, and the table is checked with
`tools/observation_log_lint.py <log> --packet <this file>` (see "Lint and ledger check").

| Group | Count | IDs |
|---|---:|---|
| A | 3 | 2026-10-06-owner-decided-work-stranded-on-local-branches · 2026-08-22-retired-procedure-kept-live-imperatives · 2026-08-12-file-map-frozen-since-wp1 |
| B | 3 | 2026-10-02-full-suite-red-on-main-unseen · 2026-10-03-shared-seam-change-merged-without-its-dependents · 2026-10-06-review-skill-edit-broke-a-pack-pinned-skill |
| C | 2 | 2026-10-03-tests-and-live-store-bound-to-machine-state · 2026-10-03-tamper-tests-pinned-to-check-order |
| D | 1 | 2026-10-06-race-fix-verified-with-three-runs-flakes-one-in-five |
| E | 1 | 2026-10-05-parked-fix-branches-drift-out-of-mergeability |
| F | 1 | 2026-09-25-codex-live-hooks-are-stale-sibling-copies |
| G | 2 | 01KZK2BCXT7EKFZ6ZM2AMKFXJR · 01KZW7B1GJ6VSA0Y0X74WJ0S5Y |
| Non-TDL: zktheoryweb | 1 | 2026-10-05-build-mutates-tracked-zotero-cache |
| Non-TDL: codex_workflow | 1 | 01M044JXYSPP0VXH15TEZVCNA3 |
| **Total** | **15** | |

---

## Lint and ledger check

| When | Tool | Result |
|---|---|---|
| 2026-10-06, before this review's edits | `tools/observation_log_lint.py` on `main` (`4003421a`) | `199 observation(s): 13 OPEN`, no findings |
| 2026-10-06, after four new entries, two notes and the archival | same | `203 observation(s): 15 OPEN`, no findings |
| 2026-10-06, `--packet` on this file | same | `ledger matches the 15 OPEN observation(s)`, exit 0 |

Negative control: the same `--packet` check against the 2026-09-29 packet exits 1. It names the 11
OPEN entries that ledger lacks and the 21 entries it lists that are no longer OPEN.

The OPEN count rose from 13 to 15 by exactly the two new OPEN entries. The archival and append
were made by a script that refused to write unless:
- the log's SHA-256 still matched the backup;
- its block split agreed with the lint's parse, id for id;
- the id order was unchanged, with the new entries appended at the end;
- the OPEN set changed only by the new entries;
- every archived block appeared verbatim in the prior log;
- the lint came back clean.

The pre-review log is at `~/.claude/skill-updates/2026-10-06/log/log.md.before`.

## Skills pass

**Inventory.**
- `sync_agent_skills.py --check` passes with 63 synced skills `IDENTICAL`.
- `--verify-state` reports "68 recorded hashes match the mirror bytes".
- Skills outside the manifest are unchanged since last week: `SKILL-INDEX.md`, the `apm-N-*`
  skills, the `source-command-*` shims, `writing-skills-extras` and `apm-communication`.
- Also checked: the global `research-observer` and `task-observer`, and the plugin skills in the
  session list.
- Pinned skills, from `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`:
  `validate-topology`, `statistical-design-audit`, `representation-freeze-audit`,
  `result-provenance-review`, `paper-claim-trace` and `research-assurance-triage`. No staged
  edit touches any of them.

**Cross-check of every OPEN group against every relevant skill:**
- **A:** `research-observer` had no check for "built" claims. Fixed in this run (SKILL lane).
  `tda-large-workflow-supervision` already says no dependency may be "disposed only to a PR
  comment, plan, handoff, or unnamed successor". A local-only branch is the same failure, and
  the reachability check (A3) is the mechanical form.
- **B:** `tda-skill-authoring-workbench` and `research-observer` say nothing about pins. The
  text is staged (B4). The workbench also still points at "the task-observer log", and the
  staged edit corrects that.
- **C:** `contract-first-tdd` already holds the rule #328 diverges from. Writing it again would
  not help, so this goes to a mechanical control (C3).
- **D:** `contract-first-tdd` has no repetition rule for race tests. Staged (D2).
  `tda-diagnosing-computational-defects` already covers non-determinism in its trigger; no
  change.
- **E:** `tda-large-workflow-supervision`. Staged (E1). `using-git-worktrees-extras` does not
  need it.
- **F:** `tda-agent-safety-guardrails` gets its Codex-hook line once the probe has decided F.
- **G and the non-TDL items:** no TDL skill involved.

**Simplification sweep ("what can we remove?").**
- `anthropic-skills:task-observer` still appears in the Claude Code skill list as a third
  observer listing. It is plugin-provided and can't be edited from here. The global copy was
  demoted on 2026-10-02.
- `Documents\Counting Lives\skill-observations\` is a dormant legacy observation store:
  - last written 2026-06-15, with six entries, all ACTIONED;
  - unlike `~/.Codex/skill-observations/`, it has no `CANONICAL-ROOT.txt` deprecation marker, so
    a Cowork session there could write to it unseen.

  Recommend the same marker, written from a Counting Lives session.
- The branch `revert-312-pipe/sweep-cadence` was created through GitHub on 2026-10-05 at 15:43,
  with no PR. #312 is still on `main` and working. Delete the branch if it was not meant.
- The main checkout has 186 local-only branches with no PR, most from July and August. Don't
  sweep them blindly: the spike-retention memory applies. The two that matter are in Group A.
- The worktrees for #308 and #311–#318 can go at the next owner-triggered sweep, once CodeRabbit
  has concluded. Keep `06s-acceptance`.

**Self-applied:** one SKILL-lane edit, to the global `research-observer` (diff in
`~/.claude/skill-updates/2026-10-06/research-observer/applied-2026-10-06.diff`). It runs no repo
tool, so "instructions ship after their mechanisms" is met.

**Staged:**

| Skill | Version | Source | Diff |
|---|---|---|---|
| `contract-first-tdd` | 1.3.0 | D | `proposed.diff` |
| `tda-large-workflow-supervision` | 1.5.0 | E | `proposed.diff` |
| `tda-skill-authoring-workbench` | 1.1.0 | B | `proposed.diff` |
| `research-observer` routing row | — | B | `proposed-pin-row.diff` |

Each `.base` copy is byte-identical to `main`, and none contains a tree-specific path literal.

**Compliance with the cross-cutting principles:**
- *No self-attestation:* the applied rule replaces a log claim with a reachability check.
- *Every gate needs a watched failure:* every proposed gate (A3, B3, C3) names its negative
  control.
- *Silent absence:* the pin check (B3) turns an edit that is invisible today into a Gate 0
  failure.

## Gate-liveness spot check

1. **`merge-admission`, a required check that is red on every open PR.** A check that is
   expected to be red can hide a second, different red (obs
   `2026-09-30-workflow-script-broke-on-an-apostrophe-no-test-could-see`). So I read the failure
   text of the latest run on each open PR.
   - #325, #328 and #329 each end "BLOCKED: review producers have not reached a terminal state on
     the candidate: chatgpt-codex-connector has not reviewed or reacted on this head", and it is
     the only failure in each run.
   - This is the expected cause, named by #304's producer states. The positive signal is that
     verdict line; the negative controls are in `tests/tools/test_merge_admission.py`. Healthy.
2. **The vault `CONVENTIONS.md` symlink.**
   - `ls -la` shows `-> /c/Users/steph/TDL/CONVENTIONS.md`, `dir /AL` lists it as `<SYMLINK>`,
     and `cmp` finds it identical to the repo file. Healthy.
   - No automated check watches it. A symlink resolves by path, so git rewrites cannot break it,
     and I logged nothing about the link itself.
   - In passing I found the memory index still describing the hardlink. That is fixed and logged
     (`2026-10-06-memory-index-still-described-the-hardlink`).

Also seen running correctly:
- `hook_currency.py` at this session's start: "hook tree in force is 4a588ce8 … none touch hook
  files" (#315's positive signal).
- The merge-admission sweep: its scheduled runs on 2026-10-05/06 were 4.6 hours apart, inside
  the 8-hour watchdog bound, and comment-triggered runs started within seconds (#312).

No destructive probe was run.

## Coverage question

"Did anything go wrong this week that no gate, contract or invariant caught?" Yes. As in the
2026-09-29 packet, each case is logged under the lane of the mechanism that should own it. None
is a numerical or statistical failure, so none is an invariant-battery item.

| What went wrong | Caught by | Observation |
|---|---|---|
| #307's skill edit made the WP6.3 pack unconsumable; 48 tests red for six days | the full-suite triage, by hand | `2026-10-06-review-skill-edit-broke-a-pack-pinned-skill` (new, B) |
| An owner-decided fence and gate never landed, and two packets called the gate built | this review, by hand | `2026-10-06-owner-decided-work-stranded-on-local-branches` (new, A) |
| Seam-changing PRs left their dependents red | the triage's bisection | `2026-10-03-shared-seam-change-merged-without-its-dependents` (B) |
| Tests depended on the live store, which pins a deleted worktree | the triage | `2026-10-03-tests-and-live-store-bound-to-machine-state` (C) |
| Tamper tests stopped reaching the checks they name | the triage | `2026-10-03-tamper-tests-pinned-to-check-order` (C) |
| A race fix merged on 3/3 green fails 4/20 | a merge-verification run, by chance | `2026-10-06-race-fix-verified-with-three-runs-flakes-one-in-five` (D) |
| Fix branches drifted out of mergeability while waiting | a `merge-tree` sweep, by hand | `2026-10-05-parked-fix-branches-drift-out-of-mergeability` (E) |
| A zktheoryweb build rewrote a tracked data file | by hand | `2026-10-05-build-mutates-tracked-zotero-cache` (non-TDL) |

## This review's actions

1. Found the previous packet (#308), confirmed it was decided on 2026-10-02, and re-resolved
   each of its 25 items against `origin/main` and the other trees.
2. Fast-forwarded the main checkout from `272b1192` to `origin/main` (`4003421a`). It was nine
   commits behind, none touching hooks.
3. Ran the lint before and after this review's edits: clean both times.
4. Verified the OPEN items read-only:
   - TDL: commit reachability, the open PRs' diffs and the hook wiring;
   - zktheoryweb: the build hook;
   - codex_workflow: the installed copy;
   - MathUni and zktheoryweb: the merge commits behind last week's closures.
5. Applied one SKILL-lane edit (`research-observer`) and one RECORD fix (the memory index and
   its companion memory), each with a dated backup in `~/.claude/skill-updates/2026-10-06/`.
6. Logged four observations: two OPEN, and two ACTIONED in the same edit as their fixes. Added
   dated review notes to `2026-08-22-retired-procedure-kept-live-imperatives` and
   `2026-08-12-file-map-frozen-since-wp1`.
7. Archived the 57 closed entries still holding full text to `archive/log-2026-10-06.md`, with
   nothing re-dispositioned.
8. Staged four skill edits for your approval (Groups B, D and E).
9. Updated `last-review-date.txt` to `2026-10-06`.
10. Opened this packet as a PR.
