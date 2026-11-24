# Handover: write the WP9.5 design note (the W9 detectors) in the TDL repository

For: a Gemini agent, writing revision 1 of one design note. Written by the Claude session that reviewed WP9.4-2, on
2026-11-21, under P-089.

You are writing a **design note**, not code. WP9.5 is the package that builds the W9 detectors: the checks that
notice when something writes a registered legacy file, `results/` outside `results/ars/`, a locked part of
`CONVENTIONS.md`, or a legacy entry in the vault's Computational-Log. Your note says exactly how each one works, what
it reads and writes, how it is tested, and what Stephen must decide before any code. The code comes later, after the
note is reviewed and Stephen has decided its owner points.

Nothing you produce is merged without review. An independent reviewer, a fresh session with none of your context,
will attack the note, and you will revise it. Report honestly: a note that names its open questions is worth more
than one that hides them.

## 1. Where you work

| Item | Value |
|---|---|
| Repository | `C:\Users\steph\TDL` (GitHub `ZK-Theory/TDL`); base branch `main` |
| Your branch | `docs/w9-wp9-5-design-note`, which you create (below) |
| Your worktree | `C:\Users\steph\TDL\.apm\worktrees\wp9-5-note` |
| Base commit | `origin/main` once it holds register entry P-089. Record the exact commit in the note's header |
| Your file | `docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md` (new). It is the only file you write |
| Platform | Windows 11, PowerShell 5.1 and Git Bash, Python 3.13 managed by `uv` |

**Setup, once, from `C:\Users\steph\TDL`:**
1. Run `git fetch origin`.
2. Check the base: `git grep -q "### P-089" origin/main -- docs/plans/agentic-research-system/03-decisions-and-open-questions.md`
   exits 0. If it does not, stop and report: P-089 is not on `main` yet.
3. Run `git worktree add -b docs/w9-wp9-5-design-note .apm/worktrees/wp9-5-note origin/main`.
4. Run `Copy-Item "C:\Users\steph\TDL\.env" "C:\Users\steph\TDL\.apm\worktrees\wp9-5-note\.env"`.
5. In the worktree, run `uv sync --extra dev`. If it fails with "Failed to update Windows PE resources ... Access is
   denied" in `%TEMP%`, set `TEMP` and `TMP` to `C:\t\uvtmp` for that command.

**Before any write,** confirm the current directory, that `git branch --show-current` is
`docs/w9-wp9-5-design-note`, and that `git status --short` shows nothing you did not make. Never touch the main
checkout or any other worktree.

## 2. Read these first, in this order

Paths are relative to the worktree root. Every claim you make about code, a workflow or a document cites `path:line`
at your base commit, **read by you**, not taken from this handover. This handover's line numbers are leads only.

1. **The project's rules:** `CLAUDE.md`, `.claude/CLAUDE.md`, `AGENTS.md` and `CONVENTIONS.md`. Two of their rules
   bind the note hard: "No speculative paths" and "verify before relying on an inferred property". Some tool advice
   names Claude tools; follow the substance.
2. **Your authority:** `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`, entry **P-089** (all
   of it). Read P-085 to P-088 for how earlier packages were authorized, built and accepted, and P-064 for the plan's
   D-1 to D-9.
3. **The plan:** `docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md`:
   - §2.4 (existing detection tooling, and what does not exist);
   - §2.8 rows U-3 and U-4;
   - §3 rows O-9 to O-13 and O-32;
   - §4 rows W9-T7 and W9-T19;
   - §5 "WP9.5 — Detectors (W9-D5)" (your scope), and the package rules at the top of §5;
   - §6 D-5, D-7 and D-8;
   - §7: L-0b, L-1 and the batch checklist;
   - §8 stop rules.
4. **The specification:** `docs/plans/agentic-research-system/design/09-migration-compatibility-and-pilot.md` (W9):
   - §4 whole (§4.1 the writers seen, §4.2 the writer rule, §4.3 shared enforcement surfaces, §4.4 the detectors and
     their negative controls, §4.5 what each action needs first);
   - §5.5 (item selectors: the granularity the `CONVENTIONS.md` check uses);
   - §7.3 (the shared-writer exception: what is legacy in the Computational-Log and `CONVENTIONS.md`);
   - §16.1 rows W9-D5, W9-D9, W9-D13 and W9-D14.
5. **The evidence-area formats WP9.3 already fixed,** which WP9.5 writes to:
   - `docs/plans/agentic-research-system/implementation/06v-addendum-2026-11-10-w9-paths.md` (the path table);
   - `research_system/legacy/evidence.py`: the constants (around `:36-64`, including `REQUIRED_DETECTOR_CONTROLS`),
     `require_registered`, `require_detector_controls`, `require_change_list` and `_change_entries`, and
     `require_cl_export`;
   - `docs/plans/agentic-research-system/transition/w9/w9-segmentation-contract-v1.md` and `tools/w9_segmentation.py`
     (how a Computational-Log entry and a `CONVENTIONS.md` lock are segmented and hashed).
