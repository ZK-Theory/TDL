# WP6.3 external assurance record store integration-seam review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject and integration seam, read-only
- Reviewed branch: `codex/review-kan67-integration-a2aa9f1`
- Reviewed subject: `a2aa9f16a7660fa492a80be86496b6d317ff4611`
- Parents: `8169bd87a51a4bee0650d538b83ef7968369976b`,
  `6c32f17a7951ee1a01ca48b9fcaf7782125ac09e`
- Tree: `ceca54a618e8ab4c974e4d6b6f655d4f36d4ed45`
- Accepted technical head in ancestry:
  `5fa82b76e23741840b6ff2d6ea9300328dc4cf29`
- PR201 final head in ancestry:
  `75d27ef8caca506b6a98e75f4f819355eeb964a0`
- Verdict: `rework_required`
- Findings: 1 Critical, 4 Major, 0 Minor

## Executive disposition

The six-path integration preserves the accepted technical subject and all
protected WP6.3 contract/schema bytes. Its exact format validation and
low-level compare-and-swap behavior pass. It does not yet constitute the
governed external control-store writer required for genuine multi-party
acceptance: authorship is not authority-bound, distinct semantic identities
are collapsed into one synthetic storage kind, completed records can be
revised, the production pack-loader digest comparison cannot be satisfied by a
schema-valid record, and replay-backed authority is not joined to the writer.

The subject is therefore quarantined. It is not PR- or merge-authorized and is
not evidence that KAN-67, KAN-68, Gate A, or Gate 6 is complete. The low-level
storage mechanics should be preserved; remediation must bind them to exact
semantic identity and current ledger authority without modifying protected
contract/schema bytes or fabricating any live party record.

## Exact identity and preserved evidence

The reviewer confirmed:

- both parents and all required ancestry;
- the merge delta is exactly the six KAN-67 paths;
- the only first-parent overlap is the PR201 bootstrap-projection negative
  control in `tests/research_system/integration/test_authority_grant_source.py`;
- all six KAN-67 blobs are byte-identical between `5fa82b76...` and the
  reviewed subject;
- the review worktree remained clean; and
- concurrent identical writes converge, while conflicting writes produce one
  winner and deterministic conflicts/read-only retries.

Protected identities remained exact:

| Protected object | Git blob | Raw SHA-256 |
|---|---|---|
| WP6.3 contract | `7298b994ca80fb43364ec53964b735f1c7e3929a` | `03cd115c8e914b015a57be2092e41044802ff0c0d018ffb25e04a09c38eda985` |
| External contract schema | `acf622b4e7ae72ab9ac58d10aac14efed04560ac` | `c6154c38bd8fa09589c2891d7771838e3561cd54df5964cd45bfc5cfce65cd8f` |
| Assurance-pack schema | `f282ec37e781aa30b9441f45dfb379dcea13ce23` | `1cac93d2ba0a8bb594b8bee9770039ed02798dfa9878019a23bd22ba56af38f6` |

Validation evidence:

```text
Declared project environment date-time test: 1 passed
Bounded external-record contract, CLI, writer/resolver and pack-loader set:
66 passed in 42.19s
git diff --check: clean
```

## C-01 - external authorship is not authority-bound

The production CLI accepts the control-store configuration, record class,
semantic ID, revision information, and record body, but no caller actor,
authority grant, or relationship evidence. The writer can therefore create
records attributed to every party, including completed reviews, owner
acceptance, and active-grant evidence, from one caller/session. This contradicts
the genuine multi-party and no-self-attestation boundary in handoff 32.

The writer must receive an authenticated actor and exact command scope, resolve
a current ledger-backed grant under the writer lock, and require the actor and
permitted relationship/record class to match the record body. Wrong actor,
project/store/root/record class/semantic ID/revision/action/risk/time, stale or
revoked grant, and mutation between authority resolution and publication must
fail without a write.

## M-01 - semantic storage identity is lossy

All 12 record classes are catalogued and Draft 2020-12 validated, but
`external_records.py` maps every semantic identifier to
`assurance_record/arec_<uuid>`. Valid `act_<uuid>` and `rel_<uuid>` identifiers
with the same UUID consequently collide in the same directory; the second
otherwise valid class is rejected as foreign.

The storage key must preserve the accepted semantic record kind and full
identifier. No synthetic `arec_` shortcut may replace the public identity.
Class/ID/prefix mismatches and cross-class UUID collisions must be decisive
negatives while valid different classes with the same UUID component remain
independent.

## M-02 - completed record classes remain mutable

The record envelope distinguishes completed classes, but the writer applies
only generic revision/CAS rules. A direct probe revised a
`contract_schema_authorship` record from revision 1 to revision 2 while
changing its non-actor `authored_at` value. Completed record classes must be
immutable after creation. Only record classes explicitly authorized for actor
or relationship lifecycle revision may revise, and each permitted field set
must be closed and tested.

## M-03 - the pack-loader digest binding is unsatisfiable

The production pack loader reads `content_sha256` from the accepted requirement
record body, while the accepted record schema forbids that property. A
schema-valid body therefore fails production loading. Existing positive tests
inject the forbidden property through an unvalidated fake resolver, so they do
not exercise the production seam.

The loader must compare the pack's referenced digest with the trusted canonical
digest returned by the external record resolver/store receipt, not with a
schema-forbidden body field. Schema-valid production-resolver positives and
wrong-digest, body-injection, stale-revision, and mutation negatives are
required.

## M-04 - replay-backed authority is not joined to the write path

`ControlStoreAuthorityResolver` reopens and schema-validates external record
history, but the writer does not invoke current replay-backed authority or
`LedgerBackedAuthorityPolicy`, and no lock spans grant resolution through the
record CAS publication. Stale/revoked-grant races are therefore unproved.

The bounded correction must resolve the exact current scoped grant from the
replayed control store inside the writer's critical section and bind the
resolved grant hash/identity to the write receipt. Exact idempotent retry may
return the original receipt only after re-resolving current authority; revoked,
expired, superseded, foreign, or changed authority must fail read-only.

The KAN-68 production acceptance runner remains a separate delivery, but the
KAN-67 writer must expose a governed production seam that the runner can call.
No genuine multi-party records or Gate A acceptance are to be created during
this remediation.

## Required bounded correction

Preserve the accepted six-path storage/CAS implementation where it is correct,
then add the minimum governed seam needed to:

1. preserve exact semantic record identity and storage kind;
2. bind caller, body actor, project/store/root, record class, semantic ID,
   action, revision, time, and current scoped ledger grant under one lock;
3. make completed record classes immutable and close the allowed revision
   field sets for the remaining lifecycle classes;
4. return the trusted canonical digest from the production resolver and use it
   in the pack loader; and
5. prove revocation/retry/restart/concurrency behavior through the real writer,
   `ControlStoreAuthorityResolver`, and ledger-backed policy.

The protected WP6.3 contract and schema bytes must remain unchanged. A fresh
independent review of the remediated exact subject is required before any PR.
