# WP6.2 T2 authority addendum R3 final static conformance review

**Date:** 2026-07-22
**Verdict:** `accept` for the P-039-bounded contract-only candidate
**Finding count:** 0 Critical, 0 Major, 0 Minor
**Lifecycle:** `final_fresh_static_r3`
**Workflow system:** standalone; no APM state, Memory Bank, manager history, or author history
**Review mode:** adversarial implementation-conformance review plus schema-contract tracing
**External review:** Stephen owns external review; no CodeRabbit activity was requested, triggered, polled, scheduled, or monitored

## Executive verdict

Candidate `391a92753d7f746fa91a6b5455c9ce0fd01baa52` closes retained
findings C1, C2, C4, M1, M3, and I1 under the exact accepted P-039 authority.
The P-039 scope correction is also implemented exactly: the T2
`PreIssueEvidenceManifest` and eight-seam evidence system are removed and deferred to
T3/T4, while ProviderCommand/ProviderReceipt 2.0 are restricted to the declared
`t2_authority_cost_subset`. No in-scope Critical, Major, or Minor finding remains.

The final R3 verdict is therefore **`accept`** for static contract conformance. This is
not owner acceptance of the candidate and grants no runtime authority. The candidate
remains proposed until Stephen separately accepts its exact hash. No provider call,
credential resolution, runtime implementation, T3/T4, T1b, eligibility, result, claim,
publication, or accepted-artifact mutation is authorized by this report.

## Exact review subject

| Item | Exact identity |
|---|---|
| Candidate | `391a92753d7f746fa91a6b5455c9ce0fd01baa52` |
| Candidate tree | `0254c5416925126412867d61b3045ee1563abd0c` |
| Direct parent/base wrapper | `bba49c11ef8cd37dee7fa571f712d77a954f6b16` |
| Candidate subject | `[PIPELINE] P00: finalize research-first WP6.2 T2 contracts` |
| Review branch | `review/ars-wp6-2-t2-authority-addendum-r3-static` |
| Initial branch equality | local, tracking, and independently queried live remote all equalled the candidate |

The Codex worktree started detached at the exact candidate. The pre-created review
branch resolved to the same commit, so the one permitted deterministic attachment was
performed. Before review and again before report creation, the symbolic branch, HEAD,
cwd, parent relationship, and clean status were verified.

## Exact controlling authority

All authority objects were resolved from Git, read as Git objects rather than mutable
working-tree copies, and independently rehashed before use.

| Source | Exact identity | Verification |
|---|---|---|
| Accepted P-039 proposal, `docs/plans/agentic-research-system/proposals/wp6-2-t2-research-first-scope-and-r3-remediation-ruling-2026-07-22.md` | commit `1301d8a5f089d27270c36b216967000a35472efc`; blob `1c6703b37579a0ffa35bfec0f9cccc7180a37f79`; raw SHA-256 `959ebeafa67368ffc87592134fd9c0caf385b4b562278789273563844295492f` | exact blob and raw hash matched |
| P-039 acceptance registration | commit `826ce6ad2cd83cbfc7a0db85b9ad068d91765b84`; parent `1301d8a5f089d27270c36b216967000a35472efc` | decision register records Stephen's acceptance and repeats the exact accepted proposal identity |
| Corrected R2 report, `docs/plans/agentic-research-system/reviews/adversarial-wp6-2-t2-authority-addendum-r2-review-2026-07-22.md` | commit `a10de8df9e0be8b381e6257aa761d8d8cea2506b`; blob `f93c030d59b7df74e08d4a960f28045a6c9fbec2`; raw SHA-256 `c2bb533d05d40f6720709406d98f096b288894c0eb0e044b44edcd3fc376cf8b` | exact blob and raw hash matched; read in full |
| Manager triage, `docs/plans/agentic-research-system/reviews/wp6-2-t2-r2-static-review-triage-2026-07-22.md` | commit `1301d8a5f089d27270c36b216967000a35472efc`; blob `0a8992239165d678439ac1994184cd796006e122`; raw SHA-256 `0e0314956f3b961e23e128bfb09f4dab420111d96da14f2f1287cb0974402373` | exact blob and raw hash matched; read in full |
| Author exact-state handback wrapper, `docs/plans/agentic-research-system/handoffs/trials/gate6-wp6-2-t2-authority-addendum-exact-state-handback.md` | commit `e1fe6b95cc9024cf40f1aa410f1a8970091bf4dc`; blob `4eb59472d31f682a99f34fd234c06055e5827545`; raw SHA-256 `4387b03d37632c577892489e6764d8996a4bb166ef39cb999a1f331e8d627ed0` | exact blob and raw hash matched; treated as evidence, not as the subject or oracle |

