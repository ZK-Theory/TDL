# WP6.2 T2 Research-First Scope and R3 Remediation Ruling

**Date:** 2026-07-22
**Decision ID:** P-039
**Status:** ACCEPTED by Stephen on 2026-07-22
**Amends:** P-038 scope and evidence timing; preserves P-037's command family
**Scope:** one final T2 contract remediation and fresh static R3; no runtime

## Owner acceptance

Stephen accepted this ruling at its pre-acceptance identity on 2026-07-22:

| Item | Accepted identity |
|---|---|
| Manager commit | `1301d8a5f089d27270c36b216967000a35472efc` |
| Proposal Git blob | `1c6703b37579a0ffa35bfec0f9cccc7180a37f79` |
| Proposal raw-byte SHA-256 | `959ebeafa67368ffc87592134fd9c0caf385b4b562278789273563844295492f` |

The acceptance authorizes the one final contract-only remediation and fresh static R3
defined below. It does not accept the future candidate or authorize runtime work.

## Why a new ruling is required

R2 found four Critical and four Major contract defects after the one remediation cycle
authorized by P-038. A second cycle requires explicit owner authority. At the same time,
the T2 effort expanded from a narrow non-persistence boundary into runtime-style security
evidence and exhaustive W7 assurance before any live adapter exists. Stephen has stated
that ARS effort must prioritize research assurance, especially mathematical, statistical,
result, provenance, and reproducibility assurance, and that orthogonal work must justify
its time and token cost.

This ruling both narrows and closes. It does not excuse the remaining authority and
replay defects.

## 1. Research-value gate

For ARS work after this decision, a non-research assurance control may become blocking
only when its dispatch records:

1. the protected research asset: validity, confidential research data, provenance,
   reproducibility, or essential execution;
2. one concrete and credible failure path;
3. why existing platform or provider controls are insufficient;
4. the cheapest adequate control;
5. the lifecycle stage at which the property can actually be evidenced; and
6. an effort budget and stopping condition.

Priority order is:

1. mathematical, statistical, result, and claim assurance;
2. data integrity, provenance, reproducibility, and confidential research data;
3. minimal operational controls required for safe execution; and
4. general infrastructure or security hardening only when separately justified.

Absent separate owner approval, category 4 receives no more than 10% of a work package's
planned supervision/author/review time or context budget and may not delay its research
assurance deliverable. Residual risk is recorded rather than converted automatically into
new blocking machinery.

## 2. Credential boundary narrowed to contract-stage evidence

P-038 C3 is amended for T2:

- `SecretReference` remains a strict opaque identity with provider and credential class,
  allowed scope, expiry, typed resolver registry URI/revision/hash, resolver version,
  redaction declaration, and exact ID/revision/hash bindings.
- No T2 canonical command, event, receipt, grant, manifest, fixture, or evidence schema
  may contain a field designated to carry raw credential bytes, provider tokens, or
  resolver output.
- Commands and grants must bind the exact `SecretReference` triple. T2 never resolves a
  credential and never claims that a live transport or logging path is leak-free.
- The T2 candidate removes `PreIssueEvidenceManifest` as a blocking type and removes the
  eight-seam scanner/sentinel evidence from its contract, catalogue, identity manifest,
  crosswalk, validators, and tests.
- The eight-seam matrix in accepted 06b is deferred to T3/T4 adapter qualification. It
  must be re-specified against the actual resolver, protected authentication channel,
  transport, logging, exception, and persistence surfaces before execution. Only
  repository-owned harmless fixtures approved for that runtime stage may be used.
- Reviewer-authored credential payloads, fuzzing, scanners, penetration tests, and
  security tooling are not required for T2 acceptance.

This is a timing and proportionality amendment, not permission to persist credentials.

## 3. W7 assurance narrowed to the T2 subset

P-038 M2 is amended. T2 does not claim complete W7 runtime qualification. ProviderCommand
2.0 and ProviderReceipt 2.0 must strictly represent and validate only the subset consumed
by P-037's atomic issue and reconciliation boundary:

- exact command/receipt, provider, model/profile, adapter, policy, Task/Dispatch/Attempt,
  grant, reservation, and `SecretReference` identities/revisions/hashes as applicable;
