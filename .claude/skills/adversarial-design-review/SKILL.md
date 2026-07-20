---
name: adversarial-design-review
description: Use when conducting an independent adversarial review of a design document, specification, plan, or proposal — to attack it for material errors, unsupported or circular evidence, missing controls, untestable interfaces, and cross-spec inconsistencies, and to produce a severity-graded findings report with a complete decision disposition. Trigger on a review gate, design sign-off, or "attack this plan / spec / design."
---

# Adversarial Design Review

Use this to review a *design / specification / plan / proposal document* adversarially —
not a computational result (that is `research-assurance-triage` and the lane audits) and
not prose quality (`humanizer`). It also covers a *committed implementation* reviewed
against its accepted plan/spec: treat the code as the artefact and the plan's claims as
citations to verify against it (Lane 1). The purpose is to *break* the design where
evidence supports it, while preserving an auditable distinction between factual
corrections, proposed amendments, decisions that belong to the owner, and work deferred
to later packages. Refine where warranted; do not rubber-stamp, and do not manufacture
findings.

## Core Rule

Work from fresh context against **direct evidence**. Do not rely on the document's own
summaries, a tracker, or a prior agent's conclusions without checking the cited files. A
finding must cross a trust boundary or violate a stated invariant — not merely be a
speculative possibility. If the strongest attack fails, show *why* it fails rather than
inflating a Minor into a Major.

## Independence and Authority (fix before starting)

- Identify which decisions are owner-approved — challenge those only with concrete
  contrary evidence **plus** an identified failure **plus** a proposed superseding
  decision — versus which are open.
- You MAY directly fix broken links, malformed markup, and unambiguous factual errors
  *after recording them in the report*. PROPOSE — never silently rewrite — any material
  governance, authority, lifecycle, storage, migration, or scientific-assurance change.
- Preserve unrelated working-tree changes; touch only the review deliverable and
  in-scope trivial fixes. Never enact an owner-reserved decision or authorize
  implementation.

## Review Lanes

1. **Evidence fidelity.** For each major diagnosis and preserved mechanism, test whether
   direct evidence supports it. Flag: stale or circular citations; a conclusion drawn
   only from a summary/tracker; a claim the cited source does not actually support; a
   citation to a *named* source (observation, paper, standard) that says something else;
   a historical case generalised beyond its evidence. **Verify the provenance of supplied
   "framing"/"reference" sources** (author, venue, date, authority class) — a source's
   weight is what it *is*, not what the prompt calls it.
   For external scanners, fetch the actual rule-and-line annotations (or exported
   findings) and map them to current HEAD before prescribing a suppression. If that
   evidence is inaccessible, label the disposition provisional rather than inferring
   exact findings from source inspection.
   **Implementation-conformance mode:** when the subject is code reviewed against an
   accepted plan/spec, enumerate every control/step/ordering the governing prose claims
   and bind each to the line that implements it — an unimplemented or subset-implemented
   claim is a finding even when all tests pass (tests exercise present behaviour, not
   absent controls). Check for schemas/contracts that are defined but unenforced
   (registered, validated by nothing). Green tests and clean lint prove the code does
   what it does, never that it does what the plan promised.
   **Remediation re-review:** when re-reviewing a prior finding's fix, bind the
   disposition's *prescribed mechanism* (the disposition text, e.g. "re-derive X from
   Y") to code lines — not to whether the original proof-of-concept still reproduces. A
   remediation can remove the PoC's vehicle (block the input, delete the test case)
   while leaving the underlying invariant violated one level down, and can even encode
   the removed vehicle as a regression test so a superficial fix reads as covered.
   Separately, for every strict validator/comparison, trace where both the expected
   side and the observed side get their values — if the same function populates both,
   the check certifies the producer against itself regardless of how strict it looks.
