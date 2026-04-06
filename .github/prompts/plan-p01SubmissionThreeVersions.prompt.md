# Plan: P01 Paper Submission — Three Versions + Code Repository Pipeline

Produce three submission-ready versions: (1) aggressively condensed for SocMethod (~10k words), (2) substantive applied paper for JRSS-A (~30pp), (3) methodological paper for JRSS-B (~25pp). Plus a reusable pipeline for extracting paper-specific code into standalone repos with Zenodo DOIs.

**Execution order:** Phase 0 (compulsory fixes) → Phase 1 (SocMethod) → Phase 2 (JRSS-A/B split) → Phase 3 (code repo + pipeline template)

---

## Phase 0: Compulsory Fixes (shared across all versions)

All produce `drafts/v9-2026-04.md` and update `papers/P01-VR-PH-Core/latex/main.tex` + `papers/P01-VR-PH-Core/latex/body.tex`.

| #   | Fix                                                                                                                                                                                                                                                                                                                | Files                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| 0.1 | **Abstract: label test statistics for BHPS p-values** — BHPS section is ambiguous about which stat each p comes from                                                                                                                                                                                               | `main.tex` abstract, `v9` abstract |
| 0.2 | **Remove `\tableofcontents`** (~line 57 of `main.tex`). Non-standard for all three targets.                                                                                                                                                                                                                        | `main.tex`                         |
| 0.3 | **Update target journal metadata** in markdown header + `papers/P01-VR-PH-Core/_project.md`                                                                                                                                                                                                                        | `v9` line 3, `_project.md`         |
| 0.4 | **Remove JEL codes** (economics-specific) from journal versions                                                                                                                                                                                                                                                    | `v9`, `main.tex`                   |
| 0.5 | **Add 6 submission statements**: Data Availability (USoc DOI: 10.5255/UKDA-SN-6614-19, BHPS DOI: 10.5255/UKDA-SN-5151-3, UKDS licence + synthetic substitute), Code Availability (GitHub + Zenodo DOI), Ethics, Conflicts ("none"), Funding ("unfunded independent researcher"), CRediT (single author, all roles) | New section in both md and LaTeX   |
| 0.6 | **Sharpen §5.2 cross-ref**: "(§4.3)" → "(§4.3, intra-regime compactness analysis)"                                                                                                                                                                                                                                 | Both md and `body.tex`             |
| 0.7 | **Justify Wasserstein p-value construction** in §3.4 — 1–2 sentences framing mean-obs-null vs null-null as energy/MMD-type two-sample test (cite Gretton et al. 2012 or Turner et al. 2014)                                                                                                                        | §3.4 in both                       |
| 0.8 | **Create Supplementary §A** (imputation balance by regime) — referenced in §3.1 but missing                                                                                                                                                                                                                        | New supplementary document         |
| 0.9 | **Create Figure S1** (UMAP-16D scatter) — referenced in §3.2 but missing. Generate from `embeddings_umap16.npy`                                                                                                                                                                                                    | Script + figure output             |

### 0.5 Detail — Submission Statements

```markdown
## Data Availability

This study uses data from Understanding Society: The UK Household Longitudinal Study
(University of Essex, Institute for Social and Economic Research, 2024,
DOI: 10.5255/UKDA-SN-6614-19) and the British Household Panel Survey (University of
Essex, Institute for Social and Economic Research, 2023, DOI: 10.5255/UKDA-SN-5151-3).
Both are available through the UK Data Service under standard licence agreement.
A synthetic dataset reproducing the statistical properties of the analysis sample is
provided at [repo URL] to enable full code reproduction.

## Code Availability

Analysis code is available at https://github.com/stephendor/p01-trajectory-ph
(DOI: [Zenodo DOI]).

## Ethics Declaration

This study uses secondary analysis of anonymised survey data available through the
UK Data Service. No ethics board approval was required.

## Conflict of Interest

The author declares no conflicts of interest.

## Funding

No external funding was received for this research. The author is an independent
researcher.

## Author Contributions (CRediT)

Stephen Dorman: Conceptualization, Methodology, Software, Formal Analysis,
Investigation, Data Curation, Writing – Original Draft, Writing – Review & Editing,
Visualization.
```

---

## Phase 1: SocMethod Version (~10,000 words)

