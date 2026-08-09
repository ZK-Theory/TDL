---
asset_id: mth_theorem_retrieval_brief
name: Theorem Retrieval Brief
version: 1.0.0
applicability_trigger: A proof gap may be bridged by an external theorem whose exact statement and assumptions are not yet in the supplied context.
compatibility: any
dependencies: []
permissions:
  - read_supplied_research_context
  - write_typed_candidate_output
observer_overlays: []
declared_review_state: candidate
supersedes: null
required_output: TheoremCitation
lineage:
  source_id: woodruff-et-al-ai-assisted-research
  source_title: "Accelerating Scientific Research with Gemini: Case Studies and Common Techniques"
  source_path: TDA-Research/01-Literature/Research Papers/Gemini For Research.md
  source_sha256: 43f65f8dfae9e0cb0a8493e517a3a19cc48432b5329b22345a64dfc731cccf24
  sections:
    - "### **2.2 Cross-Pollination of Ideas**"
    - "### **2.3 Simulation and Counterexample Search**"
  project_additions: []
---

# Theorem Retrieval Brief

## Purpose

Separate discovery of a potentially relevant theorem from verification of its
formal statement, assumptions, and applicability. A recalled theorem is a search
lead, not evidence, until an external source has been checked.

## Applicability

Use when an argument has a clearly located gap and a theorem, lemma, or analogy
from another domain may close it. Do not use retrieval as a substitute for
checking whether the target objects satisfy the theorem's hypotheses.

## Operator protocol

1. State the exact proof gap, desired conclusion, object types, and constraints.
2. Retrieve candidate theorem names and likely sources. For each, mark the
   statement as unverified and list the assumptions believed relevant.
3. Keep retrieval and verification separate. An operator must locate the formal
   statement in an external paper, book, or other authoritative source and
   record the exact source identity and statement before citation.
4. Compare every hypothesis with the current problem using explicit bindings.
   Reject a theorem if any required condition is absent, ambiguous, or merely
   analogous.
5. Only after external verification, construct a self-contained application or
   proof segment and preserve the source and assumption bindings in the output.

## Required RM-03 output

Return a `TheoremCitation` containing theorem name, exact source reference and
source identity, verified statement, hypothesis bindings, conclusion binding,
verification status, verifier attribution, and limitations. A retrieval-only
record must remain candidate and cannot be cited as a verified theorem.

## Failure modes

- A theorem name or remembered statement is treated as externally verified.
- The cited source contains a materially different theorem.
- A hypothesis is omitted, weakened, or satisfied only by analogy.
- The verification record is produced by the same unobserved retrieval step.
- The theorem is correct but does not close the declared proof gap.

## Worked example

**Illustrative TDA example only.** A stability argument retrieves a theorem
relating perturbations to bottleneck distance. The operator obtains the exact
published statement, records the permitted filtration class and metric, and
checks those assumptions against the pipeline. If the pipeline uses a different
metric order, the theorem is rejected for this application rather than cited by
name alone.

## Verified lineage

The pinned source's section 2.2 supports cross-domain analogy and retrieval of
obscure theorems. Section 2.3 separately requires the researcher to find and
feed back formal statements before they are incorporated into a proof. This
asset preserves that retrieval/verification separation.
