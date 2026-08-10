"""Owner-defined immutable context models."""

from dataclasses import dataclass, field

from research_system.errors import ArsError


@dataclass(frozen=True)
class SourceFragment:
    source_id: str
    revision: str
    authority_rank: int
    mandatory: bool
    content: str
    content_hash: str
    direct: bool = True
    current: bool = True
    superseded: bool = False
    sensitivity_class: str = "internal"


@dataclass(frozen=True)
class ContextProfile:
    profile_id: str
    reference_limit: int


@dataclass(frozen=True)
class ContextCandidate:
    context_candidate_id: str
    manifest_id: str
    content_hash: str
    utf8_bytes: int
    reference_count: int
    reference_counter_id: str
    state: str = "compiled"
    rendered_content: str = ""
    source_ids: tuple[str, ...] = ()
    mandatory_source_ids: tuple[str, ...] = ()
    mandatory_hash: str = ""
    source_manifest: tuple[dict, ...] = ()
    conflicts: tuple[str, ...] = ()
    omissions: dict[str, str] = field(default_factory=dict)

    def validate_manifest(
        self,
        required: set[str],
        included: set[str],
        optional_candidates: set[str],
        omissions: dict[str, str],
    ) -> None:
        missing = set(required) - set(included)
        if missing:
            raise ArsError(f"mandatory source omitted: {sorted(missing)}")
        invalid_omissions = set(omissions) - set(optional_candidates)
        if invalid_omissions:
            raise ArsError(f"non-optional omission: {sorted(invalid_omissions)}")
