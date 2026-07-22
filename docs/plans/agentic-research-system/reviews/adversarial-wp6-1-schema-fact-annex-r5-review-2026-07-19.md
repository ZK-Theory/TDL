# Adversarial WP6.1 schema-fact annex R5 review — 2026-07-19

## 1. Review identity and verdict

- **Reviewed PR:** #124
- **Exact reviewed subject:** `f0e9ebd72948c5e012c9fea3078c2bfb7a69267c`
- **Subject branch:** `codex/wp6-1-r1-remediation` / `pipe/ars-wp6-1-task-lifecycle`
- **R4 reviewed subject:** `890f8493174eadf860231e51373bbd87a0d5312c`
- **Review mode:** fresh independent, read-only, exact-byte adversarial re-review
- **Verdict:** `rework_required`

| Severity | Count |
|---|---:|
| Critical | 0 |
| Major | 2 |
| Minor | 1 |

The remediation materially strengthens the candidate. The exact three R4 oracle
attacks are rejected, the oracle compares an exact ordered 229-binding ledger, and the
outer ResourceRequest discriminator has three closed no-fallback branches. R4-M2 is
closed as prescribed.

R4-M1 is not closed. The proposal still does not freeze a valid total relation for
review-verdict gate satisfaction, and its ResourceRequest branches do not freeze
non-null, complete nested operational evidence. The candidate's own validation
algorithm accepts negative verdicts and an empty conditional approval; its profile
oracle accepts empty evidence objects. These are material authority and operational
controls, not editorial gaps.

This review does not accept the annex on Stephen's behalf, authorize schema generation,
authorize runtime implementation, alter PR state, or infer any Gate 6 transition. No
Stage-1 owner approval tuple is issued because the exact subject has Major findings.

## 2. Exact-head and byte verification

At review start and immediately before the report write:

- cwd was `C:\Users\steph\.codex\worktrees\cfe3\TDL`;
- the symbolic branch was `codex/wp6-1-r1-remediation`;
- local `HEAD`, `origin/pipe/ars-wp6-1-task-lifecycle`, freshly fetched
  `refs/pull/124/head`, and GitHub PR #124 `headRefOid` all equalled
  `f0e9ebd72948c5e012c9fea3078c2bfb7a69267c`; and
- the worktree was clean.

The three proposed authority objects at the exact subject were:

| Object | Git blob | SHA-256 | Bytes | Encoding |
|---|---|---|---:|---|
| `docs/plans/agentic-research-system/implementation/06e-wp6-1-schema-fact-annex-proposal.md` | `79b7bb6e1c92808cf6ba7446d9155fe9199bc51d` | `851d599fc94a35959b985f9d60959f4a38febf5e9e1054ca313f3f26fb663b14` | 24,784 | UTF-8, LF, no BOM |
| `.research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml` | `1598453970f7ae59551fbb047b0506283cc80eb8` | `789a9b9747d7e595eb0298876dedb6193ca03f13184e9039416cf1274d913ea9` | 358,103 | UTF-8, LF, no BOM |
| `.research-system/schemas/contracts/wp6-1-schema-fact-annex-proposal.schema.json` | `976e7dd461d19618d2fb8e20ee0d0811b80eec63` | `d368fa323d2f379e5279edc0f1f4b73f4c5d41b1cbeb18ceab9f99bff485963b` | 24,703 | UTF-8, LF, no BOM |

The complete byte delta from R4 subject `890f849...` through the reviewed subject was
inspected. It consists of the immutable R4 report, the profile/review conditional
proposal amendments, companion-schema amendments, and the strengthened oracle/tests.
No reviewed subject file was modified by this review.

## 3. R4 finding disposition

### R4-M1 — profile and review conditionals

**Disposition: not closed.**

The outer ResourceRequest profile relation is now exact in branch name, matching field,
forbidden fields, and no-fallback behavior. The review condition object now includes a
typed actor owner, policy, evidence, and gate disposition, and the proposal preserves
the W2 rule that a review verdict never directly changes Task state. However, the
machine fact model and its own validation algorithms disagree on requiredness,
nullability, empty conditions, and negative verdicts. See R5-M1 and R5-M2.

### R4-M2 — independent semantic oracle

**Disposition: closed as prescribed.**

The oracle module imports only the standard library. It does not import the proposal,
resolver, materializer, generated schemas, validator, or companion JSON Schema. It
reads W2, W8, and 06d as exact immutable Git objects. Its independently maintained
ordered ledger contains 229 complete tuples:

```text
(binding_id, source_id, source_section, source_fact, target_path, decision_basis)
```

The proposal's observed 229 tuples must equal that ledger in order. The exact three R4
attacks now return:

