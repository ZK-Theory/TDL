# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Find equivalised / net income vars across BHPS and UKHLS
import os
import re
from pathlib import Path
from typing import List

base_data_root = Path(__file__).resolve().parents[3]
DATA_ROOT: Path
DATA_ROOT_ENV = os.getenv("DATA_ROOT", "")
if not DATA_ROOT_ENV:
    DATA_ROOT = base_data_root / "data" / "UKDA-6614-tab" / "tab"
else:
    DATA_ROOT = Path(DATA_ROOT_ENV)

def get_header(fname: Path) -> List[str]:
    """Read the first line of a tab-delimited file and return stripped header fields."""
    with open(fname, "r", encoding="latin-1") as f:
        return [h.strip() for h in f.readline().strip().split("\t")]

# Look for equivalised income in UKHLS hhresp
print("=== UKHLS hhresp: equivalised + net income vars ===")
for wave in ["a", "b", "k"]:
    fname = DATA_ROOT / "ukhls" / f"{wave}_hhresp.tab"
    try:
        header = get_header(fname)
        hits = [
            h for h in header
            if "equ" in h.lower() or ("net" in h.lower() and "dv" in h.lower())
        ]
        if hits:
            print(f"  Wave {wave}: {hits}")
        else:
            # Show all dv-suffixed income vars
            dv = [h for h in header if "_dv" in h.lower() and "fihh" in h.lower()]
            print(f"  Wave {wave} (dv only): {dv}")
    except FileNotFoundError:
        print(f"  Wave {wave}: not found")

# Check the UKDA data dictionary for exact fihhmnnet1_dv description
DICT_ROOT_ENV = os.getenv("DATA_DICT_ROOT", "")
DICT_ROOT: Path
if not DICT_ROOT_ENV:
    DICT_ROOT = base_data_root / "data" / "UKDA-6614-tab" / "mrdoc" / "ukda_data_dictionaries"
else:
    DICT_ROOT = Path(DICT_ROOT_ENV)

def strip_rtf(raw: bytes) -> str:
    """Convert RTF bytes to plain text by stripping control words and braces."""
    text = raw.decode("latin-1", errors="replace")
    text = re.sub(r"\\[a-z]+\d*\s?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

# Get full description of the main net income variable from UKHLS wave a
fpath = DICT_ROOT / "ukhls" / "a_hhresp_ukda_data_dictionary.rtf"
with open(fpath, "rb") as f:
    raw = f.read()
text = strip_rtf(raw)

# Find fihhmnnet1_dv full description
idx = text.find("a_fihhmnnet1_dv")
if idx >= 0:
    print("\n=== a_fihhmnnet1_dv full description ===")
    print(text[idx:idx+500])

# Find fihhmngrs_dv full description for BHPS
fpath = DICT_ROOT / "bhps" / "br_hhresp_ukda_data_dictionary.rtf"
with open(fpath, "rb") as f:
    raw = f.read()
text = strip_rtf(raw)
idx = text.find("br_fihhmngrs_dv")
if idx >= 0:
    print("\n=== br_fihhmngrs_dv full description ===")
    print(text[idx:idx+400])

# Also check BHPS for a "net" household income variable
idx = text.find("hhneti")
if idx >= 0:
    print("\n=== br_hhneti description ===")
    print(text[idx:idx+400])

# Check what "hhneti" is
for wave in ["bq", "br"]:
    fname = DATA_ROOT / "bhps" / f"{wave}_hhresp.tab"
    header = get_header(fname)
    net_vars = [h for h in header if "hhnet" in h.lower()]
    print(f"\nBHPS {wave} hhnet vars: {net_vars}")
