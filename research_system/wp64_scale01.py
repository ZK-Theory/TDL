"""Read-only verification mechanics for the TDA-scale v1.0.1 candidate.

The module intentionally has no publication or persistence API.  It validates the
produced-unreviewed package, recomputes every candidate-local content identity, and
can inspect synthetic fixture/no-write evidence while Gate 6 remains pending WP6.6.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator


BASE_COMMIT = "cbe24f86b65c2c49bd58eecf4b6786e8879c4704"
PACKAGE_DIR = Path(".research-system/contracts/wp6-4/tda-scale-v1.0.1")
SCHEMA_DIR = Path(".research-system/schemas/contracts/wp6-4")
PACKAGE_INDEX_PATH = PACKAGE_DIR / "package-index.json"
BLUEPRINT_PATH = PACKAGE_DIR / "scale01-scope-definition-blueprint.json"
PREFLIGHT_PATH = PACKAGE_DIR / "scale01-gate6-preflight.json"
CREATE_SCOPE_SCHEMA_PATH = Path(".research-system/schemas/core/commands/create_scope_definition.schema.json")
W11_MANIFEST_SCHEMA_PATH = Path(".research-system/schemas/contracts/w11/research-dossier-manifest.schema.json")
W11_EXPECTED_SET_SCHEMA_PATH = Path(".research-system/schemas/contracts/w11/dossier-expected-set-content.schema.json")

PENDING_DEPENDENCY_IDS = (
    "foundation",
    "kan68_a7",
    "provider_free_operator_session",
    "wp6_6_expected_set",
    "d_g6_5",
)

_PROTECTED_STATE_SHA_FIELDS = (
    "event_tail_sha256",
    "object_set_sha256",
    "scope_definition_set_sha256",
    "dispatch_set_sha256",
    "result_set_sha256",
    "claim_set_sha256",
)

EXPECTED_SOURCE_DEPENDENCIES = (
    {
        "schema_id": "ars://core/command/CreateScopeDefinition",
        "schema_version": "1.0.0",
        "repository_path": CREATE_SCOPE_SCHEMA_PATH.as_posix(),
        "git_commit": BASE_COMMIT,
        "raw_bytes": 16949,
        "raw_sha256": "0e1e3f8f9242a69559749b491048d7ce3983fada083cdc65475cc8ac9feb2856",
        "git_blob_id": "a8ffbd7c607bbeb523074a2a96d63ab87bf67af1",
    },
    {
        "schema_id": "ars://portfolio/research-dossier-manifest",
        "schema_version": "1.0.0",
        "repository_path": W11_MANIFEST_SCHEMA_PATH.as_posix(),
        "git_commit": BASE_COMMIT,
        "raw_bytes": 8118,
        "raw_sha256": "ebba2bae34833237a5bb1dde06bcb598258b52f325635237378e7b8fdcf7e987",
        "git_blob_id": "5cc93fe457c3f540bc2bea8d19e5c92d9c801675",
    },
    {
        "schema_id": "ars://portfolio/dossier-expected-set-content",
        "schema_version": "1.0.0",
        "repository_path": W11_EXPECTED_SET_SCHEMA_PATH.as_posix(),
        "git_commit": BASE_COMMIT,
        "raw_bytes": 10518,
        "raw_sha256": "543002112c8d9ace692f15d2d0e6a3a3f2747a01e405ced717c94c1b3f3bcc0d",
        "git_blob_id": "caa26760e10f2ff04078940ef63ebe0c84944b95",
    },
)

EXPECTED_PREDECESSOR_MANIFEST = {
    "package_version": "1.0.0",
    "relative_path": (
        "00-Meta/Research Direction Reports/"
        "Evidence-Led TDA Scale and Research Programme for ARS - package manifest - v1.0.0 - 2026-07-16.md"
    ),
    "raw_bytes": 5843,
    "raw_sha256": "e20d173b1787c7adf141d08eadecb320ee534a075ad764e542b9fd495df61cbf",
    "identity_source": "external_vault_read_only",
    "git_blob_id": None,
    "subject_commit": None,
    "subject_tree": None,
}

EXPECTED_REUSED_COMPONENTS = (
    (
        "MASTER-PROGRAMME",
        "00-Meta/Research Direction Reports/"
        "Evidence-Led TDA Scale and Research Programme for ARS - v1.0.0 - 2026-07-16.md",
        28244,
        "277f57f938af78f9dd0f270e97bc94919dc55e15b468246844a778a560d241ea",
    ),
    (
        "BENCHMARK-FIXTURE-MANIFEST",
        "00-Meta/Discovery/ars-scale-benchmark-fixture-manifest-v1.0.0-2026-07-16.md",
        10114,
        "fc05bff665917f88349767213a39a6bf1be2e2238d8d08493a8882fb00275341",
    ),
    (
        "SCALE-01",
        "00-Meta/Discovery/ars-scale-01-stage-telemetry-markov-hoist-brief-v1.0.0-2026-07-16.md",
        15326,
        "bbe18f432f2cdeabb99bec4d6dcf82ba7848222b88d54411815593f7ae0918c3",
    ),
    (
        "SCALE-02",
        "00-Meta/Discovery/ars-scale-02-distribution-preserving-vectorisation-template-v1.0.0-2026-07-16.md",
        5978,
        "0370c414cd34f451b76b28fcd70d0ce0bffb270f94fcfe33800d10dc11b220b9",
    ),
    (
        "SCALE-03",
        "00-Meta/Discovery/ars-scale-03-certified-w2-acceleration-brief-v1.0.0-2026-07-16.md",
        15219,
        "18c9b3b27eb441a20d8375f2d06f4d113da38a900794c4ef01d10c2d1bfa0232",
    ),
    (
        "SCALE-04",
        "00-Meta/Discovery/ars-scale-04-giotto-execution-architecture-brief-v1.0.0-2026-07-16.md",
        13459,
        "1866e771cf744d64bd69f17219473cb309b147042e9d9f47821cc65c7fa48fbf",
    ),
    (
        "SCALE-05",
        "00-Meta/Discovery/ars-scale-05-complex-reduction-template-v1.0.0-2026-07-16.md",
        6941,
        "b9080a30c063d4107ce76236999062015cab626df75b2c7901934864fa99571f",
    ),
    (
        "SPEC-01",
        "00-Meta/Discovery/ars-spec-01-spectral-distance-ph-assay-brief-v1.0.0-2026-07-16.md",
        14660,
        "39ee3e5a44ec9dbe25766e7ecf89b98fbae8eedcace2ae40f9d5a0fb32f43b84",
    ),
    (
        "SPEC-02",
        "00-Meta/Discovery/ars-spec-02-spectral-distance-ph-micro-spike-template-v1.0.0-2026-07-16.md",
        12535,
        "f9316c33844d77c9bde9506decb942354a28441e372a06c7abc2d9ed03d5bec5",
    ),
    (
        "DIR-01",
        "00-Meta/Discovery/ars-dir-01-multiparameter-consolidation-template-v1.0.0-2026-07-16.md",
        2934,
        "1641ee199b4b463b2924cd89729f54a13f0eb67796d12403390baf03d2554f2f",
    ),
    (
        "DIR-02",
        "00-Meta/Discovery/ars-dir-02-regional-mapper-extension-template-v1.0.0-2026-07-16.md",
        3313,
        "a4d3a3615796d6cc5e75cef8c4df93cfd8c7ff8e2adbbdd2b65203fc710380ee",
    ),
    (
        "DIR-03",
        "00-Meta/Discovery/ars-dir-03-zigzag-new-event-template-v1.0.0-2026-07-16.md",
        2869,
        "8bed90be64e2fb9eeba54505d9267c4f5b06a14a9c88721dd0e1e28098684d74",
    ),
    (
        "DIR-04",
        "00-Meta/Discovery/ars-dir-04-directed-persistence-assay-template-v1.0.0-2026-07-16.md",
        3558,
        "46e790a5de1c7b44c3f00c6e644cd118a3ffbc616f99c0cb43f806a26ffd5e82",
    ),
    (
        "DIR-05",
        "00-Meta/Discovery/ars-dir-05-trajectory-pl-sheaf-template-v1.0.0-2026-07-16.md",
        3924,
        "3640180168f9f57a3d09cad17804f3f63cb0fb29e9b2002c7994ee13b39273d8",
    ),
    (
        "DIR-07",
        "00-Meta/Discovery/ars-dir-07-persistent-cup-length-literature-template-v1.0.0-2026-07-16.md",
        3613,
        "9d7288ca27424bf4189f8982d89daafae9fab28a7e3eee6730748e249caa087c",
    ),
    (
        "DIR-08",
        "00-Meta/Discovery/ars-dir-08-diffusion-nonredundancy-template-v1.0.0-2026-07-16.md",
        2870,
        "5d4078e9640c29b93160c2f9694388b437f331a96777f1c885d70b4e934e4526",
    ),
    (
        "DIR-09",
        "00-Meta/Discovery/ars-dir-09-topological-causal-effects-template-v1.0.0-2026-07-16.md",
        3392,
        "a79cb0cb7884e4e9c0b6cc116417b665307ec4c35bc86f0fc823fa2794017583",
    ),
)

EXPECTED_CHANGED_COMPONENT_IDS = {
    "SCALE01-SCOPE-DEFINITION-BLUEPRINT",
    "SCALE01-GATE6-PREFLIGHT",
    "SCALE01-SCOPE-DEFINITION-BLUEPRINT-SCHEMA",
    "SCALE01-FIXTURE-OBSERVATION-SCHEMA",
    "SCALE01-NO-WRITE-EVIDENCE-SCHEMA",
    "SCALE01-GATE6-PREFLIGHT-SCHEMA",
    "TDA-SCALE-PACKAGE-INDEX-SCHEMA",
}

EXPECTED_FIXTURE_TUPLE = (
    {
        "fixture_alias": "F-BHPS-EMBED",
        "geometry_alias": "G-MEDIAN",
        "relative_path": "results/trajectory_tda_bhps/embeddings.npy",
        "raw_sha256": "349fd443529a1212f03e8a1b8b189c02bdce6afffe82ea17c5ca8895e041b3c0",
        "authority_class": "closed_t128_engineering_fixture",
        "confidentiality_class": "registered_or_eul_uk_data",
        "permitted_consumer": "scale01_engineering_preflight_only",
    },
    {
        "fixture_alias": "F-BHPS-TRAJ",
        "geometry_alias": "G-MEDIAN",
        "relative_path": "results/trajectory_tda_bhps/01_trajectories.json",
        "raw_sha256": "a872606a435478515daa8edd91ac58172c173d61c8a8c2e2f12e305dc1b07b47",
        "authority_class": "closed_t128_engineering_fixture",
        "confidentiality_class": "registered_or_eul_uk_data",
        "permitted_consumer": "scale01_engineering_preflight_only",
    },
    {
        "fixture_alias": "G-MEDIAN-CHECKPOINT",
        "geometry_alias": "G-MEDIAN",
        "relative_path": (
            "results/panel_methodology/fdr/subgroup_checkpoints/bhps_nssec_Routine-Manual_B1000_seed42.json"
        ),
        "raw_sha256": "9a0feef58c77d8e5d2b798db2936fc6c14f1f56518177b9d31ee71f2360bd8a7",
        "authority_class": "closed_t128_engineering_fixture",
        "confidentiality_class": "registered_or_eul_uk_data",
        "permitted_consumer": "scale01_engineering_preflight_only",
    },
    {
        "fixture_alias": "F-USOC-EMBED",
        "geometry_alias": "G-SLOW-L5000",
        "relative_path": "results/trajectory_tda_integration/embeddings.npy",
        "raw_sha256": "69b2ba55902565960e8009004d2c21332d3786e2af3e83edc4ac0a2d3a5f5540",
        "authority_class": "closed_t128_engineering_fixture",
        "confidentiality_class": "registered_or_eul_uk_data",
        "permitted_consumer": "scale01_engineering_preflight_only",
    },
    {
        "fixture_alias": "F-USOC-TRAJ",
        "geometry_alias": "G-SLOW-L5000",
        "relative_path": "results/trajectory_tda_integration/01_trajectories.json",
        "raw_sha256": "d356874922685ac7052124b8a7897f6a52e5cde2a124a1ec4816bc30e6748c39",
        "authority_class": "closed_t128_engineering_fixture",
        "confidentiality_class": "registered_or_eul_uk_data",
        "permitted_consumer": "scale01_engineering_preflight_only",
    },
    {
        "fixture_alias": "G-SLOW-L5000-CHECKPOINT",
        "geometry_alias": "G-SLOW-L5000",
        "relative_path": (
            "results/panel_methodology/fdr/subgroup_checkpoints/usoc_nssec_Routine-Manual_B1000_seed42.json"
        ),
        "raw_sha256": "3c4dc1e29f2817b0f8c51a2b1892375053cb82b7f7223940f16797b207f06541",
        "authority_class": "closed_t128_engineering_fixture",
        "confidentiality_class": "registered_or_eul_uk_data",
        "permitted_consumer": "scale01_engineering_preflight_only",
    },
)

EXPECTED_ALIGNMENT_BINDINGS = {
    "G-MEDIAN": ("F-BHPS-EMBED", "F-BHPS-TRAJ", "G-MEDIAN-CHECKPOINT"),
    "G-SLOW-L5000": ("F-USOC-EMBED", "F-USOC-TRAJ", "G-SLOW-L5000-CHECKPOINT"),
}

_FORMAT_CHECKER = Draft202012Validator.FORMAT_CHECKER
_WRITE_BITS = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class Scale01VerificationError(ValueError):
    """Raised when the produced-unreviewed SCALE-01 candidate fails closed."""


def _resolve_git_executable() -> str:
    candidate = shutil.which("git")
    if candidate is None:
        raise Scale01VerificationError("Git executable is not available")
    executable = Path(candidate).resolve(strict=True)
    if not executable.is_absolute() or not executable.is_file():
        raise Scale01VerificationError("Git executable is not an absolute regular file")
    return str(executable)


GIT_EXECUTABLE = _resolve_git_executable()


@dataclass(frozen=True)
class _PathBinding:
    configured_path: str
    physical_path: str
    volume_id: str
    stable_file_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            "configured_path": self.configured_path,
            "physical_path": self.physical_path,
            "volume_id": self.volume_id,
            "stable_file_id": self.stable_file_id,
        }


@dataclass(frozen=True)
class ProtectedStateSnapshot:
    """Immutable binding between protected paths and one observed byte state."""

    fixture_root: _PathBinding
    surface_bindings: tuple[tuple[str, _PathBinding], ...]
    _state_bytes: bytes

    def evidence_state(self) -> dict[str, Any]:
        value = json.loads(self._state_bytes)
        if not isinstance(value, dict):  # pragma: no cover - constructor invariant
            raise Scale01VerificationError("protected snapshot state is not an object")
        return value


def canonical_sha256(value: Any) -> str:
    """Return the SHA-256 of one canonical JSON value."""

    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def derive_fixture_set_sha256(fixtures: Sequence[Mapping[str, Any]]) -> str:
    """Derive the fixture-set identity from full rows, sorted by alias."""

    return canonical_sha256(sorted((dict(row) for row in fixtures), key=lambda row: row["fixture_alias"]))


def derive_fixture_observation_id(observation: Mapping[str, Any]) -> str:
    """Derive the content address of an observation without self-reference."""

    preimage = {key: value for key, value in observation.items() if key != "observation_id"}
    return f"fobs_{canonical_sha256(preimage)}"


def derive_no_write_evidence_id(evidence: Mapping[str, Any]) -> str:
    """Derive the content address of no-write evidence without self-reference."""

    preimage = {key: value for key, value in evidence.items() if key != "evidence_id"}
    return f"nw_{canonical_sha256(preimage)}"


def derive_alignment_hashes(pairs: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """Recompute the three alignment identities from ordered, privacy-safe pairs."""

    ordered = sorted((dict(row) for row in pairs), key=lambda row: row["row_index"])
    return {
        "row_index_set_sha256": canonical_sha256([row["row_index"] for row in ordered]),
        "membership_set_sha256": canonical_sha256(sorted(row["membership_id_sha256"] for row in ordered)),
        "alignment_sha256": canonical_sha256(ordered),
    }


def _derive_alignment_pairs_from_bound_bytes(
    geometry_alias: str,
    bound_fixture_bytes: Mapping[str, bytes],
    index_fixture_alias: str,
) -> list[dict[str, Any]]:
    """Derive alignment pairs from the bound fixture and checkpoint bytes."""

    try:
        index = json.loads(bound_fixture_bytes[index_fixture_alias])
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Scale01VerificationError(f"{geometry_alias} bound fixture/index bytes are not valid JSON") from exc
    if not isinstance(index, dict) or not isinstance(index.get("n"), int) or isinstance(index["n"], bool):
        raise Scale01VerificationError(f"{geometry_alias} bound fixture/index bytes have no integer n")
    if index["n"] < 1:
        raise Scale01VerificationError(f"{geometry_alias} bound fixture/index bytes have an empty n")

    source_digest = canonical_sha256(
        {alias: hashlib.sha256(raw).hexdigest() for alias, raw in sorted(bound_fixture_bytes.items())}
    )
    return [
        {
            "row_index": row_index,
            "membership_id_sha256": hashlib.sha256(
                f"scale01-alignment|{geometry_alias}|{source_digest}|{row_index}".encode("ascii")
            ).hexdigest(),
        }
        for row_index in range(index["n"])
    ]


def path_identity(path: Path) -> dict[str, str]:
    """Observe one existing directory without changing it."""

    configured = path.absolute()
    physical = configured.resolve(strict=True)
    metadata = physical.stat()
    return {
        "configured_path": configured.as_posix(),
        "physical_path": physical.as_posix(),
        "volume_id": str(metadata.st_dev),
        "stable_file_id": f"dev:{metadata.st_dev}:ino:{metadata.st_ino}",
    }


def _read_bound_file(path: Path, label: str) -> tuple[_PathBinding, bytes]:
    configured = path.absolute()
    physical = configured.resolve(strict=True)
    if not physical.is_file():
        raise Scale01VerificationError(f"protected surface is not a regular file: {label}")
    before = physical.stat()
    raw = physical.read_bytes()
    after = physical.stat()
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity or len(raw) != after.st_size:
        raise Scale01VerificationError(f"protected surface changed while observed: {label}")
    return (
        _PathBinding(
            configured_path=configured.as_posix(),
            physical_path=physical.as_posix(),
            volume_id=str(after.st_dev),
            stable_file_id=f"dev:{after.st_dev}:ino:{after.st_ino}",
        ),
        raw,
    )


def snapshot_protected_state(
    fixture_root: Path,
    *,
    protected_surface_paths: Mapping[str, Path],
) -> ProtectedStateSnapshot:
    """Read and bind the legacy tree plus all six protected surface bytes."""

    actual_fields = set(protected_surface_paths)
    expected_fields = set(_PROTECTED_STATE_SHA_FIELDS)
    if actual_fields != expected_fields:
        raise Scale01VerificationError("protected surface path set mismatch")

    _assert_no_reparse_path_chain(fixture_root, "fixture root")
    fixture_identity = path_identity(fixture_root)
    root = Path(fixture_identity["physical_path"])
    if not root.is_dir():
        raise Scale01VerificationError("fixture root is not a directory")
    entries = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative_path = path.relative_to(root).as_posix()
        metadata = path.lstat()
        if stat.S_ISREG(metadata.st_mode):
            raw = path.read_bytes()
            entry = {
                "relative_path": relative_path,
                "entry_type": "file",
                "byte_size": len(raw),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
            }
        elif stat.S_ISDIR(metadata.st_mode):
            entry = {"relative_path": relative_path, "entry_type": "directory", "byte_size": 0, "raw_sha256": None}
        elif stat.S_ISLNK(metadata.st_mode):
            entry = {"relative_path": relative_path, "entry_type": "symlink", "byte_size": 0, "raw_sha256": None}
        else:
            entry = {"relative_path": relative_path, "entry_type": "other", "byte_size": 0, "raw_sha256": None}
        entries.append(entry)
    state = {
        "legacy_entry_count": len(entries),
        "legacy_entry_set_sha256": canonical_sha256(entries),
        "legacy_entries": entries,
    }
    surface_bindings = []
    stable_ids = []
    for field in _PROTECTED_STATE_SHA_FIELDS:
        binding, raw = _read_bound_file(Path(protected_surface_paths[field]), field)
        surface_bindings.append((field, binding))
        stable_ids.append((binding.volume_id, binding.stable_file_id))
        state[field] = hashlib.sha256(raw).hexdigest()
    if len(stable_ids) != len(set(stable_ids)):
        raise Scale01VerificationError("protected surface paths are not distinct")

    state_bytes = json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return ProtectedStateSnapshot(
        fixture_root=_PathBinding(**fixture_identity),
        surface_bindings=tuple(surface_bindings),
        _state_bytes=state_bytes,
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise Scale01VerificationError(f"cannot load JSON artifact {path.as_posix()}: {exc}") from exc
    if not isinstance(value, dict):
        raise Scale01VerificationError(f"JSON artifact must be an object: {path.as_posix()}")
    return value


def _raw_identity(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    # Git's blob identity is specified as SHA-1 over this exact header and byte stream;
    # this is a non-security identity calculation, so mark it usedforsecurity=False.
    git_blob_id = hashlib.sha1(header + raw, usedforsecurity=False).hexdigest()
    return {
        "raw_bytes": len(raw),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_id": git_blob_id,
    }


def _schema_validator(schema: Mapping[str, Any]) -> Draft202012Validator:
    Draft202012Validator.check_schema(schema)
    if "date-time" not in _FORMAT_CHECKER.checkers:
        raise Scale01VerificationError("the active FormatChecker cannot enforce date-time")
    return Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)


def _validate_schema(schema: Mapping[str, Any], value: Any, label: str) -> None:
    errors = sorted(_schema_validator(schema).iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise Scale01VerificationError(f"{label} schema violation at {location}: {first.message}")


def _assert_closed_objects(node: Any, location: str) -> None:
    if isinstance(node, dict):
        node_type = node.get("type")
        if node_type == "object" and node.get("additionalProperties") is not False:
            raise Scale01VerificationError(f"open object schema at {location}")
        for key, value in node.items():
            _assert_closed_objects(value, f"{location}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _assert_closed_objects(value, f"{location}[{index}]")


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise Scale01VerificationError(f"{label} mismatch")


def _git_blob_at(repo_root: Path, commit: str, repository_path: str) -> str:
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise Scale01VerificationError("Git commit identity is not a verified SHA-1")
    if (
        not repository_path
        or "\\" in repository_path
        or repository_path.startswith("/")
        or ":" in repository_path
        or any(part in {"", ".", ".."} for part in PurePosixPath(repository_path).parts)
    ):
        raise Scale01VerificationError("Git repository path is not a canonical relative path")
    result = subprocess.run(
        [GIT_EXECUTABLE, "ls-tree", commit, "--", repository_path],
        cwd=repo_root,
        check=True,
        shell=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    parts = result.stdout.strip().split()
    if len(parts) < 3 or parts[1] != "blob":
        raise Scale01VerificationError(f"Git object is absent at {commit}:{repository_path}")
    return parts[2]


def _expected_reused_rows() -> list[dict[str, Any]]:
    rows = []
    for component_id, relative_path, raw_bytes, raw_sha256 in EXPECTED_REUSED_COMPONENTS:
        rows.append(
            {
                "component_id": component_id,
                "component_version": "1.0.0",
                "relative_path": relative_path,
                "raw_bytes": raw_bytes,
                "raw_sha256": raw_sha256,
                "identity_source": "external_vault_read_only",
                "reuse_in_place": True,
                "changed_path": None,
                "git_blob_id": None,
                "subject_commit": None,
                "subject_tree": None,
            }
        )
    return rows


def _validate_dependency_identities(repo_root: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    _require_equal(list(rows), [dict(row) for row in EXPECTED_SOURCE_DEPENDENCIES], "source dependency tuple")
    for row in rows:
        path = repo_root / str(row["repository_path"])
        _require_equal(
            _raw_identity(path), {key: row[key] for key in ("raw_bytes", "raw_sha256", "git_blob_id")}, str(path)
        )
        _require_equal(
            _git_blob_at(repo_root, str(row["git_commit"]), str(row["repository_path"])),
            row["git_blob_id"],
            f"immutable Git dependency {row['schema_id']}",
        )


def _validate_changed_components(repo_root: Path, package_index: Mapping[str, Any]) -> None:
    rows = package_index["changed_components"]
    _require_equal(package_index["changed_component_count"], len(rows), "changed component count")
    component_ids = {row["component_id"] for row in rows}
    _require_equal(component_ids, EXPECTED_CHANGED_COMPONENT_IDS, "changed component set")
    paths = [row["repository_path"] for row in rows]
    if len(paths) != len(set(paths)):
        raise Scale01VerificationError("changed component paths are not unique")
    for row in rows:
        path = repo_root / row["repository_path"]
        _require_equal(
            _raw_identity(path),
            {key: row[key] for key in ("raw_bytes", "raw_sha256", "git_blob_id")},
            f"changed component {row['component_id']}",
        )


def _validate_scope_payload(repo_root: Path, blueprint: Mapping[str, Any]) -> None:
    own_schema = _read_json(repo_root / SCHEMA_DIR / "scale01-scope-definition-blueprint.schema.json")
    _validate_schema(own_schema, blueprint, "SCALE-01 ScopeDefinition blueprint")

    create_scope_schema = _read_json(repo_root / CREATE_SCOPE_SCHEMA_PATH)
    payload_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": "#/$defs/payload",
        "$defs": deepcopy(create_scope_schema["$defs"]),
    }
    _validate_schema(payload_schema, blueprint, "CreateScopeDefinition payload")

    if blueprint["members"] or blueprint["ordering_rules"]:
        raise Scale01VerificationError("WP6.6 owns the final ScopeDefinition members and ordering")
    required_rules = (
        "foundation exact identity is pending and blocks admission",
        "KAN-68/A7 exact assurance evidence is pending and blocks admission",
        "provider-free operator-session evidence is pending and blocks admission",
        "WP6.6 accepted dossier expected-set is pending and alone owns final cardinality",
        "D-G6-5 owner decision is pending and blocks dispatch",
    )
    _require_equal(tuple(blueprint["dependency_rules"]), required_rules, "ScopeDefinition pending dependency rules")


def _validate_pending_preflight(preflight: Mapping[str, Any]) -> None:
    rows = preflight["dependencies"]
    _require_equal(tuple(row["dependency_id"] for row in rows), PENDING_DEPENDENCY_IDS, "pending dependency order")
    for row in rows:
        expected = {
            "dependency_id": row["dependency_id"],
            "status": "pending",
            "exact_ref": None,
            "raw_sha256": None,
            "git_blob_id": None,
        }
        _require_equal(dict(row), expected, f"pending dependency {row['dependency_id']}")
    _require_equal(
        preflight["cardinality_authority"],
        {
            "authority": "wp6_6_dossier_expected_set",
            "status": "pending",
            "exact_ref": None,
            "object_count": None,
            "scope_count": None,
            "edge_count": None,
            "relationship_count": None,
        },
        "WP6.6 cardinality authority",
    )
    for field in (
        "fixture_observation_ref",
        "no_write_evidence_ref",
        "admission_event_ref",
        "dispatch_ref",
        "result_ref",
        "claim_ref",
        "owner_acceptance_ref",
        "research_claim",
        "pilot_claim",
        "result_claim",
    ):
        if preflight[field] is not None:
            raise Scale01VerificationError(f"{field} must remain null in the pending candidate")


def verify_scale01_documents(
    repo_root: Path,
    package_index: Mapping[str, Any],
    blueprint: Mapping[str, Any],
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify supplied candidate documents against independent repository facts."""

    root = repo_root.resolve(strict=True)
    schemas = {
        path.name: _read_json(path)
        for path in sorted((root / SCHEMA_DIR).glob("*.schema.json"), key=lambda item: item.name)
    }
    expected_schema_names = {
        "scale01-fixture-observation.schema.json",
        "scale01-gate6-preflight.schema.json",
        "scale01-no-write-evidence.schema.json",
        "scale01-scope-definition-blueprint.schema.json",
        "tda-scale-package-index.schema.json",
    }
    _require_equal(set(schemas), expected_schema_names, "WP6.4 schema set")
    for name, schema in schemas.items():
        _assert_closed_objects(schema, name)
        _schema_validator(schema)

    _validate_schema(schemas["tda-scale-package-index.schema.json"], package_index, "TDA-scale package index")
    _validate_schema(schemas["scale01-gate6-preflight.schema.json"], preflight, "SCALE-01 Gate 6 preflight")
    _validate_scope_payload(root, blueprint)

    _require_equal(package_index["predecessor_manifest"], EXPECTED_PREDECESSOR_MANIFEST, "v1.0.0 manifest identity")
    _require_equal(package_index["reused_component_count"], len(EXPECTED_REUSED_COMPONENTS), "reused count")
    _require_equal(package_index["reused_components"], _expected_reused_rows(), "v1.0.0 reuse-in-place tuple")
    _validate_dependency_identities(root, package_index["source_dependencies"])
    _validate_changed_components(root, package_index)

    _require_equal(package_index["candidate_base_git_commit"], BASE_COMMIT, "candidate base")
    _require_equal(package_index["lifecycle_status"], "produced_unreviewed", "package lifecycle")
    _require_equal(package_index["dispatchable"], False, "package dispatchability")
    _require_equal(package_index["execution_authorized"], False, "package execution authority")
    _require_equal(package_index["cardinality_authority"], preflight["cardinality_authority"], "cardinality authority")

    _validate_pending_preflight(preflight)
    _require_equal(preflight["lifecycle_status"], "produced_unreviewed", "preflight lifecycle")
    _require_equal(preflight["admission_status"], "pending_wp6_6", "preflight admission")
    _require_equal(preflight["dispatchable"], False, "preflight dispatchability")
    _require_equal(preflight["execution_authorized"], False, "preflight execution authority")

    blueprint_identity = _raw_identity(root / BLUEPRINT_PATH)
    _require_equal(
        preflight["scope_definition_blueprint"]["repository_path"], BLUEPRINT_PATH.as_posix(), "blueprint path"
    )
    _require_equal(
        {key: preflight["scope_definition_blueprint"][key] for key in blueprint_identity},
        blueprint_identity,
        "preflight blueprint identity",
    )

    return {
        "admission_status": "pending_wp6_6",
        "dispatchable": False,
        "execution_authorized": False,
        "lifecycle_status": "produced_unreviewed",
    }


