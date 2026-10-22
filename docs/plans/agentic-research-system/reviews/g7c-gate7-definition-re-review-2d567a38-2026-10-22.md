# G7-C re-review: revision 2 at `2d567a38`

**Date:** 2026-10-22
**Reviewer:** the session that reviewed revision 1 (`e8bcf243`); not the G7-C author, and not the G7-A, W9 or D8c
session
**Skill:** `adversarial-design-review` (remediation re-review), with `research-observer` running
**Runtime authority:** none. This report edits no other file. Nothing was written to `papers/`, `.apm/`, the vault,
any ARS store, GitHub or Jira.

## 1. Subject and scope

| Identity | Value |
|---|---|
| Commit | `2d567a38` on `claude/gate7-prep-docs-5202cf`; diff `e8bcf243..2d567a38` (6 files, +191 −67) |
| 04-plan | blob `431d104c` |
| 03 (P-062) | blob `eab7abde` |
| Reconciliation map | `reviews/g7c-gate7-definition-reconciliation-2026-10-22.md` (added in `2d567a38`) |
| W9 compared | blob `ea3a8e4a`, unchanged at `2d567a38` |
| Old-text base | origin/main `3fa437a1` |

All paths below are under `docs/plans/agentic-research-system/`. `04r2:N` means lines of the 04-plan at `2d567a38`.

Scope, as requested:
1. the closure of M-1 to M-4 and m-1 to m-11;
2. what the new texts introduce: table G, the added F items, the 38-unit intake set, G7C-D3 and the parked-compute
   row, opening-bar condition 4, the W0-currency wording, and the capability rows;
3. the pointer-note ID lists;
4. E1–E12 against W9 §16.2.

Unchanged revision 1 content was not re-reviewed.

## 2. Method

