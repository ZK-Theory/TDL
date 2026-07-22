# Large-Workflow Completed-Cycle Assessment

**Date:** 2026-07-23
**Verdict:** `approve_advisory_v1_1_with_revisions`
**Workflow system:** Standalone TDL supervision; not APM
**Trial subject:** WP6.2 T2 authority/addendum contract materialization through final R3
**Accepted candidate:** `391a92753d7f746fa91a6b5455c9ce0fd01baa52`
**Accepted candidate tree:** `0254c5416925126412867d61b3045ee1563abd0c`
**Final review:** `655f4173db93447a068adc6e92621455c4abc85d`; `accept`, zero findings
**Owner acceptance record:** P-040 at manager commit
`cbe47e1b7ed382308df61e9173722dc9085f4548`

## Executive assessment

The standalone method completed the delivery cycle without APM state, inherited
reviewer history, CodeRabbit polling, accepted-byte mutation, runtime expansion,
or false acceptance. Exact-state packets and fresh reviews preserved assurance,
and the research-first correction produced a final zero-finding R3 candidate.

The cycle was nevertheless more expensive than it should have been. App task-turn
metadata records at least 266.7 minutes (4.45 hours) of author/reviewer activity,
excluding Manager work, owner decision time, provisioning, and startup-only routing
stops. One 26.6-minute R2 task produced no review deliverable after crossing a
cybersecurity boundary. The first remediation also implemented contract-stage
security and complete-W7 machinery that P-039 later removed or deferred. The
advisory method therefore passes with material v1.1 revisions, not unchanged.

Exact token telemetry is not exposed for these tasks. Duration, task/turn count,
context mode, compaction reports, validation invocations, and regenerated-artifact
counts are used as auditable proxies; no token saving is invented.

## Measured cycle

The timed set contains six fresh tasks and ten completed task turns. It excludes
the Manager task and two earlier startup-only detached/routing stops, so it is a
lower bound on total campaign cost.

| Phase | Task/thread | Active duration | Outcome |
|---|---|---:|---|
| Initial authoring | `019f8a2e-61a5-7b40-8b07-adb0d8243dad` | 77.8 min | R1 candidate `1144d6a6`; 113 focused tests |
| Handback correction | same author task | 2.3 min | Wrapper-only correction |
| Fresh R1 review | `019f8a80-2e64-7633-acbd-f6fb7f12ef9b` | 16.1 min | 4 Critical, 3 Major |
| R1 remediation | initial author task, bounded continuation | 57.4 min | R2 candidate `36b51b05`; 165 focused tests |
| First R2 attempt | `019f8b0f-6fca-72f2-a551-304ff0d5d811` | 26.6 min | No deliverable; cybersecurity boundary |
| Fresh static R2 | `019f8b3e-5a2d-7552-9bd8-dfe7562c93b3` | 15.8 min | 4 Critical, 4 Major |
| R2 provenance correction | same static reviewer | 3.4 min | Full 06b source re-evaluated; verdict unchanged |
| R2 scope clarification | same static reviewer | 0.1 min | No further security exploration |
| Final fresh remediation | `019f8bb8-b7e5-73b1-bb10-ca30a679cd73` | 47.5 min | Final candidate `391a927`; 135 focused tests |
| Fresh static R3 | `019f8beb-f6f7-7900-b14c-3c7da567ba25` | 19.8 min | `accept`; zero findings |
| **Total** |  | **266.7 min** | Contract candidate accepted under P-040 |

Published validation evidence includes 826 focused-test passes across six
candidate/review runs, four 102-contract checks, and two earlier full-framework
runs. Repeating focused tests between an author and an independent reviewer was
appropriate. The second full-framework run and the pre-runtime security expansion
were not proportionate to the final semantic surface; P-039 correctly replaced
them with focused, contract, deterministic-rematerialization, and protected-byte
evidence.

## Criteria assessment

| Criterion | Evidence | Assessment |
|---|---|---|
| Standalone routing | No APM state or numbered APM skill in delivery tasks | Pass |
| Exact-state continuity | Every candidate/review handback bound commit, tree, blobs, hashes, branch, and remote | Pass |
| Fresh independent review | R1, static R2, and R3 started without author/Manager history | Pass |
| Context discipline | Fresh tasks used for independent subjects; no reported compaction in final remediation/R3 | Pass with revision: the first author task was reused for a long remediation |
| Certify before regenerate | Accepted WP6.1/T1a bytes were checked and retained; final materialization was deterministic | Pass |
| Assurance preservation | R3 closed C1/C2/C4/M1/M3/I1; P-039 explicitly disposed C3/M2 | Pass |
| Research-value proportionality | Applied only after R2 had expanded security/runtime scope | Late; must move to dispatch intake |
| Review-cycle budget | One normal remediation plus one exceptional owner-authorized final cycle | Exception exposed missing rescope rule |
| External review ownership | Zero CodeRabbit triggers, polls, waits, schedules, or automations | Pass |
| Validation proportionality | Final cycle omitted full 665 suite and custom probes | Pass after P-039; earlier cycles over-ran |
| Git/worktree routing | Corrected detached-start protocol worked for final author/reviewer | Pass after avoidable startup stops |
| Integration readiness | Accepted object, review, and P-040 are split across branches; no PR exists | Needs explicit integration lane |
| Efficiency measurement | Exact token telemetry unavailable; task durations and validation counts recoverable | Partial; record proxies prospectively |

