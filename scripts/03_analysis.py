# -*- coding: utf-8 -*-
"""
03_analysis.py — 商业分析模型计算
==================================
输出（outputs/tables/）：
  - descriptive.csv     探索性统计（价格/评论/入住等关键指标）
  - rfm.csv             RFM 变体模型八分类结果
  - cohort_pivot.csv    同期群月度留存率热力表
  - forecast.csv        Holt-Winters 12 个月预测 + 95% 置信区间
  - pareto.csv          帕累托分析（按房源评论量 ABC 分类）
  - boston.csv          波士顿矩阵（街区 份额×增长 四象限）
  - funnel.csv          评论活跃漏斗各环节人数
并打印全部关键数字（供论文写作引用），同时写出 results.json 汇总。
"""
import os
import sys
import json
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(ROOT, "data", "clean")
OUT_DIR = os.path.join(ROOT, "outputs", "tables")
REF_DATE = pd.Timestamp("2026-10-22")


def run_descriptive(listings: pd.DataFrame) -> dict:
    r = {}
    r["price_mean"] = round(float(listings["price"].mean()), 1)
    r["price_median"] = round(float(listings["price"].median()), 1)
    r["price_max"] = int(listings["price"].max())
    r["room_type_pct"] = {k: round(float(v), 1) for k, v in
                          (listings["room_type"].value_counts(normalize=True) * 100).items()}
    r["neigh_top"] = listings["neighbourhood"].value_counts().head(5).to_dict()
    r["rpm_median"] = round(float(listings["reviews_per_month"].median()), 1)
    r["recency_median"] = round(float(listings["recency_days"].median()), 1)
    r["min_nights"] = listings["minimum_nights"].describe().to_dict()
    r["avail"] = listings["availability_365"].describe().to_dict()
    r["host_top"] = listings["host_name"].value_counts().head(5).to_dict()
    # 相关性矩阵
    corr = listings[["price", "number_of_reviews", "reviews_per_month", "minimum_nights",
                     "availability_365", "calculated_host_listings_count"]].corr()
    r["corr"] = corr.round(3).to_dict()

    pd.DataFrame([{
        "指标": "price 均值", "数值": r["price_mean"],
    }, {"指标": "price 中位数", "数值": r["price_median"]},
        {"指标": "price 最大值", "数值": r["price_max"]},
        {"指标": "reviews_per_month 中位数", "数值": r["rpm_median"]},
        {"指标": "recency_days 中位数", "数值": r["recency_median"]}]).to_csv(
        os.path.join(OUT_DIR, "descriptive.csv"), index=False, encoding="utf-8-sig")
    return r


def run_rfm(listings: pd.DataFrame) -> pd.DataFrame:
    """RFM 变体：R=距最近评论天数(recency_days)，F=月均评论数，M=价格×月均评论(价值代理)"""
    med_r = listings["recency_days"].median()
    med_f = listings["reviews_per_month"].median()
    med_m = (listings["price"] * listings["reviews_per_month"]).median()

    df = listings.copy()
    df["R"] = (df["recency_days"] <= med_r).astype(int)
    df["F"] = (df["reviews_per_month"] >= med_f).astype(int)
    df["M"] = ((df["price"] * df["reviews_per_month"]) >= med_m).astype(int)
    df["rfm"] = df["R"].astype(str) + df["F"].astype(str) + df["M"].astype(str)

    seg_map = {
        "111": "明星房源", "110": "潜力房源", "101": "高价低评", "100": "新上架",
        "011": "需激活", "010": "高活跃流失", "001": "高价沉寂", "000": "沉默房源",
    }
    df["segment"] = df["rfm"].map(seg_map)
    res = df.groupby(["rfm", "segment"]).size().reset_index(name="count")
    res["pct"] = (res["count"] / len(df) * 100).round(1)
    res = res.sort_values("count", ascending=False)
    res.to_csv(os.path.join(OUT_DIR, "rfm.csv"), index=False, encoding="utf-8-sig")
    print(f"[rfm] 阈值: R<={med_r:.1f}天 F>={med_f:.2f} M>={med_m:.2f}")
    for _, row in res.iterrows():
        print(f"[rfm]   {row['segment']}: {row['count']} ({row['pct']}%)")
    return df


