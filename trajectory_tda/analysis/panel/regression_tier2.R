# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: T1.20 — Tier 2 GLMM (household random intercept) on window-based R2/R6 starters.
#
# Adds (1 | hh_group) to Tier 1 fixed-effects structure to account for within-household
# correlation. hh_group = paste0(survey_origin, "_", hidp) where hidp is from the
# FIRST observed wave (first_cov$hidp). Composite key prevents BHPS/UKHLS hidp collision.
#
# Firth penalisation unavailable for GLMMs; quasi-separation handled via ML shrinkage
# from the random intercept. regime_6 retained from Tier 1 for build-up consistency.
#
# Instruction-accuracy adaptations from task spec:
#   - jbstat_bin (not jbstat_bin_first): same recoding as Tier 1
#   - age2 (pre-computed): equivalent to I(age_first_window^2)
#   - hh_group (not bare hidp): composite key, first-wave household
#   - regime_6 added: present in Tier 1; omitting would confound the build-up comparison
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/regression_tier2.R

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
})

if (!requireNamespace("glmmTMB", quietly = TRUE)) {
  stop(
    "glmmTMB is not installed. Add it to the locked R environment (renv.lock or ",
    "the project's R package manifest) and restore dependencies before running this script. ",
    "Do not install at runtime — runtime installation breaks reproducibility."
  )
}
suppressPackageStartupMessages(library(glmmTMB))

set.seed(42)

PROJ_ROOT  <- "C:/Users/steph/TDL"
WORKTREE   <- normalizePath(getwd(), mustWork = FALSE)
PRIORITY2  <- file.path(PROJ_ROOT, "results/trajectory_tda_priority2")
DATA_TAB   <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab")
BHPS_DIR   <- file.path(DATA_TAB, "bhps")
UKHLS_DIR  <- file.path(DATA_TAB, "ukhls")
XWAVEDAT   <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab")
OUT_DIR    <- file.path(WORKTREE, "results/panel_methodology/regression")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY    <- format(Sys.Date(), "%Y-%m-%d")
OUT_PATH <- file.path(OUT_DIR, paste0("tier2_glmm_firth_", TODAY, ".json"))

# Locate Tier 1 reference JSON (most recent in worktree results)
tier1_candidates <- list.files(
  file.path(WORKTREE, "results/panel_methodology/regression"),
  pattern = "^tier1_clustered_firth_\\d{4}-\\d{2}-\\d{2}\\.json$",
  full.names = TRUE
)
TIER1_JSON <- if (length(tier1_candidates) > 0L) {
  tier1_candidates[which.max(file.info(tier1_candidates)$mtime)]
} else {
  file.path(PROJ_ROOT, "results/panel_methodology/regression/tier1_clustered_firth_2026-05-14.json")
}

BHPS_WAVES  <- paste0("b", letters[1:18])
BHPS_YEARS  <- 1991:2008
UKHLS_WAVES <- letters[1:15]
UKHLS_YEARS <- 2009:2023

# Locked jbstat recoding (T0.9)
E_CODES <- c(1L, 2L, 5L, 11L, 12L, 13L, 14L, 15L)
U_CODES <- c(3L, 9L)
I_CODES <- c(4L, 6L, 7L, 8L, 10L, 97L)

recode_jbstat <- function(x) {
  r  <- rep(NA_character_, length(x))
  xi <- as.integer(x)
  r[xi %in% E_CODES] <- "E"
  r[xi %in% U_CODES] <- "U"
  r[xi %in% I_CODES] <- "I"
  r
}

# Income tercile cuts from T1.13 (locked)
BHPS_CUTS  <- c(1282, 2437)
UKHLS_CUTS <- c(2153, 4139)

soc_to_class <- function(soc) {
  s     <- as.integer(soc)
  major <- s %/% 10L
  cls   <- rep(NA_character_, length(s))
  cls[major %in% 1:3 & !is.na(major)] <- "H"
  cls[major %in% 4:6 & !is.na(major)] <- "M"
  cls[major %in% 7:9 & !is.na(major)] <- "L"
  cls[s <= 0 | is.na(s)] <- NA_character_
  cls
}

