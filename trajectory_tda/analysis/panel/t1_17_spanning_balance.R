# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: T1.17 — Demographic balance table + propensity-score-matched spanning analysis.
#   Addresses reviewer M4 (§10): spanning (BHPS continuous) vs USoc newcomers may differ
#   systematically. Reports SMDs, matched subset sizes, age-stratified characteristics.
#   Escalates Betti comparison rerun to TDA Agent.
#
# Run from worktree root:
#   "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" trajectory_tda/analysis/panel/t1_17_spanning_balance.R

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
})

# Install MatchIt if needed
for (pkg in c("MatchIt")) {
  if (!requireNamespace(pkg, quietly = TRUE))
    install.packages(pkg, repos = "https://cloud.r-project.org")
}
suppressPackageStartupMessages(library(MatchIt))

set.seed(42)

PROJ_ROOT  <- "C:/Users/steph/TDL"
WORKTREE   <- normalizePath(getwd(), mustWork = FALSE)
DATA_TAB   <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab")
BHPS_DIR   <- file.path(DATA_TAB, "bhps")
UKHLS_DIR  <- file.path(DATA_TAB, "ukhls")
XWAVEDAT   <- file.path(PROJ_ROOT, "data/UKDA-6614-tab/tab/ukhls/xwavedat.tab")
ANALYSIS   <- file.path(PROJ_ROOT, "results/trajectory_tda_integration/05_analysis.json")
TRAJ_JSON  <- file.path(PROJ_ROOT, "results/trajectory_tda_integration/01_trajectories.json")

OUT_DIR <- file.path(WORKTREE, "results/panel_methodology/spanning_identification")
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

TODAY <- format(Sys.Date(), "%Y-%m-%d")

BHPS_WAVES  <- paste0("b", letters[1:18])
BHPS_YEARS  <- 1991:2008
UKHLS_WAVES <- letters[1:15]
UKHLS_YEARS <- 2009:2023

BHPS_CUTS  <- c(1282, 2437)
UKHLS_CUTS <- c(2153, 4139)

E_CODES <- c(1L, 2L, 5L, 11L, 12L, 13L, 14L, 15L)
U_CODES <- c(3L, 9L)
I_CODES <- c(4L, 6L, 7L, 8L, 10L, 97L)

recode_jbstat <- function(x) {
  r <- rep(NA_character_, length(x))
  xi <- as.integer(x)
  r[xi %in% E_CODES] <- "E"; r[xi %in% U_CODES] <- "U"; r[xi %in% I_CODES] <- "I"; r
}

cat("=== T1.17: Spanning Balance + PSM ===\n")

# ---------------------------------------------------------------------------
# 1. Load analytical sample pidps (n=27,280)
# ---------------------------------------------------------------------------
cat("Loading analytical sample pidps from 01_trajectories.json...\n")
traj_json <- fromJSON(TRAJ_JSON)
pidp_map  <- traj_json$metadata$pidp   # named vector: index -> pidp
anal_pidps <- as.integer(unlist(pidp_map))
n_anal <- length(anal_pidps)
cat("Analytical sample n:", n_anal, "\n")

# ---------------------------------------------------------------------------
# 2. Load xwavedat for all analytical + broader population
# ---------------------------------------------------------------------------
cat("Loading xwavedat...\n")
xwave <- fread(XWAVEDAT, sep = "\t",
               select = c("pidp", "birthy", "sex_dv",
                          "pasoc90_cc", "masoc90_cc"))
xwave[, birthy := as.integer(birthy)]
xwave[birthy <= 1900 | birthy > 2005 | is.na(birthy), birthy := NA_integer_]
xwave_anal <- xwave[pidp %in% anal_pidps]
cat("xwavedat rows for analytical sample:", nrow(xwave_anal), "\n")

# ---------------------------------------------------------------------------
# 3. Determine spanning vs newcomer from first observed wave
# ---------------------------------------------------------------------------
cat("Scanning indresp files for first-wave survey origin...\n")

get_first_survey_origin <- function(dir_path, waves, target_pidps, survey_label) {
  seen <- integer(0)
  result <- data.table(pidp = integer(0), survey_origin = character(0),
                       first_wave = character(0), first_year = integer(0))
  for (wi in seq_along(waves)) {
    wave  <- waves[wi]
    fpath <- file.path(dir_path, paste0(wave, "_indresp.tab"))
    if (!file.exists(fpath)) next
    wdt <- fread(fpath, sep = "\t", select = "pidp")
    wdt <- wdt[pidp %in% target_pidps & !pidp %in% seen]
    if (nrow(wdt) == 0L) next
    wdt[, survey_origin := survey_label]
    wdt[, first_wave    := wave]
    wdt[, first_year    := if (survey_label == "BHPS") BHPS_YEARS[wi] else UKHLS_YEARS[wi]]
    result <- rbindlist(list(result, wdt), fill = TRUE)
    seen   <- c(seen, wdt$pidp)
  }
  result
}

