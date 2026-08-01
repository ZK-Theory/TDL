"""Bind the loader's record envelope and the control-store resolver to the accepted artifacts.

The pack loader consumes external lifecycle records through a resolver protocol that, until now, had no
implementation outside test doubles. A double supplies whatever the loader asks for, so the loader's
assumptions about the record envelope were never tested against the accepted record schemas. They did not
match: the loader required ``record_id``, ``authority_root``, and ``lifecycle_state``, none of which any
record schema defines, and every record schema sets ``additionalProperties: false``.

These controls keep the reconciliation honest in both directions — the envelope map must stay equal to the
schemas, and the resolver must actually deliver the properties the loader relies on.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from research_system.assurance.pack_loader import _RECORD_ENVELOPE
from research_system.assurance.external_records import ExternalAssuranceRecordStore
from research_system.assurance.resolver import EXTERNAL_RECORD_KIND, ControlStoreAuthorityResolver
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConflictError, IntegrityError, SchemaError
from research_system.store.identity import _manifest_hash, initialize_control_store
from research_system.store.objects import ObjectStore


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / ".research-system" / "schemas" / "contracts" / "wp6-3-tdl-private-assurance-pack.schema.json"
PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
RECORD_ID = "act_01978abc-2000-7000-8000-000000002000"
STORE_RECORD_ID = "arec_01978abc-2000-7000-8000-000000002000"


def _valid_actor_body(*, name: str = "Ada") -> dict[str, str]:
    return {
        "record_type": "canonical_actor",
        "actor_id": RECORD_ID,
        "actor_kind": "agent",
        "canonical_name": name,
        "status": "active",
    }


def _record_schemas() -> dict[str, dict[str, Any]]:
    """Return every external record schema keyed by its ``record_type`` constant."""
    defs = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["$defs"]
    schemas = {}
    for schema in defs.values():
        record_type = schema.get("properties", {}).get("record_type", {}).get("const")
        if record_type is not None:
            schemas[record_type] = schema
    return schemas


def test_record_envelope_covers_exactly_the_accepted_record_schemas() -> None:
    """The loader must know an envelope for every record class the schemas define, and no others."""
    assert set(_RECORD_ENVELOPE) == set(_record_schemas())


@pytest.mark.parametrize("record_class", sorted(_RECORD_ENVELOPE))
def test_record_envelope_fields_are_the_ones_each_schema_actually_requires(record_class: str) -> None:
    """Identity field, lifecycle field, and active value must be readable off the record's own schema."""
    schema = _record_schemas()[record_class]
    id_field, state_field, active_state = _RECORD_ENVELOPE[record_class]
    required = set(schema["required"])
    assert id_field in required, f"{record_class}: {id_field} is not a required property"
    assert state_field in required, f"{record_class}: {state_field} is not a required property"
    assert schema["properties"][state_field]["const"] == active_state


def test_no_record_schema_admits_the_generic_envelope_the_loader_previously_required() -> None:
    """Guard the regression: a generic envelope check is unsatisfiable, not merely lax.

    Every record schema forbids additional properties, so a record carrying ``record_id``,
    ``authority_root``, or ``lifecycle_state`` would fail schema validation. Reintroducing a generic check
    would make the loader reject every valid record, and no test double would reveal it.
    """
    for record_class, schema in _record_schemas().items():
        assert schema["additionalProperties"] is False, record_class
        for forbidden in ("record_id", "authority_root", "lifecycle_state"):
            assert forbidden not in schema["properties"], f"{record_class} unexpectedly defines {forbidden}"


def _resolver(tmp_path: Path) -> tuple[ControlStoreAuthorityResolver, ObjectStore, str]:
    code_root = tmp_path / "code"
    code_root.mkdir()
    control_root = tmp_path / "control"
    identity = initialize_control_store([code_root], control_root, PROJECT_ID)
    binding = ControlBinding(
        code_roots=(code_root.resolve(),),
        control_root=control_root.resolve(),
        project_id=PROJECT_ID,
        schema_root=SCHEMA_PATH.parents[1],
        store_identity=identity,
    )
    resolver = ControlStoreAuthorityResolver(binding)
    return resolver, ObjectStore(control_root), resolver.authority_root


