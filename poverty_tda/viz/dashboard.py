"""
Streamlit Dashboard for Poverty TDA Basin Analysis.

Interactive dashboard for exploring poverty trap basins, comparing statistics,
demographics, and escape pathways across regions in England and Wales.
"""

import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Fix PyTorch DLL loading on Windows (Python 3.8+)
# This resolves "c10.dll initialization failed" errors in Streamlit subprocess
if sys.platform == "win32" and sys.version_info >= (3, 8):
    try:
        torch_lib = project_root / ".venv" / "Lib" / "site-packages" / "torch" / "lib"
        if torch_lib.exists():
            os.add_dll_directory(str(torch_lib))
    except Exception:
        pass  # Silently continue if torch not installed or path doesn't exist

# CRITICAL: Import torch BEFORE poverty_tda modules
# gtda/gudhi C extensions interfere with PyTorch DLL loading if loaded first
try:
    import torch  # noqa: F401 - imported early to fix DLL loading order
except ImportError:
    pass  # PyTorch optional for basic dashboard features

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Now safe to import project modules

logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Poverty TDA Basin Dashboard",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# Available regions in England and Wales
REGIONS = [
    "North West",
    "North East",
    "Yorkshire and The Humber",
    "East Midlands",
    "West Midlands",
    "East of England",
    "London",
    "South East",
    "South West",
    "Wales",
]

# Default region selection
DEFAULT_REGION = "North West"

# Color thresholds for trap scores
TRAP_SCORE_THRESHOLDS = {
    "critical": (0.8, 1.0, "#8B0000"),  # Dark red
    "severe": (0.6, 0.8, "#FF4500"),  # Orange red
    "moderate": (0.4, 0.6, "#FFA500"),  # Orange
    "low": (0.2, 0.4, "#FFD700"),  # Gold
    "minimal": (0.0, 0.2, "#90EE90"),  # Light green
}


def get_trap_score_color(score: float) -> str:
    """Return color based on trap score severity."""
    for severity, (min_val, max_val, color) in TRAP_SCORE_THRESHOLDS.items():
        if min_val <= score < max_val:
            return color
    return TRAP_SCORE_THRESHOLDS["minimal"][2]


# =============================================================================
# MOCK DATA GENERATION (Temporary - will be replaced with real data)
# =============================================================================


def generate_mock_basin_data(region: str, n_basins: int = 10) -> list[dict]:
    """
    Generate mock basin data for testing dashboard functionality.

    Args:
        region: Region name
        n_basins: Number of basins to generate

    Returns:
        List of basin data dictionaries
    """
    np.random.seed(hash(region) % 2**32)  # Reproducible per region

    basins = []
    for i in range(n_basins):
        basin_id = i + 1

        # Generate realistic trap scores (higher IDs = worse traps)
        base_score = 0.3 + (i / n_basins) * 0.5 + np.random.uniform(-0.1, 0.1)
        trap_score = np.clip(base_score, 0.0, 1.0)

        # Population and area
        population = np.random.randint(5000, 50000)
        area_km2 = np.random.uniform(10, 200)

        # Mobility score (inversely related to trap score)
        mean_mobility = 0.7 - (trap_score * 0.4) + np.random.uniform(-0.05, 0.05)
        mean_mobility = np.clip(mean_mobility, 0.2, 0.9)

        # IMD decile distribution (worse traps = more deprived)
        if trap_score > 0.6:
            # Severe trap - concentrated in low deciles
            decile_probs = [0.25, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05, 0.03, 0.01, 0.01]
        elif trap_score > 0.4:
            # Moderate trap - mixed distribution
            decile_probs = [0.15, 0.13, 0.12, 0.11, 0.10, 0.10, 0.09, 0.08, 0.07, 0.05]
        else:
            # Low trap - more uniform/higher deciles
            decile_probs = [0.05, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14, 0.11]

        decile_counts = (np.array(decile_probs) * population / 5).astype(int)

        # IMD domain scores (0-100 scale, lower = more deprived)
        # Domains correlate with overall trap score
        base_deprivation = (1 - trap_score) * 100  # Convert to 0-100 scale
        income_score = np.clip(base_deprivation + np.random.uniform(-10, 10), 0, 100)
        employment_score = np.clip(base_deprivation + np.random.uniform(-10, 10), 0, 100)
        education_score = np.clip(base_deprivation + np.random.uniform(-15, 15), 0, 100)
        health_score = np.clip(base_deprivation + np.random.uniform(-10, 10), 0, 100)

        basins.append(
            {
                "basin_id": basin_id,
                "basin_name": f"Basin {basin_id} ({region[:2].upper()})",
                "region": region,
                "population": population,
                "area_km2": area_km2,
                "mean_mobility": mean_mobility,
                "trap_score": trap_score,
                "n_lsoas": np.random.randint(10, 100),
                "decile_counts": decile_counts.tolist(),
                "domain_scores": {
                    "income": float(income_score),
                    "employment": float(employment_score),
                    "education": float(education_score),
                    "health": float(health_score),
                },
            }
        )

    return basins


