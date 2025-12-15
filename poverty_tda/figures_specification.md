# Figures Specification for Poverty TDA Paper
## Journal of Economic Geography Submission

**Paper Title:** UK Poverty Traps: A Topological Data Analysis Approach  
**Target Journal:** Journal of Economic Geography  
**Total Figures:** 6-7 (including tables integrated as figures)

---

## Figure 1: Study Area & Geographic Context

**Type:** Geographic map  
**Dimensions:** Full page width (190mm), landscape orientation  
**File Format:** PDF (vector) or high-res PNG (300+ DPI)

**Content Requirements:**
- Base map: England & Wales LSOA boundaries (n=31,810), light gray fill, thin black outlines
- LAD boundaries: Thicker black lines (0.5pt) for reference
- **Overlay 1 - SMC Cold Spots (n=13):** Red hatching or solid red fill for LAD polygons
- **Overlay 2 - Post-Industrial Deprived (n=10):** Blue hatching or solid blue fill
- **Overlay 3 - Coastal Deprived (n=7):** Green hatching or solid green fill
- Legend: Clear labels for all categories
- Scale bar: Kilometers, positioned bottom-right
- North arrow: Top-right corner
- Annotations: Label key cities (London, Manchester, Birmingham, Newcastle, Blackpool)

**Data Sources:**
- LSOA boundaries: ONS Open Geography Portal
- SMC cold spots: Social Mobility Commission reports (2017-2022)
- Known deprived: Manual curation from research literature

**Software:** GeoPandas + Matplotlib or QGIS export

**Purpose:** Establish geographic context and distribution of validation datasets

---

## Figure 2: Mobility Surface & Critical Points

**Type:** 2D heatmap with overlays OR 3D surface plot  
**Dimensions:** Full page width (190mm) for 2D, half page (90mm) if 3D  
**File Format:** PDF (vector preferred)

**Content Requirements:**
- **Base layer:** Mobility surface interpolated to 75×75 grid
  - Color scale: Diverging (red = low mobility, blue = high mobility)
  - Use perceptually uniform colormap (e.g., viridis, RdYlBu_r)
  - Include colorbar with labeled ticks (0.0 to 1.0)
- **Overlay - Critical Points:**
  - Minima (poverty traps, n=357): Red circles, size=10pt
  - Saddles (barriers, n=693): Yellow triangles, size=8pt
  - Maxima (opportunity peaks, n=337): Green stars, size=10pt
  - Legend for point types
- **Annotations:** Label top 5 traps (Blackpool, Great Yarmouth, Middlesbrough, Tendring, South Tyneside)
- **Grid axes:** X = Easting (km), Y = Northing (km), or Lon/Lat

**Data Sources:**
- Mobility surface: `poverty_tda/validation/mobility_surface.vti` (processed)
- Critical points: Extracted from TTK Morse-Smale complex output

**Software:** Matplotlib (Python) or Paraview export

**Purpose:** Visualize raw mobility landscape and Morse-Smale decomposition

---

## Figure 3: Basin Structure & Separatrices

**Type:** Geographic map with topological overlay  
**Dimensions:** Full page width (190mm), landscape  
**File Format:** PDF (vector) or PNG (300 DPI)

**Content Requirements:**
- **Base map:** LSOA boundaries (light gray, 30% opacity)
- **Basin coloring:** Each descending manifold (basin) colored by trap severity score
  - Color scale: Continuous from light yellow (low severity) to dark red (high severity)
  - Transparency: 60% to allow LSOA boundaries to show through
- **Separatrices:** Black lines (1.5pt width) showing basin boundaries (saddle-saddle connections)
- **Top 10 traps labeled:** Black text with white halo, rank + LAD name
- **Legend:** Severity score colorbar (0.0 to 1.0)
- **Inset map (optional):** Zoomed view of Blackpool basin for detail

**Data Sources:**
- Basins: TTK descending manifolds, mapped to LSOAs
- Separatrices: TTK separatrix geometry
- Trap rankings: Computed from basin scoring algorithm

**Software:** GeoPandas + Matplotlib or Paraview export → QGIS

**Purpose:** Demonstrate basin of attraction concept and spatial partitioning

---

## Figure 4: Social Mobility Commission Validation

**Type:** Combination figure (bar chart + scatterplot)  
**Dimensions:** Full page width (190mm), split into two panels (A, B)  
**File Format:** PDF (vector)

