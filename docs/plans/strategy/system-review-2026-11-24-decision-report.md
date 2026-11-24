# Weekly Research-System Review: Resolution Packet

**Review date:** 2026-11-24. The scheduled `weekly-system-review` task ran on time (Tuesday).

**Canonical source:** `C:\Users\steph\.claude\skill-observations\log.md`. After this review it holds 332 entries, 29 of
them OPEN (OPEN, ESCALATED or PARTIALLY, per the lint).

**Scope:** every OPEN observation in the shared log, across the five trees named by the 2026-09-25 and 2026-10-02 owner
decisions: TDL, MathUni, the Counting Lives vault, codex_workflow and zktheoryweb. The other four trees were read only.
zktheoryweb merged #48 to #55 on 2026-11-17 and 2026-11-19, and three OPEN entries target it (Groups I and J). MathUni has no
commit since 2026-11-17, only its dashboard's daily files. Counting Lives and codex_workflow have no file changed since
then. No tree outside the five appears in the log, so there is no scope finding.

**Decision owner:** Stephen

**Operating rule (unchanged since 2026-08-09):** approval authorizes a bounded verify-then-fix campaign on a reviewed
branch. It does not authorize direct changes to `main`, silent gate weakening, or acceptance without the named
controls.

> **The headline: last week's packet is still open, and this one stacks on it.** PR
> [#438](https://github.com/ZK-Theory/TDL/pull/438) has been open seven days with one ruling (A2 declined). Its 21
> items carry into this packet unchanged as Groups A to I, and its two applied skill edits have not reached `main`.
> This PR's two checklist edits touch the same file, so this branch is built on #438's head. **Merge #438 first, then
> this PR** (or merge this one alone: it contains #438). Group M asks whether applied edits should ship apart from
> the decisions from now on.
>
> **New this week:** two guards that run on every write but no longer cover what they were built for (Group L). The
> notation guard misses `W₁`, the form the papers write. The dispatch-readiness guard watches `.apm/bus/`, which no
> dispatch has used since July. And the writer-lock flake came back, on #439's PR run (Group C).

**What this review changed.**
- **Record (observation log):**
  - **Closed 3 entries.** Two SKILL-lane entries were applied in this PR (below). The shallow-repository entry closed
    on verified evidence: PR #440 (`cd4e10ba`, base `main`) built its detection limb.
  - **Added 13 dated Progress notes** to carried entries.
  - **Logged 3 observations,** all OPEN: two from the gate spot check (Group L) and one from step 0 (Group M).
  - **Archived** the 11 entries that the 2026-11-17 review closed on `main` evidence, to `archive/log-2026-11-24.md`.
    The two entries applied in #438 stay in full text until it merges, so a decline can reopen them in place.
- **Repo skills (applied in this PR, SKILL lane):**
  - `adversarial-design-review` 1.7.0, `references/claims-checklist.md`. "Prescribed corrections" now says corrections
    compose: when two change one rule, run the combined rule on the document's examples and fixtures, and check that
    each clause can still fire. A new entry, "Elided quotations", says to restore every ellipsis in a quoted governing
    rule from its source and check the design against the full sentence, with a case-variant probe for Windows path
    comparisons.
  - `writing-plans-extras` 1.7.0 names both in its list of checklist entries.
  - Mirrored to `.claude/skills/` by `tools/sync_agent_skills.py`; `--check` reports every skill IDENTICAL and
    `pack pins: 12 checked, 0 drifted`. Neither skill is pinned by a pack, and no test, contract or workflow binds the
    edited text.
- **Not changed:** research-observer, anything on the GATE, INVARIANT or PROCESS lanes, and nothing in the other trees.
  Everything below is a recommendation.

The pre-review log is at `~/.claude/skill-updates/2026-11-24/log/log.md.before`.

## Where last week's packet stands

PR #438 (2026-11-17) is open at `124a1287`. Its record since:
- 2026-11-20: CodeRabbit's autofix commit `29cc0a3d` qualified Group A's evidence and specified two controls.
- 2026-11-21: you said the week's bypasses were "manual and mine to speed up work in progress". The packet's Group A
  was rewritten, A1 dropped, and A2 (the workflow change) recorded as declined.
- No other group has a decision.

Re-resolved against `origin/main` (`4ca375a3`):

| Group | State now |
|---|---|
| A. Cancelled contexts, bypass reason line | Carried. 11 of 11 updates to `main` were bypasses this week; see A |
| B. Suite lane not required | Carried. Ruleset unchanged; every nightly green |
| C. Writer-lock release | Carried, and recurred on 2026-11-20 |
| D. W9 census and read paths | Carried. WP9.4 added two `ars legacy` read commands; the four gaps are unchanged |
| E. Worktree setup | Carried, with a fourth entry |
| F. Claim discipline, round 3 | Carried |
| G. Fail-opens and other shells | Carried. 10 more fail-opens, still with no cause kept |
| H. Commits that reach no PR | Carried. No recurrence; H2's three false findings cleared when #437 merged |
| I. zktheoryweb map | Carried. The CSV is still tracked |
| Two skill edits | On #438's head only. This PR carries them |

## How to use this packet

Tick one box per group. An approved group first re-resolves each mapped observation against current `main`. If an
observation is already compliant or superseded, record the evidence and close it. If it is still valid, build the named
mechanism with its negative control. Groups A to I repeat last week's proposals with this week's evidence; the full
text of their controls is in #438's packet, `docs/plans/strategy/system-review-2026-11-17-decision-report.md`.

## Decision summary

| Group | OPEN | Recommended resolution | Decision |
|---|---:|---|---|
| A. Stale cancelled contexts and the bypass reason line | 2 | One check-runs helper; keep the reason line with a `wip` short form | `[ ]` approve A4, rule on A5 · `[ ]` A5 only · `[ ]` defer |
| B. The suite lane is still not required | 2 | Your ruleset edit; fold the duplicate entry | `[ ]` approve B1 + S8 · `[ ]` S8 only · `[ ]` defer |
| C. The writer-lock release raises after its work is done | 2 | A defect task with a coordinated two-writer test; a flake-verdict line | `[ ]` approve C1+C2 · `[ ]` C2 only · `[ ]` defer |
| D. W9 census and read-path coverage | 4 | Share the census resolver; cover every `ars legacy` read; rule on one fallback; defer the scope lint | `[ ]` approve D1–D4 · `[ ]` some (name which) · `[ ]` defer |
| E. Session and worktree setup that no one runs | 4 | One SessionStart line for hooksPath, the venv, the vault and the results inputs; a pre-commit refusal | `[ ]` approve E1–E3 · `[ ]` E1+E3 only · `[ ]` defer |
| F. Design-note claim discipline, round 3 | 3 | Two checklist entries; a template line for selector scripts | `[ ]` approve F1–F3 · `[ ]` F1+F2 only · `[ ]` defer |
| G. Agent guards: fail-opens and other shells | 2 | Keep each fail-open's cause; widen the matchers to the MCP shells | `[ ]` approve G1+G2 · `[ ]` G2 only · `[ ]` defer |
| H. Commits that reach no PR | 2 | Refuse a push to a branch whose PR merged; teach the register lint "pending by content" | `[ ]` approve H1–H3 · `[ ]` H1+H2 only · `[ ]` defer |
| I. zktheoryweb: a forbidden map is tracked | 1 | A content-scan test; your call on the CSV | `[ ]` approve I1, move the CSV out · `[ ]` approve I1, relax the rule · `[ ]` defer |
| J. zktheoryweb: deploy and retire checks that live in one session | 2 | A manifest check that runs Netlify's validator; a durable record of skipped prunes | `[ ]` approve J1+J2 · `[ ]` J1 only · `[ ]` defer |
| K. The design-note review loop | 2 | Prescriptions labelled or attacked before they go; stop after two rounds in one subsystem; cite the review for credited fixes | `[ ]` approve K1–K3 · `[ ]` some (name which) · `[ ]` defer |
| L. Two guards that pass without covering | 2 | Widen the notation pattern; put the handover briefs under the readiness guard | `[ ]` approve L1 + L2(a) · `[ ]` L1 + L2(b) · `[ ]` defer |
| M. Applied skill edits wait on the packet's decisions | 1 | Ship applied edits in their own PR from next week | `[ ]` approve M1 · `[ ]` approve M2 · `[ ]` defer |
| This review's 3 closures | — | Keep them closed | `[ ]` keep · `[ ]` reopen (name which) |
| The two repo skill edits | — | Merge them with this PR, after #438 | `[ ]` keep · `[ ]` revert |

Total: 2 + 2 + 2 + 4 + 4 + 3 + 2 + 2 + 1 + 2 + 2 + 2 + 1 = **29**.

---

## A — Stale cancelled contexts and the bypass reason line (2)

`2026-11-17-cancelled-required-check-run-keeps-prs-out-of-the-queue`,
`2026-11-13-gh-pr-checks-rollup-misstates-a-rerun-check`.

**Defect.** A cancelled `merge-admission` run leaves a CANCELLED context in the status rollup after a later run
succeeds, and `gh pr checks` prints it as `fail`, so citations of check status disagree. Separately, CONVENTIONS
(2026-11-08) says a bypass states its reason, and none has.

**This week.** `tools/check_bypass_merges.py --days 7` reports 11 bypassed updates to `main` out of 11 (#437 and #439
to #448), with 44 problems. Eleven are missing reason lines. The other 33 are required checks that were not green at
the merge: 32 finished green minutes later, and one, `suite-verdict` on #439, finished red (Group C). Cancelled
`merge-admission` runs appear on two heads (#439, #447). These are reported as counts, per your statement of
2026-11-21.

**Proposed action (unchanged).**
- **A4.** A small `tools/` command that prints, for a head, every run of each check name with its event and
  conclusion. Register Evidence lines and handoffs cite it, not `gh pr checks` or one run ID.
- **A5. Your call on the reason line:** keep it, with `Bypass reason: wip` as a short form for deliberate
  work-in-progress merges; drop it for owner bypasses and have the audit print counts only; or leave it as written.
- A2 (change the workflow) was declined on 2026-11-21.

**Controls.** A4: on `d8cb0514` it lists three `merge-admission` runs, two cancelled and one success. A5: if the short
form is kept, the audit accepts `Bypass reason: wip` and still reports a bypass with no line.

**Recommended decision:** approve A4, and keep the reason line with the `wip` short form. With every merge this week a
bypass, one word per merge is what makes the audit readable.

**Decision:** `[ ]` approve A4, rule on A5 · `[ ]` A5 only · `[ ]` defer

---

## B — The suite lane is still not required (2)

`2026-10-02-full-suite-red-on-main-unseen`, `2026-10-03-shared-seam-change-merged-without-its-dependents`.

**Defect.** `suite-verdict` is not a required check, so a queue entry can merge with the suite red (#425 and #428 did,
on 2026-11-10).

**This week.** Ruleset 20822054 is unchanged (last updated 2026-09-11). The scheduled lane was green every night from
2026-11-16 to 2026-11-23. No update to `main` went through the queue, so B1 would have changed nothing this week: a
bypass skips required checks. On #439's head the suite went red after the merge.

**Proposed action (unchanged).**
- **B1.** Your ruleset edit: add `suite-verdict` to the required checks.
- **S8.** Close the twin entry, `2026-10-03-shared-seam-change-merged-without-its-dependents`, into the full-suite
  entry, which keeps the condition. Its PR-time selection has been live since #329.

**Controls.** B1: the ruleset readback lists `suite-verdict`, and the next queue entry reports it as required.

**Recommended decision:** approve B1 and S8. B1 only bites on merges that use the queue, and C1 should land first or
with it, since the writer-lock flake would otherwise eject queue entries.

**Decision:** `[ ]` approve B1 + S8 · `[ ]` S8 only · `[ ]` defer

---

## C — The writer-lock release raises after its work is done (2)

`2026-11-10-nightly-writer-lock-flake-closes-its-own-issue-untriaged`,
`2026-11-10-flake-verdicts-need-in-process-repeats-on-both-trees`.

**Defect.** The releaser in `research_system/store/anchor.py` (lines 1727 to 1731) re-checks the lock's name after
deleting its own file and raises `ConflictError("writer lock name was replaced during exact generation deletion")` when
a contender has already taken the name. The locked work has finished by then, so a successful operation is reported as
a conflict.

**This week: it recurred.** On 2026-11-20, #439's head `83176970` failed shard 3 of run 44811508964 with that error, in
`test_t2_authority_lock_domain_wins_before_revocation[AuthorizeProviderIssue]`
(`tests/research_system/unit/test_wp6_2_t2_runtime.py`; 1 failed, 574 passed). #439 had merged by bypass 32 minutes
earlier. `anchor.py` is unchanged on `main`.

**Proposed action (unchanged).**
- **C1. A defect task** (`tda-diagnosing-computational-defects`): force the order with two writers in one process on
  Windows (the first pauses after deleting its generation and before the name recheck; the second takes the name and
  holds it), then fix the release check. It goes through the queue with the affected-test selection.
- **C2. A flake-verdict line** in `tda-diagnosing-computational-defects`: a "flake" verdict on a red required check
  cites in-process repeats on the head and on the base, with counts.

**Controls.** C1: the forced order reproduces the `ConflictError` on current `main`; after the fix, the same test shows
the first writer releasing cleanly and the second writer's lock intact. C2: the next flake verdict carries both counts.

**Recommended decision:** approve C1 and C2.

**Decision:** `[ ]` approve C1+C2 · `[ ]` C2 only · `[ ]` defer

---

## D — W9 census and read-path coverage (4)

`2026-11-11-review-census-probed-only-the-named-evasions`, `2026-11-11-ars-legacy-show-failed-on-every-proposal-since-wp9-3-1`,
`2026-11-10-fallback-to-no-check-on-load-failure`, `2026-11-10-scope-item-missing-with-no-record-entry`.

**Defect.** Each instance is fixed on `main`; each entry's general check is not. The runtime-construction census
(`_Census` in `tests/research_system/contracts/test_w9_wp9_3_censuses.py`) follows `ImportFrom` aliases and plain
`Assign` only; no test runs `ars legacy show` over every projection collection; an unreadable foundation file leaves the
store "not named", so no binding check runs; no check holds a package record to its note's split list.

**This week.** WP9.4-1 and WP9.4-2 (#439, #443) added two `ars legacy` read commands, `adoption-status` and
`cited-families` (`research_system/cli.py`), each with its own integration test. `_legacy_show` and both censuses are
unchanged.

**Proposed action.**
- **D1.** The runtime census reuses the service census's name-binding resolver. Controls: `AnnAssign`, walrus and
  call-time `partial` fixtures for `LegacyRuntime` and `DiscoveryRuntime`, each failing today.
- **D2 (widened).** One read-only CLI test runs every `ars legacy` read command (`show` on one identity of each
  projection collection, plus `adoption-status` and `cited-families`) on a scratch store taken through a full flow.
  Control: a reducer that stores a datetime fails it.
- **D3. Your ruling** on the foundation skip: can an old checkout after an advance meet an unreadable or non-naming
  foundation file? If yes, a control runs that case and expects a refusal. If no, record it as a known limit beside R2.
- **D4.** Defer the scope-reconciliation lint to the Gate 7+ intake list with a new row; it needs a stable record
  format first.

**Recommended decision:** approve D1, D2 and D4, and rule on D3.

**Decision:** `[ ]` approve D1–D4 · `[ ]` some (name which) · `[ ]` defer

---

## E — Session and worktree setup that no one runs (4)

`2026-11-11-app-worktree-runs-the-main-checkouts-hooks-until-the-gate-is-run`,
`2026-11-11-fresh-worktree-uv-sync-omits-pytest`, `2026-11-13-fresh-worktree-pytest-absence-recurred`,
`2026-11-19-vault-bound-session-ran-in-a-cloud-container` (new to a packet).

**Defect.** Each of these is something a session needs from its environment and finds missing only when it needs it:
- a `core.hooksPath` that resolves into another checkout;
- a venv without pytest (missed three times despite `using-git-worktrees-extras`);
- and, new this week, the vault and the gitignored `results/` inputs. The P-085/P-086 session ran in a cloud
  container. It could not write its vault `[DECISION]` entries, which travelled to a local session as text. The
  pre-commit contract gate failed on tests that hash `results/trajectory_tda_integration/01_trajectories_sequences.json`,
  and you authorized `--no-verify` commit by commit. A later local run passed all 104 contracts.

**This week.** The WP9.4-2 and WP9.5 handovers spell out `uv sync --extra dev` and the `TEMP` workaround, a prose fix
per brief. This review provisioned its worktree with `uv sync --locked --all-extras` and checked that pytest and yaml
import first. Nothing checks any of the four conditions.

**Proposed action.**
- **E1.** Extend the SessionStart check (`tools/hook_currency.py`, which already runs in every checkout and now warns on
  a shallow repository) to report when `core.hooksPath` resolves outside the checkout or the checkout's venv cannot
  import pytest, naming the provisioning command.
- **E2.** `.githooks/pre-commit` refuses when the resolved hook directory is outside the worktree being committed in.
- **E3 (new).** The same SessionStart line reports when the vault path (or the `vault/` junction) or the `results/`
  inputs the contract gate hashes are missing, saying up front that vault entries will need a local handoff and commits
  will meet the gate.

**Controls.** E1: a fixture worktree with an absolute hooksPath to another checkout is reported, one whose venv lacks
pytest is reported, and a provisioned one is not. E2: with the guard in the selected hook, the absolute-hooksPath
fixture's commit is refused with a hooksPath diagnostic. E3: run with the vault path overridden to a missing directory
and it reports; with the real path it is quiet.

**Recommended decision:** approve E1 to E3. They share one line at session start, which already exists.

**Decision:** `[ ]` approve E1–E3 · `[ ]` E1+E3 only · `[ ]` defer

---

## F — Design-note claim discipline, round 3 (3)

`2026-11-11-note-claimed-a-tool-prints-what-its-inputs-cannot-determine`,
`2026-11-13-review-summary-list-dropped-a-reading-its-own-table-marks`,
`2026-11-16-extractor-rule-specified-twice-without-a-run-on-the-governed-files`.

**Defect.** Three lessons from the WP9.3 and WP9.4 notes with no text on `main`: "tool X prints Y" was not checked
against X's inputs; a summary list restating a table dropped a row; an extractor rule went unrun on the governed files
in two revisions.

**This week.** Unchanged. This PR's two checklist edits (composition, elided quotations) sit beside where F1 would go.

**Proposed action (unchanged).**
- **F1.** A checklist entry, "Output claims": for "X prints or produces Y", list what X may open and show Y is a
  function of it, including values fixed by a later step.
- **F2.** In `adversarial-design-review`'s "For Stephen" summary, generate the register-lines list from the readings
  table, or state that the two were compared.
- **F3.** A line in the ARS design-note template: a selector section links its script and census output, or the note is
  not ready for review. Defer a lint to the Gate 7+ intake list.

**Controls.** F1 and F2 are text; their evidence is the next design-note review. F3: revision 2 of the WP9.4 note fails
the template line.

**Recommended decision:** approve F1 to F3.

**Decision:** `[ ]` approve F1–F3 · `[ ]` F1+F2 only · `[ ]` defer

---

## G — Agent guards: fail-opens and other shells (2)

`2026-11-17-commit-state-guard-fails-open-and-discards-the-cause`,
`2026-11-17-shell-guards-do-not-match-the-mcp-shell-tools`.

**Defect.** `commit-state-guard` fails open about 0.8% of the time and its launcher sends the Python stderr to
`/dev/null`, so nothing records why. Both git-safety guards match `Bash|PowerShell` only; `mcp__terminal__run_in_terminal`
and Desktop Commander's `start_process` and `interact_with_process` reach git with no guard.

**This week.** 10 more `FAILOPEN(exit=0)` receipts, 2026-11-20T01:49Z to 2026-11-21T14:43Z, in five PreToolUse and
PostToolUse pairs. The matchers in `.claude/settings.json` (lines 36 and 83) are unchanged.

**Proposed action (unchanged).**
- **G1.** The launcher writes the exception's last line into the receipt or a sibling log, and the weekly review tallies
  fail-opens per hook. Then fix the error class the record shows.
- **G2.** Widen both matchers to the MCP shell tools, each guard reading that tool's command field; or deny git and gh
  through those tools in the permission settings.

**Controls.** G1: a payload that makes the Python raise records its exception type. G2: a PreToolUse payload for
`mcp__terminal__run_in_terminal` carrying `git commit --no-verify` is denied, and the Bash form still is.

**Recommended decision:** approve G1 and G2.

**Decision:** `[ ]` approve G1+G2 · `[ ]` G2 only · `[ ]` defer

---

## H — Commits that reach no PR (2)

`2026-11-17-review-fixes-pushed-after-their-pr-merged`,
`2026-11-17-register-lint-flags-branches-carrying-an-open-prs-register-bytes`.

**Defect.** A push to a branch whose PR has merged attaches to no PR and gets no CI or review (#428, 2026-11-10). The
register-reachability lint reports a review branch carrying an open PR's register text as stranded.

**This week.** No recurrence. Each of the 11 PRs merged since 2026-11-17 has its branch tip at its merged head, and
WP9.4-2's review fixes went through new PRs (#446, #448). H2's three false findings cleared when #437 merged; today's
run reports 0 stranded and 4 pending in open PRs #449 and #451, all true.

**Proposed action (unchanged).**
- **H1.** `.githooks/pre-push` checks `gh pr list --head <branch>`: allow if an open PR exists; refuse if the branch has
  a merged PR and no open one, naming the follow-up PR to open.
- **H2.** `check_register_reachability.py` reports a branch whose register blob equals an open PR head's as pending in
  that PR, and one equal to `origin/main`'s as landed.
- **H3. Your call:** may a PR under an independent review enter the queue before the review's disposition is on its
  head?

**Controls.** H1: a push passes with an open PR, and is refused with only a merged PR. H2: a fixture branch with an open
PR head's blob is pending; one that differs is still stranded.

**Recommended decision:** approve H1 and H2, and rule on H3.

**Decision:** `[ ]` approve H1–H3 · `[ ]` H1+H2 only · `[ ]` defer

---

## I — zktheoryweb: a forbidden map is tracked (1)

`2026-11-17-zktheoryweb-org-to-link-map-tracked-despite-rule`.

**Defect.** `docs/snapshots.md` and `scripts/snapshots/schedule.mjs` say the repository must never hold the
organisation-to-link map, and `tools/snapshots/charity_snapshot_links.csv` holds one. The only guard checks
`schedule.json`.

**This week.** Unchanged: the CSV is still tracked on zktheoryweb `origin/main` (`b74f270`).

**Proposed action (unchanged).** **I1.** A test in `scripts/snapshots/snapshots.test.ts` that fails when any tracked
file outside `public/s/` pairs an organisation-like column with a `/s/<token>/` path. **I2. Your call:** move the CSV
out of the repository, or relax the rule for a private repository.

**Controls.** I1: a temporary fixture CSV with both columns fails the test; the tree passes once the CSV moves (or the
rule is relaxed and the test scoped to match).

**Recommended decision:** approve I1 and move the CSV out. This goes through zktheoryweb's own PR.

**Decision:** `[ ]` approve I1, move the CSV out · `[ ]` approve I1, relax the rule · `[ ]` defer

---

## J — zktheoryweb: deploy and retire checks that live in one session (2)

`2026-11-17-edge-bundle-passed-locally-but-manifest-validation-failed-on-netlify`,
`2026-11-19-snapshot-retire-needs-netlify-creds-not-provisioned`. Both new to a packet; checked read-only.

**Defect.**
- **The edge manifest.** An edge function declared `method: ['GET', 'HEAD']`. Vitest, the build and a local
  `@netlify/edge-bundler` `bundle()` all passed, and the Netlify deploy failed twice: the manifest schema has no `HEAD`.
  `bundle()` does not validate the manifest; `@netlify/build` calls `validateManifest()` separately. There is still no
  check that runs it.
- **Skipped prunes.** Retiring wave 1 (#55, 2026-11-19) ran with `--skip-counts`, because `NETLIFY_SITE_ID` and
  `NETLIFY_AUTH_TOKEN` were set nowhere a session could see. The privacy notice promises that a link's count is deleted
  with the link. `scripts/snapshots/opens.mjs` prints the leftover count and the `--prune-counts` command, but only when
  someone runs the opens report, which needs the same credentials. Each wave retired this way grows the backlog with no
  signal.

**Proposed action.**
- **J1.** `scripts/check-edge-manifest.mjs`: bundle `netlify/edge-functions` and call `validateManifest()` on the
  result. Run on demand or pre-push (it fetches Deno once, about 100 MB, so not in `npm run test`).
- **J2.** `--skip-counts` writes the skipped tokens to a tracked `pending-prune.json` (tokens only, which are already
  public in the URLs), and the build warns while it is non-empty; `--prune-counts` clears it.

**Controls.** J1: a manifest with `method: ['HEAD']` is rejected with Netlify's error (reproduced by hand on
2026-11-17), and the current functions pass. J2: a `--skip-counts` dry run writes the record and the build warns; after
`--prune-counts` the record is empty and the build is quiet.

**Recommended decision:** approve J1 and J2. Provisioning the two variables in the gitignored `.env` is the
alternative to J2, but it keeps the promise only while every retiring session has them.

**Decision:** `[ ]` approve J1+J2 · `[ ]` J1 only · `[ ]` defer

---

## K — The design-note review loop (2)

`2026-11-22-review-loop-briefs-prescribe-unreviewed-designs`,
`2026-11-20-ellipsis-over-governing-rule-dropped-a-requirement` (its change-log limb). Both new to a packet.

**Defect.**
- **Prescriptions go unattacked.** In the WP9.5 note loop, every round's Majors from r2 on sat in machinery the previous
  round added, and from r4 on that machinery was prescribed by the reviewing session's own follow-up brief (R4-M1,
  R5-M1, R5-M2). The author built what the brief said, and the next review found the holes.
- **Credited claims with no citation.** WP9.4's revision 6 credited a point to "the review's statements" that the review
  never made (R6-i4).

**This week.** The loop ran r6 and r7 (REWORK REQUIRED) and r8 (CONFIRM WITH FINDINGS, 2026-11-23), on PR #449. Half of
the suggestion happened in practice: the r6 brief recorded the pin design as your decision of 2026-11-22, and P-090
puts owner points A to K to you. The other half did not: the r6 and r7 briefs still specify mechanisms for the author
to build (the r7 brief's candidate built from the merge ref or a `git commit-tree` squash). The ellipsis limb of the
second entry is now covered by this PR's "Elided quotations" entry.

**Proposed action.**
- **K1.** A follow-up brief that prescribes a mechanism, not only a correction, either gets a short independent
  adversarial pass before it goes, or labels the mechanism "candidate: attack it". A line in `adversarial-design-review`
  where it describes follow-up briefs.
- **K2.** After two rounds whose Majors fall in the same subsystem, stop revising prose and put the subsystem to you as a
  decision, with options and residual risks. WP9.5 did this at r6; make it the rule.
- **K3.** A claims-checklist Author line: a change log that credits a correction to the review cites the review's
  committed line. Then close the ellipsis entry.

**Controls.** Text items. Their evidence is the next note loop: the share of Majors that fall in brief-prescribed
machinery, the round at which a repeating subsystem goes to you, and a review citation on every credited correction.

**Recommended decision:** approve K1 to K3.

**Decision:** `[ ]` approve K1–K3 · `[ ]` some (name which) · `[ ]` defer

---

## L — Two guards that pass without covering (2)

`2026-11-24-notation-guard-misses-the-unicode-subscript-the-papers-use` (new),
`2026-11-24-dispatch-readiness-guard-watches-a-path-dispatch-no-longer-takes` (new). Both from this review's spot check.

**Defect.**
- **The notation guard misses `W₁`.** It denies ASCII `W_1` and `W_{1}` in `papers/` prose. The papers write the metric
  as Unicode `W₂` (`git grep -c "W₂" -- papers` hits `_project.md`, a draft table and several notes). Run directly on a
  payload (read-only, no receipt), the hook allowed "the W₁ distance" in `papers/P01-A-JRSSA/drafts/x.md` and denied
  the same text written `W_1`. It also ignores a MultiEdit's `edits[]` though its matcher names MultiEdit, and nothing
  checks script writes, since pre-commit has no notation check. No `W₁` is in `papers/` outside `papers/shared/` today.
- **The readiness guard watches a dead path.** It requires a passing Dispatch Readiness block in a Task Prompt written to
  `.apm/bus/<agent>/task.md`. Its only deny was a liveness probe on 2026-07-28, and no bus write has happened since; the
  newest bus `task.md` is from 2026-07-16. Dispatch now goes through the handover briefs in
  `docs/plans/agentic-research-system/handoffs/` (53 handoff writes in November). They carry the worktree, `.env` and
  `uv sync` steps as prose, and none of the 9 handovers carries a readiness block from
  `shared/manager_dispatch_check.py`.

**Proposed action.**
- **L1.** Widen the notation pattern to `W₁` (not followed by another subscript digit), read MultiEdit's
  `edits[].new_string`, and add the same check to pre-commit over staged `papers/**/*.{md,tex,txt}`.
- **L2. Your call:** (a) the handovers are dispatches: extend the guard to `handoffs/*-handover-*.md`, requiring a
  passing readiness block (follow-up briefs stay exempt); or (b) they are not: record that, and narrow or retire the
  guard.

**Controls.** L1: a `W₁` payload and a MultiEdit payload carrying `W_1` are each denied; `W₂` and `W₁₂` are allowed. L2
(a): a handover without the block is denied, one with a passing block is allowed, and a follow-up brief is allowed.

**Recommended decision:** approve L1, and L2(a). The handovers create worktrees, copy `.env` and sync venvs, which is
the setup the guard was built to check after the summer's compaction failures, and the readiness check (with its
hook-currency and shallow-repository lines) already exists.

**Decision:** `[ ]` approve L1 + L2(a) · `[ ]` L1 + L2(b) · `[ ]` defer

---

## M — Applied skill edits wait on the packet's decisions (1)

`2026-11-24-applied-skill-edits-wait-on-the-packets-decisions` (new, from step 0).

**Defect.** Each packet PR carries two things with different lifetimes: decisions that wait on you, and SKILL-lane edits
the review has already applied. #438's two edits have waited seven days on decisions they do not depend on. Sessions
that load skills from a `main`-based checkout, as the WP9.5 review branch does, read checklist 1.5.0. And this PR had
to stack on #438, because both change the same checklist entries, version lines and `tools/skill_sync_state.json`
hashes.

**Proposed action.**
- **M1.** From next week the review opens two PRs: a small one with the applied SKILL-lane edits, which can merge on
  review, and the packet. The research-observer step 7 and the task's step 11 change to match.
- **M2.** Or keep one PR, and let the packet merge as a record once its edits are reviewed, with decisions recorded
  afterwards in a follow-up.

**Controls.** By the following review, the applied-edit commit is on `origin/main`
(`git merge-base --is-ancestor <sha> origin/main`), whatever the state of the packet's decisions.

**Recommended decision:** approve M1. For now: merge #438, then this PR.

**Decision:** `[ ]` approve M1 · `[ ]` approve M2 · `[ ]` defer

---

## This review's closures

Each closing Status names its evidence and keeps the previous Status as a `Prior status:` line. They stay in full text
until the next review.

| Entry | Status | Evidence |
|---|---|---|
| `2026-11-19-fix-to-one-rule-made-another-clause-unreachable` | ACTIONED (SKILL) | This PR: "Prescribed corrections" in the claims checklist, `adversarial-design-review` 1.7.0 |
| `2026-11-20-ellipsis-quote-dropped-the-qualifier-the-fix-needed` | ACTIONED (SKILL) | This PR: "Elided quotations" in the claims checklist; named in `writing-plans-extras` 1.7.0 |
| `2026-11-20-main-checkout-went-shallow-and-reddened-the-06h-smoke-test` | ACTIONED | #440 `cd4e10ba` (base `main`): `_shallow_warning` in `tools/hook_currency.py`, the advisory in `shared/manager_dispatch_check.py`, controls in `tests/tools/test_hook_currency.py`. `git rev-parse --is-shallow-repository` prints `false` today |

The first two reopen if you revert this PR's edits.

## Simplification sweep

- **One lesson, one place.** Both of this week's SKILL lessons went into the shared claims checklist, and the
  composition lesson extended an existing entry rather than adding one. The checklist is 233 lines (212 on #438's
  head).
- **Fold twins.** S8 (Group B) and, once K3 lands, the ellipsis PROCESS entry into its applied SKILL twin. Two
  entries fewer, re-noted every week.
- **A guard to retire, perhaps.** If L2 goes (b), `dispatch-readiness-guard` and its bus path can go, and the
  bus-based APM skills (`apm-communication`, `apm-4-check-tasks`, `apm-5-check-reports`) become candidates to retire
  with it. This review proposes no removal before that ruling.
- **Archival keeps the log flat.** 11 entries archived. The OPEN count is 29: last week's 21, eight logged by other
  sessions since, and three new from this review, less this review's three closures.
- **No skill is proposed for removal.**

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
| E | 4 | 2026-11-11-app-worktree-runs-the-main-checkouts-hooks-until-the-gate-is-run · 2026-11-11-fresh-worktree-uv-sync-omits-pytest · 2026-11-13-fresh-worktree-pytest-absence-recurred · 2026-11-19-vault-bound-session-ran-in-a-cloud-container |
| F | 3 | 2026-11-11-note-claimed-a-tool-prints-what-its-inputs-cannot-determine · 2026-11-13-review-summary-list-dropped-a-reading-its-own-table-marks · 2026-11-16-extractor-rule-specified-twice-without-a-run-on-the-governed-files |
| G | 2 | 2026-11-17-commit-state-guard-fails-open-and-discards-the-cause · 2026-11-17-shell-guards-do-not-match-the-mcp-shell-tools |
| H | 2 | 2026-11-17-review-fixes-pushed-after-their-pr-merged · 2026-11-17-register-lint-flags-branches-carrying-an-open-prs-register-bytes |
| I | 1 | 2026-11-17-zktheoryweb-org-to-link-map-tracked-despite-rule |
| J | 2 | 2026-11-17-edge-bundle-passed-locally-but-manifest-validation-failed-on-netlify · 2026-11-19-snapshot-retire-needs-netlify-creds-not-provisioned |
| K | 2 | 2026-11-22-review-loop-briefs-prescribe-unreviewed-designs · 2026-11-20-ellipsis-over-governing-rule-dropped-a-requirement |
| L | 2 | 2026-11-24-notation-guard-misses-the-unicode-subscript-the-papers-use · 2026-11-24-dispatch-readiness-guard-watches-a-path-dispatch-no-longer-takes |
| M | 1 | 2026-11-24-applied-skill-edits-wait-on-the-packets-decisions |
| **Total** | **29** | |

---

## Lint and ledger check

| When | Tool | Result |
|---|---|---|
| Before this review's edits | `observation_log_lint.py --reachability . --close-conditions . --intake <list>` at `4ca375a3` | `329 observation(s): 29 OPEN`. Reachability: 43 hashes, 0 stranded, 3 not commits here. Close conditions: 0 naming PRs (7 name none). Intake: 5 checked, 0 without a row |
| After the edits | same | `332 observation(s): 29 OPEN`. Reachability: 37 hashes, 0 stranded, 4 not commits here (the new one is zktheoryweb's `b74f270`). Close conditions: 0 naming PRs (6 name none). Intake: 5 checked, 0 without a row |
| Register reachability | `check_register_reachability.py --repo .` | 424 unmerged branches, 0 stranded, 4 pending in open PRs #449 and #451, all true |
| Bypass audit | `check_bypass_merges.py --days 7` | 11 bypassed updates of 11, 44 problems: 11 without a reason line, 33 required checks not green at the merge (32 green later, 1 red). Group A |
| After the edits, `--packet` on this file | `observation_log_lint.py <log> --packet <this file>` | see the PR's test plan |

The log edit was made by a script that refused to write unless:
- the log matched its backup's SHA-256 and was CRLF throughout (as written back);
- the id order was unchanged, with the three new entries appended at the end;
- the OPEN set changed by exactly the three closures and the three new entries;
- every entry not named in the edit was unchanged apart from trailing whitespace;
- the lint's non-reachability checks came back clean.

**Archival.** The 11 entries the 2026-11-17 review closed on `main` evidence moved verbatim to
`archive/log-2026-11-24.md`, each with a stub in `log.md`. The two it applied in #438 stay in full until #438 merges.
DEFERRED entries stay in the log, since the `--intake` check reads them.

## Skills pass

**Inventory.**
- No repo skill changed on `main` since 2026-11-17. #438's head holds `adversarial-design-review` and
  `writing-plans-extras` at 1.6.0; this PR takes both to 1.7.0. `sync_agent_skills.py --check` on this branch: every
  synced skill IDENTICAL, `pack pins: 12 checked, 0 drifted`. `git grep` over `.research-system` finds no pack pin on
  either skill, and over `tests`, `tools`, `contracts` and `.github` finds no binding beyond `tools/skill_sync_state.json`.
- The research-observer and `weekly-system-review` instructions were followed as written. No edit this week. Group M,
  if approved, changes both.

**Cross-check of every OPEN group against the skills.**
- **A, B, H:** none. `tda-agent-safety-guardrails` covers agent bypasses; this week's were yours.
- **C:** `tda-diagnosing-computational-defects` (C2's line, C1's method).
- **D:** `contract-first-tdd` already asks for negative controls; D1 and D2 are tests.
- **E:** `using-git-worktrees-extras` holds the venv rule, and `vault-sync` and `tda-handoff` the vault close-out; E is
  their gate.
- **F, K:** `adversarial-design-review` and its checklist (F1, F2, K1, K3); the design-note template (F3); K2 is a loop
  rule for whichever session runs the loop.
- **G:** `tda-agent-safety-guardrails` could name the MCP shells once G2 lands.
- **I, J:** none; both are zktheoryweb tests or scripts.
- **L:** `wasserstein-audit` already scans `papers/` for both `W₁` and `W_1`; the guard is behind it. The APM skills
  are affected by L2(b).
- **M:** research-observer's step 7.

**The SKILL-lane entries.** Two OPEN entries were on the SKILL lane, and both were applied in this PR. No SKILL-lane
entry was escalated or skipped.

**Compliance against the active cross-cutting principles.**
- The composition line follows silent absence: a clause a sibling fix makes unreachable never errors, so only running
  the combined rule on the examples shows it.
- "Elided quotations" follows "metadata is suspicion, content is verdict": the quotation is the metadata, and the full
  sentence in the source decides.
- Both lessons went into the one shared checklist, with an author and a reviewer line each, as that file requires.
- Nothing adds, weakens or removes a gate.

## Gate-liveness spot check

Two gates last looked at on 2026-09-23, when the review confirmed the readiness guard fired and #303 then gave both
their controls. Neither has been checked for path coverage until now:

1. **`.claude/hooks/notation-guard.sh`** (PreToolUse on `Write`, `Edit` and `MultiEdit`).
   - Negative controls: `tests/tools/test_notation_guard_hook.py` and the hook's `--selftest`, run by admission-controls
     (`ci.yml` line 177).
   - Positive signal: 6,445 `allow` receipts in the main checkout's log since 2026-08-06, the latest today. Never a
     live deny.
   - Finding: it misses the Unicode form the papers use, MultiEdit's edits and script writes (Group L).
2. **`.claude/hooks/dispatch-readiness-guard.sh`** (same matcher).
   - Negative controls: `tests/tools/test_dispatch_readiness_guard_hook.py`, run by admission-controls (`ci.yml` line
     178).
   - Positive signal: 6,725 `allow` receipts, the latest today, and one `deny`, a liveness probe on 2026-07-28.
   - Finding: no write to its governed path since July; dispatch moved to the handover briefs (Group L).

The two control files passed: **22 tests**. `install-git-hooks.py` reports every required hook present and executable
in `.githooks`, in this review's worktree. The only probe was the notation hook run directly on two stdin payloads,
which reads and prints and writes nothing. Receipts were read with `grep -a`.

**Gates seen firing on live data this week:**
- **The bypass audit:** 11 bypasses and 44 problems, reported as counts.
- **The suite lane:** caught the writer-lock flake on #439's head; every nightly green.
- **SessionStart hook-currency:** reported this checkout level with `origin/main`. Its shallow warning (#440) has had no
  occasion to fire.
- **The observation-log lint:** clean before and after this review's edits.

**Suite runtime.** The longest shard per nightly ran 130 minutes on 2026-11-23 and 124 on 2026-11-16, with wide spread
between shards (10 to 130 minutes). No growth across the week, so nothing to escalate. Noted here so next week can
compare.

## Coverage question

"Did anything go wrong this week that no gate, contract or invariant caught?" Yes:

| What went wrong | Caught by | Observation |
|---|---|---|
| The writer-lock flake reddened #439's suite after it merged | the suite, too late to inform the merge | `2026-11-10-nightly-writer-lock-flake-closes-its-own-issue-untriaged` (C) |
| A session ran without the vault and the results inputs, and committed with `--no-verify` on your word | nothing at session start | `2026-11-19-vault-bound-session-ran-in-a-cloud-container` (E) |
| The WP9.5 note needed eight revisions, with Majors in machinery the briefs prescribed | the reviews, round by round | `2026-11-22-review-loop-briefs-prescribe-unreviewed-designs` (K) |
| Wave 1's snapshot counts were left undeleted with no record | the session, by hand | `2026-11-19-snapshot-retire-needs-netlify-creds-not-provisioned` (J) |
| A Netlify deploy failed on a manifest that passed locally, twice | Netlify | `2026-11-17-edge-bundle-passed-locally-but-manifest-validation-failed-on-netlify` (J) |
| A notation guard that cannot see the papers' own notation, and a readiness guard on a dead path | this review's spot check | Group L |
| Last week's applied skill edits have not reached `main` | this review's step 0 | `2026-11-24-applied-skill-edits-wait-on-the-packets-decisions` (M) |

None is a numerical or statistical failure, so none is a new invariant-battery item.

## This review's actions

1. Found the previous packet (#438, open) and re-resolved its nine groups against `origin/main` (`4ca375a3`), including
   the owner revision of 2026-11-21.
2. Ran `git fetch origin`, the observation-log lint with `--reachability`, `--close-conditions` and `--intake`, the
   register-reachability lint and the bypass audit, before and after the edits.
3. Read the ruleset, the scheduled suite runs and their shard times, #439's failing shard log, the fail-open receipts,
   the guard matchers, the merged PRs' branch tips, and the WP9.5 note branch and its briefs.
4. Read zktheoryweb `origin/main` for Groups I and J, and checked MathUni, Counting Lives and codex_workflow for new
   material (none for the log).
5. Spot-checked two guards, probed the notation hook on two read-only payloads, and ran both control files (22 passed)
   and `install-git-hooks.py`.
6. Created this branch on #438's head in the linked worktree `.claude/worktrees/system-review-2026-11-24`, merged
   `origin/main`, and provisioned it with `uv sync --locked --all-extras`.
7. Edited the claims checklist, `adversarial-design-review` and `writing-plans-extras` in `.agents/skills/`, synced and
   checked the mirror.
8. Closed 3 entries, added 13 Progress notes, logged 3 observations and archived 11, through one checked script. Backup:
   `~/.claude/skill-updates/2026-11-24/log/log.md.before`.
9. Updated `last-review-date.txt` to `2026-11-24`.
10. Opened this packet as a PR.
