# RM-00: Integrated Research Methods Obligation and Gate Crosswalk

**Status:** INTEGRATED 2026-08-05 under P-047. The exact revision-6 suite was
independently accepted and G-RM-3 was closed for commit `0137d2c` by the owner
record `../reviews/rm-lane-pr198-g-rm-3-owner-acceptance-2026-07-31.md`.
This file remains the obligation/gate crosswalk; it is not a separate delivery
lane or completion target. Future exact-candidate gates remain separately open.

**Created:** 2026-07-28 · **Revised:** 2026-08-05
**Supersedes for execution:**
`../proposals/research-methods-integration-plan-2026-07-28.md`
**Latest review response:**
`../reviews/rm-lane-pr198-premerge-rereview-85f33e6-response-2026-07-31.md`

This document grants no runtime, provider, migration, packet, pilot, result, or
claim authority.

Stephen accepted the P-044 candidate-stage amendment against exact PR #198 head
`fa7d8a6dec4f8d31b9a94747c33e137d4048c376`. It preserves historical G-RM-10,
authorizes only the bounded inert 06i/06j Stage A candidate paths, and defines
G-RM-12, G-RM-13 and G-RM-14. The amendment activates those definitions but
satisfies none of the stage-specific gates. G-RM-3 was subsequently closed for
the exact accepted suite by the 2026-07-31 owner record. No Stage A is
dispatchable before its remaining named prerequisites; G-RM-12, G-RM-13 and
G-RM-14 remain separate.

## 1. Integrated charter

Import provider-neutral research-method patterns into ARS as typed, versioned,
reviewable artefacts under P-042:

- ARS compiles and records bounded briefs;
- an operator runs the external application/session they choose;
- ARS imports returned material as immutable candidate artefacts;
- canonical result/review/manuscript/claim/sidecar consumers admit material
  only through replay-derived artefact authority; and
- ARS executes none of the returned content.

P-047 distributes delivery into the capability that consumes it. WP6.1 owns
06h, 06i, 06j and RM-01. WP6.4 owns RM-02, RM-03 and the non-executing
verification-record portion of RM-04. Gate 9 owns only RM-04's manuscript pilot.
There is no later RM completion event to track separately. Gate 6 cannot close
while its assigned WP6.1/WP6.4 obligations remain absent.

### 1.1 Live ownership map

| Work | Live owner | Jira control | Gate effect |
|---|---|---|---|
| 06h, 06i, 06j, RM-01 | WP6.1 | KAN-65 | Required before WP6.1 and Gate 6 integration |
| RM-02, RM-03, RM-04 verification-return core | WP6.4 | KAN-57 | Required owner-operated-session path before WP6.4 and Gate 6 integration |
| RM-04 manuscript pilot only | Gate 9 successor | KAN-22 | Post-Gate-6; does not block Gate 6 |
| RM-05 execution | Deferred owner gate | G-RM-11 | Not part of an active capability |

The Woodruff et al. paper is evidence lineage, not a provider dependency. No
file, schema ID, field, flag, or production identifier in the lane names a
model provider. TDA appears only in clearly marked examples/pilots.

## 2. Plan suite and dependency order

