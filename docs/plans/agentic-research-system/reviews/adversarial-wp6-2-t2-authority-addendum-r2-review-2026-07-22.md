# WP6.2 T2 authority addendum R2 independent static conformance review

**Date:** 2026-07-22
**Verdict:** `rework_required`
**Finding count:** 4 Critical, 4 Major, 0 Minor
**Lifecycle:** `independent_review_r2_static`
**Workflow system:** standalone; no APM state, Memory Bank, manager history, author history, or runtime authority
**Review mode:** adversarial implementation-conformance review plus schema-contract tracing
**External review:** none; no CodeRabbit activity

## Exact subject and independence

| Item | Exact identity |
|---|---|
| Candidate subject | `36b51b0571bc312043e5325ac22aee5d323e70b2` |
| Candidate tree | `be7cd32faeb9aa44c9351e3101f05c0a6ae391a6` |
| Candidate parent | `69a0fee6171fc25f936c8e3e03343bfbd0338440` |
| Review branch | `review/ars-wp6-2-t2-authority-addendum-r2-static` |
| Candidate changed-path set | exactly 27 paths |

This is a fresh, self-contained review of the exact subject. The reviewer used only the
dispatch, the accepted Git objects listed below, and direct repository evidence. The R1
review was read only because P-038 incorporates it as an exact authority object. The
candidate handback was treated as a claim source, not an oracle. No author or manager
conversation was used.

## Authority binding

| Source | Commit / blob / raw SHA-256 | Disposition |
|---|---|---|
| Accepted P-038 proposal, `docs/plans/agentic-research-system/proposals/wp6-2-t2-r1-remediation-authority-ruling-2026-07-22.md` | commit `02f7b0b951b2141fb08374bbfcb3bcc368938907`; blob `64dc129bd8147728fe007d31db54b512d633eb1f`; SHA-256 `e309b56b8d2142791171e6cfab5150f43cb2c4339d923204d64e36d12479fa52` | Exact bytes verified; operative remediation authority. |
| P-038 acceptance provenance | commit `a919eff9a7565ffb35342eac28b6033ced0b665a` | Decision record names the same P-038 commit, blob, and raw hash. |
| R1 durable review, `docs/plans/agentic-research-system/reviews/adversarial-wp6-2-t2-authority-addendum-r1-review-2026-07-22.md` | commit `02f7b0b951b2141fb08374bbfcb3bcc368938907`; blob `f3b13fdf9422083f90bffa7a4e62759de96ddb6a`; SHA-256 `f290cd066024091d478e30ba5ab16fe103cb588799a3ac76d410344a803400e4` | Exact bytes verified; incorporated finding statement only. |
| P-037 proposal, `docs/plans/agentic-research-system/proposals/wp6-2-t2-cost-grant-authority-and-versioning-ruling-2026-07-22.md` | subject blob `2925f481ef95c3d079bd202531e11b9ea0f699e3`; SHA-256 `77d8b6087f2e36093f8b94995e8586b9219f12d6110168719fe5da142478c57e` | Read as the accepted cost/version ruling referenced by P-038. |
| W2, `design/02-task-event-and-artifact-schema.md` | subject blob `7e09a9c49605663bb50163840fff3ae4c8212748`; SHA-256 `dd5f45ec91cb4c10f0e8d1d99341ad16745bec21f58400b6643285224870f9c6` | Read, including IDs, commands, receipts, events, idempotency, replay, and tests. |
| W7, `design/07-runtime-adapters-and-policy-parity.md` | subject blob `088ace2c30e702ac8df8d58629559c480e09a5bd`; SHA-256 `c9acab47d6b729b82e8081cf32681c6ebe0ddfdaa072c1adca8f91e01d967a85` | Sections 9 and 10 independently enumerated below. |
| W8, `design/08-resource-checkpoint-and-operations.md` | subject blob `d26f24b9a6670b095d307fe531a7bb9b31c55311`; SHA-256 `84c80a8b499394fed65ed0d4e7fe1f4f9a85a8ccc23b299c85198e5d60e79a58` | Read for resource-grant, lease, stop, and proportionality obligations. |
| 06b, `implementation/06b-wp6-2-live-capability-plan.md` | subject blob `4b8bc7e12df98d5760b0aede7bb7d37dfc8d49b9`; SHA-256 `365e90089307958b7c833c635e74e3c63e65aa72e3c03945ea8f304431edfe38` | Exact candidate bytes read in full; T2 boundary at lines 66-77 and eight-seam matrix at lines 193-219. |
| Candidate handback, `handoffs/trials/gate6-wp6-2-t2-authority-addendum-exact-state-handback.md` | wrapper `bba49c11ef8cd37dee7fa571f712d77a954f6b16`; blob `58525864b62942159fc605d50abee9d2ddfa0046`; SHA-256 `36ab56c32d21c0cef29befd32b1202dccea323f0827dc18cc568d03e9ecd2048` | Identity verified; claims were independently checked rather than accepted. |