- W2 command identity, expected control position, idempotency key hash, and payload hash;
- rendered payload/context hash or a typed inability where W7 already permits it;
- effective permission summary/hash sufficient to prove T2 did not widen authority;
- input/output/total token ceilings, actuals, accounting method, currency/rate evidence,
  reserved/consumed/refunded microunits, expiry, and reconciliation disposition;
- issue/terminal time, normalized status/error, duplicate/retry/reconciliation evidence;
  and
- output/artefact references and hashes plus redaction/omission declarations needed for
  provenance and later audit.

All other W7 section 9/10 provider-native, tool-action, transport, cancellation, process,
and operational-observation qualification is deferred to T3/T4. The T2 addendum and
crosswalk must label this surface `t2_authority_cost_subset`, not `complete_w7`.

## 4. Retained R2 closures

One final contract-only remediation must close:

1. **C1:** Receipt 2.0 itself enforces exact count, unique contiguous transaction
   positions, canonical event order, event IDs, stream/resulting versions, and complete
   duplicate equivalence; rejected/conflict outcomes have no event proof.
2. **C2:** all five event envelopes carry the complete W2 logical idempotency tuple and
   payload binding; reconstruction is keyed by that event-derived tuple and rejects
   same-tuple/different-command and same-tuple/different-payload collisions.
3. **C4:** every applicable Task, Dispatch, Attempt, grant, reservation, command,
   receipt, and secret-reference authority subject is an unconditional exact
   ID/revision/hash triple checked against an independently owned expected record.
4. **M1:** one mandatory composed gate performs schema validation, integer token/cost
   arithmetic, and cross-object currency/rate evidence equality. No new accounting
   subsystem is authorized.
5. **M3:** Receipt 2.0 stream identities use the existing exact lowercase UUIDv7 and
   permitted-prefix rules.
6. **I1:** the normative expected set is authored independently of the materializer;
   the exact protected membership is committed or derived from an accepted source, and
   validation live-recomputes its count and aggregate.

The corrected R2 report at commit `a10de8df9e0be8b381e6257aa761d8d8cea2506b`,
blob `f93c030d59b7df74e08d4a960f28045a6c9fbec2`, raw SHA-256
`c2bb533d05d40f6720709406d98f096b288894c0eb0e044b44edcd3fc376cf8b`
is the finding source, subject to the amendments above.

## 5. Final remediation and review budget

- Author one new immutable candidate from the existing author branch; preserve R1 and R2
  candidates as rejected history.
- One author task owns only the retained closures and the explicit C3/M2 scope reduction.
- Use at most 50k live input tokens and stop before compaction. Do not regenerate an
  artifact until its current deterministic bytes are certified and a required source
  change is identified.
- Run focused T2 tests, decisive retained-finding negatives, deterministic
  rematerialization, protected-byte comparison, Ruff/format, contract binding checks,
  and normal hooks. Do not run the full 665-test framework unless a shared contract path
  outside T2 changes.
- A fresh static R3 reviewer receives no author/manager history, runs existing tests only,
  and reviews the exact retained set. No reviewer-authored security probes or CodeRabbit
  activity is included.
- If R3 remains `rework_required`, stop. Do not authorize a third remediation cycle
  without re-evaluating the T2 architecture and its research value.

## 6. Hard boundaries

This ruling does not authorize runtime code, credential resolution, provider calls,
T3/T4, T1b, eligibility, results, claims, publication, or mutation of accepted WP6.1,
T1a, W2, W7, W8, Receipt 1.0, ProviderCommand 1.0, or ProviderReceipt 1.0 bytes. P-037's
three command families, event ordering, sole-writer rule, and replay semantics remain
unchanged.

## Copy-paste owner decision

```text
I accept the proposed WP6.2 T2 research-first scope and R3 remediation ruling dated
2026-07-22 at the exact path, Git blob, raw-byte SHA-256 identity, and manager commit
stated in the acceptance packet. Apply the research-value gate, narrow T2 credential and
W7 assurance to the contract-stage subsets stated in P-039, and authorize one final
contract-only remediation of C1, C2, C4, M1, M3, and I1 followed by fresh static R3.
This authorizes no runtime implementation, credential resolution, provider call, T3/T4,
T1b, eligibility, result, claim, publication, or third remediation cycle.
```
