---
asset_id: mth_decomposition_scaffolding_template
name: Decomposition Scaffolding Template
version: 1.0.0
applicability_trigger: A research question is too broad for a single verifiable step and needs an explicit dependency-ordered decomposition.
compatibility: any
dependencies: []
permissions:
  - read_supplied_research_context
  - write_typed_candidate_output
observer_overlays: []
declared_review_state: candidate
supersedes: null
required_output: ExploratoryMemo
lineage:
  source_id: woodruff-et-al-ai-assisted-research
  source_title: "Accelerating Scientific Research with Gemini: Case Studies and Common Techniques"
  source_path: TDA-Research/01-Literature/Research Papers/Gemini For Research.md
  source_sha256: 43f65f8dfae9e0cb0a8493e517a3a19cc48432b5329b22345a64dfc731cccf24
  sections:
    - "### **2.1 Iterative Prompting and Refinement**"
    - "### **2.8 Summary: The AI-Assisted Research Playbook**"
  project_additions: []
---

# Decomposition Scaffolding Template

## Purpose

Turn a broad research question into dependency-ordered, individually verifiable
subproblems while preserving the link from each local result to the original
claim. The scaffold guides exploration; it does not imply that filling every box
proves the top-level result.

## Applicability

Use when a direct response would hide several lemmas, calculations, data
decisions, or validation steps. The problem owner must supply the governing
definitions, fixed assumptions, and the exact outcome sought.

## Operator protocol

1. Record the top-level question, governing definitions, fixed assumptions,
   prohibited shortcuts, and decisive success or refutation condition.
2. Split the question into the smallest meaningful subproblems that can each be
   checked independently. For every subproblem, name its inputs, output, method,
   and falsifier.
3. Draw the dependency order. Mark conjectural bridges explicitly and do not let
   downstream steps consume them as established facts.
4. Work one ready subproblem at a time. After each result, check its assumptions,
   update only the downstream nodes it genuinely changes, and retain negative or
   partial results.
5. Reassemble the top-level argument by citing each verified output and every
   remaining gap. Stop when the requested outcome is established or refuted, or
   when the next step needs an owner decision or unavailable evidence.

## Required RM-03 output

Return an `ExploratoryMemo` containing the top-level question, assumptions,
subproblem table, dependency edges, per-node status and evidence, falsifiers,
integration argument, unresolved gaps, and next authorized action. Status remains
non-governing candidate evidence.

## Failure modes

- The decomposition drops a governing assumption or changes the question.
- Subproblems are activities rather than checkable claims or outputs.
- A conjectural bridge is consumed as if verified.
- Local success is reported as top-level success without reassembly.
- The scaffold grows after the decisive requested outcome is already proven.

## Worked example

**Illustrative TDA example only.** Decompose a claim about trajectory separation
into data eligibility, frozen representation, filtration construction, distance
calculation, and decision-rule nodes. Each node names its exact input artefact and
falsifier. A green distance calculation cannot compensate for a failed frozen-
representation node, so the final memo retains the claim as unresolved.

## Verified lineage

The pinned source's section 2.1 recommends specific sub-tasks and scaffolding for
technical detail; section 2.8 describes breaking deep problems into verifiable
parts under strong human orchestration. This template makes those dependencies
and stopping conditions explicit for provider-neutral use.
