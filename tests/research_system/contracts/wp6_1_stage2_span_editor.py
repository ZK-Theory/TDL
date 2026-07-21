"""Accepted-annex Stage-2 schema overlay with byte-preserving JSON edits.

The Stage-1 schemas are retained as the byte baseline.  This module builds the
accepted fact-annex semantic overlay and applies only child-node edits through
the public test/materialization seam; it never serializes a complete schema.
"""

from __future__ import annotations

import copy
import json
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from tests.research_system.contracts.wp6_1_schema_source import source_rows


FACT_ANNEX_PATH = ".research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml"
PROJECT_PATTERN = "^prj_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"


def _slug(identifier: str) -> str:
    return identifier.split("/", 1)[1]


@dataclass
class _Node:
    kind: str
    start: int
    end: int
    entries: OrderedDict[str, tuple[int, int, "_Node"]] = field(default_factory=OrderedDict)
    items: list["_Node"] = field(default_factory=list)


class _JsonSpans:
    """Minimal JSON lexer retaining exact source spans for child edits."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.decoder = json.JSONDecoder()
        self.root, end = self._value(0)
        if self._skip(end) != len(text):
            raise ValueError("trailing JSON bytes")

    def _skip(self, pos: int) -> int:
        while pos < len(self.text) and self.text[pos] in " \t\r\n":
            pos += 1
        return pos

    def _value(self, pos: int) -> tuple[_Node, int]:
        pos = self._skip(pos)
        start = pos
        char = self.text[pos]
        if char == "{":
            node = _Node("object", start, start + 1)
            pos = self._skip(pos + 1)
            if pos < len(self.text) and self.text[pos] == "}":
                node.end = pos + 1
                return node, node.end
            while True:
                key_start = self._skip(pos)
                key, key_end = self.decoder.raw_decode(self.text, key_start)
                if not isinstance(key, str):
                    raise ValueError("non-string object key")
                colon = self._skip(key_end)
                if self.text[colon] != ":":
                    raise ValueError("missing object colon")
                child, child_end = self._value(colon + 1)
                node.entries[key] = (key_start, child_end, child)
                pos = self._skip(child_end)
                if self.text[pos] == "}":
                    node.end = pos + 1
                    return node, node.end
                if self.text[pos] != ",":
                    raise ValueError("missing object comma")
                pos = self._skip(pos + 1)
        if char == "[":
            node = _Node("array", start, start + 1)
            pos = self._skip(pos + 1)
            if pos < len(self.text) and self.text[pos] == "]":
                node.end = pos + 1
                return node, node.end
            while True:
                child, child_end = self._value(pos)
                node.items.append(child)
                pos = self._skip(child_end)
                if self.text[pos] == "]":
                    node.end = pos + 1
                    return node, node.end
                if self.text[pos] != ",":
                    raise ValueError("missing array comma")
                pos = self._skip(pos + 1)
        value, end = self.decoder.raw_decode(self.text, start)
        del value
        return _Node("scalar", start, end), end


def _indent_at(text: str, offset: int) -> str:
    line_start = text.rfind("\n", 0, offset) + 1
    return text[line_start:offset] if text[line_start:offset].strip() == "" else ""


def _render_fragment(value: Any, indent: str) -> str:
    raw = json.dumps(value, ensure_ascii=False, indent=2, separators=(",", ": "))
    lines = raw.splitlines()
    if len(lines) == 1:
        return indent + lines[0]
    return indent + lines[0] + "\n" + "\n".join(indent + line for line in lines[1:])


def _property_insert(text: str, node: _Node, key: str, value: Any, target_order: list[str]) -> tuple[int, str]:
    indent = _indent_at(text, node.start + 1) + "  "
    # _render_fragment on a one-key object is deliberately used only to obtain
    # a correctly indented value; strip its outer braces and retain key order.
    rendered = json.dumps(value, ensure_ascii=False, indent=2, separators=(",", ": ")).splitlines()
    rendered_text = indent + json.dumps(key, ensure_ascii=False) + ": " + rendered[0]
    if len(rendered) > 1:
        rendered_text += "\n" + "\n".join(indent + line for line in rendered[1:])
    keys = list(node.entries)
    next_key = next((candidate for candidate in target_order if candidate in node.entries), None)
    if next_key is not None:
        return node.entries[next_key][0], rendered_text + ",\n"
    close_indent = _indent_at(text, node.end - 1)
    if keys:
        return node.end - 1, ",\n" + rendered_text + "\n" + close_indent
    return node.end - 1, "\n" + rendered_text + "\n" + close_indent


def _array_insert(text: str, node: _Node, value: Any) -> tuple[int, str]:
    if node.items:
        indent = _indent_at(text, node.items[0].start)
    else:
        indent = _indent_at(text, node.end - 1) + "  "
    rendered = json.dumps(value, ensure_ascii=False, indent=2, separators=(",", ": ")).splitlines()
    fragment = "\n".join(indent + line for line in rendered)
    if node.items:
        return node.end - 1, ",\n" + fragment + "\n" + _indent_at(text, node.end - 1)
    return node.end - 1, "\n" + fragment + "\n" + _indent_at(text, node.end - 1)


def _delete_object_entry(text: str, node: _Node, key: str) -> tuple[int, int]:
    keys = list(node.entries)
    index = keys.index(key)
    start, end, _ = node.entries[key]
    if len(keys) == 1:
        line_start = text.rfind("\n", 0, start) + 1
        cursor = end
        while cursor < len(text) and text[cursor] in " \t":
            cursor += 1
        if cursor < len(text) and text[cursor] == "\r":
            cursor += 1
        if cursor < len(text) and text[cursor] == "\n":
            cursor += 1
        return line_start, cursor
    if index < len(keys) - 1:
        line_start = text.rfind("\n", 0, start) + 1
        cursor = end
        while cursor < len(text) and text[cursor] in " \t":
            cursor += 1
        if cursor < len(text) and text[cursor] == ",":
            cursor += 1
            if cursor < len(text) and text[cursor] == "\r":
                cursor += 1
            if cursor < len(text) and text[cursor] == "\n":
                cursor += 1
            return line_start, cursor
    if index:
        cursor = start - 1
        while cursor > node.start and text[cursor] in " \t\r\n":
            cursor -= 1
        if cursor >= node.start and text[cursor] == ",":
            return cursor, end
    return start, end


def _delete_array_item(text: str, node: _Node, index: int) -> tuple[int, int]:
    item = node.items[index]
    if len(node.items) == 1:
        line_start = text.rfind("\n", 0, item.start) + 1
        cursor = item.end
        while cursor < len(text) and text[cursor] in " \t":
            cursor += 1
        if cursor < len(text) and text[cursor] == "\r":
            cursor += 1
        if cursor < len(text) and text[cursor] == "\n":
            cursor += 1
        return line_start, cursor
    if index < len(node.items) - 1:
        line_start = text.rfind("\n", 0, item.start) + 1
        cursor = item.end
        while cursor < len(text) and text[cursor] in " \t":
            cursor += 1
        if cursor < len(text) and text[cursor] == ",":
            cursor += 1
            if cursor < len(text) and text[cursor] == "\r":
                cursor += 1
            if cursor < len(text) and text[cursor] == "\n":
                cursor += 1
            return line_start, cursor
    if index:
        cursor = item.start - 1
        while cursor > node.start and text[cursor] in " \t\r\n":
            cursor -= 1
        if cursor >= node.start and text[cursor] == ",":
            return cursor, item.end
    return item.start, item.end


def _rebuild_object(text: str, node: _Node, before: Mapping[str, Any], after: Mapping[str, Any]) -> str:
    """Recompose one changed object while retaining raw unchanged child spans."""
    close_indent = _indent_at(text, node.end - 1)
    entry_indent = close_indent + "  "
    ordered_keys = [key for key in node.entries if key in after]
    ordered_keys.extend(key for key in after if key not in node.entries)
    entries: list[str] = []
    for key in ordered_keys:
        if key in node.entries:
            key_start, _, child = node.entries[key]
            line_start = text.rfind("\n", 0, key_start) + 1
            leading = text[line_start:key_start]
            prefix = text[key_start : child.start]
            if before.get(key) == after[key]:
                value_text = text[child.start : child.end]
            else:
                value_text = _apply_spans(text[child.start : child.end], before[key], after[key])
            entries.append(leading + prefix + value_text)
            continue
        raw = json.dumps(after[key], ensure_ascii=False, indent=2, separators=(",", ": ")).splitlines()
        fragment = entry_indent + json.dumps(key, ensure_ascii=False) + ": " + raw[0]
        if len(raw) > 1:
            fragment += "\n" + "\n".join(entry_indent + line for line in raw[1:])
        entries.append(fragment)
    if not entries:
        return "{}"
    return "{\n" + ",\n".join(entries) + "\n" + close_indent + "}"


def _apply_spans(text: str, old: Any, new: Any) -> str:
    spans = _JsonSpans(text)
    edits: list[tuple[int, int, str]] = []

    def scalar(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    def visit(node: _Node, before: Any, after: Any) -> None:
        if before == after:
            return
        if (
            node.kind == "scalar"
            or (isinstance(before, dict) != isinstance(after, dict))
            or (isinstance(before, list) != isinstance(after, list))
        ):
            edits.append((node.start, node.end, scalar(after)))
            return
        if isinstance(before, dict):
            before_keys = list(before)
            after_keys = list(after)
            for key in before_keys:
                if key not in after:
                    start, end = _delete_object_entry(text, node, key)
                    edits.append((start, end, ""))
            for key in before_keys:
                if key in after and key in node.entries:
                    visit(node.entries[key][2], before[key], after[key])
            additions = [key for key in after_keys if key not in before]
            if additions:
                indent = _indent_at(text, node.end - 1) + "  "
                surviving_existing = [key for key in node.entries if key in after]
                rendered_entries: list[str] = []
                for key in additions:
                    raw = json.dumps(after[key], ensure_ascii=False, indent=2, separators=(",", ": ")).splitlines()
                    fragment = indent + json.dumps(key, ensure_ascii=False) + ": " + raw[0]
                    if len(raw) > 1:
                        fragment += "\n" + "\n".join(indent + line for line in raw[1:])
                    rendered_entries.append(fragment)
                if surviving_existing:
                    last_key = surviving_existing[-1]
                    last_value_end = node.entries[last_key][1]
                    last_surviving_index = list(node.entries).index(last_key)
                    cursor = last_value_end
                    while cursor < node.end - 1 and text[cursor] in " \t\r\n":
                        cursor += 1
                    # Deleting a single trailing entry removes the separator
                    # after the last survivor; deleting a run of two or more
                    # leaves the survivor's original comma in place.
                    deleted_after = len(node.entries) - 1 - last_surviving_index
                    if deleted_after == 1 or (deleted_after == 0 and (cursor >= node.end - 1 or text[cursor] != ",")):
                        edits.append((last_value_end, last_value_end, ","))
                close_line_start = text.rfind("\n", 0, node.end - 1) + 1
                insertion = ",\n".join(rendered_entries) + "\n"
                edits.append((close_line_start, close_line_start, insertion))
            elif any(key not in after for key in before_keys):
                # When the final surviving entry originally preceded deleted
                # entries, its separator may remain in the source.  Remove
                # only that comma; retain the original whitespace/indent.
                surviving = [key for key in node.entries if key in after]
                if surviving:
                    last_key = surviving[-1]
                    cursor = node.entries[last_key][1]
                    while cursor < node.end - 1 and text[cursor] in " \t\r\n":
                        cursor += 1
                    if cursor < node.end - 1 and text[cursor] == ",":
                        edits.append((cursor, cursor + 1, ""))
            return
        if isinstance(before, list):
            if len(before) != len(after) and all(not isinstance(item, (dict, list)) for item in before + after):
                raw = json.dumps(after, ensure_ascii=False, indent=2, separators=(",", ": ")).splitlines()
                # The opening bracket shares the property line; item/closing
                # line indentation is the stable formatting anchor.
                item_indent = (
                    _indent_at(text, node.items[0].start) if node.items else _indent_at(text, node.end - 1) + "  "
                )
                close_indent = _indent_at(text, node.end - 1)
                replacement = raw[0]
                if len(raw) > 1:
                    inner = [item_indent + line.lstrip() for line in raw[1:-1]]
                    replacement += "\n" + "\n".join(inner) + "\n" + close_indent + raw[-1]
                edits.append((node.start, node.end, replacement))
                return
            common = min(len(before), len(after), len(node.items))
            for index in range(common):
                visit(node.items[index], before[index], after[index])
            for index in range(len(before) - 1, len(after) - 1, -1):
                if index < len(node.items):
                    start, end = _delete_array_item(text, node, index)
                    edits.append((start, end, ""))
            additions = after[len(before) :]
            if additions:
                indent = _indent_at(text, node.end - 1) + "  "
                surviving_existing = min(len(node.items), len(after))
                rendered_items: list[str] = []
                for value in additions:
                    raw = json.dumps(value, ensure_ascii=False, indent=2, separators=(",", ": ")).splitlines()
                    fragment = "\n".join(indent + line for line in raw)
                    rendered_items.append(fragment)
                if node.items:
                    last_item_end = node.items[min(len(node.items), len(after)) - 1].end
                    cursor = last_item_end
                    while cursor < node.end - 1 and text[cursor] in " \t\r\n":
                        cursor += 1
                    if cursor >= node.end - 1 or text[cursor] != ",":
                        edits.append((last_item_end, last_item_end, ","))
                close_line_start = text.rfind("\n", 0, node.end - 1) + 1
                insertion = ",\n".join(rendered_items) + "\n"
                edits.append((close_line_start, close_line_start, insertion))
            return
        edits.append((node.start, node.end, scalar(after)))

    visit(spans.root, old, new)
    deletion_spans = sorted((start, end) for start, end, replacement in edits if replacement == "" and end > start)
    merged_deletions: list[tuple[int, int, str]] = []
    for start, end in deletion_spans:
        if merged_deletions and start <= merged_deletions[-1][1]:
            previous_start, previous_end, _ = merged_deletions[-1]
            merged_deletions[-1] = (previous_start, max(previous_end, end), "")
        else:
            merged_deletions.append((start, end, ""))
    edits = [item for item in edits if not (item[2] == "" and item[1] > item[0])] + merged_deletions
    edits.sort(key=lambda item: (item[0], item[1]), reverse=True)
    last_start = len(text) + 1
    for start, end, replacement in edits:
        if end > last_start:
            raise ValueError(f"overlapping localized JSON edits ({start},{end}) after {last_start}; edits={edits}")
        text = text[:start] + replacement + text[end:]
        last_start = start
    return text


def _index(proposal: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    types = {item["type_id"]: item for item in proposal["primitive_types"]}
    enums = {item["enum_id"]: item for item in proposal["source_closed_enums"]}
    objects = {item["object_id"]: item for item in proposal["reusable_objects"]}
    families = {
        family["family_id"]: {field["field_name"]: field for field in family["fields"]}
        for family in proposal["family_specs"]
    }
    return types, enums, objects, families


def _type_schema(
    type_ref: str, nullable: bool, proposal: Mapping[str, Any], indexes: tuple[dict[str, Any], ...]
) -> dict[str, Any]:
    types, enums, objects, _ = indexes
    if type_ref in enums:
        result: dict[str, Any] = {"type": "string", "enum": list(enums[type_ref]["values"])}
    elif type_ref in objects:
        result = {"$ref": f"#/$defs/{_slug(type_ref)}"}
    else:
        spec = types[type_ref]
        json_type = spec["json_type"]
        result = {"type": json_type}
        if "min_length" in spec:
            result["minLength"] = spec["min_length"]
        if "pattern" in spec:
            result["pattern"] = spec["pattern"]
        if "format" in spec:
            result["format"] = spec["format"]
        if "minimum" in spec:
            result["minimum"] = spec["minimum"]
        if "maximum" in spec:
            result["maximum"] = spec["maximum"]
        if json_type == "array":
            result["items"] = _type_schema(spec["item_type_ref"], False, proposal, indexes)
            result["uniqueItems"] = True
            if "min_items" in spec:
                result["minItems"] = spec["min_items"]
            if "max_items" in spec:
                result["maxItems"] = spec["max_items"]
    if nullable:
        if "$ref" in result:
            return {"anyOf": [result, {"type": "null"}]}
        result["type"] = [result["type"], "null"]
    return result


def _field_schema(
    field_spec: Mapping[str, Any],
    proposal: Mapping[str, Any],
    indexes: tuple[dict[str, Any], ...],
    *,
    const: Any = None,
) -> dict[str, Any]:
    result = _type_schema(field_spec["type_ref"], bool(field_spec.get("nullable")), proposal, indexes)
    result["x-source-citation"] = field_spec.get("source_citation", "accepted WP6.1 fact annex")
    if const is not None:
        result["const"] = const
    return result


def _overlay_value(existing: Any, desired: Any) -> Any:
    if isinstance(existing, dict) and isinstance(desired, dict):
        result = copy.deepcopy(existing)
        for key in list(result):
            if key not in desired and key not in {"x-source-citation"}:
                del result[key]
        for key, value in desired.items():
            if key == "x-source-citation" and key in result:
                continue
            if key in result:
                result[key] = _overlay_value(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result
    return copy.deepcopy(desired)


def _overlay_object(existing: Mapping[str, Any] | None, desired: Mapping[str, Any]) -> dict[str, Any]:
    if existing is None:
        return copy.deepcopy(dict(desired))
    result = copy.deepcopy(dict(existing))
    desired_props = desired.get("properties", {})
    existing_props = result.get("properties", {})
    props: OrderedDict[str, Any] = OrderedDict()
    for name, value in existing_props.items():
        if name in desired_props:
            props[name] = _overlay_value(value, desired_props[name])
    for name, value in desired_props.items():
        if name not in props:
            props[name] = copy.deepcopy(value)
    result["properties"] = props
    result["required"] = [name for name in result.get("required", []) if name in desired.get("required", [])]
    result["required"].extend(name for name in desired.get("required", []) if name not in result["required"])
    for key in ("type", "additionalProperties", "oneOf"):
        if key in desired:
            result[key] = copy.deepcopy(desired[key])
        elif key in result and key not in {"type", "additionalProperties"}:
            del result[key]
    if "x-source-citation" not in result and "x-source-citation" in desired:
        result["x-source-citation"] = desired["x-source-citation"]
    return result


def _object_definition(
    object_id: str, proposal: Mapping[str, Any], indexes: tuple[dict[str, Any], ...], cache: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    if object_id in cache:
        return cache[object_id]
    types, enums, objects, _ = indexes
    source = objects[object_id]
    properties: OrderedDict[str, Any] = OrderedDict()
    for field_spec in source["fields"]:
        properties[field_spec["field_name"]] = _field_schema(field_spec, proposal, indexes)
    result: dict[str, Any] = {
        "additionalProperties": False,
        "properties": properties,
        "required": [item["field_name"] for item in source["fields"]],
        "type": "object",
        "x-source-citation": source.get("source_citation", "accepted WP6.1 fact annex"),
    }
    cache[object_id] = result
    for field_spec in source["fields"]:
        ref = field_spec["type_ref"]
        if ref in objects:
            _object_definition(ref, proposal, indexes, cache)
    if object_id == "object/resource_request":
        rule = proposal["object_variant_rules"][0]
        controlled = {branch["discriminator_const"] for branch in rule["branches"]}
        common = [
            item["field_name"]
            for item in source["fields"]
            if item["field_name"]
            not in {"trivial_profile_evidence", "bounded_profile_evidence", "long_running_profile_evidence"}
        ]
        result["required"] = common
        result["oneOf"] = [{"required": [branch["required_fields"][0]]} for branch in rule["branches"]]
        del controlled
    return result


def _family_field(families: Mapping[str, Mapping[str, Any]], family_ref: str, name: str) -> Mapping[str, Any]:
    try:
        return families[family_ref][name]
    except KeyError as exc:
        raise ValueError(f"accepted annex field is not in {family_ref}: {name}") from exc


def _shared_rule(proposal: Mapping[str, Any], kind: str, semantic_type: str) -> Mapping[str, Any] | None:
    return next(
        (
            rule
            for rule in proposal["shared_schema_rules"]
            if rule["schema_kind"] == kind and rule["semantic_type"] == semantic_type
        ),
        None,
    )


def _variant_descriptors(
    specs: list[Mapping[str, Any]],
    kind: str,
    semantic_type: str,
    proposal: Mapping[str, Any],
    indexes: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    _, _, _, families = indexes
    rule = _shared_rule(proposal, kind, semantic_type)
    selected = specs
    if rule and rule["variant_rule"] == "single_normalized_fact":
        selected = specs[:1]
        union: list[str] = []
        for spec in specs:
            for name in spec["required_field_names"]:
                if name not in union:
                    union.append(name)
        selected = [dict(specs[0], required_field_names=union)]
    result: list[dict[str, Any]] = []
    for spec in selected:
        props: OrderedDict[str, Any] = OrderedDict()
        consts: dict[str, Any] = {}
        if rule and rule["variant_rule"] == "one_of_discriminator":
            match = next(
                (item for item in rule["variant_const_values"] if spec["variant_id"] == item["variant_id"]), None
            )
            if match is None:
                candidates = [
                    item
                    for item in rule["variant_const_values"]
                    if spec["variant_id"].startswith(item["variant_id"] + "_")
                ]
                match = max(candidates, key=lambda item: len(item["variant_id"]))
            consts[rule["discriminator_field"]] = match["const_value"]
        for name in spec["required_field_names"]:
            field_spec = _family_field(families, spec["family_ref"], name)
            props[name] = _field_schema(field_spec, proposal, indexes, const=consts.get(name))
        variant: dict[str, Any] = {
            "additionalProperties": False,
            "properties": props,
            "required": list(spec["required_field_names"]),
            "type": "object",
            "x-source-citation": spec.get("source_citation", "accepted WP6.1 fact annex"),
        }
        if {"body", "body_artefact_ref"} <= set(props):
            variant["oneOf"] = [{"required": ["body"]}, {"required": ["body_artefact_ref"]}]
        result.append(variant)
    return result


def _merge_variants(existing: list[dict[str, Any]], desired: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    unused = list(desired)

    def score(old: Mapping[str, Any], new: Mapping[str, Any]) -> tuple[int, int]:
        old_props = old.get("properties", {})
        new_props = new.get("properties", {})
        old_consts = {k: v.get("const") for k, v in old_props.items() if isinstance(v, dict) and "const" in v}
        new_consts = {k: v.get("const") for k, v in new_props.items() if isinstance(v, dict) and "const" in v}
        return (
            len(set(old_props) & set(new_props)) + 10 * len(set(old_consts.items()) & set(new_consts.items())),
            -abs(len(old_props) - len(new_props)),
        )

    for old in existing:
        if not unused:
            break
        chosen = max(unused, key=lambda candidate: score(old, candidate))
        if score(old, chosen)[0] <= 0:
            continue
        result.append(_overlay_object(old, chosen))
        unused.remove(chosen)
    result.extend(copy.deepcopy(item) for item in unused)
    return result


def _schema_overlay(
    schema: dict[str, Any],
    kind: str,
    semantic_type: str,
    specs: list[Mapping[str, Any]],
    proposal: Mapping[str, Any],
    indexes: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    result = copy.deepcopy(schema)
    types, enums, objects, families = indexes
    root_specs = proposal["command_root"] if kind == "command" else proposal["event_root"]
    root_fields = {item["field_name"]: item for item in root_specs["fields"]}
    properties = result.get("properties", {})
    desired_properties: OrderedDict[str, Any] = OrderedDict()
    identity_fields = {"payload", "command_type", "event_type", "schema_id", "schema_version"}
    for name, old_value in properties.items():
        if name in root_fields and name not in identity_fields:
            desired_properties[name] = _overlay_value(old_value, _field_schema(root_fields[name], proposal, indexes))
        else:
            desired_properties[name] = old_value
    for name, field_spec in root_fields.items():
        if name not in desired_properties:
            if name in identity_fields:
                continue
            desired_properties[name] = _field_schema(field_spec, proposal, indexes)
    result["properties"] = desired_properties
    old_required = list(result.get("required", []))
    required = [name for name in old_required if name in root_fields or name == "payload"]
    required.extend(name for name in root_fields if name not in required)
    result["required"] = required
    target_variants = _variant_descriptors(specs, kind, semantic_type, proposal, indexes)
    payload = result.setdefault("$defs", {}).setdefault("payload", {"oneOf": []})
    payload["oneOf"] = _merge_variants(payload.get("oneOf", []), target_variants)
    defs = result["$defs"]
    cache: dict[str, dict[str, Any]] = {}
    new_defs: OrderedDict[str, dict[str, Any]] = OrderedDict()
    needed: list[str] = []
    queued: set[str] = set()

    def queue_definition(name: str) -> None:
        if name not in queued:
            queued.add(name)
            needed.append(name)

    for variant in target_variants:
        for field_schema in variant.get("properties", {}).values():
            ref = field_schema.get("$ref") if isinstance(field_schema, dict) else None
            if ref and ref.startswith("#/$defs/"):
                queue_definition(ref.removeprefix("#/$defs/"))
    while needed:
        name = needed.pop(0)
        object_id = f"object/{name}"
        if object_id not in objects:
            continue
        desired = _object_definition(object_id, proposal, indexes, cache)
        merged = _overlay_object(defs.get(name) or new_defs.get(name), desired)
        if name in defs:
            defs[name] = merged
        else:
            new_defs[name] = merged
        for field_spec in objects[object_id]["fields"]:
            ref = field_spec["type_ref"]
            if ref.startswith("object/"):
                queue_definition(_slug(ref))
            if ref.startswith("type/") and ref in types and types[ref].get("item_type_ref", "").startswith("object/"):
                queue_definition(_slug(types[ref]["item_type_ref"]))
    defs.update(new_defs)
    return result


def build_stage2_overlays(repo_root: Path, *, baseline_bytes: Mapping[str, bytes] | None = None) -> dict[str, bytes]:
    proposal = yaml.safe_load((repo_root / FACT_ANNEX_PATH).read_bytes())
    indexes = _index(proposal)
    rows = source_rows(repo_root)
    command_specs = {item["row_key"]: item for item in proposal["command_payload_specs"]}
    event_specs: dict[tuple[str, int], Mapping[str, Any]] = {
        (item["row_key"], item["event_ordinal"]): item for item in proposal["event_fact_specs"]
    }
    command_groups: dict[str, list[Mapping[str, Any]]] = {}
    event_groups: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        command_path = f".research-system/schemas/core/commands/{row.command_token.split('/', 1)[1]}.schema.json"
        command_groups.setdefault(command_path, []).append(command_specs[row.key])
        for ordinal, (event_type, event_token) in enumerate(row.events, start=1):
            event_path = f".research-system/schemas/core/events/{event_token.split('/', 1)[1]}.schema.json"
            event_groups.setdefault(event_path, []).append(event_specs[(row.key, ordinal)])
    outputs: dict[str, bytes] = {}
    for kind, groups in (("command", command_groups), ("event", event_groups)):
        for relative, specs in groups.items():
            path = repo_root / relative
            baseline = (
                baseline_bytes[relative].decode("utf-8")
                if baseline_bytes is not None
                else path.read_text(encoding="utf-8")
            )
            schema = json.loads(baseline)
            semantic_type = schema["$id"].rsplit("/", 1)[1]
            try:
                target = _schema_overlay(schema, kind, semantic_type, specs, proposal, indexes)
            except (KeyError, StopIteration, ValueError) as exc:
                raise ValueError(f"{relative}: {exc}") from exc
            try:
                outputs[relative] = _apply_spans(baseline, schema, target).encode("utf-8")
            except ValueError as exc:
                raise ValueError(f"{relative}: {exc}") from exc
    return outputs


def apply_stage2_schema_overlays(repo_root: Path, *, write: bool = False) -> list[str]:
    outputs = build_stage2_overlays(repo_root)
    mismatches: list[str] = []
    for relative, expected in outputs.items():
        path = repo_root / relative
        if path.read_bytes() != expected:
            mismatches.append(relative)
            if write:
                path.write_bytes(expected)
    return mismatches
