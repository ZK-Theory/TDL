# PR #198 Independent Pre-Merge Review — Exact Subject `c7ace86`

## Overall verdict

**`rework_required_before_merge`**

The exact PR subject is stable and mechanically clean, and several prior review
findings are now closed. Five semantic blockers remain: one Critical authority
bypass and four Major lifecycle/integration defects. Resolved inline threads,
passing focused checks, and GitHub mergeability do not change this verdict.

This is a pre-merge verdict only. It is not G-RM-3 redispatch closure, owner
acceptance, implementation authority, or dispatch authority.

## Exact subject and provenance

| Item | Required | Independently observed | Result |
|---|---|---|---|
| Base branch | `main` | `origin/main` | match |
| Base SHA | `9ed1fa034efd262061e820b48a58924d63ca3f3c` | same | match |
| Head branch | `codex/rm-lane-rereview-remediation` | `origin/codex/rm-lane-rereview-remediation` | match |
| Head SHA | `c7ace86ca097c831930a54f1dd6e99b7c341cddf` | same | match |
| Merge base | `9ed1fa034efd262061e820b48a58924d63ca3f3c` | same | match |
| Commit count | 2 | 2 | match |
| Changed paths | 11 | 11 | match |
| PR state | open, non-draft, clean merge state | open, non-draft, `MERGEABLE` / `CLEAN` | match |
| Review worktree | fresh isolated checkout | detached, clean tracked state at exact head | pass |

Expected and observed commits, in order:

1. `9be7f0ed0ab717b782076a2d6da823e298f09dc2`
2. `c7ace86ca097c831930a54f1dd6e99b7c341cddf`

The review used the fresh detached worktree
`C:\Users\steph\.codex\worktrees\pr198-c7ace86-review\TDL`, created with
`core.autocrlf=false` and `core.longpaths=true`. The exact-subject drift hard
stop did not fire.

### Changed-path blob identities

| Path | Head blob |
|---|---|
| `implementation/06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md` | `8d93c11f2cf0c8f989f9c3a0bab44046a779e1ce` |
| `implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md` | `7768fa2f6c884c1a22ba74a15770f200dc58c692` |
| `implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md` | `71ad8339c1410104900cb966a2b557300677786a` |
| `implementation/README.md` | `5f73abef4e9e40564b2ca90700de8efabddf09d6` |
| `implementation/rm-00-research-methods-lane-master-plan.md` | `425a8aba34a2447b31572d667c659de5a1401da0` |
| `implementation/rm-01-unblock-and-suite-recovery-plan.md` | `b8571b41322f4ad4f90d0e58d934d6abe77fd071` |
| `implementation/rm-02-research-methods-pack-plan.md` | `35eea6b44fb5a84c9d43cdc4bb0bb3d9d518ac08` |
| `implementation/rm-03-brief-export-import-plan.md` | `9722b03f894bb3021153debbd91d453c677c1418` |
| `implementation/rm-04-manuscript-review-and-verification-records-plan.md` | `42c7b32746030fc90cecb31050dcf9959c2bd204` |
| `reviews/adversarial-rm-lane-plan-suite-rereview-2026-07-30.md` | `915a7b11f9b95af05e9fb8684f9a0061aac62434` |
| `reviews/rm-lane-rereview-response-2026-07-30.md` | `e2393061546f288b0a8be42dbb987be1f59d2ef8` |

All paths above are relative to
`docs/plans/agentic-research-system/`. All 11 changed files were read in full.
Claims were checked against the exact-head runtime and the accepted W2/W3 and
decision-register text, not against the remediation response.

## Findings

### PR198-F1 — Critical — The proposed firewall still leaves the existing production result consumer outside authority resolution

**Exact locations**

- `docs/plans/agentic-research-system/implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md:131-146`
- `research_system/evals/release_publication.py:155-176`
- `research_system/cli.py:338-404`
- `research_system/cli.py:522-565`
- governing requirement:
  `docs/plans/agentic-research-system/design/02-task-event-and-artifact-schema.md:693-706`

