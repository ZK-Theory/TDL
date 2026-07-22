# Adversarial R2 review — WP6.1 contract materialization remediation

**Date:** 2026-07-19  
**Verdict:** `rework_required`  
**Findings:** 0 Critical, 2 Major, 1 Minor  
**Immutable reviewed subject:** `a1cf1be3f9d6c372bff68fd9aac146d5cca8eefe`  
**Subject branch / PR:** `origin/pipe/ars-wp6-1-task-lifecycle`, PR #124  
**Original PR subject:** `e2bc89565d7227d271a7bd3098741daec390b2ce`  
**Approved owner-source revision:** `fe5f1d40bc8f05f061317c677b5891cea0711249`  
**Approved 06d object:** Git blob `5e2eb60ca4419d1529506de6859fb027cff518af`; canonical UTF-8/LF SHA-256 `96932fd752362eddb6da2da77bc0b56ccb8e83ced58e93c3b139e3248acb08f7`

## 1. Executive verdict

The remediation closes the prior R1 byte-portability, null-identity, mutation-coverage,
and split-provenance defects. The exact subject deterministically regenerates 87 command
schemas, 86 event schemas, the 104-row identity manifest, and the 104-row catalogue. The
checkout bytes equal the committed LF bytes. Direct validation returns the exact 104
rows and 182 expanded edges. The identity observations total 210, the dependency order
`173 schemas -> identity manifest -> catalogue` is acyclic, the 16-field command and
27-field event roots are closed, the `ClaimDispatch` two-stream relation is literal and
atomic, ScopeDefinition relations are closed, and all ten Message variants preserve
body/body-artefact XOR plus distinct command/event message identities. The three focused
files pass 216 tests when run separately, including all 175 committed mutation cases.

The subject is nevertheless not eligible for D-G6-3 owner acceptance. The content-hash
DAG faithfully freezes schemas that are not faithful materializations of their cited
W2/W8 contracts:

1. representative strict command schemas omit large groups of required immutable Task,
   Dispatch, Artefact, and ResourceRequest facts, reject those facts as unexpected, and
   accept invented values for owner-closed vocabularies; and
2. the semantic validator compares generated payloads with expected shapes obtained from
   the same in-code `_OPERATION_DATA` model that generated them. The nominal independent
   104-key oracle checks only a selected minimum subset, while independent exact semantic
   checking is limited to Scope and Message and does not independently normalize event
   facts.

Those are material conformance failures, not requests to broaden runtime scope. The
correct remedy is to complete and independently freeze the schema-level command/event
fact oracle for all fourteen families, regenerate the same proposed-only artifact DAG,
and obtain a fresh independent review. No dispatcher, reducer, projection, command
handler, owner acceptance, or other runtime implementation is authorized by this review.

The exact-head Codacy check also remains `action_required` because one mutation-test
helper manually invokes `hashlib.sha1` for Git blob identity. That is not a security or
content-integrity bypass—the contracts use SHA-256 and production provenance helpers use
Git itself—but the test should follow the already adopted Git-native convention before
the next gate review.

## 2. Scope, independence, and authority

This is a fresh R2 implementation-conformance review. The R1 report was read only after
the governing W2, W8, 06a, and 06d sources had been checked directly; every R1
remediation disposition was rebound to current code, artifacts, and executable tests.
No prior green summary or agent conclusion is treated as evidence.

The immutable subject was verified three ways before review:

- local `HEAD` = `a1cf1be3f9d6c372bff68fd9aac146d5cca8eefe`;
- `origin/pipe/ars-wp6-1-task-lifecycle` = the same SHA; and
- GitHub PR #124 `headRefOid` = the same SHA.

The authority boundary is exact:

- W2 v0.3 is accepted under P-027 but grants no implementation authority
  (`02-task-event-and-artifact-schema.md`, lines 5-10 and 72-80).
- W8 v0.2 is accepted under P-030 but grants no implementation authority
  (`08-resource-checkpoint-and-operations.md`, lines 3-8 and 53-62).
