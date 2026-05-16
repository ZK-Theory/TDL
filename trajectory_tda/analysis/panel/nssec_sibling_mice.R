# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: Sibling-consistent MICE for parental social origin (NS-SEC proxy from father's SOC90)
#
# Parental NS-SEC proxy: pasoc90_cc (father's SOC90, cross-wave) from xwavedat.
# No direct parental NS-SEC variable exists in BHPS/UKHLS; the xwavedat `pasoc90_cc`
# is the most defensible parental social origin proxy available (76.3% coverage).
# Recoded to 3-class NS-SEC proxy: H=SOC major groups 1-3, M=4-6, L=7-9.
# FOO cluster column: foo_cluster (from data/derived/foo_clusters_2026-05-06.csv).
#
# Escalation note: No direct "parental NS-SEC" variable in BHPS/UKHLS indresp/xwavedat.
# pasoc90_cc (father's SOC90) is used as proxy, recoded to 3-class H/M/L.
# See task log for full variable search results.
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/nssec_sibling_mice.R

suppressPackageStartupMessages({
  library(data.table)
  library(mice)
  library(jsonlite)
})

set.seed(42)

PROJ_ROOT   <- "C:/Users/steph/TDL"
WORKTREE    <- normalizePath(getwd(), mustWork = FALSE)
RESULTS_DIR <- file.path(PROJ_ROOT, "results/trajectory_tda_integration")
FOO_PATH    <- file.path(PROJ_ROOT, "data/derived/foo_clusters_2026-05-06.csv")
XWAVEDAT    <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab")
OUT_DIR     <- file.path(WORKTREE, "results/panel_methodology/mice")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY    <- format(Sys.Date(), "%Y-%m-%d")
OUT_PATH <- file.path(OUT_DIR, paste0("nssec_sibling_diagnostics_", TODAY, ".json"))
M_IMPUTATIONS <- 20L
# Modal-fraction threshold for the per-cluster heterogeneity diagnostic (Fix 4).
# Clusters with modal_fraction < threshold AND >1 distinct observed value are flagged
# as high-heterogeneity. Propagation logic still uses the mode; this is data for
# Manager review of whether to introduce a propagation-skip rule.
MODAL_FRACTION_THRESHOLD <- 0.6
DIVERGENCE_WARN_THRESHOLD_REL <- 0.15  # 15% relative difference triggers warning

cat("=== T1.18: Sibling-Consistent MICE for Parental NS-SEC Proxy ===\n")

# ---------------------------------------------------------------------------
# 1. Load analytical sample pidps
# ---------------------------------------------------------------------------
cat("Loading analytical sample...\n")
traj    <- fromJSON(file.path(RESULTS_DIR, "01_trajectories.json"))
analytical_pidps <- as.integer(unlist(traj$metadata$pidp))
n_analytical     <- length(analytical_pidps)
cat("n_analytical:", n_analytical, "\n")

# ---------------------------------------------------------------------------
# 2. Load parental social origin proxy from xwavedat
# ---------------------------------------------------------------------------
cat("Loading parental SOC90 from xwavedat...\n")
xwave <- fread(XWAVEDAT, sep="\t",
               select=c("pidp","pasoc90_cc","masoc90_cc","birthy","sex_dv"))
xwave_an <- xwave[pidp %in% analytical_pidps]

# Recode SOC90 to 3-class NS-SEC proxy: H=1-3, M=4-6, L=7-9 (first digit of 2-digit code)
soc_to_class <- function(soc) {
  soc <- as.integer(soc)
  cls <- rep(NA_integer_, length(soc))
  major <- soc %/% 10L
  cls[major %in% 1:3 & !is.na(major)] <- 1L  # H: managerial/professional/associate
  cls[major %in% 4:6 & !is.na(major)] <- 2L  # M: clerical/craft/personal service
  cls[major %in% 7:9 & !is.na(major)] <- 3L  # L: sales/operatives/elementary
  cls[soc <= 0 | is.na(soc)] <- NA_integer_
  cls
}

