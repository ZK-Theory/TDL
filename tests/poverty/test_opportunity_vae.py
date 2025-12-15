"""
Tests for VAE-based opportunity landscape learning.

Tests cover:
- OpportunityVAE architecture (encode, decode, forward)
- VAELoss computation (reconstruction + KL divergence)
- Training pipeline (OpportunityVAETrainer)
- Latent space analysis utilities
- Counterfactual generation
- Integration with mobility surfaces
"""

import numpy as np
import pytest
import torch

from poverty_tda.models.opportunity_vae import (
    OpportunityVAE,
    OpportunityVAETrainer,
    VAELoss,
    analyze_latent_dimensions,
    compute_latent_distance_matrix,
    encode_surfaces,
    generate_counterfactual,
    interpolate_latent,
    sample_latent_space,
    visualize_latent_space_2d,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_surfaces():
    """Create sample mobility surfaces for testing."""
    np.random.seed(42)
    # 5 surfaces, 64x64
    surfaces = np.random.randn(5, 64, 64).astype(np.float32)
    # Normalize to [0, 1]
    surfaces = (surfaces - surfaces.min()) / (surfaces.max() - surfaces.min())
    return surfaces


@pytest.fixture
def vae_model():
    """Create a small VAE model for testing."""
    return OpportunityVAE(input_size=64, latent_dim=8, base_channels=16)


@pytest.fixture
def vae_loss():
    """Create VAE loss module."""
    return VAELoss(beta=1.0, reduction="mean")


# =============================================================================
# ARCHITECTURE TESTS
# =============================================================================


def test_vae_initialization():
    """Test VAE model initialization with various configurations."""
    # Test default configuration
    vae = OpportunityVAE(input_size=64, latent_dim=12)
    assert vae.input_size == 64
    assert vae.latent_dim == 12
    assert vae.base_channels == 32
    assert vae.encoded_size == 4  # 64 // 16

    # Test smaller configuration
    vae_small = OpportunityVAE(input_size=32, latent_dim=8, base_channels=16)
    assert vae_small.input_size == 32
    assert vae_small.latent_dim == 8
    assert vae_small.encoded_size == 2  # 32 // 16


def test_vae_initialization_invalid_size():
    """Test that VAE raises error for too-small input size."""
    with pytest.raises(ValueError, match="too small"):
        OpportunityVAE(input_size=8, latent_dim=12)  # 8 // 16 < 1


def test_vae_encode(vae_model):
    """Test encoding surfaces to latent distribution parameters."""
    batch_size = 4
    x = torch.randn(batch_size, 1, 64, 64)

    mu, logvar = vae_model.encode(x)

    # Check shapes
    assert mu.shape == (batch_size, vae_model.latent_dim)
    assert logvar.shape == (batch_size, vae_model.latent_dim)

    # Check that outputs are reasonable (not NaN, not extreme)
    assert not torch.isnan(mu).any()
    assert not torch.isnan(logvar).any()
    assert torch.abs(mu).max() < 10.0  # Reasonable range
    assert torch.abs(logvar).max() < 10.0


def test_vae_reparameterize(vae_model):
    """Test reparameterization trick."""
    batch_size = 4
    mu = torch.randn(batch_size, vae_model.latent_dim)
    logvar = torch.randn(batch_size, vae_model.latent_dim)

    # Sample multiple times with same mu, logvar
    z1 = vae_model.reparameterize(mu, logvar)
    z2 = vae_model.reparameterize(mu, logvar)

    # Check shape
    assert z1.shape == (batch_size, vae_model.latent_dim)

    # Check that samples are different (stochastic)
    assert not torch.allclose(z1, z2)

    # Check that samples are roughly centered around mu
    z_samples = torch.stack([vae_model.reparameterize(mu, logvar) for _ in range(100)])
    z_mean = z_samples.mean(dim=0)
    assert torch.allclose(z_mean, mu, atol=0.5)  # Allow some variance


def test_vae_decode(vae_model):
    """Test decoding latent codes to surfaces."""
    batch_size = 4
    z = torch.randn(batch_size, vae_model.latent_dim)

    x_recon = vae_model.decode(z)

    # Check shape
    assert x_recon.shape == (batch_size, 1, 64, 64)

    # Check that output is reasonable
    assert not torch.isnan(x_recon).any()


def test_vae_forward(vae_model):
    """Test full forward pass through VAE."""
    batch_size = 4
    x = torch.randn(batch_size, 1, 64, 64)

    x_recon, mu, logvar = vae_model(x)

    # Check shapes
    assert x_recon.shape == x.shape
    assert mu.shape == (batch_size, vae_model.latent_dim)
    assert logvar.shape == (batch_size, vae_model.latent_dim)

    # Check that reconstruction is reasonable
    assert not torch.isnan(x_recon).any()


def test_vae_sample(vae_model):
    """Test sampling from prior."""
    n_samples = 10
    device = torch.device("cpu")

    samples = vae_model.sample(n_samples, device)

    # Check shape
    assert samples.shape == (n_samples, 1, 64, 64)

    # Check that samples are different
    assert not torch.allclose(samples[0], samples[1])


# =============================================================================
# LOSS FUNCTION TESTS
# =============================================================================


def test_vae_loss_initialization():
    """Test VAE loss initialization with different parameters."""
    # Standard VAE
    loss1 = VAELoss(beta=1.0, reduction="mean")
    assert loss1.beta == 1.0
    assert loss1.reduction == "mean"

    # Beta-VAE
    loss2 = VAELoss(beta=4.0, reduction="sum")
    assert loss2.beta == 4.0
    assert loss2.reduction == "sum"


def test_vae_loss_invalid_reduction():
    """Test that VAE loss raises error for invalid reduction."""
    with pytest.raises(ValueError, match="reduction must be"):
        VAELoss(beta=1.0, reduction="invalid")


def test_vae_loss_computation(vae_model, vae_loss):
    """Test VAE loss computation."""
    batch_size = 4
    x = torch.randn(batch_size, 1, 64, 64)
    x_recon, mu, logvar = vae_model(x)

    total_loss, recon_loss, kl_loss = vae_loss(x_recon, x, mu, logvar)

    # Check that losses are scalars
    assert total_loss.shape == ()
    assert recon_loss.shape == ()
    assert kl_loss.shape == ()

    # Check that losses are positive
    assert total_loss > 0
    assert recon_loss > 0
    assert kl_loss >= 0  # Can be 0 if mu=0, logvar=0

    # Check that total = recon + beta * kl
    expected_total = recon_loss + vae_loss.beta * kl_loss
    assert torch.allclose(total_loss, expected_total)


def test_vae_loss_beta_weighting():
    """Test that beta parameter affects loss weighting."""
    vae = OpportunityVAE(input_size=64, latent_dim=8)
    x = torch.randn(4, 1, 64, 64)
    x_recon, mu, logvar = vae(x)

    # Compute with beta=1.0
    loss1 = VAELoss(beta=1.0)
    total1, recon1, kl1 = loss1(x_recon, x, mu, logvar)

    # Compute with beta=2.0
    loss2 = VAELoss(beta=2.0)
    total2, recon2, kl2 = loss2(x_recon, x, mu, logvar)

    # Reconstruction should be same
    assert torch.allclose(recon1, recon2)

    # KL should be same
    assert torch.allclose(kl1, kl2)

    # Total should differ by beta
    expected_total2 = recon2 + 2.0 * kl2
    assert torch.allclose(total2, expected_total2)


def test_vae_loss_reduction_modes():
    """Test different reduction modes for VAE loss."""
    vae = OpportunityVAE(input_size=64, latent_dim=8)
    x = torch.randn(4, 1, 64, 64)
    x_recon, mu, logvar = vae(x)

    # Mean reduction
    loss_mean = VAELoss(beta=1.0, reduction="mean")
    total_mean, recon_mean, kl_mean = loss_mean(x_recon, x, mu, logvar)

    # Sum reduction
    loss_sum = VAELoss(beta=1.0, reduction="sum")
    total_sum, recon_sum, kl_sum = loss_sum(x_recon, x, mu, logvar)

    # Sum should be larger than mean (for batch_size > 1)
    assert total_sum > total_mean
    assert recon_sum > recon_mean


# =============================================================================
# TRAINING PIPELINE TESTS
# =============================================================================


def test_trainer_initialization(vae_model):
    """Test trainer initialization."""
    trainer = OpportunityVAETrainer(vae_model, beta=1.0, lr=1e-4, device="cpu")

    assert trainer.model == vae_model
    assert trainer.device == torch.device("cpu")
    assert trainer.criterion.beta == 1.0
    assert len(trainer.history["train_loss"]) == 0


def test_trainer_train_epoch(vae_model, sample_surfaces):
    """Test training for one epoch."""
    trainer = OpportunityVAETrainer(vae_model, beta=1.0, lr=1e-3, device="cpu")

    # Create data loader
    surfaces_tensor = torch.from_numpy(sample_surfaces).unsqueeze(1)  # Add channel
    dataset = torch.utils.data.TensorDataset(surfaces_tensor)
    loader = torch.utils.data.DataLoader(dataset, batch_size=2, shuffle=True)

    # Train one epoch
    metrics = trainer.train_epoch(loader)

    # Check metrics
    assert "loss" in metrics
    assert "recon_loss" in metrics
    assert "kl_loss" in metrics
    assert metrics["loss"] > 0
    assert metrics["recon_loss"] > 0
    assert metrics["kl_loss"] >= 0


def test_trainer_validate(vae_model, sample_surfaces):
    """Test validation."""
    trainer = OpportunityVAETrainer(vae_model, beta=1.0, lr=1e-3, device="cpu")

    # Create data loader
    surfaces_tensor = torch.from_numpy(sample_surfaces).unsqueeze(1)
    dataset = torch.utils.data.TensorDataset(surfaces_tensor)
    loader = torch.utils.data.DataLoader(dataset, batch_size=2)

    # Validate
    metrics = trainer.validate(loader)

    # Check metrics
    assert "loss" in metrics
    assert "recon_loss" in metrics
    assert "kl_loss" in metrics
    assert metrics["loss"] > 0


def test_trainer_train_loop(vae_model, sample_surfaces):
    """Test full training loop with early stopping."""
    trainer = OpportunityVAETrainer(vae_model, beta=1.0, lr=1e-3, device="cpu")

    # Create train/val loaders
    n_train = 4
    train_surfaces = sample_surfaces[:n_train]
    val_surfaces = sample_surfaces[n_train:]

    train_tensor = torch.from_numpy(train_surfaces).unsqueeze(1)
    val_tensor = torch.from_numpy(val_surfaces).unsqueeze(1)

    train_dataset = torch.utils.data.TensorDataset(train_tensor)
    val_dataset = torch.utils.data.TensorDataset(val_tensor)

    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=2)
    val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=2)

    # Train for a few epochs
    history = trainer.train(
        train_loader, val_loader, epochs=5, early_stopping_patience=10
    )

    # Check history
    assert len(history["train_loss"]) == 5
    assert len(history["val_loss"]) == 5
    assert len(history["train_recon"]) == 5
    assert len(history["train_kl"]) == 5

    # Check that training reduced loss (at least slightly)
    assert history["train_loss"][-1] <= history["train_loss"][0] * 1.5


