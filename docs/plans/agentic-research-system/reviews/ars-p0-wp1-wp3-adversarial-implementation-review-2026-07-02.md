# ARS P0 WP1–WP3 — Independent Adversarial Implementation Review

**Date:** 2026-07-02
**Reviewer role:** Independent adversarial reviewer (implementation, not design snapshot)
**Subject:** PR #58 `codex/ars-p0-foundation` — "[codex] implement ARS P0 foundation through WP3"
**Method:** `adversarial-design-review` applied to committed code, schemas, tests, and the governing ARS P0 plan/design suite. Fresh context; every finding verified against files at the reviewed HEAD, not summaries or prior-agent conclusions. Read-only on all implementation and governing documents.

---

## Verdict

**`accept_with_required_changes`.**

WP1–WP3 are inside the reconciled P0 scope, entirely additive, scope-disciplined, and green on the documented gates (149/149 ARS tests pass, ruff clean, `git diff --check` clean, no live control/evidence state). I found **no P0 and no P1**: nothing at this HEAD corrupts authority/evidence, permits invalid acceptance, leaks restricted data, breaks deterministic recovery, or fails a governing P0 invariant on a reachable path.

The prior WP1 provenance review's findings (P1-1, P2-1…P2-6) and every CodeRabbit thread are dispositioned and verified closed in code. The required changes below are **P2 forward-looking guards** protecting invariants that are currently correct but rely on a P0 shape (single-event/single-stream batches, disabled live transport). They should land — or be recorded as explicit invariants/merge conditions — before the seams they protect are consumed by later work. None blocks merge of this foundation PR.

- **WP1 control-plane/replay core (identity, atomicity, recovery, replay determinism): ACCEPTED.**
- **WP2 context/routing/assurance: ACCEPTED.**
- **WP3 adapters/operations (fake-only, live disabled): ACCEPTED, with the timeout-classification seam recorded as a live-enable gate item.**

---

## Reviewed range and actual state

| Fact | Value |
|---|---|
| PR | #58, state OPEN, mergeStateStatus `UNSTABLE` (non-blocking checks) |
| Reviewed branch | `codex/ars-p0-foundation` |
| Reviewed HEAD | `0ed9fee536039848e1f6dbe66713cd0801380a6c` (`gh` `headRefOid` matches) |
| Base branch | `main` |
| Merge base | `717ead1ef1f59a7d4f14edcb3a0f1ebe87f4f31f` |
| Reviewed diff range | `717ead1..0ed9fee` (`main...pr58`): **121 files, +6548 / −12** |
| Review worktree | detached `0ed9fee` at a temp worktree; `main` checkout left untouched on `b702a4c` |
| Cleanliness | reviewed tree clean at every checkpoint; `uv run` created only an uncommitted `.venv`; no tracked file changed. The main checkout's unrelated `.superpowers` change and untracked research results were not staged, modified, or used as evidence. |

**Branch commit sequence (verified, in order):** `7b48f11` (Python-compat DECISION) → `6f0a909` scaffold → `92e9389` schema registry → `c2baed8` store → `ce22be4` command/receipt → `3cff54b` replay slice (prior review HEAD) → `45cb12e` close WP1 review findings → `3dda42e`…`6105bd3` (WP2/WP3 slices) → `b56f95d` close automated/CodeRabbit findings → `0ed9fee` stabilize conflict receipts + replay order (HEAD).

---

## PR scope reconstruction by work package

