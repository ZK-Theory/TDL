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
from research_system.command.models import Command
from research_system.command.service import CommandService
from research_system.discovery.commands import DISCOVERY_COMMAND_TYPES
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
from research_system.discovery import spec_assay, spec_result, spec_task
from research_system.discovery.spec_source import DOCUMENT_KIND as SOURCE_DOCUMENT_KIND
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
    spec_result.REGISTER: spec_result.REGISTER_EFFECTS,
    spec_result.ACCEPT: spec_result.ACCEPT_EFFECTS,
    **spec_assay.ACTIONS,
}


class _DocumentRegistrationService(CommandService):
    """Publish a registered document's bytes inside the existing command admission lock.

    Each subclass names its object kind as a literal at every store call, so the 06i
    storage-boundary contract can classify each direct object-store kind statically.
    """

    def __init__(self, *args, document: dict, **kwargs):
        super().__init__(*args, **kwargs)
        self.document = document

    def _publish(self, artefact_id: str) -> bool:
        raise NotImplementedError

    def _withdraw(self, artefact_id: str, existed_before: bool) -> None:
        raise NotImplementedError

    @contextmanager
    def _submission_lock(self, command):
        with super()._submission_lock(command) as submission:
            artefact_id = command.target_stream_id
            existed_before = self._publish(artefact_id)
            try:
                yield submission
            finally:
                # This comparison and deletion share admission's writer lock.
                # Preserve bytes if admission appended, even if later work raised.
                if self.ledger.snapshot() == submission.snapshot:
                    self._withdraw(artefact_id, existed_before)


class _SourceRegistrationService(_DocumentRegistrationService):
    def _publish(self, artefact_id: str) -> bool:
        existed_before = self.objects.revision_exists("spec_source_document", artefact_id, 1)
        self.objects.write("spec_source_document", artefact_id, 1, self.document)
        return existed_before

    def _withdraw(self, artefact_id: str, existed_before: bool) -> None:
        self.objects.rollback_new_revision(
            "spec_source_document", artefact_id, 1, self.document, existed_before=existed_before
        )


class _ProjectUseRegistrationService(_DocumentRegistrationService):
    def _publish(self, artefact_id: str) -> bool:
        existed_before = self.objects.revision_exists("project_use_decision_document", artefact_id, 1)
        self.objects.write("project_use_decision_document", artefact_id, 1, self.document)
        return existed_before

    def _withdraw(self, artefact_id: str, existed_before: bool) -> None:
        self.objects.rollback_new_revision(
            "project_use_decision_document", artefact_id, 1, self.document, existed_before=existed_before
        )


class _BriefRegistrationService(_DocumentRegistrationService):
    def _publish(self, artefact_id: str) -> bool:
        existed_before = self.objects.revision_exists("spec_operator_brief_document", artefact_id, 1)
        self.objects.write("spec_operator_brief_document", artefact_id, 1, self.document)
        return existed_before

    def _withdraw(self, artefact_id: str, existed_before: bool) -> None:
        self.objects.rollback_new_revision(
            "spec_operator_brief_document", artefact_id, 1, self.document, existed_before=existed_before
        )


class _ReturnRegistrationService(_DocumentRegistrationService):
    def _publish(self, artefact_id: str) -> bool:
        existed_before = self.objects.revision_exists("spec_operator_return_document", artefact_id, 1)
        self.objects.write("spec_operator_return_document", artefact_id, 1, self.document)
        return existed_before

    def _withdraw(self, artefact_id: str, existed_before: bool) -> None:
        self.objects.rollback_new_revision(
            "spec_operator_return_document", artefact_id, 1, self.document, existed_before=existed_before
        )


