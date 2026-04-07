# Plan: P01-P04 Strategic Reorganization — Journal-Targeted Blending

## TL;DR

Reorganize four technique-first papers into three journal-targeted papers. **P01-A** (JRSS-A): UK career inequality via VR-PH regimes + Mapper interior structure (P01 applied + P02). **P01-B** (JRSS-B): unified hypothesis-testing methodology for PH on longitudinal panel data (P01 methods + P03 diagnostics). **P04** (AoAS): multi-parameter bifiltration, reframed with income-endogeneity check. Simultaneous P01-A + P01-B submission to JRSS + arXiv same day. P04 submitted to AoAS after arXiv posting. SocMethod dropped. Separate self-contained code repos (duplicated embedding code). No fixed deadline.

---

## New Programme Structure

| New ID | Title (working)                                                                   | Source                    | Target | Main-text words | arXiv                      |
| ------ | --------------------------------------------------------------------------------- | ------------------------- | ------ | --------------- | -------------------------- |
| P01-A  | The Geometry of UK Career Inequality: Topology, Regimes, and Mobility Boundaries  | P01 applied + P02         | JRSS-A | ~10,000 + supp  | stat.AP                    |
| P01-B  | Structured Hypothesis Testing for Persistent Homology of Longitudinal Social Data | P01 methods + P03 toolkit | JRSS-B | ~8,000-10,000   | stat.ME                    |
| P04    | Multi-Parameter Persistent Homology Reveals Income-Stratified Career Topology     | P04 reframed              | AoAS   | ~8,000-10,000   | stat.ME cross-list math.AT |

**Submission strategy:** P01-A and P01-B to JRSS + arXiv simultaneously. P04 to AoAS after P01-A/B appear on arXiv (stable citations). Do not wait for JRSS acceptance; arXiv establishes priority.

---

## Phase 0: Infrastructure and Pre-Drafting Deliverables

### 0.1 Create new directory structure

```
papers/
  P01-A-JRSSA/
    _project.md, _outline.md, drafts/, figures/, submissions/jrssa/
  P01-B-JRSSB/
    _project.md, _outline.md, drafts/, figures/, submissions/jrssb/
  shared/
    notation.md          ← shared notation standard (see 0.6)
  P01-VR-PH-Core/       ← archive
  P02-Mapper/            ← archive
  P03-Zigzag/            ← archive
  P04-Multipers-Poverty/ ← keep, update target
```

### 0.2 Authorship decision (BLOCKING)

P04 currently says "Authors: To be determined." Decide before any draft assembly:

- Is a statistician collaborator being added for P01-B or P04?
- Affects CRediT, cover letters, submission accounts, contribution framing
- Must precede Phase 1/2/3 drafting

### 0.3 Archive original paper directories

- P01-VR-PH-Core → status: archived ("Content redistributed to P01-A and P01-B")
- P02-Mapper → status: archived ("Content absorbed into P01-A")
- P03-Zigzag → status: archived ("Content absorbed into P01-B")
- Original drafts preserved as historical record

### 0.4 Update P04 metadata

- target-journal → "Annals of Applied Statistics"

### 0.5 Shared submission statements (blocked on 0.2)

Write once, adapt per paper: Data Availability (USoc DOI: 10.5255/UKDA-SN-6614-19, BHPS DOI: 10.5255/UKDA-SN-5151-3, UKDS licence + synthetic data), Code Availability (paper-specific GitHub + Zenodo DOI), Ethics, Conflicts, Funding, CRediT.

### 0.6 Notation standardisation document (BEFORE drafting)

Create `papers/shared/notation.md` — 2-page reference reconciling conflicting notation:

| Concept              | P01   | P03                                                      | P04                              | Unified convention          |
| -------------------- | ----- | -------------------------------------------------------- | -------------------------------- | --------------------------- |
| Simplicial complex   | $K_t$ | $K_1 \rightsquigarrow K_1 \cap K_2 \leftarrow K_2$ tower | $K_{\theta,\alpha}$ bifiltration | Define per paper context    |
| Persistence diagram  | $D$   | (unstandardised)                                         | (unstandardised)                 | Standardise                 |
| Wasserstein distance | $W_1$ | (varies)                                                 | (varies)                         | See computation check below |

