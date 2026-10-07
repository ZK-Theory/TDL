# 06s Phase 5 prep: design pass (KAN-110)

**Capability status:** INCOMPLETE. The historical real SPEC run is PROVEN; the complete public Gate 6
implementation is not integrated on main.

**Date:** 2026-10-07. **Status:** for Stephen's acceptance. Nothing here is constructed, and no live
operation has run.
**Subject:** `origin/main` at `b0cda61548c1528997d42c6a8e35e2a9cae3c945` (contains 4c's `e5179b57` and #343).
**Worktree:** `C:/Users/steph/TDL-06s-phase5-prep`, branch `docs/06s-phase5-prep-design`. `.env` copied,
`uv sync --locked --extra dev` done, and pytest proven there (`test_schema_registry.py`: 59 passed).
**Scratch roots:** `C:/Users/steph/TDL-p5-rehearsal` (a non-linked clone, a scratch origin authority and a
scratch control store). The live store, its origin authority, providers and credentials were not touched.
**Rehearsal driver:** disposable and uncommitted, in this session's scratchpad (`p5_rehearsal.py`). Each probe's
JSON record is in `C:/Users/steph/TDL-p5-rehearsal/results/`.

## 0. The short version

1. **B-1 has a fix that needs only a small code change.** A store's origin-witness digest cannot be computed
   before `store init`. Init draws a random store nonce, and the witness pins the physical identity of the stage
   directory that init creates. But init already resumes from a reserved witness and its stage. Measured:
   reserve, then pin the reserved digest, then the genuine `ars store init` succeeds through the committed
   foundation (§1, probe P2b). The only missing piece is a sanctioned way to make the reservation.
2. **There is a second blocking gap, B-2, which the 4c review did not reach.** A freshly initialized store has
   no public path to its first store binding. Measured: after the re-pin and a genuine init, `ars discovery spec
   status` refuses with "current store binding is unavailable". `ars store repair-binding` refuses because a fresh
   store has no restore transaction. `advance-binding` needs a predecessor binding. Every scratch SPEC store in
   the tests is bound by hand-written fixtures. So Phase 5 step 1 ("bind through the merged binding-service
   path") cannot be done on any fresh store at this SHA, re-pin or not.
3. **Fixing B-2 is a STORE change, so it needs Stephen's explicit D5 exception.** I recommend one narrow owner
   action for the first binding of a never-bound, freshly initialized store (§2.2).
4. **Two more seams are replaced by test adapters and have never run through the public CLI:** grant activation
   and Task/Attempt seeding (§2.11). I recommend the first construction step be a public-CLI rehearsal census
   that finds every such gap at once, before the fix PRs are cut.
5. The other items (M-1, M-2, the Assay bar, SPEC-01's rule, `adopt_default`, cost and the runbook) have
   recommendations below. Two of them also touch inherited code outside the route and need a decision.

### Decisions for Stephen

| # | Decision | Recommendation | Kind |
|---|---|---|---|
| P5-1 | How the fresh store's witness digest is pinned before `store init` (B-1) | Add `ars store reserve` (or `store init --reserve-only`). It stops init after the witness is persisted and prints the exact foundation fields. Then commit the re-pin, then run the unchanged `store init`. | Code: STORE (`cli.py`, `authority.py`), D5 exception |
| P5-2 | Replace the live store in the foundation, or keep both | Replace. The foundation format holds one store, and "beside" would be a new selection structure. | Committed configuration |
| P5-3 | How a freshly initialized store gets its first binding (B-2, new) | One new owner action, for the first binding of a never-bound initialized store (§2.2, option B1) | Code: STORE (`binding_service.py`, `current_binding.py`, binding schemas), D5 exception |
| P5-4 | Phase 5 step 6 under a 1.0.0 root binding | Amend step 6: replay at the bound SHA from the frozen checkout after the docs PR merges. Do not build an advance path from the new root. | Plan amendment |
| P5-5 | The durable checkout (M-1) | A dedicated non-linked clone, `C:/Users/steph/TDL-ARS-G6-Checkout` | Procedure and configuration |
| P5-6 | Roots and project identity | New control root `C:/Users/steph/TDL-ARS-G6-Control` and new origin authority `C:/Users/steph/TDL-ARS-G6-Origin-Authority`. Keep project `prj_01978abc-1000-7000-8000-000000001000`. | Configuration |
| P5-7 | Which Task the SOURCE registration cites (M-2) | A separate SOURCE Task with a running Attempt. The route verifies, against the ledger, the production references the intent names. No schema change. | Code: route |
| P5-8 | Where SPEC-01's numeric rule is evaluated | In W11 admission (`rules.py`), keyed by the rubric's declared algorithm, so the scorecard records SPEC-01's real recommendation. Fallback: in the route, with a recorded residual. | Code: W11 runtime (D5 exception) or route |
| P5-9 | Who signs the Assay authority content | A dedicated non-owner author actor on the fresh store, so author, reviewer and acceptor are three identities | Committed content and procedure |
| P5-10 | `adopt_default` after a SPEC-02 PROMOTE | Remove it from the SPEC route's permitted dispositions | Code: route (very small) |
| P5-11 | Construction order | The census first, then the PRs in §3 | Process |
| P5-12 | Delta assurance | Re-run the full 4c selection plus the new nodes, with a recorded machine check before the window | Process |

## 1. What I measured

All probes ran the genuine CLI as `python -c "...; from research_system import cli; cli.main(...)"` from the
non-linked scratch clone `C:/Users/steph/TDL-p5-rehearsal/clone` at `b0cda615`. So `canonical_foundation_path()`
selected the clone's own foundation, and nothing patched it. The driver asserts that `research_system` was
imported from the clone.

| Probe | Setup | Result |
|---|---|---|
| Setup | `git clone` of the repository, checked out at `b0cda615` | `git worktree list` in the clone lists only the clone. `store init` would therefore register exactly one code root (`cli.py:173-195`). |
| P1 | Committed foundation, `store init --control-root .../fresh-control` | Refused before any write: `canonical foundation origin witness path is not canonical` (`config.py:565`). This reproduces B-1(a). |
| P2a | Foundation pinned to the fresh root's canonical witness slot with a placeholder digest | Refused: `origin witness raw bytes differ from foundation pin` (`identity.py:374-375`). No witness was written, but a stage directory `.fresh-control.authority-stage-…` was left behind. You cannot know the digest in advance: the manifest carries a random nonce (`authority.py:1162`), and the witness pins the stage's device and inode (`authority.py:1743-1750`). |
| P2b | Reservation made (stage, manifest and witness persisted, no store published) by stopping init at its existing `after-identity` failpoint (`authority.py:1778`). Then the foundation re-pinned in full to the reserved store: the slot, the reserved digest, the reserved identity, `code_roots: [clone]` and `schema_root: clone/.research-system/schemas`. | The genuine `store init` exited 0 and consumed the reservation (`authority.py:1658-1674`, `1373-1402`, `1182-1198`). The store identity equals the pinned identity, the witness digest equals the pin, and no stage was left. |
| P3 | After P2b | `ApprovedProjectBinding.load` of the re-pinned foundation succeeds. The store has no restore transaction and no binding pointer. Its manifest has no `origin_witness_path` or `origin_witness_sha256`. The genuine `ars discovery spec status` refuses: `current store binding is unavailable`. |
| P4 | The clone committed clean (the clone has no `core.hooksPath`, so no hook was skipped). A canonical `RepairStoreBinding` intent naming the clone as candidate. | The genuine `ars store repair-binding` refuses at `binding_service.py:862`: it cannot read the cleared restore transaction, and a fresh store has none. The candidate checks, which run first, passed. |

The probes stopped at P4, because nothing after it is reachable without a binding.

**Why 4c did not see B-2.** Every SPEC scratch store is made by `_bound_fixture`
(`tests/research_system/integration/test_current_binding.py:250-359`) on top of `_restored_fixture`
(`test_restore_recovery_origin_witness.py:30-90`). That fixture:
- runs init through the Python API with no pin;
- "restores" with `shutil.copytree` and a sealed preflight whose hashes are placeholders (`"a" * 64`, …);
- writes a 1.0.0 repair predecessor object by hand;
- writes a v1.1 `StoreBindingAdvanced` event directly into the ledger (`_write_historical_binding_advance_event`,
  `:185-247`), which no current service can produce.

Phase 0's genuine binding probe ran `repair-binding` on a synthetic stale restored store
(`_service_fixture(stale=True)`). It never started from an initialized store.

## 2. Scope items

### 2.1 The fresh store (B-1)

**Current behaviour (P1, P2a, P2b).** `store init` reads only the foundation's origin pins
(`config.py:539-566`). It requires the foundation's witness path to be the canonical slot for
(project, new root), which is computable in advance. It also requires the persisted witness bytes to hash to
the pinned digest, which is not computable in advance. Init already supports a reservation: if the slot holds a
witness that matches the request, it verifies it against the pin, finds the stage with that physical identity,
and builds the store from the reserved manifest.

**Options.**
- **(a) Pin after init.** Run init with no pin check (Python API or an uncommitted foundation edit), then commit
  the full foundation. That is probably how the live store was made: its pins were null until `8cb5e71a`,
  after #208 already required them. But it inverts P-058's order, so init writes an unpinned witness. Not
  recommended.
- **(b) Reserve, pin, init (recommended).** One small command, `ars store reserve` (or a `--reserve-only` flag on
  `store init`):
  - it runs init's existing code up to `after-identity` and stops: inputs validated, stage created, manifest
    written, witness persisted with no pin and no store published;
  - it takes the origin-authority root explicitly, because the committed foundation still names the live slot;
  - it prints the exact foundation fields to commit, with the pre-init tail `(0, "0"*64)`.

  Then the re-pin commit merges, and the unchanged `store init` consumes the reservation under the pin. This is
  P2b with the failpoint replaced by a supported stop.
- **(c) A helper that computes the pin without writing anything.** Not possible without changing init to accept
  a supplied nonce and stage. That is more code than (b), not less.

**Helper needed?** Yes. It writes the reservation; it cannot be write-free. "Create the control root" in P-058's
procedure is, physically, the reservation's stage directory: init publishes the store by renaming that stage
onto the control-root path, and the witness pins its identity.

**Replace or beside (P5-2).** The foundation format (`ApprovedProjectBinding`,
`current_binding._load_foundation`, `load_foundation_origin_pins`) holds exactly one store. "Beside" would need
a second foundation and a selector for the CLI. That is a new structure (D5) for no Phase 5 benefit. Replace:
- the live store stays historical evidence. Its evidence is the tracked, hash-verified P-050 manifest, which
  needs no CLI access;
- after the re-pin, a CLI on a newer SHA cannot address the live store. Any later read uses a pre-re-pin
  checkout, as P-057's read-only extraction did.

Effects of the re-pin on tests and contracts:
- `tests/research_system/contracts/test_foundation_origin_witness_contract.py` hard-codes the live roots,
  witness path and digest. It is marked `live_store`. The re-pin PR rewrites its expected values to the fresh
  store's, and it then reads the fresh store (read-only) on the operator machine.
- `test_wp64_real_a8_evidence.py::test_mechanics_only_null_foundation_fails_before_output` passes the committed
  foundation and expects it to fail to load. Before init the fresh foundation names a root that does not exist,
  so the test passes. After init its premise needs checking on the operator machine; this is the same position
  the test is in with the live store today.
- The SCALE packages (`tda-scale-v1.0.1`–`v1.0.3`) record the live foundation as "current"
  (`current_foundation_semantic_sha256: 06c20868…`). They are frozen historical contracts. No code or gate
  compares them with the committed foundation (`git grep`), so they stay unchanged. The re-pin's decision
  entry says so.
- Since #325 every other test builds its own foundation.

**Roots and project identity (P5-6).**
- **Control root:** new, `C:/Users/steph/TDL-ARS-G6-Control`. It must not exist before init.
- **Origin authority:** new, `C:/Users/steph/TDL-ARS-G6-Origin-Authority`. Reusing the live store's origin
  authority would be valid, because slots are per (project, root). A new root keeps the live evidence
  directory physically untouched.
- **Project ID:** keep `prj_01978abc-1000-7000-8000-000000001000`. It is the same project, and the store
  identity tells the stores apart. Committed route inputs pin this ID; the Assay content is being replaced in
  any case.
- **Backups:** step 5's directories are unchanged (`TDL-ARS-WP64-Backups`, `TDL-ARS-WP64-Restore-Verification`).
  Using new subfolders there is fine.

**Kind.** Code (STORE: the reserve stop; P5-1 needs the D5 exception), then committed configuration (the
re-pin), then procedure (the live reserve and init).

### 2.2 The first binding (B-2, new)

**Current behaviour.**
- `load_current_binding` requires a current binding pointer and a chain whose root is a 1.0.0 repair binding
  (`current_binding.py:487-521`).
- It also requires a restore transaction that matches the binding (`:923-929`), and manifest fields
  `origin_witness_path` and `origin_witness_sha256` (`:930-941`). Only `restore-bind` writes those fields.
- `RepairStoreBinding` requires a cleared restore transaction (`binding_service.py:859-875`, measured P4). It
  also requires a demonstrably stale store, meaning some legacy code or schema root is missing (`:908-914`).
- `AdvanceStoreBinding` requires a current 1.1.0 or 1.2.0 predecessor (`:1296-1300`, `:1328-1329`). The
  reviewed-divergence action requires the exact clean legacy v1.1 predecessor (`:1375-1381`), which only the
  retired pre-service code produced.
- A 1.0.0 root admits only its exact Git subject (`current_binding.py:826-827`). So a store whose chain is a
  lone repair root can never take a documentation-only successor.

**Options.**
- **(A) No code: a contrived restore.**
  - Initialize at root S from a throwaway code root T.
  - Activate a CreateBackup grant, back up S, and `restore-bind` into C. `restore-bind` requires the foundation
    to name S (`cli.py:530-532`), so this needs a first re-pin to S and a second to C.
  - Delete T, so that the store is "demonstrably stale".
  - `repair-binding` onto the durable checkout.

  Not recommended:
  - it creates two stores, against "one store, created once";
  - it needs two governed re-pins;
  - its durable `stale_evidence` would record a staleness made on purpose;
  - it still ends at a 1.0.0 root.
- **(B1) Recommended: one owner action for the first binding of an initialized store.** Its admission:
  - no binding pointer and no restore transaction exist;
  - the store manifest equals the origin witness's `initial_manifest` byte for byte;
  - all the manifest's code roots exist, and the candidate is the manifest's single code root (the durable
    checkout);
  - the candidate's checks are unchanged (#341 disposable refusal, clean, schema-catalogue hash, route and
    source bytes).

  It publishes a 1.0.0-shaped root binding and its event through the existing repair publication. `current_binding`
  accepts this initial root in place of the restore join: the witness's initial manifest stands in for the
  restore transaction, and the manifest's witness locator is taken from the foundation.

  Changes:
  - `binding_service.py`: one plan branch;
  - `current_binding.py`: two checks;
  - a binding intent and object schema version for the new owner action (D3);
  - tests, with mutation controls for each admission predicate.

  This is the smallest change that keeps P-058's procedure ("then bind it") and creates one store.
- **(B2) Drop the staleness requirement after a real restore.** Less code in the loader, but it keeps (A)'s two
  stores, two re-pins and the backup/restore before step 1. Not recommended.

**Step 6 consequence (P5-4).** Under B1 the root is 1.0.0, so the route admits only the exact bound SHA. M-1
freezes the checkout from step 1 to step 6 anyway. Step 6 ("docs-only final PR … verify documentation-only
governed-code descent and replay again on merged main") becomes: merge the docs PR on GitHub, do not pull it
into the durable checkout, and replay from the frozen checkout at the bound SHA. The alternative is to also
build an advance path from an initial root to 1.2.0. That is more STORE code for a check whose subject is a
documentation PR. Recommend amending step 6.

**Kind.** Code, STORE. D5 requires Stephen's explicit exception before implementation.

### 2.3 The durable checkout (M-1)

**Current behaviour.**
- `store init` registers every worktree of its code root as a code root (`_registered_code_roots`,
  `cli.py:173-195`). From the primary checkout that is every agent worktree alive at that moment: 14 today, 28
  for the live store. That list becomes permanent provenance in the immutable manifest and the foundation.
- #341 refuses linked and agent-directory checkouts as schema roots and binding candidates.
- The binding requires `code_roots == [the executing repository]`, a clean status and the exact head
  (`current_binding.py:818-829`). The integration check reads the candidate's local `refs/heads/main`
  (`binding_service.py:69`).

**Measured.** A non-linked clone registers exactly itself (setup probe), and P2b ran from one.

**Options.** (i) The primary checkout, frozen. Rejected:
- it is shared;
- it was dirty during the 4c review;
- every agent worktree would become a store code root;
- freezing it would block other work for the whole of Phase 5.

(ii) **A dedicated clone (recommended):** `C:/Users/steph/TDL-ARS-G6-Checkout`.
- It is cloned from GitHub at the post-prep main SHA, with its local `main` at that SHA.
- It has its own `.venv` (`uv sync --locked`).
- No worktree is ever added to it, nothing is ever pulled into it, and it is never used for development.
- It is the foundation's only code root and its schema root (`<clone>/.research-system/schemas`). The foundation's
  `code_roots` then lists one path, replacing the current 28.

**Kind.** Procedure, plus the two fields in the re-pin commit.

### 2.4 SOURCE provenance (M-2)

**Current behaviour.**
- `document_manifest` copies `production` verbatim from the intent (`spec_source.py:234-245`), and nothing
  checks it.
- `source_ids` derives the artefact, observation and Candidate IDs from `production.task_id`
  (`spec_source.py:25-35`). So the Task must be named before the Candidate exists.
- An Attempt's start record carries `context_packet_id`, `code_identity` and `environment_fingerprint`
  (`attempt_started` schema). Its stream carries `task_id`, `task_revision` and `dispatch_id`. The operator
  records derive exactly these (`spec_assay.py:683-733`).

**Options (P5-7).**
- **(S1, recommended)** A separate SOURCE Task. The intent keeps its schema (`spec-source-intent` 1.0.0, so no
  record change under D3). The route refuses, before any write, unless all of these hold:
  - `production.task_id` names a Task that names no registered Candidate;
  - that Task has exactly one started Attempt, which is running;
  - the Task is unamended since that Attempt's dispatch;
  - the intent's `dispatch_id`, `attempt_id`, `context_packet_id`, `code_commit` and `environment_fingerprint`
    equal the ledger's.

  The same applies to `correct_spec_01_source`. `producer_profile`, `branch_identity`, `worktree_identity` and
  `accepted_scope` stay caller strings: the ledger does not hold them, and the same is true of every other
  route manifest. That is a known limit.
- **(S2)** One Task spans SOURCE to closure: the Task names the Candidate ID derived from its own ID before the
  Candidate exists. Fewer live operations, but it needs unmeasured admission behaviour (a reference to an
  unregistered Candidate) and couples the SOURCE artefact to the closure Attempt. Not recommended now.

**Consequence.** Every public-path test seeds a running SOURCE Task first. That adds per-test cost, which is
measured against the P-058 25% rule. Phase 5 step 3 adds the SOURCE Task seeding (and its completion after
registration) before `observe_source`.

**Kind.** Code, in the route only. It ships in its own certified PR, as Stephen decided.

### 2.5 The Assay authority content and its signing identity

**Current behaviour.** The route loads two fixed files, `ASSAY_RUBRIC_PATH` and `ASSAY_SCOPE_PATH`
(`spec_assay.py:147-148`). They are W11 fixture content:
- one boolean `identity` gate;
- placeholder `1111…` reference hashes;
- author `act_019fed25-…-000000000205`, which admission requires as the submitter and the route reads
  (`:2284`).

**Recommendation.**
- **Replace both files in place** with SPEC-01's bar:
  - Axis 1, `topology_earns_its_keep`, a boolean gate;
  - Axes 2 and 3, integers in [0,3] (W11 §4.3 legacy mapping);
  - the evidence rows SPEC-01's brief requires;
  - real hashes for the brief and contract it cites.
- **Keep the current fixture bytes** as test fixtures under `tests/`, and pass them through the existing
  `repository_overrides` hook of `bind_scratch_route`. Route tests keep their behaviour; new tests cover the
  real bar.
- **Signing identity (P5-9).** The author is a dedicated non-owner actor on the fresh store. Stephen stays
  acceptor (OR-108), a third identity reviews (OR-105/106), and the file observer (OR-103/104) differs from
  the author. The route bindings already enforce author ≠ requester. The author's actor ID must be allocated
  before the content is committed, so the fresh run's actor plan (owner, author, observer, reviewers, producer,
  proposer, and the SOURCE and SPEC-01 Task actors) is a prep output.
- The content is methodological. Stephen reviews the bar itself in that PR, beyond the code review.

**Kind.** Committed content, test fixtures and procedure (the actor plan). The rule is §2.6.

### 2.6 Where SPEC-01's numeric rule is evaluated (P5-8)

**Current behaviour.**
- Admission derives `mechanical_recommendation` from the required gate axes alone: PROMOTE or KILL
  (`rules.py:507-513`).
- It requires the scorecard's field to equal that derivation (`:536`).
- The route refuses PROMOTE on any bar with a non-gate axis (`spec_assay.py:1411-1432`).

So with SPEC-01's content, a topology pass makes the scorecard record **PROMOTE** whatever the integer axes are,
and the route then refuses PROMOTE. On SPEC-01's bar, PROMOTE is unreachable on the route, and a PARK Assay
carries a scorecard that says PROMOTE.

**Options.**
- **(R-A, recommended)** Admission evaluates the rubric's declared algorithm.
  - A registered `rule_evaluation_algorithm_id` for the legacy bar yields PROMOTE, PARK or KILL by W11 §4.3: PROMOTE
    when Axis 1 passes, Axis 2 + Axis 3 ≥ 4 and neither is 0; PARK otherwise; KILL on a gate fail. W11 already
    lists PARK as a mechanical recommendation.
  - The fixture algorithm keeps today's behaviour.
  - The route's blanket refusal is narrowed to bars whose algorithm admission does not evaluate.
  - The scorecard then records SPEC-01's real result.
  - This is a W11 runtime change, which P-058 (2026-09-16) classed under D5, so it needs Stephen's exception.
- **(R-B)** The route evaluates the rule at OR-012 and OR-013 and permits PROMOTE only when the rule holds. The
  rubric declares the gate-only algorithm honestly. Residual: on a SPEC-01 PARK the scorecard still says
  mechanical PROMOTE under the gate-only rule, and the PARK rationale must cite the numeric rule. Whether the owner
  can select PARK after a mechanical PROMOTE is unmeasured; the census measures it.

**Kind.** Code, either W11 runtime (R-A, D5 exception) or route (R-B).

### 2.7 `adopt_default` against the SPEC-02 no-claim rule (P5-10)

On this route a PROMOTE terminal decision comes only from `decide_spec_02`. `_PERMITTED_DISPOSITIONS` then allows
`adopt_default` (`spec_result.py:61-65`), while the SPEC-02 contract says no result supports a superiority or
paper claim. Phase 5's planned path (PARK/no_spike) never reaches it.

**Recommendation.** Permit only `retain_experimental_benchmark` after PROMOTE, with a decisive control. This is a
one-line route change plus a test.

**Kind.** Code. It goes in its own PR, or in the M-2 PR if Stephen allows.

### 2.8 The binding's schema-catalogue re-check cost

Unchanged under D5 (P-058 2026-10-01): about five revalidations per invocation at about 1.3 s each, plus about
2.5 s of git. The 4c A/B ran the SPEC-01 public path (31 invocations, including fixture work) in 356 s, so expect
roughly 10–20 s for each live invocation and about 10 minutes of CLI time over the whole live run.
**Procedure only.**

### 2.9 The Task named in SPEC-01, before `prepare_spec_01`

**Procedure** (route rules already enforced):
- create the Task naming only the SPEC-01 Candidate after `observe_source`;
- dispatch, claim and start its Attempt with `code_identity = git:sha1:<bound SHA>` and the checkout's
  environment fingerprint;
- start it before `prepare_spec_01`;
- do not amend the Task while the Attempt runs;
- keep the Attempt running until the operator return (complete or Partial) is registered.

The public commands for this are unmeasured (§2.11).

### 2.10 The runbook note (m-4)

**Procedure.** After an admission refusal of a time-free effect (`RecordScientificReview` or
`SetArtefactUseAuthority`, on a correction or the project-use decision), do not retry under the same actor and
grant. The same command identity returns the stored refusal. Activate a new grant and retry under it. This goes in
the Phase 5 runbook in the docs PR.

### 2.11 Seams the tests replace, not yet measured

- **Grant activation.** `activate_lifecycle_grant` writes the owner's administration decision straight into the
  object store (`tests/research_system/factories.py:393`, `:484`) and then submits `ActivateAuthorityGrant`. The
  bootstrap's root grant allows only `RevokeAuthorityGrant`.
- **Task and Attempt seeding.** Tests use `GovernedTestCommandService` with trusted runtime authority
  (`test_spec_task.py:165-206`). The public route for this is `ars command submit --config … --host-identity
  --boot-identity`.

Each may have a public path, or may be a further B-class gap. **Recommendation (P5-11):** construction starts with
a disposable census driver. It runs the whole live sequence on scratch roots through the genuine CLI only, and
records every refusal. A hand-written binding is allowed only to reach seams beyond B-2, and is labelled as such.
The census fixes the PR list before any PR is cut, rather than finding gaps one review at a time.

## 3. Construction plan

| Step | Deliverable | Kind | Certification |
|---|---|---|---|
| C0 | Census (§2.11), with a short report to Stephen | Disposable driver | None. It is evidence for the PR list. |
| PR-A | `store reserve` and the initial-store first binding (B-1 helper, B-2), with a **committed slow binding test**. That test runs the genuine CLI from a non-linked scratch clone through reserve, re-pin, init, first binding and `spec status`, with no foundation monkeypatch. It is the enforcement artefact for obs 2026-10-07 (one unpatched test per seam). | Code, STORE (D5 exception) | The STORE packet (06s §12), the new tests and mutation controls |
| PR-B | M-2 SOURCE provenance (S1) | Code, route | The SOURCE packet, the SPEC-01 public path as canary, and controls |
| PR-C | The Assay bar: content, fixtures, SPEC-01 rule (R-A or R-B) and the actor plan | Code and content | The Assay packet and the SPEC-01 path, plus a rule truth-table test |
| PR-D | `adopt_default` | Code, route | The project-use packet |
| PR-E | Anything the census adds | Decided after C0 | Decided after C0 |
| Docs | P-058 amendments, the runbook (m-4, §2.9 sequence), and the step-6 amendment | Docs | `git diff --check` |
| PR-F | The foundation re-pin, the contract-test update and the SCALE note. It needs the live reservation first (§4 L2). | Configuration | The contract test, plus the binding test against the reservation |

Each PR's certification runs its own packet plus the SPEC-01 public path as canary (about 6 minutes on a clean
machine). The heavy SPEC-02 tests run once, in the delta assurance. The 06s §5.0 scope checkpoint applies to
each PR. PR-A is the most likely to approach it.

## 4. The live sequence

Each **A#** is a separate explicit authorization by Stephen. Before each one I prepare the exact command and
inputs, and after it I verify the durable result.

1. **Construction merges:** PR-A to PR-E and the docs PR, each reviewed and merged by Stephen, at main `M1`.
2. **A1, durable checkout.** Clone GitHub `main` at `M1` into `C:/Users/steph/TDL-ARS-G6-Checkout`, then
   `uv sync --locked`. Verify the clone is not linked, is clean, `git worktree list` shows one entry, and local
   `main` is at `M1`.
3. **A2, roots.** Create the empty origin authority `C:/Users/steph/TDL-ARS-G6-Origin-Authority`. Confirm
   `C:/Users/steph/TDL-ARS-G6-Control` does not exist.
4. **A3, reserve.** From the checkout, run `ars store reserve --code-root <checkout> --control-root
   <G6-Control> --origin-authority-root <G6-Origin> --project-id prj_…1000 --authority-bootstrap <bootstrap>`.
   Record the printed foundation fields. Verify one stage, one witness and no published store.
5. **PR-F, the re-pin.** Commit the printed fields (control root, store identity, witness path and digest,
   origin root, URI, `code_roots: [<checkout>]`, `schema_root: <checkout>/.research-system/schemas`, tail
   `(0, "0"*64)`, `foundation_sha256`) and the contract-test update. **A4:** Stephen reviews and merges it,
   giving main `M2`. The re-pin merges *before* `store init`.
6. **Delta assurance on M2** (§5). **A5:** Stephen records that it passed.
7. **A6, init.** Fast-forward the checkout's `main` to `M2` (a clean fast-forward; the only checkout update in
   Phase 5), then run `ars store init`. Verify the identity and witness digest equal the pins, no stage is
   left, and `ApprovedProjectBinding` loads.
