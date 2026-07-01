# ARS P0 Materialization and Narrow Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** `review_reconciled_pending_approval`; planning authority only

**Goal:** Build the smallest production-intended Agentic Research System foundation that can prove the accepted W1–W8/06c contracts against the P0 fixture dependency closure without migrating active APM work.

**Architecture:** Implement a local Python 3.13 modular monolith with one explicit command boundary, a dedicated external hash-chained control root, tracked provider-neutral definitions under `.research-system/`, and disposable projections. Four independently testable work packages converge through a deterministic evaluation harness; provider and operational evidence remain untrusted inputs until W6 grades them.

**Tech Stack:** Python 3.13.5, standard-library `dataclasses`/`pathlib`/`hashlib`/`argparse`, PyYAML, JSON Schema Draft 2020-12 via `jsonschema`, pytest, ruff, atomic filesystem replacement, subprocess argument arrays without shell interpolation.

---

## 1. Authority and non-migration boundary

This document is the Gate 4 implementation-plan proposal required by P-026 and P-030. It incorporates the required changes from `reviews/adversarial-p0-plan-suite-review-2026-07-01.md` through the dated reconciliation record, but it does not itself authorize implementation.

Implementation may begin only after Stephen accepts this reconciled plan, its exact work-package scope, and the owner decisions in section 7.3. Execution must:

- use an isolated implementation worktree and a `codex/ars-p0-foundation` branch;
- keep T1.28, both current APM-managed papers, `.apm/`, existing contracts, results, caches, and research claims outside the foundation's writable scope;
- use only synthetic, minimized, or explicitly reconstructed fixture inputs;
- require an explicit absolute control-root path outside the code repository and outside every task worktree;
- create no live provider invocation until the adapter work package passes deterministic fake-transport tests and Stephen authorizes a bounded non-sensitive smoke;
- stop as Partial when a required interface, independence route, provider capability, threshold policy, or grading oracle is unavailable.

## 2. Work-package decomposition

| Order | Plan | Responsibility | Independent acceptance |
|---|---|---|---|
| 1 | [01-control-plane-and-replay-plan.md](implementation/01-control-plane-and-replay-plan.md) | Package skeleton, schemas, IDs, canonical JSON, external control root, single writer, commands, events, receipts, replay, projections, CLI | S-001/S-002/S-006/S-008/S-009/S-010/S-011/S-012 plus F-001–F-005 |
| 2 | [02-context-routing-and-assurance-plan.md](implementation/02-context-routing-and-assurance-plan.md) | W3 context compilation/token gates, W5 requirement integrity, W4 deterministic routing/independence | F-021/F-022/F-025–F-028/F-031/F-033/F-035/F-036 |
| 3 | [03-adapters-and-operations-plan.md](implementation/03-adapters-and-operations-plan.md) | W7 policy/adapters/receipts/parity plus W8 profiles/grants/leases/checkpoints/recovery | F-007–F-010/F-020/F-032/F-034 and S-003/S-004/S-013 |
| 4 | [04-evaluation-and-p0-fixtures-plan.md](implementation/04-evaluation-and-p0-fixtures-plan.md) | W6 fixture schemas, traces, graders, coverage/release decisions, complete fixture packages, integrated scenarios | All 37 P0-materialization cases and Gate 3 scenarios A–E |

Each work package produces useful tested software and its own commit sequence. Work packages 2 and 3 may begin after work package 1 freezes shared model/schema helpers; work package 4 may scaffold its schema/runner against fakes but cannot declare integrated passes before packages 1–3 are accepted.

### 2.1 Shared interface ownership after plan review

The child plans consume these interfaces rather than defining local substitutes:

| Interface | Sole owner | Consumers | Freeze condition |
|---|---|---|---|
| canonical ID kind/prefix registry and UUIDv7 body | WP1 from W2/W4/W5/W6/W7/W8 owner catalogues | WP1–WP4 | every P0 identity has one registered kind, exact owner prefix, and field-scoped validator; no arbitrary prefix API |
| committed-command/idempotency recovery | WP1 | WP2–WP4 | retry after event rename and before receipt reconstructs the original receipt from committed events |
| `PreparedDispatch` | WP2 in `research_system/routing/models.py` | WP3/WP4 | exact requirement/context/route/provider/operations evidence IDs/hashes, attempt ID, expiry, and `unissued` state |
| provider-token evidence | WP3/W7 adapter port | WP2/WP4 | units are provider tokens; provider/model/rendering/wrapper revision and evidence quality are explicit |
| fixture/required-grader closure | WP4 | all release consumers | release derives the complete required tuple set and blocks missing, stale, duplicate, or incompatible evidence |
| evidence-store and deletion-verification manifest | WP4 policy plus WP1 commands | release/retention consumers | checked locations derive from an authorized registry; caller-supplied booleans cannot establish deletion |

