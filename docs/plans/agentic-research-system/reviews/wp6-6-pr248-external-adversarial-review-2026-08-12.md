# WP6.6 / KAN-59 — External Adversarial Review — PR #248

**Verdict: REWORK REQUIRED**
**Date:** 2026-08-12
**Reviewer:** independent external adversarial pass — read-only, fresh detached worktree, coverage disabled
**Subject:** `stephendor/TDL` PR #248, branch `codex/wp6-6-adversarial-full-review`

> This is the complete review record for the entire base-to-head implementation, not an
> incremental pass over the latest diff. Every finding carries an exact source location, an
> executed reproducer, observed vs expected behaviour, the owning correction boundary, and an
> explicit sibling-route disposition.

---

## 1. Executive verdict

**REWORK REQUIRED — 1 Critical, 1 Major, 6 non-blocking observations.**

This head is a genuine and substantial advance. **All five blocking findings and all seven
mandatory appendix items from the PR #247 review are closed, and I verified the three
executable ones by re-running the prior reproducers myself** — R1-a, R1-b and R2 all reject
now, with zero mutation and a still-replayable ledger. R1 was correctly re-shaped from
per-branch enumeration into one row-registry-driven submit fence
(`_require_admissible_target`), R2 now re-derives the Attempt/Lease from the canonical
operational partition, R3 routes dossier hashing through the P0 encoder, R4's real
TDA-scale dossier now runs by default and I certified it end to end, and R5's OR-002 is a
real, replay-joined, terminal public route.

Two defects survive, both in the same invariant families the prior review named.

**C-1 (Critical).** The global immutable-identity fence has a *temporal* hole rather than a
per-branch one. `_discovery_identity_exists` treats the W11 catalogue stream as owned only
once `state["catalogue"] is not None`. Before genesis that identity is unowned, and the
authority-lane preparers carry no genesis precondition — unlike the Candidate and Scout
preparers, which do. I executed three separate rows (OR-101, OR-102, OR-110) that claim the
catalogue stream on a fresh store and **permanently brick one-time genesis**: the resulting
ledger replays cleanly, so there is no fault to detect, and every genesis variant is
thereafter refused (version conflict at the declared version, identity collision at the true
one). This is the same failure mode and the same blast radius as prior R1-a — a permanently
destroyed one-time capability, one command deep, with no in-capability recovery.

**M-1 (Major).** OR-019's canonical operational closure is not joined to its Discovery
transaction at replay. This PR added exactly two same-transaction joins
(`candidate_spike_link_matches`, `dossier_materialization_transaction_matches`) and correctly
closed the CandidateSpike-link and orphan-materialization holes with them. The third
multi-event write set — OR-019's `PartialOutcomeRecorded` + `LeaseReleased` — got no such
join, while this PR simultaneously *waived* the generic `command_payload_hash` binding for
`LeaseReleased` under `RecordSpikeVerdict` and `CancelDiscoveryEvaluation`. At a legitimate
mid-flight EOF I deleted each canonical operational event and substituted three payload
fields; five of six attacks were accepted by replay, leaving the durable record asserting a
released Lease and a closed Attempt that the operational partition never released or closed.

Neither defect is attacker-reachable without a valid scoped authority grant. Both are exactly
the class the global identity fence and the atomic write-set contract exist to stop, and C-1
is reachable by ordinary operator error on a fresh store.

---

## 2. Exact-subject identity table

| Check | Required | Observed | Result |
|---|---|---|---|
| Review worktree | fresh, clean, detached | `…/scratchpad/rev248`, `git worktree add --detach` | MATCH |
| PR head | `5c48cc73c5f4f7706049087b4447684330d47c88` | `refs/pull/248/head` → same; `git rev-parse HEAD` → same | MATCH |
| Tree | `0a565bc029d0ef5ce7c2cfe1c016a306f7fb55a5` | `git rev-parse HEAD^{tree}` → same | MATCH |
| Base / live main | `2e6bf9c92e59208c40e55f664fc48d75e481ae04` | `origin/main` → same; `merge-base HEAD main` → same | MATCH |
| Live-main ancestry | ancestor of head | `git merge-base --is-ancestor` → 0 | MATCH |
| KAN-75 delivery ancestor | `26df87157013fa078849acb14921bbcfcdfe53f1` | ancestor → 0 | MATCH |
| KAN-75 review ancestor | `0fd4674ee4fc43515c12d498b7f786555f09bba3` | ancestor → 0 | MATCH |
| Worktree status | clean before and after | `git status --porcelain` empty at start and at end | MATCH |
| Owner checkout | untouched | `C:\Users\steph\TDL` on `main` @ `2e6bf9c9…`, only the pre-existing untracked PR #247 review present | MATCH |

**Protected W11 catalogue identity** — verified by direct byte reads (`open(path,'rb').read()`),
not line-ending-aware text tools, in **both** checkouts:

| Property | Required | Review worktree | Owner checkout |
|---|---|---|---|
| Git blob | `8d58818540e04859f929d4b04c71e4cfa0512554` | `git ls-tree -r HEAD` → `.research-system/evals/expected/w11-portfolio-discovery-v1.json` | same path |
| Size | 136229 | 136229 | 136229 |
| SHA-256 | `7e36b39a…5860b80` | `7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80` | identical |
| Rows | 81 = OR-001–041 + OR-101–140 | 81 unique, exact ordered ascending match | — |
| `owner_row_count` | 81 | 81 (field agrees with actual length) | — |

`supersedes_revision` is `null`, `record_revision` 1, `owner_spec_identity` binds
`git_blob f90729d0…`, 185214 raw bytes of
`docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md` at
reviewed commit `892d1d16…`. No identity differs; the review proceeded on the exact subject.

**Change surface reviewed:** 3 commits, 28 files, +14107/−31 —
`research_system/discovery/{runtime,dossier,authority,assay_authority,commands}.py`,
`research_system/{authority,schema_registry}.py`,
`research_system/command/{lifecycle,reducers}.py`, `research_system/projection/replay.py`,
`research_system/store/lock.py`, four `.research-system/contracts/wp6-6/*.json`,
`tools/certify_wp6_6_real_dossier.ps1`, `.github/workflows/ci.yml`, and 9 test modules.

---

## 3. Critical and Major findings, ordered by dependency

### C-1 — CRITICAL — The global identity fence does not own the catalogue stream before genesis, so a pre-genesis authority registration permanently bricks one-time W11 genesis

**1. ID and severity.** C-1 — Critical.

**2. Violated invariant.** Global immutable-identity closure: *one* unconditional identity
contract over *every* aggregate namespace, applied at the single submit choke point. Also:
"Import the exact owner-accepted W11 catalogue through **one-time replay-safe genesis**" — the
named capability. The prior review's own correction text: *"Make the global identity contract
unconditional at a single choke point rather than enumerated per row… An enumeration is the
wrong shape for this invariant."* The enumeration was removed; a **conditional** remains.

**3. Exact evidence.**

`research_system/discovery/runtime.py:708-714` — the catalogue namespace is gated:

```python
def _discovery_identity_exists(state: Mapping[str, Any], identity: Any) -> bool:
    """Apply the single global immutable-identity contract to every aggregate kind."""
    return bool(
        (state.get("catalogue") is not None and identity == _CATALOGUE_STREAM_ID)   # <-- conditional
        or any(identity in state.get(collection, {}) for collection in _DISCOVERY_IDENTITY_COLLECTIONS)
    )
```

