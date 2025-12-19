# Unveiling complex nonlinear dynamics in stock markets through topological data analysis

**Chun-Xiao Nie***

*Economic Forecasting and Policy Simulation Laboratory, Zhejiang Gongshang University, Hangzhou 310018, China*  
*School of Statistics and Mathematics, Zhejiang Gongshang University, Hangzhou 310018, China*

---

## Article Info

**Keywords:**
- Time series
- Topological data analysis
- Topological correlation coefficient
- Nonlinear serial dependence

**Journal:** Physica A  
**Volume:** 680 (2025) 131025  
**DOI:** https://doi.org/10.1016/j.physa.2025.131025

---

## Abstract

Testing and characterizing nonlinear serial dependence in financial time series constitutes a critical research focus, extensively applied in examining weak-form market efficiency. This study demonstrates ATCC's capability to capture nonlinear dependence and employs it to analyze equity market return series. Our findings reveal that rolling-window ATCC can characterize high-resolution dynamics of dependence. For instance, using minute-level data, we document how the Russia–Ukraine conflict information significantly impacted dependence structures in the Chinese market. Furthermore, based on daily index data, the 2025 Trump tariff policies are shown to have substantially influenced dependence patterns in both Chinese and U.S. market indices. Notably, through combined ATCC and linear modeling of SSE 50 constituent returns, we find that while linear models adequately characterize dependence in most daily returns, a minority of stocks exhibit nonlinear serial dependence. This research establishes an ATCC-based analytical framework, providing an effective quantitative tool for investigating nonlinear serial dependence and its high-resolution dynamics.

---

## 1. Introduction

The Efficient Market Hypothesis (EMH), a cornerstone of financial theory, has undergone extensive testing since its proposal. For weak-form market efficiency, two primary testing approaches currently exist: one approach examines deviations from random walks in financial time series using various methodologies, while the other analyzes the profitability of historical return-based strategies [1]. Within the first approach, common methods include tests for linear serial correlation, nonlinear serial dependence, long memory properties, and low-dimensional chaos. Furthermore, a well-established stylized fact in financial data analysis is the 'absence of autocorrelations' [2,3]. Empirical studies demonstrate that return series typically exhibit insignificant autocorrelations except at small time scales such as minute-level data. Serial correlation in returns constitutes a critical analytical focus for both testing the Efficient Market Hypothesis (EMH) and examining stylized facts. Previous research primarily employed methods including autocorrelation functions, AR models [4], the AQ test [5], and the AVR test to detect the presence of serial correlation [6]. More specialized methods, such as the Tsay test and BDS test among others, have been developed to analyze broader forms of nonlinear serial dependence [7,8].

However, existing methods struggle to concurrently address two critical aspects: effectively testing nonlinear dependence and performing robust analysis on small-sample data. This study employs the auto topological correlation coefficient (ATCC) to analyze return series [9,10]. ATCC enables reliable small-sample examination while effectively identifying nonlinear serial dependence.

Leveraging these dual advantages, the research focuses on two key objectives: providing high-resolution dynamic analysis through rolling-window ATCC computations, and detecting nonlinear dependence by combining ATCC diagnostics with linear models.

---

## 2. Literature review

Autocorrelation is not only an important indicator of the short-term persistence of stock returns [11], but also used to construct statistical tests such as the Box–Pierce (AQ) test and the automatic variance ratio (AVR) test [5,6]. Autocorrelation is also commonly used on important topics such as detecting market effectiveness [4,12]. Some previous studies have revealed that the autocorrelation of return series varies over time, and this feature can be observed on different time scales, such as the monthly returns of the S&P500 index and the 10 min returns of stocks in the US market [4,13]. In empirical analysis, the autocorrelation coefficient is often estimated by the AR process [4,13], and the conditional autocorrelation can be estimated by the GARCH model [14]. In addition, some studies have analyzed the relationship between autocorrelation and other indicators. For example, based on U.S. market index data, an early study found that some factors were associated with negative conditional autocorrelation, such as high volatility, high trading volume, and large price declines [15]. Based on different methods, another study also showed a relationship between volatility and autocorrelation [16]. Markets are more volatile during periods of crisis and sharp declines in stock prices, and these analyses imply a relationship between autocorrelation and market states.

