"""
Tests for CNN autoencoder anomaly detection on persistence images.

Tests the PersistenceAutoencoder module including architecture, training,
anomaly detection, and crisis validation.
"""

import numpy as np
import pytest
import torch

from financial_tda.models.persistence_autoencoder import (
    AutoencoderTrainer,
    EarlyStopping,
    PersistenceAutoencoder,
    PersistenceImageDataset,
    compute_lead_time,
    compute_reconstruction_error,
    detect_anomalies,
    fit_anomaly_threshold,
    validate_crisis_detection,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_images():
    """Generate sample persistence images."""
    np.random.seed(42)
    # Normal images: stable patterns
    normal = np.random.rand(50, 50, 50) * 0.4 + 0.3  # [0.3, 0.7]
    # Crisis images: anomalous patterns
    crisis = np.random.rand(20, 50, 50) * 0.3 + 0.1  # [0.1, 0.4]
    crisis += np.random.rand(20, 50, 50) * 0.9  # Add noise
    return {"normal": normal, "crisis": crisis}


@pytest.fixture
def trained_model(sample_images):
    """Train a small autoencoder for testing."""
    model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=16)
    trainer = AutoencoderTrainer(model, learning_rate=1e-3, device="cpu")

    # Quick training on normal data
    normal_train = sample_images["normal"][:40]
    normal_val = sample_images["normal"][40:]

    train_dataset = PersistenceImageDataset(normal_train)
    val_dataset = PersistenceImageDataset(normal_val)

    trainer.train(
        train_dataset,
        val_dataset,
        num_epochs=5,
        batch_size=8,
        patience=3,
        verbose=False,
    )

    return model


# =============================================================================
# Test PersistenceAutoencoder Architecture
# =============================================================================


class TestPersistenceAutoencoder:
    """Tests for autoencoder architecture."""

    def test_initialization(self):
        """Test model initialization with default parameters."""
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=32)

        assert model.input_size == (50, 50)
        assert model.latent_dim == 32
        assert model.encoded_size == 6  # 50 -> 25 -> 12 -> 6

    def test_initialization_custom_latent(self):
        """Test model with custom latent dimension."""
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=64)

        assert model.latent_dim == 64

    def test_forward_pass_shape(self):
        """Test forward pass returns correct shape."""
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=16)
        batch_size = 4

        x = torch.randn(batch_size, 1, 50, 50)
        output = model(x)

        assert output.shape == (batch_size, 1, 50, 50)
        assert output.min() >= 0.0  # Sigmoid output
        assert output.max() <= 1.0

    def test_encode_shape(self):
        """Test encoder output shape."""
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=16)
        x = torch.randn(4, 1, 50, 50)

        latent = model.encode(x)

        assert latent.shape == (4, 16)

    def test_decode_shape(self):
        """Test decoder output shape."""
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=16)
        latent = torch.randn(4, 16)

        reconstruction = model.decode(latent)

        assert reconstruction.shape == (4, 1, 50, 50)
        assert reconstruction.min() >= 0.0
        assert reconstruction.max() <= 1.0

    def test_encode_decode_consistency(self):
        """Test that encode -> decode preserves shape."""
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=16)
        x = torch.randn(4, 1, 50, 50)

        latent = model.encode(x)
        reconstruction = model.decode(latent)

        assert reconstruction.shape == x.shape

    def test_non_square_images_rejected(self):
        """Test that non-square images are rejected."""
        with pytest.raises(ValueError, match="Only square images supported"):
            PersistenceAutoencoder(input_size=(50, 60))


# =============================================================================
# Test PersistenceImageDataset
# =============================================================================


class TestPersistenceImageDataset:
    """Tests for dataset class."""

    def test_initialization_3d_array(self):
        """Test dataset with 3D numpy array."""
        images = np.random.rand(10, 50, 50)
        dataset = PersistenceImageDataset(images)

        assert len(dataset) == 10
        assert dataset[0].shape == (1, 50, 50)

    def test_initialization_4d_array(self):
        """Test dataset with 4D array (batch, 1, H, W)."""
        images = np.random.rand(10, 1, 50, 50)
        dataset = PersistenceImageDataset(images)

        assert len(dataset) == 10
        assert dataset[0].shape == (1, 50, 50)

    def test_normalization(self):
        """Test that images are normalized to [0, 1]."""
        images = np.random.rand(10, 50, 50) * 100  # [0, 100]
        dataset = PersistenceImageDataset(images, normalize=True)

        sample = dataset[0]
        assert sample.min() >= 0.0
        assert sample.max() <= 1.0

    def test_no_normalization(self):
        """Test dataset without normalization."""
        images = np.random.rand(10, 50, 50) * 100
        dataset = PersistenceImageDataset(images, normalize=False)

        sample = dataset[0]
        # Should not be normalized
        assert sample.max() > 1.0

    def test_tensor_input(self):
        """Test dataset with torch tensor input."""
        images = torch.randn(10, 50, 50)
        dataset = PersistenceImageDataset(images)

        assert len(dataset) == 10
        assert isinstance(dataset[0], torch.Tensor)

    def test_invalid_dimensions(self):
        """Test that invalid dimensions are rejected."""
        with pytest.raises(ValueError, match="must be 3D"):
            PersistenceImageDataset(np.random.rand(50, 50))  # 2D