SocMethod requires: Times New Roman 12pt, 1.25" margins, double-spaced, blind review, ASA citation style, grayscale figures, $25 fee.

### Steps

**1.1 Create SocMethod directory structure** (_parallel with 1.2_)

- `papers/P01-VR-PH-Core/submissions/socmethod/`
- Copy `v9-2026-04.md` as starting point
- New LaTeX files: `socmethod-main.tex`, `socmethod-body.tex` (or Word doc if preferred by reviewers)

**1.2 Convert citation style** (_parallel with 1.1_)

- Current: natbib/apalike (Author, Year)
- Required: ASA style — (Author Year:page) in text; full author lists in references
- Update `references.bib` entries to ASA format or use a different `.bst` file
- Key differences: no "and" → "&" in ASA; page numbers after colon; journal titles in italics

**1.3 Aggressive content reduction** (_depends on 1.1_)

Strategy: cut ~8,400 words (from ~17–18k to ~10k).

| Cut                                 | Words saved | Detail                                                                                                                            |
| ----------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Remove ToC, §5.5 Robustness Summary | ~800        | Table repeats §4.3 and §5.4                                                                                                       |
| Compress §1.3 Roadmap               | ~600        | 2pp → 1 short paragraph; repeats abstract                                                                                         |
| Compress §2 Literature              | ~1,500      | Merge §2.1+§2.2 into single Background (~1pp); condense §2.3 poverty economics to 2 sentences; §2.4 shortened (full spec in §3.4) |
| Move Appendices A+B to supplement   | ~800        | Landmark sensitivity + merge tree                                                                                                 |
| Compress §4.4 Regimes               | ~800        | Summary table + prose for 3 key regimes; §4.4.1 contingency to supp; §4.4.2 logistic regression compact                           |
| Compress §4.5 Phase Test            | ~400        | 1 paragraph with key stats                                                                                                        |
| Compress §4.6 Stratified            | ~600        | 1-page summary + Table 3; detail to supp                                                                                          |
| Compress §4.7 BHPS                  | ~600        | ~1pp: key Wasserstein results + Table 4                                                                                           |
| Compress §5.4 Limitations           | ~800        | ~1pp; embedding grid to supp                                                                                                      |
| Tighten §3 Methods                  | ~500        | Variable names to data note; compress VR/UMAP/OM                                                                                  |
| Line-level tightening               | ~1,000      | Redundant qualifiers, throat-clearing, sub-clause pruning                                                                         |
| **Total**                           | **~8,400**  | Target: ~10,000 words                                                                                                             |

**1.4 Blind review compliance** (_depends on 1.3_)

- Remove author name, affiliation, and any self-identifying text
- Replace "we" with passive voice or "this paper" per ASA convention
- Check all self-citations are in third person: "Dorman (2026)" not "I (Dorman 2026)"

**1.5 Grayscale figure conversion** (_parallel with 1.3_)

- Check all 14 figures + S1 for colour-dependence
- Convert colour-dependent figures to grayscale with distinguishable patterns
- SocMethod requires original format files (Excel, Word, PowerPoint, .wmf, .emf, .tif 300dpi)
- Regenerate problematic figures via `trajectory_tda/viz/paper_figures.py` with `grayscale=True` parameter

**1.6 Prepare SocMethod submission package** (_depends on 1.3, 1.4, 1.5_)
Separate files for Sage Track:

- Cover letter (contact info, title, relevant info)
- Abstract (≤200 words, separate file)
- Title page (affiliation, acknowledgments, contact, keywords)
- Blinded manuscript (no title page, no self-identifying info)
- Figures (grayscale, original format)
- Biography (≤100 words)
- $25 processing fee

**1.7 Run `/humanizer`** (_depends on 1.6_)

### Phase 1 Verification

1. Word count ≤ 10,000 (excl. references, figure captions, tables)
2. All self-identifying text removed
3. All figures grayscale
4. ASA citation style throughout
5. Abstract ≤ 200 words
6. All supplier files separated per Sage Track requirements

---

## Phase 2: JRSS-A + JRSS-B Split

### Paper 2A — JRSS-A (Statistics in Society): "Topological Structure of UK Employment-Income Trajectories: Regimes, Stickiness, and Stratified Inequality"

**Target**: ~28 pages (A4, 12pt, double-spaced, 28 lines/page)

