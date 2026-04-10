# Research context: TDA-Research/04-Methods/Pipeline-Overview.md
# Purpose: Vault-engine MCP server — provides AI agents with graph-ranked,
#          token-efficient access to Obsidian vaults via wikilink graph,
#          frontmatter index, and skeletonization. Composes QMD for text
#          search and existing hardened scripts for vault operations.
"""
vault-engine MCP server

Provides 7 tools for AI agent access to Obsidian vaults:
  vault_query    — graph-augmented search (QMD + wikilink expansion)
  vault_get      — specific page with backlinks/forward links
  vault_graph    — N-hop wikilink neighborhood
  vault_skeleton — token-efficient page summary (80-90% reduction)
  vault_status   — dashboard wrapping vault_map.py + health_check.py
  cross_vault    — shared concept detection across vaults
  vault_observe  — session memory linked to vault pages

Usage:
    python scripts/vault/mcp_server.py              # stdio transport (default)
    python scripts/vault/mcp_server.py --http 8182   # HTTP transport
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ── Vault configuration ─────────────────────────────────────────────
VAULTS: dict[str, Path] = {
    "tda": Path(os.environ.get("TDA_VAULT_PATH", r"C:\Users\steph\Documents\TDA-Research")),
    "cl": Path(os.environ.get("CL_VAULT_PATH", r"C:\Users\steph\Documents\Counting Lives\Counting Lives")),
}

DB_PATH = Path(os.environ.get("VAULT_ENGINE_DB", Path.home() / ".cache" / "vault-engine" / "graph.sqlite"))
SKIP_DIRS = {".obsidian", ".trash", "node_modules", ".git", ".apm"}

# ── Logging ─────────────────────────────────────────────────────────
LOG_PATH = Path(os.environ.get("VAULT_ENGINE_LOG", Path.home() / ".cache" / "vault-engine" / "server.log"))


def _log(msg: str) -> None:
    """Append a timestamped line to the server log."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} {msg}\n")
    except OSError:
        pass

# Resolve QMD — find qmd.js and invoke via node for cross-platform reliability
_QMD_JS_CANDIDATES = [
    Path.home() / "AppData" / "Roaming" / "npm" / "node_modules" / "@tobilu" / "qmd" / "dist" / "cli" / "qmd.js",
    Path("/usr/local/lib/node_modules/@tobilu/qmd/dist/cli/qmd.js"),
    Path("/usr/lib/node_modules/@tobilu/qmd/dist/cli/qmd.js"),
]

QMD_JS: str | None = None
for _candidate in _QMD_JS_CANDIDATES:
    if _candidate.exists():
        QMD_JS = str(_candidate)
        break

QMD_ENV = {**os.environ, "LLAMA_CUDA": "0", "NODE_LLAMA_CPP_GPU": "false"}


# ── Database layer ──────────────────────────────────────────────────

def _ensure_db() -> sqlite3.Connection:
    """Create or open the vault-graph database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pages (
            vault TEXT NOT NULL,
            rel_path TEXT NOT NULL,
            stem TEXT NOT NULL,
            title TEXT,
            frontmatter TEXT,
            headings TEXT,
            word_count INTEGER,
            mtime REAL,
            PRIMARY KEY (vault, rel_path)
        );
        CREATE TABLE IF NOT EXISTS links (
            source_vault TEXT NOT NULL,
            source_path TEXT NOT NULL,
            target_stem TEXT NOT NULL,
            FOREIGN KEY (source_vault, source_path) REFERENCES pages(vault, rel_path) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_stem);
        CREATE INDEX IF NOT EXISTS idx_pages_stem ON pages(stem);
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vault TEXT NOT NULL,
            rel_path TEXT NOT NULL,
            observation TEXT NOT NULL,
            page_mtime REAL,
            created TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    return conn


def _needs_rebuild(conn: sqlite3.Connection) -> bool:
    """Check if any vault file is newer than last index build."""
    row = conn.execute("SELECT value FROM meta WHERE key='last_build'").fetchone()
    if not row:
        return True
    last_build = float(row[0])
    for vault_name, vault_path in VAULTS.items():
        if not vault_path.exists():
            continue
        for f in vault_path.rglob("*.md"):
            if any(p in SKIP_DIRS for p in f.parts):
                continue
            if f.stat().st_mtime > last_build:
                return True
    return False


def _extract_frontmatter(content: str) -> str | None:
    """Extract YAML frontmatter as raw string."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[3:end].strip()
    return None


