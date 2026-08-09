# WP6.1 06h current producer and evidence record

**Record date:** 2026-08-09

**Accounted base:** `a5d86ed9512a3db5e6532ca8dabf13d203b902e5`

**Base tree:** `8206c60fef0691aaa24a4d56bf4182875110c8ac`

**Branch:** `codex/wp6-1-kan95-06h-acceptance`

**Status:** exact 06h candidate construction; G-RM-8 and owner acceptance remain open

## Capability truth

C2 remains **INCOMPLETE**. The current-schema identity, producer binding, and
append-path accounting candidate is implemented and directly testable, but 06h
cannot be accepted until:

1. an independent exact-subject review accepts the complete candidate;
2. Stephen selects one G-RM-8 historical protocol using the independent
   evidence required by the governing 06h plan; and
3. Stephen separately accepts the exact reviewed G-RM-9/06h subject.

This record does not activate 06i Stage A, author G-RM-14 bytes, or authorize
`artefact.register`.

## Exact authorities preserved

| Authority | Exact identity at accounted base |
|---|---|
| Accepted owner source catalogue | `.research-system/contracts/wp6-1-owner-source-catalogue.yaml`, blob `1adc66921ee9c90d8786ff173748150922f1035e` |
| Core command schemas | tree `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` |
| Core event schemas | tree `154ffc4bdde82fe903718734687e7a62797b1f69` |

The candidate does not change any of these bytes.

## Current append-path census

The executable manifest is
`tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml`. Its AST
reconciliation gate fails on an unmanifested or stale ledger append site. The
accounted sites are:

| Path and symbol | Receiver | Disposition |
|---|---|---|
| `research_system/authority.py::initialize_authority_control_store` | `ledger` | commandless system bootstrap |
| `research_system/command/service.py::submit` | `self.ledger` | generic and guarded command producer |
| `research_system/command/t2.py::submit_t2` | `service.ledger` | T2 command producer |
| `research_system/evals/executors/control_store.py::execute_s009` | `ledger` | commandless evaluation fixture |
| `research_system/evals/executors/control_store.py::execute_s011` | `ledger` | commandless evaluation fixture |
| `research_system/evals/scenarios.py::recover_writer` | `ledger` | commandless evaluation fixture |

The active runtime catalogue contains 86 deterministically ordered bindings.
The canonical rows
`schema_id|schema_version|command_type|event_type|producer_command_type|policy_action_type`
have SHA-256
`d82e45d75df6363c2ee9e5d99acb74ab1a9323034daf24a8a2be8710acfaa725`.

## Current candidate behavior

- One frozen `RegisteredSchema` retains the schema ID/version, source path,
  exact raw bytes, raw-byte SHA-256, and parsed JSON from one read.
- Validation and identity resolution return the same record object.
- Parsed schema JSON remains compatible with `jsonschema` while rejecting
  nested object and array mutation.
- Later source-file mutation cannot change the registered bytes, digest,
  parsed contract, or validation result.
- Duplicate exact schema identities fail registry construction.
- The public generic command path appends an event carrying the exact validated
  schema triple.
- Existing generic, guarded-release, and T2 controls remain bound in the
  executable manifest.
- Direct generic and T2 append attempts without the complete triple fail before
  any batch is committed.

## Historical evidence boundary

No valid pre-06h suite freeze was recorded before the producer mechanics that
are already on `main`. RM-01 marks that pre-change evidence as
non-reconstructible. This candidate therefore records the current append and
binding state and does **not** invent a substitute historical baseline.

The runtime remains fail-closed by default for missing provenance. No G-RM-8
branch is activated by this candidate. In particular, a dormant positional
legacy replay parameter is not evidence for the grandfather protocol because
it is not bound to `store_identity`, `ledger_fingerprint`, and
`max_global_position` as the governing contract requires.

## Exact owner decision required

Stephen must select exactly one G-RM-8 branch after its required independent
evidence is available:

- **Migrate:** bind an immutable store inventory and content-addressed
  transformation, with projection-equivalence, repeat-run, and rollback proof.
- **Grandfather:** bind `store_identity`, `ledger_fingerprint`, and
  `max_global_position`; field shape or position alone is inadmissible.
- **No prior store:** provide independent declared-root/store/backup discovery
  plus operator attestation, including the planted out-of-first-root negative.

Until that selection is recorded and implemented with the governing positive,
new-malformed, repeat, genesis, incremental, and rollback/stop controls, 06h is
owner-blocked and 06i Stage A remains unlawful to author.

## Candidate validation

Interpreter: `C:\Users\steph\TDL\.venv\Scripts\python.exe`

Pytest controls: plugin autoload disabled, repository `addopts` cleared, cache
provider disabled, and coverage startup disabled.

The final targeted behavior gate passed **55 tests in 157.69 seconds**. It
covered the complete `test_schema_registry.py` module, the executable 06h
manifest/smoke module, and the exact generic-command, T2, and ledger provenance
controls named in the manifest. Ruff passed for every changed Python file.

Two release-publication tests remain separately unresolved at the accounted
base behavior and are not counted as candidate passes:

- `test_authorized_verified_command_publishes_one_self_referential_event`
  stops during unrelated S-014 fixture calibration because the known-bad
  payload lacks its declared `mutation_id`.
- `test_command_service_submit_preserves_public_signature_and_guard_metadata`
  reaches the current paired-continuation guard but asserts an older singular
  error-message fragment.

KAN-95 does not authorize remediation of these unrelated release-fixture
baselines. The executable append census retains the guarded-release
classification; neither failure is presented as 06h green evidence.