2. **Per-component / per-section attack.** For each component or claim: does it have one
   responsibility; is the chosen mechanism actually simpler than the alternative it
   rejects; what are the concurrency, platform (Windows/filesystem), multi-worktree, and
   failure-mode counterexamples; can a guarantee be defeated by an actor the design does
   not control (a legacy or external writer, a degenerate fallback, a correlated reviewer)?
   Also attack inward, not just outward:
   - **Restatement-diff.** When an invariant is stated more than once, collect *all* of
     its restatements across the document and flag any that add a scope/tier/severity
     qualifier the others lack — the narrowest restatement is the de facto rule; confirm
     the narrowing is intended and consistent with the fixtures that test the invariant.
     A tier-qualifier dropped into a detail section is a more common authority leak than
     any external actor.
   - **Foundation.** For every protected process (verify/accept/promote), find the object
     that defines its acceptance bar (the requirement, floor, scope, classification) and
     check whether its author/acceptor is required to be independent of the producer —
     self-*definition* of the bar is a more common bypass than self-*approval* of the
     result.
   - **Ordering.** For every relationship-property gate (independence, freshness,
     diversity, feasibility), check it is proven *before* the expensive/irreversible step
     it governs, not deferred to a later routing/review stage where failure wastes
     completed work.
3. **Cross-spec consistency matrix.** Build *invariant → enforcement point → test*. Flag
   any invariant with no enforcement, any critical mechanism with no test, any test
   requiring a record the schema does not define, and inconsistent terms / identifiers /
   authorities / paths across documents. **Integration/manifest pass:** when a document
   claims to reconcile other specs, attack it first and hardest — resolve every identity/
   field it lists back to a defining section in an owning spec (an unresolved or
   differently-named binding is a finding); diff every field it re-defines against the
   owner's definition (divergence is a finding even when each doc is internally
   consistent alone); trace each participant through its ordering/dependency chain for a
   multi-stage participant linearized into one step (hiding an upstream dependency or
   creating temporal inversion). The document that promises the pieces fit is the one
   most likely not to — it restates every identity, field, and ordering it touches, so it
   carries the highest drift risk in the set. Also:
   - check dimensional consistency across counters and limits; do not compare values
     produced by different tokenizers or units without separate gates or a validated
     conversion / conservative bound;
   - compare prose algorithms, state machines, and failure tables for lifecycle-order
     inversions;
   - before declaring an identifier undefined, search the owning catalogue for exact and
     semantic variants, classify it as undefined / differently named / multiply defined,
     and quote the owner entry before proposing a new identity;
   - derive every required evidence set from its owning contract and attack empty,
     partial, stale-revision, duplicate, extra, and incompatible sets. A gate passes only
     on exact required-set closure, not merely because all supplied evidence passed.
4. **Currency.** If the document is a dated snapshot, check live state read-only and
   record divergences as a **proposed dated addendum** — never rewrite the snapshot. Do
   not use active or no-migration work as an experiment. When the artifact set is
   byte-hash-bound and tracked (fixture manifests, frozen caches), run the acceptance
   validation in BOTH a fresh worktree/clone AND the canonical working tree the owner
   will actually use — a post-hoc eol/text attribute (`.gitattributes`) never
   renormalizes already-checked-out files, so a hash-bound corpus can pass in every
   fresh clone and silently fail on `main` while `git status` shows nothing.
   Divergence between the two trees is itself a finding. Do not trust `grep` for
   `\r`/CRLF detection on Windows/MSYS (it treats CRLF as a normal line ending) —
   check bytes directly.
5. **Practicality / proportionality.** Estimate overhead per risk tier / workload class
   (mechanical, implementation, claim-level, long-running, non-core-domain, qualitative).
   Look for bureaucracy that will be bypassed; recommend the smallest control that
   addresses each observed risk.

## Severity Rubric

- **Critical** — can corrupt authority/evidence, permit invalid acceptance, leak
  restricted data, or make deterministic recovery impossible.
- **Major** — material ambiguity, missing control, untestable interface, likely
  operational bypass, or unjustified architecture commitment.
- **Minor** — local inconsistency, clarity/naming, or useful hardening that does not
  change direction.

## Finding Standard (every finding carries all eight)

1. ID + severity. 2. Claim stated precisely. 3. Evidence with file path + line/section.
4. Concrete failure scenario. 5. Impact (validity / operations / migration /
generalizability). 6. Recommended disposition (fix now / amend decision / defer with
dependency / reject / accept risk). 7. Exact proposed text or interface change where
feasible. 8. Affected decisions and work packages.

## Completeness Gate (re-read before delivering)

Re-read the document's decision register, invariant list, and any fixture/test catalogue,
and confirm **every** decision, invariant, and test has an explicit disposition. The
review is not complete until each does. Keep a change log inside the report; list any
files edited with verification evidence.

