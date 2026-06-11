# Notebook Work Summary

> [Back to project README](./README.md) | [中文版](./summary.md)

> Scope: All 15 `.ipynb` files in the current project directory, cross-checked against `data_schema.md` and the data files in the repository.
> Summary date: 2026-06-10

## 1. What This Project Does

This directory implements a workflow for fund data cleaning, factor exposure estimation, fund capability evaluation, and rolling backtesting. Its main research universe consists of actively managed equity and equity-oriented hybrid funds.

The main workflow can be summarized as follows:

1. Convert the raw fund NAV CSV into Feather format and inspect its fields and missing values.
2. Identify fund types using Wind fund industry classifications and the fund description table, then isolate equity and equity-oriented hybrid funds.
3. Map fund NAV dates to broad-market index trading days and remove funds that cannot be reasonably aligned or contain excessively large trading-day gaps.
4. Recalculate fund returns from adjusted NAV by `PRICE_DATE` in the final trading-day panel, updating only the `return` column.
5. Generate daily return data for broad-market indices, Shenwan Level-1 industries, and Barra style factors.
6. Merge fund returns with market, industry, and style factors.
7. Use constrained regression with an L2 penalty to estimate equity allocation, industry exposures, style exposures, and alpha for each fund.
8. Calculate factor-by-factor renormalized holdings-based style exposures; combine valid holdings exposures equally with regression exposures and fall back to regression exposures when coverage is insufficient.
9. Calculate stock-selection, market-timing, and comprehensive capabilities, while enforcing fund-manager uniqueness and fund-company concentration limits.
10. Run the process quarterly and calculate next-quarter realized returns, decile returns, TOP15 portfolio returns, and cumulative return curves.
11. Calculate quarterly comprehensive-score long-short returns as the first decile minus the tenth decile, together with the win rate, average quarterly long-short return, and a bar chart.
12. Calculate quarterly IC, Rank IC, ICIR, annualized ICIR, and significance statistics for stock-selection, market-timing, and comprehensive scores.

In this project:

- `fun_RR_plus.ipynb` is the most complete notebook and the closest to a production research program.
- `fun_RR.ipynb` is retained as the legacy functionalized workflow for methodology and historical-result comparison.
- `RR.ipynb` is a step-by-step prototype for a single time window.
- The notebooks under `基金数据/`, `宽基指数日行情/`, `申万一级行业/`, and `Barra_CNE5/` primarily prepare input data.
- The various files named `test.ipynb` contain experiments, inspections, or temporary code rather than complete workflows.

## 2. Directory and Data Roles

| Directory/File | Primary Role |
|---|---|
| `基金数据/` | Cleaning and derived data for fund NAV, fund types, fund managers, and equity/bond/other holdings |
| `宽基指数日行情/` | Market data for six broad-market indices and a wide table of their daily returns |
| `申万一级行业/` | Shenwan Level-1 industry market data and a wide table of industry daily returns |
| `Barra_CNE5/` | Barra factor returns, style-factor exposures, and orthogonalized style-factor exposures |
| `Mapping/` | Trading-day-to-holdings-report-date mapping and Barra-to-Shenwan industry-name mapping |
| `备用数据/` | Large raw CSV files and basic read tests |
| `RR.ipynb` | Prototype for regression and capability evaluation over one time window |
| `fun_RR_plus.ipynb` | Current main workflow with revised timing capability and IC/Rank IC analysis |
| `fun_RR.ipynb` | Legacy functionalized workflow for multiple windows and quarterly rolling backtests |
| `navtotradeday.ipynb` | Aligns NAV dates with trading days and produces the daily fund panel used by the regression |
| `outs.pkl`, `outs1.pkl` | Serialized rolling-backtest results; `fun_RR.ipynb` explicitly writes `outs1.pkl` |

## 3. Notebook Overview