P-039 sections 2-4 control C3, M2, and the retained finding set. Its section 5
authorizes this one fresh static R3 and existing tests only. Its section 6 preserves the
no-runtime and immutable-accepted-byte boundaries.

## Candidate delta and exact-byte verification

The direct candidate delta contains exactly 27 paths: 26 present candidate blobs and
one P-039-authorized deletion.

```text
M .research-system/contracts/wp6-2-t2-cost-grant-authority-catalogue.yaml
M .research-system/contracts/wp6-2-t2-normative-crosswalk.yaml
A .research-system/contracts/wp6-2-t2-protected-membership.yaml
M .research-system/contracts/wp6-2-t2-schema-identities.yaml
M .research-system/schemas/contracts/wp6-2-t2-cost-grant-authority-catalogue.schema.json
M .research-system/schemas/contracts/wp6-2-t2-normative-crosswalk.schema.json
A .research-system/schemas/contracts/wp6-2-t2-protected-membership.schema.json
M .research-system/schemas/contracts/wp6-2-t2-schema-identities.schema.json
M .research-system/schemas/core/receipt-v2.schema.json
M .research-system/schemas/wp6-2-t2/commands/authorize-provider-issue.schema.json
M .research-system/schemas/wp6-2-t2/commands/issue-cost-grant.schema.json
M .research-system/schemas/wp6-2-t2/commands/record-provider-receipt.schema.json
M .research-system/schemas/wp6-2-t2/events/cost-grant-issued.schema.json
M .research-system/schemas/wp6-2-t2/events/cost-grant-reconciled.schema.json
M .research-system/schemas/wp6-2-t2/events/cost-grant-reserved.schema.json
M .research-system/schemas/wp6-2-t2/events/provider-command-issued.schema.json
M .research-system/schemas/wp6-2-t2/events/provider-receipt-recorded.schema.json
D .research-system/schemas/wp6-2-t2/pre-issue-evidence-manifest.schema.json
M .research-system/schemas/wp6-2-t2/provider-command-v2.schema.json
M .research-system/schemas/wp6-2-t2/provider-receipt-v2.schema.json
M .research-system/schemas/wp6-2-t2/secret-reference.schema.json
M docs/plans/agentic-research-system/design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md
M tests/research_system/contracts/test_wp6_2_t2_authority_contract.py
M tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py
M tests/research_system/contracts/wp6_2_t2_authority_validation.py
M tests/research_system/contracts/wp6_2_t2_expectations.py
M tests/research_system/contracts/wp6_2_t2_schema_materializer.py
```

For all 26 present paths, independently recomputed candidate Git blob IDs and raw Git
blob SHA-256 values matched the exact-state handback table `26/26`. Each blob decoded as
UTF-8, had no BOM or CR byte, and ended in LF. The deleted manifest schema is absent at
the candidate. Its exact parent identity is blob
`5cce21cde9f0cff1b1a97e90dad81b75ad27c56b`, raw SHA-256
`c4d12c62997f9bcccf1ed18d1c10d903ed47ab0dcc23b7bc5667cfd0c69e4a1e`.
`git diff --check` passed.

## Review methods

1. Activated `research-observer`, applied its OPEN observations for exact-byte/history
   fixtures and read-only validation, then used only `adversarial-design-review` and
   `schema-contract-design` as the two primary review skills.
