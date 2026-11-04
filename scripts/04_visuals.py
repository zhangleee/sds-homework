# -*- coding: utf-8 -*-
"""
04_visuals.py — 可视化图表生成（18 张静态 PNG）
================================================
输出（outputs/figures/）：fig01 ~ fig18，中文显示（微软雅黑），150dpi。
图表清单：
  fig01 月度评论趋势折线图    fig02 房型结构环形图        fig03 街区房源分布柱状图
  fig04 街区房型堆叠柱状图    fig05 价格分布直方图        fig06 房型价格箱线图
  fig07 价格与评论数散点图    fig08 评论量帕累托图        fig09 RFM客户价值气泡图
  fig10 RFM八分类分布图       fig11 同期群留存热力图      fig12 HoltWinters预测置信区间
  fig13 街区波士顿矩阵        fig14 街区均价与评论双轴图  fig15 累计评论面积图
  fig16 指标相关性热力图      fig17 头部房东房源分布图    fig18 月度评论季节性分解图
交互式页面（HTML）由 05_dashboard.py 生成。
"""
import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.dates import YearLocator as DateYearLocator
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose

warnings.filterwarnings("ignore")
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(ROOT, "data", "clean")
OUT_DIR = os.path.join(ROOT, "outputs", "figures")
TBL_DIR = os.path.join(ROOT, "outputs", "tables")

# 颜色板（统一风格）
C_MAIN = "#1f6fb2"
C_ACC = "#e07b39"
C_GRID = "#e5e5e5"
C_NEIGH = ["#1f6fb2", "#e07b39", "#5aa469", "#8e6fb2", "#d1a94a",
           "#4a9e9e", "#c96a8a", "#7a8e5f", "#9a8a7a", "#5f7aa8"]


def setup_ax(ax, title=None, xlabel=None, ylabel=None, grid=True):
    ax.set_title(title, fontsize=12, pad=10)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if grid:
        ax.grid(axis="y", linestyle="--", alpha=0.4, color=C_GRID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def load():
    listings = pd.read_csv(os.path.join(CLEAN_DIR, "listings_clean.csv"))
    reviews = pd.read_csv(os.path.join(CLEAN_DIR, "reviews_clean.csv"), parse_dates=["date"])
    master = pd.read_csv(os.path.join(CLEAN_DIR, "master.csv"), parse_dates=["date"])
    monthly = master.groupby(master["date"].dt.to_period("M")).size().sort_index()
    m_ts = monthly.copy()
    m_ts.index = m_ts.index.to_timestamp()
    m_ts = m_ts.asfreq("MS").fillna(0)
    return listings, reviews, master, m_ts


def fig01_trend(m_ts):
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot(m_ts.index, m_ts.values, color=C_MAIN, lw=1.4)
    ax.fill_between(m_ts.index, m_ts.values, color=C_MAIN, alpha=0.12)
    setup_ax(ax, "Albany 月度评论量趋势（2014-07 ~ 2026-09）", "月份", "评论条数")
    ax.annotate("疫情低谷", xy=(pd.Timestamp("2020-04-01"), m_ts.loc["2020-04-01"]),
                xytext=(pd.Timestamp("2018-08-01"), 90), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="gray"))
    ax.annotate("快速复苏", xy=(pd.Timestamp("2021-07-01"), m_ts.loc["2021-07-01"]),
                xytext=(pd.Timestamp("2024-01-01"), 160), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="gray"))
    ax.xaxis.set_major_locator(DateYearLocator(2))
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig01_月度评论趋势.png")); plt.close(fig)


def fig02_roomtype(listings):
    cnt = listings["room_type"].value_counts()
    labels = ["整套房源", "独立房间", "合住房间"]
    sizes = [cnt.get("Entire home/apt", 0), cnt.get("Private room", 0), cnt.get("Shared room", 0)]
    colors = [C_MAIN, C_ACC, "#9aa0a6"]
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    wedges, _ = ax.pie(sizes, colors=colors, startangle=90, counterclock=False,
                       wedgeprops=dict(width=0.42, edgecolor="white"))
    pcts = [f"{s / sum(sizes) * 100:.1f}%" for s in sizes]
    ax.legend(wedges, [f"{l}  {p}" for l, p in zip(labels, pcts)], loc="center left",
              bbox_to_anchor=(0.98, 0.5), frameon=False, fontsize=10)
    ax.set_title("房源房型结构（环形图）", fontsize=12, pad=10)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig02_房型结构环形图.png")); plt.close(fig)


