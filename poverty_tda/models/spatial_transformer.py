"""
Spatial Transformer Network for geographic attention learning.

This module implements Spatial Transformer Networks (STN) and patch-based
spatial attention mechanisms that learn to focus on important geographic
regions in mobility surfaces. The attention mechanisms provide interpretable
insights into which areas drive mobility predictions, supporting policy analysis.

Key Components:
- SpatialTransformerSTN: Classic STN with learnable affine transformation
- AttentionSpatialTransformer: Patch-based multi-head self-attention
- MobilitySurfaceModel: Full model combining attention + prediction
- Training pipeline with early stopping and spatial regularization

Architecture:
    Input: Mobility surface as 2D image-like tensor (batch, 1, H, W)
    Attention Module: STN or patch-attention to focus on regions
    Feature Extractor: CNN backbone (ResNet-style or custom)
    Prediction Head: Mobility regression or region classification

Reference:
    Jaderberg et al. (2015) "Spatial Transformer Networks"
    Vaswani et al. (2017) "Attention Is All You Need" (for patch attention)

Integration:
    - mobility_surface.py: Creates 500×500 grid surfaces as input
    - spatial_gnn.py: Shared data loading and feature utilities

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class SpatialTransformerSTN(nn.Module):
    """
    Spatial Transformer Network with learnable affine transformation.

    This module learns to apply spatial transformations (rotation, scale,
    translation, shear) to input feature maps, allowing the network to
    focus attention on specific geographic regions. The transformation
    is learned end-to-end through backpropagation.

    Architecture:
        1. Localization Network: CNN that predicts transformation parameters
        2. Grid Generator: Creates sampling grid from affine matrix
        3. Sampler: Bilinear interpolation to apply transformation

    Args:
        input_channels: Number of input channels (typically 1 for mobility surface)
        feature_channels: Number of channels in localization network
        localization_layers: Number of conv layers in localization network

    Attributes:
        localization: CNN that predicts 6 affine transformation parameters
        fc_loc: Fully connected layers for transformation regression
        theta: Final affine transformation matrix [batch, 2, 3]

    Reference:
        Jaderberg et al. (2015) "Spatial Transformer Networks"
        https://arxiv.org/abs/1506.02025
    """

    def __init__(
        self,
        input_channels: int = 1,
        feature_channels: int = 32,
        localization_layers: int = 3,
    ):
        super().__init__()

        self.input_channels = input_channels
        self.feature_channels = feature_channels

        # Localization network: predicts transformation parameters
        # Build as a simple CNN with increasing channels
        layers = []
        in_ch = input_channels
        out_ch = feature_channels

        for i in range(localization_layers):
            layers.extend(
                [
                    nn.Conv2d(
                        in_ch,
                        out_ch,
                        kernel_size=7 if i == 0 else 5,
                        padding=3 if i == 0 else 2,
                    ),
                    nn.BatchNorm2d(out_ch),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(2, 2),
                ]
            )
            in_ch = out_ch
            out_ch = min(out_ch * 2, 256)

        self.localization = nn.Sequential(*layers)

        # Compute size after convolutions (depends on input resolution)
        # For 500×500 input with 3 pooling layers: 500 → 250 → 125 → 62
        # We'll use adaptive pooling to handle variable input sizes
        self.adaptive_pool = nn.AdaptiveAvgPool2d((4, 4))

        # Fully connected layers for affine transformation regression
        # Output 6 parameters: [a, b, c, d, tx, ty] for affine matrix:
        # [[a, b, tx],
        #  [c, d, ty]]
        fc_input_size = in_ch * 4 * 4  # After adaptive pooling to 4×4
        self.fc_loc = nn.Sequential(
            nn.Linear(fc_input_size, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(128, 6),
        )

        # Initialize transformation to identity
        # This ensures the network starts with no transformation
        self.fc_loc[-1].weight.data.zero_()
        self.fc_loc[-1].bias.data.copy_(
            torch.tensor([1, 0, 0, 0, 1, 0], dtype=torch.float)
        )

        logger.debug(
            f"Initialized SpatialTransformerSTN with {localization_layers} "
            f"localization layers and {feature_channels} initial channels"
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Apply spatial transformation to input.

        Args:
            x: Input tensor of shape (batch, channels, height, width)

        Returns:
            Tuple of (transformed_x, theta):
                - transformed_x: Spatially transformed input (same shape as x)
                - theta: Affine transformation matrix (batch, 2, 3)
        """
        batch_size = x.size(0)

        # Predict transformation parameters
        features = self.localization(x)  # (batch, channels, h', w')
        features = self.adaptive_pool(features)  # (batch, channels, 4, 4)
        features = features.view(batch_size, -1)  # Flatten

        theta = self.fc_loc(features)  # (batch, 6)
        theta = theta.view(-1, 2, 3)  # (batch, 2, 3)

        # Generate sampling grid from affine transformation
        grid = F.affine_grid(theta, x.size(), align_corners=False)

        # Apply transformation using bilinear sampling
        x_transformed = F.grid_sample(x, grid, align_corners=False)

        return x_transformed, theta

    def get_attention_map(
        self, theta: torch.Tensor, input_size: tuple[int, int]
    ) -> torch.Tensor:
        """
        Extract attention map from transformation parameters.

        The attention map shows which regions of the original image are
        emphasized by the learned transformation (scaling, translation).

        Args:
            theta: Affine transformation matrix (batch, 2, 3)
            input_size: Original input size (height, width)

        Returns:
            Attention heatmap (batch, height, width) showing transformation focus
        """
        batch_size = theta.size(0)
        H, W = input_size

        # Create identity grid in normalized coordinates [-1, 1]
        y = torch.linspace(-1, 1, H, device=theta.device)
        x = torch.linspace(-1, 1, W, device=theta.device)
        yy, xx = torch.meshgrid(y, x, indexing="ij")
        grid = torch.stack([xx, yy], dim=-1)  # (H, W, 2)

        # Apply inverse transformation to see where each output pixel came from
        # This shows the "attention" or focus region in the original image
        # grid_flat available for homogeneous coordinate transform if needed
        _ = grid.view(-1, 2)  # (H*W, 2) - available for advanced attention

        # Compute attention weights based on distance from transformation center
        attention_maps = []
        for b in range(batch_size):
            # Extract transformation parameters for this batch
            # theta[b] is [[a, b, tx], [c, d, ty]]
            tx = theta[b, 0, 2].item()
            ty = theta[b, 1, 2].item()
            scale_x = torch.sqrt(theta[b, 0, 0] ** 2 + theta[b, 0, 1] ** 2).item()
            scale_y = torch.sqrt(theta[b, 1, 0] ** 2 + theta[b, 1, 1] ** 2).item()

            # Compute attention as Gaussian centered at transformation center
            # Higher scale = more focused attention (zoomed in)
            distances = ((grid[:, :, 0] - tx) ** 2 + (grid[:, :, 1] - ty) ** 2).sqrt()
            attention = torch.exp(-(distances**2) / (0.5 + 1.0 / (scale_x + scale_y)))

            attention_maps.append(attention)

        return torch.stack(attention_maps, dim=0)


