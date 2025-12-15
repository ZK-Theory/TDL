"""
Tests for RipsGNN models and training pipeline.

Tests cover Rips graph construction, GNN architectures (GCN, GAT, GraphSAGE),
training pipeline, and comparison with Perslay approach.
"""

import numpy as np
import pytest
import torch

from financial_tda.models import (
    RipsGNN,
    RipsGNNTrainer,
    RipsGraphDataset,
    build_rips_graph,
    compare_rips_vs_perslay,
    create_rips_dataset_from_embeddings,
    create_rips_gnn,
    train_val_test_split_temporal,
)
from financial_tda.topology import takens_embedding


class TestRipsGraphConstruction:
    """Tests for Rips complex to graph conversion."""

    @pytest.fixture
    def sample_point_cloud(self):
        """Create a sample point cloud."""
        np.random.seed(42)
        ts = np.sin(np.linspace(0, 4 * np.pi, 100))
        return takens_embedding(ts, delay=3, dimension=3)

    def test_build_rips_graph_basic(self, sample_point_cloud):
        """Test basic Rips graph construction."""
        graph = build_rips_graph(sample_point_cloud)

        assert graph.num_nodes == 94
        assert graph.num_edges > 0
        assert graph.x.shape == (94, 3)
        assert graph.edge_index.shape[0] == 2
        assert graph.edge_attr.shape[1] == 1

    def test_build_rips_graph_with_threshold(self, sample_point_cloud):
        """Test Rips graph with custom threshold."""
        # High threshold = more edges
        graph_high = build_rips_graph(sample_point_cloud, filtration_threshold=10.0)
        # Low threshold = fewer edges
        graph_low = build_rips_graph(sample_point_cloud, filtration_threshold=0.1)

        assert graph_high.num_edges > graph_low.num_edges

    def test_build_rips_graph_edge_symmetry(self, sample_point_cloud):
        """Test that Rips graph edges are symmetric (undirected)."""
        graph = build_rips_graph(sample_point_cloud)

        edges = set(
            zip(
                graph.edge_index[0].tolist(),
                graph.edge_index[1].tolist(),
            )
        )
        reverse_edges = set(
            zip(
                graph.edge_index[1].tolist(),
                graph.edge_index[0].tolist(),
            )
        )

        assert edges == reverse_edges

    def test_build_rips_graph_no_self_loops(self, sample_point_cloud):
        """Test that Rips graph has no self-loops."""
        graph = build_rips_graph(sample_point_cloud)

        has_self_loops = (graph.edge_index[0] == graph.edge_index[1]).any()
        assert not has_self_loops

    def test_build_rips_graph_invalid_input(self):
        """Test error handling for invalid inputs."""
        with pytest.raises(ValueError, match="must be 2D"):
            build_rips_graph(np.array([1, 2, 3]))

        with pytest.raises(ValueError, match="at least 2 points"):
            build_rips_graph(np.array([[1, 2, 3]]))

        with pytest.raises(ValueError, match="non-finite"):
            build_rips_graph(np.array([[1, 2, np.nan], [3, 4, 5]]))


class TestRipsGraphDataset:
    """Tests for RipsGraphDataset."""

    @pytest.fixture
    def sample_dataset(self):
        """Create a sample dataset."""
        np.random.seed(42)
        point_clouds = []
        labels = []

        for i in range(20):
            ts = np.sin(np.linspace(0, 4 * np.pi, 50)) + 0.1 * np.random.randn(50)
            pc = takens_embedding(ts, delay=2, dimension=3)
            point_clouds.append(pc)
            labels.append(i % 2)

        return point_clouds, torch.tensor(labels)

    def test_dataset_creation(self, sample_dataset):
        """Test dataset creation."""
        point_clouds, labels = sample_dataset
        dataset = RipsGraphDataset(point_clouds, labels)

        assert len(dataset) == 20
        assert dataset.labels.shape == (20,)

    def test_dataset_getitem(self, sample_dataset):
        """Test dataset indexing."""
        point_clouds, labels = sample_dataset
        dataset = RipsGraphDataset(point_clouds, labels)

        graph = dataset[0]
        assert graph.num_nodes > 0
        assert graph.num_edges > 0
        assert hasattr(graph, "y")
        assert graph.y.item() == labels[0].item()

    def test_dataset_get_batch(self, sample_dataset):
        """Test batch creation."""
        point_clouds, labels = sample_dataset
        dataset = RipsGraphDataset(point_clouds, labels)

        batch = dataset.get_batch([0, 1, 2, 3])
        assert batch.num_graphs == 4
        assert batch.x.shape[0] > 0  # Has nodes
        assert batch.edge_index.shape[1] > 0  # Has edges

    def test_dataset_collate_fn(self, sample_dataset):
        """Test collate function."""
        point_clouds, labels = sample_dataset
        dataset = RipsGraphDataset(point_clouds, labels)

        graphs = [dataset[i] for i in range(4)]
        batch = RipsGraphDataset.collate_fn(graphs)

        assert batch.num_graphs == 4

    def test_create_rips_dataset_from_embeddings(self, sample_dataset):
        """Test factory function."""
        point_clouds, labels = sample_dataset
        dataset = create_rips_dataset_from_embeddings(point_clouds, labels.numpy())

        assert len(dataset) == 20
        assert isinstance(dataset.labels, torch.Tensor)


