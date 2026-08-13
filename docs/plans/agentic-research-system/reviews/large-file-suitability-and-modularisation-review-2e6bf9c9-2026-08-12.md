# Adversarial Large-File Suitability and Modularisation Review

**Subject:** the 40 Agentic Research System Python files exceeding 1,000 physical lines
**Mode:** `adversarial-design-review` — implementation-conformance
**Disposition:** `accept_with_required_changes` (one Critical defect must be closed before any
modularisation work begins; the modularisation question itself resolves to *mostly no*)

---

## 1. Reviewed subject and scope

| Item | Value |
|---|---|
| Branch | `main` |
| Commit | `2e6bf9c92e59208c40e55f664fc48d75e481ae04` |
| Tree | `156e3de64f64b53f38901442b079dd5b394507be` |
| Commit date | 2026-08-11 04:12:31 +0100 |
| Subject | "Merge pull request #246 from stephendor/codex/pr245-review-remediation" |
| Local `HEAD` vs `origin/main` | identical; `git rev-list --left-right --count` = `0 0` |
| Working tree | clean over `research_system/`, `tests/`, `.research-system/` (`git status --porcelain` empty); two untracked WP6.6 review `.md` files elsewhere, untouched |

All 40 line counts in the brief were re-derived from `git show origin/main:<path> | wc -l`.
**All 40 match exactly.** No file was mis-stated.

**Governing sources read:** `implementation/01-control-plane-and-replay-plan.md` (the file map that
created this layout), `design/01-system-architecture.md`, `design/02-task-event-and-artifact-schema.md`
(via the pinned oracle), `.research-system/contracts/artefact-authority-interface.v1.yaml`,
`.research-system/contracts/wp6-2-t2-protected-membership.yaml`,
`.research-system/contracts/wp6-2-t2-schema-identities.yaml`.

**Read-only compliance:** no file was edited, no branch created, no Jira touched, no PR comment
posted, no external review triggered. The only writes in this session are this report and three
entries appended to the private research-observer log outside the repository. Four contract tests
were executed read-only (`--no-cov -p no:cacheprovider`); results are quoted verbatim in §4.

**Declared limitation.** The brief asked for the `smallest-complete` skill. It is not installed in
this environment (`~/.claude/skills/`, `.claude/skills/`, and the plugin cache contain no such
skill). Its discipline — minimum viable change, no speculative scope, no compatibility scaffolding —
has been applied as an explicit constraint throughout, but it was not loaded as an authored artifact.
Treat that as a gap in the review's tooling provenance, not a claim.

**Not attempted.** The full pytest suite was not executed; runtime behaviour beyond the four
contract tests below is unverified. Conclusions rest on source structure, contract bindings,
git history, and those four executions.

---

## 2. Executive verdict

**Modularisation is not presently needed.** Thirty of the forty files are correctly sized for what
they own. The line-count screen surfaced one genuine ownership problem, several worthwhile-but-not-yet
boundaries, and — because verification was done against direct evidence rather than against green
checks — one Critical defect that has nothing to do with file size.

Three findings dominate, and none of them is "these files are too big":

1. **The suite gate is off.** `.github/workflows/ci.yml` is `disabled_manually` at GitHub. Its own
   in-file comment designates the unfiltered pytest step as the post-merge composition and
   exact-reference currency signal for `main`. Exactly one CI run has occurred since 2026-07-01
   (2026-07-30, `failure`); since 2026-08-01 the only workflow runs of any kind are `Dependency
   Graph`. A contract gate is failing on a byte-clean `origin/main` right now and nothing reported it.

2. **Layout is already an authority boundary.** `artefact-authority-interface.v1.yaml` binds
   qualified symbols to exact source paths in `research_system/command/service.py` and
   `research_system/cli.py`, and `test_06i_stage_a_candidate.py` enforces those bindings by AST
   (verified passing). Five of the twenty-five test files carry `git_blob_id` +
   `raw_git_blob_sha256` byte pins. **Moving code in these files is a contract amendment, not a
   refactor.** Any modularisation proposal that ignores this is wrong before it starts.

3. **The one existing extraction is the argument against extracting.** `command/t2.py` — a complete
   command family already lifted out of `CommandService` — reaches back through an untyped
   `service: Any` parameter into three *private* `CommandService` methods. It moved lines without
   creating a contract. Repeating that pattern would make the system worse, not better.

**Maximum genuinely justified refactor campaigns: three**, and none may start until (1) is closed.
The brief permits five; three is what the evidence supports. Two of the three are decompositions
*within* existing files, and one is a consolidation that makes a file *larger*.

There is no case here for splitting a file because it exceeds 1,000 lines. There is a case for
fixing a dead gate, typing one seam, and giving the projection layer a single owner.

---

## 3. Complete 40-file ledger

Churn is `git log --since="90 days ago" | wc -l`. Authors is distinct authors over 180 days —
uniformly 1–2, which matters: **there is no concurrent-editor contention to relieve**, so the
standard "big file causes merge conflicts" rationale does not apply anywhere in this set.

### Production (15)

