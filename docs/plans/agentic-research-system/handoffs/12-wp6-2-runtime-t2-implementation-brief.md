# WP6.2 Runtime T2 Implementation Brief

**Created:** 2026-07-23
**Status:** proposed dispatch brief; runtime implementation requires Stephen's
explicit authorization of this exact brief
**Workflow system:** standalone TDL supervision; never APM
**Vertical outcome:** make the accepted T2 authority/cost transition family
executable through the existing canonical `CommandService`, without resolving a
credential or invoking a provider

## 1. Controlling state

Dispatch only from a branch pre-created at the then-current accepted `main`.
The minimum certified base is PR #159 merge commit
`d390a072480d2e4c9e28fdb8f19cbd7770e6078e`.

The following accepted identities are immutable inputs:

- P-040 contract/addendum candidate
  `391a92753d7f746fa91a6b5455c9ce0fd01baa52`, tree
  `0254c5416925126412867d61b3045ee1563abd0c`;
- P-041 rate-mode boundary candidate
  `2048f6470a9542db967186cc260d235c3373de2e`, tree
  `1be775711befa047c7baa36fa485e5690b2277f1`;
- T1a accepted subject
  `599050b0809ed63a69e1a9ce6ac491b61f7ad33e`, protocol blob
  `4c9721a047c9b66912b9786a3b983c6f84e5ab00`, canonical SHA-256
  `e9512bef147d0de9bc9103b20eb1ede8b927979bfe43dd85e61fb6c27f05efda`.

Before writing, verify cwd, symbolic branch, HEAD, clean task status, and that
both accepted candidates are ancestors of the dispatch base. The effective
immutable T2 set is the P-040 27-path set minus the six paths superseded by
P-041, plus the P-041 six-path accepted tuple:

- `.research-system/contracts/wp6-2-t2-cost-grant-authority-catalogue.yaml`;
- `.research-system/contracts/wp6-2-t2-schema-identities.yaml`;
- `.research-system/schemas/wp6-2-t2/commands/authorize-provider-issue.schema.json`;
- `.research-system/schemas/wp6-2-t2/events/cost-grant-reserved.schema.json`;
- `tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py`;
- `tests/research_system/contracts/wp6_2_t2_schema_materializer.py`.

Compare every path in that effective set and the accepted T1a set directly with
its controlling accepted Git blob and raw-byte SHA-256 identity. Use P-040 for
the non-superseded paths, P-041 for the six paths above, and the T1a identity
manifest/owner acceptance for T1a. An ancestor check or comparison only with
the dispatch base is not an exact-byte proof. A normal detached Codex start
permits one deterministic switch to the pre-created branch only when detached
HEAD and that branch resolve to the same required commit.

## 2. Required operating context

Invoke `research-observer` first and use `tda-large-workflow-supervision` as the
primary coordination procedure. Use fresh implementation context because this
is a new semantic subject, then a separate fresh reviewer with no producer or
manager conversation history. Rotate only on actual compaction when continuity
degrades. Stephen alone triggers and monitors CodeRabbit.

Read only the current authorities and implementation seams needed here:

1. P-037 through P-041 in `03-decisions-and-open-questions.md`;
2. `implementation/06b-wp6-2-live-capability-plan.md`, limited to T2, its DAG,
   assurance boundary, and stop conditions;
3. `design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md`;
4. the accepted T2 catalogue, identity manifest, schemas, crosswalk, and
   contract validators;
5. `research_system.command.service.CommandService`, the ledger append path,
   receipt store, reducers, replay projections, schema registry, and their
   focused tests.

Do not replay WP6.1, T1a, or T2 contract authorship and review history.

## 3. Runtime closure

The implementation must preserve this closed family and no other mutation:

1. `IssueCostGrant -> [CostGrantIssued]`;
2. `AuthorizeProviderIssue -> [CostGrantReserved, ProviderCommandIssued]`;
3. `RecordProviderReceipt -> [ProviderReceiptRecorded, CostGrantReconciled]`.