cat("=== T1.20: Tier 2 GLMM — Household Random Intercept (First-Wave hidp) ===\n")
cat("Output:", OUT_PATH, "\n")
cat("Tier 1 reference:", TIER1_JSON, "\n\n")

# ---------------------------------------------------------------------------
# 1. Load window escape assignments
# ---------------------------------------------------------------------------
cat("Loading window escape assignments...\n")
wa_files <- list.files(PRIORITY2,
                       pattern = "^window_escape_assignments_.*\\.json$", full.names = TRUE)
if (length(wa_files) == 0L) stop("No window_escape_assignments JSON in ", PRIORITY2)
wa_path <- wa_files[which.max(file.info(wa_files)$mtime)]
cat("Using:", wa_path, "\n")

wa_json       <- fromJSON(wa_path)
asgn          <- as.data.table(wa_json$assignments)
starters      <- asgn[is_disadvantaged_starter == TRUE]
n_starters_all <- nrow(starters)
n_escaped_all  <- sum(starters$escape)
esc_rate_obs   <- n_escaped_all / n_starters_all
cat("n_starters:", n_starters_all, " escape_rate:", round(esc_rate_obs, 4), "\n")

starter_dt    <- starters[, .(pidp, escape, age_first_window, first_window_regime)]
starter_pidps <- starter_dt$pidp

# ---------------------------------------------------------------------------
# 2. Load xwavedat covariates (identical to Tier 1)
# ---------------------------------------------------------------------------
cat("Loading xwavedat covariates...\n")
xwave_full <- fread(XWAVEDAT, sep = "\t",
                    select = c("pidp", "birthy", "sex_dv", "pasoc90_cc", "masoc90_cc"))
xwave_full[, birthy := as.integer(birthy)]
xwave_full[birthy <= 1900 | birthy > 2005 | is.na(birthy), birthy := NA_integer_]

xwave_an <- xwave_full[pidp %in% starter_pidps]
xwave_an[, nssec_proxy := soc_to_class(pasoc90_cc)]
xwave_an[is.na(nssec_proxy), nssec_proxy := soc_to_class(masoc90_cc)]
xwave_an[, birth_year := as.integer(birthy)]
xwave_an[birth_year <= 1900 | birth_year > 2005, birth_year := NA_integer_]
xwave_an[, sex := fifelse(as.integer(sex_dv) == 2L, "female",
                  fifelse(as.integer(sex_dv) == 1L, "male", NA_character_))]

starter_dt <- merge(starter_dt,
                    xwave_an[, .(pidp, nssec_proxy, birth_year, sex)],
                    by = "pidp", all.x = TRUE)

starter_dt[, birth_cohort := fcase(
  birth_year < 1950,                      "pre-1950",
  birth_year >= 1950 & birth_year < 1960, "1950s",
  birth_year >= 1960 & birth_year < 1970, "1960s",
  birth_year >= 1970 & birth_year < 1980, "1970s",
  birth_year >= 1980,                     "post-1980",
  default = NA_character_
)]

# ---------------------------------------------------------------------------
# 3. Load first-wave covariates: hiqual_dv, jbstat, gor_dv, hidp (first wave)
# ---------------------------------------------------------------------------
cat("Loading first-wave covariates from BHPS and UKHLS indresp files...\n")

