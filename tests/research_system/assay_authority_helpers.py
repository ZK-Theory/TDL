from __future__ import annotations

import json
from pathlib import Path

from research_system.canonical import canonical_bytes, sha256_hex


ASSAY_RUBRIC_PATH = Path(".research-system/contracts/wp6-6/assay-rubric-content-v1.json")
ASSAY_SCOPE_PATH = Path(".research-system/contracts/wp6-6/assay-evidence-scope-content-v1.json")
ROUTE_PATH = Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json")
SPEC_01_PATH = Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md")

SCOPE_HASH_FIELDS = (
    "scope_id",
    "rubric_ref",
    "required_assurance_lanes",
    "evidence_rows",
    "prohibited_source_classes",
    "prohibited_producer_relationships",
    "no_compensation_pairs",
    "confidentiality_rules",
    "stop_conditions",
    "partial_conditions",
    "evidence_order_constraints",
    "scope_closure_algorithm_id",
    "scope_closure_algorithm_version",
    "effective_candidate_kinds",
    "effective_project_scope_ref",
)


def bind_assay_fixture_to_current_spec_sources(repository_root: Path) -> None:
    """Rebind copied test authority content to the fixture's committed SPEC sources."""

    route_sha256 = sha256_hex((repository_root / ROUTE_PATH).read_bytes())
    spec_01_sha256 = sha256_hex((repository_root / SPEC_01_PATH).read_bytes())
    rubric_path = repository_root / ASSAY_RUBRIC_PATH
    scope_path = repository_root / ASSAY_SCOPE_PATH
    rubric = json.loads(rubric_path.read_bytes())
    scope = json.loads(scope_path.read_bytes())

    for content in (rubric, scope):
        for source_ref in content["source_refs"]:
            if source_ref.get("id") == "SPEC-01":
                source_ref["content_hash"] = spec_01_sha256
            elif source_ref.get("id") == "SPEC-GATE6-RUN-V1":
                source_ref["content_hash"] = route_sha256
        content["effective_project_scope_ref"]["content_hash"] = route_sha256
    for authority_ref in rubric["source_authority_refs"]:
        if authority_ref["id"] == "SPEC-01":
            authority_ref["content_hash"] = spec_01_sha256
        elif authority_ref["id"] == "SPEC-GATE6-RUN-V1":
            authority_ref["content_hash"] = route_sha256
    rubric["content_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in rubric.items() if key != "content_hash"})
    )
    scope["rubric_ref"]["content_hash"] = rubric["content_hash"]
    scope["scope_closure_algorithm_hash"] = sha256_hex(
        canonical_bytes({field: scope[field] for field in SCOPE_HASH_FIELDS})
    )
    scope["content_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in scope.items() if key != "content_hash"})
    )
    rubric_path.write_bytes(canonical_bytes(rubric) + b"\n")
    scope_path.write_bytes(canonical_bytes(scope) + b"\n")