_REGISTRATION_SERVICES = {
    SOURCE_DOCUMENT_KIND: _SourceRegistrationService,
    spec_result.DOCUMENT_KIND: _ProjectUseRegistrationService,
    spec_assay.BRIEF_KIND: _BriefRegistrationService,
    spec_assay.RETURN_KIND: _ReturnRegistrationService,
}


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

    def _command_service(self, document: tuple[str, dict] | None = None) -> CommandService:
        service_type = CommandService if document is None else _REGISTRATION_SERVICES[document[0]]
        return service_type(
            self.binding.control_root,
            self.ledger,
            self.objects,
            ReceiptStore(self.binding.control_root),
            self.schemas,
            authority_resolver=self.resolver,
            governing_evidence_resolver=GoverningScientificReviewStore(self.objects, self.schemas),
            clock=self.clock,
            **({} if document is None else {"document": document[1]}),
        )

    def _result_context(self) -> spec_result.RouteContext:
        return spec_result.RouteContext(
            project_id=self.binding.project_id,
            objects=self.objects,
            schemas=self.schemas,
            validator=self.resolver.validate_replayed_administration_state,
            raw_prefix_sha256=self.ledger.raw_prefix_sha256,
            read_source_document=lambda artefact_id: read_document(
                artefact_id, objects=self.objects, schemas=self.schemas, ledger=self.ledger
            ),
            check_review_evidence=self._check_review_evidence,
        )

    def _assay_context(self) -> spec_assay.AssayContext:
        return spec_assay.AssayContext(
            project_id=self.binding.project_id,
            schemas=self.schemas,
            validator=self.resolver.validate_replayed_administration_state,
            repository_root=self.binding.repository_root,
            objects=self.objects,
            raw_prefix_sha256=self.ledger.raw_prefix_sha256,
        )

    def _check_review_evidence(self, registration: dict, review: dict, use: dict, actor_id: str, now: str) -> None:
        """Refuse review evidence that inherited use-authority admission would later reject.

        RecordScientificReview admission records any evidence refs, but only exactly
        governing evidence lets SetArtefactUseAuthority accept the artefact, and the
        route allows one review per decision. So the inherited governing-review rule
        runs over the prospective review before it becomes durable.
        """
        artefact_id = registration["stream_id"]
        prospective = {
            "event_type": "ScientificReviewRecorded",
            "payload": review,
            "actor_id": actor_id,
            "stream_version": registration["stream_version"] + 1,
            "event_id": None,
            "event_hash": None,
            "recorded_at": now,
        }
        command = Command(
            {
                "command_type": "SetArtefactUseAuthority",
                "target_stream_id": artefact_id,
                "submitted_at": now,
                "payload": use,
            }
        )
        outcome = self.service._validate_governing_review_evidence(
            command, [registration, prospective], registration["payload"]["manifest"]
        )
        if isinstance(outcome, tuple):
            raise IntegrityError(f"{spec_result.ACCEPT} review evidence would not govern use authority: {outcome[0]}")

    def result(self, task_id: str, output_format: str) -> dict | str:
        """Return the Task-specific project-use result.

        Args:
            task_id: The Task whose result is rendered; isolates it from every other Task.
            output_format: ``json`` for the result record or ``markdown`` for human text.

        Returns:
            The result record, or its Markdown rendering.
        """
        self.binding.revalidate()
        if not isinstance(task_id, str) or not task_id.startswith("tsk_"):
            raise ArsError("--task-id must name a Task")
        output = spec_result.result(
            task_id, self.ledger.snapshot().events, self._result_context(), route_id=self.operator.route_id
        )
        return output if output_format == "json" else spec_result.render_markdown(output)

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
            events = self.ledger.snapshot().events
            context = self._result_context()
            for task_id in spec_result.enumerated_tasks(events):
                for action in (spec_result.REGISTER, spec_result.ACCEPT):
                    try:
                        actions.append(spec_result.evaluate(action, task_id, events, context))
                    except (ConflictError, IntegrityError) as exc:
                        # As for close_task, the listing must not deny the whole route.
                        actions.append({"action": action, "task_id": task_id, "unreadable": str(exc)})
            assay_context = self._assay_context()
            for assay_intent in spec_assay.enumerated_intents(events, assay_context):
                try:
                    actions.append(spec_assay.evaluate(assay_intent, events, assay_context))
                except (ConflictError, IntegrityError) as exc:
                    # As for close_task, the listing must not deny the whole route.
                    actions.append({"action": assay_intent["action"], "unreadable": str(exc)})
            return {"route_id": self.operator.route_id, "actions": actions, "available_actions": list(ACTION_EFFECTS)}
        if intent.get("action") in spec_assay.ACTIONS:
            self.schemas.validate(spec_assay.INTENT_SCHEMA_ID, intent)
            return spec_assay.evaluate(intent, self.ledger.snapshot().events, self._assay_context())
        if intent.get("action") == spec_task.ACTION:
            self.schemas.validate(spec_task.INTENT_SCHEMA_ID, intent)
            return spec_task.evaluate(
                intent,
                self.ledger.snapshot().events,
                schemas=self.schemas,
                authority_state_validator=self.resolver.validate_replayed_administration_state,
            )
        if intent.get("action") in {spec_result.REGISTER, spec_result.ACCEPT}:
            self.schemas.validate(spec_result.INTENT_SCHEMA_ID, intent)
            return spec_result.evaluate(
                intent["action"],
                intent["task_id"],
                self.ledger.snapshot().events,
                self._result_context(),
                intent=intent if intent["action"] == spec_result.REGISTER else None,
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
        if intent.get("action") in spec_assay.ACTIONS:
            return self._advance_assay(intent, evidence)
        if intent.get("action") == spec_task.ACTION:
            return self._advance_task(intent, evidence)
        if intent.get("action") in {spec_result.REGISTER, spec_result.ACCEPT}:
            return self._advance_project_use(intent, evidence)
        state = self.status(intent)
        now = self.clock().isoformat().replace("+00:00", "Z")
        actor = self.operator.operator_actor_id
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
            document=(SOURCE_DOCUMENT_KIND, document) if effect == "RegisterArtefact" else None,
        )

    def _advance_task(self, intent: dict, evidence: dict | None) -> dict:
        """Advance close_task from one ledger snapshot.

        State, the next command and its expected stream version all come from the same
        snapshot. If another process commits the identical effect first, this command
        binds the version that commit bound and admission replays it; any other commit
        fails the version check instead of pairing stale state with newer evidence.

        Known limit: admission binds only the target stream's version. A Task-stream
        commit by another process between this snapshot and a Review-stream effect
        does not stop that effect appending. Closure stays safe, because the next
        evaluation reads the Task event as conflicting evidence and the action cannot
        complete. Binding both versions atomically would need new CommandService
        machinery, which is out of scope for this route.
        """
        self.binding.revalidate()
        self.schemas.validate(spec_task.INTENT_SCHEMA_ID, intent)
        snapshot = self.ledger.snapshot()
        validator = self.resolver.validate_replayed_administration_state
        state = spec_task.evaluate(intent, snapshot.events, schemas=self.schemas, authority_state_validator=validator)
        actor = self.operator.operator_actor_id

        # A caller who lost the response repeats the identical invocation after the
        # state has moved on. Answer it from the committed receipt, never by
        # resubmitting: admission resolves current authority before its receipt check,
        # so an exact retry after grant expiry would be refused despite its effect.
        def replay_receipt(latest_only: bool) -> dict | None:
            retry = spec_task.exact_retry(
                intent,
                state,
                snapshot.events,
                actor_id=actor,
                authority_grant_id=self.operator.authority_grant_id,
                evidence=evidence,
                schemas=self.schemas,
                authority_state_validator=validator,
                latest_only=latest_only,
            )
            if retry is None:
                return None
            receipt = self.service.receipts.load(retry["command_id"])
            if receipt is None or receipt.status != "accepted" or receipt.payload_hash != retry["command_payload_hash"]:
                raise IntegrityError(f"close_task retry has no matching committed receipt: {retry['command_id']}")
            return {**state, "receipt": asdict(receipt)}

        replayed = replay_receipt(latest_only=True)
        if replayed is not None:
            return replayed
        effect = state["next_effect"]
        if effect is None:
            return replay_receipt(latest_only=False) or state
        try:
            target, payload = spec_task.effect_command(
                effect,
                intent,
                snapshot.events,
                actor_id=actor,
                evidence=evidence,
                schemas=self.schemas,
                authority_state_validator=validator,
            )
        except ArsError:
            # An invocation does not name its effect, and SubmitForReview and AcceptTask
            # share actor, grant and evidence shape. So earlier effects are consulted only
            # when this invocation cannot build the next one: an invocation valid for the
            # next effect is that effect, never a retry of an earlier one.
            replayed = replay_receipt(latest_only=False)
            if replayed is not None:
                return replayed
            raise
        return self._submit_effect(
            intent,
            effect,
            target,
            payload,
            actor,
            self.clock().isoformat().replace("+00:00", "Z"),
            intent["reason"],
            expected_stream_version=snapshot.stream_versions.get(target, 0),
            retry_intent=spec_task.key_intent(intent),
        )

    def _advance_assay(self, intent: dict, evidence: dict | None) -> dict:
        """Advance a W11 bootstrap or SPEC-01 Assay action from one ledger snapshot.

        State, the next command and its expected stream version all come from the same
        snapshot. A repeated invocation of a committed effect is answered from its
        receipt and never resubmitted, so it stays readable after its grant expires. The
        operator records publish their bytes inside the registration's admission lock.
        """
        self.binding.revalidate()
        self.schemas.validate(spec_assay.INTENT_SCHEMA_ID, intent)
        snapshot = self.ledger.snapshot()
        context = self._assay_context()
        state = spec_assay.evaluate(intent, snapshot.events, context)
        actor, grant = self.operator.operator_actor_id, self.operator.authority_grant_id
        retry = spec_assay.exact_retry(intent, evidence, snapshot.events, context, actor_id=actor, grant_id=grant)
        if retry is not None:
            receipt = self.service.receipts.load(retry["command_id"])
            if receipt is None or receipt.status != "accepted" or receipt.payload_hash != retry["command_payload_hash"]:
                raise IntegrityError(
                    f"{intent['action']} retry has no matching committed receipt: {retry['command_id']}"
                )
            return {**state, "receipt": asdict(receipt)}
        if state["next_effect"] is None:
            return state
        now = self.clock().isoformat().replace("+00:00", "Z")
        effect, target, payload, document = spec_assay.next_command(
            intent, evidence, snapshot.events, context, actor_id=actor, grant_id=grant, now=now
        )
        return self._submit_effect(
            intent,
            effect,
            target,
            payload,
            actor,
            now,
            intent["reason"],
            document=document,
            expected_stream_version=snapshot.stream_versions.get(target, 0),
            retry_intent=spec_assay.key_intent(intent),
        )

    def _advance_project_use(self, intent: dict, evidence: dict | None) -> dict:
        """Advance a project-use action from one ledger snapshot.

        State, the next command and its expected stream version all come from the same
        snapshot. A repeated invocation of a committed effect is answered from its
        receipt and never resubmitted, so it stays readable after its grant expires.
        """
        self.binding.revalidate()
        self.schemas.validate(spec_result.INTENT_SCHEMA_ID, intent)
        snapshot = self.ledger.snapshot()
        context = self._result_context()
        action = intent["action"]
        state = spec_result.evaluate(
            action,
            intent["task_id"],
            snapshot.events,
            context,
            intent=intent if action == spec_result.REGISTER else None,
        )
        actor, grant = self.operator.operator_actor_id, self.operator.authority_grant_id
        retry = spec_result.exact_retry(intent, evidence, snapshot.events, context, actor_id=actor, grant_id=grant)
        if retry is not None:
            receipt = self.service.receipts.load(retry["command_id"])
            if receipt is None or receipt.status != "accepted" or receipt.payload_hash != retry["command_payload_hash"]:
                raise IntegrityError(f"{action} retry has no matching committed receipt: {retry['command_id']}")
            return {**state, "receipt": asdict(receipt)}
        if state["next_effect"] is None:
            return state
        now = self.clock().isoformat().replace("+00:00", "Z")
        effect, target, payload, document = spec_result.next_command(
            intent, evidence, snapshot.events, context, actor_id=actor, grant_id=grant, now=now
        )
        return self._submit_effect(
            intent,
            effect,
            target,
            payload,
            actor,
            now,
            intent["reason"],
            document=None if document is None else (spec_result.DOCUMENT_KIND, document),
            expected_stream_version=snapshot.stream_versions.get(target, 0),
            retry_intent=spec_result.key_intent(intent),
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
        document: tuple[str, dict] | None = None,
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
        if effect not in DISCOVERY_COMMAND_TYPES:
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
        service = self._discovery() if effect in DISCOVERY_COMMAND_TYPES else self.service
        if document is not None:
            service = self._command_service(document)
        receipt = service.submit(command)
        if receipt.status not in {"accepted", "replayed"}:
            raise ArsError(f"SPEC effect rejected: {asdict(receipt)}")
        return {**self.status(intent), "receipt": asdict(receipt)}
