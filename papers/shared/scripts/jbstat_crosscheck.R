# Cross-check jbstat codes 12+ with k_employ from indall
# and investigate their proper E/U/I classification
DATA_ROOT <- "c:/Users/steph/TDL/data/UKDA-6614-tab/tab"

# Read k_employ from indall and k_jbstat from indresp, merge on pidp
fname_all <- file.path(DATA_ROOT, "ukhls", "k_indall.tab")
header_all <- strsplit(readLines(fname_all, n = 1), "\t")[[1]]
header_all <- trimws(header_all)
pidp_idx_a <- match("pidp", header_all)
if (is.na(pidp_idx_a)) stop("missing column: pidp in k_indall.tab")
if (sum(header_all == "pidp") > 1) warning("duplicate pidp column in k_indall.tab; using first occurrence")
emp_idx <- match("k_employ", header_all)
if (is.na(emp_idx)) stop("missing column: k_employ in k_indall.tab")
if (sum(header_all == "k_employ") > 1) warning("duplicate k_employ column in k_indall.tab; using first occurrence")
col_a <- rep("NULL", length(header_all))
col_a[pidp_idx_a] <- "integer"
col_a[emp_idx] <- "integer"
df_all <- read.delim(fname_all,
    header = TRUE, sep = "\t",
    colClasses = col_a, stringsAsFactors = FALSE,
    quote = "", fill = TRUE, na.strings = c("", "-1", "-2", "-7", "-8", "-9")
)
cat("k_employ values:\n")
print(table(df_all$k_employ))

# Cross-tab jbstat (12+) with k_employ
fname_k <- file.path(DATA_ROOT, "ukhls", "k_indresp.tab")
header_k <- strsplit(readLines(fname_k, n = 1), "\t")[[1]]
header_k <- trimws(header_k)
pidp_idx_k <- match("pidp", header_k)
if (is.na(pidp_idx_k)) stop("missing column: pidp in k_indresp.tab")
if (sum(header_k == "pidp") > 1) warning("duplicate pidp column in k_indresp.tab; using first occurrence")
jb_idx_k <- match("k_jbstat", header_k)
if (is.na(jb_idx_k)) stop("missing column: k_jbstat in k_indresp.tab")
if (sum(header_k == "k_jbstat") > 1) warning("duplicate k_jbstat column in k_indresp.tab; using first occurrence")
col_k <- rep("NULL", length(header_k))
col_k[pidp_idx_k] <- "integer"
col_k[jb_idx_k] <- "integer"
df_k <- read.delim(fname_k,
    header = TRUE, sep = "\t",
    colClasses = col_k, stringsAsFactors = FALSE,
    quote = "", fill = TRUE, na.strings = c("", "-1", "-2", "-7", "-8", "-9")
)

merged <- merge(df_k, df_all, by = "pidp")
cat("\nCross-tab k_jbstat vs k_employ for codes 12-15:\n")
mask_new <- merged$k_jbstat %in% 12:15
cat("n with codes 12-15:", sum(mask_new, na.rm = TRUE), "\n")
print(table(merged$k_jbstat[mask_new], merged$k_employ[mask_new]))

cat("\nFor reference, codes 1-5 vs k_employ:\n")
mask_std <- merged$k_jbstat %in% 1:5
print(table(merged$k_jbstat[mask_std], merged$k_employ[mask_std]))
