# WP6.6 / KAN-59 — External Adversarial Review — PR #247

**Status: REWORK REQUIRED**
**Date:** 2026-08-12
**Reviewer:** independent adversarial pass, read-only, fresh detached worktree
**Subject:** `stephendor/TDL` PR #247, branch `codex/wp6-6-adversarial-remediation`
**Head:** `f27555aa0fa82a90a0910ec6a67904939d2e6298`
**Tree:** `6aa8e0b080ee5f05ca0720178f3be1eec8af52ab`

> This document is the complete review record. It is written to be actionable by a
> remediation agent without access to the review session. Every finding carries an
> exact source location, an executable reproducer (source embedded in Appendix C),
> the observed vs expected behaviour, and the owning correction boundary.

---

## 0. How to use this document

1. Read §2 (remediation checklist) first — it is the ordered work list.
2. Work findings in order **R1 → R4 → R2 → R3 → R5**. R1 is the only Critical.
3. Before touching anything, read §6 (**do-not-regress list**). Six previously-closed
   findings are verified closed at this head; the fixes for R1 must not weaken them.
4. Rebuild the reproducers from Appendix C. They are the acceptance evidence.
5. §7 records what was *not* proven. Do not treat green tests as coverage of it.

---

## 1. Verdict

**REWORK REQUIRED** — 5 root-cause finding groups, 7 mandatory appendix items.

