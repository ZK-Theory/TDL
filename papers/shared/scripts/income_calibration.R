# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Cross-era income calibration on spanning BHPS/UKHLS individuals.
# Compares gross household income (fihhmngrs_dv) in last BHPS wave (br)
# and first UKHLS wave where BHPS cohort appears (b, 2010-12) for
# respondents present in both. Wave a has 0 BHPS br overlap because the
# BHPS cohort was enrolled into UKHLS from wave b, not wave a.
# NOTE: task spec variables fihhmn and fihhmnnet3_dv do not exist in this
# version of UKDA-6614; fihhmngrs_dv is the available harmonised gross income
# variable present identically in both BHPS and UKHLS hhresp files.

library(jsonlite)

get_script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("--file=", args, value = TRUE)
  if (length(file_arg) > 0) {
    return(dirname(normalizePath(sub("^--file=", "", file_arg[1]))))
  }
  if (!is.null(sys.frame(1)$ofile)) {
    return(dirname(normalizePath(sys.frame(1)$ofile)))
  }
  return(normalizePath("."))
}

DATA_ROOT <- Sys.getenv("DATA_ROOT", unset = "")
if (!nzchar(DATA_ROOT)) {
  DATA_ROOT <- normalizePath(file.path(get_script_dir(), "..", "..", "..", "data", "UKDA-6614-tab", "tab"), mustWork = FALSE)
}
TODAY <- format(Sys.Date(), "%Y-%m-%d")

check_file <- function(fpath) {
  if (!file.exists(fpath)) {
    stop(sprintf("Required file not found: %s", fpath))
  }
}

read_cols <- function(fpath, cols) {
  check_file(fpath)
  header <- trimws(strsplit(readLines(fpath, n = 1), "\t")[[1]])
  missing <- cols[!cols %in% header]
  if (length(missing) > 0) {
    stop(sprintf("Missing column(s) in %s: %s", basename(fpath), paste(missing, collapse = ", ")))
  }
  col_classes <- rep("NULL", length(header))
  for (col in cols) {
    idx <- match(col, header)
    if (sum(header == col) > 1) {
      warning(sprintf("duplicate column name: %s; using first occurrence", col))
    }
    col_classes[idx] <- NA # NA = default (character, then coerce)
  }
  df <- read.delim(fpath,
    header = TRUE, sep = "\t",
    colClasses = col_classes, stringsAsFactors = FALSE,
    quote = "", fill = TRUE, na.strings = ""
  )
  # Coerce numeric columns with explicit NA checks
  for (col in names(df)) {
    temp <- suppressWarnings(as.numeric(df[[col]]))
    na_before <- sum(is.na(df[[col]]))
    na_after <- sum(is.na(temp))
    if (na_after > na_before) {
      stop(sprintf(
        "Numeric coercion introduced %d new NAs in column %s of %s",
        na_after - na_before, col, basename(fpath)
      ))
    }
    df[[col]] <- temp
  }
  df
}

# ---- 1. Read BHPS wave br: pidp + hidp from indresp ----
cat("Reading BHPS br indresp...\n")
bhps_ind <- read_cols(
  file.path(DATA_ROOT, "bhps", "br_indresp.tab"),
  c("pidp", "br_hidp")
)
cat("  N rows:", nrow(bhps_ind), "\n")

# ---- 2. Read BHPS wave br: hidp + fihhmngrs_dv from hhresp ----
cat("Reading BHPS br hhresp...\n")
bhps_hh <- read_cols(
  file.path(DATA_ROOT, "bhps", "br_hhresp.tab"),
  c("br_hidp", "br_fihhmngrs_dv")
)
cat("  N rows:", nrow(bhps_hh), "\n")

# ---- 3. Read UKHLS wave b: pidp + hidp from indresp ----
# Wave b (2010-12) is the first UKHLS wave containing the BHPS cohort.
# Wave a (2009-11) had 0 BHPS br respondents per pidp crosswalk check.
cat("Reading UKHLS b indresp...\n")
ukhls_ind <- read_cols(
  file.path(DATA_ROOT, "ukhls", "b_indresp.tab"),
  c("pidp", "b_hidp")
)
cat("  N rows:", nrow(ukhls_ind), "\n")