`research_system/discovery/runtime.py:3536-3546` — the fence consumes that predicate for every
mint row, so before genesis it is blind to the one identity the capability depends on:

```python
if row_id in _DISCOVERY_MINT_ROWS:
    if row_id in {"OR-101", "OR-102"} and projection["authority_streams"].get(target) == "assay_bar":
        return
    if _discovery_identity_exists(projection, target):
        raise IntegrityError("Discovery command target identity collision")
    return
```

The second half of the root cause — asymmetric genesis preconditions across preparers:

| Preparer | Rows | Genesis precondition | Source |
|---|---|---|---|
| `_prepare_candidate` | OR-001 | **yes** — `raise IntegrityError("W11 genesis is required before Candidate registration")` | `runtime.py:5780-5781` |
| `_prepare_scout_observation` | OR-029 | **yes** — `"W11 genesis is required before Scout observation ingestion"` | executed, §7 |
| `_prepare_assay_bar_authority` | OR-101–109 | **none** | `runtime.py:4010-4066` |
| `_prepare_authority` | OR-110–121 | **none** | `runtime.py:3774-3808` |

Third contributing factor: `_validate_discovery_route_registry(catalogue)` — the gate that
proves the production route registry is an exact partition of accepted W11 — is invoked
**only** inside `_prepare_genesis` (`runtime.py:5771`). Every pre-genesis executable row
therefore runs without that partition ever having been validated against the accepted bytes.

**4. Executed reproducer.** `scratchpad/adv248/test_adv248_b.py::test_adv_pregenesis_squat_permanently_bricks_genesis`
and `…_c.py`. Run outside the candidate tree with
`PYTHONPATH=<worktree> pytest <harness> -p no:randomly -p no:cacheprovider --no-cov -s`.
Source in Appendix C.1.

**5. Expected vs actual.**

*Expected:* preparation rejects any command whose `target_stream_id` is the reserved W11
catalogue stream unless the command is OR-140 genesis itself; zero mutation; genesis remains
available.

*Actual* (terminal output, verbatim):

```
squat receipt: accepted
appended: [('AssayRubricContentRegistered', 'obj_019fed25-b33e-7740-b280-000000000001', 1)]
ledger STILL REPLAYS. catalogue = None
authority_streams = {'obj_019fed25-b33e-7740-b280-000000000001': 'assay_bar'}
genesis expected_version=0 -> conflict stream_version_conflict
genesis expected_version=1 -> PERMANENTLY BLOCKED: IntegrityError - Discovery command target identity collision
candidate registration -> W11 genesis is required before Candidate registration
```

Both genesis escapes are closed simultaneously and permanently: the declared
`expected_stream_version = 0` can never again be observed (the stream is at 1 and the ledger
is append-only), and at the true version the fence itself refuses because the catalogue stream
is now a claimed `authority_streams` identity. Every Candidate route is dead behind
`W11 genesis is required`.

**6. Impact.** Total and unrecoverable loss of the named capability on that store. Distinctly
worse than prior R1-a in one respect: R1-a left an unreplayable ledger, which is at least a
loud, detectable fault. Here the ledger **replays cleanly** — the store is durably valid, the
route registry never validated, and the only symptom is that genesis returns a mundane
`stream_version_conflict` receipt. Silent absence, on a one-time irreversible operation.

**7. Owning-boundary remediation.** `research_system/discovery/runtime.py`, the identity
predicate and the submit fence — not the individual preparers.

1. Make the catalogue reservation unconditional:
   `identity == _CATALOGUE_STREAM_ID` alone, dropping the `state.get("catalogue") is not None`
   guard, with the OR-140 genesis route the sole permitted claimant of that identity.
2. Independently, add the missing genesis precondition to `_prepare_assay_bar_authority` and
   `_prepare_authority` so that no executable row runs before the accepted catalogue — and
   therefore before `_validate_discovery_route_registry` — has been imported. Either change
   alone closes the executed attack; both are needed, because (1) protects the identity and
   (2) protects the route-registry partition invariant.

Fix (1) is the load-bearing one: the defect is that a namespace in the global contract is
conditionally invisible, and the correct shape for the contract is unconditional.

**8. Decisive regression test.** A parametrized public-seam test over **every**
`_DISCOVERY_ROW_ROUTES` entry except OR-140, submitted against `_CATALOGUE_STREAM_ID` on a
**fresh store with no genesis**, asserting for each row: the submit raises `IntegrityError`;
`tuple(runtime.ledger.iter_events()) == ()`; and `runtime.submit(_genesis()).status ==
"accepted"` afterwards. The final assertion is the one that matters — the existing
`test_exact_w11_genesis_is_one_time_replay_safe_and_tamper_atomic` only proves genesis is
one-time *after* it has run, never that it remains *reachable*. Pair it with a negative
control asserting the test fails against the current head.

**9. Sibling routes inspected.** All 29 `_DISCOVERY_MINT_ROWS` considered; every row whose
preparer can execute pre-genesis was driven against the catalogue identity:

| Row | Command | Pre-genesis result | Disposition |
|---|---|---|---|
| **OR-101** | `RegisterAssayRubricContent` | **ACCEPTED**, genesis bricked | **FAIL — executed** |
| **OR-102** | `RegisterAssayEvidenceScopeContent` | **ACCEPTED** (after a legitimate rubric), genesis bricked | **FAIL — executed** |
| **OR-110** | `RegisterDossierExpectedSetContent` | **ACCEPTED**, genesis bricked | **FAIL — executed** |
| OR-116 | `RegisterPathRegistrationContent` | rejected — `path_scope_mismatch` | blocked by a *content* precondition, not the fence; becomes reachable once a `dossier_expected_set` authority is accepted, so it is not an independent defence |
| OR-001 | `RegisterCandidate` | rejected — `W11 genesis is required…` | PASS |
| OR-029 | `IngestScoutObservationBatch` | rejected — `W11 genesis is required…` | PASS |
| OR-003/011/012/014/015/023/025/026/028/034–038/040 | assay/spike/dossier/review mint rows | unreachable — require an existing Candidate or accepted authority | PASS (transitively) |
| OR-105/107/112/114/118/120 | authority review/decision mint rows | unreachable — require a registered authority subject first | PASS (transitively) |
| OR-140 | genesis | the legitimate claimant | PASS |

*Post-genesis twin:* re-verified PASS — with `catalogue` populated the fence rejects every
foreign claim on the catalogue stream (candidate suite
`test_every_w11_route_rejects_every_foreign_namespace_through_public_submit`, and my own
re-run of prior R1-a/R1-b).

**10. Affected rows / work packages.** OR-140 (destroyed), OR-101, OR-102, OR-110 (attack
vectors), OR-116 (latent twin), and transitively every executable row — WP6.6 / KAN-59.

---

### M-1 — MAJOR — OR-019 (and its OR-022 twin) never joins its canonical operational closure to the Discovery transaction at replay

**1. ID and severity.** M-1 — Major.

**2. Violated invariant.** The accepted OR-019 `complete_write_set` is atomic: the Discovery
outcome and the canonical operational Attempt/Lease closure are one indivisible transaction,
and replay must re-derive the whole set. Also: preparation and replay must accept exactly the
same semantic histories; and the artefact/operational/Discovery partitions must be *jointly*
sound, not merely disjoint.

**3. Exact evidence.**

The preparer emits a six-event atomic batch (`runtime.py:4881-4922`):

