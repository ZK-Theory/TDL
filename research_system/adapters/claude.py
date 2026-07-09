"""Claude adapter constructor; live enablement remains external and reviewed."""

from research_system.adapters.provider import ProviderAdapter


def build_claude_adapter(transport) -> ProviderAdapter:
    return ProviderAdapter(
        ["claude", "--print", "--output-format", "json"],
        transport,
    )
