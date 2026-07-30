# RM-00: Research Methods Lane — Master Plan

**Status:** REVISED 2026-07-29 after the G-RM-3 adversarial review returned
`rework_required` on the whole suite (`../reviews/adversarial-rm-lane-plan-suite-review-2026-07-29.md`;
disposition of every finding in `../reviews/rm-lane-review-response-2026-07-29.md`).
P-043 and P-044 remain accepted (2026-07-28); gates G-RM-1 and G-RM-2 stay
closed. **G-RM-3 is re-opened against this revised suite and no plan is
dispatchable until a fresh independent review clears it.** This document confers
no runtime, provider, migration, pilot, result, or claim authority.
**Created:** 2026-07-28 · **Revised:** 2026-07-29 (revision 2)
**Supersedes for execution:** `../proposals/research-methods-integration-plan-2026-07-28.md`
(retained as the analysis record)

**Lane character (corrected per review M-2):** an independent
specification-and-implementation lane per accepted D-2 — parallel to the
WP6.1+WP6.3 → WP6.4 → Gate 6 path, never on it. RM completion is not a Gate 6
criterion and Gate 6 does not wait for RM. **There is no longer an exception to
this.** Revision 1 hosted a WP6.1 main-path repair inside RM-01 "for scheduling
convenience"; the review showed that made acceptance authority and scheduling
dependency document-name dependent. That repair is now
[06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md](06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md),
a main-path WP6.1 plan outside this lane. RM plans depend on the accepted
*capability* it delivers, never on the plan's name.

**Naming rule (accepted D-3):** every artifact in this lane is provider-neutral.
The Woodruff et al. Gemini paper is cited as *evidence lineage* for method
assets, never as a provider dependency. No file, schema `$id`, CLI flag, or
identifier in this lane may name a model provider. Security test data uses
neutral synthetic modules, so the P-042 guard does not have to violate this rule
in order to exist (review M-4).

---

## 1. Lane charter

Import the research-method patterns evidenced in *Accelerating Scientific
Research with Gemini* (Woodruff et al.) into ARS as typed, versioned, reviewable
artifacts, operating entirely inside the P-042 owner-operated-session regime:

- ARS **compiles and records** bounded research briefs (export);
- the **operator** runs the external model session in an application of their
  choice;
- ARS **imports** returned material fail-closed into typed, append-only
  artefact records that land at `use_authority: candidate` and can become
  admissible evidence only through an attributed owner transition.

The core is STEM-generic. TDA/Markov material appears only as pilot fixtures and
in the existing W5 domain-pack layer, consistent with the open-source posture.

**Removed from the charter in revision 2.** Revision 1 carried a fourth clause:
ARS executes model-proposed verification code. Review C-4 established that
executing model-proposed Python with the project interpreter, beside a
gitignored `.env` and the vault, without isolation or egress control, makes
credential and data leakage reachable by design. Execution leaves the lane until
an isolation substrate exists (G-RM-11). The paper's neuro-symbolic loop is
therefore imported in its recording half only.

## 2. Plan suite and dependency order

| Plan | Scope | Depends on | Branch prefix |
|---|---|---|---|
| [06h](06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md) *(main path, not RM)* | Exact-byte schema identity; producer emits the `command_schema_*` triple; accepted artefact command family wired through command/ledger/replay | P-043; G-RM-3 (fresh independent review); gates G-RM-8, G-RM-9, G-RM-10 | `pipe/wp6-1-*` |
| [rm-01](rm-01-unblock-and-suite-recovery-plan.md) | Post-fix suite delta against a fresh dispatch-head manifest, coverage/lint accounting, append-path smoke gate | 06h merged; G-RM-7 for close-out | `pipe/rm-01-*` |
| [rm-02](rm-02-research-methods-pack-plan.md) | Methods Pack v1: manifest schema, revision history, five method assets, fail-closed loader, negative controls | P-044; no code-path dependency on 06h or RM-01 | `pipe/rm-02-*` |
| [rm-03](rm-03-brief-export-import-plan.md) | `ars brief export` / `ars brief import` on the accepted artefact path; W3 packet binding; consumer firewall; capability-boundary guard | **accepted artefact-record capability** (delivered by 06h) AND RM-02 | `pipe/rm-03-*` |
| [rm-04](rm-04-manuscript-review-and-verification-records-plan.md) | Manuscript-review lane; non-executing verification request/result records | RM-03 | `pipe/rm-04-*` |
| rm-05 *(unwritten)* | Isolated verification execution | **G-RM-11** — not planned until the implemented isolation substrate and its evidence receive independent readiness acceptance | — |

