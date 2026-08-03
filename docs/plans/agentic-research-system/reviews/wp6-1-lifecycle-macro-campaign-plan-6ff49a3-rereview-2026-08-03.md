# WP6.1 lifecycle macro-campaign plan exact-subject adversarial rereview

**Date:** 2026-08-03
**Verdict:** `rework_required`
**Findings:** 0 Critical, 2 Major, 0 Minor
**Reviewed commit:** `6ff49a39c96686fb687879a8e3199a711c4dd346`
**Reviewed parent:** `8631f691aac7c501b6badf95632faa721987f656`
**Reviewed tree:** `abb93229d225fe26f002e2a76691f39dccc4bd4e`
**Reviewed branch:** `review/wp6-1-macro-plan-r2-6ff49a3`
**Reviewed plan:** `docs/plans/agentic-research-system/implementation/06p-wp6-1-lifecycle-macro-campaign-execution-plan.md`
**Plan Git blob:** `b4d81bc097cd971b75dc8370e92e2ed6c7bc3453`
**Plan raw Git-blob SHA-256:** `f20c8b215a1877df4a1693f82e2dd8956956d03a9eece4848d964bbdde99f366`

## 1. Executive conclusion

The remediation materially corrects the first review's authority, lifecycle-join,
06i-route, final-audit, and schema-path defects. Independent reconstruction confirms
the 104-row catalogue, 19 active rows, 85 remaining rows, and exact disjoint
C1/C2/C3/R1 allocation of 23/28/32/2. The capability campaign remains the
orchestration unit; the plan does not devolve into 104 row tickets. Protected command
and event schema identities are unchanged.

Two Major enforcement gaps remain in the remediated routing design:

1. model/thinking is proved at initial launch, but a later write-capable continuation
   can override either value without any required integrated-phase audit of the full
   turn history; and
2. a fresh reviewer task ID and no-fork ancestry do not prove W2 independence when
   producer conclusions can be copied into the reviewer's prompt without a complete
   context-manifest and trace-visibility record.

Both are reachable with the current task-service interface while satisfying every
explicit check in the plan. They leave the revised M-5 control only partially closed
and block campaign dispatch as designed. The service's ordinary thread-read interface
does not promise model/thinking readback, but host session records expose per-turn
model and effort. The plan's explicit fail-closed rule is sufficient when authoritative
readback is unavailable; that operational limitation is not a third finding. The
blocker is that the plan never requires the available per-turn evidence to be checked
after launch.

This is an exact-subject review record only. It is not owner acceptance and grants no
contract materialization, implementation, routing activation, task or branch creation,
campaign dispatch, runtime, PR, Jira, provider, credential, CodeRabbit, merge, Gate 6,
recovery, research-execution, or result authority.

## 2. Exact identity, delta, and protected state

The linked worktree began detached at the required candidate. Detached `HEAD` and
`refs/heads/review/wp6-1-macro-plan-r2-6ff49a3` both resolved to
`6ff49a39c96686fb687879a8e3199a711c4dd346`. One deterministic switch to that branch
was made. Cwd, symbolic branch, `HEAD`, parent, candidate tree, and clean status were
then reverified before the review write.

The reviewed plan is exactly 70,309 bytes, valid UTF-8 without BOM, LF-only, and ends
in LF. Its Git blob and raw SHA-256 are recorded above. The complete
`8631f691aac7c501b6badf95632faa721987f656..6ff49a39c96686fb687879a8e3199a711c4dd346`
delta changes only the plan, with 453 insertions and 160 deletions. `git diff --check`
passes.

The protected identities are exact across the reviewed parent, candidate, and the
live remote-main commit observed during review:

| Canonical repository subject | Exact identity | Direct result |
|---|---|---|
| `.research-system/schemas/core/commands` | tree `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` | 87 files; unchanged |
| `.research-system/schemas/core/events` | tree `154ffc4bdde82fe903718734687e7a62797b1f69` | 86 files; unchanged |
| `.research-system/contracts/wp6-1-owner-source-catalogue.yaml` | blob `1adc66921ee9c90d8786ff173748150922f1035e` | unchanged |
| `research_system/command/lifecycle.py` | blob `8e02411d0b67679b08898714cbf3e23f9f4ffbf5` | unchanged |