No authority object was inaccessible or contradictory. P-038 therefore remains the
conformance standard even where this review separately questions proportionality.

**Provenance correction.** Report commit
`38e9cfe3d4c3e2549f3f7b2b51fa98b6fa7c5409` incorrectly identified the W6 W4/W5
fixture-reservation addendum as 06b. The exact source above is the WP6.2 live-capability
plan. Re-evaluation against its complete 542-line content does not change the verdict or
counts. It independently reinforces C3's opaque SecretReference and eight producer-seam
boundary, C4's Task/dispatch/attempt binding, and M1's CostGrant ceilings and
reservation/reconciliation requirements. C1, C2, M2, M3, and I1 derive from other exact
authorities and are unaffected.

## Validation performed

- Verified the exact subject, tree, parent, branch, and clean worktree before review and
  again before this report was written.
- Verified the candidate's exact 27-path diff. The identity manifest contains 26 leaf
  entries plus its externally bound self identity; all 26 candidate Git blobs, raw
  SHA-256 values, LF-only bytes, and final newlines matched in both this review worktree
  and the read-only author checkout at `C:\Users\steph\.codex\worktrees\129f\TDL`.
- Verified that the 26-leaf identity graph has unique paths and no self/back edge; the
  manifest self identity is expressly external, so the recorded graph is acyclic.
- Verified the protected command tree `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea`,
  event tree `154ffc4bdde82fe903718734687e7a62797b1f69`, Receipt 1.0 blob
  `f204b3b71d6839bc866ba1251c8b87cc814ee0ce`, ProviderCommand 1.0 blob
  `9eb58609b9703674912e64f019db3cd4fb147a9c`, and ProviderReceipt 1.0 blob
  `8ac904e6c0b16e45034bcdc2221970d6a3ef13a8` are identical at parent and subject.
- Ran the two repository-owned focused T2 files unchanged, serially, through the
  pre-existing absolute interpreter `C:\Users\steph\TDL\.venv\Scripts\python.exe`,
  with bytecode, pytest cache, and coverage disabled: **165 passed in 12.09 seconds**.
- Ran `.claude/hooks/contract_binding_check.py --validate-only` through that same
  interpreter: **all gates passed against 102 contracts**. The full mode was not used
  because its Gate 3 hard-codes `uv run`, which could bootstrap a repository-local
  environment contrary to the dispatch. The focused T2 execution supplies the required
  behavioral run; the contract command supplies repository-owned schema and binding
  gates 1 and 2.
- Statically verified the known WP6.3 `validate-topology` pin at both parent and subject.
  Both contract blobs are `6c2aa7f476f067aedf5bb6e5db544aad153206d0`, both declare
  `fb1d000f96b31a69f9f4c0adc53e0115f89e6d18`, and both resolve the actual skill to
  `487d883f1df718b1d61139434dfce70ef5fbe05d`. It is pre-existing, not candidate drift.
- For the report-only provenance correction, verified the corrected 06b Git blob and raw
  SHA-256 above and read its exact candidate content in full. Per owner instruction, no
  tests, probes, or other validation commands were rerun.

Green tests establish the implemented behavior only. They do not establish completeness
when the schema, validator, expected values, and tests omit the same relation.

## Findings

### Critical C1 - Receipt 2.0 does not enforce its ordered event proof

1. **Requirement.** An accepted Receipt 2.0 must prove the canonical ordered event batch,
   including event IDs and transaction positions, before invocation; a duplicate must be
   equivalent to the original accepted proof and create no new effects; rejected and
   conflict outcomes must carry no event proof. Receipt major-version disposition must be
   exact.
