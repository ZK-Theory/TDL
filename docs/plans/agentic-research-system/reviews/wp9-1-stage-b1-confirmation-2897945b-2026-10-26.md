# WP9.1 stage B1 confirmation at `2897945b`: revision 3

**Date:** 2026-10-26<br>
**Subject:** B1 revision 3, the single commit `2166721a..2897945b` on `pipe/w9-wp9-1-catalogue`. It changes 4 files:
- the verifier;
- its test;
- note §6;
- the reconciliation's §4.

**Mode:** A narrow confirmation (`adversarial-design-review`, remediation re-review). Each disposition in the
reconciliation's §4 is bound to code. Every new or changed control is checked to fail when, and only when, its own
check is removed. The reviewer edited nothing except this file.<br>
**Inputs:**
- the re-review `reviews/wp9-1-stage-b1-re-review-427d277a-2026-10-24.md` (commit `2166721a`);
- `reviews/wp9-1-stage-b1-reconciliation-2026-10-24.md` §4;
- Stephen's choice of option (a) for R-M1, with r-1 to r-6 in the same pass.

**Known limit (P-058):** one model family. Recorded as a limit, not as a finding.

## Verdict

**`pass`. Every re-review finding is closed, and the confirmation raises no new Blocking, Major or Minor finding.**

There are three Info notes (c-i1 to c-i3). None needs action before merge.

B1 is ready for Stephen's merge decision. The schema half is unchanged since the re-review: revision 3 touches no
schema, no generator and no stage A test.

## Finding by finding

