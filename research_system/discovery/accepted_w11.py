"""Externally accepted W11 envelope identity.

These are the protected identities of the owner-accepted W11 portfolio and
discovery catalogue.  They are the one durable subject that Discovery genesis
imports exactly once, so they live in their own leaf module: nothing here may
depend on lifecycle, replay, or preparation behaviour, and every other Discovery
module reads them rather than restating them.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any


ACCEPTED = MappingProxyType(
    {
        "accepted_commit": "09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6",
        "accepted_tree": "151e0f8b24ad76913640aa0f1de66cd177a44f8f",
        "catalogue_blob": "8d58818540e04859f929d4b04c71e4cfa0512554",
        "catalogue_bytes": 136229,
        "catalogue_sha256": "7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80",
        "bootstrap_blob": "aac7242072c3ce62370dd74d9a27a29e1a33070d",
        "bootstrap_sha256": "ebb7529a3bbf8faea9101b1556b3b71e6e0b3b9dbe0df163591466903d569d38",
        "review_commit": "bd61f00d05191de1fd330e997d33ba74ac1b506c",
        "review_blob": "2e0deee51e526cc712c6b04a79695abaa4fb6442",
        "review_sha256": "beb96faa0b58d3ba5faf326b94bb7bc7e1d6649b00c577f2239e1083fe09eaf9",
        "owner_decision": "I accept the KAN 84 envelope, proceed.",
    }
)
ROW_IDS = tuple([*(f"OR-{number:03d}" for number in range(1, 42)), *(f"OR-{number:03d}" for number in range(101, 141))])
CATALOGUE_STREAM_ID = "obj_019fed25-b33e-7740-b280-000000000001"


def accepted_genesis_payload() -> dict[str, Any]:
    """Return the exact durable payload for the externally accepted W11 envelope."""

    return {
        "accepted_commit": ACCEPTED["accepted_commit"],
        "accepted_tree": ACCEPTED["accepted_tree"],
        "catalogue_blob": ACCEPTED["catalogue_blob"],
        "catalogue_bytes": ACCEPTED["catalogue_bytes"],
        "catalogue_sha256": ACCEPTED["catalogue_sha256"],
        "bootstrap_blob": ACCEPTED["bootstrap_blob"],
        "bootstrap_sha256": ACCEPTED["bootstrap_sha256"],
        "review_commit": ACCEPTED["review_commit"],
        "review_blob": ACCEPTED["review_blob"],
        "review_sha256": ACCEPTED["review_sha256"],
        "owner_row_id": "OR-140",
        "row_count": 81,
        "row_ids": list(ROW_IDS),
    }
