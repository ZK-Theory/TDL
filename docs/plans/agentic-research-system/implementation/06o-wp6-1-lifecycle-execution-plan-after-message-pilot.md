# 06o — WP6.1 lifecycle execution plan after the Message pilot

| Field | Value |
|---|---|
| Status | **Current WP6.1 execution-control plan; C1 integrated 2026-08-05.** WP6.1 remains incomplete and this record does not start C2. |
| Date | 2026-08-05 revision of the 2026-08-03 post-Message plan |
| Original evidence base | `4f8b9b857bab1a7553af5e6ea3ef170608e7e18e` / tree `e765b75c458ebf194dd80cef6c66d11e5360e6a7` |
| Integration revision base | `1a5d8c7514fafc5c28f8624bc60259ddd00e026f` (`main` when this revision began) |
| Prior design authority | `0e842969c770811edf5c81dcd7e4f7a647e050ad:docs/plans/agentic-research-system/implementation/06m-wp6-lifecycle-family-pilot-design.md` |
| Workflow | One capability campaign at a time; C1 is integrated, followed by owner-started C2, C3, and recovery-gated R1 |

This document is the authoritative execution-control plan for the remaining WP6.1
capability and incorporates P-047 Research Methods obligations. It records C1's
accepted integration and directs Jira work decomposition and closure evidence, but
does not by itself start C2 or authorize later runtime code, schemas, providers,
merges, Gate 6, dispatch, or research execution. The
accepted 06a plan itself authorizes no implementation
(`docs/plans/agentic-research-system/implementation/06a-wp6-1-runtime-task-lifecycle-plan.md:4-15`).
Stephen's 2026-08-05 completion and merge instruction applied to C1. A later campaign
still requires an explicit owner instruction naming that campaign.

## 1. Recommendation and exact pilot outcome

### 1.1 Proposed proceed/regroup decision

**Recommendation: proceed with the ten-family semantic decomposition, but revise the
execution mechanics before P2.** Message demonstrated that one coherent vertical, one
pull request, and one serial owner for central seams can deliver exact binding,
authority, append, reducer, replay, projection, receipt, and negative-case closure
without a new framework. It also demonstrated that the original packet was not
candidate-ready: its durable residue topology, retry ordering, dependency closure,
and derived-field contract were incomplete.

The recommendation was subsequently used to start C1, the admission-to-running
campaign represented by KAN-72 and PR #212. Stephen confirmed that CodeRabbit found
no further issue at exact PR head
`f4dbfef6366ee5d77059c3b94177ad56de9f057c` and authorized integration. GitHub merged
that reviewed head without squash or rebase as
`23dcfaaaf128b4f19f5afe423522e6712a732662` on 2026-08-05. The reviewed head is an
ancestor of that merge. The tracked KAN-65 handoff established that KAN-65 owns the
remaining WP6.1 catalogue
(`docs/plans/agentic-research-system/handoffs/33-wp6-gate6-completion-manager-exact-state-2026-07-30.md:5`,
`:27-29`).

### 1.2 Exact accepted and integrated evidence

| Role | Exact identity | Meaning |
|---|---|---|
| Accepted candidate | `2c3618197bcfc7a839c81c615db6d9052ef74239` | Exact Message implementation subject accepted by a fresh independent review |
| Review commit | `6bdc9190a5dbb04c30d8f35907cf6b09128f85c6` | Adds the fifth durable Message review record only |
| Integration commit | `3e2a10e0ef113b2bf38f2804feda1103515afe5f` | Composes the accepted review head with then-current `main` |
| PR #209 merge / current `main` | `4f8b9b857bab1a7553af5e6ea3ef170608e7e18e` | Merge commit preserving candidate, review, and integration ancestry |
| Integration and merge tree | `e765b75c458ebf194dd80cef6c66d11e5360e6a7` | `3e2a10e` and `4f8b9b8` have identical trees |

The integrated first-parent delta is exactly 13 repository paths: eight
implementation/test paths and five review records. The executable census is exactly
13 Message rows, with four command/event pairs. The final review verdict is
`accept_exact_subject`, with no unresolved Critical or Major finding
(`docs/plans/agentic-research-system/reviews/wp6-1-message-lifecycle-2c361819-review-2026-08-03.md:1-30`,
`:308-336`). That verdict is bound to the exact candidate and protected identities; it
is not owner acceptance, later-family dispatch authority, Jira completion, or a Gate
6 decision (`.../wp6-1-message-lifecycle-2c361819-review-2026-08-03.md:431-455`).

The protected command tree remains
`9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` (87 files) and the protected event tree
remains `154ffc4bdde82fe903718734687e7a62797b1f69` (86 files). All eight Message raw
schema hashes remain unchanged:

- `PublishMessage`: `14c0c66afc05dce4d4e90ff28c1828e68f8ca0471f740fdf5d4ed4cd818c9f3c`;
- `MessagePublished`: `f9a4d7d685ee9cbb8c299791469078d45ad022989bcfcd8456e18ba6a6de5f3f`;
- `RecordMessageDelivery`: `9f2acb3223b1a9098750364b4401dbfad91cd1de0a0e787123a19cfb2e67e828`;
- `MessageDelivered`: `7c2fabe331a8745695345431e349637caf6eb79f8cab5938caa4caf53e329388`;
- `AcknowledgeMessage`: `3b8218236c5d0afddff30c0e936362cfbdc916a192f9e449d5cfef914f2cb92d`;
- `MessageAcknowledged`: `576f5d5369b11b355d06cc7faaaddd5ebcae1094d72cf03e5712cd96170886be`;
- `RecordMessageDeliveryFailure`: `afe3393eefe58291b4e41b3b1d496f49e89dd73c19022ef6d94f1a62d4e44a89`;
- `MessageDeliveryFailed`: `0632bd0bc4c4ecaeea753735d4094c472233cc582da590cd29c986ecec0db2e5`.

The final raw-object evidence is recorded at
`docs/plans/agentic-research-system/reviews/wp6-1-message-lifecycle-2c361819-review-2026-08-03.md:337-365`.

### 1.3 C1 exact integration evidence

PR #212 integrated the complete 23-row admission-to-running campaign at reviewed head
`f4dbfef6366ee5d77059c3b94177ad56de9f057c`, merge
`23dcfaaaf128b4f19f5afe423522e6712a732662`, and merge tree
`5abb396a06f8b0d0f884d45e985d194b6c887619`. The exact-head CodeRabbit status was
`success` (`Review completed`), after which Stephen explicitly authorized the merge.

