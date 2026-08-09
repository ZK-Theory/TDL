"""Exact identity loader for the accepted 06i artefact-authority contract."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_CANDIDATE_ROOT = Path(".research-system/contracts/candidates/06i-artefact-authority-v1")
_CANDIDATE_MANIFEST = _CANDIDATE_ROOT / "identity-manifest.yaml"
_CANONICAL_MANIFEST = Path(".research-system/contracts/artefact-authority-v1/identity-manifest.yaml")
_DIMENSIONS = (
    "availability",
    "regenerability",
    "integrity",
    "structural_validation",
    "scientific_review",
    "use_authority",
)
_CONSUMER_KINDS = (
    "result_evidence",
    "review_evidence",
    "manuscript_evidence",
    "claim_evidence",
    "sensitive_sidecar",
)
_PREDICATE_IDS = {
    "result_evidence": "result-evidence-v1",
    "review_evidence": "review-evidence-v1",
    "manuscript_evidence": "manuscript-evidence-v1",
    "claim_evidence": "claim-evidence-v1",
    "sensitive_sidecar": "sensitive-sidecar-v1",
}
_COMPONENTS = {
    "artefact-authority-interface": (
        _CANDIDATE_ROOT / "artefact-authority-interface.v1.yaml",
        Path(".research-system/contracts/artefact-authority-interface.v1.yaml"),
    ),
    "artefact-consumer-predicates": (
        _CANDIDATE_ROOT / "artefact-consumer-predicates.v1.yaml",
        Path(".research-system/policies/artefact-consumer-predicates.v1.yaml"),
    ),
    "artefact-consumer-predicates-schema": (
        _CANDIDATE_ROOT / "artefact-consumer-predicates.schema.json",
        Path(".research-system/schemas/policy/artefact-consumer-predicates.schema.json"),
    ),
    "governing-review-set-rules": (
        _CANDIDATE_ROOT / "governing-review-set-rules.v1.yaml",
        Path(".research-system/policies/governing-review-set-rules.v1.yaml"),
    ),
}
_HEX40 = frozenset("0123456789abcdef")
_HEX64 = _HEX40


class ContractIdentityError(IntegrityError):
    """Raised when canonical 06i bytes differ from the accepted subject."""


@dataclass(frozen=True)
class AcceptedContractSubject:
    """Independent identity of the accepted 06i manifest bytes."""

    manifest_git_blob: str
    manifest_sha256: str

    def __post_init__(self) -> None:
        if len(self.manifest_git_blob) != 40 or set(self.manifest_git_blob) - _HEX40:
            raise ValueError("accepted manifest git blob must be 40 lowercase hexadecimal characters")
        if len(self.manifest_sha256) != 64 or set(self.manifest_sha256) - _HEX64:
            raise ValueError("accepted manifest SHA-256 must be 64 lowercase hexadecimal characters")


@dataclass(frozen=True)
class GoverningEvidenceResolution:
    """Trusted content identity and body for one governing review reference."""

    reference_id: str
    canonical_sha256: str
    record: Mapping[str, object]


class GoverningEvidenceResolver(Protocol):
    """Resolve governing-review metadata from its independent authority channel."""

    def resolve(
        self,
        reference_id: str,
        *,
        project_id: str,
        evaluation_time: datetime,
    ) -> GoverningEvidenceResolution:
        """Return current exact governing-review evidence."""


@dataclass(frozen=True)
class AcceptedArtefactAuthorityContract:
    """Parsed contract after exact candidate/canonical byte verification."""

    manifest_git_blob: str
    manifest_sha256: str
    interface: Mapping[str, object]
    predicates_by_kind: Mapping[str, Mapping[str, object]]
    predicate_sha256_by_kind: Mapping[str, str]
    review_rules_by_kind: Mapping[str, Mapping[str, object]]
    decision_rules: Mapping[str, Mapping[str, object]]

    def predicate_for(self, consumer_kind: str) -> tuple[Mapping[str, object], str]:
        """Return the accepted predicate and its canonical record identity."""
        try:
            return self.predicates_by_kind[consumer_kind], self.predicate_sha256_by_kind[consumer_kind]
        except KeyError as exc:
            raise ContractIdentityError(f"unknown artefact consumer kind: {consumer_kind}") from exc


def git_blob_id(data: bytes) -> str:
    """Compute the Git blob identity of exact bytes without invoking a checkout filter."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def _read_exact(path: Path, label: str) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ContractIdentityError(f"{label} is unreadable: {path}") from exc
    if b"\r" in data or not data.endswith(b"\n"):
        raise ContractIdentityError(f"{label} is not UTF-8/LF with a terminal LF")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractIdentityError(f"{label} is not UTF-8/LF with a terminal LF") from exc
    return data


