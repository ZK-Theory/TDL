# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Check actual hhresp column headers for income variables
import os
from pathlib import Path
from typing import List, Sequence

DATA_ROOT = os.getenv("DATA_ROOT", "")
if not DATA_ROOT:
    DATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "UKDA-6614-tab" / "tab"
else:
    DATA_ROOT = Path(DATA_ROOT)

def get_matching_cols(fname: Path, keywords: Sequence[str]) -> List[str]:
    """Return header columns matching any keyword in the given file.

    Args:
        fname: Path to a tab-delimited file.
        keywords: Sequence of keyword substrings to search for.

    Returns:
        List of matching header strings.
    """
    with open(fname, "r", encoding="latin-1") as f:
        header = f.readline().strip().split("\t")
    header = [h.strip() for h in header]
    return [h for h in header if any(k.lower() in h.lower() for k in keywords)]

keywords = ["fihhm", "fihhn", "net3", "hhnet", "fihhynl", "equi"]

# UKHLS waves a and k
for wave in ["a", "k"]:
    fname = DATA_ROOT / "ukhls" / f"{wave}_hhresp.tab"
    try:
        cols = get_matching_cols(fname, keywords)
        print(f"UKHLS {wave} hhresp income cols: {cols}")
    except FileNotFoundError:
        print(f"UKHLS {wave} hhresp: not found")

# BHPS waves br (last BHPS) and bq
for wave in ["bq", "br"]:
    fname = DATA_ROOT / "bhps" / f"{wave}_hhresp.tab"
    try:
        cols = get_matching_cols(fname, keywords)
        print(f"BHPS {wave} hhresp income cols: {cols}")
    except FileNotFoundError:
        print(f"BHPS {wave} hhresp: not found")

# Also check for fihhmn specifically in BHPS indresp
fname = DATA_ROOT / "bhps" / "br_hhresp.tab"
try:
    with open(fname, "r", encoding="latin-1") as f:
        header = f.readline().strip().split("\t")
    header = [h.strip() for h in header]
    fihhmn_cols = [h for h in header if "fihhmn" in h.lower()]
    print(f"\nBHPS br hhresp fihhmn* cols: {fihhmn_cols}")
except Exception as e:
    print(f"Error: {e}")

# Check UKHLS wave a for net3
fname = DATA_ROOT / "ukhls" / "a_hhresp.tab"
try:
    with open(fname, "r", encoding="latin-1") as f:
        header = f.readline().strip().split("\t")
    header = [h.strip() for h in header]
    net_cols = [h for h in header if "net" in h.lower() and "fihhm" in h.lower()]
    print(f"\nUKHLS a hhresp fihhm*net* cols: {net_cols}")
except Exception as e:
    print(f"Error: {e}")
