"""Codex adapter constructor; live enablement remains external and reviewed."""

from research_system.adapters.provider import ProviderAdapter


def build_codex_adapter(transport) -> ProviderAdapter:
    return ProviderAdapter(
        ["codex", "exec", "--ephemeral", "--ignore-user-config", "--json", "-"],
        transport,
    )