```
SpikePartialRecorded        spk_…ff6a   txn_idx 1/6   cmd RecordSpikeVerdict
PartialOutcomeRecorded      att_…7203   txn_idx 2/6   cmd RecordSpikeVerdict   <- canonical operational
LeaseReleased               els_…7206   txn_idx 3/6   cmd RecordSpikeVerdict   <- canonical operational
SpikeAttemptClosed          spk_…ff6a   txn_idx 4/6   cmd RecordSpikeVerdict   <- Discovery shadow
SpikeLeaseReleased          spk_…ff6a   txn_idx 5/6   cmd RecordSpikeVerdict   <- Discovery shadow
CandidateSpikePartialLinked obj_…ff68   txn_idx 6/6   cmd RecordSpikeVerdict
```

`_shared_event_partition` (`runtime.py:331-332`) routes the two canonical events to the
operational reducer unconditionally. Replay then validates the two Discovery shadows against
**the spike's own recorded fields only** — never against the operational partition, and never
against the transaction:

`research_system/discovery/runtime.py:2976-2993`

```python
elif event_type == "SpikeAttemptClosed":
    spike = state["spikes"].get(payload.get("spike_id"))
    if (not isinstance(spike, dict)
        or spike.get("status") not in {"partial_recorded", "cancelled"}
        or spike.get("attempt_id") != payload.get("attempt_id")):      # <-- self-referential
        raise IntegrityError("invalid Spike attempt closure")
    spike.update(attempt_status="cancelled" if spike.get("status") == "cancelled" else "partial")
elif event_type == "SpikeLeaseReleased":
    spike = state["spikes"].get(payload.get("spike_id"))
    if (not isinstance(spike, dict)
        or spike.get("attempt_status") not in {"partial", "cancelled"}
        or payload.get("lease_id") != spike.get("lease_id")):          # <-- self-referential
        raise IntegrityError("invalid Spike lease release")
    spike.update(lease_status="released")
```

Contrast the two joins this PR **did** add, which are the correct shape:

| Join | Source | Binds |
|---|---|---|
| `candidate_spike_link_matches` | `runtime.py:1748-1779` | same-transaction preceding Spike event, exact stream, exact payload equality |
| `dossier_materialization_transaction_matches` | `runtime.py:1781-1799` | same-transaction preceding `ResearchDossierAdmitted` on the exact dossier stream |
| **OR-019 operational closure** | — | **absent** |

`grep -n "transaction_events.get(event" research_system/discovery/runtime.py` returns exactly
two hits — lines 1764 and 1788. There is no third.

This PR simultaneously *weakened* the generic backstop.
`research_system/command/lifecycle.py:462-467` adds:

```python
_DERIVED_PRODUCER_PAYLOAD_EVENTS = frozenset({
    ("LeaseReleased", "RecordSpikeVerdict"),
    ("LeaseReleased", "CancelDiscoveryEvaluation"),
})
```

consumed at `:508` to skip `command_payload_hash != sha256_hex(canonical_bytes(payload))`. So
the durable `LeaseReleased` payload is bound neither to its command nor to its Discovery
transaction. The only residual defence is whatever `reduce_lease` / `reduce_attempt`
independently happen to validate.

**4. Executed reproducer.** `scratchpad/adv248/test_adv248_e.py`. Drive the real OR-019
PARTIAL lifecycle, truncate at the `CandidateSpikePartialLinked` transaction boundary — a
legitimate mid-flight EOF — then fully reindex `global_position` and `stream_version`,
recompute `transaction_index`/`transaction_count`, and rebuild the entire hash chain
(`_fully_reindex_and_rehash_events`). Source in Appendix C.2.

Truncation is essential: on the untruncated ledger every one of these attacks is rejected, but
with `invalid Discovery revisit request` — a *downstream* revisit-relation hash catching the
tamper incidentally, not an OR-019 binding. See §6.

**5. Expected vs actual.**

*Expected:* replay resolves the Attempt and Lease from `replay_control_plane(operational_events)`
at that ledger position, requires the canonical closure events to be present in the same
transaction as the Discovery shadows, and binds their payloads — exactly as
`_spike_start_operational_matches` already does for OR-017.

*Actual* (verbatim; truncated baseline replays to `attempt_status partial / lease_status released`):

```
*** LeaseReleased DELETION AT BOUNDARY ACCEPTED ***
  spike status: partial_recorded attempt_status: partial lease_status: released
  canonical operational events remaining: ['PartialOutcomeRecorded']

*** PartialOutcomeRecorded DELETION AT BOUNDARY ACCEPTED ***
  spike status: partial_recorded attempt_status: partial lease_status: released
  canonical operational events remaining: ['LeaseReleased']

*** LeaseReleased.release_reason SUBSTITUTION AT BOUNDARY ACCEPTED ***
  durable LeaseReleased payload: {'holder_actor_id': 'act_…1002', 'lease_id': 'els_…7206',
                                  'observed_at': '2026-08-01T00:00:00Z', 'release_reason': 'operator_override'}

*** LeaseReleased.observed_at SUBSTITUTION AT BOUNDARY ACCEPTED ***
  durable LeaseReleased payload: {…, 'observed_at': '2099-01-01T00:00:00Z', 'release_reason': 'spike_partial'}

*** PartialOutcomeRecorded.stop_cause SUBSTITUTION ACCEPTED ***

LeaseReleased.holder_actor_id at boundary REJECTED -> invalid Discovery operational partition
```

Five of six accepted. The single rejection comes from `reduce_lease` inside
`replay_control_plane` — an incidental control-plane check, not a Discovery join.

**6. Impact.** The durable record can assert that a Lease was released and an Attempt closed
when the canonical operational ledger did neither — the Lease remains `active` and the Attempt
remains `running` in `replay_control_plane`. That is precisely the "duplicate Attempt/Lease
ownership across Spikes" and "PARTIAL operational closure and Lease release" surface the
review mandate names: a Lease believed released by Discovery but still live operationally can
be re-derived as held while a second Spike acquires it. `release_reason` and `observed_at` are
free-text and free-time in the durable operational record, defeating resource accounting and
release-timing attribution. `stop_cause` is likewise unbound.

**7. Owning-boundary remediation.** `research_system/discovery/runtime.py`, the
`SpikeAttemptClosed` and `SpikeLeaseReleased` replay branches.

Add a same-transaction operational join in the shape of the two that already exist: for
`SpikeAttemptClosed`, require exactly one preceding `PartialOutcomeRecorded` in the same
`transaction_id` on `stream_id == spike["attempt_id"]` whose payload matches the prepared
closure; for `SpikeLeaseReleased`, require exactly one preceding `LeaseReleased` in the same
transaction on `stream_id == spike["lease_id"]`, with `holder_actor_id` re-derived from
`replay_control_plane(operational_events)` and `release_reason` pinned to the value the row
mandates (`spike_partial` for OR-019, `spike_cancelled` for OR-022). Reuse
`_spike_start_operational_matches` as the template — it is the correct pattern, already
present, and already proven by R2's closure.

Separately, reconsider `_DERIVED_PRODUCER_PAYLOAD_EVENTS`: waiving the generic
`command_payload_hash` binding removed a working invariant to admit a payload shape. If the
waiver is retained, the Discovery-side join must fully replace what it removed.

