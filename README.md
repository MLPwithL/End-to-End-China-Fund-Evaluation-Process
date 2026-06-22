# 正则化基金评价复现

> [English README](./READ_EN.md) | [中文总结](./summary.md) | [English summary](./summary_EN.md)

本项目用于复现东吴证券金融工程报告《正则化基金评价 2021Q3 组合》（2021 年 7 月 3 日）中的基金评价框架，并在此基础上实现数据清洗、正则化回归、持仓暴露融合、基金能力评分、季度滚动选基和样本外回测。

项目的核心研究对象是主动股票型及偏股混合型公募基金。当前主要入口为 [`fun_RR_plus.ipynb`](./fun_RR_plus.ipynb)，旧版 [`fun_RR.ipynb`](./fun_RR.ipynb) 保留用于口径对照；各数据准备 notebook、字段说明和完整文件盘点见 [`summary.md`](./summary.md)。

> 本项目是研究复现，不构成投资建议。报告与代码均基于历史数据，实际使用仍需考虑数据质量、交易成本、申赎限制、组合容量和风险控制。

## 导航

- [研究报告](#1-研究报告)
- [方法概述](#2-方法概述)
- [基金池与组合规则](#3-基金池与组合规则)
- [回测设计](#4-回测设计)
- [2023 年后表现排查与修复](#2023-年后表现排查与修复)
- [数据体系](#5-数据体系)
- [项目结构](#6-项目结构)
- [环境依赖](#7-环境依赖)
- [数据准备顺序](#8-数据准备顺序)
- [运行主流程](#9-运行主流程)
- [主要输出](#10-主要输出)
- [报告口径与当前实现的差异](#11-报告口径与当前实现的差异)
- [当前已知问题](#12-当前已知问题)
- [复现目标](#13-复现目标)
- [参考资料](#14-参考资料)

## 快速入口

| 内容 | 文件 |
|---|---|
| 当前主回测程序 | [`fun_RR_plus.ipynb`](./fun_RR_plus.ipynb) |
| 旧版主流程 | [`fun_RR.ipynb`](./fun_RR.ipynb) |
| 单窗口模型原型 | [`RR.ipynb`](./RR.ipynb) |
| NAV 交易日对齐 | [`navtotradeday.ipynb`](./navtotradeday.ipynb) |
| English README | [`READ_EN.md`](./READ_EN.md) |
| 全部 notebook 中文总结 | [`summary.md`](./summary.md) |
| 全部 notebook 英文总结 | [`summary_EN.md`](./summary_EN.md) |
| 数据结构盘点 | [`data_schema.md`](./data_schema.md) |

## 1. 研究报告

复现依据：

- 报告：`正则化基金评价季报20210703.pdf`
- 发布机构：东吴证券研究所
- 报告日期：2021-07-03
- 报告主题：正则化基金评价 2021Q3 组合

报告的基本思想是：由于公募基金完整持仓披露频率较低，使用基金日收益率对市场、行业和风格因子进行带约束回归，从而估计基金的股票仓位、行业暴露、风格暴露和选股能力。为降低收益率回归的过拟合风险，报告对风格暴露加入 L2 正则项，并将正则化回归暴露与最新披露持仓计算出的真实风格暴露等权混合。

报告还根据选股能力、择时能力和综合得分构造季度基金组合，并通过下一季度持有收益检验评价指标的有效性。

## 2. 方法概述

### 2.1 收益率归因模型

假设在回看窗口内基金仓位、行业暴露和风格暴露保持稳定，基金日收益可以表示为：

$$
r_t =
\beta_m r_{m,t}
+ \sum_i \beta_i^{ind} r_{i,t}^{ind}
+ \sum_j \beta_j^{style} r_{j,t}^{style}
+ \alpha
+ \varepsilon_t
$$

其中：

- `r_t`：基金日收益率；
- `r_m,t`：市场收益率，当前实现使用沪深 300；
- `r_i,t^ind`：申万一级行业日收益率；
- `r_j,t^style`：Barra 风格因子日收益率；
- `beta_m`：基金股票仓位；
- `beta_i^ind`：行业暴露；
- `beta_j^style`：风格暴露；
- `alpha + epsilon_t`：模型无法由市场、行业和风格解释的选股收益。

### 2.2 约束与正则化

当前主流程求解以下带约束的二次规划：

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

约束条件为：

$$
0 \leq \beta_m \leq 1
$$

$$
0 \leq \beta_i^{ind} \leq 1
$$

$$
\sum_i \beta_i^{ind} = \beta_m
$$

报告将正则化系数固定为：

$$
\lambda = 6 \times 10^{-5}
$$

代码沿用了这一默认值。正则项只约束风格暴露，不直接惩罚股票仓位、行业暴露或 alpha。

### 2.3 风格暴露的混合估计

报告指出，单纯依赖收益率回归估计风格暴露容易过拟合，而最新半年报或年报持仓虽然存在滞后，但暴露估计更稳定。因此最终风格暴露采用等权混合：

$$
\beta_j^{mix}
=
\frac{1}{2}\beta_j^{reg}
+
\frac{1}{2}\beta_j^{holding}
$$

项目中：

- `beta_j^reg` 来自带 L2 正则项的基金收益率回归；
- `beta_j^holding` 对每个因子分别使用有效匹配股票计算：

$$
\beta_j^{holding}
=
\frac{
\sum_{k \in valid_j} w_k x_{k,j}
}{
\sum_{k \in valid_j} w_k
}
$$

- 因子覆盖率定义为该因子有效匹配股票权重除以基金全部股票持仓权重；
- 默认覆盖率阈值为 85%，低于阈值时该因子的持仓暴露记为缺失；
- 持仓暴露有效时继续使用 50% 回归暴露与 50% 持仓暴露；
- 持仓暴露缺失时使用 100% 回归暴露，不把缺失暴露当成 0。

### 2.4 选股能力

使用市场、行业和混合风格暴露重构基金模型收益：

$$
\widehat r_t^{model}
=
\beta_m r_{m,t}
+ \sum_i \beta_i^{ind}r_{i,t}^{ind}
+ \sum_j \beta_j^{mix}r_{j,t}^{style}
$$

选股收益为：

$$
u_t = r_t - \widehat r_t^{model}
$$

当前代码以窗口内 `u_t` 的平均值作为基金选股能力：

$$
StockSelectionAbility = mean(u_t)
$$

这里没有把回归得到的 `alpha` 再加入模型收益，与报告将无法解释部分视为选股收益的思路一致。

### 2.5 择时能力

报告对择时能力的直观解释是：基金经理能否在市场上涨时提高仓位、下跌时降低仓位。

当前 `fun_RR_plus.ipynb` 使用第二次、完全独立的传统 Treynor-Mazuy 回归计算择时能力：

$$
r_t
=
\alpha_{TM}
+ \beta_{m,TM}r_{m,t}
+ \gamma r_{m,t}^{2}
+ \varepsilon_t
$$

其中 $\gamma$ 为择时能力。该回归与原选股归因回归分开执行，只使用基金收益、市场收益及市场收益平方项，不加入行业或 Barra 风格因子，也不施加暴露约束和正则项。`tm_alpha`、`tm_beta` 和 $\gamma$ 通过普通最小二乘法独立估计。各基金通过 `joblib.Parallel` 并行求解，随后将 `timing_ability = gamma` 转为 0 至 100 的百分位分数并排序。

### 2.6 综合能力

代码先将选股能力与择时能力分别转换为 0 至 100 的百分位分数，再等权计算综合得分：

$$
ComprehensiveScore
=
\frac{
StockSelectionScore + TimingScore
}{2}
$$

报告写作“择时分 + 选股分”。使用平均值不会改变基金排序，只改变得分尺度。

## 3. 基金池与组合规则

报告中的样本基金组合规则为：

- 主动偏股型基金；
- 基金规模不低于 1 亿元；
- 按选股、择时或综合能力从高到低排序；
- 同一基金经理只入选一次；
- 同一家基金公司最多入选两只基金；
- 每个评价维度展示 TOP15 样本组合；
- 完整 FOF 组合使用能力排名最高的 10% 基金。

当前 `fun_RR_plus.ipynb` 已实现：

- 全局剔除 `基金数据/暂停申赎基金20260622.xlsx` 中列出的暂停申赎基金；
- 窗口内至少 120 个基金观测日；
- 基金存在资产规模大于 1 亿元的记录；
- 选股、择时和综合能力分别排名；
- 基金经理去重；
- 单家基金公司最多两只；
- 三类 TOP15 组合；
- 基金能力十分组及下一季度收益回测；
- 针对选股能力排名的 TOP15、十分组和 TOP15 相对 `885001.WI` 超额收益回测；
- 选股能力十分组第一组减第十组的季度、多月度收益和胜率；
- 年化收益、年化波动率、最大回撤和信息比率的统一绩效统计。

## 4. 回测设计

报告按每个季度末的基金评价结果进行分组，在下一季度持有一个季度，并在季末卖出。

当前主流程：

1. 以自然季度末当日或之前最近交易日作为窗口结束日。
2. 默认向前取 120 个交易日作为回归窗口。
3. 在窗口结束日形成选股、择时和综合能力排名。
4. 使用下一自然季度末当日或之前的最后一个交易日作为卖出日。
5. 根据复权净值计算各基金实际持有收益。
6. 分别计算十分组收益和 TOP15 组合平均收益。
7. 使用实际卖出日连接各季度收益，生成累计净值曲线。
8. 针对选股能力十分组计算 `第一组 - 第十组` 的季度多空收益、季度胜率和月度胜率；月度计算固定季度初分组名单。
9. 从 `基金数据/885001.WI.xlsx` 读取万得偏股混合型基金指数，计算 TOP15 的季度超额收益和累计超额净值。
10. 对选股能力 TOP15、十分组各组、十分组多空和 TOP15 超额回测统一计算年化收益、年化波动率、最大回撤和信息比率。

报告规定第十组为最高分组、第一组为最低分组。当前代码按降序排列后将 `decile == 1` 定义为最高分组、`decile == 10` 定义为最低分组。因此比较报告图表时需要反转分组编号，但基金排序与组合收益本身不受影响。

## 2023 年后表现排查与修复

旧版 `outs.pkl` / `outs1.pkl` 显示选股能力在 2023 年后出现明显反转：

- 2023 年前，选股能力与下一季度收益的平均横截面 Spearman 相关约为 `+0.034`；
- 2023 年后约为 `-0.138`；
- 2023 年后高分第一组下一季度平均收益约为 `1.4%`，低分第十组约为 `5.9%`；
- 择时能力没有出现同等幅度的反转。

针对基金收益、行业因子和持仓 Barra 暴露完成了三项修复：

1. **基金收益按 `PRICE_DATE` 重算**  
   [`基金数据/NAVReturn.ipynb`](./基金数据/NAVReturn.ipynb) 现在读取最终交易日面板，只覆盖 `return`，保持其他列、行序和列顺序不变。使用 `pct_change(fill_method=None)`，不再把首条和异常收益统一填成 0。

2. **完全断档行业动态退出回归**  
   `run_regularized_regression()` 会在每个窗口内剔除完全没有有效观测的行业。例如 `采掘` 在 2022 年后的窗口自动退出，而 `煤炭` 继续参与。

3. **持仓 Barra 暴露按逐因子覆盖率归一化**  
   每个风格因子独立计算匹配权重和覆盖率，暴露除以该因子的有效匹配权重。覆盖率低于 85% 时持仓暴露为缺失，混合阶段自动退回回归暴露。

当前验证状态：

- 三项 notebook 修改均通过语法和针对性数值测试；
- 真实行业数据检查确认 2022 年后自动剔除 `采掘`；
- 持仓暴露测试确认不会再随匹配覆盖率机械向 0 收缩；
- `NAVReturn.ipynb` 尚需实际执行，正式 Feather 才会刷新；
- 当前 `outs.pkl` 已用于验证 66 个季度持有期；绩效结果见下文“选股能力绩效分析”。

完整的修改原因、原代码、新代码和验证过程见 [`summary.md`](./summary.md#7-2023-年后表现排查与三项修复)。

## 5. 数据体系

项目使用的数据主要来自 Wind 导出的本地文件。

| 数据类别 | 当前主要文件 | 用途 |
|---|---|---|
| 基金日频 NAV | `基金数据/交易日偏股型基金.feather` | 基金收益率、基金规模、样本外收益 |
| 暂停申赎基金名单 | `基金数据/暂停申赎基金20260622.xlsx` | `load_rr_data()` 全局剔除不可申赎基金 |
| 基金股票持仓 | `基金数据/CHINAMUTUALFUNDSTOCKPORTFOLIO.feather` | 持仓风格暴露 |
| 基金经理 | `基金数据/CHINAMUTUALFUNDMANAGER_202605221351(1).csv` | 基金经理匹配和去重 |
| 基金描述 | `基金数据/CHINAMUTUALFUNDDESCRIPTION_202606031717.csv` | 基金类型、基金公司和基金基本信息 |
| 宽基指数收益 | `宽基指数日行情/宽基指数收益率.csv` | 市场因子、交易日历和市场累计收益 |
| 偏股基金基准 | `基金数据/885001.WI.xlsx` | TOP15 超额收益、跟踪误差和信息比率 |
| 申万行业收益 | `申万一级行业/申万一级行业_with_dailyreturn.feather` | 行业因子 |
| Barra 风格收益 | `Barra_CNE5/Barra风格因子收益率.feather` | 回归风格因子 |
| 个股 Barra 暴露 | `Barra_CNE5/*正交后.txt` | 从基金持仓计算真实风格暴露 |

完整数据文件与 notebook 引用关系见 [`summary.md`](./summary.md)。

## 6. 项目结构

```text
.
├── fun_RR_plus.ipynb
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
```

核心文件：

- [`fun_RR_plus.ipynb`](./fun_RR_plus.ipynb)：当前函数化、多窗口滚动回测主程序，包含新择时能力、IC/Rank IC 和经理去重兼容修复。
- [`fun_RR.ipynb`](./fun_RR.ipynb)：旧版函数化主流程，保留用于结果和口径对照。
- [`RR.ipynb`](./RR.ipynb)：单窗口逐步骤原型，适合查看模型构建过程。
- [`navtotradeday.ipynb`](./navtotradeday.ipynb)：基金 NAV 日期与交易日对齐。
- [`基金数据/Seperate_Fund.ipynb`](./基金数据/Seperate_Fund.ipynb)：基金分类与基础数据整理。
- [`基金数据/NAVReturn.ipynb`](./基金数据/NAVReturn.ipynb)：基金收益率计算。
- [`基金数据/对齐数据日期.ipynb`](./基金数据/对齐数据日期.ipynb)：持仓披露日期处理。
- [`宽基指数日行情/Return_Summary.ipynb`](./宽基指数日行情/Return_Summary.ipynb)：宽基指数收益率生成。
- [`申万一级行业/Return_Summary.ipynb`](./申万一级行业/Return_Summary.ipynb)：申万行业收益率生成。
- [`Barra_CNE5/SeperateBarraFactor.ipynb`](./Barra_CNE5/SeperateBarraFactor.ipynb)：Barra 因子收益率拆分。
- [`summary.md`](./summary.md)：全部 15 个 notebook 的工作和数据引用明细。
- [`data_schema.md`](./data_schema.md)：早期数据盘点和字段说明，部分文件名已经过时。

## 7. 环境依赖

代码当前主要在 Python 3.9 环境下运行。

主要第三方依赖：

```text
pandas
numpy
pyarrow
cvxpy
joblib
scipy
python-calamine
matplotlib
jupyter
```

回归求解器：

- `fun_RR_plus.ipynb` 默认使用 CVXPY 的 `OSQP`；
- `RR.ipynb` 原型使用 `ECOS`；
- 各 notebook 的求解器配置并不完全相同，正式批量运行应以 `fun_RR_plus.ipynb` 为准。

### 并行参数 `n_jobs`

`fun_RR_plus.ipynb` 使用 `joblib.Parallel` 对不同基金的回归任务进行并行计算，当前默认参数为：

```python
n_jobs = 14
```

`14` 是根据开发机器的 CPU 核心数手动设置的工程参数，不是基金评价模型的理论参数。它只影响运行速度、CPU 占用和内存消耗，不改变回归目标函数、正则化系数或理论结果。

使用者应根据自己的 CPU 核心数和可用内存调整：

```python
n_jobs = -1  # 使用全部可用 CPU 核心
n_jobs = 8   # 最多同时运行 8 个任务
n_jobs = 1   # 关闭并行，适合调试和排查错误
```

当前并行后端为 `loky`，属于多进程后端。设置 `n_jobs=-1` 可以充分使用 CPU，但多个进程会增加内存占用；当基金面板较大或机器内存有限时，建议使用固定值，并预留部分 CPU 核心和内存给操作系统及其他程序。

一般可参考：

- CPU 和内存充足：使用 `n_jobs=-1`。
- 日常批量回测：使用接近 CPU 逻辑核心数、但略有预留的固定值。
- 内存不足或系统响应明显变慢：降低 `n_jobs`。
- 调试求解器或定位单只基金错误：使用 `n_jobs=1`。

## 8. 数据准备顺序

如果需要从原始文件重新生成所有中间数据，建议按以下顺序执行：

1. [`基金数据/test.ipynb`](./基金数据/test.ipynb)：将原始 NAV CSV 转为 Feather。
2. [`基金数据/Seperate_Fund.ipynb`](./基金数据/Seperate_Fund.ipynb)：识别基金类型、拆分基金 NAV、处理持仓和基金描述信息。
3. [`宽基指数日行情/Return_Summary.ipynb`](./宽基指数日行情/Return_Summary.ipynb)：生成宽基指数日收益率。
4. [`申万一级行业/Return_Summary.ipynb`](./申万一级行业/Return_Summary.ipynb)：生成申万一级行业日收益率。
5. [`Barra_CNE5/SeperateBarraFactor.ipynb`](./Barra_CNE5/SeperateBarraFactor.ipynb)：拆分 Barra 风格和行业因子收益率。
6. [`基金数据/对齐数据日期.ipynb`](./基金数据/对齐数据日期.ipynb)：筛选半年报/年报持仓并生成 `available_date`。
7. [`navtotradeday.ipynb`](./navtotradeday.ipynb)：将基金日期映射到交易日并生成正式基金日频面板。
8. [`基金数据/NAVReturn.ipynb`](./基金数据/NAVReturn.ipynb)：在正式面板中按 `PRICE_DATE` 仅重算 `return`。
9. [`fun_RR_plus.ipynb`](./fun_RR_plus.ipynb)：重新加载数据后运行单窗口或季度滚动评价与回测。

部分 notebook 会直接覆盖 Feather 文件。重新运行前应确认执行顺序，并为重要中间数据保留备份。

## 9. 运行主流程

在 `fun_RR_plus.ipynb` 中先加载一次基础数据和基金经理数据：

```python
raw_data = load_rr_data()
manager_data = load_manager_data()
```

### 单窗口

```python
out = run_rr_window(
    start_date="2020-06-30",
    end_date="2021-06-30",
    raw_data=raw_data,
    manager_data=manager_data,
    keep_intermediate=True,
)
```

### 季度滚动

```python
windows = make_quarterly_rolling_windows(
    global_start_date="2009-06-30",
    global_end_date="2026-03-31",
    raw_data=raw_data,
    lookback_trading_days=120,
)

outs = run_rr_windows(
    windows,
    raw_data=raw_data,
    manager_data=manager_data,
    keep_intermediate=False,
    verbose=False,
)
```

### 选股能力十分组与 TOP15 回测

```python
stock_decile_cum, stock_decile_cum_pivot = build_decile_cum_return(
    outs,
    decile_key="decile_result",
    include_long_short=True,
)

stock_top15_cum, stock_top15_cum_pivot = build_top15_cum_return(
    outs,
    return_key="top15_return",
)
```

累计收益日期使用每个窗口的实际 `summary["sell_date"]`，不再使用组合形成日。

### TOP15 相对 885001.WI 超额回测

```python
benchmark_885001 = load_benchmark_885001()
stock_top15_excess, stock_top15_excess_cum_pivot = (
    build_top15_excess_return(
        outs,
        benchmark_data=benchmark_885001,
    )
)
```

单期超额收益为 `TOP15 收益 - 基准收益`；累计超额净值采用：

$$
RelativeNAV_T
=
\frac{\prod_{t=1}^{T}(1+r_{TOP15,t})}
{\prod_{t=1}^{T}(1+r_{Benchmark,t})}
$$

### 选股能力十分组多空收益

$$
LongShortReturn_q
=
MeanReturn_{q, decile 1}
-
MeanReturn_{q, decile 10}
$$

```python
(
    stock_selection_long_short,
    stock_selection_long_short_summary,
    stock_selection_long_short_ax,
) = build_stock_selection_long_short_return(outs)

(
    stock_selection_monthly_long_short,
    stock_selection_monthly_long_short_summary,
    stock_selection_monthly_long_short_ax,
) = build_decile_monthly_long_short_win_rate(
    outs,
    nav_data=raw_data.nav,
    fund_return_key="fund_return",
)
```

季度多空使用每季初固定的选股能力第一组和第十组；月度回测在该季度内保持名单不变，按完整自然月计算多空收益和胜率。

### 统一绩效指标

所有绩效统计按季度频率计算：

$$
AnnualizedReturn = NAV_T^{4/N} - 1
$$

$$
AnnualizedVolatility = Std(r_q) \times \sqrt{4}
$$

最大回撤从初始净值 `1.0` 开始计算。信息比率定义为主动收益均值除以跟踪误差后乘 `sqrt(4)`；TOP15 和十分组各组相对 `885001.WI`，多空组合相对零收益基准。

```python
# TOP15
stock_top15_performance_summary

# 十分组第1至第10组及第一组减第十组
stock_decile_performance_summary

# TOP15超额回测
stock_top15_excess_summary

# 十分组多空季度和月度胜率
stock_selection_long_short_summary
stock_selection_monthly_long_short_summary
```

当前 `outs.pkl` 的 66 期验证结果：

| 选股能力策略 | 年化收益 | 年化波动率 | 最大回撤 | 信息比率 |
|---|---:|---:|---:|---:|
| TOP15 | 11.90% | 20.80% | -35.76% | 0.52 |
| TOP15 相对 885001.WI 超额净值 | 4.12% | 8.31% | -12.97% | 0.52 |
| 十分组第一组减第十组 | 3.95% | 7.61% | -16.22% | 0.55 |

十分组多空月度回测包含 198 个有效月份，其中 122 个月为正，月度胜率为 61.62%，平均月度多空收益为 0.368%。

## 10. 主要输出

每个窗口的结果字典主要包含：

| 结果键 | 内容 |
|---|---|
| `stock_selection_ability` | 基金选股能力及百分位得分 |
| `timing_ability` | 基金择时能力及百分位得分 |
| `comprehensive_ability` | 选股与择时等权综合得分 |
| `top15_unique_manager` | 选股能力 TOP15 |
| `top15_timing_unique_manager` | 择时能力 TOP15 |
| `top15_comprehensive_unique_manager` | 综合能力 TOP15 |
| `fund_return` | 选股能力排序对应的下一季度实际收益 |
| `timing_fund_return` | 择时能力排序对应的下一季度实际收益 |
| `comprehensive_fund_return` | 综合能力排序对应的下一季度实际收益 |
| `decile_result` | 选股能力十分组收益 |
| `timing_decile_result` | 择时能力十分组收益 |
| `comprehensive_decile_result` | 综合能力十分组收益 |
| `top15_return` | 选股 TOP15 下一季度平均收益 |
| `timing_top15_return` | 择时 TOP15 下一季度平均收益 |
| `comprehensive_top15_return` | 综合 TOP15 下一季度平均收益 |
| `summary` | 当前窗口日期、基金数量、持仓期、收益和耗时等汇总 |

滚动窗口全部完成后，选股能力回测额外生成：

| 输出变量 | 内容 |
|---|---|
| `stock_top15_performance_summary` | TOP15 年化收益、年化波动率、最大回撤、信息比率和期末净值 |
| `stock_decile_performance_summary` | 十分组第 1 至第 10 组及多空组合的统一绩效指标 |
| `stock_top15_excess_summary` | TOP15 超额胜率、平均超额收益和统一绩效指标 |
| `stock_top15_excess` | TOP15、885001.WI、单期超额收益和累计超额净值明细 |
| `stock_selection_long_short` | 选股能力十分组季度多空收益明细 |
| `stock_selection_long_short_summary` | 季度/月度胜率和多空组合绩效指标 |
| `stock_selection_monthly_long_short` | 固定季度初名单的逐月多空收益明细 |
| `stock_selection_monthly_long_short_summary` | 有效月份、获胜月份、月度胜率和平均月度收益 |
| `stock_decile_cum_pivot` | 十分组及多空组合累计净值曲线数据 |
| `stock_top15_excess_cum_pivot` | TOP15、885001.WI 和累计超额净值曲线数据 |

当 `keep_intermediate=True` 时还会保留：

- `rr_data`
- `fund_fill_stats`
- `results_df`
- `holding_style_exposure`
- `mix_style_exposure`
- `rr_data_with_mix_exposure`

`holding_style_exposure` 还包含每个风格因子的诊断字段：

```text
{factor}_coverage
{factor}_matched_weight_sum
```

### IC 与 Rank IC

`fun_RR_plus.ipynb` 可以直接基于 `outs` 检验季度末能力值对下一季度基金实际收益的预测能力。

普通 IC 使用能力值与实际收益的 Pearson 相关：

```python
ic_summary = compute_quarterly_ic_ir(outs)
```

Rank IC 先分别对能力值和实际收益排名，再计算 Pearson 相关：

```python
rank_ic_summary = compute_quarterly_rank_ic_ir(outs)
```

两个函数默认直接返回跨季度汇总，包括平均 IC、季度标准差、ICIR、年化 ICIR、正 IC 比例和 t 统计量。需要保留每季度相关系数、p 值、基金数量和累计 IC 时：

```python
ic_summary, quarterly_ic = compute_quarterly_ic_ir(
    outs,
    keep_intermediate=True,
)

rank_ic_summary, quarterly_rank_ic = compute_quarterly_rank_ic_ir(
    outs,
    keep_intermediate=True,
)
```

季度频率的年化 ICIR 定义为：

$$
AnnualizedICIR = ICIR \times \sqrt{4}
$$

IC 的 t 统计量定义为：

$$
t_{IC}
=
\frac{\overline{IC}}{s_{IC}/\sqrt{N}}
$$

## 11. 报告口径与当前实现的差异

本项目复现了报告的核心评价框架，但并非逐字逐项的静态重建。以下差异在解释结果时尤其重要：

1. **分组编号方向不同**  
   报告以第十组为最高分组，当前代码以第一组为最高分组。

2. **基金规模判断时点不同**  
   报告要求组合构建时基金规模不低于 1 亿元；当前代码保留窗口内曾出现 `1M=True` 的基金，不一定要求窗口结束日规模仍超过 1 亿元。

3. **持仓数据范围不同**  
   报告的 TOP15 持仓分析使用最新季报重仓股，而模型附录的混合风格暴露使用最新半年报或年报完整持仓。当前代码只在混合风格暴露中使用经过筛选的半年报/年报股票持仓。

4. **择时能力公式属于当前实现**  
   `fun_RR_plus.ipynb` 使用传统 TM 二次回归，以无约束的 `gamma` 作为择时能力。TM 回归只包含截距、市场收益和市场收益平方项，不使用行业或风格因子，也不与原选股回归共享估计系数。

5. **回归窗口已参数化**  
   报告假设过去 `T` 期暴露稳定；当前代码将其具体化为默认 120 个交易日的季度滚动窗口。

6. **缺失 NAV 的处理经过扩展**  
   当前代码会对齐基金和因子交易日、填补部分缺失收益，并剔除填充比例过高的基金。这些是为适配当前数据增加的工程处理。

7. **基金池数据时间不同**  
   报告使用截至 2021 年的数据，当前目录中的基金、经理和描述数据更新到 2026 年附近，因此无法期待基金数量和 TOP15 名单与报告静态结果完全一致。

## 12. 当前已知问题

- `NAVReturn.ipynb` 已改为按 `PRICE_DATE` 计算，但必须实际执行后正式 Feather 才会更新。
- `fun_RR_plus.ipynb` 仍会对基金缺失收益使用前后收益均值及前后填充，可能复制收益并引入未来信息。
- 有效行业因子的局部缺失仍填 0；当前只自动剔除整个窗口完全断档的行业。
- 持仓报告期仍按全市场统一最新期选择，且股票 Barra 暴露日期可能晚于持仓报告期。
- `Seperate_Fund.ipynb` 中 `Passive Index Fund` 没有进入完整的优先级和输出分支。
- `unknown_nav` 只筛选空分类，没有包含显式的 `Other/Unknown`。
- `Mapping/mapping.ipynb` 使用旧版绝对路径，当前主流程不依赖该映射。
- `.txt` 后缀的 Barra 文件实际使用 Feather 格式存储。
- `fun_RR_plus.ipynb` 的注释提到 threading，但实际并行后端为 `loky` 多进程。
- 基金经理 ID 聚合结果在不同 pandas 版本中可能表现为 tuple 或 ndarray；当前主流程已统一标准化并在筛选端兼容多种序列类型。
- 多个 notebook 会覆盖原始或中间数据，尚未形成完全可重复的一键式流水线。
- 项目目前没有统一的 `requirements.txt`、自动化测试或固定随机/环境版本文件。

## 13. 复现目标

本项目的复现目标分为三层：

1. **方法复现**  
   实现报告中的带约束基金收益率归因、风格暴露正则化和持仓/回归混合估计。

2. **组合复现**  
   实现选股、择时和综合能力排名，以及经理去重、公司数量限制和 TOP15 组合构建。

3. **历史检验**  
   通过季度滚动、下一季度持有收益和十分组累计净值，检验能力指标是否具有排序单调性。

由于数据版本、基金池范围、持仓披露文件和部分工程口径不同，项目重点是复现报告的研究框架与检验方法，而不是强制重现报告中 2021Q3 的每一个静态数值。

## 14. 参考资料

- 东吴证券研究所，《正则化基金评价 2021Q3 组合》，2021-07-03。原始 PDF 未包含在本仓库中。
- [`summary.md`](./summary.md)：项目全部 notebook 和数据引用的中文总结。
- [`summary_EN.md`](./summary_EN.md)：对应的英文总结。
- [`data_schema.md`](./data_schema.md)：早期数据结构盘点。
