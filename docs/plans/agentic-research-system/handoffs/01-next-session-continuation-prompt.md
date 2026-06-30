# Continuation Session Handover Prompt

> **Historical handover — superseded.** This prompt records the pre-review state at 2026-06-28. Use [03-post-review-continuation-prompt.md](03-post-review-continuation-prompt.md) for current continuation. Do not treat the snapshot, fixture counts, decision statuses, or Observation 7 status below as current.

You are taking over the Agentic Research System planning work in the TDL repository.

## Objective

Continue from the completed first specification pass without restarting the diagnosis or relitigating decisions Stephen has already approved. The immediate user intent is to review the first-pass package as a whole before choosing the next design sequence. Do not implement the system, migrate tasks, or modify live research/APM state unless Stephen later gives explicit authorization.

## Repository and snapshot

- Repository root: `C:\Users\steph\TDL`
- Branch at handover: `main`
- HEAD at handover: `47bcdef55d0ab48ff42da8d76577da047dd5b6b5`
- Snapshot date: `2026-06-28`
- Planning root: `C:\Users\steph\TDL\docs\plans\agentic-research-system`
- The entire planning folder is currently untracked. Nothing from this work has been staged or committed.
- `.apm/` was read for evidence but not modified by this planning work.
- No `.research-system/` implementation root exists.
- Existing untracked results, recovery/checkpoint material, and `.tmp.driveupload/` belong to the user or application. Do not clean, move, stage, or reinterpret them.
- Several planning files were deliberately detached from `.tmp.driveupload` hard links after Windows patching exposed the link. Treat `.tmp.driveupload/` as app plumbing, not a working source.

Verify the live branch, HEAD, status, and file existence before writing. The snapshot is a handover anchor, not proof that active research state has not changed.

## Mandatory startup discipline

1. Invoke `task-observer` before tool work and read OPEN observations relevant to every skill you load.
2. Observation 7 is currently OPEN for `apm-communication`: bus writes require explicit task/agent ownership, collision failure, and clearing-as-acknowledgement rather than deletion. W2 and W6 already embody this rule; the skill itself has not been changed.
3. Read repository `AGENTS.md` and follow its cwd/branch, navigation, GitNexus, and commit rules.
4. Do not spawn subagents unless Stephen explicitly requests delegation or parallel agent work.
5. Direct files are authoritative. The existing Graphify index predates this planning package and prior W1/W2 queries returned unrelated computational nodes.

## Read order

Read these files in order:

1. `docs/plans/agentic-research-system/README.md` — package index and current first-pass status.
2. `docs/plans/agentic-research-system/00-master-transition-plan.md` — programme charter, diagnosis, system direction, and transition sequence.
3. `docs/plans/agentic-research-system/01-current-system-evidence.md` — source hierarchy and evidence behind the diagnosis.
4. `docs/plans/agentic-research-system/03-decisions-and-open-questions.md` — accepted directions, Stephen-approved W1 proposals, and pending W2/W6 proposals.
5. `docs/plans/agentic-research-system/transition/W0-legacy-closeout-transition-manifest-2026-06-28.md` — commit-anchored legacy boundary, source precedence, no-migration set, and historical fixtures.
6. `docs/plans/agentic-research-system/design/01-system-architecture.md` — W1 architecture.
7. `docs/plans/agentic-research-system/design/02-task-event-and-artifact-schema.md` — W2 identity, command/event, lifecycle, artefact, review, and decision design.
8. `docs/plans/agentic-research-system/design/06-evaluation-observability-and-audit.md` — initial W6 catalogue and grading/change-gate design.
9. `docs/plans/agentic-research-system/02-design-and-deliverables-roadmap.md` — remaining work packages and dependency order.
10. `docs/plans/agentic-research-system/design/README.md` — design-set status.

Only return to the original source material when checking a contested claim or extending the design:

- `C:\Users\steph\Documents\TDA-Research\02-Notes\2025_Day_3_Rewrite_v1_ContextEngineering.pdf`
- `C:\Users\steph\Documents\TDA-Research\02-Notes\Day_1_v3.pdf`
- `C:\Users\steph\TDL\docs\plans\strategy\Meta-Research-Plan-23-03-2026.md`

Use the PDF skill if you inspect the PDFs.

## Status that must be preserved accurately

### W0 — legacy boundary

- Outcome: `PARTIAL — manifest complete, legacy boundary not sealed`.
- W0 was anchored to the 2026-06-28 repository snapshot.
- At that snapshot, T1.28 was the sole open Stage 1 task and was prepared/queued, not completed.
- Full Stage 2 was not complete under the authoritative 22-task Plan: eight Wave-1 Task logs were accepted and fourteen Plan tasks lacked logs, including the T2.22 gate.
- T0.3 remained blocked on the second-machine canary.
- T1.28, T0.3, unresolved Stage 2, later stages, retained worktrees, caches/checkpoints, superseded-but-live provenance, and UKDA data are in the no-migration set.
- These claims may now be stale. Verify live state before any transition claim, but do not rewrite the dated W0 snapshot. Add a dated reconciliation/addendum instead.