# =============================================================================
# Test EarlyStopping
# =============================================================================


class TestEarlyStopping:
    """Tests for early stopping utility."""

    def test_early_stopping_triggers(self):
        """Test that early stopping triggers after patience epochs."""
        early_stopping = EarlyStopping(patience=3, min_delta=1e-4, mode="min")

        # No improvement for 3 epochs
        early_stopping(1.0)
        assert not early_stopping.early_stop

        early_stopping(1.0)
        assert not early_stopping.early_stop

        early_stopping(1.0)
        assert not early_stopping.early_stop

        early_stopping(1.0)  # 4th epoch without improvement
        assert early_stopping.early_stop

    def test_early_stopping_resets_on_improvement(self):
        """Test that counter resets on improvement."""
        early_stopping = EarlyStopping(patience=3, min_delta=1e-4, mode="min")

        early_stopping(1.0)
        early_stopping(1.0)
        early_stopping(0.9)  # Improvement
        assert not early_stopping.early_stop
        assert early_stopping.counter == 0

    def test_min_delta_threshold(self):
        """Test that min_delta is respected."""
        early_stopping = EarlyStopping(patience=2, min_delta=0.1, mode="min")

        early_stopping(1.0)
        early_stopping(0.95)  # Improvement < min_delta
        assert early_stopping.counter == 1  # Not counted as improvement

    def test_max_mode(self):
        """Test early stopping in max mode."""
        early_stopping = EarlyStopping(patience=3, min_delta=1e-4, mode="max")

        early_stopping(0.5)
        early_stopping(0.6)  # Improvement
        assert early_stopping.counter == 0
        assert not early_stopping.early_stop

        # No improvement for patience epochs
        early_stopping(0.6)  # counter = 1
        assert early_stopping.counter == 1
        assert not early_stopping.early_stop

        early_stopping(0.6)  # counter = 2
        assert early_stopping.counter == 2
        assert not early_stopping.early_stop

        early_stopping(0.6)  # counter = 3, triggers early_stop
        assert early_stopping.counter == 3
        assert early_stopping.early_stop


# =============================================================================
# Test AutoencoderTrainer
# =============================================================================


class TestAutoencoderTrainer:
    """Tests for training pipeline."""

    def test_initialization(self):
        """Test trainer initialization."""
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=16)
        trainer = AutoencoderTrainer(model, learning_rate=1e-3, device="cpu")

        assert trainer.model is model
        assert trainer.device == torch.device("cpu")
        assert trainer.optimizer is not None
        assert trainer.scheduler is not None

    def test_train_epoch(self, sample_images):
        """Test single training epoch."""
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=16)
        trainer = AutoencoderTrainer(model, learning_rate=1e-3, device="cpu")

        dataset = PersistenceImageDataset(sample_images["normal"][:20])
        loader = torch.utils.data.DataLoader(dataset, batch_size=4)

        loss = trainer.train_epoch(loader)

        assert isinstance(loss, float)
        assert loss > 0.0

    def test_validate(self, sample_images):
        """Test validation."""
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=16)
        trainer = AutoencoderTrainer(model, learning_rate=1e-3, device="cpu")

        dataset = PersistenceImageDataset(sample_images["normal"][:10])
        loader = torch.utils.data.DataLoader(dataset, batch_size=4)

        val_loss = trainer.validate(loader)

        assert isinstance(val_loss, float)
        assert val_loss > 0.0

    def test_full_training(self, sample_images):
        """Test complete training loop."""
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=16)
        trainer = AutoencoderTrainer(model, learning_rate=1e-3, device="cpu")

        train_dataset = PersistenceImageDataset(sample_images["normal"][:40])
        val_dataset = PersistenceImageDataset(sample_images["normal"][40:])

        history = trainer.train(
            train_dataset,
            val_dataset,
            num_epochs=5,
            batch_size=8,
            patience=3,
            verbose=False,
        )

        assert "train_loss" in history
        assert "val_loss" in history
        assert "best_val_loss" in history
        assert "best_epoch" in history
        assert len(history["train_loss"]) > 0
        assert len(history["val_loss"]) == len(history["train_loss"])

    def test_training_reduces_loss(self, sample_images):
        """Test that training reduces loss."""
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=16)
        trainer = AutoencoderTrainer(model, learning_rate=1e-3, device="cpu")

        train_dataset = PersistenceImageDataset(sample_images["normal"][:40])
        val_dataset = PersistenceImageDataset(sample_images["normal"][40:])

        history = trainer.train(
            train_dataset,
            val_dataset,
            num_epochs=10,
            batch_size=8,
            patience=5,
            verbose=False,
        )

        # Loss should decrease
        assert history["train_loss"][-1] < history["train_loss"][0]


