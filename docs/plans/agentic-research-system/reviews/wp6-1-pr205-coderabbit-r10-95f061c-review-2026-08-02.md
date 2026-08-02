# WP6.1 PR #205 CodeRabbit R10 Exact-Subject Review - 95f061c

**Date:** 2026-08-02

**Review mode:** fresh independent exact-subject review of the five supplied
CodeRabbit correction findings and their integration against pinned current
main. Production, tests, workflow, and producer records were read-only; this
record is the only review-owned repository path.

**Findings:** 0 Critical, 0 Major, 0 Minor

**Verdict:** `accept_exact_subject`

## 1. Exact subject and authority boundary

| Field | Exact value |
|---|---|
| Repository / remote | `stephendor/TDL`; `https://github.com/stephendor/TDL.git` |
| Review worktree | `C:\Users\steph\.codex\worktrees\532b\TDL` |
| Review branch | `codex/pr205-coderabbit-r10-integration-review` |
| Pinned current-main base | `207d92d93dd614e5e5f70c781d4bd11110b17488` |
| Exact candidate | `95f061c5cb8fed45aa1e266331711a752c1641fe` |
| Candidate tree | `b57855c75dbd91d9f0659a2ae973e0efb40ecc07` |
| Candidate parents | `57890921cf2f01857b0f212dbf302ce172d6eef0`, `207d92d93dd614e5e5f70c781d4bd11110b17488` |
| Supplied review inventory | `PRR_kwDOQn1MU88AAAABIGko0A` |
| Authority/security producer | `34b3619fe7275a31125b97ae767c1978033be69d`, tree `e4e59e9e28e5843996e4eed85041ef8ceed3bf87` |
| Mechanical producer | `bd6427fd683299ec20f46ba8feea912cc2a05484`, tree `7891263f9f913b24648ecbb6c97f4f029d797add` |
| Accepted prior PR head | `c72a69791b909c1e47fcb8b35442470a7f00a0c1`, tree `9ad319ee92898d7afb78eecaa53eccf5770e81fb` |
| Merge base | exactly the pinned current-main base |
| Candidate range | 18 paths; 5,932 insertions and 275 deletions |
| Review-owned path | this record only |

At entry, detached `HEAD`, the named local branch ref, its upstream, and the
live remote branch all equalled the exact candidate, the tree matched, and the
worktree was clean. The required base, both correction producers, and the
accepted prior head were all ancestors of the candidate. I made the single
permitted deterministic branch attachment and created no fallback branch or
detached commit.

This review did not modify or contact PR #205, GitHub comments or checks,
CodeRabbit, Jira, or any producer worktree. It did not request, trigger, poll,
or wait for a review service and grants no merge or dispatch authority.

## 2. Complete pinned-base scope

The complete `207d92d..95f061c` range contains exactly these 18 paths:

1. `.github/workflows/ci.yml`
2. `docs/plans/agentic-research-system/implementation/06k-wp6-1-authority-source-and-lock-identity-design.md`
3. `docs/plans/agentic-research-system/reviews/wp6-1-composite-lock-lease-ea589d1-review-2026-08-02.md`
4. `docs/plans/agentic-research-system/reviews/wp6-1-pr205-coderabbit-integration-45bec00-review-2026-08-02.md`
5. `research_system/authority.py`
6. `research_system/command/service.py`
7. `research_system/evals/executors/release_tranche.py`
8. `research_system/store/lock.py`
9. `tests/research_system/factories.py`
10. `tests/research_system/integration/test_authority_grant_source.py`
11. `tests/research_system/integration/test_gate5_release_tranche.py`
12. `tests/research_system/integration/test_wp6_1_scope_task_authority.py`
13. `tests/research_system/integration/test_wp6_1_task_scope_lifecycle.py`
14. `tests/research_system/unit/test_command_service.py`
15. `tests/research_system/unit/test_release_publication.py`
16. `tests/research_system/unit/test_replay.py`
17. `tests/research_system/unit/test_store.py`
18. `tests/research_system/unit/test_wp6_2_t2_runtime.py`

All four production surfaces, the workflow, the three documentation records,
and every changed fixture/test surface were inspected. The prior review records
were treated as exact historical evidence, not as proof of the current
candidate. In particular, the older `45bec00` record accurately describes the
API at its pinned subject; its historical reference to a public projection is
not a current API contract.

## 3. Five-finding disposition

