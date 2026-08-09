from research_system.context.service import PrevalidatedProviderCommandTemplate


def test_prevalidated_template_hash_binds_complete_canonical_bytes() -> None:
    template = PrevalidatedProviderCommandTemplate.freeze(
        {
            "operation": "compile_brief",
            "provider": "provider-a",
            "model": "model-a",
            "profile": "bounded-r2",
            "rendered_sha256": "1" * 64,
            "provider_count": 42,
            "provider_capacity": 100,
            "wrapper_accounting": {"system": 5, "input": 42},
        }
    )
    changed = PrevalidatedProviderCommandTemplate.freeze({**template.content, "provider_count": 43})
    assert changed.sha256 != template.sha256
