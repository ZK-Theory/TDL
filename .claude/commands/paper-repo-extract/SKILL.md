# /paper-repo-extract — Extract a Standalone Paper Repository

Create a standalone reproducibility repository from the TDL monorepo for a paper.
Required before journal submission (Zenodo DOI needed in submission statements).

## Usage

```
/paper-repo-extract [paper]
```

Example: `/paper-repo-extract P01-B`

**Precondition:** All paper computation must be complete and results files must exist.

---

## Process overview

| Step | Action | Output |
|---|---|---|
| 1 | Confirm paper readiness | `papers/PXX/_project.md` status check |
| 2 | Trace imports from entry scripts | Module dependency list |
| 3 | Create repo manifest | `papers/PXX/repo-manifest.yaml` |
| 4 | Scaffold standalone directory | `../pXX-[slug]/` with full structure |
| 5 | Create synthetic data generator | `data/synthetic/generate_synthetic_data.py` |
| 6 | Rewrite imports | All `trajectory_tda.*` → `src.*` |
| 7 | Write smoke tests | `tests/test_smoke.py` passes on synthetic data |
| 8 | Checklist + GitHub/Zenodo handoff | Numbered manual steps |

---

## Repo directory structure

```
pXX-[slug]/
├── README.md  LICENSE  pyproject.toml  .gitignore
├── src/           # copied source modules, imports rewritten
├── data/synthetic/generate_synthetic_data.py
├── results/       # pre-computed JSON/NPY artifacts
├── scripts/
│   ├── 01_[first_step].py
│   └── 02_[second_step].py
└── tests/test_smoke.py
```

---

## repo-manifest.yaml schema

```yaml
paper: PXX
repo-name: pXX-[slug]
zenodo-concept-doi: null   # fill after Zenodo setup
github-url: null           # fill after repo creation
source-files:
  - src/: trajectory_tda/topology/permutation_nulls.py
scripts:
  - "01_embed.py": trajectory_tda/scripts/bhps_pipeline.py
results:
  - results/trajectory_tda_integration/null_markov_k1.json
dependencies:
  - giotto-tda>=0.6
  python: ">=3.13"
```

---

## After repo is on GitHub

```
1. zenodo.org → GitHub → enable repo → flip toggle
2. Tag v1.0.0 on GitHub → Zenodo auto-mints DOI
3. Update papers/PXX/_project.md:
     repo: https://github.com/stephendor/pXX-[slug]
     doi: https://doi.org/10.5281/zenodo.[ID]
4. Update papers/shared/submission-statements.md
```

## Hard constraints

- No real BHPS/USoc data in the repo (data access agreement)
- Include UKDA data disclaimer in README.md
- `uv run pytest tests/` must pass without TDL installed
- Synthetic data must match statistical properties only, not real values
