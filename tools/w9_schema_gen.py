# Research context: docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md (WP9.1; P-065, P-069)
# Purpose: generate the inert ars://legacy/ schema family (W9 §5.2) so its committed bytes can be reproduced.
"""Generator for the W9 WP9.1 stage A schema family under `.research-system/schemas/contracts/w9/`.

This is a non-runtime tool (P-069 item 4). It writes only the 17 schema files it owns and reads nothing else. Every
shared definition is inlined in each schema, so no schema references another file; a test asserts that the 17 inlined
`$defs` blocks are identical.

Usage::

    python tools/w9_schema_gen.py [--check]

With `--check` it writes nothing and exits 1 if any committed schema differs from what it would generate.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / ".research-system" / "schemas" / "contracts" / "w9"

Schema = dict[str, Any]

UUID7 = "[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
# D-9's restricted suffixes (P-064 item 9), copied here under P-069 item 3. The contract's `restricted_suffixes` must
# equal this list (the stage A test asserts it); the schema pattern is derived from it, matched case-insensitively.
RESTRICTED_SUFFIXES = [".csv", ".pkl"]


def _any_case(text: str) -> str:
    return "".join(f"[{c.upper()}{c.lower()}]" if c.isalpha() else f"\\{c}" if c == "." else c for c in text)


RESTRICTED_SUFFIX = "(" + "|".join(_any_case(suffix) for suffix in RESTRICTED_SUFFIXES) + ")$"
CONVENTIONS_NAME = "(^|/)" + _any_case("CONVENTIONS.md") + "$"
# Relative, forward-slash only: no leading slash or "~", no backslash or ":", no "." / ".." / empty segment, no
# segment ending in "." or a space, no 8.3 short-name form ("~" and a digit), and no trailing whitespace. Win32 strips
# a trailing dot or space and resolves short names, so these would alias another path (review n-1). A trailing "/"
# (a directory root) is allowed. Full alias closure is the handle-bound read's (`physical_identity`).
REL_PATH_PATTERN = "^(?![/~])(?!.*[\\\\:])(?!.*//)(?!(.*/)?\\.\\.?(/|$))(?!.*[. ](/|$))(?!.*~[0-9])(?!.*\\s$).+$"


def _id(prefix: str) -> Schema:
    return {"type": "string", "pattern": f"^{prefix}_{UUID7}$"}


def _typed_ref(id_def: str) -> Schema:
    return {
        "type": "object",
        "required": ["id", "record_revision", "content_hash"],
        "properties": {
            "id": {"$ref": f"#/$defs/{id_def}"},
            "record_revision": {"type": "integer", "minimum": 1},
            "content_hash": {"$ref": "#/$defs/sha256"},
        },
        "additionalProperties": False,
    }


def ref(name: str) -> Schema:
    """Return a `$ref` to one of the inlined definitions."""
    return {"$ref": f"#/$defs/{name}"}


def arr(items: Schema, min_items: int = 0, unique: bool = False) -> Schema:
    """Return an array schema."""
    out: Schema = {"type": "array", "items": items}
    if min_items:
        out["minItems"] = min_items
    if unique:
        out["uniqueItems"] = True
    return out


def obj(required: list[str], properties: Schema, **extra: object) -> Schema:
    """Return a closed object schema."""
    out: Schema = {"type": "object", "required": required, "properties": properties, "additionalProperties": False}
    out.update(extra)
    return out


def when(prop: str, value: object, then: Schema, otherwise: Schema | None = None) -> Schema:
    """Return an `if`/`then`(/`else`) branch keyed on one property's constant value."""
    out: Schema = {"if": {"properties": {prop: {"const": value}}, "required": [prop]}, "then": then}
    if otherwise is not None:
        out["else"] = otherwise
    return out


def props(**properties: Schema) -> Schema:
    """Return a constraint on property values only."""
    return {"properties": properties}


TEXT: Schema = {"type": "string", "minLength": 1}
FAMILY_NAME: Schema = {"type": "string", "pattern": "^[a-z0-9_]+$"}
IDENTITY_KINDS = ["git_tracked", "untracked_file", "restricted_untracked_file", "vault_file"]
UNRESTRICTED_PATH: Schema = {"allOf": [ref("relPath"), {"not": {"pattern": RESTRICTED_SUFFIX}}]}
# A vault path never names CONVENTIONS.md: its vault alias is a prohibited read path for observations (W9 §7.3;
# confirmation r-1).
VAULT_PATH: Schema = {"allOf": [UNRESTRICTED_PATH, {"not": {"pattern": CONVENTIONS_NAME}}]}

