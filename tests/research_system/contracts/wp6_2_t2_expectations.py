"""Independent literal expectations for the P-037 WP6.2 T2 contract.

These values are transcribed from P-037, the accepted T2 ruling, W2, W7, W8,
and the normative addendum path named by the authoring dispatch.  They must not
be derived from runtime registration, generated schemas, or candidate YAML.
"""

from __future__ import annotations

from typing import Final

START_REVISION: Final = "ca2674fd39553a16bb583e80fc1463ce7bc59d5f"
WRITER: Final = "research_system.command.service.CommandService"
IDEMPOTENCY_TUPLE: Final = ["actor_id", "authority_scope", "command_type", "idempotency_key"]

ADDENDUM_PATH: Final = (
    "docs/plans/agentic-research-system/design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md"
)
CATALOGUE_PATH: Final = ".research-system/contracts/wp6-2-t2-cost-grant-authority-catalogue.yaml"
CATALOGUE_SCHEMA_PATH: Final = ".research-system/schemas/contracts/wp6-2-t2-cost-grant-authority-catalogue.schema.json"
IDENTITY_MANIFEST_PATH: Final = ".research-system/contracts/wp6-2-t2-schema-identities.yaml"
IDENTITY_MANIFEST_SCHEMA_PATH: Final = ".research-system/schemas/contracts/wp6-2-t2-schema-identities.schema.json"
SEMANTIC_VALIDATOR_PATH: Final = "tests/research_system/contracts/wp6_2_t2_authority_validation.py"
SCHEMA_MATERIALIZER_PATH: Final = "tests/research_system/contracts/wp6_2_t2_schema_materializer.py"
EXPECTATIONS_PATH: Final = "tests/research_system/contracts/wp6_2_t2_expectations.py"
CONTRACT_TEST_PATH: Final = "tests/research_system/contracts/test_wp6_2_t2_authority_contract.py"
MUTATION_TEST_PATH: Final = "tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py"

SCHEMA_IDENTITIES: Final = {
    "secret_reference": {
        "path": ".research-system/schemas/wp6-2-t2/secret-reference.schema.json",
        "schema_id": "ars://wp6-2/t2/secret-reference",
        "schema_version": "1.0.0",
    },
    "cost_grant": {
        "path": ".research-system/schemas/wp6-2-t2/cost-grant.schema.json",
        "schema_id": "ars://wp6-2/t2/cost-grant",
        "schema_version": "1.0.0",
    },
    "provider_command_v2": {
        "path": ".research-system/schemas/wp6-2-t2/provider-command-v2.schema.json",
        "schema_id": "ars://adapters/provider-command/v2",
        "schema_version": "2.0.0",
    },
    "provider_receipt_v2": {
        "path": ".research-system/schemas/wp6-2-t2/provider-receipt-v2.schema.json",
        "schema_id": "ars://adapters/provider-receipt/v2",
        "schema_version": "2.0.0",
    },
    "IssueCostGrant": {
        "path": ".research-system/schemas/wp6-2-t2/commands/issue-cost-grant.schema.json",
        "schema_id": "ars://wp6-2/t2/command/IssueCostGrant",
        "schema_version": "1.0.0",
    },
    "AuthorizeProviderIssue": {
        "path": ".research-system/schemas/wp6-2-t2/commands/authorize-provider-issue.schema.json",
        "schema_id": "ars://wp6-2/t2/command/AuthorizeProviderIssue",
        "schema_version": "1.0.0",
    },
    "RecordProviderReceipt": {
        "path": ".research-system/schemas/wp6-2-t2/commands/record-provider-receipt.schema.json",
        "schema_id": "ars://wp6-2/t2/command/RecordProviderReceipt",
        "schema_version": "1.0.0",
    },
    "CostGrantIssued": {
        "path": ".research-system/schemas/wp6-2-t2/events/cost-grant-issued.schema.json",
        "schema_id": "ars://wp6-2/t2/event/CostGrantIssued",
        "schema_version": "1.0.0",
    },
    "CostGrantReserved": {
        "path": ".research-system/schemas/wp6-2-t2/events/cost-grant-reserved.schema.json",
        "schema_id": "ars://wp6-2/t2/event/CostGrantReserved",
        "schema_version": "1.0.0",
    },
    "ProviderCommandIssued": {
        "path": ".research-system/schemas/wp6-2-t2/events/provider-command-issued.schema.json",
        "schema_id": "ars://wp6-2/t2/event/ProviderCommandIssued",
        "schema_version": "1.0.0",
    },
    "ProviderReceiptRecorded": {
        "path": ".research-system/schemas/wp6-2-t2/events/provider-receipt-recorded.schema.json",
        "schema_id": "ars://wp6-2/t2/event/ProviderReceiptRecorded",
        "schema_version": "1.0.0",
    },
    "CostGrantReconciled": {
        "path": ".research-system/schemas/wp6-2-t2/events/cost-grant-reconciled.schema.json",
        "schema_id": "ars://wp6-2/t2/event/CostGrantReconciled",
        "schema_version": "1.0.0",
    },
}