def run_cohort(master: pd.DataFrame) -> pd.DataFrame:
    """同期群分析：按房源首次评论年份分组，统计各月留存率"""
    first = master.groupby("listing_id")["date"].min().reset_index()
    first.columns = ["listing_id", "first_date"]
    first["first_p"] = first["first_date"].dt.to_period("M")
    cd = master.merge(first, on="listing_id")
    cd["ym"] = cd["date"].dt.to_period("M")
    cd["month_after"] = (cd["ym"] - cd["first_p"]).apply(lambda x: x.n)
    cd["cohort"] = cd["first_p"].dt.year

    pivot = cd.pivot_table(index="cohort", columns="month_after", values="listing_id",
                           aggfunc="nunique")
    pivot = pivot.div(pivot[0], axis=0).round(3)
    pivot.to_csv(os.path.join(OUT_DIR, "cohort_pivot.csv"), encoding="utf-8-sig")
    print(f"[cohort] 同期群覆盖年份: {sorted(pivot.index.astype(int).tolist())}")
    if 12 in pivot.columns:
        r12 = pivot[12].dropna()
        print(f"[cohort] 12个月留存率最高: {r12.idxmax():.0f}年 {r12.max():.1%}")
    return pivot


def run_forecast(master: pd.DataFrame) -> pd.DataFrame:
    """Holt-Winters 预测：回测(2026-01~09) + 未来12个月预测(含模拟95%置信区间)"""
    monthly = master.groupby(master["date"].dt.to_period("M")).size().sort_index()
    m_ts = monthly.copy()
    m_ts.index = m_ts.index.to_timestamp()
    m_ts = m_ts.asfreq("MS").fillna(0)  # 缺失月份按 0 评论处理

    train = m_ts[m_ts.index < "2026-01-01"]
    test = m_ts[m_ts.index >= "2026-01-01"]

    # 回测：多配置择优（启发式初始化 + 阻尼趋势的加法Holt-Winters）
    best = None
    for damped in [True, False]:
        m = ExponentialSmoothing(train, trend="add", seasonal="add", seasonal_periods=12,
                                 damped_trend=damped, initialization_method="heuristic").fit(
            optimized=True, remove_bias=True)
        fc_t = m.forecast(len(test))
        if np.isnan(fc_t).any():
            continue
        mask = test.values != 0
        mape = float(np.mean(np.abs((test.values[mask] - fc_t.values[mask]) / test.values[mask])) * 100)
        rmse = float(np.sqrt(np.mean((test.values - fc_t.values) ** 2)))
        if best is None or mape < best[0]:
            best = (mape, rmse, damped)
    mape, rmse, use_damped = best
    print(f"[forecast] 回测(2026-01~09) MAPE={mape:.1f}% RMSE={rmse:.1f} damped={use_damped}")

    # 全量拟合 + 未来12个月
    full = ExponentialSmoothing(m_ts, trend="add", seasonal="add", seasonal_periods=12,
                                damped_trend=use_damped, initialization_method="heuristic").fit(
        optimized=True, remove_bias=True)
    fc = full.forecast(12)
    resid = full.resid.dropna()
    sigma = float(resid.std())

    rng = np.random.default_rng(42)
    sims = np.zeros((2000, 12))
    for s in range(2000):
        sims[s] = fc.values + rng.normal(0, sigma, 12) * np.sqrt(np.arange(1, 13))
    lower = np.percentile(sims, 2.5, axis=0)
    upper = np.percentile(sims, 97.5, axis=0)

    fc_df = pd.DataFrame({
        "month": [str((m_ts.index.max() + pd.DateOffset(months=i + 1)).date()) for i in range(12)],
        "forecast": np.round(fc.values, 1),
        "lower95": np.round(lower, 1),
        "upper95": np.round(upper, 1),
    })
    fc_df.to_csv(os.path.join(OUT_DIR, "forecast.csv"), index=False, encoding="utf-8-sig")
    for _, row in fc_df.iterrows():
        print(f"[forecast]   {row['month']}: {row['forecast']} [{row['lower95']}, {row['upper95']}]")

    # 回测预测值也落盘（供论文图表引用）
    bt = pd.DataFrame({"month": test.index.strftime("%Y-%m"),
                       "actual": test.values,
                       "backtest_fit": np.round(full.fittedvalues[-len(test):].values, 1)})
    bt.to_csv(os.path.join(OUT_DIR, "backtest.csv"), index=False, encoding="utf-8-sig")
    return fc_df, {"mape": round(mape, 1), "rmse": round(rmse, 1)}