**Panel A - Bar Chart (left, 90mm width):**
- **X-axis:** Threshold categories (Bottom 25%, Bottom 33%, Bottom 50%, Random Baseline)
- **Y-axis:** % of SMC Cold Spots Captured (0-100%)
- **Bars:** Blue bars for observed rates, red dashed line for random baseline (25%, 33%, 50%)
- **Labels:** Exact percentages on top of bars (61.5%, 69.2%, 84.6%, 25%)
- **Annotations:** Statistical significance (p < 0.01) with asterisks

**Panel B - Scatterplot (right, 90mm width):**
- **X-axis:** All LADs (317 total), sorted by trap percentile rank
- **Y-axis:** Trap percentile rank (0-100)
- **Points:** Gray dots for all LADs (small, 3pt), red diamonds for SMC cold spots (large, 10pt)
- **Quartile bands:** Horizontal lines at 25th, 50th, 75th percentiles
- **Annotations:** Label SMC cold spots in bottom quartile (n=8) with LAD names

**Data Sources:**
- SMC cold spots: 13 LADs from SMC reports
- Trap rankings: Computed from basin scoring
- Statistical tests: χ² test results

**Software:** Matplotlib (Python) with seaborn styling

**Purpose:** Visualize validation against policy-relevant benchmark

---

## Figure 5: Regional Patterns - Mobility by Region Type

**Type:** Grouped bar chart with error bars  
**Dimensions:** Half page width (90mm), portrait  
**File Format:** PDF (vector)

**Content Requirements:**
- **X-axis:** Region type (Post-Industrial North, Coastal Towns, National Average)
- **Y-axis:** Mean Mobility Score (0.0 to 0.6)
- **Bars:** Distinct colors for each region type (blue, green, gray)
  - Post-Industrial: Blue bar, mean=0.417, error bar=±1 SE
  - Coastal: Green bar, mean=0.462, error bar=±1 SE
  - National: Gray bar, mean=0.506, error bar=±1 SE
- **Reference line:** Horizontal dashed line at national mean (0.506)
- **Annotations:** Sample sizes (n=10, n=7, n=317) below each bar
- **Statistical notation:** Significance brackets with p-values or Cohen's d values

**Data Sources:**
- Known deprived LADs: 17 LADs (10 post-industrial, 7 coastal)
- Mobility scores: Computed from IMD 2019 proxy
- Effect size: Cohen's d = -0.74 for deprived vs non-deprived

**Software:** Matplotlib or ggplot2 (R)

**Purpose:** Demonstrate geographic heterogeneity and regional disparities

---

## Figure 6: Case Study - Blackpool Basin

**Type:** Detailed geographic map with annotations  
**Dimensions:** Full page width (190mm), square aspect ratio  
**File Format:** PDF (vector) or PNG (300 DPI)

**Content Requirements:**
- **Base map:** Blackpool and surrounding LSOAs (≈30-40 LSOAs), high detail
- **Mobility heatmap:** Continuous color gradient (red=low to blue=high)
- **Basin boundary:** Thick black line (2pt) showing separatrix enclosing Blackpool basin
- **Gateway LSOAs:** Green stars (15pt) marking peripheral LSOAs with higher mobility
- **Barriers:** Yellow triangles (12pt) at saddle points with annotations
  - Example: "Transport barrier to Preston" with arrow
- **Minimum location:** Red circle (20pt) at basin center (lowest mobility point)
- **LAD boundaries:** Thin gray lines for Blackpool, Fylde, Wyre, Preston
- **Legend:** All symbol types, colorbar for mobility
- **Inset map:** Small map showing Blackpool location within England (top-right corner)

**Data Sources:**
- Blackpool basin: Extracted from TTK descending manifold for top-ranked trap
- LSOA details: ONS boundaries
- Barrier annotations: Identified from saddle point analysis + geographic context

**Software:** QGIS or GeoPandas + Contextily for basemap

**Purpose:** Concrete policy example showing gateway LSOAs and barrier locations

---

## Figure 7 (Optional): Methodological Flowchart

**Type:** Flowchart diagram  
**Dimensions:** Half page width (90mm), portrait  
**File Format:** PDF (vector)  
**Location:** May be moved to Supplementary Materials if space constrained

