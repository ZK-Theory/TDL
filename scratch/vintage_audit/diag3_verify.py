# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: WT-1c mechanism verification — prove the committed frozen-headline H1
#   values (obs-null 233.68, null-null 175.40) are GREEDY-FALLBACK artifacts of
#   vectorisation.wasserstein_distance run without POT, not exact W2. Replicate the
#   greedy fallback and the exact path on the same diagrams; also force the fallback
#   by hiding POT and calling the real committed helper. Scratch diagnostic only.
"""WT-1c: greedy-fallback vs exact W2 — reproduce 233.68/175.40 vs the exact ~12.4."""

from __future__ import annotations

import builtins
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import _auditlib as al  # noqa: E402


def greedy_fallback(f1: np.ndarray, f2: np.ndarray, p: int = 2) -> float:
    """Exact replica of trajectory_tda.topology.vectorisation.wasserstein_distance
    fallback (lines 236-254) — greedy match by persistence rank."""
    f1 = al.finite_pairs(f1)
    f2 = al.finite_pairs(f2)
    pers1 = f1[:, 1] - f1[:, 0]
    pers2 = f2[:, 1] - f2[:, 0]
    idx1 = np.argsort(-pers1)
    idx2 = np.argsort(-pers2)
    total = 0.0
    n = min(len(idx1), len(idx2))
    for i in range(n):
        diff = np.abs(f1[idx1[i]] - f2[idx2[i]])
        total += np.sum(diff**p)
    for i in range(n, len(idx1)):
        total += (pers1[idx1[i]] / 2) ** p * 2
    for i in range(n, len(idx2)):
        total += (pers2[idx2[i]] / 2) ** p * 2
    return float(total ** (1 / p))


def exact_gudhi(f1, f2) -> float:
    from gudhi.wasserstein import wasserstein_distance

    return float(wasserstein_distance(al.finite_pairs(f1), al.finite_pairs(f2), order=2, internal_p=2))


def vect_phresult(f1, f2, dim, hide_pot=False):
    """Call the REAL committed helper vectorisation.wasserstein_distance on PHResult."""
    from poverty_tda.topology.multidim_ph import PHResult
    import trajectory_tda.topology.vectorisation as vec

    ph1 = PHResult(dgms={dim: al.finite_pairs(f1)})
    ph2 = PHResult(dgms={dim: al.finite_pairs(f2)})
    if hide_pot:
        real_import = builtins.__import__

        def fake_import(name, *a, **k):
            if name == "gudhi.wasserstein" or name.startswith("gudhi.wasserstein"):
                raise ImportError("POT hidden for diagnostic")
            return real_import(name, *a, **k)

        builtins.__import__ = fake_import
        try:
            return float(vec.wasserstein_distance(ph1, ph2, dim=dim))
        finally:
            builtins.__import__ = real_import
    return float(vec.wasserstein_distance(ph1, ph2, dim=dim))


def main() -> None:
    cache = al.load_cache(al.USOC_FROZEN_CACHE)
    orphan_h0 = al.finite_pairs(cache["obs_h0_diagram"])
    orphan_h1 = al.finite_pairs(cache["obs_h1_diagram"])
    n0, n1 = cache["h0_diagrams"], cache["h1_diagrams"]

    print("Committed frozen headline: H0 obs-null=64.2803 null-null=4.3121 | H1 obs-null=233.6846 null-null=175.3990")
    print("=" * 78)

    print("\n--- H1 obs-null W2: orphan_obs_h1 vs null_h1[i] ---")
    for i in range(2):
        e = exact_gudhi(orphan_h1, n1[i])
        g = greedy_fallback(orphan_h1, n1[i])
        v = vect_phresult(orphan_h1, n1[i], 1)
        vf = vect_phresult(orphan_h1, n1[i], 1, hide_pot=True)
        print(f"  null[{i}]: exact={e:8.4f}  greedy={g:10.4f}  vect(POT)={v:8.4f}  vect(noPOT)={vf:10.4f}")

    print("\n--- H1 null-null W2: null_h1[0] vs null_h1[j]  (committed mean 175.40) ---")
    for j in (1, 2, 3):
        e = exact_gudhi(n1[0], n1[j])
        g = greedy_fallback(n1[0], n1[j])
        print(f"  null[0]-null[{j}]: exact={e:8.4f}  greedy={g:10.4f}")

    print("\n--- H0 obs-null W2: orphan_obs_h0 vs null_h0[i]  (committed 64.28) ---")
    for i in range(2):
        e = exact_gudhi(orphan_h0, n0[i])
        g = greedy_fallback(orphan_h0, n0[i])
        print(f"  null[{i}]: exact={e:8.4f}  greedy={g:8.4f}")

    print("\n--- H0 null-null W2: null_h0[0] vs null_h0[j]  (committed 4.31) ---")
    for j in (1, 2):
        e = exact_gudhi(n0[0], n0[j])
        g = greedy_fallback(n0[0], n0[j])
        print(f"  null[0]-null[{j}]: exact={e:8.4f}  greedy={g:8.4f}")


if __name__ == "__main__":
    main()
