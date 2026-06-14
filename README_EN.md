# Regularized Fund Evaluation Replication

This project replicates the fund evaluation framework from the Soochow Securities financial engineering report *Regularized Fund Evaluation 2021Q3 Portfolio* dated July 3, 2021. Based on this framework, the project implements data cleaning, regularized regression, holding-based exposure blending, fund ability scoring, quarterly rolling fund selection, and out-of-sample backtesting.

The core research objects are active equity funds and equity-oriented hybrid mutual funds. The main entry point is [`fun_RR.ipynb`](./fun_RR.ipynb). Data preparation notebooks, field descriptions, and the complete file inventory are summarized in [`summary.md`](./summary.md).

> This project is for research replication only and does not constitute investment advice. The report and code are based on historical data. Practical use should still consider data quality, transaction costs, subscription/redemption constraints, portfolio capacity, and risk control.

## Navigation

- [Research Report](#1-research-report)
- [Method Overview](#2-method-overview)
- [Fund Universe and Portfolio Rules](#3-fund-universe-and-portfolio-rules)
- [Backtest Design](#4-backtest-design)
- [Post-2023 Performance Diagnosis and Fixes](#post-2023-performance-diagnosis-and-fixes)
- [Data System](#5-data-system)
- [Project Structure](#6-project-structure)
- [Environment Dependencies](#7-environment-dependencies)
- [Data Preparation Order](#8-data-preparation-order)
- [Main Workflow](#9-main-workflow)
- [Main Outputs](#10-main-outputs)
- [Differences Between the Report Methodology and Current Implementation](#11-differences-between-the-report-methodology-and-current-implementation)
- [Known Issues](#12-known-issues)
- [Replication Objectives](#13-replication-objectives)
- [References](#14-references)

## Quick Links

| Content | File |
|---|---|
| Main backtest program | [`fun_RR.ipynb`](./fun_RR.ipynb) |
| Single-window model prototype | [`RR.ipynb`](./RR.ipynb) |
| NAV trading-day alignment | [`navtotradeday.ipynb`](./navtotradeday.ipynb) |
| Full Chinese notebook summary | [`summary.md`](./summary.md) |
| Full English notebook summary | [`summary_EN.md`](./summary_EN.md) |
| Data structure inventory | [`data_schema.md`](./data_schema.md) |

## 1. Research Report

Replication basis:

- Report: `正则化基金评价季报20210703.pdf`
- Institution: Soochow Securities Research Institute
- Report date: 2021-07-03
- Topic: Regularized Fund Evaluation 2021Q3 Portfolio

The basic idea of the report is that because mutual funds disclose complete holdings at a low frequency, daily fund returns can be regressed on market, industry, and style factors with constraints. This allows the estimation of fund equity position, industry exposure, style exposure, and stock selection ability. To reduce overfitting in return-based regression, the report adds an L2 regularization term to style exposure and blends the regularized regression exposure equally with the actual style exposure calculated from the latest disclosed holdings.

The report also constructs quarterly fund portfolios based on stock selection ability, timing ability, and comprehensive score, and then tests the effectiveness of the evaluation indicators using next-quarter holding returns.

## 2. Method Overview

### 2.1 Return Attribution Model

Assuming that fund position, industry exposure, and style exposure remain stable within the lookback window, daily fund return can be expressed as:

$$
r_t =
\beta_m r_{m,t}
+ \sum_i \beta_i^{ind} r_{i,t}^{ind}
+ \sum_j \beta_j^{style} r_{j,t}^{style}
+ \alpha
+ \varepsilon_t
$$

where:

- `r_t`: daily fund return;
- `r_m,t`: market return, currently represented by CSI 300;
- `r_i,t^ind`: daily return of Shenwan Level-1 industries;
- `r_j,t^style`: daily return of Barra style factors;
- `beta_m`: fund equity position;
- `beta_i^ind`: industry exposure;
- `beta_j^style`: style exposure;
- `alpha + epsilon_t`: stock selection return not explained by market, industry, or style factors.

### 2.2 Constraints and Regularization

The current main workflow solves the following constrained quadratic programming problem:

$$
\min
\sum_t
\left(
r_t
- \beta_m r_{m,t}
- \sum_i \beta_i^{ind}r_{i,t}^{ind}
- \sum_j \beta_j^{style}r_{j,t}^{style}
- \alpha
\right)^2
+ \lambda \sum_j \left(\beta_j^{style}\right)^2
$$

subject to:

$$
0 \leq \beta_m \leq 1
$$

$$
0 \leq \beta_i^{ind} \leq 1
$$

$$
\sum_i \beta_i^{ind} = \beta_m
$$

The report fixes the regularization coefficient as:

$$
\lambda = 6 \times 10^{-5}
$$

The code follows this default value. The regularization term only penalizes style exposure. It does not directly penalize equity position, industry exposure, or alpha.

### 2.3 Blended Style Exposure Estimation

The report states that relying only on return-based regression to estimate style exposure can easily lead to overfitting. Although the latest semiannual or annual report holdings are lagged, the exposure estimates from holdings are more stable. Therefore, the final style exposure uses an equally weighted blend:

$$
\beta_j^{mix}
=
\frac{1}{2}\beta_j^{reg}
+
\frac{1}{2}\beta_j^{holding}
$$

In this project:

- `beta_j^reg` comes from regularized fund return regression with an L2 penalty;
- `beta_j^holding` is calculated using valid matched stocks for each factor:

$$
\beta_j^{holding}
=
\frac{
\sum_{k \in valid_j} w_k x_{k,j}
}{
\sum_{k \in valid_j} w_k
}
$$

- factor coverage is defined as the valid matched stock weight for a given factor divided by the total stock holding weight of the fund;
- the default coverage threshold is 85%;
- if coverage is below the threshold, the holding-based exposure for that factor is treated as missing;
- if holding exposure is valid, the final exposure uses 50% regression exposure and 50% holding exposure;
- if holding exposure is missing, the final exposure uses 100% regression exposure instead of treating the missing exposure as 0.

### 2.4 Stock Selection Ability

The model return is reconstructed using market exposure, industry exposure, and blended style exposure:

$$
\widehat r_t^{model}
=
\beta_m r_{m,t}
+ \sum_i \beta_i^{ind}r_{i,t}^{ind}
+ \sum_j \beta_j^{mix}r_{j,t}^{style}
$$

Stock selection return is defined as:

$$
u_t = r_t - \widehat r_t^{model}
$$

The current code uses the average value of `u_t` within the window as the fund’s stock selection ability:

$$
StockSelectionAbility = mean(u_t)
$$

The regression-estimated `alpha` is not added back into the model return. This is consistent with the idea of treating the unexplained part as stock selection return.

### 2.5 Timing Ability

The report explains timing ability as whether the fund manager can increase equity position when the market rises and reduce equity position when the market falls.

The current code uses the change in total stock holdings between the two most recent available semiannual or annual reports, multiplied by the cumulative CSI 300 return between the two report periods:

$$
TimingAbility
=
\left(
Holding_{latest} - Holding_{previous}
\right)
\times MarketReturn
$$

This is the specific implementation used in this project. The report presents the portfolio results and economic interpretation of timing ability, but the appendix of this report does not fully provide its calculation formula.

### 2.6 Comprehensive Ability

The code first converts stock selection ability and timing ability into percentile scores from 0 to 100, and then calculates the comprehensive score as an equal-weighted average:

$$
ComprehensiveScore
=
\frac{
StockSelectionScore + TimingScore
}{2}
$$

The report describes this as “timing score + stock selection score.” Using the average does not change the ranking of funds; it only changes the score scale.

## 3. Fund Universe and Portfolio Rules

The sample fund portfolio rules in the report are:

- active equity-oriented funds;
- fund size no less than RMB 100 million;
- ranking from high to low by stock selection ability, timing ability, or comprehensive ability;
- each fund manager can only be selected once;
- each fund company can have at most two selected funds;
- TOP15 sample portfolios are shown for each evaluation dimension;
- the complete FOF portfolio uses the top 10% funds by ability ranking.

The current `fun_RR.ipynb` has implemented:

- at least 120 fund observation days within the window;
- the fund has at least one record with asset size greater than RMB 100 million;
- separate rankings for stock selection, timing, and comprehensive ability;
- fund manager deduplication;
- at most two funds from the same fund company;
- three types of TOP15 portfolios;
- fund ability decile grouping and next-quarter return backtesting.

## 4. Backtest Design

The report forms fund evaluation results at each quarter end, holds the selected funds for the next quarter, and sells at the end of that quarter.

The current main workflow:

1. Uses the natural quarter end date or the nearest previous trading day as the window end date.
2. Takes the previous 120 trading days as the default regression window.
3. Forms stock selection, timing, and comprehensive ability rankings at the window end date.
4. Uses the last trading day on or before the next natural quarter end as the sell date.
5. Calculates each fund’s actual holding return using adjusted NAV.
6. Calculates decile returns and TOP15 portfolio average returns.
7. Connects quarterly decile returns into cumulative return curves.
8. For comprehensive score, calculates the quarterly long-short return as Group 1 minus Group 10 and summarizes win rate and average quarterly long-short return.

The report defines Group 10 as the highest-score group and Group 1 as the lowest-score group. The current code sorts in descending order and defines `decile == 1` as the highest-score group and `decile == 10` as the lowest-score group. Therefore, the group labels need to be reversed when comparing with the report charts, but the fund ranking and portfolio returns themselves are not affected.

## Post-2023 Performance Diagnosis and Fixes

Older versions of `outs.pkl` / `outs1.pkl` showed a clear reversal of stock selection ability after 2023:

- before 2023, the average cross-sectional Spearman correlation between stock selection ability and next-quarter return was about `+0.034`;
- after 2023, it was about `-0.138`;
- after 2023, the high-score Group 1 had an average next-quarter return of about `1.4%`, while the low-score Group 10 had about `5.9%`;
- timing ability did not show a reversal of the same magnitude.

Three fixes were made to fund returns, industry factors, and holding-based Barra exposure:

1. **Fund returns are recalculated by `PRICE_DATE`**  
   [`基金数据/NAVReturn.ipynb`](./基金数据/NAVReturn.ipynb) now reads the final trading-day panel and only overwrites `return`, while preserving other columns, row order, and column order. It uses `pct_change(fill_method=None)` and no longer fills the first or abnormal return values uniformly with 0.

2. **Completely broken industry factors are dynamically removed from regression**  
   `run_regularized_regression()` removes industries that have no valid observations within each window. For example, `采掘` automatically exits windows after 2022, while `煤炭` continues to participate.

3. **Holding-based Barra exposure is normalized by factor-level coverage**  
   Each style factor independently calculates matched weight and coverage. Exposure is divided by the valid matched weight of that factor. If coverage is below 85%, holding-based exposure is treated as missing, and the blending stage automatically falls back to regression exposure.

Current validation status:

- all three notebook modifications have passed syntax checks and targeted numerical tests;
- real industry data checks confirm that `采掘` is automatically removed after 2022;
- holding exposure tests confirm that exposure no longer mechanically shrinks toward 0 due to matching coverage;
- `NAVReturn.ipynb` still needs to be executed so that the official Feather file is refreshed;
- the full rolling backtest from 2009 to 2026 has not yet been rerun under the new methodology, so the performance numbers above are the pre-fix baseline, not post-fix results.

For the full explanation of modification reasons, original code, new code, and validation process, see [`summary.md`](./summary.md#7-2023-年后表现排查与三项修复).

## 5. Data System

The project mainly uses local files exported from Wind.

| Data Category | Main File | Purpose |
|---|---|---|
| Daily fund NAV | `基金数据/交易日偏股型基金.feather` | Fund returns, fund size, out-of-sample returns |
| Fund stock holdings | `基金数据/CHINAMUTUALFUNDSTOCKPORTFOLIO.feather` | Holding position, holding-based style exposure, timing ability |
| Fund manager | `基金数据/CHINAMUTUALFUNDMANAGER_202605221351(1).csv` | Fund manager matching and deduplication |
| Fund description | `基金数据/CHINAMUTUALFUNDDESCRIPTION_202606031717.csv` | Fund type, fund company, and basic fund information |
| Broad index returns | `宽基指数日行情/宽基指数收益率.csv` | Market factor, trading calendar, and cumulative market return |
| Shenwan industry returns | `申万一级行业/申万一级行业_with_dailyreturn.feather` | Industry factors |
| Barra style returns | `Barra_CNE5/Barra风格因子收益率.feather` | Regression style factors |
| Stock-level Barra exposure | `Barra_CNE5/*正交后.txt` | Real style exposure calculated from fund holdings |

The complete data file and notebook reference relationships are summarized in [`summary.md`](./summary.md).

## 6. Project Structure

```text
.
├── fun_RR.ipynb
├── RR.ipynb
├── navtotradeday.ipynb
├── summary.md
├── summary_EN.md
├── data_schema.md
├── 基金数据/
│   ├── Seperate_Fund.ipynb
│   ├── NAVReturn.ipynb
│   ├── 对齐数据日期.ipynb
│   └── FundNAV数据缺失查找汇报.ipynb
├── 宽基指数日行情/
│   └── Return_Summary.ipynb
├── 申万一级行业/
│   └── Return_Summary.ipynb
├── Barra_CNE5/
│   ├── SeperateBarraFactor.ipynb
│   └── *正交后.txt
├── Mapping/
│   └── mapping.ipynb
└── 备用数据/
