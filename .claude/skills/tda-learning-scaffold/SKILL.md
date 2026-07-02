---
name: tda-learning-scaffold
description: Use when creating structured learning material connected to TDA, topology, statistics, Lean, Manim, or adjacent mathematics — exercise sets, study plans, worked examples, formalization drills, explainer outlines.
---

# TDA Learning Scaffold

Support the parallel learning track (computational topology, abstract
algebra, probability/statistics, Lean, Manim) without mixing study material
into the research record. Learning artifacts are for understanding; they are
never evidence. Not for producing research code, paper prose, or inference
artifacts.

## Tier 3 Constraint

This skill may generate ideas, prototypes, plans, or communication artifacts.
It may not create paper claims, result artifacts, canonical computations, or
contract-bearing implementations unless routed through the relevant tier 1 or
tier 2 skill first.

## Output Types

Concept ladder · exercise set · worked solution · Lean formalization drill ·
Manim animation outline · reading guide · prerequisite repair path.

## Required Separation

- Mark everything as learning material, in the header or filename.
- Store outside the research trees — never under `results/` and never in the
  vault's methods/results pages (a study note is not a Computational-Log
  entry).
- Do not cite exercise outputs as literature or as validation.
- Do not let toy examples become claims about USoc/BHPS data — a worked
  example on synthetic trajectories says nothing about the panel.
- Textbook conventions may differ from locked project conventions (metric
  orders, notation); when they do, note the difference rather than importing
  it.

## Procedure

1. Identify the learning goal and the current gap (prerequisite repair vs
   extension).
2. Build the ladder: each rung is one concept with one exercise and one
   worked example.
3. Connect to the research programme *as motivation only* — "this is the
   machinery behind the W2 stability theorem" — without generating claims.
4. For Lean/Manim outputs, keep the drill/animation self-contained and
   runnable.
5. File under the learning workspace, and link from a daily note if worth
   remembering.

## Self-Test Prompts

- *A worked example computes persistence on toy trajectories and the agent
  writes "this confirms the pipeline's behaviour".* → Expected: strike the
  claim; a learning example validates understanding, not the pipeline.
- *A Lean drill formalizes a lemma and the agent proposes citing it in
  P01-B.* → Expected: no — learning artifacts are not citable material.

## Related Skills

`tda-research-ideation-lab` (when study sparks a research idea) ·
`tda-prototype-sandbox` (disposable code experiments) ·
`tda-domain-modeling` (when a textbook term collides with project
vocabulary).