**Precise claim**

06i promises that every result, review, manuscript, claim, and sensitive
sidecar consumer uses one replay-derived `ArtefactUseResolver`. Its concrete
call-site table, however, names only new RM-03 `brief.py` calls, and its
structural direct-read check is limited to `research_system/methods/**`,
`research_system/evidence/**`, and the new CLI handlers. The exact-head
production result-publication path is neither named nor in the file map.

**Current-code and governing evidence**

`StoredReleasePublicationEvidence._resolve` directly calls
`ObjectStore.read("artefact", reference, 1)` and checks content identity, but
does not check replay-derived use authority, the accepted consumer predicate,
consumer kind/scope, governing review set, or P-005 state. The production
`eval publish-release` and `eval release` CLI paths construct and use that
resolver. W2 section 16.2 requires the consumer policy predicate over all six
independent dimensions; schema/content validity is not enough.

**Failure scenario and impact**

A structurally valid artefact can remain `candidate`, be accepted for a
different scope, or carry stale/superseded use authority while the result
publication consumer resolves it directly by content ID. The release path can
therefore consume evidence without the policy decision 06i claims is mandatory.
This preserves RR-C2's reachable authority failure: candidate or wrong-scope
material can feed canonical result evidence while the proposed RM-only boundary
tests remain green.

**Minimal required correction**

Add every existing production artefact consumer to the 06i file map and
call-site matrix, beginning with `StoredReleasePublicationEvidence` and both
release CLI paths, and route result evidence through `resolve_for_result`.
Make direct-read discovery repository-wide over the complete first-party call
graph, with an explicit closed allowlist for storage/internal reads that are
provably not consumption decisions. A new module outside the three named roots
must not be able to become a canonical consumer without failing the boundary
test.

### PR198-F2 — Major — 06j omits accepted W3 requested/compiling states and their failure path

**Exact locations**

- `docs/plans/agentic-research-system/implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:24-36`
- `docs/plans/agentic-research-system/implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:79-91`
- `docs/plans/agentic-research-system/implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:100-111`
- governing lifecycle:
  `docs/plans/agentic-research-system/design/03-context-memory-and-retrieval.md:358-368`

**Precise claim**

06j calls its seven-command family W3-complete, but begins with
`RegisterContextPacket -> ContextPacketRegistered (compiled)` and defines only
`registered -> validated -> issued -> delivered`, with failure from
`registered|validated`. Accepted W3 begins at
`requested -> compiling -> compiled` and permits failure from
`requested/compiling/compiled`.

**Current-code and governing evidence**

The planned compiler performs source resolution, freshness/security/conflict
checks, rendering, both token gates, object writes, and only then submits
`RegisterContextPacket`. Any mandatory-source, conflict, security, token, or
independence failure before registration therefore has no command-written
requested/compiling/failed lifecycle record. W3 expressly defines those states
and says lifecycle events are W2 extensions.

**Failure scenario and impact**

A requested packet fails during source resolution or a token gate. Replay sees
no request, compiling state, or failed terminal state, so an operator cannot
distinguish “never requested” from “requested and failed,” correlate the
failure to its request, or prove deterministic failure/retry behavior. RM-03
then depends on a lifecycle that is incomplete relative to its accepted
authority.

**Minimal required correction**

Materialize the accepted requested/compiling/compiled/failed path with
command/event/reducer/receipt and replay controls, or obtain an explicit owner
amendment to W3 before G-RM-12. Add pre-registration failure, idempotent retry,
genesis replay, and incremental replay controls. Do not treat
`registered (compiled)` as silently superseding accepted lifecycle states.

### PR198-F3 — Major — RM-01/06i/06j leave one valid merge ordering permanently outside the smoke gate

**Exact locations**