Key conflict: P01-B §3 draws on both P01 and P03 methodology. Notation MUST be reconciled before drafting, not after.

**Wasserstein order computation check (BLOCKING).** The table above lists P01 as using $W_1$ and the project mandate requires $W_2$. This is potentially a scientific error, not just a notation inconsistency. P01 v8 computes the **1-Wasserstein distance** via `gudhi.wasserstein`; P03 v2 computes **2-Wasserstein distances** in the Wasserstein matrix analysis. These are genuinely different distances ($L^1$ vs $L^2$ ground metric on the birth-death plane) — their results are not interchangeable. Before standardising notation, verify whether P01 and P03 use the same Wasserstein order computationally. If different, both papers need a sentence explaining the choice of order; they cannot both be relabelled $W_2$ without checking the underlying code. This is a Phase 0 computation check, not a pure writing decision.

### 0.7 Compulsory fixes (assigned to inheriting paper)

| Fix                                                            | Assigned to      |
| -------------------------------------------------------------- | ---------------- |
| Wasserstein p-value justification (Gretton 2012 / Turner 2014) | P01-B §3.3       |
| Supplementary A: imputation balance by regime                  | P01-A supplement |
| Figure S1: UMAP-16D scatter (from `embeddings_umap16.npy`)     | P01-A supplement |
| Remove JEL codes                                               | All              |

### 0.8 Update programme documentation

- CLAUDE.md programme table: new IDs, targets, arXiv categories
- copilot-instructions.md: submission sequence, stage descriptions
- **Email RSS editorial office:** notify of companion submission to JRSS-A and JRSS-B simultaneously, confirm cover letter language, ask whether joint or coordinated handling applies. JRSS-A and JRSS-B share editorial infrastructure at the Royal Statistical Society; a brief pre-submission query could smooth the review process.

### 0.9 Humanizer pass definition

**Humanizer pass** (referenced at the end of every Phase): run the `/humanizer` command to remove AI-generation register patterns, ensure natural academic cadence, check for repeated sentence structures, and verify hedging language is appropriately calibrated for each journal's tone. Applied to every draft before submission review.

---

## Content Allocation Map

### P01-A (JRSS-A) content sources

| Content                              | Source                     | Disposition                                                                                                                                                                                                                                          |
| ------------------------------------ | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| §1 Introduction (inequality framing) | P01 v8 §1                  | Rewrite as: statistical characterisation of career inequality — what PH adds that Markov and sequence analysis cannot provide. Not technique-first, but JRSS-A is a statistics journal; foreground the statistical contribution, not pure sociology. |
| §2 Literature                        | P01 v8 §2.3 + P02 v5 §2    | SUBSTANTIVE only: mobility, stratification, life-course. Reference P01-B for TDA testing lit. No OM/VR-PH history.                                                                                                                                   |
| §3 Data + methods                    | P01 v8 §3.1–3.3, P02 v5 §3 | ~200 words on embedding: "We embed in PCA-20D following P01-B §3." Pipeline detail to supplement/P01-B. Mapper methodology from P02.                                                                                                                 |
| §4 Global topology + regimes         | P01 v8 §4.1–4.4            | VR results, 7 regimes, transitions, Wasserstein results (interpretation only, ref P01-B for methodology)                                                                                                                                             |
| §4 OM baseline comparison            | P01 v8 §3.7, §5.1          | 1 paragraph: ARI 0.26 at $k=7$, silhouette 0.215, regime-level profile correlations 0.97 (high-employment) to 0.02 (mixed-churn). Frames TDA's added value as formal null testing, not regime typology.                                              |
| §5 Within-regime anatomy (Mapper)    | P02 v5 §4–5                | Agglomerative coverage + DBSCAN dense-region as two complementary views. 24-config sensitivity grid → supplement entirely. Saves ~2,000 words.                                                                                                       |
| §6 Stratified + cross-survey         | P01 v8 §4.5–4.7            | BHPS: regime structure (k=8) stays. Wasserstein discrepancy replication referenced as "confirmed in P01-B §4."                                                                                                                                       |
| §7 Discussion                        | P01 v8 §5 + P02 v5 §6      | PH: "7 regimes, sticky." Mapper: "here is the transient/absorbing boundary."                                                                                                                                                                         |

