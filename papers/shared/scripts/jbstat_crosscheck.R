# Cross-check jbstat codes 12+ with k_employ from indall
# and investigate their proper E/U/I classification
DATA_ROOT <- "c:/Users/steph/TDL/data/UKDA-6614-tab/tab"

# Read k_employ from indall and k_jbstat from indresp, merge on pidp
fname_all <- file.path(DATA_ROOT, "ukhls", "k_indall.tab")
header_all <- strsplit(readLines(fname_all, n = 1), "\t")[[1]]
header_all <- trimws(header_all)
pidp_idx_a <- which(header_all == "pidp")
emp_idx <- which(header_all == "k_employ")
col_a <- rep("NULL", length(header_all))
col_a[pidp_idx_a] <- "integer"
col_a[emp_idx] <- "integer"
df_all <- read.delim(fname_all, header = TRUE, sep = "\t",
                     colClasses = col_a, stringsAsFactors = FALSE,
                     quote = "", fill = TRUE, na.strings = "")
cat("k_employ values:\n")
print(table(df_all$k_employ))

# Cross-tab jbstat (12+) with k_employ
fname_k <- file.path(DATA_ROOT, "ukhls", "k_indresp.tab")
header_k <- strsplit(readLines(fname_k, n = 1), "\t")[[1]]
header_k <- trimws(header_k)
pidp_idx_k <- which(header_k == "pidp")
jb_idx_k <- which(header_k == "k_jbstat")
col_k <- rep("NULL", length(header_k))
col_k[pidp_idx_k] <- "integer"
col_k[jb_idx_k] <- "integer"
df_k <- read.delim(fname_k, header = TRUE, sep = "\t",
                   colClasses = col_k, stringsAsFactors = FALSE,
                   quote = "", fill = TRUE, na.strings = "")

merged <- merge(df_k, df_all, by = "pidp")
cat("\nCross-tab k_jbstat vs k_employ for codes 12-15:\n")
mask_new <- merged$k_jbstat %in% 12:15
cat("n with codes 12-15:", sum(mask_new, na.rm = TRUE), "\n")
print(table(merged$k_jbstat[mask_new], merged$k_employ[mask_new]))

cat("\nFor reference, codes 1-5 vs k_employ:\n")
mask_std <- merged$k_jbstat %in% 1:5
print(table(merged$k_jbstat[mask_std], merged$k_employ[mask_std]))
