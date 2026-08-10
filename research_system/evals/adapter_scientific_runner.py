"""Exact-ID fake-provider runner for adapter-scientific variant evidence."""

from __future__ import annotations

import json
from collections.abc import Callable

from research_system.adapters.base import ProviderCommand, TransportResult
from research_system.adapters.claude import build_claude_adapter
from research_system.adapters.codex import build_codex_adapter
from research_system.adapters.fake import FakeTransport
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.executors import ADAPTER_SCIENTIFIC_IDS, RegisteredExecutor


def execute_adapter_scientific_variant(
    row,
    payload: dict,
    registration: RegisteredExecutor,
    fake_transport_factory: Callable[[list[TransportResult]], FakeTransport],
) -> tuple[dict, dict]:
    """Execute only a classified adapter-scientific ID; no lifecycle inputs exist."""
    if (
        registration.execution_class != "adapter_scientific"
        or registration.fixture_id not in ADAPTER_SCIENTIFIC_IDS
        or registration.fixture_id != row.fixture_id
    ):
        raise TypeError("exact adapter-scientific registration required")
    execution_payload = dict(payload)
    execution_payload["_provider_variant"] = row.provider_variant
    observed = registration.execute_raw("known_good", execution_payload)
    observed_hash = sha256_hex(canonical_bytes(observed))
    provider = "fake-claude" if row.provider_variant.startswith("fake-claude") else "fake-codex"
    context_hash = sha256_hex(canonical_bytes(payload))
    command = ProviderCommand(
        provider_command_id=f"pcmd_{row.variant_id}",
        revision=1,
        revision_hash="a" * 64,
        provider=provider,
        model="fake-model",
        profile_id="gate5-variant-parity",
        adapter_revision=row.provider_variant,
        policy_hash="b" * 64,
        context_hash=context_hash,
        rendered_payload_hash=context_hash,
        idempotency_key=row.variant_id,
        operation="evaluate_gate5_fixture",
        timeout_s=1,
        wrapper_accounting={
            "method": "fake-gate5-v1",
            "raw_capacity": 1,
            "fixed_overhead": 0,
            "managed_tokens": 1,
            "reserved_variable_tokens": 0,
            "segments": {"managed": "managed"},
        },
        authorized=True,
    )
    response = {
        "provider": command.provider,
        "model": command.model,
        "profile_id": command.profile_id,
        "adapter_revision": command.adapter_revision,
        "command_revision": command.revision,
        "command_revision_hash": command.revision_hash,
        "delivered_context_hash": command.context_hash,
        "response_id": f"fake-response:{row.variant_id}",
        "output_refs": [f"decision:{observed_hash}"],
    }
    transport = fake_transport_factory(
        [TransportResult("terminal", json.dumps(response, sort_keys=True), "", "fake-request", 0)]
    )
    if not isinstance(transport, FakeTransport):
        raise TypeError("injected FakeTransport required")
    adapter = build_claude_adapter(transport) if provider == "fake-claude" else build_codex_adapter(transport)
    receipt = adapter.issue(command, canonical_bytes(payload).decode("utf-8"))
    expected_ref = (f"decision:{observed_hash}",)
    if not receipt.complete or receipt.output_refs != expected_ref or len(transport.invocations) != 1:
        raise ValueError("fake provider execution did not produce bound terminal evidence")
    invocation = transport.invocations[0]
    return observed, {
        "execution_class": "adapter_scientific",
        "provider": receipt.provider,
        "adapter_revision": receipt.adapter_revision,
        "output_refs": list(receipt.output_refs),
        "argv": list(invocation[0]),
        "timeout_ms": int(invocation[1] * 1000),
    }
