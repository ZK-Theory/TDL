# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Update jbstat coding JSON with document-verified labels and corrected bins
import json
import os
from datetime import date
from pathlib import Path

TODAY = date.today().isoformat()
out_dir = Path(os.getenv("OUT_DIR", Path(__file__).resolve().parents[3] / "results" / "panel_methodology" / "harmonisation"))
out_dir.mkdir(parents = True, exist_ok = True)
out_path = out_dir / f"jbstat_coding_{TODAY}.json"

# Document-verified labels from UKDA wave-level RTF data dictionaries
# Source: ukda_data_dictionaries/ukhls/{wave}_indresp_ukda_data_dictionary.rtf
# Verified 2026-05-06 across all 15 UKHLS waves (a-o); labels identical in all waves
verified_labels = {
    1: "Self employed",
    2: "Paid employment (ft/pt)",
    3: "Unemployed",
    4: "Retired",
    5: "On maternity leave",
    6: "Family care or home",
    7: "Full-time student",
    8: "LT sick or disabled",
    9: "Govt training scheme",
    10: "Unpaid, family business",
    11: "On apprenticeship",
    12: "On furlough",
    13: "Temporarily laid off/short term working",
    14: "On shared parental leave",
    15: "On adoption leave",
    97: "Doing something else",
}

# Corrected E/U/I bins — all verified against data dictionary labels
e_codes = [1, 2, 5, 11, 12, 13, 14, 15]
u_codes = [3, 9]
i_codes = [4, 6, 7, 8, 10, 97]

bin_map = {}
for c in e_codes:
    bin_map[c] = "E"
for c in u_codes:
    bin_map[c] = "U"
for c in i_codes:
    bin_map[c] = "I"

# Per-wave first-appearance data (from jbstat_audit.R run)
wave_first_appearance = {
    "code_10": "UKHLS wave a (all 15 UKHLS waves)",
    "code_11": "UKHLS wave c (waves c-o; absent a, b, all BHPS)",
    "code_12": "UKHLS wave k (waves k-o; COVID furlough scheme)",
    "code_13": "UKHLS wave k (waves k-o; counts 25-83 per wave)",
    "code_14": "UKHLS wave m (waves m-o; counts 2-4 per wave)",
    "code_15": "UKHLS wave n (waves n-o; counts 2-3 per wave)",
}

corrections = {
    "note": "Corrections applied 2026-05-06 after reading wave-level RTF data dictionaries",
    "code_11": {
        "initial_label_guess": "Waiting to take up a job",
        "correct_label": "On apprenticeship",
        "initial_bin": "I",
        "correct_bin": "E",
        "reason": "Apprentices are employed under Apprenticeship Agreements (paid workers); ILO: employed",
    },
    "code_13": {
        "initial_label_guess": "Apprenticeship scheme",
        "correct_label": "Temporarily laid off/short term working",
        "initial_bin": "E (analyst decision)",
        "correct_bin": "E",
        "reason": "Bin unchanged; label was incorrect. ILO: temporarily absent with job to return to = employed",
    },
    "code_14": {
        "initial_label_guess": "unknown",
        "correct_label": "On shared parental leave",
        "initial_bin": "I (conservative placeholder)",
        "correct_bin": "E",
        "reason": "Shared parental leave preserves employment relationship; analogous to maternity leave (code 5)",
    },
    "code_15": {
        "initial_label_guess": "unknown",
        "correct_label": "On adoption leave",
        "initial_bin": "I (conservative placeholder)",
        "correct_bin": "E",
        "reason": "Adoption leave preserves employment relationship; analogous to maternity leave (code 5)",
    },
}

output = {
    "audit_date": TODAY,
    "label_source": "UKDA data dictionaries: mrdoc/ukda_data_dictionaries/ukhls/{wave}_indresp_ukda_data_dictionary.rtf",
    "label_verification": "All codes 1-15 and 97 verified against wave-level RTF data dictionaries; labels identical across all UKHLS waves a-o",
    "verified_labels": {str(k): v for k, v in verified_labels.items()},
    "e_codes": e_codes,
    "u_codes": u_codes,
    "i_codes": i_codes,
    "bin_map": {str(k): v for k, v in bin_map.items()},
    "wave_first_appearance": wave_first_appearance,
    "corrections_from_initial_draft": corrections,
    "recode_r": (
        "jbstat_E <- c(1, 2, 5, 11, 12, 13, 14, 15)  # self-emp, employed, mat leave, "
        "apprenticeship, furlough, temp layoff, shared parental, adoption\n"
        "jbstat_U <- c(3, 9)  # ILO unemployed, govt training\n"
        "jbstat_I <- c(4, 6, 7, 8, 10, 97)  # retired, family care, student, LT sick, "
        "unpaid family business, other"
    ),
}

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
print(f"Written: {out_path}")
