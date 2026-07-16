from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError

from research_system.errors import SchemaError

_AUTHORITY_SCHEMA_IDS = frozenset(
    {
        "ars://core/store-identity/1.1",
        "ars://core/event",
        "ars://core/event/AuthorityRootInitialized/payload",
        "ars://core/event/AuthorityGrantActivated/payload",
        "ars://core/event/ReleaseGateDecisionPublished",
    }
)


class SchemaRegistry:
    def __init__(self, root: Path):
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
        schema = self._schemas.get(schema_id)
        if schema is None:
            raise SchemaError(f"unknown schema: {schema_id}")
        errors = sorted(
            Draft202012Validator(schema).iter_errors(value),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            message = "; ".join(
                f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}" for error in errors
            )
            raise SchemaError(f"{schema_id}: {message}")

    def contains(self, schema_id: str) -> bool:
        """Return whether an exact schema identifier is registered."""
        return schema_id in self._schemas


def authority_schema_registry(root: Path) -> SchemaRegistry:
    """Load a registry that can validate authority genesis and governed replay."""
    registry = SchemaRegistry(root)
    missing = sorted(schema_id for schema_id in _AUTHORITY_SCHEMA_IDS if not registry.contains(schema_id))
    if missing:
        raise SchemaError(f"authority schema registry is incomplete: {', '.join(missing)}")
    return registry


@lru_cache(maxsize=1)
def bundled_schema_registry() -> SchemaRegistry:
    """Return the immutable schema registry shipped with this code checkout."""
    return SchemaRegistry(Path(__file__).resolve().parent.parent / ".research-system" / "schemas")