2. **Representation.** `.research-system/schemas/core/receipt-v2.schema.json:65-130`
   represents event ID, transaction position, stream ID, resulting version, batch identity,
   and new-event count. Its outcome branches and duplicate annotation represent the broad
   status/version surface.
3. **Enforcement observed.** `validate_receipt_v2` at
   `tests/research_system/contracts/wp6_2_t2_authority_validation.py:483-518` enforces
   status-specific presence and duplicate field equality, but never checks unique or
   contiguous transaction positions, event order, event-count equality, stream/resulting
   version relations, or event IDs. `validate_command_relations` checks a separate event
   sequence but is not bound to the Receipt 2.0 object and does not check its event IDs or
   transaction positions.
4. **Independent expected source.** W2's receipt/event-position rules and P-038 C1 are
   independent of the candidate producer. They require relations absent from the validator.
5. **Existing tests.** `test_r1_red_c1_receipt_v2_proof_surface` checks only required
   top-level fields and version dispatch. `test_receipt_v2_outcome_relations_reject` checks
   only that a rejected receipt cannot contain events. There is no existing decisive
   positive ordered-position proof or negative order/position/count case.
6. **Trigger and impact.** Any consumer relying on a schema-valid accepted receipt can be
   given a non-canonical or internally inconsistent event proof. That defeats the
   pre-invocation evidence boundary even though status and duplicate field copying pass.
7. **Required change.** Bind schema validation and one semantic receipt validator that
   enforces exact event count, unique contiguous positions, canonical order, stream/resulting
   versions, event IDs, and the complete duplicate equivalence relation.
8. **Closure evidence.** Add existing-repository positive and negative tests for every
   relation above and show the receipt instance itself, rather than a parallel sequence,
   is the object validated. Until then C1 remains blocking.

### Critical C2 - Event replay reconstruction is keyed by command ID, not the W2 idempotency tuple

1. **Requirement.** All five accepted T2 event envelopes must permit collision-safe rebuild
   of the W2 tuple `(actor_id, authority_scope, command_type, idempotency_key)` and its
   payload binding from canonical event bytes.
2. **Representation.** All five schemas require `idempotency_key_hash` and `payload_hash`;
   they also carry command and actor/authority information. They do not carry an explicit
   authority-scope plus command-type tuple sufficient for the stated rebuild without
   consulting another producer.
3. **Enforcement observed.** `rebuild_idempotency_index` at
   `wp6_2_t2_authority_validation.py:412-450` builds
   `index[command_id] = (idempotency_key_hash, payload_hash)`. It detects disagreement only
   under the same command ID and separately de-duplicates an event-type/effect-ID pair.
   A repeated logical idempotency tuple under a distinct command ID is outside its key.
4. **Independent expected source.** W2 and the addendum at
   `design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md:76-82,292-295`
   independently define the tuple and event-derived reconstruction.
5. **Existing tests.** The positive rebuild test and both conflict/duplicate tests reuse a
   single command ID. No existing test proves a cross-command collision on the logical W2
   tuple or reconstruction without an external command producer.
6. **Trigger and impact.** Replay or rebuild after loss of a derived index can accept the
   same logical request under a new command ID, allowing duplicate grant, reservation,
   invocation, receipt, or reconciliation effects.
7. **Required change.** Make the complete logical key event-derived and key reconstruction
   by it, while retaining payload and effect collision checks. Do not derive the expected
   key from the same command producer being checked.
8. **Closure evidence.** Existing tests must show exact rebuild for all five envelopes and
   reject same-tuple/different-command and same-tuple/different-payload collisions. C2 is
   not closed by the current green tests.

### Critical C3 - Pre-issue evidence can pass semantic validation without schema-valid provenance

1. **Requirement.** The opaque SecretReference contract must bind a typed resolver and an
   ordered eight-seam PreIssueEvidenceManifest whose policy, scanner, safe-sentinel,
   producer, source-evidence, revision, hash, and freshness bindings fail closed when
   missing or stale. Semantic validation must require schema validity.
2. **Representation.** The SecretReference and pre-issue-manifest schemas represent the
   typed resolver, policy, scanner, sentinel identity/hash, exact seam order, producers,
   source evidence, outcomes, and aggregate hash. The representation is materially
   complete.
