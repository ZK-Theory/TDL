"""
health_check.py — Hardened vault health check

Performs deterministic checks on an Obsidian vault and outputs a structured
JSON report that skills can interpret and present. The LLM handles
presentation and recommendations; this script handles reliable detection.

Usage:
    python health_check.py <vault_root> [--days 14] [--json] [--output report.json]

Without --json, prints a human-readable summary.
With --json, outputs structured JSON for skill consumption.
"""

import argparse
import json
import re
from pathlib import Path
from datetime import datetime


# Files to exclude from orphan detection
EXCLUDED_STEMS = {
    "INDEX",
    "VAULT-MAP",
    "CONVENTIONS",
    "README",
    "Computational-Log",
    "Pipeline-Overview",
}

# Directory patterns to skip
SKIP_DIRS = {".obsidian", ".trash", "node_modules", ".git"}


def iter_md_files(vault_root: Path):
    """Iterate over all .md files, skipping excluded directories."""
    for f in vault_root.rglob("*.md"):
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        yield f


def find_orphans(vault_root: Path) -> list[str]:
    """
    Find .md files not referenced by any [[wikilink]] in the vault.
    Returns relative paths of orphan files.
    """
    all_files = {}
    all_links = set()

    for f in iter_md_files(vault_root):
        stem = f.stem
        rel = str(f.relative_to(vault_root))
        all_files[stem] = rel

        content = f.read_text(encoding="utf-8", errors="replace")
        # Match [[link]] and [[link|alias]] patterns
        links = re.findall(r"\[\[([^\]|#]+)", content)
        all_links.update(links)

    orphans = []
    for stem, rel in sorted(all_files.items()):
        if stem in EXCLUDED_STEMS:
            continue
        # Skip template files
        if "template" in rel.lower() or "Templates" in rel:
            continue
        # Skip daily notes (they link out, they don't need inbound links)
        if "Daily" in rel or "daily" in rel:
            continue
        # Skip _project.md and _outline.md (structural files)
        if stem.startswith("_"):
            continue
        if stem not in all_links:
            orphans.append(rel)

    return orphans


def find_stale_todos(vault_root: Path, days: int = 14) -> list[dict]:
    """
    Find unchecked task items in files not modified for N days.
    Returns list of {file, todos, last_modified, days_stale}.
    """
    cutoff = datetime.now().timestamp() - (days * 86400)
    stale = []

    for f in iter_md_files(vault_root):
        mtime = f.stat().st_mtime
        if mtime >= cutoff:
            continue

        content = f.read_text(encoding="utf-8", errors="replace")
        todos = re.findall(r"- \[ \] (.+)", content)
        if not todos:
            continue

        days_stale = (datetime.now().timestamp() - mtime) / 86400
        stale.append(
            {
                "file": str(f.relative_to(vault_root)),
                "todos": todos,
                "last_modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"),
                "days_stale": int(days_stale),
            }
        )

    stale.sort(key=lambda x: x["days_stale"], reverse=True)
    return stale


def find_broken_links(vault_root: Path) -> list[dict]:
    """
    Find [[wikilinks]] that point to non-existent files.
    Returns list of {source, target, line_number}.
    """
    # Build index of all file stems
    existing_stems = set()
    for f in iter_md_files(vault_root):
        existing_stems.add(f.stem)

    broken = []
    for f in iter_md_files(vault_root):
        content = f.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(content.splitlines(), 1):
            for match in re.finditer(r"\[\[([^\]|#]+)", line):
                target = match.group(1).strip()
                if target not in existing_stems:
                    broken.append(
                        {
                            "source": str(f.relative_to(vault_root)),
                            "target": target,
                            "line_number": i,
                        }
                    )

    return broken


def check_index_freshness(vault_root: Path) -> list[dict]:
    """
    Compare INDEX.md / VAULT-MAP.md against actual directory contents.
    Returns list of {index_file, missing_from_index, extra_in_index}.
    """
    results = []

    for index_name in ["INDEX.md", "VAULT-MAP.md"]:
        index_file = vault_root / index_name
        if not index_file.exists():
            continue

        content = index_file.read_text(encoding="utf-8", errors="replace")
        index_mtime = datetime.fromtimestamp(index_file.stat().st_mtime)

        # Find files mentioned in the index
        mentioned = set(re.findall(r"[|\s]([^\s|]+\.md)", content))

        # Find files that have been modified more recently than the index
        newer_files = []
        for f in iter_md_files(vault_root):
            if f.name == index_name:
                continue
            if f.stat().st_mtime > index_file.stat().st_mtime:
                newer_files.append(str(f.relative_to(vault_root)))

        results.append(
            {
                "index_file": index_name,
                "index_date": index_mtime.strftime("%Y-%m-%d"),
                "files_newer_than_index": len(newer_files),
                "newest_changes": newer_files[:10],
            }
        )

    return results


