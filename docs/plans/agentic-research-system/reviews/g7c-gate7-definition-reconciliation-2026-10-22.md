# G7-C reconciliation: revision 1 → revision 2

**Date:** 2026-10-22
**Author:** the G7-C author session
**Review reconciled:** `reviews/g7c-gate7-definition-review-1126eb60-2026-10-22.md` (`e8bcf243`), REWORK REQUIRED,
narrow: 0 Blocking, 4 Major, 11 Minor, 7 Info
**Subject after reconciliation:** revision 2, in the commit that adds this file. It touches the 04-plan Gate 7 section
and currency note, P-062, the pointer notes in 06l and the roadmap, and 06u §13.
**Runtime authority:** none. Author reconciliation is not acceptance.

All paths are under `docs/plans/agentic-research-system/`.

## 1. Findings and changes

| Finding | Disposition | Change in revision 2 |
|---|---|---|
| **M-1** §7 and the roadmap avoid-list still state the old boundary | Fixed | The Gate 7 stop rule now reads: "W9 §13.4's stop criteria apply. They restate §7 for Gate 7 items, and where the two differ, §13.4 governs a Gate 7 item." P-062 Decision item 1 says the same. New table G amends 04-plan §7's two bullets (G1, G2), the 04-plan §5 migration bullet (G3) and roadmap §4's first avoid bullet (G4), using the reviewer's texts. The roadmap §3 DAG is listed in F. The 04-plan currency note now names §7 |
| **M-2(a)** A8's trigger narrower than W9 §12.3 | Fixed | A8 and the Gate 7 bullet now bind "each item" to "its W9 §12.3 set ... with its fixture IDs named", naming observations, imports and reviews. P-062 Decision item 3 records why this stays within D-1 |
| **M-2(b)** W0 seal narrower than W9 §4.5 | Fixed | The Phase 1 and Stage 2 bullet now requires the §14 signatures for "any closed-reference batch acceptance, ownership transition, cutover, deprecation or retirement (W9 §4.5)". W0-D2 binds affected transitions |
| **M-2(c)** compute row partial | Fixed | The parked-compute row now points to W9 §4.5's successor-compute row as its precondition list, plus W9 §10 item 4's output root. The added closed-reference precondition is gone (see M-4) |
| **M-2(d)** D1's unqualified "read-only preparation" | Fixed | D1 new text: "the preparation W9 §4.5 allows (read-only observation only by a non-author session with Stephen's authorization)" |
| **M-2** general | Fixed | The per-item conditions open with: "W9 §4.5's matrix is the operative precondition list for each class of action. The conditions below add to it and never relax it." |
| **M-3** exit not checkable | Fixed | The intake manifest is replaced by a fixed **intake set** of 38 units: A-001 items 1–12, holes H4/H5/H8, fifteen Stage 2 rows, five park-set bullets, the SPEC-01 continuation and the two P-058 follow-ups. Units overlapping A-001 count once. Additions and removals need Stephen's recorded decision. The acceptance record names the 06u blob read for pointers. T1.20, #105 and §6.5 are explicitly not units. The exit uses units and adds "completed under its own bar" for ARS-native units. A post-closure rule now covers Step 6 and 7 actions (G7C-D2) |
| **M-4** G7C-D3 not realizable | Fixed, the reviewer's first option | The legacy rows are proposed as integration-pilot members within §14.2's rubric and bound. Compute follows W9 §4.5's row and waits neither for their acceptance nor for the threshold evaluation. A missed threshold does not stop dispatched compute; a wrong row is superseded under W9 §13.2. G7C-D3 is rewritten to match |
| **m-1** superseded wording neither amended nor listed | Fixed | Amended: the roadmap W0 review gate (G5) and 06l Step 5's output "rollback handle" (G6). Listed in F: handoff 07 §2 item 2 and §3's first row; the roadmap W1 status; the roadmap §3 DAG; the "fourteen" in P-012 and in the W0 manifest's open-decision row; 06u §6.1 row 1 and §8.2 row 3, corrected in 06u §13. The 04-plan currency note now covers §4's Gates 1 to 6 |
| **m-2** B5 span; E8 clause | Fixed | B5's source cell now says the new text replaces the whole first paragraph of §6. A note under table E says each E row replaces only its quoted clause, with E8 as the example. The E rows themselves are unchanged, so they stay identical to W9 §16.2 |
| **m-3** A8 fidelity | Fixed | "with its fixture IDs named" restored. The 06u §5.2 line is removed from F, and Decision item 3 records the deviation. As the reviewer found, no separate owner decision is needed |
| **m-4** P-058 follow-ups overstated | Fixed | Only the scientific-review record writer, or another option-A owner placement, is a precondition for project-use acceptance (06u §6.3). The verify-restore deriver is an intake unit, not a blocker |
| **m-5** opening bar omits 06l Step 1 | Fixed | Opening bar condition 4: 06l Step 1 as amended (A3, A4) holds, spelled out |
| **m-6** W0 currency timing | Fixed | The section's W0 currency bullet and B1, B2 and B4 now require the latest accepted W0 addendum to post-date every fired G7-A §17 trigger, before the next step that relies on W0 state |
| **m-7** Discovery attribution and omissions | Fixed | The section and B4 cite the D8c acceptance record for the byte binding, add the fresh handle-bound observation at transition time, and add (in the section) that WT-2 and WT-3 are revived only as new successor Candidates |
| **m-8** A3 unmapped | Fixed | The KAN-17 row maps A1→3, A2→4, A4→9, B1–B7→12, and A3 through item 1 (T1.41; W9 §10 item 2) |
| **m-9** capability rows not exclusive | Fixed | "Lead with the lowest row in the table whose condition holds". The rows after opening are prefixed "Open;". A stop under W9 §13.4 is reported inside the OPEN, INCOMPLETE rows |
| **m-10** compute risk tier | Fixed | Added to the owner decisions carried into intake |
| **m-11** KAN-22 and KAN-60 | Fixed | G7C-D4: "stay open, and their closure is not decided here" |
| **i-1 to i-7** | Noted | i-5: the pointer-note ID lists were re-checked after table G was added. 06l now lists G6. The roadmap notes list E7 and G4 (§4) and G5 (§2). The 04-plan currency note covers G1 to G3. A to E IDs are unchanged. i-3 and the later-work items remain later work, recorded in §3 |

