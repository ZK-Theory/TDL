# 06s Phase 5 delta assurance: fresh-context review of `e5179b57..M1` (brief)

**Status:** DRAFT for Stephen. Stephen decides who or what runs it.
**Jira:** KAN-110 (its exit). **Plan:** 06s Gate 6, Phase 5 prep → Phase 5, P-058 P5-12.

## Your role

You are an independent, adversarial reviewer with fresh context. You did not build the Phase 5 prep, and you
must not try to recover the conversation or session history of the campaign that built it. Judge one exact
diff between two commits against the written contracts below. You are not reviewing a pull request. You are
deciding whether the findings the 4c boundary review and the prep census raised are closed on main, so the
fresh store can be reserved, initialized and bound.

## Subject

- Repository: `C:\Users\steph\TDL`.
- **Base:** `e5179b57811f74346707a4fe5fe7c407772cb3dc`, the commit the 4c boundary review judged.
- **Head (M1):** `100730e0319ff975116fb1e18eb897f46d81a627`, main after #354.
- **Diff:** `git diff e5179b57 100730e0`. The prep code is #348 (PR-A), #349 (PR-B), #350 (PR-D), #351 (PR-G)
  and #352 (PR-C). `bbdcb068..100730e0` is documentation only.
- **Your worktree.** Create a detached one at M1:
  `git worktree add --detach C:/Users/steph/TDL-p5-review 100730e0`. Copy `C:\Users\steph\TDL\.env` into it and
  run `uv sync --locked --extra dev` there.
- **Places to leave alone:**
  - the primary checkout;
  - `C:/Users/steph/TDL-g6-p5`, where the delta assurance runs and which must stay clean;
  - `C:/Users/steph/TDL-ARS-G6-Checkout`, which must never become a linked worktree (P5-5);
  - every `C:/Users/steph/TDL-ARS-*` root.

## What you must confirm closed

For each item, say **closed**, **closed with a residual** (name it), or **open** (give the reachable failure).

1. **B-1 (4c review, Blocking): a fresh store cannot enter the committed foundation before `store init`.**
   - **The fix:** P5-1, `ars store reserve` (`research_system/cli.py`, `research_system/authority.py`
     `initialize_authority_control_store`). It stops after the witness is persisted and prints the exact
     foundation fields. The re-pin is then committed (PR-F), and the unchanged `store init` runs.
   - **What M1 cannot show.** The re-pin is not on M1. It lands as PR-F after the live reservation (runbook
     §3, L3 to L6). Judge whether the **mechanism** closes B-1:
     - Does `reserve` then the re-pin then `init` yield an identity and witness digest equal to the pins?
     - Can a reservation be consumed twice, or by a different bootstrap?
     - Does a partial reserve leave a state that `init` misreads?
   - **Also check B-1 (c).** The 4c review found that a foundation re-pin counts as a configuration change, which
     the binding refuses as a documentation-only successor. Under P5-3 the first binding happens after the
     re-pin, at M2. Confirm that nothing on the L1 to L7 path still needs a binding to survive a
     configuration change.
2. **B-2 (design pass, Blocking): a freshly initialized store has no first binding.**
   - **The fix:** P5-3, the owner action `bind-initialized-store` under `RepairStoreBinding` 1.1.0, with the new
     object schema `StoreBindingInitial` 1.0.0 and the event `StoreBindingRepaired` unchanged:
     - `research_system/store/binding_service.py`;
     - `research_system/store/current_binding.py` (`_is_initial_binding`, `load_current_binding`);
     - `.research-system/schemas/wp6-6/gate6-binding-repair/`.
   - **What to confirm.** Only a never-bound, initialized store can take this action. These refusals hold on
     the public route:
     - a second first binding;
     - a restore under an initial binding;
     - the initial action on a restored store;
     - `spec status` before the binding.
   - **Replay and records.** Replay and every closed SPEC record schema that cites
     `governed_code_subject.event_type` accept the initial binding.
3. **B-3 (census, Material): the owner decision `ActivateAuthorityGrant` verifies has no public writer.**
   - **The fix:** PR-G, `ars authority activate-grant` (`research_system/cli.py`).
   - **What to confirm:**
     - it writes the owner decision only after grant-scope and time validation pass;
     - a refused request leaves nothing written;
     - a changed request under a used grant ID is refused;
     - admission is unchanged.
4. **M-1 (4c review, Material): every Phase 5 invocation needs one durable, clean, non-linked checkout.**
   - **The fix:** P5-5, the procedure and runbook, plus reserve's refusal from a checkout with linked worktrees.
   - **What to confirm:**
     - the code accepts the dedicated non-linked clone as code root and schema root;
     - the runbook sequence keeps that checkout clean and at the bound head from L7 through step 6;
     - no step writes inside the checkout. Check especially where `--foundation-output`, the bootstrap file,
       the operator configs and `uv sync` put files.
5. **M-2 (4c review, Material): SOURCE `production` references are caller-asserted.**
   - **The fix:** PR-B, `verify_source_production` and `_lineage_candidate` in
     `research_system/discovery/spec_source.py`, called from `research_system/discovery/spec.py`. This follows
     P5-7 as amended on 2026-10-07 and the naming rule Stephen confirmed on 2026-10-15 (P-058).
   - **What to confirm:** before any write, `observe_source` and `correct_spec_01_source` refuse unless all of
     these hold:
     - the Task has exactly one started Attempt, and it is running;
     - the Task is unamended since dispatch;
     - the dispatch, Attempt, context packet, code commit and environment fingerprint equal the ledger's;
     - the Task names only Candidates that SOURCE observations citing it derive;
     - every link of a lineage cites the same Task.
   - **Known limit, not to be re-raised:** producer profile, branch, worktree and accepted scope stay caller
     strings.
