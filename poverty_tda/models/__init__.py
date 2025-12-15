"""
Machine learning models for poverty trap prediction.

Uses lazy loading to prevent PyTorch initialization in Streamlit subprocess
until explicitly required.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from poverty_tda.models.opportunity_vae import OpportunityVAE
    from poverty_tda.models.spatial_gnn import SpatialGNN
    from poverty_tda.models.spatial_transformer import SpatialTransformer


def __getattr__(name: str):
    """Lazy load modules on first access to avoid PyTorch DLL conflicts."""
    if name == "OpportunityVAE":
        from poverty_tda.models.opportunity_vae import OpportunityVAE

        return OpportunityVAE
    elif name == "SpatialGNN":
        from poverty_tda.models.spatial_gnn import SpatialGNN

        return SpatialGNN
    elif name == "SpatialTransformer":
        from poverty_tda.models.spatial_transformer import SpatialTransformer

        return SpatialTransformer

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "OpportunityVAE",
    "SpatialGNN",
    "SpatialTransformer",
]
