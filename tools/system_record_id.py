#!/usr/bin/env python3
"""Mint collision-resistant ULIDs for observation and handoff records."""

from __future__ import annotations

import argparse
import re
import secrets
import time

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
HANDOFF_SLUG_RE = re.compile(r"^[a-z0-9-]+$")


def mint_ulid(timestamp_ms: int | None = None, randomness: int | None = None) -> str:
    """Return a canonical 26-character Crockford-base32 ULID."""
    timestamp = int(time.time() * 1000) if timestamp_ms is None else timestamp_ms
    random_bits = secrets.randbits(80) if randomness is None else randomness
    if not 0 <= timestamp < 2**48 or not 0 <= random_bits < 2**80:
        raise ValueError("ULID timestamp or randomness is out of range")
    value = (timestamp << 80) | random_bits
    chars = ["0"] * 26
    for index in range(25, -1, -1):
        chars[index] = ALPHABET[value & 31]
        value >>= 5
    return "".join(chars)


def is_ulid(value: str) -> bool:
    return ULID_RE.fullmatch(value) is not None and value[0] <= "7"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff-slug", help="Emit <ULID>-<slug>.md instead of a bare ULID.")
    args = parser.parse_args()
    if args.handoff_slug is not None and HANDOFF_SLUG_RE.fullmatch(args.handoff_slug) is None:
        parser.error("--handoff-slug must contain only lowercase letters, digits, and hyphens")
    identifier = mint_ulid()
    print(f"{identifier}-{args.handoff_slug}.md" if args.handoff_slug else identifier)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
