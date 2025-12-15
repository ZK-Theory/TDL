# Basin Statistics Display - Step 2 Implementation

## Overview
Step 2 adds comprehensive statistics display for selected poverty trap basins with single-basin detailed view and multi-basin comparison capabilities.

## Features Implemented

### Single Basin View
When one basin is selected, displays 4 key metric cards:

1. **Population Metrics**
   - Total estimated population
   - Number of LSOAs (delta indicator)
   
2. **Mean Mobility Score**
   - Displayed as percentage (0-100%)
   - Delta shows "Above/Below median"
   - Color coding: green for above 50%, red for below

3. **Trap Score**
   - Composite score (0-1 scale)
   - Severity label (Critical/Severe/Moderate/Low/Minimal)
   - Color indicator bar based on severity:
     - Dark Red (#8B0000): Critical (0.8-1.0)
     - Orange Red (#FF4500): Severe (0.6-0.8)
     - Orange (#FFA500): Moderate (0.4-0.6)
     - Gold (#FFD700): Low (0.2-0.4)
     - Light Green (#90EE90): Minimal (0.0-0.2)

4. **Basin Area**
   - Area in km²
   - Population density (per km²) as delta

### Detailed Information Expander
- Basin ID and name
- Region
- Trap analysis breakdown
- Geographic coverage details
- Population density calculation

### Multi-Basin Comparison View
When 2+ basins are selected:

1. **Comparison Table**
   - Sortable by any column
   - Background gradient styling:
     - Trap Score: Yellow→Red (YlOrRd colormap)
     - Mean Mobility: Red→Yellow→Green (RdYlGn colormap)
   - Columns: Basin, Trap Score, Severity, Population, LSOAs, Mean Mobility, Area, Density
   - Sorted by trap score (worst first)

2. **Comparison Summary**
   - Total population across selected basins
   - Worst trap identification with score
   - Average mobility across selection

## Functions Added

### `render_basin_statistics(selected_basins)`
Main orchestrator that routes to single or multi-basin views.

### `render_single_basin_metrics(basin)`
Creates detailed 4-column metric cards with:
- `st.metric()` for each statistic
- Delta indicators for context
- Color-coded trap score bar
- Expandable detailed information

### `render_basin_comparison(selected_basins)`
Creates comparison interface with:
- Styled DataFrame with gradient backgrounds
- Summary statistics in 3 columns
- Formatted numbers (thousands separator, decimals)

### `get_severity_label(trap_score)`
Maps trap score to human-readable severity:
- Critical: 0.8+
- Severe: 0.6-0.8
- Moderate: 0.4-0.6
- Low: 0.2-0.4
- Minimal: 0.0-0.2

### `get_trap_score_color(score)` (existing)
Returns hex color code based on severity thresholds.

## Testing
Test suite created at `poverty_tda/viz/test_dashboard_stats.py`:
- ✓ Mock data generation validation
- ✓ Severity label classification
- ✓ Color mapping consistency
- ✓ Multi-region data generation

## Usage
1. Select region from sidebar
2. Select one or more basins
3. View statistics automatically displayed:
   - Single basin: Detailed metric cards
   - Multiple basins: Comparison table

## Dashboard Access
- URL: http://localhost:8502
- Default region: North West
- Mock data: 10 basins per region
