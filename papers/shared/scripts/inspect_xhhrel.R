# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Locate xhhrel files and inspect structure for T0.11 FOO cluster build.

DATA_ROOT <- Sys.getenv("TDL_DATA_ROOT", "")
if (!nzchar(DATA_ROOT)) {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("--file=", args, value = TRUE)
  script_dir <- if (length(file_arg) > 0) dirname(normalizePath(sub("^--file=", "", file_arg[1]))) else normalizePath(".")
  DATA_ROOT <- normalizePath(file.path(script_dir, "..", "..", "..", "data", "UKDA-6614-tab", "tab"), mustWork = FALSE)
}

bhps_files <- list.files(file.path(DATA_ROOT, "bhps"), pattern = "xhhrel", full.names = FALSE)
ukhls_files <- list.files(file.path(DATA_ROOT, "ukhls"), pattern = "xhhrel", full.names = FALSE)

cat("BHPS xhhrel files:", paste(bhps_files, collapse = ", "), "\n")
cat("UKHLS xhhrel files:", paste(ukhls_files, collapse = ", "), "\n")

# Inspect the first BHPS xhhrel file found
if (length(bhps_files) > 0) {
  fpath <- file.path(DATA_ROOT, "bhps", bhps_files[1])
  header <- trimws(strsplit(readLines(fpath, n = 1), "\t")[[1]])
  cat("\n--- BHPS", bhps_files[1], "---\n")
  cat("Columns (", length(header), "):", paste(header, collapse = ", "), "\n")
  df <- read.delim(fpath,
    nrows = 8, sep = "\t", stringsAsFactors = FALSE,
    quote = "", fill = TRUE, na.strings = ""
  )
  print(df)
  if (!requireNamespace("R.utils", quietly = TRUE)) {
    stop("R.utils is required to count lines efficiently in inspect_xhhrel.R")
  }
  total_rows <- R.utils::countLines(fpath)
  data_rows <- total_rows - 1
  cat("Total rows (excluding header):", data_rows, "\n")
}

# Inspect the first UKHLS xhhrel file found
if (length(ukhls_files) > 0) {
  fpath <- file.path(DATA_ROOT, "ukhls", ukhls_files[1])
  header <- trimws(strsplit(readLines(fpath, n = 1), "\t")[[1]])
  cat("\n--- UKHLS", ukhls_files[1], "---\n")
  cat("Columns (", length(header), "):", paste(header, collapse = ", "), "\n")
  df <- read.delim(fpath,
    nrows = 8, sep = "\t", stringsAsFactors = FALSE,
    quote = "", fill = TRUE, na.strings = ""
  )
  print(df)
}
