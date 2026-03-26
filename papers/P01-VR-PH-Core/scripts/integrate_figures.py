"""
Replace \\placeholder{Figure N...} calls in body.tex with proper LaTeX
figure environments, and update \\placeholder{Table N...} with proper
table-placeholder stubs until tables are finalised.

Reads figures/manifest.json to get filenames and captions.

Usage (from papers/P01-VR-PH-Core/latex/):
    uv run python ../scripts/integrate_figures.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

LATEX_DIR = Path(__file__).parent.parent / "latex"
FIGURES_DIR = Path(__file__).parent.parent / "figures"
BODY_TEX = LATEX_DIR / "body.tex"
MANIFEST = FIGURES_DIR / "manifest.json"

# ── Figure environment template ───────────────────────────────────────────────
FIG_TEMPLATE = r"""\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=\textwidth]{{figures/{stem}}}
  \caption{{{caption}}}
  \label{{fig:{n}}}
\end{{figure}}"""

# ── Mapping: figure number → manifest key (both are the fig number as str) ───
# Also handle the variant placeholder formats from md2latex:
#   \placeholder{Figure 1]** text...}   (has ]** suffix from markdown bold)
#   \placeholder{Figure 1: text...}     (clean colon style)
#   \placeholder{Figure 14]** text...}  (multi-figure placeholder)

PLACEHOLDER_PATTERN = re.compile(
    r"\\placeholder\{Figure\s+(\d+)[:\]].+?\}",
    re.DOTALL,
)


def build_replacement(fig_num: str, manifest: dict) -> str:
    entry = manifest.get(fig_num)
    if entry is None:
        return rf"\placeholder{{Figure {fig_num}: [FIGURE NOT IN MANIFEST]}}"
    return FIG_TEMPLATE.format(
        stem=entry["stem"],
        caption=entry["caption"],
        n=fig_num,
    )


def integrate(body_path: Path, manifest_path: Path) -> None:
    with open(manifest_path) as f:
        manifest = json.load(f)

    text = body_path.read_text(encoding="utf-8")
    orig_len = len(text.splitlines())

    def replacer(m: re.Match) -> str:
        fig_num = m.group(1)
        return build_replacement(fig_num, manifest)

    new_text = PLACEHOLDER_PATTERN.sub(replacer, text)
    new_len = len(new_text.splitlines())

    body_path.write_text(new_text, encoding="utf-8")
    print(f"integrate_figures: {orig_len} -> {new_len} lines")
    print(f"  replaced placeholders for figures: {sorted(manifest.keys(), key=int)}")

    # Report any remaining figure placeholders
    remaining = re.findall(r"\\placeholder\{Figure\s+\d+", new_text)
    if remaining:
        print(f"  WARNING: {len(remaining)} figure placeholder(s) still remain:")
        for r in remaining:
            print(f"    {r}")
    else:
        print("  All figure placeholders replaced.")


if __name__ == "__main__":
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST}\n" "Run generate_figures.py first.")
    integrate(BODY_TEX, MANIFEST)