### P01-B (JRSS-B) content sources

| Content                            | Source                  | Disposition                                                                                                                                                                                     |
| ---------------------------------- | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| §1 Introduction                    | New                     | "When PH is computed on panel data, how do you know features are real?"                                                                                                                         |
| §2 Related work                    | P01 v8 §2.4 + P03 v2 §2 | TDA hypothesis testing lit. Zigzag in ~1.5pp as "the temporal TDA technique that makes survey confounds topologically visible" (Carlsson–de Silva 2010, Bendich 2016). NOT a full zigzag paper. |
| §3.2 Markov Memory Ladder          | P01 v8 §3.4             | 5-level null hierarchy, formal statement                                                                                                                                                        |
| §3.3 Scalar vs diagram-level tests | P01 v8 §4.3.2–3         | Wasserstein discrepancy, energy/MMD (Gretton 2012, Turner 2014)                                                                                                                                 |
| §3.4 Survey-design diagnostics     | P03 v2 §3.6–3.7         | Spanning-individual decomposition, pool-draw nulls. TECHNIQUE-AGNOSTIC: applies to any time-varying topological analysis, not just zigzag.                                                      |
| §4 Application (UK careers)        | P01 v8 + P03 v2         | STRICT SCOPE — testing framework only (see scope rule below)                                                                                                                                    |
| §5 Discussion                      | New                     | Transportability to SOEP/PSID/CNEF. Practitioner guidance.                                                                                                                                      |

### P01-B §4 scope rule (strict)

P01-B §4 demonstrates the testing framework ONLY. It shows:

- Which Markov ladder levels pass/fail under each statistic (p-value table, null distributions)
- Scalar–Wasserstein discrepancy (specific numbers + interpretation)
- Survey-confound decomposition on BHPS/USoc (block ratio, spanning-individual)
- BHPS Markov-1 $H_1$ rejection at $p = 0.000$ (methodological replication)
- Practitioner guidance for any panel dataset

It does NOT discuss: regime profiles, escape rates, gender stratification, poverty trap interpretation, Mapper results. Those belong to P01-A and P04.

### BHPS split rule

- "How UK careers looked 1991–2008" → P01-A §6
- "How our methodology performs on a second dataset" → P01-B §4
- BHPS regime structure ($k = 8$, qualitative similarity) → P01-A
- BHPS Wasserstein discrepancy replication → P01-B
- BHPS Markov-1 $H_1$ rejection ($p = 0.000$, stronger than USoc $p = 0.086$) → P01-B (primary value: discrepancy replicates cross-era). Referenced briefly in P01-A §6 as "confirmed in P01-B §4."

### P04 (AoAS) changes from current

| Change                                         | Detail                                                                                                                                                                                           |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Income-proxy endogeneity check (NEW, BLOCKING) | Regress income proxy on PC1–PC20, report $R^2$. If high: explain why bifiltration still adds information beyond PC1 projection (answer: joint topology, not projection). Must precede reframing. |
| Proxy income as methodological STRENGTH        | Ordinal income states available in any panel with employment records → broader applicability. Continuous income (P05) tests generalisation; proxy tests whether method works with minimal data.  |
| Reframe introduction                           | Dual contribution: bifiltration methodology + poverty trap application                                                                                                                           |
| Strengthen methodology                         | Formal signed measure properties, single-parameter PH comparison                                                                                                                                 |
| 5,000-landmark sensitivity                     | Required computation                                                                                                                                                                             |
| Stable citations                               | Reference P01-A/B via arXiv preprints                                                                                                                                                            |

