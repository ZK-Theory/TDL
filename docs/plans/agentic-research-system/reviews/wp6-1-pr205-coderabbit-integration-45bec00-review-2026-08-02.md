# WP6.1 PR #205 CodeRabbit Integration Exact-Subject Review — 45bec00

**Date:** 2026-08-02

**Verdict:** `accept_exact_subject`

**Findings:** 0 Critical, 0 Major, 0 Minor

**Review mode:** fresh independent exact-subject review of the combined
CodeRabbit remediation. Candidate production and test files were read-only;
this report is the only review-owned repository path.

## 1. Exact subject and authority boundary

| Field | Exact value |
|---|---|
| Worktree | `C:\Users\steph\.codex\worktrees\7e26\TDL` |
| Review branch | `codex/pr205-coderabbit-integration-r9-review` |
| Required base | `ba087e33df585148251e6e71c3a4d0faa1b3021c` |
| Semantic source | `9682e3fc9c78e0e9d07305dadc0a311e1bcda856`, tree `abb2405ddfe12970bde4d55bd18ad14cc7b40417` |
| Cleanup source | `89f8e3b82d51ec1e7e318bf0d1b37e109e8d1b84`, tree `0e64693a24fdc717c77c17c3f377a1ed33fabcff` |
| First integration merge | `c37265e04b88419a9700254ab85c7f2487cc466d` |
| Candidate / second merge | `45bec009698efad021f86e2edbe9bbb8cbcfb11b` |
| Candidate tree | `d64a08d5ebf9fe54dd0bdd1fd6f4aa15d61af8da` |
| Entry state | detached `HEAD`, local branch, tracking ref, and live remote review ref all equalled the candidate; status clean |
| Branch attachment | one deterministic `git switch codex/pr205-coderabbit-integration-r9-review`; no fallback branch or commit |
| Candidate correction range | 15 paths: disjoint 10-path semantic and 5-path cleanup sets |
| Projected PR range | 17 paths by `git diff origin/main...candidate`, using merge base `6c32f17a7951ee1a01ca48b9fcaf7782125ac09e` |
| Review-owned path | this report only |

The reviewed subject is the immutable candidate `45bec009...`, not the later
review-record commit. At the final pre-write check, local `HEAD`, upstream, and
the live remote review ref all equalled that candidate and the worktree was
clean.

The two completed CodeRabbit reviews
`PRR_kwDOQn1MU88AAAABIC5xuQ` and
`PRR_kwDOQn1MU88AAAABIE3URg` were read once as the fixed claim inventory. No
review was requested, triggered, polled, or awaited. Producer history and
producer test totals were not acceptance evidence; every numbered disposition
below was checked against candidate source and independent execution.

## 2. Integration identity and byte preservation

The source subjects are direct children of the required base:

- `9682e3fc^` = `ba087e33...`;
- `89f8e3b8^` = `ba087e33...`.

The merge chain is exact and ordered:

- `c37265e` parents are `ba087e33...` then `9682e3fc...`;
- `45bec009` parents are `c37265e...` then `89f8e3b8...`.

The base-to-semantic range contains 10 paths, the base-to-cleanup range contains
5 paths, their overlap is empty, and their sorted union equals the complete
15-path base-to-candidate range. Per-path Git blob comparison found zero
mismatches between each source commit and the candidate, so neither merge
altered source bytes.

The projected PR count is the GitHub-style three-dot range. The live
`origin/main` was `207d92d93dd614e5e5f70c781d4bd11110b17488`; its merge
base with the candidate was `6c32f17...`, and
`git diff --name-only origin/main...45bec009` returned exactly 17 paths. A
two-dot tip-to-tip tree comparison is not the PR range and was not used for the
limit decision.

### Protected accepted identities

| Protected object | Base identity | Candidate identity |
|---|---|---|
| `.research-system/schemas` tree | `a1728d331f03aa8ecf09d4a3e739b55c18263a86` | same |
| `.research-system/contracts` tree | `27f1e12e8ecfb5c6fb33377981a96410555cbd56` | same |
| `.research-system/evals/catalogue.yaml` blob | `98f6413d49606e7553e74cd2fb24f914b087f133` | same |
| `research_system/schema_registry.py` blob | `740e2d9f26836bfa43699d6cf8ebc7c9ac027edb` | same |
| `research_system/adapters/provider.py` blob | `f7f8152a9fad3347ca83996622268907631250e1` | same |
| accepted composite-lock review blob | `e9e94ef7e4c103dba95aad6cc7195199a2a25b5d` | same |

