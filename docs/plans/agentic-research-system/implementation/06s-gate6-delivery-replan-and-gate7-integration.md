# 06s — Gate 6 Delivery Replan and Gate 7 Integration

**Date:** 2026-09-05 (v3 — owner-approved review revisions)
**Status:** Stephen approved the preceding review revisions and instructed the
executor to update this plan and begin Phase 0 on 2026-09-05. This records that
authorization; it does not claim independent acceptance of a future code candidate.
**Supersedes:** 06q as the active delivery plan. Only the finite SPEC action
composition in its §4 Step 5 and the source-resolution contract cited below remain
reference material. Its retirement rule, construction sequence and mandatory fresh
live SPEC-02 closure requirement are replaced here. Historical evidence is preserved.
**Preserves:** the historical real run (01M0454KCTYV0E8PB016CP3F6J), merged STORE
implementation, existing runtime authority checks, historical schemas and bytes,
retired evidence branches, and the live control store.
**Execution boundary:** Phase 0 is authorized now. Later phases require Stephen's
dispatch. Merges, live-store operations, paid/provider calls, successor binding,
final acceptance, Gate 6 closure and Gate 7 opening require explicit owner authority.
**Executors:** selected at dispatch from available models. Model labels and session
estimates are planning aids, not evidence of capability or acceptance requirements.

## 1. Verified baseline and remaining work

The 2026-09-05 live-remote and refreshed origin/main baseline is
ced524b7b59d019ad35bb44a5580400e757787b8. PR #268 merged as 969d3a7,
PR #269 added the transfer handoff, and PR #270 integrated observation-backlog
remediation. Relative to the former 6b72a267 baseline, PR #270 changes STORE writer,
command submission, evidence consumers, release publication and CLI behaviour.
Those are inherited production changes, not a reason to restart delivery.

The STORE code is integrated; Phase 0 verifies the required assembled path at the
selected baseline. SOURCE, SPEC authority integration, Task closure, model/result
and assembled execution remain the construction jobs KAN-104 and KAN-106–109.
Current Jira descriptions must be reconciled from live reads, not this snapshot.

Historical evidence records 126 configurations, 42 deterministic reruns, terminal
PROVEN/spec_02_owner_decided and research-use disposition PARK. Position 444 is the
historical ResourcesReleased anchor, not the current ledger tail. Historical Task
tsk_60c5549e-d11f-7d17-8145-d80e144aa537 still requires governed append-only closure
and an accepted ProjectUseDecision. Phase 0 does not read or mutate the live store.

## 2. Delivery correction

Three failed attempts accumulated machinery and review surface before the complete
public capability worked. Replacing the model alone does not fix conflicting
contracts, deferred integration or automatic retirement of repairable candidates.

The target remains assurance for one research mathematician: exact source/code
identity, append-only evidence, enforced owner and reviewer boundaries, deterministic
replay, a readable result, and verified logical recovery. Every construction phase
extends the same public path. Existing mechanisms are reused; additional machinery
requires a demonstrated failure of that path or a current hard constraint.

## 3. Governing decisions D1–D6

- **D1 — Finite action table and evidence-derived state.** Use the finite SPEC
  action composition in 06q §4 Step 5, with these decisions applied. W11
  (design/11-portfolio-and-discovery-lifecycle.md) supplies underlying command
  semantics; it is not itself a list of SPEC CLI actions. Add only entries needed
  by the current phase, then complete the required list by Phase 4. Use one explicit
  bounded test expectation for names, aliases, required effects and ordering.
  No blob-hash registry binding, Markdown parser or specification synchronizer.
  Completion requires all correctly bound effects for the same subject. Existing
  commands retain individual authority and transaction boundaries: a request and
  an independent review, or a proposal and an owner decision, cannot be collapsed
  into one caller role. Composite actions resume from existing effects and retry
  receipts; no new composite seal or persisted workflow state is introduced.
- **D2 — Reuse inherited authority.** Remove additional SPEC-specific session and
  grant machinery, not the authority checks already enforced by CommandService
  and DiscoveryRuntime. SpecOperatorConfig@1.0.0 remains authority-neutral and
  unchanged: it supplies actor, session and grant IDs, not a declared role or owner
  field. Derive permitted actions from existing authority records. Preserve
  exact-subject reviewer independence, distinct recorded actors and owner-only
  decisions. Do not introduce a parallel caller-declared authority policy, grant
  migration or bypass of existing expiry checks. A completed retry may read its
  existing receipt under the inherited semantics; new effects require authority.
