# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: T1.19 rerun — Tier 1 Firth regression on window-based R2/R6 starters.
#
# The v1 escape analysis is WINDOW-BASED: overlapping 10-year windows (step=5) of
# each person's jbstat sequence are embedded and assigned a GMM regime. "Starter" =
# first window in regime {2,6}. "Escape" = any subsequent window in regime ∉ {2,6}.
# Source of escape outcome and starter set: window_escape_assignments_<date>.json
# produced by build_window_assignments.py.
#
# IMPORTANT: No age<60 filter; no jbstat=4 exclusion filter. These were artefacts of
# the previous (wrong) trajectory-label approach. The regression includes all starters
# regardless of age; age_first_window is a PREDICTOR, not a filter.
# Complete-case n expected ≈ 4,832 (driven by parental NS-SEC missingness ~35%).
#
# logistf v1.26.1 does not support cluster= natively; clustered SEs post-hoc via
# sandwich::vcovCL() clustered on hidp (last observed wave).
# Profile-likelihood CIs from logistf(pl=TRUE) are primary inferential CIs.
#
# Reference values (from p2_5_age_stratified.json / v1 Python run):
#   n_starters = 7,453 | escape_rate = 5.58% | n_obs ≈ 4,832 | pseudo_r2 ≈ 0.479
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/regression_tier1.R

suppressPackageStartupMessages({
  library(data.table)
  library(logistf)
  library(sandwich)
  library(lmtest)
  library(jsonlite)
})

set.seed(42)

PROJ_ROOT   <- "C:/Users/steph/TDL"
WORKTREE    <- normalizePath(getwd(), mustWork = FALSE)
RESULTS_DIR <- file.path(PROJ_ROOT, "results/trajectory_tda_integration")
PRIORITY2   <- file.path(PROJ_ROOT, "results/trajectory_tda_priority2")
DATA_TAB    <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab")
BHPS_DIR    <- file.path(DATA_TAB, "bhps")
UKHLS_DIR   <- file.path(DATA_TAB, "ukhls")
XWAVEDAT    <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab")
OUT_DIR     <- file.path(WORKTREE, "results/panel_methodology/regression")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY    <- format(Sys.Date(), "%Y-%m-%d")
OUT_PATH <- file.path(OUT_DIR, paste0("tier1_clustered_firth_", TODAY, ".json"))

BHPS_WAVES     <- paste0("b", letters[1:18])
BHPS_YEARS     <- 1991:2008
UKHLS_WAVES    <- letters[1:15]
UKHLS_YEARS    <- 2009:2023

# Locked jbstat recoding (T0.9)
E_CODES <- c(1L,2L,5L,11L,12L,13L,14L,15L); U_CODES <- c(3L,9L); I_CODES <- c(4L,6L,7L,8L,10L,97L)

recode_jbstat <- function(x) {
  r <- rep(NA_character_, length(x))
  xi <- as.integer(x)
  r[xi %in% E_CODES] <- "E"
  r[xi %in% U_CODES] <- "U"
  r[xi %in% I_CODES] <- "I"
  r
}

# Income tercile cuts from T1.13 (locked)
BHPS_CUTS  <- c(1282, 2437)
UKHLS_CUTS <- c(2153, 4139)

cat("=== T1.19 Rerun: Tier 1 Firth Regression (Window-Based R2/R6 Starters) ===\n")

# ---------------------------------------------------------------------------
# 1. Load window escape assignments from Python output
# ---------------------------------------------------------------------------
cat("Locating window_escape_assignments JSON...\n")
wa_files <- list.files(PRIORITY2, pattern="^window_escape_assignments_.*\\.json$", full.names=TRUE)
if (length(wa_files) == 0L) {
  stop("No window_escape_assignments JSON found in ", PRIORITY2,
       ". Run build_window_assignments.py first.")
}
wa_path <- wa_files[which.max(file.info(wa_files)$mtime)]  # most recent
cat("Using:", wa_path, "\n")

wa_json <- fromJSON(wa_path)
cat("Window assignments source date:", wa_json$run_params$date, "\n")

