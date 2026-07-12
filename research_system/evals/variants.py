"""Typed, fail-closed Gate-5 matrix selection and execution evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from research_system.evals.coverage import P0Coverage
from research_system.evals.errors import FixtureDefinitionError
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.executors import require_executor
from research_system.evals.models import GraderResult
from research_system.ids import new_id

_FIELDS = (
    "fixture_id", "fixture_revision", "variant_id", "provider_variant",
    "runtime_variant", "os", "transport", "operational_profile",
)
_WILDCARDS = {"", "*", "any", "wildcard"}
_PROVIDERS = {
    "fake-claude-adapter-v1", "fake-codex-adapter-v1",
    "fake-claude-count-v1", "fake-codex-count-v1",
}


@dataclass(frozen=True, slots=True, order=True)
class Gate5VariantRow:
    fixture_id: str
    fixture_revision: str
    variant_id: str
    provider_variant: str
    runtime_variant: str
    os: str
    transport: str
    operational_profile: str
    reference_count: int | None = None
    exact_tokens: int | None = None
    evaluated_tokens: int | None = None

    @property
    def matrix_tuple(self) -> tuple[object, ...]:
        return (
            self.fixture_id, self.fixture_revision, self.variant_id,
            self.provider_variant, self.runtime_variant, self.os,
            self.transport, self.operational_profile, self.reference_count,
            self.exact_tokens, self.evaluated_tokens,
        )


def load_gate5_variant_rows(path: Path | str, coverage: P0Coverage) -> tuple[Gate5VariantRow, ...]:
    """Select and validate every exact execution_stage=gate5 row."""
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        raise FixtureDefinitionError("variant matrix must contain rows")
    selected = dict(coverage.selected_fixture_revisions)
    rows: list[Gate5VariantRow] = []
    seen: set[tuple[str, str]] = set()
    for raw in payload["rows"]:
        if not isinstance(raw, dict) or raw.get("execution_stage") != "gate5":
            continue
        missing = [field for field in _FIELDS if field not in raw]
        if missing:
            raise FixtureDefinitionError(f"gate5 row missing fields: {missing}")
        if any(str(raw[field]).lower() in _WILDCARDS for field in _FIELDS):
            raise FixtureDefinitionError("gate5 row contains wildcard")
        fixture_id = str(raw["fixture_id"])
        fixture_revision = str(raw["fixture_revision"])
        variant_id = str(raw["variant_id"])
        key = (fixture_id, variant_id)
        if key in seen:
            raise FixtureDefinitionError("duplicate fixture_id/variant_id")
        seen.add(key)
        if fixture_id not in selected:
            raise FixtureDefinitionError("gate5 fixture outside selected coverage")
        if selected[fixture_id] != fixture_revision:
            raise FixtureDefinitionError(f"stale gate5 fixture revision: {fixture_id}")
        provider = str(raw["provider_variant"])
        if provider not in _PROVIDERS:
            raise FixtureDefinitionError("unknown fake provider revision")
        sizing = provider.endswith("-count-v1")
        numeric = tuple(raw.get(name) for name in ("reference_count", "exact_tokens", "evaluated_tokens"))
        if sizing != all(isinstance(item, int) and item >= 0 for item in numeric):
            raise FixtureDefinitionError("sizing evidence fields invalid")
        rows.append(Gate5VariantRow(
            fixture_id, fixture_revision, variant_id, provider,
            str(raw["runtime_variant"]), str(raw["os"]), str(raw["transport"]),
            str(raw["operational_profile"]), *numeric,
        ))
    ordered = tuple(sorted(rows))
    if len(ordered) != 46:
        raise FixtureDefinitionError(f"expected 46 gate5 rows, found {len(ordered)}")
    return ordered


@dataclass(frozen=True, slots=True, order=True)
class ObservedAssertionEvidence:
    property: str
    json_pointer: str
    canonical_observed_value: object
    first_observed_value_hash: str
    second_observed_value_hash: str
    equal: bool

    def __post_init__(self) -> None:
        actual = sha256_hex(canonical_bytes({"property": self.property, "json_pointer": self.json_pointer, "canonical_observed_value": self.canonical_observed_value}))
        if not self.equal or self.first_observed_value_hash != actual or self.second_observed_value_hash != actual:
            raise ValueError("observed assertion evidence mismatch")


@dataclass(frozen=True, slots=True)
class VariantExecutionEvidence:
    matrix_row: Gate5VariantRow
    first_normalized_decision_hash: str
    second_normalized_decision_hash: str
    decisions_equal: bool
    grader_result_keys: tuple[tuple[str, str, str, str, str, str], ...]
    observed_assertions: tuple[ObservedAssertionEvidence, ...]
    execution_evidence_hash: str

    def __post_init__(self) -> None:
        if not self.decisions_equal or self.first_normalized_decision_hash != self.second_normalized_decision_hash:
            raise ValueError("variant repeat mismatch")
        payload = {
            "matrix_tuple": list(self.matrix_row.matrix_tuple),
            "first_hash": self.first_normalized_decision_hash,
            "second_hash": self.second_normalized_decision_hash,
            "grader_result_keys": [list(item) for item in self.grader_result_keys],
            "observed_assertions": [
                {
                    "property": item.property,
                    "json_pointer": item.json_pointer,
                    "canonical_observed_value": item.canonical_observed_value,
                    "first_observed_value_hash": item.first_observed_value_hash,
                    "second_observed_value_hash": item.second_observed_value_hash,
                    "equal": item.equal,
                }
                for item in self.observed_assertions
            ],
        }
        if self.execution_evidence_hash != sha256_hex(canonical_bytes(payload)):
            raise ValueError("execution_evidence_hash mismatch")


def build_observed_assertion_evidence(property_name: str, first: dict, second: dict) -> tuple[ObservedAssertionEvidence, ...]:
    if set(first) != set(second):
        raise ValueError("observed assertion property mismatch")
    values = []
    if property_name == "adapter_policy_parity" and "controls" in first:
        if first["controls"] != second["controls"]:
            raise ValueError("second-run observed assertion mismatch")
        for control_id, value in sorted(first["controls"].items()):
            pointer = f"/controls/{control_id}"
            digest = sha256_hex(canonical_bytes({"property": property_name, "json_pointer": pointer, "canonical_observed_value": value}))
            values.append(ObservedAssertionEvidence(property_name, pointer, value, digest, digest, True))
    else:
        if first != second:
            raise ValueError("second-run observed assertion mismatch")
        digest = sha256_hex(canonical_bytes({"property": property_name, "json_pointer": "", "canonical_observed_value": first}))
        values.append(ObservedAssertionEvidence(property_name, "", first, digest, digest, True))
    return tuple(values)


def execute_gate5_variant_rows_twice(
    rows: tuple[Gate5VariantRow, ...],
    coverage: P0Coverage,
    *,
    fixture_root: Path | str,
    baseline_results: tuple[GraderResult, ...],
    fake_transport_factory,
) -> tuple[tuple[VariantExecutionEvidence, ...], tuple[GraderResult, ...]]:
    """Execute exact fake rows twice and admit only equal normalized decisions."""
    from research_system.adapters.fake import FakeTransport

    if len(rows) != 46:
        raise FixtureDefinitionError("exact 46-row Gate-5 closure required")
    templates = {(item.fixture_id, item.grader_id, item.grader_class, item.grader_version): item for item in baseline_results}
    evidences = []
    variant_results = []
    for row in rows:
        probe = fake_transport_factory([])
        if not isinstance(probe, FakeTransport):
            raise TypeError("injected FakeTransport required")
        package = Path(fixture_root) / row.fixture_id
        stimulus = json.loads((package / "input" / "stimulus.json").read_text(encoding="utf-8"))
        post = json.loads((package / "expected" / "post-control.json").read_text(encoding="utf-8"))
        property_name = str(post["assertions"][0]["property"])
        execute = require_executor(row.fixture_id)
        first_observed = execute("known_good", dict(stimulus["payload"]))
        second_observed = execute("known_good", dict(stimulus["payload"]))
        assertions = build_observed_assertion_evidence(property_name, first_observed, second_observed)
        definition = yaml.safe_load((package / "fixture.yaml").read_text(encoding="utf-8"))
        row_results = []
        for grader in definition["required_graders"]:
            template = templates[(row.fixture_id, grader["grader_id"], grader["grader_class"], grader["grader_version"])]
            row_results.append(replace(
                template,
                grader_result_id=new_id("grader_result"),
                evaluation_run_id=new_id("evaluation_run"),
                variant_id=row.variant_id,
                evidence_refs=(f"variant:{row.variant_id}",),
            ))
        projection = {
            "matrix_tuple": list(row.matrix_tuple),
            "fixture_hashes": {
                "oracle": row_results[0].oracle_hash,
                "policy": row_results[0].policy_hash,
                "threshold": row_results[0].threshold_policy_hash,
            },
            "observed": first_observed,
            "grader_verdicts": [
                [list(item.result_key), item.verdict]
                for item in sorted(row_results, key=lambda result: result.result_key)
            ],
            "blocking_reason": "required_judgment_unavailable" if any(item.verdict == "unable_to_grade" for item in row_results) else None,
        }
        first_hash = sha256_hex(canonical_bytes(projection))
        second_projection = {**projection, "observed": second_observed}
        second_hash = sha256_hex(canonical_bytes(second_projection))
        if first_hash != second_hash:
            raise ValueError("variant repeat mismatch")
        keys = tuple(sorted(item.result_key for item in row_results))
        hash_payload = {
            "matrix_tuple": list(row.matrix_tuple), "first_hash": first_hash,
            "second_hash": second_hash, "grader_result_keys": [list(item) for item in keys],
            "observed_assertions": [
                {"property": item.property, "json_pointer": item.json_pointer,
                 "canonical_observed_value": item.canonical_observed_value,
                 "first_observed_value_hash": item.first_observed_value_hash,
                 "second_observed_value_hash": item.second_observed_value_hash,
                 "equal": item.equal} for item in assertions
            ],
        }
        evidence_hash = sha256_hex(canonical_bytes(hash_payload))
        evidences.append(VariantExecutionEvidence(row, first_hash, second_hash, True, keys, assertions, evidence_hash))
        variant_results.extend(row_results)
    if len(variant_results) != 170 or len({item.result_key for item in variant_results}) != 170:
        raise ValueError("expected exact 170 unique Gate-5 result keys")
    return tuple(evidences), tuple(variant_results)
