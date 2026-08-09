---
asset_id: mth_context_deidentification_transform
name: Context De-identification Transform
version: 1.0.0
applicability_trigger: Recognition of a paper, author, project, or open-problem label may bias or prematurely halt work on an otherwise self-contained problem.
compatibility: any
dependencies: []
permissions:
  - read_supplied_research_context
  - write_sensitive_sidecar_candidate
  - write_deidentified_brief_candidate
observer_overlays: []
declared_review_state: candidate
supersedes: null
required_output: DeidentifiedContextSidecar
lineage:
  source_id: woodruff-et-al-ai-assisted-research
  source_title: "Accelerating Scientific Research with Gemini: Case Studies and Common Techniques"
  source_path: TDA-Research/01-Literature/Research Papers/Gemini For Research.md
  source_sha256: 43f65f8dfae9e0cb0a8493e517a3a19cc48432b5329b22345a64dfc731cccf24
  sections:
    - "### **2.7 Human-AI Collaboration Dynamics**"
    - "### **9.2 Understanding Current Limitations and Failure Modes**"
  project_additions: []
---

# Context De-identification Transform

## Purpose

Create a reversible, problem-complete brief that removes contextual cues likely
to trigger prestige, authorship, project, or open-problem bias while preserving
the definitions and constraints needed for valid work. Reversibility is carried
by a separate sensitive sidecar, never by hidden material in the operator brief.

## Applicability

Use only when contextual recognition is plausibly distorting engagement and when
the research question can be stated without those cues. Do not remove facts that
change the mathematical object, estimand, admissibility conditions, safety
classification, or governing authority.

## Operator protocol

1. Identify the subject set and classify every context element as required
   problem content, removable identifying context, or uncertain. Escalate
   uncertain removals rather than guessing.
2. Replace removable names, citations, project labels, and status language with
   stable opaque tokens. Preserve definitions, hypotheses, units, domains, and
   explicit constraints verbatim where possible.
3. Write an immutable sensitive sidecar with exactly:
   `sidecar_artefact_id`, `revision`, `content_sha256`, `subject_set`,
   `transform_version`, `sensitivity_class`, and `retention_class`. The mapping
   bytes are referenced by that identity and governed by an independent access
   authority; the sidecar does not grant access to itself.
4. Give the operator-facing brief only the opaque sidecar ID, revision, and
   content hash. Confirm that no mapping values or identifying labels remain in
   the brief.
5. Before import or re-identification, resolve the exact sidecar identity and
   external access decision, then prove an exact round trip against the declared
   subject set. A missing, stale, foreign, or unavailable sidecar blocks use.

## Required RM-03 output

Return a `DeidentifiedContextSidecar` plus a de-identified problem statement.
The sidecar record uses the seven fields above; the operator brief carries only
its opaque ID, revision, and hash. Neither object claims acceptance or access
authority.

## Failure modes

- A removed fact changes the problem or the permitted claim.
- The mapping is embedded in the operator-facing brief.
- The sidecar cannot be located by exact ID, revision, and hash.
- Re-identification proceeds without a separate access decision.
- The transform is irreversible or joins a result to a different subject set.

## Worked example

**Illustrative TDA example only.** Replace a named cohort and paper title with
opaque tokens while retaining the exact trajectory variables, window rule,
metric order, and filtration definition. The sidecar maps those tokens back to
the named context and is stored as sensitive candidate material. A returned
diagram interpretation can be rejoined only after the exact sidecar and its
external access decision are resolved.

## Verified lineage

The pinned source's section 2.7 describes removing the paper and supplying only
the problem statement and definitions when recognition blocks useful work.
Section 9.2 records the associated alignment and recognition friction. The
sidecar identity, retention, and independent-access controls are ARS provenance
requirements added to make the transformation reversible and governable.