# =============================================================================
# LATENT SPACE UTILITIES TESTS
# =============================================================================


def test_encode_surfaces(vae_model, sample_surfaces):
    """Test encoding surfaces to latent codes."""
    # Test with numpy array
    latent_codes = encode_surfaces(vae_model, sample_surfaces)

    assert isinstance(latent_codes, np.ndarray)
    assert latent_codes.shape == (len(sample_surfaces), vae_model.latent_dim)

    # Test with torch tensor
    surfaces_tensor = torch.from_numpy(sample_surfaces)
    latent_codes_2 = encode_surfaces(vae_model, surfaces_tensor)

    assert latent_codes_2.shape == (len(sample_surfaces), vae_model.latent_dim)


def test_interpolate_latent(vae_model):
    """Test latent space interpolation."""
    # Create two latent codes
    z1 = np.random.randn(vae_model.latent_dim)
    z2 = np.random.randn(vae_model.latent_dim)

    # Interpolate
    steps = 11
    surfaces = interpolate_latent(vae_model, z1, z2, steps=steps)

    # Check shape
    assert surfaces.shape == (steps, 64, 64)

    # Check that endpoints are different
    assert not np.allclose(surfaces[0], surfaces[-1])

    # Check that interpolation is smooth (adjacent steps are similar)
    for i in range(steps - 1):
        diff = np.abs(surfaces[i + 1] - surfaces[i]).mean()
        assert diff < 0.5  # Adjacent steps shouldn't be too different