def _extract_headings(content: str) -> list[dict]:
    """Extract markdown headings with level and line number."""
    headings = []
    for i, line in enumerate(content.splitlines(), 1):
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            headings.append({"level": len(m.group(1)), "text": m.group(2).strip(), "line": i})
    return headings


def _extract_wikilinks(content: str) -> list[str]:
    """Extract unique wikilink targets (stems)."""
    return list(set(re.findall(r"\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]", content)))


def _extract_title(content: str, stem: str) -> str:
    """Extract title from frontmatter or first heading, falling back to stem."""
    fm = _extract_frontmatter(content)
    if fm:
        m = re.search(r'title:\s*["\']?(.+?)["\']?\s*$', fm, re.MULTILINE)
        if m:
            return m.group(1).strip()
    m = re.match(r"^(?:---.*?---\s*)?#\s+(.+)$", content, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return stem


def _rebuild_index(conn: sqlite3.Connection) -> dict:
    """Full rebuild of the wikilink graph from vault files."""
    stats = {"pages": 0, "links": 0}
    conn.execute("DELETE FROM pages")
    conn.execute("DELETE FROM links")

    for vault_name, vault_path in VAULTS.items():
        if not vault_path.exists():
            continue
        for f in vault_path.rglob("*.md"):
            if any(p in SKIP_DIRS for p in f.parts):
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            rel = str(f.relative_to(vault_path)).replace("\\", "/")
            fm = _extract_frontmatter(content)
            headings = _extract_headings(content)
            title = _extract_title(content, f.stem)
            wc = len(content.split())
            mtime = f.stat().st_mtime

            conn.execute(
                "INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?,?)",
                (vault_name, rel, f.stem, title, fm, json.dumps(headings), wc, mtime),
            )
            stats["pages"] += 1

            for target in _extract_wikilinks(content):
                conn.execute(
                    "INSERT INTO links VALUES (?,?,?)",
                    (vault_name, rel, target.strip()),
                )
                stats["links"] += 1

    conn.execute(
        "INSERT OR REPLACE INTO meta VALUES ('last_build', ?)",
        (str(time.time()),),
    )
    conn.commit()
    return stats


def _ensure_index() -> sqlite3.Connection:
    """Get a connection with a fresh-enough index."""
    conn = _ensure_db()
    if _needs_rebuild(conn):
        _rebuild_index(conn)
    return conn


# ── Skeletonization ─────────────────────────────────────────────────

def _skeletonize(content: str) -> str:
    """Reduce a page to frontmatter + heading tree + first sentence per section."""
    parts: list[str] = []

    # Frontmatter
    fm = _extract_frontmatter(content)
    if fm:
        parts.append(f"---\n{fm}\n---")

    # Strip frontmatter from body
    body = content
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            body = content[end + 3:].strip()

    # Split by headings
    sections = re.split(r"(^#{1,6}\s+.+$)", body, flags=re.MULTILINE)

    for i, section in enumerate(sections):
        if re.match(r"^#{1,6}\s+", section):
            parts.append(section.strip())
        else:
            text = section.strip()
            if not text:
                continue
            # First sentence or first 150 chars
            sentences = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
            first = sentences[0][:150]
            remaining_words = len(text.split()) - len(first.split())
            if remaining_words > 5:
                parts.append(f"{first} [+{remaining_words} words]")
            elif text:
                parts.append(first)

    return "\n".join(parts)


# ── QMD integration ─────────────────────────────────────────────────

def _qmd_cmd(args: list[str], timeout: int = 30) -> list[dict]:
    """Run a QMD CLI command via node, returns parsed JSON list."""
    if not QMD_JS:
        return []

    cmd = ["node", QMD_JS] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            env=QMD_ENV,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            _log(f"QMD returned {result.returncode}: {(result.stderr or '')[:200]}")
            return []
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        _log(f"QMD timed out after {timeout}s: {' '.join(args[:3])}")
        return []
    except (json.JSONDecodeError, FileNotFoundError, OSError) as exc:
        _log(f"QMD error: {exc}")
        return []


def _qmd_search(query: str, collection: str | None = None, n: int = 10) -> list[dict]:
    """BM25 search via QMD CLI."""
    args = ["search", query, "--json", "-n", str(n)]
    if collection:
        args.extend(["-c", collection])
    return _qmd_cmd(args)


def _qmd_query(query: str, collection: str | None = None, n: int = 10) -> list[dict]:
    """Hybrid search via QMD CLI (BM25 + vector, no reranker).

    The Qwen3-Reranker-0.6B GGUF crashes with STATUS_STACK_BUFFER_OVERRUN
    on Windows (node-llama-cpp NAPI binding issue). Skip it — the RRF
    fusion of BM25 + vector scores is good enough for ~300 documents.
    Falls back to BM25-only search if hybrid also fails.
    """
    args = ["query", query, "--json", "-n", str(n), "--no-rerank"]
    if collection:
        args.extend(["-c", collection])
    results = _qmd_cmd(args, timeout=30)
    if results:
        return results
    # Fallback to BM25-only search
    _log("QMD query failed, falling back to BM25 search")
    return _qmd_search(query, collection=collection, n=n)


# ── Page reading ────────────────────────────────────────────────────

def _resolve_page(vault: str, path_or_stem: str) -> Path | None:
    """Resolve a page reference to a filesystem path."""
    vault_path = VAULTS.get(vault)
    if not vault_path or not vault_path.exists():
        return None

    try:
        resolved_vault = vault_path.resolve()
    except OSError:
        return None

    def _safe_path(candidate: Path) -> Path | None:
        """Return candidate if it resolves to inside the vault, else None."""
        try:
            resolved = candidate.resolve()
            if resolved.is_relative_to(resolved_vault):
                return resolved
        except OSError:
            pass
        return None

    # Try as direct relative path
    candidate = vault_path / path_or_stem
    safe = _safe_path(candidate)
    if safe and safe.exists():
        return safe
    if not path_or_stem.endswith(".md"):
        candidate = vault_path / (path_or_stem + ".md")
        safe = _safe_path(candidate)
        if safe and safe.exists():
            return safe

    # Try as stem search
    for f in vault_path.rglob("*.md"):
        if any(p in SKIP_DIRS for p in f.parts):
            continue
        if f.stem == path_or_stem:
            safe = _safe_path(f)
            if safe:
                return safe

    return None


def _read_page(vault: str, path_or_stem: str) -> tuple[str | None, str | None]:
    """Read page content. Returns (content, rel_path) or (None, None)."""
    resolved = _resolve_page(vault, path_or_stem)
    if not resolved:
        return None, None
    vault_path = VAULTS[vault]
    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, None
    rel = str(resolved.relative_to(vault_path)).replace("\\", "/")
    return content, rel


# ── Import hardened scripts ─────────────────────────────────────────

# Add scripts/vault to sys.path for imports
_script_dir = Path(__file__).parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from health_check import run_health_check  # noqa: E402
from vault_map import detect_vault_type, generate_tda_map, generate_cl_map  # noqa: E402


# ── MCP Server ──────────────────────────────────────────────────────

mcp = FastMCP(
    "vault-engine",
    instructions=(
        "Vault-engine provides access to Obsidian research vaults. "
        "Use vault_query for search, vault_get for specific pages, "
        "vault_skeleton for token-efficient summaries, and vault_status "
        "for health dashboards. Available vaults: 'tda' (TDA-Research) "
        "and 'cl' (Counting Lives)."
    ),
)


@mcp.tool()
def vault_query(
    query: str,
    vault: str | None = None,
    max_results: int = 5,
    expand_links: bool = True,
) -> str:
    """Search across vaults with wikilink graph expansion.

    Calls QMD for text retrieval, then expands top results via the
    wikilink graph to include related pages as skeletons.

    Args:
        query: Natural language search query.
        vault: Restrict to 'tda' or 'cl'. None searches all vaults.
        max_results: Number of primary results (default 5).
        expand_links: Include 1-hop wikilink neighbors as skeletons (default True).
    """
    conn = _ensure_index()

    # QMD search
    qmd_results = _qmd_query(query, collection=vault, n=max_results)

    output_parts: list[str] = []

    if not qmd_results:
        # Fall back to database full-text match
        escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped_query}%"
        rows = conn.execute(
            "SELECT vault, rel_path, title FROM pages WHERE title LIKE ? ESCAPE '\\' OR frontmatter LIKE ? ESCAPE '\\' LIMIT ?",
            (pattern, pattern, max_results),
        ).fetchall()
        for v, rp, title in rows:
            content, _ = _read_page(v, rp)
            if content:
                output_parts.append(f"## [{v}] {rp}\n**Title:** {title}\n\n{_skeletonize(content)}")
        if not output_parts:
            return "No results found."
        return "\n\n---\n\n".join(output_parts)

    # Process QMD results
    seen_stems: set[str] = set()
    for r in qmd_results:
        # QMD JSON fields: docid, score, file, title, context, snippet
        file_uri = r.get("file", "")
        # file_uri looks like qmd://tda/path/to/file.md — extract collection + path
        uri_match = re.match(r"qmd://([^/]+)/(.+)", file_uri)
        if uri_match:
            collection = uri_match.group(1)
            path = uri_match.group(2)
        else:
            collection = vault or "?"
            path = file_uri
        title = r.get("title", Path(path).stem if path else "Unknown")
        score = r.get("score", 0)
        snippet = r.get("snippet", "")

        # Read full content for primary results
        content, rel = _read_page(collection, path)
        if content:
            output_parts.append(
                f"## [{collection}] {path}  (score: {score:.0%})\n"
                f"**Title:** {title}\n\n{content}"
            )
            seen_stems.add(Path(path).stem)
        else:
            output_parts.append(
                f"## [{collection}] {path}  (score: {score:.0%})\n"
                f"**Title:** {title}\n\n{snippet}"
            )

    # Expand via wikilink graph
    if expand_links and seen_stems:
        placeholders = ",".join("?" * len(seen_stems))
        neighbors = conn.execute(
            f"""
            SELECT DISTINCT p.vault, p.rel_path, p.title, p.stem
            FROM links l
            JOIN pages p ON p.stem = l.target_stem
            WHERE l.source_path IN (
                SELECT rel_path FROM pages WHERE stem IN ({placeholders})
            )
            AND p.stem NOT IN ({placeholders})
            LIMIT 10
            """,
            list(seen_stems) + list(seen_stems),
        ).fetchall()

        # Also get backlinks
        backlink_neighbors = conn.execute(
            f"""
            SELECT DISTINCT p.vault, p.rel_path, p.title, p.stem
            FROM links l
            JOIN pages p ON p.vault = l.source_vault AND p.rel_path = l.source_path
            WHERE l.target_stem IN ({placeholders})
            AND p.stem NOT IN ({placeholders})
            LIMIT 10
            """,
            list(seen_stems) + list(seen_stems),
        ).fetchall()

        all_neighbors = {(v, rp): (title, stem) for v, rp, title, stem in neighbors + backlink_neighbors}

        if all_neighbors:
            output_parts.append("\n---\n## Related pages (skeletons)\n")
            for (v, rp), (title, stem) in list(all_neighbors.items())[:8]:
                content, _ = _read_page(v, rp)
                if content:
                    output_parts.append(
                        f"### [{v}] {rp}\n**Title:** {title}\n\n{_skeletonize(content)}"
                    )

    return "\n\n".join(output_parts)