6. **The SPEC-01 rule and bar (P5-8, P5-9).**
   - **The fix:** PR-C.
     - `research_system/discovery/rules.py` (`_spec_01_recommendation`, `evaluates_spec_01_rule`, and
       `_assay_scorecard_matches`) evaluates the rule in W11 admission. It is keyed by the rubric's algorithm
       ID, version and descriptor hash.
     - `research_system/discovery/spec_assay.py` (`_scored_under_spec_01_rule`, `_refuse_blocked_promote`)
       checks the same predicate on the frozen rubric the scorecard binds.
     - The committed rubric and scope content are under
       `.research-system/contracts/wp6-6/spec-gate6-run-v1/`. Their author is a dedicated non-owner actor.
   - **What to confirm:**
     - topology failing gives KILL;
     - any further PROMOTE requirement failing gives PARK;
     - PROMOTE needs Axis 2 + Axis 3 ≥ 4 with neither zero;
     - no other rubric is evaluated under this rule;
     - a scorecard cannot record a recommendation admission would not compute;
     - author, reviewer and acceptor cannot collapse.

## Also in the diff (check for a broken guarantee only)

- **PR-D (#350, P5-10).** `adopt_default` is refused after a Spike PROMOTE (`spec_result.py`), though the intent
  schema keeps it in its closed enum.
- **The protected surfaces.**
  - The 06h census's runtime-binding digest moved to `f359855b…` (PR-A, needs Stephen's re-acceptance as
    P-059 did).
  - The 06h append manifest changed.
  - The schema registry changed.
- **The SYS changes.** CI history checkout (#344), the pre-commit ruff pin (#345) and `CONVENTIONS.md`. Report
  only if one alters a route guarantee or a gate's liveness.

## Contracts to judge against (in this order of authority)

1. `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`, P-058: every block from "Phase 5
   prep design decisions (2026-10-07)" to "Prep construction complete (2026-10-15)", including the P5-7
   amendment and the 2026-10-15 decisions.
2. `docs/plans/agentic-research-system/implementation/06s-phase5-prep-design-pass-2026-10-07.md` (§2 and §4)
   and `implementation/06s-phase5-prep-census-2026-10-07.md`.
3. `docs/plans/agentic-research-system/implementation/06s-gate6-delivery-replan-and-gate7-integration.md`:
   §3 (D1 to D6), §4 (items 1 to 7), §5.0, and Phase 5 with every P-058 amendment.
4. `docs/plans/agentic-research-system/reviews/06s-phase4c-boundary-review-e5179b57-2026-10-07.md`: the
   findings as raised.
5. `docs/plans/agentic-research-system/implementation/06s-phase5-runbook.md`: the sequence the fixes must
   support.
6. The PR descriptions of #348 to #352, including their numbered known limits and review rounds.

## Blocking criteria (06s §5.0)

A finding blocks the successor binding only if it is one of:
- an exact-head reachable failure of §4;
- durable corruption or mispublication;
- replay divergence;
- an authority, owner or paid gate bypass;
- a failure of an applicable mandatory gate.

Everything else is Material, Minor or Info.

## Rules

- **Read-only.**
  - No live store, no provider, paid or credential work, no network probe.
  - No successor binding, no commits, no pushes.
- **Tests.** You may run fast tests on scratch stores in your own worktree (`-m "not slow"`). The slow
  public-route tests, including `test_fresh_store_public_procedure.py`, passed in the integrated prep packet at
  this tree (`C:/Users/steph/.codex/tmp/g6-p5prep/prep-b09813e6/`). Read their JUnit and logs rather than
  re-running them.
- **Timing.** Do not run tests while the delta assurance is running. It is running if
  `C:/Users/steph/.codex/tmp/g6-p5/delta-100730e0/started.json` exists and `results.json` does not. Load has
  caused environment failures before.
- **Demonstrating a finding.** Prefer a minimal reproduction on a scratch store, and say how you reproduced it.
- **Out of scope:**
  - test cost and runtime;
  - style;
  - 06t (P-060);
  - Gate 7;
  - redesigns of STORE or admission (D5);
  - the red CI suite lane (P-058, 2026-10-15).

## Output

Write one Markdown report to `C:/Users/steph/.codex/tmp/g6-p5/delta-review-e5179b57-100730e0.md`. Do not
overwrite an existing file there; add a date suffix instead. It must contain:

1. **Verdict:** PASS (no blocking finding) or FAIL, in one line, naming both SHAs.
2. **Closure table:** items 1 to 6 above, each closed / closed with a residual / open, with `file:line` at M1
   and the evidence (quoted code, a test with its JUnit record, or a reproduction).
3. **Findings table,** most severe first. Give for each:
   - an ID and its severity (Blocking / Material / Minor / Info);
   - the contract clause;
   - `file:line` at M1;
   - the reachable path as a concrete action sequence;
   - the evidence;
   - a proposed disposition: fix before L3 / fix before L7 / known limit / decline;
   - your confidence.
4. **Coverage:** every changed production file in `e5179b57..100730e0`, with what you examined, or "no finding".
   Report an unexamined file as unexamined, not as passing.

The executor records a disposition for each finding with Stephen. A defect goes to Stephen as a decision. The
delta assurance changes no production code.
