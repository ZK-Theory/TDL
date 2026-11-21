# Follow-up 2: WP9.4-2 review fixes, second round

Your commit `ecd08a1b` has been reviewed. Fixes 1, 4 and 5 are done as asked. The reviewer reran `test_w9_evidence.py`,
`test_w9_evidence_acceptance.py` and `test_w9_open_items.py` at `ecd08a1b`: 71 passed.

The new departures section listed three changes that the old record called "rulings". No governing document makes
them; they were your readings. Stephen has now decided all three (in chat, 2026-11-21):
- **Departure 3, `authority.py`'s `SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES` entries: accepted.** Note §14 cites
  `authority.py:208-252`, which covers both tables, and every earlier W9 command is in both. The handover's §4 was
  narrower than the note. The two lines are part of the `authority.py` bytes Stephen re-accepts at D-4.
- **Departure 4, `LR-053`'s open-items blob: accepted.** Required when `LR-053` targets `LR-054`, refused when it
  targets `LR-055`, as a reading of note §5.4 item 3, §5.5 and §8.
- **Departure 5, `LR-055`'s window re-read: kept as built, with its limit recorded.** No code change. For a paper root,
  `LR-055` re-lists the tracked files and re-reads every row blob of the inventory recorded before `LR-054`. So any
  change under the root after `LR-054`, while the root is `successor_owned`, blocks `LR-055` until WP9.6 can supersede
  that inventory. Note §15's W9-T6 row supports the reading; the annex's `LR-055` row says it adds no precondition.

The fixes below change comments and the record only. Same branch, same worktree, same rules as before:
- commits written with `git commit -F <file>`, the file UTF-8 without a BOM;
- never `--no-verify`, no push, no PR, no merge;
- the handover's §4 boundary, with `reader.py`'s `member_path` and the two extra `authority.py` lines now allowed.

## Where you are

- Worktree: `C:\Users\steph\TDL\.apm\worktrees\wp9-4-2`
- Branch: `pipe/w9-wp9-4-2-full-path`, head `ecd08a1b`

Before any write, confirm the branch, that HEAD is `ecd08a1b`, and that `git status --short` is clean.

## The fixes

### 1. Record Stephen's three decisions (§3.1 items 3 to 5)

Add to each item: Stephen's decision, "in chat, 2026-11-21", and the wording above. Departure 5 also goes in §7 as a
known limit carried to WP9.6, with its consequence stated as above.

### 2. Stop calling them rulings in the code

These comments cite "Ruling 3" or "Ruling 4", which do not exist:
- `research_system/legacy/preparers.py:612`, `:637` and `:663`;
- `research_system/legacy/replay/reducers.py:1070`;
- `tests/research_system/integration/test_w9_wp9_4_2_replay.py:633` and `:727`;
- `tests/research_system/integration/test_w9_wp9_4_2_runtime.py:1078`.

Replace each citation with the record's departure, for example `(WP9.4-2 record §3.1 item 5)`. Change the comment text
only. Leave the test function name `test_lr050_to_lr055_w9t5_w9t17_ruling3_and_owner_point_l` as it is, and say in the
record that "ruling3" in that name means departure 4. Search the branch for any other "Ruling" citation you added and
treat it the same way.

### 3. Use P-087's own item numbers in §6.2

§6.2 labels its groups "P-087 item 1 / Decision item 3" and so on, and the mutation rows say "P-087 item 2" and "P-087
items 1 & 4". Those are the handover's §3 numbers, not P-087's. The last follow-up caused this by saying "P-087 items
1 to 4"; it meant the handover's §3 items 1 to 4. Use P-087's numbers everywhere, as §1.5 does: item 3 (O's additions),
item 4 (`root_id` dropped), item 5 (the reader's flag), item 6 (the second-registration test).

### 4. Show which test catches M16 and M17

§6.2 lists M16 and M17 as covering P-087 item 6, but its table says the O test catches them, not
`test_p087_item6_second_registration_refused_with_active_whole_file_adoption`. That test's third form registers a file
whose path and target are both under the recorded root, so either prefix check alone may still refuse it.

Run M16 and then M17 against the item 6 test alone (`-k test_p087_item6`), restoring the bytes after each as before.
Report each as caught or survived. In §6.2, list for item 6 only the mutations its own test catches, and say that M16
and M17 are caught by the O test if that is the result. Do not change the tests.

### 5. Cite both preparer sites for the root's `git_tracked` check (§1.4)

§1.4 cites `preparers.py:264-265` as the preparer site. At `LR-003`, `prepare_proposal` runs
`_require_physical_identity` (`:691`), which makes that check, and then `r._check_registration` (`:693`), which makes it
again. Cite both, and say that M48's survival shows they duplicate each other, so no test can tell them apart.

## Verification

- `ruff check` and `ruff format --check` on the changed `.py` files.
- `uv run --env-file .env python -m pytest tests/research_system/integration/test_w9_wp9_4_2_replay.py
  tests/research_system/integration/test_w9_wp9_4_2_runtime.py -q -p no:cacheprovider --no-cov` after fix 2.
- The two mutation runs in fix 4.

## What to hand back

1. Status first, on its own line: `COMPLETE` or `PARTIAL - <exact gap>`. The last handback had no status line.
2. The new head, and `git log --oneline ecd08a1b..HEAD`.
3. For each fix, what changed, with `path:line`.
4. M16's and M17's results against the item 6 test.

Do not describe the work as reviewed, accepted or ready to merge.
