# WP6.1 schema-fact authority annex proposal

**Status:** `proposed_pending_explicit_owner_approval`

**Decision boundary:** this document and its machine-readable companion are review subjects, not accepted authority.

**Runtime authority:** none.

## 1. Why this annex is required

The approved W2/W8 prose and the immutable 06d owner catalogue close the lifecycle rows, command/event names, authority subjects, reducers, projections, receipts, and tests. They do not, by themselves, select one exact JSON representation for every primitive, nullable field, nested object, shared semantic type, or row-specific command/fact payload. The current WP6.1 implementation candidate therefore cannot be promoted into the 173 content-addressed schemas merely because its Python resolver is executable.

This annex supplies the missing proposed fact model in a strictly schematized, hash-bindable form:

- `.research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml`
- `.research-system/schemas/contracts/wp6-1-schema-fact-annex-proposal.schema.json`

The YAML binds 104 owner rows to 104 exact command-payload selections and 106 ordered immutable event-fact selections, covering 87 command types and 86 event types. It fixes the 17-field command envelope (including `project_id`), the 27-field event envelope, 14 family field universes, closed reusable objects, source-closed enums, and 17 shared-type rules. The schema-identity proposal is one identity per semantic type: 87 command identities plus 86 event identities, with repeated owner rows sharing that identity and closed variants remaining inside it.

The proposal deliberately has no self-content hash, acceptance actor, owner-verdict field, runtime observation, generated schema files, or generated content-identity observations. Its exact Git blob and SHA-256 can only be observed after commit by an independent reviewer.

## 2. Immutable sources

All three sources are read as canonical UTF-8/LF bytes from revision `fe5f1d40bc8f05f061317c677b5891cea0711249`, not reopened from a mutable checkout during acceptance review.

| Source | Git blob | Canonical SHA-256 |
|---|---|---|
| W2 `design/02-task-event-and-artifact-schema.md` | `7e09a9c49605663bb50163840fff3ae4c8212748` | `dd5f45ec91cb4c10f0e8d1d99341ad16745bec21f58400b6643285224870f9c6` |
| W8 `design/08-resource-checkpoint-and-operations.md` | `d26f24b9a6670b095d307fe531a7bb9b31c55311` | `84c80a8b499394fed65ed0d4e7fe1f4f9a85a8ccc23b299c85198e5d60e79a58` |
| 06d `implementation/06d-wp6-1-owner-source-catalogue.md` | `5e2eb60ca4419d1529506de6859fb027cff518af` | `96932fd752362eddb6da2da77bc0b56ccb8e83ced58e93c3b139e3248acb08f7` |

## 3. Model and exact closure

The family model is a closed field universe plus a row-specific required-field selection. A generator must take the cited type of each selected field from the row's `family_ref`, close the resulting payload with `additionalProperties: false`, and reject an absent or unknown row. There is no generic object, catch-all branch, fallback payload, or registry widening.

The current reusable objects are closed rather than loose string maps. D1C-2a supplies the closed Task, Dispatch/root-binding, and review-verdict facts with machine-readable one-to-one source-fact bindings. This D1C-2b/D1C-3 packet completes the Artefact and ResourceRequest source-fact objects and the correction/recovery relations. The R5 semantic remediation freezes the total six-verdict gate relation plus non-null, complete profile evidence; completion remains a candidate claim pending a strengthened independent source-fact oracle and fresh exact-byte review. Candidate R3 M-5 remediation is complete, but this proposal remains pending an independent source-fact oracle, fresh exact-byte review, and explicit owner approval.

The global reusable_object_field_rule makes every field listed by every reusable object required. A field marked nullable true is still a required key whose value alone may be null; it does not become optional. Evidence that this proposal claims is present uses type/nonempty_evidence_ref_list.

