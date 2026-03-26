r"""Convert P01 markdown draft to LaTeX body sections.

Reads the markdown draft (v6-2026-03.md) and outputs LaTeX section files
that can be \input{} into main.tex, or prints the full converted body
for manual pasting.

Usage:
    python md2latex.py                     # prints to stdout
    python md2latex.py --output body.tex   # writes to file
    python md2latex.py --split             # writes per-section files
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in running text."""
    # Don't escape inside math mode or existing LaTeX commands
    # This is a simplified escaper for common cases
    replacements = [
        ("&", r"\&"),
        ("%", r"\%"),
        ("#", r"\#"),
        ("_", r"\_"),
    ]
    # Protect math mode and commands first
    protected: list[tuple[str, str]] = []
    counter = 0

    # Protect $...$ math
    def protect_math(m: re.Match) -> str:
        nonlocal counter
        key = f"<<PROTECTED{counter}>>"
        protected.append((key, m.group(0)))
        counter += 1
        return key

    text = re.sub(r"\$[^$]+\$", protect_math, text)
    text = re.sub(r"\\\w+\{[^}]*\}", protect_math, text)

    for old, new in replacements:
        text = text.replace(old, new)

    # Restore protected
    for key, original in protected:
        text = text.replace(key, original)

    return text


def convert_inline_formatting(text: str) -> str:
    """Convert markdown inline formatting to LaTeX."""
    # Bold: **text** -> \textbf{text}
    text = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", text)
    # Italic: *text* -> \textit{text}
    text = re.sub(r"\*([^*]+)\*", r"\\textit{\1}", text)
    # Inline code: `text` -> \texttt{text}
    text = re.sub(r"`([^`]+)`", r"\\texttt{\1}", text)
    return text


def convert_markdown_table(lines: list[str]) -> str:
    """Convert a markdown table to LaTeX booktabs table."""
    # Parse header
    header = lines[0].strip().strip("|").split("|")
    header = [h.strip() for h in header]
    ncols = len(header)

    # Skip separator line (lines[1])
    rows = []
    for line in lines[2:]:
        cells = line.strip().strip("|").split("|")
        cells = [c.strip() for c in cells]
        rows.append(cells)

    # Build LaTeX
    col_spec = "l" * ncols
    out = []
    out.append(f"\\begin{{tabular}}{{{col_spec}}}")
    out.append("\\toprule")
    out.append(" & ".join(header) + " \\\\")
    out.append("\\midrule")
    for row in rows:
        # Pad if needed
        while len(row) < ncols:
            row.append("")
        out.append(" & ".join(row) + " \\\\")
    out.append("\\bottomrule")
    out.append("\\end{tabular}")

    return "\n".join(out)


def convert_section(md_text: str) -> str:
    """Convert a block of markdown to LaTeX."""
    lines = md_text.split("\n")
    output: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Headings
        if line.startswith("### "):
            title = line[4:].strip()
            output.append(f"\\subsection{{{title}}}")
        elif line.startswith("## "):
            title = line[3:].strip()
            output.append(f"\\section{{{title}}}")
        elif line.startswith("# "):
            title = line[2:].strip()
            output.append(f"\\section{{{title}}}")

        # Tables (detect |---|)
        elif line.strip().startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]:
            table_lines = [line]
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("|"):
                table_lines.append(lines[j])
                j += 1
            output.append(convert_markdown_table(table_lines))
            i = j
            continue

        # Figure/table placeholders
        elif line.strip().startswith("**[Figure") or line.strip().startswith("**[Table"):
            placeholder = line.strip().strip("*").strip("[]")
            output.append(f"\\placeholder{{{placeholder}}}")

        # Horizontal rules
        elif line.strip() == "---":
            pass  # skip, sections handle breaks

        # Empty lines
        elif line.strip() == "":
            output.append("")

        # Regular text
        else:
            converted = convert_inline_formatting(line)
            output.append(converted)

        i += 1

    return "\n".join(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert P01 markdown to LaTeX")
    parser.add_argument(
        "--draft",
        type=str,
        default=None,
        help="Path to markdown draft (default: auto-detect latest)",
    )
    parser.add_argument("--output", type=str, default=None, help="Output .tex file")
    parser.add_argument("--split", action="store_true", help="Write per-section files")
    args = parser.parse_args()

    # Find draft
    if args.draft:
        draft_path = Path(args.draft)
    else:
        drafts_dir = Path(__file__).parent.parent / "drafts"
        drafts = sorted(drafts_dir.glob("v*-*.md"), reverse=True)
        if not drafts:
            print("No drafts found")
            return
        draft_path = drafts[0]

    print(f"Converting: {draft_path}", flush=True)
    md_text = draft_path.read_text(encoding="utf-8")

    # Convert
    latex_body = convert_section(md_text)

    if args.output:
        Path(args.output).write_text(latex_body, encoding="utf-8")
        print(f"Written to {args.output}")
    elif args.split:
        # Split by \section and write per-file
        out_dir = Path(__file__).parent.parent / "latex" / "sections"
        out_dir.mkdir(exist_ok=True)
        sections = re.split(r"(\\section\{)", latex_body)
        sec_num = 0
        for i in range(1, len(sections), 2):
            sec_content = sections[i] + sections[i + 1] if i + 1 < len(sections) else sections[i]
            # Extract section name for filename
            m = re.match(r"\\section\{(.+?)\}", sec_content)
            if m:
                name = m.group(1).lower().replace(" ", "-")[:30]
                fname = f"sec{sec_num:02d}-{name}.tex"
            else:
                fname = f"sec{sec_num:02d}.tex"
            (out_dir / fname).write_text(sec_content, encoding="utf-8")
            print(f"  Written: {fname}")
            sec_num += 1
    else:
        print(latex_body)


if __name__ == "__main__":
    main()
