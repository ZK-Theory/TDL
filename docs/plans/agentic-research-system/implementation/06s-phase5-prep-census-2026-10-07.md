# 06s Phase 5 prep: C0 public-CLI census (KAN-110)

**Capability status:** INCOMPLETE. The historical real SPEC run is PROVEN; the complete public Gate 6
implementation is not integrated on main.

**Date:** 2026-10-07. This is the census that design decision P5-11 requires before any construction PR is cut
(P-058, "Phase 5 prep design decisions"). Its result fixes the construction PR list.
**Subject:** the code at `b0cda615`, which `3559251f` leaves unchanged apart from documentation. It ran from the
non-linked scratch clone `C:/Users/steph/TDL-p5-rehearsal/clone`, with the foundation re-pinned in the clone to
a scratch store.
**Driver:** disposable and uncommitted (`c0_census.py`, in this session's scratchpad). Every command's JSON and
the run log are in `C:/Users/steph/TDL-p5-rehearsal/census-census-control-4/`. The live store, providers and
credentials were not touched.

## What the census asked

The public SPEC-01 path test drives every SPEC action through the genuine CLI. Four kinds of step go through
test adapters instead:

| Seam | Test adapter |
|---|---|
| The store binding | `_bound_fixture`: a hand-written restore and binding chain |
| Grant activation | `activate_lifecycle_grant`: it writes the owner's administration decision into the object store, then submits through an internal authority service |
| Task and Attempt seeding | `GovernedTestCommandService`, which auto-provisions grants |
| Attempt completion and evidence registration | the same seeding service |

The binding seam is B-2, already measured in the design pass. The census asked whether the other three can be
done through the public CLI.

## Method

Each run creates its own scratch store through the procedure decided in P5-1, with the reserve step stood in
by stopping init at its `after-identity` failpoint:
1. reserve;
2. re-pin the clone's foundation;
3. run the genuine `store init`.

The existing seeding helpers then run against a stand-in harness. Its `service.submit` and
`authority_service.submit` send every command through `research_system.cli.main(["command", "submit",
"--config", …, "--host-identity", …, "--boot-identity", …])`, imported from the clone. The foundation seam is
therefore genuine.

`ars command submit` loads a `ControlBinding` through the full foundation. It does not need a store binding,
so B-2 does not block it.

Labelled bypasses, each of which is either outside the census question or the finding itself:
- **Clock.** `cli._authority_clock` is pinned to the C1 fixture time, because the fixture commands carry fixed
  timestamps. Time semantics were not under census. Live commands carry current times.
- **Decision placement.** The owner's administration decision is written into the control object store with
  `ObjectStore.write`, exactly as the test helper does. This is finding B-3.
- **Grant scope.** The grant each lifecycle command needs is computed with
  `CommandService._lifecycle_authority_inputs`, as the governed test adapter does. This is a read-only
  planning step, which the live runbook replaces with the grant table.

## Result

On the final run (store `census-control-4`), **22 of 22 commands were accepted through the public
`ars command submit`**, with no refusal:

| Commands | Count |
|---|---|
| `ActivateAuthorityGrant`, the owner using the root grant, for the resource, Task, dispatch, lease, Attempt and two evidence artefacts | 7 |
| `CreateTask`, `RequestReadiness`, `ApproveReadiness` | 3 |
| `IssueDispatch`, `RecordDispatchDelivery`, `AcknowledgeDispatch` | 3 |
| `RequestResourceGrant`, `ClaimExecutionLease`, `ClaimDispatch` | 3 |
| `CreateAttempt`, `ClaimAttempt`, `StartAttempt`, `CompleteAttempt` | 4 |
| `RegisterArtefact` (the two evidence artefacts the Task's Attempt names) | 2 |

So Task and Attempt seeding, Attempt completion, evidence registration and grant activation all have a public
path. The trusted runtime authority comes from `--host-identity` and `--boot-identity`.

Earlier runs on stores 1–3 stopped on driver defects, not on refusals. The stand-in first returned the wrong
receipt type, and then lacked the runtime-authority accessor that the resource builder reads. Each such store
was abandoned, and a new store made for the next run.

## Findings

**B-3 (Material, not blocking): the owner's grant-activation decision has no public writer.**
- `ActivateAuthorityGrant` admission verifies an owner administration decision.
  `LedgerAuthorityGrantResolver._load_owner_administration_decision` (`authority.py:2080-2115`) loads it from
  the control store's `objects/assurance_record`.
- No `ars` command writes that object. The only writers are internal: the test helper
  (`tests/research_system/factories.py:393`) and `evals/executors/release_tranche.py:280`.
- `ars assurance-record write` writes external assurance records under a grant, so it cannot bootstrap the first
  grant.
- The live run needs about 25–35 grant activations: one per actor, command and subject.
- **Workaround:** the owner places each decision with the same internal `ObjectStore.write` call. Admission
  verifies its schema and hash, so a wrong decision is refused. But the live procedure would then depend on an
  internal API at every grant.
- **Recommendation:** one CLI command, `ars authority activate-grant --config <binding> --grant <grant.json>`.
  It derives the owner decision from the store's administration context and the supplied grant, writes it, and
  submits `ActivateAuthorityGrant` as the owner under the root grant. Admission is unchanged. It is a CLI
  wrapper over the existing object kind and command, not a STORE change. It ships as its own small certified
  PR, with controls: a non-owner caller and a tampered grant are refused, and the decision bytes are re-derived
  on retry.

No other seam failed. The census found no further gap of the B-1 or B-2 kind.

## The construction PR list (fixed by this census)

| PR | Content | Note |
|---|---|---|
| PR-A | `ars store reserve` (B-1) and the first binding of an initialized store (B-2), with a committed slow test that runs the genuine CLI from a non-linked scratch clone, from reservation to `spec status`, with no foundation, binding, grant or seeding fixture | D5 exceptions granted (P5-1, P5-3) |
| PR-B | M-2 SOURCE provenance (P5-7) | Route |
| PR-C | The Assay bar: SPEC-01 content, fixture relocation, SPEC-01's rule in W11 admission (P5-8), the signer and the actor plan (P5-9) | D5 exception granted (P5-8) |
| PR-D | `adopt_default` (P5-10) | Route |
| PR-G | `ars authority activate-grant` (B-3) | New from this census |
| Docs | The runbook: the grant table, Task seeding by `ars command submit`, the m-4 note and the §4 sequence | |
| PR-F | The foundation re-pin, after the live reservation (design pass §4) | Configuration |

PR-E ("anything the census adds") is PR-G. The committed test in PR-A will also exercise PR-G once both have
merged, so the live sequence's grant and seeding steps have an unpatched test as well.
