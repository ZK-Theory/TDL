# Weekly Research-System Review — Resolution Packet

**Review date:** 2026-11-17. The scheduled `weekly-system-review` task ran on time (Tuesday).

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md`. After this review it holds 321 entries, 21 of
them OPEN (OPEN, ESCALATED or PARTIALLY, per the lint). One of the 21 was appended by a concurrent zktheoryweb session
while this review ran (Group I).

**Scope:** every OPEN observation in the shared log, across the five trees named by the 2026-09-25 and 2026-10-02 owner
decisions: TDL, MathUni, the Counting Lives vault, codex_workflow and zktheoryweb. The other four trees were read only.
None has a commit since the last review. MathUni's dashboard wrote its daily session files, and zktheoryweb has
uncommitted snapshot work in progress; Counting Lives and codex_workflow have no file changed since 2026-11-10. One
OPEN entry targets zktheoryweb (Group I), and no tree outside the five appears in the log, so there is no scope finding.

**Decision owner:** Stephen

**Operating rule (unchanged since 2026-08-09):** approval authorizes a bounded verify-then-fix campaign on a reviewed
branch. It does not authorize direct changes to `main`, silent gate weakening, or acceptance without the named
controls.

> **The headline: the merge queue may be unreachable after most reviews.** The bypass audit built last week ran for the
> first time. It reports 6 bypassed updates to `main` in 7 days, against 2 through the queue, and none states a
> reason. Every bypassed head carries a CANCELLED required `merge-admission` run, and neither queued head does. The
> open PR #437 is BLOCKED right now with one. This pattern suggests a workflow problem; the reasons for the six
> bypasses remain unknown. See Group A. A1 is a five-minute check you can run today.

**What this review changed.**
- **Record (observation log):**
  - **Closed 10 entries on verified evidence.** Eight had met their close condition or were built in full, and two
    DEFERRED entries' limbs landed with WP9.3-2. Every PR named was checked for base `main` and a merge commit on
    `origin/main`. See "This review's closures".
  - **Applied two SKILL-lane entries** in this PR (below), and marked them ACTIONED, naming this PR.
  - **Added dated Progress notes** to 15 carried entries.
  - **Logged six observations.** Five are OPEN (Groups A, G and H). One, on the SKILL lane, was applied here.
  - **Archived** the 15 entries that the 2026-11-10 review and its campaign closed, to `archive/log-2026-11-17.md`.
- **Repo skills (applied in this PR, SKILL lane):**
  - `writing-plans-extras` 1.6.0: Forward-Obligation Scan step 7 greps the register, the Gate 7+ intake list and every
    06v addendum, not the register alone.
  - `adversarial-design-review` 1.6.0, `references/claims-checklist.md`: "Carried obligations" uses the same three-file
    grep. "Enforcement claims" checks "X always requires Y" per branch of the enforcing function.
  - Mirrored to `.claude/skills/` by `tools/sync_agent_skills.py`; `--check` reports every skill IDENTICAL and
    `pack pins: 12 checked, 0 drifted`. Neither skill is pinned by a pack.
- **research-observer (applied, outside git):** step 1's bypass audit loses its "once #425 is on `main`" conditional
  and gains a read of each bypassed head's required contexts. Backup:
  `~/.claude/skill-updates/2026-11-17/research-observer/SKILL.md.before`.
- **Not changed:** anything on the GATE, INVARIANT or PROCESS lanes, and nothing in the other trees. Everything below
  is a recommendation.

The pre-review log is at `~/.claude/skill-updates/2026-11-17/log/log.md.before`.

## Where last week's packet stands

You asked on 2026-11-10 for every group of the 2026-11-10 packet (PR [#421](https://github.com/ZK-Theory/TDL/pull/421))
to be resolved as recommended. The campaign PRs #422 to #427 all merged that day, each with base `main` and a merge
commit on `origin/main`. Re-resolved against `origin/main` (`4312dc63`):

| Group | Decision | Built | State now |
|---|---|---|---|
| A. `main` red after a bypass | approve A1–A3 | #422, #425 | Done; the entry is closed and its residual moves to B. A3's audit ran for the first time in this review (Group A) |
| B. The suite lane | approve B1–B3 | #425 (B3) | B1, your ruleset edit, is not made (readback 2026-11-17). B2 is not classified, but the WP9.3-1b review reproduced the failure in process (Group C). B3 is on `main`; no red episode since |
| C. Items carried to W9 | approve C1+C2 | #424, #432 | Done. C2's addendum merged; both C1 rows were landed by WP9.3-2 (#432, P-084 item 10). All three entries are closed |
| D. Claim discipline, round 2 | approve D1–D4 | #423, #424, #427 | Done; three entries closed. D4's findings file is on `main` byte-identical |
| E. Format drift | (b) | #423 | Done; entry closed |
| F. Results no-overwrite | approve (rewrites) | #425 | Done, and wider than the option you chose: Gate 0c refuses deletions, renames and type changes too. Entry closed; see "This review's closures" |
| S6. One claims checklist | approve | #427 | Done. This week's two lessons went into it once each |
| S7. Task prompt points at the skill | approve | — | Done |

Two of last week's PRs merged red: #425 through the queue (its own `ci-tools` controls, fixed by #431), and #428, which
followed it into the queue. Both passed the queue because `suite-verdict` is not required (Group B).

## How to use this packet

Tick one box per group. An approved group first re-resolves each mapped observation against current `main`. If an
observation is already compliant or superseded, record the evidence and close it. If it is still valid, build the named
mechanism with its negative control.

## Decision summary

| Group | OPEN | Recommended resolution | Decision |
|---|---:|---|---|
| A. Cancelled required runs keep PRs out of the queue | 2 | Confirm on #437, then stop `merge-admission` leaving a cancelled context; one check-runs helper for the audit and the register | `[ ]` approve A1–A4 · `[ ]` A1 only, then decide · `[ ]` defer |
| B. The suite lane is still not required | 2 | Your ruleset edit; fold the duplicate entry | `[ ]` approve B1 + S8 · `[ ]` S8 only · `[ ]` defer |
| C. The writer-lock release raises after its work is done | 2 | A defect task with a coordinated writer regression test; a flake-verdict line | `[ ]` approve C1+C2 · `[ ]` C2 only · `[ ]` defer |
| D. W9 census and read-path coverage | 4 | Share the census resolver; cover `show`; rule on one fallback; defer the scope lint | `[ ]` approve D1–D4 · `[ ]` some (name which) · `[ ]` defer |
| E. Worktree setup that no one runs | 3 | A SessionStart check of hooksPath and the venv; a refusal when the selected pre-commit hook includes the guard | `[ ]` approve E1+E2 · `[ ]` E1 only · `[ ]` defer |
| F. Design-note claim discipline, round 3 | 3 | Two checklist entries; a template line for selector scripts | `[ ]` approve F1–F3 · `[ ]` F1+F2 only · `[ ]` defer |
| G. Agent guards: fail-opens and other shells | 2 | Keep each fail-open's cause; widen the matchers to the MCP shells | `[ ]` approve G1+G2 · `[ ]` G2 only · `[ ]` defer |
| H. Commits that reach no PR | 2 | Refuse a push when the branch has a merged PR and no open PR; teach the register lint "pending by content" | `[ ]` approve H1–H3 · `[ ]` H1+H2 only · `[ ]` defer |
| I. zktheoryweb: a forbidden map is tracked | 1 | A content-scan test; your call on the CSV | `[ ]` approve I1, move the CSV out · `[ ]` approve I1, relax the rule · `[ ]` defer |
| This review's 10 closures | — | Keep them closed | `[ ]` keep · `[ ]` reopen (name which) |
| The two repo skill edits | — | Merge them with this PR | `[ ]` keep · `[ ]` revert |
| The research-observer edit | — | Keep it | `[ ]` keep · `[ ]` revert |

Total: 2 + 2 + 2 + 4 + 3 + 3 + 2 + 2 + 1 = **21**.

---

## A — Cancelled required runs keep PRs out of the queue (2)

`2026-11-17-cancelled-required-check-run-keeps-prs-out-of-the-queue` (new),
`2026-11-13-gh-pr-checks-rollup-misstates-a-rerun-check`.

**What the audit found.**
- `tools/check_bypass_merges.py --days 7` reports 6 bypassed updates to `main`, 2026-11-11 to 2026-11-14: #429, #430,
  #432, #433, #434 and #436. All are by the owner account, and none has a `Bypass reason:` line. The rule-suite API
  agrees: 6 `bypass` and 2 `pass` (#431, #435) since 2026-11-11.
- #429 and #430 merged while `suite-verdict` was red on their heads. In both the only red job was `ci-tools`, #425's
  control bug that #431 fixed; all eight shards passed.
- No agent receipt shows a refused bypass, so the merges were probably made outside an agent session. I did not
  establish that.

**The pattern.** I compared the four required checks on all eight heads:

| PR | Route | `merge-admission` runs on the head | `gh pr checks` |
|---|---|---|---|
| #429, #430, #432, #434, #436 | bypass | 1 success, 1 to 4 cancelled | `merge-admission` `fail` |
| #433 | bypass | 1 success, 1 cancelled, 1 failure | `merge-admission` `fail` |
| #431, #435 | queue | 1 success, none cancelled | all `pass` |

**The mechanism.**
- `merge-admission` runs on `pull_request`, `pull_request_review` and `pull_request_review_comment`, all in one
  concurrency group per PR with `cancel-in-progress: true` (`.github/workflows/merge-admission.yml`). A review that
  lands within a minute or two of a push, as CodeRabbit's does, cancels the run before it.
- The PR's status rollup keeps one context per triggering event. The cancelled event's context therefore stays
  CANCELLED after another event's run succeeds. For #434's head `d8cb0514`: run 43338626471 (`pull_request`) and run
  43338660384 were cancelled; run 43338692755 (`pull_request_review_comment`) succeeded. The rollup shows the
  `pull_request` context CANCELLED, and `gh pr checks` prints it as `fail`. That is the "three readings disagree"
  puzzle in the 2026-11-13 entry.
- **Live now:** PR #437 is `mergeStateStatus: BLOCKED`. Its `merge-admission` context is CANCELLED on
  `pull_request_review` and SUCCESS on `pull_request`, and both are `isRequired: true`.

**What is not proved.** The ruleset also requires code-owner review and resolved threads, so I have not shown that the
cancelled context is what blocks. It is the only difference I found between the bypassed and the queued heads.

**Suspected defect.** Cancelled required contexts may keep reviewed PRs out of the queue. Even if A1 confirms this
for #437, the audit cannot establish why earlier merges bypassed the queue.

**Proposed action.**
- **A1. Confirm.** On #437, re-run its cancelled `merge-admission` run (`gh run rerun <id>`) and read
  `mergeStateStatus` again. If it leaves BLOCKED, the mechanism is confirmed. This is a write to CI, so it is yours or
  a session's on your word.
- **A2. Fix the workflow.** Stop it leaving a cancelled required context. Options: key the concurrency group by event
  as well as PR; stop cancelling for the review events; or have `merge-admission-sweep.yml` re-run any cancelled
  `merge-admission` run on the current head. The choice is a design call for the fixing session. The Codex-thread
  history in the workflow's header explains why the review triggers exist; they stay.
- **A3. Show the check evidence.** `check_bypass_merges.py` prints each bypassed head's CANCELLED required contexts
  without classifying the bypass as forced or chosen.
- **A4. One helper for check status** (the 2026-11-13 entry). A small `tools/` command that prints, for a head, every
  run of each check name with its event and conclusion. A3 uses it, and register Evidence lines cite its output rather
  than `gh pr checks` or a single run ID.

**Controls.**
- A2: a fixture rollup with a CANCELLED required context on one event and SUCCESS on another is acted on (re-run) or
  reported; a rollup with only SUCCESS is not. The confirming evidence is the next CodeRabbit-reviewed PR entering the
  queue without a bypass.
- A3: the #434 fixture (two cancelled runs, one success) prints both cancelled runs without inferring a reason.
- A4: on `d8cb0514` it lists three `merge-admission` runs: two cancelled, one success.

**Recommended decision:** approve A1–A4, with A1 first, since A2's shape depends on it. State a bypass reason only
when it is independently established for that merge. If none is established, report the reason as unknown.

**Decision:** `[ ]` approve A1–A4 · `[ ]` A1 only, then decide · `[ ]` defer

---

## B — The suite lane is still not required (2)

`2026-10-02-full-suite-red-on-main-unseen`, `2026-10-03-shared-seam-change-merged-without-its-dependents`.

**Where it stands.**
- Ruleset 20822054 still requires contract-and-session-currency, require-active-currency-workflow, merge-admission and
  admission-controls. It was last updated 2026-09-11 (readback 2026-11-17).
- The scheduled lane has six consecutive green nights since 2026-11-12 (runs 43183625543 to 44055248411). The
  2026-11-11 night was red through `ci-tools` alone.
- Two queue entries merged red this week, because `suite-verdict` is not required: #425 (`1fba78aa`, its own controls)
  and #428 (`6aeb3b31`, the same failure). The closed bypass entry's residual is this condition, so the full-suite
  entry now carries it.

**Proposed action.**
- **B1.** Your ruleset edit: add `suite-verdict` to the required checks, as proposed since 2026-10-21. `suite-verdict`
  depends on `ci-tools`, so requiring it covers both #425's and #428's failures.
- **S8. Fold the twin.** `2026-10-03-shared-seam-change-merged-without-its-dependents` has 13 Progress notes, nine of
  them saying it closes with the full-suite entry. Its PR-time selection has been live since #329 (2026-10-06). Close it
  into `2026-10-02-full-suite-red-on-main-unseen`, which keeps the condition.

**Interaction with A.** On a PR, the suite workflow runs on `pull_request` alone and cancels only within that event
(`research-system-suite.yml`), so a newer run replaces the cancelled one and leaves no stale context. B1 does not make
Group A worse.

**Controls.** B1: the ruleset readback lists `suite-verdict`, and the next queue entry reports it as required.

**Recommended decision:** approve B1 and S8.

**Decision:** `[ ]` approve B1 + S8 · `[ ]` S8 only · `[ ]` defer

---

## C — The writer-lock release raises after its work is done (2)

`2026-11-10-nightly-writer-lock-flake-closes-its-own-issue-untriaged`,
`2026-11-10-flake-verdicts-need-in-process-repeats-on-both-trees`.

**What changed since last week.**
- Last week's B2 ran each test 48 times in fresh processes on Windows and saw no failure. It concluded that a
  reproduction needed shard load.
- The WP9.3-1b review, the same day, ran 300 repeats inside one process on each tree. It got 1 failure in 600 on the
  PR head and 3 in 600 on the base, with the same `ConflictError`.
- It also read the cause at `research_system/store/anchor.py:1727-1731`. The releaser re-checks the lock's name after
  deleting its own file, and raises "writer lock name was replaced during exact generation deletion" when a
  contender's retry has already created a new lock. By then the locked work has finished.
- The scheduled lane has not hit it since 2026-11-08. `anchor.py` is unchanged on `main`.

**Defect.** A release that raises after a successful operation is a store behaviour, not a test race. A production
writer under contention would see its committed operation reported as a conflict. The two entries are one defect and
its triage method.

**Proposed action.**
- **C1. A defect task** (`tda-diagnosing-computational-defects`). Coordinate two contending writers in one process
  on Windows. Have the first pause after deleting its lock generation and before the name recheck. Let the second
  acquire that name and hold its lock until the first finishes releasing. Fix the release check. A new lock under the
  name after the releaser's own generation is gone is a contender's lock, not a replacement of its own. The task
  decides the exact rule. Seam changes in `store/anchor.py` select a large part of the suite, so it runs through the
  queue with the affected selection.
- **C2. A flake-verdict line** in `tda-diagnosing-computational-defects`. A verdict of "flake" on a red required check
  cites repeats on the head and on the base, run in one process as the shard runs them, with counts.

**Controls.** C1: the forced order must reproduce the release `ConflictError` on `4312dc63`. After the fix, the
same test must show that the first writer releases successfully and leaves the second writer's lock intact.
C2 is text; its evidence is the next flake verdict carrying both repeat counts, one for the head and one for the base.

**Recommended decision:** approve C1 and C2. C1 removes the flake that would eject queue entries once B1 is in force.

**Decision:** `[ ]` approve C1+C2 · `[ ]` C2 only · `[ ]` defer

---

## D — W9 census and read-path coverage (4)

`2026-11-11-review-census-probed-only-the-named-evasions`, `2026-11-11-ars-legacy-show-failed-on-every-proposal-since-wp9-3-1`,
`2026-11-10-fallback-to-no-check-on-load-failure`, `2026-11-10-scope-item-missing-with-no-record-entry`.

Each instance is fixed on `main`; each entry's general check is not.

| Entry | Fixed by | What is still missing |
|---|---|---|
| Census binding model | #432, #434 (the `CommandService` census follows aliases, `partial` overrides, annotated assignments, walruses and scopes; P-084 item 4 records R2) | The runtime-construction census in the same file (`_Census`, lines 45 to 119) still follows `ImportFrom` aliases and plain `Assign` only |
| `ars legacy show` | #432 (`_projection_json`) | No test runs `show` over every projection collection the code writes |
| The fallback recheck | #429 (no "no binding" from a load failure; decided again in the lock) | One skip remains: a foundation file that cannot be read leaves the store "not named", so no check runs. Its one test I found (`test_w9_wp9_3_writers.py:401`) is the benign case |
| A dropped scope item | #428 (the builder landed) | No check holds a record to its note's split list |

**Proposed action.**
- **D1.** The runtime census reuses the service census's name-binding resolver. Controls: `AnnAssign`, walrus and
  call-time `partial` fixtures for `LegacyRuntime` and `DiscoveryRuntime`, each of which fails today.
- **D2.** One read-only CLI test runs `ars legacy show` on one identity of each projection collection (proposal,
  review, Decision, record, ownership), on a scratch store taken through a full flow. Control: a reducer storing a
  datetime fails it.
- **D3. Your ruling** on the foundation skip. Can an old checkout after an advance meet an unreadable or non-naming
  foundation file? If it can, add a control that runs that case and expects a refusal. If it cannot, record why as a
  known limit beside R2.
- **D4.** Defer the scope-reconciliation lint to the Gate 7+ intake list, §1, with a new row. It needs a stable
  record format ("What landed" and "Not in this PR") first. Control, when built: a fixture record omitting one split
  item fails.

**Recommended decision:** approve D1, D2 and D4, and rule on D3.

**Decision:** `[ ]` approve D1–D4 · `[ ]` some (name which) · `[ ]` defer

---

## E — Worktree setup that no one runs (3)

`2026-11-11-app-worktree-runs-the-main-checkouts-hooks-until-the-gate-is-run`,
`2026-11-11-fresh-worktree-uv-sync-omits-pytest`, `2026-11-13-fresh-worktree-pytest-absence-recurred`.

**Defect.**
- The venv rule has been in `using-git-worktrees-extras` since #387 (2026-10-21): provision with `uv sync --locked
  --all-extras` and prove pytest imports from the worktree's own venv.
- It was missed on 2026-11-11, on 2026-11-13, and in this review. Here `uv run --no-sync python
  tools/sync_agent_skills.py` wrote the mirror, then stopped at its pack-pin check for want of `yaml`. A partial run
  like that can look finished.
- The sessions ran in app-created worktrees, which no setup skill is invoked for. The hooksPath check in
  `install-git-hooks.py` is the same shape: it works, and runs only when someone remembers it.
- A documented rule that is skipped three times needs a gate, not another line of prose.

**Proposed action.**
- **E1.** Extend the SessionStart check (`tools/hook_currency.py` already runs there in every checkout) to report two
  things in the session's checkout: `core.hooksPath` resolves outside the checkout, or the checkout has no venv that
  imports pytest. The second names the provisioning command.
- **E2.** Add the refusal to `.githooks/pre-commit`. If Git selects a copy of the hook containing the guard, it
  refuses when the resolved hook directory is outside the worktree being committed in. If Git selects older hooks
  without the guard, E1 reports the configuration; E2 provides no commit refusal in that case.

**Controls.** E1: a fixture worktree with an absolute hooksPath to another checkout is reported; one with a
venv lacking pytest is reported; a provisioned worktree is not. E2: with the guard in the selected foreign hook,
the absolute-hooksPath fixture's commit is refused with a hooksPath diagnostic. With older foreign hooks that lack
the guard, assert the E1 report only.

**Recommended decision:** approve E1 and E2.

**Decision:** `[ ]` approve E1+E2 · `[ ]` E1 only · `[ ]` defer

---

## F — Design-note claim discipline, round 3 (3)

`2026-11-11-note-claimed-a-tool-prints-what-its-inputs-cannot-determine`,
`2026-11-13-review-summary-list-dropped-a-reading-its-own-table-marks`,
`2026-11-16-extractor-rule-specified-twice-without-a-run-on-the-governed-files`.

| Entry | The lesson | Nearest text on `main` |
|---|---|---|
| Tool prints what it cannot know | "Tool X prints Y" is checked against X's inputs, including values set later by another component | None. Ruled for WP9.3 by P-084 item 2 (Q1) |
| Summary dropped a reading | A summary list restating a table is derived from it, or checked against it | None |
| Extractor rule skipped twice | A note that proposes a byte-level selector ships its reference script and census output in the same commit | The checklist's "Selectors and parsers" Author line, which the WP9.4 note (PR #437) skipped in revisions 1 and 2 |

**Proposed action.**
- **F1.** A new checklist entry, "Output claims". Author line: for "X prints or produces Y", list what X may open and
  show Y is a function of it. Reviewer line: check the same, including any value fixed by a later step.
- **F2.** In `adversarial-design-review`'s "For Stephen" summary: generate the register-lines list from the readings
  table (every row marked Yes), or state that the two were compared. Handoffs cite the table, not the list.
- **F3.** The entry asks for a gate. A docs lint that finds "selector sections" would be fuzzy, so add the line to the
  ARS design-note template's checklist now: a selector section links its script and census output, or the note is
  not ready for review. Defer a lint to the Gate 7+ intake list.

**Controls.** F1 and F2 are text; their evidence is the next design-note review. F3: revision 2 of the WP9.4 note
fails the template line.

**Size.** The checklist is 212 lines after this PR's edits (202 before). S6 is working: each lesson is written once.

**Recommended decision:** approve F1–F3. These are PROCESS and GATE entries, so this run did not apply them.

**Decision:** `[ ]` approve F1–F3 · `[ ]` F1+F2 only · `[ ]` defer

---

## G — Agent guards: fail-opens and other shells (2)

`2026-11-17-commit-state-guard-fails-open-and-discards-the-cause` (new),
`2026-11-17-shell-guards-do-not-match-the-mcp-shell-tools` (new). Both come from this review's spot check.

**Defect.**
- **Fail-opens with no cause.** `commit-state-guard` is live: 98,028 `allow`, 502 `deny` (the latest on 2026-11-13)
  and 94,553 `silent` receipts, and its controls pass.
  - It also has 1,478 `FAILOPEN(exit=0)` receipts, from 2026-10-02 to 2026-11-11 (12 on that day), about 0.8% of its
    runs.
  - The launcher sends the Python stderr to `/dev/null`, so nothing records why. On 2026-11-11 the fail-opens came as
    a PreToolUse and PostToolUse pair three seconds apart. That fits an error on some command shape better than the
    30-second timeout.
  - A PreToolUse fail-open lets through exactly what the guard exists to deny.
- **Other shells.** Both git-safety guards (`admin-bypass-guard.sh`, `commit-state-guard.sh`) match `Bash|PowerShell`.
  Sessions also have `mcp__terminal__run_in_terminal`, which the project's memory recommends for long runs, and
  Desktop Commander's `start_process` and `interact_with_process`.
  - A `git commit --no-verify`, a `core.hooksPath` override or `gh pr merge --admin` sent through either would meet no
    guard.
  - Git's own hooks still run on a plain commit, so the gap is the bypass forms, which are the guards' reason to
    exist.
  - I sent no such command. The finding is the matcher text.

**Proposed action.**
- **G1.** The launcher writes the exception's last line (type and message) into the receipt or a sibling log, and the
  weekly review tallies `FAILOPEN` receipts per hook. Then fix the error class the record shows.
- **G2.** Widen both matchers to the MCP shell tools, with each guard reading that tool's command field. The
  alternative is to deny git and gh commands through those tools in the permission settings.

**Controls.** G1: a payload that makes the Python raise records its exception type. G2: a PreToolUse payload for
`mcp__terminal__run_in_terminal` carrying `git commit --no-verify` is denied, and the Bash form still is.

**Recommended decision:** approve G1 and G2.

**Decision:** `[ ]` approve G1+G2 · `[ ]` G2 only · `[ ]` defer

---

## H — Commits that reach no PR (2)

`2026-11-17-review-fixes-pushed-after-their-pr-merged` (new),
`2026-11-17-register-lint-flags-branches-carrying-an-open-prs-register-bytes` (new).

**Defect.**
- **A push to a merged branch.** #428 merged through the queue at 21:38Z on 2026-11-10, at head `649d0698`. The fixes
  from its independent review, of that head, were pushed to its branch at 23:10Z and 23:14Z (`6a907e49`, `6836b846`).
  - GitHub attached them to no PR, so they had no CI or CodeRabbit run.
  - `main` lacked them until #429 the next day. Nothing warned at the push: `.githooks/pre-push` refuses only direct
    pushes to `main`.
- **Three false "stranded" findings.** The register-reachability lint reports 3 stranded branches:
  - `origin/review/w9-wp9-4-note` (`a9935c0b`);
  - `review/w9-wp9-4-note-re-review` (`a704d9b3`), locally and on `origin`.

  Each holds the register as blob `dea3e597`, the same blob as open PR #437's head, which the same run reports as
  pending. They are the PR's own register text on review branches stacked on it. This review carries them as such.

**Proposed action.**
- **H1.** For the pushed branch, `.githooks/pre-push` first asks `gh pr list --head <branch> --state open` and
  allows the push under H1 if an open PR exists. Only after confirming there is no open PR does it check
  `--state merged`. If a merged PR exists, it refuses the push and tells the user to open a follow-up PR.
- **H2.** `check_register_reachability.py` reports a branch whose register blob equals an open PR head's as pending in
  that PR, and one equal to `origin/main`'s as landed.
- **H3. Your call:** may a PR under an independent review enter the queue before the review's disposition is on its
  head?

**Controls.** H1: a push passes when the branch has an open PR, including when it also has a merged PR. A push is
refused when the branch has a merged PR and no open PR. H2: a fixture branch whose register blob equals an open PR
head's is pending; one that differs is still stranded.

**Recommended decision:** approve H1 and H2, and rule on H3.

**Decision:** `[ ]` approve H1–H3 · `[ ]` H1+H2 only · `[ ]` defer

---

## I — zktheoryweb: a forbidden map is tracked (1)

`2026-11-17-zktheoryweb-org-to-link-map-tracked-despite-rule` (new, logged by a concurrent zktheoryweb session during
this review).

**Defect.** Checked read-only in this review:
- `docs/snapshots.md` (lines 37 and 49) and `scripts/snapshots/schedule.mjs` (line 7) say the repository must never
  hold the organisation-to-link map.
- `tools/snapshots/charity_snapshot_links.csv` is tracked, with columns `organisation,wave,price_on_page,public_path`
  and 31 data rows. It was added in #38 and extended in #46.
- The existing guard checks only that `schedule.json` has no organisation key.
- The repository is private (`gh repo view`: PRIVATE), which limits the exposure. The rule as written has never been
  enforced.

**Proposed action.**
- **I1.** A test in `scripts/snapshots/snapshots.test.ts` that fails when any tracked file outside `public/s/` pairs an
  organisation-like column with a `/s/<token>/` path (`git ls-files` and a content scan).
- **I2. Your call** on the CSV. Either move it out of the repository, to wherever the CRM-side map lives, as the rule
  says; history keeps the old copies, and removing those is a separate decision. Or relax the documented rule for a
  private repository.

**Controls.** I1: a temporary fixture CSV holding both columns fails the test, and the tree passes once the CSV is
moved (or the rule is relaxed and the test scoped to match).

**Recommended decision:** approve I1 and move the CSV out. The rule is stated in two places, and a private repository
does not stay private by default. This is zktheoryweb, not TDL, so the change goes through that repository's own PR.

**Decision:** `[ ]` approve I1, move the CSV out · `[ ]` approve I1, relax the rule · `[ ]` defer

---

## This review's closures

Each closing Status names its evidence, and the previous Status is kept as a `Prior status:` line. They stay in full
text until the next review. If you disagree with any, tick "reopen" and I will restore it from the backup.

| Entry | Status | Evidence |
|---|---|---|
| `2026-10-28-shared-location-named-but-never-defined` | ACTIONED | #424 `09bd26f0`: `implementation/06v-addendum-2026-11-10-w9-paths.md` |
| `2026-11-08-enforcement-impossibility-claim-cited-one-function` | ACTIONED | #423 `76bfb3b6`, #424 `09bd26f0`: "Enforcement claims" in the checklist; the findings file on `main` byte-identical (blob `67901fb0`) |
| `2026-11-09-design-note-encoding-never-run-through-the-unchanged-assigner` | ACTIONED | #423: "Probes", probe currency |
| `2026-11-09-design-note-wiring-claims-named-the-wrong-construction-site` | ACTIONED | #423: "Wiring claims" |
| `2026-11-09-main-holds-files-ruff-format-would-change` | ACTIONED | #423: `.claude/rules/python.md` line 13 |
| `2026-11-10-results-no-overwrite-misses-the-path-results-take` | ACTIONED | #425 `1fba78aa`: Gate 0c, 18 `allow` receipts. **It refuses deletions, renames and type changes as well**, the wider option you left open (`test_pre_commit_refuses_every_staged_loss_of_a_committed_result`). Reopen if you wanted rewrites only |
| `2026-11-10-bypass-merge-skipped-a-red-suite-and-left-main-red` | ACTIONED | #422 `0e54de75`, #425 `1fba78aa`: all three limbs. The 2026-11-11 note asked it to stay open until B1; that residual is the full-suite entry's condition, which now carries it. Its "close when #425 merges" would otherwise be flagged every week |
| `2026-11-10-binding-recheck-census-checks-callees-not-callers` | ACTIONED | #429 `fbb99ce0`: `test_every_production_command_service_construction_passes_a_binding_check`, with the `binding_check=None` control; P-083 |
| `2026-10-28-catalogue-precondition-unrepresentable-in-closed-schema` | ACTIONED (was DEFERRED) | #432 `baea2c13`: `test_w9_precondition_fields.py`; intake row "done" |
| `2026-10-29-note-cited-a-truncated-row-range-and-built-an-owner-point-on-it` | ACTIONED (was DEFERRED) | #432 `baea2c13`: `test_w9_pilot_promotion_table.py`; intake row "done" |

Applied in this review (SKILL lane): `2026-11-11-plan-step-7-misses-intake-and-paths-rows-naming-the-package` and
`2026-11-16-gate-claim-held-on-one-predicate-branch-only` (this PR), and
`2026-11-17-review-step-1-bypass-audit-conditional-outlived-its-pr` (research-observer). If you revert the repo edits,
the first two reopen.

## Simplification sweep

- **S8. Fold the suite twin** (Group B). One entry, one condition, instead of two re-noted every week.
- **The claims checklist is doing its job.** This week's two lessons each went into one file, with an author and a
  reviewer line, instead of two skills. Group F would add one entry and extend nothing twice.
- **Archival keeps the log flat.** 15 entries archived; the log's OPEN count fell from 25 to 20 with this review's
  five new entries, and is 21 with the concurrent zktheoryweb one.
- **No skill is proposed for removal.** `using-git-worktrees-extras` keeps its provisioning prose. Once E1 lands, the
  check, not the prose, is what catches the miss.

---

## Completeness ledger

Computed, not assembled. Every OPEN id comes from `observation_log_lint.parse` over the live log after this review's
edits, and the table is checked with `tools/observation_log_lint.py <log> --packet <this file>`.

| Group | Count | IDs |
|---|---:|---|
| A | 2 | 2026-11-17-cancelled-required-check-run-keeps-prs-out-of-the-queue · 2026-11-13-gh-pr-checks-rollup-misstates-a-rerun-check |
| B | 2 | 2026-10-02-full-suite-red-on-main-unseen · 2026-10-03-shared-seam-change-merged-without-its-dependents |
| C | 2 | 2026-11-10-nightly-writer-lock-flake-closes-its-own-issue-untriaged · 2026-11-10-flake-verdicts-need-in-process-repeats-on-both-trees |
| D | 4 | 2026-11-11-review-census-probed-only-the-named-evasions · 2026-11-11-ars-legacy-show-failed-on-every-proposal-since-wp9-3-1 · 2026-11-10-fallback-to-no-check-on-load-failure · 2026-11-10-scope-item-missing-with-no-record-entry |
| E | 3 | 2026-11-11-app-worktree-runs-the-main-checkouts-hooks-until-the-gate-is-run · 2026-11-11-fresh-worktree-uv-sync-omits-pytest · 2026-11-13-fresh-worktree-pytest-absence-recurred |
| F | 3 | 2026-11-11-note-claimed-a-tool-prints-what-its-inputs-cannot-determine · 2026-11-13-review-summary-list-dropped-a-reading-its-own-table-marks · 2026-11-16-extractor-rule-specified-twice-without-a-run-on-the-governed-files |
| G | 2 | 2026-11-17-commit-state-guard-fails-open-and-discards-the-cause · 2026-11-17-shell-guards-do-not-match-the-mcp-shell-tools |
| H | 2 | 2026-11-17-review-fixes-pushed-after-their-pr-merged · 2026-11-17-register-lint-flags-branches-carrying-an-open-prs-register-bytes |
| I | 1 | 2026-11-17-zktheoryweb-org-to-link-map-tracked-despite-rule |
| **Total** | **21** | |

---

## Lint and ledger check

| When | Tool | Result |
|---|---|---|
| Before this review's edits | `observation_log_lint.py --reachability . --close-conditions . --intake <list>` at `4312dc63` | `314 observation(s): 25 OPEN`. Reachability: 37 hashes, 0 stranded, 1 landed by content (`6dcc2f61`, true). Close conditions: 7 checked, 7 met, all true; one (#425) is "met in letter only" per its own note, handled as above. Intake: 7 checked, 0 without a row |
| After the edits | same, at `4312dc63` | `320 observation(s): 20 OPEN`, then 321 and 21 after the concurrent zktheoryweb append (Group I). Reachability: 35 hashes, 0 stranded; 2 "not a commit" are blob ids (`dea3e597`, `87a3862c`). Close conditions: 0 naming PRs (6 name none). Intake: 5 checked, 0 without a row |
| Register reachability | `check_register_reachability.py --repo .` | 109 unmerged branches, 3 stranded (all #437's register blob on review branches, Group H), 1 pending in open PR #437 |
| Bypass audit | `check_bypass_merges.py --days 7` | 6 bypassed updates, 8 problems: 6 without a reason line, 2 with `suite-verdict` red (`ci-tools` only). Group A |
| After the edits, `--packet` on this file | `observation_log_lint.py <log> --packet <this file>` | see the PR's test plan |

The main edit was made by a script that refused to write unless:
- the log matched its backup's SHA-256 and was CRLF throughout (as written back);
- the id order was unchanged, with the new entries appended at the end;
- the OPEN set changed by exactly the named closures and the new OPEN entries;
- every entry not named in the edit was unchanged apart from trailing whitespace;
- the lint's non-reachability checks came back clean.

Three later hand edits followed, each re-linted: a wrong citation in a new entry (an interim-report commit on a local
review branch, which the reachability check caught), and the two DEFERRED closures.

**Archival.** The 15 entries the 2026-11-10 review and its campaign closed moved verbatim to
`archive/log-2026-11-17.md`, each with a stub in `log.md`. This review's closures stay in full text until the next
review. DEFERRED entries stay in the log, since the `--intake` check reads them.

## Skills pass

**Inventory.**
- Repo skills changed between the reviews: #423 (`adversarial-design-review` 1.4.0, `writing-plans-extras` 1.4.0) and
  #427 (both to 1.5.0, the shared `references/claims-checklist.md`). `sync_agent_skills.py --check` at `4312dc63`
  shows every synced skill IDENTICAL and `pack pins: 12 checked, 0 drifted`.
- This PR changes both skills to 1.6.0 (two SKILL-lane entries). The mirror is regenerated and checked, and
  `tools/skill_sync_state.json` updated. No test, contract or pack binds the edited text (`git grep` over `tests`,
  `tools`, `contracts`, `.research-system` and `.github`).
- The research-observer edit is to a global skill outside git, with no repo mirror. No pack pins it.

**Cross-check of every OPEN group against the skills.**
- **A:** no repo skill change. `tda-agent-safety-guardrails` covers agent bypasses; the audit did not establish
  whether these merges came from an agent session.
- **B:** none.
- **C:** `tda-diagnosing-computational-defects` (C2's line, C1's method).
- **D:** `contract-first-tdd` already asks for negative controls; D1 and D2 are tests, not skill text.
- **E:** `using-git-worktrees-extras` holds the rule; E is its gate.
- **F:** `adversarial-design-review` and its checklist (F1, F2); the ARS design-note template (F3).
- **G:** `tda-agent-safety-guardrails` could name the MCP shells once G2 lands.
- **H:** none.
- **I:** none; the fix is a test in zktheoryweb.

**The SKILL-lane entries.** Two OPEN entries were on the SKILL lane, and both were applied, in this PR. The third,
logged and applied here, is research-observer's own step 1.

**Compliance against the active cross-cutting principles.**
- Step 7's widened grep follows silent absence: a forward obligation outside the register produced no signal, and now
  the scan reaches it.
- The per-branch line extends the census principle (name every path) to the branches inside a seam.
- The research-observer edit removes a dated conditional and adds a read of the head's required contexts. The
  rule-suite's `bypass` records that a bypass occurred; the contexts show the state of the checks. Report the contexts
  as evidence without classifying the bypass as forced or chosen from them. State a reason only when independently
  established for that merge; otherwise report it as unknown.
- Nothing adds, weakens or removes a gate.

## Gate-liveness spot check

Two gates no packet has named before:

1. **`.claude/hooks/commit-state-guard.sh`** (PreToolUse and PostToolUse, on Bash and PowerShell).
   - Negative controls: `tests/tools/test_commit_state_guard_hook.py`, run by admission-controls (`ci.yml` line 184).
   - Positive signal: 98,028 `allow`, 502 `deny`, 94,553 `silent` receipts.
   - Findings: 1,478 fail-opens with no cause kept, and no coverage of the MCP shell tools (Group G).
2. **`.claude/hooks/mirror-tree-guard.sh`** (PreToolUse, on `Write`, `Edit` and `MultiEdit`).
   - Negative controls: `test_system_review_hook_gates.py` (three mirror-tree tests), run by admission-controls
     (`ci.yml` line 186).
   - Positive signal: 96,513 `allow` and 71 `deny`. The last deny was on 2026-08-02, which fits agents editing only the
     authoring tree since. The only fail-opens (48) were on its first day, 2026-07-28.
   - Coverage holds. A script or shell write to the mirror bypasses the hook, but pre-commit Gate 0
     (`sync_agent_skills.py --check`, `.githooks/pre-commit` line 296) refuses the commit. This review's own sync went
     through that path.

The two control files passed: **131 tests**. `install-git-hooks.py` reports every required hook present and executable
in `.githooks`, in this review's worktree. No destructive probe was run. Receipts were read with `grep -a`, across the
main checkout's log and every app worktree's.

**Gates seen firing on live data this week:**
- **The bypass audit** (#425), first weekly run: 8 findings, all true.
- **Gate 0c** (#425): 18 `allow` receipts, no block (no result written).
- **The suite lane:** the 2026-11-11 night caught #425's broken controls through `ci-tools`.
- **The observation-log lint's reachability check:** it caught a wrong commit citation in this review's own new
  entry, before the packet.
- **SessionStart:** the hook-currency check reported the main checkout 1 commit behind `origin/main`, with no hook
  files changed.

## Coverage question

"Did anything go wrong this week that no gate, contract or invariant caught?" Yes:

| What went wrong | Caught by | Observation |
|---|---|---|
| 6 of 8 updates to `main` bypassed the queue, with no reason given | the bypass audit, a week after the fact; this review found a check pattern, with reasons still unknown | `2026-11-17-cancelled-required-check-run-keeps-prs-out-of-the-queue` (A) |
| #425 and #428 merged through the queue with `suite-verdict` red | the next nightly and a fix session | carried by `2026-10-02-full-suite-red-on-main-unseen` (B) |
| #428's review fixes were pushed after it merged and reached no PR | the review session, by hand; carried by #429 | `2026-11-17-review-fixes-pushed-after-their-pr-merged` (H) |
| `ars legacy show` had failed on every W9 proposal since WP9.3-1 | WP9.3-2's batch-mode test | `2026-11-11-ars-legacy-show-failed-on-every-proposal-since-wp9-3-1` (D) |
| A WP9.4 extractor rule went unrun on real files twice | its re-review, by hand | `2026-11-16-extractor-rule-specified-twice-without-a-run-on-the-governed-files` (F) |
| A worktree venv without pytest or yaml, three times | each session, by hand | Group E |
| zktheoryweb has tracked a map its docs forbid since #38 | its own session, by hand | `2026-11-17-zktheoryweb-org-to-link-map-tracked-despite-rule` (I) |

None is a numerical or statistical failure, so none is a new invariant-battery item. C1 is a store defect with a test,
not a battery check.

## This review's actions

1. Found the previous packet (#421) and its campaign (#422 to #427). Re-resolved them against `origin/main`, checking
   each PR's base and merge-commit ancestry. Fast-forwarded the main checkout from `634fc4f2` to `4312dc63`.
2. Ran `git fetch origin`, the observation-log lint with `--reachability`, `--close-conditions` and `--intake`, the
   register-reachability lint and the bypass audit, before and after the edits.
3. Read ruleset 20822054, the rule-suite evaluations, the merge-queue runs, the scheduled suite runs, and the
   required-check runs on all eight heads that updated `main`. Read #437's live rollup and merge state.
4. Read `research_system/cli.py` `_foundation_binding_check`, the two censuses, `store/anchor.py:1715-1731` and the
   P-084 register entry for the carried W9 items.
5. Checked MathUni, Counting Lives, codex_workflow and zktheoryweb for new material (none for the log).
6. Closed 10 entries, added 15 Progress notes, logged six observations and archived 15, through a checked script and
   three re-linted hand edits. Backup: `~/.claude/skill-updates/2026-11-17/log/log.md.before`.
7. Edited `writing-plans-extras` and `adversarial-design-review` in `.agents/skills/`, synced and checked the mirror.
8. Edited research-observer's step 1, with a dated backup.
9. Ran both spot-checked gates' controls (131 passed) and `install-git-hooks.py`.
10. Updated `last-review-date.txt` to `2026-11-17`.
11. Opened this packet as a PR, from the linked worktree `.claude/worktrees/system-review-2026-11-17`.