| Plan | Scope | Depends on | Branch |
|---|---|---|---|
| [06h](06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md) *(main path)* | Exact validated schema identity; complete generic/T2 producer binding; executable historical policy; pinned pre-change suite record | P-043; G-RM-3; G-RM-8; G-RM-9 | `pipe/wp6-1-schema-identity-*` |
| [06i Stage A](06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md) *(main path)* | Inert candidate package for catalogue-complete artefact authority, predicates, review rules and complete consumer inventory | accepted 06h; independent suite `accept`; Stephen's explicit G-RM-3; accepted P-044 amendment authorizing Stage A and G-RM-14 | `plan/wp6-1-artefact-authority-candidate-*` |
| [06i Stage B](06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md) *(main path)* | Materialize accepted candidate; production writer; existing release migration; review/P-005 binding; canonical consumer firewall | accepted 06i Stage A exact subject; operative G-RM-14 | `pipe/wp6-1-artefact-authority-*` |
| [06j Stage A](06j-w3-context-packet-lifecycle-and-resolution-plan.md) *(main path)* | Inert candidate package for the nine-command W3 packet lifecycle, schemas, transitions and authority scopes | accepted 06h; independent suite `accept`; Stephen's explicit G-RM-3; accepted P-044 amendment authorizing Stage A and G-RM-12 | `plan/w3-context-packet-candidate-*` |
| [06j Stage B](06j-w3-context-packet-lifecycle-and-resolution-plan.md) *(main path)* | Materialize accepted candidate; requested-through-delivered lifecycle; W4/W7 production-seam failure evidence; authoritative resolver | accepted 06j Stage A exact subject; operative G-RM-12 | `pipe/w3-context-packet-*` |
| [RM-01](rm-01-unblock-and-suite-recovery-plan.md) | Post-06h run against the pinned pre-06h cohort/universe; quality accounting; final-candidate reconciliation of every landed production family into the smoke gate | merged 06h; G-RM-7 close-out | `pipe/rm-01-*` |
| [RM-02](rm-02-research-methods-pack-plan.md) | Five candidate assets; independently anchored Git history; fail-closed pack loader | G-RM-3; candidate authorship independent of 06h/06i | `pipe/rm-02-*` |
| [RM-03](rm-03-brief-export-import-plan.md) | Export/import over accepted packet and artefact-use resolvers; closed capability boundary | accepted 06i + 06j; RM-02; G-RM-4 | `pipe/rm-03-*` |
| [RM-04](rm-04-manuscript-review-and-verification-records-plan.md) | Manuscript-review lane and non-executing verification records | RM-03; accepted 06i/06j; G-RM-13 before follow-up use | `pipe/rm-04-*` |
| RM-05 *(unwritten)* | Isolated verification execution | G-RM-11 only after exact-subject isolation acceptance | — |

Permitted parallelism: only after an independent `accept` and Stephen's explicit
G-RM-3 may 06h and candidate-only RM-02 proceed on disjoint files. Even then,
06i Stage A and 06j Stage A remain blocked until the accepted P-044 amendment;
after that amendment and accepted 06h they may proceed in separate worktrees.
Stage B for each waits for its accepted exact candidate and operative owner gate.
RM-01 follows 06h and may run in parallel with authorized 06i/06j work. At
merge, whichever of RM-01, 06i Stage B or 06j Stage B is second relative to an
installed family owns final smoke-manifest reconciliation against current
`main`. RM-03 follows accepted 06i/06j and RM-02. RM-04 follows RM-03.

## 3. Gate checklist

No child plan may contain an owner decision absent from this table.

