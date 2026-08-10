"""Bounded two-phase production runner for the ``TDL_private`` assurance pack.

The runner is intentionally a read-side coordinator.  It binds a verified
control store, resolves accepted repository objects from Git, validates the
accepted requirement through the real replay-backed policy, and records only
its own immutable run evidence.  It never writes assurance records, grants, or
party identities.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from research_system.assurance.external_records import ExternalRecordResolution
from research_system.assurance.models import AssuranceRequirement, LaneRequirement
from research_system.assurance.pack_loader import (
    PackAcceptanceSubject,
    PackUnconsumable,
    validate_tdl_private_pack_for_acceptance,
    validate_tdl_private_pack_for_preparation,
)
from research_system.assurance.requirements import LedgerBackedAuthorityPolicy, validate_requirement
from research_system.assurance.resolver import ControlStoreAuthorityResolver
from research_system.assurance.tdl_private_semantics import validate_tdl_private_semantics
from research_system.authority import GrantedPolicyActionIdentity, LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.errors import ArsError, IntegrityError
from research_system.routing.independence import RelationshipEvidence, independence_grade
from research_system.schema_registry import runtime_schema_registry
from research_system.store.durability import fsync_directory


__all__ = [
    "AssurancePackConsumptionResult",
    "AssurancePackRunResult",
    "AssurancePackRunnerConfig",
    "GitCurrentReferenceResolver",
    "SemanticRecordLocator",
    "accept_assurance_pack",
    "load_assurance_pack",
    "prepare_assurance_pack",
]


PACK_PATH = ".research-system/packs/tdl-private-assurance.yaml"
PACK_SCHEMA_PATH = ".research-system/schemas/assurance/assurance-pack.schema.json"
CONTRACT_PATH = ".research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml"
FACTS_SCHEMA_PATH = ".research-system/schemas/wp6-3-authority/relationship-evidence-facts.schema.json"
FACTS_ROOT = "relationship-evidence-facts"
_RUN_ROOT = "assurance-pack-runs"
_RUN_ID = re.compile(r"^run_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FACT_ID = re.compile(r"^rel_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_REVISION_FILE = re.compile(r"^(?P<revision>[0-9]{8})-(?P<sha>[0-9a-f]{64})\.json$")
_INDEPENDENCE_ORDER = {"I0": 0, "I1": 1, "I2": 2, "I3": 3}
_FUTURE_PREPARE_KEYS = frozenset(
    {
        "independent_pack_review",
        "pack_review_relationship",
        "relationship_evidence_facts:pack_review",
        "stephen_owner_acceptance",
    }
)
_STANDARD_LOCATOR_CLASSES = {
    "accepted_assurance_requirement": "accepted_assurance_requirement",
    "contract_schema_authorship": "contract_schema_authorship",
    "independent_contract_review": "independent_contract_review",
    "independent_schema_review": "independent_schema_review",
    "stephen_contract_schema_acceptance": "stephen_contract_schema_acceptance",
    "active_authority_grant": "active_authority_grant",
    "registered_pack_object": "registered_pack_object",
    "independent_pack_review": "independent_pack_review",
    "stephen_owner_acceptance": "stephen_owner_acceptance",
    "obligation_applicability_confirmation": "obligation_applicability_confirmation",
}
_RELATIONSHIP_LOCATOR_KEYS = {
    "contract_review_relationship": "producer_relationship_evidence:contract_review",
    "schema_review_relationship": "producer_relationship_evidence:schema_review",
    "requirement_scope_relationship": "producer_relationship_evidence:requirement_scope",
    "pack_review_relationship": "producer_relationship_evidence:pack_review",
}


@dataclass(frozen=True)
class SemanticRecordLocator:
    """An opaque semantic record address; it carries no body or hash oracle."""

    record_class: str
    record_id: str


@dataclass(frozen=True)
class AssurancePackRunnerConfig:
    """Bound configuration for one runner invocation."""

    binding: ControlBinding
    repository_root: Path
    authority_root: str | None = None

    @classmethod
    def load(cls, path: Path, *, repository_root: Path | None = None) -> "AssurancePackRunnerConfig":
        """Load a validated control binding and bind it to a repository root."""

        binding = ControlBinding.load(path)
        root = (repository_root or Path(__file__).resolve().parents[2]).resolve(strict=True)
        return cls(binding=binding, repository_root=root, authority_root=binding.store_identity)

    def resolved_authority_root(self) -> str:
        return self.authority_root or self.binding.store_identity


@dataclass(frozen=True)
class AssurancePackRunResult:
    run_id: str
    phase: str
    state: str
    evidence_path: Path
    preparation_identity: str
    subject: PackAcceptanceSubject


@dataclass(frozen=True)
class AssurancePackConsumptionResult:
    """Exact accepted pack returned after current point-of-use revalidation."""

    run_id: str
    phase: str
    state: str
    evidence_path: Path
    acceptance_identity: str
    subject: PackAcceptanceSubject
    pack: Mapping[str, object]
    raw_pack_bytes: bytes


@dataclass(frozen=True)
class _GitCandidate:
    commit: str
    tree: str
    repository_path: str
    blob: str
    raw_sha256: str
    raw: bytes


@dataclass(frozen=True)
class _FactsResolution:
    record_id: str
    revision: int
    canonical_sha256: str
    record: Mapping[str, object]


@dataclass(frozen=True)
class _AuthorityEvidence:
    receipt: Mapping[str, object]
    policy_action: Mapping[str, object]


def _fail(message: str, exc: BaseException | None = None) -> PackUnconsumable:
    return PackUnconsumable(message) if exc is None else PackUnconsumable(message)


def _utc(value: datetime, label: str = "evaluation_time") -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PackUnconsumable(f"{label} must be a timezone-aware UTC datetime")
    normalized = value.astimezone(UTC)
    if value.utcoffset() != normalized.utcoffset():
        raise PackUnconsumable(f"{label} must be UTC")
    return normalized


def _parse_time(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise PackUnconsumable(f"{label} is not an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PackUnconsumable(f"{label} is not an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PackUnconsumable(f"{label} must carry a timezone")
    return parsed.astimezone(UTC)


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PackUnconsumable(f"{label} is not a mapping")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PackUnconsumable(f"{label} must be a non-empty string")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PackUnconsumable(f"{label} must be a positive integer")
    return value


def _canonical_json_bytes(value: object, label: str) -> bytes:
    try:
        data = canonical_bytes(value)
    except (TypeError, ValueError) as exc:
        raise PackUnconsumable(f"{label} is not canonical JSON") from exc
    return data


class _GitObjectReader:
    """Read exact Git objects without consulting mutable checkout bytes."""

    def __init__(self, repository_root: Path) -> None:
        try:
            self.repository_root = repository_root.resolve(strict=True)
        except OSError as exc:
            raise PackUnconsumable("repository root is unavailable") from exc
        if not self.repository_root.is_dir():
            raise PackUnconsumable("repository root is not a directory")

    def _run(self, *arguments: str) -> bytes:
        try:
            result = subprocess.run(  # nosec B603 - fixed git executable and argv
                ["git", "-C", str(self.repository_root), *arguments],
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            raise PackUnconsumable("Git object resolution is unavailable") from exc
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", "replace").strip()
            raise PackUnconsumable(f"Git object resolution failed: {detail or 'unknown git error'}")
        return result.stdout

    def text(self, *arguments: str) -> str:
        return self._run(*arguments).decode("ascii").strip()

    def head_commit(self) -> str:
        commit = self.text("rev-parse", "HEAD")
        if not _SHA1.fullmatch(commit):
            raise PackUnconsumable("HEAD is not an exact commit object")
        return commit

    def tree(self, commit: str) -> str:
        tree = self.text("rev-parse", f"{commit}^{{tree}}")
        if not _SHA1.fullmatch(tree):
            raise PackUnconsumable("candidate tree is not an exact Git object")
        return tree

    def path(self, path: str | Path) -> str:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.repository_root / candidate
        try:
            relative = candidate.resolve(strict=False).relative_to(self.repository_root)
        except ValueError as exc:
            raise PackUnconsumable("candidate path is outside the bound repository") from exc
        result = relative.as_posix()
        if not result or result == ".git" or result.startswith(".git/"):
            raise PackUnconsumable("candidate path is not a repository artifact")
        return result

    def blob_at(self, revision: str, repository_path: str) -> str:
        blob = self.text("rev-parse", f"{revision}:{repository_path}")
        if not _SHA1.fullmatch(blob):
            raise PackUnconsumable(f"Git path is not a blob: {repository_path}")
        if self.text("cat-file", "-t", blob) != "blob":
            raise PackUnconsumable(f"Git object is not a blob: {repository_path}")
        return blob

    def blob(self, blob: str) -> bytes:
        if not _SHA1.fullmatch(blob):
            raise PackUnconsumable("Git blob identity is not exact")
        if self.text("cat-file", "-t", blob) != "blob":
            raise PackUnconsumable("Git accepted subject does not resolve to a blob")
        data = self._run("cat-file", "blob", blob)
        if _git_blob_id(data) != blob:
            raise PackUnconsumable("Git blob content identity is inconsistent")
        return data

    def candidate(self, path: Path) -> _GitCandidate:
        commit = self.head_commit()
        tree = self.tree(commit)
        repository_path = self.path(path)
        blob = self.blob_at(commit, repository_path)
        raw = self.blob(blob)
        return _GitCandidate(commit, tree, repository_path, blob, sha256_hex(raw), raw)

    def candidate_at(self, commit: str, tree: str, repository_path: str, blob: str, raw_sha256: str) -> _GitCandidate:
        if not _SHA1.fullmatch(commit) or not _SHA1.fullmatch(tree) or not _SHA1.fullmatch(blob):
            raise PackUnconsumable("preparation candidate identity is malformed")
        if self.tree(commit) != tree or self.blob_at(commit, repository_path) != blob:
            raise PackUnconsumable("candidate Git subject no longer resolves exactly")
        raw = self.blob(blob)
        if sha256_hex(raw) != raw_sha256:
            raise PackUnconsumable("candidate raw SHA-256 no longer resolves exactly")
        return _GitCandidate(commit, tree, repository_path, blob, raw_sha256, raw)


def _git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


class GitCurrentReferenceResolver:
    """Trusted read-side resolver for the accepted contract reference rows."""

    def __init__(self, reader: _GitObjectReader) -> None:
        self.reader = reader

    def resolve(self, contract: Mapping[str, object], *, commit: str | None = None) -> dict[str, dict[str, object]]:
        current_commit = commit or self.reader.head_commit()
        required = _mapping(contract.get("required_pack_contract"), "accepted upstream contract required_pack_contract")
        references = _mapping(required.get("references"), "accepted upstream contract references")
        rows = references.get("exact_reference_rows")
        if not isinstance(rows, list) or not rows:
            raise PackUnconsumable("accepted upstream contract has no exact reference rows")
        snapshot: dict[str, dict[str, object]] = {}
        for row_value in rows:
            row = _mapping(row_value, "accepted exact reference row")
            reference_id = _text(row.get("reference_id"), "reference_id")
            if reference_id in snapshot:
                raise PackUnconsumable(f"accepted reference set contains a duplicate: {reference_id}")
            repository_path = _text(row.get("repository_path"), f"reference {reference_id} repository_path")
            blob = self.reader.blob_at(current_commit, repository_path)
            raw = self.reader.blob(blob)
            snapshot[reference_id] = {
                "git_blob": blob,
                "canonical_sha256": sha256_hex(raw),
                "activation_state": row.get("activation_state"),
                "pack_acceptance_eligible": row.get("pack_acceptance_eligible"),
            }
        return snapshot


class _FactsReader:
    def __init__(self, binding: ControlBinding, reader: _GitObjectReader) -> None:
        self.binding = binding
        self.reader = reader

    def _schema(self) -> Mapping[str, object]:
        try:
            blob = self.reader.blob_at(self.reader.head_commit(), FACTS_SCHEMA_PATH)
            raw = self.reader.blob(blob)
        except PackUnconsumable:
            # The additive schema is still a local candidate before this branch
            # is committed.  Production acceptance always takes the Git path.
            path = self.reader.repository_root / FACTS_SCHEMA_PATH
            try:
                raw = path.read_bytes()
            except OSError as exc:
                raise PackUnconsumable("relationship-evidence-facts schema is unavailable") from exc
        try:
            schema = json.loads(raw)
            Draft202012Validator.check_schema(schema)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise PackUnconsumable("relationship-evidence-facts schema is invalid") from exc
        if schema.get("$id") != "ars://wp6-3-authority/relationship-evidence-facts/1.0":
            raise PackUnconsumable("relationship-evidence-facts schema identity is not accepted")
        return schema

    def resolve(self, record_id: str, *, phase: str) -> _FactsResolution:
        if not _FACT_ID.fullmatch(record_id):
            raise PackUnconsumable("relationship-evidence-facts locator is not a relationship identity")
        directory = self.binding.control_root / "runtime" / FACTS_ROOT / record_id
        try:
            paths = sorted(directory.glob("*.json"))
        except OSError as exc:
            raise PackUnconsumable(f"relationship-evidence-facts are unreadable at phase {phase}") from exc
        if not paths:
            raise PackUnconsumable(f"relationship-evidence-facts are missing at phase {phase}")
        history: dict[int, tuple[Path, Mapping[str, object]]] = {}
        for path in paths:
            match = _REVISION_FILE.fullmatch(path.name)
            if match is None:
                raise PackUnconsumable("relationship-evidence-facts revision filename is malformed")
            revision = int(match.group("revision"))
            if revision in history:
                raise PackUnconsumable("relationship-evidence-facts revision is ambiguous")
            try:
                raw = path.read_bytes()
                value = json.loads(raw)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise PackUnconsumable("relationship-evidence-facts bytes are unreadable") from exc
            if _canonical_json_bytes(value, "relationship-evidence-facts") != raw:
                raise PackUnconsumable("relationship-evidence-facts bytes are not canonical")
            if match.group("sha") != sha256_hex(raw):
                raise PackUnconsumable("relationship-evidence-facts filename hash mismatch")
            if not isinstance(value, Mapping):
                raise PackUnconsumable("relationship-evidence-facts body is not an object")
            history[revision] = (path, value)
        latest = max(history)
        if set(history) != set(range(1, latest + 1)):
            raise PackUnconsumable("relationship-evidence-facts revision history is not contiguous")
        record = history[latest][1]
        errors = sorted(
            Draft202012Validator(self._schema(), format_checker=FormatChecker()).iter_errors(record),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            raise PackUnconsumable(f"relationship-evidence-facts schema validation failed: {errors[0].message}")
        if record.get("relationship_evidence_facts_id") != record_id:
            raise PackUnconsumable("relationship-evidence-facts identity does not match its locator")
        return _FactsResolution(record_id, latest, sha256_hex(_canonical_json_bytes(record, "facts")), record)


def _normalise_locators(value: Mapping[str, object]) -> dict[str, SemanticRecordLocator]:
    if not isinstance(value, Mapping):
        raise PackUnconsumable("record_locators must be a mapping of semantic names to opaque locators")
    result: dict[str, SemanticRecordLocator] = {}
    for semantic, locator_value in value.items():
        if not isinstance(semantic, str) or not semantic:
            raise PackUnconsumable("record locator semantic name must be non-empty")
        if not isinstance(locator_value, SemanticRecordLocator):
            raise PackUnconsumable("record locators must contain SemanticRecordLocator values")
        if not locator_value.record_class or not locator_value.record_id:
            raise PackUnconsumable(f"record locator is incomplete: {semantic}")
        expected = _STANDARD_LOCATOR_CLASSES.get(semantic)
        if semantic in _RELATIONSHIP_LOCATOR_KEYS:
            expected = "producer_relationship_evidence"
        elif semantic.startswith("relationship_evidence_facts:"):
            expected = "relationship_evidence_facts"
        elif semantic.startswith("canonical_actor:"):
            expected = "canonical_actor"
        elif expected is None:
            raise PackUnconsumable(f"unknown semantic record locator: {semantic}")
        if locator_value.record_class != expected:
            raise PackUnconsumable(f"semantic record locator class mismatch: {semantic}")
        result[semantic] = locator_value
    return result


def _external_key_for_class(semantic: str) -> str | None:
    if semantic.startswith("canonical_actor:"):
        return semantic
    if semantic in _RELATIONSHIP_LOCATOR_KEYS:
        return _RELATIONSHIP_LOCATOR_KEYS[semantic]
    if semantic.startswith("relationship_evidence_facts:"):
        return None
    return semantic


def _resolve_record(
    resolver: ControlStoreAuthorityResolver,
    locator: SemanticRecordLocator,
    authority_root: str,
    phase: str,
) -> ExternalRecordResolution:
    try:
        result = resolver.resolve_with_receipt(
            record_id=locator.record_id,
            record_class=locator.record_class,
            authority_root=authority_root,
            phase=phase,
        )
    except Exception as exc:  # noqa: BLE001 - runner failure surface is PackUnconsumable
        raise PackUnconsumable(f"record locator did not resolve at phase {phase}: {locator.record_class}") from exc
    if not isinstance(result, ExternalRecordResolution) or not isinstance(result.record, Mapping):
        raise PackUnconsumable("record locator did not return trusted revision metadata")
    return result


def _resolve_phase(
    resolver: ControlStoreAuthorityResolver,
    facts: _FactsReader,
    locators: Mapping[str, SemanticRecordLocator],
    authority_root: str,
    phase: str,
) -> tuple[dict[str, ExternalRecordResolution], dict[str, _FactsResolution]]:
    records: dict[str, ExternalRecordResolution] = {}
    fact_records: dict[str, _FactsResolution] = {}
    for semantic, locator in locators.items():
        key = _external_key_for_class(semantic)
        if key is None:
            fact_records[semantic] = facts.resolve(locator.record_id, phase=phase)
        else:
            records[key] = _resolve_record(resolver, locator, authority_root, phase)
    return records, fact_records


def _record_receipt(resolution: ExternalRecordResolution) -> dict[str, object]:
    return {
        "record_class": resolution.record_class,
        "record_id": resolution.record_id,
        "revision": resolution.revision,
        "canonical_sha256": resolution.canonical_sha256,
    }


def _facts_receipt(resolution: _FactsResolution) -> dict[str, object]:
    return {
        "record_id": resolution.record_id,
        "revision": resolution.revision,
        "canonical_sha256": resolution.canonical_sha256,
    }


def _receipt_map(records: Mapping[str, ExternalRecordResolution]) -> dict[str, dict[str, object]]:
    return {key: _record_receipt(value) for key, value in sorted(records.items())}


def _facts_receipt_map(records: Mapping[str, _FactsResolution]) -> dict[str, dict[str, object]]:
    return {key: _facts_receipt(value) for key, value in sorted(records.items())}


def _parse_yaml_bytes(raw: bytes, label: str) -> Mapping[str, object]:
    try:
        value = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise PackUnconsumable(f"{label} is not valid UTF-8 YAML") from exc
    return _mapping(value, label)


def _candidate_pack(candidate: _GitCandidate) -> Mapping[str, object]:
    """Parse the candidate only after the exact Git blob has been selected."""

    return _parse_yaml_bytes(candidate.raw, "candidate Git blob")


def _subject_from_contract_acceptance(record: Mapping[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    contract = _mapping(record.get("contract_subject"), "contract/schema acceptance contract_subject")
    schema = _mapping(record.get("pack_schema_subject"), "contract/schema acceptance pack_schema_subject")
    contract_blob = contract.get("contract_git_blob", contract.get("git_blob"))
    contract_sha = contract.get("contract_canonical_sha256", contract.get("canonical_sha256"))
    schema_blob = schema.get("schema_git_blob", schema.get("git_blob"))
    schema_sha = schema.get("schema_canonical_sha256", schema.get("canonical_sha256"))
    accepted_contract = {
        "schema_id": "ars://contracts/wp6-3-tdl-private-assurance-pack",
        "schema_version": "1.0.0",
        "repository_path": contract.get("repository_path"),
        "git_blob": contract_blob,
        "canonical_sha256": contract_sha,
    }
    accepted_schema = {
        "schema_id": "ars://assurance/packs/tdl-private/1.0",
        "schema_version": "1.0.0",
        "repository_path": schema.get("repository_path"),
        "git_blob": schema_blob,
        "canonical_sha256": schema_sha,
    }
    if accepted_contract["repository_path"] != CONTRACT_PATH or accepted_schema["repository_path"] != PACK_SCHEMA_PATH:
        raise PackUnconsumable("accepted contract/schema subject path is foreign")
    if not isinstance(contract_blob, str) or not _SHA1.fullmatch(contract_blob):
        raise PackUnconsumable("accepted contract subject blob is invalid")
    if not isinstance(contract_sha, str) or not _SHA256.fullmatch(contract_sha):
        raise PackUnconsumable("accepted contract subject SHA-256 is invalid")
    if not isinstance(schema_blob, str) or not _SHA1.fullmatch(schema_blob):
        raise PackUnconsumable("accepted pack schema subject blob is invalid")
    if not isinstance(schema_sha, str) or not _SHA256.fullmatch(schema_sha):
        raise PackUnconsumable("accepted pack schema subject SHA-256 is invalid")
    return accepted_contract, accepted_schema


def _accepted_git_artifact(reader: _GitObjectReader, subject: Mapping[str, object], label: str) -> bytes:
    blob = _text(subject.get("git_blob"), f"{label} Git blob")
    expected_sha = _text(subject.get("canonical_sha256"), f"{label} SHA-256")
    if not _SHA1.fullmatch(blob) or not _SHA256.fullmatch(expected_sha):
        raise PackUnconsumable(f"{label} identity is malformed")
    raw = reader.blob(blob)
    if b"\r" in raw or not raw.endswith(b"\n") or sha256_hex(raw) != expected_sha:
        raise PackUnconsumable(f"{label} bytes differ from its accepted Git subject")
    return raw


def _pack_subject_dict(subject: PackAcceptanceSubject) -> dict[str, object]:
    return {
        "pack_id": subject.pack_id,
        "assurance_pack_id": subject.assurance_pack_id,
        "assurance_pack_revision": subject.assurance_pack_revision,
        "canonical_repository_path": subject.canonical_repository_path,
        "pack_git_blob": subject.pack_git_blob,
        "pack_raw_sha256": subject.pack_raw_sha256,
        "schema_id": subject.schema_id,
        "schema_version": subject.schema_version,
        "schema_repository_path": subject.schema_repository_path,
        "schema_git_blob": subject.schema_git_blob,
        "schema_canonical_sha256": subject.schema_canonical_sha256,
    }


def _candidate_subject(candidate: _GitCandidate, pack: Mapping[str, object]) -> PackAcceptanceSubject:
    """Build the deterministic candidate subject used for relationship binding."""

    schema = _mapping(pack.get("schema_reference"), "candidate schema reference")
    return PackAcceptanceSubject(
        pack_id=_text(pack.get("pack_id"), "candidate pack_id"),
        assurance_pack_id=_text(pack.get("assurance_pack_id"), "candidate assurance_pack_id"),
        assurance_pack_revision=_integer(pack.get("assurance_pack_revision"), "candidate assurance_pack_revision"),
        canonical_repository_path=_text(pack.get("canonical_repository_path"), "candidate repository path"),
        pack_git_blob=candidate.blob,
        pack_raw_sha256=candidate.raw_sha256,
        schema_id=_text(schema.get("schema_id"), "candidate schema_id"),
        schema_version=_text(schema.get("schema_version"), "candidate schema_version"),
        schema_repository_path=_text(schema.get("repository_path"), "candidate schema repository path"),
        schema_git_blob=_text(schema.get("git_blob"), "candidate schema Git blob"),
        schema_canonical_sha256=_text(schema.get("canonical_sha256"), "candidate schema SHA-256"),
    )


def _adapt_requirement(record: Mapping[str, object]) -> AssuranceRequirement:
    canonical = _mapping(record.get("canonical_requirement"), "accepted canonical requirement")
    rows = record.get("obligation_applicability_rows")
    if not isinstance(rows, list):
        raise PackUnconsumable("accepted requirement applicability rows are missing")
    rows_by_lane: dict[str, list[Mapping[str, object]]] = {}
    for value in rows:
        row = _mapping(value, "accepted requirement applicability row")
        lane = _text(row.get("lane_id"), "applicability lane_id")
        rows_by_lane.setdefault(lane, []).append(row)
    lanes_value = canonical.get("lanes")
    if not isinstance(lanes_value, list):
        raise PackUnconsumable("accepted canonical requirement lanes are missing")
    lanes: list[LaneRequirement] = []
    for lane in lanes_value:
        lane_name = _text(lane, "canonical requirement lane")
        lane_rows = rows_by_lane.get(lane_name, [])
        dispositions = {row.get("applicability") for row in lane_rows}
        if dispositions == {"not_applicable"}:
            disposition = "not_applicable"
        elif dispositions == {"required"}:
            disposition = "required"
        else:
            raise PackUnconsumable(f"accepted requirement lane applicability is incomplete: {lane_name}")
        lanes.append(
            LaneRequirement(
                lane=lane_name,
                disposition=disposition,
                rationale="; ".join(str(row.get("rationale", "")) for row in lane_rows) or "accepted lane",
                governing_ref_hashes=(),
                proof_obligation_ids=tuple(str(row.get("obligation_id")) for row in lane_rows),
                reviewer_capabilities=("independent_review",),
                failure_consequence="blocked_no_cross_lane_compensation",
            )
        )
    acceptance_actor = _text(record.get("acceptor_actor_id"), "accepted requirement acceptor_actor_id")
    producer = _text(record.get("prospective_producer_actor_id"), "accepted requirement producer_actor_id")
    return AssuranceRequirement(
        assurance_requirement_id=_text(canonical.get("assurance_requirement_id"), "assurance_requirement_id"),
        revision=int(canonical.get("revision", 0)),
        content_hash=_text(canonical.get("content_hash"), "assurance requirement content_hash"),
        task_id=_text(canonical.get("task_id"), "assurance requirement task_id"),
        task_revision=int(canonical.get("task_revision", 0)),
        purpose="accepted_assurance_requirement",
        source_position=0,
        owner_actor_id=acceptance_actor,
        author_actor_id=_text(record.get("requirement_author_actor_id"), "requirement_author_actor_id"),
        scope_reviewer_actor_id=_text(record.get("scope_reviewer_actor_id"), "scope_reviewer_actor_id"),
        accepting_actor_id=acceptance_actor,
        prospective_producer_actor_id=producer,
        prospective_producer_profile_id="",
        requested_risk=_text(canonical.get("requested_risk"), "requested_risk"),
        w5_epistemic_risk_floor=_text(canonical.get("w5_epistemic_risk_floor"), "w5_epistemic_risk_floor"),
        action_semantic_risk=_text(canonical.get("action_semantic_risk"), "action_semantic_risk"),
        requirement_relationship_grade=_text(
            canonical.get("requirement_relationship_grade"), "requirement_relationship_grade"
        ),
        lanes=tuple(lanes),
        human_gate_ids=(),
        currency_hash=_text(canonical.get("currency_hash"), "currency_hash"),
    )


def _record(records: Mapping[str, ExternalRecordResolution], key: str) -> Mapping[str, object]:
    resolution = records.get(key)
    if resolution is None:
        raise PackUnconsumable(f"required resolved record is missing: {key}")
    return resolution.record


def _scope_relation(records: Mapping[str, ExternalRecordResolution], key: str) -> ExternalRecordResolution:
    relation = records.get(key)
    if relation is None:
        raise PackUnconsumable(f"required relationship record is missing: {key}")
    return relation


def _validate_required_locator_set(
    contract: Mapping[str, object],
    locators: Mapping[str, SemanticRecordLocator],
    *,
    phase: Literal["prepare", "acceptance"],
    pack: Mapping[str, object] | None = None,
) -> None:
    required = _mapping(
        _mapping(contract.get("required_pack_contract"), "contract").get("external_acceptance_evidence"),
        "external acceptance evidence",
    )
    classes = required.get("required_record_types")
    if not isinstance(classes, list):
        raise PackUnconsumable("contract required_record_types is not a list")
    for record_class in classes:
        if record_class == "canonical_actor":
            if not any(key.startswith("canonical_actor:") for key in locators):
                raise PackUnconsumable("canonical actor semantic locators are required")
            continue
        if record_class == "producer_relationship_evidence":
            for key in (
                "contract_review_relationship",
                "schema_review_relationship",
                "requirement_scope_relationship",
            ):
                if key not in locators:
                    raise PackUnconsumable(f"semantic locator is required for {key}")
            if phase == "acceptance" and "pack_review_relationship" not in locators:
                raise PackUnconsumable("pack-review relationship locator is required")
            continue
        if record_class in {"independent_pack_review", "stephen_owner_acceptance"} and phase == "prepare":
            continue
        if record_class not in locators:
            raise PackUnconsumable(f"semantic locator is required for {record_class}")
    if phase == "acceptance":
        for key in _FUTURE_PREPARE_KEYS:
            if key not in locators:
                raise PackUnconsumable(f"semantic locator is required for {key}")
    conditional = required.get("conditionally_required_record_types", [])
    if isinstance(conditional, list) and pack is not None:
        requirement = _mapping(pack.get("assurance_requirement_reference"), "pack requirement reference")
        _ = requirement


def _validate_subject_records(
    records: Mapping[str, ExternalRecordResolution],
    contract_subject: Mapping[str, object],
    schema_subject: Mapping[str, object],
) -> None:
    for key in (
        "contract_schema_authorship",
        "independent_contract_review",
        "independent_schema_review",
        "stephen_contract_schema_acceptance",
    ):
        body = _record(records, key)
        body_contract = _mapping(body.get("contract_subject"), f"{key} contract_subject")
        body_schema = _mapping(body.get("pack_schema_subject"), f"{key} pack_schema_subject")
        for subject, expected in ((body_contract, contract_subject), (body_schema, schema_subject)):
            if subject != dict(expected):
                raise PackUnconsumable(f"{key} binds a foreign accepted contract/schema subject")


def _validate_actor_joins(
    records: Mapping[str, ExternalRecordResolution],
    locators: Mapping[str, SemanticRecordLocator],
    pack: Mapping[str, object],
) -> dict[str, str]:
    requirement = _record(records, "accepted_assurance_requirement")
    contract_authorship = _record(records, "contract_schema_authorship")
    contract_review = _record(records, "independent_contract_review")
    schema_review = _record(records, "independent_schema_review")
    contract_acceptance = _record(records, "stephen_contract_schema_acceptance")
    roles = {
        "contract_author": _text(contract_authorship.get("author_actor_id"), "contract author"),
        "future_pack_producer": _text(pack.get("producer_actor_id"), "pack producer"),
        "contract_reviewer": _text(contract_review.get("reviewer_actor_id"), "contract reviewer"),
        "schema_reviewer": _text(schema_review.get("reviewer_actor_id"), "schema reviewer"),
        "requirement_author": _text(requirement.get("requirement_author_actor_id"), "requirement author"),
        "requirement_scope_reviewer": _text(requirement.get("scope_reviewer_actor_id"), "scope reviewer"),
        "requirement_acceptor": _text(requirement.get("acceptor_actor_id"), "requirement acceptor"),
        "contract_acceptor": _text(contract_acceptance.get("acceptor_actor_id"), "contract acceptor"),
    }
    if "independent_pack_review" in records:
        review = _record(records, "independent_pack_review")
        roles["pack_scientific_reviewer"] = _text(review.get("reviewer_actor_id"), "pack reviewer")
    if "stephen_owner_acceptance" in records:
        roles["owner_acceptor"] = _text(
            _record(records, "stephen_owner_acceptance").get("acceptor_actor_id"), "owner acceptor"
        )
    for left, right in (
        ("contract_author", "future_pack_producer"),
        ("contract_author", "contract_reviewer"),
        ("contract_author", "schema_reviewer"),
        ("requirement_author", "future_pack_producer"),
        ("requirement_scope_reviewer", "future_pack_producer"),
        ("requirement_acceptor", "future_pack_producer"),
    ):
        if roles[left] == roles[right]:
            raise PackUnconsumable(f"required distinct actor pair is self-attested: {left}/{right}")
    if "owner_acceptor" in roles:
        for left, right in (
            ("contract_reviewer", "owner_acceptor"),
            ("schema_reviewer", "owner_acceptor"),
            ("pack_scientific_reviewer", "future_pack_producer"),
            ("owner_acceptor", "future_pack_producer"),
            ("pack_scientific_reviewer", "owner_acceptor"),
        ):
            if roles[left] == roles[right]:
                raise PackUnconsumable(f"required distinct actor pair is self-attested: {left}/{right}")
    actor_ids = set(roles.values())
    observed: dict[str, str] = {}
    for semantic, locator in locators.items():
        if not semantic.startswith("canonical_actor:"):
            continue
        resolution = records.get(semantic)
        if resolution is None:
            continue
        actor_id = resolution.record.get("actor_id")
        if not isinstance(actor_id, str):
            raise PackUnconsumable("canonical actor record has no actor_id")
        if not actor_id.startswith("act_"):
            raise PackUnconsumable("canonical actor record has a malformed actor identity")
        if actor_id != resolution.record_id:
            raise PackUnconsumable("canonical actor locator does not bind its actor identity")
        observed[actor_id] = semantic
    if not actor_ids.issubset(observed):
        missing = sorted(actor_ids.difference(observed))
        raise PackUnconsumable(f"actor identity join lacks canonical actor records: {missing}")
    return roles


def _relationship_grade_at_least(relationship: Mapping[str, object], minimum_grade: object, label: str) -> None:
    observed = relationship.get("grade")
    if observed not in _INDEPENDENCE_ORDER or minimum_grade not in _INDEPENDENCE_ORDER:
        raise PackUnconsumable(f"{label} relationship grade is not recognised")
    if _INDEPENDENCE_ORDER[str(observed)] < _INDEPENDENCE_ORDER[str(minimum_grade)]:
        raise PackUnconsumable(f"{label} relationship does not meet the declared independence floor")


def _validate_contract_schema_review_relationships(
    records: Mapping[str, ExternalRecordResolution],
    evaluation_time: datetime,
) -> None:
    for review_key, relationship_key, expected_context, label in (
        (
            "independent_contract_review",
            "producer_relationship_evidence:contract_review",
            "contract_review",
            "contract review",
        ),
        (
            "independent_schema_review",
            "producer_relationship_evidence:schema_review",
            "schema_review",
            "schema review",
        ),
    ):
        review = _record(records, review_key)
        relationship_resolution = _scope_relation(records, relationship_key)
        relationship = relationship_resolution.record
        reviewed_at = _parse_time(review.get("reviewed_at"), f"{label} reviewed_at")
        effective_at = _parse_time(relationship.get("effective_at"), f"{label} relationship effective_at")
        expires_at = _parse_time(relationship.get("expires_at"), f"{label} relationship expires_at")
        if (
            relationship_resolution.record_id != review.get("relationship_record_id")
            or relationship.get("relationship_record_id") != review.get("relationship_record_id")
            or relationship.get("relationship_context") != expected_context
            or relationship.get("subject_actor_id") != review.get("reviewer_actor_id")
            or relationship.get("object_actor_id") != review.get("author_actor_id")
        ):
            raise PackUnconsumable(f"{label} relationship is not semantically bound")
        _relationship_grade_at_least(relationship, review.get("minimum_independence_grade"), label)
        if not effective_at <= reviewed_at <= evaluation_time < expires_at:
            raise PackUnconsumable(f"{label} relationship is outside its review or evaluation window")


def _validate_relationship_facts(
    records: Mapping[str, ExternalRecordResolution],
    fact_records: Mapping[str, _FactsResolution],
    pack: Mapping[str, object],
    subject: PackAcceptanceSubject,
    evaluation_time: datetime,
) -> None:
    requirement = _record(records, "accepted_assurance_requirement")
    scope_resolution = _scope_relation(records, "producer_relationship_evidence:requirement_scope")
    scope = scope_resolution.record
    if (
        scope.get("relationship_record_id") != requirement.get("scope_relationship_record_id")
        or scope.get("relationship_context") != "requirement_scope_review"
        or scope.get("subject_actor_id") != requirement.get("scope_reviewer_actor_id")
        or scope.get("object_actor_id") != pack.get("producer_actor_id")
    ):
        raise PackUnconsumable("requirement-scope relationship is not semantically bound")
    if "relationship_evidence_facts:requirement_scope" not in fact_records:
        raise PackUnconsumable("requirement-scope relationship facts are required")
    requirement_subject = {
        "subject_kind": "assurance_requirement",
        "subject_id": requirement.get("assurance_requirement_id"),
        "subject_revision": requirement.get("revision"),
        "subject_sha256": records["accepted_assurance_requirement"].canonical_sha256,
    }
    _check_fact(
        fact_records["relationship_evidence_facts:requirement_scope"],
        scope_resolution,
        relationship_scope="requirement_scope",
        expected_subject=requirement_subject,
        expected_reviewer=str(requirement.get("scope_reviewer_actor_id")),
        expected_producer=str(pack.get("producer_actor_id")),
        evaluation_time=evaluation_time,
    )
    if "producer_relationship_evidence:pack_review" not in records:
        return
    if "independent_pack_review" not in records:
        raise PackUnconsumable("pack-review relationship exists without independent pack review")
    review = _record(records, "independent_pack_review")
    review_resolution = _scope_relation(records, "producer_relationship_evidence:pack_review")
    review_relationship = review_resolution.record
    if (
        review_resolution.record_id == scope_resolution.record_id
        or review_relationship.get("relationship_context") != "pack_scientific_review"
        or review_relationship.get("relationship_record_id") != review.get("relationship_record_id")
        or review_relationship.get("subject_actor_id") != review.get("reviewer_actor_id")
        or review_relationship.get("object_actor_id") != pack.get("producer_actor_id")
    ):
        raise PackUnconsumable("pack-review relationship is not a separate semantic relationship")
    review_effective_at = _parse_time(review_relationship.get("effective_at"), "pack-review relationship effective_at")
    review_expires_at = _parse_time(review_relationship.get("expires_at"), "pack-review relationship expires_at")
    review_time = _parse_time(review.get("reviewed_at"), "independent pack review reviewed_at")
    if not review_effective_at <= review_time < review_expires_at:
        raise PackUnconsumable("pack-review relationship facts are outside the relationship validity window")
    if not review_effective_at <= evaluation_time < review_expires_at:
        raise PackUnconsumable("pack-review relationship is not current at the evaluation time")
    if "relationship_evidence_facts:pack_review" not in fact_records:
        raise PackUnconsumable("pack-review relationship facts are required")
    pack_review_facts = fact_records["relationship_evidence_facts:pack_review"]
    _check_fact(
        pack_review_facts,
        review_resolution,
        relationship_scope="pack_review",
        expected_subject={
            "subject_kind": "assurance_pack",
            "subject_id": subject.assurance_pack_id,
            "subject_revision": subject.assurance_pack_revision,
            "subject_sha256": subject.pack_raw_sha256,
        },
        expected_reviewer=str(review.get("reviewer_actor_id")),
        expected_producer=str(pack.get("producer_actor_id")),
        evaluation_time=evaluation_time,
    )


def _check_pack_review_fact_provenance(
    facts: _FactsResolution,
    requirement_facts: _FactsResolution,
    provenance: Mapping[str, object],
) -> None:
    record = facts.record
    producer = _mapping(record.get("producer"), "pack-review relationship-evidence-facts producer")
    reviewer = _mapping(record.get("reviewer"), "pack-review relationship-evidence-facts reviewer")
    requirement_producer = _mapping(
        requirement_facts.record.get("producer"),
        "requirement-scope relationship-evidence-facts producer",
    )
    if (
        producer.get("task_id") != provenance.get("producer_task_id")
        or producer.get("operator_session_id") != provenance.get("producer_session_id")
        or producer.get("stable_handoff_or_run_id") != requirement_producer.get("stable_handoff_or_run_id")
        or reviewer.get("task_id") != provenance.get("review_task_id")
        or reviewer.get("operator_session_id") != provenance.get("review_session_id")
        or reviewer.get("stable_handoff_or_run_id") != provenance.get("handoff_id")
    ):
        raise PackUnconsumable("pack-review relationship facts do not bind independent review operator provenance")


def _validate_pack_review_fact_operator_provenance(
    records: Mapping[str, ExternalRecordResolution],
    fact_records: Mapping[str, _FactsResolution],
) -> None:
    review = _record(records, "independent_pack_review")
    facts = fact_records.get("relationship_evidence_facts:pack_review")
    if facts is None:
        raise PackUnconsumable("pack-review relationship facts are required")
    requirement_facts = fact_records.get("relationship_evidence_facts:requirement_scope")
    if requirement_facts is None:
        raise PackUnconsumable("requirement-scope relationship facts are required")
    _check_pack_review_fact_provenance(
        facts,
        requirement_facts,
        _mapping(review.get("operator_provenance"), "pack review"),
    )


def _check_fact(
    facts: _FactsResolution,
    relationship: ExternalRecordResolution,
    *,
    relationship_scope: str,
    expected_subject: Mapping[str, object],
    expected_reviewer: str,
    expected_producer: str,
    evaluation_time: datetime,
) -> None:
    record = facts.record
    protected = _mapping(record.get("protected_relationship"), "relationship-evidence-facts protected relationship")
    producer = _mapping(record.get("producer"), "relationship-evidence-facts producer")
    reviewer = _mapping(record.get("reviewer"), "relationship-evidence-facts reviewer")
    if (
        record.get("relationship_scope") != relationship_scope
        or facts.record_id != relationship.record_id
        or record.get("relationship_evidence_facts_id") != relationship.record_id
        or protected.get("relationship_record_id") != relationship.record_id
        or protected.get("revision") != relationship.revision
        or protected.get("canonical_sha256") != relationship.canonical_sha256
        or protected.get("grade") != relationship.record.get("grade")
        or protected.get("relationship_context") != relationship.record.get("relationship_context")
        or protected.get("effective_at") != relationship.record.get("effective_at")
        or protected.get("expires_at") != relationship.record.get("expires_at")
        or record.get("reviewed_subject") != dict(expected_subject)
        or reviewer.get("actor_id") != expected_reviewer
        or producer.get("actor_id") != expected_producer
        or record.get("evidence_author_actor_id") != expected_reviewer
        or expected_reviewer == expected_producer
    ):
        raise PackUnconsumable("relationship-evidence-facts are not bound to the protected relationship/subject")
    reviewed_at = _parse_time(record.get("reviewed_at"), "relationship-evidence-facts reviewed_at")
    if reviewed_at > evaluation_time:
        raise PackUnconsumable("relationship-evidence-facts are from the future")
    effective_at = _parse_time(protected.get("effective_at"), "relationship-evidence-facts effective_at")
    expires_at = _parse_time(protected.get("expires_at"), "relationship-evidence-facts expires_at")
    if not effective_at <= reviewed_at <= evaluation_time < expires_at:
        raise PackUnconsumable("relationship-evidence-facts are outside the protected relationship validity window")
    if producer.get("task_id") == reviewer.get("task_id"):
        raise PackUnconsumable("relationship-evidence-facts review task provenance is not separate")
    evidence = _mapping(record.get("derived_comparisons"), "relationship-evidence-facts derived comparisons")
    expected_comparisons = {
        "same_actor": producer.get("actor_id") == reviewer.get("actor_id"),
        "same_session": producer.get("operator_session_id") == reviewer.get("operator_session_id"),
        "same_context_hash": producer.get("context_hash") == reviewer.get("context_hash"),
        "same_model_family": producer.get("model_family") == reviewer.get("model_family"),
        "producer_conclusions_visible": record.get("producer_conclusions_visibility") == "visible_to_reviewer",
    }
    if evidence != expected_comparisons:
        raise PackUnconsumable("relationship-evidence-facts comparisons are not independently derived")
    try:
        derived = independence_grade(
            RelationshipEvidence(
                **{
                    key: evidence[key]
                    for key in (
                        "same_actor",
                        "same_session",
                        "same_context_hash",
                        "same_model_family",
                        "producer_conclusions_visible",
                    )
                }
            )
        )
    except (KeyError, TypeError) as exc:
        raise PackUnconsumable("relationship-evidence-facts evidence is incomplete") from exc
    if derived != record.get("independence_grade") or derived != relationship.record.get("grade") or derived != "I2":
        raise PackUnconsumable("relationship-evidence-facts independence grade is not independently derived I2")


def _validate_temporal_and_identity(
    records: Mapping[str, ExternalRecordResolution],
    pack: Mapping[str, object],
    subject: PackAcceptanceSubject,
    evaluation_time: datetime,
) -> None:
    requirement = _record(records, "accepted_assurance_requirement")
    scope = _record(records, "producer_relationship_evidence:requirement_scope")
    accepted_at = _parse_time(requirement.get("accepted_at"), "accepted requirement accepted_at")
    effective_at = _parse_time(scope.get("effective_at"), "requirement relationship effective_at")
    expires_at = _parse_time(scope.get("expires_at"), "requirement relationship expires_at")
    authored_at = _parse_time(
        _mapping(pack.get("currency"), "pack currency").get("authored_at"), "candidate authored_at"
    )
    if not effective_at <= accepted_at <= authored_at <= evaluation_time < expires_at:
        raise PackUnconsumable("requirement acceptance, candidate authorship, and relationship times are out of order")
    if "independent_pack_review" in records:
        review = _record(records, "independent_pack_review")
        reviewed_at = _parse_time(review.get("reviewed_at"), "independent pack review reviewed_at")
        if not authored_at < reviewed_at <= evaluation_time:
            raise PackUnconsumable("independent pack review is not after candidate authorship")
    if "stephen_owner_acceptance" in records:
        owner = _record(records, "stephen_owner_acceptance")
        accepted = _parse_time(owner.get("decided_at"), "owner acceptance decided_at")
        if "independent_pack_review" not in records:
            raise PackUnconsumable("owner acceptance has no independent review")
        reviewed_at = _parse_time(_record(records, "independent_pack_review").get("reviewed_at"), "reviewed_at")
        if not reviewed_at < accepted <= evaluation_time:
            raise PackUnconsumable("owner acceptance is not after independent review")
        if owner.get("review_record_id") != _record(records, "independent_pack_review").get("review_record_id"):
            raise PackUnconsumable("owner acceptance does not bind the independent review identity")
        if owner.get("authority_grant_id") != _record(records, "active_authority_grant").get("authority_grant_id"):
            raise PackUnconsumable("owner acceptance authority grant identity is foreign")
        if owner.get("subject") != _pack_subject_dict(subject):
            raise PackUnconsumable("owner acceptance subject differs from the exact Git candidate subject")


def _policy_and_requirement(
    binding: ControlBinding,
    authority_root: str,
    records: Mapping[str, ExternalRecordResolution],
    pack: Mapping[str, object],
    evaluation_time: datetime,
) -> _AuthorityEvidence:
    requirement_record = _record(records, "accepted_assurance_requirement")
    grant_record = _record(records, "active_authority_grant")
    grant_id = _text(grant_record.get("authority_grant_id"), "active authority grant id")
    acceptor = _text(requirement_record.get("acceptor_actor_id"), "accepted requirement acceptor")
    if grant_record.get("actor_id") != acceptor or grant_record.get("subject_assurance_pack_id") != pack.get(
        "assurance_pack_id"
    ):
        raise PackUnconsumable("active authority grant is foreign to the accepted owner/pack")
    try:
        registry = runtime_schema_registry(binding.schema_root)
        identity = registry.resolve_identity(
            "ars://core/policy-action/AcceptR3AssuranceRequirement",
            "1.0.0",
        )
        authority = LedgerAuthorityGrantResolver(
            binding.control_root,
            binding.project_id,
            binding.store_identity,
            registry,
            approved_witness=binding.origin_witness,
            approved_witness_path=binding.origin_witness_path,
        )
        policy = LedgerBackedAuthorityPolicy(
            resolver=authority,
            grant_ids_by_actor={acceptor: grant_id},
            policy_action=GrantedPolicyActionIdentity(
                "accept_r3_assurance_requirement",
                identity.schema_id,
                identity.schema_version,
                identity.sha256,
            ),
            project_id=binding.project_id,
            subject_kind="assurance_requirement",
            subject_id=_text(
                _mapping(requirement_record.get("canonical_requirement"), "canonical requirement").get(
                    "assurance_requirement_id"
                ),
                "requirement id",
            ),
            now=evaluation_time,
        )
        validate_requirement(_adapt_requirement(requirement_record), policy)
        replay_identity = authority.scoped_grant_identity(grant_id)
    except (ArsError, IntegrityError, ValueError, TypeError) as exc:
        raise PackUnconsumable("replay-backed acceptance authority did not resolve") from exc
    if (
        replay_identity.actor_id != acceptor
        or replay_identity.authority_grant_id != grant_id
        or replay_identity.subject_scope.project_id != binding.project_id
        or replay_identity.subject_scope.subject_kind != "assurance_requirement"
        or replay_identity.subject_scope.subject_id
        != _text(
            _mapping(requirement_record.get("canonical_requirement"), "canonical requirement").get(
                "assurance_requirement_id"
            ),
            "requirement id",
        )
        or replay_identity.status != "active"
        or grant_record.get("grant_state") != "active"
        or grant_record.get("revoked") is not False
    ):
        raise PackUnconsumable("replay-backed grant scope or identity is foreign")
    return _AuthorityEvidence(
        receipt={
            "authority_grant_id": replay_identity.authority_grant_id,
            "authority_grant_sha256": replay_identity.authority_grant_sha256,
            "actor_id": replay_identity.actor_id,
            "schema_id": replay_identity.schema_id,
            "schema_version": replay_identity.schema_version,
            "schema_sha256": replay_identity.schema_sha256,
            "activation_event_id": replay_identity.activation_event_id,
            "activation_position": replay_identity.activation_position,
            "administration_decision_id": replay_identity.administration_decision_id,
            "administration_decision_sha256": replay_identity.administration_decision_sha256,
            "status": replay_identity.status,
            "revocation_event_id": replay_identity.revocation_event_id,
            "project_id": binding.project_id,
            "subject_kind": "assurance_requirement",
            "subject_id": replay_identity.subject_scope.subject_id,
            "required_risk": "R3",
        },
        policy_action={
            "policy_action_type": "accept_r3_assurance_requirement",
            "schema_id": identity.schema_id,
            "schema_version": identity.schema_version,
            "schema_sha256": identity.sha256,
            "authority_root": authority_root,
        },
    )


def _phase_evidence_identity(value: Mapping[str, object]) -> str:
    return sha256_hex(_canonical_json_bytes(value, "run evidence"))


def _after_immutable_temp_fsync(_temporary: Path) -> None:
    """Test seam after a complete durable temporary and before publication."""


def _existing_immutable(path: Path, data: bytes) -> bool:
    try:
        existing = path.read_bytes()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise PackUnconsumable("existing run evidence is unreadable") from exc
    if existing != data:
        raise PackUnconsumable("run idempotency identity conflicts with existing evidence")
    return True


def _immutable_write(path: Path, value: Mapping[str, object]) -> None:
    data = _canonical_json_bytes(value, "run evidence")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PackUnconsumable("run evidence could not be persisted") from exc
    if _existing_immutable(path, data):
        return
    temporary = path.parent / f".{path.name}.{secrets.token_hex(16)}.tmp"
    failure: BaseException | None = None
    try:
        try:
            descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            _after_immutable_temp_fsync(temporary)
            if _existing_immutable(path, data):
                return
            try:
                os.link(temporary, path)
            except FileExistsError:
                if not _existing_immutable(path, data):
                    raise PackUnconsumable("run evidence publication could not be reconciled")
            else:
                fsync_directory(path.parent)
                if not _existing_immutable(path, data):
                    raise PackUnconsumable("run evidence publication could not be verified")
        except PackUnconsumable:
            raise
        except OSError as exc:
            raise PackUnconsumable("run evidence could not be persisted") from exc
    except BaseException as exc:
        failure = exc
        raise
    finally:
        try:
            temporary.unlink(missing_ok=True)
            fsync_directory(temporary.parent)
        except OSError as exc:
            if failure is None:
                raise PackUnconsumable("run evidence temporary cleanup failed") from exc


def _read_immutable(path: Path) -> Mapping[str, object]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackUnconsumable("immutable preparation evidence is unreadable") from exc
    if _canonical_json_bytes(value, "immutable preparation evidence") != raw:
        raise PackUnconsumable("immutable preparation evidence is not canonical")
    return _mapping(value, "immutable preparation evidence")


def _run_root(config: AssurancePackRunnerConfig, run_id: str) -> Path:
    if not isinstance(run_id, str) or _RUN_ID.fullmatch(run_id) is None:
        raise PackUnconsumable("run_id must be an evaluation-run identity")
    return config.binding.control_root / "runtime" / _RUN_ROOT / run_id


def _prepare_evidence(
    config: AssurancePackRunnerConfig,
    reader: _GitObjectReader,
    candidate: _GitCandidate,
    subject: PackAcceptanceSubject,
    records: Mapping[str, ExternalRecordResolution],
    facts: Mapping[str, _FactsResolution],
    authority: _AuthorityEvidence,
    references: Mapping[str, Mapping[str, object]],
    evaluation_time: datetime,
    run_id: str,
) -> tuple[dict[str, object], str]:
    evidence: dict[str, object] = {
        "schema_id": "ars://wp6-3-authority/assurance-pack-run-evidence/1.0",
        "schema_version": "1.0.0",
        "run_id": run_id,
        "phase": "prepare",
        "state": "prepared",
        "evaluation_time": evaluation_time.isoformat().replace("+00:00", "Z"),
        "candidate": {
            "commit": candidate.commit,
            "tree": candidate.tree,
            "repository_path": candidate.repository_path,
            "git_blob": candidate.blob,
            "raw_sha256": candidate.raw_sha256,
        },
        "subject": asdict(subject),
        "project_id": config.binding.project_id,
        "store_identity": config.binding.store_identity,
        "authority_root": config.resolved_authority_root(),
        "records": _receipt_map(records),
        "relationship_evidence_facts": _facts_receipt_map(facts),
        "grant_replay_receipt": asdict(authority),
        "reference_snapshot": {key: dict(value) for key, value in sorted(references.items())},
        "prior_preparation_identity": None,
        "retry_idempotency": {
            "run_id": run_id,
            "candidate_blob": candidate.blob,
            "candidate_raw_sha256": candidate.raw_sha256,
        },
    }
    return evidence, _phase_evidence_identity(evidence)


def prepare_assurance_pack(
    *,
    config: AssurancePackRunnerConfig,
    candidate_path: Path,
    evaluation_time: datetime,
    run_id: str,
    record_locators: Mapping[str, object],
) -> AssurancePackRunResult:
    """Prepare and persist an exact candidate subject without future decisions."""

    evaluation_time = _utc(evaluation_time)
    locators = _normalise_locators(record_locators)
    if _FUTURE_PREPARE_KEYS.intersection(locators):
        raise PackUnconsumable("future pack review and owner acceptance records are not used during prepare")
    if not isinstance(config, AssurancePackRunnerConfig) or not isinstance(config.binding, ControlBinding):
        raise PackUnconsumable("prepare requires one verified AssurancePackRunnerConfig")
    reader = _GitObjectReader(config.repository_root)
    candidate = reader.candidate(candidate_path)
    resolver = ControlStoreAuthorityResolver(config.binding)
    facts = _FactsReader(config.binding, reader)
    # The candidate is parsed only after its bytes have come from the exact Git
    # blob, so a working-tree substitution cannot influence this path.
    pack = _candidate_pack(candidate)
    if pack.get("canonical_repository_path") != candidate.repository_path:
        raise PackUnconsumable("candidate path is not the canonical registered pack path")
    records, fact_records = _resolve_phase(resolver, facts, locators, config.resolved_authority_root(), "load")
    contract_subject, schema_subject = _subject_from_contract_acceptance(
        _record(records, "stephen_contract_schema_acceptance")
    )
    contract_bytes = _accepted_git_artifact(reader, contract_subject, "accepted contract")
    schema_bytes = _accepted_git_artifact(reader, schema_subject, "accepted pack schema")
    contract = _parse_yaml_bytes(contract_bytes, "accepted contract")
    _validate_required_locator_set(contract, locators, phase="prepare", pack=pack)
    snapshot = GitCurrentReferenceResolver(reader).resolve(contract, commit=candidate.commit)
    subject = validate_tdl_private_pack_for_preparation(
        accepted_upstream_contract_subject=contract_subject,
        accepted_schema_subject=schema_subject,
        trusted_w1_w2_content_addressed_authority_resolver=resolver,
        independently_supplied_authority_root=config.resolved_authority_root(),
        opaque_external_record_ids=_opaque_ids(locators, contract, phase="prepare"),
        current_exact_reference_snapshot=snapshot,
        raw_candidate_pack_bytes=candidate.raw,
        evaluation_time=evaluation_time,
        trusted_upstream_contract_bytes=contract_bytes,
        trusted_schema_bytes=schema_bytes,
    )
    _validate_subject_records(records, contract_subject, schema_subject)
    _validate_actor_joins(records, locators, pack)
    _validate_contract_schema_review_relationships(records, evaluation_time)
    _validate_relationship_facts(records, fact_records, pack, subject, evaluation_time)
    _validate_temporal_and_identity(records, pack, subject, evaluation_time)
    validate_tdl_private_semantics(
        contract=contract,
        pack=pack,
        records=records,
        subject=subject,
        current_exact_reference_snapshot=snapshot,
        evaluation_time=evaluation_time,
        phase="prepare",
    )
    authority = _policy_and_requirement(
        config.binding, config.resolved_authority_root(), records, pack, evaluation_time
    )
    evidence, preparation_identity = _prepare_evidence(
        config, reader, candidate, subject, records, fact_records, authority, snapshot, evaluation_time, run_id
    )
    evidence["preparation_identity"] = preparation_identity
    wrapper = {"evidence": evidence, "evidence_sha256": _phase_evidence_identity(evidence)}
    path = _run_root(config, run_id) / "preparation.json"
    _immutable_write(path, wrapper)
    return AssurancePackRunResult(run_id, "prepare", "prepared", path, preparation_identity, subject)


def _opaque_ids(
    locators: Mapping[str, SemanticRecordLocator],
    contract: Mapping[str, object],
    *,
    phase: Literal["prepare", "acceptance"],
) -> dict[str, object]:
    required = _mapping(
        _mapping(contract.get("required_pack_contract"), "contract").get("external_acceptance_evidence"), "evidence"
    )
    classes = required.get("required_record_types")
    if not isinstance(classes, list):
        raise PackUnconsumable("contract required record types are not a list")
    result: dict[str, object] = {}
    for record_class in classes:
        if record_class == "canonical_actor":
            actor_locators = {
                semantic.removeprefix("canonical_actor:"): locator.record_id
                for semantic, locator in locators.items()
                if semantic.startswith("canonical_actor:")
            }
            if not actor_locators:
                raise PackUnconsumable("canonical actor locators are required")
            result[record_class] = actor_locators
        elif record_class == "producer_relationship_evidence":
            contract_review = locators.get("contract_review_relationship")
            if contract_review is None:
                raise PackUnconsumable("contract review relationship locator is required")
            schema_review = locators.get("schema_review_relationship")
            if schema_review is None:
                raise PackUnconsumable("schema review relationship locator is required")
            scope = locators.get("requirement_scope_relationship")
            if scope is None:
                raise PackUnconsumable("requirement-scope relationship locator is required")
            relationships: dict[str, str] = {
                "contract_review": contract_review.record_id,
                "schema_review": schema_review.record_id,
                "requirement_scope": scope.record_id,
            }
            pack_review = locators.get("pack_review_relationship")
            if phase == "acceptance":
                if pack_review is None:
                    raise PackUnconsumable("pack-review relationship locator is required")
                relationships["pack_review"] = pack_review.record_id
            result[record_class] = relationships
        else:
            locator = locators.get(record_class)
            if locator is None:
                if phase == "prepare" and record_class in {"independent_pack_review", "stephen_owner_acceptance"}:
                    continue
                raise PackUnconsumable(f"semantic locator is required for {record_class}")
            result[record_class] = locator.record_id
    for optional_class in ("obligation_applicability_confirmation",):
        if optional_class in locators:
            result[optional_class] = locators[optional_class].record_id
    return result


def _load_preparation(path: Path, run_id: str) -> tuple[Mapping[str, object], str]:
    wrapper = _read_immutable(path)
    evidence = _mapping(wrapper.get("evidence"), "preparation evidence")
    if wrapper.get("evidence_sha256") != _phase_evidence_identity(evidence):
        raise PackUnconsumable("preparation evidence identity is corrupt")
    if evidence.get("run_id") != run_id or evidence.get("phase") != "prepare":
        raise PackUnconsumable("preparation evidence is for a different run or phase")
    preparation_identity = _text(evidence.get("preparation_identity"), "preparation identity")
    if preparation_identity != _phase_evidence_identity(
        {key: value for key, value in evidence.items() if key != "preparation_identity"}
    ):
        # The identity is over the immutable evidence before its convenience
        # field is added; this prevents a caller from replacing the identity.
        raise PackUnconsumable("preparation identity is corrupt")
    return evidence, preparation_identity


def _load_acceptance(path: Path, run_id: str) -> tuple[Mapping[str, object], str]:
    wrapper = _read_immutable(path)
    evidence = _mapping(wrapper.get("evidence"), "acceptance evidence")
    if wrapper.get("evidence_sha256") != _phase_evidence_identity(evidence):
        raise PackUnconsumable("acceptance evidence identity is corrupt")
    if evidence.get("run_id") != run_id or evidence.get("phase") != "acceptance":
        raise PackUnconsumable("acceptance evidence is for a different run or phase")
    if evidence.get("state") != "consumption_authorized":
        raise PackUnconsumable("acceptance evidence does not authorize consumption")
    acceptance_identity = _text(evidence.get("evidence_identity"), "acceptance identity")
    if acceptance_identity != _phase_evidence_identity(
        {key: value for key, value in evidence.items() if key != "evidence_identity"}
    ):
        raise PackUnconsumable("acceptance evidence identity is corrupt")
    return evidence, acceptance_identity


def accept_assurance_pack(
    *,
    config: AssurancePackRunnerConfig,
    candidate_path: Path,
    evaluation_time: datetime,
    run_id: str,
    record_locators: Mapping[str, object],
) -> AssurancePackRunResult:
    """Reload preparation, revalidate all authority, and authorize consumption."""

    evaluation_time = _utc(evaluation_time)
    locators = _normalise_locators(record_locators)
    if not isinstance(config, AssurancePackRunnerConfig) or not isinstance(config.binding, ControlBinding):
        raise PackUnconsumable("acceptance requires one verified AssurancePackRunnerConfig")
    preparation_path = _run_root(config, run_id) / "preparation.json"
    preparation, preparation_identity = _load_preparation(preparation_path, run_id)
    candidate_value = _mapping(preparation.get("candidate"), "preparation candidate")
    reader = _GitObjectReader(config.repository_root)
    candidate = reader.candidate_at(
        _text(candidate_value.get("commit"), "preparation commit"),
        _text(candidate_value.get("tree"), "preparation tree"),
        _text(candidate_value.get("repository_path"), "preparation path"),
        _text(candidate_value.get("git_blob"), "preparation blob"),
        _text(candidate_value.get("raw_sha256"), "preparation raw SHA-256"),
    )
    if reader.path(candidate_path) != candidate.repository_path:
        raise PackUnconsumable("acceptance candidate path differs from immutable preparation")
    resolver = ControlStoreAuthorityResolver(config.binding)
    facts = _FactsReader(config.binding, reader)
    # Resolve the contract from the first phase, then require exact equality of
    # every external/reference/facts receipt at the two later phase boundaries.
    phase_records: dict[str, dict[str, ExternalRecordResolution]] = {}
    phase_facts: dict[str, dict[str, _FactsResolution]] = {}
    phase_refs: dict[str, dict[str, dict[str, object]]] = {}
    phase_authority: dict[str, _AuthorityEvidence] = {}
    contract_subject: dict[str, object] | None = None
    schema_subject: dict[str, object] | None = None
    contract_bytes: bytes | None = None
    schema_bytes: bytes | None = None
    contract: Mapping[str, object] | None = None
    pack = _candidate_pack(candidate)
    if pack.get("canonical_repository_path") != candidate.repository_path:
        raise PackUnconsumable("candidate path is not the canonical registered pack path")
    for phase in ("load", "acceptance", "consumption"):
        records, fact_records = _resolve_phase(resolver, facts, locators, config.resolved_authority_root(), phase)
        phase_records[phase] = records
        phase_facts[phase] = fact_records
        observed_contract_subject, observed_schema_subject = _subject_from_contract_acceptance(
            _record(records, "stephen_contract_schema_acceptance")
        )
        observed_contract_bytes = _accepted_git_artifact(reader, observed_contract_subject, "accepted contract")
        observed_schema_bytes = _accepted_git_artifact(reader, observed_schema_subject, "accepted pack schema")
        observed_contract = _parse_yaml_bytes(observed_contract_bytes, "accepted contract")
        if phase == "load":
            _validate_required_locator_set(observed_contract, locators, phase="acceptance", pack=pack)
        observed_refs = GitCurrentReferenceResolver(reader).resolve(observed_contract)
        phase_refs[phase] = observed_refs
        if contract_subject is None:
            contract_subject, schema_subject = observed_contract_subject, observed_schema_subject
            contract_bytes, schema_bytes, contract = observed_contract_bytes, observed_schema_bytes, observed_contract
        elif observed_contract_subject != contract_subject or observed_schema_subject != schema_subject:
            raise PackUnconsumable("accepted contract/schema subject changed between phases")
        phase_authority[phase] = _policy_and_requirement(
            config.binding, config.resolved_authority_root(), records, pack, evaluation_time
        )
        _validate_actor_joins(records, locators, pack)
        _validate_contract_schema_review_relationships(records, evaluation_time)
        _validate_relationship_facts(
            records,
            fact_records,
            pack,
            _candidate_subject(candidate, pack),
            evaluation_time,
        )
    if (
        contract_subject is None
        or schema_subject is None
        or contract_bytes is None
        or schema_bytes is None
        or contract is None
    ):
        raise PackUnconsumable("acceptance did not resolve accepted contract/schema subjects")
    if any(phase_records[phase] != phase_records["load"] for phase in ("acceptance", "consumption")):
        raise PackUnconsumable("external assurance records changed between phases")
    if any(phase_facts[phase] != phase_facts["load"] for phase in ("acceptance", "consumption")):
        raise PackUnconsumable("relationship-evidence-facts changed between phases")
    if any(phase_refs[phase] != phase_refs["load"] for phase in ("acceptance", "consumption")):
        raise PackUnconsumable("current reference snapshot changed between phases")
    loaded_receipts = _receipt_map(phase_records["load"])
    prepared_receipts = _mapping(preparation.get("records"), "preparation record receipts")
    if any(loaded_receipts.get(key) != value for key, value in prepared_receipts.items()):
        raise PackUnconsumable("external assurance records changed since preparation")
    loaded_facts = _facts_receipt_map(phase_facts["load"])
    prepared_facts = _mapping(
        preparation.get("relationship_evidence_facts"), "preparation relationship-evidence-facts receipts"
    )
    if any(loaded_facts.get(key) != value for key, value in prepared_facts.items()):
        raise PackUnconsumable("relationship-evidence-facts changed since preparation")
    if preparation.get("reference_snapshot") != phase_refs["load"]:
        raise PackUnconsumable("current reference snapshot changed since preparation")
    if preparation.get("grant_replay_receipt") != asdict(phase_authority["load"]):
        raise PackUnconsumable("replay-backed grant authority changed since preparation")
    opaque_ids = _opaque_ids(locators, contract, phase="acceptance")
    subject = validate_tdl_private_pack_for_acceptance(
        accepted_upstream_contract_subject=contract_subject,
        accepted_schema_subject=schema_subject,
        trusted_w1_w2_content_addressed_authority_resolver=resolver,
        independently_supplied_authority_root=config.resolved_authority_root(),
        opaque_external_record_ids=opaque_ids,
        current_exact_reference_snapshot=phase_refs["consumption"],
        raw_candidate_pack_bytes=candidate.raw,
        evaluation_time=evaluation_time,
        trusted_upstream_contract_bytes=contract_bytes,
        trusted_schema_bytes=schema_bytes,
    )
    if asdict(subject) != preparation.get("subject"):
        raise PackUnconsumable("acceptance exact subject differs from immutable preparation")
    _validate_subject_records(phase_records["consumption"], contract_subject, schema_subject)
    _validate_temporal_and_identity(phase_records["consumption"], pack, subject, evaluation_time)
    validate_tdl_private_semantics(
        contract=contract,
        pack=pack,
        records=phase_records["consumption"],
        subject=subject,
        current_exact_reference_snapshot=phase_refs["consumption"],
        evaluation_time=evaluation_time,
        phase="acceptance",
    )
    _validate_pack_review_fact_operator_provenance(phase_records["consumption"], phase_facts["consumption"])
    previous = preparation.get("preparation_identity")
    if previous != preparation_identity:
        raise PackUnconsumable("acceptance preparation identity is corrupt")
    evidence: dict[str, object] = {
        "schema_id": "ars://wp6-3-authority/assurance-pack-run-evidence/1.0",
        "schema_version": "1.0.0",
        "run_id": run_id,
        "phase": "acceptance",
        "state": "consumption_authorized",
        "evaluation_time": evaluation_time.isoformat().replace("+00:00", "Z"),
        "candidate": {
            "commit": candidate.commit,
            "tree": candidate.tree,
            "repository_path": candidate.repository_path,
            "git_blob": candidate.blob,
            "raw_sha256": candidate.raw_sha256,
        },
        "subject": asdict(subject),
        "project_id": config.binding.project_id,
        "store_identity": config.binding.store_identity,
        "authority_root": config.resolved_authority_root(),
        "records": _receipt_map(phase_records["consumption"]),
        "relationship_evidence_facts": _facts_receipt_map(phase_facts["consumption"]),
        "grant_replay_receipt": asdict(phase_authority["consumption"]),
        "reference_snapshot": {key: dict(value) for key, value in sorted(phase_refs["consumption"].items())},
        "prior_preparation_identity": preparation_identity,
        "retry_idempotency": {
            "run_id": run_id,
            "preparation_identity": preparation_identity,
            "candidate_blob": candidate.blob,
            "candidate_raw_sha256": candidate.raw_sha256,
        },
        "consumption_authorized_revision": 1,
    }
    evidence_identity = _phase_evidence_identity(evidence)
    evidence["evidence_identity"] = evidence_identity
    path = _run_root(config, run_id) / "acceptance.json"
    _immutable_write(
        path,
        {"evidence": evidence, "evidence_sha256": _phase_evidence_identity(evidence)},
    )
    return AssurancePackRunResult(run_id, "acceptance", "consumption_authorized", path, preparation_identity, subject)


def load_assurance_pack(
    *,
    config: AssurancePackRunnerConfig,
    candidate_path: Path,
    evaluation_time: datetime,
    run_id: str,
    record_locators: Mapping[str, object],
) -> AssurancePackConsumptionResult:
    """Load an accepted pack only after fresh point-of-use authority checks."""

    evaluation_time = _utc(evaluation_time)
    locators = _normalise_locators(record_locators)
    if not isinstance(config, AssurancePackRunnerConfig) or not isinstance(config.binding, ControlBinding):
        raise PackUnconsumable("consumption requires one verified AssurancePackRunnerConfig")
    acceptance, acceptance_identity = _load_acceptance(_run_root(config, run_id) / "acceptance.json", run_id)
    candidate_value = _mapping(acceptance.get("candidate"), "acceptance candidate")
    reader = _GitObjectReader(config.repository_root)
    candidate = reader.candidate_at(
        _text(candidate_value.get("commit"), "acceptance commit"),
        _text(candidate_value.get("tree"), "acceptance tree"),
        _text(candidate_value.get("repository_path"), "acceptance path"),
        _text(candidate_value.get("git_blob"), "acceptance blob"),
        _text(candidate_value.get("raw_sha256"), "acceptance raw SHA-256"),
    )
    if reader.path(candidate_path) != candidate.repository_path:
        raise PackUnconsumable("consumption candidate path differs from immutable acceptance")
    pack = _candidate_pack(candidate)
    if pack.get("canonical_repository_path") != candidate.repository_path:
        raise PackUnconsumable("candidate path is not the canonical registered pack path")

    resolver = ControlStoreAuthorityResolver(config.binding)
    facts_reader = _FactsReader(config.binding, reader)
    records, fact_records = _resolve_phase(
        resolver,
        facts_reader,
        locators,
        config.resolved_authority_root(),
        "consumption",
    )
    contract_subject, schema_subject = _subject_from_contract_acceptance(
        _record(records, "stephen_contract_schema_acceptance")
    )
    contract_bytes = _accepted_git_artifact(reader, contract_subject, "accepted contract")
    schema_bytes = _accepted_git_artifact(reader, schema_subject, "accepted pack schema")
    contract = _parse_yaml_bytes(contract_bytes, "accepted contract")
    _validate_required_locator_set(contract, locators, phase="acceptance", pack=pack)
    references = GitCurrentReferenceResolver(reader).resolve(contract)
    subject = validate_tdl_private_pack_for_acceptance(
        accepted_upstream_contract_subject=contract_subject,
        accepted_schema_subject=schema_subject,
        trusted_w1_w2_content_addressed_authority_resolver=resolver,
        independently_supplied_authority_root=config.resolved_authority_root(),
        opaque_external_record_ids=_opaque_ids(locators, contract, phase="acceptance"),
        current_exact_reference_snapshot=references,
        raw_candidate_pack_bytes=candidate.raw,
        evaluation_time=evaluation_time,
        trusted_upstream_contract_bytes=contract_bytes,
        trusted_schema_bytes=schema_bytes,
    )
    _validate_subject_records(records, contract_subject, schema_subject)
    _validate_actor_joins(records, locators, pack)
    _validate_contract_schema_review_relationships(records, evaluation_time)
    _validate_relationship_facts(records, fact_records, pack, subject, evaluation_time)
    _validate_temporal_and_identity(records, pack, subject, evaluation_time)
    validate_tdl_private_semantics(
        contract=contract,
        pack=pack,
        records=records,
        subject=subject,
        current_exact_reference_snapshot=references,
        evaluation_time=evaluation_time,
        phase="acceptance",
    )
    _validate_pack_review_fact_operator_provenance(records, fact_records)
    authority = _policy_and_requirement(
        config.binding,
        config.resolved_authority_root(),
        records,
        pack,
        evaluation_time,
    )
    if asdict(subject) != acceptance.get("subject"):
        raise PackUnconsumable("consumption exact subject differs from immutable acceptance")
    if _receipt_map(records) != acceptance.get("records"):
        raise PackUnconsumable("external assurance records changed since acceptance")
    if _facts_receipt_map(fact_records) != acceptance.get("relationship_evidence_facts"):
        raise PackUnconsumable("relationship-evidence-facts changed since acceptance")
    if asdict(authority) != acceptance.get("grant_replay_receipt"):
        raise PackUnconsumable("replay-backed grant authority changed since acceptance")
    reference_receipt = {key: dict(value) for key, value in sorted(references.items())}
    if reference_receipt != acceptance.get("reference_snapshot"):
        raise PackUnconsumable("current reference snapshot changed since acceptance")
    if (
        acceptance.get("project_id") != config.binding.project_id
        or acceptance.get("store_identity") != config.binding.store_identity
        or acceptance.get("authority_root") != config.resolved_authority_root()
    ):
        raise PackUnconsumable("acceptance control binding differs from current consumption binding")

    evidence: dict[str, object] = {
        "schema_id": "ars://wp6-3-authority/assurance-pack-run-evidence/1.0",
        "schema_version": "1.0.0",
        "run_id": run_id,
        "phase": "consumption",
        "state": "consumed",
        "evaluation_time": evaluation_time.isoformat().replace("+00:00", "Z"),
        "candidate": dict(candidate_value),
        "subject": asdict(subject),
        "project_id": config.binding.project_id,
        "store_identity": config.binding.store_identity,
        "authority_root": config.resolved_authority_root(),
        "records": _receipt_map(records),
        "relationship_evidence_facts": _facts_receipt_map(fact_records),
        "grant_replay_receipt": asdict(authority),
        "reference_snapshot": reference_receipt,
        "prior_acceptance_identity": acceptance_identity,
        "consumed_pack_sha256": candidate.raw_sha256,
        "retry_idempotency": {
            "run_id": run_id,
            "acceptance_identity": acceptance_identity,
            "candidate_blob": candidate.blob,
            "candidate_raw_sha256": candidate.raw_sha256,
        },
    }
    evidence_identity = _phase_evidence_identity(evidence)
    evidence["evidence_identity"] = evidence_identity
    path = _run_root(config, run_id) / "consumption.json"
    _immutable_write(path, {"evidence": evidence, "evidence_sha256": _phase_evidence_identity(evidence)})
    return AssurancePackConsumptionResult(
        run_id,
        "consumption",
        "consumed",
        path,
        acceptance_identity,
        subject,
        pack,
        candidate.raw,
    )
