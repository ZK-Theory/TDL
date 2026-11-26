# Handover: build WP9.5 (the W9 detectors) in the TDL repository

For: a fresh Claude agent, dispatched by Stephen when he chooses (P-090 item 7). Written by the reviewing Claude
session on 2026-11-24.

You are implementing one code package, WP9.5, in Stephen's TDL repository on his Windows machine. Its design is
settled, through eight reviews of the design note, an exemption-row addendum with two reviews, and owner decisions
recorded in P-090. Your job is to build it exactly as specified, with tests, and hand back a branch for review.
Nothing you produce is merged without a separate independent review, CodeRabbit and Stephen's own merge, so report
honestly. A partial result with exact gaps is worth more than a claim of completeness.

**Merging WP9.5 does not take it live.** L-1, the detectors running on real `main` and the vault, is a separate owner
decision. WP9.5 ships inert (note §10).

## 1. Where you work

| Item | Value |
|---|---|
| Repository | `C:\Users\steph\TDL` (GitHub `ZK-Theory/TDL`); base branch `main` |
| Your branch | `pipe/w9-wp9-5-detectors`, which you create (below) |
| Your worktree | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-code` |
| Base commit | `origin/main` once it holds both the note with P-090 (#449, merged as `c63684a7`) and the accepted amendments (#451). Record the exact base in your record |
| Platform | Windows 11, PowerShell 5.1 and Git Bash, Python 3.13 managed by `uv` |
| `.env` | Gitignored, so a new worktree lacks it. Copy it right after creating the worktree (below) |

**Setup, once, from `C:\Users\steph\TDL`:**
1. Run `git fetch origin`.
2. Check the base. If any of these fails, stop and report which:
   - `git grep -q "### P-090" origin/main -- docs/plans/agentic-research-system/03-decisions-and-open-questions.md`
     exits 0;
   - `git grep -q "The amendments are accepted, 2026-11-24" origin/main --
     docs/plans/agentic-research-system/03-decisions-and-open-questions.md` exits 0 (P-090 item 6);
   - `git cat-file -e origin/main:docs/plans/agentic-research-system/transition/w9/wp9-5-owner-decision-amendments-2026-11-24.md`
     exits 0 (#451 merged).
3. Run `git worktree add -b pipe/w9-wp9-5-detectors .apm/worktrees/wp9-5-code origin/main`.
4. Run `Copy-Item "C:\Users\steph\TDL\.env" "C:\Users\steph\TDL\.apm\worktrees\wp9-5-code\.env"`.
5. In the worktree, run `uv sync --extra dev` (pytest is in the `dev` extra). If it fails with "Failed to update Windows
   PE resources ... Access is denied" in `%TEMP%`, set `TEMP` and `TMP` to `C:\t\uvtmp` for that command.

**Before any write,** verify in the worktree:
- the current directory;
- that `git branch --show-current` is `pipe/w9-wp9-5-detectors`;
- that `git status --short` shows nothing you did not make.

Work only in this worktree. Apart from the setup steps above, never touch the main checkout or any other worktree.

## 2. Read these first, in this order

All paths are relative to the worktree root.

1. **P-090**, in `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`, all seven items. It is the
   authority. Item 1 is the pin decision, item 2 the owner points, item 3 the amendments, item 4 the pre-code gates
   (all run), item 5 the further decisions, item 6 the acceptance of the amendments, and item 7 this dispatch. Also
   read its Boundary.
2. **The design note**, `docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md`, all of it except the
   change logs (§17 to §20). It is long, 273 KB. Read §1 to §16 and §21 in full. The sections you build from are §2,
   §5 to §12, §15 and §16.
3. **The accepted amendments,** `docs/plans/agentic-research-system/transition/w9/wp9-5-owner-decision-amendments-2026-11-24.md`.
   Its §1 changes accepted WP9.3 code. §2 is text for W9 §4.2, §3 is text for `CONVENTIONS.md`, and §4 is rows for the
   paths addendum. All of it is applied in your PR.
4. **The reviews,** under `docs/plans/agentic-research-system/reviews/`, for context on why the design is as it is:
   - `wp9-5-note-r8-review-2026-11-23.md`;
   - `wp9-5-note-exemption-addendum-review-2026-11-24.md` and its re-review;
   - `wp9-5-amendments-review-2026-11-24.md` and its re-review.
5. **The code you change or call,** at `origin/main`. Start with `research_system/legacy/evidence.py`,
   `acceptance.py`, `preparers.py`, `accepted_w9.py`, `reader.py` and `segmentation.py`, then `tools/w9_segmentation.py`,
   `.github/workflows/ci.yml`, `.github/CODEOWNERS` and `tests/tools/test_ci_platform_policy.py`.
6. **The repository rules:** `CLAUDE.md`, `.claude/CLAUDE.md`, `CONVENTIONS.md`, and `.claude/rules/python.md`.

## 3. What WP9.5 is

The deliverables are note §2.1. In short:
- **The detector tools** (all new, all standard-library only, run under `python -S -P` from a content-pinned tree):
  - `tools/check_legacy_writes.py`, the post-merge first-parent detector (Rules 0 to 3, `acknowledged`,
    `rule0_exemptions`);
  - `tools/check_conventions_legacy_locks.py`;
  - `tools/check_legacy_log_baseline.py`;
  - `tools/run_w9_detector_controls.py`;
  - `tools/run_w9_pinned_detectors.py`, the self-contained, ASCII-only operator wrapper;
  - `tools/_w9_detector_evidence.py`, the shared helper, with `EvidenceParseError`, `UnknownEvidenceFormatError` and
    `EvidenceSchemaError`.
- **The exporter,** `tools/export_w9_registration_manifest.py` (M-6). It is outside the pinned closure, and runs from
  the checkout (note HR-7).
- **The workflow,** `.github/workflows/legacy-write-detector.yml`, triggered by `workflow_dispatch` only, with no
  `inputs:` (note §10.2).
- **The tests:**
  - `tests/tools/test_w9_detectors.py`, in the unit lane and in `admission-controls`. It includes the `L1_LIVE = False`
    tripwire, the closure and stdlib tests on the assembled tree, the pin-step cases, the comparison procedure tests,
    and the exemption-row controls;
  - `tests/research_system/integration/test_w9_wp9_5_detectors.py`, in the `slow` and `integration` lanes, using a
    scratch store (M-6 and O-13).
- **The accepted amendments' code** (amendments §1), for A1, D3, E1 and J1. These change `evidence.py`,
  `acceptance.py`, `preparers.py`, `accepted_w9.py` and the tests they name, including the WP9.4 test builders.
- **The accepted text changes:**
  - W9 §4.2 (d), from amendments §2;
  - the `CONVENTIONS.md` and CODEOWNERS changes for I1, from amendments §3, with the two policy tests;
  - the paths-addendum rows, from amendments §4;
  - the `ci.yml` `admission-controls` wiring (F1, K1).
- **The WP9.4 re-record** (amendments §1 preamble): re-run the WP9.4 integration and unit files the WP9.4 records
  cite, and append a dated re-record to `wp9-4-1-record.md` and `wp9-4-2-record.md`, keeping the original counts.
- **A record,** `docs/plans/agentic-research-system/transition/w9/wp9-5-record.md` (new), in the form of
  `wp9-4-2-record.md`.

## 4. The boundary and the hard rules

**Allowed edits** (P-090's Boundary and item 6):
- the new `tools/` files and the workflow above;
- `research_system/legacy/evidence.py`, `acceptance.py`, `preparers.py` and `accepted_w9.py`, **only** as amendments
  §1 specifies;
- tests under `tests/tools/` and `tests/research_system/` that these changes need, including the WP9.3 and WP9.4 test
  files and builders amendments §1 names;
- `.github/workflows/ci.yml` (the `admission-controls` wiring), `.github/CODEOWNERS` and
  `tests/tools/test_ci_platform_policy.py`, as amendments §3 and note §16.1 and §16.7 say;
- `CONVENTIONS.md`, only the text amendments §3 gives;
- `docs/plans/agentic-research-system/design/09-migration-compatibility-and-pilot.md`, only §4.2 item 1 (d), from
  amendments §2;
- `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md`, only the rows and header
  cells amendments §4 names;
- `wp9-4-1-record.md` and `wp9-4-2-record.md`, appended re-records only;
- `wp9-5-record.md` (new);
- `tools/research_system_durations.json`, for the shard weights of new test files.

**Must not change:**
- anything note §2.2 lists as protected: the 275-row census, the 06h manifest and its smoke test, `schema_registry.py`,
  `authority.py`, the core and W9 schemas, the T2 seal, `tools/w9_segmentation.py` and `IMPORTER_MODULES`. No D-4 is
  expected. If one would move, stop;
- any file under `.research-system/`. **Do not create any evidence file**, including `walk-baseline.json`,
  `registration-manifest.json` and `detector-controls.json`. They are created at L-1, and the tripwire requires them
  absent. Tests use fixtures under `tmp_path`;
- the design note, the amendments document and the decisions register. If the spec looks wrong, report it; do not fix
  it;
- `research_system/` outside the four files above.

**Never:**
- write to any real ARS store, create one, run genesis on one, or issue a grant on one. Every store in every test is a
  scratch store under pytest's `tmp_path`, and every repository a scratch Git repository under `tmp_path`;
- read a vault file, a paper file or restricted bytes from a test. Use a synthetic vault under `tmp_path`;
- write under `papers/`, `results/`, `.apm/` state files, the Obsidian vault, or any legacy file;
- run the detector workflow, open a throwaway PR, or call `gh api` beyond read-only GETs you need to check behaviour.
  No test may call GitHub;
- compose files with heredocs or `python -c`. Use the editor tools;
- commit on `main`, push, open a pull request, or merge. Commit on your branch only. This PR edits `ci.yml`,
  CODEOWNERS and I1 paths, so Stephen merges it himself.

## 5. How to build it

Suggested order: each step's tests are green before the next.
1. **Amendments §1, the WP9.3 gates.** A1, D3 (with the chain rule, and links never followed through the all-zero id),
   E1 (with `now` passed into `check_environment`, and the inert test before any read) and J1 (a separate
   `require_cl_classified_list`). Then the existing W9 suites, the WP9.4 re-runs and the re-records.
2. **`tools/_w9_detector_evidence.py`:** the loaders, the three exception classes (with the object-root check before
   `format`, note §6.6 item 1), and the closure walker.
3. **`tools/check_legacy_writes.py`:**
   - Rules 0 to 3, `acknowledged`, and `rule0_exemptions` per note §6.5.1, including the malformed-intermediate rule;
   - the exit-code classification (note §6.6);
   - `--verdict-json` in `w9-verdict/1`;
   - the PR mapping;
   - `--assemble-only`.
4. **The other detectors, the controls runner, the wrapper and the exporter** (note §5, §7, §8, §9).
5. **The workflow and its pin step** (note §10.2), with the pin step's confinement and post-write checks, and the
   `L1_LIVE` tripwire (§10.3).
6. **The tests** (note §12.1), including every control listed there.
7. **The wiring and text:** `ci.yml` `admission-controls`, CODEOWNERS and the policy tests, `CONVENTIONS.md`, W9 §4.2
   (d), and the addendum rows.
8. **The record.**

**Carried obligations.** Each of these is part of the job, and the record says how you met it:
- every item in note §15.3. That covers the r7 review's R7-m3 to R7-i7, the CodeRabbit items, X-m2 (b, c), X-i5,
  X-i7, and XR-m2 to XR-m5 and XR-i1 to XR-i5. XR-m1's remaining question is whether the raw-read rule covers Rules 0.1
  and 0.3: answer it in the record, and stop if the answer changes behaviour the note fixes;
- the r8 review's R8-m1, R8-m2, R8-i1, R8-i3 and R8-i5 (a), in `reviews/wp9-5-note-r8-review-2026-11-23.md`.
  R8-m1: every exit-1 site carries a `(rule, path)` pair or exits 2, with precedence stated and tested by enumerating
  the sites;
- the code-task items in the amendments document. These are A-m5 (c, d) for the A1 tests, A-m10 (b to d) for the
  addendum, and the shape test for populated `ACCEPTED_*` constants.

## 6. Verification and the record

1. **The test budget is G1:** at most 300 s, serial, `--no-cov`, including `@pytest.mark.slow`, for all new and changed
   WP9.5 test files, excluding full-history walks (note §12.3, P-090 item 2 G). One scratch-store test took 39.65 s on
   this machine (note §15.1), so allow about 34 s per scratch-store flow. Over budget is `PARTIAL`.
2. **Regression:** run `tests/research_system/` for the W9 files your changes touch, `tests/tools/`, and
   `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py`. Record counts and wall time.
3. **Mutation check:** for each new guard, remove it in memory and show its control fails (the repository's
   guard-removal convention). Record the count, and any guard that survives.
4. **D-4:** confirm every §2.2 identity is unchanged at your head (blob ids and the census digest). Record the table.
5. **Ruff and pre-commit** clean, with no `--no-verify`.
6. **The record** (`wp9-5-record.md`) states:
   - the base and head;
   - what was built, item by item against note §2.1 and amendments §1 to §4;
   - how each carried obligation was met;
   - the test counts and times;
   - the mutation table and the D-4 table;
   - every departure from the note, with a citation.

## 7. Stop rules

Stop and report `PARTIAL` (do not work around it) when any of these holds. They come from note §15.2, P-090 and the
amendments:
- an edit would alter a §2.2 protected identity;
- a change under `research_system/legacy/` goes beyond amendments §1;
- a test would read a live vault, a paper or restricted bytes, or would write the real repository, any worktree or the
  vault;
- the new and changed tests exceed G1's 300 s;
- a 1x full walk with real rules and PR mapping exceeds 600 s in a smoke run (note §15.2 item 5);
- a negative control does not fire, a positive control fires, or a closure, stdlib or wrapper test fails;
- the note, the amendments and the code contradict each other in a way that changes behaviour, or the spec is silent
  on something a guard needs. Report the exact conflict with both citations, and do not choose for Stephen;
- a guard cannot be tested without a real store, a real vault or a GitHub call.

Missing code, tests or helpers are not stops. Build them; they are the job.

## 8. What to hand back

When you finish or stop, reply with:
1. **Status** first: `COMPLETE` (every note §2.1 deliverable, amendments §1 to §4 and carried obligation built and
   tested, the regression run, and the budget met) or `PARTIAL - <exact gap>`.
2. The branch, its head commit, the base commit, and `git log --oneline <base>..HEAD`.
3. What was built, item by item, each with its tests.
4. The test counts and wall time per file, the regression counts, and the mutation count.
5. The D-4 table.
6. Every departure from the note or the amendments, and every place you were unsure of the spec, with citations.
7. Anything you saw outside your scope that looked wrong. Report it; do not fix it.

Do not describe the work as reviewed, accepted or ready to merge. It gets an independent review, then CodeRabbit, then
Stephen's merge.
