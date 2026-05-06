# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Inspect UKDA data dictionaries zip for jbstat variable labels
import zipfile, os, re

zip_path = r"C:\Users\steph\TDL\data\UKDA-6614-tab\mrdoc\ukda_data_dictionaries.zip"

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