# W9 §5.4 source identity kinds. A restricted file has no frozen-copy field (W9-T11), and every other kind refuses a
# restricted suffix, so a mislabelled restricted file cannot carry a frozen copy (P-069 item 3).
SOURCE_IDENTITY: Schema = {
    "oneOf": [
        obj(
            ["identity_kind", "repository_path", "git_commit", "git_blob", "sha256", "byte_length"],
            {
                "identity_kind": {"const": "git_tracked"},
                "repository_path": UNRESTRICTED_PATH,
                "git_commit": ref("sha1"),
                "git_blob": ref("sha1"),
                "sha256": ref("sha256"),
                "byte_length": {"type": "integer", "minimum": 0},
            },
        ),
        obj(
            ["identity_kind", "path", "sha256", "byte_length", "frozen_copy_ref"],
            {
                "identity_kind": {"const": "untracked_file"},
                "path": UNRESTRICTED_PATH,
                "sha256": ref("sha256"),
                "byte_length": {"type": "integer", "minimum": 0},
                "frozen_copy_ref": ref("artefactRef"),
            },
        ),
        obj(
            ["identity_kind", "path", "sha256", "byte_length"],
            {
                "identity_kind": {"const": "restricted_untracked_file"},
                "path": ref("relPath"),
                "sha256": ref("sha256"),
                "byte_length": {"type": "integer", "minimum": 0},
            },
        ),
        obj(
            ["identity_kind", "vault_path", "sha256", "byte_length", "frozen_copy_ref"],
            {
                "identity_kind": {"const": "vault_file"},
                "vault_path": VAULT_PATH,
                "sha256": ref("sha256"),
                "byte_length": {"type": "integer", "minimum": 0},
                "frozen_copy_ref": ref("artefactRef"),
            },
        ),
    ]
}
PHYSICAL_IDENTITY = obj(
    [
        "canonical_target",
        "reparse_chain",
        "volume_serial_number",
        "stable_file_id",
        "link_count",
        "case_aliases",
        "unicode_aliases",
        "short_name_aliases",
    ],
    {
        "canonical_target": TEXT,
        "reparse_chain": arr(TEXT),
        "volume_serial_number": TEXT,
        "stable_file_id": TEXT,
        "link_count": {"type": "integer", "minimum": 1},
        "case_aliases": arr(TEXT),
        "unicode_aliases": arr(TEXT),
        "short_name_aliases": arr(TEXT),
    },
)
FILE_FACTS: Schema = {
    "oneOf": [
        {"type": "null"},
        obj(
            ["line_ending", "ends_with_terminator", "has_utf8_bom", "line_count"],
            {
                "line_ending": {"enum": ["LF", "CRLF", "mixed", "none"]},
                "ends_with_terminator": {"type": "boolean"},
                "has_utf8_bom": {"type": "boolean"},
                "line_count": {"type": "integer", "minimum": 0},
            },
        ),
    ]
}
QUALIFIER = obj(
    ["qualifier_kind", "source_ref", "text"],
    {
        "qualifier_kind": {"enum": ["open_review_finding", "audit_verdict", "stale_projection_of", "corrected_by"]},
        "source_ref": ref("sourceRef"),
        "text": TEXT,
    },
)
# A file at an exact commit, for code, contracts and envelopes (the acceptance envelope and genesis input, M-6, m-7).
CODE_IDENTITY = obj(
    ["repository_path", "git_commit", "git_blob", "file_length", "file_sha256"],
    {
        "repository_path": ref("relPath"),
        "git_commit": ref("sha1"),
        "git_blob": ref("sha1"),
        "file_length": {"type": "integer", "minimum": 1},
        "file_sha256": ref("sha256"),
    },
)

# Reference kinds (review B-1). W9 records are obj_; W2 Decisions dec_, reviews rev_, artefacts art_, tasks tsk_.
# A field whose target kind W9 does not fix takes anyRef, a closed oneOf over the named kinds, never a free string.
DEFS: Schema = {
    "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "sha1": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
    "objId": _id("obj"),
    "decId": _id("dec"),
    "revId": _id("rev"),
    "artId": _id("art"),
    "tskId": _id("tsk"),
    "evtId": _id("evt"),
    "projectId": _id("prj"),
    "actorId": _id("act"),
    "utc": {"type": "string", "format": "date-time", "pattern": "Z$"},
    "utcMicros": {
        "type": "string",
        "format": "date-time",
        "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{6}Z$",
    },
    "relPath": {"type": "string", "minLength": 1, "pattern": REL_PATH_PATTERN},
    "recordRef": _typed_ref("objId"),
    "decisionRef": _typed_ref("decId"),
    "reviewRef": _typed_ref("revId"),
    "artefactRef": _typed_ref("artId"),
    "taskRef": _typed_ref("tskId"),
    "anyRef": {"oneOf": [ref("recordRef"), ref("decisionRef"), ref("reviewRef"), ref("artefactRef"), ref("taskRef")]},
    "nullableRecordRef": {"oneOf": [{"type": "null"}, ref("recordRef")]},
    "nullableAnyRef": {"oneOf": [{"type": "null"}, ref("anyRef")]},
    # A source ARS has not observed: a repository file at a commit or a vault file, as W11's `sourceRef` `external`
    # form. W9-T4 imports SUPERSEDED.md lines 69-71 alone while naming the tier-1 file (re-review N-2).
    "sourceLocator": {
        "oneOf": [
            obj(
                ["locator_kind", "repository_path", "git_commit", "git_blob", "sha256", "byte_length", "line_span"],
                {
                    "locator_kind": {"const": "git_file"},
                    "repository_path": UNRESTRICTED_PATH,
                    "git_commit": ref("sha1"),
                    "git_blob": ref("sha1"),
                    "sha256": ref("sha256"),
                    "byte_length": {"type": "integer", "minimum": 0},
                    "line_span": {
                        "oneOf": [
                            {"type": "null"},
                            obj(
                                ["first_line", "last_line"],
                                {
                                    "first_line": {"type": "integer", "minimum": 1},
                                    "last_line": {"type": "integer", "minimum": 1},
                                },
                            ),
                        ]
                    },
                },
            ),
            obj(
                ["locator_kind", "vault_path", "sha256", "byte_length", "heading_anchor"],
                {
                    "locator_kind": {"const": "vault_file"},
                    "vault_path": VAULT_PATH,
                    "sha256": ref("sha256"),
                    "byte_length": {"type": "integer", "minimum": 0},
                    "heading_anchor": {"type": ["string", "null"], "minLength": 1},
                },
            ),
        ]
    },
    "sourceRef": {"oneOf": [ref("anyRef"), ref("sourceLocator")]},
    "physicalIdentity": PHYSICAL_IDENTITY,
    "sourceIdentity": SOURCE_IDENTITY,
    "fileFacts": FILE_FACTS,
    "qualifier": QUALIFIER,
}

