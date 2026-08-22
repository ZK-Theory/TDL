# 06l — WP6.7 Legacy Consolidation Sequencing

**Date:** 2026-08-01
**Status:** sequencing document; no transition, migration, cutover, deprecation, retirement, or dispatch is authorised
**Authority:** P-026/P-034, the accepted WP6 plan, P-042, and the exact current Git/Jira evidence recorded below
**Jira homes:** KAN-60 (aggregate WP6.7 closure), KAN-22–26 (Gate-6-to-7 consistency), KAN-21 (later-gate planning sweep), KAN-61 (hard-stop control), KAN-12 (completion campaign)

> **Current Gate 6 reset (2026-08-22):** Every Gate 6 definition, preflight,
> dispatch, Jira, and closure instruction in this document is historical and
> non-operative. Active Gate 6 work is governed only by
> [06q — Gate 6 Recovery and Closure Plan](06q-gate6-spec-real-run-integration-and-follow-up.md).
> The historical real SPEC run is PROVEN, but no Gate 6 implementation is
> integrated on `main`; SCALE-01 is not a Gate 6 closure prerequisite. This
> document governs only the separate WP6.7/Gate 7 sequencing boundary.

## 1. Decision boundary

WP6.7 is a gated sequencing lane, not a migration ticket. It defines the
evidence and owner decisions required before a later actor may perform a
per-item transition, path cutover, deprecation, or retirement. It does not
perform any of those actions.

**Historical, non-operative Gate 6 definition:** this document used
**dispatchable, governed preflight** to mean that the then-current Gate-6
package had passed its exact review and owner gates and a controlled pilot was
eligible to be dispatched. That definition is retained only as WP6.7/Gate 7
provenance; it must not be used for current Gate 6 dispatch or closure. The
active definition and closure sequence are in 06q. Under P-042, provider
automation remains outside the first-release critical path: an authorised
operator starts an external Claude or Codex session, ARS never reads
credentials or invokes the provider, and the operator-mediated evidence path
is separately verified.

The active paper/APM surfaces remain under their current legacy authority until
their independent prerequisites close. They are not retired, migrated, or cut
over by this document.

## 2. Exact current state

### 2.1 Git and T1.28 evidence

The authoring subject was verified before writing:

| Item | Exact value |
|---|---|
| Worktree | Developer-local absolute path intentionally omitted |
| Branch | `codex/wp67-legacy-consolidation-sequencing` |
| HEAD/base | `a464eb5aefed2645da48e4495efa61a27f0e3954` |
| Parent | `12054be9186710048ea1ea9ec7f0e950850a0613` and merge parent `f0f372550c877505e7a202e45a08279e9670477c` |
| Ancestry | Required base is an ancestor of HEAD; the worktree was initially detached and was attached exactly once after the branch ref resolved to the same base |
| Initial status | Clean |

T1.28 is complete as a terminal research task, but that fact is not evidence
for any migration or successor-authority claim. The exact current-tree proof is:

- PR #72 merge `703101de6a9ebbdeb7aa56620b87f61dcbe43ce1` is an ancestor of
  HEAD;
- `results/panel_methodology/fdr/stratified_w2_recompute_2026-07-09.json`
  resolves to Git blob
  `b1a9dd8510bcfe16cce4c521ca90016dad3d3deb` (10,485 bytes);
- `results/panel_methodology/fdr/stratified_w2_bh_per_family_2026-07-09.json`
  resolves to Git blob
  `a09de18d9b1719f4732cee3c854dc10f660ff8e8` (9,444 bytes);
- the terminal result was reviewed and merged under the recorded PR path; its
  headline is USoc 12/12 subgroup rejections and BHPS 9/11, with the two
  smallest non-rejecting BHPS strata retained as the pre-registered
  underpowered cases.

This closes the T1.28 computation only. It does not close W0, A-001, the full
Stage-2 scope, Gate 6, Gate 7, or any legacy transition.

### 2.2 Open state that must not be collapsed into T1.28

The dated W0 manifest and 2026-06-29 addendum are historical/current-state
records, not a post-terminal seal. The following remain open and require fresh
evidence or a later owner decision:

1. a dated post-terminal W0 currency addendum and bounded independent delta
   review, which is Gate 7's first intake deliverable rather than a prerequisite
   to authoring, reviewing, accepting, or opening Gate 7;
