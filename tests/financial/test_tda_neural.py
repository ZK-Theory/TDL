"""
Tests for topological neural network models.

Tests cover Perslay vectorization layers, LSTM/Transformer sequence models,
training pipeline, and end-to-end regime detection functionality.
"""

import numpy as np
import pytest
import torch

from financial_tda.models import (
    EarlyStopping,
    PersistenceDataset,
    RegimeDetectionModel,
    TransformerRegimeDetector,
    collate_persistence_batch,
    compute_metrics,
    create_perslay,
    create_regime_detector,
    evaluate,
    train_epoch,
    train_model,
    train_test_split_temporal,
)
from financial_tda.models.persistence_layers import DeepSetPhi, Perslay, PowerWeight
from financial_tda.topology import compute_persistence_vr, takens_embedding


class TestPersistenceLayers:
    """Tests for Perslay and related layers."""

    @pytest.fixture
    def sample_diagrams(self):
        """Create sample persistence diagrams."""
        torch.manual_seed(42)
        diag1 = torch.rand(10, 2)
        diag1[:, 1] = diag1[:, 0] + torch.rand(10) * 0.5
        diag2 = torch.rand(5, 2)
        diag2[:, 1] = diag2[:, 0] + torch.rand(5) * 0.3
        diag3 = torch.rand(15, 2)
        diag3[:, 1] = diag3[:, 0] + torch.rand(15) * 0.4
        return [diag1, diag2, diag3]

    def test_deepset_phi_forward(self, sample_diagrams):
        """Test DeepSetPhi forward pass."""
        phi = DeepSetPhi(input_dim=2, hidden_dims=[32, 16], output_dim=8)

        from financial_tda.models.persistence_layers import pad_diagrams

        padded, mask = pad_diagrams(sample_diagrams)
        features = phi(padded, mask)

        assert features.shape == (3, 15, 8)  # (batch, max_points, output_dim)
        assert torch.isfinite(features).all()

    def test_power_weight_forward(self, sample_diagrams):
        """Test PowerWeight computation."""
        weight = PowerWeight(power=1.0, init_coeff=1.0)

        from financial_tda.models.persistence_layers import pad_diagrams

        padded, _ = pad_diagrams(sample_diagrams)
        weights = weight(padded)

        assert weights.shape == (3, 15)  # (batch, max_points)
        assert torch.isfinite(weights).all()
        assert (weights >= 0).all()

    def test_perslay_forward(self, sample_diagrams):
        """Test Perslay layer forward pass."""
        phi = DeepSetPhi(input_dim=2, output_dim=16)
        perslay = Perslay(phi=phi, perm_op="mean")

        embeddings = perslay(sample_diagrams)

        assert embeddings.shape == (3, 16)
        assert torch.isfinite(embeddings).all()

    def test_perslay_with_weight(self, sample_diagrams):
        """Test Perslay with learnable weights."""
        phi = DeepSetPhi(input_dim=2, output_dim=16)
        weight = PowerWeight(power=1.0)
        perslay = Perslay(phi=phi, weight=weight, perm_op="sum")

        embeddings = perslay(sample_diagrams)

        assert embeddings.shape == (3, 16)
        assert torch.isfinite(embeddings).all()

    def test_perslay_aggregations(self, sample_diagrams):
        """Test different aggregation operations."""
        phi = DeepSetPhi(input_dim=2, output_dim=8)

        for agg_op in ["sum", "mean", "max"]:
            perslay = Perslay(phi=phi, perm_op=agg_op)
            embeddings = perslay(sample_diagrams)
            assert embeddings.shape == (3, 8)
            assert torch.isfinite(embeddings).all()

    def test_perslay_gradient_flow(self, sample_diagrams):
        """Test gradient flow through Perslay."""
        perslay = create_perslay(output_dim=16)

        embeddings = perslay(sample_diagrams)
        loss = embeddings.sum()
        loss.backward()

        assert all(p.grad is not None for p in perslay.parameters())