On the assembled merge head, four vertical proofs passed across ResourceGrant
materialization, admission to running, heartbeat-backed renewal, and resource release;
seven C1 CLI/census selections also passed. The reviewed head remains an ancestor of
`origin/main`, and the protected command/event trees remain
`9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` and
`154ffc4bdde82fe903718734687e7a62797b1f69`. Four unrelated CLI history cases exposed
by a broader selection use a helper unchanged from merge first parent `525a595d`; they
are a separately reported current-main baseline defect and did not prompt C1 rework.

## 2. Execution retrospective

### 2.1 What worked

1. **One coherent family and one PR worked.** Binding, producer, authority,
   idempotency, reducer, replay/projection, and decisive tests stayed in one exact
   semantic subject rather than becoming later cleanup layers.
2. **Central serial ownership worked.** Shared seams were composed once, and the
   integration commit preserved both current-main activation-marker cleanup and the
   Message retry guards. The final ordering remains visible at
   `research_system/command/service.py:1015-1045`, `:1540-1604`, and `:3176-3216`.
3. **The architecture stayed bounded.** The pilot added no lifecycle DSL, provider,
   migration, persistence layer, generic event-sourcing framework, bulk schema
   activation, or protected schema-byte change.
4. **Fresh exact-subject governance worked.** Every semantic candidate had a fresh
   independent review, no producer self-review was used, findings were preserved in
   durable records, and the dedicated integration module reached 103 passing tests at
   the accepted candidate (`.../wp6-1-message-lifecycle-2c361819-review-2026-08-03.md:221-273`).
   The repository does not contain a separate post-integration test-execution record,
   so this plan does not invent one.

### 2.2 Five semantic subjects and the rework they exposed

| Exact implementation subject | Independent result | What changed in the evidence |
|---|---|---|
| `b3531092814efbd2ff3f1fb094dd929032642d1e` | `rework_required`: 2 Critical, 3 Major, 1 Minor | C-01 early retry bypassed project/current authority/scoped-index/history; C-02 allowed recognized Message events under the generic schema; M-01 regressed four shared non-Message retries; M-02 aliased caller payload into cached accepted state; M-03 lacked the 13-row common-axis matrix; m-01 dropped the supplied adapter registry (`.../wp6-1-message-lifecycle-b353109-review-2026-08-02.md:34-154`). |
| `b4000015c65c132da272f0ca6122060a17d8c0af` | `rework_required` | Five findings closed, but C-01 remained: an orphan accepted receipt with neither scoped index nor canonical event allowed an append and index publication before conflict (`.../wp6-1-message-lifecycle-b400001-rereview-2026-08-02.md:34-85`). |
| `62a87fd46642ac6c9c176058949bd2d43075a326` | `rework_required` | The orphan guard closed C-01. PB-M-01 then exposed missing-index repair for a changed command ID: original acceptance was returned and the index was reconstructed (`.../wp6-1-message-lifecycle-62a87fd-review-2026-08-02.md:39-101`). |
| `5c77239a4a30d9021605695ff3fa351c4f3e77b9` | `rework_required` | PB-M-01 closed. PB-M-02 exposed the complementary order: with event and scoped index retained but standalone receipt absent, repair occurred before the changed-command conflict (`.../wp6-1-message-lifecycle-5c77239-review-2026-08-03.md:51-92`). |
| `2c3618197bcfc7a839c81c615db6d9052ef74239` | `accept_exact_subject` | PB-M-02 closed by canonical validation, retained-receipt integrity, command identity, then repair. Parent evidence was honestly `1 failed, 1 passed`: the changed behavior was red, while integrity precedence was already a preservation-green control (`.../wp6-1-message-lifecycle-2c361819-review-2026-08-03.md:84-141`, `:183-220`). |

The result was successful, but success took five semantic implementation subjects.
Fresh subjects and reviews were sound governance; the repeated rediscovery of adjacent
residue states was avoidable rework.

### 2.3 Root cause and revised mechanics

The original brief did not provide a complete durable residue/retry topology or an
exact source-ordering matrix. It named ordinary retry, missing index, and selected
history failures, but did not take the Cartesian product across canonical event,
standalone receipt, scoped index, incoming command identity, and retained/tampered
evidence. As a result, each fix revealed the complementary durable state.

Dependency and path closure was also initially incomplete. Two mandatory registries —
`research_system/authority.py::_SCOPED_COMMAND_SUBJECT_KINDS` and
`research_system/command/lifecycle.py::EXACT_LIFECYCLE_BINDINGS` — were outside the
initial literal path allowlist, and the exact preimages for derived fields such as
Message `content_sha256` and acknowledgement `source_position` were not frozen. Future
packets must trace a positive path before freezing their writable envelope.

Finally, the manager's persistent goal included merge and Jira closure across an
owner-controlled CodeRabbit wait. Because Stephen alone triggers and monitors that
service, automatic continuation repeatedly reloaded the large campaign and performed
unchanged state audits. A stable external wait is now a task boundary: the family goal
ends at a durable PR-ready handoff; a fresh lightweight closer begins only after
Stephen reports review completion.

## 3. Honest efficiency telemetry

These figures are prompt-supplied `ccusage`/session-audit evidence. Literal searches
found no copy in the repository or five review records, so they are not presented as
repository-derived telemetry.

| Matched session evidence | Total tokens | Cache read | Uncached input | Output | Recorded model evidence |
|---|---:|---:|---:|---:|---|
| Manager session | 186,619,035 | 183,382,016 | 2,920,615 | 316,404 | Only `gpt-5.6-sol` recorded |
| Read-only Sol session 1 | 7,222,357 | — | — | — | Sol |
| Read-only Sol session 2 | 5,225,550 | — | — | — | Sol |
| Read-only Sol session 3 | 5,337,836 | — | — | — | Sol |
| Design session | 12,922,831 | — | — | — | Sol design context |

The manager arithmetic closes exactly:
`183,382,016 + 2,920,615 + 316,404 = 186,619,035`. The matched-session lower bound is
exactly:

`186,619,035 + 7,222,357 + 5,225,550 + 5,337,836 + 12,922,831 = 217,327,609`.