Previous studies have focused on linear autocorrelation, while there may be complex dependencies between observations of financial time series, as demonstrated by the ARCH effect. This implies that non-trivial nonlinear autocorrelation may be included between observations, and thus this study uses nonlinear time series analysis tools to analyze returns. Currently, there are a variety of tests for analyzing the nonlinear characteristics of return series, such as Hinich's test [17], BDS Test [8]. Researchers have widely used these tests to analyze different markets. For example, in a study of indices return series in the U.S. market, researchers used the Box–Pierce test and the automatic variance ratio test and found a relationship between significant return autocorrelations and major exogenous events [18]. Lim, K.P. and Hooy, C.W. analyzed the stock markets of the G7 countries using the BDS test and found evidence supporting short-term nonlinear predictability [19]. A. Urquhart and F. McGroarty used the VR test and the BDS test to analyze several market indices and found that the predictability of returns varies over time, thus supporting the adaptive market hypothesis [20]. Based on the Hinich portmanteau bicorrelation test, Claudio A. Bonilla et al. found that the nonlinear autocorrelation of the return series of Latin American stock market indices is episodic [21]. However, a study of the Chilean stock market suggests that episodic nonlinearities are related to exogenous events [22]. More empirical results can be found in the relevant review literature [1].

Previous studies have found that nonlinear dependencies have time-varying characteristics, and some studies have suggested that significant nonlinear dependencies are related to exogenous major events. Due to differences in test methods and data sets, empirical results show a variety of conclusions, implying that nonlinear dependencies are complex.

To characterize the dynamics of complex time series, we employ a topological data analysis (TDA) approach in this study. In recent years, TDA has garnered widespread attention from researchers, as it offers new perspectives by characterizing higher-order structures within data, such as by employing Betti numbers and homology groups to describe "hole" structures in high-dimensional datasets [23,24]. Furthermore, several studies have attempted to analyze time series using TDA [25,26]. In particular, a limited number of analyses have explored financial time series through TDA [27–29]. Here, we utilize the topological correlation coefficient (TCC) constructed via the k-nearest neighbor filtration in topological data analysis [9,30]. In recent years, several studies have revealed that k-nearest neighbor (kNN) filtration can effectively characterize the structural properties of diverse data types, including time series and complex networks [9,10,31,32].

TCC can effectively detect nonlinear dependencies between series and has some important advantages, such as that it can be implemented on small sample data and is insensitive to noise and outliers [9]. Recently, TCC has been generalized to time-dependent objects, allowing it to be applied to a wider range of complex objects, such as dynamic networks, and so on [32]. In particular, a recent study used TCC to analyze a series of cross-sectional return distributions in equity markets [10]. TCC effectively identifies the persistence of distribution series, and this study focuses on the dependence of single return series, so that the dependence of linear dependence and volatility can be filtered through the GARCH models.

Here, we analyze whether the return series in the stock market includes nonlinear autocorrelation by TCC. Furthermore, we study the factors that generate nonlinear autocorrelation through financial econometric models. In our analysis, linear correlation is a special case. To eliminate linear dependence, we use the ARMA + GARCH model to filter the return time series [33]. In this way, by combining TCC with models from financial econometrics, we analyze the factors driving dependence.

---

## 3. Data and software

### 3.1. Data

We employ ATCC to analyze four datasets, conducting tests to examine the dynamics of serial dependence and to categorize serial dependence, as presented in Table 1. The first dataset consists of the 1 min index price series for the Shanghai Composite Index (SSE) on February 24, 2022. The second and third datasets are the daily closing price series for the Shanghai Composite Index and the S&P 500 Index, respectively. The fourth dataset comprises the daily closing price series for all 50 constituent stocks of the SSE 50 Index.

**Table 1: Dataset descriptions**

| Data | Time | Frequency | n |
|------|------|-----------|---|
| 1 | 2022/2/24 | 1 min | 240 |
| 2 | 2024/1/4–2025/7/4 | Daily | 361 |
| 3 | 2024/1/4–2025/7/4 | Daily | 375 |
| 4 | 2024/1/2–2025/7/18 | Daily | 373 |

For both closing price series and index price series denoted as {p_t}, we consistently transform them into log-return series r_t, where r_t = log(p_{t+1}/p_t). All return series are stationary time series, with the null hypothesis of the ADF test rejected at the significance level α = 0.05.

### 3.2. Software

Here, we use the package fGARCH to generate simulated time series and analyze return series. We use the package tcctest to calculate TCC values as well as analyze significance. This package can be downloaded from the following link: https://github.com/niechunxiao/tcctest. In addition, the test for the ARCH effect is performed by package FinTS.