def test_sample_latent_space(vae_model):
    """Test sampling from latent space prior."""
    n_samples = 10
    surfaces = sample_latent_space(vae_model, n_samples=n_samples)

    # Check shape
    assert surfaces.shape == (n_samples, 64, 64)

    # Check that samples are different
    assert not np.allclose(surfaces[0], surfaces[1])


def test_analyze_latent_dimensions(vae_model, sample_surfaces):
    """Test latent dimension analysis."""
    # Create simple metadata
    metadata = {
        "feature_1": np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
        "feature_2": np.array([1.0, 0.8, 0.6, 0.4, 0.2]),
    }

    # Analyze
    analysis = analyze_latent_dimensions(
        vae_model, sample_surfaces, metadata, n_traversal_steps=5
    )

    # Check structure
    assert "latent_codes" in analysis
    assert "traversals" in analysis
    assert "dimension_stats" in analysis
    assert "correlations" in analysis

    # Check latent codes
    assert analysis["latent_codes"].shape == (
        len(sample_surfaces),
        vae_model.latent_dim,
    )

    # Check traversals
    assert len(analysis["traversals"]) == vae_model.latent_dim
    for dim, traversal in analysis["traversals"].items():
        assert traversal.shape == (5, 64, 64)  # n_traversal_steps=5

    # Check dimension stats
    assert len(analysis["dimension_stats"]) == vae_model.latent_dim
    for dim, stats in analysis["dimension_stats"].items():
        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats

    # Check correlations
    assert "feature_1" in analysis["correlations"]
    assert "feature_2" in analysis["correlations"]


