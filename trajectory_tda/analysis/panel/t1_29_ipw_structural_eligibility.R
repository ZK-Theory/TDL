# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: T1.29 — IPW structural eligibility sensitivity.
#   Restricts the reference population to individuals who could structurally
#   complete ≥10 waves (UKHLS: enrolled ≤ wave f by ~2014; BHPS: enrolled ≤ wave bi
#   by 1999). Re-fits the propensity model and compares ESS + weight distribution
#   to T1.13 baseline. Addresses reviewer attrition concern: does including
#   structurally late-joiners inflate attrition weight variance?
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/t1_29_ipw_structural_eligibility.R

suppressPackageStartupMessages({
  library(dplyr)
  library(pROC)
  library(jsonlite)
  library(data.table)
})

set.seed(42)

PROJ_ROOT   <- "C:/Users/steph/TDL"
WORKTREE    <- normalizePath(getwd(), mustWork = FALSE)
DATA_TAB    <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab")
BHPS_DIR    <- file.path(DATA_TAB, "bhps")
UKHLS_DIR   <- file.path(DATA_TAB, "ukhls")
RESULTS_DIR <- file.path(PROJ_ROOT, "results/trajectory_tda_integration")
BASELINE_IPW <- file.path(PROJ_ROOT, "results/panel_methodology/weights/ipw_diagnostics_2026-05-13.json")

OUT_DIR  <- file.path(WORKTREE, "results/panel_methodology/weights")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY    <- format(Sys.Date(), "%Y-%m-%d")
OUT_PATH <- file.path(OUT_DIR, paste0("ipw_structural_eligible_sensitivity_", TODAY, ".json"))

# Structural cutoffs: ≥10 waves available
# BHPS 18 waves (ba=1991...br=2008): enrol ≤ wave bi (1999) → 10 waves bi..br
# UKHLS 15 waves (a=2009...o=2023): enrol ≤ wave f (2014-15) → 10 waves f..o
BHPS_WAVES     <- paste0("b", letters[1:18])
BHPS_YEARS     <- 1991:2008
UKHLS_WAVES    <- letters[1:15]
UKHLS_YEARS    <- 2009:2023

BHPS_MAX_ENTRY_WAVE  <- "bi"    # wave 9 of BHPS (1999)
UKHLS_MAX_ENTRY_WAVE <- "f"     # wave 6 of UKHLS (2014-15)
BHPS_MAX_ENTRY_IDX   <- 9L      # index in BHPS_WAVES
UKHLS_MAX_ENTRY_IDX  <- 6L      # index in UKHLS_WAVES

E_CODES <- c(1L, 2L, 5L, 11L, 12L, 13L, 14L, 15L)
U_CODES <- c(3L, 9L)
I_CODES <- c(4L, 6L, 7L, 8L, 10L, 97L)

recode_jbstat <- function(x) {
  x <- as.integer(x)
  r <- rep(NA_character_, length(x))
  r[x %in% E_CODES] <- "E"; r[x %in% U_CODES] <- "U"; r[x %in% I_CODES] <- "I"
  r
}

cat("=== T1.29: IPW Structural Eligibility Sensitivity ===\n")
cat("Cutoffs: BHPS ≤", BHPS_MAX_ENTRY_WAVE, "(", BHPS_YEARS[BHPS_MAX_ENTRY_IDX], ")",
    "| UKHLS ≤", UKHLS_MAX_ENTRY_WAVE, "(", UKHLS_YEARS[UKHLS_MAX_ENTRY_IDX], ")\n")

# ---------------------------------------------------------------------------
# 1. Load analytical sample pidps (n=27,280)
# ---------------------------------------------------------------------------
cat("Loading analytical sample pidps...\n")
traj <- fromJSON(file.path(RESULTS_DIR, "01_trajectories.json"))
analytical_pidps <- as.integer(unlist(traj$metadata$pidp))
n_analytical <- length(analytical_pidps)
cat("Analytical sample n =", n_analytical, "\n")

