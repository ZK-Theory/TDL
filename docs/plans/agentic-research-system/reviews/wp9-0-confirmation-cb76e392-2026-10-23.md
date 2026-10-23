# Confirmation of W9 WP9.0, revision 3 (`cb76e392`)

**Date:** 2026-10-23<br>
**Reviewer:** the session that wrote the review (`079f0095`) and the re-review (`0c59ea84`). It authored none of the
subject files.<br>
**Scope:** the narrow confirmation the re-review offered (§7 step 2). This is not a full round.<br>
**Verdict:** **CONFIRMED.** N-1 to N-10, I-1 to I-5 and both vector gaps are closed. No Blocking, Major or Minor
residual remains. There is one Info note.<br>
**Known limit (P-058):** one model family throughout this review chain.

## 1. Subject and method

**Subject.** Commit `cb76e392bf133d1772199a80ac97e28442425a72` on `pipe/w9-wp9-0-documents`, one commit after the
re-review commit `0c59ea84`. `git diff --stat 0c59ea84 cb76e392` shows seven files:
- 06d;
- the segmentation contract;
- the membership template;
- the register (P-065 boundary note and P-067);
- the reconciliation, §4;
- `tools/w9_segmentation.py`;
- `tests/tools/test_w9_segmentation.py`.

**Checks:**
- Read the full diff of every file against each finding in the re-review.
- Ran `uv run --with pytest python -m pytest tests/tools/test_w9_segmentation.py -q -p no:cacheprovider -o addopts=""`:
  **37 passed**.
- Re-ran the census read-only with the revision-3 tool, using the re-review's scratchpad scripts:
  - the live Computational-Log, read at 2026-10-23T12:07:59.461057Z: 703,531 bytes, SHA-256 `19ad5c4d…66bb6`. It gave
    256 items, 167 of them dated on or before 2026-07-18; 1 structural block (`# Computational Log`, L4476); and 0
    blockers;
  - tracker blob `e791d95d`: 95 task rows and 114 Working Notes entries (88 dated);
  - `CONVENTIONS.md` blob `4620c716`: 70 units in 10 sections, with no row on the footer;
  - the 85 stage logs: 77 items and 8 blockers;
  - the Discovery backlog with region L23 to the end: the nine D8c rows, unchanged.

  Every figure matches contract §8 and the revision-3 re-run note.
- `git status` stayed clean.

## 2. Findings

| Finding | Status | Evidence |
|---|---|---|
| N-1 | **Closed** (P-067) | P-067 quotes Stephen's ruling. It names both files, extends P-065's boundary to those two only, and keeps them non-runtime. P-065 carries a pointer note, and contract §7 cites P-067 |
| N-2 | **Closed** | The contract's `log_frontmatter` opener is now "trimmed of trailing spaces and tabs". The tool, the `---  \r\n` vector and the text agree |
| N-3 | **Closed** | The tool now emits `suppressed_anchors` (line, anchor-line SHA-256, heading text) and an `anchor_line_sha256` on every row. Contract §3 and §7 assign declaration checking, and resolution of "from the first anchor after", to the inventory. "Implements every *segmentation* rule" is now accurate |
| N-4 | **Closed** | §6.5: offsets reproduce the read only, and the detector locates rows by identity |
| N-5 | **Closed** | §6.2 retains the copy and commits its hash and size with the export. §6.3 states that the recheck proves reproducibility, not the identity of the original read |
| N-6 | **Closed** | §6.4: the export carries items, structural blocks and blockers. Non-item rows are identified by anchor-line SHA-256, and a shared hash blocks the export |
| N-7 | **Closed** | 06d gives S-017 `gate_stage: pilot_promotion`, and adds it to the "agent/model routing" row by name, as an explicit addition beyond that row's P0 rule |
| N-8 | **Closed** | Template `identity_kind` is W9 §5.4's four kinds |
| N-9 | **Closed** | Template §1: the record copies W9 §5.2's fields and adds `table_sha256` and `acceptance_decision_ref`. Aligning the WP9.1 schema is that branch's work |
| N-10 | **Closed** | P-067 item 3 records the pointer, and 06v's bytes stay unchanged |
| Vector gaps | **Closed** | `test_log_entry_ended_by_same_level_non_date_heading`. CRLF parametrisations for `tracker_task_row`, `working_note_entry` and `conventions_unit`. Also new: the missing-section refusal, the suppressed-anchor record and the anchor-line hash |
| I-1 to I-5 | **Closed** | Stated in the contract §3 and template §3 rules 1 and 2 |

## 3. Info

- **C-1.** §6.4 makes the export carry every row "in the legacy region", and identifies structural and blocker rows by
  their anchor-line hash. Today the only such row is the title block at L4476, which sits among legacy entries. W9 §7.3
  item 1 already makes Stephen accept a classified list of every entry. That list should also classify each
  structural or blocker row, as legacy region or not, so the detector's comparison set is fixed by the accepted list
  and not inferred. No change to the contract is needed; this is a note for the L-0b brief.

## 4. Next

Stephen's exact-revision acceptance of 06d and the segmentation contract at `cb76e392` (P-065 item 3). Then
CodeRabbit, and Stephen merges.

Not done here: no subject file was edited. No vault, `.apm/`, stage-log, store, Jira or `papers/` write was made.
