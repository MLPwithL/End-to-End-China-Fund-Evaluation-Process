# Notebook 工作总结

> [返回项目 README](./README.md) | [English version](./summary_EN.md)

> 汇总范围：当前项目目录下全部 15 个 `.ipynb` 文件，并结合 `data_schema.md` 与目录中的数据文件核对。
> 汇总日期：2026-06-10

## 1. 项目整体在做什么

这个目录实现的是一套基金数据清洗、因子暴露估计、基金能力评价和滚动回测流程，核心研究对象是主动股票型/偏股混合型基金。

主流程可以概括为：

1. 将原始基金 NAV CSV 转成 Feather，并检查字段和缺失情况。
2. 根据 Wind 基金行业分类和基金描述表识别基金类型，拆分出股票型/偏股混合型基金。
3. 将基金净值日期映射到宽基指数交易日，剔除无法合理对齐或交易日缺口过大的基金。
4. 在最终交易日面板中按 `PRICE_DATE` 和复权净值重新计算基金收益率，只覆盖 `return` 列。
5. 生成宽基指数、申万一级行业和 Barra 风格因子的日收益率数据。
6. 将基金收益率与市场、行业、风格因子合并。
7. 使用带约束和 L2 正则项的回归估计基金股票仓位、行业暴露、风格暴露和 alpha。
8. 用基金披露持仓和个股 Barra 暴露计算逐因子归一化的持仓风格暴露；覆盖率合格时与回归暴露等权混合，覆盖率不足时回退到回归暴露。
9. 计算选股能力、择时能力和综合能力，进行基金经理去重及基金公司数量限制。
10. 按季度滚动运行，计算下一季度实际收益、十分组收益、TOP15 组合收益和累计收益曲线。
11. 计算综合评分第一组减第十组的季度多空收益，并汇总胜率、平均季度多空收益和柱状图。
12. 计算选股、择时和综合能力的季度 IC、Rank IC、ICIR、年化 ICIR 和显著性统计。

其中：

- `fun_RR_plus.ipynb` 是目前最完整、最接近正式研究程序的主 notebook。
- `fun_RR.ipynb` 保留为旧版函数化流程，用于口径和历史结果对照。
- `RR.ipynb` 是单窗口、逐步骤实现的原型。
- `基金数据/`、`宽基指数日行情/`、`申万一级行业/`、`Barra_CNE5/` 中的 notebook 主要负责准备输入数据。
- 多个名为 `test.ipynb` 的文件属于试验、检查或临时代码，不是完整流水线。

## 2. 目录与数据角色

| 目录/文件 | 主要角色 |
|---|---|
| `基金数据/` | 基金 NAV、基金类型、基金经理、股票/债券/其他持仓的清洗和派生数据 |
| `宽基指数日行情/` | 6 个宽基指数行情及其日收益率宽表 |
| `申万一级行业/` | 申万一级行业行情及行业日收益率宽表 |
| `Barra_CNE5/` | Barra 因子收益率、风格因子暴露、正交后风格因子暴露 |
| `Mapping/` | 交易日与持仓报告期映射、Barra 行业名与申万行业名映射 |
| `备用数据/` | 原始大 CSV 和简单读取测试 |
| `RR.ipynb` | 单个时间窗口的回归和能力评价原型 |
| `fun_RR_plus.ipynb` | 当前函数化主流程：新择时能力、季度滚动回测、IC/Rank IC |
| `fun_RR.ipynb` | 旧版函数化、多窗口、季度滚动回测流程 |
| `navtotradeday.ipynb` | NAV 日期与交易日对齐，生成回归使用的基金日频面板 |
| `outs.pkl`、`outs1.pkl` | 已运行滚动回测结果的序列化文件；`fun_RR.ipynb` 明确写出 `outs1.pkl` |

## 3. Notebook 总览