2. Verified the exact candidate, authority objects, 27-path delta, blob hashes, encoding,
   and authorized deletion independently from Git.
3. Traced every retained finding from P-039 and the corrected R2 prescription through
   the addendum, strict schemas, independent literal expectations, semantic validators,
   normative crosswalk, and unchanged existing focused tests.
4. Checked restatements and composition seams, including Receipt-to-event proof,
   event-to-idempotency rebuild, command-to-independent-authority subjects,
   grant/reservation/receipt/reconciliation arithmetic, and protected-set derivation.
5. Recomputed the protected membership independently without importing the candidate
   materializer or validator.
6. Ran the existing focused WP6.2 T2 tests unchanged and the existing read-only contract
   framework validation in an LF-exact, history-bearing, long-path-enabled local clone.

## Retained-finding disposition

### C1 - closed: Receipt 2.0 enforces the complete ordered proof

Receipt 2.0 strictly represents the complete event proof, status branches, and duplicate
binding at `.research-system/schemas/core/receipt-v2.schema.json:6-23`, `:73-125`, and
`:165-257`. The semantic validator at
`tests/research_system/contracts/wp6_2_t2_authority_validation.py:578-652` enforces:

- exact command-specific event count and `new_event_count`;
- canonical event order;
- contiguous zero-based transaction positions;
- unique canonical `evt_` IDs;
- event-specific `cgr_`/`pcmd_` stream identities;
- `resulting_stream_version = prior_stream_version + 1`;
- accepted, duplicate, rejected, and conflict outcome rules; and
- duplicate equality for the complete ordered proof and outcome binding, the exact
  canonical original-receipt hash, and zero new events/invocations.

The existing decisive negative set is at
`tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py:603-620`, with
duplicate and zero-event outcome checks at `:507-531`. **R3 ruling: C1 closed.**

### C2 - closed: replay reconstruction uses the event-derived W2 tuple

All five strict event schemas require `command_id`, `actor_id`, `authority_scope`,
`command_type`, `idempotency_key`, `idempotency_key_hash`, and `payload_hash`. The
independent expected field set is recorded at
`tests/research_system/contracts/wp6_2_t2_expectations.py:112-120`.

`rebuild_idempotency_index` at
`tests/research_system/contracts/wp6_2_t2_authority_validation.py:518-575` accepts
canonical serialized event bytes, re-hashes the logical key, keys the index by
`(actor_id, authority_scope, command_type, idempotency_key)`, binds that tuple to
`(command_id, payload_hash)`, and rejects both tuple/binding disagreement and duplicate
effects. Existing tests prove exact reconstruction and same-tuple collisions across a
different command ID or payload at
`tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py:239-268` and
`:623-643`. **R3 ruling: C2 closed.**

### C4 - closed: every applicable authority subject is an unconditional exact triple

The independent command-by-command subject sets are literal, not derived from candidate
YAML, at `tests/research_system/contracts/wp6_2_t2_expectations.py:241-366`. They require:

- IssueCostGrant: CostGrant, ResourceGrant, Task, Dispatch, Attempt, ProviderCommand,
  and SecretReference triples;
- AuthorizeProviderIssue: the same seven plus reservation; and
- RecordProviderReceipt: CostGrant, ResourceGrant, Task, Dispatch, Attempt,
  ProviderCommand, ProviderReceipt, reservation, and SecretReference.

All corresponding command payload schemas require each `<stem>_id`,
`<stem>_revision`, and `<stem>_hash`. `validate_command_relations` at
`tests/research_system/contracts/wp6_2_t2_authority_validation.py:655-728` first proves
that every expected stem is a complete triple, then requires the payload fields and an
independently supplied canonical subject, and finally compares ID, revision, and content
hash unconditionally. Target, write-set, expected-version, deterministic-reservation,
event-order, stream, and resulting-version joins are checked in the same validator.
Existing schema and relational negatives are at
`tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py:443-468` and
`:646-683`. **R3 ruling: C4 closed.**