class TestSequenceModels:
    """Tests for LSTM and Transformer sequence models."""

    @pytest.fixture
    def sample_sequences(self):
        """Create sample diagram sequences."""
        torch.manual_seed(42)
        sequences = []
        for _ in range(4):  # 4 samples
            seq = []
            for _ in range(5):  # 5 time windows
                n_points = np.random.randint(5, 15)
                diag = torch.rand(n_points, 2)
                diag[:, 1] = diag[:, 0] + torch.rand(n_points) * 0.3
                seq.append(diag)
            sequences.append(seq)
        return sequences

    def test_lstm_model_forward(self, sample_sequences):
        """Test LSTM-based regime detection model."""
        perslay = create_perslay(output_dim=16)
        model = RegimeDetectionModel(
            perslay=perslay, sequence_model="lstm", hidden_dim=32, num_layers=2
        )

        logits = model(sample_sequences)

        assert logits.shape == (4, 2)  # (batch, num_classes)
        assert torch.isfinite(logits).all()

    def test_bidirectional_lstm(self, sample_sequences):
        """Test bidirectional LSTM model."""
        perslay = create_perslay(output_dim=16)
        model = RegimeDetectionModel(
            perslay=perslay,
            sequence_model="lstm",
            hidden_dim=32,
            bidirectional=True,
        )

        logits = model(sample_sequences)

        assert logits.shape == (4, 2)
        assert torch.isfinite(logits).all()

    def test_transformer_model_forward(self, sample_sequences):
        """Test Transformer-based regime detection model."""
        perslay = create_perslay(output_dim=64)
        model = RegimeDetectionModel(
            perslay=perslay, sequence_model="transformer", hidden_dim=64, num_layers=2
        )

        logits = model(sample_sequences)

        assert logits.shape == (4, 2)
        assert torch.isfinite(logits).all()

    def test_transformer_with_positional_encoding(self, sample_sequences):
        """Test TransformerRegimeDetector with positional encoding."""
        perslay = create_perslay(output_dim=64)
        model = TransformerRegimeDetector(
            perslay=perslay, d_model=64, nhead=4, num_layers=2
        )

        logits = model(sample_sequences)

        assert logits.shape == (4, 2)
        assert torch.isfinite(logits).all()

    def test_predict_methods(self, sample_sequences):
        """Test predict and predict_proba methods."""
        perslay = create_perslay(output_dim=16)
        model = create_regime_detector(perslay, model_type="lstm", hidden_dim=32)

        model.eval()
        with torch.no_grad():
            probs = model.predict_proba(sample_sequences)
            preds = model.predict(sample_sequences)

        assert probs.shape == (4, 2)
        assert torch.allclose(probs.sum(dim=1), torch.ones(4))
        assert preds.shape == (4,)
        assert preds.dtype == torch.long

    def test_model_gradient_flow(self, sample_sequences):
        """Test gradient flow through complete model."""
        perslay = create_perslay(output_dim=16)
        model = create_regime_detector(perslay, model_type="lstm")

        logits = model(sample_sequences)
        labels = torch.tensor([0, 1, 0, 1])
        loss = torch.nn.CrossEntropyLoss()(logits, labels)
        loss.backward()

        assert all(p.grad is not None for p in model.parameters() if p.requires_grad)


