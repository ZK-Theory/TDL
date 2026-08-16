"""Strict operator binding for the provider-free Discovery runtime.

This module owns only public configuration admission and deterministic readback.
Discovery lifecycle, authority resolution, idempotency, and recovery remain in
``DiscoveryRuntime``; no second lifecycle state machine is introduced here.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from research_system.authority import LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command, Receipt
from research_system.config import ControlBinding
from research_system.discovery.accepted_w11 import ACCEPTED, CATALOGUE_STREAM_ID
from research_system.discovery.replay.driver import replay_discovery
from research_system.discovery.rules import _git_blob
from research_system.discovery.runtime import DiscoveryRuntime
from research_system.errors import ArsError, ConfigurationError, IntegrityError
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.layout import require_existing_control_root
from research_system.store.ledger import EventLedger


_OPERATOR_CONFIG_FIELDS = frozenset(
    {"control_binding", "authority_binding", "repository_root", "catalogue_path", "root_tokens"}
)
_COMMAND_FIELDS = frozenset(
    {
        "command_id",
        "command_type",
        "actor_id",
        "authority_grant_id",
        "idempotency_key",
        "target_stream_id",
        "expected_stream_version",
        "payload",
    }
)
_CATALOGUE_RELATIVE_PATH = Path(".research-system") / "evals" / "expected" / "w11-portfolio-discovery-v1.json"
_BOOTSTRAP_RELATIVE_PATH = (
    Path(".research-system") / "contracts" / "w11" / "w11-materialization-bootstrap-contract.yaml"
)
_GIT_TIMEOUT_SECONDS = 10


def _configuration_error(message: str, exc: BaseException | None = None) -> ConfigurationError:
    error = ConfigurationError(message)
    if exc is not None:
        error.__cause__ = exc
    return error


def _resolve_absolute_path(value: object, *, label: str, directory: bool | None = None) -> Path:
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{label} must be a non-empty absolute path")
    path = Path(value)
    if not path.is_absolute():
        raise ConfigurationError(f"{label} must be an absolute path")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise _configuration_error(f"{label} is unavailable", exc)
    if directory is True and not resolved.is_dir():
        raise ConfigurationError(f"{label} must be an existing directory")
    if directory is False and not resolved.is_file():
        raise ConfigurationError(f"{label} must be an existing file")
    return resolved


def _read_canonical_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _configuration_error(f"invalid {label} JSON", exc)
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise ConfigurationError(f"{label} JSON must be a canonical object")
    return value


def _validate_root_tokens(value: object, repository_root: Path) -> dict[str, Path]:
    if not isinstance(value, dict) or set(value) != {"repository"}:
        raise ConfigurationError("root_tokens must contain exactly the repository token")
    root = _resolve_absolute_path(value["repository"], label="root token repository", directory=True)
    if root != repository_root:
        raise ConfigurationError("root token repository must resolve to repository_root")
    return {"repository": root}


@dataclass(frozen=True)
class DiscoveryOperatorConfig:
    """The explicit, immutable inputs required to bind one Discovery operator."""

    control_binding_path: Path
    authority_binding_path: Path
    repository_root: Path
    catalogue_path: Path
    root_tokens: Mapping[str, Path]

    @classmethod
    def load(cls, path: Path) -> "DiscoveryOperatorConfig":
        config_path = _resolve_absolute_path(str(path), label="operator config", directory=False)
        value = _read_canonical_object(config_path, label="operator config")
        if set(value) != _OPERATOR_CONFIG_FIELDS:
            raise ConfigurationError("operator config fields are invalid")
        control_binding_path = _resolve_absolute_path(
            value["control_binding"],
            label="control_binding",
            directory=False,
        )
        authority_binding_path = _resolve_absolute_path(
            value["authority_binding"],
            label="authority_binding",
            directory=False,
        )
        repository_root = _resolve_absolute_path(value["repository_root"], label="repository_root", directory=True)
        _validate_clean_git_worktree(repository_root)
        catalogue_path = _resolve_absolute_path(value["catalogue_path"], label="catalogue_path", directory=False)
        expected_catalogue = (repository_root / _CATALOGUE_RELATIVE_PATH).resolve(strict=True)
        if catalogue_path != expected_catalogue:
            raise ConfigurationError("catalogue_path is not the accepted W11 catalogue path")
        _validate_w11_repository_bytes(repository_root, catalogue_path)
        return cls(
            control_binding_path,
            authority_binding_path,
            repository_root,
            catalogue_path,
            _validate_root_tokens(value["root_tokens"], repository_root),
        )


def _scrubbed_git_environment() -> dict[str, str]:
    """Return an environment that cannot redirect fixed Git repository queries."""

    environment = dict(os.environ)
    for variable in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    ):
        environment.pop(variable, None)
    # Git honours this as a read-only hint: configuration admission must not
    # refresh an index or create a lock while deciding whether to reject it.
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    return environment


def _git_result(repository_root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run one fixed Git validation command; this never reaches a provider process."""

    try:
        return subprocess.run(  # nosec B603 B607 - fixed Git executable and argument vectors
            ["git", "-C", str(repository_root), *arguments],
            capture_output=True,
            check=False,
            env=_scrubbed_git_environment(),
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise _configuration_error("repository_root Git validation is unavailable", exc)


def _git_output(repository_root: Path, *arguments: str) -> str:
    result = _git_result(repository_root, *arguments)
    if result.returncode != 0:
        raise ConfigurationError("repository_root is not an actual Git worktree root")
    return result.stdout.strip()


def _validate_clean_git_worktree(repository_root: Path) -> None:
    """Require the explicit root to be one clean Git worktree, not a marker or subdirectory."""

    top_level = _git_output(repository_root, "rev-parse", "--show-toplevel")
    git_directory = _git_output(repository_root, "rev-parse", "--git-dir")
    try:
        resolved_top_level = Path(top_level).resolve(strict=True)
        resolved_git_directory = Path(git_directory)
        if not resolved_git_directory.is_absolute():
            resolved_git_directory = repository_root / resolved_git_directory
        resolved_git_directory = resolved_git_directory.resolve(strict=True)
    except OSError as exc:
        raise _configuration_error("repository_root Git metadata is unavailable", exc)
    if resolved_top_level != repository_root or not resolved_git_directory.is_dir():
        raise ConfigurationError("repository_root is not an actual Git worktree root")
    status = _git_output(
        repository_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    if status:
        raise ConfigurationError("repository_root is not clean")
    for arguments in (("diff", "--quiet", "--no-ext-diff"), ("diff", "--cached", "--quiet", "--no-ext-diff")):
        result = _git_result(repository_root, *arguments)
        if result.returncode == 1:
            raise ConfigurationError("repository_root is not clean")
        if result.returncode != 0:
            raise ConfigurationError("repository_root Git validation failed")


def _validate_w11_repository_bytes(repository_root: Path, catalogue_path: Path) -> None:
    """Bind the configured paths to accepted W11 bytes and their committed Git blobs."""

    try:
        catalogue = catalogue_path.read_bytes()
        bootstrap = (repository_root / _BOOTSTRAP_RELATIVE_PATH).read_bytes()
    except OSError as exc:
        raise _configuration_error("accepted W11 repository material is unavailable", exc)
    if (
        len(catalogue) != ACCEPTED["catalogue_bytes"]
        or sha256_hex(catalogue) != ACCEPTED["catalogue_sha256"]
        or _git_blob(catalogue) != ACCEPTED["catalogue_blob"]
    ):
        raise ConfigurationError("catalogue_path does not bind the accepted W11 catalogue")
    if sha256_hex(bootstrap) != ACCEPTED["bootstrap_sha256"] or _git_blob(bootstrap) != ACCEPTED["bootstrap_blob"]:
        raise ConfigurationError("repository_root does not bind the accepted W11 bootstrap")
    if (
        _git_output(repository_root, "rev-parse", "--verify", f"HEAD:{_CATALOGUE_RELATIVE_PATH.as_posix()}")
        != ACCEPTED["catalogue_blob"]
    ):
        raise ConfigurationError("catalogue_path is not the committed accepted W11 catalogue")
    if (
        _git_output(repository_root, "rev-parse", "--verify", f"HEAD:{_BOOTSTRAP_RELATIVE_PATH.as_posix()}")
        != ACCEPTED["bootstrap_blob"]
    ):
        raise ConfigurationError("repository_root does not commit the accepted W11 bootstrap")


def _require_physical_directory(path: Path, *, label: str) -> Path:
    """Resolve an existing directory while rejecting every symlink/reparse escape on its path."""

    candidate = Path(os.path.abspath(os.fspath(path)))
    if not candidate.is_absolute() or not candidate.anchor:
        raise ConfigurationError(f"{label} physical path must be absolute")
    current = Path(candidate.anchor)
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for part in candidate.relative_to(current).parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise _configuration_error(f"{label} physical path is unavailable", exc)
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse_attribute:
            raise ConfigurationError(f"{label} physical path has a reparse component")
        if not stat.S_ISDIR(metadata.st_mode):
            raise ConfigurationError(f"{label} physical path is not a directory")
    try:
        return candidate.resolve(strict=True)
    except OSError as exc:
        raise _configuration_error(f"{label} physical path is unavailable", exc)


def _require_runtime_layout(control_root: Path, project_id: str, *, label: str) -> None:
    """Reject any nested store layout that a constructor would otherwise create."""

    required = (
        Path("objects"),
        Path("events"),
        Path("events") / project_id,
        Path("manifests"),
        Path("receipts"),
        Path("receipts") / "idempotency",
        Path("runtime"),
    )
    for relative in required:
        resolved = _require_physical_directory(control_root / relative, label=f"{label} {relative.as_posix()}")
        try:
            resolved.relative_to(control_root)
        except ValueError as exc:
            raise _configuration_error(f"{label} {relative.as_posix()} escapes its configured root", exc)


@dataclass(frozen=True)
class DiscoveryOperator:
    """Validated operator resources with one submit path and a read-only replay path."""

    control_root: Path
    ledger: EventLedger
    schemas: SchemaRegistry
    authority_resolver: LedgerAuthorityGrantResolver
    repository_root: Path
    catalogue_path: Path
    root_tokens: Mapping[str, Path]
    clock: Callable[[], datetime]

    def submit(self, envelope: dict[str, Any]) -> Receipt:
        """Submit only through the authoritative DiscoveryRuntime public seam."""

        return DiscoveryRuntime(
            self.control_root,
            self.ledger,
            self.schemas,
            catalogue_path=self.catalogue_path,
            authority_resolver=self.authority_resolver,
            clock=self.clock,
            repository_root=self.repository_root,
            root_tokens=self.root_tokens,
            operational_ledger=self.ledger,
        ).submit(envelope)

    def prevalidate(
        self,
        envelope: dict[str, Any],
        *,
        prospective_document: Mapping[str, Any] | None = None,
    ) -> None:
        """Validate one governed command at the current tail without publishing it."""

        DiscoveryRuntime(
            self.control_root,
            self.ledger,
            self.schemas,
            catalogue_path=self.catalogue_path,
            authority_resolver=self.authority_resolver,
            clock=self.clock,
            repository_root=self.repository_root,
            root_tokens=self.root_tokens,
            operational_ledger=self.ledger,
        ).prevalidate(envelope, prospective_document=prospective_document)

    def status(self) -> dict[str, Any]:
        """Return deterministic Discovery replay/readback without invoking a writer."""

        events = tuple(self.ledger.iter_events())
        projection = replay_discovery(
            events,
            schemas=self.schemas,
            authority_state_validator=self.authority_resolver.validate_replayed_administration_state,
        )
        catalogue = projection["catalogue"]
        catalogue_readback: dict[str, object] | None
        if catalogue is None:
            catalogue_readback = None
        else:
            catalogue_readback = {
                "stream_id": CATALOGUE_STREAM_ID,
                "state": "imported",
                "accepted_commit": catalogue["accepted_commit"],
            }
        latest_position = events[-1]["global_position"] if events else 0
        return {
            "event_count": len(events),
            "latest_global_position": latest_position,
            "projection": {
                "catalogue": catalogue_readback,
                "source_observation_count": len(projection["source_observations"]),
                "candidate_count": len(projection["candidates"]),
                "assay_count": len(projection["assays"]),
                "spike_count": len(projection["spikes"]),
                "dossier_count": len(projection["dossiers"]),
            },
        }


def load_discovery_operator(config_path: Path) -> DiscoveryOperator:
    """Validate all immutable operator inputs before constructing any writer-capable runtime."""

    config = DiscoveryOperatorConfig.load(config_path)
    try:
        try:
            binding = ControlBinding.load(config.control_binding_path)
        except ConfigurationError:
            binding = ControlBinding.load_repaired(config.control_binding_path)
        try:
            authority_binding = ControlBinding.load(config.authority_binding_path)
        except ConfigurationError:
            authority_binding = ControlBinding.load_repaired(config.authority_binding_path)
        bound_code_roots = {Path(root).resolve(strict=True) for root in binding.code_roots}
        if config.repository_root not in bound_code_roots:
            raise ConfigurationError("repository_root is not bound by control_binding")
        if binding.project_id != authority_binding.project_id:
            raise ConfigurationError("control and authority bindings have different project identities")
        schema_root = Path(binding.schema_root).resolve(strict=True)
        authority_schema_root = Path(authority_binding.schema_root).resolve(strict=True)
        if schema_root != authority_schema_root:
            raise ConfigurationError("control and authority bindings have different schema roots")
        configured_control_root = _require_physical_directory(
            Path(binding.control_root),
            label="control store",
        )
        configured_authority_root = _require_physical_directory(
            Path(authority_binding.control_root),
            label="authority store",
        )
        control_root = require_existing_control_root(list(binding.code_roots), configured_control_root)
        authority_root = require_existing_control_root(
            list(authority_binding.code_roots),
            configured_authority_root,
        )
        if control_root != configured_control_root or authority_root != configured_authority_root:
            raise ConfigurationError("configured store path did not retain its physical identity")
        _require_runtime_layout(control_root, binding.project_id, label="control store")
        _require_runtime_layout(authority_root, authority_binding.project_id, label="authority store")
        schemas = runtime_schema_registry(schema_root)
        if schemas.command_binding("ImportAcceptedW11CatalogueGenesis") is None:
            raise ConfigurationError("schema root has no active Discovery command binding")
        resolver = LedgerAuthorityGrantResolver(
            authority_root,
            authority_binding.project_id,
            authority_binding.store_identity,
            schemas,
            approved_witness=authority_binding.origin_witness,
            approved_witness_path=authority_binding.origin_witness_path,
        )
    except ConfigurationError:
        raise
    except (ArsError, AttributeError, OSError, TypeError, ValueError) as exc:
        raise _configuration_error("Discovery operator binding is invalid", exc)
    # The preflight above requires every directory touched by EventLedger and
    # ReceiptStore. These constructors cannot repair an absent/partial store.
    ledger = EventLedger(control_root, binding.project_id, schemas, store_identity=binding.store_identity)
    return DiscoveryOperator(
        control_root=control_root,
        ledger=ledger,
        schemas=schemas,
        authority_resolver=resolver,
        repository_root=config.repository_root,
        catalogue_path=config.catalogue_path,
        root_tokens=dict(config.root_tokens),
        clock=lambda: datetime.now(UTC),
    )


def read_discovery_command(path: Path) -> dict[str, Any]:
    """Read the exact eight-field canonical Discovery command envelope before binding a runtime."""

    command_path = _resolve_absolute_path(str(path), label="Discovery command", directory=False)
    value = _read_canonical_object(command_path, label="Discovery command")
    if set(value) != _COMMAND_FIELDS or not isinstance(value.get("payload"), dict):
        raise IntegrityError("invalid Discovery command envelope")
    try:
        Command(deepcopy(value)).payload_hash
    except (TypeError, ValueError) as exc:
        raise IntegrityError("Discovery command payload is not P0-canonical") from exc
    return value
