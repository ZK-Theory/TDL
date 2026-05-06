# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Locate xhhrel files and inspect structure for T0.11 FOO cluster build.

DATA_ROOT <- "c:/Users/steph/TDL/data/UKDA-6614-tab/tab"

bhps_files  <- list.files(file.path(DATA_ROOT, "bhps"),  pattern = "xhhrel", full.names = FALSE)
ukhls_files <- list.files(file.path(DATA_ROOT, "ukhls"), pattern = "xhhrel", full.names = FALSE)

cat("BHPS xhhrel files:", paste(bhps_files, collapse = ", "), "\n")
cat("UKHLS xhhrel files:", paste(ukhls_files, collapse = ", "), "\n")

# Inspect the first BHPS xhhrel file found
if (length(bhps_files) > 0) {
  fpath <- file.path(DATA_ROOT, "bhps", bhps_files[1])
  header <- trimws(strsplit(readLines(fpath, n = 1), "\t")[[1]])
  cat("\n--- BHPS", bhps_files[1], "---\n")
  cat("Columns (", length(header), "):", paste(header, collapse = ", "), "\n")
  df <- read.delim(fpath, nrows = 8, sep = "\t", stringsAsFactors = FALSE,
                   quote = "", fill = TRUE, na.strings = "")
  print(df)
  cat("Total rows:", nrow(read.delim(fpath, sep = "\t", stringsAsFactors = FALSE,
                                      quote = "", fill = TRUE, na.strings = "")), "\n")
}

# Inspect the first UKHLS xhhrel file found
if (length(ukhls_files) > 0) {
  fpath <- file.path(DATA_ROOT, "ukhls", ukhls_files[1])
  header <- trimws(strsplit(readLines(fpath, n = 1), "\t")[[1]])
  cat("\n--- UKHLS", ukhls_files[1], "---\n")
  cat("Columns (", length(header), "):", paste(header, collapse = ", "), "\n")
  df <- read.delim(fpath, nrows = 8, sep = "\t", stringsAsFactors = FALSE,
                   quote = "", fill = TRUE, na.strings = "")
  print(df)
}
