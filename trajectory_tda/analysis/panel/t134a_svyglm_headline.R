# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Promote the stable MICE-pooled survey GLM column to the Tier-2
# escape-regression headline after the weighted household-RE fits were found
# non-estimable on the singleton-dominated household structure.
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/t134a_svyglm_headline.R

suppressPackageStartupMessages({
  library(jsonlite)
})

PROJ_ROOT <- Sys.getenv("TDL_PROJ_ROOT", "C:/Users/steph/TDL")
WORKTREE <- normalizePath(getwd(), mustWork = TRUE)
OUT_DIR <- file.path(WORKTREE, "results/panel_methodology/regression")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY <- format(Sys.Date(), "%Y-%m-%d")
OUT_LABEL <- Sys.getenv("T134A_OUT_LABEL", "")
OUT_SUFFIX <- if (nzchar(OUT_LABEL)) paste0(OUT_LABEL, "_", TODAY) else TODAY
OUT_PATH <- file.path(OUT_DIR, paste0("tier2_svyglm_headline_", OUT_SUFFIX, ".json"))
if (file.exists(OUT_PATH)) {
  stop("Refusing to overwrite existing result: ", OUT_PATH)
}

TIER2_SOURCE <- file.path(OUT_DIR, "tier2_ipw_mice_svyglm_2026-06-03.json")
DIAG_SOURCE <- file.path(OUT_DIR, "tier2_weight_diagnostic_2026-06-03.json")
WEMIX_SOURCE <- file.path(OUT_DIR, "tier2_wemix_feasibility_2026-06-03.json")
BASELINE_SOURCE <- file.path(OUT_DIR, "tier2_glmm_firth_2026-05-14.json")

required <- c(TIER2_SOURCE, DIAG_SOURCE, WEMIX_SOURCE, BASELINE_SOURCE)
missing <- required[!file.exists(required)]
if (length(missing) > 0L) {
  stop("Missing required source artifact(s): ", paste(missing, collapse = ", "))
}

iso_now <- function() {
  format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ")
}

as_row <- function(row) {
  level <- row$level
  if (is.null(level) || length(level) == 0L || is.na(level) || !nzchar(as.character(level))) {
    level <- NA_character_
  } else {
    level <- as.character(level)[1L]
  }
  list(
    name = row$name,
    level = level,
    estimate = row$svyglm_estimate,
    cluster_robust_se = row$svyglm_se,
    pvalue = row$svyglm_pvalue,
    rubin_df = row$glmm_rubin_df,
    rubin_fmi = row$glmm_rubin_fmi
  )
}

baseline_direction <- function(baseline, term) {
  rows <- baseline$coefficient_table
  hit <- Filter(function(x) identical(x$term, term), rows)
  if (length(hit) != 1L) return(NA_real_)
  sign(hit[[1L]]$estimate)
}

tier2 <- fromJSON(TIER2_SOURCE, simplifyVector = FALSE)
diag <- fromJSON(DIAG_SOURCE, simplifyVector = FALSE)
wemix <- fromJSON(WEMIX_SOURCE, simplifyVector = FALSE)
baseline <- fromJSON(BASELINE_SOURCE, simplifyVector = FALSE)

headline_rows <- lapply(tier2$coefficients, as_row)
regime <- Filter(function(x) identical(x$name, "regime_initR6"), headline_rows)
nssec_m <- Filter(function(x) identical(x$name, "nssec_proxyM"), headline_rows)
nssec_l <- Filter(function(x) identical(x$name, "nssec_proxyL"), headline_rows)
if (length(regime) != 1L || length(nssec_m) != 1L || length(nssec_l) != 1L) {
  stop("Required headline coefficient row is missing.")
}

dir_m <- baseline_direction(baseline, "nssec_proxyM")
dir_l <- baseline_direction(baseline, "nssec_proxyL")
if (is.na(dir_m) || is.na(dir_l)) {
  stop("Baseline missing required NS-SEC terms: nssec_proxyM/nssec_proxyL")
}
nssec_consistent <- (
  sign(nssec_m[[1L]]$estimate) == dir_m &&
    sign(nssec_l[[1L]]$estimate) == dir_l
)

payload <- list(
  schema_version = "panel-output/tier2-svyglm-headline/v1",
  generated_at = iso_now(),
  task = "T1.34a svyglm headline (Option A fallback)",
  pre_registration = "2026-06-03 resolution amendment: weighted household random-effect variance non-estimable; design-based svyglm promoted to headline",
  params = list(
    m_imputations = tier2$params$m_imputations,
    engine_headline = "survey::svyglm",
    family = "quasibinomial",
    design_ids = "~foo_cluster",
    ipw_source = tier2$params$ipw_source,
    ipw_trimming = "p1/p99 of raw, per-stratum normalisation to mean 1",
    model_formula_fixed = tier2$params$model_formula_fixed,
    conditioning_sample = tier2$params$conditioning_sample,
    escape_definition_source = tier2$params$escape_definition_source,
    seed = 42L,
    n_obs = tier2$params$n_obs,
    n_clusters = tier2$params$n_clusters_foo,
    source_pooled_output = TIER2_SOURCE,
    source_weight_diagnostic = DIAG_SOURCE
  ),
  convergence = tier2$convergence,
  svyglm_headline = headline_rows,
  unweighted_glmm_companion = list(
    regime_init_r6_logor = diag$glmm_unweighted$regime_initR6,
    sigma_u_hh = diag$glmm_unweighted$sigma_u,
    icc_hh = diag$glmm_unweighted$icc,
    coefficients = list(
      list(name = "regime_initR6", level = "R6", estimate = diag$glmm_unweighted$regime_initR6, se = NA_real_, pvalue = NA_real_),
      list(name = "nssec_proxyM", level = "M", estimate = diag$glmm_unweighted$nssec_proxyM, se = NA_real_, pvalue = NA_real_),
      list(name = "nssec_proxyL", level = "L", estimate = diag$glmm_unweighted$nssec_proxyL, se = NA_real_, pvalue = NA_real_)
    ),
    note = "Unweighted diagnostic companion from first completed NS-SEC imputation; not the IPW-adjusted headline."
  ),
  household_variance_estimability = list(
    weighted_household_variance_estimable = FALSE,
    rationale = sprintf(
      "Weighted household random-effect variance is not reliably estimable on the singleton-dominated household structure (%s households / %s individuals in the Tier-2 model frame).",
      format(tier2$params$n_clusters_hh, big.mark = ","),
      format(tier2$params$n_obs, big.mark = ",")
    ),
    evidence = list(
      sprintf("Weighted glmmTMB diagnostic diverged to sigma_u=%.4f and ICC=%.4f.", diag$glmm_weighted$sigma_u, diag$glmm_weighted$icc),
      sprintf("WeMix bounded smoke failed with error: %s", wemix$bounded_fit$error),
      sprintf("Full first-imputation WeMix smoke was censored after %.1f seconds without completing.", wemix$params$full_single_imputation_censored_seconds)
    )
  ),
  acceptance = list(
    regime6_or_gt_1 = exp(regime[[1L]]$estimate) > 1,
    nssec_direction_consistent_with_t120 = nssec_consistent,
    accepted = (exp(regime[[1L]]$estimate) > 1) && nssec_consistent,
    t120_baseline_source = BASELINE_SOURCE,
    t120_nssec_proxyM_sign = dir_m,
    t120_nssec_proxyL_sign = dir_l
  )
)

write(toJSON(payload, auto_unbox = TRUE, pretty = TRUE, na = "null"), OUT_PATH)
cat("Saved ", OUT_PATH, "\n", sep = "")
