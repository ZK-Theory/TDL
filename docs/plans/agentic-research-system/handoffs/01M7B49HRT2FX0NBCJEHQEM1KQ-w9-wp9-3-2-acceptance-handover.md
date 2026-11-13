# TDL Handoff: W9 transition, WP9.3-2 acceptance and WP9.3 close-out (P06)

Capability status: INCOMPLETE. WP9.3's code is merged to `main` (WP9.3-2 as `baea2c13`, PR #432), but it is not
accepted. The gap: P-084 is not written, the WP9.3-2 independent review is committed only on a local, unpushed
branch, and the review's one follow-up fix (m-5, PR #434) is open and unmerged.

Written 2026-11-13 by the parent session that dispatched and coordinated WP9.3-1, WP9.3-1b and WP9.3-2 and their
reviews. Every claim below was re-derived at the time of writing against `origin/main` at `a6a98966`, the branches
named, and GitHub. Nothing was carried over from an older status table.

## Purpose of next session

Take over as the coordinating session for WP9.3's close-out. In order:

1. **PR #434 (m-5).** See it through Stephen's review and merge. Don't merge it yourself.
2. **P-084.** After Stephen accepts, write the register entry that accepts WP9.3-2 and records WP9.3 as complete. Commit
   the independent review with it, as P-083 did for WP9.3-1b. Then open a docs PR.
3. **The vault entry** for P-084.

Hard stop: continue WP9.3's acceptance only. Do **not** start WP9.4 to WP9.7 or any live operation (see the do-not-do
list), even after P-084 merges. Those need their own dispatch from Stephen.

## Active paper / project

P06, the agentic research system (ARS). This is the W9 transition, work package WP9.3 (closed-reference acceptance,
LR-003 to LR-020). Register: `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`, last entry P-083
(line 5404 at `a6a98966`). The governing decisions are P-080, P-081 (with its amendments), P-082 and P-083.

## Named end-to-end capability

WP9.3: every W9 legacy-route row LR-003 to LR-020 is routed and checked, from its replay and preparer checks through
Stephen's acceptance in the register. That acceptance is the precondition for the later WP9.4+ packages and the
L-0 to L-5 live operations. All of those remain unauthorized.

## Capability state

PROVEN, not yet INTEGRATED. Code is on `main`, and the independent review at the merged tree says **accept**. The
owner's acceptance (P-084) and the m-5 merge are outstanding.

## Completed production path

