# RM-04: Manuscript Review Lane and Verification Records Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. The governing idea:
> the external model *proposes*; a human *verifies*; ARS *records*. A passing
> verification is **evidence about a candidate**, never acceptance of a result
> (W5 two-key). Keep that asymmetry visible in every interface name.
> **ARS executes nothing in this plan.** If a task finds itself running
> returned content, stop Partial — that is G-RM-11 territory.

**Status:** REVISED 2026-07-29 (revision 2). Renamed from
`rm-04-verification-execution-and-manuscript-review-plan.md`, which the
adversarial review returned `reject` on for a Critical (C-4): it executed
model-proposed Python with the project interpreter beside a gitignored `.env`
and the vault, without isolation, egress control, or non-self-attested
approval. **All execution is removed.** Dispatch blocked on **G-RM-3** and on
**RM-03 merged**. The pilot additionally requires **G-RM-5**.
**Goal:** (1) The manuscript-review lane: a draft section exported with the
adversarial-review asset, its `ReviewFindingSet` bound to the draft's exact
hash, landing as a `candidate` artefact. (2) Verification *records*: a
`VerificationRequest` capturing a proposed recipe, and an
`OperatorVerificationRun` capturing an outcome the **operator** produced and
attests to. (3) Round-trip support so a follow-up brief can carry a prior
outcome including its traceback. (4) One owner-chosen manuscript pilot.
**Owner authorization:** P-044 (accepted 2026-07-28; G-RM-3 and plan-specific
dependencies remain open); G-RM-5 for the pilot.

## What changed in revision 2, and why

| Revision 1 | Revision 2 | Driver |
|---|---|---|
| `ars brief verify` executed model-proposed Python via subprocess | **Removed.** No runner, no `verify` command, no execution anywhere | **C-4**: `cwd` and a wall-time timeout are not a security boundary. A returned recipe could read `.env`, walk the vault, open a socket, write to the repository, or spawn a child outliving the timeout |
| `approved_for_execution_by` / `--approved-by` free string | Gone with execution. The operator-run record carries an **actor ID resolved by ARS**, not a typed name | **C-4**: any caller could type Stephen's name |
| "W8 spirit (bounded resources)" | W8 is either satisfied properly or not invoked. This plan invokes no resource, so it claims nothing | **C-4**: W8 requires typed roots, grants, leases, process identity and stop evidence — "spirit" was a downgrade |
| The counterexample pilot ran a recipe | Pilot is manuscript-review only | **C-4**; the counterexample lane returns with RM-05 |
| `verification_context` embedded a complete result in a closed schema | A versioned reference object, specified in RM-03 | **M-8** |
| Assurance lane: Output/Provenance | Output/Provenance **and Paper Claim governance** | **M-12** |
| `P-044 (pending)`; "Full gates" | Accepted status; exact command set | **m-1**, **m-3** |

## The honest position on verification

The source paper's neuro-symbolic loop is: the model proposes a check, the
check runs, the traceback feeds back. ARS can hold three of those four steps.
It cannot safely run the check, so it does not pretend to.

What this plan records instead:

- **`VerificationRequest`** — a proposed recipe, content-addressed and bound to
  the candidate it came from. Recording it is not approving it.
- **`OperatorVerificationRun`** — an outcome the operator produced **on their
  own responsibility, outside ARS**, with the environment they used described
  and the exact script hash bound. This is **self-attested evidence** and the
  schema description says so in those words. It is weaker than an ARS-executed
  result would be, and the weakness is recorded rather than hidden.
- The feedback loop still closes: `--attach-result` places the reference-only
  `verification_context` in the manifest, resolves and hash-checks that
  artefact, and renders its outcome and traceback into the follow-up brief,
  with the operator as relay — exactly the P-042 posture the rest of the lane
  already assumes.

Only after G-RM-11 independently accepts an implemented isolation substrate and
its exact-subject evidence may RM-05 add an ARS-executed result type that does
**not** carry the self-attestation caveat. Funding or implementation alone is
insufficient. Until readiness acceptance, no interface in this lane implies
ARS ran anything.

## Global constraints

- All standing constraints of rm-00 §5 apply. Branch
  `pipe/rm-04-manuscript-and-verification-records`. Copy `.env` into the
  worktree.
- **No execution, no subprocess, no runner.** RM-03's capability boundary
  (Task 5 there) extends over every file this plan creates **and over the new
  brief command handlers and their call graph in `research_system/cli.py`**.
  Its CLI AST check rejects dynamic import, sockets, `eval`/`exec`, process
  launch, and every other prohibited execution primitive from those handlers.
  The only module-level subprocess allowance is the pre-existing fixed-argv Git
  root discovery in `_registered_code_roots`; the guard identifies that
  function and exact operation structurally, and any additional subprocess use
  in `cli.py` fails. Negative fixtures must prove each CLI prohibition fires.
