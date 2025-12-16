# Advanced TDA Research Opportunities

**Date:** December 15, 2025  
**Context:** Strategic Planning - Hybrid Methods & Longitudinal Analysis  
**Purpose:** Capture research opportunities for enhanced poverty trap analysis

---

## Executive Summary

Three major opportunities have emerged for advancing the poverty TDA methodology:

1. **Hybrid TDA Methods**: Combine Morse-Smale with other topological/statistical techniques (inspired by Gidea & Katz financial approach)
2. **Longitudinal Analysis**: IMD 2025 data now available - enables 3-timepoint analysis (2015, 2019, 2025)
3. **Enhanced Visualization**: Learn from UK government's interactive deprivation maps for public engagement

---

## 1. Hybrid Topological-Statistical Methods

### Context: Learning from Financial TDA Success

**Gidea & Katz (2018) Hybrid Approach:**
- **Persistence Landscapes** (L^p norms) for time series → statistical trend detection
- **Multiple Metrics**: Variance + Autocorrelation + Spectral Density
- **Ensemble Detection**: Combine topological signals for robustness

**Key Insight:** Financial track's success came from combining TDA with classical statistics. Poverty track currently uses **only** Morse-Smale - opportunity for similar hybrid approach.

### Proposed Hybrid Methods for Poverty Analysis

#### 1.1 Persistent Homology + Morse-Smale Fusion

**Current State:** We use Morse-Smale for basin decomposition only

**Enhancement:** Add persistent homology analysis of mobility surface
- **H₀ (Connected Components)**: Identify disconnected high-mobility regions
- **H₁ (Loops/Holes)**: Detect circular barrier structures (e.g., ring of deprivation around city centers)
- **H₂ (Voids)**: Identify 3D cavity structures if elevation added as third dimension

**Implementation:**
```python
# Add to poverty_tda/topology/
from gudhi import CubicalComplex
import persim

# Compute persistence diagram
cubical_complex = CubicalComplex(dimensions=grid_dims, top_dimensional_cells=mobility_grid)
persistence = cubical_complex.persistence()

# Extract H₀ and H₁ features
h0_pairs = [(b, d) for dim, (b, d) in persistence if dim == 0]
h1_pairs = [(b, d) for dim, (b, d) in persistence if dim == 1]

# Combine with Morse-Smale basin analysis
# Cross-validate: Do H₁ holes correspond to trap boundaries?
```

**Expected Benefits:**
- **Multi-scale trap detection**: Persistent homology captures features at all scales
- **Validation**: Cross-check Morse-Smale basins against H₀ components
- **New insights**: H₁ loops may reveal circular poverty structures around urban cores

**Computational Cost:** +30 seconds (GUDHI CubicalComplex fast on 2D grids)

#### 1.2 Topological Data + Spatial Statistics

**Enhancement:** Combine Morse-Smale with spatial econometrics

**Method 1: Spatial Autocorrelation within Basins**
- Compute Moran's I within each basin
- Test hypothesis: "True" traps have high internal autocorrelation (spatial clustering)
- Spurious traps from noise have low autocorrelation

**Method 2: Geographically Weighted Regression (GWR)**
- Model: `mobility ~ education + income + environment` with spatial variation
- Compare basin-wise GWR coefficients
- Identify which factors drive traps in different regions (education in North, housing in South)

**Method 3: Spatial Regime Detection**
- Use Getis-Ord Gi* to identify hot/cold spots
- Cross-validate with Morse-Smale basins
- Quantify agreement: Do basins align with Gi* clusters?

**Implementation:**
```python
# Add to poverty_tda/analysis/
from esda.moran import Moran
from mgwr.gwr import GWR
from libpysal.weights import Queen

# Within-basin autocorrelation
for basin_id, basin_lsoas in basins.items():
    w = Queen.from_dataframe(lsoas[lsoas['basin'] == basin_id])
    moran = Moran(lsoas['mobility'], w)
    basin_metrics[basin_id]['moran_i'] = moran.I
    basin_metrics[basin_id]['p_value'] = moran.p_sim
```

**Expected Benefits:**
- **Validation**: Basins with high Moran's I are spatially coherent traps
- **Mechanism identification**: GWR reveals why different basins trap (education vs housing vs transport)
- **Policy targeting**: Interventions customized by basin-specific drivers

**Computational Cost:** +2-3 minutes (GWR on 30K LSOAs)

#### 1.3 Machine Learning Enhanced Trap Scoring

**Current State:** Simple weighted severity score (mobility + area + barrier height)

**Enhancement:** Train ML model to predict trap "escapability"