No schema, contract, catalogue, accepted-review, or provider identity changed.

## 3. Semantic disposition completeness — findings 1–25

| # | Independent disposition | Candidate evidence |
|---:|---|---|
| 1 | Closed | 06k L-8 now states that acquisition, fence, and body errors remain primary; all reverse-order cleanup attempts run and the first cleanup error is chained. The existing acquisition control and an independent body-error probe both passed. |
| 2 | Closed as a design correction | 06k A-1/A-2 explicitly close `ControlStoreT2AuthorityResolver` over `IssueCostGrant` and `AuthorizeProviderIssue` and keep the six Scope/Task lifecycle commands on `LedgerAuthorityGrantResolver.resolve_command`. No runtime family conflation was introduced. |
| 3 | Correctly retained as design-only, not reported green | 06k A-9, the execution sequence, and A-N10 require current-authority revalidation on T2 retry. Current runtime still returns an exact retry as `duplicate` after the authority record is changed to revoked; the independent probe confirmed that boundary. The document is explicitly `design decision only; no runtime implementation or activation`, and this candidate makes no `t2.py` implementation claim. |
| 4 | Closed | The 06k failure matrix now snapshots each physical store that exists and separately requires an absent L-N1 root or L-N2 runtime directory to remain absent. |
| 5 | Closed | POSIX `delete_protect` is propagated through `_open_directory_anchor`, `_open_posix_anchor`, refresh, and final-path resolution. Protected `st_nlink <= 0` and Linux ` (deleted)` cases fail closed; unprotected compatibility remains. The three changed POSIX controls passed, including both protected parameter cases. |
| 6 | Closed | `.github/workflows/ci.yml` adds one focused `windows-store-lock` job without changing the Ubuntu job. Its exact six-name selection executed independently on Windows as 7 parametrized cases: all passed. |
| 7 | Closed | `_resolve_lifecycle_authority` clears both `resolution` and `canonical_resolution` on `ArsError`, and `authority_key` is guarded by `canonical_resolution`. The partial-evidence denial control passed with zero writes. |
| 8 | Closed | `LedgerAuthorityGrantResolver.projection()` is public and documents same-resolver trust; the service uses it once and passes the projection back only to that resolver. The one-public-projection control passed. |
| 9 | Skip upheld | The four-behavior composite cleanup test remains one cohesive, deterministic failure setup. Splitting it would duplicate setup without improving the independently exercised acquisition, body-error, and normal-cleanup branches. |
| 10 | Closed | The redundant release-publication resolver reassignment is absent. The affected authority-failure cases completed successfully. |
| 11 | Closed | The release-schema negative now explains that it borrows a fully registered authority store while removing only release-event schemas from the domain registry. |
| 12 | Closed | The tautological T2 command-type parametrization is gone. The remaining resolver-root and two-command revocation controls passed. |
| 13 | Already satisfied, independently confirmed | `_authority_key` accepts only a canonical 64-character lower-case digest, while the receipt reconciliation tests compare independently derived canonical history and resolved evidence. The independent canonical-value control passed. |
| 14 | Already satisfied and strengthened | One authority projection is captured under the composite lock and reused for actor identity, command resolution, scoped identity, receipt reconciliation, and write. The complete scope-authority module, including lock/revocation races, passed 33/33. |
| 15 | Already satisfied | Release schema binding absence fails closed before dereference. `test_release_append_requires_exact_registered_release_schema` passed with no release write. |
| 16 | Closed | The activation-tamper control rewrites only the selected `ActivateAuthorityGrant` JSONL line, preserves the other lines and original line ending, then observes fail-closed canonical-history reconstruction. The tamper cases passed. |
| 17 | Already satisfied | The envelope-mismatch test is accurately named and the direct `authority_resolver=None` publication control expects `release_publication_authorizer_unavailable` with no ledger event. Both completed successfully. |
| 18 | Already satisfied | Release publication uses `_canonical_authority_resolver`; no obsolete duck-typed publication helper or reachable missing-resolver continuation remains in that path. |
| 19 | Already satisfied | `_resolve_lifecycle_authority` reads project, subject kind/id, and required risk from the already built binding instead of recomputing lifecycle inputs. |
| 20 | Already satisfied | `_COMMAND_EVENT_TYPES` is one complete module-level mapping, and an unknown key becomes an explicit `IntegrityError`. |
| 21 | Already satisfied | `_authority_key` takes only the resolution and has no unused binding parameter. |
| 22 | Already satisfied | Shared command-ID conflict handling is centralized; the remaining receipt paths have different reconciliation semantics and are not identical copies. |
| 23 | Closed | The unreachable lifecycle-only `invalid_command_project` pre-branch is removed; non-lifecycle handling remains. Foreign project submissions still produce deterministic `lifecycle_authority_unauthorized` receipts with the exact explanation and no mutation. |
| 24 | Closed | `_real_lifecycle_service` now types `schemas` and its returned tuple, and documents Args/Returns. Ruff and format checks passed. |
| 25 | Closed | Dead `GRANTS` / `grant_id` plumbing is removed from the authority integration fixture; the real activated grant remains installed by `_submit`. The full module passed. |

