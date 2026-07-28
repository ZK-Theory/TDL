# RM-00: Research Methods Lane — Master Plan

**Status:** ACCEPTED FOR PLANNING — P-043 and P-044 entered in the decisions register
by Stephen's instruction on 2026-07-28 (gates G-RM-1 and G-RM-2 closed). Dispatch of
each plan remains blocked on its independent adversarial review (gate G-RM-3) and, for
RM-01, on the handoff-26 Defect 1–2 fixes landing. This document confers no runtime, provider, migration, pilot, result, or
claim authority.
**Created:** 2026-07-28
**Supersedes for execution:** `../proposals/research-methods-integration-plan-2026-07-28.md`
(retained as the analysis record; this suite is the executable form)
**Lane character:** independent specification-and-implementation lane per accepted D-2 —
parallel to the WP6.1+WP6.3 → WP6.4 → Gate 6 path, never on it. RM completion is not a
Gate 6 criterion and Gate 6 does not wait for RM. Exception: RM-01 Task A repairs a
WP6.1 currency gap on the main path under its own decision entry (P-043); it is hosted
here for scheduling convenience only and its acceptance is recorded against WP6.1.
**Naming rule (accepted D-3):** every artifact in this lane is provider-neutral. The
Woodruff et al. Gemini paper is cited as *evidence lineage* for method assets, never as a
provider dependency. No file, schema `$id`, CLI flag, or identifier in this lane may name
a model provider.

---

## 1. Lane charter

Import the research-method patterns evidenced in *Accelerating Scientific Research with
Gemini* (Woodruff et al.) into ARS as typed, versioned, reviewable artifacts, operating
entirely inside the P-042 owner-operated-session regime:

- ARS **compiles and records** bounded research briefs (export);
- the **operator** runs the external model session in an application of their choice;
- ARS **imports** returned material fail-closed into typed, append-only records that sit
  strictly below result acceptance and claim promotion;
- ARS **executes** model-proposed verification code itself (the one half of the paper's
  neuro-symbolic loop ARS is authorized to automate) and binds results to candidates.

The core is STEM-generic. TDA/Markov material appears only as pilot fixtures and in the
existing W5 domain-pack layer, consistent with the open-source posture.

## 2. Plan suite and dependency order

| Plan | Scope | Depends on | Branch prefix |
|---|---|---|---|
| [rm-01-unblock-and-suite-recovery-plan.md](rm-01-unblock-and-suite-recovery-plan.md) | WP6.1 producer-emits repair (P-043), full-suite failure inventory, coverage/lint accounting, append-path smoke gate | P-043 accepted; handoff-26 Defect 1–2 fixes landed (external, in flight) | `pipe/rm-01-*` |
| [rm-02-research-methods-pack-plan.md](rm-02-research-methods-pack-plan.md) | Methods Pack v1: manifest schema, five method assets, registry binding, negative controls | P-044 accepted; no code-path dependency on RM-01 | `pipe/rm-02-*` |
| [rm-03-brief-export-import-plan.md](rm-03-brief-export-import-plan.md) | `ars brief export` / `ars brief import`, import schemas, typed landing, P-042 negative controls | RM-01 (green append path) AND RM-02 (assets to export) | `pipe/rm-03-*` |
| [rm-04-verification-execution-and-manuscript-review-plan.md](rm-04-verification-execution-and-manuscript-review-plan.md) | `ars brief verify` execution lane, round-trip support, manuscript-review lane, one pilot | RM-03 | `pipe/rm-04-*` |

Permitted parallelism: RM-01 and RM-02 may run concurrently (disjoint file sets — see
each plan's file map; the only shared file is `research_system/cli.py`, which RM-01 and
RM-02 do not touch; only RM-03/RM-04 touch it, and they are serialized).

## 3. Gate checklist (owner touchpoints, hoisted from all child plans)

Per writing-plans-extras, every owner precondition in a child plan is listed here; the
acceptance runner works from this table, not from child prose.