3. **Enforcement observed.** `validate_pre_issue_evidence` at
   `wp6_2_t2_authority_validation.py:453-480` checks supplied payload order, sentinel hash,
   serialized payload hashes/outcomes, and an aggregate. It does not invoke JSON Schema
   validation and does not examine policy, scanner, safe-sentinel identity, producer,
   source-evidence identity/revision/hash, or currency/freshness. The repository's own
   positive semantic fixture omits required top-level schema fields and uses records that
   do not meet the manifest schema, yet the semantic test passes.
4. **Independent expected source.** P-038 C3 specifically requires the typed manifest and
   its policy/scanner/source bindings. Correct 06b independently requires an opaque,
   byte-free SecretReference bound to the exact Task/dispatch/attempt, route/profile,
   adapter, and ProviderCommand (`implementation/06b-wp6-2-live-capability-plan.md:66-77`),
   plus the eight pre-invocation producer-seam failures and zero-side-effect boundary
   (`:193-219`). W7 supplies the provider command/receipt boundary. The candidate's
   expected-value module does not supply an independent proof because it is imported by
   both materializer and validator.
5. **Existing tests.** The positive and negative scan tests prove recursive checking of the
   supplied eight payload objects only. No existing decisive test requires schema validity
   or rejects missing/stale/mismatched policy, scanner, producer, or source evidence.
6. **Trigger and impact.** A caller can satisfy the semantic function with unbound evidence
   and no authoritative scanner/policy/source chain. This is a contract-stage proof gap;
   it does not assert that a live provider credential was observed or leaked.
7. **Required change.** Couple semantic validation to the exact manifest schema and resolve
   and compare every declared policy/scanner/source identity, revision, hash, and validity
   state against independent expected records before accepting the seam results.
8. **Closure evidence.** Repository-owned tests must demonstrate schema-valid clean evidence
   and fail closed for each missing/stale/mismatched binding. Reviewer-authored security
   payloads are neither required nor authorized to close this static defect.

### Critical C4 - Exact command subjects are not uniformly bound by ID, revision, and hash

1. **Requirement.** For each command, target, ordered write set, payload entity, expected
   version, and every authority subject must agree. Exact subjects include the prepared
   CostGrant, ResourceGrant, Task/Dispatch/Attempt, ProviderCommand, SecretReference,
   ProviderReceipt, and reservation as applicable.
2. **Representation.** The command schemas represent target/write sets and most subject
   triples. `IssueCostGrant` represents CostGrant and ResourceGrant triples but represents
   Task, Dispatch, and Attempt only as IDs
   (`issue-cost-grant.schema.json:149-209`). `AuthorizeProviderIssue` represents exact
   CostGrant, ProviderCommand, SecretReference, and evidence bindings, but reservation only
   as its newly derived ID. `RecordProviderReceipt` represents exact CostGrant,
   ProviderCommand, ProviderReceipt, and reservation triples.
3. **Enforcement observed.** `validate_command_relations` at
   `wp6_2_t2_authority_validation.py:521-591` correctly checks target/write-set/payload
   identity, key versions, deterministic reservation ID, event order, and resulting
   versions. For authority subjects it iterates only `*_id` entries from `EXPECTED_ROWS`
   and checks revision/hash only if either happens to be present. `EXPECTED_ROWS` lists
   Task/Dispatch/Attempt IDs without revisions/hashes and omits the prepared CostGrant from
   the Issue authority-subject list, so those exact bindings cannot be enforced.
4. **Independent expected source.** P-038 C4 and the addendum sections 4 and 11 independently
   require exact ID/revision/hash equality; W8 independently supplies ResourceGrant and
   reservation semantics. Correct 06b lines 66-77 separately require resolved use to bind
   the exact Task/dispatch/attempt, route/profile, adapter revision, ProviderCommand, and
   CostGrant.
5. **Existing tests.** Positive fixtures reproduce the same omissions. The subject-negative
   test mutates a RecordProviderReceipt reservation hash, and the missing-subject test
   removes the Task record, but no test rejects wrong/missing Task, Dispatch, Attempt, or
   prepared-CostGrant revision/hash.
