# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Feasibility-gated survey pseudo-likelihood mixed-model smoke test
# for the Tier-2 escape headline. This script intentionally runs a bounded
# WeMix diagnostic before any full m=20 pooled refit is attempted.
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/t134a_wemix_feasibility.R

Sys.setenv(
  OMP_NUM_THREADS = Sys.getenv("OMP_NUM_THREADS", "1"),
  OPENBLAS_NUM_THREADS = Sys.getenv("OPENBLAS_NUM_THREADS", "1"),
  MKL_NUM_THREADS = Sys.getenv("MKL_NUM_THREADS", "1"),
  VECLIB_MAXIMUM_THREADS = Sys.getenv("VECLIB_MAXIMUM_THREADS", "1")
)

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
  library(mice)
})

set.seed(42L)
setDTthreads(as.integer(Sys.getenv("T134_DATATABLE_THREADS", "1")))

PROJ_ROOT <- Sys.getenv("TDL_PROJ_ROOT", "C:/Users/steph/TDL")
WORKTREE <- normalizePath(getwd(), mustWork = TRUE)
OUT_DIR <- file.path(WORKTREE, "results/panel_methodology/regression")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY <- format(Sys.Date(), "%Y-%m-%d")
ESCAPE_PATH <- file.path(PROJ_ROOT, "results/trajectory_tda_priority2/window_escape_assignments_2026-05-14.json")
IPW_PATH <- file.path(PROJ_ROOT, "results/panel_methodology/weights/ipw_individual_weights_2026-05-14.rds")
MICE_PATH <- file.path(PROJ_ROOT, "results/panel_methodology/imputation/nssec_mids_2026-05-25.rds")
XWAVEDAT <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab")
DATA_TAB <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab")
BHPS_DIR <- file.path(DATA_TAB, "bhps")
UKHLS_DIR <- file.path(DATA_TAB, "ukhls")

OUT_LABEL <- Sys.getenv("T134_WEMIX_OUT_LABEL", "")
OUT_STEM <- if (nzchar(OUT_LABEL)) {
  paste0("tier2_wemix_feasibility_", OUT_LABEL, "_")
} else {
  "tier2_wemix_feasibility_"
}
OUT_PATH <- file.path(OUT_DIR, paste0(OUT_STEM, TODAY, ".json"))
if (file.exists(OUT_PATH)) {
  stop("Refusing to overwrite existing result: ", OUT_PATH)
}

MAX_HH <- as.integer(Sys.getenv("T134_WEMIX_BOUNDED_MAX_HH", "300"))
NQUAD <- as.integer(Sys.getenv("T134_WEMIX_NQUAD", "3"))
MAX_ITERATION <- as.integer(Sys.getenv("T134_WEMIX_MAX_ITERATION", "3"))
FULL_RUN_CENSORED_SECONDS <- as.numeric(Sys.getenv("T134_WEMIX_FULL_CENSORED_SECONDS", "4001.4"))
FULL_RUN_CENSORED_COMPLETED <- Sys.getenv("T134_WEMIX_FULL_CENSORED_COMPLETED", "0") == "1"

BHPS_WAVES <- paste0("b", letters[1:18])
BHPS_YEARS <- 1991:2008
UKHLS_WAVES <- letters[1:15]
UKHLS_YEARS <- 2009:2023

iso_now <- function() {
  format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ")
}

birth_cohort_of <- function(birth_year) {
  fcase(
    birth_year < 1950, "pre-1950",
    birth_year >= 1950 & birth_year < 1960, "1950s",
    birth_year >= 1960 & birth_year < 1970, "1960s",
    birth_year >= 1970 & birth_year < 1980, "1970s",
    birth_year >= 1980, "post-1980",
    default = NA_character_
  )
}