| Notebook | Main Work | Main Inputs | Main Outputs |
|---|---|---|---|
| `fun_RR_plus.ipynb` | Current RR regression, capability scoring, quarterly backtesting, and IC analysis | Daily fund panel, holdings, broad-market/industry/Barra factors, fund managers | `outs`, decile and TOP15 returns, long-short returns, and IC/Rank IC summaries and details |
| `fun_RR.ipynb` | Legacy functionalized RR regression and quarterly rolling backtest | Mostly the same inputs as the plus version | Historical-methodology `outs`, cumulative returns, and long-short analysis |
| `RR.ipynb` | Single-window regression prototype and capability calculation | Mostly the same inputs as the functionalized workflows | Regression exposures, holdings exposures, stock-selection capability, and manager-deduplicated TOP15 |
| `navtotradeday.ipynb` | Aligns fund NAV dates to the nearest trading day | Equity-oriented fund NAV and broad-market index returns | `基金数据/交易日偏股型基金.feather` |
| `基金数据/Seperate_Fund.ipynb` | Fund classification, NAV splitting, holdings classification, and fund-description enrichment | NAV, fund industry classifications, holdings CSV files, and fund description CSV | NAV files by fund type, holdings Feather files, and updated equity-oriented fund data |
| `基金数据/NAVReturn.ipynb` | Recalculates returns by `PRICE_DATE` in the final trading-day panel | `交易日偏股型基金.feather` | Updates only the `return` column in the same file |
| `基金数据/test.ipynb` | Converts NAV CSV to Feather and experiments with fund classification and date continuity | Raw NAV CSV, classification tables, and NAV Feather | `Mutual_Fund_Nav.feather`; most other work is diagnostic |
| `基金数据/对齐数据日期.ipynb` | Filters holdings report dates and generates availability dates | Equity and bond holdings Feather files | Overwrites both holdings Feather files |
| `基金数据/FundNAV数据缺失查找汇报.ipynb` | Diagnoses missing values in core NAV fields | `Fund_NAV.feather` | In-memory `nan_summary` |
| `宽基指数日行情/Return_Summary.ipynb` | Calculates daily returns for six broad-market indices | Six index Excel files | `宽基指数收益率.csv` |
| `申万一级行业/Return_Summary.ipynb` | Calculates daily returns for Shenwan Level-1 industries | Shenwan index daily-market CSV | `申万一级行业_with_dailyreturn.feather` |
| `Barra_CNE5/SeperateBarraFactor.ipynb` | Splits Barra returns into style, industry, and complete factor datasets | `BarraFactorReturn.txt` | Three Feather files |
| `Barra_CNE5/test.ipynb` | Tests reading the Barra factor-return file | `BarraFactorReturn.txt` | None |
| `Mapping/mapping.ipynb` | Builds trading-day/report-date and industry-name mappings | Legacy NAV and quarterly holdings | Two Feather/CSV mapping files |
| `备用数据/test.ipynb` | Tests reading the date column from the raw NAV CSV | `Mutual_Fund_Nav.csv` | None |

## 4. Detailed Notebook Descriptions

### 4.1 `fun_RR_plus.ipynb`

This is the current core notebook. It extends the functionalized workflow with a revised regression-position timing measure, manager-deduplication compatibility across pandas versions, and quarterly IC/Rank IC analysis.

Main modules:

- Defines `RRRawData` to store NAV, holdings, broad-market, industry, and Barra data in one object.
- `load_rr_data()` reads all required datasets once and standardizes their date formats.
- `prepare_rr_base_data()` prebuilds a reduced NAV table and a date-merged factor table to avoid repeated work across multiple windows.
- `build_rr_data()`:
  - Filters data to a specified time window.
  - Retains funds with at least 120 fund dates in the window and at least one positive `1M` flag.
  - Expands fund dates to the factor trading-day calendar.
  - Fills missing returns using the average of surrounding values, followed by forward and backward filling.
  - Calculates fill ratios and removes funds whose fill ratio exceeds 5%.
- `run_regularized_regression()` estimates the following for each fund:
  - Equity allocation, `stock_exposure`.
  - Exposures to 32 Shenwan industries.
  - Exposures to 10 Barra style factors.
  - `alpha`.
- Before regression, industry factors with no valid observations anywhere in the current window are removed dynamically. For example, `采掘` is removed from post-2021 windows while the still-active `煤炭` series remains.
- Regression constraints:
  - Equity allocation must remain within `[0, 1]`.
  - Each industry exposure must remain within `[0, 1]`.
  - The sum of industry exposures must equal the equity allocation.
  - Only style exposures receive an L2 penalty, with a default coefficient of `6e-5`.
- `compute_holding_style_exposure()`:
  - Selects the latest available semiannual or annual holdings report before `end_date`.
  - Selects the nearest available Barra exposure date on or before `end_date`.
  - Matches valid stocks separately for every Barra style factor.
  - Renormalizes each holdings exposure by that factor's valid matched weight.
  - Retains `{factor}_coverage` and `{factor}_matched_weight_sum`.
  - Sets the holdings exposure to missing when factor coverage is below 85% by default.
- `compute_stock_selection_ability()`:
  - Uses 50% regression and 50% holdings exposure when the holdings exposure is valid.
  - Falls back entirely to the regression exposure when the holdings exposure is missing because coverage is insufficient.
  - Reconstructs model returns from market, industry, and mixed style exposures.
  - Defines stock-selection capability as the average of actual fund returns minus model returns.
- `compute_timing_ability()`:
  - Runs a traditional Treynor-Mazuy quadratic regression independently from the stock-selection attribution regression.
  - Includes only an intercept, market return, and squared market return.
  - Re-estimates `tm_alpha`, `tm_beta`, and `gamma` by ordinary least squares.
  - Uses no industry or Barra style factors, exposure constraints, or regularization.
  - Leaves `gamma` unconstrained and uses it as `timing_ability`.
  - Solves funds in parallel using `joblib.Parallel` and the `loky` backend.
- Converts stock-selection and market-timing capabilities into percentile scores and calculates an equally weighted comprehensive score.
- Fund-selection rules require:
  - No repeated fund managers.
  - Removal of funds with missing manager or fund-company information.
  - No more than two selected funds from the same fund company.
  - Separate TOP15 selections for stock-selection, market-timing, and comprehensive capability.
- `run_rr_window()`:
  - Runs the complete process for one window.
  - Uses the last trading day before the end of the following calendar quarter as the sell date.
  - Calculates realized fund returns over the next quarter.
  - Divides funds into 10 groups based on capability rankings.
  - Produces decile-average returns and TOP15 average returns.
