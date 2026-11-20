# Follow-up 3: WP9.4-1, CodeRabbit's second round on PR #439

CodeRabbit reviewed `d28a05b3` and resolved all ten of its first-round threads. It then raised new points on the PR head `cefc7f82`. A Claude session checked each point against the code. Decisions are below.

Make the changes marked **Fix** under the same rules as follow-up 2:
- commits written with `git commit -F <file>`, the file UTF-8 without a BOM;
- never `--no-verify`;
- the boundary in the first handover's §4;
- **no push**;
- **no GitHub replies** and no resolving of threads.

## First: catch up with `origin`

Stephen merged PR #440 into `main`, then updated #439's branch from `main` on GitHub. `origin/pipe/w9-wp9-4-1-adoption-discharge` is now `cefc7f82`: a merge commit whose first parent is your `d28a05b3`, adding #440's four files. None of those files are WP9.4-1's.

In `C:\Users\steph\TDL\.apm\worktrees\wp9-4-1`, do these in order:
1. Confirm `git status --short` is clean and HEAD is `d28a05b3`.
2. Run `git fetch origin`, then `git merge --ff-only origin/pipe/w9-wp9-4-1-adoption-discharge`.
3. Confirm HEAD is `cefc7f82`.

Do not rebase and do not create another merge. If the fast-forward fails, stop and report.

## The fixes

Every new or changed guard gets a test that asserts the guard's own message, plus a negative control that passes. Every refusal through `submit` leaves the snapshot unchanged, where the snapshot is the widened one from fix 3.

1. **LR-026 and LR-031 need a real review question** (comment on `research_system/legacy/replay/reducers.py:1135`).
   - Today a request whose only `review_questions` entry is `w9-applicable-fixtures:` passes, and it takes the review reservation.
   - For both rows, require at least one non-blank entry that is not the fixture entry. Refuse with a message such as `"W9 review request carries no review question besides the applicable-fixtures entry"`.
   - Keep an empty fixture entry valid for a discharge request that also has a question.
   - Tests:
     - a forged-ledger refusal at LR-031 with only `["w9-applicable-fixtures:"]`;
     - the same at LR-026, with only its fixture entry;
     - controls: the existing flows, each with a question and the fixture entry.

2. **The import-seam test reports an allowed submodule import** (comment on `tests/research_system/contracts/test_w9_import_seam.py:89`).
   - In an allowlisted importer, `from research_system.legacy.replay import reducers` records `research_system.legacy.replay` and is reported. The direct `import research_system.legacy.replay.reducers` passes.
   - When `from <legacy module> import <name>` names a submodule, record `<legacy module>.<name>`. A submodule is one that exists as a module file or package under `research_system/legacy/`. When `<name>` is a symbol, keep recording `<legacy module>`. For example, `from research_system.legacy.replay.driver import replay_legacy` stays `research_system.legacy.replay.driver`.
   - Add positive controls for both forms in an allowlisted importer. Keep every existing negative control.

3. **Widen the refusal snapshot to the ledger's control root** (comment on `tests/research_system/integration/test_w9_wp9_4_1_runtime.py:74`).
   - `_snapshot` covers `store.events()` and `store.runtime.control_root`. The ledger's own control root, `store.harness.ledger.control_root`, is a separate directory, and nothing covers it.
   - Make `_snapshot` include the tree of the ledger's control root as well. If a part of that tree legitimately changes on a refusal, exclude only that part, by name, with a comment saying why. A lock file is the likely case.
   - Then rerun every test that uses `_snapshot`.

4. **The retry tests should compare the whole receipt** (comment on `test_w9_wp9_4_1_runtime.py:636`). Assert `retried == receipt` for each W9-C11 retry, and keep the separate no-append assertion.

5. **The O-33 test should check its own setup** (comment on `test_w9_wp9_4_1_runtime.py:952`).
   - Assert that the file-changing callback ran, by checking that the file's bytes changed.
   - Then, on the path where LR-029 commits, assert that the recorded adoption carries the original observation reference and hash.
   - A test that can pass when its callback never runs is not evidence.

6. **Evidence files: treat a parse `ValueError` as an evidence refusal** (comment outside the diff, on `research_system/legacy/evidence.py:85-86`).
   - `json.loads` raises a plain `ValueError` for an integer longer than CPython's limit, about 4,300 digits. `read_evidence` catches only `UnicodeDecodeError` and `json.JSONDecodeError`, so the CLI shows a traceback.
   - Catch `ValueError`, which `JSONDecodeError` subclasses, and raise the existing `"W9 evidence file is not JSON: <path>"`. Don't raise the integer limit.
   - Test it with a scratch evidence file holding a 5,000-digit integer.
   - This is WP9.3's shared reader, so the change reaches every W9 evidence file. Record it in record §3 as a reading, not a departure: it only turns a crash into the documented refusal.