- `docs/plans/agentic-research-system/implementation/rm-00-research-methods-lane-master-plan.md:45-56`
- `docs/plans/agentic-research-system/implementation/rm-01-unblock-and-suite-recovery-plan.md:121-135`
- `docs/plans/agentic-research-system/implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md:199-205`
- `docs/plans/agentic-research-system/implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:151-158`

**Precise claim**

RM-01 covers only families present at its exact dispatch head. A successor adds
its families only if the smoke gate already exists at successor close-out;
otherwise it publishes cases as blocking RM-01 input. No plan rechecks the
successor set at RM-01 close-out or owns a final three-branch reconciliation.

**Failure scenario and impact**

RM-01 dispatches before 06i lands, so it freezes a head without 06i. 06i then
lands and closes before RM-01 merges; because the smoke test does not yet exist,
06i publishes cases to RM-01. RM-01 remains scoped to its older dispatch head
and is not required to consume a successor that landed after dispatch. When
RM-01 later merges, 06i is already closed, so no plan extends the gate. The same
ordering applies to 06j. A new command/event family is permanently absent from
the live P-043 smoke control despite every local close-out following its plan.

**Minimal required correction**

Name one final reconciliation owner. Either make accepted 06i/06j prerequisites
of RM-01, or require RM-01 at final candidate head to consume every successor
case published before its merge and require any later successor to modify and
run the installed smoke gate. Add a merge-order matrix covering all relative
orders of RM-01, 06i, and 06j; every terminal ordering must have one owner and a
test proving all landed production families are present.

### PR198-F4 — Major — G-RM-10 and G-RM-12 require exact subjects that their blocked implementations are supposed to create

**Exact locations**

- `docs/plans/agentic-research-system/implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md:39-68`
- `docs/plans/agentic-research-system/implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md:152-157`
- `docs/plans/agentic-research-system/implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:18-32`
- `docs/plans/agentic-research-system/implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:38-53`
- `docs/plans/agentic-research-system/implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md:126-130`

**Precise claim**

Before 06i dispatch, G-RM-10 requires Stephen to pin Git blobs and canonical
hashes for the consumer-policy registry and public interface specification.
Those files are listed as new 06i outputs, and 06i Task 1 defines the registry.
Before 06j implementation, G-RM-12 requires approval of exact schemas, but 06j
Task 1 and its create list materialize those schemas. Neither plan provides an
authorized pre-gate candidate-authoring stage.

**Failure scenario and impact**

The owner cannot inspect or hash the required decision subject before dispatch,
but the Worker cannot create that subject because dispatch is blocked on the
owner decision. The gate is then either impossible to close honestly or is
closed against plan prose while later Worker-authored bytes inherit an
acceptance they never received. That defeats independent policy/schema
acceptance and makes catalogue completeness self-attested.

**Minimal required correction**

Split each contract/schema subject into a bounded candidate-authoring
predecessor that grants no runtime implementation authority. Independently
review the exact candidate bytes, then have Stephen bind their blobs/hashes at
G-RM-10/G-RM-12, and only then dispatch implementation against those fixed
subjects. Alternatively, move exact candidate artefacts into the current PR
and review them now. Preserve both gates as hard stops.

### PR198-F5 — Major — RM-04's candidate-only verification run cannot traverse its required follow-up consumer

**Exact locations**

- `docs/plans/agentic-research-system/implementation/rm-04-manuscript-review-and-verification-records-plan.md:16-25`
- `docs/plans/agentic-research-system/implementation/rm-04-manuscript-review-and-verification-records-plan.md:27-39`
- `docs/plans/agentic-research-system/implementation/rm-04-manuscript-review-and-verification-records-plan.md:89-98`
- `docs/plans/agentic-research-system/implementation/rm-04-manuscript-review-and-verification-records-plan.md:121-130`
- `docs/plans/agentic-research-system/implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md:123-129`

**Precise claim**

RM-04 registers every `OperatorVerificationRun` at forced candidate state,
forbids RM-04 from producing a use-authority transition or scientific-review
verdict, and then requires the follow-up export to resolve that run through
06i's review/manuscript consumer. 06i expressly fails closed on candidate
artefacts.

