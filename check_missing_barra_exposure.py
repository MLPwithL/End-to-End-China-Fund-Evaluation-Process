from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd


STYLE_FACTORS = [
    "Size",
    "Volatility",
    "Liquidity",
    "Momentum",
    "Quality",
    "Value",
    "Growth",
    "Sentiment",
    "DividendYield",
]

DEFAULT_START_DATE = "2022-01-01"
DEFAULT_BARRA_FILE = Path("Barra_CNE5") / "barra_cne6_daily_primary.parquet"
DEFAULT_HOLDING_FILE = Path("基金数据") / "CHINAMUTUALFUNDSTOCKPORTFOLIO.feather"
DEFAULT_FUND_POOL_FILE = Path("基金数据") / "交易日偏股型基金.feather"
DEFAULT_OUTPUT_FILE = Path("barra_cne6_missing_holding_exposure_by_factor_2022plus.csv")


def parse_date_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")

    text = series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    compact_mask = text.str.fullmatch(r"\d{8}", na=False)
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    parsed.loc[compact_mask] = pd.to_datetime(text.loc[compact_mask], format="%Y%m%d", errors="coerce")
    parsed.loc[~compact_mask] = pd.to_datetime(text.loc[~compact_mask], errors="coerce")
    return parsed


def find_project_root(script_path: Path) -> Path:
    root = script_path.resolve().parent
    if (root / DEFAULT_BARRA_FILE).exists() and (root / DEFAULT_HOLDING_FILE).exists():
        return root
    cwd = Path.cwd().resolve()
    if (cwd / DEFAULT_BARRA_FILE).exists() and (cwd / DEFAULT_HOLDING_FILE).exists():
        return cwd
    raise FileNotFoundError(
        "没有找到 Barra_CNE5/barra_cne6_daily_primary.parquet 或 "
        "基金数据/CHINAMUTUALFUNDSTOCKPORTFOLIO.feather。请在项目根目录运行，"
        "或把脚本放在 fun_RR_plus.ipynb 同级目录。"
    )


