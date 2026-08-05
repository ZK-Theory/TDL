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
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from research_system.errors import ArsError
from research_system.assurance.external_records import ExternalRecordResolution, _RECORD_ENVELOPE
from research_system.schema_registry import SchemaRegistry


PACK_SCHEMA_ID = "ars://assurance/packs/tdl-private/1.0"

_ROOT = Path(__file__).resolve().parents[2]
_SCHEMAS_ROOT = _ROOT / ".research-system" / "schemas"
_CONTRACT_PATH = _ROOT / ".research-system" / "contracts" / "wp6-3-tdl-private-assurance-pack.yaml"
_PACK_SCHEMA_PATH = _SCHEMAS_ROOT / "assurance" / "assurance-pack.schema.json"

#: Phases the contract requires every external authority to resolve at. Resolution must be
#: stable across all three; a record that changes between load and consumption is stale.
AUTHORITY_RESOLUTION_PHASES = ("load", "acceptance", "consumption")

#: Identity field, lifecycle field, and active lifecycle value per record class,
#: loaded from the shared exact external-record schema catalogue.

#: Independence ordering spanning every grade the record schemas admit. The requirement models use I0-I2
#: while the relationship record schema admits I2-I3, so the comparison needs the union, not either range.
_INDEPENDENCE_ORDER = {"I0": 0, "I1": 1, "I2": 2, "I3": 3}


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

    def resolve_with_receipt(
        self,
        *,
        record_id: str,
        record_class: str,
        authority_root: str,
        phase: str,
    ) -> ExternalRecordResolution:
        """Return the body with trusted storage revision and canonical digest."""


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


def _accepted_repository_artifact(
    path: Path,
    accepted_subject: Mapping[str, object],
    label: str,
    trusted_bytes: bytes | None = None,
) -> bytes:
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
    if trusted_bytes is None:
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise PackUnconsumable(f"{label} is unreadable at {path}") from exc
    else:
        data = trusted_bytes
        if not isinstance(data, bytes):
            raise PackUnconsumable(f"{label} trusted bytes are not bytes")
    if b"\r" in data:
        raise PackUnconsumable(f"{label} is not on the git_blob_utf8_lf canonical byte surface")
    if accepted_subject.get("git_blob") != git_blob_id(data) or accepted_subject.get("canonical_sha256") != _sha256(
        data
    ):
        raise PackUnconsumable(f"{label} bytes differ from the independently accepted subject")
    return data


def _parse_candidate(raw_candidate_pack_bytes: bytes, trusted_schema_bytes: bytes | None = None) -> dict:
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
        if trusted_schema_bytes is None:
            _pack_schema_registry().validate(PACK_SCHEMA_ID, parsed)
        else:
            schema = json.loads(trusted_schema_bytes)
            Draft202012Validator.check_schema(schema)
            errors = sorted(
                Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(parsed),
                key=lambda error: list(error.absolute_path),
            )
            if errors:
                raise ValueError("; ".join(error.message for error in errors))
    except (ArsError, TypeError, ValueError, json.JSONDecodeError) as exc:
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


def _parse_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise PackUnconsumable(f"{label} is not an RFC 3339 timestamp")
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


