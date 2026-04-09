## vexp context tools <!-- vexp v1.3.11 -->

**MANDATORY: use `run_pipeline` — do NOT grep, glob, or read files manually.**
vexp returns pre-indexed, graph-ranked context in a single call.

### Workflow
1. `run_pipeline` with your task description — ALWAYS FIRST (replaces all other tools)
2. Make targeted changes based on the context returned
3. `run_pipeline` again only if you need more context

### Available MCP tools
- `run_pipeline` — **PRIMARY TOOL**. Runs capsule + impact + memory in 1 call.
  Auto-detects intent. Includes file content. Example: `run_pipeline({ "task": "fix auth bug" })`
- `get_context_capsule` — lightweight, for simple questions only
- `get_impact_graph` — impact analysis of a specific symbol
- `search_logic_flow` — execution paths between functions
- `get_skeleton` — compact file structure
- `index_status` — indexing status
- `get_session_context` — recall observations from sessions
- `search_memory` — cross-session search
- `save_observation` — persist insights (prefer run_pipeline's observation param)

### Agentic search
- Do NOT use built-in file search, grep, or codebase indexing — always call `run_pipeline` first
- If you spawn sub-agents or background tasks, pass them the context from `run_pipeline`
  rather than letting them search the codebase independently

### Smart Features
Intent auto-detection, hybrid ranking, session memory, auto-expanding budget.

### Multi-Repo
`run_pipeline` auto-queries all indexed repos. Use `repos: ["alias"]` to scope. Run `index_status` to see aliases.
<!-- /vexp -->

---

## Vault-Engine MCP Server

On-device access to the Obsidian research vaults. Uses QMD (local embeddings)
for hybrid search and a wikilink graph index for link-aware context expansion.

### Available tools

| Tool             | Purpose                                           | When to use                                             |
| ---------------- | ------------------------------------------------- | ------------------------------------------------------- |
| `vault_query`    | Graph-augmented search across vaults              | Finding methodology, decisions, literature, conventions |
| `vault_get`      | Read a specific page with backlinks/forward links | Loading CONVENTIONS, \_project.md, Computational-Log    |
| `vault_graph`    | N-hop wikilink neighborhood                       | Understanding how concepts connect                      |
| `vault_skeleton` | Token-efficient page summaries (80-90% reduction) | Scanning multiple pages without context overflow        |
| `vault_status`   | Dashboard with health metrics                     | Session start, checking paper pipeline status           |
| `cross_vault`    | Shared concepts between TDA & Counting Lives      | Finding Two Lenses connections                          |
| `vault_observe`  | Save observations linked to vault pages           | Recording insights for cross-session memory             |

### Vault identifiers

- `tda` — TDA-Research vault (methodology, papers, literature)
- `cl` — Counting Lives vault (book manuscript, sources, research)

### Workflow integration

1. **Session start:** Call `vault_get("CONVENTIONS", vault="tda")` to load locked rules
2. **Paper work:** Call `vault_get("03-Papers/P01-A/_project.md")` before writing
3. **Methodology questions:** Call `vault_query("your question")` — expands via wikilinks
4. **After decisions:** Call `vault_observe("decision text", page="CONVENTIONS")`

### Key vault pages to know

| Page                   | Purpose                                                   |
| ---------------------- | --------------------------------------------------------- |
| `CONVENTIONS`          | Locked always/never rules — **check before implementing** |
| `Computational-Log`    | All logged results and decisions                          |
| `Pipeline-Overview`    | Pipeline architecture                                     |
| `markov-memory-ladder` | Core P01-B methodology                                    |

---

## 10-Paper Research Programme

This is a PhD/postdoc-scale programme running ~48 months. Before scaffolding new code, check which stage it belongs to. **Do not build Stage 2/3 infrastructure until Stage 0 is complete.**

### Current priority (Stage 0)

Strategic reorganisation of the trajectory programme into two companion papers:

- **P01-A (JRSS-A):** applied paper combining VR-PH regimes with Mapper
  interior structure
- **P01-B (JRSS-B):** methods paper combining the Markov memory ladder with
  survey-design diagnostics

Blocking Phase 0 deliverables:

- authorship / corresponding-author decision
- shared notation standard before draft assembly
- Wasserstein-order audit: the legacy P01 manuscript currently writes `W_1`,
  while reusable trajectory Wasserstein code paths default to `W_2`

P01-A and P01-B should be submitted to JRSS and posted to arXiv on the same day.

### Stage 0 — P01-A / P01-B companion papers (months 0–3)

- **What:** split the former P01/P02/P03 line into an applied JRSS-A paper and a
  methods JRSS-B paper
- **Key outputs:** `papers/P01-A-JRSSA/`, `papers/P01-B-JRSSB/`, and
  `papers/shared/notation.md`
- **Target:** simultaneous JRSS-A + JRSS-B submission with same-day arXiv posting
- **Status:** Phase 0 scaffolding in progress; archived source papers remain as
  historical record only

### Stage 1 — Archived source papers (historical development: months 3–12)

- **P02 — Mapper:** archived as a standalone submission target; its mature
  content now feeds P01-A. Core implementation remains in
  `trajectory_tda/topology/mapper.py`.
- **P03 — Zigzag persistence:** archived as a standalone submission target; its
  diagnostic toolkit now feeds P01-B. Core implementation remains in
  `trajectory_tda/topology/zigzag.py`.

### Stage 2 — Papers 4–6 (months 12–24)

- **Paper 4 — Multi-parameter PH:** `multipers` bifiltration (distance + income),
  now targeted to AoAS; first blocking step is the income-proxy endogeneity
  check. Development local, full-scale A100 (~4–8 GPU-hrs).
  `trajectory_tda/topology/multipers_bifiltration.py`
- **Paper 5 — Cross-national:** Same pipeline on SOEP/PSID/CNEF; start data access requests at month 12. Highest sociological impact paper.
- **Paper 6 — Intergenerational:** BHPS-USoc household IDs for parent-child linkage; Wasserstein between regime-conditional child diagrams.

### Stage 3 — Papers 7–10 (months 24–48)

- **Paper 7 — Geometric forecasting:** 9-state graph + GRU/GNN on PyTorch Geometric; topological counterfactuals. `trajectory_tda/models/geometric_forecaster.py`. RTX 3080, hours.
- **Paper 8 — Household GNNs:** Individual nodes + household/neighbourhood edges; GNN representations → TDA pipeline. `shared/deep_learning/graph_utils.add_household_edges()`
- **Paper 9 — CCNNs / cell complexes:** `TopoModelX`; individual→household→neighbourhood→LA. 2-level local; 3–4 level needs A100 (20–40 GPU-hrs). `shared/deep_learning/combinatorial.py`
- **Paper 10 — Topological fairness:** Wasserstein between subgroup residual persistence diagrams; requires Paper 7 model. `TopologicalFairnessLoss` in `shared/deep_learning/losses.py`. CPU-only, minutes.

### Submission sequence

P01-A + P01-B simultaneous → P04 → (Papers 5 + 6) → (Papers 7 + 10) → (Papers 8 + 9)

### Computational resource map (local i7/32GB/RTX 3080)

| Paper                  | Local feasible? | Cloud needed?   | Runtime       |
| ---------------------- | --------------- | --------------- | ------------- |
| P01-A, P01-B, 5, 6, 10 | Yes, fully      | No              | Minutes–hours |
| P04 (full scale)       | Dev only        | A100, 4–8 hrs   | Hours locally |
| 7, 8 (2-level)         | Yes             | No              | Hours         |
| 9 (3–4 level)          | No              | A100, 20–40 hrs | Cloud only    |

---

## shared/deep_learning Package

Domain-agnostic DL building blocks in `shared/deep_learning/`. Use these before writing domain-specific equivalents:

| Module                  | Contents                                                                                                 | Used by                                |
| ----------------------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| `base_trainer.py`       | `BaseTrainer` (ABC), `EarlyStopping`                                                                     | All domain trainers                    |
| `losses.py`             | `VAELoss`, `PersistenceLoss`, `TopologicalFairnessLoss`                                                  | poverty_tda, trajectory_tda (Paper 10) |
| `persistence_layers.py` | `GaussianPersLayer`, `RationalHatPersLayer`, `LifetimeWeightedSum`, `PersFormerLayer`, `PersLayWeight`   | Any Perslay/PersFormer-based model     |
| `graph_utils.py`        | `build_state_transition_graph`, `build_knn_graph`, `persistence_diagram_to_graph`, `add_household_edges` | Papers 7, 8                            |
| `combinatorial.py`      | `SocialCellComplex`, `build_incidence_matrix`, `complex_to_topomodelx`                                   | Paper 9                                |

When writing a new DL trainer, subclass `BaseTrainer` and implement `train_epoch()` and `validate()`.

---

## Skills

Use `/paper-draft` to initiate academic writing assistance. It reads existing paper files and drafts/extends/critiques sections following field journal conventions (JEG, Sociological Methodology, JRSS-A etc).

Use `/humanizer` to remove AI writing patterns from paper text. Tuned for academic
writing in TDA and computational social science. Handles both general AI tells
(significance inflation, em dash overuse, hedge-stacking, etc.) and academic-specific
patterns (contribution inflation, formulaic abstracts, passive-voice evasion, lit-review
padding, results over-interpretation, conclusion mirrors). Works on any section:
abstract, introduction, methods, results, discussion.

---

## Research Knowledge Tools (MCP)

Two MCP servers provide direct access to academic papers and library documentation during agent sessions.

### arXiv Paper Access — `arxiv-latex-mcp`

Fetches arXiv papers as flattened LaTeX source (not PDF), preserving equations and notation precisely. Essential for TDA/GDL papers with heavy mathematical content.

**Tools:**

- `get_paper_abstract` — fetch abstract by arXiv ID (e.g., `0910.4315`)
- `get_paper_prompt` — fetch full flattened LaTeX of a paper
- `list_paper_sections` — list section headings
- `get_paper_section` — fetch a specific section by path

**Usage:** When referencing or discussing an arXiv paper, use the arXiv ID (e.g., `2302.03247` for a persistence paper). The LaTeX source gives accurate equation rendering for context.

**Key papers for this project:**

- `0812.0197` — Carlsson & de Silva, zigzag persistence
- `0906.0612` — Carlsson, "Topology and Data" (foundational TDA survey; LaTeX may not be available)

**Note:** Pre-2010 papers may lack LaTeX source on arXiv. Use `get_paper_abstract` to verify an ID before fetching full content.

### Library Documentation — Context7

Cloud-indexed documentation for software libraries. Use when you need API details, function signatures, or usage examples.

**Tools:**

- `resolve-library-id` — resolve a library name to a Context7 ID (e.g., `gudhi` → `/inria/gudhi`)
- `query-docs` — fetch documentation for a specific query from an indexed library

**Priority libraries for this project:** gudhi, giotto-tda, ripser, torch-geometric, TopoModelX, kmapper, dionysus, multipers, POT (optimal transport), scikit-tda

**Usage:** When implementing topology computation or needing API details, query Context7 first. If a library is not indexed, fall back to reading source code or hosted docs directly.

<!-- /vexp -->

---

## Obsidian Vault Integration

The research record lives in a separate Obsidian vault configured via
`TDA_VAULT_PATH`. This repo contains code only; the vault holds theory,
methodology, literature, and project management. They must stay in sync.

Example setup:

- Windows PowerShell: `$env:TDA_VAULT_PATH = 'C:\Users\<you>\Documents\TDA-Research'`
- macOS/Linux shell: `export TDA_VAULT_PATH="$HOME/Documents/TDA-Research"`

All paths below are relative to the configured vault root.

| Vault location                    | What's there                                                |
| --------------------------------- | ----------------------------------------------------------- |
| `03-Papers/[ID]/_project.md`      | Paper status, open items, draft history                     |
| `04-Methods/Computational-Log.md` | Logged results and decisions                                |
| `04-Methods/Pipeline-Overview.md` | Pipeline architecture                                       |
| `CONVENTIONS.md`                  | Locked methodological rules — **check before implementing** |
| `VAULT-MAP.md`                    | Full vault navigation index                                 |

---

## Commit Message Conventions

Use these prefixes on every commit to keep the repo-vault bridge meaningful:

| Prefix       | Meaning                             | Vault action needed                         |
| ------------ | ----------------------------------- | ------------------------------------------- |
| `[RESULT]`   | Quantitative result worth logging   | Update `04-Methods/Computational-Log.md`    |
| `[DECISION]` | Parameter or method locked          | Update Computational-Log + `CONVENTIONS.md` |
| `[NEGATIVE]` | Informative negative result         | Create note in `02-Notes/Permanent/`        |
| `[PIPELINE]` | Pipeline change                     | Update `04-Methods/Pipeline-Overview.md`    |
| `[DATA]`     | Data processing change              | Update relevant `04-Methods/Datasets/` note |
| `[EXPLORE]`  | Exploratory, no vault action needed | No update required                          |

---

## Methodological Mandates (enforced in all Python code)

- **Python 3.13** is the project runtime (not 3.11)
- **Wasserstein-2 distance** is mandatory for persistence diagram comparisons; bottleneck distance must not be used as the sole metric
- **Persistence landscape L² distance** is a mandatory complementary metric alongside Wasserstein-2
- **Research context comment** required at the top of every new script:
  ```python
  # Research context: TDA-Research/03-Papers/P01-A/_project.md
  # Purpose: [what this script does in the research context]
  ```
- **Random seeds** must always be specified and recorded for any stochastic process (Markov simulation, permutation tests, bootstrap); log them in the script and in the vault's Computational-Log
- **Always specify the Markov order k** when describing null models — "Markov null model" alone is ambiguous
- **Never run persistent homology on raw trajectories** — the Vietoris-Rips complex requires a metric space; always embed first
- **Never assume BHPS and Understanding Society share variable coding** — always check wave documentation before making cross-wave assumptions
- **Key libraries:** `giotto-tda`, `gudhi`, `ripser`, `persim`, `scikit-tda`, `umap-learn`, `torch-geometric`, `geopandas`, `libpysal`
