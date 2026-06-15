# Regularized Fund Evaluation Replication

> [Chinese README](./README.md) | [Chinese notebook summary](./summary.md) | [English notebook summary](./summary_EN.md)

This project replicates the fund-evaluation framework in the Soochow Securities financial-engineering report *Regularized Fund Evaluation 2021Q3 Portfolio* dated July 3, 2021. It extends the original framework with data cleaning, constrained regularized regression, holdings-based exposure blending, fund capability scoring, quarterly selection, and out-of-sample backtesting.

The main research universe consists of actively managed equity funds and equity-oriented hybrid funds. The current primary workflow is [`fun_RR_plus.ipynb`](./fun_RR_plus.ipynb). The legacy [`fun_RR.ipynb`](./fun_RR.ipynb) is retained for methodology comparison.

> This repository is for research replication only and is not investment advice. Historical backtests do not account fully for transaction costs, subscriptions/redemptions, capacity, liquidity, or operational constraints.

## Quick Links

| Item | File |
|---|---|
| Current main workflow | [`fun_RR_plus.ipynb`](./fun_RR_plus.ipynb) |
| Legacy workflow | [`fun_RR.ipynb`](./fun_RR.ipynb) |
| Single-window prototype | [`RR.ipynb`](./RR.ipynb) |
| NAV trading-day alignment | [`navtotradeday.ipynb`](./navtotradeday.ipynb) |
| Chinese notebook summary | [`summary.md`](./summary.md) |
| English notebook summary | [`summary_EN.md`](./summary_EN.md) |
| Data schema | [`data_schema.md`](./data_schema.md) |

## 1. Method Overview

### 1.1 Return Attribution

Fund daily returns are modeled as:

$$
r_t =
\beta_m r_{m,t}
+ \sum_i \beta_i^{ind} r_{i,t}^{ind}
+ \sum_j \beta_j^{style} r_{j,t}^{style}
+ \alpha
+ \varepsilon_t
$$

where:

- `r_t` is the fund return.
- `r_m,t` is the market return, currently represented by CSI 300.
- `r_i,t^ind` is a Shenwan Level-1 industry return.
- `r_j,t^style` is a Barra style-factor return.
- `beta_m` is the estimated equity allocation.
- `beta_i^ind` and `beta_j^style` are industry and style exposures.

### 1.2 Constraints and Regularization

The regression minimizes squared residuals plus an L2 penalty on style exposures:

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

The default regularization coefficient is `6e-5`.

### 1.3 Mixed Style Exposure

When holdings coverage is sufficient, the final style exposure is:

$$
\beta_j^{mix}
=
0.5\beta_j^{reg}
+ 0.5\beta_j^{holding}
$$

Holdings exposure is calculated separately for each factor using only stocks with valid factor exposure:

$$
\beta_j^{holding}
=
\frac{\sum_{k \in valid_j} w_k x_{k,j}}
{\sum_{k \in valid_j} w_k}
$$

The default minimum factor coverage is 85%. If coverage is insufficient, the model uses 100% regression exposure instead of treating missing holdings exposure as zero.

### 1.4 Stock-Selection Capability

Model returns are reconstructed from market, industry, and mixed style exposures:

$$
\widehat r_t^{model}
=
\beta_m r_{m,t}
+ \sum_i \beta_i^{ind}r_{i,t}^{ind}
+ \sum_j \beta_j^{mix}r_{j,t}^{style}
$$

Stock-selection capability is the average unexplained return:

$$
StockSelectionAbility
=
mean(r_t-\widehat r_t^{model})
$$

### 1.5 Market-Timing and Comprehensive Capability

The current timing measure is the unconstrained `gamma` from an independent Treynor-Mazuy regression:

$$
r_t
=
\alpha_{TM}
+ \beta_{m,TM}r_{m,t}
+ \gamma r_{m,t}^{2}
+ \varepsilon_t
$$

Stock-selection and timing capabilities are converted to percentile scores. Their equal-weighted average forms the comprehensive score.

## 2. Fund Selection Rules

The current workflow applies the following rules:

