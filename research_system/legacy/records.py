"""W9 record identity rules (WP9.3 design note §4.1, §4.2, §5.2, §5.3).

One module computes every value the preparers stamp and replay recomputes, so the two can never disagree:

- the record content hash (N-2): SHA-256 of ``canonical_bytes`` over the record without ``content_hash``, the rule the
  accepted owner annex fixes (``wp9-1-catalogue-owner-annex.yaml:19``);
- the pre-assigned ref hash (owner point M): a review or Decision ref a proposal carries before that review or
  Decision exists hashes ``{"w9_pre_assigned": kind, "id": ..., "record_id": ...}``, so it depends on no hash;
- derived UUIDv7 identities, built as WP9.2's reserved external refs are (WP9.2 note §5.3, steps 2 to 5): the review
  context and attempt IDs of a verdict (§5.2), and an observation's ``record_id`` (§5.3).

It is a leaf: it imports nothing from :mod:`research_system.legacy` but the accepted constants.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError

# The preparer-set fields of a record a command creates (§5.1). A payload that supplies one is refused.
PREPARER_SET_FIELDS = frozenset({"created_by_actor_id", "created_at", "content_hash"})
OBSERVATION_PREPARER_SET_FIELDS = PREPARER_SET_FIELDS | {"observed_at"}
# The read-derived fields of an observation (§5.1): a function of the bytes, filled by the preparer from its own read.
OBSERVATION_READ_DERIVED_FIELDS = frozenset({"source_identity", "file_facts", "importer", "record_id"})


def record_content_hash(record: Mapping[str, Any]) -> str:
    """Return a W9 record's content hash: SHA-256 of ``canonical_bytes`` over the record without ``content_hash``.

    Args:
        record: A W9 record, with or without its ``content_hash`` field.

    Returns:
        The lowercase hexadecimal SHA-256.

    Raises:
        IntegrityError: If the record is not a P0-canonical object.
    """

    if not isinstance(record, Mapping):
        raise IntegrityError("W9 record must be an object")
    body = {key: value for key, value in record.items() if key != "content_hash"}
    try:
        return sha256_hex(canonical_bytes(body))
    except (TypeError, ValueError) as exc:
        raise IntegrityError("W9 record is not P0-canonical") from exc


def require_content_hash(record: Mapping[str, Any]) -> str:
    """Recompute a record's content hash and refuse a record whose declared value differs (§4.1).

    Returns:
        The recomputed hash.

    Raises:
        IntegrityError: If the declared ``content_hash`` is not the recomputed one.
    """

    recomputed = record_content_hash(record)
    if record.get("content_hash") != recomputed:
        raise IntegrityError("W9 record content_hash is not the hash of its content")
    return recomputed


def pre_assigned_ref_hash(kind: Literal["review", "decision"], ref_id: str, record_id: str) -> str:
    """Return the ``content_hash`` of a pre-assigned review or Decision ref (§4.2; owner point M).

    Args:
        kind: ``review`` or ``decision``.
        ref_id: The pre-assigned ``rev_`` or ``dec_`` ID.
        record_id: The record ID of the proposal that pre-assigns it.

    Returns:
        SHA-256 of ``canonical_bytes`` over ``{"w9_pre_assigned": kind, "id": ref_id, "record_id": record_id}``.
    """

    if kind not in {"review", "decision"}:
        raise IntegrityError("W9 pre-assigned ref kind is invalid")
    return sha256_hex(canonical_bytes({"w9_pre_assigned": kind, "id": ref_id, "record_id": record_id}))


def pre_assigned_ref(kind: Literal["review", "decision"], ref_id: str, record_id: str) -> dict[str, Any]:
    """Return the complete pre-assigned ref object (``record_revision`` 1 and §4.2's hash)."""

    return {"id": ref_id, "record_revision": 1, "content_hash": pre_assigned_ref_hash(kind, ref_id, record_id)}


def utc_milliseconds(value: Any) -> int:
    """Return an RFC 3339 UTC timestamp ending in ``Z`` as whole milliseconds since the epoch.

    Raises:
        IntegrityError: If the value is not a UTC timestamp ending in ``Z``.
    """

    if not isinstance(value, str) or not value.endswith("Z"):
        raise IntegrityError("W9 timestamp must be UTC and end in Z")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise IntegrityError("W9 timestamp is not RFC 3339") from exc
    delta = parsed.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86_400 + delta.seconds) * 1000 + delta.microseconds // 1000


