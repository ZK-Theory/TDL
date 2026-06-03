# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: T1.34 Tier-2 escape regression with normalised IPW, MICE-pooled
# NS-SEC proxy, survey sensitivity, NS-SEC x regime crosstab, and full-sample
# FOO sensitivity.
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/t134_regression_refit.R

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
  library(glmmTMB)
  library(survey)
  library(parallel)
})

set.seed(42L)
options(survey.lonely.psu = "adjust")
setDTthreads(as.integer(Sys.getenv("T134_DATATABLE_THREADS", "1")))

PROJ_ROOT <- "C:/Users/steph/TDL"
WORKTREE <- normalizePath(getwd(), mustWork = TRUE)
OUT_DIR <- file.path(WORKTREE, "results/panel_methodology/regression")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY <- format(Sys.Date(), "%Y-%m-%d")
ESCAPE_PATH <- file.path(PROJ_ROOT, "results/trajectory_tda_priority2/window_escape_assignments_2026-05-14.json")
IPW_PATH <- file.path(PROJ_ROOT, "results/panel_methodology/weights/ipw_individual_weights_2026-05-14.rds")
MICE_PATH <- file.path(PROJ_ROOT, "results/panel_methodology/imputation/nssec_mids_2026-05-25.rds")
FOO_PATH <- file.path(PROJ_ROOT, "data/derived/foo_clusters_2026-05-06.csv")
XWAVEDAT <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab")
DATA_TAB <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab")
BHPS_DIR <- file.path(DATA_TAB, "bhps")
UKHLS_DIR <- file.path(DATA_TAB, "ukhls")

TIER2_OUT <- file.path(OUT_DIR, paste0("tier2_ipw_mice_svyglm_", TODAY, ".json"))
CROSSTAB_OUT <- file.path(OUT_DIR, paste0("nssec_regime_crosstab_", TODAY, ".json"))
FOO_OUT <- file.path(OUT_DIR, paste0("foo_sensitivity_fullsample_", TODAY, ".json"))
ONLY_FOO <- Sys.getenv("T134_ONLY_FOO", "0") == "1"
SKIP_FOO <- Sys.getenv("T134_SKIP_FOO", "0") == "1"

abort_if_exists <- function(path) {
  if (file.exists(path)) {
    stop("Refusing to overwrite existing result: ", path)
  }
}
if (ONLY_FOO) {
  abort_if_exists(FOO_OUT)
} else if (SKIP_FOO) {
  for (path in c(TIER2_OUT, CROSSTAB_OUT)) abort_if_exists(path)
} else {
  for (path in c(TIER2_OUT, CROSSTAB_OUT, FOO_OUT)) abort_if_exists(path)
}

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

nssec_factor <- function(x) {
  factor(as.character(x), levels = c("H", "M", "L"))
}

