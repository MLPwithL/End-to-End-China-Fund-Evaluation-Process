from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd


FUND_POOL_FILE = Path("交易日偏股型基金.feather")
FUND_DESCRIPTION_FILE = Path("CHINAMUTUALFUNDDESCRIPTION_202606031717.csv")
STOCK_HOLDING_FILE = Path("CHINAMUTUALFUNDSTOCKPORTFOLIO.feather")
REMOVED_FUND_LIST_FILE = Path("交易日偏股型基金_港股相关剔除基金清单.csv")

FUND_CODE_COL = "F_INFO_WINDCODE"
HOLDING_FUND_CODE_COL = "S_INFO_WINDCODE"
STOCK_CODE_COL = "S_INFO_STOCKWINDCODE"

HK_THEME_PATTERN = (
    r"QDII|沪港深|港股|港股通|香港|恒生|互联互通|港深|H股|"
    r"境外|海外|全球|美国|纳斯达克|标普|亚太|亚洲|日本|越南|印度|新兴市场"
)

DESCRIPTION_TEXT_COLS = [
    "F_INFO_FULLNAME",
    "F_INFO_NAME",
    "F_INFO_INVESTSCOPE",
    "F_INFO_INVESTOBJECT",
    "F_INFO_INVESTCONCEPTION",
]

DESCRIPTION_OUTPUT_COLS = [
    "F_INFO_FULLNAME",
    "F_INFO_NAME",
    "F_INFO_FIRSTINVESTTYPE",
    "F_INFO_TYPE",
    "F_INFO_INVESTSCOPE",
    "F_INFO_INVESTOBJECT",
]


def normalize_code(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.upper()


def resolve_data_dir(script_path: Path) -> Path:
    script_dir = script_path.resolve().parent
    if (script_dir / FUND_POOL_FILE).exists():
        return script_dir
    cwd = Path.cwd().resolve()
    if (cwd / FUND_POOL_FILE).exists():
        return cwd
    raise FileNotFoundError(
        "没有找到 交易日偏股型基金.feather。请在基金数据目录运行，"
        "或把脚本放在基金数据目录下运行。"
    )


def read_fund_description(path: Path) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0).columns.tolist()
    usecols = [FUND_CODE_COL]
    usecols += [col for col in DESCRIPTION_TEXT_COLS + DESCRIPTION_OUTPUT_COLS if col in header]
    usecols = list(dict.fromkeys(usecols))

    desc = pd.read_csv(path, usecols=usecols, dtype=str)
    desc["_fund_code_norm"] = normalize_code(desc[FUND_CODE_COL])
    return desc.dropna(subset=["_fund_code_norm"]).drop_duplicates("_fund_code_norm", keep="last")


def find_hk_theme_funds(nav_funds: pd.Series, desc: pd.DataFrame) -> pd.DataFrame:
    nav_ref = pd.DataFrame({"_fund_code_norm": normalize_code(nav_funds).dropna().unique()})
    matched = nav_ref.merge(desc, on="_fund_code_norm", how="left", validate="one_to_one")

    text_cols = [col for col in DESCRIPTION_TEXT_COLS if col in matched.columns]
    if not text_cols:
        matched["_is_hk_theme"] = False
    else:
        text = matched[text_cols].fillna("").agg(" ".join, axis=1)
        matched["_is_hk_theme"] = text.str.contains(HK_THEME_PATTERN, regex=True, na=False)

    return matched.loc[matched["_is_hk_theme"]].copy()


def find_actual_hk_holding_funds(path: Path) -> pd.DataFrame:
    holding = pd.read_feather(path, columns=[HOLDING_FUND_CODE_COL, STOCK_CODE_COL])
    holding["_fund_code_norm"] = normalize_code(holding[HOLDING_FUND_CODE_COL])
    holding["_stock_code_norm"] = normalize_code(holding[STOCK_CODE_COL])

    hk_holding = holding.loc[
        holding["_fund_code_norm"].notna()
        & holding["_stock_code_norm"].str.endswith(".HK", na=False)
    ]
    if hk_holding.empty:
        return pd.DataFrame(columns=["_fund_code_norm", "hk_stock_count", "hk_holding_row_count"])

    return (
        hk_holding.groupby("_fund_code_norm", as_index=False)
        .agg(
            hk_stock_count=("_stock_code_norm", "nunique"),
            hk_holding_row_count=("_stock_code_norm", "size"),
        )
        .sort_values(["hk_holding_row_count", "hk_stock_count"], ascending=False)
    )