The remediation in this PR is substantial and genuinely responsive. All six findings from
the prior review (PR #244) are **closed**, verified by re-running the original reproducers
unmodified. The added hardening goes well beyond what was asked: scorecard axis binding,
Spike execution-authority relations bound to live resource content hashes, canonical
artefact reference resolution, staleness evidence predicates, closed cancellation subjects,
scoped receipt idempotency, and a typed `DiscoveryLedgerReplayError`.

However:

- The **root cause of the most severe prior finding (F-1) survives in three unremediated
  variants**, two of which were executed to a permanently bricked capability.
- A second prior root-cause class (preparation-only authority guards) **recurs in the
  operational lane at OR-017**.
- The capability's **headline deliverable — "admit the real TDA-scale dossier" — now has
  zero executed evidence in any default environment**, a regression introduced by this PR.

---

## 2. Remediation checklist (ordered)

| # | Finding | Severity | One-line action |
|---|---------|----------|-----------------|
| 1 | **R1-a** | Critical | Guard `target_stream_id` at OR-103/OR-104 (`ObserveW11AuthorityFile`, assay_bar) |
| 2 | **R1-b** | Critical | Remove the `status != "stale"` exemption on the OR-101 identity guard |
| 3 | **R1-c** | Major | Guard `target_stream_id` for `action == "observe"` in `_prepare_authority` (OR-111/OR-117) |
| 4 | **R1-*** | Critical | Replace per-branch enumeration with **one unconditional** identity fence at the submit seam |
| 5 | **R4** | Major | Make the real-dossier suite run by default (CI env or committed fixture root); fail, don't skip |
| 6 | **R2** | Major | Re-derive Attempt/Lease from the operational ledger in the `SpikeStarted` replay branch |
| 7 | **R3** | Major | Make `dossier.py` use `canonical_bytes`; widen the `_submit_authorized` except clause |
| 8 | **R5** | Major | Implement OR-002 (+OR-030) or file an explicit owner-visible deferral + coverage gate |
| 9 | App. 1–7 | — | See §5; all are mandatory remediation inputs |

---

## 3. Exact subject verification

| Check | Required | Observed | Result |
|---|---|---|---|
| PR head | `f27555aa…` | `refs/pull/247/head` → `f27555aa0fa82a90a0910ec6a67904939d2e6298` | MATCH |
| Branch head | same | `codex/wp6-6-adversarial-remediation` → same | MATCH |
| Tree | `6aa8e0b0…` | `6aa8e0b080ee5f05ca0720178f3be1eec8af52ab` | MATCH |
| Live-main ancestor | `2e6bf9c9…` | `git merge-base --is-ancestor` → 0 | MATCH |
| `origin/main` ancestor | — | `origin/main = 2e6bf9c9…`, ancestor → 0 | MATCH |
| KAN-75 ancestor | `26df871` | ancestor → 0 | MATCH |

**Clean worktree.** Fresh detached worktree; `git status --porcelain` empty before and after.
Primary working directory `C:\Users\steph\TDL` untouched (`main` @ `2e6bf9c9…`, clean).

**W11 catalogue identity.**

```
blob   8d58818540e04859f929d4b04c71e4cfa0512554
path   .research-system/evals/expected/w11-portfolio-discovery-v1.json
size   136229
sha256 7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80
rows   81, exact ordered match to OR-001..OR-041 + OR-101..OR-140, no duplicates
```

**Protected material** (tree-object comparison against accepted KAN-75 `26df871`):

```
UNCHANGED  .research-system/contracts/w11        c61f639fc70fec63506d38939b33e72425d78888
UNCHANGED  .research-system/contracts/wp6-4      0847965e3595c56da74ca808022719d9198df1fa
UNCHANGED  .research-system/evals/expected       ac7597ee9ac57ce1620fe089bd0f7f25ca3c6375
```

`git diff live-main..head` over those paths plus `.research-system/schemas` is **empty**.

---

## 4. Blocking findings

### R1 — CRITICAL — The global immutable-identity contract is not applied at every W11 authority-stream admission point

> This is the **unremediated remainder of prior finding F-1**.

The fix correctly routed `_prepare_candidate`, `RequestAssay`, `RegisterSpikePlan`, the
decision/review minting sites, OR-101/102 (non-stale), OR-105 and OR-107 through
`_discovery_identity_exists`, and added `claim_authority_stream` on the replay side.

But `claim_authority_stream` applies the global check to **every** newly seen authority
stream, while preparation still leaves **three** admission points unguarded. Preparation
therefore accepts histories replay rejects.

**Violated invariant:** W11 immutable-identity closure; preparation/replay equivalence
("preparation and replay must accept the same semantic histories").

**Replay side (always enforces):** `research_system/discovery/runtime.py:1084-1095`

```python
def claim_authority_stream(identity: Any, kind: Any) -> None:
    existing = state["authority_streams"].get(identity)
    if existing is None:
        if aggregate_identity_exists(identity):          # <-- unconditional
            raise IntegrityError("W11 authority stream identity collision")
        state["authority_streams"][identity] = kind
    elif existing != kind:
        raise IntegrityError("W11 authority stream identity collision")
```

---

#### R1-a — OR-103 / OR-104 `ObserveW11AuthorityFile` — **EXECUTED, 2 commands deep**

**Source:** `research_system/discovery/runtime.py`

| Row | Line | Guard present? |
|---|---|---|
| OR-101 / OR-102 (register) | `:3116-3126` | yes (but see R1-b) |
| **OR-103 / OR-104 (observe)** | `:3147-3168` | **NONE — and no constraint on `target_stream_id` at all** |
| OR-105 (request review) | `:3199-3206` | yes |
| OR-107 (propose) | `:3325-3330` | yes |

**Reproduction:** Appendix C.1. Genesis → ingest Candidate `CAND1` → OR-101 register rubric
(normal stream) → OR-103 `ObserveW11AuthorityFile` with `target_stream_id = CAND1`.

**Observed:**

```
bar status after OR-101: content_registered
OR-103 receipt: accepted
appended: [('W11AuthorityFileObserved', 'obj_019fed25-b33e-7740-b280-6f661aaef102')]
LEDGER NO LONGER REPLAYS: IntegrityError - W11 authority stream identity collision
SUBSEQUENT COMMAND FAILS: DiscoveryLedgerReplayError - persisted Discovery ledger failed replay before command preparation
```

**Expected:** preparation rejects with zero mutation, exactly as OR-101/105/107 already do.

**Blast radius:** total and unrecoverable. `_submit_authorized` replays the whole ledger
before preparing any command, so every subsequent public command fails permanently.
Genesis is one-time and the ledger append-only — there is no in-capability recovery.

---

#### R1-b — OR-101 stale-successor registration — **EXECUTED**

**Source:** `research_system/discovery/runtime.py:3124`

```python
or (state.get("status") != "stale" and _discovery_identity_exists(projection, command.target_stream_id))
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ guard is conditioned OFF whenever the bar is stale
```

Replay's `claim_authority_stream` has no such exemption for a **new** identity.

**Reproduction:** Appendix C.2. Genesis → ingest `CAND1` → accept bar → ingest a later Scout
observation carrying `assay-bar-change:rubric:<accepted>:<new>` → OR-109 staleness →
OR-101 successor rubric with `record_id = CAND1`.

**Observed:**

```
OR-109 receipt: accepted        bar status after OR-109: stale
OR-101 successor receipt: accepted
events appended: 1 ['AssayRubricContentRegistered']
stream written: ['obj_019fed25-b33e-7740-b280-6f661aaee002']   # a live Candidate
LEDGER NO LONGER REPLAYS: IntegrityError - W11 authority stream identity collision
SUBSEQUENT COMMAND FAILS: DiscoveryLedgerReplayError
```

**Expected:** the exemption should cover only *re-registration on the already-claimed
authority stream*, not any new identity. (Note `claim_authority_stream` already permits
re-claim when `existing == kind` — that is the correct shape; preparation should mirror it.)

---

#### R1-c — OR-111 / OR-117 `ObserveW11AuthorityFile` — **inspection only; executed twin is R1-a**

**Source:** `research_system/discovery/runtime.py:2870-2881`

```python
if action in {"register", "request_review", "propose"} and _discovery_identity_exists(
    projection, command.target_stream_id
):
    raise IntegrityError("W11 authority stream identity collision")
current_authority = projection["authorities"].get(kind, {})
if action == "record_review" and command.target_stream_id != current_authority.get("review_id"):
    raise IntegrityError("W11 authority review stream mismatch")
if action == "propose" and command.target_stream_id != payload.get("decision_id"):
    raise IntegrityError("W11 authority decision stream mismatch")
if action == "resolve" and command.target_stream_id != payload.get("decision_id"):
    raise IntegrityError("W11 authority decision stream mismatch")
```

`observe` is excluded from the identity guard **and** carries no target-stream constraint —
structurally identical to R1-a. No separate reproducer was built because reaching OR-111
requires the dossier-authority chain, which sits inside the suite disabled by **R4**.

---

#### R1 — required correction (owning boundary: `research_system/discovery/runtime.py`, preparation seam)

Make the global identity contract **unconditional at a single choke point** rather than
enumerated per row. Suggested shape — resolve once, immediately after
`_require_candidate_target` in `_submit_authorized`:

```python
self._require_candidate_target(command, projection)
self._require_admissible_target(command, projection)   # NEW: one fence, all commands
```

where `_require_admissible_target` rejects when `_discovery_identity_exists(projection,
command.target_stream_id)` is true **unless** the command is explicitly advancing an
already-claimed stream of the same aggregate kind (assay/spike/review/decision advancement,
authority-stream re-entry where `authority_streams[target] == kind`).

The current per-branch enumeration has now failed **twice** with two different rows escaping
it. An enumeration is the wrong shape for this invariant.

#### R1 — decisive regression test

A single parametrized public-seam test over **every** `_DISCOVERY_COMMAND_TYPES` entry ×
**every** namespace in `_DISCOVERY_IDENTITY_COLLECTIONS` (plus the catalogue stream),
asserting for each cell:

1. the submit is rejected;
2. `tuple(runtime.ledger.iter_events())` is unchanged (zero mutation);
3. `replay_discovery(events)` still succeeds afterwards.

> The existing `test_global_identity_contract_names_every_discovery_namespace` asserts the
> *contract lists* every namespace but never drives every command through it — which is
> exactly why R1-a and R1-b survived this PR.

---

### R2 — MAJOR — OR-017 does not re-derive the operational Attempt/Lease at replay

**Violated invariant:** Spike authorization and execution must come from replaying the exact
locked operational ledger at **OR-015, OR-016 and OR-017**. OR-015/OR-016 are now correctly
replay-bound (`runtime.py:1979-2054` — resolves the resource through
`replay_control_plane(operational_events)` and requires `status == "active"`).
**OR-017 is not.**

**Source:** `research_system/discovery/runtime.py:2055-2080`

```python
elif event_type == "SpikeStarted":
    spike = state["spikes"].get(payload.get("spike_id"))
    attempt_id = required_string("attempt_id")
    lease_id = required_string("lease_id")
    if (
        not isinstance(spike, dict)
        or spike.get("status") != "authorized"
        or not _spike_execution_ids_available(state["spikes"], payload.get("spike_id"), attempt_id, lease_id)
        or payload.get("execution_authority_relation") != spike.get("execution_authority_relation")
        or spike.get("execution_authority_relation", {}).get("resource_ref", {}).get("id")
        != payload.get("resource_grant_id")
    ):
        raise IntegrityError("invalid Spike start")
    spike.update(
        status="running",
        attempt_id=attempt_id,
        attempt_sha256=required_string("attempt_sha256"),   # <-- taken on trust
        lease_id=lease_id,
        lease_sha256=required_string("lease_sha256"),       # <-- taken on trust
        lease_status="active",
    )
```

Preparation (`_valid_live_spike_lease`, `runtime.py:4266+`) verifies **eight** properties
that replay does not re-derive:

1. Attempt exists and `status == "running"`
2. `attempt_sha256 == sha256(canonical_bytes(attempt))`
3. `attempt.lease_id == lease_id`
4. Lease exists and `status == "active"`
5. `lease.attempt_id == attempt_id`
6. `lease.holder_actor_id == command.actor_id`
7. `lease.expires_at > now`
8. `payload.resource_grant_id == lease.resource_grant_id`

**Reproduction:** Appendix C.3. Drive the real positive Spike lifecycle, truncate at the
OR-017 transaction boundary (a legitimate mid-flight EOF), substitute the Attempt/Lease
identities and digests, then fully reindex `global_position`, recompute
`transaction_index`/`transaction_count`, and rehash the whole chain.

**Observed:**

```
BASELINE attempt/lease: att_01978abc-7203-…  els_01978abc-7206-…
REPLAY ACCEPTED A FABRICATED OPERATIONAL ATTEMPT/LEASE AT OR-017
  spike status   : running
  attempt_id     : att_019fed25-b33e-7740-b280-0000deadbeef
  attempt_sha256 : aaaa…aaaa
  lease_id       : els_019fed25-b33e-7740-b280-0000deadbeef
  lease_sha256   : bbbb…bbbb
  fabricated ids present anywhere in ledger: False False
```

**Expected:** replay resolves the Attempt and Lease from `operational_events` at that ledger
position and rejects any that are absent, not running/active, not mutually bound, expired,
or not held by the acting actor — mirroring what OR-015/OR-016 already do.

**Blast radius:** the durable record can attribute Spike execution to an Attempt and Lease
that never existed, defeating resource accounting and lease-holder attribution.
`lease_sha256` propagates into `_spike_cancellation_matches` (`lease_ref`), so fabricated
operational identity flows into cancellation evidence.

**Required correction:** in the `SpikeStarted` replay branch, resolve `attempt_id`/`lease_id`
through `replay_control_plane(operational_events)` and re-apply the `_valid_live_spike_lease`
predicate set, with `event["actor_id"]` as the required lease holder.

**Honest caveat:** my full-chain variant (carrying the fabrication through to a reviewed PASS
verdict) was rejected downstream at `invalid Candidate promotion request`. That is a
limitation of my crude digest propagation, **not a proven defence** — the verdict-stage joins
are self-consistent with whatever `SpikeStarted` recorded.

---

### R3 — MAJOR — Preparation and replay use different canonical encoders for dossier semantic hashes

**Violated invariant:** preparation and replay must accept the same semantic histories.

**Source:**

| Side | Function | Location | Behaviour |
|---|---|---|---|
| Prepare | `canonical_dossier_hash` | `research_system/discovery/dossier.py:76` | permissive `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)` |
| Replay | `sha256_hex(canonical_bytes(...))` | `runtime.py:1559` (`PortfolioObjectRegistered`), `:1584` (`ScopeDefinitionRegistered`), `:1669` (dossier relationship closure) | **P0 canonical** — rejects floats, non-ASCII object keys, ints outside ±2⁵³−1 (`research_system/canonical.py:10-30`) |

**Executed evidence:**

```
canonical_dossier_hash({'axis_id':'x','value':0.5}) -> 5e4677b6d4ffe33762e23ea99749fac763420bb0f112154f87d916060c092aff
canonical_bytes(same)  -> ValueError: P0 canonical JSON rejects floating-point values

canonical_dossier_hash({'kéy':1}) -> dbc02d34bef777dbc83f69006e725960bc5a4480f0d760b4ae6a5ce167a0dc20
canonical_bytes(same)  -> ValueError: P0 canonical JSON requires ASCII object keys
```

**Impact:** any accepted expected set whose object/scope/edge blueprints or relationship
members contain a float, a non-ASCII object key, or an unsafe integer is admitted at
preparation and then makes the ledger unreplayable — R1's failure mode via a different
predicate. Worse, it surfaces as a raw `ValueError` escaping `replay_discovery`, so it
**bypasses the new `DiscoveryLedgerReplayError` wrapper** (which catches only
`IntegrityError`) and propagates as an untyped exception.

**Honest scope:** all four accepted WP6.6 authority files were verified clean of floats,
non-ASCII keys and unsafe integers, so this is **not attacker-reachable at this head** — the
trigger is future owner-accepted content, not an attacker-chosen value. It is reported as
blocking because it is a live divergence in the exact invariant family under review, and
because the two encoders are silently interchangeable to a reader.

**Required correction:**

1. Make `dossier.py` use `canonical_bytes` (or make `canonical_dossier_hash` delegate to it),
   so admission fails closed at preparation on any value replay cannot represent.
2. Widen the `_submit_authorized` wrapper from `except IntegrityError` to
   `except (IntegrityError, ValueError, TypeError)` so encoder faults surface as
   `DiscoveryLedgerReplayError`.

---

### R4 — MAJOR (coverage) — The real TDA-scale dossier admission has no executed evidence in any default environment

**Violated invariant:** the capability statement's headline deliverable — *"admit the real
TDA-scale dossier"*. And: passing schemas or fixtures do not establish the capability.

**Source:** `tests/research_system/integration/test_wp6_6_dossier_admission.py:50-58`.
This PR changed the gate:

```python
# BEFORE (PR #244)
TDA_RUNTIME_ROOT = Path(os.environ.get("TDL_REPOSITORY_ROOT", Path.home() / "TDL"))
...
pytest.mark.skipif(not VAULT.exists() or not CONTRACT_ROOT.exists(), ...)

# AFTER (PR #247)
_TDA_RUNTIME_ROOT_VALUE = os.environ.get("TDL_REPOSITORY_ROOT")
TDA_RUNTIME_ROOT = Path(_TDA_RUNTIME_ROOT_VALUE) if _TDA_RUNTIME_ROOT_VALUE else Path("__unconfigured_tdl_root__")
...
pytest.mark.skipif(not _TDA_RUNTIME_ROOT_VALUE or not VAULT.exists() or not CONTRACT_ROOT.exists(), ...)
```

`TDL_REPOSITORY_ROOT` is **not** set in the repo `.env`, and **not** set in
`.github/workflows/ci.yml` (whose only change here is `fetch-depth: 0`). Nothing fails when
it is absent.

**Executed evidence — both directions, same worktree, same commit:**

```
uv run --env-file .env pytest …/test_wp6_6_dossier_admission.py -rs
  → 32 skipped in 0.43s   ("real TDA dossier roots are not configured in this environment")

TDL_REPOSITORY_ROOT="C:/Users/steph/TDL" uv run --env-file .env pytest …/test_wp6_6_dossier_admission.py
  → 32 passed in 37.93s
```

At PR #244 head, in this identical environment, the same suite **ran and passed (31 tests)**.
The change converted working evidence into a silent skip.

**Impact:** review families 11 (dossier authority and admission), 12 (registered paths and
physical identity: traversal, symlink, junction, nested reparse, hardlink, root replacement,
ABA-during-read) and half of 13 (projection/receipt equivalence) have **zero default
evidence**. Neither CI nor the owner's default invocation exercises the deliverable.

**Required correction:** make the real-dossier proof non-optional in at least one committed,
reproducible invocation — set `TDL_REPOSITORY_ROOT`/`TDA_VAULT_ROOT` in CI, or vendor a
committed fixture root — and make an unconfigured environment **fail** rather than skip when
the capability is being certified.

---

### R5 — MAJOR — OR-002 `SupersedeDiscoveryRecord` has no production route at all

**Violated invariant:** an absent producer, reducer, projection, replay join, terminal state
or public route is a finding.

**Accepted catalogue defines OR-002 as a Candidate-lifecycle row:**

```
command_type        : SupersedeDiscoveryRecord
eligible_profile    : Portfolio Steward
logical_key         : supersede-discovery-record/candidate
ordered_events      : ['E:candidate-superseded']
complete_write_set  : ['`E:candidate-superseded`', 'predecessor Candidate + project index']
reducer             : U:candidate
projection_targets  : ['P:candidate']
preconditions       : ['Replacement current; predecessor not terminally superseded']
positive_test_id    : W11-T01-OR-002
```

A repo-wide search for `SupersedeDiscoveryRecord` / `CandidateSuperseded` /
`candidate-superseded` matches **one** file — `tools/verify_w11_materialization.py`, a
design-side helper. Nothing in `research_system/`: no entry in `_DISCOVERY_COMMAND_TYPES`,
no schema binding, no preparer, no replay branch, no `superseded` terminal Candidate state.
The Candidate state machine implements `AssaySuperseded` and `SpikeSuperseded` but has no
Candidate-record supersession at all.

`OR-030 IngestDiscoveryAnnotation` (`reducer: U:annotation`, `projection: P:annotation-audit`)
is absent on the same basis, though it sits in the annotation-evidence lane rather than the
Candidate lifecycle.

**Distinguish from correct absence:** OR-031/032/033 and OR-122–OR-139 are legacy-inventory,
transition-mapping, cutover-closure, ownership-transition and path-cutover rows — correctly
unimplemented, and their absence is **affirmative evidence** for the boundary family.
OR-002 is not in that class.

**Required correction:** either implement the OR-002 route with its terminal Candidate state
and replay join, or record an explicit owner-visible deferral binding OR-002 (and OR-030) to
a named later work package — **and** add a coverage gate asserting every in-scope W11 row has
a production route. No such gate exists today.

---

## 5. Non-blocking appendix (mandatory remediation inputs)

| # | Observation | Why it matters | Minimal disposition |
|---|---|---|---|
| 1 | **`value_type: "number"` axes are unusable.** `_assay_scorecard_matches` (`runtime.py:488-495`) accepts `isinstance(value, (int, float))` for `"number"`, but `canonical_bytes` rejects every non-integer — a number-valued scorecard can never be hashed. Fails as a bare `ValueError` out of `submit()`, not a governed `IntegrityError`. | A declared axis type is dead; attempting it produces an ungoverned exception. | Drop `"number"` from the accepted rubric contract, or use a scaled-integer representation. Either way convert the failure to `IntegrityError`. |
| 2 | **`allowed_set` / `bounds` / `integer` axis validation is unexercised in production.** The accepted rubric declares exactly one axis (`identity`, boolean gate, required). All numeric-bounds logic is reachable only from test fixtures. | Risk of being mistaken for exercised behaviour. | State explicitly in the acceptance record. |
| 3 | **A preparation placeholder is persisted into durable authority bytes.** `_prepare_authority` sets `transition_payload["transaction_id"] = "pending-ledger-transaction"` (`runtime.py:2963-2966`); `persisted_payload` writes that literal into the durable `DossierExpectedSetAccepted` / `PathRegistrationAccepted` shadow. Replay overwrites it before use. | The durable record contains a value false on its face. | Omit the key at preparation and let replay inject it, or rename to `transaction_id_pending`. |
| 4 | **Preparer routing keys on caller-controlled payload shape.** `_submit_authorized` dispatches on `"assay_id" in payload`, `"spike_id" in payload`, `payload["authority_kind"]`. Safe today only because each preparer re-validates `row_id`. | Fragile; one preparer forgetting the re-check becomes a routing exploit. | Derive the route from the resolved command binding, not payload key presence. |
| 5 | **Two parallel reducers over one ledger.** `_operational_events()` excludes `_ARTEFACT_EVENT_TYPES` from the control-plane replay used by `_valid_live_spike_lease` / `_live_spike_operational_pair`, while `replay_discovery` builds a separate `canonical_artefact_streams` projection via `reduce_artefact`. | Latent drift surface between two views of one ledger. | Document the partition invariant; add a test asserting the two partitions are disjoint and exhaustive. |
| 6 | **OR-001 and OR-140 carry no `row_id` binding.** `RegisterCandidate`'s payload schema forbids `row_id` entirely; genesis is untagged. Every other implemented row is row-bound. | Breaks uniform row traceability. | Tag them, or record why they are exempt. |
| 7 | **`pytest.mark.integration` is unregistered**, emitting `PytestUnknownMarkWarning` on every run. (Separately: repo-wide coverage config reports `TOTAL 0%` — cosmetic.) | Noise that hides real warnings. | One line in `pyproject.toml` markers. |

---

## 6. Do-not-regress list — six prior findings verified CLOSED at this head

These were re-tested with the **original PR #244 reproducers, unmodified**. Any R1 fix must
keep all six closed.

| Prior ID | Attack | Result at `f27555aa…` |
|---|---|---|
| F-1 | `RegisterCandidate` squats a live source-observation identity | `Candidate identity collision`, zero mutation, ledger still replays |
| F-2 | `RequestAssay` mints an Assay on the W11 catalogue genesis identity | `Discovery lifecycle target is outside authorized Candidate` |
| F-3 | `RequestAssay` writes to a foreign Candidate's stream under a grant scoped elsewhere | `Discovery lifecycle target is outside authorized Candidate` |
| F-4 | Whole Assay-bar chain deleted, ledger reindexed/recounted/rehashed (17 → 8 events) | `invalid Assay request transition` |
| F-5 | Fabricated `assay_bar_acceptance_sha256` | `invalid Assay request transition` |
| F-6 | Rogue producer scores the Assay | `invalid Assay score transition` |

Key mechanisms that deliver these — do not weaken:

- `_discovery_identity_exists` + `_DISCOVERY_IDENTITY_COLLECTIONS` (`runtime.py:341-357`)
- `_require_candidate_target` (`runtime.py:2575-2620`)
- `_current_assay_bar_matches` called from replay's `AssayRequested`, `AssayScored`,
  `AssayPartialRecorded`

---

## 7. Coverage ledger

### 7a. Review families

| # | Family | Result |
|---|---|---|
| 1 | Genesis and accepted authority | **PASS** |
| 2 | Current command authority | **PASS** |
| 3 | Immutable identity closure | **FAIL** — R1 |
| 4 | Producer and schema binding | **PASS** |
| 5 | Candidate lifecycle | **PARTIAL** — R5 |
| 6 | Assay lifecycle | **PARTIAL** — Appendix 1 |
| 7 | Spike lifecycle | **PASS** |
| 8 | Operational cross-ledger authority | **FAIL** — R2 |
| 9 | Transaction, receipt, recovery | **PASS** |
| 10 | Semantic replay equivalence | **FAIL** — R1, R2, R3 |
| 11 | Dossier authority and admission | **FAIL** — R4 |
| 12 | Registered paths and physical identity | **FAIL** — R4 |
| 13 | Projection and receipt equivalence | **PARTIAL** — dossier half gated by R4 |
| 14 | Boundary enforcement | **PASS** |

Family 14 detail: only external process invocation is read-only `git rev-parse` / `git show`
for authority-file identity (`runtime.py:2912-2932`, `:3462-3483`). No network imports, no
dispatch, no result promotion. `dispatchable: False` / `provider_execution: "forbidden"` /
`execution_authorized is not False` asserted at `dossier.py:98,104,391` and
`authority.py:100`. Migration/cutover rows deliberately unimplemented.

### 7b. W11 row coverage — all 81 rows accounted for

| Class | Rows | Count | Status |
|---|---|---|---|
| Implemented and row-bound in `runtime.py` | OR-003–OR-029, OR-034–OR-041, OR-101–OR-121 | 56 | Reviewed |
| Implemented but carrying no `row_id` binding | OR-001, OR-140 | 2 | Appendix 6 |
| Correctly absent — outside the WP6.6 boundary | OR-031, OR-032, OR-033, OR-122–OR-139 | 21 | **PASS** |
| **Materially absent** — no route/producer/reducer/projection/replay join/terminal state | **OR-002**, OR-030 | 2 | **FAIL** — R5 |

---

## 8. Test evidence

All figures are from runs **executed by the reviewer** in the detached worktree at
`f27555aa…`. Nothing is reported on the author's behalf.

| Command | Result |
|---|---|
| `uv run --env-file .env pytest tests/…/test_wp6_6_discovery_runtime.py tests/…/test_wp6_6_discovery_authority.py tests/…/test_wp6_6_discovery_crash_recovery.py tests/…/test_wp6_6_dossier_admission.py tests/…/contracts/test_w11_expected_catalogue.py tests/…/unit/test_command_lifecycle.py tests/…/unit/test_schema_registry.py -q -p no:randomly --no-cov -rs` | **349 passed, 33 skipped, 603.45s** (32 real-dossier skips = R4; 1 `rfc3339-validator` absent) |
| `TDL_REPOSITORY_ROOT="C:/Users/steph/TDL" uv run --env-file .env pytest tests/…/test_wp6_6_dossier_admission.py -q --no-cov -rs` | **32 passed, 37.93s** |
| same without the env var | **32 skipped, 0.43s** |
| `pytest ../review247/test_adv247.py -k reg_ -s` (prior F-1…F-6) | **5 passed, 53.78s** |
| `pytest ../review247/test_adv247.py -k or017 -s` | **1 passed, 1 skipped, 131.35s** — R2 |
| `pytest ../review247/test_adv247_stale.py -s` | **1 passed, 18.86s** — R1-b |
| `pytest ../review247/test_adv247_observe.py -s` | **1 passed, 6.96s** — R1-a |

No timeouts. No unresolved executions.

---

## 9. Residual uncertainty

- **R1-c (OR-111 / OR-117) is inspection-only.** The source asymmetry is exact and the
  executed twin (R1-a) is the same code shape, but no independent reproducer was built —
  reaching OR-111 requires the dossier-authority chain gated by R4. Treat as
  unproven-but-structurally-identical.
- **R3 is unit-level.** The encoder divergence was proven and both call sites located; no
  end-to-end admission was constructed because the accepted authority content is clean. The
  end-to-end consequence is inferred from the identical mechanism proven in R1.
- **R2's downstream reach is unproven.** A fabricated Attempt/Lease was proven to survive to
  `running` at a legitimate EOF. The full-chain variant was rejected at the promotion
  relation; that does **not** establish that the promotion gate defends the invariant.
- **Concurrency.** All work was single-process. `CompositeWriterLock` spans the Discovery,
  authority and operational roots and the cross-process revocation test passes, but genuine
  parallel-writer races were not exercised.
- **Families 11/12 are proven only under a manually exported env var** (32 passed). The
  physical-path attacks were not independently re-derived; the candidate's own tests were
  relied on once unblocked. That is supporting evidence, not reviewer attack surface — and
  it is the direct consequence of R4.
- **Windows-only path semantics.** Junction/reparse behaviour exercised on NTFS / Windows 11
  only.
- No inference is drawn from the 349 passing tests to any behaviour not directly attacked.

---

## Appendix A — Review provenance

No edits, commits, pushes, or PR/Jira/external-review changes were made. CodeRabbit was
neither triggered nor polled. Nothing was merged and no owner acceptance is inferred.

Local, additive, review-only artifacts: a fetched `refs/remotes/origin/pr-247-review` ref,
a detached read-only worktree, a copied gitignored `.env`, and the harnesses in Appendix C
(written outside the candidate tree).

---

## Appendix B — Environment

```
Platform     Windows 11 (NTFS)
Python       3.13 via uv 0.11.29
Invocation   uv run --env-file .env pytest …
Vault        C:\Users\steph\TDL\vault  (junction, present)
Harness path harnesses placed OUTSIDE the candidate tree; run with
             PYTHONPATH=<worktree> pytest <harness> -p no:randomly -p no:cacheprovider --no-cov -s
```

---

## Appendix C — Reproducer source

These are the executable negatives. They import the candidate's own test helpers, so they
must be run with `PYTHONPATH` set to the worktree root and placed **outside** the candidate
tree.

### C.1 — R1-a: OR-103 observation on a live Candidate stream

```python
"""R1-a: unguarded authority-observation stream identity (OR-103/OR-104)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_system.discovery.runtime import replay_discovery
from research_system.errors import IntegrityError
from research_system.ids import new_id

import tests.research_system.integration.test_wp6_6_discovery_runtime as T

OBS1 = "obj_019fed25-b33e-7740-b280-6f661aaef101"
CAND1 = "obj_019fed25-b33e-7740-b280-6f661aaef102"


def _cmd(command_type, target, version, payload, actor=None):
    return {
        "command_id": new_id("command"),
        "command_type": command_type,
        "actor_id": actor or T.ACTOR_ID,
        "authority_grant_id": T.GRANT_ID,
        "idempotency_key": f"obsv:{command_type}:{target}:{version}",
        "target_stream_id": target,
        "expected_stream_version": version,
        "payload": payload,
    }


def _version(runtime, stream_id: str) -> int:
    return runtime.ledger.snapshot().stream_versions.get(stream_id, 0)


def test_adv_assay_bar_file_observation_can_target_a_live_candidate_stream(tmp_path: Path) -> None:
    runtime = T._runtime(tmp_path)
    runtime.submit(T._genesis())
    T._ingest_candidate(runtime, CAND1, observation_id=OBS1, title="Victim candidate")

    rubric_observer, scope_observer, requester, reviewer, author, proposer = T.ASSAY_AUTHORITY_ACTORS
    rubric = json.loads((T.REPO_ROOT / T.ASSAY_RUBRIC_PATH).read_bytes())
    rubric["created_by_actor_id"] = author

    runtime.submit(
        _cmd(
            "RegisterAssayRubricContent",
            rubric["record_id"],
            0,
            {
                "row_id": "OR-101",
                "authority_kind": "assay_bar",
                "content": rubric,
                "authority_file_path": T.ASSAY_RUBRIC_PATH,
            },
            actor=author,
        )
    )
    projection = replay_discovery(tuple(runtime.ledger.iter_events()))
    assert CAND1 in projection["candidates"]

    before = tuple(runtime.ledger.iter_events())
    try:
        receipt = runtime.submit(
            _cmd(
                "ObserveW11AuthorityFile",
                CAND1,  # a live Candidate identity, not an authority stream
                _version(runtime, CAND1),
                {"row_id": "OR-103", "authority_kind": "assay_bar"},
                actor=rubric_observer,
            )
        )
    except IntegrityError as exc:
        print("OR-103 on a Candidate stream REJECTED at preparation:", exc)
        assert tuple(runtime.ledger.iter_events()) == before
        pytest.skip(f"preparation rejected: {exc}")   # <-- DESIRED post-fix outcome

    after = tuple(runtime.ledger.iter_events())
    print("OR-103 receipt:", receipt.status)
    print("appended:", [(e["event_type"], e["stream_id"]) for e in after[len(before):]])
    with pytest.raises(IntegrityError) as err:
        replay_discovery(after)
    print("LEDGER NO LONGER REPLAYS:", type(err.value).__name__, "-", err.value)

    fresh = "obj_019fed25-b33e-7740-b280-6f661aaef199"
    with pytest.raises(IntegrityError) as later:
        runtime.submit(
            _cmd(
                "RegisterCandidate",
                fresh,
                0,
                {
                    "candidate_id": fresh,
                    "revision": 1,
                    "content_sha256": "0" * 64,
                    "source_observation_refs": [OBS1],
                    "title": "Any later candidate",
                },
            )
        )
    print("SUBSEQUENT COMMAND FAILS:", type(later.value).__name__, "-", later.value)
```

### C.2 — R1-b: OR-109 → OR-101 stale-successor identity squat

```python
"""R1-b: OR-109 -> OR-101 stale-successor identity closure."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from research_system.discovery.assay_authority import content_sha256 as assay_content_sha256
from research_system.discovery.runtime import replay_discovery
from research_system.errors import IntegrityError
from research_system.ids import new_id

import tests.research_system.integration.test_wp6_6_discovery_runtime as T

OBS1 = "obj_019fed25-b33e-7740-b280-6f661aaee001"
CAND1 = "obj_019fed25-b33e-7740-b280-6f661aaee002"
OBS2 = "obj_019fed25-b33e-7740-b280-6f661aaee003"
CAND2 = "obj_019fed25-b33e-7740-b280-6f661aaee004"
BAR_DECISION = "dec_019fed25-b33e-7740-b280-000000000107"


def _cmd(command_type, target, version, payload, actor=None):
    return {
        "command_id": new_id("command"),
        "command_type": command_type,
        "actor_id": actor or T.ACTOR_ID,
        "authority_grant_id": T.GRANT_ID,
        "idempotency_key": f"stale:{command_type}:{target}:{version}",
        "target_stream_id": target,
        "expected_stream_version": version,
        "payload": payload,
    }


def _version(runtime, stream_id: str) -> int:
    return runtime.ledger.snapshot().stream_versions.get(stream_id, 0)


def test_adv_stale_successor_rubric_can_squat_a_live_candidate_identity(tmp_path: Path) -> None:
    runtime = T._runtime(tmp_path)
    runtime.submit(T._genesis())
    T._ingest_candidate(runtime, CAND1, observation_id=OBS1, title="Victim candidate")
    bar_sha, producer_sha = T._accept_assay_bar(runtime)

    projection = replay_discovery(tuple(runtime.ledger.iter_events()))
    bar = projection["assay_bar_authority"]
    old_rubric_sha = bar["contents"]["rubric"]["content_sha256"]

    # 1. A later Scout observation objectively demonstrating the bar changed (OR-109 evidence).
    #    _ingest_candidate puts `title` into batch.matching_facts, which is what
    #    _assay_staleness_matches parses.
    fact = f"assay-bar-change:rubric:{old_rubric_sha}:{'c' * 64}"
    T._ingest_candidate(runtime, CAND2, observation_id=OBS2, title=fact)

    projection = replay_discovery(tuple(runtime.ledger.iter_events()))
    obs = projection["source_observations"][OBS2]
    trigger_ref = {"id": OBS2, "record_revision": obs["version"], "content_hash": obs["content_sha256"]}

    # 2. OR-109 staleness.
    runtime.submit(
        _cmd(
            "RecordAssayBarStaleness",
            BAR_DECISION,
            _version(runtime, BAR_DECISION),
            {
                "row_id": "OR-109",
                "authority_kind": "assay_bar",
                "acceptance_sha256": bar["acceptance_sha256"],
                "trigger_evidence_refs": [trigger_ref],
            },
        )
    )
    projection = replay_discovery(tuple(runtime.ledger.iter_events()))
    assert projection["assay_bar_authority"]["status"] == "stale"

    # 3. OR-101 successor rubric whose record_id IS a live Candidate identity.
    author = T.ASSAY_AUTHORITY_ACTORS[4]
    rubric = json.loads((T.REPO_ROOT / T.ASSAY_RUBRIC_PATH).read_bytes())
    successor = deepcopy(rubric)
    successor["record_id"] = CAND1
    successor["record_revision"] = rubric["record_revision"] + 1
    successor["supersedes_revision"] = rubric["record_revision"]
    successor["created_by_actor_id"] = author
    successor.pop("content_hash", None)
    successor["content_hash"] = assay_content_sha256(successor)

    before = tuple(runtime.ledger.iter_events())
    command = _cmd(
        "RegisterAssayRubricContent",
        CAND1,
        _version(runtime, CAND1),
        {
            "row_id": "OR-101",
            "authority_kind": "assay_bar",
            "content": successor,
            "authority_file_path": T.ASSAY_RUBRIC_PATH,
        },
        actor=author,
    )
    try:
        successor_receipt = runtime.submit(command)
    except IntegrityError as exc:
        print("OR-101 successor REJECTED at preparation:", exc)
        assert tuple(runtime.ledger.iter_events()) == before
        pytest.skip(f"preparation rejected the collision: {exc}")   # <-- DESIRED post-fix outcome

    after = tuple(runtime.ledger.iter_events())
    print("OR-101 successor receipt:", successor_receipt.status)
    print("stream written:", [e["stream_id"] for e in after[len(before):]])
    with pytest.raises(IntegrityError) as err:
        replay_discovery(after)
    print("LEDGER NO LONGER REPLAYS:", type(err.value).__name__, "-", err.value)
```

### C.3 — R2: OR-017 operational Attempt/Lease not re-derived at replay

```python
"""R2: OR-017 does not re-derive the operational Attempt/Lease at replay."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from research_system.discovery.runtime import replay_discovery

import tests.research_system.integration.test_wp6_6_discovery_runtime as T


def test_adv_or017_replay_does_not_rederive_attempt_or_lease(tmp_path: Path) -> None:
    # Drive the real positive Spike lifecycle to build a genuine ledger.
    T.test_spike_positive_lifecycle_reaches_reviewed_atomically_and_without_provider_execution(
        tmp_path, "PASS", "OR-018"
    )
    harness = T._HARNESSES[tmp_path]
    events = tuple(deepcopy(e) for e in harness.ledger.iter_events())

    baseline = replay_discovery(events)
    spike_id = next(iter(baseline["spikes"]))
    print("BASELINE attempt/lease:",
          baseline["spikes"][spike_id]["attempt_id"],
          baseline["spikes"][spike_id]["lease_id"])

    # Truncate at the OR-017 transaction boundary: a legitimate mid-flight EOF.
    last = max(i for i, e in enumerate(events) if e["event_type"] == "CandidateSpikeStarted")
    prefix = tuple(deepcopy(e) for e in events[: last + 1])

    fake_attempt = "att_019fed25-b33e-7740-b280-0000deadbeef"
    fake_lease = "els_019fed25-b33e-7740-b280-0000deadbeef"
    for event in prefix:
        if event["event_type"] in {"SpikeStarted", "CandidateSpikeStarted"}:
            event["payload"]["attempt_id"] = fake_attempt
            event["payload"]["lease_id"] = fake_lease
            event["payload"]["attempt_sha256"] = "a" * 64
            event["payload"]["lease_sha256"] = "b" * 64

    # Full semantic rehash: reindex global_position, recompute transaction_index /
    # transaction_count, rebuild previous_event_hash and event_hash across the chain.
    attacked = T._reindex_and_rehash_events(prefix)

    state = replay_discovery(attacked)          # <-- MUST raise IntegrityError after the fix
    spike = state["spikes"][spike_id]
    print("REPLAY ACCEPTED A FABRICATED OPERATIONAL ATTEMPT/LEASE AT OR-017")
    print("  spike status   :", spike["status"])
    print("  attempt_id     :", spike["attempt_id"])
    print("  lease_id       :", spike["lease_id"])
    assert spike["status"] == "running"
    assert spike["attempt_id"] == fake_attempt
    assert spike["lease_id"] == fake_lease
```

### C.4 — R3: encoder divergence (one-liner)

```python
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.dossier import canonical_dossier_hash

for value in ({"axis_id": "x", "value": 0.5}, {"kéy": 1}):
    print("prepare :", canonical_dossier_hash(value))
    try:
        print("replay  :", sha256_hex(canonical_bytes(value)))
    except Exception as exc:
        print("replay  :", type(exc).__name__, exc)   # <-- divergence
```

---

## Final statement

**REWORK REQUIRED — exact head `f27555aa0fa82a90a0910ec6a67904939d2e6298` / tree
`6aa8e0b080ee5f05ca0720178f3be1eec8af52ab` has 5 root-cause finding groups and 7 mandatory
appendix items. The review matrix is otherwise complete; no additional review pass is needed
before remediation.**
