# W9 segmentation contract, version 1.0.0

**Contract ID:** `w9-segmentation/1.0.0`<br>
**Date:** 2026-10-23<br>
**Status:** Draft, revision 1, `review_pending`. It needs an independent review and Stephen's acceptance (P-065). Under
D-7 it may be reviewed and accepted together with the Computational-Log baseline export, ahead of the rest of WP9.0.<br>
**Authority:** W9 §5.5 (item selectors) and §7.3 (baselines); 06v WP9.0 and re-review m-7; P-064 D-7; P-065<br>
**Implemented by:** 06v WP9.3, which reproduces every hash this contract defines<br>
**Implementation authority:** None. This contract defines a rule. It observes, hashes or registers nothing.

## 1. Purpose

An item hash can be compared across observers, and across dates, only if every observer cuts the item at the same
bytes. This contract fixes that cut for every Markdown selector in W9 §5.5. The D8c backlog observation chose its own
convention (`transition/discovery-backlog-observation-2026-10-22.md` §2) and recorded that a different one would give
different hashes (its §7). This contract adopts that convention and makes it binding, versioned and complete.

It does not apply to JSON results, which W9 selects by JSON-pointer family (W9 §6.2), or to whole-file hashes, which are
always over the exact file bytes.

## 2. Lines

1. **Input.** The input is the exact bytes of the file as read through the handle-bound protocol (W11 §7.3). There is
   no decoding, normalization, BOM stripping or line-ending conversion before segmentation.
2. **Lines.** A line is a maximal byte run ending with LF (`0x0A`), the LF included. A CR (`0x0D`) immediately before
   the LF belongs to the line. If the file does not end with LF, its last line is the bytes after the final LF.
3. **Line numbers.** Lines are numbered from 1.
4. **Blank lines.** A line is blank when its bytes, minus its terminator, are empty or consist only of spaces (`0x20`)
   and tabs (`0x09`).
5. **Observation record.** Every observation records:
   - the file's line-ending kind (`LF`, `CRLF` or `mixed`);
   - whether it ends with a terminator;
   - whether it starts with a UTF-8 BOM;
   - the total line count.
   
   A `mixed` file is still segmented by rule 2. The kind is recorded, never corrected.

## 3. Items

**An item span** is a contiguous run of whole lines, from its anchor line to its **last non-blank line** before the
next anchor of the same selector kind, or before the end of the region its selector covers. Blank lines between items
are **structural**: they belong to no item. The item hash is SHA-256 over the exact bytes of the span's lines,
**including** every line's terminator, the last line's included.

| Selector kind (W9 §5.5) | Anchor line | Region | Anchor text |
|---|---|---|---|
| `heading_section` | A line starting with `#`×k plus one space, for the level k the inventory names | Between that heading and the next heading of level ≤ k | The heading text after `#`×k plus the space, without its terminator, with trailing spaces and tabs removed |
| `computational_log_entry` | A level-3 heading `### YYYY-MM-DD -- ` | The whole page, inside the baseline export (W9 §7.3) | The full heading text, as above |
| `tracker_task_row` | A Markdown table row whose first cell, trimmed of spaces, equals a task ID | One line only (the row) | The task ID |
| `working_note_entry` | A date heading (`### YYYY-MM-DD` or the file's own date-heading form, named in the inventory) inside the Working Notes section | Until the next date heading or the end of the section | The heading text |
| `log_frontmatter` | The first line, when it is exactly `---` plus its terminator | Through the next line that is exactly `---` plus its terminator, both delimiters included | The constant `frontmatter` |
| `conventions_unit` | A bullet line (`- ` or `* ` at the section's base indent), or the first line of a paragraph, inside a `## ` section of `CONVENTIONS.md` read from blob `4b143c92` | A bullet runs to its last non-blank line before the next base-indent bullet, the next paragraph or the next heading, and continuation lines belong to it. A paragraph runs to its last non-blank line. | The section heading text, plus the unit's ordinal **within the section**, plus its own hash. The ordinal is recorded but is never the identity (§4) |

## 4. Identity, duplicates and blockers

1. **Identity.** An item's identity is its selector kind plus its anchor text, plus the unit hash where §3 says so.
   **Position is never identity.** Line numbers and byte offsets are recorded for reproduction only.
2. **Byte offsets.** Each item records its start byte offset and byte length within the file. This hardens the D8c
   convention as its carried finding m-3 asked.
3. **Duplicate anchors.** When two items of one selector kind in one region share an anchor text, both are
   **blocker rows** (W9 §5.5). They are never resolved by position.
4. **Unaddressed regions.** Any non-blank line in a light inventory's covered region that belongs to no item is a
   blocker row, unless the inventory lists it as a classified structural region (as D8c's B1 and B2 were).
5. **Unparseable anchors.** A line that looks like an anchor of the selector kind but does not parse (for example a
   malformed date heading) is a blocker row.

## 5. Time and versions

1. **Time.** Every observation and inventory records the UTC time of the read as ISO 8601 with `Z`
   (`2026-10-23T09:14:05Z`). This closes the gap that observation
   `2026-10-22-dated-observations-lack-time-and-hash-convention` records.
2. **Version.** Every observation, inventory and export names `w9-segmentation/1.0.0`. A change to any rule here is a
   new version, reviewed and accepted. Hashes taken under different versions are never compared.

## 6. Reference vectors

WP9.3 adds committed reference vectors for every selector kind: synthetic inputs, never legacy bytes, with their
expected spans and hashes. They cover:
- LF and CRLF;
- a missing final terminator;
- trailing blank lines;
- a duplicate anchor;
- an unaddressed region;
- a malformed anchor.

An independent re-implementation must reproduce every vector before any observation under this contract is accepted.