- **WP1 — control plane & replay.** New `research_system/` package: `canonical` (P0-subset canonical JSON + SHA-256), `ids` (owner-registered UUIDv7, field-scoped validation), `schema_registry` (Draft 2020-12), `store/{layout,lock,objects,ledger,receipts,identity}` (external single-writer store, atomic JSONL batches, content-addressed objects, tamper-evident store identity), `command/{models,reducers,service}` (idempotent command→event→receipt), `projection/replay` (pure verified replay + disposable projection rebuild), `cli`. Tracked `.research-system/config` + `.research-system/schemas/core`.
- **WP2 — context, routing, assurance.** `context/{models,sources,tokenizers,compiler}` (immutable candidates, mandatory-source closure, distinct reference/provider token gates), `assurance/{models,requirements}` (exact six W5 lanes, producer-independent scope confirmation, two-key non-compensable), `routing/{models,independence,engine,orchestrator}` (evidence-derived independence, eligibility-first deterministic ranking, unissued `PreparedDispatch`). Tracked context/assurance/routing schemas + policy packs.
- **WP3 — adapters & operations.** `policy/{models,compiler}` (canonical→provider projection, semantic parity), `adapters/{base,fake,subprocess_transport,claude,codex,parity,provider}` (normalized commands/receipts, redaction boundary, argv-only, `live_enabled: false`), `operations/{models,profiles,resources,leases,checkpoints,recovery,coordinator}` (proportional profiles, resource-conflict matrix, leases/checkpoints/recovery, typed issue coordinator). Tracked adapter/operations schemas + policies.
- **Docs.** Reconciliation edits to design/02, design/08, implementation/01, implementation/02, README, plus the Python-compat baseline note and the prior WP1 provenance review. No WP4 code (correctly deferred).

---

## Findings

### P0 — Blocking
**None.**

### P1 — Required before merge
**None.**

### P2 — Required changes (land or record as explicit invariant before the seam is consumed)

**P2-A — `observed_stream_version` is derived by two different formulas that coincide only for single-event, single-stream batches (the exact concern flagged for re-evaluation).**
- **Evidence.** Accept path: `research_system/command/service.py:94` `observed_version = view.stream_versions.get(command.target_stream_id, 0)` and `service.py:115` `observed_stream_version=observed_version + 1`. Reconstruction path: `service.py:168` `observed_stream_version=max(event['stream_version'] for event in events)`. `EventLedger.append` already returns the authoritative per-stream result (`store/ledger.py:150` `resulting_stream_versions`), which the service ignores.
- **Why it is not currently a defect.** `CommandService._build_event` (`service.py:177-208`) emits exactly one event whose `stream_id` is always `command.target_stream_id`, and `submit` calls `append([event])`. For every P0 command shape the batch is single-event on the target stream, so `max(stream_version) == observed_version + 1 == resulting_stream_versions[target]`. `test_s011_crash_after_event_rename_reconstructs_receipt` exercises reconstruction and passes byte-identically.
- **Failure scenario (forward).** `EventLedger.append` fully supports multi-event batches (`ledger.py:96-124`), and design §9.1 permits a batch to carry multiple events/referenced objects. If any later reducer emits a batch that touches a second stream whose resulting version exceeds the target stream's — or emits two events on the target — the originally written `accepted` receipt (`target+1`) and a later crash-reconstructed receipt (`max` across the batch) diverge. That breaks the S-011 "byte-identical receipt reconstructed from committed events" invariant and the design §8.3 guarantee that "accepted idempotency outcomes are reconstructible from events": the retry path at `service.py:170-173` would raise `IntegrityError('stored receipt does not match committed batch')` or serve a receipt reporting the wrong stream's version.
- **Violated invariant / trust boundary.** S-011 deterministic receipt reconstruction; design §8.3 "accepted … reconstructible from events."
- **Minimum correction.** Derive the scalar from the target stream on both paths: on accept use `ledger_receipt['resulting_stream_versions'][command.target_stream_id]`; on reconstruct use `max(e['stream_version'] for e in events if e['stream_id'] == events[0]['stream_id'])`. Cheaper alternative acceptable for P0: assert single-event/single-stream batches in `submit`/`append` and document the invariant in `01-control-plane-and-replay-plan.md` so extension cannot silently break reconstruction.
- **Affected WPs/decisions.** WP2/WP3 command emission; any future multi-event reducer; Gate 5 backup/restore (S-013/S-014).

