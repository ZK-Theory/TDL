# Adversarial review: WP6.1 schema-fact authority annex proposal

**Date:** 2026-07-19  
**Review type:** independent focused design and authority review  
**Subject commit:** `6bcf1ea0870b5bc0aac5189454ae6eb3f6649090`  
**PR:** `#124` (`pipe/ars-wp6-1-task-lifecycle`)  
**Verdict:** `rework_required`  
**Findings:** 0 Critical, 5 Major, 1 Minor

## 1. Executive verdict

The proposal is not yet safe for Stephen to approve as Stage 1 fact authority.

Its mechanical catalogue closure is strong: the three bound source identities are exact; the YAML validates against the companion Draft 2020-12 JSON Schema; the independently parsed 06d tables yield exactly 104 ordered rows, 87 unique command types, 106 ordered event facts, and 86 unique event types; all 104 command and 106 event bindings match those source rows in order; the 17 shared-type rules cover exactly the repeated semantic types; all declared type references and row bindings resolve; and no generic or fallback payload branch exists.

Those successes do not cure five authority defects. The proposal expressly defers choices that its own two-stage gate says must be settled before generation; its four headline “complete” source objects omit directly required W2/W8 facts; its closed command envelope cannot represent the 06d authority-scope tuple; its primitive/identifier/enum model contradicts closed source constraints; and two admitted relational gaps cannot be generated without adding semantics absent from the annex. Approving the exact bytes would therefore either block generation or transfer fact-authoring authority back to the generator/reviewer at Stage 2.

No owner acceptance tuple is offered for this revision. The exact proposal identities below are review-subject evidence only, not a recommendation to accept them.

## 2. Exact subject and source identities

### 2.1 Proposal files at the subject commit

| File | Git blob | Raw committed-byte SHA-256 | Bytes | Line ending |
|---|---|---|---:|---|
| `docs/plans/agentic-research-system/implementation/06e-wp6-1-schema-fact-annex-proposal.md` | `eaf7cce2a7d33ca47496c47f2964e05d51698d8b` | `e1644ac6ac4a9df75fa9d67390b5f1fd2f2f8247d6b8b95867a09270b7fa1ae8` | 14,084 | LF, no BOM |
| `.research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml` | `cb4e77ff246b216d09160ff9dae3ba686461a101` | `09b205d75d64daed6ebeaaf0d20f70006d4c357c17933502aef24211c66e7b9c` | 263,060 | LF, no BOM |
| `.research-system/schemas/contracts/wp6-1-schema-fact-annex-proposal.schema.json` | `b0716e250e4a075d4c75adc957791104f06b2b06` | `99217e9d4ebda7eac1f20644d073179e9312025a00093a12e08f7f780f5d69c4` | 10,278 | LF, no BOM |

The Markdown's committed LF bytes are recorded without platform translation. Its raw hash above is the exact Git-blob content hash reviewed.

### 2.2 Bound sources at `fe5f1d40bc8f05f061317c677b5891cea0711249`

| Source | Git blob | Raw committed-byte SHA-256 | Bytes |
|---|---|---|---:|
| W2 `docs/plans/agentic-research-system/design/02-task-event-and-artifact-schema.md` | `7e09a9c49605663bb50163840fff3ae4c8212748` | `dd5f45ec91cb4c10f0e8d1d99341ad16745bec21f58400b6643285224870f9c6` | 65,105 |
| W8 `docs/plans/agentic-research-system/design/08-resource-checkpoint-and-operations.md` | `d26f24b9a6670b095d307fe531a7bb9b31c55311` | `84c80a8b499394fed65ed0d4e7fe1f4f9a85a8ccc23b299c85198e5d60e79a58` | 24,225 |
| 06d `docs/plans/agentic-research-system/implementation/06d-wp6-1-owner-source-catalogue.md` | `5e2eb60ca4419d1529506de6859fb027cff518af` | `96932fd752362eddb6da2da77bc0b56ccb8e83ced58e93c3b139e3248acb08f7` | 48,175 |

All three source byte streams are UTF-8/LF without BOM. The current checkout's 06d file is newer, but the review used the bound Git object, not mutable checkout text.

## 3. Major findings

### M-1 — Major: the Stage 1 gate leaves generator-time fact decisions unresolved

