# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: 20-imputation MICE (PMM) for fihhmngrs_dv within BHPS and UKHLS eras separately

# Verified variable names:
#   Income:   {wave}_fihhmngrs_dv  (hhresp, wave-prefixed, both BHPS and UKHLS)
#   hidp:     {wave}_hidp          (both)
#   hhsize:   {wave}_hhsize        (both)
#   gor_dv:   {wave}_gor_dv        (indresp, both)
#   jbstat:   {wave}_jbstat_bh (ba only) / {wave}_jbstat (bb-br, UKHLS a-o)
#
# Locked codings (T0.9): E={1,2,5,11,12,13,14,15}, U={3,9}, I={4,6,7,8,10,97}
# Locked income tercile (T0.10): within-era boundaries (BHPS and UKHLS separately)
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/mice_income.R

suppressPackageStartupMessages({
  library(mice)
  library(dplyr)
  library(jsonlite)
  library(data.table)
})

set.seed(42)

WORKTREE    <- normalizePath(getwd(), mustWork = FALSE)
PROJ_ROOT   <- Sys.getenv("TDL_ROOT", unset = WORKTREE)
DATA_TAB    <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab")
BHPS_DIR    <- file.path(DATA_TAB, "bhps")
UKHLS_DIR   <- file.path(DATA_TAB, "ukhls")
RESULTS_DIR <- file.path(PROJ_ROOT, "results/trajectory_tda_integration")
OUT_DIR     <- file.path(WORKTREE, "results/panel_methodology/imputation")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY    <- format(Sys.Date(), "%Y-%m-%d")
OUT_PATH <- file.path(OUT_DIR, paste0("mice_income_diagnostics_", TODAY, ".json"))
M_IMPUTATIONS <- 20L

cat("=== T1.14: MICE for Income (Within-Era Imputation) ===\n")

# ---------------------------------------------------------------------------
# 1. Load analytical sample pidps and regime labels
# ---------------------------------------------------------------------------
cat("Loading analytical sample and regime labels...\n")
traj    <- fromJSON(file.path(RESULTS_DIR, "01_trajectories.json"))
anal_05 <- fromJSON(file.path(RESULTS_DIR, "05_analysis.json"))
analytical_pidps <- as.integer(unlist(traj$metadata$pidp))
regime_labels    <- as.integer(unlist(anal_05$gmm_labels))   # R0-R6, one per individual
n_analytical     <- length(analytical_pidps)
stopifnot(length(regime_labels) == n_analytical)
cat("n =", n_analytical, "| regimes:", sort(unique(regime_labels)), "\n")

# ---------------------------------------------------------------------------
# 2. Locked jbstat recoding (T0.9)
# ---------------------------------------------------------------------------
E_CODES <- c(1L,2L,5L,11L,12L,13L,14L,15L); U_CODES <- c(3L,9L); I_CODES <- c(4L,6L,7L,8L,10L,97L)
recode_jbstat <- function(x) {
  x <- as.integer(x)
  r <- rep(NA_integer_, length(x))
  r[x %in% E_CODES] <- 1L   # E=1, U=2, I=3 as integer for mice
  r[x %in% U_CODES] <- 2L
  r[x %in% I_CODES] <- 3L
  r
}

# ---------------------------------------------------------------------------
# 3. Load income + jbstat + hhsize for all analytical sample individuals
# ---------------------------------------------------------------------------
cat("Loading income panel data...\n")

