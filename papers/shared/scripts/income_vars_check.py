# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Identify harmonised household income variables in UKHLS/BHPS data dictionaries
import os
import re
from pathlib import Path

DICT_ROOT = os.getenv("DATA_DICT_ROOT", "")
if not DICT_ROOT:
    DICT_ROOT = Path(__file__).resolve().parents[3] / "data" / "UKDA-6614-tab" / "mrdoc" / "ukda_data_dictionaries"
else:
    DICT_ROOT = Path(DICT_ROOT)

def strip_rtf(raw):
    text = raw.decode("latin-1", errors="replace")
    text = re.sub(r"\\[a-z]+\d*\s?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

def find_vars(text, keywords):
    pairs = re.findall(r"Variable = (\S+) Variable label = (.+?) (?:This variable|Pos\.)", text)
    return [(n, l.strip()) for n, l in pairs
            if any(k.lower() in l.lower() or k.lower() in n.lower() for k in keywords)]

# Check hhresp files (household-level derived income)
for wave, survey in [("a", "ukhls"), ("br", "bhps")]:
    fpath = DICT_ROOT / survey / f"{wave}_hhresp_ukda_data_dictionary.rtf"
    if not fpath.exists():
        print(f"{survey}/{wave}_hhresp: NOT FOUND")
        continue
    with open(fpath, "rb") as f:
        raw = f.read()
    text = strip_rtf(raw)
    print(f"\n=== {survey} wave {wave} hhresp: income vars ===")
    hits = find_vars(text, ["fihhm", "fihhn", "net3", "hhnet", "income", "monthly", "equivali"])
    for name, label in hits[:30]:
        print(f"  {name}: {label[:100]}")

# Also check if there's a specific harmonised income variable via xwavedat
fpath = DICT_ROOT / "ukhls" / "xwavedat_ukda_data_dictionary.rtf"
if fpath.exists():
    with open(fpath, "rb") as f:
        raw = f.read()
    text = strip_rtf(raw)
    print("\n=== xwavedat: income vars ===")
    hits = find_vars(text, ["fihhm", "income", "net3", "monthly"])
    for name, label in hits[:20]:
        print(f"  {name}: {label[:100]}")

# Check specific variable names from task spec
print("\n\n=== Searching for fihhmn / fihhmnnet3_dv specifically ===")
for wave, survey in [("br", "bhps"), ("a", "ukhls")]:
    for ftype in ["hhresp", "indresp"]:
        fpath = DICT_ROOT / survey / f"{wave}_{ftype}_ukda_data_dictionary.rtf"
        if not fpath.exists():
            continue
        with open(fpath, "rb") as f:
            raw = f.read()
        text = strip_rtf(raw)
        for varname in ["fihhmn", "fihhmnnet3_dv", "fihhmnlw", "fihhmnnet"]:
            if varname in text.lower():
                # Find surrounding context
                idx = text.lower().find(varname)
                print(f"  FOUND {varname} in {survey}/{wave}_{ftype}: ...{text[idx:idx+200]}...")
