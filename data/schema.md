# 数据字典

## 1. `data/clean/listings_clean.csv`（500 行 × 19 列）

房源主表，由 Inside Airbnb 官方 listings.xlsx 清洗后得到。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | int | 房源唯一主键 |
| name | str | 房源标题 |
| host_id | int/str | 房东 ID（部分行原始列错位，host_profile_id 可恢复时置空） |
| host_profile_id | str | 房东主页 ID（19 位数字字符串，用于识别列错位） |
| host_name | str | 房东名 |
| neighbourhood_group | str | 行政区（Albany 数据多为空） |
| neighbourhood | str | 街区（如 SIXTH WARD，共 18 个） |
| latitude / longitude | float | 经纬度 |
| room_type | str | 房型：Entire home/apt / Private room / Shared room |
| price | float | 每晚价格（美元）；缺失按同房型中位数填充 |
| minimum_nights | int | 最低入住晚数 |
| number_of_reviews | int | 累计评论数 |
| last_review | date | 最近一条评论日期 |
| reviews_per_month | float | 月均评论数 |
| calculated_host_listings_count | int | 房东在管房源数 |
| availability_365 | int | 一年可订天数 |
| number_of_reviews_ltm | int | 最近 12 个月评论数 |
| license | str | 经营许可证号 |
| recency_days | int | 最近评论距数据截止日的天数（RFM 之 R） |

## 2. `data/clean/reviews_clean.csv`（30,242 行 × 4 列）

评论明细表，原始 30,251 行按 (listing_id, date) 去重 9 行。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| listing_id | int | 关联房源 id |
| date | date | 评论日期 |
| review_year | int | 年份 |
| review_month | int | 月份 |

## 3. `data/clean/master.csv`（30,242 行 × 8 列）

评论 × 房源主表（内连接），用于月度趋势、漏斗与活跃度分析。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| listing_id / id | int | 房源 ID（id 为房源主表键） |
| date | date | 评论日期 |
| review_year / review_month | int | 年/月 |
| price | float | 房源价格 |
| neighbourhood | str | 街区 |
| room_type | str | 房型 |

## 4. `outputs/tables/` 中间表

- `descriptive.csv`：描述统计
- `rfm.csv`：八分类分群（rfm 三位码 + segment + count + pct）
- `pareto.csv`：A/B/C 类评论量贡献
- `cohort_pivot.csv` / `cohort_retention.csv`：房东同期群
- `boston.csv`：街区份额与同比增速
- `funnel.csv`：评论活跃漏斗各环节
- `forecast.csv`：月度评论序列与 Holt-Winters 预测
- `results.json`：全部关键指标汇总（论文数字口径以此为准）