EXPECTED_ROWS: Final = [
    {
        "key": "cost_grant.issue",
        "command_type": "IssueCostGrant",
        "ordered_events": ["CostGrantIssued"],
        "target_stream_role": "cost_grant",
        "write_set": ["cost_grant"],
        "authority_scope": "wp6.2.t2.cost-grant.issue",
        "authority_subject": "resource_grant",
        "authority_subject_fields": [
            "resource_grant_id",
            "resource_grant_revision",
            "resource_grant_hash",
            "task_id",
            "dispatch_id",
            "attempt_id",
        ],
        "reducers": ["cost_grant_reducer@1.0.0"],
        "projections": [
            "cost_grant_balance_projection@1.0.0",
            "cost_grant_authorization_projection@1.0.0",
        ],
        "positive_test": "pos_issue_cost_grant",
    },
    {
        "key": "provider_issue.authorize",
        "command_type": "AuthorizeProviderIssue",
        "ordered_events": ["CostGrantReserved", "ProviderCommandIssued"],
        "target_stream_role": "cost_grant",
        "write_set": ["cost_grant", "provider_command"],
        "authority_scope": "wp6.2.t2.provider.issue",
        "authority_subject": "cost_grant_provider_command",
        "authority_subject_fields": [
            "cost_grant_id",
            "cost_grant_revision",
            "cost_grant_hash",
            "provider_command_id",
            "provider_command_revision",
            "provider_command_hash",
            "secret_reference_id",
            "secret_reference_revision",
            "secret_reference_hash",
        ],
        "reducers": ["cost_grant_reducer@1.0.0", "provider_command_reducer@2.0.0"],
        "projections": [
            "cost_grant_balance_projection@1.0.0",
            "provider_command_lifecycle_projection@2.0.0",
        ],
        "positive_test": "pos_authorize_provider_issue_atomic",
    },
    {
        "key": "provider_receipt.record",
        "command_type": "RecordProviderReceipt",
        "ordered_events": ["ProviderReceiptRecorded", "CostGrantReconciled"],
        "target_stream_role": "provider_command",
        "write_set": ["provider_command", "cost_grant"],
        "authority_scope": "wp6.2.t2.provider.receipt.record",
        "authority_subject": "issued_provider_command_reservation",
        "authority_subject_fields": [
            "provider_command_id",
            "provider_command_revision",
            "provider_command_hash",
            "provider_receipt_id",
            "provider_receipt_revision",
            "provider_receipt_hash",
            "cost_grant_id",
            "reservation_id",
        ],
        "reducers": ["provider_command_reducer@2.0.0", "cost_grant_reducer@1.0.0"],
        "projections": [
            "provider_command_lifecycle_projection@2.0.0",
            "provider_receipt_binding_projection@2.0.0",
            "cost_grant_balance_projection@1.0.0",
        ],
        "positive_test": "pos_record_provider_receipt_atomic",
    },
]

PRE_ISSUE_SENTINEL_SEAMS: Final = [
    "compiled_context_packet",
    "generated_adapter_provider_file",
    "rendered_provider_payload",
    "argv_environment_config_provider_options",
    "event_producer",
    "receipt_producer",
    "canonical_object_producer",
    "fixture_evaluation_evidence_producer",
]

