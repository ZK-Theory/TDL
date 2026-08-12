# WP6.6 PR #247 adversarial-review remediation record

Status: candidate construction record; not owner acceptance, CodeRabbit completion,
merge authorization, or integration evidence.

Controlling review: `wp6-6-pr247-adversarial-review-2026-08-12.md`, 928 lines,
SHA-256 `3f6babf7d11e8da5ea7f495d43bea3e538bfdbc7f99386f9de1312c73def6dd6`.
Its exact reviewed subject was `f27555aa0fa82a90a0910ec6a67904939d2e6298`
(tree `6aa8e0b080ee5f05ca0720178f3be1eec8af52ab`). This record preserves the
review's R1-R5 and Appendix 1-7 matrix so later construction does not silently
shrink the requested correction surface.

## Finding dispositions

| Review item | Candidate disposition | Owning proof |
|---|---|---|
| R1 | One row-registry-driven submit fence applies mint-or-advance identity ownership to every executable row. W11 authority observation is also bound to the exact registered content stream. | Public OR-103, stale OR-101, OR-111 and OR-117 cross-namespace attacks reject with no mutation; exhaustive executable-row/namespace matrix; same-kind continuation remains valid. |
| R2 | `SpikeStarted` replay re-derives the exact running Attempt and active Lease from the shared operational partition and binds both hashes, mutual references, holder, resource and expiry at the event instant. | Appendix C.3 coordinated fabricated Attempt/Lease IDs and hashes at the OR-017 EOF rejects after full reindex and rehash. |
| R3 | Dossier semantic identities use the P0 canonical encoder used by replay. Non-P0 command and dossier values become governed integrity/admission errors. The already accepted Windows physical-root digest retains its separate legacy byte contract. | P0 parity and float/non-ASCII/unsafe-integer negatives; public zero-ledger/zero-receipt negative; real-dossier regression. |
| R4 | Owner defaults resolve to `Path.home()/TDL` and its real vault. The committed `tools/certify_wp6_6_real_dossier.ps1` invocation always sets `TDL_REQUIRE_REAL_DOSSIER=1`, making absent or inaccessible roots a certification failure, while ordinary integration deselection remains available. Hosted CI does not impersonate those physical roots: Stephen is the named release operator and runs the committed command at every exact acceptance candidate. | Owner-default and explicit-root real-dossier runs; required-mode missing-root collection failure; committed certification command and exact-head owner-machine receipt. |
| R5 / OR-002 | `SupersedeDiscoveryRecord` is an active, authorized, producer-bound public route with immutable predecessor/replacement lineage, terminal predecessor state, replay joins and retry-safe receipt recovery. | Public positive/restart/retry plus self, stale, reused replacement, lineage/hash/stream tamper and post-supersession lifecycle negatives. |
| R5 / OR-030 | Explicitly deferred and inactive. Accepted §7.4 requires a current annotation epoch, but the protected closed v1 annotation schema forbids `annotation_epoch_id` and no accepted initial-epoch authority/event exists. Encoding it in a path or unrelated field would invent authority. | Public `IngestDiscoveryAnnotation` rejects before mutation because no command binding is active; a successor contract and owner-accepted initial epoch are required before activation. |
| R5 coverage | A production-used route registry is checked against all 81 accepted catalogue rows: 59 executable, OR-030 explicitly deferred under the later annotation-epoch/cutover work, and 21 explicitly excluded migration/cutover/transition rows. | Exact executable/deferred/excluded partition gate plus active schema/authority bindings. |

## Mandatory appendix dispositions

1. Number-valued Assay axes are rejected at OR-101 with `IntegrityError` until a
   separately accepted P0 scaled-integer contract exists. No floating-point
   scorecard lane is claimed.
2. Production activation and proof cover only the accepted required Boolean
   identity gate. Integer axes, numeric bounds, `registered_measure`, and a
   non-trivial `allowed_set` domain are not activated and are not claimed by
   this candidate. Their dormant validation code is not acceptance evidence.
3. Accepted W11 authority shadows omit the preparation-only transaction marker;
   replay binds the real outer ledger transaction identity.
4. Dispatch derives from the accepted row and exact producer command through
   the production route registry, never from caller-controlled payload shape.
5. One shared-ledger partition function assigns every event to exactly one of
   Discovery, artefact, or operational replay. A real Spike ledger proves the
   partitions disjoint and exhaustive and feeds the exact owning reducers.
6. Durable producer traceability is `OR-140` for genesis, `OR-001` for direct
   Candidate registration, and `OR-029` for Scout-created Candidates; replay
   rejects missing or substituted owner rows.
7. `pytest.mark.integration` is registered in the reviewed baseline when pytest
   uses the repository `pyproject.toml`. An out-of-tree review harness must run
   from the repository root or pass `--rootdir <repository-root> -c
   <repository-root>/pyproject.toml`; repository configuration cannot register
   a marker for an unrelated foreign rootdir. Strict-marker collection under
   the bound project configuration is the disposition, so no ineffective
   duplicate `conftest.py` registration was added.

## Protected-contract contradiction and OR-030 deferral