**8. Decisive regression test.** A parametrized replay test that, for both OR-019 (PARTIAL)
and OR-022 (cancellation of a *running* Spike), truncates the real ledger at the closure
transaction boundary and asserts `replay_discovery` raises `IntegrityError` for each of:
(a) `LeaseReleased` deleted; (b) `PartialOutcomeRecorded` deleted; (c) each of
`release_reason`, `observed_at`, `holder_actor_id` substituted; (d) `stop_cause` substituted;
(e) the canonical events moved to a different `transaction_id` — each after
`_fully_reindex_and_rehash_events`. The suite's existing OR-019 coverage exercises the happy
path and downstream relations only, which is why this survived.

**9. Sibling routes inspected.**

| Route | Multi-event write set | Same-transaction join | Disposition |
|---|---|---|---|
| OR-018 `CandidateSpikeVerdictLinked` | yes | `candidate_spike_link_matches` | **PASS** — added this PR; candidate test `test_replay_rejects_fully_rehashed_candidate_spike_links_without_exact_transaction_join` |
| OR-019 `CandidateSpikePartialLinked` | yes | `candidate_spike_link_matches` | **PASS** — same helper |
| OR-028 objects / edges / Scopes | yes | `dossier_materialization_transaction_matches` | **PASS** — added this PR |
| **OR-019 `SpikeAttemptClosed` / `SpikeLeaseReleased`** | yes | **none** | **FAIL — executed** |
| **OR-022 `SpikeAttemptClosed/cancelled` + `LeaseReleased`** | yes | **none** | **FAIL — structural twin, inspection-confirmed.** The cancellation path emits the same two canonical events (`runtime.py:4969-4997`) into the **same two replay branches** proven defective above (`:2976-2993`), and carries the same `_DERIVED_PRODUCER_PAYLOAD_EVENTS` waiver. No separate reproducer was built: the only committed OR-022 coverage cancels *before* start with `attempt_ref`/`lease_ref` `None` (test module lines 3985-4029), so no canonical closure is emitted on that path and the running-Spike cancellation has no positive test to truncate. Treat as unproven-but-structurally-identical. |
| OR-017 `SpikeStarted` operational binding | yes | `_spike_start_operational_matches` | **PASS** — R2 closed; I re-executed the prior reproducer |
| OR-115 / OR-121 authority accept shadows | yes | outer transaction id injected at replay (`:1862`) | PASS |

**10. Affected rows / work packages.** OR-019 (executed), OR-022 (twin), OR-017 boundary
(adjacent), and the shared-ledger partition contract — WP6.6 / KAN-59.

---

## 4. Invariant → enforcement → test matrix

| # | Invariant | Enforcement artifact | Binding test | Status |
|---|---|---|---|---|
| I1 | Accepted W11 bytes are exact and unaltered | `_ACCEPTED` byte/blob/size check + bootstrap digest, `runtime.py:5755-5770` | `contracts/test_w11_expected_catalogue.py` (287 cases) | PASS |
| I2 | Genesis is one-time and replay-safe | `_prepare_genesis` + catalogue reservation in `_discovery_identity_exists:712` | `test_exact_w11_genesis_is_one_time_replay_safe_and_tamper_atomic` | **FAIL — C-1**: proves one-time *after* genesis, never that genesis stays reachable |
| I3 | Route registry is an exact 59/1/21 partition of accepted W11 | `_validate_discovery_route_registry`, `runtime.py:355-390` | `test_wp6_6_discovery_activation.py` | PASS as written; **not invoked before genesis** (C-1 contributing factor) |
| I4 | Dispatch derives from the accepted row, never payload shape | `_discovery_route`, `runtime.py:393-406` | route/namespace matrix tests | PASS — prior Appendix 4 closed |
| I5 | One unconditional global identity fence at the submit choke point | `_require_admissible_target`, `runtime.py:3536-3554`, called at `:3670` | `test_every_w11_route_rejects_every_foreign_namespace_through_public_submit` (59 rows × 12 namespaces) | **FAIL — C-1**: fence is unconditional over collections, conditional over the catalogue |
| I6 | Authority observation binds the exact registered content stream | `_DISCOVERY_EXISTING_TARGETS` → `authority_streams` kind match; replay `:1877`, `:1891-1894` | `test_assay_authority_observe_rejects_a_candidate_stream_without_mutation`, `test_generic_authority_observe_…` | PASS — R1-a/R1-c closed, **re-executed by reviewer** |
| I7 | Stale-successor registration may re-enter only its own claimed stream | fence exemption `:3542-3543` mirroring `claim_authority_stream:1745` | `test_assay_authority_observe_allows_same_kind_stream_continuation` | PASS — R1-b closed, **re-executed by reviewer** |
| I8 | Preparation and replay accept the same semantic histories | shared predicates; `DiscoveryLedgerReplayError` wrapper widened to `(IntegrityError, TypeError, ValueError)` at `:3666` | `test_submit_surfaces_persisted_replay_failure_as_operational_fault` | PASS |
| I9 | All dossier semantic hashes use the P0 canonical encoder | `canonical_dossier_hash` → `canonical_bytes`, `dossier.py:77-89`; command payload P0 check `runtime.py:3404-3407` | `test_assay_fixture_axis_and_dependent_content_hashes_are_canonical`, P0 negatives | PASS — R3 closed |
| I10 | OR-017 Attempt/Lease re-derived from the operational ledger | `_spike_start_operational_matches`, `runtime.py:1322-1358` (8 properties + resource + expiry) | OR-017 replay negatives | PASS — R2 closed, **re-executed by reviewer** |
| I11 | OR-019/OR-022 canonical operational closure is atomic and re-derivable | **none** | none | **FAIL — M-1** |
| I12 | Every materialization binds its admission in the same transaction | `dossier_materialization_transaction_matches`, `runtime.py:1781-1799` | orphan-object / orphan-Scope replay negatives | PASS |
| I13 | Candidate links bind their exact preceding Spike result | `candidate_spike_link_matches`, `runtime.py:1748-1779` | `test_replay_rejects_fully_rehashed_candidate_spike_links_without_exact_transaction_join` | PASS |
| I14 | Shared ledger partitions are disjoint and exhaustive | `_shared_event_partition`, `runtime.py:323-337`; unconditional `replay_control_plane(operational_events)` at `:3234-3237` | `test_shared_ledger_partition_is_disjoint_and_exhaustive`, `test_replay_unconditionally_validates_the_complete_operational_partition` | PASS structurally; **the operational half is unbound to Discovery — M-1** |
| I15 | OR-002 supersession is immutable, acyclic, single-use, terminal | `_prepare_candidate_supersession:5810-5854` + symmetric replay `:2128-2167`; `_candidate_supersession_lineage:505-534` | 2 public tests + reviewer chain/cycle attack | PASS |
| I16 | OR-030 is inactive and cannot mutate | no entry in `DISCOVERY_COMMAND_TYPES`; `command_binding` None → `inactive Discovery command binding`; replay guard `:1807` | `test_annotation_ingestion_is_deferred_…`, `test_forged_annotation_event_cannot_bypass_the_deferred_route` | PASS |
| I17 | OR-116 `content_sha256` canonically derived at registration and replay | `_content_sha256` + `content_hash_mismatch`, `authority.py:63-71, 132-133` | 3 authority tests | PASS |
| I18 | Number-valued Assay axes cannot activate | `runtime.py:4072-4079` → `IntegrityError` | `test_number_valued_assay_rubric_cannot_activate_…` | PASS — prior Appendix 1 closed |
| I19 | Durable authority shadows carry no preparation placeholder | `persisted_shadow.pop("transaction_id")`, `runtime.py:3991-3993`; replay injects at `:1862` | `test_accepted_authority_shadow_uses_the_outer_durable_transaction_identity` | PASS — prior Appendix 3 closed |
| I20 | Real TDA-scale dossier admission is certified, not skipped | owner default `Path.home()/TDL` + `TDL_REQUIRE_REAL_DOSSIER=1`, test module `:51-91`; `tools/certify_wp6_6_real_dossier.ps1` | 35 real-dossier tests | PASS on the owner default and under certification; **CI still skips — m-1** |
| I21 | No provider execution, dispatch, promotion, migration or cutover | `dispatchable: False` / `provider_execution: "forbidden"` / `execution_authorized is not False` at `dossier.py:141-142, 435-436, 701`, `authority.py:111-112`, `runtime.py:1415` | boundary assertions across the dossier suite | PASS |