**Claim.** The proposal cannot be accepted as the complete fact authority consumed by Stage 2 while its decision register requires later choices “before generation” or requires generated schemas to invent unrepresented branches.

**Evidence.** Section 6 says only the accepted annex may be consumed to materialize the 173 schemas and that generated-schema acceptance is a separate hash review (`06e` lines 91–96). Yet the YAML keeps `access_mode` open and requires “a later owner-approved closed enum before generation” (lines 4388–4392); leaves the Git object grammar for “final generation” to choose (lines 4394–4398); permits shared discriminator names to be renamed before generation (lines 4418–4422); and requires kind-specific correction branches that the annex does not define (lines 4436–4441). The external-availability decision likewise defers a relational review of a shape that loses per-reference status (lines 4430–4435).

**Concrete failure scenario.** Stephen approves this exact YAML. A generator must then either (a) emit open strings despite a recorded requirement for closed values, (b) select an enum, Git grammar, discriminator, or correction branch not present in the accepted bytes, or (c) stop and request another fact-authority revision. Options (a) and (b) let Stage 2 author facts; option (c) proves Stage 1 was not complete.

**Impact.** The authority chain is circular: exact generated hashes cannot establish that the generator consumed only owner-accepted facts when material semantics were selected after the accepted annex.

**Disposition.** Fix now. Convert every “unresolved” item into one of two explicit states:

1. a selected Stage 1 rule sufficiently exact for deterministic generation; or
2. a declared runtime-only restriction that does not change generated schema bytes.

Any choice that changes generated bytes must be resolved in a revised annex before Stage 1 approval. The exact proposed text should say: “Generation is a total deterministic function of this accepted annex. No enum member, identifier grammar, discriminator, relational branch, required field, or schema-identity rule may be selected or renamed during generation.”

**Affected decisions/work packages.** All ten `proposal_decision/*` entries; D-G6-3; WP6.1 contract materialization; independent oracle authoring.

### M-2 — Major: the four advertised complete source objects omit directly required W2/W8 facts

**Claim.** `object/task_definition`, `object/dispatch_definition`, `object/artefact_manifest`, and `object/resource_request` are closed but incomplete. Because generated objects are closed, omitted facts are not merely optional: they become unrepresentable.

**Evidence.** The Markdown calls the four objects complete (`06e` lines 36–41). Their YAML definitions are at lines 141–275. Direct comparison against the bound sources identifies at least these omissions:

| Object | Direct source obligation | Missing or collapsed proposal facts |
|---|---|---|
| Task definition | W2 lines 361–371 | project and portfolio identity; independent-review requirements; root-binding requirements; source/import references |
| Dispatch definition/root binding | W2 lines 453–468 | optional target actor; expected branch within each applicable root; root provenance authority; the distinction between target role and profile is not closed |
| Artefact manifest | W2 lines 676–691 | aliases; producer profile; branch/worktree identity; creation time distinct from observation; availability-check evidence; dependency roles; typed dataset vintage/representation/parameters/seeds/sample restrictions; expected contract/schema IDs; accepted scope and consumer restrictions; external-data constraints |
| Resource request | W8 lines 126–141 and 212–224 | requesting actor/profile/authority; expected control-store position; sensitivity constraints; exclusive/shared resource declarations; operational-profile policy ID; projection evidence; release obligation; explicit `not_applicable` policy ID/rationale/applicability evidence |

The same pattern occurs outside the four headline objects. W2 requires a verdict to record reviewer actor/profile/session/model metadata and trace-visibility evidence (lines 756–769); `review.record_verdict` selects neither reviewer profile/session/model metadata nor trace-visibility evidence.

**Concrete failure scenario.** A `RegisterArtefact` payload containing the proposed 25-field manifest passes the generated closed schema while carrying no dependency roles, expected contract IDs, consumer restrictions, or external-data constraints. Conversely, a source-complete manifest that supplies those facts is rejected as having additional properties.

**Impact.** The generated schemas would certify reduced records as source-complete, defeating W2/W8 provenance, review-independence, root, resource, and use-authority controls.