- **D3 — Bounded schema validation.** Preserve existing validators and historical
  schema versions. New operative records declare required and optional fields
  explicitly and reject unrecognized fields. Version only a required record
  change. Do not add global unknown-field warning behaviour or schema migration
  infrastructure. ProjectUseDecision and spec_02_live_run_approval remain closed.
- **D4 — Append-only correction version.** Preserve historical
  spec_01_source_correction@1.0.0 for replay. The new causal-prefix correction is
  2.0.0; never silently replace the historical version.
- **D5 — Inherit STORE.** Do not refactor, extend or harden merged STORE
  speculatively. Phase 0 verifies the required path once. A later demonstrated
  required-path failure is reported with a reproducer and the smallest proposed
  repair; any necessary exception to protected STORE scope is agreed explicitly
  before implementation. Preserve the candidate and valid completed work.
- **D6 — Bounded operational proof, including legitimate PARK.** The owner names
  the exact subset of the historical 126/42 design and cost ceiling in the paid-run
  approval. A legitimate terminal PARK/no_spike outcome can satisfy the fresh
  operational proof when Task acceptance, independently accepted result, replay
  and restore all succeed. The allowed and blocked SPEC-02 branches are exercised
  on scratch stores; historical full SPEC-02 evidence remains historical.
  This explicitly replaces 06q's mandatory fresh live SPEC-02 requirement.
  If fresh SPEC-02 is warranted, it still requires a valid later PROMOTE and
  separate owner approval; a paid-run approval cannot change Candidate state.
  The fresh ProjectUseDecision states that this is a route-proof subset, not a
  replication or scientific promotion. No rerun or manufactured PROMOTE is used
  to force gate completion.

Formal [DECISION] entries for D1–D6 are published with the Phase 0 docs PR in
03-decisions-and-open-questions.md. They amend execution, not historical results.

## 4. Target capability and finite closure contract

One connected public path on integrated main, exercised by an owner-approved
bounded real run:

1. ars discovery spec status, advance and result consume SpecOperatorConfig@1.0.0
   and the inherited shared verified-binding loader.
2. Exact Git resolution (neurips2024 at
   145efcde673f1a1897eff250b77221d26c34c479), source bytes and SHA-256 are
   registered append-only; correction follows D4.
3. Effects retain actor/authority provenance; independent review and owner-only
   decisions cannot be supplied by the wrong actor.
4. Historical and fresh Tasks close only through SubmitForReview then AcceptTask.
5. Both Tasks have registered, independently accepted ProjectUseDecision records
   and JSON/Markdown results isolated by --task-id. A legitimate PARK/no_spike
   fresh result is admissible under D6 and cannot imply empirical adoption.
6. Both histories replay from a fresh process. Governed backup restores to a fresh
   root with matching identity, ledger, artefacts and bytes/hashes. This is
   same-disk logical recovery, not machine-loss resilience.
7. Independent final evidence review, Stephen's recorded closure, final
   documentation/Jira reconciliation and replay after the final docs PR merges.

Freeze acceptance against this contract and its recorded evidence. Gate 7 and
unrelated later improvements cannot add closure prerequisites. Reopening requires
evidence that the accepted closure claim was invalid and Stephen's decision.

## 5. Phase briefs

### 5.0 Common executor preamble

Read this plan's decisions, capability contract, working rules and your phase.
The named primary contracts remain authoritative where this plan preserves them.
Consult 06q only for the explicitly retained action/source references.

- **Start identity:** refresh origin/main and compare with the job's recorded
  baseline. Identify relevant production deltas and preserve integrated work.
  Stop for a demonstrated failure or unresolved scope/authority conflict, not
  merely because main moved. Record the selected SHA before the first task write.
  Use a fresh uniquely named branch and linked worktree; verify cwd, symbolic
  branch, required ancestry and clean initial status. Preserve the dirty primary
  checkout and retired branches. The named original untracked plan may be updated
  with this approved revision after verifying it has not changed concurrently.
- **Scope checkpoint:** 20 changed files, 2,500 added non-generated lines, or more
  than one session plus one follow-up requires an owner decision on continuation.
  These are checkpoints, not reasons to compress code, discard work or split
  mechanically. Do not widen the approved scope yourself.
