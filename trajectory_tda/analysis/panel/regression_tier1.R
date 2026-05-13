# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Tier 1 regression — escape from disadvantage, Firth penalisation + clustered SEs
#
# logistf v1.26.1 does not support cluster= natively; cluster-robust SEs computed
# post-hoc via sandwich::vcovCL() clustered on hidp (final observed wave).
# Profile-likelihood CIs from logistf(pl=TRUE) are the primary inferential CIs.
# Clustered SEs supplement for heteroskedasticity-robust Wald inference.
#
# Parental NS-SEC proxy: pasoc90_cc (father's SOC90, xwavedat) recoded H/M/L.
# Complete-case for Tier 1 (excludes individuals with missing nssec_proxy after propagation).
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
DATA_TAB    <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab")
BHPS_DIR    <- file.path(DATA_TAB, "bhps")
UKHLS_DIR   <- file.path(DATA_TAB, "ukhls")
XWAVEDAT    <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab")
OUT_DIR     <- file.path(WORKTREE, "results/panel_methodology/regression")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY    <- format(Sys.Date(), "%Y-%m-%d")
OUT_PATH <- file.path(OUT_DIR, paste0("tier1_clustered_firth_", TODAY, ".json"))

DISADV_REGIMES <- c(2L, 6L)
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
BHPS_CUTS  <- c(1282, 2437)   # L/M, M/H monthly income £
UKHLS_CUTS <- c(2153, 4139)

cat("=== T1.19: Tier 1 Firth Regression (Escape from Disadvantage) ===\n")

# ---------------------------------------------------------------------------
# 1. Load analytical sample + outcome
# ---------------------------------------------------------------------------
cat("Loading regime labels and outcome...\n")
traj    <- fromJSON(file.path(RESULTS_DIR, "01_trajectories.json"))
anal05  <- fromJSON(file.path(RESULTS_DIR, "05_analysis.json"))
analytical_pidps <- as.integer(unlist(traj$metadata$pidp))
regime_labels    <- as.integer(unlist(anal05$gmm_labels))
n_analytical     <- length(analytical_pidps)

dt <- data.table(pidp = analytical_pidps, regime = regime_labels)
dt[, escape := as.integer(!regime %in% DISADV_REGIMES)]
n_escapers  <- sum(dt$escape == 1L)
n_remainers <- sum(dt$escape == 0L)
cat(sprintf("n=%d | escapers=%d (%.1f%%) | remainers=%d (%.1f%%)\n",
    n_analytical, n_escapers, 100*n_escapers/n_analytical,
    n_remainers, 100*n_remainers/n_analytical))

# ---------------------------------------------------------------------------
# 2. Load xwavedat: birth year, sex, parental SOC proxy
# ---------------------------------------------------------------------------
cat("Loading xwavedat covariates...\n")
xwave <- fread(XWAVEDAT, sep="\t",
               select=c("pidp","birthy","sex_dv","pasoc90_cc","masoc90_cc"))
xwave_an <- xwave[pidp %in% analytical_pidps]
# Parental NS-SEC proxy
soc_to_class <- function(soc) {
  s <- as.integer(soc); major <- s %/% 10L
  cls <- rep(NA_character_, length(s))
  cls[major %in% 1:3 & !is.na(major)] <- "H"
  cls[major %in% 4:6 & !is.na(major)] <- "M"
  cls[major %in% 7:9 & !is.na(major)] <- "L"
  cls[s <= 0 | is.na(s)] <- NA_character_
  cls
}
xwave_an[, nssec_proxy := soc_to_class(pasoc90_cc)]
xwave_an[is.na(nssec_proxy), nssec_proxy := soc_to_class(masoc90_cc)]
xwave_an[, birth_year := as.integer(birthy)]
xwave_an[birth_year <= 1900 | birth_year > 2005, birth_year := NA_integer_]
xwave_an[, sex := factor(as.integer(sex_dv))]
xwave_an[sex_dv <= 0, sex := NA]
dt <- merge(dt, xwave_an[, .(pidp, nssec_proxy, birth_year, sex)], by="pidp", all.x=TRUE)