**Disposition.** Fix now. Expand each object with one exact field or closed reusable subobject per direct source fact group. Where several source phrases are intentionally normalized into one field, add a machine-readable `source_fact_bindings` entry mapping every source fact to the exact field/subfield and prove no many-to-one collapse loses independent state. Re-run negative tests that remove each source fact and positive tests that include the complete object.

**Affected decisions/work packages.** Task, Dispatch, Artefact, Review, and Resource/operation family proposals; all rows that carry `definition`, `manifest`, `resource_request`, or review verdict facts; D-G6-3.

### M-3 — Major: the closed command root cannot represent 06d's authority-scope foundation

**Claim.** The 16-field command root omits `project_id`, although the bound normative 06d source defines every row's authority scope using `envelope.project_id`.

**Evidence.** The YAML command root is closed and has exactly 16 fields at lines 726–745; `project_id` appears only in the event root at line 753. Bound 06d lines 128–139 define the canonical authority scope for every row as `(envelope.project_id, authority_subject_kind, authority_subject_id_source)`. The Markdown nevertheless declares the 16-field root fixed and exact (`06e` lines 18 and 43).

**Concrete failure scenario.** A command includes `project_id` so the authority service can construct the required tuple; the generated command schema rejects it under `additionalProperties: false`. If the command omits it, the authority service cannot evaluate the exact source-defined scope without deriving project identity from an unapproved substitute.

**Impact.** Every command's foundational authority check becomes unrepresentable or implementation-derived. This is a material cross-spec contradiction, not a payload-detail gap.

**Disposition.** Fix now through an owner-visible amendment. The least surprising correction is to add typed `project_id` to `root/command` and change the root cardinality from 16 to 17. If a different field is to own project identity, 06d must be explicitly amended; it may not be silently reinterpreted by the annex.

**Affected decisions/work packages.** Command root/cardinality, all 104 command schemas, authority-subject tests, idempotency/receipt tests, D-G6-3.

### M-4 — Major: source-closed identifiers, numeric bounds, and compatibility are widened or misclassified

**Claim.** The primitive/enum layer accepts values prohibited by the bound sources and labels at least one widened enum `source_literal`.

**Evidence.** The generic `type/any_id` is only a non-empty string (YAML line 19) and is used for scope, lease, message, blocker, review, decision, checkpoint, resource, backup, and other identities throughout the family fields. The unresolved decision says these prefixes are unfixed (lines 4382–4387). In fact, W2 fixes `obj`, `els`, `msg`, `blk`, `rev`, `dec`, `ctx`, `val`, and other prefixes (W2 lines 143–166), while W8 fixes `rsq`, `rgr`, `rcf`, `els`, `hbt`, `pid`, `cpm`, `stp`, `rsd`, `rcv`, `bkr`, `opc`, and `opr` (W8 lines 76–94).

The compatibility enum adds `not_applicable` and marks the four-member domain `source_literal` (YAML line 53). W8's compatibility result is exactly `compatible`, `incompatible`, or `unable_to_determine`, and only `compatible` permits resume (W8 lines 285–298). W8 uses `not_applicable` for profile evidence-group dispositions, not as a compatibility verdict (lines 212–224).

Finally, `type/nonnegative_integer` and `type/positive_integer` set only lower bounds (YAML lines 15–16), while W2's P0 canonical domain limits all integers to `[-(2^53-1), 2^53-1]` (W2 line 203).

**Concrete failure scenario.** The generated schemas accept `message_id: "anything"`, `compatibility: "not_applicable"` on a resume request, and a counter larger than `2^53-1`. Those values respectively violate canonical identifier grammar, can bypass the fail-closed resume verdict, and cannot enter the accepted P0 canonical JSON domain.

**Impact.** Invalid identities can cross owner streams, an inapplicable checkpoint can be represented as a resume verdict, and numeric values can validate yet fail canonical hashing/interchange.

**Disposition.** Fix now. Add exact UUIDv7 types for every prefix already closed by W2/W8 and remap every applicable field; retain a generic ID only for classes genuinely left open. Split `checkpoint_compatibility` into the exact three-value verdict and a separate explicit applicability-disposition object. Add maximum `9007199254740991` to non-negative/positive integer types and test boundary ±1 mutations. Rewrite the ID-prefix decision to list only genuinely unresolved classes.

