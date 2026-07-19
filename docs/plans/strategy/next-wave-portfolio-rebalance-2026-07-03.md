# Next-Wave Research Portfolio Rebalance (canonical)

> **Prepared 2026-07-03** by a tool-enabled strategic-director session (Fable 5, systematic mode);
> **reconciled** the same day into this single canonical document.
>
> **Provenance.** Two independent passes were run against the same brief. The first pivoted Track A to
> US public data (IRS migration + FEMA, CMS providers, US Census) with an AI-weather-forecast bold bet;
> the second kept Track A on UK panel/open data and ported the signature Markov ladder into
> seismology/ecology. Stephen chose the **UK-open pass** as the spine — deliberately, the UK microdata
> edge is a moat he wants to lean on — and this file merges the genuinely additive ideas from the US
> pass into it (chiefly its *temporal* segregation-morphology angle and its precise TTK finding). The
> two source passes are superseded by this file.
>
> **Data-access question resolved (was the whole fork).** Stephen is **registered with the UK Data
> Service** and holds access to the datasets this programme needs **at the required level** — standard
> **End User Licence / Safeguarded** access, *not* Secure Lab / Special Licence / controlled access.
> So the next-wave data constraint is: **openly downloadable OR UK Data Service EUL/Safeguarded
> (registered access); excludes only Secure-Lab / special-licence / controlled data.** This removes the
> access risk from every UK Track-A candidate below (BHPS/USoc are already held; IMD/Census/NHS/OS are
> OGL-open).
>
> Companion to [`Meta-Research-Plan-23-03-2026.md`](./Meta-Research-Plan-23-03-2026.md) (superseded for
> the *future* programme) and [`Discovery-Harness-Plan-16-06-2026.md`](./Discovery-Harness-Plan-16-06-2026.md).
> **Horizon:** 6–18 months. **Status:** recommendation for User ratification; scorecards are Assay-*style*
> previews, not completed `/assay` runs. Nothing here authorizes compute.

---

## Method note

Five verified stages: (1) edge inventory; (2) a three-track frontier scan starting inside the Scout signal —
the two inbox weeks plus the expanded seed (`_NEW-2024-2026-Literature-Review.md`, 35 Literature Notes, 4
Perplexity captures) — under a forceful adversarial filter, then an outward roam via three parallel sub-agents;
(3) an insight-capability (TTK) audit; (4) verified-feasibility scoring (two decision-relevant claims checked
directly — see §(e)); (5) this synthesis. The Scout seed was genuinely thin on Track B by design (the watchlist
streams are all social/finance/methods), so the Track B roam carries that load under the same gate.

> **Verification status (updated 2026-07-03):** the first roam used a mismatched search index (a Wiley
> `semanticSearch` gateway that returned off-query results); a **corrected re-roam** was run with that tool
> disabled and WebSearch/WebFetch/alphaXiv named, every citation fetched-and-confirmed, and every "no prior
> work" claim required to record its query. The scorecards below carry the corrected verdicts; the full
> correction log with provenance is in **§(g) Re-roam verification pass**. Net effect: Track A held and
> strengthened; Track B's weather-regime alternate was killed (a missed foundational paper) and two of its
> kills were *vacated* (false-match citations); Track C's C1 strengthened and C2 weakened.

---

## (a) Executive rebalance

