# Handover: build WP9.4-2 (the W9 full path) in the TDL repository

You are implementing one code package, WP9.4-2, in Stephen's TDL repository on his Windows machine. Its design is
settled. Your job is to build it exactly as specified, with tests, and hand back a branch for review. Nothing you
produce is merged without a separate review, so report honestly. A partial result with exact gaps is worth more than a
claim of completeness.

WP9.4-2 is the second half of WP9.4. The first half, WP9.4-1 (adoption and discharge), is merged and accepted (P-087).
WP9.4-2 is larger, and unlike WP9.4-1 it adds two runtime-binding rows, so it carries a D-4 re-acceptance (§6 below).

## 1. Where you work

| Item | Value |
|---|---|
| Repository | `C:\Users\steph\TDL` (GitHub `ZK-Theory/TDL`); base branch `main` |
| Your branch | `pipe/w9-wp9-4-2-full-path`, which you create (below) |
| Your worktree | `C:\Users\steph\TDL\.apm\worktrees\wp9-4-2` |
| Base commit | `origin/main` once it holds register entry P-087. Record the exact commit in your record |
| Platform | Windows 11, PowerShell 5.1 and Git Bash, Python 3.13 managed by `uv` |
| `.env` | Gitignored, so a new worktree lacks it. Copy it right after creating the worktree (below). Without it, `uv run --env-file .env ...` fails silently |

**Setup, once, from `C:\Users\steph\TDL`:**
1. Run `git fetch origin`.
2. Check the base:
   - `git grep -q "### P-087" origin/main -- docs/plans/agentic-research-system/03-decisions-and-open-questions.md` exits 0;
   - `git merge-base --is-ancestor cc81b733 origin/main` exits 0.

   If either fails, stop and report: P-087 is not on `main` yet.
3. Run `git worktree add -b pipe/w9-wp9-4-2-full-path .apm/worktrees/wp9-4-2 origin/main`.
4. Run `Copy-Item "C:\Users\steph\TDL\.env" "C:\Users\steph\TDL\.apm\worktrees\wp9-4-2\.env"`.
5. In the worktree, run `uv sync --extra dev`. pytest is in the `dev` extra, so a plain sync leaves it out. If
   `uv sync` fails with "Failed to update Windows PE resources ... Access is denied" in `%TEMP%`, set `TEMP` and `TMP`
   to `C:\t\uvtmp` for that command.

**Before any write,** verify in the worktree:
- the current directory;
- `git branch --show-current` is `pipe/w9-wp9-4-2-full-path`;
- `git status --short` shows nothing you did not make.

Work only in this worktree. Apart from the setup steps above, never touch the main checkout at `C:\Users\steph\TDL`,
or any other worktree under `.apm\worktrees\` or `.claude\worktrees\`.

## 2. Read these first, in this order

All paths are relative to the worktree root.

1. **The project's rules:** `CLAUDE.md`, `.claude/CLAUDE.md` and `AGENTS.md`. Some of their tool advice names
   Claude-specific tools; follow the substance (read before editing, search with a content search, never skip hooks).
   `.claude/rules/python.md` gives the code conventions.
2. **Locked project decisions:** `CONVENTIONS.md`.
3. **The specification:** `docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md` (revision 8). Read
   all of it once.
   - **Your spec:** §2 (scope, the commands and the split), §10 (the full path), §11 (citation status and the
     extractor), §12 (the reference graph), §13 (the `cited-families` verb), §14 (bindings and D-4), §15 (the tests
     marked `2` or `both`), §16 to §18, and §19 rows I, K and O.
   - **Already built in WP9.4-1:** §1 to §9. Read them, because WP9.4-2's rows read adoptions, their suspension and
     the legacy read interface, but do not rebuild them.
   - **Change logs:** §20 to §26. Read them for why a rule is shaped as it is, not as requirements. §26 matters
     most: it explains the LR-003 collision rules.
4. **The decisions that govern the note:** `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`,
   entries P-085, P-086 and **P-087** (search `### P-087`).
   - P-086 records Stephen's answer to each owner point A to O. Where the note's §19 and P-086 differ, P-086 governs.
   - P-087 dispatches WP9.4-2 and adds five things to it (§3 below). Where P-087 and the note differ, P-087 governs.