The only authorized review write is this report. The plan, runtime, tests, schemas,
catalogues, decision records, PR/Jira/provider state, and every other path remain
untouched.

## 3. Independent reconstruction

### 3.1 Catalogue, activation, and allocation

The catalogue was parsed independently from the accepted machine source and checked
against 06d. Active rows were derived from `SchemaRegistry` plus
`EXACT_LIFECYCLE_BINDINGS`; the plan's four allocations were parsed as exact sets.

| Set | Count | Unique | Active overlap | Allocation overlap |
|---|---:|---:|---:|---:|
| accepted catalogue | 104 | 104 | n/a | n/a |
| active | 19 | 19 | n/a | n/a |
| remaining | 85 | 85 | 0 | n/a |
| C1 | 23 | 23 | 0 | 0 |
| C2 | 28 | 28 | 0 | 0 |
| C3 | 32 | 32 | 0 | 0 |
| R1 | 2 | 2 | 0 | 0 |

There are zero duplicate, missing, extra, or cross-campaign rows. The union of the
19 active rows and 85 allocated rows equals the 104-row catalogue exactly. The sorted
catalogue-set SHA-256 is
`3b4d92934f5789ffbf17a6443b4f69acf1709791f35999c094f544faa8b22466`; the sorted
remaining/allocation-set SHA-256 is
`6931b66a94913b284a1471e09f4303652d049e6398c8e90ae4476483a6b4d4c2`.

The active set consists of six Scope/Task foundation rows and thirteen Message rows.
`task.supersede` is active and is correctly absent from the four allocations; its
future role is a compatibility touchback, not a second row. The accepted catalogue
also reconstructs to 182 expanded edges.

The accepted 06m subject at `0e842969c770811edf5c81dcd7e4f7a647e050ad`
organizes the same lifecycle surface by semantic family and capability, not row. The
superseded 06o subject at `a557ab0e00d5d1497735f21b593823b12a5df866`
partitions the same 85 remaining rows as P2-P8 = 17/9/11/19/9/18/2. The remediated
23/28/32/2 redistribution preserves the exact set while improving producer/consumer
ordering.

### 3.2 Governing contracts and current seams

Direct inspection supports the plan's principal seam claims:

- the current authority subject map admits Scope, Task, and Message lifecycle subjects,
  not the remaining campaigns (`research_system/authority.py:153-164`);
- the ordinary command path constructs one event and appends `[event]`, while the
  legacy `ClaimDispatch` builder emits only `DispatchClaimed`
  (`research_system/command/service.py:1222-1245,3290-3292`);
- current exact lifecycle routing contains ten protected command/event pairs
  (`research_system/command/lifecycle.py:9-60`);
- protected `RegisterArtefact` requires the complete eight-field authority object,
  while protected Review and submission envelopes cannot alone enforce the plan's
  required non-empty current bijections; and
- W2 requires immutable Review bars, exact Task/Attempt/Artefact/Review closure, and
  independence evidence including context-manifest identity and trace visibility.

The remediation freezes the complete initial Artefact tuple or stops for a successor
identity (`06p:233-244`), freezes exact Review/Task joins with protected-envelope
reconstructibility or a successor identity (`06p:246-276`), and keeps C2 atomic on
failure (`06p:553-565`). These controls no longer permit plan-level invention or
self-attestation.

The `preserve_06i`/`supersede_06i` route is now exact and owner-selected
(`06p:278-309`). It preserves the distinction between G-RM-3 and G-RM-14 and does not
let C2 infer its own start. This matches 06i, P-044, the accepted G-RM-3 owner record,
and D-G6-3's exact-bytes-only boundary. W11 remains an inert, separately governed
81-row subject and supplies no materialization or runtime authority here.