- `make_quarterly_rolling_windows()` creates quarter-end rolling windows, with a default lookback of 120 trading days.
- `run_rr_windows()` runs all windows in batch.
- `compute_quarterly_ic_ir()` independently calculates Pearson IC between capability values and next-quarter realized returns. It returns the cross-quarter summary by default and optionally returns quarterly IC details with `keep_intermediate=True`.
- `compute_quarterly_rank_ic_ir()` independently ranks capability and return values before calculating Pearson correlation. It returns mean Rank IC and Rank ICIR summaries by default and can optionally retain quarterly details.
- Both summaries include the mean correlation, sample standard deviation, IR, annualized IR, positive-correlation ratio, and t statistic.
- Manager IDs produced by pandas aggregation are normalized and accepted as tuples, lists, ndarrays, or Series before manager deduplication.
- The example covers `2009-06-30` through `2026-03-31` and keeps the results in the in-memory `outs` dictionary.
- `build_decile_cum_return()` links decile returns across periods into cumulative return series and plots cumulative returns for stock-selection, market-timing, and comprehensive capability.
- `build_comprehensive_long_short_return()`:
  - Extracts average returns for the first and tenth deciles from each window's `comprehensive_decile_result`.
  - Calculates each quarterly long-short return as `first-decile average return - tenth-decile average return`.
  - Retains both decile sample counts, quarter validity, and win/loss status.
  - Uses only quarters with valid returns for both deciles when calculating the win rate and average quarterly long-short return.
  - Draws a quarterly long-short bar chart and returns the detail table, summary dictionary, and Matplotlib axes object.

Referenced data:

**Directly read**

- `基金数据/交易日偏股型基金.feather`
- `基金数据/CHINAMUTUALFUNDSTOCKPORTFOLIO.feather`
- `宽基指数日行情/宽基指数收益率.csv`
- `申万一级行业/申万一级行业_with_dailyreturn.feather`
- `Barra_CNE5/Barra风格因子收益率.feather`
- `基金数据/CHINAMUTUALFUNDMANAGER_202605221351(1).csv`
- `Barra_CNE5/Beta正交后.txt`
- `Barra_CNE5/BooktoPrice正交后.txt`
- `Barra_CNE5/EarningYield正交后.txt`
- `Barra_CNE5/Growth正交后.txt`
- `Barra_CNE5/Leverage正交后.txt`
- `Barra_CNE5/Liquidity正交后.txt`
- `Barra_CNE5/Momentum正交后.txt`
- `Barra_CNE5/NonlinearSize正交后.txt`
- `Barra_CNE5/ResidualVolatility正交后.txt`
- `Barra_CNE5/Size正交后.txt`

The plus version does not write a pickle by default. Callers should use a distinct filename for revised-methodology results rather than overwriting legacy `outs.pkl` or `outs1.pkl`.

The legacy [`fun_RR.ipynb`](./fun_RR.ipynb) remains available for comparison with the previous disclosed-holdings timing definition and historical backtests.

### 4.2 `RR.ipynb`

This is the step-by-step prototype for the functionalized workflows, using a fixed example window from `2020-06-30` to `2021-06-29`.

Main work:

- Reads fund, holdings, broad-market, Shenwan industry, and Barra style-return data.
- Contains a set of commented-out data-quality inspection functions.
- Selects funds with at least 120 dates and at least one record with assets exceeding CNY 100 million.
- Completes fund dates using the broad-market index trading calendar and forward-fills missing observations.
- Merges market, industry, and style factors, then removes funds whose fill ratio exceeds 5%.
- Runs constrained regularized regression for each fund using CVXPY and ECOS.
- Calculates holdings-based style exposures using the latest available holdings and 10 orthogonalized Barra files.
- Equally combines holdings-based and regression-based style exposures to calculate stock-selection capability.
- Matches active fund managers as of `end_date`; if no active manager exists, it uses the most recent prior management record.
- Sorts funds by stock-selection capability and selects a TOP15 after removing repeated fund managers.

The referenced data is largely the same as in the functionalized workflows, but this notebook does not write a result file.

### 4.3 `navtotradeday.ipynb`

This notebook aligns fund NAV `PRICE_DATE` values to broad-market index trading days and generates the formal regression input.

Main rules:

- Retains only data on or after `2002-01-04`.
- If a fund has duplicate records on the same original date, keeps the last record.
- Matches each fund date to the nearest broad-market trading day, preferring the previous trading day when the distances are equal.
- Allows a maximum shift of seven calendar days and removes records beyond that limit.
- If alignment creates duplicate fund/trading-day records, it prioritizes rows with fewer missing fields and smaller date shifts.
- Checks for missing broad-market trading days during each fund's observed lifetime.
- Uses trading-day sequence numbers to calculate the number of missing trading days between adjacent fund observations.
- Removes an entire fund if it contains any interval with more than seven missing trading days.

Referenced data:

**Read**

- `基金数据/股票型_偏股混合型_nav.feather`
- `宽基指数日行情/宽基指数收益率.csv`

**Written**