That is a **lower bound of 217,327,609 total tokens**, not a whole-pilot total. It
excludes other producer and reviewer sessions. There is no evidence of Spark, Luna,
or Terra use in the matched sessions. The honest conclusion is: **the pilot was
successful, but not token-efficient**. The cache-heavy manager total also shows why a
long-lived goal waiting on an external owner gate is the wrong unit of continuation.

## 4. Goal and session topology

1. Reject one single Sol Ultra completion goal spanning every remaining WP6.1 family.
2. Use a thin portfolio coordinator to hold only exact current state, dependency
   ordering, protected identities, owner decisions, and the next slice.
3. Create one fresh completion goal per dependency-ordered delivery slice and PR
   subject. If a second semantic remediation is required, stop for rescope and start a
   new exact subject in a fresh task.
4. End each family/slice goal at a **PR-ready durable handoff**: exact candidate,
   parent/tree, paths, tests, protected identities, independent review record, PR
   state if separately authorized, and one explicit CodeRabbit unblock condition. Do
   not keep it alive through Stephen's review-service wait or merge.
5. After Stephen reports review completion, use a fresh lightweight integration
   closer. It re-resolves the current PR head, the review's commit identity, current
   `main`, protected trees, merge-tree composition, and authorization before any
   separately permitted integration action.
6. Rotate tasks only after actual compaction makes the current task an unreliable
   continuation surface. Durable plans, reviews, and handoffs are state; conversation
   is not.
7. Give every exact semantic subject a fresh independent review context with no
   author/reviewer history. Review acceptance remains evidence for a separate owner
   decision, never a substitute for it.

## 5. Current-main interface contract

All citations below resolve at planning base
`4f8b9b857bab1a7553af5e6ea3ef170608e7e18e`. A later dispatcher must re-open these
lines at its exact base; a moved or semantically changed seam is not accepted by this
snapshot.

| Seam | Verified current behavior | Current repository citation |
|---|---|---|
| Schema catalogue and activation | `SchemaRegistry(root, *, active_bindings=())` loads every schema by exact ID/version, retains raw bytes/path/SHA-256, and separately builds trusted discriminator maps. Runtime activation is the hard-coded binding set, not file presence or a dynamic registration API. | `research_system/schema_registry.py:56-76`, `:308-384`, `:575-585` |
| Current active lifecycle set | Scope/Task creation, amendment, supersession and the four Message command/event pairs are active. `SupersedeTask -> TaskSuperseded` and producer-qualified Message bindings are explicit. | `research_system/schema_registry.py:79-183` |
| Binding lookup and exact validation | `command_binding`, producer-qualified `event_binding`, and `validate_active` select and validate exact registered identities; inactive bindings fail. | `research_system/schema_registry.py:456-512` |
| Authority subject registry | Lifecycle authority activation recognizes the exact scoped subject kind for Scope, Task, and Message command types. | `research_system/authority.py:153-164` |
| Fresh lifecycle authority | `resolve_lifecycle_command` derives actor class and exact command authority from one fresh authority projection; it does not accept caller-provided cached authority state. | `research_system/authority.py:2126-2189` |
| Public command submission | The decorated public surface is `CommandService.submit(self, envelope)`. The underlying implementation declares guarded release/scoped-authority continuations, strips caller provenance, selects the trusted binding from `command_type`, and requires the envelope ID/version to match it. | `research_system/store/ledger.py:89-142`; `research_system/command/service.py:897-944` |
| Submission ordering | Under one submission lock: fresh lifecycle authority precedes scoped recovery; committed matching precedes the Message orphan guard; preparation precedes event build; append precedes accepted receipt/index publication. | `research_system/command/service.py:958-1045`, `:1116-1143`, `:1221-1258` |
| Scoped durable recovery | Reconciliation replays canonical history, checks the exact accepted event and authority evidence, checks any retained standalone receipt, applies Message identity, and only then repairs a missing receipt. | `research_system/command/service.py:1540-1604`, `:2157-2197` |
| Committed-match recovery | `_matching_committed(self, command, view, *, command_schema)` scopes by actor, grant, command type, idempotency key, and exact schema identity. Message reconstruction rejects a changed command ID before same-submission repair. | `research_system/command/service.py:3176-3216` |
| Event construction | `_build_event(..., *, command_schema)` deep-copies Message payloads, selects producer-specific event bindings, and records exact command schema ID/version/SHA and canonical payload hash. | `research_system/command/service.py:3235-3241`, `:3293-3309`, `:3350-3373` |
| Ledger append | `EventLedger.append(proposed_events, *, snapshot=None)` checks snapshot fingerprint and persisted tail, allocates ledger-owned identities/order, validates command provenance and producer binding, validates pre-hash/final event, fsyncs, then atomically publishes one JSONL batch. | `research_system/store/ledger.py:326-368`, `:393-518`, `:521-547` |
| Exact lifecycle provenance | `EXACT_LIFECYCLE_BINDINGS` independently joins event schema, event type, producer command, and command schema. Recognized Message events cannot use the generic schema. | `research_system/command/lifecycle.py:9-67`, `:70-107` |
| Online reducers | Current reducers implement exact Task, Scope, and Message state. Message preserves canonical content hash/source position; Task supersession preserves revision history and compatibility checks. | `research_system/command/reducers.py:105-161`, `:195-386`, `:507-581` |
| Replay reducer routing | Current control-plane and projection replay route only the presently supported lifecycle events plus existing special cases; remaining P2-P8 families require explicit reducer/projection closure rather than assuming generic routing. | `research_system/command/reducers.py:584-624`; `research_system/projection/replay.py:495-515`, `:533-636` |
| Replay and projection rebuild | `replay(...)` validates schema/provenance, major version, position/hash chain, stream/transaction order, then applies reducers. `rebuild_projection(...)` writes canonical replay state through a sibling temporary file and `os.replace`. | `research_system/projection/replay.py:653-773`, `:776-795` |
| SupersedeTask compatibility | Exact submission validates graph currentness, terminal/cycle state, immutable source/replacement objects, same-Task ordering, rich/generic compatibility, and continuing-consumer equality. Replay independently validates compatibility and preserves history. | `research_system/command/service.py:2851-2978`, `:2980-2992`; `research_system/command/reducers.py:105-161`, `:295-379` |

### 5.1 Positive-path closure that every packet must repeat

For one representative command, trace and cite all of:

`accepted schema bytes -> active command binding -> scoped subject-kind registry ->
fresh authority resolution -> command preparation -> event construction ->
EventLedger.append -> exact lifecycle binding -> reducer -> replay -> projection
rebuild -> receipt/index recovery`.