def verify_static_scale01_candidate(repo_root: Path) -> dict[str, Any]:
    """Load and verify the tracked candidate without consulting mutable state."""

    root = repo_root.resolve(strict=True)
    return verify_scale01_documents(
        root,
        _read_json(root / PACKAGE_INDEX_PATH),
        _read_json(root / BLUEPRINT_PATH),
        _read_json(root / PREFLIGHT_PATH),
    )


def verify_w11_dossier_manifest(repo_root: Path, manifest: Mapping[str, Any]) -> None:
    """Validate W11 manifest bytes without allowing SCALE-01 admission fields."""

    schema = _read_json(repo_root.resolve(strict=True) / W11_MANIFEST_SCHEMA_PATH)
    _validate_schema(schema, manifest, "W11 research dossier manifest")


def _safe_relative_path(value: str, label: str) -> PurePosixPath:
    if value != unicodedata.normalize("NFC", value):
        raise Scale01VerificationError(f"{label} is not Unicode NFC")
    if "\\" in value or value.startswith("/") or ":" in value or "//" in value:
        raise Scale01VerificationError(f"{label} is not a canonical relative path")
    path = PurePosixPath(value)
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise Scale01VerificationError(f"{label} contains traversal or an empty segment")
    return path


def _is_reparse(path: Path) -> bool:
    metadata = path.lstat()
    return stat.S_ISLNK(metadata.st_mode) or bool(getattr(metadata, "st_file_attributes", 0) & _REPARSE_ATTRIBUTE)