load_first_wave <- function(dir_path, waves, wave_years, target_pidps) {
  first_dt   <- data.table(pidp = integer(0), hiqual_dv = integer(0),
                            jbstat = integer(0), gor_dv = integer(0),
                            hidp = integer(0), wave = character(0),
                            wave_year = integer(0), survey_origin = character(0))
  seen_first <- integer(0)

  for (wi in seq_along(waves)) {
    wave  <- waves[wi]
    wyear <- wave_years[wi]
    fpath <- file.path(dir_path, paste0(wave, "_indresp.tab"))
    if (!file.exists(fpath)) next
    hdr <- names(fread(fpath, nrows = 0L, sep = "\t"))

    hidp_col <- paste0(wave, "_hidp")
    gor_col  <- paste0(wave, "_gor_dv")
    hq_col   <- paste0(wave, "_hiqual_dv")
    jb_col   <- if (paste0(wave, "_jbstat_bh") %in% hdr) paste0(wave, "_jbstat_bh")
                else if (paste0(wave, "_jbstat") %in% hdr) paste0(wave, "_jbstat")
                else NA_character_

    needed <- c("pidp", hidp_col)
    opt    <- intersect(c(gor_col, hq_col, if (!is.na(jb_col)) jb_col), hdr)
    wdt    <- fread(fpath, sep = "\t", select = c(needed, opt))
    wdt    <- wdt[pidp %in% target_pidps]
    if (nrow(wdt) == 0L) next

    wdt[, wave          := wave]
    wdt[, wave_year     := wyear]
    wdt[, survey_origin := fifelse(wave %in% BHPS_WAVES, "BHPS", "UKHLS")]
    if (hidp_col %in% names(wdt)) setnames(wdt, hidp_col, "hidp",      skip_absent = TRUE)
    if (!is.na(jb_col) && jb_col %in% names(wdt))
      setnames(wdt, jb_col, "jbstat",   skip_absent = TRUE)
    if (hq_col  %in% names(wdt)) setnames(wdt, hq_col,  "hiqual_dv", skip_absent = TRUE)
    if (gor_col %in% names(wdt)) setnames(wdt, gor_col, "gor_dv",    skip_absent = TRUE)

    new_pidps <- setdiff(wdt$pidp, seen_first)
    if (length(new_pidps) > 0L) {
      first_dt   <- rbindlist(list(first_dt, wdt[pidp %in% new_pidps]), fill = TRUE)
      seen_first <- c(seen_first, new_pidps)
    }
  }
  first_dt
}

bhps_first  <- load_first_wave(BHPS_DIR,  BHPS_WAVES,  BHPS_YEARS,  starter_pidps)
ukhls_first <- load_first_wave(UKHLS_DIR, UKHLS_WAVES, UKHLS_YEARS, starter_pidps)
first_all   <- rbindlist(list(bhps_first, ukhls_first), fill = TRUE, use.names = TRUE)
setorder(first_all, pidp, wave_year)
first_cov   <- first_all[, .SD[1L], by = pidp]
cat("First-wave coverage:", nrow(first_cov), "/", n_starters_all, "\n")

# ---------------------------------------------------------------------------
# 4. Load first income for income_tercile_init (identical to Tier 1)
# ---------------------------------------------------------------------------
cat("Loading first income observation...\n")

get_first_income <- function(hhresp_dir, waves, wave_years) {
  rbindlist(lapply(seq_along(waves), function(wi) {
    wave  <- waves[wi]
    wyear <- wave_years[wi]
    fpath <- file.path(hhresp_dir, paste0(wave, "_hhresp.tab"))
    if (!file.exists(fpath)) return(NULL)
    hdr <- names(fread(fpath, nrows = 0L, sep = "\t"))
    hidp_col <- paste0(wave, "_hidp")
    inc_col  <- paste0(wave, "_fihhmngrs_dv")
    if (!hidp_col %in% hdr || !inc_col %in% hdr) return(NULL)
    dt2 <- fread(fpath, sep = "\t", select = c(hidp_col, inc_col))
    setnames(dt2, c(hidp_col, inc_col), c("hidp", "income"))
    dt2[, wave := wave]
    dt2
  }), fill = TRUE)
}

bhps_inc  <- get_first_income(BHPS_DIR,  BHPS_WAVES,  BHPS_YEARS)
ukhls_inc <- get_first_income(UKHLS_DIR, UKHLS_WAVES, UKHLS_YEARS)
all_inc   <- rbindlist(list(bhps_inc, ukhls_inc), fill = TRUE)