**Content Requirements:**
- **Box 1 - Data Inputs:** LSOA boundaries + IMD 2019 → arrows down
- **Box 2 - Mobility Proxy:** Weighted combination (α=0.2, β=0.5, γ=0.3) → arrow down
- **Box 3 - Surface Construction:** Interpolation to 75×75 grid → arrow down
- **Decision Diamond:** Apply TTK simplification? (Yes: 5% threshold)
- **Box 4 - TTK Analysis:** Morse-Smale complex computation → arrow down
- **Box 5 - Basin Extraction:** Properties (size, mobility, barriers) → arrow down
- **Box 6 - Trap Scoring:** Multi-factor severity score → arrow down
- **Box 7 - Validation:** SMC comparison + Known deprived areas
- **Output:** Reports, maps, policy recommendations

**Style:** Clean, professional (use mermaid.js syntax or draw.io)

**Purpose:** Enhance reproducibility and clarity of methodological pipeline

---

## Tables (to be integrated as figures)

### Table 1: Top 10 Poverty Traps by Severity Score

**Format:** Standard table, can be typeset in LaTeX or created as image  
**Location:** Results section, after Figure 3

**Columns:**
1. Rank (1-10)
2. LAD Name (text)
3. Severity Score (2 decimal places, 0.00-1.00)
4. Mean Mobility (3 decimal places, 0.000-1.000)
5. Basin Area (km²) (integer)
6. Barrier Height (2 decimal places)
7. Population Estimate (thousands)

**Formatting:**
- Header row: Bold, light gray background
- Rank 1-3: Highlight with light red background
- Right-align numeric columns
- Include footnote: "Population estimated from LSOA counts within basin"

---

### Table 2: Regional Patterns in Known Deprived Areas

**Format:** Standard table  
**Location:** Results section, near Figure 5

**Columns:**
1. Region Type (Post-Industrial North, Coastal Towns, National Average)
2. N LADs (integer)
3. Mean Mobility (3 decimal places, with ±SE)
4. % Bottom Quartile (1 decimal place)
5. % of National Mean (1 decimal place)
6. Cohen's d (2 decimal places)

**Formatting:**
- Header row: Bold
- Regional rows: Alternate light gray/white background
- National Average row: Bold for comparison
- Significant Cohen's d values: Bold if |d| > 0.5

---

### Table 3: Validation Metrics Summary

**Format:** Standard table  
**Location:** Results or Discussion section

**Columns:**
1. Validation Source (SMC Cold Spots, Known Deprived Areas)
2. Metric (description)
3. Result (numeric with units)
4. Statistical Test (χ², Cohen's d, etc.)
5. p-value (3 decimal places or scientific notation)
6. Interpretation (text: "Strong", "Significant", etc.)

**Rows:**
1. SMC - Bottom Quartile | 61.5% | χ² test | p=0.008 | Highly significant
2. SMC - Mean Percentile | 25.9th | Descriptive | N/A | Bottom third
3. Deprived - Mobility Gap | -18.1% | Cohen's d=-0.74 | p<0.001 | Medium-large effect
4. Post-Industrial - Bottom Q | 60% | Descriptive | N/A | 2.4× random
5. Coastal - Bottom Q | 43% | Descriptive | N/A | 1.7× random

---

## Production Notes

### Figure Creation Workflow
1. **Data extraction:** Export from TTK VTK files + validation scripts
2. **Draft figures:** Create in Matplotlib/GeoPandas with draft styling
3. **Review iteration:** Adjust colors, labels, sizes for readability
4. **High-res export:** PDF vector format (preferred) or 300+ DPI PNG
5. **Journal submission:** Follow JEG figure guidelines exactly

### Color Accessibility
- **Use colorblind-friendly palettes:** Avoid red-green combinations alone
- **Test with simulators:** Coblis or similar tools
- **Provide alternative indicators:** Use shapes + colors (not color alone)

### Software Stack
- **Python:** Matplotlib, GeoPandas, Seaborn
- **GIS:** QGIS for final map polishing
- **TTK:** Paraview for 3D surface exports (Figure 2 option)
- **LaTeX:** Table typesetting for journal submission

### File Naming Convention
- `fig1_study_area.pdf`
- `fig2_mobility_surface.pdf`
- `fig3_basin_structure.pdf`
- `fig4_smc_validation.pdf`
- `fig5_regional_patterns.pdf`
- `fig6_blackpool_case.pdf`
- `fig7_methodology_flowchart.pdf` (optional)
- `table1_top_traps.tex`
- `table2_regional_patterns.tex`
- `table3_validation_summary.tex`

---

**Specification Status:** COMPLETE  
**Next Steps:** Begin figure production in parallel with manuscript writing (Step 2 onwards)  
**Estimated Production Time:** 2-3 days for all figures (after data is finalized)
