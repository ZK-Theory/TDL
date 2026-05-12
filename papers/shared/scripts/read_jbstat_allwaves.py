# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Extract jbstat value labels from all UKHLS wave RTF data dictionaries
import os
import re
from pathlib import Path

base_path = Path(__file__).resolve().parents[3]
DICT_ROOT = os.getenv("DATA_DICT_ROOT", "")
if not DICT_ROOT:
    DICT_ROOT = base_path / "data" / "UKDA-6614-tab" / "mrdoc" / "ukda_data_dictionaries"
else:
    DICT_ROOT = Path(DICT_ROOT)

def strip_rtf(rtf_bytes: bytes) -> str:
    """Strip RTF markup from bytes and return plain text.

    Args:
        rtf_bytes: Raw RTF content read from a dictionary file.

    Returns:
        Plain text with control words, braces, and extra whitespace removed.
    """
    text = rtf_bytes.decode("latin-1", errors="replace")
    text = re.sub(r"\\[a-z]+\d*\s?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

def extract_jbstat_labels(text: str, wave: str) -> dict[int, str]:
    """Extract jbstat value labels from stripped RTF text.

    Args:
        text: Plain text obtained by stripping RTF control codes.
        wave: UKHLS wave prefix (a-o) used in the variable name.

    Returns:
        Mapping from numeric jbstat code to its label.
    """
    var_name = f"Variable = {wave}_jbstat "
    idx = text.find(var_name)
    if idx == -1:
        return None
    # Grab from "Value label information for {wave}_jbstat" onward
    block = text[idx: idx + 2000]
    pairs = re.findall(r"Value = (-?\d+(?:\.\d+)?) Label = (.+?)(?= Value = | Pos\. = |\Z)", block)
    result = {}
    for k, v in pairs:
        code = int(float(k))
        result[code] = v.strip()
    return result

waves = list("abcdefghijklmno")

print("=== jbstat positive-code labels by wave ===\n")
for wave in waves:
    fpath = DICT_ROOT / "ukhls" / f"{wave}_indresp_ukda_data_dictionary.rtf"
    if not fpath.exists():
        print(f"Wave {wave}: file not found")
        continue
    with open(fpath, "rb") as f:
        raw = f.read()
    text = strip_rtf(raw)
    labels = extract_jbstat_labels(text, wave)
    if labels is None:
        print(f"Wave {wave}: jbstat not found in dictionary")
        continue
    pos = {k: v for k, v in labels.items() if k > 0}
    codes_str = ", ".join(f"{k}={v!r}" for k, v in sorted(pos.items()))
    print(f"Wave {wave}: {codes_str}")
