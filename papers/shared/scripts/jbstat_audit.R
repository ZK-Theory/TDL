# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Verify jbstat harmonisation across harmonised BHPS (ba-br) and UKHLS (a-o) waves.
# Produces per-wave coding table for the E/U/I 9-state crossing.

library(jsonlite)

DATA_ROOT <- Sys.getenv("TDL_DATA_ROOT", "")
if (!nzchar(DATA_ROOT)) {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("--file=", args, value = TRUE)
  script_dir <- if (length(file_arg) > 0) dirname(normalizePath(sub("^--file=", "", file_arg[1]), mustWork = FALSE)) else normalizePath(".") DATA_ROOT <- normalizePath(file.path(script_dir, "..", "..", "..", "data", "UKDA-6614-tab", "tab"), mustWork = FALSE)
}
TODAY <- format(Sys.Date(), "%Y-%m-%d")

# ---- Helper: read jbstat from a single indresp.tab file ----
# In harmonised BHPS: column is "{wave}_jbstat" (e.g. "ba_jbstat")
# In UKHLS: column is "{wave}_jbstat" (e.g. "a_jbstat")
read_jbstat <- function(filepath, wave) {
  header <- strsplit(readLines(filepath, n = 1), "\t")[[1]]
  header <- trimws(header)
  target_col <- paste0(wave, "_jbstat")
  col_idx <- which(header == target_col)
  if (length(col_idx) == 0) {
    return(NULL)
  }

  # Build colClasses: only read jbstat column
  col_classes <- rep("NULL", length(header))
  col_classes[col_idx] <- "integer"

  df <- tryCatch(
    read.delim(filepath,
      header = TRUE, sep = "\t",
      colClasses = col_classes, stringsAsFactors = FALSE,
      quote = "", fill = TRUE, na.strings = ""
    ),
    error = function(e) NULL
  )
  if (is.null(df)) {
    return(NULL)
  }
  df[[1]]
}

# ---- E/U/I bin mapping ----
# Based on BHPS/USoc documentation and harmonised BHPS user guide.
# Standard jbstat codes:
#   1 = Self-employed
#   2 = Employed (paid employment)
#   3 = Unemployed (ILO)
#   4 = Retired
#   5 = Maternity/paternity leave
#   6 = Family care/home
#   7 = Full-time student
#   8 = Long-term sick/disabled
#   9 = Government training scheme
#  10 = Unpaid voluntary work (UKHLS waves c+; not in BHPS)
#  11 = Waiting to take up a job (UKHLS; maps differently)
#  97 = Something else
# Negative codes: missing/inapplicable

assign_bin <- function(code) {
  employed <- c(1L, 2L, 5L) # Self-emp, employed, mat/pat leave
  unemployed <- c(3L, 9L) # ILO unemployed, govt training
  inactive <- c(4L, 6L, 7L, 8L, 10L, 11L, 97L)
  dplyr_like <- function(x, choices) x %in% choices

  ifelse(code %in% employed, "E",
    ifelse(code %in% unemployed, "U",
      ifelse(code %in% inactive, "I", NA_character_)
    )
  )
}

# ---- Process all waves ----
results <- list()

# Harmonised BHPS waves: ba through br
bhps_waves <- paste0("b", letters[1:18])
for (w in bhps_waves) {
  fname <- file.path(DATA_ROOT, "bhps", paste0(w, "_indresp.tab"))
  if (!file.exists(fname)) {
    results[[w]] <- list(
      wave = w, survey = "BHPS", n = 0, codes = NULL,
      note = "file not found"
    )
    next
  }
  vals <- read_jbstat(fname, w)
  if (is.null(vals)) {
    results[[w]] <- list(
      wave = w, survey = "BHPS", n = NA, codes = NULL,
      note = "jbstat not found in file"
    )
    next
  }
  pos_vals <- vals[vals > 0] # exclude missing/inapplicable
  tab <- sort(table(pos_vals), decreasing = TRUE)
  code_vec <- as.integer(names(tab))
  results[[w]] <- list(
    wave = w,
    survey = "BHPS_harmonised",
    n_total = length(vals),
    n_valid = length(pos_vals),
    codes = as.list(tab),
    unique_pos = sort(unique(pos_vals)),
    has_code10 = 10L %in% pos_vals,
    has_code11 = 11L %in% pos_vals,
    note = ""
  )
}

# UKHLS waves: a through o
ukhls_waves <- letters[1:15]
for (w in ukhls_waves) {
  fname <- file.path(DATA_ROOT, "ukhls", paste0(w, "_indresp.tab"))
  if (!file.exists(fname)) {
    results[[w]] <- list(
      wave = w, survey = "UKHLS", n = 0, codes = NULL,
      note = "file not found"
    )
    next
  }
  vals <- read_jbstat(fname, w)
  if (is.null(vals)) {
    results[[w]] <- list(
      wave = w, survey = "UKHLS", n = NA, codes = NULL,
      note = "jbstat not found in file"
    )
    next
  }
  pos_vals <- vals[vals > 0]
  tab <- sort(table(pos_vals), decreasing = TRUE)
  results[[w]] <- list(
    wave = w,
    survey = "UKHLS",
    n_total = length(vals),
    n_valid = length(pos_vals),
    codes = as.list(tab),
    unique_pos = sort(unique(pos_vals)),
    has_code10 = 10L %in% pos_vals,
    has_code11 = 11L %in% pos_vals,
    note = ""
  )
}

