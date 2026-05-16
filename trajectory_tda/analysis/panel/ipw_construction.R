# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Two-stage IPW construction — longitudinal survey weight x continuity propensity score

# Variable name audit (verified against actual UKDA files):
#   BHPS jbstat:     {wave}_jbstat_bh (ba only) OR {wave}_jbstat (bb–br)
#   UKHLS jbstat:    {wave}_jbstat
#   Education:       {wave}_hiqual_dv  (in indresp)
#   Region:          {wave}_gor_dv     (in indresp)
#   Longitudinal wt: {wave}_indinub_lw (UKHLS wave c+, BHPS+GPS+EMBS)
#                    {wave}_indin01_lw (BHPS-UK longitudinal; present in ba_indresp onwards)
#   Income (BHPS):   {wave}_fihhmngrs_dv  (in hhresp, wave-prefixed)
#   Income (UKHLS):  {wave}_fihhmngrs_dv  (in hhresp, wave-prefixed)
#   hidp (BHPS):     {wave}_hidp
#   hidp (UKHLS):    {wave}_hidp
#   Permanent vars:  pidp, sex, birthy in xwavedat.tab
#
# Note: "lwtresp" referenced in task spec does not exist in data; the actual
# longitudinal weight variables are {wave}_indinub_lw (UKHLS) / {wave}_indin01_lw (BHPS).
#
# Locked codings (T0.9): E={1,2,5,11,12,13,14,15}, U={3,9}, I={4,6,7,8,10,97}
# Locked income tercile (T0.10): within-era (BHPS and UKHLS separately)
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/ipw_construction.R

