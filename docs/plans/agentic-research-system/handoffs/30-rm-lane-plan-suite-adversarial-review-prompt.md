# RM Lane Plan-Suite Adversarial Review (G-RM-3) — Agent Prompt

**Created:** 2026-07-29
**Purpose:** Self-contained brief for the independent adversarial review that gate
G-RM-3 requires before any RM plan may be dispatched. Paste this file (or point a
fresh agent at it) as the opening instruction of a new session. Retained in
`handoffs/` as review provenance.
**Routing guidance (house policy):** fresh context, no access to the authoring
session; cross-family reviewer preferred (Codex xhigh or equivalent) per D-006/P-029.
Under P-042 the operator starts the external session and chooses the application.
If the repository's `adversarial-design-review` skill is available in your session,
load it before starting.

---

## Your role

You are the independent adversarial reviewer for the ARS Research Methods (RM) plan
suite. You did not author it. Your job is to attack it for material errors, authority
leaks, unenforceable claims, missing controls, factual claims about the live tree that
do not hold, and cross-document inconsistencies — and to deliver a severity-graded
findings report with a complete disposition table. Findings produce **revision or
stop** recommendations; they never weaken an acceptance set.

**Process context you must know:** the suite was merged to `main` as PROPOSED
planning material (PRs #177, #185) without an implementation gate. Merging was
deliberate — the documents are records, not authorizations. Your verdict governs
whether RM-01..RM-04 may be **dispatched for execution as written**. The merge is not
evidence of correctness, and the authoring agent's confidence is not evidence of
anything.

**A specific caution about this suite's provenance.** Two of its inputs are external
deep-research reports produced with no repository access and partial repository
access respectively. The authoring agent claims to have adversarially reviewed both
and discarded their unsupported conclusions. Verify that quarantine held: any plan
requirement whose only support traces to one of those reports, rather than to the
repository or an accepted specification, is a finding.

## Review subject (exact)

Review these files at `origin/main` commit `6e7d0e0` with the exact blob identities
below. If `main` has advanced in a way that touches these files, record the drift as
your first finding and review the current state.

| File | Blob |
|---|---|
| `implementation/rm-00-research-methods-lane-master-plan.md` | `911243b773a906a1cc9f92af0631d2251cd7e1ee` |
| `implementation/rm-01-unblock-and-suite-recovery-plan.md` | `652bcf24ad21bbc24e6c3d57162d1ba7d1891fbf` |
| `implementation/rm-02-research-methods-pack-plan.md` | `fb2478f103206a6df0da6e64ea3a8191e19b5ba1` |
| `implementation/rm-03-brief-export-import-plan.md` | `0126fd2d5f6f19cb811f2c1d4f61f491af10cddd` |
| `implementation/rm-04-verification-execution-and-manuscript-review-plan.md` | `55ffae966715d547eefbbccf6668a07378ab2eda` |
| `proposals/research-methods-integration-plan-2026-07-28.md` | `15de3b81f9ab0ab17ff0cc13a18166f9c13e911f` |
| `proposals/rm-decision-entry-drafts-2026-07-28.md` | `9141f6887d532ecbc71b48f0169c8845130dfd12` |

Also in scope, **as rendering checks only**: `03-decisions-and-open-questions.md`
§P-043 and §P-044 (are they protocol-complete, and does the suite render them
faithfully?).

Each plan is separately dispatchable. Your verdict must therefore be **per plan**, not
only for the suite as a whole.

## Fixed ground (do not re-litigate)

- Accepted designs W1–W8, decisions P-001–P-042, and the Gate 3/4/5 review record.
  These are the measuring stick, not the subject.
- Stephen's accepted decisions **P-043** (WP6.1 currency resolved producer-side;
  generated event schemas not relaxed) and **P-044** (RM lane creation; provider-
  neutral naming; independent lane). Attack the suite's **implementation** of these
  decisions — gaps, contradictions, unenforceable renderings, boundary drift — not the
  decisions themselves.
- P-042's owner-operated-session regime. That ARS must not invoke providers is
  settled; whether this suite's mechanisms actually enforce it is squarely in scope.
- The WP6.3 exact-byte acceptance at `449b0d00` (handoff 25) and the do-not-touch
  lists that follow from it.

## Governing references (read before attacking)

- `03-decisions-and-open-questions.md` §P-042, §P-043, §P-044.
- W3 `design/03-context-memory-and-retrieval.md` — §9 packet/manifest, §13.1–13.2
  memory identity and lifecycle, §15 security/privacy/retention.