| Notebook | 主要工作 | 主要输入 | 主要输出 |
|---|---|---|---|
| `fun_RR_plus.ipynb` | 当前 RR 回归、能力评分、季度滚动回测和 IC 检验 | 基金日频面板、持仓、宽基/行业/Barra 因子、基金经理 | `outs`、十分组和 TOP15 收益、季度多空收益、IC/Rank IC 汇总与明细 |
| `fun_RR.ipynb` | 旧版函数化 RR 回归、能力评分与季度滚动回测 | 与 plus 版本基本相同 | 历史口径的 `outs`、累计收益和多空分析 |
| `RR.ipynb` | 单窗口回归原型和能力计算 | 与函数化主流程基本相同 | 回归暴露、持仓暴露、选股能力、经理去重 TOP15 |
| `navtotradeday.ipynb` | 基金 NAV 日期对齐到最近交易日 | 偏股基金 NAV、宽基指数收益率 | `基金数据/交易日偏股型基金.feather` |
| `基金数据/Seperate_Fund.ipynb` | 基金分类、NAV 拆分、持仓分类、基金描述补充 | NAV、基金行业分类、持仓 CSV、基金描述 CSV | 各类基金 NAV、持仓 Feather、更新后的偏股基金数据 |
| `基金数据/NAVReturn.ipynb` | 在最终交易日面板中按 `PRICE_DATE` 重算基金收益率 | `交易日偏股型基金.feather` | 仅更新同一文件的 `return` 列 |
| `基金数据/test.ipynb` | NAV CSV 转 Feather、基金分类和日期连续性试验 | 原始 NAV CSV、分类表、NAV Feather | `Mutual_Fund_Nav.feather`，其余多为诊断 |
| `基金数据/对齐数据日期.ipynb` | 持仓报告期筛选并生成可用日期 | 股票/债券持仓 Feather | 覆盖写回两个持仓 Feather |
| `基金数据/FundNAV数据缺失查找汇报.ipynb` | NAV 核心字段缺失率诊断 | `Fund_NAV.feather` | 内存中的 `nan_summary` |
| `宽基指数日行情/Return_Summary.ipynb` | 计算 6 个宽基指数日收益率 | 6 个指数 Excel | `宽基指数收益率.csv` |
| `申万一级行业/Return_Summary.ipynb` | 计算申万一级行业日收益率 | 申万指数日行情 CSV | `申万一级行业_with_dailyreturn.feather` |
| `Barra_CNE5/SeperateBarraFactor.ipynb` | 拆分 Barra 风格、行业和全因子收益率 | `BarraFactorReturn.txt` | 3 个 Feather 文件 |
| `Barra_CNE5/test.ipynb` | 测试读取 Barra 因子收益率 | `BarraFactorReturn.txt` | 无 |
| `Mapping/mapping.ipynb` | 交易日/持仓期映射和行业名映射 | 旧版 NAV、季度持仓 | 2 个 Feather/CSV 映射表 |
| `备用数据/test.ipynb` | 测试读取原始 NAV CSV 的日期列 | `Mutual_Fund_Nav.csv` | 无 |

## 4. 各 Notebook 详细说明

### 4.1 `fun_RR_plus.ipynb`

这是整个项目当前的核心 notebook。在 `fun_RR.ipynb` 的函数化结构上更新了择时能力、经理去重兼容性，并增加了季度 IC、Rank IC 和 ICIR 检验。

主要模块：

- 定义 `RRRawData`，集中保存 NAV、持仓、宽基、行业和 Barra 数据。
- `load_rr_data()` 一次性读取并统一日期格式。
- `prepare_rr_base_data()` 预先建立精简 NAV 表和按日期合并的因子表，减少多窗口重复计算。
- `build_rr_data()`：
  - 按时间窗口筛选数据；
  - 保留窗口内至少 120 个基金日期且曾满足 `1M` 标记的基金；
  - 将基金日期扩展到因子交易日；
  - 对缺失收益率做前后值均值填补，再前后填充；
  - 统计填充比例并剔除填充比例超过 5% 的基金。
- `run_regularized_regression()` 对每只基金估计：
  - 股票仓位 `stock_exposure`；
  - 32 个申万行业暴露；
  - 10 个 Barra 风格暴露；
  - `alpha`。
- 回归前会按当前窗口动态剔除整段没有任何有效观测的行业因子。例如 `采掘` 在 2022 年后的窗口退出回归，而仍有数据的 `煤炭` 继续参与。
- 回归约束：
  - 股票仓位在 `[0, 1]`；
  - 行业暴露在 `[0, 1]`；
  - 行业暴露之和等于股票仓位；
  - 只对风格暴露施加 L2 正则，默认系数 `6e-5`。
- `compute_holding_style_exposure()`：
  - 选取 `end_date` 前最新可用半年报/年报持仓；
  - 选取 `end_date` 前最近的 Barra 暴露日期；
  - 对每个 Barra 风格因子分别匹配有效股票；
  - 用该因子的有效匹配权重重新归一化持仓暴露；
  - 保存 `{factor}_coverage` 和 `{factor}_matched_weight_sum`；
  - 默认覆盖率低于 85% 时将该因子的持仓暴露设为缺失。