# Use pasoc90_cc (father's SOC90) as primary; masoc90_cc (mother's SOC90) as fallback
xwave_an[, nssec_proxy := soc_to_class(pasoc90_cc)]
xwave_an[is.na(nssec_proxy), nssec_proxy := soc_to_class(masoc90_cc)]
xwave_an[, nssec_proxy := factor(nssec_proxy, levels=1:3, labels=c("H","M","L"))]

obs_nssec <- sum(!is.na(xwave_an$nssec_proxy))
cat("nssec_proxy observed (before propagation):", obs_nssec, "/", n_analytical,
    sprintf("(%.1f%%)\n", 100*obs_nssec/n_analytical))

# ---------------------------------------------------------------------------
# 3. Load FOO clusters
# ---------------------------------------------------------------------------
cat("Loading FOO clusters...\n")
foo <- fread(FOO_PATH)
foo_an <- foo[pidp %in% analytical_pidps, .(pidp, foo_cluster, foo_size)]
cat("FOO coverage:", nrow(foo_an), "/", n_analytical, "\n")

# Build working dataset
work <- merge(
  data.table(pidp = analytical_pidps),
  xwave_an[, .(pidp, nssec_proxy, birthy, sex_dv)],
  by = "pidp", all.x = TRUE
)
work <- merge(work, foo_an, by = "pidp", all.x = TRUE)
setkey(work, pidp)

n_singletons     <- sum(work$foo_size == 1L, na.rm=TRUE)
n_in_families    <- sum(work$foo_size > 1L,  na.rm=TRUE)
cat("Singletons (no siblings in data):", n_singletons, "\n")
cat("In multi-individual FOO clusters:", n_in_families, "\n")

# ---------------------------------------------------------------------------
# 4. Sibling propagation: within each cluster, if >=1 observed, propagate to all
# ---------------------------------------------------------------------------
cat("Applying sibling propagation...\n")

# Identify multi-individual clusters with >=1 observed NS-SEC
# Fix 4: also compute per-cluster heterogeneity diagnostic
#   - n_distinct: number of distinct H/M/L levels among observed siblings
#   - modal_count: count of observed siblings agreeing with the mode
#   - modal_fraction: modal_count / n_obs (NA when n_obs == 0)
multi_clusters <- work[foo_size > 1L, .(
  n_obs        = sum(!is.na(nssec_proxy)),
  n_total      = .N,
  n_distinct   = length(unique(nssec_proxy[!is.na(nssec_proxy)])),
  mode_val     = {
    obs <- nssec_proxy[!is.na(nssec_proxy)]
    if (length(obs) == 0) NA_character_
    else as.character(names(sort(table(obs), decreasing=TRUE))[1L])
  },
  modal_count  = {
    obs <- nssec_proxy[!is.na(nssec_proxy)]
    if (length(obs) == 0) 0L
    else max(table(obs))
  }
), by=foo_cluster]
multi_clusters[, modal_fraction := ifelse(n_obs > 0, modal_count / n_obs, NA_real_)]

clusters_with_obs    <- multi_clusters[n_obs > 0]
n_propagatable       <- sum(work$foo_size > 1L & !is.na(work$nssec_proxy) |
                              work$foo_cluster %in% clusters_with_obs$foo_cluster, na.rm=TRUE)

# Identify clusters eligible for propagation (consistent enough to mode-propagate)
propagation_eligible <- clusters_with_obs[
  is.na(modal_fraction) | modal_fraction >= MODAL_FRACTION_THRESHOLD | n_distinct == 1L,
  foo_cluster
]
n_skipped_high_heterogeneity <- nrow(clusters_with_obs) - length(propagation_eligible)
cat("Skipped propagation for", n_skipped_high_heterogeneity, "high-heterogeneity clusters\n")