## What should remain unchanged

- Standalone workflow identity must be declared before reading campaign state.
- Exact-state packets remain continuity aids, never self-authoritative decisions.
- Self-contained implementers and reviewers receive no parent history.
- At most two primary skills remain the default.
- Stephen owns CodeRabbit triggering and monitoring.
- Existing deterministic and accepted artifacts are certified before regeneration.
- Author and independent-review validation remain distinct where independence is
  the assurance property.

## Required v1.1 revisions

### 1. Put the research-value gate before scope freezes

Before a non-research assurance control becomes blocking, the dispatch must record
the protected research asset, credible failure path, insufficiency of existing
controls, cheapest adequate control, lifecycle stage where evidence is possible,
and an effort/context budget with a stop. General hardening remains capped at 10%
unless Stephen explicitly elevates it. Runtime-only evidence defaults to runtime
integration, not a contract-only package.

### 2. Treat a second remediation as a rescope event

One author-review-remediation cycle remains the default. If another cycle appears
necessary, stop ordinary delivery. The Manager must classify each finding as:
retained research/contract integrity, later-stage evidence, separately justified
hardening, or rejected scope. Any second cycle requires a recorded owner ruling,
a new exact subject, and a fresh task with no inherited author/reviewer history.

### 3. Separate management, candidate, review, and integration branches

The campaign declares these branch roles before authoring. Meta-method and
governance commits should not become candidate ancestry merely because the Manager
created the author branch. Acceptance binds the immutable candidate. Integration
uses a separate branch and a declared merge strategy that keeps the accepted
candidate commit reachable; do not squash or rebase away an exact accepted subject.

### 4. Make external-review capacity a packaging contract

Before opening or updating a PR, compute the merge-base file count with
`git diff --name-only <base>...<head>`. CodeRabbit has a hard 100-file PR limit.
Target at most 90 files where practical; if a PR would exceed 100, split it on
semantic dependency boundaries, declare merge order and bases, and review the final
integration seam. A split must not separate a contract from the tests or identity
records required to review it.

### 5. Make validation launchers part of read-only assurance

Where tests need Git history, use a temporary no-hardlink clone with
`core.autocrlf=false` and `core.longpaths=true`; a source archive is insufficient.
Use an already verified external interpreter. Do not invoke an environment manager
from a review root when it can create an ignored `.venv`. Check ignored residue as
well as `git status` after hooks.

### 6. Record efficiency proxies prospectively

Each completion handback records task/turn count, app-reported active duration when
available, context mode, compactions, inherited turns, validation invocations,
regenerated artifacts, true/false stops, remediation cycles, and external-review
waits. If token telemetry is unavailable, say so; never substitute an estimate.

## Enforcement disposition

The evidence threshold for designing a dispatch checker has now been met, but this
assessment does not activate a mandatory checker or a `CONVENTIONS.md` lock. The
v1.1 advisory fields should first land through normal review. A separate owner-approved
checker PR may then implement only mechanically decidable rules: workflow identity,
exact subject/root/branch/write owner, context and skill budgets, research-value
disposition for blocking non-research controls, cycle count, branch roles, validation
levels, external-review ownership, and PR file cap. It must ship negative controls and
a positive execution signal. Research-value judgments themselves remain human/Manager
decisions, not linter verdicts.

## Integration recommendation

1. Land the v1.1 assessment and advisory instruction changes as PR A. Compute its
   exact file count first and split if it exceeds CodeRabbit's 100-file limit.
2. After PR A merges, create a distinct T2 integration branch that preserves accepted
   candidate `391a92753d7f746fa91a6b5455c9ce0fd01baa52` as an ancestor and includes
   the R3 report, exact-state handback, and P-040 record.
3. Run one fresh integration-seam review against then-current `main`; do not repeat
   authoring or reopen settled R3 findings absent a touched authority.
4. Only after that integration merges may a separately authorized T2 runtime brief
   be proposed. T3/T4 remain out of scope until merged T2 runtime behavior passes its
   own independent gates.

## Final verdict

Adopt advisory v1.1 through review. The method successfully preserved assurance and
completed the cycle, but the research-value gate, second-cycle rescope rule, branch
topology, launcher hygiene, prospective metrics, and 100-file PR packaging limit are
required corrections. Mandatory enforcement remains a separate owner decision.
