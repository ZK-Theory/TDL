# Research context: TDA-Research/00-Meta/Discovery/w2-fallback-audit-memo (WT-6)
# Purpose: Exact-W2 re-derivation worker for one disjoint block of pairs.
#   Exact EMD is memory-bandwidth-bound and scales NEGATIVELY under loky/threads
#   (WT-1c), so parallelism is by independent OS processes over disjoint blocks,
#   each checkpointing to its own npz and resumable after interruption.
#
# Usage (one process per block):
#   python 01_recompute_block.py --cache <npz> --dim 1 --kind obs_null \
#       --start 0 --end 250 --out ckpt/bhps_frozen_h1_obsnull_000_250.npz

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import audit_lib as al
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Exact-W2 re-derivation worker (one block).")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--dim", type=int, required=True, choices=[0, 1])
    ap.add_argument("--kind", required=True, choices=["obs_null", "null_null"])
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--checkpoint-every", type=int, default=25)
    ap.add_argument("--benchmark", type=int, default=0, help="If >0, time this many pairs and exit.")
    args = ap.parse_args()

    cache = al.load_cache(Path(args.cache))
    nulls = cache[f"h{args.dim}_diagrams"]
    obs = cache[f"obs_h{args.dim}_diagram"]
    n_perm = len(nulls)

    if args.kind == "obs_null":
        items: list = list(range(args.start, args.end))

        def compute(item: int) -> float:
            return al.exact_w2(obs, nulls[item])
    else:
        pairs = al.reproduce_pair_indices(n_perm, max(al.DEFAULT_N_NULL_PAIRS, n_perm), args.seed)
        items = pairs[args.start : args.end]

        def compute(item: tuple[int, int]) -> float:
            return al.exact_w2(nulls[item[0]], nulls[item[1]])

    if args.benchmark:
        t0 = time.time()
        for it in items[: args.benchmark]:
            compute(it)
        per = (time.time() - t0) / args.benchmark
        print(
            f"BENCHMARK {args.kind} dim={args.dim}: {per:.3f}s/pair (obs card={len(obs)}, null card~{len(nulls[0])})",
            flush=True,
        )
        return

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    values: list[float] = []
    done = 0
    if out.exists():
        with np.load(out) as d:
            values = [float(x) for x in d["values"]]
            done = int(d["done"])
        print(f"[resume] {out.name}: {done}/{len(items)} already done", flush=True)

    t0 = time.time()
    for k in range(done, len(items)):
        values.append(compute(items[k]))
        n_new = k + 1 - done
        if (k + 1) % args.checkpoint_every == 0 or (k + 1) == len(items):
            np.savez(out, values=np.array(values, dtype=np.float64), done=k + 1, start=args.start, end=args.end)
            rate = (time.time() - t0) / max(n_new, 1)
            remaining = (len(items) - (k + 1)) * rate
            print(
                f"[{args.kind} d{args.dim} {args.start}:{args.end}] {k + 1}/{len(items)} "
                f"{rate:.2f}s/pair eta={remaining / 60:.1f}min",
                flush=True,
            )

    print(f"BLOCK DONE {args.kind} d{args.dim} {args.start}:{args.end} n={len(values)}", flush=True)


if __name__ == "__main__":
    main()