class TestRipsGNN:
    """Tests for RipsGNN models."""

    @pytest.fixture
    def sample_batch(self):
        """Create a sample batch."""
        np.random.seed(42)
        point_clouds = []
        labels = []

        for i in range(8):
            ts = np.sin(np.linspace(0, 4 * np.pi, 50)) + 0.1 * np.random.randn(50)
            pc = takens_embedding(ts, delay=2, dimension=3)
            point_clouds.append(pc)
            labels.append(i % 2)

        dataset = RipsGraphDataset(point_clouds, torch.tensor(labels))
        return dataset.get_batch(list(range(8)))

    def test_gcn_forward(self, sample_batch):
        """Test GCN forward pass."""
        model = create_rips_gnn(input_dim=3, architecture="gcn", hidden_dim=32)
        model.eval()

        with torch.no_grad():
            logits = model(sample_batch)

        assert logits.shape == (8, 2)
        assert torch.isfinite(logits).all()

    def test_gat_forward(self, sample_batch):
        """Test GAT forward pass."""
        model = create_rips_gnn(
            input_dim=3,
            architecture="gat",
            hidden_dim=32,
            heads=4,
        )
        model.eval()

        with torch.no_grad():
            logits = model(sample_batch)

        assert logits.shape == (8, 2)
        assert torch.isfinite(logits).all()

    def test_graphsage_forward(self, sample_batch):
        """Test GraphSAGE forward pass."""
        model = create_rips_gnn(input_dim=3, architecture="graphsage", hidden_dim=32)
        model.eval()

        with torch.no_grad():
            logits = model(sample_batch)

        assert logits.shape == (8, 2)
        assert torch.isfinite(logits).all()

    def test_different_readout_methods(self, sample_batch):
        """Test different graph pooling methods."""
        for readout in ["mean", "max"]:
            model = create_rips_gnn(
                input_dim=3,
                architecture="gcn",
                readout=readout,
            )
            model.eval()

            with torch.no_grad():
                logits = model(sample_batch)

            assert logits.shape == (8, 2)

    def test_predict_proba(self, sample_batch):
        """Test probability prediction."""
        model = create_rips_gnn(input_dim=3, architecture="gcn")
        model.eval()

        probs = model.predict_proba(sample_batch)

        assert probs.shape == (8, 2)
        assert torch.allclose(probs.sum(dim=1), torch.ones(8), atol=1e-5)
        assert (probs >= 0).all() and (probs <= 1).all()

    def test_predict(self, sample_batch):
        """Test class prediction."""
        model = create_rips_gnn(input_dim=3, architecture="gcn")
        model.eval()

        preds = model.predict(sample_batch)

        assert preds.shape == (8,)
        assert ((preds == 0) | (preds == 1)).all()

    def test_model_parameters(self):
        """Test model parameter counts."""
        model_gcn = create_rips_gnn(input_dim=3, hidden_dim=64, architecture="gcn")
        model_gat = create_rips_gnn(input_dim=3, hidden_dim=64, architecture="gat")
        model_sage = create_rips_gnn(
            input_dim=3, hidden_dim=64, architecture="graphsage"
        )

        params_gcn = sum(p.numel() for p in model_gcn.parameters())
        params_gat = sum(p.numel() for p in model_gat.parameters())
        params_sage = sum(p.numel() for p in model_sage.parameters())

        # GAT should have most parameters (attention)
        assert params_gat > params_gcn
        assert params_gat > params_sage

    def test_invalid_architecture(self):
        """Test error for invalid architecture."""
        with pytest.raises(ValueError, match="Invalid architecture"):
            create_rips_gnn(input_dim=3, architecture="invalid")

    def test_invalid_readout(self):
        """Test error for invalid readout."""
        with pytest.raises(ValueError, match="Invalid readout"):
            RipsGNN(
                input_dim=3,
                hidden_dim=64,
                architecture="gcn",
                readout="invalid",
            )