# =============================================================================
# STREAMLIT SIDEBAR: REGION AND BASIN SELECTION
# =============================================================================


def render_sidebar():
    """Render sidebar with region and basin selection controls."""
    st.sidebar.title("🗺️ Basin Selection")

    # Region selector
    st.sidebar.subheader("Region")
    selected_region = st.sidebar.selectbox(
        "Select region:",
        options=REGIONS,
        index=REGIONS.index(DEFAULT_REGION),
        key="region_selector",
    )

    # Load basins for selected region
    if "basins_data" not in st.session_state or st.session_state.get("current_region") != selected_region:
        st.session_state.basins_data = generate_mock_basin_data(selected_region)
        st.session_state.current_region = selected_region

    basins = st.session_state.basins_data

    # Basin multi-select
    st.sidebar.subheader("Basins")
    basin_options = [f"{b['basin_name']} (Score: {b['trap_score']:.2f})" for b in basins]

    selected_basin_labels = st.sidebar.multiselect(
        "Select basins to compare:",
        options=basin_options,
        default=[basin_options[0]] if basin_options else [],
        key="basin_multiselect",
    )

    # Extract basin IDs from selected labels
    selected_basin_ids = []
    for label in selected_basin_labels:
        # Extract basin_id from label (e.g., "Basin 1 (NW) (Score: 0.45)" -> 1)
        basin_id = int(label.split("Basin ")[1].split()[0])
        selected_basin_ids.append(basin_id)

    # Filter selected basins
    selected_basins = [b for b in basins if b["basin_id"] in selected_basin_ids]

    # Display selection summary
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Selected:** {len(selected_basins)} basin(s)")

    if len(selected_basins) == 0:
        st.sidebar.warning("⚠️ Select at least one basin to view statistics")

    return selected_region, selected_basins


# =============================================================================
# STATISTICS DISPLAY
# =============================================================================


def render_basin_statistics(selected_basins: list[dict]):
    """
    Render statistics cards and comparison table for selected basins.

    Args:
        selected_basins: List of basin data dictionaries
    """
    st.markdown("### Basin Statistics")

    if len(selected_basins) == 0:
        return

    # Single basin view - show detailed metrics
    if len(selected_basins) == 1:
        basin = selected_basins[0]
        render_single_basin_metrics(basin)

    # Multiple basins - show comparison
    else:
        render_basin_comparison(selected_basins)


