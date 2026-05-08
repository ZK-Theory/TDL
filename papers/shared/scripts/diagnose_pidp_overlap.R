# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Diagnose why pidp merge found 0 spanning individuals.
# Per user guide §2.3.2.1: pidp works across harmonised BHPS and UKHLS files.
# Read as character first to rule out numeric conversion artefacts.

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
  DATA_ROOT <- normalizePath(file.path(get_script_dir(), "..", "..", "data", "UKDA-6614-tab", "tab"), mustWork = FALSE)
}

check_file <- function(fpath) {
  if (!file.exists(fpath)) {
    stop(sprintf("Required file not found: %s", fpath))
  }
}

read_pidp_raw <- function(fpath) {
  check_file(fpath)
  header <- trimws(strsplit(readLines(fpath, n = 1), "\t")[[1]])
  idx <- match("pidp", header)
  if (is.na(idx)) {
    stop(sprintf("ERROR: no pidp column in %s", basename(fpath)))
  }
  if (sum(header == "pidp") > 1) {
    warning("duplicate pidp column found; using first occurrence")
  }
  col_classes <- rep("NULL", length(header))
  col_classes[idx] <- "character"
  df <- read.delim(fpath,
    header = TRUE, sep = "\t",
    colClasses = col_classes, stringsAsFactors = FALSE,
    quote = "", fill = TRUE, na.strings = ""
  )
  trimws(df[["pidp"]])
}

cat("Reading BHPS br_indresp pidp...\n")
bhps_raw <- read_pidp_raw(file.path(DATA_ROOT, "bhps", "br_indresp.tab"))
cat("  N rows:", length(bhps_raw), "\n")
cat("  First 5 raw values:", paste(head(bhps_raw, 5), collapse = " | "), "\n")
bhps_clean <- bhps_raw[!is.na(bhps_raw) & nchar(bhps_raw) > 0 & bhps_raw != "NA"]
cat("  Non-empty:", length(bhps_clean), "\n")

cat("\nReading UKHLS a_indresp pidp...\n")
ukhls_raw <- read_pidp_raw(file.path(DATA_ROOT, "ukhls", "a_indresp.tab"))
cat("  N rows:", length(ukhls_raw), "\n")
cat("  First 5 raw values:", paste(head(ukhls_raw, 5), collapse = " | "), "\n")
ukhls_clean <- ukhls_raw[!is.na(ukhls_raw) & nchar(ukhls_raw) > 0 & ukhls_raw != "NA"]
cat("  Non-empty:", length(ukhls_clean), "\n")

# Numeric ranges
bhps_num <- suppressWarnings(as.numeric(bhps_clean))
ukhls_num <- suppressWarnings(as.numeric(ukhls_clean))
cat("\nBHPS pidp numeric range:", min(bhps_num, na.rm = TRUE), "–", max(bhps_num, na.rm = TRUE), "\n")
cat("UKHLS pidp numeric range:", min(ukhls_num, na.rm = TRUE), "–", max(ukhls_num, na.rm = TRUE), "\n")
cat("BHPS NA after as.numeric:", sum(is.na(bhps_num)), "\n")
cat("UKHLS NA after as.numeric:", sum(is.na(ukhls_num)), "\n")

# Character-level intersection
overlap_char <- intersect(bhps_clean, ukhls_clean)
cat("\nOverlap (character match):", length(overlap_char), "\n")
if (length(overlap_char) > 0) {
  cat("Sample overlap pidp values:", paste(head(overlap_char, 5), collapse = " | "), "\n")
}

# Numeric-level intersection
bhps_set <- bhps_num[!is.na(bhps_num)]
ukhls_set <- ukhls_num[!is.na(ukhls_num)]
overlap_num <- length(intersect(bhps_set, ukhls_set))
cat("Overlap (numeric match):", overlap_num, "\n")

cat("\nDone.\n")
