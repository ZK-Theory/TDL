# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Diagnostic-only comparison for T1.34 Tier-2 weighting behaviour.

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
  library(mice)
  library(glmmTMB)
})

PROJ_ROOT <- "C:/Users/steph/TDL"
WORKTREE <- normalizePath(getwd(), mustWork = TRUE)
ESCAPE_PATH <- file.path(PROJ_ROOT, "results/trajectory_tda_priority2/window_escape_assignments_2026-05-14.json")
IPW_PATH <- file.path(PROJ_ROOT, "results/panel_methodology/weights/ipw_individual_weights_2026-05-14.rds")
MICE_PATH <- file.path(PROJ_ROOT, "results/panel_methodology/imputation/nssec_mids_2026-05-25.rds")
FOO_PATH <- file.path(PROJ_ROOT, "data/derived/foo_clusters_2026-05-06.csv")
XWAVEDAT <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab")
DATA_TAB <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab")
BHPS_DIR <- file.path(DATA_TAB, "bhps")
UKHLS_DIR <- file.path(DATA_TAB, "ukhls")
OUT_DIR <- file.path(WORKTREE, "results/panel_methodology/regression")
OUT_PATH <- file.path(OUT_DIR, paste0("tier2_weight_diagnostic_", format(Sys.Date(), "%Y-%m-%d"), ".json"))
if (file.exists(OUT_PATH)) stop("Refusing to overwrite existing diagnostic: ", OUT_PATH)

