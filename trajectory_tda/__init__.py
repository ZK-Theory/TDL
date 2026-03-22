"""Trajectory TDA — employment/income career trajectory analysis.

Applies persistent homology and related TDA methods to BHPS/UKHLS
panel data to study the topological structure of UK employment trajectories
and its relationship to social mobility.

Paper 1: Markov memory ladder — do observed trajectories exhibit more
topological complexity than Markov-1 null models predict?

Roadmap (see .apm/): Mapper (Paper 2), Zigzag (Paper 3),
cross-national comparison (Paper 5), geometric deep learning (Paper 7),
topological fairness (Paper 10).
"""
"""
Trajectory TDA: Topological analysis of life-course mobility trajectories.

Constructs Employment Status × Income Band state sequences from BHPS/USoc
longitudinal panel data, embeds them as point clouds, and uses persistent
homology to discover mobility regimes, poverty/unemployment cycles, and
group-level topological differences.
"""

__version__ = "0.1.0"