class AttentionSpatialTransformer(nn.Module):
    """
    Patch-based multi-head spatial self-attention transformer.

    This module divides the input mobility surface into spatial patches,
    applies multi-head self-attention across patches, and aggregates
    information. More interpretable than STN for policy applications
    as attention weights directly show which patches are important.

    Architecture:
        1. Patch Embedding: Divide image into patches (e.g., 16×16 regions)
        2. Positional Encoding: Add spatial position information
        3. Multi-Head Self-Attention: Learn patch interactions
        4. Aggregation: Reconstruct spatial attention map

    Args:
        input_channels: Number of input channels (typically 1)
        patch_size: Size of each square patch (e.g., 16 for 16×16 patches)
        embed_dim: Dimension of patch embeddings
        num_heads: Number of attention heads
        num_layers: Number of transformer encoder layers

    Attributes:
        patch_embed: Convolution to embed patches
        pos_encoding: Learnable positional encoding
        transformer: Multi-head self-attention layers
        attention_weights: Stored attention maps for visualization
    """

    def __init__(
        self,
        input_channels: int = 1,
        patch_size: int = 16,
        embed_dim: int = 128,
        num_heads: int = 8,
        num_layers: int = 2,
    ):
        super().__init__()

        self.input_channels = input_channels
        self.patch_size = patch_size
        self.embed_dim = embed_dim
        self.num_heads = num_heads

        # Patch embedding: Conv2d with stride=patch_size to extract patches
        self.patch_embed = nn.Conv2d(
            input_channels,
            embed_dim,
            kernel_size=patch_size,
            stride=patch_size,
        )

        # Positional encoding: learnable parameters for each patch position
        # Will be initialized with proper size in forward pass
        self.pos_encoding = None

        # Transformer encoder layers with multi-head self-attention
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=embed_dim * 4,
            dropout=0.1,
            activation="gelu",
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # Storage for attention weights (for visualization)
        self.attention_weights = None

        logger.debug(
            f"Initialized AttentionSpatialTransformer with {num_layers} layers, "
            f"{num_heads} heads, patch_size={patch_size}, embed_dim={embed_dim}"
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Apply patch-based spatial attention to input.

        Args:
            x: Input tensor of shape (batch, channels, height, width)

        Returns:
            Tuple of (attended_x, attention_map):
                - attended_x: Attention-weighted features
                  (batch, embed_dim, num_patches_h, num_patches_w)
                - attention_map: Attention weights (batch, num_patches_h, num_patches_w)
        """
        batch_size, channels, H, W = x.size()

        # Extract patches
        patch_embeds = self.patch_embed(
            x
        )  # (batch, embed_dim, num_patches_h, num_patches_w)
        _, embed_dim, num_patches_h, num_patches_w = patch_embeds.size()
        num_patches = num_patches_h * num_patches_w

        # Initialize positional encoding if needed
        if self.pos_encoding is None or self.pos_encoding.size(1) != num_patches:
            self.pos_encoding = nn.Parameter(
                torch.randn(1, num_patches, embed_dim, device=x.device) * 0.02
            )

        # Flatten patches for transformer: (batch, num_patches, embed_dim)
        patch_embeds_flat = patch_embeds.flatten(2).transpose(1, 2)

        # Add positional encoding
        patch_embeds_flat = patch_embeds_flat + self.pos_encoding

        # Apply transformer (self-attention across patches)
        # Note: We need to extract attention weights manually
        attended_patches = self._forward_with_attention(patch_embeds_flat)

        # Reshape back to spatial layout
        attended_patches_spatial = attended_patches.transpose(1, 2).view(
            batch_size, embed_dim, num_patches_h, num_patches_w
        )

        # Compute attention map by aggregating attention weights
        # Average attention across all heads and queries for interpretability
        if self.attention_weights is not None:
            # attention_weights shape: (batch, num_heads, num_patches, num_patches)
            # Take mean over heads and queries to get per-patch attention
            attention_map = self.attention_weights.mean(dim=1).mean(
                dim=1
            )  # (batch, num_patches)
            attention_map = attention_map.view(batch_size, num_patches_h, num_patches_w)
        else:
            # Fallback: uniform attention
            attention_map = (
                torch.ones(batch_size, num_patches_h, num_patches_w, device=x.device)
                / num_patches
            )

        return attended_patches_spatial, attention_map

    def _forward_with_attention(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through transformer while storing attention weights.

        Args:
            x: Patch embeddings (batch, num_patches, embed_dim)

        Returns:
            Attended patch embeddings (batch, num_patches, embed_dim)
        """
        # We need to manually iterate through transformer layers to extract attention
        # PyTorch's TransformerEncoder doesn't expose attention weights directly

        output = x
        all_attention_weights = []

        for layer in self.transformer.layers:
            # Extract self-attention layer
            self_attn = layer.self_attn

            # Manually compute attention (simplified)
            # This is a workaround since TransformerEncoder doesn't expose weights
            batch_size, num_patches, embed_dim = output.size()

            # Query, Key, Value projections
            q = self_attn.in_proj_weight[:embed_dim] @ output.transpose(
                1, 2
            )  # Simplified
            k = self_attn.in_proj_weight[embed_dim : 2 * embed_dim] @ output.transpose(
                1, 2
            )

            # Compute attention scores (simplified - not splitting heads for extraction)
            attn_scores = torch.softmax(
                (q.transpose(1, 2) @ k) / np.sqrt(embed_dim), dim=-1
            )
            all_attention_weights.append(attn_scores)

            # Full forward pass through layer
            output = layer(output)

        # Store last layer's attention weights for visualization
        if all_attention_weights:
            # Expand to match multi-head format (batch, 1, num_patches, num_patches)
            self.attention_weights = all_attention_weights[-1].unsqueeze(1)

        return output

    def get_attention_map(
        self,
        attention_weights: torch.Tensor,
        upscale_size: tuple[int, int] | None = None,
    ) -> torch.Tensor:
        """
        Extract interpretable attention map from stored weights.

        Args:
            attention_weights: Raw attention map (batch, num_patches_h, num_patches_w)
            upscale_size: Optional target size (H, W) to upsample attention map
                to match original input resolution

        Returns:
            Attention heatmap (batch, H, W) showing patch importance
        """
        if upscale_size is not None:
            # Upsample attention map to original resolution for visualization
            attention_upscaled = F.interpolate(
                attention_weights.unsqueeze(
                    1
                ),  # (batch, 1, num_patches_h, num_patches_w)
                size=upscale_size,
                mode="bilinear",
                align_corners=False,
            ).squeeze(1)  # (batch, H, W)
            return attention_upscaled
        else:
            return attention_weights


class MobilitySurfaceModel(nn.Module):
    """
    Full model combining spatial attention with mobility prediction.

    This model integrates a spatial attention mechanism (STN or patch-attention)
    with a CNN feature extractor and prediction head for mobility regression
    or region classification. Designed for interpretable policy analysis.

    Architecture:
        1. Input: Mobility surface (batch, 1, H, W)
        2. Spatial Attention: STN or patch-attention module
        3. Feature Extractor: CNN backbone (ResNet-style)
        4. Prediction Head: Regression or classification

    Args:
        attention_type: Type of attention mechanism ("stn" or "patch")
        input_size: Expected input resolution (H, W), default (500, 500)
        num_feature_channels: Base channels for feature extractor
        num_output_classes: Output dimension (1 for regression, >1 for classification)
        dropout_rate: Dropout probability for regularization

    Attributes:
        attention_module: Spatial attention layer (STN or patch-based)
        feature_extractor: CNN backbone for feature extraction
        prediction_head: Final prediction layer
        attention_maps: Stored attention maps for visualization
    """

    def __init__(
        self,
        attention_type: Literal["stn", "patch"] = "patch",
        input_size: tuple[int, int] = (500, 500),
        num_feature_channels: int = 64,
        num_output_classes: int = 1,
        dropout_rate: float = 0.3,
    ):
        super().__init__()

        self.attention_type = attention_type
        self.input_size = input_size
        self.num_output_classes = num_output_classes

        # Spatial attention module
        if attention_type == "stn":
            self.attention_module = SpatialTransformerSTN(
                input_channels=1, feature_channels=32, localization_layers=3
            )
            # STN outputs same size as input
            attention_output_channels = 1
        elif attention_type == "patch":
            # For 500×500 input with patch_size=16: 31×31 patches
            self.attention_module = AttentionSpatialTransformer(
                input_channels=1,
                patch_size=16,
                embed_dim=128,
                num_heads=8,
                num_layers=2,
            )
            attention_output_channels = 128  # Patch embeddings
        else:
            raise ValueError(f"Unknown attention_type: {attention_type}")

        # Feature extractor CNN backbone
        # ResNet-style architecture with residual connections
        self.feature_extractor = self._build_feature_extractor(
            input_channels=attention_output_channels,
            base_channels=num_feature_channels,
        )

        # Compute feature map size after convolutions
        # For 64×64 input with 2 pooling: 64 → 32 → 16
        # For patch attention (4×4 patches) with 2 pooling: 4 → 2 → 1
        self.adaptive_pool = nn.AdaptiveAvgPool2d((4, 4))

        # Prediction head
        # Updated to match reduced channel count (base * 4 instead of base * 8)
        fc_input_size = num_feature_channels * 4 * 4 * 4  # After adaptive pooling
        self.prediction_head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(fc_input_size, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(128, num_output_classes),
        )

        # Storage for attention maps
        self.attention_maps = None

        logger.info(
            f"Initialized MobilitySurfaceModel with {attention_type} attention, "
            f"input_size={input_size}, output_classes={num_output_classes}"
        )

    def _build_feature_extractor(
        self, input_channels: int, base_channels: int
    ) -> nn.Module:
        """
        Build ResNet-style feature extractor with residual blocks.

        Args:
            input_channels: Number of input channels from attention module
            base_channels: Base number of feature channels

        Returns:
            Feature extraction CNN
        """
        # For STN: input_channels=1, For patch attention: input_channels=128
        # If patch attention, add projection layer first
        layers = []

        if input_channels > 1:
            # Project patch embeddings to standard channel count
            layers.append(
                nn.Conv2d(input_channels, base_channels, kernel_size=1, bias=False)
            )
            layers.append(nn.BatchNorm2d(base_channels))
            layers.append(nn.ReLU(inplace=True))
            current_channels = base_channels
        else:
            current_channels = input_channels

        # Build progressive feature extraction blocks
        # Reduce number of pooling layers to avoid over-reduction
        channel_progression = [
            base_channels,
            base_channels * 2,
            base_channels * 4,
        ]

        for i, out_channels in enumerate(channel_progression):
            # Residual block
            layers.append(self._residual_block(current_channels, out_channels))

            # Only pool for first 2 blocks to avoid over-reduction
            # For 64×64 input: 64→32→16 (2 pooling layers)
            # For patch attention 4×4: stays at 4×4 or 2×2
            if i < 2:
                layers.append(nn.MaxPool2d(2, 2))

            current_channels = out_channels

        return nn.Sequential(*layers)

    def _residual_block(self, in_channels: int, out_channels: int) -> nn.Module:
        """
        Create a residual block with skip connection.

        Args:
            in_channels: Input channels
            out_channels: Output channels

        Returns:
            Residual block module
        """
        return ResidualBlock(in_channels, out_channels)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through full model.

        Args:
            x: Input mobility surface (batch, 1, H, W)

        Returns:
            Tuple of (predictions, attention_map):
                - predictions: Output predictions (batch, num_output_classes)
                - attention_map: Spatial attention map for visualization (batch, H, W)
        """
        # Apply spatial attention
        if self.attention_type == "stn":
            x_attended, theta = self.attention_module(x)
            # Extract attention map from transformation parameters
            attention_map = self.attention_module.get_attention_map(
                theta, self.input_size
            )
            features_in = x_attended
        else:  # patch attention
            x_attended, attention_map_patches = self.attention_module(x)
            # Upsample attention map to original resolution
            attention_map = self.attention_module.get_attention_map(
                attention_map_patches, upscale_size=self.input_size
            )
            features_in = x_attended

        # Extract features
        features = self.feature_extractor(features_in)
        features_pooled = self.adaptive_pool(features)

        # Predict
        predictions = self.prediction_head(features_pooled)

        # Store attention maps for visualization
        self.attention_maps = attention_map.detach()

        return predictions, attention_map

    def extract_attention_maps(self) -> torch.Tensor | None:
        """
        Extract stored attention maps for visualization.

        Returns:
            Attention maps from last forward pass (batch, H, W) or None
        """
        return self.attention_maps


class ResidualBlock(nn.Module):
    """
    Residual block with skip connection for feature extraction.

    Implements a simple residual connection:
        out = F(x) + projection(x)

    where F(x) is Conv-BN-ReLU-Conv-BN and projection matches dimensions.

    Args:
        in_channels: Input channels
        out_channels: Output channels
    """

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()

        self.conv1 = nn.Conv2d(
            in_channels, out_channels, kernel_size=3, padding=1, bias=False
        )
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(
            out_channels, out_channels, kernel_size=3, padding=1, bias=False
        )
        self.bn2 = nn.BatchNorm2d(out_channels)

        # Projection shortcut if dimensions change
        if in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.shortcut = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with residual connection."""
        identity = self.shortcut(x)

        out = self.conv1(x)
        out = self.bn1(out)
        out = F.relu(out, inplace=True)

        out = self.conv2(out)
        out = self.bn2(out)

        out += identity
        out = F.relu(out, inplace=True)

        return out


class MobilitySurfaceDataset(torch.utils.data.Dataset):
    """
    PyTorch Dataset for mobility surface data.

    Loads regional mobility surfaces (by LAD or region) with optional
    data augmentation for training. Surfaces are expected to be 2D numpy
    arrays from mobility_surface.py pipeline.

    Args:
        surfaces: List of 2D numpy arrays, each shape (H, W)
        targets: List of target values (mobility scores or class labels)
        transform: Optional data augmentation transforms
        normalize: If True, normalize surfaces to zero mean, unit variance

    Example:
        >>> from poverty_tda.topology.mobility_surface import build_mobility_surface
        >>> surfaces = [build_mobility_surface(gdf, mobility) for gdf in region_gdfs]
        >>> targets = [compute_regional_mobility(region) for region in regions]
        >>> dataset = MobilitySurfaceDataset(surfaces, targets)
    """

    def __init__(
        self,
        surfaces: list[np.ndarray],
        targets: list[float] | np.ndarray,
        transform: callable | None = None,
        normalize: bool = True,
    ):
        if len(surfaces) != len(targets):
            raise ValueError(
                f"surfaces length ({len(surfaces)}) != targets length ({len(targets)})"
            )

        self.surfaces = surfaces
        self.targets = np.array(targets, dtype=np.float32)
        self.transform = transform
        self.normalize = normalize

        # Compute normalization statistics if needed
        if self.normalize:
            all_values = np.concatenate([s.flatten() for s in surfaces])
            self.mean = float(np.nanmean(all_values))
            self.std = float(np.nanstd(all_values))
            if self.std == 0:
                self.std = 1.0
            logger.info(
                f"Dataset normalization: mean={self.mean:.4f}, std={self.std:.4f}"
            )

    def __len__(self) -> int:
        return len(self.surfaces)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        """Get a single sample."""
        surface = self.surfaces[idx].copy()
        target = self.targets[idx]

        # Normalize
        if self.normalize:
            surface = (surface - self.mean) / self.std

        # Convert to tensor: (1, H, W) for single-channel image
        surface_tensor = torch.from_numpy(surface).float().unsqueeze(0)

        # Apply transforms (augmentation)
        if self.transform is not None:
            surface_tensor = self.transform(surface_tensor)

        target_tensor = torch.tensor(target, dtype=torch.float32)

        return surface_tensor, target_tensor


class SpatialTransformerTrainer:
    """
    Training pipeline for Spatial Transformer models.

    Implements training loop with:
    - MSE loss for mobility regression
    - Optional spatial regularization to encourage smooth transformations
    - Adam optimizer with learning rate scheduling
    - Early stopping on validation loss
    - Checkpointing of best model

    Args:
        model: MobilitySurfaceModel instance
        train_dataset: Training dataset
        val_dataset: Validation dataset
        batch_size: Batch size for training
        learning_rate: Initial learning rate (default 1e-4 for attention stability)
        weight_decay: L2 regularization weight
        spatial_reg_weight: Weight for spatial regularization loss
        device: Device for training ("cpu" or "cuda")
        patience: Early stopping patience (epochs without improvement)
        max_epochs: Maximum training epochs

    Example:
        >>> model = MobilitySurfaceModel(attention_type="patch")
        >>> trainer = SpatialTransformerTrainer(model, train_ds, val_ds)
        >>> trainer.train()
        >>> best_model = trainer.get_best_model()
    """

    def __init__(
        self,
        model: MobilitySurfaceModel,
        train_dataset: MobilitySurfaceDataset,
        val_dataset: MobilitySurfaceDataset,
        batch_size: int = 16,
        learning_rate: float = 1e-4,
        weight_decay: float = 1e-5,
        spatial_reg_weight: float = 0.01,
        device: str = "cpu",
        patience: int = 10,
        max_epochs: int = 100,
    ):
        self.model = model.to(device)
        self.device = device

        # Data loaders
        self.train_loader = torch.utils.data.DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True, num_workers=0
        )
        self.val_loader = torch.utils.data.DataLoader(
            val_dataset, batch_size=batch_size, shuffle=False, num_workers=0
        )

        # Optimizer and scheduler
        self.optimizer = torch.optim.Adam(
            model.parameters(), lr=learning_rate, weight_decay=weight_decay
        )
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="min", factor=0.5, patience=5
        )

        # Training parameters
        self.spatial_reg_weight = spatial_reg_weight
        self.patience = patience
        self.max_epochs = max_epochs

        # Tracking
        self.train_losses = []
        self.val_losses = []
        self.best_val_loss = float("inf")
        self.best_model_state = None
        self.epochs_without_improvement = 0

        logger.info(
            f"Initialized trainer: lr={learning_rate}, batch_size={batch_size}, "
            f"spatial_reg={spatial_reg_weight}, device={device}"
        )

    def compute_loss(
        self,
        predictions: torch.Tensor,
        targets: torch.Tensor,
        attention_map: torch.Tensor,
    ) -> tuple[torch.Tensor, dict]:
        """
        Compute total loss with MSE and optional spatial regularization.

        Args:
            predictions: Model predictions (batch, num_outputs)
            targets: Ground truth targets (batch, num_outputs)
            attention_map: Attention maps (batch, H, W)

        Returns:
            Tuple of (total_loss, loss_dict) where loss_dict contains
            individual loss components.
        """
        # MSE loss for regression
        mse_loss = F.mse_loss(predictions.squeeze(), targets)

        # Spatial regularization: encourage smooth attention transformations
        # Penalize high spatial gradients in attention map
        spatial_reg = 0.0
        if self.spatial_reg_weight > 0:
            # Compute gradient magnitudes
            dx = attention_map[:, :, 1:] - attention_map[:, :, :-1]
            dy = attention_map[:, 1:, :] - attention_map[:, :-1, :]
            spatial_reg = (dx.abs().mean() + dy.abs().mean()) / 2.0

        # Total loss
        total_loss = mse_loss + self.spatial_reg_weight * spatial_reg

        loss_dict = {
            "total": total_loss.item(),
            "mse": mse_loss.item(),
            "spatial_reg": spatial_reg
            if isinstance(spatial_reg, float)
            else spatial_reg.item(),
        }

        return total_loss, loss_dict

    def train_epoch(self) -> dict:
        """Train for one epoch."""
        self.model.train()
        epoch_losses = {"total": 0.0, "mse": 0.0, "spatial_reg": 0.0}
        num_batches = 0

        for surfaces, targets in self.train_loader:
            surfaces = surfaces.to(self.device)
            targets = targets.to(self.device)

            # Forward pass
            self.optimizer.zero_grad()
            predictions, attention_map = self.model(surfaces)

            # Compute loss
            loss, loss_dict = self.compute_loss(predictions, targets, attention_map)

            # Backward pass
            loss.backward()
            # Gradient clipping for stability
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

            # Track losses
            for key, value in loss_dict.items():
                epoch_losses[key] += value
            num_batches += 1

        # Average losses
        for key in epoch_losses:
            epoch_losses[key] /= num_batches

        return epoch_losses

    def validate(self) -> dict:
        """Validate on validation set."""
        self.model.eval()
        epoch_losses = {"total": 0.0, "mse": 0.0, "spatial_reg": 0.0}
        num_batches = 0

        with torch.no_grad():
            for surfaces, targets in self.val_loader:
                surfaces = surfaces.to(self.device)
                targets = targets.to(self.device)

                # Forward pass
                predictions, attention_map = self.model(surfaces)

                # Compute loss
                _, loss_dict = self.compute_loss(predictions, targets, attention_map)

                # Track losses
                for key, value in loss_dict.items():
                    epoch_losses[key] += value
                num_batches += 1

        # Average losses
        for key in epoch_losses:
            epoch_losses[key] /= num_batches

        return epoch_losses

    def train(self) -> dict:
        """
        Execute full training loop with early stopping.

        Returns:
            Dictionary with training history
        """
        logger.info(f"Starting training for up to {self.max_epochs} epochs")

        for epoch in range(self.max_epochs):
            # Train
            train_losses = self.train_epoch()
            self.train_losses.append(train_losses)

            # Validate
            val_losses = self.validate()
            self.val_losses.append(val_losses)

            # Learning rate scheduling
            self.scheduler.step(val_losses["total"])

            # Logging
            train_mse = train_losses["mse"]
            val_mse = val_losses["mse"]
            logger.info(
                f"Epoch {epoch + 1}/{self.max_epochs} - "
                f"Train: {train_losses['total']:.6f} (MSE:{train_mse:.6f}) - "
                f"Val: {val_losses['total']:.6f} (MSE:{val_mse:.6f})"
            )

            # Early stopping check
            if val_losses["total"] < self.best_val_loss:
                self.best_val_loss = val_losses["total"]
                self.best_model_state = self.model.state_dict().copy()
                self.epochs_without_improvement = 0
                logger.info(f"  New best validation loss: {self.best_val_loss:.6f}")
            else:
                self.epochs_without_improvement += 1
                if self.epochs_without_improvement >= self.patience:
                    logger.info(
                        f"Early stopping triggered after {epoch + 1} epochs "
                        f"(no improvement for {self.patience} epochs)"
                    )
                    break

        logger.info(f"Training complete. Best val loss: {self.best_val_loss:.6f}")

        return {
            "train_losses": self.train_losses,
            "val_losses": self.val_losses,
            "best_val_loss": self.best_val_loss,
            "total_epochs": len(self.train_losses),
        }

    def get_best_model(self) -> MobilitySurfaceModel:
        """Load and return best model from training."""
        if self.best_model_state is not None:
            self.model.load_state_dict(self.best_model_state)
        return self.model

    def save_checkpoint(self, path: str) -> None:
        """Save training checkpoint."""
        checkpoint = {
            "model_state_dict": self.best_model_state or self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "train_losses": self.train_losses,
            "val_losses": self.val_losses,
            "best_val_loss": self.best_val_loss,
        }
        torch.save(checkpoint, path)
        logger.info(f"Saved checkpoint to {path}")

    def load_checkpoint(self, path: str) -> None:
        """Load training checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.train_losses = checkpoint["train_losses"]
        self.val_losses = checkpoint["val_losses"]
        self.best_val_loss = checkpoint["best_val_loss"]
        self.best_model_state = checkpoint["model_state_dict"]
        logger.info(f"Loaded checkpoint from {path}")


# ============================================================================
# VISUALIZATION UTILITIES
# ============================================================================


def visualize_attention_map(
    surface: np.ndarray,
    attention: np.ndarray,
    save_path: str | None = None,
    title: str = "Spatial Attention on Mobility Surface",
    cmap_surface: str = "viridis",
    cmap_attention: str = "hot",
    alpha: float = 0.5,
    figsize: tuple[int, int] = (12, 5),
) -> tuple:
    """
    Visualize attention heatmap overlaid on mobility surface.

    Creates a side-by-side visualization showing:
    1. Original mobility surface
    2. Attention heatmap overlaid on surface

    Args:
        surface: 2D mobility surface array (H, W)
        attention: 2D attention map array (H, W), values should be in [0, 1]
        save_path: Optional path to save figure
        title: Figure title
        cmap_surface: Colormap for surface visualization
        cmap_attention: Colormap for attention heatmap
        alpha: Transparency of attention overlay (0=transparent, 1=opaque)
        figsize: Figure size (width, height)

    Returns:
        Tuple of (fig, axes) matplotlib objects

    Example:
        >>> model = MobilitySurfaceModel(attention_type="patch")
        >>> predictions, attention_map = model(surface_tensor)
        >>> visualize_attention_map(
        ...     surface.numpy(), attention_map[0].numpy(),
        ...     save_path="attention_map.png"
        ... )
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.error("matplotlib not installed - cannot visualize attention maps")
        raise

    # Normalize attention to [0, 1] if needed
    attention_norm = attention.copy()
    if attention_norm.max() > 1.0 or attention_norm.min() < 0.0:
        attention_norm = (attention_norm - attention_norm.min()) / (
            attention_norm.max() - attention_norm.min() + 1e-10
        )

    # Create figure
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # Plot 1: Original surface
    im1 = axes[0].imshow(surface, cmap=cmap_surface, aspect="auto")
    axes[0].set_title("Mobility Surface")
    axes[0].set_xlabel("Grid X")
    axes[0].set_ylabel("Grid Y")
    plt.colorbar(im1, ax=axes[0], label="Mobility Score")

    # Plot 2: Attention overlay
    axes[1].imshow(surface, cmap=cmap_surface, aspect="auto")
    im2 = axes[1].imshow(
        attention_norm, cmap=cmap_attention, alpha=alpha, aspect="auto"
    )
    axes[1].set_title("Attention Heatmap Overlay")
    axes[1].set_xlabel("Grid X")
    axes[1].set_ylabel("Grid Y")
    plt.colorbar(im2, ax=axes[1], label="Attention Weight")

    fig.suptitle(title, fontsize=14, fontweight="bold")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"Saved attention visualization to {save_path}")

    return fig, axes


