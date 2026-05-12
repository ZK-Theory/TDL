# Family-of-Origin (FOO) Cluster Coverage Report
## P01: xhhrel.tab Connected Components via igraph

**Date:** 2026-05-06  
**Auditor:** panel-statistics-agent  
**Script:** `papers/shared/scripts/foo_clusters.R`  
**Reference:** `data/guides/6614/6614_main_survey_user_guide_family_matrix_xhhrel.md`  
**Results JSON:** `results/panel_methodology/harmonisation/foo_clusters_2026-05-06.json`  
**FOO CSV:** `data/derived/foo_clusters_2026-05-06.csv`  

---

## Method

Edge types used (biological relationships only, per variable naming convention in user guide Table 1):
- `bcx_pidp_*` — biological children (up to 16 per person)
- `bpx_pidp_*` — biological parents (up to 4 per person)
- `bsbx_pidp_*` — biological siblings (up to 13 per person)

Graph: undirected, edges deduplicated by canonical (min, max) pair. Isolated individuals (no recorded biological link in any of these columns) are assigned singleton clusters. `igraph::components()` finds connected components.

Missing/inapplicable value code: -8 (per user guide §2 "Missing values and data inconsistencies").

---

## Coverage Results

| Metric | Value |
|---|---|
| xhhrel N rows | 168,281 |
| Deduplicated biological edges | 150,086 |
| Graph vertices (linked individuals) | 114,946 |
| Graph connected components | 27,972 |
| Singleton individuals | 53,335 |
| Total FOO-assigned | 168,281 |
| xwavedat N (denominator) | 168,377 |
| xwavedat members with FOO assignment | 168,281 (99.94%) |
| xwavedat members in cluster size > 1 | 114,946 (68.27%) |

**Coverage verdict: 99.94% — full-sample coverage.**

---

## Cluster Size Distribution

| Cluster size | N individuals |
|---|---|
| 1 (singleton) | 53,335 |
| 2 | 9,652 |
| 3 | 21,579 |
| 4 | 31,740 |
| 5 | 18,190 |
| 6 | 11,268 |
| 7–10 | 15,977 |
| 11–20 | 5,772 |
| >20 | 768 |
| **Max** | **48** |
| **Median** | **3** |

---

## ICC Pre-Check

**Variable:** `b_fihhmngrs_dv` (gross household income, UKHLS wave b)  
**N observations (valid income, cluster size > 1):** 35,100  
**ICC (one-way ANOVA decomposition):** 0.899  

**Important caveat — household income inflation:** `b_fihhmngrs_dv` is a household-level variable. Biological relatives who were co-resident in wave b share an identical income value, mechanically inflating the within-cluster correlation. The ICC of 0.899 should be interpreted as an upper bound; a proper ICC would use individual earnings or employment outcomes after excluding within-household pairs.

**Practical verdict:** Even discounting co-residency inflation, FOO clustering is clearly material (ICC >> 0.05). The 9-state trajectory model should account for FOO family clustering. Recommended approach: include FOO cluster as a random effect grouping variable, or use cluster-robust standard errors at the FOO cluster level.

---

## Variables in Output CSV

`data/derived/foo_clusters_2026-05-06.csv` — one row per sample member:

| Column | Description |
|---|---|
| `pidp` | Cross-wave person identifier (links to all wave files) |
| `foo_cluster` | Integer cluster ID (connected component); singletons have unique IDs |
| `foo_size` | Number of members in this cluster |

---

## Notes on Data Quality

The user guide (§2) flags two data inconsistency variables:
- `bpx_ef`: more than 2 biological parents listed — affects <0.01%–3.17% of sample
- `bpx_rr_ef`: biological parent/child inverse relationships don't match

These are present in the data but not filtered here. Future work may want to exclude or review `bpx_ef > 0` cases for sensitivity analysis.