---

## 5. Attack-family completeness ledger

| # | Mandatory family | Verdict | Evidence |
|---|---|---|---|
| 1 | Genesis and route completeness | **FAIL — C-1** | Byte/blob/size/row census verified in both checkouts. Exact 59 executable + OR-030 deferred + 21 excluded partition verified mechanically (`_validate_discovery_route_registry`, `runtime.py:355-390`) and it is a genuine join against accepted catalogue `command_type` and normalized `ordered_events`, not a restatement of the registry. Every executable row binds command, authority subject, schema, producer, event batch, reducer and projection. **But** genesis itself is destroyable pre-emptively, and the route registry is never validated on any pre-genesis path. |
| 2 | Persisted envelope and replay equivalence | **PASS** | `_validate_persisted_event_envelopes:1551-1700` binds project, stream version, transaction index/count, command id/type/schema id+version+sha256, idempotency key, payload hash, correlation/causation, actor, grant, occurred-at. Attacks on fully reindexed/recounted/rehashed ledgers (mine and the suite's) reject on semantics, not on hash-chain arithmetic. `DiscoveryLedgerReplayError` now wraps `(IntegrityError, TypeError, ValueError)`. |
| 3 | Global immutable identity closure | **FAIL — C-1** | All eleven namespaces plus catalogue crossed. `_DISCOVERY_IDENTITY_COLLECTIONS:693-705` is exhaustive (`authority_subject_streams` is keyed by kind, not identity — correctly excluded). Prior R1-a/R1-b re-executed and closed. The catalogue namespace remains conditional. |
| 4 | Candidate lifecycle | **PASS** | OR-001 direct, OR-029 Scout-created, OR-002 supersession all reviewed. My own chain attack (A→B→C then C→A) rejects with `Candidate supersession lineage is cyclic`; predecessor/replacement inversion, self-supersession, stale predecessor and reused replacement all reject atomically; post-supersession `RegisterSpikePlan` rejects; receipt retry after receipt-file deletion returns the identical receipt and restores the file. |
| 5 | Assay lifecycle and authority | **PASS** | OR-101–109 authority chain, positive/partial/cancellation/revisit/retry paths, six-actor independence across accumulated history, rubric/scope successor ordering, exact `commit:path`/raw/blob joins, scorecard axis/domain enforcement, dormant numeric lanes rejected at OR-101, review supersession. |
| 6 | Spike lifecycle and operational authority | **FAIL — M-1** | PASS/PARTIAL/FAIL all driven through public seams. OR-017 operational re-derivation closed (re-executed). Decision option closure, resource content hashes, holder/expiry/revocation timing, verdict truth table, cancellation atomicity all hold. **OR-019/OR-022 canonical operational closure is unbound.** |
| 7 | Atomicity, crash recovery and receipts | **PARTIAL** | Before-append and after-publish-before-receipt injection both covered and zero-mutation/exact-receipt-recovery proven; restart/retry, command-id reuse with a mismatched envelope, durable idempotency scoping, and cross-process authority revocation under `CompositeWriterLock` all covered. **No crash-injection test exists for dossier preparation/publication** — see m-6. |
| 8 | Shared-ledger partitioning | **PASS** | `_shared_event_partition` assigns every event exactly once; `replay_control_plane(operational_events)` runs unconditionally at `:3234-3237` and raises on any unsupported type; generic replay now invokes `replay_discovery` when any Discovery event is present (`projection/replay.py:1271-1278`), and skips only the generic lifecycle binding for Discovery-owned events. I confirmed by inspection that every Discovery `ResolveDecision` row emits at least one event type unknown to `replay_control_plane`, so a partition-flip tamper is fail-closed. |
| 9 | Dossier authority and semantic materialization | **PASS** | OR-110–121 and OR-028 end to end; 35 real-dossier tests executed by me, twice (default environment and committed certification). Orphan materialization now bound to the exact admission transaction. Expected-set content hash canonically recomputed at admission (`dossier.py:362-363`). Acyclic dependency validation is iterative, not recursive. |
| 10 | Physical path authority | **PASS (candidate-derived)** | Traversal, symlink/junction/nested-reparse aliases, hardlink/file-identity collision, root replacement, rename/double-swap ABA during reads, stale registration hash, unauthorized root, wrong environment scope and missing root are all exercised by the 35 real-dossier tests, which I executed. OR-116 `content_sha256` confirmed canonically derived and checked at registration **and** replay. I did not independently re-derive the physical-path attacks — see §9. |
| 11 | OR-030 deferral boundary | **PASS** | No schema binding, no command-type membership, no producer, no scoped grant. Public submission fails with `inactive Discovery command binding` before any event or receipt mutation. Forged durable annotation events fail both `replay_discovery` and `replay_projection`. The route census names OR-030 explicitly as deferred with its owning work package. No adjacent implementation claims annotation ingestion. The contract contradiction (accepted §7.4 requires an `annotation_epoch_id` the protected `additionalProperties: false` v1 schema forbids) is accurately represented, and the required owner decision — accept a versioned successor schema plus one initial-epoch authority — is stated. Deferral is **not** counted as implemented capability anywhere in this review. The deferral disables nothing else: the other 59 executable rows are independently routed. |
| 12 | Provider-free boundary | **PASS** | The only external process invocation in the entire reviewed surface is read-only `git rev-parse` / `git show` at `runtime.py:3839-3858` and `:4421-4438`, both timeout-bounded and both verifying committed bytes against read bytes. No network imports (`socket`/`requests`/`urllib`/`httpx`/`aiohttp` absent). No credential handling, no SCALE-01 pilot or research execution, no result or claim promotion, no migration/cutover, no KAN-69 transition work, no live restore cutover, no WP6.7 or Gate 6 closure. The 21 excluded migration/cutover/transition rows are affirmatively unimplemented. |

---

## 6. Minor and non-blocking observations

Recorded in full; none is a merge blocker on its own.

| # | Observation | Why it matters | Minimal disposition |
|---|---|---|---|
| **m-1** | **CI does not certify the real dossier.** `.github/workflows/ci.yml`'s only change is `fetch-depth: 0` / `persist-credentials: false`. Neither `TDL_REPOSITORY_ROOT` nor `TDL_REQUIRE_REAL_DOSSIER` is set, and on a CI runner `Path.home()/TDL` does not exist — so `_UNAVAILABLE_REAL_DOSSIER_ROOTS` is non-empty and all 35 tests **skip silently**. R4 is genuinely closed for the owner's default environment and under the committed script; it is not closed in CI. | The headline deliverable has no automated gate. A future change that breaks real-dossier admission goes green in CI. | Set `TDL_REQUIRE_REAL_DOSSIER=1` plus a vendored fixture root in one CI job, or state in the acceptance record that certification is an owner-machine step and name who runs it per release. |
| **m-2** | **The certification script's Python auto-resolution is fragile.** `tools/certify_wp6_6_real_dossier.ps1:9-13` prefers `$repositoryRoot\.venv\Scripts\python.exe`. In a fresh clone or review worktree, `uv run` creates a `.venv` **without** pytest, so the committed certification command fails with `No module named pytest` rather than a usable message. I had to override `TDL_PYTHON` to certify. | The one committed reproducible invocation does not work out of the box on a fresh checkout — the exact scenario R4 was raised to fix. | Probe for pytest importability and fall back, or run via `uv run --group dev python -m pytest`. |
| **m-3** | **The R1 regression test cannot distinguish a fence rejection from any other.** `test_every_w11_route_rejects_every_foreign_namespace_through_public_submit` monkeypatches `replay_discovery` to a synthetic projection and asserts bare `pytest.raises(IntegrityError)` with no `match=`. Any rejection — including one from an unrelated preparer check — passes the cell. | The prior review's decisive test for the Critical invariant is one refactor away from becoming vacuous. | Add `match="Discovery command target identity collision|W11 authority stream identity collision|Discovery command target is owned by another aggregate"`. |
| **m-4** | **`pytest.mark.integration` is registered only relative to the repo rootdir.** Appendix 7's disposition ("already registered in the reviewed baseline") holds when pytest resolves `pyproject.toml`; every harness run from outside the tree emitted `PytestUnknownMarkWarning`. | Cosmetic, but it obscured real warnings during this review. | Note the rootdir dependence, or register the marker in a `conftest.py` that travels with the tests. |
| **m-5** | **The Discovery/generic `ResolveDecision` split keys on caller-influenced payload content.** `discovery_resolve_transaction_ids` (`commands.py:48-65`) claims a transaction when any event payload carries `row_id` or `owner_row_id` in `DISCOVERY_RESOLVE_ROWS`. A *generic* CommandService `ResolveDecision` whose payload happens to contain `row_id: "OR-010"` is pulled into the Discovery partition and fails Discovery replay, bricking the shared ledger. | Fail-closed, and no privilege escalation — but a denial surface reachable from ordinary generic payload content. | Key the split on the command's resolved row binding rather than raw payload key presence, or reserve those payload keys in the generic command schema. |
| **m-6** | **No crash-injection coverage for dossier preparation/publication.** `test_wp6_6_discovery_crash_recovery.py` contains exactly two tests (before-publish, after-publish) and both drive the generic multi-stream batch, not OR-028. | OR-028 has the largest write set in the capability; its irreversible boundary is the least tested. | Add the two crash boundaries for `AdmitResearchDossier`. |
| **m-7** | **M-1's incidental defence is load-bearing on the untruncated ledger.** Every M-1 attack rejects on a complete ledger, but with `invalid Discovery revisit request` — a downstream revisit-relation hash, not an OR-019 binding. | A future change that shortens or reshapes the post-PARTIAL revisit chain silently removes the only defence. | Fixing M-1 makes this moot; until then, do not read the untruncated rejections as coverage. |

---

## 7. Claims tested, and attacks that failed safely

Every disposition in `wp6-6-pr247-adversarial-review-remediation-2026-08-12.md` was treated as
a claim to verify. Results:

| Remediation claim | Verified? | How |
|---|---|---|
| R1 — one row-registry submit fence, mint-or-advance, every executable row | **Partly.** The fence exists, is applied at one choke point, and closes R1-a/R1-b/R1-c. It does **not** own the catalogue identity pre-genesis — **C-1** | Re-executed prior R1-a and R1-b reproducers; read `_require_admissible_target`; drove 3 new rows pre-genesis |
| R2 — `SpikeStarted` re-derives Attempt/Lease from the shared operational partition | **Yes** | Re-executed Appendix C.3 verbatim → `invalid Spike start`. Confirmed `operational_events` accumulates in ledger order, so the re-derivation is at the event instant |
| R3 — dossier identities use the P0 encoder; non-P0 values become governed errors | **Yes** | `canonical_dossier_hash` delegates to `canonical_bytes` (`dossier.py:89`); command payloads P0-checked at `runtime.py:3404-3407`; `_submit_authorized` wraps `(TypeError, ValueError)` → `DossierAdmissionRejected` and `(IntegrityError, TypeError, ValueError)` → `DiscoveryLedgerReplayError` |
| R4 — owner defaults resolve; `TDL_REQUIRE_REAL_DOSSIER=1` makes absent roots a failure | **Yes, with m-1/m-2** | 35 real-dossier tests ran and passed in the default environment with no env var set; required-mode against a nonexistent root produced a **collection error**, not a skip; committed script passed 35/35 |
| R5 / OR-002 — active, authorized, producer-bound, terminal, replay-joined, retry-safe | **Yes** | Read both sides; ran my own lineage-chain and cycle attack |
| R5 / OR-030 — explicitly deferred and inactive | **Yes** | Public submit fails pre-mutation; forged durable event fails both replays; census names it deferred |
| R5 coverage — exact 59 / 1 / 21 partition against all 81 rows | **Yes** | `_validate_discovery_route_registry` joins each row's `command_type` and normalized `ordered_events` to the registry — a real content join, not a self-restatement |
| Appendices 1–7 | **Yes** (1, 3, 4, 5, 6 verified in source; 2 is a scope statement; 7 holds subject to m-4) | See §4 I18, I19, I4, I14, and the route registry's OR-001/OR-029/OR-140 row tagging |
| "PR #248 current-head dispositions" — CandidateSpike link joins, orphan materialization, OR-116 canonical digest, W11 identity test byte comparison | **Yes** | `candidate_spike_link_matches:1748`, `dossier_materialization_transaction_matches:1781`, `authority.py:132-133`, and my own byte-level W11 check in both checkouts |

**Attacks I ran that failed safely** (the implementation held):

- Prior R1-a — OR-103 `ObserveW11AuthorityFile` on a live Candidate stream → `W11 authority stream identity collision`, zero mutation, ledger still replays.
- Prior R1-b — OR-109 stale → OR-101 successor squatting a live Candidate identity → `Discovery command target identity collision`, zero mutation.
- Prior R2 — OR-017 fabricated Attempt/Lease at a legitimate EOF, fully reindexed and rehashed → `invalid Spike start`.
- OR-002 supersession cycle (A→B, B→C, then C→A) → `Candidate supersession lineage is cyclic`, zero mutation, ledger still replays.
- OR-029 `IngestScoutObservationBatch` pre-genesis on the catalogue stream → `W11 genesis is required before Scout observation ingestion`.
- OR-001 `RegisterCandidate` pre-genesis on the catalogue stream → `W11 genesis is required before Candidate registration`.
- OR-116 `RegisterPathRegistrationContent` pre-genesis on the catalogue stream → `path_scope_mismatch`.
- `LeaseReleased.holder_actor_id` substitution at the OR-019 boundary → `invalid Discovery operational partition`.
- All four M-1 attacks against the **untruncated** ledger → rejected downstream (see m-7).

---

## 8. Commands executed and terminal results

All figures are from runs I executed myself in the detached worktree at `5c48cc7`, with
coverage disabled (`--no-cov`) and random ordering disabled. Nothing is reported on the
author's behalf.

| Command | Result |
|---|---|
| `git worktree add --detach … 5c48cc7` then `rev-parse HEAD` / `HEAD^{tree}` / `merge-base --is-ancestor` ×3 / `status --porcelain` | all MATCH, clean |
| `python -c` direct byte read + SHA-256 of the W11 catalogue, in worktree **and** owner checkout | 136229 bytes, `7e36b39a…5860b80`, identical |
| `uv run --env-file .env pytest` over the full changed Discovery/authority/crash/dossier/contract/unit surface `-q -p no:randomly --no-cov -rs` | **427 passed, 1 skipped, 776.50s** (only skip: `rfc3339-validator absent`; **zero real-dossier skips**) |
| `tools/certify_wp6_6_real_dossier.ps1` (with `TDL_PYTHON` overridden per m-2) | **35 passed, 53.31s, exit 0** |
| `TDL_REQUIRE_REAL_DOSSIER=1 TDL_REPOSITORY_ROOT=C:/nonexistent-review-root pytest …dossier_admission.py` | **collection ERROR** — `pytest.UsageError: real TDA dossier certification requires accessible roots: TDL_REPOSITORY_ROOT, TDA_VAULT_ROOT` (negative control fires) |
| `pytest adv248/test_adv248_a.py -k "r1a or r1b or r2" -s` | **3 passed, 71.23s** — all three prior findings confirmed closed |
| `pytest adv248/test_adv248_a.py -k "pregenesis or chain" -s` | **2 passed, 13.73s** — C-1 first observed |
| `pytest adv248/test_adv248_b.py -s` | **6 passed, 9.28s** — C-1 blast radius + 5-row sibling sweep |
| `pytest adv248/test_adv248_c.py -s` | **2 passed, 10.31s** — OR-110 and OR-102 twins confirmed |
| `pytest adv248/test_adv248_d.py -s` | **5 passed, 261.75s** — M-1 attacks on the untruncated ledger, all rejected downstream |
| `pytest adv248/test_adv248_e.py -s` | **5 failed, 2 passed, 347.29s** — M-1 confirmed; the 5 failures are my assertions firing on accepted attacks |
| `grep -n "transaction_events.get(event" runtime.py` | exactly 2 hits (`:1764`, `:1788`) — no third same-transaction join |
| provider-boundary scan (`subprocess`/`socket`/`requests`/`urllib`/`httpx`/`aiohttp`/dispatch/promotion/cutover tokens) | only read-only `git rev-parse`/`git show`; no network; boundary assertions present |

No timeouts. No run exceeded its bound. No unresolved execution is reported as green.

---

## 9. Unresolved evidence and residual risks

- **OR-022 running-Spike cancellation is inspection-only.** The defect shape is identical to
  the executed OR-019 case — same two replay branches, same missing join, same payload-binding
  waiver — but I built no separate reproducer, because the only committed OR-022 coverage
  cancels before start (`attempt_ref`/`lease_ref` `None`), leaving no positive running-Spike
  cancellation to truncate. Unproven-but-structurally-identical.
- **Physical-path attacks are candidate-derived.** Family 10 is proven by the candidate's own
  35 real-dossier tests, which I executed twice. I did not independently re-derive the
  traversal/junction/reparse/hardlink/ABA attacks. That is supporting evidence, not reviewer
  attack surface.
- **Windows-only path semantics.** All junction and reparse behaviour was exercised on
  NTFS / Windows 11 only.
- **Concurrency.** All work was single-process. `CompositeWriterLock` spans the Discovery,
  authority and operational roots and the cross-process revocation test passes, but genuine
  parallel-writer races were not exercised. Unchanged from the prior review.
- **C-1's authority precondition.** Reaching C-1 needs a valid scoped grant naming the
  catalogue stream as its subject. I did not assess how easily such a grant is minted in
  production. This bounds exploitability, not the defect: an operator who copies the
  well-known genesis stream id into an authority record's `record_id` on a fresh store
  destroys the capability, and the global identity fence exists precisely to make a
  correct-authority/wrong-target command fail.
- **M-1's cross-Spike consequence is unproven.** I proved the durable inconsistency (Discovery
  says released/closed, operational says active/running). I did not construct a second Spike
  acquiring the still-active Lease. The inconsistency is proven; the exploit path is inferred.