**2A.1 Create JRSS-A directory**

- `papers/P01-VR-PH-Core/submissions/jrssa/`
- Derive from `v9-2026-04.md`

**2A.2 Content allocation** (_depends on 2A.1_)

| Section          | Disposition             | Notes                                                             |
| ---------------- | ----------------------- | ----------------------------------------------------------------- |
| §1.1–§1.2        | Full                    | UK mobility, research gap                                         |
| §2.1             | Full                    | Sequence analysis literature                                      |
| §2.2             | Condensed (~1pp)        | TDA foundations for non-TDA audience                              |
| §2.3             | Full                    | Mobility regimes                                                  |
| §2.4             | Brief                   | Reference Paper 2B for details                                    |
| §3.1             | Full                    | Data description                                                  |
| §3.2             | Full                    | Embedding                                                         |
| §3.3–§3.4        | Summarised (~1.5pp)     | Reference Paper 2B for methodology                                |
| §3.5, §3.6, §3.7 | Full                    | Regime discovery, windows, OM baseline                            |
| §4.1             | Full                    | Descriptives                                                      |
| §4.2             | Condensed               | Topological structure                                             |
| §4.3             | Key results only (~1pp) | Both tables as summary; ref Paper 2B for analysis                 |
| §4.4             | Full (all subsections)  | Seven regimes, H₀ vs GMM, stickiness, escape rates                |
| §4.5             | Condensed               | Cycle analysis                                                    |
| §4.6             | Full                    | Stratified comparisons                                            |
| §4.7             | Regime focus            | BHPS cross-era, regime structure (BIC k=8)                        |
| §5.1             | Full                    | TDA vs OM                                                         |
| §5.3             | Full                    | H₁ qualified negative                                             |
| §5.4             | Condensed               | Limitations                                                       |
| New content      | —                       | Substantive discussion of regime inequality + policy implications |

Figures: 1, 2, 5, 6, 7, 10, 11, 12, 13, 14

**2A.3 Write new Introduction and Conclusion** (_depends on 2A.2_)

- Introduction: Emphasise UK substantive questions, with TDA as the tool
- Conclusion: Focus on policy implications, regime structure, inequality
- Reference Paper 2B: "The methodological framework (the Markov memory ladder and dual test-statistic approach) is developed in [companion paper / arXiv preprint]"

**2A.4 JRSS-A formatting** (_parallel with 2A.3_)

- A4, 12pt, double-spaced
- UK spelling
- Abstract ≤ 200 words + 5–6 keywords alphabetically
- References: any readable style at submission (JRSS is flexible)
- Data Availability Statement required (before Acknowledgements)
- Alt text for all figures
- Tables at end of main text
- Figures as individual image files (PDF or EPS, not JPEG)

---

### Paper 2B — JRSS-B (Statistical Methodology): "The Markov Memory Ladder: Scalar vs Diagram-Level Hypothesis Tests for Persistent Homology of Sequential Data"

**Target**: ~25 pages (same format as JRSS-A)

**2B.1 Create JRSS-B directory**

- `papers/P01-VR-PH-Core/submissions/jrssb/`

**2B.2 Content allocation** (_depends on 2B.1_)

| Section          | Disposition        | Notes                                                         |
| ---------------- | ------------------ | ------------------------------------------------------------- |
| New introduction | —                  | Methodological motivation: scalar summaries → false negatives |
| §2.2             | Streamlined        | TDA foundations                                               |
| §2.4             | Expanded           | Statistical null models — core contribution                   |
| §3.1             | Condensed (~1pp)   | UK trajectories as motivating example only                    |
| §3.3             | Full               | VR PH pipeline                                                |
| §3.4             | Full (centrepiece) | Null model battery + both test statistics                     |
| §4.3             | Full               | Both tables, discrepancy, bootstrap stability, compactness    |
| §4.5             | 1 paragraph        | Cycle analysis summary                                        |
| §4.7             | Condensed          | Key Wasserstein replication numbers only                      |
| §5.2             | Expanded           | Test-statistic discrepancy + methodological implications      |
| New discussion   | —                  | Transportability; comparison to kernel two-sample tests       |
| Appendix B       | Full               | Landmark sensitivity                                          |

UK trajectories as motivating example; methodology is primary.

Figures: 3, 4, 8, 9 + new BHPS Wasserstein summary figure