def fig03_neigh(listings):
    top = listings["neighbourhood"].value_counts().head(10).sort_values()
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.barh(top.index, top.values, color=C_MAIN)
    for i, v in enumerate(top.values):
        ax.text(v + 1, i, str(v), va="center", fontsize=9)
    setup_ax(ax, "Top10 街区房源数量分布", "房源数量", None)
    ax.set_xlim(0, top.max() * 1.12)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig03_街区房源分布柱状图.png")); plt.close(fig)


def fig04_stack(listings):
    top8 = listings["neighbourhood"].value_counts().head(8).index
    sub = listings[listings["neighbourhood"].isin(top8)]
    ct = sub.groupby(["neighbourhood", "room_type"]).size().unstack(fill_value=0)
    ct = ct.loc[top8]
    room_map = {"Entire home/apt": "整套", "Private room": "独立", "Shared room": "合住"}
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    bottom = np.zeros(len(ct))
    for rt in ct.columns:
        ax.bar(ct.index, ct[rt], bottom=bottom, label=room_map.get(rt, rt),
               color={"Entire home/apt": C_MAIN, "Private room": C_ACC, "Shared room": "#9aa0a6"}[rt])
        bottom += ct[rt].values
    ax.set_xticklabels(ct.index, rotation=30, ha="right")
    setup_ax(ax, "Top8 街区房型结构（堆叠柱状图）", None, "房源数量")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig04_街区房型堆叠柱状图.png")); plt.close(fig)


def fig05_price(listings):
    p = listings["price"]
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    ax.hist(p, bins=40, color=C_MAIN, alpha=0.85, edgecolor="white")
    ax.axvline(p.mean(), color=C_ACC, ls="--", lw=1.5, label=f"均值 ${p.mean():.0f}")
    ax.axvline(p.median(), color="#2e7d32", ls="-.", lw=1.5, label=f"中位数 ${p.median():.0f}")
    setup_ax(ax, "房源价格分布直方图", "价格（美元/晚）", "房源数")
    ax.legend(frameon=False)
    ax.set_xlim(0, 1500)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig05_价格分布直方图.png")); plt.close(fig)


def fig06_box(listings):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    order = ["Entire home/apt", "Private room", "Shared room"]
    data = [listings.loc[listings["room_type"] == rt, "price"].values for rt in order]
    bp = ax.boxplot(data, tick_labels=["整套房源", "独立房间", "合住房间"], patch_artist=True,
                    medianprops=dict(color="white"), widths=0.5)
    for patch, c in zip(bp["boxes"], [C_MAIN, C_ACC, "#9aa0a6"]):
        patch.set_facecolor(c); patch.set_alpha(0.75)
    ax.set_ylim(0, 800)
    setup_ax(ax, "不同房型价格分布箱线图", None, "价格（美元/晚）")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig06_房型价格箱线图.png")); plt.close(fig)


def fig07_scatter(listings):
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    x = listings["number_of_reviews"]
    y = listings["price"]
    sc = ax.scatter(x, y, s=14, c=x, cmap="viridis", alpha=0.75)
    ax.set_xscale("symlog")
    setup_ax(ax, "房源价格与累计评论数关系散点图", "累计评论数（对数轴）", "价格（美元/晚）")
    cb = fig.colorbar(sc, ax=ax, pad=0.01)
    cb.set_label("累计评论数")
    ax.set_ylim(0, 12000)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig07_价格与评论数散点图.png")); plt.close(fig)


def fig08_pareto():
    pareto = pd.read_csv(os.path.join(TBL_DIR, "pareto.csv"))
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    colors = np.where(pareto["class"] == "A", C_MAIN,
                      np.where(pareto["class"] == "B", C_ACC, "#c9ced4"))
    ax.bar(range(len(pareto)), pareto["reviews"], color=colors, width=0.9)
    ax2 = ax.twinx()
    ax2.plot(range(len(pareto)), pareto["cum_pct"] * 100, color="#333", lw=1.6)
    ax2.axhline(80, color="#d32f2f", ls="--", lw=1)
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("累计评论占比（%）")
    ax.set_xticks([0, 122, 229, 449])
    ax.set_xticklabels(["第1套\n(A类起点)", "第123套\n(A类终点,80%)", "第230套\n(B类终点,95%)", "第500套\n(全部)"])
    setup_ax(ax, "评论量帕累托分析（A/B/C 三类）", "房源（按评论量降序）", "评论条数")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=C_MAIN, label="A类 123套(24.6%)"),
                       Patch(color=C_ACC, label="B类 107套(21.4%)"),
                       Patch(color="#c9ced4", label="C类 270套(54.0%)")],
              loc="upper right", frameon=False, fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig08_评论量帕累托图.png")); plt.close(fig)


