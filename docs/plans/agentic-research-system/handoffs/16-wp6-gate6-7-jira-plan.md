# Jira backlog plan for ARS documentation rollout (Gate 6/7 docs package)

**Created:** 2026-07-24  
**Scope:** Create/import tickets for the docs set described in `15-ars-documentation-plan.md` only.

## 1) Jira issue import schema (project-agnostic)

Use CSV import where Jira has default fields available. Replace only the custom field IDs that exist in your instance.

```csv
Project,Issue Type,Summary,Description,Priority,Labels,Components,Assignee,Reporter,Fix Version(s),Due Date,Reporter,
customfield_<DocType>,customfield_<Audience>,customfield_<Gate>,customfield_<Owner>,customfield_<SourceRef>,customfield_<AcceptCriteria>
```

Minimal JSON-equivalent payload (for REST clients):

```json
{
  "fields": {
    "project": {"key": "ARS"},
    "issuetype": {"name": "Task"},
    "summary": "DOC-011: ...",
    "description": {
      "type": "doc",
      "version": 1,
      "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Plain-language summary ..."}]},
        {"type": "paragraph", "content": [{"type": "text", "text": "Acceptance: ..."}]}
      ]
    },
    "priority": {"name": "Medium"},
    "labels": ["ars", "docs", "gate6", "gate7", "handoff"],
    "customfield_10000": "documentation",
    "customfield_10001": "end-user",
    "customfield_10002": "W6/W7",
    "customfield_10003": "Owner",
    "customfield_10004": "docs/plans/agentic-research-system/handoffs/15-ars-documentation-plan.md",
    "customfield_10005": "Acceptance checklist and line-referenced source links completed"
  }
}
```

### Recommended conventions

- `Summary` format: `DOC-XXX: <family>/<short topic>`
- `Description` first paragraph: non-technical plain-language synopsis.
- `Description` second paragraph: technical scope and acceptance.
- `Labels`: include both `ars` and `gate6-7`.
- `Components`: use `documentation` and one of `user`/`technical`.
- `Fix Version`: target project checkpoint milestone when known (e.g., `ars-gate7-prep`).

## 2) OKF-friendly ticket body skeleton

Each ticket description should follow this fixed order:

1. **What this document is for**
2. **How to use it**
3. **Inputs required**
4. **Acceptance criteria**
5. **Source trace** (exact planning-doc references with line anchors)
6. **Open issues / follow-up**
7. **Reviewer checklist**

That pattern maps cleanly to Open Knowledge Format style (audience summary + machine-verifiable sections).

## 3) Backlog list from documentation plan

### Track A: end-user onboarding

| Jira ticket | Planned doc | Suggested priority | Summary | Acceptance criteria |
|---|---|---|---|---|
| DOC-E01 | `documentation/user/getting-started-with-ars.md` | Medium | Create beginner ARS onboarding guide for mathematical research workflow | Explain where legacy work remains and what ARS owns; include a one-screen end-to-end example |
| DOC-E02 | `documentation/user/first-math-paper-ingestion.md` | Medium | Create ingestion walkthrough for feeding GTDL Frontier report-like material | Explicitly map to an example paper and explain handoff artefacts, review step, and state outcomes |
| DOC-E03 | `documentation/user/ars-operator-runbook.md` | High | Create runbook for dispatch, status checks, recovery, and escalation | Include CLI and non-CLI paths, stop conditions, and command-to-state outcomes |
| DOC-E04 | `documentation/user/troubleshooting-and-results.md` | Medium | Create troubleshooting guide for Partial/blocked/rejected paths | Include likely failure classes and required review/owner escalation path |
| DOC-E05 | `documentation/user/faq-and-terms.md` | Low | Create terminology glossary for non-specialist users | Define `Task`, `attempt`, `review`, `decision`, `claim` with examples |

### Track B: technical

| Jira ticket | Planned doc | Suggested priority | Summary | Acceptance criteria |
|---|---|---|---|---|
| DOC-T01 | `documentation/technical/system-architecture-overview.md` | High | Publish architecture and module map with control-flow direction | Include component responsibilities and dependency direction; explicit non-authority surfaces |
| DOC-T02 | `documentation/technical/lifecycle-model.md` | High | Publish lifecycle flow (command/receipt/event/projection) | Include sequence diagram or Mermaid flow plus function-level touchpoints |
| DOC-T03 | `documentation/technical/schema-and-identity-guide.md` | High | Publish identity, schema, and idempotency guide | Include canonical schema and provenance proof expectations |
| DOC-T04 | `documentation/technical/security-and-safety-boundaries.md` | Medium | Publish control boundaries and secret/compatibility safety points | List prohibited data paths and conflict/failure checks |
| DOC-T05 | `documentation/technical/provider-runtime-contract.md` | Medium | Publish runtime adapter contract and dispatch contract boundaries | Include provider differences and what remains in core vs. adapter |
| DOC-T06 | `documentation/technical/legacy-to-ars-transition.md` | Medium | Publish W9/W7 migration logic and legacy-read/write boundaries | Include explicit sequencing and irreversible-authority transitions |

## 4) Import sequencing for fresh agent session

1. Create epic: `ARS-Gate6/7 Documentation Set` (if available).
2. Add Track A tickets first (E01–E05) so user-facing material is available while technical tickets are authored.
3. Add Track B tickets in `T02→T03→T01→T04→T05→T06` dependency order so lifecycle mapping exists before security/rule docs.
4. Attach `15-ars-documentation-plan.md` and `14-wp6-gate6-7-handover.md` as evidence attachments.

## 4.1) Dependency ledger for the Jira package

| Dependency ID | Dependency type | Upstream | Downstream | Required state | Recommended Jira evidence |
|---|---|---|---|---|---|
| DEP-JIRA-01 | Hard sequencing dependency | Track A: DOC-E01, DOC-E02, DOC-E03, DOC-E04, DOC-E05 | Track B: DOC-T02, DOC-T03, DOC-T01, DOC-T04, DOC-T05, DOC-T06 | Track A ticket set is created/accepted before Track B starts. | `KAN-42`..`KAN-46` block `KAN-47`; `KAN-47` blocks `KAN-48` → `KAN-49` → `KAN-50` → `KAN-51` → `KAN-52` (example evidence in instance). |
| DEP-JIRA-02 | Blocking dependency | DOC-T02 (`KAN-47`) | DOC-T03 (`KAN-48`) | Lifecycle model artifact available before schema/identity authoring. | `KAN-47` is blocked by `KAN-48` link.
| DEP-JIRA-03 | Blocking dependency | DOC-T05 (`KAN-51`) | DOC-T06 (`KAN-52`) | Provider/runtime contract finished before migration transition write-up. | `KAN-52` is blocked by `KAN-51` link. |
| DEP-JIRA-04 | Gate-7 sequencing dependency | 07 handoff intake requirement (W0 addendum + bounded delta review first) | Any migration-related Jira action in this stream | Migration/Gate-7 execution planning must not precede intake completion. | `docs/plans/agentic-research-system/handoffs/07-w9...` and `14-wp6-gate6-7-handover.md` dependencies. |

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
  "source": "16-wp6-gate6-7-jira-plan",
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

## 5) Optional one-time Jira schema sanity check

## 5) Optional one-time Jira schema sanity check

Before import:
- verify `Project` key exists,
- verify customfield IDs for `DocType/Audience/Gate/Owner` in the target instance,
- keep descriptions under text limits,
- confirm required fields for your Jira permission profile.