**Failure scenario and impact**

The planned positive round trip reaches
`candidate -> request -> operator run -> follow-up export`. The run is still
candidate, so `resolve_for_review` or `resolve_for_manuscript` rejects it.
There is no intervening review-set/owner gate analogous to G-RM-4 for the run.
Task 3 cannot reach its own happy path without weakening the candidate firewall
or inventing an unplanned authority transition.

**Minimal required correction**

Insert an explicit external 06i review/use-authority step between import of the
operator-reported run and follow-up export, with a named acceptor, exact
review-only/manuscript scope, independent review evidence, and negative controls
showing that candidate/result/claim use remains blocked. If the intended
feedback display must show candidate evidence, define and owner-approve a
separate visibly non-authoritative audit-display policy; do not reuse a
canonical manuscript/result consumer.

## Prior RR closure matrix

| Prior finding | Current disposition | Evidence |
|---|---|---|
| RR-C1 — artefact authority semantics | **Partially closed** | 06i now specifies forced-candidate registration, grant/scope/effectivity checks, the six-dimensional predicate, review-set evidence, P-005 binding, catalogue controls, and atomic negatives. G-RM-10 cannot yet bind the Worker-created policy/interface subject (PR198-F4), so independently accepted policy authority is not closed. |
| RR-C2 — production consumer firewall | **Open** | Five method names exist, but the current production result consumer remains a direct object read outside the file map and structural boundary (PR198-F1). |
| RR-M1 — T2 excluded | **Closed** | 06h Task 0 inventories producers; Task 2 explicitly covers `research_system/command/t2.py`, its separate validation, `_event_envelope`, and append path (`06h:124-172`). |
| RR-M2 — G-RM-8 branch protocols | **Closed at plan level; owner gate open** | 06h supplies bounded migrate/grandfather/no-store inventories, admission rules, repeat/replay behavior, stops, and distinguishing negatives (`06h:98-109`). Stephen still selects one at G-RM-8. |
| RR-M3 — two post-06h baselines | **Closed** | 06h Task 0 freezes pre-change nodes/cohort before production mutation; RM-01 reads that record and labels no later collection “pre-06h” (`06h:124-142`; `RM-01:75-109`). |
| RR-M4 — no reachable W3 packet authority | **Partially closed** | 06j adds producer, command family, replay, delivery, resolver, and CLI reachability, but omits accepted requested/compiling failure states and has a circular G-RM-12 subject (PR198-F2/F4). |
| RR-M5 — self-attested methods history | **Closed at plan level** | RM-02 receives base/subject from the acceptance runner, verifies ancestry and prior blob/absence, retains the prior prefix, and includes a coordinated current-file rewrite negative (`RM-02:17-48,149-188`). |
| RR-M6 — CLI/call-graph capability boundary | **Closed** | RM-03 names `brief_export`/`brief_import` and their complete transitive first-party graph; RM-04 extends the same exact handler graph and forbids broad `research_system.*` allowance (`RM-03:57-85,165-184`; `RM-04:27-34`). |
| RR-m1 — stale `pyproject.toml` lines | **Closed** | RM-01 binds semantic keys, not line numbers (`RM-01:111-119`). |
| RR-m2 — wrong README | **Closed** | RM-01 names `implementation/README.md` (`RM-01:137-148`). |
| RR-m3 — obsolete/overstated verification record | **Closed** | `OperatorVerificationRun` is consistently operator-self-attested and expressly certifies neither ARS execution, scientific validity, acceptance, nor claim authority (`RM-04:16-25,75-87`). |

## Resolved inline-comment disposition

