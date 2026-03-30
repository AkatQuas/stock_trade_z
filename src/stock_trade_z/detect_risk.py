from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd
from lib.data_utils import load_data_folder
from lib.load_data import load_data
from lib.load_stocklist import load_total_stocklist
from lib.logger import get_logger
from lib.risk_selectors import (ATRVolatilitySelector, MADeclineSelector,
                                RSIExtremesSelector, VolumeSelloffSelector)
from lib.time import get_today_name

logger = get_logger("risk")


def main():
    p = argparse.ArgumentParser(description="Run risk selectors over CSV K-line data folder")
    p.add_argument("--data-dir", type=Path, required=True, help="行情数据目录， CSV K线数据")
    p.add_argument("--date", help="交易日 YYYY-MM-DD，默认=数据最新日期")
    args = p.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error("数据目录 %s 不存在", data_dir)
        return

    try:
        data, trade_date = load_data_folder(data_dir, date=args.date)
    except Exception as e:
        logger.error("加载行情失败: %s", e)
        return

    logger.info("Detecting risks for %s (%s)", trade_date.date(), trade_date.day_name())

    stocklist = load_total_stocklist()

    # instantiate selectors
    selectors = [
        ("ATR Volatility 高波动率", ATRVolatilitySelector()),
        ("RSI Extremes 超买或超卖", RSIExtremesSelector()),
        ("MA Decline 均线走弱", MADeclineSelector()),
        ("Volume Selloff 放量抛售", VolumeSelloffSelector()),
    ]

    # run selectors and collect results
    per_selector_hits: Dict[str, List[str]] = {}
    aggregated: Dict[str, List[str]] = {}  # code -> list of selector names

    for name, sel in selectors:
        try:
            hits = sel.select(trade_date, data)
        except Exception as e:
            logger.exception("selector %s raised", name)
            hits = []
        per_selector_hits[name] = hits
        for code in hits:
            aggregated.setdefault(code, []).append(name)

    # print per-selector results in human-friendly format (symbol, name, url)
    # for name, hits in per_selector_hits.items():
    #     if hits:
    #         logger.info("============ [%s] 风险检测结果 (%d) ==========", name, len(hits))
    #         filtered = [s for s in stocklist if s["symbol"] in hits]
    #         if filtered:
    #             lines = [f"{s["symbol"]}, {s["name"].ljust(5)}({s["xueqiu_url"]})" for s in filtered]
    #             logger.info("\n\n%s\n\n", "\n".join(lines))
    #         else:
    #             # fallback to symbol list
    #             logger.info("%s", ", ".join(hits))
    #     else:
    #         logger.info("============ [%s] 无结果 ========", name)

    # check summary only for now
    # aggregated summary (single log invocation)
    if aggregated:
        header = f"=== Aggregated risk summary ({len(aggregated)} symbols) ==="
        out_lines: List[str] = [header]
        for code, reasons in sorted(aggregated.items(), key=lambda kv: len(kv[1]), reverse=True):
            info = next((s for s in stocklist if s["symbol"] == code), None)
            if info:
                name = info.get("name", "")
                name_padded = name.ljust(5)
                url = info.get("xueqiu_url", "")
                out_lines.append(f"{code}, {name_padded}({url}) => {len(reasons)} flags: {', '.join(reasons)}")
            else:
                out_lines.append(f"{code} => {len(reasons)} flags: {', '.join(reasons)}")

        logger.info("\n%s", "\n".join(out_lines))
    else:
        logger.info("No risky symbols detected by selectors.")

    logger.info("Done. %s", get_today_name())


if __name__ == "__main__":
    main()