load_first_wave <- function(dir_path, waves, wave_years, target_pidps) {
  first_dt <- data.table(
    pidp = integer(0), gor_dv = integer(0), hidp = integer(0),
    wave = character(0), wave_year = integer(0), survey_origin = character(0)
  )
  seen_first <- integer(0)
  for (wi in seq_along(waves)) {
    wave <- waves[wi]
    fpath <- file.path(dir_path, paste0(wave, "_indresp.tab"))
    if (!file.exists(fpath)) next
    hdr <- names(fread(fpath, nrows = 0L, sep = "\t"))
    hidp_col <- paste0(wave, "_hidp")
    gor_col <- paste0(wave, "_gor_dv")
    if (!hidp_col %in% hdr) next
    select_cols <- intersect(c("pidp", hidp_col, gor_col), hdr)
    wdt <- fread(fpath, sep = "\t", select = select_cols)
    wdt <- wdt[pidp %in% target_pidps]
    if (nrow(wdt) == 0L) next
    setnames(wdt, hidp_col, "hidp", skip_absent = TRUE)
    setnames(wdt, gor_col, "gor_dv", skip_absent = TRUE)
    wdt[, wave := wave]
    wdt[, wave_year := wave_years[wi]]
    wdt[, survey_origin := fifelse(wave %in% BHPS_WAVES, "BHPS", "UKHLS")]
    new_pidps <- setdiff(wdt$pidp, seen_first)
    if (length(new_pidps) > 0L) {
      first_dt <- rbindlist(list(first_dt, wdt[pidp %in% new_pidps]), fill = TRUE)
      seen_first <- c(seen_first, new_pidps)
    }
  }
  setorder(first_dt, pidp, wave_year)
  first_dt[, .SD[1L], by = pidp]
}

required_packages <- c("WeMix", "survey", "glmmTMB")
package_available <- setNames(
  vapply(required_packages, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1)),
  required_packages
)
if (!package_available["WeMix"]) {
  stop("WeMix is not available; install it before running the feasibility smoke.")
}

cat("Loading Tier-2 first-imputation model frame...\n")
wa <- as.data.table(fromJSON(ESCAPE_PATH)$assignments)
xwave <- fread(XWAVEDAT, sep = "\t", select = c("pidp", "birthy", "sex_dv"))
xwave[, birthy := as.integer(birthy)]
xwave[birthy <= 1900 | birthy > 2005, birthy := NA_integer_]
xwave[, birth_cohort := birth_cohort_of(birthy)]
xwave[, sex := fifelse(as.integer(sex_dv) == 2L, "female", fifelse(as.integer(sex_dv) == 1L, "male", NA_character_))]

target_pidps <- as.integer(wa$pidp)
first_cov <- rbindlist(list(
  load_first_wave(BHPS_DIR, BHPS_WAVES, BHPS_YEARS, target_pidps),
  load_first_wave(UKHLS_DIR, UKHLS_WAVES, UKHLS_YEARS, target_pidps)
), fill = TRUE)
setorder(first_cov, pidp, wave_year)
first_cov <- first_cov[, .SD[1L], by = pidp]
first_cov[gor_dv <= 0, gor_dv := NA_integer_]
first_cov[, hh_group := paste0(survey_origin, "_", hidp)]

ipw <- as.data.table(readRDS(IPW_PATH))
ipw[, analytical_status := ifelse(in_analytical_sample == 1L, "analytical", "non_analytical")]
ipw[, ipw_norm := ipw_trimmed * .N / sum(ipw_trimmed), by = analytical_status]

mice_saved <- readRDS(MICE_PATH)
comp <- as.data.table(complete(mice_saved$mids, 1L))
nssec <- data.table(
  pidp = as.integer(mice_saved$pidps),
  nssec_proxy = factor(comp$nssec_proxy, levels = 1:3, labels = c("H", "M", "L"))
)