**P2-B — `SubprocessTransport` timeouts are classified `blocked`, not `uncertain`, so the "uncertain completion" path is unreachable from the real transport.**
- **Evidence.** `research_system/adapters/subprocess_transport.py:25-32` returns `status='terminal', exit_code=124` on `TimeoutExpired`. `research_system/adapters/provider.py:72-84`: the `status_map` produces `uncertain` only for the literal statuses `timed_out`/`uncertain` (which only `FakeTransport` emits); a `terminal` result with `exit_code not in {0, None}` (`provider.py:83`) is mapped to `blocked`.
- **Why it is not currently a defect.** WP3 uses `FakeTransport` exclusively; `SubprocessTransport` is disabled (`.research-system/adapters/{claude,codex}.yaml` `live_enabled: false`). Both `blocked` and `uncertain` set `complete=False`, so neither permits invalid acceptance in P0.
- **Failure scenario (forward).** At live-enable, a genuine wall-clock timeout — an *uncertain* completion where the provider may already have written outputs before being killed — is recorded as a definite `blocked` non-completion. A resume/duplicate handler keying on `uncertain` vs `blocked` could re-issue partially completed work (duplicate side effects) or fail to trigger duplicate detection.
- **Violated invariant / trust boundary.** W7 receipt semantics: timeout ⇒ uncertain completion, not terminal-blocked.
- **Minimum correction.** Emit a distinct `timed_out`/`uncertain` status from `SubprocessTransport.invoke`, or have `normalize_receipt` treat `exit_code == 124`/timeout as `uncertain`. Record as an explicit checklist item on the WP3 "before provider enablement" review gate (`03-adapters-and-operations-plan.md:614-615`).
- **Affected WPs/decisions.** WP3 live-enable approval; recovery/duplicate handling.

**P2-C — Context candidate and manifest share one ID kind (`ctx`); the WP2 plan's `context_candidate`/`context_manifest` kinds do not exist in the owner catalogue.**
- **Evidence.** `research_system/context/compiler.py:37-38` mints both `context_candidate_id=new_id("context")` and `manifest_id=new_id("context")`. `.research-system/config/id-kind-registry.yaml:13` defines only `context: ctx`; there is no `context_manifest` or `context_candidate` kind. The WP2 plan snippet (`02-context-routing-and-assurance-plan.md:409-410`) calls `new_id('context_candidate')`/`new_id('context_manifest')` — **kinds that are undefined in the catalogue**, so the implementation coerced both to `context`.
- **Impact.** Two semantically distinct objects share a prefix and a kind; no validator distinguishes a manifest ID from a candidate ID. Not a P0 defect (nothing validates `manifest_id` against a distinct kind, and field-scoped validation is the accepted model), but a catalogue-coherence gap and a plan-vs-registry divergence ("undefined," not merely "differently named").
- **Minimum correction.** Either add `context_candidate`/`context_manifest` kinds to `id-kind-registry.yaml` and mint each accordingly, or amend the WP2 plan snippet to state both intentionally share the `ctx` kind and record why. Prefer the former if manifests are ever validated independently downstream.
- **Affected WPs/decisions.** WP2 context identity; W3 owner catalogue.

**P2-D — The "mandatory source cannot be excused by an omission reason" invariant has no enforcement point in the real compile pipeline.**
- **Evidence.** `build_candidate` hardcodes `omissions={}` (`context/compiler.py:51`); `compile_candidate` then calls `candidate.validate_manifest(..., candidate.omissions)` (`compiler.py:80-85`) with that empty dict. The `non-optional omission` guard in `ContextCandidate.validate_manifest` (`context/models.py:189-195`) is therefore never reached through compilation; F-021/F-022 blocking is enforced solely by the upstream `missing` check (`compiler.py:63-65`). The omission-excusal invariant is asserted only by a direct model unit test (`test_context_compiler.py::test_mandatory_source_cannot_be_excused_by_omission_reason`), not through the pipeline.
- **Impact.** Coverage gap: a future compiler that populated `omissions` would have no integration test catching an illegitimate omission. Low risk today (omissions are inert).
- **Minimum correction.** Add an integration test that drives omissions through `compile_candidate`, or wire real omissions into `build_candidate` so the guard sits on the live path.
- **Affected WPs/decisions.** WP2/WP4 fixture coverage.

