# W9 segmentation contract, version 1.0.0

**Contract ID:** `w9-segmentation/1.0.0`<br>
**Date:** 2026-10-23<br>
**Status:** Draft, revision 2, `review_pending`. It reconciles the review `reviews/wp9-0-review-a427084e-2026-10-23.md`
(see `reviews/wp9-0-reconciliation-2026-10-23.md`). It needs re-review and Stephen's acceptance (P-065). Under D-7 it
may be accepted together with the Computational-Log baseline export, ahead of the rest of WP9.0.<br>
**Authority:** W9 §5.5 (item selectors) and §7.3 (baselines); 06v WP9.0 and re-review m-7; P-064 D-7; P-065<br>
**Reference implementation:** `tools/w9_segmentation.py`, with vectors in `tests/tools/test_w9_segmentation.py`
(§7)<br>
**Implementation authority:** None. This contract defines a rule. It observes, hashes or registers nothing.

## 1. Purpose and relation to D8c

An item hash can be compared across observers, and across dates, only if every observer cuts the item at the same
bytes. This contract fixes that cut for every Markdown selector in W9 §5.5.

**Relation to D8c.** This contract adopts D8c's **span rule**: raw line bytes with their terminators, from the anchor
to the last non-blank line, with blank separator lines being structural. It **changes** D8c's anchor text and region
rule, as §3 and §4 state. Under this contract the D8c backlog's nine item spans and hashes reproduce exactly when the
covered region is declared as lines 23 to the end (§8). D8c's anchor texts, which were truncated at ` — `, are
**superseded** by §3's full heading text. D8c's carried finding m-3 closes only when the backlog is re-observed under
this contract.

This contract does not apply to JSON results, which W9 selects by JSON-pointer family (W9 §6.2), or to whole-file
hashes, which are always over the exact file bytes.

## 2. Lines

1. **Input.** The input is the exact bytes of the file as read: no decoding, no normalization, no BOM stripping, no
   line-ending conversion. For L-0b, §6 says which reader may supply them.
2. **Lines and terminators.** A line is a maximal byte run ending with LF (`0x0A`). Its **terminator** is `CRLF` when
   the LF is preceded by CR (`0x0D`), otherwise `LF`. A file not ending with LF has a last line with an empty
   terminator. Lines are numbered from 1.
3. **Line text.** A line's text is its bytes minus its terminator. **Match text** is the line text, except that on
   line 1 a leading UTF-8 BOM (`EF BB BF`) is removed. The BOM stays part of line 1's bytes for hashing. It is ignored
   only for anchor matching and blankness.
4. **Blank lines.** A line is blank when its match text consists only of spaces (`0x20`) and tabs (`0x09`), or is
   empty.
5. **Rule lines.** A line is a rule line when its match text, with trailing spaces and tabs removed, is exactly `---`.
6. **No Markdown parsing.** Segmentation is purely line-based.
   - Fenced code blocks, setext headings, HTML and indented code are **not** recognized.
   - A `#` line inside a fence is a heading if it has the ATX form below.
   - A line underlined by `===` or `---` is not a heading. A lone `---` is a rule line (rule 5).
7. **ATX headings.** A line is a heading of level k (1 to 6) when its match text starts at column 0 with exactly k `#`
   characters followed by one space. Leading spaces, a tab after the hashes, or no space at all mean no heading.
   **Heading text** is the match text after the `#`s and the one space, with trailing spaces and tabs removed. Closing
   `#` sequences stay part of the heading text.
8. **Observation record.** Every observation records:
   - the line-ending kind (`LF`, `CRLF`, `mixed` or `none`);
   - whether the file ends with a terminator;
   - whether it starts with a UTF-8 BOM;
   - the line count.
   
   Nothing is corrected.

## 3. Items, regions and anchors

**Span rule.** An item span is a run of whole lines from its anchor line to its **last line that is neither blank nor
a rule line**, before the item's end boundary. Lines after that, up to the boundary, are structural. The item hash
(`raw_row_sha256`) is SHA-256 over the exact bytes of the span's lines, terminators included.