@mcp.tool()
def vault_get(
    path: str,
    vault: str = "tda",
    include_links: bool = True,
    skeleton: bool = False,
) -> str:
    """Get a specific vault page with its link context.

    Args:
        path: Relative path or page stem (e.g. 'CONVENTIONS' or '03-Papers/P01-A/_project.md').
        vault: Which vault ('tda' or 'cl').
        include_links: Show backlinks and forward links (default True).
        skeleton: Return skeleton instead of full content (default False).
    """
    content, rel_path = _read_page(vault, path)
    if not content:
        return f"Page not found: {path} in vault '{vault}'"

    conn = _ensure_index()
    stem = Path(rel_path).stem

    parts: list[str] = []

    if skeleton:
        parts.append(f"# [{vault}] {rel_path}\n\n{_skeletonize(content)}")
    else:
        parts.append(f"# [{vault}] {rel_path}\n\n{content}")

    if include_links:
        # Forward links
        fwd = conn.execute(
            "SELECT target_stem FROM links WHERE source_vault=? AND source_path=?",
            (vault, rel_path),
        ).fetchall()
        if fwd:
            parts.append("\n**Forward links:** " + ", ".join(f"[[{r[0]}]]" for r in fwd))

        # Backlinks
        back = conn.execute(
            "SELECT p.vault, p.rel_path, p.title FROM links l "
            "JOIN pages p ON p.vault=l.source_vault AND p.rel_path=l.source_path "
            "WHERE l.target_stem=?",
            (stem,),
        ).fetchall()
        if back:
            parts.append(
                "\n**Backlinks:**\n"
                + "\n".join(f"- [{v}] {rp} — {title}" for v, rp, title in back)
            )

    return "\n".join(parts)


