"""Post-process body.tex: remove duplicate References section and convert
inline author-year citations to LaTeX \\citep{}/\\citet{} commands."""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Mapping: (partial author string to match, year) → BibTeX key
# The author string should match how it appears in the markdown/body.tex,
# using \\& since the converter already escaped & → \\&.
# ---------------------------------------------------------------------------
CITE_MAP: list[tuple[str, str, str]] = [
    # author text          year   bibtex key
    ("Abbott", "1995", "abbott1995sequence"),
    ("Abbott", "2000", "abbott2000sequence"),
    ("Atienza", "2019", "atienza2019persistent"),
    ("Azariadis", "2005", "azariadis2005poverty"),
    ("Barrett", "2013", "barrett2013economics"),
    ("Bauer", "2021", "bauer2021ripser"),
    ("Blanden", "2004", "blanden2004changes"),
    ("Blanden", "2013", "blanden2013intergenerational"),
    ("Bobrowski", "2018", "bobrowski2018topology"),
    ("Bukodi", "2019", "bukodi2019social"),
    ("Carlsson", "2009", "carlsson2009topology"),
    ("Cohen-Steiner", "2007", "cohen2007stability"),
    ("Steiner", "2007", "cohen2007stability"),  # abbreviated form
    ("Coulter", "2016", "coulter2016rethinking"),
    ("de Silva", "2004", "desilva2004topological"),
    ("Silva", "2004", "desilva2004topological"),
    ("DiPrete", "2006", "diprete2006cumulative"),
    ("Eirich", "2006", "diprete2006cumulative"),
    ("Edelsbrunner", "2002", "edelsbrunner2002topological"),
    ("Edelsbrunner", "2010", "edelsbrunner2010computational"),
    ("Elzinga", "2007", "elzinga2007destandardization"),
    ("Gauthier", "2010", "gauthier2010multichannel"),
    ("Gidea", "2018", "gidea2018topological"),
    ("Goldthorpe", "2016", "goldthorpe2016social"),
    ("Goldthorpe", "2008", "goldthorpe2008trends"),
    ("Halpin", "1998", "halpin1998class"),
    ("Hiraoka", "2016", "hiraoka2016hierarchical"),
    ("Government", "2022", "hmgov2022levelling"),
    ("HM Government", "2022", "hmgov2022levelling"),
    ("Iacopini", "2019", "iacopini2019simplicial"),
    ("Jenkins", "2011", "jenkins2011changing"),
    ("Lesnard", "2010", "lesnard2010setting"),
    ("McInnes", "2018", "mcinnes2018umap"),
    ("Rizvi", "2017", "rizvi2017single"),
    ("Robette", "2008", "robette2008comparing"),
    ("Robinson", "2017", "robinson2017hypothesis"),
    ("Saggar", "2018", "saggar2018towards"),
    ("Savage", "2013", "savage2013new"),
    ("Singer", "1976", "singer1976representation"),
    ("Sizemore", "2018", "sizemore2018importance"),
    ("Stolz", "2017", "stolz2017persistent"),
    ("Studer", "2016", "studer2016what"),
    ("Tong", "1990", "tong1990nonlinear"),
    ("Turner", "2014", "turner2014frechet"),
    ("Vandecasteele", "2010", "vandecasteele2010poverty"),
    ("Zomorodian", "2005", "zomorodian2005computing"),
]

# Build lookup: (first_author_word, year) → key
# Allow any suffix on author (e.g. "Blanden et al.", "Blanden, J.")
LOOKUP: dict[tuple[str, str], str] = {}
for auth, yr, key in CITE_MAP:
    # use the last word of the author string as the primary match key
    first_word = auth.split()[-1]
    LOOKUP[(first_word, yr)] = key


def resolve_token(token: str) -> str | None:
    """Resolve 'Author Year' or 'Author et al. Year' to a bibtex key."""
    # Extract year from end of token
    m = re.search(r"(\d{4})", token)
    if not m:
        return None
    year = m.group(1)
    # Extract author — everything before the year
    author_part = token[: m.start()].strip().rstrip(",").strip()
    # Try each defined author pattern
    for auth, yr, key in CITE_MAP:
        if yr == year and auth.lower() in author_part.lower():
            return key
    # Fallback: try first word of author part
    words = author_part.split()
    if words:
        k = LOOKUP.get((words[0], year))
        if k:
            return k
    return None


