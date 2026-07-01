---
document: W0 legacy closeout and transition addendum
date: 2026-06-29
baseline_manifest: W0-legacy-closeout-transition-manifest-2026-06-28.md
review_commit: 33ab053e30fa5e564ac7cc999544dec2225e9ccb
status: current_state_addendum
implementation_authority: none
---

# W0 Legacy Closeout and Transition Addendum — 2026-06-29

## 1. Additive status

This addendum updates the dated state observations in the 2026-06-28 W0 manifest. It does not rewrite that snapshot, alter its source-precedence rules, migrate legacy evidence, or authorize ARS implementation. The original manifest remains the record of what was established on its audit date.

## 2. T1.6 authority anchor

The original W0 manifest cites merge commit `551a9888`. That merge was reverted by `17ae8c91` so that the work could pass the required CodeRabbit-gated pull-request route. T1.6 was then re-merged through PR #55 at `7e798464`, which is an ancestor of current `main` and is the current authoritative merge anchor.

The T1.6 scientific disposition is unchanged; only the durable integration anchor and merge history are corrected.

## 3. T1.28 live state

T1.28 is no longer merely prepared with no compute activity. Current evidence includes:

- commit `e7204373`, which records the BHPS data blocker as extractor defects and dispatches the follow-up;
- compute and subgroup logs under `results/panel_methodology/fdr/`;
- subgroup checkpoints and the local continuation script in that result root;
- no final `stratified_w2_*.json` output at the addendum check;
- no `.apm/memory/stage-01/task-01-28.log.md` at the addendum check.

T1.28 therefore remains active, incomplete, and entirely `legacy_owned`. Its files, processes, contracts, checkpoints, bus state, and conclusions remain in the W0 no-migration set.

## 4. Legacy bus ownership backport

Commit `7c8de855` added explicit ownership, collision refusal, and clearing-as-acknowledgement rules to the mirrored `apm-communication` skills. This is a useful legacy safety improvement but remains instructional rather than a complete mechanical guarantee. It does not authorize shared legacy/ARS slots and does not close M-3 from the adversarial review.

## 5. Assumption status

### A-001 — T1.28 is the final Phase 1 task

**Status:** Pending, not confirmed.

The current coordination record still identifies T1.28 as the sole open Stage 1 task, but Phase 1 cannot be declared closed until T1.28 reaches a reviewed terminal disposition and the current Manager confirms that no additional Phase 1 computational or assurance task remains.

### A-002 — Existing Phase 2 artefacts remain authoritative

**Status:** Unchanged and scope-qualified.

The eight merged Wave-1 outputs retain their recorded authority. The fourteen Plan-defined Stage 2 tasks without accepted logs or explicit supersession remain a `decision_required`; no stage-complete claim follows from the eight-task subset.

## 6. ARS review consequence

The adversarial review verdict is `accept_with_required_changes`. W0 remains open at the transition boundary. W1/W2/W6 may be revised as design documents, but implementation, migration, pilot cutover, and A-001 confirmation remain blocked by their own review gates and the live legacy closeout state.

## 7. Next currency trigger

A further dated addendum is required when any of the following occurs:

- T1.28 produces a final artefact or terminal Task log;
- the Manager changes the Phase 1 scope statement;
- the fourteen unresolved Stage 2 tasks are accepted, deferred, removed, or superseded through an attributed scope decision;
- an active no-migration item is proposed for ARS adoption.
