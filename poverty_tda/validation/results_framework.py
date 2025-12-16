"""
Experimental Results Storage and Documentation Framework.

Standard format for storing comparison protocol results to ensure
reproducibility and consistent documentation across experiments.

Usage:
    from poverty_tda.validation.results_framework import (
        ExperimentResult, save_experiment, load_experiment
    )

    result = ExperimentResult(
        name="west_midlands_comparison",
        region="West Midlands",
        ...
    )
    save_experiment(result)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class MethodResult:
    """Results for a single method."""

    name: str
    column: str
    n_clusters: int
    eta_squared: float
    eta_squared_ci_lower: float | None = None
    eta_squared_ci_upper: float | None = None
    ari_vs_others: dict[str, float] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentResult:
    """Complete experiment result with metadata."""

    # Identification
    name: str
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Scope
    region: str = "England"
    n_observations: int = 0

    # Data sources
    data_sources: dict[str, str] = field(default_factory=dict)

    # Outcome variable
    outcome_variable: str = ""
    outcome_description: str = ""

    # Methods and results
    methods: list[MethodResult] = field(default_factory=list)

    # Agreement matrix
    ari_matrix: dict[str, dict[str, float]] = field(default_factory=dict)

    # Best performer
    best_method: str = ""
    best_eta_squared: float = 0.0

    # Files
    input_files: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)

    # Reproducibility
    random_seed: int | None = None
    git_commit: str | None = None

    # Notes
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Convert MethodResult list
        result["methods"] = [asdict(m) for m in self.methods]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentResult":
        """Create from dictionary."""
        methods = [MethodResult(**m) for m in data.pop("methods", [])]
        return cls(**data, methods=methods)

    def add_method(self, name: str, column: str, n_clusters: int, eta_squared: float, **kwargs) -> None:
        """Add a method result."""
        self.methods.append(
            MethodResult(
                name=name,
                column=column,
                n_clusters=n_clusters,
                eta_squared=eta_squared,
                **kwargs,
            )
        )

        # Update best if needed
        if eta_squared > self.best_eta_squared:
            self.best_method = name
            self.best_eta_squared = eta_squared

    def generate_id(self) -> str:
        """Generate unique experiment ID."""
        content = f"{self.name}_{self.region}_{self.timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def get_ranking(self) -> list[tuple[str, float, int]]:
        """Get methods ranked by eta_squared."""
        return sorted(
            [(m.name, m.eta_squared, m.n_clusters) for m in self.methods],
            key=lambda x: x[1],
            reverse=True,
        )


# =============================================================================
# STORAGE FUNCTIONS
# =============================================================================


RESULTS_DIR = Path(__file__).parent / "results"


def save_experiment(
    result: ExperimentResult,
    output_dir: Path | str | None = None,
) -> tuple[Path, Path]:
    """
    Save experiment result to JSON and Markdown.

    Args:
        result: ExperimentResult to save
        output_dir: Output directory (default: validation/results/)

    Returns:
        Tuple of (json_path, markdown_path)
    """
    output_dir = Path(output_dir) if output_dir else RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    exp_id = result.generate_id()
    base_name = f"{date_str}_{result.name}_{exp_id}"

    # Save JSON
    json_path = output_dir / f"{base_name}.json"
    with open(json_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)

    # Save Markdown summary
    md_path = output_dir / f"{base_name}.md"
    md_content = generate_markdown_report(result)
    md_path.write_text(md_content, encoding="utf-8")

    return json_path, md_path


def load_experiment(path: Path | str) -> ExperimentResult:
    """Load experiment result from JSON."""
    path = Path(path)
    with open(path) as f:
        data = json.load(f)
    return ExperimentResult.from_dict(data)


def list_experiments(results_dir: Path | str | None = None) -> list[Path]:
    """List all experiment JSON files."""
    results_dir = Path(results_dir) if results_dir else RESULTS_DIR
    return sorted(results_dir.glob("*.json"))


# =============================================================================
# REPORT GENERATION
# =============================================================================


def generate_markdown_report(result: ExperimentResult) -> str:
    """Generate Markdown report from experiment result."""
    lines = [
        f"# {result.name}",
        "",
        f"**Generated:** {result.timestamp}",
        f"**Region:** {result.region}",
        f"**Observations:** {result.n_observations:,}",
        "",
        "## Description",
        "",
        result.description,
        "",
        "## Data Sources",
        "",
    ]

    for name, source in result.data_sources.items():
        lines.append(f"- **{name}:** {source}")

    lines.extend(
        [
            "",
            "## Outcome Variable",
            "",
            f"**{result.outcome_variable}**: {result.outcome_description}",
            "",
            "## Results",
            "",
            "### Method Ranking (by η²)",
            "",
            "| Rank | Method | Clusters | η² | Variance Explained |",
            "|------|--------|----------|----|--------------------|",
        ]
    )

    for i, (name, eta2, n) in enumerate(result.get_ranking(), 1):
        marker = "🏆" if i == 1 else ""
        lines.append(f"| {i} | {name} | {n} | {eta2:.4f} | {eta2 * 100:.1f}% {marker} |")

    lines.extend(
        [
            "",
            "## Key Findings",
            "",
            f"**Best performing method:** {result.best_method} (η² = {result.best_eta_squared:.4f})",
            "",
        ]
    )

    if result.notes:
        lines.extend(["## Notes", ""])
        for note in result.notes:
            lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Reproducibility",
            "",
            f"- **Random Seed:** {result.random_seed or 'Not set'}",
            f"- **Git Commit:** {result.git_commit or 'Not recorded'}",
            "",
            "### Input Files",
            "",
        ]
    )

    for f in result.input_files:
        lines.append(f"- `{f}`")

    lines.extend(["", "### Output Files", ""])
    for f in result.output_files:
        lines.append(f"- `{f}`")

    return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def record_comparison_result(
    name: str,
    description: str,
    region: str,
    gdf,  # GeoDataFrame with results
    method_columns: dict[str, str],
    outcome_column: str,
    outcome_description: str = "",
    input_files: list[str] = None,
    output_files: list[str] = None,
    random_seed: int = None,
    notes: list[str] = None,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> ExperimentResult:
    """
    Convenience function to record a comparison experiment.

    Args:
        name: Experiment name
        description: Description of what was tested
        region: Geographic region
        gdf: GeoDataFrame with method assignments and outcome
        method_columns: Dict mapping method name to column name
        outcome_column: Column with outcome variable
        outcome_description: Description of outcome
        input_files: List of input file paths
        output_files: List of output file paths
        random_seed: Random seed used
        notes: Additional notes
        n_bootstrap: Number of bootstrap iterations for CIs
        confidence: Confidence level (default 0.95)

    Returns:
        Populated ExperimentResult
    """

    result = ExperimentResult(
        name=name,
        description=description,
        region=region,
        n_observations=len(gdf),
        outcome_variable=outcome_column,
        outcome_description=outcome_description,
        input_files=input_files or [],
        output_files=output_files or [],
        random_seed=random_seed,
        notes=notes or [],
    )

    # Compute η² for each method
    outcome = gdf[outcome_column].values

    def compute_eta_squared(labels, values):
        """Helper to compute eta squared efficiently."""
        # Handle case where labels might be filtered out (if any)
        if len(values) == 0:
            return 0.0

        # Convert to dataframe for easy grouping if not already efficient
        # But doing it with numpy is faster for bootstrap
        df = pd.DataFrame({"l": labels, "v": values})

        overall_mean = np.mean(values)
        ss_total = np.sum((values - overall_mean) ** 2)

        if ss_total == 0:
            return 0.0

        # SS Between
        group_means = df.groupby("l")["v"].mean()
        group_counts = df.groupby("l")["v"].count()

        ss_between = np.sum(group_counts * (group_means - overall_mean) ** 2)

        return ss_between / ss_total

    # Compute ARI between all method pairs
    try:
        # Build ARI matrix
        method_names = list(method_columns.keys())
        ari_scores = {}  # Store all pairwise ARIs

        for i, method1 in enumerate(method_names):
            for method2 in method_names[i + 1 :]:
                col1 = method_columns[method1]
                col2 = method_columns[method2]

                # Get labels as categorical codes
                labels1 = pd.Categorical(gdf[col1]).codes
                labels2 = pd.Categorical(gdf[col2]).codes

                # Compute ARI
                ari = adjusted_rand_score(labels1, labels2)

                # Store in matrix (both directions for easy lookup)
                pair_key = f"{method1} vs {method2}"
                ari_scores[pair_key] = ari

        result.ari_matrix = ari_scores

    except ImportError:
        # sklearn not available - skip ARI computation
        result.ari_matrix = {}

    # Add methods with their individual results
    rng = np.random.default_rng(random_seed if random_seed is not None else 42)

    for method_name, col in method_columns.items():
        labels = pd.Categorical(gdf[col]).codes
        n_clusters = gdf[col].nunique()

        # Point estimate
        eta2 = compute_eta_squared(labels, outcome)

        # Bootstrap CIs
        ci_lower, ci_upper = None, None
        if n_bootstrap > 0:
            boot_stats = []
            n_samples = len(outcome)

            for _ in range(n_bootstrap):
                # Resample indices
                indices = rng.integers(0, n_samples, n_samples)
                resampled_labels = labels[indices]
                resampled_outcome = outcome[indices]

                boot_eta = compute_eta_squared(resampled_labels, resampled_outcome)
                boot_stats.append(boot_eta)

            alpha = 1.0 - confidence
            ci_lower = np.percentile(boot_stats, alpha / 2 * 100)
            ci_upper = np.percentile(boot_stats, (1 - alpha / 2) * 100)

        # Compute ARI vs others for this method
        ari_vs_others = {}
        if result.ari_matrix:  # If ARI was computed
            for other_method in method_columns.keys():
                if other_method != method_name:
                    # Find the ARI score for this pair
                    pair1 = f"{method_name} vs {other_method}"
                    pair2 = f"{other_method} vs {method_name}"

                    if pair1 in result.ari_matrix:
                        ari_vs_others[other_method] = result.ari_matrix[pair1]
                    elif pair2 in result.ari_matrix:
                        ari_vs_others[other_method] = result.ari_matrix[pair2]

        result.add_method(
            name=method_name,
            column=col,
            n_clusters=n_clusters,
            eta_squared=eta2,
            eta_squared_ci_lower=ci_lower,
            eta_squared_ci_upper=ci_upper,
            ari_vs_others=ari_vs_others,
        )

    return result