- **Build order:** extend the real public path first, then the initial acceptance
  negatives, then affected regression checks. Add a test only for a demonstrated
  capability violation or applicable hard constraint. Do not anticipate speculative
  review comments, refactor unrelated code or add infrastructure without need.
- **Construction boundary (Phases 0–4):** no live control-store operations
  (C:/Users/steph/TDL-ARS-WP64-Control), provider/paid calls or credential use.
  No retired spec_flow port, no new plan, no speculative STORE changes.
  Phase 5 permits only separately owner-authorized live operations. No phase
  authorizes merge or CodeRabbit triggering/polling.
- **Validation:** run the targeted changed-path packet, Ruff lint/format on the
  changed Python surface, and git diff --check. Honour mandated repository gates.
  Broaden only for demonstrated shared impact, a narrower failure, or an explicit
  gate. Do not duplicate the full STORE assurance suite.
- **Review:** block only on exact-head reachable failure of §4, durable corruption
  or mispublication, replay divergence, an authority/owner/paid gate bypass, or an
  applicable mandatory gate. Record and decline unrelated findings briefly.
  Batch related root fixes and run their direct regressions together.
  A second material round triggers diagnosis and Stephen's continuation decision.
  Preserve the candidate. Retirement requires evidence that the approach cannot
  satisfy the contract within an agreed bound; review count alone is insufficient.
- **Handback:** lead with the applicable §8 capability status; give the public path
  now demonstrated, exact remaining gap and next action, then branch/PR/SHA,
  test results, declined findings and verified Jira changes. Component success
  never means Gate 6 closure.

### Phase 0 — Verify current STORE and publish the revised plan

**Authorized scope:** verification, this plan, D1–D6 decision entries, a
superseded-by-06s header in 06q, documentation PR and bounded Jira reconciliation.
No production-code or tracked test changes. A disposable, uncommitted driver may
reuse existing fixture setup to exercise the genuine CLI against scratch stores.
It must not replace the service, weaken admission or touch the live store.

1. Select current merged main, record SHA and relevant delta from the former
   baseline. Verify PR #268 is inherited; account for subsequent relevant changes.
2. Run one fixed STORE packet using the existing files/nodes below. Counts from
   the older 53/38/86 packets are provenance only, not acceptance totals.
3. Exercise one successful public binding CLI operation on a disposable root,
   read back the published binding and ledger, retry the exact intent and verify
   no duplicate publication. Real service and validation must run. Help output or
   fake-service routing tests cannot substitute for this operation.
4. Publish the three-file docs PR and record results in §12. Preserve historical
   06q text except its supersession header. No merge is authorized.
5. Update and read back the named Jira descriptions/statuses/labels under §9.
   If the connector fails, provide the exact unapplied changes.

The frozen initial test selection, relative to tests/research_system, is:

- unit/test_spec_operator_config.py
- integration/test_store_binding_cli.py
- integration/test_store_binding_public_contract.py
- integration/test_store_binding_service.py
- integration/test_current_binding.py
- integration/test_wp64_create_backup.py::test_store_backup_cli_is_event_first_retryable_and_not_available_via_generic_submit
- integration/test_wp64_create_backup.py::test_store_verify_restore_appends_evidence_without_cutover_and_replays

Use the populated primary-checkout Python interpreter from the selected worktree,
disable pytest cache and coverage, and retain the command and terminal summary.
Acceptance is passing selected checks, successful genuine CLI publication/readback/
retry, clean documentation diff and an open docs PR. A STORE failure is reproduced
and reported under D5, not silently repaired. Missing evidence remains explicit.

### Phase 1 — SOURCE on the public route — KAN-104

**Exit:** a public advance action registers source evidence; status reports its
completion; replay preserves it. Introduce the thin CLI coordinator and only the
action-table entries needed now. Phase 4 must not introduce the coordinator anew.

Resolve locators, register exact bytes through the verified-binding context, and
support append-only correction. Use existing EventLedger.raw_prefix_sha256.
No optional resolver callbacks, duplicate prefix hashing or STORE changes.
Retired source modules may inform design; do not cherry-pick their infrastructure.