# ---- 4. Read UKHLS wave b: hidp + income from hhresp ----
cat("Reading UKHLS b hhresp...\n")
ukhls_hh_path <- file.path(DATA_ROOT, "ukhls", "b_hhresp.tab")
check_file(ukhls_hh_path)
ukhls_hh <- read_cols(
  ukhls_hh_path,
  c("b_hidp", "b_fihhmngrs_dv", "b_fihhmnnet1_dv")
)
cat("  N rows:", nrow(ukhls_hh), "\n")

# ---- 5. Construct BHPS income per individual ----
bhps_merged <- merge(bhps_ind, bhps_hh, by = "br_hidp")
bhps_merged <- bhps_merged[!is.na(bhps_merged$pidp) & bhps_merged$pidp > 0, ]
bhps_merged$bhps_grs <- bhps_merged$br_fihhmngrs_dv
bhps_merged$bhps_grs[bhps_merged$bhps_grs < 0] <- NA
cat("\nBHPS br valid income obs:", sum(!is.na(bhps_merged$bhps_grs)), "\n")

# ---- 6. Construct UKHLS income per individual ----
ukhls_merged <- merge(ukhls_ind, ukhls_hh, by = "b_hidp")
ukhls_merged <- ukhls_merged[!is.na(ukhls_merged$pidp) & ukhls_merged$pidp > 0, ]
ukhls_merged$ukhls_grs <- ukhls_merged$b_fihhmngrs_dv
ukhls_merged$ukhls_grs[ukhls_merged$ukhls_grs < 0] <- NA
ukhls_merged$ukhls_net1 <- ukhls_merged$b_fihhmnnet1_dv
ukhls_merged$ukhls_net1[ukhls_merged$ukhls_net1 < 0] <- NA
cat("UKHLS b valid income obs:", sum(!is.na(ukhls_merged$ukhls_grs)), "\n")

# ---- 7. Merge on pidp to get spanning individuals ----
bhps_small <- bhps_merged[, c("pidp", "bhps_grs")]
ukhls_small <- ukhls_merged[, c("pidp", "ukhls_grs", "ukhls_net1"), drop = FALSE]
spanning <- merge(bhps_small, ukhls_small, by = "pidp")
cat("\nSpanning individuals (in both br and wave b):", nrow(spanning), "\n")

# Filter to those with valid income in both waves
spanning_valid <- spanning[!is.na(spanning$bhps_grs) & !is.na(spanning$ukhls_grs), ]
cat("Spanning with valid income both waves:", nrow(spanning_valid), "\n")

# ---- 8. Tercile concordance ----
# Compute terciles within each wave's distribution of spanning individuals
bhps_q <- quantile(spanning_valid$bhps_grs, probs = c(1 / 3, 2 / 3), na.rm = TRUE)
ukhls_q <- quantile(spanning_valid$ukhls_grs, probs = c(1 / 3, 2 / 3), na.rm = TRUE)

cat("\nBHPS gross income tercile cutoffs:", round(bhps_q, 0), "\n")
cat("UKHLS gross income tercile cutoffs:", round(ukhls_q, 0), "\n")

spanning_valid$bhps_tercile <- cut(spanning_valid$bhps_grs,
  breaks = c(-Inf, bhps_q, Inf),
  labels = c("L", "M", "H")
)
spanning_valid$ukhls_tercile <- cut(spanning_valid$ukhls_grs,
  breaks = c(-Inf, ukhls_q, Inf),
  labels = c("L", "M", "H")
)

concordance_exact <- mean(spanning_valid$bhps_tercile == spanning_valid$ukhls_tercile, na.rm = TRUE)
concordance_adj <- mean(abs(as.integer(spanning_valid$bhps_tercile) -
  as.integer(spanning_valid$ukhls_tercile)) <= 1, na.rm = TRUE)

cat("\nTercile concordance (exact same bin):", round(concordance_exact * 100, 1), "%\n")
cat("Tercile concordance (within 1 bin):", round(concordance_adj * 100, 1), "%\n")

# Cross-tabulation
cat("\nCross-tabulation BHPS tercile x UKHLS tercile:\n")
print(table(spanning_valid$bhps_tercile, spanning_valid$ukhls_tercile,
  dnn = c("BHPS_tercile", "UKHLS_tercile")
))

