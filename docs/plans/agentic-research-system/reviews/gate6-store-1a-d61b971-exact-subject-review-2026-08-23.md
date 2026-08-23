# Gate 6 STORE-1A exact-subject review — 2026-08-23

## Current executive verdict

**Verdict: `ACCEPT FOR PUBLICATION`.**

Current reviewed code subject:
`ac6daed4a6cb9679e4e882ae41cb9363b00f0969` on
`codex/g6-spec-store-1`. The exact-subject semantic review accepts all eight
minimal STORE-1A controls. The candidate is ready for publication through the
owner-controlled PR route; this is not merge permission or Gate 6 acceptance.

Exact campaign scope from
`02e4b2baf8e2e85052fdbdda8f4d35e27fa0cc30` is **22 files, 4,989 additions,
207 deletions**, within the 35-file/5,000-added-line hard stops.

Gate 6 remains **INCOMPLETE**. STORE-1A is a bounded foundation. **STORE-1B
follows** with the verified binding/predecessor, transaction, shared admission,
public consumer migration, and historical binding lineage.

## Review method and independence

Expected behavior came from the accepted `06q` STORE-1A boundary before source
comparison. Observed behavior came from the exact commit, its complete 22-file
diff, direct source/test inspection, the minimal failure-family controls, and
independent tester evidence. Candidate summaries were not treated as proof.

Inputs were kept independent to avoid self-certification:

- expected lock identity is caller identity plus process-instance observation;
  observed identity is the held canonical file and filesystem generation;
- expected governed content is the persisted manifest; observed content is
  independently rebuilt from repository/tree/blob objects, working bytes,
  index flags, origin, and ancestry;
- expected schema precedence comes from activation and producer contracts;
  observed precedence comes from submitted envelopes;
- expected frozen behavior comes from fixtures/contracts; observed behavior
  comes from real command, ledger, object, and publication seams.

## Current decision and invariant matrix

| Minimal control | Exact-subject observation | Decision |
|---|---|---|
| 1. Exact-generation ownership and crash recovery on Windows/POSIX | Private durable stage, no-follow canonical claim, generation/byte proof, anchored deletion or POSIX quarantine; post-publication cleanup is tracked | **ACCEPT** |
| 2. Post-proof substitution preserves foreign generations | Windows held handle and POSIX private dirfd quarantine revalidate identity/bytes; mismatch is never deleted | **ACCEPT** |
| 3. Retry typing is narrow | Only `WriterLockContentionError` retries; sibling `ConflictError` and publication failures propagate | **ACCEPT** |
| 4. Manifest binds repository and bytes | Versioned inventory covers code/config/schemas/contracts/locks; blob OID and SHA-256 are rebuilt; redirected roots, hidden index state, filtered-byte drift, origin mismatch, and non-descendant divergence reject/classify | **ACCEPT** |
| 5. Documentation-only descendants exclude hidden governed bytes | Descendancy and unchanged governed catalogue/bytes are required; hidden or non-regular changes reject | **ACCEPT** |
| 6. `SpecOperatorConfig` remains authority-neutral | It contains locators only and grants no origin witness, admin decision, semantic authority, or effect permission | **ACCEPT** |
| 7. Diagnostic precedence and historical regression behavior remain exact | Inactive/full-only schema precedes unbound producer; active wrong producer remains distinct; S-014, Scenario-A, release retry, and real contention semantics are preserved | **ACCEPT** |
| 8. Public observable and ownership boundary remain bounded | No parallel binding lineage or premature public SPEC route was added; STORE-1B owns verified binding/admission and consumers | **ACCEPT** |

**Semantic acceptance: 8/8 minimal controls.** No concrete reachable Major or
Minor defect remains at `ac6daed4a6cb9679e4e882ae41cb9363b00f0969`.

## Historical finding and disposition

### G6-S1A-M1 — Major at `d61b971` — closed at `ac6daed4`

The initial exact-subject review of
`d61b971ec0205cbaf3b5fe2b7dcf9d56578673ce` returned **REWORK**. After canonical
`writer.lock` publication, failure deleting its private staging hard link made
`WriterLock.__enter__` raise before the composite owner recorded acquisition.
The current process therefore left a live canonical lock that later operations
could neither reclaim nor release.

The direct historical falsifier produced:

```text
OSError injected cleanup failure
lock_exists True
state live
```

The accepted repair makes publication ownership explicit:

- canonical ownership is authorized only after hard-link publication and
  directory durability;
- failure before durability never authorizes writes;
- after durability, private-temp cleanup failure returns a tracked lease only
  after held, no-follow, exact-generation observation;
- inability to roll back an uncertain canonical publication leaves explicit
  fail-closed poison rather than returning success;
- foreign canonical substitutions are preserved;
- anchor-close failure is chained/deferred without discarding completed
  ownership proof;
- exit attempts deferred private-temp cleanup even when canonical release
  fails, and the body exception remains primary.

The exact-head minimal failure family passed **8/8**. It covers durable-temp
cleanup ownership, pre-durable fsync failure, rollback failure, foreign
canonical preservation, held no-follow observation, anchor-close ordering,
canonical release failure with deferred cleanup, and body-exception chaining.
No unsafe success path remains in that reachable family.

If canonical release fails while private-temp deletion succeeds, the missing
directory fsync for the private deletion is not material to exact publication:
release reports failure, the canonical generation remains authoritative, and
only a noncanonical private name may reappear after crash.

## Independent tester evidence

The module-isolated equivalent frozen selection recorded **403 collected**,
**401 passed**, and **2 expected POSIX-only Windows skips**.

The combined invocation was orphaned at **53%** without a terminal summary. It
is explicitly **unresolved and not claimed green**. Retained log:
`C:\Users\steph\AppData\Local\Temp\g6-store-1a-final-exact-selection.log`.

This distinction preserves the successful independently completed module
selection without converting an interrupted aggregate process into evidence.

## Exact evidence commands

```text
git rev-parse HEAD
git branch --show-current
git status --short
git diff --stat 02e4b2baf8e2e85052fdbdda8f4d35e27fa0cc30
git diff --numstat 02e4b2baf8e2e85052fdbdda8f4d35e27fa0cc30
git diff --check 02e4b2baf8e2e85052fdbdda8f4d35e27fa0cc30
```

Focused semantic evidence comprised the eight minimal publication controls at
the exact subject plus the tester's module-isolated frozen selection described
above. The interrupted combined invocation is retained only as an unresolved
test-process observation.

## Residual risks and boundaries

- Windows is the accepted live runtime. The two POSIX-only runtime tests were
  skipped as designed; POSIX source/contracts were inspected, but a Linux run
  remains useful platform evidence rather than a STORE-1A publication blocker.
- Repository identity is the configured origin spelling, not an independently
  authenticated origin witness. STORE-1A grants no binding authority; STORE-1B
  must join it to the approved historical binding and independent authority.
- Publication acceptance does not establish a runnable or integrated SPEC
  capability and does not authorize merge, live-store mutation, or owner
  acceptance.

This review record preserves the initial `d61b971` REWORK evidence and records
the independent semantic acceptance of its exact repaired successor
`ac6daed4a6cb9679e4e882ae41cb9363b00f0969`. It changes no implementation,
test, planning authority, Git history, Jira, live store, PR, or external review
state.
