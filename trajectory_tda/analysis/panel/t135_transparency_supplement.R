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
  library(mice)
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
XWAVEDAT <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab")
DATA_TAB <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab")
BHPS_DIR <- file.path(DATA_TAB, "bhps")
UKHLS_DIR <- file.path(DATA_TAB, "ukhls")

ICC_GRID <- c(0.01, 0.025, 0.05, 0.10, 0.20)
SIM_ICC_GRID <- c(0, ICC_GRID)
B <- as.integer(Sys.getenv("T135_B", "1000"))
if (B != 1000L && Sys.getenv("T135_ALLOW_SMALL_B", "0") != "1") {
  stop("T1.35 requires B=1000; set T135_ALLOW_SMALL_B=1 only for local benchmark tests.")
}
WORKERS <- max(4L, as.integer(Sys.getenv("T135_WORKERS", "4")))
CHUNK <- max(1L, as.integer(Sys.getenv("T135_CHUNK", as.character(WORKERS * 5L))))
BENCHMARK_ONLY <- Sys.getenv("T135_BENCHMARK_ONLY", "0") == "1"
RUN_LABEL <- if (nzchar(OUT_LABEL)) paste0(OUT_LABEL, "_", TODAY) else TODAY

BHPS_WAVES <- paste0("b", letters[1:18])
BHPS_YEARS <- 1991:2008
UKHLS_WAVES <- letters[1:15]
UKHLS_YEARS <- 2009:2023
E_CODES <- c(1L, 2L, 5L, 11L, 12L, 13L, 14L, 15L)
U_CODES <- c(3L, 9L)
I_CODES <- c(4L, 6L, 7L, 8L, 10L, 97L)
BHPS_CUTS <- c(1282, 2437)
UKHLS_CUTS <- c(2153, 4139)
EXPECTED_PRIOR_T135 <- list(n = 7098L, singletons = 6363L, multi_members = 735L, multi_clusters = 353L)

iso_now <- function() format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ")

as_json_list <- function(x) {
  if (length(x) == 0L) list() else as.list(x)
}

recode_jbstat <- function(x) {
  r <- rep(NA_character_, length(x))
  xi <- as.integer(x)
  r[xi %in% E_CODES] <- "E"
  r[xi %in% U_CODES] <- "U"
  r[xi %in% I_CODES] <- "I"
  r
}

birth_cohort_of <- function(birth_year) {
  fcase(
    birth_year < 1950, "pre-1950",
    birth_year >= 1950 & birth_year < 1960, "1950s",
    birth_year >= 1960 & birth_year < 1970, "1960s",
    birth_year >= 1970 & birth_year < 1980, "1970s",
    birth_year >= 1980, "post-1980",
    default = NA_character_
  )
}

load_first_wave <- function(dir_path, waves, wave_years, target_pidps) {
  first_dt <- data.table(
    pidp = integer(0), hiqual_dv = integer(0), jbstat = integer(0),
    gor_dv = integer(0), hidp = integer(0), wave = character(0),
    wave_year = integer(0), survey_origin = character(0)
  )
  seen_first <- integer(0)
  for (wi in seq_along(waves)) {
    wave <- waves[wi]
    fpath <- file.path(dir_path, paste0(wave, "_indresp.tab"))
    if (!file.exists(fpath)) next
    hdr <- names(fread(fpath, nrows = 0L, sep = "\t"))
    hidp_col <- paste0(wave, "_hidp")
    gor_col <- paste0(wave, "_gor_dv")
    hq_col <- paste0(wave, "_hiqual_dv")
    jb_col <- if (paste0(wave, "_jbstat_bh") %in% hdr) {
      paste0(wave, "_jbstat_bh")
    } else if (paste0(wave, "_jbstat") %in% hdr) {
      paste0(wave, "_jbstat")
    } else {
      NA_character_
    }
    opt <- intersect(c(gor_col, hq_col, if (!is.na(jb_col)) jb_col), hdr)
    wdt <- fread(fpath, sep = "\t", select = c("pidp", hidp_col, opt))
    wdt <- wdt[pidp %in% target_pidps]
    if (nrow(wdt) == 0L) next
    wdt[, wave := wave]
    wdt[, wave_year := wave_years[wi]]
    wdt[, survey_origin := fifelse(wave %in% BHPS_WAVES, "BHPS", "UKHLS")]
    setnames(wdt, hidp_col, "hidp", skip_absent = TRUE)
    if (!is.na(jb_col)) setnames(wdt, jb_col, "jbstat", skip_absent = TRUE)
    setnames(wdt, hq_col, "hiqual_dv", skip_absent = TRUE)
    setnames(wdt, gor_col, "gor_dv", skip_absent = TRUE)
    new_pidps <- setdiff(wdt$pidp, seen_first)
    if (length(new_pidps) > 0L) {
      first_dt <- rbindlist(list(first_dt, wdt[pidp %in% new_pidps]), fill = TRUE)
      seen_first <- c(seen_first, new_pidps)
    }
  }
  setorder(first_dt, pidp, wave_year)
  first_dt[, .SD[1L], by = pidp]
}