class TestDatasetAndLoading:
    """Tests for dataset and data loading utilities."""

    @pytest.fixture
    def sample_dataset(self):
        """Create sample PersistenceDataset."""
        torch.manual_seed(42)
        sequences = []
        for _ in range(20):
            seq = []
            for _ in range(5):
                n_points = np.random.randint(5, 15)
                diag = torch.rand(n_points, 2)
                diag[:, 1] = diag[:, 0] + torch.rand(n_points) * 0.3
                seq.append(diag)
            sequences.append(seq)
        labels = torch.randint(0, 2, (20,))
        return PersistenceDataset(sequences, labels)

    def test_dataset_creation(self, sample_dataset):
        """Test PersistenceDataset creation."""
        assert len(sample_dataset) == 20

        seq, label = sample_dataset[0]
        assert len(seq) == 5
        assert isinstance(label, torch.Tensor)

    def test_dataset_validation(self):
        """Test dataset validation with mismatched lengths."""
        sequences = [[torch.rand(5, 2)]]
        labels = torch.tensor([0, 1])  # Mismatched length

        with pytest.raises(ValueError, match="must match"):
            PersistenceDataset(sequences, labels)

    def test_collate_function(self, sample_dataset):
        """Test collate_persistence_batch function."""
        loader = torch.utils.data.DataLoader(
            sample_dataset, batch_size=4, collate_fn=collate_persistence_batch
        )

        batch_seqs, batch_labels = next(iter(loader))

        assert len(batch_seqs) == 4
        assert batch_labels.shape == (4,)
        assert all(len(seq) == 5 for seq in batch_seqs)

    def test_temporal_split(self):
        """Test train_test_split_temporal."""
        torch.manual_seed(42)
        sequences = []
        for _ in range(100):
            seq = [torch.rand(10, 2) for _ in range(5)]
            sequences.append(seq)
        labels = torch.randint(0, 2, (100,))

        train_ds, val_ds, test_ds = train_test_split_temporal(
            sequences, labels, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15
        )

        assert len(train_ds) == 70
        assert len(val_ds) == 15
        assert len(test_ds) == 15

    def test_temporal_split_validation(self):
        """Test temporal split ratio validation."""
        sequences = [[torch.rand(5, 2)]]
        labels = torch.tensor([0])

        with pytest.raises(ValueError, match="must sum to 1.0"):
            train_test_split_temporal(
                sequences, labels, train_ratio=0.5, val_ratio=0.3, test_ratio=0.3
            )


class TestTrainingPipeline:
    """Tests for training loop and utilities."""

    @pytest.fixture
    def sample_data(self):
        """Create sample training data."""
        torch.manual_seed(42)
        sequences = []
        for _ in range(40):
            seq = []
            for _ in range(5):
                n_points = np.random.randint(5, 15)
                diag = torch.rand(n_points, 2)
                diag[:, 1] = diag[:, 0] + torch.rand(n_points) * 0.3
                seq.append(diag)
            sequences.append(seq)
        labels = torch.randint(0, 2, (40,))

        train_ds, val_ds, _ = train_test_split_temporal(
            sequences, labels, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2
        )

        return train_ds, val_ds

    def test_train_epoch(self, sample_data):
        """Test single epoch training."""
        train_ds, _ = sample_data

        perslay = create_perslay(output_dim=16)
        model = create_regime_detector(perslay, model_type="lstm", hidden_dim=32)

        train_loader = torch.utils.data.DataLoader(
            train_ds, batch_size=4, collate_fn=collate_persistence_batch
        )

        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        criterion = torch.nn.CrossEntropyLoss()

        loss, acc = train_epoch(
            model, train_loader, optimizer, criterion, torch.device("cpu")
        )

        assert isinstance(loss, float)
        assert isinstance(acc, float)
        assert 0 <= acc <= 1

    def test_evaluate(self, sample_data):
        """Test model evaluation."""
        _, val_ds = sample_data

        perslay = create_perslay(output_dim=16)
        model = create_regime_detector(perslay, model_type="lstm")

        val_loader = torch.utils.data.DataLoader(
            val_ds, batch_size=4, collate_fn=collate_persistence_batch
        )

        criterion = torch.nn.CrossEntropyLoss()

        loss, acc, preds, labels = evaluate(
            model, val_loader, criterion, torch.device("cpu")
        )

        assert isinstance(loss, float)
        assert isinstance(acc, float)
        assert preds.shape == labels.shape
        assert len(preds) == len(val_ds)

    def test_early_stopping(self):
        """Test EarlyStopping functionality."""
        early_stopping = EarlyStopping(patience=3, mode="min")

        # Simulate improving validation loss
        early_stopping(1.0)
        assert not early_stopping.early_stop

        early_stopping(0.9)
        assert not early_stopping.early_stop

        # Simulate plateau
        early_stopping(0.95)
        early_stopping(0.96)
        early_stopping(0.97)
        early_stopping(0.98)

        assert early_stopping.early_stop

    def test_train_model(self, sample_data):
        """Test complete training loop."""
        train_ds, val_ds = sample_data

        perslay = create_perslay(output_dim=16)
        model = create_regime_detector(perslay, model_type="lstm", hidden_dim=32)

        history = train_model(
            model,
            train_ds,
            val_ds,
            num_epochs=3,
            batch_size=4,
            learning_rate=1e-3,
            patience=2,
            verbose=False,
        )

        assert "train_loss" in history
        assert "val_loss" in history
        assert "train_acc" in history
        assert "val_acc" in history
        assert len(history["train_loss"]) <= 3  # May stop early