Permitted parallelism: **06h and RM-02** may run concurrently — disjoint file
sets, no shared module. RM-01 follows 06h. RM-03 follows both RM-02 and the 06h
capability. RM-04 follows RM-03. The review confirmed RM-01/RM-02 file-level
parallelism was sound in revision 1; the same disjointness now holds for
06h/RM-02.

## 3. Gate checklist (owner touchpoints, hoisted from all child plans)

Per writing-plans-extras, every owner precondition in a child plan is listed
here; the acceptance runner works from this table, not from child prose. Review
M-1 found revision 1's table incomplete — R1-3b was an owner decision visible
only in RM-01 prose. The rule is restated as a check: **no child plan may
contain the words "owner decision" without a row here.**

| Gate | What Stephen must do | Blocks | Source |
|---|---|---|---|
| G-RM-1 | **CLOSED 2026-07-28** — P-043 entered in the register | 06h (unblocked) | 03-decisions §P-043; handoff 26 Defect 3 |
| G-RM-2 | **CLOSED 2026-07-28** — P-044 entered in the register | all RM dispatches (unblocked at this gate) | 03-decisions §P-044 |
| G-RM-3 | **RE-OPENED 2026-07-29.** Accept the adversarial-review disposition of the *revised* suite, per the tightened semantics below | dispatch of every plan including 06h | house review-then-dispatch practice; review M-1 |
| G-RM-4 | Accept Methods Pack assets (`candidate -> reviewed -> accepted`); **only `accepted` assets are exportable, with no override flag** | RM-02 close-out; RM-03 export | W3 §13.1-13.2; review M-1 |
| G-RM-5 | Choose the manuscript-review pilot subject (suggested: one P01 draft section) | RM-04 pilot | Stephen's steer: TDA as testbed, not definition |
| G-RM-6 | Confirm append-path smoke-gate wiring location (quality-gate command list vs `.githooks` pre-push) | RM-01 close-out | observer log Obs. 137; `.githooks` discipline |
| **G-RM-7** | **NEW.** Resolve R1-3b through an owner record choosing one branch. **Add:** add `receipt-v2.schema.json` to the closed 13-name literal and record evidence that the literal and submit-signature guards were verified. **Deliberate omission:** record why this is an unreviewed-schema-addition gate, name the follow-up owner/action, and keep RM-01 non-green until the closed-set failure is actually resolved. RM-01 remains non-green while either the known closed-set or signature-guard failure is unresolved; the signature guard is fixed at current currency by `a681180` but must be reverified at dispatch head | RM-01 close-out; **any "suite green" claim** | handoff 28 §"NOT Defect 3"; review M-1, M-9 |
| **G-RM-8** | **NEW.** Historical-event policy: migrate events predating the `command_schema_*` triple, grandfather them behind a documented predicate, or assert with evidence that no prior durable store exists | 06h Task 2 | handoff 26 §"existing events"; review C-1 |
| **G-RM-9** | **NEW.** Approve the `RegisteredSchema` exact-byte registry interface (the only sanctioned edit to `schema_registry.py`) | 06h Task 1 | review C-1 |
| **G-RM-10** | **NEW.** Confirm RM records use the **accepted artefact command family** (`RegisterArtefact` / `SetArtefactUseAuthority`) rather than a new reviewed event family | 06h Task 3; RM-03 | review C-3; see §5a |
| **G-RM-11** | **NEW.** Either keep execution deferred, or independently accept the implemented isolation substrate as ready: OS-enforced isolation, deny-by-default egress, W8 grant/lease/process/stop records, attributed exact-script approval, and passing escape-control negative evidence must all be reviewed at an exact subject. Funding or implementation alone does not clear the gate | RM-05 (unwritten); any execution anywhere in the lane | review C-4 |

**G-RM-3 semantics (tightened per review M-1).** Revision 1 required only
"accepted review disposition; zero unresolved Critical", which would have let a
plan carrying unresolved blocking Majors count as dispatchable. The gate now
reads:

- a `reject` verdict on a plan **always** blocks that plan's dispatch;
- `accept_with_required_changes` clears the gate **only** once every
  dispatch-blocking condition named in the review has independent closure
  evidence — not the authoring session's assertion that it was addressed;
- `accept` clears the gate;
- RM-00 earns a readiness verdict, not a dispatch verdict, and a `not_ready`
  RM-00 blocks the whole suite, because this gate table is the runner's only
  input.

## 4. Master obligation register

