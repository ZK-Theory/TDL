# Research context: TDA-Research/04-Methods/Pipeline-Overview.md
# Purpose: Refresh the QMD vault index that backs the vault-engine MCP server.
#          Runs `qmd update` (fast full-text re-index, keeps BM25 search fresh)
#          and a best-effort `qmd embed` (CPU vectors for hybrid recall).
#          Intended to be driven by a Windows Scheduled Task; also runnable
#          by hand. See register_refresh_task.ps1 for scheduling.
"""Refresh the QMD index for vault-engine.

Usage:
    python scripts/vault/refresh_index.py            # update + CPU embed
    python scripts/vault/refresh_index.py --no-embed # update only (fast)

Environment:
    XDG_CACHE_HOME  where QMD keeps its index (default: ~/.cache). MUST match
                    the value used by the MCP server, or they read different
                    indexes.
    QMD_LLAMA_GPU   forced to "false" — QMD's bulk embed runs concurrent
                    inference across CUDA contexts which node-llama-cpp aborts
                    on; CPU embedding is reliable.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Locate qmd.js the same way mcp_server.py does.
_QMD_JS_CANDIDATES = [
    Path.home() / "AppData" / "Roaming" / "npm" / "node_modules" / "@tobilu" / "qmd" / "dist" / "cli" / "qmd.js",
    Path("/usr/local/lib/node_modules/@tobilu/qmd/dist/cli/qmd.js"),
    Path("/usr/lib/node_modules/@tobilu/qmd/dist/cli/qmd.js"),
]


def _find_qmd() -> str | None:
    for candidate in _QMD_JS_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return None


def _run(qmd_js: str, sub: str, env: dict, timeout: int) -> tuple[int, str]:
    """Run a qmd subcommand, returning (returncode, tail-of-output)."""
    try:
        result = subprocess.run(
            ["node", qmd_js, sub],
            capture_output=True,
            timeout=timeout,
            env=env,
            encoding="utf-8",
            errors="replace",
        )
        out = (result.stdout or "") + (result.stderr or "")
        return result.returncode, out.strip()[-500:]
    except subprocess.TimeoutExpired:
        return 124, f"{sub} timed out after {timeout}s"
    except OSError as exc:
        return 1, f"{sub} failed: {exc}"


def main() -> int:
    """Refresh the QMD vault index: `qmd update` (required) then `qmd embed`.

    Parses CLI flags (``--no-embed`` to skip the slow CPU embed step,
    ``--embed-timeout`` for the embed cap) and runs the QMD subcommands with
    ``XDG_CACHE_HOME`` and ``QMD_LLAMA_GPU`` set so it targets the same index
    as the MCP server on CPU. Embedding is best-effort — an embed failure does
    not fail the job, since BM25 search works without vectors.

    Returns:
        Process exit code: ``0`` on success, ``2`` if ``qmd.js`` is not found,
        or the non-zero return code from ``qmd update`` if the update step
        fails (embed failures are swallowed).
    """
    # QMD prints non-ASCII glyphs (e.g. the check mark); the default Windows
    # console codec (cp1252) cannot encode them. Make stdout/stderr tolerant.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Refresh the QMD vault index")
    parser.add_argument("--no-embed", action="store_true", help="skip the (slow) CPU embed step")
    parser.add_argument("--embed-timeout", type=int, default=1800, help="seconds for qmd embed")
    args = parser.parse_args()

    qmd_js = _find_qmd()
    if not qmd_js:
        print("ERROR: qmd.js not found; is @tobilu/qmd installed?", file=sys.stderr)
        return 2

    env = {
        **os.environ,
        "XDG_CACHE_HOME": os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")),
        "QMD_LLAMA_GPU": os.environ.get("QMD_LLAMA_GPU", "false"),
    }

    t0 = time.time()
    rc, out = _run(qmd_js, "update", env, timeout=300)
    print(f"[qmd update] rc={rc} ({time.time() - t0:.1f}s)\n{out}")
    if rc != 0:
        return rc

    if not args.no_embed:
        t1 = time.time()
        rc_e, out_e = _run(qmd_js, "embed", env, timeout=args.embed_timeout)
        print(f"[qmd embed] rc={rc_e} ({time.time() - t1:.1f}s)\n{out_e}")
        # Embedding is best-effort: BM25 search works without it. Don't fail the
        # job (and thus the scheduled task) if only the embed step has trouble.

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
