"""Inert semantic admission controls for materialized W11 contract documents.

The W11 JSON Schemas describe the shape of a document.  This module supplies
the small set of cross-field and cross-document rules that must run at the
same admission seam as that shape validation.  It contains no runtime
bindings, handlers, stores, or lifecycle effects.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from math import isfinite
from typing import Any

from research_system.errors import SchemaError


W11_CONTENT_SCHEMA_IDS = frozenset(
    {
        "ars://portfolio/programme",
        "ars://portfolio/paper",
        "ars://portfolio/hypothesis",
        "ars://portfolio/candidate",
        "ars://portfolio/method",
        "ars://portfolio/dataset",
        "ars://portfolio/claim",
        "ars://portfolio/dependency-edge",
        "ars://portfolio/assay-rubric-content",
        "ars://portfolio/assay-evidence-scope-content",
        "ars://portfolio/path-registration-content",
        "ars://portfolio/dossier-expected-set-content",
        "ars://portfolio/legacy-source-inventory-content",
        "ars://portfolio/legacy-transition-mapping-content",
        "ars://portfolio/legacy-cutover-closure-content",
        "ars://portfolio/w11-schema-catalogue-content",
    }
)
W11_SCHEMA_CATALOGUE_SCHEMA_ID = "ars://portfolio/w11-schema-catalogue-content"
W11_ASSAY_RUBRIC_SCHEMA_ID = "ars://portfolio/assay-rubric-content"
W11_ASSAY_SCORECARD_SCHEMA_ID = "ars://portfolio/assay-scorecard"

_OWNER_ROW_IDS = frozenset(
    {*(f"OR-{number:03d}" for number in range(1, 42)), *(f"OR-{number:03d}" for number in range(101, 141))}
)

ReferenceValidator = Callable[[str, Mapping[str, Any]], None]


def validate_w11_document(
    schema_id: str,
    value: Any,
    *,
    reference_documents: Iterable[Mapping[str, Any]] = (),
    validate_reference: ReferenceValidator | None = None,
) -> None:
    """Apply inert W11 semantic rules after the JSON Schema has accepted ``value``.

    ``reference_documents`` is an explicit admission input, not a repository
    scan or a self-generated catalogue.  A scorecard therefore fails closed
    when its frozen rubric cannot be resolved from that input.
    """
    if not isinstance(value, Mapping):
        return

    if schema_id in W11_CONTENT_SCHEMA_IDS:
        _validate_content_envelope(schema_id, value)
    if schema_id == W11_SCHEMA_CATALOGUE_SCHEMA_ID:
        _validate_owner_contract_rows(schema_id, value)
    if schema_id == W11_ASSAY_SCORECARD_SCHEMA_ID:
        _validate_scorecard_against_rubric(
            schema_id,
            value,
            reference_documents=reference_documents,
            validate_reference=validate_reference,
        )


def _invalid(schema_id: str, message: str) -> None:
    raise SchemaError(f"{schema_id}: {message}")


def _validate_content_envelope(schema_id: str, value: Mapping[str, Any]) -> None:
    revision = value["record_revision"]
    predecessor = value["supersedes_revision"]
    if revision == 1 and predecessor is not None:
        _invalid(schema_id, "revision 1 must have null supersedes_revision")
    if type(revision) is int and revision > 1 and predecessor != revision - 1:
        _invalid(schema_id, "later revisions must name the exact predecessor")

    for index, source_ref in enumerate(value["source_refs"]):
        ref_kind = source_ref["ref_kind"]
        identifier = source_ref.get("id")
        if (
            ref_kind == "record"
            and not isinstance(identifier, str)
            or (ref_kind == "record" and not identifier.startswith("obj_"))
        ):
            _invalid(schema_id, f"source_refs[{index}] record identity must start with obj_")
        if (
            ref_kind == "artefact"
            and not isinstance(identifier, str)
            or (ref_kind == "artefact" and not identifier.startswith("art_"))
        ):
            _invalid(schema_id, f"source_refs[{index}] artefact identity must start with art_")


def _validate_owner_contract_rows(schema_id: str, value: Mapping[str, Any]) -> None:
    rows = value["owner_contract_rows"]
    observed_ids = [row["owner_row_id"] for row in rows]
    if len(set(observed_ids)) != len(observed_ids):
        _invalid(schema_id, "owner_contract_rows must contain each owner_row_id exactly once")
    if set(observed_ids) != _OWNER_ROW_IDS:
        missing = sorted(_OWNER_ROW_IDS - set(observed_ids))
        unexpected = sorted(set(observed_ids) - _OWNER_ROW_IDS)
        _invalid(schema_id, f"owner row set mismatch; missing={missing}, unexpected={unexpected}")

    for row in rows:
        owner_row_id = row["owner_row_id"]
        expected = {
            "positive_test_identity": f"W11-T01-{owner_row_id}",
            "negative_mutation_test_identity": f"W11-T03-{owner_row_id}-owner-row-mutation",
            "retry_test_identity": f"W11-T11-{owner_row_id}",
        }
        for field, expected_value in expected.items():
            if row[field] != expected_value:
                _invalid(schema_id, f"owner row {owner_row_id} {field} must be {expected_value}")


def _validate_scorecard_against_rubric(
    schema_id: str,
    value: Mapping[str, Any],
    *,
    reference_documents: Iterable[Mapping[str, Any]],
    validate_reference: ReferenceValidator | None,
) -> None:
    rubric_ref = value["rubric_ref"]
    matches: list[Mapping[str, Any]] = []
    for candidate in reference_documents:
        if not isinstance(candidate, Mapping):
            _invalid(schema_id, "reference documents must be mappings")
        if (
            candidate.get("schema_id") == W11_ASSAY_RUBRIC_SCHEMA_ID
            and candidate.get("schema_version") == "1.0.0"
            and candidate.get("record_id") == rubric_ref["id"]
            and candidate.get("record_revision") == rubric_ref["record_revision"]
            and candidate.get("content_hash") == rubric_ref["content_hash"]
        ):
            matches.append(candidate)

    if not matches:
        _invalid(schema_id, "rubric_ref could not be resolved to the frozen rubric")
    if len(matches) > 1:
        _invalid(schema_id, "rubric_ref resolved ambiguously")

    rubric = matches[0]
    if validate_reference is not None:
        validate_reference(W11_ASSAY_RUBRIC_SCHEMA_ID, rubric)

    axes: dict[str, Mapping[str, Any]] = {}
    for axis in rubric["axis_definitions"]:
        axis_id = axis["axis_id"]
        if axis_id in axes:
            _invalid(schema_id, f"frozen rubric contains duplicate axis {axis_id}")
        axes[axis_id] = axis
        expected_value_type = {
            "gate": "boolean",
            "integer_score": "integer",
            "registered_measure": "number",
        }[axis["axis_kind"]]
        if axis["value_type"] != expected_value_type:
            _invalid(schema_id, f"frozen rubric axis {axis_id} has an inconsistent value type")
        if "bounds" in axis and axis["bounds"]["minimum"] > axis["bounds"]["maximum"]:
            _invalid(schema_id, f"frozen rubric axis {axis_id} has descending bounds")

    required_axis_ids = set(rubric["required_axis_ids"])
    missing_rubric_axes = sorted(required_axis_ids - axes.keys())
    if missing_rubric_axes:
        _invalid(schema_id, f"frozen rubric required axes are undefined: {missing_rubric_axes}")

    observed_axis_ids: set[str] = set()
    for index, result in enumerate(value["axis_results"]):
        axis_id = result["axis_id"]
        if axis_id not in axes:
            _invalid(schema_id, f"axis_results[{index}] references unknown rubric axis {axis_id}")
        if axis_id in observed_axis_ids:
            _invalid(schema_id, f"axis_results contains duplicate rubric axis {axis_id}")
        observed_axis_ids.add(axis_id)
        axis = axes[axis_id]
        if result["axis_kind"] != axis["axis_kind"]:
            _invalid(
                schema_id,
                f"axis_results[{index}] axis kind mismatch for {axis_id}: expected {axis['axis_kind']}",
            )
        if not _value_is_in_frozen_domain(axis, result["value"]):
            _invalid(schema_id, f"axis_results[{index}] value is outside the frozen rubric domain for {axis_id}")

    missing_required_axes = sorted(required_axis_ids - observed_axis_ids)
    if missing_required_axes:
        _invalid(schema_id, f"axis_results is missing required rubric axes: {missing_required_axes}")


def _value_is_in_frozen_domain(axis: Mapping[str, Any], value: Any) -> bool:
    axis_kind = axis["axis_kind"]
    if axis_kind == "gate" and type(value) is not bool:
        return False
    if axis_kind == "integer_score" and (type(value) is not int or isinstance(value, bool)):
        return False
    if axis_kind == "registered_measure" and (
        not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value)
    ):
        return False

    if "allowed_set" in axis:
        return any(_same_scalar(value, allowed) for allowed in axis["allowed_set"])

    bounds = axis.get("bounds")
    if bounds is None:
        return False
    return bounds["minimum"] <= value <= bounds["maximum"]


def _same_scalar(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    return type(left) is type(right) and left == right
