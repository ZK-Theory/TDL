"""
Streamlit Dashboard for Financial TDA Analysis.

Interactive dashboard for exploring topological data analysis of financial markets,
including persistence diagrams, regime detection, and anomaly alerts.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path so we can import financial_tda modules
project_root = Path(__file__).parent.parent.parent
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

# CRITICAL: Import torch BEFORE financial_tda modules
# gtda/gudhi C extensions interfere with PyTorch DLL loading if loaded first
try:
    import torch  # noqa: F401 - imported early to fix DLL loading order
except ImportError:
    pass  # PyTorch optional for basic dashboard features

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Import financial TDA modules
from financial_tda.analysis.windowed import extract_windowed_features
from financial_tda.data.fetchers.yahoo import fetch_ticker
from financial_tda.models.persistence_autoencoder import PersistenceAutoencoder
from financial_tda.models.regime_classifier import (
    RegimeClassifier,
    create_regime_labels,
    prepare_features,
)
from financial_tda.topology.embedding import takens_embedding
from financial_tda.topology.features import compute_persistence_image
from financial_tda.topology.filtration import compute_persistence_vr

logger = logging.getLogger(__name__)

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="Financial TDA Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
    <style>
    .main > div {
        padding-top: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    h1, h2, h3 {
        margin-top: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# Session State Initialization
# =============================================================================


def initialize_session_state():
    """Initialize session state variables for caching computed results."""
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
    if "price_data" not in st.session_state:
        st.session_state.price_data = None
    if "returns_data" not in st.session_state:
        st.session_state.returns_data = None
    if "windowed_features" not in st.session_state:
        st.session_state.windowed_features = None
    if "persistence_diagrams" not in st.session_state:
        st.session_state.persistence_diagrams = None
    if "window_dates" not in st.session_state:
        st.session_state.window_dates = None
    if "regime_predictions" not in st.session_state:
        st.session_state.regime_predictions = None
    if "anomaly_scores" not in st.session_state:
        st.session_state.anomaly_scores = None
    if "regime_classifier" not in st.session_state:
        st.session_state.regime_classifier = None
    if "regime_confidence" not in st.session_state:
        st.session_state.regime_confidence = None
    if "vix_data" not in st.session_state:
        st.session_state.vix_data = None
    if "autoencoder_model" not in st.session_state:
        st.session_state.autoencoder_model = None
    if "anomaly_threshold" not in st.session_state:
        st.session_state.anomaly_threshold = None
    if "persistence_images" not in st.session_state:
        st.session_state.persistence_images = None


initialize_session_state()

# =============================================================================
# Sidebar: Data Source Selection
# =============================================================================

st.sidebar.header("📊 Data Configuration")

data_source = st.sidebar.radio(
    "Data Source",
    options=["Yahoo Finance", "Upload CSV", "Sample Data"],
    help="Choose data source for TDA analysis",
)

# Data source specific inputs
if data_source == "Yahoo Finance":
    st.sidebar.subheader("Yahoo Finance Settings")

    ticker = st.sidebar.text_input(
        "Ticker Symbol",
        value="^GSPC",
        help="S&P 500: ^GSPC, Dow Jones: ^DJI, NASDAQ: ^IXIC",
    )

    # Date range picker
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime(2004, 1, 1),
            min_value=datetime(2000, 1, 1),
            max_value=datetime.today(),
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.today(),
            min_value=datetime(2000, 1, 1),
            max_value=datetime.today(),
        )

    load_button = st.sidebar.button("🔄 Load Data", use_container_width=True)

    if load_button:
        with st.spinner(f"Fetching {ticker} data from Yahoo Finance..."):
            try:
                # Fetch data using Yahoo Finance fetcher
                price_data = fetch_ticker(
                    ticker=ticker,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                )

                if price_data is not None and len(price_data) > 0:
                    # Normalize column names to lowercase for consistency
                    price_data.columns = price_data.columns.str.lower()
                    # Store in session state
                    st.session_state.price_data = price_data
                    st.session_state.returns_data = price_data["close"].pct_change().dropna()
                    st.session_state.data_loaded = True
                    st.sidebar.success(f"✓ Loaded {len(price_data)} data points")
                else:
                    st.sidebar.error("Failed to fetch data. Check ticker symbol.")
            except Exception as e:
                st.sidebar.error(f"Error loading data: {str(e)}")
                logger.exception("Error in Yahoo Finance data fetch")

elif data_source == "Upload CSV":
    st.sidebar.subheader("CSV Upload Settings")

    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV file",
        type=["csv"],
        help="CSV must contain 'date' and 'close' columns",
    )

    if uploaded_file is not None:
        try:
            # Read CSV
            price_data = pd.read_csv(uploaded_file, parse_dates=["date"])
            price_data = price_data.set_index("date")

            # Validate required columns
            if "close" not in price_data.columns:
                st.sidebar.error("CSV must contain 'close' column")
            else:
                st.session_state.price_data = price_data
                st.session_state.returns_data = price_data["close"].pct_change().dropna()
                st.session_state.data_loaded = True
                st.sidebar.success(f"✓ Loaded {len(price_data)} data points")
        except Exception as e:
            st.sidebar.error(f"Error reading CSV: {str(e)}")

elif data_source == "Sample Data":
    st.sidebar.subheader("Sample Data Settings")

    sample_period = st.sidebar.selectbox(
        "Sample Period",
        options=[
            "2008 Financial Crisis",
            "2020 COVID Crash",
            "2022 Rate Hike Crisis",
            "Full Dataset (2004-2024)",
        ],
        help="Pre-loaded sample data covering major crises",
    )

    load_sample_button = st.sidebar.button("🔄 Load Sample", use_container_width=True)

    if load_sample_button:
        with st.spinner(f"Loading sample data: {sample_period}..."):
            try:
                # Define date ranges for each sample
                sample_ranges = {
                    "2008 Financial Crisis": ("2007-01-01", "2010-12-31"),
                    "2020 COVID Crash": ("2019-01-01", "2021-12-31"),
                    "2022 Rate Hike Crisis": ("2021-01-01", "2023-12-31"),
                    "Full Dataset (2004-2024)": ("2004-01-01", "2024-12-31"),
                }

                start, end = sample_ranges[sample_period]

                # Fetch S&P 500 data for sample period
                price_data = fetch_ticker(ticker="^GSPC", start_date=start, end_date=end)

                if price_data is not None and len(price_data) > 0:
                    # Normalize column names to lowercase for consistency
                    price_data.columns = price_data.columns.str.lower()
                    st.session_state.price_data = price_data
                    st.session_state.returns_data = price_data["close"].pct_change().dropna()
                    st.session_state.data_loaded = True
                    st.sidebar.success(f"✓ Loaded {len(price_data)} sample data points")
                else:
                    st.sidebar.error("Failed to load sample data")
            except Exception as e:
                st.sidebar.error(f"Error loading sample: {str(e)}")
                logger.exception("Error loading sample data")

# =============================================================================
# Sidebar: TDA Analysis Parameters
# =============================================================================

st.sidebar.header("🔧 TDA Parameters")

with st.sidebar.expander("Embedding Parameters", expanded=False):
    embedding_dim = st.slider(
        "Embedding Dimension",
        min_value=2,
        max_value=10,
        value=3,
        help="Takens embedding dimension (d)",
    )
    embedding_delay = st.slider(
        "Embedding Delay",
        min_value=1,
        max_value=20,
        value=5,
        help="Takens embedding delay (tau)",
    )

with st.sidebar.expander("Window Parameters", expanded=False):
    window_size = st.slider(
        "Window Size",
        min_value=20,
        max_value=100,
        value=40,
        help="Sliding window size in days",
    )
    window_stride = st.slider(
        "Window Stride",
        min_value=1,
        max_value=20,
        value=5,
        help="Stride between windows in days",
    )

with st.sidebar.expander("Persistence Parameters", expanded=False):
    max_homology_dim = st.selectbox(
        "Max Homology Dimension",
        options=[0, 1, 2],
        index=2,
        help="Maximum homology dimension to compute (H0, H1, H2)",
    )

# =============================================================================
# Main Dashboard: Title and Data Overview
# =============================================================================

st.title("📊 Financial TDA Dashboard")
st.markdown("Interactive topological data analysis for financial market regime detection and anomaly alerts.")

# Show data status
if not st.session_state.data_loaded:
    st.info("👈 Select a data source from the sidebar to begin analysis")
    st.stop()

# Data overview section
st.header("📈 Data Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Data Points",
        f"{len(st.session_state.price_data):,}",
    )

with col2:
    date_range = (st.session_state.price_data.index.max() - st.session_state.price_data.index.min()).days
    st.metric("Date Range", f"{date_range} days")

with col3:
    start_date_str = st.session_state.price_data.index.min().strftime("%Y-%m-%d")
    st.metric("Start Date", start_date_str)

with col4:
    end_date_str = st.session_state.price_data.index.max().strftime("%Y-%m-%d")
    st.metric("End Date", end_date_str)

# Plot price data
st.subheader("Price History")

fig = px.line(
    st.session_state.price_data,
    x=st.session_state.price_data.index,
    y="close",
    labels={"close": "Close Price", "date": "Date"},
    title="Historical Price Data",
)
fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Price (USD)",
    hovermode="x unified",
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)

# Returns distribution
st.subheader("Returns Distribution")

col1, col2 = st.columns(2)

with col1:
    fig_returns = px.line(
        st.session_state.returns_data,
        x=st.session_state.returns_data.index,
        y=st.session_state.returns_data.values,
        labels={"y": "Daily Returns", "x": "Date"},
        title="Daily Returns Time Series",
    )
    fig_returns.update_layout(showlegend=False, hovermode="x unified")
    st.plotly_chart(fig_returns, use_container_width=True)

with col2:
    fig_hist = px.histogram(
        st.session_state.returns_data,
        x=st.session_state.returns_data.values,
        nbins=100,
        labels={"x": "Daily Returns"},
        title="Returns Histogram",
    )
    fig_hist.update_layout(showlegend=False)
    st.plotly_chart(fig_hist, use_container_width=True)

# Summary statistics
st.subheader("Summary Statistics")

stats_df = pd.DataFrame(
    {
        "Metric": [
            "Mean Return",
            "Std Deviation",
            "Min Return",
            "Max Return",
            "Skewness",
            "Kurtosis",
        ],
        "Value": [
            f"{st.session_state.returns_data.mean():.4f}",
            f"{st.session_state.returns_data.std():.4f}",
            f"{st.session_state.returns_data.min():.4f}",
            f"{st.session_state.returns_data.max():.4f}",
            f"{st.session_state.returns_data.skew():.4f}",
            f"{st.session_state.returns_data.kurtosis():.4f}",
        ],
    }
)

st.dataframe(stats_df, use_container_width=True, hide_index=True)

# =============================================================================
# Persistence Diagram Visualization
# =============================================================================

st.header("🔷 Persistence Diagram Analysis")

st.markdown(
    """
    Persistence diagrams reveal topological features in the financial time series at different scales.
    Points far from the diagonal indicate persistent features (structural patterns), while points near
    the diagonal represent noise.
    """
)

# Button to compute persistence
compute_persistence_button = st.button("🔬 Compute Persistence Diagrams", use_container_width=True)

if compute_persistence_button:
    with st.spinner("Computing persistence diagrams... This may take a few minutes."):
        try:
            # Extract windowed features with topological analysis
            returns_array = st.session_state.returns_data.values

            # Compute persistence diagrams for sliding windows
            from financial_tda.analysis.windowed import sliding_window_generator

            persistence_results = []
            window_dates = []

            for start_idx, end_idx, window_data in sliding_window_generator(
                returns_array,
                window_size=window_size,
                stride=window_stride,
            ):
                try:
                    # Takens embedding
                    point_cloud = takens_embedding(
                        window_data,
                        delay=embedding_delay,
                        dimension=embedding_dim,
                    )

                    # Compute persistence
                    diagram = compute_persistence_vr(
                        point_cloud,
                        homology_dimensions=tuple(range(max_homology_dim + 1)),
                    )

                    persistence_results.append(diagram)
                    # Get date for this window
                    window_date = st.session_state.returns_data.index[end_idx - 1]
                    window_dates.append(window_date)

                except Exception as e:
                    logger.warning(f"Failed to compute persistence for window [{start_idx}:{end_idx}]: {e}")
                    continue

            if len(persistence_results) > 0:
                st.session_state.persistence_diagrams = persistence_results
                st.session_state.window_dates = window_dates
                st.success(f"✓ Computed {len(persistence_results)} persistence diagrams")
            else:
                st.error("Failed to compute any persistence diagrams")

        except Exception as e:
            st.error(f"Error computing persistence: {str(e)}")
            logger.exception("Persistence computation error")

# Display persistence diagrams if computed
if st.session_state.persistence_diagrams is not None:
    st.subheader("Interactive Persistence Diagram")

    # Window selector
    selected_window_idx = st.slider(
        "Select Window",
        min_value=0,
        max_value=len(st.session_state.persistence_diagrams) - 1,
        value=0,
        help="Slide to view persistence diagram for different time windows",
    )

    selected_diagram = st.session_state.persistence_diagrams[selected_window_idx]
    selected_date = st.session_state.window_dates[selected_window_idx]

    st.write(f"**Window Date:** {selected_date.strftime('%Y-%m-%d')}")

    # Homology dimension selector
    col1, col2 = st.columns([3, 1])

    with col1:
        # Filter by selected dimensions
        dimension_filter = st.multiselect(
            "Homology Dimensions to Display",
            options=list(range(max_homology_dim + 1)),
            default=list(range(max_homology_dim + 1)),
            format_func=lambda x: f"H{x} ({'Components' if x == 0 else 'Loops' if x == 1 else 'Voids'})",
        )

    # Filter diagram by selected dimensions
    if len(dimension_filter) > 0:
        filtered_diagram = selected_diagram[np.isin(selected_diagram[:, 2], dimension_filter)]
    else:
        filtered_diagram = selected_diagram

    # Create persistence diagram plot
    if len(filtered_diagram) > 0:
        # Prepare data for plotting
        births = filtered_diagram[:, 0]
        deaths = filtered_diagram[:, 1]
        dims = filtered_diagram[:, 2].astype(int)

        # Calculate persistence
        persistence = deaths - births

        # Create DataFrame for plotly
        plot_df = pd.DataFrame(
            {
                "Birth": births,
                "Death": deaths,
                "Dimension": dims,
                "Persistence": persistence,
            }
        )

        # Map dimension to color and label
        dimension_labels = {0: "H0 (Components)", 1: "H1 (Loops)", 2: "H2 (Voids)"}
        plot_df["Dimension_Label"] = plot_df["Dimension"].map(dimension_labels)

        # Create scatter plot
        fig = px.scatter(
            plot_df,
            x="Birth",
            y="Death",
            color="Dimension_Label",
            size="Persistence",
            hover_data={
                "Birth": ":.4f",
                "Death": ":.4f",
                "Persistence": ":.4f",
                "Dimension_Label": True,
            },
            labels={
                "Birth": "Birth Time",
                "Death": "Death Time",
                "Dimension_Label": "Feature Type",
            },
            title=f"Persistence Diagram - {selected_date.strftime('%Y-%m-%d')}",
            color_discrete_map={
                "H0 (Components)": "#636EFA",
                "H1 (Loops)": "#EF553B",
                "H2 (Voids)": "#00CC96",
            },
        )

        # Add diagonal line (birth = death)
        max_val = max(deaths.max(), births.max())
        fig.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode="lines",
                line=dict(color="gray", dash="dash", width=1),
                name="Diagonal",
                showlegend=True,
            )
        )

        fig.update_layout(
            xaxis_title="Birth Time",
            yaxis_title="Death Time",
            hovermode="closest",
            height=600,
        )

        st.plotly_chart(fig, use_container_width=True)

        # Persistence statistics
        st.subheader("Persistence Statistics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Features", len(filtered_diagram))

        with col2:
            st.metric("Mean Persistence", f"{persistence.mean():.4f}")

        with col3:
            st.metric("Max Persistence", f"{persistence.max():.4f}")

        with col4:
            st.metric("Birth Range", f"[{births.min():.3f}, {births.max():.3f}]")

        # Dimension breakdown
        st.subheader("Feature Breakdown by Dimension")

        dimension_counts = plot_df.groupby("Dimension_Label").agg(
            {
                "Persistence": ["count", "mean", "max", "sum"],
            }
        )
        dimension_counts.columns = [
            "Count",
            "Mean Persistence",
            "Max Persistence",
            "Total Persistence",
        ]
        st.dataframe(dimension_counts, use_container_width=True)

        # Persistence distribution
        col1, col2 = st.columns(2)

        with col1:
            fig_pers_hist = px.histogram(
                plot_df,
                x="Persistence",
                color="Dimension_Label",
                nbins=30,
                title="Persistence Distribution",
                labels={"Persistence": "Persistence (Death - Birth)"},
                color_discrete_map={
                    "H0 (Components)": "#636EFA",
                    "H1 (Loops)": "#EF553B",
                    "H2 (Voids)": "#00CC96",
                },
            )
            st.plotly_chart(fig_pers_hist, use_container_width=True)

        with col2:
            fig_birth_hist = px.histogram(
                plot_df,
                x="Birth",
                color="Dimension_Label",
                nbins=30,
                title="Birth Time Distribution",
                labels={"Birth": "Birth Time"},
                color_discrete_map={
                    "H0 (Components)": "#636EFA",
                    "H1 (Loops)": "#EF553B",
                    "H2 (Voids)": "#00CC96",
                },
            )
            st.plotly_chart(fig_birth_hist, use_container_width=True)

    else:
        st.warning("No features found for selected dimensions")

else:
    st.info("👆 Click 'Compute Persistence Diagrams' to begin topological analysis")

# =============================================================================
# Regime Detection Display
# =============================================================================

st.header("🚦 Regime Detection & Classification")

st.markdown(
    """
    Market regime detection identifies crisis periods (high volatility, drawdowns) vs normal periods.
    The classifier uses topological features extracted from sliding windows to predict market state.
    """
)

# Regime detection controls
col1, col2 = st.columns(2)

with col1:
    classifier_type = st.selectbox(
        "Classifier Type",
        options=["random_forest", "svm", "xgboost", "gradient_boosting"],
        format_func=lambda x: {
            "random_forest": "Random Forest",
            "svm": "Support Vector Machine",
            "xgboost": "XGBoost",
            "gradient_boosting": "Gradient Boosting",
        }[x],
        help="ML classifier backend for regime detection",
    )

with col2:
    use_pretrained = st.checkbox(
        "Use Pre-trained Model",
        value=False,
        help="Use a pre-trained classifier (if available) or train on current data",
    )

# Button to compute regime detection
compute_regime_button = st.button("🔬 Detect Market Regimes", use_container_width=True)

if compute_regime_button:
    # Check if windowed features exist
    if st.session_state.persistence_diagrams is None:
        st.warning("⚠️ Please compute persistence diagrams first (Step 2)")
    else:
        with st.spinner("Training regime classifier and detecting market states..."):
            try:
                # Extract windowed topological features
                returns_array = st.session_state.returns_data.values

                windowed_features_df = extract_windowed_features(
                    returns_array,
                    window_size=window_size,
                    stride=window_stride,
                    embedding_dim=embedding_dim,
                    embedding_delay=embedding_delay,
                )

                # Convert window indices to actual dates
                windowed_features_df["window_end_date"] = windowed_features_df["window_end"].apply(
                    lambda idx: st.session_state.returns_data.index[idx - 1]
                )

                st.session_state.windowed_features = windowed_features_df

                # Fetch VIX data for labeling and comparison
                try:
                    vix_data = fetch_ticker(
                        ticker="^VIX",
                        start_date=st.session_state.price_data.index.min().strftime("%Y-%m-%d"),
                        end_date=st.session_state.price_data.index.max().strftime("%Y-%m-%d"),
                    )
                    # Normalize column names to lowercase
                    if vix_data is not None and len(vix_data) > 0:
                        vix_data.columns = vix_data.columns.str.lower()
                        st.info(
                            f"✓ Fetched VIX data: {len(vix_data)} days "
                            f"({vix_data.index.min().strftime('%Y-%m-%d')} to {vix_data.index.max().strftime('%Y-%m-%d')})"
                        )
                        st.session_state.vix_data = vix_data
                    else:
                        raise ValueError("VIX data is empty")
                except Exception as e:
                    st.warning(f"⚠️ Could not fetch VIX data: {e}. Using 20-day rolling volatility as proxy.")
                    # Create volatility proxy if VIX unavailable
                    rolling_vol = st.session_state.returns_data.rolling(window=20).std() * np.sqrt(252) * 100
                    st.session_state.vix_data = pd.DataFrame(
                        {"close": rolling_vol},
                        index=st.session_state.returns_data.index,
                    )

                # Create regime labels
                if st.session_state.vix_data is not None:
                    try:
                        regime_labels = create_regime_labels(
                            prices=st.session_state.price_data["close"],
                            vix=st.session_state.vix_data["close"],
                            vix_crisis_threshold=25.0,
                            vix_crisis_days=5,
                            vix_normal_threshold=20.0,
                            vix_normal_days=20,
                            drawdown_threshold=0.15,
                        )
                    except ValueError as e:
                        if "no overlapping dates" in str(e).lower():
                            # Date mismatch - align VIX data to price data dates
                            st.warning("⚠️ Aligning VIX data to price data dates...")
                            # Reindex VIX to match price data, forward fill missing values
                            aligned_vix = st.session_state.vix_data["close"].reindex(
                                st.session_state.price_data.index, method="ffill"
                            )
                            regime_labels = create_regime_labels(
                                prices=st.session_state.price_data["close"],
                                vix=aligned_vix,
                                vix_crisis_threshold=25.0,
                                vix_crisis_days=5,
                                vix_normal_threshold=20.0,
                                vix_normal_days=20,
                                drawdown_threshold=0.15,
                            )
                        else:
                            raise

                    # Get window dates (now actual datetimes, not indices)
                    feature_dates = windowed_features_df["window_end_date"]

                    # Strip timezone from both labels and windows for consistent matching
                    if regime_labels.index.tz is not None:
                        regime_labels.index = regime_labels.index.tz_localize(None)

                    # Also strip timezone from window dates if present
                    if hasattr(feature_dates.iloc[0], "tz") and feature_dates.iloc[0].tz is not None:
                        feature_dates = feature_dates.dt.tz_localize(None)
                        windowed_features_df["window_end_date"] = feature_dates

                    # Debug: Show regime labels info
                    n_labels = len(regime_labels)
                    n_valid = (~regime_labels.isna()).sum()
                    n_crisis_labels = (regime_labels == 1).sum()
                    n_normal_labels = (regime_labels == 0).sum()

                    with st.expander("🔍 Debug: Regime Labels Info", expanded=False):
                        st.write(f"- Total labels: {n_labels}")
                        st.write(f"- Valid (non-NaN) labels: {n_valid}")
                        st.write(f"- Crisis labels (1): {n_crisis_labels}")
                        st.write(f"- Normal labels (0): {n_normal_labels}")
                        st.write(f"- Label date range: {regime_labels.index.min()} to {regime_labels.index.max()}")
                        st.write(f"- Window date range: {feature_dates.min()} to {feature_dates.max()}")
                        st.write(
                            f"- Date types: labels={type(regime_labels.index[0])}, windows={type(feature_dates.iloc[0])}"
                        )
                        # Sample matching
                        sample_window_date = feature_dates.iloc[0]
                        st.write(f"- Sample window date: {sample_window_date}")
                        st.write(f"- Is in regime_labels? {sample_window_date in regime_labels.index}")

                    # Align labels with windowed features
                    aligned_labels = []
                    valid_indices = []

                    for i, date in enumerate(feature_dates):
                        if date in regime_labels.index:
                            label = regime_labels.loc[date]
                            if not pd.isna(label):
                                aligned_labels.append(int(label))
                                valid_indices.append(i)

                    # Diagnostic info
                    st.info(f"📊 Regime labeling: {len(aligned_labels)}/{len(feature_dates)} windows have valid labels")

                    if len(aligned_labels) > 10:  # Need enough samples
                        # Check class balance
                        n_crisis = sum(aligned_labels)
                        n_normal = len(aligned_labels) - n_crisis

                        if n_crisis < 5 or n_normal < 5:
                            st.warning(
                                f"⚠️ Imbalanced data: {n_crisis} crisis vs {n_normal} normal windows. "
                                "Results may be unreliable. Consider adjusting VIX thresholds or date range."
                            )

                        # Prepare features for classification
                        X, scaler = prepare_features(windowed_features_df.iloc[valid_indices])
                        y = np.array(aligned_labels)

                        # Train classifier
                        if not use_pretrained or st.session_state.regime_classifier is None:
                            classifier = RegimeClassifier(
                                classifier_type=classifier_type,
                                class_weight="balanced",
                                random_state=42,
                            )

                            # Fit on labeled data
                            classifier.fit(X, y)
                            st.session_state.regime_classifier = classifier
                            st.success(
                                f"✓ Trained {classifier_type} on {len(y)} samples ({n_crisis} crisis, {n_normal} normal)"
                            )
                        else:
                            classifier = st.session_state.regime_classifier

                        # Predict on all windows
                        X_all, _ = prepare_features(windowed_features_df, scaler=scaler, fit_scaler=False)
                        predictions = classifier.predict(X_all)
                        probabilities = classifier.predict_proba(X_all)

                        # Store results
                        st.session_state.regime_predictions = predictions
                        st.session_state.regime_confidence = probabilities[:, 1]  # Probability of crisis

                        st.success(
                            f"✓ Classified {len(predictions)} windows: {(predictions == 1).sum()} crisis, {(predictions == 0).sum()} normal"
                        )
                    else:
                        st.error(
                            f"❌ Not enough labeled data for training: only {len(aligned_labels)}/{len(feature_dates)} windows have labels.\n\n"
                            "**Possible causes:**\n"
                            "- VIX/price date misalignment (check if VIX data was fetched successfully)\n"
                            "- Window dates don't match available label dates\n"
                            "- Too many NaN values in regime labels\n\n"
                            "**Solutions:**\n"
                            "- Try a longer date range (2007-2023 recommended for crisis coverage)\n"
                            "- Use a more recent date range where VIX data is available\n"
                            "- Reduce window size or stride to generate more windows"
                        )
                else:
                    st.error("Could not obtain VIX or volatility data for labeling")

            except Exception as e:
                st.error(f"Error in regime detection: {str(e)}")
                logger.exception("Regime detection error")

# Display regime timeline if computed
if st.session_state.regime_predictions is not None:
    st.subheader("Regime Timeline Visualization")

    # Create timeline dataframe
    timeline_df = pd.DataFrame(
        {
            "Date": st.session_state.windowed_features["window_end_date"],
            "Regime": st.session_state.regime_predictions,
            "Crisis_Probability": st.session_state.regime_confidence,
        }
    )

    # Create figure with secondary y-axis
    fig = go.Figure()

    # Add price data
    fig.add_trace(
        go.Scatter(
            x=st.session_state.price_data.index,
            y=st.session_state.price_data["close"],
            name="Price",
            line=dict(color="lightgray", width=1),
            yaxis="y2",
            hovertemplate="Price: $%{y:.2f}<extra></extra>",
        )
    )

    # Add regime predictions as colored background
    crisis_periods = timeline_df[timeline_df["Regime"] == 1]
    for _, row in crisis_periods.iterrows():
        fig.add_vrect(
            x0=row["Date"] - pd.Timedelta(days=window_size // 2),
            x1=row["Date"] + pd.Timedelta(days=window_size // 2),
            fillcolor="red",
            opacity=0.2,
            layer="below",
            line_width=0,
        )

    # Add confidence line
    fig.add_trace(
        go.Scatter(
            x=timeline_df["Date"],
            y=timeline_df["Crisis_Probability"],
            name="Crisis Probability",
            line=dict(color="darkred", width=2),
            yaxis="y",
            hovertemplate="Crisis Prob: %{y:.2%}<extra></extra>",
        )
    )

    # Add VIX or volatility overlay
    if st.session_state.vix_data is not None:
        # Normalize VIX to 0-1 range for comparison
        vix_normalized = (st.session_state.vix_data["close"] - st.session_state.vix_data["close"].min()) / (
            st.session_state.vix_data["close"].max() - st.session_state.vix_data["close"].min()
        )

        fig.add_trace(
            go.Scatter(
                x=st.session_state.vix_data.index,
                y=vix_normalized,
                name="VIX (normalized)",
                line=dict(color="orange", width=1, dash="dot"),
                yaxis="y",
                hovertemplate="VIX: %{text:.1f}<extra></extra>",
                text=st.session_state.vix_data["close"],
            )
        )

    # Update layout
    fig.update_layout(
        title="Market Regime Timeline with Crisis Detection",
        xaxis_title="Date",
        yaxis=dict(
            title="Probability / Normalized VIX",
            range=[0, 1],
        ),
        yaxis2=dict(
            title="Price (USD)",
            overlaying="y",
            side="right",
        ),
        hovermode="x unified",
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Regime statistics
    st.subheader("Regime Detection Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        crisis_count = (st.session_state.regime_predictions == 1).sum()
        st.metric("Crisis Windows", crisis_count)

    with col2:
        normal_count = (st.session_state.regime_predictions == 0).sum()
        st.metric("Normal Windows", normal_count)

    with col3:
        crisis_pct = 100 * crisis_count / len(st.session_state.regime_predictions)
        st.metric("Crisis %", f"{crisis_pct:.1f}%")

    with col4:
        mean_confidence = st.session_state.regime_confidence.mean()
        st.metric("Mean Crisis Prob", f"{mean_confidence:.2%}")

    # Confidence distribution
    st.subheader("Confidence Distribution")

    col1, col2 = st.columns(2)

    with col1:
        # Histogram of crisis probability
        fig_conf_hist = px.histogram(
            timeline_df,
            x="Crisis_Probability",
            color="Regime",
            nbins=50,
            title="Crisis Probability Distribution",
            labels={
                "Crisis_Probability": "Crisis Probability",
                "Regime": "True Regime",
            },
            color_discrete_map={0: "green", 1: "red"},
            barmode="overlay",
        )
        fig_conf_hist.update_layout(showlegend=True)
        st.plotly_chart(fig_conf_hist, use_container_width=True)

    with col2:
        # Time series of confidence
        fig_conf_ts = px.line(
            timeline_df,
            x="Date",
            y="Crisis_Probability",
            color="Regime",
            title="Crisis Probability Over Time",
            labels={"Crisis_Probability": "Crisis Probability"},
            color_discrete_map={0: "green", 1: "red"},
        )
        st.plotly_chart(fig_conf_ts, use_container_width=True)

    # Detailed regime periods table
    with st.expander("📋 Detailed Regime Periods"):
        # Group consecutive crisis periods
        crisis_periods_list = []
        in_crisis = False
        crisis_start = None

        for idx, row in timeline_df.iterrows():
            if row["Regime"] == 1 and not in_crisis:
                in_crisis = True
                crisis_start = row["Date"]
            elif row["Regime"] == 0 and in_crisis:
                in_crisis = False
                crisis_periods_list.append(
                    {
                        "Start": crisis_start.strftime("%Y-%m-%d"),
                        "End": timeline_df.iloc[idx - 1]["Date"].strftime("%Y-%m-%d"),
                        "Duration (days)": (timeline_df.iloc[idx - 1]["Date"] - crisis_start).days,
                    }
                )

        if in_crisis:  # Handle case where crisis extends to end
            crisis_periods_list.append(
                {
                    "Start": crisis_start.strftime("%Y-%m-%d"),
                    "End": timeline_df.iloc[-1]["Date"].strftime("%Y-%m-%d"),
                    "Duration (days)": (timeline_df.iloc[-1]["Date"] - crisis_start).days,
                }
            )

        if len(crisis_periods_list) > 0:
            crisis_df = pd.DataFrame(crisis_periods_list)
            st.dataframe(crisis_df, use_container_width=True, hide_index=True)
        else:
            st.info("No crisis periods detected")

else:
    st.info("👆 Click 'Detect Market Regimes' to begin classification")

# =============================================================================
# Anomaly Detection & Alerts
# =============================================================================

st.header("⚠️ Anomaly Detection & Early Warning System")

st.markdown(
    """
    The Persistence Autoencoder learns the "normal" topology of stable markets and flags
    anomalous patterns indicating market stress. High reconstruction errors suggest
    topological changes associated with crisis periods.
    """
)

# Anomaly detection controls
col1, col2 = st.columns(2)

with col1:
    anomaly_threshold_percentile = st.slider(
        "Alert Threshold Percentile",
        min_value=80,
        max_value=99,
        value=95,
        help="Percentile of reconstruction error for anomaly threshold (default: 95th)",
    )

with col2:
    use_pretrained_ae = st.checkbox(
        "Use Pre-trained Autoencoder",
        value=False,
        help="Use cached autoencoder model or train new one",
    )

# Button to compute anomaly detection
compute_anomaly_button = st.button("🔬 Detect Anomalies", use_container_width=True)

if compute_anomaly_button:
    if st.session_state.persistence_diagrams is None:
        st.warning("⚠️ Please compute persistence diagrams first (Step 2)")
    else:
        with st.spinner("Computing persistence images and training autoencoder..."):
            try:
                import torch

                from financial_tda.topology.features import compute_persistence_image

                # Convert persistence diagrams to persistence images
                persistence_images = []

                for diagram in st.session_state.persistence_diagrams:
                    # Filter for H1 features (loops) - most informative for crisis detection
                    h1_diagram = diagram[diagram[:, 2] == 1]  # Keep all 3 columns: birth, death, dimension

                    if len(h1_diagram) > 0:
                        # Create persistence image
                        img = compute_persistence_image(
                            h1_diagram,
                            resolution=(50, 50),
                            sigma=0.1,
                        )
                        # Reshape from (1, 2500) to (50, 50)
                        img_2d = img.reshape(50, 50)
                        persistence_images.append(img_2d)
                    else:
                        # Empty image if no H1 features
                        persistence_images.append(np.zeros((50, 50)))

                persistence_images = np.array(persistence_images)
                st.session_state.persistence_images = persistence_images

                st.info(f"✓ Generated {len(persistence_images)} persistence images (50×50)")

                # Train or load autoencoder
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

                if not use_pretrained_ae or st.session_state.autoencoder_model is None:
                    # Initialize model
                    model = PersistenceAutoencoder(
                        input_size=(50, 50),
                        latent_dim=32,
                    ).to(device)

                    # For demo purposes, use a simple training approach
                    # In production, should train only on normal periods
                    st.info("⚠️ Demo mode: Training on all available data")
                    st.info("Production: Should train only on 2004-2007, 2013-2019 normal periods")

                    # Convert to torch tensors
                    images_tensor = torch.FloatTensor(persistence_images).unsqueeze(1)  # Add channel dim

                    # Simple training loop (abbreviated for demo)
                    from torch.utils.data import DataLoader, TensorDataset

                    dataset = TensorDataset(images_tensor)
                    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

                    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
                    criterion = torch.nn.MSELoss()

                    model.train()
                    n_epochs = 50

                    progress_bar = st.progress(0)
                    for epoch in range(n_epochs):
                        epoch_loss = 0.0
                        for batch in dataloader:
                            images_batch = batch[0].to(device)

                            optimizer.zero_grad()
                            reconstructions = model(images_batch)
                            loss = criterion(reconstructions, images_batch)
                            loss.backward()
                            optimizer.step()

                            epoch_loss += loss.item()

                        if (epoch + 1) % 10 == 0:
                            st.write(f"Epoch {epoch + 1}/{n_epochs}, Loss: {epoch_loss / len(dataloader):.6f}")

                        progress_bar.progress((epoch + 1) / n_epochs)

                    st.session_state.autoencoder_model = model
                    st.success("✓ Autoencoder training complete")
                else:
                    model = st.session_state.autoencoder_model
                    st.info("✓ Using cached autoencoder model")

                # Compute anomaly scores (reconstruction errors)
                model.eval()
                with torch.no_grad():
                    images_tensor = torch.FloatTensor(persistence_images).unsqueeze(1).to(device)
                    reconstructions = model(images_tensor)

                    # Compute MSE per sample
                    errors = torch.mean((images_tensor - reconstructions) ** 2, dim=[1, 2, 3])
                    anomaly_scores = errors.cpu().numpy()

                st.session_state.anomaly_scores = anomaly_scores

                # Compute threshold
                threshold = np.percentile(anomaly_scores, anomaly_threshold_percentile)
                st.session_state.anomaly_threshold = threshold

                # Count anomalies
                n_anomalies = (anomaly_scores > threshold).sum()
                st.success(f"✓ Computed anomaly scores: {n_anomalies}/{len(anomaly_scores)} anomalies detected")

            except Exception as e:
                st.error(f"Error in anomaly detection: {str(e)}")
                logger.exception("Anomaly detection error")

# Display anomaly detection results
if st.session_state.anomaly_scores is not None:
    st.subheader("Reconstruction Error Timeline")

    # Create timeline dataframe
    anomaly_df = pd.DataFrame(
        {
            "Date": st.session_state.window_dates,
            "Reconstruction_Error": st.session_state.anomaly_scores,
            "Is_Anomaly": st.session_state.anomaly_scores > st.session_state.anomaly_threshold,
        }
    )

    # Create figure
    fig = go.Figure()

    # Add reconstruction error line
    fig.add_trace(
        go.Scatter(
            x=anomaly_df["Date"],
            y=anomaly_df["Reconstruction_Error"],
            name="Reconstruction Error",
            line=dict(color="blue", width=2),
            mode="lines",
            hovertemplate="Error: %{y:.6f}<extra></extra>",
        )
    )

    # Add threshold line
    fig.add_trace(
        go.Scatter(
            x=anomaly_df["Date"],
            y=[st.session_state.anomaly_threshold] * len(anomaly_df),
            name=f"Threshold ({anomaly_threshold_percentile}th percentile)",
            line=dict(color="red", width=2, dash="dash"),
            mode="lines",
            hovertemplate="Threshold: %{y:.6f}<extra></extra>",
        )
    )

    # Add anomaly markers
    anomalies = anomaly_df[anomaly_df["Is_Anomaly"]]
    if len(anomalies) > 0:
        fig.add_trace(
            go.Scatter(
                x=anomalies["Date"],
                y=anomalies["Reconstruction_Error"],
                name="Anomaly Alert",
                mode="markers",
                marker=dict(
                    color="red",
                    size=10,
                    symbol="x",
                    line=dict(width=2),
                ),
                hovertemplate="⚠️ Anomaly<br>Error: %{y:.6f}<extra></extra>",
            )
        )

    fig.update_layout(
        title="Autoencoder Reconstruction Error Over Time",
        xaxis_title="Date",
        yaxis_title="Reconstruction Error (MSE)",
        hovermode="x unified",
        height=500,
        showlegend=True,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Anomaly statistics
    st.subheader("Anomaly Detection Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        n_anomalies = anomaly_df["Is_Anomaly"].sum()
        st.metric("Anomalies Detected", n_anomalies)

    with col2:
        anomaly_pct = 100 * n_anomalies / len(anomaly_df)
        st.metric("Anomaly Rate", f"{anomaly_pct:.1f}%")

    with col3:
        mean_error = anomaly_df["Reconstruction_Error"].mean()
        st.metric("Mean Error", f"{mean_error:.6f}")

    with col4:
        max_error = anomaly_df["Reconstruction_Error"].max()
        st.metric("Max Error", f"{max_error:.6f}")

    # Combined regime + anomaly view
    if st.session_state.regime_predictions is not None:
        st.subheader("Integrated Regime & Anomaly Timeline")

        # Create combined figure
        fig_combined = go.Figure()

        # Add price with secondary axis
        fig_combined.add_trace(
            go.Scatter(
                x=st.session_state.price_data.index,
                y=st.session_state.price_data["close"],
                name="Price",
                line=dict(color="lightgray", width=1),
                yaxis="y2",
                hovertemplate="Price: $%{y:.2f}<extra></extra>",
            )
        )

        # Add regime predictions (normalized crisis probability)
        regime_timeline = pd.DataFrame(
            {
                "Date": st.session_state.windowed_features["window_end"],
                "Crisis_Probability": st.session_state.regime_confidence,
            }
        )

        fig_combined.add_trace(
            go.Scatter(
                x=regime_timeline["Date"],
                y=regime_timeline["Crisis_Probability"],
                name="Crisis Probability",
                line=dict(color="darkred", width=2),
                yaxis="y",
                hovertemplate="Crisis Prob: %{y:.2%}<extra></extra>",
            )
        )

        # Add normalized anomaly scores
        anomaly_normalized = (anomaly_df["Reconstruction_Error"] - anomaly_df["Reconstruction_Error"].min()) / (
            anomaly_df["Reconstruction_Error"].max() - anomaly_df["Reconstruction_Error"].min()
        )

        fig_combined.add_trace(
            go.Scatter(
                x=anomaly_df["Date"],
                y=anomaly_normalized,
                name="Anomaly Score (normalized)",
                line=dict(color="purple", width=2, dash="dot"),
                yaxis="y",
                hovertemplate="Anomaly: %{text:.6f}<extra></extra>",
                text=anomaly_df["Reconstruction_Error"],
            )
        )

        # Add anomaly markers
        if len(anomalies) > 0:
            anomaly_norm_markers = (anomalies["Reconstruction_Error"] - anomaly_df["Reconstruction_Error"].min()) / (
                anomaly_df["Reconstruction_Error"].max() - anomaly_df["Reconstruction_Error"].min()
            )

            fig_combined.add_trace(
                go.Scatter(
                    x=anomalies["Date"],
                    y=anomaly_norm_markers,
                    name="Anomaly Alert",
                    mode="markers",
                    marker=dict(
                        color="red",
                        size=12,
                        symbol="diamond",
                        line=dict(width=2, color="darkred"),
                    ),
                    yaxis="y",
                    hovertemplate="⚠️ Alert<extra></extra>",
                )
            )

        # Shade crisis regions
        crisis_periods = regime_timeline[regime_timeline["Crisis_Probability"] > 0.5]
        for _, row in crisis_periods.iterrows():
            fig_combined.add_vrect(
                x0=row["Date"] - pd.Timedelta(days=window_size // 2),
                x1=row["Date"] + pd.Timedelta(days=window_size // 2),
                fillcolor="red",
                opacity=0.1,
                layer="below",
                line_width=0,
            )

        fig_combined.update_layout(
            title="Combined View: Market Regime + Topological Anomalies",
            xaxis_title="Date",
            yaxis=dict(
                title="Normalized Scores / Probability",
                range=[0, 1],
            ),
            yaxis2=dict(
                title="Price (USD)",
                overlaying="y",
                side="right",
            ),
            hovermode="x unified",
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )

        st.plotly_chart(fig_combined, use_container_width=True)

    # Anomaly list
    with st.expander("📋 Detected Anomaly Events"):
        if len(anomalies) > 0:
            anomaly_list = anomalies[["Date", "Reconstruction_Error"]].copy()
            anomaly_list["Date"] = anomaly_list["Date"].dt.strftime("%Y-%m-%d")
            anomaly_list = anomaly_list.sort_values("Reconstruction_Error", ascending=False)
            anomaly_list.columns = ["Date", "Reconstruction Error"]

            st.dataframe(anomaly_list, use_container_width=True, hide_index=True)
        else:
            st.info("No anomalies detected with current threshold")

    # Error distribution
    st.subheader("Error Distribution Analysis")

    col1, col2 = st.columns(2)

    with col1:
        fig_error_hist = px.histogram(
            anomaly_df,
            x="Reconstruction_Error",
            nbins=50,
            title="Reconstruction Error Distribution",
            labels={"Reconstruction_Error": "Reconstruction Error (MSE)"},
        )
        fig_error_hist.add_vline(
            x=st.session_state.anomaly_threshold,
            line_dash="dash",
            line_color="red",
            annotation_text="Threshold",
        )
        st.plotly_chart(fig_error_hist, use_container_width=True)

    with col2:
        # Box plot by month
        anomaly_df["Month"] = pd.to_datetime(anomaly_df["Date"]).dt.to_period("M").astype(str)
        fig_box = px.box(
            anomaly_df,
            x="Month",
            y="Reconstruction_Error",
            title="Error Distribution by Month",
            labels={"Reconstruction_Error": "Reconstruction Error"},
        )
        fig_box.update_xaxes(tickangle=45)
        st.plotly_chart(fig_box, use_container_width=True)

else:
    st.info("👆 Click 'Detect Anomalies' to begin autoencoder-based anomaly detection")

# =============================================================================
# Real-time Monitoring Interface
# =============================================================================

st.header("⚡ Real-time Monitoring Interface")

st.markdown(
    """
    Monitor live market topology with automatic refresh, bottleneck distance tracking,
    and configurable alert thresholds. Test with historical data replay at accelerated speed.
    """
)

# Initialize monitoring session state
if "monitoring_active" not in st.session_state:
    st.session_state.monitoring_active = False
if "monitoring_refresh_interval" not in st.session_state:
    st.session_state.monitoring_refresh_interval = 5
if "monitoring_reference_state" not in st.session_state:
    st.session_state.monitoring_reference_state = None
if "monitoring_alert_threshold" not in st.session_state:
    st.session_state.monitoring_alert_threshold = 2.0
if "monitoring_recent_alerts" not in st.session_state:
    st.session_state.monitoring_recent_alerts = []
if "replay_mode" not in st.session_state:
    st.session_state.replay_mode = False
if "replay_speed" not in st.session_state:
    st.session_state.replay_speed = 10.0
if "replay_position" not in st.session_state:
    st.session_state.replay_position = 0
if "replay_playing" not in st.session_state:
    st.session_state.replay_playing = False

# Monitoring controls in sidebar
st.sidebar.header("⚡ Real-time Monitor Controls")

with st.sidebar.expander("Auto-Refresh Settings", expanded=True):
    auto_refresh_enabled = st.checkbox(
        "Enable Auto-Refresh",
        value=st.session_state.monitoring_active,
        help="Automatically refresh data at specified interval",
    )
    st.session_state.monitoring_active = auto_refresh_enabled

    refresh_interval = st.slider(
        "Refresh Interval (seconds)",
        min_value=1,
        max_value=60,
        value=st.session_state.monitoring_refresh_interval,
        help="How often to update the display",
    )
    st.session_state.monitoring_refresh_interval = refresh_interval

with st.sidebar.expander("Reference State Selection", expanded=False):
    st.markdown("**Baseline Period for Comparison**")

    # Predefined reference periods
    reference_preset = st.selectbox(
        "Preset Reference Period",
        options=[
            "Custom Date Range",
            "Pre-GFC (2004-2007)",
            "Post-Recovery (2013-2019)",
            "Recent Stable (Last 100 days)",
        ],
        help="Select a normal period baseline for anomaly detection",
    )

    if reference_preset == "Custom Date Range" and st.session_state.data_loaded:
        ref_start = st.date_input(
            "Reference Start Date",
            value=st.session_state.price_data.index.min().date(),
        )
        ref_end = st.date_input(
            "Reference End Date",
            value=st.session_state.price_data.index.min().date() + pd.Timedelta(days=100),
        )
        st.session_state.monitoring_reference_state = {
            "type": "custom",
            "start": pd.to_datetime(ref_start),
            "end": pd.to_datetime(ref_end),
        }
    elif reference_preset == "Pre-GFC (2004-2007)":
        st.session_state.monitoring_reference_state = {
            "type": "preset",
            "start": pd.to_datetime("2004-01-01"),
            "end": pd.to_datetime("2007-06-30"),
        }
    elif reference_preset == "Post-Recovery (2013-2019)":
        st.session_state.monitoring_reference_state = {
            "type": "preset",
            "start": pd.to_datetime("2013-01-01"),
            "end": pd.to_datetime("2019-12-31"),
        }
    elif reference_preset == "Recent Stable (Last 100 days)" and st.session_state.data_loaded:
        end_date = st.session_state.price_data.index.max()
        start_date = end_date - pd.Timedelta(days=100)
        st.session_state.monitoring_reference_state = {
            "type": "recent",
            "start": start_date,
            "end": end_date,
        }

with st.sidebar.expander("Alert Configuration", expanded=False):
    alert_threshold = st.slider(
        "Alert Threshold (σ)",
        min_value=1.0,
        max_value=5.0,
        value=st.session_state.monitoring_alert_threshold,
        step=0.1,
        help="Number of standard deviations from reference baseline",
    )
    st.session_state.monitoring_alert_threshold = alert_threshold

    st.markdown("**Current Settings:**")
    st.markdown(f"- Warning: > {alert_threshold:.1f}σ (yellow)")
    st.markdown(f"- Critical: > {alert_threshold * 1.5:.1f}σ (red)")

with st.sidebar.expander("Historical Data Replay", expanded=False):
    st.markdown("**Simulated Live Data Testing**")

    replay_mode = st.checkbox(
        "Enable Replay Mode",
        value=st.session_state.replay_mode,
        help="Replay historical data at accelerated speed",
    )
    st.session_state.replay_mode = replay_mode

    if replay_mode and st.session_state.data_loaded:
        replay_period = st.selectbox(
            "Crisis Period to Replay",
            options=[
                "2008 GFC (2007-2010)",
                "2020 COVID Crash (2019-2021)",
                "2022 Rate Hikes (2021-2023)",
            ],
            help="Select a crisis period for accelerated replay",
        )

        replay_speed = st.slider(
            "Replay Speed (x)",
            min_value=1,
            max_value=100,
            value=10,
            step=1,
            help="Speed multiplier: 10x = 10 trading days per second",
        )
        st.session_state.replay_speed = replay_speed

        # Map replay period to date range
        replay_ranges = {
            "2008 GFC (2007-2010)": ("2007-01-01", "2010-12-31"),
            "2020 COVID Crash (2019-2021)": ("2019-01-01", "2021-12-31"),
            "2022 Rate Hikes (2021-2023)": ("2021-01-01", "2023-12-31"),
        }

        replay_start, replay_end = replay_ranges[replay_period]
        st.session_state.replay_start = pd.to_datetime(replay_start)
        st.session_state.replay_end = pd.to_datetime(replay_end)

        # Reset button
        if st.button("Reset Replay", use_container_width=True):
            st.session_state.replay_position = 0
            st.rerun()

# Main monitoring display
if not st.session_state.data_loaded:
    st.info("👈 Load data from the sidebar to enable real-time monitoring")
    st.stop()

# Auto-refresh logic
if st.session_state.monitoring_active:
    st.markdown(f"🔄 **Auto-refresh enabled** (updating every {st.session_state.monitoring_refresh_interval}s)")

    # Use Streamlit's auto-rerun with time delay
    import time as time_module

    # Display countdown
    placeholder = st.empty()
    for remaining in range(st.session_state.monitoring_refresh_interval, 0, -1):
        placeholder.text(f"Next refresh in {remaining} seconds...")
        time_module.sleep(1)

    placeholder.empty()
    st.rerun()
else:
    st.markdown("ℹ️ Auto-refresh is disabled. Enable in sidebar to start monitoring.")

# Reference state display
if st.session_state.monitoring_reference_state is not None:
    ref_state = st.session_state.monitoring_reference_state
    st.subheader("📍 Reference Baseline Period")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Start Date",
            ref_state["start"].strftime("%Y-%m-%d"),
        )

    with col2:
        st.metric(
            "End Date",
            ref_state["end"].strftime("%Y-%m-%d"),
        )

    with col3:
        duration = (ref_state["end"] - ref_state["start"]).days
        st.metric("Duration", f"{duration} days")

    st.info(f"Using **{ref_state.get('type', 'custom')}** reference period for baseline comparison")
else:
    st.warning("⚠️ No reference baseline selected. Configure in sidebar to enable monitoring.")

# =============================================================================
# Simulated Live Data Replay (Testing Mode)
# =============================================================================

if st.session_state.replay_mode and st.session_state.data_loaded:
    st.subheader("🎬 Historical Data Replay Simulation")

    st.markdown(
        """
        **Test the monitoring system** by replaying historical crisis periods at accelerated speed.
        This simulates live data updates to validate alert thresholds and visualization responsiveness.
        """
    )

    # Get replay parameters
    replay_start = st.session_state.replay_start
    replay_end = st.session_state.replay_end
    replay_speed = st.session_state.replay_speed

    # Strip timezone from price data index and replay dates for comparison
    price_index = st.session_state.price_data.index
    if hasattr(price_index, "tz") and price_index.tz is not None:
        price_index_naive = price_index.tz_localize(None)
    else:
        price_index_naive = price_index

    if hasattr(replay_start, "tz") and replay_start.tz is not None:
        replay_start = replay_start.tz_localize(None)
    if hasattr(replay_end, "tz") and replay_end.tz is not None:
        replay_end = replay_end.tz_localize(None)

    # Filter price data to replay period
    replay_mask = (price_index_naive >= replay_start) & (price_index_naive <= replay_end)
    replay_data = st.session_state.price_data[replay_mask]

    if len(replay_data) == 0:
        st.error(
            f"No data available for replay period "
            f"({replay_start.strftime('%Y-%m-%d')} to {replay_end.strftime('%Y-%m-%d')})"
        )
    else:
        # Calculate replay progress
        total_days = len(replay_data)
        current_position = st.session_state.replay_position

        # Progress bar
        progress = min(current_position / total_days, 1.0) if total_days > 0 else 0.0
        st.progress(
            progress,
            text=f"Replay Progress: {current_position}/{total_days} days ({progress * 100:.1f}%)",
        )

        # Current date in replay
        if current_position < total_days:
            current_date = replay_data.index[current_position]
            st.metric("Current Replay Date", current_date.strftime("%Y-%m-%d %H:%M"))

            # Show current window data
            window_end = current_position
            window_start = max(0, window_end - window_size)

            current_window_data = replay_data.iloc[window_start:window_end]

            col1, col2, col3 = st.columns(3)

            with col1:
                if len(current_window_data) > 0:
                    current_price = current_window_data["close"].iloc[-1]
                    st.metric("Current Price", f"${current_price:.2f}")

            with col2:
                if len(current_window_data) > 1:
                    window_return = (
                        current_window_data["close"].iloc[-1] / current_window_data["close"].iloc[0] - 1
                    ) * 100
                    st.metric("Window Return", f"{window_return:+.2f}%")

            with col3:
                if len(current_window_data) > 1:
                    window_volatility = current_window_data["close"].pct_change().std() * np.sqrt(252) * 100
                    st.metric("Annualized Volatility", f"{window_volatility:.1f}%")

            # Price chart for replay window
            fig_replay = go.Figure()

            fig_replay.add_trace(
                go.Scatter(
                    x=current_window_data.index,
                    y=current_window_data["close"],
                    mode="lines",
                    name="Price",
                    line=dict(color="#636EFA", width=2),
                )
            )

            # Mark current position with a vertical marker
            if len(current_window_data) > 0:
                current_price = current_window_data["close"].iloc[-1]
                fig_replay.add_trace(
                    go.Scatter(
                        x=[current_date],
                        y=[current_price],
                        mode="markers+text",
                        name="Current",
                        marker=dict(size=15, color="red", symbol="diamond"),
                        text=["Current"],
                        textposition="top center",
                        showlegend=False,
                    )
                )

            fig_replay.update_layout(
                title=f"Replay Window (Last {window_size} Days)",
                xaxis_title="Date",
                yaxis_title="Price (USD)",
                hovermode="x unified",
                height=300,
                showlegend=False,
            )

            st.plotly_chart(fig_replay, use_container_width=True)

            # Replay controls
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                # Play/Pause toggle
                if st.session_state.replay_playing:
                    if st.button("⏸️ Pause", use_container_width=True, type="primary"):
                        st.session_state.replay_playing = False
                        st.rerun()
                else:
                    if st.button("▶️ Play", use_container_width=True, type="primary"):
                        st.session_state.replay_playing = True
                        st.rerun()

            with col2:
                if st.button("⏩ +10 Days", use_container_width=True):
                    st.session_state.replay_position = min(current_position + 10, total_days - 1)
                    st.rerun()

            with col3:
                if st.button("⏭️ End", use_container_width=True):
                    st.session_state.replay_position = total_days - 1
                    st.session_state.replay_playing = False
                    st.rerun()

            with col4:
                if st.button("🔄 Reset", use_container_width=True):
                    st.session_state.replay_position = 0
                    st.session_state.replay_playing = False
                    st.rerun()

            # Auto-advance when playing
            if st.session_state.replay_playing and current_position < total_days - 1:
                import time as time_module

                delay = 1.0 / replay_speed  # Speed is now "x" multiplier

                # Show playing indicator
                st.markdown(f"▶️ **Playing** at {replay_speed}x speed (advancing every {delay:.3f}s)")

                time_module.sleep(delay)
                st.session_state.replay_position += 1
                st.rerun()
            elif st.session_state.replay_playing and current_position >= total_days - 1:
                # Auto-stop at end
                st.session_state.replay_playing = False

        else:
            st.success("✅ Replay complete!")
            st.balloons()

            if st.button("🔄 Restart Replay", use_container_width=True):
                st.session_state.replay_position = 0
                st.session_state.replay_playing = False
                st.rerun()

        # Replay statistics
        with st.expander("📊 Replay Session Statistics"):
            st.markdown(
                f"""
                **Replay Configuration:**
                - Period: {replay_start.strftime("%Y-%m-%d")} to {replay_end.strftime("%Y-%m-%d")}
                - Total Days: {total_days}
                - Replay Speed: {replay_speed}x
                - Current Position: Day {current_position + 1} of {total_days}

                **Market Statistics:**
                - Start Price: ${replay_data["close"].iloc[0]:.2f}
                - End Price: ${replay_data["close"].iloc[-1]:.2f}
                - Total Return: {((replay_data["close"].iloc[-1] / replay_data["close"].iloc[0]) - 1) * 100:+.2f}%
                - Max Drawdown: {((replay_data["close"] / replay_data["close"].cummax() - 1).min() * 100):.2f}%
                """
            )

# =============================================================================
# Live Betti Curve Display
# =============================================================================

st.subheader("📈 Live Betti Curve Monitoring")

# Check if persistence diagrams have been computed
if st.session_state.persistence_diagrams is None:
    st.info(
        "📊 Persistence diagrams not yet computed. "
        "Go to 'Persistence Diagram Analysis' section and click 'Compute Persistence Diagrams' first."
    )
else:
    # Extract Betti numbers from persistence diagrams
    betti_numbers_data = []

    for idx, (diagram, date) in enumerate(zip(st.session_state.persistence_diagrams, st.session_state.window_dates)):
        # Count features by dimension (Betti numbers)
        beta_0 = np.sum(diagram[:, 2] == 0)  # Connected components
        beta_1 = np.sum(diagram[:, 2] == 1)  # Loops/cycles
        beta_2 = np.sum(diagram[:, 2] == 2)  # Voids

        betti_numbers_data.append(
            {
                "Date": date,
                "β₀ (Components)": beta_0,
                "β₁ (Loops)": beta_1,
                "β₂ (Voids)": beta_2,
            }
        )

    betti_df = pd.DataFrame(betti_numbers_data)

    # Store in session state for other components
    if "betti_curve_data" not in st.session_state:
        st.session_state.betti_curve_data = betti_df

    # Compute historical statistics
    beta_0_mean = betti_df["β₀ (Components)"].mean()
    beta_1_mean = betti_df["β₁ (Loops)"].mean()
    beta_2_mean = betti_df["β₂ (Voids)"].mean()

    beta_0_std = betti_df["β₀ (Components)"].std()
    beta_1_std = betti_df["β₁ (Loops)"].std()
    beta_2_std = betti_df["β₂ (Voids)"].std()

    # Get recent window size for display
    recent_window_size = st.slider(
        "Recent Windows to Display",
        min_value=10,
        max_value=min(200, len(betti_df)),
        value=min(50, len(betti_df)),
        help="Number of most recent windows to show in the chart",
    )

    # Filter to recent windows
    recent_betti_df = betti_df.tail(recent_window_size)

    # Current values (most recent window)
    current_beta_0 = recent_betti_df["β₀ (Components)"].iloc[-1]
    current_beta_1 = recent_betti_df["β₁ (Loops)"].iloc[-1]
    current_beta_2 = recent_betti_df["β₂ (Voids)"].iloc[-1]

    # Compute trends (comparing recent vs previous)
    if len(recent_betti_df) >= 2:
        prev_beta_0 = recent_betti_df["β₀ (Components)"].iloc[-2]
        prev_beta_1 = recent_betti_df["β₁ (Loops)"].iloc[-2]
        prev_beta_2 = recent_betti_df["β₂ (Voids)"].iloc[-2]

        trend_beta_0 = "↗" if current_beta_0 > prev_beta_0 else "↘" if current_beta_0 < prev_beta_0 else "→"
        trend_beta_1 = "↗" if current_beta_1 > prev_beta_1 else "↘" if current_beta_1 < prev_beta_1 else "→"
        trend_beta_2 = "↗" if current_beta_2 > prev_beta_2 else "↘" if current_beta_2 < prev_beta_2 else "→"
    else:
        trend_beta_0 = trend_beta_1 = trend_beta_2 = "→"

    # Display current Betti numbers with trends
    st.markdown("**Current Topological Features**")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "β₀ (Components)",
            f"{current_beta_0}",
            delta=f"{trend_beta_0} {current_beta_0 - beta_0_mean:.1f} from avg",
        )

    with col2:
        st.metric(
            "β₁ (Loops)",
            f"{current_beta_1}",
            delta=f"{trend_beta_1} {current_beta_1 - beta_1_mean:.1f} from avg",
        )

    with col3:
        st.metric(
            "β₂ (Voids)",
            f"{current_beta_2}",
            delta=f"{trend_beta_2} {current_beta_2 - beta_2_mean:.1f} from avg",
        )

    # Time-series plot with deviation bands
    st.markdown("**Betti Number Time Series**")

    fig_betti = go.Figure()

    # Add historical average lines (full dataset)
    fig_betti.add_hline(
        y=beta_0_mean,
        line_dash="dash",
        line_color="lightblue",
        opacity=0.5,
        annotation_text="β₀ avg",
        annotation_position="right",
    )
    fig_betti.add_hline(
        y=beta_1_mean,
        line_dash="dash",
        line_color="lightcoral",
        opacity=0.5,
        annotation_text="β₁ avg",
        annotation_position="right",
    )
    if beta_2_mean > 0:
        fig_betti.add_hline(
            y=beta_2_mean,
            line_dash="dash",
            line_color="lightgreen",
            opacity=0.5,
            annotation_text="β₂ avg",
            annotation_position="right",
        )

    # Add deviation bands (±1 standard deviation)
    # β₀ band
    fig_betti.add_trace(
        go.Scatter(
            x=list(recent_betti_df["Date"]) + list(recent_betti_df["Date"][::-1]),
            y=[beta_0_mean + beta_0_std] * len(recent_betti_df) + [beta_0_mean - beta_0_std] * len(recent_betti_df),
            fill="toself",
            fillcolor="rgba(173, 216, 230, 0.2)",
            line=dict(color="rgba(255,255,255,0)"),
            name="β₀ ±1σ",
            showlegend=True,
        )
    )

    # β₁ band
    fig_betti.add_trace(
        go.Scatter(
            x=list(recent_betti_df["Date"]) + list(recent_betti_df["Date"][::-1]),
            y=[beta_1_mean + beta_1_std] * len(recent_betti_df) + [beta_1_mean - beta_1_std] * len(recent_betti_df),
            fill="toself",
            fillcolor="rgba(240, 128, 128, 0.2)",
            line=dict(color="rgba(255,255,255,0)"),
            name="β₁ ±1σ",
            showlegend=True,
        )
    )

    # β₂ band (if non-zero)
    if beta_2_mean > 0:
        fig_betti.add_trace(
            go.Scatter(
                x=list(recent_betti_df["Date"]) + list(recent_betti_df["Date"][::-1]),
                y=[beta_2_mean + beta_2_std] * len(recent_betti_df) + [beta_2_mean - beta_2_std] * len(recent_betti_df),
                fill="toself",
                fillcolor="rgba(144, 238, 144, 0.2)",
                line=dict(color="rgba(255,255,255,0)"),
                name="β₂ ±1σ",
                showlegend=True,
            )
        )

    # Add Betti number lines
    fig_betti.add_trace(
        go.Scatter(
            x=recent_betti_df["Date"],
            y=recent_betti_df["β₀ (Components)"],
            mode="lines+markers",
            name="β₀ (Components)",
            line=dict(color="#636EFA", width=2),
            marker=dict(size=4),
        )
    )

    fig_betti.add_trace(
        go.Scatter(
            x=recent_betti_df["Date"],
            y=recent_betti_df["β₁ (Loops)"],
            mode="lines+markers",
            name="β₁ (Loops)",
            line=dict(color="#EF553B", width=2),
            marker=dict(size=4),
        )
    )

    fig_betti.add_trace(
        go.Scatter(
            x=recent_betti_df["Date"],
            y=recent_betti_df["β₂ (Voids)"],
            mode="lines+markers",
            name="β₂ (Voids)",
            line=dict(color="#00CC96", width=2),
            marker=dict(size=4),
        )
    )

    fig_betti.update_layout(
        title=f"Betti Numbers Over Time (Recent {recent_window_size} Windows)",
        xaxis_title="Date",
        yaxis_title="Betti Number Count",
        hovermode="x unified",
        height=500,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
    )

    st.plotly_chart(fig_betti, use_container_width=True)

    # Statistical summary table
    st.markdown("**Statistical Summary**")

    summary_data = {
        "Betti Number": ["β₀ (Components)", "β₁ (Loops)", "β₂ (Voids)"],
        "Current": [current_beta_0, current_beta_1, current_beta_2],
        "Mean (All)": [
            f"{beta_0_mean:.1f}",
            f"{beta_1_mean:.1f}",
            f"{beta_2_mean:.1f}",
        ],
        "Std Dev": [
            f"{beta_0_std:.1f}",
            f"{beta_1_std:.1f}",
            f"{beta_2_std:.1f}",
        ],
        "Z-Score": [
            f"{(current_beta_0 - beta_0_mean) / beta_0_std:.2f}" if beta_0_std > 0 else "N/A",
            f"{(current_beta_1 - beta_1_mean) / beta_1_std:.2f}" if beta_1_std > 0 else "N/A",
            f"{(current_beta_2 - beta_2_mean) / beta_2_std:.2f}" if beta_2_std > 0 else "N/A",
        ],
        "Trend": [trend_beta_0, trend_beta_1, trend_beta_2],
    }

    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # Interpretation guide
    with st.expander("📖 Interpretation Guide"):
        st.markdown(
            """
            **Betti Numbers and Market Regimes:**

            - **β₀ (Components)**: Number of connected components in the point cloud
              - Higher values → Market fragmentation, loss of correlation
              - Typical in crisis periods when asset correlations break down

            - **β₁ (Loops)**: Number of 1-dimensional holes (cycles)
              - Higher values → Complex circular dependencies, feedback loops
              - Indicates market instability and herding behavior
              - Most informative for crisis detection

            - **β₂ (Voids)**: Number of 2-dimensional voids
              - Higher values → High-dimensional market structure
              - Rare but significant when present

            **Trend Indicators:**
            - ↗ Increasing: Feature count growing (potential instability)
            - → Stable: No change from previous window
            - ↘ Decreasing: Feature count declining (stabilizing)

            **Z-Score Interpretation:**
            - |Z| < 1: Within normal range (±1σ)
            - 1 < |Z| < 2: Moderate deviation
            - |Z| > 2: Significant deviation (potential alert)
            - |Z| > 3: Extreme deviation (critical alert)
            """
        )

# =============================================================================
# Bottleneck Distance Monitoring
# =============================================================================

st.subheader("📏 Bottleneck Distance from Reference State")

# Check prerequisites
if st.session_state.persistence_diagrams is None:
    st.info(
        "📊 Persistence diagrams not yet computed. " "Compute them first in the 'Persistence Diagram Analysis' section."
    )
elif st.session_state.monitoring_reference_state is None:
    st.warning(
        "⚠️ No reference baseline selected. " "Configure reference state in sidebar to enable distance monitoring."
    )
else:
    # Import distance computation
    from financial_tda.models.change_point_detector import NormalPeriodCalibrator

    ref_state = st.session_state.monitoring_reference_state

    # Filter reference period diagrams
    ref_start = ref_state["start"]
    ref_end = ref_state["end"]

    # Get diagrams and dates
    all_diagrams = st.session_state.persistence_diagrams
    all_dates = st.session_state.window_dates

    # Strip timezone from reference dates and window dates for comparison
    if hasattr(ref_start, "tz") and ref_start.tz is not None:
        ref_start = ref_start.tz_localize(None)
    if hasattr(ref_end, "tz") and ref_end.tz is not None:
        ref_end = ref_end.tz_localize(None)

    # Ensure all_dates are timezone-naive
    all_dates_naive = []
    for date in all_dates:
        if hasattr(date, "tz") and date.tz is not None:
            all_dates_naive.append(date.tz_localize(None))
        else:
            all_dates_naive.append(date)

    # Filter reference period indices
    ref_mask = [(ref_start <= date <= ref_end) for date in all_dates_naive]
    ref_indices = [i for i, mask in enumerate(ref_mask) if mask]

    if len(ref_indices) < 2:
        st.error(
            f"Not enough windows in reference period ({len(ref_indices)} windows). "
            "Need at least 2 windows. Try selecting a longer reference period."
        )
    else:
        # Compute reference baseline (mean diagram of reference period)
        ref_diagrams = [all_diagrams[i] for i in ref_indices]

        # Use first reference diagram as baseline (can also use median or average)
        baseline_diagram = ref_diagrams[len(ref_diagrams) // 2]  # Middle of reference period

        # Compute bottleneck distances from baseline to all windows
        st.markdown("**Computing bottleneck distances from reference baseline...**")

        with st.spinner("Computing distances (this may take a moment)..."):
            # Use gudhi's bottleneck distance - handles variable-length diagrams correctly
            import gudhi

            # Compute distances for each window
            distances_from_baseline = []

            for diagram in all_diagrams:
                # Extract H1 features (loops) - most informative for crisis detection
                baseline_h1 = baseline_diagram[baseline_diagram[:, 2] == 1][:, :2]
                diagram_h1 = diagram[diagram[:, 2] == 1][:, :2]

                # Compute bottleneck distance using gudhi
                # gudhi expects diagrams as list of [birth, death] pairs
                if len(baseline_h1) > 0 and len(diagram_h1) > 0:
                    distance = gudhi.bottleneck_distance(baseline_h1.tolist(), diagram_h1.tolist())
                elif len(baseline_h1) == 0 and len(diagram_h1) == 0:
                    # Both empty - distance is 0
                    distance = 0.0
                else:
                    # One is empty - distance is max persistence of non-empty diagram
                    non_empty = baseline_h1 if len(baseline_h1) > 0 else diagram_h1
                    persistence_values = non_empty[:, 1] - non_empty[:, 0]
                    distance = np.max(persistence_values) / 2.0  # bottleneck to empty diagram

                distances_from_baseline.append(distance)

            distances_array = np.array(distances_from_baseline)

        # Calibrate on reference period distances
        ref_distances = distances_array[ref_indices]

        calibrator = NormalPeriodCalibrator()
        calibrator.fit(ref_distances)

        # Store in session state
        if "bottleneck_distances" not in st.session_state:
            st.session_state.bottleneck_distances = distances_array
        if "bottleneck_calibrator" not in st.session_state:
            st.session_state.bottleneck_calibrator = calibrator

        # Current distance (most recent window)
        current_distance = distances_array[-1]

        # Compute z-score
        z_score = (current_distance - calibrator.mean_) / calibrator.std_

        # Get threshold based on configured alert level
        threshold = calibrator.get_threshold(percentile=95.0 + (st.session_state.monitoring_alert_threshold - 2.0) * 2)

        # Determine alert status
        if z_score > st.session_state.monitoring_alert_threshold * 1.5:
            alert_status = "🔴 CRITICAL"
            alert_color = "red"
        elif z_score > st.session_state.monitoring_alert_threshold:
            alert_status = "🟡 WARNING"
            alert_color = "orange"
        else:
            alert_status = "🟢 NORMAL"
            alert_color = "green"

        # Display current status
        st.markdown("**Current Topological Deviation**")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Current Distance",
                f"{current_distance:.4f}",
            )

        with col2:
            st.metric(
                "Z-Score",
                f"{z_score:.2f}σ",
                delta=f"{z_score - 0:.2f}σ from baseline",
            )

        with col3:
            st.metric(
                "Alert Threshold",
                f"{threshold:.4f}",
            )

        with col4:
            st.markdown("**Status**")
            st.markdown(
                f"<h2 style='color: {alert_color};'>{alert_status}</h2>",
                unsafe_allow_html=True,
            )

        # Gauge visualization
        st.markdown("**Distance Gauge Visualization**")

        # Create gauge chart
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=current_distance,
                delta={"reference": calibrator.mean_, "increasing": {"color": "red"}},
                title={"text": "Bottleneck Distance from Reference"},
                domain={"x": [0, 1], "y": [0, 1]},
                gauge={
                    "axis": {
                        "range": [
                            None,
                            max(
                                calibrator.mean_ + 4 * calibrator.std_,
                                current_distance * 1.2,
                            ),
                        ]
                    },
                    "bar": {"color": alert_color},
                    "steps": [
                        {
                            "range": [0, calibrator.mean_ + calibrator.std_],
                            "color": "lightgreen",
                        },
                        {
                            "range": [calibrator.mean_ + calibrator.std_, threshold],
                            "color": "lightyellow",
                        },
                        {
                            "range": [
                                threshold,
                                calibrator.mean_ + 4 * calibrator.std_,
                            ],
                            "color": "lightcoral",
                        },
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": threshold,
                    },
                },
            )
        )

        fig_gauge.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
        )

        st.plotly_chart(fig_gauge, use_container_width=True)

        # Time series of distances
        st.markdown("**Distance Time Series**")

        # Filter to recent windows
        recent_window_size = min(100, len(distances_array))
        recent_distances = distances_array[-recent_window_size:]
        recent_dates = all_dates_naive[-recent_window_size:]

        fig_distance = go.Figure()

        # Add mean line
        fig_distance.add_hline(
            y=calibrator.mean_,
            line_dash="dash",
            line_color="blue",
            annotation_text="Baseline Mean",
            annotation_position="right",
        )

        # Add threshold line
        fig_distance.add_hline(
            y=threshold,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Alert Threshold ({st.session_state.monitoring_alert_threshold:.1f}σ)",
            annotation_position="right",
        )

        # Add ±1σ band
        fig_distance.add_trace(
            go.Scatter(
                x=list(recent_dates) + list(recent_dates[::-1]),
                y=[calibrator.mean_ + calibrator.std_] * len(recent_dates)
                + [calibrator.mean_ - calibrator.std_] * len(recent_dates),
                fill="toself",
                fillcolor="rgba(135, 206, 250, 0.2)",
                line=dict(color="rgba(255,255,255,0)"),
                name="±1σ Range",
                showlegend=True,
            )
        )

        # Add distance line
        fig_distance.add_trace(
            go.Scatter(
                x=recent_dates,
                y=recent_distances,
                mode="lines+markers",
                name="Bottleneck Distance",
                line=dict(color="#636EFA", width=2),
                marker=dict(size=4),
            )
        )

        # Highlight reference period
        if any(ref_mask[-recent_window_size:]):
            ref_dates_recent = [d for d, m in zip(recent_dates, ref_mask[-recent_window_size:]) if m]
            if ref_dates_recent:
                fig_distance.add_vrect(
                    x0=min(ref_dates_recent),
                    x1=max(ref_dates_recent),
                    fillcolor="lightblue",
                    opacity=0.2,
                    layer="below",
                    line_width=0,
                    annotation_text="Reference Period",
                    annotation_position="top left",
                )

        # Add alert markers on timeline
        warning_threshold = threshold
        critical_threshold = calibrator.mean_ + st.session_state.monitoring_alert_threshold * 1.5 * calibrator.std_

        # Find alert points
        warning_mask = recent_distances > warning_threshold
        critical_mask = recent_distances > critical_threshold

        # Add warning markers (yellow)
        warning_indices = np.where(warning_mask & ~critical_mask)[0]
        if len(warning_indices) > 0:
            fig_distance.add_trace(
                go.Scatter(
                    x=[recent_dates[i] for i in warning_indices],
                    y=[recent_distances[i] for i in warning_indices],
                    mode="markers",
                    name="⚠️ Warning",
                    marker=dict(
                        color="orange",
                        size=12,
                        symbol="triangle-up",
                        line=dict(width=2, color="darkorange"),
                    ),
                    hovertemplate="⚠️ Warning Alert<br>Date: %{x}<br>Distance: %{y:.4f}<extra></extra>",
                )
            )

        # Add critical markers (red)
        critical_indices = np.where(critical_mask)[0]
        if len(critical_indices) > 0:
            fig_distance.add_trace(
                go.Scatter(
                    x=[recent_dates[i] for i in critical_indices],
                    y=[recent_distances[i] for i in critical_indices],
                    mode="markers",
                    name="🔴 Critical",
                    marker=dict(
                        color="red",
                        size=14,
                        symbol="x",
                        line=dict(width=3, color="darkred"),
                    ),
                    hovertemplate="🔴 Critical Alert<br>Date: %{x}<br>Distance: %{y:.4f}<extra></extra>",
                )
            )

        fig_distance.update_layout(
            title="Bottleneck Distance Over Time",
            xaxis_title="Date",
            yaxis_title="Distance",
            hovermode="x unified",
            height=450,
            showlegend=True,
        )

        st.plotly_chart(fig_distance, use_container_width=True)

        # Alert Notification Panel
        st.markdown("**🔔 Recent Alert History**")

        # Collect all alerts from full dataset
        all_alerts = []
        for i, (date, distance) in enumerate(zip(all_dates_naive, distances_array)):
            z_score_i = (distance - calibrator.mean_) / calibrator.std_

            if distance > critical_threshold:
                all_alerts.append(
                    {
                        "Timestamp": date,
                        "Severity": "🔴 Critical",
                        "Distance": distance,
                        "Z-Score": z_score_i,
                        "Deviation": f"{((distance - calibrator.mean_) / calibrator.mean_) * 100:+.1f}%",
                    }
                )
            elif distance > warning_threshold:
                all_alerts.append(
                    {
                        "Timestamp": date,
                        "Severity": "🟡 Warning",
                        "Distance": distance,
                        "Z-Score": z_score_i,
                        "Deviation": f"{((distance - calibrator.mean_) / calibrator.mean_) * 100:+.1f}%",
                    }
                )

        # Store in session state
        st.session_state.monitoring_recent_alerts = all_alerts

        if len(all_alerts) > 0:
            # Show most recent 10 alerts
            recent_alerts_df = pd.DataFrame(all_alerts[-10:][::-1])  # Reverse for newest first
            recent_alerts_df["Timestamp"] = recent_alerts_df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M")
            recent_alerts_df["Distance"] = recent_alerts_df["Distance"].apply(lambda x: f"{x:.4f}")
            recent_alerts_df["Z-Score"] = recent_alerts_df["Z-Score"].apply(lambda x: f"{x:.2f}σ")

            # Color-code by severity
            def color_severity(row):
                if "Critical" in row["Severity"]:
                    return ["background-color: #ffcccc"] * len(row)
                else:
                    return ["background-color: #fff4cc"] * len(row)

            styled_df = recent_alerts_df.style.apply(color_severity, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            # Alert summary
            n_critical = sum(1 for a in all_alerts if "Critical" in a["Severity"])
            n_warning = sum(1 for a in all_alerts if "Warning" in a["Severity"])

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Alerts", len(all_alerts))
            with col2:
                st.metric("🟡 Warnings", n_warning)
            with col3:
                st.metric("🔴 Critical", n_critical)
        else:
            st.success("✅ No alerts detected. Market topology remains within normal range.")

        # Statistical summary
        st.markdown("**Statistical Summary**")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Reference Period Statistics**")
            stats_data = {
                "Metric": ["Mean", "Std Dev", "Min", "Max", "95th Percentile"],
                "Value": [
                    f"{calibrator.mean_:.4f}",
                    f"{calibrator.std_:.4f}",
                    f"{ref_distances.min():.4f}",
                    f"{ref_distances.max():.4f}",
                    f"{calibrator.get_threshold(95):.4f}",
                ],
            }
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**Current Window Analysis**")
            current_stats = {
                "Metric": [
                    "Current Distance",
                    "Z-Score",
                    "Percentile (vs ref)",
                    "Status",
                    "Deviation",
                ],
                "Value": [
                    f"{current_distance:.4f}",
                    f"{z_score:.2f}σ",
                    f"{(current_distance > ref_distances).mean() * 100:.1f}%",
                    alert_status,
                    f"{((current_distance - calibrator.mean_) / calibrator.mean_) * 100:+.1f}%",
                ],
            }
            st.dataframe(pd.DataFrame(current_stats), use_container_width=True, hide_index=True)

        # Interpretation
        with st.expander("📖 Bottleneck Distance Interpretation"):
            st.markdown(
                f"""
                **What is Bottleneck Distance?**

                The bottleneck distance measures the maximum difference between two persistence
                diagrams, representing the largest topological change required to transform
                one diagram into another.

                **Current Analysis:**
                - **Baseline**: Middle window of {ref_state["type"]} reference period
                  ({ref_start.strftime("%Y-%m-%d")} to {ref_end.strftime("%Y-%m-%d")})
                - **Reference Statistics**: {len(ref_indices)} windows, mean={
                    calibrator.mean_:.4f},
                  std={calibrator.std_:.4f}
                - **Current Z-Score**: {z_score:.2f}σ → {
                    "Within normal range"
                    if abs(z_score) < 1
                    else "Moderate deviation"
                    if abs(z_score) < 2
                    else "Significant deviation"
                    if abs(z_score) < 3
                    else "Extreme deviation"
                }

                **Alert Levels:**
                - 🟢 **Normal**: Z-score < {
                    st.session_state.monitoring_alert_threshold:.1f}σ
                - 🟡 **Warning**: {
                    st.session_state.monitoring_alert_threshold:.1f}σ ≤ Z-score < {
                    st.session_state.monitoring_alert_threshold * 1.5:.1f}σ
                - 🔴 **Critical**: Z-score ≥ {
                    st.session_state.monitoring_alert_threshold * 1.5:.1f}σ

                **Interpretation:**
                - **Low Distance** (near baseline): Market topology similar to normal periods
                - **High Distance** (above threshold): Significant topological shift, potential regime change
                - **Persistent High Distance**: Sustained crisis or new market regime
                """
            )

# =============================================================================
# Footer
# =============================================================================

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
    <p>Financial TDA Dashboard v1.0 | Powered by Streamlit & Topological Data Analysis</p>
    </div>
    """,
    unsafe_allow_html=True,
)