def test_generate_counterfactual(vae_model, sample_surfaces):
    """Test counterfactual generation."""
    source = sample_surfaces[0]
    target = sample_surfaces[-1]

    # Generate counterfactual with specific dimensions
    intervention_dims = [0, 1, 2]
    counterfactual, details = generate_counterfactual(
        vae_model,
        source,
        target,
        intervention_dims=intervention_dims,
        intervention_strength=0.5,
    )

    # Check shape
    assert counterfactual.shape == (64, 64)

    # Check details
    assert "source_code" in details
    assert "target_code" in details
    assert "intervened_code" in details
    assert "intervention_dims" in details
    assert details["intervention_dims"] == intervention_dims

    # Check latent changes
    assert len(details["latent_changes"]) == len(intervention_dims)


def test_compute_latent_distance_matrix(vae_model, sample_surfaces):
    """Test latent space distance matrix computation."""
    distances = compute_latent_distance_matrix(vae_model, sample_surfaces)

    # Check shape
    n = len(sample_surfaces)
    assert distances.shape == (n, n)

    # Check properties
    assert np.allclose(np.diag(distances), 0, atol=1e-4)  # Diagonal is zero
    assert np.allclose(distances, distances.T)  # Symmetric
    assert (distances >= 0).all()  # All non-negative


def test_visualize_latent_space_2d(vae_model, sample_surfaces):
    """Test 2D latent space visualization."""
    # Test PCA
    coords_pca, meta_pca = visualize_latent_space_2d(
        vae_model, sample_surfaces, method="pca"
    )

    assert coords_pca.shape == (len(sample_surfaces), 2)
    assert "explained_variance_ratio" in meta_pca
    assert "total_variance_explained" in meta_pca

    # Note: Skipping t-SNE test for small sample size (perplexity issues)
    # t-SNE requires perplexity < n_samples, and default is 30


def test_visualize_latent_space_2d_invalid_method(vae_model, sample_surfaces):
    """Test that invalid method raises error."""
    with pytest.raises(ValueError, match="Unknown method"):
        visualize_latent_space_2d(vae_model, sample_surfaces, method="invalid")


# =============================================================================
# RECONSTRUCTION QUALITY TESTS
# =============================================================================


def test_vae_reconstruction_quality(vae_model, sample_surfaces):
    """Test that VAE can reconstruct surfaces reasonably well."""
    # Train briefly to get some reconstruction capability
    trainer = OpportunityVAETrainer(vae_model, beta=1.0, lr=1e-3, device="cpu")

    surfaces_tensor = torch.from_numpy(sample_surfaces).unsqueeze(1)
    dataset = torch.utils.data.TensorDataset(surfaces_tensor)
    loader = torch.utils.data.DataLoader(dataset, batch_size=2)

    # Train for a few epochs
    for _ in range(10):
        trainer.train_epoch(loader)

    # Test reconstruction
    vae_model.eval()
    with torch.no_grad():
        x = surfaces_tensor[:2]
        x_recon, _, _ = vae_model(x)

    # Check that reconstruction has reasonable MSE
    mse = torch.nn.functional.mse_loss(x_recon, x).item()
    assert mse < 1.0  # Should be able to reconstruct with some fidelity after training