- `compute_stock_selection_ability()`：
  - 持仓暴露有效时，回归风格暴露与持仓风格暴露各占 50%；
  - 持仓暴露因覆盖率不足而缺失时，完全使用回归暴露；
  - 用市场、行业、混合风格暴露重构模型收益；
  - 基金实际收益减模型收益，均值作为选股能力。
- `compute_timing_ability()`：
  - 独立于原选股归因回归，运行传统 Treynor-Mazuy 二次回归；
  - 只使用截距、市场收益和市场收益平方项；
  - 通过普通最小二乘法重新估计 `tm_alpha`、`tm_beta` 和 `gamma`；
  - 不加入行业或 Barra 风格因子，不施加暴露约束或正则项；
  - `gamma` 不设正负约束，并作为 `timing_ability`；
  - 使用 `joblib.Parallel` / `loky` 结构并行求解基金。
- 将选股能力和择时能力转成百分位分数，并等权计算综合分数。
- 基金筛选时要求：
  - 基金经理不能重复；
  - 缺少基金经理或基金公司信息的基金剔除；
  - 每家基金公司最多入选 2 只；
  - 分别选出选股、择时、综合能力 TOP15。
- `run_rr_window()`：
  - 完整运行一个窗口；
  - 计算下一自然季度末前最后一个交易日作为卖出日；
  - 计算基金下一季度实际收益；
  - 按能力排名分成 10 组；
  - 输出十分组平均收益和 TOP15 平均收益。
- `make_quarterly_rolling_windows()` 生成季度末滚动窗口，默认每个窗口回看 120 个交易日。
- `run_rr_windows()` 批量运行全部窗口。
- `compute_quarterly_ic_ir()`：
  - 能力值与下一季度实际收益计算 Pearson IC；
  - 默认返回跨季度 `mean_ic`、`std_ic`、`icir`、年化 ICIR、正 IC 比例和 t 统计量；
  - `keep_intermediate=True` 时同时返回季度 IC、p 值、基金数量和累计 IC。
- `compute_quarterly_rank_ic_ir()`：
  - 显式对能力值和下一季度实际收益排名后计算 Pearson 相关；
  - 与普通 IC 函数可完全独立调用；
  - 默认返回平均 Rank IC 和 Rank ICIR 汇总，可选保留季度明细。
- 基金经理 ID 在不同 pandas 版本中可能被聚合为 tuple 或 ndarray；快照和筛选函数现已统一标准化并兼容 tuple、list、ndarray 和 Series。
- 示例区间为 `2009-06-30` 至 `2026-03-31`，结果保存在内存字典 `outs` 中。
- `build_decile_cum_return()` 将各期十分组收益串联为累计收益，并绘制选股、择时、综合三类累计收益曲线。
- `build_comprehensive_long_short_return()`：
  - 从每个窗口的 `comprehensive_decile_result` 提取第一组和第十组平均收益；
  - 按 `第一组平均收益 - 第十组平均收益` 计算每季度多空收益；
  - 保留两组样本数、季度有效性和胜负标记；
  - 只用两组收益均有效的季度计算胜率和平均季度多空收益；
  - 绘制季度多空收益柱状图，并返回明细表、汇总字典和 Matplotlib 图对象。

引用的数据：

**直接读取**

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

当前 plus 版本默认不主动写出 pickle；如需持久化，应由调用者为新口径结果指定独立文件名，避免覆盖旧版 `outs.pkl` / `outs1.pkl`。

旧版 [`fun_RR.ipynb`](./fun_RR.ipynb) 仍保留在项目中，用于对照此前“披露持仓变化乘市场累计收益”的择时口径及历史回测结果。

### 4.2 `RR.ipynb`

这是函数化主流程的逐步原型，固定示例窗口为 `2020-06-30` 至 `2021-06-29`。

主要工作：

- 读取基金、持仓、宽基、申万行业和 Barra 风格收益率。
- 包含一组被注释掉的数据质量检查函数。
- 筛选至少 120 个日期且存在规模大于 1 亿元记录的基金。
- 按宽基指数交易日补齐基金日期，使用前值填充。
- 合并市场、行业和风格因子，剔除填充比例超过 5% 的基金。
- 使用 CVXPY/ECOS 对每只基金执行带约束正则回归。
- 用最新可用持仓和 10 个正交后 Barra 文件计算持仓风格暴露。
- 将持仓风格和回归风格等权混合，计算选股能力。
- 按 `end_date` 匹配在任基金经理；没有在任经理时使用此前最近任职记录。
- 按选股能力排序，执行基金经理去重后选取 TOP15。

