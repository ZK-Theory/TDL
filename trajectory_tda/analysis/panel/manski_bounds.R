# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Manski worst-case bounds on regime proportions and escape rates for permanent attritors

# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/manski_bounds.R

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
})

PROJ_ROOT   <- "C:/Users/steph/TDL"
WORKTREE    <- normalizePath(getwd(), mustWork = FALSE)
RESULTS_DIR <- file.path(PROJ_ROOT, "results/trajectory_tda_integration")
IPW_PATH    <- file.path(PROJ_ROOT, "results/panel_methodology/weights/ipw_diagnostics_2026-05-14.json")
XWAVEDAT    <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab")
OUT_DIR     <- file.path(WORKTREE, "results/panel_methodology/manski_bounds")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY    <- format(Sys.Date(), "%Y-%m-%d")
OUT_PATH <- file.path(OUT_DIR, paste0("regime_escape_bounds_", TODAY, ".json"))

cat("=== T1.15: Manski Bounds for Permanent Attritors ===\n")

# ---------------------------------------------------------------------------
# 1. Load analytical sample + regime labels
# ---------------------------------------------------------------------------
cat("Loading regime labels...\n")
anal05           <- fromJSON(file.path(RESULTS_DIR, "05_analysis.json"))
if (is.null(anal05$gmm_labels_pidp)) {
  stop("gmm_labels_pidp missing from 05_analysis.json; cannot match PIDs to regime labels.")
}
analytical_pidps <- as.integer(unlist(anal05$gmm_labels_pidp))
regime_labels    <- as.integer(unlist(anal05$gmm_labels))
n_analytical     <- length(regime_labels)
cat("n_analytical:", n_analytical, "\n")

# Regime counts
regime_tbl <- table(regime_labels)
cat("Regime table:\n"); print(regime_tbl)

# ---------------------------------------------------------------------------
# 2. Load n_eligible from IPW diagnostics
# ---------------------------------------------------------------------------
cat("Loading eligible population count...\n")
ipw       <- fromJSON(IPW_PATH)
n_eligible <- as.integer(ipw$propensity_model$n_eligible)
cat("n_eligible:", n_eligible, "\n")

n_attritors <- n_eligible - n_analytical
cat("n_attritors:", n_attritors, "(=", n_eligible, "-", n_analytical, ")\n")
stopifnot(n_attritors > 0)

# ---------------------------------------------------------------------------
# 3. Load birth year from xwavedat for working-age subset
# ---------------------------------------------------------------------------
cat("Loading birth year from xwavedat...\n")
xhdr    <- names(fread(XWAVEDAT, nrows=0L, sep="\t"))
x_cols  <- intersect(c("pidp", "birthy", "doby_dv"), xhdr)
xwave   <- fread(XWAVEDAT, sep="\t", select=x_cols)

# Use birthy as primary, doby_dv as fallback
if ("birthy" %in% names(xwave)) {
  xwave[, birth_year := as.integer(birthy)]
} else if ("doby_dv" %in% names(xwave)) {
  xwave[, birth_year := as.integer(doby_dv)]
} else {
  warning("Neither 'birthy' nor 'doby_dv' in xwave; birth_year set to NA.")
  xwave[, birth_year := NA_integer_]
}
xwave <- xwave[, .(pidp, birth_year)]

# For the analytical sample, we need pidp — load from 05_analysis.json or 01_trajectories.json
traj    <- fromJSON(file.path(RESULTS_DIR, "01_trajectories.json"))
pidp_dt <- data.table(pidp=as.integer(unlist(traj$metadata$pidp)),
                      regime=regime_labels)
pidp_dt <- merge(pidp_dt, xwave, by="pidp", all.x=TRUE)

cat("Birth year coverage:", sum(!is.na(pidp_dt$birth_year)), "/", nrow(pidp_dt), "\n")
if (!is.na(median(pidp_dt$birth_year, na.rm=TRUE)))
  cat("Birth year range:", range(pidp_dt$birth_year, na.rm=TRUE), "\n")