dt <- merge(wa, xwave[, .(pidp, birth_cohort, sex)], by = "pidp", all.x = TRUE)
dt <- merge(dt, first_cov[, .(pidp, gor_dv, hh_group)], by = "pidp", all.x = TRUE)
dt <- merge(dt, ipw[, .(pidp, ipw_trimmed, ipw_norm, in_analytical_sample)], by = "pidp", all.x = TRUE)
dt <- merge(dt, nssec, by = "pidp", all.x = TRUE)
dt <- dt[first_window_regime %in% c(2L, 6L)]
dt[, regime_init := factor(paste0("R", first_window_regime), levels = c("R2", "R6"))]
dt[, region := factor(gor_dv)]
dt[, sex := factor(sex, levels = c("male", "female"))]
dt[, birth_cohort := factor(birth_cohort, levels = c("pre-1950", "1950s", "1960s", "1970s", "post-1980"))]
dt[, hh_group := factor(hh_group)]

full_fit_dt <- dt[complete.cases(
  escape, regime_init, nssec_proxy, birth_cohort, sex, region,
  hh_group, ipw_norm, ipw_trimmed
)]
full_fit_dt[, ipw_model := ipw_trimmed * .N / sum(ipw_trimmed)]
full_fit_dt[, hh_weight := 1]

set.seed(42L)
eligible_hh <- unique(as.character(full_fit_dt$hh_group))
esc_hh <- unique(as.character(full_fit_dt[escape == 1L]$hh_group))
non_hh <- setdiff(eligible_hh, esc_hh)
n_esc_hh <- min(length(esc_hh), ceiling(MAX_HH / 2))
n_non_hh <- min(length(non_hh), MAX_HH - n_esc_hh)
chosen_hh <- c(
  sample(esc_hh, size = n_esc_hh, replace = FALSE),
  sample(non_hh, size = n_non_hh, replace = FALSE)
)
bounded_dt <- full_fit_dt[as.character(hh_group) %in% chosen_hh]
bounded_dt[, ipw_model := ipw_trimmed * .N / sum(ipw_trimmed)]
bounded_dt[, hh_weight := 1]
bounded_df <- as.data.frame(bounded_dt[, .(
  escape, regime_init, nssec_proxy, birth_cohort, sex, region,
  hh_group, ipw_model, hh_weight
)])

cat(
  "Bounded WeMix fit: n=", nrow(bounded_df),
  " hh=", length(unique(bounded_df$hh_group)),
  " nQuad=", NQUAD,
  " max_iteration=", MAX_ITERATION,
  "\n",
  sep = ""
)

warnings_fit <- character(0)
start_time <- Sys.time()
fit_error <- NULL
fit <- tryCatch(
  withCallingHandlers(
    WeMix::mix(
      escape ~ regime_init + nssec_proxy + birth_cohort + sex + region + (1 | hh_group),
      data = bounded_df,
      weights = c("ipw_model", "hh_weight"),
      cWeights = FALSE,
      nQuad = NQUAD,
      max_iteration = MAX_ITERATION,
      family = binomial()
    ),
    warning = function(w) {
      warnings_fit <<- c(warnings_fit, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  ),
  error = function(e) {
    fit_error <<- conditionMessage(e)
    NULL
  }
)
elapsed_seconds <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))

if (is.null(fit)) {
  regime_log_or <- NA_real_
  nssec_l_log_or <- NA_real_
  sigma2_hh <- NA_real_
  icc_hh <- NA_real_
} else {
  coef_vec <- fit$coef
  vars <- fit$vars
  icc <- fit$ICC
  regime_log_or <- as.numeric(coef_vec["regime_initR6"])
  nssec_l_log_or <- as.numeric(coef_vec["nssec_proxyL"])
  sigma2_hh <- if (length(vars) > 0L) as.numeric(vars[1L]) else NA_real_
  icc_hh <- if (length(icc) > 0L) as.numeric(icc[1L]) else NA_real_
}