**Approach:**
1. **Training Data**: Historical trap basins + subsequent mobility changes (2015→2019)
2. **Features**: 
   - Topological: Basin depth, barrier height, separatrix length
   - Spatial: Moran's I, distance to high-mobility regions
   - Socioeconomic: Education, employment, transport scores
3. **Target**: Mobility improvement 2015→2019 (proxy for "escapability")
4. **Model**: Random Forest or Gradient Boosting

**Implementation:**
```python
# Add to poverty_tda/models/
from sklearn.ensemble import RandomForestRegressor

# Feature engineering
X = basins_df[['depth', 'barrier_height', 'area', 'moran_i', 'education', 'transport']]
y = basins_df['mobility_change_2015_2019']

# Train model
rf = RandomForestRegressor(n_estimators=100)
rf.fit(X, y)

# Feature importance reveals trap drivers
importance = pd.DataFrame({
    'feature': X.columns,
    'importance': rf.feature_importances_
}).sort_values('importance', ascending=False)
```

**Expected Benefits:**
- **Predictive trap scoring**: Identify which traps most resistant to escape
- **Feature importance**: Reveal which factors (topological vs socioeconomic) matter most
- **Intervention targeting**: Focus on traps where interventions likely effective

**Computational Cost:** +1 minute (training), near-instant (inference)

#### 1.4 Graph Neural Networks for Basin Relationships

**Enhancement:** Model inter-basin connectivity and spillover effects

**Approach:**
1. **Graph Construction**: Basins as nodes, separatrices as edges (weighted by barrier height)
2. **Node Features**: Basin properties (mobility, area, population)
3. **GNN Training**: Predict basin mobility from neighbors (spatial contagion hypothesis)
4. **Analysis**: Identify "keystone" basins whose improvement cascades to neighbors

**Implementation:**
```python
# Add to poverty_tda/models/
import torch
from torch_geometric.nn import GCNConv

# Build basin adjacency graph
basin_graph = build_basin_graph(morse_smale_complex)  # Nodes = basins, edges = shared separatrices

# GNN for mobility prediction
class BasinGNN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = GCNConv(in_channels=10, out_channels=16)  # Basin features
        self.conv2 = GCNConv(16, 1)  # Predict mobility
    
    def forward(self, x, edge_index, edge_weight):
        x = self.conv1(x, edge_index, edge_weight).relu()
        x = self.conv2(x, edge_index, edge_weight)
        return x

# Train to predict basin mobility from neighbors
model = BasinGNN()
# ... training loop ...
```

**Expected Benefits:**
- **Spillover quantification**: Measure inter-basin influence
- **Keystone basin identification**: Target basins with high network centrality
- **Cascade analysis**: Simulate intervention effects propagating through basin network

**Computational Cost:** +5 minutes (GPU training), relates to existing Task 5.4 GNN work

---

## 2. Longitudinal Analysis with IMD 2025 Data

### New Data Availability

**IMD 2025 Released:** December 2025 (https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025)

**Available Timepoints:**
- **IMD 2015**: 32,844 LSOAs
- **IMD 2019**: 32,844 LSOAs (current analysis baseline)
- **IMD 2025**: 32,844 LSOAs (newly released)

**Temporal Span:** 10 years (2015-2025) with 4-6 year intervals

### Research Questions Enabled

#### 2.1 Trap Persistence Analysis

**Question:** Which poverty traps persist across 10 years vs emerge/dissolve?

**Method:**
1. Compute Morse-Smale for 2015, 2019, 2025 (3 surfaces)
2. Match basins across timepoints (centroid proximity + mobility correlation)
3. Classify traps:
   - **Persistent:** Present in all 3 timepoints (2015, 2019, 2025)
   - **Emergent:** Absent in 2015, present in 2019/2025
   - **Dissolved:** Present in 2015/2019, absent in 2025
   - **Transient:** Only present in single timepoint (noise or brief shock)

**Expected Findings:**
- **Hypothesis 1:** Post-industrial traps persistent (coal mining regions)
- **Hypothesis 2:** Coastal traps emergent (tourism decline accelerating)
- **Hypothesis 3:** Urban traps dissolved (regeneration programs)

**Policy Relevance:** Target interventions at persistent traps (structural), different approach for emergent (prevention)

#### 2.2 Policy Intervention Effectiveness

**Question:** Do policy interventions correlate with trap dissolution or mobility improvement?

**Data Sources:**
- **Levelling Up Fund** awards 2021-2024 (publicly available)
- **City Deals** (2012-2015)
- **Combined Authority** formation dates
- **Enterprise Zone** designations

