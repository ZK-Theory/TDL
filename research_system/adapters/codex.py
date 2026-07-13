"""Codex adapter constructor; live enablement remains external and reviewed."""

from research_system.adapters.provider import ProviderAdapter, default_provider_operation_policy


def build_codex_adapter(transport, *, live_provider_enabled: bool = False) -> ProviderAdapter:
    return ProviderAdapter(
        ["codex", "exec", "--ephemeral", "--ignore-user-config", "--json", "-"],
        transport,
        operation_policy=default_provider_operation_policy(
            live_provider_enabled=live_provider_enabled
        ),
    )
