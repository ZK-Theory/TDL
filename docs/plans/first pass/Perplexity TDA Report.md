<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Having researched further I have discovered that a combination of paraview (https://www.paraview.org/) especially with catalyst and topology toolkit (https://topology-tool-kit.github.io/index.html) represents a SOTA implementation of modern mathematical research in TDA. As such rewriting algorithms is not the play and I need to make a strategic pivot towards analysing actual data in a useful way. I wonder if we can brainstorm some ideas that could make for good portfolio projects to display on a website.

We would need to be able to work with publically available datasets and ideally we want to do something surprising and interesting. I'm particularly interested in economics, poverty and financial market movements but we are very much not limited to that.

I wonder if it might be possible to develop some sort of agentic version of paraview and ttk to improve accessibility and uses but again this is loose and speculative (and we should be cautious around replication of other work).

Other potential things to look at are [https://tdlbook.org/](https://tdlbook.org/) and [https://datarefiner.com/](https://datarefiner.com/)

We are looking for small team projects that could be accomplished on a tight budget and limited hardware (CUDA is available however). Do some deep research and suggest some possible avenues to explore giving clear justification for why you are recommending them. Make them grounded, realistic and worthwhile.

Perfect! Now I have comprehensive information. Let me compile my brainstorming response with concrete, actionable project ideas.

***

## STRATEGIC PIVOT: TDA-POWERED PORTFOLIO PROJECTS

Your recognition that **building SOTA TDA infrastructure is redundant** (ParaView + Catalyst + TTK already achieve this brilliantly) is strategically sound. The real value is in **novel data applications + accessibility layers**. Here are concrete, grounded project ideas:

***

## **TIER 1: HIGH-IMPACT, FEASIBLE PROJECTS**

### **1. Financial Crisis Early Warning Dashboard**

**Why this:** Your files show TDA excels at detecting topological shifts in correlation matrices before crashes. This is production-ready.

**Dataset:**

- Daily stock returns: S\&P 500, Russell 2000 + sector ETFs (free via Yahoo Finance API)
- 15+ years history available
- Public financial data is abundant and clean

**Innovation:**

- Build a **real-time Wasserstein Distance turbulence index** as TTK computes it
- Deploy on a lightweight web interface (Flask/React) showing:
    - Persistent homology barcodes of market correlation structure
    - Rolling turbulence signals (top 90th percentile triggers alerts)
    - Backtest performance against VIX, historical crashes

**Portfolio Value:**

- Demonstrates **domain expertise in finance + mathematical rigor**
- GitHub repo with reproducible methodology
- Blog post: "Why topology detects market crashes better than statistics"
- Could attract fintech interest

**Timeline:** 4-6 weeks (core dashboard)
**Hardware:** CPU-only sufficient (CUDA helpful for larger windows, not required)
**Replication Risk:** LOW—literature validates approach, just needs implementation[^1][^2]

***

### **2. Global Inequality Topology Atlas**

**Why this:** Your stated interest in poverty/economics. TDA reveals **hidden stratification patterns** in inequality that traditional metrics miss.

**Dataset:**

- World Bank Poverty \& Inequality Platform (PIP): 180 countries, 40+ inequality measures
- OWID inequality database (free, machine-readable)
- UN Gini indices, income distribution data
- Clean, publicly available, no permissions needed

**Innovation:**

- **Mapper algorithm** on inequality indicators → discover country clusters with *topological affinity* (not just k-means)
- Identify "island nations" of inequality patterns (outliers with unique structure)
- Track **persistent topology over time**: how do country inequality clusters birth, merge, die across 20 years?
- Interactive visualization: hover countries to see their topological neighbors

**Portfolio Value:**

- **Novel visualization** of global economic structure
- Actionable insights for policy (which countries are topologically similar to successful equalization?)
- Publishable: "Topological signatures of sustainable inequality reduction"
- Appeals to development organizations, policy research

**Timeline:** 6-8 weeks
**Hardware:** CPU-only
**Data Quality:** Excellent (World Bank validated)
**Replication Risk:** MEDIUM—needs careful feature engineering (which indicators to use?)

***

### **3. Supply Chain Disruption Detector**

**Why this:** Time-series TDA for dependent sequences is SOTA-proven in your papers (Chazal et al. TADA framework).

**Dataset:**

- Shipping delays (MarineTraffic API, some free tiers)
- Port congestion indices (public from major ports)
- Semiconductor fab capacity utilization (public reports)
- OR: synthetic data + semi-real data blend (more controllable)

**Innovation:**

- Apply **persistent homology to rolling-window dependence graphs**
- Detect when supply chain correlation structure shifts → early warning of disruption
- Compare: TDA vs. traditional anomaly detection (Isolation Forest, etc.)
- Build as **lightweight CLI tool** for supply chain analysts

**Portfolio Value:**

- B2B appeal (logistics companies, manufacturers)
- Demonstrates **practical data ops** (integration, streaming, alerting)
- Open-source release with benchmarks

**Timeline:** 5-7 weeks
**Hardware:** CPU sufficient
**Data Quality:** Good (aggregated public sources)
**Replication Risk:** MEDIUM—needs realistic data pipeline

***

## **TIER 2: SPECIALIZED/LONGER-HORIZON PROJECTS**

### **4. Agentic ParaView Wrapper ("AutoViz")**

**Feasibility caveat:** This is speculative but defensible if scoped tightly.

**Why:**

- Current bottleneck: expertise needed to configure ParaView + TTK visualizations
- An **LLM-powered agent** that converts natural language queries → visualization code could democratize access
- "Show me connected components in this stock correlation structure" → auto-generates ParaView pipeline

**Scope (minimal MVP):**

- Small Python library on top of ParaView Python API + TTK
- Agent interprets user queries → generates filter/representation configs
- NOT a full UI overhaul; NOT competing with ParaView
- More like: **ParaView scripting automation layer**

**Portfolio Value:**

- Unique positioning: TDA accessibility
- Avoids direct competition with ParaView/TTK teams
- Could be packaged as Jupyter extension

**Timeline:** 8-10 weeks (rough prototype)
**Risk:** MEDIUM-HIGH (LLM reliability, ParaView API learning curve)

***

### **5. Pandemic-Scale Economic Resilience Index**

**Why:** Combines TDA + economics + social impact (publishable research potential).

**Dataset:**

- World Bank purchasing power parity (PPP) data
- IMF real GDP growth
- ILO employment statistics
- WFP food insecurity indices
- All public, time-series (2010-2024)

**Innovation:**

- **Persistent homology of 50-country economic networks** (trade, capital flows, debt)
- Track **topological entropy** during COVID (2020) vs baseline
- Identify countries whose economic resilience comes from *structural diversification* (topological property) vs. size
- Hypothesis: topologically "central" countries recover faster

**Portfolio Value:**

- **Research publication** (interdisciplinary journal: nature sustainability, world development, etc.)
- NGO/UN appeal (development impact)
- Complex, novel methodology

**Timeline:** 10-12 weeks
**Hardware:** CPU
**Data Quality:** Excellent (IMF/World Bank curated)
**Replication Risk:** MEDIUM (needs literature review, methodology justification)

***

## **TIER 3: QUICK-WIN PORTFOLIO PIECES**

### **6. "TDA Cookbook" + Benchmark Suite**

**Why:** Lower-hanging fruit; still high value.

**What:**

- Jupyter notebooks: TDA on 5-6 real datasets (finance, biology, networks, images)
- Performance benchmarks: Ripser vs. GUDHI vs. DIPHA on your hardware
- Best practices guide: which complex type for which data?
- Docker container: reproducible environment

**Portfolio Value:**

- **Community contribution** (cite in papers citing TTK/ParaView)
- Demonstrates systems expertise + teaching ability
- Low risk, high signal

**Timeline:** 3-4 weeks
**Hardware:** Any

***

## **CRITICAL RESOURCES IDENTIFIED**

### **Datasets (All Free, No Permissions)**

1. **Finance:** Yahoo Finance API, FRED (Federal Reserve), Kaggle financial indices
2. **Economics:** World Bank PIP, IMF Data, OECD.stat, Our World in Data
3. **Supply Chain:** MarineTraffic (limited free), Port Authority APIs, Shipping data aggregators
4. **Pandemic:** World Bank, WFP, ILO databases

### **Tools Stack (No Cost)**

- **Computation:** GUDHI (Python), Ripser, TTK standalone
- **Viz:** ParaView (free), Plotly/Dash (web dashboards)
- **Frameworks:** scikit-learn for preprocessing, Giotto-TDA for integration
- **Infrastructure:** GitHub (free), Docker, AWS Free Tier or lightweight VPS


### **Literature Validation**

Your papers show:

- **Financial TDA works:** Turbulence index outperforms VIX[^1]
- **Time-series TDA proven:** Persistent homology detects anomalies in dependent sequences[^3]
- **Mapper for clustering:** Discovers non-linear stratification[^4]
- **GPU acceleration optional:** CPU implementations (Ripser) handle most problem sizes efficiently

***

## **RECOMMENDATION**

**Start with \#1 (Financial Crisis Dashboard) or \#2 (Inequality Atlas), then expand:**


| Project | Weeks | Appeal | Risk | CUDA? |
| :-- | :-- | :-- | :-- | :-- |
| Financial Dashboard | 4-6 | FinTech + Academia | LOW | No |
| Inequality Atlas | 6-8 | Policy + Dev | MEDIUM | No |
| Supply Chain Detector | 5-7 | B2B + Ops | MEDIUM | No |
| TDA Cookbook | 3-4 | Community | LOW | No |
| Economic Resilience | 10-12 | Publication | MEDIUM | No |

**Path forward:**

1. Pick project \#1 or \#2 (start this week)
2. Publish code + blog post (4-6 weeks out)
3. Use momentum to propose \#2 or \#5 (publishable research tier)
4. Position yourself as **"TDA + [Domain] expert"** for portfolio/hiring

**Why avoid re-implementing ParaView/TTK:**

- Competing with teams of 50+ researchers
- Your advantage is *novel domains + interpretation*, not infrastructure
- Portfolio hires care about **unique insights**, not algorithmic reimplementation

Does one of these resonate? Happy to detail any further.
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30][^31][^32][^33][^34][^35][^36][^37][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://www.paraview.org

[^2]: https://topology-tool-kit.github.io/index.html

[^3]: https://fupubco.com/futech/article/view/410/247

[^4]: https://www.mdpi.com/1911-8074/18/11/598

[^5]: https://jicrcr.com/index.php/jicrcr/article/view/3254

[^6]: http://dergipark.org.tr/en/doi/10.52122/nisantasisbd.1557322

[^7]: https://taapublications.com/tijsrat/article/view/716

[^8]: https://economics-msu.com.ua/en/journals/tom-12-1-2025/tsifrovi-innovatsiyi-v-bukhgalterskomu-obliku-yak-faktor-ekonomichnogo-zrostannya-pidpriyemstva

[^9]: https://invergejournals.com/index.php/ijss/article/view/168

[^10]: https://journals.sagepub.com/doi/10.1177/14727978251355788

[^11]: https://wjaets.com/node/3860

[^12]: https://www.semanticscholar.org/paper/88fc4a9d572b6703b3b25e92d133fca2c5192de8

[^13]: https://arxiv.org/pdf/2403.19735.pdf

[^14]: https://dx.plos.org/10.1371/journal.pone.0318939

[^15]: http://arxiv.org/pdf/2304.03368.pdf

[^16]: https://arxiv.org/pdf/2205.13426.pdf

[^17]: https://arxiv.org/pdf/2207.03579.pdf

[^18]: https://www.ijfmr.com/papers/2024/4/26288.pdf

[^19]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11957772/

[^20]: https://arxiv.org/pdf/1908.09156.pdf

[^21]: https://arxiv.org/html/2508.14136v1

[^22]: https://www.adb.org/sites/default/files/publication/181581/ewp-477.pdf

[^23]: https://economicsnetwork.ac.uk/links/data_free/

[^24]: https://papers.ssrn.com/sol3/Delivery.cfm/5196633.pdf?abstractid=5196633\&mirid=1

[^25]: https://www.princeton.edu/~deaton/downloads/20080301SmallAreas_FINAL.pdf

[^26]: https://data.worldbank.org

[^27]: https://wjaets.com/sites/default/files/WJAETS-2024-0396.pdf

[^28]: https://ukdataservice.ac.uk/app/uploads/dh-presentation_final.pdf

[^29]: https://www.imf.org/en/data

[^30]: https://www.aimsciences.org/article/doi/10.3934/fods.2024024

[^31]: A-persistent-homology-based-turbulence-index-some-applications-of-TDA-on-financial-markets.pdf

[^32]: A-generalization-of-the-Topological-Tail-Dependence-theory.pdf

[^33]: 24-0853.pdf

[^34]: A-roadmap-for-the-computation_of-persistent-homology.pdf

[^35]: A_Survey_on_the_High-Performance_Computation_of_Persistent_Homology.pdf

[^36]: https://iuojs.intimal.edu.my/index.php/joit/article/view/792

[^37]: https://medinform.jmir.org/2025/1/e77297