- 06a permits contract materialization before runtime and requires D-G6-3 acceptance of
  exact content identities before runtime implementation or command registration
  (`06a`, lines 49-59 and 146-175).
- 06d is the literal accepted expected set, requires a distinct reviewer and owner
  acceptance, and prohibits runtime/schema registry observations from producing or
  repairing expected identities (`06d`, lines 70-103).
- The candidate remains `proposed_materialized`, with review and D-G6-3 acceptance
  pending. It carries no self-asserted accepted state.

The PR changes contract artifacts, core command/event schema files, test-only generation
and validation support, the path-specific `.gitattributes` rules, and the historical R1
report. It changes no `research_system/` production module, command service, dispatcher,
reducer, projection, runtime handler, shared Gate 5 decision, fixture, result, or release
record. Recursive `SchemaRegistry` discovery makes the proposed schemas publicly
validateable, but no runtime handler is added and the pending lifecycle remains explicit.

## 3. Findings

### M-1 — Major — the strict payload schemas omit required owner facts and admit invented closed-vocabulary values

1. **Claim.** The 173 generated schemas are content-complete as files but are not
   semantically complete materializations of their cited W2/W8 record contracts. Closed
   payload objects accept partial records, reject directly required owner facts as
   unexpected, and treat several closed owner vocabularies as arbitrary non-empty
   strings.
2. **Evidence.** W2 requires the immutable Task groups identity, purpose (including
   bounded scope and non-goals), dependencies, research design, assurance, delivery,
   execution, authority, and provenance (`W2` lines 357-373). A Dispatch must bind model
   and assurance versions, all typed roots, branch/worktree/commit, capabilities,
   permissions, resource request, output namespace, deadlines, concurrency, and
   stop/Partial/escalation rules (`W2` lines 451-468). An Artefact manifest requires the
   complete identity, production, code/environment, location, integrity, input, research
   provenance, validation, authority, and operations groups (`W2` lines 674-691). W8's
   `ResourceRequest` requires the extensive identity, authority, host/root, resource,
   compatibility, timing, benchmark, stop, and cleanup fields (`W8` lines 126-141).

   The generated required lists are much smaller: `create_task.schema.json` lines 53-61,
   `issue_dispatch.schema.json` lines 54-61, `register_artefact.schema.json` lines 46-53,
   and `request_resource_grant.schema.json` lines 66-76. A direct public-
   `SchemaRegistry` probe validated minimally generated instances while 17 named Task,
   22 Dispatch, 21 Artefact, and 22 ResourceRequest facts directly represented by those
   owner groups were absent. Adding representative owner facts (`non_goals`,
   `expected_commit`, `input_hashes`, or `cpu_limit`) made each otherwise valid instance
   fail because the payloads use `additionalProperties: false`.

   The same public seam accepted `invented_verdict` for `RecordReviewVerdict`,
   `invented_availability` for artefact availability, `invented_profile` for the W8
   operational profile, and `invented_compatibility` for resume compatibility. Those
   fields are unconstrained strings in, respectively,
   `record_review_verdict.schema.json` line 50,
   `record_artefact_availability.schema.json` line 13,
   `request_resource_grant.schema.json` line 24, and
   `request_resume.schema.json` line 21. Their cited owners close the domains: W2 verdicts
   at lines 756-769, W2 artefact dimensions at lines 693-706, W8 profiles at lines
   212-224, and W8 compatibility at lines 285-298.
3. **Concrete failure scenario.** Stephen accepts the current exact hashes under D-G6-3.
   A later runtime either submits a minimal `CreateTask`/`IssueDispatch` that passes the
   accepted public schema while omitting the roots, authority, assurance, or provenance
   W2 requires, or it supplies the complete W2/W8 record and is rejected by the closed
   accepted schema. A made-up review verdict or operational profile is likewise
   shape-valid and can reach later semantic code unless every runtime consumer recreates
   the missing closed vocabulary independently.