```text
R4_ATTACK_1_REJECTED
R4_ATTACK_2_REJECTED
R4_ATTACK_3_REJECTED
```

Those attacks change the ResourceRequest operational-profile type, change the review
condition owner from `type/actor_id` to `type/any_id`, and redirect
`resource_profile_revision` to a different existing field. The current oracle rejects
all three.

R4-M2 closure does not make every new test sufficient. R5-M1 and R5-M2 identify new
semantic counterexamples that the candidate-authored tests do not bind back to the
machine proposal.

## 4. Major findings

### R5-M1 — The proposed gate predicate accepts negative and empty conditional verdicts

**Claim.** The annex does not freeze a complete, internally consistent Review verdict
to gate-satisfaction relation. One candidate-authored validation path permits invalid
acceptance.

**Evidence.** W2 §17.3 at immutable source line 769 states that
`approve_with_conditions` satisfies a gate only when the acceptance policy declares
the conditions non-blocking and records their owner. W2 §17.4 line 779 states that a
review verdict never changes Task state directly and that `AcceptTask` references the
satisfied review set.

The YAML rule at lines 131–142 covers only the `approve_with_conditions` discriminant.
Its predicate is named
`every_condition_non_blocking_with_non_null_owner_policy_and_evidence`; it does not
require a non-empty condition list and does not state the satisfaction disposition of
the other five verdicts. `type/review_gate_condition_list` has no `min_items` constraint.

The proposal's own validation algorithm at Markdown lines 189–200 is worse:

```python
def gate_satisfied(verdict, conditions):
    return verdict != 'approve_with_conditions' or all(... for x in conditions)
```

Fresh execution of that exact predicate produced:

```text
DOCUMENTED_GATE approve_with_conditions True   # conditions = []
DOCUMENTED_GATE reject True
DOCUMENTED_GATE changes_requested True
DOCUMENTED_GATE unable_to_verify True
```

Python's `all([])` is true, and every verdict other than `approve_with_conditions`
passes the first disjunct. The independent oracle helper happens to implement a
different, correct relation—only `approve` passes unconditionally; conditional approval
requires a non-empty valid list; all other verdicts fail. That helper is review
evidence, not proposal authority, and cannot repair contradictory authoritative bytes.

**Failure scenario.** A generator or later gate evaluator follows the validation
algorithm or the underspecified YAML rule. A `reject`, `changes_requested`, or
`unable_to_verify` review is counted in the satisfied review set, or an
`approve_with_conditions` record with no conditions satisfies vacuously. `AcceptTask`
can then reference an invalid satisfied set even though the verdict record itself does
not directly mutate Task state.

**Impact.** The design permits an invalid acceptance path and leaves a byte-changing
semantic choice despite `byte_changing_choices_remaining: 0`. The separation between
Review and Task transitions does not protect the gate if the satisfied set is wrong.

**Recommended disposition: fix now.** Freeze one closed total relation over all six W2
verdicts:

```text
approve                  -> satisfied
approve_with_conditions  -> satisfied only when conditions has minItems >= 1
                             and every item is non_blocking, typed-owner non-null,
                             policy-bound, and has non-empty evidence
changes_requested        -> unsatisfied
reject                   -> unsatisfied
unable_to_verify         -> unsatisfied
withdrawn                -> unsatisfied
```

Retain `no_direct_task_state_change`. Change the list/evidence types or the conditional
rule so non-empty conditions and non-empty evidence are machine-explicit. Correct the
Markdown predicate. Add positive and negative tests for all six verdicts, empty
conditions, mixed conditions, missing/null owners, empty policy/evidence, and the
separate `AcceptTask` satisfied-set reference.

**Affected decisions and work packages.** Amend
`proposal_decision/review_condition_gate_relation`, its companion-schema constants, the
review-condition source bindings, the oracle, and WP6.1 D-G6-3 Stage 1. This finding
does not authorize runtime implementation.

### R5-M2 — Resource profile branches permit null or empty operational evidence

**Claim.** The outer profile discriminator identifies the correct evidence property,
but the annex does not freeze the property's non-null and nested required-field
semantics. Consequently the listed W8 obligations can collapse to `null` or `{}`.

**Evidence.** W8 §11.1 immutable lines 214–224 requires one unified ResourceRequest
schema and distinguishes exact evidence groups for `trivial`, `bounded`, and
`long_running`. The YAML branch table at lines 119–130 correctly requires one matching
evidence field and forbids the other two.

