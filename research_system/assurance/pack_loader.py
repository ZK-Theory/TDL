"""Fail-closed loader for the ``TDL_private`` assurance-pack candidate.

The WP6.3 upstream contract places
``loader_computes_exact_candidate_subject_identity`` between candidate
authorship and independent review, and names
``research_system.assurance.validate_tdl_private_pack_for_acceptance`` as the
public semantic interface invoked by the pack loader, the pack review gate, the
owner acceptance gate, and every pack consumer.

The point of the seam is that no participant computes its own subject. The
candidate cannot supply an expected identity, the caller cannot supply a hash
oracle, and the reviewer does not hand-compute a digest: the loader derives
``pack_git_blob`` and ``pack_raw_sha256`` from the raw candidate bytes and every
other authority arrives as an independent input.

Two enforcement layers exist and are deliberately not duplicated here. The pack
JSON Schema (``ars://assurance/packs/tdl-private/1.0``) is closed on every
object and pins ``candidate_state``, the identity constants, and the whole
reference/lane/fixture shape. Anything the schema rejects is not re-checked at
runtime, because an unreachable check can never be given a watched negative.
The runtime checks below are exactly those the schema cannot express: agreement
with independently supplied accepted subjects, revalidation against a current
reference snapshot, resolution of external lifecycle records, and time.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import yaml

from research_system.errors import ArsError
from research_system.schema_registry import SchemaRegistry


PACK_SCHEMA_ID = "ars://assurance/packs/tdl-private/1.0"

_ROOT = Path(__file__).resolve().parents[2]
_SCHEMAS_ROOT = _ROOT / ".research-system" / "schemas"
_CONTRACT_PATH = _ROOT / ".research-system" / "contracts" / "wp6-3-tdl-private-assurance-pack.yaml"
_PACK_SCHEMA_PATH = _SCHEMAS_ROOT / "assurance" / "assurance-pack.schema.json"

#: Phases the contract requires every external authority to resolve at. Resolution must be
#: stable across all three; a record that changes between load and consumption is stale.
AUTHORITY_RESOLUTION_PHASES = ("load", "acceptance", "consumption")


class PackUnconsumable(ArsError):
    """Raised whenever the candidate cannot be consumed or accepted.

    The contract's ``failure_behavior`` is
    ``pack_unconsumable_and_no_acceptance``: there is no partial or
    best-effort acceptance, so every failure path raises this and nothing
    returns a degraded result.
    """


class ContentAddressedAuthorityResolver(Protocol):
    """Trusted W1/W2 resolver for opaque external lifecycle record ids.

    The candidate may not supply record bodies and the caller may not supply a
    hash oracle, so this is the only channel through which external records
    enter the loader.
    """

    def resolve(self, *, record_id: str, record_class: str, authority_root: str, phase: str) -> Mapping[str, object]:
        """Return the external record body for an opaque id.

        Args:
            record_id: Opaque content-addressed record identifier.
            record_class: Required record class the caller expects.
            authority_root: Independently supplied authority root to resolve under.
            phase: One of :data:`AUTHORITY_RESOLUTION_PHASES`.

        Returns:
            The resolved record body.
        """


@dataclass(frozen=True)
class PackAcceptanceSubject:
    """The exact candidate subject an independent review and owner acceptance bind.

    Attributes:
        pack_id: Pack family name.
        assurance_pack_id: W1-allocated object identity carried by the candidate.
        assurance_pack_revision: Object revision.
        canonical_repository_path: Canonical path of the candidate.
        pack_git_blob: Git blob id computed from the raw candidate bytes.
        pack_raw_sha256: SHA-256 computed from the raw candidate bytes.
        schema_id: Pack schema identifier.
        schema_version: Pack schema version.
        schema_repository_path: Pack schema repository path.
        schema_git_blob: Accepted pack schema blob id.
        schema_canonical_sha256: Accepted pack schema SHA-256.
    """

    pack_id: str
    assurance_pack_id: str
    assurance_pack_revision: int
    canonical_repository_path: str
    pack_git_blob: str
    pack_raw_sha256: str
    schema_id: str
    schema_version: str
    schema_repository_path: str
    schema_git_blob: str
    schema_canonical_sha256: str


def git_blob_id(data: bytes) -> str:
    """Return the Git blob object id for exact bytes.

    Args:
        data: Raw bytes to address.

    Returns:
        The 40-character hexadecimal blob id.
    """
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=1)
def _pack_schema_registry() -> SchemaRegistry:
    """Return the registry for the accepted schema tree.

    Cached because the registry loads and checks every registered schema below the root,
    and this seam is invoked by every pack consumer.
    """
    return SchemaRegistry(_SCHEMAS_ROOT)


def _accepted_repository_artifact(path: Path, accepted_subject: Mapping[str, object], label: str) -> bytes:
    """Read a repository artifact and prove it is the independently accepted one.

    The loader derives the contract's requirements from the contract itself. That is only
    sound once the bytes on disk are shown to be the bytes an external acceptance record
    named, which is why the accepted subject is an input rather than something read here.

    Args:
        path: Repository path of the artifact.
        accepted_subject: Independently supplied accepted subject for it.
        label: Human-readable artifact label used in failure messages.

    Returns:
        The artifact bytes.

    Raises:
        PackUnconsumable: If the artifact is unreadable or is not the accepted bytes.
    """
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise PackUnconsumable(f"{label} is unreadable at {path}") from exc
    if b"\r" in data:
        raise PackUnconsumable(f"{label} is not on the git_blob_utf8_lf canonical byte surface")
    if accepted_subject.get("git_blob") != git_blob_id(data) or accepted_subject.get("canonical_sha256") != _sha256(
        data
    ):
        raise PackUnconsumable(f"{label} bytes differ from the independently accepted subject")
    return data


def _parse_candidate(raw_candidate_pack_bytes: bytes) -> dict:
    """Parse and schema-validate raw candidate bytes.

    Args:
        raw_candidate_pack_bytes: Exact candidate bytes.

    Returns:
        The parsed candidate object.

    Raises:
        PackUnconsumable: If the bytes are off-surface, unparseable, or schema-invalid.
    """
    if b"\r" in raw_candidate_pack_bytes or not raw_candidate_pack_bytes.endswith(b"\n"):
        raise PackUnconsumable("candidate bytes must be exact UTF-8/LF with a terminal LF")
    try:
        decoded = raw_candidate_pack_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PackUnconsumable("candidate bytes must be exact UTF-8/LF with a terminal LF") from exc
    try:
        parsed = yaml.safe_load(decoded)
    except yaml.YAMLError as exc:
        raise PackUnconsumable("candidate bytes must parse to one pack object") from exc
    if not isinstance(parsed, dict):
        raise PackUnconsumable("candidate bytes must parse to one pack object")
    try:
        _pack_schema_registry().validate(PACK_SCHEMA_ID, parsed)
    except ArsError as exc:
        raise PackUnconsumable(f"candidate fails the accepted pack schema: {exc}") from exc
    return parsed


def _require_key(mapping: object, key: str, label: str) -> object:
    """Read a required key, failing closed instead of leaking ``KeyError``.

    The candidate's own fields are guaranteed by the pack schema, so they are read
    directly. These are the contract-derived and resolver-derived reads, which a revised
    contract or a malformed resolver response can omit — and an escaping ``KeyError``
    would break the documented ``PackUnconsumable``-only failure surface.

    Args:
        mapping: Value expected to be a mapping.
        key: Required key.
        label: Human-readable location used in failure messages.

    Returns:
        The value at ``key``.

    Raises:
        PackUnconsumable: If the value is not a mapping or the key is absent.
    """
    if not isinstance(mapping, Mapping):
        raise PackUnconsumable(f"{label} is not a mapping")
    if key not in mapping:
        raise PackUnconsumable(f"{label} does not declare {key}")
    return mapping[key]


def _parse_timestamp(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PackUnconsumable(f"{label} is not an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise PackUnconsumable(f"{label} must carry a timezone")
    return parsed


def _require_matching_subject(observed: object, accepted: Mapping[str, object], label: str) -> None:
    if observed != dict(accepted):
        raise PackUnconsumable(f"candidate {label} is stale or foreign to the accepted subject")


def _revalidate_references(pack: Mapping[str, object], snapshot: Mapping[str, Mapping[str, object]]) -> None:
    """Re-resolve every exact reference against the current snapshot.

    A pinned reference row is a claim about the world at authoring time. The contract
    requires that claim be re-resolved from the current snapshot at every phase, so a
    reference edited or deactivated after authoring stales the candidate instead of
    passing on the strength of its own pin.

    Args:
        pack: Parsed candidate.
        snapshot: Current identity/activation state per reference id.

    Raises:
        PackUnconsumable: If any reference is unresolved, drifted, or not acceptance-active.
    """
    references = pack["references"]
    rows: Sequence[Mapping[str, object]] = [
        *references["contract_references"],  # type: ignore[index]
        *references["skill_references"],  # type: ignore[index]
    ]
    for row in rows:
        reference_id = row["reference_id"]
        current = snapshot.get(reference_id)  # type: ignore[arg-type]
        if current is None:
            raise PackUnconsumable(f"reference does not resolve in the current snapshot: {reference_id}")
        if current.get("git_blob") != row["git_blob"] or current.get("canonical_sha256") != row["canonical_sha256"]:
            raise PackUnconsumable(f"reference identity drifted since authoring: {reference_id}")
        if current.get("activation_state") != row["activation_state"]:
            raise PackUnconsumable(f"reference activation changed since authoring: {reference_id}")
        if not current.get("pack_acceptance_eligible", False):
            raise PackUnconsumable(f"reference is not acceptance-eligible: {reference_id}")
    missing = set(snapshot) - {row["reference_id"] for row in rows}
    if missing:
        raise PackUnconsumable(f"current snapshot carries references the candidate omits: {sorted(missing)}")


def _resolve_records(
    required_classes: Sequence[str],
    opaque_external_record_ids: Mapping[str, str],
    resolver: ContentAddressedAuthorityResolver,
    authority_root: str,
) -> dict[str, Mapping[str, object]]:
    """Resolve every required external record, at every declared phase.

    Args:
        required_classes: Record classes the contract declares required.
        opaque_external_record_ids: Opaque id per record class.
        resolver: Trusted content-addressed authority resolver.
        authority_root: Independently supplied authority root.

    Returns:
        The resolved record body per record class.

    Raises:
        PackUnconsumable: If any record is missing, foreign, inactive, or unstable across phases.
    """
    if not isinstance(required_classes, (list, tuple)) or not all(isinstance(c, str) for c in required_classes):
        raise PackUnconsumable("contract does not declare required_record_types as a list of record classes")
    missing = [record_class for record_class in required_classes if record_class not in opaque_external_record_ids]
    if missing:
        raise PackUnconsumable(f"no external record id supplied for required classes: {sorted(missing)}")

    resolved: dict[str, Mapping[str, object]] = {}
    for record_class in required_classes:
        record_id = opaque_external_record_ids[record_class]
        per_phase: list[Mapping[str, object]] = []
        for phase in AUTHORITY_RESOLUTION_PHASES:
            try:
                record = resolver.resolve(
                    record_id=record_id,
                    record_class=record_class,
                    authority_root=authority_root,
                    phase=phase,
                )
            except Exception as exc:  # noqa: BLE001 - any resolver failure is fail-closed
                raise PackUnconsumable(f"external record did not resolve at phase {phase}: {record_class}") from exc
            if not isinstance(record, Mapping):
                raise PackUnconsumable(f"external record is not a record body: {record_class}")
            per_phase.append(record)
        if any(record != per_phase[0] for record in per_phase[1:]):
            raise PackUnconsumable(f"external record is unstable across authority phases: {record_class}")

        record = per_phase[0]
        if record.get("record_id") != record_id or record.get("record_type") != record_class:
            raise PackUnconsumable(f"resolved record does not identify as the requested record: {record_class}")
        if record.get("authority_root") != authority_root:
            raise PackUnconsumable(f"resolved record is bound to a foreign authority root: {record_class}")
        if record.get("lifecycle_state") != "active":
            raise PackUnconsumable(f"resolved record is not active: {record_class}")
        resolved[record_class] = record
    return resolved


def _require_registered_object(record: Mapping[str, object], pack: Mapping[str, object]) -> None:
    if (
        record.get("assurance_pack_id") != pack["assurance_pack_id"]
        or record.get("assurance_pack_revision") != pack["assurance_pack_revision"]
        or record.get("canonical_repository_path") != pack["canonical_repository_path"]
    ):
        raise PackUnconsumable("candidate object identity is not the W1-registered pack object")


def _require_accepted_requirement(record: Mapping[str, object], pack: Mapping[str, object]) -> None:
    reference = pack["assurance_requirement_reference"]
    if (
        record.get("assurance_requirement_id") != reference["assurance_requirement_id"]  # type: ignore[index]
        or record.get("revision") != reference["revision"]  # type: ignore[index]
        or record.get("content_sha256") != reference["acceptance_record_sha256"]  # type: ignore[index]
    ):
        raise PackUnconsumable("candidate requirement reference is not the accepted assurance requirement")
    if record.get("prospective_producer_actor_id") != pack["producer_actor_id"]:
        raise PackUnconsumable("prospective producer relationship is stale")


def _require_subject_bound_lifecycle(
    resolved: Mapping[str, Mapping[str, object]],
    subject: PackAcceptanceSubject,
    opaque_external_record_ids: Mapping[str, str],
    evaluation_time: datetime,
) -> None:
    """Bind review and owner acceptance to the loader-computed subject, in order.

    Args:
        resolved: Resolved external records by class.
        subject: The loader-computed candidate subject.
        opaque_external_record_ids: Opaque id per record class.
        evaluation_time: Caller-supplied evaluation time.

    Raises:
        PackUnconsumable: If either decision binds a different subject or the order inverts.
    """
    review = _require_key(resolved, "independent_pack_review", "resolved external records")
    owner = _require_key(resolved, "stephen_owner_acceptance", "resolved external records")
    review_record_id = _require_key(opaque_external_record_ids, "independent_pack_review", "opaque external record ids")
    expected = {
        "pack_git_blob": subject.pack_git_blob,
        "pack_raw_sha256": subject.pack_raw_sha256,
        "assurance_pack_id": subject.assurance_pack_id,
        "assurance_pack_revision": subject.assurance_pack_revision,
    }
    for record, label in ((review, "independent pack review"), (owner, "owner acceptance")):
        observed = record.get("subject")
        if not isinstance(observed, Mapping) or any(observed.get(key) != value for key, value in expected.items()):
            raise PackUnconsumable(f"{label} binds a different subject than the loader computed")
    if owner.get("review_record_id") != review_record_id:
        raise PackUnconsumable("owner acceptance does not bind the resolved independent pack review")

    reviewed_at = _parse_timestamp(str(review.get("decided_at")), "independent pack review decided_at")
    accepted_at = _parse_timestamp(str(owner.get("decided_at")), "owner acceptance decided_at")
    if not reviewed_at < accepted_at <= evaluation_time:
        raise PackUnconsumable("owner acceptance must follow the independent review and precede evaluation")


def validate_tdl_private_pack_for_acceptance(
    *,
    accepted_upstream_contract_subject: Mapping[str, object],
    accepted_schema_subject: Mapping[str, object],
    trusted_w1_w2_content_addressed_authority_resolver: ContentAddressedAuthorityResolver,
    independently_supplied_authority_root: str,
    opaque_external_record_ids: Mapping[str, str],
    current_exact_reference_snapshot: Mapping[str, Mapping[str, object]],
    raw_candidate_pack_bytes: bytes,
    evaluation_time: datetime,
) -> PackAcceptanceSubject:
    """Compute and validate the exact acceptance subject of a ``TDL_private`` pack candidate.

    Every input is independent of the candidate. The subject identity is derived from
    ``raw_candidate_pack_bytes`` here rather than read from the candidate, so a candidate
    cannot name its own identity and a reviewer never hand-computes one.

    Args:
        accepted_upstream_contract_subject: Externally accepted subject of the WP6.3 contract.
        accepted_schema_subject: Externally accepted subject of the pack schema.
        trusted_w1_w2_content_addressed_authority_resolver: Trusted external record resolver.
        independently_supplied_authority_root: Authority root the records must resolve under.
        opaque_external_record_ids: Opaque record id per required record class.
        current_exact_reference_snapshot: Current identity/activation state per reference id.
        raw_candidate_pack_bytes: Exact candidate bytes.
        evaluation_time: Timezone-aware evaluation time.

    Returns:
        The exact subject an independent review and owner acceptance must bind.

    Raises:
        PackUnconsumable: On any failure. There is no partial acceptance.
    """
    if evaluation_time.tzinfo is None:
        raise PackUnconsumable("evaluation_time must carry a timezone")

    contract_bytes = _accepted_repository_artifact(
        _CONTRACT_PATH, accepted_upstream_contract_subject, "upstream contract"
    )
    _accepted_repository_artifact(_PACK_SCHEMA_PATH, accepted_schema_subject, "pack schema")
    contract = yaml.safe_load(contract_bytes.decode("utf-8"))
    required = _require_key(contract, "required_pack_contract", "upstream contract")

    pack = _parse_candidate(raw_candidate_pack_bytes)

    # The candidate's own claims about the contract and schema must equal the independently
    # accepted subjects. A coordinated edit of both sides still fails, because neither side
    # of this comparison is derived from the candidate.
    _require_matching_subject(
        pack["upstream_contract_reference"], accepted_upstream_contract_subject, "upstream contract reference"
    )
    _require_matching_subject(pack["schema_reference"], accepted_schema_subject, "pack schema reference")

    _revalidate_references(pack, current_exact_reference_snapshot)

    evidence = _require_key(required, "external_acceptance_evidence", "upstream contract")
    required_record_types = _require_key(evidence, "required_record_types", "external acceptance evidence")
    resolved = _resolve_records(
        required_record_types,
        opaque_external_record_ids,
        trusted_w1_w2_content_addressed_authority_resolver,
        independently_supplied_authority_root,
    )
    _require_registered_object(_require_key(resolved, "registered_pack_object", "resolved external records"), pack)
    _require_accepted_requirement(
        _require_key(resolved, "accepted_assurance_requirement", "resolved external records"), pack
    )

    currency = pack["currency"]
    authored_at = _parse_timestamp(currency["authored_at"], "authored_at")
    effective_at = _parse_timestamp(currency["effective_at"], "effective_at")
    expires_at = _parse_timestamp(currency["expires_at"], "expires_at")
    if not authored_at <= effective_at < expires_at:
        raise PackUnconsumable("candidate currency time order is invalid")
    if not effective_at <= evaluation_time < expires_at:
        raise PackUnconsumable("candidate is not current at the evaluation time")

    subject = PackAcceptanceSubject(
        pack_id=pack["pack_id"],
        assurance_pack_id=pack["assurance_pack_id"],
        assurance_pack_revision=pack["assurance_pack_revision"],
        canonical_repository_path=pack["canonical_repository_path"],
        pack_git_blob=git_blob_id(raw_candidate_pack_bytes),
        pack_raw_sha256=_sha256(raw_candidate_pack_bytes),
        schema_id=pack["schema_reference"]["schema_id"],
        schema_version=pack["schema_reference"]["schema_version"],
        schema_repository_path=pack["schema_reference"]["repository_path"],
        schema_git_blob=pack["schema_reference"]["git_blob"],
        schema_canonical_sha256=pack["schema_reference"]["canonical_sha256"],
    )
    _require_subject_bound_lifecycle(resolved, subject, opaque_external_record_ids, evaluation_time)
    return subject
