from __future__ import annotations

ADDENDUM_PATH = "docs/plans/agentic-research-system/design/10-wp6-2-t3-t4-live-issue-binding-addendum-2026-07-23.md"
CATALOGUE_PATH = ".research-system/contracts/wp6-2-t3-t4-live-issue-catalogue.yaml"
CATALOGUE_SCHEMA_PATH = ".research-system/schemas/contracts/wp6-2-t3-t4-live-issue-catalogue.schema.json"
IDENTITY_MANIFEST_PATH = ".research-system/contracts/wp6-2-t3-t4-live-issue-schema-identities.yaml"
IDENTITY_MANIFEST_SCHEMA_PATH = (
    ".research-system/schemas/contracts/wp6-2-t3-t4-live-issue-schema-identities.schema.json"
)
TRUSTED_RESOLVER_PATH = ".research-system/contracts/wp6-2-t3-t4-trusted-resolver-authorities.yaml"
TRUSTED_RESOLVER_SCHEMA_PATH = ".research-system/schemas/contracts/wp6-2-t3-t4-trusted-resolver-authorities.schema.json"

EXPECTED_TRANSITIONS = {
    "live_provider_invocation.claim": {
        "command_type": "ClaimLiveProviderInvocation",
        "ordered_events": ["LiveProviderInvocationClaimed"],
        "stream_role": "provider_invocation",
        "writer": "research_system.command.service.CommandService",
    },
    "live_provider_invocation.outcome.record": {
        "command_type": "RecordLiveProviderInvocationOutcome",
        "ordered_events": [
            "ProviderInvocationOutcomeRecorded",
            "LiveProviderReceiptRecorded",
            "LiveCostGrantReconciled",
        ],
        "stream_role": "provider_invocation",
        "writer": "research_system.command.service.CommandService",
    },
}

EXPECTED_SCHEMA_IDENTITIES = {
    "live_issue_binding": (
        ".research-system/schemas/wp6-2-live-issue/live-issue-binding.schema.json",
        "ars://wp6-2/live-issue/LiveIssueBinding",
        "1.0.0",
    ),
    "credential_use_receipt": (
        ".research-system/schemas/wp6-2-live-issue/credential-use-receipt.schema.json",
        "ars://wp6-2/live-issue/CredentialUseReceipt",
        "1.0.0",
    ),
    "provider_invocation_evidence": (
        ".research-system/schemas/wp6-2-live-issue/provider-invocation-evidence.schema.json",
        "ars://wp6-2/live-issue/ProviderInvocationEvidence",
        "1.0.0",
    ),
    "live_provider_receipt_v3": (
        ".research-system/schemas/wp6-2-live-issue/live-provider-receipt-v3.schema.json",
        "ars://adapters/provider-receipt/v3",
        "3.0.0",
    ),
    "claim_command": (
        ".research-system/schemas/wp6-2-live-issue/commands/claim-live-provider-invocation.schema.json",
        "ars://wp6-2/live-issue/command/ClaimLiveProviderInvocation",
        "1.0.0",
    ),
    "record_outcome_command": (
        ".research-system/schemas/wp6-2-live-issue/commands/record-live-provider-invocation-outcome.schema.json",
        "ars://wp6-2/live-issue/command/RecordLiveProviderInvocationOutcome",
        "1.0.0",
    ),
    "claimed_event": (
        ".research-system/schemas/wp6-2-live-issue/events/live-provider-invocation-claimed.schema.json",
        "ars://wp6-2/live-issue/event/LiveProviderInvocationClaimed",
        "1.0.0",
    ),
    "outcome_event": (
        ".research-system/schemas/wp6-2-live-issue/events/provider-invocation-outcome-recorded.schema.json",
        "ars://wp6-2/live-issue/event/ProviderInvocationOutcomeRecorded",
        "1.0.0",
    ),
    "receipt_event": (
        ".research-system/schemas/wp6-2-live-issue/events/live-provider-receipt-recorded.schema.json",
        "ars://wp6-2/live-issue/event/LiveProviderReceiptRecorded",
        "1.0.0",
    ),
    "reconciliation_event": (
        ".research-system/schemas/wp6-2-live-issue/events/live-cost-grant-reconciled.schema.json",
        "ars://wp6-2/live-issue/event/LiveCostGrantReconciled",
        "1.0.0",
    ),
    "trusted_resolver_authorities": (
        TRUSTED_RESOLVER_SCHEMA_PATH,
        "ars://contracts/wp6-2-t3-t4-trusted-resolver-authorities",
        "1.0.0",
    ),
    "provider_invocation_reducer": (
        ".research-system/schemas/wp6-2-live-issue/components/provider-invocation-reducer.schema.json",
        "ars://wp6-2/live-issue/reducer/provider-invocation",
        "1.0.0",
    ),
    "live_provider_receipt_reducer": (
        ".research-system/schemas/wp6-2-live-issue/components/live-provider-receipt-reducer.schema.json",
        "ars://wp6-2/live-issue/reducer/live-provider-receipt",
        "3.0.0",
    ),
    "cost_grant_reducer": (
        ".research-system/schemas/wp6-2-live-issue/components/cost-grant-reducer.schema.json",
        "ars://wp6-2/live-issue/reducer/cost-grant",
        "1.0.0",
    ),
    "provider_invocation_lifecycle_projection": (
        ".research-system/schemas/wp6-2-live-issue/components/provider-invocation-lifecycle-projection.schema.json",
        "ars://wp6-2/live-issue/projection/provider-invocation-lifecycle",
        "1.0.0",
    ),
    "live_provider_receipt_binding_projection": (
        ".research-system/schemas/wp6-2-live-issue/components/live-provider-receipt-binding-projection.schema.json",
        "ars://wp6-2/live-issue/projection/live-provider-receipt-binding",
        "3.0.0",
    ),
    "cost_grant_balance_projection": (
        ".research-system/schemas/wp6-2-live-issue/components/cost-grant-balance-projection.schema.json",
        "ars://wp6-2/live-issue/projection/cost-grant-balance",
        "1.0.0",
    ),
}

EXPECTED_DIRECT_DEPENDENCY_EDGES = {
    ("LiveIssueBinding", "claim_intent_hash"),
    ("claim_intent_hash", "CredentialUseReceipt"),
    ("claim_intent_hash", "completed_claim_payload_hash"),
    ("LiveIssueBinding", "completed_claim_payload_hash"),
    ("CredentialUseReceipt", "completed_claim_payload_hash"),
}

INTENT_EXCLUDED_FIELDS = {
    "credential_use_receipt_id",
    "credential_use_receipt_revision",
    "credential_use_receipt_hash",
    "payload_hash",
    "submitted_at",
    "recorded_at",
}
