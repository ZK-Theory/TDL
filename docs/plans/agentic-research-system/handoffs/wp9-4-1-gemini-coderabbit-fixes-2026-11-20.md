# Follow-up 2: WP9.4-1, the CodeRabbit fixes on PR #439

Your branch is now PR #439 (`https://github.com/ZK-Theory/TDL/pull/439`), pushed at `74ff49d6`. CodeRabbit has reviewed it. A Claude session checked each of its 13 comments against the code. The decision on each is below. Make the changes marked **Fix** on the same branch and in the same worktree, under the same rules as before:
- commits written with `git commit -F <file>`, the file UTF-8 without a BOM;
- never `--no-verify`;
- the boundary in the first handover's §4.

Two rules are new or stricter now that a PR is open:
- **Do not push.** The reviewing session pushes after checking your commit.
- **Do not reply on GitHub** or resolve any thread. The reviewing session does that.

## Where you are

- Worktree: `C:\Users\steph\TDL\.apm\worktrees\wp9-4-1`
- Branch: `pipe/w9-wp9-4-1-adoption-discharge`, head `74ff49d6`, which is also `origin`'s head

Before any write, confirm the branch, that HEAD is `74ff49d6`, and that `git status --short` is clean.

## The fixes

Each fix names CodeRabbit's comment. Every new or changed guard gets a test that asserts the guard's own message, and a negative control that passes. Every refusal through `submit` leaves `_snapshot(store)` unchanged.

### A. Code

1. **LR-026: refuse an analyst session that equals the eligible session** (comment on `research_system/legacy/replay/reducers.py:1129`).
   - If the request's analyst session equals its eligible session, no verdict can satisfy it, because note §5.5 needs the verdict's session to differ from the first and equal the second. Yet the request still uses up the one derived review reservation.
   - Refuse it in `_check_review_request`, before `_take_reservation`, with a message such as `"W9 adoption review request names the analyst session as the eligible session"`.
   - Tests:
     - a forged-ledger refusal;
     - a scratch-store refusal through `submit`, with the snapshot unchanged;
     - the existing positive flow, with distinct sessions, as the control.

