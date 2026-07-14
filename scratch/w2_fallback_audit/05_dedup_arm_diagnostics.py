# Research context: TDA-Research/00-Meta/Discovery/w2-fallback-audit-memo (WT-6 addendum)
# Purpose: Diagnose what actually differs between the 2026-05-29 (no-dedup) and
#   2026-05-30 (dedup) arms of the dedup amendment comparison. The committed
#   comparison attributes the H1 W2 flip to dedup stripping phantom features, but
#   the arms also straddle the greedy/exact solver boundary. If the null banks are
#   identical and the observed diagrams are near-identical, the flip cannot be a
#   dedup effect under an order-preserving metric.
from __future__ import annotations

import sys

import audit_lib as al
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

C29 = al.CACHE_DIR / "null_diagrams_bhps_length_matched_truncate_frozen_B1000_L5000_seed42_2026-05-29.npz"
C30 = al.CACHE_DIR / "null_diagrams_bhps_length_matched_truncate_frozen_B1000_L5000_seed42_2026-05-30.npz"

c29, c30 = al.load_cache(C29), al.load_cache(C30)
print(f"cache 05-29 sha256 {al.sha256_file(C29)}")
print(f"cache 05-30 sha256 {al.sha256_file(C30)}")

# --- Are the null banks identical? -------------------------------------------
same = 0
maxdiff = 0.0
for i in range(len(c29["h1_diagrams"])):
    a, b = c29["h1_diagrams"][i], c30["h1_diagrams"][i]
    if a.shape == b.shape:
        d = float(np.abs(a - b).max()) if a.size else 0.0
        maxdiff = max(maxdiff, d)
        if d == 0.0:
            same += 1
print(f"H1 null bank: {same}/{len(c29['h1_diagrams'])} draws byte-identical; max|diff| over same-shape = {maxdiff:.3e}")

# --- How different are the observed diagrams? --------------------------------
o29, o30 = c29["obs_h1_diagram"], c30["obs_h1_diagram"]
print(f"obs H1 card: 05-29={len(o29)}  05-30={len(o30)}  (dedup removed 139 near-duplicate LANDMARKS: 5000->4861)")
print(f"exact W2(obs_05-29, obs_05-30) = {al.exact_w2(o29, o30):.6f}   <- how far apart the two observed diagrams are")
p29 = o29[:, 1] - o29[:, 0]
p30 = o30[:, 1] - o30[:, 0]
print(f"obs H1 persistence: 05-29 sum={p29.sum():.4f} max={p29.max():.4f} n(pers<1e-6)={int((p29 < 1e-6).sum())}")
print(f"obs H1 persistence: 05-30 sum={p30.sum():.4f} max={p30.max():.4f} n(pers<1e-6)={int((p30 < 1e-6).sum())}")
print(
    f"diagonal bound (obs_29 vs mean null) = {np.mean([al.diagonal_bound(o29, nd) for nd in c29['h1_diagrams'][:50]]):.4f}"
)