---

## 4. Method

### 4.1. Topological correlation coefficient

TCC extracts the topology of time series by kNN filtration, and characterizes the nonlinear correlation between time series by network similarity [9]. Next, we first construct kNN filtration for the time series. If we define a distance between observations of a time series x = {x_i : i = 1, 2, …, n}, such as Euclidean distance d_x(i, j) = |x_i − x_j|, then x corresponds to a distance matrix (d_x = [d_x(i, j)]) of order n. This distance matrix describes the metric-based relationship between observations. Next, we use the k-nearest neighbor network sequence to extract the neighbor-based relationships between observations. For a value k, we construct a network of n nodes, W_k(V, E_k) (V = {v_i}), where each observation x_i corresponds to a node v_i. The edge set E_k is constructed as follows. We order the distance values of x_i and other observations in ascending order, and use the symbol N^k_i = {v^1_i, v^2_i, …, v^k_i} to represent the set of k neighbors of x_i, that is, these k nodes correspond to the top k observations close to x_i. By changing k from 1 to n − 1, a network sequence {W_k(V, E_k), k = 1, 2, …, n − 1} can be constructed. Since N^{k_1}_i is included in N^{k_2}_i (k_1 < k_2), there is a relationship Eq. (1).

```
E_1 ⊆ E_2 ⊆ ⋯ E_k ⊆ E_{k+1} ⋯ ⊆ E_{n−1}     (1)
```

Below, we define the TCC for the series x = {x_i : i = 1, 2, …, n} and y = {y_i : i = 1, 2 ⋯, n}. We assume that the kNN filtration sequences for x and y are {W^x_k(V, E^x_k)} and {W^y_k(V, E^y_k)}, respectively. TCC is the average of the Jaccard similarities between two sequences Eq. (2). Here, Jaccard similarity is defined as J(W^x_i, W^y_i) = |E^x_i ∩ E^y_i| / |E^x_i ∪ E^y_i| [34,35]. Since Jaccard similarity is valued at the interval [0, 1], TCC is valued at [0, 1], and larger TCC values indicate stronger similarity.

```
TCC(x, y) = (1/(n − 1)) Σ^{n−1}_{i=1} J(W^x_i, W^y_i)     (2)
```

If the time series includes large sample observations, we can approximate TCC values by converting Eq. (3) to integral form. We denote J(ρ_{i/n}) with J(W^x_i, W^y_i), and then Eq. (2) can be approximated by the integral form Eq. (3). Here, the function J(ρ) is a polynomial function fitted by the sequence {(i/n, J(ρ_{i/n})), i = 1, 2, …, n − 1}. To simplify the calculation, we do not need to fit a polynomial function with all the Jaccard similarities. A suitable estimate can be obtained by selecting a set of Jaccard similarity values at equal intervals. For example, we can select the sequence {(i/n, J(ρ_{i/n})), i = 1, 1 + l, 1 + 2l, …, 1 + ml} (m = [n/l]) for fitting a polynomial function, where l is a parameter. Here, we always fit a polynomial of order 3.

```
TCC(x, y) = ∫^1_0 J(ρ)dρ     (3)
```

### 4.2. Permutation test

Since this study only needs to focus on dependencies between observations, significance analysis based on random permutations (RP) surrogates was used. RP surrogates are obtained by randomizing the timestamps of the original observations [36]. This approach directly destroys dependencies, providing baseline values for detecting dependencies. We test the significance of TCC(x, y) as follows.

1. We generate RP surrogate for x and y, respectively, and denote x_1 = {x^1_1, x^1_2, …, x^1_n} and y_1 = {y^1_1, y^1_2, …, y^1_n}.
2. We calculate the TCC values for x_1 and y_1, which is denoted as TCC_1.
3. By repeating steps 1 and 2, a total of N TCC values (TCC_rp = {TCC_i, i = 1, 2, …, N}) are calculated. We represent the mean and standard deviation of TCC_rp using the symbols m_rp and sd_rp.
4. The p-value is obtained from the distribution {TCC_i} and the original TCC(x, y) value.