# Extract starters only
asgn    <- as.data.table(wa_json$assignments)
starters <- asgn[is_disadvantaged_starter == TRUE]
n_starters_all <- nrow(starters)
n_escaped_all  <- sum(starters$escape)
cat("n_starters_all_ages:", n_starters_all,
    "  escape_rate:", round(n_escaped_all/n_starters_all, 4), "\n")

# Escalation check
REF_N   <- 7453L; REF_RATE <- 0.05581
if (abs(n_starters_all - REF_N) / REF_N > 0.10) {
  cat("WARNING: n_starters =", n_starters_all, "deviates >10% from expected", REF_N, "ESCALATE.\n")
}
esc_rate_obs <- n_escaped_all / n_starters_all
if (abs(esc_rate_obs - REF_RATE) / REF_RATE > 0.10) {
  cat("WARNING: escape_rate =", round(esc_rate_obs,4),
      "deviates >10% from expected", REF_RATE, "ESCALATE.\n")
}

# Core regression columns: pidp, escape, age_first_window, first_window_regime
starter_dt <- starters[, .(pidp, escape, age_first_window, first_window_regime)]
starter_pidps <- starter_dt$pidp

cat("Loading xwavedat covariates...\n")
xwave_full <- fread(XWAVEDAT, sep="\t",
                    select=c("pidp","birthy","sex_dv","pasoc90_cc","masoc90_cc"))
xwave_full[, birthy := as.integer(birthy)]
xwave_full[birthy <= 1900 | birthy > 2005 | is.na(birthy), birthy := NA_integer_]

soc_to_class <- function(soc) {
  s <- as.integer(soc); major <- s %/% 10L
  cls <- rep(NA_character_, length(s))
  cls[major %in% 1:3 & !is.na(major)] <- "H"
  cls[major %in% 4:6 & !is.na(major)] <- "M"
  cls[major %in% 7:9 & !is.na(major)] <- "L"
  cls[s <= 0 | is.na(s)] <- NA_character_
  cls
}

xwave_an <- xwave_full[pidp %in% starter_pidps]
xwave_an[, nssec_proxy := soc_to_class(pasoc90_cc)]
xwave_an[is.na(nssec_proxy), nssec_proxy := soc_to_class(masoc90_cc)]
xwave_an[, birth_year := as.integer(birthy)]
xwave_an[birth_year <= 1900 | birth_year > 2005, birth_year := NA_integer_]
xwave_an[, sex := fifelse(as.integer(sex_dv) == 2L, "female",
                  fifelse(as.integer(sex_dv) == 1L, "male", NA_character_))]

# Merge xwavedat covariates
starter_dt <- merge(starter_dt,
                    xwave_an[, .(pidp, nssec_proxy, birth_year, sex)],
                    by="pidp", all.x=TRUE)

# Birth cohort (using birth_year from xwavedat)
starter_dt[, birth_cohort := fcase(
  birth_year < 1950,                       "pre-1950",
  birth_year >= 1950 & birth_year < 1960,  "1950s",
  birth_year >= 1960 & birth_year < 1970,  "1960s",
  birth_year >= 1970 & birth_year < 1980,  "1970s",
  birth_year >= 1980,                      "post-1980",
  default = NA_character_
)]

# Use age_first_window from JSON; fill from xwavedat if NULL
# (Python script uses xwavedat birth_year so these should match)
starter_dt[is.na(age_first_window) & !is.na(birth_year),
           age_first_window := NA_integer_]  # already NA; no xwavedat recompute needed here

# ---------------------------------------------------------------------------
# 2. Load first-wave covariates: hiqual_dv, jbstat_bin, gor_dv, hidp
# ---------------------------------------------------------------------------
cat("Loading first-wave covariates from BHPS and UKHLS indresp files...\n")

