"""Derive the explicit P0 variant matrix from the committed fixture packages.

Rows are recomputed from package bytes -- never hand-authored -- so the matrix
is load-bearing evidence (review M-2). Fake counting/adapter revisions are
*definitions*: fake-claude-count-v1 counts ceil(bytes/4), fake-codex-count-v1
counts ceil(bytes/3).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

CONTROL_STORE = (
    "F-001", "F-002", "F-003", "F-004", "F-005",
    "S-001", "S-002", "S-006", "S-008", "S-009", "S-010", "S-011", "S-012",
)
CONTEXT_ROUTING = (
    "F-021", "F-022", "F-025", "F-026", "F-027", "F-028", "F-031", "F-033", "F-035",
)
ADAPTER_SCIENTIFIC = (
    "F-007", "F-008", "F-009", "F-010", "F-011", "F-012", "F-013", "F-014",
    "F-020", "F-032", "F-034", "F-036", "S-003", "S-004", "S-013",
)
OPERATIONAL_PROFILES = {
    "S-003": "long_running", "S-004": "long_running",
    "S-013": "trivial", "F-034": "trivial",
}
COUNTERS = {"fake-claude-count-v1": 4, "fake-codex-count-v1": 3}


def _revision(root: Path, fixture_id: str) -> str:
    definition = yaml.safe_load((root / fixture_id / "fixture.yaml").read_text(encoding="utf-8"))
    return str(definition["fixture_revision"])


def _executed_row(root: Path, fixture_id: str, profile: str) -> dict:
    return {
        "fixture_id": fixture_id,
        "fixture_revision": _revision(root, fixture_id),
        "variant_id": "python313-windows-in-process",
        "provider_variant": "provider-neutral",
        "runtime_variant": "python-3.13",
        "os": "windows",
        "transport": "in_process_fake",
        "operational_profile": profile,
        "execution_stage": "p0",
    }


def _gate5_adapter_rows(root: Path, fixture_id: str, profile: str) -> list[dict]:
    return [
        {
            "fixture_id": fixture_id,
            "fixture_revision": _revision(root, fixture_id),
            "variant_id": f"{provider}-windows-fake-transport",
            "provider_variant": provider,
            "runtime_variant": "python-3.13",
            "os": "windows",
            "transport": "fake",
            "operational_profile": profile,
            "execution_stage": "gate5",
        }
        for provider in ("fake-claude-adapter-v1", "fake-codex-adapter-v1")
    ]


def _sizing_rows(root: Path, fixture_id: str, stage: str) -> list[dict]:
    package = root / fixture_id
    stimulus = (package / "input" / "stimulus.json").read_bytes()
    evaluated = stimulus + b"".join(
        (package / "expected" / name).read_bytes()
        for name in ("pre-control.json", "post-control.json")
    )
    manifest = json.loads((package / "input" / "source-manifest.json").read_text(encoding="utf-8"))
    payload = json.loads(stimulus)["payload"]
    reference_count = len(manifest["authoritative_refs"]) + (
        1 if "governing_amendment" in payload.get("action", {}) else 0
    )
    return [
        {
            "fixture_id": fixture_id,
            "fixture_revision": _revision(root, fixture_id),
            "variant_id": f"mandatory_closure_sizing-{counter}",
            "provider_variant": counter,
            "runtime_variant": "python-3.13",
            "os": "windows",
            "transport": "in_process_fake",
            "operational_profile": "bounded",
            "execution_stage": stage,
            "reference_count": reference_count,
            "exact_tokens": math.ceil(len(stimulus) / divisor),
            "evaluated_tokens": math.ceil(len(evaluated) / divisor),
        }
        for counter, divisor in COUNTERS.items()
    ]


def build_matrix(root: Path) -> dict:
    rows: list[dict] = []
    for fixture_id in CONTROL_STORE:
        rows.append(_executed_row(root, fixture_id, "bounded"))
    for fixture_id in CONTEXT_ROUTING:
        rows.append(_executed_row(root, fixture_id, "bounded"))
        stage = "p0" if fixture_id == "F-021" else "gate5"
        rows.extend(_sizing_rows(root, fixture_id, stage))
    for fixture_id in ADAPTER_SCIENTIFIC:
        profile = OPERATIONAL_PROFILES.get(fixture_id, "bounded")
        rows.append(_executed_row(root, fixture_id, profile))
        rows.extend(_gate5_adapter_rows(root, fixture_id, profile))
    return {
        "schema_version": "1.0.0",
        "matrix_revision": "p0-variant-matrix-v1",
        "counting_revisions": {name: f"tokens = ceil(bytes/{d})" for name, d in COUNTERS.items()},
        "rows": rows,
    }


def main() -> None:
    """Generate or check the committed variant matrix."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=_REPO_ROOT / ".research-system" / "evals" / "fixtures")
    parser.add_argument("--output", type=Path, default=_REPO_ROOT / ".research-system" / "evals" / "p0-variant-matrix.yaml")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = yaml.safe_dump(build_matrix(args.root), sort_keys=False).encode()
    if args.check:
        if args.output.read_bytes() != rendered:
            raise SystemExit("p0-variant-matrix.yaml is not byte-identical to regeneration")
        print("p0-variant-matrix.yaml byte-identical")
        return
    args.output.write_bytes(rendered)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