| Finding | Disposition (reconciliation §4) | Bound to | Control, and what removing its check does | Result |
|---|---|---|---|---|
| **R-M1** note §6 edited a schema `const` | Option (a) | Note §6 now lists two contract edits for B2: the `forbidden` entry and the verification rule. Both are free `arr(TEXT, 1)` values. `expected_catalogue` and `acceptance_instance: forbidden_in_stage_a` stay, with the reason given | Probe X6 patched `HEAD`'s contract with B2's two edits. A catalogue pinned at the schema commit still verifies with `[]`. The verifier compares only the family and the owner tuples across commits, so B2's edits leave it green | **Closed** |
| **R-M2** a control that is not portable | Literal pre-fold identity | Test lines 33-43 hold literal values. Checked against Git: commit `8a0d68fc6038…`, blob `4e648b7f…`, 85,510 bytes, SHA-256 `cd483876…`. All match | Probe X1 replaced the commit with an absent `fff…f`, which simulates a clone without the branch. The asserted message still appears, so the control does not depend on the commit. The author's probe confirmed that deleting the blob check fails the control | **Closed.** See c-i1 |
| **r-1** a hollow off-main control | The exact message | Test asserts `owner_annex_identity.git_commit is not on 5d325c5b` | Deleting the annex ancestry branch fails the control (author's probe, rerun here) | **Closed** |
| **r-2** the `HEAD`-drift check had no control | New control at `5d325c5b` | `test_schema_changed_after_its_source_commit_is_refused` asserts the drift message for `w9-schema-catalogue-content` | Deleting the drift check fails it. `5d325c5b` is an ancestor of `origin/main` | **Closed** |
| **r-3** W9-C01 derived fields | Independent parse and literals | Each W9-C01 node checks `logical_key`, `receipt_identity` and `complete_write_set` against the plain-YAML parse, and checks the three `owner_annex_ref` constants | The probe-R7 bug, streams before events on 60 rows, is now caught by W9-C01 (author's probe, rerun here) | **Closed** |
| **r-4** the contract at the schema commit | `_check_schema_commit`, `W9_BOOTSTRAP_KINDS` | `verify_w9_materialization.py`, `_check_schema_commit`. It checks: `HEAD`'s family equals the pinned record and bootstrap sets; the family at the schema commit equals `HEAD`'s; the owner tuples equal `HEAD`'s contract; and the schema commit's tuples equal `HEAD`'s | Removing any one of the three new checks fails its control (author's probe). Removing the owner-tuples-versus-`HEAD` comparison fails `test_non_row_field_errors_are_refused` (probe X2) | **Closed** |
| **r-5** inner-shape tracebacks | Shape check, and a caught family read | `schema_source_rows` must be a non-empty list of objects with string commits before any use. The `_check_schema_commit` call catches `CalledProcessError`, `KeyError`, `TypeError` and `YAMLError` | Removing the shape check makes the malformed-rows control error (X3). Removing the `except` makes the `d660f091` control error (X4). `d660f091` is on `origin/main` | **Closed.** See c-i2 |
| **r-6** a test B2 must change | Named in §6 | Note §6 lists `test_required_absent_catalogue_fails` | n/a (docs) | **Closed** |
| ri-1 to ri-6 | Recorded | Reconciliation §4 | n/a | Closed |

**Branch-only SHA sweep.** Every hex literal in the two W9 test files was checked:
- the commits `5d325c5b`, `d660f091`, `4999111c` and `50371fac` are ancestors of `origin/main`;
- the blobs `2b40fae4`, `ea3a8e4a`, `8d588185` and `d8fbda41` are reachable;
- `8a0d68fc…` and `4e648b7f…` appear only as literal strings in the pre-fold identity, and X1 shows the control does
  not need them to resolve.

## Info

- **c-i1.** The reconciliation says the blob check refuses the pre-fold identity "before any Git read". The verifier
  still runs `git rev-parse` on the literal commit, at line 456. In a clone without that commit, the run adds a
  second problem ("not a full commit SHA"). The asserted message is unaffected (X1). This is a wording point only.
- **c-i2.** When `_check_schema_commit` raises, the problems it had already collected are discarded, and schema
  validation is skipped. One generic message replaces them (X5). The catalogue is still refused, so this loses
  diagnostics, not safety.
- **c-i3.** One model family (P-058).

## Regression check

| Check | Result |
|---|---|
| Files changed since `2166721a` | 4: the verifier, its test, note §6 and the reconciliation. No schema, generator, contract or stage A test changed, and nothing under `research_system/` |
| Tests | 244 passed: 177 verifier and 67 stage A |
| `w9_schema_gen.py --check` | exit 0 |
| Verifier, annex only | `61 pinned rows; 0 problem(s)`, exit 0 |
| ruff check and format | clean on the two changed Python files |
| Author's probe `probe_b1r3.py`, read and then run | 7 of 7 caught, `0 hollow` |
| Reviewer's probe `probe_r3.py` (X1 to X6) | as above |

## Decision audit

| Decision | Disposition |
|---|---|
| R-M1 option (a) (Stephen) | Keep. Implemented, and B2 can carry it out (X6) |
| P-072 item 6 (pin at B1's main commit) | Keep. It is now consistent with note §6 |
| P-074 items 1 to 3 | Keep. Unchanged since the re-review |
| P-058 | Known limit |

## Commands run (read-only; probes from the scratchpad)

```text
git switch pipe/w9-wp9-1-catalogue                          # HEAD 2897945b
git log --oneline 2166721a..HEAD; git diff --stat 2166721a..HEAD
git diff 2166721a..HEAD -- tools/verify_w9_materialization.py tests/.../test_w9_expected_catalogue.py \
    transition/w9/wp9-1-stage-b-design-note.md reviews/wp9-1-stage-b1-reconciliation-2026-10-24.md
git rev-parse 8a0d68fc; git rev-parse 8a0d68fc:<annex>; git cat-file -s 4e648b7f…; git cat-file blob 4e648b7f… | sha256sum
git merge-base --is-ancestor {5d325c5b,d660f091,4999111c,50371fac} origin/main   # all on main
grep -noE '"[0-9a-f]{7,40}"' <the two W9 test files>
python -I <gate7-prep scratchpad>/probe_b1r3.py <repo> <my scratchpad>/r3out   # 0 hollow
python -I <my scratchpad>/probe_r3.py <repo> <my scratchpad>/r3own            # X1-X6
python -I -m pytest tests/research_system/contracts/test_w9_contract_materialization.py \
    tests/research_system/contracts/test_w9_expected_catalogue.py -q -p no:cacheprovider -o addopts=""   # 244 passed
python -I tools/w9_schema_gen.py --check; python -I tools/verify_w9_materialization.py   # exit 0; exit 0
ruff check --no-cache <2 files>; ruff format --check --no-cache <2 files>               # clean
```

`python` is `C:/Users/steph/TDL/.venv/Scripts/python.exe`. Mutated sources were written only under the reviewer's
scratchpad. `git status` was clean after every command. No store, vault, `.apm/` or `papers/` path was written, and
nothing was pushed.

## Change log

- Added this file only.