## 2. Owner-decision dispositions taken in

| ID | Reviewer | Revision 2 |
|---|---|---|
| G7C-D1 | Agree, with the C1 citation addition | Adds: the record of Stephen's W0-D1 signing cites C1 as the operative §14 wording, and the notes are removed if the decision or P-062 is declined. The pointer-note list now includes the roadmap §2 and the 04-plan currency note |
| G7C-D2 | Agree; require the post-closure rule | Post-closure rule added to the decision and the exit |
| G7C-D3 | Agree with M-4's text | Rewritten per M-4's first option |
| G7C-D4 | Agree except for KAN-22/KAN-60 | KAN-22 and KAN-60 stay open with no closure trigger. KAN-17's and KAN-14's preconditions (m-8, M-1) are fixed |

## 3. Checks run on revision 2

- **Old-text occurrence.** A scratch script (author scratchpad, `check_p062_quotes.py`) collapses whitespace and counts
  each quoted old text in `git show 3fa437a1:<source>`. Result: 57 quotes, all present, each with count 1. That covers
  the A–E segments, the new G1–G6 and the new F items.
- **E1–E12.** The rows are byte-identical to W9 §16.2 (blob `ea3a8e4a`), ID column removed.
- **Retirement gate.** `uv run python tools/check_retired_imperatives.py` is clean.
- **Later work, not done here.** Widening the retirement gate's scope to 03, 04-plan and the roadmap (i-3), and making
  the old-text check a shared, committed tool. Both remain proposals, outside this documentation track.