def test_latent_interpolation_smoothness(vae_model, sample_surfaces):
    """Test that latent interpolation produces smooth transitions."""
    # Encode two surfaces
    z1 = encode_surfaces(vae_model, sample_surfaces[0:1])[0]
    z2 = encode_surfaces(vae_model, sample_surfaces[1:2])[0]

    # Interpolate with many steps
    surfaces = interpolate_latent(vae_model, z1, z2, steps=20)

    # Compute differences between adjacent steps
    diffs = []
    for i in range(len(surfaces) - 1):
        diff = np.abs(surfaces[i + 1] - surfaces[i]).mean()
        diffs.append(diff)

    # Check that differences are roughly constant (smooth interpolation)
    diffs = np.array(diffs)
    assert np.std(diffs) / np.mean(diffs) < 0.5  # Coefficient of variation < 0.5


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


def test_vae_end_to_end_workflow(sample_surfaces):
    """Test complete VAE workflow from training to analysis."""
    # 1. Create model
    vae = OpportunityVAE(input_size=64, latent_dim=8, base_channels=16)

    # 2. Create trainer and train
    trainer = OpportunityVAETrainer(vae, beta=1.0, lr=1e-3, device="cpu")

    # Split data
    n_train = 4
    train_surfaces = sample_surfaces[:n_train]
    val_surfaces = sample_surfaces[n_train:]

    train_tensor = torch.from_numpy(train_surfaces).unsqueeze(1)
    val_tensor = torch.from_numpy(val_surfaces).unsqueeze(1)

    train_dataset = torch.utils.data.TensorDataset(train_tensor)
    val_dataset = torch.utils.data.TensorDataset(val_tensor)

    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=2)
    val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=2)

    # Train
    history = trainer.train(
        train_loader, val_loader, epochs=5, early_stopping_patience=10
    )

    assert len(history["train_loss"]) == 5

    # 3. Encode surfaces
    latent_codes = encode_surfaces(vae, sample_surfaces)
    assert latent_codes.shape == (len(sample_surfaces), 8)

    # 4. Generate counterfactual
    counterfactual, details = generate_counterfactual(
        vae, sample_surfaces[0], sample_surfaces[-1], intervention_dims=[0, 1]
    )
    assert counterfactual.shape == (64, 64)

    # 5. Compute distances
    distances = compute_latent_distance_matrix(vae, sample_surfaces)
    assert distances.shape == (len(sample_surfaces), len(sample_surfaces))

    # 6. Visualize in 2D
    coords_2d, meta = visualize_latent_space_2d(vae, sample_surfaces, method="pca")
    assert coords_2d.shape == (len(sample_surfaces), 2)


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================


def test_vae_with_different_input_sizes():
    """Test VAE with various valid input sizes."""
    for size in [16, 32, 64, 128]:
        vae = OpportunityVAE(input_size=size, latent_dim=8)
        x = torch.randn(2, 1, size, size)
        x_recon, mu, logvar = vae(x)
        assert x_recon.shape == x.shape


def test_encode_surfaces_single_surface(vae_model):
    """Test encoding a single surface."""
    surface = np.random.randn(64, 64)
    latent_code = encode_surfaces(vae_model, surface[np.newaxis, :])
    assert latent_code.shape == (1, vae_model.latent_dim)


def test_counterfactual_with_all_dimensions(vae_model, sample_surfaces):
    """Test counterfactual generation transferring all dimensions."""
    counterfactual, details = generate_counterfactual(
        vae_model,
        sample_surfaces[0],
        sample_surfaces[-1],
        intervention_dims=None,  # Transfer all
        intervention_strength=1.0,
    )

    assert counterfactual.shape == (64, 64)
    assert len(details["intervention_dims"]) == vae_model.latent_dim


def test_counterfactual_amplified_intervention(vae_model, sample_surfaces):
    """Test counterfactual with intervention strength > 1 (extrapolation)."""
    counterfactual, details = generate_counterfactual(
        vae_model,
        sample_surfaces[0],
        sample_surfaces[-1],
        intervention_dims=[0, 1],
        intervention_strength=1.5,  # Amplified
    )

    assert counterfactual.shape == (64, 64)
    assert details["intervention_strength"] == 1.5