If TCC_rp is sampled from a normal population, the p-value can be obtained directly. In this way, we obtain significance analysis results by comparing the p-value with the specified significance level α. In addition, we can also characterize how far TCC(x, y) deviates from the baseline value by Z = (TCC(x,y) − m_rp) / sd_rp, and a Z-score greater than 1.65 implies that the TCC value is significant, where the significance level α = 0.05. Since the Z-score changes with N, a small N value may significantly affect the analysis, and based on previous studies, we set N = 300 [9]. Furthermore, p-values can be directly derived from {TCC_i} quantiles. Empirical computations confirm that this approach typically yields results consistent with Z-score-based analysis.

### 4.3. Auto topological correlation coefficient (ATCC)

In this study, we characterize the dependence of a return series as follows [9,10]. We construct two series from the observations of one time series and calculate the ATCC value with the lag order. For series x, the ATCC_τ value of order τ is TCC(x_{1,n−τ}, x_{τ+1,n}), where x_{1,n−τ} = {x_1, x_2, …, x_{n−τ}}, x_{τ+1,n} = {x_{τ+1}, x_{τ+2}, …, x_n}. Furthermore, for comparative analysis, we also calculate the sample autocorrelation coefficient and denote it with the symbol ACF. ACF can be considered as an indicator of linear dependence and can therefore be used for comparison with ATCC.

### 4.4. GARCH model

Volatility clustering describes a stylized fact of financial markets [2,3]. For a return series, a large price change is often followed by large price changes, and small changes are typically followed by small changes. As a result, volatility exhibits persistence or autocorrelation. This property can be captured by GARCH models.

To demonstrate ATCC's ability to capture nonlinear dependencies, we use the GARCH model to generate surrogates and test the significance of ATCC values. Here, we choose a classical model for the purpose of analyzing the impact of volatility dependence on return dependence. The GARCH(p, q) model includes two equations that characterize returns and volatility, respectively, where a_t represents new information [33]. In many analyses, the μ_t in the mean equation is set up as an ARMA process. The symbol ε_t represents an I.I.D random variable with a mean and variance of 0 and 1, respectively. The two equations are connected by a_t, whose lag term is included in the volatility equation and used to model volatility aggregation. In addition, for the GARCH model, the equation for volatility also includes the lag term of σ_t.

```
r_{i,t} = μ_t + a_t
a_t = σ_t ε_t
σ^2_t = α_0 + Σ^p_{i=1} α_i a^2_{t−i} + Σ^q_{i=1} β_i σ^2_{t−i}     (4)
```

For the return series, we estimate a suitable model by adjusting the order of ARMA and GARCH. In addition, the distribution of the variable ε_t can be set to a Gaussian distribution (norm), a Student-t-distribution (std), a skewed Student distribution (sstd), a generalized error distribution (ged), and so on.

### 4.5. ATCC-based test for nonlinear serial dependence

There are many extended models that can capture more features, such as the APARCH model that captures asymmetry [33]. However, we found that if the model was adequately estimated, there was only a slight difference between the volatility series estimated by GARCH and the series estimated by other models. Similar to previous studies, we used the ARMA + GARCH model to filter the return series and then analyze the nonlinearity of the residuals [19].

By filtering linear serial correlation from return series using ARMA+GARCH modeling, we extract the standardized residual series to analyze whether nonlinear serial dependence persists. If ATCC identifies significant dependence in these residuals, this indicates the presence of nonlinear serial dependence in the original returns. The method combining ATCC with ARMA+GARCH proceeds as follows.

1. First, we estimate a well-specified ARMA + GARCH model for the return series, where the null hypothesis of the Ljung–Box test is not rejected for both the standardized residual series and its squared series.
2. We extract the standardized residuals s_res obtained in step 1 and calculate the TCC_τ value of s_res.
3. If the standardized residual series from Step 2 exhibits significant ATCC values, this indicates the presence of nonlinear serial dependence in the original return series. Conversely, insignificant ATCC values imply that serial correlation has been adequately captured by the linear model.

---

## 5. Results

### 5.1. Testing based on synthetic data

#### 5.1.1. Comparative analysis of test results across synthetic models

One advantage of ATCC is its effectiveness in small-sample data. To demonstrate its ability to detect serial correlation, we apply the ATCC test to several datasets generated from artificial models. The four models are: AR(1) with GARCH(1,1) errors (Eq. (5)), AR(1) with SV (stochastic volatility) errors (Eq. (6)), the bilinear model (Eq. (7)), and the TAR(1) model (Eq. (8)) [37]. Among these, the first two are linear models, while the latter two are nonlinear models.