5. **The previous half, as a pattern and a base:**
   - `transition/w9/wp9-4-1-record.md`: what WP9.4-1 shipped, its readings R1 to R5, its departures, its known limits
     and its obligations. §7's obligations list names three WP9.4-2 items.
   - Your PR needs a record of the same shape (§6 below).
6. **Earlier W9 packages:**
   - `transition/w9/wp9-3-design-note.md` and the `wp9-3-*-record.md` files: WP9.3, whose checks owner point K reads
     in five places;
   - `transition/w9/wp9-3-1-record.md` §5: the D-4 table to copy for your own D-4;
   - `transition/w9/wp9-1-stage-b-design-note.md`: the five-step authority flow;
   - `transition/w9/wp9-1-catalogue-owner-annex.yaml`: the owner annex, row by row (LR-035 and LR-039 to LR-055 are
     yours).
7. **The plan and its paths:**
   - `docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md`: WP9.4, §2.7, §2.8, §8 and
     D-4 (search `| D-4 |`);
   - `implementation/06v-addendum-2026-11-10-w9-paths.md`: the "Citation disambiguation file" row is yours to
     re-cite with your constant and its line, as that file's 2026-11-20 amendment asks.
8. **The code you extend:**
   - `research_system/legacy/`, especially `routes.py`, `commands.py`, `preparers.py`, `records.py`, `runtime.py`,
     `evidence.py`, `reader.py`, `projection_read.py`, `replay/reducers.py` and `replay/driver.py`;
   - `research_system/schema_registry.py` and `research_system/authority.py`, for the bindings (§4);
   - `research_system/cli.py`.
   - The record schemas are under `.research-system/schemas/contracts/w9/`, read only. Both `legacy-paper-root` and
     `legacy-paper-citation-status` exist there already.
9. **The tests you extend:**
   - `tests/research_system/integration/test_w9_*.py`, `w9_flows.py` and `w9_runtime_harness.py`;
   - `tests/research_system/unit/test_w9_*.py` and `tests/research_system/contracts/test_w9_*.py`;
   - for D-4: `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py`, its manifest
     `wp6_1_06h_current_append_manifest.yaml`, and `tests/research_system/unit/test_schema_registry.py`.

Two repository skill files are useful as plain method documents:
- `.agents/skills/contract-first-tdd/SKILL.md`: write the failing test and its negative control before the code;
- `.agents/skills/research-assurance-triage/SKILL.md`.

## 3. What WP9.4-2 is

The note's §2.4 and P-086 item 1 define it. WP9.4-2 is **the full path**:

| Rows | Record | Flow | Note sections |
|---|---|---|---|
| LR-035 | `legacy-paper-root`, ordinary | recorded directly by the analyst, through the new `CreateLegacyPaperRoot` | §10.1 |
| LR-039 | `legacy-paper-citation-status` | recorded directly by the independent reviewer, through the new `RecordPaperCitationStatus` | §11 |
| LR-040 to LR-044 | `legacy-source-inventory` | all five steps | §10.3 |
| LR-045 to LR-049 | `legacy-transition-mapping` | all five steps | §10.4 |
| LR-050 to LR-055 | `legacy-ownership-transitioned` | all five steps, with two resolution rows | §10.5 |

It also carries:
- **the root's registration and its member files** (§10.2): owner point K's five recorded readings of WP9.3's checks,
  each gated on role `legacy_manuscript_root`. Owner point O's directory identity, read handle-bound, applies at
  LR-003 and LR-005;
- **the citation extractor and its comparison** (§11.1, §11.2; owner point I): the tokenizer, the four classes,
  templates and empty stems, the disambiguation file `w9-citation-disambiguation/1` and its constant in `evidence.py`;
- **the reference-graph checks** (§12);
- **two command bindings and their authority entries** (§14; §5.6, owner point N): `CreateLegacyPaperRoot` and
  `RecordPaperCitationStatus`;
- **one read-only CLI verb:** `ars legacy cited-families --root <root id> [--reviewer-sha256 <hash>]` (§13). It
  writes nothing.