---

## Phase 1: P01-A (JRSS-A) — Assembly

**Readiness: HIGH.** P01 v8 + P02 v5 both mature. Can start immediately after Phase 0.

### Word budget

JRSS-A typical: 8,000–12,000 main-text words + supplement. Raw merged P01 (~17k) + P02 (~12k) = ~29k. Target: ~10,000 main text. Requires ~65% cut.

| Section                           | Word target | Strategy                                                                                                         |
| --------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------- |
| §1 Introduction                   | ~800        | Career inequality question, not technique survey                                                                 |
| §2 Background                     | ~1,200      | Substantive lit only. Reference P01-B for TDA testing lit. No OM/VR-PH history.                                  |
| §3 Data and Methods               | ~1,500      | ~200 words on embedding pipeline. Remainder: brief VR-PH + Mapper methodology                                    |
| §4 Global Topology + Regimes      | ~2,500      | VR results, 7 regimes, transitions, Wasserstein results (ref P01-B)                                              |
| §5 Within-Regime Anatomy (Mapper) | ~2,000      | Two views (agglomerative + DBSCAN). 24-config grid to supplement.                                                |
| §6 Stratified + Cross-Survey      | ~1,200      | Gender/age/education/regional + BHPS regime replication                                                          |
| §7 Discussion                     | ~800        | Combined policy implications                                                                                     |
| **Total main text**               | **~10,000** |                                                                                                                  |
| Supplement                        | ~5,000+     | Embedding detail, imputation balance, UMAP scatter, Mapper sensitivity, additional viz, detailed regime profiles |

### Steps

1. Write unified outline with single argument arc — PH (global → regimes → stratified) flows into Mapper (within-regime anatomy) as deepening the regime story. One integrated analysis, not two bolted. (_parallel with Phase 2 pre-req_)

2. Draft v1 following section targets. Key principles:
   - §3 is output-focused ("the embedding produces X"), not pipeline-focused
   - §5 presents Mapper as two analytical lenses, NOT a sensitivity analysis
   - BHPS §6 follows split rule: regime structure only; Wasserstein validation referenced to P01-B

3. Harmonise figures — renumber from both papers, deduplicate overlapping persistence diagrams

4. Generate missing supplementary material:
   - Figure S1: UMAP-16D scatter from `embeddings_umap16.npy`
   - Supplementary A: imputation balance by regime
   - Mapper 24-config sensitivity grid (moved from main text)

5. JRSS-A formatted submission: RSS style, title page, abstract ≤250 words, word count, supplement as separate doc

6. Humanizer pass

7. Hold for simultaneous submission with P01-B + arXiv posting

### Phase 1 Verification

- Main text ≤12,000 words (target ~10,000)
- Abstract ≤250 words
- Self-contained: methodology summarised, not just cited
- Mapper integrated into argument arc, not appended
- BHPS follows split rule (no methodology validation content)
- No technique-first framing in introduction
- §3 embedding pipeline ≤200 words main text
- Mapper sensitivity grid entirely in supplement
- All figures renumbered and cross-refs updated

### Key files

- `papers/P01-VR-PH-Core/drafts/v8-2026-03.md` — primary applied content
- `papers/P02-Mapper/drafts/v5-2026-04.md` — Mapper §4–5, figures
- `trajectory_tda/viz/paper_figures.py` — figure regeneration

---

## Phase 2: P01-B (JRSS-B) — Assembly

**Readiness: MODERATE.** P01 methodology mature (v8), P03 at v2. Core tools computed; maturation is formalisation and writing, not new discovery.

### Pre-requisite: P03 maturation (start immediately, parallel with Phase 1)

1. **Formalise spanning-individual decomposition** — P03 v2 §3.7: formal statement, explicit algorithm, connection to survey methodology (~2 weeks)

2. **Formalise pool-draw null model** — P03 v2 §3.6: explicit null hypothesis, relationship to bootstrap methods (~1 week)