**Covered region.** Every inventory declares its covered region in one of two ways:
- as a line range plus the SHA-256 of each anchor line's bytes;
- as "from the first anchor after" a named structural line, given by line number and hash.

A selector with a fixed region (below) needs no declaration. Within the region, an inventory may declare **classified
structural ranges**. A heading inside a declared structural range is a **suppressed anchor**: it opens no item, and the
inventory records it.

**Anchor text.** Anchor text is the selector's anchor bytes decoded as UTF-8, **never repaired**. Double-encoded or
mojibake text is kept exactly as its bytes decode. Bytes that are not valid UTF-8 make the row a blocker
(`unparseable_anchor`).

| Selector kind (W9 §5.5) | Region | Anchor line | End boundary | Anchor text |
|---|---|---|---|---|
| `heading_section` | Declared (above). The heading level k is declared by the inventory | A heading of level k, not suppressed | The next heading of level ≤ k that is not suppressed, or the region's end | The full heading text (§2.7) |
| `computational_log_entry` | The whole page, unless declared | A heading of level 2 or 3 whose heading text starts with a **date token** (below) | The next heading whose level is ≤ the anchor's level, or the next date anchor, or the region's end. A deeper heading inside an entry belongs to the entry | The full heading text |
| `tracker_task_row` | Fixed: from the line after `## Task Tracking` to the line before the next heading of level 1 or 2 | A table row (a line starting with `\|`) in a **stage table** whose first cell matches the **task grammar** (below) | The row itself (one line) | The first cell. The task ID is `T` plus the cell |
| `working_note_entry` | Fixed: from the line after `## Working Notes` to the line before the next heading of level 1 or 2, or the end of the file | A **top-level bullet**: a line whose match text starts with `- ` at column 0 | The next top-level bullet, or the region's end | The full first line's text, with trailing spaces and tabs removed. An entry whose anchor text starts `- **` followed by a date is recorded as dated |
| `log_frontmatter` | Fixed: the whole file | Line 1, when its match text is exactly `---` | The next line whose match text, trimmed of trailing spaces and tabs, is `---`. Both delimiters are included | The constant `frontmatter` |
| `conventions_unit` | Fixed: each `## ` section of `CONVENTIONS.md` read from **blob `4620c71607ca3a06c6df3b8e96a6bddffc783960`** (33,645 bytes; SHA-256 `d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589`), which is the file at commit `4b143c92` | A **unit** (below) | As defined for each unit kind | The section's heading text, plus the unit's ordinal within the section (recorded, never identity), plus the unit hash |

**Date token** (`computational_log_entry`). Matched at the start of the heading text:

    ~?[0-9]{4}-[0-9]{2}(-[0-9]{2}([a-z]|/[0-9]{2})?)?

It must be followed by the end of the text, a space, a tab or `(`. Month precision (`2026-03`), a day suffix
(`2026-06-03b`), a `/DD` range and a leading `~` are all anchors. The separator after the date (` -- `, ` — `,
mojibake or anything else) plays no part in anchoring.

**Non-anchor headings** (`computational_log_entry`). A heading of level 1, 2 or 3 that is not a date anchor opens a
block running to the next heading of level ≤ its level, or the next date anchor:
- if the heading is level 2 or 3 and its text starts with a digit, or with `~` and a digit, but fails the date-token
  grammar, the block is a **blocker** (`unparseable_anchor`). This is the closed definition of "looks like an anchor";
- otherwise the block is **structural**, for example the page title `# Computational Log`.

The lines before the first heading are a structural preamble. A heading of level 4 to 6 opens no block. Outside
every block, its lines, and any other non-blank, non-rule lines, fall into an unaddressed region (§4.4).

**Task grammar** (`tracker_task_row`):
- A **table** is a maximal run of consecutive lines starting with `|`. Cells are split on `|` not preceded by a
  backslash, and each cell is trimmed of spaces.