2. **Refuse the owner as a named reviewer, at every W9 review-request row** (CodeRabbit's comment outside the diff, on `reducers.py:1137-1138`).
   - Today a review request can name the bound owner as reviewer. `LegacyRuntime._require_role` (`research_system/legacy/runtime.py`) then refuses the owner's verdict, so the reservation is used up and the proposal is stuck until it lapses.
   - Replay has no owner identity, so the fix belongs in the runtime. It has `authority_evidence.administration_context.owner_actor_id`. For `RequestW9AuthorityReview`, refuse before the shadow replay and before any write when the payload's `reviewer_actor_id` is the owner. Use a message such as `"W9 review request names the owner as reviewer"`.
   - This covers WP9.3's request rows (LR-007, LR-012, LR-017) as well as LR-026 and LR-031. That changes accepted WP9.3 behaviour, though only to refuse a request no verdict could ever complete. **Record it as a second departure** in record §3, saying exactly that.
   - Tests:
     - a scratch-store refusal at LR-031;
     - a scratch-store refusal at one WP9.3 request row, LR-007 or LR-017, whichever the existing harness reaches more cheaply;
     - each with the snapshot unchanged, and the existing positive flows as controls.

3. **The import-seam test: handle `from research_system import legacy`** (comment on `tests/research_system/contracts/test_w9_import_seam.py:81`).
   - Normalise `from research_system import <name>` to `research_system.<name>` before the allowlist applies.
   - Keep the wildcard handling and the existing submodule detection.
   - Add a negative control: an unlisted importer using that form is reported. Keep the `projection_read` positive.

### B. Tests that do not yet test their guard

4. **LR-029's own "review satisfied" check** (comment on `tests/research_system/integration/test_w9_wp9_4_1_replay.py:259-263`).
   - Both LR-029 cases fail on earlier checks, so removing `review_satisfied` at LR-029 is caught by nothing.
   - Start from a valid replayed prefix through LR-028. Then make the review unsatisfied at resolution while keeping the record, its evidence refs and `considered_review_ids` unchanged. One way is to forge the state the resolution reducer sees, so the review is missing or its verdict is not `approve`. Assert `"W9 resolution's review is not satisfied on the record's hash"`.
   - Then mutate only that check, run the test, and report that it fails.

5. **The LR-033 item check, your recorded departure** (comment on `tests/research_system/integration/test_w9_wp9_4_1_runtime.py:1288`).
   - Every LR-033 case fails on the blob.
   - After LR-032, commit an open-item list that omits `A001-01`, and assert that it is absent. Submit LR-033 with that list's actual blob, and assert `"W9 discharge item is not in the open-item list at git_head"` with the snapshot unchanged.
   - Restore the original list before the existing positive LR-033 submission, and assert that its blob is the original.
   - Then mutate only the membership half of `_check_discharge_open_item`, as called at LR-033, and report that the new test fails.

6. **The forged flows drop LR-023 and LR-030 payload changes** (comments on `tests/research_system/integration/w9_flows.py:879` and `:985`).
   - `adoption_recorded` and `discharge_recorded` throw away `Tweak.payload` for their first row (`actor, when, _ = step(...)`). No current test passes one, but the next test that does would be vacuous.
   - Apply the payload to a copy of the record. Because the content hash covers the record, recompute what depends on it. Keep a way to pass an intentionally wrong hash for hash controls.
   - Add one test per flow showing the change takes effect. A good pair is a `w5_consequence` change at LR-023 refused with its own message, and a `legacy_item` change at LR-030 that hits the uniqueness refusal.

7. **W9-T1 through the observation path** (comment on `tests/research_system/unit/test_w9_projection_read.py:436`).
   - The test plants `"Done"` as a `w0_class`, which is not a valid class, so the observation path never sees it.
   - Note §15 asks that "A `Done` status word in the source yields no adoption". Put `Done` in synthetic source bytes, for example a JSON field value or a status line, and record a valid observation of that source through the existing scratch-store or forged-ledger path.
   - Assert two things: no `legacy_adoption_decision` record exists; and `family_admissible` for the observed family is `unadopted`.
   - Replace the planted-class fixture rather than adding a second test.

8. **The discharge fixture tuples** (nitpick on `tests/research_system/contracts/test_w9_pilot_promotion_table.py:121`). Assert that `DISCHARGE_UNCONDITIONAL_FIXTURES` and `DISCHARGE_CONDITIONAL_FIXTURES` are each empty, and that `DISCHARGE_FIXTURES` equals their union, as the adoption check does.

### C. The record (`docs/plans/agentic-research-system/transition/w9/wp9-4-1-record.md`)

9. **Line 121:** label each verification run with the commit it ran at. Separate the baseline runs at `0846bdaf` from the post-fix runs at `74ff49d6` and from your new runs.
10. **Line 165:** say what the late-match test compares: the ordered ledger events and the control-root tree, through `_snapshot`. Don't say "byte-identical ledger".
11. **§7, known limits: add the cross-registration case** (CodeRabbit's Major, on `research_system/legacy/projection_read.py:96`). **Do not change the code for this one.** Write it as follows.
    - The limit: `adoption_suspension_cause` reads only the adoption's own registration's observations (note §7). So a later observation of the same file under a second registration does not suspend the adoption. Examples of a second registration: a case-variant path, another path to the same physical file, or a file under a registered root.
    - Why it is a limit: note §7 assumes one file has one registration. WP9.4-2's collision checks enforce that under Stephen's 2026-11-20 scope decisions (note §15, the "Prefix collisions" and "One file registered twice" rows). Until then, no real adoption exists.
    - Under "Obligations carried beyond WP9.4-1", add a WP9.4-2 binding test: with a whole-file adoption recorded, a second registration of the same file is refused at LR-003, so the adoption cannot stay active past a re-observation.
12. **§7, out-of-scope item 2:** the shared `.git` is no longer shallow. It was unshallowed on 2026-11-20, and the 06h smoke test passes on `main` (42 passed). Say so, and keep the original observation.
13. **Add a "CodeRabbit fixes" section** after §8. List each item above with `path:line`, its test, and the message it asserts. Add the second departure to §3, and the new mutations to §6. Update §5's counts.

### Declined; do not change

- The nitpick on `preparers.py:700-714`, to build the shared `DecisionResolved` payload once. LR-025's branch is separate on purpose (note §5.5). Merging it touches tested preparer code for style only.

## Verification

- Run the changed and new files:
  - `test_w9_wp9_4_1_runtime.py`, `test_w9_wp9_4_1_replay.py`, `test_w9_import_seam.py`, `test_w9_projection_read.py` and `test_w9_pilot_promotion_table.py`;
  - for fix 2, also `test_w9_wp9_3_runtime.py` and `test_w9_wp9_3_2_runtime.py`, because the refusal reaches WP9.3's rows.

  Use `uv run --env-file .env python -m pytest <files> -q -p no:cacheprovider --no-cov`.
- Run the mutations for fixes 1, 2, 4 and 5, one guard at a time, restoring each file byte for byte.
- `ruff check` and `ruff format --check` on every changed Python file.
- Commit once, with the subject `[PIPELINE] P06: WP9.4-1: CodeRabbit fixes on #439 (LR-026 sessions, owner as reviewer, import seam, test controls, record)` and your `Co-Authored-By` trailer.

## Hand back

1. `COMPLETE` or `PARTIAL - <gap>`.
2. The new head and `git log --oneline 74ff49d6..HEAD`.
3. For each of items 1 to 13: what changed (`path:line`), its test, and the message it asserts.
4. Pass, fail and skip counts and wall time for each file you ran.
5. Each mutation and its result.
6. Anything you were unsure of, especially how far fix 2 reaches into WP9.3's rows.

Do not describe the work as reviewed or ready to merge.