def _assert_no_reparse_path_chain(path: Path, label: str) -> Path:
    configured = path.absolute()
    current = Path(configured.anchor)
    for part in configured.parts[1:]:
        current = current / part
        try:
            is_reparse = _is_reparse(current)
        except FileNotFoundError as exc:
            raise Scale01VerificationError(f"{label} is missing: {current}") from exc
        if is_reparse:
            raise Scale01VerificationError(f"{label} contains a symlink or reparse point: {current}")
    return configured


def _assert_no_reparse_chain(root: Path, relative_path: PurePosixPath) -> Path:
    configured_root = _assert_no_reparse_path_chain(root, "fixture root")
    current = configured_root
    for part in relative_path.parts:
        current = current / part
        try:
            is_reparse = _is_reparse(current)
        except FileNotFoundError as exc:
            raise Scale01VerificationError(f"fixture path is missing: {current}") from exc
        if is_reparse:
            raise Scale01VerificationError(f"fixture path contains a symlink or reparse point: {current}")
    return current


def _derive_root_write_capability(path: Path) -> bool:
    """Derive the root's effective directory write capability without mutation."""

    metadata = path.stat()
    if not stat.S_ISDIR(metadata.st_mode):
        raise Scale01VerificationError("fixture root is not a directory")
    return os.access(path, os.W_OK)


