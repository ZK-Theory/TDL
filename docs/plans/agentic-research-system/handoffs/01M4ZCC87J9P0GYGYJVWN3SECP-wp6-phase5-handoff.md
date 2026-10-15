# WP6 Gate 6 Phase 5 handoff: the delta assurance, the fresh store and the bounded live run

**Capability status:** INCOMPLETE. The historical real SPEC run is PROVEN; the complete public Gate 6
implementation is not integrated on main. Phase 5 prep construction is complete: #348 to #352 are merged, and
an integrated packet certified main `bbdcb068` (P-058, "Prep construction complete (2026-10-15)").

**Dispatch state:** ready for Stephen's explicit dispatch. Two decisions in that P-058 entry come first:
- the PR-B naming rule;
- whether the integrated packet counts toward the delta assurance's selection.

The first deliverable is the delta assurance. Nothing live happens before Stephen records it.

**Recommended model:** the strongest available reasoning model, at `xhigh`.

**Predecessors:** `handoffs/01M4AJCXSVTDDDDAYZTZWZ9AQK-wp6-phase5-prep-handoff.md` (prep) and
`handoffs/01M4677SY7MNV0FA274DM87YME-wp6-phase4c-assembly-handoff.md` (4c). Their mechanics and hard boundaries
still apply, except where this handoff updates them.

## Handoff prompt

You are the primary executor for **06s Gate 6 Phase 5**: KAN-110's exit (the delta assurance), then KAN-103's
remaining Phase 5 steps, in `C:\Users\steph\TDL`.

### Start identity

