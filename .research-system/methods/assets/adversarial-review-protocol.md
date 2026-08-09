---
asset_id: mth_adversarial_review_protocol
name: Adversarial Review Protocol
version: 1.0.0
applicability_trigger: A proof, derivation, or technical argument needs risk-led independent critique before it can support a research decision.
compatibility: any
dependencies: []
permissions:
  - read_supplied_research_context
  - write_typed_candidate_output
observer_overlays: []
declared_review_state: candidate
supersedes: null
required_output: ReviewFindingSet
lineage:
  source_id: woodruff-et-al-ai-assisted-research
  source_title: "Accelerating Scientific Research with Gemini: Case Studies and Common Techniques"
  source_path: TDA-Research/01-Literature/Research Papers/Gemini For Research.md
  source_sha256: 43f65f8dfae9e0cb0a8493e517a3a19cc48432b5329b22345a64dfc731cccf24
  sections:
    - "### **2.1 Iterative Prompting and Refinement**"
    - "### **3.2 Cryptography: AI-Assisted Bug Detection in SNARGs**"
  project_additions: []
---

# Adversarial Review Protocol

## Purpose

Produce a risk-led technical review whose findings survive explicit attempts to
disprove them. The protocol separates an initial critique from scrutiny of that
critique so that plausible but unsupported findings do not acquire authority by
repetition.

## Applicability

Use this procedure when a supplied proof, derivation, design argument, or
technical manuscript must be checked for material errors, missing assumptions,
invalid reductions, or claim-strength drift. It is a review procedure, not an
acceptance decision and not a substitute for a domain expert where the governing
contract requires one.

## Operator protocol

1. **Initial review.** Read the complete declared subject, including appendices.
   Identify candidate errors and improvements, binding each item to exact subject
   evidence and explaining the consequence if the item is valid.
2. **Self-critique of findings.** Challenge every candidate finding. Recheck the
   cited derivation, search for a definition or assumption that defeats the
   finding, distinguish a substantive error from preference, and remove any item
   that cannot be supported without invention.
3. **Iterative refinement.** Revise the review from the self-critique, repeat the
   challenge on changed findings, and stop only when each retained finding has a
   reproducible evidence path and each rejected finding has a recorded reason.
   Label incomplete arguments as partial progress; never silently promote them to
   complete proofs.

## Required RM-03 output

Return a `ReviewFindingSet` containing the exact review subject, each retained
finding's severity, location, evidence, consequence, required disposition, and
self-critique result, plus a disposition for every candidate finding considered.
The record remains candidate evidence until independently reviewed and granted
use authority through the external lifecycle seam.

## Failure modes

- The initial review is returned without a self-critique pass.
- A finding cites no exact subject evidence or relies on a different revision.
- A stylistic preference is presented as a correctness failure.
- The reviewer confirms its own claim by restating it rather than checking the
  consumed definition, equation, or implementation seam.
- Appendices or declared supporting artefacts are omitted without an explicit
  scope limitation.

## Worked example

**Illustrative TDA example only.** A review of a persistence-distance argument
initially claims that two diagrams use different ground metrics. The
self-critique checks the cited definitions and discovers both use the same
ordered metric after normalization, so that candidate finding is removed. A
second finding survives because the implementation applies normalization after
the distance is computed; the final finding cites the exact call site and states
the downstream claim affected.

## Verified lineage

The three stages distil the initial-review, self-critique, and iterative-refinement
procedure described in the pinned source at sections 2.1 and 3.2. The source's
case study also requires findings to be checked for hallucination and substantive
effect before expert verification. This asset generalizes that procedure without
making the cited provider or the TDA example a runtime dependency.