first_inc <- merge(first_cov[, .(pidp, hidp, wave, wave_year, survey_origin)],
                   all_inc, by = c("hidp", "wave"), all.x = TRUE)
setorder(first_inc, pidp, wave_year)
first_inc <- first_inc[income > 0L & !is.na(income)][, .SD[1L], by = pidp]

first_inc[, income_tercile_init := fcase(
  survey_origin == "BHPS"  & income <= BHPS_CUTS[1],  "L",
  survey_origin == "BHPS"  & income <= BHPS_CUTS[2],  "M",
  survey_origin == "BHPS"  & income  > BHPS_CUTS[2],  "H",
  survey_origin == "UKHLS" & income <= UKHLS_CUTS[1], "L",
  survey_origin == "UKHLS" & income <= UKHLS_CUTS[2], "M",
  survey_origin == "UKHLS" & income  > UKHLS_CUTS[2], "H"
)]

# ---------------------------------------------------------------------------
# 5. Assemble analytical dataset
# ---------------------------------------------------------------------------
cat("Assembling regression dataset...\n")

# Tier 2: merge first-wave hidp (not hidp_last) as the GLMM grouping factor
reg_dt <- merge(starter_dt,
                first_cov[, .(pidp, hiqual_dv, jbstat, gor_dv, hidp, wave_year, survey_origin)],
                by = "pidp", all.x = TRUE)
reg_dt <- merge(reg_dt, first_inc[, .(pidp, income_tercile_init)], by = "pidp", all.x = TRUE)

# Rename to hidp_first for clarity (vs hidp_last used in Tier 1 clustering)
setnames(reg_dt, "hidp", "hidp_first")

# Composite household group key to prevent BHPS/UKHLS hidp integer collision
reg_dt[, hh_group := paste0(survey_origin, "_", hidp_first)]

reg_dt[, jbstat_bin := recode_jbstat(jbstat)]
reg_dt[hiqual_dv <= 0 | is.na(hiqual_dv), hiqual_dv := NA_integer_]
reg_dt[gor_dv    <= 0 | is.na(gor_dv),    gor_dv    := NA_integer_]

# regime_6: R6 vs R2 starters — in Tier 1 (OR=18.6); retained for build-up consistency
reg_dt[, regime_6 := as.integer(first_window_regime == 6L)]

reg_dt[, hiqual_dv           := factor(hiqual_dv)]
reg_dt[, gor_dv              := factor(gor_dv)]
reg_dt[, jbstat_bin          := factor(jbstat_bin,          levels = c("E", "U", "I"))]
reg_dt[, income_tercile_init := factor(income_tercile_init, levels = c("L", "M", "H"))]
reg_dt[, nssec_proxy         := factor(nssec_proxy,         levels = c("H", "M", "L"))]
reg_dt[, birth_cohort        := factor(birth_cohort,
                                       levels = c("pre-1950", "1950s", "1960s",
                                                  "1970s", "post-1980"))]
reg_dt[, survey_origin       := factor(survey_origin, levels = c("BHPS", "UKHLS"))]
reg_dt[, sex                 := factor(sex, levels = c("male", "female"))]
reg_dt[, hh_group            := factor(hh_group)]

cat("Total starter rows before complete-case:", nrow(reg_dt), "\n")

pred_cols <- c("age_first_window", "sex", "hiqual_dv", "jbstat_bin",
               "income_tercile_init", "nssec_proxy", "birth_cohort", "gor_dv",
               "survey_origin")
cc_mask <- complete.cases(reg_dt[, ..pred_cols]) &
           !is.na(reg_dt$escape) &
           !is.na(reg_dt$hidp_first)
reg_cc <- reg_dt[cc_mask]

n_cc        <- nrow(reg_cc)
n_esc_cc    <- sum(reg_cc$escape == 1L)
n_rem_cc    <- sum(reg_cc$escape == 0L)
esc_rate_cc <- round(mean(reg_cc$escape), 4)
n_clusters  <- length(unique(reg_cc$hh_group))