def load_snapshot_dates(root: Path, start_date: pd.Timestamp) -> list[pd.Timestamp]:
    outs_path = root / "outs.pkl"
    if outs_path.exists():
        with outs_path.open("rb") as f:
            outs = pickle.load(f)
        dates = []
        for item in outs:
            if isinstance(item, dict):
                for key in ("end_date", "PRICE_DATE", "snapshot_date"):
                    if key in item:
                        dates.append(pd.to_datetime(item[key], errors="coerce"))
                        break
        dates = sorted({date.normalize() for date in dates if pd.notna(date)})
        dates = [date for date in dates if date >= start_date]
        if dates:
            return dates

    holding = pd.read_feather(root / DEFAULT_HOLDING_FILE, columns=["F_PRT_ENDDATE", "available_date"])
    holding["F_PRT_ENDDATE"] = parse_date_series(holding["F_PRT_ENDDATE"])
    holding["available_date"] = parse_date_series(holding["available_date"])
    semi_annual_or_annual = (
        ((holding["F_PRT_ENDDATE"].dt.month == 6) & (holding["F_PRT_ENDDATE"].dt.day == 30))
        | ((holding["F_PRT_ENDDATE"].dt.month == 12) & (holding["F_PRT_ENDDATE"].dt.day == 31))
    )
    dates = (
        holding.loc[semi_annual_or_annual & holding["available_date"].notna(), "available_date"]
        .dropna()
        .dt.normalize()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    return [date for date in dates if date >= start_date]


def latest_holding_snapshot(
    holding: pd.DataFrame,
    snapshot_date: pd.Timestamp,
    allowed_funds: set[str] | None = None,
) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    report_col = "F_PRT_ENDDATE"
    available_col = "available_date"
    stock_col = "S_INFO_STOCKWINDCODE"
    weight_col = "F_PRT_STKVALUETONAV"

    semi_annual_or_annual = (
        ((holding[report_col].dt.month == 6) & (holding[report_col].dt.day == 30))
        | ((holding[report_col].dt.month == 12) & (holding[report_col].dt.day == 31))
    )
    available = holding.loc[
        semi_annual_or_annual
        & holding[available_col].notna()
        & (holding[available_col] <= snapshot_date)
        & holding[report_col].notna()
    ]
    if available.empty:
        return pd.DataFrame(), pd.NaT, pd.NaT

    latest = available[[report_col, available_col]].drop_duplicates().sort_values([available_col, report_col]).iloc[-1]
    latest_report_date = latest[report_col]
    latest_available_date = latest[available_col]

    snapshot = available.loc[
        (available[report_col] == latest_report_date)
        & (available[available_col] == latest_available_date)
        & available[stock_col].notna()
        & available[weight_col].gt(0)
    ].copy()
    if allowed_funds is not None:
        snapshot = snapshot.loc[
            snapshot["S_INFO_WINDCODE"].astype(str).str.upper().str.strip().isin(allowed_funds)
        ].copy()
        if snapshot.empty:
            return pd.DataFrame(), latest_report_date, latest_available_date

    snapshot["holding_weight"] = snapshot[weight_col] / 100.0
    return snapshot, latest_report_date, latest_available_date


def build_missing_rows(
    holding_snapshot: pd.DataFrame,
    exposure_day: pd.DataFrame,
    all_barra_stocks: set[str],
    snapshot_date: pd.Timestamp,
    holding_report_date: pd.Timestamp,
    holding_available_date: pd.Timestamp,
    barra_exposure_date: pd.Timestamp,
) -> list[pd.DataFrame]:
    fund_col = "S_INFO_WINDCODE"
    stock_col = "S_INFO_STOCKWINDCODE"
    exposure_stock_col = "S_INFO_WINDCODE"

    exposure_day = exposure_day.drop_duplicates(exposure_stock_col, keep="last")
    exposure_stocks_on_date = set(exposure_day[exposure_stock_col].dropna().astype(str))
    base = holding_snapshot[[fund_col, stock_col, "holding_weight"]].copy()
    base[stock_col] = base[stock_col].astype(str)

    rows = []
    for factor in STYLE_FACTORS:
        factor_values = exposure_day[[exposure_stock_col, factor]].rename(columns={exposure_stock_col: stock_col})
        merged = base.merge(factor_values, on=stock_col, how="left", indicator=True)
        missing = merged.loc[merged[factor].isna()].copy()
        if missing.empty:
            continue

        missing["missing_reason"] = np.select(
            [
                ~missing[stock_col].isin(all_barra_stocks),
                ~missing[stock_col].isin(exposure_stocks_on_date),
            ],
            [
                "stock_not_in_barra_universe",
                "stock_not_in_barra_exposure_date",
            ],
            default="factor_value_is_nan",
        )
        summary = (
            missing.groupby([stock_col, "missing_reason"], as_index=False)
            .agg(
                holding_fund_count=(fund_col, "nunique"),
                holding_row_count=(fund_col, "size"),
                holding_weight_sum=("holding_weight", "sum"),
                holding_weight_mean=("holding_weight", "mean"),
                holding_weight_max=("holding_weight", "max"),
            )
            .sort_values(["holding_weight_sum", "holding_fund_count"], ascending=False)
        )
        summary.insert(0, "factor", factor)
        summary.insert(0, "barra_exposure_date", barra_exposure_date)
        summary.insert(0, "holding_available_date", holding_available_date)
        summary.insert(0, "holding_report_date", holding_report_date)
        summary.insert(0, "snapshot_date", snapshot_date)
        summary = summary.rename(columns={stock_col: "stock_code"})
        rows.append(summary)

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="检查基金披露持仓中哪些股票缺少新 CNE6 Barra 风格因子暴露值，并输出 CSV 明细。"
    )
    parser.add_argument("--start-date", default=DEFAULT_START_DATE, help="开始检查的快照日期，默认 2022-01-01。")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_FILE), help="输出 CSV 路径，默认写到项目根目录。")
    parser.add_argument(
        "--fund-pool",
        default=str(DEFAULT_FUND_POOL_FILE),
        help="基金池 feather 路径，默认使用 基金数据/交易日偏股型基金.feather。",
    )
    parser.add_argument(
        "--all-holdings",
        action="store_true",
        help="不按基金池过滤，检查股票持仓文件中的全部基金持仓。",
    )
    parser.add_argument(
        "--snapshot-dates",
        default="",
        help="可选，逗号分隔的快照日期，例如 2022-03-31,2022-06-30。留空则优先使用 outs.pkl，否则用持仓可得日期。",
    )
    args = parser.parse_args()

    root = find_project_root(Path(__file__))
    start_date = pd.to_datetime(args.start_date)

    if args.snapshot_dates.strip():
        snapshot_dates = sorted(
            {
                pd.to_datetime(item.strip()).normalize()
                for item in args.snapshot_dates.split(",")
                if item.strip()
            }
        )
    else:
        snapshot_dates = load_snapshot_dates(root, start_date)

    if not snapshot_dates:
        raise ValueError(f"{start_date.date()} 之后没有可检查的快照日期。")

    holding_cols = [
        "S_INFO_WINDCODE",
        "F_PRT_ENDDATE",
        "available_date",
        "S_INFO_STOCKWINDCODE",
        "F_PRT_STKVALUETONAV",
    ]
    holding = pd.read_feather(root / DEFAULT_HOLDING_FILE, columns=holding_cols)
    holding["F_PRT_ENDDATE"] = parse_date_series(holding["F_PRT_ENDDATE"])
    holding["available_date"] = parse_date_series(holding["available_date"])
    holding["F_PRT_STKVALUETONAV"] = pd.to_numeric(holding["F_PRT_STKVALUETONAV"], errors="coerce")

    allowed_funds = None
    if not args.all_holdings:
        fund_pool_path = Path(args.fund_pool)
        if not fund_pool_path.is_absolute():
            fund_pool_path = root / fund_pool_path
        fund_pool = pd.read_feather(fund_pool_path, columns=["F_INFO_WINDCODE"])
        allowed_funds = set(fund_pool["F_INFO_WINDCODE"].dropna().astype(str).str.upper().str.strip().unique())
        print(f"[fund pool] {fund_pool_path} funds={len(allowed_funds)}")

    exposure_cols = ["TRADE_DT", "S_INFO_WINDCODE"] + STYLE_FACTORS
    exposure = pd.read_parquet(root / DEFAULT_BARRA_FILE, columns=exposure_cols)
    missing_factor_cols = [factor for factor in STYLE_FACTORS if factor not in exposure.columns]
    if missing_factor_cols:
        raise KeyError(f"Barra 暴露文件缺少这些风格因子列: {missing_factor_cols}")
    exposure["time"] = parse_date_series(exposure["TRADE_DT"])
    exposure = exposure.loc[exposure["time"].notna()].copy()
    all_barra_stocks = set(exposure["S_INFO_WINDCODE"].dropna().astype(str))

    all_rows = []
    for snapshot_date in snapshot_dates:
        barra_dates = exposure.loc[exposure["time"] <= snapshot_date, "time"]
        if barra_dates.empty:
            print(f"[skip] {snapshot_date.date()} 前没有 Barra 暴露日期")
            continue
        barra_exposure_date = barra_dates.max()
        exposure_day = exposure.loc[exposure["time"] == barra_exposure_date, ["S_INFO_WINDCODE"] + STYLE_FACTORS].copy()

        holding_snapshot, holding_report_date, holding_available_date = latest_holding_snapshot(
            holding,
            snapshot_date,
            allowed_funds=allowed_funds,
        )
        if holding_snapshot.empty:
            print(f"[skip] {snapshot_date.date()} 前没有可用半年/全年持仓")
            continue

        rows = build_missing_rows(
            holding_snapshot=holding_snapshot,
            exposure_day=exposure_day,
            all_barra_stocks=all_barra_stocks,
            snapshot_date=snapshot_date,
            holding_report_date=holding_report_date,
            holding_available_date=holding_available_date,
            barra_exposure_date=barra_exposure_date,
        )
        all_rows.extend(rows)
        missing_count = sum(len(row) for row in rows)
        print(
            f"[done] snapshot={snapshot_date.date()} holding={holding_report_date.date()} "
            f"available={holding_available_date.date()} barra={barra_exposure_date.date()} "
            f"missing_rows={missing_count}"
        )

    if all_rows:
        result = pd.concat(all_rows, ignore_index=True)
    else:
        result = pd.DataFrame(
            columns=[
                "snapshot_date",
                "holding_report_date",
                "holding_available_date",
                "barra_exposure_date",
                "factor",
                "stock_code",
                "missing_reason",
                "holding_fund_count",
                "holding_row_count",
                "holding_weight_sum",
                "holding_weight_mean",
                "holding_weight_max",
            ]
        )

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"[output] {output_path}")
    print(f"[rows] {len(result)}")
    if not result.empty:
        print("[summary by factor]")
        print(result.groupby("factor")["stock_code"].nunique().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()
