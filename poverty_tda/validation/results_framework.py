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

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


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
            MethodResult(name=name, column=column, n_clusters=n_clusters, eta_squared=eta_squared, **kwargs)
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
        return sorted([(m.name, m.eta_squared, m.n_clusters) for m in self.methods], key=lambda x: x[1], reverse=True)


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
        lines.append(f"| {i} | {name} | {n} | {eta2:.4f} | {eta2*100:.1f}% {marker} |")

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

    def eta_squared(labels, values):
        groups = pd.DataFrame({"label": labels, "value": values})
        overall_mean = values.mean()
        ss_total = ((values - overall_mean) ** 2).sum()
        ss_between = sum(len(g) * (g["value"].mean() - overall_mean) ** 2 for _, g in groups.groupby("label"))
        return ss_between / ss_total if ss_total > 0 else 0

    for method_name, col in method_columns.items():
        labels = pd.Categorical(gdf[col]).codes
        n_clusters = gdf[col].nunique()
        eta2 = eta_squared(labels, outcome)

        result.add_method(
            name=method_name,
            column=col,
            n_clusters=n_clusters,
            eta_squared=eta2,
        )

    return result
