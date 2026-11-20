# Handover: build WP9.4-1 (W9 adoption and discharge) in the TDL repository

You are implementing one code package, WP9.4-1, in Stephen's TDL repository on his Windows machine. Its design is
settled and accepted. Your job is to build it exactly as specified, with tests, and hand back a branch for review.
Nothing you produce is merged without a separate review, so report honestly. A partial result with exact gaps is worth
more than a claim of completeness.

## 1. Where you work

| Item | Value |
|---|---|
| Repository | `C:\Users\steph\TDL` (GitHub `ZK-Theory/TDL`); base branch `main` |
| Your branch | `pipe/w9-wp9-4-1-adoption-discharge`, already created at the base commit and not checked out anywhere |
| Your worktree | Your own linked worktree on that branch. If your runtime has not made one, create it from `C:\Users\steph\TDL` with `git worktree add .apm/worktrees/wp9-4-1 pipe/w9-wp9-4-1-adoption-discharge`. Do not create a different branch |
| Base commit | `3b1a0e3f` on `main`, the squash merge of PR #437. Its tree equals the design note's final head `28ec7134`. The squash title says "revision 1"; ignore that, the note on `main` is revision 8 |
| Platform | Windows 11, PowerShell 5.1 and Git Bash, Python 3.13 managed by `uv` |
| `.env` | Gitignored, so a new worktree lacks it. Immediately after creating the worktree, copy it: `Copy-Item "C:\Users\steph\TDL\.env" "<your worktree>\.env"`. Without it, `uv run --env-file .env ...` fails silently |

If your runtime starts the worktree at a detached HEAD on `3b1a0e3f`, run `git switch
pipe/w9-wp9-4-1-adoption-discharge` once (both resolve to the same commit). Before any write, verify in the worktree:
the current directory, `git branch --show-current` is `pipe/w9-wp9-4-1-adoption-discharge`, `git merge-base --is-ancestor 3b1a0e3f HEAD` exits 0, and `git status --short`
shows nothing you did not make. Work only in this worktree. Apart from that one `git worktree add`, never touch the
main checkout at `C:\Users\steph\TDL` or
any other worktree under `.apm\worktrees\` or `.claude\worktrees\`.

If `uv sync` fails with "Failed to update Windows PE resources ... Access is denied" in `%TEMP%`, set `TEMP` and `TMP`
to `C:\t\uvtmp` for that command.

## 2. Read these first, in this order

All paths are relative to the worktree root.

1. `CLAUDE.md`, `.claude/CLAUDE.md` and `AGENTS.md`: the project's rules. Some of their tool advice names
   Claude-specific tools; follow the substance (read before editing, search with a content search, never skip hooks).
   `.claude/rules/python.md` gives the code conventions.
2. `CONVENTIONS.md`: locked project decisions.
3. **The specification:** `docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md` (revision 8). Read
   all of it once. §1 to §9, §13 to §16 and §18 are your spec. §10 to §12 are WP9.4-2's (not yours). §20 to §26 are
   change logs: read them for why a rule is shaped as it is, not as requirements.
4. **The decisions that govern the note:** `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`,
   entries P-085 (search `### P-085`) and P-086 (`### P-086`). P-086 records Stephen's answer to each owner point
   A to O, all at the note's recommended option. Where §19 of the note and P-086 differ, P-086 governs.
5. **The pattern to follow:** WP9.3, the previous package, built the same five-step authority flow you are extending.
   - `transition/w9/wp9-3-design-note.md`: its design;
   - `transition/w9/wp9-3-1-record.md`, `wp9-3-1b-record.md` and `wp9-3-2-record.md`: what each code PR shipped, how it
     was verified, and how its record reads. Your PR needs a record of the same shape (§6 below);
   - `transition/w9/wp9-1-stage-b-design-note.md`: the stage B command set and the five-step flow;
   - `transition/w9/wp9-1-catalogue-owner-annex.yaml`: the owner annex, row by row (LR-023 to LR-034 are yours).
6. **The plan and its paths:** `docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md` (WP9.4,
   §2.7, §2.8, §8) and `implementation/06v-addendum-2026-11-10-w9-paths.md` (the W9 evidence area; the open-item list
   row is yours to complete, §5 below).
7. **The code you extend:** `research_system/legacy/`, especially `routes.py`, `commands.py`, `preparers.py`,
   `records.py`, `runtime.py`, `evidence.py`, `acceptance.py`, `accepted_w9.py`, `replay/reducers.py` and
   `replay/driver.py`; plus `research_system/schema_registry.py` (read only, see §4) and `research_system/cli.py`.
   The schemas are under `.research-system/schemas/contracts/w9/` (read only).
8. **The tests you extend:** `tests/research_system/integration/test_w9_*.py`, `w9_flows.py`, `w9_runtime_harness.py`,
   `tests/research_system/unit/test_w9_*.py` and `tests/research_system/contracts/test_w9_*.py`.

