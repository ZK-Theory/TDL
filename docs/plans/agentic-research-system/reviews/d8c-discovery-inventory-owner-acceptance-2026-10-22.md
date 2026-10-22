# G7-B Discovery inventory: owner acceptance

**Date:** 2026-10-22
**Decision:** `accepted` as the G7-B Discovery inventory (W9 §15; W9-D8c; W0-D4)
**Owner:** Stephen Dorman
**Authority:** Stephen, in chat, 2026-10-22: "I accept the D8c observation revision 2 at cd9f3600 (blob 026a9d10) as the
G7-B Discovery inventory, for backlog bytes 96b5775c, with B1/B2 as classified structural regions and WT-2/WT-3 as
sub-items of rows 4 and 3, revived only as new successor Candidates. Record it."
**Runtime authority:** none. The inventory imports, adopts, transitions and freezes nothing. The backlog stays
`legacy_owned` and legacy-written.

## Exact accepted subject

| Identity | Value |
|---|---|
| Inventory file | `docs/plans/agentic-research-system/transition/discovery-backlog-observation-2026-10-22.md` |
| Revision | 2 |
| Commit | `cd9f3600` on branch `claude/gate7-prep-docs-5202cf` (not yet on main) |
| Blob | `026a9d107430469fdf7bc731dbf64f4fcfe91f4a` |
| Backlog observed | `C:\Users\steph\Documents\TDA-Research\00-Meta\Discovery\_backlog.md` |
| Backlog bytes | 27,590 bytes; SHA-256 `96b5775ca3ba777d7cf13ebdd1f60bc187c08316bf5c2683c5496d7ff2b818a1` |

The acceptance covers those backlog bytes only. If the backlog's hash changes, this inventory describes a past state
of the file, and any 06l Step 3 or later action on a Discovery item needs a fresh observation first.

## Evidence

| Step | Record |
|---|---|
| Observation, revision 1 (non-author observer session d8c-backlog-observation; read 2026-10-22T12:14:17Z) | `46c2adf0` |
| Independent review, every hash recomputed from a live read at 12:20:15Z | PASS WITH FINDINGS (0, 0, 3, 3); `reviews/d8c-backlog-observation-review-46c2adf0-2026-10-22.md` (`3c50fff3`) |
| Revision 2, by the observer, applying m-1 and m-2 | `cd9f3600` |
| Reviewer confirmation, with a live read at 12:30:21Z (unchanged) | PASS; `reviews/d8c-backlog-observation-confirmation-cd9f3600-2026-10-22.md` (`ec737c73`) |

The observer was neither the W9 author nor the W9 reviewer. The reviewer was the G7-B reviewer session. Both ran on
the same model family as the author (a P-058 known limit). The reads were path-string reads, not W11 §7.3
handle-bound reads.

## What is accepted

1. **Nine items** in source order (inventory §3), each with its row anchor, line range, item hash and status text as
   written. Status words are untrusted legacy text, not Decisions.
2. **B1 (L8–L12) and B2 (L14–L20)** as classified structural regions, not items and not open blockers. B1 carries a
   qualifier: its "single source of truth for lifecycle state" claim is legacy self-description, bounded by P-004
   and P-032, with no authority over successor-owned Discovery objects.
3. **WT-2 and WT-3 as sub-items:** WT-2 of row 4 (`c1-persistent-laplacian-nonharmonic-spectrum`, L76–L77) and WT-3
   of row 3 (`mcbif-multiscale-clustering`, L47, L58). Both rows' status text is a `stale_projection_of` the freeze
   handoff §3 PARK records, which are the stronger record (W0 manifest §8.4). **Reviving either is a new successor
   Candidate (W11 OR-001) that cites the legacy row by lineage, never a legacy transition of the row.**
4. **No P04 or P01-A item** is in the backlog; P01-B is named only in row 9; SPEC-01 is named only inside row 1, and
   its Candidate is successor-owned.

## Consequences

- **W0-D4's condition is met** for the nine rows (with WT-2 and WT-3 through rows 4 and 3): a Discovery item may now
  reach 06l Step 3 or later on this inventory, subject to every other gate in W9 §4.5 and a fresh handle-bound
  observation at transition time.
- **W9 condition 2 (W9-D8c) is met.** W9's acceptance now waits only on G7-C's register entry (condition 3).
- **Carried:** m-3 (hardening the parsing convention into a positional-free selector with byte offsets) and the
  confirmation's wording note on two §7 limit lines, both at the next re-observation.
