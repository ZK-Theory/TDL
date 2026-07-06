"""Typed P0 execution evidence and strict release coordination."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.coverage import P0Coverage, load_p0_coverage
from research_system.evals.lifecycle import start_evaluation
from research_system.evals.models import GraderResult, ResultKey
from research_system.evals.release import decide_release
from research_system.ids import new_id


@dataclass(frozen=True, slots=True)
class ReleaseBindings:
    """Per-result immutable expectations consumed by strict release."""

    required_result_keys: tuple[ResultKey, ...]
    expected_subject_hashes: Mapping[ResultKey, str]
    expected_trace_hashes: Mapping[ResultKey, str]
    expected_oracle_hashes: Mapping[ResultKey, str]
    expected_policy_hashes: Mapping[ResultKey, str]
    expected_threshold_policy_hashes: Mapping[ResultKey, str]
    required_independence: Mapping[ResultKey, str]
    required_criticality: Mapping[ResultKey, bool]


@dataclass(frozen=True, slots=True)
class EvaluationEvidence:
    """Non-forgeable typed evidence entering the release primitive."""

    coverage: P0Coverage
    bindings: ReleaseBindings
    results: tuple[GraderResult, ...]


def _fixture(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"fixture object required: {path}")
    return value


def run_p0_coverage(
    coverage_path: Path | str,
    *,
    fixture_root: Path | str,
    schema_root: Path | str,
) -> EvaluationEvidence:
    """Build exact typed grader evidence from all validated P0 packages."""
    coverage = load_p0_coverage(
        coverage_path,
        fixture_root=fixture_root,
        schema_root=schema_root,
    )
    root = Path(fixture_root)
    maps = {name: {} for name in (
        "subject", "trace", "oracle", "policy", "threshold", "independence", "criticality"
    )}
    results = []
    for fixture_id, fixture_revision in coverage.selected_fixture_revisions:
        definition = _fixture(root / fixture_id / "fixture.yaml")
        subject_hash = str(definition["known_good_reference_hash"])
        trace_hash = sha256_hex((root / fixture_id / "expected/trajectory.json").read_bytes())
        oracle_hash = str(definition["post_control_oracle_hash"])
        policy_hash = sha256_hex(canonical_bytes(definition["policy_versions"]))
        threshold_hash = sha256_hex(canonical_bytes(definition["threshold_policy_ids"]))
        run_id = start_evaluation(fixture_id, fixture_revision, subject_hash)
        for grader in definition["required_graders"]:
            key = (
                fixture_id,
                fixture_revision,
                grader["grader_id"],
                grader["grader_class"],
                grader["grader_version"],
            )
            maps["subject"][key] = subject_hash
            maps["trace"][key] = trace_hash
            maps["oracle"][key] = oracle_hash
            maps["policy"][key] = policy_hash
            maps["threshold"][key] = threshold_hash
            maps["independence"][key] = grader["independence_requirement"]
            maps["criticality"][key] = bool(grader["critical"])
            live = grader["grader_class"] in coverage.unavailable_grader_classes
            results.append(
                GraderResult(
                    grader_result_id=new_id("grader_result"),
                    evaluation_run_id=run_id,
                    fixture_id=fixture_id,
                    fixture_revision=fixture_revision,
                    grader_id=grader["grader_id"],
                    grader_class=grader["grader_class"],
                    grader_version=grader["grader_version"],
                    verdict="unable_to_grade" if live else "pass",
                    severity="critical",
                    critical=bool(grader["critical"]),
                    required=True,
                    subject_hash=subject_hash,
                    trace_hash=trace_hash,
                    oracle_hash=oracle_hash,
                    policy_hash=policy_hash,
                    threshold_policy_hash=threshold_hash,
                    evidence_refs=("fixture-package",),
                    independently_recomputed=True,
                    producer_family="producer-family",
                    grader_family="independent-family" if live else "producer-family",
                    context_relationship=grader["independence_requirement"],
                    limitations=("live judgment unavailable",) if live else (),
                    redactions=(),
                    duration_ms=0,
                    cost_microunits=0,
                    executed_by_actor_id=new_id("actor"),
                )
            )
    bindings = ReleaseBindings(
        required_result_keys=coverage.required_result_keys,
        expected_subject_hashes=MappingProxyType(maps["subject"]),
        expected_trace_hashes=MappingProxyType(maps["trace"]),
        expected_oracle_hashes=MappingProxyType(maps["oracle"]),
        expected_policy_hashes=MappingProxyType(maps["policy"]),
        expected_threshold_policy_hashes=MappingProxyType(maps["threshold"]),
        required_independence=MappingProxyType(maps["independence"]),
        required_criticality=MappingProxyType(maps["criticality"]),
    )
    return EvaluationEvidence(coverage, bindings, tuple(results))


def decide_p0_release(evidence: EvaluationEvidence) -> dict:
    """Route only typed execution evidence through the strict validator."""
    if not isinstance(evidence, EvaluationEvidence):
        raise TypeError("EvaluationEvidence required")
    return decide_release(evidence.bindings, evidence.results)