3. **Complete macroeconomic correlation** — GDP/unemployment/Gini correlation with topological measures. Needed to show toolkit separates survey artefacts from genuine macro effects (~1 week computation + writing)

4. **Verify sensitivity grid** — 2D grid ($\varepsilon \times L$, 44 configs). Check computation status (~days if done, ~1 week if not)

5. **Verify sub-sampled Betti comparison** — BHPS-subsample vs USoc: killer evidence for survey-design confound (~days)

### Steps (after P03 reaches ~v3–v4)

1. Create `papers/P01-B-JRSSB/` with `_project.md`, `_outline.md`

2. Draft unified methodology paper (~8,000–10,000 words):
   - §1 Introduction (~800): Two sub-problems — (a) is topology from the DGP or sequential structure? (b) is temporal change substantive or survey-design-driven?
   - §2 Related Work (~800): TDA hypothesis testing. Zigzag in ~1.5pp: "temporal TDA that makes confounds visible" (Carlsson–de Silva 2010, Bendich 2016). Full zigzag treatment stays in P03 archive.
   - §3 Framework (~3,500):
     - §3.1 Setup and notation (~400, uses `papers/shared/notation.md`)
     - §3.2 Markov Memory Ladder (~1,200): 5-level null hierarchy
     - §3.3 Scalar vs Diagram-Level Tests (~800): Wasserstein discrepancy, MMD connection
     - §3.4 Survey-Design Diagnostics (~1,100): spanning-individual decomposition, pool-draw nulls. Presented as TECHNIQUE-AGNOSTIC.
   - §4 Application (~2,500, STRICT SCOPE per scope rule):
     - §4.1 Data and embedding (~400, brief, ref P01-A)
     - §4.2 Markov ladder results (~800)
     - §4.3 Survey-design decomposition (~800)
     - §4.4 Genuine temporal signal: flexibilisation within BHPS era (~500). **Framing guidance:** this subsection must read as "the toolkit successfully isolates genuine structural signal from survey-design artefact" — the UK flexibilisation content (self-employment share driving complexity, not GDP growth) is illustrative evidence that the diagnostics work, not the paper's sociological conclusion. Avoid sociology-register language; maintain JRSS-B statistics-methodology framing throughout.
   - §5 Discussion (~800): Transportability, practitioner guidance
   - Supplement: Full permutation distributions, sensitivity, macro correlations

3. Notation uses Phase 0.6 notation document throughout

4. JRSS-B formatted submission: RSS style, mathematical typesetting

5. Humanizer pass

### Phase 2 Verification

- Methodology clearly transportable (not UK-specific)
- Framework complete enough for practitioner implementation
- Application section follows strict scope rule (no regime profiles, escape rates, stratification, Mapper)
- Scalar–Wasserstein discrepancy clearly explained
- Survey-confound toolkit general, not just BHPS/USoc finding
- Zigzag exposition brief (~1.5pp) and motivating, not primary
- Cross-references to P01-A informational, not structural dependencies
- BHPS Markov-1 $H_1$ result included as methodological replication

### Key files

- `papers/P01-VR-PH-Core/drafts/v8-2026-03.md` §3.4, §4.3 — Markov ladder
- `papers/P03-Zigzag/drafts/v2-2026-03.md` §3.6–3.7, §4 — diagnostic toolkit
- `trajectory_tda/validation/wasserstein_null_tests.py` — null model implementations

---

## Phase 3: P04 (AoAS) — Reframing

**Readiness: MODERATE.** v4 with exploratory computation. Independent timeline but sequenced after P01-A/B arXiv posting.

### Steps

1. **Income-proxy endogeneity check (BLOCKING, do first):**
   - Regress income proxy on PC1–PC20, report $R^2$
   - If $R^2$ LOW: concern moot, report in §4.1, one sentence
   - If $R^2$ HIGH: add paragraph in §3 explaining why bifiltration adds information beyond PC1 projection (answer: bifiltration decomposes joint topology, not single-axis projection)
   - This neutralises the single most likely AoAS rejection reason _regardless of outcome_