# Working-age definition: born 1945–1980 (in working age ≥16 for substantial part of 1991–2023)
# These cohorts are aged 11–46 in 1991 and 43–78 in 2023 — prime career-trajectory window
WORK_AGE_LO <- 1945L
WORK_AGE_HI <- 1980L
work_age_pidp_dt <- pidp_dt[!is.na(birth_year) & birth_year >= WORK_AGE_LO & birth_year <= WORK_AGE_HI]
cat("Working-age analytical n (born", WORK_AGE_LO, "-", WORK_AGE_HI, "):",
    nrow(work_age_pidp_dt), "\n")

# ---------------------------------------------------------------------------
# 4. Observed regime proportions and escape rates
# ---------------------------------------------------------------------------
cat("Computing observed proportions...\n")

# Disadvantaged regimes: R2 (employment trap) and R6 (long-term inactive)
DISADV_REGIMES <- c(2L, 6L)

obs_regime_props <- setNames(
  as.list(round(as.numeric(regime_tbl) / n_analytical, 4)),
  paste0("R", names(regime_tbl))
)

n_disadvantaged_obs   <- sum(regime_labels %in% DISADV_REGIMES)
n_non_disadvantaged   <- n_analytical - n_disadvantaged_obs
obs_escape_rate       <- round(n_non_disadvantaged / n_analytical, 4)
obs_R6_share          <- round(sum(regime_labels == 6L) / n_analytical, 4)
obs_R2_share          <- round(sum(regime_labels == 2L) / n_analytical, 4)
obs_R1_share          <- round(sum(regime_labels == 1L) / n_analytical, 4)
obs_disadv_share      <- round(n_disadvantaged_obs / n_analytical, 4)

# Working-age equivalents
n_wa             <- nrow(work_age_pidp_dt)
n_wa_disadv      <- sum(work_age_pidp_dt$regime %in% DISADV_REGIMES)
obs_escape_wa    <- round((n_wa - n_wa_disadv) / n_wa, 4)

cat("Observed escape rate (overall):", obs_escape_rate, "\n")
cat("Observed escape rate (working-age):", obs_escape_wa, "\n")
cat("Observed R2 share:", obs_R2_share, "\n")
cat("Observed R6 share:", obs_R6_share, "\n")
cat("Observed R1 share:", obs_R1_share, "\n")
cat("Observed disadvantaged share:", obs_disadv_share, "\n")

# ---------------------------------------------------------------------------
# 5. Pessimistic Manski bounds
# ---------------------------------------------------------------------------
# Scenario A: all attritors → R2 (employment trap)
# Scenario B: all attritors → R6 (long-term inactive)
# Worst-case for R2+R6 combined: all attritors → either R2 or R6
# For escape/R1 bounds: pessimistic lower bound = observed count / (analytical + attritors)
# (attritors contribute 0 escapers under worst case)

n_total <- n_analytical + n_attritors  # = n_eligible

# Upper bounds (share increases if attritors are all in that regime)
pess_R2_share_upper  <- round((sum(regime_labels == 2L) + n_attritors) / n_total, 4)
pess_R6_share_upper  <- round((sum(regime_labels == 6L) + n_attritors) / n_total, 4)
pess_disadv_upper    <- round((n_disadvantaged_obs    + n_attritors) / n_total, 4)

# Lower bounds (escape/R1 rates fall if attritors all fail to escape)
pess_escape_lower    <- round(n_non_disadvantaged / n_total, 4)
pess_R1_share_lower  <- round(sum(regime_labels == 1L) / n_total, 4)

