from __future__ import annotations

from pathlib import Path

import pytest

from research_system.discovery.path_safety import contained_regular_file
from research_system.errors import IntegrityError


def test_contained_regular_file_rejects_traversal_absolute_and_redirected_paths(tmp_path: Path) -> None:
    root = tmp_path / "control"
    root.mkdir()
    accepted = root / "methods" / "documents" / "result.json"
    accepted.parent.mkdir(parents=True)
    accepted.write_text("{}", encoding="utf-8")
    assert contained_regular_file(root, "methods/documents/result.json", label="registered result") == accepted

    for relative in ("../outside.json", str((tmp_path / "outside.json").resolve())):
        with pytest.raises(IntegrityError, match="canonical and relative"):
            contained_regular_file(root, relative, label="registered result")

    external = tmp_path / "external.json"
    external.write_text("{}", encoding="utf-8")
    redirected = root / "methods" / "documents" / "redirected.json"
    try:
        redirected.symlink_to(external)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(IntegrityError, match="reparse component"):
        contained_regular_file(root, "methods/documents/redirected.json", label="registered result")
    assert external.read_text(encoding="utf-8") == "{}"