**2B.3 Write new Introduction and Discussion** (_depends on 2B.2_)

- Introduction: Position within TDA methodology literature (Robinson & Turner 2017, Stolz et al. 2017)
- Discussion: Transportability of ladder; recommendations for practitioners; comparison to kernel-based two-sample tests
- Reference Paper 2A: "the substantive application in [companion paper]"

**2B.4 JRSS-B specific requirements** (_parallel with 2B.3_)

- Code publicly available with DOI before acceptance → Phase 3 delivers this
- Data: USoc/BHPS under UK Data Service licence → synthetic dataset needed (Phase 3)
- Alt text for all figures
- Single-blind peer review (author names visible)
- Data Availability Statement required
- Supplementary material: no data (must be in public repo); other material cited in text

**2B.5 Cross-referencing** (_depends on 2A.3 and 2B.3_)

- Each paper must be readable independently
- Paper 2A references 2B for methodology details
- Paper 2B references 2A for substantive application
- Both reference the arXiv preprint (combined version)
- If submitting simultaneously: "submitted" or "in preparation" reference
- If one accepted first: update the other with DOI

### Phase 2 Verification

1. Page count ≤ 30 for each paper
2. Each paper is self-contained (reviewer can read without the other)
3. No substantive duplication (brief summaries OK, repeated full tables NOT OK)
4. Consistent terminology across both papers
5. Cross-references correctly formatted
6. Abstract ≤ 200 words each + 5–6 keywords
7. JRSS-B: code URL and data statement present

---

## Phase 3: Code Repository Extraction + Zenodo DOI

Two deliverables: (A) the P01-specific repo, and (B) a reusable pipeline template for all future papers.

### Phase 3A: P01 Code Repository (`stephendor/p01-trajectory-ph`)

**3A.1 Determine repo scope**

The paper repo must enable a reader to:

1. Starting from raw UKDS data (or synthetic substitute), reproduce all results
2. Generate all figures
3. Build the LaTeX PDF

**Target structure:**

```
p01-trajectory-ph/
├── README.md                    # Paper abstract, quickstart, data instructions
├── LICENSE                      # MIT or Apache 2.0
├── pyproject.toml               # Minimal: only P01 dependencies
├── requirements.txt             # Pinned versions for reproducibility
│
├── src/
│   ├── data/                    # From trajectory_tda/data/
│   │   ├── trajectory_builder.py
│   │   ├── covariate_extractor.py
│   │   ├── employment_status.py
│   │   ├── income_band.py
│   │   └── annual_partition.py
│   │
│   ├── embedding/               # From trajectory_tda/embedding/
│   │   └── ngram_embed.py
│   │
│   ├── topology/                # From trajectory_tda/topology/ (P01-relevant only)
│   │   ├── trajectory_ph.py
│   │   ├── permutation_nulls.py
│   │   ├── markov_ladder.py
│   │   └── vectorisation.py
│   │
│   ├── validation/              # From trajectory_tda/validation/
│   │   └── wasserstein_null_tests.py
│   │
│   ├── analysis/                # From trajectory_tda/analysis/ (P01-relevant only)
│   │   ├── regime_discovery.py
│   │   ├── cycle_detection.py
│   │   ├── group_comparison.py
│   │   ├── h0_gmm_overlap.py
│   │   ├── gmm_bootstrap.py
│   │   ├── age_stratified.py
│   │   ├── escape_paths.py
│   │   ├── bootstrap_null_stability.py
│   │   ├── intra_regime_compactness.py
│   │   └── nssec_missingness.py
│   │
│   ├── viz/                     # From trajectory_tda/viz/
│   │   ├── paper_figures.py
│   │   └── constants.py
│   │
│   └── shared/                  # From shared/ (only what P01 imports)
│       ├── persistence.py
│       └── validation.py
│
├── scripts/                     # Numbered reproduction scripts
│   ├── 01_build_trajectories.py      # → results/01_trajectories.json
│   ├── 02_embed.py                   # → results/02_embedding.json, embeddings.npy
│   ├── 03_compute_ph.py              # → results/03_ph.json, 03_ph_diagrams.json
│   ├── 04_null_tests_scalar.py       # → results/04_nulls.json
│   ├── 05_null_tests_wasserstein.py  # → results/04_nulls_wasserstein.json
│   ├── 06_regime_discovery.py        # → results/05_analysis.json
│   ├── 07_stratified.py              # → results/06_stratified.json
│   ├── 08_sensitivity.py             # → results/07_umap_sensitivity.json
│   ├── 09_bhps_pipeline.py           # → results/bhps/
│   ├── 10_generate_figures.py        # → figures/fig*.pdf
│   ├── run_all.sh                    # Full reproduction (bash)
│   └── run_all.ps1                   # Full reproduction (PowerShell)
│
├── data/
│   ├── README.md                # Instructions for obtaining UKDS data
│   └── synthetic/               # Synthetic dataset (to be generated)
│       └── generate_synthetic.py
│
├── results/                     # Gitignored (generated by scripts)
│   └── .gitkeep
│
├── figures/                     # Generated figures
│   └── .gitkeep
│
├── paper/                       # LaTeX source
│   ├── main.tex
│   ├── body.tex
│   ├── references.bib
│   ├── Makefile
│   └── figures/                 # Symlink or copy of generated figures
│
└── tests/                       # Minimal smoke tests
    └── test_pipeline.py         # Tests on synthetic data
```