# Get hidp for each wave (to join hhresp income)
get_hidp_for_pidps <- function(indresp_dir, waves, target_pidps) {
  rbindlist(lapply(waves, function(wave) {
    fpath <- file.path(indresp_dir, paste0(wave, "_indresp.tab"))
    if (!file.exists(fpath)) return(NULL)
    hdr <- names(fread(fpath, nrows=0L, sep="\t"))
    hidp_col   <- paste0(wave, "_hidp")
    jbstat_col <- if(paste0(wave,"_jbstat_bh") %in% hdr) paste0(wave,"_jbstat_bh")
                  else if(paste0(wave,"_jbstat") %in% hdr) paste0(wave,"_jbstat")
                  else NA_character_
    gor_col    <- paste0(wave, "_gor_dv")
    needed     <- c("pidp", hidp_col)
    opt        <- intersect(c(if(!is.na(jbstat_col)) jbstat_col, gor_col), hdr)
    cols       <- c(needed, opt)
    if (!all(needed %in% hdr)) return(NULL)
    dt <- fread(fpath, sep="\t", select=cols)
    dt <- dt[pidp %in% target_pidps]
    if (!is.na(jbstat_col) && jbstat_col %in% names(dt))
      dt[, jbstat_bin := recode_jbstat(as.integer(get(jbstat_col)))]
    setnames(dt, hidp_col, "hidp", skip_absent=TRUE)
    if (gor_col %in% names(dt)) setnames(dt, gor_col, "gor_dv", skip_absent=TRUE)
    dt[, wave := wave]
    dt
  }), fill=TRUE, use.names=TRUE)
}

get_income_hhsize <- function(hhresp_dir, waves) {
  rbindlist(lapply(waves, function(wave) {
    fpath <- file.path(hhresp_dir, paste0(wave, "_hhresp.tab"))
    if (!file.exists(fpath)) return(NULL)
    hdr      <- names(fread(fpath, nrows=0L, sep="\t"))
    hidp_col <- paste0(wave, "_hidp")
    inc_col  <- paste0(wave, "_fihhmngrs_dv")
    hhs_col  <- paste0(wave, "_hhsize")
    if (!hidp_col %in% hdr || !inc_col %in% hdr) return(NULL)
    cols <- c(hidp_col, inc_col, intersect(hhs_col, hdr))
    dt   <- fread(fpath, sep="\t", select=cols)
    setnames(dt, hidp_col, "hidp", skip_absent=TRUE)
    setnames(dt, inc_col, "fihhmngrs_dv", skip_absent=TRUE)
    if (hhs_col %in% names(dt)) setnames(dt, hhs_col, "hhsize", skip_absent=TRUE)
    dt[, wave := wave]
    dt
  }), fill=TRUE, use.names=TRUE)
}

BHPS_WAVES  <- paste0("b", letters[1:18])
BHPS_YEARS  <- 1991:2008
UKHLS_WAVES <- letters[1:15]
UKHLS_YEARS <- 2009:2023

bhps_ind  <- get_hidp_for_pidps(BHPS_DIR,  BHPS_WAVES,  analytical_pidps)
ukhls_ind <- get_hidp_for_pidps(UKHLS_DIR, UKHLS_WAVES, analytical_pidps)
bhps_hh   <- get_income_hhsize(BHPS_DIR,  BHPS_WAVES)
ukhls_hh  <- get_income_hhsize(UKHLS_DIR, UKHLS_WAVES)

bhps_panel  <- merge(bhps_ind,  bhps_hh[, .(hidp, wave, fihhmngrs_dv, hhsize)],
                     by=c("hidp","wave"), all.x=TRUE)
ukhls_panel <- merge(ukhls_ind, ukhls_hh[, .(hidp, wave, fihhmngrs_dv, hhsize)],
                     by=c("hidp","wave"), all.x=TRUE)

bhps_panel[,  era := "BHPS"]
ukhls_panel[, era := "UKHLS"]

# Add wave_index (numeric position within era)
bhps_panel[,  wave_index := match(wave, BHPS_WAVES)]
ukhls_panel[, wave_index := match(wave, UKHLS_WAVES)]

all_panel <- rbindlist(list(bhps_panel, ukhls_panel), fill=TRUE, use.names=TRUE)

# ---------------------------------------------------------------------------
# 4. Assess missingness by wave × era
# ---------------------------------------------------------------------------
cat("Assessing missingness...\n")
miss_bhps  <- bhps_panel[, .(n_obs=.N, n_miss=sum(is.na(fihhmngrs_dv)|fihhmngrs_dv<=0),
                              miss_rate=mean(is.na(fihhmngrs_dv)|fihhmngrs_dv<=0)),
                           by=wave][order(wave)]