引用的数据与函数化主流程基本相同，但没有写出结果文件。

### 4.3 `navtotradeday.ipynb`

作用是把基金 NAV 的 `PRICE_DATE` 对齐到宽基指数交易日，生成正式回归输入。

主要规则：

- 只保留 `2002-01-04` 之后的数据。
- 同一基金同一原始日期重复时保留最后一条。
- 每条基金日期匹配最近的宽基交易日，前后距离相同时优先前一个交易日。
- 最大允许偏移为 7 个自然日，超过则删除。
- 对齐后若同一基金同一交易日重复，优先保留缺失字段较少、日期偏移较小的记录。
- 检查基金存续期内缺失的宽基交易日。
- 用交易日序号计算基金相邻观测之间缺失了多少个交易日。
- 只要出现一次缺失交易日数大于 7 的间隔，就剔除整只基金。

引用的数据：

**读取**

- `基金数据/股票型_偏股混合型_nav.feather`
- `宽基指数日行情/宽基指数收益率.csv`

**写出**

- `基金数据/交易日偏股型基金.feather`

### 4.4 `基金数据/Seperate_Fund.ipynb`

这是基金分类和基金基础数据整理的主 notebook，内容较杂，包含多个后续追加步骤。

主要工作：

- 根据基金行业分类定义表和基金所属分类表，把多个中英文说明字段拼接后用正则表达式分类。
- 分类包括 FOF、被动指数、ETF、LOF、QDII、货币、债券、股票、混合和未知。
- 分类优先级以 FOF、ETF、LOF、QDII、货币、债券、股票、混合、未知为主。
- 将分类结果合并到 NAV 长表，并拆分保存各类基金 NAV。
- 对 `交易日偏股型基金.feather` 中的基金规模前向填充，新增 `1M = F_PRT_NETASSET > 1e8`。
- 将基金分类映射到其他、股票、债券三类持仓表，并新增 `fund_type` 和 `is_equity_fund`。
- 检查 NAV 中有、三个持仓文件中没有的基金，并排除 2026-02-01 以后才出现的新基金。
- 使用基金描述表重新校验：
  - 只保留 `F_INFO_FIRSTINVESTTYPE` 为“股票型”或“混合型”的基金；
  - 新增基金公司 `fund_com`；
  - 新增或刷新 `F_INFO_TYPE`。

引用的数据：

**读取**

- `Mutual_Fund_Nav.feather`
- `ASHAREINDUSTRIESCODE_202605221326.csv`
- `CHINAMUTUALFUNDSECTOR_202605221321.csv`
- `交易日偏股型基金.feather`
- `CMFOTHERPORTFOLIO_202605200918.csv`
- `CHINAMUTUALFUNDSTOCKPORTFOLIO_202605190939.csv`
- `CHINAMUTUALFUNDBONDPORTFOLIO_202605200915.csv`
- `股票型_偏股混合型_nav.feather`
- `CHINAMUTUALFUNDDESCRIPTION_202606031717.csv`

**写出**

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
- 覆盖更新 `交易日偏股型基金.feather`

### 4.5 `基金数据/NAVReturn.ipynb`

主要工作：

- 读取最终回归输入 `交易日偏股型基金.feather`。
- 在临时精简表中按基金代码和 `PRICE_DATE` 稳定排序。
- 仅在计算副本中把复权净值 `F_NAV_ADJUSTED` 的 0 视为缺失，不修改原净值列。
- 使用 `pct_change(fill_method=None)` 计算 `return`，首条记录和无法计算的收益保持缺失。
- 恢复原始行序后只覆盖 `return` 列。
- 保存前检查行数、列名和列顺序，先写临时 Feather，检查成功后再原子替换正式文件。
- notebook 已修改，但截至 2026-06-08 尚未实际执行，因此正式 Feather 中的 `return` 是否已刷新取决于本地执行状态。

引用的数据：

- 读取并仅更新 `return`：`交易日偏股型基金.feather`

### 4.6 `基金数据/test.ipynb`

这是基金数据处理的试验 notebook，代码单元之间并非完整连续流程。

包含的工作：

- 使用分块读取和 PyArrow，把大文件 `Mutual_Fund_Nav.csv` 转成 `Mutual_Fund_Nav.feather`。
- 删除若干不需要的字段，并显式指定数据类型。
- 删除 `ANN_DATE` 缺失记录并转为整数。
- 试验基金行业分类函数。
- 检查具体基金代码的 NAV。
- 提供一段依赖外部变量的 NAV 日期连续性诊断代码。