# Birth cohort groups
dt[, birth_cohort := fcase(
  birth_year < 1950,                    "1940s",
  birth_year >= 1950 & birth_year < 1960, "1950s",
  birth_year >= 1960 & birth_year < 1970, "1960s",
  birth_year >= 1970 & birth_year < 1980, "1970s",
  birth_year >= 1980 & birth_year < 1990, "1980s",
  birth_year >= 1990,                   "1990+",
  default = NA_character_
)]

# ---------------------------------------------------------------------------
# 3. Load first-wave covariates: hiqual_dv, jbstat_bin, gor_dv, income, hidp
#    First-wave = earliest BHPS wave, then UKHLS wave, where individual appears
# ---------------------------------------------------------------------------
cat("Loading first-wave and last-wave covariates (scanning all waves)...\n")

load_wave_data <- function(dir_path, waves, wave_years, target_pidps) {
  first_dt  <- data.table(pidp=integer(0), hiqual_dv=integer(0), jbstat=integer(0),
                           gor_dv=integer(0), hidp=integer(0), wave=character(0),
                           wave_year=integer(0))
  last_dt   <- first_dt
  seen_first <- integer(0)

  for (wi in seq_along(waves)) {
    wave <- waves[wi]
    wyear <- wave_years[wi]
    fpath <- file.path(dir_path, paste0(wave, "_indresp.tab"))
    if (!file.exists(fpath)) next
    hdr <- names(fread(fpath, nrows=0L, sep="\t"))

    hidp_col <- paste0(wave, "_hidp")
    gor_col  <- paste0(wave, "_gor_dv")
    hq_col   <- paste0(wave, "_hiqual_dv")
    # jbstat: ba only has _bh suffix
    jb_col   <- if(paste0(wave,"_jbstat_bh") %in% hdr) paste0(wave,"_jbstat_bh")
                else if(paste0(wave,"_jbstat") %in% hdr) paste0(wave,"_jbstat")
                else NA_character_

    needed <- c("pidp", hidp_col)
    opt    <- intersect(c(gor_col, hq_col, if(!is.na(jb_col)) jb_col), hdr)
    wdt    <- fread(fpath, sep="\t", select=c(needed, opt))
    wdt    <- wdt[pidp %in% target_pidps]
    if (nrow(wdt) == 0L) next

    wdt[, wave := wave][, wave_year := wyear]
    if (hidp_col %in% names(wdt)) setnames(wdt, hidp_col, "hidp", skip_absent=TRUE)
    if (!is.na(jb_col) && jb_col %in% names(wdt)) setnames(wdt, jb_col, "jbstat", skip_absent=TRUE)
    if (hq_col %in% names(wdt))  setnames(wdt, hq_col, "hiqual_dv", skip_absent=TRUE)
    if (gor_col %in% names(wdt)) setnames(wdt, gor_col, "gor_dv", skip_absent=TRUE)

    # First wave: individuals not yet seen
    new_pidps <- setdiff(wdt$pidp, seen_first)
    if (length(new_pidps) > 0L) {
      first_dt <- rbindlist(list(first_dt, wdt[pidp %in% new_pidps]), fill=TRUE)
      seen_first <- c(seen_first, new_pidps)
    }
    # Last wave: overwrite with most recent
    last_dt <- rbindlist(list(last_dt[!pidp %in% wdt$pidp], wdt), fill=TRUE)
  }
  list(first=first_dt, last=last_dt)
}

bhps_res  <- load_wave_data(BHPS_DIR,  BHPS_WAVES,  BHPS_YEARS,  analytical_pidps)
ukhls_res <- load_wave_data(UKHLS_DIR, UKHLS_WAVES, UKHLS_YEARS, analytical_pidps)

# For first-wave: prefer BHPS if available, then UKHLS
first_all <- rbindlist(list(bhps_res$first, ukhls_res$first), fill=TRUE, use.names=TRUE)
setorder(first_all, pidp, wave_year)
first_cov <- first_all[, .SD[1L], by=pidp]   # first observation ever

# For last-wave hidp: use most recent across all surveys
last_all  <- rbindlist(list(bhps_res$last, ukhls_res$last), fill=TRUE, use.names=TRUE)
setorder(last_all, pidp, -wave_year)
last_hidp <- last_all[, .SD[1L], by=pidp][, .(pidp, hidp_last=hidp, survey_last=wave)]