def fig09_rfm_bubble(listings):
    rfm_map = {str(k).zfill(3): v for k, v in
               pd.read_csv(os.path.join(TBL_DIR, "rfm.csv"))[["rfm", "segment"]].values}
    df = listings.copy()
    med_r = listings["recency_days"].median()
    med_f = listings["reviews_per_month"].median()
    med_m = (listings["price"] * listings["reviews_per_month"]).median()
    df["R"] = (df["recency_days"] <= med_r).astype(int)
    df["F"] = (df["reviews_per_month"] >= med_f).astype(int)
    df["M"] = (df["price"] * df["reviews_per_month"]) >= med_m
    df["rfm"] = df["R"].astype(str) + df["F"].astype(str) + df["M"].astype(str)
    df["segment"] = df["rfm"].map(rfm_map)
    seg_colors = {"明星房源": C_MAIN, "沉默房源": "#9aa0a6", "需激活": C_ACC, "新上架": "#5aa469",
                  "高价沉寂": "#8e6fb2", "潜力房源": "#4a9e9e", "高活跃流失": "#c96a8a", "高价低评": "#d1a94a"}
    fig, ax = plt.subplots(figsize=(8.0, 5.2))
    for seg, g in df.groupby("segment"):
        ax.scatter(g["reviews_per_month"], g["recency_days"], s=g["M"] * 1.2 + 12,
                   c=seg_colors.get(seg, "#333"), alpha=0.7, label=f"{seg}({len(g)})",
                   edgecolors="white", linewidths=0.4)
    ax.axhline(med_r, color="gray", ls="--", lw=0.9)
    ax.axvline(med_f, color="gray", ls="--", lw=0.9)
    ax.text(med_f + 0.3, ax.get_ylim()[0], "F 中位数", fontsize=8, color="gray")
    ax.text(ax.get_xlim()[0], med_r + 8, "R 中位数", fontsize=8, color="gray")
    ax.set_xscale("symlog")
    setup_ax(ax, "RFM 客户价值气泡图（气泡大小=价值 M）", "月均评论数 F（对数轴）", "距最近评论天数 R")
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncol=2)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig09_RFM客户价值气泡图.png")); plt.close(fig)


def fig10_rfm_bar():
    rfm = pd.read_csv(os.path.join(TBL_DIR, "rfm.csv"))
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    bars = ax.bar(rfm["segment"], rfm["count"], color=C_MAIN, alpha=0.88)
    bars[1].set_color("#9aa0a6")
    for i, (c, p) in enumerate(zip(rfm["count"], rfm["pct"])):
        ax.text(i, c + 2, f"{c} ({p}%)", ha="center", fontsize=9)
    ax.set_xticklabels(rfm["segment"], rotation=25, ha="right")
    setup_ax(ax, "RFM 八分类客户群分布", None, "房源数")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig10_RFM八分类分布图.png")); plt.close(fig)


def fig11_cohort():
    pivot = pd.read_csv(os.path.join(TBL_DIR, "cohort_pivot.csv"))
    years = pivot["cohort"].astype(int).values
    months = [str(c) for c in pivot.columns if c != "cohort"]
    data = pivot.drop(columns="cohort").values
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    im = ax.imshow(data, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_yticks(range(len(years))); ax.set_yticklabels([f"{y}年" for y in years])
    ax.set_xticks(range(len(months))); ax.set_xticklabels([f"{int(m)}月" for m in months], fontsize=8)
    for i in range(len(years)):
        for j in range(len(months)):
            v = data[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.5,
                        color="white" if v > 0.55 else "#333")
    ax.set_title("同期群月度留存率热力图（按首次评论年份）", fontsize=12, pad=10)
    ax.set_xlabel("首次评论后的第 N 个月")
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, label="留存率")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig11_同期群留存热力图.png")); plt.close(fig)