- WP9.3-1: PR #420. Accepted in P-082.
- WP9.3-1b: `6aeb3b31` (#428) and `fbb99ce0` (#429). Accepted in P-083 (#430).
- WP9.3-2: PR #432, merged 2026-11-12 03:13 UTC as `baea2c13a4a28f30cf38f2a5c51fdd6a063db510`, from head
  `bc47fea828908522abb118bd27ee7ec250af8627`. The merge tree equals the head (`git diff --quiet bc47fea8 baea2c13`).
  Record: `docs/plans/agentic-research-system/transition/w9/wp9-3-2-record.md`, whose §10 tables every CodeRabbit and
  review finding with its fix and control.

## Exact remaining functional gap

1. **PR #434 is open.** "[PIPELINE] P06: the CommandService census no longer lets a class body enclose its methods
   (WP9.3-2 review m-5)", branch `pipe/w9-census-class-scope`, head `d8cb0514456383e0c706485610388edbea9c7860`.
   - It changes one file: `tests/research_system/contracts/test_w9_wp9_3_censuses.py` (+206/-3). No production code.
   - First commit `92e55475`: the m-5 fix (a class body no longer encloses its methods).
   - Second commit `d8cb0514`: CodeRabbit's one thread, which the WP9.3-2 reviewer fixed. Definition-time expressions
     (decorators, defaults, annotations, class bases) take the scope around the statement, and comprehensions are
     their own scopes. There are 11 new fixtures, each checked against Python itself, and 9 of them fail against
     `92e55475`'s census.
   - The thread is replied to and resolved.
   - CI at `d8cb0514`: all suite shards, `suite-verdict` and `windows-store-lock` passed. `merge-admission` was
     **cancelled**, not failed. It was cancelled the same way on #429. Re-run it if Stephen wants it green.
2. **P-084 is not written.**
3. **The WP9.3-2 independent review is not on `main`, or on any remote.** It exists only on local branch
   `review/w9-wp9-3-2`.

## Next production action

Ask Stephen whether to merge PR #434. Merging is his. Once he has, or says to proceed without it, draft P-084 for his
acceptance (see "Decisions to record in P-084").

## Current state

### The independent review (review/w9-wp9-3-2)

- **Worktree:** `C:/Users/steph/TDL/.claude/worktrees/w9-wp9-3-2-8a7ce5`, on branch `review/w9-wp9-3-2`, HEAD
  `667d8df0`. **Not pushed:** `git ls-remote --heads origin review/w9-wp9-3-2` is empty. Check `git status` there
  before you use it. The session left it after committing, but that wasn't re-checked here.
- **Report:** `docs/plans/agentic-research-system/reviews/wp9-3-2-review-b98515c6-2026-11-11.md`, on that branch.
  - **First round at `b98515c6`:** accept with required changes. 0 Blocking, 0 Major, 4 Minor (m-1 to m-4), 8 Info
    (i-1 to i-8), no D-4. 1,698 tests passed.
  - **Addendum at the merged tree `bc47fea8` (= `baea2c13`):** accept. 0 Blocking, 0 Major, 1 Minor (m-5, now PR
    #434) and 2 Info (i-9, i-10). m-1 to m-4 and i-1 are closed. The re-check probes give 45 passed. The W9 and CLI
    regression gave 1,276 passed, 0 failed.
- **Probes:** `docs/plans/agentic-research-system/reviews/wp9-3-2-review-artifacts/`. The two first-round files are
  kept as evidence of the defects at `b98515c6`, and the re-check probe file asserts their inverses.
- **Commits on the branch** (rebased onto `bc47fea8`):

  | Commit | Content |
  |---|---|
  | `61faaa7d` | The first-round probes |
  | `f4e79301` | The first-round report |
  | `86f19a01`, `5265a8d9`, `45aa3ecf` | WIP commits kept across usage limits |
  | `667d8df0` | The final addendum |

  Bring the report and its artifacts to `main` as files, as P-083 did. Don't merge the branch: its base and WIP
  history aren't wanted on `main`. Check the files' content against `667d8df0` before committing.

### Sessions (all idle, each linked from the parent)

| Session | Role |
|---|---|
| `local_b227bbb8-2e77-4c1d-8133-d4bec392cef3` | WP9.3-2 implementer, PR #432. Its worktree is now on `docs/worktree-sweep-2026-11-12` (#433, merged) |
| `local_84ec517d-2bd0-46c0-9f3b-343718c5b77a` | WP9.3-2 independent reviewer. It also reviewed #434 and pushed `d8cb0514` |
| `local_4652eed2-e247-4b1e-87e3-255df1e3f2fa` | Wrote #434's first commit `92e55475`. Worktree `C:/Users/steph/TDL/.claude/worktrees/silly-einstein-d9f409`, branch `pipe/w9-census-class-scope`, local HEAD still `92e55475` (behind the PR head) |

### Vault

`C:/Users/steph/Documents/TDA-Research/04-Methods/Computational-Log.md`. Its top entry is "2026-11-12 -- P06:
WP9.3-2 merged after three CodeRabbit passes ..." `[PIPELINE]`, written by the implementer. There is no `[DECISION]`
entry for WP9.3-2's acceptance yet.

## Workflow system

Standalone (not APM). This handoff lives in the project's `handoffs/` directory. Branches are `pipe/`, `review/` and
`docs/`. Stephen controls dispatch, CodeRabbit, merges, every live store and provider operation, and every acceptance.

## Packet predecessor

None for this handoff. The relevant gate handoff is
`docs/plans/agentic-research-system/handoffs/01M5G6WDA43PAEMZCNG3A8S4R0-gate7-prep-handoff.md`. It is not re-checked
here and isn't needed for this close-out.

## Files and artifacts

- Design note: `docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md` (revision 14).
- Records: `transition/w9/wp9-3-1-record.md`, `wp9-3-1b-record.md`, `wp9-3-2-record.md`.
- Earlier reviews on `main`: `reviews/wp9-3-1-review-23f8f737-2026-11-10.md` and
  `reviews/wp9-3-1b-review-649d0698-2026-11-10.md`, each with its `-artifacts/` directory.
- Intake list: `docs/plans/agentic-research-system/implementation/gate7-intake-deferrals.md`, rows 36 and 37.
- Paths addendum: `implementation/06v-addendum-2026-11-10-w9-paths.md`, row 28 (dated amendment citing
  `w9-cl-export/1`, Q3).
- The P-083 PR body and commit message used as models:
  `C:/Users/steph/AppData/Local/Temp/claude/e088a017a981a492/b9665fc0-0c00-46e3-9093-d7ac18be8a78/scratchpad/pr-body-p083.md`
  and `.../commit-msg-p083.txt`. These are in the parent's scratchpad and may not survive.

## Commands run (re-runnable)

```
gh pr view 432 --json state,headRefOid,mergeCommit,mergedAt
git diff --quiet bc47fea8 baea2c13            # merge tree == head
gh pr checks 434
gh run view 43338626471 --json jobs           # merge-admission: cancelled
git ls-remote --heads origin review/w9-wp9-3-2   # empty: not pushed
git log --format='%h %s' -8 review/w9-wp9-3-2
```

## Contracts and validation

- **D-4 identities**, unchanged at `baea2c13` per the review addendum. Re-check them before P-084 cites them:
  - runtime-binding census: 273 rows, `0cca0414641bf4fbed32b5f42d7c3753a8c47dcdd09d815dcba0658ef8814712`;
  - 06h manifest: blob `4c8950421d3a9f25da7cf4b657a358536df42332`;
  - 06h smoke test: blob `559d684a5d78abc285ce9b50dd23ce071aad32c5`;
  - `tools/w9_segmentation.py`: blob `43e1454de09b61e274954c42b21d6ae533857a24`.
- **Genesis** (P-081 item 6, for the L-3 checklist): the addendum names itself as the review that verified the genesis
  path on the merged tree. Guard 8 holds 19 routed rows (LR-001, LR-003 to LR-020) and 42 deferred. A real W9 genesis
  on a scratch store replays.
- **#434 changes only a test file.** It doesn't touch any D-4 identity, but confirm the census still gives 273 rows
  after it merges.

## Results and provenance

No numerical results. The evidence is code, tests, probes and the review report. Nothing goes under `results/`.

## Decisions to record in P-084 (Stephen's acceptance first)

Each item comes from the review report: §9, §13 and addendum A.7. Read the report rather than this list when you draft.

- **WP9.3-2 accepted** as merged at `baea2c13` (#432, head `bc47fea8`). The review was at `b98515c6`, with its
  addendum at the merged tree. There is no D-4.
- **Readings:** R1, R3, R4, R5, R7, R8, R10, R11 (i-1's set comparison), R12 (the evidence area) and i-3 (a conditional
  `pilot_promotion` fixture counts as applicable when listed and not applicable when absent).
- **R2:** a computed class name escapes the census. Record it as a known limit beside note §18.
- **Stephen's answers to the WP9.3-2 plan, 2026-11-11, "Yes, as recommended":**
  - Q1: batch mode prints the fixed parts, and `ars legacy show` the full list;
  - Q2: refuse a fixture outside LR-020's seven;
  - Q3: the paths addendum row 28 amendment. Q3 and row 27 are departures from the addendum.
- **The later-pin checklist line** (P-083 item 5): the review supports dropping it now that n-1's hardening has merged.
  **Stephen's call. Ask him.**
- **Intake rows 36 and 37 (i-5, i-10):** restate their "done" against `baea2c13`, not the branch name.
- **Genesis:** the addendum is the L-3 genesis verification for the merged tree. If #434 merges, it changes only a
  test, so the production tree that genesis covers is unchanged.
- **Checklist carries:**
  - L-0b (i-2): confirm the export's region is the legacy region;
  - L-4 (i-4): S-014's freshness at LR-020, the post-batch re-run, and §10.1's owner facts.
- **i-9:** Git replace refs could change what the anchor check sees, but only through deliberate tampering. A later
  hardening could pass `--no-replace-objects`. Record it, with no change asked.
- **m-5:** a follow-up as PR #434. Record its merge, or that it is still open.
- **T2 CI failure at `4636bc4c`:** consistent with the known `WriterLock` flake. It did not reproduce in 900 local
  repeats. The flake stays with the `WriterLock` follow-up, outside WP9.3.
- **P-081 item 3** probably needs its tenth amendment pointing at P-084, and its item 1 or 10 may also be touched.
  Check what P-083 amended and follow the same pattern.
- **Mark the WP9.3-2 record** merged and accepted. Add a "WP9.3 complete" statement covering LR-003 to LR-020.

## Open risks

- **Independence of #434's second commit.** `d8cb0514` was written by the WP9.3-2 independent reviewer, not reviewed
  by an independent session. Only CodeRabbit has looked at it. It is test-only. Tell Stephen, and let him decide
  whether a short independent look is needed before he merges.
- **The review exists only on a local branch.** If that worktree is swept before P-084 copies the files, the review is
  lost. Don't sweep `w9-wp9-3-2-8a7ce5` until P-084 has merged.
- **The main checkout is behind.** `C:/Users/steph/TDL` is on `main` at `a16310cb`, behind `origin/main`, and its hook
  tree is pre-merge (the SessionStart hook-currency warning). Work in a worktree from `origin/main`, as this handoff
  did. Updating the main checkout is Stephen's call.
- **Test runtime growth.** The SPEC test-runtime escalation is still open with Stephen. WP9.3-2 added about 4.4 min.
  Don't normalise it (memory: escalate growing test runtimes).

## Owner-only items, outside this close-out, still open with Stephen

- The SPEC test-runtime escalation.
- The segmentation readings R-1 to R-8, six of them still open.
- The T2 `WriterLock` release flake follow-up.

## Suggested skills

`research-assurance-triage` (before accepting) · `commit-log` · `vault-sync` · `adversarial-design-review` (only if
Stephen asks for an independent look at `d8cb0514`).

## Branch / integration state

- Base: `origin/main` at `a6a98966`.
- This handoff: branch `docs/w9-wp9-3-handover`, worktree `C:/Users/steph/TDL/.claude/worktrees/w9-wp9-3-handover`,
  one file.
- PR #434: 1 changed path against `main`.
- P-084's PR will be docs only. Expect the register, the WP9.3-2 record, the intake file, and the review report with
  its artifacts. That is a handful of paths, well under CodeRabbit's 100-file cap.
- CodeRabbit must review before merge (memory: CodeRabbit must review before a PR merges). Read inline findings with
  `gh api repos/ZK-Theory/TDL/pulls/N/comments`.

## Do-not-do list

- Don't write to any ARS store, including `C:/Users/steph/TDL-ARS-G6-Control` and the named scratch stores. Only
  stores a test creates under `tmp_path` are allowed.
- Don't touch `papers/P01-A-JRSSA/`, `papers/P01-B-JRSSB/`, `.apm/` state, or the vault Discovery `_backlog.md`.
  WP9.3's `.apm/` inventory tools only read.
- Not authorized, even after P-084 merges: WP9.4 to WP9.7; the live operations L-0 to L-5, including the D-7 baseline
  export; real stores, genesis or grants on one; legacy writes. P-084 records an acceptance and opens none of these.
  Each needs Stephen's own dispatch.
- Don't merge any PR, accept anything, or decide the later-pin checklist line yourself. If a finding would change a
  register entry, a decision or an accepted text, bring it to Stephen first.
- Commits: messages start `[DECISION] P06:` or `[PIPELINE] P06:`. Write each one BOM-free with Write to a scratch file
  and commit with `git commit -F <file>`. End with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never
  `--no-verify`, and never amend a published commit.
- Never compose code or prose through heredocs or `python -c`.
- PR bodies: use `--body-file`, end with "🤖 Generated with [Claude Code](https://claude.com/claude-code)", and verify
  the published body byte for byte.
- A merged PR's head SHA, not its branch tip, is what landed. Check `gh api repos/ZK-Theory/TDL/pulls/N --jq .head.sha`.
- Don't sweep the review worktree, or the #434 worktree, before their content has merged.
- Don't write anything under `results/`.

## Sensitive information redacted

None present: no UKDA data, credentials or tokens.
