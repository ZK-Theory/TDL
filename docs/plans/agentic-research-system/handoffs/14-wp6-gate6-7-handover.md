# WP6 Gate 6/7 handover: fresh session baseline

**Created:** 2026-07-24  
**Scope:** Gate 6 and Gate 7 planning consistency check only (no implementation)

This handover is for a fresh session start. It contains only planning-level inconsistencies and the exact text that conflicts.

## What was verified

- `docs/plans/agentic-research-system/implementation/06-wp6-gate6-readiness-and-integration-plan.md`
- `docs/plans/agentic-research-system/handoffs/07-w9-gate7-legacy-integration-authoring-brief.md`
- `docs/plans/agentic-research-system/transition/W0-legacy-closeout-transition-addendum-2026-06-29.md`
- `docs/plans/agentic-research-system/03-decisions-and-open-questions.md`
- `docs/plans/agentic-research-system/04-parallel-specification-and-foundation-pilot-plan.md`
- `docs/plans/agentic-research-system/handoffs/08-wp6-context-budgeted-manager-handoff-prompt.md`
- `docs/plans/agentic-research-system/00-master-transition-plan.md`
- `docs/plans/agentic-research-system/02-design-and-deliverables-roadmap.md`

## Confirmed Gate 6/7 clashes needing immediate reconciliation

### 1) WP6.7 “hold on T1.28/current-paper activity” appears in conflicting forms

| Document | Statement | Conflict |
|---|---|---|
| `06-wp6-gate6-readiness-and-integration-plan.md:182-185` | “Nothing in WP6.7 dispatches while T1.28 or either current paper remains active.” | Absolute hold rule in WP6.7 dispatch prose. |
| `07-w9-gate7-legacy-integration-authoring-brief.md:40-42` | Calls the WP6.7 sentence “stale…must be replaced.” | States that same text is stale and should not be authoritative. |
| `08-wp6-context-budgeted-manager-handoff-prompt.md:171` | “WP6.7 sequencing document only while its W9/T1.28/current-paper gates remain.” | Keeps gate language aligned to old “hold while gates remain,” which can still be read as a hard freeze despite other instructions. |

**Why this can confuse agents:** A reader can follow one doc and incorrectly assume dispatch is blocked even after corrected state language appears elsewhere.

### 2) T1.28 status is represented as both DONE and active/incomplete

| Document | Statement | Conflict |
|---|---|---|
| `07-w9-gate7-legacy-integration-authoring-brief.md:44` | “T1.28 is DONE, not active… PR #72 merged.” | Hard-closed state for T1.28. |
| `transition/W0-legacy-closeout-transition-addendum-2026-06-29.md:22-33` | T1.28 has compute/checkpoints and remains “active, incomplete, and entirely `legacy_owned`.” | Indicates ongoing activity. |
| `03-decisions-and-open-questions.md:767-771` | A-001 status: `T1.28 is now active and Phase 1 closeout is not confirmed`. | Marks phase-1 closeout as not confirmed and pending. |

**Why this is high risk:** A fresh execution agent could either over-block Gate 7 (thinking active) or over-authorize legacy transition steps (thinking already done).

### 3) The first Gate 7 intake step is explicit in one doc but not reflected as an enforced sequencing requirement in another

| Document | Statement | Conflict |
|---|---|---|
| `07-w9-gate7-legacy-integration-authoring-brief.md:48-53` | Gate 7’s first deliverable is W0 addendum + bounded delta review. | Makes this an explicit, required intake action. |
| `06-wp6-gate6-readiness-and-integration-plan.md:197` | “WP6.7 legacy consolidation (gated on W9 + T1.28 closeout; sequencing doc only).” | Describes end state but does not encode the explicit first-deliverable intake artifact. |

**Why this is operationally important:** The same sequence can be started without the intended precondition if only one document is read.

### 4) T1.28’s role is split between migration-only boundary and broader hold semantics

| Document | Statement | Conflict |
|---|---|---|
| `03-decisions-and-open-questions.md:313-315` | T1.28 active does not hold non-migrating successor design after W1/W2 + W3–W5 + W6–W8 gates. | Allows independent successor design progress. |
| `transition/W0-legacy-closeout-transition-addendum-2026-06-29.md:32-44` | T1.28 remains active and legacy-boundary closeout is pending. | Keeps migration closeout unresolved and legacy boundary still active. |
| `04-parallel-specification-and-foundation-pilot-plan.md:26-34` | Succession design continues while T1.28 runs; closeout triggers a W0 addendum and bounded delta review after terminal disposition. | Reinforces partial separation (design can continue, closeout artifacts gate migration). |

**Why this is confusing in practice:** Different teams may infer different boundaries for Gate 6 planning vs migration sequencing versus execution.

## One-line rule for the next session

Treat `T1.28` as a live migration/legacy-closeout constraint until the addendum and terminal disposition are fully confirmed; do not use any one stale sentence as the sole source of authority.

## Suggested immediate alignment work (for a fresh start)

1. Make one reconciler note that explicitly synchronizes:
   - WP6.7 dispatch text (07 update), and
   - canonical migration boundary language (`P-026`, transition addendum status, and D-G6-4).
2. Update the one document that is now becoming the canonical sequencing entrypoint so that all other handoff/pilot docs can follow it without divergence.
3. Keep this file as the entry handoff artifact for any Gate 6/7 continuation handoff and cite the exact line-level sources above.

## Dependency ledger (execution continuity dependencies)

