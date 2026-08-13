# WP6.6 `discovery/runtime.py` adversarial architecture assessment (frozen pre-edit)

Status: frozen Phase A assessment. Written **before** any production edit in this
session. Not independent acceptance, not CodeRabbit completion, not owner
acceptance, not merge authorization, not integration evidence.

Because the same session implements the remediation that follows, this document
is a construction verdict, not an independent approval. The resulting exact head
remains subject to external review and owner acceptance.

## Exact frozen subject

| Property | Value |
|---|---|
| Repository | `stephendor/TDL` |
| PR | #248 |
| Branch | `codex/wp6-6-adversarial-full-review` |
| HEAD | `cf4ea2e48b0564c4e21e63af40846274bf26a039` |
| Tree | `4573e3c2970002851b669e5341161028698b41f7` |
| PR base / live main | `2e6bf9c92e59208c40e55f664fc48d75e481ae04` (verified ancestor of HEAD) |
| Subject file | `research_system/discovery/runtime.py`, 6,481 lines, 320,052 bytes |
| Protected W11 catalogue | blob `8d58818540e04859f929d4b04c71e4cfa0512554`, 136,229 bytes, SHA-256 `7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80` — verified unchanged |

## 1. What responsibilities does `runtime.py` currently own?

Measured region map of the single file:

| Lines | Size | Responsibility |
|---|---:|---|
| 1–42 | 42 | Imports |
| 44–110 | 67 | Accepted-W11 genesis constants (`_ACCEPTED`, `_ROW_IDS`, `_CATALOGUE_STREAM_ID`, `_ARTEFACT_EVENT_TYPES`), `_accepted_genesis_payload`, `DiscoveryLedgerReplayError` |
| 112–406 | 295 | Route registry: `DiscoveryRowRoute`, `_DISCOVERY_ROW_ROUTES` (59 executable rows), `_DISCOVERY_EXCLUDED_ROWS`, `_DISCOVERY_DEFERRED_ROWS`, `_DISCOVERY_MINT_ROWS`, `_DISCOVERY_EXISTING_TARGETS`, `_shared_event_partition`, `_catalogue_event_name`, `_validate_discovery_route_registry`, `_discovery_route` |
| 409–1534 | 1,126 | Shared lifecycle predicates — the `_*_matches` family plus artifact-shape validators |
| 1536–1682 | 147 | Durable-ledger integrity: `_validate_hash_chain`, `_validate_persisted_event_envelopes`, `_default_replay_schemas` |
| 1685–3756 | **2,072** | `replay_discovery` — one function |
| 3759–6481 | **2,723** | `DiscoveryRuntime` — one class |

Inside those two large regions:

- `replay_discovery` holds state initialisation (17-key mutable `state` dict,
  `runtime.py:1709`), 9 closures defined before the loop
  (`runtime.py:1731,1735,1748,1781,1802,1830,1856,1881,1956`), 3 further closures
  re-defined **inside** the per-event loop on every iteration
  (`required_string`, `required_int`, `required_string_list`,
  `runtime.py:2008,2014,2020`), and a **53-branch `if/elif event_type ==` chain**
  (`runtime.py:2257–3641`) that mutates the shared `state` dict in place.
- `DiscoveryRuntime` holds the public seam (`submit`, `runtime.py:3822`),
  authority resolution (`_resolve_authority`, `runtime.py:3852`), identity
  fencing (`_require_candidate_target`, `_require_admissible_target`,
  `runtime.py:3927,3986`), and `_submit_authorized` (`runtime.py:4013–4299`,
  287 lines) which alone performs receipt/idempotency recovery, committed-
  transaction reconstruction, conflict detection, route dispatch, schema and
  producer binding, event-record construction, ledger append and receipt
  persistence. The remaining ~2,180 lines are the `_prepare_*` family and its
  preparation-side `_valid_*` wrappers.

## 2. Which responsibilities are cohesive, and which are improperly coupled?

**Genuinely cohesive, already well-factored:**

- The route registry (112–406) is the strongest asset in the file. It is
  immutable, and `_validate_discovery_route_registry` proves it is an exact
  partition of the 81 accepted catalogue rows (59 executable + 1 deferred +
  21 excluded) and that each row's `command_type` and normalised `ordered_events`
  equal the accepted bytes. Dispatch derives from the accepted row, never from
  caller-controlled payload shape (`_discovery_route`, `runtime.py:393`).