bhps_first  <- get_first_survey_origin(BHPS_DIR,  BHPS_WAVES,  anal_pidps, "BHPS")
ukhls_first <- get_first_survey_origin(UKHLS_DIR, UKHLS_WAVES, anal_pidps, "UKHLS")

cat("First wave in BHPS:", nrow(bhps_first),
    "| First wave in UKHLS:", nrow(ukhls_first), "\n")

# Spanning = appears in BOTH BHPS and UKHLS (first wave in BHPS, later in UKHLS)
# Since we search BHPS first, bhps_first captures anyone with ANY BHPS wave presence
ukhls_pidps_all <- fread(file.path(UKHLS_DIR, "a_indresp.tab"), sep="\t", select="pidp")$pidp

# Spanning = has BHPS first wave AND appears in UKHLS
bhps_pidps_set   <- bhps_first$pidp
# Check UKHLS presence for BHPS-first individuals
ukhls_presence   <- logical(length(bhps_pidps_set))
for (wave in UKHLS_WAVES) {
  fpath <- file.path(UKHLS_DIR, paste0(wave, "_indresp.tab"))
  if (!file.exists(fpath)) next
  wdt <- fread(fpath, sep = "\t", select = "pidp")
  ukhls_presence <- ukhls_presence | (bhps_pidps_set %in% wdt$pidp)
}
spanning_pidps  <- bhps_pidps_set[ukhls_presence]
bhps_only_pidps <- bhps_pidps_set[!ukhls_presence]
newcomer_pidps  <- ukhls_first[!pidp %in% bhps_pidps_set, pidp]

cat("Spanning (BHPS+UKHLS):", length(spanning_pidps), "\n")
cat("BHPS-only:", length(bhps_only_pidps), "\n")
cat("UKHLS newcomers:", length(newcomer_pidps), "\n")

# Create analytical sample classification
first_all <- rbindlist(list(bhps_first, ukhls_first), fill = TRUE)
setorder(first_all, pidp, first_year)
first_cov <- first_all[, .SD[1L], by = pidp]

first_cov[, group := fcase(
  pidp %in% spanning_pidps,  "spanning",
  pidp %in% bhps_only_pidps, "bhps_only",
  default = "newcomer"
)]

cat("\nGroup distribution in analytical sample:\n")
print(first_cov[, .N, by = group])

# ---------------------------------------------------------------------------
# 4. Load first-wave covariates: hiqual_dv, jbstat, income
# ---------------------------------------------------------------------------
cat("\nLoading first-wave covariates for balance table...\n")

load_covariate_wave <- function(dir_path, waves, wave_years, target_pidps, survey) {
  seen <- integer(0)
  out  <- data.table(pidp = integer(0), hiqual_dv = integer(0),
                     jbstat = integer(0), gor_dv = integer(0),
                     hidp = integer(0), wave = character(0), wave_year = integer(0))
  for (wi in seq_along(waves)) {
    wave  <- waves[wi]; wyear <- wave_years[wi]
    fpath <- file.path(dir_path, paste0(wave, "_indresp.tab"))
    if (!file.exists(fpath)) next
    hdr     <- names(fread(fpath, nrows = 0L, sep = "\t"))
    hq_col  <- paste0(wave, "_hiqual_dv")
    hidp_col <- paste0(wave, "_hidp")
    gor_col  <- paste0(wave, "_gor_dv")
    jb_col   <- if (paste0(wave, "_jbstat_bh") %in% hdr) paste0(wave, "_jbstat_bh")
                else if (paste0(wave, "_jbstat") %in% hdr) paste0(wave, "_jbstat")
                else NA_character_
    needed <- "pidp"
    opt    <- intersect(c(hidp_col, hq_col, gor_col, if (!is.na(jb_col)) jb_col), hdr)
    wdt    <- fread(fpath, sep = "\t", select = c(needed, opt))
    wdt    <- wdt[pidp %in% target_pidps & !pidp %in% seen]
    if (nrow(wdt) == 0L) next
    wdt[, wave      := wave]
    wdt[, wave_year := wyear]
    if (hq_col  %in% names(wdt)) setnames(wdt, hq_col,  "hiqual_dv",  skip_absent=TRUE)
    if (hidp_col %in% names(wdt)) setnames(wdt, hidp_col, "hidp",      skip_absent=TRUE)
    if (gor_col  %in% names(wdt)) setnames(wdt, gor_col,  "gor_dv",    skip_absent=TRUE)
    if (!is.na(jb_col) && jb_col %in% names(wdt)) setnames(wdt, jb_col, "jbstat", skip_absent=TRUE)
    out     <- rbindlist(list(out, wdt), fill = TRUE)
    seen    <- c(seen, wdt$pidp)
  }
  out
}