def _require_source_authority_projection(contract: Mapping[str, object], pack: Mapping[str, object]) -> None:
    source_authority = _require_key(contract, "source_authority", "upstream contract")
    governing_sources = _require_key(source_authority, "governing_sources", "contract source_authority")
    if not isinstance(governing_sources, Sequence) or isinstance(governing_sources, (str, bytes, bytearray)):
        raise PackUnconsumable("contract source_authority governing_sources is not a sequence")
    expected = {
        "accepted_plan_revision": _require_key(source_authority, "accepted_plan_revision", "contract source_authority"),
        "governing_sources": list(governing_sources),
    }
    if pack.get("source_authority") != expected:
        raise PackUnconsumable("candidate source_authority differs from accepted contract")


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
    opaque_external_record_ids: Mapping[str, object],
    resolver: ContentAddressedAuthorityResolver,
    authority_root: str,
) -> dict[str, ExternalRecordResolution]:
    """Resolve every required external record, at every declared phase.

    Args:
        required_classes: Record classes the contract declares required.
        opaque_external_record_ids: Opaque id per record class.
        resolver: Trusted content-addressed authority resolver.
        authority_root: Independently supplied authority root.

    Returns:
        The trusted storage resolution receipt per record class.

    Raises:
        PackUnconsumable: If any record is missing, foreign, inactive, or unstable across phases.
    """
    if not isinstance(required_classes, (list, tuple)) or not all(isinstance(c, str) for c in required_classes):
        raise PackUnconsumable("contract does not declare required_record_types as a list of record classes")
    missing = [record_class for record_class in required_classes if record_class not in opaque_external_record_ids]
    if missing:
        raise PackUnconsumable(f"no external record id supplied for required classes: {sorted(missing)}")

    resolved: dict[str, ExternalRecordResolution] = {}
    for record_class in required_classes:
        requested = opaque_external_record_ids[record_class]
        if isinstance(requested, Mapping):
            record_ids = {str(label): value for label, value in requested.items()}
        else:
            record_ids = {"default": requested}
        if not record_ids or not all(isinstance(record_id, str) and record_id for record_id in record_ids.values()):
            raise PackUnconsumable(f"external record ids are not exact: {record_class}")
        for semantic_label, record_id in record_ids.items():
            per_phase: list[ExternalRecordResolution] = []
            resolver_with_receipt = getattr(resolver, "resolve_with_receipt", None)
            if not callable(resolver_with_receipt):
                raise PackUnconsumable(
                    f"external record resolver does not provide trusted storage receipts: {record_class}"
                )
            for phase in AUTHORITY_RESOLUTION_PHASES:
                try:
                    resolution = resolver_with_receipt(
                        record_id=record_id,
                        record_class=record_class,
                        authority_root=authority_root,
                        phase=phase,
                    )
                except Exception as exc:  # noqa: BLE001 - any resolver failure is fail-closed
                    raise PackUnconsumable(f"external record did not resolve at phase {phase}: {record_class}") from exc
                if not isinstance(resolution, ExternalRecordResolution) or not isinstance(resolution.record, Mapping):
                    raise PackUnconsumable(f"external record lacks trusted storage metadata: {record_class}")
                record = resolution.record
                if (
                    resolution.record_class != record_class
                    or resolution.record_id != record_id
                    or isinstance(resolution.revision, bool)
                    or not isinstance(resolution.revision, int)
                    or resolution.revision < 1
                    or not isinstance(resolution.canonical_sha256, str)
                ):
                    raise PackUnconsumable(f"external record trusted identity is not exact: {record_class}")
                if "content_sha256" in record:
                    raise PackUnconsumable(f"schema-forbidden content_sha256 in external record: {record_class}")
                per_phase.append(resolution)
            if any(
                (
                    resolution.record != per_phase[0].record
                    or resolution.revision != per_phase[0].revision
                    or resolution.canonical_sha256 != per_phase[0].canonical_sha256
                )
                for resolution in per_phase[1:]
            ):
                raise PackUnconsumable(f"external record is unstable across authority phases: {record_class}")

            resolution = per_phase[0]
            record = resolution.record
            envelope = _RECORD_ENVELOPE.get(record_class)
            if envelope is None:
                raise PackUnconsumable(f"no accepted record envelope for record class: {record_class}")
            id_field, state_field, active_state = envelope
            if record.get(id_field) != record_id or record.get("record_type") != record_class:
                raise PackUnconsumable(f"resolved record does not identify as the requested record: {record_class}")
            if record.get(state_field) != active_state:
                raise PackUnconsumable(f"resolved record is not active: {record_class}")
            key = record_class if semantic_label == "default" else f"{record_class}:{semantic_label}"
            resolved[key] = resolution
    return resolved


def _require_registered_object(record: Mapping[str, object], pack: Mapping[str, object]) -> None:
    if (
        record.get("assurance_pack_id") != pack["assurance_pack_id"]
        or record.get("revision") != pack["assurance_pack_revision"]
        or record.get("canonical_repository_path") != pack["canonical_repository_path"]
    ):
        raise PackUnconsumable("candidate object identity is not the W1-registered pack object")


