# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: T1.15 supplement — conditional escape rate Manski bounds from window-based figures.
#
# All base figures read directly from results/trajectory_tda_priority2/p2_5_age_stratified.json.
# No window analysis or GMM prediction is re-run here — this is purely arithmetic.
#
# Computes two bound types:
#   full_pessimism   — all attritors are R2/R6 starters who fail to escape
#   partial_pessimism — attritors enter R2/R6 at the same rate as the analytical sample
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/manski_bounds_conditional.R

suppressPackageStartupMessages(library(jsonlite))

PROJ_ROOT  <- "C:/Users/steph/TDL"
WORKTREE   <- normalizePath(getwd(), mustWork = FALSE)
P25_PATH   <- file.path(PROJ_ROOT, "results/trajectory_tda_priority2/p2_5_age_stratified.json")
IPW_PATH   <- file.path(PROJ_ROOT, "results/panel_methodology/weights/ipw_diagnostics_2026-05-13.json")
ANAL05     <- file.path(PROJ_ROOT, "results/trajectory_tda_integration/05_analysis.json")
OUT_DIR    <- file.path(WORKTREE, "results/panel_methodology/manski_bounds")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY    <- format(Sys.Date(), "%Y-%m-%d")
OUT_PATH <- file.path(OUT_DIR, paste0("regime_escape_bounds_conditional_", TODAY, ".json"))

cat("=== T1.15 Supplement: Conditional Escape Rate Manski Bounds (window-based) ===\n")

# ---------------------------------------------------------------------------
# 1. Load base figures from p2_5_age_stratified.json
# ---------------------------------------------------------------------------
cat("Loading p2_5_age_stratified.json...\n")
p25 <- fromJSON(P25_PATH)

n_starters_overall  <- as.integer(p25$escape_rates$overall$n_starting_disadvantaged)
n_escaped_overall   <- as.integer(p25$escape_rates$overall$n_ever_escape)
obs_rate_overall    <- p25$escape_rates$overall$ever_escape_rate

n_starters_wa       <- as.integer(p25$escape_rates$working_age$n_starting_disadvantaged)
n_escaped_wa        <- as.integer(p25$escape_rates$working_age$n_ever_escape)
obs_rate_wa         <- p25$escape_rates$working_age$ever_escape_rate

cat("Overall:     n_starters=", n_starters_overall, " n_escaped=", n_escaped_overall,
    " rate=", round(obs_rate_overall * 100, 2), "%\n")
cat("Working-age: n_starters=", n_starters_wa, " n_escaped=", n_escaped_wa,
    " rate=", round(obs_rate_wa * 100, 2), "%\n")

# ---------------------------------------------------------------------------
# 2. Load n_eligible and n_analytical
# ---------------------------------------------------------------------------
cat("Loading IPW diagnostics...\n")
ipw         <- fromJSON(IPW_PATH)
n_eligible  <- as.integer(ipw$propensity_model$n_eligible)

cat("Loading analytical sample size...\n")
anal05      <- fromJSON(ANAL05)
n_analytical <- length(unlist(anal05$gmm_labels))

n_attritors <- n_eligible - n_analytical
cat("n_eligible=", n_eligible, " n_analytical=", n_analytical, " n_attritors=", n_attritors, "\n")

# ---------------------------------------------------------------------------
# 3. Full-pessimism bounds (all attritors are R2/R6 non-escapers)
# ---------------------------------------------------------------------------
fp_n_starters_overall <- n_starters_overall + n_attritors
fp_rate_overall       <- round(n_escaped_overall / fp_n_starters_overall, 6)

fp_n_starters_wa      <- n_starters_wa + n_attritors
fp_rate_wa            <- round(n_escaped_wa / fp_n_starters_wa, 6)

cat("\nFull pessimism:\n")
cat("  Overall:     n_starters_pessimistic=", fp_n_starters_overall,
    " lower_bound=", round(fp_rate_overall * 100, 3), "%\n")
cat("  Working-age: n_starters_pessimistic=", fp_n_starters_wa,
    " lower_bound=", round(fp_rate_wa * 100, 3), "%\n")

