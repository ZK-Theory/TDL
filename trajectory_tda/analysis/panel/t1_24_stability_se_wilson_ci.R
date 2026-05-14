# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: T1.24 — Table 2 stability SEs + Table 3 Wilson 95% escape CIs.
#   Addresses reviewer B10/B11 (no uncertainty in Table 2 stability scores and
#   Table 3 escape rates).
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/t1_24_stability_se_wilson_ci.R

suppressPackageStartupMessages(library(jsonlite))

set.seed(42)

PROJ_ROOT <- "C:/Users/steph/TDL"
WORKTREE  <- normalizePath(getwd(), mustWork = FALSE)
TODAY     <- format(Sys.Date(), "%Y-%m-%d")

ANALYSIS_JSON <- file.path(PROJ_ROOT, "results/trajectory_tda_integration/05_analysis.json")
SEQS_JSON     <- file.path(PROJ_ROOT, "results/trajectory_tda_integration/01_trajectories_sequences.json")
P2_JSON       <- file.path(PROJ_ROOT, "results/trajectory_tda_priority2/p2_5_age_stratified.json")

OUT_DIR <- file.path(WORKTREE, "results/panel_methodology/uncertainty_addons")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

SE_PATH   <- file.path(OUT_DIR, paste0("stability_se_", TODAY, ".json"))
WCI_PATH  <- file.path(OUT_DIR, paste0("escape_wilson_ci_", TODAY, ".json"))

cat("=== T1.24: Stability SEs + Wilson CIs ===\n")

# ---------------------------------------------------------------------------
# 1. Load inputs
# ---------------------------------------------------------------------------
cat("Loading 05_analysis.json...\n")
analysis <- fromJSON(ANALYSIS_JSON)
profiles <- analysis$regimes$profiles

cat("Loading 01_trajectories_sequences.json...\n")
seqs <- fromJSON(SEQS_JSON)  # list of 27,280 character vectors
n_total <- length(seqs)
cat("n_sequences:", n_total, "\n")

cat("Loading gmm_labels...\n")
gmm_labels <- analysis$gmm_labels  # integer vector of length 27,280
cat("n_labels:", length(gmm_labels), "\n")
stopifnot(length(gmm_labels) == n_total)

cat("Loading p2_5_age_stratified.json...\n")
p2 <- fromJSON(P2_JSON)

# ---------------------------------------------------------------------------
# 2. Table 2 — Stability SEs
#
# Stability = P(stay in same regime at next window)
# For each individual: extract consecutive pair of regime assignments within
# their sequence. In the v1 analysis each individual has ONE regime label
# assigned to their full trajectory. We compute stability as the proportion
# of window-pair transitions where the individual stays.
#
# Since each trajectory is a single sequence and GMM assigns one label per
# trajectory, we approximate regime transitions by looking at consecutive
# STATE TRANSITIONS within each trajectory (treating each state as a "window")
# and counting how many transitions stay within the regime's dominant-state pattern.
#
# More accurately: stability in 05_analysis.json is the proportion of
# consecutive state-pairs within the regime's sequences that are the same state.
# We use the stored stability + n_members as the binomial SE inputs.
# ---------------------------------------------------------------------------
cat("\n--- Table 2: Stability SEs ---\n")

# Also compute stability directly from sequences + gmm_labels:
# For each individual i in regime r, look at consecutive state pairs in seqs[[i]].
# Stability_r = # consecutive same-state pairs / # total consecutive pairs in regime r.
# This gives us n = total consecutive pairs in regime r (denominator for SE).

regime_ids <- sort(unique(gmm_labels))
cat("Regimes:", paste(regime_ids, collapse=", "), "\n")

stability_results <- lapply(regime_ids, function(r) {
  # Indices of individuals in this regime (0-indexed labels → 1-indexed R)
  idx <- which(gmm_labels == r)  # gmm_labels is 0-indexed if numeric
  n_members <- length(idx)

  # Count consecutive same-state pairs in sequences for this regime
  n_stay  <- 0L
  n_trans <- 0L
  for (i in idx) {
    s <- seqs[[i]]  # character vector of states
    if (length(s) < 2L) next
    pairs <- length(s) - 1L
    stays <- sum(s[-length(s)] == s[-1L])
    n_stay  <- n_stay  + stays
    n_trans <- n_trans + pairs
  }

  if (n_trans == 0L) {
    return(list(regime = r, n_members = n_members,
                n_transitions = 0L, n_stays = 0L,
                stability_from_seqs = NA_real_, stability_stored = NA_real_,
                SE = NA_real_, CI95_lo = NA_real_, CI95_hi = NA_real_))
  }

  p_seq  <- n_stay / n_trans
  se_seq <- sqrt(p_seq * (1 - p_seq) / n_trans)
  ci_lo  <- p_seq - 1.96 * se_seq
  ci_hi  <- p_seq + 1.96 * se_seq

  # Stored stability from profile (for comparison)
  prof_key <- as.character(r)
  p_stored <- if (!is.null(profiles[[prof_key]])) profiles[[prof_key]]$stability else NA_real_

  cat(sprintf("  R%d: n=%d, n_trans=%d, p=%.4f (stored=%.4f), SE=%.4f, 95%% CI [%.4f, %.4f]\n",
              r, n_members, n_trans, p_seq, p_stored, se_seq, ci_lo, ci_hi))

  list(
    regime            = r,
    n_members         = n_members,
    n_transitions     = n_trans,
    n_stays           = n_stay,
    stability_from_seqs = round(p_seq, 6),
    stability_stored    = round(p_stored, 6),
    SE                = round(se_seq, 6),
    CI95_lo           = round(max(0, ci_lo), 6),
    CI95_hi           = round(min(1, ci_hi), 6),
    CI95_note         = "Normal approximation 95% CI"
  )
})
names(stability_results) <- paste0("R", regime_ids)

