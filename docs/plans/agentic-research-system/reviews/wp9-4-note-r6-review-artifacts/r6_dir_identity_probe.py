# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 6, §10.2, R5-i2)
# Purpose: R6 review probe. Can a directory's identity come "from fstat on the bound handle" (revision 6), and does
# the store's directory anchor give the same numbers in the reader's encoding? Is a directory's link count stable
# when entries are added? Scratch directory only.
"""Probe for the review of WP9.4 design note revision 6 (R6-i1).

Run from the worktree root:
    uv run --env-file .env python docs/plans/agentic-research-system/reviews/wp9-4-note-r6-review-artifacts/r6_dir_identity_probe.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from research_system.store.anchor import open_registered_root_anchor


def main() -> int:
    print(f"platform={sys.platform} python={sys.version.split()[0]}")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve() / "papers" / "P01-A-JRSSA"
        root.mkdir(parents=True)
        try:
            fd = os.open(root, os.O_RDONLY)
        except OSError as exc:
            print(f"os.open(directory) for os.fstat: REFUSED ({type(exc).__name__}: {exc.strerror})")
        else:
            print(f"os.open(directory): ok, fstat st_ino={os.fstat(fd).st_ino}")
            os.close(fd)
        st = os.stat(root)
        anchor = open_registered_root_anchor(root, delete_protect=False)
        try:
            ident = anchor.identity
            order = "little" if ident.scheme == "windows-file-id-v1" else "big"
            as_int = int.from_bytes(ident.file_id, order, signed=False)
            print(f"anchor scheme={ident.scheme}")
            print(f"anchor volume == st_dev: {ident.volume_or_device == st.st_dev}")
            print(f"anchor file_id ({order}-endian int) == st_ino: {as_int == st.st_ino}")
        finally:
            anchor.close()
        before = os.stat(root).st_nlink
        (root / "drafts").mkdir()
        (root / "a.md").write_bytes(b"a\n")
        after = os.stat(root).st_nlink
        print(f"directory st_nlink before={before} after adding a subdirectory and a file={after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