- **No inference is drawn from the 427 passing tests** to any behaviour not directly attacked.

**Explicit owner decisions required:**

1. **OR-030.** The contract contradiction is real and accurately represented: accepted W11 §7.4
   requires an immutable `annotation_epoch_id` that the protected
   `ars://portfolio/discovery-annotation@1.0.0` schema forbids under
   `additionalProperties: false`, and no accepted initial-epoch authority exists. Activation
   needs Stephen to accept a versioned successor schema, one exact annotation-inbox
   `PathRegistrationContent`, and an initial epoch authority/event. Deferring was the right
   call; the deferral is not capability.
2. **m-1.** Whether real-dossier certification stays an owner-machine step or becomes a CI gate.
3. **M-1's `_DERIVED_PRODUCER_PAYLOAD_EVENTS` waiver.** Whether the generic
   `command_payload_hash` binding stays waived for these two producer pairs once the Discovery
   join replaces it.

---

## 10. Review provenance and boundaries

Read-only throughout. No implementation, no remediation, no commits, no pushes, no PR replies
or thread resolution, no Jira changes. CodeRabbit was neither triggered, polled, scheduled,
simulated nor inferred. Nothing was merged; no owner acceptance or merge recommendation is
made or implied beyond the verdict below.

Local, additive, review-only artifacts, all outside the candidate tree: a fetched
`refs/remotes/origin/pr-248-head` ref, a detached worktree under the session scratchpad, a
copied gitignored `.env`, a `uv`-created `.venv`, and the five harnesses in
`scratchpad/adv248/`. The candidate worktree reported `git status --porcelain` empty at the
start and at the end of the review. The owner checkout `C:\Users\steph\TDL` was never modified
and remains on `main` @ `2e6bf9c9…`.