**One sentence:** weight the next wave toward **Track A** (edge-leveraging UK-open-data work, where topology
earns its keep fastest and most fundably), carry **one genuinely bold Track B bet** (a signature-method port
into a field that hasn't seen null-calibrated PH testing), and hold **Track C open as cheap optionality**
anchored on persistent Laplacians — with **attention**, not compute, as the binding constraint.

| Track | Attention | Agent-compute | Role | Committed bets |
|---|---:|---:|---|---|
| **A — Adjacent, edge-leveraging** | **50%** | 40% | Near-term, fundable, low-risk outputs | 3 (2 near, 1 methods-flagship) |
| **B — Bold, method-led** | **30%** | 40% | One field-defining port, carried by agent compute | 2 committed + 1 User-decision |
| **C — Frontier mathematics** | **20%** | 20% | Optionality; persistent-Laplacian probe | 2 build + 1 watch |

The attention/compute asymmetry is deliberate: agent compute is cheap and parallelizable, so Tracks B and C
(permutation batteries on open catalogs, PL spectra) are loaded onto compute while sparing the scarce resource —
Stephen's attention. No more than **two manuscript-critical analyses** active at once.

---

## Edge statement (the yardstick)

TDL's edge is **rigorous, null-calibrated, Wasserstein-2-primary persistent-homology inference on UK longitudinal
panel microdata, executed by a trustworthy agent workforce.**

- **Signature method:** the **Markov memory ladder** — a permutation-null battery testing whether observed PH
  exceeds a *k*-th-order Markov null at each order *k*. Most portable, most reusable; generalises to any
  sequential/temporal data with a well-posed null.
- **Machinery:** W2 (primary) + landscape-L² testing; frozen-representation embedding (n-gram → PCA, frozen
  loadings across obs/null draws); validated multiparameter PH (`multipers`); Morse-Smale via TTK; Mapper;
  zigzag (planned). A strong contracts/assurance layer that makes agent-run research trustworthy.
- **Data moat:** BHPS (1991–2008) + USoc (2009–, 14 waves); the 27,280-trajectory frozen embedding; 8,459
  spanning individuals; household IDs.
- **Capacity:** one researcher (attention = bottleneck) + agent workforce + local i7/32GB/RTX-3080 + occasional
  cloud A100 (~20–40 GPU-hr). Runtime estimates must cover the *complete* unit (prep → representation → null →
  topology → comparison → review), not just the PH kernel.
- **Data constraint (resolved):** openly downloadable **or UK Data Service EUL/Safeguarded (registered
  access, which Stephen holds)** — excludes only Secure-Lab / special-licence / controlled data. Existing
  holdings are not the boundary; UK microdata reachable at EUL level is in-bounds and is the *moat*.

GNNs, CCNNs, sheaves, quivers, and broad topological deep learning are **not** current execution advantages —
they are frontier investments and receive no incumbency bonus.

---

## (b) Three-track shortlist (Assay-style scorecards)

Rubric: **Axis-1** topology-earns-its-keep = adversarial pass/fail **gate**; **Axis-2** data feasibility 0–3;
**Axis-3** novelty 0–3. PROMOTE iff gate passes and (Axis-2 + Axis-3) ≥ 4, neither = 0.

### Track A — Adjacent, edge-leveraging (UK-open)

**A1 · Multiscale topological autocorrelation in UK deprivation clustering (MCbiF on IMD × Census hierarchy)**
- *New question:* do England's nested deprivation clusterings (LSOA→MSOA→LAD) show genuine multiscale
  fragmentation, distinguishing regions where deprivation is *scale-fragile* (administrative artifact) from
  *scale-robust* (real spatial phenomenon)?
- *Construction:* 2-parameter PH (Schindler 2025 [MCbiF](https://arxiv.org/abs/2510.14710)) over (resolution ×
  cover radius) on IMD 7-domain z-score vectors — a defensible metric space, not an invented embedding.
- *Feature → claim:* MCbiF topological-autocorrelation statistic; specific city-regions show higher multiscale
  fragmentation than a spatially-permuted null.
- *Baseline:* ARI-across-resolutions / ONS OAC consistency / Moran's I.
- *Gate:* **PASS**, conditionally — survives only if the claim is fragmentation-*across-scale* (which ARI/Moran's
  cannot express), not raw autocorrelation. Enforce the framing at spike.
- *Data:* IMD 2019/2025 LSOA (OGL); ONS 2021 OAC + geography hierarchy (OGL). **Axis-2 = 3.**
- *Novelty:* MCbiF has only synthetic validation; no real socioeconomic-clustering application exists. **Axis-3 = 3.**
- *Effort:* ~4–5 attention-weeks; local. MCbiF's bifiltration is not off-the-shelf in `multipers` — budget
  reimplementation. **Sum 6 → PROMOTE (Track-A methods flagship).**

**A2 · Intergenerational topological inheritance (household-linked BHPS/USoc parent–child pairs)**
- *New question:* is intergenerational mobility topologically *path-dependent* — does the Markov ladder on the
  **joint** parent×child process reject a *k*=1 null at a higher order than either trajectory alone?
- *Construction:* reuse the frozen 27,280 embedding; points = household-linked (parent, child) coordinates at
  matched life-stage, embedded with the *same frozen loadings* (`representation-freeze-audit` is load-bearing);
  VR complex + Markov ladder on the joint process.
- *Feature → claim:* H1 loops = recurring joint career patterns; joint memory-depth exceeds individual.
- *Baseline:* rank-rank / income-elasticity mobility regression (which collapses each trajectory to one statistic).
- *Gate:* **PASS** — closest fit to the signature method on a genuinely new object.
- *Data:* no new acquisition (household IDs, held); `hgrid` coding must clear `/bhps-wave-crosswalk`. **Axis-2 = 2**
  (parent–child pairs with adequate two-sided overlap are likely low thousands — a real point-density gate).
- *Novelty:* the topological-intergenerational niche is open, but this *is* the already-listed P06 idea. **Axis-3 = 2.**
- *Effort:* ~4 attention-weeks; local. **Sum 4 → PROMOTE.** Absorbs and sharpens P06 (see §(e)).

**A3 · NHS GP coverage deserts (VR/witness on a travel-time metric)**
- *New question:* which GP-coverage holes persist across the *plausible range* of travel-time thresholds (robust
  deserts) vs appearing only at one arbitrary cutoff (the NHS's fixed "X-minute" rule)?
- *Construction:* points = population-weighted LSOA centroids; metric = network travel time to nearest practice
  (the field-standard access metric); VR/witness filtration on radius.
- *Feature → claim:* H0 components persisting beyond a null of randomly-relocated practices (capacity fixed) =
  genuine undersupply, not low density.
- *Baseline:* 2SFCA and single-threshold coverage. Must show cases where PH and 2SFCA *disagree*.
- *Gate:* **PASS**, conditionally (method established; contribution = persistence-across-thresholds + UK findings).
- *Data:* NHS ODS GP locations (OGL); ONS LSOA population (OGL); OS Open Roads (OGL) — verified open. **Axis-2 = 3.**
- *Novelty:* **verified UK-first** (no UK GP-access PH exists), but the *method* is established
  ([Hickok 2024](https://arxiv.org/abs/2206.04834) polling sites; [González 2025](https://arxiv.org/abs/2512.12011)
  California sexual-health; Cooling-Center 2024). Domain-novel, not method-novel. **Axis-3 = 2.**
- *Effort:* ~3–4 attention-weeks; local. **Sum 5 → PROMOTE (cheapest near-term win).**

### Track B — Bold, method-led (signature-method ports)

**B1 · Seismicity memory depth — the Markov ladder on earthquake catalogs**
- *New question:* at what Markov order *k\** does the loop/cluster topology of a regional earthquake sequence
  become indistinguishable from a *k*-th-order memoryless surrogate? ETAS tests fit to a fixed kernel and cannot
  produce a graded memory-order answer.
- *Construction:* hypocenters in the Baiesi–Paczuski rescaled space-time-magnitude metric (the field's own
  nearest-neighbour metric); VR/sublevel filtration; the ladder battery.
- *Feature → claim:* H1 (quiescence-then-reactivation loops) + the region-comparable number *k\**.
- *Baseline:* ETAS (Ogata 1988); Baiesi–Paczuski (2004) NN clustering.
- *Gate:* **PASS** — H0 risks reducing to NN cluster counts, so H1 and *k\** carry the novelty.
- *Data:* USGS ComCat (API); SCEDC (AWS Open Data); JMA. **Axis-2 = 3.** *Novelty (corrected — CONFIRMED, strengthened):*
  the one claimed near-miss (arXiv 2509.14661) turned out to be a **false cognate** (neural forecasting with a Markov
  baseline, *no TDA*); four query angles found no PH-on-catalog-with-permutation-nulls. **Axis-3 = 3.**
- *Effort:* ~3–4 attention-weeks; local. Domain risk moderate (completeness cutoffs, declustering — co-validate
  vs a published ETAS fit). **Sum 6 → PROMOTE (recommended flagship Track-B bet — the cleanest, best-verified bold gap).**

**B2 · Ecological community-assembly memory — the Markov ladder on BioTIME**
- *New question:* does community-composition trajectory show H1 reassembly loops exceeding a *k*-th-order Markov
  null — is reassembly path-dependent beyond order *k*, against neutral theory's memoryless prediction?
- *Construction:* yearly composition vectors, CLR/Aitchison-transformed (the field's compositional geometry); VR
  on the trajectory; the ladder. Structurally *identical* to the trajectory_tda pipeline (site ↔ individual).
- *Feature → claim:* H1 loops = cyclic succession/reassembly; memory-depth *k\** years.
- *Baseline:* neutral-theory nulls; Bray-Curtis turnover trend (Dornelas 2014). H1-loop claim must beat
  wavelet/Fourier cyclicity.
- *Gate:* **PASS** — near-direct reuse of TDL's own machinery.
- *Data:* BioTIME (CC-BY); LTER; GBIF. **Axis-2 = 3.** *Novelty (corrected — WEAKENED to 2):* no PH-on-BioTIME with
  the ladder framing, but the closest prior (arXiv 2209.08974, zigzag on coral reefs) has an **empirical arm** (not
  simulation-only, as first stated) — a partial precedent for "TDA + real ecological time-evolving data". **Axis-3 = 2.**
- *Effort:* ~2–3 attention-weeks; light. Domain risk **high** (neutral-theory / Bray-Curtis conventions are an
  opinionated subfield — real rejection risk for a solo TDA researcher). **Sum 5 → PROMOTE (cheapest bold win — natural pilot).**

**B3 · Paleoclimate abrupt-transition memory — the Markov ladder on Dansgaard–Oeschger events · USER-DECISION (third slot)**
- *New question:* does the δ¹⁸O proxy trajectory show H1 recurrence around a bistable attractor requiring Markov
  order > 0 — adjudicating the live "internal memory vs purely-stochastic forcing" disagreement (arXiv 2502.08460
  argues *for* memoryless forcing)?
- *Baseline:* the stochastic-forcing model; early-warning-signal indicators (critical slowing down).
- *Gate:* **PASS**, conditionally. *Data:* NOAA Paleo (NGRIP/GRIP/GISP2), PaleoJump, PAGES2k — open. **Axis-2 = 3, Axis-3 = 3.**
- **Why User-decision, not committed:** highest domain-knowledge risk on the scan (dating uncertainty, irregular
  sampling, contested proxies), plus small-N limiting permutation power. **Recommendation:** take only descoped
  (EWS-baseline first, topology second, publish only if it adds detection power) and ideally with a paleoclimate
  sanity-checker — **or** hold the slot. *(The weather-regime alternate is now OFF the table: the corrected search
  found a missed foundational paper — Strommen, Chantry, Dorrington & Otter 2023, arXiv 2104.03196 — making PH-on-
  reanalysis-weather-regimes a 3+ paper lineage; corrected novelty 1/3. See §(g).) New third-slot options that
  replaced it: the two vacated Track-B kills (neuroscience-zigzag, animal-movement-PH — reopened, novelty not yet
  re-searched) and the top gap-fill **GDELT conflict-event Markov ladder** (open data, clean HMM baseline, high
  political-science domain risk).*

### Track C — Frontier mathematics (persistent-Laplacian anchored)

**C1 · Persistent-Laplacian non-harmonic spectrum on the BHPS/USoc transition graph (+ weighted-PL Markov-ladder robustness rider)**
- *Machinery:* single-parameter persistent (combinatorial) Laplacian — [PETLS](https://arxiv.org/abs/2508.11560)-class software.
- *New question:* single-parameter PH tells you *when* a cycle is born/dies; the PL's **non-harmonic eigenvalues**
  ask a genuinely geometric question at the same filtration steps — how rigid/redundant are the pathways around a
  persisting feature? Can two cohorts have *indistinguishable H1 barcodes* (as P01 already checks) yet
  *distinguishable* pathway rigidity?
- *Feature → claim:* the smallest non-zero eigenvalue trajectory (persistent Fiedler value); a cohort shift in it,
  holding the diagram fixed, is direct evidence of a rigidity change PH structurally cannot detect (persistent
  Hodge theorem: ker(∆_q) ≅ H_q exactly, non-harmonic part provably orthogonal).
- *Additivity:* **genuinely additive** (a proven theorem). **Gate-1 at spike (mandatory):** correlate the
  non-harmonic eigenvalue trajectory against existing scalar summaries (persistence entropy, total persistence,
  landscape-L² norm) — if ≈1, it reframes rather than adds → KILL.
- *Data:* reuses the frozen P01 embedding. **Axis-2 = 3.** *Novelty (corrected — CONFIRMED, strengthened):* five
  independent searches found **no persistent-Laplacian application to social/panel/socioeconomic data** (field is
  overwhelmingly biomolecular/materials/viral) — total gap; TDL first. **Axis-3 = 3.**
- *Buildability (corrected):* PETLS is working software supporting **simplicial / alpha / directed-flag / Dowker /
  sheaf** complexes (*not* cubical — correct the earlier note), benchmarked at ~209 vertices / up to ~4,000 simplices
  — *higher* than the "30–500 vertices" first stated, which **strengthens** buildability since TDL's employment-state
  transition graph is far smaller (~9 states). This is exactly the backlog 4-gate PL spike
  (`t128-spike-4-persistent-laplacians`). The **weighted-PL Markov-ladder robustness check** shares the same core
  computation — bundle it as a rider, framed as methods hardening for P01-B, not new discovery.
- *Effort:* ~2–3 attention-weeks; local. **Sum 6 → PROMOTE (Track-C flagship).**

**C2 · Sheaf-consistency on the household/neighbourhood relational graph**
- *Machinery:* cellular sheaves / sheaf Laplacians (non-neural, Robinson-style — scipy/networkx, *not* torch-geometric).
- *New question:* are there household/neighbourhood clusters where individual trajectories are locally coherent
  yet globally anomalous — a relational-inconsistency signature W2/landscape methods (which discard the graph)
  cannot see?
- *Feature → claim:* non-trivial sheaf cohomology H¹ (obstruction to extending local consistency to a global
  section) in a specific neighbourhood cluster.
- *Baseline:* ordinary graph-Laplacian spectral clustering.
- *Additivity:* **genuinely additive** (sheaves generalise the coefficient system, not the filtration). **Load-bearing
  risk:** naive restriction maps degenerate the sheaf Laplacian to the graph Laplacian → the restriction-map design
  must be **pre-registered**, not discovered post hoc.
- *Data:* household/neighbourhood IDs + employment/income vectors (held); relational graph is new engineering. **Axis-2 = 2.**
- *Novelty (corrected — WEAKENED):* the broad "no sheaf on real social-network data" claim is **false** — Wolf & Monod
  2023 (arXiv 2310.05767) is the first sheaf implementation on real social-network data (Zachary karate club). The
  **narrower gap survives**: no sheaf application to household/neighbourhood *survey-panel* data using H¹ as an
  inconsistency diagnostic at BHPS/USoc scale. Must cite and distinguish Wolf & Monod, and engage "the illusion of
  households as entities in social networks" (arXiv 2502.14764) on household-node hazards. **Axis-3 = 2 (was 3).**
- *Effort:* ~3–4 attention-weeks; local. **Sum 4 → PROMOTE (lower priority), gated on a restriction-map pre-registration
  and an explicit distinction from Wolf & Monod.**

**C3 (watch, not a bet) · Multiparameter persistent Laplacian on the P04 bifiltration**
- Held as **WATCH-not-build:** the object is listed as *unsolved future work* in the Wei survey — no published
  algorithm, no stability theorem, no software (PETLS is single-parameter). Building it means new mathematics
  before any empirical claim, and it risks reducing to P04's existing Hilbert function (a live Möbius-inversion
  relationship in P04's own draft). Track via Scout (watch Wang 2026 and follow-ups). **Quiver-theoretic
  decomposition** was investigated and **killed** — `multipers`' signed measure is already the practical proxy.

---

## (c) Recommended portfolio + sequencing (6–18 months)

**Months 0–6 — near wins + cheap probes:** A3 (NHS GP deserts) + A2 (intergenerational, after a sample-size Assay
gate); B2 (ecology/BioTIME) as the Track-B pilot; C1 (PL non-harmonic spectrum) via the backlog 4-gate spike,
gate-1 = the additivity correlation check; TTK re-establishment (delegated, §(d)) up front since Track A leans on it.

**Months 6–12 — methods-forward + field-defining bets:** A1 (MCbiF deprivation) once TTK's live threshold slider
shortens its dominant cost (parameter search); commit **one** field-defining Track-B result (B1 seismology, or
scale B2 to a paper — not both); C2 (sheaf-consistency) only if C1 clears its additivity gate and a restriction-map
pre-reg is filed.

**Months 12–18 — consolidate + decide:** turn the strongest 1–2 into full papers (`/paper-repo-extract` for
submission); nominate the **ARS Phase-F greenfield pilot** (the first paper initiated after the two APM papers —
A3 or A2 for clean R0/R1 provenance; User-decision); run the three-tracks-to-two narrowing review.

The tracks are near-independent by design — no candidate blocks another, so parallel agent dispatch is safe.
A1 benefits from live TTK; C2 depends on C1's additivity result; B1/B2 are substitutable for the one bold slot.

---

## (d) Operating engines

### Scout
- **Fold the expanded seed into the funnel.** Add the three literature sources (`_NEW-2024-2026-Literature-Review.md`,
  the Literature Notes, the Perplexity captures) to `scout/watchlist.yaml` → `dedup.against`, promote still-live
  candidates into `_backlog.md`, and label Perplexity captures `lead_only`. Triage the **untriaged W26 inbox** first.
- **Watchlist additions per committed direction:** *A* — "multicover bifiltration", "topological autocorrelation",
  "floating catchment area", "healthcare access topology", "intergenerational mobility topology". *B* (only if the
  bold bet is committed — Track B is a deliberate Scout blind spot today) — "earthquake catalog persistent homology",
  "ETAS Markov order"; "community assembly topology", "compositional data TDA". *C* — "persistent Laplacian",
  "PETLS", "non-harmonic spectrum", "cellular sheaf", "sheaf Laplacian", "multiparameter persistent Laplacian";
  authors Wei, Botnan, Monod, Wang.
- **Feedback:** the finance kill (§(e)) and any `[NEGATIVE]` spike results re-seed the watchlist.

### Live TTK / ParaView — audit finding
| Track | TTK verdict | Why |
|---|---|---|
| **A** | **TTK-ENHANCED** (some near-critical) | A1/A3 use level-set/coverage filtrations where TTK's persistence-diagram + Morse-Smale filters apply; A2 uses a Mapper companion. The live merge-tree / threshold slider attacks the *parameter-search* cost that dominates these directions. |
| **B** | **TTK-IRRELEVANT** | Point-process (seismicity) and delay-embedded point-cloud (ecology, paleoclimate) PH; ripser/gudhi suffice. |
| **C** | **TTK-IRRELEVANT to computation** | TTK computes neither PL nor sheaves; at most a Morse-Smale/Mapper visual cross-check against GMM regime boundaries. |

**Honest conclusion:** live TTK is load-bearing chiefly in **Track A and the existing poverty_tda / Morse-Smale
line**, not across the portfolio. That still justifies re-establishing it (Track A is the largest allocation; P04
depends on it; the fix is cheap and delegable) but it should not be oversold as pan-portfolio infrastructure.

**Note on TTK state (harvested from the alternative pass):** the US-public pass reported a *more specific verified
finding* than this pass first assumed — that core TTK 1.3.0 computation works through the isolated `ttk_env`, but
**live TTK filters inside ParaView do not**, and a bottleneck-distance smoke test currently *false-passes* after VTK
input errors (project W2 remains authoritative). That corroborates the "verify first, don't assume the docs" stance
below and sharpens the acceptance gate (VTK errors must fail tests).

### Delegated work item — TTK re-establishment (implementation agent; do **not** solve in strategy)
- **Verify first, don't assume:** run `python shared/ttk_utils.py` and `pytest tests/shared/test_ttk_utils.py`; the
  conda-subprocess design (`ttk_env` py3.11 / TTK 1.3.0, isolated from the locked 3.13 venv) may still compute.
- **Probe separately:** core TTK, `pvpython`, and ParaView plugin filters are distinct — one working does not imply
  the others. Make VTK input errors **fail** tests and assert numerical invariants (the current false-pass is the
  bug to close), or mark a filter unsupported.
- **If broken:** recreate `ttk_env` per `docs/TTK_SETUP.md` §1–3; re-verify detection from the 3.13 venv;
  **document the effective 3.13-conflict workaround** (the piece the stale docs miss).
- **Acceptance gate:** a Morse-Smale extraction end-to-end on a small cached poverty_tda mobility field returns
  critical points, with state/screenshots/checksum/commands recorded; one reusable `.pvsm` template so mid-analysis
  viewing is one command (stretch); `docs/TTK_SETUP.md` updated to current truth.
- **Hard constraint:** do **not** alter the locked 3.13 venv or its pins, begin an unbounded source build, or weaken
  isolation — stop and escalate instead. Branch `pipe/ttk-reestablish`; commit env recipe + tests + doc update;
  do not merge; `[PIPELINE]` vault entry.

---

## (e) Risks, park/kill criteria, User-decision points

### Park/kill criteria (enforce at Assay/Spike)
- **A1:** KILL if it reduces to spatial autocorrelation (Moran's I / ARI-across-resolutions) rather than a
  fragmentation-across-scale claim MCbiF alone can make.
- **A2:** PARK if household-linked parent–child pairs with adequate two-sided overlap fall below the point-density
  PH needs (a real risk at low thousands — a hard Assay gate).
- **A3:** KILL if PH and 2SFCA never materially disagree.
- **B1/B2:** KILL if the loop claim reduces to existing clustering (seismic NN clusters) or cyclicity tests
  (ecological wavelet/Fourier) — H0 alone is insufficient; the loop structure and *k\** must carry it.
- **B3:** default PARK/descope unless a paleoclimate sanity-check is available.
- **C1:** KILL at gate-1 if the non-harmonic spectrum correlates ≈1 with existing scalar summaries. **C2:** KILL if
  the restriction-map design degenerates to the ordinary graph Laplacian.
- **C3:** remains WATCH until a computable multiparameter-PL algorithm with a stability result exists.

### Standing risks
- **Finance pre-emption (verified):** [arXiv 2602.00383](https://arxiv.org/abs/2602.00383) (Akingbade, Jan 2026)
  already does null-validated topological finance (persistence-landscape L¹ on Bitcoin, shuffle + phase-randomized
  surrogate nulls). This kills *bold new* finance directions and means **FIN-01's "first to null-validate" framing
  needs softening** (FIN-01 is differentiated by metric and target, but recheck before submission).
- **Track B domain-knowledge risk:** the bold bet's credibility depends on field conventions (seismic
  completeness/declustering; ecological null models; paleoclimate dating). Budget domain-grounding attention;
  co-validate against a published in-field baseline before claiming a topological result.
- **Attention over-commit:** nine directions is more than a solo researcher can carry — sequencing commits *one*
  bold bet and *one* Track-C flagship; resist widening.
- **Track C reframe risk:** persistent Laplacians sit next to two programme strengths (PL + multiparameter) — the
  C3 watch exists to stop "combine them" becoming novelty-for-its-own-sake (the T-STRAND-1 "concordance ≠
  additivity" lesson).

### Settled (recorded 2026-07-03)
- **Canonical variant + data-access definition (was UD-1 / UD-7).** UK-open pass is canonical; UK Data Service
  EUL/Safeguarded registered access counts as in-bounds (Stephen holds it), so UK microdata at that level is a
  usable moat, not a constraint. Only Secure-Lab / special-licence / controlled data is out. The alternative
  pass's additive ideas are folded in (§(f)).

### Explicit User-decision points (open)
1. **Ratify the 50/30/20 attention split** or adjust the near-vs-bold emphasis.
2. **Third Track-B slot (options changed by the re-roam)** — weather-regime is now OUT (corrected novelty 1/3,
   crowded). Remaining options: B3 paleoclimate descoped (with a sanity-checker); B2 ecology promoted to the slot;
   the top gap-fill **GDELT conflict-event Markov ladder** (open data, clean HMM baseline, high political-science
   domain risk); or one of the **two reopened kills** (neuroscience-zigzag / animal-movement-PH — see UD-6).
   *Recommendation: hold the slot empty initially; commit B1 (seismology) as the single bold flagship — it is now the
   cleanest, best-verified bold gap.*
3. **ARS greenfield-pilot nominee** (recommend A3 or A2 for clean R0/R1 provenance).
4. **FIN-01 positioning** given the 2602.00383 pre-emption (confirmed: L¹-landscape + shuffle/phase-randomized
   surrogates — small deltas from the house style, but "null-validated topological finance" as a category is pre-empted).
5. **Legacy slate:** formally **supersede P05** as scoped (its SOEP/PSID/CNEF data are non-UK, not reachable via the
   UK Data Service — reframe around open cross-national panels or park) and **absorb P06 into A2**; keep P07–P10 parked
   as future optionality.
6. **Reopen the two vacated Track-B kills?** The corrected search found the citations that killed
   **neuroscience-zigzag** (arXiv 2603.03037 is calcium imaging, not spike-trains) and **animal-movement-PH**
   (arXiv 2406.15195 has no topology at all) were false matches from the broken index. Their novelty was never
   re-searched — decide whether to spend a roam re-assessing either as a live Track-B candidate.
7. **MCbiF cross-track efficiency** — MCbiF (arXiv 2510.14710) is both Track A's A1 (deprivation, spatial) *and* a
   strong Track-C candidate (employment-state clustering consistency across BHPS/USoc waves, temporal-methods). One
   bifiltration-reimplementation investment yields two papers across two tracks. Decide whether to prioritise MCbiF
   as the shared early build (possibly ahead of, or alongside, C1 as the first frontier-maths output).

---

## (f) Reconciliation — what was harvested from the alternative (US-public) pass

This canonical file is the UK-open pass. The alternative pass (US public data + AI-weather-forecast bold bet) is
superseded, but three of its ideas were genuinely additive and are folded in:

1. **Temporal segregation/deprivation morphology (harvested as a new Track-A candidate, A4 below).** The alternative
   pass's strongest distinct idea was *change over time* — cities with similar scalar-index change can have different
   enclave-fragmentation topology. The UK-open A1 measures fragmentation across *scale*; this measures it across
   *time*, which is a different, publishable object. UK-ified: harmonised cubical persistence on **Census 2011 → 2021**
   ethnic-group / deprivation surfaces (or IMD 2015 → 2019 → 2025), baseline-matched against the dissimilarity/isolation
   indices and Getis-Ord, testing whether topological enclave change separates cities matched on conventional indices.
   Data: ONS Census 2011/2021 counts + cross-census harmonisation lookups + TIGER-equivalent OS boundaries — all
   OGL/open. Preliminary Axis-2 = 3, Axis-3 = 2 (Friesen/Kauba established the static US version; the *temporal, matched*
   framing on UK data is the contribution). **Needs its own Assay pass** (shallow — harvested, not yet gap-searched).
2. **Directed-network persistent-path H1 (noted, lighter).** The alternative pass's disaster-conditioned
   *migration-network* anchor used directed persistent paths (H1 as directed circulation/return structure) that ordinary
   undirected PH cannot recover — an elegant construction. Its cleanest UK home is the commuting-flow zigzag gap-fill in
   §(g) (ONS Census origin-destination); if that is promoted, borrow the directed-path-H1 framing rather than treating
   it as a separate candidate.
3. **Pre-spike dataset-provenance discipline (harvested into the kill/assurance rules).** Before any spike, record
   dataset ID, query, release/version, licence, coverage, transformations, missingness, local artifact path, and use
   class — so a spike's data foundation is auditable. Added to the Assay/Spike expectations below.

The alternative pass's **precise TTK finding** (core TTK computes in isolation, live ParaView filters do not, one smoke
test false-passes on VTK errors) is already carried in §(d).

**A4 · Changing segregation/deprivation morphology over time (harvested — UK Census cubical persistence)** — *New
question:* do UK cities with similar *scalar* segregation/deprivation change (2011→2021) show different *topological*
enclave fragmentation/consolidation? *Baseline:* dissimilarity & isolation indices, Moran's I / LISA, Getis-Ord. *Gate:*
PASS only if topology separates cities matched on conventional indices and composition. *Data:* ONS Census 2011/2021,
harmonisation lookups, OS boundaries (OGL). *Risk:* crosswalk sensitivity across census geographies dominating the
signal — a hard Assay check. **Axis-2 = 3, Axis-3 = 2; PROMOTE-candidate pending its own Assay** (distinct from A1's
across-scale claim).

---

## (g) Re-roam verification pass (2026-07-03) — correction log with provenance

The first frontier roam used a mismatched search index (a Wiley `semanticSearch` gateway that returned off-query
results — e.g. multiparameter-persistence papers when queried for persistent Laplacians). A corrected re-roam ran
with that tool **disabled**, WebSearch/WebFetch/alphaXiv **named**, **no nested sub-agents** (the file↔task pairing
that scrambled), **every citation fetched and confirmed** against `arxiv.org/abs/<id>`, and **every "no prior work"
claim required to record its query**. What changed:

| Item | First pass | Corrected verdict | Provenance |
|---|---|---|---|
| **B1 seismology** | novelty 3/3, one "near-miss" | **CONFIRMED, strengthened** — the near-miss (2509.14661) is a *false cognate* (neural forecasting + Markov baseline, no TDA); 4 query angles clean | direct fetch + 4 recorded queries |
| **B2 ecology** | novelty 3/3, "simulation-only" precedent | **WEAKENED to 2/3** — 2209.08974 has an *empirical* arm (partial precedent); domain risk raised to high | full-text fetch of 2209.08974 |
| **B3 paleoclimate** | 3/3 | **CONFIRMED 3/3** (strongest original); baseline 2502.08460 confirmed | 3 recorded queries |
| **Weather-regime alternate** | "crowded, 2 competitors" | **KILLED — novelty 1/3** — missed **foundational** paper Strommen, Chantry, Dorrington & Otter 2023 (arXiv 2104.03196); it is a 3+ paper lineage; 2602.09004 uses ERA20C + Gaussian null (not ERA5 + Markov ladder) | full-text fetch + citation trace |
| **Finance kill** | killed | **CONFIRMED killed** — 2602.00383 = L¹-landscape + shuffle/phase-randomized surrogates | direct fetch |
| **Neuroscience kill (2603.03037)** | killed as "zigzag on spike-trains" | **KILL VACATED** — paper is *calcium imaging (Sensorium 2023), not spike-trains*; the killing citation was a false match → reopen (novelty not re-searched) | direct fetch |
| **Animal-movement kill (2406.15195)** | killed as "movement PH prior art" | **KILL VACATED** — "persistent dynamics" = autocorrelated Langevin params, *no topology at all* → reopen | direct fetch |
| **C1 persistent Laplacian** | novelty 3/3; "PETLS simplicial/cubical/digraph, 30–500 vertices" | **CONFIRMED, strengthened** — 5 clean searches; PETLS supports simplicial/alpha/**directed-flag/Dowker/sheaf** (*not* cubical); benchmarks ~209 vertices / ~4,000 simplices (higher → better buildability) | 5 recorded queries + PETLS/survey full-text |
| **C2 sheaf-consistency** | novelty 3/3, "no sheaf on social data" | **WEAKENED to 2/3** — Wolf & Monod 2023 (arXiv 2310.05767) is the *first sheaf on real social-network data*; only the narrower survey-panel/H¹-diagnostic gap survives; must cite + distinguish, and engage 2502.14764 on household-node hazards | full-text fetch of 2310.05767 |
| **C3 multiparameter PL** | WATCH; cite Wang 2026 (2602.14846) | **WATCH confirmed** — 2602.14846 is *image-analysis PSL spectrum-aggregation across PCA dims, NOT a true bifiltration*; no computable multiparameter PL with a stability theorem exists | full-text read |
| **Quiver kill** | killed | **CONFIRMED killed** — multiparameter modules are wild rep type; multipers/MMA (2206.02026, JOSS 2024) already approximates it | primary-source confirmation |

**New candidates surfaced by the corrected search** (each shallow — needs a dedicated Assay pass): Track A —
**commuting-flow zigzag persistence** on ONS Census O-D (post-COVID catchment shift; zigzag-temporal-networks
precedent arXiv 2205.11338) and **school-catchment coverage topology** (GIAS + travel-time VR). Track B — **GDELT
conflict-event Markov ladder** (top; zero PH+GDELT hits; HMM baseline; high domain risk) and **exoplanet transit
light-curve Markov ladder** (open; higher domain risk). Track C — **MCbiF on wave-by-wave employment-state
clusterings** (arXiv 2510.14710 is finitely-presented + *block-decomposable* → dodges the wild-type problem; may be
a stronger *first* frontier-maths paper than C1, and shares its build with Track A's A1).

**Minor citation corrections for any future write-up:** MCbiF authors are **Schindler & Barahona** (2, ICLR 2026),
not "Schindler et al."; **IMD 2025** (Oct 2025) is the live edition superseding IMD 2019; Hickok (2206.04834) uses a
**weighted Vietoris–Rips**, not a witness complex (witness = O'Neil & Tymochko 2410.09067); D'Acunto & Battiloro's
paper is titled **"The Relativity of Causal Knowledge"** (2503.11718). A UK near-miss to cite in A3 is **Corcoran &
Jones 2023 (IJGIS)** — PH on UK pub point-patterns/rainfall (method-adjacent, does not kill the NHS-access gap).

**Residual under-verified claims (flagged honestly):** A2's "no intergenerational-mobility TDA" gap never got an
isolated dedicated query; the weather-regime space had no forward-citation ("cited by") sweep so may be *more*
crowded still; C2 was weakened by one confirmed counter-example but not exhaustively surveyed; the two reopened
Track-B kills have had *no* novelty search. All of these are Assay-stage tasks before any dispatch.

---

## Self-critique

Three honest weaknesses. **First, the scorecards are previews, not `/assay` runs** — Axis-2/3 rest on named open
datasets verified for existence and licence but not exhaustively probed for the *structure a permutation null needs*
(A2's pair-count is the sharpest, deliberately scored 2 and gated). **Second, Track B's novelty scores lean on
absence-of-evidence** — "no PH-on-catalog-with-nulls found" is a bounded search, not a proof of gap; the bold bet
needs one more in-field literature pass before dispatch (the finance kill shows how fast a gate closes). **Third,
the persistent-Laplacian flagship (C1) is the most attractive-sounding Track-C bet and also the one whose additivity
is genuinely uncertain** — the whole case rests on gate-1, exactly the "concordance ≠ additivity" trap the programme
was burned by in T-STRAND-1. It is sequenced cheap-and-first so a KILL there costs days, not months, and should not
be presented internally as more than a probe until gate-1 passes.