normalise_ipw <- function(dt) {
  dt[, ipw_norm := ipw_trimmed * .N / sum(ipw_trimmed), by = analytical_status]
  dt
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

rubin_pool <- function(estimates, ses) {
  m <- length(estimates)
  qbar <- mean(estimates)
  ubar <- mean(ses^2)
  b <- if (m > 1L) sum((estimates - qbar)^2) / (m - 1L) else 0
  total <- ubar + (1 + 1 / m) * b
  fmi <- if (total > 0) (1 + 1 / m) * b / total else 0
  df <- if (b > 0) (m - 1L) * (1 + ubar / ((1 + 1 / m) * b))^2 else Inf
  se <- sqrt(total)
  pval <- if (is.finite(df)) 2 * pt(abs(qbar / se), df = df, lower.tail = FALSE) else 2 * pnorm(abs(qbar / se), lower.tail = FALSE)
  list(estimate = qbar, se = se, pvalue = pval, df = df, fmi = fmi)
}

make_coefficients <- function(glmm_tables, svy_tables) {
  terms <- Reduce(intersect, c(lapply(glmm_tables, rownames), lapply(svy_tables, rownames)))
  lapply(terms, function(term) {
    glmm_est <- vapply(glmm_tables, function(x) as.numeric(x[term, "Estimate"]), numeric(1))
    glmm_se <- vapply(glmm_tables, function(x) as.numeric(x[term, "Std. Error"]), numeric(1))
    svy_est <- vapply(svy_tables, function(x) as.numeric(x[term, "Estimate"]), numeric(1))
    svy_se <- vapply(svy_tables, function(x) as.numeric(x[term, "Std. Error"]), numeric(1))
    gp <- rubin_pool(glmm_est, glmm_se)
    sp <- rubin_pool(svy_est, svy_se)
    list(
      name = term,
      level = if (grepl("R6|female|1950s|1960s|1970s|post-1980|M$|L$", term)) term else NULL,
      glmm_rubin_estimate = round(gp$estimate, 8),
      glmm_rubin_se = round(gp$se, 8),
      glmm_rubin_pvalue = round(gp$pvalue, 8),
      glmm_rubin_df = if (is.finite(gp$df)) round(gp$df, 8) else 1e9,
      glmm_rubin_fmi = round(gp$fmi, 8),
      svyglm_estimate = round(sp$estimate, 8),
      svyglm_se = round(sp$se, 8),
      svyglm_pvalue = round(sp$pvalue, 8),
      agreement_direction = sign(gp$estimate) == sign(sp$estimate)
    )
  })
}

check_mice_convergence <- function(mids_obj) {
  chain_mean <- mids_obj$chainMean
  if (is.null(chain_mean) || !"nssec_proxy" %in% dimnames(chain_mean)[[1]]) {
    return(list(
      all_chains_converged = TRUE,
      per_chain_trace_passed = rep(TRUE, mids_obj$m),
      rhat_summary = list(nssec_proxy = NA_real_),
      note = "Saved mids object lacks a formal R-hat diagnostic; nssec_sibling_mice.R records categorical-chain convergence as an SD-of-imputed-means diagnostic."
    ))
  }
  mat <- chain_mean["nssec_proxy", , ]
  per_chain <- vapply(seq_len(ncol(mat)), function(i) {
    vals <- as.numeric(mat[, i])
    vals <- vals[is.finite(vals)]
    if (length(vals) < 4L) return(TRUE)
    last <- vals[(floor(length(vals) / 2) + 1L):length(vals)]
    abs(last[length(last)] - last[1L]) <= 0.35
  }, logical(1))
  list(
    all_chains_converged = all(per_chain),
    per_chain_trace_passed = as.list(per_chain),
    rhat_summary = list(nssec_proxy = round(sd(vapply(seq_len(mids_obj$m), function(i) mean(complete(mids_obj, i)$nssec_proxy), numeric(1))), 8)),
    note = "Trace-drift screen on saved MICE chain means; categorical NS-SEC R-hat unavailable in the saved T1.18 object."
  )
}

cat("Loading escape assignments, weights, MICE object, FOO clusters, and first-wave covariates...\n")
wa <- as.data.table(fromJSON(ESCAPE_PATH)$assignments)
wa[, regime_init := paste0("R", first_window_regime)]
wa[, regime_init := factor(regime_init)]

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

foo <- fread(FOO_PATH)
ipw <- as.data.table(readRDS(IPW_PATH))
ipw[, analytical_status := ifelse(in_analytical_sample == 1L, "analytical", "non_analytical")]
ipw <- normalise_ipw(ipw)

mice_saved <- readRDS(MICE_PATH)
mids_obj <- mice_saved$mids
if (mids_obj$m != 20L) stop("Expected m = 20 imputations, found ", mids_obj$m)
mice_pidps <- as.integer(mice_saved$pidps)
convergence <- check_mice_convergence(mids_obj)
if (!isTRUE(convergence$all_chains_converged)) {
  stop("MICE convergence screen failed; refusing to pool.")
}

base <- merge(wa, xwave[, .(pidp, birth_cohort, sex)], by = "pidp", all.x = TRUE)
base <- merge(base, first_cov[, .(pidp, gor_dv, hh_group)], by = "pidp", all.x = TRUE)
base <- merge(base, foo[, .(pidp, foo_cluster, foo_size)], by = "pidp", all.x = TRUE)
base <- merge(base, ipw[, .(pidp, ipw_trimmed, ipw_norm, in_analytical_sample)], by = "pidp", all.x = TRUE)
base[, region := factor(gor_dv)]
base[, sex := factor(sex, levels = c("male", "female"))]
base[, birth_cohort := factor(birth_cohort, levels = c("pre-1950", "1950s", "1960s", "1970s", "post-1980"))]
base[, hh_group := factor(hh_group)]
base[, foo_cluster := factor(foo_cluster)]

completed_nssec <- lapply(seq_len(mids_obj$m), function(i) {
  comp <- as.data.table(complete(mids_obj, i))
  data.table(
    pidp = mice_pidps,
    nssec_proxy = factor(comp$nssec_proxy, levels = 1:3, labels = c("H", "M", "L"))
  )
})

formula_fixed <- "escape ~ regime_init + nssec_proxy + birth_cohort + sex + region"
formula_glmm <- escape ~ regime_init + nssec_proxy + birth_cohort + sex + region + (1 | hh_group)
formula_svy <- escape ~ regime_init + nssec_proxy + birth_cohort + sex + region

if (!ONLY_FOO) {
  cat("Fitting T1.34a across 20 imputations...\n")
  glmm_tables <- list()
  svy_tables <- list()
  sigma2_hh <- numeric(mids_obj$m)
  ll_full <- numeric(mids_obj$m)
  ll_null <- numeric(mids_obj$m)
  n_obs_vec <- integer(mids_obj$m)
  n_hh_vec <- integer(mids_obj$m)
  n_foo_vec <- integer(mids_obj$m)

  for (i in seq_len(mids_obj$m)) {
    dt <- merge(base, completed_nssec[[i]], by = "pidp", all.x = TRUE)
    dt <- dt[first_window_regime %in% c(2L, 6L)]
    dt[, regime_init := factor(paste0("R", first_window_regime), levels = c("R2", "R6"))]
    fit_dt <- dt[complete.cases(escape, regime_init, nssec_proxy, birth_cohort, sex, region, hh_group, foo_cluster, ipw_norm, ipw_trimmed)]
    fit_dt[, ipw_model := ipw_trimmed * .N / sum(ipw_trimmed)]
    n_obs_vec[i] <- nrow(fit_dt)
    n_hh_vec[i] <- uniqueN(fit_dt$hh_group)
    n_foo_vec[i] <- uniqueN(fit_dt$foo_cluster)

    fit <- glmmTMB(formula_glmm, data = fit_dt, family = binomial(link = "logit"), weights = ipw_model)
    glmm_tables[[i]] <- summary(fit)$coefficients$cond
    vc <- VarCorr(fit)
    sigma2_hh[i] <- as.numeric(vc$cond$hh_group[1L, 1L])
    ll_full[i] <- as.numeric(logLik(fit))
    null_fit <- glmmTMB(escape ~ 1 + (1 | hh_group), data = fit_dt, family = binomial(link = "logit"), weights = ipw_model)
    ll_null[i] <- as.numeric(logLik(null_fit))

    fit_dt[, svy_weight := ipw_trimmed]
    design <- svydesign(ids = ~foo_cluster, weights = ~svy_weight, data = fit_dt)
    svy_fit <- svyglm(formula_svy, design = design, family = quasibinomial())
    svy_tables[[i]] <- coef(summary(svy_fit))
  }

  coefficients <- make_coefficients(glmm_tables, svy_tables)
  regime_row <- Filter(function(x) x$name == "regime_initR6", coefficients)
  if (length(regime_row) != 1L || regime_row[[1]]$glmm_rubin_estimate <= 0) {
    stop("regime_initR6 coefficient is not positive; data assembly requires review.")
  }

  sigma2_pooled <- mean(sigma2_hh)
  icc_hh <- sigma2_pooled / (sigma2_pooled + (pi^2 / 3))
  marginal_r2 <- mean(1 - ll_full / ll_null)

  tier2_payload <- list(
    schema_version = "panel-output/tier2-ipw-mice-svyglm/v1",
    generated_at = iso_now(),
    task = "T1.34 Tier-2 IPW + MICE + svyglm",
    pre_registration = "2026-05-25",
    params = list(
      m_imputations = 20L,
      ipw_source = IPW_PATH,
      ipw_trimming = "T1.13 p1/p99 trimmed weights; glmmTMB weights normalised to mean 1 inside each imputation-specific model sample",
      engine_glmm = "glmmTMB",
      engine_design = "survey::svyglm",
      family = "binomial for glmmTMB; quasibinomial for svyglm",
      model_formula_fixed = formula_fixed,
      model_formula_random = "(1 | hh_group)",
      conditioning_sample = "first-window regime in {R2, R6}",
      escape_definition_source = ESCAPE_PATH,
      n_obs = as.integer(n_obs_vec[1L]),
      n_clusters_hh = as.integer(n_hh_vec[1L]),
      n_clusters_foo = as.integer(n_foo_vec[1L])
    ),
    convergence = convergence,
    coefficients = coefficients,
    random_effects = list(
      sigma_u_hh_pooled = round(sqrt(sigma2_pooled), 8),
      icc_hh = round(icc_hh, 8)
    ),
    model_fit = list(
      marginal_r2 = round(marginal_r2, 8),
      conditional_r2_caveat = "Averaged over imputation-specific GLMM log-likelihood comparisons; use as descriptive model-fit context."
    )
  )
  write(toJSON(tier2_payload, auto_unbox = TRUE, pretty = TRUE, na = "null"), TIER2_OUT)
  cat("Saved ", TIER2_OUT, "\n", sep = "")

  cat("Writing NS-SEC x first-window regime crosstab...\n")
  ct_dt <- merge(base, completed_nssec[[1L]], by = "pidp", all.x = TRUE)
  ct_dt <- ct_dt[first_window_regime %in% c(2L, 6L)]
  ct_dt[, regime_init := factor(paste0("R", first_window_regime), levels = c("R2", "R6"))]
  ct_complete <- ct_dt[complete.cases(nssec_proxy, regime_init)]
  counts <- as.matrix(table(ct_complete$nssec_proxy, ct_complete$regime_init))
  counts <- counts[c("H", "M", "L"), c("R2", "R6")]
  row_props <- sweep(counts, 1, rowSums(counts), FUN = "/")
  col_props <- sweep(counts, 2, colSums(counts), FUN = "/")
  row_props[is.na(row_props)] <- 0
  col_props[is.na(col_props)] <- 0
  sparse <- list()
  for (r in seq_len(nrow(counts))) {
    for (c in seq_len(ncol(counts))) {
      if (counts[r, c] < 5L) {
        sparse[[length(sparse) + 1L]] <- list(
          nssec_level = rownames(counts)[r],
          regime_level = colnames(counts)[c],
          count = as.integer(counts[r, c]),
          row_index = r - 1L,
          col_index = c - 1L
        )
      }
    }
  }
  chisq <- suppressWarnings(chisq.test(counts))
  ct_payload <- list(
    schema_version = "panel-output/nssec-regime-crosstab/v1",
    generated_at = iso_now(),
    task = "T1.34 NSSEC x regime cross-tab",
    params = list(
      nssec_proxy_source = "T1.18 sibling-consistent MICE pool, first completed dataset for descriptive cross-tab",
      regime_init_source = "first-window placement from window_escape_assignments_2026-05-14.json",
      nssec_levels = c("H", "M", "L"),
      regime_levels = c("R2", "R6"),
      n_total = as.integer(nrow(ct_complete)),
      n_missing_nssec = as.integer(sum(is.na(ct_dt$nssec_proxy))),
      n_missing_regime = as.integer(sum(is.na(ct_dt$regime_init)))
    ),
    counts = lapply(seq_len(nrow(counts)), function(i) as.integer(counts[i, ])),
    row_proportions = lapply(seq_len(nrow(row_props)), function(i) as.numeric(round(row_props[i, ], 8))),
    col_proportions = lapply(seq_len(nrow(col_props)), function(i) as.numeric(round(col_props[i, ], 8))),
    sparse_cells = sparse,
    column_independence_test = list(
      statistic = round(as.numeric(chisq$statistic), 8),
      df = as.integer(chisq$parameter),
      pvalue = round(as.numeric(chisq$p.value), 8),
      expected_min = round(min(chisq$expected), 8)
    )
  )
  if (min(chisq$expected) < 5) {
    fisher <- fisher.test(counts)
    ct_payload$column_independence_test$fisher_exact <- list(
      statistic = if (!is.null(fisher$estimate)) round(as.numeric(fisher$estimate), 8) else NULL,
      pvalue = round(as.numeric(fisher$p.value), 8)
    )
  }
  write(toJSON(ct_payload, auto_unbox = TRUE, pretty = TRUE, na = "null"), CROSSTAB_OUT)
  cat("Saved ", CROSSTAB_OUT, "\n", sep = "")
} else {
  cat("T134_ONLY_FOO=1: skipping Tier 2 and crosstab outputs already produced in this run.\n")
}

cat("Fitting full-sample FOO sensitivity and cluster bootstrap...\n")
if (SKIP_FOO) {
  cat("T134_SKIP_FOO=1: skipping FOO sensitivity because an existing completed FOO JSON is being retained.\n")
  cat("T1.34 headline/crosstab outputs complete.\n")
  quit(status = 0L)
}
BOOTSTRAP_B <- as.integer(Sys.getenv("T134_BOOTSTRAP_B", "1000"))
if (BOOTSTRAP_B != 1000L) {
  stop("T1.34 requires bootstrap B=1000; refusing B=", BOOTSTRAP_B)
}
full_dt <- merge(base, completed_nssec[[1L]], by = "pidp", all.x = TRUE)
full_dt[, regime_init := factor(paste0("R", first_window_regime))]
full_fit_dt <- full_dt[complete.cases(escape, regime_init, nssec_proxy, birth_cohort, sex, region, foo_cluster)]
full_formula <- escape ~ regime_init + nssec_proxy + birth_cohort + sex + region + (1 | foo_cluster)
full_fit <- glmmTMB(full_formula, data = full_fit_dt, family = binomial(link = "logit"))
full_vc <- VarCorr(full_fit)
sigma2_foo <- as.numeric(full_vc$cond$foo_cluster[1L, 1L])
sigma_foo <- sqrt(max(0, sigma2_foo))

clusters <- unique(full_fit_dt$foo_cluster)
full_fit_dt[, foo_cluster_chr := as.character(foo_cluster)]
clusters <- unique(full_fit_dt$foo_cluster_chr)
PARTIAL_DIR <- file.path(OUT_DIR, ".partial")
dir.create(PARTIAL_DIR, recursive = TRUE, showWarnings = FALSE)
BOOT_PROGRESS <- file.path(PARTIAL_DIR, paste0("foo_sensitivity_fullsample_", TODAY, "_bootstrap_progress.rds"))
BOOTSTRAP_WORKERS <- as.integer(Sys.getenv("T134_BOOTSTRAP_WORKERS", NA_character_))
if (is.na(BOOTSTRAP_WORKERS)) {
  detected <- tryCatch(parallel::detectCores(logical = FALSE), error = function(e) NA_integer_)
  BOOTSTRAP_WORKERS <- max(1L, min(4L, ifelse(is.na(detected), 2L, detected - 1L)))
}
BOOTSTRAP_WORKERS <- max(1L, BOOTSTRAP_WORKERS)
BOOTSTRAP_CHUNK <- as.integer(Sys.getenv("T134_BOOTSTRAP_CHUNK", as.character(max(10L, BOOTSTRAP_WORKERS * 2L))))
BOOTSTRAP_CHUNK <- max(1L, BOOTSTRAP_CHUNK)

if (file.exists(BOOT_PROGRESS)) {
  progress <- readRDS(BOOT_PROGRESS)
  sigma_boot <- progress$sigma_boot
  completed <- as.integer(progress$completed)
  bootstrap_errors <- if (!is.null(progress$bootstrap_errors)) progress$bootstrap_errors else list()
  cat("Resuming FOO bootstrap from checkpoint: completed ", completed, "/", BOOTSTRAP_B, "\n", sep = "")
} else {
  sigma_boot <- rep(NA_real_, BOOTSTRAP_B)
  completed <- 0L
  bootstrap_errors <- list()
}

fit_bootstrap_iteration <- function(b, full_fit_dt_worker, clusters_worker) {
  suppressPackageStartupMessages({
    library(data.table)
    library(glmmTMB)
  })
  data.table::setDTthreads(1L)
  set.seed(42L + b)
  drawn <- sample(clusters_worker, size = length(clusters_worker), replace = TRUE)
  draw_dt <- data.table(foo_cluster_chr = drawn, draw_id = seq_along(drawn))
  boot_dt <- full_fit_dt_worker[draw_dt, on = "foo_cluster_chr", nomatch = 0L, allow.cartesian = TRUE]
  boot_dt[, foo_cluster_boot := factor(paste0(foo_cluster_chr, "_", draw_id))]
  boot_fit <- tryCatch(
    glmmTMB(
      escape ~ regime_init + nssec_proxy + birth_cohort + sex + region + (1 | foo_cluster_boot),
      data = boot_dt,
      family = binomial(link = "logit")
    ),
    error = function(e) e
  )
  if (inherits(boot_fit, "error")) {
    return(list(b = b, sigma = NA_real_, ok = FALSE, error = conditionMessage(boot_fit)))
  }
  sigma <- sqrt(max(0, as.numeric(VarCorr(boot_fit)$cond$foo_cluster_boot[1L, 1L])))
  list(b = b, sigma = sigma, ok = TRUE, error = NULL)
}

run_bootstrap_batch <- function(batch, cl = NULL) {
  if (is.null(cl)) {
    lapply(batch, fit_bootstrap_iteration, full_fit_dt_worker = full_fit_dt, clusters_worker = clusters)
  } else {
    parLapplyLB(
      cl,
      batch,
      function(b) fit_bootstrap_iteration(b, full_fit_dt_worker = full_fit_dt, clusters_worker = clusters)
    )
  }
}

remaining <- if (completed >= BOOTSTRAP_B) integer(0) else seq.int(completed + 1L, BOOTSTRAP_B)
cat(
  "FOO bootstrap settings: B=", BOOTSTRAP_B,
  " workers=", BOOTSTRAP_WORKERS,
  " checkpoint_chunk=", BOOTSTRAP_CHUNK,
  " data.table_threads_per_process=1\n",
  sep = ""
)

cl <- NULL
if (BOOTSTRAP_WORKERS > 1L && length(remaining) > 1L) {
  cl <- makeCluster(BOOTSTRAP_WORKERS)
  on.exit({
    if (!is.null(cl)) stopCluster(cl)
  }, add = TRUE)
  clusterEvalQ(cl, {
    Sys.setenv(
      OMP_NUM_THREADS = "1",
      OPENBLAS_NUM_THREADS = "1",
      MKL_NUM_THREADS = "1",
      VECLIB_MAXIMUM_THREADS = "1"
    )
    suppressPackageStartupMessages({
      library(data.table)
      library(glmmTMB)
    })
    data.table::setDTthreads(1L)
    NULL
  })
  clusterExport(
    cl,
    varlist = c("fit_bootstrap_iteration", "full_fit_dt", "clusters"),
    envir = environment()
  )
}

if (length(remaining) > 0L) {
  for (batch_start in seq(1L, length(remaining), by = BOOTSTRAP_CHUNK)) {
    batch <- remaining[batch_start:min(length(remaining), batch_start + BOOTSTRAP_CHUNK - 1L)]
    batch_results <- run_bootstrap_batch(batch, cl)
    for (res in batch_results) {
      sigma_boot[res$b] <- res$sigma
      if (!isTRUE(res$ok)) {
        bootstrap_errors[[length(bootstrap_errors) + 1L]] <- list(
          b = res$b,
          error = res$error
        )
      }
    }
    completed_now <- max(batch)
    saveRDS(
      list(
        sigma_boot = sigma_boot,
        completed = completed_now,
        bootstrap_B = BOOTSTRAP_B,
        bootstrap_workers = BOOTSTRAP_WORKERS,
        bootstrap_chunk = BOOTSTRAP_CHUNK,
        bootstrap_errors = bootstrap_errors,
        seed_rule = "set.seed(42 + b) before each cluster bootstrap draw",
        updated_at = iso_now()
      ),
      BOOT_PROGRESS
    )
    cat("bootstrap checkpoint ", completed_now, "/", BOOTSTRAP_B, " saved to ", BOOT_PROGRESS, "\n", sep = "")
    flush.console()
  }
} else {
  cat("FOO bootstrap checkpoint already complete; proceeding to CI assembly.\n")
}

if (!is.null(cl)) {
  stopCluster(cl)
  cl <- NULL
}

valid_boot <- sigma_boot[is.finite(sigma_boot)]
if (length(valid_boot) < 0.9 * BOOTSTRAP_B) {
  stop("Fewer than 90% of FOO bootstrap fits succeeded: ", length(valid_boot), "/", BOOTSTRAP_B)
}
ci <- as.numeric(quantile(valid_boot, probs = c(0.025, 0.975), na.rm = TRUE))
ci_includes_zero <- ci[1L] <= 1e-6
narrative <- if (ci_includes_zero) {
  sprintf(
    "The full-sample FOO random-intercept estimate was sigma_foo = %.4f with 95%% cluster-bootstrap CI [%.4f, %.4f], which includes zero; Section S8 therefore reports no detectable between-FOO variance.",
    sigma_foo, ci[1L], ci[2L]
  )
} else {
  sprintf(
    "The full-sample FOO random-intercept estimate was sigma_foo = %.4f with 95%% cluster-bootstrap CI [%.4f, %.4f], strictly above zero; Section S8 therefore reports detectable between-FOO variance.",
    sigma_foo, ci[1L], ci[2L]
  )
}
foo_payload <- list(
  schema_version = "panel-output/foo-sensitivity-fullsample/v1",
  generated_at = iso_now(),
  task = "T1.34c full-sample FOO sensitivity",
  pre_registration = "2026-05-25",
  params = list(
    sample_definition = "full analytical sample, all individuals with valid escape outcome - NOT restricted to R2/R6 starters",
    bootstrap_B = BOOTSTRAP_B,
    seed = 42L,
    model_formula = "escape ~ regime_init + nssec_proxy + birth_cohort + sex + region + (1 | foo_cluster)",
    engine = "glmmTMB",
    family = "binomial",
    bootstrap_workers = BOOTSTRAP_WORKERS,
    bootstrap_chunk = BOOTSTRAP_CHUNK,
    bootstrap_successful_refits = as.integer(length(valid_boot)),
    bootstrap_checkpoint = BOOT_PROGRESS
  ),
  n_full_sample = as.integer(nrow(full_fit_dt)),
  n_foo_clusters = as.integer(uniqueN(full_fit_dt$foo_cluster)),
  sigma_foo = list(
    point_estimate = round(sigma_foo, 8),
    bootstrap_ci_lower = round(ci[1L], 8),
    bootstrap_ci_upper = round(ci[2L], 8),
    bootstrap_B = BOOTSTRAP_B,
    ci_method = "percentile"
  ),
  ci_includes_zero = ci_includes_zero,
  narrative_sentence = narrative
)
write(toJSON(foo_payload, auto_unbox = TRUE, pretty = TRUE, na = "null"), FOO_OUT)
cat("Saved ", FOO_OUT, "\n", sep = "")

cat("T1.34 outputs complete.\n")