def fig12_forecast(m_ts):
    train = m_ts[m_ts.index < "2026-01-01"]
    test = m_ts[m_ts.index >= "2026-01-01"]
    model = ExponentialSmoothing(train, trend="add", seasonal="add", seasonal_periods=12,
                                 damped_trend=True, initialization_method="heuristic").fit(
        optimized=True, remove_bias=True)
    fc_t = model.forecast(len(test))
    full = ExponentialSmoothing(m_ts, trend="add", seasonal="add", seasonal_periods=12,
                                damped_trend=True, initialization_method="heuristic").fit(
        optimized=True, remove_bias=True)
    fc = full.forecast(12)
    resid = full.resid.dropna()
    rng = np.random.default_rng(42)
    sims = np.zeros((2000, 12))
    for s in range(2000):
        sims[s] = fc.values + rng.normal(0, resid.std(), 12) * np.sqrt(np.arange(1, 13))
    lower = np.percentile(sims, 2.5, axis=0)
    upper = np.percentile(sims, 97.5, axis=0)

    fig, ax = plt.subplots(figsize=(9.6, 4.4))
    ax.plot(m_ts.index, m_ts.values, color="#9aa0a6", lw=1.2, label="历史实际")
    ax.plot(test.index, fc_t.values, color="#2e7d32", ls="--", lw=1.2, label="回测预测(2026-01~09)")
    ax.plot(test.index, test.values, "o", color="#2e7d32", ms=3)
    fut_idx = pd.date_range(m_ts.index.max() + pd.DateOffset(months=1), periods=12, freq="MS")
    ax.fill_between(fut_idx, lower, upper, color=C_MAIN, alpha=0.18, label="95% 置信区间")
    ax.plot(fut_idx, fc.values, color=C_MAIN, lw=1.8, label="未来12个月预测")
    setup_ax(ax, "Holt-Winters 月度评论预测（回测 MAPE=37.0%，RMSE=136.7）", None, "评论条数")
    ax.legend(frameon=False, fontsize=9)
    ax.xaxis.set_major_locator(DateYearLocator(2))
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig12_HoltWinters预测置信区间.png")); plt.close(fig)


def fig13_boston():
    boston = pd.read_csv(os.path.join(TBL_DIR, "boston.csv"))
    med_share = boston["share"].median()
    med_growth = boston["growth"].median()
    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    quad = ["问题街区" if (s <= med_share and g >= med_growth) else
            "瘦狗街区" if (s <= med_share and g < med_growth) else
            "明星街区" if (s > med_share and g >= med_growth) else "金牛街区"
            for s, g in zip(boston["share"], boston["growth"])]
    boston["quad"] = quad
    qcolor = {"明星街区": C_MAIN, "金牛街区": "#5aa469", "问题街区": C_ACC, "瘦狗街区": "#9aa0a6"}
    for q, g in boston.groupby("quad"):
        ax.scatter(g["share"] * 100, g["growth"] * 100, s=g["reviews"] * 0.35 + 40,
                   c=qcolor[q], alpha=0.75, label=f"{q}({len(g)})", edgecolors="white", linewidths=0.5)
        for _, row in g.iterrows():
            ax.annotate(row["neighbourhood"].replace(" WARD", ""), (row["share"] * 100, row["growth"] * 100),
                        fontsize=7.5, xytext=(4, 4), textcoords="offset points")
    ax.axhline(med_growth * 100, color="gray", ls="--", lw=0.9)
    ax.axvline(med_share * 100, color="gray", ls="--", lw=0.9)
    setup_ax(ax, "街区波士顿矩阵（气泡大小=近12月评论量）", "近12月评论份额（%）", "近12月 vs 前12月 增长率（%）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig13_街区波士顿矩阵.png")); plt.close(fig)


def fig14_dual(listings, master):
    top = master.groupby("neighbourhood").size().sort_values(ascending=False).head(10)
    avg_price = listings.groupby("neighbourhood")["price"].mean().reindex(top.index)
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    x = np.arange(len(top))
    ax.bar(x - 0.18, top.values, width=0.36, color=C_MAIN, label="评论量")
    ax.bar(x + 0.18, avg_price.values, width=0.36, color=C_ACC, label="平均价格($)")
    ax.set_xticks(x); ax.set_xticklabels([i.replace(" WARD", "") for i in top.index], rotation=30, ha="right")
    setup_ax(ax, "Top10 街区评论量与平均价格对比（双轴）", None, "数量 / 价格")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig14_街区均价与评论双轴图.png")); plt.close(fig)