W0_CLASSES = [
    "authoritative",
    "authoritative_supersession",
    "merged_draft",
    "prepared",
    "active",
    "blocked",
    "deferred",
    "superseded",
    "stale_projection",
    "unverified",
]
SELECTOR_KINDS = [
    "heading_section",
    "computational_log_entry",
    "tracker_task_row",
    "working_note_entry",
    "log_frontmatter",
    "conventions_unit",
]
FIXED_REGION_SELECTORS = ["tracker_task_row", "working_note_entry", "log_frontmatter", "conventions_unit"]
SEGMENTATION: Schema = {"const": "w9-segmentation/1.0.0"}
FIXTURE_ID: Schema = {"type": "string", "pattern": "^[FS]-[0-9]{3}$"}
ROLES = [
    "legacy_research_result",
    "legacy_supersession_manifest",
    "legacy_pre_registration",
    "legacy_contract",
    "shared_enforcement_surface",
    "legacy_coordination",
    "legacy_task_log",
    "legacy_bus_file",
    "legacy_manuscript_root",
    "legacy_decision_log_entry",
    "conventions_lock",
    "successor_results_root",
    "legacy_read_only_projection",
]
ARS_ROLES = ["successor_results_root", "legacy_read_only_projection"]
LEGACY_ROLES = [role for role in ROLES if role not in ARS_ROLES and role != "shared_enforcement_surface"]
MODES = ["legacy_owned", "successor_owned", "closed_reference"]
# W9 §4.2's three legacy writer classes, §4.3's shared-surface class, and the ARS writer of an ARS-owned path.
LEGACY_WRITER_CLASSES = ["legacy_lane_commit", "repository_wide_change_with_owner_note", "owner_ruling"]
WRITER_CLASSES = [
    *LEGACY_WRITER_CLASSES,
    "ars_reviewed_pr_with_owner_note",
    "ars_reviewed_pr",
    "ars_projection_rebuild",
]
P01_ROOTS = ["papers/P01-A-JRSSA/", "papers/P01-B-JRSSB/"]


def header(kind: str) -> tuple[list[str], Schema]:
    """Return the required keys and properties shared by every W9 record.

    W9 records are immutable: a correction is a `legacy-record-supersession` (W9 §13.2), so the revision is always 1
    (review m-1).
    """
    required = [
        "schema_id",
        "schema_version",
        "record_id",
        "record_revision",
        "supersedes_revision",
        "project_id",
        "created_at",
        "created_by_actor_id",
        "content_hash",
    ]
    properties: Schema = {
        "schema_id": {"const": f"ars://legacy/{kind}"},
        "schema_version": {"const": "1.0.0"},
        "record_id": ref("objId"),
        "record_revision": {"const": 1},
        "supersedes_revision": {"const": None},
        "project_id": ref("projectId"),
        "created_at": ref("utc"),
        "created_by_actor_id": ref("actorId"),
        "content_hash": ref("sha256"),
    }
    return required, properties


def record(kind: str, fields: Schema, required_extra: list[str], extra: Schema | None = None) -> Schema:
    """Return one closed record schema with the shared header and inlined definitions."""
    required, properties = header(kind)
    properties.update(fields)
    schema: Schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"ars://legacy/{kind}",
        "type": "object",
        "required": required + required_extra,
        "properties": properties,
        "additionalProperties": False,
    }
    if extra:
        schema.update(extra)
    schema["$defs"] = deepcopy(DEFS)
    return schema


def bootstrap_schema(kind: str, body: Schema) -> Schema:
    """Return one bootstrap schema with inlined definitions."""
    out: Schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"ars://legacy/{kind}"}
    out.update(body)
    out["$defs"] = deepcopy(DEFS)
    return out


SCHEMAS: dict[str, Schema] = {}

SCHEMAS["legacy-path-registration"] = record(
    "legacy-path-registration",
    {
        "root_kind": {"enum": ["repository_root", "vault_root"]},
        "root_id": TEXT,
        "normalized_path": ref("relPath"),
        "physical_identity": ref("physicalIdentity"),
        "source_identity_kind": {"enum": IDENTITY_KINDS},
        "role": {"enum": ROLES},
        "ownership_mode": {"enum": MODES},
        "writer_classes": arr({"enum": WRITER_CLASSES}, unique=True),
        "prohibited_consumers": arr(TEXT, unique=True),
        "registration_decision_ref": ref("decisionRef"),
    },
    [
        "root_kind",
        "root_id",
        "normalized_path",
        "physical_identity",
        "source_identity_kind",
        "role",
        "ownership_mode",
        "writer_classes",
        "prohibited_consumers",
        "registration_decision_ref",
    ],
    {
        "allOf": [
            when(
                "role",
                "successor_results_root",
                props(
                    ownership_mode={"const": "successor_owned"},
                    root_kind={"const": "repository_root"},
                    normalized_path={"const": "results/ars/"},
                ),
            ),
            # Only conventions_lock names CONVENTIONS.md, and only at its repository path (W9 §7.3; review M-2).
            when(
                "role",
                "conventions_lock",
                props(
                    root_kind={"const": "repository_root"},
                    normalized_path={"const": "CONVENTIONS.md"},
                    source_identity_kind={"const": "git_tracked"},
                ),
                props(normalized_path={"not": {"pattern": CONVENTIONS_NAME}}),
            ),
            when(
                "role",
                "legacy_manuscript_root",
                props(root_kind={"const": "repository_root"}, normalized_path={"enum": P01_ROOTS}),
            ),
            # Writers (W9 §4.2, §4.3; review M-1): no successor writer on a legacy file.
            {
                "if": {"properties": {"role": {"enum": LEGACY_ROLES}}, "required": ["role"]},
                "then": props(writer_classes=arr({"enum": LEGACY_WRITER_CLASSES}, unique=True)),
            },
            when(
                "role",
                "shared_enforcement_surface",
                props(writer_classes={"const": ["ars_reviewed_pr_with_owner_note"]}),
            ),
            when("role", "successor_results_root", props(writer_classes={"const": ["ars_reviewed_pr"]})),
            # The read-only projection (W9 §7.2, 06v O-16) is gitignored and written only by `ars projection rebuild`
            # from the store; no PR can write it (re-review N-1).
            when(
                "role",
                "legacy_read_only_projection",
                props(
                    ownership_mode={"const": "successor_owned"},
                    root_kind={"const": "repository_root"},
                    normalized_path={"pattern": "^\\.research-system/projections/legacy/"},
                    source_identity_kind={"const": "untracked_file"},
                    writer_classes={"const": ["ars_projection_rebuild"]},
                ),
            ),
            # A vault root holds vault files, and only vault files sit under one (review m-3).
            when(
                "root_kind",
                "vault_root",
                props(source_identity_kind={"const": "vault_file"}),
                props(source_identity_kind={"enum": [k for k in IDENTITY_KINDS if k != "vault_file"]}),
            ),
            # A restricted suffix is registrable only as restricted (P-069 item 3; review M-3).
            {
                "if": {
                    "properties": {"normalized_path": {"pattern": RESTRICTED_SUFFIX}},
                    "required": ["normalized_path"],
                },
                "then": props(source_identity_kind={"const": "restricted_untracked_file"}),
            },
        ]
    },
)