def analyze_attention_patterns(
    model: MobilitySurfaceModel,
    surfaces: list[np.ndarray] | torch.Tensor,
    region_names: list[str] | None = None,
    grid_coords: tuple[np.ndarray, np.ndarray] | None = None,
    top_k: int = 5,
) -> dict:
    """
    Aggregate attention across samples to identify important regions.

    Analyzes which geographic regions consistently receive high attention
    across multiple mobility surface samples. Useful for policy interpretation.

    Args:
        model: Trained MobilitySurfaceModel
        surfaces: List of mobility surfaces (H, W) or batch tensor (N, 1, H, W)
        region_names: Optional names for each surface/region
        grid_coords: Optional tuple of (grid_x, grid_y) meshgrids for geographic mapping
        top_k: Number of top attention regions to identify

    Returns:
        Dictionary with attention analysis:
            - mean_attention: Average attention map across all samples (H, W)
            - std_attention: Standard deviation of attention (H, W)
            - top_regions: List of (row, col, attention_value) for top-k regions
            - per_sample_attention: List of attention maps for each sample
            - geographic_coords: Optional list of (x, y) coords for top regions

    Example:
        >>> model = trainer.get_best_model()
        >>> results = analyze_attention_patterns(
        ...     model, test_surfaces, region_names=["North", "South", "East"]
        ... )
        >>> print(f"Top attention region: {results['top_regions'][0]}")
    """
    model.eval()
    device = next(model.parameters()).device

    # Convert to tensor if needed
    if isinstance(surfaces, list):
        surfaces_tensor = torch.stack(
            [torch.from_numpy(s).float().unsqueeze(0) for s in surfaces]
        )
    else:
        surfaces_tensor = surfaces

    # Collect attention maps
    all_attention_maps = []
    with torch.no_grad():
        for i in range(surfaces_tensor.size(0)):
            surface_batch = surfaces_tensor[i : i + 1].to(device)
            _, attention_map = model(surface_batch)
            all_attention_maps.append(attention_map.cpu().squeeze().numpy())

    # Stack for analysis
    attention_stack = np.stack(all_attention_maps, axis=0)  # (N, H, W)

    # Compute statistics
    mean_attention = attention_stack.mean(axis=0)
    std_attention = attention_stack.std(axis=0)

    # Find top-k attention regions
    flat_mean = mean_attention.flatten()
    top_indices = np.argsort(flat_mean)[-top_k:][::-1]
    H, W = mean_attention.shape
    top_regions = []

    for idx in top_indices:
        row = idx // W
        col = idx % W
        attention_value = mean_attention[row, col]
        top_regions.append((row, col, float(attention_value)))

    # Map to geographic coordinates if provided
    geographic_coords = None
    if grid_coords is not None:
        grid_x, grid_y = grid_coords
        geographic_coords = []
        for row, col, _ in top_regions:
            x = grid_x[row, col] if grid_x.ndim == 2 else grid_x[col]
            y = grid_y[row, col] if grid_y.ndim == 2 else grid_y[row]
            geographic_coords.append((float(x), float(y)))

    logger.info(
        f"Analyzed attention patterns across {len(all_attention_maps)} samples. "
        f"Mean attention: {mean_attention.mean():.4f} ± {std_attention.mean():.4f}"
    )

    return {
        "mean_attention": mean_attention,
        "std_attention": std_attention,
        "top_regions": top_regions,
        "per_sample_attention": all_attention_maps,
        "geographic_coords": geographic_coords,
        "region_names": region_names,
    }