**Excluded from paper repo** (stays in TDL monorepo only):

- `trajectory_tda/topology/mapper.py` (Paper 2)
- `trajectory_tda/topology/zigzag.py` (Paper 3)
- `trajectory_tda/topology/multipers_bifiltration.py` (Paper 4)
- `trajectory_tda/mapper/` (Paper 2)
- `trajectory_tda/scripts/p04_*` (Paper 4)
- `trajectory_tda/scripts/run_mapper*` (Paper 2)
- `trajectory_tda/scripts/run_zigzag*` (Paper 3)
- `shared/deep_learning/` (Papers 7–10)
- `shared/ttk_utils.py`
- All `financial_tda/`, `poverty_tda/`

**3A.2 Create extraction script**

- Script that copies files from TDL monorepo to paper repo structure
- Rewrites import paths: `from trajectory_tda.topology.trajectory_ph` → `from src.topology.trajectory_ph`
- Strips monorepo-specific code (e.g., references to financial_tda, poverty_tda)
- Validates: all imports resolve, no broken references

**3A.3 Create minimal `pyproject.toml` for paper repo**

Only P01 dependencies:

```toml
[project]
name = "p01-trajectory-ph"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.23.0,<2.0.0",
    "pandas>=2.0.0",
    "scipy>=1.10.0",
    "scikit-learn>=1.3.0",
    "gudhi>=3.8.0",
    "ripser>=0.6.0",
    "umap-learn>=0.5.0",
    "pot>=0.9.0",
    "joblib>=1.3.0",
    "matplotlib>=3.7.0",
]
```

**3A.4 Create synthetic dataset generator** (_parallel with 3A.2_)

- Script that generates synthetic trajectories mimicking statistical properties:
  - Same 9-state space (EL/EM/EH/UL/UM/UH/IL/IM/IH)
  - Same trajectory length distribution (10–14 years, mean ~13)
  - Same state frequency distribution
  - Same first-order transition matrix (estimated from real data, published in paper)
  - Same n_trajectories (27,280) or a smaller subset (e.g., 5,000)
- Does NOT contain any real survey responses → freely distributable
- Enables code execution and figure generation (results will differ from paper but pipeline runs)
- Note: the synthetic data IS effectively a Markov-1 surrogate — this is a natural fit since the paper's Wasserstein test specifically shows real data differs from Markov-1 surrogates

**3A.5 Create numbered reproduction scripts** (_depends on 3A.2_)

- Numbered 01–10 matching the pipeline stages
- Each reads prior stage output and produces next
- `run_all.sh` / `run_all.ps1` chains them
- Each script has `--data-dir` and `--output-dir` CLI args

**3A.6 Create README.md** (_depends on 3A.5_)

- Paper title, abstract, citation (BibTeX)
- Quickstart (synthetic data): `pip install -e . && bash scripts/run_all.sh`
- Full reproduction (real data): instructions for UKDS account, data download, placement
- Software versions table
- Figure index: which script produces which figure

**3A.7 Add tests** (_parallel with 3A.5_)

- Smoke test: run pipeline on synthetic data, check outputs exist and have expected shapes
- No numerical accuracy tests (synthetic data produces different results)