2. A-001: the current Manager's explicit confirmation that no other Phase-1
   computational or assurance requirement remains;
3. A-002/full Stage-2 disposition: every Plan-defined Stage-2 item, including
   the T2.22 completion gate, must be completed, deferred, removed, or
   superseded by an attributed scope decision; eight merged Wave-1 prose tasks
   do not establish full Stage-2 completion. A-001/A-002 and the full Stage-2
   decision are conditions for an affected ownership transition, cutover,
   deprecation, or retirement, not for W9/Gate-7 document authoring or Gate-7
   opening;
4. the commissioned W9/Gate-7 authoring, independent review, reconciliation,
   and exact-revision acceptance, which may proceed now under the owner-approved
   authoring brief;
5. Gate-6 pilot-promotion evidence and Stephen's separate decision opening
   Gate 7; and
6. accepted W11 evidence and the first content-addressed ownership-transition
   batch.

### 2.3 Live Jira state used

Read-only Jira queries against `https://nexusstephen.atlassian.net` were made
on 2026-08-01. The observed states are:

| Issue | Live state | Sequencing meaning |
|---|---|---|
| KAN-22 | In Progress | Gate-6-to-7 consistency parent remains open |
| KAN-23 | To Do | Hold-language/source-authority reconciliation remains open |
| KAN-24 | To Do | T1.28-DONE versus post-terminal W0 state remains to be recorded |
| KAN-25 | To Do | Gate-7 first-deliverable precondition remains open |
| KAN-26 | To Do | Preparation/transition/cutover/retirement matrix remains open |
| KAN-21 | To Do | Later Gate-7/8/9 planning validation sweep remains open and blocks KAN-60 |
| KAN-60 | To Do | Aggregate WP6.7 closure remains open; it authorises no legacy mutation |
| KAN-61 | To Do | No-live-governance hard-stop remains open and blocks KAN-12 |
| KAN-12 | In Progress | Completion campaign remains open; later Gate-7–9 work is not WP6 merely because it is open |

The Jira statuses are coordination projections, not proof of gate closure.
Exact Git evidence, independent review, and owner decisions control the
transitions below.

## 3. Classification of work

| Class | Included work | Current rule |
|---|---|---|
| Completed | T1.28 terminal result and its exact merge/blob evidence | Record as completed research evidence only; do not use it as W0, Gate-6, Gate-7, migration, or retirement evidence |
| W9/Gate-7 document lane | Authoring, independent review, reconciliation, and Stephen's exact-revision acceptance of the W9 specification and Gate-7 definition | The owner-approved authoring brief commissions this work now; it does not open Gate 7, dispatch work, or alter legacy authority |
| Gate-7 opening/dispatch bar | Accepted W9/Gate-7 documents, Gate-6 pilot-promotion evidence, and Stephen's separate Gate-7 opening decision | No Gate-7 dispatch or legacy transition until this distinct bar closes; W0 is the first intake deliverable after opening, not an opening prerequisite |
| Gate-7 intake and affected-transition conditions | W0 post-terminal addendum/delta, A-001/A-002/full Stage-2 disposition, W11/runtime acceptance, and an attributed first transition batch | A-001/A-002/full Stage-2 scope bind the affected ownership transition, cutover, deprecation, or retirement; preparation may remain read-only |
| Out of scope | Provider invocation/credential automation, current-paper migration, silent import, dual-running, research execution, eligibility changes, claim promotion, and retirement of active APM surfaces | No WP6.7 document or Jira status permits these actions |

The deferred WP6.2 provider automation, including direct Claude/Codex transport,
live-grader activation, and provider-profile eligibility work, remains outside
the first-release critical path under P-042. Its historical contracts and
fixtures are preserved; they are not a reason to invoke a provider or to
reopen the first-release Gate-6 path.

## 4. Non-negotiable authority and path rules

The legacy and successor lanes exchange dated evidence and decisions only. They
do not share mutable state or canonical ownership.

- T1.28, its results, logs, checkpoints, contracts, and decisions remain
  `legacy_owned`; the successor may reference their exact identities only.
- The current paper roots, including `papers/P01-A-JRSSA/` and
  `papers/P01-B-JRSSB/`, remain APM/legacy-owned. No ARS writer may edit them,
  normalize their history, or promote their draft status.
