# RM-04: Verification Execution and Manuscript Review Lane Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. The governing idea:
> the external model *proposes*; ARS *executes and records*; a passing
> execution is **evidence about a candidate**, never acceptance of a result
> (W5 two-key). Keep that asymmetry visible in every interface name.

**Status:** PROPOSED — dispatch blocked on G-RM-2, G-RM-3, and RM-03 merged.
The pilot task additionally requires G-RM-5 (Stephen chooses subjects).
**Goal:** (1) `ars brief verify`: execute a model-proposed verification recipe
attached to an imported candidate, under wall-time and root discipline, and
bind a typed `VerificationResult` to that candidate. (2) Round-trip support:
a follow-up brief can carry the prior result including the traceback — the
paper's automated-feedback step with the operator as relay. (3) The
manuscript-review lane: a draft section exported with the adversarial-review
asset and its `ReviewFindingSet` bound to the draft's exact hash. (4) One
owner-chosen pilot of each lane.
**Architecture:** `VerificationRequest` is derived from an imported
`CounterexampleCandidate.verification_recipe` (or supplied standalone against
another import type), stored content-addressed, then executed by a subprocess
runner: fixed interpreter, cwd inside a declared scratch root, wall-time flag
mandatory, stdout/stderr/exit code/traceback captured, environment
fingerprint (interpreter path, platform, package-list hash) recorded. The
result event binds `{candidate content id, script sha256, env fingerprint}`.
Execution is *not* a sandbox-security claim — the runner's constraints are
provenance and bounding, and the plan says so honestly; scripts are reviewed
by the operator before `verify` is invoked (an explicit CLI confirmation
records who approved execution).
**Tech stack:** Python 3.13, subprocess with timeout, existing object
store/ledger seams, pytest, ruff.
**Owner authorization:** P-044 (pending); G-RM-5 for pilots.

## Global constraints

- All standing constraints of rm-00 §5 apply. Branch
  `pipe/rm-04-verification-lane`.
- P-042 boundary unchanged: the runner executes *local scripts only*; the
  Task-5 guard from RM-03 stays green (network/provider usage inside
  `research_system/methods/` remains banned — a verification recipe needing
  network data is out of scope and fails with a typed error, not a warning).
- A `VerificationResult` never mutates the candidate it verifies; it is a new
  record referencing it (append-only, O-RM-16).
- No W5 lifecycle transition is performed by any code in this plan: no review
  verdict, no result acceptance, no claim object. The manuscript lane *feeds*
  W5 review by producing bound evidence; a human takes it from there.
- Long recipes: respect the parallel-compute working rule only if a recipe is
  itself long stochastic compute — default posture is that recipes are small
  checks; a recipe exceeding the wall-time flag fails with `timeout` recorded.

## File map

**Create:**

~~~text
.research-system/schemas/methods/verification-request.schema.json    # ars://methods/verification/VerificationRequest
.research-system/schemas/methods/verification-result.schema.json     # ars://methods/verification/VerificationResult
.research-system/schemas/methods/verification-executed.schema.json   # ars://methods/event/VerificationExecuted
research_system/methods/verification.py
tests/research_system/unit/test_verification_runner.py
tests/research_system/integration/test_verification_round_trip.py
docs/plans/agentic-research-system/implementation/rm-04a-pilot-record-<date>.md
~~~

**Modify:**

~~~text
research_system/cli.py                     # `brief verify`; export gains --attach-result
research_system/methods/brief.py           # populate the reserved verification_context field
~~~

## Interface specifications

- `VerificationRequest`: `{request_id, candidate_content_id, script_sha256,
  script_source (inline, bounded length), interpreter: const "project-venv",
  wall_time_seconds (required, max 600), scratch_root, approved_for_execution_by}`.
- `VerificationResult`: `{request_id, candidate_content_id, script_sha256,
  outcome: enum passed|failed|error|timeout, exit_code, stdout_sha256,
  stderr_sha256, stdout_excerpt, stderr_excerpt (bounded), traceback
  (nullable), env_fingerprint, duration_seconds}`. Note `passed` means *the
  script exited 0*, and the schema description says exactly that — semantic
  meaning belongs to the human reading it (O-RM-5).