# ---- 9. Spearman correlation ----
spearman_rho <- cor(spanning_valid$bhps_grs, spanning_valid$ukhls_grs,
  method = "spearman", use = "complete.obs"
)
cat("\nSpearman rho (gross income):", round(spearman_rho, 4), "\n")

# ---- 10. Mean absolute log-ratio ----
# Only for positive values
pos_mask <- spanning_valid$bhps_grs > 0 & spanning_valid$ukhls_grs > 0
log_ratio <- log(spanning_valid$ukhls_grs[pos_mask]) - log(spanning_valid$bhps_grs[pos_mask])
malr <- mean(abs(log_ratio), na.rm = TRUE)
med_log_ratio <- median(log_ratio, na.rm = TRUE)
cat("Mean absolute log-ratio:", round(malr, 4), "\n")
cat(
  "Median log-ratio (USoc/BHPS):", round(med_log_ratio, 4),
  " (exp:", round(exp(med_log_ratio), 3), "x)\n"
)

# ---- 11. Net income Spearman (UKHLS net1 vs BHPS gross as proxy) ----
spanning_net <- spanning[!is.na(spanning$bhps_grs) & !is.na(spanning$ukhls_net1), ]
if (nrow(spanning_net) > 100) {
  rho_net <- cor(spanning_net$bhps_grs, spanning_net$ukhls_net1,
    method = "spearman", use = "complete.obs"
  )
  cat("Spearman rho (BHPS br gross vs UKHLS b net1):", round(rho_net, 4), "\n")
}

# ---- 12. Summary statistics ----
cat("\n=== Summary ===\n")
cat("N spanning individuals total:", nrow(spanning), "\n")
cat("N spanning with valid income (both waves):", nrow(spanning_valid), "\n")
cat("Tercile exact concordance:", round(concordance_exact * 100, 1), "%\n")
cat("Spearman rho:", round(spearman_rho, 4), "\n")
cat("Mean absolute log-ratio:", round(malr, 4), "\n")

# ---- 13. Save JSON results ----
out_dir <- Sys.getenv("RESULTS_DIR", file.path(get_script_dir(), "..", "..", "..", "results", "panel_methodology", "harmonisation"))
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_json <- file.path(out_dir, paste0("income_calibration_", TODAY, ".json"))

result <- list(
  audit_date = TODAY,
  note = paste0(
    "Task spec variables fihhmn and fihhmnnet3_dv do not exist in UKDA-6614. ",
    "Calibration uses fihhmngrs_dv (gross household income, month before interview) ",
    "available identically in both BHPS and UKHLS hhresp files. ",
    "BHPS hhneti (net) and UKHLS fihhmnnet1_dv (net, no deductions) are not ",
    "directly comparable due to different derivation methods."
  ),
  income_variable_used = "fihhmngrs_dv (gross household income, month before interview)",
  bhps_wave = "br (last BHPS wave)",
  ukhls_wave = "b (first UKHLS wave with BHPS cohort, 2010-12)",
  n_spanning_total = nrow(spanning),
  n_spanning_valid_income = nrow(spanning_valid),
  bhps_tercile_cutoffs_gbp_monthly = as.list(round(bhps_q, 0)),
  ukhls_tercile_cutoffs_gbp_monthly = as.list(round(ukhls_q, 0)),
  tercile_exact_concordance_pct = round(concordance_exact * 100, 2),
  tercile_within1_concordance_pct = round(concordance_adj * 100, 2),
  spearman_rho_gross = round(spearman_rho, 4),
  mean_absolute_log_ratio = round(malr, 4),
  median_log_ratio_ukhls_over_bhps = round(med_log_ratio, 4),
  median_income_ratio_ukhls_over_bhps = round(exp(med_log_ratio), 4),
  s12_verdict = ifelse(concordance_exact >= 0.80,
    "RESOLVED: concordance >= 80%",
    "FLAG: concordance < 80% — requires calibration review"
  )
)

write(toJSON(result, pretty = TRUE, auto_unbox = TRUE), out_json)
cat("\nJSON written to:", out_json, "\n")
cat("Done.\n")
