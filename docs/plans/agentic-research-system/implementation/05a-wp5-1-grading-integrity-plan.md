# ARS P0 Work Package 5.1: Grading-Integrity Closure Implementation Plan

> **For the implementing Worker:** use contract-first-tdd and
> research-assurance-triage. Write one failing public-seam test before each
> production change. Do not author a new math-correctness contract: O14 and O16
> are control-plane provenance invariants already frozen by the accepted Gate 5
> scope; the binding tests in this plan are their enforcement artifacts.

**Status:** approved for Worker dispatch; implementation remains isolated and
subject to the review-then-merge gate.

**Goal:** Close Gate 5 obligations O14 and O16 without changing the P0 fixture
corpus, release acceptance set, or aggregate invariants: make grader-family
independence consume truthful per-run execution context, and make deletion
authorization source the current retention-policy revision independently from
the canonical tracked policy.

**Architecture:** Preserve the strict GraderResult -> validate_grader_result ->
decide_release path. Replace role-shaped family literals at the harness seam
with typed identities derived from the actual evaluation transport/context. A
fake-only run has one available execution family, so it must not masquerade as a
cross-family run. Separately, move policy validation into the deletion-authorizer
factory and derive the canonical policy path from the bound schema root; a stale
evidence-store registry must not validate itself.

**Tech stack:** Python 3.13.5, frozen dataclasses, pathlib, pytest, ruff, existing
research_system.evals models/release/retention modules, fake transport only.

**Owner authorization:** Stephen approved the Gate 5 scope and D-G5-1 option (a)
on 2026-07-10. D-G5-4 is also closed. WP5.1 changes no invariant and needs no
additional owner decision. D-G5-2 remains open and is out of scope.

## Global Constraints

- Branch pipe/ars-gate5-grading-integrity from the approved main; isolated
  worktree under .apm/worktrees/. Immediately copy
  C:/Users/steph/TDL/.env to the worktree. The Worker commits and reports; the
  Manager alone merges.
- Review-then-merge is mandatory. CodeRabbit must conclude before the Manager
  merges with gh pr merge; never fast-forward a local branch onto main.
- Fake transport only. No live provider, live M/H threshold policy,
  DeleteEvidenceObject, variant execution, parity wiring, release-event
  publication, S-014/S-015/S-016, Gate 6, migration, or research claim.
- Invariants remain exact stop conditions after every task:
  fixture_count: 37, blocked_fixture_count: 14,
  fixtures_with_uncalibrated_mutations: 0,
  mutation_calibration: "calibrated", result_count: 122, and
  candidate_status: "blocked".
- **Identity truth rule:** producer_family and grader_family must come from a
  typed execution context attached to the run. Profile/role names such as
  reference-subject, live-judgment-pending, or deterministic-package-grader are
  not family evidence. Under fake-only P0, no distinct live grader family
  exists; cross-family rows therefore stay incompatible/unable_to_grade rather
  than receiving invented diversity.
- **Canonical-policy rule:** the current revision comes only from
  validate_retention_policy(binding.schema_root.parent / "evals" /
  "retention-policy.yaml"). It never comes from registry.policy_revision, the
  command payload, process CWD, or a new caller-controlled CLI flag.
- Preserve anti-anchoring and exact required-result closure. Do not adjust an
  oracle, fixture, required grader, threshold policy, or expected invariant to
  make a test pass.
- Commit subjects use [PIPELINE] P00: and a Co-Authored-By trailer. Write
  multi-line commit messages to a BOM-free UTF-8 file and use git commit -F;
  never --no-verify.
- Use uv run --no-sync for every command on this machine. Quality gates for
  each task:

~~~powershell
uv run --no-sync ruff check research_system tools/ars tests/research_system
uv run --no-sync pytest tests/research_system -q --no-cov
~~~

## File Map

**Modify for O14:**

~~~text
research_system/evals/harness.py
tests/research_system/unit/test_graders.py
tests/research_system/integration/test_release_coordinator.py
~~~

**Create for O16:**

~~~text
tests/research_system/integration/test_command_cli.py
~~~

**Modify for O16:**

~~~text
research_system/evals/retention_authorizer.py
research_system/cli.py
tests/research_system/unit/test_retention.py
~~~