引用的数据：

- `Mutual_Fund_Nav.csv`
- `Mutual_Fund_Nav.feather`
- `ASHAREINDUSTRIESCODE_202605221326.csv`
- `CHINAMUTUALFUNDSECTOR_202605221321.csv`
- `股票型_偏股混合型_nav.feather`

### 4.7 `基金数据/对齐数据日期.ipynb`

主要工作：

- 处理股票和债券持仓 Feather。
- 将 `F_PRT_ENDDATE` 转为日期。
- 只保留 6 月 30 日半年报和 12 月 31 日年报。
- 设置估计可用日期：
  - 半年报：当年 8 月 31 日；
  - 年报：次年 3 月 31 日。
- 新增 `available_date` 并覆盖原文件。
- 检查股票持仓中 `available_date` 为空的记录。

引用并覆盖：

- `CHINAMUTUALFUNDBONDPORTFOLIO.feather`
- `CHINAMUTUALFUNDSTOCKPORTFOLIO.feather`

### 4.8 `基金数据/FundNAV数据缺失查找汇报.ipynb`

读取 `Fund_NAV.feather`，对 12 个 NAV 核心字段计算：

- 整体缺失比例；
- 各年份缺失比例；
- 缺失比例超过 90% 的年份；
- 根据是否存在高度缺失年份标记为 `Acceptable (early missing)` 或 `Needs cleaning`。

只生成内存表 `nan_summary`，不写文件。

### 4.9 `宽基指数日行情/Return_Summary.ipynb`

处理以下 6 个指数 Excel：

- `上证50.xlsx`
- `中证500.xlsx`
- `中证800指数行情.xlsx`
- `中证1000.xlsx`
- `创业板指数.xlsx`
- `沪深300.xlsx`

主要工作：

- 使用 `python-calamine` 读取 Excel。
- 按日期排序。
- 用收盘价 `pct_change()` 计算各指数日收益率。
- 列名使用“指数名称 + dailyreturn”。
- 按日期外连接成宽表，缺失值填 0。
- 输出 `宽基指数收益率.csv`。
- 额外检查每列第一个非零收益日期和指定行。

### 4.10 `申万一级行业/Return_Summary.ipynb`

主要工作：

- 读取 `ASWSINDEXEOD_202605210941.csv`。
- 使用固定字典筛选 32 个申万一级行业代码。
- 按行业和日期排序，以收盘价计算日收益率。
- 透视成“日期一行、行业一列”的宽表。
- 输出 `申万一级行业_with_dailyreturn.feather`。

### 4.11 `Barra_CNE5/SeperateBarraFactor.ipynb`

主要工作：

- 以 Feather 格式读取扩展名为 `.txt` 的 `BarraFactorReturn.txt`。
- 识别 10 个风格因子。
- 将其余非日期列视为行业因子。
- 分别保存风格因子、行业因子和完整因子收益率。

输出：

- `Barra风格因子收益率.feather`
- `Barra行业因子收益率.feather`
- `Barra因子收益率.feather`

### 4.12 `Barra_CNE5/test.ipynb`

只读取 `BarraFactorReturn.txt` 并查看前几行，用于验证文件可以被 `pd.read_feather()` 正常读取。

### 4.13 `Mapping/mapping.ipynb`

包含两类映射：

1. 从旧版 NAV 中提取交易日，保存为 `trading_days.feather`。
2. 将每个交易日向后匹配到最近一期季度持仓日期，保存为 `交易日_持仓日期映射.feather`。
3. 手工建立 Barra 行业名称到申万一级行业名称的映射，保存为 `行业名称映射表.csv`。

引用的数据：

- `基金数据/开放式基金_NAV_clean.feather`
- `基金数据/开放式基金_StockHold_quarterly.feather`
- `trading_days.feather`

前两个绝对路径文件属于旧版数据命名，当前主流程已经改用其他文件。

### 4.14 `备用数据/test.ipynb`

只读取 `Mutual_Fund_Nav.csv` 并查看 `ANN_DATE` 前几行，是最简单的原始数据读取测试。

## 5. 数据依赖链

主要派生关系如下：