8. **A7, step 1: the first binding.** Run the B1 owner action with the checkout as candidate at `M2`. Then
   `ars discovery spec status` succeeds.
9. **Freeze.** From here to step 6, nothing is pulled into the checkout, and no worktree is added to it.
10. **Phase 5 steps 2 onward,** as amended: the SOURCE Task (§2.4), then `observe_source`, then the SPEC-01
    Task (§2.9), and so on.

If the delta assurance requires a code fix after `M2`, the reservation and re-pin stay valid. The fix gives
`M3`, the assurance re-runs on `M3`, and steps 7–8 use `M3`.

## 5. Delta assurance on the post-prep SHA

**Selection: full, not delta-selected.** The prep diff touches:
- STORE init and binding, which the Phase 0 packet covers;
- `observe_source`, which every public path test runs first;
- the Assay bar, which every SPEC-01 test uses.

A delta selection would therefore be almost the whole selection. Run the 4c selection (310 nodes in 64 groups)
plus the new nodes, through `C:/Users/steph/.codex/tmp/g6-4c/assemble_4c.py` with a new collected node list. The
runner is resumable, reconciles every node against JUnit, and keeps the window and budget flags. Copy the runner
next to its evidence (obs 2026-10-06-certification-runner-lives-in-a-dead-session-scratchpad).