| # | Disposition | Independent evidence at the candidate |
|---:|---|---|
| 1 | Closed | The `windows-store-lock` job has job-level `permissions: {contents: read}` and its sole `actions/checkout@v4` step sets `persist-credentials: false` (`.github/workflows/ci.yml:48-57`). PyYAML structural assertions passed. Exact parsed-object comparison proved both Ubuntu jobs, `lint-and-test` and `petls-backend`, semantically unchanged from the pinned base. |
| 2 | Closed | The prior review record uses the exact code token `` `(deleted)` `` with no leading space (`wp6-1-pr205-coderabbit-integration-45bec00-review-2026-08-02.md:89`). A positive exact-token assertion and a negative leading-space assertion both passed. |
| 3 | Closed | `LedgerAuthorityGrantResolver` exposes no public mutable projection. `resolve_lifecycle_command` owns one `_projection()` invocation, derives bound administration context, owner class, command authorization, and canonical identity internally, and returns only nested frozen dataclasses (`authority.py:705-718`, `2048-2113`). `CommandService` accepts only the exact resolver/evidence/context/resolution types, checks project and owner-derived actor class, and requires command resolution to equal canonical grant identity before append (`service.py:220-229`, `1087-1162`). Fresh resolution occurs inside the domain-plus-authority composite lock and before receipt lookup or append (`service.py:344-390`, `573-609`). |
| 4 | Closed | Public `resolve_command` has no `projection` parameter. Its Args, Returns, Raises, and Security sections describe active schema identity, trusted caller actor class for the generic API, current UTC/risk/scope constraints, fresh bound-store replay, and the separate bootstrap-owner lifecycle API (`authority.py:1987-2046`). Signature and documentation assertions passed against the imported candidate API. |
| 5 | Closed | `GovernedTestCommandService._before_submission_lock` explains that restore mode reuses the deterministic scoped grant already activated in the sibling authority store and must not activate it again (`tests/research_system/factories.py:430-438`). The moved-restore positive exercised that branch through the real command service and passed. |

## 4. Semantic authority and negative-control audit

### 4.1 Replay ownership, provenance, and immutable evidence

`_projection` verifies the configured physical store identity, canonical
bootstrap bytes/hash, ledger replay, owner-administration decisions, grant
objects, and bootstrap-to-ledger bindings before returning internal state
(`research_system/authority.py:1414-1458`, `1460-1499`, `1522-1592`). The public
lifecycle API never returns that mapping. Its result, administration context,
scope, command resolution, and canonical identity are frozen dataclasses.

The accepted-path control counted exactly one authority replay and proved the
bundle and every nested evidence object reject mutation. Direct API negatives
proved that stale pre-revocation, caller-mutated revoked, foreign-resolver, and
synthetic unactivated projections cannot be supplied to any public lifecycle
authority API. The internal status guard admits only exact `active`; `revoked`
and every unknown status fail closed (`authority.py:1865-1881`).

### 4.2 Exact owner, type, command, scope, risk, and canonical joins

Owner classification is derived from the replay-verified bootstrap context,
not from a caller `actor_class`. The resolver validates the active command
binding and exact schema bytes, actor identity, allowed command tuple, exact
project/subject scope, risk ceiling, effectiveness, expiry, and active status
before returning evidence (`authority.py:1938-1985`, `2086-2113`). The service
then checks exact concrete evidence types, the context project, owner-derived
actor class, and equality of current command resolution with canonical grant
identity (`service.py:1127-1146`).

The complete negative set covered non-owner, foreign project, wrong subject,
wrong command/schema identity, insufficient risk, not-effective, expired,
revoked, unknown status, foreign store identity, synthetic object without
activation history, tampered activation history, missing/ambiguous/hash-drifted
canonical objects, and resolver substitution. Each failure precedes domain
mutation and, where applicable, receipt/index creation.

### 4.3 Lock interval, revocation, replay, and receipt reconciliation

Lifecycle submissions acquire one `CompositeWriterLock` over the domain root
and the exact resolver root. The resolver replay, current-authority decision,
receipt lookup/reconstruction, domain append, history join, and scoped receipt
write all occur before that lease exits. The two deterministic race controls
proved both orderings: a domain-first command commits before later revocation;
a revocation-first command replays the revoked grant and rejects without domain
mutation.

Receipt reconciliation cannot regenerate missing authority evidence. A
lifecycle receipt is looked up only after a fresh lifecycle bundle exists
(`service.py:1164-1189`). `_validate_lifecycle_authority_history` requires a
supplied canonical resolution and fails if it is absent or hash-disagrees; it
has no replay/projection fallback (`service.py:801-835`). Accepted receipts are
joined to the exact event type, transaction, command and payload hash, stream
and version, project, actor, authority grant, and command-schema identity before
index reconstruction (`service.py:736-799`).

Missing-index recovery passed only with the fresh canonical join. Missing,
tampered, ambiguous, and hash-mismatched authority evidence all failed closed;
a forged command-resolution hash could not coordinate with the independent
canonical value. Restart retry rechecked current expiry/revocation rather than
returning an old accepted receipt as fresh authority.

### 4.4 API migration and escalation check