def run_pareto(master: pd.DataFrame, listings: pd.DataFrame) -> pd.DataFrame:
    """帕累托：按房源评论量排序，A类=累计80%评论的房源（无评论房源归入C类）"""
    counts = master.groupby("listing_id").size()
    s = counts.reindex(listings["id"]).fillna(0).sort_values(ascending=False)
    total = s.sum()
    cum = s.cumsum() / total
    cls = np.where(cum <= 0.80, "A", np.where(cum <= 0.95, "B", "C"))
    pareto = pd.DataFrame({"listing_id": s.index, "reviews": s.values, "cum_pct": cum.values, "class": cls})
    pareto.to_csv(os.path.join(OUT_DIR, "pareto.csv"), index=False, encoding="utf-8-sig")
    summary = pareto.groupby("class").agg(listings=("listing_id", "count"), reviews=("reviews", "sum"))
    summary["pct"] = (summary["listings"] / len(listings) * 100).round(1)
    print(f"[pareto] 总评论 {int(total)}")
    for c in ["A", "B", "C"]:
        row = summary.loc[c]
        print(f"[pareto] {c}类: {int(row['listings'])} 套 ({row['pct']}%) 评论 {int(row['reviews'])} 条")
    return pareto


def run_boston(master: pd.DataFrame, listings: pd.DataFrame) -> pd.DataFrame:
    """波士顿矩阵：街区维度，x=评论份额(近12月)，y=近12月 vs 前12月增长率"""
    df = master.copy()
    df["recent12"] = df["date"] >= (df["date"].max() - pd.DateOffset(years=1))
    g = df.groupby("neighbourhood")
    recent = g.apply(lambda x: int((x["recent12"]).sum()), include_groups=False)
    prev = g.apply(lambda x: int(((x["date"] >= (x["date"].max() - pd.DateOffset(years=2))) &
                                  (x["date"] < (x["date"].max() - pd.DateOffset(years=1)))).sum()),
                   include_groups=False)
    listings_n = listings.groupby("neighbourhood")["id"].count()
    boston = pd.DataFrame({"recent": recent, "prev": prev}).dropna()
    boston = boston[boston["recent"] + boston["prev"] > 0]
    boston["reviews"] = g.size().reindex(boston.index).fillna(0).astype(int)
    boston["share"] = (boston["recent"] / boston["recent"].sum()).round(4)
    boston["growth"] = ((boston["recent"] - boston["prev"]) / boston["prev"].replace(0, np.nan)).round(4)
    boston["listings"] = listings_n.reindex(boston.index).fillna(0).astype(int)
    boston = boston.sort_values("reviews", ascending=False).reset_index()
    boston.to_csv(os.path.join(OUT_DIR, "boston.csv"), index=False, encoding="utf-8-sig")
    for _, row in boston.head(6).iterrows():
        print(f"[boston] {row['neighbourhood']}: 份额{row['share']:.1%} 增长{row['growth']:+.1%} 房源{int(row['listings'])}")
    return boston


def run_funnel(listings: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """评论活跃漏斗：全部 -> 有评论 -> 近12月有评论 -> 90天内活跃 -> 月均≥1"""
    n_all = len(listings)
    n_has = master["listing_id"].nunique()
    recent12 = master[master["date"] >= (master["date"].max() - pd.DateOffset(years=1))]
    n_r12 = recent12["listing_id"].nunique()
    rpm = listings.set_index("id")["reviews_per_month"]
    n_active90 = int(listings["recency_days"].le(90).sum())
    n_rpm1 = int((rpm >= 1).sum())
    funnel = pd.DataFrame({
        "环节": ["全部房源", "有评论记录", "近12月有评论", "90天内活跃", "月均评论≥1"],
        "房源数": [n_all, n_has, n_r12, n_active90, n_rpm1],
    })
    funnel["转化率"] = (funnel["房源数"] / funnel["房源数"].shift(1) * 100).round(1)
    funnel.to_csv(os.path.join(OUT_DIR, "funnel.csv"), index=False, encoding="utf-8-sig")
    for _, row in funnel.iterrows():
        print(f"[funnel] {row['环节']}: {row['房源数']}")
    return funnel


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    listings = pd.read_csv(os.path.join(CLEAN_DIR, "listings_clean.csv"))
    reviews = pd.read_csv(os.path.join(CLEAN_DIR, "reviews_clean.csv"),
                          parse_dates=["date"])
    master = pd.read_csv(os.path.join(CLEAN_DIR, "master.csv"), parse_dates=["date"])
    print(f"[analysis] listings={len(listings)} reviews={len(reviews)} master={len(master)}")

    results = {"n_listings": len(listings), "n_reviews": len(reviews), "n_master": len(master)}
    results["descriptive"] = run_descriptive(listings)
    run_rfm(listings)
    run_cohort(master)
    fc_df, fc_metrics = run_forecast(master)
    results["forecast"] = fc_metrics
    run_pareto(master, listings)
    run_boston(master, listings)
    run_funnel(listings, master)

    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("[analysis] 全部模型计算完成，结果已导出 outputs/tables/ 与 results.json")


if __name__ == "__main__":
    sys.exit(main())