**Affected decisions/work packages.** `proposal_decision/id_prefixes`, `proposal_decision/numeric_policy_bounds`, attempt/checkpoint and resource/operation families, every family using `type/any_id`, canonicalization tests, D-G6-3.

### M-5 — Major: correction and recovery relations are not closed by the fact model

**Claim.** Two acknowledged relationships cannot be represented without information loss: correction kind-to-subject/projection selection and per-external-artefact availability.

**Evidence.** The correction family contains one `erroneous_record_id: type/any_id`, one closed kind enum, and untyped projection strings (YAML lines 636–646). Bound 06d lines 175–202 require each corrected-record kind to select exactly one named owner projection plus the governance correction index, with zero or multiple owner projections rejected. The decision register says generated schemas must add kind-specific `oneOf` branches (YAML lines 4436–4441), but neither those branches nor a kind-to-ID-type/projection map exists in the annex.

The backup family represents plural `external_artefact_refs` plus one scalar `external_availability` (YAML lines 700–727). W8 requires an external artefact manifest and availability status and requires restore to prove external availability before writer lease (W8 lines 346–357). The decision register itself asks whether availability must be per-reference, then retains the lossy scalar shape pending later review (YAML lines 4430–4435).

**Concrete failure scenario.** A correction declares kind `review` with an artefact ID and arbitrary `affected_projections`; the schema cannot reject the mismatched selector. A backup contains two external artefacts, one available and one missing; a single availability value either misstates one artefact or cannot express the restore-blocking state per reference.

**Impact.** Corrections can target the wrong owner projection, and restore evidence can collapse a mixed availability set into one misleading status. Both are relationship properties that must be closed before the generated schemas claim exactness.

**Disposition.** Fix now. Add a literal correction-variant mapping copied from 06d §1.4, with each kind bound to an exact subject-ID type and owner projection; the generator must materialize that mapping without invention. Replace parallel recovery values with a closed per-reference object such as `{artefact_ref, availability, evidence_refs}` and require an exact non-empty list where external artefacts exist.

**Affected decisions/work packages.** `proposal_decision/correction_subject_union`, `proposal_decision/recovery_external_availability`, correction rows, backup/restore rows, recovery acceptance tests, D-G6-3.

## 4. Minor finding

### m-1 — Minor: the human proposal restates fields the machine annex does not contain

**Claim.** The Rule evaluation family summary says numerator and threshold are explicit, but neither field exists in `family/rule_evaluation` or the `rule.evaluate` command/event selection.

**Evidence.** `06e` line 61 names “numerator, denominator, metric, threshold”. The YAML family at lines 617–633 and the row selections contain `metric` and `denominator`, but no `numerator` or `threshold`. Bound W2 line 817 requires metric and denominator, not numerator or threshold.

**Concrete failure scenario.** A reader treats the Markdown restatement as accepted authority and expects generated numerator/threshold fields; the deterministic generator following YAML cannot produce them.

**Impact.** Local authority ambiguity and avoidable review churn; it does not independently change the governing source requirement.

**Disposition.** Fix now with the next Major remediation. Remove “numerator” and “threshold” from the Markdown unless Stephen deliberately adds them as conservative proposals, in which case add exact typed YAML fields and decision basis.

**Affected decisions/work packages.** Rule evaluation family; proposal documentation; D-G6-3.

## 5. Decision audit

| Decision | Disposition | Reason |
|---|---|---|
| `proposal_decision/id_prefixes` | **amend now** | Most listed identities are already closed by W2/W8; enumerate only genuinely open classes. |
| `proposal_decision/access_mode_vocabulary` | **owner decision before Stage 1** | Current text requires a byte-changing decision before generation. Choose a closed enum now or explicitly accept open strings in generated schemas until a later runtime-only gate. |
| `proposal_decision/git_object_identity` | **owner decision before Stage 1** | Select the algorithm-tagged grammar now or explicitly accept non-empty strings in Stage 2; do not delegate the choice to generation. |
| `proposal_decision/numeric_policy_bounds` | **amend now** | Preserve genuinely open policy ceilings, but encode W2's already-fixed P0 integer maximum and exact units for each typed quantity. |
| `proposal_decision/open_policy_vocabularies` | **keep with explicit risk** | Open non-empty strings may be acceptable for contract generation if the later runtime gate blocks use until institutional vocabularies are accepted. |
| `proposal_decision/schema_id_scope` | **keep** | Distinct path-bound identities plus explicit shared normalization is a conservative, auditable Stage 1 rule; exact generated IDs remain Stage 2 observations. |
| `proposal_decision/shared_discriminators` | **amend wording** | The 17 current rules are structurally complete. Acceptance must freeze their exact names/values; any rename requires a revised annex, not a generator choice. |
| `proposal_decision/retention_and_sensitivity` | **keep with explicit risk** | Typed open values are honest while institutional vocabularies remain unavailable, provided runtime use remains blocked by a later accepted amendment/policy. |
| `proposal_decision/recovery_external_availability` | **amend now** | The scalar status cannot preserve the per-reference relation required for mixed sets. |
| `proposal_decision/correction_subject_union` | **amend now** | The required kind-specific mapping/branches are absent and cannot be invented at generation. |