| # | File | Lines | Churn/90d | Capability owned today | Decision |
|---|---|---|---|---|---|
| 1 | `research_system/command/service.py` | 7,183 | **92** | The single public command → durable event → receipt transaction, plus nine per-family preparation validators, the scoped-activation crash-recovery marker protocol, authority resolution, and moved-restore admission | **PRIORITY REFACTOR** |
| 2 | `research_system/store/identity.py` | 3,209 | 15 | Store origin witness, manifest identity, restore-binding transaction state machine, and Windows/POSIX owned-temporary primitives | **EXTRACT LATER** |
| 3 | `research_system/authority.py` | 2,618 | 45 | Two lifecycles: one-time authority control-store bootstrap (L936–1763) and the per-command `LedgerAuthorityGrantResolver` read path (L1764–2618) | **EXTRACT LATER** |
| 4 | `research_system/operations/backups.py` | 2,090 | 12 | `BackupMaterializer` (create/materialize) and restore preflight/admission — opposite directions of one data path | **EXTRACT LATER** |
| 5 | `research_system/cli.py` | 1,991 | 52 | One entry point per public operation: ~217 lines of argparse (`_parser`, L1760–1976) plus ~1,500 lines of handlers, several owning verification semantics found nowhere else | **WATCH** |
| 6 | `research_system/evidence/wp64_real_a8.py` | 1,877 | 7 | Single-purpose fail-closed operator harness for one WP6.4 real-A8 proof; explicitly never initializes a store or authors owner values | **WATCH** |
| 7 | `research_system/command/reducers.py` | 1,803 | 18 | The deterministic replay reducer family (16 `reduce_*` + lifecycle validators). `reduce_task` is 403 lines | **RETAIN** |
| 8 | `research_system/assurance/runner.py` | 1,792 | 9 | Assurance-pack prepare/accept, plus a private git object reader and ~15 validators | **WATCH** |
| 9 | `research_system/schema_registry.py` | 1,406 | 30 | ~980 lines of `_RUNTIME_BINDINGS` declarative data (L121–1100) colocated with a ~350-line resolver | **EXTRACT LATER** |
| 10 | `research_system/projection/replay.py` | 1,255 | 40 | Replay, event-schema validation, hash-chain verification, and `apply_event` (650 lines) which dispatches 16 event families to `reducers.py` but **inlines 4 others** | **EXTRACT LATER** |
| 11 | `research_system/command/t2.py` | 1,205 | 7 | A complete T2 command family: receipt type, semantics validators, reducers, projection, event builder, one entry point | **RETAIN** (see M-1) |
| 12 | `research_system/context/service.py` | 1,122 | 6 | The context-packet lifecycle (request → compile → validate → issue → deliver) behind `Protocol`-typed collaborators | **RETAIN** |
| 13 | `research_system/store/lock.py` | 1,092 | 12 | Composite writer lock with physical directory identity; Windows and POSIX anchors implementing one identity contract | **RETAIN** |
| 14 | `research_system/assurance/external_records.py` | 1,013 | 14 | External assurance record schema catalogue → store → publication authority → receipt | **WATCH** |
| 15 | `research_system/evals/executors/release_tranche.py` | 1,012 | 21 | Three independent fixture executors (`execute_s014/s015/s016`) over one real-lifecycle bootstrap harness | **WATCH** |

### Tests and test-support (25)

`P` = byte-protected: carries `git_blob_id` + `raw_git_blob_sha256` in
`wp6-2-t2-protected-membership.yaml` or a pinned row in `wp6-2-t2-schema-identities.yaml`.
`L/T` = lines per test function.

| # | File | Lines | Tests | L/T | Capability owned today | Decision |
|---|---|---|---|---|---|---|
| 16 | `contracts/test_wp6_3_tdl_private_assurance_pack_contract.py` | 3,833 | 37 | 103 | One contract's conformance campaign; imports only `errors` + `schema_registry` | **WATCH** |
| 17 | `integration/test_wp6_1_c1_readiness_lease.py` | 3,145 | 67 | 46 | C1 readiness/dispatch/attempt/lease/resource-grant over the real `CommandService` seam (117 real-seam references) | **WATCH** |
| 18 | `integration/test_wp6_1_message_lifecycle.py` | 2,805 | 42 | 66 | One message lifecycle end to end | **RETAIN** |
| 19 | `integration/test_gate5_release_tranche.py` | 2,379 | 49 | 48 | **Three unrelated campaigns**: tranche executors S014–S016, restore preflight/registry/moved-restore, supersession (legacy + graph) | **EXTRACT LATER** |
| 20 | `integration/test_wp6_1_task_scope_lifecycle.py` | 2,124 | 24 | 88 | Task/scope revision lifecycle and replay | **RETAIN** |
| 21 | `integration/test_scoped_authority_grant_activation.py` | 1,977 | 26 | 76 | The direct regression suite for the scoped-activation marker protocol | **WATCH** |
| 22 | `integration/test_authority_grant_source.py` | 1,953 | 49 | 39 | Authority grant source and bootstrap provenance | **RETAIN** |
| 23 | `unit/test_wp6_2_live_grader_calibration_protocol.py` `P` | 1,902 | 16 | 118 | Calibration-protocol contract conformance; 78 helpers building mutation probes | **RETAIN** |
| 24 | `unit/test_release_publication.py` | 1,772 | 50 | 35 | Release publication evidence and verification | **RETAIN** |
| 25 | `integration/test_wp6_1_scope_task_authority.py` | 1,764 | 32 | 55 | Scope/task authority binding under lock | **RETAIN** |
| 26 | `integration/test_external_assurance_record_publication.py` | 1,754 | 33 | 53 | External record publication path | **RETAIN** |
| 27 | `contracts/test_w11_contract_materialization.py` | 1,745 | 38 | 45 | W11 portfolio/discovery contract materialization | **RETAIN** |
| 28 | `integration/test_assurance_pack_runner.py` | 1,641 | 30 | 54 | Assurance pack prepare/accept lifecycle | **RETAIN** |
| 29 | `contracts/wp6_1_schema_fact_oracle.py` `P` | 1,583 | 0 | — | The **independent** source-fact oracle; explicitly has no dependency on the resolver, materializer, validator, or generated schemas | **RETAIN** |
| 30 | `contracts/wp6_1_schema_source.py` `P` | 1,555 | 0 | — | Approved git-object access **and** the ~790-line hand-authored derivation model consumed by both producer and validator | **RETAIN** (see M-2) |
| 31 | `unit/test_store.py` | 1,542 | 58 | **26** | Lock, ledger, objects, layout, receipts — the WP1-designated single store test file. Lowest L/T in the set | **WATCH** |
| 32 | `contracts/wp6_2_t2_schema_materializer.py` `P` | 1,373 | 0 | — | T2 schema materializer; contract role `schema_materializer` | **RETAIN** |
| 33 | `integration/test_context_packet_lifecycle.py` | 1,285 | 22 | 58 | Context packet lifecycle through CLI and service | **RETAIN** |
| 34 | `integration/test_wp6_1_c3_completion_review_decision.py` | 1,281 | 13 | 98 | C3 completion/review/decision lifecycle | **RETAIN** |
| 35 | `integration/test_wp6_1_c2_operating_lifecycle.py` | 1,265 | 28 | 45 | C2 operating lifecycle | **RETAIN** |
| 36 | `contracts/test_tdl_private_pack_candidate.py` | 1,243 | 40 | 31 | TDL-private pack candidate conformance | **RETAIN** |
| 37 | `contracts/wp6_1_materialization_validation.py` `P` | 1,212 | 0 | — | Fail-closed validation for reviewable contract artifacts | **RETAIN** (see M-2) |
| 38 | `contracts/test_wp6_2_live_issue_contract.py` | 1,196 | 33 | 36 | Live-issue contract document conformance (no `research_system` imports) | **RETAIN** |
| 39 | `contracts/test_wp6_2_t2_authority_mutations.py` | 1,133 | 37 | 30 | T2 authority mutation attacks **and the producer/validator independence guards** | **RETAIN** |
| 40 | `unit/test_wp6_2_t2_runtime.py` | 1,094 | 18 | 60 | T2 runtime over the real seam | **RETAIN** |