SCHEMAS["legacy-field-family-membership"] = record(
    "legacy-field-family-membership",
    {
        "file_schema_id": TEXT,
        # The bytes the table's author read (membership template §3 rule 10); a git_tracked file must name its blob.
        "applies_to": arr(
            {
                **obj(
                    ["path", "identity_kind", "git_blob", "sha256", "size_bytes"],
                    {
                        "path": ref("relPath"),
                        "identity_kind": {"enum": IDENTITY_KINDS},
                        "git_blob": {"oneOf": [ref("sha1"), {"type": "null"}]},
                        "sha256": ref("sha256"),
                        "size_bytes": {"type": "integer", "minimum": 0},
                    },
                ),
                **when("identity_kind", "git_tracked", props(git_blob=ref("sha1")), props(git_blob={"type": "null"})),
            },
            1,
        ),
        "table_sha256": ref("sha256"),
        "families": arr(
            obj(
                ["name", "definition_source", "pointers"],
                {
                    "name": FAMILY_NAME,
                    "definition_source": TEXT,
                    "pointers": arr({"type": "string", "pattern": "^(/([^~/]|~[01])*)*$"}, 1, unique=True),
                },
            ),
            1,
        ),
        "unassigned": arr({"type": "string", "pattern": "^(/([^~/]|~[01])*)*$"}, unique=True),
        "author_actor_id": ref("actorId"),
        "review_ref": ref("reviewRef"),
        "acceptance_decision_ref": ref("decisionRef"),
    },
    [
        "file_schema_id",
        "applies_to",
        "table_sha256",
        "families",
        "unassigned",
        "author_actor_id",
        "review_ref",
        "acceptance_decision_ref",
    ],
)

# One row as `tools/w9_segmentation.py` emits it, plus its selector kind; a field a selector does not emit is null
# (review B-2; segmentation contract §3, §4, §6.4).
INVENTORY_ROW = obj(
    [
        "row_ordinal",
        "row_kind",
        "selector_kind",
        "anchor_text",
        "unit_hash",
        "unit_ordinal",
        "dated",
        "task_id",
        "start_byte",
        "byte_length",
        "start_line",
        "line_count",
        "raw_row_sha256",
        "anchor_line_sha256",
        "blocker_reason",
    ],
    {
        "row_ordinal": {"type": "integer", "minimum": 1},
        "row_kind": {"enum": ["item", "blocker", "structural"]},
        "selector_kind": {"enum": SELECTOR_KINDS},
        "anchor_text": {"type": ["string", "null"]},
        "unit_hash": {"oneOf": [{"type": "null"}, ref("sha256")]},
        "unit_ordinal": {"type": ["integer", "null"], "minimum": 1},
        "dated": {"type": ["boolean", "null"]},
        "task_id": {"oneOf": [{"type": "null"}, {"type": "string", "pattern": "^T[0-9]+\\.[0-9]+[a-z]*(-[a-z]+)?$"}]},
        "start_byte": {"type": "integer", "minimum": 0},
        "byte_length": {"type": "integer", "minimum": 0},
        "start_line": {"type": "integer", "minimum": 1},
        "line_count": {"type": "integer", "minimum": 0},
        "raw_row_sha256": ref("sha256"),
        "anchor_line_sha256": {"oneOf": [{"type": "null"}, ref("sha256")]},
        "blocker_reason": {"enum": [None, "duplicate_anchor", "unaddressed_region", "unparseable_anchor"]},
    },
    allOf=[
        when(
            "row_kind",
            "blocker",
            props(blocker_reason={"enum": ["duplicate_anchor", "unaddressed_region", "unparseable_anchor"]}),
            props(blocker_reason={"const": None}),
        ),
        when("row_kind", "item", props(anchor_text={"type": "string"})),
        # Only an empty file yields a zero-length row: one unparseable blocker at byte 0 (contract §4.5).
        when(
            "line_count",
            0,
            props(
                row_kind={"const": "blocker"},
                blocker_reason={"const": "unparseable_anchor"},
                byte_length={"const": 0},
                start_byte={"const": 0},
                anchor_line_sha256={"type": "null"},
            ),
            props(byte_length={"minimum": 1}, anchor_line_sha256=ref("sha256")),
        ),
        when(
            "selector_kind",
            "conventions_unit",
            props(unit_hash=ref("sha256"), unit_ordinal={"type": "integer", "minimum": 1}),
            props(unit_hash={"type": "null"}, unit_ordinal={"type": "null"}),
        ),
        {
            "if": {"properties": {"selector_kind": {"const": "working_note_entry"}, "row_kind": {"const": "item"}}},
            "then": props(dated={"type": "boolean"}),
        },
        {"if": {"not": props(selector_kind={"const": "working_note_entry"})}, "then": props(dated={"type": "null"})},
        {
            "if": {"properties": {"selector_kind": {"const": "tracker_task_row"}, "row_kind": {"const": "item"}}},
            "then": props(task_id={"type": "string"}),
        },
        {"if": {"not": props(selector_kind={"const": "tracker_task_row"})}, "then": props(task_id={"type": "null"})},
    ],
)
COVERED_REGION: Schema = {
    "oneOf": [
        obj(["form"], {"form": {"const": "fixed_by_selector"}}),
        obj(
            ["form", "first_line", "last_line", "anchor_line_sha256s"],
            {
                "form": {"const": "line_range"},
                "first_line": {"type": "integer", "minimum": 1},
                "last_line": {"type": "integer", "minimum": 1},
                "anchor_line_sha256s": arr(ref("sha256")),
            },
        ),
        obj(
            ["form", "after_line", "after_line_sha256", "resolved_first_line", "resolved_last_line"],
            {
                "form": {"const": "first_anchor_after"},
                "after_line": {"type": "integer", "minimum": 1},
                "after_line_sha256": ref("sha256"),
                "resolved_first_line": {"type": "integer", "minimum": 1},
                "resolved_last_line": {"type": "integer", "minimum": 1},
            },
        ),
    ]
}
SCHEMAS["legacy-light-inventory"] = record(
    "legacy-light-inventory",
    {
        "registration_ref": ref("recordRef"),
        "source_identity": ref("sourceIdentity"),
        "segmentation_contract": SEGMENTATION,
        "selector_kind": {"enum": SELECTOR_KINDS},
        "heading_level": {"type": ["integer", "null"], "minimum": 1, "maximum": 6},
        "covered_region": COVERED_REGION,
        "structural_ranges": arr(
            obj(
                ["first_line", "last_line"],
                {"first_line": {"type": "integer", "minimum": 1}, "last_line": {"type": "integer", "minimum": 1}},
            )
        ),
        "suppressed_anchors": arr(
            obj(
                ["line", "anchor_line_sha256", "heading_text"],
                {
                    "line": {"type": "integer", "minimum": 1},
                    "anchor_line_sha256": ref("sha256"),
                    "heading_text": {"type": ["string", "null"]},
                },
            )
        ),
        "file_facts": ref("fileFacts"),
        "read_started_at": ref("utcMicros"),
        "read_ended_at": ref("utcMicros"),
        "path_form": obj(
            ["path_as_given", "resolved_through_link", "resolved_target"],
            {
                "path_as_given": TEXT,
                "resolved_through_link": {"type": "boolean"},
                "resolved_target": {"type": ["string", "null"], "minLength": 1},
            },
        ),
        "observer_actor_id": ref("actorId"),
        "rows": arr(INVENTORY_ROW, 1),
        "independent_reproduction_ref": ref("anyRef"),
    },
    [
        "registration_ref",
        "source_identity",
        "segmentation_contract",
        "selector_kind",
        "heading_level",
        "covered_region",
        "structural_ranges",
        "suppressed_anchors",
        "file_facts",
        "read_started_at",
        "read_ended_at",
        "path_form",
        "observer_actor_id",
        "rows",
        "independent_reproduction_ref",
    ],
    {
        "allOf": [
            when(
                "selector_kind",
                "heading_section",
                props(
                    heading_level={"type": "integer"},
                    covered_region={"properties": {"form": {"enum": ["line_range", "first_anchor_after"]}}},
                ),
                props(
                    heading_level={"type": "null"},
                    structural_ranges={"maxItems": 0},
                    suppressed_anchors={"maxItems": 0},
                ),
            ),
            {
                "if": {
                    "properties": {"selector_kind": {"enum": FIXED_REGION_SELECTORS}},
                    "required": ["selector_kind"],
                },
                "then": props(covered_region={"properties": {"form": {"const": "fixed_by_selector"}}}),
            },
            {
                "if": props(path_form=props(resolved_through_link={"const": False})),
                "then": props(path_form=props(resolved_target={"type": "null"})),
                "else": props(path_form=props(resolved_target={"type": "string"})),
            },
            # Every row has the inventory's own selector kind (re-review n-4).
            *(
                when("selector_kind", kind, props(rows={"items": props(selector_kind={"const": kind})}))
                for kind in SELECTOR_KINDS
            ),
        ]
    },
)