| Gate | What Stephen must do | Blocks | Source |
|---|---|---|---|
| G-RM-1 | Accept P-043 (producer emits `command_schema_*`) | RM-01 Task A | proposals/rm-decision-entry-drafts §P-043; handoff 26 Defect 3 |
| G-RM-2 | Accept P-044 (lane creation, scope, boundary) | all RM dispatches | proposals/rm-decision-entry-drafts §P-044; P-042 boundary clause ("plan and dependency correction only") |
| G-RM-3 | Accept the adversarial review disposition of this suite (each plan individually reviewable; zero unresolved Critical) | dispatch of the reviewed plan | folder change discipline; house review-then-dispatch practice |
| G-RM-4 | Accept Methods Pack assets (procedural memory `candidate -> reviewed -> accepted`; only `accepted` assets are exportable by default) | RM-02 close-out; RM-03 pilot export | W3 §13.1–13.2 lifecycle |
| G-RM-5 | Choose the pilot brief subjects for RM-04 (suggested: one P01 draft section for the review lane; one Markov-ladder conjecture-shaped claim for the counterexample lane) | RM-04 Task 4 | Stephen's steer: TDA as testbed, not definition |
| G-RM-6 | Confirm CI/smoke-gate wiring location for the append-path smoke (quality-gate command list vs `.githooks`) | RM-01 Task D close-out | observer log Observation 137; `.githooks` discipline in `.claude/CLAUDE.md` |

## 4. Master obligation register

Forward-obligation scan run against: P-042 (03-decisions §P-042), W3 (design/03), W5
(design/05), WP6.3 acceptance (handoffs/25), handoff 26, README governing constraints,
CLAUDE.md/APM_RULES, CONVENTIONS.md-relevant working rules. Dispositions:

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| O-RM-1 | P-042 decision text | ARS must not invoke a provider, spawn a provider CLI, make a provider API call, select a provider for the user, or read/store/resolve/pass OAuth credentials | Global constraint in every plan; mechanical negative control in RM-03 Task 5 (no-provider-import guard test) |
| O-RM-2 | P-042 boundary clause | P-042 authorizes plan/dependency correction only; implementation needs a new owner decision | P-044 draft; gate G-RM-2 |
| O-RM-3 | P-042 decision text | Operator-mediated workflow must record operator, chosen application/session, exact subjects, artifacts, and returned evidence | RM-03 import schema mandatory session-metadata block; RM-03 Task 3 negative controls |
| O-RM-4 | W5 §19.3 | Claim promotion requires Stephen's attributed P-005 decision; nothing else is promotion authority | Import types carry closed `status` enums with no accepted/promoted member; RM-03 Task 4 negative control; RM-04 verify command writes verification evidence only |
| O-RM-5 | W5 §17 | Two-key validity: no operational success or schema pass compensates for a failed required key | RM-04 constraint: a passing `VerificationResult` never auto-accepts a result |
| O-RM-6 | W3 §15 / §9 | Secrets, raw restricted data, full transcripts, hidden reasoning prohibited from reusable packets and manifests | Import schemas `additionalProperties: false` + explicit forbidden-field negative tests (RM-03 Task 4); export prohibitions block (RM-03 Task 2) |
| O-RM-7 | W3 §13.2 | Procedural memory carries name, version/hash, source path, applicability trigger, compatibility, dependencies, supersession, review state | RM-02 manifest schema fields; contract test |
| O-RM-8 | W3 §13.1 lifecycle | Memory assets: `candidate -> reviewed -> accepted`; non-accepted excluded from governing use | RM-02 Task 3; exporter default filter (RM-03 Task 2); gate G-RM-4 |
| O-RM-9 | handoffs/25 + handoff 26 "Do not touch" | `wp6-3-tdl-private-assurance-pack.yaml` and its schema are owner-accepted exact bytes at `449b0d00` | Do-not-touch list in every plan |
| O-RM-10 | handoff 26 | Defects 1–2 are assigned to an in-flight agent in `schema_registry.py`; two agents in one file will conflict | RM-01 excludes `schema_registry.py`; RM-01 Task B blocked until that work lands |
| O-RM-11 | handoff 26 Defect 3 | Direction decision required: producer emits vs schema relax | P-043 (producer emits, accepted-in-principle 2026-07-28, formal entry pending); RM-01 Task A |
| O-RM-12 | APM_RULES vault discipline | Every task ends with the matching vault entry, top-of-page reverse-chronological | Close-out step in every plan (`[PIPELINE]` → Pipeline-Overview + Computational-Log per mapping) |
| O-RM-13 | Working rules (CLAUDE.md, memory) | `[PIPELINE] P00:` commit subjects, Co-Authored-By trailer, BOM-free `git commit -F` files, never `--no-verify`, worktree `.env` copy, review-then-merge with CodeRabbit concluded | Global constraints in every plan |
| O-RM-14 | D-3 acceptance | Provider-neutral naming everywhere | Naming rule above; adversarial-review question for every plan |
| O-RM-15 | Report-2 rollback semantics | Rollback = disable commands / mark pack ineligible; imported artifacts remain immutable and are superseded, never deleted | RM-03/RM-04 architecture constraint |
| O-RM-16 | W2 append-only discipline | Imported material lands as append-only typed records, replayable | RM-03 Task 3 (`MethodBriefRecorded` / `MethodResultImported` events); replay check |
| O-RM-17 | Track 3 deferrals (analysis doc §3) | Direct provider adapter, Lean-lane expansion, TDA-on-proof-states, sheaf consistency, remote MCP, fine-tuning: all deferred with named next gates | §6 below |
| O-RM-18 | Observer log Obs. 136 | README/status drift risk when acceptance records land | RM-01/… close-out steps update the folder README row for this lane in the same PR as each acceptance |