| Thread | Current disposition |
|---|---|
| 06j did not expose `FailContextPacket` / `ExpireContextPacket` through CLI | **Semantically closed for the stated comment.** Task 5 exposes all seven lifecycle operations and Task 6 requires successful `fail`/`expire`, invalid-state, and idempotent-retry coverage (`06j:136-142`); close-out records all-seven reachability (`06j:151-154`). PR198-F2 is a separate accepted-W3 lifecycle omission. |
| RM-01 dependency contradicted 06i/06j smoke scope | **Not semantically closed.** The current text fixes the immediate dispatch-head contradiction, but the successor-lands-before-RM-01-merge ordering leaves a permanent family gap (PR198-F3). Thread resolution is not closure. |

## Gate and hard-stop audit

- **G-RM-3:** explicit, open, and blocking. This report does not close it.
- **G-RM-8:** explicit hard stop. The three protocols are inspectable; Stephen's
  choice remains open.
- **G-RM-9:** explicit hard stop. `RegisteredSchema` acceptance remains Stephen's
  decision after exact-subject evidence.
- **G-RM-10:** explicit hard stop, but not executable in the current lifecycle
  because its exact policy/interface subject is created by the blocked plan
  (PR198-F4).
- **G-RM-12:** explicit hard stop, but not executable against exact schema bytes
  until the candidate-authoring lifecycle is separated (PR198-F4).
- **G-RM-11:** correctly fail-closed. No plan executes externally proposed code.
- **G-RM-4/G-RM-5/G-RM-6/G-RM-7:** remain later owner actions with their stated
  scopes. None can cure the findings above by approval alone.

No plan is dispatchable from this review. Passing document checks, accepted
direction under P-043/P-044, or GitHub mergeability is not semantic or owner
acceptance.

## Validation commands and results

1. Fetched exact remote refs:

   `git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main +refs/heads/codex/rm-lane-rereview-remediation:refs/remotes/origin/codex/rm-lane-rereview-remediation`

   Result: base, head, and merge base matched the review packet.

2. Enumerated commits and paths:

   `git rev-list --reverse <base>..<head>`

   `git diff --name-only <base> <head>`

   Result: exactly the two expected commits and 11 changed paths.

3. Queried GitHub PR metadata and review threads read-only.

   Result: PR open, non-draft, `MERGEABLE`, `CLEAN`; two resolved threads and
   zero unresolved threads; head/base matched the Git fetch.

4. Verified exact object identities:

   `git ls-tree c7ace86... -- <each changed path>`

   Result: the 11 blobs listed above.

5. Checked patch and document mechanics:

   `git diff --check 9ed1fa0... c7ace86...`

   Result: pass.

   A read-only Markdown link resolver checked every inline relative link in all
   11 changed files.

   Result: `MISSING_LINKS=0`.

   Byte checks found no UTF-8 BOM and no CRLF bytes in any changed file.

6. Ran the exact focused catalogue/materialization slice with cache and coverage
   plugins disabled:

   `C:\Users\steph\TDL\.venv\Scripts\python.exe -B -m pytest -q`
   plus the three exact nodes in
   `test_wp6_1_generated_schema_materialization.py`, with
   `-o "addopts=" -p no:cacheprovider -p no:cov`.

   Result: `3 passed in 16.78s`.

   These checks establish catalogue/schema materialization closure only; they do
   not establish runtime authority or plan acceptance.

7. Final review-worktree tracked status:

   `git status --short`

   Result: clean.

No broad test suite was run because the PR changes plans/review records only and
the remaining findings are direct lifecycle/authority contradictions.

## Remaining risks and required next action

The remaining risk is concentrated at authority and merge seams: a direct
result consumer can bypass replay-derived use authority; accepted W3 lifecycle
states can disappear before registration; locally correct successor close-outs
can compose into an incomplete smoke gate; owner gates can be satisfied only
against not-yet-created subjects; and an operator-reported candidate cannot
reach its planned follow-up consumer.

Minimal next action: revise only the five mechanisms above, preserve all owner
hard stops, and request a fresh exact-subject pre-merge review. Do not merge,
dispatch, treat G-RM-3 as closed, or infer owner acceptance from this report.