def render_single_basin_metrics(basin: dict):
    """Render detailed metric cards for a single basin."""

    # Create 4 columns for key metrics
    col1, col2, col3, col4 = st.columns(4)

    # Population metrics
    with col1:
        st.metric(
            label="Population",
            value=f"{basin['population']:,}",
            delta=f"{basin['n_lsoas']} LSOAs",
            help="Estimated population and number of LSOAs in basin",
        )

    # Mobility score
    with col2:
        mobility_pct = basin["mean_mobility"] * 100
        st.metric(
            label="Mean Mobility",
            value=f"{mobility_pct:.1f}%",
            delta=f"{'Above' if mobility_pct > 50 else 'Below'} median",
            delta_color="normal" if mobility_pct > 50 else "inverse",
            help="Average mobility proxy score within basin",
        )

    # Trap score with color indicator
    with col3:
        trap_score = basin["trap_score"]
        trap_color = get_trap_score_color(trap_score)
        severity = get_severity_label(trap_score)

        st.metric(
            label="Trap Score",
            value=f"{trap_score:.2f}",
            delta=severity,
            delta_color="inverse" if trap_score > 0.5 else "normal",
            help="Composite trap severity: 0.4×mobility + 0.3×size + 0.3×barrier",
        )

        # Color indicator
        st.markdown(
            f'<div style="background-color: {trap_color}; height: 10px; '
            f'border-radius: 5px; margin-top: -10px;"></div>',
            unsafe_allow_html=True,
        )

    # Basin area
    with col4:
        st.metric(
            label="Basin Area",
            value=f"{basin['area_km2']:.1f} km²",
            delta=f"{basin['population'] / basin['area_km2']:.0f} per km²",
            help="Geographic area and population density",
        )

    # Additional details in expander
    with st.expander("📋 Detailed Basin Information"):
        st.markdown(f"""
        **Basin ID:** {basin["basin_id"]}
        **Basin Name:** {basin["basin_name"]}
        **Region:** {basin["region"]}

        **Trap Analysis:**
        - Severity Rank: **{severity}**
        - Trap Score: {trap_score:.3f}
        - Mean Mobility: {basin["mean_mobility"]:.3f}

        **Geographic Coverage:**
        - Total Area: {basin["area_km2"]:.2f} km²
        - Number of LSOAs: {basin["n_lsoas"]}
        - Population Density: {basin["population"] / basin["area_km2"]:.1f} people/km²
        """)