2. **Proxy income reframing** — not just "scope limitation" but methodological STRENGTH:
   - Ordinal income states available in any panel with employment records → broader applicability
   - Continuous income (P05) tests generalisation to richer data
   - Proxy version tests whether method works with minimal data

3. **Reframe introduction** for AoAS: dual contribution (bifiltration methodology on panel data + poverty trap application)

4. **Strengthen methodology:** formal signed measure properties, comparison with single-parameter PH (reference P01-A)

5. **Complete 5,000-landmark sensitivity** — required computation

6. **Add companion paper references** via P01-A/B arXiv preprints

7. **AoAS formatted submission:** AoAS uses the IMS format (`.ims` LaTeX class, available from IMSTAT). No strict page limit but expects ~25–40 pages in practice. Supplementary material submitted as a separate file. AoAS strongly favours a reproducibility statement (link to code repo + data access instructions). The IMSTAT format is different from RSS style — do not reuse JRSS templates.

8. **Humanizer pass**

### Phase 3 Verification

- Income-endogeneity $R^2$ reported and interpreted
- Proxy income framed as strength (broader applicability), not just limitation
- Both methodological and substantive contributions clear
- 5,000-landmark sensitivity complete
- Single-parameter baseline comparison included (reference P01-A)
- P01-A/B cited via arXiv DOIs
- AoAS format compliance: IMS `.ims` class used, supplementary as separate file, reproducibility statement present

### Key files

- `papers/P04-Multipers-Poverty/drafts/v4-2026-04.md`
- `trajectory_tda/topology/multipers_bifiltration.py`

---

## Phase 4: Code Repositories

Separate self-contained repos per paper. **Embedding code duplicated across all three repos** — standard academic reproducibility approach (reviewers get self-contained repo, no cross-repo dependency management). Accept the maintenance cost of three copies.

### 4.1 P01-A repo: `stephendor/p01a-career-inequality-topology`

- PCA-20D embedding pipeline (duplicated)
- VR-PH computation (from `trajectory_tda/topology/`)
- Mapper computation (from `trajectory_tda/topology/mapper.py`)
- Regime identification and stratified analysis
- BHPS replication scripts
- Synthetic data generator (9-state space, transition matrix, trajectory length distribution)
- Numbered reproduction scripts (01–NN)

### 4.2 P01-B repo: `stephendor/p01b-ph-hypothesis-testing`

- PCA-20D embedding pipeline (duplicated)
- Markov memory ladder (null model hierarchy)
- Wasserstein vs total-persistence comparison tools
- Survey-design diagnostic toolkit (spanning-individual, pool-draw nulls)
- Zigzag persistence scripts
- Synthetic data generator
- Numbered reproduction scripts

### 4.3 P04 repo: `stephendor/p04-multiparameter-poverty`

- PCA-20D embedding pipeline (duplicated)
- Bifiltration computation (multipers)
- Signed measure decomposition
- Income-proxy regression check
- Permutation null testing
- Sensitivity analysis (2,000 + 5,000 landmarks)
- Synthetic data generator
- Numbered reproduction scripts

### Verification (all repos)

- `uv run pytest` passes on synthetic data
- Numbered scripts reproduce all paper figures/tables
- `pyproject.toml` has only required dependencies
- README documents full reproduction workflow
- No cross-repo dependencies
- GitHub + Zenodo integration, tag v1.0.0
- **JRSS-B timing note:** JRSS-B requires publicly archived code with a persistent DOI (Zenodo or equivalent) to be in place **before acceptance**, not just before initial submission — reviewers may request it during revision. The P01-B repo must be finalised and tagged v1.0.0 before responding to any revision request. Plan accordingly: repo extraction for P01-B should be prioritised over P01-A and P04 repos if revision arrives before all repos are complete.

---

## Sequencing and Dependencies