The current Message path exercises each seam above. The exact derived-field preimages
are not conventions: `command_payload_hash` is the canonical command payload;
`MessagePublished.content_sha256` is the canonical published payload hash; and
acknowledgement `source_position` is the original `MessagePublished.global_position`
(`research_system/command/reducers.py:507-563`).

### 5.2 Interface-unverified blockers

- Persistent production wiring for `message_adapter_registry` is not present in the
  current CLI constructor; delivery/failure adapter discovery outside explicit
  constructor injection is **interface-unverified**
  (`research_system/command/service.py:349-393`, `research_system/cli.py:146-164`).
  Provider automation remains deferred, so this does not authorize adding it inside
  P2-P8. Any slice that unexpectedly depends on live adapter discovery must stop.
- P6's 06i plan requires separate Stage A/Stage B decisions and appears to require a
  minimum `ResolveDecision` path before the design's P7 Decision slice. Resolution of
  that ordering conflict is **interface-unverified** and a P6 dispatch blocker
  (`docs/plans/agentic-research-system/implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md:9-16`,
  `:53-92`, `:225-247`).

No other named live interface in this plan remains unverified at the planning base.

## 6. Mandatory candidate-readiness artifacts before first independent review

A producer attestation is not evidence. Before review dispatch, the candidate must
contain or be accompanied by executable artifacts/tests for every item below.

1. **Positive-path dependency/path closure.** One exact command traced from protected
   schema through activation/authority, producer, append, reducer, replay, and
   projection. Every consulted registry and shared caller is either writable in the
   packet or certified unchanged by exact blob/test evidence.
2. **Derived-field preimage table.** For every hash, position, version, actor, subject,
   linkage, and receipt field, name the authoritative source value, canonicalization,
   allocation point, and independent negative.
3. **Row-to-command/event/reducer/projection census.** Literal accepted row IDs, exact
   commands/events, discriminants, reducer targets, projection selectors, and
   applicability of every common axis; no expectations generated from runtime
   registrations.
4. **Authority variant matrix.** Missing, wrong kind, wrong subject, wrong actor,
   wrong project, expired, not-yet-effective, revoked, changed schema identity/hash,
   and stale authority, with no mutation through the public seam.
5. **Durable residue topology Cartesian matrix.** Vary independently:
   canonical event absent/present/tampered; standalone receipt absent/present/
   mismatching; scoped index absent/present/tampered; incoming command ID identical/
   changed; and history/schema valid/tampered. Classify every cell as exact return,
   permitted repair, typed conflict, or integrity failure.
6. **Explicit source ordering.** Freeze and test, as applicable:
   current authority and canonical history -> retained-artifact integrity -> incoming
   command identity -> permitted repair -> append/publication. If a family needs a
   different order, that difference requires Sol adjudication before code.
7. **No-mutation snapshot.** Compare ledger files/tail/batches/versions, standalone
   receipts, scoped indexes, replay/history, projection, authority store/projection,
   and locks/markers for every rejection or integrity failure.
8. **Parent-baseline classification.** Mark each new control before parent execution
   as `defect-demonstrating red` or `preservation/characterization green`. Require red
   only for changed behavior and green at parent/candidate for preserved behavior.
9. **Shared-caller regression selection.** Enumerate public callers, registries,
   wrappers, restore/replay roots, factories, and exact unchanged controls affected by
   every central helper edit.
10. **Current-main merge-tree composition.** Before review, recompute the candidate's
    merge base and non-mutating merge tree against live `main`, resolve every semantic
    overlap in an integration plan, and name the exact integration regressions. An
    automatic textual merge is not semantic evidence.

An independent review is not dispatchable while any artifact above is absent or
labelled by producer assertion only.

## 7. Authoritative delivery campaigns and semantic coverage map

The accepted catalogue contains 104 unique rows. The fixed pre-C1 baseline was 19
active rows (the original six Scope/Task rows and the 13 Message rows) and 85 allocated
rows. C1 has now integrated all 23 rows in its coherent campaign, so the current
executable census is `104 = 42 active + 62 remaining`. The remaining semantic-family
partition is:

`P2 15 + P3 0 + P4 2 + P5 16 + P6 9 + P7 18 + P8 2 = 62`.

The machine catalogue records 104 normalized rows and 182 expanded edges
(`.research-system/contracts/wp6-1-owner-source-catalogue.yaml:4-17`, `:75-76`), and
the accepted row catalogue is the authority for identities
(`docs/plans/agentic-research-system/implementation/06d-wp6-1-owner-source-catalogue.md:215-335`).
No row is duplicated below.

The fixed pre-C1 delivery allocation remains:

`C1 23 + C2 28 + C3 32 + R1 2 = 85`.

After C1 integration, the outstanding delivery campaigns are
`C2 28 + C3 32 + R1 2 = 62`.

These totals must never be added to the P2-P8 totals. P2-P8 describe *what semantic
family owns each row*; C1/C2/C3/R1 describe *which coherent capability campaign
delivers it*. Their exact intersection is:

| Delivery campaign | P2 | P3 | P4 | P5 | P6 | P7 | P8 | Total | Jira |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| C1 admission to running | 2 | 9 | 9 | 3 | 0 | 0 | 0 | 23 | KAN-72 |
| C2 operating lifecycle | 8 | 0 | 2 | 16 | 1 | 1 | 0 | 28 | KAN-73 |
| C3 completion, evidence, review and decision | 7 | 0 | 0 | 0 | 8 | 17 | 0 | 32 | KAN-74 |
| R1 backup/restore evidence | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | KAN-102 |
| **Semantic totals** | **17** | **9** | **11** | **19** | **9** | **18** | **2** | **85** | KAN-75 closes only after all campaigns and horizontal gates |

### 7.1 Literal campaign census

The following sets are normative. The C1 candidate census test was built from this
allocation; later campaigns must reuse these identities rather than reconstructing
their own convenient totals.

- **C1 (23):** `task.request_readiness`, `task.approve_readiness`,
  `task.claim_start`; `dispatch.issue`, `dispatch.deliver`,
  `dispatch.acknowledge`, `dispatch.claim`, `dispatch.expire_issued`,
  `dispatch.expire_delivered`, `dispatch.expire_acknowledged`,
  `dispatch.withdraw_issued`; `lease.activate`, `lease.renew`, `lease.release`,
  `lease.expire`, `lease.revoke`; `attempt.create`, `attempt.claim`,
  `attempt.start`; `operator.request_resource_grant`,
  `operator.claim_execution_lease`, `operator.record_heartbeat`,
  `operator.release_resources`.