GitReferenceResolution carries repository_url, requested_locator, status and
non-empty resolution_trace; subpath exists only for a locator with one. Resolved
has exactly one canonical_ref, resolved_kind and commit_oid, without candidates or
failure_kind. Ambiguous has at least two candidates and no failure_kind.
Unavailable has failure_kind auth/timeout/transport and no candidates. Absent
requires exhaustive successful resolution; malformed input is a validation error.

New spec_source_observation / ars://portfolio/spec-source-observation is 1.0.0;
spec_01_source_correction is 2.0.0 per D4. Use D3 validation and existing authority
for every publication; Phase 2 extends integration rather than creating a bypass
for earlier phases.

**Initial packet:** neurips2024 exact resolution and registration; one head,
annotated tag, direct OID and subpath; causal-prefix event binding and exact-prior
correction. Malformed, ambiguous and unavailable cases; failed publication has no
authoritative effect; nonexistent correction target rejects. Public status/advance,
one replay positive and one governed backup-admission positive with the new family.

### Phase 2 — AUTHORITY and TASK on the same route — KAN-106 and KAN-107

**Exit:** extend Phase 1's CLI path through the required inherited authority checks
and SubmitForReview → AcceptTask. One PR may deliver both jobs; a split is optional
when a real dependency or review boundary warrants it.

Use D2, preserving individual command actors inside multi-actor actions. No new
session containment, grant-expiry subsystem, Task state or closure path. Required
Task evidence must be supplied through existing governed contracts on scratch
stores; historical live closure remains Phase 5 only.

**Initial packet:** authorized producer, independent reviewer and owner actions;
Task accepted after satisfying review; exact retry reads without new effects.
Reject self-review, non-owner decisions, unsatisfied SubmitForReview/AcceptTask,
and closure inferred only from attempt completion, lease release or result presence.

### Phase 3 — Accepted project-use result on the same route — KAN-108

**Exit:** registration and independent acceptance produce the Task-specific
JSON/Markdown result through the CLI. Extend the same table/evaluator, not a
parallel model.

The evaluator is pure over ledger-derived evidence: not_started, prepared or
completed. Conflicting evidence rejects; no fourth persisted state is introduced.
Completion is conjunctive over correctly bound required effects.

ProjectUseDecision / ars://portfolio/project-use-decision at 1.0.0 requires the
Candidate, current Assay and Spike (or explicit no_spike reason), terminal owner
Decision, source observation/correction, evidence artefacts, accepted operational
Task, governed-code subject, disposition retain_experimental_benchmark/adopt_default/
reject, rationale, limitations and next gates. Include D6's subset qualification.
Preserve the historical PARK restriction.

ars discovery spec result --operator-config … --task-id … --format json|markdown
remains pending until registration and independent acceptance both exist.

**Initial packet:** explicit action expectations; empty, partial, complete,
conflicting, unrelated and retry evidence for required action classes; pending and
accepted output; historical and fresh Task isolation; no promotion wording for
PARK; hash-only, wrong-binding and unknown-field rejection.

### Phase 4 — Remaining branches and assembled proof — KAN-109

**Exit:** complete remaining required actions and verify the assembled public route.
Reuse DiscoveryRuntime.submit, CommandService.submit, replay_discovery and
verify_restore_before_writer_lease. SpecActionIntent stays semantic; the system
derives IDs, envelopes and retry keys. No new persisted model or composite seal.

SPEC-02 requires a valid PROMOTE plus its separate approval. After PARK, the
objective revisit predicate must be satisfied before request_spec_01_revisit →
authorize_spec_01_retry (owner selects RETRY) → request_spec_01_retry → new Assay →
later PROMOTE. Approval alone never changes Candidate state.
Provider work is operator-mediated; construction neither launches nor fabricates it.

**Initial packet:** public SPEC-01 sequence and terminal PARK/no_spike closure;
scratch revisit/retry/PROMOTE and separately approved SPEC-02 sequence; exact
Task/result closure. Wrong role, missing revisit/approval, conflicting concurrent
advance and prepare/publication crash controls, with idempotent recovery and replay.

After construction merges, run one bounded assembled selection on exact main:
the Phase 1–4 packets and the Phase 0 packet. Obtain one independent exact-main
boundary review from a fresh context before proposing the live successor binding.
This is assembly evidence, not Gate 6 closure.

### Phase 5 — Owner-gated live proof and closure

For each step, prepare the exact action, obtain Stephen's explicit authorization,
perform only that action and verify its durable result.