- `基金数据/交易日偏股型基金.feather`

### 4.4 `基金数据/Seperate_Fund.ipynb`

This is the main notebook for fund classification and basic fund-data preparation. It contains several distinct processing steps that were added over time.

Main work:

- Uses the fund industry-definition table and fund classification-membership table, concatenating several Chinese and English description fields and applying regular expressions to classify funds.
- Categories include FOF, passive index, ETF, LOF, QDII, money market, bond, equity, hybrid, and unknown funds.
- The primary classification priority is FOF, ETF, LOF, QDII, money market, bond, equity, hybrid, and unknown.
- Merges classification results into the long-format NAV table and saves separate NAV files by fund type.
- Forward-fills fund assets in `交易日偏股型基金.feather` and adds `1M = F_PRT_NETASSET > 1e8`.
- Maps fund classifications to other, equity, and bond holdings tables, adding `fund_type` and `is_equity_fund`.
- Identifies funds present in NAV but absent from all three holdings files, excluding funds that first appeared on or after 2026-02-01.
- Revalidates the fund universe using the fund description table:
  - Retains only funds whose `F_INFO_FIRSTINVESTTYPE` is `股票型` or `混合型`.
  - Adds the fund company field `fund_com`.
  - Adds or refreshes `F_INFO_TYPE`.

Referenced data:

**Read**

- `Mutual_Fund_Nav.feather`
- `ASHAREINDUSTRIESCODE_202605221326.csv`
- `CHINAMUTUALFUNDSECTOR_202605221321.csv`
- `交易日偏股型基金.feather`
- `CMFOTHERPORTFOLIO_202605200918.csv`
- `CHINAMUTUALFUNDSTOCKPORTFOLIO_202605190939.csv`
- `CHINAMUTUALFUNDBONDPORTFOLIO_202605200915.csv`
- `股票型_偏股混合型_nav.feather`
- `CHINAMUTUALFUNDDESCRIPTION_202606031717.csv`

**Written**

- `ETF_nav.feather`
- `FOF_nav.feather`
- `股票型_偏股混合型_nav.feather`
- `其他混合型_nav.feather`
- `债券型_nav.feather`
- `QDII_nav.feather`
- `货币基金_nav.feather`
- `其他未知_nav.feather`
- `CMFOTHERPORTFOLIO.feather`
- `CHINAMUTUALFUNDSTOCKPORTFOLIO.feather`
- `CHINAMUTUALFUNDBONDPORTFOLIO.feather`
- Overwrites and updates `交易日偏股型基金.feather`

### 4.5 `基金数据/NAVReturn.ipynb`

Main work:

- Reads the final regression input, `交易日偏股型基金.feather`.
- Uses a reduced temporary table and performs a stable sort by fund code and `PRICE_DATE`.
- Treats zero adjusted NAV values as missing only in the calculation copy; the original `F_NAV_ADJUSTED` column is not modified.
- Calculates `return` with `pct_change(fill_method=None)`; first observations and non-computable returns remain missing.
- Restores the original row order and updates only the `return` column.
- Checks row count, column names, and column order before replacing the formal file through a temporary Feather file.
- The notebook code has been updated, but as of June 8, 2026 it has not yet been executed to overwrite the formal Feather file.

Referenced data:

- Read with only `return` updated: `交易日偏股型基金.feather`

### 4.6 `基金数据/test.ipynb`

This is an experimental notebook for fund-data processing. Its cells do not form one complete sequential workflow.

Included work:

- Uses chunked reading and PyArrow to convert the large `Mutual_Fund_Nav.csv` file into `Mutual_Fund_Nav.feather`.
- Removes several unnecessary fields and explicitly defines data types.
- Removes records with missing `ANN_DATE` and converts the field to an integer.
- Experiments with the fund industry-classification functions.
- Inspects NAV data for specific fund codes.
- Contains NAV date-continuity diagnostic code that depends on variables created elsewhere.

Referenced data:

- `Mutual_Fund_Nav.csv`
- `Mutual_Fund_Nav.feather`
- `ASHAREINDUSTRIESCODE_202605221326.csv`
- `CHINAMUTUALFUNDSECTOR_202605221321.csv`
- `股票型_偏股混合型_nav.feather`

### 4.7 `基金数据/对齐数据日期.ipynb`

Main work:

- Processes equity and bond holdings Feather files.
- Converts `F_PRT_ENDDATE` to a date.
- Retains only June 30 semiannual reports and December 31 annual reports.
- Assigns estimated availability dates:
  - Semiannual reports: August 31 of the same year.
  - Annual reports: March 31 of the following year.
- Adds `available_date` and overwrites the original files.
- Inspects equity holdings records where `available_date` is missing.

Referenced and overwritten:

- `CHINAMUTUALFUNDBONDPORTFOLIO.feather`
- `CHINAMUTUALFUNDSTOCKPORTFOLIO.feather`

### 4.8 `基金数据/FundNAV数据缺失查找汇报.ipynb`

This notebook reads `Fund_NAV.feather` and calculates the following for 12 core NAV fields:

- Overall missing-value ratio.
- Missing-value ratio by year.
- Years in which the missing-value ratio exceeds 90%.
- A status of `Acceptable (early missing)` or `Needs cleaning`, depending on whether highly missing years exist.

It only creates the in-memory table `nan_summary` and does not write a file.

### 4.9 `宽基指数日行情/Return_Summary.ipynb`

This notebook processes the following six index Excel files:

- `上证50.xlsx`
- `中证500.xlsx`
- `中证800指数行情.xlsx`
- `中证1000.xlsx`
- `创业板指数.xlsx`
- `沪深300.xlsx`

Main work:

- Reads Excel files using `python-calamine`.
- Sorts the data by date.
- Calculates daily returns for each index using `pct_change()` on closing prices.
- Names each return column using the index name followed by `dailyreturn`.
- Outer-joins the series by date into a wide table and fills missing values with zero.
- Writes `宽基指数收益率.csv`.
- Additionally checks the first nonzero return date for each column and inspects a specified row.

### 4.10 `申万一级行业/Return_Summary.ipynb`

Main work:

- Reads `ASWSINDEXEOD_202605210941.csv`.
- Uses a fixed dictionary to select 32 Shenwan Level-1 industry codes.
- Sorts by industry and date and calculates daily returns from closing prices.
- Pivots the data into a wide table with one date per row and one industry per column.
- Writes `申万一级行业_with_dailyreturn.feather`.

### 4.11 `Barra_CNE5/SeperateBarraFactor.ipynb`

Main work:

- Reads `BarraFactorReturn.txt`, whose actual format is Feather despite the `.txt` extension.
- Identifies the 10 style factors.
- Treats all remaining non-date columns as industry factors.
- Separately saves style-factor returns, industry-factor returns, and the complete factor-return table.

Outputs:

- `Barra风格因子收益率.feather`
- `Barra行业因子收益率.feather`
- `Barra因子收益率.feather`

### 4.12 `Barra_CNE5/test.ipynb`

This notebook only reads `BarraFactorReturn.txt` and displays its first few rows to verify that the file can be read successfully using `pd.read_feather()`.

### 4.13 `Mapping/mapping.ipynb`

This notebook contains the following mappings:

1. Extracts trading days from a legacy NAV dataset and saves them as `trading_days.feather`.
2. Backward-matches each trading day to the most recent quarterly holdings date and saves the result as `交易日_持仓日期映射.feather`.
3. Manually constructs a mapping from Barra industry names to Shenwan Level-1 industry names and saves it as `行业名称映射表.csv`.

Referenced data:

- `基金数据/开放式基金_NAV_clean.feather`
- `基金数据/开放式基金_StockHold_quarterly.feather`
- `trading_days.feather`

The first two absolute-path files use legacy dataset names and are no longer used directly by the current main workflow.

### 4.14 `备用数据/test.ipynb`

This notebook only reads `Mutual_Fund_Nav.csv` and displays the first few values of `ANN_DATE`. It is the simplest raw-data read test in the project.

## 5. Data Dependency Chain

The main derivation relationships are:

```text
备用数据/Mutual_Fund_Nav.csv
    -> 基金数据/Mutual_Fund_Nav.feather
    -> Fund-type identification and splitting
    -> 基金数据/股票型_偏股混合型_nav.feather
    -> Align with broad-market trading days and remove funds with large gaps
    -> 基金数据/交易日偏股型基金.feather
    -> Recalculate return by PRICE_DATE, updating only return

Broad-market index Excel files
    -> 宽基指数日行情/宽基指数收益率.csv

Shenwan index daily-market CSV
    -> 申万一级行业/申万一级行业_with_dailyreturn.feather

Barra_CNE5/BarraFactorReturn.txt
    -> Barra风格因子收益率.feather
    -> Barra行业因子收益率.feather
    -> Barra因子收益率.feather

Raw holdings CSV files
    -> Equity/bond/other holdings Feather files
    -> Semiannual/annual report filtering and available_date

Daily fund panel + broad-market returns + industry returns + Barra style returns
    -> Constrained regularized regression

Equity holdings + orthogonalized stock-level Barra exposures
    -> Holdings-based style exposures

Regression exposures + holdings exposures + fund managers + fund companies
    -> Stock-selection/market-timing/comprehensive capabilities
    -> TOP15 and next-quarter decile backtests
    -> Comprehensive-score first-minus-tenth-decile quarterly long-short return, win rate, and mean
```

## 6. Key Methodological Definitions