4. **Impact.** D-G6-3 would freeze a materially incomplete authority contract. Later
   runtime work could not conform to both the accepted schemas and accepted W2/W8 source
   without a breaking re-materialization, and schema validity would overstate lifecycle,
   provenance, review, and resource safety.
5. **Recommended disposition.** Fix now; do not accept the current manifest/catalogue
   hashes and do not implement runtime consumers from them.
6. **Exact proposed change.** Create a literal, independently reviewable fact/type table
   for every command and event variant in all fourteen families. Bind every W2/W8
   required immutable fact, nested shape, nullability rule, identifier, closed enum,
   hash, timestamp, and command-to-event normalization. Reject invented enum members.
   Regenerate all 173 schemas and both contracts, then repeat raw-byte, hash-DAG,
   strict-shape, public-registry, omission, addition, wrong-type, and enum mutations.
7. **Affected decisions.** P-027 W2 record semantics, P-030 W8 operational contracts,
   P-036 plan boundary, and D-G6-3 exact content acceptance.
8. **Affected work packages.** WP6.1 T1 contract materialization and T8 binding closure;
   all later Task/Dispatch/Artefact/operator runtime tranches that would consume these
   schemas.

### M-2 — Major — payload expected and observed semantics share one producer outside Scope and Message

1. **Claim.** The strict semantic comparison is common-mode for most payloads. The
   materializer and validator obtain their command/event shapes from the same
   `_OPERATION_DATA`/`resolve_operation_specs` source, so equality proves deterministic
   reproduction of that model, not that the model exhausts W2/W8.
2. **Evidence.** The materializer resolves operation specs at
   `wp6_1_schema_materializer.py` line 346 and passes them into schema generation at
   lines 358-365. The validator separately calls the same
   `schema_source.resolve_operation_specs` at
   `wp6_1_materialization_validation.py` line 938, builds expected payload specs from it
   at lines 941-950, and compares generated shapes to those same-source shapes at lines
   930-932. The handwritten operation map supplies, for example, Task, Dispatch,
   Artefact, and ResourceRequest definitions at `wp6_1_schema_source.py` lines 722, 789,
   945, and 1056.

   The additional `wp6_1_schema_expectations.py` oracle does cover all 104 keys, but its
   test explicitly checks only `expectation.required_fields <= required`
   (`test_wp6_1_generated_schema_materialization.py`, lines 147-168). Its selected
   minimums do not include the omitted groups in M-1 and do not establish exact property
   sets, types, nested relations, or closed vocabularies. The validator's genuinely
   independent semantic routine is named
   `_verify_independent_scope_and_message_contracts` (line 797); beyond root/count/toy-
   field checks over all schemas, it performs exact domain semantics only for Scope and
   Message. There is no separate exact event-fact oracle for the other twelve families.
3. **Concrete failure scenario.** An author omits a W2 Task fact or assigns a W8 verdict
   the generic string rule in `_OPERATION_DATA`. The generator emits that shape; the
   identity DAG hashes it; the semantic validator reconstructs the same shape from the
   same map; the minimum oracle does not name the omitted fact or enum; all checks pass.
   The current M-1 omissions are an executed example of this failure, not a hypothetical
   mutation.
4. **Impact.** Green materializer, validator, registry, and mutation results cannot prove
   schema conformance for twelve domain families or their event facts. This undermines
   the independent expected-source boundary required by 06d section 1.1 and makes a
   coordinated producer defect durable under exact hashes.
5. **Recommended disposition.** Fix now as a separate assurance control from M-1.
6. **Exact proposed change.** Make the exact command/event fact oracle an independent
   literal authority that does not import `wp6_1_schema_source`, the materializer, or a
   generated schema. For every one of 104 keys, compare the exact command variant and
   each normalized event variant: property set, required/optional set, JSON types,
   nested shape, constants/enums, patterns, nullability, and command-intent versus event-
   fact identifier mapping. Add coordinated mutations that change generator and
   generated artifacts together and still fail against that independent oracle.