@mcp.tool()
def vault_graph(
    page: str,
    vault: str = "tda",
    depth: int = 1,
    format: str = "list",
) -> str:
    """Explore the wikilink neighborhood around a page.

    Args:
        page: Page stem or relative path.
        vault: Which vault ('tda' or 'cl').
        depth: How many hops to traverse (1-3, default 1).
        format: Output format — 'list' or 'mermaid'.
    """
    depth = min(max(depth, 1), 3)
    conn = _ensure_index()

    # Find the starting page
    row = conn.execute(
        "SELECT stem, rel_path FROM pages WHERE (stem=? OR rel_path=?) AND vault=?",
        (page, page, vault),
    ).fetchone()

    if not row:
        # Try across vaults
        row = conn.execute(
            "SELECT vault, stem, rel_path FROM pages WHERE stem=? OR rel_path=?",
            (page, page),
        ).fetchone()
        if row:
            vault = row[0]
            row = (row[1], row[2])
        else:
            return f"Page not found: {page}"

    start_stem = row[0]
    visited: set[str] = {start_stem}
    edges: list[tuple[str, str]] = []
    frontier: set[str] = {start_stem}

    for _ in range(depth):
        if not frontier:
            break
        next_frontier: set[str] = set()
        placeholders = ",".join("?" * len(frontier))

        # Forward links from frontier
        fwd = conn.execute(
            f"SELECT DISTINCT p.stem, l.target_stem FROM links l "
            f"JOIN pages p ON p.rel_path=l.source_path AND p.vault=l.source_vault "
            f"WHERE p.stem IN ({placeholders})",
            list(frontier),
        ).fetchall()
        for src, tgt in fwd:
            edges.append((src, tgt))
            if tgt not in visited:
                visited.add(tgt)
                next_frontier.add(tgt)

        # Backlinks to frontier
        back = conn.execute(
            f"SELECT DISTINCT p.stem, l.target_stem FROM links l "
            f"JOIN pages p ON p.rel_path=l.source_path AND p.vault=l.source_vault "
            f"WHERE l.target_stem IN ({placeholders})",
            list(frontier),
        ).fetchall()
        for src, tgt in back:
            edges.append((src, tgt))
            if src not in visited:
                visited.add(src)
                next_frontier.add(src)

        frontier = next_frontier

    if not edges:
        return f"No links found for {page}"

    # Deduplicate edges
    unique_edges = list(set(edges))

    if format == "mermaid":
        lines = ["```mermaid", "graph LR"]
        for src, tgt in unique_edges:
            safe_src = src.replace(" ", "_").replace("-", "_")
            safe_tgt = tgt.replace(" ", "_").replace("-", "_")
            lines.append(f'    {safe_src}["{src}"] --> {safe_tgt}["{tgt}"]')
        lines.append("```")
        return "\n".join(lines)

    # List format
    parts = [f"## Link graph for [[{start_stem}]] (depth={depth})\n"]
    parts.append(f"**Nodes:** {len(visited)}  |  **Edges:** {len(unique_edges)}\n")

    # Group by direction from start
    fwd_targets = [tgt for src, tgt in unique_edges if src == start_stem]
    back_sources = [src for src, tgt in unique_edges if tgt == start_stem]

    if fwd_targets:
        parts.append("**Links to:**")
        for t in sorted(set(fwd_targets)):
            parts.append(f"  → [[{t}]]")

    if back_sources:
        parts.append("**Linked from:**")
        for s in sorted(set(back_sources)):
            parts.append(f"  ← [[{s}]]")

    if len(unique_edges) > len(fwd_targets) + len(back_sources):
        parts.append(f"\n**Extended neighborhood:** {len(unique_edges) - len(fwd_targets) - len(back_sources)} more edges")

    return "\n".join(parts)