- `object/task_definition`, `object/dispatch_definition`, and `object/root_binding` are complete for the cited W2 §10.1/§12.1 facts in D1C-2a; `source_fact_bindings` records each target field or explicit non-lossy subfield mapping.
- `family/review` and the `review.record_verdict` command/event selections represent every W2 §§17.3–17.4 verdict condition as a closed per-condition record. The frozen total gate map makes `approve` satisfied, makes `approve_with_conditions` satisfied only for a non-empty all-non-blocking, owned, policy-bound, non-empty-evidence condition list, and makes the four negative verdicts unsatisfied; verdict recording remains separate from the Task transition.
- `object/artefact_manifest` now represents every independently stateful W2 §§16.1–16.2 identity, production, code/environment, location, integrity, input, research-provenance, validation, authority, and operations fact through closed objects where a relation must remain paired.
- `object/resource_request` remains one unified W8 §7/§§11.1–12 request object. Its closed `operational_profile` discriminator has exactly `trivial`, `bounded`, and `long_running` branches, with a required non-null matching evidence object, both foreign evidence objects forbidden, no fallback, globally required nested fields, and trivial-only explicit `not_applicable` dispositions. Checkpoint compatibility remains the separate three-value W8 §16 relation and never uses `not_applicable`.
- `correction_variant_mappings` is the literal 06d §1.4 authority table: exactly 15 kind-specific branches fix the subject-ID grammar, exactly one owner projection, and the governance correction index; no generic correction branch is permitted.
- `object/external_artefact_availability` carries one immutable artefact ID/content-SHA-256 reference, availability, and non-empty evidence. `external_artefacts` replaces the lossy parallel recovery fields; its deterministic rules require unique complete manifest coverage and diagnostic-only/no-writer-lease treatment unless every entry is available with evidence.

The machine contract asserts these cardinalities as constants: 104 rows, 104 command bindings, 106 event bindings, 87 unique command types, 86 unique event types, 173 generated schema identities, 17 command-root fields, 27 event-root fields, and 14 families.

## 4. Conservative proposal decisions by family

The following choices are not silently attributed to W2, W8, or 06d. Each appears as a frozen `conservative_proposal` in the YAML decision register. The generation contract is a deterministic total function with zero byte-changing choices: a generator may not rename, select, infer, or widen these rules.

| Family | Non-source-literal decision selected for review |
|---|---|
| Scope | Source-literal W2/W8 ID prefixes are typed; `type/any_id` remains only for genuinely open identifier families. |
| Task | D1C-2a completes the closed definition object and source-fact bindings; shared partial and reopen discriminators are frozen. |
| Dispatch | D1C-2a completes distinct target role/profile/optional actor, root binding, and dispatch source facts; `access_mode` is frozen to `read_only`, `create_only`, `append_only`, or `read_write`. |
| Lease | One normalized claim/grant shape across lifecycle and operator rows; holder/session/capability/renewal fields; scheduler authority on expiry. |
| Attempt/checkpoint | One family with explicit checkpoint disposition, compatibility, invariants, progress, confidentiality, and `creation_kind`/`subject_kind` discriminators. |
| Message | Source-closed message types select row variants; delivery, acknowledgement, action, correlation, and evidence fields remain explicit. |
| Blocker | Stop semantics, responsible authority, resume condition, and evidence lists are normalized as a closed fact. |
| Artefact | Retention, sensitivity, provenance-class, and destination-class strings are explicit separately versioned runtime-policy inputs; generation cannot invent institutional classifications. |
| Review | The owner-visible conservative JSON representation uses closed per-condition records (text, proposed two-value policy disposition, typed owner, policy ID, non-empty evidence) and a closed six-verdict map. The W2 all-non-blocking/non-null-owner gate predicate remains source semantics; Task acceptance remains a distinct transition. |
| Decision | Source-closed decision kinds; authority, subject, consequences, conditions, evidence, lifecycle, lineage, and effective-boundary fields are non-compensating. |
| Rule evaluation | Estimand/object, compared subjects, metric, denominator, input IDs/hashes, validator, output, and evidence hash are explicit. The `rule_evaluation -> type/validation_id (val_)` correction mapping is an owner-visible conservative cross-use: W2 assigns `val_` to ValidationRecord, not source-literally to RuleEvaluation. |
| Correction | The literal 15-kind mapping freezes each corrected-record ID type, owner projection, governance correction index, subject field, and selector rule. Generation emits exactly 15 non-overlapping `oneOf` branches; a generic fallback is prohibited. |
| Resource/operation | Integer primitives are capped at the interoperable maximum `9007199254740991`; `minimum <= expected <= maximum` runtime and `ram_working <= ram_peak` are generation rules. No universal maximum beyond P0 is invented. `type/resource_id` unions sourced `rsq`/`rgr`/`rcf` components and `type/operation_id` unions sourced `hbt`/`pid`/`stp`/`rsd`/`rcv`/`opc`/`opr` components; both unions are owner-visible conservative selections, not source-literal families. A second owner-visible conservative JSON choice freezes the unified ResourceRequest discriminator shape: exactly three non-overlapping branches, matching evidence required, other evidence forbidden, no fallback. Checkpoint compatibility is exactly `compatible`, `incompatible`, or `unable_to_determine`, while `not_applicable` belongs only to profile applicability. |
| Backup/recovery | Closed `external_artefacts` entries replace aggregate availability. A writer lease requires complete unique manifest coverage and every entry `available` with non-empty evidence; missing, inaccessible, quarantined, incomplete, or partial restore is diagnostic-only/no writer lease. |

