# Research context: docs/plans/agentic-research-system/design/05a-lean-proof-evidence-class-addendum-2026-07-07.md
# Purpose: Contract-first TDD suite for the acceptor-side `lean_proof` harness
#   (tools/check_lean_proof.py). Every 05a §3.1 negative-control fixture is
#   asserted to FAIL first (a gate never watched to fail is not an assurance),
#   the three exit codes are pinned, and the C1 re-execution property (producer
#   build.log never trusted) is demonstrated in both directions.
"""Tests for the standalone lean_proof acceptance harness (05a §3 items 0-8, Key A)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tools import check_lean_proof as clp

# --------------------------------------------------------------------------- #
# Fixture construction — synthetic promoted bundles + a re-execution stand-in  #
# --------------------------------------------------------------------------- #

# A promoted set that passes every Key-A machine check: only theorem/lemma/example
# declarations, no holes, no native_decide, a named non-vacuity witness for the
# hypothesis, and a kernel-checked equality pinning the artefact constant.
BASELINE_LEAN = (
    "-- S2 fixed-margin max-ARI concentration bound - promoted set (pilot)\n"
    "theorem max_ari_bound (h : 0 < nMax) : greedyValue margins ≤ maxAriBoundConst := by\n"
    "  decide\n"
    "lemma max_ari_witness : 0 < nMax := by\n"
    "  decide\n"
    "example : greedyValue margins = 60862048 := by decide\n"
)

REPO_COMMIT = "deadbeefcafe0011"


def build_bundle(
    tmp_path: Path,
    *,
    files: dict[str, str] | None = None,
    manifest_extra: dict[str, Any] | None = None,
    repo_commit: str = REPO_COMMIT,
    build_log: str = "Build completed successfully.\nexit: 0\n",
    corrupt_hash: bool = False,
) -> Path:
    """Write a promoted lean_proof bundle to disk and return its directory.

    The producer ``build.log`` deliberately asserts success so the C1
    re-execution tests can prove the harness never reads it for a verdict.
    """
    bundle = tmp_path / "bundle"
    bundle.mkdir(exist_ok=True)
    files = files or {"MaxAri.lean": BASELINE_LEAN}
    promoted = []
    for rel, text in files.items():
        path = bundle / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        # Hash the ACTUAL on-disk bytes (write_text may translate newlines on
        # Windows); a real producer hashes the file it ships, and the harness
        # recomputes from bytes (content is verdict).
        recorded = "0" * 64 if corrupt_hash else hashlib.sha256(path.read_bytes()).hexdigest()
        promoted.append({"path": rel, "sha256": recorded})

    manifest: dict[str, Any] = {
        "bundle_id": "aev_s2_maxari_pilot",
        "repo": {"identity": "github.com/stephendor/tdl-lean-proofs", "commit": repo_commit},
        "toolchain": {
            "lean_toolchain": "leanprover/lean4:v4.12.0",
            "mathlib_commit": "abc123",
            "lake_manifest_hash": "m1",
        },
        "lake_project_dir": ".",
        "import_modules": ["MaxAri"],
        "promoted_files": promoted,
        "theorems": ["max_ari_bound"],
        "artefact_constants": [
            {
                "name": "greedyValue margins",
                "recorded_value": "60862048",
                "artefact_id": "res_s2_greedy_2026-07-07",
                "artefact_hash": "sha256:aaa",
            }
        ],
        "witness_obligations": [{"theorem": "max_ari_bound", "witness_example": "max_ari_witness"}],
        "native_decide_approved": [],
    }
    if manifest_extra:
        manifest.update(manifest_extra)

    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (bundle / "build.log").write_text(build_log, encoding="utf-8")
    return bundle


class FakeToolchain:
    """Deterministic stand-in for the acceptor's own clean re-execution.

    It models what ``lake build`` / ``#print axioms`` return on a fresh rebuild,
    independent of the producer's advisory ``build.log`` — the whole point of C1.
    """

    def __init__(
        self,
        *,
        build_exit: int = 0,
        build_output: str = "Build completed successfully.",
        axioms: dict[str, str] | None = None,
        is_available: bool = True,
    ) -> None:
        self.build_exit = build_exit
        self.build_output = build_output
        self._axioms = axioms or {}
        self._available = is_available
        self.build_calls = 0

    def available(self) -> bool:
        return self._available

    def lake_build(self, project_dir: Path) -> tuple[int, str]:
        self.build_calls += 1
        return self.build_exit, self.build_output

    def print_axioms(self, project_dir: Path, imports: list[str], theorems: list[str]) -> dict[str, str]:
        return {t: self._axioms.get(t, f"'{t}' depends on axioms: [propext]") for t in theorems}


# --------------------------------------------------------------------------- #
# NEGATIVE CONTROLS FIRST — one per 05a §3.1 acceptance item (must FAIL)       #
# --------------------------------------------------------------------------- #


def test_forged_build_log_rejected(tmp_path: Path) -> None:
    """§3.1 item 0/1 - producer build.log says exit 0 but the acceptor rebuild fails."""
    bundle = build_bundle(tmp_path, build_log="Build completed successfully.\nexit: 0\n")
    tc = FakeToolchain(build_exit=1, build_output="error: lake build failed")
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, tc)
    assert not outcome.admissible
    assert "kernel-build" in outcome.failed_items
    assert tc.build_calls == 1, "harness must RE-EXECUTE the build (C1), not trust the log"


def test_sorry_bearing_file_rejected(tmp_path: Path) -> None:
    """§3.1 item 2 - a sorry/admit-bearing promoted file is rejected."""
    lean = (
        "theorem max_ari_bound (h : 0 < nMax) : greedyValue margins ≤ maxAriBoundConst := by\n"
        "  sorry\n"
        "lemma max_ari_witness : 0 < nMax := by decide\n"
        "example : greedyValue margins = 60862048 := by decide\n"
    )
    bundle = build_bundle(tmp_path, files={"MaxAri.lean": lean})
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, FakeToolchain())
    assert not outcome.admissible
    assert "no-holes" in outcome.failed_items


def test_disallowed_axiom_rejected(tmp_path: Path) -> None:
    """§3.1 item 3 - an axiom outside {propext, Classical.choice, Quot.sound} is rejected."""
    bundle = build_bundle(tmp_path)
    tc = FakeToolchain(axioms={"max_ari_bound": "'max_ari_bound' depends on axioms: [propext, EvilAxiom]"})
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, tc)
    assert not outcome.admissible
    assert "axiom-audit" in outcome.failed_items


def test_native_decide_rejected(tmp_path: Path) -> None:
    """§3.1 item 4 - native_decide / FFI evaluation is rejected absent explicit approval."""
    lean = (
        "theorem max_ari_bound (h : 0 < nMax) : greedyValue margins ≤ maxAriBoundConst := by\n"
        "  native_decide\n"
        "lemma max_ari_witness : 0 < nMax := by decide\n"
        "example : greedyValue margins = 60862048 := by decide\n"
    )
    bundle = build_bundle(tmp_path, files={"MaxAri.lean": lean})
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, FakeToolchain())
    assert not outcome.admissible
    assert "trusted-computing-base" in outcome.failed_items


def test_inflated_constant_surfaced_with_discrepancy(tmp_path: Path) -> None:
    """§3.1 item 5 - an inflated recorded constant is surfaced by the equality mismatch."""
    bundle = build_bundle(
        tmp_path,
        manifest_extra={
            "artefact_constants": [
                {
                    "name": "greedyValue margins",
                    "recorded_value": "60862049",  # inflated by one vs the kernel-checked 60862048
                    "artefact_id": "res_s2_greedy_2026-07-07",
                    "artefact_hash": "sha256:aaa",
                }
            ]
        },
    )
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, FakeToolchain())
    assert not outcome.admissible
    assert "constant-equality" in outcome.failed_items
    assert outcome.discrepancies, "a discrepancy record must be emitted, not a silent pass"
    disc = outcome.discrepancies[0]
    assert disc["artefact_id"] == "res_s2_greedy_2026-07-07"
    assert disc["recorded_value"] == "60862049"
    assert disc["derived_value"] == "60862048"


def test_inequality_only_constant_rejected(tmp_path: Path) -> None:
    """§3.1 item 5 - a strict-inequality-only derivation never pins the value and is rejected."""
    lean = (
        "theorem max_ari_bound (h : 0 < nMax) : greedyValue margins ≤ maxAriBoundConst := by\n"
        "  decide\n"
        "lemma max_ari_witness : 0 < nMax := by decide\n"
        "example : greedyValue margins ≤ 60862048 := by decide\n"
    )
    bundle = build_bundle(tmp_path, files={"MaxAri.lean": lean})
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, FakeToolchain())
    assert not outcome.admissible
    assert "constant-equality" in outcome.failed_items


def test_missing_witness_rejected(tmp_path: Path) -> None:
    """§3.1 item 6 - a hypothesis-bearing theorem with no non-vacuity witness is rejected."""
    lean = (
        "theorem max_ari_bound (h : 0 < nMax) : greedyValue margins ≤ maxAriBoundConst := by\n"
        "  decide\n"
        "example : greedyValue margins = 60862048 := by decide\n"
    )
    bundle = build_bundle(tmp_path, files={"MaxAri.lean": lean})
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, FakeToolchain())
    assert not outcome.admissible
    assert "non-vacuity-witness" in outcome.failed_items


def test_notation_captured_signature_rejected(tmp_path: Path) -> None:
    """§3.1 item 8 - a prover-authored notation declaration is drift and is rejected."""
    lean = BASELINE_LEAN + 'notation "≼" => LE.le\n'
    bundle = build_bundle(tmp_path, files={"MaxAri.lean": lean})
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, FakeToolchain())
    assert not outcome.admissible
    assert "declaration-kind" in outcome.failed_items


def test_prover_authored_def_rejected(tmp_path: Path) -> None:
    """§3.1 item 8 - a prover-authored def in a promoted file is drift and is rejected."""
    lean = BASELINE_LEAN + "def helper : Nat := 42\n"
    bundle = build_bundle(tmp_path, files={"MaxAri.lean": lean})
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, FakeToolchain())
    assert not outcome.admissible
    assert "declaration-kind" in outcome.failed_items


def test_tampered_file_rejected(tmp_path: Path) -> None:
    """Content is verdict - a promoted file whose bytes differ from its manifest hash is rejected."""
    bundle = build_bundle(tmp_path, corrupt_hash=True)
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, FakeToolchain())
    assert not outcome.admissible
    assert "file-integrity" in outcome.failed_items


# --------------------------------------------------------------------------- #
# Environment / harness errors -> exit 2 (fail closed, never pass a skip)      #
# --------------------------------------------------------------------------- #


def test_missing_bundle_is_env_error(tmp_path: Path) -> None:
    with pytest.raises(clp.BundleError):
        clp.accept_bundle(tmp_path / "does-not-exist", REPO_COMMIT, FakeToolchain())


def test_absent_toolchain_is_env_error(tmp_path: Path) -> None:
    bundle = build_bundle(tmp_path)
    with pytest.raises(clp.ToolchainError):
        clp.accept_bundle(bundle, REPO_COMMIT, FakeToolchain(is_available=False))


def test_malformed_manifest_is_env_error(tmp_path: Path) -> None:
    bundle = build_bundle(tmp_path)
    (bundle / "manifest.json").write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(clp.BundleError):
        clp.accept_bundle(bundle, REPO_COMMIT, FakeToolchain())


def test_repo_commit_mismatch_is_env_error(tmp_path: Path) -> None:
    bundle = build_bundle(tmp_path)
    with pytest.raises(clp.BundleError):
        clp.accept_bundle(bundle, "0000000000000000", FakeToolchain())


# --------------------------------------------------------------------------- #
# Positive path + C1 re-execution property                                    #
# --------------------------------------------------------------------------- #


def test_valid_bundle_accepted(tmp_path: Path) -> None:
    bundle = build_bundle(tmp_path)
    tc = FakeToolchain(
        axioms={"max_ari_bound": "'max_ari_bound' depends on axioms: [propext, Classical.choice, Quot.sound]"}
    )
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, tc)
    assert outcome.admissible, outcome.failed_items
    assert outcome.failed_items == []
    assert outcome.discrepancies == []


def test_producer_build_log_is_ignored_when_reexecution_succeeds(tmp_path: Path) -> None:
    """C1, other direction - a build.log claiming FAILURE cannot sink a clean rebuild."""
    bundle = build_bundle(tmp_path, build_log="error: FAILED\nexit: 1\n")
    tc = FakeToolchain(
        axioms={"max_ari_bound": "'max_ari_bound' depends on axioms: [propext, Classical.choice, Quot.sound]"}
    )
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, tc)
    assert outcome.admissible


# --------------------------------------------------------------------------- #
# Exit codes through main()                                                    #
# --------------------------------------------------------------------------- #


def test_main_exit_admissible(tmp_path: Path) -> None:
    bundle = build_bundle(tmp_path)
    tc = FakeToolchain(
        axioms={"max_ari_bound": "'max_ari_bound' depends on axioms: [propext, Classical.choice, Quot.sound]"}
    )
    code = clp.main(["--bundle", str(bundle), "--repo-commit", REPO_COMMIT], toolchain=tc)
    assert code == clp.EXIT_ADMISSIBLE == 0


def test_main_exit_inadmissible(tmp_path: Path) -> None:
    bundle = build_bundle(tmp_path)
    tc = FakeToolchain(build_exit=1)
    code = clp.main(["--bundle", str(bundle), "--repo-commit", REPO_COMMIT], toolchain=tc)
    assert code == clp.EXIT_INADMISSIBLE == 1


def test_main_exit_env_error(tmp_path: Path) -> None:
    code = clp.main(
        ["--bundle", str(tmp_path / "nope"), "--repo-commit", REPO_COMMIT],
        toolchain=FakeToolchain(),
    )
    assert code == clp.EXIT_ENV_ERROR == 2


def test_main_emits_discrepancy_file(tmp_path: Path) -> None:
    bundle = build_bundle(
        tmp_path,
        manifest_extra={
            "artefact_constants": [
                {
                    "name": "greedyValue margins",
                    "recorded_value": "60862049",
                    "artefact_id": "res_s2_greedy_2026-07-07",
                    "artefact_hash": "sha256:aaa",
                }
            ]
        },
    )
    disc_path = tmp_path / "discrepancies.json"
    code = clp.main(
        [
            "--bundle",
            str(bundle),
            "--repo-commit",
            REPO_COMMIT,
            "--emit-discrepancies",
            str(disc_path),
        ],
        toolchain=FakeToolchain(),
    )
    assert code == clp.EXIT_INADMISSIBLE
    assert disc_path.is_file()
    recorded = json.loads(disc_path.read_text(encoding="utf-8"))
    assert recorded[0]["derived_value"] == "60862048"


# --------------------------------------------------------------------------- #
# Pure-helper unit checks                                                      #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (
            "'t' depends on axioms: [propext, Classical.choice, Quot.sound]",
            {"propext", "Classical.choice", "Quot.sound"},
        ),
        ("'t' does not depend on any axioms", set()),
        ("'t' depends on axioms: [propext, Lean.ofReduceBool]", {"propext", "Lean.ofReduceBool"}),
        ("'t' depends on axioms: [sorryAx, propext]", {"sorryAx", "propext"}),
    ],
)
def test_parse_axiom_set(output: str, expected: set[str]) -> None:
    assert clp.parse_axiom_set(output) == expected


def test_native_decide_axiom_caught_by_audit(tmp_path: Path) -> None:
    """Defence in depth - native_decide's Lean.ofReduceBool also fails the axiom audit."""
    bundle = build_bundle(tmp_path)
    tc = FakeToolchain(axioms={"max_ari_bound": "'max_ari_bound' depends on axioms: [propext, Lean.ofReduceBool]"})
    outcome = clp.accept_bundle(bundle, REPO_COMMIT, tc)
    assert not outcome.admissible
    assert "axiom-audit" in outcome.failed_items
