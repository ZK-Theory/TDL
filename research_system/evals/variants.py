"""Typed, fail-closed Gate-5 matrix selection and execution evidence."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from research_system.adapters.base import ProviderCommand, TransportResult
from research_system.adapters.claude import build_claude_adapter
from research_system.adapters.codex import build_codex_adapter
from research_system.adapters.fake import FakeTransport
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.coverage import P0Coverage
from research_system.evals.errors import FixtureDefinitionError
from research_system.evals.executors import require_executor
from research_system.evals.fixture_package import validate_fixture_package
from research_system.evals.models import GraderResult
from research_system.ids import new_id

_FIELDS = (
    "fixture_id",
    "fixture_revision",
    "variant_id",
    "provider_variant",
    "runtime_variant",
    "os",
    "transport",
    "operational_profile",
)
_WILDCARDS = {"", "*", "any", "wildcard"}
_PROVIDERS = {
    "fake-claude-adapter-v1",
    "fake-codex-adapter-v1",
    "fake-claude-count-v1",
    "fake-codex-count-v1",
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
            self.fixture_id,
            self.fixture_revision,
            self.variant_id,
            self.provider_variant,
            self.runtime_variant,
            self.os,
            self.transport,
            self.operational_profile,
            self.reference_count,
            self.exact_tokens,
            self.evaluated_tokens,
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
        rows.append(
            Gate5VariantRow(
                fixture_id,
                fixture_revision,
                variant_id,
                provider,
                str(raw["runtime_variant"]),
                str(raw["os"]),
                str(raw["transport"]),
                str(raw["operational_profile"]),
                *numeric,
            )
        )
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
        payload = {
            "property": self.property,
            "json_pointer": self.json_pointer,
            "canonical_observed_value": self.canonical_observed_value,
        }
        actual = sha256_hex(canonical_bytes(payload))
        if not self.equal or self.first_observed_value_hash != actual or self.second_observed_value_hash != actual:
            raise ValueError("observed assertion evidence mismatch")


@dataclass(frozen=True, slots=True)
class VariantExecutionEvidence:
    matrix_row: Gate5VariantRow
    first_normalized_decision_hash: str
    second_normalized_decision_hash: str
    decisions_equal: bool
    grader_result_keys: tuple[tuple[str, str, str, str, str, str], ...]
    grader_result_bindings: tuple[tuple[object, ...], ...]
    observed_assertions: tuple[ObservedAssertionEvidence, ...]
    execution_evidence_hash: str

    def __post_init__(self) -> None:
        if not self.decisions_equal or self.first_normalized_decision_hash != self.second_normalized_decision_hash:
            raise ValueError("variant repeat mismatch")
        if (
            self.grader_result_bindings != tuple(sorted(self.grader_result_bindings))
            or any(len(item) != 6 for item in self.grader_result_bindings)
            or tuple(item[0] for item in self.grader_result_bindings) != self.grader_result_keys
            or len(set(self.grader_result_keys)) != len(self.grader_result_keys)
        ):
            raise ValueError("grader result binding mismatch")
        payload = {
            "matrix_tuple": list(self.matrix_row.matrix_tuple),
            "first_hash": self.first_normalized_decision_hash,
            "second_hash": self.second_normalized_decision_hash,
            "grader_result_keys": [list(item) for item in self.grader_result_keys],
            "grader_results": [
                [list(item[0]), *item[1:]] for item in self.grader_result_bindings
            ],
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


def build_observed_assertion_evidence(
    property_name: str, first: dict, second: dict
) -> tuple[ObservedAssertionEvidence, ...]:
    """Bind two normalized observations to exact assertion hashes.

    Args:
        property_name: Oracle property represented by both observations.
        first: Normalized observation from the first provider execution.
        second: Normalized observation from the repeated provider execution.

    Returns:
        Content-bound assertion evidence in deterministic pointer order.

    Raises:
        ValueError: If properties or normalized observations differ.
    """
    if set(first) != set(second):
        raise ValueError("observed assertion property mismatch")
    values = []
    if property_name == "adapter_policy_parity" and "controls" in first:
        if first["controls"] != second["controls"]:
            raise ValueError("second-run observed assertion mismatch")
        for control_id, value in sorted(first["controls"].items()):
            pointer = f"/controls/{control_id}"
            payload = {
                "property": property_name,
                "json_pointer": pointer,
                "canonical_observed_value": value,
            }
            digest = sha256_hex(canonical_bytes(payload))
            values.append(ObservedAssertionEvidence(property_name, pointer, value, digest, digest, True))
    else:
        if first != second:
            raise ValueError("second-run observed assertion mismatch")
        payload = {
            "property": property_name,
            "json_pointer": "",
            "canonical_observed_value": first,
        }
        digest = sha256_hex(canonical_bytes(payload))
        values.append(ObservedAssertionEvidence(property_name, "", first, digest, digest, True))
    return tuple(values)


def _execute_through_fake_provider(
    row: Gate5VariantRow,
    payload: dict,
    execute: Callable[[str, dict], dict],
    fake_transport_factory: Callable[[list[TransportResult]], FakeTransport],
) -> tuple[dict, dict]:
    execution_payload = dict(payload)
    execution_payload["_provider_variant"] = row.provider_variant
    observed = execute("known_good", execution_payload)
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
        timeout_s=1.0,
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
        "provider": receipt.provider,
        "adapter_revision": receipt.adapter_revision,
        "output_refs": list(receipt.output_refs),
        "argv": list(invocation[0]),
        "timeout_ms": int(invocation[1] * 1000),
    }


def execute_gate5_variant_rows_twice(
    rows: tuple[Gate5VariantRow, ...],
    coverage: P0Coverage,
    *,
    fixture_root: Path | str,
    schema_root: Path | str,
    baseline_results: tuple[GraderResult, ...],
    fake_transport_factory: Callable[[list[TransportResult]], FakeTransport],
) -> tuple[tuple[VariantExecutionEvidence, ...], tuple[GraderResult, ...]]:
    """Execute exact fake rows twice through bound provider transports.

    Args:
        rows: Exact validated Gate 5 matrix rows.
        coverage: Selected fixture revisions governing the execution.
        fixture_root: Root containing materialized fixture packages.
        schema_root: Root used for full package schema and hash validation.
        baseline_results: Accepted baseline grader results used as templates.
        fake_transport_factory: Constructor-compatible fake transport factory.

    Returns:
        Typed repeated-execution evidence and exactly 170 variant results.

    Raises:
        FixtureDefinitionError: If row closure or package bindings are invalid.
        TypeError: If the injected factory does not return ``FakeTransport``.
        ValueError: If repeated decisions or result-key closure differ.
    """

    if len(rows) != 46:
        raise FixtureDefinitionError("exact 46-row Gate-5 closure required")
    templates = {
        (item.fixture_id, item.grader_id, item.grader_class, item.grader_version): item for item in baseline_results
    }
    evidences = []
    variant_results = []
    validated_packages = {}
    for row in rows:
        package = Path(fixture_root) / row.fixture_id
        package_key = (row.fixture_id, row.fixture_revision)
        validated = validated_packages.get(package_key)
        if validated is None:
            validated = validate_fixture_package(package, schema_root=schema_root)
            if validated.fixture_id != row.fixture_id or validated.fixture_revision != row.fixture_revision:
                raise FixtureDefinitionError("matrix row does not match validated fixture package")
            validated_packages[package_key] = validated
        fixture_bytes = (package / "fixture.yaml").read_bytes()
        stimulus_bytes = (package / "input" / "stimulus.json").read_bytes()
        post_bytes = (package / "expected" / "post-control.json").read_bytes()
        reread = {
            "fixture.yaml": fixture_bytes,
            "input/stimulus.json": stimulus_bytes,
            "expected/post-control.json": post_bytes,
        }
        for relative, data in reread.items():
            if sha256_hex(data) != validated.content_hashes[relative]:
                raise FixtureDefinitionError(f"validated package changed before execution: {relative}")
        stimulus = json.loads(stimulus_bytes)
        post = json.loads(post_bytes)
        property_name = str(post["assertions"][0]["property"])
        execute = require_executor(row.fixture_id)
        first_observed, first_receipt = _execute_through_fake_provider(
            row,
            stimulus["payload"],
            execute,
            fake_transport_factory,
        )
        second_observed, second_receipt = _execute_through_fake_provider(
            row,
            stimulus["payload"],
            execute,
            fake_transport_factory,
        )
        assertions = build_observed_assertion_evidence(property_name, first_observed, second_observed)
        definition = yaml.safe_load(fixture_bytes.decode("utf-8"))
        row_results = []
        for grader in definition["required_graders"]:
            template_key = (
                row.fixture_id,
                grader["grader_id"],
                grader["grader_class"],
                grader["grader_version"],
            )
            template = templates[template_key]
            row_results.append(
                replace(
                    template,
                    grader_result_id=new_id("grader_result"),
                    evaluation_run_id=new_id("evaluation_run"),
                    variant_id=row.variant_id,
                    evidence_refs=(f"variant:{row.variant_id}",),
                )
            )
        projection = {
            "matrix_tuple": list(row.matrix_tuple),
            "fixture_hashes": {
                "oracle": row_results[0].oracle_hash,
                "policy": row_results[0].policy_hash,
                "threshold": row_results[0].threshold_policy_hash,
            },
            "observed": first_observed,
            "provider_receipt": first_receipt,
            "grader_verdicts": [
                [list(item.result_key), item.verdict]
                for item in sorted(row_results, key=lambda result: result.result_key)
            ],
            "blocking_reason": (
                "required_judgment_unavailable"
                if any(item.verdict == "unable_to_grade" for item in row_results)
                else None
            ),
        }
        first_hash = sha256_hex(canonical_bytes(projection))
        second_projection = {
            **projection,
            "observed": second_observed,
            "provider_receipt": second_receipt,
        }
        second_hash = sha256_hex(canonical_bytes(second_projection))
        if first_hash != second_hash:
            raise ValueError("variant repeat mismatch")
        keys = tuple(sorted(item.result_key for item in row_results))
        grader_bindings = tuple(
            sorted(
                (
                    item.result_key,
                    item.verdict,
                    item.trace_hash,
                    item.oracle_hash,
                    item.policy_hash,
                    item.threshold_policy_hash,
                )
                for item in row_results
            )
        )
        hash_payload = {
            "matrix_tuple": list(row.matrix_tuple),
            "first_hash": first_hash,
            "second_hash": second_hash,
            "grader_result_keys": [list(item) for item in keys],
            "grader_results": [
                [list(item[0]), *item[1:]] for item in grader_bindings
            ],
            "observed_assertions": [
                {
                    "property": item.property,
                    "json_pointer": item.json_pointer,
                    "canonical_observed_value": item.canonical_observed_value,
                    "first_observed_value_hash": item.first_observed_value_hash,
                    "second_observed_value_hash": item.second_observed_value_hash,
                    "equal": item.equal,
                }
                for item in assertions
            ],
        }
        evidence_hash = sha256_hex(canonical_bytes(hash_payload))
        evidences.append(
            VariantExecutionEvidence(
                row,
                first_hash,
                second_hash,
                True,
                keys,
                grader_bindings,
                assertions,
                evidence_hash,
            )
        )
        variant_results.extend(row_results)
    if len(variant_results) != 170 or len({item.result_key for item in variant_results}) != 170:
        raise ValueError("expected exact 170 unique Gate-5 result keys")
    return tuple(evidences), tuple(variant_results)