# Working-age pessimistic escape: assume working-age attritors are proportionate to overall attritors
# Working-age fraction in analytical sample
wa_frac <- n_wa / n_analytical
n_attritors_wa <- round(n_attritors * wa_frac)  # estimated working-age attritors
n_wa_total     <- n_wa + n_attritors_wa
n_wa_escapers  <- n_wa - n_wa_disadv
pess_escape_wa_lower <- round(n_wa_escapers / n_wa_total, 4)

cat("\n--- Pessimistic Manski Bounds ---\n")
cat("Pessimistic R2 share upper:", pess_R2_share_upper,
    "(observed:", obs_R2_share, ")\n")
cat("Pessimistic R6 share upper:", pess_R6_share_upper,
    "(observed:", obs_R6_share, ")\n")
cat("Pessimistic disadvantaged share upper:", pess_disadv_upper,
    "(observed:", obs_disadv_share, ")\n")
cat("Pessimistic escape rate lower:", pess_escape_lower,
    "(observed:", obs_escape_rate, ")\n")
cat("Pessimistic R1 share lower:", pess_R1_share_lower,
    "(observed:", obs_R1_share, ")\n")
cat("Pessimistic working-age escape lower:", pess_escape_wa_lower,
    "(observed:", obs_escape_wa, ")\n")

# ---------------------------------------------------------------------------
# 6. Save JSON
# ---------------------------------------------------------------------------
cat("Saving Manski bounds JSON...\n")

result <- list(
  run_params = list(
    n_eligible  = n_eligible,
    n_analytical = n_analytical,
    n_attritors  = n_attritors,
    disadv_regimes = DISADV_REGIMES,
    working_age_definition = paste0("born ", WORK_AGE_LO, "–", WORK_AGE_HI),
    n_working_age_analytical = n_wa,
    source_05_analysis = "results/trajectory_tda_integration/05_analysis.json",
    source_ipw = "results/panel_methodology/weights/ipw_diagnostics_2026-05-14.json",
    paths_relative_to = "PROJ_ROOT (C:/Users/steph/TDL on this machine)"
  ),
  observed_regime_proportions = obs_regime_props,
  observed_summary = list(
    escape_rate_overall   = obs_escape_rate,
    escape_rate_workingage = obs_escape_wa,
    R1_share              = obs_R1_share,
    R2_share              = obs_R2_share,
    R6_share              = obs_R6_share,
    disadvantaged_share   = obs_disadv_share
  ),
  pessimistic_bounds = list(
    R6_share              = list(observed=obs_R6_share,   pessimistic_upper=pess_R6_share_upper),
    R2_share              = list(observed=obs_R2_share,   pessimistic_upper=pess_R2_share_upper),
    disadvantaged_share   = list(observed=obs_disadv_share, pessimistic_upper=pess_disadv_upper),
    escape_rate_overall   = list(observed=obs_escape_rate, pessimistic_lower=pess_escape_lower),
    R1_share              = list(observed=obs_R1_share,   pessimistic_lower=pess_R1_share_lower),
    escape_rate_workingage = list(observed=obs_escape_wa, pessimistic_lower=pess_escape_wa_lower,
                                   n_wa_attritors_estimated=n_attritors_wa)
  ),
  rationale_pessimistic_allocation = paste0(
    "Permanent attritors are individuals who entered the BHPS/USoc frame (>=1 valid jbstat) ",
    "but did not complete the 10-wave threshold required for trajectory inclusion. ",
    "These individuals are more likely to face labour-market instability, long-term inactivity, ",
    "or ill-health — the defining features of regimes R2 (employment trap) and R6 (long-term inactive). ",
    "Allocating all n=", n_attritors, " attritors to R2 or R6 under the Manski worst-case assumption ",
    "yields conservative upper bounds on disadvantaged-regime shares and lower bounds on escape rates. ",
    "These are not expected values but the worst-case counterfactuals under maximum informative attrition."
  )
)

write(toJSON(result, auto_unbox=TRUE, pretty=TRUE), OUT_PATH)
cat("Saved:", OUT_PATH, "\n")
cat("=== T1.15 complete ===\n")
