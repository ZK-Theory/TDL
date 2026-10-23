# WP9.0 reconciliation: revision 2 against the review of `a427084e`

**Date:** 2026-10-23<br>
**Author:** the WP9.0 author session (the author of revision 1)<br>
**Review:** `reviews/wp9-0-review-a427084e-2026-10-23.md` (commit `079f0095`). Verdict REWORK REQUIRED: 3 Blocking, 12
Major, 10 Minor, 7 Info.<br>
**Owner decisions:** P-066. Stephen chose the recommended option on M-1 (new ID S-017), M-12 (`accepted_w9.py` is
outside P-065) and m-3 (a W9 §12.3 erratum).<br>
**Status:** Revision 3 (§4) is ready for the review session's narrow confirmation. It is not accepted. Point §3.1 is
settled by P-067.

## 1. Files in revision 2

Paths are under `docs/plans/agentic-research-system/` unless they start at the repository root.

| File | Change |
|---|---|
| `design/06d-w9-s016-operator-mediated-addendum-2026-10-23.md` | Rewritten. It now reserves S-017 and records S-016 r1 as unchanged. The file name keeps `s016`, the name 06v O-15 gave it |
| `transition/w9/w9-segmentation-contract-v1.md` | Rewritten to match the reference implementation, with a census section |
| `transition/w9/w9-membership-table-template.md` | Revised |
| `03-decisions-and-open-questions.md` | P-065 item 2 corrected (with a correction note); P-066 added |
| `tools/w9_segmentation.py` (repository root) | New. The reference implementation of `w9-segmentation/1.0.0`, a non-runtime tool |
| `tests/tools/test_w9_segmentation.py` (repository root) | New. 31 synthetic vectors |
| this file | New |

## 2. Dispositions