**P2-E — Codacy "2 critical Security" findings are the two `subprocess.run` call sites; triage-with-rationale so the gate does not mask a future real finding.**
- **Evidence.** Independent scan of `research_system/` finds exactly two subprocess calls — `cli.py:31` (git worktree enumeration) and `adapters/subprocess_transport.py:16` — both `shell=False` with argv arrays and no user-interpolated shell string; and **no** `eval`/`exec`/`pickle`/`os.system`/`shell=True`/unsafe `yaml.load`/`md5`. The argv-only design is an explicit W7 hardening (`03-adapters-and-operations-plan.md:240-249`), and `subprocess_transport` is disabled in P0.
- **Impact.** The Codacy "not up to standards" gate is driven by Bandit-class subprocess flags that are false positives here. Left un-annotated, the gate stays red and can mask a genuinely new security finding later.
- **Minimum correction.** Suppress the two flags with a documented rationale (per-line `# nosec`/Codacy ignore with justification) or record the accepted-risk decision. Non-blocking.
- **Limitation.** Exact Codacy items are only on the Codacy web app; this session is non-interactive, so I inferred them from the independent source scan rather than reading Codacy's list. Reported as a limitation.

### P3 — Editorial
- `03-adapters-and-operations-plan.md:409-410`/`690-714` and `02-context-routing-and-assurance-plan.md` code snippets reference helpers that differ from the shipped implementation (`canonical_json_bytes` vs `canonical_bytes`; `route.kind`/`route.expires_at` vs dict access; `new_id('context_candidate')`). The shipped code is self-consistent and correct; the plan snippets are illustrative and now stale. Optional: annotate the snippets as indicative.

---

## Disposition of the earlier WP1 provenance review (2026-07-01, HEAD `3cff54b`)

| Prior finding | Status at `0ed9fee` | Evidence |
|---|---|---|
| **P1-1** `submit()` is not an authorization boundary but plan overstated coverage | **Resolved** | `service.py:79` docstring "Validate WP1 integrity controls; authorization remains downstream"; design §8.2 deferral of steps 2/3/4/8 preserved. |
| **P2-1** `canonical_bytes` not full RFC 8785 | **Resolved (documented subset + retained Gate-5 obligation)** | design/02 §7.1 amended (P0 canonical subset: ASCII keys, no floats, safe-int range; full RFC 8785 = Gate 5 obligation); `canonical.py:13-29` enforces it. |
| **P2-2** `task.schema.json` status enum diverged; unenforced | **Resolved** | `.research-system/schemas/core/task.schema.json` enum now equals W2 §11.1; description records object-level validation deferred to WP2. |
| **P2-3** idempotency uses `authority_grant_id`; no `command_id` global-uniqueness | **Resolved** | design §13.1 amended (grant-id as stricter proxy until WP2; `command_id` globally unique, reuse rejected pre-publication) and enforced at `service.py:157-159` (command-id collision → `ConflictError` before `append`). |
| **P2-4** CLI degrades to single-root on `git` failure | **Resolved (fail-closed)** | `cli.py:42-46` raises `ConfigurationError` on non-zero `git worktree list`; `cli.py:38-41` on timeout. |
| **P2-5** `recorded_at` not in `_PROTECTED_FIELDS` | **Resolved** | `store/ledger.py:26` now includes `recorded_at`. |
| **P2-6** lease prefix `els` vs `lse` | **Resolved (els is correct)** | W8 owner catalogue `design/08:82` = `els_...`; design/02 §7.1 corrected `lse`→`els`; registry `els` confirmed. |
| Residual: stale writer lock after hard crash | **Preserved as fail-closed by design** | `store/lock.py` never auto-breaks a pre-existing lock; the `__enter__` cleanup (`lock.py:27-29`) removes only the just-created lock, never a stale one — no regression. Operational recovery tooling remains a WP3 obligation. |