### M1 - closed: one mandatory gate composes shape, arithmetic, and evidence equality

`validate_t2_authority_cost_gate` at
`tests/research_system/contracts/wp6_2_t2_authority_validation.py:796-860` is the single
composed gate named by the addendum and crosswalk. It validates the strict CostGrant,
reservation, ProviderReceipt 2.0 subset, and reconciliation schemas; calls the integer
reconciliation validator; equates reservation ceilings with reconciliation; equates
provider actual/cost quantities with reconciliation; and requires exact currency plus
rate-evidence ID/revision/hash equality across all four objects.

The integer validator at `:731-784` excludes booleans and negative values, enforces
input/output/total identities and ceilings, handles metered and explicitly authorized
zero-cost modes, performs separate integer ceiling division for input and output,
enforces consumed cost within the reservation, and proves refund amount/disposition.
The existing schema-valid composed positive and the four independent evidence mismatch
negatives are at
`tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py:690-895`.
**R3 ruling: M1 closed.**

### M3 - closed: Receipt 2.0 stream IDs use exact lowercase UUIDv7 rules

Receipt 2.0 constrains event stream IDs to exact lowercase UUIDv7 `cgr_` or `pcmd_`
patterns at `.research-system/schemas/core/receipt-v2.schema.json:103-113`.
`validate_receipt_v2` applies the event-specific prefix through the canonical UUIDv7
validator at
`tests/research_system/contracts/wp6_2_t2_authority_validation.py:508-511` and
`:598-612`. Existing positive and malformed/case/version/variant/prefix negatives are at
`tests/research_system/contracts/test_wp6_2_t2_authority_contract.py:257-276` and
`tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py:549-561,898-902`.
**R3 ruling: M3 closed.**

### I1 - closed: exact 220-member contract and independent live recomputation

The normative contract
`.research-system/contracts/wp6-2-t2-protected-membership.yaml` commits exactly 220
`path|Git-blob|raw-Git-blob-SHA-256` rows at baseline
`69a0fee6171fc25f936c8e3e03343bfbd0338440`. Its candidate blob is
`e682ef7860b6d7fab5eaeb80bdeaea7a6401aaca`, raw SHA-256
`9e71924d9cfc9610490ffa6fe9bad15f5aa3c6cf32ef2f473a5fabf5497df64e`.

An independent R3 recomputation, implemented without importing the candidate
materializer or validator, reproduced:

- member count: **220**;
- sorted-map aggregate:
  `74c911466203f64277b2189c5fc2455c5644fa24818193cac33c19bed4e5c84c`;
- command tree: `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea`;
- event tree: `154ffc4bdde82fe903718734687e7a62797b1f69`;
- pre-addition core tree:
  `b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46`;
- Receipt 1.0 blob: `f204b3b71d6839bc866ba1251c8b87cc814ee0ce`;
- ProviderCommand 1.0 blob: `9eb58609b9703674912e64f019db3cd4fb147a9c`;
- ProviderReceipt 1.0 blob: `8ac904e6c0b16e45034bcdc2221970d6a3ef13a8`.

Every contract row matched the independently derived baseline row and every one of the
220 current candidate blobs matched its baseline identity. The whole current `core/`
tree is correctly different because Receipt 2.0 is an authorized new successor; the
member-by-member predecessor comparison remains exact.

The repository validator independently derives the expected paths, recomputes each
baseline object and aggregate, and compares all live candidate objects at
`tests/research_system/contracts/wp6_2_t2_authority_validation.py:263-330`. The
materializer does not import or construct that expected set; it reads the committed
membership only when binding the identity manifest. The existing omission, live-set,
and dependency-direction tests are at
`tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py:905-936`.

The normative crosswalk is separately authored and checked against the literal
`EXPECTED_CROSSWALK` at
`tests/research_system/contracts/wp6_2_t2_expectations.py:159-239` and
`tests/research_system/contracts/wp6_2_t2_authority_validation.py:492-497`; the
materializer does not import that expectation or emit the crosswalk document.
**R3 ruling: I1 closed.**