- **C2 (28):** `task.block`, `task.request_input`, `task.pause`,
  `task.submit_review`, `task.resume`, `task.cancel`; `dispatch.fulfil`,
  `dispatch.withdraw_claimed`; `attempt.complete`, `attempt.fail`,
  `attempt.partial`, `attempt.pause`, `attempt.resume`, `attempt.request_stop`,
  `attempt.abandon`, `attempt.supersede`, `attempt.retry`; `checkpoint.record`;
  `blocker.record`, `blocker.resolve`; `artefact.register`; `review.request`;
  `operator.request_pause`, `operator.confirm_pause`, `operator.request_stop`,
  `operator.confirm_stop`, `operator.request_resume`,
  `operator.quarantine_orphan`.
- **C3 (32):** `scope.complete`; `task.accept`, `task.reject`,
  `task.close_partial`, `task.reopen_partial`, `task.reopen_rejected`,
  `task.reopen_cancelled`; `artefact.availability`,
  `artefact.regenerability`, `artefact.integrity`,
  `artefact.structural_validation`, `artefact.scientific_review`,
  `artefact.use_authority`, `artefact.supersede`,
  `operator.adopt_late_artefact`; `review.assign`, `review.start`,
  `review.record_verdict`, `review.request_changes`, `review.satisfy`,
  `review.satisfy_after_changes`, `review.withdraw`, `review.supersede`;
  `decision.propose`, `decision.request_review`, `decision.resolve`,
  `decision.reject`, `decision.expire`, `decision.supersede`, `rule.evaluate`,
  `decision.amend`, `correction.record`.
- **R1 (2):** `operator.create_backup`, `operator.verify_restore`.

C1's literal 23-row set is the campaign boundary, not an assertion that all 23 rows
were newly implemented by PR #212. It contains the complete public-path closure that
now works together: readiness; resource grant and lease; dispatch issue, delivery,
acknowledgement and atomic claim; and Attempt create, claim and start. Its campaign
census test preserves the original `23/28/32/2` allocation. The accepted integration
moves those 23 rows from `remaining` to `active`; KAN-71 records the resulting
`104 = 42 active + 62 remaining` census from executable public behavior rather than
changed-file or passing-test counts.

### 7.2 Jira and P-047 control mapping

| Jira job | Plan responsibility | Effect on 104-row arithmetic |
|---|---|---|
| KAN-71 | Authoritative row-by-row executable census and arithmetic control | Counts every row once; closes no row by itself |
| KAN-72 | C1's integrated 23-row admission-to-running campaign | Done after accepted PR #212 integration and KAN-71 census reconciliation |
| KAN-73 | C2's 28-row operating-lifecycle campaign | Same rule |
| KAN-74 | C3's 32-row completion/evidence/review/decision campaign | Same rule |
| KAN-102 | R1's two recovery-evidence rows | Same rule; owner/WP6.4 recovery gate applies |
| KAN-95 | 06h schema currency plus RM-01 append-path completeness | Horizontal final-candidate gate; adds no catalogue row |
| KAN-96 | 06i artefact authority and consumer firewall | Governs the nine P6 rows already counted across C2/C3; adds no second set of nine |
| KAN-97 | 06j W3 context-packet lifecycle and resolver | Separate nine-command W3 obligation outside the 104-row catalogue; must alter neither the fixed `104/19/85` baseline nor current `104/42/62` census |
| KAN-75 | Final integrated WP6.1 capability proof | May close only after KAN-71–74, KAN-95–97 and KAN-102 are complete with exact evidence |

### 7.3 Common campaign rules

- Start only from an owner-named exact current-main SHA, reverified at dispatch.
- One coherent completion goal per C1/C2/C3/R1 capability campaign. Internal packets,
  commits, tests, or review findings are evidence inside that campaign, never separate
  Jira-complete deliverables. One serial owner owns all central seams; leaf workers
  never edit them concurrently.
- Deliver bindings, producer, authority/state checks, declared append set, reducer,
  replay/projection, receipts, decisive negatives, and compatibility together.
- Every PR changes fewer than 100 paths; target at most 90. A lower slice-specific cap
  controls where stated.
- Use a fresh independent exact-subject review at the complete campaign candidate.
  Remediation validates still-valid findings at the new exact head; it does not restart
  the whole plan/review cycle or declare a repaired mechanic to be campaign completion.
  The campaign goal ends at the PR-ready handoff before Stephen's CodeRabbit wait.
- A proposed second semantic remediation, protected-byte defect, new generic
  abstraction, unowned shared path, missing dependency, or interface-unverified seam
  is a stop and owner-rescope event.

### 7.4 P2 — Readiness: remaining Scope + Task + Blocker

**Rows (17 inactive):** `scope.complete`; `task.request_readiness`,
`task.approve_readiness`, `task.block`, `task.request_input`, `task.pause`,
`task.submit_review`, `task.resume`, `task.accept`, `task.reject`,
`task.close_partial`, `task.cancel`, `task.reopen_partial`,
`task.reopen_rejected`, `task.reopen_cancelled`; `blocker.record`,
`blocker.resolve`.

`task.supersede` is already active and is not an eighteenth row. P2 must carry it as a
compatibility touchback with three control groups: (1) preserve generic same-Task
higher-revision compatibility and reject stale/currentness violations; (2) reject
rich/generic or task-type/provenance-incompatible replacements; and (3) reject
continuing-consumer drift. The repository handoff describes four manifestations — it
counts stale misclassification separately — so the stale reason/control must remain
explicit rather than disappearing into the three-group shorthand
(`docs/plans/agentic-research-system/handoffs/33-wp6-gate6-completion-manager-exact-state-2026-07-30.md:19-29`).

- **Dependencies:** owner accepts/revises this proposal and records `proceed`; exact
  current main; current Scope/Task/Message bindings and protected identities intact.
- **Model:** Terra Max by default; Terra Ultra if readiness/Partial authority or
  Task/Blocker ordering is not fully frozen. Sol Ultra adjudicates any ambiguity.
- **Central seam owner:** one owner for schema bindings, scoped subject kinds,
  lifecycle provenance, `CommandService`, reducers, replay/projection, receipts, and
  shared factories. `EventLedger` is read-only unless a contract-first failure proves
  a missing accepted capability.
