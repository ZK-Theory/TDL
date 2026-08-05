"""Research-assurance requirement primitives."""

from research_system.assurance.pack_loader import (
    AUTHORITY_RESOLUTION_PHASES,
    ContentAddressedAuthorityResolver,
    PackAcceptanceSubject,
    PackUnconsumable,
    git_blob_id,
    validate_tdl_private_pack_for_acceptance,
    validate_tdl_private_pack_for_preparation,
)
from research_system.assurance.resolver import (
    EXTERNAL_RECORD_KIND,
    ControlStoreAuthorityResolver,
)
from research_system.assurance.external_records import (
    ExternalRecordPublicationContext,
    ExternalRecordResolution,
)
from research_system.assurance.relationship_facts import (
    ProtectedRelationshipReference,
    RelationshipEvidenceFactsReceipt,
    RelationshipEvidenceFactsStore,
    RelationshipEvidenceParticipant,
)
from research_system.assurance.runner import (
    AssurancePackRunResult,
    AssurancePackRunnerConfig,
    SemanticRecordLocator,
    accept_assurance_pack,
    prepare_assurance_pack,
)


__all__ = [
    "AUTHORITY_RESOLUTION_PHASES",
    "EXTERNAL_RECORD_KIND",
    "ContentAddressedAuthorityResolver",
    "ControlStoreAuthorityResolver",
    "ExternalRecordPublicationContext",
    "ExternalRecordResolution",
    "ProtectedRelationshipReference",
    "RelationshipEvidenceFactsReceipt",
    "RelationshipEvidenceFactsStore",
    "RelationshipEvidenceParticipant",
    "PackAcceptanceSubject",
    "PackUnconsumable",
    "AssurancePackRunResult",
    "AssurancePackRunnerConfig",
    "SemanticRecordLocator",
    "accept_assurance_pack",
    "git_blob_id",
    "validate_tdl_private_pack_for_acceptance",
    "validate_tdl_private_pack_for_preparation",
    "prepare_assurance_pack",
]