def derived_id(prefix: str, domain: str, timestamp_ms: int) -> str:
    """Derive a UUIDv7 ID from a domain string and a millisecond timestamp (WP9.2 note §5.3, steps 2 to 5).

    ``d`` is the SHA-256 of the domain's UTF-8 bytes; ``rand_a`` is its first 12 bits and ``rand_b`` its next 62.

    Args:
        prefix: The ID kind prefix, for example ``obj``.
        domain: The domain string.
        timestamp_ms: The 48-bit ``unix_ts_ms``.

    Returns:
        ``<prefix>_<uuid>``, a version 7, variant ``10`` UUID.
    """

    if not 0 <= timestamp_ms < 1 << 48:
        raise IntegrityError("W9 derived ID timestamp is outside the 48-bit range")
    digest = int.from_bytes(hashlib.sha256(domain.encode("utf-8")).digest(), "big")
    rand_a = digest >> (256 - 12)
    rand_b = (digest >> (256 - 12 - 62)) & ((1 << 62) - 1)
    value = (timestamp_ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return f"{prefix}_{uuid.UUID(int=value)}"


def review_context_manifest_id(review_id: str, requested_at: str) -> str:
    """The verdict's ``context_manifest_id``: ``ctx_`` from ``w9-review-context:<review ID>`` (§5.2)."""

    return derived_id("ctx", f"w9-review-context:{review_id}", utc_milliseconds(requested_at))


def review_attempt_id(review_id: str, requested_at: str) -> str:
    """The verdict's ``producing_attempt_id``: ``att_`` from ``w9-review-attempt:<review ID>`` (§5.2)."""

    return derived_id("att", f"w9-review-attempt:{review_id}", utc_milliseconds(requested_at))


def observation_subject_digest(record: Mapping[str, Any]) -> str:
    """Return the digest of LR-015's full authority subject for one observation record (§5.3).

    The subject is the registration, the source identity, the selector and the importer tool identity.
    """

    registration = record.get("registration_ref")
    importer = record.get("importer")
    if not isinstance(registration, Mapping) or not isinstance(importer, Mapping):
        raise IntegrityError("W9 observation subject is incomplete")
    subject = {
        "w9_observation_subject": {
            "registration_id": registration.get("id"),
            "source_identity": record.get("source_identity"),
            "selector": record.get("selector"),
            "importer_tool": {key: importer.get(key) for key in ("tool_id", "tool_version", "tool_sha256")},
        }
    }
    try:
        return sha256_hex(canonical_bytes(subject))
    except (TypeError, ValueError) as exc:
        raise IntegrityError("W9 observation subject is not P0-canonical") from exc


def observation_record_id(
    registration_id: str, subject_digest: str, observation_count: int, registration_created_at: str
) -> str:
    """Return an observation's derived ``record_id`` (§5.3).

    Args:
        registration_id: The registration record's ID.
        subject_digest: :func:`observation_subject_digest` of the observation.
        observation_count: ``n``, the observations of that registration already in the ledger.
        registration_created_at: The registration record's ``created_at``, the ID's timestamp.

    Returns:
        An ``obj_`` UUIDv7 from ``w9-observation:<registration ID>:<subject digest>:<n>``.
    """

    if isinstance(observation_count, bool) or not isinstance(observation_count, int) or observation_count < 0:
        raise IntegrityError("W9 observation count is invalid")
    return derived_id(
        "obj",
        f"w9-observation:{registration_id}:{subject_digest}:{observation_count}",
        utc_milliseconds(registration_created_at),
    )


def w0_signature_ref_id(domain: str, accepted_at: str, suffix: int | None = None) -> str:
    """Derive a pinned W0 signature ref, a ``dec_`` from its register entry's domain (§9.1).

    A collision found by the pre-pin check re-derives it with ``#<n>``, using the next unused ``n``.
    """

    if suffix is not None and (isinstance(suffix, bool) or not isinstance(suffix, int) or suffix < 1):
        raise IntegrityError("W9 signature ref suffix is invalid")
    return derived_id("dec", domain if suffix is None else f"{domain}#{suffix}", utc_milliseconds(accepted_at))
