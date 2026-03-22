# Revision Plan: First Draft → Second Draft

## Sources

Two independent critiques were compared and merged:
- **Plan A** (internal): Systematic tracking of all critique points, emphasis on GMM validation, H₀–GMM overlap, pipeline sensitivity.
- **Plan B** (external): Phased approach (quick fixes → new analysis → redraft), concrete rewritten sections, OM baseline as highest priority, FDR correction, age-adjusted escape rates.

## Merge Decisions

| External Plan Proposal | Decision | Rationale |
|------------------------|----------|-----------|
| Compressed Abstract (198 words) | **Rejected** — wrote fuller version (~280 words) | Too compressed; lost readability and key details; JEG allows longer abstracts |
| Skeletal §1.3 (3 bullet points) | **Rejected** — kept expanded paragraph form | Too terse for a methods-heavy paper; needs to set up Sections 3–4 |
| Invented ARI=0.62, R²=0.41, age-adjusted 4.2% | **Rejected** — used [TODO] placeholders | Cannot publish fabricated numbers; these must come from actual analysis |
| New §3.7 Sequence Analysis Baseline | **Adopted** | Both plans agreed this is essential |
| New §5.5 Robustness Summary table | **Adopted** | Clean structure for reviewers to see what's done vs. pending |
| FDR correction for Wasserstein | **Adopted** | Both plans agreed |
| Phase null label as "exploratory" | **Adopted** | Both plans agreed n=20 is insufficient |
| Age caveat for regime persistence | **Adopted** — expanded beyond external plan | Added lifecycle vs. inequality framing throughout §4.4.1, §5.4, §6 |
| GMM bootstrap stability (Plan A only) | **Adopted** | External plan missed this; important for k=7 validation |
| H₀–GMM overlap analysis (Plan A only) | **Adopted** | External plan missed this; needed to substantiate the H₀→GMM claim |
| Pipeline sensitivity (Plan A only) | **Adopted as P3** | Important but not blocking; deferred to supplementary |
| Regional stratification | **Adopted as P3** | Both plans flagged geography gap; JEG-critical |

## Summary of Textual Changes Made in Second Draft

### 1. Big-Picture Positioning
| Critique | Change | Location |
|----------|--------|----------|
| "No existing framework" too strong | Narrowed to "no study has applied PH with structured null-model batteries to socioeconomic life-course trajectories" | Abstract, §1.2 |
| Contribution hierarchy muddled | Reduced to two primary contributions + exploratory extension | §1.3, Abstract |
| "Invisible to sequence analysis" | Changed to "complement" / "not naturally available in OM-based frameworks" | Abstract, §5.1 |
| TDA novelty overstated in §2.4 | Added Robinson & Turner (2017) and Stolz et al. (2017) as prior art; positioned memory ladder as specific innovation | §2.4 |

### 2. Methods and Robustness
| Critique | Change | Location |
|----------|--------|----------|
| 5,000 landmarks unjustified | Added explicit motivation + sensitivity check reference to Appendix B | §3.3 |
| Null implementation glossed over | Clarified: PCA loadings fixed; landmarks re-selected; n=500 resolution bounded to p≈0.002 | §3.4 |
| Markov estimation under-explained | Added: globally estimated via ML; Laplace smoothing; conditional on starting states; ~70% non-zero cells for order-2 | §3.4 |
| No H₀–GMM regime link | Added paragraph + TODO for overlap table (Table S2) | §3.5, §4.4 |
| UMAP sensitivity verbal only | Added TODO for quantitative re-run of key results under UMAP | §3.2, §5.5 |
| GMM not validated | Added TODO for bootstrap stability | §3.5 |
| No OM baseline section | Added new §3.7 with OM methodology and TODO | §3.7 |

### 3. Interpretation of Results
| Critique | Change | Location |
|----------|--------|----------|
| p=0.148 oversold as "consistent" | Changed to "not rejected"; added extended caveat about power, richer process classes, failure-to-reject ≠ evidence-for | §4.3, §5.2 |
| H₁ negative result oversold | Removed "honestly" rhetoric; trimmed to a bounding-result framing | §4.5, §5.3 |
| Phase-ordering n=20 too coarse | Relabeled entire subsection as "exploratory"; added resolution caveat; TODO for n≥200 | §4.5 |
| Regime persistence ≠ traps without age controls | Added lifecycle/retirement caveat throughout; TODO for age-stratified rates | §4.4, §4.4.1, §5.4 |
| "p < 0.001" misleading with n=500 | Changed to "p ≤ 0.002" with explicit note on simulation resolution | §4.3, §6 |

### 4. Policy and Geography
| Critique | Change | Location |
|----------|--------|----------|
| Policy claims too sharp | Softened to "consistent with", "could in principle", "causal validation remains necessary" | §5.2, §6 |
| Geography absent | Added spatial paragraph to §1.1; expanded §5.4 limitation; regional extension in §6 as "priority" | §1.1, §5.4, §6 |

### 5. Style and Tone
| Change | Location |
|--------|----------|
| Removed "we are committed to honest reporting" | §1.3 |
| Removed "important negative result that we report honestly" | §4.5 |
| Removed "honest assessment" section title → "H₁ Cycles: A Negative Result" | §5.3 |
| "Invisible to" → "not naturally available in" / "complement" | Throughout |
| Metaphorical "height"/"depth" replaced with persistence-value language | §2.3, §4.5, §5.1 |

### 6. Structural Changes
| Change | Location |
|--------|----------|
| New §3.7 (Sequence Analysis Baseline) | Methods |
| New §5.5 (Robustness Summary) with tracking table | Discussion |
| Regime persistence moved to §4.4.1 (subsection) | Results |
| Phase-ordering test retitled "Phase-Ordering Test (Exploratory)" | §4.5 |
| Appendix B stub added for landmark sensitivity | End |
| New supplementary tables S2, S3, S4 planned | Tables |

---

## Items Requiring New Analysis

All tracked in `MISSING_ELEMENTS_ACTION_PLAN.md` with priority levels:
- **P1 (Required):** OM baseline, landmark sensitivity, Wasserstein FDR, phase-null n increase
- **P2 (Strongly recommended):** Age-stratified persistence, UMAP re-run, GMM bootstrap, H₀–GMM overlap
- **P3 (Desirable):** Regional stratification, pipeline sensitivity, Markov sparsity reporting