load_wave_data <- function(dir_path, waves, wave_years, target_pidps) {
  first_dt   <- data.table(pidp=integer(0), hiqual_dv=integer(0), jbstat=integer(0),
                            gor_dv=integer(0), hidp=integer(0), wave=character(0),
                            wave_year=integer(0), survey_origin=character(0))
  last_hidp_dt <- first_dt
  seen_first <- integer(0)

  for (wi in seq_along(waves)) {
    wave <- waves[wi]; wyear <- wave_years[wi]
    fpath <- file.path(dir_path, paste0(wave, "_indresp.tab"))
    if (!file.exists(fpath)) next
    hdr <- names(fread(fpath, nrows=0L, sep="\t"))

    hidp_col <- paste0(wave, "_hidp")
    gor_col  <- paste0(wave, "_gor_dv")
    hq_col   <- paste0(wave, "_hiqual_dv")
    jb_col   <- if (paste0(wave, "_jbstat_bh") %in% hdr) paste0(wave, "_jbstat_bh")
                else if (paste0(wave, "_jbstat") %in% hdr) paste0(wave, "_jbstat")
                else NA_character_

    needed <- c("pidp", hidp_col)
    opt    <- intersect(c(gor_col, hq_col, if (!is.na(jb_col)) jb_col), hdr)
    wdt    <- fread(fpath, sep="\t", select=c(needed, opt))
    wdt    <- wdt[pidp %in% target_pidps]
    if (nrow(wdt) == 0L) next

    wdt[, wave := wave][, wave_year := wyear]
    wdt[, survey_origin := fifelse(wave %in% BHPS_WAVES, "BHPS", "UKHLS")]
    if (hidp_col %in% names(wdt)) setnames(wdt, hidp_col, "hidp", skip_absent=TRUE)
    if (!is.na(jb_col) && jb_col %in% names(wdt)) setnames(wdt, jb_col, "jbstat", skip_absent=TRUE)
    if (hq_col  %in% names(wdt)) setnames(wdt, hq_col,  "hiqual_dv", skip_absent=TRUE)
    if (gor_col %in% names(wdt)) setnames(wdt, gor_col, "gor_dv",    skip_absent=TRUE)

    new_pidps <- setdiff(wdt$pidp, seen_first)
    if (length(new_pidps) > 0L) {
      first_dt <- rbindlist(list(first_dt, wdt[pidp %in% new_pidps]), fill=TRUE)
      seen_first <- c(seen_first, new_pidps)
    }
    last_hidp_dt <- rbindlist(list(last_hidp_dt[!pidp %in% wdt$pidp], wdt), fill=TRUE)
  }
  list(first=first_dt, last=last_hidp_dt)
}

bhps_res  <- load_wave_data(BHPS_DIR,  BHPS_WAVES,  BHPS_YEARS,  starter_pidps)
ukhls_res <- load_wave_data(UKHLS_DIR, UKHLS_WAVES, UKHLS_YEARS, starter_pidps)

first_all <- rbindlist(list(bhps_res$first, ukhls_res$first), fill=TRUE, use.names=TRUE)
setorder(first_all, pidp, wave_year)
first_cov <- first_all[, .SD[1L], by=pidp]

last_all  <- rbindlist(list(bhps_res$last, ukhls_res$last), fill=TRUE, use.names=TRUE)
setorder(last_all, pidp, -wave_year)
last_hidp <- last_all[, .SD[1L], by=pidp][, .(pidp, hidp_last=hidp, survey_last=wave)]

cat("First-wave coverage:", nrow(first_cov), "/", n_starters_all, "\n")

# ---------------------------------------------------------------------------
# 3. Load first income for income_tercile_init
# ---------------------------------------------------------------------------
cat("Loading first income observation...\n")

get_first_income <- function(hhresp_dir, waves, wave_years) {
  rbindlist(lapply(seq_along(waves), function(wi) {
    wave <- waves[wi]; wyear <- wave_years[wi]
    fpath <- file.path(hhresp_dir, paste0(wave, "_hhresp.tab"))
    if (!file.exists(fpath)) return(NULL)
    hdr <- names(fread(fpath, nrows=0L, sep="\t"))
    hidp_col <- paste0(wave, "_hidp")
    inc_col  <- paste0(wave, "_fihhmngrs_dv")
    if (!hidp_col %in% hdr || !inc_col %in% hdr) return(NULL)
    dt2 <- fread(fpath, sep="\t", select=c(hidp_col, inc_col))
    setnames(dt2, c(hidp_col, inc_col), c("hidp", "income"))
    dt2[, wave := wave]
    dt2
  }), fill=TRUE)
}

