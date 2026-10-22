# G7-C review: the Gate 7 definition and P-062, revision 1, at `1126eb60`

**Date:** 2026-10-22
**Reviewer:** an independent session distinct from the G7-C author, and not the G7-A, W9 or D8c session
**Skill:** `adversarial-design-review`, with `research-observer` running
**Runtime authority:** none. This report edits no other file. Nothing was written to `papers/`, `.apm/`, the vault,
any ARS store, GitHub or Jira.

## 1. Subject and verification base

| Identity | Value |
|---|---|
| Commit | `1126eb60a9b4a0f609519ae755f3894dd76f3112` on `claude/gate7-prep-docs-5202cf`, parent `06cda014` |
| 04-plan (Gate 7 section, currency note) | `04-parallel-specification-and-foundation-pilot-plan.md`, blob `967473e0` |
| 03 (P-062; notes in P-026, P-034, A-001, A-002) | `03-decisions-and-open-questions.md`, blob `d4f00858` |
| 06l (pointer note) | `implementation/06l-wp6-7-legacy-consolidation-sequencing.md`, blob `3c2d2adf` |
| 06-wp6 (WP6.7 pointer note) | `implementation/06-wp6-gate6-readiness-and-integration-plan.md`, blob `f5e3fbac` |
| Roadmap (§4 pointer note) | `02-design-and-deliverables-roadmap.md`, blob `3ebe7b31` |
| 06u (§13 progress lines) | `implementation/06u-gate7-prep-current-state-scope-note.md`, blob `8458909e` |
| Old-text base | origin/main `3fa437a160ab75c5fa0083fd35176006b1ee19a4` (unchanged at review time) |
| W9 compared | `design/09-migration-compatibility-and-pilot.md`, blob `ea3a8e4a` (identical at `1126eb60`) |
| G7-A compared | `transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md`, blob `1ebcf96f` |
| D8c inventory compared | `transition/discovery-backlog-observation-2026-10-22.md`, blob `026a9d10` |

All paths below are under `docs/plans/agentic-research-system/`. `04:N` and `03:N` mean lines of those files at
`1126eb60`; `W9:N` means lines of blob `ea3a8e4a`; `06l@base:N` means lines of 06l at `3fa437a1`.

## 2. Method