`research_system.command.service.CommandService` remains the sole canonical
writer. Each accepted command appends its complete event set once, in the exact
order above, as one `Ledger.append` batch. Multi-stream expected versions come
from the command's ordered `write_set`; every version must match the same
materialized snapshot before append. A stale member conflicts with zero events.

Runtime routing must validate each T2 envelope against its exact T2 command
schema. Do not route it through the legacy `ars://core/command` shape: that
schema and the legacy `Command`/`Receipt` models are single-stream 1.0
interfaces. Add the smallest production representation needed for the accepted
multi-stream command and `ars://core/receipt/v2` proof surface while preserving
all existing 1.0 behaviour.

For every command:

- verify the supplied `payload_hash` against canonical payload bytes;
- enforce the accepted schema identity/version, authority scope, target,
  ordered write set, subject triples, command-specific lifecycle rule, and
  semantic relations;
- reconstruct idempotency from the exact tuple
  `(actor_id, authority_scope, command_type, idempotency_key)`;
- return the original accepted Receipt 2.0 binding on exact replay, with zero
  new events or other effects;
- return the catalogue's stable rejected/conflict outcome with zero events for
  any failed precondition or identity/version conflict;
- ensure a same-tuple different-command or different-payload submission is an
  idempotency conflict;
- produce the exact reducers and projections named by the accepted catalogue,
  including replay/rebuild behaviour from ledger events alone.

`AuthorizeProviderIssue` reserves the accepted quantity and records a
`ProviderCommandIssued` intent. It must not invoke transport. P-037 explicitly
leaves the external dispatch crash seam unresolved, so no implementation may
claim that this event proves provider invocation.

`RecordProviderReceipt` validates a caller-supplied ProviderReceipt 2.0 T2
authority/cost subset and atomically records it with reconciliation. Metered
cost uses the accepted integer ceiling arithmetic. `zero_cost_authorized`
requires zero rates and zero reserved/consumed cost with its exact authority
triple. Refund and balance arithmetic must never exceed or underflow the
accepted grant.

Lifecycle enforcement is command-specific. `IssueCostGrant` requires current
ResourceGrant and authority grants. `AuthorizeProviderIssue` requires an
unexpired, unrevoked SecretReference and CostGrant plus current external
grants. `RecordProviderReceipt` must reconcile a previously accepted
reservation even when its grant or SecretReference later expired or was
revoked; those later lifecycle changes must not strand accepted cost actuals.

## 4. Bounded production surface

The implementer may change only the smallest subset of these paths:

- `research_system/command/service.py`;
- `research_system/command/models.py`;
- `research_system/command/reducers.py`;
- one new T2-specific module under `research_system/command/` if separation
  materially reduces risk;
- `research_system/store/ledger.py`, limited to T2-specific zero-based
  `transaction_index` allocation (`0..transaction_count-1`) and selection and
  validation of the accepted T2 event schema identities; legacy events must
  retain their existing one-based indices (`1..transaction_count`) and
  core-event validation;
- `research_system/store/receipts.py`;
- `research_system/projection/replay.py`;
- `tests/research_system/factories.py`;
- one focused new runtime test module under `tests/research_system/unit/`;
- existing directly affected command, receipt, reducer, projection, or schema
  registry unit tests.

`research_system/schema_registry.py` already discovers all bundled schemas and
is not an expected write. Do not edit any accepted file under
`.research-system/contracts/wp6-2-t2-*`,
`.research-system/schemas/wp6-2-t2/`, `receipt-v2.schema.json`, the T2 addendum,
P-040/P-041 acceptance records, or their contract tests. If runtime correctness
appears to require such an edit, stop for owner authority.

Target no more than 15 changed paths. Any expansion needs a concrete
research-value justification and manager approval before writing.

## 5. Machine acceptance

Add literal, implementation-independent runtime tests covering:

- all three positive commands and exact event order/count/stream versions;
- atomic two-stream append failure with no partial publication;
- cost-grant issuance only at version zero;
- exact replay versus idempotency conflict;
- stale version and two-command over-reservation arbitration with exactly one
  accepted reservation;
- missing, wrong-type, exhausted, expired, revoked, identity-mismatched, and
  insufficient grants at issuance/authorization where the catalogue requires
  them;