6. **Trigger and impact.** An Issue command can be authorized against IDs whose revisions or
   contents differ from the intended Task/Dispatch/Attempt or prepared CostGrant. This
   weakens the authority subject before any runtime provider call.
7. **Required change.** Add and require every applicable subject triple, enumerate it in an
   authority-owned expected set, and make absence or inequality unconditionally fail. Keep
   the already-correct target, version, reservation, grant, and receipt relations.
8. **Closure evidence.** Provide decisive existing tests per command and per subject for
   missing ID, missing revision/hash, and mismatched revision/hash, with the expected record
   independent of the command producer.

### Major M1 - Arithmetic is correct, but cross-object rate evidence is not part of one mandatory gate

1. **Requirement.** Enforce input/output/total ceilings, integer-only values, explicit
   metered and zero-cost modes, ceiling division per token class, the refund equation, and
   identical currency/rate-evidence ID/revision/hash across grant, reservation, provider
   receipt, and reconciliation.
2. **Representation.** The CostGrant and reconciliation schemas represent the required
   ceilings, modes, rates, evidence identities, currency, consumed cost, and refund.
3. **Enforcement observed.** `validate_reconciliation` at lines 594-647 correctly rejects
   booleans/non-integers/negative values, applies all three ceilings, distinguishes rate
   modes, performs integer ceiling division, bounds consumed cost, and enforces refund and
   disposition. `validate_cost_evidence_relations` at lines 650-656 separately checks the
   four cross-object evidence fields. No mandatory composed validator requires both.
4. **Independent expected source.** P-037, P-038 M1, and W8 independently specify the
   arithmetic and cross-object agreement. Correct 06b lines 70-77 also require token and
   cost ceilings, reserved/consumed/refunded amounts, atomic reservation, and receipt
   reconciliation; its lines 211-219 bind the rejection and positive-path relations.
5. **Existing tests.** Existing tests are decisive for arithmetic, zero-cost authority, and
   the standalone evidence-equality helper. The normative crosswalk names only
   `validate_reconciliation` and omits the evidence helper and its test, so it does not
   prove the required composed gate.
6. **Trigger and impact.** Correct arithmetic can be accepted while records refer to
   different currency or rate evidence if a caller runs only the crosswalk-declared gate.
7. **Required change.** Define one mandatory orchestration validator that first validates
   the objects' schemas, then applies arithmetic and exact cross-object evidence equality.
8. **Closure evidence.** A positive four-object test and one negative per differing evidence
   field must call that single mandatory gate. M1's arithmetic portion is accepted; the
   composed evidence obligation remains open.

### Major M2 - W7 representation is broad, but field-level completeness and enforcement are unproved

1. **Requirement.** ProviderCommand 2.0 must cover every W7 section 9 obligation and
   ProviderReceipt 2.0 every section 10 obligation, with required representation,
   enforcement, and positive/negative evidence per obligation.
2. **Representation.** The command schema has nine corresponding groups and the receipt
   schema has eleven corresponding groups. However, W7 section 10 requires
   command/provider/profile/adapter/policy identities and hashes; `provider_binding` at
   `provider-receipt-v2.schema.json:147-200` gives the provider only an enum, not an exact
   provider identity/hash. The actual-provider completeness claim is therefore not fully
   represented.
3. **Enforcement observed.** `validate_provider_receipt_gates` enforces only complete versus
   diagnostic-only gate flags. It does not semantically bind the W7 fields. The crosswalk's
   one M2 row points to whole `/properties` objects rather than enumerated W7 obligations.
4. **Independent expected source.** W7 sections 9 and 10 at lines 160-192 are the independent
   source. The candidate `EXPECTED_CROSSWALK` is not independent of its generated crosswalk.
5. **Existing tests.** `test_r1_red_m2_w7_successors_are_complete` checks top-level required
   sets and native-ID inability handling. `test_incomplete_provider_receipt_is_diagnostic_only`
   checks completeness flags. Neither provides a positive and negative case for each W7
   field/gate obligation.
6. **Trigger and impact.** A structurally present group can omit or misbind a normative
   child while the finding-level crosswalk and tests remain green; an incomplete receipt
   can therefore be over-credited as W7-complete.
