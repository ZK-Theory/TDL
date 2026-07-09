"""Evidence-derived producer/reviewer relationship grading."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RelationshipEvidence:
    same_actor: bool
    same_session: bool
    same_context_hash: bool
    same_model_family: bool
    producer_conclusions_visible: bool


def independence_grade(evidence: RelationshipEvidence) -> str:
    """Return I0/I1/I2 without trusting nominal role labels."""
    if evidence.same_actor or evidence.same_session:
        return "I0"
    if evidence.same_context_hash or evidence.producer_conclusions_visible:
        return "I0"
    if evidence.same_model_family:
        return "I1"
    return "I2"