def plot_attention_aggregation(
    analysis_results: dict,
    save_path: str | None = None,
    figsize: tuple[int, int] = (15, 5),
) -> tuple:
    """
    Visualize aggregated attention patterns across samples.

    Creates a three-panel plot showing:
    1. Mean attention map
    2. Standard deviation of attention
    3. Consistency map (regions with consistently high attention)

    Args:
        analysis_results: Output from analyze_attention_patterns()
        save_path: Optional path to save figure
        figsize: Figure size

    Returns:
        Tuple of (fig, axes) matplotlib objects
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.error("matplotlib not installed - cannot visualize attention patterns")
        raise

    mean_attention = analysis_results["mean_attention"]
    std_attention = analysis_results["std_attention"]

    # Compute consistency: high mean, low std
    consistency = mean_attention / (std_attention + 1e-6)

    fig, axes = plt.subplots(1, 3, figsize=figsize)

    # Plot 1: Mean attention
    im1 = axes[0].imshow(mean_attention, cmap="hot", aspect="auto")
    axes[0].set_title("Mean Attention")
    plt.colorbar(im1, ax=axes[0], label="Attention")

    # Plot 2: Std attention
    im2 = axes[1].imshow(std_attention, cmap="viridis", aspect="auto")
    axes[1].set_title("Attention Variability (Std)")
    plt.colorbar(im2, ax=axes[1], label="Std")

    # Plot 3: Consistency
    im3 = axes[2].imshow(consistency, cmap="coolwarm", aspect="auto")
    axes[2].set_title("Attention Consistency")
    plt.colorbar(im3, ax=axes[2], label="Consistency")

    # Mark top regions on mean attention plot
    top_regions = analysis_results["top_regions"]
    for i, (row, col, _) in enumerate(top_regions[:3]):  # Top 3
        axes[0].plot(col, row, "w*", markersize=15, markeredgecolor="black")
        axes[0].text(
            col, row - 10, f"#{i + 1}", color="white", ha="center", fontweight="bold"
        )

    fig.suptitle(
        "Aggregated Attention Pattern Analysis", fontsize=14, fontweight="bold"
    )
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"Saved attention aggregation plot to {save_path}")

    return fig, axes


def generate_policy_report(
    analysis_results: dict,
    region_metadata: dict | None = None,
    output_path: str | None = None,
) -> str:
    """
    Generate text report of attention patterns for policy interpretation.

    Creates a human-readable summary of which geographic regions the model
    focuses on, suitable for policy briefs and non-technical audiences.

    Args:
        analysis_results: Output from analyze_attention_patterns()
        region_metadata: Optional dict mapping (row, col) to region info
            (e.g., LAD names, LSOA codes)
        output_path: Optional path to save report as text file

    Returns:
        Report text string

    Example:
        >>> analysis = analyze_attention_patterns(model, surfaces)
        >>> report = generate_policy_report(
        ...     analysis,
        ...     region_metadata={(100, 200): "Greater London"}
        ... )
        >>> print(report)
    """
    top_regions = analysis_results["top_regions"]
    mean_attention = analysis_results["mean_attention"]
    std_attention = analysis_results["std_attention"]
    geographic_coords = analysis_results.get("geographic_coords")
    region_names = analysis_results.get("region_names")

    # Build report
    lines = []
    lines.append("=" * 80)
    lines.append("SPATIAL ATTENTION ANALYSIS - POLICY INTERPRETATION REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Summary statistics
    lines.append("SUMMARY STATISTICS:")
    lines.append(
        f"  Total samples analyzed: {len(analysis_results['per_sample_attention'])}"
    )
    lines.append(f"  Mean attention (overall): {mean_attention.mean():.4f}")
    lines.append(f"  Attention variability (overall std): {std_attention.mean():.4f}")
    lines.append("")

    # Top attention regions
    lines.append(f"TOP {len(top_regions)} HIGH-ATTENTION REGIONS:")
    lines.append("  (Regions where the model consistently focuses for predictions)")
    lines.append("")

    for i, (row, col, attention_value) in enumerate(top_regions, 1):
        lines.append(f"  #{i}: Grid Position ({row}, {col})")
        lines.append(f"      Attention Score: {attention_value:.4f}")

        # Add geographic coordinates if available
        if geographic_coords and i <= len(geographic_coords):
            x, y = geographic_coords[i - 1]
            lines.append(f"      Geographic Coords: ({x:.0f}m E, {y:.0f}m N)")

        # Add region metadata if available
        if region_metadata and (row, col) in region_metadata:
            lines.append(f"      Region: {region_metadata[(row, col)]}")

        lines.append("")

    # Policy implications
    lines.append("POLICY IMPLICATIONS:")
    lines.append(
        "  The model learns to focus on specific geographic regions when predicting"
    )
    lines.append("  mobility outcomes. High-attention regions may represent:")
    lines.append("    - Areas with strong influence on overall regional mobility")
    lines.append("    - Regions with distinctive socioeconomic patterns")
    lines.append("    - Potential intervention targets for policy")
    lines.append("")

    # Sample-specific analysis
    if region_names:
        lines.append("PER-SAMPLE ATTENTION SUMMARY:")
        for i, name in enumerate(region_names):
            sample_attention = analysis_results["per_sample_attention"][i]
            mean_att = sample_attention.mean()
            max_att = sample_attention.max()
            lines.append(f"  {name}: Mean={mean_att:.4f}, Max={max_att:.4f}")
        lines.append("")

    lines.append("=" * 80)

    report = "\n".join(lines)

    # Save if requested
    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
        logger.info(f"Saved policy report to {output_path}")

    return report