- A table is a **stage table** when its first row's first cell is exactly `Task`. In a stage table, the first row
  (the header) and separator rows (cells made only of `-` and optional `:`) are structural.
- A data row whose first cell matches `[0-9]+\.[0-9]+[a-z]*(-[a-z]+)?` is an item. Any other data row of a stage table
  is a blocker (`unaddressed_region`).
- Tables that are not stage tables (for example "Open threads"), and every non-table line, are outside the selector:
  structural.

**Units** (`conventions_unit`). Within a section, after its heading line, these lines are **structural** and belong to
no unit:
- blank lines;
- rule lines;
- the footer, matching `*Last updated: …*` exactly with its asterisks;
- headings.

The H1 and the preamble before the first `## ` are structural. The units are:
- **Bullet.** A line whose text starts with `- ` or `* ` at column 0 (the base indent). It continues over following
  lines that start with a space or tab, and over blank lines followed by such a line. It ends before the next line at
  column 0 that is not blank. Its span then follows the span rule.
- **Table.** A maximal run of lines starting with `|` is one unit.
- **Paragraph.** A maximal run of consecutive non-blank lines that are not bullets, table lines, rule lines, the
  footer or headings.

## 4. Identity, duplicates and blockers

1. **Identity.** An item's identity is its selector kind plus its anchor text, plus the unit hash where §3 says so.
   **Position is never identity.** Line numbers and byte offsets are recorded for reproduction only.
2. **Byte offsets.** Each row records its start byte offset and byte length, relative to the bytes read (§6.3 for the
   export).
3. **Duplicate anchors.** When two items of one selector kind in one region share an anchor text, or for
   `conventions_unit` share a section and unit hash, all of them are **blocker rows** (`duplicate_anchor`, W9 §5.5).
   They are never resolved by position. For `working_note_entry` the anchor text is the full first line, so two entries
   on one date are duplicates only if their whole first lines are identical. This is how W9 §5.5's "two Working Notes
   under one date heading" reads for `.apm/tracker.md`, which has no date headings.
4. **Unaddressed regions.** Inside a `heading_section`, `computational_log_entry` or `working_note_entry` region, any
   run of non-blank, non-rule lines outside every item, every structural block and every declared structural range
   is one blocker row (`unaddressed_region`). In a stage table, a data row whose first cell fails the task grammar is
   one such row.
5. **Unparseable anchors** are the cases §3 names:
   - invalid UTF-8 in anchor bytes, including a stage-table data row;
   - a level-2 or level-3 log heading that looks dated but fails the grammar;
   - a `log_frontmatter` file whose line 1 is not `---`, or whose frontmatter is unterminated;
   - an empty `log_frontmatter` file, recorded as one zero-length blocker row at byte 0.

## 5. Time, path form and versions

1. **Time.** Every read records its start and end time in UTC, ISO 8601 with `Z` and microseconds
   (`2026-10-23T09:14:05.123456Z`).
2. **Path form.** Every read records the path exactly as given, and whether it resolved through a junction or symbolic
   link to a different target.
3. **Version.** Every observation, inventory and export names `w9-segmentation/1.0.0`. A change to any rule is a new
   version, reviewed and accepted. Hashes taken under different versions are never compared. A version change
   therefore requires every baseline to be re-derived under the new version before the detectors can compare against
   it.
4. **Final terminator.** If a file without a final terminator later gains one, its last item's hash changes. Under the
   insertion-only rule (W9 §7.3) that change is flagged. It is a real byte change, not a false positive.

## 6. The L-0b export (D-7)

1. **Reader.** The export may be taken before WP9.3's handle-bound reader exists. It is read by the reference
   implementation (§7) from bytes copied once from the live page. The export records:
   - the copy's SHA-256 and size;
   - the read times (§5.1);
   - the path form (§5.2);
   - its limits, as D8c §7 recorded them: a path-string read, not a W11 §7.3 handle-bound read.
2. **Recheck.** WP9.3's reader later re-hashes the same bytes and must reproduce every entry. A mismatch voids the
   export.
