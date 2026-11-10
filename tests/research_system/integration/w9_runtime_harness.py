# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1; P-080, P-081)
# Purpose: drive LR-003 to LR-015 through the real LegacyRuntime.submit on scratch stores and scratch Git repositories.
"""A ``submit``-level harness for WP9.3-1 (WP9.3 note §5, §6, §7, §17).

Every store is a scratch store under ``tmp_path`` holding W11 genesis and a real W9 genesis. Sources live in a scratch
Git repository under ``tmp_path``, never the live repository or vault (§17, "Fixtures"). The repository also carries the
two evidence files WP9.3-1 reads (§11.1) and stand-in copies of the importer's modules (§7.5), so the importer identity
is read at the scratch ``git_head``. Every actor but the owner is a non-owner holding its own exact-subject grant (§5.3;
the owner short-circuits actor classification).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from research_system.canonical import sha256_hex
from research_system.ids import new_id
from research_system.legacy import evidence
from research_system.legacy.reader import IMPORTER_MODULES, LegacyReader, handle_bound_read
from research_system.legacy.records import pre_assigned_ref
from research_system.legacy.runtime import LegacyRuntime
from tests.research_system.factories import ACTORS, activate_lifecycle_grant
from tests.research_system.integration import w9_flows as flows
from tests.research_system.integration.test_artefact_authority_commands import artefact_manifest, command
from tests.research_system.integration.test_w9_legacy_runtime import REPO_ROOT, _genesis_command, _store

OWNER = ACTORS["actor-a"]
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "w9"
# The committed fixture copies (WP9.3 note §17), placed in the scratch repository at these paths.
FIXTURE_PATHS = {
    "usoc_headline_frozen_2026-05-28.json": "fixtures/usoc_headline_frozen_2026-05-28.json",
    "superseded_lines_69_71.md": "fixtures/SUPERSEDED.md",
}
T0 = datetime(2026, 9, 1, tzinfo=UTC)
TRACKER = b"## Task Tracking\n| Task | S |\n|---|---|\n| 1.1 | a |\n| 1.2 | b |\n"
# A heading_section source for the builder (WP9.3-1b): three level-2 sections after a title, at lines 3, 6 and 9.
SECTIONS = b"# Title\n\n## a\nlegacy text a\n\n## b\nlegacy text b\n\n## c\nlegacy text c\n"
RESULT = b'{"headline": 1.0, "other": [1, 2]}\n'
RESULT_FAMILIES = [
    {"name": "meta", "definition_source": "w9 test fixture", "pointers": ["", "/other"]},
    {"name": "headline", "definition_source": "w9 test fixture", "pointers": ["/headline"]},
    {"name": "other", "definition_source": "w9 test fixture", "pointers": ["/other/[*]"]},
]


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=w9@test", "-c", "user.name=w9", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class Clock:
    """A settable runtime clock, so a test can move time (lapse) or keep it."""

    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


@dataclass
class W9Store:
    """One scratch store, its runtime, and the scratch source repository."""

    runtime: LegacyRuntime
    harness: Any
    repo: Path
    head: str
    clock: Clock
    pin: dict[str, Any]
    actors: flows.Actors
    grants: dict[tuple[str, str, str], str] = field(default_factory=dict)
    log: list[tuple[dict[str, Any], Any]] = field(default_factory=list)

    # --- Envelopes ---------------------------------------------------------------------------------------------------

    def grant(self, command_type: str, subject_kind: str, subject_id: str, actor: str) -> str:
        key = (command_type, subject_id, actor)
        if key not in self.grants:
            raw = bytearray(hashlib.sha256(f"w9-3:{command_type}:{subject_id}:{actor}".encode()).digest()[:16])
            raw[6] = (raw[6] & 0x0F) | 0x70
            raw[8] = (raw[8] & 0x3F) | 0x80
            self.grants[key] = activate_lifecycle_grant(
                self.harness,
                subject_kind=subject_kind,
                subject_id=subject_id,
                actor_id=actor,
                allowed_actor_classes=("human",) if actor == OWNER else ("agent",),
                command_types=(command_type,),
                grant_id=f"agr_{uuid.UUID(bytes=bytes(raw))}",
            )
        return self.grants[key]

    def envelope(
        self, command_type: str, actor: str, target: str, version: int, payload: dict[str, Any], **overrides: Any
    ) -> dict[str, Any]:
        kind = {"Review": "review", "Decision": "decision"}
        subject_kind = next((value for key, value in kind.items() if key in command_type), "scope_definition")
        envelope = {
            "command_id": new_id("command"),
            "command_type": command_type,
            "actor_id": actor,
            "authority_grant_id": self.grant(command_type, subject_kind, target, actor),
            "idempotency_key": f"wp9.3:{command_type}:{target}:{new_id('command')}",
            "target_stream_id": target,
            "expected_stream_version": version,
            "payload": payload,
        }
        envelope.update(overrides)
        return envelope

    def submit(self, command_type: str, actor: str, target: str, version: int, payload: dict[str, Any], **kw: Any):
        envelope = self.envelope(command_type, actor, target, version, payload, **kw)
        receipt = self.runtime.submit(envelope)
        self.log.append((envelope, receipt))
        return receipt

    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.harness.ledger.iter_events())

    # --- Records -----------------------------------------------------------------------------------------------------

    def registration_payload(
        self, path: str, *, role: str = "legacy_research_result", kind: str = "git_tracked", root: Path | None = None
    ) -> dict[str, Any]:
        _, physical, _ = handle_bound_read(root or self.repo, path)
        record = {
            "schema_id": "ars://legacy/legacy-path-registration",
            "schema_version": "1.0.0",
            "record_id": new_id("scope_definition"),
            "record_revision": 1,
            "supersedes_revision": None,
            "project_id": self.harness.ledger.project_id,
            "root_kind": "vault_root" if kind == "vault_file" else "repository_root",
            "root_id": "vault" if kind == "vault_file" else "repository",
            "normalized_path": path,
            "physical_identity": physical,
            "source_identity_kind": kind,
            "role": role,
            "ownership_mode": "legacy_owned",
            "writer_classes": ["owner_ruling"],
            "prohibited_consumers": [],
        }
        record["registration_decision_ref"] = pre_assigned_ref("decision", new_id("decision"), record["record_id"])
        return record

    def register(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """LR-003 → LR-004 → LR-005 through ``submit``. Returns the recorded registration."""
        payload = self.registration_payload(path, **kwargs)
        record_id = payload["record_id"]
        assert self.submit("ProposeLegacyRecord", self.actors.analyst, record_id, 0, payload).status == "accepted"
        decision_id = payload["registration_decision_ref"]["id"]
        decide = {
            "subject_record_id": record_id,
            "question": "Register the path?",
            "recommendation": "accept",
            "consequences": ["registered"],
        }
        assert (
            self.submit("ProposeW9AuthorityDecision", self.actors.analyst, decision_id, 0, decide).status == "accepted"
        )
        resolve = {"decision_id": decision_id, "selected_option": "accept"}
        assert self.submit("ResolveW9AuthorityDecision", OWNER, decision_id, 1, resolve).status == "accepted"
        return self.recorded("legacy_path_registration", record_id)

    def recorded(self, kind: str, record_id: str) -> dict[str, Any]:
        from research_system.legacy.replay.driver import replay_legacy

        state = replay_legacy(self.events(), schemas=self.harness.schemas, pinned_signatures=(self.pin,))
        return state["records"][kind][record_id]

    def review(self, row_subject: dict[str, Any], review_id: str, reviewer: str, *, author_session: bool) -> None:
        request = {
            "subject_record_id": row_subject["record_id"],
            "reviewer_actor_id": reviewer,
            "review_questions": ["Is it right?"],
            "analyst_session": "session-analyst",
        }
        if author_session:
            request["author_session"] = "session-author"
        assert self.submit("RequestW9AuthorityReview", self.actors.analyst, review_id, 0, request).status == "accepted"
        verdict = {
            "review_id": review_id,
            "verdict": "approve",
            "findings": [],
            "limitations": [],
            "reviewer_session": "session-reviewer",
            "reviewer_model_metadata": "w9-test-model",
            "context_manifest_sha256": "9" * 64,
        }
        assert self.submit("RecordW9AuthorityReview", reviewer, review_id, 1, verdict).status == "accepted"

    def membership(self, path: str = "results/x.json", families: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """LR-006 to LR-010 through ``submit``. Returns the recorded table."""
        raw = (self.repo / path).read_bytes()
        record = {
            "schema_id": "ars://legacy/legacy-field-family-membership",
            "schema_version": "1.0.0",
            "record_id": new_id("scope_definition"),
            "record_revision": 1,
            "supersedes_revision": None,
            "project_id": self.harness.ledger.project_id,
            "file_schema_id": "w9-test-result/1",
            "applies_to": [
                {
                    "path": path,
                    "identity_kind": "git_tracked",
                    "git_blob": git(self.repo, "rev-parse", f"{self.head}:{path}"),
                    "sha256": sha256_hex(raw),
                    "size_bytes": len(raw),
                }
            ],
            "table_sha256": "c" * 64,
            "families": deepcopy(families or RESULT_FAMILIES),
            "unassigned": [],
            "author_actor_id": self.actors.author,
        }
        record["review_ref"] = pre_assigned_ref("review", new_id("review"), record["record_id"])
        record["acceptance_decision_ref"] = pre_assigned_ref("decision", new_id("decision"), record["record_id"])
        record_id = record["record_id"]
        assert self.submit("ProposeLegacyRecord", self.actors.author, record_id, 0, record).status == "accepted"
        self.review(record, record["review_ref"]["id"], self.actors.reviewer, author_session=True)
        decision_id = record["acceptance_decision_ref"]["id"]
        decide = {"subject_record_id": record_id, "question": "Accept?", "recommendation": "accept", "consequences": []}
        assert (
            self.submit("ProposeW9AuthorityDecision", self.actors.analyst, decision_id, 0, decide).status == "accepted"
        )
        resolve = {"decision_id": decision_id, "selected_option": "accept"}
        assert self.submit("ResolveW9AuthorityDecision", OWNER, decision_id, 1, resolve).status == "accepted"
        return self.recorded("legacy_field_family_membership", record_id)

    def inventory_payload(self, registration: dict[str, Any], raw: bytes) -> dict[str, Any]:
        from research_system.legacy.preparers import inventory_rows
        from research_system.legacy.segmentation import segment

        segmented = segment(raw, "tracker_task_row")
        read = self.runtime.reader.read(registration)
        record = {
            "schema_id": "ars://legacy/legacy-light-inventory",
            "schema_version": "1.0.0",
            "record_id": new_id("scope_definition"),
            "record_revision": 1,
            "supersedes_revision": None,
            "project_id": self.harness.ledger.project_id,
            "registration_ref": flows.record_ref(registration),
            "source_identity": read.source_identity,
            "segmentation_contract": "w9-segmentation/1.0.0",
            "selector_kind": "tracker_task_row",
            "heading_level": None,
            "covered_region": {"form": "fixed_by_selector"},
            "structural_ranges": [],
            "suppressed_anchors": segmented["suppressed_anchors"],
            "file_facts": segmented["file_facts"],
            "read_started_at": read.read_started_at,
            "read_ended_at": read.read_ended_at,
            "path_form": read.path_form,
            "observer_actor_id": self.actors.observer,
            "rows": inventory_rows(segmented, "tracker_task_row"),
        }
        record["independent_reproduction_ref"] = pre_assigned_ref("review", new_id("review"), record["record_id"])
        return record

    def inventory(self, registration: dict[str, Any]) -> dict[str, Any]:
        """LR-011 to LR-014 through ``submit``. Returns the recorded inventory."""
        record = self.inventory_payload(registration, (self.repo / registration["normalized_path"]).read_bytes())
        record_id = record["record_id"]
        assert self.submit("ProposeLegacyRecord", self.actors.observer, record_id, 0, record).status == "accepted"
        self.review(record, record["independent_reproduction_ref"]["id"], self.actors.reproducer, author_session=False)
        receipt = self.submit(
            "RecordLegacyLightInventory", self.actors.observer, record_id, 1, {"record_id": record_id}
        )
        assert receipt.status == "accepted"
        return self.recorded("legacy_light_inventory", record_id)

    def observation_payload(
        self, registration: dict[str, Any], *, selector: dict[str, Any] | None = None, family: str = "whole_file"
    ) -> dict[str, Any]:
        selector = selector or {"selector_kind": "whole_file"}
        return {
            "schema_id": "ars://legacy/legacy-observation",
            "schema_version": "1.0.0",
            "record_revision": 1,
            "supersedes_revision": None,
            "project_id": self.harness.ledger.project_id,
            "registration_ref": flows.record_ref(registration),
            "selector": selector,
            "segmentation_contract": "w9-segmentation/1.0.0" if selector["selector_kind"] == "inventory_item" else None,
            "observer_actor_id": self.actors.observer,
            "families": [flows.signed_family(family, self.pin)],
            "qualifiers": [],
            "conflicts": [],
        }

    def observation_id(self, payload: dict[str, Any], actor: str | None = None) -> str:
        from research_system.legacy.preparers import Environment, observation_id
        from research_system.legacy.replay.driver import replay_legacy

        state = replay_legacy(self.events(), schemas=self.harness.schemas, pinned_signatures=(self.pin,))
        environment = Environment(self.runtime.reader, {}, self.harness.ledger.control_root, None)
        return observation_id(payload, actor=actor or self.actors.observer, legacy=state, environment=environment)

    def observe(self, payload: dict[str, Any], actor: str | None = None) -> tuple[Any, str]:
        observation_id = self.observation_id(payload, actor)
        return self.submit(
            "ObserveLegacyRecord", actor or self.actors.observer, observation_id, 0, payload
        ), observation_id

    def frozen_copy(self, raw: bytes, name: str) -> dict[str, Any]:
        """Register a frozen copy through the generic ``RegisterArtefact`` path, ``root_id: control`` (§7.3)."""
        control = self.harness.ledger.control_root
        relative = f"evidence/w9-frozen/{name}"
        (control / relative).parent.mkdir(parents=True, exist_ok=True)
        (control / relative).write_bytes(raw)
        artefact_id = new_id("artefact")
        grant = activate_lifecycle_grant(
            self.harness,
            subject_kind="artefact",
            subject_id=artefact_id,
            command_types=("RegisterArtefact",),
            grant_id=f"agr_{uuid.UUID(bytes=bytes(_uuid7_bytes(artefact_id)))}",
        )
        manifest = artefact_manifest()
        manifest.update(
            artefact_id=artefact_id,
            relative_path=relative,
            size_bytes=len(raw),
            content_sha256=sha256_hex(raw),
            media_type="text/markdown",
        )
        register = command(
            command_id=new_id("command"),
            command_type="RegisterArtefact",
            actor_id=OWNER,
            authority_grant_id=grant,
            expected_stream_version=0,
            payload={"new_artefact_id": artefact_id, "manifest": manifest},
            target_stream_id=artefact_id,
        )
        receipt = self.harness.service.submit(register)
        assert receipt.status == "accepted", receipt
        return {"id": artefact_id, "record_revision": 1, "content_hash": sha256_hex(raw)}


def _uuid7_bytes(seed: str) -> bytearray:
    raw = bytearray(hashlib.sha256(seed.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    return raw


def scratch_repository(tmp_path: Path) -> tuple[Path, str]:
    """A scratch Git repository with a tracked result, a tracker, the evidence files and the importer modules."""
    repo = tmp_path / "source"
    (repo / "results").mkdir(parents=True)
    (repo / "results" / "x.json").write_bytes(RESULT)
    (repo / "tracker.md").write_bytes(TRACKER)
    (repo / "sections.md").write_bytes(SECTIONS)
    for name, path in FIXTURE_PATHS.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_bytes((FIXTURES / name).read_bytes())
    for module in IMPORTER_MODULES:
        (repo / module).parent.mkdir(parents=True, exist_ok=True)
        (repo / module).write_bytes(f"# stand-in for {module}\n".encode())
    controls = {
        "format": evidence.DETECTOR_CONTROLS_FORMAT,
        "detectors": [
            {"detector": name, "control": kind, "output_sha256": "d" * 64, "recorded_at": "2026-08-31T00:00:00Z"}
            for name, kind in evidence.REQUIRED_DETECTOR_CONTROLS.items()
        ],
    }
    manifest = {
        "format": evidence.REGISTRATION_MANIFEST_FORMAT,
        "registrations": [
            {"root_kind": "repository_root", "root_id": "repository", "normalized_path": path}
            for path in (
                *FIXTURE_PATHS.values(),
                "results/x.json",
                "tracker.md",
                "sections.md",
                "notes/untracked.md",
                "data/rows.pkl",
            )
        ],
    }
    (repo / evidence.DETECTOR_CONTROLS).parent.mkdir(parents=True)
    (repo / evidence.DETECTOR_CONTROLS).write_text(json.dumps(controls), encoding="utf-8")
    (repo / evidence.REGISTRATION_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    (repo / ".gitignore").write_text("notes/\ndata/\n", encoding="utf-8")
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "w9 scratch source")
    return repo, git(repo, "rev-parse", "HEAD")


def w9_store(tmp_path: Path, monkeypatch: Any, **runtime_kwargs: Any) -> W9Store:
    """A scratch store with W11 and W9 genesis, and a runtime whose reader is bound to a scratch repository.

    The test W0 signature is pinned in the code constant for the test's duration, as a reviewed PR would pin a real
    one (§9.1), because the public shared replay the runtime runs before each command reads the code's pins.
    """
    import research_system.legacy.accepted_w9 as accepted_w9

    repo, head = scratch_repository(tmp_path)
    clock = Clock()
    pin = flows.signature()
    monkeypatch.setattr(accepted_w9, "ACCEPTED_W0_SIGNATURES", (pin,))
    reader = LegacyReader(repository_root=repo, git_head=head, clock=clock)
    runtime, harness = _store(tmp_path)
    runtime.submit(_genesis_command(harness))
    runtime = LegacyRuntime(
        runtime.control_root,
        harness.ledger,
        harness.schemas,
        repository_root=REPO_ROOT,
        authority_resolver=harness.authority_resolver,
        clock=clock,
        reader=reader,
        **runtime_kwargs,
    )
    return W9Store(runtime, harness, repo, head, clock, pin, flows.Actors(owner=OWNER))
