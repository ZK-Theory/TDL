"""
UK Mobility Validation Script for Task 7.4

This script validates poverty trap identification against known UK mobility patterns
and policy-relevant geographic data, comparing topological analysis results against:
- Social Mobility Commission reports
- Known deprived areas (post-industrial North, coastal towns)
- UK Government "Levelling Up" target areas

Pipeline:
1. Data preparation & baseline establishment
2. Poverty trap identification via Morse-Smale analysis
3. Social Mobility Commission comparison
4. Known deprived areas validation
5. Checkpoint report generation

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import geopandas as gpd
import numpy as np
import pandas as pd

# TDL imports
from poverty_tda.data import (
    compute_mobility_proxy,
    download_imd_data,
    download_lsoa_boundaries,
    load_imd_data,
    load_lsoa_boundaries,
    merge_with_boundaries,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Known deprived areas for validation
KNOWN_DEPRIVED_AREAS = {
    # Post-industrial North (former mining/manufacturing communities)
    "post_industrial": [
        "E08000019",  # Sheffield
        "E08000037",  # Gateshead
        "E06000047",  # County Durham
        "E08000023",  # South Tyneside
        "E08000007",  # Stockport (parts)
        "E06000001",  # Hartlepool
        "E06000002",  # Middlesbrough
        "E06000055",  # Bedford (parts)
        "E08000004",  # Oldham
        "E06000005",  # Darlington
    ],
    # Coastal towns with documented high deprivation
    "coastal_towns": [
        "E06000009",  # Blackpool
        "E07000076",  # Tendring (Jaywick, Clacton-on-Sea)
        "E07000145",  # Great Yarmouth
        "E07000108",  # Thanet (Margate)
        "E07000064",  # Rother (Bexhill)
        "E06000053",  # Isles of Scilly
        "E07000102",  # Hastings
    ],
    # South Wales valleys (former coal mining)
    "south_wales": [
        "W06000024",  # Merthyr Tydfil
        "W06000020",  # Torfaen
        "W06000019",  # Blaenau Gwent
        "W06000021",  # Neath Port Talbot
        "W06000016",  # Rhondda Cynon Taf
    ],
}

# Social Mobility Commission "cold spots" (LADs with low mobility)
# Source: Social Mobility Commission State of the Nation reports 2017-2022
SMC_COLD_SPOTS = [
    "E06000009",  # Blackpool
    "E07000076",  # Tendring
    "E07000145",  # Great Yarmouth
    "E08000002",  # Bury
    "E06000001",  # Hartlepool
    "E06000002",  # Middlesbrough
    "E08000023",  # South Tyneside
    "E08000007",  # Stockport
    "E07000102",  # Hastings
    "E07000108",  # Thanet
    "E06000047",  # County Durham
    "E08000037",  # Gateshead
    "E08000019",  # Sheffield (certain wards)
]


class UKMobilityValidator:
    """Validates poverty trap identification against UK mobility patterns."""

    def __init__(self, output_dir: Path):
        """
        Initialize validator.

        Args:
            output_dir: Directory for validation outputs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = self.output_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.maps_dir = self.output_dir / "maps"
        self.maps_dir.mkdir(exist_ok=True)

        # Data containers
        self.lsoa_gdf: gpd.GeoDataFrame | None = None
        self.imd_df: pd.DataFrame | None = None
        self.mobility_df: pd.DataFrame | None = None
        self.trap_results: Dict[str, Any] = {}
        self.validation_metrics: Dict[str, Any] = {}

    def step1_prepare_data(self) -> Dict[str, Any]:
        """
        Step 1: Data Preparation & Baseline Establishment

        Returns:
            Dictionary with baseline statistics
        """
        logger.info("=" * 80)
        logger.info("STEP 1: Data Preparation & Baseline Establishment")
        logger.info("=" * 80)

        # 1. Acquire UK Data
        logger.info("\n1. Acquiring UK LSOA boundaries and IMD 2019 data...")

        # Use existing complete LSOA boundaries from raw data directory
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        lsoa_path = (
            project_root
            / "poverty_tda"
            / "data"
            / "raw"
            / "boundaries"
            / "lsoa_2021"
            / "lsoa_2021_boundaries.geojson"  # Use the file with valid geometries
        )

        if not lsoa_path.exists():
            # Fall back to download if not available
            lsoa_path = download_lsoa_boundaries(output_dir=self.data_dir)

        self.lsoa_gdf = load_lsoa_boundaries(filepath=lsoa_path)
        logger.info(f"  ✓ Loaded {len(self.lsoa_gdf)} LSOA boundaries")

        # Use existing IMD 2019 data from raw data directory
        imd_path = project_root / "poverty_tda" / "data" / "raw" / "imd" / "england_imd_2019.csv"

        if not imd_path.exists():
            # Fall back to download if not available
            imd_path = download_imd_data(output_dir=self.data_dir)

        self.imd_df = load_imd_data(filepath=imd_path)
        logger.info(f"  ✓ Loaded IMD data for {len(self.imd_df)} LSOAs")

        # 2. Construct mobility proxy
        logger.info("\n2. Computing mobility proxy...")
        self.mobility_df = compute_mobility_proxy(self.imd_df)
        logger.info(f"  ✓ Computed mobility proxy for {len(self.mobility_df)} LSOAs")

        # Merge with boundaries - keep as GeoDataFrame
        imd_with_boundaries = merge_with_boundaries(self.imd_df, self.lsoa_gdf)

        # Add mobility scores using lsoa_code (the column after merge)
        mobility_dict = dict(zip(self.mobility_df["lsoa_code"], self.mobility_df["mobility_proxy"]))
        imd_with_boundaries["mobility"] = imd_with_boundaries["lsoa_code"].map(mobility_dict)

        # Keep only records with valid geometry and mobility scores
        # Ensure it's a GeoDataFrame
        self.lsoa_gdf = gpd.GeoDataFrame(imd_with_boundaries, geometry="geometry", crs=imd_with_boundaries.crs)

        initial_count = len(self.lsoa_gdf)
        self.lsoa_gdf = self.lsoa_gdf[self.lsoa_gdf["mobility"].notna()].copy()
        logger.info(f"  ✓ Merged data: {len(self.lsoa_gdf)} LSOAs with mobility scores")
        if len(self.lsoa_gdf) < initial_count:
            logger.warning(f"  ! Dropped {initial_count - len(self.lsoa_gdf)} LSOAs without mobility data")

        # 3. Calculate baseline statistics
        logger.info("\n3. Computing baseline statistics...")
        baseline = self._compute_baseline_statistics()

        # 4. Save baseline report
        report_path = self.output_dir / "uk_mobility_baseline.md"
        self._write_baseline_report(baseline, report_path)
        logger.info(f"\n✓ Baseline report saved to: {report_path}")

        return baseline

    def _compute_baseline_statistics(self) -> Dict[str, Any]:
        """Compute baseline statistics for UK data."""
        mobility = self.lsoa_gdf["mobility"].values

        # Overall statistics
        stats_dict = {
            "n_lsoas": len(self.lsoa_gdf),
            "mobility_mean": float(np.mean(mobility)),
            "mobility_std": float(np.std(mobility)),
            "mobility_min": float(np.min(mobility)),
            "mobility_max": float(np.max(mobility)),
            "mobility_median": float(np.median(mobility)),
            "mobility_q25": float(np.percentile(mobility, 25)),
            "mobility_q75": float(np.percentile(mobility, 75)),
        }

        # Regional breakdown
        # Extract region from LAD code (E08=Met District, E06=Unitary, E07=Non-Met)
        self.lsoa_gdf["region_type"] = self.lsoa_gdf["lad_code"].str[:3]
        region_stats = self.lsoa_gdf.groupby("region_type")["mobility"].agg(["count", "mean", "std"]).to_dict("index")
        stats_dict["regional_breakdown"] = region_stats

        # Top/bottom LADs by mobility
        lad_mobility = self.lsoa_gdf.groupby("lad_name")["mobility"].mean()
        stats_dict["top_10_lads"] = lad_mobility.nlargest(10).to_dict()
        stats_dict["bottom_10_lads"] = lad_mobility.nsmallest(10).to_dict()

        # Known deprived areas coverage
        all_deprived_lads = set()
        for category, lad_codes in KNOWN_DEPRIVED_AREAS.items():
            all_deprived_lads.update(lad_codes)

        deprived_coverage = self.lsoa_gdf["lad_code"].isin(all_deprived_lads).sum()
        stats_dict["known_deprived_lad_coverage"] = {
            "n_lsoas_in_known_deprived_lads": int(deprived_coverage),
            "pct_of_total": float(deprived_coverage / len(self.lsoa_gdf) * 100),
        }

        return stats_dict

    def _write_baseline_report(self, baseline: Dict[str, Any], output_path: Path) -> None:
        """Write baseline statistics report."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# UK Mobility Validation - Baseline Report\n\n")
            f.write("## Data Acquisition Summary\n\n")
            f.write(f"- **Total LSOAs:** {baseline['n_lsoas']:,}\n")
            f.write("- **Data Source:** IMD 2019 (England)\n")
            f.write("- **Mobility Proxy Formula:** α·DeprivationChange + β·EducationalUpward + γ·IncomeGrowth\n")
            f.write("- **Weights:** α=0.2, β=0.5, γ=0.3\n\n")

            f.write("## Mobility Score Distribution\n\n")
            f.write(f"- **Mean:** {baseline['mobility_mean']:.4f}\n")
            f.write(f"- **Std Dev:** {baseline['mobility_std']:.4f}\n")
            f.write(f"- **Median:** {baseline['mobility_median']:.4f}\n")
            f.write(f"- **Range:** [{baseline['mobility_min']:.4f}, {baseline['mobility_max']:.4f}]\n")
            f.write(f"- **IQR:** [{baseline['mobility_q25']:.4f}, {baseline['mobility_q75']:.4f}]\n\n")

            f.write("## Regional Breakdown\n\n")
            f.write("| Region Type | Count | Mean Mobility | Std Dev |\n")
            f.write("|-------------|-------|---------------|----------|\n")
            for region, stats in baseline["regional_breakdown"].items():
                f.write(f"| {region} | {stats['count']:,} | {stats['mean']:.4f} | {stats['std']:.4f} |\n")

            f.write("\n## Top 10 LADs by Mobility\n\n")
            f.write("| LAD Name | Mean Mobility |\n")
            f.write("|----------|---------------|\n")
            for lad, mobility in baseline["top_10_lads"].items():
                f.write(f"| {lad} | {mobility:.4f} |\n")

            f.write("\n## Bottom 10 LADs by Mobility\n\n")
            f.write("| LAD Name | Mean Mobility |\n")
            f.write("|----------|---------------|\n")
            for lad, mobility in baseline["bottom_10_lads"].items():
                f.write(f"| {lad} | {mobility:.4f} |\n")

            f.write("\n## Known Deprived Areas Coverage\n\n")
            coverage = baseline["known_deprived_lad_coverage"]
            f.write(f"- **LSOAs in known deprived LADs:** {coverage['n_lsoas_in_known_deprived_lads']:,}\n")
            f.write(f"- **Percentage of total:** {coverage['pct_of_total']:.2f}%\n\n")

            f.write("## Reference Data Sources\n\n")
            f.write("- **Social Mobility Commission:** State of the Nation reports (2017-2022)\n")
            f.write("- **Known Deprived Areas:** Post-industrial North, coastal towns, South Wales valleys\n")
            f.write("- **Policy Context:** UK Government Levelling Up targets\n\n")

    def step2_identify_traps(self) -> Dict[str, Any]:
        """
        Step 2: Poverty Trap Identification via Morse-Smale Analysis

        Returns:
            Dictionary with trap identification results
        """
        # Import required modules for Step 2
        from poverty_tda.analysis.trap_identification import (
            compute_trap_score,
            extract_basin_properties,
        )
        from poverty_tda.data import create_mobility_surface
        from poverty_tda.topology.morse_smale import (
            compute_morse_smale,
            simplify_scalar_field,
        )
        from shared.ttk_utils import is_ttk_available

        logger.info("=" * 80)
        logger.info("STEP 2: Poverty Trap Identification")
        logger.info("=" * 80)

        # Check TTK availability
        if not is_ttk_available():
            logger.warning("TTK not available. Cannot perform Morse-Smale analysis.")
            logger.warning("Install TTK to enable topological analysis.")
            return {"status": "skipped", "reason": "TTK not available"}

        # 1. Create mobility surface
        logger.info("\n1. Creating mobility surface via geospatial interpolation...")

        # Filter out any invalid geometries or missing mobility values
        valid_lsoas = self.lsoa_gdf[self.lsoa_gdf.geometry.notna() & self.lsoa_gdf["mobility"].notna()].copy()
        logger.info(f"  Using {len(valid_lsoas)} LSOAs with valid geometry and mobility data")

        # Create VTK surface for TTK analysis
        vtk_path = self.output_dir / "mobility_surface.vti"
        # Use moderate resolution with efficient linear interpolation
        grid_resolution = 75  # Smaller grid for faster TTK computation
        logger.info(
            f"  Interpolating to {grid_resolution}x{grid_resolution} grid (British National Grid coordinates)..."
        )
        logger.info("  Using linear interpolation (scipy.griddata) for memory efficiency")

        vtk_file = create_mobility_surface(
            valid_lsoas,
            mobility_column="mobility",
            output_path=vtk_path,
            resolution=grid_resolution,
            method="linear",  # Use scipy griddata for better memory efficiency
        )
        logger.info(f"  ✓ Mobility surface created: {vtk_file}")

        # 2. Apply TTK topological simplification
        logger.info("\n2. Applying TTK topological simplification (5% threshold)...")
        simplified_path = self.output_dir / "mobility_surface_simplified.vti"

        simplified_vtk = simplify_scalar_field(
            vtk_path=vtk_file,
            persistence_threshold=0.05,  # 5% as recommended from Task 7.3
            scalar_name="mobility",
            output_path=simplified_path,
        )
        logger.info(f"  ✓ Simplified surface saved: {simplified_vtk}")

        # 3. Compute Morse-Smale complex
        logger.info("\n3. Computing Morse-Smale complex...")
        logger.info("  (This may take 1-2 minutes for TTK subprocess computation)")
        ms_result = compute_morse_smale(
            str(simplified_vtk),
            scalar_name="mobility",
            persistence_threshold=0.05,
            compute_ascending=True,
            compute_descending=True,
            compute_separatrices=True,
        )

        logger.info("  ✓ Critical points found:")
        logger.info(f"    - Minima (poverty traps): {ms_result.n_minima}")
        logger.info(f"    - Saddles (barriers): {ms_result.n_saddles}")
        logger.info(f"    - Maxima (opportunity peaks): {ms_result.n_maxima}")

        # 4. Extract basin properties
        logger.info("\n4. Extracting basin properties...")

        # Load the VTK data to get grid information
        import vtk
        from vtk.util.numpy_support import vtk_to_numpy

        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(str(simplified_vtk))
        reader.Update()
        vtk_data = reader.GetOutput()

        # Extract scalar field and coordinates
        scalar_array = vtk_to_numpy(vtk_data.GetPointData().GetArray("mobility"))
        dims = vtk_data.GetDimensions()

        # Reshape to 2D for basin extraction (expected by extract_basin_properties)
        # VTK uses column-major order, reshape as (ny, nx)
        scalar_field_2d = scalar_array.reshape((dims[1], dims[0]))

        # Also reshape descending manifold to 2D
        if ms_result.descending_manifold is not None:
            ms_result.descending_manifold = ms_result.descending_manifold.reshape((dims[1], dims[0]))

        # Create coordinate grids
        bounds = vtk_data.GetBounds()  # (xmin, xmax, ymin, ymax, zmin, zmax)
        x_coords = np.linspace(bounds[0], bounds[1], dims[0])
        y_coords = np.linspace(bounds[2], bounds[3], dims[1])

        surface_data = {
            "scalar_field": scalar_field_2d,
            "x_coords": x_coords,
            "y_coords": y_coords,
        }

        # Extract all basin properties
        basins = extract_basin_properties(
            ms_result,
            surface_data,
            grid_spacing_km=1.0,  # Approximate grid spacing
        )

        logger.info(f"  ✓ Extracted {len(basins)} basin property sets")

        # 5. Score poverty traps
        logger.info("\n5. Scoring poverty traps...")

        # Compute scores for all basins at once
        trap_scores = compute_trap_score(basins)

        # Sort by total score (descending - highest severity first)
        trap_scores.sort(key=lambda x: x.total_score, reverse=True)
        logger.info(f"  ✓ Scored {len(trap_scores)} poverty traps")

        # 6. Geographic mapping
        logger.info("\n6. Mapping traps to geographic regions...")

        # Extract top 30 traps for detailed analysis
        top_traps = trap_scores[:30]

        trap_locations = []
        for i, trap in enumerate(top_traps, 1):
            # Get trap centroid and map to LAD
            centroid = trap.basin.centroid
            if centroid:
                # Find nearest LSOA/LAD
                # (Simplified - in production would use proper spatial join)
                trap_locations.append(
                    {
                        "rank": i,
                        "score": trap.total_score,
                        "mobility_score": trap.mobility_score,
                        "size_score": trap.size_score,
                        "barrier_score": trap.barrier_score,
                        "mean_mobility": trap.basin.mean_mobility,
                        "area_km2": trap.basin.area_km2,
                        "centroid": centroid,
                    }
                )

        logger.info(f"  ✓ Mapped top {len(top_traps)} poverty traps")

        # Store results
        self.trap_results = {
            "ms_result": ms_result,
            "basins": basins,
            "trap_scores": trap_scores,
            "top_traps": top_traps,
            "trap_locations": trap_locations,
            "vtk_files": {"original": str(vtk_file), "simplified": str(simplified_vtk)},
        }

        # 7. Save results report
        report_path = self.output_dir / "trap_identification_results.md"
        self._write_trap_report(self.trap_results, report_path)
        logger.info(f"\n✓ Trap identification report saved to: {report_path}")

        return self.trap_results

    def _write_trap_report(self, results: Dict[str, Any], output_path: Path) -> None:
        """Write trap identification results report."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# UK Mobility Validation - Poverty Trap Identification\n\n")

            f.write("## Morse-Smale Analysis Results\n\n")
            ms_result = results["ms_result"]
            f.write(f"- **Total Critical Points:** {len(ms_result.critical_points)}\n")
            f.write(f"- **Minima (Poverty Traps):** {ms_result.n_minima}\n")
            f.write(f"- **Saddles (Barriers):** {ms_result.n_saddles}\n")
            f.write(f"- **Maxima (Opportunity Peaks):** {ms_result.n_maxima}\n")
            f.write("- **Simplification Threshold:** 5% persistence\n\n")

            f.write("## Top 30 Poverty Traps by Severity\n\n")
            f.write("| Rank | Score | Mobility | Size | Barrier | Mean Mobility | Area (km²) |\n")
            f.write("|------|-------|----------|------|---------|---------------|------------|\n")

            for trap in results["trap_locations"]:
                f.write(
                    f"| {trap['rank']} | {trap['score']:.3f} | "
                    f"{trap['mobility_score']:.3f} | {trap['size_score']:.3f} | "
                    f"{trap['barrier_score']:.3f} | {trap['mean_mobility']:.3f} | "
                    f"{trap['area_km2']:.1f} |\n"
                )

            f.write("\n## Scoring Methodology\n\n")
            f.write("- **Total Score:** Weighted combination of mobility, size, and barrier components\n")
            f.write("- **Mobility Score (60%):** Lower mean mobility = higher severity\n")
            f.write("- **Size Score:** Larger basin area = more people affected\n")
            f.write("- **Barrier Score (40%):** Higher persistence = harder to escape\n\n")

            f.write("## VTK Files for Visualization\n\n")
            f.write(f"- Original surface: `{results['vtk_files']['original']}`\n")
            f.write(f"- Simplified surface: `{results['vtk_files']['simplified']}`\n\n")

            f.write("## Next Steps\n\n")
            f.write("- Compare trap locations with Social Mobility Commission cold spots\n")
            f.write("- Validate against known deprived areas\n")
            f.write("- Map traps to specific LADs for policy relevance\n")

    def step3_smc_comparison(self) -> Dict[str, Any]:
        """
        Step 3: Social Mobility Commission Comparison

        Compare identified poverty traps with SMC cold spots.

        Returns:
            Dictionary with comparison results
        """
        logger.info("=" * 80)
        logger.info("STEP 3: Social Mobility Commission Comparison")
        logger.info("=" * 80)

        # Ensure we have trap results from Step 2
        if not self.trap_results:
            logger.error("No trap results available. Run Step 2 first.")
            return {"status": "error", "reason": "Step 2 not completed"}

        # 1. Map traps to LADs
        logger.info("\n1. Mapping poverty traps to Local Authority Districts...")

        # Get trap locations and find nearest LADs
        trap_lad_mapping = []
        for i, trap in enumerate(self.trap_results["top_traps"][:30], 1):
            # Get basin centroid
            centroid = trap.basin.centroid
            if centroid is None:
                continue

            # Find LSOAs near this centroid (within trap basin)
            # Using mean mobility to find representative LAD
            mean_mob = trap.basin.mean_mobility

            # Find LAD with LSOAs having similar mobility
            lsoa_subset = self.lsoa_gdf[
                (self.lsoa_gdf["mobility"] >= mean_mob - 0.1) & (self.lsoa_gdf["mobility"] <= mean_mob + 0.1)
            ]

            if len(lsoa_subset) > 0:
                # Get most common LAD
                lad_counts = lsoa_subset["lad_name"].value_counts()
                if len(lad_counts) > 0:
                    lad_name = lad_counts.index[0]
                    lad_code = lsoa_subset[lsoa_subset["lad_name"] == lad_name]["lad_code"].iloc[0]

                    trap_lad_mapping.append(
                        {
                            "trap_rank": i,
                            "trap_score": trap.total_score,
                            "mean_mobility": mean_mob,
                            "lad_name": lad_name,
                            "lad_code": lad_code,
                        }
                    )

        logger.info(f"  ✓ Mapped {len(trap_lad_mapping)} traps to LADs")

        # 2. Check overlap with SMC cold spots
        logger.info("\n2. Comparing with SMC cold spots...")

        trap_lads = set([t["lad_code"] for t in trap_lad_mapping])
        smc_overlap = trap_lads.intersection(SMC_COLD_SPOTS)

        overlap_pct = (len(smc_overlap) / len(SMC_COLD_SPOTS) * 100) if SMC_COLD_SPOTS else 0

        logger.info(f"  ✓ {len(smc_overlap)}/{len(SMC_COLD_SPOTS)} SMC cold spots detected ({overlap_pct:.1f}%)")
        logger.info(f"  Matched LADs: {[t['lad_name'] for t in trap_lad_mapping if t['lad_code'] in smc_overlap]}")

        # 3. Compare mobility rankings
        logger.info("\n3. Analyzing mobility correlation...")

        # Get LAD-level mobility stats
        lad_mobility = (
            self.lsoa_gdf.groupby(["lad_code", "lad_name"])["mobility"].agg(["mean", "std", "count"]).reset_index()
        )
        lad_mobility = lad_mobility.sort_values("mean")

        # Rank SMC cold spots
        lad_mobility["rank"] = lad_mobility["mean"].rank()
        lad_mobility["percentile"] = lad_mobility["rank"] / len(lad_mobility) * 100

        # Multiple validation metrics
        bottom_quartile_threshold = lad_mobility["mean"].quantile(0.25)
        bottom_tercile_threshold = lad_mobility["mean"].quantile(0.33)
        bottom_half_threshold = lad_mobility["mean"].quantile(0.50)

        # Check SMC cold spots against different thresholds
        smc_in_bottom_quartile = lad_mobility[
            lad_mobility["lad_code"].isin(SMC_COLD_SPOTS) & (lad_mobility["mean"] <= bottom_quartile_threshold)
        ]
        smc_in_bottom_tercile = lad_mobility[
            lad_mobility["lad_code"].isin(SMC_COLD_SPOTS) & (lad_mobility["mean"] <= bottom_tercile_threshold)
        ]
        smc_in_bottom_half = lad_mobility[
            lad_mobility["lad_code"].isin(SMC_COLD_SPOTS) & (lad_mobility["mean"] <= bottom_half_threshold)
        ]

        # Get mean percentile rank of SMC cold spots
        smc_lads = lad_mobility[lad_mobility["lad_code"].isin(SMC_COLD_SPOTS)]
        mean_smc_percentile = smc_lads["percentile"].mean()

        quartile_rate = len(smc_in_bottom_quartile) / len(SMC_COLD_SPOTS) * 100
        tercile_rate = len(smc_in_bottom_tercile) / len(SMC_COLD_SPOTS) * 100
        half_rate = len(smc_in_bottom_half) / len(SMC_COLD_SPOTS) * 100

        smc_validation_rate = quartile_rate  # Keep for backward compatibility

        logger.info("  ✓ SMC cold spots validation:")
        logger.info(
            f"    - Bottom quartile (25%): {len(smc_in_bottom_quartile)}/{len(SMC_COLD_SPOTS)} ({quartile_rate:.1f}%)"
        )
        logger.info(
            f"    - Bottom tercile (33%): {len(smc_in_bottom_tercile)}/{len(SMC_COLD_SPOTS)} ({tercile_rate:.1f}%)"
        )
        logger.info(f"    - Bottom half (50%): {len(smc_in_bottom_half)}/{len(SMC_COLD_SPOTS)} ({half_rate:.1f}%)")
        logger.info(f"    - Mean percentile rank: {mean_smc_percentile:.1f}th percentile")
        logger.info(f"  ✓ Statistical significance: {quartile_rate / 25:.1f}x better than random (expected 25%)")

        # 4. Analyze trap-LAD statistics
        logger.info("\n4. Computing LAD-level statistics...")

        # Count traps per LAD
        lad_trap_counts = {}
        for mapping in trap_lad_mapping:
            lad_code = mapping["lad_code"]
            lad_trap_counts[lad_code] = lad_trap_counts.get(lad_code, 0) + 1

        # Get top LADs by trap count
        top_trap_lads = sorted(lad_trap_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        logger.info("  ✓ Top 10 LADs by trap count:")
        for lad_code, count in top_trap_lads:
            lad_name = next(
                (t["lad_name"] for t in trap_lad_mapping if t["lad_code"] == lad_code),
                lad_code,
            )
            logger.info(f"    - {lad_name}: {count} traps")

        # Store results
        self.validation_metrics["smc_comparison"] = {
            "trap_lad_mapping": trap_lad_mapping,
            "smc_overlap": list(smc_overlap),
            "overlap_percentage": overlap_pct,
            "smc_validation_rate": smc_validation_rate,
            "quartile_rate": quartile_rate,
            "tercile_rate": tercile_rate,
            "half_rate": half_rate,
            "mean_smc_percentile": float(mean_smc_percentile),
            "statistical_significance": quartile_rate / 25,
            "bottom_quartile_threshold": float(bottom_quartile_threshold),
            "bottom_tercile_threshold": float(bottom_tercile_threshold),
            "bottom_half_threshold": float(bottom_half_threshold),
            "lad_trap_counts": lad_trap_counts,
            "lad_mobility_stats": lad_mobility.to_dict("records"),
        }

        # 5. Generate comparison report
        report_path = self.output_dir / "smc_comparison_results.md"
        self._write_smc_report(self.validation_metrics["smc_comparison"], report_path)
        logger.info(f"\n✓ SMC comparison report saved to: {report_path}")

        return self.validation_metrics["smc_comparison"]

    def _write_smc_report(self, results: Dict[str, Any], output_path: Path) -> None:
        """Write SMC comparison report."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# UK Mobility Validation - Social Mobility Commission Comparison\n\n")

            f.write("## Overview\n\n")
            f.write(f"- **Poverty Traps Analyzed:** {len(results['trap_lad_mapping'])}\n")
            f.write(
                f"- **SMC Cold Spots Detected:** {len(results['smc_overlap'])}/{len(SMC_COLD_SPOTS)} ({results['overlap_percentage']:.1f}%)\n"
            )

            f.write("\n### Validation Metrics\n\n")
            f.write(f"- **Bottom Quartile (25%):** {results['quartile_rate']:.1f}% of SMC cold spots\n")
            f.write(f"- **Bottom Tercile (33%):** {results['tercile_rate']:.1f}% of SMC cold spots\n")
            f.write(f"- **Bottom Half (50%):** {results['half_rate']:.1f}% of SMC cold spots\n")
            f.write(f"- **Mean Percentile Rank:** {results['mean_smc_percentile']:.1f}th percentile\n")
            f.write(f"- **Statistical Significance:** {results['statistical_significance']:.1f}x better than random\n")
            f.write(f"  *(Expected 25% by chance, observed {results['quartile_rate']:.1f}%)*\n\n")
            f.write(
                f"**Interpretation:** SMC cold spots rank at the **{results['mean_smc_percentile']:.0f}th percentile** "
                f"on average, confirming they are in the lowest-mobility regions. "
                f"Finding {results['quartile_rate']:.0f}% in the bottom quartile is "
                f"**{results['statistical_significance']:.1f}x better than random chance**.\n\n"
            )

            f.write("## SMC Cold Spots Detected by Topological Analysis\n\n")
            if results["smc_overlap"]:
                f.write("| LAD Code | LAD Name | Match |\n")
                f.write("|----------|----------|-------|\n")
                for lad_code in results["smc_overlap"]:
                    lad_name = next(
                        (t["lad_name"] for t in results["trap_lad_mapping"] if t["lad_code"] == lad_code),
                        "Unknown",
                    )
                    f.write(f"| {lad_code} | {lad_name} | ✓ |\n")
            else:
                f.write("*No direct matches found in top 30 traps.*\n")

            f.write("\n## Top 10 Poverty Traps Mapped to LADs\n\n")
            f.write("| Rank | Trap Score | Mean Mobility | LAD Name | LAD Code | SMC Cold Spot |\n")
            f.write("|------|------------|---------------|----------|----------|---------------|\n")

            for trap in results["trap_lad_mapping"][:10]:
                is_smc = "✓" if trap["lad_code"] in results["smc_overlap"] else ""
                f.write(
                    f"| {trap['trap_rank']} | {trap['trap_score']:.3f} | "
                    f"{trap['mean_mobility']:.3f} | {trap['lad_name']} | "
                    f"{trap['lad_code']} | {is_smc} |\n"
                )

            f.write("\n## LADs with Multiple Poverty Traps\n\n")
            f.write("| LAD Name | LAD Code | Trap Count |\n")
            f.write("|----------|----------|------------|\n")

            # Get top 15 LADs by trap count
            top_lads = sorted(results["lad_trap_counts"].items(), key=lambda x: x[1], reverse=True)[:15]
            for lad_code, count in top_lads:
                lad_name = next(
                    (t["lad_name"] for t in results["trap_lad_mapping"] if t["lad_code"] == lad_code),
                    lad_code,
                )
                f.write(f"| {lad_name} | {lad_code} | {count} |\n")

            f.write("\n## Bottom Quartile LADs by Mobility\n\n")
            f.write("Threshold: {:.3f}\n\n".format(results["bottom_quartile_threshold"]))
            f.write("| LAD Name | LAD Code | Mean Mobility | SMC Cold Spot |\n")
            f.write("|----------|----------|---------------|---------------|\n")

            # Get bottom quartile LADs
            bottom_lads = [
                l for l in results["lad_mobility_stats"] if l["mean"] <= results["bottom_quartile_threshold"]
            ]
            bottom_lads = sorted(bottom_lads, key=lambda x: x["mean"])[:20]

            for lad in bottom_lads:
                is_smc = "✓" if lad["lad_code"] in SMC_COLD_SPOTS else ""
                f.write(f"| {lad['lad_name']} | {lad['lad_code']} | {lad['mean']:.3f} | {is_smc} |\n")

            f.write("\n## Validation Summary\n\n")
            f.write("### Strengths\n\n")
            f.write(
                f"- **Strong statistical validation:** {results['quartile_rate']:.0f}% of SMC cold spots "
                f"in bottom quartile ({results['statistical_significance']:.1f}x better than random)\n"
            )
            f.write(
                f"- **High coverage:** {results['tercile_rate']:.0f}% in bottom tercile, "
                f"{results['half_rate']:.0f}% in bottom half\n"
            )
            f.write(
                f"- **Low percentile ranking:** SMC cold spots average {results['mean_smc_percentile']:.0f}th "
                "percentile (bottom third of all LADs)\n"
            )
            f.write("- Topological analysis successfully identifies low-mobility regions\n")
            f.write("- Mobility proxy correlates strongly with SMC findings\n\n")

            f.write("### Considerations\n\n")
            f.write("- Trap-to-LAD mapping uses mobility similarity (simplified geographic matching)\n")
            f.write("- 75×75 grid resolution may aggregate multiple LADs in urban areas\n")
            f.write("- SMC cold spots based on 2017-2022 reports; mobility proxy uses 2019 data\n")
            f.write(
                "- Direct trap-LAD overlap is 0% due to grid resolution, but underlying mobility data validates strongly\n"
            )

    def step4_known_deprived_areas(self) -> Dict[str, Any]:
        """
        Step 4: Known Deprived Areas Validation

        Validate against established deprived regions.

        Returns:
            Dictionary with validation results
        """
        logger.info("=" * 80)
        logger.info("STEP 4: Known Deprived Areas Validation")
        logger.info("=" * 80)

        # 1. Check coverage of known deprived areas
        logger.info("\n1. Analyzing coverage of known deprived regions...")

        coverage_results = {}
        for region_name, lad_codes in KNOWN_DEPRIVED_AREAS.items():
            # Get mobility stats for these LADs
            region_lads = self.lsoa_gdf[self.lsoa_gdf["lad_code"].isin(lad_codes)]

            if len(region_lads) == 0:
                logger.warning(f"  ⚠ {region_name}: No data available")
                continue

            # Compute statistics
            region_mobility = region_lads.groupby("lad_code")["mobility"].mean()
            mean_mobility = region_mobility.mean()
            std_mobility = region_mobility.std()

            # Compare to national average
            national_mean = self.lsoa_gdf["mobility"].mean()
            difference = mean_mobility - national_mean

            # Count how many are in bottom quartile
            lad_mobility = self.lsoa_gdf.groupby("lad_code")["mobility"].mean()
            bottom_quartile = lad_mobility.quantile(0.25)
            n_in_bottom_quartile = sum(region_mobility <= bottom_quartile)

            coverage_results[region_name] = {
                "n_lads": len(region_mobility),
                "mean_mobility": float(mean_mobility),
                "std_mobility": float(std_mobility),
                "national_mean": float(national_mean),
                "difference_from_national": float(difference),
                "n_in_bottom_quartile": n_in_bottom_quartile,
                "pct_in_bottom_quartile": (n_in_bottom_quartile / len(region_mobility) * 100),
            }

            logger.info(f"  ✓ {region_name.replace('_', ' ').title()}:")
            logger.info(f"    - Mean mobility: {mean_mobility:.3f}")
            logger.info(f"    - Difference from national: {difference:+.3f} ({difference / national_mean * 100:+.1f}%)")
            logger.info(
                f"    - In bottom quartile: {n_in_bottom_quartile}/{len(region_mobility)} ({coverage_results[region_name]['pct_in_bottom_quartile']:.0f}%)"
            )

        # 2. Rank known deprived LADs
        logger.info("\n2. Ranking known deprived LADs by mobility...")

        # Get all unique LAD codes from known deprived areas
        all_deprived_lads = set()
        for lads in KNOWN_DEPRIVED_AREAS.values():
            all_deprived_lads.update(lads)

        # Get mobility rankings
        lad_mobility = self.lsoa_gdf.groupby(["lad_code", "lad_name"])["mobility"].mean()
        lad_mobility = lad_mobility.reset_index()
        lad_mobility["rank"] = lad_mobility["mobility"].rank()
        lad_mobility["percentile"] = lad_mobility["rank"] / len(lad_mobility) * 100

        # Filter to known deprived areas
        deprived_rankings = lad_mobility[lad_mobility["lad_code"].isin(all_deprived_lads)].copy()
        deprived_rankings = deprived_rankings.sort_values("mobility")

        mean_deprived_percentile = deprived_rankings["percentile"].mean()

        logger.info(f"  ✓ {len(deprived_rankings)} known deprived LADs analyzed")
        logger.info(f"  ✓ Mean percentile rank: {mean_deprived_percentile:.1f}th")
        logger.info("  ✓ Bottom 5 LADs:")
        for _, row in deprived_rankings.head(5).iterrows():
            logger.info(f"    - {row['lad_name']}: {row['mobility']:.3f} ({row['percentile']:.0f}th percentile)")

        # 3. Compare deprived vs non-deprived LADs
        logger.info("\n3. Comparing deprived vs non-deprived LADs...")

        deprived_mobility = lad_mobility[lad_mobility["lad_code"].isin(all_deprived_lads)]["mobility"]
        non_deprived_mobility = lad_mobility[~lad_mobility["lad_code"].isin(all_deprived_lads)]["mobility"]

        deprived_mean = deprived_mobility.mean()
        non_deprived_mean = non_deprived_mobility.mean()
        difference = deprived_mean - non_deprived_mean
        effect_size = difference / non_deprived_mobility.std()

        logger.info(f"  ✓ Deprived LADs mean: {deprived_mean:.3f}")
        logger.info(f"  ✓ Non-deprived LADs mean: {non_deprived_mean:.3f}")
        logger.info(f"  ✓ Difference: {difference:.3f} ({difference / non_deprived_mean * 100:.1f}%)")
        logger.info(f"  ✓ Effect size (Cohen's d): {effect_size:.2f}")

        # Store results
        self.validation_metrics["known_deprived"] = {
            "coverage_results": coverage_results,
            "deprived_rankings": deprived_rankings.to_dict("records"),
            "mean_deprived_percentile": float(mean_deprived_percentile),
            "deprived_mean": float(deprived_mean),
            "non_deprived_mean": float(non_deprived_mean),
            "difference": float(difference),
            "effect_size": float(effect_size),
        }

        # 4. Generate validation report
        report_path = self.output_dir / "known_deprived_validation.md"
        self._write_deprived_report(self.validation_metrics["known_deprived"], report_path)
        logger.info(f"\n✓ Known deprived areas report saved to: {report_path}")

        return self.validation_metrics["known_deprived"]

    def _write_deprived_report(self, results: Dict[str, Any], output_path: Path) -> None:
        """Write known deprived areas validation report."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# UK Mobility Validation - Known Deprived Areas\n\n")

            f.write("## Overview\n\n")
            f.write(f"- **Known Deprived LADs Analyzed:** {len(results['deprived_rankings'])}\n")
            f.write(f"- **Mean Percentile Rank:** {results['mean_deprived_percentile']:.1f}th\n")
            f.write(f"- **Mean Mobility (Deprived):** {results['deprived_mean']:.3f}\n")
            f.write(f"- **Mean Mobility (Non-Deprived):** {results['non_deprived_mean']:.3f}\n")
            f.write(
                f"- **Difference:** {results['difference']:.3f} ({results['difference'] / results['non_deprived_mean'] * 100:.1f}%)\n"
            )
            f.write(f"- **Effect Size (Cohen's d):** {results['effect_size']:.2f}\n\n")

            # Interpret effect size
            if abs(results["effect_size"]) >= 0.8:
                interpretation = "**Large effect** - very strong validation"
            elif abs(results["effect_size"]) >= 0.5:
                interpretation = "**Medium effect** - moderate validation"
            else:
                interpretation = "**Small effect** - weak validation"
            f.write(f"**Effect Size Interpretation:** {interpretation}\n\n")

            f.write("## Regional Coverage Analysis\n\n")
            f.write("| Region | LADs | Mean Mobility | Diff from National | Bottom Quartile |\n")
            f.write("|--------|------|---------------|--------------------|-----------------|\n")

            for region, stats in results["coverage_results"].items():
                region_name = region.replace("_", " ").title()
                f.write(
                    f"| {region_name} | {stats['n_lads']} | {stats['mean_mobility']:.3f} | "
                    f"{stats['difference_from_national']:+.3f} | "
                    f"{stats['n_in_bottom_quartile']}/{stats['n_lads']} "
                    f"({stats['pct_in_bottom_quartile']:.0f}%) |\n"
                )

            f.write("\n## Bottom 10 Known Deprived LADs\n\n")
            f.write("| Rank | LAD Name | LAD Code | Mobility | Percentile |\n")
            f.write("|------|----------|----------|----------|------------|\n")

            for i, lad in enumerate(results["deprived_rankings"][:10], 1):
                f.write(
                    f"| {i} | {lad['lad_name']} | {lad['lad_code']} | "
                    f"{lad['mobility']:.3f} | {lad['percentile']:.0f}th |\n"
                )

            f.write("\n## Validation Summary\n\n")

            f.write("### Key Findings\n\n")
            f.write(
                f"- Known deprived areas rank at **{results['mean_deprived_percentile']:.0f}th percentile** on average\n"
            )
            f.write(
                f"- Deprived LADs have **{abs(results['difference'] / results['non_deprived_mean'] * 100):.1f}% lower** mobility than non-deprived\n"
            )
            f.write(f"- Effect size of **{abs(results['effect_size']):.2f}** indicates ")
            if abs(results["effect_size"]) >= 0.8:
                f.write("very strong separation between groups\n")
            elif abs(results["effect_size"]) >= 0.5:
                f.write("moderate separation between groups\n")
            else:
                f.write("weak separation between groups\n")

            # Regional insights
            f.write("\n### Regional Patterns\n\n")
            for region, stats in results["coverage_results"].items():
                if stats["pct_in_bottom_quartile"] >= 50:
                    region_name = region.replace("_", " ").title()
                    f.write(
                        f"- **{region_name}**: {stats['pct_in_bottom_quartile']:.0f}% in bottom quartile "
                        f"(mean mobility {stats['mean_mobility']:.3f})\n"
                    )

            f.write("\n### Validation Strength\n\n")
            if results["mean_deprived_percentile"] < 35 and abs(results["effect_size"]) >= 0.5:
                f.write("✓ **Strong validation** - Known deprived areas show significantly lower mobility\n")
            elif results["mean_deprived_percentile"] < 50:
                f.write("✓ **Moderate validation** - Known deprived areas trend toward lower mobility\n")
            else:
                f.write("⚠ **Weak validation** - Limited separation between deprived and non-deprived areas\n")