- No W5 lifecycle transition is performed by any code here: no review verdict,
  no result acceptance, no claim object, no `SetArtefactUseAuthority`. The
  manuscript lane *feeds* W5 review by producing bound evidence; a human takes
  it from there.
- Imported records land as `candidate` artefacts via the accepted
  `RegisterArtefact` command, exactly as in RM-03. No new event family.
- An `OperatorVerificationRun` never mutates the candidate it concerns; it is a
  new artefact referencing it (append-only, O-RM-16).

## File map

**Create:**

~~~text
.research-system/schemas/methods/verification-request.schema.json      # ars://methods/verification-request
.research-system/schemas/methods/operator-verification-run.schema.json # ars://methods/import/OperatorVerificationRun
research_system/methods/verification_records.py
tests/research_system/unit/test_verification_records.py
tests/research_system/integration/test_verification_round_trip.py
docs/plans/agentic-research-system/implementation/rm-04a-manuscript-pilot-record-<date>.md
~~~

**Modify:**

~~~text
research_system/cli.py                     # `brief export --attach-result`
research_system/methods/brief.py           # populate the verification_context reference
~~~

Note the module is `verification_records.py`, not `verification.py`: the name
states that it records rather than performs. Keep it.

## Interface specifications

- **`VerificationRequest`** — `{request_artefact_id (art_ UUIDv7),
  candidate_artefact_id, script_sha256, script_source (opaque text, bounded
  length), proposed_by: const "external_session", recorded_at}`.
  **No interpreter field, no wall-time field, no approver field** — ARS is not
  going to run it, so declaring how it would be run would be theatre.
- **`OperatorVerificationRun`** — `{run_artefact_id, request_artefact_id,
  candidate_artefact_id, script_sha256, outcome: enum passed|failed|error|timeout,
  exit_code (nullable), stdout_excerpt, stderr_excerpt (bounded), traceback
  (nullable), environment_description (free text supplied by the operator),
  executed_by_actor_id, executed_on, attestation: const "operator_self_attested"}`.
  The schema description states in words: *`passed` means the operator reports
  the script exited 0 in an environment ARS did not observe; semantic meaning
  belongs to the human reading it* (O-RM-5, R4-2). `script_sha256` must match
  the referenced `VerificationRequest` or the import is rejected.
- **`ars brief export --attach-result <run_artefact_id>`** — embeds
  `verification_context` per RM-03's specified reference object
  `{schema_id, schema_version, verification_result_id, content_hash}` (M-8).
  No schema version bump, because RM-03 specified the field rather than
  reserving it open.
- **Manuscript lane needs no new code.** It is RM-03's exporter with asset 1
  and a draft file as subject. This plan's contribution is the pilot proving it
  end to end plus the documented recipe in the pilot record.

## Obligation register

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| R4-1 | Paper §2.6 | Propose → capture traceback → feed back | `VerificationRequest` + `OperatorVerificationRun` + `--attach-result`, with the operator as relay |
| R4-2 | W5 §17 / O-RM-5 | Execution success is not acceptance | `outcome` semantics stated in the schema; `attestation` const; no lifecycle code; review question |
| R4-3 | P-042 / O-RM-1 | No network/provider in the lane | RM-03 capability boundary extends over new files |
| R4-4 | **Review C-4 / O-RM-19** | ARS must not execute externally-proposed code without an isolation substrate | **Satisfied by not executing.** Execution deferred to RM-05 under G-RM-11 |
| R4-5 | O-RM-16 / W2 | Records append-only, bound by artefact IDs and hashes | `RegisterArtefact`; replay test |
| R4-6 | G-RM-5 | Stephen picks the pilot subject | Task 4 gate |
| R4-7 | Vault discipline | Pilot outcome recorded; `[PIPELINE]` entry; daily note for the pilot story | Close-out |
| R4-8 | Honesty rule (no security theater) | Self-attested evidence is labelled as such, and no interface implies ARS observed the run | `attestation` const; schema descriptions; docstring requirement |
| R4-9 | M-8 | RM-03 and RM-04 must agree exactly on shared schema identities | Shared schema-equality contract test (Task 1) |
| R4-10 | M-12 / O-RM-22 | Paper Claim governance applies | Assurance section |

## Research assurance requirements

- **Lanes:** Output/Provenance **and Paper Claim governance** (M-12). The
  manuscript lane carries external review findings toward a draft, which is
  where wording-strength and human-authority controls matter most.
  Verification records certify **nothing about scientific validity** — they
  inherit no scientific lane from the candidate they reference, and the review
  question below exists to keep that true.
