"""Run the locked MCbiF deprivation scale-coherence confirmatory battery."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import os
import shutil
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score

from poverty_tda.topology.deprivation_scale_coherence import (
    ALPHA,
    B_LOCKED,
    IMD_SHA256,
    KS,
    LSOA_SHA256,
    SCHEMA_VERSION,
    SEED,
    benjamini_hochberg,
    empirical_tail_pvalues,
    null_validity_record,
    redundancy_record,
    scale_coherence_statistic,
    spatialised_null_draw,
    validate_result_payload,
)

LAD_CODE_COL = "Local Authority District code (2024)"
LAD_NAME_COL = "Local Authority District name (2024)"
LAD_FLOOR = 150
DOMAINS = [
    "Income Score (rate)",
    "Employment Score (rate)",
    "Education, Skills and Training Score",
    "Health Deprivation and Disability Score",
    "Crime Score",
    "Barriers to Housing and Services Score",
    "Living Environment Score",
]
LSOA_COL = "LSOA code (2021)"
SPIKE_LAD_CODES = [
    "E08000025",  # Birmingham
    "E08000035",  # Leeds
    "E06000065",  # North Yorkshire
    "E08000019",  # Sheffield
    "E06000066",  # Somerset
    "E06000052",  # Cornwall
]
REPO_ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedLad:
    """In-memory LAD inputs with fixed queen closed-neighbourhood indices."""

    lad_code: str
    lad_name: str
    raw: NDArray[np.float64]
    closed_neighbours: list[NDArray[np.intp]]
    n_islands: int


def enumerate_eligible_lads(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Return the complete deterministic 2024-code LAD family at the locked floor."""
    required = {LAD_CODE_COL, LAD_NAME_COL}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"IMD frame lacks LAD columns: {sorted(missing)}")
    counts = frame.groupby([LAD_CODE_COL, LAD_NAME_COL], dropna=False).size()
    eligible = counts[counts >= LAD_FLOOR]
    return [
        {"lad_code": str(code), "lad_name": str(name), "n_lsoas": int(count)}
        for (code, name), count in eligible.sort_index().items()
    ]


