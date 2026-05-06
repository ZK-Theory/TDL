# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Diagnose why pidp merge found 0 spanning individuals.
# Per user guide §2.3.2.1: pidp works across harmonised BHPS and UKHLS files.
# Read as character first to rule out numeric conversion artefacts.

DATA_ROOT <- "c:/Users/steph/TDL/data/UKDA-6614-tab/tab"

read_pidp_raw <- function(fpath) {
  header <- trimws(strsplit(readLines(fpath, n = 1), "\t")[[1]])
  idx <- which(header == "pidp")
  if (!length(idx)) { cat("ERROR: no pidp column in", basename(fpath), "\n"); return(NULL) }
  col_classes <- rep("NULL", length(header))
  col_classes[idx] <- "character"
  df <- read.delim(fpath, header = TRUE, sep = "\t",
                   colClasses = col_classes, stringsAsFactors = FALSE,
                   quote = "", fill = TRUE, na.strings = "")
  trimws(df[[1]])
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
bhps_num  <- suppressWarnings(as.numeric(bhps_clean))
ukhls_num <- suppressWarnings(as.numeric(ukhls_clean))
cat("\nBHPS pidp numeric range:", min(bhps_num, na.rm=TRUE), "–", max(bhps_num, na.rm=TRUE), "\n")
cat("UKHLS pidp numeric range:", min(ukhls_num, na.rm=TRUE), "–", max(ukhls_num, na.rm=TRUE), "\n")
cat("BHPS NA after as.numeric:", sum(is.na(bhps_num)), "\n")
cat("UKHLS NA after as.numeric:", sum(is.na(ukhls_num)), "\n")

# Character-level intersection
overlap_char <- intersect(bhps_clean, ukhls_clean)
cat("\nOverlap (character match):", length(overlap_char), "\n")
if (length(overlap_char) > 0) {
  cat("Sample overlap pidp values:", paste(head(overlap_char, 5), collapse = " | "), "\n")
}

# Numeric-level intersection
bhps_set  <- bhps_num[!is.na(bhps_num)]
ukhls_set <- ukhls_num[!is.na(ukhls_num)]
overlap_num <- length(intersect(bhps_set, ukhls_set))
cat("Overlap (numeric match):", overlap_num, "\n")

cat("\nDone.\n")