cat("Complete-case n:", n_cc, "(excluded:", n_starters_all - n_cc, ")\n")
cat("Escapers:", n_esc_cc, sprintf("(%.1f%%)", 100 * esc_rate_cc), "\n")
cat("Remainers:", n_rem_cc, "\n")
cat("n clusters (hh_group):", n_clusters, "\n")

reg_cc[, age2 := age_first_window^2]
reg_df <- as.data.frame(reg_cc)

# ---------------------------------------------------------------------------
# 6. Quasi-separation diagnostic (same cell definitions as Tier 1)
# ---------------------------------------------------------------------------
cat("Running quasi-separation diagnostic...\n")

check_sep <- function(dt2, var1, var2 = NULL) {
  by_vars <- if (is.null(var2)) var1 else c(var1, var2)
  tbl     <- dt2[, .(n = .N, n_escape = sum(escape)), by = by_vars]
  tbl[, n_no_escape := n - n_escape]
  tbl[, has_sep := (n_escape == 0L | n_no_escape == 0L)]
  tbl
}

sep1 <- check_sep(reg_cc, "birth_cohort", "nssec_proxy")
sep2 <- check_sep(reg_cc, "birth_cohort", "survey_origin")
sep3 <- check_sep(reg_cc, "gor_dv",       "birth_cohort")
n_sep_cells <- sum(c(sep1$has_sep, sep2$has_sep, sep3$has_sep))
cat("Quasi-separation cells:", n_sep_cells,
    "(Tier 1 reference: 11; 9 gor x cohort + 2 cohort x nssec)\n")

sep_summary <- list(
  n_separation_cells = n_sep_cells,
  cohort_x_nssec  = list(n_cells = nrow(sep1), n_sep = sum(sep1$has_sep)),
  cohort_x_survey = list(n_cells = nrow(sep2), n_sep = sum(sep2$has_sep)),
  gor_x_cohort    = list(n_cells = nrow(sep3), n_sep = sum(sep3$has_sep)),
  tier1_n_sep     = 11L,
  note = paste0(
    "Tier 1 used Firth penalisation (n_sep=11: 9 gor x cohort, 2 cohort x nssec). ",
    "Tier 2 standard GLMM ML; quasi-separation handled via RE shrinkage. ",
    "Large directional reversals vs Tier 1 would warrant follow-up."
  )
)

# ---------------------------------------------------------------------------
# 7. Fit Tier 2 GLMM with household random intercept (glmmTMB)
# ---------------------------------------------------------------------------
cat("Fitting Tier 2 GLMM with (1|hh_group) via glmmTMB...\n")
cat("Formula: escape ~ age_first_window + age2 + sex + hiqual_dv + jbstat_bin +\n")
cat("         income_tercile_init + nssec_proxy + birth_cohort + gor_dv +\n")
cat("         survey_origin + regime_6 + (1 | hh_group)\n")

formula_t2 <- escape ~ age_first_window + age2 + sex + hiqual_dv + jbstat_bin +
  income_tercile_init + nssec_proxy + birth_cohort + gor_dv + survey_origin +
  regime_6 + (1 | hh_group)

optimizer_used <- "default (nlminb)"
warnings_fit   <- character(0)

fit_t2 <- withCallingHandlers(
  glmmTMB(formula_t2, data = reg_df, family = binomial(link = "logit")),
  warning = function(w) {
    warnings_fit <<- c(warnings_fit, conditionMessage(w))
    invokeRestart("muffleWarning")
  }
)
cat("Initial fit complete.\n")

convergence_code <- tryCatch(fit_t2$fit$convergence, error = function(e) NA_integer_)
convergence_msg  <- tryCatch(fit_t2$fit$message,     error = function(e) "unavailable")
gradient_max     <- tryCatch(max(abs(fit_t2$fit$gradient)), error = function(e) NA_real_)

cat(sprintf("Convergence: code=%s | gradient_max=%.6f\n",
            convergence_code, ifelse(is.na(gradient_max), -999, gradient_max)))