```text
备用数据/Mutual_Fund_Nav.csv
    -> 基金数据/Mutual_Fund_Nav.feather
    -> 基金类型识别与拆分
    -> 基金数据/股票型_偏股混合型_nav.feather
    -> 与宽基交易日对齐、剔除大缺口基金
    -> 基金数据/交易日偏股型基金.feather
    -> 按 PRICE_DATE 重算 return，仅覆盖 return 列

宽基指数 Excel
    -> 宽基指数日行情/宽基指数收益率.csv

申万指数日行情 CSV
    -> 申万一级行业/申万一级行业_with_dailyreturn.feather

Barra_CNE5/BarraFactorReturn.txt
    -> Barra风格因子收益率.feather
    -> Barra行业因子收益率.feather
    -> Barra因子收益率.feather

原始持仓 CSV
    -> 股票/债券/其他持仓 Feather
    -> 半年报/年报筛选及 available_date

基金日频面板 + 宽基收益 + 行业收益 + Barra 风格收益
    -> 约束正则回归

股票持仓 + 个股正交后 Barra 暴露
    -> 持仓风格暴露

回归暴露 + 持仓暴露 + 基金经理 + 基金公司
    -> 选股/择时/综合能力
    -> TOP15 和十分组下一季度回测
    -> 综合评分第一组减第十组的季度多空收益、胜率和均值
```

## 6. 关键口径

- 基金收益：在最终交易日面板中按基金和 `PRICE_DATE` 排序后，以复权净值 `F_NAV_ADJUSTED` 计算百分比变化；不自动填充缺失净值。
- 市场因子：`沪深300dailyreturn`。
- 行业因子：申万一级行业日收益率。
- 风格因子：10 个 Barra 风格因子收益率。
- 回归股票仓位：限制在 0 到 1。
- 行业暴露：非负、单项不超过 1，合计等于股票仓位。
- 风格暴露：不设区间约束，但施加 L2 正则。
- 持仓风格暴露：每个因子分别使用有效匹配股票计算加权平均，即 `sum(weight * exposure) / sum(valid weight)`。
- 持仓因子覆盖率：该因子有效匹配股票权重除以基金全部股票持仓权重；默认低于 85% 时持仓暴露设为缺失。
- 选股能力：基金实际收益减市场、行业和混合风格模型收益后的平均残差；未加入回归 alpha。
- 择时能力：独立传统 TM 二次回归中的市场平方项系数 `gamma`。
- 综合能力：选股能力百分位分数与择时能力百分位分数等权平均。
- 普通 IC：每季度能力值与下一季度基金实际收益的 Pearson 相关。
- Rank IC：每季度能力值排名与下一季度收益排名的 Pearson 相关。
- ICIR：季度 IC 均值除以季度 IC 样本标准差；季度频率年化 ICIR 为 `ICIR × sqrt(4)`。
- IC t 统计量：`mean_ic / (std_ic / sqrt(valid_quarter_count))`。
- 综合评分季度多空收益：当前代码第一组为最高分组、第十组为最低分组，定义为 `第一组平均收益 - 第十组平均收益`。
- 多空胜率：两组收益均有效的季度中，多空收益严格大于 0 的季度占比；缺少任一组的季度不进入分母。
- 平均多空收益：仅对有效季度的 `第一组平均收益 - 第十组平均收益` 做算术平均。
- TOP15：经理不重复，每家基金公司最多 2 只。
- 样本外收益：窗口结束日买入，下一自然季度末前最后一个交易日卖出。

## 7. 2023 年后表现排查与三项修复

### 7.1 排查背景与修复状态

旧版 `outs.pkl` / `outs1.pkl` 的分组结果显示，选股能力在 2023 年后出现明显反转：

- 2023 年前，选股能力与下一季度收益的横截面 Spearman 相关均值约为 `+0.034`；
- 2023 年后，该相关均值约为 `-0.138`；
- 2023 年后高分第一组下一季度平均收益约为 `1.4%`，低分第十组约为 `5.9%`；
- 择时能力没有出现同等幅度的反转，问题主要集中在基金收益、行业回归和持仓风格暴露链路。

因此对旧版只在 2009 至 2022 年附近验证过的数据处理假设进行了专项检查，并完成以下三项修复。当前状态为：

- 三项 notebook 代码均已修改；
- notebook JSON、Python 语法、真实行业窗口检查和小型数值测试均已通过；
- `NAVReturn.ipynb` 尚未实际执行并覆盖正式 Feather；
- 尚未用三项修复后的数据重新运行 2009 至 2026 年完整滚动回测；
- 上述收益和相关系数是修复前的问题基线，不是修复后的业绩声明。

### 7.2 修复一：按 `PRICE_DATE` 重算基金收益

**修改原因**