## 5. Standing constraints (inherited by every RM plan)

1. **Worktree isolation.** Each task branches from current approved `main` into a
   worktree under `.apm/worktrees/`; immediately copy `C:/Users/steph/TDL/.env` into the
   worktree. Worker commits and reports; merges happen only after review.
2. **Review-then-merge.** CodeRabbit must conclude on the PR before merge; never
   fast-forward a local merge onto `main` (memory: PR #54 incident).
3. **Environment.** Until RM-01 Task B confirms `uv run` health in fresh worktrees, use
   the direct interpreter invocation from handoff 26 for pytest:
   `C:/Users/steph/TDL/.venv/Scripts/python.exe -m pytest -q <target> -o "addopts=" -p no:cacheprovider -p no:cov`.
   Budget test time using handoff 26's measurements; a silent 11-minute first progress
   line is normal for large slices.
4. **Do not touch, any plan:** `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`,
   `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`
   (owner-accepted exact bytes); `.research-system/schemas/wp6-2-*/**` (accepted T2
   family); anything under `docs/plans/agentic-research-system/reviews/` or `handoffs/`
   (immutable provenance).
5. **Skills for implementing Workers:** `contract-first-tdd`,
   `research-assurance-triage`, `executing-plans-extras`. One failing public-seam test
   before each production change.
6. **Assurance lanes.** All RM work is Output/Provenance lane only; no mathematical,
   statistical, topological, or representation logic is created or altered. Any task
   that finds itself editing such logic stops Partial.
7. **Stop-Partial rule.** If a plan's stated interface proves wrong against live code
   (e.g., the ledger append seam differs from the file map), the Worker stops Partial
   and reports the discrepancy; plans are corrected by revision, not improvised around.

## 6. Deferred items (owner and next gate named; not silently dropped)

| Item | Owner | Next gate |
|---|---|---|
| Direct provider adapter (any provider) | Stephen | New owner decision superseding the relevant part of P-042, then W4 eligibility evidence + W7 parity + W6 calibration; report 2's adapter/privacy design is the reference input |
| Lean/formalization bridge expansion (proof obligations from W5 typed claims) | Stephen | After RM-04 pilot evidence shows which claims merit formalization; builds on `design/05a` evidence class + `lean-proof` skill |
| TDA-on-proof-state trajectories; sheaf-theoretic claim consistency | Stephen (Discovery Harness) | `/assay` scorecard; PROMOTE required before any spike |
| Remote MCP exposure; fine-tuning/distillation | Stephen | Out of first-release scope (W1); legal/governance review required first |

## 7. Success criteria

- RM-01: `tests/research_system` completes affordably with a recorded full inventory;
  the append path validates against the generated event schemas; coverage/lint
  accounting includes `research_system`; the smoke gate demonstrably fails on a seeded
  producer/schema divergence (negative control).
- RM-02: five accepted method assets with complete W3 §13.2 metadata; manifest
  contract test green including all negative controls.
- RM-03: a brief exported for a real task validates against its schema; a conforming
  import lands as replayable events; every negative control (bad hash, missing session
  metadata, forbidden field, status-escalation, provider-import guard) is red-then-green.
- RM-04: one operator-run pilot round trip completed on a Stephen-chosen subject with a
  `VerificationResult` bound to an imported candidate, and one manuscript-review
  `ReviewFindingSet` imported against a draft's exact subject hash — with no claim,
  result acceptance, or lifecycle transition performed by any RM component.