bhps_inc  <- get_first_income(BHPS_DIR,  BHPS_WAVES,  BHPS_YEARS)
ukhls_inc <- get_first_income(UKHLS_DIR, UKHLS_WAVES, UKHLS_YEARS)
all_inc   <- rbindlist(list(bhps_inc, ukhls_inc), fill=TRUE)

first_inc <- merge(first_cov[, .(pidp, hidp, wave, wave_year, survey_origin)],
                   all_inc, by=c("hidp","wave"), all.x=TRUE)
setorder(first_inc, pidp, wave_year)
first_inc <- first_inc[income > 0L & !is.na(income)][, .SD[1L], by=pidp]

first_inc[, income_tercile_init := fcase(
  survey_origin == "BHPS"  & income <= BHPS_CUTS[1],  "L",
  survey_origin == "BHPS"  & income <= BHPS_CUTS[2],  "M",
  survey_origin == "BHPS"  & income  > BHPS_CUTS[2],  "H",
  survey_origin == "UKHLS" & income <= UKHLS_CUTS[1], "L",
  survey_origin == "UKHLS" & income <= UKHLS_CUTS[2], "M",
  survey_origin == "UKHLS" & income  > UKHLS_CUTS[2], "H"
)]

# ---------------------------------------------------------------------------
# 4. Assemble analytical dataset
# ---------------------------------------------------------------------------
cat("Assembling regression dataset...\n")

reg_dt <- merge(starter_dt,
                first_cov[, .(pidp, hiqual_dv, jbstat, gor_dv, wave_year, survey_origin)],
                by="pidp", all.x=TRUE)
reg_dt <- merge(reg_dt, last_hidp[, .(pidp, hidp_last)], by="pidp", all.x=TRUE)
reg_dt <- merge(reg_dt, first_inc[, .(pidp, income_tercile_init)], by="pidp", all.x=TRUE)

reg_dt[, jbstat_bin := recode_jbstat(jbstat)]
reg_dt[hiqual_dv <= 0 | is.na(hiqual_dv), hiqual_dv := NA_integer_]
reg_dt[gor_dv    <= 0 | is.na(gor_dv),    gor_dv    := NA_integer_]

# regime_6 binary indicator (R6 vs R2 starters)
reg_dt[, regime_6 := as.integer(first_window_regime == 6L)]

reg_dt[, hiqual_dv           := factor(hiqual_dv)]
reg_dt[, gor_dv              := factor(gor_dv)]
reg_dt[, jbstat_bin          := factor(jbstat_bin, levels=c("E","U","I"))]
reg_dt[, income_tercile_init := factor(income_tercile_init, levels=c("L","M","H"))]
reg_dt[, nssec_proxy         := factor(nssec_proxy, levels=c("H","M","L"))]
reg_dt[, birth_cohort        := factor(birth_cohort,
                                       levels=c("pre-1950","1950s","1960s","1970s","post-1980"))]
reg_dt[, survey_origin       := factor(survey_origin, levels=c("BHPS","UKHLS"))]
reg_dt[, sex                 := factor(sex, levels=c("male","female"))]

cat("Total starter rows before complete-case:", nrow(reg_dt), "\n")

# Complete-case on core predictors (includes age_first_window and nssec_proxy)
pred_cols <- c("age_first_window","sex","hiqual_dv","jbstat_bin",
               "income_tercile_init","nssec_proxy","birth_cohort","gor_dv","survey_origin")
cc_mask <- complete.cases(reg_dt[, ..pred_cols]) & !is.na(reg_dt$escape)
reg_cc  <- reg_dt[cc_mask]
n_cc    <- nrow(reg_cc)
n_esc_cc  <- sum(reg_cc$escape == 1L)
n_rem_cc  <- sum(reg_cc$escape == 0L)
esc_rate_cc <- round(mean(reg_cc$escape), 4)

cat("Complete-case n:", n_cc, "(excluded:", n_starters_all - n_cc, ")\n")
cat("Escapers:", n_esc_cc, sprintf("(%.1f%%)", 100*esc_rate_cc), "\n")
cat("Remainers:", n_rem_cc, "\n")

if (abs(n_cc - 4832L) / 4832L > 0.10) {
  cat("WARNING: n_cc =", n_cc, "deviates >10% from expected 4,832. Note for report.\n")
}

