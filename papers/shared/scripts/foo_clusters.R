# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: T0.11 — Build family-of-origin (FOO) clusters from xhhrel.tab
# using igraph::components(). Edges: biological parent-child (bpx/bcx) and
# biological siblings (bsbx). Connected components = FOO clusters.
# Reference: data/guides/6614/6614_main_survey_user_guide_family_matrix_xhhrel.pdf

library(igraph)
library(jsonlite)

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
  DATA_ROOT <- normalizePath(file.path(get_script_dir(), "..", "..", "..", "data", "UKDA-6614-tab", "tab"), mustWork = FALSE)
}

TODAY <- format(Sys.Date(), "%Y-%m-%d")
MISS <- -8 # USoc inapplicable / not in sample code

fpath_xhhrel <- file.path(DATA_ROOT, "ukhls", "xhhrel.tab")
fpath_xwave <- file.path(DATA_ROOT, "ukhls", "xwavedat.tab")
out_dir <- Sys.getenv("DERIVED_DIR", file.path(get_script_dir(), "..", "..", "..", "data", "derived"))
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# ---- 1. Identify columns to read ----
cat("Reading xhhrel header...\n")
header_all <- trimws(strsplit(readLines(fpath_xhhrel, n = 1), "\t")[[1]])
cat("  Total columns:", length(header_all), "\n")

# Columns needed: pidp, bcx_pidp_*, bpx_pidp_*, bsbx_pidp_*
need_cols <- c(
  "pidp",
  grep("^bcx_pidp_", header_all, value = TRUE), # biological children (up to 16)
  grep("^bpx_pidp_", header_all, value = TRUE), # biological parents (up to 4)
  grep("^bsbx_pidp_", header_all, value = TRUE) # biological siblings (up to 13)
)
cat("  Columns to load:", length(need_cols), "\n")

# ---- 2. Read relevant columns ----
cat("Reading xhhrel relevant columns...\n")
idx <- match(need_cols, header_all)
col_classes <- rep("NULL", length(header_all))
col_classes[idx] <- NA # default (read then coerce)
xhhrel <- read.delim(fpath_xhhrel,
  header = TRUE, sep = "\t",
  colClasses = col_classes, stringsAsFactors = FALSE,
  quote = "", fill = TRUE, na.strings = ""
)
for (col in names(xhhrel)) suppressWarnings(xhhrel[[col]] <- as.numeric(xhhrel[[col]]))
cat("  N rows:", nrow(xhhrel), "\n")

# ---- 3. Build edge list ----
cat("Building biological family edge list...\n")

make_edges <- function(df, from_col, to_cols) {
  # Returns data.frame(from, to) for all valid to-values
  rows <- list()
  for (tc in to_cols) {
    if (!tc %in% names(df)) next
    to_vals <- df[[tc]]
    valid <- !is.na(to_vals) & to_vals > 0 & to_vals != MISS
    from_vals <- df[[from_col]]
    if (any(valid)) {
      rows[[tc]] <- data.frame(
        from = from_vals[valid],
        to   = to_vals[valid]
      )
    }
  }
  do.call(rbind, rows)
}

bcx_cols <- grep("^bcx_pidp_", names(xhhrel), value = TRUE)
bpx_cols <- grep("^bpx_pidp_", names(xhhrel), value = TRUE)
bsbx_cols <- grep("^bsbx_pidp_", names(xhhrel), value = TRUE)

edges_bc <- make_edges(xhhrel, "pidp", bcx_cols)
edges_bp <- make_edges(xhhrel, "pidp", bpx_cols)
edges_sb <- make_edges(xhhrel, "pidp", bsbx_cols)

cat("  Parent→child edges:", nrow(edges_bc), "\n")
cat("  Child→parent edges:", nrow(edges_bp), "\n")
cat("  Sibling edges:", nrow(edges_sb), "\n")

# Combine and deduplicate (treat as undirected: sort each pair)
all_edges <- rbind(edges_bc, edges_bp, edges_sb)
all_edges <- all_edges[!is.na(all_edges$from) & !is.na(all_edges$to), ]
all_edges <- all_edges[all_edges$from > 0 & all_edges$to > 0, ]

# Canonical form: smaller pidp first
if (nrow(all_edges) > 0) {
  all_edges$from_c <- pmin(all_edges$from, all_edges$to)
  all_edges$to_c <- pmax(all_edges$from, all_edges$to)
  all_edges_dedup <- unique(data.frame(
    from = all_edges$from_c,
    to = all_edges$to_c
  ))
} else {
  all_edges_dedup <- data.frame(from = integer(0), to = integer(0))
}
cat("  Deduplicated undirected edges:", nrow(all_edges_dedup), "\n")

# ---- 4. Build igraph and find components ----
# Note: some relatives listed in edge columns may not appear in xhhrel rows
# (they may be non-sample members). Build graph from edge list only; singletons
# (those with no recorded biological relative in the data) are handled separately.
cat("Building igraph and finding connected components...\n")