def _validate_alias_uniqueness(values: Sequence[str], label: str) -> None:
    if len(values) != len({unicodedata.normalize("NFC", value).casefold() for value in values}):
        raise Scale01VerificationError(f"{label} has a case-fold or Unicode alias collision")


def _fixture_expected_projection() -> list[dict[str, Any]]:
    return sorted((dict(row) for row in EXPECTED_FIXTURE_TUPLE), key=lambda row: row["fixture_alias"])


def verify_fixture_observation(
    repo_root: Path,
    fixture_root: Path,
    observation: Mapping[str, Any],
) -> None:
    """Recompute the read-only fixture observation and its independent closure."""

    root = repo_root.resolve(strict=True)
    schema = _read_json(root / SCHEMA_DIR / "scale01-fixture-observation.schema.json")
    _validate_schema(schema, observation, "SCALE-01 fixture observation")
    if observation["observation_id"] != derive_fixture_observation_id(observation):
        raise Scale01VerificationError("fixture observation content address mismatch")

    _assert_no_reparse_path_chain(fixture_root, "fixture root")
    actual_root_identity = path_identity(fixture_root)
    observed_root = observation["fixture_root"]
    for key, value in actual_root_identity.items():
        _require_equal(observed_root[key], value, f"fixture root {key}")
    actual_root_write_capable = _derive_root_write_capability(fixture_root)
    _require_equal(observed_root["root_write_capable"], actual_root_write_capable, "fixture root write capability")
    if actual_root_write_capable:
        raise Scale01VerificationError("fixture root is write-capable")

    fixtures = list(observation["fixtures"])
    _require_equal(observation["fixture_count"], len(fixtures), "fixture count")
    _require_equal(observation["fixture_set_sha256"], derive_fixture_set_sha256(fixtures), "fixture-set hash")
    aliases = [row["fixture_alias"] for row in fixtures]
    relative_paths = [row["relative_path"] for row in fixtures]
    _validate_alias_uniqueness(aliases, "fixture aliases")
    _validate_alias_uniqueness(relative_paths, "fixture relative paths")
    for row in fixtures:
        _safe_relative_path(row["relative_path"], f"fixture {row['fixture_alias']} path")

    expected_projection = _fixture_expected_projection()
    actual_projection = sorted(
        (
            {
                key: row[key]
                for key in (
                    "fixture_alias",
                    "geometry_alias",
                    "relative_path",
                    "raw_sha256",
                    "authority_class",
                    "confidentiality_class",
                    "permitted_consumer",
                )
            }
            for row in fixtures
        ),
        key=lambda row: row["fixture_alias"],
    )
    _require_equal(actual_projection, expected_projection, "independent fixed fixture tuple")

    for row in fixtures:
        relative = _safe_relative_path(row["relative_path"], f"fixture {row['fixture_alias']} path")
        physical = _assert_no_reparse_chain(fixture_root, relative)
        if not physical.is_file():
            raise Scale01VerificationError(f"fixture is not a regular file: {row['fixture_alias']}")
        metadata = physical.stat()
        raw = physical.read_bytes()
        _require_equal(
            row["physical_path"], physical.resolve(strict=True).as_posix(), f"{row['fixture_alias']} physical path"
        )
        _require_equal(row["volume_id"], str(metadata.st_dev), f"{row['fixture_alias']} volume")
        _require_equal(
            row["stable_file_id"],
            f"dev:{metadata.st_dev}:ino:{metadata.st_ino}",
            f"{row['fixture_alias']} stable identity",
        )
        _require_equal(row["byte_size"], len(raw), f"{row['fixture_alias']} size")
        _require_equal(row["raw_sha256"], hashlib.sha256(raw).hexdigest(), f"{row['fixture_alias']} hash")
        if metadata.st_mode & _WRITE_BITS:
            raise Scale01VerificationError(f"fixture file is write-capable: {row['fixture_alias']}")

    alignments = list(observation["alignments"])
    _require_equal(observation["alignment_count"], len(alignments), "alignment count")
    _require_equal({row["geometry_alias"] for row in alignments}, set(EXPECTED_ALIGNMENT_BINDINGS), "alignment set")
    for row in alignments:
        expected_binding = EXPECTED_ALIGNMENT_BINDINGS[row["geometry_alias"]]
        actual_binding = (
            row["embedding_fixture_alias"],
            row["trajectory_fixture_alias"],
            row["checkpoint_fixture_alias"],
        )
        _require_equal(actual_binding, expected_binding, f"{row['geometry_alias']} fixture binding")
        _safe_relative_path(row["scratch_row_index_relative_path"], "scratch row-index path")
        if not row["scratch_row_index_relative_path"].startswith("scale-01/row-indices/"):
            raise Scale01VerificationError("row-index evidence is not under scale-01 scratch")
        bound_fixture_bytes = {}
        for fixture_alias in expected_binding:
            fixture_row = next(item for item in fixtures if item["fixture_alias"] == fixture_alias)
            bound_fixture_bytes[fixture_alias] = (
                fixture_root / _safe_relative_path(fixture_row["relative_path"], f"fixture {fixture_alias} path")
            ).read_bytes()
        expected_pairs = _derive_alignment_pairs_from_bound_bytes(
            row["geometry_alias"],
            bound_fixture_bytes,
            row["checkpoint_fixture_alias"],
        )
        pairs = list(row["pairs"])
        _require_equal(pairs, expected_pairs, f"{row['geometry_alias']} bound fixture/index pairs")
        row_indices = [pair["row_index"] for pair in pairs]
        memberships = [pair["membership_id_sha256"] for pair in pairs]
        if len(row_indices) != len(set(row_indices)) or len(memberships) != len(set(memberships)):
            raise Scale01VerificationError(f"{row['geometry_alias']} alignment is not one-to-one")
        _require_equal(row["row_count"], len(pairs), f"{row['geometry_alias']} row count")
        _require_equal(row["membership_count"], len(pairs), f"{row['geometry_alias']} membership count")
        _require_equal(row["pair_count"], len(pairs), f"{row['geometry_alias']} pair count")
        derived = derive_alignment_hashes(pairs)
        for key, value in derived.items():
            _require_equal(row[key], value, f"{row['geometry_alias']} {key}")


