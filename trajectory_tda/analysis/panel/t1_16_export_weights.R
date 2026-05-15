# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: T1.16 helper — export individual IPW weights from RDS to CSV for Python GMM script.
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/t1_16_export_weights.R

suppressPackageStartupMessages(library(data.table))

WORKTREE  <- normalizePath(getwd(), mustWork = FALSE)
TODAY     <- format(Sys.Date(), "%Y-%m-%d")

RDS_PATH  <- file.path(WORKTREE, "results/panel_methodology/weights",
                       paste0("ipw_individual_weights_", TODAY, ".rds"))
CSV_PATH  <- file.path(WORKTREE, "results/panel_methodology/weights",
                       paste0("ipw_individual_weights_", TODAY, ".csv"))

cat("=== T1.16 weight export ===\n")
cat("Reading RDS:", RDS_PATH, "\n")
if (!file.exists(RDS_PATH)) stop("RDS not found — run ipw_construction.R first.")

weights_df <- readRDS(RDS_PATH)
cat("Rows:", nrow(weights_df),
    "| Analytical:", sum(weights_df$in_analytical_sample), "\n")

fwrite(weights_df, CSV_PATH)
cat("Saved CSV:", CSV_PATH, "\n")
cat("=== export complete ===\n")