**Close-out records:**

~~~text
docs/plans/agentic-research-system/implementation/04a-wp4-8-verdict-derivation-and-release-evidence-plan.md
vault/04-Methods/Computational-Log.md
~~~

Do not modify research_system/evals/models.py, .research-system/schemas/**,
.research-system/evals/fixtures/**, p0-coverage.yaml, p0-variant-matrix.yaml,
retention-policy.yaml, research_system/evals/release.py, or
research_system/command/service.py. If the current string family fields or
service interface prove insufficient, stop Partial and escalate before
expanding the schema or command surface.

## Obligation Register

| ID | Source | Obligation | Owner | Disposition |
|---|---|---|---|---|
| G1 | Gate 5 scope approval | No WP5 dispatch before scope approval | Owner | Delivered 2026-07-10 |
| G2 | 04a O14 / scope WP5.1 | Cross-family branch consumes real per-run family identities and rejects a same-family pair | WP5.1 | Task 1 |
| G3 | 04a O16 / scope WP5.1 | Current policy revision comes from canonical retention-policy.yaml through validate_retention_policy | WP5.1 | Task 2 |
| G4 | D-G5-1(a) | Missing M/H authority remains capability-blocking; no fabricated cross-family pass | WP5.1/WP5.6 | Task 1 preserves; WP5.6 records restriction |
| G5 | Gate 4 stop conditions | 37 fixtures, 14 blocked, 122 results, candidate blocked | WP5.1 | Tasks 1-3; exact smoke in Task 3 |
| G6 | Research assurance | Machine-checkable provenance claims have negative binding tests | WP5.1 | Tasks 1-2 |
| G7 | Review discipline | Full gates, register closure, vault record, CodeRabbit before merge | Manager/Worker | Task 3 |

## Research Assurance Requirements

- **Assurance lanes touched:** Output/Provenance only.
- **Governing sources:** accepted Gate 5 scope WP5.1; 04a O14/O16;
  06-evaluation grader pass rule and GraderResult identity semantics; accepted
  P0 plan section 7/7.1; D-G5-1(a); CONVENTIONS.md research assurance and
  value/type enforcement rules.
- **Parameters/seeds:** none. This task adds no stochastic operation.
- **Contract disposition:** no new contracts/ manifest. These are control-plane
  provenance invariants, not a mathematical/statistical formula; the accepted
  specifications are upstream authority and the public-seam negative tests are
  the binding artifacts.
- **Machine-checkable claims:**
  - truthful family source -> production harness exposes the actual fake
    execution family, never role labels;
  - same-family cross-family requirement -> strict release reports
    cross-family independence unavailable;
  - canonical policy source -> a stale registry plus a manifest built from that
    same stale registry is rejected against the tracked policy;
  - no regression -> current manifest still emits exactly one unchanged
    EvidenceDeletionVerified; tampered/malformed manifests emit none;
  - invariant preservation -> exact Task 3 smoke.
- **Human-review-only questions:** Does each family value identify the execution
  context that actually produced/graded the row, rather than a label chosen to
  satisfy the validator? Is the policy path anchored to the bound
  .research-system tree rather than CWD or caller choice?
- **Output provenance:** no new numerical result or cache. The only durable
  evidence is tests, exact CLI smoke, commit/PR, obligation-register updates,
  and the top-of-page vault [PIPELINE] entry.
- **Partial criteria:** no truthful family source, ambiguous canonical policy
  root, any schema/service expansion, any invariant drift, or any need to weaken
  a required result -> report Partial and stop.

## Task 1: Bind grader independence to actual execution context (O14)

**Files:** research_system/evals/harness.py,
tests/research_system/unit/test_graders.py, and
tests/research_system/integration/test_release_coordinator.py.

**Interfaces:**

- Add a frozen, slotted ExecutionContextIdentity dataclass in harness.py with
  actor_id: str, family: str, and profile: str. Add an ExecutionContextFactory
  callable seam consumed by run_p0_coverage; its inputs include the validated
  transport, fixture/run identity, grader requirement, and live/unavailable
  state, and it returns the producer/grader context pair.
- For one fixture/run, create the producer context once and bind it to every
  result from that run. Create the grader/evaluator context per required result.
  The fake factory derives both families from coverage.transport (fake), while
  profile remains role-specific and separate.
- The two family fields consume context.family; role/profile strings never
  enter them. executed_by_actor_id consumes the grader/evaluator context actor.
- The fake P0 path has no independently executed live family. Its cross-family
  rows must therefore exercise the same-family failure branch and remain
  blocking. The typed factory is the injection seam for a future real distinct
  producer/grader pair; no live implementation is added here.

- [ ] **Step 1: Write failing public-seam tests.**

  In test_release_coordinator.py, add a test that runs the real P0 harness and
  proves:

  1. family values come from the fake execution context, not the three retired
     role literals;
  2. every required cross-family row under fake-only execution is reported in
     `decide_p0_release(...)[incompatible]` with
     cross-family independence unavailable;
  3. result-key closure remains exact and the overall decision remains blocked.

  This test must fail on current main, whose never-equal role literals make the
  cross-family branch unreachable.

  In test_graders.py, add/retain focused controls: an explicit same-family pair
  under a cross-family requirement raises UnableToGrade; an explicitly
  different-family pair with all other immutable bindings correct is gradeable.

- [ ] **Step 2: Run the red tests.**

~~~powershell
uv run --no-sync pytest tests/research_system/unit/test_graders.py tests/research_system/integration/test_release_coordinator.py -q --no-cov
~~~

  Record the failing test name and assertion. A collection/environment failure
  is not the required red state.

- [ ] **Step 3: Implement the minimal typed context binding.**

  Remove the fixed family literals from GraderResult construction. Keep
  profile/role and family semantically distinct. Do not special-case a fixture,
  grader ID, or expected error message. Do not modify the strict validator to
  make the new evidence pass; the purpose is to make its existing failure
  branch reachable from production evidence.

- [ ] **Step 4: Run targeted and invariant smoke.**

~~~powershell
uv run --no-sync pytest tests/research_system/unit/test_graders.py tests/research_system/integration/test_release_coordinator.py tests/research_system/integration/test_eval_cli.py -q --no-cov
uv run --no-sync python -m research_system.cli eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync python -m research_system.cli eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake
~~~

  Exact invariant values remain 37/14/0/calibrated and blocked/122.

- [ ] **Step 5: Commit.**

  Subject: [PIPELINE] P00: bind grader independence to execution context

## Task 2: Source deletion policy revision canonically (O16)

**Files:** create tests/research_system/integration/test_command_cli.py; modify
research_system/evals/retention_authorizer.py, research_system/cli.py, and
tests/research_system/unit/test_retention.py.

**Interfaces:**

- Change
  build_deletion_manifest_authorizer(registry, *, current_policy_revision)
  to
  build_deletion_manifest_authorizer(registry, *, retention_policy_path: Path).
- The factory calls validate_retention_policy(retention_policy_path) once,
  type-checks/extracts policy_revision, and captures only that validated
  revision in the closure.
- _command_submit derives the path from
  binding.schema_root.parent / "evals" / "retention-policy.yaml".
  Do not add --retention-policy.
- Keep validate_deletion_manifest_for_event, CommandService, event payloads,
  replay, and registry schema unchanged.

- [ ] **Step 1: Write the failing stale-self-validation test.**

  Construct a registry at p0-retention-v0; create its manifest through
  verify_deletion so registry and manifest agree with each other; build the
  production authorizer using the canonical policy path; assert authorization
  raises ValueError matching stale deletion registry or policy. Exercise
  through CommandService where practical and assert no event batch or receipt
  was written.

  Add a construction-time negative test for a missing/malformed policy path.
  Update existing positive, wrong-hash, tampered, and malformed payload tests to
  the new factory interface.

  In test_command_cli.py, exercise the public main(["command", "submit", ...])
  composition seam with controlled test doubles and capture the factory keyword
  arguments. Assert retention_policy_path equals
  binding.schema_root.parent / "evals" / "retention-policy.yaml", and assert
  no raw current_policy_revision is supplied. This is the binding test for the
  production caller, not a private factory-only assertion.

- [ ] **Step 2: Run the red tests.**

~~~powershell
uv run --no-sync pytest tests/research_system/unit/test_retention.py -q --no-cov -k "authorizer or retention_policy or evidence_store_registry"
uv run --no-sync pytest tests/research_system/integration/test_command_cli.py -q --no-cov
~~~

- [ ] **Step 3: Implement the factory and production composition change.**

  The independently validated policy must be loaded before
  service.submit(command). A stale registry may still produce a stale manifest,
  but the authorizer must reject it against the canonical revision.

- [ ] **Step 4: Run targeted verification.**

~~~powershell
uv run --no-sync pytest tests/research_system/unit/test_command_service.py tests/research_system/unit/test_retention.py tests/research_system/integration/test_command_cli.py -q --no-cov
uv run --no-sync python -m research_system.cli eval retention validate --policy .research-system/evals/retention-policy.yaml
uv run --no-sync ruff check research_system/evals/retention_authorizer.py research_system/cli.py tests/research_system/unit/test_retention.py
~~~

- [ ] **Step 5: Commit.**

  Subject: [PIPELINE] P00: source deletion policy revision canonically

## Task 3: Full verification, obligation closure, and PR handoff

**Files:** modify only the O14/O16 disposition cells in the 04a obligation
register; prepend one matching [PIPELINE] entry to
vault/04-Methods/Computational-Log.md after read-reconcile-place.

- [ ] **Step 1: Run full gates.**

~~~powershell
uv run --no-sync ruff check research_system tools/ars tests/research_system
uv run --no-sync pytest tests/research_system -q --no-cov
uv run --no-sync python -m research_system.cli eval validate --catalogue .research-system/evals/catalogue.yaml
uv run --no-sync python -m research_system.cli eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync python -m research_system.cli eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync python -m research_system.cli eval retention validate --policy .research-system/evals/retention-policy.yaml
git diff --check
~~~

  Expected exactly: validate 37 fixtures; calibrate fixture_count=37,
  blocked_fixture_count=14, fixtures_with_uncalibrated_mutations=0,
  mutation_calibration="calibrated"; run candidate_status="blocked",
  result_count=122; retention revision p0-retention-v1 with five rules. Any
  deviation is Partial/stop.

- [ ] **Step 2: Close the register and record provenance.**

  Update 04a O14 to delivered by WP5.1 Task 1 and O16 to delivered by WP5.1
  Task 2. The vault entry names both obligations, the exact negative tests,
  full test count, invariant smoke, branch/commits, and no new seed.

- [ ] **Step 3: Commit and report to the Manager.**

  Subject: [PIPELINE] P00: close Gate 5 grading-integrity obligations

  Push the Worker branch and provide the Manager a Task Report containing:
  changed files, red/green evidence per task, Research Assurance Evidence,
  exact invariant outputs, commit hashes, and remaining gaps. Do not merge.
  The Manager will open or review the PR, fetch both issue comments and inline
  review comments, wait for CodeRabbit to conclude, disposition findings,
  rerun gates on the final branch, and merge with gh pr merge.

## Acceptance Checklist

- [ ] No fixed role literal populates either family field in production.
- [ ] Same-family cross-family evidence reaches and is rejected by the strict
      release path.
- [ ] A genuinely distinct-family unit control remains gradeable.
- [ ] The deletion authorizer accepts a policy path, not a raw current revision.
- [ ] Production composition derives the path from the bound schema root.
- [ ] A stale registry cannot self-validate its own stale manifest.
- [ ] Current manifest acceptance and tamper/malformed rejection remain intact.
- [ ] No model/schema/service/fixture/policy/coverage change.
- [ ] Exact 37/14/122/blocked invariants hold.
- [ ] 04a O14/O16 delivered; vault entry written.
- [ ] CodeRabbit concludes before Manager merge.

## Stop Conditions

1. A truthful family identity cannot be obtained without inventing role labels
   or changing an accepted W4/W6/W7 identity contract.
2. The canonical policy cannot be located from the bound schema root without
   CWD inference or caller choice.
3. Any change to GraderResult schema, CommandService, fixture corpus, retention
   policy, release acceptance set, or Gate 5 owner decisions.
4. Any invariant drift from 37 fixtures, 14 blocked, 122 results, candidate
   blocked, or complete mutation calibration.
5. A required negative test cannot be made red on pre-change code or green
   without weakening the validator.