Accepted W11 §7.4 requires every annotation payload to repeat an immutable
`annotation_epoch_id` resolved from one active epoch whose directory physical
identity, path-registration revision/hash, writer-grant-set hash, activation
position and `active | fenced` state are durable authority. The protected
`ars://portfolio/discovery-annotation@1.0.0` schema has no such property and
uses `additionalProperties: false`; no accepted initial-epoch authority or
activation event exists. The current WP6.6 path subject is a root bag rather
than a schema-valid `human_annotation_inbox` PathRegistrationContent.

This is not safely repairable by implementation alone without changing or
superseding accepted contract bytes. OR-030 is therefore deliberately inactive:
there is no runtime schema binding, scoped-grant activation, producer binding,
or public positive path. Activation belongs to the later annotation-epoch and
cutover work after Stephen accepts a versioned successor schema, one exact
annotation-inbox PathRegistrationContent, and an initial epoch authority/event.
The protected v1 bytes remain unchanged and this candidate claims no OR-030
execution capability.

## PR #248 reviewed-source dispositions

The exact source subsequently reviewed in full for PR #248 was commit
`5c48cc73c5f4f7706049087b4447684330d47c88`, tree
`0a565bc029d0ef5ce7c2cfe1c016a306f7fb55a5`, with subject
`[RESULT] WP6.6: close replay and authority review findings`, against live-main
base `2e6bf9c92e59208c40e55f664fc48d75e481ae04`. These are historical reviewed
bytes, not the identity of any later remediation head.

- `CandidateSpikeVerdictLinked` and its PARTIAL twin now join the exact
  Candidate, Spike, prior state, Candidate stream, transaction, and preceding
  Spike result. Fully reindexed and rehashed identity, stream, transaction, and
  missing-result substitutions reject during replay.
- Every dossier object, dependency edge, and Scope materialization now requires
  the matching `ResearchDossierAdmitted` event earlier in the same atomic
  transaction. A fully rehashed orphan object or Scope event is rejected rather
  than becoming an unowned durable projection.
- OR-116 path-registration content now recomputes its canonical content digest
  at registration and replay. The candidate fixture's placeholder digest was
  replaced by the canonical value
  `ba67b4175a6d82619abdc5083ea8b566604d6fc6c46702465e8689884d902a59`;
  protected W11 bytes were not changed.
- The accepted-W11 identity test uses shared repository-relative `Path` values
  for both tree comparisons and compares working-tree bytes without line-ending
  normalization.

The independent external reviewer reported the following exact-source evidence
for that commit:

- `uv run --env-file .env pytest tests/research_system/contracts/test_w11_expected_catalogue.py tests/research_system/integration/test_wp6_6_discovery_authority.py tests/research_system/integration/test_wp6_6_discovery_crash_recovery.py tests/research_system/integration/test_wp6_6_discovery_runtime.py tests/research_system/integration/test_wp6_6_dossier_admission.py tests/research_system/unit/test_command_lifecycle.py tests/research_system/unit/test_discovery_dossier.py tests/research_system/unit/test_schema_registry.py tests/research_system/unit/test_wp6_6_discovery_activation.py -q -p no:randomly --no-cov -rs`
  returned `427 passed, 1 skipped` in `776.50s`; the only skip was the absent
  optional `rfc3339-validator`, and no real-dossier test skipped.
- `tools/certify_wp6_6_real_dossier.ps1`, with `TDL_PYTHON` explicitly set to a
  pytest-capable interpreter, returned `35 passed` in `53.31s`, exit `0`.
- `tests/research_system/integration/test_wp6_6_discovery_runtime.py::test_replay_rejects_fully_rehashed_candidate_spike_links_without_exact_transaction_join`
  and both cases of
  `tests/research_system/integration/test_wp6_6_dossier_admission.py::test_replay_rejects_fully_rehashed_orphan_dossier_materialization`
  were part of the reported 427-test aggregate.
- The path-authority digest nodes
  `test_bundled_path_registration_content_digest_matches_canonical_content`,
  `test_path_registration_rejects_false_canonical_content_digest_at_registration`,
  and
  `test_path_registration_replay_rejects_rehashed_false_canonical_content_digest`
  were part of the same aggregate.
- Required-mode negative command
  `TDL_REQUIRE_REAL_DOSSIER=1 TDL_REPOSITORY_ROOT=C:/nonexistent-review-root pytest tests/research_system/integration/test_wp6_6_dossier_admission.py`
  stopped at collection with
  `pytest.UsageError: real TDA dossier certification requires accessible roots: TDL_REPOSITORY_ROOT, TDA_VAULT_ROOT`,
  proving the strict gate fired rather than silently skipping.

Exact committed-head validation and external-thread dispositions are recorded
on PR #248 and KAN-59. They do not constitute CodeRabbit completion, owner
acceptance, merge authorization, or integration evidence.

## Closure boundary

The corrected end product will be recommitted as a fresh pull request so the
external service can perform a full review. Stephen alone triggers and monitors
CodeRabbit. This campaign must stop at the exact PR head until Stephen reports
CodeRabbit complete at that head and separately authorizes a fresh closer to
integrate it.
