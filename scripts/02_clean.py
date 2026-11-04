# -*- coding: utf-8 -*-
"""
02_clean.py — 数据清洗与治理
==============================
处理策略（与论文第3章一一对应）：
  1. 列偏移修复：原始文件中 37 行因空字段导致 pandas 解析列错位。
     经逐行诊断，存在两种偏移模式：
       - 深偏移（6 行）：从 host_id 起整行左移一列（host_id 无法恢复，置空）
       - 浅偏移（31 行）：从 neighbourhood_group 起整行左移一列
     统一按"右移一列"修复，修复后用 room_type 合法值断言校验。
  2. 类型统一：价格、评论数等转数值；日期转 datetime64。
  3. 缺失值处理：
       - price 缺失 33 处 -> 按同房型中位数填充
       - reviews_per_month 缺失 -> 按 0 填充（无评论记录）
       - 无 last_review 的房源 recency_days 置为较大值（视为远期沉寂）
  4. 重复值处理：reviews 表删除完全重复记录（9 条）。
  5. 派生字段：reviews 增加 review_year/review_month；listings 增加
     recency_days（最近评论距参考日 2026-10-22 的天数）。
  6. 多表整合：reviews 与 listings 按 listing_id = id 内连接，输出 master.csv。
"""
import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
CLEAN_DIR = os.path.join(ROOT, "data", "clean")

# 固定参考日期（与论文一致，保证结果可复现）
REF_DATE = pd.Timestamp("2026-10-22")
VALID_ROOM = ["Entire home/apt", "Private room", "Shared room"]


def _is_19digit(x) -> bool:
    """host_profile_id 为 19 位数字串，用于判断偏移起点"""
    s = str(x)
    return s.isdigit() and len(s) == 19


def fix_shifted_rows(df: pd.DataFrame) -> pd.DataFrame:
    """修复 37 行列偏移（深偏移 6 行 + 浅偏移 31 行）"""
    bad_mask = ~df["room_type"].isin(VALID_ROOM)
    print(f"[clean] 检测到列偏移行数: {bad_mask.sum()}")

    deep_cols = ["host_id", "host_profile_id", "host_name", "neighbourhood_group",
                 "neighbourhood", "latitude", "longitude", "room_type", "price",
                 "minimum_nights", "number_of_reviews", "last_review",
                 "reviews_per_month", "calculated_host_listings_count",
                 "availability_365", "number_of_reviews_ltm", "license"]
    shallow_cols = deep_cols[3:]  # 从 neighbourhood_group 起

    df[deep_cols] = df[deep_cols].astype(object)
    n_deep = n_shallow = 0
    for idx in df[bad_mask].index:
        if _is_19digit(df.loc[idx, "host_profile_id"]):
            # 浅偏移：host_id / host_profile_id / host_name 正常
            vals = df.loc[idx, shallow_cols].tolist()
            df.loc[idx, shallow_cols] = [np.nan] + vals[:-1]
            n_shallow += 1
        else:
            # 深偏移：host_id 位置被 host_profile_id 覆盖，host_id 无法恢复
            vals = df.loc[idx, deep_cols].tolist()
            df.loc[idx, deep_cols] = [np.nan] + vals[:-1]
            n_deep += 1
    print(f"[clean] 修复完成：深偏移 {n_deep} 行（host_id 置空），浅偏移 {n_shallow} 行")

    # 修复校验
    assert df["room_type"].isin(VALID_ROOM).all(), "room_type 修复失败"
    assert df["neighbourhood"].notna().all(), "neighbourhood 修复失败"
    print("[clean] 修复校验通过：room_type / neighbourhood 全部合法")
    return df


def clean_listings(raw: pd.DataFrame) -> pd.DataFrame:
    df = fix_shifted_rows(raw.copy())

    # 类型统一
    num_cols = ["price", "minimum_nights", "number_of_reviews", "reviews_per_month",
                "calculated_host_listings_count", "availability_365",
                "number_of_reviews_ltm", "latitude", "longitude"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["last_review"] = pd.to_datetime(df["last_review"], errors="coerce")

    # 缺失值处理
    n_price_na = df["price"].isna().sum()
    df["price"] = df["price"].fillna(df.groupby("room_type")["price"].transform("median"))
    df["reviews_per_month"] = df["reviews_per_month"].fillna(0)
    print(f"[clean] price 缺失 {n_price_na} 处 -> 按同房型中位数填充")

    # 派生字段：距参考日天数
    df["recency_days"] = (REF_DATE - df["last_review"]).dt.days
    df["recency_days"] = df["recency_days"].where(df["recency_days"].notna(), 3650)
    return df


def clean_reviews(raw: pd.DataFrame) -> pd.DataFrame:
    n0 = len(raw)
    df = raw.drop_duplicates()
    n_dup = n0 - len(df)
    df["date"] = pd.to_datetime(df["date"])
    df["review_year"] = df["date"].dt.year
    df["review_month"] = df["date"].dt.to_period("M")
    print(f"[clean] reviews 去重删除 {n_dup} 条完全重复记录")
    return df


def main() -> None:
    os.makedirs(CLEAN_DIR, exist_ok=True)

    # 从 raw 加载（若 raw CSV 存在则读 CSV，否则读 xlsx）
    raw_listings_path = os.path.join(RAW_DIR, "listings.xlsx")
    raw_reviews_path = os.path.join(RAW_DIR, "reviews.xlsx")
    raw_l = pd.read_excel(raw_listings_path)
    raw_r = pd.read_excel(raw_reviews_path)

    listings = clean_listings(raw_l)
    reviews = clean_reviews(raw_r)

    # 数据整合：内连接
    master = reviews.merge(listings[["id", "price", "neighbourhood", "room_type"]],
                           left_on="listing_id", right_on="id", how="inner")
    n_matched = listings["id"].isin(master["listing_id"]).sum()
    print(f"[clean] 内连接后 master 行数: {len(master)}，覆盖房源 {n_matched}/{len(listings)} 套 "
          f"({n_matched / len(listings) * 100:.1f}%)")

    # 导出
    listings.to_csv(os.path.join(CLEAN_DIR, "listings_clean.csv"), index=False, encoding="utf-8-sig")
    reviews.to_csv(os.path.join(CLEAN_DIR, "reviews_clean.csv"), index=False, encoding="utf-8-sig")
    master.to_csv(os.path.join(CLEAN_DIR, "master.csv"), index=False, encoding="utf-8-sig")

    print(f"[clean] listings_clean: {len(listings)} 行")
    print(f"[clean] reviews_clean : {len(reviews)} 行")
    print(f"[clean] master       : {len(master)} 行")
    print(f"[clean] 完成。清洗结果已导出至 data/clean/")


if __name__ == "__main__":
    sys.exit(main())
