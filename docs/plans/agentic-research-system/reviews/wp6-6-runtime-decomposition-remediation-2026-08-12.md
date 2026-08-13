# WP6.6 `discovery/runtime.py` decomposition remediation record

Status: candidate construction record. **Not** independent acceptance, CodeRabbit
completion, owner acceptance, merge authorization, or integration evidence.

The same session that froze the Phase A verdict implemented this remediation, so
nothing here is an independent approval. The controlling assessment is
`wp6-6-runtime-architecture-adversarial-assessment-2026-08-12.md`, committed at
`bcafb9d` **before** the first production edit.

## Subject

| Property | Value |
|---|---|
| Reviewed subject | `cf4ea2e48b0564c4e21e63af40846274bf26a039`, tree `4573e3c2970002851b669e5341161028698b41f7` |
| Base / live main | `2e6bf9c92e59208c40e55f664fc48d75e481ae04` (verified ancestor) |
| Verdict | SUBSTANTIAL DECOMPOSITION |
| Pre-refactor baseline | nine-module gate **459 passed, exit 0** |

## What changed

`research_system/discovery/runtime.py`: **6,481 → 2,802 lines** (−57%).
`replay_discovery`: **2,072 → 728 lines**, and it now owns no lifecycle policy.

| Commit | Step |
|---|---|
| `bcafb9d` | Frozen pre-edit adversarial assessment |
| `6f5a4a0` | Leaf extraction (`accepted_w11`, `routes`, `rules`, `ledger_integrity`) |
| `fd1f9e0` | `replay_discovery` split into owned lifecycle reducers + architectural controls |
| `2f74bc8` | Assay Partial binding rule de-duplicated |

## Responsibility map

| Module | Lines | Owns exactly |
|---|---:|---|
| `accepted_w11.py` | 49 | The protected accepted-W11 envelope identity and the one-time genesis payload. |
| `routes.py` | 352 | The immutable row→command/event registry (59 executable rows), its accepted-catalogue partition proof, the mint/existing-target split, the shared-ledger partition, and the single global immutable-identity contract. |
| `rules.py` | 1,172 | The shared lifecycle predicate family. Each rule has one definition reached by both preparation and replay. Pure: mappings in, booleans out. |
| `ledger_integrity.py` | 168 | Hash-chain and persisted-envelope validation of durable bytes. |
| `replay/scope.py` | 40 | The names a reducer may read. Nothing else is reachable from a reducer. |
| `replay/driver.py` | 760 | Ledger preconditions, projection initialisation, the transaction-join closures, the shared-ledger partition, and the authority shadow lane. **No lifecycle policy.** |
| `replay/registry.py` | 84 | 66 event types → exactly one owning reducer. |
| `replay/genesis.py` | 31 | `W11CatalogueGenesisImported`. |
| `replay/scout_candidate.py` | 186 | Scout ingestion, Candidate registration and supersession. |
| `replay/assay.py` | 475 | Assay request, score, partial, cancellation and their Candidate links. |
| `replay/spike.py` | 649 | Spike plan, authorization, start, verdict, partial, review, cancellation, and operational closure shadows. |
| `replay/review_decision.py` | 354 | Review/Decision relations, revisit and retry across both lifecycles. |
| `replay/promotion.py` | 123 | Candidate promotion request and application. |
| `replay/dossier.py` | 130 | Dossier admission and its object/Scope materialisation. |
| `runtime.py` | 2,802 | The public `DiscoveryRuntime` façade: authority resolution, identity fencing, receipt/idempotency recovery, route dispatch, schema/producer binding, event construction, ledger append. |

## Dependency direction

```text
accepted_w11          (no intra-package imports)
      ↑
   routes ────────────────┐
      ↑                   │
   rules            ledger_integrity
      ↑                   ↑
  replay.scope            │
      ↑                   │
 replay.{genesis, scout_candidate, assay, spike,
         review_decision, promotion, dossier}
      ↑
 replay.registry
      ↑
 replay.driver ──────────┘
      ↑
   runtime  (façade)
      ↑
  discovery.__init__
```

Enforced by `tests/research_system/unit/test_wp6_6_discovery_architecture.py`:
forbidden leaf→façade imports, an acyclic package graph, one owning reducer per
event, no unreachable reducer, no reducer owned by two modules, and a façade
that defines no reducer and no `replay_discovery`.

## Defects found during extraction

**1. Import cycle through the replay package initialiser — found, watched red, fixed.**
`replay/registry.py` imported the `replay` package while `replay/__init__.py`
eagerly imported `driver`, making the package initialiser part of its own
dependency chain (`__init__ → runtime → replay → replay.driver → replay.registry
→ replay`). It functioned only because Python tolerates partially-initialised
parents. The new cycle control **failed on this before it passed**:

```text
AssertionError: import cycle: __init__ -> runtime -> replay -> replay.driver -> replay.registry -> replay
```

Fixed by emptying `replay/__init__.py` and importing `replay.driver` directly —
not by relaxing the test. That failure is the negative control for this gate.

**2. Assay Partial binding rule duplicated — corrected, with a precision
correction to the frozen assessment.**

The frozen assessment (§3.1) called the two copies "already diverged" and listed
this under defects. That wording overstates it, and the record should be exact:
**the divergence is not exploitable.** Replay's
`_current_assay_bar_matches(assay, bar, actor_id)` subsumes both of
preparation's bar comparisons *and* adds the producer-relation and actor
binding, so replay is at least as strong as preparation on every input. No
ledger replay would accept could have been refused at preparation. No red
behavioural proof is claimed here, because the divergence does not admit one.

What was real is the maintainability defect: the seven reference comparisons
were written twice, 3,700 lines apart, with nothing forcing them to agree. They
now have one definition, `rules._assay_partial_bindings_match`, reached by both
paths; each side keeps only the extra checks its own context can make, so
rejection behaviour on both paths is unchanged.

## Behaviour preservation method

Every moved line is a verbatim slice of the original file:

- Leaf extraction: the script asserted the kept + removed line partition
  reconstitutes the original exactly, and the extracted route registry was
  proven field-identical to the original for all 59 rows.
- Reducer split: each reducer body is the original branch body dedented by
  exactly 8 columns (asserted, then re-parsed). Each reducer's prologue rebinds,
  under their original names, only the shared-scope names its body actually
  reads — derived by AST, not guessed. Because the module scope contains no
  `state`/`event`/`payload`, any missed binding fails loudly as `NameError`
  rather than silently changing a rejection.
- The `else: raise IntegrityError(f"unsupported Discovery event: {event_type}")`
  terminator is preserved exactly as the registry miss.

## Preserved seams

- `DiscoveryRuntime`, `DiscoveryRuntime.submit`, `replay_discovery` all still
  resolve from `research_system.discovery.runtime`.
- `runtime.replay_discovery` remains a module global, so the crash-recovery
  tests' `monkeypatch.setattr(discovery_runtime_module, "replay_discovery", …)`
  still intercepts it.
- `research_system/projection/replay.py`'s deferred import is unchanged.
- No command, event, schema or producer identity changed. No durable event or
  receipt format changed. OR-030 remains deliberately inactive and fail-closed.
- Two test modules now import the route registry and lifecycle predicates from
  their owning modules rather than through the façade. No assertion changed.

## Protected identity at the candidate head

| Item | Value |
|---|---|
| W11 catalogue blob | `8d58818540e04859f929d4b04c71e4cfa0512554` |
| bytes | 136229 |
| SHA-256 | `7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80` |
| `git diff cf4ea2e..HEAD -- .research-system/ contracts/` | empty |
| `2e6bf9c` ancestor of HEAD | yes |
| `cf4ea2e` ancestor of HEAD | yes |

## Residual risks

1. **The façade is still 2,802 lines.** `DiscoveryRuntime` retains the
   `_prepare_*` family and a 287-line `_submit_authorized` that still fuses
   receipt/idempotency recovery with route dispatch and schema binding. The
   preparation split named in the assessment's target design is **not done**.
   Establishing preparation/replay equivalence for one row still requires
   reading `runtime.py` plus the owning reducer module — two files instead of
   ten regions of one, but not one file.
2. **Catalogue token vs runtime event name.** Three accepted catalogue tokens
   normalise to names the runtime does not emit (`AssayReviewRequested` vs
   `AssayOutcomeReviewRequested`; `CandidateRevisitRequested/assay` vs
   `CandidateAssayRevisitRequested`, likewise `/spike`). This is pre-existing at
   the frozen subject and was deliberately not changed — the event identities are
   durable. It does mean the architecture test cannot assert a plain string
   equality between `catalogue_events` and registry keys, so registry coverage is
   proven structurally (one owner, no orphans, no duplicates) rather than by
   catalogue-name equality.
3. **Nine authority-lane event types are reduced by the driver**, not the
   registry, through the `authority_event_type` shadow branch. That lane is
   cohesive but is a second dispatch mechanism a reviewer must know about.
4. The reducer modules are grouped by lifecycle; `spike.py` (649) and
   `assay.py` (475) remain the largest and could be split further by transition
   family if a later review finds them hard to reason about.
