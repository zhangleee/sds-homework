# -*- coding: utf-8 -*-
"""
05_dashboard.py — 交互式可视化（ECharts）
=========================================
输出：
  - outputs/figures/fig19_房源地图散点.html  房源地理分布散点（经纬度，颜色=价格）
  - outputs/figures/fig20_评论活跃漏斗.html   评论活跃漏斗图
  - dashboard.html                           8 组件联动大屏（KPI卡片/月度趋势/房型饼图/
                                             街区房源/街区均价/RFM玫瑰图/地理散点/街区活跃度，
                                             房型与街区筛选器联动，暗色主题）
数据全部内嵌（self-contained），打开页面需联网加载 ECharts CDN。
"""
import os
import sys
import json
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(ROOT, "data", "clean")
TBL_DIR = os.path.join(ROOT, "outputs", "tables")
FIG_DIR = os.path.join(ROOT, "outputs", "figures")

ECHARTS_LOCAL = "assets/echarts.min.js"        # 项目根下本地库（离线可用）
ECHARTS_FIG = "../../assets/echarts.min.js"    # outputs/figures/ 相对路径


def html_head(title: str, src: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="{src}"></script>
</head>
<body>
"""


def load_data():
    listings = pd.read_csv(os.path.join(CLEAN_DIR, "listings_clean.csv"))
    master = pd.read_csv(os.path.join(CLEAN_DIR, "master.csv"), parse_dates=["date"])
    rfm = pd.read_csv(os.path.join(TBL_DIR, "rfm.csv"))
    funnel = pd.read_csv(os.path.join(TBL_DIR, "funnel.csv"))

    # 每套房源近12月是否有评论（基于 master 最近12个月）
    recent_cut = master["date"].max() - pd.DateOffset(years=1)
    recent_ids = set(master.loc[master["date"] >= recent_cut, "listing_id"])
    seg_map = {str(k).zfill(3): v for k, v in rfm[["rfm", "segment"]].values}
    med_r = listings["recency_days"].median()
    med_f = listings["reviews_per_month"].median()
    med_m = (listings["price"] * listings["reviews_per_month"]).median()
    rows = []
    for _, r in listings.iterrows():
        rcode = f"{int(r['recency_days'] <= med_r)}{int(r['reviews_per_month'] >= med_f)}{int((r['price'] * r['reviews_per_month']) >= med_m)}"
        rows.append({
            "id": int(r["id"]), "room": r["room_type"], "neigh": r["neighbourhood"],
            "price": float(r["price"]), "lat": float(r["latitude"]), "lon": float(r["longitude"]),
            "reviews": int(r["number_of_reviews"]), "rpm": float(r["reviews_per_month"]),
            "recency": int(r["recency_days"]), "seg": seg_map.get(rcode, "其他"),
            "active12": int(r["id"] in recent_ids),
        })
    monthly = master.groupby(master["date"].dt.to_period("M")).size().sort_index()
    monthly = monthly.reindex(pd.period_range(monthly.index.min(), monthly.index.max(), freq="M")).fillna(0)
    monthly_list = [{"m": str(p), "v": int(v)} for p, v in monthly.items()]

    recent12_by_neigh = master.loc[master["date"] >= recent_cut].groupby("neighbourhood").size().to_dict()

    return {
        "listings": rows,
        "monthly": monthly_list,
        "funnel": [{"name": row["环节"], "value": int(row["房源数"])} for _, row in funnel.iterrows()],
        "recent12": recent12_by_neigh,
        "total_reviews": int(len(master)),
    }


def build_map_page(data) -> str:
    listings = data["listings"]
    pts = [[x["lon"], x["lat"], x["price"], x["reviews"], x["neigh"]] for x in listings]
    title = "Albany 房源地理分布散点图"
    return html_head(title, ECHARTS_FIG) + f"""
<div id="c" style="width:100%;height:100vh;"></div>
<script>
var pts = {json.dumps(pts, ensure_ascii=False)};
var chart = echarts.init(document.getElementById('c'));
chart.setOption({{
  backgroundColor: '#0f1b2d',
  title: {{text: '{title}', left: 20, top: 14, textStyle: {{color: '#dfe7f3', fontSize: 18}}}},
  tooltip: {{formatter: function(p) {{
      var d = p.value;
      return '街区: ' + d[4] + '<br>价格: $' + d[2] + '<br>累计评论: ' + d[3];
  }}}},
  xAxis: {{type: 'value', name: '经度', nameTextStyle: {{color: '#9fb2c8'}}, axisLabel: {{color: '#9fb2c8'}}, splitLine: {{lineStyle: {{color: 'rgba(255,255,255,0.08)'}}}}}},
  yAxis: {{type: 'value', name: '纬度', nameTextStyle: {{color: '#9fb2c8'}}, axisLabel: {{color: '#9fb2c8'}}, splitLine: {{lineStyle: {{color: 'rgba(255,255,255,0.08)'}}}}}},
  series: [{{
    type: 'scatter', data: pts, symbolSize: function(d) {{ return Math.max(5, Math.min(22, Math.sqrt(d[3]) * 0.9)); }},
    itemStyle: {{opacity: 0.82}},
    visualMap: {{dimension: 2, min: 0, max: 1200, inRange: {{color: ['#2b6cb0', '#f6ad55', '#e53e3e']}},
                 textStyle: {{color: '#9fb2c8'}}, left: 20, bottom: 20}}
  }}]
}});
window.addEventListener('resize', function() {{ chart.resize(); }});
</script>
</body>
</html>"""


def build_funnel_page(data) -> str:
    funnel = data["funnel"]
    title = "评论活跃漏斗图"
    return html_head(title, ECHARTS_FIG) + f"""
<div id="c" style="width:100%;height:100vh;"></div>
<script>
var funnel = {json.dumps(funnel, ensure_ascii=False)};
var chart = echarts.init(document.getElementById('c'));
chart.setOption({{
  backgroundColor: '#0f1b2d',
  title: {{text: '{title}', left: 'center', top: 16, textStyle: {{color: '#dfe7f3', fontSize: 20}}}},
  tooltip: {{trigger: 'item', formatter: '{{b}}: {{c}} 套'}},
  series: [{{
    type: 'funnel', left: '18%', width: '64%', top: 80, bottom: 60,
    min: 0, max: 500, sort: 'descending', gap: 4,
    label: {{show: true, position: 'inside', formatter: '{{b}}  {{c}}', color: '#fff', fontSize: 13}},
    data: funnel,
    itemStyle: {{borderColor: '#0f1b2d', borderWidth: 2}}
  }}]
}});
window.addEventListener('resize', function() {{ chart.resize(); }});
</script>
</body>
</html>"""


def build_dashboard(data) -> str:
    listings = data["listings"]
    monthly = data["monthly"]
    recent12 = data["recent12"]
    neigh_list = sorted({x["neigh"] for x in listings})
    room_list = sorted({x["room"] for x in listings})

    kpis = {
        "房源总数": len(listings),
        "累计评论": sum(x["reviews"] for x in listings),
        "平均价格": round(sum(x["price"] for x in listings) / len(listings), 1),
        "中位价格": round(sorted(x["price"] for x in listings)[len(listings) // 2], 1),
    }

    return html_head("Albany 商业数据分析大屏", ECHARTS_LOCAL) + f"""
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0b1524; color:#dfe7f3; font-family:'Microsoft YaHei',sans-serif; }}
  .header {{ text-align:center; padding:14px 0 6px; }}
  .header h1 {{ font-size:22px; letter-spacing:2px; }}
  .header p {{ color:#7f95b0; font-size:12px; margin-top:4px; }}
  .filter {{ display:flex; align-items:center; justify-content:center; gap:10px; padding:8px 0; font-size:13px; flex-wrap:wrap; }}
  .filter select, .filter button {{ background:#12233c; color:#dfe7f3; border:1px solid #2c4a73; border-radius:4px; padding:4px 8px; font-size:12px; }}
  .filter .opt-group {{ display:flex; gap:6px; flex-wrap:wrap; }}
  .filter label {{ display:flex; align-items:center; gap:3px; cursor:pointer; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; padding:10px 16px; }}
  .kpi {{ background:#12233c; border:1px solid #2c4a73; border-radius:8px; padding:12px 16px; }}
  .kpi .v {{ font-size:26px; font-weight:700; color:#6db3f2; }}
  .kpi .k {{ font-size:12px; color:#7f95b0; margin-top:2px; }}
  .grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; padding:0 16px 16px; }}
  .panel {{ background:#12233c; border:1px solid #2c4a73; border-radius:8px; padding:8px; }}
  .panel h3 {{ font-size:13px; color:#9fc2ec; padding:2px 4px 6px; }}
  .chart {{ width:100%; height:260px; }}
  @media (max-width:1100px) {{ .grid {{ grid-template-columns:1fr; }} }}
</style>
<div class="header">
  <h1>Albany 短租市场商业数据分析大屏</h1>
  <p>数据来源：Inside Airbnb · 清洗后 500 套房源 / 30,242 条评论（2014-07 ~ 2026-09）</p>
</div>
<div class="filter">
  <span>房型：</span>
  <select id="fRoom">
    <option value="ALL">全部</option>
    {''.join(f'<option value="{r}">{r}</option>' for r in room_list)}
  </select>
  <span>街区（可多选）：</span>
  <div class="opt-group" id="neighGroup">
    <button data-n="ALL" class="on">全选</button>
    {''.join(f'<button data-n="{n}">{n.replace(" WARD","")}</button>' for n in neigh_list)}
  </div>
</div>
<div class="kpis">
  <div class="kpi"><div class="v" id="kpi0">-</div><div class="k">房源总数</div></div>
  <div class="kpi"><div class="v" id="kpi1">-</div><div class="k">累计评论数</div></div>
  <div class="kpi"><div class="v" id="kpi2">-</div><div class="k">平均价格($/晚)</div></div>
  <div class="kpi"><div class="v" id="kpi3">-</div><div class="k">中位价格($/晚)</div></div>
</div>
<div class="grid">
  <div class="panel"><h3>月度评论趋势</h3><div id="cTrend" class="chart"></div></div>
  <div class="panel"><h3>房型结构</h3><div id="cRoom" class="chart"></div></div>
  <div class="panel"><h3>RFM 客户价值（玫瑰图）</h3><div id="cRfm" class="chart"></div></div>
  <div class="panel"><h3>Top10 街区房源数量</h3><div id="cNeigh" class="chart"></div></div>
  <div class="panel"><h3>Top10 街区平均价格</h3><div id="cPrice" class="chart"></div></div>
  <div class="panel"><h3>房源地理分布</h3><div id="cGeo" class="chart"></div></div>
  <div class="panel" style="grid-column: span 2;"><h3>街区活跃度（近12月评论量）</h3><div id="cActive" class="chart"></div></div>
  <div class="panel"><h3>评论活跃漏斗</h3><div id="cFunnel" class="chart"></div></div>
</div>
<script>
var ALL = {json.dumps(listings, ensure_ascii=False)};
var MONTHLY = {json.dumps(monthly, ensure_ascii=False)};
var RECENT12 = {json.dumps(recent12, ensure_ascii=False)};
var FUNNEL = {json.dumps(data["funnel"], ensure_ascii=False)};
var TOTAL_REV = {json.dumps(data["total_reviews"])};
var ROOM_CN = {{"Entire home/apt":"整套","Private room":"独立","Shared room":"合住"}};

var charts = {{}};
['cTrend','cRoom','cRfm','cNeigh','cPrice','cGeo','cActive','cFunnel'].forEach(function(id){{
  charts[id] = echarts.init(document.getElementById(id));
}});

var selRoom = 'ALL';
var selNeigh = {{}};
document.querySelectorAll('#neighGroup button').forEach(function(b){{
  selNeigh[b.dataset.n] = (b.dataset.n === 'ALL');
  b.onclick = function(){{
    if (b.dataset.n === 'ALL') {{
      var all = !selNeigh['ALL'];
      document.querySelectorAll('#neighGroup button').forEach(function(x){{
        selNeigh[x.dataset.n] = all; x.className = all ? 'on' : '';
      }});
    }} else {{
      selNeigh[b.dataset.n] = !selNeigh[b.dataset.n];
      b.className = selNeigh[b.dataset.n] ? 'on' : '';
      var on = document.querySelectorAll('#neighGroup button[data-n!="ALL"].on').length;
      selNeigh['ALL'] = (on === document.querySelectorAll('#neighGroup button[data-n!="ALL"]').length);
      document.querySelector('#neighGroup button[data-n="ALL"]').className = selNeigh['ALL'] ? 'on' : '';
    }}
    updateAll();
  }};
}});
document.getElementById('fRoom').onchange = function(){{ selRoom = this.value; updateAll(); }};

function filtered() {{
  return ALL.filter(function(x){{
    if (selRoom !== 'ALL' && x.room !== selRoom) return false;
    if (!selNeigh['ALL'] && !selNeigh[x.neigh]) return false;
    return true;
  }});
}}

function updateAll() {{
  var rows = filtered();
  // KPI
  var n = rows.length;
  var rev = rows.reduce(function(s,x){{return s+x.reviews;}},0);
  var priceArr = rows.map(function(x){{return x.price;}}).sort(function(a,b){{return a-b;}});
  var avg = n ? (rows.reduce(function(s,x){{return s+x.price;}},0)/n).toFixed(1) : 0;
  var med = n ? priceArr[Math.floor(n/2)].toFixed(1) : 0;
  document.getElementById('kpi0').textContent = n;
  document.getElementById('kpi1').textContent = TOTAL_REV;
  document.getElementById('kpi2').textContent = '$' + avg;
  document.getElementById('kpi3').textContent = '$' + med;

  // 月度趋势（全量，不受筛选影响，加注释）
  charts.cTrend.setOption({{tooltip:{{trigger:'axis'}}, grid:{{left:44,right:12,top:24,bottom:24}},
    xAxis:{{type:'category',data:MONTHLY.map(function(m){{return m.m;}}),axisLabel:{{color:'#7f95b0',interval:11}}}},
    yAxis:{{type:'value',axisLabel:{{color:'#7f95b0'}},splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.08)'}}}}}},
    series:[{{type:'line',data:MONTHLY.map(function(m){{return m.v;}}),smooth:true,symbol:'none',
      lineStyle:{{color:'#6db3f2',width:1.6}},areaStyle:{{color:'rgba(109,179,242,0.15)'}}}}]}});

  // 房型饼图
  var roomCnt = {{}};
  rows.forEach(function(x){{ roomCnt[x.room] = (roomCnt[x.room]||0)+1; }});
  charts.cRoom.setOption({{tooltip:{{trigger:'item',formatter:'{{b}}: {{c}} ({{d}}%)'}},
    series:[{{type:'pie',radius:['38%','66%'],center:['50%','55%'],
      data:Object.keys(roomCnt).map(function(k){{return {{name:ROOM_CN[k]||k,value:roomCnt[k]}};}}),
      label:{{color:'#dfe7f3'}}, labelLine:{{lineStyle:{{color:'#5a7090'}}}}}}]}});

  // RFM 玫瑰图
  var segCnt = {{}};
  rows.forEach(function(x){{ segCnt[x.seg] = (segCnt[x.seg]||0)+1; }});
  var segOrder = ['明星房源','潜力房源','高价低评','新上架','需激活','高活跃流失','高价沉寂','沉默房源'];
  var segData = segOrder.filter(function(s){{return segCnt[s];}}).map(function(s){{return {{name:s,value:segCnt[s]}};}});
  charts.cRfm.setOption({{tooltip:{{trigger:'item',formatter:'{{b}}: {{c}} 套'}},
    series:[{{type:'pie',roseType:'area',radius:['18%','72%'],center:['50%','55%'],
      data:segData,label:{{color:'#dfe7f3',fontSize:10}},labelLine:{{lineStyle:{{color:'#5a7090'}}}}}}]}});

  // Top10 街区房源
  var neighCnt = {{}};
  rows.forEach(function(x){{ neighCnt[x.neigh] = (neighCnt[x.neigh]||0)+1; }});
  var topN = Object.entries(neighCnt).sort(function(a,b){{return b[1]-a[1];}}).slice(0,10);
  charts.cNeigh.setOption({{tooltip:{{}},grid:{{left:70,right:20,top:20,bottom:24}},
    xAxis:{{type:'value',axisLabel:{{color:'#7f95b0'}},splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.08)'}}}}}},
    yAxis:{{type:'category',data:topN.map(function(d){{return d[0].replace(' WARD','');}}).reverse(),
      axisLabel:{{color:'#dfe7f3'}}}},
    series:[{{type:'bar',data:topN.map(function(d){{return d[1];}}).reverse(),itemStyle:{{color:'#6db3f2'}}}}]}});

  // Top10 街区均价
  var neighSum = {{}};
  rows.forEach(function(x){{ neighSum[x.neigh] = neighSum[x.neigh]||{{s:0,n:0}}; neighSum[x.neigh].s+=x.price; neighSum[x.neigh].n+=1; }});
  var topP = Object.entries(neighSum).map(function(e){{return [e[0], +(e[1].s/e[1].n).toFixed(0)];}})
      .sort(function(a,b){{return b[1]-a[1];}}).slice(0,10);
  charts.cPrice.setOption({{tooltip:{{formatter:function(p){{return p.name + ': $' + p.value;}}}},
    grid:{{left:70,right:20,top:20,bottom:24}},
    xAxis:{{type:'value',axisLabel:{{color:'#7f95b0'}},splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.08)'}}}}}},
    yAxis:{{type:'category',data:topP.map(function(d){{return d[0].replace(' WARD','');}}).reverse(),axisLabel:{{color:'#dfe7f3'}}}},
    series:[{{type:'bar',data:topP.map(function(d){{return d[1];}}).reverse(),itemStyle:{{color:'#e07b39'}}}}]}});

  // 地理散点
  charts.cGeo.setOption({{tooltip:{{formatter:function(p){{var d=p.value; return d[4]+'<br>价格: $'+d[2]+'<br>评论: '+d[3];}}}},
    xAxis:{{type:'value',name:'经度',nameTextStyle:{{color:'#7f95b0'}},axisLabel:{{color:'#7f95b0'}},splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.06)'}}}}}},
    yAxis:{{type:'value',name:'纬度',nameTextStyle:{{color:'#7f95b0'}},axisLabel:{{color:'#7f95b0'}},splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.06)'}}}}}},
    series:[{{type:'scatter',data:rows.map(function(x){{return [x.lon,x.lat,x.price,x.reviews,x.neigh];}}),
      symbolSize:function(d){{return Math.max(4,Math.min(18,Math.sqrt(d[3])*0.8));}},
      itemStyle:{{opacity:0.75}},
      visualMap:{{show:false,dimension:2,min:0,max:1200,inRange:{{color:['#2b6cb0','#f6ad55','#e53e3e']}}}}}}]}});

  // 街区活跃度（近12月评论量）
  var actData = Object.entries(RECENT12).filter(function(d){{ return selNeigh['ALL'] || selNeigh[d[0]]; }})
      .sort(function(a,b){{return b[1]-a[1];}}).slice(0,10);
  charts.cActive.setOption({{tooltip:{{}},grid:{{left:70,right:20,top:20,bottom:24}},
    xAxis:{{type:'value',axisLabel:{{color:'#7f95b0'}},splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.08)'}}}}}},
    yAxis:{{type:'category',data:actData.map(function(d){{return d[0].replace(' WARD','');}}).reverse(),axisLabel:{{color:'#dfe7f3'}}}},
    series:[{{type:'bar',data:actData.map(function(d){{return d[1];}}).reverse(),itemStyle:{{color:'#5aa469'}}}}]}});

  // 漏斗
  charts.cFunnel.setOption({{tooltip:{{trigger:'item',formatter:'{{b}}: {{c}} 套'}},
    series:[{{type:'funnel',left:'6%',width:'88%',top:16,bottom:8,min:0,max:500,sort:'descending',gap:3,
      label:{{show:true,position:'inside',formatter:'{{b}}  {{c}}',color:'#fff',fontSize:11}},
      data:FUNNEL}}]}});
}}
updateAll();
window.addEventListener('resize', function(){{ Object.values(charts).forEach(function(c){{c.resize();}}); }});
</script>
</body>
</html>"""


def main():
    data = load_data()
    os.makedirs(FIG_DIR, exist_ok=True)
    with open(os.path.join(FIG_DIR, "fig19_房源地图散点.html"), "w", encoding="utf-8") as f:
        f.write(build_map_page(data))
    with open(os.path.join(FIG_DIR, "fig20_评论活跃漏斗.html"), "w", encoding="utf-8") as f:
        f.write(build_funnel_page(data))
    with open(os.path.join(ROOT, "dashboard.html"), "w", encoding="utf-8") as f:
        f.write(build_dashboard(data))
    print("[dashboard] fig19/fig20 已生成于 outputs/figures/")
    print("[dashboard] dashboard.html 已生成于项目根目录")
    print("[dashboard] 数据规模:", len(data["listings"]), "套房源,", len(data["monthly"]), "个月度观测")


if __name__ == "__main__":
    sys.exit(main())
