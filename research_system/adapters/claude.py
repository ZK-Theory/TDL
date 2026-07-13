"""Claude adapter constructor; live enablement remains external and reviewed."""

from research_system.adapters.provider import ProviderAdapter, default_provider_operation_policy


def build_claude_adapter(transport, *, live_provider_enabled: bool = False) -> ProviderAdapter:
    return ProviderAdapter(
        ["claude", "--print", "--output-format", "json"],
        transport,
        operation_policy=default_provider_operation_policy(
            live_provider_enabled=live_provider_enabled
        ),
    )