All 25 semantic findings are therefore dispositioned. Finding 3 remains an
explicit, reproduced future implementation obligation; it is not represented
as behavior delivered by this candidate.

## 4. Cleanup disposition completeness — findings 1–12

| # | Independent disposition | Candidate evidence |
|---:|---|---|
| 1 | Already satisfied | The authority service, plain domain service, and `GovernedTestCommandService` all receive the same injectable `clock`. The shared-clock control passed. |
| 2 | Already satisfied | Default revocation decisions derive from the subject grant through `_revocation_decision_id(grant_id)` rather than a global constant. The per-grant uniqueness control passed. |
| 3 | Closed | `ControlPlaneHarness.schemas` is `SchemaRegistry`; harness construction uses explicit keywords. Runtime construction and all selected consumers succeeded. |
| 4 | Closed | `GovernedTestCommandService` is public-named consistently, documents actor-a overwrite and `auto_authority=False`, and has typed constructor/hook signatures. Gate 5 imported and used it successfully. |
| 5 | Closed | `scoped_lifecycle_grant_id`, `activate_lifecycle_grant`, and `revoke_lifecycle_grant` have accurate Args/Returns/Raises documentation without inventing exceptions. Ruff/format passed. |
| 6 | Closed | Gate 5 `_moved_service` distinguishes `authority_harness_root` from the harness attribute. The real moved-restore service positive passed. |
| 7 | Closed with a separate pre-existing test defect | The supersession test stores and uses the grant returned by `activate_lifecycle_grant`; it no longer recomputes it. The repository node fails before reaching that behavior because its unchanged `TrackingLock` lacks `.path`/`.identity`. An interface-complete equivalent reused the returned grant and passed the cycle rejection under the live lock. |
| 8 | Closed | The accepted-vs-foreign retry control asserts the exact accepted receipt remains in `ReceiptStore` and the event set is unchanged. It passed. |
| 9 | Closed | Foreign-project Scope and Task denials assert `authority subject scope mismatch` and the exact `lifecycle_authority_unauthorized` unmet prerequisite. Both controls passed. |
| 10 | Closed | The renamed unbound-schema-version control asserts zero event batches, no receipt, and no object JSON writes. It passed. |
| 11 | Closed | Command-service setup uses `harness.service.control_root`; the affected generic-history control passed. |
| 12 | Closed | Replay asserts `lifecycle_authority_unauthorized`, the matching unmet prerequisite, and explains the deliberately unactivated CLI store. The replay control passed. |

All 12 cleanup findings are dispositioned. Findings 1 and 2 were already
satisfied at the exact base and required no rewrite; findings 3–12 are present
in the cleanup source bytes and remain unchanged through integration.

## 5. Independent execution evidence

All pytest commands used
`C:\Users\steph\TDL\.venv\Scripts\python.exe` directly with bytecode,
third-party plugin autoload, cache, and coverage disabled. No full suite ran.

| Surface | Independent result | Adjudication |
|---|---|---|
| `tests/research_system/unit/test_release_publication.py` | completed in 348.23s: 100 collected, 98 passed, 2 failed | Not called green. Both failures are source-proven exact-base test defects; all changed release-schema/publication nodes passed. |
| Changed Gate 5 node `test_supersession_graph_and_rejected_receipt_io_stay_inside_writer_lock` | completed in 308.11s: 1 failed with `ConflictError: writer lock ownership record is unavailable` | Not called green. The unchanged test double omits the production lock interface; failure occurs before the candidate grant-reuse assertion. |
| Interface-complete equivalent of the changed Gate 5 node | passed | Returned grant reused; supersession cycle rejected; graph preparation and rejected-receipt write occurred under the live lock; lock inactive afterward. |
| `test_wp6_1_scope_task_authority.py` | 33 passed in 19.08s | Shared six-command resolver/projection, zero-write denial, canonical evidence, retry/revocation, and composite lock behavior green. |
| Non-overlapping changed cross-surface batch | 16 passed in 27.68s | Windows/POSIX cleanup, project/receipt/replay explanations, unbound-schema zero-write denial, and T2 resolver separation green. |
| Exact `windows-store-lock` workflow selection | 7 passed, 67 deselected in 0.47s | Windows CI selection is real and executable. |
| Moved-restore service positive | 1 passed in 5.33s | Cleanup authority-root/harness seam green. |
| Composite body-primary / cleanup-cause probe | passed | Body `KeyError` remained primary; cleanup `RuntimeError` was `__cause__`; lease state cleared. |
| T2 retry-boundary probe | confirmed `accepted -> duplicate` after current authority changed to revoked | Negative residual captured; no runtime-green claim. |

