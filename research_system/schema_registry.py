from __future__ import annotations

import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError

from research_system.errors import SchemaError

_AUTHORITY_SCHEMA_IDS = frozenset(
    {
        "ars://core/store-identity/1.1",
        "ars://core/command",
        "ars://core/command/RevokeAuthorityGrant/payload",
        "ars://core/event",
        "ars://core/event/AuthorityRootInitialized/payload",
        "ars://core/event/AuthorityGrantActivated/payload",
        "ars://core/event/AuthorityGrantRevoked/payload",
        "ars://core/event/ReleaseGateDecisionPublished",
    }
)

_RFC3339_DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$")


def _is_rfc3339_date_time(value: object) -> bool:
    """Provide the Draft 2020-12 date-time check when its optional dependency is absent."""
    if not isinstance(value, str):
        # ``format`` is ignored for instance types it does not apply to, so a
        # non-string (e.g. a null ``occurred_at``) conforms vacuously. This
        # mirrors jsonschema's own ``is_datetime``; returning False here made
        # this fallback stricter than the checker it stands in for.
        return True
    if _RFC3339_DATE_TIME.fullmatch(value) is None:
        return False
    normalized = value[:-1] + "+00:00" if value[-1] in "Zz" else value
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


if "date-time" not in Draft202012Validator.FORMAT_CHECKER.checkers:
    Draft202012Validator.FORMAT_CHECKER.checks("date-time")(_is_rfc3339_date_time)


class SchemaRegistry:
    def __init__(self, root: Path) -> None:
        """Load and validate every JSON Schema below a registry root.

        Args:
            root: Directory containing registered ``*.schema.json`` files.

        Raises:
            SchemaError: If a schema is unreadable, invalid, or duplicated.
        """
        self._schemas: dict[str, dict[str, Any]] = {}
        for path in sorted(root.rglob("*.schema.json")):
            try:
                schema = json.loads(path.read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(schema)
                schema_id = schema["$id"]
            except (OSError, json.JSONDecodeError, JsonSchemaError, KeyError) as exc:
                raise SchemaError(f"invalid schema: {path}") from exc
            if schema_id in self._schemas:
                raise SchemaError(f"duplicate schema: {schema_id}")
            self._schemas[schema_id] = schema

    def validate(self, schema_id: str, value: Any) -> None:
        """Validate a value against an exact registered schema identifier.

        Args:
            schema_id: Exact ``$id`` of the schema to apply.
            value: JSON-compatible value to validate.

        Raises:
            SchemaError: If the schema is unknown or the value is invalid.
        """
        schema = self._schemas.get(schema_id)
        if schema is None:
            raise SchemaError(f"unknown schema: {schema_id}")
        errors = sorted(
            Draft202012Validator(
                schema,
                format_checker=Draft202012Validator.FORMAT_CHECKER,
            ).iter_errors(value),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            message = "; ".join(
                f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}" for error in errors
            )
            raise SchemaError(f"{schema_id}: {message}")

    def contains(self, schema_id: str) -> bool:
        """Return whether an exact schema identifier is registered.

        Args:
            schema_id: Exact ``$id`` to look up.

        Returns:
            Whether the registry contains the identifier.
        """
        return schema_id in self._schemas


def authority_schema_registry(root: Path) -> SchemaRegistry:
    """Load a registry that supports authority genesis and governed operations.

    Args:
        root: Directory containing the candidate authority schemas.

    Returns:
        A complete authority-capable schema registry.

    Raises:
        SchemaError: If any schema is invalid or a required schema is absent.
    """
    registry = SchemaRegistry(root)
    missing = sorted(schema_id for schema_id in _AUTHORITY_SCHEMA_IDS if not registry.contains(schema_id))
    if missing:
        raise SchemaError(f"authority schema registry is incomplete: {', '.join(missing)}")
    return registry


@lru_cache(maxsize=8)
def _registry_for_resolved_root(root: Path) -> SchemaRegistry:
    return SchemaRegistry(root)


def cached_schema_registry(root: Path | str) -> SchemaRegistry:
    """Return a shared registry for an immutable schema directory.

    Constructing a registry meta-validates every ``*.schema.json`` below the
    root, so callers that validate many documents against one checked-in schema
    tree must not rebuild it per document. Registries are read-only after
    construction, and the schema tree is immutable for the life of a checkout,
    so one instance per resolved root is safe to share.

    Args:
        root: Directory containing registered ``*.schema.json`` files.

    Returns:
        The shared registry for ``root``.

    Raises:
        SchemaError: If a schema is unreadable, invalid, or duplicated.
    """
    return _registry_for_resolved_root(Path(root).resolve())


@lru_cache(maxsize=1)
def bundled_schema_registry() -> SchemaRegistry:
    """Return the immutable schema registry shipped with this code checkout."""
    return SchemaRegistry(Path(__file__).resolve().parent.parent / ".research-system" / "schemas")