bhps_cov  <- load_covariate_wave(BHPS_DIR,  BHPS_WAVES,  BHPS_YEARS,  anal_pidps, "BHPS")
ukhls_cov <- load_covariate_wave(UKHLS_DIR, UKHLS_WAVES, UKHLS_YEARS, anal_pidps, "UKHLS")

first_covar <- rbindlist(list(bhps_cov, ukhls_cov), fill = TRUE, use.names = TRUE)
setorder(first_covar, pidp, wave_year)
first_covar <- first_covar[, .SD[1L], by = pidp]

# ---------------------------------------------------------------------------
# 5. Assemble balance dataset
# ---------------------------------------------------------------------------
cat("Assembling balance dataset...\n")

bal_dt <- merge(xwave_anal[, .(pidp, birthy, sex_dv)],
                first_covar[, .(pidp, jbstat, hiqual_dv, gor_dv, hidp, wave_year)],
                by = "pidp", all.x = TRUE)
bal_dt <- merge(bal_dt, first_cov[, .(pidp, group, first_year, survey_origin)],
                by = "pidp", all.x = TRUE)

bal_dt[, sex      := fifelse(as.integer(sex_dv) == 2L, 1L, 0L)]  # 1=female
bal_dt[, age_first := as.integer(wave_year) - as.integer(birthy)]
bal_dt[age_first < 16L | age_first > 80L | is.na(age_first), age_first := NA_integer_]
bal_dt[, hiqual   := as.integer(hiqual_dv)]
bal_dt[hiqual < 0L | is.na(hiqual), hiqual := NA_integer_]
bal_dt[, jbstat_bin := recode_jbstat(jbstat)]
bal_dt[, employed := as.integer(jbstat_bin == "E")]
bal_dt[is.na(group), group := "newcomer"]

n_span <- sum(bal_dt$group == "spanning", na.rm=TRUE)
n_new  <- sum(bal_dt$group == "newcomer", na.rm=TRUE)
n_bhps_only <- sum(bal_dt$group == "bhps_only", na.rm=TRUE)
cat("Balance dataset: spanning =", n_span, "| newcomers =", n_new,
    "| bhps_only =", n_bhps_only, "\n")

# ---------------------------------------------------------------------------
# 6. Standardised Mean Differences (SMDs)
# ---------------------------------------------------------------------------
cat("Computing SMDs...\n")

smd <- function(x, group, ref = "spanning") {
  g1 <- x[group == ref]
  g2 <- x[group != ref & group %in% c("newcomer")]
  g1 <- g1[!is.na(g1)]; g2 <- g2[!is.na(g2)]
  if (length(g1) == 0 || length(g2) == 0) return(NA_real_)
  pooled_sd <- sqrt((var(g1) + var(g2)) / 2)
  if (pooled_sd == 0) return(0)
  (mean(g1) - mean(g2)) / pooled_sd
}

vars_for_smd <- list(
  age_first = bal_dt$age_first,
  sex_female = bal_dt$sex,
  hiqual_dv  = bal_dt$hiqual,
  employed   = bal_dt$employed
)

smd_results <- lapply(names(vars_for_smd), function(v) {
  s <- smd(vars_for_smd[[v]], bal_dt$group)
  cat(sprintf("  SMD %-15s: %.4f\n", v, ifelse(is.na(s), NA, s)))
  list(variable = v,
       mean_spanning  = round(mean(vars_for_smd[[v]][bal_dt$group=="spanning"], na.rm=TRUE), 4),
       mean_newcomer  = round(mean(vars_for_smd[[v]][bal_dt$group=="newcomer"], na.rm=TRUE), 4),
       smd            = round(s, 4))
})
names(smd_results) <- names(vars_for_smd)

# ---------------------------------------------------------------------------
# 7. Propensity-score matching (MatchIt)
# ---------------------------------------------------------------------------
cat("\nRunning propensity-score matching (spanning vs newcomer)...\n")

match_dt <- bal_dt[group %in% c("spanning","newcomer") &
                   !is.na(age_first) & !is.na(sex) & !is.na(hiqual) & !is.na(employed)]
match_dt[, treated := as.integer(group == "spanning")]