# ---------------------------------------------------------------------------
# 2. Helper: read one indresp wave
# ---------------------------------------------------------------------------
read_indresp_wave <- function(fpath, wave, year, era) {
  if (!file.exists(fpath)) return(NULL)
  hdr <- names(fread(fpath, nrows = 0L, sep = "\t"))

  jbstat_col <- if (paste0(wave, "_jbstat_bh") %in% hdr) paste0(wave, "_jbstat_bh")
                else if (paste0(wave, "_jbstat") %in% hdr) paste0(wave, "_jbstat")
                else return(NULL)
  hiqual_col <- paste0(wave, "_hiqual_dv")
  gor_col    <- paste0(wave, "_gor_dv")
  hidp_col   <- paste0(wave, "_hidp")
  lw_col <- if      (paste0(wave, "_indinub_lw") %in% hdr) paste0(wave, "_indinub_lw")
            else if (paste0(wave, "_indin01_lw") %in% hdr) paste0(wave, "_indin01_lw")
            else if (paste0(wave, "_indin91_lw") %in% hdr) paste0(wave, "_indin91_lw")
            else NA_character_

  wanted <- unique(c("pidp", jbstat_col,
                     intersect(c(hiqual_col, gor_col, hidp_col), hdr),
                     if (!is.na(lw_col)) lw_col else character(0)))
  dt <- fread(fpath, sep = "\t", select = wanted)
  wi <- if (era == "BHPS") which(BHPS_WAVES == wave) else which(UKHLS_WAVES == wave)
  dt[, jbstat_raw := as.integer(get(jbstat_col))]
  dt[, jbstat_bin := recode_jbstat(jbstat_raw)]
  dt[, wave_label := wave]
  dt[, wave_year  := as.integer(year)]
  dt[, era        := era]
  dt[, wave_index := wi]
  if (hiqual_col %in% names(dt)) setnames(dt, hiqual_col, "hiqual_dv")
  if (gor_col    %in% names(dt)) setnames(dt, gor_col,    "gor_dv")
  if (hidp_col   %in% names(dt)) setnames(dt, hidp_col,   "hidp")
  if (!is.na(lw_col) && lw_col %in% names(dt)) setnames(dt, lw_col, "lw_base")
  dt <- dt[!is.na(jbstat_bin)]
  dt
}

# ---------------------------------------------------------------------------
# 3. Scan BHPS and UKHLS indresp — first-wave-only for eligibility
# ---------------------------------------------------------------------------
cat("Scanning BHPS waves for first-wave observation...\n")
bhps_list <- lapply(seq_along(BHPS_WAVES), function(i) {
  read_indresp_wave(file.path(BHPS_DIR, paste0(BHPS_WAVES[i], "_indresp.tab")),
                   BHPS_WAVES[i], BHPS_YEARS[i], "BHPS")
})
bhps_all <- rbindlist(Filter(Negate(is.null), bhps_list), fill = TRUE, use.names = TRUE)
bhps_first <- bhps_all[order(pidp, wave_year), .SD[1L], by = pidp]
cat("  BHPS first-wave individuals:", nrow(bhps_first), "\n")

cat("Scanning UKHLS waves for first-wave observation...\n")
ukhls_list <- lapply(seq_along(UKHLS_WAVES), function(i) {
  read_indresp_wave(file.path(UKHLS_DIR, paste0(UKHLS_WAVES[i], "_indresp.tab")),
                   UKHLS_WAVES[i], UKHLS_YEARS[i], "UKHLS")
})
ukhls_all <- rbindlist(Filter(Negate(is.null), ukhls_list), fill = TRUE, use.names = TRUE)
ukhls_first <- ukhls_all[order(pidp, wave_year), .SD[1L], by = pidp]
cat("  UKHLS first-wave individuals:", nrow(ukhls_first), "\n")