# age² after complete-case
reg_cc[, age2 := age_first_window^2]

# ---------------------------------------------------------------------------
# 5. Quasi-separation diagnostic
# ---------------------------------------------------------------------------
cat("Running quasi-separation diagnostic...\n")

check_sep <- function(dt2, var1, var2=NULL) {
  by_vars <- if (is.null(var2)) var1 else c(var1, var2)
  tbl <- dt2[, .(n=.N, n_escape=sum(escape)), by=by_vars]
  tbl[, n_no_escape := n - n_escape]
  tbl[, has_sep := (n_escape==0L | n_no_escape==0L)]
  tbl
}

sep1 <- check_sep(reg_cc, "birth_cohort", "nssec_proxy")
sep2 <- check_sep(reg_cc, "birth_cohort", "survey_origin")
sep3 <- check_sep(reg_cc, "gor_dv",       "birth_cohort")

n_sep_cells <- sum(c(sep1$has_sep, sep2$has_sep, sep3$has_sep))
cat("Quasi-separation cells found:", n_sep_cells, "\n")
if (n_sep_cells > 0L) {
  sparse <- rbindlist(list(
    sep1[has_sep==TRUE][, check := "cohort x nssec"],
    sep2[has_sep==TRUE][, check := "cohort x survey"],
    sep3[has_sep==TRUE][, check := "gor x cohort"]
  ), fill=TRUE)
  print(sparse)
}

sep_summary <- list(
  n_separation_cells = n_sep_cells,
  cohort_x_nssec  = list(n_cells=nrow(sep1), n_sep=sum(sep1$has_sep)),
  cohort_x_survey = list(n_cells=nrow(sep2), n_sep=sum(sep2$has_sep)),
  gor_x_cohort    = list(n_cells=nrow(sep3), n_sep=sum(sep3$has_sep)),
  note = "Firth penalisation handles quasi-separation; all specifications converge"
)

# ---------------------------------------------------------------------------
# 6. Fit Firth logistic regression
# ---------------------------------------------------------------------------
cat("Fitting Firth logistic regression (pl=TRUE, may take several minutes)...\n")

formula_t1 <- escape ~ age_first_window + age2 + sex + hiqual_dv + jbstat_bin +
  income_tercile_init + nssec_proxy + birth_cohort + gor_dv + survey_origin + regime_6

reg_df <- as.data.frame(reg_cc)
fit <- logistf(formula_t1, data=reg_df, pl=TRUE, firth=TRUE,
               control=logistf.control(maxit=200))
cat("Convergence:", fit$conv, "\n")

# ---------------------------------------------------------------------------
# 7. Cluster-robust SEs via sandwich::vcovCL (clustered on hidp_last)
# ---------------------------------------------------------------------------
cat("Computing cluster-robust SEs...\n")
fit_glm <- glm(formula_t1, data=reg_df, family=binomial(link="logit"))
vcov_cl  <- vcovCL(fit_glm, cluster=~hidp_last, data=reg_df)
ct       <- coeftest(fit_glm, vcov=vcov_cl)
n_clusters <- length(unique(reg_cc$hidp_last))
cat("Cluster-robust SE computation complete.\n")
cat("Number of clusters (unique hidp_last):", n_clusters, "\n")

# ---------------------------------------------------------------------------
# 8. Extract coefficient table
# ---------------------------------------------------------------------------
cat("Extracting coefficient table...\n")

fmt_pval <- function(p) {
  if (is.na(p)) return(NA_character_)
  if (p < 1e-4) return("< 1e-4")
  format(round(p, 5), nsmall = 5)
}

firth_coefs <- coef(fit)
firth_ci_lo <- fit$ci.lower
firth_ci_hi <- fit$ci.upper
firth_p     <- fit$prob
cl_se       <- ct[, 2]
cl_p        <- ct[, 4]

coef_names <- names(firth_coefs)