### W1 — architecture

- Stephen approved W1 on 2026-06-28 and instructed work to proceed.
- Current Manager confirmation and post-T1.28 reconciliation remain pending.
- Implementation and migration remain prohibited.
- P-001 through P-005 are approved by Stephen but not fully accepted through the remaining Manager/reconciliation gate.

### W2 — schema and lifecycle

- Status: review pending.
- P-006 through P-013 are proposals, not accepted decisions.
- No JSON Schemas, runtime, event ledger, adapters, or implementation files exist.

### W6 — initial catalogue

- Status: initial catalogue review pending.
- It contains historical F-001–F-020 and synthetic S-001–S-010.
- P-014 through P-019 are proposals.
- It is not a full executable W6 specification; trace schemas, graders, thresholds, retention, and tooling remain deferred.

## Decisions not to relitigate without new evidence

Treat D-001 through D-008 and Stephen's approval of P-001 through P-005 as the baseline:

- this is a system redesign, not prompt-only cleanup;
- evolve APM rather than patch it indefinitely or adopt an external framework wholesale;
- preserve pre-registration, contracts, provenance, worktrees, no-overwrite output, checkpoints, and Partial/escalation semantics;
- use a domain-general, provider-neutral core with specialist assurance packs;
- local inspectable control plane first;
- JSONL/events and immutable manifests are canonical; SQLite/search/graph/dashboard/bus files are projections;
- `.research-system/` is the proposed neutral root;
- one serialized command boundary writes canonical lifecycle state;
- `legacy_owned`, `successor_owned`, and `closed_reference` are mutually exclusive; no dual ownership;
- reserve pre-registration changes, R3 dispatch, decision-lock reversal, claim promotion, and imported-authority promotion for Stephen;
- keep high-reasoning models on epistemically risky mathematical work until eval evidence supports change;
- separate design, implementation, verification, acceptance, and claim authority.

You may identify a contradiction or new evidence that requires revisiting one of these, but do not reopen it as a matter of taste. Record the evidence, impact, and a proposed superseding decision.

## First-pass design summary

W1 defines a modular local control plane with portfolio, command/event, projection, artefact/provenance, execution, assurance, context/memory, evaluation, provider-adapter, APM-compatibility, and domain-pack components.

W2 defines:

- prefixed UUIDv7 canonical IDs and scoped aliases;
- immutable versioned objects;
- atomic JSONL event batches, one per accepted command;
- commands, receipts, event envelopes, idempotency, stream versions, and deterministic replay;
- separate Task, dispatch, attempt, lease, message, review, decision, and artefact state;
- typed blocker/input/Partial/reopen/supersession semantics;
- exact ScopeDefinition revisions for milestone completion;
- multidimensional artefact authority;
- exact-hash review binding and explicit decision authority.

W6 defines paired pre-control/post-control fixtures, non-compensable hard graders, deterministic-first grading, minimized/redacted sources, change-to-fixture coverage manifests, and P0/P1 gates.

## Working rules

- Preserve dated history. Amend or supersede; do not silently rewrite earlier conclusions.
- Do not infer completion from `Success`, `Done`, an empty bus, merged prose, or a dashboard.
- No active APM task is a pilot or migration experiment.
- No raw UKDA data, secrets, `.env` content, hidden reasoning, or full transcripts enter reusable designs/fixtures.
- Passing software tests or schemas never substitutes for scientific review.
- Exact pre-registered tasks must not be weakened for cost without an explicit amendment/decision.
- Hard runtime guardrails create stop/input-required/Partial behavior; they are not advisory.
- Messages do not mutate lifecycle state; compatibility-file clearing acknowledges delivery and preserves history.
- Significant new governance choices go into `03-decisions-and-open-questions.md` before a later specification assumes them.

## What to do in the next session

1. Read and verify the first-pass package and live repository status.
2. Give Stephen a concise continuity confirmation containing:
   - current W0/W1/W2/W6 status;
   - any live-state changes since the handover snapshot;
   - unresolved review/authority gates;
   - no more than the genuinely material questions needed for the next decision.
3. Do not restate the entire diagnosis or ask Stephen to reconfirm settled directions.
4. Wait for Stephen's review direction unless he has already asked for a specific next work package.
5. If asked to continue design, use the dependency order in the roadmap. W3–W5 are the natural next interface set; W7/W8 and executable W6 depend on them. Keep each specification independently reviewable.
6. Do not start implementation planning until the relevant W1/W2 governance gates are resolved and Stephen explicitly authorizes implementation planning.

## Verification baseline at handover

The planning folder contained ten Markdown files before these handover prompts. The first-pass verification found:

- all local links valid;
- UTF-8 valid and no stray control characters;
- W6 exactly 20 historical plus 10 synthetic fixtures;
- no placeholders in the planning package;
- no planning files staged;
- `.apm/` unchanged;
- `.research-system/` absent.

Re-run proportionate checks after edits. Do not claim completion from this historical verification alone.
