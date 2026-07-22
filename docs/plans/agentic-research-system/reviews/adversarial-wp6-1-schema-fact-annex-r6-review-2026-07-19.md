# Adversarial WP6.1 schema-fact annex R6 review — 2026-07-19

## 1. Review identity and verdict

- **Reviewed PR:** #124
- **Exact reviewed candidate:** `5f795e165cb8029aefcaf512da4e8076d7d64395`
- **Subject branch:** `codex/wp6-1-r1-remediation` / `pipe/ars-wp6-1-task-lifecycle`
- **R5 reviewed subject:** `f0e9ebd72948c5e012c9fea3078c2bfb7a69267c`
- **Review mode:** fresh independent exact-byte adversarial delta review
- **Verdict:** `rework_required`

| Severity | Count |
|---|---:|
| Critical | 0 |
| Major | 1 |
| Minor | 0 |

The R5 gate-relation and non-empty nested-evidence remediations are materially correct.
The total six-verdict map, conditional-approval minimum, typed owner, non-empty
evidence, conservative enum attribution, non-null selected profile evidence, complete
nested profile objects, and exact 229-row provenance ledger all withstand the bounded
attacks in this review.

One cross-rule contradiction remains. The new global rule requires every field listed
by every reusable object, while each `ResourceRequest` profile branch forbids two of
the three listed profile-evidence fields. Every branch therefore both requires and
forbids two fields, so no `ResourceRequest` instance can satisfy the frozen rules. The
oracle and documented helper validate the profile slice independently of the global
requiredness rule and do not detect that empty language.

No Stage-1 owner tuple is issued. This review does not accept the annex for Stephen,
authorize generation, authorize runtime implementation, alter PR state, or infer a
Gate 6 transition.

## 2. Exact-head and byte verification

Immediately before this report was written:

- cwd was `C:\Users\steph\.codex\worktrees\cfe3\TDL`;
- the symbolic branch was `codex/wp6-1-r1-remediation`;
- local `HEAD`, `origin/pipe/ars-wp6-1-task-lifecycle`, freshly fetched
  `refs/pull/124/head`, `git ls-remote` for both branch and pull ref, and GitHub PR #124
  `headRefOid` all equalled
  `5f795e165cb8029aefcaf512da4e8076d7d64395`; and
- the worktree was clean.

The exact authority objects were:

| Object | Git blob | SHA-256 | Bytes | Encoding |
|---|---|---|---:|---|
| `docs/plans/agentic-research-system/implementation/06e-wp6-1-schema-fact-annex-proposal.md` | `ff7872c11349e54e527cd8fd5668a6bdd7db2401` | `2bdf5c670ade0e6c648ae87956b5c63dabe02306281a36496535597d7897f51f` | 33,948 | UTF-8, LF, no BOM |
| `.research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml` | `b8ccd4ab032e33e31e9bac7ba0286d0d7e8175cd` | `942e0ae1eafe39fefc09a79483d3d4cd512c1784fc007e3a8939ddc7121fb9aa` | 359,497 | UTF-8, LF, no BOM |
| `.research-system/schemas/contracts/wp6-1-schema-fact-annex-proposal.schema.json` | `8f966317aec497b7a62c261def24e5cb0a1018e5` | `e086c48a564fb8172998d5f31f1733c98af49f179352209654bc1aaff5d009c4` | 30,769 | UTF-8, LF, no BOM |

The complete delta from `f0e9ebd...` was inspected. It contains the immutable R5
report and the proposal, companion-schema, Markdown, oracle, and test amendments that
claim to close R5. No reviewed subject file was changed by this review.

## 3. R5 finding disposition

| R5 finding | R6 disposition | Basis |
|---|---|---|
| R5-M1 — incomplete/unsafe review gate relation | **Closed** | Closed total six-verdict map; only `approve` is unconditional; conditional approval requires at least one complete non-blocking condition with non-null typed owner, policy, and non-empty evidence; four negative verdicts are unsatisfied; no direct Task-state effect. |
| R5-M2 — nullable/incomplete ResourceRequest evidence | **Not closed** | The selected evidence value is now non-null and each nested profile object is complete, but the new global requiredness rule contradicts the branch forbidden fields and makes every outer ResourceRequest branch impossible. See R6-M1. |
| R5-m1 — source-literal attribution of conservative enum | **Closed** | `enum/review_condition_gate_disposition` and its binding now use `conservative_proposal`; the exact ordered 229-ledger changes only that intended basis row. |

## 4. Major finding