# ---------------------------------------------------------------------------
# 4. Build eligible population and apply structural cutoff
# ---------------------------------------------------------------------------
cat("Building eligible population + applying structural cutoff...\n")
xwave <- fread(file.path(UKHLS_DIR, "xwavedat.tab"), sep = "\t",
               select = c("pidp", "sex", "birthy"))
xwave <- xwave[birthy > 0L & sex > 0L]

combined <- rbindlist(list(bhps_first, ukhls_first), fill = TRUE, use.names = TRUE)
combined  <- combined[order(pidp, wave_year)]
eligible  <- combined[, .SD[1L], by = pidp]
eligible  <- merge(eligible, xwave, by = "pidp", all.x = TRUE)

n_full_eligible <- nrow(eligible)
cat("Full eligible population (before structural cutoff) n =", n_full_eligible, "\n")

# Apply structural cutoff: keep only those who entered early enough
eligible[, structurally_eligible := fifelse(
  era == "BHPS",
  wave_index <= BHPS_MAX_ENTRY_IDX,
  fifelse(era == "UKHLS", wave_index <= UKHLS_MAX_ENTRY_IDX, FALSE)
)]

n_struct <- sum(eligible$structurally_eligible, na.rm = TRUE)
cat("Structurally eligible (≥10 waves available): n =", n_struct,
    sprintf("(%.1f%% of full eligible)\n", 100*n_struct/n_full_eligible))

eligible_struct <- eligible[structurally_eligible == TRUE]
eligible_struct[, in_analytical_sample := as.integer(pidp %in% analytical_pidps)]
n_anal_struct <- sum(eligible_struct$in_analytical_sample)
cat("Analytical sample within structural eligible: n =", n_anal_struct,
    sprintf("(%.1f%% of analytical n=%d)\n", 100*n_anal_struct/n_analytical, n_analytical))

# ---------------------------------------------------------------------------
# 5. Load income and assign within-era terciles (LOCKED Option A)
# ---------------------------------------------------------------------------
cat("Loading income data for within-era tercile assignment...\n")

load_hhresp_income <- function(dir, wave_list) {
  out <- lapply(wave_list, function(wave) {
    fpath <- file.path(dir, paste0(wave, "_hhresp.tab"))
    if (!file.exists(fpath)) return(NULL)
    hdr <- names(fread(fpath, nrows = 0L, sep = "\t"))
    hidp_col   <- paste0(wave, "_hidp")
    income_col <- paste0(wave, "_fihhmngrs_dv")
    if (!hidp_col %in% hdr || !income_col %in% hdr) return(NULL)
    dt <- fread(fpath, sep = "\t", select = c(hidp_col, income_col))
    setnames(dt, c(hidp_col, income_col), c("hidp", "fihhmngrs_dv"))
    dt[, wave_label := wave]
    dt
  })
  rbindlist(Filter(Negate(is.null), out), use.names = TRUE)
}

bhps_income  <- load_hhresp_income(BHPS_DIR,  BHPS_WAVES)
ukhls_income <- load_hhresp_income(UKHLS_DIR, UKHLS_WAVES)

eligible_hidp <- eligible_struct[!is.na(hidp), .(pidp, wave_label, hidp, era)]

bhps_inc <- merge(eligible_hidp[era == "BHPS"],  bhps_income,
                  by = c("hidp", "wave_label"), all.x = TRUE)
ukhls_inc <- merge(eligible_hidp[era == "UKHLS"], ukhls_income,
                   by = c("hidp", "wave_label"), all.x = TRUE)
inc_combined <- rbindlist(list(bhps_inc, ukhls_inc), fill = TRUE)

inc_valid <- inc_combined[!is.na(fihhmngrs_dv) & fihhmngrs_dv >= 0]
bhps_cuts  <- quantile(inc_valid[era == "BHPS",  fihhmngrs_dv], c(1/3, 2/3), na.rm = TRUE)
ukhls_cuts <- quantile(inc_valid[era == "UKHLS", fihhmngrs_dv], c(1/3, 2/3), na.rm = TRUE)