| Gate | Required owner action | Blocks | Mechanism/evidence required before choice |
|---|---|---|---|
| G-RM-1 | **CLOSED 2026-07-28:** P-043 recorded | 06h direction | decision register |
| G-RM-2 | **CLOSED:** P-044 recorded 2026-07-28; bounded candidate-stage amendment accepted 2026-07-30 | RM lane direction and 06i/06j Stage A authority | decision register |
| G-RM-3 | **CLOSED 2026-07-31:** Stephen accepted exact reviewed commit `0137d2c`, tree `ee7d510`, after zero-finding independent review | accepted suite plan bytes | owner record `reviews/rm-lane-pr198-g-rm-3-owner-acceptance-2026-07-31.md` |
| G-RM-4 | Accept selected Methods Pack assets for exact consumer scope | RM-03 export of those assets | 06i production command; exact asset IDs/hashes; review set; replay-derived authority |
| G-RM-5 | Choose the manuscript-review pilot subject | RM-04 pilot only | exact subject/scope record |
| G-RM-6 | Choose smoke-gate location: quality-gate list or `.githooks` pre-push | RM-01 close-out | liveness negative control |
| G-RM-7 | Resolve the known closed-schema literal defect by **add** or an attributed deliberate omission with continuing non-green status and follow-up owner | any RM-01 “green” claim | exact dispatch-head guard/literal evidence |
| G-RM-8 | Choose 06h migrate, bounded grandfather, or independently evidenced no-store | 06h historical implementation | all three executable protocols and branch-specific positive/bypass/repeat/replay/rollback evidence in 06h |
| G-RM-9 | Accept exact `RegisteredSchema` interface | 06h Task 1 | exact source, identity/path controls, memory measurement |
| G-RM-10 | **PRESERVED:** confirm RM records use the already accepted `RegisterArtefact` / `SetArtefactUseAuthority` family rather than a new event family | 06h artefact-family wiring; RM-03 family choice | accepted family identities and explicit owner confirmation; this gate does not accept 06i candidate bytes |
| G-RM-11 | Keep execution deferred, or independently accept implemented OS isolation, deny-by-default egress, W8 records, exact-script approval, cleanup and escape controls | RM-05 / any execution | exact-subject readiness review; funding or implementation alone is insufficient |
| G-RM-12 | **OPEN:** accept the independently reviewed 06j Stage A nine-command W3 packet lifecycle candidate, schemas, transitions, scopes and resolver contract | 06j Stage B; RM-03 packet use | exact candidate Git blobs/canonical hashes, phase-qualified failures, sealed capability/template, ordering controls and executable F-025-F-028 plus reserved F-029/F-030 mapping |
| G-RM-13 | **OPEN:** Stephen accepts an exact `OperatorVerificationRun` for named `review_evidence` or `manuscript_evidence` scope after independent scientific review | RM-04 follow-up export of that run | exact run ID/hash, eligible unrelated reviewer evidence, 06i predicate/scope, `SetArtefactUseAuthority` event/receipt; result/claim use remains prohibited |
| G-RM-14 | **OPEN:** accept the independently reviewed 06i Stage A candidate without changing the accepted artefact command family | 06i Stage B; RM-03/RM-04 canonical use | exact candidate blobs/hashes, grants/scopes, predicates, review/P-005 bindings, complete consumer inventory, public resolver and atomic failure contract |

Independent-review verdict semantics:

- `reject` blocks the named plan;
- `not_ready` on RM-00 blocks the suite;
- `accept_with_required_changes` makes the subject eligible only after every
  dispatch-blocking condition has independent closure evidence;
- `accept` makes the exact subject eligible for Stephen's separate G-RM-3
  decision; it does not itself clear G-RM-3, dispatch a stage, authorize merge,
  accept candidate bytes, or satisfy G-RM-12/G-RM-13/G-RM-14;
- G-RM-3 closes only when Stephen records an explicit owner decision binding the
  exact reviewed commit and review after the admissible verdict.

## 4. Master obligation register

Forward scan sources: P-042/P-043/P-044, W2, W3, W5, W8, handoffs 25/26/28,
the 2026-07-29/30 reviews, all four PR #198 pre-merge reviews, prior responses,
implementation README, CLAUDE/AGENTS/APM rules.

