"""Immutable-source model for the WP6.1 schema materializer.

This module intentionally obtains its authority from the reviewed Git object, not
from the mutable checkout or runtime registry.  It is pure: callers receive
ordinary dictionaries and canonical bytes, and decide whether to write them.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ANNEX_PATH = "docs/plans/agentic-research-system/implementation/06d-wp6-1-owner-source-catalogue.md"
ANNEX_REVISION = "fe5f1d40bc8f05f061317c677b5891cea0711249"
ANNEX_BLOB = "5e2eb60ca4419d1529506de6859fb027cff518af"
ANNEX_SHA256 = "96932fd752362eddb6da2da77bc0b56ccb8e83ced58e93c3b139e3248acb08f7"
TICK = chr(96)
ARROW = chr(0x2192)


@dataclass(frozen=True)
class SourceRow:
    """One exact owner row, normalized only after raw authority verification."""

    source_table: str
    key: str
    owner_transition: str
    command_event_identity: str
    command_token: str
    command_type: str
    events: tuple[tuple[str, str], ...]
    reducer_projection: str
    authority: str
    receipt_tests: str


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def canonical_yaml_bytes(value: Any) -> bytes:
    """Serialize committed YAML as UTF-8, LF-only, without a BOM."""
    import yaml

    text = yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=4096)
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def git_blob_id(repo_root: Path, data: bytes) -> str:
    """Ask Git for the raw, no-filter blob identity; never call hashlib.sha1."""
    result = subprocess.run(
        ["git", "hash-object", "--no-filters", "--stdin"],
        cwd=repo_root,
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout.decode("ascii").strip()


def approved_annex_bytes(repo_root: Path) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{ANNEX_REVISION}:{ANNEX_PATH}"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("approved WP6.1 06d object is unavailable")
    data = result.stdout
    if git_blob_id(repo_root, data) != ANNEX_BLOB:
        raise RuntimeError("approved WP6.1 06d Git blob mismatch")
    if hashlib.sha256(data).hexdigest() != ANNEX_SHA256:
        raise RuntimeError("approved WP6.1 06d SHA-256 mismatch")
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise RuntimeError("approved WP6.1 06d bytes are not UTF-8/LF canonical")
    return data


def _plain(value: str) -> str:
    return value.replace(TICK, "")


def _parse_rows(data: bytes) -> list[SourceRow]:
    lines = data.decode("utf-8").splitlines()
    section: str | None = None
    rows: list[SourceRow] = []
    for line in lines:
        if line.startswith("## 2. "):
            section = "w2_lifecycle"
        elif line.startswith("## 3. "):
            section = "w2_messages_governance"
        elif line.startswith("## 4. "):
            section = "w8_operator"
        elif line.startswith("## 5. "):
            section = None
        if section is None or not line.startswith(f"| {TICK}"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            continue
        parts = [_plain(item.strip()) for item in cells[2].split(";")]
        if len(parts) != 3:
            raise RuntimeError(f"malformed command/event cell for {cells[0]}")
        command_token, command_type = (item.strip() for item in parts[0].split(" / ", 1))
        events = [item.strip() for item in parts[1].strip("[]").split(",")]
        event_tokens = [item.strip() for item in parts[2].strip("[]").split(",")]
        if len(events) != len(event_tokens):
            raise RuntimeError(f"event/token mismatch for {cells[0]}")
        rows.append(
            SourceRow(
                source_table=section,
                key=_plain(cells[0]),
                owner_transition=cells[1],
                command_event_identity=cells[2],
                command_token=command_token,
                command_type=command_type,
                events=tuple(zip(events, event_tokens, strict=True)),
                reducer_projection=cells[3],
                authority=cells[4],
                receipt_tests=cells[5],
            )
        )
    if len(rows) != 104 or len({row.key for row in rows}) != 104:
        raise RuntimeError("approved WP6.1 06d row cardinality is not exactly 104")
    return rows


def source_rows(repo_root: Path) -> list[SourceRow]:
    """Return the 104 rows parsed from those same verified authority bytes."""
    return _parse_rows(approved_annex_bytes(repo_root))


def source_citation(row: SourceRow) -> str:
    section = {"w2_lifecycle": "06d §2 / W2", "w2_messages_governance": "06d §3 / W2", "w8_operator": "06d §4 / W8"}[
        row.source_table
    ]
    return f"{section}, owner row `{row.key}` at {ANNEX_REVISION}:{ANNEX_PATH}"


def snake(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def schema_identity(token: str, semantic_type: str, kind: str) -> dict[str, str]:
    suffix = token.split("/", 1)[1]
    if kind == "command":
        return {
            "schema_token": token,
            "command_schema_path": f".research-system/schemas/core/commands/{suffix}.schema.json",
            "command_schema_id": f"ars://core/command/{semantic_type}",
            "command_schema_version": "1.0.0",
        }
    return {
        "event_type": semantic_type,
        "schema_token": token,
        "event_schema_path": f".research-system/schemas/core/events/{suffix}.schema.json",
        "event_schema_id": f"ars://core/event/{semantic_type}",
        "event_schema_version": "1.0.0",
    }


def grouped_rows(rows: Iterable[SourceRow], *, kind: str) -> dict[str, list[tuple[SourceRow, str, str]]]:
    grouped: dict[str, list[tuple[SourceRow, str, str]]] = {}
    for row in rows:
        values = (
            [(row.command_token, row.command_type)]
            if kind == "command"
            else [(event_token, event_type) for event_type, event_token in row.events]
        )
        for token, semantic_type in values:
            path = schema_identity(token, semantic_type, kind)[f"{kind}_schema_path"]
            grouped.setdefault(path, []).append((row, token, semantic_type))
    return grouped