## 5. Candidate resolver comparison — evidence, not authority

The current `tests/research_system/contracts/wp6_1_schema_source.py` resolver was used only as a comparison candidate. It is not a source document and does not acquire authority through this annex. Its command required-field list differs from the direct-source proposal on 104 of 104 rows. Its root helper contains 15 command and 26 event fields because it adds `payload` elsewhere and omits the source-required command `project_id`; the annex records the final flat 17/27 roots explicitly.

The table below records union-level differences. `Annex-only` includes complete direct-source groups and normalized names missing from the resolver. `Resolver-only` is candidate vocabulary that is not silently imported; each such name must either be mapped to an annex field or raised as an explicit amendment during review.

| Family | Annex fields | Resolver candidate fields | Annex-only | Resolver-only |
|---|---:|---:|---:|---:|
| Scope | 20 | 24 | 12 | 16 |
| Task | 54 | 67 | 35 | 48 |
| Dispatch | 24 | 31 | 13 | 20 |
| Lease | 22 | 23 | 9 | 10 |
| Attempt/checkpoint | 45 | 53 | 24 | 32 |
| Message | 39 | 42 | 18 | 21 |
| Blocker | 9 | 12 | 6 | 9 |
| Artefact | 20 | 39 | 9 | 28 |
| Review | 33 | 36 | 22 | 25 |
| Decision | 35 | 31 | 24 | 20 |
| Rule evaluation | 15 | 9 | 8 | 2 |
| Correction | 9 | 8 | 5 | 4 |
| Resource/operation | 47 | 45 | 28 | 26 |
| Backup/recovery | 21 | 12 | 16 | 7 |

Representative resolver-only names include `completion_rule`, `acceptance_evidence_ref`, `claimed_at`, `compatibility_verdict`, `availability_evidence_ref`, `finding_ids`, `calculation_ref`, and `canonical_tail_hash`. Representative annex-only choices include the complete Task/Dispatch/Artefact/ResourceRequest objects, plural evidence sets, explicit dispositions, the six artefact dimensions, resource ceilings/distribution, and shared discriminators. This delta is a required review surface, not a claim that one vocabulary is implicitly equivalent to the other.

## 6. Two-stage authority gate