### R6-M1 — Global reusable-object requiredness makes every ResourceRequest profile branch unsatisfiable

**Claim.** The proposed rules define an empty language for `object/resource_request`.
They cannot deterministically generate a usable ResourceRequest schema without making
an unrecorded precedence choice.

**Evidence.** The YAML at lines 151–156 freezes:

```yaml
reusable_object_field_rule:
  all_listed_reusable_object_fields_required: true
```

`object/resource_request` lists all three outer profile fields at lines 540–542:
`trivial_profile_evidence`, `bounded_profile_evidence`, and
`long_running_profile_evidence`. The three branch constants at lines 128–130 each
require the matching field and forbid both foreign fields. The companion schema
independently const-locks both the global rule and those branch arrays at lines
128–150. No exception, scoping rule, or precedence relation exists.

The Markdown makes the conflict normative rather than incidental. Line 38 says the
global rule makes every field listed by every reusable object required. Line 45 says
each ResourceRequest branch forbids the foreign evidence objects. The decision register
at YAML line 4929 repeats both propositions in the same selected generation rule.

A fresh independent set-intersection attack derived required fields from the outer
object and forbidden fields from each branch:

```text
GLOBAL_REQUIRED True
LISTED_PROFILE_FIELDS ['bounded_profile_evidence', 'long_running_profile_evidence', 'trivial_profile_evidence']
PROFILE_CONFLICT trivial ['bounded_profile_evidence', 'long_running_profile_evidence'] satisfiable= False
PROFILE_CONFLICT bounded ['long_running_profile_evidence', 'trivial_profile_evidence'] satisfiable= False
PROFILE_CONFLICT long_running ['bounded_profile_evidence', 'trivial_profile_evidence'] satisfiable= False
```

The companion schema passes because it validates the fact document, not the
satisfiability of the generated instance language. The oracle also misses the defect:
`_profile_object_valid` at lines 1424–1437 checks only nested evidence objects, while
`resource_profile_branch_allowed` at lines 1440–1460 constructs a projection
containing the three common profile fields and only the selected evidence field. It
does not combine `REUSABLE_OBJECT_FIELD_RULE` with the outer ResourceRequest field set.
The Markdown validation helper uses the same split model. Candidate-authored valid
fixtures therefore prove branch-local nested completeness but not cross-rule
satisfiability.

**Failure scenario.** A generator applies `all_listed_reusable_object_fields_required`
literally and emits all three evidence fields in the outer `required` array, then emits
the branch `not`/absence constraints. Every valid-looking ResourceRequest fails. A
different generator silently gives branch rules precedence and omits foreign fields,
but that changes the meaning of the global rule without an accepted machine-readable
decision. Either behavior violates the claimed deterministic total function with zero
byte-changing choices.

**Impact.** The 173-schema generation packet cannot be authorized from these bytes:
ResourceRequest is a core command/fact surface and its generated schema would be
unusable or generator-dependent. This is Major rather than Critical because no schema
generation or runtime activation has yet been authorized.

**Smallest remediation.** Keep the unified three-branch discriminator and complete
nested objects, but make requiredness precedence explicit in one machine-readable
place. The narrowest acceptable rule is:

1. all listed reusable-object fields are required **except fields whose presence is
   controlled by an `object_variant_rules` entry for that object**;
2. for a selected variant, every `required_fields` member is required and non-null,
   every `forbidden_fields` member is absent, and all other non-variant listed fields
   remain globally required; and
3. all fields listed inside the selected nested evidence object remain required under
   the ordinary global rule.

Encode that exception/precedence in the YAML, companion schema, Markdown, decision
register, and oracle rather than relying on prose or generator convention. Add a
cross-rule satisfiability check that derives the outer required set after excluding
variant-controlled fields, proves at least one complete witness for each of the three
branches, rejects any required/forbidden intersection, and mutation-tests deletion or
reversal of the exception/precedence rule.

**Affected decisions/work packages.** Amend
`reusable_object_field_rule`,
`proposal_decision/resource_request_profile_discriminator`, the companion schema, the
source-fact oracle/tests, and WP6.1 D-G6-3 Stage 1. Do not change the W8 profile facts,
the three branch names, nested evidence content, or authorize runtime work.

## 5. Six-verdict gate and profile-evidence audit

Fresh direct helper probes returned:

```text
GATE approve empty=True positive=True
GATE approve_with_conditions empty=False positive=True
GATE changes_requested empty=False positive=False
GATE reject empty=False positive=False
GATE unable_to_verify empty=False positive=False
GATE withdrawn empty=False positive=False
GATE_ATTACK blocking False
GATE_ATTACK null_owner False
GATE_ATTACK empty_policy False
GATE_ATTACK empty_evidence False
```