- W5 `design/05-research-assurance-and-independent-review.md` — §16 review,
  §17 two-key validity, §18 Partial/negative/rejected/superseded, §19 result
  acceptance and claim promotion.
- W2 `design/02-task-event-and-artifact-schema.md` — event/artifact identity and
  deterministic replay.
- `handoffs/26-research-system-suite-red-briefing.md` (defect briefing) and
  `handoffs/28-research-system-suite-baseline-inventory.md` (measured baseline).
- `reviews/adversarial-wp6-plan-suite-remediation-r3-review-2026-07-17.md` and
  `reviews/adversarial-gate5-foundation-review-2026-07-16.md` — the depth and format
  bar.
- Source of the method assets: `TDA-Research/01-Literature/Research Papers/Gemini For
  Research.md`, §§2.1–2.8 and §9.2 (for asset-fidelity checks in surface 8).

## Attack surface (work through all twelve; report null results explicitly)

1. **P-042 boundary integrity, and whether the guard is real.** RM-03 Task 5 proposes
   a denylist-based "no provider surface" test as the mechanical enforcement of
   P-042. A denylist is an open-world control: attack it. Can the boundary be crossed
   without tripping it (indirect import, `importlib`, a subprocess, a dependency that
   itself calls out, an MCP or tool seam, a config-driven URL)? Is a denylist the
   right rung on the enforcement ladder, or does this need an allowlist/interface
   constraint? Separately: does any prose anywhere in the suite authorize, presume, or
   drift toward provider invocation?
2. **The claim-promotion firewall.** RM-03 asserts that closed status enums make
   escalation "structurally unrepresentable, not merely forbidden". Test that claim end
   to end. Can an imported artifact reach a promoted claim without Stephen's P-005
   decision — by being referenced as evidence in a later record, by a projection that
   reclassifies it, by supersession, or by a consumer that reads `status` loosely? Is
   the W5 §19 boundary preserved in fact or only in the schema?