| Finding | Disposition | Where |
|---|---|---|
| **B-1** S-016 r1 is materialized and executed | Fixed. 06d §1 has a current-state paragraph citing the package, its tree and blob, its graders and mutation, its commits, its execution and its pins. "Deferred" is gone. S-016 r1 stays unchanged, executed and pinned | 06d §1 |
| **B-2** log anchor grammar | Fixed: a level-2 or level-3 heading whose text starts with a date token, `~?YYYY-MM(-DD([a-z]\|/DD)?)?`, followed by the end, a space, a tab or `(`. The separator plays no part. A heading of level L ends at the next heading of level ≤ L or the next date anchor, so sub-headings stay inside entries and the page title is its own structural block. Trailing `---` rules are structural, as in D8c. "Looks like an anchor" is closed: a level-2/3 heading starting with a digit, or `~` and a digit, that fails the grammar. Anchor text is the heading bytes as UTF-8, never repaired. The census of the live page (the review's bytes, `de44a67b…`) gives 255 entries, the title as the one structural block, and no blockers, including month-only `## 2026-03` at L5611 | Contract §3, §4, §8 |
| **B-3** tracker selectors | Fixed. Working Notes anchor: a top-level `- ` bullet under `## Working Notes`. Anchor text: the full first line, so same-date entries are not duplicates; the reconciliation of W9 §5.5's "two Working Notes under one date heading" is in §4.3. Dated entries are flagged by the `- **date` grammar; undated entries are items too. Task rows: stage tables only (header first cell `Task`), cell grammar `[0-9]+\.[0-9]+[a-z]*(-[a-z]+)?`, ID `T` + cell, header and separator rows structural, other tables out of selector. Census: 95 task rows, 114 notes (88 dated, 26 undated), no blockers | Contract §3, §4.3, §8 |
| **M-1** variant IDs | Fixed by Stephen's decision (P-066 item 1): a new ID, S-017. No suffix grammar, no schema change | 06d §1, §2; P-066 |
| **M-2** checker rule | Fixed. W9 §11.2's sentence is quoted exactly. The requester or proposer (including the migration analyst) is excluded as this addendum's stated addition | 06d §2 |
| **M-3** controls and H row | Fixed. Six pre-control cases: no second family; (b); (c); excluded checker; late check; lost verifier at grading. The post-dispatch case grades blocking `unable_to_grade` with no substitute. The H grader is named `s-017-human-authority`, with its question | 06d §2, §5 |
| **M-4** terminator and BOM | Fixed: the terminator is CRLF when CR precedes the LF, else LF. A line-1 BOM is hashed but ignored for matching and blankness. Vectors cover CRLF blanks, BOM headings and BOM frontmatter. All nine BOM-led stage logs parse | Contract §2; vectors |
| **M-5** line-based or Markdown-aware | Fixed: purely line-based. Fences, setext, HTML and indented code are not recognized. ATX headings are at column 0 only, one space after the hashes, and closing hashes stay in the text. Table cells split on unescaped `\|` | Contract §2.6, §2.7, §3 |
| **M-6** conventions units | Fixed. Structural: blank lines, rule lines, the footer, headings, the H1 and the preamble. Base indent is column 0. Bullets (`- ` or `* `) continue over indented lines, including after blank lines. A table is one unit. A paragraph is a maximal run of other non-blank lines. Census: 70 units in 10 sections, no duplicates | Contract §3, §8 |
| **M-7** covered region; D8c | Fixed. Inventories declare a covered region (a line range plus anchor-line hashes, or "from the first anchor after" a named structural line) and may declare structural ranges whose headings are suppressed and recorded. §1 now reads "adopts D8c's span rule; changes its anchor text and region rule". D8c's anchor texts are superseded, and its m-3 closes only on re-observation. With region L23 to the end, the nine D8c spans, lengths and hashes reproduce exactly | Contract §1, §3, §8 |
| **M-8** input and vectors versus D-7 | Fixed. §6 names the interim reader (the reference implementation, over bytes copied once from the live page, with D8c §7's limits recorded) and WP9.3's recheck. The reference script and vectors are committed now. Offsets are relative to the bytes read, and the export carries live-page offsets and lengths | Contract §4.2, §6, §7 |
| **M-9** container membership | Fixed: a container carries its own shape only; the root `""` is listed | Template §3 rule 4 |
| **M-10** array patterns | Fixed: a `[*]` segment means every index and never matches a key. Homogeneity is defined. The importer expands patterns against the observed bytes. A file with a key literally `[*]` uses no patterns | Template §3 rules 2 and 5 |
| **M-11** self-hash and early binding | Fixed. Review and acceptance identities are out of the table, and the W9 record binds them. `applies_to` binds identity kind, blob, SHA-256 and size of the bytes the author read. The first observation must match them, or block for re-review | Template §1, §3 rule 10, §4 |
| **M-12** `accepted_w9.py` | Fixed by Stephen's decision (P-066 item 2). P-065 item 2 is corrected, with a correction note quoting the struck clause | P-065, P-066 |
| **m-1** W6 version | Fixed: version 0.3 | 06d header |
| **m-2** 06b format | Fixed: priority, lanes, two-axis provenance and dependency columns; a §3 on priority and change-gate effect; S-017 mapped to the agent/model routing and event/task schema rows | 06d §2, §3 |
| **m-3** applicability; W9 erratum | Fixed. The reviewer proposes and Stephen fixes; for an R3 item the only permitted outcome is "applicable". The W9 §12.3 erratum is recorded in P-066 item 3, with W9's bytes unchanged | 06d §4; P-066 |
| **m-4** WP9.7 home | Fixed: "candidate home WP9.7, fixed at its dispatch" | 06d §5 |
| **m-5** CONVENTIONS pin | Fixed: blob `4620c716…`, 33,645 bytes, SHA-256 `d04fe97e…8589`; commit `4b143c92` given only as context | Contract §3 |
| **m-6** time and path form | Fixed: start and end times, UTC with microseconds; the path form and any junction or link | Contract §5.1, §5.2; census in §8 |
| **m-7** vectors and independence | Fixed. The vector list covers every case the review named, plus more. Independence: a session distinct from the contract's author and from WP9.3's implementer must reproduce every vector before any export or observation is accepted, L-0b included | Contract §7; vectors |
| **m-8** two-way exhaustiveness; parsing | Fixed. Unassigned observed pointers block, and so do table pointers absent from the bytes. A duplicate key blocks. `NaN`, `Infinity` and `-Infinity` are accepted as number leaves and recorded | Template §3 rules 1 and 2 |
| **m-9** `class_source` | Fixed: renamed `definition_source`; the table assigns no W0 class (O-27) | Template §3 rule 8, §4 |
| **m-10** actor rules | Fixed. W9 §5.2's exclusion is cited as W9's; the others are marked as the template's additions. The migration analyst is excluded from authoring. The reviewer's exclusions and distinct sessions are stated | Template §2 |
| I-1, I-2, I-3, I-7 | Recorded; no change | — |
| **I-4** landscape family | Adopted: the real table's author decides from G7-A §6.1 | Template §5 |
| **I-5** final terminator | Adopted | Contract §5.4 |
| **I-6** version bump | Adopted | Contract §5.3 |

## 3. Points for the re-review and for Stephen

1. **The reference tool's place.** P-065's Boundary line reads "Docs and data files only". The review's M-8 requires a
   reference script and vectors committed with the contract. `tools/w9_segmentation.py` is a stand-alone, non-runtime
   tool outside `research_system/`: it opens no store and writes nothing, and its tests are synthetic. It is committed
   as M-8's fix. Stephen's acceptance of revision 2 should say whether he reads it as within WP9.0, or wants it moved
   to a later package.
2. **06d's file name.** It keeps `s016` from 06v O-15. Renaming it to `s017` would change a path that the accepted plan
   names.
3. **Interim tool fixes found while writing vectors.** Three behaviours were brought into line with the contract:
   - Working Notes now treats `---` rules as structural, like every other selector.
   - An empty `log_frontmatter` file now yields one zero-length blocker row. Before the fix, it yielded no rows.
   - Invalid UTF-8 in a stage-table data row is now `unparseable_anchor`.

   The census was re-run after these fixes, and every figure is unchanged.

## 4. Revision 3, against the re-review of `185510bc`

The re-review (`reviews/wp9-0-re-review-185510bc-2026-10-23.md`, commit `0c59ea84`) returned PASS WITH FINDINGS: one
new Major (N-1, an owner decision), 9 Minor and 6 Info findings, and two vector gaps. Stephen ruled on N-1 (P-067).
Revision 3 folds in the rest. The reviewer offered a narrow confirmation in place of a full round.

| Finding | Disposition | Where |
|---|---|---|
| **N-1** reference tool under P-065 | Stephen's ruling (P-067): both files are within WP9.0, as a named extension of P-065's boundary. P-065 carries a pointer note | P-065, P-067; contract §7 |
| **N-2** frontmatter opener | Contract amended to match the tool: line 1's match text, trimmed of trailing spaces and tabs, is `---`. The existing vector now agrees with the text | Contract §3 |
| **N-3** "implements every rule" | Both parts addressed: (a) the tool now records suppressed anchors (line, anchor-line SHA-256, heading text) and reports each row's anchor-line SHA-256; (b) §3 and §7 state that checking a region declaration, and resolving "from the first anchor after", are the inventory's checks | Tool; contract §3, §7; vectors |
| **N-4** offsets | §6.5: offsets reproduce the read only; the detector locates rows by identity | Contract §6.5 |
| **N-5** the copy and the recheck | §6.2 retains the copy and commits its hash and size with the export. §6.3 says the recheck proves reproducibility, not the original read's identity | Contract §6.2, §6.3 |
| **N-6** non-item rows | §6.4: the export carries every row in the legacy region. Structural and blocker rows are identified by anchor-line SHA-256; a shared hash blocks the export | Contract §6.4 |
| **N-7** 06d gate stage; change class | `gate_stage: pilot_promotion`. S-017 is added to the "agent/model routing" row by name, as an explicit addition beyond its P0 rule | 06d §2, §3 |
| **N-8** identity kinds | W9 §5.4's four kinds: `git_tracked`, `untracked_file`, `restricted_untracked_file`, `vault_file` | Template §4 |
| **N-9** what the W9 record binds | Template §1: the record copies W9 §5.2's fields from the accepted bytes and adds `table_sha256` and `acceptance_decision_ref`. WP9.1 stage A's schema is aligned on its own branch | Template §1; WP9.1 |
| **N-10** 06v still adds `accepted_w9.py` in WP9.1 | P-067 item 3: 06v's bytes stay unchanged. The WP9.1 stage note and every WP9.1 or WP9.2 dispatch brief cite P-066 item 2 | P-067; WP9.1 stage note |
| Vector gaps (§4.2) | Added: a dated entry ended by a same-level non-date heading; CRLF input for `tracker_task_row`, `working_note_entry` and `conventions_unit`. Also added: missing-section refusal, the suppressed-anchor record, and the anchor-line hash on every row. 37 vectors pass | Vectors; contract §7 |
| I-1 date token is syntactic | Stated | Contract §3 |
| I-2 dated-flag grammar | Stated | Contract §3 |
| I-3 missing section | Stated: segmentation is refused | Contract §3 |
| I-4 empty-array pattern | Stated | Template §3 rule 2 |
| I-5 `NaN` count | Re-worded as an upper bound | Template §3 rule 1 |
| I-6 | Recorded | — |

**Census.** Re-run with the revision-3 tool. No segmentation changed. The live log gives 256 entries and one
structural block, with no blockers, matching the re-review's read (contract §8).

## 5. Not done

- No L-0b export, no observation, no store write and no legacy write. The vault, `.apm/` and the stage logs were read
  only.
- The D8c backlog is not re-observed here; m-3 stays open until that happens.
- WP9.1 stage A is aligned with S-017 separately, on `pipe/w9-wp9-1-schemas`.
