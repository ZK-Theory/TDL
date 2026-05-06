# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Extract jbstat value labels from all UKHLS wave RTF data dictionaries
import re, os

DICT_ROOT = r"C:\Users\steph\TDL\data\UKDA-6614-tab\mrdoc\ukda_data_dictionaries"

def strip_rtf(rtf_bytes):
    text = rtf_bytes.decode("latin-1", errors="replace")
    text = re.sub(r"\\[a-z]+\d*\s?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

def extract_jbstat_labels(text, wave):
    """Extract value labels for jbstat from stripped RTF text."""
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
    fpath = os.path.join(DICT_ROOT, "ukhls", f"{wave}_indresp_ukda_data_dictionary.rtf")
    if not os.path.exists(fpath):
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