**P-087 adds five things.** Each is a requirement:
1. **O's additions** (P-087 item 3, note §19 O and §10.2).
   - Within O's role scope (`legacy_manuscript_root`):
     - LR-003 refuses a collision with a root, by the case-folded path scoped by `root_kind`, and by the physical
       target's prefix at a component boundary;
     - a root is `git_tracked`, in replay and at the preparer.
   - For every role:
     - LR-003's equality half compares `(volume_serial_number, stable_file_id)` and the case-folded
       `(root_kind, normalized_path)`;
     - the projection prefix test compares case-folded paths.
2. **`root_id` is not in the every-role equality key** (P-087 item 4). The key is scoped by `root_kind` alone, so a
   second registration of one path under another `root_id` of the same `root_kind` is refused.
3. **The reader ignores Git replacement refs** (P-087 item 5).
   - **The change:** `reader._git` (`research_system/legacy/reader.py:79-89`) passes `--no-replace-objects`, exactly
     as `evidence.py` does (WP9.4-1 Reading R5; `evidence.py:71-79`). That one change is the only edit to
     `reader.py` you may make.
   - **The test:** a binding test in `tests/research_system/unit/test_w9_reader.py` installs `git replace H R` in a
     scratch repository. It shows that the reader still reads the source and the importer blobs committed at `H`,
     and that a plain `git` call reads `R` at the same time.
   - **The record:** list this as a change to WP9.3's accepted reader. `reader.py` is in `IMPORTER_MODULES`, so
     observations made after the change carry a new `tool_sha256`.
4. **The second-registration binding test** (P-087 item 6; WP9.4-1 record §7). With a whole-file adoption recorded,
   a second registration of the same file is refused at LR-003. Cover every form §10.2 names: a case variant, the
   same physical file at another path, and a file under a recorded root.
5. **The test-time budget** (P-087 item 7). Your new and changed test files may add at most **5 minutes**, measured
   serially with `--no-cov`, against the same files' time at the base commit.
   - Before you add a scratch-store flow, profile one slow test alone and say where its time goes.
   - Prefer forged-ledger replay tests where the check is a replay check. Use a scratch store through `submit` only
     where the check sits at the preparer or the runtime.
   - Measure as you go, not only at the end. If you cannot meet the budget, stop and report **Partial** with the
     measurements. Do not record it as a known limit.

**LR-035 and LR-054 refuse on every store** until WP9.7 routes LR-022 (owner point D; note §2.2). Build them and test
their positive paths against a **test route set** that adds LR-021 and LR-022, as WP9.2 tested its deferred reducers.
On the production route set, test that they refuse with their own message.

**Not yours:**
- **WP9.7:** the CreateTask and AmendTask guard (owner point J), the content rule at use and at promotion (owner
  point E), LR-021 and LR-022;
- **WP9.6:** the recovery half of W9-T21;
- **Anything WP9.4-1 built,** except where a WP9.4-2 row needs an extension, which the record lists.

## 4. The boundary and the hard rules

