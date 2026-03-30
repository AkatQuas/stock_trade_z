import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
from lib.compare import compare_with_preview
from lib.load_stocklist import sort_dataframe
from lib.paths import get_file_in_pack
from lib.ts_pro_api import get_pro_api
from lib.xueqiu import add_xueqiu_url_to_dataframe


def fetch_data():
    """Fetch stock list DataFrame from the API and perform light normalization."""
    api = get_pro_api()
    df = api.stock_basic(
        **{
            # "ts_code": "",
            # "name": "",
            # "exchange": "",
            # "market": "",
            # "is_hs": "",
            "list_status": "L",
            # "limit": "",
            # "offset": "",
        },
        fields=["ts_code", "symbol", "name", "area", "industry"],
    )
    df["name"] = df["name"].str.replace("Ａ", "A")
    df = sort_dataframe(df)
    df_with_urls = add_xueqiu_url_to_dataframe(df)
    return df_with_urls


def save_with_date(df: pd.DataFrame) -> Path:
    """Save DataFrame to a dated CSV and return the Path."""
    current_date = datetime.now().strftime("%m%d")
    csv_file = get_file_in_pack(f"./stocklist.{current_date}.csv")
    df.to_csv(csv_file, index=False)
    print(f"Saved to {csv_file}")
    return Path(csv_file)


def main():
    """End-to-end: fetch, save, preview, then optionally replace total file."""
    df = fetch_data()
    new_path = save_with_date(df)
    old_total = new_path.with_name("stocklist.total.csv")
    shutil.copy2(new_path, old_total)
    print(f"{old_total} is replaced.")
    print(f"{new_path} backup.")


if __name__ == "__main__":
    print("建议一个月执行一次")
    main()
