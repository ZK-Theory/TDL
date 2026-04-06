"""
vault_map.py — Hardened VAULT-MAP.md generator

Scans an Obsidian vault's directory structure and produces a navigable
markdown index. Replaces the LLM's ad-hoc directory scanning with a
deterministic script that runs identically every time.

Usage:
    python vault_map.py <vault_root> [--vault-type tda|cl] [--output VAULT-MAP.md]

The script detects vault type from directory structure if not specified.
Output defaults to VAULT-MAP.md in the vault root.
"""

import argparse
import re
from pathlib import Path
from datetime import datetime


def detect_vault_type(vault_root: Path) -> str:
    """Detect whether this is the TDA-Research or Counting Lives vault."""
    if (vault_root / "03-Papers").exists():
        return "tda"
    if (vault_root / "01 - Manuscript").exists():
        return "cl"
    raise ValueError(f"Cannot detect vault type at {vault_root}. " "Use --vault-type to specify.")


def scan_tda_papers(vault_root: Path) -> list[dict]:
    """Read all _project.md files and extract structured status."""
    papers_dir = vault_root / "03-Papers"
    if not papers_dir.exists():
        return []

    papers = []
    for project_file in sorted(papers_dir.rglob("_project.md")):
        content = project_file.read_text(encoding="utf-8")
        paper_id = project_file.parent.name

        # Extract status from frontmatter or content
        status_match = re.search(r"status:\s*(\S+)", content)
        status = status_match.group(1) if status_match else "unknown"

        stage_match = re.search(r"stage:\s*(\d+)", content)
        stage = stage_match.group(1) if stage_match else "—"

        deadline_match = re.search(r"deadline:\s*(\S+)", content)
        deadline = deadline_match.group(1) if deadline_match else "—"

        # Count open items
        open_items = len(re.findall(r"- \[ \]", content))

        # Extract title from first heading or frontmatter
        title_match = re.search(r'title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
        if not title_match:
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else paper_id

        papers.append(
            {
                "id": paper_id,
                "title": title,
                "stage": stage,
                "status": status,
                "deadline": deadline,
                "open_items": open_items,
                "last_modified": datetime.fromtimestamp(project_file.stat().st_mtime),
            }
        )

    return papers


def scan_cl_chapters(vault_root: Path) -> list[dict]:
    """Read chapter files and extract status information."""
    manuscript_dir = vault_root / "01 - Manuscript"
    if not manuscript_dir.exists():
        return []

    chapters = []
    for ch_folder in sorted(manuscript_dir.rglob("Ch*")):
        if not ch_folder.is_dir():
            continue

        # Count sections
        sections_dir = ch_folder / "sections"
        sections_count = len(list(sections_dir.glob("*.md"))) if sections_dir.exists() else 0

        # Find the main chapter file
        ch_files = list(ch_folder.glob("Ch*.md"))
        if not ch_files:
            continue

        ch_file = ch_files[0]
        content = ch_file.read_text(encoding="utf-8")

        # Count TODOs
        todos = len(re.findall(r"- \[ \]", content))

        # Extract title from filename
        title_match = re.match(r"Ch\d+\s*[-–—]\s*(.+)\.md$", ch_file.name)
        title = title_match.group(1).strip() if title_match else ch_folder.name

        # Determine chapter number
        ch_num_match = re.search(r"Ch(\d+)", ch_folder.name)
        ch_num = ch_num_match.group(1) if ch_num_match else "??"

        chapters.append(
            {
                "number": ch_num,
                "title": title,
                "sections_drafted": sections_count,
                "research_gaps": todos,
                "last_modified": datetime.fromtimestamp(ch_file.stat().st_mtime),
                "folder": ch_folder,
            }
        )

    return chapters


def count_md_files(directory: Path) -> int:
    """Count .md files in a directory (non-recursive)."""
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.md")))


def count_unprocessed_captures(vault_root: Path, vault_type: str) -> tuple[int, int]:
    """Count total and unprocessed Perplexity captures."""
    if vault_type == "tda":
        captures_dir = vault_root / "01-Literature" / "Perplexity-Captures"
    else:
        captures_dir = vault_root / "03 - Research"

    if not captures_dir.exists():
        return 0, 0

    total = 0
    unprocessed = 0
    for f in captures_dir.rglob("*.md"):
        content = f.read_text(encoding="utf-8")
        if "perplexity-research" in content or "perplexity" in f.name.lower():
            total += 1
            if "to-process" in content or "⬜" in content:
                unprocessed += 1

    return total, unprocessed


def find_recent_activity(vault_root: Path, days: int = 7) -> list[dict]:
    """Find most recently modified .md files."""
    cutoff = datetime.now().timestamp() - (days * 86400)
    recent = []

    for f in vault_root.rglob("*.md"):
        mtime = f.stat().st_mtime
        if mtime > cutoff:
            recent.append(
                {
                    "file": str(f.relative_to(vault_root)),
                    "modified": datetime.fromtimestamp(mtime),
                }
            )

    recent.sort(key=lambda x: x["modified"], reverse=True)
    return recent[:10]


def find_health_check_date(vault_root: Path) -> str:
    """Find the most recent health check date from daily notes."""
    daily_dirs = [
        vault_root / "05-Daily",
        vault_root / "05 - AI Sessions",
    ]

    for daily_dir in daily_dirs:
        if not daily_dir.exists():
            continue
        for f in sorted(daily_dir.glob("*.md"), reverse=True):
            content = f.read_text(encoding="utf-8")
            if "health check" in content.lower():
                match = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
                if match:
                    return match.group(1)

    return "unknown"


def generate_tda_map(vault_root: Path) -> str:
    """Generate VAULT-MAP.md content for TDA-Research vault."""
    papers = scan_tda_papers(vault_root)
    captures_total, captures_unprocessed = count_unprocessed_captures(vault_root, "tda")
    recent = find_recent_activity(vault_root)
    health_date = find_health_check_date(vault_root)
    now = datetime.now().strftime("%Y-%m-%d")

    lines = [
        "# Vault Map — TDA-Research\n",
        "> **Auto-generated by vault_map.py. Do not edit manually.**",
        f"> Last updated: {now}",
        f"> Last health check: {health_date}\n",
        "---\n",
        "## Paper Pipeline\n",
        "| ID | Title | Stage | Status | Deadline | Open Items |",
        "|---|---|---|---|---|---|",
    ]

    for p in papers:
        lines.append(
            f"| {p['id']} | {p['title']} | {p['stage']} | " f"{p['status']} | {p['deadline']} | {p['open_items']} |"
        )

    # Methods section
    methods_dir = vault_root / "04-Methods"
    lines.extend(
        [
            "\n## Methods & Infrastructure\n",
            "| Note | Location | Last modified |",
            "|---|---|---|",
        ]
    )
    if methods_dir.exists():
        for f in sorted(methods_dir.glob("*.md")):
            mdate = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
            lines.append(f"| {f.name} | 04-Methods/ | {mdate} |")

    # Literature section
    lit_dir = vault_root / "01-Literature"
    lit_count = count_md_files(lit_dir) if lit_dir.exists() else 0
    perm_dir = vault_root / "02-Notes" / "Permanent"
    perm_count = count_md_files(perm_dir) if perm_dir.exists() else 0

    lines.extend(
        [
            "\n## Literature\n",
            "| Category | Count | Unprocessed |",
            "|---|---|---|",
            f"| Literature notes | {lit_count} | — |",
            f"| Perplexity captures | {captures_total} | {captures_unprocessed} |",
            f"| Permanent notes | {perm_count} | — |",
        ]
    )

    # Recent activity
    lines.extend(["\n## Recent Activity (last 7 days)\n"])
    if recent:
        lines.extend(
            [
                "| File | Modified |",
                "|---|---|",
            ]
        )
        for r in recent:
            lines.append(f"| {r['file']} | {r['modified'].strftime('%Y-%m-%d')} |")
    else:
        lines.append("No files modified in the last 7 days.")

    lines.extend(
        [
            "\n---\n",
            f"*Regenerated by vault_map.py on {now}.*",
        ]
    )

    return "\n".join(lines)


def generate_cl_map(vault_root: Path) -> str:
    """Generate VAULT-MAP.md content for Counting Lives vault."""
    chapters = scan_cl_chapters(vault_root)
    captures_total, captures_unprocessed = count_unprocessed_captures(vault_root, "cl")
    recent = find_recent_activity(vault_root)
    health_date = find_health_check_date(vault_root)
    now = datetime.now().strftime("%Y-%m-%d")

    # Group chapters by part
    parts = {
        "I": ("The State Learns to Count", []),
        "II": ("The Ideology of Optimisation", []),
        "III": ("The Automated Poorhouse", []),
        "IV": ("Counter-Mathematics", []),
    }

    for ch in chapters:
        num = int(ch["number"])
        if num <= 4:
            parts["I"][1].append(ch)
        elif num <= 9:
            parts["II"][1].append(ch)
        elif num <= 13:
            parts["III"][1].append(ch)
        else:
            parts["IV"][1].append(ch)

    lines = [
        "# Vault Map — Counting Lives\n",
        "> **Auto-generated by vault_map.py. Do not edit manually.**",
        f"> Last updated: {now}",
        f"> Last health check: {health_date}\n",
        "---\n",
        "## Book Structure\n",
    ]

    for part_num, (part_title, part_chapters) in parts.items():
        lines.extend(
            [
                f"### Part {part_num} — {part_title}",
                "| Ch | Title | Sections | Gaps | Last modified |",
                "|---|---|---|---|---|",
            ]
        )
        for ch in part_chapters:
            mdate = ch["last_modified"].strftime("%Y-%m-%d")
            lines.append(
                f"| {ch['number']} | {ch['title']} | " f"{ch['sections_drafted']} | {ch['research_gaps']} | {mdate} |"
            )
        lines.append("")

    # Sources
    sources_dir = vault_root / "02 - Sources" / "literature-notes"
    lit_count = count_md_files(sources_dir) if sources_dir.exists() else 0
    research_dir = vault_root / "03 - Research"
    research_count = count_md_files(research_dir) if research_dir.exists() else 0
    sessions_dir = vault_root / "05 - AI Sessions"
    sessions_count = count_md_files(sessions_dir) if sessions_dir.exists() else 0

    lines.extend(
        [
            "## Sources & Literature\n",
            "| Category | Count |",
            "|---|---|",
            f"| Literature notes | {lit_count} |",
            f"| Research notes | {research_count} |",
            f"| Perplexity captures | {captures_total} ({captures_unprocessed} unprocessed) |",
            f"| AI session logs | {sessions_count} |",
        ]
    )

    # Recent activity
    lines.extend(["\n## Recent Activity (last 7 days)\n"])
    if recent:
        lines.extend(
            [
                "| File | Modified |",
                "|---|---|",
            ]
        )
        for r in recent:
            lines.append(f"| {r['file']} | {r['modified'].strftime('%Y-%m-%d')} |")
    else:
        lines.append("No files modified in the last 7 days.")

    lines.extend(
        [
            "\n---\n",
            f"*Regenerated by vault_map.py on {now}.*",
        ]
    )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate VAULT-MAP.md for an Obsidian vault")
    parser.add_argument("vault_root", type=Path, help="Path to the vault root")
    parser.add_argument("--vault-type", choices=["tda", "cl"], help="Vault type (auto-detected if not specified)")
    parser.add_argument(
        "--output", type=Path, default=None, help="Output file path (default: VAULT-MAP.md in vault root)"
    )
    args = parser.parse_args()

    vault_root = args.vault_root.resolve()
    if not vault_root.exists():
        print(f"Error: vault root does not exist: {vault_root}")
        return 1

    vault_type = args.vault_type or detect_vault_type(vault_root)
    output_path = args.output or (vault_root / "VAULT-MAP.md")

    if vault_type == "tda":
        content = generate_tda_map(vault_root)
    else:
        content = generate_cl_map(vault_root)

    output_path.write_text(content, encoding="utf-8")
    print(f"Generated {output_path} ({vault_type} vault)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