1. **Fact-annex acceptance.** D1C-2a/D1C-2b/D1C-3 plus the R5 semantic remediation supply the candidate source groups and R3 M-5 correction/recovery shapes. `stage_1_ready` remains `false`: a strengthened independently authored source-fact oracle, fresh exact-byte review, and Stephen's explicit owner approval are still required, and no generation is authorized. An independent reviewer then validates the exact committed Markdown, YAML, and JSON Schema bytes; recomputes their Git blobs and SHA-256 values; reviews every conservative proposal and resolver delta; and returns a verdict. Stephen may then explicitly accept the exact annex path, schema ID/version, Git blob, and SHA-256. Candidate status cannot assert or infer this acceptance.
2. **Generated-schema acceptance.** Only after stage 1 may a generator consume the accepted annex to materialize the 173 unique command/event schema files and populate all 210 row/event content observations. Those exact generated paths, schema IDs/versions, Git blobs, SHA-256 values, row/multiset identities, and independent review form a separate D-G6-3 owner decision.

This D1C-2a/D1C-2b/D1C-3 candidate is not Stage-1 ready and does not authorize schema generation. The R5 semantic-gap remediation is complete pending strengthened oracle evidence, fresh exact-byte review, and explicit owner approval; those independent readiness blockers remain closed. Stage 1 does not authorize generation as runtime implementation. Stage 2 does not authorize registration, dispatch, reduction, projection, migration, hooks, or Gate 6 transition work. Those remain later gates.

## 7. Validation commands

The following script validates the public JSON Schema, exact counts, references, source-row ordering, and ordered event bindings. It intentionally reads 06d through the immutable-source helper and never treats the current resolver's payload shapes as authority.