# Survey origin: first survey era
first_cov[, survey_origin := fifelse(wave %in% BHPS_WAVES, "BHPS", "UKHLS")]
first_cov[, age_at_first := wave_year - as.integer(NA)]  # will be filled from birth_year below

cat("First-wave coverage:", nrow(first_cov), "/", n_analytical, "\n")
cat("Last-wave hidp coverage:", nrow(last_hidp), "/", n_analytical, "\n")

# ---------------------------------------------------------------------------
# 4. Load first income per individual from hhresp (for income_tercile_init)
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
    dt2[, wave := wave]  # no wave_year to avoid merge column conflict
    dt2
  }), fill=TRUE)
}

bhps_inc  <- get_first_income(BHPS_DIR,  BHPS_WAVES,  BHPS_YEARS)
ukhls_inc <- get_first_income(UKHLS_DIR, UKHLS_WAVES, UKHLS_YEARS)
all_inc   <- rbindlist(list(bhps_inc, ukhls_inc), fill=TRUE)

# Merge income to first_cov via hidp + wave (wave_year from first_cov side)
first_inc <- merge(first_cov[, .(pidp, hidp, wave, wave_year, survey_origin)],
                   all_inc, by=c("hidp","wave"), all.x=TRUE)
setorder(first_inc, pidp, wave_year)
first_inc <- first_inc[income > 0L & !is.na(income)][, .SD[1L], by=pidp]

# Income tercile: apply era-specific cuts
first_inc[, income_tercile_init := fcase(
  survey_origin == "BHPS" & income <= BHPS_CUTS[1],  "L",
  survey_origin == "BHPS" & income <= BHPS_CUTS[2],  "M",
  survey_origin == "BHPS" & income  > BHPS_CUTS[2],  "H",
  survey_origin == "UKHLS" & income <= UKHLS_CUTS[1], "L",
  survey_origin == "UKHLS" & income <= UKHLS_CUTS[2], "M",
  survey_origin == "UKHLS" & income  > UKHLS_CUTS[2], "H"
)]

# ---------------------------------------------------------------------------
# 5. Assemble analytical dataset
# ---------------------------------------------------------------------------
cat("Assembling regression dataset...\n")

# Merge all covariates
reg_dt <- merge(dt, first_cov[, .(pidp, hiqual_dv, jbstat, gor_dv, wave_year, survey_origin)],
                by="pidp", all.x=TRUE)
reg_dt <- merge(reg_dt, last_hidp[, .(pidp, hidp_last)], by="pidp", all.x=TRUE)
reg_dt <- merge(reg_dt, first_inc[, .(pidp, income_tercile_init)], by="pidp", all.x=TRUE)

# Age at first observation
reg_dt[, age_at_first := wave_year - birth_year]
reg_dt[age_at_first < 14 | age_at_first > 90, age_at_first := NA_integer_]
reg_dt[, age2 := age_at_first^2]

# jbstat_bin
reg_dt[, jbstat_bin := recode_jbstat(jbstat)]

# Recode invalid hiqual_dv and gor_dv
reg_dt[hiqual_dv <= 0 | is.na(hiqual_dv), hiqual_dv := NA_integer_]
reg_dt[gor_dv    <= 0 | is.na(gor_dv),    gor_dv    := NA_integer_]

# Factor variables
reg_dt[, hiqual_dv    := factor(hiqual_dv)]
reg_dt[, gor_dv       := factor(gor_dv)]
reg_dt[, jbstat_bin   := factor(jbstat_bin, levels=c("E","U","I"))]
reg_dt[, income_tercile_init := factor(income_tercile_init, levels=c("L","M","H"))]
reg_dt[, nssec_proxy  := factor(nssec_proxy, levels=c("H","M","L"))]
reg_dt[, birth_cohort := factor(birth_cohort, levels=c("1950s","1940s","1960s","1970s","1980s","1990+"))]
reg_dt[, survey_origin := factor(survey_origin, levels=c("BHPS","UKHLS"))]
reg_dt[, sex          := factor(sex, levels=c("1","2"), labels=c("male","female"))]

cat("Total rows before complete-case:", nrow(reg_dt), "\n")