The structural list deliberately permits zero items so unconditional approval and
negative verdict records remain representable. The gate rule alone imposes
`approve_with_conditions_min_items: 1`. This is internally coherent. The four negative
verdicts remain structurally representable and gate-unsatisfied. The gate rule has
`task_state_effect: no_direct_task_state_change`.

The three selected outer evidence fields are non-null. Trivial, bounded, and
long-running nested evidence fixtures are exact closed objects; deleting a nested
group, using `{}`/`null`, leaking a foreign profile field, using empty claimed evidence,
or changing the trivial applicability disposition is rejected. Those local properties
pass. They do not cure R6-M1's outer cross-rule contradiction.

## 6. Provenance, closure, counts, and decision audit

- Immutable W2, W8, and 06d Git blobs and SHA-256 identities still match the frozen
  `fe5f1d40bc8f05f061317c677b5891cea0711249` source revision.
- The standard-library-only oracle retains the exact ordered 229-tuple source-binding
  ledger and the three R4 authority attacks. The candidate differs from R5 in exactly
  one ledger row: the review-condition gate-disposition basis becomes
  `conservative_proposal`; order remains unchanged.
- Exact counts remain 104 owner rows, 104 command bindings, 106 ordered event bindings,
  87 unique command types, 86 unique event types, 173 schema identities, 17 command
  root fields, 27 event root fields, 14 families, and 17 shared type rules.
- All reusable objects and family field universes remain closed; references resolve;
  correction mappings remain 15 closed non-overlapping branches with no fallback;
  recovery manifest coverage remains identity-complete and writer-lease fail-closed.
- No generic object/fallback, self-hash, owner-verdict assertion, generated schema,
  registration, dispatch, reducer, projection, migration, hook, or runtime authority
  was added.

All 14 conservative family decisions were re-audited:

| Family | R6 disposition |
|---|---|
| Scope | Pass — typed sourced prefixes and bounded `any_id` use unchanged |
| Task | Pass — closed definition and explicit partial/reopen variants unchanged |
| Dispatch | Pass — role/profile/actor and root binding remain distinct |
| Lease | Pass — normalized lifecycle facts remain explicit |
| Attempt/checkpoint | Pass — checkpoint and creation/subject variants remain closed |
| Message | Pass — closed message variants and evidence fields unchanged |
| Blocker | Pass — stop/resume authority facts remain explicit |
| Artefact | Pass — six dimensions and policy inputs remain non-compensating |
| Review | Pass after R5 remediation — conservative disposition enum and total gate map are explicit |
| Decision | Pass — closed kinds, lineage, evidence, and boundary fields unchanged |
| Rule evaluation | Pass — `val_` cross-use remains explicitly conservative |
| Correction | Pass — 15 literal branches, one owner projection, no fallback |
| Resource/operation | **Fail — R6-M1 cross-rule ResourceRequest contradiction** |
| Backup/recovery | Pass — unique complete manifest and no-writer-lease conditions unchanged |

## 7. Mechanical and external evidence

| Check | Exact-head result |
|---|---|
| Independent source-fact oracle | `213 passed in 1.56s` |
| Companion Draft 2020-12 schema validation | Pass |
| Independent exact-byte identities / UTF-8-LF checks | Pass |
| Independent six-verdict and cross-rule attacks | Gate attacks pass; R6-M1 reproduced for all three profiles |
| Exact cardinality reconstruction | `104 / 104 / 106 / 87 / 86 / 173 / 17 / 27 / 14` |
| `git diff --check f0e9ebd...5f795e1` | Pass |
| Codacy exact-head check | Success, zero annotations |

The controller also supplied exact-head evidence for the 55-test
foundation/materialization set, 175 mutation cases, Ruff, and diff checks. This review
credits those as corroboration, not as a substitute for the independent cross-rule
attack.

## 8. Authority boundary and next review

The exact candidate remains `stage_1_ready: false`. Because R6-M1 is Major, this review
issues no Stage-1 owner-approval tuple and authorizes neither deterministic generation
of the 173 schemas nor any runtime surface.

A successor exact-byte review should be delta-bounded to the requiredness
exception/precedence remediation and its independent oracle tests, then reverify all
three object identities, the exact ordered binding ledger, counts, companion schema,
Codacy, and the unchanged authority boundary. Only a clean successor review may
present an exact Stage-1 tuple for Stephen's explicit acceptance.
