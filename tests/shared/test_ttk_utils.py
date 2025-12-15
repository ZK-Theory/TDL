"""
Tests for TTK availability detection and subprocess utilities.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.ttk_utils import (
    TTK_CONDA_PYTHON,
    check_ttk_status,
    get_ttk_backend,
    get_ttk_unavailable_message,
    get_ttk_version,
    is_ttk_available,
    is_ttk_paraview_available,
    run_ttk_subprocess,
)


class TestTTKAvailability:
    """Test TTK availability detection functions."""

    def test_is_ttk_available_real(self):
        """Test actual TTK availability on this system."""
        available = is_ttk_available()
        assert isinstance(available, bool)

        # If conda env exists, TTK should be available
        if Path(TTK_CONDA_PYTHON).exists():
            assert available, "TTK conda env exists but is_ttk_available() returns False"

    def test_is_ttk_available_missing_python(self):
        """Test behavior when TTK python doesn't exist."""
        with patch("shared.ttk_utils.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            available = is_ttk_available()
            assert available is False

    def test_is_ttk_available_import_fails(self):
        """Test behavior when TTK import fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            available = is_ttk_available()
            assert available is False

    def test_is_ttk_paraview_available_real(self):
        """Test actual TTK ParaView availability."""
        available = is_ttk_paraview_available()
        assert isinstance(available, bool)

        # Note: ParaView filters via paraview.simple require full ParaView GUI environment
        # TTK Python API (topologytoolkit module) works without ParaView
        # This is expected behavior for conda TTK installation

    def test_is_ttk_paraview_available_missing_python(self):
        """Test ParaView check when python doesn't exist."""
        with patch("shared.ttk_utils.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            available = is_ttk_paraview_available()
            assert available is False


class TestTTKVersion:
    """Test TTK version detection."""

    def test_get_ttk_version_real(self):
        """Test getting real TTK version."""
        version = get_ttk_version()

        if is_ttk_available():
            assert version is not None
            assert isinstance(version, str)
            # Version should look like "1.3.0" or similar
            assert len(version) > 0
        else:
            assert version is None

    def test_get_ttk_version_missing_python(self):
        """Test version check when python doesn't exist."""
        with patch("shared.ttk_utils.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            version = get_ttk_version()
            assert version is None

    def test_get_ttk_version_conda_fails(self):
        """Test version check when conda command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            version = get_ttk_version()
            assert version is None


class TestTTKBackend:
    """Test TTK backend detection."""

    def test_get_ttk_backend_structure(self):
        """Test backend info has correct structure."""
        backend = get_ttk_backend()

        assert isinstance(backend, dict)
        assert "available" in backend
        assert "backend" in backend
        assert "python_path" in backend
        assert "vtk_version" in backend
        assert "ttk_version" in backend
        assert "paraview_filters" in backend

    def test_get_ttk_backend_real(self):
        """Test real backend detection."""
        backend = get_ttk_backend()

        if is_ttk_available():
            assert backend["available"] is True
            assert backend["backend"] == "conda_subprocess"
            assert backend["python_path"] == TTK_CONDA_PYTHON
            assert backend["ttk_version"] is not None
            assert backend["vtk_version"] is not None
            assert isinstance(backend["paraview_filters"], bool)
        else:
            assert backend["available"] is False
            assert backend["backend"] == "none"
            assert backend["python_path"] is None

    def test_get_ttk_backend_unavailable(self):
        """Test backend info when TTK unavailable."""
        with patch("shared.ttk_utils.is_ttk_available", return_value=False):
            backend = get_ttk_backend()

            assert backend["available"] is False
            assert backend["backend"] == "none"


class TestTTKSubprocess:
    """Test TTK subprocess execution."""

    def test_run_ttk_subprocess_unavailable(self):
        """Test subprocess raises error when TTK unavailable."""
        with patch("shared.ttk_utils.is_ttk_available", return_value=False):
            with pytest.raises(RuntimeError, match="TTK conda environment not available"):
                run_ttk_subprocess("dummy.py")

    def test_run_ttk_subprocess_success(self):
        """Test successful subprocess execution."""
        if not is_ttk_available():
            pytest.skip("TTK not available on this system")

        # Create a simple test script
        test_script = Path(__file__).parent / "test_ttk_subprocess.py"
        test_script.write_text('print("TTK subprocess test")')

        try:
            code, stdout, stderr = run_ttk_subprocess(str(test_script), timeout=10)

            assert code == 0
            assert "TTK subprocess test" in stdout
            assert stderr == ""
        finally:
            if test_script.exists():
                test_script.unlink()

    def test_run_ttk_subprocess_with_args(self):
        """Test subprocess with command-line arguments."""
        if not is_ttk_available():
            pytest.skip("TTK not available on this system")

        # Create a test script that echoes arguments
        test_script = Path(__file__).parent / "test_ttk_args.py"
        test_script.write_text('import sys; print(" ".join(sys.argv[1:]))')

        try:
            code, stdout, stderr = run_ttk_subprocess(str(test_script), args=["arg1", "arg2", "arg3"], timeout=10)

            assert code == 0
            assert "arg1 arg2 arg3" in stdout
        finally:
            if test_script.exists():
                test_script.unlink()

    def test_run_ttk_subprocess_timeout(self):
        """Test subprocess timeout."""
        if not is_ttk_available():
            pytest.skip("TTK not available on this system")

        # Create a script that sleeps
        test_script = Path(__file__).parent / "test_ttk_timeout.py"
        test_script.write_text("import time; time.sleep(10)")

        try:
            with pytest.raises(subprocess.TimeoutExpired):
                run_ttk_subprocess(str(test_script), timeout=1)
        finally:
            if test_script.exists():
                test_script.unlink()

    def test_run_ttk_subprocess_error(self):
        """Test subprocess with non-zero exit code."""
        if not is_ttk_available():
            pytest.skip("TTK not available on this system")

        # Create a script that exits with error
        test_script = Path(__file__).parent / "test_ttk_error.py"
        test_script.write_text("import sys; sys.exit(1)")

        try:
            code, stdout, stderr = run_ttk_subprocess(str(test_script), timeout=10)

            assert code == 1
        finally:
            if test_script.exists():
                test_script.unlink()


class TestTTKMessages:
    """Test TTK user-facing messages."""

    def test_get_ttk_unavailable_message(self):
        """Test unavailable message is informative."""
        message = get_ttk_unavailable_message()

        assert isinstance(message, str)
        assert "conda create" in message
        assert "conda install" in message
        assert "topologytoolkit" in message
        assert TTK_CONDA_PYTHON in message

    def test_check_ttk_status_returns_backend(self):
        """Test check_ttk_status returns backend info."""
        status = check_ttk_status(verbose=False)

        assert isinstance(status, dict)
        assert "available" in status
        assert "backend" in status

    def test_check_ttk_status_verbose(self, capsys):
        """Test verbose status output."""
        check_ttk_status(verbose=True)

        captured = capsys.readouterr()
        assert "TTK Installation Status" in captured.out
        assert "TTK Status:" in captured.out


class TestTTKIntegration:
    """Integration tests for TTK functionality."""

    @pytest.mark.skipif(not is_ttk_available(), reason="TTK not available")
    def test_ttk_import_subprocess(self):
        """Test importing TTK in subprocess."""
        test_script = Path(__file__).parent / "test_ttk_import.py"
        test_script.write_text("import topologytoolkit; import vtk; " 'print(f"VTK: {vtk.vtkVersion.GetVTKVersion()}")')

        try:
            code, stdout, stderr = run_ttk_subprocess(str(test_script), timeout=10)

            assert code == 0
            assert "VTK:" in stdout
            assert stderr == ""
        finally:
            if test_script.exists():
                test_script.unlink()

    @pytest.mark.skipif(not is_ttk_paraview_available(), reason="TTK ParaView not available")
    def test_ttk_paraview_filters_subprocess(self):
        """Test importing TTK ParaView filters in subprocess."""
        test_script = Path(__file__).parent / "test_ttk_paraview.py"
        test_script.write_text(
            "from paraview.simple import TTKPersistenceDiagram, TTKBottleneckDistance; " 'print("Filters OK")'
        )

        try:
            code, stdout, stderr = run_ttk_subprocess(str(test_script), timeout=10)

            assert code == 0
            assert "Filters OK" in stdout
        finally:
            if test_script.exists():
                test_script.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