def _require_accepted_requirement(
    resolved: Mapping[str, ExternalRecordResolution],
    pack: Mapping[str, object],
    evaluation_time: datetime,
) -> None:
    """Bind the candidate to the accepted requirement and its current producer relationship.

    Args:
        resolved: Resolved external records by class.
        pack: Parsed candidate pack.
        evaluation_time: Caller-supplied evaluation time.

    Raises:
        PackUnconsumable: If the reference is not the accepted requirement, or the producer relationship
            names a different producer, has lapsed, or no longer meets the accepted independence floor.
    """
    resolution = _require_key(resolved, "accepted_assurance_requirement", "resolved external records")
    record = resolution
    reference = pack["assurance_requirement_reference"]
    if (
        record.get("assurance_requirement_id") != reference["assurance_requirement_id"]  # type: ignore[index]
        or resolution.revision != reference["revision"]  # type: ignore[index]
        or record.get("revision") != reference["revision"]  # type: ignore[index]
        or resolution.canonical_sha256 != reference["acceptance_record_sha256"]  # type: ignore[index]
    ):
        raise PackUnconsumable("candidate requirement reference is not the accepted assurance requirement")
    if record.get("prospective_producer_actor_id") != pack["producer_actor_id"]:
        raise PackUnconsumable("prospective producer relationship is stale")
    scope_relationship = resolved.get("producer_relationship_evidence:requirement_scope")
    if scope_relationship is None:
        # Preserve the original single-relationship test seam.  Production
        # runners supply the explicit semantic requirement-scope locator.
        scope_relationship = _require_key(resolved, "producer_relationship_evidence", "resolved external records")
    _require_current_producer_relationship(record, scope_relationship, pack, evaluation_time)


def _require_relationship_grade(
    relationship: Mapping[str, object],
    minimum_grade: object,
    *,
    relationship_label: str,
    insufficient_message: str,
) -> None:
    """Require a recognised relationship grade at or above a declared floor.

    Args:
        relationship: Resolved producer relationship evidence record.
        minimum_grade: Minimum independence grade declared by the caller's record.
        relationship_label: Label used for an unrecognised-grade failure.
        insufficient_message: Caller-specific failure when the grade is below its floor.

    Raises:
        PackUnconsumable: If either grade is unknown or the relationship is below the floor.
    """
    observed = relationship.get("grade")
    if observed not in _INDEPENDENCE_ORDER or minimum_grade not in _INDEPENDENCE_ORDER:
        raise PackUnconsumable(f"{relationship_label} grade is not a recognised independence grade")
    if _INDEPENDENCE_ORDER[str(observed)] < _INDEPENDENCE_ORDER[str(minimum_grade)]:
        raise PackUnconsumable(insufficient_message)


def _require_current_producer_relationship(
    requirement: Mapping[str, object],
    relationship: Mapping[str, object],
    pack: Mapping[str, object],
    evaluation_time: datetime,
) -> None:
    """Require the relationship the requirement was accepted under to still hold, now.

    Actor equality alone does not implement the staleness rule: the accepted requirement pins a
    ``scope_relationship_record_id`` and a ``minimum_independence_grade``, and the relationship record
    carries its own validity window. A relationship that has lapsed, been re-graded downward, or been
    replaced by a different relationship record is stale even when every actor id still matches.

    Args:
        requirement: Resolved accepted assurance requirement record.
        relationship: Resolved producer relationship evidence record.
        pack: Parsed candidate pack.
        evaluation_time: Caller-supplied evaluation time.

    Raises:
        PackUnconsumable: If the relationship is a different record, omits the producer, has lapsed, or
            grades below the accepted independence floor.
    """
    if relationship.get("relationship_record_id") != requirement.get("scope_relationship_record_id"):
        raise PackUnconsumable("producer relationship evidence is not the relationship the requirement pins")
    producer = pack["producer_actor_id"]
    if producer not in {relationship.get("subject_actor_id"), relationship.get("object_actor_id")}:
        raise PackUnconsumable("producer relationship evidence does not describe the candidate's producer")

    effective_at = _parse_timestamp(relationship.get("effective_at"), "relationship effective_at")
    expires_at = _parse_timestamp(relationship.get("expires_at"), "relationship expires_at")
    if not effective_at <= evaluation_time < expires_at:
        raise PackUnconsumable("producer relationship is not current at the evaluation time")

    _require_relationship_grade(
        relationship,
        requirement.get("minimum_independence_grade"),
        relationship_label="producer relationship",
        insufficient_message="producer relationship no longer meets the accepted independence floor",
    )