**Method:**
1. Identify basins receiving major interventions (£10M+)
2. Compare mobility change 2019→2025 vs matched control basins (no intervention)
3. Quasi-experimental design: Synthetic Control Method or Difference-in-Differences

**Implementation:**
```python
# Add to poverty_tda/analysis/policy_evaluation.py
from sklearn.neighbors import NearestNeighbors

# Match treated basins to controls
treated_basins = basins[basins['received_intervention'] == True]
control_pool = basins[basins['received_intervention'] == False]

# Match on pre-intervention characteristics
matcher = NearestNeighbors(n_neighbors=3)
matcher.fit(control_pool[['mobility_2015', 'mobility_2019', 'area', 'education']])
matches = matcher.kneighbors(treated_basins[same_features], return_distance=False)

# Compute treatment effect
treated_change = treated_basins['mobility_2025'] - treated_basins['mobility_2019']
control_change = matched_controls['mobility_2025'] - matched_controls['mobility_2019']
treatment_effect = treated_change - control_change  # Average Treatment Effect
```

**Expected Benefits:**
- **Evidence-based policy:** Quantify which interventions reduce trap severity
- **Cost-effectiveness:** Compare intervention cost vs mobility improvement
- **Best practices:** Identify successful intervention patterns for replication

#### 2.3 Topological Dynamics: Basin Evolution

**Question:** How do basin structures change over time (not just mobility values)?

**Metrics:**
1. **Basin size change:** Are traps expanding or contracting geographically?
2. **Barrier height change:** Are separatrices strengthening or weakening?
3. **Basin merging/splitting:** Do separate traps merge into larger structures?
4. **Critical point stability:** Do minima locations shift spatially?

**Visualization:**
- Animated basin maps (2015 → 2019 → 2025)
- Alluvial diagrams showing LSOA flow between basins
- Barrier height time series for major separatrices

**Expected Insights:**
- **Trap expansion:** Identify areas where poverty is spreading
- **Barrier strengthening:** Detect increasing structural impediments
- **Basin consolidation:** Large-scale regional decline patterns

#### 2.4 Predictive Modeling: 2025→2030

**Question:** Can we forecast future trap evolution?

**Method:**
1. **Train on historical data:** Use 2015→2019 changes to predict 2019→2025
2. **Validate:** Test predictive accuracy on 2025 actual data
3. **Forecast 2030:** Apply validated model to project 2025→2030 changes

**Features for Prediction:**
- **Topological:** Basin depth, barrier height, separatrix length
- **Temporal:** Mobility velocity (rate of change 2015-2019)
- **Policy:** Announced interventions, infrastructure projects
- **Demographic:** Aging trends, migration patterns

**Expected Benefits:**
- **Early warning system:** Identify basins at risk of deepening
- **Proactive policy:** Target interventions before traps worsen
- **Scenario analysis:** "What if" simulations of policy alternatives

---

## 3. Enhanced Visualization & Public Engagement

### Learning from UK Government Interactive Maps

**Government Tool:** https://deprivation.communities.gov.uk/maps

**Key Features to Emulate:**
1. **Interactive basemap:** Pan, zoom, switch between metrics
2. **LSOA-level detail:** Click for full deprivation profile
3. **Choropleth layers:** Multiple views (IMD, income, education, etc.)
4. **Color schemes:** Intuitive red (deprived) to green (affluent)
5. **Responsive design:** Works on mobile and desktop

### Proposed Enhanced Visualizations

#### 3.1 Interactive Basin Explorer (Phase 10 Enhancement)

**Tool:** Web-based application (Folium + Streamlit or Dash)

**Features:**
- **Basin boundaries overlaid on government IMD map**
- **Click basin → Show properties:**
  - Severity score, mean mobility, population
  - Barrier heights to neighboring basins
  - Gateway LSOAs highlighted
  - Temporal trend (2015-2019-2025)
- **Policy layer:** Show interventions (Levelling Up Fund, City Deals) as markers
- **Comparison mode:** Select two basins for side-by-side comparison

**Implementation Priority:** Phase 10 (Task 10.2 Streamlit deployment)

#### 3.2 Temporal Animation: Basin Evolution

**Tool:** Animated GIF or interactive slider (Plotly or Matplotlib animation)

**Features:**
- **3-frame animation:** 2015 → 2019 → 2025 basin maps
- **Highlight changes:** 
  - Expanding basins (red glow)
  - Contracting basins (green fade)
  - Strengthening barriers (thicker separatrices)
  - Weakening barriers (thinner separatrices)