SELECTOR: Schema = {
    "oneOf": [
        obj(["selector_kind"], {"selector_kind": {"const": "whole_file"}}),
        obj(
            ["selector_kind", "membership_ref", "family_names"],
            {
                "selector_kind": {"const": "json_family_set"},
                "membership_ref": ref("recordRef"),
                "family_names": arr(FAMILY_NAME, 1, unique=True),
            },
        ),
        obj(
            ["selector_kind", "inventory_ref", "row_ordinal", "anchor_text", "raw_row_sha256"],
            {
                "selector_kind": {"const": "inventory_item"},
                "inventory_ref": ref("recordRef"),
                "row_ordinal": {"type": "integer", "minimum": 1},
                "anchor_text": TEXT,
                "raw_row_sha256": ref("sha256"),
            },
        ),
    ]
}
SCHEMAS["legacy-observation"] = record(
    "legacy-observation",
    {
        "registration_ref": ref("recordRef"),
        "selector": SELECTOR,
        "source_identity": ref("sourceIdentity"),
        "segmentation_contract": {"oneOf": [{"type": "null"}, SEGMENTATION]},
        "file_facts": ref("fileFacts"),
        "importer": obj(
            ["actor_id", "tool_id", "tool_version", "tool_sha256"],
            {"actor_id": ref("actorId"), "tool_id": TEXT, "tool_version": TEXT, "tool_sha256": ref("sha256")},
        ),
        "observer_actor_id": ref("actorId"),
        "observed_at": ref("utc"),
        "families": arr(
            obj(
                ["family_name", "w0_class", "signed_w0_revision_ref", "signature_record_ref"],
                {
                    "family_name": FAMILY_NAME,
                    "w0_class": {"enum": W0_CLASSES},
                    "signed_w0_revision_ref": ref("sourceRef"),
                    "signature_record_ref": ref("anyRef"),
                },
            ),
            1,
        ),
        "qualifiers": arr(ref("qualifier")),
        "conflicts": arr(
            obj(
                ["conflicting_record_refs", "resolution", "precedence_tier"],
                {
                    "conflicting_record_refs": arr(ref("sourceRef"), 2, unique=True),
                    "resolution": {"enum": ["resolved_by_precedence", "blocked"]},
                    "precedence_tier": {"type": ["integer", "null"], "minimum": 1, "maximum": 7},
                },
                allOf=[
                    when(
                        "resolution",
                        "resolved_by_precedence",
                        props(precedence_tier={"type": "integer"}),
                        props(precedence_tier={"type": "null"}),
                    )
                ],
            )
        ),
        "non_inferences": arr(TEXT, 1),
    },
    [
        "registration_ref",
        "selector",
        "source_identity",
        "segmentation_contract",
        "file_facts",
        "importer",
        "observer_actor_id",
        "observed_at",
        "families",
        "qualifiers",
        "conflicts",
        "non_inferences",
    ],
    {
        "allOf": [
            # Only an inventory-item selector is cut by the segmentation contract (review m-4).
            {
                "if": props(selector=props(selector_kind={"const": "inventory_item"})),
                "then": props(segmentation_contract=SEGMENTATION),
                "else": props(segmentation_contract={"type": "null"}),
            }
        ]
    },
)