Forward-obligation scan run against: P-042/P-043/P-044 (03-decisions), W2
(design/02), W3 (design/03), W5 (design/05), W8 (design/08), WP6.3 acceptance
(handoffs/25), handoff 26, handoff 28, the 2026-07-29 adversarial review, README
governing constraints, CLAUDE.md/APM_RULES.

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| O-RM-1 | P-042 decision text | ARS must not invoke a provider, spawn a provider CLI, make a provider API call, select a provider for the user, or read/store/resolve/pass OAuth credentials | Global constraint in every plan; **capability-boundary** guard in RM-03 Task 5 (a denylist proved insufficient — review M-4) |
| O-RM-2 | P-042 boundary clause | P-042 authorizes plan/dependency correction only; implementation needs a new owner decision | P-044 accepted; G-RM-2 closed |
| O-RM-3 | P-042 decision text | Operator-mediated workflow must record operator, chosen application/session, exact subjects, artifacts, and returned evidence | RM-03 **RM-owned session record** as attributed evidence — not an eligibility allowlist (review M-7) |
| O-RM-4 | W5 §19.3 | Claim promotion requires Stephen's attributed P-005 decision; nothing else is promotion authority | Imported records land at `use_authority: candidate`; only an attributed `SetArtefactUseAuthority` admits them; RM-03 consumer-firewall tests |
| O-RM-5 | W5 §17 | Two-key validity: no operational success or schema pass compensates for a failed required key | RM-04: a `VerificationResult` never auto-accepts a result and certifies execution only |
| O-RM-6 | W3 §15 / §9 | Secrets, raw restricted data, full transcripts, hidden reasoning prohibited from reusable packets and manifests | Import schemas `additionalProperties: false` + forbidden-field negative tests; export prohibitions block |
| O-RM-7 | W3 §13.2 | Procedural memory carries name, version/hash, source path, applicability trigger, compatibility, dependencies, supersession, review state, **permissions, and applicable observer overlays** | RM-02 manifest schema; the last two were missing in revision 1 (review M-3) |
| O-RM-8 | W3 §13.1 lifecycle | Memory assets: `candidate -> reviewed -> accepted`; non-accepted excluded from governing use | RM-02 immutable revisions + append-only revision history; exporter filter with **no override flag**; G-RM-4 |
| O-RM-9 | handoffs/25 + handoff 26 "Do not touch" | `wp6-3-tdl-private-assurance-pack.yaml` and its schema are owner-accepted exact bytes at `449b0d00` | Do-not-touch list in every plan; RM-03 no longer *reads* the pack either (review M-7) |
| O-RM-10 | handoff 26 | Defects 1-2 were assigned to a then-in-flight agent in `schema_registry.py` | **Discharged** — landed on `main` via PR #176/#179. The file is now editable **only** inside 06h Task 1 under G-RM-9 |
| O-RM-11 | handoff 26 Defect 3 | Direction decision required: producer emits vs schema relax | **Closed** — P-043 (producer emits); executed by 06h Task 2 |
| O-RM-12 | APM_RULES vault discipline | Every task ends with the matching vault entry, top-of-page reverse-chronological | Close-out step in every plan |
| O-RM-13 | Working rules (CLAUDE.md, memory) | `[PIPELINE] P00:` commit subjects, Co-Authored-By trailer, BOM-free `git commit -F` files, never `--no-verify`, worktree `.env` copy, review-then-merge with CodeRabbit concluded | Global constraints in every plan |
| O-RM-14 | D-3 acceptance | Provider-neutral naming everywhere | Naming rule above; review question for every plan |
| O-RM-15 | Report-2 rollback semantics | Rollback = disable commands / mark pack ineligible; imported artifacts remain immutable and are superseded, never deleted | Now expressible in accepted terms: `use_authority: superseded` / `rejected`; RM-03 |
| O-RM-16 | W2 append-only discipline | Imported material lands as append-only typed records, replayable | RM-03 via the **accepted artefact family**; replay proven in 06h Task 3 |
| O-RM-17 | Track 3 deferrals (analysis doc §3) | Direct provider adapter, Lean-lane expansion, TDA-on-proof-states, sheaf consistency, remote MCP, fine-tuning: all deferred with named next gates | §6 |
| O-RM-18 | Observer log Obs. 136 | README/status drift when acceptance records land | Every plan's close-out updates its README row in the same PR |
| **O-RM-19** | Review C-4 / W8 | Any execution of externally-proposed code requires OS-enforced isolation, deny-by-default egress, W8 grant/lease/process records, and non-self-attested exact-script approval | **G-RM-11**; no plan in this suite executes anything |
| **O-RM-20** | Review M-6 / W3 §§9, 13 | A bounded brief must bind an accepted W3 context packet, not substitute a weaker manifest for one | RM-03 packet binding; brief declared a non-governing rendering |
| **O-RM-21** | Review M-10 | De-identification must be *reversible by ARS*: a digest alone neither locates nor authorizes the mapping | RM-02 asset 3 + RM-03 sidecar object with ID/revision/hash and round-trip tests |
| **O-RM-22** | Review M-12 / W5 §§14.6, 19 | Work carrying review findings toward a manuscript is Paper Claim governance, not provenance-only | §5.6; RM-03/RM-04 assurance sections |