## Disposition of CodeRabbit + Codacy findings

All CodeRabbit inline threads (1 Critical + Majors) are **resolved and confirmed closed by the bot**:
- **Critical** duplicate ID prefix (`resource_request` = `rrq`, colliding with `route_request`) → fixed in `b56f95d` (`resource_request: rsq`). Independently verified; the `IdRegistry` duplicate-prefix guard (`ids.py:61-66`) would have hard-failed import otherwise. **Regression-checked: no remaining duplicate prefixes.**
- Majors (checkpoint hash `format`/pattern; subprocess timeout→terminal conversion; hardcoded R3 approver → injected `GrantBackedAuthorityPolicy`; git-worktree timeout; full-ledger snapshot caching; coordinator/leases/profiles/recovery/engine type hints & docstrings; lock cleanup on write failure; receipt temp-file recovery; factory schema-root anchoring) → all fixed in `b56f95d`/`0ed9fee`, each confirmed by a CodeRabbit "closing this out / confirmed" reply. Spot-verified in code (e.g. `cli.py:38-46`, `store/lock.py:27-29`, `store/receipts.py:60-66`, `assurance/requirements.py:16-23,76-85`).
- One residual, **regressed into scope by this review as forward-looking**, not by CodeRabbit: the subprocess timeout is *converted to a terminal result* (as CodeRabbit requested for stability) but the downstream *classification* is `blocked`, not `uncertain` — see **P2-B**.

**Codacy** "not up to standards" (2 critical / 3 medium / 2 minor, all Security) — dispositioned as **P2-E** (subprocess-argv false positives; triage-with-rationale).

---

## Invariant → enforcement point → hostile test matrix

