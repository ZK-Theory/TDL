"""Exactly one owning replay reducer per executable Discovery event type."""

from __future__ import annotations

from typing import Callable

from research_system.discovery.replay import assay
from research_system.discovery.replay import dossier
from research_system.discovery.replay import genesis
from research_system.discovery.replay import promotion
from research_system.discovery.replay import review_decision
from research_system.discovery.replay import scout_candidate
from research_system.discovery.replay import spike
from research_system.discovery.replay.scope import EventScope


REDUCERS: dict[str, Callable[[EventScope], None]] = {
    "AssayCancellationReviewRequested": assay.reduce_assay_cancellation_review_requested,
    "AssayCancellationReviewed": assay.reduce_assay_cancellation_reviewed,
    "AssayCancelled": assay.reduce_assay_cancelled,
    "AssayEvidenceCollectionOpened": assay.reduce_assay_evidence_collection_opened,
    "AssayOutcomeReviewRequested": assay.reduce_assay_cancellation_review_requested,
    "AssayPartialRecorded": assay.reduce_assay_partial_recorded,
    "AssayPartialReviewRequested": assay.reduce_assay_cancellation_review_requested,
    "AssayPartialReviewed": assay.reduce_assay_cancellation_reviewed,
    "AssayRequested": assay.reduce_assay_requested,
    "AssayReviewed": assay.reduce_assay_reviewed,
    "AssayRevisitRequested": review_decision.reduce_assay_revisit_requested,
    "AssayRevisitResolved": review_decision.reduce_assay_revisit_resolved,
    "AssayScored": assay.reduce_assay_scored,
    "AssaySuperseded": review_decision.reduce_assay_superseded,
    "CandidateAssayCancellationReviewed": assay.reduce_candidate_assay_cancellation_reviewed,
    "CandidateAssayLinked": assay.reduce_candidate_assay_linked,
    "CandidateAssayPartialLinked": assay.reduce_candidate_assay_partial_linked,
    "CandidateAssayPartialReviewed": assay.reduce_candidate_assay_cancellation_reviewed,
    "CandidateAssayRequested": assay.reduce_candidate_assay_requested,
    "CandidateAssayRetryStarted": review_decision.reduce_candidate_assay_retry_started,
    "CandidateAssayRevisitRequested": review_decision.reduce_candidate_assay_revisit_requested,
    "CandidateAssayRevisitResolved": review_decision.reduce_candidate_assay_revisit_resolved,
    "CandidateEvaluationCancelled": assay.reduce_candidate_evaluation_cancelled,
    "CandidatePromotionApplied": promotion.reduce_candidate_promotion_applied,
    "CandidatePromotionRequested": promotion.reduce_candidate_promotion_requested,
    "CandidateRegistered": scout_candidate.reduce_candidate_registered,
    "CandidateSpikeAuthorized": spike.reduce_candidate_spike_authorized,
    "CandidateSpikeCancellationReviewed": spike.reduce_candidate_spike_cancellation_reviewed,
    "CandidateSpikePartialLinked": spike.reduce_candidate_spike_partial_linked,
    "CandidateSpikePartialReviewed": spike.reduce_candidate_spike_partial_reviewed,
    "CandidateSpikePlanLinked": spike.reduce_candidate_spike_plan_linked,
    "CandidateSpikeRetryStarted": review_decision.reduce_candidate_assay_retry_started,
    "CandidateSpikeRevisitRequested": review_decision.reduce_candidate_assay_revisit_requested,
    "CandidateSpikeRevisitResolved": review_decision.reduce_candidate_assay_revisit_resolved,
    "CandidateSpikeStarted": spike.reduce_candidate_spike_started,
    "CandidateSpikeVerdictLinked": spike.reduce_candidate_spike_verdict_linked,
    "CandidateSuperseded": scout_candidate.reduce_candidate_superseded,
    "DecisionProposed": review_decision.reduce_decision_proposed,
    "DecisionResolved": review_decision.reduce_decision_resolved,
    "PortfolioObjectRegistered": dossier.reduce_portfolio_object_registered,
    "ResearchDossierAdmitted": dossier.reduce_research_dossier_admitted,
    "ReviewRequested": review_decision.reduce_review_requested,
    "ReviewVerdictRecorded": review_decision.reduce_review_verdict_recorded,
    "ScopeDefinitionRegistered": dossier.reduce_scope_definition_registered,
    "ScoutObservationIngested": scout_candidate.reduce_scout_observation_ingested,
    "SpikeApprovalRequested": spike.reduce_spike_approval_requested,
    "SpikeAttemptClosed": spike.reduce_spike_attempt_closed,
    "SpikeAuthorized": spike.reduce_spike_authorized,
    "SpikeCancellationReviewRequested": spike.reduce_spike_cancellation_review_requested,
    "SpikeCancellationReviewed": spike.reduce_spike_cancellation_reviewed,
    "SpikeCancelled": spike.reduce_spike_cancelled,
    "SpikeExecutionDecisionRequested": spike.reduce_spike_execution_decision_requested,
    "SpikeExecutionProposalSupersededByCancellation": review_decision.reduce_spike_execution_proposal_superseded_by_cancellation,
    "SpikeLeaseReleased": spike.reduce_spike_lease_released,
    "SpikePartialRecorded": spike.reduce_spike_partial_recorded,
    "SpikePartialReviewRequested": spike.reduce_spike_cancellation_review_requested,
    "SpikePartialReviewed": spike.reduce_spike_partial_reviewed,
    "SpikePlanned": spike.reduce_spike_planned,
    "SpikeReviewRequested": spike.reduce_spike_cancellation_review_requested,
    "SpikeReviewed": spike.reduce_spike_reviewed,
    "SpikeRevisitRequested": review_decision.reduce_assay_revisit_requested,
    "SpikeRevisitResolved": review_decision.reduce_assay_revisit_resolved,
    "SpikeStarted": spike.reduce_spike_started,
    "SpikeSuperseded": review_decision.reduce_assay_superseded,
    "SpikeVerdictRecorded": spike.reduce_spike_verdict_recorded,
    "W11CatalogueGenesisImported": genesis.reduce_w11_catalogue_genesis_imported,
}