| ID | Obligation | Enforced by |
|---|---|---|
| O-RM-1 | No provider invocation, provider CLI, API selection, credential read/store/resolve/pass | RM-03/RM-04 closed capability graph over methods, exact CLI handlers and transitive first-party modules |
| O-RM-2 | P-042 authorizes planning only; implementation needed P-044 | closed G-RM-2 |
| O-RM-3 | Record operator, chosen application/session, exact subjects, artefacts and returned evidence | RM-03 session record; no provider eligibility inference |
| O-RM-4 | P-005 claim promotion belongs to Stephen; candidate material cannot feed canonical claims | 06i review/P-005 resolver and five production consumer methods |
| O-RM-5 | Operational/schema success cannot substitute for scientific/authority keys | RM-04 `OperatorVerificationRun` records an operator-reported run; it certifies neither ARS execution nor acceptance |
| O-RM-6 | No secrets, restricted raw data, transcript or hidden reasoning in reusable packets/imports | 06j packet security; closed RM import schemas and negatives |
| O-RM-7 | Procedural memory includes permissions and observer overlays | RM-02 manifest |
| O-RM-8 | Asset history/lifecycle cannot be self-attested | independently supplied Git ancestor/blob anchor; G-RM-4 transition through 06i |
| O-RM-9 | WP6.3 accepted bytes untouched and unread by RM | every file map |
| O-RM-10 | Registry ownership belongs only to 06h under G-RM-9 | standing constraint |
| O-RM-11 | Producer emits exact command-schema identity | 06h generic + T2 matrix |
| O-RM-12 | Every task closes to the matching vault record | each plan close-out |
| O-RM-13 | Worktree, commit, review, commit-message and CodeRabbit boundaries remain literal | standing constraints |
| O-RM-14 | Provider-neutral naming | standing constraint and diff review |
| O-RM-15 | Rollback is rejection/restriction/supersession, never deletion | 06i replay authority; RM-03 |
| O-RM-16 | Imported material is append-only and replayable | 06i command/event/reducer path |
| O-RM-17 | Deferred work has owner and next gate | section 6 |
| O-RM-18 | README status changes with the accepting PR | each close-out uses `implementation/README.md` |
| O-RM-19 | Externally proposed code never executes without accepted isolation | G-RM-11; no current plan executes |
| O-RM-20 | Brief binds an accepted, reachable W3 packet, not a local manifest | 06j producer/lifecycle/resolver; RM-03 read-only consumption |
| O-RM-21 | De-identification sidecar is locatable, reversible and independently authorized | sidecar artefact + 06i replay-derived `sensitive_sidecar` policy; no self-declared allowlist |
| O-RM-22 | RM-03/RM-04 are Paper Claim governance as well as provenance | assurance sections |
| O-RM-23 | Historical policy cannot admit newly malformed events | 06h G-RM-8 position/store/fingerprint bounds |
| O-RM-24 | Production consumption cannot bypass replay authority through direct object reads or projections | 06i public port + repository-wide first-party boundary + existing release and RM-03/RM-04 call sites |
| O-RM-25 | W3 failure before validation remains attributable and replayable across compilation and real W4/W7 production seams | 06j lifecycle service, compiled-state failure bindings, complete CLI/calibration/variant/registry call-graph firewall and phase-specific replay controls |
| O-RM-26 | Owner gates bind exact pre-authored candidate bytes, never later Worker outputs | 06i/06j Stage A packages, independent reviews and operative G-RM-14/G-RM-12 |
| O-RM-27 | Every landed production family enters the live append-path smoke gate under every merge ordering | RM-01 final candidate reconciliation plus second-to-merge ownership in 06i/06j |
| O-RM-28 | Candidate operator reports cannot traverse canonical consumers | RM-04 G-RM-13 external review/use-authority step and result/claim negatives |

## 5. Standing constraints

1. **Worktree/branch.** One approved branch per plan, separate linked worktree,
   `.env` bootstrap, exact cwd/branch/HEAD/status before writes.
2. **Review/merge.** Workers commit and report. Independent review precedes
   owner acceptance. Stephen triggers/monitors CodeRabbit; do not merge while it
   is pending and do not operate it unless explicitly asked.
3. **Validation.** Start with direct artefact checks plus tests exercising the
   changed behavior. Expand only for a named dependency/blast trigger or
   explicit gate; mandated final suites run once at final exact head.
4. **Fixed accepted bytes.** Never modify WP6.2 accepted schemas or WP6.3
   accepted-byte files. Core command/event schemas change only in 06j under
   G-RM-12. `schema_registry.py` changes only in 06h under G-RM-9.