The three outer fields at YAML lines 526–528 are nevertheless declared
`nullable: true`. In JSON Schema, property requiredness and nullability are independent:
a branch can require a property whose value is still `null`. The branch rule says
`required_fields`, but contains no non-null constraint. The oracle helper does require
the selected value to be non-null, so the machine proposal and oracle interpretation
again differ.

The nested problem is broader. Reusable object fields have `nullable` metadata and
`additional_properties: false`, but no `required` flag, no per-object
`required_field_names`, and no global rule stating that every listed reusable-object
field is required. The companion `fieldSpec` likewise has no requiredness attribute.
Thus closedness rejects unknown keys but does not decide whether known keys may be
absent.

The new positive tests make the gap observable. They assert that each of these is an
accepted matching branch:

```python
{"operational_profile": "trivial", "trivial_profile_evidence": {}}
{"operational_profile": "bounded", "bounded_profile_evidence": {}}
{"operational_profile": "long_running", "long_running_profile_evidence": {}}
```

Fresh attack output confirmed:

```text
PROFILE_HELPER_EMPTY_TRIVIAL_EVIDENCE True
```

No test requires the trivial receipt/not-applicable facts, the four bounded groups, or
the six long-running groups in an actual branch instance.

**Failure scenario.** A bounded request presents `bounded_profile_evidence: {}` (or a
matching field with `null` under the annex's declared nullability). The outer
no-fallback discriminator accepts the correct branch name, but no heartbeat,
output-tail, stop, or checkpoint disposition is present. The same bypass can erase all
long-running benchmark/process/recovery/backup evidence.

**Impact.** W8 operational obligations become optional in the exact proposal that is
supposed to freeze them. A later generator must invent requiredness or can generate a
schema that accepts evidence-free operations. This leaves byte-changing choices and a
likely operational bypass.

**Recommended disposition: fix now.** Use conditional presence rather than nullability:

1. make all three outer evidence fields non-nullable;
2. retain the exact required/forbidden discriminator branches to control presence;
3. add a global `all_listed_reusable_object_fields_required: true` rule or explicit
   `required_field_names` for every reusable object, with any genuine optional field
   separately and conservatively declared;
4. require non-empty applicability and receipt evidence where the proposal claims
   evidence is present; and
5. add actual nested profile fixtures rejecting `null`, `{}`, missing group members,
   wrong disposition types, extra members, cross-profile leakage, and fallback values.

**Affected decisions and work packages.** Amend
`proposal_decision/resource_request_profile_discriminator`, the reusable-object
generation rule and companion schema, the profile oracle/fixtures, and WP6.1 D-G6-3
Stage 1. This is fact-model remediation only.

## 5. Minor finding

### R5-m1 — The new blocking/non-blocking vocabulary is mislabelled source-literal

**Claim.** A reasonable conservative representation is attributed too strongly to W2.

**Evidence.** W2 §17.3 line 769 literally says the acceptance policy must declare the
conditions non-blocking. It does not define a closed two-value JSON enum named
`review_condition_gate_disposition` with values `non_blocking` and `blocking`. The YAML
enum and its field/binding label that vocabulary `source_literal`, and the oracle places
it in `SOURCE_CLOSED_ENUMS`. The surrounding rule correctly admits that the JSON
representation is a `conservative_proposal`.

**Failure scenario and impact.** An owner reviewing source-literal decisions is not
shown that `blocking` and the per-condition enum shape are selections for approval.
Direction is not changed—the complement is sensible—but provenance classification is
inaccurate.

**Recommended disposition.** Keep the two values if desired, but label the enum, field
mapping, and binding as `conservative_proposal`; retain the W2 all-non-blocking gate
predicate as source literal. Update the independent oracle accordingly.

**Affected decision.** `proposal_decision/review_condition_gate_relation` and its
source-fact ledger entries only.

## 6. Decision-register audit

| Decision | R5 disposition |
|---|---|
| `id_prefixes` | Keep. Source-fixed families and genuinely open IDs remain separated. |
| `rule_evaluation_subject_id_grammar` | Keep as explicit conservative cross-use. |
| `resource_operation_id_unions` | Keep as explicit conservative grouping. |
| `access_mode_vocabulary` | Keep pending owner approval. |
| `git_object_identity` | Keep; Git SHA-1 is correctly treated as an object-algorithm label. |
| `numeric_policy_bounds` | Keep; exact units and relational bounds remain frozen. |
| `open_policy_vocabularies` | Keep; generation cannot invent runtime policy. |
| `schema_id_scope` | Keep; 87 + 86 = 173 identities. |
| `shared_discriminators` | Keep; all 17 rules remain exact. |
| `retention_and_sensitivity` | Keep as a later versioned runtime-policy gate. |
| `recovery_external_availability` | Keep; unique complete availability evidence remains required before writer lease. |
| `correction_subject_union` | Keep; 15 exact no-fallback branches remain closed. |
| `resource_request_profile_discriminator` | **Amend now** for R5-M2 non-null and nested requiredness. |
| `review_condition_gate_relation` | **Amend now** for R5-M1's total verdict map/non-empty relation and R5-m1's provenance labels. |

No decision is accepted on Stephen's behalf by this table.

## 7. Consistency and coverage matrix

| Invariant | Enforcement / evidence | R5 disposition |
|---|---|---|
| Exact immutable W2/W8/06d sources | Git revision, blob, SHA-256 checks | Pass |
| 104 rows / 106 ordered events / 87 + 86 identities | independent 06d parser and ordered comparisons | Pass |
| 17/27 closed roots; command `project_id` | exact tuple oracle | Pass |
| Exact high-risk field types | independent semantic tuple constants | Pass for listed types |
| Exact ordered source bindings | independent 229-tuple ledger | Pass |
| Resource profile branch names/no fallback/no leakage | exact branch constant and mutations | Pass at outer property-selection level |
| Resource profile evidence is non-null and complete | no authoritative requiredness; empty objects accepted | **Fail, R5-M2** |
| Conditional approvals are owned/policy/evidence-bound | oracle helper covers non-empty valid examples | Partial |
| Complete six-verdict gate relation | absent/contradictory documented predicate | **Fail, R5-M1** |
| Review verdict does not directly change Task | exact rule constant | Pass |
| 15 correction kinds and projections | exact map/no fallback | Pass |
| Recovery writer lease only after exact available evidence | exact relation and mutation helper | Pass |
| Zero generator byte choices | two semantic choices remain | **Fail** |
| No generation/runtime/owner inference | status and readiness blockers | Pass |

## 8. Validation and live-check evidence

| Check | Result |
|---|---|
| Exact proposal YAML against exact companion JSON Schema | 0 errors |
| Companion Draft 2020-12 schema validity | Pass |
| Exact-head oracle suite | **184 passed in 1.42s** |
| Exact three R4 semantic attacks | All rejected |
| Ordered source-fact ledger | 229 exact tuples, exact order |
| Proposal objects | 55 primitive types, 27 closed enums, 29 reusable objects, 14 families, 14 decisions |
| Core row/schema counts | 104 commands, 106 events, 87/86 unique types, 173 identities, 17/27 roots |
| `git diff --check` over R4-to-R5 delta | Pass |
| Exact-head Codacy check run `88178545665` | Completed `success`; zero annotations |
| CodeRabbit | Not requested or used in this R5 review |

The 184 green tests establish the intended oracle behavior. They do not compensate for
the authoritative/helper divergences demonstrated by the fresh attacks. Codacy is exact
head and clean, but static-analysis success is not schema-fact acceptance evidence.

## 9. Smallest remediation packet

Keep remediation inside the six files already in the R4-to-R5 fact packet; do not touch
generated schemas or runtime code:

1. **YAML:** freeze a six-verdict total gate map; require at least one condition for
   conditional approval; make condition evidence non-empty; make profile evidence
   fields non-null; freeze reusable-object requiredness; correct provenance labels.
2. **Companion JSON Schema:** validate those exact new constants and requiredness facts.
3. **Markdown:** replace the faulty predicate and state the reusable-object requiredness
   rule explicitly.
4. **Oracle:** independently encode the total verdict relation, non-empty condition and
   evidence constraints, outer non-null profile fields, and complete nested-object
   requiredness.
5. **Tests:** attack all six verdicts, zero/mixed conditions, missing/null/empty
   condition facts, null/empty/incomplete profile evidence, every profile group, and
   cross-profile/fallback leakage.
6. **Fresh review:** bind the corrected exact bytes and rerun the full oracle before
   presenting any owner approval tuple.

The R4 report and this R5 report remain immutable evidence. Do not rewrite either.

## 10. Gate disposition and limitations

The exact candidate must remain:

```text
proposal_status: proposed_pending_explicit_owner_approval
stage_1_ready: false
generator_runtime_authority: false
```

This review did not generate any of the 173 schemas, run a dispatcher/reducer/projection,
exercise runtime policy, modify GitHub, request CodeRabbit, or infer Stephen's decision.
Those omissions are authority boundaries, not unreported validation failures.

After the bounded remediation, a fresh exact-byte independent reviewer must return zero
Critical and zero Major findings before giving the exact Stage-1 wording and tuple for
Stephen's explicit decision. Stage-1 acceptance would authorize only the separately
bounded generation step; it would not authorize runtime registration, dispatch,
reduction, projection, migration, or a Gate 6 transition batch.
