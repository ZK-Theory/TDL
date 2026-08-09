# WP6.1 06h live-main current producer and evidence record

**Record date:** 2026-08-09

**Accounted base:** `9736c900fd4f72e84b2208eeff0dcfb2a2b44106`

**Base tree:** `24c95b02694229976abdb02d701ec39b36865a9e`

**Branch:** `codex/wp6-1-kan95-06h-reconcile-9736c90`

**Historical candidate preserved:** `6cc557198f0fc0f624ffd834643ec2788f8d2711`

**Status:** exact live-main 06h candidate construction; G-RM-8, independent review,
and owner acceptance remain open

## Capability truth

C2 remains **INCOMPLETE**. The G-RM-9/current-schema identity, current producer
binding, and complete append-path accounting candidate is implemented against
the PR #222 merge, but 06h cannot be accepted until:

1. Stephen selects one G-RM-8 historical protocol using the independent
   evidence required by the governing 06h plan;
2. the selected protocol is implemented with the required positive,
   new-malformed, repeat, genesis, incremental, and rollback/stop controls;
3. one fresh no-history independent reviewer accepts that complete exact
   subject; and
4. Stephen separately accepts the exact reviewed 06h subject.

This record does not activate G-RM-8 or 06i Stage A, author G-RM-14 bytes,
authorize `artefact.register`, commission review, or claim acceptance.

## Exact live-main authorities preserved

| Authority | Exact identity at accounted base |
|---|---|
| Accepted owner source catalogue | `.research-system/contracts/wp6-1-owner-source-catalogue.yaml`, blob `1adc66921ee9c90d8786ff173748150922f1035e` |
| Core command schemas | tree `8a86a0c4921343e6a3afca3f491fad33e9a8a10f` |
| Core event schemas | tree `058c1d5ddcb9d249916977f12b11768b6d15de0f` |

The candidate does not change any of these bytes. Both C1 merge commits,
PR #212 merge `23dcfaaaf128b4f19f5afe423522e6712a732662` and PR #217 merge
`b21640deeffba234ea02425c156d2682a204d289`, are ancestors of the accounted
base.

## Current append-path and binding census

The executable manifest is
`tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml`. Its AST
reconciliation gate fails on an unmanifested or stale ledger append site. PR
#222 added no append site, so the complete current set remains:

| Path and symbol | Receiver | Disposition |
|---|---|---|
| `research_system/authority.py::initialize_authority_control_store` | `ledger` | commandless system bootstrap |
| `research_system/command/service.py::submit` | `self.ledger` | generic and guarded command producer |
| `research_system/command/t2.py::submit_t2` | `service.ledger` | T2 command producer |
| `research_system/evals/executors/control_store.py::execute_s009` | `ledger` | commandless evaluation fixture |
| `research_system/evals/executors/control_store.py::execute_s011` | `ledger` | commandless evaluation fixture |
| `research_system/evals/scenarios.py::recover_writer` | `ledger` | commandless evaluation fixture |

The PR #222 schema universe contains 112 deterministically ordered active
bindings. The canonical rows
`schema_id|schema_version|command_type|event_type|producer_command_type|policy_action_type`
have SHA-256
`4b7a5b1813415f360e12d40341320444fc13334a6cb78690effd0695eb4b2b6a`.

## Current candidate behavior

- One frozen `RegisteredSchema` retains the schema ID/version, source path,
  exact raw bytes, raw-byte SHA-256, and parsed JSON from one read.
- Validation and exact identity resolution return the same record object.
- Parsed schema JSON preserves ordinary `dict`/`list` validator semantics while
  rejecting nested object and array mutation.
- Later source-file mutation cannot change the registered bytes, digest, parsed
  contract, or validation result.
- Duplicate exact schema identities fail registry construction.
- The public generic command path appends an event carrying the exact validated
  schema triple.
- Generic, guarded-release, T2, artefact-authority, and W3 context command
  bindings are included in the deterministic current inventory.
- Direct generic and T2 append attempts without the complete triple fail before
  any batch is committed.

## Historical evidence boundary

No valid pre-06h suite freeze was recorded before producer mechanics landed on
`main`; RM-01 marks it non-reconstructible. Neither the historical candidate nor
this reconciliation fabricates a substitute baseline. The earlier candidate
`6cc5571` remains immutable evidence for its authorized base and was not
rewritten or rebased.

The runtime remains fail-closed by default for missing provenance. No G-RM-8
branch is activated. The dormant position-only replay parameter is not an
admissible grandfather protocol because it is not bound to `store_identity`,
`ledger_fingerprint`, and `max_global_position`.

## Validation

Interpreter: `C:\Users\steph\TDL\.venv\Scripts\python.exe`.

Pytest controls: plugin autoload disabled, repository `addopts` cleared, cache
provider disabled, coverage plugin disabled, and bytecode writes disabled.

- The real public generic append control was watched red before implementation
  on absent `RegisteredSchema.raw_bytes_sha256`, then passed after the
  single-record implementation: **1 passed**.
- Exact identity, immutable nested JSON, duplicate identity, deterministic
  112-binding inventory, complete append census, manifest-node resolution,
  generic/T2 missing-triple rejection, and planted-unmanifested-site controls:
  **9 passed in 7.28 seconds**.
- Final targeted 06h gate: the complete schema-registry module, executable
  manifest/smoke module, and exact generic-command, T2, and ledger provenance
  controls: **55 passed in 185.70 seconds**.
- PR #222 shared-schema public positives for real artefact authority and W3
  context lifecycle: **2 passed in 15.28 seconds**.

The two separately known release-publication failures were run at both the
candidate worktree and an LF-exact, history-bearing clone of the exact parent
`9736c900` (tree `24c95b0`). Both subjects failed identically: the signature
guard expects the stale singular message fragment, and the S-014 known-bad
fixture lacks its declared `mutation_id`. They are parent-baseline failures, not
candidate regressions, and are not counted as green.

## Full-tree memory measurement

Separate cold processes constructed `SchemaRegistry` over all 399 live schemas
under `tracemalloc`, starting tracing immediately before construction:

| Subject | Current traced bytes | Peak traced bytes |
|---|---:|---:|
| Exact parent `9736c900` | 15,128,130 | 15,490,490 |
| Candidate worktree | 15,615,888 | 15,992,105 |
| Delta | +487,758 (+3.22%) | +501,615 (+3.24%) |

This is a bounded Python-allocation measurement for registry construction, not
a process-RSS or production-load claim.

## Exact owner decision still required

Stephen must select exactly one G-RM-8 branch after its required independent
evidence is available:

- **Migrate:** immutable store inventory, content-addressed transformation,
  projection equivalence, repeat-run no-op, drift rejection, and atomic
  owner-approved binding switch.
- **Grandfather:** an attributed decision binding `store_identity`,
  `ledger_fingerprint`, and `max_global_position`, with failure on any pin drift
  or historical-set growth.
- **No prior store:** independent declared-root/store/backup discovery plus
  operator attestation and the planted out-of-first-root negative.
- **Defer:** 06h and C2 remain owner-blocked.

Until one choice is recorded and the selected branch is implemented and
accepted, `artefact.register`, 06i Stage A, and G-RM-14 remain blocked.