# Per-fixture evidence or waiver (O-37; review M-5); a waiver is an owner-accepted Decision (W9 §12.3).
PILOT_PROMOTION_ENTRY = obj(
    ["fixture_id", "disposition", "ref"],
    {"fixture_id": FIXTURE_ID, "disposition": {"enum": ["evidence", "waiver"]}, "ref": ref("anyRef")},
    allOf=[when("disposition", "waiver", props(ref=ref("decisionRef")))],
)
ANCHOR = obj(
    ["anchored", "anchor_kind", "value"],
    {
        "anchored": {"enum": ["threshold_preregistration", "governing_record_set"]},
        "anchor_kind": {"enum": ["git_commit", "ars_event"]},
        "value": TEXT,
    },
    allOf=[when("anchor_kind", "git_commit", props(value=ref("sha1")), props(value=ref("evtId")))],
)
SCHEMAS["legacy-closed-reference-acceptance"] = record(
    "legacy-closed-reference-acceptance",
    {
        "independent_review_ref": ref("reviewRef"),
        "decision_ref": ref("decisionRef"),
        "items": arr(
            obj(
                ["observation_ref", "pilot_promotion"],
                {"observation_ref": ref("recordRef"), "pilot_promotion": arr(PILOT_PROMOTION_ENTRY, 1, unique=True)},
            ),
            1,
            unique=True,
        ),
        "threshold_preregistration_sha256": ref("sha256"),
        "governing_record_set_sha256": ref("sha256"),
        "anchors": {
            **arr(ANCHOR, 2, unique=True),
            "allOf": [
                {"contains": props(anchored={"const": "threshold_preregistration"}), "maxContains": 1},
                {"contains": props(anchored={"const": "governing_record_set"}), "maxContains": 1},
            ],
        },
        "enforcement_change_list": {
            "oneOf": [
                {"type": "null"},
                obj(["git_commit", "git_blob"], {"git_commit": ref("sha1"), "git_blob": ref("sha1")}),
            ]
        },
    },
    [
        "independent_review_ref",
        "decision_ref",
        "items",
        "threshold_preregistration_sha256",
        "governing_record_set_sha256",
        "anchors",
        "enforcement_change_list",
    ],
)

SCHEMAS["legacy-adoption-decision"] = record(
    "legacy-adoption-decision",
    {
        "observation_ref": ref("recordRef"),
        "subject": {
            "oneOf": [
                obj(
                    ["subject_kind", "family_names"],
                    {"subject_kind": {"const": "families"}, "family_names": arr(FAMILY_NAME, 1, unique=True)},
                ),
                obj(
                    ["subject_kind", "rehash_at_use"],
                    {"subject_kind": {"const": "whole_file"}, "rehash_at_use": {"const": True}},
                ),
            ]
        },
        "intended_use": obj(
            ["description", "successor_ref"], {"description": TEXT, "successor_ref": ref("nullableAnyRef")}
        ),
        "w5_consequence": TEXT,
        "qualifiers_to_discharge": arr(ref("qualifier")),
        "decision_ref": ref("decisionRef"),
    },
    ["observation_ref", "subject", "intended_use", "w5_consequence", "qualifiers_to_discharge", "decision_ref"],
)

SCHEMAS["legacy-discharge-relation"] = record(
    "legacy-discharge-relation",
    {
        "successor_result_ref": ref("artefactRef"),
        "legacy_item": obj(
            ["item_kind", "item_id"],
            {"item_kind": {"enum": ["a001_item", "audit_hole", "review_finding"]}, "item_id": TEXT},
        ),
        "reviewer_ref": ref("reviewRef"),
        "decision_ref": ref("decisionRef"),
    },
    ["successor_result_ref", "legacy_item", "reviewer_ref", "decision_ref"],
)

SCHEMAS["legacy-paper-root"] = record(
    "legacy-paper-root",
    {
        "paper_key": {"enum": ["P01-A", "P01-B"]},
        "manuscript_root_path": {"enum": P01_ROOTS},
        "qualifiers": arr(ref("qualifier")),
        "owner_actor_id": ref("actorId"),
        "recovery": {
            "oneOf": [
                {"type": "null"},
                obj(
                    ["predecessor_root_ref", "recovery_decision_ref"],
                    {"predecessor_root_ref": ref("recordRef"), "recovery_decision_ref": ref("decisionRef")},
                ),
            ]
        },
    },
    ["paper_key", "manuscript_root_path", "qualifiers", "owner_actor_id", "recovery"],
    {
        "allOf": [
            when("paper_key", "P01-A", props(manuscript_root_path={"const": P01_ROOTS[0]})),
            when("paper_key", "P01-B", props(manuscript_root_path={"const": P01_ROOTS[1]})),
        ]
    },
)

SCHEMAS["legacy-paper-citation-status"] = record(
    "legacy-paper-citation-status",
    {
        "root_ref": ref("recordRef"),
        "cited_family_set_sha256": ref("sha256"),
        "derivation": obj(
            ["extractor_output_sha256", "reviewer_derivation_sha256", "reviewer_actor_id"],
            {
                "extractor_output_sha256": ref("sha256"),
                "reviewer_derivation_sha256": ref("sha256"),
                "reviewer_actor_id": ref("actorId"),
            },
        ),
        "families": arr(
            obj(
                ["observation_ref", "family_name", "status", "adoption_ref"],
                {
                    "observation_ref": ref("recordRef"),
                    "family_name": FAMILY_NAME,
                    "status": {"enum": ["adopted", "unadopted"]},
                    "adoption_ref": ref("nullableRecordRef"),
                },
                allOf=[
                    when(
                        "status",
                        "adopted",
                        props(adoption_ref=ref("recordRef")),
                        props(adoption_ref={"type": "null"}),
                    )
                ],
            ),
            1,
        ),
        "supersedes_status_ref": ref("nullableRecordRef"),
    },
    ["root_ref", "cited_family_set_sha256", "derivation", "families", "supersedes_status_ref"],
)

