# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Find crosswalk between BHPS harmonised pidp and UKHLS pidp

DATA_ROOT <- "c:/Users/steph/TDL/data/UKDA-6614-tab/tab"

read_col <- function(fpath, col) {
  header <- trimws(strsplit(readLines(fpath, n = 1), "\t")[[1]])
  idx <- which(header == col)
  if (!length(idx)) return(NULL)
  col_classes <- rep("NULL", length(header))
  col_classes[idx] <- NA
  df <- read.delim(fpath, header = TRUE, sep = "\t",
                   colClasses = col_classes, stringsAsFactors = FALSE,
                   quote = "", fill = TRUE, na.strings = "")
  suppressWarnings(as.numeric(df[[1]]))
}

# xwavedat full column list
xwave_file <- file.path(DATA_ROOT, "ukhls", "xwavedat.tab")
all_cols <- trimws(strsplit(readLines(xwave_file, n = 1), "\t")[[1]])
cat("All xwavedat columns (", length(all_cols), "):\n")
cat(paste(all_cols, collapse = "\n"), "\n")
