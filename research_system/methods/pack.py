"""Fail-closed loading and independently anchored history checks for RM-02."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import yaml
from jsonschema import Draft202012Validator


METHODS_ROOT = PurePosixPath(".research-system/methods")
MANIFEST_PATH = METHODS_ROOT / "methods-pack.yaml"
HISTORY_PATH = METHODS_ROOT / "methods-pack-revisions.yaml"
MANIFEST_SCHEMA_PATH = PurePosixPath(".research-system/schemas/methods/methods-pack-manifest.schema.json")
HISTORY_SCHEMA_PATH = PurePosixPath(".research-system/schemas/methods/methods-pack-revisions.schema.json")
ASSET_ROOT = METHODS_ROOT / "assets"
_FRONTMATTER_FIELDS = frozenset(
    {
        "asset_id",
        "name",
        "version",
        "applicability_trigger",
        "compatibility",
        "dependencies",
        "permissions",
        "observer_overlays",
        "declared_review_state",
        "supersedes",
        "required_output",
        "lineage",
    }
)
_SELF_HASH_FIELDS = frozenset(
    {
        "identity",
        "identity_scheme",
        "content_sha256",
        "asset_sha256",
        "raw_sha256",
        "git_blob",
        "git_blob_sha1",
    }
)
_REQUIRED_HEADINGS = (
    "## Purpose",
    "## Applicability",
    "## Operator protocol",
    "## Required RM-03 output",
    "## Failure modes",
    "## Worked example",
    "## Verified lineage",
)


class MethodsPackError(ValueError):
    """Raised when candidate bytes or independently supplied history fail closed."""


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise MethodsPackError(f"duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class ObserverOverlay:
    log_path: str
    title: str
    date: str
    status: str


@dataclass(frozen=True)
class ProjectAddition:
    name: str
    authority: str
    rationale: str


@dataclass(frozen=True)
class AssetLineage:
    source_id: str
    source_title: str
    source_path: str
    source_sha256: str
    sections: tuple[str, ...]
    project_additions: tuple[ProjectAddition, ...]


@dataclass(frozen=True)
class MethodsAsset:
    asset_id: str
    name: str
    version: str
    path: str
    identity_scheme: str
    identity: str
    applicability_trigger: str
    compatibility: str
    dependencies: tuple[str, ...]
    permissions: tuple[str, ...]
    observer_overlays: tuple[ObserverOverlay, ...]
    declared_review_state: str
    supersedes: str | None
    required_output: str
    lineage: AssetLineage
    content: str


@dataclass(frozen=True)
class MethodsPack:
    pack_id: str
    pack_version: str
    declared_review_state: str
    assets: tuple[MethodsAsset, ...]


@dataclass(frozen=True)
class HistoryVerification:
    base_commit: str
    subject_commit: str
    base_history_blob: str | None
    subject_history_blob: str
    asset_count: int
    revision_count: int


def _decode_utf8(raw: bytes, label: str) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise MethodsPackError(f"{label} must not contain a UTF-8 BOM")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MethodsPackError(f"{label} is not valid UTF-8") from exc


def _load_yaml_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = yaml.load(_decode_utf8(raw, label), Loader=_UniqueKeyLoader)
    except MethodsPackError:
        raise
    except yaml.YAMLError as exc:
        raise MethodsPackError(f"{label} is not valid YAML: {exc}") from exc
    if not isinstance(value, dict):
        raise MethodsPackError(f"{label} must be a YAML mapping")
    if not all(isinstance(key, str) for key in value):
        raise MethodsPackError(f"{label} requires string keys")
    return value


def _load_schema_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(_decode_utf8(raw, label))
    except json.JSONDecodeError as exc:
        raise MethodsPackError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise MethodsPackError(f"{label} must be a JSON object")
    try:
        Draft202012Validator.check_schema(value)
    except Exception as exc:
        raise MethodsPackError(f"{label} is not a valid Draft 2020-12 schema") from exc
    return value


def _validate_schema(document: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda item: list(item.path))
    if not errors:
        return
    error = errors[0]
    location = ".".join(str(part) for part in error.absolute_path) or "<root>"
    raise MethodsPackError(f"{label} schema validation failed at {location}: {error.message}")


def _canonical_lf(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _git_blob_sha1(raw: bytes) -> str:
    completed = subprocess.run(
        ["git", "hash-object", "--no-filters", "--stdin"],
        input=raw,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        diagnostic = completed.stderr.decode("utf-8", errors="replace").strip()
        raise MethodsPackError(f"git hash-object failed: {diagnostic}")
    identity = completed.stdout.decode("ascii").strip()
    if len(identity) != 40:
        raise MethodsPackError("git hash-object returned an invalid blob identity")
    return identity


def _asset_identity(raw: bytes, scheme: str) -> str:
    canonical = _canonical_lf(raw)
    if scheme == "git_blob_sha1":
        return _git_blob_sha1(canonical)
    if scheme == "lf_canonical_sha256":
        return hashlib.sha256(canonical).hexdigest()
    raise MethodsPackError(f"unsupported methods asset identity scheme: {scheme!r}")


def _parse_frontmatter(raw: bytes, label: str) -> tuple[dict[str, Any], str]:
    text = _decode_utf8(_canonical_lf(raw), label)
    if not text.startswith("---\n"):
        raise MethodsPackError(f"{label} requires YAML frontmatter")
    try:
        frontmatter_text, body = text[4:].split("\n---\n", 1)
    except ValueError as exc:
        raise MethodsPackError(f"{label} has unterminated YAML frontmatter") from exc
    frontmatter = _load_yaml_bytes(frontmatter_text.encode("utf-8"), f"{label} frontmatter")
    return frontmatter, body


def _find_forbidden_key(value: object) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in _SELF_HASH_FIELDS:
                return str(key)
            found = _find_forbidden_key(nested)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_forbidden_key(nested)
            if found:
                return found
    return None


def _safe_asset_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise MethodsPackError(f"unsafe methods asset path: {value!r}")
    if path.parent != ASSET_ROOT or path.suffix != ".md":
        raise MethodsPackError(f"unknown methods asset path: {value!r}")
    return path


def _overlay(value: dict[str, Any]) -> ObserverOverlay:
    return ObserverOverlay(
        log_path=value["log_path"],
        title=value["title"],
        date=value["date"],
        status=value["status"],
    )


def _lineage(value: dict[str, Any]) -> AssetLineage:
    return AssetLineage(
        source_id=value["source_id"],
        source_title=value["source_title"],
        source_path=value["source_path"],
        source_sha256=value["source_sha256"],
        sections=tuple(value["sections"]),
        project_additions=tuple(
            ProjectAddition(
                name=item["name"],
                authority=item["authority"],
                rationale=item["rationale"],
            )
            for item in value["project_additions"]
        ),
    )


def _validate_history_semantics(
    manifest: dict[str, Any],
    history: dict[str, Any],
) -> None:
    assets = manifest["assets"]
    asset_ids = {item["asset_id"] for item in assets}
    revisions = history["revisions"]
    seen_keys: set[tuple[str, str]] = set()
    seen_identities: set[str] = set()
    by_asset: dict[str, list[dict[str, Any]]] = {asset_id: [] for asset_id in asset_ids}
    for row in revisions:
        asset_id = row["asset_id"]
        if asset_id not in asset_ids:
            raise MethodsPackError(f"unknown asset in methods history: {asset_id}")
        key = (asset_id, row["version"])
        if key in seen_keys:
            raise MethodsPackError(f"duplicate methods history version: {asset_id} {row['version']}")
        if row["identity"] in seen_identities:
            raise MethodsPackError(f"duplicate methods history identity: {row['identity']}")
        seen_keys.add(key)
        seen_identities.add(row["identity"])
        by_asset[asset_id].append(row)

    manifest_by_id = {item["asset_id"]: item for item in assets}
    for asset_id, rows in by_asset.items():
        if not rows:
            raise MethodsPackError(f"current manifest asset has no history: {asset_id}")
        for index, row in enumerate(rows):
            if index == 0:
                if row["supersedes_identity"] is not None:
                    raise MethodsPackError(f"genesis history entry supersedes an identity: {asset_id}")
            elif row["supersedes_identity"] != rows[index - 1]["identity"]:
                raise MethodsPackError(f"broken supersedes chain for methods asset: {asset_id}")
        latest = rows[-1]
        current = manifest_by_id[asset_id]
        for field in ("version", "identity_scheme", "identity"):
            if latest[field] != current[field]:
                raise MethodsPackError(f"methods history does not match current manifest for {asset_id}: {field}")


def _materialize_pack(
    *,
    manifest: dict[str, Any],
    history: dict[str, Any],
    asset_bytes: dict[str, bytes],
) -> MethodsPack:
    rows = manifest["assets"]
    asset_ids = [row["asset_id"] for row in rows]
    paths = [row["path"] for row in rows]
    identities = [row["identity"] for row in rows]
    if len(asset_ids) != len(set(asset_ids)):
        raise MethodsPackError("duplicate methods asset_id in manifest")
    if len(paths) != len(set(paths)):
        raise MethodsPackError("duplicate methods asset path in manifest")
    if len(identities) != len(set(identities)):
        raise MethodsPackError("duplicate methods asset identity in manifest")
    safe_paths = {_safe_asset_path(path).as_posix() for path in paths}
    if safe_paths != set(asset_bytes):
        missing = sorted(safe_paths - set(asset_bytes))
        extra = sorted(set(asset_bytes) - safe_paths)
        raise MethodsPackError(f"manifest asset paths do not match current assets: missing={missing}, extra={extra}")

    _validate_history_semantics(manifest, history)
    assets: list[MethodsAsset] = []
    for row in rows:
        raw = asset_bytes[row["path"]]
        frontmatter, body = _parse_frontmatter(raw, row["path"])
        forbidden = _find_forbidden_key(frontmatter)
        if forbidden:
            raise MethodsPackError(f"methods asset frontmatter contains forbidden self-hash field {forbidden!r}")
        if set(frontmatter) != _FRONTMATTER_FIELDS:
            missing = sorted(_FRONTMATTER_FIELDS - set(frontmatter))
            extra = sorted(set(frontmatter) - _FRONTMATTER_FIELDS)
            raise MethodsPackError(
                f"methods asset frontmatter fields differ for {row['asset_id']}: missing={missing}, extra={extra}"
            )
        expected_frontmatter = {field: row[field] for field in _FRONTMATTER_FIELDS}
        if frontmatter != expected_frontmatter:
            raise MethodsPackError(f"methods asset frontmatter mismatch for {row['asset_id']}")
        missing_headings = [heading for heading in _REQUIRED_HEADINGS if heading not in body]
        if missing_headings:
            raise MethodsPackError(f"methods asset {row['asset_id']} lacks required sections: {missing_headings}")
        if row["asset_id"] == "mth_context_deidentification_transform" and "authorized_consumers" in body.lower():
            raise MethodsPackError("context de-identification sidecar must not self-declare authorized_consumers")
        computed = _asset_identity(raw, row["identity_scheme"])
        if computed != row["identity"]:
            raise MethodsPackError(
                f"methods asset identity mismatch for {row['asset_id']}: "
                f"expected {row['identity']}, computed {computed}"
            )
        assets.append(
            MethodsAsset(
                asset_id=row["asset_id"],
                name=row["name"],
                version=row["version"],
                path=row["path"],
                identity_scheme=row["identity_scheme"],
                identity=row["identity"],
                applicability_trigger=row["applicability_trigger"],
                compatibility=row["compatibility"],
                dependencies=tuple(row["dependencies"]),
                permissions=tuple(row["permissions"]),
                observer_overlays=tuple(_overlay(item) for item in row["observer_overlays"]),
                declared_review_state=row["declared_review_state"],
                supersedes=row["supersedes"],
                required_output=row["required_output"],
                lineage=_lineage(row["lineage"]),
                content=body,
            )
        )
    return MethodsPack(
        pack_id=manifest["pack_id"],
        pack_version=manifest["pack_version"],
        declared_review_state=manifest["declared_review_state"],
        assets=tuple(assets),
    )


def load_methods_pack(repo_root: str | Path) -> MethodsPack:
    """Load current RM-02 candidate bytes without deriving acceptance from them."""

    root = Path(repo_root).resolve()
    manifest_schema = _load_schema_bytes((root / MANIFEST_SCHEMA_PATH).read_bytes(), str(MANIFEST_SCHEMA_PATH))
    history_schema = _load_schema_bytes((root / HISTORY_SCHEMA_PATH).read_bytes(), str(HISTORY_SCHEMA_PATH))
    manifest = _load_yaml_bytes((root / MANIFEST_PATH).read_bytes(), str(MANIFEST_PATH))
    history = _load_yaml_bytes((root / HISTORY_PATH).read_bytes(), str(HISTORY_PATH))
    _validate_schema(manifest, manifest_schema, "methods manifest")
    _validate_schema(history, history_schema, "methods history")

    asset_dir = root / ASSET_ROOT
    asset_bytes = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(asset_dir.glob("*.md"))
        if path.is_file()
    }
    return _materialize_pack(manifest=manifest, history=history, asset_bytes=asset_bytes)


def verify_methods_pack_lineage(
    pack: MethodsPack,
    source_bytes_by_sha256: Mapping[str, bytes],
) -> None:
    """Verify cited section anchors against independently supplied source bytes."""

    checked_sources: dict[str, str] = {}
    for asset in pack.assets:
        lineage = asset.lineage
        raw = source_bytes_by_sha256.get(lineage.source_sha256)
        if raw is None:
            raise MethodsPackError(f"lineage source bytes are unavailable for methods asset {asset.asset_id}")
        if lineage.source_sha256 not in checked_sources:
            computed = hashlib.sha256(raw).hexdigest()
            if computed != lineage.source_sha256:
                raise MethodsPackError(
                    f"lineage source identity mismatch: expected {lineage.source_sha256}, computed {computed}"
                )
            checked_sources[lineage.source_sha256] = _decode_utf8(raw, f"lineage source {lineage.source_path}")
        source_text = checked_sources[lineage.source_sha256]
        for section in lineage.sections:
            if section not in source_text:
                raise MethodsPackError(f"nonexistent lineage section {section!r} for methods asset {asset.asset_id}")


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-C", str(root), *args],
        input=input_bytes,
        capture_output=True,
        check=False,
    )


def _resolve_commit(root: Path, ref: str, label: str) -> str:
    completed = _git(root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if completed.returncode != 0:
        raise MethodsPackError(f"cannot resolve independently supplied {label} ref: {ref!r}")
    return completed.stdout.decode("ascii").strip()


def _git_object_exists(root: Path, object_spec: str) -> bool:
    return _git(root, "cat-file", "-e", object_spec).returncode == 0


def _git_show(root: Path, commit: str, path: PurePosixPath) -> bytes:
    completed = _git(root, "show", f"{commit}:{path.as_posix()}")
    if completed.returncode != 0:
        raise MethodsPackError(f"required methods path absent at {commit}: {path}")
    return completed.stdout


def _git_blob_at(root: Path, commit: str, path: PurePosixPath) -> str:
    completed = _git(root, "rev-parse", f"{commit}:{path.as_posix()}")
    if completed.returncode != 0:
        raise MethodsPackError(f"cannot resolve methods blob at {commit}: {path}")
    return completed.stdout.decode("ascii").strip()


def _subject_asset_bytes(root: Path, commit: str) -> dict[str, bytes]:
    completed = _git(root, "ls-tree", "-r", "--name-only", commit, "--", ASSET_ROOT.as_posix())
    if completed.returncode != 0:
        raise MethodsPackError("cannot enumerate subject methods assets")
    paths = [line for line in completed.stdout.decode("utf-8").splitlines() if line.endswith(".md")]
    return {path: _git_show(root, commit, PurePosixPath(path)) for path in paths}


def verify_methods_pack_history(
    repo_root: str | Path,
    *,
    base_ref: str,
    subject_ref: str,
) -> HistoryVerification:
    """Verify append history using refs supplied only by the independent caller."""

    root = Path(repo_root).resolve()
    base_commit = _resolve_commit(root, base_ref, "base")
    subject_commit = _resolve_commit(root, subject_ref, "subject")
    ancestry = _git(root, "merge-base", "--is-ancestor", base_commit, subject_commit)
    if ancestry.returncode != 0:
        raise MethodsPackError("independently supplied base is not an ancestor of subject")

    manifest_schema = _load_schema_bytes(
        _git_show(root, subject_commit, MANIFEST_SCHEMA_PATH), str(MANIFEST_SCHEMA_PATH)
    )
    history_schema = _load_schema_bytes(_git_show(root, subject_commit, HISTORY_SCHEMA_PATH), str(HISTORY_SCHEMA_PATH))
    manifest = _load_yaml_bytes(
        _git_show(root, subject_commit, MANIFEST_PATH),
        f"{subject_commit}:{MANIFEST_PATH}",
    )
    history = _load_yaml_bytes(
        _git_show(root, subject_commit, HISTORY_PATH),
        f"{subject_commit}:{HISTORY_PATH}",
    )
    _validate_schema(manifest, manifest_schema, "subject methods manifest")
    _validate_schema(history, history_schema, "subject methods history")
    subject_history_blob = _git_blob_at(root, subject_commit, HISTORY_PATH)
    base_spec = f"{base_commit}:{HISTORY_PATH.as_posix()}"
    base_history_blob: str | None = None
    if _git_object_exists(root, base_spec):
        base_history_blob = _git_blob_at(root, base_commit, HISTORY_PATH)
        base_history = _load_yaml_bytes(
            _git_show(root, base_commit, HISTORY_PATH),
            f"{base_commit}:{HISTORY_PATH}",
        )
        _validate_schema(base_history, history_schema, "base methods history")
        base_revisions = base_history["revisions"]
        subject_revisions = history["revisions"]
        if subject_revisions[: len(base_revisions)] != base_revisions:
            raise MethodsPackError("subject methods history lacks the retained ordered prefix from base")
        appended = subject_revisions[len(base_revisions) :]
        if not appended:
            if subject_history_blob != base_history_blob:
                raise MethodsPackError("methods history blob changed without an appended revision")
        elif any(row["previous_history_blob"] != base_history_blob for row in appended):
            raise MethodsPackError("appended revision has wrong previous_history_blob")
    elif any(row["previous_history_blob"] is not None for row in history["revisions"]):
        raise MethodsPackError("genesis history cannot claim a previous_history_blob")

    pack = _materialize_pack(
        manifest=manifest,
        history=history,
        asset_bytes=_subject_asset_bytes(root, subject_commit),
    )

    return HistoryVerification(
        base_commit=base_commit,
        subject_commit=subject_commit,
        base_history_blob=base_history_blob,
        subject_history_blob=subject_history_blob,
        asset_count=len(pack.assets),
        revision_count=len(history["revisions"]),
    )