def _yaml_mapping(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(data.decode("utf-8"))
    except yaml.YAMLError as exc:
        raise ContractIdentityError(f"{label} is not valid YAML") from exc
    if not isinstance(value, dict):
        raise ContractIdentityError(f"{label} must contain one mapping")
    return value


def _json_mapping(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractIdentityError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ContractIdentityError(f"{label} must contain one mapping")
    return value


def _require_exact_keys(value: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ContractIdentityError(f"{label} fields are not exact")


class ArtefactAuthorityContractLoader:
    """Load only the independently accepted, byte-identical 06i materialization."""

    def __init__(
        self,
        accepted_subject: AcceptedContractSubject,
        *,
        repository_root: Path = _REPOSITORY_ROOT,
    ) -> None:
        self.accepted_subject = accepted_subject
        self.repository_root = repository_root.resolve(strict=False)

    def load(self) -> AcceptedArtefactAuthorityContract:
        """Revalidate the manifest and every component on every authority read."""
        candidate_manifest_bytes = _read_exact(
            self.repository_root / _CANDIDATE_MANIFEST,
            "candidate identity manifest",
        )
        canonical_manifest_bytes = _read_exact(
            self.repository_root / _CANONICAL_MANIFEST,
            "canonical identity manifest",
        )
        if candidate_manifest_bytes != canonical_manifest_bytes:
            raise ContractIdentityError("candidate and canonical identity manifests diverge")
        if (
            git_blob_id(canonical_manifest_bytes) != self.accepted_subject.manifest_git_blob
            or sha256_hex(canonical_manifest_bytes) != self.accepted_subject.manifest_sha256
        ):
            raise ContractIdentityError("identity manifest differs from the independently accepted subject")

        manifest = _yaml_mapping(canonical_manifest_bytes, "identity manifest")
        _require_exact_keys(
            manifest,
            {"schema_id", "schema_version", "candidate_state", "identity_surface", "components"},
            "identity manifest",
        )
        if (
            manifest["schema_id"] != "ars://contracts/artefact-authority-identity-manifest"
            or manifest["schema_version"] != "1.0.0"
            or manifest["candidate_state"] != "proposed"
            or manifest["identity_surface"] != "git_blob_utf8_lf"
        ):
            raise ContractIdentityError("identity manifest constants are invalid")
        rows = manifest.get("components")
        if not isinstance(rows, list) or len(rows) != len(_COMPONENTS):
            raise ContractIdentityError("identity manifest component set is incomplete")

        component_bytes: dict[str, bytes] = {}
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ContractIdentityError("identity manifest component row is invalid")
            _require_exact_keys(
                row,
                {"component_id", "candidate_path", "canonical_path", "git_blob", "canonical_sha256"},
                "identity manifest component",
            )
            component_id = row.get("component_id")
            if not isinstance(component_id, str) or component_id in seen or component_id not in _COMPONENTS:
                raise ContractIdentityError("identity manifest component identity is invalid")
            seen.add(component_id)
            expected_candidate, expected_canonical = _COMPONENTS[component_id]
            if (
                row.get("candidate_path") != expected_candidate.as_posix()
                or row.get("canonical_path") != expected_canonical.as_posix()
            ):
                raise ContractIdentityError(f"component path binding is invalid: {component_id}")
            candidate = _read_exact(self.repository_root / expected_candidate, f"candidate {component_id}")
            canonical = _read_exact(self.repository_root / expected_canonical, f"canonical {component_id}")
            if candidate != canonical:
                raise ContractIdentityError(f"candidate and canonical component diverge: {component_id}")
            if row.get("git_blob") != git_blob_id(canonical) or row.get("canonical_sha256") != sha256_hex(canonical):
                raise ContractIdentityError(f"component identity mismatch: {component_id}")
            component_bytes[component_id] = canonical
        if seen != set(_COMPONENTS):
            raise ContractIdentityError("identity manifest component set is incomplete")

        interface = _yaml_mapping(component_bytes["artefact-authority-interface"], "authority interface")
        policy = _yaml_mapping(component_bytes["artefact-consumer-predicates"], "consumer predicates")
        review_rules = _yaml_mapping(component_bytes["governing-review-set-rules"], "review-set rules")
        policy_schema = _json_mapping(
            component_bytes["artefact-consumer-predicates-schema"],
            "consumer predicate schema",
        )
        try:
            Draft202012Validator.check_schema(policy_schema)
            errors = sorted(
                Draft202012Validator(policy_schema, format_checker=FormatChecker()).iter_errors(policy),
                key=lambda error: list(error.absolute_path),
            )
        except (TypeError, ValueError) as exc:
            raise ContractIdentityError("consumer predicate schema is invalid") from exc
        if errors:
            raise ContractIdentityError(f"consumer predicate registry is invalid: {errors[0].message}")

        predicates = policy.get("predicates")
        if not isinstance(predicates, list):
            raise ContractIdentityError("consumer predicate registry is incomplete")
        predicates_by_kind: dict[str, Mapping[str, object]] = {}
        predicate_hashes: dict[str, str] = {}
        for predicate in predicates:
            if not isinstance(predicate, dict):
                raise ContractIdentityError("consumer predicate row is invalid")
            kind = predicate.get("consumer_kind")
            if not isinstance(kind, str) or kind in predicates_by_kind or kind not in _CONSUMER_KINDS:
                raise ContractIdentityError("consumer predicate kind is invalid")
            if predicate.get("predicate_id") != _PREDICATE_IDS[kind] or predicate.get("predicate_version") != "1.0.0":
                raise ContractIdentityError(f"consumer predicate identity is invalid: {kind}")
            dimensions = predicate.get("dimensions")
            if not isinstance(dimensions, dict) or tuple(dimensions) != _DIMENSIONS:
                raise ContractIdentityError(f"consumer predicate dimensions are incomplete: {kind}")
            consumers = predicate.get("allowed_consumer_ids")
            if not isinstance(consumers, list) or not consumers or len(consumers) != len(set(consumers)):
                raise ContractIdentityError(f"consumer predicate consumer set is invalid: {kind}")
            predicates_by_kind[kind] = predicate
            predicate_hashes[kind] = sha256_hex(canonical_bytes(predicate))
        if tuple(predicates_by_kind) != _CONSUMER_KINDS:
            raise ContractIdentityError("consumer predicate registry kind set is incomplete or reordered")

        rules = review_rules.get("rules")
        decisions = review_rules.get("decision_rules")
        if not isinstance(rules, dict) or tuple(rules) != _CONSUMER_KINDS:
            raise ContractIdentityError("governing review rule set is incomplete or reordered")
        if not isinstance(decisions, dict) or set(decisions) != {"claim_promotion"}:
            raise ContractIdentityError("governing decision rule set is invalid")
        for kind, rule in rules.items():
            if not isinstance(rule, dict):
                raise ContractIdentityError(f"governing review rule is invalid: {kind}")
            _require_exact_keys(
                rule,
                {
                    "minimum_approved_reviews",
                    "minimum_independence_grade",
                    "require_eligible",
                    "prohibit_related_reviewer",
                    "prohibit_producer_reviewer",
                },
                f"governing review rule {kind}",
            )

        inventory = interface.get("consumer_inventory")
        if not isinstance(inventory, list) or [
            row.get("consumer_kind") for row in inventory if isinstance(row, dict)
        ] != list(_CONSUMER_KINDS):
            raise ContractIdentityError("public consumer inventory is incomplete or reordered")

        return AcceptedArtefactAuthorityContract(
            manifest_git_blob=self.accepted_subject.manifest_git_blob,
            manifest_sha256=self.accepted_subject.manifest_sha256,
            interface=interface,
            predicates_by_kind=predicates_by_kind,
            predicate_sha256_by_kind=predicate_hashes,
            review_rules_by_kind=rules,
            decision_rules=decisions,
        )