inc_combined[, income_tercile_init := fifelse(
  era == "BHPS",
  fifelse(fihhmngrs_dv <= bhps_cuts[1], "L",
    fifelse(fihhmngrs_dv <= bhps_cuts[2], "M", "H")),
  fifelse(fihhmngrs_dv <= ukhls_cuts[1], "L",
    fifelse(fihhmngrs_dv <= ukhls_cuts[2], "M", "H"))
)]
inc_tercile <- inc_combined[!is.na(income_tercile_init)][
  order(pidp, wave_label), .SD[1L], by = pidp][, .(pidp, income_tercile_init)]

# ---------------------------------------------------------------------------
# 6. Assemble modelling dataset
# ---------------------------------------------------------------------------
cat("Assembling modelling dataset...\n")
model_data <- merge(eligible_struct, inc_tercile, by = "pidp", all.x = TRUE)
model_data[, birth_cohort_group := cut(
  as.integer(birthy),
  breaks = c(-Inf, 1940L, 1950L, 1960L, 1970L, 1980L, 1990L, Inf),
  labels = c("pre1940","1940s","1950s","1960s","1970s","1980s","1990+"), right = TRUE
)]
model_data[, age_at_first   := as.integer(wave_year) - as.integer(birthy)]
model_data[age_at_first < 16L | age_at_first > 80L, age_at_first := NA_integer_]
model_data[, survey_origin  := era]

for (col in c("sex","hiqual_dv","gor_dv","jbstat_bin",
              "income_tercile_init","birth_cohort_group","survey_origin")) {
  if (col %in% names(model_data)) model_data[, (col) := as.factor(get(col))]
}

core <- intersect(c("age_at_first","sex","hiqual_dv","jbstat_bin","income_tercile_init",
                    "gor_dv","birth_cohort_group","survey_origin"), names(model_data))
mdf <- model_data[complete.cases(model_data[, ..core])]
cat("Rows for propensity model:", nrow(mdf),
    "(analytical:", sum(mdf$in_analytical_sample), ")\n")

# ---------------------------------------------------------------------------
# 7. Fit propensity model
# ---------------------------------------------------------------------------
cat("Fitting propensity model on structurally eligible population...\n")
preds <- intersect(
  c("age_at_first","sex","hiqual_dv","jbstat_bin","income_tercile_init",
    "gor_dv","birth_cohort_group","survey_origin"),
  names(mdf)
)
formula_str <- paste("in_analytical_sample ~", paste(preds, collapse = " + "))
cat("Formula:", formula_str, "\n")

prop_model <- tryCatch(
  glm(as.formula(formula_str), data = mdf, family = binomial(link = "logit")),
  error = function(e) { cat("Model error:", conditionMessage(e), "\n"); NULL }
)
if (is.null(prop_model)) stop("Propensity model failed.")

propensity <- predict(prop_model, newdata = mdf, type = "response")
propensity <- pmax(pmin(propensity, 0.995), 0.005)

roc_obj <- roc(mdf$in_analytical_sample, propensity, quiet = TRUE)
auc_val  <- as.numeric(auc(roc_obj))
cat("AUC:", round(auc_val, 4), "\n")

# ---------------------------------------------------------------------------
# 8. Construct and trim IPW
# ---------------------------------------------------------------------------
cat("Constructing IPW...\n")
lw_vals <- as.numeric(mdf$lw_base)
lw_vals[is.na(lw_vals) | lw_vals <= 0] <- 1.0

ipw_raw     <- lw_vals / propensity
trim_lo     <- quantile(ipw_raw, 0.01, na.rm = TRUE)
trim_hi     <- quantile(ipw_raw, 0.99, na.rm = TRUE)
ipw_trimmed <- pmax(pmin(ipw_raw, trim_hi), trim_lo)
ess         <- (sum(ipw_trimmed))^2 / sum(ipw_trimmed^2)
cat("ESS:", round(ess, 1), "\n")

