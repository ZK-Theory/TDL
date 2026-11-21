# Follow-up: WP9.4-2 review fixes

Your WP9.4-2 branch has been reviewed. What the reviewer checked in the code matches the note and P-087:
- the D-4 boundary: two bindings, two authority entries, the count and digest pins, and nothing under `.research-system/`;
- the routes, with LR-035 and LR-054 refusing without a passed LR-022 and on the production routes;
- O's additions and the `root_id` drop in `_registration_conflicts` (`replay/reducers.py:540-576`);
- K's readings 2 to 4 (`_whole_file`, `_batch_rules`, the per-path stale rule);
- the second-registration test's three forms;
- the replacement-ref test.

The reviewer's own serial regression at `707cbe0d` is in "The reviewer's measurements" below.

**Stephen accepts the `member_path` change to `reader.py`** ("The member_path change is fine, go ahead", in chat, 2026-11-21). The note's §10.2 K reading 5 requires it. The handover allowed only the flag, which was the handover's error. You should still have stopped and reported it rather than choosing, and the record must list it (fix 3).

The fixes below are to the record and one comment. No production behaviour changes. Make them on the same branch, in the same worktree, under the same rules as the handover:
- commits written with `git commit -F <file>`, the file UTF-8 without a BOM;
- never `--no-verify`, no push, no PR, no merge;
- the boundary in the handover's §4, with `reader.py`'s `member_path` now allowed.

## Where you are

- Worktree: `C:\Users\steph\TDL\.apm\worktrees\wp9-4-2`
- Branch: `pipe/w9-wp9-4-2-full-path`, head `707cbe0d`

Before any write, confirm the branch, that HEAD is `707cbe0d`, and that `git status --short` is clean.

## The fixes

### 1. Correct the record's row groups (§1.1)

`wp9-4-2-record.md` §1.1's table groups the rows wrongly. It puts LR-040 to LR-043 under the inventory, LR-044 to LR-047 under the
mapping, and LR-048 to LR-054 under the ownership transition. The code (`routes.py:288-401`, LR-039 to LR-055) and the handover's §3 have:
- LR-040 to LR-044: the source inventory, five steps, with LR-044 recording it;
- LR-045 to LR-049: the transition mapping, five steps, with LR-049 recording it;
- LR-050 to LR-055: the ownership transition. LR-050 to LR-053 are the first four steps, and LR-054 and LR-055 are the two
  resolution rows (to `successor_owned`, and `successor_owned` to `closed_reference`).

Fix the table and every anchor in it, and check the anchors in §3 item 3 and §3 item 4 against the same rows.

### 2. Add the tables the handover's §6 asks for

The record has none of these yet. Add each one, citing `path:line` for the code and `file::test` for the test:
- **Rows:** one line per row, LR-035, LR-039 and LR-040 to LR-055. For each: what the annex row requires, what the note
  adds, where it is enforced (preparer, replay or both), and the test that proves it.
- **K's five readings** (note §10.2 items 1 to 5): each reading's site and its test, including the non-root control that
  shows every other role keeps today's check.
- **O's additions** (P-087 item 3): the root-scoped prefix check, a root being `git_tracked` in replay and at the
  preparer, the every-role equality, and the case-folded projection prefix. Each with its site and test.
- **P-087's five items** (handover §3): each with its site and test.
- **The mutations:** all 44, each with an ID, its `path:line`, what was changed, the test that caught it, and the message
  that test asserts. Say which mutations cover P-087 items 1 to 4. If any of those items has no mutation, add one, run
  it, and report the result.

### 3. List the departures (a new section)

The record has no departures section. Every departure from the note or the handover goes there with its reason:
- **`reader.py`'s `member_path`** (`reader.py:278-303`). It is outside the handover's allowed `reader.py` edit, it is
  required by note §10.2 K reading 5, and Stephen accepted it in chat on 2026-11-21. Record it as a change to WP9.3's
  accepted reader, alongside the flag;
- **`reader._git`'s refusal text** (`reader.py:80-92`). It now names the first non-flag argument (`git show failed`)
  rather than `args[0]`, which would now be the flag;
- any other departure you know of. One that is not listed is a defect.

### 4. Correct `evidence.py`'s comment

`research_system/legacy/evidence.py:73-77` still says the flag is passed in `evidence.py` "not in `reader._git`", because of
the importer identity. That is no longer true: `reader._git` now adds it itself (`reader.py:81`). Rewrite the comment to
say what the code does: `reader._git` passes `--no-replace-objects` (P-087 item 5), `_evidence_git` passes it too, and
`reader._git` does not add it twice. Keep `_evidence_git` as it is.

### 5. Replace §6.3 (the time budget) and §6.4 (the regression)

§6.3's result is not valid. The same 8 existing files took 497s at the base and 302s at the head. Subtracting that gap
from the 197s of the new files gives "+1.966s", but those 8 files are mostly unchanged, so the gap is measurement noise,
not time the branch saved. It also leaves out two changed files.