| Dependency ID | Dependency type | Upstream | Downstream | Required state | Why this is a dependency |
|---|---|---|---|---|---|
| DEP-HO-01 | Hard sequencing dependency | `docs/plans/agentic-research-system/implementation/06-wp6-gate6-readiness-and-integration-plan.md` Track A tickets (`DOC-E01`–`DOC-E05`) | `DOC-T02` → `DOC-T03` → `DOC-T01` → `DOC-T04` → `DOC-T05` → `DOC-T06` | Track A documentation artifacts are produced before Track B sequencing begins in this package. | Enables canonical onboarding/operational context before technical dependencies are published. |
| DEP-HO-02 | Evidence dependency | Jira ticketing execution in Topology `KAN` project (`DOC-E01`..`DOC-T06`) | This handoff's follow-on sessions | Jira keys and order must be queryable from the handoff artifacts when dispatching. | Prevents re-creating already-defined sequencing from prose alone. |
| DEP-HO-03 | Gate-7 intake hard dependency | `T1.28` terminal disposition closure and W0 addendum first deliverable | Gate-7 definition and legacy consolidation implementation | W0 addendum and bounded delta review are intake prerequisites before migration execution semantics proceed. | Aligns migration sequencing with source-of-truth gating and prevents premature WP6.7 execution. |

## Shared dependency template (machine-comparable)

| dep_id | dependency_type | upstream | downstream | required_state | evidence_source |
|---|---|---|---|---|---|
| DEP-SEQ-01 | hard-precondition | T1.28 terminal disposition; W0 addendum | Gate 7 first deliverable | W0 addendum and bounded delta review must be completed before migration work proceeds | `14-wp6-gate6-7-handover.md`; `07-w9-gate7-legacy-integration-authoring-brief.md` |
| DEP-SEQ-02 | hard-precondition | DOC-E01 | DOC-T02 | Track A ticket set establishes onboarding baseline before Track B technical sequence starts | Topology `KAN` issue links; KAN-47 blocks KAN-42 |
| DEP-SEQ-03 | hard-precondition | DOC-T02 | DOC-T03 | Lifecycle model is required before schema/identity guide | KAN-47 blocks KAN-48 |
| DEP-SEQ-04 | hard-precondition | DOC-T03 | DOC-T01 | Schema/identity reference is required before architecture module map | KAN-48 blocks KAN-49 |
| DEP-SEQ-05 | hard-precondition | DOC-T01 | DOC-T04 | Architecture module map is required before security boundaries | KAN-49 blocks KAN-50 |
| DEP-SEQ-06 | hard-precondition | DOC-T04 | DOC-T05 | Security boundary work is required before provider runtime contract | KAN-50 blocks KAN-51 |
| DEP-SEQ-07 | hard-precondition | DOC-T05 | DOC-T06 | Provider runtime contract is required before migration transition guide | KAN-51 blocks KAN-52 |

```json
{
  "dependency_template_version": "1",
  "source": "14-wp6-gate6-7-handover",
  "dependencies": [
    {
      "dep_id": "DEP-SEQ-01",
      "dependency_type": "hard-precondition",
      "upstream": "T1.28 terminal disposition; W0 addendum",
      "downstream": "Gate 7 first deliverable",
      "required_state": "W0 addendum and bounded delta review must be completed before migration work proceeds",
      "evidence_source": "14-wp6-gate6-7-handover.md; 07-w9-gate7-legacy-integration-authoring-brief.md"
    },
    {
      "dep_id": "DEP-SEQ-02",
      "dependency_type": "hard-precondition",
      "upstream": "DOC-E01",
      "downstream": "DOC-T02",
      "required_state": "Track A ticket set establishes onboarding baseline before Track B technical sequence starts",
      "evidence_source": "KAN issue links"
    },
    {
      "dep_id": "DEP-SEQ-03",
      "dependency_type": "hard-precondition",
      "upstream": "DOC-T02",
      "downstream": "DOC-T03",
      "required_state": "Lifecycle model is required before schema/identity guide",
      "evidence_source": "KAN-47 blocks KAN-48"
    },
    {
      "dep_id": "DEP-SEQ-04",
      "dependency_type": "hard-precondition",
      "upstream": "DOC-T03",
      "downstream": "DOC-T01",
      "required_state": "Schema/identity reference is required before architecture module map",
      "evidence_source": "KAN-48 blocks KAN-49"
    },
    {
      "dep_id": "DEP-SEQ-05",
      "dependency_type": "hard-precondition",
      "upstream": "DOC-T01",
      "downstream": "DOC-T04",
      "required_state": "Architecture module map is required before security boundaries",
      "evidence_source": "KAN-49 blocks KAN-50"
    },
    {
      "dep_id": "DEP-SEQ-06",
      "dependency_type": "hard-precondition",
      "upstream": "DOC-T04",
      "downstream": "DOC-T05",
      "required_state": "Security boundary work is required before provider runtime contract",
      "evidence_source": "KAN-50 blocks KAN-51"
    },
    {
      "dep_id": "DEP-SEQ-07",
      "dependency_type": "hard-precondition",
      "upstream": "DOC-T05",
      "downstream": "DOC-T06",
      "required_state": "Provider runtime contract is required before migration transition guide",
      "evidence_source": "KAN-51 blocks KAN-52"
    }
  ]
}
```

```json
{
  "dependency_schema": {
    "name": "plan_dependency_contract_v1",
    "required": [
      "dep_id",
      "dependency_type",
      "upstream",
      "downstream",
      "required_state",
      "evidence_source"
    ],
    "optional": [
      "target_issue",
      "target_status",
      "notes"
    ],
    "enum": {
      "dependency_type": ["hard-precondition", "blocking", "soft-order", "evidence-required"]
    },
    "patterns": {
      "dep_id": "^DEP-SEQ-\\d{2}$",
      "evidence_source": "non-empty string"
    },
    "notes": "Validate rows with non-empty fields, then check Jira evidence claims through API links where available."
  }
}
```

## No change requested

No code or schema changes were made by this handover action; this is planning continuity only.
