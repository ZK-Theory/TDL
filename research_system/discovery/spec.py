"""Thin public SPEC coordinator. Later phases extend this same action table."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from collections.abc import Callable
from contextlib import contextmanager
from research_system.store.binding_service import VerifiedBindingContext

from research_system.authority import LedgerAuthorityGrantResolver
from research_system.artefacts.runtime import GoverningScientificReviewStore
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.service import CommandService
from research_system.discovery.replay.driver import replay_discovery
from research_system.discovery.runtime import DiscoveryRuntime
from research_system.discovery.spec_source import (
    document_manifest,
    prepare_document,
    read_document,
    registration_ref,
    source_ids,
    source_ref,
    validate_source_refs,
)
from research_system.discovery import spec_task
from research_system.discovery.spec_source_git import parse_locator
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.methods.registration import _stable_command_id
from research_system.schema_registry import runtime_schema_registry
from research_system.config import SpecOperatorConfig
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore

ACTION_EFFECTS = {
    "observe_source": ("RegisterArtefact", "IngestScoutObservationBatch"),
    "correct_spec_01_source": ("RegisterArtefact", "RecordScientificReview", "SetArtefactUseAuthority"),
    spec_task.ACTION: spec_task.EFFECTS,
}


class _SourceRegistrationService(CommandService):
    """Publish SOURCE bytes inside the existing command admission lock."""

    def __init__(self, *args, source_document: dict, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_document = source_document

    @contextmanager
    def _submission_lock(self, command):
        with super()._submission_lock(command) as submission:
            artefact_id = command.target_stream_id
            document = self.source_document
            existed_before = self.objects.revision_exists("spec_source_document", artefact_id, 1)
            self.objects.write("spec_source_document", artefact_id, 1, document)
            try:
                yield submission
            finally:
                # This comparison and deletion share admission's writer lock.
                # Preserve bytes if admission appended, even if later work raised.
                if self.ledger.snapshot() == submission.snapshot:
                    self.objects.rollback_new_revision(
                        "spec_source_document", artefact_id, 1, document, existed_before=existed_before
                    )


class SpecCoordinator:
    def __init__(
        self,
        context: VerifiedBindingContext,
        operator: SpecOperatorConfig,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.binding = context.current_binding.revalidate()
        self.operator = operator
        self.clock = clock
        binding = self.binding
        self.schemas = runtime_schema_registry(binding.schema_root)
        self.ledger = EventLedger(binding.control_root, binding.project_id, self.schemas)
        self.objects = ObjectStore(binding.control_root)
        self.resolver = LedgerAuthorityGrantResolver(
            binding.control_root,
            binding.project_id,
            binding.store_identity,
            self.schemas,
            approved_witness=binding.origin_witness,
            approved_witness_path=binding.origin_witness_path,
        )
        self.service = self._command_service()

    def _command_service(self, source_document: dict | None = None) -> CommandService:
        service_type = CommandService if source_document is None else _SourceRegistrationService
        return service_type(
            self.binding.control_root,
            self.ledger,
            self.objects,
            ReceiptStore(self.binding.control_root),
            self.schemas,
            authority_resolver=self.resolver,
            governing_evidence_resolver=GoverningScientificReviewStore(self.objects, self.schemas),
            clock=self.clock,
            **({} if source_document is None else {"source_document": source_document}),
        )

    def _discovery(self) -> DiscoveryRuntime:
        binding = self.binding
        return DiscoveryRuntime(
            binding.control_root,
            self.ledger,
            self.schemas,
            catalogue_path=binding.repository_root / ".research-system/evals/expected/w11-portfolio-discovery-v1.json",
            authority_resolver=self.resolver,
            clock=self.clock,
            repository_root=binding.repository_root,
            root_tokens={"control": binding.control_root, "repo": binding.repository_root},
            operational_ledger=self.ledger,
        )

    def status(self, intent: dict | None = None) -> dict:
        self.binding.revalidate()
        if intent is None:
            actions = []
            for event in self.ledger.snapshot().events:
                if event["event_type"] == "ArtefactRegistered" and event["payload"]["manifest"]["artefact_type"] in {
                    "spec_source_observation",
                    "spec_01_source_correction",
                }:
                    manifest = event["payload"]["manifest"]
                    if (
                        manifest["artefact_schema_version"] == "1.0.0"
                        and manifest["artefact_type"] == "spec_01_source_correction"
                    ):
                        continue  # Historical 1.0.0 remains readable; it is not a new SOURCE action.
                    document, _ = read_document(
                        event["stream_id"], objects=self.objects, schemas=self.schemas, ledger=self.ledger
                    )
                    actions.append(self.status(document["intent"]))
            for task_intent in spec_task.enumerated_intents(self.ledger.snapshot().events):
                try:
                    actions.append(self.status(task_intent))
                except (ConflictError, IntegrityError) as exc:
                    # An explicit status(intent) call must raise on conflicting or
                    # misbound evidence, but the enumerating listing is not a question
                    # about this subject: one decided Task must not deny the whole
                    # route. The entry carries no "state" key, so nothing can read it
                    # as one of the three route states.
                    actions.append(
                        {"action": spec_task.ACTION, **spec_task.subject_ids(task_intent), "unreadable": str(exc)}
                    )
            return {"route_id": self.operator.route_id, "actions": actions, "available_actions": list(ACTION_EFFECTS)}
        if intent.get("action") == spec_task.ACTION:
            self.schemas.validate(spec_task.INTENT_SCHEMA_ID, intent)
            return spec_task.evaluate(
                intent,
                self.ledger.snapshot().events,
                schemas=self.schemas,
                authority_state_validator=self.resolver.validate_replayed_administration_state,
            )
        self.schemas.validate("ars://portfolio/spec-source-intent", intent)
        parse_locator(intent["requested_locator"])
        ids = source_ids(self.binding.project_id, intent)
        events = self.ledger.snapshot().events
        projection = replay_discovery(
            events, schemas=self.schemas, authority_state_validator=self.resolver.validate_replayed_administration_state
        )
        effects = ACTION_EFFECTS[intent["action"]]
        state = {"action": intent["action"], "state": "not_started", **ids, "next_effect": effects[0], "effects": []}
        registered = [
            e for e in events if e["event_type"] == "ArtefactRegistered" and e["stream_id"] == ids["artefact_id"]
        ]
        if not registered:
            return state
        document, registration = read_document(
            ids["artefact_id"], objects=self.objects, schemas=self.schemas, ledger=self.ledger
        )
        if document["intent"] != intent:
            raise ConflictError("SOURCE action key already binds different intent")
        state.update(
            state="prepared",
            registration=registration_ref(registration),
            source_sha256=document["source_sha256"],
            resolution=document["resolution"],
        )
        completed = [registration]
        if intent["action"] == "observe_source":
            observation = projection["source_observations"].get(ids["observation_id"])
            if observation:
                batch = observation["batch"]
                validate_source_refs(
                    batch,
                    events,
                    before_position=observation["global_position"],
                    objects=self.objects,
                    schemas=self.schemas,
                    ledger=self.ledger,
                )
                candidate = projection["candidates"].get(ids["candidate_id"])
                if (
                    batch["raw_source_refs"] != [source_ref(registration)]
                    or candidate is None
                    or candidate["source_observation_refs"] != [ids["observation_id"]]
                    or batch
                    != {
                        "schema_id": "ars://portfolio/scout-observation-batch",
                        "schema_version": "1.0.0",
                        "source_query": intent["repository_url"] + "@" + intent["requested_locator"],
                        "source_version": document["resolution"]["commit_oid"],
                        "observed_at": document["recorded_at"],
                        "returned_identifiers": [ids["artefact_id"]],
                        "normalized_dedup_keys": [ids["artefact_id"]],
                        "raw_source_refs": [source_ref(registration)],
                        "matching_facts": [intent["title"]],
                        "omissions_or_errors": [],
                        "viability_judgment_absent": True,
                    }
                    or candidate.get("title") != intent["title"]
                    or candidate.get("content_sha256")
                    != sha256_hex(
                        canonical_bytes(
                            [
                                {
                                    "observation_id": ids["observation_id"],
                                    "content_sha256": sha256_hex(canonical_bytes(batch)),
                                }
                            ]
                        )
                    )
                ):
                    raise IntegrityError("SOURCE completion is bound to another Candidate or observation")
                completed.append(
                    next(
                        e
                        for e in events
                        if e["event_type"] == "ScoutObservationIngested" and e["stream_id"] == ids["observation_id"]
                    )
                )
        else:
            reviews = [
                e
                for e in events
                if e["event_type"] == "ScientificReviewRecorded"
                and e["stream_id"] == ids["artefact_id"]
                and e["payload"]["scientific_review"] == "approved"
            ]
            if reviews:
                review = reviews[-1]
                if (
                    review["actor_id"] == registration["actor_id"]
                    or review["payload"]["subject_sha256"] != state["registration"]["content_sha256"]
                ):
                    raise IntegrityError("SOURCE correction review lacks exact independent provenance")
                completed.append(review)
                accepted = [
                    e
                    for e in events
                    if e["event_type"] == "ArtefactUseAuthoritySet"
                    and e["stream_id"] == ids["artefact_id"]
                    and e["payload"]["use_authority"] == "accepted_for_scope"
                ]
                if accepted and accepted[-1]["global_position"] > review["global_position"]:
                    use = accepted[-1]
                    if (
                        use["actor_id"] == review["actor_id"]
                        or len(
                            {
                                registration["authority_grant_id"],
                                review["authority_grant_id"],
                                use["authority_grant_id"],
                            }
                        )
                        != 3
                        or use["payload"]["subject_sha256"] != state["registration"]["content_sha256"]
                        or review["payload"]["review_id"] not in use["payload"]["evidence_refs"]
                    ):
                        raise IntegrityError(
                            "SOURCE correction completion lacks separate exact review and use authority"
                        )
                    completed.append(use)
        state["effects"] = [
            {
                "event_id": e["event_id"],
                "event_hash": e["event_hash"],
                "command_id": e["command_id"],
                "actor_id": e["actor_id"],
                "authority_grant_id": e["authority_grant_id"],
            }
            for e in completed
        ]
        state["next_effect"] = effects[len(completed)] if len(completed) < len(effects) else None
        if state["next_effect"] is None:
            state["state"] = "completed"
        return state

    def advance(self, intent: dict, evidence: dict | None = None) -> dict:
        state = self.status(intent)
        now = self.clock().isoformat().replace("+00:00", "Z")
        actor = self.operator.operator_actor_id
        if intent.get("action") == spec_task.ACTION:
            events = self.ledger.snapshot().events
            validator = self.resolver.validate_replayed_administration_state
            # A caller who lost the response repeats the identical invocation after the
            # state has moved on. Replay that committed effect's receipt instead of
            # deriving a different next command from mismatched evidence or authority.
            retry = spec_task.exact_retry(
                intent,
                state,
                events,
                actor_id=actor,
                authority_grant_id=self.operator.authority_grant_id,
                evidence=evidence,
                schemas=self.schemas,
                authority_state_validator=validator,
            )
            if retry is not None:
                effect, target, payload, expected_version = retry
                return self._submit_effect(
                    intent,
                    effect,
                    target,
                    payload,
                    actor,
                    now,
                    intent["reason"],
                    expected_stream_version=expected_version,
                    retry_intent=spec_task.key_intent(intent),
                )
            effect = state["next_effect"]
            if effect is None:
                return state
            target, payload = spec_task.effect_command(
                effect,
                intent,
                events,
                actor_id=actor,
                evidence=evidence,
                schemas=self.schemas,
                authority_state_validator=validator,
            )
            return self._submit_effect(
                intent, effect, target, payload, actor, now, intent["reason"], retry_intent=spec_task.key_intent(intent)
            )
        effect = state["next_effect"]
        if effect is None:
            return state
        artefact_id = state["artefact_id"]
        target = artefact_id
        if effect == "RegisterArtefact":
            document = prepare_document(
                intent,
                artefact_id,
                actor_id=actor,
                now=now,
                objects=self.objects,
                schemas=self.schemas,
                ledger=self.ledger,
            )
            payload = {"new_artefact_id": artefact_id, "manifest": document_manifest(document, artefact_id)}
        elif effect == "IngestScoutObservationBatch":
            document, registration = read_document(
                artefact_id, objects=self.objects, schemas=self.schemas, ledger=self.ledger
            )
            target = state["observation_id"]
            batch = {
                "schema_id": "ars://portfolio/scout-observation-batch",
                "schema_version": "1.0.0",
                "source_query": intent["repository_url"] + "@" + intent["requested_locator"],
                "source_version": document["resolution"]["commit_oid"],
                "observed_at": document["recorded_at"],
                "returned_identifiers": [artefact_id],
                "normalized_dedup_keys": [artefact_id],
                "raw_source_refs": [source_ref(registration)],
                "matching_facts": [intent["title"]],
                "omissions_or_errors": [],
                "viability_judgment_absent": True,
            }
            digest = sha256_hex(canonical_bytes(batch))
            payload = {
                "row_id": "OR-029",
                "observation_id": target,
                "batch": batch,
                "batch_sha256": digest,
                "candidate_blueprints": [
                    {
                        "candidate_id": state["candidate_id"],
                        "revision": 1,
                        "content_sha256": sha256_hex(
                            canonical_bytes([{"observation_id": target, "content_sha256": digest}])
                        ),
                        "source_observation_refs": [target],
                        "title": intent["title"],
                    }
                ],
            }
        else:
            if not isinstance(evidence, dict):
                raise ArsError(f"{effect} requires independent evidence in --input")
            digest = state["registration"]["content_sha256"]
            if effect == "RecordScientificReview":
                if actor == state["effects"][0]["actor_id"] or set(evidence) != {"review_id", "evidence_refs"}:
                    raise IntegrityError("SOURCE correction requires independent review evidence")
                payload = {
                    "artefact_id": artefact_id,
                    "subject_sha256": digest,
                    "scientific_review": "approved",
                    **evidence,
                }
            else:
                if actor == state["effects"][-1]["actor_id"] or self.operator.authority_grant_id in {
                    e["authority_grant_id"] for e in state["effects"]
                }:
                    raise IntegrityError(
                        "SOURCE correction use-authority requires a separate actor and grant from review"
                    )
                if set(evidence) != {"consumer_predicate", "evidence_refs"}:
                    raise IntegrityError("SOURCE correction use-authority evidence fields are not exact")
                payload = {
                    "artefact_id": artefact_id,
                    "subject_sha256": digest,
                    "use_authority": "accepted_for_scope",
                    **evidence,
                }
        return self._submit_effect(
            intent,
            effect,
            target,
            payload,
            actor,
            now,
            intent.get("correction_reason", intent["title"]),
            source_document=document if effect == "RegisterArtefact" else None,
        )

    def _submit_effect(
        self,
        intent: dict,
        effect: str,
        target: str,
        payload: dict,
        actor: str,
        now: str,
        reason: str,
        *,
        source_document: dict | None = None,
        expected_stream_version: int | None = None,
        retry_intent: dict | None = None,
    ) -> dict:
        """Submit one effect through the shared retry key, envelope and admission."""
        retry = "spec:" + sha256_hex(
            canonical_bytes(
                [
                    intent if retry_intent is None else retry_intent,
                    effect,
                    actor,
                    self.operator.authority_grant_id,
                    payload,
                ]
            )
        )
        command = {
            "command_id": _stable_command_id(retry),
            "command_type": effect,
            "actor_id": actor,
            "authority_grant_id": self.operator.authority_grant_id,
            "idempotency_key": retry,
            "target_stream_id": target,
            # An exact retry must bind the version its original submission bound.
            "expected_stream_version": (
                self.ledger.snapshot().stream_versions.get(target, 0)
                if expected_stream_version is None
                else expected_stream_version
            ),
            "payload": payload,
        }
        if effect != "IngestScoutObservationBatch":
            command.update(
                schema_id=f"ars://core/command/{effect}",
                schema_version="1.0.0",
                submitted_at=now,
                on_behalf_of_actor_id=None,
                correlation_id=retry,
                causation_id=None,
                reason=reason,
                evidence_refs=[],
                project_id=self.binding.project_id,
            )
        self.binding.revalidate()
        service = self._discovery() if effect == "IngestScoutObservationBatch" else self.service
        if source_document is not None:
            service = self._command_service(source_document)
        receipt = service.submit(command)
        if receipt.status not in {"accepted", "replayed"}:
            raise ArsError(f"SPEC effect rejected: {asdict(receipt)}")
        return {**self.status(intent), "receipt": asdict(receipt)}