def check_unverified_captures(vault_root: Path) -> dict:
    """
    Count Perplexity captures and their verification status.
    """
    capture_dirs = [
        vault_root / "01-Literature" / "Perplexity-Captures",
        vault_root / "03 - Research",
    ]

    total = 0
    unprocessed = 0
    unverified_sources = 0
    files_with_issues = []

    for capture_dir in capture_dirs:
        if not capture_dir.exists():
            continue
        for f in capture_dir.rglob("*.md"):
            content = f.read_text(encoding="utf-8", errors="replace")
            if "perplexity-research" not in content and "perplexity" not in f.name.lower():
                continue

            total += 1
            squares = content.count("⬜")

            if "to-process" in content:
                unprocessed += 1
            if squares > 0:
                unverified_sources += squares
                files_with_issues.append(
                    {
                        "file": str(f.relative_to(vault_root)),
                        "unverified_count": squares,
                        "still_to_process": "to-process" in content,
                    }
                )

    return {
        "total_captures": total,
        "unprocessed": unprocessed,
        "unverified_sources": unverified_sources,
        "files": files_with_issues,
    }


def run_health_check(vault_root: Path, days: int = 14) -> dict:
    """Run all health checks and return structured results."""
    total_files = sum(1 for _ in iter_md_files(vault_root))
    orphans = find_orphans(vault_root)
    stale = find_stale_todos(vault_root, days)
    broken = find_broken_links(vault_root)
    index_status = check_index_freshness(vault_root)
    captures = check_unverified_captures(vault_root)

    total_stale_todos = sum(len(s["todos"]) for s in stale)

    return {
        "vault_root": str(vault_root),
        "check_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": {
            "total_files": total_files,
            "orphan_count": len(orphans),
            "orphan_pct": round(len(orphans) / max(total_files, 1) * 100, 1),
            "stale_todo_files": len(stale),
            "stale_todo_count": total_stale_todos,
            "broken_links": len(broken),
            "index_files_checked": len(index_status),
            "perplexity_total": captures["total_captures"],
            "perplexity_unprocessed": captures["unprocessed"],
            "perplexity_unverified_sources": captures["unverified_sources"],
        },
        "orphans": orphans,
        "stale_todos": stale,
        "broken_links": broken,
        "index_freshness": index_status,
        "perplexity_captures": captures,
    }


def print_human_readable(report: dict):
    """Print a human-readable health report."""
    s = report["summary"]
    print(f"\n{'=' * 60}")
    print(f"Vault Health Report — {report['check_date']}")
    print(f"{'=' * 60}")
    print(f"Vault: {report['vault_root']}")
    print(f"Total files: {s['total_files']}")
    print()

    # Immediate attention
    immediate = []
    if s["broken_links"] > 0:
        immediate.append(f"  {s['broken_links']} broken wikilinks")
    if s["stale_todo_count"] > 0:
        immediate.append(f"  {s['stale_todo_count']} stale TODOs across " f"{s['stale_todo_files']} files")

    if immediate:
        print("🔴 IMMEDIATE ATTENTION")
        for item in immediate:
            print(item)
        print()

    # Maintenance
    maintenance = []
    if s["orphan_count"] > 0:
        maintenance.append(f"  {s['orphan_count']} orphan notes ({s['orphan_pct']}%)")
    if s["perplexity_unprocessed"] > 0:
        maintenance.append(
            f"  {s['perplexity_unprocessed']}/{s['perplexity_total']} "
            f"Perplexity captures unprocessed "
            f"({s['perplexity_unverified_sources']} unverified sources)"
        )
    for idx in report["index_freshness"]:
        if idx["files_newer_than_index"] > 0:
            maintenance.append(f"  {idx['index_file']}: {idx['files_newer_than_index']} " f"files newer than index")

    if maintenance:
        print("🟡 MAINTENANCE")
        for item in maintenance:
            print(item)
        print()

    # Details
    if report["broken_links"]:
        print("Broken links:")
        for bl in report["broken_links"][:10]:
            print(f"  {bl['source']}:{bl['line_number']} → [[{bl['target']}]]")
        if len(report["broken_links"]) > 10:
            print(f"  ... and {len(report['broken_links']) - 10} more")
        print()

    if report["stale_todos"]:
        print("Stale TODOs (oldest first):")
        for st in report["stale_todos"][:5]:
            print(f"  {st['file']} ({st['days_stale']} days stale)")
            for todo in st["todos"][:3]:
                print(f"    - [ ] {todo}")
            if len(st["todos"]) > 3:
                print(f"    ... and {len(st['todos']) - 3} more")
        print()

    if report["orphans"]:
        print(f"Orphan notes ({len(report['orphans'])} total):")
        for orph in report["orphans"][:10]:
            print(f"  {orph}")
        if len(report["orphans"]) > 10:
            print(f"  ... and {len(report['orphans']) - 10} more")


def main():
    parser = argparse.ArgumentParser(description="Run vault health check")
    parser.add_argument("vault_root", type=Path, help="Path to the vault root")
    parser.add_argument("--days", type=int, default=14, help="Days threshold for stale TODOs (default: 14)")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of human-readable text")
    parser.add_argument("--output", type=Path, default=None, help="Write output to file instead of stdout")
    args = parser.parse_args()

    vault_root = args.vault_root.resolve()
    if not vault_root.exists():
        print(f"Error: vault root does not exist: {vault_root}")
        return 1

    report = run_health_check(vault_root, args.days)

    if args.json:
        output = json.dumps(report, indent=2, default=str)
        if args.output:
            args.output.write_text(output, encoding="utf-8")
            print(f"Report written to {args.output}")
        else:
            print(output)
    else:
        if args.output:
            # Write human-readable to file
            import io
            import contextlib

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                print_human_readable(report)
            args.output.write_text(buf.getvalue(), encoding="utf-8")
            print(f"Report written to {args.output}")
        else:
            print_human_readable(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
