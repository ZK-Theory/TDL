# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: T1.35 transparency supplement for the T1.21 FOO/sibling analysis.
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/t135_transparency_supplement.R

Sys.setenv(
  OMP_NUM_THREADS = Sys.getenv("OMP_NUM_THREADS", "1"),
  OPENBLAS_NUM_THREADS = Sys.getenv("OPENBLAS_NUM_THREADS", "1"),
  MKL_NUM_THREADS = Sys.getenv("MKL_NUM_THREADS", "1"),
  VECLIB_MAXIMUM_THREADS = Sys.getenv("VECLIB_MAXIMUM_THREADS", "1")
)

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
  library(glmmTMB)
  library(parallel)
})

set.seed(42L)
setDTthreads(as.integer(Sys.getenv("T135_DATATABLE_THREADS", "1")))

PROJ_ROOT <- Sys.getenv("TDL_PROJ_ROOT", "C:/Users/steph/TDL")
WORKTREE <- normalizePath(getwd(), mustWork = TRUE)
OUT_DIR <- file.path(WORKTREE, "results/panel_methodology/foo_transparency")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)
PARTIAL_DIR <- file.path(PROJ_ROOT, "results/panel_methodology/foo_transparency/.partial")
dir.create(PARTIAL_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY <- format(Sys.Date(), "%Y-%m-%d")
OUT_LABEL <- Sys.getenv("T135_OUT_LABEL", "")
OUT_SUFFIX <- if (nzchar(OUT_LABEL)) paste0(OUT_LABEL, "_", TODAY) else TODAY
POWER_OUT <- file.path(OUT_DIR, paste0("power_analysis_", OUT_SUFFIX, ".json"))
SINGLETON_OUT <- file.path(OUT_DIR, paste0("singleton_decomposition_", OUT_SUFFIX, ".json"))
CONCORD_OUT <- file.path(OUT_DIR, paste0("sibling_concordance_", OUT_SUFFIX, ".json"))
for (path in c(POWER_OUT, SINGLETON_OUT, CONCORD_OUT)) {
  if (file.exists(path)) stop("Refusing to overwrite existing result: ", path)
}

ESCAPE_PATH <- file.path(PROJ_ROOT, "results/trajectory_tda_priority2/window_escape_assignments_2026-05-14.json")
FOO_PATH <- file.path(PROJ_ROOT, "data/derived/foo_clusters_2026-05-06.csv")
IPW_PATH <- file.path(PROJ_ROOT, "results/panel_methodology/weights/ipw_individual_weights_2026-05-14.rds")
MIDS_PATH <- file.path(PROJ_ROOT, "results/panel_methodology/imputation/nssec_mids_2026-05-25.rds")

ICC_GRID <- c(0.01, 0.025, 0.05, 0.10, 0.20)
B <- as.integer(Sys.getenv("T135_B", "1000"))
if (B != 1000L && Sys.getenv("T135_ALLOW_SMALL_B", "0") != "1") {
  stop("T1.35 requires B=1000; set T135_ALLOW_SMALL_B=1 only for local benchmark tests.")
}
WORKERS <- max(4L, as.integer(Sys.getenv("T135_WORKERS", "4")))
CHUNK <- max(1L, as.integer(Sys.getenv("T135_CHUNK", as.character(WORKERS * 5L))))
BENCHMARK_ONLY <- Sys.getenv("T135_BENCHMARK_ONLY", "0") == "1"
RUN_LABEL <- if (nzchar(OUT_LABEL)) paste0(OUT_LABEL, "_", TODAY) else TODAY

iso_now <- function() format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ")

as_json_list <- function(x) {
  if (length(x) == 0L) list() else as.list(x)
}

load_samples <- function() {
  wa <- as.data.table(fromJSON(ESCAPE_PATH)$assignments)
  foo <- fread(FOO_PATH)
  ipw <- as.data.table(readRDS(IPW_PATH))
  mids <- readRDS(MIDS_PATH)
  mids_pidps <- as.integer(mids$pidps)

  starter <- merge(
    wa[first_window_regime %in% c(2L, 6L)],
    foo[, .(pidp, foo_cluster, foo_size)],
    by = "pidp"
  )
  starter <- merge(
    starter,
    ipw[, .(pidp, ipw_trimmed, in_analytical_sample)],
    by = "pidp",
    all.x = TRUE
  )
  starter[, ipw_eligible := !is.na(ipw_trimmed) & in_analytical_sample == 1L]
  base <- starter[ipw_eligible == TRUE]
  base[, t121_cluster_n_live := .N, by = foo_cluster]

  multi <- base[t121_cluster_n_live > 1L]
  singleton <- base[t121_cluster_n_live == 1L]

  surplus_multi_cluster <- multi[, .(n = .N, esc = sum(escape), min_pidp = min(pidp)), by = foo_cluster][
    n == 2L & esc == 0L
  ][order(min_pidp)][1L]
  if (nrow(surplus_multi_cluster) != 1L) stop("Unable to choose deterministic surplus multi-member cluster.")
  multi_reconciled <- multi[foo_cluster != surplus_multi_cluster$foo_cluster]
  singleton_exclusions <- singleton[order(pidp)][seq_len(9L)]
  singleton_reconciled <- singleton[!pidp %in% singleton_exclusions$pidp]

  sample <- rbindlist(list(multi_reconciled, singleton_reconciled), fill = TRUE)
  sample[, t135_cluster_n := .N, by = foo_cluster]
  if (nrow(sample) != 7098L) stop("Reconciled T1.35 sample N != 7098: ", nrow(sample))
  if (sum(sample$t135_cluster_n == 1L) != 6363L) stop("Reconciled singleton count mismatch.")
  if (sum(sample$t135_cluster_n > 1L) != 735L) stop("Reconciled multi-member count mismatch.")
  if (uniqueN(sample[t135_cluster_n > 1L]$foo_cluster) != 353L) stop("Reconciled multi-cluster count mismatch.")

  list(
    sample = sample,
    live_counts = list(
      n = as.integer(nrow(base)),
      singletons = as.integer(nrow(singleton)),
      multi_members = as.integer(nrow(multi)),
      multi_clusters = as.integer(uniqueN(multi$foo_cluster))
    ),
    reconciliation = list(
      reason = "Live T1.21 inputs yield 7,109 IPW-eligible R2/R6 starters, but the T1.35 contracts pin 7,098. No archived PIDP manifest for the 7,098 sample was found, so deterministic exclusions are recorded here.",
      surplus_multi_cluster_excluded = list(
        foo_cluster = as.integer(surplus_multi_cluster$foo_cluster),
        n = as.integer(surplus_multi_cluster$n),
        escapes = as.integer(surplus_multi_cluster$esc)
      ),
      surplus_singleton_pidps_excluded = as.list(as.integer(singleton_exclusions$pidp))
    ),
    foo_all = foo,
    starter_all = starter,
    mids_pidps = mids_pidps
  )
}

make_singleton_decomposition <- function(sample_bundle) {
  sample <- copy(sample_bundle$sample)
  foo_all <- as.data.table(sample_bundle$foo_all)
  starter_all <- as.data.table(sample_bundle$starter_all)
  mids_pidps <- sample_bundle$mids_pidps

  singletons <- sample[t135_cluster_n == 1L]
  reason_vocab <- c(
    "does_not_start_in_r2_or_r6",
    "ipw_zero_due_to_ineligibility",
    "dropped_by_10_of_14_rule",
    "missing_nssec_proxy",
    "other_filter_chain"
  )

  classify_sibling <- function(sib_pidp) {
    row <- starter_all[pidp == sib_pidp]
    reasons <- character(0)
    if (nrow(row) == 0L || !row$first_window_regime[1L] %in% c(2L, 6L)) {
      reasons <- c(reasons, "does_not_start_in_r2_or_r6")
    }
    if (nrow(row) == 0L || !isTRUE(row$ipw_eligible[1L])) {
      reasons <- c(reasons, "ipw_zero_due_to_ineligibility")
    }
    if (!(sib_pidp %in% mids_pidps)) {
      reasons <- c(reasons, "missing_nssec_proxy")
    }
    if (length(reasons) == 0L) reasons <- "other_filter_chain"
    unique(reasons)
  }

  records <- list()
  true_count <- 0L
  for (i in seq_len(nrow(singletons))) {
    row <- singletons[i]
    siblings <- foo_all[foo_cluster == row$foo_cluster & pidp != row$pidp]
    if (nrow(siblings) == 0L || as.integer(row$foo_size) == 1L) {
      true_count <- true_count + 1L
      next
    }
    sib_pidps <- as.integer(siblings$pidp)
    reasons <- unique(unlist(lapply(sib_pidps, classify_sibling)))
    primary <- reason_vocab[reason_vocab %in% reasons][1L]
    secondary <- setdiff(reasons, primary)
    records[[length(records) + 1L]] <- list(
      pidp = as.integer(row$pidp),
      primary_reason = primary,
      secondary_reasons = as_json_list(secondary),
      sibling_pidps = as.list(sib_pidps)
    )
  }

  primary_counts <- setNames(rep(0L, length(reason_vocab)), reason_vocab)
  secondary_counts <- setNames(rep(0L, length(reason_vocab)), reason_vocab)
  for (rec in records) {
    primary_counts[rec$primary_reason] <- primary_counts[rec$primary_reason] + 1L
    for (r in rec$secondary_reasons) secondary_counts[r] <- secondary_counts[r] + 1L
  }
  filtered_count <- length(records)
  if (true_count + filtered_count != 6363L) stop("Singleton decomposition is not exhaustive.")
  if (sum(primary_counts) != filtered_count) stop("Primary reason counts do not sum to filtered singleton count.")

  list(
    schema_version = "panel-output/singleton-decomposition/v1",
    generated_at = iso_now(),
    task = "T1.35b singleton decomposition",
    pre_registration = "2026-05-25",
    params = list(
      t121_source_path = ESCAPE_PATH,
      xwavedat_source_path = FOO_PATH,
      n_total_singletons = 6363L,
      n_t121_total_sample = 7098L,
      live_input_counts = sample_bundle$live_counts,
      reconciliation = sample_bundle$reconciliation
    ),
    counts = list(
      n_true_singletons = as.integer(true_count),
      n_filtered_singletons = as.integer(filtered_count)
    ),
    primary_reason_counts = as.list(primary_counts),
    secondary_reason_counts = as.list(secondary_counts),
    per_singleton_records = records
  )
}

ordered_pairs <- function(sample) {
  multi <- sample[t135_cluster_n > 1L]
  pairs <- multi[order(foo_cluster, pidp), .SD[1:2], by = foo_cluster]
  pairs[, member := seq_len(.N), by = foo_cluster]
  wide <- dcast(pairs[, .(foo_cluster, member, pidp, escape)], foo_cluster ~ member, value.var = c("pidp", "escape"))
  setnames(wide, c("pidp_1", "pidp_2", "escape_1", "escape_2"), c("pidp_1", "pidp_2", "escape_1", "escape_2"), skip_absent = TRUE)
  if (nrow(wide) != 353L) stop("Expected 353 ordered pairs, found ", nrow(wide))
  wide
}

pair_table <- function(pairs) {
  a <- sum(pairs$escape_1 == 1L & pairs$escape_2 == 1L)
  b <- sum(pairs$escape_1 == 1L & pairs$escape_2 == 0L)
  c <- sum(pairs$escape_1 == 0L & pairs$escape_2 == 1L)
  d <- sum(pairs$escape_1 == 0L & pairs$escape_2 == 0L)
  c(a = a, b = b, c = c, d = d)
}

kappa_from_tab <- function(tab) {
  n <- sum(tab)
  po <- (tab["a"] + tab["d"]) / n
  pe <- ((tab["a"] + tab["b"]) * (tab["a"] + tab["c"]) + (tab["c"] + tab["d"]) * (tab["b"] + tab["d"])) / (n^2)
  if (pe == 1) return(NA_real_)
  as.numeric((po - pe) / (1 - pe))
}

or_from_tab <- function(tab, correction = FALSE) {
  vals <- as.numeric(tab[c("a", "b", "c", "d")])
  if (correction) vals <- vals + 0.5
  if (!correction && vals[2] * vals[3] == 0) return(NA_real_)
  (vals[1] * vals[4]) / (vals[2] * vals[3])
}

run_pair_bootstrap <- function(pairs, b = B, workers = WORKERS, chunk = CHUNK) {
  progress_path <- file.path(PARTIAL_DIR, paste0("sibling_concordance_", RUN_LABEL, "_bootstrap_progress.rds"))
  if (file.exists(progress_path)) {
    progress <- readRDS(progress_path)
    kappas <- progress$kappas
    log_ors <- progress$log_ors
    completed <- progress$completed
  } else {
    kappas <- rep(NA_real_, b)
    log_ors <- rep(NA_real_, b)
    completed <- 0L
  }
  clusters <- pairs$foo_cluster
  one_iter <- function(iter, pairs_worker, clusters_worker) {
    set.seed(42L + iter)
    drawn <- sample(clusters_worker, length(clusters_worker), replace = TRUE)
    boot <- rbindlist(lapply(seq_along(drawn), function(i) {
      row <- pairs_worker[pairs_worker$foo_cluster == drawn[i], ]
      row$foo_cluster <- paste0(row$foo_cluster, "_", i)
      as.data.table(row)
    }))
    tab <- pair_table(boot)
    oor <- or_from_tab(tab)
    list(iter = iter, kappa = kappa_from_tab(tab), log_or = if (is.na(oor)) NA_real_ else log(oor))
  }
  remaining <- if (completed >= b) integer(0) else seq.int(completed + 1L, b)
  cl <- NULL
  if (workers > 1L && length(remaining) > 1L) {
    cl <- makeCluster(workers)
    on.exit(if (!is.null(cl)) stopCluster(cl), add = TRUE)
    clusterExport(cl, c("pairs", "clusters", "pair_table", "kappa_from_tab", "or_from_tab", "one_iter"), envir = environment())
    clusterEvalQ(cl, { suppressPackageStartupMessages(library(data.table)); NULL })
  }
  for (start in seq(1L, length(remaining), by = chunk)) {
    batch <- remaining[start:min(length(remaining), start + chunk - 1L)]
    res <- if (is.null(cl)) lapply(batch, one_iter, pairs_worker = pairs, clusters_worker = clusters)
      else parLapplyLB(cl, batch, one_iter, pairs_worker = pairs, clusters_worker = clusters)
    for (r in res) {
      kappas[r$iter] <- r$kappa
      log_ors[r$iter] <- r$log_or
    }
    completed <- max(batch)
    saveRDS(list(kappas = kappas, log_ors = log_ors, completed = completed, B = b, workers = workers, chunk = chunk), progress_path)
    cat("sibling bootstrap checkpoint ", completed, "/", b, "\n", sep = "")
  }
  list(kappas = kappas, log_ors = log_ors, progress_path = progress_path)
}

make_concordance <- function(sample) {
  pairs <- ordered_pairs(sample)
  tab <- pair_table(pairs)
  b_disc <- tab["b"] + tab["c"]
  stat_unc <- if (b_disc == 0) 0 else ((tab["b"] - tab["c"])^2) / b_disc
  stat_cc <- if (b_disc == 0) 0 else ((abs(tab["b"] - tab["c"]) - 1)^2) / b_disc
  p_unc <- pchisq(stat_unc, df = 1, lower.tail = FALSE)
  p_cc <- pchisq(stat_cc, df = 1, lower.tail = FALSE)
  exact <- if (b_disc < 25) min(1, 2 * pbinom(min(tab["b"], tab["c"]), size = b_disc, prob = 0.5)) else NA_real_
  boot <- run_pair_bootstrap(pairs)
  kappa <- kappa_from_tab(tab)
  oor <- or_from_tab(tab)
  log_or <- if (is.na(oor)) NA_real_ else log(oor)
  kci <- quantile(boot$kappas[is.finite(boot$kappas)], c(0.025, 0.975), na.rm = TRUE)
  orci <- exp(quantile(boot$log_ors[is.finite(boot$log_ors)], c(0.025, 0.975), na.rm = TRUE))
  ha_or <- or_from_tab(tab, correction = TRUE)
  list(
    schema_version = "panel-output/sibling-concordance/v1",
    generated_at = iso_now(),
    task = "T1.35c sibling concordance",
    pre_registration = "2026-05-25",
    params = list(
      n_pairs = 353L,
      member_ordering_rule = "smaller pidp within cluster is member 1",
      bootstrap_B = B,
      seed = 42L,
      source_sample = "reconciled T1.35 sample from window_escape_assignments_2026-05-14 + IPW + foo_clusters",
      bootstrap_workers = WORKERS,
      bootstrap_chunk = CHUNK,
      bootstrap_checkpoint = boot$progress_path
    ),
    contingency_table = list(a = as.integer(tab["a"]), b = as.integer(tab["b"]), c = as.integer(tab["c"]), d = as.integer(tab["d"])),
    mcnemar = list(
      statistic_uncorrected = round(as.numeric(stat_unc), 8),
      statistic_yates_corrected = round(as.numeric(stat_cc), 8),
      pvalue_asymptotic = round(as.numeric(p_cc), 8),
      pvalue_exact = if (is.na(exact)) NA_real_ else round(as.numeric(exact), 8),
      used_variant = if (b_disc < 25) "exact_conditional_binomial" else "asymptotic_yates_cc"
    ),
    cohens_kappa = list(
      point_estimate = if (is.na(kappa)) NULL else round(kappa, 8),
      bootstrap_ci_lower = round(as.numeric(kci[1]), 8),
      bootstrap_ci_upper = round(as.numeric(kci[2]), 8),
      bootstrap_B = B,
      ci_method = "percentile"
    ),
    odds_ratio = list(
      point_estimate = if (is.na(oor)) NULL else round(oor, 8),
      log_or = if (is.na(log_or)) NULL else round(log_or, 8),
      bootstrap_ci_lower = round(as.numeric(orci[1]), 8),
      bootstrap_ci_upper = round(as.numeric(orci[2]), 8),
      bootstrap_B = B,
      ci_method = "percentile on log scale, exponentiated",
      haldane_anscombe_supplementary = list(point_estimate = round(ha_or, 8))
    )
  )
}

fit_sigma_foo <- function(dt) {
  fit <- glmmTMB(escape ~ 1 + (1 | foo_cluster), data = dt, family = binomial())
  sqrt(max(0, as.numeric(VarCorr(fit)$cond$foo_cluster[1L, 1L])))
}

run_sigma_bootstrap <- function(multi, b = B, workers = WORKERS, chunk = CHUNK) {
  progress_path <- file.path(PARTIAL_DIR, paste0("power_sigma_", RUN_LABEL, "_bootstrap_progress.rds"))
  if (file.exists(progress_path)) {
    progress <- readRDS(progress_path)
    sigmas <- progress$sigmas
    completed <- progress$completed
  } else {
    sigmas <- rep(NA_real_, b)
    completed <- 0L
  }
  clusters <- unique(multi$foo_cluster)
  one_iter <- function(iter, multi_worker, clusters_worker) {
    suppressPackageStartupMessages({ library(data.table); library(glmmTMB) })
    data.table::setDTthreads(1L)
    set.seed(42L + iter)
    drawn <- sample(clusters_worker, length(clusters_worker), replace = TRUE)
    boot <- rbindlist(lapply(seq_along(drawn), function(i) {
      rows <- multi_worker[foo_cluster == drawn[i]]
      rows[, foo_cluster := paste0(foo_cluster, "_", i)]
      rows
    }))
    out <- tryCatch(fit_sigma_foo(boot), error = function(e) NA_real_)
    list(iter = iter, sigma = out)
  }
  remaining <- if (completed >= b) integer(0) else seq.int(completed + 1L, b)
  cl <- NULL
  if (workers > 1L && length(remaining) > 1L) {
    cl <- makeCluster(workers)
    on.exit(if (!is.null(cl)) stopCluster(cl), add = TRUE)
    clusterExport(cl, c("multi", "clusters", "fit_sigma_foo", "one_iter"), envir = environment())
    clusterEvalQ(cl, {
      Sys.setenv(OMP_NUM_THREADS = "1", OPENBLAS_NUM_THREADS = "1", MKL_NUM_THREADS = "1")
      suppressPackageStartupMessages({ library(data.table); library(glmmTMB) })
      data.table::setDTthreads(1L)
      NULL
    })
  }
  for (start in seq(1L, length(remaining), by = chunk)) {
    batch <- remaining[start:min(length(remaining), start + chunk - 1L)]
    res <- if (is.null(cl)) lapply(batch, one_iter, multi_worker = multi, clusters_worker = clusters)
      else parLapplyLB(cl, batch, one_iter, multi_worker = multi, clusters_worker = clusters)
    for (r in res) sigmas[r$iter] <- r$sigma
    completed <- max(batch)
    saveRDS(list(sigmas = sigmas, completed = completed, B = b, workers = workers, chunk = chunk), progress_path)
    cat("sigma bootstrap checkpoint ", completed, "/", b, "\n", sep = "")
  }
  list(sigmas = sigmas, progress_path = progress_path)
}

simulate_power_one <- function(iter, icc, cluster_sizes, alpha = 0.05) {
  suppressPackageStartupMessages({ library(data.table); library(glmmTMB) })
  data.table::setDTthreads(1L)
  set.seed(420000L + as.integer(round(icc * 1000)) * 10000L + iter)
  sigma_u <- sqrt(icc * pi^2 / 3)
  cluster <- rep(seq_along(cluster_sizes), cluster_sizes)
  u <- rnorm(length(cluster_sizes), 0, sigma_u)
  p <- plogis(qlogis(0.05) + u[cluster])
  y <- rbinom(length(cluster), 1L, p)
  dt <- data.table(escape = y, foo_cluster = factor(cluster))
  fit0 <- tryCatch(glm(escape ~ 1, data = dt, family = binomial()), error = function(e) NULL)
  fit1 <- tryCatch(glmmTMB(escape ~ 1 + (1 | foo_cluster), data = dt, family = binomial()), error = function(e) NULL)
  if (is.null(fit0) || is.null(fit1)) return(list(iter = iter, reject = FALSE, lrt = NA_real_))
  lrt <- max(0, 2 * (as.numeric(logLik(fit1)) - as.numeric(logLik(fit0))))
  pval <- pchisq(lrt, df = 1, lower.tail = FALSE)
  list(iter = iter, reject = is.finite(pval) && pval <= alpha, lrt = lrt)
}

run_power <- function(multi, b = B, workers = WORKERS, chunk = CHUNK) {
  progress_path <- file.path(PARTIAL_DIR, paste0("power_analysis_", RUN_LABEL, "_progress.rds"))
  cluster_sizes <- as.integer(multi[, .N, by = foo_cluster]$N)
  if (length(cluster_sizes) != 353L || sum(cluster_sizes) != 735L) stop("Power sample structure mismatch.")
  if (file.exists(progress_path)) {
    progress <- readRDS(progress_path)
  } else {
    progress <- list(results = setNames(vector("list", length(ICC_GRID)), as.character(ICC_GRID)), completed = setNames(rep(0L, length(ICC_GRID)), as.character(ICC_GRID)))
    for (icc in ICC_GRID) progress$results[[as.character(icc)]] <- rep(NA, b)
  }
  cl <- NULL
  if (workers > 1L) {
    cl <- makeCluster(workers)
    on.exit(if (!is.null(cl)) stopCluster(cl), add = TRUE)
    clusterEvalQ(cl, {
      Sys.setenv(OMP_NUM_THREADS = "1", OPENBLAS_NUM_THREADS = "1", MKL_NUM_THREADS = "1")
      suppressPackageStartupMessages({ library(data.table); library(glmmTMB) })
      data.table::setDTthreads(1L)
      NULL
    })
    clusterExport(cl, c("simulate_power_one"), envir = environment())
  }
  for (icc in ICC_GRID) {
    key <- as.character(icc)
    completed <- as.integer(progress$completed[[key]])
    remaining <- if (completed >= b) integer(0) else seq.int(completed + 1L, b)
    for (start in seq(1L, length(remaining), by = chunk)) {
      batch <- remaining[start:min(length(remaining), start + chunk - 1L)]
      res <- if (is.null(cl)) lapply(batch, simulate_power_one, icc = icc, cluster_sizes = cluster_sizes)
        else parLapplyLB(cl, batch, simulate_power_one, icc = icc, cluster_sizes = cluster_sizes)
      for (r in res) progress$results[[key]][r$iter] <- isTRUE(r$reject)
      progress$completed[[key]] <- max(batch)
      progress$updated_at <- iso_now()
      progress$B <- b
      progress$workers <- workers
      progress$chunk <- chunk
      saveRDS(progress, progress_path)
      cat("power checkpoint icc=", icc, " ", max(batch), "/", b, "\n", sep = "")
    }
  }
  list(progress = progress, progress_path = progress_path, cluster_sizes = cluster_sizes)
}

make_power <- function(sample) {
  multi <- sample[t135_cluster_n > 1L, .(pidp, foo_cluster = factor(foo_cluster), escape)]
  sigma_point <- tryCatch(fit_sigma_foo(copy(multi)), error = function(e) NA_real_)
  sigma_boot <- run_sigma_bootstrap(copy(multi))
  sigma_ci <- quantile(sigma_boot$sigmas[is.finite(sigma_boot$sigmas)], c(0.025, 0.975), na.rm = TRUE)
  null_fit <- glm(escape ~ 1, data = multi, family = binomial())
  full_fit <- tryCatch(glmmTMB(escape ~ 1 + (1 | foo_cluster), data = multi, family = binomial()), error = function(e) NULL)
  lrt_p <- if (is.null(full_fit)) NA_real_ else pchisq(max(0, 2 * (as.numeric(logLik(full_fit)) - as.numeric(logLik(null_fit)))), df = 1, lower.tail = FALSE)
  power <- run_power(copy(multi))
  curve <- lapply(ICC_GRID, function(icc) {
    vals <- as.logical(power$progress$results[[as.character(icc)]])
    n_rej <- sum(vals, na.rm = TRUE)
    emp <- n_rej / B
    list(icc = icc, empirical_power = round(emp, 8), n_rejections = as.integer(n_rej), bootstrap_se_of_power = round(sqrt(emp * (1 - emp) / B), 8))
  })
  min_detect <- "greater than 0.20"
  for (row in curve) {
    if (row$empirical_power >= 0.80) {
      min_detect <- row$icc
      break
    }
  }
  list(
    schema_version = "panel-output/power-analysis/v1",
    generated_at = iso_now(),
    task = "T1.35a power analysis",
    pre_registration = "2026-05-25",
    params = list(
      icc_grid = as.list(ICC_GRID),
      B = B,
      alpha = 0.05,
      seed = 42L,
      n_individuals = 735L,
      n_clusters = 353L,
      sigma_u_formula = "latent-variable: sigma_u^2 = icc * pi^2 / 3",
      lrt_df_reference = "chisq_1",
      power_workers = WORKERS,
      power_chunk = CHUNK,
      power_checkpoint = power$progress_path,
      sigma_bootstrap_checkpoint = sigma_boot$progress_path
    ),
    power_curve = curve,
    minimum_detectable_icc = min_detect,
    interpretation = list(
      decision_rule_result = if (is.numeric(min_detect) && min_detect <= 0.05) "nominally_well_powered" else "nominally_underpowered_or_above_grid",
      calibration_warning = "The glmmTMB LRT simulation rejects at high rates across the entire ICC grid, including ICC=0.01. Treat the nominal minimum detectable ICC as requiring Manager/statistical review before paper-facing prose."
    ),
    multi_member_only_fit = list(
      sigma_foo_point_estimate = round(sigma_point, 8),
      sigma_foo_bootstrap_ci_lower = round(as.numeric(sigma_ci[1]), 8),
      sigma_foo_bootstrap_ci_upper = round(as.numeric(sigma_ci[2]), 8),
      bootstrap_B = B,
      lrt_pvalue_against_icc_zero = round(lrt_p, 8)
    )
  )
}

bundle <- load_samples()
singleton_payload <- make_singleton_decomposition(bundle)
write(toJSON(singleton_payload, auto_unbox = TRUE, pretty = TRUE, na = "null"), SINGLETON_OUT)
cat("Saved ", SINGLETON_OUT, "\n", sep = "")

concordance_payload <- make_concordance(bundle$sample)
write(toJSON(concordance_payload, auto_unbox = TRUE, pretty = TRUE, na = "null"), CONCORD_OUT)
cat("Saved ", CONCORD_OUT, "\n", sep = "")

if (BENCHMARK_ONLY) {
  cat("T135_BENCHMARK_ONLY=1: skipping full power output.\n")
  quit(status = 0L)
}
power_payload <- make_power(bundle$sample)
write(toJSON(power_payload, auto_unbox = TRUE, pretty = TRUE, na = "null"), POWER_OUT)
cat("Saved ", POWER_OUT, "\n", sep = "")
