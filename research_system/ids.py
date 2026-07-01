from __future__ import annotations

import re
import secrets
import time
import uuid
from collections.abc import Mapping
from pathlib import Path

import yaml

from research_system.errors import ConfigurationError

_PREFIX = re.compile(r'^[a-z][a-z0-9]{2,3}$')
_REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent
    / '.research-system'
    / 'config'
    / 'id-kind-registry.yaml'
)


def _uuid7(now_ms: int | None = None) -> uuid.UUID:
    timestamp_ms = time.time_ns() // 1_000_000 if now_ms is None else now_ms
    if not 0 <= timestamp_ms < 1 << 48:
        raise ValueError('UUIDv7 timestamp is outside 48-bit range')
    value = (
        (timestamp_ms << 80)
        | (0x7 << 76)
        | (secrets.randbits(12) << 64)
        | (0b10 << 62)
        | secrets.randbits(62)
    )
    return uuid.UUID(int=value)


class IdRegistry:
    def __init__(self, kind_prefixes: Mapping[str, str]):
        if not kind_prefixes:
            raise ConfigurationError('ID kind registry is empty')
        malformed = {
            kind: prefix
            for kind, prefix in kind_prefixes.items()
            if not isinstance(kind, str)
            or not isinstance(prefix, str)
            or not _PREFIX.fullmatch(prefix)
        }
        if malformed:
            raise ConfigurationError(f'malformed ID kind registry entries: {malformed}')
        self._kind_prefixes = dict(kind_prefixes)

    def new(self, kind: str) -> str:
        try:
            prefix = self._kind_prefixes[kind]
        except KeyError as exc:
            raise ValueError(f'unknown ID kind: {kind}') from exc
        return f'{prefix}_{_uuid7()}'

    def validate(self, value: str, kind: str) -> str:
        try:
            prefix = self._kind_prefixes[kind]
        except KeyError as exc:
            raise ValueError(f'unknown ID kind: {kind}') from exc
        marker = f'{prefix}_'
        if not value.startswith(marker):
            raise ValueError(f'expected {kind} ID with {marker} prefix')
        try:
            body = uuid.UUID(value.removeprefix(marker))
        except ValueError as exc:
            raise ValueError(f'expected {kind} ID with UUID body') from exc
        if body.version != 7 or body.variant != uuid.RFC_4122:
            raise ValueError(f'expected {kind} ID with UUIDv7 body')
        return value


def _load_registry(path: Path = _REGISTRY_PATH) -> IdRegistry:
    try:
        payload = yaml.safe_load(path.read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f'cannot load ID kind registry: {path}') from exc
    if not isinstance(payload, dict) or payload.get('schema_version') != '1.0.0':
        raise ConfigurationError('invalid ID kind registry schema version')
    kinds = payload.get('kinds')
    if not isinstance(kinds, dict):
        raise ConfigurationError('ID kind registry kinds must be a mapping')
    return IdRegistry(kinds)


_REGISTRY = _load_registry()


def new_id(kind: str) -> str:
    return _REGISTRY.new(kind)


def validate_id(value: str, kind: str) -> str:
    return _REGISTRY.validate(value, kind)