7. **Affected decisions.** 06d's producer/reviewer separation and D-G6-3; 06a T1/T8's
   requirement that a smaller self-consistent schema is a failure.
8. **Affected work packages.** WP6.1 contract materialization and binding-suite closure;
   later runtime conformance review, where observed registrations must remain a distinct
   comparison input.

### m-1 — Minor — the mutation helper reimplements Git blob SHA-1 and leaves the exact-head scanner action-required

1. **Claim.** One test helper manually invokes the SHA-1 security API even though the
   reviewed codebase has already adopted Git-native blob identity elsewhere.
2. **Evidence.** `test_wp6_1_contract_materialization_mutations.py` line 44 calls
   `hashlib.sha1(b"blob " + ...)`. Exact-head check run `88159405737` is completed with
   conclusion `action_required`; its sole annotation names that line and says
   `Detected SHA1 hash algorithm which is considered insecure.` By contrast,
   `wp6_1_schema_source.py` lines 120-132 and
   `wp6_1_materialization_validation.py` lines 203-215 use
   `git hash-object --no-filters --stdin`. Contract integrity remains separately bound
   by SHA-256.
3. **Concrete failure scenario.** The review subject is otherwise remediated but Gate 6
   remains non-green, or later maintainers misread a security-hash call as part of the
   acceptance integrity design and add suppressions rather than using the existing
   Git-native seam.
4. **Impact.** Static-analysis compatibility and audit clarity only; no demonstrated
   false acceptance, authority bypass, or weakened artifact integrity.
5. **Recommended disposition.** Fix before the next review because the exact-head check
   is action-required; retain Minor severity.
6. **Exact proposed change.** Replace the helper formula with
   `git hash-object --no-filters --stdin` (or call the already reviewed Git-native test
   helper) and retain independent raw-byte SHA-256 assertions. Do not suppress or label
   the general-purpose SHA-1 call as a security operation.
7. **Affected decisions.** None of the W2/W8 semantic decisions; D-G6-3 review hygiene
   and exact-head static-check readiness only.
8. **Affected work packages.** WP6.1 T8 test support.

## 4. R1 remediation disposition

| R1 finding | Current direct evidence | R2 disposition |
|---|---|---|
| M-1 Windows CRLF failure | Path-specific `.gitattributes` LF rules cover both YAML contracts and all generated command/event schemas; checkout bytes equal `git show HEAD:path`; both YAML files have zero CR bytes | Closed |
| M-2 null future schema identities | 173 schema files exist; all 210 command/event observations bind non-null schema SHA-256 and Git blob identities; `materialization_status=proposed_materialized` | Closed as identity materialization; semantic completeness fails independently under R2 M-1 |
| M-3 narrow mutation suite | 175 mutation cases are collected and pass, including 104 authority rows, ClaimDispatch relations/races, selectors, schema identities, runtime pairs, and same-path freshness | Closed for the named R1 mutation catalogue; R2 M-2 requires a stronger independent semantic oracle |
| m-1 immutable provenance verified but mutable checkout parsed | Both source and validator now return and parse the verified `git show fe5...:06d` bytes | Closed |
| R1 Codacy SHA-1 disposition | Production/test validator moved to Git-native identity, but one mutation helper retained the manual formula | Reopened narrowly as R2 m-1 because the current exact-head check is action-required |

## 5. Invariant → enforcement → test/attack matrix