def convert_parenthetical(match: re.Match) -> str:
    """Replace (Author Year; Author Year) with \\citep{key1,key2}."""
    inner = match.group(1).strip()
    # Split on semicolons or commas between citations
    # Handle "Author 2004, 2013" (same author, two years)
    parts: list[str] = []

    # Try splitting on semicolons first
    segments = re.split(r";", inner)
    for seg in segments:
        seg = seg.strip()
        # Check for "Author YEAR, YEAR" pattern (same author, multiple years)
        multi_year = re.match(r"(.+?)\s+(\d{4})\s*,\s*(\d{4})", seg)
        if multi_year:
            auth_base = multi_year.group(1).strip()
            parts.append(f"{auth_base} {multi_year.group(2)}")
            parts.append(f"{auth_base} {multi_year.group(3)}")
        else:
            parts.append(seg)

    keys: list[str] = []
    for part in parts:
        k = resolve_token(part)
        if k:
            keys.append(k)

    if keys:
        return r"\citep{" + ", ".join(keys) + "}"
    # Cannot resolve — return unchanged
    return match.group(0)


def convert_author_paren_year(match: re.Match) -> str:
    """Replace Author (Year) with \\citet{key}."""
    author_part = match.group(1).strip()
    year = match.group(2)
    token = f"{author_part} {year}"
    k = resolve_token(token)
    if k:
        return rf"\citet{{{k}}}"
    return match.group(0)


def convert_author_possessive(match: re.Match) -> str:
    """Replace Author's (Year) with \\citeauthor{key}'s (\\citeyear{key})."""
    author_part = match.group(1).strip()
    year = match.group(2)
    token = f"{author_part} {year}"
    k = resolve_token(token)
    if k:
        return rf"\citeauthor{{{k}}}'s (\citeyear{{{k}}})"
    return match.group(0)


def process(text: str) -> str:
    """Apply all citation conversions."""

    # 1. Author's (Year) possessive — e.g. Abbott's (1995)
    text = re.sub(
        r"([A-Z][a-z]+(?:\s+et\s+al\.?)?)'s\s+\((\d{4})\)",
        convert_author_possessive,
        text,
    )

    # 2. Author (Year) in-text — e.g. Robinson & Turner (2017)
    text = re.sub(
        r"([A-Z][a-z]+(?:[-][A-Z][a-z]+)?(?:\s+(?:et\s+al\.?|[&\\]+[&]?)\s+[A-Z][a-z]+)*)" r"\s+\((\d{4})\)",
        convert_author_paren_year,
        text,
    )

    # 3. (Author Year; Author Year) parenthetical
    text = re.sub(
        r"\(([A-Z][a-z][^()]*\d{4}[^()]*)\)",
        convert_parenthetical,
        text,
    )

    return text


def remove_references_section(lines: list[str]) -> list[str]:
    """Strip the hand-formatted References section — BibTeX handles it."""
    for i, line in enumerate(lines):
        if r"\section{References}" in line:
            return lines[:i]
    return lines


def main() -> None:
    latex_dir = Path(__file__).parent.parent / "latex"
    body_path = latex_dir / "body.tex"

    print(f"Reading {body_path}")
    lines = body_path.read_text(encoding="utf-8").splitlines(keepends=True)

    # Remove duplicate References section
    lines = remove_references_section(lines)
    print(f"  Removed References section — {len(lines)} lines remain")

    text = "".join(lines)
    converted = process(text)

    body_path.write_text(converted, encoding="utf-8")
    print(f"Written {body_path}")

    # Report how many \cite commands now present
    cites = re.findall(r"\\cite[tp]?\{", converted)
    print(f"  \\cite* commands inserted: {len(cites)}")


if __name__ == "__main__":
    main()