def _validate_protected_state(state: Mapping[str, Any], label: str) -> None:
    entries = list(state["legacy_entries"])
    _require_equal(state["legacy_entry_count"], len(entries), f"{label} legacy entry count")
    relative_paths = [row["relative_path"] for row in entries]
    _validate_alias_uniqueness(relative_paths, f"{label} legacy paths")
    for relative_path in relative_paths:
        _safe_relative_path(relative_path, f"{label} legacy path")
    ordered = sorted((dict(row) for row in entries), key=lambda row: row["relative_path"])
    _require_equal(state["legacy_entry_set_sha256"], canonical_sha256(ordered), f"{label} legacy entry set")


def _assert_disjoint(first: Path, second: Path) -> None:
    first_resolved = first.resolve(strict=True)
    second_resolved = second.resolve(strict=True)
    if (
        first_resolved == second_resolved
        or first_resolved in second_resolved.parents
        or second_resolved in first_resolved.parents
    ):
        raise Scale01VerificationError("scratch and fixture roots are not disjoint")


def _derive_protected_state_comparison(pre_state: Mapping[str, Any], post_state: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "legacy_entry_sets_equal": pre_state["legacy_entry_set_sha256"] == post_state["legacy_entry_set_sha256"],
        "legacy_bytes_equal": pre_state["legacy_entries"] == post_state["legacy_entries"],
        "event_tail_unchanged": pre_state["event_tail_sha256"] == post_state["event_tail_sha256"],
        "object_set_unchanged": pre_state["object_set_sha256"] == post_state["object_set_sha256"],
        "scope_definition_set_unchanged": pre_state["scope_definition_set_sha256"]
        == post_state["scope_definition_set_sha256"],
        "dispatch_set_unchanged": pre_state["dispatch_set_sha256"] == post_state["dispatch_set_sha256"],
        "result_set_unchanged": pre_state["result_set_sha256"] == post_state["result_set_sha256"],
        "claim_set_unchanged": pre_state["claim_set_sha256"] == post_state["claim_set_sha256"],
    }