| Invariant / control | Enforcement point at reviewed subject | Independent test or attack | Disposition |
|---|---|---|---|
| Immutable subject identity | Local HEAD, remote branch, PR API | all equal `a1cf1be3...` | Pass |
| Approved 06d raw source | revision/blob/SHA constants; `git show` bytes parsed directly | recomputed blob `5e2eb60...`, SHA `96932f...`; no checkout reopen | Pass |
| W2/W8 raw source provenance | exact revision/blob/SHA in `schema_source` | source bytes verified before operation resolution | Pass |
| Canonical Windows checkout bytes | `.gitattributes` LF rules; BOM/CR rejection | catalogue 432,828 bytes/0 CR; identities 144,969 bytes/0 CR; each equals Git object | Pass |
| Deterministic artifact set | materializer exact artifact count/check | `--check`: 175/175; 87 commands + 86 events + 2 contracts | Pass |
| Acyclic content-hash construction | schemas precede identities; catalogue alone references identity bytes | 173 -> identities -> catalogue; no self-edge or reverse catalogue edge | Pass |
| 104 normalized rows | annex parser plus exact key comparison | 50/41/13 partition; 104 unique keys | Pass |
| 182 expanded edges | literal closed state classes | direct validator returns 182; class mutations pass | Pass |
| 210 identity observations | per-row command + ordered event identities | 104 command + 106 event observations; 87/86 unique paths | Pass |
| Strict 16-field command root | fixed independent root set and closed root | every command root exactly 16; no `envelope` wrapper | Pass |
| Strict 27-field event root | fixed independent root set and closed root | every event root exactly 27 | Pass |
| Complete immutable payload facts | handwritten operation map and closed generated payloads | public registry accepts owner-fact omissions and rejects representative required additions | **Gap M-1** |
| Closed owner vocabularies | mostly generic `_field` string rendering | invented verdict/availability/profile/compatibility values validate | **Gap M-1** |
| Independent 104-key command oracle | `PAYLOAD_EXPECTATIONS` key closure and minimum subset | exact key count, but only `minimum <= required` | **Gap M-2** |
| Independent normalized event-fact oracle | shared `resolve_operation_specs` plus message-specific checks | no independent exact event facts outside Message | **Gap M-2** |
| Fourteen domain families | explicit map covers scope/task/dispatch/lease/attempt/checkpoint/message/blocker/artefact/review/decision/rule/correction/operator | all families have schemas; semantic depth is incomplete | Cardinality pass; conformance gap M-1/M-2 |
| ScopeDefinition relations | closed member/dependency/order/disposition objects and exact disposition enum | scope-focused independent tests/mutations | Pass |
| ClaimDispatch two-stream binding | two equal atomic facets; exact write set and stored Task/lease relation | relation/race/write-set mutations; both facets and ordered events checked | Pass at contract level; runtime behavior deferred |
| Ten Message variants | exact message-type constants, common facts, body XOR, command/event ID split | public registry and independent message checks; `new_message_id` never leaks into events | Pass |
| Same-path content freshness | SHA-256 recomputed from current schema bytes | same path/different bytes changes digest | Pass |
| Authority subject closure | all 104 rows bind kind/ID/scope/classes | 104-row authority mutation pass | Pass |
| Decision/RuleEvaluation non-compensation | distinct subjects/projections and closed mapping | coordinated substitutions reject | Pass at contract level |
| Correction selector closure | literal 15-member mapping and governance index | unknown/swapped/zero/multiple/missing-index mutations reject | Pass |
| Proposed-only lifecycle | `proposed_materialized`, pending review/acceptance, no candidate accepted fields | schema/artifact inspection and lifecycle tests | Pass |
| Public SchemaRegistry discovery | recursive strict schema registry | exact schemas validate and omission/extra probes execute through public seam | Enforced; exposes M-1 rather than compensating for it |
| No unauthorized runtime implementation | subject path inventory | no production module/handler/reducer/projection diff | Pass |
| No Gate 5 or scientific-result change | PR diff inventory | no fixture/result/release-decision changes | Pass |
| Required mutation catalogue | committed 175-case suite | 175/175 pass | Pass, subject to independent-oracle M-2 |

## 6. Decision audit

### 6.1 W2 accepted decisions (W2 section 29)

