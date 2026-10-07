# 06s Phase 4c: independent exact-main boundary review of the integrated SPEC route (brief)

**Status:** DRAFT for Stephen. Stephen decides who or what runs it.
**Jira:** KAN-109. **Plan:** 06s Gate 6, Phase 4, sub-phase 4c.

## Your role

You are an independent, adversarial reviewer. You have not worked on this route, and you must not try to
recover the conversation or session history of the campaign that built it. Judge the code at one exact
commit against the written contracts below. You are not reviewing a pull request. You are deciding whether
the integrated route is fit to be bound as the live successor, the first step of Phase 5.

## Subject

- Repository: `C:\Users\steph\TDL`. Review the exact commit
  **`e5179b57811f74346707a4fe5fe7c407772cb3dc`** (main after #338). Create your own detached
  worktree of that commit (for example `git worktree add --detach C:/Users/steph/TDL-4c-review e5179b57`),
  copy `C:\Users\steph\TDL\.env` into it and run `uv sync --locked --extra dev` there. Do not use or touch
  `C:/Users/steph/TDL-06s-phase4c`: the assembled selection is running in it, and it must stay clean. Do not
  use the primary checkout either. Do not review a moving branch.
- Production surface: `research_system/discovery/spec.py`, `spec_assay.py`, `spec_result.py`,
  `spec_task.py`, `spec_source.py`, `spec_replay.py`. Also the seams they call:
  `DiscoveryRuntime.submit`, `CommandService.submit`, `replay_discovery`,
  `verify_restore_before_writer_lease`, the shared verified-binding loader and `SpecOperatorConfig@1.0.0`.
- Platform changes merged since the last SPEC certification (`e7b8f1da`), which the route now runs on:
  #313 (`run_git` names its cause), #322 (new-command-id retry conflict limited to C1 commands),
  #324 (identical authority initializers converge), #325 (research_system tests' own foundation),
  #333 (origin-witness path comparison), #341 (approved schema roots and binding candidates refused in
  disposable checkouts, so binding advance and repair must run from the main checkout).

## Contracts to judge against (in this order of authority)

1. `docs/plans/agentic-research-system/implementation/06s-gate6-delivery-replan-and-gate7-integration.md`:
   §3 (D1–D6), **§4 (the finite closure contract, items 1–7)**, §5.0, Phase 4 and Phase 5 with every
   P-058 amendment.
2. `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`: P-051 to P-058, every block
   of P-058 in order (the newest are "4b-2b design decisions (2026-09-25)" and "Test-cost decisions
   (2026-10-01)").
3. `docs/plans/agentic-research-system/implementation/06q-gate6-spec-real-run-integration-and-follow-up.md`
   §4 **Step 5** (`G6-SPEC-MODEL-1`), the retained SPEC action composition. P-058 amends it: it removes
   `bootstrap_dossier_authority`, `bootstrap_path_authority`, `admit_dossier` and the three brief-input
   actions, and the route adds `close_task`. The route's `ACTION_EFFECTS` holds 25 actions at the
   expected SHA. Where P-058 and Step 5 disagree, P-058 governs; report any disagreement P-058 does not
   explicitly decide.
4. The PR descriptions of #282, #286, #288, #290, #291, #292, #296, #297, #298, #309, #310 and #331.
   They record each sub-phase's route bindings, review decisions and **numbered known limits**.

## Questions

1. **Composition.** Does the route's action table, with each action's ordered effects, actors, grants and
   completion proof, match Step 5 as amended by P-058? Name every divergence and whether a decision
   covers it.
2. **Closure contract.** For each 06s §4 item that Phase 5 will rely on (items 1–6), can the integrated
   route produce it on a fresh store as Phase 5 describes? If not, give the reachable failure.
3. **Boundaries.** Can any of these happen on exact main through the public route?
   - an independent review or owner-only decision supplied by the wrong actor;
   - PROMOTE, SPEC-02 approval or a Spike start without its required predecessor;
   - a durable write before a refusal, a durable record that misstates what happened, or a mispublication;
   - replay of a route-written ledger that diverges from the live projection, from a fresh process;
   - a Task closed other than through SubmitForReview then AcceptTask;
   - a project-use result rendered as accepted before its independent review and use authority, or a
     PARK/no_spike result that implies empirical adoption.
4. **Platform interaction.** Does any of the six post-`e7b8f1da` platform changes alter a route
   guarantee? In particular, does #341 change what Phase 5 step 1 (successor binding) must do or where
   it must run?
5. **Known limits.** Is any recorded known limit reachable on the planned Phase 5 path in a way that
   falsifies a durable claim? Do not re-raise a recorded limit as new unless you argue exactly that.

## Blocking criteria (06s §5.0)

A finding blocks the successor binding only if it is one of: an exact-head reachable failure of §4;
durable corruption or mispublication; replay divergence; an authority, owner or paid gate bypass; or a
failure of an applicable mandatory gate. Everything else is Material, Minor or Info.

## Rules

- Read-only. No live control store (`C:/Users/steph/TDL-ARS-WP64-Control`), no provider, paid or
  credential work, no successor binding, no commits, no pushes.
- You may run fast tests on scratch stores: `-m "not slow"` over `tests/research_system/integration/test_spec_*.py`
  and `tests/research_system/unit/test_spec_replay.py`. Do not run the slow public-route tests; the
  assembled selection runs them separately. To demonstrate a finding, prefer a minimal reproduction on a
  scratch store, and say how you reproduced it.
- Out of scope: test cost and runtime, style, Gate 7, and redesigns of STORE or admission (D5).

## Output

One Markdown report, written to `C:/Users/steph/.codex/tmp/g6-4c/boundary-review-e5179b57.md` (do not
overwrite an existing file there; add a date suffix instead):
1. **Verdict:** PASS (no blocking finding) or FAIL, in one line, naming the exact SHA reviewed.
2. **Findings table**, most severe first: ID; severity (Blocking / Material / Minor / Info); the
   contract clause (§4 item, P-058 block or Step 5 row); `file:line` at the SHA; the reachable path as a
   concrete action sequence; evidence (quoted code, a test, or a reproduction); proposed disposition
   (fix before the successor binding / Phase 5 prep / known limit / decline); confidence.
3. **Coverage:** for each of the 25 actions and each §4 item 1–6, what you examined and "no finding"
   where none. An unexamined item is reported as unexamined, not as passing.
4. **Composition map:** the Step 5 → P-058 → `ACTION_EFFECTS` mapping you checked, with divergences.

The executor records a disposition for each finding with Stephen. A defect goes to Stephen as a decision;
4c changes no production code.