get_first_income <- function(hhresp_dir, waves) {
  rbindlist(lapply(waves, function(wave) {
    fpath <- file.path(hhresp_dir, paste0(wave, "_hhresp.tab"))
    if (!file.exists(fpath)) return(NULL)
    hdr <- names(fread(fpath, nrows = 0L, sep = "\t"))
    hidp_col <- paste0(wave, "_hidp")
    inc_col <- paste0(wave, "_fihhmngrs_dv")
    if (!hidp_col %in% hdr || !inc_col %in% hdr) return(NULL)
    dt <- fread(fpath, sep = "\t", select = c(hidp_col, inc_col))
    setnames(dt, c(hidp_col, inc_col), c("hidp", "income"))
    dt[, wave := wave]
    dt
  }), fill = TRUE)
}

load_samples <- function() {
  wa <- as.data.table(fromJSON(ESCAPE_PATH)$assignments)
  starters <- wa[is_disadvantaged_starter == TRUE]
  starter_dt <- starters[, .(pidp, escape, age_first_window, first_window_regime)]
  starter_pidps <- starter_dt$pidp

  xwave <- fread(XWAVEDAT, sep = "\t", select = c("pidp", "birthy", "sex_dv"))
  xwave[, birthy := as.integer(birthy)]
  xwave[birthy <= 1900 | birthy > 2005 | is.na(birthy), birthy := NA_integer_]
  xwave <- xwave[pidp %in% starter_pidps]
  xwave[, birth_year := as.integer(birthy)]
  xwave[birth_year <= 1900 | birth_year > 2005, birth_year := NA_integer_]
  xwave[, sex := fifelse(as.integer(sex_dv) == 2L, "female", fifelse(as.integer(sex_dv) == 1L, "male", NA_character_))]
  xwave[, birth_cohort := birth_cohort_of(birth_year)]
  starter_dt <- merge(starter_dt, xwave[, .(pidp, birth_year, sex, birth_cohort)], by = "pidp", all.x = TRUE)

  first_cov <- rbindlist(list(
    load_first_wave(BHPS_DIR, BHPS_WAVES, BHPS_YEARS, starter_pidps),
    load_first_wave(UKHLS_DIR, UKHLS_WAVES, UKHLS_YEARS, starter_pidps)
  ), fill = TRUE, use.names = TRUE)
  setorder(first_cov, pidp, wave_year)
  first_cov <- first_cov[, .SD[1L], by = pidp]

  all_inc <- rbindlist(list(
    get_first_income(BHPS_DIR, BHPS_WAVES),
    get_first_income(UKHLS_DIR, UKHLS_WAVES)
  ), fill = TRUE)
  first_inc <- merge(
    first_cov[, .(pidp, hidp, wave, wave_year, survey_origin)],
    all_inc,
    by = c("hidp", "wave"),
    all.x = TRUE
  )
  setorder(first_inc, pidp, wave_year)
  first_inc <- first_inc[income > 0L & !is.na(income)][, .SD[1L], by = pidp]
  first_inc[, income_tercile_init := fcase(
    survey_origin == "BHPS" & income <= BHPS_CUTS[1L], "L",
    survey_origin == "BHPS" & income <= BHPS_CUTS[2L], "M",
    survey_origin == "BHPS" & income > BHPS_CUTS[2L], "H",
    survey_origin == "UKHLS" & income <= UKHLS_CUTS[1L], "L",
    survey_origin == "UKHLS" & income <= UKHLS_CUTS[2L], "M",
    survey_origin == "UKHLS" & income > UKHLS_CUTS[2L], "H"
  )]

  base <- merge(
    starter_dt,
    first_cov[, .(pidp, hiqual_dv, jbstat, gor_dv, hidp, wave_year, survey_origin)],
    by = "pidp",
    all.x = TRUE
  )
  base <- merge(base, first_inc[, .(pidp, income_tercile_init)], by = "pidp", all.x = TRUE)
  setnames(base, "hidp", "hidp_first")
  base[, hh_group := paste0(survey_origin, "_", hidp_first)]
  base[, jbstat_bin := recode_jbstat(jbstat)]
  base[hiqual_dv <= 0 | is.na(hiqual_dv), hiqual_dv := NA_integer_]
  base[gor_dv <= 0 | is.na(gor_dv), gor_dv := NA_integer_]
  base[, regime_6 := as.integer(first_window_regime == 6L)]

  foo <- fread(FOO_PATH)
  ipw <- as.data.table(readRDS(IPW_PATH))
  mids <- readRDS(MIDS_PATH)
  mids_pidps <- as.integer(mids$pidps)
  comp <- as.data.table(complete(mids$mids, 1L))
  nssec <- data.table(
    pidp = mids_pidps,
    nssec_proxy = factor(c("H", "M", "L")[pmax(1L, pmin(3L, as.integer(round(comp$nssec_proxy))))], levels = c("H", "M", "L"))
  )

  starter_all <- merge(base, ipw[, .(pidp, ipw_trimmed, in_analytical_sample)], by = "pidp", all.x = TRUE)
  starter_all <- merge(starter_all, foo[, .(pidp, foo_cluster, foo_size)], by = "pidp", all.x = TRUE)
  starter_all <- merge(starter_all, nssec, by = "pidp", all.x = TRUE)
  starter_all[, ipw_eligible := !is.na(ipw_trimmed)]

  pred_cols <- c(
    "age_first_window", "sex", "hiqual_dv", "jbstat_bin",
    "income_tercile_init", "birth_cohort", "gor_dv", "survey_origin"
  )
  cc_mask <- complete.cases(starter_all[, ..pred_cols]) &
    !is.na(starter_all$escape) &
    !is.na(starter_all$nssec_proxy) &
    !is.na(starter_all$hh_group) &
    !is.na(starter_all$foo_cluster) &
    !is.na(starter_all$ipw_trimmed)
  sample <- starter_all[cc_mask]
  sample[, t135_cluster_n := .N, by = foo_cluster]
  sample[, foo_cluster := as.integer(foo_cluster)]

  singleton <- sample[t135_cluster_n == 1L]
  multi <- sample[t135_cluster_n > 1L]
  actual_counts <- list(
    n = as.integer(nrow(sample)),
    singletons = as.integer(nrow(singleton)),
    multi_members = as.integer(nrow(multi)),
    multi_clusters = as.integer(uniqueN(multi$foo_cluster))
  )

  list(
    sample = sample,
    live_counts = list(
      n_disadvantaged_starters = as.integer(nrow(starters)),
      n_after_regression_tier3_complete_case = actual_counts$n,
      singletons = actual_counts$singletons,
      multi_members = actual_counts$multi_members,
      multi_clusters = actual_counts$multi_clusters
    ),
    reconciliation = list(
      method = "Exact procedural reconstruction of regression_tier3.R on branch run/tier3-regression: disadvantaged starters, first-wave covariates, first household income, IPW, FOO cluster, first completed NS-SEC MICE draw, and the same complete-case filter used before the cross-classified GLMM fit.",
      status = if (
        actual_counts$n == EXPECTED_PRIOR_T135$n &&
          actual_counts$singletons == EXPECTED_PRIOR_T135$singletons &&
          actual_counts$multi_members == EXPECTED_PRIOR_T135$multi_members &&
          actual_counts$multi_clusters == EXPECTED_PRIOR_T135$multi_clusters
      ) "matches_prior_t135_contract_counts" else "regression_tier3_actual_sample_differs_from_prior_t135_contract_counts",
      expected_prior_t135_counts = EXPECTED_PRIOR_T135,
      actual_regression_tier3_counts = actual_counts,
      forced_exclusions_applied = FALSE,
      note = "The prior 7,098/735/353 counts are not forced. If this mismatch is not accepted, the Manager must amend the corrected contract or identify a different archived sample-definition path."
    ),
    foo_all = foo,
    starter_all = starter_all,
    mids_pidps = mids_pidps
  )
}

