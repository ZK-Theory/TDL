# Weekly Research-System Review — Resolution Packet

**Review date:** 2026-10-27. The scheduled `weekly-system-review` task ran on time (Tuesday, 08:44Z).

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md`. After this review it holds 269 entries, 25 of
them OPEN (OPEN, ESCALATED or PARTIALLY, per the lint).

**Scope:** every OPEN observation in the shared log, across the five trees named by the 2026-09-25 and 2026-10-02 owner
decisions: TDL, MathUni, the Counting Lives vault, codex_workflow and zktheoryweb. The other trees were read only. All 25
OPEN entries belong to TDL, so there is no scope finding. MathUni, Counting Lives and zktheoryweb have no observation file
newer than the last archive. codex_workflow's one entry is DEFERRED.

**Decision owner:** Stephen

**Operating rule (unchanged since 2026-08-09):** approval authorizes a bounded verify-then-fix campaign on a reviewed
branch. It does not authorize direct changes to `main`, silent gate weakening, or acceptance without the named
controls.

**What this review changed.**
- **Record (observation log):**
  - **Closed eight entries.** Five on met close conditions (#383, #384, #385), two SKILL entries applied in this PR, and
    one duplicate merged into its twin. See "This review's closures".
  - **Added dated Progress notes** to twelve entries. Six of them record that the specific defect is already fixed on
    `main`, so only the general lesson stays open.
  - **Logged three observations**, all GATE, all OPEN (Groups A and H).
  - **Archived** the four entries the 2026-10-20 review closed, to `archive/log-2026-10-27.md`.
- **Skills (applied, in this PR):** `adversarial-design-review` 1.0.0 → 1.1.0 and `writing-plans-extras` 1.0.0 → 1.1.0.
  See "Skills pass".
- **Record (applied, in this PR):** one sentence in the root `CLAUDE.md` access-mode paragraph (Group F).
- **Not changed:** anything on the GATE, INVARIANT or PROCESS lanes, and nothing in the other trees. Everything below is
  a recommendation.

The pre-review log is at `~/.claude/skill-updates/2026-10-27/log/log.md.before`.

## Where last week's packet stands

You decided the 2026-10-20 packet (PR [#382](https://github.com/ZK-Theory/TDL/pull/382), 8 OPEN in four groups) on
2026-10-21. The decisions are in the log's Progress notes and in the follow-up PRs, which all merged that day.
Re-resolved against `origin/main` (`7979e85a`):

| Group | Decision | Built | State now |
|---|---|---|---|
| A. Lane required | approve 1–3 | #385 (`7e0570a4`): `suite-verdict` job and `merge_group` trigger | `suite-verdict` green on PRs and every night since 2026-10-22. **Ruleset edit not made**; its merge-queue leg cannot be observed (Group A below) |
| B. Merge-admission guidance | option 1; keep Codex | #384 (`53b7c5be`): no waiver, guidance and CONVENTIONS corrected, policy test | Done. Three entries closed this review |
| C. Amended-decision entry | close | — | Closed in the campaign; archived this review |
| D. Cross-repo close conditions | approve | #383 (`6e3ad7f3`) | Done; used by this review. Entry closed |
| Two closures, skill edit | keep | — | Archived this review |
| Simplification S1–S4 | no recorded decision | S3 done: worktree sweep, #388 | S1, S2, S4 carried (see "Carried from last week") |

No outcome PR was opened for the 2026-10-20 campaign, unlike #378 for the one before. The campaign PRs merged, but the
six entries they were meant to close stayed OPEN for six days. This review's `--close-conditions` run caught all six,
which is the mechanism working as designed. One of the six was a false positive (Group A).

## How to use this packet

Tick one box per group. An approved group first re-resolves each mapped observation against current `main`. If an
observation is already compliant or superseded, record the evidence and close it. If it is still valid, build the named
mechanism with its negative control.

## Decision summary

| Group | OPEN | Recommended resolution | Decision |
|---|---:|---|---|
| A. Lane required: the merge-queue question | 3 | Build a bypass audit; choose queue or direct merges; then the ruleset edit | `[ ]` A1 audit · `[ ]` (a) queue · `[ ]` (b) direct merges · `[ ]` defer |
| B. Stranded W11 acceptance record | 1 | Push and PR the record now; add a register-reachability lint | `[ ]` approve 1–3 · `[ ]` 1 only · `[ ]` defer |
| C. Design review: check the bytes, not the prose | 5 | One consolidated checklist subsection in two skills | `[ ]` approve · `[ ]` approve skill text, defer the lint · `[ ]` defer |
| D. ARS verifier and fixture controls | 5 | Hex-literal ancestry lint plus a verifier checklist | `[ ]` approve 1–3 · `[ ]` some (name which) · `[ ]` defer |
| E. Record currency | 5 | Fix `SUPERSEDED.md`; supersession lint for cited decisions; two skill lines | `[ ]` approve 1–4 · `[ ]` some (name which) · `[ ]` defer |
| F. Agent-guidance corrections | 2 | Close both | `[ ]` close both · `[ ]` add the registry line first · `[ ]` keep open |
| G. Live-run dispatch hygiene | 2 | Two lines in `tda-large-workflow-supervision` | `[ ]` approve · `[ ]` defer |
| H. Gate precision and liveness | 2 | Run the four unrun hook controls; scope the advisory hook | `[ ]` approve both · `[ ]` H1 only · `[ ]` defer |
| This review's eight closures | — | Keep them closed | `[ ]` keep · `[ ]` reopen (name which) |
| The two skill edits and the `CLAUDE.md` sentence | — | Keep them | `[ ]` keep · `[ ]` revert (name which) |
| Carried simplification S1, S2, S4 | — | Approve | `[ ]` approve · `[ ]` some (name which) · `[ ]` decline |

Total: 3 + 1 + 5 + 5 + 5 + 2 + 2 + 2 = **25**.

---

## A — Making the lane required: the merge-queue question (3)

**Where it stands.** #385 merged on 2026-10-21. `suite-verdict` reported success on PR #395 (run 40421477597) and on every
scheduled night since 2026-10-22 (latest: run 40461404737, 2026-10-27). Ruleset 20822054 still requires only
contract-and-session-currency, require-active-currency-workflow, merge-admission and admission-controls.

The lint reports `2026-10-02-full-suite-red-on-main-unseen` as met. That is a false positive: the 2026-10-21 clause names
#385 as a precondition, and the condition is your ruleset edit. The entry stays open; its Progress note says so for the
next reader.

**Defect (new, `2026-10-27-merge-queue-never-entered-every-main-update-bypasses`).** Last week's step 2 said: add
`suite-verdict` to the ruleset after it has run green on one PR, **one merge-queue entry** and one scheduled night. The
queue leg cannot be observed:
- `gh run list --event merge_group` shows no run of any workflow since 2026-09-11 (the #278 to #281 entries).
- The rule-suite API lists 95 evaluations on `refs/heads/main` from 2026-09-30 to today. Every one is `result: bypass`
  by stephendor, docs-only PRs such as #388 included.
- So, in practice, every merge goes through the admin bypass P-049 allows, not through the queue.

Three consequences follow:
1. The ruleset edit that closes two entries has no evidence path as merges are made today.
2. CONVENTIONS relies on "GitHub records every bypass in rule insights" to make a deliberate gate-file bypass visible.
   When every merge is a bypass, that record cannot single one out.
3. A required `suite-verdict` would bind nothing a bypass merge cannot skip. Nothing records whether a bypassed merge
   had its required checks green on the head that merged.

This is a missing signal, not a known bad merge: every PR I inspected (#384, #385, #394, #395) had green checks.

**Proposed action.**
- **A1. Bypass audit (useful under either choice).** A scheduled job that, for each `main` commit since its last run,
  finds the PR and asserts that every required check was green on the head that merged. It reports any merge that was
  not. Read-only; it writes no ruleset.
- **Then choose one:**
  - **(a) Queue for ordinary merges.** Merge through the queue and keep the bypass for gate-file edits, so a bypass is a
    signal again. The queue leg of last week's precondition then gets observed on the next PR. Cost: every merge waits
    for the queue's checks on the synthetic commit, the selected shards included.
  - **(b) Keep direct merges.** Remove the `merge_queue` rule and the queue leg of the precondition. The PR and night legs
    are already green, so the ruleset edit can go ahead. A1 becomes the record that checks were green.
- Either way, the ruleset edit is yours (agent sessions never write rulesets, `admin-bypass-guard.sh`), and the two older
  entries close when the readback lists `suite-verdict`.

**Controls.**
- A1: a fixture PR record with a red required check at merge is reported; one with all checks green is not. The run
  summary states how many merges it checked (positive signal).
- (a): a `merge_group` run reports `suite-verdict` on the queue head. The `merge_group` trigger's policy test already
  exists.
- Ruleset readback lists `suite-verdict`.

**Recommended decision:** approve A1, then (b). The queue has had no entry for 46 days, so (b) records the practice
that actually holds and gives it a check. Choose (a) if you want the bypass to mean "gate-file edit" again.

**Decision:** `[ ]` approve A1 · `[ ]` (a) queue for ordinary merges · `[ ]` (b) keep direct merges, drop the queue
rule · `[ ]` defer

---

## B — The stranded W11 acceptance record (1)

`2026-10-22-w11-owner-acceptance-stranded-on-unmerged-branch` (its duplicate,
`2026-10-22-owner-acceptance-stranded-off-main-misled-a-spec`, was merged into it this review).

**Defect.** Your 2026-08-01 acceptance of W11 for D-G6-4 limb 1 is still not on `main`:
- `cee20209`, the original record, is only on `codex/wp6-gate6-completion`.
- `d2e09eea`, the fix that carries it onto main and records KAN-84, was made on 2026-10-22. It is still only on the
  local branch `docs/w11-limb1-acceptance-record`, checked out in worktree `.claude/worktrees/cool-yalow-de9824`. It is
  on no remote ref, and there is no PR.
- `origin/main` still reads "D-G6-4 remains open for (1)" at `03-decisions-and-open-questions.md:1221`. Gate 7 opened
  (#391) and W9 code merged (#394 to #396) with the register in that state.

The fix for a stranded-record finding was itself stranded for five days. Only this review's reachability lint caught
it. This review did not push it: the branch belongs to another session's worktree.

**Proposed action.**
1. The session that owns `cool-yalow-de9824`, or you, pushes `docs/w11-limb1-acceptance-record` and opens its PR. It is
   docs only: the register update plus the review record.
2. A register-reachability lint: list every local or remote branch commit that touches
   `docs/plans/agentic-research-system/03-decisions-and-open-questions.md` or `reviews/*owner-acceptance*` and is not
   an ancestor of `origin/main`. Run it in the review's step 1, next to `--reachability`.
3. One line in `tda-task-brief-from-plan`: when a scope note names a "verify before X" item, X's brief starts by doing
   it (06u D-10 asked for exactly that before G7-B, and it was skipped).

**Controls.** (2) flags `d2e09eea` today and is silent once (1) merges. (2) is silent on a commit already on `main`.

**Recommended decision:** approve 1–3. Item 1 is the urgent one: main's register misstates an owner decision.

**Decision:** `[ ]` approve 1–3 · `[ ]` approve 1 only · `[ ]` defer

---

## C — Design review: check the bytes, not the prose (5)

The W9 and Gate 7 review chain (2026-10-22 to 2026-10-24) produced these. Each records an author or reviewer who
checked a claim about another artefact against prose, and an independent reviewer who caught it by opening the
artefact. All five instances were fixed in their review cycles. The lessons are not yet in any skill.

| Entry | The lesson |
|---|---|
| `2026-10-22-reviewer-prescribed-identifiers-copied-unverified` | A reviewer's prescribed fix is not an owner source. Quote identifiers from the owner with `file:line`, and trace a prescribed mechanism through the code it relies on (happened twice: OR-109, then `load_store_manifest`) |
| `2026-10-22-gate-definition-restates-owning-matrix-narrowly` | A gate that summarises another spec's precondition matrix points to it as operative ("adds to, never relaxes") and restates only its delta. Reviewers diff every restated condition against its owning row |
| `2026-10-23-segmentation-contract-written-without-target-census` | A byte-selector contract ships a census of each governed file and a reference script, run on the real bytes (the anchor matched 114 of 167 headings) |
| `2026-10-23-respec-addendum-missed-materialized-fixture` | Before re-specifying, renaming or deferring a catalogue ID, run `git grep -l <ID> -- .research-system research_system tests tools` |
| `2026-10-24-design-note-routed-commands-to-a-generic-path-without-reading-its-preparer` | Following a precedent means diffing its row set, not only its field set. "Handled by existing X" requires reading X's preparer |

**Proposed action.** Replace a bullet per finding with one subsection in `adversarial-design-review`, "Claims about
another artefact: open the artefact". It would hold the five lessons above plus the two bullets this review already
applied (reuse claims and shared-store tenants), so the skill gets shorter rather than longer. Add the author-side
counterparts to `writing-plans-extras`. Optionally, widen `tools/check_retired_imperatives.py` beyond `implementation/`
to 03, 04-plan and the roadmap, as the gate-definition entry asks, or record why not.

**Controls.** Skill text has no negative control. The evidence is the next review: a W9 design note reviewed after the
change that cites `path:line` for each "handled by" claim. If you approve the `check_retired_imperatives.py` widening,
its control is a fixture retired imperative in `04-plan` that the check flags.

**Recommended decision:** approve the skill text; defer the lint widening to the next Gate 7 planning pass.

**Decision:** `[ ]` approve · `[ ]` approve skill text, defer the lint · `[ ]` defer

---

## D — ARS verifier and fixture controls (5)

Five GATE and INVARIANT entries from the same chain. **Every instance is fixed on `main`** (each Progress note names the
line). What stays open is the general control.

| Entry | Fixed on main by | Open general control |
|---|---|---|
| `2026-10-24-squash-merge-strands-sha-pinned-controls` | `test_w9_expected_catalogue.py:35` no longer reads the branch-only commit | Lint: every 7-to-40-hex literal in `tests/` passed to git is an ancestor of `origin/main` |
| `2026-10-24-verifier-pin-chosen-by-its-subject` | `verify_w9_materialization.py:48` pins `W9_ANNEX_SHA256`; lines 456–466 refuse an off-main commit | Checklist: the verifier, not the subject, names the version of the expected side |
| `2026-10-27-gate-pass-set-wider-than-accepted-identity` | #396 (`7979e85a`, merged after the entry was logged): `test_byte_identity_refuses_a_re_encoding_or_a_new_created_at` | Same byte binding for W11's verifier; checklist line |
| `2026-10-23-schema-fixtures-used-one-placeholder-id-for-every-ref` | `test_w9_contract_materialization.py:92–94, 168` type refs by kind | Fixture rule: each ref fixtured with a real-kind ID plus a wrong-kind negative |
| `2026-10-23-accepted-tool-and-schema-claim-same-shape-without-a-binding-test` | B-2 section of the same test (from line 945) | Rule: every "in the shape of" claim gets a producer→consumer binding test in the PR that lands the later artefact |

**Proposed action.**
1. The hex-literal ancestry lint. It is cheap, and TDL squash-merges, so the failure will recur.
2. A "verifier conformance" checklist in `schema-contract-design` and `contract-first-tdd`: pinned expected side, byte
   identity for owner-accepted artefacts, real-kind ref fixtures, producer→consumer binding.
3. The W11 byte-identity test. Read-only: W11's catalogue is already genesis-imported.

**Controls.** (1): a fixture test file passing a branch-only hex literal to git fails, and one passing a `main` ancestor
passes. (3): a CRLF or re-signed copy of the W11 catalogue is refused.

**Recommended decision:** approve 1–3.

**Decision:** `[ ]` approve 1–3 · `[ ]` approve some (name which) · `[ ]` defer

---

## E — Record currency (5)

| Entry | State now | Proposed action |
|---|---|---|
| `2026-10-22-superseded-md-lags-reclassifying-results` | **Still stale**: `SUPERSEDED.md` lines 69–71 say "presumed IMMUNE … Confirm by gate" against T1.38's UNVERIFIABLE | E1. Correct the entry, citing T1.38 Phase 1, before any W9 import batch reads `SUPERSEDED.md` (W0 §8.1 makes it the import source). Defer the supersession-currency contract to Gate 7+ intake |
| `2026-10-21-gate7-brief-restated-superseded-and-closed-items` | Unchanged | E2. A small lint: for each `P-0NN` cited in a handoff or brief, report any later register entry whose Supersedes/Amends line names it |
| `2026-10-22-additive-addendum-leaves-unrederived-rows-stale` | Unchanged | E3. A line in `tda-handoff` and `writing-plans-extras`: a currency addendum re-derives every inherited row or marks it "not re-checked at `<commit>`" |
| `2026-10-22-verified-star-let-a-value-conflict-through` | Instance resolved: the vault correction of 2026-10-22 finds the draft correct | E4. Defer the claim→value contract to the next P01-A claim-trace pass. Note: `paper-claim-trace` is pinned by the `tdl-private-assurance` pack, so a skill line there needs a pack update, which is yours |
| `2026-10-22-dated-observations-lack-time-and-hash-convention` | Partly superseded: `w9-segmentation/1.0.0` (P-068) is a named, versioned segmentation rule with a reference script, and the W9 schemas define `utc` date-time types | E5. In the campaign, check whether W9's observation records require a UTC time. Close if they do; otherwise add the field |

**Controls.** E1: a re-read of lines 69–71 matches T1.38. E2: a fixture brief citing P-033 is flagged "superseded by
P-042". E3 and E4 are text. E5: the schema rejects an observation without a UTC time, or the entry stays open.

**Recommended decision:** approve E1–E4 as described, and E5 as a verification step.

**Decision:** `[ ]` approve E1–E5 · `[ ]` approve some (name which) · `[ ]` defer

---

## F — Agent-guidance corrections (2)

- `2026-10-21-pilot-promotion-term-read-as-assay-promote`. Half done on `main`: the Gate 7 section of `04-plan` binds
  the bar to the typed id, "the W6 `gate_stage: pilot_promotion` evidence" (line 131). What remains is a registry line
  separating `pilot_promotion` from the Discovery `PROMOTE` verdict. That would be a CONVENTIONS or W6 lock.
- `2026-10-21-vault-junction-path-blocked-from-worktree-sessions`. Verified: the junction is gitignored and absent from
  linked worktrees. **Applied in this PR:** the root `CLAUDE.md` access-mode paragraph now tells worktree sessions to use
  the absolute vault path. The guard that gave the wrong hint is not a repo hook (nothing in `.claude/settings.json` or
  `.claude/hooks/`). It is the desktop app's worktree check, so its hint can only be reported upstream.

**Recommended decision:** close both. The first on `04-plan:131`, since the operative wording is bound. The second on
this PR's merge, with the app-side hint recorded as outside the repo.

**Decision:** `[ ]` close both · `[ ]` add the pilot-promotion registry line first · `[ ]` keep open

---

## G — Live-run dispatch hygiene (2)

- `2026-10-21-owner-action-prompt-pack-has-no-already-done-precheck`. A prepared pack of eight owner-action prompts
  would have re-run seven live writes that had already merged in #381. Only a manual `git log origin/main` caught it.
- `2026-10-21-jira-connector-errors-still-write-late`. Two Jira comments that returned connector errors appeared about
  three minutes later. An immediate retry would have duplicated them.

**Proposed action.** Two lines in `tda-large-workflow-supervision`:
- before dispatching a prepared prompt pack, re-resolve each prompt against the ledger and `origin/main`, and give each
  prompt an "Already done if:" line naming its completion event;
- a remote write that errors has an unknown outcome: read back after a delay of a few minutes, and retry only if the
  late read-back is still negative.

**Controls.** Text only. Evidence is the next live-run dispatch that drops a completed prompt before running it.

**Recommended decision:** approve.

**Decision:** `[ ]` approve · `[ ]` defer

---

## H — Gate precision and liveness (2)

From this review's spot check (details under "Gate-liveness spot check").

- **H1, `2026-10-27-hook-control-tests-run-by-no-lane`.** Four hook-control files run in no CI lane:
  `test_pre_push_hook.py`, `test_commit_msg_hooks.py`, `test_handoff_surface_hook.py` and
  `test_hook_script_lf_bytes.py`. The policy test in `tests/tools/test_ci_platform_policy.py` checks a hand-written module
  list (lines 178–197), so a hook test nobody added is never missed. pre-push also writes no receipt. Proposed action:
  derive the list from `tests/tools/test_*hook*.py` minus a named exemption list with reasons, and add the four files to
  admission-controls. Control: a new `tests/tools/test_x_hook.py` missing from `ci.yml` fails the policy test. Both files
  are code-owned gate files, so this is your review.
- **H2, `2026-10-27-research-context-advisory-fires-mostly-outside-the-repo`.** Of 282 advisories, 193 were for scratchpad
  files and 54 for `.py` files outside any TDL checkout; 35 concerned TDL files. Proposed action: scope the hook to `.py`
  files in `$CLAUDE_PROJECT_DIR` or a TDL worktree, excluding scratchpad and temp paths. Control: a scratchpad write
  records `silent`; a headerless file under `trajectory_tda/` records `advise`.

Context for H1: the 2026-09-11 [DECISION] accepted that no lane runs the unfiltered suite, and about 135 test files
outside `tests/research_system/` are in no workflow. That decision covers the domain suites; it did not decide to leave
gate controls unrun. If you want the domain suites revisited, that is a separate question, not part of H1.

**Recommended decision:** approve both.

**Decision:** `[ ]` approve both · `[ ]` H1 only · `[ ]` defer

---

## This review's closures

| Entry | Evidence |
|---|---|
| `2026-10-17-merge-admission-waiver-has-no-mechanism` | #384 `53b7c5be`. CONVENTIONS: "There is no owner waiver for thread finality"; `check_merge_admission.py:293`: "there is no waiver path" |
| `2026-10-20-git-guidance-still-requires-codex-after-producer-removal` | #384 `53b7c5be`. `git.instructions.md` merge-admission line rewritten; policy test added |
| `2026-10-21-codex-connector-still-reviews-after-removal` | #384 `53b7c5be`. CONVENTIONS records the integration as kept, still reviewing, not required |
| `2026-10-20-close-conditions-lint-blind-to-cross-repo-prs` | #383 `6e3ad7f3`, with `test_a_cross_repo_close_condition_is_judged_in_its_own_repository` |
| `2026-10-20-suite-lane-has-no-stable-required-check-name` | #385 `7e0570a4`. `suite-verdict` green on PR #395 and the 2026-10-27 night |
| `2026-10-22-spec-reuse-claims-must-diff-against-materialized-schemas` | Applied in this PR: `adversarial-design-review` 1.1.0 |
| `2026-10-23-new-event-family-must-map-whole-ledger-replays` | Applied in this PR: `writing-plans-extras` 1.1.0 and `adversarial-design-review` 1.1.0 |
| `2026-10-22-owner-acceptance-stranded-off-main-misled-a-spec` | Duplicate, merged into its twin (Group B) |

Each closing Status names its evidence, and the previous Status is kept as a `Prior status:` line. They stay in full
text until the next review. If you disagree with any, tick "reopen" and I will restore it from the backup.

## Carried from last week (no OPEN entries)

The 2026-10-20 packet proposed four removals. One was done; three have no recorded decision:

- **S1.** Delete the two finished one-time scheduled tasks, `pr333-heavy-regression` and
  `research-system-lane-required-followup`. Both are still listed, disabled.
- **S2.** Mark DECLINED and archive the four DEFERRED entries about the Codex app, its plugins, hooks and workflow (`155`,
  `01KZKNM7DPMJWTB8D83JQGXCJM`, `01M044JXYSPP0VXH15TEZVCNA3`, `2026-09-25-codex-live-hooks-are-stale-sibling-copies`),
  and archive the legacy `~/.Codex/skill-observations` store. Keeping the GitHub Codex integration (Group B, 2026-10-21)
  does not affect these: they concern Codex sessions, which you stopped using.
- **S3.** Done: the 2026-10-21 worktree sweep (#388).
- **S4.** Move `log.md.bak-2026-09-08` and `log.md.bak-2026-09-09` (357 KB) from the observation store root to
  `archive/`. They are still at the root.

This run did none of them: deleting tasks and archiving decisions is outside an autonomous review's remit.

---

## Completeness ledger

Computed, not assembled. Every OPEN id comes from `observation_log_lint.parse` over the live log after this review's
edits, and the table is checked with `tools/observation_log_lint.py <log> --packet <this file>`.

| Group | Count | IDs |
|---|---:|---|
| A | 3 | 2026-10-02-full-suite-red-on-main-unseen · 2026-10-03-shared-seam-change-merged-without-its-dependents · 2026-10-27-merge-queue-never-entered-every-main-update-bypasses |
| B | 1 | 2026-10-22-w11-owner-acceptance-stranded-on-unmerged-branch |
| C | 5 | 2026-10-22-reviewer-prescribed-identifiers-copied-unverified · 2026-10-22-gate-definition-restates-owning-matrix-narrowly · 2026-10-23-segmentation-contract-written-without-target-census · 2026-10-23-respec-addendum-missed-materialized-fixture · 2026-10-24-design-note-routed-commands-to-a-generic-path-without-reading-its-preparer |
| D | 5 | 2026-10-24-squash-merge-strands-sha-pinned-controls · 2026-10-24-verifier-pin-chosen-by-its-subject · 2026-10-27-gate-pass-set-wider-than-accepted-identity · 2026-10-23-schema-fixtures-used-one-placeholder-id-for-every-ref · 2026-10-23-accepted-tool-and-schema-claim-same-shape-without-a-binding-test |
| E | 5 | 2026-10-22-superseded-md-lags-reclassifying-results · 2026-10-21-gate7-brief-restated-superseded-and-closed-items · 2026-10-22-additive-addendum-leaves-unrederived-rows-stale · 2026-10-22-verified-star-let-a-value-conflict-through · 2026-10-22-dated-observations-lack-time-and-hash-convention |
| F | 2 | 2026-10-21-pilot-promotion-term-read-as-assay-promote · 2026-10-21-vault-junction-path-blocked-from-worktree-sessions |
| G | 2 | 2026-10-21-owner-action-prompt-pack-has-no-already-done-precheck · 2026-10-21-jira-connector-errors-still-write-late |
| H | 2 | 2026-10-27-hook-control-tests-run-by-no-lane · 2026-10-27-research-context-advisory-fires-mostly-outside-the-repo |
| **Total** | **25** | |

---

## Lint and ledger check

| When | Tool | Result |
|---|---|---|
| Before this review's edits | `observation_log_lint.py --reachability . --close-conditions .` at `fc5f356b` (then `origin/main`) | `266 observation(s): 30 OPEN`. Reachability: 44 hashes, 2 stranded (`d2e09eea`, cited by both W11 entries). Close conditions: 6 checked, 6 met. Exit 1 |
| After the edits | same, at `7979e85a` | `269 observation(s): 25 OPEN`. Reachability: 40 hashes, 1 stranded (`d2e09eea`, carried as Group B). Close conditions: 1 checked, 1 met (the Group A false positive, carried). Exit 1 on the two carried findings only |
| After the edits, `--packet` on this file | `observation_log_lint.py <log> --packet <this file>` | see the PR's test plan |

The main edit was made by a script that refused to write unless:
- the log matched its backup's SHA-256;
- the id order was unchanged, with the three new entries appended at the end;
- the OPEN set changed by exactly the eight closures and three additions;
- every entry not named in the edit was byte-identical apart from trailing whitespace;
- the lint's non-reachability checks came back clean.

A second, narrower script added two Progress notes (Groups D and F) and refused unless only those two blocks changed.

**Archival.** The four entries the 2026-10-20 review closed moved verbatim to `archive/log-2026-10-27.md`, each with a
stub in `log.md`. This review's eight closures stay in full text until the next review.

## Skills pass

**Inventory.**
- No skill changed on `main` between the two reviews. Before this review's edits, `sync_agent_skills.py --check` showed
  all synced skills IDENTICAL and `pack pins: 12 checked, 0 drifted`.
- After the edits: `sync_agent_skills.py` updated the two mirrors and `tools/skill_sync_state.json`; `--check` shows all
  IDENTICAL, and `pack pins: 12 checked, 0 drifted`.
- Pack pins: neither edited skill is pinned (`git grep "<name>/SKILL.md" .research-system/` is empty for both).
  `paper-claim-trace` is pinned by `wp6-3-tdl-private-assurance-pack.yaml` and `packs/tdl-private-assurance.yaml`, which
  is why E4 is routed to you rather than applied.

**Cross-check of every OPEN group against the skills.**
- **A, H:** no skill change. The fixes are a workflow job, a ruleset choice and two hook changes.
- **B:** `tda-task-brief-from-plan` (one line, B3).
- **C:** `adversarial-design-review`, `writing-plans-extras`. Five lessons, consolidated rather than appended.
- **D:** `schema-contract-design`, `contract-first-tdd` (the verifier-conformance checklist).
- **E:** `tda-handoff`, `writing-plans-extras` (E3); `paper-claim-trace` (E4, pack-pinned).
- **F:** no skill; the `CLAUDE.md` sentence is applied.
- **G:** `tda-large-workflow-supervision`.

Only two OPEN entries were on the SKILL lane. Both were applied. Everything else that suggests a skill line is on the
PROCESS, GATE, INVARIANT or RECORD lane, so an autonomous run leaves it to you.

**Applied (SKILL lane, repo skills, edited in `.agents/skills/` and mirrored):**
1. `adversarial-design-review` 1.1.0. Lane 3 gains two bullets: a reuse or extension claim is checked against the
   accepted schema bytes and one real source instance; a new command or event family on a shared store is checked
   against every whole-ledger reducer and closed allowlist it meets. A W9 pressure scenario records both.
   (`2026-10-22-spec-reuse-claims-must-diff-against-materialized-schemas`)
2. `writing-plans-extras` 1.1.0. New section "Shared-Ledger Reader Inventory", the author-side form of the second bullet.
   (`2026-10-23-new-event-family-must-map-whole-ledger-replays`)

**Compliance against the active cross-cutting principles.** Both edits apply Principle 6 (match the semantic property,
not the surface form): they replace "the prose looks compatible" with "the bytes and the code decide". Neither adds,
weakens or removes a gate.

**Simplification sweep.**
- `adversarial-design-review` grew by 17 lines this review and is now 262. Group C proposes one
  consolidated subsection instead of a bullet per finding. It would absorb both of this review's bullets, so approving C
  shrinks the skill.
- S1, S2 and S4 are carried (above).
- No skill is proposed for removal. None is superseded by a mechanism built this week.

## Gate-liveness spot check

Two gates that no packet has spot-checked before:

1. **`.claude/hooks/research-context-check.sh`** (advisory, PostToolUse). Never named in any packet.
   - Positive signal: 1,177 receipts (282 `advise`, 895 `silent`), the latest today.
   - Negative control: `test_research_context_check_receipt_records_advise_and_silent` in
     `tests/tools/test_system_review_hook_gates.py`, run by admission-controls.
   - Live, but imprecise: about seven in eight advisories concern files the rule does not govern (H2).
2. **`.githooks/pre-push`** (refuses a push to `refs/heads/main`). Never named in any packet.
   - Negative control: `test_pre_push_rejects_direct_main_update`. **No CI lane runs it** (H1).
   - Positive signal: none. The hook writes no receipt, and it has no recorded production refusal; main is updated
     only by PR merges on GitHub, so it is rarely on the path.
   - `install-git-hooks.py`: every required hook present and executable in `.githooks`.

Both controls ran locally in this review: **3 passed**. No destructive probe was run.

**Gates seen firing on live data this week:**
- **The primary-checkout guard** (#360, #373) refused this session's no-op `git checkout -q main` in the primary
  checkout, so the review moved to a linked worktree. A true positive in spirit: the command could have moved HEAD.
- **The review-staleness SessionStart line** printed "last ran 2026-10-20 (7 days ago)" at session start.
- **`--reachability`** flagged `d2e09eea`: a true positive (Group B).
- **`--close-conditions`** flagged six met conditions: five true, one false positive (Group A).

## Coverage question

"Did anything go wrong this week that no gate, contract or invariant caught?" Yes:

| What went wrong | Caught by | Observation |
|---|---|---|
| The W11 acceptance fix sat five days on a local branch while Gate 7 opened on the stale register | this review's reachability lint, at the weekly cadence only | Progress note on `2026-10-22-w11-owner-acceptance-stranded-on-unmerged-branch` (B) |
| Every update to `main` for a month was a ruleset bypass, and the queue has not run since 2026-09-11 | this review, by reading the rule-suite API | `2026-10-27-merge-queue-never-entered-every-main-update-bypasses` (A) |
| Four hook negative controls run in no CI lane | this review's spot check | `2026-10-27-hook-control-tests-run-by-no-lane` (H) |
| An advisory hook fires mostly on files its rule does not govern | this review's spot check | `2026-10-27-research-context-advisory-fires-mostly-outside-the-repo` (H) |
| `SUPERSEDED.md` still misclassifies a result five days after it was logged | this review, re-reading the file | Progress note on `2026-10-22-superseded-md-lags-reclassifying-results` (E) |
| The W9 chain's ten defects in candidate or accepted artefacts | independent reviewers, by hand, during the week | logged at the time (C, D) |

None is a numerical or statistical failure, so none is a new invariant-battery item. The value conflict in E4 was
logged as INVARIANT during the week and has a resolved instance.

## This review's actions

1. Found the previous packet (#382) and its follow-ups (#383 to #385), and re-resolved them against `origin/main`
   (`fc5f356b`, then `7979e85a` after #396 merged during the review).
2. Ran `git fetch origin` and the lint with `--reachability . --close-conditions .`, before and after the edits.
3. Read ruleset 20822054, its rule-suite evaluations, the suite lane's runs since 2026-10-20 and the checks on #395.
4. Re-resolved each W9-chain entry against the merged code and tests, and the T1.20 entry against the vault
   Computational-Log.
5. Checked the other trees read-only for observation files newer than the last archive (none).
6. Closed eight entries, added twelve Progress notes, logged three observations and archived four, through two checked
   scripts. Backup: `~/.claude/skill-updates/2026-10-27/log/log.md.before`.
7. Edited `adversarial-design-review` and `writing-plans-extras` in `.agents/skills/`, synced the mirror, and ran
   `sync_agent_skills.py --check`.
8. Added one sentence to the root `CLAUDE.md` (Group F).
9. Ran both spot-checked gates' negative-control tests (3 passed).
10. Updated `last-review-date.txt` to `2026-10-27`.
11. Opened this packet as a PR, from the linked worktree `.claude/worktrees/system-review-2026-10-27`.