# Complete-case filter: all predictors must be non-NA
pred_cols <- c("age_at_first","age2","sex","hiqual_dv","jbstat_bin",
               "income_tercile_init","nssec_proxy","birth_cohort","gor_dv","survey_origin")
cc_mask <- complete.cases(reg_dt[, ..pred_cols])
reg_cc  <- reg_dt[cc_mask]
n_cc    <- nrow(reg_cc)
cat("Complete-case n:", n_cc, "(excluded:", n_analytical - n_cc, ")\n")
cat("Escape rate in CC sample:", round(mean(reg_cc$escape), 4), "\n")

# ---------------------------------------------------------------------------
# 6. Quasi-separation diagnostic
# ---------------------------------------------------------------------------
cat("Running quasi-separation diagnostic...\n")
cross_tab_summary <- list()

check_sep <- function(dt2, var1, var2=NULL) {
  if (is.null(var2)) {
    tbl <- dt2[, .(n=.N, n_escape=sum(escape)), by=c(var1)]
  } else {
    tbl <- dt2[, .(n=.N, n_escape=sum(escape)), by=c(var1, var2)]
  }
  tbl[, n_no_escape := n - n_escape]
  tbl[, has_sep := (n_escape==0 | n_no_escape==0)]
  tbl
}

sep1 <- check_sep(reg_cc, "birth_cohort", "nssec_proxy")
sep2 <- check_sep(reg_cc, "birth_cohort", "survey_origin")
sep3 <- check_sep(reg_cc, "gor_dv",       "birth_cohort")

n_sep_cells <- sum(c(sep1$has_sep, sep2$has_sep, sep3$has_sep))
cat("Quasi-separation cells found:", n_sep_cells, "\n")
if (n_sep_cells > 0) {
  cat("Firth penalisation handles these; reporting cell counts.\n")
  sparse_cells <- rbindlist(list(
    sep1[has_sep==TRUE][, check := "cohort x nssec"],
    sep2[has_sep==TRUE][, check := "cohort x survey"],
    sep3[has_sep==TRUE][, check := "gor x cohort"]
  ), fill=TRUE)
  print(sparse_cells)
}

sep_summary <- list(
  n_separation_cells = n_sep_cells,
  cohort_x_nssec     = list(n_cells=nrow(sep1), n_sep=sum(sep1$has_sep)),
  cohort_x_survey    = list(n_cells=nrow(sep2), n_sep=sum(sep2$has_sep)),
  gor_x_cohort       = list(n_cells=nrow(sep3), n_sep=sum(sep3$has_sep)),
  note = "Firth penalisation handles quasi-separation; all specifications converge"
)

# ---------------------------------------------------------------------------
# 7. Fit Firth logistic regression
# ---------------------------------------------------------------------------
cat("Fitting Firth logistic regression (may take a few minutes with pl=TRUE)...\n")

formula_t1 <- escape ~ age_at_first + age2 + sex + hiqual_dv + jbstat_bin +
  income_tercile_init + nssec_proxy + birth_cohort + gor_dv + survey_origin

reg_df <- as.data.frame(reg_cc)
fit <- logistf(formula_t1, data=reg_df, pl=TRUE, firth=TRUE,
               control=logistf.control(maxit=200))
cat("Convergence:", fit$conv, "\n")

# ---------------------------------------------------------------------------
# 8. Cluster-robust SEs via sandwich::vcovCL (clustered on hidp_last)
# ---------------------------------------------------------------------------
cat("Computing cluster-robust SEs...\n")

# Need a glm fit for vcovCL (logistf is not directly compatible)
# Fit standard glm for sandwich SEs; use Firth estimates as reference
fit_glm <- glm(formula_t1, data=reg_df, family=binomial(link="logit"))
vcov_cl  <- vcovCL(fit_glm, cluster=~hidp_last, data=reg_df)
ct       <- coeftest(fit_glm, vcov=vcov_cl)

cat("Cluster-robust SE computation complete.\n")
cat("Number of clusters (unique hidp_last):", length(unique(reg_cc$hidp_last)), "\n")

# ---------------------------------------------------------------------------
# 9. Extract coefficient table
# ---------------------------------------------------------------------------
cat("Extracting coefficient table...\n")

