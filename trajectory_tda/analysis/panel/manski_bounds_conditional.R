# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: T1.15 supplement — conditional escape rate Manski bounds for R2/R6 starters
#
# Corrects original T1.15 which reported unconditional "escape rate" (regime prevalence).
# This script computes the CONDITIONAL escape rate: among individuals whose trajectory
# is classified as R2/R6 (disadvantaged) AND who are working-age at entry (age_at_entry<60),
# what fraction have their last observed state as employed?
#
# Working-age definition: age_at_entry < 60 (consistent with T1.19 rerun).
# jbstat=4 (retired) exclusion: approximated by age_at_entry < 60 proxy.
# Precise jbstat=4 check is applied in T1.19 via first-wave indresp loading.
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/manski_bounds_conditional.R

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
})

PROJ_ROOT      <- "C:/Users/steph/TDL"
WORKTREE       <- normalizePath(getwd(), mustWork = FALSE)
RESULTS_DIR    <- file.path(PROJ_ROOT, "results/trajectory_tda_integration")
IPW_PATH       <- file.path(PROJ_ROOT, "results/panel_methodology/weights/ipw_diagnostics_2026-05-13.json")
ORIG_BOUNDS    <- file.path(WORKTREE, "results/panel_methodology/manski_bounds/regime_escape_bounds_2026-05-13.json")
XWAVEDAT       <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab")
OUT_DIR        <- file.path(WORKTREE, "results/panel_methodology/manski_bounds")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY    <- format(Sys.Date(), "%Y-%m-%d")
OUT_PATH <- file.path(OUT_DIR, paste0("regime_escape_bounds_conditional_", TODAY, ".json"))

DISADV_REGIMES <- c(2L, 6L)
AGE_AT_ENTRY_MAX <- 59L  # age_at_entry < 60

cat("=== T1.15 Supplement: Conditional Escape Rate Manski Bounds ===\n")

# ---------------------------------------------------------------------------
# 1. Load regime labels and trajectory metadata
# ---------------------------------------------------------------------------
cat("Loading regime labels...\n")
anal05        <- fromJSON(file.path(RESULTS_DIR, "05_analysis.json"))
regime_labels <- as.integer(unlist(anal05$gmm_labels))
n_analytical  <- length(regime_labels)
cat("n_analytical:", n_analytical, "\n")

cat("Loading trajectory metadata (pidp, start_year)...\n")
traj       <- fromJSON(file.path(RESULTS_DIR, "01_trajectories.json"))
# metadata fields are dicts with string keys; some birth_year values may be JSON null.
# Use sapply with explicit null guard instead of unlist() which drops NULLs.
safe_int   <- function(lst) sapply(lst, function(v) if(is.null(v)||length(v)==0) NA_integer_ else as.integer(v[1]))
pidp_vec   <- safe_int(traj$metadata$pidp)
start_year <- safe_int(traj$metadata$start_year)
stopifnot(length(pidp_vec) == n_analytical)
stopifnot(length(start_year) == n_analytical)

# birth_year from xwavedat (more reliable — metadata birth_year has nulls for BHPS entrants)
cat("Loading birth year from xwavedat...\n")
xwave_by   <- fread(XWAVEDAT, sep="\t", select=c("pidp","birthy"))
xwave_by[, birthy := as.integer(birthy)]
xwave_by[birthy <= 1900 | birthy > 2005 | is.na(birthy), birthy := NA_integer_]
pidp_pos   <- data.table(pidp=pidp_vec, pos=seq_len(n_analytical))
pidp_by    <- merge(pidp_pos, xwave_by, by="pidp", all.x=TRUE)
setorder(pidp_by, pos)
birth_year <- pidp_by$birthy  # parallel to pidp_vec order
stopifnot(length(birth_year) == n_analytical)

# ---------------------------------------------------------------------------
# 2. Age at entry and working-age R2/R6 filter
# ---------------------------------------------------------------------------
age_at_entry <- start_year - birth_year
# Recode implausible ages to NA
age_at_entry[is.na(age_at_entry) | age_at_entry < 14L | age_at_entry > 90L] <- NA_integer_
cat("Age at entry: median =", median(age_at_entry, na.rm=TRUE),
    "range =", paste(range(age_at_entry, na.rm=TRUE), collapse="-"), "\n")

in_disadv  <- regime_labels %in% DISADV_REGIMES
valid_age  <- !is.na(age_at_entry) & age_at_entry <= AGE_AT_ENTRY_MAX
wa_starter <- in_disadv & valid_age

n_r2r6_all      <- sum(in_disadv)
n_starters_disadv <- sum(wa_starter)
cat("R2+R6 all ages:", n_r2r6_all, "\n")
cat("R2+R6 age_at_entry <=", AGE_AT_ENTRY_MAX, ":", n_starters_disadv, "\n")

if (n_starters_disadv < 4000L || n_starters_disadv > 5500L) {
  cat("WARNING: n_starters_disadv =", n_starters_disadv,
      "outside expected range 4,000-5,500. Escalate to Manager before proceeding.\n")
}

# ---------------------------------------------------------------------------
# 3. Load jbstat sequences for escape determination
# ---------------------------------------------------------------------------
cat("Loading jbstat sequences (this may take 10-20s)...\n")
t0   <- proc.time()
seqs <- fromJSON(file.path(RESULTS_DIR, "01_trajectories_sequences.json"))
cat("Sequences loaded in", round((proc.time()-t0)["elapsed"], 1), "s\n")
stopifnot(length(seqs) == n_analytical)