- `ars brief verify --candidate <content-id> [--recipe <file>] --wall-time <s> --approved-by <operator>`:
  resolves recipe from the candidate or the flag; refuses if both present and
  hashes differ; stores request; executes; stores result blobs and emits
  `VerificationExecuted`.
- Round trip: `ars brief export --attach-result <request_id>` embeds the
  result (including traceback) in the bundle's `verification_context` (schema
  field reserved by RM-03 — no schema version bump).
- Manuscript lane needs **no new code**: it is RM-03's exporter with asset 1
  and a draft file as subject. This plan's contribution is the pilot proving
  it plus a documented recipe in the pilot record.

## Obligation register

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| R4-1 | Paper §2.6 / analysis Track 2 | Execute → capture traceback → feed back | verify command + `--attach-result` |
| R4-2 | W5 §17 / O-RM-5 | Execution success is not acceptance | `passed` semantics note; no lifecycle code; review question |
| R4-3 | P-042 / O-RM-1 | No network/provider in the lane | RM-03 guard extends over new files; typed error for network-needing recipes |
| R4-4 | W8 spirit (bounded resources) | Mandatory wall time, declared scratch root, recorded approver | Request schema required fields |
| R4-5 | O-RM-16 | Results append-only, bound by content ids + hashes | Result/event schemas; replay test |
| R4-6 | G-RM-5 | Stephen picks pilot subjects | Task 4 gate |
| R4-7 | Vault discipline | Pilot outcomes recorded; `[PIPELINE]` entry; daily note for the pilot story | Close-out |
| R4-8 | Honesty rule (no security theater) | Runner constraints documented as provenance/bounding, not sandboxing | Architecture note; docstring requirement |

## Research assurance requirements

- **Lanes:** Output/Provenance. **Machine-checkable:** result binds the exact
  script hash executed (test recomputes); timeout path produces `timeout`
  outcome with partial output captured (test with a sleeping script); a
  tampered recipe (hash mismatch vs candidate) refuses to run; replay
  reproduces the projection; `--attach-result` round-trips byte-identical
  result content.
- **Human-review-only:** does the pilot brief + result read as a coherent
  evidence chain to someone who wasn't in the session?
- **Partial criteria:** any need for W5 lifecycle writes; any sandboxing claim
  creeping into docs; recipe format proving too weak for the pilot candidate
  (report, don't improvise a DSL).

## Tasks

- [ ] **Task 1 — Schemas + failing runner test.** Author the three schemas;
  red test: run a trivial recipe (`print("ok")`) against a fixture candidate →
  result `passed`, hashes bound, event emitted.
  Commit: `[PIPELINE] P00: verification request/result schema family`.
- [ ] **Task 2 — Runner + CLI.** Implement `verification.py` and
  `brief verify`; green Task 1; add timeout, error, tamper, and refusal tests
  (each red first).
  Commit: `[PIPELINE] P00: bounded verification runner (ars brief verify)`.
- [ ] **Task 3 — Round trip.** `--attach-result` in exporter; integration
  test: import candidate → verify (failing script) → export follow-up brief →
  assert traceback present in `verification_context`.
  Commit: `[PIPELINE] P00: verification round-trip into follow-up briefs`.
- [ ] **Task 4 — Pilots (owner-gated, G-RM-5).** With Stephen's chosen
  subjects: (a) counterexample lane — export brief with asset 2, operator runs
  the session, import candidate, verify recipe, record; (b) manuscript lane —
  export a draft section with asset 1, import the `ReviewFindingSet`, hand the
  findings to the normal human review path. Write
  `rm-04a-pilot-record-<date>.md`: full command transcript, artifact ids,
  friction observations, and explicit statement of what was *not* done (no
  acceptance, no claim).
  Commit: `[PIPELINE] P00: RM lane pilot record`.

## Close-out

- Full gates; PR; CodeRabbit; merge per house rule.
- README lane row; vault `[PIPELINE]` entry; daily note capturing pilot
  friction (this is the evidence base for deciding whether the lane earns
  further investment — rm-00 §6 deferrals point here).