Post-C3 is correctly a 102-row audit with exactly the two R1 rows inactive and no
Gate 6 claim (`06p:939-963`). Final 104-row closure occurs only after exact R1 review,
separate owner acceptance, authorized integration, and all 104 rows are active
(`06p:965-991`).

### 3.3 Focused checks

The exact changed behavior is planning-only. Two existing immutable-subject controls
were run through `C:/Users/steph/TDL/.venv/Scripts/python.exe` with pytest cache,
coverage, and bytecode writes disabled:

```text
tests/research_system/contracts/test_wp6_1_contract_materialization.py::test_wp6_1_materialization_binds_exact_104_row_multiset_and_182_expanded_edges
tests/research_system/contracts/test_wp6_1_stage2_owner_acceptance.py::test_wp6_1_stage2_owner_acceptance_preserves_the_accepted_core_tree
```

Result: `2 passed in 10.52s`. These checks establish the catalogue and protected-byte
claims only. No broader suite was warranted for a one-plan delta.

## 4. Severity-ranked findings

### R2-M-1 - Major - launch-only model evidence permits substitution on a write-capable continuation

1. **Claim.** The named model/thinking pair is part of packet identity, but the plan
   verifies it only for initial task launch. A later continuation can use a different
   model or thinking level and still satisfy the integrated record.

2. **Direct evidence.** The plan defines model/thinking as packet identity at
   `06p:650-659`. Initial task creation is deliberately no-write; a distinct
   launch-cleared continuation performs the repository work (`06p:671-675`). The
   `launched` receipt records actual model/thinking and initial history facts
   (`06p:757-768`). The `integrated` phase then computes Git root, branch, ancestry,
   paths, and collisions, but contains no final or per-turn model/history check
   (`06p:774-782`). Its nominal requested/observed mismatch rejection at
   `06p:797-805` therefore has only the launch observation specified as input.

   The current Codex task-service interface makes the bypass concrete:
   `send_message_to_thread` accepts optional `model` and `thinking` overrides on any
   follow-up. `read_thread` does not promise those fields in its response schema. A
   host-generated archived session for planning task
   `019fc903-ad2c-77d1-9279-5ee8be83ec1c` nevertheless contains a `turn_context` for
   each turn with `model=gpt-5.3-codex-spark` and `effort=high`, plus session metadata
   binding cwd, Git commit, source, and history mode. Authoritative per-turn evidence
   is therefore operationally available on this host, but the plan does not require
   the integrated validator to consume it.

3. **Failure scenario.** A Luna Max leaf or Terra Ultra central task passes no-write
   preflight and receives exact clearance. The launch-cleared follow-up overrides the
   task to another model or thinking level and writes the candidate. Correct root,
   branch, ancestry, allowlisted paths, and ownership make `integrated` pass even
   though the work was performed by a routing class the packet did not authorize.

4. **Impact.** The claimed model-routing control is an initial-state assertion, not
   an execution invariant. A mistaken or substituted continuation can perform
   semantic or central work outside the accepted capability/risk boundary while the
   strict ledger reports success.

5. **Required disposition.** Freeze that every write-capable continuation must omit
   model/thinking overrides, or prove an equivalent immutable task-configuration
   guarantee. Hash the complete ordered task-turn history. At integrated review,
   independently resolve every turn's model and thinking level and prove that every
   turn after clearance used the packet pair. Missing, reordered, unobservable, or
   mismatching turn metadata must fail closed before composition or review.

6. **Operational adjudication.** The plan's existing
   `task_metadata_unverifiable` stop is sufficient when the service cannot expose an
   authoritative readback; dispatch simply cannot proceed. The plan defect is not
   temporary metadata availability. It is the absence of a required full-turn audit
   when the service permits overrides and the host record can expose them.

7. **Affected contract/work.** `campaign-routing-ledger-v1`, its strict checker and
   negative suite, bootstrap, and every C1/C2/C3/R1 write-capable packet.

### R2-M-2 - Major - fresh task identity does not establish W2 reviewer independence

