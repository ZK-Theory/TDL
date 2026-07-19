# Adversarial WP6.1 schema-fact annex R4 review — 2026-07-19

## 1. Review identity and verdict

- **Reviewed PR:** #124
- **Exact reviewed subject:** `890f8493174eadf860231e51373bbd87a0d5312c`
- **Subject branch:** `pipe/ars-wp6-1-task-lifecycle`
- **Review boundary:** fresh independent exact-byte review of the remediated schema-fact annex and its independent oracle
- **Verdict:** `rework_required`

| Severity | Count |
|---|---:|
| Critical | 0 |
| Major | 2 |
| Minor | 0 |

The remediation closes most of R3. The exact candidate is structurally valid, binds the
104 owner rows and 106 ordered event facts, closes the 17/27 roots, freezes the 173
schema identities, and makes all twelve conservative proposals explicit and
non-generator-authoritative. It does not yet close R3 M-2 or the independent-oracle
readiness blocker. Two source-required conditional relations remain absent, and the new
oracle accepts semantic mutations in precisely this review surface.

This review does not accept the annex on Stephen's behalf, authorize generation,
authorize runtime implementation, or assert Stage-1 readiness. Because the verdict is
`rework_required`, no Stage-1 approval tuple is issued.

## 2. Exact subject and byte identities

At review entry, local `HEAD`, `origin/pipe/ars-wp6-1-task-lifecycle`, freshly fetched
`refs/pull/124/head`, `git ls-remote` for the branch, and GitHub PR #124's
`headRefOid` all equalled:

```text
890f8493174eadf860231e51373bbd87a0d5312c
```

The worktree was clean. The three proposed authority objects at that subject were:

| Object | Git blob | SHA-256 | Bytes | Encoding |
|---|---|---|---:|---|
| `docs/plans/agentic-research-system/implementation/06e-wp6-1-schema-fact-annex-proposal.md` | `85531a6f6be3aa9e8e02ca77e51b7d152196dd51` | `81025f7fa3fcd092258aafc08ae9323a8bee70f3900ff2c3959d23160e9b728b` | 21,444 | UTF-8, LF, no BOM |
| `.research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml` | `ba55d14c800ad61f7058a413f9d0cceacd595906` | `7a7130b455a3f63934453c73ec2305e8fac25c32ef891062c4b58379d69de1fa` | 346,712 | UTF-8, LF, no BOM |
| `.research-system/schemas/contracts/wp6-1-schema-fact-annex-proposal.schema.json` | `32b6d5e24c226695ed795d65d572fb2c293b96fd` | `bc1aeb922f2913e314f7c256052f860d70245016be10ff66b36948e25bbfc1a3` | 21,016 | UTF-8, LF, no BOM |

The annex correctly binds immutable source revision
`fe5f1d40bc8f05f061317c677b5891cea0711249` and independently verified Git
blob/SHA-256 pairs for W2, W8, and 06d. No source document was treated as mutable
working-tree authority.

## 3. R3 finding disposition

| R3 finding | R4 disposition |
|---|---|
| M-1 — generator-time fact decisions unresolved | **Closed.** The generation contract is a deterministic total-function proposal with zero declared byte-changing choices, no runtime authority, and all twelve decisions frozen. |
| M-2 — advertised complete source objects omit required W2/W8 facts | **Not closed.** The previously missing field names are present, but two source-required conditional relations are not representable; see R4-M1. |
| M-3 — command root cannot represent project authority scope | **Closed.** The exact closed command root contains 17 fields including non-null `project_id`; the event root contains 27 fields. |
| M-4 — identifiers, numeric bounds, and compatibility widened/misclassified | **Closed.** Source-fixed prefixes, the P0 interoperable integer maximum, source-closed enums, and the three-value checkpoint compatibility relation are exact. Conservative cross-use and resource/operation unions are separately disclosed. |
| M-5 — correction and recovery relations not closed | **Closed at proposal level.** All 15 correction projections are explicit, recovery external artefacts use paired ID/hash/availability/evidence entries, and the writer-lease rule requires unique complete available evidence. |
| m-1 — unsupported terminology/proposal wording | **Closed.** The remediated prose and machine-readable decisions distinguish source literals from conservative selections. |

## 4. Major findings

### R4-M1 — The annex still omits source-required profile and review conditionals

**Claim.** The annex contains the relevant field names but does not encode the
conditions that give those fields their W2/W8 meaning. Therefore its claimed
deterministic 173-schema materialization still has a material source-fact choice left.

**Resource profile evidence.** Immutable W8 §11.1 says one unified
`ResourceRequest` schema has a required `operational_profile`, while the evidence is
profile-dependent:

- `trivial` requires explicit `not_applicable` benchmark, checkpoint,
  periodic-heartbeat, and recovery evidence;
- `bounded` requires the heartbeat, output-tail, stop, and checkpoint groups selected by
  its policy; and
- `long_running` requires the full applicable benchmark, heartbeat, process,
  checkpoint, stop/recovery, and backup obligations.

W8 lines 214–224 expressly distinguish these branches. W8 line 228 permits a
`provider_command_id` plus process-identity `not_applicable` rationale only for a
trivial provider-only command. W8 line 241 likewise permits explicit heartbeat
`not_applicable` only for the trivial profile.

The annex instead places one non-null `trivial_profile_evidence` object directly on
every `object/resource_request` (`YAML` lines 430–470). That nested object fixes a
trivial provider-command/process branch and fixes periodic heartbeat to the
`not_applicable`-only enum (`YAML` lines 396–429). There is no profile discriminator,
`oneOf`, relational rule, or decision-register entry that makes this object exclusive
to `operational_profile: trivial` or substitutes the bounded/long-running evidence
groups. The annex metadata also has no per-object-field requiredness rule. Thus either:

1. all listed object fields are generated as required, making bounded and long-running
   requests assert trivial-only evidence; or
2. the generator must invent optionality and profile branch rules, contradicting
   `byte_changing_choices_remaining: 0`.

Neither reading is a faithful deterministic materialization of W8.

**Conditional review ownership.** Immutable W2 §17.3 line 769 says
`approve_with_conditions` satisfies a gate only when acceptance policy declares the
conditions non-blocking **and records their owner**. The annex supplies a nullable
`family/review.conditional_approval_owner` (`YAML` line 982) and selects that name for
`review.record_verdict` (`YAML` line 1955), but it has no verdict/policy conditional
requiring a non-null owner when conditional approval satisfies a gate. Mere presence of
a nullable field does not encode the source relation.

**Consequence.** The Markdown's statement that the direct-source pass proves all five
M-2 groups complete is too strong. A generated schema may accept an unowned
gate-satisfying conditional approval, and the ResourceRequest branch is either
unrepresentable or generator-defined for two of its three closed profiles.

**Required remediation.** Preserve one unified outer ResourceRequest schema, but add a
closed discriminator relation for `trivial`, `bounded`, and `long_running` evidence.
The trivial branch must be the only branch that permits the cited process/heartbeat
`not_applicable` facts; the other branches must select their policy-required evidence
without silently inventing universal obligations. Add an explicit review conditional
that permits gate satisfaction for `approve_with_conditions` only when the policy
classifies every condition non-blocking and each condition has an owner. Freeze both
relations in the annex and exercise positive and negative mutations.

**Scope boundary.** This is schema-fact remediation only. It does not authorize a
dispatcher, reducer, policy engine, generated-schema publication, or runtime behavior.

### R4-M2 — The independent oracle accepts wrong field types and wrong source bindings

**Claim.** The 159-test oracle is structurally independent of the existing resolver and
materializer, but it does not independently establish the source semantics it is used
to clear.

**Evidence from inspection.** In
`tests/research_system/contracts/wp6_1_schema_fact_oracle.py`:

- `assert_complete_source_groups` compares only field-name sets for the high-risk
  objects; it does not compare each field's type, nullability, or conditional relation;
- `assert_all_binding_targets_resolve` checks that every declared target path exists,
  not that each source fact maps to its exact independently derived target; and
- `assert_required_source_facts_bound` independently requires only four Task dependency
  bindings and four recovery bindings, rather than the exact 209 source-fact tuples.

Fresh in-memory attacks ran all positive oracle assertions against deep copies of the
exact proposal. The oracle accepted each of these mutations:

```text
object/resource_request.operational_profile:
  enum/operational_profile -> type/nonempty_string

family/review.conditional_approval_owner:
  type/nonempty_string -> type/any_id

source_fact_binding resource_profile_revision target:
  object/resource_request.operational_profile_revision
  -> object/resource_request.operational_profile_policy_id
```

The attack output was:

```text
ORACLE_ACCEPTED_WRONG_RESOURCE_REQUEST_OPERATIONAL_PROFILE_TYPE
ORACLE_ACCEPTED_WRONG_CONDITIONAL_OWNER_TYPE
ORACLE_ACCEPTED_WRONG_SOURCE_FACT_TARGET
```

This is not merely a desire for more tests: R4-M1 demonstrates that a green oracle
currently coexists with material source-conformance defects on the same untested
dimensions. The proposal's readiness blocker `independent_source_fact_oracle` therefore
has not been independently satisfied.