**Environment.** Windows 11 (NTFS) · Python 3.13.5 · pytest 9.0.2 · uv ·
`uv run --env-file .env pytest` · vault junction `C:\Users\steph\TDL\vault` present ·
harnesses run with `PYTHONPATH=<worktree> -p no:randomly -p no:cacheprovider --no-cov -s`.

---

## Appendix A — Anti-loop completeness sweep

Performed before returning, as required:

- **Every finding's shared clause was traced to every route it governs.** C-1 → all 29 mint
  rows, with the 4 pre-genesis-reachable ones executed and the rest dispositioned by
  reachability. M-1 → all multi-event write sets, via an exhaustive grep for same-transaction
  joins (exactly two exist; the third is missing).
- **Every mandatory attack family is marked PASS / FAIL / PARTIAL with evidence** in §5. No
  family is unmarked.
- **Structural twins searched for both defects.** C-1's twin is the post-genesis catalogue
  claim (PASS). M-1's twins are the two joins this PR added (PASS) plus OR-022 (FAIL,
  inspection-confirmed).
- **Nothing is held back for a later pass.** Every finding I hold, blocking or not, is in §3
  or §6, including observations that are merely fragile rather than wrong.
- **No finding was manufactured.** Nine distinct attacks failed safely and are listed as such
  in §7. Where the implementation held, I say so plainly.
- **Prior critical invariants rechecked at this exact head** by re-executing the prior
  reproducers rather than inheriting the remediation record's claims.

---

## Appendix B — Reproducer sources