def render_basin_comparison(selected_basins: list[dict]):
    """Render comparison table and metrics for multiple basins."""

    st.markdown(f"**Comparing {len(selected_basins)} basins**")

    # Create comparison DataFrame
    comparison_data = []
    for basin in selected_basins:
        comparison_data.append(
            {
                "Basin": basin["basin_name"],
                "Trap Score": basin["trap_score"],
                "Severity": get_severity_label(basin["trap_score"]),
                "Population": basin["population"],
                "LSOAs": basin["n_lsoas"],
                "Mean Mobility": basin["mean_mobility"],
                "Area (km²)": basin["area_km2"],
                "Density": basin["population"] / basin["area_km2"],
            }
        )

    df = pd.DataFrame(comparison_data)

    # Sort by trap score (worst first)
    df = df.sort_values("Trap Score", ascending=False)

    # Display styled table
    st.dataframe(
        df.style.background_gradient(subset=["Trap Score"], cmap="YlOrRd", vmin=0.0, vmax=1.0)
        .background_gradient(subset=["Mean Mobility"], cmap="RdYlGn", vmin=0.0, vmax=1.0)
        .format(
            {
                "Trap Score": "{:.3f}",
                "Population": "{:,.0f}",
                "Mean Mobility": "{:.3f}",
                "Area (km²)": "{:.1f}",
                "Density": "{:.1f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # Summary statistics
    st.markdown("#### Comparison Summary")
    col1, col2, col3 = st.columns(3)

    with col1:
        total_pop = sum(b["population"] for b in selected_basins)
        st.metric("Total Population", f"{total_pop:,}")

    with col2:
        max_trap = max(b["trap_score"] for b in selected_basins)
        worst_basin = next(b for b in selected_basins if b["trap_score"] == max_trap)
        st.metric(
            "Worst Trap",
            f"{worst_basin['basin_name']}",
            delta=f"Score: {max_trap:.2f}",
            delta_color="inverse",
        )

    with col3:
        avg_mobility = np.mean([b["mean_mobility"] for b in selected_basins])
        st.metric(
            "Average Mobility",
            f"{avg_mobility * 100:.1f}%",
            delta=f"Across {len(selected_basins)} basins",
        )


def get_severity_label(trap_score: float) -> str:
    """Get human-readable severity label for trap score."""
    if trap_score >= 0.8:
        return "Critical"
    elif trap_score >= 0.6:
        return "Severe"
    elif trap_score >= 0.4:
        return "Moderate"
    elif trap_score >= 0.2:
        return "Low"
    else:
        return "Minimal"


# =============================================================================
# DEMOGRAPHIC BREAKDOWN
# =============================================================================


def render_demographic_breakdown(selected_basins: list[dict]):
    """
    Render demographic breakdown charts for selected basins.

    Args:
        selected_basins: List of basin data dictionaries
    """
    st.markdown("### Demographic Breakdown")

    if len(selected_basins) == 0:
        return

    # Single basin view - detailed breakdown
    if len(selected_basins) == 1:
        render_single_basin_demographics(selected_basins[0])

    # Multiple basins - side-by-side comparison
    else:
        render_demographic_comparison(selected_basins)


def render_single_basin_demographics(basin: dict):
    """Render detailed demographic charts for a single basin."""

    # IMD Decile Distribution
    st.markdown("#### IMD Decile Distribution")
    st.caption(
        "Distribution of LSOAs across Index of Multiple Deprivation deciles (1=most deprived, 10=least deprived)"
    )

    decile_counts = basin["decile_counts"]
    decile_labels = [f"Decile {i + 1}" for i in range(10)]

    fig_decile = go.Figure(
        data=[
            go.Bar(
                x=decile_labels,
                y=decile_counts,
                marker=dict(
                    color=decile_counts,
                    colorscale="RdYlGn",  # Red (deprived) to Green (affluent)
                    showscale=True,
                    colorbar=dict(title="Population"),
                ),
                text=decile_counts,
                textposition="auto",
            )
        ]
    )

    fig_decile.update_layout(
        xaxis_title="IMD Decile",
        yaxis_title="Population",
        height=400,
        showlegend=False,
    )

    st.plotly_chart(fig_decile, use_container_width=True)

    # Quintile Distribution (Pie Chart)
    st.markdown("#### Deprivation Quintile Distribution")
    st.caption("Proportion of LSOAs in each deprivation quintile")

    # Aggregate deciles into quintiles (2 deciles per quintile)
    quintile_counts = [
        sum(decile_counts[0:2]),  # Q1: Most deprived (deciles 1-2)
        sum(decile_counts[2:4]),  # Q2: Deprived (deciles 3-4)
        sum(decile_counts[4:6]),  # Q3: Average (deciles 5-6)
        sum(decile_counts[6:8]),  # Q4: Affluent (deciles 7-8)
        sum(decile_counts[8:10]),  # Q5: Most affluent (deciles 9-10)
    ]

    quintile_labels = [
        "Q1: Most Deprived",
        "Q2: Deprived",
        "Q3: Average",
        "Q4: Affluent",
        "Q5: Most Affluent",
    ]

    fig_quintile = go.Figure(
        data=[
            go.Pie(
                labels=quintile_labels,
                values=quintile_counts,
                marker=dict(colors=["#8B0000", "#FF4500", "#FFA500", "#9ACD32", "#32CD32"]),
                textinfo="label+percent",
                hovertemplate="%{label}<br>Population: %{value:,}<extra></extra>",
            )
        ]
    )

    fig_quintile.update_layout(height=400)

    st.plotly_chart(fig_quintile, use_container_width=True)

    # Domain Breakdown
    st.markdown("#### IMD Domain Scores")
    st.caption("Average scores across key deprivation domains (higher = better)")

    domain_scores = basin["domain_scores"]
    domains = ["Income", "Employment", "Education", "Health"]
    scores = [
        domain_scores["income"],
        domain_scores["employment"],
        domain_scores["education"],
        domain_scores["health"],
    ]

    fig_domains = go.Figure(
        data=[
            go.Bar(
                x=domains,
                y=scores,
                marker=dict(
                    color=scores,
                    colorscale="RdYlGn",
                    showscale=False,
                    cmin=0,
                    cmax=100,
                ),
                text=[f"{s:.1f}" for s in scores],
                textposition="auto",
            )
        ]
    )

    fig_domains.update_layout(
        xaxis_title="Domain",
        yaxis_title="Score (0-100)",
        yaxis_range=[0, 100],
        height=400,
        showlegend=False,
    )

    st.plotly_chart(fig_domains, use_container_width=True)


def render_demographic_comparison(selected_basins: list[dict]):
    """Render side-by-side demographic comparison for multiple basins."""

    st.markdown(f"**Comparing demographics across {len(selected_basins)} basins**")

    # IMD Decile Comparison
    st.markdown("#### IMD Decile Distribution Comparison")

    fig_decile_comp = go.Figure()

    for basin in selected_basins:
        decile_labels = [f"D{i + 1}" for i in range(10)]
        fig_decile_comp.add_trace(
            go.Bar(
                name=basin["basin_name"],
                x=decile_labels,
                y=basin["decile_counts"],
                text=basin["decile_counts"],
                textposition="auto",
            )
        )

    fig_decile_comp.update_layout(
        xaxis_title="IMD Decile",
        yaxis_title="Population",
        barmode="group",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig_decile_comp, use_container_width=True)

    # Quintile Comparison (Grouped Bar Chart)
    st.markdown("#### Deprivation Quintile Comparison")

    fig_quintile_comp = go.Figure()

    quintile_labels = [
        "Q1: Most Deprived",
        "Q2: Deprived",
        "Q3: Average",
        "Q4: Affluent",
        "Q5: Most Affluent",
    ]

    for basin in selected_basins:
        decile_counts = basin["decile_counts"]
        quintile_counts = [
            sum(decile_counts[0:2]),
            sum(decile_counts[2:4]),
            sum(decile_counts[4:6]),
            sum(decile_counts[6:8]),
            sum(decile_counts[8:10]),
        ]

        fig_quintile_comp.add_trace(
            go.Bar(
                name=basin["basin_name"],
                x=quintile_labels,
                y=quintile_counts,
                text=quintile_counts,
                textposition="auto",
            )
        )

    fig_quintile_comp.update_layout(
        xaxis_title="Deprivation Quintile",
        yaxis_title="Population",
        barmode="group",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig_quintile_comp, use_container_width=True)

    # Domain Score Comparison
    st.markdown("#### IMD Domain Score Comparison")

    fig_domain_comp = go.Figure()

    domains = ["Income", "Employment", "Education", "Health"]

    for basin in selected_basins:
        scores = [
            basin["domain_scores"]["income"],
            basin["domain_scores"]["employment"],
            basin["domain_scores"]["education"],
            basin["domain_scores"]["health"],
        ]

        fig_domain_comp.add_trace(
            go.Bar(
                name=basin["basin_name"],
                x=domains,
                y=scores,
                text=[f"{s:.1f}" for s in scores],
                textposition="auto",
            )
        )

    fig_domain_comp.update_layout(
        xaxis_title="Domain",
        yaxis_title="Score (0-100)",
        yaxis_range=[0, 100],
        barmode="group",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig_domain_comp, use_container_width=True)

    # Summary Table
    st.markdown("#### Demographic Summary")

    summary_data = []
    for basin in selected_basins:
        decile_counts = basin["decile_counts"]
        # Calculate mean decile (weighted average)
        mean_decile = sum((i + 1) * count for i, count in enumerate(decile_counts)) / sum(decile_counts)

        # Most deprived proportion (deciles 1-3)
        most_deprived = sum(decile_counts[0:3]) / sum(decile_counts) * 100

        summary_data.append(
            {
                "Basin": basin["basin_name"],
                "Mean Decile": mean_decile,
                "Most Deprived (%)": most_deprived,
                "Income Score": basin["domain_scores"]["income"],
                "Employment Score": basin["domain_scores"]["employment"],
                "Education Score": basin["domain_scores"]["education"],
                "Health Score": basin["domain_scores"]["health"],
            }
        )

    df_summary = pd.DataFrame(summary_data)

    st.dataframe(
        df_summary.style.background_gradient(subset=["Mean Decile"], cmap="RdYlGn", vmin=1, vmax=10)
        .background_gradient(subset=["Most Deprived (%)"], cmap="YlOrRd", vmin=0, vmax=100)
        .format(
            {
                "Mean Decile": "{:.2f}",
                "Most Deprived (%)": "{:.1f}%",
                "Income Score": "{:.1f}",
                "Employment Score": "{:.1f}",
                "Education Score": "{:.1f}",
                "Health Score": "{:.1f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


# =============================================================================
# MAP & TERRAIN INTEGRATION
# =============================================================================


def render_geographic_context(selected_basins: list[dict], region: str):
    """
    Render geographic context including map and 3D terrain preview.

    Args:
        selected_basins: List of basin data dictionaries
        region: Selected region name
    """
    st.markdown("### Geographic Context")

    if len(selected_basins) == 0:
        return

    # Create two columns for map and terrain
    col_map, col_terrain = st.columns([1.5, 1])

    with col_map:
        render_basin_map(selected_basins, region)

    with col_terrain:
        render_terrain_preview(selected_basins, region)


def render_basin_map(selected_basins: list[dict], region: str):
    """
    Render Folium interactive map with selected basins highlighted.

    Args:
        selected_basins: List of basin data dictionaries
        region: Selected region name
    """
    st.markdown("#### Interactive Map")
    st.caption("Basin locations and boundaries")

    # Import folium for map creation
    import folium
    from streamlit_folium import st_folium

    # Regional centers (approximate lat/lon for major regions)
    region_centers = {
        "North West": [53.5, -2.5],
        "North East": [55.0, -1.6],
        "Yorkshire and The Humber": [53.8, -1.3],
        "East Midlands": [52.9, -1.0],
        "West Midlands": [52.5, -2.0],
        "East of England": [52.2, 0.5],
        "London": [51.5, -0.1],
        "South East": [51.3, -0.8],
        "South West": [51.0, -3.0],
        "Wales": [52.3, -3.7],
    }

    center = region_centers.get(region, [52.8, -2.0])

    # Create base map
    m = folium.Map(
        location=center,
        zoom_start=8,
        tiles="OpenStreetMap",
        width="100%",
        height="500px",
    )

    # Color scheme for basins
    colors = [
        "#FF4500",
        "#8B0000",
        "#FFA500",
        "#FFD700",
        "#32CD32",
        "#1E90FF",
        "#9370DB",
        "#FF1493",
        "#00CED1",
        "#7FFF00",
    ]

    # Generate mock basin locations around the center
    for i, basin in enumerate(selected_basins):
        # Create circular mock boundaries around center with offset
        offset_lat = (i % 3 - 1) * 0.15
        offset_lon = (i // 3 - 1) * 0.15

        basin_center = [center[0] + offset_lat, center[1] + offset_lon]

        # Determine color based on trap score
        color = colors[i % len(colors)]
        if basin["trap_score"] >= 0.8:
            color = "#8B0000"  # Critical - dark red
        elif basin["trap_score"] >= 0.6:
            color = "#FF4500"  # Severe - orange red
        elif basin["trap_score"] >= 0.4:
            color = "#FFA500"  # Moderate - orange
        else:
            color = "#90EE90"  # Low - light green

        # Add circle marker for basin center
        folium.CircleMarker(
            location=basin_center,
            radius=15,
            popup=folium.Popup(
                f"""
                <b>{basin["basin_name"]}</b><br>
                Trap Score: {basin["trap_score"]:.3f}<br>
                Population: {basin["population"]:,}<br>
                Mean Mobility: {basin["mean_mobility"]:.3f}<br>
                Area: {basin["area_km2"]:.1f} km²
                """,
                max_width=300,
            ),
            tooltip=f"{basin['basin_name']} (Score: {basin['trap_score']:.2f})",
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.6,
            weight=3,
        ).add_to(m)

        # Add circular boundary
        folium.Circle(
            location=basin_center,
            radius=5000,  # 5km radius
            color=color,
            fill=True,
            fillOpacity=0.15,
            weight=2,
            dashArray="5, 5",
        ).add_to(m)

        # Add label
        folium.Marker(
            location=[basin_center[0] + 0.05, basin_center[1]],
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    font-size: 11px;
                    font-weight: bold;
                    color: {color};
                    text-shadow: 1px 1px 2px white;
                ">
                    {basin["basin_name"]}
                </div>
                """
            ),
        ).add_to(m)

    # Render map in Streamlit
    st_folium(m, width=700, height=500, returned_objects=[])

    # Legend
    with st.expander("🗺️ Map Legend"):
        st.markdown("""
        **Basin Colors:**
        - 🔴 **Dark Red**: Critical trap (score ≥ 0.8)
        - 🟠 **Orange Red**: Severe trap (score 0.6-0.8)
        - 🟡 **Orange**: Moderate trap (score 0.4-0.6)
        - 🟢 **Light Green**: Low trap (score < 0.4)

        **Map Features:**
        - **Solid circles**: Basin centers
        - **Dashed circles**: Approximate basin boundaries (5km radius)
        - **Click markers** for detailed basin information
        """)


def render_terrain_preview(selected_basins: list[dict], region: str):
    """
    Render 3D terrain preview using mock elevation data.

    Args:
        selected_basins: List of basin data dictionaries
        region: Selected region name
    """
    st.markdown("#### 3D Terrain Preview")

    # Dynamic caption based on number of basins
    if len(selected_basins) == 1:
        st.caption(f"Mobility surface topology for {selected_basins[0]['basin_name']}")
    else:
        st.caption(f"Combined mobility landscape showing {len(selected_basins)} selected basins")

    # Create mock 3D terrain visualization using Plotly
    # Generate height map based on mobility scores

    grid_size = 30
    x = np.linspace(0, 10, grid_size)
    y = np.linspace(0, 10, grid_size)
    X, Y = np.meshgrid(x, y)

    # Generate base terrain with multiple peaks/valleys
    Z = np.zeros_like(X)

    # Store basin positions for annotations
    basin_positions = []

    # Add basin "valleys" (low mobility = low elevation)
    for i, basin in enumerate(selected_basins):
        # Position basins across the terrain
        cx = 2 + (i % 3) * 3
        cy = 2 + (i // 3) * 3

        basin_positions.append({"basin": basin, "x": cx, "y": cy, "index": i})

        # Depth based on trap severity (higher trap = deeper valley)
        depth = basin["trap_score"] * 3.0

        # Width based on basin area
        width = np.sqrt(basin["area_km2"]) / 10

        # Gaussian valley
        valley = -depth * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * width**2))
        Z += valley

    # Add some noise for realism
    np.random.seed(42)
    Z += np.random.randn(*Z.shape) * 0.1

    # Normalize to mobility scale (0-1)
    Z = (Z - Z.min()) / (Z.max() - Z.min())

    # Create 3D surface plot
    fig_terrain = go.Figure(
        data=[
            go.Surface(
                x=X,
                y=Y,
                z=Z,
                colorscale="RdYlGn",  # Red (low) to Green (high)
                showscale=True,
                colorbar=dict(
                    title="Mobility",
                    x=1.1,
                ),
                hovertemplate="<b>Mobility: %{z:.3f}</b><extra></extra>",
            )
        ]
    )

    # Add basin markers/annotations
    for pos in basin_positions:
        basin = pos["basin"]
        # Find the Z value at basin center
        x_idx = int((pos["x"] / 10) * (grid_size - 1))
        y_idx = int((pos["y"] / 10) * (grid_size - 1))
        z_val = Z[y_idx, x_idx]

        # Add scatter point for basin center
        fig_terrain.add_trace(
            go.Scatter3d(
                x=[pos["x"]],
                y=[pos["y"]],
                z=[z_val],
                mode="markers+text",
                marker=dict(
                    size=8,
                    color="red" if basin["trap_score"] >= 0.6 else "orange",
                    symbol="diamond",
                ),
                text=[basin["basin_name"]],
                textposition="top center",
                textfont=dict(size=10, color="black"),
                name=basin["basin_name"],
                hovertemplate=f"<b>{basin['basin_name']}</b><br>Trap Score: {basin['trap_score']:.3f}<br>Mobility: {z_val:.3f}<extra></extra>",
                showlegend=False,
            )
        )

    fig_terrain.update_layout(
        scene=dict(
            xaxis=dict(title="", showticklabels=False, showgrid=False),
            yaxis=dict(title="", showticklabels=False, showgrid=False),
            zaxis=dict(title="Mobility", range=[0, 1]),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2),
            ),
        ),
        height=500,
        margin=dict(l=0, r=0, t=30, b=0),
        title=dict(
            text=f"Mobility Landscape - {region}"
            if len(selected_basins) > 1
            else f"{selected_basins[0]['basin_name']} Topology",
            x=0.5,
            xanchor="center",
            font=dict(size=14),
        ),
    )

    st.plotly_chart(fig_terrain, use_container_width=True)

    # Explanation - different for single vs multiple basins
    with st.expander("📊 Terrain Interpretation"):
        if len(selected_basins) == 1:
            st.markdown(f"""
            **Single Basin Topology - {selected_basins[0]["basin_name"]}:**

            This 3D visualization shows the mobility landscape within and around the selected basin.

            - **Red/Orange valleys**: The poverty trap basin with low mobility scores
            - **Green peaks**: Surrounding high mobility regions
            - **Valley depth**: Trap severity (deeper = more difficult to escape)
            - **Valley width**: Basin geographic extent

            **How to Read This:**
            - The central valley represents the basin you selected
            - Low elevation (red) = low mobility = poverty trap
            - High elevation (green) = high mobility = opportunity
            - Steeper slopes = stronger barriers to escape
            """)
        else:
            st.markdown(f"""
            **Combined Mobility Landscape - {len(selected_basins)} Basins:**

            This 3D visualization shows a *unified topological view* of all selected basins on a single mobility surface.
            Each valley represents one of your selected basins.

            - **Diamond markers**: Basin centers labeled with basin names
            - **Valley depth**: Trap severity (deeper valleys = worse traps)
            - **Valley width**: Basin size (wider = more people affected)
            - **Color gradient**: Red (low mobility) → Yellow → Green (high mobility)

            **What You're Seeing:**
            - Each labeled valley corresponds to one selected basin
            - Multiple valleys show relative trap severity across basins
            - Deeper, redder valleys indicate more severe poverty traps
            - The surface represents a composite mobility landscape

            **Topological Concepts:**
            - **Minima** (valley bottoms): Core trap locations
            - **Saddles** (mountain passes between valleys): Barriers between basins
            - **Peaks** (green highlands): High-mobility opportunity regions
            - **Gradient flow**: Escape pathways follow upward slopes from valleys to peaks
            """)

    # Basin elevation summary
    st.markdown("##### Basin Elevations")

    elevation_data = []
    for basin in selected_basins:
        # Mock elevation based on mobility
        elevation = basin["mean_mobility"]
        elevation_data.append(
            {
                "Basin": basin["basin_name"],
                "Mobility": f"{elevation:.3f}",
                "Interpretation": "Valley" if elevation < 0.5 else "Plateau",
            }
        )

    df_elevation = pd.DataFrame(elevation_data)
    st.dataframe(df_elevation, use_container_width=True, hide_index=True)


# =============================================================================
# MAIN DASHBOARD
# =============================================================================


def main():
    """Main dashboard application."""

    # Title and description
    st.title("🗺️ Poverty TDA Basin Dashboard")
    st.markdown(
        """
        Explore poverty trap basins across England and Wales using topological data analysis.
        Compare basin statistics, demographics, and intervention opportunities.
        """
    )

    # Render sidebar and get selections
    selected_region, selected_basins = render_sidebar()

    # Check if any basins selected
    if len(selected_basins) == 0:
        st.info("👈 Select one or more basins from the sidebar to begin analysis")
        return

    # Display selected basin(s)
    st.header(f"📊 Basin Analysis: {selected_region}")

    # Statistics display (Step 2)
    render_basin_statistics(selected_basins)

    # Demographic breakdown (Step 3)
    render_demographic_breakdown(selected_basins)

    # Map & Terrain Integration (Step 4)
    render_geographic_context(selected_basins, selected_region)


if __name__ == "__main__":
    main()