7. **Required change.** Add a W7 requirement-level crosswalk, close the provider identity/hash
   representation, and bind each obligation to a semantic validator and decisive tests.
8. **Closure evidence.** The following independent enumeration must have no `coverage gap`:

| W7 obligation | Candidate group | Static disposition |
|---|---|---|
| §9.1 provider-command ID and idempotency | identity/idempotency | represented; no obligation-level semantic/negative proof |
| §9.2 W2 command/message/dispatch and control position | `w2_binding` | represented; coverage gap |
| §9.3 W4 route/profile/eval/policy and exact routing snapshot | `w4_binding` | represented; coverage gap |
| §9.4 W3 candidate/packet/addendum/hash/two token gates | `w3_binding` | represented; coverage gap |
| §9.5 W5 purpose/visibility/prohibited material | `w5_binding` | represented; coverage gap |
| §9.6 W8 grant/lease/stop policy | `w8_binding` | represented; coverage gap |
| §9.7 operation class/rendered hash | `operation` | represented; coverage gap |
| §9.8 tools/roots/network/write/sensitivity/default deny | `effective_permissions` | represented; coverage gap |
| §9.9 receipt/timeout/expiry/retry/reconciliation | `lifecycle_expectations` | represented; coverage gap |
| §10.1 command/provider/profile/adapter/policy identities/hashes | command/provider bindings | provider exact identity/hash missing; coverage gap |
| §10.2 exposed native IDs | `provider_native_ids` | represented with typed inability; shallow positive only |
| §10.3 issue/ack/terminal timestamps | timestamps | represented; coverage gap |
| §10.4 delivered hash or inability | delivery evidence | represented; coverage gap |
| §10.5 token/accounting/capacity | accounting | represented; coverage gap |
| §10.6 attempted/allowed/denied/completed actions | tool actions | represented; coverage gap |
| §10.7 normalized/native terminal status | terminal status | represented; coverage gap |
| §10.8 output references and hashes | outputs | represented; coverage gap |
| §10.9 cancel/timeout/retry/duplicate/reconciliation | lifecycle evidence | represented; coverage gap |
| §10.10 W8 observations | resource/process observation | represented; coverage gap |
| §10.11 redaction/omission declarations | evidence disposition | represented; coverage gap |

### Major M3 - Receipt event stream identifiers bypass the canonical UUIDv7 rule

1. **Requirement.** Every canonical ID must use an exact lowercase UUIDv7 suffix and the
   accepted prefix rules; `pcmd_` and `prcp_` remain the accepted W7 exceptions to the
   usual three-letter prefix convention.
2. **Representation.** New first-class IDs generally use strict patterns. Receipt 2.0 event
   `stream_id`, however, is only a non-empty string at
   `.research-system/schemas/core/receipt-v2.schema.json:84-87`.
3. **Enforcement observed.** `validate_canonical_id` is strict for fields passed to it, but
   `validate_receipt_v2` never applies it to event stream IDs. The separate command relation
   comparison is not a schema-validity prerequisite for Receipt 2.0.
4. **Independent expected source.** W2 canonical ID rules and P-038 M3 independently require
   lowercase UUIDv7 and exact prefixes.
5. **Existing tests.** M3 tests cover SecretReference, CostGrant, pre-issue manifest,
   ProviderCommand, and ProviderReceipt top-level IDs. They do not cover Receipt 2.0 event
   stream IDs.
6. **Trigger and impact.** A schema-valid receipt can carry a noncanonical stream identity,
   undermining deterministic receipt binding and later replay/audit lookup.
7. **Required change.** Constrain receipt event stream IDs to the permitted canonical stream
   identifier union and make the semantic validator apply the same rule.
8. **Closure evidence.** Add a valid test for each permitted stream prefix and negative
   tests for case, UUID version/variant, malformed suffix, and disallowed prefix in the
   Receipt 2.0 event surface.

### Major I1 - The claimed independent crosswalk oracle and 214-path baseline are not independently reproducible

1. **Requirement.** The candidate crosswalk must be complete, independently sourced, and
   exact-set closed. Immutable accepted bytes and the manifest's protected baseline must
   be independently certifiable, not asserted by the same producer.