F-031/F-033 route and verifier-feasibility primitives belong to WP2. F-032/F-034 integrated outage, permission, root, sensitivity, and operational paths belong to WP3/WP4. Cross-package contract tests may consume another package's fixture data but do not duplicate ownership.

## 3. Planned file structure

```text
research_system/
  canonical.py
  ids.py
  errors.py
  config.py
  schema_registry.py
  command/
  store/
  projection/
  context/
  assurance/
  routing/
  policy/
  adapters/
  operations/
  evals/
  cli.py

.research-system/
  config/
  schemas/
    core/
    context/
    routing/
    assurance/
    adapters/
    operations/
    evals/
  policies/
  packs/
  adapters/
  evals/
    catalogue.yaml
    p0-calibration-policy.yaml
    fixtures/{fixture_id}/
    p0-variant-matrix.yaml

tests/research_system/
  unit/
  integration/
  fixtures/
```

Tracked `.research-system/` content contains definitions only. `.research-system/projections/`, `.research-system/indexes/`, and `.research-system/runtime/` are ignored local projections/caches. Dynamic canonical `objects/`, `events/`, `manifests/`, `receipts/`, `snapshots/`, and writer runtime live only beneath the explicit external control root.

## 4. Exact P0 materialization closure

### 4.1 Priority-P0 fixtures

```text
F-001–F-005
F-007–F-014
F-020
F-022
F-025–F-028
F-031–F-036
```

These 25 fixtures retain priority `P0` and `gate_stage: p0_materialization`.

### 4.2 P1 dependency fixture required during P0

`F-021` retains priority `P1` but receives `gate_stage: p0_materialization` for its mandatory-closure sizing variant because P-028 requires F-021/F-022/F-025/F-026 measurement under both token gates before context/compiler release. Its broader stale-memory oracle remains a later P1 gate.

### 4.3 Synthetic dependency scenarios

```text
S-001, S-002, S-003, S-004, S-006, S-008,
S-009, S-010, S-011, S-012, S-013
```

These eleven scenarios are materialized without changing their accepted priority. Together, sections 4.1–4.3 define 37 executable P0-materialization cases.

### 4.4 Explicitly deferred cases

- `F-006`, `F-015–F-019`, `F-023–F-024`, `F-029–F-030`, and `F-037–F-038` remain outside P0 except for dependencies already represented by a P0 case.
- `S-005`, `S-007`, and `S-014–S-016` remain later `foundation_release` or `pilot_promotion` cases.
- Before Gate 5 foundation release, a follow-on release tranche must add at least S-014 backup/restore, S-015 supersession-cycle rejection, and S-016 R3 provider-outage handling.

## 5. Execution DAG and review checkpoints

```text
P0-0 plan acceptance and isolated worktree
  -> P0-1 control-plane primitives and schemas
  -> P0-2 single writer, replay, projections, CLI
       -> P0-3A context/routing/assurance
       -> P0-3B adapters/operations
            -> P0-4 evaluation harness and fixture packages
            -> P0-5 integrated scenarios A–E
            -> P0-6 independent review and P0 release decision
```

Review checkpoints:

1. **Identity and recovery freeze:** an independent software/provenance reviewer checks the owner-derived ID registry, UUIDv7 validation, root separation, all-worktree/reparse-point rejection, committed-command reconstruction, and zero-or-one batch behavior before reducers are extended.
2. **Schema freeze:** the same reviewer checks field ownership, versioning, root separation, and fail-closed semantics before WP2/WP3 consume shared models.
3. **Authority freeze:** an independent reviewer checks the exact six-lane W5 universe, requirement authorship/scope review, action-risk escalation, verifier feasibility, and no-self-approval before any R2/R3 route can be marked eligible.
4. **Adapter/operations freeze:** the complete required Claude/Codex semantic matrix, unit-safe token evidence, symmetric resource conflicts, minimized receipts, and operational evidence are reviewed before live provider smoke or long-running process control.
5. **Fixture activation:** every case demonstrates known-bad failure and known-good pass; exact fixture/grader closure is checked before verdicts; a fixture defect produces quarantine, not a system pass.
6. **Retention freeze:** Stephen accepts the section 7.3 durations, roles, extension authorities, consumers, replica rule, and deletion-verification semantics before any R1/R2 fixture activates.
7. **P0 decision:** W6 emits one non-aggregated `ReleaseGateDecision`; any missing required grader, stale revision/hash, critical fail, `unable_to_grade`, or `fixture_error` blocks the affected capability.

## 6. Research assurance requirements