- The shared predicate family (409–1534) is real single-source policy, not
  duplication. Each `_*_matches` predicate has exactly two call sites — one in
  preparation, one in replay (verified usage count 3 = definition + 2 call sites
  for `_promotion_relation_matches`, `_revisit_relation_matches`,
  `_assay_scorecard_matches`, `_spike_plan_matches`, `_assay_cancellation_matches`,
  `_spike_cancellation_matches`; 4 for `_spike_verdict_matches` and
  `_spike_execution_relation_matches`, which have an extra internal use).
  The preparation-side `_valid_*` methods are thin wrappers that add schema
  validation and delegate (`_valid_promotion_relation`, `runtime.py:5108`;
  `_valid_assay_scorecard`, `runtime.py:6212`; `_valid_spike_verdict`,
  `runtime.py:5862`). **This design is correct and must be preserved.**

**Improperly coupled:**

- **`replay_discovery` is a single 2,072-line function.** Fifty-three lifecycle
  reducers share one mutable `state` dict by lexical closure. There is no
  per-lifecycle boundary: the Candidate, Assay, Spike, Decision/Review, dossier,
  authority and artefact reducers are branches of one chain, and any of them may
  read or write any of the 17 state keys.
- **`_submit_authorized` fuses four unrelated concerns**: receipt/idempotency
  recovery (4131–4192), route dispatch (4196–4223), schema/producer binding
  (4224–4258), and event construction plus append (4260–4299). Receipt recovery
  is entirely independent of Discovery lifecycle policy, yet lives inside the
  same method as lifecycle dispatch.
- **Preparation and replay are ~2,000 lines apart** in the same file. The
  equivalence a reviewer must establish — "preparation refuses to publish exactly
  what replay refuses to accept" — is a relation between two regions that cannot
  be held on screen together.
- **Genesis contract constants are ambient.** `_ACCEPTED` (44–56) is protected
  accepted-envelope identity sitting in the same namespace as mutable lifecycle
  helpers.

## 3. Duplicated, implicit, order-sensitive, or distant invariants

1. **One genuine duplication — the Assay Partial reference-binding rule.**
   Unlike every sibling rule, the Partial artifact's reference bindings are
   written twice:
   - preparation: `_valid_assay_partial` (`runtime.py:6228–6265`)
   - replay: the `AssayPartialRecorded` branch (`runtime.py:2506–2547`)

   Both independently compare `candidate_ref`, `assay_id`, `rubric_ref`,
   `scope_ref`, `assay_bar_acceptance_ref`, `assay_relation_hash` and
   `partial_sha256`. The two copies have **already diverged** on the
   bar/assay relation: preparation asserts `bar["status"] == "accepted"` and
   `assay["assay_bar_acceptance_sha256"] == bar["acceptance_sha256"]`, while
   replay asserts `assay["status"] == "evidence_collecting"` and
   `_current_assay_bar_matches(assay, bar, event["actor_id"])`. Only the shape
   and axis halves (`_valid_assay_partial_shape`, `_assay_partial_axes_match`)
   are shared. This is precisely the asymmetry class that hides defects.

2. **Order-sensitive replay state.** `claim_authority_stream` (1735) mutates
   `state["authority_streams"]` and depends on the prior contents of every
   aggregate collection through `_discovery_identity_exists`. Genesis
   (`state["catalogue"] is None`) gates authority replay at 2071 and again at
   2257. These preconditions are enforced at scattered points rather than by one
   envelope.

3. **Implicit closure capture.** The 9 pre-loop closures capture `state`,
   `transaction_events` and `operational_events` implicitly. Nothing in a
   reducer branch's local text declares which state it may touch.

4. **In-loop closure redefinition.** `required_string`/`required_int`/
   `required_string_list` are rebuilt on every event iteration (2008–2023),
   binding `payload` by closure. Their correctness depends on loop position.

## 4. Which past defects were made harder to see by this concentration?

The file has five commits; **four of them are review remediation**, and the file
grew 5,690 → 6,481 lines (+13.9%) entirely through defect correction:

| Commit | Δ lines | Hunk start lines in the new file |
|---|---|---|
| `2e4255c` create | +5,690 | — |
| `d3b72fe` remediate PR review | +213 / −32 | 82, 518, 1548, 1700, 2013, 2095, 2108, 2842, 3158, 3466, 3970, 3984, 5696, 5764 |
| `5c48cc7` replay + authority findings | +77 / −4 | 1703, 1745, 2992, 3175, 3205 |
| `cd61865` PR248 adversarial findings | +228 / −11 | 709, 1778, 1975, 2358, 2916, 3107, 3117, 3293, 3302, 3385, 3615, 3643, 3683, 3699, 3739, 3942, 3967, 3987, 4229 |
| `cf4ea2e` replay + recovery integrity | +374 / −54 | 1778, 2030, 2282, 2336, 2410, 2441, 2539, 2557, 2590, 2633, 2931, 2941, 2961, 3198, 3433, 3470, 4020, 4121, 4137, 4191, 4952, 4962, 6476 |

The decisive evidence is the **hunk spread within a single remediation round**.
`cf4ea2e` — one round of findings — required coordinated edits in the replay
reducer (2030–3470), the receipt-recovery path inside `_submit_authorized`
(4020–4191), and Assay-bar authority preparation (4952–4962). `cd61865` likewise
spans 709 (shared predicates), 1778–3739 (replay), and 3942–4229 (preparation
and dispatch). No reviewer reading any one region could have seen these findings
whole.

Representative defect paths that the structure obscured, taken from the accepted
remediation records:

- *Candidate link joins* (`CandidateAssayLinked`, `CandidateSpikePlanLinked`,
  `CandidateSpikeVerdictLinked`): the shadow event and the result event it must
  join are reduced ~800 lines apart in the same chain; the missing same-
  transaction join was invisible from either branch alone.
- *Orphan dossier materialisation*: `ResearchDossierAdmitted` (3544),
  `PortfolioObjectRegistered` (3569) and `ScopeDefinitionRegistered` (3599) are
  adjacent branches, but their required transaction closure lives in a closure
  defined 1,600 lines earlier (`dossier_materialization_transaction_matches`,
  1956).
- *OR-019 / OR-022 operational closure*: the Discovery reducer defers
  `PartialOutcomeRecorded` / `LeaseReleased` to `replay_control_plane`
  (2001–2006) while the binding predicate sits at 1881 and the preparation-side
  pair builder at 5799 — three regions, one invariant.
- *Receipt recovery vs. lifecycle*: the crash-after-publication finding lives at
  4121–4191, structurally interleaved with route dispatch, though it has nothing
  to do with Discovery lifecycle policy.

## 5. Is the problem length, coupling, state, duplication, abstraction, or boundaries?

It is **not** primarily duplicated producer/reducer rules — the `_*_matches`
family is genuinely shared, and that part of the design is good. It is **not**
primarily raw line count.

The problem is a **combination**, in this order of severity:

1. **Responsibility coupling inside two god-functions.** `replay_discovery`
   (2,072 lines) and `_submit_authorized` (287 lines) each own several unrelated
   concerns with no internal boundary.
2. **Mutable shared projection state with implicit capture.** One 17-key dict
   mutated by 53 branches and 9 closures, with no declared ownership.
3. **Weak module boundaries.** Pure, dependency-free assets (route registry,
   shared predicates, envelope validation, accepted-genesis constants) are
   trapped in the same namespace as stateful orchestration, so they cannot be
   reviewed or reasoned about independently.
4. **Inadequate transaction-level abstraction.** The same-transaction join is
   expressed ad hoc by four separate closures rather than one envelope.
5. **One localised duplication** (Assay Partial, §3.1), already divergent.

Length is a symptom of 1–3, not the disease.

## 6. Can a reviewer establish preparation/replay equivalence locally?

**No.** To verify a single lifecycle transition — for example OR-005
(`RecordAssayPartial`) — a reviewer must currently read:

- `_discovery_route` (393) and the OR-005 registry row (134);
- `_require_admissible_target` / `_require_candidate_target` (3986, 3927);
- `_prepare_assay` (5894) and its OR-005 arm;
- `_valid_assay_partial` (6228);
- `_valid_assay_partial_shape` (431) and `_assay_partial_axes_match` (1107);
- the `AssayPartialRecorded` branch (2506) and the
  `CandidateAssayPartialLinked` branch (2558);
- `following_transaction_event_matches` (1802);
- `_current_assay_bar_matches` (717);
- receipt recovery in `_submit_authorized` (4131–4192).

That is ten regions spread over ~5,800 lines of one file, and the two halves of
the duplicated rule are 3,700 lines apart. This alone answers the mandatory
decision rule against KEEP AS-IS.