1. **Successor binding:** use the merged binding-service path and its local/
   refreshed-remote/live-remote equality checks for the reviewed main SHA.
   Use the inherited reviewed-divergence successor for the legacy predecessor;
   do not redesign admission.
2. **Historical closure:** append SubmitForReview → AcceptTask for
   tsk_60c5549e-d11f-7d17-8145-d80e144aa537; register its P-050 ProjectUseDecision
   and obtain independent exact-subject acceptance. Preserve historical provenance.
3. **Fresh bounded run:** owner-approved exact subset and cost ceiling; real
   Damrich–Berens–Kobak source at neurips2024, new IDs, distinct recorded actors.
   A legitimate terminal PARK/no_spike is sufficient under D6. Fresh SPEC-02
   runs only if justified by valid promotion and separately approved. A production
   defect stops the paid run; no automatic rerun.
4. **Fresh closure and readback:** accept the Task and ProjectUseDecision; render
   historical/fresh JSON and Markdown after replay from a fresh process; verify
   position-444 historical anchor, Task isolation and PARK limitation language.
5. **Governed recovery:** backup under C:/Users/steph/TDL-ARS-WP64-Backups and
   restore to a fresh root under
   C:/Users/steph/TDL-ARS-WP64-Restore-Verification. Compare identity, ledger,
   artefacts and exact bytes/hashes. Same-disk recovery only.
6. **Final closure:** independent evidence review; Stephen's recorded closure;
   docs-only final PR and its owner-authorized merge; verify documentation-only
   governed-code descent and replay again on merged main. Reconcile KAN-104–109
   with their actual milestone evidence, then KAN-103 and KAN-12 when all required
   capability evidence and descendants are closed.

## 6. Working rules

The public capability governs delivery; phases bound construction, not success
claims. Preserve valid work, fix demonstrated causes and stop when the accepted
contract is satisfied. Do not start another plan, framework or assurance campaign.
Owner-controlled operations remain explicit. Session/file/line checkpoints and
model choices do not establish efficiency or quality; use actual telemetry if
those claims are requested.

## 7. Gate 7 track — documentation only, deferred

This track produces documents and reviews only. It authorizes no implementation,
migration, dispatch or pilot. Start only on Stephen's separate trigger. Gate 7
opening requires Gate 6 closure evidence and separate owner authorization.
Documents consume §4's output contract and may not add requirements back to Gate 6.

- **G7-A:** W0 addendum and bounded delta review for T1.28's terminal disposition;
  reconcile the planning clashes in handoff 14, including WP6.7 hold wording.
- **G7-B:** design/09-migration-and-pilot.md per handoff 07 and the roadmap:
  content-addressed read-only legacy projections only, no legacy task/bus/log/
  decision writes into successor authority; preserve rollback and pilot rubric.
- **G7-C:** Gate 7 definition in 04-plan §4, carrying the intake manifest by pointer:
  W0 addendum, T1.41 double-null panel, Markov-2 alpha=1 W2-only recompute, parked
  work, H1–H9 audit holes, unclosed T1.20 audit and H3 owner scope decision.
  Propose explicit old/new P-026/P-034/WP6.7 wording for owner acceptance.

Each receives an independent adversarial review and Stephen's exact-revision
acceptance. A possible gap in §4 is raised to Stephen, not added to either gate
unilaterally. Original authoring authority: handoffs/07-w9-gate7-legacy-integration-authoring-brief.md.

## 8. Capability reporting

Use exactly the applicable row, followed by the exact gap and next action.

| Position | Required leading status |
|---|---|
| Construction incomplete | Capability status: INCOMPLETE — the historical real SPEC run is PROVEN; the complete public Gate 6 implementation is not integrated on main. |
| Assembled code integrated and passing | Capability status: INCOMPLETE — implementation is integrated; successor binding and fresh live proof remain pending. |
| Successor bound | Capability status: INCOMPLETE — integrated code is bound; fresh run, Task, accepted result, replay and recovery evidence remain incomplete. |
| Live evidence complete, review pending | Capability status: INCOMPLETE — integrated fresh proof is complete; independent final evidence review is pending. |
| Only owner closure remains | Capability status: OWNER-BLOCKED — evidence and independent review are complete; Stephen's Gate 6 closure decision is required. |
| Closure recorded, reconciliation pending | Capability status: INCOMPLETE — owner closure is recorded; final documentation merge, replay and reconciliation are pending. |
| All §4 requirements satisfied | Capability status: INTEGRATED — Gate 6 is closed against the accepted 06s contract and its recorded evidence. |

