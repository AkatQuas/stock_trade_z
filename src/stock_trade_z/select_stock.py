from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from lib.data_utils import load_data_folder
from lib.load_data import load_data
from lib.load_selector import load_selector
from lib.load_stocklist import load_total_stocklist
from lib.logger import get_logger
from lib.time import get_today_name

logger = get_logger("select")


def main():
    p = argparse.ArgumentParser(description="Run selectors defined in configs.json")
    p.add_argument("--data-dir", type=Path, help="行情数据目录， CSV K线数据")
    p.add_argument("--date", help="交易日 YYYY-MM-DD ，默认=数据最新日期")
    args = p.parse_args()

    # --- 加载行情 ---
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error("数据目录 %s 不存在", data_dir)
        sys.exit(1)

    try:
        data, trade_date = load_data_folder(data_dir, date=args.date)
    except Exception as e:
        logger.error("加载行情失败: %s", e)
        sys.exit(1)

    # --- 加载 Selector 配置 ---
    selector_dict = load_selector()
    stocklist = load_total_stocklist()

    logger.info(
        "🤖 开始本轮选股 🚀 🚀, 交易日: %s %s 。 \n\n",
        trade_date.date(),
        trade_date.day_name(),
    )
    # --- 逐个 Selector 运行 ---
    for alias, selector in selector_dict.items():
        picks = selector.select(trade_date, data)

        # 将结果写入日志，同时输出到控制台
        if len(picks) > 0:
            logger.info(
                "============ 🎉 🎉 [%s] 选股结果 (%d) ==========", alias, len(picks)
            )
            filtered_list = [s for s in stocklist if s["symbol"] in picks]
            single_str_list = [
                f"{s["symbol"]}, {s["name"].ljust(5)}({s["xueqiu_url"]})"
                for s in filtered_list
            ]
            big_string = "\n".join(single_str_list)
            logger.info("\n\n%s\n\n", big_string)
        else:
            logger.info("============ ❌ ❌ [%s] 无结果 =======\n\n", alias)

    logger.info("🤖 选股结束，下次再来。 %s 🏖️️ 🏖️\n", get_today_name())


if __name__ == "__main__":
    main()