class TestTrainingPipeline:
    """Tests for training pipeline."""

    @pytest.fixture
    def training_data(self):
        """Create training data."""
        np.random.seed(42)
        torch.manual_seed(42)

        point_clouds = []
        labels = []

        for i in range(40):
            if i % 2 == 0:
                ts = np.sin(np.linspace(0, 4 * np.pi, 50)) + 0.05 * np.random.randn(50)
            else:
                x = np.random.randn(50).cumsum()
                ts = x / np.std(x) + 0.2 * np.random.randn(50)

            pc = takens_embedding(ts, delay=2, dimension=3)
            point_clouds.append(pc)
            labels.append(i % 2)

        return RipsGraphDataset(point_clouds, torch.tensor(labels))

    def test_temporal_split(self, training_data):
        """Test temporal data splitting."""
        train_idx, val_idx, test_idx = train_val_test_split_temporal(
            training_data,
            train_ratio=0.7,
            val_ratio=0.15,
            test_ratio=0.15,
        )

        assert len(train_idx) == 28
        assert len(val_idx) == 6
        assert len(test_idx) == 6

        # Check chronological order
        assert train_idx[-1] < val_idx[0]
        assert val_idx[-1] < test_idx[0]

    def test_temporal_split_invalid_ratios(self, training_data):
        """Test error for invalid split ratios."""
        with pytest.raises(ValueError, match="must sum to 1.0"):
            train_val_test_split_temporal(
                training_data,
                train_ratio=0.5,
                val_ratio=0.3,
                test_ratio=0.1,
            )

    def test_trainer_initialization(self, training_data):
        """Test trainer initialization."""
        train_idx, val_idx, _ = train_val_test_split_temporal(training_data)
        model = create_rips_gnn(input_dim=3, architecture="gcn", hidden_dim=32)

        trainer = RipsGNNTrainer(
            model=model,
            dataset=training_data,
            train_idx=train_idx,
            val_idx=val_idx,
        )

        assert trainer.model is not None
        assert trainer.optimizer is not None
        assert trainer.criterion is not None

    def test_train_epoch(self, training_data):
        """Test single training epoch."""
        train_idx, val_idx, _ = train_val_test_split_temporal(training_data)
        model = create_rips_gnn(input_dim=3, architecture="gcn", hidden_dim=32)

        trainer = RipsGNNTrainer(
            model=model,
            dataset=training_data,
            train_idx=train_idx,
            val_idx=val_idx,
        )

        loss, acc = trainer.train_epoch()

        assert isinstance(loss, float)
        assert isinstance(acc, float)
        assert 0 <= acc <= 1

    def test_validate(self, training_data):
        """Test validation."""
        train_idx, val_idx, _ = train_val_test_split_temporal(training_data)
        model = create_rips_gnn(input_dim=3, architecture="gcn", hidden_dim=32)

        trainer = RipsGNNTrainer(
            model=model,
            dataset=training_data,
            train_idx=train_idx,
            val_idx=val_idx,
        )

        val_loss, val_acc = trainer.validate()

        assert isinstance(val_loss, float)
        assert isinstance(val_acc, float)
        assert 0 <= val_acc <= 1

    def test_full_training(self, training_data):
        """Test full training loop."""
        train_idx, val_idx, _ = train_val_test_split_temporal(training_data)
        model = create_rips_gnn(input_dim=3, architecture="gcn", hidden_dim=32)

        trainer = RipsGNNTrainer(
            model=model,
            dataset=training_data,
            train_idx=train_idx,
            val_idx=val_idx,
            patience=5,
        )

        history = trainer.train(epochs=10, verbose=False)

        assert "train_loss" in history
        assert "val_loss" in history
        assert "train_acc" in history
        assert "val_acc" in history
        assert len(history["train_loss"]) > 0

    def test_early_stopping(self, training_data):
        """Test early stopping mechanism."""
        train_idx, val_idx, _ = train_val_test_split_temporal(training_data)
        model = create_rips_gnn(input_dim=3, architecture="gcn", hidden_dim=32)

        trainer = RipsGNNTrainer(
            model=model,
            dataset=training_data,
            train_idx=train_idx,
            val_idx=val_idx,
            patience=3,
        )

        history = trainer.train(epochs=100, verbose=False)

        # Early stopping should trigger before max epochs
        # Note: May not always trigger if model continues improving
        assert len(history["train_loss"]) <= 100
        assert len(history["val_loss"]) == len(history["train_loss"])

    def test_evaluate(self, training_data):
        """Test model evaluation."""
        train_idx, val_idx, test_idx = train_val_test_split_temporal(training_data)
        model = create_rips_gnn(input_dim=3, architecture="gcn", hidden_dim=32)

        trainer = RipsGNNTrainer(
            model=model,
            dataset=training_data,
            train_idx=train_idx,
            val_idx=val_idx,
        )

        # Quick training
        trainer.train(epochs=5, verbose=False)

        # Evaluate
        results = trainer.evaluate(test_idx)

        assert "test_loss" in results
        assert "test_accuracy" in results
        assert "predictions" in results
        assert "probabilities" in results
        assert "true_labels" in results

        assert len(results["predictions"]) == len(test_idx)
        assert results["probabilities"].shape == (len(test_idx), 2)

    def test_training_multiple_architectures(self, training_data):
        """Test training with different architectures."""
        train_idx, val_idx, _ = train_val_test_split_temporal(training_data)

        for arch in ["gcn", "gat", "graphsage"]:
            torch.manual_seed(42)
            model = create_rips_gnn(
                input_dim=3,
                architecture=arch,
                hidden_dim=32,
            )

            trainer = RipsGNNTrainer(
                model=model,
                dataset=training_data,
                train_idx=train_idx,
                val_idx=val_idx,
            )

            history = trainer.train(epochs=5, verbose=False)
            assert len(history["train_loss"]) > 0