旧版 `NAVReturn.ipynb` 按公告日 `ANN_DATE` 排序计算收益，但主回归按净值日期 `PRICE_DATE` 与因子对齐。这会把部分净值变化挂到错误交易日。检查发现 2023 年约 4.57% 的记录与按 `PRICE_DATE` 重算的收益不一致，两种收益的相关性约为 0.743。

**修改前**

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

旧逻辑还会原地修改净值列、把首条和异常收益填成 0，并可能通过排序与 `reset_index()` 改变行序和列结构。

**修改后**

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

保存时先写临时文件，检查行数和完整列顺序后再替换正式文件：

```python
nav.to_feather(temp_path)
saved_dataset = ds.dataset(temp_path, format="feather")

if saved_dataset.count_rows() != original_row_count:
    raise RuntimeError("保存后行数发生变化")
if saved_dataset.schema.names != original_columns:
    raise RuntimeError("保存后列结构发生变化")

os.replace(temp_path, data_path)
```

**保持不变**

- 除 `return` 外的所有列及其值；
- 原始行数、行序和列顺序；
- `F_NAV_ADJUSTED` 原始列；
- `fun_RR_plus.ipynb` 对正式交易日面板的读取方式。

**修改后验证结果**

- notebook JSON 和全部代码单元通过语法检查；
- 代码断言保证内存中行数和列顺序不变；
- 保存阶段使用 Feather 元数据再次检查；
- 截至 2026-06-08 尚未实际执行 notebook，因此需要先运行该 notebook 才会刷新正式数据。

### 7.3 修复二：动态剔除窗口内完全断档的行业因子

**修改原因**

申万 `采掘` 行业收益最后有效日期为 2021-12-10，之后全部缺失，同时新的 `煤炭` 行业仍持续更新。旧逻辑把所有缺失填成 0，使 `采掘` 在 2022 年后仍占据一个行业暴露变量，并继续进入“行业暴露之和等于股票仓位”的约束。

**修改前**

```python
industry_factors = list(industry_factors)
factor_cols = style_factors + industry_factors
regression_data[factor_cols] = (
    regression_data[factor_cols]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0.0)
)
```

**修改后**

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
    raise ValueError("当前回归窗口没有任何可用行业因子。")

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

**保持不变**

- `run_regularized_regression()` 的名称、参数和调用方法；
- `INDUSTRY_FACTORS` 全局候选列表；
- 股票仓位和行业暴露约束；
- 风格 L2 正则项及默认 `lambda_style=6e-5`；
- `industry_exposure` 字典结构；
- 后续能力计算会把未参与本期回归的行业暴露补为 0，以保持列结构兼容。

**修改后验证结果**

真实行业数据窗口检查结果：

```text
2021-07-01 至 2021-12-31：采掘、煤炭都参与
2022-01-01 至 2022-06-30：只保留煤炭
2023-01-01 至 2023-06-30：只保留煤炭
```

合成回归测试确认：完全断档行业不会创建 CVXPY 暴露变量，后续展开结果仍能生成对应的 0 暴露列。

### 7.4 修复三：持仓 Barra 暴露按逐因子覆盖率归一化

**修改原因**

旧代码直接计算 `sum(weight * exposure)`。当部分持仓股票无法匹配某个 Barra 因子时，缺失股票不会进入求和，等价于把其因子暴露当成 0，导致持仓暴露随覆盖率机械向 0 收缩。真实数据中，持仓权重的 Barra 匹配覆盖率由 2022 年约 94% 下降到 2025 年约 86%，后期偏差更明显。

**修改前**

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

**修改后**

新增默认覆盖率阈值：

```python
HOLDING_FACTOR_COVERAGE_THRESHOLD = 0.85
```

函数末尾新增可选参数，原调用方式保持有效：

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

每个因子独立匹配非空股票，并分别计算有效权重：

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

覆盖率和归一化暴露为：

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

新增诊断字段：

```text
Beta_coverage
Beta_matched_weight_sum
BooktoPrice_coverage
BooktoPrice_matched_weight_sum
...
Size_coverage
Size_matched_weight_sum
```

混合阶段不再把缺失持仓暴露当成 0：

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

即：

```text
持仓暴露有效：50% 回归暴露 + 50% 持仓暴露
持仓暴露无效：100% 回归暴露
```

**保持不变**

- 两个函数的名称和原有调用方式；
- 持仓权重仍使用 `F_PRT_STKVALUETONAV / 100`；
- 最新持仓期和 Barra 日期的选择逻辑；
- 有效持仓暴露的 50%/50% 混合结构；
- 返回值数量和原有风格暴露列名；
- `matched_stock_weight_sum` 旧字段为兼容下游代码继续保留。

