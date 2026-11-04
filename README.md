# Albany 短租市场商业数据分析

嘉兴大学数据科学学院《商业数据分析》期末大作业。

基于 Inside Airbnb 公开数据集，对美国 Albany 短租市场进行完整的数据商业分析：数据清洗 → 描述统计 → RFM 客户分群 → 帕累托 / 波士顿 / 漏斗分析 → Holt-Winters 时间序列预测 → 可视化报告与交互大屏。

## 数据规模（清洗后）

- 房源主表 `listings`：500 套（满足 ≥500 的硬性要求）
- 评论明细表 `reviews`：30,242 条（原始 30,251，去重 9 条）
- 评论-房源主表 `master`：30,242 行，覆盖 449 套有评论记录的房源
- 时间范围：2014-07 ~ 2026-09（共 147 个月）

## 目录结构

```
商业数据分析/
├── listings.xlsx / reviews.xlsx        # 原始数据（Inside Airbnb 官方下载）
├── run_all.py                          # 一键复现（01→05 顺序执行）
├── requirements.txt                    # Python 依赖
├── dashboard.html                      # ★ 交互大屏（暗色 ECharts，浏览器直接打开）
├── 商业数据分析_期末大作业.docx        # 论文（最终交付物）
├── assets/
│   └── echarts.min.js                  # ECharts 5.5.0 本地库（离线可用）
├── data/
│   ├── raw/                            # 原始 xlsx 与导出 CSV
│   └── clean/                          # 清洗后 listings_clean / reviews_clean / master
├── scripts/
│   ├── 01_load.py                      # 加载与合规检查
│   ├── 02_clean.py                     # 列偏移修复、缺失值、去重、master 整合
│   ├── 03_analysis.py                 # RFM / 帕累托 / 波士顿 / 漏斗 / Holt-Winters
│   ├── 04_visuals.py                  # 18 张 matplotlib 图 + 2 个 ECharts 交互页
│   └── 05_dashboard.py                 # 生成 dashboard.html 与 fig19/fig20
├── outputs/
│   ├── tables/                         # rfm/pareto/cohort/forecast/boston/funnel/descriptive + results.json
│   └── figures/                        # fig01~fig18 PNG + fig19 地图散点.html + fig20 漏斗.html
├── docs/
│   └── 数据来源合规声明.md
└── 5、《商业数据分析》 - 期末大作业模板.docx
```

## 快速开始

```bash
pip install -r requirements.txt
python run_all.py
```

运行完成后：

- 打开 `dashboard.html` 查看交互大屏（暗色主题，支持房型 / 街区联动筛选）
- 论文图表位于 `outputs/figures/`，模型中间表位于 `outputs/tables/`

## 关键分析结论

- **描述统计**：均价 $282.1/晚（中位数 $146.5），Entire home/apt 占 70.4%；房源最集中街区为 SIXTH WARD（116 套）。
- **RFM 分群**：明星房源 187 套（37.4%）、沉默房源 187 套（37.4%）、需激活 42、新上架 42、潜力 14、高价沉寂 14、高活跃流失 7、高价低评 7。
- **帕累托**：A 类 123 套（24.6%）贡献评论量 24,128 条（约 80%），是核心运营对象。
- **波士顿矩阵**：SIXTH WARD 份额 32.2%、同比 +16.0%，为明星街区；THIRTEENTH 份额下滑 18.5%。
- **漏斗**：500 套 → 449 有评论 → 391 近 12 月活跃 → 280 近 90 天 → 243 月均 ≥1 条。
- **预测**：Holt-Winters（加法趋势 + 加法季节，damped）回测 MAPE = 37.0%，RMSE = 136.7 条/月。

## 数据来源合规

- 数据源：[Inside Airbnb](https://insideairbnb.com/get-the-data)（Albany, NY）
- 获取方式：官方 xlsx 直接下载，未使用爬虫
- License：CC BY 4.0，仅用于课程学术研究
- 详见 `docs/数据来源合规声明.md`

## 仓库地址

https://github.com/zhangleee/sds-homework