| Decision | Disposition at this materialization gate |
|---|---|
| Atomic JSONL batch per command | Keep; represented by closed event roots and ClaimDispatch batch contract; runtime publication remains deferred |
| Prefixed UUIDv7 IDs and scoped aliases | Keep; schemas carry identity fields, but complete Task alias/provenance materialization must be amended under M-1 |
| Separate Task and operational state machines | Keep; catalogue edges remain separate |
| Immutable messages / clearing as acknowledgement | Keep; ten variants and delivery/ack facts pass |
| Attempt and Task Partial/reopen | Keep; row/edge identities pass; complete immutable outcome facts require M-1 completion |
| Multidimensional artefact validation/use authority | Keep; reject the current open-string/incomplete payload rendering under M-1 |
| Exact ScopeDefinition revision for completion | Keep; independently enforced |
| Review verdict exact subject hash | Keep; subject hash facts exist; close verdict vocabulary and complete review facts under M-1 |
| Project-wide writer/control-store identity and non-shared compatibility paths | Keep; no runtime implementation in this tranche |
| Evidence-derived independence and delegated acceptance | Keep; runtime policy deferred; complete review/request facts under M-1 |
| Typed RuleEvaluation and regenerability evidence | Keep; Decision/Rule non-compensation passes; complete typed fields under M-1 |
| Verified snapshot anchors and reserved coverage | Keep; runtime/replay coverage remains later-work evidence |

### 6.2 W8 accepted decisions (W8 section 1)

| Decision | Disposition at this materialization gate |
|---|---|
| Distinct request/grant/lease/process/checkpoint identities | Keep; schema identities exist; complete record facts require M-1 |
| No resource ownership without valid grant | Keep; runtime enforcement deferred |
| Full-design feasibility before expensive dispatch | Keep; current ResourceRequest schema omits much of the required evidence, so amend under M-1 |
| Heartbeat is liveness evidence, not progress proof | Keep; current facts are prospective; runtime behavior deferred |
| Deterministic checkpoint compatibility | Keep; close compatibility vocabulary and complete checkpoint facts under M-1 |
| Separate stop/pause/resume receipts | Keep; catalogue rows remain distinct; complete stop evidence under M-1 |
| Orphan/late evidence remains unauthorized | Keep; proposed schemas do not self-accept |
| Restore proves store/chain/snapshot/availability before writer lease | Keep; complete BackupReceipt/restore facts under M-1 |
| Operational risk cannot lower epistemic risk | Keep; no scientific authority change |
| Specification is evidence only, not scheduler/runtime | Keep; subject adds no runtime implementation |

### 6.3 06a/06d/D-G6-3 controls

| Control | Disposition |
|---|---|
| 06d is the immutable owner-row source | Keep; provenance and 104/182 bindings pass |
| Runtime/registry observations cannot generate or repair expected rows | Keep for catalogue identities; amend payload semantics because validator shares the generation source (M-2) |
| Exact schema IDs/versions/blobs/SHA before runtime | Keep; hash mechanics pass but owner acceptance is prohibited until M-1/M-2 close |
| ClaimDispatch atomic two-stream relation | Keep |
| Decision/RuleEvaluation non-compensation | Keep |
| Correction selector closure | Keep |
| Proposed candidate cannot carry acceptance | Keep |
| Current subject receives D-G6-3 owner acceptance | Reject |
| Runtime implementation/registration begins from current subject | Defer; prohibited |

## 7. Coverage, practicality, and proportionality

The materializer is deterministic and fast (about one second for all 175 artifacts). The
direct semantic validator takes about four seconds. The 6 core contract tests take about
9 seconds and the 35 generated-schema tests about 38 seconds. The 175 mutation tests take
about 4 minutes 21 seconds on this Windows host because many cases rerun the full strict
validator. That cost is proportionate for an exact owner-acceptance gate but is too high
for every edit loop unless the suite keeps a fast structural tier and a full gate tier.

The present coverage is broad in cardinality and mutation breadth:

- exact 104 keys, 182 edges, 210 identity observations, 173 unique schemas;
- 104 authority mutations and the complete named ClaimDispatch/correction/runtime-pair
  regression set;
- strict object closure, path/hash/blob freshness, public-registry validation, Scope
  relations, and Message variants;
- no production/runtime or scientific-result surface.