scale_ratio <- uniqueN(full_fit_dt$hh_group) / max(1L, uniqueN(bounded_dt$hh_group))
linear_seconds <- elapsed_seconds * scale_ratio
quadratic_seconds <- elapsed_seconds * scale_ratio^2
parallel_workers <- 4L

payload <- list(
  schema_version = "panel-output/tier2-wemix-feasibility/v1",
  generated_at = iso_now(),
  task = "T1.34a-redo Phase 1 WeMix feasibility",
  params = list(
    seed = 42L,
    estimator = "WeMix::mix",
    family = "binomial",
    formula = "escape ~ regime_init + nssec_proxy + birth_cohort + sex + region + (1 | hh_group)",
    weights = c("ipw_model", "hh_weight"),
    weight_threading = "level-1 ipw_model is T1.13 p1/p99 trimmed IPW renormalised to mean 1 in the model frame; level-2 hh_weight is 1 for every household because no household-level survey weight is available",
    cWeights = FALSE,
    nQuad = NQUAD,
    max_iteration = MAX_ITERATION,
    bounded_max_households = MAX_HH,
    full_single_imputation_censored_seconds = FULL_RUN_CENSORED_SECONDS,
    full_single_imputation_censored_completed = FULL_RUN_CENSORED_COMPLETED
  ),
  package_available = as.list(package_available),
  sample = list(
    full_first_imputation_n_obs = as.integer(nrow(full_fit_dt)),
    full_first_imputation_n_households = as.integer(uniqueN(full_fit_dt$hh_group)),
    bounded_n_obs = as.integer(nrow(bounded_dt)),
    bounded_n_households = as.integer(uniqueN(bounded_dt$hh_group)),
    bounded_mean_weight = round(mean(bounded_dt$ipw_model), 8)
  ),
  bounded_fit = list(
    status = if (is.null(fit)) "failed" else "completed",
    error = fit_error,
    elapsed_seconds = round(elapsed_seconds, 3),
    sigma2_hh = round(sigma2_hh, 8),
    icc_hh = round(icc_hh, 8),
    regime_initR6_log_or = round(regime_log_or, 8),
    regime_initR6_or = round(exp(regime_log_or), 8),
    nssec_proxyL_log_or = round(nssec_l_log_or, 8),
    nssec_proxyL_direction = if (is.na(nssec_l_log_or)) "missing" else if (nssec_l_log_or > 0) "positive" else if (nssec_l_log_or < 0) "negative" else "zero",
    warnings = as.list(unique(warnings_fit))
  ),
  full_run_estimate = list(
    basis = "bounded elapsed scaling plus censored failed full-sample smoke evidence",
    bounded_linear_seconds_per_imputation = round(linear_seconds, 1),
    bounded_quadratic_seconds_per_imputation = round(quadratic_seconds, 1),
    observed_full_smoke_lower_bound_seconds_per_imputation = FULL_RUN_CENSORED_SECONDS,
    serial_m20_lower_bound_hours = round((FULL_RUN_CENSORED_SECONDS * 20) / 3600, 2),
    four_worker_m20_lower_bound_hours = round((FULL_RUN_CENSORED_SECONDS * ceiling(20 / parallel_workers)) / 3600, 2),
    feasibility_conclusion = "Full-sample WeMix is installable and weight-threading is specified, but one full single-imputation smoke did not finish after the censored wall-time lower bound; Manager should decide whether this estimator remains feasible before any m=20 run."
  ),
  proposed_output_json_field_set = list(
    "schema_version",
    "generated_at",
    "task",
    "pre_registration",
    "params",
    "package_versions",
    "sample",
    "mice_convergence",
    "parallelization",
    "coefficients",
    "random_effects",
    "model_fit",
    "acceptance_gate",
    "fallback_if_failed"
  )
)

write(toJSON(payload, auto_unbox = TRUE, pretty = TRUE, na = "null"), OUT_PATH)
cat("Saved ", OUT_PATH, "\n", sep = "")