No decision is rejected merely because it is conservative. The disposition distinguishes safe open strings whose closure can remain a runtime gate from choices that change the 173 generated schema bytes and therefore belong in Stage 1.

## 6. Conservative-proposal coverage audit

The machine annex contains 771 entries or fields marked `conservative_proposal`, grouped as follows:

- 15 primitive types;
- 14 reusable objects plus 95 object fields;
- 14 family universes plus 394 family fields;
- 104 command-payload selections;
- 106 event-fact selections;
- 17 shared-type rules;
- 10 unresolved decisions; and
- 2 root payload fields.

Every group received an explicit disposition:

- **Primitive/type proposals:** fail pending M-4; source-literal enums were separately checked and checkpoint compatibility fails.
- **Reusable objects and their fields:** fail pending M-2 and M-5; all 16 objects are closed and reference-valid, but four complete-source objects and two relational objects are incomplete.
- **Family fields:** structurally closed and reference-valid across all 14 families; fail for type widening under M-4 and admitted relational gaps under M-5.
- **104 command and 106 event selections:** pass exact row order, semantic type, family membership, field membership, uniqueness, and ordered event binding; they do not pass source-fact completeness because they select from incomplete family/object universes under M-2.
- **17 shared rules:** pass exact repeated-type coverage and variant membership. All discriminator fields are required in every applicable variant; all `single_normalized_fact` variants have identical family/field shapes.
- **10 decisions:** individually disposed in §5.
- **Root payload choices:** the closed family substitution rule is acceptable, but the command root fails M-3.

This grouping is an audit of every conservative entry class, not reliance on the candidate Python resolver. The resolver was not used to derive expected payload semantics.

## 7. Consistency matrix

| Invariant | Enforcement / evidence | Result |
|---|---|---|
| Exact immutable source identities | Git object and raw SHA-256 recomputation | **pass** |
| YAML conforms to exact companion JSON Schema | Draft 2020-12 schema validation | **pass** |
| Every contract/object schema is closed | top-level and all object `$defs` use `additionalProperties: false`; YAML object/payload flags are false | **pass** |
| 104 ordered rows, 87 command types | independent parse of bound 06d, then exact YAML comparison | **pass** |
| 106 ordered events, 86 event types | independent parse of bound 06d, then exact binding comparison | **pass** |
| 16/27 roots and 14 families | direct counts | **pass as declared; command root semantically fails M-3** |
| No duplicate IDs or dangling refs | independent uniqueness/reference walk | **pass** |
| No absent/unknown/fallback row | exact row-key equality and reference closure | **pass** |
| Shared semantic types cannot collapse | derived duplicate-type set equals all 17 rules; discriminator/shape checks | **pass** |
| Complete Task/Dispatch/Artefact/ResourceRequest groups | direct W2/W8 field-group comparison | **fail (M-2)** |
| Source-closed ID and enum vocabularies | direct W2/W8 comparison | **fail (M-4)** |
| Authority scope representable | command root versus 06d §1.2 | **fail (M-3)** |
| Correction and recovery relations closed | 06d §1.4/W8 restore comparison | **fail (M-5)** |
| Generation consumes only owner-accepted facts | two-stage gate versus unresolved decisions | **fail (M-1)** |
| No runtime authorization | status fields and `06e` lines 91–96 | **pass** |

## 8. Coverage and fixture gaps