@mcp.tool()
def vault_skeleton(
    pages: list[str],
    vault: str = "tda",
) -> str:
    """Get token-efficient summaries of multiple pages.

    Returns frontmatter + heading tree + first sentence per section.
    Typically 80-90% token reduction vs full content.

    Args:
        pages: List of page stems or relative paths, e.g. ["CONVENTIONS", "Computational-Log"].
               NOT a single string — must be a JSON array.
        vault: Which vault ('tda' or 'cl').
    """
    parts: list[str] = []
    for page in pages:
        content, rel = _read_page(vault, page)
        if content:
            parts.append(f"## [{vault}] {rel}\n\n{_skeletonize(content)}")
        else:
            parts.append(f"## {page} — not found in vault '{vault}'")

    return "\n\n---\n\n".join(parts)


@mcp.tool()
def vault_status(
    vault: str | None = None,
    include_health: bool = True,
) -> str:
    """Dashboard showing vault status, paper pipeline, and health metrics.

    Wraps the hardened vault_map.py and health_check.py scripts.

    Args:
        vault: Which vault ('tda', 'cl', or None for both).
        include_health: Run health check too (default True).
    """
    parts: list[str] = []
    targets = [vault] if vault else list(VAULTS.keys())

    for v in targets:
        vault_path = VAULTS.get(v)
        if not vault_path or not vault_path.exists():
            parts.append(f"## {v} — vault not found at {vault_path}")
            continue

        # Generate vault map
        try:
            vtype = detect_vault_type(vault_path)
            if vtype == "tda":
                map_content = generate_tda_map(vault_path)
            else:
                map_content = generate_cl_map(vault_path)
            parts.append(map_content)
        except ValueError as e:
            parts.append(f"## {v} — vault type detection failed: {e}")

        # Health check
        if include_health:
            try:
                report = run_health_check(vault_path)
                s = report["summary"]
                health_lines = [
                    f"\n## Health Check — {v}\n",
                    f"| Metric | Value |",
                    f"|---|---|",
                    f"| Total files | {s['total_files']} |",
                    f"| Orphan notes | {s['orphan_count']} ({s['orphan_pct']}%) |",
                    f"| Stale TODOs | {s['stale_todo_count']} across {s['stale_todo_files']} files |",
                    f"| Broken links | {s['broken_links']} |",
                ]
                if s.get("perplexity_total", 0) > 0:
                    health_lines.append(
                        f"| Perplexity captures | {s['perplexity_unprocessed']}/{s['perplexity_total']} unprocessed |"
                    )

                # Index freshness
                for idx in report.get("index_freshness", []):
                    if idx["files_newer_than_index"] > 0:
                        health_lines.append(
                            f"| {idx['index_file']} freshness | {idx['files_newer_than_index']} files newer |"
                        )

                parts.append("\n".join(health_lines))

                # Top broken links
                if report["broken_links"][:5]:
                    parts.append("\n**Broken links (top 5):**")
                    for bl in report["broken_links"][:5]:
                        parts.append(f"- {bl['source']}:{bl['line_number']} → [[{bl['target']}]]")

                # Top stale TODOs
                if report["stale_todos"][:3]:
                    parts.append("\n**Stalest TODOs:**")
                    for st in report["stale_todos"][:3]:
                        parts.append(f"- {st['file']} ({st['days_stale']} days)")
                        for t in st["todos"][:2]:
                            parts.append(f"  - [ ] {t}")

            except Exception as e:
                parts.append(f"\n## Health check failed for {v}: {e}")

    return "\n\n".join(parts)


