# ARS documentation plan (Phase 6/7 handoff version)

**Created:** 2026-07-24  
**Mode:** planning only (no docs authored yet)  
**Audience split:**  
- End-user/onboarding track (non-specialist first use)  
- Technical track (implementation, mapping, and operator/runtime details)

This plan turns earlier “docs gap” notes into a concrete documentation queue for Gate 6/7 follow-through.

## 1) Deliverable set and naming

### Track A — End-user onboarding + math-research workflow

| ID | Planned file | Purpose | Dependency |
|---|---|---|---|
| E-01 | `docs/plans/agentic-research-system/documentation/user/getting-started-with-ars.md` | Plain-language explanation of ARS and why it replaces legacy orchestration for successor tasks. | `00-master-transition-plan.md`, `02-design-and-deliverables-roadmap.md` |
| E-02 | `docs/plans/agentic-research-system/documentation/user/first-math-paper-ingestion.md` | Walkthrough for feeding the GTDL program proposal (or any paper) into ARS as a candidate. | `04-parallel-specification-and-foundation-pilot-plan.md`, `03-decisions-and-open-questions.md` |
| E-03 | `docs/plans/agentic-research-system/documentation/user/ars-operator-runbook.md` | Day-to-day actions: dispatch, status checks, pauses, recovery, and handoffs. | `implementation/06a-wp6-1-runtime-task-lifecycle-plan.md` |
| E-04 | `docs/plans/agentic-research-system/documentation/user/troubleshooting-and-results.md` | What candidates do when results are Partial, blocked, or rejected. | `03-decisions-and-open-questions.md`, `06a/06b` plan references |
| E-05 | `docs/plans/agentic-research-system/documentation/user/faq-and-terms.md` | One-page language bridge for `Task`, `attempt`, `review`, `decision`, and `claim`. | `design/02-task-event-and-artifact-schema.md`, `design/01-system-architecture.md` |

### Track B — Technical documentation (plain-language header + full section)

Each technical document must start with a short non-technical “What this is in one minute” paragraph before deep sections.

| ID | Planned file | Purpose | Dependency |
|---|---|---|---|
| T-01 | `docs/plans/agentic-research-system/documentation/technical/system-architecture-overview.md` | Full module map from entry points to control-plane boundaries, with function-level hooks. | `design/01-system-architecture.md`, `research_system/*` |
| T-02 | `docs/plans/agentic-research-system/documentation/technical/lifecycle-model.md` | Command → receipt → event → projection → command retry loop and state transition map. | `design/02-task-event-and-artifact-schema.md`, `06a-wp6-1-runtime-task-lifecycle-plan.md` |
| T-03 | `docs/plans/agentic-research-system/documentation/technical/schema-and-identity-guide.md` | Canonical IDs, schema versioning, idempotency, and provenance links. | `design/02...`, `.research-system/schemas`, W2 records |
| T-04 | `docs/plans/agentic-research-system/documentation/technical/security-and-safety-boundaries.md` | Secret handling, writer exclusivity, migration boundaries, and compatibility surfaces. | `03-decisions-and-open-questions.md`, `P-001..P-021` rows |
| T-05 | `docs/plans/agentic-research-system/documentation/technical/provider-runtime-contract.md` | How Claude/Codex/adapters are called, and where authority lives. | `design/01-system-architecture.md`, `06f-wp6-2-p1-activation-contract.md` |
| T-06 | `docs/plans/agentic-research-system/documentation/technical/legacy-to-ars-transition.md` | End-to-end W9/W7 migration sequencing and handover logic; what is read-only vs. authoritative. | `handoffs/07-w9-gate7...`, `04-parallel-specification...` |

## 2) Technical module-to-function mapping anchor

The following map can be embedded at the top of each technical doc’s deep section.

| Module family | Key files | Core functions/classes to document | Inbound/outbound connection |
|---|---|---|---|
| Command service | `research_system/command/service.py`, `command/models.py` | `CommandService`, `submit`, envelope validation, receipt emission | Accepts human/provider/operator commands; writes to `store/ledger.py` |
| Reduction and replay | `research_system/command/reducers.py`, `projection/replay.py` | `replay_control_plane`, `reduce_task`, `rebuild_projection`, `apply_event` | Converts events into canonical projections and validates event continuity |
| Ledger + objects | `research_system/store/ledger.py`, `store/objects.py`, `store/receipts.py`, `store/identity.py` | `EventLedger`, `AllocatedEvent`, `write_object`, `ReceiptStore`, `initialize_control_store` | Source of canonical sequencing, object identity, and typed receipt storage |
| Routing and profile | `research_system/routing/engine.py`, `routing/independence.py`, `routing/orchestrator.py`, `operations/profiles.py` | `select_route`, `independence_grade`, `build_route_request`, `OperationalProfile` | Uses policy, profile, independence, and route constraints prior to dispatch |
| Dispatch coordination | `operations/coordinator.py`, `operations/resources.py`, `operations/backups.py` | `submit_ars_command`, `issue_prepared_dispatch`, `authorize_operational_surface` | Converts accepted dispatch into runtime start conditions and resource constraints |
| Provider adapters | `adapters/base.py`, `adapters/provider.py`, `adapters/codex.py`, `adapters/claude.py` | `ProviderAdapter`, `build_codex_adapter`, `build_claude_adapter`, `render_*_payload`, `normalize_receipt` | Encapsulates runtime-specific transport while preserving core contracts |
| Assurance & gates | `assurance/models.py`, `assurance/requirements.py`, `routing/orchestrator.py` | `AssuranceRequirement`, `GrantBackedAuthorityPolicy`, route/gate evidence | Applies review requirements and gate gates after replay/recovery evidence |

## 3) Document contract (applies to all six documents)

- **Open file format:** Markdown.
- **Top section:** one paragraph in plain language for non-expert entry.
- **Deep section:** detailed implementation mapping and references to governing files.
- **OKF alignment:** each doc includes:
  1. Problem statement
  2. Data/metadata model
  3. Workflow graph
  4. Validation/evidence requirements
  5. Decision/authority points
  6. Versioned dependencies and status
- **Reference style:** absolute file path + explicit line references for any normative statement.
- **No runtime code in docs:** docs should describe behavior and contracts; implementation evidence remains in PRs.

## 4) Delivery order

1. Publish Track A first for immediate operator onboarding (E-01 to E-03).
2. Publish Track B foundational map (`T-01`, `T-02`) to lock technical vocabulary.
3. Publish boundary/risk docs (`T-03` to `T-06`) before authoring Gate 7 migration sequencing in a fresh implementation cycle.

## 5) Output format for Jira-ready handoff

This plan is designed to flow directly into ticket payloads with:
- one ticket per document above,
- one review checklist per document,
- one acceptance signature per document family (Track A and Track B).
