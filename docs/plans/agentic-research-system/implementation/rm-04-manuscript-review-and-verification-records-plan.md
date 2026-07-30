# RM-04: Manuscript Review Lane and Verification Records Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. External sessions may
> propose; operators may report; ARS records. ARS executes nothing here. Read
> PR198-F5 from the PR #198 pre-merge review before starting.

**Status:** REVISED 2026-07-30 (suite revision 4). Dispatch is blocked on G-RM-3,
merged RM-03, and the accepted 06i/06j interfaces RM-03 binds. The pilot is
separately blocked on G-RM-5; any follow-up export of an
`OperatorVerificationRun` is blocked on G-RM-13 for that exact run and scope.

**Goal:** record verification requests and operator-reported runs as candidate
artefacts, render an exact prior run into a follow-up brief, and pilot a
manuscript-review flow without execution, result acceptance, promotion or
claim mutation. Review/manuscript use authority is external, exact-scope and
does not convert the operator report into execution truth.

## Honest verification boundary

- `VerificationRequest` records opaque proposed script text/hash.
- `OperatorVerificationRun` records what an attributed operator reports
  happened outside ARS. `passed` is not ARS execution evidence, scientific
  validity, result acceptance or claim authority.
- A run remains forced `candidate` until an eligible unrelated reviewer records
  an independent scientific review through 06i and Stephen accepts the exact
  run/hash for a named `review_evidence` or `manuscript_evidence` scope at
  G-RM-13. That use-authority event accepts only bounded consumption of an
  operator-reported trace; it does not certify execution or scientific truth.
- Follow-up export resolves the exact run through the corresponding 06i port
  and binds it to the 06j packet before rendering traceback bytes.
- G-RM-11 is the only route to future ARS execution.

## Global constraints

- No execution, subprocess, runner, network, dynamic import, credentials or
  provider operation.
- RM-03's capability boundary covers every new methods module, the exact
  `brief_export` handler with `--attach-result`, and their complete transitive
  graph. The only subprocess exception remains the pre-existing exact
  `_registered_code_roots` Git discovery operation.
- All records register via 06i at forced candidate state.
- Every canonical read uses a 06i production consumer; no direct object read,
  local status or projection is authority.
- RM-04 code produces no `SetArtefactUseAuthority`, scientific review verdict,
  result acceptance, claim object or P-005 decision. The operator/human workflow
  invokes accepted 06i review and authority commands outside the RM-04 writer,
  with Stephen as the G-RM-13 acceptor.

## File map

**Create:**

~~~text
.research-system/schemas/methods/verification-request.schema.json
.research-system/schemas/methods/operator-verification-run.schema.json
research_system/methods/verification_records.py
tests/research_system/unit/test_verification_records.py
tests/research_system/integration/test_verification_round_trip.py
docs/plans/agentic-research-system/implementation/rm-04-manuscript-pilot-record-<date>.md
~~~

**Modify:**

~~~text
.research-system/schemas/methods/brief-manifest.schema.json
research_system/cli.py
research_system/methods/brief.py
tests/research_system/unit/test_methods_capability_boundary.py
tests/research_system/integration/test_methods_production_consumers.py
~~~

## Interfaces

`VerificationRequest`:

~~~text
request_artefact_id, candidate_artefact_id, script_sha256,
script_source, proposed_by: external_session, recorded_at
~~~

No interpreter, timeout or approver field: ARS will not run it.

`OperatorVerificationRun`:

~~~text
run_artefact_id, request_artefact_id, candidate_artefact_id,
script_sha256, outcome: passed|failed|error|timeout,
exit_code, stdout_excerpt, stderr_excerpt, traceback,
environment_description, executed_by_actor_id, executed_on,
attestation: operator_self_attested
~~~

The schema description states: `passed` means the operator reports exit zero in
an environment ARS did not observe. The record certifies neither ARS execution
nor acceptance. `script_sha256` must equal the request's exact value.

`ars brief export --attach-result <run_artefact_id>` uses RM-03's closed
reference:

~~~text
{schema_id, schema_version, operator_verification_run_id, content_hash}
~~~

