# WP6.3 governed external assurance record store exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, read-only
- Reviewed branch: `codex/kan67-external-assurance-record-store-r2`
- Reviewed subject: `b7575d518a4b93e46f61a371651f220e0602048c`
- Parent: `a2aa9f16a7660fa492a80be86496b6d317ff4611`
- Tree: `58c53261ea8becf02f28764523469d3aeadd762a`
- Delta: exactly 23 paths
- Verdict: `rework_required`
- Findings: 0 Critical, 1 Major, 0 Minor

## Executive disposition

The subject closes the earlier identity, lifecycle, digest, attribution, and
replay-backed publication gaps, but its grant-activation transaction is not
atomic. The canonical grant object is persisted before the activation event is
appended. An append failure therefore leaves durable store state that replay
does not recognize as active, and a later retry can complete the activation.

KAN-67 remains quarantined. This subject is not PR- or merge-authorized and is
not evidence that KAN-68, Gate A, or Gate 6 is complete.

## Exact identity and recorded positive evidence

The exact subject has the required parent and tree and changes 23 paths. The
existing protected authority and WP6.3 assurance schema paths are outside the
delta.

The management record reports the producer's focused evidence as:

- 3 governed-publication integration tests;
- 100 assurance/store/CLI tests;
- 52 scoped-authority integration tests;
- 51 authority/requirement unit tests;
- 139 authority contract/mutation tests; and
- focused accepted-authority regressions, Ruff, hooks, diff, and new-schema
  identity/binding checks.

The same record marks the slow full schema-registry attempt inconclusive. These
positives are useful regression evidence but do not exercise the failing append
boundary and do not override the finding below.

## M-01 - grant activation mutates the object store before ledger commit

`CommandService._prepare_scoped_authority_activation` writes the canonical
`authority_grant` object before returning the prepared event payload
(`research_system/command/service.py:2011-2016`). Only afterward does `submit`
build the activation event and invoke the scoped-authority ledger append
(`research_system/command/service.py:467-487`). The writer lock serializes these
steps but supplies neither a joint commit nor rollback.

An injected append failure after preparation leaves the grant object persisted
while the ledger and replay projection contain no activation. No accepted
receipt exists, yet a later identical retry observes the already-written object
idempotently and can append the missing event, activating authority from a
previously failed command. Store state and replay authority therefore disagree
across failure and restart.

### Minimum correction

Publish the canonical grant object and activation ledger batch through one
crash-safe atomic transaction, or provide an exact recovery/rollback protocol
that cannot delete a pre-existing legitimate object. On every failed
activation, the grant object, ledger, receipt store, command index, snapshots,
and replay projection must remain byte-for-byte and semantically unchanged.

Add deterministic injected-failure controls at the object/ledger boundary that
prove:

1. append failure leaves all named surfaces unchanged;
2. process restart observes no latent or active grant;
3. retry after failure has one deterministic outcome and no duplicate history;
4. an exact pre-existing object is never removed as rollback collateral; and
5. successful activation and revocation behavior remains unchanged.

No live grant or assurance record may be created by this remediation. A fresh
independent review of the corrected exact subject is required before any PR.