- **Assurance lanes touched:** Output/provenance throughout; representation, stochastic/null, topology, and paper-claim lanes only where fixtures F-010–F-014/F-022/F-035/F-036 test the control boundary.
- **Governing decisions/specifications:** D-001–D-008; P-001–P-030; accepted W1–W8 and 06c; fixture catalogue/addenda 06a/06b.
- **Machine-checkable claims:** identity/version/hash integrity, schema validity, atomicity, replay determinism, root separation, token-accounting units, routing determinism, independence evidence, parity coverage, lease/checkpoint compatibility, trace completeness, grader non-compensation, and fixture catalogue closure.
- **Human-review-only claims:** whether a scientific proof obligation, conceptual direction, claim wording, or methodological exception is adequate. P0 uses calibrated synthetic examples and cannot promote a research claim.
- **Output provenance:** every fixture run records immutable subject/config hashes, schema/policy/adapter versions, seed when applicable, exact control/code/result roots, and non-overwriting output paths.
- **Partial rule:** missing independent judgment, unavailable cross-family capability, uncalibrated oracle, or unresolved source authority returns Partial/blocked; the implementation plan cannot weaken the requirement.

## 7. Retention and deletion-verification proposal for exact-scope approval

Expiring R1/R2 payloads never enter immutable events, receipts, or the canonical object store. They live in an explicit authorized evidence root outside the repository; canonical records retain only R0 identity, hash, retention rule, consumers, expiry, and deletion-verification receipts. P0 prohibits unregistered replicas and backups of R1/R2 payloads. Gate 5 must extend verification to the registered backup/restore topology before S-014 can pass.

| Evidence type | Class | Proposed maximum window | Review lead | Owner / extension authority |
|---|---|---:|---:|---|
| Redacted command/tool summary | R1 | 180 days after evaluation-run terminal time | 30 days | system maintainer / Manager |
| Operational measurement | R1 | 365 days after linked release decision | 30 days | system maintainer / Manager |
| Grader explanation | R1 | 365 days after linked release decision | 30 days | evaluation owner / Manager |
| Restricted local reference | R2 | 90 days after evaluation-run terminal time or earlier source expiry | 14 days | data controller / Stephen or delegated data authority |
| Minimized sensitive excerpt | R2 | 30 days after evaluation-run terminal time or earlier source expiry | 7 days | data controller / Stephen or delegated data authority |

Deletion is an explicit command, not an inference from supersession or expiry. Verification must prove payload absence from the primary evidence root, runtime/staging/temp paths, and every registered replica; prove canonical records never contained the payload; rebuild projections with the evidence marked `expired_deleted`; and emit an R0 `EvidenceDeletionVerified` event plus immutable command receipt containing the evidence ID/hash, rule, actor, checked locations, timestamp, and verification status. A failed or incomplete check remains `deletion_pending`, blocks a clean release report, and forbids further R2 intake into the affected store.

### 7.1 Deletion-verification contract

The verifier receives an immutable evidence-store registry containing the store ID/hash, primary root identity, runtime/staging/temp roots, registered replicas, permitted consumers, applicable retention policy, and verifier authority. It derives the checked-location set from that registry and performs the checks itself. A caller cannot submit `*_absent = true` flags as proof.

The verification manifest records the evidence ID/hash, policy revision, registry hash, resolved checked locations, per-location result/evidence hash, inaccessible locations, canonical-object scan result, actor/authority, and verification time. Any unregistered replica, inaccessible applicable location, canonical payload match, or unresolved reparse-point/junction escape yields `deletion_pending`. Only a complete verified manifest may authorize `EvidenceDeletionVerified` through the WP1 command service.

### 7.2 Forward-obligation closure

| Governing obligation | P0 implementation owner | Exact plan disposition |
|---|---|---|
| W2 UUIDv7/owner identities and crash-after-rename receipt recovery | WP1 Tasks 1, 4, 5 | registered kind validators; event-derived accepted-command index; fault injection at object/temp/rename/tail/receipt boundaries |
| W3 mandatory closure and F-021/F-022/F-025/F-026 two-gate sizing | WP2 Task 2 and WP4 Tasks 4–5 | mandatory omissions always block; sizing matrix records reference count plus exact/evaluated provider-token evidence for every declared variant |
| W4/W5 complete lane/floor/scope authority and verifier feasibility | WP2 Tasks 1, 3–5 | exact six lanes; `asr_` identity; distinct scope-review evidence; final relationship recomputation |
| W6 exact required-grader closure and retention/deletion policy | WP4 Tasks 2–3 | required-tuple set equality; fail-on-omission mutations; authorized evidence registry/verifier |
| W6/06b repeated-run, uncertainty, and false-accept policy | WP4 Tasks 4–6 | deterministic fake/reference cases run twice for byte/decision equality; model/human capability stays blocked until a separately accepted live-grader threshold policy exists |
| W7 exact adapter fixture revisions/variants and provider-token units | WP3 Tasks 1–2 and WP4 Task 4 | `p0-variant-matrix.yaml` binds fixture revision, provider, adapter profile, rendering/accounting revision, transport, OS, and operational profile; no wildcard activation |
| W8 symmetric conflicts, stop/recovery, and registered-root evidence | WP3 Tasks 3–5 | full compatibility matrix, typed stop evidence, new resume epoch, and no inferred root/process identity |
| Gate 5 deferred S-014/S-015/S-016 | WP4 coverage/release | omitted from P0 materialization with explicit capability restriction; remain required before foundation/pilot promotion |