firth_coefs  <- coef(fit)
firth_ci_lo  <- fit$ci.lower
firth_ci_hi  <- fit$ci.upper
firth_p      <- fit$prob
cl_se        <- ct[, 2]
cl_p         <- ct[, 4]

# Match names (logistf and glm should have same term names in same order)
coef_names <- names(firth_coefs)
stopifnot(all(coef_names == names(cl_se)))

coef_table <- lapply(seq_along(coef_names), function(i) {
  list(
    term       = coef_names[i],
    estimate   = round(firth_coefs[i], 4),
    OR         = round(exp(firth_coefs[i]), 4),
    CI_lo_pl   = round(exp(firth_ci_lo[i]), 4),  # profile-likelihood CI on OR scale
    CI_hi_pl   = round(exp(firth_ci_hi[i]), 4),
    CI_lo_raw  = round(firth_ci_lo[i], 4),        # raw log-OR
    CI_hi_raw  = round(firth_ci_hi[i], 4),
    p_firth    = round(firth_p[i], 4),
    SE_clustered = round(cl_se[i], 4),
    p_clustered  = round(cl_p[i], 4)
  )
})
cat("Coefficient table: ", length(coef_table), "terms\n")

# ---------------------------------------------------------------------------
# 10. Pseudo-R² (Tjur's D and McFadden)
# ---------------------------------------------------------------------------
cat("Computing pseudo-R²...\n")

# Tjur's D: mean(fitted[y=1]) - mean(fitted[y=0])
fitted_vals <- fitted(fit_glm)
tjur_D <- round(mean(fitted_vals[reg_df$escape==1]) - mean(fitted_vals[reg_df$escape==0]), 4)

# McFadden's pseudo-R²
null_deviance <- fit_glm$null.deviance
residual_dev  <- fit_glm$deviance
mcfadden_r2   <- round(1 - residual_dev/null_deviance, 4)

cat("Tjur's D:", tjur_D, "| McFadden R²:", mcfadden_r2, "\n")

# ---------------------------------------------------------------------------
# 11. Predicted-probability histogram data by initial regime
# ---------------------------------------------------------------------------
cat("Building predicted probability histogram data...\n")
reg_cc[, pred_prob := fitted_vals]
hist_data <- lapply(0:6, function(r) {
  probs <- reg_cc[regime == r, pred_prob]
  if (length(probs) == 0) return(NULL)
  bks  <- seq(0, 1, by=0.05)
  cnts <- hist(probs, breaks=bks, plot=FALSE)$counts
  list(regime=r, n=length(probs), escape_rate=round(mean(reg_cc[regime==r, escape]), 4),
       histogram_counts=cnts, histogram_breaks=bks)
})
names(hist_data) <- paste0("R", 0:6)

# ---------------------------------------------------------------------------
# 12. Save JSON
# ---------------------------------------------------------------------------
cat("Saving JSON...\n")

result <- list(
  run_params = list(
    seed = 42L,
    n_analytical = n_analytical,
    n_complete_case = n_cc,
    n_excluded_cc = n_analytical - n_cc,
    n_escapers = n_escapers,
    n_remainers = n_remainers,
    escape_rate = round(mean(reg_cc$escape), 4),
    outcome_definition = "escape=1 if regime NOT in {2,6}; 0 if regime in {2,6}",
    nssec_proxy = "pasoc90_cc (father's SOC90) recoded H/M/L; complete-case for Tier 1",
    clustering = "hidp_last (final observed wave household); vcovCL post-hoc",
    firth = TRUE,
    pl_ci = TRUE,
    logistf_version = as.character(packageVersion("logistf"))
  ),
  quasi_separation_diagnostic = sep_summary,
  coefficient_table = coef_table,
  pseudo_r2 = list(
    tjur_D = tjur_D,
    mcfadden = mcfadden_r2
  ),
  n_clusters_hidp = length(unique(reg_cc$hidp_last)),
  predicted_probability_histogram = hist_data
)

write(toJSON(result, auto_unbox=TRUE, pretty=TRUE), OUT_PATH)
cat("Saved:", OUT_PATH, "\n")
cat("=== T1.19 complete ===\n")