miss_ukhls <- ukhls_panel[, .(n_obs=.N, n_miss=sum(is.na(fihhmngrs_dv)|fihhmngrs_dv<=0),
                               miss_rate=mean(is.na(fihhmngrs_dv)|fihhmngrs_dv<=0)),
                           by=wave][order(wave)]

cat("  BHPS missingness range:", round(range(miss_bhps$miss_rate),3), "\n")
cat("  UKHLS missingness range:", round(range(miss_ukhls$miss_rate),3), "\n")

# ---------------------------------------------------------------------------
# 5. Build wide panel and run MICE within each era
# ---------------------------------------------------------------------------
run_mice_wide <- function(panel_long, waves, era_label, m=20L) {
  cat(sprintf("  Building wide format for %s (%d waves)...\n", era_label, length(waves)))

  # Recode negative income as NA
  panel_long[fihhmngrs_dv <= 0, fihhmngrs_dv := NA_real_]

  # Keep only analytical sample individuals
  panel_long <- panel_long[pidp %in% analytical_pidps]

  # Deduplicate per (pidp, wave): some individuals appear in >1 household per wave.
  # Order so non-NA income rows sort first; .SD[1L] takes the best available row.
  panel_long <- panel_long[order(pidp, wave_index, is.na(fihhmngrs_dv)), .SD[1L], by=.(pidp, wave)]

  # Build income wide: rows = pidp, cols = wave incomes
  income_wide <- dcast(panel_long, pidp ~ wave, value.var="fihhmngrs_dv")

  # Use the first gor_dv per individual as a static predictor
  gor_static <- panel_long[!is.na(gor_dv), .(gor_dv = gor_dv[1L]), by=pidp]

  # Merge gor_dv
  wide <- merge(income_wide, gor_static, by="pidp", all.x=TRUE)
  wide[, gor_dv := as.factor(gor_dv)]

  # Ensure all analytical sample individuals are present (add missing rows)
  all_pidp_dt <- data.table(pidp=analytical_pidps)
  wide <- merge(all_pidp_dt, wide, by="pidp", all.x=TRUE)
  wide_df <- as.data.frame(wide[, -"pidp"])

  wave_cols <- intersect(waves, names(wide_df))
  n_miss_total <- sum(is.na(wide_df[, wave_cols]))
  cat(sprintf("    Total missing income cells: %d / %d (%.1f%%)\n",
              n_miss_total, length(wave_cols)*nrow(wide_df),
              100*n_miss_total/(length(wave_cols)*nrow(wide_df))))

  # Build predictor matrix: each wave income predicted by adjacent waves + gor_dv
  pred_mat <- make.predictorMatrix(wide_df)
  pred_mat[wave_cols, "gor_dv"] <- 1L
  # Remove gor_dv from predicting itself
  pred_mat["gor_dv", ] <- 0L

  method_vec <- rep("", ncol(wide_df))
  names(method_vec) <- names(wide_df)
  method_vec[wave_cols] <- "pmm"

  cat(sprintf("    Running MICE m=%d on %s era...\n", m, era_label))
  imp <- mice(wide_df, m=m, method=method_vec, predictorMatrix=pred_mat,
              seed=42L, printFlag=FALSE)
  list(imp=imp, wide=wide, wave_cols=wave_cols, pidps=wide$pidp)
}

cat("Running MICE...\n")
bhps_res  <- run_mice_wide(copy(bhps_panel),  BHPS_WAVES,  "BHPS",  m=M_IMPUTATIONS)
ukhls_res <- run_mice_wide(copy(ukhls_panel), UKHLS_WAVES, "UKHLS", m=M_IMPUTATIONS)

# ---------------------------------------------------------------------------
# 6. Assign within-era terciles and compute Rubin-pooled regime statistics
# ---------------------------------------------------------------------------
cat("Computing pooled regime income statistics...\n")

# Map pidps to regime labels
regime_map <- data.table(pidp=analytical_pidps, regime=regime_labels)

