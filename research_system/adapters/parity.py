"""Semantic parity evaluation across required providers."""


def build_parity_report(bundle, manifests, required_providers=("claude", "codex")):
    by_provider = {}
    for manifest in manifests:
        if manifest.provider in by_provider:
            raise ValueError(f"duplicate provider manifest: {manifest.provider}")
        by_provider[manifest.provider] = manifest
    rows = []
    blocking = []
    for control in sorted(bundle.controls, key=lambda item: item.control_id):
        dispositions = {
            provider: (
                by_provider[provider].disposition(control.control_id)
                if provider in by_provider
                else "unsupported"
            )
            for provider in sorted(required_providers)
        }
        rows.append(
            {"control_id": control.control_id, "providers": dispositions}
        )
        if control.critical and any(
            value in {"unsupported", "divergent", "diagnostic_only"}
            for value in dispositions.values()
        ):
            blocking.append(control.control_id)
    return {
        "rows": rows,
        "blocking_controls": sorted(blocking),
        "passed": not blocking,
    }
