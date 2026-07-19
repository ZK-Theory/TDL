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

The current reusable objects are closed rather than loose string maps, but the R3 M-2 finding remains open: this packet does not yet prove one-to-one coverage of every atomic W2/W8 source fact for the four objects below.

- `object/task_definition` must be expanded and source-fact-bound against W2 §10.1.
- `object/dispatch_definition` and `object/root_binding` must be expanded and source-fact-bound against W2 §12.1.
- `object/artefact_manifest` must be expanded and source-fact-bound against W2 §§16.1–16.2.
- `object/resource_request` must be expanded and source-fact-bound against W8 §§7 and 11.1.

The machine contract asserts these cardinalities as constants: 104 rows, 104 command bindings, 106 event bindings, 87 unique command types, 86 unique event types, 173 generated schema identities, 17 command-root fields, 27 event-root fields, and 14 families.

## 4. Conservative proposal decisions by family

The following choices are not silently attributed to W2, W8, or 06d. Each appears as a frozen `conservative_proposal` in the YAML decision register. The generation contract is a deterministic total function with zero byte-changing choices: a generator may not rename, select, infer, or widen these rules.

| Family | Non-source-literal decision selected for review |
|---|---|
| Scope | Source-literal W2/W8 ID prefixes are typed; `type/any_id` remains only for genuinely open identifier families. |
| Task | Current closed definition object and typed lifecycle evidence sets; M-2 expansion/source-fact binding remains pending; shared partial and reopen discriminators are frozen. |
| Dispatch | `access_mode` is frozen to `read_only`, `create_only`, `append_only`, or `read_write`; Git identities use the exact algorithm-tagged pattern `^git:(sha1:[0-9a-f]{40}|sha256:[0-9a-f]{64})$`. |
| Lease | One normalized claim/grant shape across lifecycle and operator rows; holder/session/capability/renewal fields; scheduler authority on expiry. |
| Attempt/checkpoint | One family with explicit checkpoint disposition, compatibility, invariants, progress, confidentiality, and `creation_kind`/`subject_kind` discriminators. |
| Message | Source-closed message types select row variants; delivery, acknowledgement, action, correlation, and evidence fields remain explicit. |
| Blocker | Stop semantics, responsible authority, resume condition, and evidence lists are normalized as a closed fact. |
| Artefact | Retention, sensitivity, provenance-class, and destination-class strings are explicit separately versioned runtime-policy inputs; generation cannot invent institutional classifications. |
| Review | Source-closed review types and verdicts; request, independence, assignment, findings, subject hashes, satisfaction gates, and amendment/supersession facts remain separate. |
| Decision | Source-closed decision kinds; authority, subject, consequences, conditions, evidence, lifecycle, lineage, and effective-boundary fields are non-compensating. |
| Rule evaluation | Estimand/object, compared subjects, metric, denominator, input IDs/hashes, validator, output, and evidence hash are explicit. |
| Correction | The corrected-record-kind vocabulary is source-closed; M-5 must still supply the exact 15-kind union, and a generic fallback remains prohibited. |
| Resource/operation | Integer primitives are capped at the interoperable maximum `9007199254740991`; checkpoint compatibility is exactly `compatible`, `incompatible`, or `unable_to_determine`, while `not_applicable` belongs only to profile applicability. |
| Backup/recovery | M-5 remains pending: generation is prohibited until the reviewed per-external-artefact availability relation and correction union are represented. |

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
| Backup/recovery | 22 | 12 | 17 | 7 |

Representative resolver-only names include `completion_rule`, `acceptance_evidence_ref`, `claimed_at`, `compatibility_verdict`, `availability_evidence_ref`, `finding_ids`, `calculation_ref`, and `canonical_tail_hash`. Representative annex-only choices include the complete Task/Dispatch/Artefact/ResourceRequest objects, plural evidence sets, explicit dispositions, the six artefact dimensions, resource ceilings/distribution, and shared discriminators. This delta is a required review surface, not a claim that one vocabulary is implicitly equivalent to the other.

## 6. Two-stage authority gate

1. **Fact-annex acceptance.** M-2 complete source-fact objects/bindings and M-5 correction/recovery shapes must first be remediated. An independent reviewer then validates the exact committed Markdown, YAML, and JSON Schema bytes; recomputes their Git blobs and SHA-256 values; reviews every conservative proposal and resolver delta; and returns a verdict. Stephen may then explicitly accept the exact annex path, schema ID/version, Git blob, and SHA-256. Candidate status cannot assert or infer this acceptance.
2. **Generated-schema acceptance.** Only after stage 1 may a generator consume the accepted annex to materialize the 173 unique command/event schema files and populate all 210 row/event content observations. Those exact generated paths, schema IDs/versions, Git blobs, SHA-256 values, row/multiset identities, and independent review form a separate D-G6-3 owner decision.

This D1C-1 packet is not Stage-1 ready and does not authorize schema generation. Stage 1 does not authorize generation as runtime implementation. Stage 2 does not authorize registration, dispatch, reduction, projection, migration, hooks, or Gate 6 transition work. Those remain later gates.

## 7. Validation commands

The following script validates the public JSON Schema, exact counts, references, source-row ordering, and ordered event bindings. It intentionally reads 06d through the immutable-source helper and never treats the current resolver's payload shapes as authority.

```powershell
@'
from pathlib import Path
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
assert contract['cardinalities']['generated_schema_identities'] == 173
assert contract['generation_contract']['byte_changing_choices_remaining'] == 0
assert contract['generation_contract']['stage_1_ready'] is False

type_ids = {x['type_id'] for x in contract['primitive_types']}
enum_ids = {x['enum_id'] for x in contract['source_closed_enums']}
object_ids = {x['object_id'] for x in contract['reusable_objects']}
valid_refs = type_ids | enum_ids | object_ids
for section in ('reusable_objects', 'family_specs'):
    for owner in contract[section]:
        assert len({f['field_name'] for f in owner['fields']}) == len(owner['fields'])
        assert all(f['type_ref'] in valid_refs for f in owner['fields'])

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
- Verify source-closed enums, especially review verdict, artefact availability/dimensions, operational profile, checkpoint compatibility, and corrected-record kind.
- Confirm shared types are either one normalized fact or have an explicit discriminator/variant rule.
- Confirm M-2 and M-5 remain explicit blockers; this packet must not be treated as Stage-1 readiness or generation authority.
- Confirm the proposal contains no self-hash, acceptance actor, inferred owner verdict, runtime registration, dispatch, reducer, projection, migration, or Gate 6 transition authorization.
- Record findings against exact committed bytes. A candidate-authored checklist result is not independent acceptance.
