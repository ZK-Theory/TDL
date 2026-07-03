from __future__ import annotations

import hashlib
import json
from typing import Any

_MAX_SAFE_INTEGER = (1 << 53) - 1


def _validate_p0_canonical_value(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key.isascii():
                raise ValueError('P0 canonical JSON requires ASCII object keys')
            _validate_p0_canonical_value(item)
        return
    if isinstance(value, list):
        for item in value:
            _validate_p0_canonical_value(item)
        return
    if isinstance(value, float):
        raise ValueError('P0 canonical JSON rejects floating-point values')
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, int):
        if not -_MAX_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER:
            raise ValueError('P0 canonical JSON requires the safe integer range')
        return
    raise TypeError(f'unsupported P0 canonical JSON value: {type(value).__name__}')


def canonical_bytes(value: Any) -> bytes:
    _validate_p0_canonical_value(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
        allow_nan=False,
    ).encode('utf-8')


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