For comparison with existing studies, we generate 1000 sample series for each model, where each sample series consists of n_s observations [37]. Here, we specifically include the computational results for n_s = 50, and additionally set n_s = 100 and 300. We then compute ATCC_1 and count the number of series with p-values less than 0.05. The computational results are presented in Table 2.

```
x_t = 0.1x_{t−1} + a_t
a_t = ε_t σ_t
σ^2_t = 0.001 + 0.09a^2_{t−1} + 0.90σ^2_{t−1}
ε_t ∼ N(0, 1)     (5)
```

```
x_t = 0.1x_{t−1} + v_t
v_t = exp(0.5h_t)ε_t
h_t = 0.95h_{t−1} + u_t
u_t ∼ N(0, 1)     (6)
```

```
x_t = ε_t + 0.25ε_{t−1}x_{t−1} + 0.15ε_{t−1}x_{t−2}
ε_t ∼ N(0, 1)     (7)
```

```
x_t = −0.5x_{t−1} + ε_t,  x_{t−1} ≥ 1
x_t = 0.4x_{t−1} + ε_t,   x_t < 1
ε_t ∼ N(0, 1)     (8)
```

**Table 2: ATCC-based test results for four artificial model-generated datasets**

| n_s | AR + G | AR + S | Bilinear | TAR(1) |
|-----|--------|--------|----------|--------|
| 50  | 78.4   | 78.7   | 22.3     | 43.8   |
| 100 | 97.1   | 98.7   | 34.5     | 73.7   |
| 300 | 100    | 100    | 79.9     | 99.3   |

*AR + G: AR(1) + GARCH(1, 1). AR + S: AR(1) + SV.*

Firstly, for linear models, when n_s = 50, ATCC can already detect serial dependence in the majority of series, and approaches detection in all series when n_s = 100. This significantly outperforms the results of other tests in existing studies [37]. For example, at n_s = 100, previous analyses showed that the AQ, AVR, DL, and GS tests could only detect dependence in fewer than 20% of the series [37]. Secondly, for the Bilinear model, at n_s = 100, ATCC's performance exceeds that of AQ, AVR, and DL when compared to prior analyses [37]. For the TAR(1) model, ATCC can detect dependence in the majority of series at n_s = 100, outperforming all four tests from earlier research [37]. In summary, for small samples, ATCC can effectively detect serial dependence in the vast majority of series generated by linear models, as well as in most series generated by nonlinear models.

#### 5.1.2. ATCC analysis for AR+GARCH models

We generate a sequence comprising 300 observations using Eq. (9) (Fig. 1), where the mean equation incorporates AR(2). Subsequently, we estimate the parameters using an AR(2) model and extract the residual series. The estimation results for the parameters are presented in Eq. (10), with the p-values of all parameter coefficients being less than 0.01. Finally, we achieved a well-specified parameter estimation using the AR(2)+GARCH(1,1) model, as shown in Eq. (11), where all parameters exhibit p-values below 0.01. Furthermore, both the standardized residual series and its squared series yield Ljung–Box test p-values exceeding 0.1, demonstrating that the model has been adequately characterized.

```
x_t = 0.5x_{t−1} − 0.4x_{t−2} + a_t
a_t = σ_t ε_t,  ε_t ∼ N(0, 1)
σ^2_t = 1 × 10^{−6} + 0.6a^2_{t−1} + 0.3σ^2_{t−1}     (9)
```

```
x_t = 0.6166x_{t−1} − 0.4605x_{t−1} + ε_t     (10)
```

```
x_t = 0.478x_{t−1} − 0.464x_{t−2} + a_t
a_t = σ_t ε_t,  ε_t ∼ N(0, 1)
σ^2_t = 7.629 × 10^{−7} + 0.550a^2_{t−1} + 0.364σ^2_{t−1}     (11)
```

**Table 3: ATCC analysis results for AR+GARCH-generated synthetic data**

| τ | ATCC_τ | ATCC^{res,1}_τ | ATCC^{res,2}_τ |
|---|--------|----------------|----------------|
| 1 | 0.424*** | 0.408*** | 0.388 (0.553) |
| 2 | 0.411*** | 0.395*** | 0.38 (0.967) |
| 3 | 0.407*** | 0.398*** | 0.385 (0.71) |
| 4 | 0.403*** | 0.404*** | 0.392 (0.143) |
| 5 | 0.4*** | 0.387 (0.29) | 0.384 (0.567) |
| 6 | 0.392 (0.077) | 0.383 (0.83) | 0.381 (0.967) |