**Budget.**
- P-058's limits stand: 02:00–11:00, 8 workers, 60 minutes per group, 5 hours per packet.
- Under #331's conditions the same tests summed to 14.8 h, which is about 2–2.5 h of wall time at 8 workers.
  The worst group was the complete SPEC-02 path at 54 minutes, close to the 60-minute limit.
- M-2's SOURCE seeding adds cost to every path test. Measure the SPEC-01 path before and after PR-B, and put
  any rise over 25% in that PR's decision table.

**Machine check (before every certification window).** Record, in the run's evidence folder:
- the top processes by CPU and memory;
- that no other `pytest`, `uv` or long Python job is running;
- that no Codex or Claude runs are scheduled in the window;
- a 60-second CPU-idle sample.

If the check fails, delay the start; the runner already refuses to start after 08:00. Bring it to Stephen
only if the SPEC-02 complete path exceeds 60 minutes on a clean machine. That would be a real regression, and
the remedy would be #331-style splitting.

**Fresh-context review brief (draft).**
- **Subject:** `e5179b57..<post-prep SHA>`, reviewed in its own detached worktree, with no live store, provider
  or credential.
- **Required verdicts:**
  1. **B-1:** a store not named at `e5179b57` is created through the public CLI with the committed foundation,
     and the pin is committed before `store init` writes the witness. Cite the binding test and the live A3/A6
     records.
  2. **B-2:** an initialized store gets its first binding through the public service; its admission refuses a
     restored, bound or tampered store; `spec status` succeeds with no fixture binding.
  3. **M-1:** the foundation's code and schema roots are the one durable non-linked checkout.
  4. **M-2:** SOURCE production references equal the ledger's, for observation and correction.
  5. The SPEC-01 rule and the Assay bar: the truth table; no PROMOTE is reachable against the rule; the
     scorecard records the rule's result (R-A) or the documented residual (R-B).
- **Also:** no authority, owner or paid-gate bypass; no durable misstatement; replay equality; and the STORE
  exception limited to what Stephen granted.
- **Format:** the 4c review's (findings table, then dispositions).

## 6. What I did not do

- No construction, no commit or push of this document, no PR and no Jira write. KAN-110 was read: To Do, with
  labels `g6-phase5-prep` and others, and its blocks link to KAN-103 unchanged. I propose to update it after
  Stephen accepts this design.
- No live operation. The scratch roots under `C:/Users/steph/TDL-p5-rehearsal` can be deleted, or kept as the
  probe evidence.
- The census seams (§2.11) and the admission behaviour R-B needs are unmeasured.