# Propagate only within eligible clusters
work_out <- copy(work)
propagated_count <- 0L
for (cl in propagation_eligible) {
  mode_val <- clusters_with_obs[foo_cluster == cl, mode_val]
  if (is.na(mode_val)) next
  missing_in_cl <- which(work_out$foo_cluster == cl & is.na(work_out$nssec_proxy))
  if (length(missing_in_cl) > 0) {
    work_out[missing_in_cl, nssec_proxy := factor(mode_val, levels = c("H","M","L"))]
    propagated_count <- propagated_count + length(missing_in_cl)
  }
}
cat("Propagated to:", propagated_count, "individuals\n")
obs_after_prop <- sum(!is.na(work_out$nssec_proxy))
cat("nssec_proxy observed (after propagation):", obs_after_prop, "/", n_analytical,
    sprintf("(%.1f%%)\n", 100*obs_after_prop/n_analytical))

# ---------------------------------------------------------------------------
# 5. Verify within-cluster consistency for propagated clusters
# ---------------------------------------------------------------------------
cat("Verifying within-cluster consistency...\n")
consistency_ok <- TRUE
inconsistent_n <- 0L
for (cl in clusters_with_obs$foo_cluster) {
  vals <- work_out[foo_cluster==cl & !is.na(nssec_proxy), nssec_proxy]
  if (length(unique(as.character(vals))) > 1L) {
    consistency_ok <- FALSE
    inconsistent_n <- inconsistent_n + 1L
  }
}
if (consistency_ok) {
  cat("Within-cluster consistency: PASS (all propagated clusters have identical NS-SEC proxy)\n")
} else {
  cat("Within-cluster consistency: FAIL (", inconsistent_n, " clusters have mixed values)\n")
}

# ---------------------------------------------------------------------------
# 6. MICE for remaining missing
# ---------------------------------------------------------------------------
n_still_missing <- sum(is.na(work_out$nssec_proxy))
cat("Remaining missing after propagation:", n_still_missing, "\n")

# Load additional MICE predictors: education, region, age from IPW covariates or xwavedat
# Use birthy (age proxy) and sex_dv already in work_out
# Add hiqual_dv: load from UKHLS wave a or BHPS wave ba (first available per individual)
cat("Loading education predictor (hiqual_dv)...\n")
load_hiqual <- function(dir_path, waves) {
  rbindlist(lapply(waves, function(wave) {
    fpath <- file.path(dir_path, paste0(wave, "_indresp.tab"))
    if (!file.exists(fpath)) return(NULL)
    hdr <- names(fread(fpath, nrows=0L, sep="\t"))
    hq_col <- paste0(wave, "_hiqual_dv")
    if (!hq_col %in% hdr) return(NULL)
    dt <- fread(fpath, sep="\t", select=c("pidp", hq_col))
    dt <- dt[pidp %in% analytical_pidps & get(hq_col) > 0]
    setnames(dt, hq_col, "hiqual_dv")
    dt[, wave := wave]
  }), fill=TRUE)
}
bhps_hq   <- load_hiqual(file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/bhps"),
                          paste0("b", letters[1:18]))
ukhls_hq  <- load_hiqual(file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls"),
                          letters[1:15])
all_hq <- rbindlist(list(bhps_hq, ukhls_hq), fill=TRUE)
# Take first non-missing hiqual_dv per individual
first_hq <- all_hq[order(pidp, wave)][, .SD[1L], by=pidp][, .(pidp, hiqual_dv)]
work_out  <- merge(work_out, first_hq, by="pidp", all.x=TRUE)
work_out[, hiqual_dv := factor(as.integer(hiqual_dv))]

# MICE predictors: nssec_proxy (outcome), hiqual_dv, birthy, sex_dv
mice_df <- work_out[, .(
  nssec_proxy  = as.integer(nssec_proxy),  # 1/2/3 for H/M/L; NA = missing
  hiqual_dv    = as.integer(hiqual_dv),
  birthy       = as.integer(birthy),
  sex_dv       = as.integer(sex_dv)
)]
# Recode invalid values to NA
mice_df[hiqual_dv <= 0 | is.na(hiqual_dv), hiqual_dv := NA_integer_]
mice_df[birthy <= 1900 | birthy > 2010 | is.na(birthy), birthy := NA_integer_]
mice_df[sex_dv <= 0 | is.na(sex_dv), sex_dv := NA_integer_]