### 7.3 Owner decisions included in later exact-scope approval

Stephen's later approval of this exact reconciled plan accepts the retention rows above as P0 maxima, including their review-lead times, owners, extension authorities, permitted-consumer requirement, prohibition on unregistered replicas, and fail-closed deletion semantics. Until that approval is recorded, fixture activation and implementation remain unauthorized.

P0 uses deterministic fake transports only. Deterministic D/T/O/P calibration executes each known-bad, known-good, and declared mutation twice and requires byte-identical normalized decisions for identical immutable inputs, the intended known-bad failure in both runs, and the intended known-good pass in both runs. Any stochastic fixture supplies its own accepted seed/repeat/uncertainty policy; absence is `fixture_error`. Required M/H evidence has no permissive P0 sample-count default: the affected capability remains `unable_to_grade`/blocked until a separate live-grader threshold policy and bounded provider/human review authority are accepted.

## 8. Global commands and quality gates

All implementation tasks use:

```powershell
uv run ruff check research_system tools/ars tests/research_system
uv run pytest tests/research_system -q --no-cov
```

The complete P0 acceptance run additionally uses:

```powershell
uv run pytest tests/research_system/unit -q --no-cov
uv run pytest tests/research_system/integration -q --no-cov
uv run python -m research_system.cli eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run python -m research_system.cli replay verify --control-root $env:ARS_P0_CONTROL_ROOT
```

`ARS_P0_CONTROL_ROOT` must be set explicitly to Stephen's approved external control root. The value is a runtime parameter, not a repository default, and must not be inferred from the current working directory.

## 9. Commit and evidence discipline

Each child plan commits only its scoped files and uses a research-prefixed subject. Multi-line messages are written to a task-specific file such as `C:\tmp\ars-p0-wp2-task3.txt` and committed with `git commit -F`; shell here-strings are prohibited.

Every completed task records:

- failing test command and observed failure before implementation;
- passing targeted test command after implementation;
- affected fixture IDs and accepted contract sections;
- GitNexus `detect_changes(scope: staged)` result before commit;
- no-migration check confirming `.apm/`, current-paper files, results, and active control state were untouched.

## 10. Stop conditions

Stop and request direction when:

- the external control root cannot be proven outside the code repository/worktree;
- a task requires changing an accepted W1–W8/06c semantic rather than implementing it;
- exact/evaluated provider token accounting is unavailable for a route;
- a provider adapter needs credentials, broad shell/network permission, or a hidden transcript to satisfy a fixture;
- a P0 scientific fixture lacks independent oracle/reviewer evidence;
- atomic writer recovery yields a state other than zero-or-one committed batch;
- a change would import, normalize, or write active APM/current-paper state;
- the 37-case closure cannot be graded without silently adding or dropping a fixture.

## 11. Plan review gate

- [x] The four child plans map every created/modified file, shared-interface owner, and exact test command after reconciliation.
- [x] The 37-case P0 closure is correct without relabeling F-021 or synthetic scenarios.
- [x] Shared schemas and identifiers are bound to W1–W8/06c owner catalogues; unknown or conflicting catalogue entries stop schema freeze.
- [x] The control root cannot default into a code worktree and is checked against every registered worktree plus resolved reparse-point targets.
- [x] Provider adapters fail closed and tests use deterministic fake transports.
- [x] Scientific fixtures retain independent grading and human-review boundaries; missing M/H policy remains blocking.
- [ ] R1/R2 durations, owners, evidence-root boundary, and deletion verification await Stephen's exact-scope acceptance; R3 storage remains prohibited.
- [x] Each work package is independently testable and revertible across the frozen shared contracts.
- [x] P0 acceptance cannot authorize migration, a pilot, or a research claim.
- [ ] Stephen has approved this exact plan before execution.

**Outcome:** `REVIEW_RECONCILED_PENDING_APPROVAL — required review findings are incorporated; no foundation or fixture implementation is authorized until Stephen accepts the exact reconciled scope and owner decisions`.
