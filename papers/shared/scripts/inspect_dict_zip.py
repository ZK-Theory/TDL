# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Inspect UKDA data dictionaries zip for jbstat variable labels
import os
import re
import zipfile
from pathlib import Path

DATA_DICT_ROOT = os.getenv("DATA_DICT_ROOT", "")
if DATA_DICT_ROOT:
    DATA_DICT_ROOT = Path(DATA_DICT_ROOT)
else:
    DATA_DICT_ROOT = Path(__file__).resolve().parents[3] / "data" / "UKDA-6614-tab" / "mrdoc"

if DATA_DICT_ROOT.is_dir():
    candidate = DATA_DICT_ROOT / "ukda_data_dictionaries.zip"
    if candidate.exists():
        zip_path = candidate
    else:
        candidate = DATA_DICT_ROOT.parent / "ukda_data_dictionaries.zip"
        zip_path = candidate
else:
    zip_path = DATA_DICT_ROOT
if not zip_path.exists():
    raise FileNotFoundError(f"ZIP archive not found: {zip_path}")

with zipfile.ZipFile(zip_path, "r") as z:
    names = z.namelist()
    # Show files related to jbstat or wave 11
    print("Files mentioning 'jbstat' or 'indresp' or 'wave11':")
    relevant = [n for n in names if re.search(r"jbstat|indresp|wave11|wave_11|k_ind", n, re.I)]
    for n in relevant[:30]:
        print(" ", n)
    print(f"\nTotal files in zip: {len(names)}")
    # Show first 30 file names to understand structure
    print("\nFirst 30 files:")
    for n in names[:30]:
        print(" ", n)