The existing structural validation is necessary but cannot detect the Majors because it validates the annex against its own declared universe. The revised acceptance suite needs an independently authored source-fact oracle with at least these mutations:

1. remove each W2/W8 required fact from the four complete objects and from review verdict;
2. add each omitted source fact to prove the closed object accepts it after remediation;
3. wrong-but-well-formed prefixes for every W2/W8 identity class;
4. `not_applicable` as checkpoint compatibility and the three valid compatibility outcomes;
5. integer values at `2^53-1` and `2^53`;
6. missing `command.project_id` and wrong project in the 06d authority tuple;
7. correction kind/ID/projection mismatches for every 06d §1.4 kind; and
8. mixed external-artefact availability in one backup/restore record.

Expected and observed values in those tests must not both be populated by the annex generator or `resolve_operation_specs`.

## 9. Practicality and proportionality

The required correction is bounded to the fact-authority layer. It does not require runtime command, reducer, projection, migration, hook, or transition work. The most efficient route is:

1. resolve the byte-changing owner decisions and the command-root conflict;
2. repair reusable objects, exact ID/enum/number types, and the two relational mappings;
3. regenerate only the proposal YAML/JSON Schema/Markdown;
4. run the independent oracle against immutable sources; and
5. obtain a fresh exact-byte review before asking Stephen for Stage 1 acceptance.

That one-time cost is proportionate: repairing the authority annex now avoids propagating the same omissions into 173 schemas and 210 row/event observations.

## 10. Revision plan

### Immediate corrections

- Resolve M-3 and update root cardinalities.
- Restore all direct source facts in M-2.
- Remap closed identifiers, compatibility, and integer bounds under M-4.
- Encode the correction and external-availability relations under M-5.
- Remove the Rule evaluation restatement drift.

### Owner decisions

- Select or explicitly defer access-mode and Git-object grammars without leaving generation-time discretion.
- Confirm whether open policy/retention/sensitivity strings are acceptable in Stage 2 schemas subject to a later runtime gate.
- Confirm that exact current discriminator names are frozen by Stage 1.

### Later-work dependencies

- Independent exact source-fact oracle and mutation suite.
- Deterministic generation of the 173 schemas only after Stage 1 acceptance.
- Separate Stage 2 hash/review/owner decision.
- Runtime implementation and Gate 6 transitions remain unauthorized.

## 11. Residual risks after correction

Even a corrected annex will intentionally retain open institutional policy vocabularies unless Stephen closes them. That is acceptable only if the accepted schema and later runtime gate make the restriction explicit. Stage 2 must also verify generated content hashes in both the canonical worktree and a fresh checkout, using Git-object bytes rather than platform-translated text.

## 12. Verification evidence and change log

Performed from `C:\Users\steph\.codex\worktrees\cfe3\TDL` on branch `codex/wp6-1-r1-remediation` with clean subject worktree and exact local HEAD, remote branch, fetched `refs/pull/124/head`, `git ls-remote`, and GitHub `headRefOid` all equal to `6bcf1ea0870b5bc0aac5189454ae6eb3f6649090` before review.

Independent checks:

- raw `git show <revision>:<path>` source-byte hashing and Git object identity;
- raw proposal-file Git blob and SHA-256 recomputation;
- `Draft202012Validator.check_schema` and validation of the YAML instance: zero errors;
- independent Markdown-table parse of bound 06d: 104 rows / 87 command types / 106 event bindings / 86 event types;
- exact command-row order, command type, event order/type, ordinal, and binding-reference comparison: all pass;
- unique identifiers across primitives, enums, objects, families, command specs, event specs, and decisions: all pass;
- recursive type/reference closure: no dangling reference;
- derived shared-type set versus 17 rules: exact; every discriminator is required in every variant; normalized shapes are identical;
- direct W2/W8/06d source attack for fact groups, enums, identity prefixes, authority foundation, canonical numeric bounds, correction mapping, and restore evidence;
- `git diff --check` before report creation: pass.

Files edited by this review: only `docs/plans/agentic-research-system/reviews/adversarial-wp6-1-schema-fact-annex-review-2026-07-19.md`.

No annex, machine contract, JSON Schema, implementation, test, runtime path, review thread, remote branch, or PR state was changed by the reviewer.
