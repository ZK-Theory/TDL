# Adversarial review — Gate 6 PR #258 SpecFlow convergence

**Date:** 2026-08-21
**Subject:** local uncommitted SpecFlow convergence candidate based on
`bb9ab7a0f679ba71d2a364410f69ec53673c2ae2`
**Governing plan:**
[06r](../implementation/06r-gate6-pr258-review-convergence-plan.md)
**Verdict:** `accept_with_required_changes`

The bounded SpecFlow design is coherent after remediation. No open Critical or
Major code finding remains in the reviewed boundary. Acceptance remains
conditional because clean-head read-only live replay is blocked by the separate
binding-advance workstream, which was not reviewed here.

## Critical and Major findings

### ADR-SF-01 — Major — status and admission restated completion separately

**Claim.** The first implementation slice centralized admission but left later
`status()` branches checking raw rows and document-type presence. A future
definition change could therefore make status and admission disagree.

**Evidence and scenario.** The registry now defines all 25 actions at
[`spec_flow.py:119`](../../../../research_system/discovery/spec_flow.py#L119) and
[`spec_flow.py:141`](../../../../research_system/discovery/spec_flow.py#L141).
Before remediation, later status branches independently checked OR rows and
document keys. A return branch with a registered document but incomplete exact
effects could be displayed as complete while `advance()` rejected it.

**Impact.** Material lifecycle ambiguity and renewed specimen-by-specimen
repair.

**Disposition.** `fixed_now`. `_action_state` is the one phase evaluator at
[`spec_flow.py:1664`](../../../../research_system/discovery/spec_flow.py#L1664),
and both `_status_from_snapshot` and `_advance_unfenced` consume it at
[`spec_flow.py:1703`](../../../../research_system/discovery/spec_flow.py#L1703)
and
[`spec_flow.py:2528`](../../../../research_system/discovery/spec_flow.py#L2528).
Status and admission also share one immutable snapshot.

**Affected work:** 06r SF-1, SF-4, SF-D.

### ADR-SF-02 — Major — brief-input effects could outrun completion identity

**Claim.** Registration, review, or acceptance could complete all durable
effects and crash before the action identity. They had no preparation journal,
so status advanced instead of requiring exact recovery.

**Evidence and scenario.** The single-shot recovery set and identity reader are
at
[`spec_action_journal.py:16`](../../../../research_system/discovery/spec_action_journal.py#L16)
and
[`spec_action_journal.py:81`](../../../../research_system/discovery/spec_action_journal.py#L81).
The three-stage injected-crash control is at
[`test_discovery_spec_flow_cli.py:3777`](../../../../tests/research_system/integration/test_discovery_spec_flow_cli.py#L3777).

**Impact.** Forward route actions could begin without an exact completed packet
identity; deterministic recovery was incomplete.

**Disposition.** `fixed_now`. Every registry-declared single-shot action is
journalled before its first durable effect. The import-time registry/journal
equality fence prevents an unjournalled single-shot addition. Pending state is
cleared only by the document completion event or exact action identity.

**Affected work:** 06r SF-1, SF-3, SF-6.

### ADR-SF-03 — Major — retry still selected documents by type-wide uniqueness

**Claim.** Exact completion association was fixed for status, but completed
retry still required exactly one artefact stream of the document type.

**Evidence and scenario.** A later unrelated registration of the same type left
status unchanged but made retry raise “no exact durable registration.” The
extended public control is at
[`test_discovery_spec_flow_cli.py:3565`](../../../../tests/research_system/integration/test_discovery_spec_flow_cli.py#L3565).

**Impact.** Unrelated evidence could deny an otherwise valid exact retry,
violating SF-2 and SF-5.

**Disposition.** `fixed_now`. Completion census binds the full registration
tuple at
[`spec_flow.py:860`](../../../../research_system/discovery/spec_flow.py#L860),
and retry resolves the packet's exact artefact and content at
[`spec_flow.py:1336`](../../../../research_system/discovery/spec_flow.py#L1336).

**Affected work:** 06r SF-2, SF-3, SF-5.

### ADR-SF-04 — Major — plan overstated preparation as an authority extension

**Claim.** SF-3 said only `not_started` work needed current authority. A partial
prepared action can still contain effects that were never admitted, and the
preparation record is not an authority grant.

**Evidence and scenario.** The journal proves an exact packet and recovery
owner. It does not prove that each missing command was accepted before expiry.
Bypassing current command-service authority for those effects would change the
authority model.

**Impact.** The original prose could be read as permission to publish new
effects after authority expiry.

**Disposition.** `fixed_now` in 06r. Completed effects reconstruct before live
authority. Prepared but unpublished effects retain normal production authority
checks. No authority-expansion implementation was introduced.

**Affected work:** 06r SF-3; no owner decision changed.

### ADR-SF-05 — Major — early Assay authority progress was absent from the route census

**Claim.** Before a SPEC Candidate exists, Assay authority events are outside
the Candidate-lineage event filter. The projection fallback recognized only
`review_requested` and later statuses, so an otherwise valid OR-105 request was
rejected as though OR-101 through OR-104 had never happened.

**Evidence and scenario.** The unchanged starting head reproduced the public
OR-105 failure. Frame inspection showed `completed_rows == {"OR-140"}` after
four accepted Assay authority transitions. The early state is not ambiguous:
the accepted projection carries exact `contents.rubric`, `contents.scope`,
`observations.rubric`, and `observations.scope` records.

**Impact.** The public SPEC coordinator could not advance a valid projected
Assay authority chain, so status/admission compatibility depended on whether a
later Candidate happened to exist.

**Disposition.** `fixed_now`. `_SpecRouteCensus.from_snapshot` derives
OR-101/102 from exact projected contents and OR-103/104 from exact projected
observations before applying the existing late-status rows. A nine-case
parameterized control covers every phase from `empty` to `accepted`, and the
public OR-105/OR-106 test now passes.

**Affected work:** 06r SF-1, SF-4, SF-6.

## Minor and baseline corrections

- Four action definitions with both row and document fields now use named
  arguments; this removes positional-field ambiguity from the registry.
- Two failing preservation tests were reproduced unchanged at the starting
  head and corrected without weakening production gates: the partial Assay
  fixture now derives the complete required-axis partition from the accepted
  bar, and the SPEC-02 promotion helper consumes the already externally
  validated projection rather than replaying without the required validator.
- The approval restart test now injects after `ArtefactRegistered`, not before
  immutable bytes are published, and requires `prepared` until exact retry
  seals completion.
- Seven failures from the first complete module run reproduced unchanged at
  exact starting head `bb9ab7a0`: one missing recorded-time fixture, one stale
  exact-subject error expression, the real Assay census defect above, one
  bypass negative that tried to read the deliberately absent brief, and three
  stale private-helper calls/fixtures. Their intended contracts are restored;
  no production gate was weakened.

## Decision audit

| Decision or invariant | Disposition | Enforcement and evidence |
| --- | --- | --- |
| SF-1 total action state | keep, implemented | `_SpecActionState`; 25-action empty-effect census; three-stage crash matrix |
| SF-2 exact completion tuple | keep, implemented | exact route/action/packet/document/artefact/registration comparison in `_registered_documents` |
| SF-3 retry ordering | amend and implement | completed document and brief retries reconstruct before authority; incomplete prepared effects retain authority checks |
| SF-4 one status/admission interpretation | keep, implemented | one registry, evaluator, snapshot, and alias source |
| SF-5 unrelated evidence isolation | keep, implemented | same-type status plus exact-retry regression; existing foreign-row controls |
| SF-6 durable compatibility | keep, blocked by binding advance | 109-test module and restart/recovery controls green; clean-head live replay was refused before replay because the governed recovery binding remains pinned to the preceding Git subject |
| No second persisted state machine | keep | ledger, receipts, completion identity, and existing preparation journal remain the facts |
| Binding-advance transaction repair | defer | separate 06r workstream; not assessed by this review |
| Push, external review, or merge | defer | no authority inferred; owner controls reviewer operation and merge |

## Consistency matrix

| Invariant | Enforcement point | Direct test |
| --- | --- | --- |
| No empty completion | immutable registry plus `_action_effects_are_complete` | `test_registered_spec_action_family_has_no_empty_effect_completion` |
| Exact completion join | `_registered_documents` | premature action and later same-type registration controls |
| Completed retry before live authority | durable result reconstruction | document plus three brief-input expired-grant controls |
| Prepared is not completed | journal plus `_action_state` | three brief-input crash controls; document restart controls |
| Complete/partial aliases are exclusive | registry alias plus status branch cardinality | complete and partial end-to-end preservation routes |
| Changed retry conflicts | action identity and preparation journal | existing changed-command/same-retry controls |

## Remaining required change

1. Complete the separately planned binding-advance transaction, advance the
   governed live binding to the frozen candidate, then replay the live control
   store read-only. Compare the terminal public status with the recorded Gate 6
   result and prove zero file-byte/hash changes. A mismatch or new
   same-invariant defect returns the verdict to `rework_required` under 06r's
   stop-loss rule.

## Practicality

The added control is proportionate: one immutable definition per action, one
phase evaluator, and the already existing recovery journal. It removes alias
switches, duplicate snapshots, and type-wide inference. It does not add a new
persisted state machine or an authority bypass. The principal cost is the slow
integration fixture; the complete module should therefore run once at the
frozen candidate rather than after every local edit.

## Revision plan

**Immediate:** repair and validate the binding-advance transaction, then
complete clean-head live compatibility evidence.
**Owner decisions:** none for this local slice.
**Later dependency:** review and repair the binding-advance transaction under
06r before the PR can be frozen for owner-triggered external review.

## Change log and verification evidence

Files reviewed or changed in this boundary:

- `research_system/discovery/spec_flow.py`
- `research_system/discovery/spec_action_journal.py`
- `tests/research_system/integration/test_discovery_spec_flow_cli.py`
- `tests/research_system/integration/test_wp6_6_discovery_runtime.py`
- `docs/plans/agentic-research-system/implementation/06r-gate6-pr258-review-convergence-plan.md`

Observed green evidence: 11-case remediation matrix; 7-case
recovery/restart/conflict selector; three-stage expired-grant retry; three-stage
crash-before-identity; partial brief recovery; complete SPEC-02 route; partial
SPEC-01 route; partial SPEC-02 route; complete expanded SPEC-flow module
(`109 passed` in 5,211.12 seconds); direct artefact-storage boundary; both
contract-binding modes against 103 contracts; Ruff; formatting; syntax
compilation; and `git diff --check`. Clean-head live replay remains pending,
hence `accept_with_required_changes`. The first clean-head attempt was rejected
during operator binding load with `binding recovery Git subject changed`,
before Discovery replay or any write; this is the production trigger for the
separate binding-advance workstream.