compute_regime_stats_per_m <- function(imp, wave_cols, pidps, era_label) {
  lapply(seq_len(imp$m), function(m_idx) {
    comp <- complete(imp, m_idx)
    income_mat <- as.matrix(comp[, wave_cols, drop=FALSE])

    # Within-era tercile cut-points from this imputed dataset
    all_incomes <- as.numeric(income_mat)
    all_incomes <- all_incomes[!is.na(all_incomes) & all_incomes > 0]
    cuts <- quantile(all_incomes, c(1/3, 2/3))

    # Assign predominant tercile per individual (majority across observed waves)
    tercile_per_wave <- matrix(NA_character_, nrow=nrow(income_mat), ncol=ncol(income_mat))
    tercile_per_wave[income_mat <= cuts[1]] <- "L"
    tercile_per_wave[income_mat > cuts[1] & income_mat <= cuts[2]] <- "M"
    tercile_per_wave[income_mat > cuts[2]] <- "H"

    mode_tercile <- apply(tercile_per_wave, 1, function(row) {
      valid <- row[!is.na(row)]
      if (length(valid) == 0) return(NA_character_)
      tbl <- table(valid)
      names(tbl)[which.max(tbl)]
    })

    dt <- data.table(pidp=pidps, tercile=mode_tercile)
    dt <- merge(dt, regime_map, by="pidp", all.x=TRUE)
    # Proportions per regime (Fix 1: add n_regime for within-imputation variance)
    dt[!is.na(tercile) & !is.na(regime),
       .(L_prop = mean(tercile=="L"), M_prop = mean(tercile=="M"), H_prop = mean(tercile=="H"),
         n_regime = .N),
       by=regime]
  })
}

bhps_stats  <- compute_regime_stats_per_m(bhps_res$imp,  bhps_res$wave_cols,  bhps_res$pidps,  "BHPS")
ukhls_stats <- compute_regime_stats_per_m(ukhls_res$imp, ukhls_res$wave_cols, ukhls_res$pidps, "UKHLS")

# Combine: take UKHLS if available (more waves), else BHPS
pool_regime_stats <- function(stats_list, era) {
  # Each element is a data.table with (regime, L_prop, M_prop, H_prop, n_regime)
  all_m   <- rbindlist(stats_list, idcol="m_idx")
  # Fix 2: Rubin's rules with within-imputation variance
  m <- length(stats_list)
  pooled <- all_m[, {
    m_n      <- length(L_prop)
    L_mean   <- mean(L_prop, na.rm=TRUE)
    M_mean   <- mean(M_prop, na.rm=TRUE)
    H_mean   <- mean(H_prop, na.rm=TRUE)
    L_var_b  <- var(L_prop, na.rm=TRUE)
    M_var_b  <- var(M_prop, na.rm=TRUE)
    H_var_b  <- var(H_prop, na.rm=TRUE)
    # Within-imputation variance (W_bar) per regime
    L_w_bar  <- mean(L_prop * (1 - L_prop) / n_regime, na.rm=TRUE)
    M_w_bar  <- mean(M_prop * (1 - M_prop) / n_regime, na.rm=TRUE)
    H_w_bar  <- mean(H_prop * (1 - H_prop) / n_regime, na.rm=TRUE)
    L_se     <- sqrt(L_w_bar + (1 + 1/m_n) * L_var_b)
    M_se     <- sqrt(M_w_bar + (1 + 1/m_n) * M_var_b)
    H_se     <- sqrt(H_w_bar + (1 + 1/m_n) * H_var_b)
    .(L_prop=round(L_mean,4), M_prop=round(M_mean,4), H_prop=round(H_mean,4),
      L_se=round(L_se,4), M_se=round(M_se,4), H_se=round(H_se,4),
      L_var_b=round(L_var_b,6), L_w_bar=round(L_w_bar,6))
  }, by=regime]
  pooled
}

bhps_pooled  <- pool_regime_stats(bhps_stats,  "BHPS")
ukhls_pooled <- pool_regime_stats(ukhls_stats, "UKHLS")