- **LSOA flow:** Alluvial diagram showing LSOAs changing basins

**Implementation Priority:** Phase 14 (Task 14.2 Temporal Analysis)

#### 3.3 Public-Facing Poverty Atlas

**Tool:** Standalone website (GitHub Pages or similar)

**Target Audience:** 
- Policymakers (local authority leaders, MPs)
- Media (journalists covering regional inequality)
- General public (citizens understanding their area)

**Features:**
- **Postcode search:** "Enter your postcode → See your basin"
- **Local authority view:** Filter to single LAD, show all traps within
- **Downloadable data:** CSVs of trap rankings, basin memberships
- **Methodology explainer:** Accessible language description of Morse-Smale
- **Policy recommendations:** Gateway LSOAs, barrier reduction strategies per basin

**Implementation Priority:** Phase 10 (Task 10.2) or Phase 15 (outreach)

---

## 4. Implementation Roadmap

### Immediate (Phase 9 - Documentation)

**Task 9.2 (Policy Brief):**
- ✅ Mention IMD 2025 release in "Future Directions" section
- ✅ Note longitudinal analysis opportunity (2015-2019-2025)
- ✅ Reference government interactive maps as visualization gold standard

**Task 9.6 (Supplementary Materials):**
- Add brief hybrid methods discussion (H₀/H₁ persistent homology)
- Include IMD 2025 as "data available for future work"

### Near-Term (Phase 11-12)

**New Task 11.6: IMD 2025 Data Integration** (P1 priority)
- Download IMD 2025 data (December 2025 release)
- Verify LSOA boundary compatibility (2021 boundaries)
- Recompute mobility proxy for 2025
- Generate 2025 Morse-Smale complex (75×75 resolution)
- **Deliverable:** `poverty_tda/data/processed/imd_2025/` with mobility surface

**Task 12.7: Basic Longitudinal Comparison** (P1 priority)
- Match basins across 2015, 2019, 2025
- Classify persistence (persistent/emergent/dissolved)
- Compute mobility change per basin
- Statistical tests: Which basins improved significantly?
- **Deliverable:** `poverty_tda/analysis/longitudinal/basin_persistence.py`

### Medium-Term (Phase 14 - International & Extensions)

**Task 14.2 (Already Planned): Temporal Poverty Analysis**
- **Expand scope:** Use 2015, 2019, 2025 (3 timepoints instead of 2)
- Add policy intervention correlation analysis
- Basin evolution metrics (size, depth, barriers)
- Predictive modeling (2025→2030 forecast)

**New Task 14.8: Hybrid TDA Methods Pilot** (P2 priority)
- Implement persistent homology (H₀, H₁) on 2025 surface
- Spatial autocorrelation analysis within basins
- GWR to identify basin-specific drivers
- Compare results to pure Morse-Smale approach
- **Deliverable:** `poverty_tda/topology/hybrid_methods.py`

### Long-Term (Phase 15 - Advanced Research)

**Task 15.9: Basin Network GNN** (P2 priority)
- Implement graph neural network for inter-basin dynamics
- Train on 2015→2019 changes, validate on 2019→2025
- Identify keystone basins with high network influence
- Simulate intervention cascade effects

**Task 15.10: Public Poverty Atlas** (P3 priority)
- Build standalone website with interactive basin explorer
- Postcode search, local authority filtering
- Integrate with government IMD map API (if available)
- Media-friendly data exports and visualizations

---

## 5. Expected Outcomes & Benefits

### Scientific Contributions

1. **Methodological Rigor:** Hybrid TDA approach strengthens poverty trap identification
2. **Temporal Understanding:** First longitudinal topological poverty study (10-year span)
3. **Policy Evaluation:** Causal evidence on intervention effectiveness

### Policy Impact

1. **Targeted Interventions:** Persistent vs emergent traps require different approaches
2. **Evidence-Based Allocation:** Quantify which interventions work
3. **Early Warning:** Predict trap evolution before they worsen

### Public Engagement

1. **Transparency:** Interactive atlas makes research accessible
2. **Local Relevance:** Postcode search connects citizens to findings
3. **Media Amplification:** Visualizations support news coverage

---

## 6. Resource Requirements

### Data

- ✅ **IMD 2015:** Already available (for historical comparison)
- ✅ **IMD 2019:** Current baseline (already processed)
- ✅ **IMD 2025:** Newly released (download required)
- 🔲 **Policy Intervention Data:** Levelling Up Fund awards, City Deals (FOI requests)
- 🔲 **LSOA Boundaries 2021:** Verify compatibility across timepoints

### Computational

