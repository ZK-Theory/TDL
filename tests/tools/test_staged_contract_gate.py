"""The contract gate must validate index bytes, not unrelated working-copy bytes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / ".claude" / "hooks" / "run_staged_contract_gate.py"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def test_staged_runner_uses_index_bytes_and_preserves_working_copy(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    validator = repo / ".claude" / "hooks" / "contract_binding_check.py"
    validator.parent.mkdir(parents=True)
    validator.write_text(
        "from pathlib import Path\n"
        "ok = Path('.git').exists() and Path('governed.txt').read_text(encoding='utf-8') == 'staged\\n'\n"
        "raise SystemExit(0 if ok else 9)\n",
        encoding="utf-8",
    )
    governed = repo / "governed.txt"
    governed.write_text("staged\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    governed.write_text("unrelated working-copy value\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(RUNNER), "--repo-root", str(repo)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert governed.read_text(encoding="utf-8") == "unrelated working-copy value\n"


def test_staged_runner_propagates_candidate_validator_failure(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    validator = repo / ".claude" / "hooks" / "contract_binding_check.py"
    validator.parent.mkdir(parents=True)
    validator.write_text("raise SystemExit(7)\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")

    result = subprocess.run(
        [sys.executable, str(RUNNER), "--repo-root", str(repo)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 7