7. **The open-item reader: check the bytes against the blob before parsing** (comment outside the diff, on `evidence.py:404-405`).
   - `require_open_items` gets content through `read_evidence`, which runs `git show`, and gets the blob through `blob_at`, which runs `git rev-parse`. A Git replacement object can make `git show` return bytes that are not that blob, and the membership check would then run on them.
   - In `require_open_items`, read the raw bytes, check `git_blob_id(raw) == blob`, and only then parse. That is the check `LegacyReader._git_object` already makes (`reader.py:261-266`). Refuse with a message such as `"W9 open-item list bytes do not hash to their blob at git_head"`.
   - Do not change `reader.py`: its blob is pinned in the importer hash.
   - Test it in `test_w9_open_items.py`. Either install a real `git replace` object in the scratch repository, or monkeypatch the content read to return other bytes, and say in the docstring which one you used.
   - Then add to record §7's out-of-scope list: WP9.3's other evidence reads through `read_evidence` have the same gap, which is not changed here.

8. **Two builder nitpicks** (`tests/research_system/integration/w9_flows.py:776-777` and `:835`). Default `subject`, `intended_use` and `successor_result_ref` only when the argument is `None`, so an explicit `{}` reaches the schema. Add one test showing an explicit `{}` reaches the schema and is refused there.

9. **W9-T1 through the real observation preparer** (CodeRabbit's reply on the W9-T1 thread, `tests/research_system/unit/test_w9_projection_read.py:436`).
   - The forged-ledger test never passes the `Done` bytes through `prepare_observation`.
   - Add a scratch-store test in `test_w9_wp9_4_1_runtime.py`:
     - commit a JSON source whose bytes contain a `Done` status word;
     - register it, accept its membership table and observe it through `store.observe`, which runs the preparer;
     - assert that no `legacy_adoption_decision` exists in the replayed state, and that `family_admissible` for the observed family is `unadopted`.
   - Keep the forged-ledger test, and correct its docstring to say it shows only that the recorded path admits nothing without an adoption.

## Record only (no code change)

10. **Record §7, known limits: how a discharge recovers** (comment outside the diff, on `preparers.py:758`).
    - If the open-item file at `git_head` changes after LR-033, LR-034 refuses every attempt, and a WP9.3-style resolution can only `accept`. So the discharge ends when its proposal lapses after 30 days (`PROPOSAL_TERM`). Until then, a new LR-030 for the same item is refused as already open.
    - WP9.3's rows behave the same way when a re-read fails at resolution.
    - Whether a discharge should get a reject path is open for Stephen.
    - Do not add one.

## Declined; do not change

- **Running the owner-as-reviewer check before the version-conflict receipt** (comment on `runtime.py:497`). A stale-version envelope gets the conflict receipt before any content check runs, the same order every WP9.3 preparer refusal follows. Moving this one check earlier would make it the only exception.

## Verification

- Run every file you change, and every file that uses `_snapshot`:
  - `test_w9_wp9_4_1_runtime.py`, `test_w9_wp9_4_1_replay.py`, `test_w9_import_seam.py`, `test_w9_open_items.py` and `test_w9_projection_read.py`;
  - for fix 6, `test_w9_evidence_acceptance.py` and any other test of `read_evidence` you find with a content search;
  - `test_w9_wp9_3_runtime.py` and `test_w9_wp9_3_2_runtime.py`.

  Use `uv run --env-file .env python -m pytest <files> -q -p no:cacheprovider --no-cov`.
- Run the mutations for fixes 1, 6 and 7, one guard at a time. Also run one for fix 3: make a refusal path write a file under the ledger control root, and show the widened snapshot catches it. Restore every file byte for byte.
- `ruff check` and `ruff format --check` on every changed Python file.
- Update the record:
  - a "CodeRabbit second round" section listing items 1 to 10, each with `path:line`, test and message;
  - §3 for fix 6;
  - §5's counts;
  - §6's runs, labelled by commit, and the mutations;
  - §7 for items 7 and 10.
- Commit once on top of `cefc7f82`, with the subject `[PIPELINE] P06: WP9.4-1: CodeRabbit second-round fixes on #439` and your `Co-Authored-By` trailer.

## Hand back

1. `COMPLETE` or `PARTIAL - <gap>`.
2. The new head, `git log --oneline cefc7f82..HEAD`, and confirmation that the fast-forward landed on `cefc7f82`.
3. For each of items 1 to 10: what changed (`path:line`), its test, and the message it asserts.
4. Pass, fail and skip counts and wall time for each file you ran.
5. Each mutation and its result.
6. What, if anything, you excluded from the widened snapshot, and why.
7. Anything you were unsure of.

Do not describe the work as reviewed or ready to merge.
