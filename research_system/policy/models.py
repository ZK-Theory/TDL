"""Immutable canonical policy models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Control:
    control_id: str
    semantic_class: str
    critical: bool
    failure_mode: str


@dataclass(frozen=True)
class CanonicalPolicyBundle:
    canonical_policy_bundle_id: str
    revision: str
    content_hash: str
    controls: tuple[Control, ...]
