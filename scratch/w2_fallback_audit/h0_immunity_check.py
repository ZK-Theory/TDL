# Research context: TDA-Research/00-Meta/Discovery/w2-fallback-audit-memo (WT-6)
# Purpose: Test the H0-immunity claim empirically per cache instead of assuming it.
#   Theory says births all 0 => rank-matching is optimal 1-D transport (greedy==exact),
#   but that holds only when the matching structure makes rank-order optimal; unequal
#   cardinality can make greedy's diagonal assignment suboptimal.
import sys
import numpy as np
import audit_lib as al

sys.stdout.reconfigure(encoding="utf-8")

CASES = [
    ("usoc_frozen_2026-05-28", "null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-28.npz"),
    ("bhps_frozen_2026-05-28", "null_diagrams_bhps_frozen_B1000_L5000_seed42_2026-05-28.npz"),
    ("bhps_2026-05-24", "null_diagrams_bhps_B1000_L5000_seed42_2026-05-24.npz"),
    (
        "bhps_lm_truncate_frozen_2026-05-29",
        "null_diagrams_bhps_length_matched_truncate_frozen_B1000_L5000_seed42_2026-05-29.npz",
    ),
]
N = 6
for label, cname in CASES:
    cache = al.load_cache(al.CACHE_DIR / cname)
    obs, nulls = cache["obs_h0_diagram"], cache["h0_diagrams"]
    cards = np.array([len(nd) for nd in nulls[:N]])
    ex = al.obs_null_distances(obs, nulls[:N], "exact")
    gr = al.obs_null_distances(obs, nulls[:N], "greedy")
    d = np.abs(ex - gr)
    print(
        f"[{label}] H0 obs_card={len(obs)} null_cards={cards.tolist()} "
        f"max|exact-greedy|={d.max():.3e} rel={d.max() / max(ex.mean(), 1e-12):.2e}",
        flush=True,
    )
