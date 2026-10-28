# Research context: docs/plans/agentic-research-system/transition/w9/wp9-2-design-note.md (WP9.2-1; P-075, P-077)
# Purpose: derive the W9 catalogue acceptance envelope from its pinned sources and pin the committed instance to it.
"""Controls for the W9 catalogue acceptance envelope (WP9.2-1).

The envelope records what Stephen's O-8 acceptance (P-075) rested on. Every field is derived here from Git at a
pinned commit, so the committed instance is checked against an independent expected side (design note §5.3):
- the catalogue, the annex, the bootstrap contract, the generator, the verifier and the binding tests, at the
  accepted commit ``7979e85a``;
- the specification, plan and schema identities, verbatim from the accepted catalogue;
- ``owner_row_multiset_hash`` over the catalogue's owner rows (P-077 item 3);
- three reserved external refs for the out-of-store observation, review and decision (P-077 item 2).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from research_system.canonical import canonical_bytes

REPO_ROOT = Path(__file__).resolve().parents[3]
ENVELOPE_PATH = ".research-system/evals/expected/w9-catalogue-acceptance-envelope-v1.json"
ENVELOPE_SCHEMA = ".research-system/schemas/contracts/w9/w9-catalogue-acceptance-envelope.schema.json"
CATALOGUE_PATH = ".research-system/evals/expected/w9-legacy-integration-v1.json"
CONTRACT_PATH = ".research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml"
GENERATOR_PATH = "tools/w9_schema_gen.py"
VERIFIER_PATH = "tools/verify_w9_materialization.py"
BINDING_TEST_PATHS = (
    "tests/research_system/contracts/test_w9_expected_catalogue.py",
    "tests/research_system/contracts/test_w9_contract_materialization.py",
)
REGISTER_PATH = "docs/plans/agentic-research-system/03-decisions-and-open-questions.md"
CONFIRMATION_PATH = "docs/plans/agentic-research-system/reviews/wp9-1-stage-b2-confirmation-3241f0e9-2026-10-27.md"

ACCEPTED_COMMIT = "7979e85a075ab6a643a7b201ac4186b0b2090d74"  # PR #396's merge; O-8 accepts the catalogue here
P075_COMMIT = "eab253f695bd2b834c2dfa3a1d42b7a38584207c"  # PR #404's merge; records P-075 on main
ACCEPTED_AT = "2026-10-27T18:55:08Z"  # the author and committer time of P075_COMMIT (design note §5.3)
ACCEPTED_AT_MS = 1793127308000
ACCEPTANCE_SCOPE = "O-8: the W9 expected catalogue and its owner annex at main commit 7979e85a (P-075)"

# Owner-accepted values, as literals, so the derivation below has an independent expected side.
P077_MULTISET_HASH = "a80788184c02b5baa9ea47cf2f1a254f4f14499188e6a0dcbef8d083072ffde7"
O8_CONTRACT_BLOB = "96a63114dbf94d3efa8019e18d8208832eee833d"  # P-075: "the envelope cites the merged contract"
RESERVED_REF_IDS = {
    "observation": "obj_01a17eb7-5ae0-7071-b0bf-bacc039a26ce",
    "review": "rev_01a17eb7-5ae0-778e-8617-52ef7a4f7665",
    "decision": "dec_01a17eb7-5ae0-7e7b-9f86-bc9d2f8b07ab",
}
# (kind, ID prefix, entry, repository path, commit) for each reserved ref (design note §5.3).
EXTERNAL_REFS = {
    "observation": ("obj", "P-075", REGISTER_PATH, P075_COMMIT),
    "review": ("rev", "B2-confirmation", CONFIRMATION_PATH, ACCEPTED_COMMIT),
    "decision": ("dec", "P-075", REGISTER_PATH, P075_COMMIT),
}


@lru_cache(maxsize=None)
def _verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_w9_verify_envelope", REPO_ROOT / VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, check=True, text=True).stdout.strip()


@lru_cache(maxsize=None)
def _git_bytes(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=REPO_ROOT, capture_output=True, check=True).stdout


def _file_identity(commit: str, path: str) -> dict[str, Any]:
    data = _git_bytes(commit, path)
    return {
        "repository_path": path,
        "git_commit": commit,
        "git_blob": _git("rev-parse", f"{commit}:{path}"),
        "file_length": len(data),
        "file_sha256": hashlib.sha256(data).hexdigest(),
    }


def external_ref_id(prefix: str, kind: str, entry: str, path: str, commit: str) -> str:
    """Derive one reserved external ref ID as a valid UUIDv7 (design note §5.3, P-077 item 2).

    The 48-bit timestamp is ``ACCEPTED_AT`` in milliseconds. ``rand_a`` is the first 12 bits, and ``rand_b`` the next
    62 bits, of the SHA-256 of ``w9-external:<kind>:<entry>:<path>@<commit>``.
    """
    digest = int.from_bytes(hashlib.sha256(f"w9-external:{kind}:{entry}:{path}@{commit}".encode()).digest(), "big")
    rand_a = digest >> (256 - 12)
    rand_b = (digest >> (256 - 12 - 62)) & ((1 << 62) - 1)
    value = (ACCEPTED_AT_MS << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return f"{prefix}_{uuid.UUID(int=value)}"


def _external_ref(kind: str) -> dict[str, Any]:
    prefix, entry, path, commit = EXTERNAL_REFS[kind]
    return {
        "id": external_ref_id(prefix, kind, entry, path, commit),
        "record_revision": 1,
        "content_hash": hashlib.sha256(_git_bytes(commit, path)).hexdigest(),
    }


@lru_cache(maxsize=None)
def _accepted_catalogue() -> dict[str, Any]:
    return json.loads(_git_bytes(ACCEPTED_COMMIT, CATALOGUE_PATH))


def expected_envelope() -> dict[str, Any]:
    """Derive the envelope from its pinned sources (design note §5.3)."""
    catalogue = _accepted_catalogue()
    return {
        "schema_id": "ars://legacy/w9-catalogue-acceptance-envelope",
        "schema_version": "1.0.0",
        "specification_identity": catalogue["owner_spec_identity"],
        "plan_identity": catalogue["owner_plan_identity"],
        "catalogue_identity": _file_identity(ACCEPTED_COMMIT, CATALOGUE_PATH),
        "owner_annex_identity": catalogue["owner_annex_identity"],
        "schema_identities": catalogue["schema_source_rows"],
        "owner_row_multiset_hash": _verifier().owner_row_multiset_hash(catalogue["owner_contract_rows"]),
        "bootstrap_contract_identity": _file_identity(ACCEPTED_COMMIT, CONTRACT_PATH),
        "schema_generator_identity": _file_identity(ACCEPTED_COMMIT, GENERATOR_PATH),
        "verifier_identity": _file_identity(ACCEPTED_COMMIT, VERIFIER_PATH),
        "binding_test_identities": [_file_identity(ACCEPTED_COMMIT, path) for path in BINDING_TEST_PATHS],
        "independent_observation_ref": _external_ref("observation"),
        "independent_review_ref": _external_ref("review"),
        "acceptance_decision_ref": _external_ref("decision"),
        "accepted_at": ACCEPTED_AT,
        "acceptance_scope": ACCEPTANCE_SCOPE,
    }


def _committed() -> bytes:
    return (REPO_ROOT / ENVELOPE_PATH).read_bytes()


def _valid(instance: dict[str, Any]) -> bool:
    schema = json.loads((REPO_ROOT / ENVELOPE_SCHEMA).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).is_valid(instance)


# --- The committed instance -----------------------------------------------------------------------------------------


def test_committed_envelope_is_the_derived_envelope() -> None:
    data = _committed()
    assert b"\n" not in data  # canonical JSON is one line, so encoding drift shows up as an added line ending
    assert data == canonical_bytes(expected_envelope())


def test_committed_envelope_validates_against_its_schema() -> None:
    assert _valid(json.loads(_committed()))


def test_byte_identity_refuses_what_the_schema_admits() -> None:
    # The schema checks shape only; the byte test is what binds the values (as m-2 did for the catalogue).
    tampered = json.loads(_committed())
    tampered["owner_row_multiset_hash"] = "0" * 64
    assert _valid(tampered)
    assert canonical_bytes(tampered) != canonical_bytes(expected_envelope())
    re_encoded = json.dumps(json.loads(_committed()), indent=2, sort_keys=True).encode()
    assert re_encoded != canonical_bytes(expected_envelope())


# --- The values against owner-accepted literals ---------------------------------------------------------------------


def test_owner_row_multiset_hash_is_p077s_value() -> None:
    assert expected_envelope()["owner_row_multiset_hash"] == P077_MULTISET_HASH
    # P-077 item 3 chose the catalogue's rows; the annex rows give a different value (B2 review i-3).
    annex_hashes = sorted(row["owner_annex_ref"]["row_sha256"] for row in _accepted_catalogue()["owner_contract_rows"])
    assert hashlib.sha256(canonical_bytes(annex_hashes)).hexdigest() != P077_MULTISET_HASH


def test_envelope_cites_the_contract_o8_rested_on_not_the_amended_one() -> None:
    cited = expected_envelope()["bootstrap_contract_identity"]
    assert cited["git_blob"] == O8_CONTRACT_BLOB
    assert _git("hash-object", CONTRACT_PATH) != O8_CONTRACT_BLOB  # WP9.2-1 amends the checked-out contract


def test_catalogue_identity_is_o8s() -> None:
    assert expected_envelope()["catalogue_identity"] == {
        "repository_path": CATALOGUE_PATH,
        "git_commit": ACCEPTED_COMMIT,
        "git_blob": "d1916ffd380050f193fb2c927bb4d724cd2f8a88",
        "file_length": 128583,
        "file_sha256": "f7e2d9e2deac022790c296a4962ea3feb7feb1e646da125edf7819ff8719db8c",
    }


# --- The reserved external refs (P-077 item 2) ----------------------------------------------------------------------


def test_accepted_at_is_p075s_main_commit_time() -> None:
    assert _git("log", "-1", "--format=%cI", P075_COMMIT).replace("+00:00", "Z") == ACCEPTED_AT
    assert int(datetime.fromisoformat(ACCEPTED_AT).replace(tzinfo=UTC).timestamp() * 1000) == ACCEPTED_AT_MS


@pytest.mark.parametrize("kind", sorted(EXTERNAL_REFS))
def test_reserved_ref_is_the_pinned_uuidv7(kind: str) -> None:
    ref = _external_ref(kind)
    assert ref["id"] == RESERVED_REF_IDS[kind]
    value = uuid.UUID(ref["id"].split("_", 1)[1])
    assert value.version == 7
    assert value.variant == uuid.RFC_4122
    assert value.int >> 80 == ACCEPTED_AT_MS


@pytest.mark.parametrize("kind", sorted(EXTERNAL_REFS))
def test_reserved_ref_hashes_its_named_file(kind: str) -> None:
    _, entry, path, commit = EXTERNAL_REFS[kind]
    data = _git_bytes(commit, path)
    assert _external_ref(kind)["content_hash"] == hashlib.sha256(data).hexdigest()
    if entry == "P-075":
        assert b"### P-075 - O-8:" in data


def test_reserved_ref_ids_are_distinct_and_domain_bound() -> None:
    assert len(set(RESERVED_REF_IDS.values())) == 3
    prefix, entry, path, commit = EXTERNAL_REFS["decision"]
    assert external_ref_id(prefix, "decision", entry, path, P075_COMMIT[:39] + "0") != RESERVED_REF_IDS["decision"]
    assert external_ref_id(prefix, "observation", entry, path, commit) != RESERVED_REF_IDS["decision"]


def test_a_changed_ref_breaks_the_envelope() -> None:
    envelope = deepcopy(expected_envelope())
    envelope["acceptance_decision_ref"]["id"] = external_ref_id("dec", "decision", "P-076", REGISTER_PATH, P075_COMMIT)
    assert _valid(envelope)
    assert canonical_bytes(envelope) != _committed()
