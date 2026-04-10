---
description: Help draft, extend, or critique sections of research papers in TDA/social science
allowed_tools: Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# Skill: paper-draft

Assist with writing, extending, or critiquing academic paper sections for this TDA social science research project.

## Context about the papers

Three active papers:
1. **poverty_tda**: "UK Poverty Traps: A Topological Data Analysis Approach to Social Mobility" — Target: Journal of Economic Geography. Method: Morse-Smale complex on 31,810 LSOAs. Key results: 357 poverty traps, 61.5% SMC cold spot match (2.5× baseline, p<0.01), Cohen's d=−0.74.
2. **financial_tda**: Market regime detection via persistent homology on multi-asset time series. Validates against 2008 GFC, 2020 COVID.
3. **trajectory_tda**: Career trajectory analysis via persistent homology on BHPS/UKHLS panel data.

## Your task

1. Ask the user:
   - Which paper/domain?
   - Which section to work on (Abstract, Introduction, Methods, Results, Discussion, Conclusion)?
   - Mode: draft new content, extend existing, critique/revise, or write methods for a new analysis?

2. Read the relevant existing files:
   - `<domain>/paper_draft.md` or `<domain>/paper_outline.md` if they exist
   - `.apm/Memory/` for any paper task logs with key findings
   - Key results from `results/<domain>/` or `outputs/<domain>/` if referenced

3. Work according to the mode:

   **Draft / Extend**: Write academic prose at the level of a top field journal (JEG, QJE, JRSS, etc.). Follow IMRaD structure. Use hedged, precise language — avoid AI-sounding constructions (vague attributions, inflated symbolism, em dash overuse, "it is worth noting"). Cite existing references already in the draft rather than inventing new ones.

   **Methods section**: Describe TDA methods accurately and accessibly for a social science audience. Cover:
   - Intuition for the topological concept (what does it capture?)
   - Formal definition (filtration, persistence, complex type)
   - Why this method is suited to the specific research question
   - Computational implementation (libraries, key parameters)
   - Link to the statistical tests used (permutation nulls, bootstrap CIs)

   **Results section**: Report findings in precise academic language. Always include:
   - Effect sizes alongside p-values
   - Confidence intervals (from bootstrap resampling)
   - Comparison to baseline/benchmark where applicable
   - Geographic or group-level breakdown if relevant

   **Critique / Revise**: Apply the humanizer skill principles — flag and rewrite any: inflated symbolism, promotional language, vague attributions ("this work demonstrates…"), em dash overuse, hollow transition phrases. Preserve all substantive content.

4. Output the drafted text as markdown. If editing an existing file, propose the change and ask the user to confirm before applying it.

## TDA methodology writing conventions

- Persistent homology: "We apply Vietoris-Rips filtration to construct a sequence of simplicial complexes…"
- Persistence diagrams: "Features are summarised as persistence diagrams, recording (birth, death) pairs for topological features across filtration scales."
- Significance: "Statistical significance was assessed using permutation tests (n=1000 permutations) with Benjamini-Hochberg FDR correction for multiple comparisons."
- Effect sizes: Always report Cohen's d or equivalent; report as "substantial" (d≥0.5), "moderate" (d≈0.3), "small" (d≈0.2).
- Validation language: "The topological classification achieves X% detection accuracy against [benchmark], representing a Y-fold improvement over random baseline."

## Style guidance

- Past tense for what was done; present tense for what the paper argues/shows
- No first-person plural in methods ("Persistent homology was applied to…" not "We applied…") — unless the target journal uses active voice
- Quantitative results in the text, not just tables
- Each figure/table should be interpretable without reading the surrounding text
- Limitations section: honest about data constraints, computational approximations, generalisability