- **Machine-checkable claims:** an `OperatorVerificationRun` whose
  `script_sha256` differs from its `VerificationRequest` is rejected; a run
  referencing an unknown request is rejected; `--attach-result` round-trips the
  outcome and traceback byte-identically; replay reproduces the projection;
  imported runs land `candidate` and cannot be consumed as evidence (RM-03's
  firewall test extended); **no module or new CLI handler in this plan imports
  or invokes `subprocess` or any execution primitive** (capability-boundary
  guard, with only the pre-existing fixed Git-discovery exception above).
- **Human-review-only:** does the pilot brief plus findings read as a coherent
  evidence chain to someone who was not in the session? Does any interface name
  or description imply ARS verified something it did not?
- **Partial criteria:** any need for W5 lifecycle writes; any execution
  primitive appearing anywhere; any sandboxing or "verified by ARS" claim
  creeping into docs or schema descriptions; the recipe format proving too weak
  for the pilot (report — do not improvise a DSL).

## Tasks

- [ ] **Task 1 — Schemas + shared-contract test.** Author the two schemas.
      Add the **shared RM-03/RM-04 schema-equality test** (R4-9, M-8):
      equality-check the artefact ID conventions, the `$id`s, and the
      `verification_context` object shape against RM-03's definitions, so the
      two plans cannot drift.
      Commit: `[PIPELINE] P00: verification record schema family`.
- [ ] **Task 2 — Record handling.** Implement `verification_records.py`:
      validate and register a `VerificationRequest` and an
      `OperatorVerificationRun` as `candidate` artefacts. Negative controls
      (each red first): script-hash mismatch against the request; unknown
      request reference; unknown candidate reference; an `attestation` value
      other than the const; a payload carrying an execution-implying field.
      Commit: `[PIPELINE] P00: verification request and operator-run records`.
- [ ] **Task 3 — Round trip.** `--attach-result` in the exporter; integration
      test: import a candidate → import a failing operator run → export a
      follow-up brief → assert the manifest's reference-only
      `verification_context` resolves to that exact artefact and passes its
      schema/hash checks, then assert the traceback rendered into the brief is
      byte-identical to the resolved imported record.
      Commit: `[PIPELINE] P00: verification round-trip into follow-up briefs`.
- [ ] **Task 4 — Manuscript pilot (owner-gated, G-RM-5).** With Stephen's
      chosen subject: export a draft section with asset 1, the operator runs
      the session, import the `ReviewFindingSet` bound to the draft's exact
      hash, hand the findings to the normal human review path. Write
      `rm-04a-manuscript-pilot-record-<date>.md` with a **redacted command
      inventory** (tool/operation, sanitized argument shape, timestamp, status,
      and command hash), artefact IDs, friction observations, and an explicit
      statement of what was *not* done — no acceptance, no claim, no promotion,
      no execution. Never commit an unredacted transcript: exclude stdout,
      stderr, credentials, tokens, raw returned content, sensitive paths, and
      any other restricted data.
      Commit: `[PIPELINE] P00: manuscript-review lane pilot record`.

## Deferred to RM-05 (G-RM-11)

Not dropped — owner and gate named, per rm-00 §6:

- ARS-executed verification with an OS-enforced isolation profile: disposable
  interpreter, sanitized environment with no inherited credentials,
  deny-by-default network egress, read-only exact input mounts plus one
  disposable writable scratch mount, and no repository, `.env`, vault or home
  visibility.
- W8 `ResourceGrant`, `ExecutionLease`, `ProcessIdentity`, child-process and
  stop-confirmation records.
- An attributed approval command resolving canonical actor and authority and
  binding the exact request and script hash.
- Escape negative controls: absolute-path read, `.env` access, network egress,
  repository write, environment leak, child survival past timeout, forged
  approver identity, timeout cleanup.
- The counterexample-verification pilot, which needs the above to be safe.

A threat model is written and reviewed **before** RM-05 is planned, not as part
of it.

## Close-out

- Exact verification commands (m-3):

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/unit/test_verification_records.py tests/research_system/integration/test_verification_round_trip.py tests/research_system/unit/test_methods_capability_boundary.py tests/research_system/integration/test_claim_consumer_firewall.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system
~~~

  Full-tree validation triggers only if `cli.py` changes beyond adding the
  `--attach-result` flag.
- PR; CodeRabbit concludes; merge per house rule.
- README lane row; vault `[PIPELINE]` entry in Pipeline-Overview; daily note
  capturing pilot friction — that friction is the evidence base for deciding
  whether the lane earns further investment, and specifically for whether
  G-RM-11 is worth funding.