## Output Format

A report written to a `reviews/` path (never overwrite the reviewed documents) with:
executive verdict (`accept` / `accept_with_required_changes` / `rework_required`);
Critical/Major findings ordered by severity and dependency; Minor + editorial
corrections; decision audit (keep / amend / reject / defer per decision); the consistency
matrix; coverage/fixture gaps; practicality assessment; a revision plan split into
immediate corrections / owner decisions / later-work dependencies; residual risks; and
verification evidence for any edits.

## Escalate Or Stop When

- A proposed change would reverse an owner-approved decision, alter human authority,
  migrate evidence, or authorize implementation — stop and ask the owner.
- Source evidence is missing, contradictory, or inaccessible — report Partial; do not
  fill gaps by inference.
- Live state differs from a dated snapshot — propose a dated addendum, do not rewrite.

## Pressure Scenario From This Repo

- ARS first-pass review (2026-06-29): the deepest finding was a git-tracked JSONL ledger
  vs. a single global event position under a pervasive multi-worktree model — a Major
  that turns Critical only if implemented naively. Two "framing" PDFs proved to be
  third-party vendor whitepapers, not project notes; a schema proposal cited
  "Observation 7" for a principle that observation did not state; and the dated W0
  snapshot was stale (a cited merge commit had been reverted; the "prepared" task was
  actually running). Each was caught only by checking the cited source directly.
- Later ARS rounds (2026-06-30 – 2026-07-01) confirmed the deepest finding is never in the
  mechanism the document defends: a W3 restatement-diff caught a §13.3 tier-qualifier
  that silently reopened an otherwise-unconditional guarantee; a W4/W5 review found the
  requirement that *seeds* two-key validity was unguarded (self-definition of the risk
  floor, not self-approval of the result) and an independence gate proven too late to
  matter; a Gate-3 review of a `06c` integration manifest found all three Majors in the
  manifest itself (a linearized two-stage dependency, a redefined shared field, drifted
  identifiers); and a code-vs-plan review of a committed implementation found the one P1
  in an all-green, ruff-clean package was a claimed control (W2 §8.2 step 4) the code
  silently never implemented.
- A seventh review (2026-07-07) of a remediation rebuild found the vehicle-removal
  pattern: a prior Critical ("release gate certifies producer-supplied verdicts")
  was closed by making the release CLI ignore the flagged input entirely and
  synthesize verdicts in-process, with a new regression test asserting only a
  type check — the invariant stayed violated one level down. The same review found
  a hash-bound fixture corpus that passed in every fresh worktree but failed on the
  canonical `main` tree, because a `.gitattributes` eol rule added after checkout
  never renormalized the already-checked-out files; MSYS `grep` could not detect
  the CRLF bytes that a Python bytes check confirmed.

## Related Skills

- `research-assurance-triage` (validity of a *result/claim*, not a design document),
  `result-provenance-review` (provenance of result files), `humanizer` (prose quality).
- `pre-reg-to-dispatch` when a reviewed-and-accepted decision must become an executable task.
## Exact-authority and lifecycle stress tests

- Bind validation to an exact commit. Compare reported, local, remote PR, and check-run heads; any later commit requires focused re-review and execution.
- For partial cutovers, enumerate path-level owners for old and new surfaces and reject overlap or unowned gaps.
- Topologically order gates and producers. An early owner gate cannot require evidence that only a downstream accepted action can create.
- For exact sets, bind complete row identity and test cross-record joins: allowlist membership, discriminants, effect-to-projection targets, and class-specific producer/owner enums.
- Reject expected authorities copied from the implementation under test or deferred semantic copies lacking independent provenance.
- In read-only pytest reviews, disable repository coverage and other write-producing plugins explicitly.
- Draw hash dependencies as a directed graph; reject self-edges and strongly connected components without a specified non-hashed indirection or staged identity.
- For cancel, Partial, and failure edges, enumerate live proposals, requests, attempts, leases, grants, and locks; require each to close, supersede, or be deliberately preserved before the next command.
- When testing uncommitted bytes under Windows checkout filters, stage only scoped files in a disposable clone, rematerialize them from its index, and confirm CRLF bytes were actually produced before crediting portability.