```powershell
@'
from pathlib import Path
from copy import deepcopy
import json
import yaml
from jsonschema import Draft202012Validator
from tests.research_system.contracts.wp6_1_schema_source import source_rows

root = Path('.')
contract_path = root / '.research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml'
schema_path = root / '.research-system/schemas/contracts/wp6-1-schema-fact-annex-proposal.schema.json'
contract = yaml.safe_load(contract_path.read_text(encoding='utf-8'))
schema = json.loads(schema_path.read_text(encoding='utf-8'))
Draft202012Validator.check_schema(schema)
Draft202012Validator(schema).validate(contract)

rows = source_rows(root)
assert len(rows) == 104
assert len(contract['command_payload_specs']) == 104
assert len(contract['event_fact_specs']) == 106
assert len(contract['row_bindings']) == 104
assert len({x['command_type'] for x in contract['command_payload_specs']}) == 87
assert len({x['event_type'] for x in contract['event_fact_specs']}) == 86
assert len(contract['command_root']['fields']) == 17
assert len(contract['event_root']['fields']) == 27
assert len(contract['family_specs']) == 14
assert len(contract['shared_schema_rules']) == 17
assert len(contract['decision_register']) == 14
assert len({x['decision_id'] for x in contract['decision_register']}) == 14
assert contract['cardinalities']['generated_schema_identities'] == 173
assert contract['generation_contract']['byte_changing_choices_remaining'] == 0
assert contract['generation_contract']['stage_1_ready'] is False
assert contract['generation_contract']['pending_r3_remediation'] == []
assert contract['generation_contract']['readiness_blockers'] == ['independent_source_fact_oracle', 'fresh_exact_byte_review', 'explicit_owner_approval']
assert len(contract['correction_variant_mappings']) == 15
assert {x['corrected_record_kind'] for x in contract['correction_variant_mappings']} == set(next(x for x in contract['source_closed_enums'] if x['enum_id'] == 'enum/corrected_record_kind')['values'])
assert all(x['subject_field'] == 'erroneous_record_id' and x['governance_correction_index'] == 'governance_correction_index' and x['projection_selector_rule'] == 'exactly_one_owner_projection_plus_governance_correction_index' for x in contract['correction_variant_mappings'])
assert contract['recovery_external_artefact_rules']['writer_lease_rule'] == 'every_entry_available_with_nonempty_evidence_before_writer_lease'
assert contract['recovery_external_artefact_rules']['diagnostic_only_conditions'] == ['missing', 'inaccessible', 'quarantined', 'missing_availability_evidence', 'incomplete_manifest_coverage', 'partial_restore']

type_ids = {x['type_id'] for x in contract['primitive_types']}
enum_ids = {x['enum_id'] for x in contract['source_closed_enums']}
object_ids = {x['object_id'] for x in contract['reusable_objects']}
valid_refs = type_ids | enum_ids | object_ids
for section in ('reusable_objects', 'family_specs'):
    for owner in contract[section]:
        assert len({f['field_name'] for f in owner['fields']}) == len(owner['fields'])
        assert all(f['type_ref'] in valid_refs for f in owner['fields'])

object_specs = {x['object_id']: x for x in contract['reusable_objects']}
type_specs = {x['type_id']: x for x in contract['primitive_types']}
correction_mappings = {x['corrected_record_kind']: x for x in contract['correction_variant_mappings']}
profile_rules = contract['object_variant_rules']
assert len(profile_rules) == 1
profile_rule = profile_rules[0]
assert profile_rule['object_id'] == 'object/resource_request'
assert profile_rule['discriminator_field'] == 'operational_profile'
assert profile_rule['no_fallback'] is True
assert contract['reusable_object_field_rule'] == {
    'all_listed_reusable_object_fields_required': True,
    'nullable_field_semantics': 'required_key_value_may_be_null_only_when_nullable_true',
    'nonempty_evidence_type_ref': 'type/nonempty_evidence_ref_list',
    'decision_basis': 'conservative_proposal',
    'source_citation': 'W2/W8 listed typed facts and R5 requiredness closure',
}
enum_specs = {x['enum_id']: x for x in contract['source_closed_enums']}
assert enum_specs['enum/review_condition_gate_disposition']['decision_basis'] == 'conservative_proposal'
assert type_specs['type/review_gate_condition_list']['min_items'] == 1
branches = {x['discriminator_const']: x for x in profile_rule['branches']}
assert set(branches) == {'trivial', 'bounded', 'long_running'}
assert len(branches) == 3
for profile, evidence in {
    'trivial': 'trivial_profile_evidence',
    'bounded': 'bounded_profile_evidence',
    'long_running': 'long_running_profile_evidence',
}.items():
    branch = branches[profile]
    assert branch['required_fields'] == [evidence]
    assert set(branch['forbidden_fields']) == {
        'trivial_profile_evidence',
        'bounded_profile_evidence',
        'long_running_profile_evidence',
    } - {evidence}
trivial = object_specs['object/trivial_profile_evidence']
trivial_fields = {x['field_name']: x for x in trivial['fields']}
for name in ('benchmark', 'checkpoint', 'periodic_heartbeat', 'recovery'):
    assert trivial_fields[name]['type_ref'] == 'object/trivial_not_applicable_evidence'
assert 'provider_command_process' in trivial_fields
bounded = {x['field_name'] for x in object_specs['object/bounded_profile_evidence']['fields']}
assert bounded == {'heartbeat', 'output_tail', 'stop', 'checkpoint'}
long_running = {x['field_name'] for x in object_specs['object/long_running_profile_evidence']['fields']}
assert long_running == {'benchmark', 'heartbeat', 'process', 'checkpoint', 'stop_recovery', 'backup'}
resource_fields = {x['field_name']: x for x in object_specs['object/resource_request']['fields']}
assert {'trivial_profile_evidence', 'bounded_profile_evidence', 'long_running_profile_evidence'} <= set(resource_fields)
assert all(resource_fields[name]['nullable'] is False for name in (
    'trivial_profile_evidence',
    'bounded_profile_evidence',
    'long_running_profile_evidence',
))

def sample_for_ref(ref):
    if ref in object_specs:
        return {
            field['field_name']: sample_for_ref(field['type_ref'])
            for field in object_specs[ref]['fields']
        }
    if ref in enum_specs:
        return enum_specs[ref]['values'][0]
    spec = type_specs[ref]
    if spec['json_type'] == 'array':
        item = sample_for_ref(spec['item_type_ref'])
        return [item] if spec.get('min_items', 0) else []
    if spec['json_type'] == 'string':
        if ref == 'type/actor_id':
            return 'act_00000000-0000-7000-8000-000000000000'
        if ref == 'type/policy_version_id':
            return 'pol_00000000-0000-7000-8000-000000000000'
        return 'value'
    if spec['json_type'] == 'integer':
        return max(0, spec.get('minimum', 0))
    if spec['json_type'] == 'boolean':
        return True
    return {}

def ref_valid(ref, value):
    if ref in object_specs:
        return object_valid(ref, value)
    if ref in enum_specs:
        return value in enum_specs[ref]['values']
    spec = type_specs[ref]
    if spec['json_type'] == 'array':
        return (
            isinstance(value, list)
            and len(value) >= spec.get('min_items', 0)
            and all(ref_valid(spec['item_type_ref'], item) for item in value)
        )
    if spec['json_type'] == 'string':
        return isinstance(value, str) and len(value) >= spec.get('min_length', 0)
    if spec['json_type'] == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if spec['json_type'] == 'boolean':
        return isinstance(value, bool)
    return isinstance(value, dict)

def object_valid(object_id, value):
    if not isinstance(value, dict):
        return False
    fields = {x['field_name']: x for x in object_specs[object_id]['fields']}
    if set(value) != set(fields):
        return False
    for name, field in fields.items():
        if value[name] is None:
            if not field['nullable']:
                return False
        elif not ref_valid(field['type_ref'], value[name]):
            return False
    return True

assert all(not object_valid(object_id, {}) for object_id in object_specs)
condition_fields = {x['field_name']: x for x in object_specs['object/review_gate_condition']['fields']}
assert condition_fields['owner_actor_id']['type_ref'] == 'type/actor_id'
assert condition_fields['evidence_refs']['type_ref'] == 'type/nonempty_evidence_ref_list'
gate_rule = contract['review_gate_condition_rule']
assert gate_rule['verdict_gate_results'] == {
    'approve': 'satisfied',
    'approve_with_conditions': 'satisfied_if_nonempty_all_conditions_non_blocking_with_non_null_typed_actor_owner_policy_and_nonempty_evidence',
    'changes_requested': 'unsatisfied',
    'reject': 'unsatisfied',
    'unable_to_verify': 'unsatisfied',
    'withdrawn': 'unsatisfied',
}

def gate_satisfied(verdict, conditions):
    result = gate_rule['verdict_gate_results'].get(verdict)
    if result == 'satisfied':
        return True
    if result != gate_rule['verdict_gate_results']['approve_with_conditions']:
        return False
    return (
        isinstance(conditions, list)
        and len(conditions) >= gate_rule['approve_with_conditions_min_items']
        and all(
            object_valid('object/review_gate_condition', item)
            and item['gate_disposition'] == 'non_blocking'
            and item['owner_actor_id'] is not None
            and bool(item['policy_id'])
            and bool(item['evidence_refs'])
            for item in conditions
        )
    )

positive_condition = sample_for_ref('object/review_gate_condition')
assert gate_satisfied('approve', [])
assert gate_satisfied('approve_with_conditions', [positive_condition])
for verdict in ('changes_requested', 'reject', 'unable_to_verify', 'withdrawn'):
    assert not gate_satisfied(verdict, [positive_condition])
assert not gate_satisfied('approve_with_conditions', [])
assert not gate_satisfied('approve_with_conditions', [
    positive_condition,
    {**positive_condition, 'gate_disposition': 'blocking'},
])
assert not gate_satisfied('approve_with_conditions', [{**positive_condition, 'owner_actor_id': None}])
assert not gate_satisfied('approve_with_conditions', [{**positive_condition, 'policy_id': ''}])
assert not gate_satisfied('approve_with_conditions', [{**positive_condition, 'evidence_refs': []}])
missing_owner = dict(positive_condition)
del missing_owner['owner_actor_id']
assert not gate_satisfied('approve_with_conditions', [missing_owner])
assert gate_rule['task_state_effect'] == 'no_direct_task_state_change'

profile_object_refs = {
    'trivial': 'object/trivial_profile_evidence',
    'bounded': 'object/bounded_profile_evidence',
    'long_running': 'object/long_running_profile_evidence',
}
profile_fields = {
    profile: branches[profile]['required_fields'][0]
    for profile in branches
}

def profile_valid(value):
    if not isinstance(value, dict):
        return False
    profile = value.get('operational_profile')
    if profile not in branches:
        return False
    branch = branches[profile]
    if any(name not in value for name in branch['required_fields']):
        return False
    if any(name in value for name in branch['forbidden_fields']):
        return False
    selected = profile_fields[profile]
    return value[selected] is not None and object_valid(profile_object_refs[profile], value[selected])

valid_profiles = {}
for profile in ('trivial', 'bounded', 'long_running'):
    selected = profile_fields[profile]
    evidence = sample_for_ref(profile_object_refs[profile])
    fixture = {'operational_profile': profile, selected: evidence}
    valid_profiles[profile] = fixture
    assert profile_valid(fixture)
    assert not profile_valid({'operational_profile': profile, selected: None})
    assert not profile_valid({'operational_profile': profile, selected: {}})
    for group in tuple(evidence):
        incomplete = deepcopy(fixture)
        del incomplete[selected][group]
        assert not profile_valid(incomplete)
    leaked = deepcopy(fixture)
    foreign = next(name for name in branches[profile]['forbidden_fields'])
    leaked[foreign] = {}
    assert not profile_valid(leaked)
assert not profile_valid({'operational_profile': 'fallback'})

for name in ('benchmark', 'checkpoint', 'periodic_heartbeat', 'recovery'):
    empty_evidence = deepcopy(valid_profiles['trivial'])
    empty_evidence['trivial_profile_evidence'][name]['applicability_evidence_refs'] = []
    assert not profile_valid(empty_evidence)
wrong_trivial_disposition = deepcopy(valid_profiles['trivial'])
wrong_trivial_disposition['trivial_profile_evidence']['benchmark']['disposition'] = 'required'
assert not profile_valid(wrong_trivial_disposition)
empty_receipt = deepcopy(valid_profiles['trivial'])
empty_receipt['trivial_profile_evidence']['terminal_receipt_evidence_refs'] = []
assert not profile_valid(empty_receipt)
for profile in ('bounded', 'long_running'):
    selected = profile_fields[profile]
    for group in object_specs[profile_object_refs[profile]]['fields']:
        empty_evidence = deepcopy(valid_profiles[profile])
        empty_evidence[selected][group['field_name']]['applicability_evidence_refs'] = []
        assert not profile_valid(empty_evidence)
def resolves_target(path):
    if path.startswith('correction_variant_mappings{'):
        kind = path.split('corrected_record_kind=', 1)[1].split('}', 1)[0]
        return kind in correction_mappings and path.split('}.', 1)[1] in correction_mappings[kind]
    if path.startswith('recovery_external_artefact_rules.'):
        return path.split('.', 1)[1] in contract['recovery_external_artefact_rules']
    owner_id, tail = path.split('.', 1)
    owner = object_specs.get(owner_id)
    if owner is None:  # a family target is flat
        owner = next(x for x in contract['family_specs'] if x['family_id'] == owner_id)
    fields = {x['field_name']: x for x in owner['fields']}
    for index, name in enumerate(tail.split('.')):
        if name not in fields:
            return False
        if index == len(tail.split('.')) - 1:
            return True
        ref = fields[name]['type_ref']
        if ref in object_specs:
            fields = {x['field_name']: x for x in object_specs[ref]['fields']}
        elif ref in type_specs and type_specs[ref].get('item_type_ref') in object_specs:
            item = type_specs[ref]['item_type_ref']
            fields = {x['field_name']: x for x in object_specs[item]['fields']}
        else:
            return False
    return False
assert len(contract['source_fact_bindings']) == 229
assert len({x['binding_id'] for x in contract['source_fact_bindings']}) == len(contract['source_fact_bindings'])
assert all(resolves_target(x['target_path']) for x in contract['source_fact_bindings'] if '{' not in x['target_path'] or x['target_path'].startswith('correction_variant_mappings{'))

families = {x['family_id']: {f['field_name'] for f in x['fields']} for x in contract['family_specs']}
for section in ('command_payload_specs', 'event_fact_specs'):
    for spec in contract[section]:
        assert spec['family_ref'] in families
        assert set(spec['required_field_names']) <= families[spec['family_ref']]

facts = {x['spec_id']: x for x in contract['event_fact_specs']}
bindings = {x['row_key']: x for x in contract['row_bindings']}
assert [x['row_key'] for x in contract['command_payload_specs']] == [r.key for r in rows]
assert [x['row_key'] for x in contract['row_bindings']] == [r.key for r in rows]
for row in rows:
    binding = bindings[row.key]
    assert binding['command_payload_spec_ref'] == 'command_payload/' + row.key.replace('.', '_')
    observed = [facts[ref]['event_type'] for ref in binding['ordered_event_fact_spec_refs']]
    assert observed == [event_type for event_type, _ in row.events]

for path in (contract_path, schema_path):
    raw = path.read_bytes()
    assert not raw.startswith(b'\xef\xbb\xbf')
    assert b'\r' not in raw
print('WP6.1 proposed fact annex: structural and semantic validation passed')
'@ | python -

git diff --check
```