3. **Owner-touchpoint hoisting (the Observation-76 pattern).** Diff rm-00 §3's
   G-RM-1..G-RM-6 checklist against every owner-gated precondition stated anywhere in
   RM-01..RM-04 prose ("owner-gated", "Stephen chooses/accepts", "owner decision
   point"). Any precondition living only in child prose is an authority leak even if
   each child is individually sound. R1-3b (the `receipt-v2` enumeration decision) was
   added late — check it is hoisted.
4. **Independent forward-obligation scan.** Re-run the scan yourself against P-042,
   W3, W5, W2, handoffs 25/26/28, and the README governing constraints. Compare your
   hits to rm-00 §4's 18-row register. Report every obligation the register misses,
   mis-attributes, or disposes of without a named owner and next gate. Also check
   §6's deferrals: does each name an owner *and* a next gate, as
   `writing-plans-extras` requires?
5. **Lane-independence coherence.** P-044 and rm-00 claim RM is never on the Gate 6
   critical path, yet RM-01 Task A repairs a WP6.1 main-path defect and RM-01 is
   hosted in the lane "for scheduling convenience". Attack that arrangement: does it
   smuggle main-path work into an independent lane, confuse acceptance authority
   (rm-01 says its acceptance is recorded against WP6.1, not RM), or create a Gate 6
   dependency the master plan denies?
6. **RM-01 seam and P-043 implementability — verify in source.** The file map is
   declared "expected". Verify against `research_system/` that (a) the event envelope
   is assembled where the plan says (`CommandService.submit` → `ledger.append`), and
   (b) **the byte-exact hash requirement is achievable**: does the schema registry
   retain the exact validated schema *bytes*, or only a parsed object? If it does not
   retain bytes, P-043's byte-exact clause as rendered in the register and RM-01 is
   unimplementable as written — a Critical finding, not a nitpick. Also check whether
   a single derivation point exists that every producing path flows through, or
   whether the "sweep every call site" instruction implies an unbounded change.
7. **Baseline currency and the delta prediction.** RM-01 Task B is stated against
   handoff 28's baseline (tree `97f447f`, 1515 tests, 156 Defect-3 cases). `main` has
   advanced since (at least PRs #184, #187 and the #185 merge). Is the baseline still
   the right comparator, and is the "all 156 move together" prediction sound or
   over-confident? Verify the two non-Defect-3 cases still exist as described, and
   that the signature-guard pre-step (R1-3a) is correctly ordered relative to Task A.
8. **Method-asset fidelity and neutrality (RM-02).** Against the source paper
   §§2.1–2.8 and §9.2: do the five specified assets faithfully capture the protocols
   they cite, or do they flatten them? In particular the adversarial-review protocol's
   self-critique stage, the neutral prove-or-refute framing as an *anti-confirmation-
   bias* control, and the de-identification transform's provenance sidecar. Then check
   D-3 compliance mechanically: grep the suite for provider names outside lineage
   citations. Are the assets genuinely STEM-generic, or is TDA load-bearing anywhere it
   should be exemplary?
9. **RM-04 execution honesty and control adequacy.** The plan disclaims sandboxing
   and bounds execution by wall-time, declared scratch root, and a recorded approver.
   Attack that: is `approved_for_execution_by` a real control or self-attestation? Is
   executing model-proposed code under these bounds acceptable in this repository's
   threat model, given the runner sits inside a research tree with credentials in
   `.env` and gitignored data at `PROJ_ROOT`? Say plainly whether the honest
   disclaimer is sufficient or whether a real isolation requirement is missing.
10. **Binding-test and negative-control adequacy.** For every machine-checkable claim
    in each plan's "Research assurance requirements" and every listed negative
    control: is it an enforcement artifact by the CONVENTIONS locks (value-and-type,
    atomic rejection, fail-closed) rather than a description? Name each test that
    could pass while the claimed property fails. Does every new gate ship a negative
    control proving it can fire (invariant I2b)?
11. **Cross-plan interface consistency.** RM-03 reserves `verification_context` for
    RM-04's use "so RM-04 does not bump the schema" — do the two plans' field
    specifications actually agree? Check the import-type names, `$id` conventions, and
    event names for drift across rm-00/RM-03/RM-04. Verify the claimed RM-01 ∥ RM-02
    parallelism (disjoint file sets) and the dependency edges in rm-00 §2. Check
    RM-03's schema-family placement claim (`ars://methods/...` outside
    `schemas/core/events/`) against how the ledger actually routes validation — if
    core-family placement is mandatory, RM-03's architecture is broken.
12. **Assurance-lane classification.** Every plan declares Output/Provenance only.
    Test that: does RM-04's manuscript-review lane touch paper-claim logic? Does
    RM-02's asset content constitute methodological guidance requiring a different
    lane? Does anything require a `contracts/` entry that the suite declines to
    author, and is the declination reasoned?

## Verification obligations

- Every finding cites file and line and quotes the live text; verify against the
  working tree, never from memory or this prompt.
- Claims about the implemented foundation (surfaces 1, 2, 6, 11) are verified in
  `research_system/` source, not inferred from plan prose. A plan's factual assertion
  about the code that does not hold is at minimum Major.
- A referenced artifact that does not exist where the suite says it does is a
  finding, not a guess.
- Research-assurance lanes: declare them (expected: Output/Provenance primary).

## Constraints

- Read-only except your review report. Do not edit the reviewed files, do not
  implement anything, do not run research computation, do not dispatch anything.
- Environment (per handoff 28): a fresh worktree `.venv` is an empty stub and the
  main-repo interpreter lacks `jsonschema`. If you need to run tests, provision with
  `uv sync --all-extras --no-install-package petls`, then `uv run --no-sync`. Do not
  pipe long runs through `tail`. You are unlikely to need a full suite run; the
  baseline already exists in handoff 28.
- Do not touch `.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`,
  its schema, or `.research-system/schemas/wp6-2-*/**` — owner-accepted exact bytes.
- Do not consult or reconstruct the authoring session's reasoning; the documents
  stand or fall as written.

## Output contract

Write `docs/plans/agentic-research-system/reviews/adversarial-rm-lane-plan-suite-review-<YYYY-MM-DD>.md` containing:

1. **Header:** review date, reviewed commit and blob identities as you recomputed
   them, reviewer identity/family/context basis (state independence honestly per
   P-022).
2. **Findings**, severity-graded per house convention — Critical (C-n), Major (M-n),
   Minor (m-n), Informational (i-n) — each with: location, quoted evidence, why it is
   a defect, and the exact required change or stop.
3. **Attack-surface disposition table:** all twelve surfaces with outcome
   (findings | clean) — null results stated, not implied.
4. **Decision disposition:** for P-042, P-043, P-044 and gates G-RM-1..G-RM-6,
   whether the suite renders each faithfully.
5. **Per-plan verdict:** for each of RM-00, RM-01, RM-02, RM-03, RM-04 —
   `accept` | `accept_with_required_changes` | `reject` — with the exact condition set
   that must clear before that plan may be dispatched. A plan may be dispatchable
   while others are not; say so explicitly if that is your finding.

Do not soften findings because the suite is already merged, because the decisions are
already accepted, or because the lane is described as low-risk. Planning documents
that read well are the ones that hide unenforceable claims.