- **Leaf work:** Luna Max may own the single-stream `ScopeCompleted` or Blocker leaf
  after interfaces freeze. Spark may add only frozen literal row matrices, fixture
  rows, and protected path/hash assertions in 1-3 paths.
- **Tests:** all 17 row positives; readiness separation; unresolved blocker/input;
  Partial evidence; three reopen discriminants; Task/Blocker non-substitution; the
  four SupersedeTask manifestations; authority/retry/residue/no-mutation axes; replay
  and projection equivalence; shared callers.
- **Review:** fresh Sol Ultra review of the exact 17-row subject plus inherited
  SupersedeTask controls.
- **PR budget:** target 12-20 paths; ceiling 28; global hard limit remains `<100`.
- **Stops:** any row/authority ambiguity, attempt to count `task.supersede` twice,
  Task command mutating Blocker directly, regression of generic history, new
  framework, or missing dependency/path closure.

### 7.5 P3 — Lease and resource ownership

**Rows (9):** `lease.activate`, `lease.renew`, `lease.release`, `lease.expire`,
`lease.revoke`; `operator.request_resource_grant`,
`operator.claim_execution_lease`, `operator.record_heartbeat`,
`operator.release_resources`.

- **Dependencies:** accepted P2 readiness state and exact Task revision semantics.
- **Model:** Terra Max/Ultra for the central state machine; Sol Ultra only for
  unresolved authority or ownership adjudication.
- **Central seam owner:** one serial owner for binding/authority/service/ledger seam,
  Lease/Resource reducers, replay/projection, and shared lock/receipt fixtures.
- **Leaf work:** Luna Max may implement a frozen single-stream heartbeat or resource
  release leaf. Spark may materialize literal resource fixture tables or protected
  assertions only after semantics freeze.
- **Tests:** single live holder; exact Task/Dispatch/Attempt/resource joins; interval,
  renewal, heartbeat, expiry/revocation, release-by-owner; authority and durable retry
  matrices; no hidden Task/Dispatch writes; replay rejects overlapping/broken
  ownership.
- **Review:** fresh Sol Ultra exact-subject review, including shared lock and receipt
  callers.
- **PR budget:** target 12-20; ceiling 28.
- **Stops:** overlapping holder semantics unresolved, heartbeat treated as renewal,
  provider/credential dependency, new lock abstraction, or an unowned shared seam.

### 7.6 P4 — Dispatch and atomic ClaimDispatch

**Rows (11):** `task.claim_start`; `dispatch.issue`, `dispatch.deliver`,
`dispatch.acknowledge`, `dispatch.claim`, `dispatch.fulfil`,
`dispatch.expire_issued`, `dispatch.expire_delivered`,
`dispatch.expire_acknowledged`, `dispatch.withdraw_issued`,
`dispatch.withdraw_claimed`.

- **Dependencies:** accepted P2 and P3; composite-lock correction is an ancestor of
  the dispatch base; exact Task/Lease joins are frozen.
- **Model:** Sol Ultra for the atomicity design and implementation subject. This is not
  a Spark or Luna central task.
- **Central seam owner:** one owner owns `ClaimDispatch`, the declared two-stream write
  set, composite lock, `EventLedger.append`, both reducers, replay, projection, and
  receipts. Keep ordered `[DispatchClaimed, TaskClaimStarted]` under that one owner;
  never split Task and Dispatch ownership.
- **Leaf work:** Luna Max may handle a frozen single-stream expiry/withdrawal
  discriminant after the atomic interface is fixed. Spark may add literal
  discriminant/ordering fixtures only.
- **Tests:** exact write-set membership and order; both expected stream versions plus
  global tail; all-or-nothing append; receipt binds both events; half-append,
  reversed/swapped/extra/missing member, stale Task/Dispatch/Lease, changed retry, and
  concurrency races; replay applies the whole batch or fails closed.
- **Review:** fresh Sol Ultra exact-subject review plus explicit integration-seam
  review.
- **PR budget:** target 14-24; ceiling 32.
- **Stops:** any compensating second command, split owner, unproven multi-stream
  atomicity, lock-seam drift, or proposed generic transaction framework.

### 7.7 P5 — Attempt, checkpoint, and operator control excluding recovery-gated rows

**Rows (19):** `attempt.create`, `attempt.claim`, `attempt.start`,
`attempt.complete`, `attempt.fail`, `attempt.partial`, `attempt.pause`,
`attempt.resume`, `attempt.request_stop`, `attempt.abandon`,
`attempt.supersede`, `attempt.retry`; `checkpoint.record`;
`operator.request_pause`, `operator.confirm_pause`, `operator.request_stop`,
`operator.confirm_stop`, `operator.request_resume`, `operator.quarantine_orphan`.

- **Dependencies:** accepted P3 lease ownership and P4 claim/Task-start atomicity.
- **Model:** Terra Ultra for the central implementation; Sol Ultra for any unresolved
  request/confirmation separation or recovery-boundary question.
- **Central seam owner:** one serial owner for Attempt/checkpoint/operator bindings,
  service ordering, reducers, replay/projection, lease/heartbeat joins, receipts, and
  shared factories.
- **Leaf work:** Luna Max may own one frozen single-stream Attempt transition. Spark
  may add exact fixture matrices or path/hash assertions after freeze.
- **Tests:** current claim/lease before start; complete/fail/Partial terminal
  divergence; pause/stop request-confirm separation; resume only after confirmed
  pause; checkpoint ancestry/monotonicity; retry/supersession lineage; live-owner
  quarantine rejection; late-completion races; residue/authority/no-mutation/replay.
- **Review:** fresh Sol Ultra exact-subject review.
- **PR budget:** target 16-28; ceiling 36.
- **Stops:** either backup/restore row appears, live recovery/cutover is needed,
  requester can self-confirm contrary to accepted authority, or one owner cannot close
  the full replay surface.

### 7.8 P6 — Artefact authority and consumer firewall

**Rows (9):** `artefact.register`, `artefact.availability`,
`artefact.regenerability`, `artefact.integrity`,
`artefact.structural_validation`, `artefact.scientific_review`,
`artefact.use_authority`, `artefact.supersede`, `operator.adopt_late_artefact`.

KAN-96 and 06i govern these exact nine rows. `artefact.register` is delivered in C2;
the remaining eight are delivered in C3. KAN-96 is therefore a horizontal authority
and consumer-closure obligation over counted campaign rows, not another nine rows.