# Load T1.13 baseline ESS for comparison
baseline_ess <- tryCatch({
  b <- fromJSON(BASELINE_IPW)
  b$effective_sample_size
}, error = function(e) NA_real_)
cat("T1.13 baseline ESS:", baseline_ess, "\n")

dist_stats <- function(x) list(
  min  = round(min(x,  na.rm=TRUE), 4),
  p1   = round(quantile(x, 0.01, na.rm=TRUE), 4),
  p5   = round(quantile(x, 0.05, na.rm=TRUE), 4),
  p25  = round(quantile(x, 0.25, na.rm=TRUE), 4),
  p50  = round(median(x, na.rm=TRUE), 4),
  p75  = round(quantile(x, 0.75, na.rm=TRUE), 4),
  p95  = round(quantile(x, 0.95, na.rm=TRUE), 4),
  p99  = round(quantile(x, 0.99, na.rm=TRUE), 4),
  max  = round(max(x,  na.rm=TRUE), 4),
  mean = round(mean(x, na.rm=TRUE), 4),
  cv   = round(sd(x, na.rm=TRUE) / mean(x, na.rm=TRUE), 4)
)

# ---------------------------------------------------------------------------
# 9. Save output JSON
# ---------------------------------------------------------------------------
cat("Saving output JSON...\n")
result <- list(
  run_params = list(
    seed = 42L, date = TODAY,
    structural_cutoff = list(
      bhps_max_entry_wave  = BHPS_MAX_ENTRY_WAVE,
      bhps_max_entry_year  = BHPS_YEARS[BHPS_MAX_ENTRY_IDX],
      ukhls_max_entry_wave = UKHLS_MAX_ENTRY_WAVE,
      ukhls_max_entry_year = UKHLS_YEARS[UKHLS_MAX_ENTRY_IDX],
      min_waves_available  = 10L,
      rationale = paste0(
        "Restricts to individuals who enrolled early enough to have had ≥10 panel waves ",
        "available: BHPS enrolment ≤ wave bi (1999) gives waves bi..br = 10 waves; ",
        "UKHLS enrolment ≤ wave f (2014-15) gives waves f..o = 10 waves."
      )
    )
  ),
  population_counts = list(
    full_eligible          = n_full_eligible,
    structurally_eligible  = n_struct,
    pct_structurally_elig  = round(100 * n_struct / n_full_eligible, 2),
    analytical_total       = n_analytical,
    analytical_in_struct   = n_anal_struct,
    pct_analytical_in_struct = round(100 * n_anal_struct / n_analytical, 2)
  ),
  propensity_model = list(
    n_model_rows = nrow(mdf),
    n_analytical = sum(mdf$in_analytical_sample),
    auc          = round(auc_val, 6),
    formula      = formula_str
  ),
  ipw_distribution = list(
    raw         = dist_stats(ipw_raw),
    trimmed     = dist_stats(ipw_trimmed),
    trim_bounds = list(lower = round(trim_lo, 4), upper = round(trim_hi, 4))
  ),
  effective_sample_size = round(ess, 2),
  baseline_comparison = list(
    t1_13_ess           = baseline_ess,
    t1_29_ess           = round(ess, 2),
    ess_change_absolute = (if (is.na(baseline_ess) || baseline_ess == 0) NA_real_
                           else round(ess - baseline_ess, 2)),
    ess_pct_change      = (if (is.na(baseline_ess) || baseline_ess == 0) NA_real_
                           else round(100 * (ess - baseline_ess) / baseline_ess, 2)),
    baseline_note       = (if (is.na(baseline_ess)) {
      "baseline_ess unavailable; comparison not computed"
    } else if (baseline_ess == 0) {
      "baseline_ess is zero; pct change undefined"
    } else {
      paste0("baseline_ess from ", BASELINE_IPW)
    })
  )
)

write(toJSON(result, auto_unbox = TRUE, pretty = TRUE), OUT_PATH)
cat("Saved:", OUT_PATH, "\n")
cat("=== T1.29 complete ===\n")