if (length(warnings_fit) > 0L) {
  cat("Fit warnings:\n")
  for (w in warnings_fit) cat(" -", w, "\n")
}

# Fallback: L-BFGS-B if convergence uncertain
if (!isTRUE(convergence_code == 0L)) {
  cat("Retrying with L-BFGS-B optimizer...\n")
  warnings_retry <- character(0)
  fit_retry <- tryCatch(
    withCallingHandlers(
      glmmTMB(formula_t2, data = reg_df, family = binomial(link = "logit"),
              control = glmmTMBControl(optimizer  = optim,
                                      optArgs    = list(method = "L-BFGS-B"))),
      warning = function(w) {
        warnings_retry <<- c(warnings_retry, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(e) {
      cat("L-BFGS-B retry failed:", conditionMessage(e), "\n")
      NULL
    }
  )
  if (!is.null(fit_retry)) {
    conv_retry <- tryCatch(fit_retry$fit$convergence, error = function(e) NA_integer_)
    if (isTRUE(conv_retry == 0L) || (!isTRUE(convergence_code == 0L))) {
      fit_t2         <- fit_retry
      convergence_code <- conv_retry
      convergence_msg  <- tryCatch(fit_retry$fit$message, error = function(e) "unavailable")
      gradient_max     <- tryCatch(max(abs(fit_retry$fit$gradient)), error = function(e) NA_real_)
      warnings_fit   <- warnings_retry
      optimizer_used <- "L-BFGS-B fallback"
      cat(sprintf("L-BFGS-B retry: code=%s | gradient_max=%.6f\n",
                  convergence_code, ifelse(is.na(gradient_max), -999, gradient_max)))
    }
  }
}

# Singular fit check
singular_fit <- tryCatch(isSingular(fit_t2), error = function(e) NA)
cat("Singular fit:", singular_fit, "\n")

# ---------------------------------------------------------------------------
# 8. Random effects: sigma2_u, sigma_u, ICC
# ---------------------------------------------------------------------------
cat("Extracting random effects...\n")

vc_list  <- VarCorr(fit_t2)
sigma2_u <- tryCatch({
  as.numeric(vc_list$cond$hh_group[1L, 1L])
}, error = function(e) {
  tryCatch(attr(vc_list$cond$hh_group, "stddev")[[1L]]^2,
           error = function(e2) NA_real_)
})
sigma_u  <- sqrt(sigma2_u)
icc      <- sigma2_u / (sigma2_u + (pi^2 / 3))
cat(sprintf("sigma2_u=%.6f | sigma_u=%.6f | ICC=%.6f\n", sigma2_u, sigma_u, icc))

# ---------------------------------------------------------------------------
# 9. Fixed-effects coefficient table (Wald CIs)
# ---------------------------------------------------------------------------
cat("Extracting coefficient table...\n")

summ_t2  <- summary(fit_t2)
fe_table <- summ_t2$coefficients$cond

# Wald CIs via manual calculation (confint may include RE rows which misalign)
est_vec <- fe_table[, "Estimate"]
se_vec  <- fe_table[, "Std. Error"]
ci_lo   <- est_vec - 1.96 * se_vec
ci_hi   <- est_vec + 1.96 * se_vec

coef_list <- lapply(seq_len(nrow(fe_table)), function(i) {
  list(
    term      = rownames(fe_table)[i],
    estimate  = round(fe_table[i, "Estimate"],   4),
    SE        = round(fe_table[i, "Std. Error"], 4),
    z_value   = round(fe_table[i, "z value"],    4),
    p_value   = round(fe_table[i, "Pr(>|z|)"],   4),
    OR        = round(exp(est_vec[i]),  4),
    CI_lo_OR  = round(exp(ci_lo[i]),   4),
    CI_hi_OR  = round(exp(ci_hi[i]),   4),
    CI_lo_log = round(ci_lo[i], 4),
    CI_hi_log = round(ci_hi[i], 4)
  )
})
cat("Fixed-effects terms:", length(coef_list), "\n")

# ---------------------------------------------------------------------------
# 10. Pseudo-R²: McFadden conditional (null includes RE)
# ---------------------------------------------------------------------------
cat("Computing McFadden R² (conditional on random effects)...\n")

ll_full    <- as.numeric(logLik(fit_t2))
fit_null_re <- tryCatch(
  suppressWarnings(
    glmmTMB(escape ~ 1 + (1 | hh_group), data = reg_df, family = binomial(link = "logit"))
  ),
  error = function(e) { cat("Null-RE model failed:", conditionMessage(e), "\n"); NULL }
)

mcfadden_cond <- if (!is.null(fit_null_re)) {
  round(1 - ll_full / as.numeric(logLik(fit_null_re)), 4)
} else NA_real_

# Marginal McFadden (intercept-only GLM as null)
ll_null_marg  <- as.numeric(logLik(glm(escape ~ 1, data = reg_df, family = binomial)))
mcfadden_marg <- round(1 - ll_full / ll_null_marg, 4)

cat(sprintf("McFadden R2: conditional=%.4f | marginal=%.4f\n",
            mcfadden_cond, mcfadden_marg))

# Nakagawa-Schielzeth marginal/conditional R² (if MuMIn available)
r2_naka <- tryCatch({
  if (requireNamespace("MuMIn", quietly = TRUE)) {
    r2 <- MuMIn::r.squaredGLMM(fit_t2)
    list(marginal = round(r2[1, "R2m"], 4), conditional = round(r2[1, "R2c"], 4))
  } else NULL
}, error = function(e) NULL)

pseudo_r2 <- list(
  mcfadden_conditional = mcfadden_cond,
  mcfadden_marginal    = mcfadden_marg,
  note = paste0(
    "Conditional: null model includes (1|hh_group). ",
    "Marginal: null is intercept-only GLM."
  )
)
if (!is.null(r2_naka)) {
  pseudo_r2$nakagawa_marginal    <- r2_naka$marginal
  pseudo_r2$nakagawa_conditional <- r2_naka$conditional
  cat("Nakagawa R²: marginal =", r2_naka$marginal,
      " conditional =", r2_naka$conditional, "\n")
}

# ---------------------------------------------------------------------------
# 11. Build-up comparison: Tier 1 vs Tier 2 key ORs
# ---------------------------------------------------------------------------
cat("Building Tier 1 vs Tier 2 comparison table...\n")

t1_data   <- tryCatch(fromJSON(TIER1_JSON), error = function(e) NULL)
t1_coefs  <- if (!is.null(t1_data)) as.data.table(t1_data$coefficient_table) else NULL

key_terms <- c(
  "nssec_proxyM", "nssec_proxyL",
  "birth_cohort1950s", "birth_cohort1960s", "birth_cohort1970s", "birth_cohortpost-1980",
  "income_tercile_initM", "income_tercile_initH",
  "sexfemale", "regime_6",
  "jbstat_binU", "jbstat_binI"
)

extract_t2 <- function(term) {
  for (r in coef_list)
    if (r$term == term) return(r)
  NULL
}

buildup_comparison <- lapply(key_terms, function(trm) {
  t1r <- if (!is.null(t1_coefs)) t1_coefs[get("term") == trm] else data.table()
  t2r <- extract_t2(trm)
  t1_or <- if (nrow(t1r) > 0) as.numeric(t1r$OR[1L])       else NA_real_
  t1_p  <- if (nrow(t1r) > 0) as.numeric(t1r$p_firth[1L])  else NA_real_
  t2_or <- if (!is.null(t2r)) t2r$OR       else NA_real_
  t2_p  <- if (!is.null(t2r)) t2r$p_value  else NA_real_
  list(
    term                = trm,
    T1_OR               = t1_or,
    T1_p_firth          = t1_p,
    T2_OR               = t2_or,
    T2_p_wald           = t2_p,
    OR_ratio_T2_T1      = if (!is.na(t1_or) && !is.na(t2_or) && t1_or > 0)
                            round(t2_or / t1_or, 4) else NA_real_,
    direction_consistent = if (!is.na(t1_or) && !is.na(t2_or) && t1_or != 1 && t2_or != 1)
                            sign(log(t1_or)) == sign(log(t2_or)) 
                           else if (!is.na(t1_or) && !is.na(t2_or) && (t1_or == 1 || t2_or == 1))
                            TRUE  # Null effect is direction-consistent with any effect
                           else NA  )
})

# Flag large directional reversals (log-OR difference > 0.5 and direction flips)
reversals <- Filter(function(x) isFALSE(x$direction_consistent) &&
                                 !is.na(x$T1_OR) && !is.na(x$T2_OR) &&
                                 abs(log(x$T2_OR) - log(x$T1_OR)) > 0.5,
                    buildup_comparison)
if (length(reversals) > 0L) {
  cat("WARNING: large directional reversals (requires follow-up):\n")
  for (r in reversals)
    cat(sprintf("  %s: T1 OR=%.3f → T2 OR=%.3f\n", r$term, r$T1_OR, r$T2_OR))
} else {
  cat("No large directional reversals in Tier 1 vs Tier 2.\n")
}

# ---------------------------------------------------------------------------
# 12. Assemble and save JSON
# ---------------------------------------------------------------------------
cat("Saving JSON to", OUT_PATH, "...\n")

result <- list(
  run_params = list(
    seed                = 42L,
    date                = TODAY,
    methodology         = paste0(
      "Tier 2 GLMM: Tier 1 fixed-effect structure + household random intercept (1|hh_group). ",
      "hh_group = paste0(survey_origin, '_', hidp_first) where hidp_first is the household ID ",
      "at the individual's first observed BHPS/UKHLS wave (composite key avoids BHPS/UKHLS ",
      "integer collision). Estimator: glmmTMB ML, binomial logit. No Firth penalisation ",
      "(unavailable for GLMMs); quasi-separation handled via RE shrinkage. ",
      "regime_6 included for build-up consistency with Tier 1."
    ),
    source_assignments  = wa_path,
    tier1_reference     = TIER1_JSON,
    n_starters_all_ages = n_starters_all,
    escape_rate_all     = round(esc_rate_obs, 6),
    n_obs               = n_cc,
    n_excluded_cc       = n_starters_all - n_cc,
    n_escapers          = n_esc_cc,
    n_remainers         = n_rem_cc,
    escape_rate         = esc_rate_cc,
    n_clusters_hidp     = n_clusters,
    hidp_definition     = "hidp at first observed BHPS/UKHLS wave (not hidp_last); composite key",
    optimizer_used      = optimizer_used,
    glmmTMB_version     = as.character(packageVersion("glmmTMB")),
    regime_6_included   = TRUE,
    ci_note             = "Wald CIs (estimate ± 1.96*SE); profile CIs unavailable for GLMM"
  ),
  convergence = list(
    convergence_code = convergence_code,
    convergence_msg  = convergence_msg,
    gradient_max     = if (is.na(gradient_max)) NULL else round(gradient_max, 8),
    converged        = isTRUE(convergence_code == 0L),
    singular_fit     = isTRUE(singular_fit),
    warnings         = if (length(warnings_fit) == 0L) list() else as.list(warnings_fit)
  ),
  random_effects = list(
    grouping_factor = "hh_group (survey_origin + '_' + hidp_first)",
    sigma2_u        = round(sigma2_u, 6),
    sigma_u         = round(sigma_u, 6),
    ICC             = round(icc, 6),
    ICC_formula     = "sigma2_u / (sigma2_u + pi^2/3)",
    singular_fit    = isTRUE(singular_fit)
  ),
  quasi_separation_diagnostic = sep_summary,
  coefficient_table  = coef_list,
  pseudo_r2          = pseudo_r2,
  buildup_comparison = buildup_comparison
)

write(toJSON(result, auto_unbox = TRUE, pretty = TRUE, na = "null"), OUT_PATH)
cat("Saved:", OUT_PATH, "\n")
cat("=== T1.20 Tier 2 GLMM complete ===\n")