**Ledger totals:** RETAIN 25 · WATCH 9 · EXTRACT LATER 5 · PRIORITY REFACTOR 1 · IMMEDIATE DEFECT 0
*(the Critical below is a live gate failure surfaced during scope verification; it is not a
suitability verdict on any of the 40 files)*.

---

## 4. Findings

### Critical

#### C-1 — The designated post-merge currency gate is administratively disabled, and a contract gate is failing on `main` behind it

**Claim.** `.github/workflows/ci.yml` is `disabled_manually`. The unfiltered pytest step that its own
comment designates as the composition and exact-reference currency signal for `main` has not run
since 2026-07-30, and a contract gate is red on a byte-clean `origin/main`.

**Evidence.**

- `.github/workflows/ci.yml:3-7` — `on: push: branches: [main]` / `pull_request: branches: [main]`.
- `.github/workflows/ci.yml:36-38` — verbatim comment: *"This unfiltered suite is also the post-merge
  composition and exact-reference currency signal on pushes to main. A stale pinned blob or a
  producer/schema composition failure must therefore turn the merge red."*
- `gh api repos/:owner/:repo/actions/workflows` → `CI | disabled_manually | .github/workflows/ci.yml`.
  All other workflows (`Copilot code review`, `Dependabot Updates`, `Dependency Graph`) are `active`.
- `gh run list --workflow=ci.yml --limit 100` → exactly **1** run since 2026-07-01, on 2026-07-30,
  conclusion `failure`. Since 2026-08-01, the only workflow runs on the repository of any kind are
  `Dependency Graph`. `main` received merges through 2026-08-11.
- Executed read-only on the clean tree:
  ```
  tests/research_system/contracts/test_06i_stage_a_candidate.py
  1 failed, 8 passed in 3.70s
  FAILED ...::test_direct_artefact_storage_boundary_is_exact_including_history_and_content_reads
  E  Extra items in the right set:
  E  ('research_system/session_exchange/exchange.py', 'prepare_session_brief', 'write', 'artefact')
  ```
- Root cause of that failure: the artefact-write authority moved from `prepare_session_brief` to
  `record_session_evidence`. `research_system/session_exchange/exchange.py` now contains exactly one
  `store.write("artefact", ...)`, at line 648, inside `record_session_evidence`. Neither the test's
  hard-coded expected set (`test_06i_stage_a_candidate.py:576-624`) nor
  `.research-system/contracts/artefact-authority-interface.v1.yaml` `direct_storage_inventory`
  (L432-440) was updated.
- The test is not deselected, skipped, or `xfail` anywhere in `pyproject.toml` or the workflows.

**Failure scenario.** Any change that breaks a pinned blob, a schema composition, or an interface
binding merges to `main` and stays there. That has already happened once: the interface contract
currently misdescribes where artefact objects are written, and the gate built to catch exactly this
was switched off. The next occurrence has no reason to be benign.

**Direction matters, and limits the severity.** The discovered set is a strict *subset* of the
declared set — the contract over-declares a write path that no longer exists. There is no
*undeclared* artefact write, so this is not an unguarded storage bypass. It is a stale contract plus
a dead gate. Rated Critical for the dead gate, not for the drift.

**Impact.** Operations and evidence integrity. Every "green checks" claim about `main` since
2026-07-30 rests on a workflow that did not execute.

**Disposition.** Fix now, before any other work in this report. Owner decision required on
re-enabling the workflow (why it was disabled is not recorded anywhere I can read, and I will not
speculate).