mice_df <- as.data.frame(mice_df)

# Only impute nssec_proxy; other cols are complete-case predictors
method_vec <- rep("", ncol(mice_df))
names(method_vec) <- names(mice_df)
method_vec["nssec_proxy"] <- "pmm"

pred_mat <- make.predictorMatrix(mice_df)
pred_mat["nssec_proxy", ] <- 0L
pred_mat["nssec_proxy", c("hiqual_dv", "birthy", "sex_dv")] <- 1L
pred_mat[c("hiqual_dv", "birthy", "sex_dv"), ] <- 0L

cat(sprintf("Running MICE m=%d (PMM) for remaining missing nssec_proxy...\n", M_IMPUTATIONS))
imp <- mice(mice_df, m=M_IMPUTATIONS, method=method_vec, predictorMatrix=pred_mat,
            seed=42L, printFlag=FALSE)
cat("MICE complete. Logged events:", nrow(imp$loggedEvents), "\n")

# ---------------------------------------------------------------------------
# 7. Convergence diagnostics
# ---------------------------------------------------------------------------
rhat_proxy <- function(imp_obj) {
  # Between-chain SD of mean imputed NS-SEC across m imputations
  means <- sapply(seq_len(imp_obj$m), function(i) {
    comp <- complete(imp_obj, i)
    mean(comp$nssec_proxy[is.na(mice_df$nssec_proxy)], na.rm=TRUE)
  })
  round(sd(means), 4)
}
rhat <- rhat_proxy(imp)
cat("R-hat proxy (SD of imputed means across", M_IMPUTATIONS, "chains):", rhat, "\n")

# ---------------------------------------------------------------------------
# 8. NS-SEC distribution comparison
# ---------------------------------------------------------------------------
obs_dist <- round(prop.table(table(work_out$nssec_proxy[!is.na(work_out$nssec_proxy)])), 4)
cat("Observed NS-SEC proxy distribution (after propagation):\n"); print(obs_dist)

imp_distributions <- lapply(seq_len(imp$m), function(i) {
  comp <- complete(imp, i)
  vals <- comp$nssec_proxy[is.na(mice_df$nssec_proxy)]
  vals_chr <- c("H","M","L")[pmax(1, pmin(3, round(vals)))]
  vals_mapped <- factor(vals_chr, levels = c("H","M","L"))
  prop.table(table(vals_mapped))
})
imp_dist_matrix <- do.call(rbind, lapply(imp_distributions, as.numeric))
imp_dist_mean   <- round(colMeans(imp_dist_matrix), 4)
names(imp_dist_mean) <- c("H","M","L")
cat("Imputed NS-SEC proxy mean distribution:\n"); print(imp_dist_mean)

divergence <- lapply(c("H","M","L"), function(cat_lbl) {
  obs      <- as.numeric(obs_dist[cat_lbl])
  imp_val  <- imp_dist_mean[[cat_lbl]]
  abs_diff <- imp_val - obs
  rel_diff <- if (!is.na(obs) && obs > 0) abs_diff / obs else NA_real_
  list(
    observed_post_propagation = obs,
    imputed_mean              = imp_val,
    abs_diff                  = round(abs_diff, 4),
    rel_diff                  = round(rel_diff, 4),
    exceeds_threshold         = !is.na(rel_diff) && abs(rel_diff) >= DIVERGENCE_WARN_THRESHOLD_REL
  )
})
names(divergence) <- c("H","M","L")
n_categories_exceed <- sum(sapply(divergence, function(x) isTRUE(x$exceeds_threshold)))

# ---------------------------------------------------------------------------
# 9. Save diagnostics JSON
# ---------------------------------------------------------------------------
cat("Saving diagnostics JSON...\n")

