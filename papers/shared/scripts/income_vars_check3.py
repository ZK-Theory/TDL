# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Find fihhmn and fihhmnnet3 in BHPS/UKHLS data files
import re

DATA_ROOT = r"C:\Users\steph\TDL\data\UKDA-6614-tab\tab"

def get_header(fname):
    with open(fname, "r", encoding="latin-1") as f:
        return [h.strip() for h in f.readline().strip().split("\t")]

# Check UKHLS indresp waves for fihhmnnet3_dv
print("=== UKHLS indresp: looking for net3 and fihhmn vars ===")
for wave in ["a", "b", "j", "k", "o"]:
    fname = f"{DATA_ROOT}/ukhls/{wave}_indresp.tab"
    try:
        header = get_header(fname)
        hits = [h for h in header if "net3" in h.lower() or ("fihhm" in h.lower() and "net" in h.lower())]
        if hits:
            print(f"  Wave {wave}: {hits}")
        else:
            print(f"  Wave {wave}: no net3/fihhmnnet vars")
    except FileNotFoundError:
        print(f"  Wave {wave}: not found")

# Check BHPS harmonised indresp for fihhmn
print("\n=== BHPS harmonised indresp: fihhmn vars ===")
for wave in ["ba", "br"]:
    fname = f"{DATA_ROOT}/bhps/{wave}_indresp.tab"
    try:
        header = get_header(fname)
        hits = [h for h in header if "fihhmn" in h.lower() or ("fihh" in h.lower() and "mn" in h.lower())]
        if hits:
            print(f"  Wave {wave}: {hits}")
        else:
            print(f"  Wave {wave}: no fihhmn vars")
    except FileNotFoundError:
        print(f"  Wave {wave}: not found")

# Check BHPS hhresp for fihhmn (original variable)
print("\n=== BHPS hhresp: fihhmn vars across waves ===")
for wave in ["ba", "bm", "br"]:
    fname = f"{DATA_ROOT}/bhps/{wave}_hhresp.tab"
    try:
        header = get_header(fname)
        hits = [h for h in header if "fihhmn" in h.lower()]
        print(f"  Wave {wave}: {hits if hits else 'none'}")
        # Also check for just fihh
        fihh = [h for h in header if h.lower().startswith(f"{wave}_fihh")]
        print(f"    All fihh* in {wave}: {fihh[:10]}")
    except FileNotFoundError:
        print(f"  Wave {wave}: not found")