g <- graph_from_data_frame(all_edges_dedup, directed = FALSE)
comps <- components(g)
cat("  N vertices in graph:", vcount(g), "\n")
cat("  N edges:", ecount(g), "\n")
cat("  N connected components:", comps$no, "\n")

# ---- 5. Build cluster assignment data frame ----
# Linked individuals: those in the graph (have at least one biological relative)
foo_linked <- data.frame(
  pidp = as.numeric(names(comps$membership)),
  foo_cluster = comps$membership,
  stringsAsFactors = FALSE
)
cluster_sizes_linked <- as.integer(table(comps$membership))
foo_linked$foo_size <- cluster_sizes_linked[foo_linked$foo_cluster]

# Singleton individuals: those in xhhrel but not in any edge
all_xhhrel_pidp <- unique(xhhrel$pidp[!is.na(xhhrel$pidp) & xhhrel$pidp > 0])
linked_pidp <- foo_linked$pidp
singleton_pidp <- setdiff(all_xhhrel_pidp, linked_pidp)

if (nrow(foo_linked) == 0 || all(is.na(foo_linked$foo_cluster))) {
  next_cluster_id <- 1L
} else {
  next_cluster_id <- max(foo_linked$foo_cluster, na.rm = TRUE) + 1L
}

if (length(singleton_pidp) > 0) {
  foo_singletons <- data.frame(
    pidp = singleton_pidp,
    foo_cluster = seq(next_cluster_id, next_cluster_id + length(singleton_pidp) - 1L),
    foo_size = 1L,
    stringsAsFactors = FALSE
  )
} else {
  foo_singletons <- data.frame(pidp = integer(0), foo_cluster = integer(0), foo_size = integer(0), stringsAsFactors = FALSE)
}

foo_df <- if (nrow(foo_linked) > 0) rbind(foo_linked, foo_singletons) else foo_singletons

n_linked <- sum(foo_df$foo_size > 1)
n_singletons <- sum(foo_df$foo_size == 1)
cat("  Individuals in clusters of size > 1:", n_linked, "\n")
cat("  Singletons (xhhrel, no recorded biological link):", n_singletons, "\n")
cat("  Total in foo_df:", nrow(foo_df), "\n")

# ---- 6. Coverage: proportion of full xwavedat sample with a FOO link ----
cat("\nReading xwavedat pidp for coverage denominator...\n")
xwave_header <- trimws(strsplit(readLines(fpath_xwave, n = 1), "\t")[[1]])
idx_xw <- which(xwave_header == "pidp")
cc_xw <- rep("NULL", length(xwave_header))
cc_xw[idx_xw] <- NA
xwave_pidp_df <- read.delim(fpath_xwave,
  header = TRUE, sep = "\t",
  colClasses = cc_xw, stringsAsFactors = FALSE,
  quote = "", fill = TRUE, na.strings = ""
)
xwave_pidp_all <- suppressWarnings(as.numeric(xwave_pidp_df[[1]]))
xwave_pidp_all <- unique(xwave_pidp_all[!is.na(xwave_pidp_all) & xwave_pidp_all > 0])
cat("  xwavedat unique pidp:", length(xwave_pidp_all), "\n")

# Merge foo_df with xwave population
in_both <- intersect(foo_df$pidp, xwave_pidp_all)
denom <- length(xwave_pidp_all)
if (denom == 0) {
  pct_cov <- NA_real_
  pct_linked <- NA_real_
} else {
  pct_cov <- round(length(in_both) / denom * 100, 2)
}
cat("  xwavedat members with FOO cluster:", length(in_both), "(", pct_cov, "%)\n")

linked_in_both <- sum(foo_df$foo_size[foo_df$pidp %in% in_both] > 1, na.rm = TRUE)
if (denom == 0) {
  pct_linked <- NA_real_
} else {
  pct_linked <- round(linked_in_both / denom * 100, 2)
}
cat("  xwavedat members in FOO cluster size > 1:", linked_in_both, "(", pct_linked, "%)\n")

# ---- 7. Cluster size distribution ----
cluster_sizes <- foo_df$foo_size
size_dist <- table(cluster_sizes)
cat("\nCluster size distribution (size : count):\n")
for (nm in names(size_dist)) cat("  ", nm, ":", size_dist[nm], "\n")
cat("  Max cluster size:", max(cluster_sizes), "\n")
cat("  Median cluster size:", median(cluster_sizes), "\n")

# ---- 8. ICC pre-check ----
# Use gross income from UKHLS wave b hhresp as the outcome variable.
# ICC within FOO clusters via one-way ANOVA decomposition.
cat("\nICC pre-check using b_fihhmngrs_dv (gross HH income, wave b)...\n")

read_cols_num <- function(fpath, cols) {
  header <- trimws(strsplit(readLines(fpath, n = 1), "\t")[[1]])
  idx <- match(cols, header)
  ok <- !is.na(idx)
  col_classes <- rep("NULL", length(header))
  col_classes[idx[ok]] <- NA
  df <- read.delim(fpath,
    header = TRUE, sep = "\t",
    colClasses = col_classes, stringsAsFactors = FALSE,
    quote = "", fill = TRUE, na.strings = ""
  )
  for (col in names(df)) suppressWarnings(df[[col]] <- as.numeric(df[[col]]))
  df
}