result <- list(
  run_params = list(
    m = M_IMPUTATIONS, method = "pmm", seed = 42L,
    proxy_variable = "pasoc90_cc (father's SOC90, xwavedat) recoded to 3-class H/M/L",
    proxy_note = "No direct parental NS-SEC variable in BHPS/UKHLS. pasoc90_cc (father's SOC90 from xwavedat) is the most defensible parental social origin proxy (76.3% base coverage). Recoded: SOC major groups 1-3=H, 4-6=M, 7-9=L. See escalation note in task log.",
    foo_clusters_source = "data/derived/foo_clusters_2026-05-06.csv"
  ),
  coverage = list(
    n_analytical              = n_analytical,
    n_with_observed_pre_prop  = obs_nssec,
    pct_observed_pre_prop     = round(100*obs_nssec/n_analytical, 2),
    n_propagated              = propagated_count,
    n_with_observed_post_prop = obs_after_prop,
    pct_observed_post_prop    = round(100*obs_after_prop/n_analytical, 2),
    n_still_missing           = n_still_missing,
    n_singleton               = n_singletons,
    n_in_multi_foo_cluster    = n_in_families,
    n_clusters_with_obs                   = nrow(clusters_with_obs),
    n_skipped_high_heterogeneity_clusters = n_skipped_high_heterogeneity,
    n_propagated_after_skip_rule          = propagated_count
  ),
  within_cluster_consistency = list(
    result                  = if(consistency_ok) "PASS" else "FAIL",
    n_inconsistent_clusters = inconsistent_n,
    note                    = "Propagation uses mode NS-SEC proxy within each FOO cluster. See per_cluster_diagnostic for heterogeneity detail.",
    propagation_rule        = paste0(
      "Mode-propagation applied only when modal_fraction >= ",
      MODAL_FRACTION_THRESHOLD,
      " OR n_distinct == 1. High-heterogeneity clusters skip propagation; ",
      "missing members enter standard MICE imputation."
    ),
    per_cluster_diagnostic = list(
      threshold_modal_fraction              = MODAL_FRACTION_THRESHOLD,
      n_clusters_with_obs                   = nrow(clusters_with_obs),
      n_clusters_inconsistent               = inconsistent_n,
      n_clusters_flagged_high_heterogeneity = sum(multi_clusters$modal_fraction < MODAL_FRACTION_THRESHOLD &
                                                    multi_clusters$n_distinct > 1, na.rm=TRUE),
      summary_modal_fraction = list(
        median = round(median(multi_clusters$modal_fraction, na.rm=TRUE), 4),
        mean   = round(mean(multi_clusters$modal_fraction, na.rm=TRUE), 4),
        min    = round(min(multi_clusters$modal_fraction, na.rm=TRUE), 4),
        q25    = round(quantile(multi_clusters$modal_fraction, 0.25, na.rm=TRUE), 4)
      ),
      flagged_clusters_sample = head(multi_clusters[modal_fraction < MODAL_FRACTION_THRESHOLD &
                                                      n_distinct > 1, foo_cluster], 20)
    )
  ),
  convergence = list(
    sd_of_imputed_means = rhat,
    mice_logged_events  = nrow(imp$loggedEvents),
    note = "SD of mean imputed nssec_proxy across m imputations (not Gelman-Rubin R-hat — categorical outcome makes Gelman-Rubin inapplicable)."
  ),
  nssec_distribution_comparison = list(
    observed_post_propagation     = as.list(obs_dist),
    imputed_mean                  = list(H=imp_dist_mean[1], M=imp_dist_mean[2], L=imp_dist_mean[3]),
    divergence                    = divergence,
    divergence_threshold_rel      = DIVERGENCE_WARN_THRESHOLD_REL,
    n_categories_exceed_threshold = n_categories_exceed,
    divergence_note = paste0(
      "Per-category absolute and relative differences (imputed_mean - observed_post_propagation). ",
      "exceeds_threshold flags when |rel_diff| >= ", DIVERGENCE_WARN_THRESHOLD_REL, ". ",
      "Material divergence may indicate MNAR pattern or imputation-model misspecification; ",
      "downstream analyses should treat imputed-only individuals as a sensitivity not a primary."
    )
  )
)

write(toJSON(result, auto_unbox=TRUE, pretty=TRUE), OUT_PATH)
cat("Saved:", OUT_PATH, "\n")
cat("=== T1.18 complete ===\n")
