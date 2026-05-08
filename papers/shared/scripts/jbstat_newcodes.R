# Check frequencies and labels for unexpected jbstat codes 12-15 in UKHLS waves k-o

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

DATA_ROOT <- Sys.getenv("TDL_DATA_ROOT", "")
if (!nzchar(DATA_ROOT)) {
  DATA_ROOT <- normalizePath(file.path(get_script_dir(), "..", "..", "..", "data", "UKDA-6614-tab", "tab"), mustWork = FALSE)
}

for (w in c("k", "l", "m", "n", "o")) {
  fname <- file.path(DATA_ROOT, "ukhls", paste0(w, "_indresp.tab"))
  header <- strsplit(readLines(fname, n = 1), "\t")[[1]]
  header <- trimws(header)

  jb_idx <- match(paste0(w, "_jbstat"), header)
  if (is.na(jb_idx)) {
    warning(sprintf("Missing column %s in %s; skipping wave %s", paste0(w, "_jbstat"), fname, w))
    next
  }
  if (sum(header == paste0(w, "_jbstat")) > 1) {
    warning(sprintf("Duplicate column name %s in %s; using first occurrence", paste0(w, "_jbstat"), fname))
  }
  jbl_idx <- match(paste0(w, "_jbstatl"), header)
  if (!is.na(jbl_idx) && sum(header == paste0(w, "_jbstatl")) > 1) {
    warning(sprintf("Duplicate column name %s in %s; using first occurrence", paste0(w, "_jbstatl"), fname))
  }

  col_classes <- rep("NULL", length(header))
  col_classes[jb_idx] <- "integer"
  if (!is.na(jbl_idx)) col_classes[jbl_idx] <- "character"

  df <- read.delim(fname,
    header = TRUE, sep = "\t",
    colClasses = col_classes, stringsAsFactors = FALSE,
    quote = "", fill = TRUE, na.strings = ""
  )

  jbstat_col <- df[[paste0(w, "_jbstat")]]
  high_codes <- jbstat_col[!is.na(jbstat_col) & jbstat_col >= 10]
  cat("Wave", w, "- codes >= 10:\n")
  print(sort(table(high_codes), decreasing = TRUE))

  if (length(jbl_idx) > 0 && paste0(w, "_jbstatl") %in% names(df)) {
    jbstatl_col <- df[[paste0(w, "_jbstatl")]]
    new_mask <- !is.na(jbstat_col) & jbstat_col %in% 12:15
    if (any(new_mask)) {
      cat("  Labels for codes 12-15:\n")
      combo <- unique(data.frame(
        code = jbstat_col[new_mask],
        label = jbstatl_col[new_mask]
      ))
      combo <- combo[order(combo$code), ]
      print(combo)
    }
  }
  cat("\n")
}
