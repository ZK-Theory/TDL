from typing import TYPE_CHECKING, Any

from research_system.discovery.operator import DiscoveryOperator, DiscoveryOperatorConfig, load_discovery_operator
from research_system.discovery.runtime import DiscoveryRuntime, replay_discovery

if TYPE_CHECKING:
    from research_system.discovery.spec_flow import SpecFlow, SpecFlowStatus


def __getattr__(name: str) -> Any:
    """Lazily expose the SPEC coordinator without creating replay import cycles."""

    if name in {"SpecFlow", "SpecFlowStatus", "build_spec_authority_subject"}:
        from research_system.discovery.spec_flow import SpecFlow, SpecFlowStatus, build_spec_authority_subject

        return {
            "SpecFlow": SpecFlow,
            "SpecFlowStatus": SpecFlowStatus,
            "build_spec_authority_subject": build_spec_authority_subject,
        }[name]
    raise AttributeError(name)


__all__ = [
    "DiscoveryOperator",
    "DiscoveryOperatorConfig",
    "DiscoveryRuntime",
    "SpecFlow",
    "SpecFlowStatus",
    "build_spec_authority_subject",
    "load_discovery_operator",
    "replay_discovery",
]