## P-039 scope-narrowing disposition

### C3 narrowing - confirmed

The strict SecretReference remains at
`.research-system/schemas/wp6-2-t2/secret-reference.schema.json:1-193`. It carries the
opaque identity, revision/hash, provider and credential class, typed resolver identity,
resolver version, allowed scope, expiry, revocation binding, and redaction declaration.
Its objects are closed and contain no raw credential or resolver-output field.

The obsolete `pre-issue-evidence-manifest.schema.json` is absent at the candidate. An
exact Git-object search found no `PreIssueEvidenceManifest`,
`pre_issue_evidence_manifest`, or `PRE_ISSUE_SENTINEL_SEAMS` token in the T2 catalogue,
crosswalk, identity manifest, T2 schemas, validator, materializer, expectation source,
focused tests, or addendum. The existing absence test is at
`tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py:939-964`.

This is the P-039 timing amendment: strict opaque metadata and exact binding remain;
eight-seam runtime evidence is deferred. **R3 ruling: P-039 C3 narrowing confirmed.**

### M2 narrowing - confirmed

ProviderCommand 2.0 and ProviderReceipt 2.0 declare
`x-t2-validation-scope: t2_authority_cost_subset` and explicitly defer remaining W7
sections 9/10 runtime evidence at
`.research-system/schemas/wp6-2-t2/provider-command-v2.schema.json:5-6` and
`.research-system/schemas/wp6-2-t2/provider-receipt-v2.schema.json:5-6`.

Their strict required groups cover the P-039 subset: command/receipt and W2 identity;
provider/model/profile/adapter/policy; Task/Dispatch/Attempt/grant/reservation/
SecretReference; payload/context evidence; permission summary/hash; token and cost
ceilings/actuals/rate evidence; issue/terminal and retry/reconciliation state; output
references; and redaction/omission declarations. The candidate no longer claims
`complete_w7`, and provider-native IDs, tool-action execution, resource/process
observations, transport, and broader runtime qualification are absent from the exact T2
surface. The existing exact-subset tests are at
`tests/research_system/contracts/test_wp6_2_t2_authority_contract.py:245-254` and
`tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py:967-975`.

This is a scope reduction, not a claim that full W7 has been qualified.
**R3 ruling: P-039 M2 narrowing confirmed.**

## Severity-ranked findings

No findings. Specifically:

- Critical: 0
- Major: 0
- Minor: 0

No rejected attack crossed an in-scope authority, evidence, replay, arithmetic,
identity, composition, or independent-oracle boundary. Orthogonal later-stage
hardening is recorded below and is not promoted into a T2 research-blocking finding.

## Validation evidence

| Check | Result |
|---|---|
| Candidate/authority/blob identities | exact matches; PASS |
| Candidate delta | 27 paths: 26 present, 1 authorized deletion; PASS |
| Present-candidate blob table | 26/26 blob and raw SHA-256 identities matched; UTF-8/no BOM/LF/final LF; PASS |
| Protected membership independent recomputation | 220/220 members; aggregate `74c911466203f64277b2189c5fc2455c5644fa24818193cac33c19bed4e5c84c`; PASS |
| Validation fixture | local no-hardlink clone, `core.autocrlf=false`, `core.longpaths=true`, detached at exact candidate, 3,273 tracked paths and 0 missing, clean |
| Existing focused WP6.2 T2 tests unchanged | **135 passed in 92.54s** |
| Existing contract framework `--validate-only` | **all gates passed against 102 contracts** |
| Repository artifacts after validation | no `.venv`, `.pytest_cache`, coverage file, tracked change, or untracked change in validation clone; review root stayed clean |
| `git diff --check` | PASS |

The tests used the pre-existing external interpreter
`C:\Users\steph\TDL\.venv\Scripts\python.exe` (Python 3.13.5, pytest 9.0.2),
with bytecode, plugin autoload, pytest cache, and configured coverage addopts disabled.
No dependency installation, network dependency fetch, repo-local environment, lockfile
mutation, cache, or coverage artifact occurred.