- Fund return: Percentage change in `F_NAV_ADJUSTED` after sorting each fund by `PRICE_DATE` in the final trading-day panel, without automatically filling missing NAV values.
- Market factor: `沪深300dailyreturn`.
- Industry factors: Daily returns of Shenwan Level-1 industries.
- Style factors: Returns of 10 Barra style factors.
- Regression equity allocation: Constrained between 0 and 1.
- Industry exposures: Nonnegative, individually no greater than 1, and summing to the equity allocation.
- Style exposures: No range constraints, but subject to an L2 penalty.
- Holdings-based style exposure: For each factor, `sum(weight * exposure) / sum(valid matched weight)`, using only stocks with a non-missing exposure for that factor.
- Holdings factor coverage: Valid matched stock weight divided by total disclosed stock-holding weight; the holdings exposure is missing when coverage is below 85% by default.
- Stock-selection capability: Average residual after subtracting market, industry, and mixed-style model returns from actual fund returns; regression alpha is not included.
- Market-timing capability: The unconstrained `gamma` coefficient from an independent traditional TM quadratic regression.
- Comprehensive capability: Equal-weighted average of the percentile scores for stock-selection and market-timing capability.
- IC: Quarterly Pearson correlation between capability values and next-quarter realized fund returns.
- Rank IC: Pearson correlation after separately ranking capability values and next-quarter returns.
- ICIR: Mean quarterly IC divided by its sample standard deviation; annualized quarterly ICIR equals `ICIR × sqrt(4)`.
- IC t statistic: `mean_ic / (std_ic / sqrt(valid_quarter_count))`.
- Comprehensive-score quarterly long-short return: The current code assigns the highest score to the first decile and the lowest score to the tenth decile, so the return is `first-decile average return - tenth-decile average return`.
- Long-short win rate: Among quarters with valid returns for both deciles, the share whose long-short return is strictly greater than zero; incomplete quarters are excluded from the denominator.
- Average long-short return: Arithmetic mean of `first-decile average return - tenth-decile average return` across valid quarters only.
- TOP15: No repeated managers and no more than two funds from the same fund company.
- Out-of-sample return: Buy at the window end date and sell on the last trading day before the end of the following calendar quarter.

## 7. Post-2023 Performance Investigation and Three Repairs

### 7.1 Investigation Background and Current Status

The legacy `outs.pkl` and `outs1.pkl` results showed a material reversal in stock-selection performance after 2023:

- Before 2023, the average cross-sectional Spearman correlation between stock-selection capability and next-quarter return was approximately `+0.034`.
- From 2023 onward, the average correlation was approximately `-0.138`.
- After 2023, the highest-scored first decile earned approximately `1.4%` on average in the next quarter, while the lowest-scored tenth decile earned approximately `5.9%`.
- Market-timing capability did not show a reversal of comparable magnitude, concentrating the investigation on fund returns, industry regression inputs, and holdings-based style exposures.

The review focused on processing assumptions originally validated mainly on the 2009-2022 sample. Three repairs have been implemented. Current status:

- All three notebook code changes are complete.
- Notebook JSON, Python syntax, real-data industry-window checks, and focused numerical tests passed.
- `NAVReturn.ipynb` has not yet been executed to overwrite the formal Feather file.
- The full 2009-2026 rolling backtest has not yet been rerun with all three repairs.
- The performance figures above are the pre-repair problem baseline, not a claim about repaired investment performance.

### 7.2 Repair One: Recalculate Fund Returns by `PRICE_DATE`

**Reason for the change**

The legacy `NAVReturn.ipynb` sorted observations by announcement date, `ANN_DATE`, while the main regression aligned returns with factors by NAV date, `PRICE_DATE`. This could attach a NAV change to the wrong factor-return date. In 2023, approximately 4.57% of observations differed from a `PRICE_DATE` recalculation, and the correlation between the two return series was approximately 0.743.

**Previous code**

```python
nav = pd.read_feather("股票型_偏股混合型_nav.feather")
nav["ANN_DATE"] = pd.to_datetime(nav["ANN_DATE"].astype(str))
nav = nav.sort_values(["F_INFO_WINDCODE", "ANN_DATE"])
nav["F_NAV_ADJUSTED"] = nav["F_NAV_ADJUSTED"].replace(0, np.nan)
nav["return"] = (
    nav.groupby("F_INFO_WINDCODE")["F_NAV_ADJUSTED"]
       .pct_change()
)
nav["return"] = nav["return"].fillna(0)
nav.reset_index().to_feather("股票型_偏股混合型_nav.feather")
```

This also modified the working NAV column, converted all missing or invalid returns to zero, and could alter row order and file structure through sorting and `reset_index()`.

**Revised code**

```python
data_path = Path("交易日偏股型基金.feather")
nav = pd.read_feather(data_path)

original_columns = nav.columns.tolist()
original_row_count = len(nav)

return_work = nav[
    ["F_INFO_WINDCODE", "PRICE_DATE", "F_NAV_ADJUSTED"]
].copy()
return_work["_row_position"] = np.arange(len(return_work))
return_work["_price_date_parsed"] = pd.to_datetime(
    return_work["PRICE_DATE"], errors="coerce"
)
return_work["_nav_for_return"] = pd.to_numeric(
    return_work["F_NAV_ADJUSTED"], errors="coerce"
).replace(0, np.nan)

return_work = return_work.sort_values(
    ["F_INFO_WINDCODE", "_price_date_parsed", "_row_position"],
    kind="stable",
)
return_work["_new_return"] = (
    return_work.groupby(
        "F_INFO_WINDCODE", sort=False
    )["_nav_for_return"]
    .pct_change(fill_method=None)
    .replace([np.inf, -np.inf], np.nan)
)

nav["return"] = (
    return_work.sort_values("_row_position")["_new_return"]
    .reset_index(drop=True)
    .to_numpy()
)
```

The notebook writes a temporary Feather file, validates row count and the complete ordered schema, and only then atomically replaces the formal file:

```python
nav.to_feather(temp_path)
saved_dataset = ds.dataset(temp_path, format="feather")

if saved_dataset.count_rows() != original_row_count:
    raise RuntimeError("Row count changed after saving")
if saved_dataset.schema.names != original_columns:
    raise RuntimeError("Column structure changed after saving")

os.replace(temp_path, data_path)
```

**Unchanged behavior**

- Every column other than `return`.
- Original row count, row order, and column order.
- Original `F_NAV_ADJUSTED` values.
- The way `fun_RR_plus.ipynb` reads the formal trading-day panel.

**Validation result**

- Notebook JSON and all code cells passed syntax checks.
- In-memory assertions protect row count and column order.
- Feather metadata is checked again before replacement.
- The formal data file will not change until the notebook is actually executed.

### 7.3 Repair Two: Dynamically Remove Fully Discontinued Industry Factors

**Reason for the change**

The Shenwan `采掘` return series ends on December 10, 2021, while the newer `煤炭` series continues. The legacy code filled the discontinued series with zero after 2021, retained a corresponding optimization variable, and included that variable in the constraint requiring industry exposures to sum to equity exposure.

**Previous code**

```python
industry_factors = list(industry_factors)
factor_cols = style_factors + industry_factors
regression_data[factor_cols] = (
    regression_data[factor_cols]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0.0)
)
```

**Revised code**

```python
requested_industry_factors = list(industry_factors)
industry_numeric = regression_data[
    requested_industry_factors
].apply(pd.to_numeric, errors="coerce")

industry_factors = [
    factor
    for factor in requested_industry_factors
    if industry_numeric[factor].notna().any()
]
dropped_industry_factors = [
    factor
    for factor in requested_industry_factors
    if factor not in industry_factors
]

if not industry_factors:
    raise ValueError("No industry factor is available in this window")

regression_data = regression_data.drop(
    columns=dropped_industry_factors
)
factor_cols = style_factors + industry_factors
regression_data[factor_cols] = (
    regression_data[factor_cols]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0.0)
)
```

**Unchanged behavior**

- Function name, parameters, and calling convention of `run_regularized_regression()`.
- The global candidate list, `INDUSTRY_FACTORS`.
- Equity-exposure and industry-exposure constraints.
- Style L2 regularization and default `lambda_style=6e-5`.
- The dictionary structure of `industry_exposure`.
- Downstream expansion still produces a zero exposure column for an industry omitted from a particular regression window.

**Validation result**

Real-data window checks produced:

```text
2021-07-01 to 2021-12-31: both 采掘 and 煤炭 are active
2022-01-01 to 2022-06-30: only 煤炭 remains
2023-01-01 to 2023-06-30: only 煤炭 remains
```

A synthetic regression test confirmed that a fully discontinued factor does not create a CVXPY exposure variable and that the downstream output remains structurally compatible.

### 7.4 Repair Three: Renormalize Holdings-Based Barra Exposure by Factor Coverage

**Reason for the change**

The legacy implementation calculated `sum(weight * exposure)` directly. When some holdings could not be matched to a particular Barra factor, those stocks were omitted from the sum, which was economically equivalent to assigning them zero factor exposure. The resulting holdings exposure mechanically shrank toward zero as coverage declined. Real-data checks showed matched holding-weight coverage falling from approximately 94% in 2022 to approximately 86% in 2025.

**Previous code**

```python
weighted[factor_name] = (
    weighted["holding_weight"]
    * weighted[factor_name]
)
factor_exposure = (
    weighted.groupby(sh_fund_col, as_index=False)[factor_name]
    .sum()
)
```

**Revised code**

The default threshold is:

```python
HOLDING_FACTOR_COVERAGE_THRESHOLD = 0.85
```

The optional parameter is appended to the function, so existing calls remain valid:

```python
def compute_holding_style_exposure(
    raw_data,
    rr_data,
    end_date,
    fold=DEFAULT_FOLD,
    style_factor_files=STYLE_FACTOR_FILES,
    verbose=True,
    coverage_threshold=HOLDING_FACTOR_COVERAGE_THRESHOLD,
):
```

Each factor is matched independently:

```python
factor_long = factor_long.dropna(subset=[factor_name])
weighted = holding_snapshot.merge(
    factor_long,
    on=stock_col,
    how="inner",
)
weighted["_weighted_factor_exposure"] = (
    weighted["holding_weight"] * weighted[factor_name]
)

factor_stats = (
    weighted.groupby(sh_fund_col, as_index=False)
    .agg(
        weighted_exposure_sum=(
            "_weighted_factor_exposure", "sum"
        ),
        matched_factor_weight=(
            "holding_weight", "sum"
        ),
    )
)
```

Coverage and renormalized exposure are calculated as:

```python
factor_stats[coverage_col] = (
    factor_stats["matched_factor_weight"]
    / factor_stats["holding_stock_weight_sum"]
)
factor_stats[factor_name] = (
    factor_stats["weighted_exposure_sum"]
    / factor_stats["matched_factor_weight"]
)
factor_stats.loc[
    factor_stats[coverage_col].lt(coverage_threshold),
    factor_name,
] = np.nan
```