Repository-wide caller inventory found no production `projection()` method,
no production `projection=` argument, no mutable authority-projection field,
and no lifecycle production caller of generic `resolve_command`. The only
production lifecycle edge is
`CommandService._resolve_lifecycle_authority -> resolve_lifecycle_command`.
Generic `resolve_command` explicitly retains caller-class semantics for its
non-lifecycle contract; lifecycle owner authority uses the owner-derived API.

No schema, contract, catalogue, schema-registry, provider, grant-creation,
activation, revocation, owner-decision, or actor identity was added or weakened
by the R10 correction. There is no new caller self-attestation or authority
escalation path within the reviewed production call graph.

## 5. Pinned-main integration and protected bytes

The candidate's merge base with the supplied main parent is exactly
`207d92d...`. Both R10 producers are direct children of the accepted prior head;
`5789092...` merges them, and `95f061c...` merges that correction integration
with pinned current main. The complete base-to-candidate range remains below
the supplied 100-path cap at 18 paths.

| Protected object | Base identity | Candidate identity |
|---|---|---|
| `.research-system/schemas` tree | `b36fec20f89e22f9cd5811fa289c2fe4c029ffba` | same |
| `.research-system/contracts` tree | `4138918ab422eec604e8f3251c8846c8227870b4` | same |
| root `contracts` tree | `49dfb3bf5e698d6f815e9a475ee54153ff49fd9c` | same |
| `.research-system/evals/catalogue.yaml` blob | `98f6413d49606e7553e74cd2fb24f914b087f133` | same |
| `research_system/schema_registry.py` blob | `740e2d9f26836bfa43699d6cf8ebc7c9ac027edb` | same |
| `research_system/adapters/provider.py` blob | `f7f8152a9fad3347ca83996622268907631250e1` | same |

The protected-path diff count is zero. The current-main W11 contract/schema
materialization is present identically on both sides of the pinned comparison;
none of those bytes is part of the PR delta. No contract or schema byte drift
was introduced by integration.

## 6. Independent validation

All commands ran at exact candidate `95f061c...` from the review worktree with
the primary checkout's locked Python 3.13.5 environment. Repository coverage
and pytest cache were disabled. No full repository suite ran.

| Validation | Result |
|---|---|
| `C:/Users/steph/TDL/.venv/Scripts/python.exe -m pytest -p no:cacheprovider --no-cov -q tests/research_system/integration/test_wp6_1_scope_task_authority.py` | 39 passed in 15.56s |
| `C:/Users/steph/TDL/.venv/Scripts/python.exe -m pytest -p no:cacheprovider --no-cov -q tests/research_system/integration/test_gate5_release_tranche.py::test_real_command_service_accepts_only_current_verified_moved_restore` | 1 passed in 6.81s |
| Ruff check over all 14 changed Python paths | passed |
| Ruff `format --check` over all 14 changed Python paths | 14 already formatted |
| Workflow PyYAML structural assertions | passed; Windows least privilege present and both Ubuntu jobs unchanged |
| Exact Markdown token positive/negative assertions | passed |
| Public `resolve_command` signature/documentation assertions | passed |
| `git diff --check 207d92d..95f061c` | passed |
| SHA/tree/ancestry/path-count/protected-identity checks | passed |
| Candidate local/upstream/live-remote equality and pre-write status | all `95f061c...`; clean |

The 39-test authority module includes the public-surface, one-replay/frozen
bundle, stale/mutated/foreign/synthetic/unknown-status, canonical-history,
receipt-rebuild, expiry, revocation-race, and resolver-substitution negatives.
Passing execution supports, but does not replace, the source-level verdict.

## 7. Residual risk and non-authorization

No candidate-caused Critical, Major, or Minor defect remains in the reviewed
18-path range. The following bounded residuals remain visible:

1. The full repository suite was intentionally not run. Confidence is limited
   to the complete changed authority module, required restore node, static
   checks, direct artifact assertions, and source-level integration audit.
2. The workflow least-privilege correction was structurally validated locally;
   this review did not trigger or inspect a new GitHub Actions run.
3. The accepted composite-lock design's stated boundary remains: store I/O is
   not wholly handle-relative after the final fence, and privileged mutation of
   the running process or unanchored ancestor is outside this correction.
4. The generic public command resolver deliberately accepts a trusted caller
   actor class. Bootstrap-owner lifecycle commands do not use that generic
   classification path.

Acceptance is limited to exact candidate
`95f061c5cb8fed45aa1e266331711a752c1641fe` and tree
`b57855c75dbd91d9f0659a2ae973e0efb40ecc07`. The later review-record commit is
provenance only and is not a newly reviewed production subject. This decision
does not authorize PR mutation, comment or thread closure, Jira changes,
CodeRabbit activity, merge, dispatch, or any producer remediation.
