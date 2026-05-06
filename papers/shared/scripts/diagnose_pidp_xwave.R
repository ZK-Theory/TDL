# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Check BHPS br pidp against xwavedat (all UKHLS waves) to confirm
# pidp crosswalk works, then find earliest UKHLS wave for each spanning individual.

DATA_ROOT <- "c:/Users/steph/TDL/data/UKDA-6614-tab/tab"

read_cols_char <- function(fpath, cols) {
  header <- trimws(strsplit(readLines(fpath, n = 1), "\t")[[1]])
  idx <- match(cols, header)
  ok  <- !is.na(idx)
  col_classes <- rep("NULL", length(header))
  col_classes[idx[ok]] <- "character"
  df <- read.delim(fpath, header = TRUE, sep = "\t",
                   colClasses = col_classes, stringsAsFactors = FALSE,
                   quote = "", fill = TRUE, na.strings = "")
  for (col in names(df)) df[[col]] <- trimws(df[[col]])
  df
}

# ---- 1. BHPS br pidp ----
cat("Reading BHPS br_indresp pidp...\n")
bhps_br <- read_cols_char(file.path(DATA_ROOT, "bhps", "br_indresp.tab"), "pidp")
bhps_pidp <- unique(bhps_br$pidp[nchar(bhps_br$pidp) > 0])
cat("  Unique BHPS br pidp:", length(bhps_pidp), "\n")

# ---- 2. xwavedat pidp + memorig ----
cat("Reading xwavedat (pidp, memorig)...\n")
xwave <- read_cols_char(file.path(DATA_ROOT, "ukhls", "xwavedat.tab"), c("pidp", "memorig"))
xwave$memorig_n <- suppressWarnings(as.integer(xwave$memorig))
cat("  Total rows:", nrow(xwave), "\n")
cat("  memorig=1 (BHPS-origin):", sum(xwave$memorig_n == 1, na.rm = TRUE), "\n")

xwave_pidp <- unique(xwave$pidp[nchar(xwave$pidp) > 0])
cat("  Unique xwavedat pidp:", length(xwave_pidp), "\n")

# ---- 3. Intersection: BHPS br ∩ xwavedat (any UKHLS wave) ----
overlap_xwave <- intersect(bhps_pidp, xwave_pidp)
cat("\nBHPS br ∩ xwavedat (any UKHLS wave):", length(overlap_xwave), "\n")

# ---- 4. Check across individual UKHLS waves ----
cat("\nChecking BHPS br pidp against each UKHLS wave a_indresp – o_indresp:\n")
ukhls_waves <- c("a","b","c","d","e","f","g","h","i","j","k","l","m","n","o")
wave_counts <- integer(length(ukhls_waves))
names(wave_counts) <- ukhls_waves
for (w in ukhls_waves) {
  fpath <- file.path(DATA_ROOT, "ukhls", paste0(w, "_indresp.tab"))
  if (!file.exists(fpath)) { wave_counts[w] <- NA; next }
  dat <- read_cols_char(fpath, "pidp")
  wave_pidp <- unique(dat$pidp[nchar(dat$pidp) > 0])
  wave_counts[w] <- length(intersect(bhps_pidp, wave_pidp))
}
for (w in ukhls_waves) cat("  Wave", w, ":", wave_counts[w], "\n")

cat("\nDone.\n")