# ---------------------------------------------------------------------------
# 4. Partial-pessimism bounds (attritors enter R2/R6 proportionally)
# ---------------------------------------------------------------------------
prop_r2r6_overall <- n_starters_overall / n_analytical
n_attritors_r2r6  <- round(n_attritors * prop_r2r6_overall)
pp_n_starters_overall <- n_starters_overall + n_attritors_r2r6
pp_rate_overall       <- round(n_escaped_overall / pp_n_starters_overall, 6)

prop_wa           <- n_starters_wa / n_analytical
n_attritors_wa    <- round(n_attritors * prop_wa)
pp_n_starters_wa  <- n_starters_wa + n_attritors_wa
pp_rate_wa        <- round(n_escaped_wa / pp_n_starters_wa, 6)

cat("\nPartial pessimism:\n")
cat("  Overall:     prop_r2r6=", round(prop_r2r6_overall, 4),
    " n_attritors_r2r6=", n_attritors_r2r6,
    " lower_bound=", round(pp_rate_overall * 100, 3), "%\n")
cat("  Working-age: prop_wa=", round(prop_wa, 4),
    " n_attritors_wa=", n_attritors_wa,
    " lower_bound=", round(pp_rate_wa * 100, 3), "%\n")

# ---------------------------------------------------------------------------
# 5. Save JSON
# ---------------------------------------------------------------------------
cat("\nSaving conditional Manski bounds JSON...\n")

result <- list(
  run_params = list(
    date              = TODAY,
    source_p25        = P25_PATH,
    source_ipw        = IPW_PATH,
    source_anal05     = ANAL05,
    method            = "Window-based escape rates from p2_5_age_stratified.json; no GMM re-run",
    window_definition = "10-year overlapping windows (step=5); R2/R6 first-window starters"
  ),
  base_figures = list(
    overall = list(
      n_starting_disadvantaged = n_starters_overall,
      n_ever_escape            = n_escaped_overall,
      observed_escape_rate     = obs_rate_overall
    ),
    working_age = list(
      n_starting_disadvantaged = n_starters_wa,
      n_ever_escape            = n_escaped_wa,
      observed_escape_rate     = obs_rate_wa
    )
  ),
  attritor_counts = list(
    n_eligible   = n_eligible,
    n_analytical = n_analytical,
    n_attritors  = n_attritors
  ),
  full_pessimism = list(
    description = "All attritors are assumed to be R2/R6 starters who fail to escape",
    overall = list(
      n_starters_pessimistic = fp_n_starters_overall,
      pessimistic_lower_escape_rate = fp_rate_overall
    ),
    working_age = list(
      n_starters_pessimistic = fp_n_starters_wa,
      pessimistic_lower_escape_rate = fp_rate_wa
    )
  ),
  partial_pessimism = list(
    description = paste0(
      "Attritors enter R2/R6 at the same rate as the analytical sample (",
      round(prop_r2r6_overall * 100, 1), "% overall, ",
      round(prop_wa * 100, 1), "% working-age)"
    ),
    overall = list(
      prop_r2r6_in_analytical  = round(prop_r2r6_overall, 6),
      n_attritors_r2r6         = as.integer(n_attritors_r2r6),
      n_starters_partial       = as.integer(pp_n_starters_overall),
      partial_lower_escape_rate = pp_rate_overall
    ),
    working_age = list(
      prop_wa_in_analytical    = round(prop_wa, 6),
      n_attritors_wa           = as.integer(n_attritors_wa),
      n_starters_partial       = as.integer(pp_n_starters_wa),
      partial_lower_escape_rate = pp_rate_wa
    )
  ),
  rationale = paste0(
    "Manski worst-case bounds assess the impact of permanent attrition on the escape-rate estimate. ",
    "Under full pessimism, all ", n_attritors, " permanent attritors (eligible but not in analytical sample) ",
    "are assumed to have been R2/R6 starters who failed to escape. Under partial pessimism, attritors ",
    "are allocated to R2/R6 in proportion to their prevalence in the analytical sample. ",
    "Both bounds bracket the true escape rate; the observed 5.6% lies above both bounds. ",
    "Attritors who cannot complete 10 waves are more likely to face persistent labour-market ",
    "instability (consistent with R2/R6 membership), making the full-pessimism allocation ",
    "the methodologically conservative worst case."
  )
)

write(toJSON(result, auto_unbox = TRUE, pretty = TRUE), OUT_PATH)
cat("Saved:", OUT_PATH, "\n")
cat("=== T1.15 Supplement complete ===\n")