## 9. Jira reconciliation

Read current descriptions, status, labels, parent and dependency fields before
writing; read back every changed issue and both endpoints of changed dependency
links. Preserve valid links, not contradictory ones. A completed component is
explicitly a MILESTONE; the canonical capability remains open through Phase 5.

| Issue | Phase 0 change |
|---|---|
| KAN-105 | Record exact merged baseline and successful STORE/CLI evidence. Replace stale PR #268-pending instructions. On passing verification, mark MILESTONE and Done; remove stale owner-action-required/integration-pending labels. Live backup/restore remains a visible KAN-103/KAN-12 Phase 5 requirement. |
| KAN-104 | Remove blocked-by-store after verification. Replace obsolete source version and broad resolver matrices with Phase 1's public-path brief and D3/D4. Keep To Do until dispatched; record exact execution SHA then. |
| KAN-106 | Replace session-containment work with D2 and Phase 2. State planned joint delivery with KAN-107, not delivered. |
| KAN-107 | Replace separate post-AUTHORITY-merge requirement with within-Phase-2 ordering; keep existing Task contracts and Phase 5 live-write boundary. |
| KAN-108 | Replace registry ceremony with Phase 3's incremental evaluator and accepted result. |
| KAN-109 | Replace first-time coordinator construction and seals with Phase 4 completion/assembly; preserve D6. |
| KAN-103 and KAN-12 | Update current descriptions to the approved 06s scope, actual STORE state, exact remaining capability gap and next action. Link the open docs PR as pending integration; record merged-plan evidence only after merge. Keep capability open. |

Unstarted jobs remain To Do. In Progress means an actual production/integration
job is executing; at the Phase 0 handback, a pending owner merge/next dispatch is
recorded as a pause with its exact resume action, not continuing execution.
Do not create Gate 7 tasks until that track is triggered.

## 10. Delivery estimates

Phase 0 is one bounded verification/docs task. Phases 1–4 each extend the same
public route, normally within one session plus one follow-up; Phase 5 depends on
owner approvals and the bounded real run. These estimates do not promise a fixed
closure date. A second material review or exceeded scope checkpoint requires a
continuation decision, not an automatic restart. Gate 7 estimates are separate.

## 11. Dispatch and stopping point

Supply this plan's §§3–5.0, the selected phase, §8 and its Jira key. Include exact
branch/base, allowed writes and any owner approval required by that phase.
Read cited primary contracts where needed; briefs do not replace those sources.
Dispatch 0 → 1 → 2 → 3 → 4 → 5. Gate 7 is separately triggered.
The current authorization ends at the Phase 0 handback and proposed docs merge.

## 12. Phase 0 execution evidence

**Baseline:** ced524b7b59d019ad35bb44a5580400e757787b8, branch
codex/gate6-06s-phase0-20260905, fresh linked worktree.

**Genuine CLI probe:** PASS. On a disposable scratch store, the real
research_system.cli store repair-binding --intent path published one binding
event, read back the canonical binding with matching SHA-256
ff3d649ffb711c96fd9b873cae71289a4d195970ecc0993c0195df29d97ca406, and an
exact retry left the ledger at position 3 with the same tail hash
3e344fa4b458b471c0edec9360641b527258e908704338ac112d91fe0d6e27e5.
The probe used the real service, did not replace it, and did not touch the live
control store. Full JSON evidence is retained at
C:/Users/steph/.codex/tmp/gate6-06s-phase0-20260905/public-cli-result.json.

**Bounded STORE packet:** unresolved. The selected pytest command produced
partial progress (24 tests reported) but did not return a terminal summary
within the bounded execution window; it was stopped and is not counted as
passing. No STORE failure was silently repaired. Phase 0 therefore remains
**INCOMPLETE — the genuine CLI smoke path passes, but the bounded STORE packet
has no terminal result and the documentation PR is not yet merged.**

**Documentation checks:** git diff --check passes. The revised plan, six
decision records (P-051–P-056), and 06q supersession banner are present in this
worktree. Jira descriptions for KAN-106–109 were updated and read back; their
statuses remain To Do and dependency links were unchanged. KAN-105, KAN-103
and KAN-12 remain open pending the unresolved packet, docs PR and owner review.