- `.apm/` task, bus, tracker, log, result, and compatibility state remains
  legacy-owned unless a later accepted W9 contract names a specific read-only
  projection. Import is content-addressed observation, not copying into
  successor authority.
- `00-Meta/Discovery/_backlog.md` remains exclusively legacy-written until an
  explicit whole-path cutover after every item on that path transitions.
- Successor-generated Discovery views use the registered ARS namespace
  `00-Meta/ARS/Discovery/`. No legacy tool or human workflow writes there.
- Human annotations enter through the separate registered
  `00-Meta/ARS/Discovery-annotations/` inbox and become authority only through
  a typed ingestion command. Any combined view is a third registered,
  read-only path and is never an input to either authority.
- A path/writer registry is mandatory. A path has one authoritative writer at a
  time; no dual-authority overlap, shadow writer, shared mutable compatibility
  file, or implicit fallback writer is permitted.

## 5. Sequencing contract

The following is the only bounded transition sequence defined by this document.
Each row names the responsible Jira home, required inputs, output, review and
owner decision, rollback/stop rule, and proof required before the next class of
action.

### Step 0 — Author, review, and accept the W9/Gate-7 documents

**Jira home:** KAN-25 and KAN-60; KAN-21 remains the later planning-validation
blocker.
**Inputs:** the owner-approved W9/Gate-7 authoring brief; the W9 specification
and Gate-7 definition to be drafted; P-026/P-034 boundary text; the W11 entry
conditions; and the current legacy-authority boundaries.
**Output:** an accepted W9/Gate-7 contract that defines read-only,
content-addressed legacy projections; status mapping; path/writer registry;
per-item transition events; rollback and stop criteria; review points; and a
deprecation path that cannot retire a writer before durable cutover.
**Review/decision:** distinct adversarial review and reconciliation, followed
by Stephen's exact-revision acceptance. This acceptance concerns the documents;
it is not the separate decision opening Gate 7.
**Stop/rollback:** stop if W9 imports legacy records into successor authority,
permits a shared mutable path, treats Gate-6 eligibility as execution, or
omits rollback/collision/writer-revocation evidence. A rejected W9 revision is
discarded; no legacy path changes.
**Proof before Step 1:** accepted W9/Gate-7 documents only. Their authoring,
review, and acceptance neither require a W0 addendum nor open or dispatch Gate 7.

### Step 1 — Open Gate 7 only after the separate opening bar

**Jira home:** KAN-22–26 and KAN-25, aggregated by KAN-60; KAN-61 is the
parallel no-live-governance control.
**Inputs:** accepted W9/Gate-7 documents; exact Gate-6 pilot-promotion evidence;
the accepted WP6 plan and P-042; current Jira state; and Stephen's separate
opening decision.
**Output:** a recorded Gate-7 opening decision. It authorises only the bounded
Gate-7 intake/dispatch stated in that decision; it does not migrate, cut over,
or retire a legacy surface.
**Review/decision:** distinct exact-subject review and reconciliation of the
pilot-promotion evidence, followed by Stephen's separate Gate-7 opening
decision; no author self-acceptance.
**Stop/rollback:** stop on stale or missing pilot-promotion evidence, missing
separate owner decision, unresolved KAN-22–26 contradiction, provider/credential
path, or a claim that a plan or Jira status is runtime evidence. A proposed
opening may be returned for correction without touching legacy evidence.
**Proof before Step 2:** accepted W9/Gate-7 documents, exact Gate-6
pilot-promotion evidence, and the separate recorded Stephen decision opening
Gate 7. W0 is not a prerequisite to this proof.

### Step 2 — Produce the post-terminal W0 addendum and delta review

**Jira home:** KAN-24, with KAN-23 for source/hold reconciliation and KAN-25
for the Gate-7 entry condition.
**Inputs:** T1.28 merge/blob identities above; the W0 manifest and 2026-06-29
addendum; current APM/Tracker/Plan/task-log inventory; the current paper and
Discovery boundary.
**Output:** a dated W0 addendum that records T1.28 as terminal `DONE`, preserves
the June snapshots, identifies every post-terminal divergence, and records a
bounded independent delta verdict.
**Review/decision:** an independent reviewer checks exact identities and the
delta set; Stephen accepts or rejects the addendum revision.
**Stop/rollback:** stop if the result blobs, ancestry, current task log, or
source precedence disagree; do not rewrite the W0 snapshots or repair the
legacy record from the successor lane.
**Proof before Step 3:** accepted dated addendum, exact T1.28 evidence, and a
closed bounded delta review. This is Gate 7's first intake deliverable and a
closeout record, not a migration event or an opening prerequisite.