**3A.8 Create GitHub repo + Zenodo DOI** (_depends on 3A.6, 3A.7_)

- Create `stephendor/p01-trajectory-ph` on GitHub
- Enable Zenodo integration
- Tag release (v1.0.0)
- Zenodo mints DOI automatically
- Add DOI badge to README
- Update paper submission statements with DOI

---

### Phase 3B: Reusable Paper-Repo Pipeline (General Methodology)

Creates a template and documented process for extracting paper repos from the TDL monorepo. Applicable to Papers 2–10.

**3B.1 Create template** in TDL

- `papers/repo-template/` containing:
  - `README.template.md` (with placeholders: `{{PAPER_TITLE}}`, `{{PAPER_ID}}`, etc.)
  - `pyproject.template.toml`
  - `scripts/run_all.template.sh`
  - `.github/workflows/ci.yml` (basic: install, pytest, lint)
  - `data/README.md` (generic UKDS data instructions)
  - `data/synthetic/generate_synthetic.template.py`
  - `.gitignore`
  - `LICENSE`

**3B.2 Create extraction tool** in TDL

- `scripts/extract_paper_repo.py`
- CLI: `python scripts/extract_paper_repo.py --paper P01 --output ../p01-trajectory-ph`
- Reads a manifest file: `papers/PXX/repo-manifest.yaml` specifying:
  - Which source modules to include
  - Import path rewriting rules
  - Which results files to include (as examples or .gitignore)
  - Dependencies subset
- Copies, rewrites imports, validates

**3B.3 Document the pipeline** in TDL

- Add section to `CLAUDE.md` under "## Paper Repository Extraction"
- Add to `papers/README.md`
- Create `docs/plans/paper-repo-pipeline.md` with:
  - When to create the repo (after computation is complete, before submission)
  - Checklist: code extracted, synthetic data works, tests pass, DOI created
  - How to update after revisions

**3B.4 Add to `_project.md` schema**

- New field: `repo: null` (or URL when created)
- New field: `doi: null` (or Zenodo DOI when created)

---

## Verification

| Check                                            | Phase | Method                             |
| ------------------------------------------------ | ----- | ---------------------------------- |
| Word count ≤ 10,000 (SocMethod)                  | 1     | wc excl. refs/captions/tables      |
| Page count ≤ 30 (JRSS-A, JRSS-B)                 | 2     | Compile LaTeX, count pages         |
| Cross-references all correct                     | 0,1,2 | Grep for §X.Y, verify targets      |
| Figures/tables renumbered sequentially           | 1,2   | Manual audit                       |
| Abstract numbers match body                      | 0,1,2 | Spot-check all statistics          |
| Citations ↔ references bidirectional             | 0,1,2 | LaTeX compile warnings             |
| `/humanizer` pass                                | 1,2   | Before marking ready               |
| Blind review (SocMethod)                         | 1     | Search for author name/affiliation |
| Grayscale figures (SocMethod)                    | 1     | Visual check                       |
| Self-containment (split)                         | 2     | Read each paper without the other  |
| No duplication (split)                           | 2     | Cross-check tables/results         |
| Code repo: `pip install`, `run_all.sh`, `pytest` | 3     | Run on synthetic data              |
| Zenodo DOI resolves                              | 3     | Browser check                      |

---

## Decisions Made

- Three versions produced in order: SocMethod → JRSS-A → JRSS-B
- Independent researcher, unfunded, no conflicts of interest
- Synthetic dataset for code reproducibility; real data stays under UKDS licence (detail TBD)
- Code repo pipeline becomes reusable infrastructure for Papers 2–10
- Code repo is among final steps in paper process, after computation and before submission

## Further Considerations

1. **JRSS-B data requirement**: The synthetic dataset must reproduce the first-order transition matrix and trajectory length distribution from the paper. It does NOT need to match higher-order statistics — the paper's Wasserstein test specifically shows these differ. This is actually a natural fit: the synthetic data IS a Markov-1 surrogate.
2. **Simultaneous or sequential submission** of JRSS-A/B split papers? Simultaneous is cleanest but requires both ready at once. Sequential means the second paper cites a "submitted" companion.
3. **arXiv preprint** of the combined version could be posted before journal submission, giving both split papers a citable reference and establishing priority.