NEGATIVE_CASES: Final = {
    **{
        f"neg_secret_sentinel_{seam}": {
            "rejection_code": "secret_material_detected",
            "reservation_count": 0,
            "invocation_count": 0,
            "canonical_publication_count": 0,
        }
        for seam in PRE_ISSUE_SENTINEL_SEAMS
    },
    "neg_secret_reference_missing": {"rejection_code": "secret_reference_missing"},
    "neg_secret_reference_wrong_type": {"rejection_code": "secret_reference_wrong_type"},
    "neg_secret_reference_expired": {"rejection_code": "secret_reference_expired"},
    "neg_secret_reference_revoked": {"rejection_code": "secret_reference_revoked"},
    "neg_secret_reference_identity_mismatch": {"rejection_code": "secret_reference_identity_mismatch"},
    "neg_cost_grant_missing": {"rejection_code": "cost_grant_missing"},
    "neg_cost_grant_wrong_type": {"rejection_code": "cost_grant_wrong_type"},
    "neg_cost_grant_zero": {"rejection_code": "cost_grant_zero"},
    "neg_cost_grant_exhausted": {"rejection_code": "cost_grant_exhausted"},
    "neg_cost_grant_expired": {"rejection_code": "cost_grant_expired"},
    "neg_cost_grant_revoked": {"rejection_code": "cost_grant_revoked"},
    "neg_cost_grant_identity_mismatch": {"rejection_code": "cost_grant_identity_mismatch"},
    "neg_cost_grant_insufficient_balance": {"rejection_code": "cost_grant_insufficient_balance"},
    "neg_provider_command_identity_mismatch": {"rejection_code": "provider_command_identity_mismatch"},
    "neg_provider_receipt_identity_mismatch": {"rejection_code": "provider_receipt_identity_mismatch"},
    "neg_provider_receipt_incomplete": {"rejection_code": "provider_receipt_incomplete"},
    "neg_reconciliation_actuals_invalid": {"rejection_code": "reconciliation_actuals_invalid"},
    "neg_concurrent_over_reservation": {"rejection_code": "cost_grant_exhausted"},
    "neg_stale_cost_grant_stream_version": {"rejection_code": "stale_stream_version"},
    "neg_stale_provider_command_stream_version": {"rejection_code": "stale_stream_version"},
    "neg_idempotency_payload_conflict": {"rejection_code": "idempotency_conflict"},
    "neg_accepted_command_replay": {"rejection_code": None},
    "neg_atomic_event_order_swap": {"rejection_code": "event_batch_order_invalid"},
    "neg_atomic_batch_partial": {"rejection_code": "event_batch_incomplete"},
    "neg_reducer_missing": {"rejection_code": "reducer_missing"},
    "neg_projection_missing": {"rejection_code": "projection_missing"},
    "neg_schema_alias_substitution": {"rejection_code": "schema_identity_mismatch"},
    "neg_schema_version_substitution": {"rejection_code": "schema_identity_mismatch"},
    "neg_schema_hash_substitution": {"rejection_code": "schema_hash_mismatch"},
    "neg_provider_command_v1_mutation": {"rejection_code": "protected_artifact_modified"},
    "neg_provider_receipt_v1_mutation": {"rejection_code": "protected_artifact_modified"},
    "neg_wp6_1_t1a_protected_bytes_mutation": {"rejection_code": "protected_artifact_modified"},
}

PROTECTED_TREE_IDENTITIES: Final = {
    ".research-system/schemas/core/commands": "9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea",
    ".research-system/schemas/core/events": "154ffc4bdde82fe903718734687e7a62797b1f69",
    ".research-system/schemas/core": "b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46",
}

PROTECTED_PROVIDER_BLOBS: Final = {
    ".research-system/schemas/adapters/provider-command.schema.json": "9eb58609b9703674912e64f019db3cd4fb147a9c",
    ".research-system/schemas/adapters/provider-receipt.schema.json": "8ac904e6c0b16e45034bcdc2221970d6a3ef13a8",
}

MATERIALIZED_LEAF_PATHS: Final = {
    ADDENDUM_PATH,
    CATALOGUE_PATH,
    CATALOGUE_SCHEMA_PATH,
    IDENTITY_MANIFEST_SCHEMA_PATH,
    SEMANTIC_VALIDATOR_PATH,
    SCHEMA_MATERIALIZER_PATH,
    EXPECTATIONS_PATH,
    CONTRACT_TEST_PATH,
    MUTATION_TEST_PATH,
    *(identity["path"] for identity in SCHEMA_IDENTITIES.values()),
}