*\*\*\*: p < 0.001. \*\*: p < 0.01. \*: p < 0.05.*

**Table 4: ACF results for AR+GARCH-generated synthetic data**

| τ | ACF_τ | ACF^{res,1}_τ | ACF^{res,2}_τ |
|---|-------|---------------|---------------|
| 1 | 0.422 | 0.033 | 0.077 |
| 2 | −0.203 | −0.018 | 0.011 |
| 3 | −0.276 | 0.059 | 0.107 |
| 4 | −0.039 | 0.01 | −0.035 |
| 5 | 0.144 | 0.066 | 0.033 |
| 6 | 0.091 | −0.036 | 0.003 |

*\*\*\*: p < 0.001. \*\*: p < 0.01. \*: p < 0.05.*

We then compute the ATCC for both the original series and the residual series, respectively, as shown in Table 3. We denote the ATCC values of the residual series filtered by Eqs. (10) and (11) as ATCC^{res,1}_τ and ATCC^{res,2}_τ, respectively. Additionally, for comparison with ACF, Table 4 lists the ACF values for the original series, and the residual series from Eqs. (6) and (7). The comparative analysis is as follows. Firstly, the original series exhibits significant ATCC values and significant ACF values, which decay with increasing lags. Secondly, the residual series filtered by the AR(2) model shows no significant ACF values, but displays four significant ATCC values. Finally, the residual series obtained after filtering with the AR(2)+GARCH(1,1) model exhibits no significant ATCC values. This example demonstrates that ATCC can capture serial dependence generated by the volatility equation. Furthermore, if the residual series filtered by an adequate ARMA+GARCH model exhibits significant ATCC values, this suggests the presence of nonlinear serial dependence in the original series.

### 5.2. Dynamics of serial dependence

#### 5.2.1. Example based on high-frequency data

Below, we analyze 1 min frequency data from the Shanghai Composite Index (SSE) of the Chinese stock market on February 24, 2022. On this day, Vladimir Putin announced the decision to conduct a "special military operation" in the Donbas region during a televised address. This news significantly impacted the Chinese stock market. Due to the time zone difference between Moscow and Beijing, this information impacted the Chinese stock market around midday (China time). Fig. 2 displays the minute-level return series for that day. A pronounced abnormal volatility can be observed around midday, characterized by an extreme negative return spike, which was directly triggered by news regarding the Russia–Ukraine conflict.

**Table 5: ACF versus ATCC for minute-level return series**

| τ | ACF_τ | ATCC_τ |
|---|-------|--------|
| 1 | 0.388*** | 0.411*** |
| 2 | 0.1 | 0.397** |
| 3 | 0.058 | 0.404*** |
| 4 | −0.041 | 0.398*** |
| 5 | 0.021 | 0.403*** |
| 6 | 0.099 | 0.404*** |

*\*\*\*: p < 0.001. \*\*: p < 0.01. \*: p < 0.05.*

Firstly, we compute the ATCC and ACF of the return series for that day, as shown in Table 5. Only one ACF value is significant, while six ATCC values are significant. This indicates the presence of nonlinear serial dependence in the series. Secondly, we calculate the ATCC_1 values using a rolling window approach, with the window length set to 30 min. The resulting ATCC series is shown in Fig. 3, which exhibits a distinct peak around midday and displays a rising pattern towards the market close. Here, we focus on the variation in ATCC values during the midday period.

Corresponding to Figs. 3, 4 displays the series of p-values. There exists a sub-period exhibiting significant serial dependence around midday. During this midday period, the first window with a significant ATCC_1 value spans 11:03:00-13:02:00. Given the lunch break in the Chinese stock market, this window precisely covers a segment before the trading halt and extends two minutes after the afternoon reopening. Subsequently, the ATCC values increase rapidly, reaching a maximum of 0.487 in the window 11:19:00-13:18:00. These results indicate that market serial dependence intensified during the midday period, coinciding with the information shock from the Russia–Ukraine conflict.

#### 5.2.2. Example based on daily data

Below, we separately analyze the return series of the Shanghai Composite Index and the S&P 500 Index. We set the rolling window length to 40, which approximately corresponds to two months of trading days. We then calculate the ATCC_1 values using this rolling window, as shown in Fig.