1. **Claim.** The plan proves a distinct reviewer task ID and no fork ancestry, but it
   does not bind what context the reviewer actually received. A nominally fresh task
   can inherit producer conclusions and still pass every specified independence
   check.

2. **Direct evidence.** The planned record carries free-form `context_policy` and
   `fork_policy` fields (`06p:740-742`). The launched receipt reads history/fork/context
   mode and parent/source IDs (`06p:757-768`); the review extension proves Sol Ultra,
   distinct identity, no author-history or fork ancestry, and a report-only path
   (`06p:770-772`). It does not require a context-manifest ID/hash, source/exposure
   list, producing-attempt relationship, prior roles, or trace-visibility evidence.

   W2 requires those exact facts. A verdict records reviewer actor/profile/session/model
   metadata, context-manifest ID/hash, producing-attempt relationship,
   trace-visibility evidence, and a derived independence grade; self-declaration proves
   nothing (`02-task-event-and-artifact-schema.md:769`). A verifier may not inherit
   producer conclusions or hidden reasoning unless an explicit delta-review policy
   requires and records that exposure (`02-task-event-and-artifact-schema.md:773-777`).
   The authority record also requires prior roles, context-manifest ID/hash, model
   family/version, session, and trace-visibility class
   (`02-task-event-and-artifact-schema.md:858-868`).

3. **Failure scenario.** A manager creates a new Sol Ultra task with no fork or parent
   task, but pastes the producer's findings, conclusions, or hidden rationale into its
   initial prompt or a later follow-up. The task ID, model, no-fork ancestry, Git
   subject, and report-only path all pass. The resulting review is nevertheless not
   the independent reconstruction required by W2.

4. **Impact.** Producer framing can be laundered through a fresh task identity into
   the exact-subject review gate. That undermines the principal semantic and authority
   check used before owner acceptance and integration.

5. **Required disposition.** Bind an immutable complete context manifest covering the
   initial prompt, every follow-up, attachment, source task/report, and visibility
   class. Record the producing-attempt relationship, prior roles, model/session facts,
   and permitted source set. Independently derive the W2 independence grade and reject
   inherited producer conclusions or hidden reasoning unless an accepted exact
   delta-review policy expressly permits and records that exposure. The review receipt
   and final report must bind the manifest ID/hash.

6. **Affected contract/work.** `campaign-routing-ledger-v1`, independent-review
   routing, C1/C2/C3/R1 exact-subject reviews, and any later acceptance relying on
   those reviews.

## 5. Disposition of every first-review finding

The first report at commit `3c27dc5c5dce5fddf579dd38f416ed84ba8ab184`
was used as a finding source only. Each finding was reconstructed against the new
exact subject rather than inherited as authority.

| Prior finding | Rereview disposition | Direct basis |
|---|---|---|
| M-1 non-composable authority | closed | `06p:183-226` separates plan eligibility, successor materialization, exact-byte acceptance, routing bootstrap, campaign dispatch, no-write allocation, and post-allocation Stephen clearance. Dynamic roots are observed before clearance at `06p:663-686,757-768`; no plan or byte acceptance composes into write authority. |
| M-2 full initial Artefact authority tuple | closed | `06p:233-244` requires every protected field/value or owner-authoritative derivation, reject/recompute/evidence treatment, canonical scope/restrictions, no self-attestation, and a successor-identity stop. C2 proof and atomic negatives appear at `06p:553-565`. |
| M-3 exact Review/Task joins | closed | `06p:246-276` freezes the immutable request bar, non-empty canonical tuples, current Task/Attempt/terminal-event/epoch/Artefact/Review sets, cardinality and bijection, protected-envelope reconstruction or successor identity, and atomic W2-permitted failure. |
| M-4 exact 06i route | closed | `06p:278-309,514-520,585-591` requires one owner-selected preserve/supersede route, exact governing identities and predicates, prevents G-RM-3 from substituting for G-RM-14, and keeps C2 start separate. |
| M-5 planned/launched/integrated evidence | partially closed | Independent authority witnesses, no-write allocation, observed task/root/model/history, Stephen clearance, Git-computed paths, negatives, and separate bootstrap/activation now exist at `06p:663-834`. R2-M-1 and R2-M-2 show that execution-turn routing and W2 context independence remain unenforced. |
| M-6 post-C3/final audit | closed | `06p:939-991` proves exactly 102 active after C3 with only the two R1 rows inactive and no Gate 6 claim, then requires exact R1 review, separate owner acceptance, authorized integration, and all 104 active before final audit. |
| m-1 canonical routing schema path | closed | `06p:790-795` uses `.research-system/schemas/contracts/wp6-1-campaign-routing-ledger.schema.json`, matching the repository's contract-schema convention. |

