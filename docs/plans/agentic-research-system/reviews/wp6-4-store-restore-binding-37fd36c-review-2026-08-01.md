# WP6.4 restored-store binding second-remediation exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, read-only static attack
- Producer task: `019fbe40-3022-70e2-b734-8c2b688b11b6`
- Independent reviewer: `/root/wp64_static_attack`
- Reviewed subject: `37fd36cda2ba08bad0412b64da00904b6fdef6c8`
- Direct parent: `f18ece7c0bd181e2e8ca07c61d57eb868b45d1db`
- Tree: `3ec6f9f6acff40bebcfc07bfd6ed0d4716b64185`
- Producer remote: `origin/codex/wp64-store-restore-binding-r3`
- Corrective delta: exactly 5 paths
- Verdict: `rework_required`
- Findings: 0 Critical, 2 Major, 1 Minor

## Executive disposition

The subject materially improves canonical-foundation restriction, source and
ledger-tail revalidation under ordered source/target/output locks, output
publication checking, journaled recovery, pending-evidence promotion, and
crash restart. It does not invoke a provider and leaves the tracked production
`foundation.yaml` null rather than fabricating the absent owner bundle.

Two material seams remain. Loading the supposedly read-only approved binding
creates directories inside the external control root before store identity is
verified. The configuration output also has a later replacement window after
its last validation but before manifest/evidence publication and journal
clear. Crash coverage exercises only one of several durable phase boundaries.

The subject remains quarantined. It is not PR, merge, owner, dispatch,
Gate A, or Gate 6 acceptance evidence. The real current owner operational
bundle remains a later legitimate dependency; that absence does not authorize
fabrication or excuse the two mechanical findings.

## Exact identity and candidate boundary

The exact subject, parent, tree, producer remote, and five-path delta were
confirmed. The delta is limited to:

- `research_system/cli.py`;
- `research_system/config.py`;
- `research_system/operations/backups.py`;
- `research_system/store/identity.py`; and
- `tests/research_system/integration/test_external_assurance_record_cli.py`.

The producer reported the following final-tree evidence:

```text
Required remediation negatives: 6 passed
Gate-5 named restore controls: 18 passed
Replay rebind controls: 3 passed
Focused CLI controls: 14 passed
Focused Ruff and git diff --check: passed
Remote branch equals exact subject
```

The reviewer did not rerun tests and performed no repository writes. The green
producer checks do not exercise or override the later substitution and
read-path mutation sequences below.

## M-01 - approved-binding load mutates the store before verification

`ApprovedProjectBinding.load` calls the write-creating
`require_external_control_root` before loading and verifying the approved store
manifest. A read-only owner-foundation load can therefore create
`objects/events/manifests/receipts/snapshots/runtime` beneath an absent or
partial approved external root before identity validation.

This violates the no-production-foundation-mutation and fail-closed boundary
and can repair or hide a partial store while deciding whether to trust it.
Use the read-only code-root disjointness check at this stage, then load and
verify the existing store manifest. Add absent- and partial-store negatives
that prove byte-for-byte no mutation.

## M-02 - configuration output can be replaced after its final check

The output is validated inside `commit_output`. Manifest/evidence publication
and journal clearing occur afterward without another output identity check. A
foreign replacement after `commit_output` returns but before manifest replace
can therefore leave durable evidence claiming `bound-and-config-published`
while the actual output is foreign.

Run the final binding/output validator as the journaled post-commit check while
the transaction is still recoverable. On mismatch, roll back or recover
without accepting the foreign output. Add an injection after the
`output-published` phase and before manifest/evidence publication.

## m-01 - crash controls omit durable phase boundaries

Only one true process-crash case is exercised, at manifest replacement. Add
bounded process-exit/restart controls for output publication and phase
recording, evidence publication and phase recording, and journal-clear
boundaries. Each must either complete the exact intended transaction or restore
the exact pre-operation state; no pending-only evidence may authorize success.

## Preserved closures and owner dependency

Static review found the canonical-foundation restriction, source/tail rechecks
under the final ordered locks, and journal-state recovery materially improved.
No provider, credential, transport, or live research invocation was added.

The tracked canonical foundation remains null; the historical external root is
absent; and the endpoint, current manifest/tail, and full foundation digest are
not materialized. After the mechanics pass fresh review, the current external
store and complete canonical owner bundle still need one exact owner-backed
materialization. This review neither requests that act prematurely nor turns
historical values into current operational evidence.