## 8. Independent review checklist

- Recompute all three immutable source identities before interpreting citations.
- Validate the YAML against the exact companion JSON Schema and confirm every object schema is closed.
- Reconstruct the 104 rows and 106 ordered events independently from 06d; compare order and type, not only set membership.
- Confirm 104/106/87/86, 173 identities, 17/27 roots, 14 families, and 17 shared rules exactly; reject duplicates, omissions, aliases, dangling refs, or a zero/fallback branch.
- Review all 104 command required-field selections and all 106 immutable fact selections against the complete family fields.
- Review every `conservative_proposal`, every frozen decision-register selection, and the resolver delta; do not infer equivalence from similar names.
- Confirm the two additional owner-visible identity selections: `rule_evaluation -> type/validation_id (val_)` is a conservative cross-use of W2's ValidationRecord grammar, and the resource/operation ID unions are conservative groupings of W8's separately sourced component prefixes.
- Verify source-closed enums, especially review verdict, artefact availability/dimensions, operational profile, checkpoint compatibility, and corrected-record kind.
- Confirm shared types are either one normalized fact or have an explicit discriminator/variant rule.
- Confirm the closed six-verdict gate map, non-empty conditional list/evidence, all-non-blocking typed-owner policy predicate, four unsatisfied negative verdicts, and no direct Task-state change.
- Confirm all listed reusable-object fields are required, nullable metadata never makes a key optional, each ResourceRequest branch selects non-null complete evidence, and claimed applicability/receipt evidence is non-empty.
- Confirm all five M-2 source groups and every 06d §1.4/W8 §§19–21 correction/recovery binding; prove all 15 correction branches are non-overlapping and cover their source-literal kinds, with no fallback. Confirm the external manifest is unique and complete and that any unavailable/evidence-less/partial restore is diagnostic-only with no writer lease.
- Confirm independent source-fact oracle evidence, fresh exact-byte review, and explicit owner approval remain required; this packet must not be treated as Stage-1 readiness or generation authority.
- Confirm the proposal contains no self-hash, acceptance actor, inferred owner verdict, runtime registration, dispatch, reducer, projection, migration, or Gate 6 transition authorization.
- Record findings against exact committed bytes. A candidate-authored checklist result is not independent acceptance.
