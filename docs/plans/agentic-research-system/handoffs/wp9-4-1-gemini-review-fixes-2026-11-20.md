# Follow-up: WP9.4-1 review fixes

Your WP9.4-1 branch has been reviewed. The code matches the design note, and the reviewer's own reruns passed:
- 187 tests across the four fast new files and the route and replay files you changed;
- 9 tests in `test_w9_wp9_4_1_runtime.py`.

The departure at LR-033 is accepted as recorded. Your report of the shallow `.git` and the `.apm/` path sensitivity was correct and useful.

The review found three things to fix and two nits. Make them on the same branch, in the same worktree, under the same rules as the first handover:
- commits written with `git commit -F <file>`, the file UTF-8 without a BOM;
- never `--no-verify`, no push, no PR, no merge;
- the boundary in that handover's §4.

## Where you are

- Worktree: `C:\Users\steph\TDL\.apm\worktrees\wp9-4-1`
- Branch: `pipe/w9-wp9-4-1-adoption-discharge`, head `fe8fcc71`

Before any write, confirm the branch, that HEAD is `fe8fcc71`, and that `git status --short` is clean.

## The fixes

### 1. Test LR-034's content recheck at LR-034 itself (design note §15, the "LR-034's negatives" row)

§15 asks for LR-034 to refuse "a byte copy of a recorded legacy observation as the successor result".

`prepare_resolution` does recheck this at LR-034, in `check_discharge_resolution` (`research_system/legacy/preparers.py`, the LR-034 branch). That calls `_check_discharge_artefact`, which calls `legacy_content_matches`. But only LR-030 tests that check (`test_w9_wp9_4_1_runtime.py`, around lines 1223-1230). If the LR-034 branch stopped calling the check, every test would still pass: your mutation suite mutated the shared function, which the LR-030 test catches.

Add a test where the successor result is clean at LR-030 and becomes a match before LR-034. A legacy observation with the artefact's SHA-256, or its Git blob, is recorded after LR-033. Then LR-034 refuses with `"W9 discharge successor result matches a recorded legacy observation"`, and the ledger and control root stay byte-identical.

- Prefer a real scratch-store path if `w9_flows.py` can record an observation cheaply.
- If not, a direct `preparers.prepare_resolution` call on a copied state is acceptable. Put an added recorded observation in the copied state, as your G3 check at step 3 of that test does (around lines 1363-1390). Say in the test's docstring why it is direct.

Then mutate only the LR-034 branch: make it skip the content check, leaving the function and LR-030 unchanged. Confirm the new test fails and that its failure names that message. Report the mutation and its result.

### 2. Refuse a missing review in LR-034's G3 recheck

In the same `check_discharge_resolution`:

```python
review = legacy["reviews"].get(record["reviewer_ref"]["id"])
if review is not None and review.get("reviewer") == manifest.get("producer_actor_id"):
```

A missing review passes this check silently. Replay's G5 makes that unreachable on a real ledger, but a guard that passes on missing input is the wrong shape. Refuse it with its own message, such as `"W9 discharge resolution names no recorded review"`. Add a direct preparer test asserting that message, with a negative control. Check that the existing G3 message test still passes.

### 3. Correct the record's analyst-rule line

`docs/plans/agentic-research-system/transition/w9/wp9-4-1-record.md`, §1, the "Analyst rule" bullet (line 47), says the exemption adds `legacy_field_family_membership` and `legacy_ownership_transitioned`. The code (`replay/reducers.py`, `_refuse_analyst_creator`) adds `legacy_transition_mapping` and `legacy_ownership_transitioned`, which is what note §5.3 asks for. Exempting the membership kind would break WP9.3's LR-006 rule, so the record must not say it. Correct the line.

### Nits (fix both)

- `prepare_decision_proposal` (`preparers.py`): the refusal for a bad key set still reads "must carry exactly: consequences, question, recommendation, subject_record_id". It now admits three optional fields. Make the message say which are required and which are optional, and update any test that matches the old text.
- `test_w9_wp9_4_1_runtime.py:1407`: the comment "Restore exact blob at git_head via amending? No, commit exact initial bytes back -> same blob SHA-1!" is a working note. Replace it with one plain sentence on what the step does.

## Verification

- Run `test_w9_wp9_4_1_runtime.py`, `test_w9_wp9_4_1_replay.py` and any file you change, with `uv run --env-file .env python -m pytest <files> -q -p no:cacheprovider`.
- The full regression is not needed again. The fixes touch only the LR-034 preparer branch, one error message, tests and the record.
- Update the record:
  - add a short "Review fixes" section listing the three fixes and two nits, each with `path:line`;
  - add the new test cases to §5's counts;
  - add the new mutation to §6.
- Commit once, with the subject `[PIPELINE] P06: WP9.4-1: review fixes (LR-034 content and review rechecks, record correction)` and your `Co-Authored-By` trailer.

## Hand back

1. `COMPLETE` or `PARTIAL - <gap>`.
2. The new head and `git log --oneline fe8fcc71..HEAD`.
3. For each fix: what changed (`path:line`), the test that proves it, and the message it asserts.
4. Pass, fail and skip counts and wall time for each file you ran.
5. The LR-034 mutation and its result.
6. Anything you were unsure of.

Do not describe the work as reviewed or ready to merge.