1. Refresh `origin/main`. It must contain `bbdcb068` (#352) and the prep close-out docs PR that added this file.
   Record that exact SHA as **M1** before the first write.
2. Create one clean linked worktree under `C:/Users/steph/` for docs and evidence work. Copy the primary
   checkout's `.env` into it, run `uv sync --locked --extra dev` and prove that pytest runs there.
3. Before any write, verify:
   - the working directory;
   - the symbolic branch and HEAD;
   - a clean status;
   - ancestry from M1.

### Read first

1. `implementation/06s-phase5-runbook.md`. It is the live sequence, the actor plan, the bootstrap and step 3's
   order of operations, updated 2026-10-15 for the merged code.
2. `03-decisions-and-open-questions.md`, P-058 from "Phase 5 prep design decisions (2026-10-07)" to "Prep
   construction complete (2026-10-15)". It holds P5-1 to P5-12, the census, PR-A's decisions, the P5-7 amendment
   and the close-out.
3. `implementation/06s-phase5-prep-design-pass-2026-10-07.md` §4 (A1 to A7) and
   `implementation/06s-phase5-prep-census-2026-10-07.md`.
4. `implementation/06s-gate6-delivery-replan-and-gate7-integration.md`: Phase 5, with every P-058 amendment.
5. `reviews/06s-phase4c-boundary-review-e5179b57-2026-10-07.md`: B-1, M-1 and M-2.
6. The known limits and review rounds in the PR descriptions of #348 to #352.

### Scope, in order

1. **The delta assurance (P5-12; KAN-110's exit).** No live operation.
   - **The selection.** Follow Stephen's decision:
     - **Option A:** the 57 nodes of the 4c selection that the integrated packet did not run;
     - **Option B:** the full 4c selection (310 nodes) plus the prep selection (607 nodes), de-duplicated, on M1.

     Build the node list by collection at M1. Derive the new nodes from the diff, never by hand. Reconcile every
     node against JUnit.
   - **The window and budget.** Run in the 02:00–11:00 window under P-058's budget, with a machine check
     recorded before the window.
   - **The network probe.** Propose to Stephen running the opt-in probe
     `test_spec_source.py::test_neurips2024_exact_public_registration` once with `ARS_SOURCE_NETWORK_PROOF=1`. It
     is read-only public Git, with no credentials, against the step 3 source. Run it only if he agrees.
   - **The fresh-context review.**
     - Write its brief, scoped to the `e5179b57..M1` diff. It must confirm closed: B-1, B-2 and B-3; M-1 and M-2;
       and the SPEC-01 rule and bar.
     - Stephen dispatches the reviewer. You do not review your own construction.
   - **Hand back** the results for Stephen to record. KAN-110 closes on his record.
2. **A0, Stephen's decisions for the run** (runbook §0 and §2). Prepare them, without executing anything:
   - the owner actor and the allocated actor plan (runbook §1);
   - the authority bootstrap manifest and its digest;
   - the paid-run subset and cost ceiling (D6).
3. **The live sequence L1 to L7** (runbook §3). Each A# is prepared exactly, authorized by Stephen on its own,
   run alone, and verified from durable state before the next.
   - **PR-F, the re-pin,** is a docs-and-config PR that Stephen merges, giving M2.
   - **L5, the delta assurance on M2.** Propose its scope before L4. M2 is M1 plus the foundation and its
     contract test, so a re-pin-scoped selection plus that diff's review may be enough. That is Stephen's call.
4. **Step 3, the bounded run** (runbook §4), then **steps 4 to 6** (runbook §5), each under its own
   authorization.

### Mechanics

- **The runner.** `C:/Users/steph/.codex/tmp/g6-p5prep/certify_prep.py` is the 4c runner adapted for prep.
  - It takes a SHA, a label, a worktree and a collected node list. `--now` skips the window, and only on
    Stephen's say-so.
  - It is resumable, reconciles every node against JUnit and records the budget flags.
  - Copy it next to your evidence. Do not edit it in place.
- **Known runner traps** (observations 2026-10-07 to 2026-10-15):
  - **The app restart.** A terminal tab dies when the app or session restarts. After any resume, check
    `waiting.json`/`started.json` and the live runner processes, and relaunch if needed.
  - **Interrupted results.** Stopping the runner with Ctrl-C writes result files for the groups it interrupts.
    They show exit 1/2, `KeyboardInterrupt` or "no tests ran", and a resume trusts them. Before resuming, move
    any such result aside.
  - **A run proves nothing on environment failure.** "Git inspection is unavailable (timed out)" appears under
    load. Do not overlap heavy runs. A mutation control holds only when its failure is the one the guard
    causes.
- **Durations.** The SPEC-01, SPEC-02 and spike-outcome public-path tests take 30 to 70 minutes each.
  `p14-spec_spike_outcome-2` exceeded the 60-minute group budget once (69.7 min).
- **The Candidate ID.** Step 3 derives it with a read-only Python call (`spec_source.source_ids`). There is no
  CLI for it.
- **The CI suite lane is red on main** (P-058, 2026-10-15): the nightly's failures are outside the
  known-failures list and are not prep regressions. The delta assurance runs locally. Do not treat CI red as
  evidence either way, and do not fix it inside Phase 5.
- **Commits.** The 4c mechanics still apply:
  - commit with `git commit -F`, never piped;
  - throwaway detached worktrees for mutation controls;
  - a head Codex did not review is recorded as such.

### Hard boundaries

- **Live work.** Each live operation (A1 to A7, step 3's effects, backup and restore) is prepared exactly and
  authorized separately by Stephen. Nothing in this handoff authorizes one. No provider, paid or credential
  work beyond the subset and ceiling Stephen sets at A0.
- **The live store.** `C:/Users/steph/TDL-ARS-WP64-Control` stays historical evidence. Never append to it
  (P-057, P-058).
- **The successor binding.** None until the delta assurance passes and Stephen records it.
- **The durable checkout.** `C:/Users/steph/TDL-ARS-G6-Checkout` stays clean and frozen once bound: nothing is
  pulled into it and no worktree is added (P5-5).
- **No new structures.** No new plan, framework, persisted model, composite seal or speculative STORE change
  (D5). No replacement of `SpecOperatorConfig@1.0.0` without Stephen's decision.
- **The results directory.** No toy or synthetic output in `results/`.
- **Hooks, reviews and merges.**
  - Never bypass hooks.
  - Stephen controls CodeRabbit, merges and auto-merge.
  - Do not apply a review stopping rule to a PR until Stephen accepts it for that PR.
- **06t (P-060).** Out of scope until Gate 6 closes.

### Handback

Lead with the applicable 06s §8 row. Then give:
- the exact SHAs (M1, and M2 once it exists);
- the delta assurance evidence and the review brief;
- each authorized live step with its durable verification;
- the decisions Stephen needs to make;
- verified Jira changes.