# =============================================================================
# Test Anomaly Detection
# =============================================================================


class TestAnomalyDetection:
    """Tests for anomaly detection utilities."""

    def test_compute_reconstruction_error(self, trained_model, sample_images):
        """Test reconstruction error computation."""
        normal_images = sample_images["normal"][:10]

        errors = compute_reconstruction_error(
            trained_model, normal_images, device="cpu"
        )

        assert errors.shape == (10,)
        assert np.all(errors >= 0.0)
        assert isinstance(errors, np.ndarray)

    def test_reconstruction_error_with_tensor(self, trained_model):
        """Test reconstruction error with torch tensor input."""
        images = torch.randn(5, 50, 50)

        errors = compute_reconstruction_error(trained_model, images, device="cpu")

        assert errors.shape == (5,)
        assert isinstance(errors, np.ndarray)

    def test_fit_anomaly_threshold(self, trained_model, sample_images):
        """Test threshold fitting at 95th percentile."""
        normal_images = sample_images["normal"]

        threshold = fit_anomaly_threshold(
            trained_model, normal_images, percentile=95, device="cpu"
        )

        assert isinstance(threshold, float)
        assert threshold > 0.0

    def test_threshold_percentile_relationship(self, trained_model, sample_images):
        """Test that higher percentile gives higher threshold."""
        normal_images = sample_images["normal"]

        threshold_90 = fit_anomaly_threshold(
            trained_model, normal_images, percentile=90, device="cpu"
        )
        threshold_95 = fit_anomaly_threshold(
            trained_model, normal_images, percentile=95, device="cpu"
        )

        assert threshold_95 > threshold_90

    def test_detect_anomalies(self, trained_model, sample_images):
        """Test anomaly detection."""
        normal_images = sample_images["normal"]
        crisis_images = sample_images["crisis"]

        # Fit threshold on normal data
        threshold = fit_anomaly_threshold(
            trained_model, normal_images, percentile=95, device="cpu"
        )

        # Detect on crisis data
        is_anomaly, scores = detect_anomalies(
            trained_model, crisis_images, threshold, device="cpu"
        )

        assert is_anomaly.shape == (20,)
        assert scores.shape == (20,)
        assert is_anomaly.dtype == bool
        assert isinstance(scores, np.ndarray)

    def test_crisis_higher_scores_than_normal(self, trained_model, sample_images):
        """Test that crisis images have higher anomaly scores."""
        normal_images = sample_images["normal"][:20]
        crisis_images = sample_images["crisis"]

        # Compute scores
        errors_normal = compute_reconstruction_error(
            trained_model, normal_images, device="cpu"
        )
        errors_crisis = compute_reconstruction_error(
            trained_model, crisis_images, device="cpu"
        )

        # Crisis should have higher mean error
        assert errors_crisis.mean() > errors_normal.mean()

    def test_false_positive_rate_approximately_correct(
        self, trained_model, sample_images
    ):
        """Test that FPR is approximately at target percentile."""
        normal_images = sample_images["normal"]

        threshold = fit_anomaly_threshold(
            trained_model, normal_images, percentile=95, device="cpu"
        )

        # Test on same data (should be ~5% flagged)
        is_anomaly, _ = detect_anomalies(
            trained_model, normal_images, threshold, device="cpu"
        )

        fpr = 100 * is_anomaly.mean()
        # Should be close to 5% (allow 10% margin due to small sample)
        assert fpr < 15.0


# =============================================================================
# Test Crisis Validation
# =============================================================================


