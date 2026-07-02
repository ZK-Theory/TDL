"""Deterministic compilation and two-stage context budget gates."""

from collections.abc import Iterable

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.context.errors import ContextBudgetExceeded
from research_system.context.models import (
    ContextCandidate,
    ContextProfile,
    SourceFragment,
)
from research_system.context.tokenizers import CountEvidence, ProviderCountEvidence
from research_system.errors import ArsError
from research_system.ids import new_id


def build_candidate(
    rendered: str,
    ordered: list[SourceFragment],
    mandatory: list[SourceFragment],
    evidence: CountEvidence,
) -> ContextCandidate:
    source_manifest = tuple(
        {
            "source_id": item.source_id,
            "revision": item.revision,
            "content_hash": item.content_hash,
            "mandatory": item.mandatory,
        }
        for item in ordered
    )
    mandatory_ids = {source.source_id for source in mandatory}
    mandatory_manifest = tuple(
        item for item in source_manifest if item["source_id"] in mandatory_ids
    )
    return ContextCandidate(
        context_candidate_id=new_id("context"),
        manifest_id=new_id("context"),
        content_hash=sha256_hex(rendered.encode("utf-8")),
        utf8_bytes=len(rendered.encode("utf-8")),
        reference_count=evidence.count,
        reference_counter_id=evidence.counter_id,
        rendered_content=rendered,
        source_ids=tuple(item["source_id"] for item in source_manifest),
        mandatory_source_ids=tuple(
            item["source_id"] for item in mandatory_manifest
        ),
        mandatory_hash=sha256_hex(canonical_bytes(list(mandatory_manifest))),
        source_manifest=source_manifest,
        conflicts=(),
        omissions={},
    )


def compile_candidate(
    fragments: Iterable[SourceFragment],
    profile: ContextProfile,
    reference_counter,
    required_source_ids: set[str],
) -> ContextCandidate:
    fragment_list = list(fragments)
    included_ids = {item.source_id for item in fragment_list}
    missing = set(required_source_ids) - included_ids
    if missing:
        raise ArsError(f"mandatory source omitted: {sorted(missing)}")
    ordered = sorted(
        fragment_list,
        key=lambda item: (-item.authority_rank, item.source_id, item.revision),
    )
    mandatory = [
        item for item in ordered if item.source_id in required_source_ids
    ]
    rendered = "\n\n".join(item.content for item in ordered)
    evidence = reference_counter.count(rendered)
    if evidence.units != "ars_reference_tokens":
        raise ArsError("invalid reference-token units")
    if evidence.count > profile.reference_limit:
        raise ContextBudgetExceeded("reference_token_gate")
    candidate = build_candidate(rendered, ordered, mandatory, evidence)
    candidate.validate_manifest(
        required_source_ids,
        included_ids,
        {item.source_id for item in ordered if not item.mandatory},
        candidate.omissions,
    )
    return candidate


def validate_provider_gate(
    candidate: ContextCandidate,
    evidence: ProviderCountEvidence,
    usable_capacity_tokens: int,
) -> ProviderCountEvidence:
    del candidate
    if evidence.units != "provider_tokens":
        raise ArsError("provider count must use provider_tokens")
    if (
        not evidence.counter_id
        or not evidence.provider
        or not evidence.model
        or not evidence.rendering_revision
        or not evidence.evidence_revision
    ):
        raise ArsError("provider count scope incomplete")
    limit = usable_capacity_tokens * 80 // 100
    if evidence.count > limit:
        raise ContextBudgetExceeded("bound_provider_capacity_gate")
    return evidence