BHPS_WAVES <- paste0("b", letters[1:18])
BHPS_YEARS <- 1991:2008
UKHLS_WAVES <- letters[1:15]
UKHLS_YEARS <- 2009:2023

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
  first_dt <- data.table(pidp = integer(0), gor_dv = integer(0), hidp = integer(0), wave_year = integer(0), survey_origin = character(0))
  seen_first <- integer(0)
  for (wi in seq_along(waves)) {
    wave <- waves[wi]
    fpath <- file.path(dir_path, paste0(wave, "_indresp.tab"))
    if (!file.exists(fpath)) next
    hdr <- names(fread(fpath, nrows = 0L, sep = "\t"))
    hidp_col <- paste0(wave, "_hidp")
    gor_col <- paste0(wave, "_gor_dv")
    if (!hidp_col %in% hdr) next
    wdt <- fread(fpath, sep = "\t", select = intersect(c("pidp", hidp_col, gor_col), hdr))
    wdt <- wdt[pidp %in% target_pidps]
    if (nrow(wdt) == 0L) next
    setnames(wdt, hidp_col, "hidp", skip_absent = TRUE)
    setnames(wdt, gor_col, "gor_dv", skip_absent = TRUE)
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

wa <- as.data.table(fromJSON(ESCAPE_PATH)$assignments)
xwave <- fread(XWAVEDAT, sep = "\t", select = c("pidp", "birthy", "sex_dv"))
xwave[, birthy := as.integer(birthy)]
xwave[birthy <= 1900 | birthy > 2005, birthy := NA_integer_]
xwave[, birth_cohort := birth_cohort_of(birthy)]
xwave[, sex := fifelse(as.integer(sex_dv) == 2L, "female", fifelse(as.integer(sex_dv) == 1L, "male", NA_character_))]
first_cov <- rbindlist(list(
  load_first_wave(BHPS_DIR, BHPS_WAVES, BHPS_YEARS, wa$pidp),
  load_first_wave(UKHLS_DIR, UKHLS_WAVES, UKHLS_YEARS, wa$pidp)
), fill = TRUE)
setorder(first_cov, pidp, wave_year)
first_cov <- first_cov[, .SD[1L], by = pidp]
first_cov[gor_dv <= 0, gor_dv := NA_integer_]
first_cov[, hh_group := paste0(survey_origin, "_", hidp)]

foo <- fread(FOO_PATH)
ipw <- as.data.table(readRDS(IPW_PATH))
mice_saved <- readRDS(MICE_PATH)
comp <- as.data.table(complete(mice_saved$mids, 1L))
nssec <- data.table(pidp = as.integer(mice_saved$pidps), nssec_proxy = factor(comp$nssec_proxy, levels = 1:3, labels = c("H", "M", "L")))

dt <- merge(wa, xwave[, .(pidp, birth_cohort, sex)], by = "pidp", all.x = TRUE)
dt <- merge(dt, first_cov[, .(pidp, gor_dv, hh_group)], by = "pidp", all.x = TRUE)
dt <- merge(dt, foo[, .(pidp, foo_cluster)], by = "pidp", all.x = TRUE)
dt <- merge(dt, ipw[, .(pidp, ipw_trimmed)], by = "pidp", all.x = TRUE)
dt <- merge(dt, nssec, by = "pidp", all.x = TRUE)
dt <- dt[first_window_regime %in% c(2L, 6L)]
dt[, regime_init := factor(paste0("R", first_window_regime), levels = c("R2", "R6"))]
dt[, birth_cohort := factor(birth_cohort, levels = c("pre-1950", "1950s", "1960s", "1970s", "post-1980"))]
dt[, sex := factor(sex, levels = c("male", "female"))]
dt[, region := factor(gor_dv)]
dt[, hh_group := factor(hh_group)]
fit_dt <- dt[complete.cases(escape, regime_init, nssec_proxy, birth_cohort, sex, region, hh_group, ipw_trimmed)]
fit_dt[, ipw_model := ipw_trimmed * .N / sum(ipw_trimmed)]

formula_fixed <- escape ~ regime_init + nssec_proxy + birth_cohort + sex + region
formula_re <- escape ~ regime_init + nssec_proxy + birth_cohort + sex + region + (1 | hh_group)

summarise_glm <- function(fit) {
  tab <- coef(summary(fit))
  list(
    regime_initR6 = as.numeric(tab["regime_initR6", "Estimate"]),
    nssec_proxyM = as.numeric(tab["nssec_proxyM", "Estimate"]),
    nssec_proxyL = as.numeric(tab["nssec_proxyL", "Estimate"])
  )
}
summarise_re <- function(fit) {
  tab <- summary(fit)$coefficients$cond
  vc <- VarCorr(fit)
  sigma2 <- as.numeric(vc$cond$hh_group[1L, 1L])
  list(
    regime_initR6 = as.numeric(tab["regime_initR6", "Estimate"]),
    nssec_proxyM = as.numeric(tab["nssec_proxyM", "Estimate"]),
    nssec_proxyL = as.numeric(tab["nssec_proxyL", "Estimate"]),
    sigma_u = sqrt(sigma2),
    icc = sigma2 / (sigma2 + pi^2 / 3),
    convergence = fit$fit$convergence
  )
}

result <- list(
  generated_at = format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ"),
  n = nrow(fit_dt),
  weight_summary = list(
    ipw_trimmed_mean = mean(fit_dt$ipw_trimmed),
    ipw_model_mean = mean(fit_dt$ipw_model),
    ipw_model_min = min(fit_dt$ipw_model),
    ipw_model_max = max(fit_dt$ipw_model)
  ),
  glm_unweighted = summarise_glm(glm(formula_fixed, data = fit_dt, family = binomial())),
  glm_weighted = summarise_glm(glm(formula_fixed, data = fit_dt, family = binomial(), weights = ipw_model)),
  glmm_unweighted = summarise_re(glmmTMB(formula_re, data = fit_dt, family = binomial())),
  glmm_weighted = summarise_re(glmmTMB(formula_re, data = fit_dt, family = binomial(), weights = ipw_model))
)
write(toJSON(result, auto_unbox = TRUE, pretty = TRUE, na = "null"), OUT_PATH)
cat("Saved ", OUT_PATH, "\n", sep = "")