5. **No provider/no execution.** P-042 and G-RM-11 are hard stops.
6. **Assurance lanes.** 06h/06i/06j: Output/Provenance plus
   provenance-integrity. RM-02: Output/Provenance. RM-03/RM-04:
   Output/Provenance plus Paper Claim governance. No plan changes mathematical,
   statistical, topological or representation logic.
7. **Stop Partial.** A wrong live interface, missing authority producer,
   unreachable predecessor, or widened schema decision stops work and returns
   the plan for revision; a Worker does not invent an interface.
8. **Implementation skills.** contract-first-tdd,
   research-assurance-triage, executing-plans-extras; schema-contract-design
   for 06i/06j schema work.

## 6. Deferred items

| Item | Owner | Next gate |
|---|---|---|
| ARS execution of proposed code | Stephen | G-RM-11 after threat model and exact isolation evidence |
| Remaining accepted command families not named by 06i/06j | Stephen | separately reviewed plan after the focused families |
| Direct provider adapter | Stephen | decision superseding relevant P-042 boundary plus W4/W6/W7 evidence |
| Lean/formalization expansion | Stephen | after RM-04 pilot identifies warranted claims |
| TDA-on-proof-state / sheaf consistency | Discovery Harness | assay + PROMOTE |
| Remote MCP / fine-tuning | Stephen | later legal/governance gate |

## 7. Success criteria

- **06h:** exact bytes and same instance; generic and T2 paths emit correct
  triples; pre-change cohort/universe pinned; selected historical protocol is
  idempotent, replay-safe and rejects newly malformed events.
- **06i:** an independently reviewed Stage A package is accepted before
  implementation; registration forces candidate; all catalogue authority/review
  controls and atomic negatives pass; existing release publication and all five
  consumer kinds use one replay-derived resolver; every unclassified
  repository-wide direct-read bypass fails.
- **06j:** an independently reviewed Stage A package is accepted before
  implementation; requested, compiling, compiled and failed states remain
  attributable/replayable before validation; W4 routing and selected-route W7
  revalidation cannot fail outside the lifecycle writer; every CLI/rederivation,
  coverage, calibration, variant and registry path is literally classified and
  rejects missing/forged lifecycle capability before side effects; no fallible
  W3/W4/W7 check remains between validation and issue; a W3-complete packet is issued,
  delivered and resolved by exact current state; executable F-025-F-028 pass and F-029/F-030 remain explicit P1 reservations with owned pre-pilot follow-up.
- **RM-01:** the same pre-06h 156-node cohort and full universe are observed
  post-06h; additions/removals/renames are explicit; the final candidate
  smoke-manifest covers every production family landed on current `main`; smoke
  negative fires; no green claim before G-RM-7.
- **RM-02:** five candidate assets; checkout-stable identity; history anchored
  to an independently supplied prior Git subject; coordinated asset/manifest/
  history rewrite still fails; acceptance remains external.
- **RM-03:** export consumes 06j packet authority and G-RM-4 asset authority;
  import lands candidate through 06i; real result/review/manuscript/claim/
  sidecar resolution call sites use 06i; capability graph covers CLI and
  transitive modules.
- **RM-04:** manuscript pilot and operator-run records remain non-executing and
  non-promoting; a run remains candidate until independent review and G-RM-13
  grant exact review/manuscript scope, while result/claim use stays blocked.

## 8. Residual risk

- Static capability analysis cannot make untrusted execution safe; execution is
  therefore absent.
- Operator session records establish provenance, not truth.
- Canonical use controls do not prevent human cognition from being influenced
  by candidate material.
- Git identity and event/replay authority remain only as strong as their
  independently accepted anchors and current revalidation.
- The new 06i/06j families enlarge the implementation surface; they require
  their own exact-subject reviews and cannot be accepted through RM-03 tests.