## 6. Strongest adversarial attacks and decision audit

### 6.1 Attacks that did not produce additional findings

- **Circular approval/write loop:** the plan does not require the post-allocation
  clearance to be committed into the worker candidate before it can authorize that
  worker. The Git path/commit/blob/raw-hash tuple at `06p:206-216` applies expressly to
  start/dispatch records; clearance is a distinct Stephen owner act over observed
  no-write facts. The successor routing contract must still freeze authenticated
  clearance provenance, immutable reference resolution, freshness, and no-self-hash
  rules. Because the future package is absent and the plan hard-stops before its
  accepted activation, this is a materialization acceptance test, not a present plan
  blocker.
- **Impracticable owner step:** clearance may cover a closed batch
  (`06p:202-215`), so the plan does not require a row-by-row owner decision. One
  no-write allocation wave followed by a bounded exact owner act is executable.
- **Stale-witness selection:** the validator must independently resolve current versus
  revoked/superseded state and statement provenance (`06p:747-755`), and strict mode
  rejects stale or wrong-scope evidence (`06p:797-805`). The future schema must encode
  lineage and precedence; until then dispatch is prohibited.
- **Row-by-row design:** campaign briefs, shared serial owners, vertical journeys, and
  the exact allocation keep capability campaigns as the orchestration unit.
- **Path collision:** planned literal ownership and integrated Git-computed actual and
  generated paths are both required (`06p:735-755,774-805,855-863`). The successor
  tests must prove campaign-wide uniqueness before live fan-out, but missing accepted
  package bytes already stop dispatch.
- **06i/G-RM substitution:** the explicit owner-selected route preserves the
  G-RM-3/G-RM-14 distinction and surviving predicates.
- **Premature portfolio or Gate 6 claim:** post-C3 and post-R1 audits are now distinct,
  and the plan grants no Gate 6 transition.
- **Implicit external authority:** `06p:1015-1044` denies runtime activation,
  protected-schema mutation, W11, PR, Jira, provider, credential, CodeRabbit, merge,
  owner-acceptance, and Gate 6 authority.

### 6.2 Decision audit

| Candidate decision | Rereview result |
|---|---|
| Capability campaigns C1/C2/C3/R1 with 23/28/32/2 rows | retain; exact and dependency-coherent |
| One serial central owner with bounded disjoint leaves | retain; actual turn routing must close R2-M-1 |
| Five-step non-composable authority ladder | retain; materially closes prior M-1 |
| Complete Artefact and Review/Task upstream freezes | retain; closes prior M-2/M-3 |
| Owner-selected preserve/supersede 06i route | retain; closes prior M-4 |
| Planned/launched/integrated routing evidence | amend; retain structure, add full-turn and context-manifest proofs |
| Bounded routing-package bootstrap and separate activation | retain; package remains absent and non-authoritative until separately accepted/activated |
| 102-row post-C3 audit and 104-row post-R1 audit | retain; closes prior M-6 |
| Canonical routing schema path | retain; closes prior m-1 |
| Independent Sol exact-subject review | amend; bind W2 context and trace evidence under R2-M-2 |

## 7. Required revision sequence

1. Extend the routing evidence contract so initial launch, every launch-cleared
   continuation, and integrated review bind one complete ordered turn history. Reject
   per-turn model/thinking substitution or missing authoritative turn metadata.