- **Dependencies:** accepted P5 Attempt/Artefact references; the 06i Stage A/B owner
  gates and the P6/P7 `ResolveDecision` ordering conflict are explicitly resolved at
  an exact base before dispatch.
- **Model:** Sol Ultra for authority, exact-byte, and consumer-firewall closure.
- **Central seam owner:** one owner owns producer, authority/reducer/replay seams and
  every direct/transitive consumer found from CLI/rederivation roots and registries.
- **Leaf work:** Luna Max may implement a frozen evidence-dimension leaf after the
  consumer contract is fixed. Spark may add only literal consumer census fixtures,
  frozen evidence tables, and protected assertions.
- **Tests:** exact manifest bytes and supersession; six evidence dimensions remain
  non-substitutable; no producer self-attestation; missing/stale authority fails
  closed; every real consumer root rejects before route/grant/lease/provider effects;
  late adoption is owner-governed; replay preserves old accepted bytes; full caller
  inventory and residue/no-mutation matrix.
- **Review:** fresh Sol Ultra exact-subject authority and caller-closure review.
- **PR budget:** target `<=90`; hard stop at 99 changed paths. If authority semantics
  cannot stay intact below 100, stop for architectural/owner replan rather than split
  the firewall arbitrarily.
- **Stops:** unresolved 06i/P7 ordering, incomplete caller closure, protected-byte
  reopening, new authority abstraction without two-family evidence, or path count
  reaching 100.

### 7.9 P7 — Review plus Decision/rule/correction

**Rows (18):** `review.request`, `review.assign`, `review.start`,
`review.record_verdict`, `review.request_changes`, `review.satisfy`,
`review.satisfy_after_changes`, `review.withdraw`, `review.supersede`;
`decision.propose`, `decision.request_review`, `decision.resolve`,
`decision.reject`, `decision.expire`, `decision.supersede`, `rule.evaluate`,
`decision.amend`, `correction.record`.

- **Dependencies:** accepted P6 evidence and Artefact authority subjects; any P6
  ordering decision is incorporated explicitly rather than assumed.
- **Model:** Sol Ultra for Review/Decision separation, correction history, and owner
  authority.
- **Central seam owner:** one owner integrates both families while preserving their
  distinct subject kinds, reducers, projections, and authority. A review verdict must
  never resolve a Decision or substitute for owner acceptance.
- **Leaf work:** Luna Max may own a frozen single-stream Review leaf. Spark may add
  literal review/decision matrices or protected path/hash assertions only.
- **Tests:** proposer/reviewer/owner separation; exact subject revision and evidence;
  both satisfaction discriminants; verdict/change/withdraw/supersede races; rule
  evaluation cannot act as Decision; correction appends without rewriting original
  history; amendment/supersession lineage; authority/residue/no-mutation/replay.
- **Review:** fresh Sol Ultra exact-subject review, with original finding meanings and
  all governed sibling rows dispositioned.
- **PR budget:** target 18-32; ceiling 40.
- **Stops:** any review/Decision substitution, correction deletes or rewrites an
  event, owner decision inferred from review/PR/Jira, or authority separation remains
  ambiguous.

### 7.10 P8 — Backup/restore rows

**Rows (2):** `operator.create_backup`, `operator.verify_restore`.

- **Dependencies:** a separate Stephen-owned WP6.4 recovery-state-machine decision
  and a current exact accepted base. The older recovery candidate is not imported
  merely because it exists.
- **Model:** Sol Ultra for recovery boundary, source provenance, store identity, and
  cutover/non-cutover adjudication.
- **Central seam owner:** one owner for backup/restore command/event bindings,
  project-store identity, recovery reducer, replay/projection, and every restore
  preflight/consumer seam.
- **Leaf work:** Luna or Spark only after the owner decision freezes semantics; Spark
  may then add literal two-row matrices or protected assertions, never recovery logic.
- **Tests:** exact backup chain and source-store identity; witness/provenance joins;
  VerifyRestore remains evidence rather than live restore/cutover; wrong source,
  store, chain, schema, snapshot, endpoint authority, or tampered history fails before
  writer authorization and leaves all stores/locks unchanged.
- **Review:** fresh Sol Ultra exact-subject review against the owner-selected base.
- **PR budget:** target 10-20; ceiling 28.
- **Stops:** absent owner decision/base, implicit absorption of a historical WP6.4
  candidate, live restore/cutover, provider/external action, or unresolved store
  identity. P8 is currently **not dispatchable**.

## 8. Model routing decision

If the only choice is one all-family Sol Ultra goal versus separate family/slice Sol
Ultra goals, choose **separate goals**. The better route is hybrid:

| Work | Recommended model |
|---|---|
| Portfolio architecture, dependency reconciliation, P4/P6/P7/P8 ambiguity, hard finding adjudication, every independent exact-subject review | Sol Ultra |
| Known-pattern central implementation for P2/P3/P5 after interfaces freeze | Terra Max or Terra Ultra |
| Bounded single-stream leaf with frozen authority/state/replay semantics | Luna Max |
| Mechanical 1-3-path packet after semantic freeze: literal row matrix, frozen fixture table, protected hash/path assertion | Spark |

Spark must never activate bindings, change authority/state/reducer/replay/concurrency,
decide a protected identity, operate a recovery boundary, edit a central semantic
seam, or review an exact subject. Message could have used Spark for the literal
13-row matrix after semantic freeze. Spark was unsuitable for every defect the pilot
actually found: authority bypass, replay provenance downgrade, shared retry
regression, mutable evidence aliasing, and durable recovery ordering.

Model routing does not grant write or decision authority. Each packet still carries
its exact base, paths, owner, tests, review boundary, and stop conditions.

## 9. Prompt templates

### 9.1 Family/slice goal dispatch envelope

```text
Workflow: standalone; phase: deliver. One fresh completion goal.
Deliverable: <P# / exact rows> as one PR-ready semantic subject.
Exact base/branch/root: <SHA> / <pre-created branch> / <authorized worktree>.
Verify cwd, detached/branch identity, HEAD, upstream, ancestry, status, live main,
protected 87+86 trees, and current interface citations before writing.
Owned paths: <literal closed list>. Central seam owner: <one owner>.
Forbidden: protected schemas/catalogues/contracts/decisions, provider/external action,
Jira, merge, CodeRabbit polling, new generic abstraction, or rows outside the packet.
Required executable artifacts: positive-path closure, preimage/census/authority/residue
matrices, source ordering, no-mutation snapshot, parent-red/preservation-green labels,
shared-caller regressions, and current-main merge-tree composition.
Validation: exact new nodes -> changed-behavior regressions -> broader tier only on a
named trigger. Fresh Sol Ultra exact-subject review, no author history.
Goal ends at durable PR-ready handoff before Stephen's external-review wait.
Stop on any ambiguity, protected drift, second semantic remediation, cap breach, or
unowned/interface-unverified seam.
```