### Step 3 — Resolve A-001 and the full Stage-2 scope for affected ownership work

**Jira home:** KAN-24 for A-001/A-002 state; KAN-60 for aggregate closure.
**Inputs:** accepted W0 addendum; the full APM Plan; all Stage-2 task logs and
commits; the eight merged Wave-1 outputs; the fourteen currently unlogged or
unresolved Plan items, including T2.22; paper dashboards and supersession
records; and the affected proposed ownership-transition, cutover, deprecation,
or retirement scope.
**Output:** an attributed Phase-1/Stage-2 disposition manifest. Each item is
`authoritative`, `merged_draft`, `blocked`, `deferred`, `superseded`, or
`unverified`, with source pointer, exact identity, owner, and next decision.
The Manager explicitly confirms or rejects A-001; Stephen decides any scope
supersession or removal.
**Review/decision:** independent completeness review against the full Plan,
then explicit owner acceptance. Wave-1 prose success, Tracker labels, or Jira
`Done` cannot substitute.
**Stop/rollback:** stop if any Stage-2 item lacks a disposition, a task is
quietly upgraded from draft to final, or a paper claim is changed. Retain
unresolved records in legacy authority and amend only through an attributed
decision.
**Proof before an affected Step 5 transition, Step 6 cutover, or Step 7 retirement:** for each affected ownership transition, cutover,
deprecation, or retirement, an accepted manifest, explicit A-001 confirmation,
and full Stage-2 scope decision; no claim that T1.28 alone sealed Phase 1.

### Step 4 — Prepare, but do not execute, the first transition inventory

**Jira home:** KAN-60 aggregate; KAN-21 must complete the later Gate-7/8/9
planning validation sweep; per-item work remains under the named KAN-12
child/home selected by the owner.
**Inputs:** accepted W9; the separate Gate-7 opening decision and its
pilot-promotion evidence; accepted W11 specification/runtime chain; current
Discovery inventory; current P01-A/P01-B and APM surface inventory; path/writer
registry; the exact D-G6-4 first-batch relation; content-addressed source
observations.
**Output:** a proposed, bounded first batch with one row per item: source
authority, successor object, source and target path, current writer, proposed
writer, transition owner, evidence handles, and status. It must distinguish
the two current papers, active Discovery items, APM orchestration surfaces,
and read-only compatibility views.
**Review/decision:** independent inventory/path-collision review; Stephen
approves the exact first batch. Preparation creates no successor authority and
does not alter the source paths.
**Stop/rollback:** stop on incomplete item bijection, stale mutable source,
missing writer identity, path collision, unresolved annotation epoch, or a
paper/APM item without its own closed prerequisite. Delete no source and do
not claim a batch was transitioned.
**Proof before Step 5:** accepted inventory, disjoint path/writer registry,
complete first-batch relation, exact source hashes, and owner decision.

### Step 5 — Per-item ownership transition

**Jira home:** the exact owner-selected per-item issue under KAN-12, aggregated
by KAN-60; KAN-61 remains a hard-stop prerequisite.
**Inputs:** Step-4 accepted row; W9 transition event contract; source and target
content hashes; item-level review/acceptance requirements; the current legacy
writer's final checkpoint; and, for an affected item, the accepted A-001/A-002/
full Stage-2 disposition required by Step 3.
**Output:** one attributed ownership-transition event and one successor-owned
object or projection, with the old source retained and linked. The event must
state the old authority, new authority, writer change, reviewer, owner
decision, and rollback handle.
**Review/decision:** independent item review, then explicit owner acceptance;
the producing actor cannot establish its own independence.
**Stop/rollback:** stop atomically before any write if a source changes during
load, a writer is still active, the mapping is not bijective, a reviewer is not
independent, or the item is a current paper/APM surface whose prerequisites
are not closed. Rollback returns the item to its prior authority and preserves
all evidence; it never rewrites an accepted result or decision.
**Proof before Step 6:** accepted transition event, old/new content addresses,
writer handoff evidence, independent verdict, owner decision, and a tested
rollback handle for that item.

### Step 6 — Whole-path cutover

