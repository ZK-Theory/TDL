"""Model persistence: save and load fitted sklearn objects.

Convention:
    .joblib files are saved alongside JSON checkpoints in the same directory.
    Example: results/trajectory_tda_integration/02_pca.joblib

Usage:
    from trajectory_tda.utils.model_io import save_model, load_model

    save_model(fitted_pca, checkpoint_dir / "02_pca.joblib")
    pca = load_model(checkpoint_dir / "02_pca.joblib")
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib

logger = logging.getLogger(__name__)


def save_model(model: object, path: str | Path) -> Path:
    """Persist a fitted model object using joblib.

    Args:
        model: Any picklable object (typically fitted sklearn estimator).
        path: Destination file path (should end in .joblib).

    Returns:
        The resolved Path where the model was saved.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    logger.info(f"Model saved: {path}")
    return path


def load_model(path: str | Path) -> object:
    """Load a previously saved model object.

    Args:
        path: Path to the .joblib file.

    Returns:
        The deserialised model object.

    Raises:
        FileNotFoundError: If the model file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    model = joblib.load(path)
    logger.info(f"Model loaded: {path}")
    return model