### 9.2 Spark mechanical subpacket

```text
Model: Spark. Semantics are frozen by <owner artifact/commit>.
Base/branch/root: <exact values>. Allowed paths: exactly <1-3 paths>.
Mechanical change only: <literal rows / frozen fixture table / hash-path assertions>.
Copy exact IDs/expected values from <authority>; do not infer or generate authority.
Forbidden: bindings, CommandService, EventLedger, authority, reducers, replay,
projection, concurrency, protected bytes/identities, recovery, review, or new helpers.
Run <exact static/test commands>. Stop on any semantic choice or path expansion and
return the ambiguity to the central owner. Do not review or attest completeness.
```

### 9.3 Fresh exact-subject review

```text
Fresh independent Sol Ultra review; no author history and no remediation.
Resolve exact candidate, parent, tree, branch/root, changed paths, protected trees and
raw hashes. Read the governing plan, row census, candidate-readiness artifacts, and
all earlier immutable findings by original meaning.
Verify public positive path, authority variants, full residue Cartesian matrix,
source ordering, no-mutation axes, parent-red versus preservation-green evidence,
shared callers, and current-main merge-tree composition.
Write one durable review record and return exactly accept_exact_subject or
rework_required with severity-ranked findings. Review acceptance is not owner
acceptance, PR/merge/Jira authority, CodeRabbit action, or later-family dispatch.
```

### 9.4 Post-CodeRabbit integration closer

```text
Fresh lightweight closer; start only after Stephen supplies review-completion notice
and separately authorizes the requested integration action. Do not trigger or poll
CodeRabbit.
Re-fetch and compare PR head, latest CodeRabbit review commit, accepted exact subject,
current main, ancestry, protected identities, path count, and clean worktree.
Recompute non-mutating merge-tree composition; preserve every named semantic ordering;
run only the exact integration regressions plus any explicitly required final gate at
the final candidate head. If head/review identity differs, protected bytes drift, a
new conflict appears, or authority is missing, stop.
Record exact integration/merge SHA and tree only after authorized success. Do not infer
Jira, owner acceptance, Gate 6, dispatch, or research-result completion.
```

## 10. Forward obligation register and gates

| Obligation | Current disposition | Owner / next gate |
|---|---|---|
| Preserve all 173 accepted schema bytes and the exact 87-command/86-event trees | Hard invariant. No regeneration, normalization, or equivalent reserialization. | Every candidate and integration reviewer; Stephen decides any protected defect. |
| No bulk activation | Runtime activation remains an explicit exact-binding decision per delivered vertical; materialized file presence is inert. | Slice owner plus fresh exact review; no plan-level activation authority. |
| KAN-65 is broader than C1 | Message and C1 are integrated, but C2, C3, R1 and the horizontal obligations remain open. | KAN-65 remains incomplete; a later campaign needs its own explicit owner start. |
| C1 integrated | KAN-72/PR #212 delivered one coherent 23-row admission-to-running campaign through the complete public path. | Keep KAN-72 Done and do not reopen its rows in later campaigns. |
| Dual arithmetic | Fixed pre-C1 allocation `P2..P8 = 85` and `C1+C2+C3+R1 = 85` remains authoritative; current outstanding totals are 62 after C1. | KAN-71 mechanically verifies the fixed allocation, current census, and intersections above. |
| Integrated RM obligations | KAN-95 is horizontal and row-neutral; KAN-96 governs the nine already-counted P6 rows; KAN-97's nine W3 commands are outside the 104-row catalogue. | All three remain required for WP6.1 completion under P-047 without inflating the catalogue denominator. |
| Preserve SupersedeTask compatibility | P2 carries the three control groups and the separately named stale-classification manifestation without recounting `task.supersede`. | P2 candidate/reviewer. |
| Provider automation | Deferred under P-042; no provider invocation, credential handling, or live adapter/profile automation inside P2-P8. | Separate owner decision outside this sequence (`docs/plans/agentic-research-system/implementation/06g-wp6-owner-operated-session-amendment.md:13-55`, `:82-106`). |
| W11 | Separate 81-row programme. No P2-P8 row, runtime activation, transition, genesis, migration, or cutover is authorized here. | Separate W11 review/owner gates (`docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md:4-15`, `:68-83`, `:490-587`). |
| External review service | Stephen triggers and monitors CodeRabbit. Family goals do not poll or wait across that boundary. | Stephen; fresh closer after explicit notice. |
| New shared abstraction | Prohibited unless two implemented families demonstrate the same missing interface and existing seams cannot carry it. | Sol Ultra architecture review plus Stephen's explicit decision. |
| Recovery-gated rows | P8 remains blocked on a separate WP6.4 owner decision and current accepted base. | Stephen; no import of an old candidate by implication. |
| Artefact-firewall ordering | 06i Stage A/B gates and P6/P7 Decision dependency remain unresolved. | Stephen resolves before P6 dispatch; otherwise `interface-unverified` stop. |
| PR size | Every PR `<100` paths; target `<=90`. P6 hard-stops at 99; other slices use their lower ceilings. | Portfolio coordinator before review. |
| Review authority | Fresh independent exact-subject review is mandatory; no self-review. Review acceptance never substitutes for owner acceptance. | Sol Ultra reviewer, then Stephen. |
| Gate and result claims | This plan claims no Gate 6 closure, dispatch authorization, provider action, research execution, or research result. | Separate accepted evidence and owner decisions. |

## 11. Immediate next action

**Do not reopen C1. Keep KAN-65 and WP6.1 incomplete. C2/KAN-73 is the next capability
campaign, but this record does not authorize its start. On an explicit owner start,
re-resolve C2 against exact live `main`, preserve the fixed catalogue and protected
identities, and validate C2 as one end-to-end capability.**

C2, C3, R1, 06h/RM-01, 06i and 06j remain open Jira work rather than completed
capabilities.