def verify_no_write_evidence(
    repo_root: Path,
    fixture_root: Path,
    scratch_root: Path,
    evidence: Mapping[str, Any],
    *,
    pre_snapshot: ProtectedStateSnapshot,
) -> None:
    """Derive post-state from the immutable, byte-backed pre-state binding."""

    root = repo_root.resolve(strict=True)
    schema = _read_json(root / SCHEMA_DIR / "scale01-no-write-evidence.schema.json")
    _validate_schema(schema, evidence, "SCALE-01 no-write evidence")
    if evidence["evidence_id"] != derive_no_write_evidence_id(evidence):
        raise Scale01VerificationError("no-write evidence content address mismatch")

    _require_equal(evidence["fixture_root"], path_identity(fixture_root), "no-write fixture root")
    _require_equal(evidence["scratch_root"], path_identity(scratch_root), "no-write scratch root")
    _assert_disjoint(fixture_root, scratch_root)

    if not isinstance(pre_snapshot, ProtectedStateSnapshot):
        raise Scale01VerificationError("protected pre-snapshot type mismatch")
    _require_equal(
        pre_snapshot.fixture_root.as_dict(),
        path_identity(fixture_root),
        "immutable pre-snapshot fixture-root binding",
    )

    bound_paths = {field: Path(binding.configured_path) for field, binding in pre_snapshot.surface_bindings}
    post_snapshot = snapshot_protected_state(
        fixture_root,
        protected_surface_paths=bound_paths,
    )
    _require_equal(
        post_snapshot.fixture_root,
        pre_snapshot.fixture_root,
        "immutable pre-snapshot fixture-root binding",
    )
    _require_equal(
        post_snapshot.surface_bindings,
        pre_snapshot.surface_bindings,
        "immutable pre-snapshot protected-path binding",
    )

    pre_state = pre_snapshot.evidence_state()
    post_state = post_snapshot.evidence_state()
    _validate_protected_state(pre_state, "observed pre-state")
    _validate_protected_state(post_state, "observed post-state")
    derived_comparison = _derive_protected_state_comparison(pre_state, post_state)
    _require_equal(evidence["pre_state"], pre_state, "pre/post protected state")
    _require_equal(evidence["post_state"], post_state, "pre/post protected state")
    _require_equal(evidence["comparison"], derived_comparison, "derived protected-state comparison")
    if not all(derived_comparison.values()):
        raise Scale01VerificationError("pre/post protected state changed")

    if evidence["legacy_write_paths"] or evidence["publication_paths"]:
        raise Scale01VerificationError("no-write evidence records a forbidden write or publication")
    expected_rollback = (
        "verified_zero_publication_after_failure" if evidence["failure_injected"] else "not_required_zero_publication"
    )
    _require_equal(evidence["rollback_status"], expected_rollback, "rollback status")


def verify_scale01_preflight_candidate(
    repo_root: Path,
    fixture_root: Path,
    scratch_root: Path,
    fixture_observation: Mapping[str, Any],
    no_write_evidence: Mapping[str, Any],
    *,
    package_index: Mapping[str, Any] | None = None,
    blueprint: Mapping[str, Any] | None = None,
    preflight: Mapping[str, Any] | None = None,
    w11_dossier_manifest: Mapping[str, Any] | None = None,
    failure_injector: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Fail closed until the canonical foundation dependency is materialized."""

    root = repo_root.resolve(strict=True)
    frozen_preflight = _read_json(root / PREFLIGHT_PATH)
    foundation_dependencies = [row for row in frozen_preflight["dependencies"] if row["dependency_id"] == "foundation"]
    _require_equal(
        foundation_dependencies,
        [
            {
                "dependency_id": "foundation",
                "status": "pending",
                "exact_ref": None,
                "raw_sha256": None,
                "git_blob_id": None,
            }
        ],
        "canonical foundation dependency",
    )
    raise Scale01VerificationError(
        "canonical foundation dependency is pending: exact_ref, raw_sha256, and git_blob_id are null"
    )