The practical gap is depth, not test count. A smaller independent oracle with exact
typed fact rows would add little runtime overhead and materially improve assurance.
Generating both schemas and their semantic expectations from one large Python map is
convenient but defeats the reviewer boundary. The smallest effective control is a
separate literal exact fact/type table plus a coordinated-pair mutation, not another
large family of tests built from the same operation model.

## 8. Exact verification evidence

| Command/check | Exact result |
|---|---|
| `git rev-parse HEAD` | `a1cf1be3f9d6c372bff68fd9aac146d5cca8eefe` |
| `git rev-parse origin/pipe/ars-wp6-1-task-lifecycle` | same SHA |
| `gh pr view 124 --json headRefName,headRefOid,...` | head `pipe/ars-wp6-1-task-lifecycle`; same SHA; PR open |
| `python -m tests.research_system.contracts.wp6_1_schema_materializer --check` | `wp6.1 materializer verified 175 artifacts` |
| Direct `validate_wp6_1_contract_materialization(...)` | 104 rows; 182 edges; catalogue multiset `b37fc85caf2edfd47ea62a46373b9b83228b1c3e9de2eb48d1ec068a43a0f7fc`; identity multiset `4195f45758788f4e627ac92bac7a78c792ed8961435b81b288e1b5702dde1012` |
| Raw contract-byte probe | catalogue 432,828 bytes, 9,832 LF, 0 CR, checkout SHA-256 `c64ff7c201eee7d6470c2ebf2c12a1a9382165f18516e4e21e75d1d2b01f9492`, Git blob `8666a0214fa404be377e95b6ae3a93ac15fe7123`; identities 144,969 bytes, 2,535 LF, 0 CR, SHA-256 `52a8e0c9032eb4ef3e77dafed396b511016bc559164e46d8b1495c824dac931a`, Git blob `8a4ed4cd2a9fe390f08f2fbaa46bb3975eff765f`; both checkout objects equal `git show HEAD:path` |
| Count/hash DAG probe | 104 catalogue rows; 104 identity rows; 210 identity observations; 87 unique command paths; 86 unique event paths; catalogue embeds the identity-manifest blob/SHA; no reverse/self reference |
| `pytest ...test_wp6_1_contract_materialization.py -q` | 6 passed in 9.16s |
| `pytest ...test_wp6_1_generated_schema_materialization.py -q` | 35 passed in 38.37s |
| `pytest ...test_wp6_1_contract_materialization_mutations.py -q` | 175 passed in 261.38s |
| Aggregate three-file pytest attempt | timed out at 302.8s before completion; not credited; split exact-file runs above completed and passed all 216 collected tests |
| Public registry incomplete-fact probe | minimal Task/Dispatch/Artefact/ResourceRequest instances pass with 17/22/21/22 representative owner facts absent; adding `non_goals`/`expected_commit`/`input_hashes`/`cpu_limit` rejects |
| Public registry invented-vocabulary probe | invented review verdict, artefact availability, operational profile, and compatibility verdict all pass |
| `gh pr checks 124` and check-run annotations | Codacy fail/action-required with sole warning at mutation test line 44; CodeRabbit pass means `Review skipped: draft pull request`, not substantive review |
| Post-test worktree check | subject SHA unchanged; no tracked worktree change before this report |

The repository-local `.venv` lacked PyYAML and pytest, so validation used the installed
system Python 3.13.5 with pytest 9.0.2. All pytest runs set
`PYTHONDONTWRITEBYTECODE=1`, disabled pytest cache and repository coverage with
`-p no:cacheprovider --no-cov`, and routed `COVERAGE_FILE` outside the worktree. Existing
ignored `.coverage` and `__pycache__` artifacts predated the review and were neither
credited nor modified as subject evidence.

## 9. Revision plan

### Immediate required corrections

1. Build an independent exact command-and-event fact/type oracle for all fourteen
   families from the approved W2/W8 sources and literal 06d rows.