2. **Representation.** The crosswalk schema records seven finding rows and free-form lists.
   The identity manifest records a 214-path count and aggregate
   `b99f76f3406dc2bdf50b41051ffdb252681ea2ab7861d0fdc8a19da3dec52a65`, but no 214-row
   path/blob/raw-hash map.
3. **Enforcement observed.** The materializer imports `EXPECTED_CROSSWALK` and emits the
   crosswalk; the validator imports the same value and checks equality at
   `wp6_2_t2_authority_validation.py:391`. This is same-producer agreement, not an
   independent oracle. The materializer hard-codes the protected count and aggregate at
   `wp6_2_t2_schema_materializer.py:1564-1573`; manifest validation does not recompute them.
   The committed protected-path selector reconstructs 179 rows, not 214, so it cannot
   reproduce the declared aggregate.
4. **Independent expected source.** P-038 requires independent expected values and exact-set
   closure. Git parent/subject comparison independently proves the 27 candidate paths and
   named protected trees/blobs, but it cannot infer the absent 214-path membership list.
5. **Existing tests.** Existing tests prove generated bytes agree with the shared expectation
   module and that selected protected pathspecs did not change. No test reconstructs the
   declared 214-row set and aggregate from an independent declarative source.
6. **Trigger and impact.** A materializer/expectation omission can remain green in both the
   artifact and validator, and the broad immutable-byte claim cannot be audited exactly.
   This does not show an accepted-byte mutation; the independently checked named trees,
   blobs, and 27-path candidate diff are clean.
7. **Required change.** Store or derive the exact protected membership from an accepted,
   independently content-addressed source; recompute count and aggregate in validation.
   Author the requirement-level crosswalk oracle independently of the materializer.
8. **Closure evidence.** An exact-set comparison must reproduce all 214 path/blob/raw-hash
   rows and the aggregate, and a deliberately omitted crosswalk obligation must be rejected
   by an oracle that is not imported by the producer.

## Requirement/enforcement/existing-test matrix

| Requirement | Schema representation | Semantic validator | Independent expected source | Existing positive | Existing negative | Disposition |
|---|---|---|---|---|---|---|
| C1 Receipt 2.0 | Broad surface present | Status/duplicate subset only | W2 + P-038 | Required-field test | Rejected-events test | **Fail**: order/position/count/binding absent |
| C2 five event envelopes | Hash fields present | Rebuild keyed by command ID | W2 + P-038 | Five-schema/rebuild tests | Same-command conflict/effect tests | **Fail**: logical tuple collision unproved |
| C3 resolver/eight-seam evidence | Typed schemas present | Payload scan; provenance ignored; no schema prerequisite | 06b T2/§4 + W7 + P-038 | Eight supplied payloads | Supplied-payload detection | **Fail**: policy/scanner/source/staleness unbound |
| C4 command relations | Most fields present | Target/version/order strong; subject triples conditional/incomplete | 06b T2 + W2 + W8 + P-037/P-038 | Three command fixtures | Four relation mutations | **Fail**: Task/Dispatch/Attempt/prepared grant exactness incomplete |
| M1 cost/reconciliation | Complete arithmetic/evidence fields | Arithmetic strong; evidence equality separate | 06b T2/§4 + W8 + P-037/P-038 | Integer/mode/equality tests | Arithmetic/equality tests | **Fail**: no composed mandatory gate |
| M2 W7 successors | Broad grouped representation | Completeness flags only | W7 §§9-10 + P-038 | Top-level required sets | Diagnostic-only gate | **Fail**: provider binding and per-obligation coverage |
| M3 canonical IDs | Most strict; receipt stream loose | Strict helper not applied to receipt stream | W2 + W7 + P-038 | Selected top-level IDs | Selected prefix/case cases | **Fail**: receipt stream bypass |
| Identity/crosswalk closure | 26 leaf identities exact; 214 aggregate asserted | Shared oracle and partial protected selector | P-038 + Git objects | Byte/materialization tests | Selected mutation tests | **Fail**: independent 214-set/oracle absent |

## Failed static challenges and decision audit

