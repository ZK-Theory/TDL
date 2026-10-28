"""Externally accepted W9 envelope identity.

These are the protected identities that W9 genesis imports exactly once: the W9 expected catalogue and its owner annex
as Stephen accepted them at O-8 (P-075), the bootstrap contract as he accepted it at O-3 (P-078), and the acceptance
envelope that records O-8 (WP9.2-1). They live in their own leaf module, as ``discovery/accepted_w11.py`` does: nothing
here may depend on lifecycle, replay or preparation behaviour, and every other legacy module reads them rather than
restating them.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

ACCEPTED = MappingProxyType(
    {
        "accepted_commit": "7979e85a075ab6a643a7b201ac4186b0b2090d74",
        "accepted_tree": "d6746b4d583f3f6e1beefd74723290ac30e5fa3f",
        "catalogue_path": ".research-system/evals/expected/w9-legacy-integration-v1.json",
        "catalogue_blob": "d1916ffd380050f193fb2c927bb4d724cd2f8a88",
        "catalogue_bytes": 128583,
        "catalogue_sha256": "f7e2d9e2deac022790c296a4962ea3feb7feb1e646da125edf7819ff8719db8c",
        "content_hash": "fd94dc94f309106ab5b3f84513b450525eaf23678c1896f7b623dd33681e5676",
        "annex_path": "docs/plans/agentic-research-system/transition/w9/wp9-1-catalogue-owner-annex.yaml",
        "annex_blob": "d8fbda416b016f5e19c03689f336caff3166d0d9",
        "annex_bytes": 85664,
        "annex_sha256": "36a3d1ac945930ae68a24059fc4be1a7f90050ff99a4038fd41853e01a3536fc",
        "owner_row_multiset_hash": "a80788184c02b5baa9ea47cf2f1a254f4f14499188e6a0dcbef8d083072ffde7",
        "bootstrap_path": ".research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml",
        "bootstrap_commit": "69e9e059348baad153884f43b34ee6c52df63add",
        "bootstrap_blob": "6bbbb14a6754b64209bab5e50aa8e552bf71b63d",
        "bootstrap_bytes": 4164,
        "bootstrap_sha256": "47699ed77c1934ee6764f514e6aecf3ddad3349819106d030b600020c964ddb1",
        "envelope_path": ".research-system/evals/expected/w9-catalogue-acceptance-envelope-v1.json",
        "envelope_commit": "69e9e059348baad153884f43b34ee6c52df63add",
        "envelope_blob": "9b28528c119ef45244b277ccd30855c68826e41f",
        "envelope_bytes": 11185,
        "envelope_sha256": "c26f468c9cfa0195d82812f05faa4e6e663a3ceb9737d31f8f5f1bd190465999",
        "gate6_store_identity": "5e3b95a956a8a416accd697f250088b5c8723924eb68544f01064ede6eb18d69",
        "owner_decision": (
            "I accept O-8: the W9 catalogue (blob d1916ffd, SHA-256 f7e2d9e2…db8c) and the owner annex (blob d8fbda41,"
            " SHA-256 36a3d1ac…36fc) at main commit 7979e85a. Record the acceptance."
        ),
    }
)
# The three out-of-store records the envelope cites (P-077 item 2; design note §5.3). Genesis reserves their IDs, and
# the W9 identity check refuses any pre-assigned ID equal to one of them (W9-C25). No reader dereferences them.
RESERVED_EXTERNAL_REFS = MappingProxyType(
    {
        "observation": MappingProxyType(
            {
                "id": "obj_01a17eb7-5ae0-7071-b0bf-bacc039a26ce",
                "domain": "w9-external:observation:P-075:docs/plans/agentic-research-system/"
                "03-decisions-and-open-questions.md@eab253f695bd2b834c2dfa3a1d42b7a38584207c",
            }
        ),
        "review": MappingProxyType(
            {
                "id": "rev_01a17eb7-5ae0-778e-8617-52ef7a4f7665",
                "domain": "w9-external:review:B2-confirmation:docs/plans/agentic-research-system/reviews/"
                "wp9-1-stage-b2-confirmation-3241f0e9-2026-10-27.md@7979e85a075ab6a643a7b201ac4186b0b2090d74",
            }
        ),
        "decision": MappingProxyType(
            {
                "id": "dec_01a17eb7-5ae0-7e7b-9f86-bc9d2f8b07ab",
                "domain": "w9-external:decision:P-075:docs/plans/agentic-research-system/"
                "03-decisions-and-open-questions.md@eab253f695bd2b834c2dfa3a1d42b7a38584207c",
            }
        ),
    }
)
RESERVED_IDS = frozenset(ref["id"] for ref in RESERVED_EXTERNAL_REFS.values())
ROW_IDS = tuple(f"LR-{number:03d}" for number in range(1, 62))
# Accepted catalogue revisions LR-002 may import. Inert in v1: none exists (P-071 item 4; P-072 item 5).
ACCEPTED_REVISIONS: tuple[MappingProxyType[str, Any], ...] = ()
CATALOGUE_STREAM_ID = "obj_01a17eb7-5ae0-7000-8000-000000000001"
# The nominal request string the closed genesis schema requires. It is not a ledger transaction ID and carries no
# ``txb_`` prefix; retries are answered from receipts (design note §5.2; confirmation n-2).
REQUESTED_GENESIS_TRANSACTION_ID = "w9-genesis-request-v1"
REQUIRED_W11_CATALOGUE = MappingProxyType(
    {
        "repository_path": ".research-system/evals/expected/w11-portfolio-discovery-v1.json",
        "git_blob": "8d58818540e04859f929d4b04c71e4cfa0512554",
        "raw_sha256": "7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80",
        "raw_bytes": 136229,
    }
)
# The accepted contract's verification_rules, verbatim (O-3, P-078). Genesis re-hashes the contract bytes, so these
# cannot drift from the file without the bytes changing too.
VERIFICATION_REQUIREMENTS = (
    "the accepted W9 and 06v raw-byte tuples are independently observed at their pinned commits and at the checked-out"
    " HEAD",
    "the W9 runtime cannot produce or accept its own prerequisite",
    "restricted_suffixes is a copy of the D-9 list and changes with it under the same reviewed PR (P-069 item 3)",
    "every W9 schema is reproduced byte for byte by tools/w9_schema_gen.py",
    "every materialized schema is Draft 2020-12 valid, closed at the top level, and carries schema_id equal to its $id",
    "every W9 schema id is under ars://legacy/ and none collides with ars://portfolio/ or ars://core/",
    "ars://legacy/ schema ids remain absent from runtime bindings; the W9 runtime validates content through the registry",
    "the accepted W11 schema tree, route partition and catalogue are unchanged",
    "the only W9 expected catalogue instance is .research-system/evals/expected/w9-legacy-integration-v1.json, and"
    " tools/verify_w9_materialization.py --require-catalogue verifies it",
    "the only W9 acceptance envelope instance is .research-system/evals/expected/w9-catalogue-acceptance-envelope-v1.json",
    "runtime_activation and materialization_status govern the ars://legacy/ schemas' runtime bindings only; the W9"
    " runtime is WP9.2's (P-077)",
    "the W9 genesis requires a store whose replayed Discovery projection holds the accepted W11 catalogue",
    "the W9 genesis refuses every store identity listed in refused_store_identities, read before binding",
)


def _file_identity(prefix: str) -> dict[str, Any]:
    return {
        "repository_path": ACCEPTED[f"{prefix}_path"],
        "git_commit": ACCEPTED[f"{prefix}_commit"],
        "git_blob": ACCEPTED[f"{prefix}_blob"],
        "file_length": ACCEPTED[f"{prefix}_bytes"],
        "file_sha256": ACCEPTED[f"{prefix}_sha256"],
    }


def accepted_genesis_payload() -> dict[str, Any]:
    """Return the exact closed genesis record (``ars://legacy/import-accepted-w9-catalogue-genesis`` 1.0.0).

    Returns:
        A fresh copy of the one genesis payload this code admits, field by field as design note §5.2 fixes it.
    """

    return {
        "schema_id": "ars://legacy/import-accepted-w9-catalogue-genesis",
        "schema_version": "1.0.0",
        "bootstrap_contract_identity": _file_identity("bootstrap"),
        "external_envelope_identity": _file_identity("envelope"),
        "requested_genesis_transaction_id": REQUESTED_GENESIS_TRANSACTION_ID,
        "required_w11_catalogue": dict(REQUIRED_W11_CATALOGUE),
        "refused_store_identities": [ACCEPTED["gate6_store_identity"]],
        "verification_requirements": list(VERIFICATION_REQUIREMENTS),
        "activation_status": "not_executed",
    }
