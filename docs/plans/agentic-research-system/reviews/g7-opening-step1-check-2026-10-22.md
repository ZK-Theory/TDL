# Gate 7 opening: the 06l Step 1 check (opening-bar condition 4)

**Date:** 2026-10-22
**Kind:** a distinct exact-subject check, read-only. It is not an opening decision.
**Checker:** a Claude Code session (Claude Opus 5.5) started from the gate7-prep family to run this check. It did not
author or review G7-A, W9, the Discovery inventory or G7-C.
**Governing text:** 04-plan §4, "Gate 7 — Legacy research integration", opening bar condition 4; 06l Step 1 as P-062
amends it (A3, A4).
**Runtime authority:** none. This record opens nothing, dispatches nothing and writes no store. It made no Jira change.

**Result: Condition 4 holds.** Conditions 1 and 2 are also MET. Condition 3, Stephen's separate opening decision, is
required and not yet given, so Gate 7 stays NOT OPEN (OWNER-BLOCKED under the Gate 7 capability table).

## 1. Subject

| Identity | Value |
|---|---|
| Repository | `C:\Users\steph\TDL`, worktree `gate7-step1-check-18647f`, branch `claude/gate7-step1-check-18647f` |
| origin/main at check time | `50371fac50f6c600f552ae687b0cea90dca1d0a6` (PR #389 merge, committed 2026-10-22T18:15:45+01:00) |
| HEAD at check time | `50371fac`, equal to origin/main |
| Jira | site `nexusstephen.atlassian.net`, read 2026-10-22 between 20:06Z and 20:09Z |
| Off-repo evidence | `C:/Users/steph/.codex/tmp/g6-p5/s3-b19/`, read-only hashing |

Blobs read on origin/main `50371fac` (all paths under `docs/plans/agentic-research-system/`):

| File | Blob on main |
|---|---|
| `transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md` | `1ebcf96ff07127561402873a52dd6a7280aa9700` |
| `design/09-migration-compatibility-and-pilot.md` | `ea3a8e4a5e89a599c255fd881c2a040db4f2d3c5` |
| `04-parallel-specification-and-foundation-pilot-plan.md` | `96f34634a4b1c3926725a76b232c09b33c216eae` |
| `03-decisions-and-open-questions.md` | `9bc3dc737ca3ba302a562425f79aaf0a2407377b` |
| `implementation/06l-wp6-7-legacy-consolidation-sequencing.md` | `24961ba2c4ff58237912d31488524af5ae562ead` |
| `implementation/06-wp6-gate6-readiness-and-integration-plan.md` | `f5e3fbacb899be527b87a7d266f7cc65a93fbe67` |
| `02-design-and-deliverables-roadmap.md` | `bbb87c715b9b95e5025a62aa106c7b12666ce7e7` |

Records read: the three owner-acceptance records (`reviews/g7a-…-owner-acceptance-2026-10-22.md`,
`reviews/g7b-w9-owner-acceptance-2026-10-22.md`, `reviews/g7c-gate7-definition-owner-acceptance-2026-10-22.md`);
P-042, P-058 (closure and step 6 replay sections) and P-062 (table A) in 03; 06s §§4, 8 and 9; 06l §4 and Step 1;
06u's header; W9 §4.5 and §11.1; the 04-plan Gate 7 section.

## 2. Method and commands

All commands ran in the worktree. None writes anything except this file.

1. `git fetch origin`; `git merge --ff-only origin/main` ("Already up to date"); `git rev-parse HEAD origin/main`;
   `git merge-base --is-ancestor 50371fac HEAD` (true).
2. `git rev-parse origin/main:<path>` for the seven files above, compared with each acceptance record's blob.
3. `git merge-base --is-ancestor <c> origin/main` for the accepted commits `a4e5310c`, `481dcca7`, `2b257da0`.
4. `git diff -U0 2b257da0 origin/main -- 03-decisions-and-open-questions.md 04-parallel-specification-and-foundation-pilot-plan.md`,
   compared line by line with the two status-only changes the G7-C acceptance record lists.
5. `git log -1` and `git merge-base --is-ancestor` for `df5ba1ec` and `bb9d91d4`;
   `gh pr view 381` and `gh pr view 386` (`--json number,title,state,mergedAt,mergeCommit,baseRefName,headRefName,files`).
6. Read P-058's closure and step 6 sections in 03, 06s §4 and §8, and grep for the INTEGRATED status across the plan tree.
7. `sha256sum` over the replay evidence P-058 cites in `s3-b19/`, compared with the prefixes P-058 records.
8. Jira, read-only through the Atlassian connector: `searchJiraIssuesUsingJql` for KAN-13, KAN-22 to KAN-26 and KAN-60
   (summary, status, labels, description, links, resolution, comments); `getJiraIssue KAN-26` with changelog;
   status of KAN-12, KAN-14, KAN-15, KAN-16, KAN-17, KAN-20 and KAN-103 for context.
9. Grep of W9, 04-plan, P-062, 06u and the acceptance records for provider, credential, P-042, "runtime evidence",
   "status word" and "Jira status".

## 3. Results

| # | Condition or item | Status | Evidence gathered here |
|---|---|---|---|
| 1 | G7-A, W9 and G7-C accepted at exact revisions | **MET** | See §3.1 |
| 2 | Gate 6 closure evidence under 06s §4 on file | **MET** | See §3.2 |
| 3 | Stephen's separate opening decision, naming the bounded intake | **Required, not yet given** | Not checked here, by design |
| 4 | 06l Step 1 as amended by P-062 A3 and A4 | **MET** | Items 4(a) to 4(d) |
| 4(a) | Distinct exact-subject check that the evidence on file is P-058's accepted closure evidence | **MET** | §3.2, done by this session, including off-repo hashes |
| 4(b) | No unresolved KAN-22 to KAN-26 contradiction | **MET** | §3.3: no substantive contradiction; description lags only, each reconciled |
| 4(c) | No provider or credential path in what opening would authorize | **MET** | §3.4 |
| 4(d) | No claim that a plan or Jira status is runtime evidence in the opening chain | **MET** | §3.5 |

### 3.1 Condition 1

| Document | Accepted subject (record) | On main `50371fac` | Verdict |
|---|---|---|---|
| G7-A, W0 post-terminal addendum rev. 3 | blob `1ebcf96f` | `1ebcf96ff071…` | identical |
| W9 draft 0.5 | blob `ea3a8e4a`; completion progress note says all three conditions hold and W9 is `accepted` | `ea3a8e4a5e89…`; the progress note is present in the record on main | identical |
| G7-C, 04-plan | blob `964e4e10` plus two status-only follow-ups | `96f34634`; diff from `2b257da0` is 4 changed lines | matches the record exactly |
| G7-C, 03 | blob `5b665beb` plus the P-062 status line | `9bc3dc73`; diff from `2b257da0` is one 5-line hunk | matches the record exactly |
| G7-C, 06l, 06-wp6, roadmap | `24961ba2`, `f5e3fbac`, `bbb87c71` | the same three blobs | identical |

The 04-plan diff is: line 96 (the Gate 7 `**Status (2026-10-22):**` line), line 109 (W9 governing row), line 111 (G7-C
governing row) and line 218 (the "Documents not all accepted" capability row). Lines 96 and 111 are the first
follow-up's two 04-plan lines; lines 109 and 218 are the second follow-up's two lines. The 03 diff is P-062's
`**Status:**` paragraph only, from "Proposed" to "Accepted by Stephen … at G7-C revision 3 (`2b257da0`)". No other line
of the accepted files differs. The Discovery inventory (`reviews/d8c-discovery-inventory-owner-acceptance-2026-10-22.md`)
and W9's other two completion conditions are on main as the W9 progress note says.

### 3.2 Condition 2 and item 4(a)

| Evidence | Check | Result |
|---|---|---|
| #381 | `gh pr view 381`: MERGED 2026-10-21T13:24:58Z into `main` from `docs/g6-phase5-step3-b6-b7`, merge commit `df5ba1ece6796cdc1055551a7e56575017dca2db`, title "[DECISION] P06: record 06s Gate 6 Phase 5 through closure, the final docs-only PR (P-058)"; files: 03 and `implementation/06s-phase5-runbook.md` only (docs-only) | ancestor of origin/main; subject matches |
| #386 | `gh pr view 386`: MERGED 2026-10-21T21:42:20Z into `main` from `docs/g6-phase5-replay`, merge commit `bb9d91d45493f7dfdf31aa1c3e6b34ecf6113a32`, title "[RESULT] P06: record the frozen-checkout replay that completes Phase 5 step 6 (P-058)"; same two files | ancestor of origin/main; subject matches |
| P-058 closure | 03 carries "**06s Gate 6 Phase 5 is closed (Stephen, 2026-10-21).**" with the run, actors, outcome (PARK, accepted project-use result), independent reviews, final evidence review (PASS WITH FINDINGS, m-1 to m-8 corrected), recovery, and known limits; then the step 6 replay section, which names #381 `df5ba1ec` as the precondition and ends "step 6 is complete, and Phase 5's live work is finished" | present on main |
| Replay bytes | `sha256sum` in `s3-b19/`: `live-replay/s6-replay.log` `51ce56fb…`, `replay-verify.json` `08ab7c0c…`, `spec-status.json` `dcf682f5…`, `step6-replay-checks.json` `35fa3c5d…`, `inputs/evidence-index.json` `66d45785…`, `live-replay/result.json` `1f4db7c6…`, `live-replay/result.md` `9ceafa14…` | every prefix matches the one P-058 records |
| Replay verdicts | `step6-replay-checks.json`: eight checks, all `"pass": true`; before and after both `[91, 1744f888…]`; all eleven SPEC-01 actions `completed` | consistent with P-058 |
| 06s §8 | §8 is a reporting rubric with no dated status line of its own. The applicable row, "All §4 requirements satisfied", reads "Capability status: INTEGRATED — Gate 6 is closed against the accepted 06s contract and its recorded evidence". That status is recorded on main in 06u's header (line 8, citing P-058, #381 and #386) and in 04-plan line 10; KAN-22 states it too | INTEGRATED |
| 06s §4 item 7 | Independent final evidence review, Stephen's closure, docs-only final PR and post-merge replay are all above. Jira reconciliation: KAN-12 and KAN-103 read Done (updated 2026-10-21) | satisfied |

The evidence on file is P-058's accepted closure evidence, at the exact subjects P-062 A1/A3 name.

### 3.3 Item 4(b): KAN-22 to KAN-26, with KAN-13 and KAN-60

The G7-C record's "Jira (G7C-D4): pending" section lists the changes. They were made on 2026-10-22 between 20:06Z and
20:07Z (comments and transitions), minutes before this check. KAN-26 read To Do in the first query and Done in the next
(changelog: To Do → Done at 20:07:09Z). Every listed change is now in place.

| Issue | Live status | Description and comments compared with the repository | Classification |
|---|---|---|---|
| KAN-22 (epic) | In Progress | The 2026-10-21 description says "Gate 7 is **not open**" (true) but calls the D-1 opening bar "proposed" and keeps the "[BLOCKED SUCCESSOR]" summary. The 2026-10-22 comment records all documents accepted and merged (#389), Gate 7 NOT OPEN and OWNER-BLOCKED, and this check pending; the epic stays open under G7C-D4 | Description lag, reconciled by the dated comment. Not a contradiction |
| KAN-23 | Done | Acceptance cites an "additive 06i" file. The 2026-10-21 comment records that the 06i name is unavailable; the 2026-10-22 Done comment points to P-062 D1, D2, B1 to B4 and list F. Matches the repository | No mismatch in substance; the 06i file name is a recorded description lag |
| KAN-24 | Done (2026-10-22 07:46 BST) | T1.28 DONE; W0 post-terminal items still open. The repository has W0 `post_terminal_recorded`, not `sealed`, W0-D1 and W0-D2 pending. "A-001 Manager confirmation" is amended by P-062 to Stephen's W0-D1 signature (G7-A record) | Consistent. Closed under the G7-A record |
| KAN-25 | Done | Acceptance: the W0 addendum and delta review are the first deliverable; Gate 6 completion and a separate opening decision remain prerequisites. The repository has G7-A accepted, the addendum a precondition of 06l Step 3 onward (P-062 B1 to B5), Gate 6 closure and the opening decision in the bar | Consistent. The 06i file name is a recorded lag, as for KAN-23 |
| KAN-26 | Done | The description's transition bar still names "Gate 6 pilot-promotion evidence". W9 §4.5 (on main) states that this bar "is superseded by D-1"; P-062 A8 keeps `pilot_promotion` evidence as a per-item condition; the Done comment says the same | Superseded wording, recorded as superseded in W9 §4.5. Not a contradiction |
| KAN-13 | Done | W9 fully accepted; Done comment cites the acceptance and completion records and #389. The description's "positive Gate 7 entry conditions from additive 06i" reads as the D-1 bar W9 §4.5 binds | Consistent; the 06i name is the same recorded lag |
| KAN-60 | To Do | "[BLOCKED PLANNING]" summary and `state-blocked` label; resume action "after KAN-12 is complete" (KAN-12 is Done). The 2026-10-22 status comment says WP6.7 execution has not started and nothing dispatches before Gate 7 opens; it stays open under G7C-D4 | Status lag recorded as intended by G7C-D4. Not a contradiction |

No Jira issue claims Gate 7 is open, that a transition or dispatch has happened, or a bar weaker than the repository's.
No substantive contradiction remains. The mismatches are description or summary lags, and each is reconciled by a
dated comment or by a repository record.

### 3.4 Item 4(c): no provider or credential path

- The opening bar authorizes only "the bounded intake" Stephen's decision names, and says "Opening by itself imports,
  transitions, dispatches and implements nothing" (04-plan Gate 7).
- P-042 (accepted 2026-07-26): ARS must not invoke a provider, spawn its CLI, call a provider API, select a provider,
  or read, store, resolve or pass OAuth credentials. Dispatch is operator-mediated.
- W9 §11.1 (W9-D2): "Gate 7 dispatch is operator-mediated under P-042 … No live-provider reactivation follows". W9 §2.1
  (the P-042 row) and §3.3 "Out of scope" ("provider invocation (P-042)") say the same.
- W9 §4.5's last row prohibits provider calls before their own gates.
- No text in the Gate 7 section, P-062 or the acceptance records adds a provider, API key or credential path. The only
  04-plan hit outside the bar is the W7 adapter boundary in the specification inventory (line 73), which W9 consumes
  only through P-042 (W9-A2).

### 3.5 Item 4(d): no plan or Jira status claimed as runtime evidence

- Condition 2 rests on P-058's record of a live run whose bytes are hash-indexed off-repo, and on the two merge commits
  checked in §3.2. It does not rest on a plan's status word or a Jira state.
- The opening bar names no Jira state as an input. Jira is cited only for reconciliation (KAN-17's binding table is
  about which documents bind, not about evidence).
- P-062 (03) treats the 06l §2.3 Jira table as "a dated observation" and requires current Jira state to be read live.
- W9 forbids the substitution directly: "a status word would stand in for evidence" is a stop condition (line 668);
  W9-T1 tests that "A status word never yields acceptance" (line 791); F-023 imports never turn status words into P-005
  decisions (line 592). The 04-plan objective says no legacy record is upgraded "by its status word".
- The 06u header and KAN-22 state INTEGRATED by citing P-058, #381 and #386, the evidence itself.

## 4. Findings

| ID | Grade | Finding | Recommended action |
|---|---|---|---|
| S1-1 | Minor | The G7-C acceptance record on main still says "Jira (G7C-D4): pending". The changes were made at 20:06–20:07Z on 2026-10-22, after the record merged. No repository record yet states that they were made or read back, which G7C-D4 requires ("Each change is read back"). This check read back all seven closures and both open-issue comments (§3.3), which covers the read for now | Record the G7C-D4 completion and its read-back as a status-only note when the next ARS record is written. It does not block opening |
| S1-2 | Info | The accepted commits `a4e5310c`, `481dcca7` and `2b257da0` are not ancestors of origin/main. PR #389 was squash-merged as `50371fac`. The acceptance records bind blobs and each says the commit was "not yet on main"; the blobs on main match (§3.1), so the acceptances carry | None. A later reader should check blobs, not commit ancestry |
| S1-3 | Info | Jira descriptions lag the repository: KAN-22 (opening bar "proposed", "[BLOCKED SUCCESSOR]"), KAN-60 ("[BLOCKED PLANNING]", `state-blocked`), KAN-13, KAN-23 and KAN-25 (a nonexistent "06i" addendum), KAN-26 (the superseded pilot-promotion bar). Each is reconciled by a dated comment or by W9 §4.5 | Optional description cleanup when KAN-22 and KAN-60 are next touched |
| S1-4 | Info | 06s itself carries no dated INTEGRATED status line; the §8 status is carried by 06u line 8, 04-plan line 10 and KAN-22 | None for opening |
| S1-5 | Info | The 06l file still shows the old Step 1 text. Its pointer note (line 27) sends readers to P-062, whose A3 and A4 are operative since acceptance. This check applied the amended wording | None |

No Blocking or Major finding.

**Known limit, not a finding.** Every review in the Gate 7 documentation chain, and this check, ran on one model family
(Claude Opus 5.5). This is the P-058 known limit. The check also relies on Stephen's local filesystem for the off-repo
evidence root; it did not re-run the replay.

## 5. Overall

**Condition 4 holds.**

| Condition | Status |
|---|---|
| 1. Documents accepted at exact revisions | MET |
| 2. Gate 6 closure evidence on file | MET |
| 3. Stephen's separate opening decision | Required, not yet given |
| 4. 06l Step 1 as amended | MET (4(a) to 4(d) all MET) |

Gate 7 status: OWNER-BLOCKED. The documents are accepted, the Gate 6 closure evidence is on file and the 06l Step 1
check holds. Stephen's opening decision, naming the bounded intake it authorizes, is required. Under 06l Step 1 that
decision may not be self-accepted by its author, and it authorizes no migration, cutover or retirement.