- successful receipt recording and reconciliation after later grant or
  SecretReference expiry/revocation;
- subject-triple, authority-scope, schema alias/version, write-set, target,
  payload-hash, and rate-evidence mismatches;
- metered positive-cost and `zero_cost_authorized` zero-cost paths;
- receipt actual-token/cost/refund arithmetic, duplicate receipt rejection, and
  reconciliation bounds;
- Receipt 2.0 event proof and stored/reconstructed equality;
- reducer/projection replay from a fresh process state;
- literal zero-based T2 event indices and exact T2 event-schema selection, plus
  unchanged one-based legacy indices and legacy core-event validation;
- unchanged legacy command/Receipt 1.0 behaviour;
- zero provider invocations. Use a counting fail-if-called seam; do not add a
  provider adapter or resolver.

Validation is deliberately proportional:

```powershell
python -m pytest -q tests/research_system/unit/test_wp6_2_t2_runtime.py
python -m pytest -q tests/research_system/unit/test_command_service.py tests/research_system/unit/test_schema_registry.py
python -m pytest -q tests/research_system/contracts/test_wp6_2_t2_authority_contract.py tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py -k "rate_mode or zero_cost or metered"
git diff --check
```

If the implementer chooses a different focused test filename, substitute that
one exact path. Do not run the package-wide 135-test T2 contract suite merely
because it exists. Expand validation only when a changed shared seam or a
specific failure supplies a concrete reason, and record that reason.

Before handback, repeat the direct accepted Git-blob and raw-byte SHA-256
comparison for the effective immutable set defined in section 1: non-superseded
P-040 paths, the P-041 six-path tuple, and T1a. A no-diff result against the
dispatch base is insufficient. Recount `origin/main...candidate`; the
changed-path set must stay within the authorized surface and below the 15-path
target.

## 6. Assurance and research-value boundary

Primary lanes are Output and Provenance. This action protects the research
system from unbudgeted provider work, ambiguous provider-command provenance,
double reservation, and incorrect receipt/cost reconciliation. It produces no
research result and supports no statistical, model-quality, parity, eligibility,
or publication claim.

Strict opaque SecretReference metadata and its exact binding are in scope.
Credential resolution, secret scanning/sentinels across actual adapter
surfaces, invocation canaries against real transports, and complete W7 runtime
qualification belong to T3/T4. General security hardening is not part of this
vertical action.

## 7. Explicit non-goals and stops

Do not implement or perform:

- credential resolution, provider process/session creation, network or local
  provider calls, an outbox, retrying transport, or transport success claims;
- T3, T4, T1b-M, T1b-H, T5-T8, M/H eligibility, Gate 6 transition, result,
  claim, publication, descriptor build, or P1 observation;
- a second writer, a fourth command, automatic retry after concurrency
  conflict, or mutation/regeneration of accepted bytes;
- broad refactoring, generalized accounting infrastructure, or unrelated
  hardening.

Stop on any need to change an accepted contract/schema/test byte, invent
transport atomicity, weaken an accepted rejection, exceed the authorized path
surface, or continue after a fresh review returns `rework_required` following
one bounded remediation cycle.

## 8. Delivery and review

Commit with the repository convention:

```text
[PIPELINE] P00: implement WP6.2 runtime T2 boundary
```

Return one compact exact-state handback containing branch/root, base and
candidate commits, exact changed paths, validation commands and counts,
accepted-byte immutability proof, unresolved risks, and a ready-to-paste fresh
review prompt. Push only the pre-created implementation branch; do not open or
merge a PR unless Stephen instructs it.

The fresh independent reviewer examines only the implementation delta and its
direct contract/runtime evidence. One bounded producer remediation is allowed
for still-valid findings, followed by one fresh review of changed elements
only. A second `rework_required` verdict stops for Stephen. Passing tests and an
accepting review make a proposed runtime candidate only; Stephen's exact
acceptance and merge remain separate.

After merged, independently passing runtime T2, separate T3 and T4 provider
transports become dependency-eligible, subject to separate explicit owner
authority. Nothing in this brief starts or authorizes either.