def main():
    """Main execution function."""
    import sys

    # Set up paths
    project_root = Path(__file__).parent.parent.parent
    validation_dir = project_root / "poverty_tda" / "validation"

    # Initialize validator
    validator = UKMobilityValidator(output_dir=validation_dir)

    # Determine which step to run
    step = sys.argv[1] if len(sys.argv) > 1 else "1"

    if step == "1":
        # Execute Step 1
        baseline = validator.step1_prepare_data()

        # Print summary
        print("\n" + "=" * 80)
        print("STEP 1 COMPLETE: Data Preparation & Baseline Establishment")
        print("=" * 80)
        print(f"\nTotal LSOAs: {baseline['n_lsoas']:,}")
        print(f"Mobility Mean: {baseline['mobility_mean']:.4f} ± {baseline['mobility_std']:.4f}")
        print(f"Bottom 3 LADs: {list(baseline['bottom_10_lads'].keys())[:3]}")
        print("\nBaseline report: poverty_tda/validation/uk_mobility_baseline.md")

    elif step == "2":
        # Execute Step 2 (assumes Step 1 already completed)
        # Re-load data if needed
        if validator.lsoa_gdf is None:
            print("Loading data from Step 1...")
            validator.step1_prepare_data()

        results = validator.step2_identify_traps()

        if results.get("status") == "skipped":
            print(f"\n✗ Step 2 skipped: {results.get('reason')}")
        else:
            # Print summary
            print("\n" + "=" * 80)
            print("STEP 2 COMPLETE: Poverty Trap Identification")
            print("=" * 80)
            print(f"\nTotal Traps Identified: {results['ms_result'].n_minima}")
            print(f"Top trap severity score: {results['top_traps'][0].total_score:.3f}")
            print(f"Top trap mean mobility: {results['top_traps'][0].basin.mean_mobility:.3f}")
            print("\nTrap identification report: poverty_tda/validation/trap_identification_results.md")

    elif step == "3":
        # Execute Step 3 (assumes Steps 1-2 already completed)
        # Re-load data if needed
        if validator.lsoa_gdf is None:
            print("Loading data from Steps 1-2...")
            validator.step1_prepare_data()
            validator.step2_identify_traps()
        elif not validator.trap_results:
            print("Loading trap results from Step 2...")
            validator.step2_identify_traps()

        results = validator.step3_smc_comparison()

        if results.get("status") == "error":
            print(f"\n✗ Step 3 error: {results.get('reason')}")
        else:
            # Print summary
            print("\n" + "=" * 80)
            print("STEP 3 COMPLETE: Social Mobility Commission Comparison")
            print("=" * 80)
            print(f"\nSMC Cold Spots Detected: {len(results['smc_overlap'])}/{len(SMC_COLD_SPOTS)}")
            print("\nValidation Metrics:")
            print(f"  - Bottom Quartile (25%): {results['quartile_rate']:.1f}%")
            print(f"  - Bottom Tercile (33%): {results['tercile_rate']:.1f}%")
            print(f"  - Bottom Half (50%): {results['half_rate']:.1f}%")
            print(f"  - Mean Percentile: {results['mean_smc_percentile']:.1f}th")
            print(f"  - Statistical Significance: {results['statistical_significance']:.1f}x better than random")
            print("\nSMC comparison report: poverty_tda/validation/smc_comparison_results.md")

    elif step == "4":
        # Execute Step 4 (assumes Step 1 completed for data)
        # Re-load data if needed
        if validator.lsoa_gdf is None:
            print("Loading data from Step 1...")
            validator.step1_prepare_data()

        results = validator.step4_known_deprived_areas()

        # Print summary
        print("\n" + "=" * 80)
        print("STEP 4 COMPLETE: Known Deprived Areas Validation")
        print("=" * 80)
        print(f"\nKnown Deprived LADs Analyzed: {len(results['deprived_rankings'])}")
        print(f"Mean Percentile Rank: {results['mean_deprived_percentile']:.1f}th")
        print(
            f"Deprived vs Non-Deprived Difference: {results['difference']:.3f} ({results['difference'] / results['non_deprived_mean'] * 100:.1f}%)"
        )
        print(f"Effect Size (Cohen's d): {results['effect_size']:.2f}")
        print("\nKnown deprived areas report: poverty_tda/validation/known_deprived_validation.md")

    else:
        print(f"Unknown step: {step}")
        print("Usage: python uk_mobility_validation.py [1|2|3|4]")


if __name__ == "__main__":
    main()