**Jira home:** KAN-60 aggregate with the item-level KAN-12 child/home and the
KAN-21 validation result.
**Inputs:** all item-level transitions for one registered path; final source
observation; path/writer registry; collision and deletion/rebuild checks;
annotation-epoch fence; writer-revocation procedure; and the accepted
A-001/A-002/full Stage-2 disposition for any affected path.
**Output:** a durable cutover decision for one whole path. The successor writer
becomes authoritative only after the legacy writer is revoked and the final
observation matches the accepted item bijection.
**Review/decision:** independent path-level review, then Stephen's explicit
cutover acceptance.
**Stop/rollback:** stop on any missing/extra/duplicate item, collision,
annotation race, writer still capable of mutation, or source drift. Roll back
to the previous writer only through the recorded recovery procedure; never
delete the source or run both writers.
**Proof before Step 7:** complete bijection, final content-addressed
observation, collision/path tests, annotation fence, writer revocation, and
durable cutover decision.

### Step 7 — Retire an obsolete APM surface

**Jira home:** KAN-60, only after the relevant KAN-12 item/path record and
KAN-21 validation are closed.
**Inputs:** durable whole-path cutover; all dependent paths/items; rollback
window and recovery record; final owner decision; and the accepted
A-001/A-002/full Stage-2 disposition for the affected surface.
**Output:** a retirement record that names the exact surface, replacement
projection, last writer, cutover decision, retained read-only provenance, and
recovery location.
**Review/decision:** independent retirement review and Stephen's explicit
retirement acceptance.
**Stop/rollback:** stop if any active paper, Discovery item, compatibility
view, or dependent APM workflow still references the surface as authority.
Retirement is reversible only by restoring the recorded prior surface; it is
never a deletion or history rewrite.
**Proof:** durable cutover acceptance plus the final retirement decision. No
retirement proof exists at the current state.

## 6. Current next transition

The only bounded next transition is **Step 0 W9/Gate-7 document authoring and
independent review under the owner-approved authoring brief**. This work may
produce a reviewable W9 specification and Gate-7 definition, followed by their
reconciliation and exact-revision acceptance. It is distinct from the later
Gate-7 opening/dispatch decision: that decision remains blocked on exact Gate-6
pilot-promotion evidence and Stephen's separate recorded approval. The W0
addendum and bounded delta review are the first Gate-7 intake deliverable after
opening, not an authoring or opening prerequisite.

The next actor must not execute a pilot, open Gate 7, treat a W0 draft as
accepted, write a transition event, migrate a paper or Discovery item, cut over
a path, revoke a writer, deprecate an APM surface, or retire an APM surface.

The next actor must re-verify the exact subject and all Jira dependencies before
any write. A passing test, a Jira status, a merged plan, or this sequencing
document is not owner acceptance.

## 7. Evidence register

The current claims above are bound to these repository sources and exact
read-only Jira observations:

- [WP6 Gate-6 readiness and integration plan](06-wp6-gate6-readiness-and-integration-plan.md), especially WP6.7 and the exit checklist;
- [WP6 owner-operated session amendment](06g-wp6-owner-operated-session-amendment.md), P-042 boundary and first-release evidence contract;
- [WP6.3 management handoff 32](../handoffs/32-wp6-3-management-handoff-authority-model-and-acceptance-tooling.md), current WP6 completion hard stops;
- [W9/Gate-7 authoring brief](../handoffs/07-w9-gate7-legacy-integration-authoring-brief.md), present authority for W9/Gate-7 document authoring and review, and the separate later Gate-7 opening condition;
- [W0 legacy manifest](../transition/W0-legacy-closeout-transition-manifest-2026-06-28.md) and [W0 current-state addendum](../transition/W0-legacy-closeout-transition-addendum-2026-06-29.md), including the unresolved A-001/A-002 state;
- [master transition plan](../00-master-transition-plan.md), separate authorities, migration lineage, and no-current-paper-migration boundary;
- [current system evidence](../01-current-system-evidence.md), Stage-2 and T1.28 evidence limitations;
- Jira read-only issues KAN-12, KAN-21, KAN-22–26, KAN-60, and KAN-61 on the named cloud, queried 2026-08-01.

No Jira issue, repository plan, or status projection is treated as proof of a
completed transition without the exact artifact, independent review, and owner
decision specified in this document.