b_ind <- read_cols_num(file.path(DATA_ROOT, "ukhls", "b_indresp.tab"), c("pidp", "b_hidp"))
b_hh <- read_cols_num(file.path(DATA_ROOT, "ukhls", "b_hhresp.tab"), c("b_hidp", "b_fihhmngrs_dv"))
b_merged <- merge(b_ind, b_hh, by = "b_hidp")
b_merged$income <- b_merged$b_fihhmngrs_dv
b_merged$income[!is.na(b_merged$income) & b_merged$income < 0] <- NA

# Merge with FOO clusters
icc_df <- merge(b_merged[, c("pidp", "income")], foo_df[, c("pidp", "foo_cluster", "foo_size")], by = "pidp")
icc_df <- icc_df[!is.na(icc_df$income) & icc_df$foo_size > 1, ]
cat("  N obs for ICC (valid income + FOO cluster size > 1):", nrow(icc_df), "\n")

icc_val <- NA_real_
if (nrow(icc_df) > 100) {
  # One-way ANOVA ICC: (MSB - MSW) / (MSB + (k-1)*MSW)
  # Using lm approach
  n_total <- nrow(icc_df)
  grand_mean <- mean(icc_df$income, na.rm = TRUE)

  # Between-cluster SS
  clust_means <- tapply(icc_df$income, icc_df$foo_cluster, mean, na.rm = TRUE)
  clust_n <- tapply(icc_df$income, icc_df$foo_cluster, length)
  SSB <- sum(clust_n * (clust_means - grand_mean)^2, na.rm = TRUE)

  # Within-cluster SS
  icc_df$clust_mean <- clust_means[as.character(icc_df$foo_cluster)]
  SSW <- sum((icc_df$income - icc_df$clust_mean)^2, na.rm = TRUE)

  n_clusters <- length(unique(icc_df$foo_cluster))
  dfB <- n_clusters - 1
  dfW <- n_total - n_clusters
  if (dfB <= 0 || dfW <= 0) {
    warning("Insufficient degrees of freedom for ICC calculation")
    icc_val <- NA_real_
  } else {
    MSB <- SSB / dfB
    MSW <- SSW / dfW

    # Average cluster size for ICC formula
    k_avg <- mean(clust_n)
    denom_icc <- MSB + (k_avg - 1) * MSW
    if (abs(denom_icc) < .Machine$double.eps) {
      warning("ICC denominator is numerically zero; setting ICC to NA")
      icc_val <- NA_real_
    } else {
      icc_val <- (MSB - MSW) / denom_icc
    }
  }
  if (!is.na(icc_val)) {
    cat("  ICC (within FOO clusters, gross income):", round(icc_val, 4), "\n")
    cat(
      "  Interpretation: ICC", round(icc_val, 4), "—",
      ifelse(icc_val > 0.05, "substantial clustering (>0.05), account for FOO in model",
        "weak clustering, FOO effect marginal"
      ), "\n"
    )
  } else {
    cat("  ICC could not be computed due to degenerate cluster sizes or denominator issues.\n")
  }
}

# ---- 9. Save cluster CSV ----
out_csv <- file.path(out_dir, paste0("foo_clusters_", TODAY, ".csv"))
write.csv(foo_df[, c("pidp", "foo_cluster", "foo_size")], out_csv, row.names = FALSE)
cat("\nFOO cluster CSV written to:", out_csv, "\n")

# ---- 10. Save JSON results ----
out_json_dir <- Sys.getenv("OUT_JSON_DIR", file.path(get_script_dir(), "..", "..", "..", "results", "panel_methodology", "harmonisation"))
dir.create(out_json_dir, recursive = TRUE, showWarnings = FALSE)
out_json <- file.path(out_json_dir, paste0("foo_clusters_", TODAY, ".json"))

result <- list(
  audit_date = TODAY,
  data_source = "ukhls/xhhrel.tab",
  edge_types = c("bcx (biological children)", "bpx (biological parents)", "bsbx (biological siblings)"),
  n_vertices = vcount(g),
  n_edges = ecount(g),
  n_components = comps$no,
  n_singletons = n_singletons,
  n_linked = n_linked,
  max_cluster_size = max(cluster_sizes),
  median_cluster_size = median(cluster_sizes),
  xwavedat_n_total = length(xwave_pidp_all),
  xwavedat_n_covered = length(in_both),
  coverage_pct = pct_cov,
  linked_pct = pct_linked,
  icc_gross_income = if (!is.na(icc_val)) round(icc_val, 4) else NULL,
  icc_verdict = if (!is.na(icc_val)) {
    ifelse(icc_val > 0.05, "ACCOUNT: ICC > 0.05, FOO clustering material",
      "MARGINAL: ICC <= 0.05, FOO effect weak"
    )
  } else {
    "insufficient data"
  }
)

write(toJSON(result, pretty = TRUE, auto_unbox = TRUE), out_json)
cat("JSON written to:", out_json, "\n")
cat("Done.\n")