def _require_review_relationship(
    review: Mapping[str, object],
    relationship: Mapping[str, object],
    pack: Mapping[str, object],
) -> None:
    """Require the review to bind the already-current relationship at its declared grade.

    The accepted-requirement check runs first and establishes the shared
    relationship record's current validity window. Rechecking that same window
    here would create an unreachable duplicate failure branch.

    Args:
        review: Resolved independent pack review record.
        relationship: Current producer relationship evidence established by the
            accepted-requirement check.
        pack: Parsed candidate pack.

    Raises:
        PackUnconsumable: If the review omits or names another relationship, the
            actor roles or context do not match, or the relationship grade is
            below the review's declared floor.
    """

    review_relationship_id = review.get("relationship_record_id")
    if not isinstance(review_relationship_id, str) or not review_relationship_id:
        raise PackUnconsumable("independent pack review relationship_record_id is required")
    if review_relationship_id != relationship.get("relationship_record_id"):
        raise PackUnconsumable("independent pack review does not bind the resolved producer relationship")

    producer = pack["producer_actor_id"]
    reviewer = review.get("reviewer_actor_id")
    if (
        review.get("producer_actor_id") != producer
        or not isinstance(reviewer, str)
        or not reviewer
        or reviewer == producer
        or relationship.get("relationship_context") != "pack_scientific_review"
        or relationship.get("subject_actor_id") != reviewer
        or relationship.get("object_actor_id") != producer
    ):
        raise PackUnconsumable("producer relationship evidence does not bind the declared reviewer and producer roles")

    _require_relationship_grade(
        relationship,
        review.get("minimum_independence_grade"),
        relationship_label="independent review relationship",
        insufficient_message="producer relationship does not meet the independent pack review floor",
    )


def _require_subject_bound_lifecycle(
    resolved: Mapping[str, Mapping[str, object]],
    subject: PackAcceptanceSubject,
    opaque_external_record_ids: Mapping[str, str],
    pack: Mapping[str, object],
    evaluation_time: datetime,
) -> None:
    """Bind review and owner acceptance to the loader-computed subject, in order.

    Args:
        resolved: Resolved external records by class.
        subject: The loader-computed candidate subject.
        opaque_external_record_ids: Opaque id per record class.
        pack: Parsed candidate pack.
        evaluation_time: Caller-supplied evaluation time.

    Raises:
        PackUnconsumable: If either decision binds a different subject or the order inverts.
    """
    review = _require_key(resolved, "independent_pack_review", "resolved external records")
    owner = _require_key(resolved, "stephen_owner_acceptance", "resolved external records")
    review_relationship = resolved.get("producer_relationship_evidence:pack_review")
    if review_relationship is None:
        # Preserve the original single-relationship test seam.  Production
        # runners supply the explicit semantic pack-review locator above.
        review_relationship = _require_key(resolved, "producer_relationship_evidence", "resolved external records")
    _require_review_relationship(
        review,
        review_relationship,
        pack,
    )
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

    reviewed_at = _parse_timestamp(str(review.get("reviewed_at")), "independent pack review reviewed_at")
    accepted_at = _parse_timestamp(str(owner.get("decided_at")), "owner acceptance decided_at")
    relationship_effective_at = _parse_timestamp(
        str(review_relationship.get("effective_at")), "pack-review relationship effective_at"
    )
    relationship_expires_at = _parse_timestamp(
        str(review_relationship.get("expires_at")), "pack-review relationship expires_at"
    )
    if not relationship_effective_at <= reviewed_at < relationship_expires_at:
        raise PackUnconsumable("independent pack review is outside its relationship validity window")
    if not relationship_effective_at <= evaluation_time < relationship_expires_at:
        raise PackUnconsumable("pack-review relationship is not current at the evaluation time")
    if not reviewed_at < accepted_at <= evaluation_time:
        raise PackUnconsumable("owner acceptance must follow the independent review and precede evaluation")


def validate_tdl_private_pack_for_acceptance(
    *,
    accepted_upstream_contract_subject: Mapping[str, object],
    accepted_schema_subject: Mapping[str, object],
    trusted_w1_w2_content_addressed_authority_resolver: ContentAddressedAuthorityResolver,
    independently_supplied_authority_root: str,
    opaque_external_record_ids: Mapping[str, object],
    current_exact_reference_snapshot: Mapping[str, Mapping[str, object]],
    raw_candidate_pack_bytes: bytes,
    evaluation_time: datetime,
    trusted_upstream_contract_bytes: bytes | None = None,
    trusted_schema_bytes: bytes | None = None,
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
        _CONTRACT_PATH,
        accepted_upstream_contract_subject,
        "upstream contract",
        trusted_upstream_contract_bytes,
    )
    _accepted_repository_artifact(_PACK_SCHEMA_PATH, accepted_schema_subject, "pack schema", trusted_schema_bytes)
    contract = yaml.safe_load(contract_bytes.decode("utf-8"))
    required = _require_key(contract, "required_pack_contract", "upstream contract")

    pack = _parse_candidate(raw_candidate_pack_bytes, trusted_schema_bytes)

    # The candidate's own claims about the contract and schema must equal the independently
    # accepted subjects. A coordinated edit of both sides still fails, because neither side
    # of this comparison is derived from the candidate.
    _require_matching_subject(
        pack["upstream_contract_reference"], accepted_upstream_contract_subject, "upstream contract reference"
    )
    _require_matching_subject(pack["schema_reference"], accepted_schema_subject, "pack schema reference")
    _require_source_authority_projection(contract, pack)

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
    _require_accepted_requirement(resolved, pack, evaluation_time)

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
    _require_subject_bound_lifecycle(resolved, subject, opaque_external_record_ids, pack, evaluation_time)
    return subject


