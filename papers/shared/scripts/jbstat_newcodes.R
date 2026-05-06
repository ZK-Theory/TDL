# Check frequencies and labels for unexpected jbstat codes 12-15 in UKHLS waves k-o
DATA_ROOT <- "c:/Users/steph/TDL/data/UKDA-6614-tab/tab"

for (w in c("k", "l", "m", "n", "o")) {
  fname <- file.path(DATA_ROOT, "ukhls", paste0(w, "_indresp.tab"))
  header <- strsplit(readLines(fname, n = 1), "\t")[[1]]
  header <- trimws(header)

  jb_idx <- which(header == paste0(w, "_jbstat"))
  jbl_idx <- which(header == paste0(w, "_jbstatl"))

  col_classes <- rep("NULL", length(header))
  col_classes[jb_idx] <- "integer"
  if (length(jbl_idx) > 0) col_classes[jbl_idx] <- "character"

  df <- read.delim(fname, header = TRUE, sep = "\t",
                   colClasses = col_classes, stringsAsFactors = FALSE,
                   quote = "", fill = TRUE, na.strings = "")

  jbstat_col <- df[[paste0(w, "_jbstat")]]
  high_codes <- jbstat_col[!is.na(jbstat_col) & jbstat_col >= 10]
  cat("Wave", w, "- codes >= 10:\n")
  print(sort(table(high_codes), decreasing = TRUE))

  if (length(jbl_idx) > 0 && paste0(w, "_jbstatl") %in% names(df)) {
    jbstatl_col <- df[[paste0(w, "_jbstatl")]]
    new_mask <- !is.na(jbstat_col) & jbstat_col %in% 12:15
    if (any(new_mask)) {
      cat("  Labels for codes 12-15:\n")
      combo <- unique(data.frame(code = jbstat_col[new_mask],
                                 label = jbstatl_col[new_mask]))
      combo <- combo[order(combo$code), ]
      print(combo)
    }
  }
  cat("\n")
}