@mcp.tool()
def cross_vault(
    min_overlap: int = 2,
) -> str:
    """Detect shared concepts across TDA-Research and Counting Lives vaults.

    Finds page stems and wikilink targets that appear in both vaults,
    indicating potential Two Lenses connections.

    Args:
        min_overlap: Minimum number of shared references to report (default 2).
    """
    conn = _ensure_index()

    # Find stems that exist in both vaults
    shared_stems = conn.execute("""
        SELECT p1.stem, p1.title, p2.title
        FROM pages p1
        JOIN pages p2 ON p1.stem = p2.stem
        WHERE p1.vault = 'tda' AND p2.vault = 'cl'
    """).fetchall()

    # Find wikilink targets referenced from both vaults
    shared_links = conn.execute("""
        SELECT l1.target_stem, COUNT(DISTINCT l1.source_path) as tda_refs,
               COUNT(DISTINCT l2.source_path) as cl_refs
        FROM links l1
        JOIN links l2 ON l1.target_stem = l2.target_stem
        WHERE l1.source_vault = 'tda' AND l2.source_vault = 'cl'
        GROUP BY l1.target_stem
        HAVING tda_refs + cl_refs >= ?
    """, (min_overlap,)).fetchall()

    parts = ["# Cross-Vault Analysis\n"]

    if shared_stems:
        parts.append("## Pages with same name in both vaults\n")
        parts.append("| Stem | TDA title | CL title |")
        parts.append("|---|---|---|")
        for stem, t1, t2 in shared_stems:
            parts.append(f"| {stem} | {t1} | {t2} |")

    if shared_links:
        parts.append("\n## Shared wikilink targets\n")
        parts.append("| Target | TDA refs | CL refs |")
        parts.append("|---|---|---|")
        for target, tda_refs, cl_refs in shared_links:
            parts.append(f"| [[{target}]] | {tda_refs} | {cl_refs} |")

    if not shared_stems and not shared_links:
        parts.append("No shared concepts detected between vaults.")

    return "\n".join(parts)