## 7. Does each accepted W11 row have one discoverable owner?

Partly. **Producer ownership is excellent**: `_DISCOVERY_ROW_ROUTES` gives every
executable row exactly one command type and preparer family, and
`_validate_discovery_route_registry` proves the partition against accepted bytes.

**Replay-reducer ownership is not discoverable.** There is no mapping from a row
to the reducer branches that accept its events. The correspondence exists only
as `event_type` string equality between the registry's `catalogue_events` tuple
and an `elif` label 2,000 lines away. Nothing prevents a row's event from having
no reducer, or two reducers, and no test asserts the correspondence.

**Write-set validation ownership is scattered** across four transaction-join
closures. **Projection mutation** is discoverable per branch but the state key a
branch may touch is undeclared.

## 8. Are public seams and dependency directions clear?

Public seams are clear and narrow: `research_system/discovery/__init__.py`
exports exactly `DiscoveryRuntime` and `replay_discovery`. The only other
importers are `research_system/projection/replay.py:1277` (a deferred import of
`replay_discovery`) and the test modules. `discovery/authority.py` explicitly
documents that persistence is owned by `runtime.py`.

Dependency direction *within* the file is not expressed at all — it is lexical
ordering only.

## 9. Would extraction create cycles, duplicated policy, or new bypasses?

Analysed per candidate module:

- Route registry, accepted-genesis constants, shared predicates and envelope
  validation are **pure leaves**. They import only `canonical`, `errors`,
  `schema_registry`, `command.reducers`, `discovery.commands` — none of which
  import `discovery.runtime`. No cycle is possible.
- The reducer package needs `state` + `transaction_events` + the join closures.
  Passing an explicit context object removes the implicit capture without new
  dependencies.
- The preparation package needs `self.schemas`, `self.operational_ledger` and
  the shared predicates. Passing the runtime or a narrow protocol keeps the
  direction preparation → rules, never rules → preparation.
- **The real risk is new bypasses, not cycles**: if a reducer branch moves to a
  module but the dispatch chain retains a fall-through, an event could silently
  become unowned. This must be closed by an explicit reducer registry with a
  proven one-owner-per-event-type property, not by convention.
- `research_system/projection/replay.py` imports `replay_discovery` lazily
  *inside* a function specifically to avoid a cycle; that import must keep
  resolving to the same public symbol.

## 10. Decision

**SUBSTANTIAL DECOMPOSITION.**

KEEP AS-IS is refused: §6 shows a reviewer cannot reason locally about a single
transaction, and §4 shows four consecutive review rounds each required
coordinated edits across regions that cannot be read together. A green test
suite does not answer the mandatory decision rule.

BOUNDED EXTRACTION (pure leaves only) is insufficient: it would leave a
2,072-line `replay_discovery` and a 2,723-line `DiscoveryRuntime`, which is
cosmetic relocation of the two god-functions that actually caused the defect
pattern.

### Governing constraint on execution

The decomposition is executed as **strictly behaviour-preserving extraction**,
validated after each coherent step, in dependency order (leaves first). The one
semantic correction identified (§3.1, Assay Partial duplication) is made **after**
the structural work and only behind a red-then-green proof.

### Risks accepted, and their controls

| Risk | Control |
|---|---|
| A moved reducer silently changes rejection behaviour | Focused adversarial subset after every extraction; full 459-test gate at candidate head |
| An event type loses its reducer during the chain split | Explicit reducer registry + architectural test proving one owner per executable event, no duplicates, no orphans |
| New import cycle | Leaf-first order; architectural test forbidding reverse imports |
| Refactor invalidates the exact-head review evidence | Accepted and stated: any new head requires fresh owner-controlled CodeRabbit; this is unavoidable for any remediation |
| Refactoring a frozen adversarially-proven artifact introduces regression | Behaviour-preserving-first rule; no semantic change without a red proof |

### Risk of *not* refactoring

Four rounds of adversarial review have each found defects in this file, and each
round's fixes landed in regions no single reading could span. The defect-arrival
rate has not fallen (the most recent round produced the largest diff of the four).
Leaving the structure intact predicts a fifth round with the same properties.

---

Frozen at `cf4ea2e48b0564c4e21e63af40846274bf26a039` / tree
`4573e3c2970002851b669e5341161028698b41f7` before any production edit.