2. Complete every required immutable record group and every closed owner vocabulary;
   remove or justify duplicate/invented fields with an exact owner binding.
3. Regenerate the 173 schemas, identity manifest, and catalogue; recompute every row,
   multiset, Git blob, and raw-byte SHA-256.
4. Replace the mutation helper's manual SHA-1 formula with Git-native blob identity.

### Fresh review and owner decision

5. Re-run the exact raw-byte/hash/count tests, public registry probes, 216 focused tests,
   and coordinated generator/artifact mutations against the new immutable subject.
6. Obtain a fresh independent review that did not author the fact oracle or regenerated
   schemas.
7. Only after a zero-Major review may Stephen decide whether to accept the new exact
   repository paths, IDs, versions, blobs, and SHA-256 values under D-G6-3.

### Later-work dependencies

8. Runtime grant/dispatcher/idempotency propagation, command handlers, atomic event
   publication, receipts, reducers, projections, replay, concurrency, and no-side-effect
   negatives remain a separately authorized implementation phase.

## 10. Residual risks and hard stops

- Do not accept the current manifest/catalogue under D-G6-3.
- Do not treat 104/182/210/173 cardinality, exact hashes, or 216 green tests as proof of
  W2/W8 payload completeness.
- Do not start runtime implementation, registration, migration, or owner acceptance from
  `a1cf1be3...`.
- Do not repair this contract gap by widening payload objects with permissive
  `additionalProperties`; preserve strictness and complete the literal owner facts.
- Do not mutate the accepted W2, W8, 06a, 06d, R1 report, Gate 5 evidence, fixtures,
  results, decisions, or release records during remediation.
- Even after M-1/M-2 close, runtime behavior remains unproved by design. Contract-level
  ClaimDispatch, authority, correction, and Decision/Rule separation cannot substitute
  for later concurrency and unchanged-side-effect execution evidence.
- Recursive public schema discovery currently exposes proposed schemas. That is not a
  demonstrated runtime bypass because no handler/registration exists, but later runtime
  work must bind consumption to the separately accepted D-G6-3 identity rather than
  accepting any recursively discoverable proposal by ID alone.

## 11. Strongest attacks that passed

The following attacks did not produce findings and should be preserved:

- canonical Git bytes versus ordinary Windows checkout bytes, including direct CR/BOM
  checks;
- hash-dependency DAG construction and same-path byte mutation;
- exact 104-key, 182-edge, 210-observation, and 173-schema reconstruction;
- command/event root-field closure and unexpected nested fields;
- missing/extra/duplicate/swapped/aliased rows and test identities;
- all 104 authority-subject mutations;
- `ClaimDispatch` missing facet, foreign/stale Task, lease, write-set, race, and event
  ordering mutations;
- Scope member/disposition/dependency/order closure;
- all ten Message discriminants, universal facts, body XOR, and command/event identifier
  normalization;
- Decision/RuleEvaluation and correction-selector coordinated substitutions;
- candidate self-acceptance, accepted-field injection, and runtime path inventory.

They fail to rescue the subject because none supplies an independent exact payload-fact
oracle for the under-materialized domains.

## 12. Change log and completeness gate

- Files created or edited by this review: this report only.
- Reviewed subject, schemas, contracts, tests, runtime, manifests, decisions, plans, and
  prior reports edited: none.
- Temporary review scripts in the repository: none; all probes were inline/read-only.
- Push, merge, PR state, CodeRabbit request, review-thread reply/resolution, and Stephen
  acceptance actions: none.

Completeness check: every R1 finding; every W2 section-29 decision; all ten W8 section-1
decisions; all fourteen domain families; raw source and checkout bytes; artifact and hash
DAG counts; command/event roots; Scope; ClaimDispatch; Message variants; authority;
corrections; Decision/Rule non-compensation; independent command/event oracle boundaries;
public SchemaRegistry behavior; proposed-only lifecycle; mutation coverage; runtime and
Gate 5 path boundaries; practicality; and residual later-runtime risks have an explicit
disposition above.