def _project_root() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    common = Path(completed.stdout.strip())
    if not common.is_absolute():
        common = (REPO_ROOT / common).resolve()
    return common.parent


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_once(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != encoded:
            raise FileExistsError(f"refusing to overwrite a different artifact: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(path)


def freeze_lad_family(family: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    """Persist Gate 0 before any statistic or p-value is evaluated."""
    canonical = json.dumps(family, sort_keys=True, separators=(",", ":")).encode()
    payload = {
        "schema_version": "deprivation-scale-coherence-family/v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "lad_floor": LAD_FLOOR,
        "eligible_count": len(family),
        "members": family,
        "family_sha256": hashlib.sha256(canonical).hexdigest(),
        "contains_p_values": False,
    }
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("members") != family or existing.get("lad_floor") != LAD_FLOOR:
            raise ValueError("existing frozen LAD family differs from deterministic Gate 0")
        return existing
    _write_json_once(path, payload)
    return payload


def build_staged_launch_plan(
    frozen_family: dict[str, Any],
    preflight: dict[str, Any],
    *,
    approved_at: str,
) -> dict[str, Any]:
    """Build the approved exact-three-batch plan without changing the frozen family."""
    members = frozen_family["members"]
    if frozen_family["eligible_count"] != 69 or len(members) != 69:
        raise ValueError("staged launch requires the locked 69-LAD frozen family")
    if preflight["decision"]["status"] != "STOP":
        raise ValueError("staged launch is only valid after the preregistered full-launch stop")

    batches: list[list[dict[str, Any]]] = [[], [], []]
    batch_lsoa_counts = [0, 0, 0]
    ordered = sorted(members, key=lambda member: (-member["n_lsoas"], member["lad_code"]))
    for member in ordered:
        available = [index for index, batch in enumerate(batches) if len(batch) < 23]
        batch_index = min(available, key=lambda index: (batch_lsoa_counts[index], index))
        batches[batch_index].append(member)
        batch_lsoa_counts[batch_index] += member["n_lsoas"]

    if any(len(batch) != 23 for batch in batches):
        raise RuntimeError("staged partition did not produce three exact 23-LAD batches")
    projected_hours = float(preflight["estimated_wall_time_hours"])
    return {
        "schema_version": "deprivation-scale-coherence-staged-plan/v1",
        "family_sha256": frozen_family["family_sha256"],
        "eligible_count": frozen_family["eligible_count"],
        "batch_count": 3,
        "assignment": (
            "descending (-n_lsoas, lad_code) least-loaded assignment with a hard 23-LAD capacity; "
            "ties resolve by batch index and batch 1 starts with the largest LAD"
        ),
        "approval": {
            "approved_at": approved_at,
            "approved_by": "User",
            "instruction": "Approve staged launch",
        },
        "locked_compute_contract": {
            "B": B_LOCKED,
            "per_draw_seeds": "42+b for b=0..998",
            "workers": 8,
            "statistic_and_null_unchanged": True,
            "bh_family_sha256": frozen_family["family_sha256"],
        },
        "inference_deferred_until_all_batches_complete": True,
        "projected_total_hours": projected_hours,
        "batches": [
            {
                "batch_index": index,
                "member_count": len(batch),
                "lsoa_count": sum(member["n_lsoas"] for member in batch),
                "projected_hours": projected_hours * len(batch) / len(members),
                "members": batch,
            }
            for index, batch in enumerate(batches, start=1)
        ],
    }


def prepare_staged_batch_artifact(
    rows: list[dict[str, Any]],
    *,
    plan: dict[str, Any],
    batch_index: int,
    elapsed_seconds: float,
) -> dict[str, Any]:
    """Remove family inference and wrap one completed staged batch."""
    batch = next((item for item in plan["batches"] if item["batch_index"] == batch_index), None)
    if batch is None:
        raise ValueError(f"batch index {batch_index} is not in the staged plan")
    expected_codes = [member["lad_code"] for member in batch["members"]]
    if [row["lad_code"] for row in rows] != expected_codes:
        raise ValueError("batch rows do not exactly match the staged plan order")
    expected_draws = int(plan["locked_compute_contract"]["B"])
    expected_seeds = list(range(SEED, SEED + expected_draws))
    if any(len(row["null_h1_total_area"]) != expected_draws or row["draw_seeds"] != expected_seeds for row in rows):
        raise ValueError("batch rows do not contain the complete locked null-draw sequence")

    staged_rows = copy.deepcopy(rows)
    for row in staged_rows:
        for key in ("p_lower", "p_upper", "p_fdr", "rejects_lower_fdr"):
            row.pop(key, None)
        row["null_summary"].pop("observed_percentile", None)
    return {
        "schema_version": "deprivation-scale-coherence-staged-batch/v1",
        "family_sha256": plan["family_sha256"],
        "batch_index": batch_index,
        "batch_count": plan["batch_count"],
        "member_count": len(staged_rows),
        "members": batch["members"],
        "params": plan["locked_compute_contract"],
        "contains_family_inference": False,
        "elapsed_seconds": elapsed_seconds,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": staged_rows,
    }


def load_staged_batch_rows(plan: dict[str, Any], batch_root: Path) -> tuple[list[dict[str, Any]], float]:
    """Load only a complete, exact cover of the approved staged family."""
    rows: list[dict[str, Any]] = []
    elapsed_seconds = 0.0
    seen_codes: set[str] = set()
    for batch in plan["batches"]:
        path = batch_root / f"batch_{batch['batch_index']}.json"
        if not path.exists():
            raise FileNotFoundError(f"staged assembly requires completed {path.name}")
        artifact = json.loads(path.read_text(encoding="utf-8"))
        if artifact["family_sha256"] != plan["family_sha256"]:
            raise ValueError(f"{path.name} belongs to a different frozen family")
        if (
            artifact["batch_index"] != batch["batch_index"]
            or artifact["batch_count"] != plan["batch_count"]
            or artifact["params"] != plan["locked_compute_contract"]
            or artifact["contains_family_inference"] is not False
        ):
            raise ValueError(f"{path.name} violates the staged batch contract")
        expected_codes = [member["lad_code"] for member in batch["members"]]
        actual_codes = [row["lad_code"] for row in artifact["rows"]]
        if actual_codes != expected_codes or artifact["member_count"] != len(expected_codes):
            raise ValueError(f"{path.name} does not exactly match its planned members")
        if seen_codes.intersection(actual_codes):
            raise ValueError(f"{path.name} duplicates a LAD from another batch")
        expected_draws = int(plan["locked_compute_contract"]["B"])
        expected_seeds = list(range(SEED, SEED + expected_draws))
        forbidden = {"p_lower", "p_upper", "p_fdr", "rejects_lower_fdr"}
        if any(
            forbidden.intersection(row)
            or "observed_percentile" in row["null_summary"]
            or len(row["null_h1_total_area"]) != expected_draws
            or row["draw_seeds"] != expected_seeds
            for row in artifact["rows"]
        ):
            raise ValueError(f"{path.name} contains inference or an incomplete null sequence")
        seen_codes.update(actual_codes)
        rows.extend(artifact["rows"])
        elapsed_seconds += float(artifact["elapsed_seconds"])
    if len(rows) != plan["eligible_count"]:
        raise ValueError("staged batch artifacts do not cover the complete frozen family")
    return rows, elapsed_seconds


def ensure_staged_launch_plan(
    frozen_family: dict[str, Any],
    preflight: dict[str, Any],
    path: Path,
) -> dict[str, Any]:
    """Persist the user's approval once and verify it on every later stage."""
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        expected = build_staged_launch_plan(
            frozen_family,
            preflight,
            approved_at=existing["approval"]["approved_at"],
        )
        if existing != expected:
            raise ValueError("existing staged launch plan differs from the frozen family or preflight")
        return existing
    plan = build_staged_launch_plan(
        frozen_family,
        preflight,
        approved_at=datetime.now(timezone.utc).isoformat(),
    )
    _write_json_once(path, plan)
    return plan


def build_staged_execution_provenance(
    plan: dict[str, Any],
    *,
    plan_path: Path,
    batch_root: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Bind the approved plan and ignored batch artifacts into the final result."""
    batch_artifacts: list[dict[str, Any]] = []
    for batch in plan["batches"]:
        path = batch_root / f"batch_{batch['batch_index']}.json"
        artifact = json.loads(path.read_text(encoding="utf-8"))
        batch_artifacts.append(
            {
                "batch_index": batch["batch_index"],
                "path": path.relative_to(project_root).as_posix(),
                "sha256": _sha256(path),
                "member_count": artifact["member_count"],
                "elapsed_seconds": artifact["elapsed_seconds"],
            }
        )
    return {
        "mode": "staged",
        "plan": {
            "path": plan_path.relative_to(REPO_ROOT).as_posix(),
            "sha256": _sha256(plan_path),
            "family_sha256": plan["family_sha256"],
            "approval": plan["approval"],
        },
        "batch_artifacts": batch_artifacts,
        "all_batches_complete": True,
        "inference_deferred_until_all_batches_complete": True,
    }


def load_inputs(input_root: Path) -> tuple[pd.DataFrame, gpd.GeoDataFrame, dict[str, str]]:
    imd_path = input_root / "data/imd2025_file7.csv"
    boundary_path = input_root / "data/lsoa_dec_2021_bgc_v5.geojson"
    if not imd_path.exists() or not boundary_path.exists():
        raise FileNotFoundError("locked IMD or LSOA boundary input is missing")
    actual_hashes = {
        "imd2025_file7": _sha256(imd_path),
        "lsoa_boundaries": _sha256(boundary_path),
    }
    if actual_hashes != {"imd2025_file7": IMD_SHA256, "lsoa_boundaries": LSOA_SHA256}:
        raise ValueError(f"locked input SHA-256 mismatch: {actual_hashes}")
    imd = pd.read_csv(
        imd_path,
        usecols=[LSOA_COL, LAD_CODE_COL, LAD_NAME_COL, *DOMAINS],
    )
    if len(imd) != 33_755:
        raise ValueError(f"IMD row count {len(imd)} != locked 33,755")
    boundaries = gpd.read_file(boundary_path)[["LSOA21CD", "geometry"]]
    return imd, boundaries, actual_hashes


def prepare_lads(
    imd: pd.DataFrame,
    boundaries: gpd.GeoDataFrame,
    family: list[dict[str, Any]],
) -> list[PreparedLad]:
    """Join locked geometries and build fixed queen adjacency for every LAD."""
    from libpysal.weights import Queen

    prepared: list[PreparedLad] = []
    for member in family:
        code = member["lad_code"]
        sub = imd[imd[LAD_CODE_COL] == code].reset_index(drop=True)
        geometry = boundaries.merge(sub[[LSOA_COL]], left_on="LSOA21CD", right_on=LSOA_COL)
        geometry = geometry.set_index("LSOA21CD").loc[sub[LSOA_COL].to_numpy()].reset_index()
        if len(geometry) != len(sub) or len(sub) != member["n_lsoas"]:
            raise ValueError(f"{code}: LSOA geometry/LAD membership join lost rows")
        weights = Queen.from_dataframe(geometry, use_index=False)
        open_neighbours = [np.asarray(weights.neighbors[index], dtype=np.intp) for index in range(len(sub))]
        closed = [
            np.concatenate((np.array([index], dtype=np.intp), adjacent))
            for index, adjacent in enumerate(open_neighbours)
        ]
        raw = sub[DOMAINS].to_numpy(dtype=np.float64)
        prepared.append(
            PreparedLad(
                lad_code=code,
                lad_name=member["lad_name"],
                raw=raw,
                closed_neighbours=closed,
                n_islands=sum(len(adjacent) == 0 for adjacent in open_neighbours),
            )
        )
    return prepared


def _mean_ari(partitions: list[NDArray[np.int64]]) -> float:
    return float(np.mean([adjusted_rand_score(left, right) for left, right in combinations(partitions, 2)]))


def _morans_i(values: NDArray[np.float64], neighbours: list[NDArray[np.intp]]) -> float:
    centered = values - values.mean()
    denominator = float(np.sum(centered**2))
    if denominator == 0.0:
        raise ValueError("Moran's I is undefined for a constant vector")
    numerator = 0.0
    weight_total = 0
    for index, adjacent in enumerate(neighbours):
        open_neighbours = adjacent[adjacent != index]
        numerator += float(np.sum(centered[index] * centered[open_neighbours]))
        weight_total += len(open_neighbours)
    if weight_total == 0:
        raise ValueError("Moran's I is undefined without any adjacency edges")
    return float((len(values) / weight_total) * (numerator / denominator))


def _pc1_scores(raw: NDArray[np.float64]) -> NDArray[np.float64]:
    means = raw.mean(axis=0)
    standard_deviations = raw.std(axis=0)
    standard_deviations[standard_deviations == 0.0] = 1.0
    standardised = (raw - means) / standard_deviations
    return PCA(n_components=1, random_state=SEED).fit_transform(standardised)[:, 0]


def _peak_rss_mb() -> float | None:
    try:
        import psutil
    except ImportError:
        if os.name != "nt":
            return None
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        process = kernel32.GetCurrentProcess()
        success = psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb)
        if not success:
            return None
        return float(counters.PeakWorkingSetSize / (1024**2))
    else:
        memory = psutil.Process(os.getpid()).memory_info()
        return float(getattr(memory, "peak_wset", memory.rss) / (1024**2))


def _write_checkpoint(
    path: Path,
    h1: NDArray[np.float64],
    ari: NDArray[np.float64],
    moran: NDArray[np.float64],
    completed: int,
    n_draws: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as handle:
        np.savez(
            handle,
            h1=h1[:completed],
            ari=ari[:completed],
            moran=moran[:completed],
            completed=completed,
            n_draws=n_draws,
        )
    temporary.replace(path)


def run_lad_battery(
    lad: PreparedLad,
    *,
    n_draws: int,
    checkpoint_dir: Path,
    checkpoint_interval: int = 25,
) -> dict[str, Any]:
    """Run one LAD with deterministic resume checkpoints in draw-index order."""
    if type(n_draws) is not int or n_draws <= 0:
        raise ValueError("n_draws must be a positive int")
    if type(checkpoint_interval) is not int or checkpoint_interval <= 0:
        raise ValueError("checkpoint_interval must be a positive int")
    started = time.perf_counter()
    raw = np.asarray(lad.raw, dtype=np.float64)
    observed = scale_coherence_statistic(raw, lad.closed_neighbours)
    observed_partitions = observed["partitions"]
    observed_ari = _mean_ari(observed_partitions)
    pc1 = _pc1_scores(raw)
    observed_moran = _morans_i(pc1, lad.closed_neighbours)

    h1 = np.empty(n_draws, dtype=np.float64)
    ari = np.empty(n_draws, dtype=np.float64)
    moran = np.empty(n_draws, dtype=np.float64)
    checkpoint_path = checkpoint_dir / f"deprivation_scale_coherence_{lad.lad_code}.npz"
    completed = 0
    if checkpoint_path.exists():
        with np.load(checkpoint_path) as checkpoint:
            if int(checkpoint["n_draws"]) != n_draws:
                raise ValueError(f"checkpoint draw count differs for {lad.lad_code}")
            completed = int(checkpoint["completed"])
            h1[:completed] = checkpoint["h1"]
            ari[:completed] = checkpoint["ari"]
            moran[:completed] = checkpoint["moran"]

    probe = spatialised_null_draw(raw, lad.closed_neighbours, draw_index=0)
    for draw_index in range(completed, n_draws):
        draw = (
            probe
            if draw_index == 0
            else spatialised_null_draw(
                raw,
                lad.closed_neighbours,
                draw_index=draw_index,
            )
        )
        h1[draw_index] = float(draw["h1_total_area"])
        ari[draw_index] = _mean_ari(draw["partitions"])
        permutation = np.random.default_rng(SEED + draw_index).permutation(len(raw))
        moran[draw_index] = _morans_i(pc1[permutation], lad.closed_neighbours)
        next_completed = draw_index + 1
        if next_completed % checkpoint_interval == 0 or next_completed == n_draws:
            _write_checkpoint(checkpoint_path, h1, ari, moran, next_completed, n_draws)

    p_lower, p_upper, percentile = empirical_tail_pvalues(h1, observed=float(observed["h1_total_area"]))
    validity = null_validity_record(observed_partitions, probe["partitions"], h1)
    redundancy = redundancy_record(
        np.append(h1, observed["h1_total_area"]),
        np.append(ari, observed_ari),
        np.append(moran, observed_moran),
    )
    elapsed = time.perf_counter() - started
    return {
        "lad_code": lad.lad_code,
        "lad_name": lad.lad_name,
        "n_lsoas": len(raw),
        "n_islands": lad.n_islands,
        "observed": {
            "h1_total_area": float(observed["h1_total_area"]),
            "h1_lag1_area": float(observed["h1_lag1_area"]),
            "h1_max": float(observed["h1_max"]),
            "mean_ari_across_k": observed_ari,
            "moran_i_pc1": observed_moran,
        },
        "null_h1_total_area": h1.tolist(),
        "null_summary": {
            "mean": float(h1.mean()),
            "standard_deviation": float(h1.std()),
            "observed_percentile": percentile,
        },
        "p_lower": p_lower,
        "p_upper": p_upper,
        "rho_h1_mean_ari_across_k": redundancy["rho_h1_mean_ari_across_k"],
        "rho_h1_moran_i_pc1": redundancy["rho_h1_moran_i_pc1"],
        "redundant": redundancy["redundant"],
        "null_validity": validity,
        "draw_seeds": list(range(SEED, SEED + n_draws)),
        "runtime": {
            "wall_seconds": elapsed,
            "peak_rss_mb": _peak_rss_mb(),
            "worker_pid": os.getpid(),
            "completed_draws": n_draws,
            "checkpoint_interval": checkpoint_interval,
            "checkpoint_file": checkpoint_path.name,
        },
    }


def run_family(
    lads: list[PreparedLad],
    *,
    n_draws: int,
    workers: int,
    checkpoint_dir: Path,
    checkpoint_interval: int = 25,
) -> list[dict[str, Any]]:
    """Run independent LAD batteries in deterministic family order."""
    if workers < 1:
        raise ValueError("workers must be positive")
    if workers == 1:
        return [
            run_lad_battery(
                lad,
                n_draws=n_draws,
                checkpoint_dir=checkpoint_dir,
                checkpoint_interval=checkpoint_interval,
            )
            for lad in lads
        ]
    by_code: dict[str, dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                run_lad_battery,
                lad,
                n_draws=n_draws,
                checkpoint_dir=checkpoint_dir,
                checkpoint_interval=checkpoint_interval,
            ): lad.lad_code
            for lad in lads
        }
        for future in as_completed(futures):
            code = futures[future]
            by_code[code] = future.result()
            LOGGER.info("completed %s (%d/%d LADs)", code, len(by_code), len(lads))
    return [by_code[lad.lad_code] for lad in lads]


def reproduce_spike_pilot(lads: list[PreparedLad], checkpoint_dir: Path) -> dict[str, Any]:
    """Reproduce Birmingham's Spike-3 observed statistic and lower tail."""
    birmingham = next(lad for lad in lads if lad.lad_code == "E08000025")
    result = run_lad_battery(
        birmingham,
        n_draws=99,
        checkpoint_dir=checkpoint_dir,
        checkpoint_interval=25,
    )
    if result["observed"]["h1_total_area"] != 27.0 or not np.isclose(result["p_lower"], 0.01):
        raise RuntimeError(
            "STOP: Birmingham pilot failed Spike-3 reproduction "
            f"(observed={result['observed']['h1_total_area']}, p_lower={result['p_lower']})"
        )
    return result


def audit_lad_size_strata(lads: list[PreparedLad]) -> dict[str, Any]:
    """Audit one deterministic representative from each LSOA-count tertile."""
    ordered = sorted(lads, key=lambda lad: (len(lad.raw), lad.lad_code))
    groups = np.array_split(np.arange(len(ordered)), 3)
    records: list[dict[str, Any]] = []
    for label, indices in zip(("small", "medium", "large"), groups, strict=True):
        representative = ordered[int(indices[len(indices) // 2])]
        observed = scale_coherence_statistic(representative.raw, representative.closed_neighbours)
        probe = spatialised_null_draw(
            representative.raw,
            representative.closed_neighbours,
            draw_index=0,
        )
        shapes_match = all(
            left.shape == right.shape for left, right in zip(observed["partitions"], probe["partitions"], strict=True)
        )
        perturbed = shapes_match and any(
            not np.array_equal(left, right)
            for left, right in zip(observed["partitions"], probe["partitions"], strict=True)
        )
        if not shapes_match or not perturbed:
            raise RuntimeError(
                f"STOP: null invariance audit failed for {label} representative {representative.lad_code}"
            )
        records.append(
            {
                "stratum": label,
                "representative_lad_code": representative.lad_code,
                "representative_lad_name": representative.lad_name,
                "n_lsoas": len(representative.raw),
                "draw_index": 0,
                "draw_seed": SEED,
                "partition_shapes_match": True,
                "partitions_perturbed": True,
            }
        )
    return {
        "strata_definition": "tertiles of the frozen family ordered by (n_lsoas, lad_code)",
        "records": records,
        "centering_statement": (
            "The null permutes raw deprivation vectors across fixed spatial nodes before the shared statistic "
            "pipeline. It destroys observed spatial autocorrelation and is not fit from h1_total_area, so the "
            "statistic is not structurally centred on the null's sufficient statistic."
        ),
        "verdict": "VALID NULL",
    }


def _worker_sweep(
    lads: list[PreparedLad],
    *,
    maximum_workers: int,
    checkpoint_root: Path,
    n_draws: int = 25,
) -> list[dict[str, Any]]:
    worker_counts = sorted({count for count in (1, 2, 4, 8, maximum_workers) if count <= maximum_workers})
    sample = sorted(lads, key=lambda lad: len(lad.raw), reverse=True)[: min(8, len(lads))]
    records: list[dict[str, Any]] = []
    for workers in worker_counts:
        started = time.perf_counter()
        run_family(
            sample,
            n_draws=n_draws,
            workers=workers,
            checkpoint_dir=checkpoint_root / f"workers_{workers}",
            checkpoint_interval=25,
        )
        records.append(
            {
                "workers": workers,
                "wall_seconds": time.perf_counter() - started,
                "lad_count": len(sample),
                "draws_per_lad": n_draws,
                "production_entry_point": "run_family",
            }
        )
    return records


def run_resource_preflight(
    lads: list[PreparedLad],
    *,
    workers: int,
    partial_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Run the full-B canary and process-count sweep, then record projection."""
    benchmark_dir = partial_root / "benchmark"
    benchmark_record_path = benchmark_dir / "benchmark_record.json"
    mid_sized = sorted(lads, key=lambda lad: len(lad.raw))[len(lads) // 2]
    if benchmark_record_path.exists():
        benchmark = json.loads(benchmark_record_path.read_text(encoding="utf-8"))
    else:
        result = run_lad_battery(
            mid_sized,
            n_draws=B_LOCKED,
            checkpoint_dir=benchmark_dir,
            checkpoint_interval=25,
        )
        benchmark = {
            "lad_code": mid_sized.lad_code,
            "lad_name": mid_sized.lad_name,
            "n_lsoas": len(mid_sized.raw),
            "B": B_LOCKED,
            "wall_seconds": result["runtime"]["wall_seconds"],
            "peak_rss_mb": result["runtime"]["peak_rss_mb"],
            "production_entry_point": "run_lad_battery",
        }
        _write_json_once(benchmark_record_path, benchmark)

    sweep_record_path = partial_root / "worker_sweep.json"
    if sweep_record_path.exists():
        sweep = json.loads(sweep_record_path.read_text(encoding="utf-8"))["records"]
    else:
        run_slug = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        sweep = _worker_sweep(
            lads,
            maximum_workers=workers,
            checkpoint_root=partial_root / f"worker_sweep_{run_slug}",
        )
        _write_json_once(sweep_record_path, {"records": sweep})

    one_worker = next(record for record in sweep if record["workers"] == 1)
    target_worker = next(record for record in sweep if record["workers"] == workers)
    measured_speedup = one_worker["wall_seconds"] / target_worker["wall_seconds"]
    effective_workers = max(1.0, min(float(workers), measured_speedup))
    projected_seconds = benchmark["wall_seconds"] * len(lads) / effective_workers
    stop_required = projected_seconds > 12 * 3600

    try:
        import psutil

        total_memory_gb = psutil.virtual_memory().total / (1024**3)
    except ImportError:
        total_memory_gb = None
    disk_free_gb = shutil.disk_usage(partial_root.parent).free / (1024**3)
    preflight = {
        "task_id": "mcbif-deprivation-scale-coherence",
        "paper_id": "P04",
        "command": "uv run python -m poverty_tda.scripts.run_deprivation_scale_coherence --mode full --workers 8",
        "data_scale": {
            "lad_count": len(lads),
            "lsoa_count_min": min(len(lad.raw) for lad in lads),
            "lsoa_count_max": max(len(lad.raw) for lad in lads),
            "null_draws_per_lad": B_LOCKED,
            "target_statistic_calls": len(lads) * B_LOCKED,
        },
        "resources": {
            "cpu_cores": os.cpu_count(),
            "memory_gb": total_memory_gb,
            "disk_free_gb": disk_free_gb,
            "driver_peak_rss_mb_at_preflight": _peak_rss_mb(),
        },
        "strategy": {
            "parallel_backend": "ProcessPoolExecutor",
            "workers": workers,
            "parallel_axis": "LAD",
            "checkpointing": True,
            "resume_supported": True,
            "progress_reporting": True,
            "checkpoint_interval_draws": 25,
        },
        "benchmark": {
            "harness_is_production_entry_point": True,
            "full_B_mid_sized_lad": benchmark,
            "worker_sweep": sweep,
            "sweep_call_count": len(sweep) * min(8, len(lads)) * 25,
            "target_call_count": len(lads) * B_LOCKED,
            "scale_pct": 100.0 * len(sweep) * min(8, len(lads)) * 25 / (len(lads) * B_LOCKED),
            "measured_speedup_at_target": measured_speedup,
        },
        "risk_flags": [
            "worker sweep is sub-scale and the family projection remains provisional until full launch",
            "LAD geometry sizes vary from the full-B canary",
            "the committed full-B canary predates the Windows peak-RSS fallback and records peak_rss_mb=null",
        ],
        "estimated_wall_time_seconds": projected_seconds,
        "estimated_wall_time_hours": projected_seconds / 3600,
        "provisional": True,
        "decision": {
            "launch_authorized": not stop_required,
            "status": "STOP" if stop_required else "PASS",
            "stop_threshold_hours": 12,
            "reason": (
                f"projected single launch {projected_seconds / 3600:.2f} h exceeds 12 h"
                if stop_required
                else "projected single launch is within the locked 12 h ceiling"
            ),
            "staged_launch_proposal": (
                "Split the frozen 69-LAD family into deterministic size-balanced batches, largest LADs first, "
                "with unchanged B=999/seeds/statistic/null; assemble BH-FDR only after every batch completes. "
                "Requires User approval before launch."
                if stop_required
                else None
            ),
        },
        "validation_commands": [
            "uv run pytest tests/poverty tests/discovery/test_deprivation_scale_coherence_contract.py -q",
            "uv run ruff check poverty_tda tests/poverty tests/discovery/test_deprivation_scale_coherence_contract.py",
        ],
    }
    _write_json_once(output_path, preflight)
    if stop_required:
        raise RuntimeError(f"STOP: projected family launch is {projected_seconds / 3600:.2f} h (>12 h)")
    return preflight


def assemble_result(
    rows: list[dict[str, Any]],
    *,
    frozen_family: dict[str, Any],
    input_hashes: dict[str, str],
    workers: int,
    preflight: dict[str, Any],
    pilot: dict[str, Any],
    invariance_audit: dict[str, Any],
    staged_execution: dict[str, Any] | None,
    elapsed_seconds: float,
) -> dict[str, Any]:
    """Apply validity exclusions, BH families, sensitivity, and locked verdict."""
    for row in rows:
        p_lower, p_upper, percentile = empirical_tail_pvalues(
            np.asarray(row["null_h1_total_area"], dtype=np.float64),
            observed=float(row["observed"]["h1_total_area"]),
        )
        row["p_lower"] = p_lower
        row["p_upper"] = p_upper
        row["null_summary"]["observed_percentile"] = percentile
    invalid = [row for row in rows if not row["null_validity"]["valid"]]
    if len(invalid) / len(rows) > 0.20:
        raise RuntimeError(f"STOP: spatialised null degenerate on {len(invalid)}/{len(rows)} LADs (>20%)")
    valid_rows = [row for row in rows if row["null_validity"]["valid"]]
    if not valid_rows:
        raise RuntimeError("STOP: no LAD has a valid spatialised null")
    adjusted = benjamini_hochberg(np.asarray([row["p_lower"] for row in valid_rows], dtype=np.float64))
    for row, q_value in zip(valid_rows, adjusted, strict=True):
        row["p_fdr"] = float(q_value)
        row["rejects_lower_fdr"] = bool(q_value <= ALPHA)

    reduced_rows = [row for row in valid_rows if row["lad_code"] not in set(SPIKE_LAD_CODES)]
    reduced_q = benjamini_hochberg(np.asarray([row["p_lower"] for row in reduced_rows], dtype=np.float64))
    reduced_rejects = int(np.count_nonzero(reduced_q <= ALPHA))
    sensitivity_rows = [
        {
            "lad_code": row["lad_code"],
            "lad_name": row["lad_name"],
            "n_lsoas": row["n_lsoas"],
            "observed_h1_total_area": row["observed"]["h1_total_area"],
            "p_lower": row["p_lower"],
            "p_upper": row["p_upper"],
            "primary_p_fdr": row["p_fdr"],
            "primary_rejects_lower_fdr": row["rejects_lower_fdr"],
            "p_fdr": float(q_value),
            "rejects_lower_fdr": bool(q_value <= ALPHA),
            "redundant": row["redundant"],
        }
        for row, q_value in zip(reduced_rows, reduced_q, strict=True)
    ]
    primary_rejects = sum(row["rejects_lower_fdr"] for row in valid_rows)
    primary_fraction = primary_rejects / len(valid_rows)
    reduced_fraction = reduced_rejects / len(reduced_rows)
    primary_direction = "above" if primary_fraction > ALPHA else "below" if primary_fraction < ALPHA else "equal"
    reduced_direction = "above" if reduced_fraction > ALPHA else "below" if reduced_fraction < ALPHA else "equal"
    sensitivity_agrees = primary_direction == reduced_direction
    rejecting_redundant = any(row["rejects_lower_fdr"] and row["redundant"] for row in valid_rows)
    if primary_rejects == 0:
        verdict = "negative"
    elif primary_fraction >= 0.20 and not rejecting_redundant and sensitivity_agrees:
        verdict = "coherence-confirmed"
    else:
        verdict = "partial-signal"

    family_members = [
        {"lad_code": row["lad_code"], "lad_name": row["lad_name"], "n_lsoas": row["n_lsoas"]} for row in valid_rows
    ]
    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "input_sha256": input_hashes,
        "params": {
            "B": B_LOCKED,
            "seed": SEED,
            "per_draw_seeds": "42+b for b=0..998",
            "ks": list(KS),
            "lad_floor": LAD_FLOOR,
            "test": "one-sided-lower",
            "alpha": ALPHA,
            "fdr_method": "benjamini-hochberg",
            "workers": workers,
        },
        "lad_family": {
            "enumerated_count": frozen_family["eligible_count"],
            "enumerated_members": frozen_family["members"],
            "family_sha256": frozen_family["family_sha256"],
            "frozen_at": frozen_family["frozen_at"],
            "eligible_count": len(family_members),
            "members": family_members,
            "excluded": [
                {
                    "lad_code": row["lad_code"],
                    "lad_name": row["lad_name"],
                    "n_lsoas": row["n_lsoas"],
                    "reason": row["null_validity"]["reasons"],
                    "statistic_independent": True,
                }
                for row in invalid
            ],
        },
        "lad_results": valid_rows,
        "sensitivity_excluding_spike_lads": {
            "excluded_lad_codes": SPIKE_LAD_CODES,
            "bh_recomputed_on_reduced_family": True,
            "family_size": len(reduced_rows),
            "reject_count": reduced_rejects,
            "coherent_fraction": reduced_fraction,
            "direction_vs_null_base_rate": reduced_direction,
            "primary_direction_vs_null_base_rate": primary_direction,
            "direction_agrees": sensitivity_agrees,
            "lad_results": sensitivity_rows,
        },
        "decision": {
            "verdict": verdict,
            "reject_count": primary_rejects,
            "eligible_count": len(valid_rows),
            "reject_fraction": primary_fraction,
            "rejecting_lad_redundant": rejecting_redundant,
        },
        "runtime": {
            "wall_seconds": elapsed_seconds,
            "workers": workers,
            "per_lad_peak_rss_mb": {row["lad_code"]: row["runtime"]["peak_rss_mb"] for row in valid_rows},
            "resource_preflight_estimated_hours": preflight["estimated_wall_time_hours"],
        },
        "pilot_reproduction": {
            "lad_code": pilot["lad_code"],
            "B": 99,
            "observed_h1_total_area": pilot["observed"]["h1_total_area"],
            "p_lower": pilot["p_lower"],
            "passed": True,
        },
        "null_invariance_audit": invariance_audit,
        "provenance": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "git_commit": git_commit,
            "inputs": {
                "imd2025_file7": {
                    "path": "data/imd2025_file7.csv",
                    "sha256": input_hashes.get("imd2025_file7"),
                },
                "lsoa_boundaries": {
                    "path": "data/lsoa_dec_2021_bgc_v5.geojson",
                    "sha256": input_hashes.get("lsoa_boundaries"),
                    "source": "ONS Open Geography Portal item 68515293204e43ca8ab56fa13ae8a547",
                    "downloaded_at": "2026-07-10",
                    "license": "OGL v3.0",
                },
            },
            "staged_execution": staged_execution
            or {
                "mode": "single-launch",
                "all_batches_complete": True,
                "inference_deferred_until_all_batches_complete": False,
            },
            "pre_registration": "vault/00-Meta/Discovery/deprivation-scale-coherence-dispatch-prereg-2026-07-10.md",
            "pre_registration_sha256": "4038ceb802d5a5185da1fde858d29e1147ac502e8c1178c1b4b366848c5f6bac",
            "pre_registration_json_sha256": "fa1af694c4e740acd63ef591ec2b53e03e93b6bfc35ec1a79d9ce9ed45398a66",
            "pre_registration_status": "LOCKED 2026-07-10",
            "lad_assignment": "2024 LAD code/name columns in locked IMD File 7; boundaries joined by 2021 LSOA code",
            "null_centering_statement": (
                "Raw deprivation vectors are permuted across fixed spatial nodes before the shared pipeline. "
                "This destroys the spatial autocorrelation encoded by the observed construction; it is not a "
                "parametric fit to h1_total_area and is not centred on that statistic by construction."
            ),
        },
    }
    validate_result_payload(payload)
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["gate0", "pilot", "benchmark", "plan", "staged", "assemble", "full"],
        default="full",
    )
    parser.add_argument("--batch-index", type=int, choices=[1, 2, 3], default=None)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--input-root", type=Path, default=None)
    parser.add_argument("--result-date", default=date.today().isoformat())
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()
    if args.mode in {"benchmark", "staged", "full"} and args.workers < 8:
        raise SystemExit("STOP: locked compute contract requires workers >= 8")
    if args.mode == "staged" and args.batch_index is None:
        raise SystemExit("--batch-index 1, 2, or 3 is required for staged execution")
    if args.mode != "staged" and args.batch_index is not None:
        raise SystemExit("--batch-index is only valid with --mode staged")
    project_root = args.input_root or _project_root()
    partial_root = project_root / "results/poverty_tda_mcbif/.partial/deprivation_scale_coherence"
    imd, boundaries, input_hashes = load_inputs(project_root)
    family = enumerate_eligible_lads(imd)
    frozen = freeze_lad_family(family, partial_root / "frozen_family.json")
    LOGGER.info("Gate 0 frozen: %d eligible LADs", len(family))
    if args.mode == "gate0":
        return

    result_dir = REPO_ROOT / "results/poverty_tda_mcbif"
    preflight_path = result_dir / f"resource_preflight_deprivation_scale_coherence_{args.result_date}.json"
    plan_path = result_dir / f"staged_launch_plan_deprivation_scale_coherence_{args.result_date}.json"
    if args.mode == "plan":
        if not preflight_path.exists():
            raise FileNotFoundError(f"approved staged plan requires {preflight_path}")
        preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        plan = ensure_staged_launch_plan(frozen, preflight, plan_path)
        LOGGER.info(
            "wrote approved staged plan: %s (%s)",
            plan_path,
            [batch["member_count"] for batch in plan["batches"]],
        )
        return

    prepared = prepare_lads(imd, boundaries, family)
    invariance_audit = audit_lad_size_strata(prepared)
    LOGGER.info("null invariance audit passed for small/medium/large LAD strata")
    pilot = reproduce_spike_pilot(prepared, partial_root / "pilot")
    LOGGER.info("Birmingham pilot reproduced: observed=27, p_lower=0.01")
    if args.mode == "pilot":
        return

    if args.mode in {"staged", "assemble"}:
        if not preflight_path.exists():
            raise FileNotFoundError(f"staged execution requires {preflight_path}")
        preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        plan = ensure_staged_launch_plan(frozen, preflight, plan_path)
        batch_root = partial_root / "staged_results"
        if args.mode == "staged":
            batch = next(item for item in plan["batches"] if item["batch_index"] == args.batch_index)
            batch_path = batch_root / f"batch_{args.batch_index}.json"
            if batch_path.exists():
                existing = json.loads(batch_path.read_text(encoding="utf-8"))
                expected_codes = [member["lad_code"] for member in batch["members"]]
                if (
                    existing["family_sha256"] != plan["family_sha256"]
                    or existing["contains_family_inference"] is not False
                    or [row["lad_code"] for row in existing["rows"]] != expected_codes
                ):
                    raise ValueError(f"existing {batch_path.name} violates the staged contract")
                LOGGER.info("staged batch %d is already complete", args.batch_index)
                return
            prepared_by_code = {lad.lad_code: lad for lad in prepared}
            batch_lads = [prepared_by_code[member["lad_code"]] for member in batch["members"]]
            started = time.perf_counter()
            rows = run_family(
                batch_lads,
                n_draws=B_LOCKED,
                workers=args.workers,
                checkpoint_dir=partial_root / "family",
                checkpoint_interval=25,
            )
            artifact = prepare_staged_batch_artifact(
                rows,
                plan=plan,
                batch_index=args.batch_index,
                elapsed_seconds=time.perf_counter() - started,
            )
            _write_json_once(batch_path, artifact)
            LOGGER.info("completed staged batch %d: %s", args.batch_index, batch_path)
            return

        rows, elapsed_seconds = load_staged_batch_rows(plan, batch_root)
        payload = assemble_result(
            rows,
            frozen_family=frozen,
            input_hashes=input_hashes,
            workers=args.workers,
            preflight=preflight,
            pilot=pilot,
            invariance_audit=invariance_audit,
            staged_execution=build_staged_execution_provenance(
                plan,
                plan_path=plan_path,
                batch_root=batch_root,
                project_root=project_root,
            ),
            elapsed_seconds=elapsed_seconds,
        )
        output_path = result_dir / f"deprivation_scale_coherence_{args.result_date}.json"
        _write_json_once(output_path, payload)
        LOGGER.info("wrote %s with verdict %s", output_path, payload["decision"]["verdict"])
        return

    preflight = run_resource_preflight(
        prepared,
        workers=args.workers,
        partial_root=partial_root,
        output_path=preflight_path,
    )
    LOGGER.info("projected full family wall time: %.2f h", preflight["estimated_wall_time_hours"])
    if args.mode == "benchmark":
        return

    started = time.perf_counter()
    rows = run_family(
        prepared,
        n_draws=B_LOCKED,
        workers=args.workers,
        checkpoint_dir=partial_root / "family",
        checkpoint_interval=25,
    )
    payload = assemble_result(
        rows,
        frozen_family=frozen,
        input_hashes=input_hashes,
        workers=args.workers,
        preflight=preflight,
        pilot=pilot,
        invariance_audit=invariance_audit,
        staged_execution=None,
        elapsed_seconds=time.perf_counter() - started,
    )
    output_path = result_dir / f"deprivation_scale_coherence_{args.result_date}.json"
    _write_json_once(output_path, payload)
    LOGGER.info("wrote %s with verdict %s", output_path, payload["decision"]["verdict"])


if __name__ == "__main__":
    main()