**Proposed change.** (a) Re-enable the `CI` workflow, or record a dated decision explaining what
replaced it. (b) Reconcile `direct_storage_inventory` and the boundary test's expected set with the
live `exchange.py` — one serial owner, one change. (c) Add a liveness assertion that treats workflow
*state* as part of the gate, not just workflow *content*: a probe over
`gh api repos/:owner/:repo/actions/workflows --jq '.workflows[] | select(.state != "active")'`,
shipped with a negative control proving it fires.

**Affected work packages.** WP6.4 (session exchange), WP6.1 06i (artefact authority interface), and
every acceptance record since 2026-07-30 that cited suite state as evidence.

### Major

#### M-1 — The one existing extraction from `CommandService` reaches into three private methods through an untyped parameter

**Claim.** `command/t2.py` — the sole precedent for extracting a command family — did not create a
narrow contract. It created an unpoliceable private-API dependency edge.

**Evidence.** `research_system/command/t2.py:1012` — `def submit_t2(service: Any, raw_envelope: dict[str, Any]) -> T2Receipt`.
Attribute reach measured across the module: `service.schemas` ×17, `service.receipts` ×13,
`service.ledger` ×2, `service.clock`, `service._submission_lock` (L1019), plus
`service._retire_moved_restore_preflight` and `service._authority_state_validator`. Three of those
are private. `service: Any` means no type checker, no `Protocol`, and no test can detect a signature
change on the `CommandService` side.

**Contrast within the same codebase.** `research_system/context/service.py:21-45` declares
`ContextObjectWriter` and `ContextCommandWriter` as `Protocol`s and depends on nothing private. That
file is 1,122 lines, 6 commits/90d, and is the cleanest module in the set. The pattern that works is
already present and was not used.

**Failure scenario.** A rename or signature change to `CommandService._submission_lock` — a method
inside the highest-churn file in the repository at 92 commits/90d — breaks T2 command submission at
runtime with no static signal. `_retire_moved_restore_preflight` is a restore-lifecycle method; T2
has no restore semantics, so the coupling is not even conceptually justified.

**Impact.** Correctness and change safety. More importantly for this review: it establishes that
extraction from `CommandService`, as practised here, produces worse coupling than colocation.

**Disposition.** Fix now, as the prerequisite for campaign R-3. This is not itself a modularisation.

**Proposed change.** Define `CommandSubmissionHost(Protocol)` in `research_system/command/models.py`
with exactly the members T2 needs, promote `_submission_lock`, `_retire_moved_restore_preflight`, and
`_authority_state_validator` to that protocol's public surface (or supply narrow public wrappers),
and retype `submit_t2(service: CommandSubmissionHost, ...)`. No behaviour change. No file split.

**Affected work packages.** WP6.2 T2; any future WP6.7 consolidation.

#### M-2 — One materialization lane machine-checks producer/validator independence; its sibling holds the same property by convention only

**Claim.** The T2 lane declares artifact roles in contract and enforces the independence edge by AST.
The WP6.1 lane pins the same class of files' bytes but declares no roles and has no guard — and
currently carries the exact import edge T2 forbids.

**Evidence.**

- T2, verified passing:
  `tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py:1078-1102` asserts by AST that
  `wp6_2_t2_schema_materializer` is not in the validator's imports and
  `wp6_2_t2_authority_validation` is not in the materializer's imports. Roles are declared in
  `.research-system/contracts/wp6-2-t2-schema-identities.yaml` as `artifact_role: independent_oracle`
  and `artifact_role: schema_materializer`.
- WP6.1: `tests/research_system/contracts/wp6_1_schema_materializer.py:17` — the producer imports
  `wp6_1_materialization_validation` (the validator). Both sides then derive from the same module:
  `wp6_1_materialization_validation.py:19` imports `wp6_1_schema_source`, and both call
  `schema_source.resolve_operation_specs`, `grouped_rows`, `source_rows`, `COMMAND_ROOT_NAMES`,
  `EVENT_ROOT_NAMES`.
- `wp6_1_schema_source.py` is not merely approved-bytes access. Beyond `approved_annex_bytes`
  (L287) and `approved_fact_annex_bytes` (L300), it contains the derivation model:
  `resolve_operation_specs` (L1467), `_resolver_for` (L1432), `schema_identity` (L403),
  `command_root_spec`/`event_root_spec` (L1506/L1531), and ~790 lines of hand-authored per-operation
  field specs (`_field`, `_object`, `_d`, `_message_d`, L641–1432).
- The WP6.1 rows in `wp6-2-t2-protected-membership.yaml:647-670` carry `git_blob_id` and
  `raw_git_blob_sha256` but **no `artifact_role`** field.