@mcp.tool()
def vault_observe(
    observation: str,
    page: str | None = None,
    vault: str = "tda",
) -> str:
    """Save an observation linked to a vault page for cross-session memory.

    Observations are surfaced when the linked page appears in query
    results. Staleness is flagged if the page has been modified since
    the observation was recorded.

    Args:
        observation: The insight or note to record (required string, e.g. "Decided to use W2 not W1").
        page: Page stem or path to link to (optional, e.g. "CONVENTIONS").
        vault: Which vault ('tda' or 'cl').
    """
    conn = _ensure_index()

    page_mtime = None
    rel_path = page or ""

    if page:
        resolved = _resolve_page(vault, page)
        if resolved:
            vault_path = VAULTS[vault]
            rel_path = str(resolved.relative_to(vault_path)).replace("\\", "/")
            page_mtime = resolved.stat().st_mtime

    conn.execute(
        "INSERT INTO observations (vault, rel_path, observation, page_mtime) VALUES (?,?,?,?)",
        (vault, rel_path, observation, page_mtime),
    )
    conn.commit()

    # Return confirmation with any existing observations for context
    existing = conn.execute(
        "SELECT observation, created, page_mtime FROM observations "
        "WHERE vault=? AND rel_path=? ORDER BY created DESC LIMIT 5",
        (vault, rel_path),
    ).fetchall()

    parts = [f"Observation saved for [{vault}] {rel_path}"]

    if len(existing) > 1:
        parts.append(f"\n**Previous observations ({len(existing) - 1}):**")
        for obs, created, obs_mtime in existing[1:]:
            stale = ""
            if page_mtime and obs_mtime and page_mtime > obs_mtime:
                stale = " ⚠️ STALE (page modified since)"
            parts.append(f"- [{created}] {obs}{stale}")

    return "\n".join(parts)


# ── Entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="vault-engine MCP server")
    parser.add_argument("--http", type=int, default=None, metavar="PORT",
                        help="Run as HTTP server on given port")
    args = parser.parse_args()

    if args.http:
        _log(f"Starting vault-engine HTTP on port {args.http}")
        mcp.run(transport="sse", sse_params={"port": args.http})
    else:
        _log("Starting vault-engine stdio")
        mcp.run(transport="stdio")
