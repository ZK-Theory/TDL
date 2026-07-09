"""Owner-defined immutable assurance models."""

from dataclasses import dataclass


CORE_LANES = frozenset(
    {
        "topology",
        "stochastic_null",
        "statistical_panel",
        "representation",
        "output_provenance",
        "paper_claim",
    }
)


@dataclass(frozen=True)
class LaneRequirement:
    lane: str
    disposition: str
    rationale: str
    governing_ref_hashes: tuple[str, ...]
    proof_obligation_ids: tuple[str, ...]
    reviewer_capabilities: tuple[str, ...]
    failure_consequence: str


@dataclass(frozen=True)
class AssuranceRequirement:
    assurance_requirement_id: str
    revision: int
    content_hash: str
    task_id: str
    task_revision: int
    purpose: str
    source_position: int
    owner_actor_id: str
    author_actor_id: str
    scope_reviewer_actor_id: str
    accepting_actor_id: str
    prospective_producer_actor_id: str
    prospective_producer_profile_id: str
    requested_risk: str
    w5_epistemic_risk_floor: str
    action_semantic_risk: str
    requirement_relationship_grade: str
    lanes: tuple[LaneRequirement, ...]
    human_gate_ids: tuple[str, ...]
    currency_hash: str
