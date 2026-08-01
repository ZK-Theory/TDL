# WP6.4 restored-store binding r3 exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, authority and recovery,
  read-only
- Review task: `019fbe14-5031-7682-918d-cac267a89268`
- Reviewed subject: `f18ece7c0bd181e2e8ca07c61d57eb868b45d1db`
- Direct parent: `523a354ada0ccbdd6c459f4e106c30443fb89c9f`
- Tree: `cafb5620b7d3ccf283f6181de5f614f49e1bf4b8`
- Corrective delta: exactly 8 paths
- Verdict: `rework_required`
- Findings: 1 Critical, 2 Major, 0 Minor

## Executive disposition

The subject preserves useful authority ordering, pre-mutation durability,
conflict, rollback, and replay controls. Its focused CLI, Gate 5, and replay
tests pass, and the review performed no provider or live-system mutation.

The exact subject remains unsafe to integrate. Its approved project binding
does not independently bind the real external control store, its configuration
output can be substituted during retry, and a crash after manifest replacement
can strand a partially committed restore that retry cannot complete or roll
back. The subject is quarantined and is not PR-, merge-, or
owner-acceptance-authorized; KAN-57, WP6.4, and Gate 6 remain open.

## Exact identity and retained positive controls

The subject has the required parent and tree and changes exactly:

- `research_system/cli.py`;
- `research_system/command/service.py`;
- `research_system/config.py`;
- `research_system/operations/backups.py`;
- `research_system/store/identity.py`;
- `tests/research_system/integration/test_external_assurance_record_cli.py`;
- `tests/research_system/integration/test_gate5_release_tranche.py`; and
- `tests/research_system/unit/test_replay.py`.

Recorded positive evidence:

```text
External-assurance CLI: 8 passed
Gate 5 focused slices: 20 passed and 17 passed
Replay: 4 passed
Normal injected rollback: passed
Pre-mutation durability checks: passed
Command, schema, conflict, and authority ordering: passed
```

These positives do not exercise or override the substitution, retry-race, and
crash-state probes below. No provider call, credential use, or live mutation
occurred.

## C-01 - approved binding omits the external control-store identity

`ApprovedProjectBinding` binds only `project_id`, `code_roots`, and
`schema_root`. It does not bind an independently owner-approved `control_root`,
store identity, or foundation digest. The canonical `foundation.yaml` is null
or unloadable, so the public operation can instead be supplied an ad hoc
foundation derived from the roots being authenticated.

An independent probe jointly substituted the source and target manifest roots
and supplied a matching ad hoc foundation. The public CLI returned 0 and
published the substituted roots. The operation therefore remained
self-anchored despite the nominal approved-binding layer.

The correction must use one canonical owner-approved foundation that binds the
real external `control_root`, exact store identity, code roots, schema root,
and foundation content digest. That authority must load independently of the
candidate source and target manifests and be revalidated under the final
publication locks. Coordinated substitution must fail closed with every target
surface unchanged.

## M-01 - configuration-output retry has a check-to-use race

`config_output` is checked before lock acquisition, while the source and target
locks omit the output path. The already-bound retry path also returns without
rereading and revalidating the output under a lock. A valid foreign binding can
therefore replace the checked output before it is consumed.

An independent interleaving probe replaced `config_output` with a foreign but
valid binding between the checks. The retry returned 0 and loaded the foreign
project and control root.

Include the output path in the final lock set and recheck its exact identity
under that lock immediately before both publication and success. The
already-bound path must reread and validate the locked output instead of
trusting an earlier observation. A deterministic replacement probe must fail
closed without loading or publishing the foreign binding.

## M-02 - crash recovery cannot complete or roll back partial publication

An injected process exit 77 immediately after manifest replacement left a
published configuration output and bound manifest, but neither canonical
evidence nor the temporary evidence needed to finish publication. Retry then
failed because the evidence was missing. A related pending-evidence state can
also return success without promoting that evidence to its canonical path.

Normal exception rollback does not cover process termination at the durable
publication boundary. The correction needs a durable, fsynced journal or
equivalent state machine written before the first mutation. On restart it must
deterministically verify and complete the exact committed publication or roll
back to the exact pre-operation state. Pending evidence must never permit
success without verified canonical promotion.

## Required bounded correction

The next exact subject must:

1. load a canonical owner-approved foundation that binds the real external
   control root, store identity, code/schema roots, and foundation digest;
2. include `config_output` in the final lock and identity recheck for both new
   publication and already-bound retry paths;
3. add durable journaled recovery that completes or rolls back every crash
   state around manifest, output, and evidence publication; and
4. preserve the passing authority, ordering, rollback, durability, conflict,
   CLI, Gate 5, and replay controls without widening scope.

A fresh independent exact-subject review is required. No PR update,
integration, provider action, live mutation, or acceptance is authorized by
this record.
