"""Fixed-kind production consumer port for replay-authorized artefacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from research_system.artefacts.use_resolver import (
    ArtefactUseRequest,
    ArtefactUseResolver,
    ResolvedArtefactEvidence,
)
from research_system.store.ledger import LedgerSnapshot


@dataclass(frozen=True)
class ArtefactConsumerContext:
    """Exact subject and scope common to every fixed consumer method."""

    artefact_id: str
    exact_content_sha256: str
    project_id: str
    task_id: str
    scope_id: str
    evaluation_time: datetime


class ArtefactEvidenceConsumers:
    """Expose the five accepted consumer kinds without a generic public fallback."""

    def __init__(self, resolver: ArtefactUseResolver) -> None:
        self._resolver = resolver

    def resolve_for_result(
        self,
        context: ArtefactConsumerContext,
        *,
        consumer_id: str,
        expected_snapshot: LedgerSnapshot | None = None,
    ) -> ResolvedArtefactEvidence:
        """Resolve result evidence for a policy-enumerated concrete caller."""
        return self._resolve(
            context,
            consumer_id=consumer_id,
            consumer_kind="result_evidence",
            expected_snapshot=expected_snapshot,
        )

    def capture_authority_snapshot(self) -> LedgerSnapshot:
        """Freeze the replay tail shared by one multi-reference operation."""
        return self._resolver.ledger.snapshot()

    def resolve_for_review(
        self,
        context: ArtefactConsumerContext,
        *,
        consumer_id: str,
    ) -> ResolvedArtefactEvidence:
        """Resolve review evidence for a policy-enumerated concrete caller."""
        return self._resolve(context, consumer_id=consumer_id, consumer_kind="review_evidence")

    def resolve_for_manuscript(
        self,
        context: ArtefactConsumerContext,
        *,
        consumer_id: str,
    ) -> ResolvedArtefactEvidence:
        """Resolve manuscript evidence for a policy-enumerated concrete caller."""
        return self._resolve(context, consumer_id=consumer_id, consumer_kind="manuscript_evidence")

    def resolve_for_claim(
        self,
        context: ArtefactConsumerContext,
        *,
        consumer_id: str,
    ) -> ResolvedArtefactEvidence:
        """Resolve claim evidence only with the accepted P-005 decision requirement."""
        return self._resolve(context, consumer_id=consumer_id, consumer_kind="claim_evidence")

    def resolve_sensitive_sidecar(
        self,
        context: ArtefactConsumerContext,
        *,
        consumer_id: str,
    ) -> ResolvedArtefactEvidence:
        """Resolve a sensitive sidecar only for its closed independent consumer."""
        return self._resolve(context, consumer_id=consumer_id, consumer_kind="sensitive_sidecar")

    def _resolve(
        self,
        context: ArtefactConsumerContext,
        *,
        consumer_id: str,
        consumer_kind: str,
        expected_snapshot: LedgerSnapshot | None = None,
    ) -> ResolvedArtefactEvidence:
        contract = self._resolver.contract_loader.load()
        predicate, predicate_sha256 = contract.predicate_for(consumer_kind)
        decision_kind = predicate.get("required_decision_kind")
        if decision_kind is not None and not isinstance(decision_kind, str):
            raise TypeError("accepted consumer predicate decision kind is invalid")
        return self._resolver.resolve(
            ArtefactUseRequest(
                artefact_id=context.artefact_id,
                exact_content_sha256=context.exact_content_sha256,
                consumer_id=consumer_id,
                consumer_kind=consumer_kind,
                project_id=context.project_id,
                task_id=context.task_id,
                scope_id=context.scope_id,
                predicate_id=str(predicate["predicate_id"]),
                predicate_version=str(predicate["predicate_version"]),
                predicate_sha256=predicate_sha256,
                evaluation_time=context.evaluation_time,
                required_decision_kind=decision_kind,
            ),
            expected_snapshot=expected_snapshot,
        )


__all__ = ["ArtefactConsumerContext", "ArtefactEvidenceConsumers"]