# Use UKHLS as primary (longer observation window); BHPS supplement not needed
# but compute FMI (fraction missing information) from Rubin's formula
compute_fmi <- function(stats_list) {
  m <- length(stats_list)
  all_m <- rbindlist(stats_list, idcol="m_idx")
  # Fix 2: Proper Rubin formula using per-regime n
  all_m[, {
    L_var_b <- var(L_prop, na.rm=TRUE)
    L_w_bar <- mean(L_prop * (1 - L_prop) / n_regime, na.rm=TRUE)
    fmi     <- (1 + 1/m) * L_var_b / (L_w_bar + (1 + 1/m) * L_var_b)
    .(fmi = round(fmi, 4))
  }, by=regime]
}

bhps_fmi  <- compute_fmi(bhps_stats)
ukhls_fmi <- compute_fmi(ukhls_stats)

# ---------------------------------------------------------------------------
# 7. Convergence check (R-hat proxy from between-chain variance)
# ---------------------------------------------------------------------------
# MICE convergence monitored via max between-imputation SD of pooled mean estimates
rhat_proxy <- function(stats_list) {
  all_m <- rbindlist(stats_list, idcol="m_idx")
  max(all_m[, .(sd_L=sd(L_prop,na.rm=TRUE)), by=regime]$sd_L, na.rm=TRUE)
}
bhps_rhat  <- round(rhat_proxy(bhps_stats),  4)
ukhls_rhat <- round(rhat_proxy(ukhls_stats), 4)
cat("  BHPS R-hat proxy (max between-m SD):", bhps_rhat, "\n")
cat("  UKHLS R-hat proxy (max between-m SD):", ukhls_rhat, "\n")

# ---------------------------------------------------------------------------
# 8. Save diagnostics JSON
# ---------------------------------------------------------------------------
cat("Saving diagnostics JSON...\n")

# Missingness by wave
miss_bhps_list  <- setNames(as.list(round(miss_bhps$miss_rate, 4)),  miss_bhps$wave)
miss_ukhls_list <- setNames(as.list(round(miss_ukhls$miss_rate, 4)), miss_ukhls$wave)

# FMI by regime
fmi_by_regime_bhps  <- setNames(as.list(bhps_fmi$fmi),  paste0("R", bhps_fmi$regime))
fmi_by_regime_ukhls <- setNames(as.list(ukhls_fmi$fmi), paste0("R", ukhls_fmi$regime))
# Use UKHLS FMI as primary
fmi_by_regime <- fmi_by_regime_ukhls

# Pooled tercile proportions by regime (use UKHLS; BHPS supplement)
pooled_list <- setNames(
  lapply(sort(unique(ukhls_pooled$regime)), function(r) {
    row <- ukhls_pooled[regime == r]
    list(L_prop=row$L_prop, M_prop=row$M_prop, H_prop=row$H_prop,
         L_se=row$L_se, M_se=row$M_se, H_se=row$H_se)
  }),
  paste0("R", sort(unique(ukhls_pooled$regime)))
)

result <- list(
  run_params = list(m=M_IMPUTATIONS, method="pmm", seed=42L),
  missingness_by_wave = list(bhps=miss_bhps_list, ukhls=miss_ukhls_list),
  convergence = list(bhps_rhat_proxy=bhps_rhat, ukhls_rhat_proxy=ukhls_rhat,
                     note="R-hat proxy = max between-imputation SD of L_prop across regimes"),
  fraction_missing_information_by_regime = fmi_by_regime,
  pooled_tercile_proportions_by_regime   = pooled_list,
  note_rubins_rules = "Pooled SEs follow Rubin's rules: Total Var = W_bar + (1 + 1/m) * B, where W_bar is the within-imputation variance (mean across m imputations of p*(1-p)/n_regime for binomial proportions) and B is the between-imputation variance. FMI = (1 + 1/m) * B / (W_bar + (1 + 1/m) * B).",
  note_tercile = "Within-era tercile boundaries computed per imputed dataset; BHPS and UKHLS eras imputed separately. UKHLS pooled estimates reported as primary.",
  note_imputed_datasets = "20 imputed datasets are NOT committed (gitignored). Reproduce via mice_income.R with seed=42."
)

write(toJSON(result, auto_unbox=TRUE, pretty=TRUE), OUT_PATH)
cat("Saved:", OUT_PATH, "\n")
cat("=== T1.14 complete ===\n")