```
Phase 0 (infrastructure + notation + authorship)
    │
    ├── Phase 1 (P01-A assembly) ← start immediately, P01 v8 + P02 v5 ready
    │
    ├── Phase 2 pre-req (P03 maturation) ← start immediately, parallel
    │     │
    │     └── Phase 2 (P01-B assembly) ← blocked on P03 ~v3–v4
    │
    └── Phase 3 step 1 (P04 endogeneity check) ← start immediately, independent
          │
          └── Phase 3 (P04 reframing) ← blocked on endogeneity result + P01-A/B arXiv

Phase 1 + Phase 2 done → Simultaneous P01-A + P01-B submission + arXiv posting
Phase 3 done → P04 submission to AoAS (after P01-A/B on arXiv)
Phase 4 (repos) → after drafts finalised, before submission
```

**Critical path:** P03 maturation → P01-B assembly → simultaneous submission with P01-A.
P01-A will be ready first; use wait time for polish, supplement, and P04 endogeneity check.

---

## Decisions

- **SocMethod dropped** — resources on higher-impact JRSS targets
- **Simultaneous JRSS-A + JRSS-B + arXiv** — maximises coherence, establishes priority, gives P04 stable citations
- **P04 upgraded to AoAS** — better fit for methodology+application hybrid
- **arXiv categories:** P01-A = `stat.AP`, P01-B = `stat.ME`, P04 = `stat.ME` cross-list `math.AT`
- **Separate code repos with duplicated embedding** — self-contained per paper, accept maintenance cost
- **BHPS split rule:** "how UK careers looked" → P01-A; "how methodology performs" → P01-B
- **P01-B §4 strict scope:** testing framework demonstration only, no regime profiles/escape rates/stratification/Mapper
- **Zigzag in P01-B:** brief (~1.5pp), motivating, technique-agnostic framing; NOT a full zigzag paper
- **P04 sequenced after arXiv:** submit to AoAS after P01-A/B posted; do not wait for JRSS acceptance
- **Authorship:** must be resolved in Phase 0 before any drafting

## Risks

1. **P01-A length** — raw ~29k words needs ~65% cut to ~10,000. Mitigation: concrete word targets per section; aggressive deduplication; §3 embedding ≤200 words; Mapper sensitivity grid to supplement.

2. **P01-B depends on P03 maturation** — P03 at v2, needs ~v3–v4. Mitigation: core tools already computed; maturation is formalisation and writing, not new computation. Start immediately parallel with Phase 1.

3. **Self-containment** — each paper must stand alone. Mitigation: P01-A summarises methodology (not just cites P01-B); P01-B has own application section with strict scope rule (not just cites P01-A).

4. **P04 income-proxy endogeneity** — HIGHEST REJECTION RISK if unaddressed. PC1 is described as "income gradient proxy" in P02; bifiltration's income parameter may be partially encoded in Rips distances. Mitigation: regress on PC1–PC20, report $R^2$, interpret either outcome. A single computation neutralises the risk.

5. **P04 proxy-income limitation** — AoAS reviewers may push for real income. Mitigation: reframe as broader applicability (ordinal states available in any employment panel); continuous income framed as generalisation test, not missing prerequisite.

## Resolved Further Considerations

1. **Zigzag in P01-B:** Brief (~1.5pp). Framed as motivating: "the temporal TDA technique that makes survey confounds topologically visible." Diagnostics are technique-agnostic. Full zigzag treatment stays in P03 archive. Paper identity is the testing framework, not zigzag.

2. **P04 submission timing:** Proceed independently but sequence after P01-A/B arXiv. P04 references "Paper 1 in this programme" throughout; arXiv preprints provide stable citations. Do not wait for JRSS acceptance (adds 12–18 months).

3. **arXiv preprints:** Yes, post simultaneously with journal submission. Category choices matter for visibility: `stat.AP` (P01-A), `stat.ME` (P01-B), `stat.ME` + `math.AT` (P04). P01-B on `stat.ME` specifically reaches TDA-in-panel-data researchers in neuroscience, public health, economics who may cite quickly.