SCHEMAS["legacy-source-inventory"] = record(
    "legacy-source-inventory",
    {
        "root_registration_ref": ref("recordRef"),
        "segmentation_contract": SEGMENTATION,
        "rows": arr(
            obj(
                ["row_ordinal", "repository_path", "git_blob", "observation_ref"],
                {
                    "row_ordinal": {"type": "integer", "minimum": 1},
                    "repository_path": ref("relPath"),
                    "git_blob": ref("sha1"),
                    "observation_ref": ref("recordRef"),
                },
            ),
            1,
        ),
        "observer_actor_id": ref("actorId"),
        "reviewer_ref": ref("reviewRef"),
        "decision_ref": ref("decisionRef"),
    },
    ["root_registration_ref", "segmentation_contract", "rows", "observer_actor_id", "reviewer_ref", "decision_ref"],
)

SCHEMAS["legacy-transition-mapping"] = record(
    "legacy-transition-mapping",
    {
        "source_inventory_ref": ref("recordRef"),
        "target_paper_root_ref": ref("recordRef"),
        "mapped_row_ordinals": arr({"type": "integer", "minimum": 1}, 1, unique=True),
        "analyst_actor_id": ref("actorId"),
        "reviewer_ref": ref("reviewRef"),
        "decision_ref": ref("decisionRef"),
    },
    [
        "source_inventory_ref",
        "target_paper_root_ref",
        "mapped_row_ordinals",
        "analyst_actor_id",
        "reviewer_ref",
        "decision_ref",
    ],
)

SCHEMAS["legacy-ownership-transitioned"] = record(
    "legacy-ownership-transitioned",
    {
        "mapping_ref": ref("nullableRecordRef"),
        "subject_registration_ref": ref("recordRef"),
        "paper_root_ref": ref("nullableRecordRef"),
        "from_mode": {"enum": ["legacy_owned", "successor_owned"]},
        "to_mode": {"enum": ["successor_owned", "closed_reference"]},
        "reviewer_ref": ref("reviewRef"),
        "decision_ref": ref("decisionRef"),
    },
    [
        "mapping_ref",
        "subject_registration_ref",
        "paper_root_ref",
        "from_mode",
        "to_mode",
        "reviewer_ref",
        "decision_ref",
    ],
    {
        # W9 §8.2's three transitions; only a transition to successor_owned names a mapping and a root (review m-2).
        "oneOf": [
            props(
                from_mode={"const": "legacy_owned"},
                to_mode={"const": "successor_owned"},
                mapping_ref=ref("recordRef"),
                paper_root_ref=ref("recordRef"),
            ),
            props(
                from_mode={"const": "legacy_owned"},
                to_mode={"const": "closed_reference"},
                mapping_ref={"type": "null"},
                paper_root_ref={"type": "null"},
            ),
            props(
                from_mode={"const": "successor_owned"},
                to_mode={"const": "closed_reference"},
                mapping_ref={"type": "null"},
                paper_root_ref={"type": "null"},
            ),
        ]
    },
)

# Targets: an observation, closed-reference acceptance, adoption or mapping (W9 §13.1-13.2, read by P-070 over §5.2's
# narrower row). A record ID does not carry its kind, so the target set is declared in the stage A test's edge table.
SCHEMAS["legacy-record-supersession"] = record(
    "legacy-record-supersession",
    {
        "superseded_ref": ref("recordRef"),
        "replacing_ref": ref("recordRef"),
        "reason": TEXT,
        "reviewer_ref": ref("reviewRef"),
        "decision_ref": ref("decisionRef"),
    },
    ["superseded_ref", "replacing_ref", "reason", "reviewer_ref", "decision_ref"],
)

SCHEMA_FILE_IDENTITY = obj(
    ["repository_path", "schema_id", "schema_version", "git_commit", "git_blob", "file_length", "file_sha256"],
    {
        "repository_path": ref("relPath"),
        "schema_id": {"type": "string", "pattern": "^ars://legacy/[a-z0-9-]+$"},
        "schema_version": {"const": "1.0.0"},
        "git_commit": ref("sha1"),
        "git_blob": ref("sha1"),
        "file_length": {"type": "integer", "minimum": 1},
        "file_sha256": ref("sha256"),
    },
)
SPEC_IDENTITY = obj(
    ["repository_path", "reviewed_commit", "git_blob", "raw_sha256", "raw_bytes"],
    {
        "repository_path": ref("relPath"),
        "reviewed_commit": ref("sha1"),
        "git_blob": ref("sha1"),
        "raw_sha256": ref("sha256"),
        "raw_bytes": {"type": "integer", "minimum": 1},
    },
)
W11_CATALOGUE_IDENTITY = obj(
    ["repository_path", "git_blob", "raw_sha256", "raw_bytes"],
    {
        "repository_path": ref("relPath"),
        "git_blob": ref("sha1"),
        "raw_sha256": ref("sha256"),
        "raw_bytes": {"type": "integer", "minimum": 1},
    },
)

# Modelled on W11's envelope, which binds the verifier and the binding tests (review M-6).
SCHEMAS["w9-catalogue-acceptance-envelope"] = bootstrap_schema(
    "w9-catalogue-acceptance-envelope",
    obj(
        [
            "schema_id",
            "schema_version",
            "specification_identity",
            "plan_identity",
            "catalogue_identity",
            "schema_identities",
            "owner_row_multiset_hash",
            "bootstrap_contract_identity",
            "schema_generator_identity",
            "verifier_identity",
            "binding_test_identities",
            "independent_observation_ref",
            "independent_review_ref",
            "acceptance_decision_ref",
            "accepted_at",
            "acceptance_scope",
        ],
        {
            "schema_id": {"const": "ars://legacy/w9-catalogue-acceptance-envelope"},
            "schema_version": {"const": "1.0.0"},
            "specification_identity": SPEC_IDENTITY,
            "plan_identity": SPEC_IDENTITY,
            "catalogue_identity": CODE_IDENTITY,
            "schema_identities": arr(SCHEMA_FILE_IDENTITY, 1, unique=True),
            "owner_row_multiset_hash": ref("sha256"),
            "bootstrap_contract_identity": CODE_IDENTITY,
            "schema_generator_identity": CODE_IDENTITY,
            "verifier_identity": CODE_IDENTITY,
            "binding_test_identities": arr(CODE_IDENTITY, 1, unique=True),
            "independent_observation_ref": ref("anyRef"),
            "independent_review_ref": ref("reviewRef"),
            "acceptance_decision_ref": ref("decisionRef"),
            "accepted_at": ref("utc"),
            "acceptance_scope": TEXT,
        },
    ),
)