- `git diff e8bcf243 2d567a38`, read in full, with the reconciliation map.
- **Old texts.** `check_old_r2.py` (this session's scratchpad, not committed) extends the revision 1 script. It parses
  every A–G row of P-062 from `git show 2d567a38:03-…`, adds the seven quoted F items new in revision 2 with their
  named sources, collapses whitespace, and counts occurrences in `git show 3fa437a1:<source>`. Run with
  `uv run python -I`.
- **E1–E12.** The same `diff` as in revision 1: the W9 §16.2 rows against P-062's E rows with the ID column removed.
- **Intake units.** Checked against G7-A §9 (the fifteen Stage 2 rows), §10 (the twelve A-001 items) and §12 (the
  park set), and against the claim-trace audit §3.3 (holes H1–H9).
- **D3 and the compute row.** Checked against W9 §4.5 (`W9:203-216`), §10, §14.2 and §14.3.
- **Lint.** `uv run python tools/check_retired_imperatives.py` → clean, exit 0.

## 3. Verdict

**PASS WITH FINDINGS.**

| Severity | Count |
|---|---|
| Blocking | 0 |
| Major | 0 |
| Minor | 6 |
| Info | 6 |

Every revision 1 finding is closed by the stated change. The six new Minors are local wording and consistency points in
the new texts. Accepted texts cannot be edited later, so I recommend fixing r-1 and r-2 before Stephen's acceptance.
The other four can be fixed in the same pass or carried.

## 4. Closure of the revision 1 findings

| Finding | Status | Evidence at `2d567a38` |
|---|---|---|
| M-1 | **Closed** | The stop rule now says §13.4 governs (`04r2:192`), and so does Decision item 1. G1 and G2 amend §7's two bullets, G3 the §5 bullet and G4 the roadmap avoid bullet, each old text present at `3fa437a1` (§5 below). The roadmap §3 DAG is in F. The currency note names §7. |
| M-2 (a)–(d) | **Closed** | "W9 §4.5's matrix is the operative precondition list … never relax it" heads the per-item conditions. A8 covers "each item", with "its W9 §12.3 set" and "every result-family observation, every import and every review". The §14 signatures are required before "any closed-reference batch acceptance" (W9 §4.5, `W9:209`). The compute row points to W9 §4.5's row. D1 carries W9 §4.5's qualifier word for word. |
| M-3 | **Closed**, with r-1 | A fixed set of 38 units; additions and removals need Stephen's decision; the acceptance record names the 06u blob; T1.20, #105 and §6.5 are explicitly not units; ARS-native units can be "completed under its own bar"; the post-closure rule is in the exit and in G7C-D2. 12 + 3 + 15 + 5 + 1 + 2 = 38. |
| M-4 | **Closed**, with r-2 | The legacy rows are proposed as pilot members, compute follows W9 §4.5's row, and the pilot's threshold evaluation does not hold compute back. That matches W9 §4.5, which adds no closed-reference precondition and calls compute "likely the first Gate 7 action". A pilot stop under §13.4 applies to "a transition, batch or pilot", not to dispatched compute, so "a missed threshold does not stop dispatched compute" is consistent with W9. |
| m-1 | **Closed** | G5 and G6 amend. The seven new F quotes are all present at `3fa437a1`. The 06u corrections are in 06u §13. |
| m-2 | **Closed** | B5's source cell names the whole paragraph. The note under table E fixes the clause scope. |
| m-3 | **Closed** | "with its fixture IDs named" is restored, and the 06u §5.2 line has left F. |
| m-4 | **Closed** | Only the review-record writer, or option A, is a precondition (06u §6.3). The deriver is an intake unit. |
| m-5 | **Closed**, with r-3 | Opening-bar condition 4. |
| m-6 | **Closed**, with r-5 | B1, B2, B4 and the section now tie the requirement to fired §17 triggers. |
| m-7 | **Closed** | The D8c record is cited, and the transition-time observation and the WT-2/WT-3 rule are added. |
| m-8 | **Closed** | A3 is mapped through item 1 (T1.41; W9 §10 item 2). |
| m-9 | **Closed**, with r-4 | "Lowest row whose condition holds", with "Open;" prefixes. I walked every reachable state: closure beats all rows, "every unit disposed" beats the machinery and pilot rows, and the two pre-opening rows exclude each other. |
| m-10 | **Closed** | The risk tier is among the owner decisions carried into intake. |
| m-11 | **Closed** | G7C-D4: "stay open, and their closure is not decided here". |

**G7C-D1 to G7C-D4 as revised.** All four now carry the changes I asked for. D1 adds the C1 citation in the signing
record and the removal of the notes if declined. D2 adds the post-closure rule. D3 is rewritten to M-4's first option.
D4 changes the KAN-22/KAN-60 wording. I agree with all four as now worded, subject to r-2 for D3.

## 5. Old texts and E1–E12

- **48 quoted segments checked:** 41 in tables A–G and 7 new F items. All are present at `3fa437a1`. A3's "exact
  Gate-6 pilot-promotion evidence" occurs 3 times, as in revision 1: Step 1's inputs and proof, plus §6, which B5
  covers. Every other segment occurs exactly once. G1–G6 are each present once.
- **E1–E12** are still byte-identical to W9 §16.2's twelve rows (`diff` empty).

## 6. New findings

**r-1 (Minor). The intake set double-counts two objects.** It de-duplicates against A-001, but not between holes,
park-set bullets and Stage 2 rows.
- *Hole H4 and the park-set bullet are one object.* The audit's H4 is the "§6.2 / §4.3 / §S6 rewritten prose
  (rulings on file; reviewed #106 rewrite reverted)" (audit §3.3). The park-set bullet "the §6.2/§4.3/§S6 prose
  directions" is the same object, and both are counted (`04r2:170`, `04r2:172`).
- *The #106 dedup prose and two Stage 2 rows are one object.* The park-set bullet "the #106 dedup prose" is the
  content of Stage 2 rows T2.17a and T2.24. G7-A §9 records both as `superseded` because #106 was reverted by #112,
  and both are counted among the fifteen.
- *Failure.* One object gets two units, which can receive contradictory dispositions. For example, the hole is
  "deferred to Gate 9" while the park-set bullet is "scoped out". The table's "each counts once" holds only for
  A-001.
- *Change.* Either merge H4 into the park-set prose-directions unit (37 units), or keep both and add: "H4 and the
  park-set prose-directions bullet, and the #106 dedup prose with rows T2.17a and T2.24, take one consistent
  disposition."

**r-2 (Minor). "Compute waits neither for those rows' acceptance" can override W9 §4.5's adoption rule.**
- W9 §4.5 requires "adoption of any legacy input it uses (prefer regeneration)" before compute dispatch. Adoption in
  turn requires "the item's closed-reference acceptance" (`W9:210-211`).
- If a legacy row proposed for the pilot is also an input the compute uses, the row's sentence and §4.5 disagree. One
  example: 06u §6.1 says the Markov-2 recompute's L² side is "certified from the #129 cells". The row's sentence
  reads as an exception to the governing rule.
- *Change.* Append to the row and to G7C-D3: "unless the compute uses that row as an input. A used legacy input needs
  its closed-reference acceptance and adoption first (W9 §4.5)."

**r-3 (Minor). Opening-bar condition 4's spelled-out list omits one of 06l Step 1's stops.**
- Condition 4 (`04r2:119`) restates 06l Step 1 after a colon, as if complete.
- 06l Step 1 also stops on "a claim that a plan or Jira status is runtime evidence" (06l at `3fa437a1`, Step 1's
  stop line).
- *Change.* Add that stop, or end the list with "and 06l Step 1's other stop conditions".

**r-4 (Minor). The "Documents accepted" row ignores condition 4.**
- The row says Stephen's opening decision is the remaining requirement (`04r2:216`). Under the new bar, the 06l
  Step 1 check and the Jira-contradiction condition may also be outstanding.
- *Change.* "…the Gate 6 closure evidence is on file; the 06l Step 1 check (condition 4) and Stephen's opening
  decision are required."

**r-5 (Minor). The W0-currency rule is restated two ways.**
- B1 and B2 require the current W0 addendum "before any Step 3 or later action".
- The section's bullet requires it "before the next 06l step that relies on W0 state" (`04r2:144`), a phrase defined
  nowhere. That reading is narrower.
- *Change.* Use B1's wording in the section, or define "relies on W0 state" as "any 06l Step 3 or later action".

**r-6 (Minor). The governing-documents table is stale against the section's own status line.** It still says "G7-C:
this section and P-062 | Revision 1, under review" (`04r2:111`), while the status line and P-062 say revision 2.
*Change:* "Revision 2, under review", or "see P-062's status line", so the row does not need editing at each revision.

## 7. Info

- **i-1.** The reconciliation's check report says "57 quotes, all present, each with count 1". My independent count
  finds 48 quoted segments, all present, but A3's occurs 3 times, not once. The difference in totals may be how
  segments are split. The "each with count 1" claim is not accurate. Presence, the property that matters, holds.
- **i-2.** E1–E12 are unchanged and identical to W9 §16.2.
- **i-3.** The pointer-note ID lists are correct after table G:
  - 06l lists A1–A5, B1–B5, C4–C6, E8–E11 and G6, every row whose source is 06l;
  - roadmap §2 lists G5, and roadmap §4 lists E7 and G4;
  - the 04-plan currency note covers §§2, 5, 6 and 7 (E2, E3, E5, E6, G1–G3);
  - the 03 notes (E1, E4, C2, C3) and the 06-wp6 note (D1, D2) are unchanged and still correct.
- **i-4.** `check_retired_imperatives.py` is clean. Its scope is still `implementation/` only (revision 1 i-3; later
  work).
- **i-5.** The nine Discovery backlog items are not intake units, so they do not bind the Gate 7 exit. That is
  consistent with 06u §6 and with W9 §15, which routes them through W11. It is noted so that Stephen sees it.
- **i-6.** This review ran on the same model family as the author (a P-058 known limit). Jira was not read; the
  Atlassian connector is not authorized in this session.

## 8. Change log

- Created this file. No other file was edited.
