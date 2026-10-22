# G7-A owner acceptance: W0 post-terminal addendum, revision 3

**Date:** 2026-10-22
**Decision:** `accepted` (the addendum's own state, §3); the W0 series moves to `post_terminal_recorded`
**Owner:** Stephen Dorman
**Authority:** Stephen, in chat, 2026-10-22: "I accept G7-A revision 3 at a4e5310c (blob 1ebcf96f) and W0-D1 to W0-D4
as recommended: I sign the manifest §14 items after the independent check; Stage 2 scope at 06l Step 3; accept the §3
state sequences; accept the Discovery exclusion with its condition. Record it, then start G7-B."
**Runtime authority:** none. This acceptance migrates nothing, seals nothing, opens nothing and dispatches nothing.

## Exact accepted subject

| Identity | Value |
|---|---|
| File | `docs/plans/agentic-research-system/transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md` |
| Revision | 3 |
| Commit | `a4e5310c` on branch `claude/gate7-prep-docs-5202cf` (not yet on main) |
| Blob | `1ebcf96ff07127561402873a52dd6a7280aa9700` |
| Observation commit it records | origin/main `3fa437a1` |

The addendum's frontmatter field `status: under_review` is the reviewed snapshot's state. This record supplies its
effective post-review status, `accepted`, without rewriting the reviewed bytes. If the file's blob ever differs from
`1ebcf96f`, this acceptance does not cover the difference.

## Review evidence

| Round | Subject | Verdict | Record |
|---|---|---|---|
| Delta review | revision 1, `77388ec9` | REWORK REQUIRED (0 Blocking, 6 Major, 12 Minor, 5 Info) | `reviews/g7a-w0-post-terminal-addendum-delta-review-77388ec9-2026-10-22.md` (`73d73357`) |
| Re-review | revision 2, `8988f463` | REWORK REQUIRED (narrow; 0, 2, 3, 4) | `reviews/g7a-w0-post-terminal-addendum-re-review-8988f463-2026-10-22.md` (`c7ef464b`) |
| Re-check | revision 3, `a4e5310c` | **PASS** (0, 0, 0, 2 Info) | `reviews/g7a-w0-post-terminal-addendum-re-check-a4e5310c-2026-10-22.md` (`31e1a6dd`) |

Author reconciliation: `reviews/g7a-w0-post-terminal-addendum-reconciliation-2026-10-22.md` (§1 for revision 2,
§5 for revision 3). Every review came from one independent session (g7a-delta-review), distinct from the author
session and on the same model family (a P-058 known limit).

**Re-check Info I-a, recorded here instead of in the accepted bytes.** H10's resolution rests on a read of the P01-A
§4.5 draft `papers/P01-A-JRSSA/drafts/sections/results-escape-regression-foo.md` at origin/main `3fa437a1`, blob
`1268dfa70066f369e54fb06dc26a00e26714f5d9` (last changed in `08689307`). A later reader can re-verify H10 against
those exact bytes.

**Re-check Info I-b.** The vault correction of the 2026-07-11 T1.20 `[DECISION]` (Computational-Log, 2026-10-22) was
written by the author session and independently verified by the reviewer against the committed JSON and the draft.

## Owner decisions

| ID | Decision (Stephen, 2026-10-22) |
|---|---|
| W0-D1 | Stephen is the signatory for all eight manifest §14 items, including the enumerated A-001 list (addendum §10, twelve items), and signs them **after the independent check** that covers addendum §6.1, §7 and §10. This decision names the signatory; **no §14 item is signed by this record**. The amendment to A-001's confirmation condition ("the current Manager confirms") and to 06l Step 3 ("The Manager explicitly confirms or rejects A-001") is recorded through G7-C's register entry. |
| W0-D2 | The Stage 2 scope (the fifteen rows in addendum §9) is decided at 06l Step 3, not now. |
| W0-D3 | The two state sequences in addendum §3 are accepted as the W0 series' and the addendum's states. |
| W0-D4 | The Discovery boundary is excluded from G7-A, a deviation from 06l Step 2. G7-B inventories it against W11, **on condition** that the 06l Step 2 amendment G7-C carries states that no Discovery item takes a 06l Step 3 or later action until G7-B's Discovery inventory is accepted. |

## State after this acceptance

- **The addendum:** `accepted`, at blob `1ebcf96f`.
- **The W0 series:** `post_terminal_recorded`. It is not `sealed`. Sealing needs Stephen's signature on all eight §14
  items after the independent check (W0-D1), and the Stage 2 scope decision (W0-D2).
- **Superseded as current state, not edited:** the 2026-06-29 addendum's §3 T1.28 observation; the 03 A-001 status
  line "T1.28 is now active".
- **Carried to later documents:** to G7-B, the `SUPERSEDED.md` line-69 import conflict, the post-freeze writer list
  (addendum §11, including the two no-PR direct pushes) and the Discovery inventory under W0-D4; to G7-C, the
  stale-projection list (addendum §15), the A-001 and 06l Step 3 amendments, the replacement WP6.7 wording and W0-D4's
  condition.
- **Integration:** the accepted bytes reach main only through a PR Stephen opens and merges after CodeRabbit review.

## Jira

KAN-15 (the addendum and delta review), KAN-24 (T1.28 DONE and the open post-terminal state) and KAN-20 (the W0
state sequence) meet their acceptance criteria with this record. KAN-23 stays open: its criteria require the
positive gate conditions that replace the WP6.7 hold, which G7-C writes.