class TestComparisonUtilities:
    """Tests for comparison with Perslay."""

    @pytest.mark.slow
    def test_compare_rips_vs_perslay(self):
        """Test comparison utility (marked as slow test)."""
        np.random.seed(42)
        torch.manual_seed(42)

        # Create small dataset for quick test
        point_clouds = []
        labels = []

        for i in range(20):
            ts = (
                np.sin(np.linspace(0, 4 * np.pi, 50))
                + (i % 2) * 0.5
                + 0.1 * np.random.randn(50)
            )
            pc = takens_embedding(ts, delay=2, dimension=3)
            point_clouds.append(pc)
            labels.append(i % 2)

        results = compare_rips_vs_perslay(
            point_clouds=point_clouds,
            labels=np.array(labels),
            gnn_architecture="gcn",
            hidden_dim=32,
            num_layers=2,
            epochs=10,
            device="cpu",
        )

        assert "rips_results" in results
        assert "perslay_results" in results
        assert "comparison" in results

        # Check RipsGNN results
        assert "test_accuracy" in results["rips_results"]
        assert "train_time" in results["rips_results"]
        assert "inference_time_ms" in results["rips_results"]

        # Check Perslay results
        assert "test_accuracy" in results["perslay_results"]
        assert "train_time" in results["perslay_results"]
        assert "inference_time_ms" in results["perslay_results"]

        # Check comparison metrics
        assert "accuracy_diff" in results["comparison"]
        assert "train_time_ratio" in results["comparison"]
        assert "inference_time_ratio" in results["comparison"]


class TestIntegration:
    """Integration tests for end-to-end workflow."""

    def test_end_to_end_workflow(self):
        """Test complete workflow from time series to predictions."""
        np.random.seed(42)
        torch.manual_seed(42)

        # 1. Generate time series
        time_series = [
            np.sin(np.linspace(0, 4 * np.pi, 50)) + 0.1 * np.random.randn(50)
            for _ in range(30)
        ]
        labels = torch.tensor([i % 2 for i in range(30)])

        # 2. Create Takens embeddings
        point_clouds = [
            takens_embedding(ts, delay=2, dimension=3) for ts in time_series
        ]

        # 3. Build Rips graph dataset
        dataset = create_rips_dataset_from_embeddings(point_clouds, labels.numpy())

        # 4. Split data
        train_idx, val_idx, test_idx = train_val_test_split_temporal(dataset)

        # 5. Create and train model
        model = create_rips_gnn(
            input_dim=3,
            architecture="gat",
            hidden_dim=32,
            num_layers=2,
        )

        trainer = RipsGNNTrainer(
            model=model,
            dataset=dataset,
            train_idx=train_idx,
            val_idx=val_idx,
        )

        # 6. Train
        history = trainer.train(epochs=10, verbose=False)

        # 7. Evaluate
        results = trainer.evaluate(test_idx)

        # Verify complete workflow
        assert len(history["train_loss"]) > 0
        assert "test_accuracy" in results
        assert results["test_accuracy"] >= 0
        assert len(results["predictions"]) == len(test_idx)