def _binding(tmp_path: Path) -> ControlBinding:
    code_root = tmp_path / "code"
    code_root.mkdir()
    control_root = tmp_path / "control"
    identity = initialize_control_store([code_root], control_root, PROJECT_ID)
    return ControlBinding(
        code_roots=(code_root.resolve(),),
        control_root=control_root.resolve(),
        project_id=PROJECT_ID,
        schema_root=SCHEMA_PATH.parents[1],
        store_identity=identity,
    )


def test_resolver_returns_the_persisted_record_body(tmp_path: Path) -> None:
    resolver, objects, root = _resolver(tmp_path)
    body = _valid_actor_body()
    objects.write(EXTERNAL_RECORD_KIND, STORE_RECORD_ID, 1, body)
    resolved = resolver.resolve(record_id=RECORD_ID, record_class="canonical_actor", authority_root=root, phase="load")
    assert resolved == body


def test_resolver_rejects_a_foreign_authority_root(tmp_path: Path) -> None:
    """The supplied root and the store's own verified identity are two values that must agree."""
    resolver, objects, _ = _resolver(tmp_path)
    objects.write(EXTERNAL_RECORD_KIND, STORE_RECORD_ID, 1, _valid_actor_body())
    with pytest.raises(ArsError, match="authority root"):
        resolver.resolve(record_id=RECORD_ID, record_class="canonical_actor", authority_root="0" * 64, phase="load")


def test_resolver_rejects_an_unknown_phase(tmp_path: Path) -> None:
    resolver, objects, root = _resolver(tmp_path)
    objects.write(EXTERNAL_RECORD_KIND, STORE_RECORD_ID, 1, _valid_actor_body())
    with pytest.raises(ArsError, match="phase"):
        resolver.resolve(record_id=RECORD_ID, record_class="canonical_actor", authority_root=root, phase="whenever")


def test_resolver_fails_closed_on_an_unpersisted_record(tmp_path: Path) -> None:
    resolver, _, root = _resolver(tmp_path)
    with pytest.raises(ArsError, match="no persisted revision"):
        resolver.resolve(record_id=RECORD_ID, record_class="canonical_actor", authority_root=root, phase="load")


def test_resolution_is_stable_across_phases_until_a_revision_supersedes(tmp_path: Path) -> None:
    """Phase stability is a property of the store, not of resolver bookkeeping.

    The loader treats a body that changes between phases as stale. That detection only works if resolution
    tracks supersession, so this asserts both halves: stable while nothing is published, changed once a
    superseding revision lands.
    """
    resolver, objects, root = _resolver(tmp_path)
    first = _valid_actor_body(name="first")
    objects.write(EXTERNAL_RECORD_KIND, STORE_RECORD_ID, 1, first)
    kwargs = {"record_id": RECORD_ID, "record_class": "canonical_actor", "authority_root": root}
    assert [resolver.resolve(phase=phase, **kwargs) for phase in ("load", "acceptance", "consumption")] == [first] * 3

    superseding = _valid_actor_body(name="second")
    objects.write(EXTERNAL_RECORD_KIND, STORE_RECORD_ID, 2, superseding)
    assert resolver.resolve(phase="consumption", **kwargs) == superseding


def test_resolver_detects_a_tampered_record_body(tmp_path: Path) -> None:
    """Content addressing is the point: an edited body no longer matches its filename digest."""
    resolver, objects, root = _resolver(tmp_path)
    objects.write(EXTERNAL_RECORD_KIND, STORE_RECORD_ID, 1, _valid_actor_body())
    persisted = next((tmp_path / "control" / "objects" / EXTERNAL_RECORD_KIND / STORE_RECORD_ID).glob("*.json"))
    persisted.write_bytes(json.dumps({"record_type": "canonical_actor", "status": "revoked"}).encode("utf-8"))
    with pytest.raises(IntegrityError):
        resolver.resolve(record_id=RECORD_ID, record_class="canonical_actor", authority_root=root, phase="load")


def test_initializing_a_control_root_inside_a_code_root_is_refused(tmp_path: Path) -> None:
    """The externality guarantee is what makes these records not producer-authored."""
    code_root = tmp_path / "code"
    code_root.mkdir()
    with pytest.raises(ArsError, match="disjoint"):
        initialize_control_store([code_root], code_root / "control", PROJECT_ID)