3. **Offsets.** Every entry carries its live-page byte offset and length (§4.2), so the vault detector (W9 §7.3 item 5)
   can locate each entry in the live page.

## 7. Reference implementation and vectors

- **The implementation.** `tools/w9_segmentation.py` implements every rule above. It is not runtime code: it reads the
  bytes it is given and returns rows in the shape of `legacy-light-inventory` rows. Where it and this contract
  disagree, the contract governs.
- **The vectors.** `tests/tools/test_w9_segmentation.py` holds synthetic vectors, never legacy bytes. Each vector
  states its expected spans by line range and recomputes the expected hash from those lines. Together they cover:
  - LF, CRLF and mixed endings;
  - a missing final terminator;
  - CRLF blank lines;
  - a BOM before a heading and before frontmatter;
  - trailing blank lines and trailing rule lines;
  - a `#` line inside a fence;
  - a setext underline;
  - closing `#`s;
  - nested headings and sub-headings inside a log entry;
  - month-precision and suffixed dates;
  - a dated-looking heading that fails the grammar;
  - a table and an escaped `\|` in a first cell;
  - a bullet with continuation, and with a blank-separated continuation;
  - the footer and rule lines in a conventions section;
  - unterminated frontmatter, an empty file, and a file of only blank lines;
  - a duplicate anchor;
  - an unaddressed region;
  - suppressed anchors in a declared structural range.
- **Independence.** An independent re-implementation, by a session distinct from this contract's author and from
  WP9.3's implementer, must reproduce every vector before any export or observation under this contract is accepted.
  The L-0b export (§6) is no exception.

## 8. Census of the governed files (the grammar's evidence)

The reference implementation, as committed with this revision, was run read-only over each governed file on
2026-10-23, from 09:07:42.990960Z to 09:07:43.027460Z. Path forms:
- the vault files were read through their real path under `C:\Users\steph\Documents\TDA-Research\`, not through the
  `vault/` junction;
- the tracker and `CONVENTIONS.md` were read from copies of their blobs written by `git show`;
- the stage logs were read in place under `C:\Users\steph\TDL\.apm\memory\`.

| File | Bytes read | Result |
|---|---|---|
| Vault Computational-Log, live page | 700,632 bytes, SHA-256 `de44a67b8b72b62bbd17fafee9a20f91308c66e6105e860155bce25120ef1026` (the bytes the review read at 08:22:53Z), LF, no BOM | 255 dated entries and one structural block (the `# Computational Log` title at L4436); **no blockers**. This includes every heading form the review listed: double-encoded em dashes, `(canonically backfilled …)`, `(later)`, ` - `, `2026-06-03b/c`, `~2026-…`, ` ? `, the month-only `## 2026-03 …` at L5611, and the six dated level-2 entries, whose level-3 sub-headings stay inside them |
| `.apm/tracker.md` at origin/main | Blob `e791d95d`, 250,777 bytes, SHA-256 `0bb080f7…1597` | `tracker_task_row`: 95 task rows, no blockers; the "Open threads", Worker Tracking and Version Control tables are outside the selector. `working_note_entry`: 114 entries (88 dated, 26 undated), no duplicate first lines |
| `CONVENTIONS.md` | Blob `4620c716…` (commit `4b143c92`) | 70 units in 10 sections, no duplicates; the `---` rules and the `*Last updated: 2026-07-16*` footer are structural |
| `.apm/memory/stage-*/*.log.md` | 85 files: 67 LF; 8 mixed endings with BOM; 7 LF without a final terminator; 2 CRLF; 1 LF with BOM | `log_frontmatter`: 77 items. Eight blockers, all files with no frontmatter (they open with a `# Task Log` heading). All nine BOM-led files parse |
| Discovery `_backlog.md` | 27,590 bytes, SHA-256 `96b5775c…` | `heading_section`, k = 2, region L23 to the end: the nine D8c items, with spans, byte lengths and SHA-256 identical to D8c §3 |

The census is evidence for the grammar, not a baseline. The L-0b export is the baseline, taken under §6.