# The genesis input names files by identity, not as records, and names the W11 catalogue it requires (review m-7).
SCHEMAS["import-accepted-w9-catalogue-genesis"] = bootstrap_schema(
    "import-accepted-w9-catalogue-genesis",
    obj(
        [
            "schema_id",
            "schema_version",
            "bootstrap_contract_identity",
            "external_envelope_identity",
            "requested_genesis_transaction_id",
            "required_w11_catalogue",
            "refused_store_identities",
            "verification_requirements",
            "activation_status",
        ],
        {
            "schema_id": {"const": "ars://legacy/import-accepted-w9-catalogue-genesis"},
            "schema_version": {"const": "1.0.0"},
            "bootstrap_contract_identity": CODE_IDENTITY,
            "external_envelope_identity": CODE_IDENTITY,
            "requested_genesis_transaction_id": TEXT,
            "required_w11_catalogue": W11_CATALOGUE_IDENTITY,
            "refused_store_identities": arr(ref("sha256"), 1, unique=True),
            "verification_requirements": arr(TEXT, 1),
            "activation_status": {"const": "not_executed"},
        },
    ),
)

OWNER_ROW = obj(
    [
        "owner_row_id",
        "command_type",
        "record_schema_id",
        "eligible_actor",
        "resolver",
        "preconditions",
        "ordered_events",
        "affected_streams",
        "binding_tests",
    ],
    {
        "owner_row_id": {"type": "string", "pattern": "^LR-[0-9]{3}$"},
        "command_type": {"type": "string", "pattern": "^[A-Z][A-Za-z0-9]+$"},
        "record_schema_id": {"oneOf": [{"type": "null"}, {"type": "string", "pattern": "^ars://legacy/[a-z0-9-]+$"}]},
        "eligible_actor": {
            "enum": ["migration_analyst", "observer", "independent_reviewer", "stephen", "operator", "system_guard"]
        },
        "resolver": {"enum": ["stephen", "none"]},
        "preconditions": arr(TEXT, 1),
        "ordered_events": arr({"type": "string", "pattern": "^E:[a-z0-9-]+$"}, 1),
        "affected_streams": arr(TEXT, 1),
        "binding_tests": arr({"type": "string", "pattern": "^W9-T[0-9]+$"}, 1),
    },
)
_cat_required, _cat_props = header("w9-schema-catalogue-content")
_cat_props.update(
    {
        "owner_spec_identity": SPEC_IDENTITY,
        "owner_plan_identity": SPEC_IDENTITY,
        "owner_row_count": {"type": "integer", "minimum": 1},
        "owner_row_range_hash": ref("sha256"),
        "schema_source_rows": arr(SCHEMA_FILE_IDENTITY, 1, unique=True),
        "owner_contract_rows": arr(OWNER_ROW, 1, unique=True),
    }
)
SCHEMAS["w9-schema-catalogue-content"] = bootstrap_schema(
    "w9-schema-catalogue-content",
    {
        "type": "object",
        "required": _cat_required
        + [
            "owner_spec_identity",
            "owner_plan_identity",
            "owner_row_count",
            "owner_row_range_hash",
            "schema_source_rows",
            "owner_contract_rows",
        ],
        "properties": _cat_props,
        "additionalProperties": False,
    },
)

SCHEMAS["w9-materialization-bootstrap-contract"] = bootstrap_schema(
    "w9-materialization-bootstrap-contract",
    obj(
        [
            "schema_id",
            "schema_version",
            "source_spec",
            "source_plan",
            "materialization_status",
            "runtime_activation",
            "expected_catalogue",
            "acceptance_instance",
            "segmentation_contract",
            "refused_store_identities",
            "required_w11_catalogue",
            "restricted_suffixes",
            "verification_rules",
            "families",
            "forbidden",
        ],
        {
            "schema_id": {"const": "ars://legacy/w9-materialization-bootstrap-contract"},
            "schema_version": {"const": "1.0.0"},
            "source_spec": SPEC_IDENTITY,
            "source_plan": SPEC_IDENTITY,
            "materialization_status": {"const": "inert_foundation_only"},
            "runtime_activation": {"const": "forbidden"},
            "expected_catalogue": {"const": "forbidden_in_stage_a"},
            "acceptance_instance": {"const": "forbidden_in_stage_a"},
            "segmentation_contract": SEGMENTATION,
            "refused_store_identities": arr(ref("sha256"), 1, unique=True),
            "required_w11_catalogue": W11_CATALOGUE_IDENTITY,
            "restricted_suffixes": arr({"type": "string", "pattern": "^\\.[a-z0-9]+$"}, 1, unique=True),
            "verification_rules": arr(TEXT, 1),
            "families": obj(
                ["record", "bootstrap"],
                {"record": arr(TEXT, 1, unique=True), "bootstrap": arr(TEXT, 1, unique=True)},
            ),
            "forbidden": arr(TEXT, 1),
        },
    ),
)


def render(schema: Schema) -> str:
    """Serialize one schema exactly as committed."""
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write (or, with --check, compare) the 17 schema files.

    Args:
        argv: Command-line arguments; defaults to `sys.argv[1:]`.

    Returns:
        0 on success; 1 if `--check` finds a committed schema that differs from the generated one.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare only; write nothing")
    args = parser.parse_args(argv)
    stale = []
    for kind, schema in sorted(SCHEMAS.items()):
        path = OUT_DIR / f"{kind}.schema.json"
        data = render(schema).encode("utf-8")
        if args.check:
            # Bytes, not decoded text, so a CRLF copy is stale too (re-review n-3).
            if not path.exists() or path.read_bytes() != data:
                stale.append(path.relative_to(REPO_ROOT).as_posix())
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for name in stale:
        print(f"stale: {name}", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