Both harnesses import the candidate's own test helpers and must be run with `PYTHONPATH` set
to the worktree root, placed **outside** the candidate tree.

### B.1 — C-1: pre-genesis catalogue-identity squat

```python
"""C-1: a pre-genesis authority registration permanently bricks one-time W11 genesis."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_system.discovery.runtime import replay_discovery
from research_system.errors import IntegrityError
from research_system.ids import new_id

import tests.research_system.integration.test_wp6_6_discovery_runtime as T


def _cmd(command_type, target, version, payload, actor=None):
    return {
        "command_id": new_id("command"),
        "command_type": command_type,
        "actor_id": actor or T.ACTOR_ID,
        "authority_grant_id": T.GRANT_ID,
        "idempotency_key": f"advB:{command_type}:{target}:{version}",
        "target_stream_id": target,
        "expected_stream_version": version,
        "payload": payload,
    }


def _rubric_on(stream_id: str) -> dict:
    from research_system.discovery.assay_authority import content_sha256 as assay_content_sha256

    rubric = json.loads((T.REPO_ROOT / T.ASSAY_RUBRIC_PATH).read_bytes())
    rubric["record_id"] = stream_id
    rubric["created_by_actor_id"] = T.ASSAY_AUTHORITY_ACTORS[4]
    rubric.pop("content_hash", None)
    rubric["content_hash"] = assay_content_sha256(rubric)
    return rubric


def test_adv_pregenesis_squat_permanently_bricks_genesis(tmp_path: Path) -> None:
    runtime = T._runtime(tmp_path)
    assert tuple(runtime.ledger.iter_events()) == ()

    receipt = runtime.submit(
        _cmd(
            "RegisterAssayRubricContent",
            T.CATALOGUE_STREAM_ID,
            0,
            {
                "row_id": "OR-101",
                "authority_kind": "assay_bar",
                "content": _rubric_on(T.CATALOGUE_STREAM_ID),
                "authority_file_path": T.ASSAY_RUBRIC_PATH,
            },
            actor=T.ASSAY_AUTHORITY_ACTORS[4],
        )
    )
    print("squat receipt:", receipt.status)                       # accepted   <-- MUST reject
    after = tuple(runtime.ledger.iter_events())
    projection = replay_discovery(after)
    print("ledger STILL REPLAYS. catalogue =", projection["catalogue"])
    print("authority_streams =", projection["authority_streams"])

    g0 = runtime.submit(T._genesis())
    print("genesis expected_version=0 ->", g0.status, g0.reason_code)   # conflict

    g1 = T._genesis()
    g1["expected_stream_version"] = 1
    g1["command_id"] = new_id("command")
    g1["idempotency_key"] = "advB:genesis:v1"
    with pytest.raises(IntegrityError) as exc:                    # <-- capability is now dead
        runtime.submit(g1)
    print("genesis expected_version=1 -> PERMANENTLY BLOCKED:", exc.value)

    cand = "obj_019fed25-b33e-7740-b280-00000000b001"
    with pytest.raises(IntegrityError) as exc:
        runtime.submit(
            _cmd("RegisterCandidate", cand, 0, {
                "candidate_id": cand, "revision": 1, "content_sha256": "0" * 64,
                "source_observation_refs": ["obj_019fed25-b33e-7740-b280-00000000b002"],
                "title": "post-brick",
            })
        )
    print("candidate registration ->", exc.value)
```

The OR-110 twin is identical with
`("RegisterDossierExpectedSetContent", {"row_id": "OR-110", "authority_kind":
"dossier_expected_set", "subject": T._sealed_authority_subject(T.DOSSIER_AUTHORITY_PATH)})`.
The OR-102 twin registers a legitimate rubric on its own stream first, then targets
`T.CATALOGUE_STREAM_ID` with `row_id: "OR-102"`.

### B.2 — M-1: OR-019 canonical operational closure, truncated at the transaction boundary

```python
"""M-1: OR-019 never joins its canonical operational closure to the Discovery transaction."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from research_system.discovery.runtime import replay_discovery
from research_system.errors import IntegrityError

import tests.research_system.integration.test_wp6_6_discovery_runtime as T


def _partial_prefix(tmp_path: Path):
    T.test_spike_positive_lifecycle_reaches_reviewed_atomically_and_without_provider_execution(
        tmp_path, "PARTIAL", "OR-019"
    )
    events = tuple(deepcopy(e) for e in T._HARNESSES[tmp_path].ledger.iter_events())
    last = max(i for i, e in enumerate(events) if e["event_type"] == "CandidateSpikePartialLinked")
    return tuple(deepcopy(e) for e in events[: last + 1])          # legitimate mid-flight EOF


@pytest.mark.parametrize("victim", ["LeaseReleased", "PartialOutcomeRecorded"])
def test_adv_e_delete_canonical_operational_closure_at_boundary(tmp_path: Path, victim: str) -> None:
    prefix = _partial_prefix(tmp_path)
    kept = tuple(e for e in prefix if e["event_type"] != victim)
    assert len(kept) == len(prefix) - 1
    attacked = T._fully_reindex_and_rehash_events(kept)             # full semantic rehash
    state = replay_discovery(attacked)                              # <-- MUST raise after the fix
    spike = state["spikes"][next(iter(state["spikes"]))]
    print(f"*** {victim} DELETION AT BOUNDARY ACCEPTED ***")
    print("  attempt_status:", spike.get("attempt_status"), "lease_status:", spike.get("lease_status"))
    raise AssertionError(f"replay accepted a ledger with canonical {victim} removed")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("holder_actor_id", "act_019fed25-b33e-7740-b280-00000000dead"),   # rejected today
        ("release_reason", "operator_override"),                            # ACCEPTED today
        ("observed_at", "2099-01-01T00:00:00Z"),                            # ACCEPTED today
    ],
)
def test_adv_e_lease_released_payload_substitution_at_boundary(tmp_path, field, value) -> None:
    prefix = _partial_prefix(tmp_path)
    attacked = tuple(deepcopy(e) for e in prefix)
    hit = 0
    for event in attacked:
        if event["event_type"] == "LeaseReleased":
            event["payload"][field] = value
            hit += 1
    assert hit == 1
    state = replay_discovery(T._fully_reindex_and_rehash_events(attacked))
    released = next(e for e in T._fully_reindex_and_rehash_events(attacked)
                    if e["event_type"] == "LeaseReleased")
    print(f"*** LeaseReleased.{field} SUBSTITUTION AT BOUNDARY ACCEPTED ***", released["payload"])
    raise AssertionError(f"replay accepted substituted LeaseReleased.{field}")
```

The `PartialOutcomeRecorded.stop_cause` variant is the same shape, substituting
`event["payload"]["stop_cause"] = "operator_stop"`.

---

## Final statement

**REWORK REQUIRED** — exact head `5c48cc73c5f4f7706049087b4447684330d47c88` /
tree `0a565bc029d0ef5ce7c2cfe1c016a306f7fb55a5` carries **one Critical (C-1)** and
**one Major (M-1)** finding plus seven non-blocking observations.

All five prior blocking findings and all seven prior appendix items are closed, and the three
executable ones were re-verified by the reviewer at this head. The review matrix is complete:
every mandatory attack family is explicitly dispositioned, protected identities are verified
by direct byte reads in both checkouts, and all reported results were executed here. No
further review pass is needed before remediation.

**No merge recommendation, owner acceptance, integration authorization, or CodeRabbit
disposition is expressed or implied by this document.**