**Required remediation.** Build the expected high-risk object facts independently from
the immutable W2/W8 bytes and compare exact `(field_name, type_ref, nullable,
conditional rule)` tuples. Independently freeze all 209 source-fact bindings, or derive
their exact tuple set from a separately maintained source oracle, and add mutations for
wrong-but-resolving targets. Add explicit negative tests for the ResourceRequest profile
branches and the conditional-approval ownership rule. The oracle must remain independent
of the proposal, current resolver, materializer, generated schemas, and companion JSON
Schema.

**Scope boundary.** The remedy changes only proposed fact authority and its review
oracle. It does not authorize generation or runtime implementation.

## 5. Structural and cardinality verification

The proposal YAML validates against its Draft 2020-12 companion JSON Schema with zero
errors, and the companion schema itself passes Draft 2020-12 schema validation.

Independent counts returned:

| Item | Count |
|---|---:|
| Primitive types | 54 |
| Source-closed enums | 26 |
| Reusable objects | 26 |
| Families | 14 |
| Command payload specs / row bindings | 104 / 104 |
| Ordered event fact specs | 106 |
| Unique command/event semantic types | 87 / 86 |
| Proposed generated schema identities | 173 |
| Command/event root fields | 17 / 27 |
| Shared schema rules | 17 |
| Source-fact bindings | 209 |
| Correction mappings | 15 |
| Conservative decisions | 12 |

All identifiers in the proposal are unique, all declared type/object/family/spec
references resolve, every reusable object and selected payload is closed, and all 209
declared source section identifiers occur in the exact immutable source documents.
Independent parsing of 06d recovered 104 owner rows, 104 command selections, 106 ordered
events, 87 unique command types, and 86 unique event types in exact order.

These passes establish structural integrity. They do not compensate for the missing
conditional semantics in R4-M1 or the circularly weak comparisons in R4-M2.

## 6. Conservative proposal review

All twelve decisions are explicitly labelled `conservative_proposal`, have
`generator_byte_change_allowed: false`, and remain pending explicit owner approval.
The separate disclosures for RuleEvaluation's proposed `val_` subject grammar and the
proposed resource/operation ID unions correctly avoid attributing those cross-uses to
W2 or W8. The access-mode vocabulary, Git object grammar, numeric relations, schema
identity rule, shared discriminators, policy-vocabulary boundaries, retention and
sensitivity classifications, recovery availability rule, and correction subject union
are likewise frozen rather than silently delegated to a generator.

No reviewer or generator acceptance is inferred from this assessment. Stephen's owner
approval remains an external decision over exact immutable bytes after a clean review.

## 7. Validation evidence

| Check | Result |
|---|---|
| Exact oracle suite: `test_wp6_1_schema_fact_annex.py` | **159 passed in 5.63s** |
| Fresh exact-head generated/materialization plus registry suites | **55 passed in 79.41s** (35 + 6 + 14) |
| Mutation suite collection | **175 tests collected** |
| Prior exact mutation execution at subject `a1cf1be...` | **175 passed in 261.38s**, preserved in the immutable R2 report |
| Mutation-suite delta from `a1cf1be...` to this subject | Git blob helper only: manual SHA-1 replaced with `git hash-object`; no test cases or production semantics changed |
| YAML against companion JSON Schema | **0 errors** |
| Companion Draft 2020-12 schema validity | **pass** |
| Fresh semantic oracle attack | **3 wrong-but-plausible mutations accepted; fail** |

The earlier 35/6/14 positive suites were rerun because they are bounded. The 175-case
suite was verified proportionately from its immutable exact execution evidence, current
175-test collection, and the exact intervening diff: only the already dispositioned
test helper changed from manual Git blob SHA-1 construction to Git-native hashing.
Rerunning the four-minute suite would not exercise either new finding.

## 8. Gate disposition

The exact candidate must remain:

```text
proposal_status: proposed_pending_explicit_owner_approval
stage_1_ready: false
generator_runtime_authority: false
```

Before a fresh review:

1. encode the three ResourceRequest profile branches inside the unified schema-fact
   model without trivial-only evidence leaking into bounded or long-running requests;
2. encode W2's gate-satisfying conditional-approval policy and ownership relation;
3. strengthen the independent oracle to compare exact high-risk field semantics and all
   exact source-fact bindings; and
4. add negative mutations proving all three defects are rejected.

After remediation, a fresh exact-byte reviewer must re-run the source oracle and issue a
new verdict. Only a clean review may present the exact Stage-1 approval tuple for
Stephen's explicit decision. Until then, no generation, runtime consumption, merge
acceptance, or transition-batch authority follows from this report.