def build_remove_list(data_dir: Path, nav: pd.DataFrame) -> pd.DataFrame:
    nav_funds = normalize_code(nav[FUND_CODE_COL]).dropna().unique()
    nav_ref = pd.DataFrame({"_fund_code_norm": nav_funds})

    desc = read_fund_description(data_dir / FUND_DESCRIPTION_FILE)
    hk_theme = find_hk_theme_funds(nav[FUND_CODE_COL], desc)
    actual_hk = find_actual_hk_holding_funds(data_dir / STOCK_HOLDING_FILE)

    remove_base = nav_ref.merge(
        actual_hk,
        on="_fund_code_norm",
        how="inner",
        validate="one_to_one",
    ).merge(
        hk_theme[["_fund_code_norm", "_is_hk_theme"]],
        on="_fund_code_norm",
        how="left",
        validate="one_to_one",
    )
    remove_base["_is_hk_theme"] = remove_base["_is_hk_theme"].fillna(False)
    remove_base["remove_reason"] = "actual_hk_holding"
    remove_base["hk_theme_match"] = remove_base["_is_hk_theme"]

    remove_base = remove_base.merge(desc, on="_fund_code_norm", how="left", validate="one_to_one")
    output_cols = [
        "_fund_code_norm",
        "remove_reason",
        "hk_theme_match",
        "hk_stock_count",
        "hk_holding_row_count",
    ] + [col for col in DESCRIPTION_OUTPUT_COLS if col in remove_base.columns]

    return (
        remove_base[output_cols]
        .rename(columns={"_fund_code_norm": FUND_CODE_COL})
        .sort_values(["remove_reason", FUND_CODE_COL])
        .reset_index(drop=True)
    )


def verify_no_hk_funds(data_dir: Path, cleaned_nav: pd.DataFrame, removed_funds: set[str]) -> None:
    remaining_funds = set(normalize_code(cleaned_nav[FUND_CODE_COL]).dropna().unique())
    if remaining_funds & removed_funds:
        raise RuntimeError("清洗后仍有应剔除基金留在 交易日偏股型基金.feather。")

    actual_hk = find_actual_hk_holding_funds(data_dir / STOCK_HOLDING_FILE)
    remaining_actual_hk = set(actual_hk["_fund_code_norm"]).intersection(remaining_funds)
    if remaining_actual_hk:
        sample = sorted(remaining_actual_hk)[:20]
        raise RuntimeError(f"清洗后仍有基金持有 .HK 股票，样例: {sample}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "从 交易日偏股型基金.feather 中剔除股票持仓文件里实际持有过 .HK 股票的基金，"
            "并确保剩余基金在股票持仓文件中没有 .HK 持仓。"
        )
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印和导出剔除清单，不写回 feather。")
    parser.add_argument("--no-backup", action="store_true", help="写回前不备份原 feather。")
    parser.add_argument(
        "--removed-list",
        default=str(REMOVED_FUND_LIST_FILE),
        help="剔除基金清单 CSV 输出路径。",
    )
    args = parser.parse_args()

    data_dir = resolve_data_dir(Path(__file__))
    feather_path = data_dir / FUND_POOL_FILE
    removed_list_path = Path(args.removed_list)
    if not removed_list_path.is_absolute():
        removed_list_path = data_dir / removed_list_path

    nav = pd.read_feather(feather_path)
    if FUND_CODE_COL not in nav.columns:
        raise KeyError(f"{FUND_POOL_FILE} 缺少基金代码列 {FUND_CODE_COL}")

    original_columns = nav.columns.tolist()
    original_dtypes = nav.dtypes.astype(str).to_dict()
    before_rows = len(nav)
    before_funds = nav[FUND_CODE_COL].nunique()

    remove_list = build_remove_list(data_dir, nav)
    removed_funds = set(normalize_code(remove_list[FUND_CODE_COL]).dropna().unique())

    cleaned_nav = nav.loc[
        ~normalize_code(nav[FUND_CODE_COL]).isin(removed_funds)
    ].copy()

    if cleaned_nav.columns.tolist() != original_columns:
        raise RuntimeError("清洗过程改变了列名或列顺序。")
    if cleaned_nav.dtypes.astype(str).to_dict() != original_dtypes:
        raise RuntimeError("清洗过程改变了列 dtype。")

    removed_list_path.parent.mkdir(parents=True, exist_ok=True)
    remove_list.to_csv(removed_list_path, index=False, encoding="utf-8-sig")

    verify_no_hk_funds(data_dir, cleaned_nav, removed_funds)

    print(f"原基金池记录数: {before_rows:,}")
    print(f"原基金池基金数: {before_funds:,}")
    print(f"剔除历史实际 .HK 持仓基金数: {len(removed_funds):,}")
    print(f"清洗后记录数: {len(cleaned_nav):,}")
    print(f"清洗后基金数: {cleaned_nav[FUND_CODE_COL].nunique():,}")
    print(f"剔除清单: {removed_list_path}")

    if args.dry_run:
        print("dry-run 模式：未写回 交易日偏股型基金.feather。")
        return

    if not args.no_backup:
        backup_path = feather_path.with_suffix(
            f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.feather"
        )
        shutil.copy2(feather_path, backup_path)
        print(f"原文件备份: {backup_path}")

    temp_path = feather_path.with_suffix(".tmp_hk_filter.feather")
    cleaned_nav.reset_index(drop=True).to_feather(temp_path)
    temp_path.replace(feather_path)
    print(f"已写回: {feather_path}")


if __name__ == "__main__":
    main()