**Countervailing evidence — this is a missing control, not a present mis-certification.**
`wp6_1_schema_fact_oracle.py:1-6` states and honours genuine independence ("deliberately has no
dependency on the WP6.1 resolver, materializer, validator, generated schemas, or proposal companion
schema"), pins W2/W8/06d by revision and blob, and independently authors the cardinalities
(`owner_rows: 104`, `generated_schema_identities: 173`, …). `wp6_1_schema_expectations.py:15` imports
only `approved_fact_annex_bytes` from `schema_source` — the approved input, not the derivation. So
the expected side is currently independent. **Nothing is presently mis-certified.**

**Failure scenario.** The property that keeps this honest is unwritten. A future edit adding
`from ...wp6_1_schema_source import resolve_operation_specs` to `wp6_1_schema_expectations.py` would
silently make the conformance test certify the producer against itself, pass every existing check,
and pass review — because the reviewer would be looking at a file that already imports from
`schema_source` legitimately.

**Impact.** Assurance validity, latent. The project's own failure record names self-attestation as
one of three mechanisms behind nearly every recorded failure.

**Disposition.** Fix now — it is cheap and it is a guard, not a refactor. Note the constraint: the
five WP6.1 files are byte-pinned, so the guard must live in a *new* test file, not inside them.

**Proposed change.** Add `artifact_role` to the WP6.1 protected-membership rows and generate the AST
independence assertion from the declared roles rather than hand-listing per lane, so one rule covers
both lanes. Ship the negative control that adds the forbidden import to a temp copy and proves the
assertion fires.

**Affected work packages.** WP6.1 stage 2 acceptance; WP6.2 T2.

#### M-3 — Projection ownership is split: `apply_event` inlines four event families while dispatching sixteen

**Claim.** No single file answers "where does event type X change state?"

**Evidence.** `research_system/projection/replay.py:378-1027` — `apply_event` is 650 lines. Sixteen
event families dispatch to `command/reducers.py` (`reduce_task`, `reduce_scope`, `reduce_message`,
`reduce_lease`, `reduce_attempt`, `reduce_dispatch`, `reduce_blocker`, `reduce_checkpoint`,
`reduce_operation`, `reduce_recovery`, `reduce_review`, `reduce_resource`, `reduce_backup`,
`reduce_restore_verification`, `reduce_artefact`, `reduce_decision`, `reduce_rule_evaluation`).
Four families are reduced inline instead: authority grants (`AuthorityRootInitialized`,
`AuthorityGrantActivated`, `AuthorityGrantRevoked` — ~180 lines), context packets (~90 lines),
evidence deletion, and `ReleaseGateDecisionPublished`.

**Failure scenario.** A change to authority-grant projection semantics is made in `replay.py` while
a reviewer checking "did the reducers change?" reads `reducers.py` and sees nothing. The two files
co-change 33 times in 92 `service.py` commits, so this is not hypothetical drift risk — it is the
observed pattern.

**Impact.** Replay determinism review surface. Both files are correct today; the problem is that
correctness cannot be checked from one place.

**Disposition.** Defer to campaign R-4, after R-2 and R-3. This is a **consolidation** — it makes
`reducers.py` larger (~2,200 lines) and `replay.py` smaller. Recommending it is the opposite of what
a line-count-driven review would produce, which is the point.

**Proposed change.** Move the four inlined families into `reducers.py` as `reduce_authority_grant`,
`reduce_context_packet`, `reduce_evidence_deletion`, `reduce_release_decision`, leaving `apply_event`
as validate → order → dispatch → verify-hash-chain. Then the invariant "every state transition lives
in `reducers.py`" becomes true and mechanically checkable.

#### M-4 — `CommandService._prepare_c1_command` is 711 lines covering five distinct sub-capabilities with no internal sectioning

**Claim.** The largest preparation method in the largest file is a flat conditional chain, not a
dispatcher.

**Evidence.** `research_system/command/service.py:2598-3309`. Within it: task readiness (L2642+),
dispatch issue/deliver/acknowledge/expire/withdraw (L2656–2794), attempt create/claim/start
(L2793+, L3174+, L3217+), resource grant request/release (L2841+, L3262+), and execution lease
claim/renew/release/expire/revoke/heartbeat (L2862–3049). Each is a top-level
`if command_type == ...` in one function body. Siblings for comparison:
`_prepare_c2_command` 567 lines, `_prepare_c3_command` 356, `_prepare_artefact_authority_command` 318.

**Failure scenario.** A lease-expiry edit must be reviewed inside a 711-line function whose other
610 lines concern dispatch and attempts. At 92 commits/90d on this file, that review context is
re-entered roughly every third day.

**Impact.** Review surface and defect probability on the highest-churn code in the repository.

**Disposition.** Campaign R-3 — decompose **in place** into private methods on `CommandService`. No
file split; no contract touched; no new import edges.

**Why not extract.** Extraction would require passing `snapshot`, `observed_version`, the rejection
constructor, and the authority validator across a module boundary — reproducing M-1 exactly.

#### M-5 — Git blob identity is independently reimplemented in at least six production modules

**Claim.** A cryptographic identity function that must agree across the assurance surface has six
production implementations and seven more in tests.

**Evidence.** `research_system/artefacts/authority.py:128`, `assurance/external_records.py:190`,
`assurance/pack_loader.py:137`, `assurance/runner.py:316` (`_git_blob_id`),
`evidence/wp64_real_a8.py:1710` (`_git_blob_sha1`), `methods/pack.py:202` (`_git_blob_sha1`). Test-side:
`wp6_1_schema_source.py:222`, `wp6_1_materialization_validation.py:221`,
`wp6_1_stage2_acceptance_validation.py:148`, `test_wp6_3_...:250` and `:254`,
`test_wp6_1_contract_materialization_mutations.py:44`,
`test_wp6_2_live_grader_calibration_protocol.py:88`. Signatures already differ
(`git_blob_id(data)` vs `git_blob_id(repo_root, data)` vs
`_git_blob_id_without_filters(data)`), which shows the semantics have already forked over
checkout filters.

**Failure scenario.** Two of these disagree on CRLF or filter handling; a pinned blob validates
against one implementation and fails against another. Byte pins are the mechanism protecting five of
the forty files in this review.

**Impact.** Assurance validity across the whole protected-bytes surface.

**Disposition.** Defer to campaign R-5 with a prerequisite: first prove whether the six agree.
Consolidating divergent implementations without establishing which is correct would propagate a bug.

### Minor

- **m-1 — `schema_registry.py` is 70% declarative data.** `_RUNTIME_BINDINGS` spans L121–1100 of
  1,406. "Add a binding" (mechanical, frequent — 30 commits/90d) and "change resolution semantics"
  (rare, dangerous) share one file. Extracting the tuple to `research_system/schema_bindings.py`
  leaves a ~420-line resolver and changes no public seam. Verified: no contract byte-pins this file.
  Low risk, low urgency.
- **m-2 — the ARS suite has essentially no shared fixture layer.** Seven files in the entire
  `tests/research_system/` tree use `@pytest.fixture`, and there is no `tests/research_system/conftest.py`
  (only `tests/conftest.py` and the 872-line `tests/research_system/factories.py`). This is the
  single largest structural driver of test file size. **It is not, however, causing duplication**:
  cross-file helper-name collision across the 25 files peaks at 2 (`_task_definition`,
  `_scope_create_payload`, `_command_id`, `_load_yaml`). Recording it as an observation, not a defect.
- **m-3 — `test_gate5_release_tranche.py` holds three unrelated campaigns.** Name-prefix clustering:
  `real_command_service` ×7, `restore_preflight_*`/`restore_registry_*`/`moved_restore_*` ×8,
  `legacy_supersession_*`/`supersession_*` ×7, `s016_*` executor tests. See R-6 (not ranked).
- **m-4 — `replay_control_plane` has no production consumer at this commit.** Defined at
  `command/reducers.py:1630`; the only callers are `tests/research_system/factories.py:20,250`.
  Untracked WP6.6 review documents describe production callers in `discovery/runtime.py`, but
  `research_system/discovery/` does not exist at `2e6bf9c9` — those consumers are in unmerged PRs
  #247/#248. Worth knowing before anyone treats it as dead code.
- **m-5 — the WP1 file map was never amended.**
  `implementation/01-control-plane-and-replay-plan.md:17-53` fixes the layout that produced every
  oversized production file. Five subsequent work packages added capability into those exact files
  with no plan restating or amending the map.

---

## 5. Cross-file dependency and conflict matrix

Derived from `git log --since="90 days ago"` over `research_system/command/service.py` (92 commits),
counting files changed in the same commits.

| Co-changed with `service.py` | Commits | Share | Consequence |
|---|---|---|---|
| `research_system/authority.py` | 37 | 40% | Same seam |
| `research_system/projection/replay.py` | 33 | 36% | Same seam |
| `tests/research_system/factories.py` | 26 | 28% | Shared test harness |
| `research_system/store/ledger.py` | 26 | 28% | Same seam |
| `research_system/cli.py` | 26 | 28% | Same seam |
| `research_system/schema_registry.py` | 18 | 20% | Same seam |
| `research_system/command/reducers.py` | 18 | 20% | Same seam |
| `research_system/command/lifecycle.py` | 12 | 13% | Same seam |
| `tests/.../test_gate5_release_tranche.py` | 18 | 20% | Downstream |
| `tests/.../test_store.py`, `test_replay.py`, `test_schema_registry.py` | 17–18 each | ~19% | Downstream |

**Conclusion.** `service.py`, `authority.py`, `replay.py`, `reducers.py`, `ledger.py`,
`schema_registry.py`, and `cli.py` are **one shared seam**, not seven independent files. Every
campaign in §6 touches it.

**Serial owner requirement — mandatory.** All campaigns R-2 through R-5 must run **strictly serially
under one named owner**. No two may be in flight together, and none may be delegated to a parallel
worktree. This is not a caution; the co-change data makes concurrent work on this seam a guaranteed
conflict.

**Contract constraints that bind before any of them.**

| Constraint | Binds | Enforced by | Verified |
|---|---|---|---|
| `artefact-authority-interface.v1.yaml` `transitive_root_bindings` — `source_path` + `qualified_symbol` + `required_calls` | `cli.py::_eval_publish_release`, `::_publication_evidence`, `::stored_evidence_resolver`, `::_eval_release`; `service.py::CommandService._prepare_release_publication` | `test_06i_stage_a_candidate.py:558` (AST) | **PASSED** (29.7s) |
| `artefact-authority-interface.v1.yaml` `direct_storage_inventory` | `service.py::CommandService._ensure_artefact_materialized` | `test_06i_..._direct_artefact_storage_boundary...` | **FAILED** — see C-1 |
| `artefact-authority-interface.v1.yaml` `dynamic_object_store_kind_exclusions` | `service.py::CommandService._reconcile_scoped_activation_marker` (read + `rollback_new_revision`), `::_reconcile_scoped_activation_receipt` | `test_06i_..._object_store_boundary_analysis...` | **PASSED** |
| `wp6-2-t2-protected-membership.yaml` byte pins | 5 of the 25 test files (#23, #29, #30, #32, #37) | `test_wp6_2_t2_authority_mutations.py::test_protected_membership_recomputes_exact_live_set` | **PASSED** |
| T2 role independence | `wp6_2_t2_schema_materializer.py` ↔ `wp6_2_t2_authority_validation.py` | `..._expected_side_has_no_materializer_dependency` | **PASSED** |

The third row is decisive and easy to miss: **the scoped-activation marker methods — otherwise the
single best extraction candidate in `service.py` — are contract-pinned by qualified symbol at that
path.** Moving them out of `CommandService` is an authority-boundary change requiring a contract
amendment and re-review of the artefact-authority interface. That is why no campaign below proposes
extracting them.

---

## 6. Ranked, dependency-aware campaign list

Three campaigns are justified. R-1 is a blocking precondition, not a modularisation. R-5 and R-6 are
listed for completeness and explicitly **not** recommended for scheduling yet.

| Rank | Campaign | Depends on | Scope | Why it reduces demonstrated risk |
|---|---|---|---|---|
| **R-1** | **Restore the gate.** Re-enable `CI` (owner decision) or record what replaced it; reconcile `direct_storage_inventory` + the boundary test's expected set with the live `exchange.py`; add the workflow-state liveness probe with a negative control. | — | ~1 contract file, 1 test file, 1 workflow | Closes C-1. **Nothing below may start until this is done** — without a running suite, no campaign can prove it changed nothing. |
| **R-2** | **Type the T2 submission seam.** `CommandSubmissionHost(Protocol)` in `command/models.py`; retype `submit_t2`; promote or wrap the three private methods. | R-1 | `command/models.py`, `command/t2.py`, `command/service.py` | Closes M-1. Prerequisite for R-3: without it, any `service.py` decomposition can silently break T2. |
| **R-3** | **Decompose `_prepare_c1_command` in place.** Five private methods on `CommandService` (task readiness, dispatch, attempt, resource grant, lease). No file split, no contract change, no new imports. | R-2 | `command/service.py` only | Closes M-4 on the highest-churn code in the repo. Preserves every contract pin by construction. |
| **R-4** | **Give the projection layer one owner.** Move the four inlined event families from `apply_event` into `reducers.py`. Consolidation: `reducers.py` grows, `replay.py` shrinks. | R-3 | `projection/replay.py`, `command/reducers.py` | Closes M-3. Makes "all state transitions live in `reducers.py`" true and checkable. |
| *R-5* | *Reconcile git blob identity.* **Prerequisite first:** prove whether the six production implementations agree on filters and CRLF. Only then consolidate. | R-4 + evidence | 6 production modules | Addresses M-5. **Do not schedule until the agreement question is answered** — consolidating divergent implementations would propagate whichever is wrong. |
| *R-6* | *Split `test_gate5_release_tranche.py` by campaign.* Move the restore-preflight and supersession clusters to the files already owning those capabilities. | R-1 | 3 test files | Addresses m-3. Lowest value in the set; listed so it is not rediscovered as novel. |

**Deliberately excluded.** `schema_registry.py` binding-table extraction (m-1) is real and cheap, but
that file co-changes with `service.py` 18 times in 92 commits — it sits on the serial seam and is not
worth a slot ahead of R-2 through R-4. Revisit after R-4.

### Migration sequence for R-3 (the only campaign proposing structural change to a pinned file)

1. Verify R-1 and R-2 complete and the suite is green **and observed running**.
2. Extract each `if command_type == ...` block into a private method, one block per commit, with no
   signature or behaviour change. Each commit must leave `_prepare_c1_command` calling the new method
   in the same position with the same arguments.
3. After each commit: run `test_wp6_1_c1_readiness_lease.py` (67 tests — the direct regression),
   `test_wp6_1_scope_task_authority.py`, and the three `test_06i_stage_a_candidate.py` boundary tests.
4. Positive validation: all 67 C1 tests pass unchanged, no test file edited.
5. Negative validation: deliberately invert one preparation guard in a throwaway commit and confirm
   the corresponding C1 test fails. If it does not, the seam was not covered and the extraction stops.
6. Confirm `test_06i_stage_a_candidate.py` still passes — `_prepare_c1_command` is not itself pinned,
   but `CommandService._ensure_artefact_materialized` and the reconcile methods are, and any
   accidental movement of those is caught here.

**Alternatives considered and rejected for R-3.** Extracting to `command/c1_preparation.py` would
require passing `snapshot`, `observed_version`, `self._rejected`, and `self._authority_state_validator`
across a module boundary — reproducing M-1 exactly. Private helper functions at module scope in
`service.py` would lose access to `self.ledger`/`self.objects` and force the same parameter passing
with none of the benefit. In-place private methods are the smallest change that resolves the finding.

---

## 7. Explicit non-recommendations — files that look large but must stay intact

These are the ones a line-count screen would flag and a reviewer should refuse.

- **`command/reducers.py` (1,803).** The deterministic replay authority. Every reducer must move
  together when an event's shape changes; splitting by stream kind creates N files that always change
  in lockstep. R-4 makes it *larger* on purpose.
- **`store/lock.py` (1,092).** Lock ordering, anchor lifetime, and the final fence are one atomic
  acquisition protocol. The Windows and POSIX branches implement a single identity contract; splitting
  them lets one platform's semantics drift silently — the exact failure the physical-identity design
  exists to prevent.
- **`context/service.py` (1,122).** One lifecycle, `Protocol`-typed seams, 6 commits/90d. This is the
  model the rest of the system should copy, not a candidate for change.
- **`command/t2.py` (1,205).** Coherent command family. Its problem (M-1) is its *seam*, not its size.
  Splitting it further would multiply the private-API edges.
- **The five byte-protected test files** (#23 `test_wp6_2_live_grader_calibration_protocol.py`,
  #29 `wp6_1_schema_fact_oracle.py`, #30 `wp6_1_schema_source.py`,
  #32 `wp6_2_t2_schema_materializer.py`, #37 `wp6_1_materialization_validation.py`).
  Any split changes their bytes, breaks the `git_blob_id`/`raw_git_blob_sha256` pins, and requires a
  contract amendment plus owner re-acceptance of the stage-1/stage-2 acceptance records. **Contract-blocked
  regardless of any coherence judgement.**
- **`test_wp6_1_c1_readiness_lease.py` (3,145).** 67 tests at 46 lines each over the real
  `CommandService` seam (117 real-seam references, real `replay`, real `factories`). It is large
  because the C1 lifecycle is large. There is no synthetic harness here to remove.
- **`test_store.py` (1,542).** 58 tests at 26 lines — the *densest* file in the set. It covers five
  store modules because the WP1 file map designated one store test file. Splitting it now buys nothing.

**The general non-recommendation.** No file in this set should be split to reduce its line count.
Every boundary proposed above is justified by an ownership, authority, or review-surface argument that
would hold at half the size.

---

## 8. Residual risks and required checks before any later edit

**Residual risks.**

1. **Unverified suite state.** I ran four contract tests, not the suite. With CI disabled since
   2026-07-30, the true state of `main` is unknown. There may be further failures behind C-1. **Run
   the full suite before treating any conclusion here as a baseline.**
2. **Unknown reason for the CI disable.** Nothing in the repository records why. If it was disabled
   for a reason (cost, a known-flaky job, a runner problem), re-enabling it without addressing that
   reason will fail again. Owner input required.
3. **M-2 is latent, not active.** The WP6.1 expected side is independent *today*. If the guard is not
   added, that fact must be re-verified by hand at every future review of that lane — which is exactly
   the "no re-validation trigger" failure mode the project's record names.
4. **M-5 agreement is unproven.** I established that six implementations exist and that their
   signatures have diverged. I did **not** establish whether they produce identical output. That is the
   prerequisite, and until it is answered the duplication could be masking an active defect.
5. **Repowise index staleness.** The index is at `d3259a15`; 36 files differ at `2e6bf9c9`, including
   `service.py`, `cli.py`, `authority.py`, `replay.py`, `reducers.py`, and `schema_registry.py`. All
   structural facts in this report were derived from direct reads and `git show`, not from the index —
   but any follow-up using Repowise tooling on these files should resync first.

**Required checks before any edit to a file in this set.**

| Check | Command | Gates |
|---|---|---|
| Interface symbol bindings | `pytest tests/research_system/contracts/test_06i_stage_a_candidate.py --no-cov -p no:cacheprovider` | `cli.py` and `service.py` symbol-at-path pins. **Currently 1 failed / 8 passed — must be green before it can serve as a baseline.** |
| Byte-protection closure | `pytest tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py -k protected_membership --no-cov` | The five pinned test files |
| Producer/validator independence | `pytest ...::test_protected_membership_expected_side_has_no_materializer_dependency --no-cov` | T2 lane only — WP6.1 has no equivalent (M-2) |
| Direct C1 regression | `pytest tests/research_system/integration/test_wp6_1_c1_readiness_lease.py --no-cov` | R-3 |
| Activation-marker regression | `pytest tests/research_system/integration/test_scoped_authority_grant_activation.py --no-cov` | Any touch to the scoped-activation protocol |
| Replay determinism | `pytest tests/research_system/unit/test_replay.py tests/research_system/unit/test_store.py --no-cov` | R-4 |
| Workflow liveness | `gh api repos/:owner/:repo/actions/workflows --jq '.workflows[] \| select(.state != "active")'` | C-1 — **does not exist yet; proposed** |

**Negative-control requirement.** Every gate added by R-1 or M-2 ships with a control proving it can
fail, in the same change. A gate nobody has watched fail is the condition that produced C-1.

---

## 9. Decision audit

| Decision under review | Disposition |
|---|---|
| WP1 file map fixes `service.py`/`reducers.py`/`replay.py`/`schema_registry.py`/`lock.py`/`cli.py` | **Amend.** Superseded in practice by WP2–WP6; never restated. Now load-bearing for contract pins (m-5). |
| `submit_t2` extracted from `CommandService` with `service: Any` | **Amend** — M-1. Keep the extraction; fix the seam. |
| Scoped-activation marker protocol lives inside `CommandService` | **Keep.** Contract-pinned by qualified symbol; moving it is an authority change with no proportionate benefit. |
| Four event families reduced inline in `apply_event` | **Amend** — M-3, via R-4. |
| `wp6_1_schema_source` as shared derivation authority for producer and validator | **Keep with an added guard** — M-2. The design is defensible; the missing control is not. |
| T2 role declaration + AST independence guard | **Keep and generalise.** This is the correct pattern; extend it to WP6.1. |
| Byte-pinning contract artifacts including test-support modules | **Keep.** It is working — the closure test passes and it correctly blocks casual refactoring of assurance code. |
| `context/service.py` Protocol-typed seams | **Keep and propagate.** The model for R-2. |
| CI as the post-merge currency signal | **Owner decision required** — C-1. Currently asserted in a comment and not true in fact. |

---

## 10. Change log

No repository files were created, edited, or deleted by this review other than this report at
`docs/plans/agentic-research-system/reviews/large-file-suitability-and-modularisation-review-2e6bf9c9-2026-08-12.md`.
No contract, test, workflow, or source file was modified — including the stale
`direct_storage_inventory` entry behind C-1, which is left in place deliberately as evidence.

Three entries were appended to the private research-observer log at
`~/.claude/skill-observations/log.md` (outside the repository):
`2026-08-12-ci-workflow-disabled-manually` (GATE),
`2026-08-12-wp61-lane-lacks-t2-independence-guard` (GATE),
`2026-08-12-file-map-frozen-since-wp1` (PROCESS).

Tests executed, read-only, `--no-cov -p no:cacheprovider`:

```
test_06i_stage_a_candidate.py::test_consumer_inventory_is_exactly_closed_over_policy_and_production_dispatch  PASSED
test_wp6_2_t2_authority_mutations.py::test_protected_membership_expected_side_has_no_materializer_dependency  PASSED
test_wp6_2_t2_authority_mutations.py::test_protected_membership_recomputes_exact_live_set                      PASSED
                                                                                       3 passed in 29.74s

test_06i_stage_a_candidate.py::test_object_store_boundary_analysis_catches_alias_method_and_typed_wrapper_bypasses  PASSED
test_06i_stage_a_candidate.py::test_direct_artefact_storage_boundary_is_exact_including_history_and_content_reads   FAILED
tests/research_system/contracts/test_06i_stage_a_candidate.py (whole file)              1 failed, 8 passed in 3.70s
```