def validate_tdl_private_pack_for_preparation(
    *,
    accepted_upstream_contract_subject: Mapping[str, object],
    accepted_schema_subject: Mapping[str, object],
    trusted_w1_w2_content_addressed_authority_resolver: ContentAddressedAuthorityResolver,
    independently_supplied_authority_root: str,
    opaque_external_record_ids: Mapping[str, object],
    current_exact_reference_snapshot: Mapping[str, Mapping[str, object]],
    raw_candidate_pack_bytes: bytes,
    evaluation_time: datetime,
    trusted_upstream_contract_bytes: bytes | None = None,
    trusted_schema_bytes: bytes | None = None,
) -> PackAcceptanceSubject:
    """Validate the candidate subject before future pack review or owner records exist.

    Preparation deliberately shares the accepted candidate/schema/reference and
    requirement/registered-object checks with the consumption loader, but its
    required record map is supplied by the caller and must omit the future
    ``independent_pack_review`` and ``stephen_owner_acceptance`` records.  This
    is the only loader entry point that may persist a preparation evidence file;
    it never treats a candidate as accepted.
    """
    if evaluation_time.tzinfo is None or evaluation_time.utcoffset() is None:
        raise PackUnconsumable("evaluation_time must carry a timezone")

    contract_bytes = _accepted_repository_artifact(
        _CONTRACT_PATH,
        accepted_upstream_contract_subject,
        "upstream contract",
        trusted_upstream_contract_bytes,
    )
    _accepted_repository_artifact(_PACK_SCHEMA_PATH, accepted_schema_subject, "pack schema", trusted_schema_bytes)
    try:
        contract = yaml.safe_load(contract_bytes.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise PackUnconsumable("accepted upstream contract is not valid YAML") from exc
    required = _require_key(contract, "required_pack_contract", "upstream contract")
    pack = _parse_candidate(raw_candidate_pack_bytes, trusted_schema_bytes)
    _require_matching_subject(
        pack["upstream_contract_reference"], accepted_upstream_contract_subject, "upstream contract reference"
    )
    _require_matching_subject(pack["schema_reference"], accepted_schema_subject, "pack schema reference")
    _require_source_authority_projection(contract, pack)
    _revalidate_references(pack, current_exact_reference_snapshot)
    evidence = _require_key(required, "external_acceptance_evidence", "upstream contract")
    required_record_types = _require_key(evidence, "required_record_types", "external acceptance evidence")
    future = {"independent_pack_review", "stephen_owner_acceptance"}
    if future.intersection(opaque_external_record_ids):
        raise PackUnconsumable("prepare cannot resolve future pack review and owner acceptance records")
    pre_required = [record_class for record_class in required_record_types if record_class not in future]
    resolved = _resolve_records(
        pre_required,
        opaque_external_record_ids,
        trusted_w1_w2_content_addressed_authority_resolver,
        independently_supplied_authority_root,
    )
    _require_registered_object(_require_key(resolved, "registered_pack_object", "resolved external records"), pack)
    _require_accepted_requirement(resolved, pack, evaluation_time)
    currency = pack["currency"]
    authored_at = _parse_timestamp(currency["authored_at"], "authored_at")
    effective_at = _parse_timestamp(currency["effective_at"], "effective_at")
    expires_at = _parse_timestamp(currency["expires_at"], "expires_at")
    if not authored_at <= effective_at < expires_at:
        raise PackUnconsumable("candidate currency time order is invalid")
    if not effective_at <= evaluation_time < expires_at:
        raise PackUnconsumable("candidate is not current at the evaluation time")
    return PackAcceptanceSubject(
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
