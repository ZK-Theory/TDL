# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Extract jbstat value labels from UKHLS wave k data dictionary RTF
import re
import zipfile
import os
from pathlib import Path
from typing import Dict

DATA_DICT_ROOT = os.getenv("DATA_DICT_ROOT", "")
if DATA_DICT_ROOT:
    DATA_DICT_ROOT = Path(DATA_DICT_ROOT)
else:
    DATA_DICT_ROOT = Path(__file__).resolve().parents[3] / "data" / "UKDA-6614-tab"

if DATA_DICT_ROOT.is_dir():
    candidates = [
        DATA_DICT_ROOT / "ukda_data_dictionaries.zip",
        DATA_DICT_ROOT.parent / "ukda_data_dictionaries.zip",
        DATA_DICT_ROOT / "mrdoc" / "ukda_data_dictionaries.zip",
        DATA_DICT_ROOT.parent / "mrdoc" / "ukda_data_dictionaries.zip",
        DATA_DICT_ROOT / "ukda_data_dictionaries" / "ukda_data_dictionaries.zip",
    ]
    zip_path = next((p for p in candidates if p.exists()), candidates[0])
else:
    zip_path = DATA_DICT_ROOT

if not zip_path.exists():
    raise FileNotFoundError(f"ZIP archive not found: {zip_path}")

def strip_rtf(rtf_bytes: bytes) -> str:
    """Convert raw RTF bytes to a plain-text string.

    Args:
        rtf_bytes: Raw bytes read from an RTF file.

    Returns:
        Plain-text string with RTF control words and braces removed.
    """
    text = rtf_bytes.decode("latin-1", errors="replace")
    # Remove RTF control words and groups
    text = re.sub(r"\\[a-z]+\d*\s?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

# Read wave k data dictionary
target = "ukhls/k_indresp_ukda_data_dictionary.rtf"
with zipfile.ZipFile(zip_path, "r") as z:
    raw = z.read(target)

text = strip_rtf(raw)

# Find the jbstat section — search for "jbstat" and grab ~3000 chars around it
matches = [(m.start(), m.end()) for m in re.finditer(r"jbstat", text, re.I)]
print(f"Found {len(matches)} occurrences of 'jbstat' in wave k data dictionary")

if matches:
    # Look for the value labels section — typically after the variable name
    # Find first occurrence and print surrounding context
    for i, (start, end) in enumerate(matches[:5]):
        snippet = text[max(0, start-50):start+500]
        print(f"\n--- occurrence {i+1} at pos {start} ---")
        print(snippet)

# Also search specifically for codes 10-15 in numeric context near jbstat
print("\n\n=== Searching for value labels 10-15 ===")
if matches:
    # Look for patterns like "12 " or "12=" near jbstat section
    jbstat_region_start = matches[0][0]
    jbstat_region = text[jbstat_region_start:jbstat_region_start + 5000]
    # Find lines with "12" "13" "14" "15"
    for code in [10, 11, 12, 13, 14, 15]:
        pattern = rf"\b{code}\b.{{0,80}}"
        hits = re.findall(pattern, jbstat_region)
        for h in hits[:3]:
            print(f"  code {code}: {h.strip()}")
else:
    print("No jbstat section found; skipping code-specific search.")