1. Read the full diff: `git show 1126eb60 --stat`, then `git show 1126eb60 -- <each file>`.
2. **Old texts.** A scratch script (`check_old.py`, in this session's scratchpad, not committed) parses every A–E row of
   P-062 from `git show 1126eb60:03-…`, extracts every double-quoted old segment, collapses runs of whitespace to one
   space, and counts occurrences in `git show 3fa437a1:<source>` after the same collapse. Run with
   `uv run python -I check_old.py`.
3. **E1–E12.** Extracted the twelve rows of W9 §16.2 from `git show ea3a8e4a` and the E rows of P-062 with the ID
   column removed, and ran `diff`.
4. **Superseded wording sweep.** `git show 3fa437a1:<path> | grep -n -i` over 06l, 04-plan, handoff 07, the W0
   manifest, 03, 06-wp6, the roadmap and the master plan for "pilot-promotion", "pilot promotion", "first intake
   deliverable", "current Manager", "fourteen", "while T1.28", "T1.28 closeout", "prior authority" and "rollback
   handle"; then read 06l §2.2 and Steps 1 to 7 and §6, the whole 04-plan, roadmap §§2–4 and W9 in full context at
   `3fa437a1`.
5. **Fidelity.** Read 06u §§5, 6, 7, 8, 11, 12 and 13; the G7-A acceptance record; the W9 acceptance record; the D8c
   acceptance record; G7-A §§10, 13, 15, 16 and 17; W9 §§4.5, 7.3, 10 to 16; 06s §§4, 7 and 8; handoff 07 in full;
   P-058's closure record (`03:3588-3645`).
6. **Evidence commits.** `git merge-base --is-ancestor` for `df5ba1ec` and `bb9d91d4` against `3fa437a1`: both are
   ancestors, with the expected subjects.
7. **Lint.** `uv run python tools/check_retired_imperatives.py` → "retirement gate: clean across
   docs/plans/agentic-research-system/implementation", exit 0.
8. **Jira.** The Atlassian connector needs authorization in this session and was not used. The KAN criteria below are
   the brief's summary of the 2026-10-22 read, not a read of the issues.

## 3. Verdict

**REWORK REQUIRED** (narrow).

| Severity | Count |
|---|---|
| Blocking | 0 |
| Major | 4 |
| Minor | 11 |
| Info | 7 |

The mechanical core holds. Every one of the 40 quoted old segments occurs in its source at `3fa437a1`, and E1–E12
are byte-identical to W9 §16.2. Nothing adds a Gate 6 closure prerequisite, and nothing opens or dispatches anything.

The four Majors are all restatement problems:

- **M-1:** the Gate 7 section invokes 04-plan §7 as written, and the roadmap §4 avoid-list binds the pilot through
  W9 §14.2. Both still state the old boundary, and neither is amended or listed.
- **M-2:** the section and D1 restate W9 §4.5 and §12.3 more narrowly than the accepted W9 text.
- **M-3:** the exit is not checkable against a fixed item set.
- **M-4:** G7C-D3's ordering cannot be realized under W9's batch rules as written.

Each fix is a text change inside P-062 or the Gate 7 section. None needs a new design.

## 4. Findings

### Major

**M-1 (Major). Gate 7 invokes stop and pilot rules that still state the superseded boundary.**
- *Claim.* The Gate 7 section says "§7 applies, together with W9 §13.4's stop criteria" (`04:171`). 04-plan §7 at
  `3fa437a1` says to stop "foundation or pilot progression" when "a second canonical writer or shared legacy path is
  required" and when "the prototype would need current-paper data/state migration".
  - W9 §7.3 (W9-D9, accepted) is a deliberate shared-writer exception for the vault Computational-Log and
    `CONVENTIONS.md` (`W9:379-383`).
  - W9 §12.1 transitions the P01 paper roots (`W9:560-572`).
  - Read literally, §7 stops both. W9 §13.4 restated §7 for Gate 7 and dropped those two bullets (`W9:661-676`), but
    the Gate 7 section applies both lists, so the stricter one governs.
- *Same family.* Three more passages are neither amended nor listed in F.
  - The roadmap §4 "Avoid as the first pilot" list still says "T1.28 or any task from either current APM-managed
    paper". W9 §14.2 says the integration pilot follows "the roadmap §4 rubric" (`W9:696`), yet the pilot's
    closed-reference items are P01 result files and decision entries. E7 replaces only the first bullet of the
    "should" list.
  - 04-plan §5 still excludes "migration or normalization of either current paper", the bullet beside the one E3
    amends.
  - The roadmap §3 DAG still reads "first post-APM paper pilot └─ W9/W10 wider migration/template work".
- *Failure scenario.* A reviewer of the first paper-root transition or the first shared-writer registration cites
  04-plan §7, which the Gate 7 section makes operative, and stops the item. Or an author reads the conflict away
  without any record. Either way, the exit's "each P01 paper root has transitioned" limb can be blocked by text that
  G7-C imported itself.
- *Impact.* Validity of the stop rule, and reachability of the exit. KAN-14's "no stale sequencing language" is not
  met.
- *Disposition.* Fix now.
- *Proposed text.*
  - Replace `04:171`'s first sentence with: "W9 §13.4's stop criteria apply. They restate 04-plan §7 for Gate 7
    items, and where the two differ, §13.4 governs a Gate 7 item."
  - Add three rows to P-062, each with the old text quoted from `3fa437a1`:
    - 04-plan §7, the "second canonical writer or shared legacy path" bullet → "…except W9 §7.3's shared-writer
      exception (W9-D9)";
    - 04-plan §7, the "current-paper data/state migration" bullet → "…outside W9's per-item transition";
    - roadmap §4's first "Avoid" bullet → "T1.28, or any legacy item outside the W9 §14.2 closed-reference rubric".
  - Add 04-plan §5's migration bullet and the roadmap §3 DAG to F, or amend them the same way.
- *Affected.* P-062 (A or E tables, F); 04-plan §4 Gate 7, §§5 and 7; roadmap §§3 and 4; W9 §§7.3, 12.1, 13.4 and
  14.2.

**M-2 (Major). The Gate 7 section and D1 restate W9 §4.5 and §12.3 more narrowly than the accepted W9 text.**
The narrowest restatement becomes the de facto rule. Four divergences:
- *(a) The `pilot_promotion` trigger.*
  - A8 (`04:126`; `03:3934`) binds the condition to "an item that would accept research evidence, change a result's
    citability or advance a claim", and then points to W9 §12.3 for the set.
  - W9 §12.3 assigns fixtures to kinds that fall outside that trigger: "every result-family observation" (F-018,
    F-037), "every import" (F-023), "every review" (S-007), "every `legacy-record-supersession`" (S-015), and
    successor compute context packets (F-029, F-030) (`W9:584-602`).
  - W9 §13.4 stops an item whose §12.3 set "fails or cannot be graded" (`W9:666`).
  - Under A8's trigger, an observation or import dispatches with no fixture evidence. Under W9 it cannot.
- *(b) The W0 seal.*
  - The per-item condition requires the eight §14 signatures only for "any ownership transition, cutover,
    deprecation or retirement that the Stage 1 or Stage 2 state affects" (`04:130`).
  - W9 §4.5 requires "Stephen's W0-D1 signature on all eight §14 items" before any closed-reference observation and
    batch acceptance (`W9:209`). That includes the integration pilot, which contains no ownership transition.
- *(c) Compute dispatch.*
  - W9 §4.5 lists the requirements for successor compute: the new pre-registration resolved by Stephen; §11.2
    coverage; F-016, F-029 and F-030 evidence; the W8 grant; adoption of any legacy input; and the accepted W0
    addendum (`W9:211`).
  - The parked-compute row (`04:146`) omits the W8 grant, the three fixtures and input adoption.
  - It also adds a precondition W9 §4.5 does not state: "legacy rows accepted `closed_reference`". See M-4.
- *(d) Read-only preparation (authority).*
  - W9 §4.5 allows "read-only observation by a non-author session with Stephen's authorization" (`W9:207`).
  - D1 (`03:3961`) allows "Document authoring and read-only preparation" with no qualifier.
  - D1 therefore permits a read-only observation by the producing session, without Stephen's authorization, that
    W9 does not. That is the independence the D8c observation was built to provide.
- *Impact.* Missing controls on the first batch and on observations; a silent widening of who may observe.
- *Disposition.* Fix now.
- *Proposed text.*
  - Add one sentence after `04:124`: "W9 §4.5's matrix is the operative precondition list for each class of action.
    The conditions below add to it and never relax it."
  - A8: "Each item dispatches only after the W6 `gate_stage: pilot_promotion` evidence for its W9 §12.3 set is
    produced, or explicitly waived by Stephen, with its fixture IDs named. W9 §12.3 assigns the set by item kind…"
  - The Phase 1/Stage 2 bullet: "Any closed-reference batch acceptance, ownership transition, cutover, deprecation or
    retirement needs Stephen's W0-D1 signature on all eight §14 items (W9 §4.5); an affected transition also needs
    W0-D2…"
  - The compute row: point to W9 §4.5's compute row instead of a partial list.
  - D1: "Document authoring and the preparation W9 §4.5 allows (read-only observation only by a non-author session
    with Stephen's authorization) may proceed."
- *Affected.* A8; the per-item conditions; D1; the parked-compute row; W9 §§4.5, 12.3 and 13.4.

**M-3 (Major). The exit is not checkable: the intake set is unpinned and has no item granularity.**
- *Claim.* The exit requires "every intake-manifest item has an attributed disposition" (`04:178`). The manifest is
  "06u §6, read with the corrections in 06u §13" (`04:155`).
  - 06u is a working note, corrected in place. Its §6.1 #105 row was "corrected in place on 2026-10-21" (`06u:424`),
    and §13 was edited in this very commit.
  - Neither the Gate 7 section nor P-062 pins a 06u blob.
  - The manifest's units are mixed:
    - one row is "Audit holes H1–H5, H7–H9";
    - another is "A-001, A-002, full Stage-2 disposition", which stands for twelve A-001 items and fifteen Stage 2
      rows;
    - §6.5's enforcement inputs "bind every Gate 7 deliverable" and cannot take any of the five dispositions;
    - §6.2's SPEC-01 continuation is ARS-native and fits none of the legacy-shaped dispositions except "deferred".
- *Second gap (G7C-D2).* Retirement is excluded from the exit (`04:182`). Nothing says which gate or rule governs a
  06l Step 6 cutover or Step 7 retirement after Gate 7 closes, while the opening decision authorizes only Gate 7's
  "bounded intake".
- *Failure scenario.* At closure, the set the closure is checked against is whatever 06u says that day. Two reviewers
  can count the holes as one item or eight. An in-place 06u edit after acceptance silently changes the exit.
- *Impact.* The exit and the capability table's "Every item disposed" row cannot be checked mechanically.
- *Disposition.* Fix now.
- *Proposed text.*
  - "The intake set is 06u §6 at blob `<pinned at acceptance>`, as one row per: audit hole H1–H9; A-001 item 1–12
    (G7-A §10); Stage 2 row (G7-A §9); park-set bullet (G7-A §12); T1.41; Markov-2; the SPEC-01 continuation;
    each §6.3 follow-up. §6.5 binds deliverables and is not an intake item. An addition or removal needs Stephen's
    recorded decision."
  - Add: "After closure, a remaining Step 6 cutover or Step 7 retirement proceeds under 06l as amended and W9 §4.5,
    by Stephen's separate decision" (or name the later gate).
- *Affected.* 04-plan §4 Gate 7 (intake, exit, capability table); G7C-D2; 06u §6.

**M-4 (Major). The parked-compute ordering (G7C-D3) cannot be realized under W9's batch rules as written.**
- *Claim.* The track table and G7C-D3 put the compute "after their legacy rows are accepted `closed_reference`"
  and say "it does not wait for the pilot to pass" (`04:146`; `03:4007`). Under W9:
  - Closed-reference acceptance is the light path, which ends in "Stephen's batch decision" (`W9:37-38`, `W9:427`).
  - "The first W9 batch is the integration pilot" (`W9:696`).
  - "A missed threshold stops further batches" (`W9:726`).
  - W9 §4.5 calls successor compute "likely the first Gate 7 action" and does not list closed-reference acceptance
    among its requirements (`W9:211`).
- *Consequence.* The T1.41 and Markov-2 legacy rows can reach `closed_reference` before the pilot passes only if they
  are members of the pilot batch itself. That is not stated, and it has to fit §14.2's "no successor compute" and
  20-item bound. Otherwise they need a second batch, which W9 places after the pilot, and the compute then waits for
  the pilot after all. G7-C's added precondition also contradicts W9 §4.5's "likely the first Gate 7 action".
- *Failure scenario.* Stephen accepts G7C-D3 on the stated rationale, and the first compute dispatch is then blocked
  until the pilot passes, the opposite of the decision. Or the rows are put into the pilot batch without the
  pre-registered thresholds anticipating them.
- *Impact.* The owner decision is not executable as worded.
- *Disposition.* Amend the decision text before acceptance.
- *Proposed text.* "The T1.41 and Markov-2 legacy rows are proposed as members of the integration-pilot batch
  (closed-reference result files, inside §14.2's rubric). Compute dispatches once those rows are accepted and W9 §4.5's
  compute row holds, without waiting for the batch's threshold evaluation. If the pilot misses a threshold, dispatched
  compute continues, because its outputs are successor-owned under `results/ars/`, and any wrong row is superseded under
  W9 §13.2." Or, if Stephen prefers, drop the closed-reference precondition and follow W9 §4.5 as written: dispatch
  first, rows later.
- *Affected.* G7C-D3; the parked-compute row; W9 §§4.5, 10, 14.2 and 14.3.

### Minor

**m-1 (Minor). Superseded wording neither amended nor listed in F.** Each of these, at `3fa437a1`, still states a
superseded rule or count:
- handoff 07 §2 item 2 ("**Gate 7's first deliverable is that dated W0 addendum + bounded delta review** — it is
  intake work for the gate, not a blocker on it") and its §3 first row ("first deliverable"). D-4 superseded both.
- the roadmap W0 "Review gate: Current Manager and Stephen agree…", superseded by W0-D1. Also the roadmap W1 status
  "legacy migration remains blocked by final post-T1.28 reconciliation".
- 03 P-012's "fourteen unlogged tasks" (`03@base:174`) and the W0 manifest's open-decision row "Decide whether the
  fourteen unlogged Plan tasks…" (manifest@base:340). G7-A counts fifteen rows (G7-A §9, §13).
- 06l Step 5's output "…owner decision, and rollback handle" (`06l@base:300`). E9 changes only the proof line's
  "tested rollback handle", but W9 §13.1 redefines the term for both.
- 06u §8.2 row 3, "The current Manager's A-001 confirmation", and 06u §6.1 row 1, W0 addendum "Outstanding". These are
  the pointed-to manifest, and §13 does not correct either.
- 04-plan §4's Gate 1–6 text, including Gate 6 "Greenfield paper preflight". The currency note flags §§1–3 and 5–8 as
  2026-06-30 text, but not §4's pre-Gate-7 subsections.

*Change:* add each to F with its current state, or amend, and extend the currency note to "§4 above Gate 7".

**m-2 (Minor). B5's replacement span is ambiguous.** B5's old text is two quotes joined by "…". The skipped sentences
("This work may produce… It is distinct from the later Gate-7 opening/dispatch decision:") end in a colon. If only the
quoted segments are replaced, a dangling clause remains. *Change:* "replaces the whole first paragraph of §6". In the
same spirit, state that E8 replaces only its quoted clause, so that "…and preserves all evidence; it never rewrites…"
still follows.

**m-3 (Minor). A8's fidelity to D-1.**
- Pointing to W9 §12.3 instead of 06u §5.2's parenthetical is within Stephen's authority already given. W9 §12.3,
  headed "(06u D-1)", is in the accepted W9 bytes, and W9-D12b accepts its two changes. All seven fixtures in the 06u
  list are in W9's set. So no separate owner decision is needed.
- But A8 drops D-1's accepted clause "with its fixture IDs named". F also lists "06u §5.2's fixture parenthetical" as
  a stale projection, although 06u is not at `3fa437a1` and §5.2 is an accepted proposal text, not a projection.
- *Change:* restore "with its fixture IDs named" (see M-2's text). Move the 06u §5.2 line out of F, since P-062
  Decision item 3 already records the deviation.

**m-4 (Minor). The P-058 follow-ups are restated beyond their source.**
- `04:150` says both follow-ups "block any project-use acceptance". P-058 lists them only as "Follow-ups" (`03:3633`).
- 06u §6.3 says project-use acceptance needs the review-record writer "or another option-A owner placement". It says
  no such thing of the verify-restore deriver.
- G7-C makes the deriver a blocker with no alternative, which no owner decision records. *Change:* limit the blocker
  to the review-record writer (or option A), as 06u §6.3 has it, or name this as an owner decision in the G7C-D table.

**m-5 (Minor). The opening bar omits 06l Step 1's own conditions.**
- The bar lists three conditions (`04:113-118`). 06l Step 1, as A3 and A4 amend it, adds:
  - a distinct exact-subject check of the closure evidence;
  - the stops on unresolved KAN-22–26 contradictions and on a provider or credential path.
- *Change:* append "and 06l Step 1 as amended (A3, A4) holds".

**m-6 (Minor). W0 currency beyond compute has no timing.**
- `04:137` says every G7-A §17 trigger "needs a further dated W0 addendum", but fixes the acceptance point only for
  compute.
- §17 also fires on proposing a Step 4 or 5 transition, on recording W0-D2, and on any `papers/P01-*` change.
- B1 and B2 name G7-A itself as the addendum required before Step 3, so after a trigger the requirement still points
  at a stale addendum.
- *Change:* "the latest accepted W0 addendum, which must post-date every G7-A §17 trigger that has fired, is required
  before the next 06l step that relies on W0 state".

**m-7 (Minor). The Discovery condition: attribution and omissions.**
- The hash-binding ("if the backlog's SHA-256 is no longer `96b5775c…`") and B4's "an inventory covers only the
  backlog bytes it observed" are attributed to W0-D4. Both come from the D8c acceptance record. W0-D4 says only "until
  G7-B's Discovery inventory is accepted".
- The condition also omits two things the D8c record attaches:
  - "a fresh handle-bound observation at transition time";
  - WT-2 and WT-3 are "revived only as new successor Candidates".
- *Change:* cite the D8c record, and add both.

**m-8 (Minor). KAN-17's mapping leaves A3 unmapped.**
- "Findings A1 to A4 … as A-001 items 3, 4, 9 and 12" maps A1→3, A2→4, A4→9 and B1–B7→12.
- A3, the missing calibration, enters through A-001 item 1 (T1.41, whose design answers A3, W9 §10 item 2).
- *Change:* "A3 through A-001 item 1 (T1.41; W9 §10)".

**m-9 (Minor). The capability rows are not mutually exclusive.**
- "Open; W9 machinery not accepted" and "Every item disposed" both hold if Stephen scopes out or defers every item
  before any machinery. "Machinery accepted; integration pilot not passed" overlaps "Every item disposed" the same way.
- No row covers a gate-level stop under §13.4.
- 06s §8 requires "exactly the applicable row".
- *Change:* "use the lowest row in the table whose condition holds", and fold a stopped state into the OPEN,
  INCOMPLETE rows ("stopped under W9 §13.4: <criterion>").

**m-10 (Minor). The compute risk tier is not named (06u D-6, §7 question 2).**
- 06u §7 found "the risk tier of these compute items" stated nowhere, and D-6 assigned it to G7-B and G7-C as a named
  decision point.
- W9-D3 settles family coverage but not the tier.
- *Change:* add "the risk tier of T1.41 and the Markov-2 recompute" to the owner decisions carried into intake
  (`04:167`).

**m-11 (Minor). Jira dispositions for KAN-22 and KAN-60.**
- G7C-D4's "KAN-22 and KAN-60 stay open until Gate 7 opens" implies closure at opening.
- KAN-60 aggregates 06l Steps 1–7, and KAN-22 is the Gate 7–9 readiness parent.
- *Change:* "stay open; their closure is not decided here". See also G7C-D4 below.

### Info

- **i-1.** Old texts: all 40 quoted segments occur at `3fa437a1` (counts 1). The one exception is A3's "exact Gate-6
  pilot-promotion evidence", count 3: Step 1's inputs and proof, plus §6, which B5 covers. A8 and E12 have no old text
  by design. E1–E12 are identical to W9 §16.2's twelve rows (`diff` empty).
- **i-2.** 06u, G7-A and W9 are not in `3fa437a1`. References to them were checked at `1126eb60`.
- **i-3.** `check_retired_imperatives.py` is clean, but its scope is `implementation/` only. 03, 04-plan and the
  roadmap are not scanned.
- **i-4.** No Gate 6 back-pressure. The bar cites only 06s §4's own closure evidence (`df5ba1ec`, `bb9d91d4`, both
  on main). Nothing reopens or adds to Gate 6. 06s §4 ("cannot add closure prerequisites", `06s:133`) and §7 are
  respected. W0-D1's signatory change narrows the signer to Stephen and expands no one's authority. W9 §13.1's
  manual-operation mode is reached only by pointer and is not widened. The one widening found is D1's unqualified
  "read-only preparation" (M-2(d)).
- **i-5.** The pointer-note ID lists (06l: A1–A5, B1–B5, C4–C6, E8–E11; 06-wp6: D1, D2; roadmap: E7; 03: E1, E4, C2,
  C3) match P-062 at this revision. They project P-062's table, so any renumbering in reconciliation must re-check them.
  The notes delegate status to P-062's status line, so they do not go stale on acceptance.
- **i-6.** D2 drops "sequencing doc only" from the WP6.7 DAG line. That is consistent with Gate 7 formalizing WP6.7
  execution, and is noted so that Stephen sees it.
- **i-7.** Every G7 review so far, this one included, ran on one model family (a P-058 known limit), noted and not
  treated as a finding. The Jira criteria were taken from the brief's summary, because the Atlassian connector was not
  authorized in this session.

## 5. Owner decisions G7C-D1 to G7C-D4

| ID | Disposition | Reason |
|---|---|---|
| G7C-D1 | **Agree, with one addition.** | One operative record is right, and the notes are correctly conditional on P-062's status. The addition concerns the W0 manifest §14. It is the checklist Stephen will actually sign, C1 amends it, and under this decision it gets no note. Rather than edit a frozen record, P-062 should require the W0-D1 signing record to cite C1 as the operative wording. Note also that the pointer notes are already committed in revision 1. If Stephen declines G7C-D1 or P-062, the notes must be removed in the next revision. |
| G7C-D2 | **Agree with excluding retirement; require the post-closure rule.** | Retirement depends on cutovers that can outlast the research items, and prose waits for Gate 9 (W9-D7). But the exit must say what governs a Step 6 or 7 action after closure, and the intake set must be pinned (M-3). |
| G7C-D3 | **Agree in substance; the text must change before acceptance.** | The rationale holds: the pilot measures import machinery, and A3's calibration should not wait on unrelated batches. As worded, though, the decision cannot be realized under W9's batch rules (M-4). Accept it only with M-4's text, or with W9 §4.5's dispatch-first ordering. |
| G7C-D4 | **Agree for KAN-14, KAN-16, KAN-17, KAN-23, KAN-25, KAN-13 and KAN-26, with read-back. Disagree with the KAN-22/KAN-60 wording.** | The closures follow from P-062's acceptance and the W9 acceptance record. KAN-17 closes only once m-8 is fixed, and KAN-14 only once M-1 is fixed ("no stale sequencing language"). KAN-22 and KAN-60 should stay open with no closure trigger set here (m-11). I could not read the issues (i-7). |

## 6. Completeness against the commissioning texts

| Requirement | Met? |
|---|---|
| Handoff 07 §1 item 2: a Gate 7 section formalizing W9 acceptance and WP6.7 execution, P01-A/P01-B first, with a currency note | Yes (`04:94-110`, `04:9`) |
| Handoff 07 §4: Gate 6 untouched; no self-attestation; read-only consumption; explicit old→new | Yes (i-4; 06u §6.5 by pointer; P-062 A–E) |
| 06s §7's G7-C list: W0 addendum, T1.41, Markov-2, parked work, H1–H9, T1.20, H3 | Yes by pointer to 06u §6.1, but unpinned (M-3) |
| 06u §8.1 item 3: section, currency note, manifest by pointer, old→new for P-026, P-034, WP6.7 and the bar, a capability table | Yes. The capability table is weak (m-9), and the currency note is incomplete (m-1) |
| 06u §8.2: G7-C places the compute items and the SPEC-01 continuation | Placed (`04:146-148`); compute ordering per M-4 |
| 06u D-6 (§7 questions) | Q1 by W9-D2, Q2 family rule by W9-D3, Q3 by W9-D1; the risk tier is missing (m-10) |
| 06u D-9 (prose waits for Gate 9) | Yes (`04:148`) |
| KAN-14 | Partly: stale language remains (M-1, m-1) |
| KAN-16, KAN-23 | Yes in substance (D1, D2), with D1's qualifier fix (M-2(d)) |
| KAN-17 | Yes, with A3's mapping (m-8) |
| KAN-25 | Yes (B1–B5; `04:120-121`) |
| G7-A acceptance "carried to G7-C": the §15 list, the A-001 and 06l Step 3 amendments, the WP6.7 wording, W0-D4's condition | Yes (F, C2, C4–C6, D1–D2, B4) |
| W9 acceptance "carried": the 06l, P-026, P-034, 04-plan and roadmap amendments, and W0-D4's condition | Yes (E1–E12, B4), but see M-1 for what §16.2 missed |

## 7. Revision plan

- **Immediate (author):** M-1 to M-4, m-1 to m-11.
- **Owner decisions:** G7C-D1 to G7C-D4 as dispositioned above. Whether the verify-restore deriver blocks project-use
  acceptance (m-4) becomes an owner point only if the author keeps it.
- **Later work:** widen `check_retired_imperatives.py`'s scope to 03, 04-plan and the roadmap, or record why not
  (i-3). Mechanize old-text occurrence as a re-runnable check that the reconciliation and this review can share. This
  review's script is a scratch file.

## 8. Change log

- Created this file. No other file was edited.
