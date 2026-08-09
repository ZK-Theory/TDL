from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from research_system.methods import MethodsPackError, verify_methods_pack_history


REPO_ROOT = Path(__file__).resolve().parents[3]
METHODS_ROOT = Path(".research-system/methods")
SCHEMA_ROOT = Path(".research-system/schemas/methods")
HISTORY_PATH = ".research-system/methods/methods-pack-revisions.yaml"


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> str:
    completed = subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-C", str(root), *args],
        input=input_bytes,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    return completed.stdout.decode("ascii").strip()


def _write_yaml(path: Path, value: object) -> None:
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )


def _yaml(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _init_repo(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--initial-branch=main")
    _git(root, "config", "user.name", "RM History Test")
    _git(root, "config", "user.email", "rm-history@example.invalid")
    (root / "README.md").write_text("history root\n", encoding="utf-8", newline="\n")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "base")
    base = _git(root, "rev-parse", "HEAD")

    shutil.copytree(REPO_ROOT / METHODS_ROOT, root / METHODS_ROOT)
    shutil.copytree(REPO_ROOT / SCHEMA_ROOT, root / SCHEMA_ROOT)
    _git(root, "add", ".research-system")
    _git(root, "commit", "-m", "candidate")
    subject = _git(root, "rev-parse", "HEAD")
    return root, base, subject


def _blob(root: Path, revision: str, path: str = HISTORY_PATH) -> str:
    return _git(root, "rev-parse", f"{revision}:{path}")


def _commit_valid_revision(root: Path, base: str) -> str:
    asset_path = root / METHODS_ROOT / "assets/decomposition-scaffolding-template.md"
    asset_text = asset_path.read_text(encoding="utf-8").replace("version: 1.0.0", "version: 1.1.0", 1)
    asset_path.write_text(asset_text + "\nRevision note: clarify stopping conditions.\n", encoding="utf-8")
    identity = _git(
        root,
        "hash-object",
        "--no-filters",
        "--stdin",
        input_bytes=asset_path.read_bytes().replace(b"\r\n", b"\n"),
    )

    manifest_path = root / METHODS_ROOT / "methods-pack.yaml"
    manifest = _yaml(manifest_path)
    assets = manifest["assets"]
    assert isinstance(assets, list)
    row = next(item for item in assets if item["asset_id"] == "mth_decomposition_scaffolding_template")
    row["version"] = "1.1.0"
    row["identity"] = identity
    _write_yaml(manifest_path, manifest)

    history_path = root / HISTORY_PATH
    history = _yaml(history_path)
    revisions = history["revisions"]
    assert isinstance(revisions, list)
    revisions.append(
        {
            "asset_id": "mth_decomposition_scaffolding_template",
            "version": "1.1.0",
            "identity_scheme": "git_blob_sha1",
            "identity": identity,
            "recorded_at": "2026-08-08",
            "revision_reason": "Clarify the operator stopping condition.",
            "supersedes_identity": next(
                item["identity"] for item in revisions if item["asset_id"] == "mth_decomposition_scaffolding_template"
            ),
            "previous_history_blob": _blob(root, base),
        }
    )
    _write_yaml(history_path, history)
    _git(root, "add", ".research-system")
    _git(root, "commit", "-m", "append valid revision")
    return _git(root, "rev-parse", "HEAD")


def test_methods_pack_history_accepts_genesis_from_independently_absent_base(tmp_path: Path) -> None:
    root, base, subject = _init_repo(tmp_path)

    verified = verify_methods_pack_history(root, base_ref=base, subject_ref=subject)

    assert verified.base_history_blob is None
    assert verified.subject_history_blob == _blob(root, subject)
    assert verified.asset_count == 5


def test_methods_pack_history_accepts_ordered_append_bound_to_prior_blob(tmp_path: Path) -> None:
    root, _, base = _init_repo(tmp_path)
    subject = _commit_valid_revision(root, base)

    verified = verify_methods_pack_history(root, base_ref=base, subject_ref=subject)

    assert verified.base_history_blob == _blob(root, base)
    assert verified.subject_history_blob == _blob(root, subject)
    assert verified.revision_count == 6


@pytest.mark.parametrize("mutation", ["delete", "reorder", "duplicate", "extra"])
def test_methods_pack_history_rejects_prefix_rewrites(tmp_path: Path, mutation: str) -> None:
    root, _, base = _init_repo(tmp_path)
    subject = _commit_valid_revision(root, base)
    _git(root, "reset", "--hard", subject)
    path = root / HISTORY_PATH
    history = _yaml(path)
    revisions = history["revisions"]
    assert isinstance(revisions, list)
    if mutation == "delete":
        del revisions[0]
    elif mutation == "reorder":
        revisions[0], revisions[1] = revisions[1], revisions[0]
    elif mutation == "duplicate":
        revisions.insert(1, dict(revisions[0]))
    else:
        revisions.append(dict(revisions[-1]) | {"asset_id": "mth_foreign_asset"})
    _write_yaml(path, history)
    _git(root, "add", HISTORY_PATH)
    _git(root, "commit", "-m", f"invalid {mutation}")
    bad_subject = _git(root, "rev-parse", "HEAD")

    with pytest.raises(MethodsPackError, match="prefix|duplicate|unknown|current manifest"):
        verify_methods_pack_history(root, base_ref=base, subject_ref=bad_subject)


def test_methods_pack_history_rejects_coordinated_asset_manifest_history_replacement(tmp_path: Path) -> None:
    root, _, base = _init_repo(tmp_path)
    _commit_valid_revision(root, base)
    history_path = root / HISTORY_PATH
    history = _yaml(history_path)
    revisions = history["revisions"]
    assert isinstance(revisions, list)
    history["revisions"] = [dict(revisions[-1]) | {"previous_history_blob": _blob(root, base)}]
    _write_yaml(history_path, history)
    _git(root, "add", ".research-system")
    _git(root, "commit", "-m", "coordinated replacement")
    replaced = _git(root, "rev-parse", "HEAD")

    with pytest.raises(MethodsPackError, match="retained ordered prefix"):
        verify_methods_pack_history(root, base_ref=base, subject_ref=replaced)


def test_methods_pack_history_rejects_wrong_previous_blob(tmp_path: Path) -> None:
    root, _, base = _init_repo(tmp_path)
    _commit_valid_revision(root, base)
    path = root / HISTORY_PATH
    history = _yaml(path)
    revisions = history["revisions"]
    assert isinstance(revisions, list)
    revisions[-1]["previous_history_blob"] = "0" * 40
    _write_yaml(path, history)
    _git(root, "add", HISTORY_PATH)
    _git(root, "commit", "-m", "wrong prior blob")
    bad_subject = _git(root, "rev-parse", "HEAD")

    with pytest.raises(MethodsPackError, match="previous_history_blob"):
        verify_methods_pack_history(root, base_ref=base, subject_ref=bad_subject)


def test_methods_pack_history_rejects_non_ancestor_base(tmp_path: Path) -> None:
    root, base, subject = _init_repo(tmp_path)
    _git(root, "switch", "--orphan", "foreign")
    (root / "foreign.txt").write_text("foreign\n", encoding="utf-8")
    _git(root, "add", "foreign.txt")
    _git(root, "commit", "-m", "foreign")
    foreign = _git(root, "rev-parse", "HEAD")

    with pytest.raises(MethodsPackError, match="not an ancestor"):
        verify_methods_pack_history(root, base_ref=foreign, subject_ref=subject)

    assert base != foreign