**Allowed edits** (P-085's Boundary, extended by P-086 item 13 and P-087):
- `research_system/legacy/**`. For `reader.py`, only P-087 item 5's flag;
- `research_system/schema_registry.py`: the two `SchemaBinding` rows, and nothing else;
- `research_system/authority.py`: the two subject-kind entries (§5.6; `_SCOPED_COMMAND_SUBJECT_KINDS`), and nothing
  else;
- `research_system/cli.py`: the `cited-families` verb only;
- tests under `tests/research_system/`. That includes, for D-4 only:
  - the 06h manifest YAML's count and digest;
  - the 06h smoke test, only if its pins need the new count;
  - `test_schema_registry.py`'s count pin;
- `tools/research_system_durations.json`, for the shard weights of new test files;
- `docs/plans/agentic-research-system/transition/w9/wp9-4-2-record.md` (new; §6);
- the "Citation disambiguation file" row of `implementation/06v-addendum-2026-11-10-w9-paths.md`, re-cited with your
  constant and its line.

**Must not change:**
- anything under `.research-system/`: schemas, contracts and evidence files. Neither evidence file exists, and you
  must not create either. Tests use fixture files under `tmp_path`;
- `research_system/store/`, `command/`, `discovery/` and `projection/`;
- `tools/w9_segmentation.py`;
- the append-site classification, any schema tree ID, and the T2 validator expectations and seal. The two new rows are
  command bindings under `ars://core/command` 1.0.0, so none of these should move. If one does, stop.

The census goes from 273 rows to **275** (note §14). If you find you need any other row, a schema change, or an edit
outside the allowed list, **stop** (§7).

**Never:**
- write to any real ARS store, create one, run genesis on one, or issue a grant on one. Every store in every test is
  a scratch store under pytest's `tmp_path`, and every source a scratch Git repository under `tmp_path`. Never touch
  `C:/Users/steph/TDL-ARS-G6-Control`;
- write under `papers/`, `results/`, `.apm/` state files, the Obsidian vault, or any legacy file;
- read a real paper file, a vault file or restricted bytes from a test. The extractor's tests use fixture copies of
  the citation forms §11.1 lists;
- edit the design note, the decisions register, `CONVENTIONS.md`, `CLAUDE.md` or `AGENTS.md`. If the spec looks wrong,
  report it; do not fix it;
- commit on `main`, push, open a pull request, or merge. Commit on your branch only. Stephen reviews the branch
  locally first.

## 5. How to build it

1. **Plan against the rows.** For each of LR-035 and LR-039 to LR-055, list:
   - what the annex row requires;
   - what the note adds;
   - which site enforces it: the preparer, replay, or both;
   - the test that proves it.

   §15 gives the required tests; every row marked `2` or `both` is yours. Keep this mapping, because it becomes the
   record's table. Do the same for P-087's five items and for K's five readings.
2. **Test first.** For each check, write the failing test and a negative control that shows the test can fail, then
   the code.
   - A test must assert the refusal's own message, not just "an error", so that a different refusal cannot satisfy
     it.
   - Replay checks get forged-ledger tests. Preparer and runtime checks get scratch-store integration tests through
     `submit`, as `test_w9_wp9_4_1_runtime.py` does.
   - Every refusal through `submit` must leave three things unchanged: the ledger events, the runtime control root,
     and the ledger's own control root. Use a snapshot like `_snapshot` in `test_w9_wp9_4_1_runtime.py:73-80`.
   - Every positive path needs a control that fails when its guard is removed.
3. **Reuse WP9.3's and WP9.4-1's machinery** rather than building a parallel path:
   - the five-step flow in `preparers.py`, `replay/reducers.py` and `w9_flows.py`;
   - `review_id_for`, the fixture-ref encoding and the G4 subjects;
   - the read interface in `projection_read.py`.
4. **The real positive paths first.** Before widening the negatives, get these working on scratch stores:
   - one ordinary root through LR-035, on the test route set;
   - one citation status through LR-039;
   - one inventory, one mapping and one ownership transition through their five steps.
5. **Mutation check, before you report.** As WP9.4-1 did, write a scratch script (not committed) that:
   - removes or inverts each guard you added, one at a time;
   - runs the tests;
   - restores the file byte for byte, checked by SHA-256.

   Every guard must be caught by a failing test that asserts its own message. Report the count caught out of the
   count tried, and the ones missed, with what you added to catch them. Include P-087 items 1 to 4.

**Code conventions:**
- Python 3.13, with 120-character lines and ruff rules E, F, I and W;
- type hints on public functions, and Google-style docstrings;
- imports ordered standard, third-party, local;
- format only the files you changed (`uv run ruff format <files>`), never a directory.

## 6. Verification, D-4 and the record

**Commits.**
- Use the subject `[PIPELINE] P06: WP9.4-2: <what>`, then a body.
- End every message with the line `Co-Authored-By: <your model name> <noreply@google.com>`, so the history shows which
  model wrote it.
- Write each message to a file outside the repository, and commit with `git commit -F <file>`. Never pass the message
  in a shell here-string.
- Write that file as UTF-8 **without a BOM**. In PowerShell 5.1, use
  `[IO.File]::WriteAllText(<path>, <text>, (New-Object Text.UTF8Encoding $false))`. A BOM breaks the commit-message
  hook.
- **Never use `--no-verify`.** The pre-commit hook runs ruff, a CRLF check, and the math-correctness contract gate over
  104 contracts, so a commit can take minutes.
- Do not pipe `git commit` into another command. Redirect its output to a file, then check `git log -1` to confirm
  HEAD moved.
- If a hook fails, fix the cause.

**Tests.**
- **As you go,** run the files you add or change:
  `uv run --env-file .env python -m pytest <files> -q -p no:cacheprovider --no-cov`.
- **At your final head,** run the full W9 regression once. Run it in the background with its output going to a
  file, rather than in a foreground call that may time out. The set is:
  - every `tests/research_system/**/test_w9_*.py` file;
  - `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py`;
  - `tests/research_system/unit/test_schema_registry.py`;
  - `tests/research_system/integration/test_command_cli.py`, and every test that drives `ars legacy` through the CLI.
    Find them with a content search for `"legacy"` in `tests/research_system/`.
- **Report** the pass, fail and skip counts, and the wall time.
- **Report the time budget** (§3 item 5) per file: each new or changed file's time at the base commit and at your
  head, serial, `--no-cov`, and the total added.

**D-4.** Your record gives a table in the shape of `wp9-3-1-record.md` §5, before and after:
- the runtime-binding census row count and digest (273 rows, `0cca0414641bf4fbed32b5f42d7c3753a8c47dcdd09d815dcba0658ef8814712`,
  before);
- the 06h manifest YAML: blob, SHA-256 and byte length (blob `4c8950421d3a9f25da7cf4b657a358536df42332` before);
- `test_wp6_1_06h_append_path_closure.py`: blob, SHA-256 and byte length (blob
  `559d684a5d78abc285ce9b50dd23ce071aad32c5` before);
- the append-site classification: unchanged;
- the command and event schema trees: unchanged;
- `test_schema_registry.py`'s count pin.

Also show that `git diff --stat <base> HEAD` touches none of §4's must-not-change paths. Stephen re-accepts these
bytes as they stand in the merge-queue entry, so any later rebase needs them recomputed.

**The record.** Write `docs/plans/agentic-research-system/transition/w9/wp9-4-2-record.md` in the shape of
`wp9-4-1-record.md`:
- **the header:** date, status, package, authority (P-085, P-086, P-087, the note at revision 8), base, boundary, and
  not authorized;
- **what it routes,** row by row, with `path:line`;
- **K's five readings and O's additions,** each with its site and test;
- **P-087's five items,** each with its site and test;
- **D-4,** with the table above;
- **a tests table,** with case counts;
- **verification:** the regression, the mutation result, and the time budget;
- **every departure from the note,** each with its reason. A departure that is not listed is a defect;
- **known limits, obligations carried to later packages, and out-of-scope observations.**

Plain, direct English. Cite `path:line` for every code claim.

## 7. Stop rules

Stop and report **Partial** (do not work around it) when any of these holds. They come from the note's §18, 06v §8 and
P-087:
- a row needs a runtime-binding row beyond the two, a schema change, or any `.research-system/` change;
- the append-site classification, a schema tree ID or the T2 expectations would change;
- a row needs an edit outside §4's allowed list;
- a test needs a real paper file, a vault file or restricted bytes;
- a positive path for LR-035 or LR-054 can run without a passed LR-022 on the production route set;
- another site, beyond the five readings of §10.2, keys on registration where K's option 1 needs a path;
- a site other than LR-003's conflict check needs a prefix comparison for a root registration (§17 claim 15);
- the extractor, run on fixture copies of the citation forms in §11.1, leaves a candidate in no class, or blocks on a
  template that no disambiguation row can clear;
- the new test files exceed the 5-minute budget (§3 item 5);
- the note and the code contradict each other in a way that changes a row's behaviour, or the note is silent on
  something a row needs. Report the exact conflict with both citations; do not choose for Stephen;
- a guard cannot be tested without a real store.

Missing code, reducers, preparers, projections or tests are not stops. Build them; they are the job.

## 8. What to hand back

When you finish or stop, reply with:
1. **Status** first: `COMPLETE` (every WP9.4-2 row and P-087 item built and tested, the regression run, and the
   budget met) or `PARTIAL - <exact gap>`.
2. The branch, its head commit, the base commit, and `git log --oneline <base>..HEAD`.
3. The rows built, row by row, each with its tests. Then K's readings, O's additions and P-087's five items, the same
   way.
4. The regression counts and wall time, the mutation count, and the time budget per file.
5. The D-4 table.
6. Every departure from the note, and every place you were unsure of the spec, with citations.
7. Anything you saw outside your scope that looked wrong. Report it; do not fix it.

Do not describe the work as reviewed, accepted or ready to merge. It gets an independent review, then CodeRabbit, D-4
and Stephen's merge.
