#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        file_path = payload.get("tool_input", {}).get("file_path")
        if not file_path:
            return 0
        path = Path(file_path)
        if path.suffix != ".py":
            return 0
        for cmd in [["uv", "run", "ruff", "check", "--fix", str(path)], ["uv", "run", "ruff", "format", str(path)]]:
            subprocess.run(cmd, check=False)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