- **IMD 2025 Processing:** +3-5 minutes (same as IMD 2019)
- **Longitudinal Analysis:** +10-15 minutes (3 timepoints comparison)
- **Hybrid Methods:** +5-10 minutes per method (persistent homology, GWR, ML)
- **Total Additional:** ~30-45 minutes one-time processing

### Personnel

- **Data Processing:** Agent_Poverty_Data (1-2 days)
- **Longitudinal Analysis:** Agent_Poverty_Topology (3-5 days)
- **Hybrid Methods:** Agent_Poverty_ML (5-7 days)
- **Visualization:** Agent_Poverty_Viz (3-4 days)
- **Total Effort:** ~15-20 days spread across Phase 11-15

---

## 7. Risks & Mitigation

### Risk 1: IMD 2025 Methodology Changes

**Risk:** Government may have changed IMD calculation methods between 2019 and 2025

**Mitigation:** 
- Review IMD 2025 technical documentation carefully
- If methodology changed substantially, normalize/calibrate before comparison
- Sensitivity analysis: Compare results with/without calibration

### Risk 2: LSOA Boundary Changes

**Risk:** LSOA boundaries may have been updated between IMD releases

**Mitigation:**
- Use 2021 LSOA boundaries consistently (official Census boundaries)
- If boundaries changed, use LSOA lookup tables (ONS provides)
- Spatial interpolation for any mismatched LSOAs

### Risk 3: Hybrid Methods Computational Complexity

**Risk:** Some methods (GNN, GWR) may be computationally expensive at scale

**Mitigation:**
- Pilot on subset first (5,000 LSOAs)
- Use GPU acceleration if available (PyTorch for GNN)
- Consider cloud computing (AWS/Azure) for heavy computation

---

## 8. Success Metrics

### Immediate Success (Phase 11-12)

- ✅ IMD 2025 data successfully integrated
- ✅ 3-timepoint Morse-Smale complexes computed (2015, 2019, 2025)
- ✅ Basin persistence classification complete
- ✅ Mobility change statistics calculated

### Medium-Term Success (Phase 14)

- ✅ Policy intervention correlation quantified (treatment effects)
- ✅ Hybrid TDA methods implemented and validated
- ✅ At least one method improves trap identification accuracy by 10%+
- ✅ Temporal forecasting model achieves R² > 0.6

### Long-Term Success (Phase 15)

- ✅ Public atlas deployed with 1,000+ unique visitors
- ✅ Media coverage (3+ articles referencing topological poverty research)
- ✅ Policy adoption (Social Mobility Commission incorporates basin analysis)
- ✅ Academic impact (5+ citations, follow-up studies)

---

## 9. Key References for Hybrid Methods

**Topological Data Analysis:**
- Gidea & Katz (2018): Topological Data Analysis of Financial Time Series
- Bubenik (2015): Statistical Topological Data Analysis using Persistence Landscapes
- Oudot (2015): Persistence Theory: From Quiver Representations to Data Analysis

**Spatial Econometrics:**
- Anselin (1988): Spatial Econometrics: Methods and Models
- Fotheringham et al. (2002): Geographically Weighted Regression
- Getis & Ord (1992): The Analysis of Spatial Association

**Longitudinal Methods:**
- Chetty et al. (2014): Where is the Land of Opportunity? (mobility trends)
- Abadie et al. (2010): Synthetic Control Methods for Comparative Case Studies
- Athey & Imbens (2021): Design-Based Analysis in Difference-in-Differences

**Graph Neural Networks:**
- Kipf & Welling (2017): Semi-Supervised Classification with Graph Convolutional Networks
- Hamilton et al. (2017): Inductive Representation Learning on Large Graphs

---

## Next Steps for Manager_11

**Update Implementation Plan:**
- Add Task 11.6 (IMD 2025 Integration) as P1 priority
- Add Task 12.7 (Basic Longitudinal Comparison) as P1 priority
- Enhance Task 14.2 (Temporal Analysis) scope with 3-timepoint data
- Add Task 14.8 (Hybrid TDA Pilot) as P2 priority
- Add Task 15.9 (Basin GNN) and Task 15.10 (Public Atlas) as P2-P3 priorities

**For Phase 9 Task Assignments:**
- Task 9.2 (Policy Brief): Include IMD 2025 release, longitudinal opportunity
- Task 9.6 (Supplementary): Brief hybrid methods discussion

**Resource Planning:**
- Budget 15-20 additional days for Phase 14 enhancements
- Consider GPU compute resources for GNN experiments
- Plan data access strategy for policy intervention datasets (FOI requests)