6. **What the detectors build on:**
   - `tools/check_merge_admission.py`, in particular how a squash commit on `main` is mapped to its PR (06v §2.4 cites
     `:703-709`);
   - `tools/check_bypass_merges.py` (it already reads bypass use on `main` with the owner's `gh`);
   - `.github/workflows/` (every workflow, for triggers, permissions and the token each uses);
   - `.claude/hooks/admin-bypass-guard.sh` (it allows `gh api` GETs of rulesets and blocks mutations).
7. **Templates for a W9 design note:** `docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md` and
   `docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md`. Copy their
   shape: a header table, what the note settles, scope, carried obligations, interface findings with `path:line`,
   one section per mechanism, tests, research assurance, claims for review, stop rules, owner points, change log.

## 3. What the note must settle

Write one section per item below. For each mechanism say: what it reads, the exact rule, what it writes or reports,
how it fails (closed, and with what message), where it runs (CI, the operator machine, or a test), its negative
control, and its test.

1. **Scope and the package.** WP9.5 adds no command, so no D-4 is expected (P-089 item 1). Say whether any part
   changes a protected identity; if one would, say so and stop that part for an owner decision.
2. **The ruleset read** (detector `main_ruleset`, control kind `recorded_read`). What is read from ruleset 20822054
   and its rule-suites history, with which token, how the read is recorded, and when (06v §7 batch checklist: before
   every batch).
3. **U-3.** Whether the CI token can read the ruleset and rule-suites is unknown. Design the read-only probe: the
   workflow, its trigger, its `permissions:` block, the calls, and what it records. Do not run it (§4). If the probe
   could fail, give D-8's fallback exactly as P-064 accepted it. For context, already observed on 2026-11-21 with
   **Stephen's own `gh` login** (not the CI token): `gh api repos/ZK-Theory/TDL/rulesets/20822054` returns the
   ruleset, with bypass actor `RepositoryRole` 5 in `pull_request` mode, and
   `gh api "repos/ZK-Theory/TDL/rulesets/rule-suites"` returns entries such as `result: "bypass"` for pushes to
   `refs/heads/main`. Re-run those two GETs yourself and cite what you see.

   P-089 item 3 requires U-3 to be recorded **before any code**. So the note names the probe as an open gap with an
   owner and a step: it gives the exact steps to run it, says that Stephen authorizes the run and that the reviewing
   session runs it and records the result in the note, and makes "U-3 recorded" a precondition of the code package in
   its stop rules (item 16). The code is not dispatched until that result is in the note.
4. **The post-merge first-parent detector** (`tools/check_legacy_writes.py` and
   `.github/workflows/legacy-write-detector.yml`, 06v §5). Settle:
   - the recorded baseline commit it walks from, and why;
   - the three rules (06v §5 items 1 to 3), each exactly;
   - the §4.2 record: where it lives, its format, and how it is keyed **by PR number plus each registered file's old
     and new blob**, not by commit SHA;
   - how each first-parent commit is mapped to its PR. Note that `5df0c001`, one of W9-T7's two replay commits, is a
     **merge commit** (#215), not a squash, so say what the first-parent diff of a merge commit is and how the
     detector treats it. `811d5a2b` is a direct push;
   - how it reads rule-suites for bypass use, given U-3;
   - what it does with a registered legacy file it cannot read, and with a commit it cannot map.
5. **The registration manifest export** (M-6). Who writes `registration-manifest.json` in the WP9.3 format, when (each
   batch, before that batch's first observation), and the test that the manifest equals the store's registered set
   at the bound head. CI cannot read the store; say what the detector reads instead.
6. **The shared-surface rule** (O-32, the detector half). Rule 3: a merged change to a `shared_enforcement_surface`
   contract with no entry in `shared-surface-changes.json`, or no W9 §4.3 owner note, fails. Say how the detector
   knows which contracts are shared surfaces, and what the owner note is.
7. **The `CONVENTIONS.md` check** (`tools/check_conventions_legacy_locks.py`). The insertion-only rule against the
   legacy baseline at commit `4b143c92` (W9 §7.3 item 2). Settle the granularity (bullet or paragraph, per §5.5),
   which sections hold legacy locks, how a "pure insertion of successor bullets" is recognised, and the controls: a
   modified legacy bullet fires; an inserted successor bullet does not.
8. **The vault Computational-Log detector** (`tools/check_legacy_log_baseline.py`). It compares every live legacy
   entry with the accepted baseline export (format `w9-cl-export/1`, `require_cl_export`). **No export exists yet:**
   it is L-0b, which needs Stephen's authorization (06v D-7). So design and test the detector against a fixture
   export, and say exactly what changes when the real one is accepted. Also settle D-5: it runs before every batch
   and weekly on the operator machine, each run files an output hash in the evidence area, and a missed run blocks
   the next batch. Say how "a missed run blocks" is enforced, and by what.
9. **U-4.** The operator machine's path to the vault. Record what you can from a read-only check (§4 says exactly
   what you may do). P-089 item 3 also requires U-4 to be recorded before any code, so if the full dry run needs more
   than §4 allows you, the note names that remaining step as an open gap with an owner and a step, as for U-3, and
   makes it a precondition of the code package in its stop rules.
10. **The detector-controls file.** How each detector's negative control is run, how its output hash is produced, and
    how it is written to `detector-controls.json` in the WP9.3 format with the control kinds
    `REQUIRED_DETECTOR_CONTROLS` names. WP9.3's LR-003 refuses the first registration without it.
11. **Merging is not going live** (P-089 item 3, last bullet). Merging WP9.5 must not start any detector on `main` or
    the vault: L-1 is a separate owner decision. Say how the workflow and the scheduled runs stay inactive until
    then, for example dispatch-only triggers, and how a test or check proves it.
12. **Where the controls run** (P-089 item 4; 06v O-13). Every negative control runs on a scratch clone or a byte
    copy, never by writing `main` or the vault. W9-T7 replays `5df0c001` and `811d5a2b` on a scratch clone made from
    the local object store, with a fixture registry listing the files they touched. Say how the clone is made, and how
    the test proves it never writes the real repository.
13. **Tests.** W9-T7 (`slow`, integration) and W9-T19 (unit), plus each detector's own controls. Give a time
    estimate per test file. P-087 item 7 set WP9.4-2 a 5-minute budget for new tests; propose one for WP9.5.
14. **Research assurance.** Which claims are machine-checked and which only a human can judge, with the enforcement
    artifact for each machine-checkable one.
15. **Claims for review.** A numbered list of the note's load-bearing claims, each with the evidence that supports
    it, for the reviewer to attack.
16. **Stop rules** for the code package. They include its preconditions: U-3 and U-4 recorded in the note (items 3
    and 9), and Stephen's decisions on the owner points.
17. **Owner points.** Every decision the note needs from Stephen, each with options and your recommendation. Do not
    decide them yourself.

## 4. The boundary and the hard rules

**You may:**
- write `docs/plans/agentic-research-system/transition/w9/wp9-5-design-note.md` on your branch, and commit it;
- read any file in the worktree, and run read-only Git commands (`git log`, `git show`, `git diff`, `git cat-file`,
  `git rev-parse`) against the local repository;
- make a scratch clone under `%TEMP%` (for example `git clone --local --no-hardlinks C:\Users\steph\TDL <scratch>`) to
  check a claim, such as what a first-parent walk over `5df0c001` shows. Delete it when you are done, and never push
  from it;
- write throwaway scripts under `%TEMP%` to verify a claim. Do not commit them; describe what each showed;
- run read-only `gh api` **GET** requests for ruleset 20822054 and its rule-suites, and `gh pr view` / `gh pr list`;
- for U-4, run only `Get-Item` and `Get-ChildItem` on `C:\Users\steph\TDL\vault` and
  `C:\Users\steph\Documents\TDA-Research` (to record the junction's target and whether `04-Methods\Computational-Log.md`
  exists, and its size and last-write time), and `Get-FileHash` on that one file.

**You must not:**
- read the contents of any vault file, including the Computational-Log;
- write to the vault, `main`, `papers/`, `results/`, `.research-system/` or any `.apm/` state file;
- create, dispatch or run a GitHub workflow, or make any `gh api` call that is not a GET;
- write code under `research_system/`, `tools/`, `tests/` or `.github/`. Sketch code in the note if it helps;
- edit the register, 06v, W9, the paths addendum, `CONVENTIONS.md`, `CLAUDE.md` or `AGENTS.md`. If one looks wrong,
  say so in the note's open questions;
- push, open a pull request, or merge.

Commits: `git commit -F <file>`, with the message in a UTF-8 file without a byte-order mark. The subject starts
`[PIPELINE] P06: WP9.5 design note`. End the message with your own `Co-Authored-By:` trailer. Never use `--no-verify`.

## 5. Stop and report

Stop and report **PARTIAL - <exact gap>** when:
- P-089 is not on `main`;
- a mechanism cannot be specified without information you are not allowed to read (for example the CI token's
  rights, or a vault file's contents). Specify everything else, and name the gap as an owner point or a probe;
- the plan, W9 and the WP9.3 formats contradict each other in a way that changes a detector's behaviour. Give both
  citations; do not choose for Stephen;
- WP9.5 would need to change a protected identity, a WP9.3 format or a W9 command.

## 6. What to hand back

1. **Status** first, on its own line: `COMPLETE` (revision 1 of the note covers every item in §3) or
   `PARTIAL - <exact gap>`.
2. The branch, the head commit, the base commit, and `git log --oneline <base>..HEAD`.
3. The note's section list, and for each §3 item the section that settles it.
4. The owner points, one line each, with your recommendation.
5. What you verified by running something (scratch clone, script, `gh api` GET, U-4 check), and what each showed.
6. Every open question, and every place you were unsure, with citations.

Do not describe the note as reviewed, accepted or ready to merge. It goes to an independent review next.