## Explicit omissions

- The full 665-test framework was not run; P-039 explicitly omits it for this candidate.
- No reviewer-authored security payload, fuzzing, mutation probe, scanner, credential
  test, secret resolution, provider call, penetration test, or external service was run.
- No runtime implementation or live adapter path was executed.
- No deterministic artifact was regenerated. Existing artifact bytes had already been
  certified; this review used independent read-only identity and semantic validation,
  so regeneration was neither necessary nor authorized.
- The normal write-capable contract hook mode was not run. Its read-only
  `--validate-only` mode passed 102 contracts, and the focused suite supplied the
  existing behavioral execution.
- Ruff/format and the author's materialization comparison were not redundantly rerun;
  this review made no candidate source edit and independently certified candidate bytes.
- CodeRabbit was not used.

These omissions are deliberate scope boundaries, not candidate findings.

## Residual research risk

1. This is a contract-only static review. It establishes the required representations,
   validators, identities, negative controls, and exact predecessor protections; it does
   not establish that a future CommandService implementation invokes every mandatory
   gate in the required order.
2. No empirical research result, statistical estimate, mathematical result, dataset,
   eligibility decision, claim, or publication artifact was produced or assessed.
3. Future runtime implementation must preserve the exact independent expected-record
   boundary for authority triples and must treat incomplete provider receipts as
   diagnostic-only. That integration remains separately gated rather than inferred from
   these green contract tests.

None of these residual research risks invalidates the present contract-stage verdict.

## Orthogonal operational and security hardening

The following is explicitly outside the blocking R3 research verdict and remains for an
authorized later lifecycle stage:

- qualify the actual resolver, protected authentication channel, transport, logging,
  exception, telemetry, and persistence surfaces at T3/T4;
- re-specify and execute the accepted eight-seam matrix only against real adapter
  surfaces and approved harmless runtime fixtures;
- qualify provider-native IDs, tool actions, cancellation, process/resource
  observations, and the rest of W7 sections 9/10;
- prove live secret non-persistence and provider-specific redaction/omission behavior;
  and
- execute broader operational or security testing only under a separately justified
  research-value gate and owner authority.

These items do not contradict an in-scope T2 guarantee and therefore do not block the
`accept` verdict.

## Operational residue

The two pre-existing external temporary paths named in the dispatch were not used or
deleted:

- `C:\Users\steph\AppData\Local\Temp\tdl-c275-hook-venv-20260722-225620`
- `C:\Users\steph\AppData\Local\Temp\tdl-wp6-2-r3-baseline-96cd82f61c264194a3f57ced21eee8e8`

This review created one recoverable local validation clone outside the repository:

- `C:\Users\steph\AppData\Local\Temp\tdl-wp6-2-r3-static-405f-019f8beb`

It is detached at the exact candidate and clean. An exact, validated recursive cleanup
command was blocked by execution policy, so the clone remains as non-candidate residue.
It contains no environment, cache, coverage artifact, credential, provider output, or
research result.

## Decision and change audit

| Decision / obligation | R3 disposition |
|---|---|
| P-037 three-command family and sole writer | keep; exact |
| P-037 ordered atomic batches and replay semantics | keep; exact |
| C1 | closed |
| C2 | closed |
| C4 | closed |
| M1 | closed |
| M3 | closed |
| I1 | closed |
| P-039 C3 narrowing | confirmed |
| P-039 M2 narrowing | confirmed |
| Runtime/T3/T4/T1b/result/claim/publication authority | absent; keep hard stop |
| Third remediation cycle | not authorized and not required by this verdict |

## File-change log

This review adds only:

- `docs/plans/agentic-research-system/reviews/adversarial-wp6-2-t2-authority-addendum-r3-review-2026-07-22.md`

The immutable candidate and all 27 candidate paths remain unmodified.