# ---- Build per-wave coding map ----
wave_summaries <- lapply(names(results), function(w) {
  r <- results[[w]]
  if (is.null(r$unique_pos) || length(r$unique_pos) == 0) {
    return(r)
  }

  # Map each observed positive code to E/U/I bin
  bins <- setNames(assign_bin(r$unique_pos), as.character(r$unique_pos))

  # Summarise bins
  E_codes <- r$unique_pos[bins == "E"]
  U_codes <- r$unique_pos[bins == "U"]
  I_codes <- r$unique_pos[bins == "I"]
  unclassified <- r$unique_pos[is.na(bins)]

  c(r, list(
    E_codes = E_codes,
    U_codes = U_codes,
    I_codes = I_codes,
    unclassified = unclassified,
    code_bin_map = as.list(bins)
  ))
})
names(wave_summaries) <- names(results)

# ---- Detect inconsistencies ----
# Reference: codes 1,2,5 -> E; 3,9 -> U; 4,6,7,8,10,11,97 -> I
inconsistencies <- list()

# Check whether any wave has codes not in expected set
expected_positive_codes <- c(1L, 2L, 3L, 4L, 5L, 6L, 7L, 8L, 9L, 10L, 11L, 97L)
for (w in names(wave_summaries)) {
  r <- wave_summaries[[w]]
  if (is.null(r$unique_pos)) next
  unexpected <- setdiff(r$unique_pos, expected_positive_codes)
  if (length(unexpected) > 0) {
    inconsistencies[[w]] <- paste0(
      "Wave ", w, ": unexpected jbstat codes: ",
      paste(unexpected, collapse = ", ")
    )
  }
}

# Check for code 10/11 presence (UKHLS-specific)
code10_waves <- names(which(sapply(wave_summaries, function(r) isTRUE(r$has_code10))))
code11_waves <- names(which(sapply(wave_summaries, function(r) isTRUE(r$has_code11))))

# ---- Save JSON output ----
out_dir <- "c:/Users/steph/TDL/results/panel_methodology/harmonisation"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_json <- file.path(out_dir, paste0("jbstat_coding_", TODAY, ".json"))

output_list <- list(
  audit_date = TODAY,
  waves_processed = names(wave_summaries),
  wave_details = wave_summaries,
  code10_waves = code10_waves,
  code11_waves = code11_waves,
  unexpected_codes = inconsistencies,
  e_codes_standard = c(1L, 2L, 5L),
  u_codes_standard = c(3L, 9L),
  i_codes_standard = c(4L, 6L, 7L, 8L, 10L, 11L, 97L),
  notes = paste0(
    "Code 10 (unpaid voluntary work) and code 11 (waiting to take up a job) ",
    "appear in UKHLS only. The harmonised BHPS user guide example code recodes ",
    "these to 97 (something else). For the 9-state crossing, codes 10 and 11 ",
    "are assigned to I (inactive) as they represent non-employment statuses."
  )
)
write(toJSON(output_list, pretty = TRUE, auto_unbox = TRUE), out_json)
cat("JSON written to:", out_json, "\n")

# ---- Print summary table ----
cat("\n=== Per-Wave jbstat Coding Summary ===\n")
cat(sprintf(
  "%-8s %-20s %-12s %-12s %-12s %-6s %-6s\n",
  "Wave", "Survey", "N_valid", "E_codes", "U_codes", "c10", "c11"
))
cat(paste(rep("-", 80), collapse = ""), "\n")
for (w in names(wave_summaries)) {
  r <- wave_summaries[[w]]
  if (is.null(r$unique_pos)) {
    cat(sprintf("%-8s %-20s %-12s\n", w, r$survey, r$note))
    next
  }
  cat(sprintf(
    "%-8s %-20s %-12d %-12s %-12s %-6s %-6s\n",
    w,
    r$survey,
    r$n_valid,
    paste(r$E_codes, collapse = ","),
    paste(r$U_codes, collapse = ","),
    ifelse(isTRUE(r$has_code10), "YES", "no"),
    ifelse(isTRUE(r$has_code11), "YES", "no")
  ))
}

cat("\nCode 10 present in waves:", paste(code10_waves, collapse = ", "), "\n")
cat("Code 11 present in waves:", paste(code11_waves, collapse = ", "), "\n")
if (length(inconsistencies) > 0) {
  cat("\nUnexpected codes:\n")
  for (msg in inconsistencies)
    cat(" ", msg, "\n")
} else {
  cat("\nNo unexpected codes beyond {1-11, 97} found.\n")
}
cat("\nDone.\n")