class TestMetrics:
    """Tests for evaluation metrics."""

    def test_compute_metrics_basic(self):
        """Test basic metrics computation."""
        predictions = torch.tensor([0, 1, 1, 0, 1])
        labels = torch.tensor([0, 1, 0, 0, 1])

        metrics = compute_metrics(predictions, labels)

        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert 0 <= metrics["accuracy"] <= 1

    def test_compute_metrics_with_probs(self):
        """Test metrics with probabilities (AUC-ROC)."""
        predictions = torch.tensor([0, 1, 1, 0])
        labels = torch.tensor([0, 1, 0, 0])
        probs = torch.tensor([[0.8, 0.2], [0.3, 0.7], [0.4, 0.6], [0.9, 0.1]])

        metrics = compute_metrics(predictions, labels, probs)

        assert "auc_roc" in metrics
        assert 0 <= metrics["auc_roc"] <= 1 or np.isnan(metrics["auc_roc"])


class TestEndToEndIntegration:
    """End-to-end integration tests with real persistence diagrams."""

    @pytest.mark.slow
    def test_end_to_end_pipeline(self):
        """Test complete pipeline from time series to predictions."""
        np.random.seed(42)
        torch.manual_seed(42)

        # Create time series
        time_series = []
        labels = []
        for i in range(20):
            label = i % 2
            volatility = 0.1 if label == 0 else 0.3
            ts = np.sin(np.linspace(0, 2 * np.pi, 100)) + volatility * np.random.randn(
                100
            )
            time_series.append(ts)
            labels.append(label)

        # Convert to persistence diagrams
        diagrams = []
        for ts in time_series:
            pc = takens_embedding(ts, delay=5, dimension=3)
            diag = compute_persistence_vr(pc, homology_dimensions=(1,))
            h1 = diag[diag[:, 2] == 1, :2]
            diagrams.append(torch.from_numpy(h1).float())

        # Create sequences
        seq_length = 3
        sequences = []
        seq_labels = []
        for i in range(len(diagrams) - seq_length + 1):
            sequences.append(diagrams[i : i + seq_length])
            seq_labels.append(labels[i])

        seq_labels = torch.tensor(seq_labels)

        # Split data
        train_ds, val_ds, test_ds = train_test_split_temporal(
            sequences, seq_labels, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2
        )

        # Build and train model
        perslay = create_perslay(output_dim=16, perm_op="mean")
        model = create_regime_detector(perslay, model_type="lstm", hidden_dim=32)

        history = train_model(
            model, train_ds, val_ds, num_epochs=2, batch_size=2, verbose=False
        )

        # Test predictions
        test_loader = torch.utils.data.DataLoader(
            test_ds, batch_size=2, collate_fn=collate_persistence_batch
        )

        model.eval()
        all_preds = []
        with torch.no_grad():
            for batch_seqs, _ in test_loader:
                preds = model.predict(batch_seqs)
                all_preds.append(preds)

        all_preds = torch.cat(all_preds)

        assert len(all_preds) == len(test_ds)
        assert all_preds.dtype == torch.long
        assert (
            history["train_loss"][-1] < history["train_loss"][0]
            or len(history["train_loss"]) == 1
        )