# ---------------------------------------------------------------------------
# 3. Table 3 — Wilson 95% CIs for escape rates
# ---------------------------------------------------------------------------
cat("\n--- Table 3: Wilson CIs for escape rates ---\n")

wilson_ci <- function(x, n, conf = 0.95) {
  # Wilson score interval
  z   <- qnorm((1 + conf) / 2)
  p   <- x / n
  denom <- 1 + z^2 / n
  center <- (p + z^2 / (2*n)) / denom
  margin <- z * sqrt(p*(1-p)/n + z^2/(4*n^2)) / denom
  list(
    estimate = round(p, 6),
    lower    = round(max(0, center - margin), 6),
    upper    = round(min(1, center + margin), 6)
  )
}

escape_rates <- p2$escape_rates

# Overall
ov <- escape_rates$overall
wi_overall <- wilson_ci(ov$n_ever_escape, ov$n_starting_disadvantaged)
cat(sprintf("  Overall:    n=%d, x=%d, p=%.4f, Wilson [%.4f, %.4f]\n",
            ov$n_starting_disadvantaged, ov$n_ever_escape,
            wi_overall$estimate, wi_overall$lower, wi_overall$upper))

# Working-age
wa <- escape_rates$working_age
wi_wa <- wilson_ci(wa$n_ever_escape, wa$n_starting_disadvantaged)
cat(sprintf("  Working-age: n=%d, x=%d, p=%.4f, Wilson [%.4f, %.4f]\n",
            wa$n_starting_disadvantaged, wa$n_ever_escape,
            wi_wa$estimate, wi_wa$lower, wi_wa$upper))

# Retirement-age
ra <- escape_rates$retirement_age
wi_ra <- wilson_ci(ra$n_ever_escape, ra$n_starting_disadvantaged)
cat(sprintf("  Retirement:  n=%d, x=%d, p=%.4f, Wilson [%.4f, %.4f]\n",
            ra$n_starting_disadvantaged, ra$n_ever_escape,
            wi_ra$estimate, wi_ra$lower, wi_ra$upper))

wilson_results <- list(
  overall = list(
    n_starters = ov$n_starting_disadvantaged,
    n_escaped  = ov$n_ever_escape,
    estimate   = wi_overall$estimate,
    CI_lower   = wi_overall$lower,
    CI_upper   = wi_overall$upper,
    CI_note    = "Wilson 95% CI"
  ),
  working_age = list(
    n_starters = wa$n_starting_disadvantaged,
    n_escaped  = wa$n_ever_escape,
    estimate   = wi_wa$estimate,
    CI_lower   = wi_wa$lower,
    CI_upper   = wi_wa$upper,
    CI_note    = "Wilson 95% CI"
  ),
  retirement_age = list(
    n_starters = ra$n_starting_disadvantaged,
    n_escaped  = ra$n_ever_escape,
    estimate   = wi_ra$estimate,
    CI_lower   = wi_ra$lower,
    CI_upper   = wi_ra$upper,
    CI_note    = "Wilson 95% CI"
  ),
  source = P2_JSON
)

# ---------------------------------------------------------------------------
# 4. Save outputs
# ---------------------------------------------------------------------------
cat("\nSaving stability SE JSON...\n")
stability_out <- list(
  run_params = list(
    seed   = 42L,
    date   = TODAY,
    method = paste0(
      "Stability = proportion of consecutive same-state pairs within each ",
      "individual's trajectory sequence for individuals in that regime. ",
      "SE = sqrt(p*(1-p)/n_transitions). 95% CI = Normal approx."
    ),
    source_analysis  = ANALYSIS_JSON,
    source_sequences = SEQS_JSON,
    n_total          = n_total
  ),
  stability_by_regime = stability_results
)
write(toJSON(stability_out, auto_unbox = TRUE, pretty = TRUE), SE_PATH)
cat("Saved:", SE_PATH, "\n")

cat("Saving Wilson CI JSON...\n")
write(toJSON(wilson_results, auto_unbox = TRUE, pretty = TRUE), WCI_PATH)
cat("Saved:", WCI_PATH, "\n")
cat("=== T1.24 complete ===\n")