| Invariant / trust boundary | Enforcement point | Hostile test | Verdict |
|---|---|---|---|
| Single global writer | `store/lock.py:17-21` `O_CREAT\|O_EXCL`; re-check inside lock `service.py:86-95` | `test_store.py` second-writer; competing claims | Holds |
| Idempotent retry ⇒ one batch, original receipt | `service.py:138-175` scope/command-id index + reconstruct | `test_command_service.py` identical-retry, changed-payload conflict | Holds (scalar caveat **P2-A**) |
| `command_id` global uniqueness pre-publication | `service.py:157-159`, `_stored_conflict_receipt:119-131` | command-id reuse across scope/actor | Holds |
| Conflict receipt byte-stable across retry/restart/mutation | persisted `service.py:96-105`; returned as-is `_stored_conflict_receipt` | `test_command_service.py` persisted-conflict (added in `0ed9fee`) | Holds |
| Atomic commit = event rename; objects inert without batch | `store/ledger.py:130-138` (`os.replace`) | 6 fault-injection windows `test_control_plane_fixtures.py` | Holds |
| Zero-or-one committed batch across crash | same + `test_replay.py` fault cases | event-rename/receipt-rename reconstruction | Holds |
| Replay fails closed on tamper | `projection/replay.py:108-165` major/schema/position/hash/project/stream/txn checks | tampered tail; bad major; position gap | Holds |
| Ledger order stable under wall-clock/dir moves | `store/ledger.py:162-170` sort by 20-digit position; bad filename → `ConflictError` | year/month cross, malformed filename | Holds |
| Control root external to every code root | `store/layout.py:require_external_control_root`; CLI enumerates all worktrees | reparse-parent, ancestor/descendant, git-fail | Holds |
| Store identity verified before writes | `config.py:ControlBinding.load:51-57` (externality + project + identity token + code-root) gates `command submit` | `test_store.py` S-012 mismatch | Holds |
| Canonical hash rejects floats/non-ASCII keys/unsafe ints | `canonical.py:13-29` | `test_canonical_ids.py` | Holds; RFC 8785 = Gate 5 |
| Exact six W5 lanes; non-compensable two-key | `assurance/requirements.py:44-46,34-36` | empty/partial/dup/extra lanes; key-A-only | Holds |
| Producer cannot self-confirm R2 scope / self-accept R3 | `requirements.py:68-85` (scope-reviewer≠producer ∧ I≥I1 at R2+; I2 ∧ granted R3 authority) | `test_assurance_requirements.py`; `test_independence.py` | Holds; **stricter than spec §6.2 (AND vs OR)** — conservative |
| Eligibility-first routing invariant to candidate order/telemetry | `routing/engine.py:select_route` sorted eval; unknown reason → raise | `test_routing_engine.py` permutation; unbound telemetry | Holds |
| Token units never cross-compared | `compiler.py:75,95` (`ars_reference_tokens` vs `provider_tokens`); UTF-8 diagnostic-only | `test_token_gates.py` | Holds |
| Resource-conflict matrix symmetric, fail-closed on mixed modes | `operations/profiles.py:has_resource_conflict` | parametrized symmetric matrix | Holds |
| Raw transcript/stdout never enters receipts | `adapters/provider.py:normalize_receipt` extracts registered fields + hash only | `test_provider_receipts.py` no-transcript | Holds |
| Timeout ⇒ uncertain (live) | `adapters/provider.py:72-84` | Fake `timed_out`→uncertain | **Gap on real transport — P2-B** |

---

## Decision and forward-obligation audit

- **§7.3 owner decisions / reconciled P0 scope:** treated as approved. No concrete contradictory evidence found; no owner-approved decision challenged.
- **Deferred W2 §8.2 steps 2/3/4/8 (authority/assurance/human gates):** visibly deferred (service docstring + design §8.2) and **cannot be mistaken for implemented authorization** — `submit` is explicitly integrity-only. Confirmed.
- **Retention boundary (R1/R2/R3 durations, `EvidenceDeletionVerified`):** a WP4 obligation; canonical state holds only R0 identity/hash/policy; receipts carry no restricted payload (verified in `provider.py`). No P0 code persists R2/R3 content. Forward obligation intact.
- **Deferred imports / incompatible Python envs (item 13):** ARS imports only stdlib + `jsonschema` + `PyYAML`; providers are invoked out-of-process via argv (`subprocess_transport`), so no provider SDK is imported and **the future-provider seam is preserved** and not bound to one interpreter. The `giotto-tda`/`topologytoolkit` 3.13 incompatibility is pre-existing, quarantined, and correctly not waived for ARS (`python-compatibility-baseline-2026-07-01.md`; DECISION `7b48f11`). No implementation makes future imports impossible. Confirmed.
- **Live provider use / migration / pilot / claims:** none present. `live_enabled: false`; no `.apm`/vault/results/credentials touched.
- **Exact 37-case closure & priority vs gate_stage:** WP1–WP3 fixture-bound cases are represented by named tests; the authoritative W6 fixture-catalogue binding (06a/06b) and S-014/S-015/S-016 remain WP4/Gate-5 obligations (correctly out of this PR).

## Test & fixture coverage gaps

1. **P2-A** reconstruction-vs-accept divergence has no multi-event/multi-stream regression test (unreachable today, so untested).
2. **P2-D** omission-excusal invariant untested through the compile pipeline.
3. **P2-B** no test asserts a real-transport timeout classification (only Fake `timed_out`).
4. Fixture-catalogue fidelity: F-001…F-005 / S-006 are bound to plausible-control tests, not cross-checked against the authoritative 06a/06b definitions — a WP4 checkpoint obligation (carried over from the prior review).
5. Hard-crash-while-locked (kill/power-loss) is simulated only as an unwinding Python exception (lock releases); the true strand-the-lock path is an operational residual, not covered by an automated test.

