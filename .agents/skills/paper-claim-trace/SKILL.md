---
name: paper-claim-trace
description: Use when turning TDL results into manuscript claims, table entries, figure captions, discussion prose, limitations, or disclosure text — to bind every claim to a result file and decision rule and to keep negative/weaker results honestly reported.
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - paper-claim
  roles:
    - claim-reviewer
    - verifier
  runtime: agnostic
---

# Paper Claim Trace

Use this for the Paper Claim assurance lane. Every quantitative or interpretive
claim in a draft must trace to a specific result file and the pre-registered
decision rule that licenses it. The failure mode is prose that runs ahead of the
evidence: a number with no backing JSON, a conclusion stronger than the result,
or an outcome interpreted without the registered outcome-to-prose mapping.

## Procedure

For each claim, table entry, figure caption, and limitation in the draft:

1. **Bind to a result file.** Identify the date-suffixed result JSON and the vault
   `[RESULT]` / `[DECISION]` / `[NEGATIVE]` entry behind the claim. A claim with no
   backing artifact is flagged "awaiting computation" — do not draft prose for it
   (empiricism-first).
2. **Check the number.** The value in prose matches the value in the result file
   to the stated precision. Note any rounding.
3. **Check the decision-rule lock.** For outcome-contingent claims, the
   outcome-to-prose direction is fixed by a vault `[DECISION]` against the
   pre-registered rule. Prose follows the locked direction, not a post-hoc reading.
4. **Honest reporting.** Negative or weaker-than-expected results are reported as
   such — no contribution inflation, no burying a null. The claim's strength
   matches the result's strength.
5. **Disclosure completeness.** Cascade effects, pre-reg amendments, and
   superseded analyses that affect the claim are disclosed in the limitations or
   methods text.
6. **Freeze and refresh the audit state.** Record the audited commit in the
   deliverable and re-check `origin/main` before finalising any verdict that
   depends on file presence; if it moved, re-pin and re-evaluate those verdicts.
   Before authoring a mandated output, run `git check-ignore` on its path and
   record the intended whitelist/force-add route rather than discovering an
   ignored deliverable at commit time.

## Output Format

A claim-by-claim table: claim → backing result file + vault entry → number
matches (Y/N) → decision-rule lock present (Y/N) → verdict (TRACED / AWAITING
COMPUTATION / OVERSTATED / UNDISCLOSED). List every untraced or overstated claim
explicitly.

## Escalate Or Stop When

- A drafted claim has no backing result file or vault entry.
- Prose asserts a stronger conclusion than the result supports.
- An outcome-contingent claim has no decision-rule lock on file.

## Pressure Scenarios From This Repo

- T1.2 cascade disclosure: an amendment downstream affected earlier claims that
  needed explicit disclosure rather than silent revision.
- Claims drafted against expected results before the computation landed.
- A weaker-than-hoped result that needed honest prose, not a hedge that implied
  the stronger finding.

## Related Skills & Contracts

- Pairs with `humanizer` (anti-AI-tell pass), `notation-check` (notation standard),
  `vault-sync`, and `paper-draft`.
- Enforcing artifact: human-review-only — there is no contract for claim honesty;
  this skill *is* the check, and the Manager records the review explicitly.