Two repository skill files are useful as plain method documents: `.agents/skills/contract-first-tdd/SKILL.md` (write
the failing test and its negative control before the code) and `.agents/skills/research-assurance-triage/SKILL.md`.

## 3. What WP9.4-1 is

The note's §2.4 and P-086 item 1 define it. WP9.4-1 is **adoption and discharge**:

| Rows | Record | Note sections |
|---|---|---|
| LR-023, LR-026 to LR-029 | `legacy-adoption-decision` | §5, §6 |
| LR-024, LR-025 | the reviewer-eligibility Decision (moved here by owner point B) | §2.2, §5.5 |
| LR-030 to LR-034 | `legacy-discharge-relation` | §8 |

It also carries:
- **the suspension projection** `P:legacy-adoption-status` (§7);
- **the legacy read interface** that later packages' guards call: `family_admissible`, `resolve_adoption_ref`,
  `legacy_content_matches` and the import allowlist (§9, §4.2 items 1 to 3, §4.3);
- **the WP9.3 authority-flow changes** these rows need (§5.1 to §5.6): the extended tables, the derived adoption
  review ID behind `review_id_for` (§5.2, owner point C), the analyst rule (§5.3), fixture refs in the resolving
  Decision (§5.4, owner point L), the eligibility Decision's encoding (§5.5, owner point B) and G4 grant subjects for
  LR-023, LR-024 and LR-030 (§5.6, owner point N);
- **the route-table change:** retag LR-024 and LR-025 from `WP9.7` to `WP9.4` in `research_system/legacy/routes.py`
  (today at line 449), and update the routed and deferred counts the contract tests pin;
- **one read-only CLI verb:** `ars legacy adoption-status <adoption id>` (§13). The other verb in §13,
  `cited-families`, is WP9.4-2's;
- **the open-item list reader** (§8, owner point H): the constant and reader for
  `.research-system/evidence/w9/legacy-open-items.json`, format `w9-legacy-open-items/1`, read at the binding's
  `git_head` from Git, never from the working tree. The file itself does not exist and you must not create it; tests
  use fixture files under `tmp_path`.

**Not yours (WP9.4-2, a later PR):** LR-035, LR-039 to LR-055, the citation extractor (§11), the paper root and its
member files (§10, owner points K and O), the reference graph (§12), the `cited-families` verb, any change to
LR-003's registration checks (the collision and case-folding work in §10.2), and every D-4 change. **Not yours
(WP9.7):** the CreateTask and AmendTask guard (owner point J), the content rule at use and at promotion (owner
point E), LR-021 and LR-022.

## 4. The boundary and the hard rules