It resolves only after G-RM-13 through the 06i production consumer at the exact
accepted review/manuscript scope, requires the matching 06j packet
purpose/scope, and renders the resolved outcome/traceback. The reference object
never embeds open result data. The default traceback-feedback flow uses
`review_evidence`; manuscript display requires a separate explicitly named
G-RM-13 scope.

## Obligations

| ID | Obligation | Enforcement |
|---|---|---|
| R4-1 | propose -> operator run -> traceback feedback | request/run/attach-result |
| R4-2 | operational/schema success is not scientific/authority acceptance | explicit semantics and candidate authority |
| R4-3 | no provider/network/process | complete RM-03 capability graph |
| R4-4 | no untrusted execution | absence; G-RM-11 deferral |
| R4-5 | immutable/replayable records | 06i registration/replay |
| R4-6 | Stephen chooses pilot | G-RM-5 |
| R4-7 | durable pilot/vault record | close-out |
| R4-8 | self-attestation labelled | const and review question |
| R4-9 | RM-03/04 schema/reference equality | shared contract test |
| R4-10 | Paper Claim governance | assurance + no promotion |
| R4-11 | candidate run cannot traverse follow-up consumer | independent 06i review + Stephen's exact G-RM-13 use-authority event |

## Tasks

1. **Schemas/shared contract.** Create the two closed record schemas and extend
   RM-03's closed brief schema from `verification_context: null` to the exact
   shared `OperatorVerificationRun` reference. Equality-check IDs, `art_` UUIDv7
   conventions and the reference shape across the two plans.
2. **Record writer.** Validate request/run and register each through 06i.
   Reject wrong script/request/candidate, wrong attestation, execution-implying
   fields and caller-selected accepted state.
3. **Round trip.** Import candidate -> request -> operator run at forced
   candidate -> eligible unrelated `RecordScientificReview` -> Stephen's
   G-RM-13 `SetArtefactUseAuthority` for exact run/hash and review/manuscript
   scope -> follow-up export. Resolve through 06i, packet through 06j, verify
   exact hash/schema and byte-identical traceback rendering. Missing, stale,
   wrong-review, wrong-scope or superseded authority fails.
4. **Consumer/capability controls.** Candidate cannot satisfy review,
   manuscript, result or claim consumption. Accepted review-scoped evidence can
   feed only `resolve_for_review`; result/claim and unaccepted manuscript use
   remain blocked. A separately accepted manuscript scope cannot imply result
   or claim use. Plant execution/network/dynamic-import evasion in methods,
   exact CLI handler and transitive fixture; every plant fails.
5. **Manuscript pilot (G-RM-5).** Export Stephen's exact draft subject with the
   adversarial-review asset, run the external session manually, import the
   finding set, and hand it to normal human review. Record sanitized command
   inventory and exact artefact IDs/hashes. State explicitly: no acceptance,
   claim, promotion, provider invocation by ARS, or execution.

## Deferred to RM-05

Threat model first; then OS-enforced disposable interpreter, sanitized
environment, deny-by-default egress, read-only exact inputs, isolated scratch,
no repository/home/`.env`/vault access, W8 grants/leases/process/stop evidence,
canonical exact-script approval, and escape/cleanup negatives. Until G-RM-11
accepts those exact bytes/evidence, RM-05 remains unwritten.

## Assurance and close-out

- **Lanes:** Output/Provenance and Paper Claim governance.
- **Partial:** any execution primitive; direct object consumption; need for a
  runtime-written authority transition inside RM-04; changed 06i/06j interface;
  claim that G-RM-13 certifies execution/truth; claim that ARS observed the run.

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/unit/test_verification_records.py tests/research_system/integration/test_verification_round_trip.py tests/research_system/unit/test_methods_capability_boundary.py tests/research_system/integration/test_methods_production_consumers.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system
~~~

Run broader tests only if shared CLI/consumer changes trigger the RM-03 final
suite. Update `implementation/README.md`, Pipeline-Overview and the pilot record
with exact subjects, hashes, reviewer evidence, G-RM-13 event/receipt, consumer
purpose, and explicit non-actions.