class TestCrisisValidation:
    """Tests for crisis validation utilities."""

    def test_validate_crisis_detection(self, trained_model, sample_images):
        """Test multi-crisis validation."""
        crisis_data = {
            "2008_GFC": sample_images["crisis"][:10],
            "2020_COVID": sample_images["crisis"][10:],
        }
        normal_data = sample_images["normal"][:20]

        threshold = fit_anomaly_threshold(
            trained_model, sample_images["normal"], percentile=95, device="cpu"
        )

        results = validate_crisis_detection(
            trained_model,
            threshold,
            crisis_data,
            normal_data=normal_data,
            device="cpu",
        )

        assert "2008_GFC" in results
        assert "2020_COVID" in results

        for crisis_name, metrics in results.items():
            assert "true_positive_rate" in metrics
            assert "n_detected" in metrics
            assert "n_total" in metrics
            assert "mean_anomaly_score" in metrics
            assert "max_anomaly_score" in metrics
            assert "false_positive_rate" in metrics

            # TPR should be between 0 and 100
            assert 0.0 <= metrics["true_positive_rate"] <= 100.0

    def test_validate_without_normal_data(self, trained_model, sample_images):
        """Test validation without normal data (no FPR)."""
        crisis_data = {"Test_Crisis": sample_images["crisis"][:10]}

        threshold = fit_anomaly_threshold(
            trained_model, sample_images["normal"], percentile=95, device="cpu"
        )

        results = validate_crisis_detection(
            trained_model, threshold, crisis_data, normal_data=None, device="cpu"
        )

        assert "Test_Crisis" in results
        assert "false_positive_rate" not in results["Test_Crisis"]

    def test_compute_lead_time(self):
        """Test lead time computation."""
        # Anomalies detected 14 days before peak
        anomaly_flags = np.array([False] * 85 + [True] * 15)
        crisis_peak = 99

        lead_time = compute_lead_time(anomaly_flags, crisis_peak)

        assert lead_time == 14

    def test_compute_lead_time_no_warning(self):
        """Test lead time when no early warning."""
        anomaly_flags = np.array([False] * 100)
        crisis_peak = 99

        lead_time = compute_lead_time(anomaly_flags, crisis_peak)

        assert lead_time is None

    def test_compute_lead_time_immediate(self):
        """Test lead time when detected at peak."""
        anomaly_flags = np.array([False] * 99 + [True])
        crisis_peak = 99

        lead_time = compute_lead_time(anomaly_flags, crisis_peak)

        # No anomaly before peak, so no lead time
        assert lead_time is None

    def test_compute_lead_time_invalid_peak(self):
        """Test that invalid peak index raises error."""
        anomaly_flags = np.array([False] * 100)

        with pytest.raises(ValueError, match="out of range"):
            compute_lead_time(anomaly_flags, 150)


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_pipeline_normal_vs_crisis(self, sample_images):
        """Test complete pipeline from training to crisis detection."""
        # 1. Train on normal periods
        model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=32)
        trainer = AutoencoderTrainer(model, learning_rate=1e-3, device="cpu")

        normal_train = sample_images["normal"][:40]
        normal_val = sample_images["normal"][40:]

        trainer.train(
            PersistenceImageDataset(normal_train),
            PersistenceImageDataset(normal_val),
            num_epochs=10,
            batch_size=8,
            patience=5,
            verbose=False,
        )

        # 2. Fit threshold
        threshold = fit_anomaly_threshold(
            model, normal_train, percentile=95, device="cpu"
        )

        # 3. Detect on crisis data
        crisis_images = sample_images["crisis"]
        is_anomaly, scores = detect_anomalies(
            model, crisis_images, threshold, device="cpu"
        )

        # 4. Validate detection rate
        detection_rate = 100 * is_anomaly.mean()

        # Should detect significant portion of crisis windows
        assert detection_rate > 50.0  # At least 50% detection
        assert np.all(scores >= 0.0)

    def test_model_save_load(self, trained_model, tmp_path):
        """Test model save and load functionality."""
        save_path = tmp_path / "test_model.pt"

        # Create trainer and save
        trainer = AutoencoderTrainer(trained_model, device="cpu")
        trainer.save_model(save_path)

        assert save_path.exists()

        # Create new model and load
        new_model = PersistenceAutoencoder(input_size=(50, 50), latent_dim=16)
        new_trainer = AutoencoderTrainer(new_model, device="cpu")
        new_trainer.load_model(save_path)

        # Test that loaded model produces same output
        test_input = torch.randn(2, 1, 50, 50)

        with torch.no_grad():
            output_original = trained_model(test_input)
            output_loaded = new_model(test_input)

        assert torch.allclose(output_original, output_loaded, atol=1e-6)
