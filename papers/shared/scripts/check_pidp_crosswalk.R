# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Find crosswalk between BHPS harmonised pidp and UKHLS pidp

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

read_col <- function(fpath, col) {
  if (!file.exists(fpath)) {
    stop(sprintf("File not found: %s", fpath))
  }
  header <- trimws(strsplit(readLines(fpath, n = 1), "\t")[[1]])
  if (!col %in% header) {
    stop(sprintf("missing column: %s", col))
  }
  if (sum(header == col) > 1) {
    warning(sprintf("duplicate column name: %s; using first occurrence", col))
  }
  idx <- match(col, header)
  col_classes <- rep("NULL", length(header))
  col_classes[idx] <- NA
  df <- read.delim(fpath,
    header = TRUE, sep = "\t",
    colClasses = col_classes, stringsAsFactors = FALSE,
    quote = "", fill = TRUE, na.strings = ""
  )
  suppressWarnings(as.numeric(df[[idx]]))
}

# xwavedat full column list
xwave_file <- file.path(DATA_ROOT, "ukhls", "xwavedat.tab")
all_cols <- trimws(strsplit(readLines(xwave_file, n = 1), "\t")[[1]])
cat("All xwavedat columns (", length(all_cols), "):\n")
cat(paste(all_cols, collapse = "\n"), "\n")
