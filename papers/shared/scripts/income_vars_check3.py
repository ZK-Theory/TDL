# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Find fihhmn and fihhmnnet3 in BHPS/UKHLS data files
import os
from pathlib import Path
from typing import List

DATA_ROOT = os.getenv("DATA_ROOT", "")
if not DATA_ROOT:
    DATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "UKDA-6614-tab" / "tab"
else:
    DATA_ROOT = Path(DATA_ROOT)

def get_header(fname: Path) -> List[str]:
    """Read the first line of a tab-delimited file and return stripped headers."""
    with open(fname, "r", encoding="latin-1") as f:
        return [h.strip() for h in f.readline().strip().split("\t")]

# Check UKHLS indresp waves for fihhmnnet3_dv
print("=== UKHLS indresp: looking for net3 and fihhmn vars ===")
for wave in ["a", "b", "j", "k", "o"]:
    fname = DATA_ROOT / "ukhls" / f"{wave}_indresp.tab"
    try:
        header = get_header(fname)
        hits = [
            h for h in header
            if "net3" in h.lower() or (
                "fihhm" in h.lower() and "net" in h.lower()
            )
        ]
        if hits:
            print(f"  Wave {wave}: {hits}")
        else:
            print(f"  Wave {wave}: no net3/fihhmnnet vars")
    except FileNotFoundError:
        print(f"  Wave {wave}: not found")

# Check BHPS harmonised indresp for fihhmn
print("\n=== BHPS harmonised indresp: fihhmn vars ===")
for wave in ["ba", "br"]:
    fname = DATA_ROOT / "bhps" / f"{wave}_indresp.tab"
    try:
        header = get_header(fname)
        hits = [
            h for h in header
            if "fihhmn" in h.lower() or (
                "fihh" in h.lower() and "mn" in h.lower()
            )
        ]
        if hits:
            print(f"  Wave {wave}: {hits}")
        else:
            print(f"  Wave {wave}: no fihhmn vars")
    except FileNotFoundError:
        print(f"  Wave {wave}: not found")

# Check BHPS hhresp for fihhmn (original variable)
print("\n=== BHPS hhresp: fihhmn vars across waves ===")
for wave in ["ba", "bm", "br"]:
    fname = DATA_ROOT / "bhps" / f"{wave}_hhresp.tab"
    try:
        header = get_header(fname)
        hits = [h for h in header if "fihhmn" in h.lower()]
        print(f"  Wave {wave}: {hits if hits else 'none'}")
        # Also check for just fihh
        fihh = [h for h in header if h.lower().startswith(f"{wave}_fihh")]
        print(f"    All fihh* in {wave}: {fihh[:10]}")
    except FileNotFoundError:
        print(f"  Wave {wave}: not found")
