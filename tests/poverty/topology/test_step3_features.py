"""
Test new Step 3 features: filter_by_persistence and simplify_first parameter.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import pyvista as pv

from poverty_tda.topology.morse_smale import (
    CriticalPoint,
    compute_morse_smale,
    filter_by_persistence,
)

# Check if pyvista is available
try:
    import pyvista as pv

    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False

# Check if TTK environment is available
from shared.ttk_utils import is_ttk_available

TTK_AVAILABLE = is_ttk_available()


@pytest.mark.skipif(not HAS_PYVISTA, reason="pyvista not available")
@pytest.mark.skipif(not TTK_AVAILABLE, reason="TTK environment not available")
class TestEnhancedExtraction:
    """Tests for enhanced critical point extraction features (Step 3)."""

    @pytest.fixture
    def noisy_gaussian_vtk(self) -> Path:
        """Create a noisy Gaussian surface VTK file."""
        n = 25
        grid = pv.ImageData(
            dimensions=(n, n, 1),
            spacing=(0.4, 0.4, 1.0),
            origin=(-5, -5, 0),
        )

        x = np.linspace(-5, 5, n)
        y = np.linspace(-5, 5, n)
        xx, yy = np.meshgrid(x, y)

        # Gaussian + significant noise
        zz = np.exp(-(xx**2 + yy**2) / 4) + 0.1 * np.random.randn(n, n)
        grid["mobility"] = zz.ravel()

        with tempfile.NamedTemporaryFile(suffix=".vti", delete=False) as tmp:
            path = Path(tmp.name)

        grid.save(str(path))
        yield path
        path.unlink(missing_ok=True)

    def test_simplify_first_parameter(self, noisy_gaussian_vtk: Path) -> None:
        """Test that simplify_first parameter works."""
        # Standard extraction
        result_standard = compute_morse_smale(
            noisy_gaussian_vtk,
            scalar_name="mobility",
            persistence_threshold=0.0,
            simplify_first=False,
        )

        # Enhanced extraction with pre-simplification
        result_enhanced = compute_morse_smale(
            noisy_gaussian_vtk,
            scalar_name="mobility",
            persistence_threshold=0.0,
            simplify_first=True,
            simplification_threshold=0.08,
        )

        # Check metadata
        assert "simplified" not in result_standard.metadata
        assert result_enhanced.metadata.get("simplified") is True
        assert result_enhanced.metadata.get("simplification_threshold") == 0.08

        # Both should return valid results
        assert len(result_standard.critical_points) > 0
        assert len(result_enhanced.critical_points) > 0

    def test_simplification_threshold_default(self, noisy_gaussian_vtk: Path) -> None:
        """Test that simplification_threshold defaults to persistence_threshold."""
        result = compute_morse_smale(
            noisy_gaussian_vtk,
            scalar_name="mobility",
            persistence_threshold=0.05,
            simplify_first=True,
            # simplification_threshold not specified
        )

        # Should use persistence_threshold
        assert result.metadata.get("simplification_threshold") == 0.05

    def test_filter_by_persistence_basic(self) -> None:
        """Test filter_by_persistence with mock critical points."""
        # Create mock critical points with persistence values
        points = [
            CriticalPoint(
                point_id=0,
                position=(0.0, 0.0, 0.0),
                value=0.1,
                point_type=0,
                persistence=0.05,  # 5% of range [0, 1]
            ),
            CriticalPoint(
                point_id=1,
                position=(1.0, 1.0, 0.0),
                value=0.9,
                point_type=2,
                persistence=0.15,  # 15% of range
            ),
            CriticalPoint(
                point_id=2,
                position=(0.5, 0.5, 0.0),
                value=0.5,
                point_type=1,
                persistence=0.02,  # 2% of range
            ),
        ]

        # Filter with 10% threshold
        filtered = filter_by_persistence(
            points,
            persistence_threshold=0.10,
            scalar_range=(0.0, 1.0),
        )

        # Should keep points with >= 10% persistence
        assert len(filtered) == 1
        assert filtered[0].point_id == 1
        assert filtered[0].persistence == 0.15

    def test_filter_by_persistence_none_values(self) -> None:
        """Test that points with persistence=None are always kept."""
        points = [
            CriticalPoint(
                point_id=0,
                position=(0.0, 0.0, 0.0),
                value=0.1,
                point_type=0,
                persistence=None,  # No persistence info
            ),
            CriticalPoint(
                point_id=1,
                position=(1.0, 1.0, 0.0),
                value=0.9,
                point_type=2,
                persistence=0.01,  # Below threshold
            ),
        ]

        filtered = filter_by_persistence(
            points,
            persistence_threshold=0.05,
            scalar_range=(0.0, 1.0),
        )

        # Should keep the None point, filter the low-persistence point
        assert len(filtered) == 1
        assert filtered[0].point_id == 0
        assert filtered[0].persistence is None

    def test_filter_by_persistence_invalid_threshold(self) -> None:
        """Test that invalid thresholds raise ValueError."""
        points = []

        with pytest.raises(ValueError, match="persistence_threshold must be in"):
            filter_by_persistence(points, persistence_threshold=1.5, scalar_range=(0.0, 1.0))

        with pytest.raises(ValueError, match="persistence_threshold must be in"):
            filter_by_persistence(points, persistence_threshold=-0.1, scalar_range=(0.0, 1.0))

    def test_simplify_first_invalid_threshold(self, noisy_gaussian_vtk: Path) -> None:
        """Test that invalid simplification_threshold raises ValueError."""
        with pytest.raises(ValueError, match="simplification_threshold must be in"):
            compute_morse_smale(
                noisy_gaussian_vtk,
                scalar_name="mobility",
                persistence_threshold=0.05,
                simplify_first=True,
                simplification_threshold=1.5,
            )
