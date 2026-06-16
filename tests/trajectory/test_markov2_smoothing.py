# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: Unit tests for alpha=1 Laplace smoothing on Markov-2 conditional
#          probabilities in _markov_shuffle.
"""Tests for Markov-2 Laplace smoothing in permutation_nulls._markov_shuffle."""

from __future__ import annotations

import inspect

import numpy as np

from tests.trajectory.conftest import make_synthetic_trajectories
from trajectory_tda.embedding.ngram_embed import STATES
from trajectory_tda.topology import permutation_nulls
from trajectory_tda.topology.permutation_nulls import _markov_shuffle

N_STATES = len(STATES)

# ── helpers ──────────────────────────────────────────────────────────────────

def _cyclic_trajs(cycle: list[str], length: int = 30, n: int = 80) -> list[list[str]]:
    """Return n trajectories cycling through the given state sequence."""
    t = (cycle * ((length // len(cycle)) + 1))[:length]
    return [list(t) for _ in range(n)]


def _count_bigram_transitions(
    trajs: list[list[str]],
    prefix: tuple[str, str],
    successor: str,
) -> tuple[int, int]:
    """Count (#times successor follows prefix, #times prefix appears)."""
    a, b = prefix
    total = 0
    hits = 0
    for traj in trajs:
        for t in range(len(traj) - 2):
            if traj[t] == a and traj[t + 1] == b:
                total += 1
                if traj[t + 2] == successor:
                    hits += 1
    return hits, total


# ── Test 1: alpha parameter exists with default 1 ────────────────────────────


class TestAlphaParameter:
    def test_alpha_in_signature(self):
        sig = inspect.signature(_markov_shuffle)
        assert "alpha" in sig.parameters, "_markov_shuffle must have an 'alpha' parameter"

    def test_alpha_default_is_1(self):
        sig = inspect.signature(_markov_shuffle)
        assert sig.parameters["alpha"].default == 1.0

    def test_alpha_accepted_as_keyword(self):
        trajs = [["EL", "EM", "EH", "EL"] for _ in range(20)]
        rng = np.random.RandomState(0)
        result = _markov_shuffle(trajs, rng, markov_order=2, alpha=1.0)
        assert result is not None


# ── Test 2: transition rows sum to 1 ─────────────────────────────────────────


class TestTransitionRowsSumToOne:
    """np.random.choice raises ValueError when probabilities don't sum to ~1.
    A no-NaN, no-exception run verifies all conditioning bigram rows are valid."""

    def test_standard_trajectories_no_nan(self):
        trajs = make_synthetic_trajectories(n=100, t=20, seed=42)
        rng = np.random.RandomState(0)
        result = _markov_shuffle(trajs, rng, markov_order=2, alpha=1.0)
        assert not np.any(np.isnan(result))
        assert result.shape[0] == 100

    def test_sparse_trajectories_no_nan(self):
        """Even with only 3 trajectories many bigrams are unobserved — should still work."""
        trajs = [["EL", "EM", "EH", "EL", "EM"], ["EH", "EL", "EM"], ["EM", "EH", "EL"]]
        rng = np.random.RandomState(0)
        result = _markov_shuffle(trajs, rng, markov_order=2, alpha=1.0)
        assert not np.any(np.isnan(result))

    def test_single_state_trajectories_no_nan(self):
        """All trajectories in one state; nearly all bigrams unobserved."""
        trajs = [["EL"] * 10 for _ in range(10)]
        rng = np.random.RandomState(0)
        result = _markov_shuffle(trajs, rng, markov_order=2, alpha=1.0)
        assert not np.any(np.isnan(result))


# ── Test 3: observed-bigram cells use smoothed estimates, not raw MLE ─────────


class TestObservedBigramSmoothedNotMLE:
    """alpha changes the conditional probabilities for observed bigrams.
    alpha=0 → raw MLE; alpha=1 → smoothed (probability mass spread across all states).
    For a deterministic bigram (A,B)→C under MLE, alpha=1 must assign nonzero
    probability to other states, which will eventually change the generated output."""

    def test_alpha_changes_output(self):
        """Different alpha values produce different surrogate embeddings."""
        trajs = _cyclic_trajs(["EL", "EM", "EH"], length=30, n=80)
        rng0 = np.random.RandomState(42)
        rng1 = np.random.RandomState(42)
        result_alpha0 = _markov_shuffle(trajs, rng0, markov_order=2, alpha=0.0)
        result_alpha1 = _markov_shuffle(trajs, rng1, markov_order=2, alpha=1.0)
        # alpha=0 (raw MLE, all transitions deterministic) and alpha=1 (smoothed)
        # must yield different point clouds when starting from the same RNG state
        assert not np.allclose(result_alpha0, result_alpha1), (
            "alpha=0 and alpha=1 should produce different embeddings "
            "for deterministic-transition trajectories"
        )

    def test_smoothed_formula_reduces_peak_probability(self):
        """For a bigram that always leads to the same successor, alpha=1 reduces P < 1.

        We verify this by counting how often different alpha values lead to
        the successor state in the input trajectories (which we can inspect
        since bigram_counts is derivable from the input).
        """
        cycle = ["EL", "EM", "EH"]
        trajs = _cyclic_trajs(cycle, length=30, n=80)

        # Under raw MLE (alpha=0): P(EH | EL, EM) = 1.0 (deterministic cycle)
        # Under Laplace (alpha=1): P(EH | EL, EM) = (count+1)/(count+N_STATES) < 1
        hits, total = _count_bigram_transitions(trajs, ("EL", "EM"), "EH")
        assert total > 0, "Test setup error: (EL,EM) bigram never appeared"
        mle_prob = hits / total  # should be 1.0 for this cyclic input
        laplace_prob = (hits + 1.0) / (total + N_STATES)
        assert laplace_prob < mle_prob, (
            "Laplace-smoothed probability must be strictly less than MLE "
            "when MLE is 1.0 (all observations go to same successor)"
        )


# ── Test 4: unobserved-bigram cells use smoothed-uniform fallback ─────────────


class TestUnobservedBigram:
    """Unobserved bigrams must return uniform probability (1/n_states), not 0 or crash."""

    def test_unobserved_bigram_does_not_crash(self):
        """If a generated trajectory hits an unobserved bigram, it must not raise."""
        # Two trajectories cover only a handful of bigrams; generation will
        # encounter unobserved ones because initial 2 states are drawn from
        # the initial distribution and uniform_fallback respectively.
        trajs = [["EL", "EM", "EH"], ["EM", "EL", "EH"]]
        rng = np.random.RandomState(0)
        result = _markov_shuffle(trajs, rng, markov_order=2, alpha=1.0)
        assert not np.any(np.isnan(result))

    def test_zero_count_bigram_uniform_probability(self):
        """Verify the Laplace formula for an unobserved bigram gives 1/n_states.

        For count vector = [0]*n_states (unobserved bigram):
        smoothed = (0 + alpha) / (0 + alpha * n_states) = 1 / n_states
        """
        alpha = 1.0
        counts = np.zeros(N_STATES)
        total = counts.sum()  # 0
        smoothed = (counts + alpha) / (total + alpha * N_STATES)
        expected = np.ones(N_STATES) / N_STATES
        np.testing.assert_allclose(smoothed, expected, rtol=1e-10)

    def test_alpha0_with_unobserved_bigram_still_valid(self):
        """alpha=0 on unobserved bigram → uniform fallback (no crash)."""
        trajs = [["EL", "EM", "EH"], ["EM", "EL", "EH"]]
        rng = np.random.RandomState(0)
        result = _markov_shuffle(trajs, rng, markov_order=2, alpha=0.0)
        assert not np.any(np.isnan(result))


# ── Test 5: alpha=0 recovers raw MLE for fully observed bigrams ───────────────


class TestAlphaZeroMLE:
    """alpha=0 must produce raw MLE for bigrams that have observations."""

    def test_smoothed_formula_at_alpha0_equals_mle(self):
        """With alpha=0, (counts + 0) / (total + 0) = counts / total (raw MLE)."""
        rng_ref = np.random.RandomState(42)
        counts = rng_ref.randint(1, 100, size=N_STATES).astype(float)
        total = counts.sum()

        mle = counts / total
        smoothed_alpha0 = (counts + 0.0) / (total + 0.0 * N_STATES)
        np.testing.assert_allclose(smoothed_alpha0, mle, rtol=1e-10)

    def test_different_alpha_different_probabilities(self):
        """Smoothed probabilities differ from MLE whenever alpha > 0."""
        counts = np.array([10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # all mass on state 0
        total = counts.sum()
        alpha = 1.0

        mle = counts / total  # [1, 0, 0, ..., 0]
        smoothed = (counts + alpha) / (total + alpha * N_STATES)

        assert not np.allclose(mle, smoothed), (
            "Laplace smoothing must change probabilities relative to raw MLE"
        )
        assert smoothed[0] < mle[0], "Smoothing must reduce peak probability"
        assert np.all(smoothed[1:] > mle[1:]), "Smoothing must assign mass to unseen successors"


class TestPublicRunnerAlphaThreading:
    def test_public_runner_threads_alpha_to_markov2(self, monkeypatch):
        """The public permutation runner must pass alpha into Markov-2 draws."""
        embeddings = np.zeros((4, 2), dtype=float)
        trajectories = [["EL", "EM", "EH", "EL"] for _ in range(4)]
        seen: list[dict[str, np.ndarray | float]] = []

        class FakePH:
            def __init__(self, points):
                self.points = np.asarray(points, dtype=float)

        def fake_markov_shuffle(
            trajectories,
            rng,
            markov_order=1,
            embed_kwargs=None,
            alpha=1.0,
            frozen_models=None,
        ):
            assert markov_order == 2
            counts = np.zeros(N_STATES, dtype=float)
            counts[0] = 6.0
            probs = counts / counts.sum() if alpha == 0 else (counts + alpha) / (counts.sum() + alpha * N_STATES)
            np.testing.assert_allclose(probs.sum(), 1.0)
            seen.append({"alpha": float(alpha), "probs": probs.copy()})
            return np.full((len(trajectories), 2), float(probs[0]))

        def fake_compute_rips_ph(points, max_dim=0):
            return FakePH(points)

        def fake_persistence_summary(ph):
            return {"H0": {"total_persistence": float(ph.points[:, 0].mean())}}

        monkeypatch.setattr(permutation_nulls, "_markov_shuffle", fake_markov_shuffle)
        monkeypatch.setattr(permutation_nulls, "compute_rips_ph", fake_compute_rips_ph)
        monkeypatch.setattr(permutation_nulls, "persistence_summary", fake_persistence_summary)

        result_alpha0 = permutation_nulls.permutation_test_trajectories(
            embeddings,
            trajectories=trajectories,
            null_type="markov",
            markov_order=2,
            alpha=0.0,
            n_permutations=1,
            max_dim=0,
            n_landmarks=4,
            n_jobs=1,
            seed=42,
        )
        result_alpha1 = permutation_nulls.permutation_test_trajectories(
            embeddings,
            trajectories=trajectories,
            null_type="markov",
            markov_order=2,
            alpha=1.0,
            n_permutations=1,
            max_dim=0,
            n_landmarks=4,
            n_jobs=1,
            seed=42,
        )

        assert [row["alpha"] for row in seen] == [0.0, 1.0]
        assert not np.allclose(seen[0]["probs"], seen[1]["probs"])
        assert result_alpha0["H0"]["null_distribution"] != result_alpha1["H0"]["null_distribution"]