| Challenge | Result | Decision consequence |
|---|---|---|
| Can Receipt 2.0 itself prove exact ordered positions and count? | No. | C1 Critical. |
| Can canonical event bytes rebuild the W2 logical idempotency tuple without command-producer dependence? | No. | C2 Critical. |
| Must semantic pre-issue acceptance first be schema-valid and provenance-current? | No. | C3 Critical. |
| Are all command authority subjects unconditional ID/revision/hash triples? | No. | C4 Critical. |
| Are ceilings, integer rounding, rate modes, refund, and cross-object evidence one mandatory gate? | Arithmetic yes; composition no. | M1 Major. |
| Is every W7 §9/§10 obligation independently mapped and decisively tested? | No. | M2 Major. |
| Does every canonical ID surface enforce lowercase UUIDv7/prefix rules? | No. | M3 Major. |
| Can the declared independent crosswalk and 214-path digest be reproduced from independent committed inputs? | No. | I1 Major. |
| Did candidate alter named immutable predecessor bytes? | No. | Pass; no finding. |
| Is the candidate 27-path/26-leaf identity set exact, LF-only, and acyclic? | Yes. | Pass; narrows I1 to the broader baseline claim. |
| Is the WP6.3 stale pin candidate drift? | No; identical at parent and subject. | Excluded from verdict. |

Four unresolved Critical findings affect pre-invocation authority proof, replay safety,
secret-boundary evidence, and exact authority subjects. The only defensible accepted-authority
conformance verdict is therefore `rework_required`. Green focused tests do not override
the failed independent static mappings.

## Bounded proportionality assessment

Three layers must remain distinct:

1. **T2 contract stage.** It is proportionate and necessary to keep raw provider
   credentials out of canonical commands, events, receipts, and artifacts, and to bind an
   opaque SecretReference by exact identity/revision/hash. Correct 06b lines 66-77 define
   that contract-stage boundary. This is a representation and authority-boundary
   requirement. C3 concerns the evidentiary binding of that contract, not a claim that a
   live secret path was exercised.
2. **T3/T4 runtime stage.** Verification of the actual resolver, provider transport,
   exception path, telemetry, logging, persistence, and redaction path belongs to later
   runtime work. Correct 06b lines 78-90 expressly place provider-specific canary execution
   and repetition of the T2 matrix in T3/T4. This review grants no runtime authority and
   draws no conclusion about those implementations.
3. **Reviewer-authored custom security probes.** Custom payloads, fuzzing, mutations,
   exploit demonstrations, credential-like inputs, scanners, penetration tests, and
   network/security tooling were intentionally omitted. Their omission is a validation
   limitation and residual risk, not automatically a candidate defect. None of the
   findings above depends on such a probe; each follows from schema/validator/source/test
   tracing or repository-owned unchanged tests.

The eight-seam pre-issue manifest is an accepted P-038 owner requirement, so this review
must enforce it and cannot weaken or rewrite it. Correct 06b lines 193-219 establish the
same eight producer seams as a binding pre-issue matrix and explicitly make post-run scans
defense in depth; the seam set is therefore not a reviewer invention. As a
design-proportionality matter, requiring an exact ordered manifest across all eight seams
at T2 is defensible as a fail-closed contract, but the manifest may still be an
over-specified T2 evidence form because 06b assigns actual provider-specific canary
execution to T3/T4. The owner should reconsider that allocation separately, deciding
which minimal T2 invariants are representation-checkable and which evidence must be
proved during runtime qualification. That future decision does not alter P-038's current
authority or this conformance verdict.

## Practicality and residual risk

The remediation is feasible without runtime implementation: it is bounded to schemas,
semantic composition, independently authored declarative expectations, and decisive
repository tests. Preserve all accepted predecessor bytes and create successor bytes only
where the accepted versioning ruling permits them.

Residual risk remains because this static review did not observe a real resolver,
transport, logging, or provider path; did not run reviewer-authored security probes; did
not inspect credentials, environment files, live secrets, or external services; did not
run the full 665-test framework; and did not execute the contract gate mode that invokes
`uv`. These omissions must be addressed only in an authorized later stage or by a safe
pre-existing test path. They are not filled by inference.

No runtime, provider call, T3/T4, T1b, eligibility, result, claim, publication, or
accepted-artifact mutation is authorized by this report.

## File-change log

This review task adds only:

- `docs/plans/agentic-research-system/reviews/adversarial-wp6-2-t2-authority-addendum-r2-review-2026-07-22.md`

The candidate subject and its 27 paths were not modified.
