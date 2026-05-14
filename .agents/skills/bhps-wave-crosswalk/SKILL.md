# /bhps-wave-crosswalk — Verify BHPS/USoc Variable Coding

Look up variable coding differences between BHPS and Understanding Society waves,
and generate the correct harmonisation code. Prevents the class of errors caused
by assuming coding is consistent across the survey bridge.

## Usage

```
/bhps-wave-crosswalk [variable-concept]
```

Example: `/bhps-wave-crosswalk health`
Example: `/bhps-wave-crosswalk` (interactive)

**Core rule:** Never assume BHPS and USoc share variable coding. Always check before implementing.

---

## Survey reference

| Survey | SN | Waves | Period | File prefix |
|---|---|---|---|---|
| BHPS | SN5151 | a–r (18) | 1991–2008 | `b{wave}_indresp.tab` e.g. `ba_indresp.tab` |
| USoc | SN6614 | a–n (14) | 2009–2023 | `{wave}_indresp.tab` e.g. `a_indresp.tab` |

USoc wave `a` = 2009 — **independent** of BHPS wave `a` (1991).
Python wave lists: `BHPS_WAVES = list("abcdefghijklmnopqr")`, `USOC_WAVES = list("abcdefghijklmn")`

---

## Known coding differences (quick reference)

### Employment status (jbstat) — HARMONISED ✓

Fully harmonised in SN6614 user guide. Code 10 (USoc-only) maps to "E".
See `trajectory_tda/data/employment_status.py` → `JBSTAT_TO_STATUS`.

### Income — NOT harmonised ⚠️

| | BHPS | USoc |
|---|---|---|
| Variable | `{w}fihhmn` | `fihhmnnet1_dv` |
| Equivalised? | **No** — apply OECD scale from `{w}hhresp` manually | **Yes** — pre-applied |

See `trajectory_tda/data/income_band.py` for the implemented harmonisation.

### NS-SEC — Scheme differs ⚠️

BHPS uses SOC 2000 coding rules; USoc uses SOC 2010. Not directly comparable.
3-class collapse reduces (but does not eliminate) the difference.
See `trajectory_tda/data/covariate_extractor.py` → `NSSEC3_MAP`.

### Self-rated health — Verify scale direction ⚠️

BHPS `{w}hlstat` and USoc `sf1` both 1–5 (excellent→poor) but **questionnaire changed**.
Always check scale direction before cross-wave analysis.

### Education (hiqual) — Category definitions changed ⚠️

BHPS `{w}hiqual` ≠ USoc `hiqual_dv` due to UK qualification framework changes.

---

## Generated code pattern

```python
def extract_[variable](
    data_dir: Path,
    waves: list[str] | None = None,
    survey: Literal["bhps", "usoc", "both"] = "both",
) -> pd.DataFrame:
    """Returns DataFrame: pidp | wave | year | [variable] | source"""
    ...
```

For unverified variables, add:
```python
# CODING UNVERIFIED: [variable] BHPS/USoc difference not checked.
# Before use: verify against UKDA-5151 and UKDA-6614 user guides.
```

---

## After finding a new coding difference

Use `/vault-sync` with type `[DATA]` to log in `04-Methods/Datasets/` vault note.