make_singleton_decomposition <- function(sample_bundle) {
  sample <- copy(sample_bundle$sample)
  foo_all <- as.data.table(sample_bundle$foo_all)
  starter_all <- as.data.table(sample_bundle$starter_all)
  mids_pidps <- sample_bundle$mids_pidps
  setkey(foo_all, foo_cluster)
  setkey(starter_all, pidp)

  singletons <- sample[t135_cluster_n == 1L]
  reason_vocab <- c(
    "does_not_start_in_r2_or_r6",
    "ipw_zero_due_to_ineligibility",
    "dropped_by_10_of_14_rule",
    "missing_nssec_proxy",
    "other_filter_chain"
  )

  classify_sibling <- function(sib_pidp) {
    row <- starter_all[.(sib_pidp), nomatch = 0]
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
    siblings <- foo_all[.(row$foo_cluster), nomatch = 0]
    siblings <- siblings[pidp != row$pidp]
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
  n_total_singletons <- nrow(singletons)
  if (true_count + filtered_count != n_total_singletons) stop("Singleton decomposition is not exhaustive.")
  if (sum(primary_counts) != filtered_count) stop("Primary reason counts do not sum to filtered singleton count.")

  list(
    schema_version = "panel-output/singleton-decomposition/v1",
    generated_at = iso_now(),
      task = "T1.35b singleton decomposition",
    pre_registration = "2026-05-25",
    params = list(
      t121_source_path = ESCAPE_PATH,
      xwavedat_source_path = XWAVEDAT,
      n_total_singletons = as.integer(n_total_singletons),
      n_t121_total_sample = as.integer(nrow(sample)),
      sample_provenance = "regression_tier3.R fitted-stage complete-case sample reconstruction; FOO clusters from foo_clusters_2026-05-06.csv",
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
  pairs <- multi[order(pidp), {
    pair_idx <- utils::combn(seq_len(.N), 2L)
    data.table(
      pidp_1 = as.integer(pidp[pair_idx[1L, ]]),
      pidp_2 = as.integer(pidp[pair_idx[2L, ]]),
      escape_1 = as.integer(escape[pair_idx[1L, ]]),
      escape_2 = as.integer(escape[pair_idx[2L, ]])
    )
  }, by = foo_cluster]
  if (nrow(pairs) < uniqueN(multi$foo_cluster)) {
    stop("All-pairs enumeration produced fewer pairs than contributing clusters.")
  }
  if (any(pairs$pidp_1 > pairs$pidp_2)) {
    stop("Pair member ordering rule violated: pidp_1 must be the smaller pidp.")
  }
  pairs
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
  clusters <- unique(pairs$foo_cluster)
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
      n_pairs = as.integer(nrow(pairs)),
      n_clusters = as.integer(uniqueN(pairs$foo_cluster)),
      member_ordering_rule = "smaller pidp within cluster is member 1",
      bootstrap_B = B,
      seed = 42L,
      source_sample = "exact regression_tier3.R complete-case T1.21 reconstruction; no forced reconciliation to prior T1.35 counts",
      sample_provenance = "all within-family pairs from the fitted-stage multi-member FOO sample; bootstrap resamples FOO clusters",
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

fit_converged <- function(fit) {
  isTRUE(fit$fit$convergence == 0L) && isTRUE(fit$sdr$pdHess)
}

boundary_mixture_p <- function(lrt) {
  if (!is.finite(lrt) || lrt <= 0) return(1)
  0.5 * pchisq(lrt, df = 1, lower.tail = FALSE)
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
  if (!is.finite(icc) || icc < 0 || icc >= 1) {
    stop("ICC must be in [0, 1) for latent-variable sigma_u conversion.")
  }
  set.seed(420000L + as.integer(round(icc * 1000)) * 10000L + iter)
  sigma_u <- sqrt((icc / (1 - icc)) * pi^2 / 3)
  cluster <- rep(seq_along(cluster_sizes), cluster_sizes)
  u <- rnorm(length(cluster_sizes), 0, sigma_u)
  p <- plogis(qlogis(0.05) + u[cluster])
  y <- rbinom(length(cluster), 1L, p)
  dt <- data.table(escape = y, foo_cluster = factor(cluster))
  fit0 <- tryCatch(glmmTMB(escape ~ 1, data = dt, family = binomial()), error = function(e) NULL)
  fit1 <- tryCatch(glmmTMB(escape ~ 1 + (1 | foo_cluster), data = dt, family = binomial()), error = function(e) NULL)
  if (is.null(fit0) || is.null(fit1) || !fit_converged(fit0) || !fit_converged(fit1)) {
    return(list(iter = iter, reject = NA, lrt = NA_real_, pvalue = NA_real_, convergence_failure = TRUE))
  }
  lrt <- max(0, 2 * (as.numeric(logLik(fit1)) - as.numeric(logLik(fit0))))
  pval <- boundary_mixture_p(lrt)
  list(iter = iter, reject = is.finite(pval) && pval <= alpha, lrt = lrt, pvalue = pval, convergence_failure = FALSE)
}

run_power <- function(multi, b = B, workers = WORKERS, chunk = CHUNK) {
  progress_path <- file.path(PARTIAL_DIR, paste0("power_analysis_", RUN_LABEL, "_progress.rds"))
  cluster_sizes <- as.integer(multi[, .N, by = foo_cluster]$N)
  if (length(cluster_sizes) == 0L || sum(cluster_sizes) == 0L) stop("Power sample structure mismatch.")
  if (file.exists(progress_path)) {
    progress <- readRDS(progress_path)
  } else {
    progress <- list(
      results = setNames(vector("list", length(SIM_ICC_GRID)), as.character(SIM_ICC_GRID)),
      lrt = setNames(vector("list", length(SIM_ICC_GRID)), as.character(SIM_ICC_GRID)),
      completed = setNames(rep(0L, length(SIM_ICC_GRID)), as.character(SIM_ICC_GRID))
    )
    for (icc in SIM_ICC_GRID) {
      progress$results[[as.character(icc)]] <- rep(NA, b)
      progress$lrt[[as.character(icc)]] <- rep(NA_real_, b)
    }
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
    clusterExport(cl, c("simulate_power_one", "fit_converged", "boundary_mixture_p"), envir = environment())
  }
  for (icc in SIM_ICC_GRID) {
    key <- as.character(icc)
    completed <- as.integer(progress$completed[[key]])
    remaining <- if (completed >= b) integer(0) else seq.int(completed + 1L, b)
    for (start in seq(1L, length(remaining), by = chunk)) {
      batch <- remaining[start:min(length(remaining), start + chunk - 1L)]
      res <- if (is.null(cl)) lapply(batch, simulate_power_one, icc = icc, cluster_sizes = cluster_sizes)
        else parLapplyLB(cl, batch, simulate_power_one, icc = icc, cluster_sizes = cluster_sizes)
      for (r in res) {
        progress$results[[key]][r$iter] <- if (is.na(r$reject)) NA else isTRUE(r$reject)
        progress$lrt[[key]][r$iter] <- r$lrt
      }
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
  null_fit <- tryCatch(glmmTMB(escape ~ 1, data = multi, family = binomial()), error = function(e) NULL)
  full_fit <- tryCatch(glmmTMB(escape ~ 1 + (1 | foo_cluster), data = multi, family = binomial()), error = function(e) NULL)
  lrt_p <- if (is.null(null_fit) || is.null(full_fit) || !fit_converged(null_fit) || !fit_converged(full_fit)) {
    NA_real_
  } else {
    boundary_mixture_p(max(0, 2 * (as.numeric(logLik(full_fit)) - as.numeric(logLik(null_fit)))))
  }
  power <- run_power(copy(multi))
  summarise_sim <- function(icc) {
    vals <- power$progress$results[[as.character(icc)]]
    converged <- !is.na(vals)
    n_converged <- sum(converged)
    n_rej <- sum(vals[converged] == TRUE)
    emp <- if (n_converged == 0L) NA_real_ else n_rej / n_converged
    list(
      icc = icc,
      empirical_power = if (is.na(emp)) NULL else round(emp, 8),
      n_rejections = as.integer(n_rej),
      n_converged = as.integer(n_converged),
      convergence_failures = as.integer(B - n_converged),
      bootstrap_se_of_power = if (is.na(emp)) NULL else round(sqrt(emp * (1 - emp) / n_converged), 8)
    )
  }
  calibration_row <- summarise_sim(0)
  type_i <- calibration_row$empirical_power
  calibrated <- !is.null(type_i) && abs(type_i - 0.05) <= 0.03
  curve <- lapply(ICC_GRID, function(icc) {
    summarise_sim(icc)
  })
  min_detect <- if (!calibrated) {
    "engine not calibrated"
  } else {
    found <- "greater than 0.20"
    for (row in curve) {
      if (!is.null(row$empirical_power) && row$empirical_power >= 0.80) {
        found <- row$icc
        break
      }
    }
    found
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
      n_individuals = as.integer(nrow(multi)),
      n_clusters = as.integer(uniqueN(multi$foo_cluster)),
      sigma_u_formula = "latent-variable: sigma_u^2 = (icc / (1 - icc)) * pi^2 / 3",
      lrt_df_reference = "chisq_0_1_mixture",
      null_engine = "glmmTMB",
      full_engine = "glmmTMB",
      power_workers = WORKERS,
      power_chunk = CHUNK,
      power_checkpoint = power$progress_path,
      sigma_bootstrap_checkpoint = sigma_boot$progress_path,
      sample_reconciliation = list(
        sample_provenance = "regression_tier3.R fitted-stage complete-case sample reconstruction; power uses the multi-member FOO cluster-size distribution from that sample",
        expected_prior_t135_counts = EXPECTED_PRIOR_T135,
        actual_regression_tier3_counts = list(
          n = as.integer(nrow(sample)),
          singletons = as.integer(sum(sample$t135_cluster_n == 1L)),
          multi_members = as.integer(nrow(multi)),
          multi_clusters = as.integer(uniqueN(multi$foo_cluster))
        )
      )
    ),
    calibration = list(
      type_i_at_icc0 = type_i,
      calibrated = calibrated,
      tolerance = 0.03,
      alpha = 0.05,
      n_rejections = calibration_row$n_rejections,
      n_converged = calibration_row$n_converged,
      convergence_failures = calibration_row$convergence_failures
    ),
    power_curve = curve,
    minimum_detectable_icc = min_detect,
    interpretation = list(
      decision_rule_result = if (!calibrated) "engine_not_calibrated" else if (is.numeric(min_detect) && min_detect <= 0.05) "nominally_well_powered" else "nominally_underpowered_or_above_grid",
      non_estimability_warning = "The multi-member FOO variance component is treated as non-estimable on this tiny/concordant cluster structure; sigma_foo is reported as a separation artifact rather than a substantive large FOO effect."
    ),
    multi_member_only_fit = list(
      sigma_foo_point_estimate = round(sigma_point, 8),
      sigma_foo_bootstrap_ci_lower = round(as.numeric(sigma_ci[1]), 8),
      sigma_foo_bootstrap_ci_upper = round(as.numeric(sigma_ci[2]), 8),
      bootstrap_B = B,
      lrt_pvalue_against_icc_zero = round(lrt_p, 8),
      sigma_foo_estimability = "not_reliably_estimable_separation_artifact"
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
