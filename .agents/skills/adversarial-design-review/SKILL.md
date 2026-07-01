---
name: adversarial-design-review
description: Use when conducting an independent adversarial review of a design document, specification, plan, or proposal — to attack it for material errors, unsupported or circular evidence, missing controls, untestable interfaces, and cross-spec inconsistencies, and to produce a severity-graded findings report with a complete decision disposition. Trigger on a review gate, design sign-off, or "attack this plan / spec / design."
---

# Adversarial Design Review

Use this to review a *design / specification / plan / proposal document* adversarially —
not a computational result (that is `research-assurance-triage` and the lane audits) and
not prose quality (`humanizer`). The purpose is to *break* the design where evidence
supports it, while preserving an auditable distinction between factual corrections,
proposed amendments, decisions that belong to the owner, and work deferred to later
packages. Refine where warranted; do not rubber-stamp, and do not manufacture findings.

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
2. **Per-component / per-section attack.** For each component or claim: does it have one
   responsibility; is the chosen mechanism actually simpler than the alternative it
   rejects; what are the concurrency, platform (Windows/filesystem), multi-worktree, and
   failure-mode counterexamples; can a guarantee be defeated by an actor the design does
   not control (a legacy or external writer, a degenerate fallback, a correlated reviewer)?
3. **Cross-spec consistency matrix.** Build *invariant → enforcement point → test*. Flag
   any invariant with no enforcement, any critical mechanism with no test, any test
   requiring a record the schema does not define, and inconsistent terms / identifiers /
   authorities / paths across documents.
4. **Currency.** If the document is a dated snapshot, check live state read-only and
   record divergences as a **proposed dated addendum** — never rewrite the snapshot. Do
   not use active or no-migration work as an experiment.
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

## Related Skills

- `research-assurance-triage` (validity of a *result/claim*, not a design document),
  `result-provenance-review` (provenance of result files), `humanizer` (prose quality).
- `pre-reg-to-dispatch` when a reviewed-and-accepted decision must become an executable task.