当前持仓端只计算 10 个股票级 Barra 风格因子；行业暴露仍来自收益率回归，没有新增股票级持仓行业暴露。

**修改后验证结果**

小型数值测试确认：

- 因子覆盖率 100% 时，暴露等于有效股票的完整加权平均；
- 因子覆盖率 90% 时，暴露除以 90% 有效权重，不再缩成原值的 90%；
- 因子覆盖率 60% 时，持仓暴露为 `NaN`；
- 持仓暴露为 `NaN` 时，混合暴露精确回退到回归暴露；
- `compute_holding_style_exposure()` 原有位置参数顺序保持兼容；
- 持仓 Barra 暴露函数中不存在 `fillna(0)`。

### 7.5 修复后的运行顺序

由于 `NAVReturn.ipynb` 现在直接更新最终交易日面板，相关步骤调整为：

1. 先运行 `navtotradeday.ipynb`，生成 `基金数据/交易日偏股型基金.feather`。
2. 再运行 `基金数据/NAVReturn.ipynb`，按 `PRICE_DATE` 仅重算该文件的 `return`。
3. 重新启动或重新执行 `fun_RR_plus.ipynb` 的 `load_rr_data()`，避免继续使用内存中的旧收益。
4. 运行单窗口检查。
5. 重新运行完整季度滚动回测并生成新的 `outs`。
6. 调用 `build_comprehensive_long_short_return(outs)` 生成综合评分季度多空明细、胜率、平均收益和图表。
7. 新结果确认无误后再覆盖或另存新的 pickle，避免与修复前的 `outs.pkl` / `outs1.pkl` 混淆。

## 8. 值得注意的问题

1. `fun_RR_plus.ipynb` 是当前最完整版本；`fun_RR.ipynb` 和 `RR.ipynb` 保留为旧版与原型，后续应优先维护 plus 版本。
2. `navtotradeday.ipynb` 的 Markdown 仍写 `ANN_DATE`，实际代码处理的是 `PRICE_DATE`；注释中有“5d”旧命名，但当前参数是 7 天。
3. `NAVReturn.ipynb` 已改为按 `PRICE_DATE` 计算，但必须实际执行后正式 Feather 才会更新。
4. `fun_RR_plus.ipynb` 仍会对基金缺失收益使用前后收益均值及前后填充，这一处理可能复制收益并引入未来信息，尚未修复。
5. 有效行业因子的局部缺失仍会填 0；当前只自动剔除整个窗口完全无有效值的行业。
6. 持仓报告期仍采用全市场统一最新期，尚未改为每只基金分别回退到自身最近可用报告。
7. 持仓股票使用报告期权重，但股票 Barra 暴露仍取评价日前最新日期，两者可能存在时间错配。
8. `Seperate_Fund.ipynb` 能返回 `Passive Index Fund`，但该类别未写入完整的优先级和输出分支。
9. `unknown_nav` 只筛选空分类，没有包含显式的 `Other/Unknown`。
10. 多个 notebook 会直接覆盖 Feather 文件；执行顺序会影响最终结果。
11. `Mapping/mapping.ipynb` 使用旧版绝对路径，当前主流程不依赖该映射。
12. `.txt` 后缀的 Barra 文件实际使用 Feather 格式存储。
13. `fun_RR_plus.ipynb` 的注释提到 threading，但基金回归实际使用 `loky` 多进程。
14. 项目尚未形成自动化测试和完全可重复的一键式流水线。

## 9. 建议的执行顺序

1. `基金数据/test.ipynb`：原始 NAV CSV 转 Feather。
2. `基金数据/Seperate_Fund.ipynb`：基金分类和数据拆分。
3. `宽基指数日行情/Return_Summary.ipynb`：生成市场收益率。
4. `申万一级行业/Return_Summary.ipynb`：生成行业收益率。
5. `Barra_CNE5/SeperateBarraFactor.ipynb`：拆分 Barra 因子收益率。
6. `基金数据/对齐数据日期.ipynb`：处理持仓可用日期。
7. `navtotradeday.ipynb`：生成交易日偏股基金面板。
8. `基金数据/NAVReturn.ipynb`：在最终面板中按 `PRICE_DATE` 仅重算 `return`。
9. `fun_RR_plus.ipynb`：重新加载数据，执行季度滚动回归与能力回测，并生成多空收益、IC、Rank IC 和 ICIR 结果。