## Python / dependency-boundary assessment

Clean. New runtime deps: `jsonschema>=4.20` (already pinned) and `PyYAML` (already a repo dep; `ids.py`/`config.py` import `yaml`). `[project.scripts] ars` and the `research_system*` package-find entry are the only `pyproject` changes. No pin loosened, no new topology/ML dependency, no in-process provider SDK. Out-of-process provider design keeps the door open for providers needing a different interpreter. **No accidental single-environment binding.**

## Scope discipline (item 15)

Confirmed clean. `git diff --name-only main...pr58` is entirely within `research_system/`, `tests/research_system/`, tracked `.research-system/{config,schemas,policies,adapters,packs}`, `docs/plans/agentic-research-system/`, `pyproject.toml`, `.gitignore` (which adds only disposable `projections/`, `indexes/`, `runtime/` ignores). No live research/control state, migration, provider credential, vault state, `.apm/`, or unrelated change. No committed control root or evidence root.

## Residual risks and merge conditions

**Merge conditions (P2, land or record before the protected seam is consumed):**
1. **P2-A** — add the target-stream derivation (or a single-event/single-stream assertion + documented invariant) so receipt reconstruction cannot silently break when reducers are extended. *Highest-priority forward guard (protects S-011).*
2. **P2-B** — record the timeout→`uncertain` fix as a WP3 live-enable gate item.
3. **P2-C** — reconcile the context ID catalogue (add kinds or document shared `ctx`).
4. **P2-D** — cover the omission-excusal path through compilation.
5. **P2-E** — annotate/triage the Codacy subprocess flags with rationale.

**Residual risks (accepted):** stale writer-lock after hard crash (fail-closed by design; needs an operator procedure/tooling in WP3); fixture-fidelity binding deferred to WP4; GitNexus impact analysis unavailable for the new package (see below).

## Validation evidence (exact commands and results)

Run in the review worktree at `0ed9fee`, Python 3.13.5:

| Command | Result |
|---|---|
| `git rev-parse HEAD` | `0ed9fee536039848e1f6dbe66713cd0801380a6c` (matches `gh` headRefOid) |
| `git merge-base main pr58` | `717ead1ef1f59a7d4f14edcb3a0f1ebe87f4f31f` |
| `git diff --check main...HEAD` | exit 0 (clean) |
| `uv run ruff check research_system tests/research_system` | `All checks passed!` (exit 0) |
| `uv run pytest tests/research_system -q --no-cov` | `149 passed in 6.36s` (exit 0) |
| `git diff --name-only main...pr58` scope filter | no path outside the expected roots |
| independent security scan (`shell=True`/`eval`/`exec`/`pickle`/`os.system`/unsafe-yaml) | none; only two `shell=False` argv `subprocess.run` sites |
| GitNexus `impact`/`detect_changes` | **not run against the new package** — the GitNexus index is built on `main`, where `research_system/` does not exist, so symbol-level impact is `not found` (same limitation the prior WP1 review recorded). New-package assessment done by direct source + call-site inspection. |

The repository-wide suite was **not** run (13 pre-existing `gtda`/`topologytoolkit` collection errors, unrelated to ARS, are documented and correctly not waived for ARS).

## Change log / files edited

The **only** file I created is this review deliverable, `docs/plans/agentic-research-system/reviews/ars-p0-wp1-wp3-adversarial-implementation-review-2026-07-02.md`, written to the `main` working tree (untracked, uncommitted). **I changed no implementation, schema, test, or governing-document file.** No commit or push was made. The review worktree was clean throughout except for the `uv`-created `.venv`.
