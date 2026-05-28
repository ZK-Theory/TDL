# A Topology of Educational Outcome Inequality

**Authors:** Alexander Benites, Koichiro Hara, Piyush Singh, Ben Zubier, Simon Rudkin (corresponding)
**Affiliation:** School of Social Sciences, University of Manchester, UK
**Source:** SSRN paper 5401815
**Local PDF:** `ssrn-5401815.pdf` (in user's reading folder)

**Keywords:** Education inequality, topological data analysis, education policy, ball mapper, schooling levels
**JEL Codes:** I24, I28, C38

---

## Abstract

This paper examines educational inequality using the Education Gini Index alongside Topological Data Analysis Ball Mapper. A ward-level empirical case study of Greater Manchester and Merseyside identifies clear socio-demographic patterns beyond pure spatial differences. Wards with higher educational inequality are characterised by higher deprivation, larger young populations, and greater ethnic diversity. In contrast, low-inequality areas are more socioeconomically stable. Wards with differing levels of inequality are often geographic neighbours. This paper demonstrates how TDA Ball Mapper preserves complex, multidimensional relationships without dimensionality reduction, enabling the detection of distinct clusters of educational inequality across regions. The analysis highlights the need for targeted educational policies to address entrenched inequalities. The implementation casts light on the opportunities to implement such targeted policies.

---

## 1. Introduction

Educational inequality remains a persistent societal concern (Blanden et al., 2023). Inequality in educational attainment contributes heavily to broader socioeconomic disparities (Anders and Jerrim, 2017; Coady and Dizioli, 2017; Jackson et al., 2016). Conversely, socioeconomic disparities also contribute to educational inequality (Kiernan and Mensah, 2011; Crawford and Greaves, 2015). Therefore, inequitable educational attainment and poor socioeconomic conditions can be viewed as a positive feedback loop, where, without policy intervention, each amplifies the other over time (Blanden et al., 2022; Johnson and Jackson, 2019; Britton and Sibieta, 2024). This paper analyses educational inequality in the United Kingdom. The analysis combines traditional methods, like the Education Gini Index, with novel methods in Topological Data Analysis (henceforth TDA) to uncover spatial patterns in inequality.

Greater Manchester and Merseyside are taken as exemplars of city regions with diverse communities residing within. Both counties were formed in the local government changes of the 1970s, each taking from the ceremonial counties of Lancashire and Cheshire. Manchester and Liverpool now have metropolitan mayors with power to direct policy beyond that which may be found in many UK local authorities. Manchester and Liverpool, as the cities that make up the majority of the land areas of Greater Manchester and Merseyside respectively, are both known for their industrial past and for undergoing a renaissance in recent times. Whilst gentrification has brought new investment and residents to many inner-city areas of both cities, there remain highly deprived areas in both. More than 60% of wards in Liverpool are in the top 20% most deprived in the UK, making Liverpool the 4th most deprived local authority overall. Manchester fared slightly better, ranking 8th overall for deprivation. Other local authorities within the Greater Manchester and Merseyside regions were similarly deprived. This paper uses a case study of what is happening behind the regeneration successes of Merseyside and Greater Manchester to understand how the topology of data can inform policy and practice.

Understanding spatial distributions of educational inequalities is crucial for targeted, efficient policy interventions, and ultimately, in delivering equitable educational outcomes. This paper offers new insights into the complex and multidimensional nature of educational inequality in urban contexts, highlighting regional demographic, geographic, and socioeconomic features as key drivers of educational inequality. We use the Ball Mapper algorithm (BM) of Dłotko (2019) to map educational inequality across the demographic, geographic and socioeconomic factors. The BM method used in the analysis are effective in creating a holistic analysis of the myriad features contributing to, or mitigating the impact of, educational inequality. BM does not require dimensionality reduction, which traditional spatial analytical methods like clustering can do. Rather than seek to sub-divide the data into clusters in the style of K-means (Hartigan and Wong, 1979), BM is simply mapping the data. Clusters are areas within the map, rather than being computationally derived. Hence, using BM methods in this analysis allowed for the preservation of many unique features in the data. The analysis reveals distinct clusters of both low and high educational inequality linked to these features, making suggestions for targeted policy.

The contributions of this paper are threefold. Firstly, this paper positions educational inequality as linked to the full combination of factors, rather than as the additive result of each individual factor. Our mapping approach allows the data to speak unconstrained by the impositions of statistical models. Secondly, using a case study of Greater Manchester and Merseyside, we show that inequality in educational outcomes is driven by the interaction of factors. Our maps reveal areas of high and low inequality. Finally, the mapping generated by our approach gives policymakers the opportunity to identify strategies to both improve the position of areas with high educational inequality, and to help individual children move to areas with lower inequality. Examples of policies of both types are given.

The remainder of the paper is organised as follows. Section 2 presents the related literature on educational inequality. Section 3 provides the methodological approach, both the construction of educational inequality measures and the process of implementing the BM algorithm. Section 4 introduces the case study data from Greater Manchester and Merseyside. Section 5 provides the core BM analysis of the case study. Section 6 discusses the implications of the results, gives policy suggestions and concludes.

---

## 2. Literature Review

The benefits of education are well-documented, not only in relation to the role a skilled workforce plays in modern economies (Blanden, Doepke and Stuhler, 2022), but also in terms of their broader societal impact. For instance, laws enforcing compulsory schooling have been shown to reduce both child and adult mortality rates while improving key health indicators (Lleras-Muney, 2005; Lochner, 2011; Cutler and Lleras-Muney, 2010). Similarly, reducing educational gender disparities has been found to lower overall income inequality (Coady and Dizioli, 2018), enhance country-level economic performance (Klasen, 2002; Klasen & Lamanna, 2003; Baliamoune-Lutz and McGillivray, 2015), and alleviate poverty, particularly in rural areas (Chaudhry and Rashman, 2009). On a different level, better educational outcomes have also been linked to lower crime rates (Lochner and Moretti, 2004; Machin et al., 2011) and higher individual perceptions of quality of life (Powdthavee, Lekfuangfu and Wooden, 2014).

Based on this evidence, two main discussions have emerged. First, the different methodological approaches that can be employed to capture educational disparities across countries (OECD, 2016) and to identify variations within national boundaries (Thomas, Wang and Fan, 2001). Second, studies that explore the possible drivers of educational inequalities. Broadly speaking, and although inherently interrelated, three different levels of factors contributing to these disparities can be identified: (a) individual-level conditions (e.g., gender, ethnicity, and socioeconomic background); (b) intermediate-level conditions (e.g., levels of educational investment, teacher effectiveness, and school resources); and (c) macro-level conditions (e.g., state territorial presence, geography, market incentives, and cultural factors).

### 2.1 Individual and Family-Level Determinants of Educational Inequality

At the most fundamental level, individual and family socioeconomic factors are central in explaining disparities in educational outcomes (Jencks et al., 1972; Teachman, 1987; Kiernan and Mensah, 2013; Melby, Conger, Fang, Wickrama and Conger, 2008; Aakvik, Vaage and Salvanes, 2019). Parental income and education critically shape a child's educational trajectory. Parental income, and the education level obtained by parents, not only provides the necessary conditions for improved academic performance but also by facilitating educational transitions (Leibowitz, 1977; Beblo and Lauer, 2004). Improved academic performances occurs through access to role models, mentors, information, and social networks, supported by both financial and social capital (Buchmann, DiPrete and McDaniel, 2008).

Crawford and Greaves (2015) demonstrate that wealthier high school students in the United Kingdom are more likely to progress to higher education, with pupils from the highest socioeconomic quintile being "40 percentage points more likely to go to university than those in the lowest socioeconomic quintile" (Crawford and Greaves, 2015, p. 8). Similarly, findings from Farquharson, McNally, and Tahir (2022) indicate that students in the top two deciles of household income are approximately 50% more likely than those in the poorest 10% of families to earn good grades in English and Mathematics. Importantly, these disparities persist across generations, demonstrating the intergenerational transmission of educational advantage (Chetty et al., 2014; Blanden et al., 2022).

Additionally, there exists an intersection between ethnicity and socioeconomic status that shapes educational outcomes. While pupils from some ethnic minority groups in the UK, such as Indian and Chinese, display higher university entry rates than White British pupils, even from disadvantaged backgrounds, others — particularly White working-class students — face entrenched barriers to attainment (Crawford and Greaves, 2015; UK Government Commission on Race and Ethnic Disparities, 2021). Gender brings another layer of complexity. Although girls presently outperform boys in many educational contexts, substantial gender gaps remain in specific global regions and cultural contexts due to entrenched norms and religious practices (Cooray and Potrafke, 2011; Hanushek et al., 2013; Unterhalter, 2005).

### 2.2 Institutional-Level Drivers: Teachers, School Quality, and Resources

At an intermediate level, different institutional environments have also been shown to impact educational outcomes. One of the most significant factors is teacher quality, which has been described as "transformative" (Farquharson et al., 2022, p. 800). Effective teachers not only enhance students' academic progress but also have lasting effects on their future earnings. For instance, Slater et al. (2012) found that having a teacher in the 75th percentile of effectiveness, rather than the 25th percentile, increases students' GCSE scores by nearly half a grade per subject. Similarly, using US data, Chetty et al. (2014) estimated that replacing a teacher in the bottom 5% of value-added with an average teacher could generate a lifetime earnings gain of $250,000 per classroom over the teacher's career.

Beyond teacher effects, equitable school funding has been shown to yield substantial long-term benefits, including higher graduation rates and better labour market outcomes (Heinesen and Krogh Graversen, 2005; Jackson et al., 2016). Policy interventions delivering this are particularly important for deprived schools, where increased resources can offset socioeconomic deficits, lowering incarceration rates and poverty levels, and increasing wages (Johnson and Jackson, 2019). Following the same line of reasoning, Gorard et al. (2022) highlight the positive effects of the 'Pupil Premium' — a grant designed to improve educational outcomes for disadvantaged pupils in state-funded schools in England. Their findings indicate that, following the policy intervention, socioeconomic segregation between primary schools declined, and educational attainment gaps narrowed substantially (Gorard et al., 2022, p. 1011).

### 2.3 Structural and Geographical Drivers of Inequality

Finally, and central to the scope of this study, one of the most significant manifestations of educational disparities is spatial. In almost every context, educational outcomes exhibit territorial differences to some extent (Thomas, Wang and Fan, 2001; Tomul, 2009; Trabelsi, 2013). Focusing on the United Kingdom, research indicates that substantial inequalities in educational attainment across local authorities are already evident by the end of primary school. Moreover, London boroughs demonstrate significantly higher levels of educational attainment compared to other regions, alongside greater per-pupil funding, particularly when contrasted with the northern parts of the country and inner-city areas (Gorard et al., 2022; Farquharson et al., 2022).

### 2.4 Topological Data Analysis

Topological Data Analysis (TDA) is a newly emerging method after Carlsson (2009), that identifies the sensitive geometric patterns of a dataset. Patterns include correlation structures, patterns within the joint densities of the data, outliers and combinations of characteristics which do not appear within the data. The BM algorithm is a TDA tool which enables the mapping of complex multidimensional data without discarding important variables. Unlike traditional regression or clustering methods, which often require dimensionality reduction before analysis, TDA preserves the full dimensionality of the data, without concerns of multicollinearity (Almgren et al., 2017; Godwin et al., 2019).

Applications of TDA have been expanding across various fields, demonstrating significant potential for capturing the nuances of educational outcomes in spatial contexts. Wolf and Monod (2023) apply TDA to detect geospatial patterns using social network data, identifying clusters of high-performing areas alongside isolated low-performing areas based on educational inequality. Similarly, Kauba and Weighill (2023) utilise TDA on demographic data to uncover clusters of cities based on demographic patterns derived from the dataset. Boyd et al. (2023) explore the impact of geoscience classes on students' career trajectories, further illustrating the potential of TDA in educational research. These emerging studies argue that TDA addresses the limitations of traditional statistical methods, which typically require low-dimensional data and yield static results. In contrast, TDA can process high-dimensional datasets and reveal more intricate patterns within the data. For these reasons, this study adopts TDA to identify geospatial patterns in the area, offering deeper insights into educational inequalities and their underlying structures.

Where much of the past work is based on the original mapper algorithm of Singh et al. (2007), this paper employs the Ball Mapper algorithm (BM) of Dłotko (2019). BM offers a more intuitive and flexible approach, avoiding filter functions and working directly on data using overlapping balls (Dłotko, 2019). BM produces graph-based visualisations preserving both local and global structures, and is robust to noise and high-dimensionality. Relative to the original mapper algorithm, BM only requires a single input parameter. The BM algorithm has proven especially powerful in finance, visualising non-monotonic relationships in stock returns (Dłotko et al., 2024), evaluating the efficient market hypothesis (Rudkin et al., 2025), and revealing patterns in financial data missed by standard methods (Dłotko et al., 2022). Within economics, applications of BM include regional resilience (Rudkin and Webber, 2023), and cultural gravity (Tubadji and Rudkin, 2025). In political economy, TDABM maps complex socio-demographic spaces, such as Brexit-related voting patterns (Rudkin et al., 2024), and changing political geographies (Rudkin and Otway, 2024), offering novel insights into political geography making it a useful tool for mapping regional patterns involving high-dimensional data.

---

## 3. Methodological Approach

### 3.1 Measuring Inequality in Education

To identify patterns of educational inequalities across the wards in Greater Manchester and Merseyside, the Education Gini Index (EGI) was selected as the primary measure of analysis, calculated for each ward. The EGI, developed by Thomas et al. (2001), adapts the income Gini coefficient as a measure of inequality. The index ranges from 0 (complete equality) to 1 (complete inequality):

$$\text{EGI} = \frac{1}{2\mu} \sum_{i=1}^{n} \sum_{j=1}^{n} p_i p_j |y_i - y_j|$$

where:
- $\mu$ = Average Years of Schooling (AYS) of the population distribution
- $p_i, p_j$ = Proportions of population at given educational achievement level (i or j)
- $y_i, y_j$ = Years of schooling at given educational achievement level (i or j)
- $n$ = Number of levels in educational achievement (n=6 for this paper)

Additionally, **Average Years of Schooling (AYS)** was calculated:

$$\text{AYS} = \sum_{i=1}^{n} p_i y_i$$

ranging from 0 to 16, with higher values indicating a more educated population.

Finally, the **Educational Attainment Ratio (EAR)** was also calculated as the proportion of the population that has reached at least a specific education threshold (Level 3 or higher):

$$\text{EAR} = \frac{P \geq \text{Level 3}}{P \text{ Total}} \times 100$$

### 3.2 Topological Data Analysis Ball Mapper

To visualise the structure of ward-level characteristics, and map the relationship between characteristics and educational inequalities, this paper uses the BM algorithm. The BM algorithm constructs a cover of a dataset $X$ using a set of balls with fixed radius, $\varepsilon$. The only parameter to be selected by the user is $\varepsilon$. The resulting cover is then plotted as a BM graph — an abstract two-dimensional representation of $X$.

Alternative dimensionality reductions to permit visualisation (PCA, UMAP, t-SNE) involve reducing the dimensionality of the dataset before constructing the graphics. The dimensionality reduction causes information to be lost. By contrast, the abstract nature of the BM visualisation means that the underlying dimensionality, and all information in the dataset, is retained.

**Algorithm:** Consider $X$ as a $D$-dimensional point cloud containing $N$ observations. A single data point, $\ell_1$, is selected at random from the dataset (notation $\ell$ denotes a landmark). A ball of radius $\varepsilon$ is drawn around $\ell_1$. The ball becomes ball 1; all points within the ball are considered covered by ball 1. A second landmark, $\ell_2$, is then selected from uncovered points; a ball of radius $\varepsilon$ is drawn around $\ell_2$. The algorithm continues to select landmarks until all data points in $X$ are covered. The result is the BM cover of $X$.

**Visualisation:** In the BM graph each landmark is represented by a ball. An edge is constructed between any pair of balls which have a non-empty intersection. The discs are sized according to the number of points contained and coloured according to a function on the members. In this paper the average EGI across all wards in the ball provides the colouration. The representation is abstract — to see values for any of the axes the plot must be recoloured according to the average value of that axis within each ball.

---

## 4. Data

### 4.1 Description of Data

To provide empirical evidence on patterns of educational inequality, the authors present a case study of Greater Manchester and Merseyside. The dataset is created to capture different components across wards within the spatial scope of this study. Primary sources:

- (a) UK Census 2021 data
- (b) English Deprivation Indices (Ministry of Housing, Communities & Local Government, 2018–2021)
- (c) Open-source GeoJSON files of UK wards (findthatpostcode.uk)

#### Table 1: Components, Variables, and Data Sources

| Component | Variables | Source |
|---|---|---|
| **Inequality in Education** | Gini Education Index (EGI); Average Years of Schooling (AYS); Educational Attainment Ratio (EAR) | Census 2021 |
| **Demographics** | % residents aged 24 or younger; % female residents; % no declared religion; % non-white ethnicity | Census 2021 |
| **Socioeconomic Status** | % unemployed; % households not deprived; % deprived in 1–2 dimensions; % deprived in 3–4 dimensions | Census 2021 |
| | Adult skill score | English Deprivation Indices (2018–2021) |
| **Health** | % residents reporting a disability | Census 2021 |
| | Health score | English Deprivation Indices (2018–2021) |
| **Crime** | Crime score | English Deprivation Indices (2018–2021) |
| **Geography** | % households without a car | Census 2021 |
| | Geographical barriers score | English Deprivation Indices (2018–2021) |
| | Distance from ward to city centre; Population density | findthatpostcode.uk (2021) |

EGI and AYS were calculated based on responses to questions concerning the highest level of qualification attained by all usual residents aged 16 and over in Greater Manchester and Merseyside.

### 4.2 Descriptive Statistics and Exploratory Data Analysis

The full sample is 372 wards across Greater Manchester and Merseyside in 2021.

**Headline statistics (selected from Table 2 in the paper):**

| Variable | Mean | SD | Min | Median | Max |
|---|---|---|---|---|---|
| EGI | 0.31 | 0.07 | 0.1 | 0.32 | 0.48 |
| AYS | 9.81 | 1.30 | 6.99 | 9.72 | 14.01 |
| Education Attainment Ratio (%) | 48.75 | 10.29 | 31.3 | 47.4 | 85.8 |
| Bottom-Top Quartile Ratio | 3.83 | 3.35 | 1.21 | 2.94 | 31.71 |
| Distance to city (km) | 4.97 | 2.78 | 0.18 | 4.58 | 14.83 |
| IMD score | 28.92 | 15.45 | 3.98 | 26.85 | 70.82 |
| Income score | 0.17 | 0.09 | 0.01 | 0.15 | 0.42 |
| Adult skills score | 0.33 | 0.11 | 0.08 | 0.33 | 0.63 |
| Population density | 3186 | 2045 | 18.6 | 2918 | 12980 |

Education indicators reveal a moderate average EGI of 0.31, suggesting some inequality in aggregated educational attainment across both regions. Central regions within both Greater Manchester and Merseyside display higher levels of educational inequality, with suburban areas appearing more equitable in terms of educational outcomes (Owens, 2023).

**Bivariate scatterplot patterns (Figures 2–5 in the paper) summarised:**

- **Demographics (Fig 2):** EGI rises moderately with proportion under-24 and proportion female; no strong relationship with non-religious proportion; slight positive association with proportion non-white. Greater Manchester displays more extreme values.
- **Socioeconomic (Fig 3):** EGI shows strong positive association with unemployment, income deprivation, multiple deprivation, and low adult skills. Consistent across both regions; Greater Manchester more extreme.
- **Health and Crime (Fig 4):** EGI increases with worse health, higher disability rates, and higher crime scores. Some Manchester wards depart from the main cloud — high health score and low EGI, or high crime and low EGI; some wards low-disabled but high-EGI. *These outliers are the motivating intuition for the BM analysis.*
- **Geography (Fig 5):** EGI rises with proportion of car-less households. Weak or no relationship with distance, geographical barriers, or population density.

---

## 5. Results

### 5.1 Core BM Analysis

Figure 6 in the paper provides the core BM analysis: 372 wards (data points) covered by 44 balls at radius $\varepsilon = 160$. EGI is the colouring variable. Each ball includes data points that are comparatively close to each other in Euclidean distance within the given data feature space (Singh et al., 2007; Rudkin et al., 2024). The edges between balls represent overlapping cover (mutual ward membership). Isolated balls are outliers — they do not share common patterns with other balls.

The BM plot shows three "strings" of balls. The two longest strings cross close to balls 10 and 12; a smaller string includes balls 30, 34, 18, 41 (crossing near 27); a shorter collection of three balls — 25, 42, 31. There are two sets of highly connected balls in the longest string indicating groups of wards which have similar characteristics but are sufficiently different to occupy separate balls — such structures appear when data in that region has low correlation. Overall, the BM plot is indicative of strong correlation between all of the characteristics studied, but the disparate strings and lower-correlation areas confirm all variables matter.

### 5.2 Low EGI Areas

The lowest EGI (0.15) is Blackfriars and Trinity (Ball 43) in Salford — highly isolated, coloured red. Distinguishing characteristics: extremely low under-15 share (6.9%), >50% non-deprived (58.3%), White-majority (71.4%), non-religious majority (55.4%).

Ball 40 (Old Moat) is also isolated with EGI 0.22 — low under-24 share (14.6%), moderate deprivation, low unemployment (3.5%), White-majority (65.4%); 18.24% disabled.

Ball 38 (Deansgate, Broughton (Salford), Sedgley (Bury)) — EGI 0.26; under-24 share 20.66%; moderate deprivation 51.8%; low unemployment 3.83%; White-majority 65.4%; lower disabled share 13.5%.

Pattern: low EGI clusters in Greater Manchester and suburban regions, lower proportions of younger residents, relatively stable socioeconomic indicators, White-majority population.

### 5.3 Mid EGI Areas

The mid-range EGI values dominate the main topology — Balls 0, 1, 8, 9, 10, 16, 24, 26 — moderate EGI of 0.32, under-24 share ~18.5%, deprivation 1–2 at 48.1%, unemployment 2.6%, predominantly White (91.3%).

Balls 25, 31, 42 share similar moderate EGI levels (~0.31), with under-15 share ~19.9% and deprivation 1–2 at 53.0%. Primarily located in Manchester and Liverpool city cores.

### 5.4 High EGI Areas

Highest EGI (0.44) is observed in Rumworth and Werneth (Balls 11 and 19), in Bolton and Oldham. These wards are isolated from the main topology despite geographic proximity to other connected wards. Distinguishing characteristics: large under-24 share (28.4%), Asian-majority (65.75%), Muslim-majority (69.4%), high deprivation (62.3%).

Ball 18 (St Mary's, Oldham) has the highest EGI of any ball (0.46) and shares the same demographic profile as Balls 11/19. It is connected to Ball 41 (Derby (Sefton), Piccadilly) and Ball 34 (Riverside (Liverpool), Tuebrook and Stoneycroft, Derby (Sefton), Litherland, Victoria (Sefton), New Brighton, Swanside).

Ball 6 (Greater Manchester), Ball 13 (Manchester), and Ball 30 (Liverpool) are higher-EGI hotspots (~0.38) *within* the main topology — share larger young population (22.6%), weaker socioeconomic indicators (deprivation 1–2 at 54.7%), but share ethnic/religious characteristics with the main topology (White 70.0%, Christian 47.8%).

**Synthesis (paper's claim):** Isolated balls with high EGI have distinct demographic characteristics (consistent with Crawford and Greaves 2015), while "hotspot" balls within the main topology share characteristics with connected areas but have poorer socioeconomic indicators (consistent with the White-working-class entrenched-disadvantage finding).

### 5.5 Role of Ball Radius

The radius $\varepsilon$ is the only parameter. Figure 7 illustrates the impact of different $\varepsilon$ values: smaller radii ($\varepsilon = 50, 100$) generate many balls (hard to interpret); larger radius ($\varepsilon = 200$) simplifies but merges too many wards into each ball. Based on this robustness check, $\varepsilon = 160$ is selected as "the most interpretable value." When radius is lowered, most balls disconnect; as radius increases, the three groups become clearer.

### 5.6 Different Variables

Recolouring the same topology by AYS instead of EGI (Figure 8) gives roughly the inverse pattern (higher EGI ↔ lower AYS).

Removing ethnicity and religion variables from $X$ (Figure 9) significantly changes the topology — Ball 18 (St Mary's, Oldham) is no longer isolated; it merges into Ball 17 with Riverside (Liverpool), Derby (Sefton), Victoria (Sefton), Piccadilly. The paper claims this demonstrates that excluding these variables weakens the robustness and validity of the analysis.

---

## 6. Discussion and Conclusion

The paper reveals important insights into spatial patterns of educational inequality. Using ward-level data from Greater Manchester and Merseyside, it identifies distinct clusters of high and low educational inequality aligning with socioeconomic, demographic, and ethnic characteristics. Wards with high EGI exhibited higher levels of deprivation, greater numbers of young people, and greater ethnic diversity (Crawford and Greaves 2015; UK Government Commission on Race and Ethnic Disparities 2021). Low EGI areas were more socioeconomically stable and predominantly White (Gorard et al. 2022; Farquharson et al. 2022).

BM is positioned as a strength because it captures complex, high-dimensional relationships without dimensionality reduction (Almgren et al. 2017; Godwin et al. 2019); it preserves intricate interactions, reveals hidden patterns and outlier communities, and enables detection of spatially isolated areas of high inequality. Robustness checks confirmed stability of results across different radius parameters and demonstrated the significance of including ethnicity and religion variables.

### Policy Suggestions (the paper's framing)

Two groups of policy responses to BM analysis:

1. **Structural change at the area level** — position geographic areas closer to balls where EGI is higher (better) — increase income, provide better local facilities, tackle crime, employment opportunities, transport. Some characteristics (ethnic make-up) are harder to adjust with policy. BM helps identify the nearest wards in characteristic space and guides which specific variables are best targeted.
2. **Individual-level redistribution** — redistribute students from overcrowded wards to underutilised schools (citing Britton and Sibieta 2024; Filges et al. 2018; Machin and McNally 2008; Sibieta 2020 on class-size effects). Existing UK Department for Education policies — Basic Need Funding and Academy Expansions — are noted; given the high concentration of younger populations in high-EGI wards, more intensive student reallocation or increased funding may be necessary.

The paper notes that direct empirical evidence on the effectiveness of redistribution policies remains limited.

### Closing claim

The Greater Manchester and Merseyside case study underlines that despite strong correlation amongst the relevant geographic, demographic and economic conditions, the interaction between characteristics is important. BM allows the consideration of the joint distribution, mapping outcomes in a way that can drive policy at both the regional and individual level. There remains an opportunity to explore the inference in other areas, or in different time periods. There is also an open question as to the choice of relevant characteristics and the gathering of data there on. Nonetheless, the robustness explored in this paper points to a consistency that could be expected to be present in other situations.

---

## References (selected — full bibliography in PDF)

- Aakvik, A., Vaage, K. & Salvanes, K. (2005). Educational Attainment and Family Background. *German Economic Review*, 6(3), 377–394.
- Almgren, K., Kim, M. & Lee, J. (2017). Extracting knowledge from the geometric shape of social network data using topological data analysis. *Entropy*, 19(7), 360.
- Blanden, J., Doepke, M. & Stuhler, J. (2023). Educational inequality. In *Handbook of the Economics of Education*, Vol. 6, pp. 405–497. Elsevier.
- Boyd, E. A., Lazar, K. B. & Moysey, S. (2023). Big data to support geoscience recruitment: Novel adoption of topological data analysis in geoscience education. *GSA Bulletin*, 136(3-4), 1458–1468.
- Carlsson, G. (2009). Topology and data. *Bulletin of the American Mathematical Society*, 46(2), 255–308.
- Chetty, R., Friedman, J. N. & Rockoff, J. E. (2014). Measuring the impacts of teachers I. *American Economic Review*, 104(9), 2593–2632.
- Crawford, C. & Greaves, E. (2015). Socio-economic, ethnic and gender differences in HE participation. BIS Research Papers 186.
- Dłotko, P. (2019). Ball mapper: A shape summary for topological data analysis. arXiv:1901.07410.
- Dłotko, P., Qiu, W. & Rudkin, S. (2022). Topological Data Analysis Ball Mapper for Finance. arXiv:2206.03622.
- Dłotko, P., Qiu, W. & Rudkin, S. T. (2021/2024). Financial ratios and stock returns reappraised through a topological data analysis lens. *European Journal of Finance*, 30(1), 53–77.
- Farquharson, C., McNally, S. & Tahir, I. (2022). Education Inequalities. IFS Deaton Review of Inequalities.
- Gorard, S., See, B. H. & Siddiqui, N. (2021). The Geography of School Inequality in England. *Educational Review*, 73(3), 275–290.
- Gorard, S., See, B. H. & Siddiqui, N. (2022). *Making Schools Better for Disadvantaged Students*. Routledge.
- Johnson, R. C. & Jackson, C. K. (2019). Reducing inequality through dynamic complementarity. *American Economic Journal: Economic Policy*, 11(4), 310–349.
- Kauba, J. A. & Weighill, T. (2023). Topological analysis of U.S. city demographics. arXiv:2310.08334.
- Rudkin, S., Barros, L., Dłotko, P. & Qiu, W. (2024). An economic topology of the Brexit vote. *Regional Studies*, 58(3), 601–618.
- Rudkin, S., Rudkin, W. & Dłotko, P. (2025). Return trajectory and the forecastability of bitcoin returns. *The Financial Review*.
- Rudkin, S. & Webber, D. J. (2023). Regional growth paths and regional resilience. SSRN 4333276.
- Singh, G., Mémoli, F. & Carlsson, G. E. (2007). Topological Methods for the Analysis of High Dimensional Data Sets and 3D Object Recognition. *Eurographics*, 91–100.
- Thomas, V., Wang, Y. & Fan, X. (2001). Measuring education inequality: Gini coefficients of education. IIEP.
- Tubadji, A. & Rudkin, S. (2025). Cultural gravity and redistribution of growth through migration. *Papers in Regional Science*, 104(1), 100064.
- Wolf, A. & Monod, A. (2023). Topological community detection: A sheaf-theoretic approach. arXiv:2310.05767.

---

## Source Notes

- PDF text extraction: contained garbled math symbols (rendered as Unicode replacement characters) in equation blocks; reconstructed from context. EGI formula is the Thomas-Wang-Fan (2001) standard form.
- The full ward-by-ball mapping (Table 3 in the paper) and the per-ball characteristic table (Table 4 / Table 5-2 in the paper) are not reproduced here — see source PDF for the comprehensive listings.
- Figures 1–9 referenced in the text are visual artefacts in the source PDF and not reproduced here.