suppressPackageStartupMessages({
  library(dplyr)
  library(haven)
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
OUT_DIR     <- file.path(WORKTREE, "results/panel_methodology/weights")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY        <- format(Sys.Date(), "%Y-%m-%d")
OUT_PATH     <- file.path(OUT_DIR, paste0("ipw_diagnostics_", TODAY, ".json"))
WEIGHTS_RDS  <- file.path(OUT_DIR, paste0("ipw_individual_weights_", TODAY, ".rds"))

cat("=== T1.13: IPW Construction ===\n")

# ---------------------------------------------------------------------------
# 1. Load analytical sample pidps
# ---------------------------------------------------------------------------
cat("Loading analytical sample pidps...\n")
traj <- fromJSON(file.path(RESULTS_DIR, "01_trajectories.json"))
analytical_pidps <- as.integer(unlist(traj$metadata$pidp))
n_analytical <- length(analytical_pidps)
cat("Analytical sample n =", n_analytical, "\n")

# ---------------------------------------------------------------------------
# 2. Locked jbstat recoding (T0.9)
# ---------------------------------------------------------------------------
E_CODES <- c(1L, 2L, 5L, 11L, 12L, 13L, 14L, 15L)
U_CODES <- c(3L, 9L)
I_CODES <- c(4L, 6L, 7L, 8L, 10L, 97L)

recode_jbstat <- function(x) {
  x <- as.integer(x)
  result <- rep(NA_character_, length(x))
  result[x %in% E_CODES] <- "E"
  result[x %in% U_CODES] <- "U"
  result[x %in% I_CODES] <- "I"
  result
}

# ---------------------------------------------------------------------------
# 3. Helper: read one indresp wave, return standardised data.table
# ---------------------------------------------------------------------------
read_indresp_wave <- function(fpath, wave, year, era) {
  if (!file.exists(fpath)) return(NULL)
  hdr <- names(fread(fpath, nrows = 0L, sep = "\t"))

  # jbstat: try _bh variant first (ba only), then plain
  jbstat_col <- if (paste0(wave, "_jbstat_bh") %in% hdr) paste0(wave, "_jbstat_bh")
                else if (paste0(wave, "_jbstat")    %in% hdr) paste0(wave, "_jbstat")
                else return(NULL)

  hiqual_col <- paste0(wave, "_hiqual_dv")
  gor_col    <- paste0(wave, "_gor_dv")
  hidp_col   <- paste0(wave, "_hidp")

  # Longitudinal weight: indinub_lw (UKHLS c+) > indin01_lw (BHPS-UK) > indin91_lw (BHPS-GB)
  lw_col <- if      (paste0(wave, "_indinub_lw") %in% hdr) paste0(wave, "_indinub_lw")
            else if (paste0(wave, "_indin01_lw") %in% hdr) paste0(wave, "_indin01_lw")
            else if (paste0(wave, "_indin91_lw") %in% hdr) paste0(wave, "_indin91_lw")
            else NA_character_

  wanted <- unique(c("pidp", jbstat_col,
                      intersect(c(hiqual_col, gor_col, hidp_col), hdr),
                      if (!is.na(lw_col)) lw_col else character(0)))
  dt <- fread(fpath, sep = "\t", select = wanted)

  dt[, jbstat_raw  := as.integer(get(jbstat_col))]
  dt[, jbstat_bin  := recode_jbstat(jbstat_raw)]
  dt[, wave_label  := wave]
  dt[, wave_year   := as.integer(year)]
  dt[, era         := era]

  if (hiqual_col %in% names(dt)) setnames(dt, hiqual_col, "hiqual_dv")
  if (gor_col    %in% names(dt)) setnames(dt, gor_col,    "gor_dv")
  if (hidp_col   %in% names(dt)) setnames(dt, hidp_col,   "hidp")
  if (!is.na(lw_col) && lw_col %in% names(dt)) setnames(dt, lw_col, "lw_base")

  dt <- dt[!is.na(jbstat_bin)]
  dt
}

# ---------------------------------------------------------------------------
# 4. Scan BHPS and UKHLS indresp waves
# ---------------------------------------------------------------------------
BHPS_WAVES  <- paste0("b", letters[1:18])
BHPS_YEARS  <- 1991:2008
UKHLS_WAVES <- letters[1:15]
UKHLS_YEARS <- 2009:2023

cat("Scanning BHPS waves...\n")
bhps_list <- lapply(seq_along(BHPS_WAVES), function(i) {
  read_indresp_wave(file.path(BHPS_DIR, paste0(BHPS_WAVES[i], "_indresp.tab")),
                    BHPS_WAVES[i], BHPS_YEARS[i], "BHPS")
})
bhps_all <- rbindlist(Filter(Negate(is.null), bhps_list), fill = TRUE, use.names = TRUE)
cat("  BHPS person-wave rows (valid jbstat):", nrow(bhps_all), "\n")

cat("Scanning UKHLS waves...\n")
ukhls_list <- lapply(seq_along(UKHLS_WAVES), function(i) {
  read_indresp_wave(file.path(UKHLS_DIR, paste0(UKHLS_WAVES[i], "_indresp.tab")),
                    UKHLS_WAVES[i], UKHLS_YEARS[i], "UKHLS")
})
ukhls_all <- rbindlist(Filter(Negate(is.null), ukhls_list), fill = TRUE, use.names = TRUE)
cat("  UKHLS person-wave rows (valid jbstat):", nrow(ukhls_all), "\n")

# First observed wave per individual per era
bhps_first  <- bhps_all[order(pidp, wave_year), .SD[1L], by = pidp]
ukhls_first <- ukhls_all[order(pidp, wave_year), .SD[1L], by = pidp]

# ---------------------------------------------------------------------------
# 5. Build eligible population (union, keep earliest first observation)
# ---------------------------------------------------------------------------
cat("Building eligible population...\n")
xwave <- fread(file.path(UKHLS_DIR, "xwavedat.tab"), sep = "\t",
               select = c("pidp", "sex", "birthy"))
xwave <- xwave[birthy > 0L & sex > 0L]

combined <- rbindlist(list(bhps_first, ukhls_first), fill = TRUE, use.names = TRUE)
combined  <- combined[order(pidp, wave_year)]
eligible  <- combined[, .SD[1L], by = pidp]
eligible  <- merge(eligible, xwave, by = "pidp", all.x = TRUE)
eligible[, in_analytical_sample := as.integer(pidp %in% analytical_pidps)]
n_eligible <- nrow(eligible)
cat("Eligible population n =", n_eligible, "(analytical:", sum(eligible$in_analytical_sample), ")\n")

# ---------------------------------------------------------------------------
# 6. Load income and assign within-era terciles (LOCKED Option A)
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
cat("  BHPS hhresp income rows:", nrow(bhps_income), "\n")
cat("  UKHLS hhresp income rows:", nrow(ukhls_income), "\n")

# Join income to eligible individuals via hidp at first wave
eligible_hidp <- eligible[!is.na(hidp), .(pidp, wave_label, hidp, era)]

bhps_inc <- merge(
  eligible_hidp[era == "BHPS"],
  bhps_income,
  by = c("hidp", "wave_label"), all.x = TRUE
)
ukhls_inc <- merge(
  eligible_hidp[era == "UKHLS"],
  ukhls_income,
  by = c("hidp", "wave_label"), all.x = TRUE
)
inc_combined <- rbindlist(list(bhps_inc, ukhls_inc), fill = TRUE)

# Within-era tercile cut-points
inc_valid <- inc_combined[!is.na(fihhmngrs_dv) & fihhmngrs_dv >= 0]
cat("Tercile cuts computed including zero-income households (CR fix: prior `> 0` filter excluded legitimate zeros).\n")
bhps_cuts  <- quantile(inc_valid[era == "BHPS",  fihhmngrs_dv], c(1/3, 2/3), na.rm = TRUE)
ukhls_cuts <- quantile(inc_valid[era == "UKHLS", fihhmngrs_dv], c(1/3, 2/3), na.rm = TRUE)
cat("  BHPS income tercile cuts: L/M=", round(bhps_cuts[1]),
    " M/H=", round(bhps_cuts[2]), "\n")
cat("  UKHLS income tercile cuts: L/M=", round(ukhls_cuts[1]),
    " M/H=", round(ukhls_cuts[2]), "\n")

inc_combined[, income_tercile_init := fifelse(
  era == "BHPS",
  fifelse(fihhmngrs_dv <= bhps_cuts[1], "L",
    fifelse(fihhmngrs_dv <= bhps_cuts[2], "M", "H")),
  fifelse(fihhmngrs_dv <= ukhls_cuts[1], "L",
    fifelse(fihhmngrs_dv <= ukhls_cuts[2], "M", "H"))
)]

inc_tercile <- inc_combined[!is.na(income_tercile_init)][order(pidp, wave_label), .SD[1L], by = pidp][, .(pidp, income_tercile_init)]
# ---------------------------------------------------------------------------
# 7. Assemble modelling dataset
# ---------------------------------------------------------------------------
cat("Assembling modelling dataset...\n")
model_data <- merge(eligible, inc_tercile, by = "pidp", all.x = TRUE)
model_data[, birth_cohort_group := cut(
  as.integer(birthy),
  breaks = c(-Inf, 1940L, 1950L, 1960L, 1970L, 1980L, 1990L, Inf),
  labels = c("pre1940","1940s","1950s","1960s","1970s","1980s","1990+"),
  right  = TRUE
)]
model_data[, age_at_first := as.integer(wave_year) - as.integer(birthy)]
model_data[age_at_first < 16L | age_at_first > 80L, age_at_first := NA_integer_]
model_data[, survey_origin := era]

# Factorise predictors
for (col in c("sex","hiqual_dv","gor_dv","jbstat_bin",
              "income_tercile_init","birth_cohort_group","survey_origin")) {
  if (col %in% names(model_data)) model_data[, (col) := as.factor(get(col))]
}

# Drop rows missing any propensity predictor (income_tercile_init included: NA propagates to predict)
core <- intersect(c("age_at_first","sex","hiqual_dv","jbstat_bin","income_tercile_init",
                    "gor_dv","birth_cohort_group","survey_origin"),
                  names(model_data))
mdf <- model_data[complete.cases(model_data[, ..core])]
cat("Rows for propensity model:", nrow(mdf),
    "(analytical:", sum(mdf$in_analytical_sample), ")\n")

# ---------------------------------------------------------------------------
# 8. Fit propensity model
# ---------------------------------------------------------------------------
cat("Fitting propensity model...\n")
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
coef_list <- as.list(round(coef(prop_model), 6))

# ---------------------------------------------------------------------------
# 9. Construct and trim IPW
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

weights_df <- data.table(pidp = mdf$pidp, ipw_trimmed = ipw_trimmed,
                         in_analytical_sample = mdf$in_analytical_sample)
saveRDS(weights_df, WEIGHTS_RDS)
cat("Saved individual weights RDS:", WEIGHTS_RDS, "\n")

# ---------------------------------------------------------------------------
# 10. SMD diagnostics (pre/post weighting) and propensity overlap by cohort (A2)
# ---------------------------------------------------------------------------
cat("Computing SMD diagnostics and propensity overlap...\n")

compute_smd_val <- function(x, group, wts = NULL) {
  xa <- x[group == 1L]; xb <- x[group == 0L]
  if (is.null(wts)) {
    ma <- mean(xa, na.rm=TRUE); mb <- mean(xb, na.rm=TRUE)
    va <- var(xa, na.rm=TRUE);  vb <- var(xb, na.rm=TRUE)
  } else {
    wa <- wts[group == 1L]; wb <- wts[group == 0L]
    ma <- weighted.mean(xa, wa, na.rm=TRUE)
    mb <- weighted.mean(xb, wb, na.rm=TRUE)
    va <- sum(wa * (xa - ma)^2, na.rm=TRUE) / sum(wa, na.rm=TRUE)
    vb <- sum(wb * (xb - mb)^2, na.rm=TRUE) / sum(wb, na.rm=TRUE)
  }
  denom <- sqrt((va + vb) / 2)
  if (is.na(denom) || denom == 0) return(NA_real_)
  (ma - mb) / denom
}

smd_vars <- c("age_at_first","sex","hiqual_dv","jbstat_bin","income_tercile_init",
              "gor_dv","birth_cohort_group","survey_origin")
smd_pre <- list(); smd_post <- list()
grp_vec <- mdf$in_analytical_sample

for (vn in smd_vars) {
  if (!vn %in% names(mdf)) next
  vv <- mdf[[vn]]
  if (is.factor(vv) || is.character(vv)) {
    lvls <- levels(as.factor(vv))
    for (lv in lvls) {
      ind <- as.integer(as.character(vv) == lv)
      key <- paste0(vn, "_", lv)
      smd_pre[[key]]  <- round(compute_smd_val(ind, grp_vec),              4)
      smd_post[[key]] <- round(compute_smd_val(ind, grp_vec, ipw_trimmed), 4)
    }
  } else {
    smd_pre[[vn]]  <- round(compute_smd_val(as.numeric(vv), grp_vec),              4)
    smd_post[[vn]] <- round(compute_smd_val(as.numeric(vv), grp_vec, ipw_trimmed), 4)
  }
}

smd_diagnostics <- list(
  pre_weight  = smd_pre,
  post_weight = smd_post,
  note = "SMD = (mean_analytical - mean_non_analytical) / sqrt((var_anal + var_other)/2). Post-weight uses trimmed IPW. Conventional balance threshold |SMD| < 0.1."
)

cohort_levels <- levels(mdf$birth_cohort_group)
prop_overlap_by_cohort <- setNames(lapply(cohort_levels, function(cg) {
  idx  <- as.character(mdf$birth_cohort_group) == cg
  p_a  <- propensity[idx & mdf$in_analytical_sample == 1L]
  p_b  <- propensity[idx & mdf$in_analytical_sample == 0L]
  bins <- seq(0, 1, by = 0.05)
  h_a  <- hist(p_a, breaks = bins, plot = FALSE)$counts
  h_b  <- hist(p_b, breaks = bins, plot = FALSE)$counts
  pos_warn <- length(p_a) > 0 && (mean(p_a < 0.1, na.rm=TRUE) > 0.7 ||
                                    mean(p_a > 0.9, na.rm=TRUE) > 0.7)
  list(
    n_analytical     = length(p_a),
    n_non_analytical = length(p_b),
    propensity_hist_analytical     = as.list(h_a),
    propensity_hist_non_analytical = as.list(h_b),
    summary_analytical = list(
      mean   = round(mean(p_a, na.rm=TRUE), 4),
      median = round(median(p_a, na.rm=TRUE), 4),
      q25    = round(quantile(p_a, 0.25, na.rm=TRUE)[[1]], 4),
      q75    = round(quantile(p_a, 0.75, na.rm=TRUE)[[1]], 4)
    ),
    summary_non_analytical = list(
      mean   = round(mean(p_b, na.rm=TRUE), 4),
      median = round(median(p_b, na.rm=TRUE), 4),
      q25    = round(quantile(p_b, 0.25, na.rm=TRUE)[[1]], 4),
      q75    = round(quantile(p_b, 0.75, na.rm=TRUE)[[1]], 4)
    ),
    positivity_warning = pos_warn
  )
}), cohort_levels)

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
# 10. Save diagnostics JSON
# ---------------------------------------------------------------------------
cat("Saving diagnostics JSON...\n")
result <- list(
  propensity_model = list(
    n_eligible      = nrow(mdf),
    n_analytical    = sum(mdf$in_analytical_sample),
    auc             = round(auc_val, 6),
    formula         = formula_str,
    coefficients    = coef_list,
    tercile_filter  = "fihhmngrs_dv >= 0 (zero-income included)",
    note_lw_variable = paste(
      "Base longitudinal weight fallback order: {wave}_indinub_lw (UKHLS c+, BHPS+GPS+EMBS)",
      "> {wave}_indin01_lw (BHPS-UK) > {wave}_indin91_lw (BHPS-GB).",
      "Wave ba has no longitudinal weight (cross-sectional only); lw_base=1 used for ba.",
      "'lwtresp' in task spec not present in data; adapted to actual variable names."
    )
  ),
  ipw_distribution = list(
    raw         = dist_stats(ipw_raw),
    trimmed     = dist_stats(ipw_trimmed),
    trim_bounds = list(lower = round(trim_lo, 4), upper = round(trim_hi, 4))
  ),
  effective_sample_size       = round(ess, 2),
  smd_diagnostics             = smd_diagnostics,
  propensity_overlap_by_cohort = prop_overlap_by_cohort,
  lwtresp_wave = "most_recent_available_per_individual_indinub_or_indin01"
)

write(toJSON(result, auto_unbox = TRUE, pretty = TRUE), OUT_PATH)
cat("Saved:", OUT_PATH, "\n")
cat("=== T1.13 complete ===\n")