def test_binding_a_resolver_to_a_control_root_inside_a_code_root_is_refused(tmp_path: Path) -> None:
    """Externality must be assertable at bind time, not only at initialization.

    The test above covers ``initialize_control_store``, which is not this resolver's code. A store can be
    initialized disjointly and later moved, or have its manifest written elsewhere, and
    ``load_store_manifest`` checks the manifest's own bindings without re-checking disjointness. Without
    this control the resolver would bind cleanly to a control root sitting inside a code root — where a
    repository commit *could* author the records, which is exactly what the substrate must rule out.
    """
    code_root = tmp_path / "code"
    code_root.mkdir()
    control_root = tmp_path / "control"
    initialize_control_store([code_root], control_root, PROJECT_ID)

    # Same store bytes, re-registered so the control root now sits inside a declared code root.
    manifest_path = control_root / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["code_roots"] = [str(tmp_path.resolve())]
    manifest["manifest_hash"] = _manifest_hash(manifest)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ArsError, match="disjoint"):
        ControlStoreAuthorityResolver(
            ControlBinding(
                code_roots=(tmp_path.resolve(),),
                control_root=control_root.resolve(),
                project_id=PROJECT_ID,
                schema_root=SCHEMA_PATH.parents[1],
                store_identity=manifest["store_identity"],
            )
        )


def test_binding_a_resolver_without_registered_code_roots_is_refused(tmp_path: Path) -> None:
    """An empty code-root set cannot vacuously satisfy disjointness."""
    code_root = tmp_path / "code"
    code_root.mkdir()
    control_root = tmp_path / "control"
    initialize_control_store([code_root], control_root, PROJECT_ID)

    manifest_path = control_root / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["code_roots"] = []
    manifest["manifest_hash"] = _manifest_hash(manifest)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ArsError, match="code roots required"):
        ControlStoreAuthorityResolver(
            ControlBinding(
                code_roots=(),
                control_root=control_root.resolve(),
                project_id=PROJECT_ID,
                schema_root=SCHEMA_PATH.parents[1],
                store_identity=manifest["store_identity"],
            )
        )


def test_external_record_store_validates_identity_and_cas_idempotently(tmp_path: Path) -> None:
    store = ExternalAssuranceRecordStore(_binding(tmp_path))
    body = _valid_actor_body()

    first = store.write(
        record_class="canonical_actor",
        record_id=RECORD_ID,
        revision=1,
        expected_previous_revision=0,
        record=body,
    )
    repeat = store.write(
        record_class="canonical_actor",
        record_id=RECORD_ID,
        revision=1,
        expected_previous_revision=0,
        record=body,
    )
    assert repeat == first
    assert first.revision == 1
    assert first.record_class == "canonical_actor"
    assert len(first.canonical_sha256) == 64

    with pytest.raises(ConflictError, match="expected previous revision"):
        store.write(
            record_class="canonical_actor",
            record_id=RECORD_ID,
            revision=3,
            expected_previous_revision=0,
            record=_valid_actor_body(name="gap"),
        )
    with pytest.raises(ConflictError, match="different content"):
        store.write(
            record_class="canonical_actor",
            record_id=RECORD_ID,
            revision=1,
            expected_previous_revision=0,
            record=_valid_actor_body(name="divergent"),
        )


def test_external_record_store_rejects_schema_invalid_and_identity_mismatch(tmp_path: Path) -> None:
    store = ExternalAssuranceRecordStore(_binding(tmp_path))
    with pytest.raises(SchemaError):
        store.write(
            record_class="canonical_actor",
            record_id=RECORD_ID,
            revision=1,
            expected_previous_revision=0,
            record={"record_type": "canonical_actor", "status": "active"},
        )
    with pytest.raises(SchemaError, match="identity"):
        store.write(
            record_class="canonical_actor",
            record_id=RECORD_ID,
            revision=1,
            expected_previous_revision=0,
            record={**_valid_actor_body(), "actor_id": "act_01978abc-2000-7000-8000-000000002001"},
        )


def test_resolver_schema_validates_every_resolved_record(tmp_path: Path) -> None:
    resolver, objects, root = _resolver(tmp_path)
    objects.write(EXTERNAL_RECORD_KIND, STORE_RECORD_ID, 1, {"record_type": "canonical_actor", "status": "active"})
    with pytest.raises(SchemaError):
        resolver.resolve(record_id=RECORD_ID, record_class="canonical_actor", authority_root=root, phase="load")