- At least 120 observed fund dates in the regression window.
- At least one record with net assets above CNY 100 million.
- Separate rankings for stock-selection, timing, and comprehensive capability.
- No repeated fund manager in a selected TOP15 portfolio.
- No more than two selected funds from the same fund company.
- Separate TOP15 portfolios for the three capability dimensions.

The enhanced performance analysis described below applies only to the stock-selection ranking.

## 3. Quarterly Backtest

For each quarter:

1. Use the latest trading day on or before the natural quarter end as the formation date.
2. Use a default 120-trading-day regression lookback.
3. Form capability rankings at the formation date.
4. Use the last available trading day on or before the end of the following natural quarter as the sell date.
5. Calculate realized returns from adjusted fund NAV.
6. Calculate decile returns and the manager-deduplicated TOP15 return.
7. Link returns using the actual sell date to build cumulative NAV curves.

The code sorts capabilities in descending order:

- `decile == 1` is the highest-ranked group.
- `decile == 10` is the lowest-ranked group.

## 4. Stock-Selection Performance Analysis

### 4.1 TOP15 Backtest

The stock-selection TOP15 analysis includes:

- Quarterly TOP15 return.
- Cumulative TOP15 NAV.
- Annualized return.
- Annualized volatility.
- Maximum drawdown.
- Information ratio versus `885001.WI`.

### 4.2 Decile Backtest

The stock-selection decile analysis includes:

- Quarterly returns for deciles 1 through 10.
- Cumulative NAV for every decile.
- First-decile-minus-tenth-decile long-short return.
- Cumulative long-short NAV.
- Unified performance metrics for every decile and the long-short portfolio.

Individual deciles use `885001.WI` as the information-ratio benchmark. The long-short portfolio uses a zero-return benchmark.

### 4.3 TOP15 Excess-Return Backtest

The benchmark file is:

```text
基金数据/885001.WI.xlsx
```

It contains the Wind Equity-Oriented Hybrid Fund Index. Benchmark returns are calculated using the latest available closing value on or before each actual buy and sell date.

Arithmetic quarterly excess return is:

$$
ExcessReturn_t
=
r_{TOP15,t}-r_{Benchmark,t}
$$

Cumulative relative NAV is:

$$
RelativeNAV_T
=
\frac{\prod_{t=1}^{T}(1+r_{TOP15,t})}
{\prod_{t=1}^{T}(1+r_{Benchmark,t})}
$$

The analysis reports excess-return win rate, average quarterly excess return, annualized relative return, annualized volatility, maximum drawdown, and information ratio.

### 4.4 Quarterly and Monthly Long-Short Win Rates

Quarterly stock-selection long-short return is:

$$
LongShortReturn_q
=
MeanReturn_{q,decile\,1}
- MeanReturn_{q,decile\,10}
$$

For monthly analysis, decile membership is fixed at the quarter's formation date. Returns are then calculated over each full calendar month in the holding quarter. No intra-quarter reranking is performed.

## 5. Performance Metric Definitions

All unified performance metrics use quarterly returns and `periods_per_year = 4`.

### Annualized Return

$$
AnnualizedReturn
=
EndingNAV^{4/N}-1
$$

### Annualized Volatility

$$
AnnualizedVolatility
=
Std(r_q)\sqrt{4}
$$

### Maximum Drawdown

Maximum drawdown is the minimum cumulative-NAV decline from its historical peak. The initial NAV of `1.0` is included in the running peak.

### Information Ratio

$$
InformationRatio
=
\frac{Mean(ActiveReturn_q)}
{Std(ActiveReturn_q)}
\sqrt{4}
$$

TOP15 and individual deciles use `885001.WI` as the benchmark. The first-minus-tenth long-short portfolio uses zero return as the benchmark.

## 6. Verified Results

The following results were verified using 66 quarterly holding periods in the current `outs.pkl`:

| Stock-Selection Strategy | Annualized Return | Annualized Volatility | Maximum Drawdown | Information Ratio |
|---|---:|---:|---:|---:|
| TOP15 | 11.90% | 20.80% | -35.76% | 0.52 |
| TOP15 relative NAV versus 885001.WI | 4.12% | 8.31% | -12.97% | 0.52 |
| First decile minus tenth decile | 3.95% | 7.61% | -16.22% | 0.55 |

The monthly long-short backtest contains:

- 198 valid months.
- 122 positive months.
- 61.62% monthly win rate.
- 0.368% average monthly long-short return.

These figures describe the current local data and implementation. They are not expected to match the report's static historical portfolio exactly.

## 7. Running the Main Workflow

Restart the notebook kernel before a full rerun, then execute all cells in [`fun_RR_plus.ipynb`](./fun_RR_plus.ipynb).

Load shared data once:

```python
raw_data = load_rr_data()
manager_data = load_manager_data()
```

Create quarterly windows:

```python
windows = make_quarterly_rolling_windows(
    global_start_date="2009-06-30",
    global_end_date="2026-03-31",
    raw_data=raw_data,
    lookback_trading_days=120,
)
```

Run the rolling backtest:

```python
outs = run_rr_windows(
    windows,
    raw_data=raw_data,
    manager_data=manager_data,
    keep_intermediate=False,
    verbose=False,
)
```

The notebook then builds the decile, TOP15, benchmark-relative, quarterly long-short, monthly long-short, and performance-summary outputs.

## 8. Result Variables

### Performance Summaries

```python
# TOP15 metrics
stock_top15_performance_summary

# Deciles 1-10 and first-minus-tenth metrics
stock_decile_performance_summary

# TOP15 excess-return metrics and win rate
stock_top15_excess_summary

# Quarterly and monthly long-short statistics
stock_selection_long_short_summary
stock_selection_monthly_long_short_summary
```

### Period Details

```python
stock_top15_cum
stock_decile_cum
stock_top15_excess
stock_selection_long_short
stock_selection_monthly_long_short
```

### Cumulative Curves

```python
stock_top15_cum_pivot
stock_decile_cum_pivot
stock_top15_excess_cum_pivot
```

### Chart Objects

```python
stock_top15_ax
stock_selection_long_short_ax
stock_selection_monthly_long_short_ax
```

The same calls are listed in the notebook appendix under the result-access section.

## 9. Main Data Files

| Data | File | Use |
|---|---|---|
| Daily fund panel | `基金数据/交易日偏股型基金.feather` | Regression, fund size, realized return |
| Equity holdings | `基金数据/CHINAMUTUALFUNDSTOCKPORTFOLIO.feather` | Holdings-based style exposure |
| Fund managers | `基金数据/CHINAMUTUALFUNDMANAGER_202605221351(1).csv` | Manager matching and deduplication |
| Fund descriptions | `基金数据/CHINAMUTUALFUNDDESCRIPTION_202606031717.csv` | Fund type and company |
| Broad-market returns | `宽基指数日行情/宽基指数收益率.csv` | Market factor and trading calendar |
| Shenwan industries | `申万一级行业/申万一级行业_with_dailyreturn.feather` | Industry factors |
| Barra style returns | `Barra_CNE5/Barra风格因子收益率.feather` | Style factors |
| TOP15 benchmark | `基金数据/885001.WI.xlsx` | Excess returns and information ratio |

## 10. Repository Structure

```text
.
├── README.md
├── READ_EN.md
├── summary.md
├── summary_EN.md
├── data_schema.md
├── fun_RR_plus.ipynb
├── fun_RR.ipynb
├── RR.ipynb
├── navtotradeday.ipynb
├── 基金数据/
├── 宽基指数日行情/
├── 申万一级行业/
├── Barra_CNE5/
├── Mapping/
└── 备用数据/
```

## 11. Known Limitations

- Missing fund returns in the regression panel may still be filled using surrounding-return averages followed by forward and backward filling, which can duplicate returns and introduce future information.
- Transaction costs, subscriptions/redemptions, capacity, and implementation frictions are not fully modeled.
- Fund-manager and fund-company metadata can be incomplete and may remove otherwise eligible funds.
- Holdings data are disclosed with a lag.
- Data in the repository extend beyond the report's original 2021 sample, so fund counts and TOP15 selections will differ.
- `outs.pkl` is a serialized local result object and should be regenerated whenever upstream data or methodology changes.

## 12. References

- Soochow Securities Research Institute, *Regularized Fund Evaluation 2021Q3 Portfolio*, July 3, 2021.
- Wind fund NAV, holdings, manager, description, index, and factor data exported to local files.

