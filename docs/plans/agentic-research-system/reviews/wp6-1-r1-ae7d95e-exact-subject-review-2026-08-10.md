# WP6.1 R1 exact-subject review — 2026-08-10

- Subject: `ae7d95eaec57c7b7cfc76ecfbc19290d3f8dc92e`
- Accepted base: `516cc5320a2c09255414b94d5db7786dd12208df`
- Review mode: fresh, independent, read-only, exact subject
- Verdict: `rework_required`
- Findings: one Major; no Critical or Minor findings
- Review validation: 21 targeted tests passed in 88.09 seconds
- Protected command/event schema directories: unchanged from the accepted base

## Major finding

`store verify-restore` completed full target preflight before the source-ledger
submission, but did not revalidate the target at the final pre-append point. A target
history, file, or artefact change in that interval could therefore allow stale
`RestoreVerified` evidence to be appended.

## In-scope disposition

The delivery owner accepted the finding. The provider now returns the exact prepared
payload with a checked-input revalidator. `CommandService.submit` invokes that
revalidator after event construction and immediately before append. Revalidation
repeats the full restore admission, requires exact equality with the prepared result,
rechecks the target schema set, and revalidates the WP6.4 checked-input closure. It
does not acquire target writer authority, a restore lock, or cutover authority.

The public-seam integration test injects an endpoint-history change after initial
preflight and proves that verification fails before any source-ledger event or command
receipt is written and without creating a target lock. After restoring the injected
test mutation, the ordinary evidence-only success and replay assertions still pass.

This disposition records remediation of the single independent-review finding. It is
not a second independent review verdict, owner authorization for restore cutover, or
Gate 6 closure.
