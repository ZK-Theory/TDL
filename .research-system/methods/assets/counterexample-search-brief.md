---
asset_id: mth_counterexample_search_brief
name: Counterexample Search Brief
version: 1.0.0
applicability_trigger: A conjecture or universal claim needs a neutral prove-or-refute search before it can be relied upon.
compatibility: any
dependencies: []
permissions:
  - read_supplied_research_context
  - write_typed_candidate_output
observer_overlays: []
declared_review_state: candidate
supersedes: null
required_output: CounterexampleCandidate
lineage:
  source_id: woodruff-et-al-ai-assisted-research
  source_title: "Accelerating Scientific Research with Gemini: Case Studies and Common Techniques"
  source_path: TDA-Research/01-Literature/Research Papers/Gemini For Research.md
  source_sha256: 43f65f8dfae9e0cb0a8493e517a3a19cc48432b5329b22345a64dfc731cccf24
  sections:
    - "### **2.3 Simulation and Counterexample Search**"
    - "### **9.2 Understanding Current Limitations and Failure Modes**"
  project_additions:
    - name: minimal-instance-first
      authority: ARS heuristic
      rationale: Start with the smallest admissible instance to make a returned candidate easier to verify; this ordering is not attributed to the source paper.
---

# Counterexample Search Brief

## Purpose

Test a conjecture without confirmation bias by asking for either a proof or a
refutation and by requiring every returned candidate to be independently
checkable. The output records a search recipe and candidate evidence; it does not
execute code or declare the conjecture resolved.

## Applicability

Use this procedure for a universal mathematical, algorithmic, or empirical claim
when a concrete violating instance would be decisive. State all admissibility
conditions and the exact predicate before starting.

## Operator protocol

1. Restate the question neutrally as **prove or refute**. Define the quantified
   domain, admissibility rules, and the predicate whose failure is decisive.
2. Search both directions: outline the strongest plausible proof route and the
   strongest plausible counterexample construction. Do not discard evidence
   merely because it opposes the supplied conjecture.
3. Apply the ARS `minimal-instance-first` heuristic: start with the smallest
   admissible cases, then expand systematically. This ordering improves manual
   verification but is a project heuristic, not a claim from the source paper.
4. For each candidate, give exact construction data and a deterministic checking
   recipe. Record the recipe only; this methods pack neither runs it nor treats a
   successful-looking calculation as verified.
5. Return proof progress and counterexample candidates separately. If neither is
   decisive, report the search bounds and unresolved gap without choosing a side.

## Required RM-03 output

Return a `CounterexampleCandidate` containing the conjecture identity, domain and
predicate, construction parameters, expected violating relation, deterministic
verification recipe, searched bounds, and status `candidate`. A later operator
run or domain review must establish whether the candidate is valid.

## Failure modes

- The prompt asks only for a proof or otherwise embeds the desired conclusion.
- The candidate violates an admissibility condition.
- A numerical coincidence is returned without an exact checking recipe.
- The search bound is omitted, making a null result look exhaustive.
- The minimal-first ordering is misrepresented as source-derived authority.

## Worked example

**Illustrative TDA example only.** To test a claim that one filtration ordering
always lowers a persistence distance, define the admissible point-cloud family
and both ordered metrics. Begin with two- and three-point configurations, record
coordinates and filtration parameters for any reversal, and provide a recipe
that recomputes both diagrams and distances. The candidate remains unverified
until that recipe is run through an authorized verification path.

## Verified lineage

The pinned source's section 2.3 supports explicit counterexample construction;
section 9.2 identifies confirmation bias and prescribes neutral "prove or refute"
framing. The minimal-instance-first ordering is explicitly labelled above as an
ARS heuristic rather than source content.
