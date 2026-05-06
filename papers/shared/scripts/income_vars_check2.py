# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Check actual hhresp column headers for income variables
import re

DATA_ROOT = r"C:\Users\steph\TDL\data\UKDA-6614-tab\tab"

def get_matching_cols(fname, keywords):
    with open(fname, "r", encoding="latin-1") as f:
        header = f.readline().strip().split("\t")
    header = [h.strip() for h in header]
    return [h for h in header if any(k.lower() in h.lower() for k in keywords)]

keywords = ["fihhm", "fihhn", "net3", "hhnet", "fihhynl", "equi"]

# UKHLS waves a and k
for wave in ["a", "k"]:
    fname = f"{DATA_ROOT}/ukhls/{wave}_hhresp.tab"
    try:
        cols = get_matching_cols(fname, keywords)
        print(f"UKHLS {wave} hhresp income cols: {cols}")
    except FileNotFoundError:
        print(f"UKHLS {wave} hhresp: not found")

# BHPS waves br (last BHPS) and bq
for wave in ["bq", "br"]:
    fname = f"{DATA_ROOT}/bhps/{wave}_hhresp.tab"
    try:
        cols = get_matching_cols(fname, keywords)
        print(f"BHPS {wave} hhresp income cols: {cols}")
    except FileNotFoundError:
        print(f"BHPS {wave} hhresp: not found")

# Also check for fihhmn specifically in BHPS indresp
fname = f"{DATA_ROOT}/bhps/br_hhresp.tab"
try:
    with open(fname, "r", encoding="latin-1") as f:
        header = f.readline().strip().split("\t")
    header = [h.strip() for h in header]
    fihhmn_cols = [h for h in header if "fihhmn" in h.lower()]
    print(f"\nBHPS br hhresp fihhmn* cols: {fihhmn_cols}")
except Exception as e:
    print(f"Error: {e}")

# Check UKHLS wave a for net3
fname = f"{DATA_ROOT}/ukhls/a_hhresp.tab"
try:
    with open(fname, "r", encoding="latin-1") as f:
        header = f.readline().strip().split("\t")
    header = [h.strip() for h in header]
    net_cols = [h for h in header if "net" in h.lower() and "fihhm" in h.lower()]
    print(f"\nUKHLS a hhresp fihhm*net* cols: {net_cols}")
except Exception as e:
    print(f"Error: {e}")