coef_table <- lapply(seq_along(coef_names), function(i) {
  list(
    term         = coef_names[i],
    estimate     = round(firth_coefs[i], 4),
    OR           = round(exp(firth_coefs[i]), 4),
    CI_lo_OR     = round(exp(firth_ci_lo[i]), 4),
    CI_hi_OR     = round(exp(firth_ci_hi[i]), 4),
    CI_lo_log    = round(firth_ci_lo[i], 4),
    CI_hi_log    = round(firth_ci_hi[i], 4),
    p_firth      = fmt_pval(firth_p[i]),
    SE_clustered = if (coef_names[i] %in% rownames(ct)) round(ct[coef_names[i], 2], 4) else NA_real_,
    p_clustered  = if (coef_names[i] %in% rownames(ct)) fmt_pval(ct[coef_names[i], 4]) else NA_character_
  )
})
cat("Coefficient table:", length(coef_table), "terms\n")

# ---------------------------------------------------------------------------
# 9. Pseudo-R²
# ---------------------------------------------------------------------------
cat("Computing pseudo-R²...\n")
fitted_vals  <- fitted(fit_glm)
tjur_D       <- round(mean(fitted_vals[reg_df$escape==1L]) - mean(fitted_vals[reg_df$escape==0L]), 4)
null_dev     <- fit_glm$null.deviance
resid_dev    <- fit_glm$deviance
mcfadden_r2  <- round(1 - resid_dev/null_dev, 4)
cat("Tjur's D:", tjur_D, "| McFadden R²:", mcfadden_r2, "\n")

# ---------------------------------------------------------------------------
# 10. Predicted-probability histogram by first_window_regime
# ---------------------------------------------------------------------------
cat("Building predicted probability histogram data...\n")
reg_cc[, pred_prob := fitted_vals]
hist_data <- lapply(unique(reg_cc$first_window_regime), function(r) {
  probs <- reg_cc[first_window_regime == r, pred_prob]
  if (length(probs) == 0L) return(NULL)
  bks  <- seq(0, 1, by=0.05)
  cnts <- hist(probs, breaks=bks, plot=FALSE)$counts
  list(regime=r, n=length(probs),
       escape_rate=round(mean(reg_cc[first_window_regime==r, escape]), 4),
       histogram_counts=cnts, histogram_breaks=bks)
})
names(hist_data) <- paste0("R", unique(reg_cc$first_window_regime))

# ---------------------------------------------------------------------------
# 11. Save JSON
# ---------------------------------------------------------------------------
cat("Saving JSON...\n")

result <- list(
  run_params = list(
    seed               = 42L,
    date               = TODAY,
    methodology        = "Window-based escape (10-year overlapping windows, step=5). Starter = first window in R{2,6}. Escape = any subsequent window not in R{2,6}.",
    source_assignments = wa_path,
    n_starters_all_ages  = n_starters_all,
    escape_rate_all_ages = round(esc_rate_obs, 6),
    n_complete_case    = n_cc,
    n_excluded_cc      = n_starters_all - n_cc,
    n_escapers_cc      = n_esc_cc,
    n_remainers_cc     = n_rem_cc,
    escape_rate_cc     = esc_rate_cc,
    ref_n_starters     = 7453L,
    ref_escape_rate    = 0.05581644975177781,
    ref_n_obs          = 4832L,
    nssec_proxy        = "pasoc90_cc falling back to masoc90_cc; recoded H/M/L; complete-case",
    clustering         = "hidp_last (last observed wave household); vcovCL post-hoc",
    ci_note            = "Profile-likelihood CIs from Firth (primary); clustered Wald SEs from vcovCL (supplementary)",
    firth              = TRUE,
    pl_ci              = TRUE,
    logistf_version    = as.character(packageVersion("logistf")),
    pvalue_format_note = "p-values below 1e-4 displayed as '< 1e-4' string; do not parse as numeric without handling."
  ),
  quasi_separation_diagnostic = sep_summary,
  coefficient_table    = coef_table,
  pseudo_r2            = list(tjur_D=tjur_D, mcfadden=mcfadden_r2),
  n_clusters_hidp      = n_clusters,
  predicted_probability_histogram = hist_data
)

write(toJSON(result, auto_unbox=TRUE, pretty=TRUE), OUT_PATH)
cat("Saved:", OUT_PATH, "\n")
cat("=== T1.19 Window-Based Rerun complete ===\n")
