# Adversarial Review: WP5.3-A Canonical Authority Source Plan

**Date:** 2026-07-12

**Reviewed artefact:** `implementation/05e-wp5-3a-canonical-authority-grant-plan.md`

**Initial verdict:** `rework_required` pending Owner decision G5.3-B

**Final disposition:** `accept` after Owner acceptance of G5.3-B(a)

**Review mode:** fresh-context read-only subagent, followed by Manager evidence verification and plan correction

## Executive verdict

The prerequisite direction is sound, but the first draft overclaimed actor
authenticity from a self-consistent local store. The existing CLI and W2 store
can prove canonical provenance, exact scope, immutable content, current time,
and revocation under the writer lock; they cannot authenticate the human or
process presenting a public actor ID. That is a Critical governance boundary,
not a missing unit test.

Six implementation-contract findings were corrected in the reviewed plan. The
Owner then accepted G5.3-B(a)'s trusted-local-operator boundary and rejected
cryptographic principal authentication as disproportionate for this project.
The plan is implementation-ready; WP5.3 runtime still waits for its merge.

## Findings and dispositions

### ADR-01 - Critical - actor authenticity was circular

**Evidence:** current `research_system/store/identity.py` creates and verifies a
self-hashed local manifest, while `research_system/command/service.py` treats
the envelope actor ID as attribution and explicitly leaves authorization
downstream. `05d` section 4.2 prohibited caller assertion as authority.

**Failure:** any trusted local operator able to initialize a new store can name
an arbitrary actor; later equality with that public ID proves consistency, not
principal authentication.

**Disposition:** resolved. The Owner accepted G5.3-B(a). The plan records
trusted-local-operator provenance and an exact Owner-approved bootstrap hash as
an explicit capability restriction. Signed-principal/key-lifecycle work is
rejected as disproportionate and remains out of scope.

### ADR-02 - Major - genesis root activation was underspecified

**Evidence:** the first draft named `AuthorityRootInitialized` but did not define
its command identity, transaction ordering, or same-batch authority semantics,
despite the generic event schema requiring complete command/actor/grant fields.

**Failure:** a fail-closed resolver could reject the root or an implementation
could invent a reusable bootstrap bypass.

**Disposition:** corrected. `05e` section 3.2 now defines the exact internal
`InitializeAuthorityRoot` envelope, index 0 root activation, index 1 publication
activation, same-batch limit, and missing/reversed/extra/non-genesis rejection.

### ADR-03 - Major - immutable grant hash lacked a governed interface

**Evidence:** generic command/event envelopes carry `authority_grant_id` but no
grant-object hash.

**Failure:** a narrative could claim exact immutable binding while commands,
receipts, or events retained only the ID.

**Disposition:** corrected. New command-specific payloads, authority event
payloads, receipt scope/index, resolver result, and WP5.3 request/event evidence
must carry one equal grant SHA-256. `05d` now requires both
`publication_authority_grant_id` and `publication_authority_sha256`.

### ADR-04 - Major - idempotency depended on missing receipt indexing

**Evidence:** W2 section 13.1 permits `authority_grant_id` as the stricter pre-WP2
proxy, but current service/receipt persistence cannot return an exact logical
retry under a new command ID.

**Failure:** a lost-response retry can conflict or be re-evaluated after
revocation instead of returning the historical outcome.

**Disposition:** corrected. The prerequisite now owns an atomic pre-WP2
proxy-tuple + payload-hash + grant-hash receipt index for accepted, rejected,
and conflict outcomes, including restart and new-command-ID retry tests. It does
not misstate the later normalized-scope rule.

### ADR-05 - Major - bootstrap crash recovery could brick a store

**Evidence:** existing immutable objects and event files have separate commit
steps; inert orphan objects are valid W2 crash residue.

**Failure:** an object-first crash could violate a simplistic empty-store retry
precondition with no legal recovery.

**Disposition:** corrected. The plan now stages the complete new store in a
same-volume sibling, validates/replays it, and atomically publishes the whole
directory to an absent target. Exact staged/final retries are resumable or
duplicate; foreign stages and legacy identity-only stores remain inert and fail
closed. Ordinary post-genesis W2 event-file commit semantics are unchanged.

### ADR-06 - Major - scope and expiry were not typed tightly enough

**Evidence:** AuthorityGrant 1.0.0 permits arbitrary string-array scope and a
nullable expiry.

**Failure:** overbroad root scope, v1.0 scope ambiguity, or null/equal/inverted
publication times could pass schema shape checks.

**Disposition:** corrected. G5.3-A accepts only AuthorityGrant 1.1.0 with one
typed project + subject object. Root and publication grants have exact subjects;
publication expiry is finite and active only on `[effective_at, expires_at)`.

### ADR-07 - Major - high-level approval did not settle material root choices

**Evidence:** the Owner approved implementing a canonical source/resolver, not a
specific principal-authentication mechanism, genesis exception, or migration
policy.

**Failure:** implementation could turn a Manager-selected trust model into an
irreversible owner-approved architecture by implication.

**Disposition:** resolved through the governance gate. The Owner accepted
G5.3-B(a); `05e`, `05d`, and the Gate 5 master plan record the trusted-local-
operator boundary and leave cryptographic principal authentication out of scope.

## Decision audit

| Decision | Disposition |
| --- | --- |
| G5.3-A canonical source/resolver prerequisite | Keep; direction owner-approved. |
| G5.3-B principal-authentication boundary | Option (a) accepted; option (b) rejected as disproportionate. |
| AuthorityGrant 1.1 typed scope | Accepted under option (a). |
| New-store-only staged genesis | Accepted under option (a); no existing-store migration. |
| Exact bootstrap-manifest hash | Owner approval required before integrated publication. |
| O12/WP5.3 publication | Deferred until prerequisite implementation merges. |
| O15/Gate 5/Gate 6 | Unchanged and open/restricted as previously recorded. |

## Consistency matrix

| Invariant | Enforcement point | Test/evidence |
| --- | --- | --- |
| Object inert until canonical activation | Genesis/replay/resolver | Object-only, wrong-kind, duplicate activation controls |
| Exact grant bytes bind governed action | Command/event payload + receipt index + resolver | Per-boundary hash mutation controls |
| Root exception cannot escape genesis | Staged initializer + replay | Missing/reversed/extra/non-genesis batch controls |
| Current authority checked while locked | CommandService resolver hook | Deterministic revoke-versus-operation race |
| Exact logical retry is historical | ReceiptStore proxy-tuple index | New-command-ID, restart, changed-payload controls |
| No half-created store | Same-volume staged directory publish | Interruption at each durability boundary |
| Principal authentication is not overclaimed | G5.3-B capability restriction | Manager review of release evidence wording |

## Practicality and residual risk

The Owner accepted option (a) as proportionate for the current synthetic, offline, trusted-local-
operator P0 foundation and avoids introducing credentials or a signing service.
Its residual risk is explicit: a malicious process with authority to initialize
or replace the registered store is outside the authenticated-principal threat
model. Option (b) is materially stronger but expands Gate 5 into identity,
signature, key custody, rotation, and incident-recovery design.

## Change log and verification

- Added `05e-wp5-3a-canonical-authority-grant-plan.md`.
- Amended `05d-wp5-3-release-event-publication-plan.md` for the real ledger
  resolver, grant ID/hash evidence, initialization ordering, and G5.3-B.
- Amended the Gate 5 master plan Owner record with G5.3-A/G5.3-B.
- No runtime code, fixture, policy, result, provider, credential, or `.env` file
  changed.
- `git diff --check` and labelled-fence validation pass after corrections.
