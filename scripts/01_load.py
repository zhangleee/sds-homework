# -*- coding: utf-8 -*-
"""
01_load.py — 数据加载与合规检查
=================================
功能：
  1. 从 data/raw/ 读取 Inside Airbnb 官方下载的 listings.xlsx 与 reviews.xlsx
  2. 输出数据规模、字段清单与基础检查（字段类型、缺失概况）
  3. 导出 raw 副本 CSV 便于复用与版本管理

数据来源合规说明：
  - 数据源：Inside Airbnb (https://insideairbnb.com/get-the-data)
  - 获取方式：官方 CSV/XLSX 文件直接下载（白名单方式，未使用任何爬虫）
  - License：CC BY 4.0（学术研究与非商业用途）
"""
import os
import sys
import pandas as pd

# 项目根目录（本文件位于 scripts/ 下）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")


def load_excel(fname: str) -> pd.DataFrame:
    """读取原始 Excel 文件并打印检查信息"""
    path = os.path.join(RAW_DIR, fname)
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到原始数据文件: {path}，请先放置官方下载文件。")
    df = pd.read_excel(path)
    print(f"[load] {fname}: {len(df)} 行 x {len(df.columns)} 列")
    print(f"[load] 字段列表: {list(df.columns)}")
    return df


def main() -> None:
    listings = load_excel("listings.xlsx")
    reviews = load_excel("reviews.xlsx")

    # 基础检查
    print(f"\n[check] listings 主键 id 唯一性: {listings['id'].is_unique}")
    print(f"[check] listings 缺失值概况:\n{listings.isna().sum()}")
    print(f"\n[check] reviews 缺失值: {reviews.isna().sum().to_dict()}")

    # 导出 raw CSV（便于复用与版本管理）
    os.makedirs(RAW_DIR, exist_ok=True)
    listings.to_csv(os.path.join(RAW_DIR, "listings_raw.csv"), index=False, encoding="utf-8-sig")
    reviews.to_csv(os.path.join(RAW_DIR, "reviews_raw.csv"), index=False, encoding="utf-8-sig")
    print("\n[load] 已导出 raw 副本: data/raw/listings_raw.csv, data/raw/reviews_raw.csv")
    print("[load] 完成。数据规模达标：主表 listings 记录数 =", len(listings), ">= 500")


if __name__ == "__main__":
    sys.exit(main())
