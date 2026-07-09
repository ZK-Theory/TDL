"""Load-bearing threshold and calibration policy registries (review M-2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from research_system.errors import ConfigurationError

_REQUIRED_CALIBRATION = {
    "schema_version": "1.0.0",
    "policy_revision": "p0-calibration-v1",
    "deterministic_repetitions": 2,
    "identical_input_requirement": "byte_identical_normalized_decision",
    "known_bad_requirement": "intended_failure_in_every_repetition",
    "known_good_requirement": "intended_pass_in_every_repetition",
    "declared_mutation_requirement": "detected_in_every_repetition",
    "stochastic_policy_missing": "fixture_error",
    "model_or_human_threshold_policy_missing": "unable_to_grade",
    "live_provider_calibration_enabled": False,
}


def _yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"cannot load policy file: {path}") from exc
    if not isinstance(payload, dict):
        raise ConfigurationError(f"policy file must be a mapping: {path}")
    return payload


def load_threshold_policies(path: Path | str) -> dict[str, dict[str, Any]]:
    """Load the threshold-policy registry keyed by threshold_policy_id.

    Args:
        path: Location of ``threshold-policies.yaml``.

    Returns:
        Mapping of policy id to its full row.

    Raises:
        ConfigurationError: If the file is malformed or ids collide.
    """
    payload = _yaml(Path(path))
    rows = payload.get("policies")
    if not isinstance(rows, list):
        raise ConfigurationError("threshold policies must be a list")
    registry: dict[str, dict[str, Any]] = {}
    for row in rows:
        policy_id = row.get("threshold_policy_id")
        if not isinstance(policy_id, str) or policy_id in registry:
            raise ConfigurationError(f"invalid or duplicate threshold policy: {policy_id!r}")
        registry[policy_id] = dict(row)
    return registry


def require_calibration_policy(path: Path | str) -> dict[str, Any]:
    """Load the calibration policy and reject any drift from the engine.

    Args:
        path: Location of ``p0-calibration-policy.yaml``.

    Returns:
        The validated policy payload.

    Raises:
        ConfigurationError: If any required key is missing or differs from the
            accepted 04-plan §571 values (fail-closed: the file cannot silently
            authorize weaker calibration than the engine performs).
    """
    payload = _yaml(Path(path))
    if payload != _REQUIRED_CALIBRATION:
        drift = {
            key: (payload.get(key), value)
            for key, value in _REQUIRED_CALIBRATION.items()
            if payload.get(key) != value
        } or {key: (payload[key], None) for key in payload.keys() - _REQUIRED_CALIBRATION.keys()}
        raise ConfigurationError(f"calibration policy drift: {drift}")

    from research_system.evals.calibration import DETERMINISTIC_REPETITIONS

    if payload["deterministic_repetitions"] != DETERMINISTIC_REPETITIONS:
        raise ConfigurationError(
            f"calibration policy says {payload['deterministic_repetitions']} "
            f"repetitions but the engine constant is {DETERMINISTIC_REPETITIONS}"
        )
    return payload