**Allowed edits** (P-085's Boundary, extended by P-086 item 13):
- `research_system/legacy/**`;
- `research_system/cli.py`, for the one read-only verb only;
- tests under `tests/research_system/`;
- `tools/research_system_durations.json`, for shard weights of new test files (WP9.3-2 had to add them; see its
  record §7);
- `docs/plans/agentic-research-system/transition/w9/wp9-4-1-record.md` (new, §6);
- the open-item list row of `implementation/06v-addendum-2026-11-10-w9-paths.md`, to re-cite it with your constant and
  its line, as that file's 2026-11-20 amendment asks.

**Must not change** (WP9.4-1 carries no D-4; note §14):
- `research_system/schema_registry.py`, `research_system/authority.py`, and anything under `.research-system/`
  (schemas, contracts, evidence files);
- `research_system/store/`, `command/`, `discovery/`, `projection/`;
- `tools/w9_segmentation.py`;
- `tests/research_system/unit/test_schema_registry.py` and `tests/research_system/smoke/`.
The runtime-binding census must stay 273 rows (digest `0cca0414…4712`), the 06h manifest blob `4c895042` and the 06h
smoke test blob `559d684a`. If you find you need a binding row, a schema change, or an edit outside the allowed list,
**stop** (§7).

**Never:**
- write to any real ARS store, or create one, run genesis or issue a grant. Every store in every test is a scratch
  store under pytest's `tmp_path`. Never touch `C:/Users/steph/TDL-ARS-G6-Control`;
- write under `papers/`, `results/`, `.apm/` state files, the Obsidian vault, or any legacy file;
- read a real paper file, a vault file or restricted bytes from a test;
- edit the design note, the decisions register, `CONVENTIONS.md`, `CLAUDE.md` or `AGENTS.md`. If the spec looks wrong,
  report it; do not fix it;
- commit on `main`, push, open a pull request, or merge. Commit on your branch only. Stephen reviews the branch locally
  first.

## 5. How to build it

1. **Plan against the rows.** For each of LR-023 to LR-034, list what the annex row requires, what the note adds
   (§6.5 has the checks by row; §8 for discharge), which site enforces it (preparer, replay, or both), and the test
   that proves it. The note's §15 gives the required tests; every row marked `1` or `both` is yours. Keep this
   mapping; it becomes the record's table.
2. **Test first.** For each check, write the failing test and a negative control that shows the test can fail, then
   the code. A test must assert the refusal's own message, not just "an error", so a different refusal cannot satisfy
   it. Replay checks get forged-ledger tests; preparer checks get scratch-store integration tests through `submit`, as
   `test_w9_wp9_3_2_runtime.py` does. Every refusal must leave the ledger and the control root byte-identical.
3. **Reuse WP9.3's machinery** rather than building a parallel path. §5.1 says which tables to extend.
4. **The real positive path first.** Before widening the negatives, get one adoption through all five steps (LR-023,
   LR-026 to LR-029) on a scratch store, including LR-024 and LR-025's eligibility Decision, and one discharge through
   LR-030 to LR-034. Then the suspension projection over that adoption (W9-T9's three re-observation cases).
5. **Mutation check, before you report.** As WP9.3's PRs did, write a scratch script (not committed) that removes or
   inverts each guard you added, one at a time, runs the tests, and restores the file byte for byte. Every guard must
   be caught by a failing test that asserts its own message. Report the count caught out of the count tried, and the
   ones missed with what you added to catch them.

**Code conventions:** Python 3.13; 120-character lines; ruff rules E, F, I, W; type hints on public functions;
Google-style docstrings; imports ordered standard, third-party, local. Format only the files you changed
(`uv run ruff format <files>`), never a directory.

## 6. Verification and the record

**Commits.**
- Subject `[PIPELINE] P06: WP9.4-1: <what>`, then a body.
- End every message with the line `Co-Authored-By: <your model name> <noreply@google.com>`, so the
  history shows which model wrote it.
- Write each message to a file outside the repository and commit with `git commit -F <file>`. Never pass it in a
  shell here-string. Write the file as UTF-8 **without a BOM**: in PowerShell 5.1 use
  `[IO.File]::WriteAllText(<path>, <text>, (New-Object Text.UTF8Encoding $false))`. A BOM breaks the commit-message hook.
- **Never use `--no-verify`.** The pre-commit hook runs ruff, a CRLF check, and the math-correctness contract gate over
  104 contracts, so a commit can take minutes.
- Do not pipe `git commit` into another command; redirect its output to a file, then check `git log -1` to confirm
  HEAD moved.
- If a hook fails, fix the cause.

**Tests.** Run the files you add or change as you go:
`uv run --env-file .env python -m pytest <files> -q -p no:cacheprovider`.
The full W9 regression is long: WP9.3-2's 52-file run took 71 minutes. Run it once, at your final head, in the
background with its output going to a file, rather than in a foreground call that may time out. The regression set:
- every `tests/research_system/**/test_w9_*.py` file;
- `tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py`;
- `tests/research_system/unit/test_schema_registry.py`;
- `tests/research_system/integration/test_command_cli.py` and any test that drives `ars legacy` through the CLI. Find
  them with a content search for `"legacy"` in `tests/research_system/`;
- the files WP9.3-2's record §7 lists for its regression, so your run compares with its 71 minutes.
Report the pass, fail and skip counts and the wall time. The test-runtime escalation is an open item with Stephen, so
report how much time your new files add.

**D-4 identities.** Show that `git diff --stat 3b1a0e3f HEAD` touches none of the must-not-change paths in §4, and that
the 06h smoke test and the census tests pass unchanged.

**The record.** Write `docs/plans/agentic-research-system/transition/w9/wp9-4-1-record.md` in the shape of
`wp9-3-2-record.md`:
- the header: date, status, package, authority (P-085, P-086, the note at revision 8), base, boundary, and not
  authorized;
- what it routes, row by row;
- the changes to WP9.3's flow (§5);
- "No D-4", with the evidence;
- a tests table with case counts;
- verification: the regression, the mutation result, and the runtime;
- every departure from the note, each with its reason. A departure that is not listed is a defect.

Plain, direct English. Cite `path:line` for every code claim.

## 7. Stop rules

Stop and report **Partial** (do not work around it) when (note §18 and 06v §8):
- WP9.4-1 needs a runtime-binding row, a schema change or any `.research-system/` change;
- a row needs an edit outside §4's allowed list;
- a test needs a real paper file, a vault file or restricted bytes;
- the note and the code contradict each other in a way that changes a row's behaviour, or the note is silent on
  something a row needs. Report the exact conflict with both citations; do not choose for Stephen;
- a guard cannot be tested without a real store.

Missing code, reducers, preparers, projections or tests are not stops. Build them; they are the job.

## 8. What to hand back

When you finish or stop, reply with:
1. **Status** first: `COMPLETE` (every WP9.4-1 row built and tested, regression run) or `PARTIAL - <exact gap>`.
2. The branch and its head commit, and `git log --oneline 3b1a0e3f..HEAD`.
3. Rows built, by row, each with its tests.
4. Regression counts and wall time; the mutation count; the runtime your new files add.
5. The D-4 evidence.
6. Every departure from the note, and every place you were unsure of the spec, with citations.
7. Anything you saw outside your scope that looked wrong. Report it; do not fix it.

Do not describe the work as reviewed, accepted or ready to merge. It gets an independent review, then CodeRabbit,
then Stephen's merge.