New diagnostic columns include:

```text
Beta_coverage
Beta_matched_weight_sum
BooktoPrice_coverage
BooktoPrice_matched_weight_sum
...
Size_coverage
Size_matched_weight_sum
```

The mixing step no longer treats a missing holdings exposure as zero:

```python
mix_style_exposure[mix_col] = np.where(
    mix_style_exposure[holding_col].notna(),
    (
        mix_style_exposure[reg_col]
        + mix_style_exposure[holding_col]
    ) / 2.0,
    mix_style_exposure[reg_col],
)
```

Therefore:

```text
Valid holdings exposure: 50% regression + 50% holdings
Invalid holdings exposure: 100% regression
```

**Unchanged behavior**

- Existing function names and calling conventions.
- Holdings weights still use `F_PRT_STKVALUETONAV / 100`.
- Latest-report and Barra-date selection logic.
- The 50%/50% structure when holdings exposure is valid.
- Return-value count and existing style-exposure column names.
- The legacy `matched_stock_weight_sum` field remains for downstream compatibility.

The holdings path currently covers ten stock-level Barra style factors only. Industry exposures still come from return regression; no stock-level holdings industry exposure was added.

**Validation result**

Focused numerical tests confirmed:

- At 100% coverage, exposure equals the full weighted average of valid stocks.
- At 90% coverage, exposure is divided by the 90% valid weight and no longer shrinks to 90% of its economic value.
- At 60% coverage, holdings exposure becomes `NaN`.
- When holdings exposure is `NaN`, mixed exposure falls back exactly to regression exposure.
- Existing positional argument order remains compatible.
- The holdings Barra exposure function contains no `fillna(0)`.

### 7.5 Required Execution Order After the Repairs

Because `NAVReturn.ipynb` now updates the final trading-day panel:

1. Run `navtotradeday.ipynb` to generate `基金数据/交易日偏股型基金.feather`.
2. Run `基金数据/NAVReturn.ipynb` to recalculate only `return` by `PRICE_DATE`.
3. Restart or rerun `load_rr_data()` in `fun_RR_plus.ipynb` so no stale in-memory returns remain.
4. Run a single-window diagnostic.
5. Rerun the complete quarterly rolling backtest and build new `outs`.
6. Call `build_comprehensive_long_short_return(outs)` to generate quarterly comprehensive-score long-short details, win rate, average return, and chart.
7. Save the repaired results under a distinct pickle name until they have been reviewed against the pre-repair files.

## 8. Issues Worth Noting

1. `fun_RR_plus.ipynb` is the most complete current version. `fun_RR.ipynb` and `RR.ipynb` are retained as the legacy workflow and prototype, so future maintenance should prioritize the plus version.
2. The Markdown in `navtotradeday.ipynb` still refers to `ANN_DATE`, while the code actually processes `PRICE_DATE`. Some comments also retain an old `5d` name even though the current parameter is seven days.
3. `NAVReturn.ipynb` now uses `PRICE_DATE`, but the formal Feather file changes only after the notebook is actually executed.
4. `fun_RR_plus.ipynb` still fills missing fund returns using surrounding-return averages followed by forward and backward filling. This can duplicate returns and introduce future information.
5. Partial missing values in otherwise active industry factors are still filled with zero; only factors that are entirely missing within a window are removed automatically.
6. Holdings reports are still selected using one market-wide latest report period rather than a per-fund fallback to each fund's latest available report.
7. Holdings weights come from the report date, while stock-level Barra exposures are still taken from the latest date before evaluation, creating potential timing mismatch.
8. `Seperate_Fund.ipynb` can return `Passive Index Fund`, but that category is not fully represented in the priority and output branches.
9. The `unknown_nav` logic does not include rows explicitly labeled `Other/Unknown`.
10. Multiple notebooks overwrite Feather files, so execution order affects final results.
11. `Mapping/mapping.ipynb` uses legacy absolute paths and is not required by the current main workflow.
12. Barra files with a `.txt` suffix are actually stored in Feather format.
13. A comment in `fun_RR_plus.ipynb` mentions threading, while fund regression uses the `loky` multiprocessing backend.
14. The project still lacks automated tests and a fully reproducible one-command pipeline.

## 9. Recommended Execution Order

1. `基金数据/test.ipynb`: Convert the raw NAV CSV to Feather.
2. `基金数据/Seperate_Fund.ipynb`: Classify funds and split the data.
3. `宽基指数日行情/Return_Summary.ipynb`: Generate market returns.
4. `申万一级行业/Return_Summary.ipynb`: Generate industry returns.
5. `Barra_CNE5/SeperateBarraFactor.ipynb`: Split Barra factor returns.
6. `基金数据/对齐数据日期.ipynb`: Process holdings availability dates.
7. `navtotradeday.ipynb`: Generate the trading-day-aligned equity-oriented fund panel.
8. `基金数据/NAVReturn.ipynb`: Recalculate only `return` by `PRICE_DATE` in the final panel.
9. `fun_RR_plus.ipynb`: Reload the data, run rolling regression and capability backtesting, and generate long-short, IC, Rank IC, and ICIR results.