# Escape = last observed sequence state first char == "E" (employed)
# Sequences use composite state strings: E/U/I + H/M/L income (e.g. "EH", "IM", "UL")
# E encodes jbstat ∈ {1,2,5,11,12,13,14,15}; consistent with T1.19 escape definition
get_last_char <- function(seq_vec) {
  nna <- seq_vec[!is.na(seq_vec) & nzchar(seq_vec)]
  if (length(nna) == 0L) return(NA_character_)
  substr(nna[length(nna)], 1L, 1L)
}
get_first_char <- function(seq_vec) {
  nna <- seq_vec[!is.na(seq_vec) & nzchar(seq_vec)]
  if (length(nna) == 0L) return(NA_character_)
  substr(nna[1L], 1L, 1L)
}

cat("Extracting first/last states for R2/R6 working-age starters...\n")
wa_idx         <- which(wa_starter)
first_char_wa  <- sapply(wa_idx, function(i) get_first_char(seqs[[i]]))
last_char_wa   <- sapply(wa_idx, function(i) get_last_char(seqs[[i]]))

escape_cond    <- as.integer(last_char_wa == "E")
n_na_last      <- sum(is.na(last_char_wa))
n_escaped_cond <- sum(escape_cond, na.rm=TRUE)

# First state distribution (informational)
first_state_tbl <- table(first_char_wa, useNA="ifany")
cat("First state distribution (R2/R6 working-age starters):\n"); print(first_state_tbl)
cat("Last state distribution:\n"); print(table(last_char_wa, useNA="ifany"))

cond_escape_rate <- round(n_escaped_cond / n_starters_disadv, 4)
cat("n_starters_disadv:", n_starters_disadv, "\n")
cat("n_escaped_conditional:", n_escaped_cond, "\n")
cat("conditional_escape_rate:", cond_escape_rate, "\n")

if (cond_escape_rate < 0.04 || cond_escape_rate > 0.08) {
  cat("WARNING: conditional_escape_rate =", cond_escape_rate,
      "outside expected range [0.04, 0.08]. Escalate to Manager.\n")
}

# ---------------------------------------------------------------------------
# 4. Manski pessimistic lower bound for conditional escape rate
# ---------------------------------------------------------------------------
cat("Computing pessimistic Manski lower bound...\n")
ipw        <- fromJSON(IPW_PATH)
n_eligible <- as.integer(ipw$propensity_model$n_eligible)
n_attritors <- n_eligible - n_analytical
cat("n_eligible:", n_eligible, "  n_attritors:", n_attritors, "\n")

# Worst case: all attritors are R2/R6 working-age starters who fail to escape
cond_lower <- round(n_escaped_cond / (n_starters_disadv + n_attritors), 4)
cat("Pessimistic lower bound (conditional escape rate):", cond_lower, "\n")

# ---------------------------------------------------------------------------
# 5. Load original regime share bounds for completeness
# ---------------------------------------------------------------------------
cat("Loading original regime share bounds from T1.15...\n")
orig <- fromJSON(ORIG_BOUNDS)

# ---------------------------------------------------------------------------
# 6. Save JSON
# ---------------------------------------------------------------------------
cat("Saving conditional Manski bounds JSON...\n")

result <- list(
  run_params = list(
    working_age_filter  = paste0("age_at_entry <= ", AGE_AT_ENTRY_MAX),
    jbstat4_note        = paste0(
      "jbstat=4 (retired at entry) exclusion approximated by age_at_entry <= ",
      AGE_AT_ENTRY_MAX,
      ". Precise per-person jbstat=4 exclusion is applied in T1.19 via first-wave indresp data."
    ),
    escape_definition   = "last observed sequence state first char == 'E' (employed); consistent with T1.19",
    disadv_regimes      = DISADV_REGIMES,
    n_analytical        = n_analytical,
    n_eligible          = n_eligible,
    n_attritors         = n_attritors,
    source_sequences    = "results/trajectory_tda_integration/01_trajectories_sequences.json",
    source_05_analysis  = "results/trajectory_tda_integration/05_analysis.json",
    source_ipw          = "results/panel_methodology/weights/ipw_diagnostics_2026-05-13.json",
    source_orig_t115    = "results/panel_methodology/manski_bounds/regime_escape_bounds_2026-05-13.json"
  ),
  conditional_escape_rate = list(
    n_r2r6_all_ages           = n_r2r6_all,
    n_starters_disadv         = n_starters_disadv,
    n_escaped_conditional     = n_escaped_cond,
    n_last_state_na           = n_na_last,
    conditional_escape_rate_observed  = cond_escape_rate,
    first_state_distribution  = as.list(first_state_tbl),
    conditional_escape_rate_bounds = list(
      pessimistic_lower = cond_lower,
      observed          = cond_escape_rate
    ),
    attritor_worst_case_note = paste0(
      "Pessimistic lower bound assumes all ", n_attritors,
      " permanent attritors are R2/R6 working-age starters who fail to escape. ",
      "This is the Manski non-parametric bound — no assumption about selection direction."
    )
  ),
  regime_share_bounds = list(
    note                      = "Copied from original T1.15 output (regime_escape_bounds_2026-05-13.json); unconditional bounds unchanged.",
    observed_regime_proportions = orig$observed_regime_proportions,
    pessimistic_bounds          = orig$pessimistic_bounds
  )
)

write(toJSON(result, auto_unbox=TRUE, pretty=TRUE), OUT_PATH)
cat("Saved:", OUT_PATH, "\n")
cat("=== T1.15 Supplement complete ===\n")
