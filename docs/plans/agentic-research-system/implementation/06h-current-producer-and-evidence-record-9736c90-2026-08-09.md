# WP6.1 06h live-main current producer and evidence record

**Record date:** 2026-08-09

**Accounted base:** `9736c900fd4f72e84b2208eeff0dcfb2a2b44106`

**Base tree:** `24c95b02694229976abdb02d701ec39b36865a9e`

**Branch:** `codex/wp6-1-kan95-06h-reconcile-9736c90`

**Candidate commit:** `3c75d3d102d8fe14746b19662005e88c4b776ffa`

**Candidate tree:** `01625ae2e64a90981f0721c9bb7b35bf7d3abe25`

**Post-PR #229 integrated main:** `35f20340a026aafdd4eb17a594eff8a079f6a493`

**Post-PR #229 production candidate:** `4ad065464c5e51f4cc0e4e633af910a548f2c697`

**Historical candidate preserved:** `6cc557198f0fc0f624ffd834643ec2788f8d2711`

**Status:** current-producer and G-RM-8 `GRANDFATHER` construction preserved;
the final post-PR #229 census is reconciled; independent review and owner
acceptance remain open

## Capability truth

C2 remains **INCOMPLETE**. The G-RM-9/current-schema identity, current producer
binding, complete append-path accounting, and selected G-RM-8 exact-prefix
protocol are implemented. The post-PR #229 census is reconciled at production
candidate `4ad0654`. 06h cannot be accepted until:

1. one fresh no-history independent reviewer assesses the complete exact
   subject; and
2. Stephen separately accepts the exact reviewed 06h subject.

This record does not authorize 06i Stage A, author G-RM-14 bytes, authorize
`artefact.register`, commission premature review, or claim acceptance.

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

After PR #229 and the intervening live-main merges were integrated at
`35f2034`, the final census remained exactly 112 bindings with the same digest,
and the AST reconciliation still found exactly the same six append sites. The
exact evidence is recorded in
`06h-post-pr229-reconciliation-evidence-4ad0654-2026-08-09.md`.

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

The runtime remains fail-closed by default for missing provenance. Stephen has
selected G-RM-8 `GRANDFATHER`, whose exact-prefix construction is recorded in
the later decision/evidence files. The position-only replay parameter is not an
admissible grandfather protocol because it is not bound to `store_identity`,
the exact prefix fingerprint and event set, and `max_global_position`.

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
  **9 passed in 7.28 seconds before commit** and **9 passed in 16.15 seconds at
  exact candidate head `3c75d3d`**.
- The complete schema-registry module, executable
  manifest/smoke module, and exact generic-command, T2, and ledger provenance
  controls passed **55 tests in 185.70 seconds before commit** on the content
  committed as `3c75d3d`. The one exact-head repeat exceeded its 300-second
  bound without emitting a terminal pytest summary; no child process survived.
  That aggregate repeat is **unresolved**, not reported green.
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

## Recorded owner decision and remaining gate

Stephen selected G-RM-8 `GRANDFATHER` for lineage `3c75d3d`. The attributed
decision, exact prefix evidence, implementation, and fail-closed controls are
preserved in reachable ancestors and the linked evidence records. The remaining
06h gates are one fresh no-history review of the complete exact subject and
Stephen's separate acceptance of that reviewed subject. Until that acceptance,
`artefact.register`, 06i Stage A, and G-RM-14 remain blocked.