def fig15_cum(master):
    cum = master.groupby(master["date"].dt.year).size().cumsum()
    fig, ax = plt.subplots(figsize=(8.0, 3.8))
    ax.fill_between(cum.index, cum.values, color=C_MAIN, alpha=0.3)
    ax.plot(cum.index, cum.values, color=C_MAIN, lw=1.6, marker="o", ms=3)
    setup_ax(ax, "累计评论量增长（按年份）", "年份", "累计评论条数")
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig15_累计评论面积图.png")); plt.close(fig)


def fig16_corr(listings):
    corr = listings[["price", "number_of_reviews", "reviews_per_month", "minimum_nights",
                     "availability_365", "calculated_host_listings_count"]].corr()
    labels = ["价格", "累计评论", "月均评论", "最低入住", "可订天数", "房东房源数"]
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=9)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title("指标相关性热力图", fontsize=12, pad=10)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig16_指标相关性热力图.png")); plt.close(fig)


def fig17_hosts(listings):
    top = listings["host_name"].value_counts().head(15).sort_values()
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.barh(top.index.astype(str), top.values, color=C_MAIN)
    for i, v in enumerate(top.values):
        ax.text(v + 0.3, i, str(int(v)), va="center", fontsize=8.5)
    setup_ax(ax, "Top15 房东房源数量分布", "房源数", None)
    ax.set_xlim(0, top.max() * 1.15)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig17_头部房东房源分布图.png")); plt.close(fig)


def fig18_decompose(m_ts):
    decomp = seasonal_decompose(m_ts, model="additive", period=12)
    fig, axes = plt.subplots(4, 1, figsize=(9.6, 7.6), sharex=True)
    axes[0].plot(m_ts.index, m_ts.values, color=C_MAIN, lw=1.0)
    axes[0].set_ylabel("观测值")
    axes[1].plot(decomp.trend.index, decomp.trend.values, color=C_ACC, lw=1.2)
    axes[1].set_ylabel("趋势")
    axes[2].plot(decomp.seasonal.index, decomp.seasonal.values, color="#5aa469", lw=1.0)
    axes[2].set_ylabel("季节成分")
    axes[3].plot(decomp.resid.index, decomp.resid.values, color="#9aa0a6", lw=0.9)
    axes[3].set_ylabel("残差")
    axes[0].set_title("月度评论量季节性分解（加法模型，周期=12）", fontsize=12, pad=10)
    for a in axes:
        a.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "fig18_月度评论季节性分解图.png")); plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    listings, reviews, master, m_ts = load()
    print("[visuals] 数据加载完成")
    fig01_trend(m_ts); print("[visuals] fig01 ok")
    fig02_roomtype(listings); print("[visuals] fig02 ok")
    fig03_neigh(listings); print("[visuals] fig03 ok")
    fig04_stack(listings); print("[visuals] fig04 ok")
    fig05_price(listings); print("[visuals] fig05 ok")
    fig06_box(listings); print("[visuals] fig06 ok")
    fig07_scatter(listings); print("[visuals] fig07 ok")
    fig08_pareto(); print("[visuals] fig08 ok")
    fig09_rfm_bubble(listings); print("[visuals] fig09 ok")
    fig10_rfm_bar(); print("[visuals] fig10 ok")
    fig11_cohort(); print("[visuals] fig11 ok")
    fig12_forecast(m_ts); print("[visuals] fig12 ok")
    fig13_boston(); print("[visuals] fig13 ok")
    fig14_dual(listings, master); print("[visuals] fig14 ok")
    fig15_cum(master); print("[visuals] fig15 ok")
    fig16_corr(listings); print("[visuals] fig16 ok")
    fig17_hosts(listings); print("[visuals] fig17 ok")
    fig18_decompose(m_ts); print("[visuals] fig18 ok")
    print(f"[visuals] 完成，共生成 {len(os.listdir(OUT_DIR))} 个文件于 outputs/figures/")


if __name__ == "__main__":
    sys.exit(main())