### 5.1 Release-publication failures

The failures were:

1. `test_command_service_submit_preserves_public_signature_and_guard_metadata`
   expects the singular substring `guarded release continuation`; both base and
   candidate production emit `CommandService.submit requires its guarded
   continuations`.
2. `test_release_draft_cannot_supply_noop_validation_or_append_invalid_payload`
   expects only `envelope` and `finalize_payload`; base and candidate
   `EventDraft` also contain `admission`.

AST-source SHA-256 comparison showed the first failing test identical on base
and candidate (`31180de9...`), the second identical (`93060f06...`), and the
`EventDraft` class identical (`76f4207c...`). The guard message is present on
both subjects. These are pre-existing assertion drift, not candidate-caused
release failures. Because the full module completed, and the exact changed
schema-binding, envelope-mismatch, no-authorizer, and authority-denial cases
passed, release acceptance evidence is complete for this candidate despite the
two residual test defects.

### 5.2 Gate 5 failure

The exact node reaches `CompositeWriterLock._verify_writer_lock`, which requires
`.path` and `.identity`; its local `TrackingLock` exposes only `.inner`,
`__enter__`, and `__exit__`. The service retries the resulting conflict for its
five-minute budget before surfacing the error.

The `_verify_writer_lock` source is byte-identical between base and candidate
(AST-source SHA-256 `d9bf4438...`), as is the nested `TrackingLock` class
(`c1feae65...`). The candidate's cleanup change only reuses the returned grant.
The interface-complete equivalent forwarded `.path` and `.identity` and passed
the intended behavior. This is a pre-existing test-double defect and expensive
failure mode, not a candidate production defect; the repository node remains a
known non-green residual and is not hidden in an aggregate pass count.

## 6. Static validation

| Check | Result |
|---|---|
| Ruff over all 13 changed Python paths | passed |
| Ruff format check over all 13 changed Python paths | 13 already formatted |
| PyYAML structural compose of `.github/workflows/ci.yml` | passed |
| `git diff --check ba087e33..45bec009` | passed |
| Final pre-write status | clean |

The validation surface was expanded only where the candidate changes a shared
lifecycle resolver/factory or where the task explicitly required the two slow
surfaces. No package-wide or full-suite result is inferred.

## 7. Findings and residual risk

### Critical

None.

### Major

None.

### Minor

None.

### Non-finding residuals

1. T2 stored/reconstructed retries still return before current authority
   semantics. This was independently reproduced. It is accurately captured as
   an unimplemented design obligation in a document whose status is explicitly
   design-only; it is not a delivered behavior claim in this candidate.
2. The two release-publication assertions remain stale and the Gate 5
   `TrackingLock` remains interface-incomplete. Each is source-proven present at
   the exact base. The latter consumes approximately five minutes before
   failing because it enters the production retry path.
3. The accepted Slice L filesystem boundary remains: store I/O is not wholly
   handle-relative after the final fence, and hostile privileged retargeting of
   an unanchored ancestor is outside this correction. No candidate text
   overstates that boundary.

These residuals should remain visible to the next implementation/test-cleanup
subject. None changes the correctness of the 15-path CodeRabbit remediation at
the exact reviewed candidate.

## 8. Verdict and non-authorization statement

The integration preserves both exact source commits without byte drift, covers
the complete 25 + 12 finding inventory, closes every finding claimed by this
candidate, accurately labels the unimplemented T2 retry obligation, and has no
candidate-caused Critical, Major, or Minor defect.

**Final exact-subject verdict:** `accept_exact_subject` for
`45bec009698efad021f86e2edbe9bbb8cbcfb11b` only.

This review does **not** authorize updating PR #205, merging any branch,
marking Jira Done, closing or resolving review threads, or advancing Gate 6.
Those remain separate owner/integration decisions.