if (nrow(match_dt) > 10L && sum(match_dt$treated) > 1L) {
  m_out <- tryCatch(
    matchit(treated ~ age_first + sex + hiqual + employed,
            data     = as.data.frame(match_dt),
            method   = "nearest",
            distance = "glm",
            link     = "logit",
            caliper  = 0.2,
            replace  = FALSE,
            ratio    = 1L),
    error = function(e) {
      cat("MatchIt failed:", conditionMessage(e), "\n")
      NULL
    }
  )

  if (!is.null(m_out)) {
    m_summary <- summary(m_out)
    n_matched_span <- sum(m_out$weights[match_dt$treated == 1L] > 0)
    n_matched_new  <- sum(m_out$weights[match_dt$treated == 0L] > 0)
    cat("Matched: spanning =", n_matched_span, "| newcomers =", n_matched_new, "\n")

    match_info <- list(
      n_spanning_unmatched = sum(match_dt$treated == 1L),
      n_newcomer_unmatched = sum(match_dt$treated == 0L),
      n_spanning_matched   = n_matched_span,
      n_newcomer_matched   = n_matched_new,
      method = "nearest-neighbour 1:1 logit propensity, caliper=0.2",
      seed   = 42L
    )
  } else {
    match_info <- list(status = "MatchIt failed", n_spanning = sum(match_dt$treated), n_newcomer = sum(1-match_dt$treated))
    n_matched_span <- 0L; n_matched_new <- 0L
  }
} else {
  cat("Insufficient spanning individuals for PSM — skipping.\n")
  match_info <- list(status = "skipped", n_spanning = n_span, n_newcomer = n_new, reason = "n_spanning too small or insufficient complete cases")
  n_matched_span <- 0L; n_matched_new <- 0L
}

# ---------------------------------------------------------------------------
# 8. Age-stratified (30–55) subset characteristics
# ---------------------------------------------------------------------------
cat("\nAge-stratified subset (30-55)...\n")

age_strat <- bal_dt[!is.na(age_first) & age_first >= 30L & age_first <= 55L]
n_age_span <- sum(age_strat$group == "spanning", na.rm=TRUE)
n_age_new  <- sum(age_strat$group == "newcomer", na.rm=TRUE)
cat("Age 30-55: spanning =", n_age_span, "| newcomers =", n_age_new, "\n")

age_strat_info <- list(
  age_band    = "30-55",
  n_spanning  = n_age_span,
  n_newcomer  = n_age_new,
  mean_age_spanning = round(mean(age_strat$age_first[age_strat$group=="spanning"], na.rm=TRUE), 2),
  mean_age_newcomer = round(mean(age_strat$age_first[age_strat$group=="newcomer"], na.rm=TRUE), 2),
  betti_rerun_escalation = paste0(
    "Betti comparison on age-stratified subset requires TDA pipeline rerun. ",
    "n_spanning=", n_age_span, ", n_newcomer=", n_age_new, " — ",
    "escalate to TDA Agent with subset pidp lists."
  )
)

# ---------------------------------------------------------------------------
# 9. Save outputs
# ---------------------------------------------------------------------------
cat("\nSaving outputs...\n")

balance_out <- list(
  run_params = list(seed=42L, date=TODAY, n_analytical=n_anal,
                    method="spanning=first_wave_in_BHPS_WAVES AND appears_in_UKHLS; newcomer=first_wave_in_UKHLS_WAVES"),
  population_counts = list(spanning=n_span, newcomer=n_new, bhps_only=n_bhps_only),
  balance_table = smd_results,
  betti_escalation = paste0(
    "The Betti comparison for spanning vs newcomer in P01-B §7 requires TDA pipeline rerun ",
    "on matched and age-stratified subsets. This is outside panel-statistics-agent scope. ",
    "Escalate to TDA Agent with: ",
    "(a) matched spanning pidps (n=", n_matched_span, "), ",
    "(b) matched newcomer pidps (n=", n_matched_new, "), ",
    "(c) age-stratified spanning pidps (n=", n_age_span, "), ",
    "(d) age-stratified newcomer pidps (n=", n_age_new, ")."
  )
)

BALANCE_PATH <- file.path(OUT_DIR, paste0("balance_", TODAY, ".json"))
write(toJSON(balance_out, auto_unbox=TRUE, pretty=TRUE), BALANCE_PATH)
cat("Saved:", BALANCE_PATH, "\n")

matched_out <- list(
  run_params = list(seed=42L, date=TODAY),
  matching   = match_info,
  age_stratified = age_strat_info
)
MATCH_PATH <- file.path(OUT_DIR, paste0("matched_subset_", TODAY, ".json"))
write(toJSON(matched_out, auto_unbox=TRUE, pretty=TRUE), MATCH_PATH)
cat("Saved:", MATCH_PATH, "\n")

cat("=== T1.17 complete ===\n")
cat("ESCALATION: Betti comparison on matched and age-stratified subsets requires TDA Agent.\n")