§6.4 is incomplete:
- 13 files ran before the last production edit;
- `test_command_cli.py` and `test_store_binding_cli.py` were never run, though the handover's §6 names them;
- "0 failed" hides the known `.apm/` path failure in `test_w9_wp9_3_inventory_builder.py`, which only passed when rerun
  from `%TEMP%`.

Do not re-measure. Replace both sections with "The reviewer's measurements" below, cited as the reviewer's serial run at
`707cbe0d`, and keep your profile paragraph.

## The reviewer's measurements

All runs were serial, on Stephen's machine, on 2026-11-21, each file a separate
`uv run --env-file .env python -m pytest <file> -q -p no:cacheprovider --no-cov`. Times are wall seconds per file. The base
is `f0e010e0`, run in the main checkout; the head is `707cbe0d`, run in your worktree.

**The time budget (P-087 item 7): met, 183s added against the 300s budget.**

The first pass ran every head file, then every base file. Two files differed by far more than their test changes could
explain: `test_w9_wp9_3_runtime.py` (head 135.1, base 79.8) and `test_schema_registry.py` (head 286.6, base 197.3). Those
two were rerun as back-to-back pairs, in both orders, and the table uses the pairs' means:
- `test_w9_wp9_3_runtime.py`: head then base 136.3 and 143.5; base then head 124.5 and 127.2;
- `test_schema_registry.py`: head then base 289.0 and 294.5; base then head 284.5 and 282.2.

The first pass's gaps were machine load, not the branch.

| File | Base (s) | Head (s) | Added (s) |
|---|---|---|---|
| `unit/test_w9_citations.py` (new) | - | 2.6 | 2.6 |
| `integration/test_w9_wp9_4_2_replay.py` (new) | - | 13.0 | 13.0 |
| `integration/test_w9_wp9_4_2_runtime.py` (new) | - | 160.7 | 160.7 |
| `unit/test_w9_reader.py` | 4.2 | 5.8 | 1.6 |
| `contracts/test_w9_legacy_routes.py` | 10.4 | 10.9 | 0.5 |
| `contracts/test_w9_pilot_promotion_table.py` | 0.9 | 0.9 | 0.0 |
| `contracts/test_w9_import_seam.py` | 1.4 | 1.4 | 0.0 |
| `integration/test_w9_legacy_replay.py` | 65.9 | 67.7 | 1.8 |
| `integration/test_w9_legacy_runtime.py` | 76.7 | 79.8 | 3.1 |
| `integration/test_w9_wp9_3_runtime.py` (paired means) | 134.0 | 131.8 | -2.3 |
| `integration/test_w9_wp9_4_1_replay.py` | 12.7 | 19.7 | 7.0 |
| `unit/test_schema_registry.py` (paired means) | 289.5 | 285.6 | -3.9 |
| `smoke/test_wp6_1_06h_append_path_closure.py` | 35.8 | 34.4 | -1.4 |
| **Total** | | | **182.7** |

The new files add 176.3s, and the changed files 6.4s. Run-to-run noise on this machine is up to 10s per file, so treat
any single row's difference under that as zero.

**The regression at `707cbe0d`: 1,289 passed and 1 failed, across 38 files, in 2,736s of serial wall time.**
- The failure is `test_w9_wp9_3_inventory_builder.py::test_the_output_guard_requires_a_vault_root`. It fails because the
  worktree sits under `.apm/`: it raised `"W9 tool output is under .apm/: out.json"` before the vault-root check it
  expects. This is the path sensitivity in WP9.4-1's record §7, not a WP9.4-2 defect. Report it as 1 failed with that
  cause, not as a pass.
- The 38 files: every `tests/research_system/**/test_w9_*.py` file (34), the 06h smoke test, `test_schema_registry.py`,
  `test_command_cli.py` (11 passed) and `test_store_binding_cli.py` (6 passed).
- The slowest files were `test_w9_wp9_3_binding_head.py` (611.5s), `test_w9_wp9_4_1_runtime.py` (556.9s),
  `test_schema_registry.py` (286.6s), `test_w9_wp9_3_2_runtime.py` (223.1s) and `test_w9_wp9_4_2_runtime.py` (160.7s).
  None of the first four changed on this branch.

## Not required

- Splitting the large test functions. Several new tests check many guards in sequence, so one failure hides the checks
  after it. Leave them; the mutation table in fix 2 shows each guard is caught.
- The commit trailer. Your commit's trailer reads `Antigravity`; use your model's name in this round's commits. Do not
  amend `707cbe0d`.

## Verification

- Run `test_w9_evidence.py`, `test_w9_evidence_acceptance.py` and `test_w9_open_items.py` after fix 4, with
  `uv run --env-file .env python -m pytest <files> -q -p no:cacheprovider --no-cov`.
- Run any mutation you add under fix 2.
- The full regression is not needed again. These fixes change one comment and the record.

## What to hand back

1. Status first: `COMPLETE` or `PARTIAL - <exact gap>`.
2. The new head, and `git log --oneline 707cbe0d..HEAD`.
3. For each fix, what changed, with `path:line`.
4. Any mutation you added, and its result.

Do not describe the work as reviewed, accepted or ready to merge.
