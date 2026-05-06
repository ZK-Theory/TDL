# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Extract jbstat value labels from UKHLS wave k data dictionary RTF
import zipfile, re

zip_path = r"C:\Users\steph\TDL\data\UKDA-6614-tab\mrdoc\ukda_data_dictionaries.zip"

def strip_rtf(rtf_bytes):
    """Rough RTF -> plain text for pattern matching."""
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
# Look for patterns like "12 " or "12=" near jbstat section
jbstat_region_start = matches[0][0] if matches else 0
jbstat_region = text[jbstat_region_start:jbstat_region_start + 5000]
# Find lines with "12" "13" "14" "15"
for code in [10, 11, 12, 13, 14, 15]:
    pattern = rf"\b{code}\b.{{0,80}}"
    hits = re.findall(pattern, jbstat_region)
    for h in hits[:3]:
        print(f"  code {code}: {h.strip()}")