## 5. Standing constraints (inherited by every RM plan)

1. **Worktree isolation.** Each task branches from current approved `main` into
   a worktree under `.apm/worktrees/`; immediately copy
   `C:/Users/steph/TDL/.env` into the worktree. Workers commit and report;
   merges happen only after review.
2. **Review-then-merge.** CodeRabbit must conclude on the PR before merge;
   never fast-forward a local merge onto `main` (memory: PR #54 incident).
3. **Environment.** A fresh worktree `.venv` is an empty stub and the main-repo
   interpreter lacks `jsonschema`. Provision with
   `uv sync --all-extras --no-install-package petls`, then run pytest via
   `uv run --no-sync python -m pytest -q <target> -o "addopts=" -p no:cacheprovider -p no:cov`.
   Budget with handoff 28's measured numbers (full suite ~1:13 h); the full
   tree runs **once per plan, at final exact head**, never per task. Do not
   pipe long background runs through `tail` — output buffers until exit.
4. **Do not touch, any plan:**
   `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`,
   `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`
   (owner-accepted exact bytes); `.research-system/schemas/wp6-2-*/**`
   (accepted T2 family); `.research-system/schemas/core/commands/**` and
   `.research-system/schemas/core/events/**` (accepted generated surface — the
   fixed target, not the adjustable variable); anything under
   `docs/plans/agentic-research-system/reviews/` or `handoffs/` (immutable
   provenance). `research_system/schema_registry.py` is editable **only** in
   06h Task 1 under G-RM-9.
5. **Skills for implementing Workers:** `contract-first-tdd`,
   `research-assurance-triage`, `executing-plans-extras`. One failing
   public-seam test before each production change.
6. **Assurance lanes (corrected per review M-12).** RM-02 is Output/Provenance.
   **RM-03 and RM-04 are Output/Provenance *and* Paper Claim governance** —
   they carry externally-produced review findings and counterexamples toward
   work that may reach a manuscript, which is exactly where claim-consumer,
   wording-strength, independent-review and human-authority controls are
   needed. 06h is Output/Provenance plus provenance-integrity. No plan creates
   or alters mathematical, statistical, topological or representation logic;
   any task finding itself in such logic stops Partial.
7. **Stop-Partial rule.** If a plan's stated interface proves wrong against
   live code, the Worker stops Partial and reports the discrepancy; plans are
   corrected by revision, not improvised around. Revision 2 exists because a
   reviewer applied this rule to the plans themselves before a Worker had to
   discover it mid-task.

## 5a. Why the accepted artefact family (review C-3, gate G-RM-10)

Recorded here because it is this revision's load-bearing architectural choice,
and the next reviewer should attack it directly.

Revision 1 invented `ars://methods/event/MethodBriefRecorded` and
`MethodResultImported`. The review proved that family unreachable:
`CommandService._build_event` rejects unknown command types and hard-codes
`ars://core/event/...`; replay raises `unknown event schema` for anything
outside the core and T2 prefixes.

Inspecting the schema tree while confirming that finding showed ARS has already
accepted the mechanism the lane needs. `.research-system/schemas/core/commands/`
holds 86 accepted command schemas including `RegisterArtefact`,
`SetArtefactUseAuthority`, `SupersedeArtefact` and `RecordScientificReview`;
`ars://core/command`'s `target_stream_id` already admits `art_`; `artefact: art`
is a registered ID kind. All are `x-lifecycle: proposed_materialized` — accepted
in specification, unwired in runtime.

So: a brief is an artefact, and an imported result is an artefact. That gives
the lane three things it could not otherwise get cheaply:

- **no new event family** and no ID-catalogue amendment (review C-3, M-8);
- **a real consumer firewall.** `SetArtefactUseAuthority` is an
  authority-checked, owner-attributed transition binding `subject_sha256` and a
  `consumer_predicate`, over the closed enum
  `candidate | accepted_for_scope | rejected | superseded | restricted`.
  Imported material lands `candidate` and moves only by attributed command —
  which is precisely what review M-5 showed four local status enums could not
  deliver;
- **rollback in accepted terms**: `superseded` / `rejected`, satisfying
  O-RM-15 without any delete path.

**The risk, stated plainly.** Reusing a generic mechanism becomes an authority
bypass if consumer predicates are loose — the review's own closing residual
risk. The mitigation is that `accepted_for_scope` requires an attributed command
whose `subject_sha256` matches the registered artefact's `content_sha256`, and
RM-03's firewall tests must prove a consumer cannot treat a `candidate` artefact
as evidence. If the next review finds that predicate weak, G-RM-10 is where the
decision gets revisited.

## 6. Deferred items (owner and next gate named; not silently dropped)

| Item | Owner | Next gate |
|---|---|---|
| **Verification execution of model-proposed code** | Stephen | **G-RM-11** — requires OS-enforced isolation (disposable interpreter, sanitized environment, deny-by-default egress, read-only exact input mounts, no repository/`.env`/vault/home visibility), W8 `ResourceGrant`/`ExecutionLease`/`ProcessIdentity`/stop records, attributed exact-script approval, and the eight escape negative controls in the review's coverage list. Threat model first, then a plan |
| Sweep of the 78 still-unwired accepted command types | Stephen | After 06h proves the pattern on two; separate reviewed plan |
| Direct provider adapter (any provider) | Stephen | New owner decision superseding the relevant part of P-042, then W4 eligibility evidence + W7 parity + W6 calibration |
| Lean/formalization bridge expansion | Stephen | After RM-04 pilot evidence shows which claims merit formalization |
| TDA-on-proof-state trajectories; sheaf-theoretic claim consistency | Stephen (Discovery Harness) | `/assay` scorecard; PROMOTE required before any spike |
| Remote MCP exposure; fine-tuning/distillation | Stephen | Out of first-release scope (W1); legal/governance review first |

## 7. Success criteria

- **06h:** the emitted `command_schema_sha256` equals an independently computed
  digest of the exact schema file bytes; the producer and `validate()` provably
  share one `RegisteredSchema` instance; both artefact commands round-trip
  through command → ledger → replay with identical genesis and incremental
  projections; every negative control (TOCTOU, valid-but-wrong triple,
  direct-append bypass, illegal transition, `subject_sha256` mismatch, missing
  reducer) is red-then-green; the producer coverage matrix is recorded.
- **RM-01:** a dispatch-head collection manifest recorded before any production
  mutation; the 156-node handoff-28 cohort preserved by name and shown to move
  together; the full current universe compared, not only the cohort;
  coverage/lint accounting includes `research_system`; the smoke gate
  demonstrably fails on a seeded producer/schema divergence. **No "green" claim
  until G-RM-7 resolves.**
- **RM-02:** five method assets with complete W3 §13.2 metadata including
  permissions and observer overlays; checkout-stable external identity; an
  append-only revision history that detects a same-version byte replacement;
  every forbidden lifecycle transition, EOL variant, forged acceptance
  reference and self-hash shape rejected.
- **RM-03:** a brief binding an accepted W3 packet by `context_id`, revision and
  hash exports for a real task; a conforming import lands as a `candidate`
  artefact and replays; the consumer firewall blocks direct
  imported-evidence-to-result use, projection reclassification and forged
  operator verification; the capability-boundary guard fires on dynamic import,
  subprocess, socket, generic URL and transitive dependency paths; the
  de-identification sidecar round-trips and rejects wrong/missing/stale joins.
- **RM-04:** one manuscript-review pilot on a Stephen-chosen subject, with a
  `ReviewFindingSet` bound to the draft's exact hash, landed as a `candidate`
  artefact — with no execution, no claim, no result acceptance, and no
  lifecycle transition performed by any RM component.

## 8. Residual risks that survive this revision

Carried from the review unchanged, because none is closed by editing plan text:

- Static controls reduce accidental provider coupling but cannot replace
  process-level network and filesystem restrictions for executed code. This is
  why execution is deferred rather than merely constrained.
- Operator-mediated sessions remain a human provenance boundary: recording an
  application and session does not evidence the returned content's truth.
- Imported review and counterexample material still influences humans outside
  ARS. The mechanical firewall governs canonical use, not cognition.
- Git-blob identity is stable for tracked text, but operator-facing rendered
  bytes need their own explicit canonicalization and content hash.
- A generic artefact event minimizes code only while consumer predicates stay
  strict enough that "generic" does not become an authority bypass (§5a).
