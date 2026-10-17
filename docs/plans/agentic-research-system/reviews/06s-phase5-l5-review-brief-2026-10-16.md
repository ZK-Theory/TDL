# 06s Phase 5 L5: fresh-context review of the `100730e0..4d867d85` non-docs diff (brief)

**Status:** DRAFT for Stephen. Stephen dispatches the reviewer.
**Plan:** 06s Gate 6 Phase 5, runbook §3 L5 (A5). The scope is Stephen's decision of 2026-10-16 (P-058, "Live
steps A1 to A4, and the L5 scope").

## Your role

You are an independent, adversarial reviewer with fresh context. You did not build PR-F or the SYS PRs, and you
must not recover the session history of the campaign. You are deciding whether M2 is fit for `store init` (L6)
and the first binding (L7).

The diff from M1 to M2 was already reviewed up to M1. The prep diff `e5179b57..100730e0` passed its own review
(`reviews/06s-phase5-delta-review-e5179b57-100730e0-2026-10-15.md`). Judge only what changed after it.

## Subject

- **Repository:** `C:\Users\steph\TDL`.
- **Base:** M1, `100730e0319ff975116fb1e18eb897f46d81a627`.
- **Head:** M2, `4d867d85574dcf90300f059ab1fd52324be3c85a` (main after #365).
- **Your worktree:** `git worktree add --detach C:/Users/steph/TDL-l5-review 4d867d85`. Copy `.env` into it and
  run `uv sync --locked --extra dev` there.
- **Places to leave alone:**
  - `C:/Users/steph/TDL-g6-p5`, where the L5 selection runs;
  - the primary checkout;
  - `C:/Users/steph/TDL-ARS-G6-Checkout`. Never add a worktree from it.
  - every `C:/Users/steph/TDL-ARS-*` root. The fresh store is **reserved but not initialized**: one stage beside
    `TDL-ARS-G6-Control`, and the witness in `TDL-ARS-G6-Origin-Authority`.

## The diff under review (non-docs only)

| Path | From | What to judge |
|---|---|---|
| `.research-system/config/foundation.yaml` | #365 (PR-F) | Is it exactly the reserved foundation? Recompute that the file's sha256 is `0bf20c38…` and that `foundation_sha256` is the canonical digest of its other fields. It must name only the G6 control root, origin witness (`1a7aa957…`), store identity (`5e3b95a9…`) and the durable checkout as code and schema root. It is schema **1.0.0**, while the foundation it replaces was 1.1.0, with `schema_binding_activation_sha256`. Confirm that `store init`, `repair-binding --owner_action bind-initialized-store`, `load_current_binding` and `ApprovedProjectBinding.load` at M2 all accept a 1.0.0 foundation, and that nothing at M2 requires the 1.1.0 activation field for the fresh store. |
| `tests/research_system/contracts/test_foundation_origin_witness_contract.py` | #365 | Correct for after L6. Its value assertions match the foundation. |
| `research_system/evals/executors/release_tranche.py` | #358 | `Path(directory).resolve()` in `execute_s014` and `execute_s015`. Does it change any route guarantee or record? |
| `tests/research_system/integration/test_fresh_store_public_procedure.py`, `tests/research_system/unit/test_store.py` | #358, #364 | Test-only fixes (`switch -C`; a skip when the ACE precondition is absent). Does either weaken what the test proves on the operator machine? |
| `.claude/hooks/commit_state_guard.py`, `.claude/settings.json`, `.github/workflows/*`, `tools/*`, `.agents/skills/*`, `.claude/skills/*` | #357, #359 to #362, #364 | Confirm none of them touches the `research_system` package, `.research-system/` schemas or contracts, or anything the `ars` CLI loads at runtime. |

**Also confirm the stale record is harmless.** The WP6.4 `tda-scale-v1.0.1` to `v1.0.3` packs record the old
foundation as `current_exact` (pinned at commit `03107b48`). Confirm that no code or test compares that record
with the live file. The executor found none.

## Contracts (in order of authority)

1. P-058: "Phase 5 prep design decisions" to "Live steps A1 to A4, and the L5 scope", especially P5-1, P5-2, P5-3
   and P5-5.
2. `implementation/06s-phase5-runbook.md`, §3 L1 to L7, including "Where files go".
3. `implementation/06s-gate6-delivery-replan-and-gate7-integration.md`: §4, §5.0 and Phase 5.

## Blocking criteria (06s §5.0)

A finding blocks L6 or L7 only if it is one of:
- an exact-head reachable failure of §4;
- durable corruption or mispublication;
- replay divergence;
- an authority, owner or paid gate bypass;
- a failure of an applicable mandatory gate.

Everything else is Material, Minor or Info.

## Rules

- **Read-only.** No store init, binding or live CLI against any `TDL-ARS-*` root, no commits, no pushes, no
  network or provider work.
- **Tests.** You may run fast tests in your own worktree. Do not run tests while the L5 selection is running: it
  is running while `C:/Users/steph/.codex/tmp/g6-p5/l5/out/4d867d85-60ccf9d7/` holds a `started.json` but no `results.json`.
- **Out of scope:** test cost, style, 06t and Gate 7.

## Output

Write `C:/Users/steph/.codex/tmp/g6-p5/l5/review-100730e0-4d867d85.md`. Do not overwrite an existing file; add a
date suffix instead. It must contain:

1. **Verdict:** PASS or FAIL, naming both SHAs.
2. **Findings,** most severe first. Give each its severity, contract clause, `file:line` at M2, reachable path,
   evidence, proposed disposition and confidence.
3. **Coverage:** every non-docs path in the diff, with what you examined, or "unexamined".