2. Extend the independent-review contract with the exact W2 context-manifest,
   source/exposure, producing-attempt, prior-role, trace-visibility, and derived-grade
   evidence. Add the copied-producer-conclusion bypass as a mandatory negative.
3. Bind the revised plan to a new exact commit/tree/blob/raw SHA-256 and obtain a fresh
   independent adversarial review. This reviewer must not implement or review its own
   remediation.

The remediation may retain the exact census/allocation, non-composable authority
ladder, full Artefact and Review/Task freezes, 06i route, campaign topology, model
classes, path ownership, PR cap, protected identities, W11 separation, and final-audit
structure.

## 8. Residual risks and non-authorities

- All successor schemas, checkers, tests, exact-byte acceptances, activations, and
  campaign dispatch records remain absent. The plan is not dispatch-ready, and their
  absence is an intentional hard stop rather than evidence that the future interfaces
  work.
- During review, local `main` remained `4f8b9b857bab1a7553af5e6ea3ef170608e7e18e`,
  while both the tracked and live remote `main` were
  `cbe24f86b65c2c49bd58eecf4b6786e8879c4704`. Protected WP6.1 trees, catalogue,
  lifecycle map, and the cited ClaimDispatch gap remain unchanged there. The plan's
  mandatory dispatch-time live-main rebind at `06p:416-417` is therefore sufficient;
  this dated snapshot drift is not an additional finding.
- The current ordinary task-read interface does not contractually expose model,
  thinking, or context-manifest facts. Host session records do expose per-turn model,
  effort, cwd, roots, source, and Git identity. If the accepted routing implementation
  cannot obtain an authoritative, complete readback, `06p:683-686,767-768` requires it
  to stop. No owner or manager assertion may fill the gap.
- The future clearance resolver must prove authenticated owner provenance, immutable
  external/reference identity, decision precedence, revocation, and phase freshness
  without requiring a record to embed its own hash or modify a worker's pre-clearance
  candidate. The future campaign manifest must also prove literal path/symbol/generated
  output/fixture uniqueness across the entire simultaneous allocation set.
- `AmendTask` currently preserves status while accepted readiness edges are narrower.
  The plan correctly routes this risk through `readiness-assessment-v1` and the
  separately versioned-successor stop rather than claiming the protected identity can
  express an unfrozen invalidation rule.

Acceptance of this report would accept only this report's exact evidentiary record.
It would not accept a revised plan, successor bytes, implementation, task launch,
campaign dispatch, routing activation, runtime binding, PR, merge, Jira transition,
external service action, owner decision, Gate 6 transition, recovery cutover,
research execution, or result claim.

## 9. Review evidence and change boundary

- Exact Git checks: cwd, permitted branch attachment, candidate, parent, tree, plan
  blob, and clean status.
- Raw-byte checks: byte count, UTF-8 validity, BOM absence, LF-only line endings,
  terminal LF, and SHA-256.
- Whole-delta and whole-plan review: the complete parent-to-candidate patch plus all
  1,095 lines of the remediated subject.
- Static set reconstruction: accepted catalogue, 06d, active registry/lifecycle
  bindings, and exact C1/C2/C3/R1 sets.
- Pinned cross-spec review: 06m, superseded 06o, 06a, 06d, 06i, P-044, D-G6-3,
  G-RM-3/G-RM-14, W2, W11, protected schemas, and current runtime/replay seams.
- Operational routing review: current task-tool schemas and service-generated session
  metadata, bounded without waiting for an unavailable richer API response.
- Focused immutable-subject checks: two exact tests passed as recorded in section 3.3.
- Prior-finding source: report blob
  `5ac94f367e775a81ebbb1fa9e8d02fc0af32ee17` at review commit
  `3c27dc5c5dce5fddf579dd38f416ed84ba8ab184`, treated as claims to reconstruct rather
  than authority.
- Review write boundary: this report only; no remediation and no self-review.
