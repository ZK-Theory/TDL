import pytest

from research_system.context.service import (
    ContextLifecycleCapability,
    PrevalidatedProviderCommandTemplate,
)


def test_lifecycle_capability_has_no_public_constructor() -> None:
    with pytest.raises(TypeError, match="service-minted"):
        ContextLifecycleCapability(
            context_id="ctx_01978abc-1000-7000-8000-000000001000",
            request_id="req-1",
            revision=1,
            packet_sha256="1" * 64,
            writer_id="writer-1",
            lifecycle_version="context-packet-v1",
            issuer_nonce="forged",
            mint_key=object(),
        )


def test_provider_template_preimage_is_immutable_across_reads() -> None:
    source = {"operation": "compile_brief", "nested": {"count": 2}}
    frozen = PrevalidatedProviderCommandTemplate.freeze(source)
    source["nested"]["count"] = 9
    first = frozen.content
    first["nested"]["count"] = 7
    assert frozen.content == {"nested": {"count": 2}, "operation": "compile_brief"}
