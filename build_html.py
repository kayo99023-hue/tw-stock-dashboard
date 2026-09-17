# -*- coding: utf-8 -*-
"""讀取 data.json,產生 index.html(首頁)與 top100.html(成交量前100)。"""
import json

with open("data.json", "r", encoding="utf-8") as f:
    D = json.load(f)

CSS = """
:root{
  --bg:#0f1420; --panel:#161d2e; --panel-2:#1c2438; --border:#2a3350;
  --text:#e8ecf5; --text-dim:#8b93ab; --accent:#4f8cff; --accent-2:#a78bfa;
  --up:#ff5c5c; --down:#2fbf71; --gold:#ffc94d; --silver:#c9d2e0; --bronze:#e0995e;
}
*{box-sizing:border-box;}
body{
  margin:0; padding:0; background:linear-gradient(180deg,#0b0f18,#0f1420 400px);
  color:var(--text); font-family:"Segoe UI","PingFang TC","Microsoft JhengHei",sans-serif;
}
.wrap{max-width:1100px; margin:0 auto; padding:32px 20px 80px;}
header.top{margin-bottom:28px;}
header.top h1{font-size:28px; margin:0 0 6px; font-weight:800; letter-spacing:0.5px;}
header.top .sub{color:var(--text-dim); font-size:14px; line-height:1.8;}
header.top .sub b{color:var(--text);}
.live-status{
  display:inline-block; margin-top:10px; font-size:12.5px; padding:5px 12px; border-radius:999px;
  background:var(--panel-2); border:1px solid var(--border); color:var(--text-dim);
}
.live-status.live{color:var(--up); border-color:rgba(255,92,92,.4); background:rgba(255,92,92,.08);}
.live-status.loading{color:var(--accent);}
.live-status.error{color:#ffc94d;}
a{color:var(--accent); text-decoration:none;}
a:hover{text-decoration:underline;}
.section{margin-top:36px;}
.section-title{display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;}
.section-title h2{font-size:19px; margin:0; display:flex; align-items:center; gap:8px;}
.section-title .note{font-size:12.5px; color:var(--text-dim);}
.badge{display:inline-block; font-size:11px; padding:2px 8px; border-radius:999px; background:var(--panel-2); color:var(--text-dim); border:1px solid var(--border);}
.card-grid{display:grid; grid-template-columns:repeat(5,1fr); gap:12px;}
@media (max-width:900px){.card-grid{grid-template-columns:repeat(2,1fr);}}
@media (max-width:520px){.card-grid{grid-template-columns:1fr;}}
.card{
  background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:14px 14px 12px;
  position:relative; overflow:hidden; transition:transform .15s ease, border-color .15s ease;
}
.card:hover{transform:translateY(-2px); border-color:var(--accent);}
.card .rank{
  position:absolute; top:10px; right:12px; font-size:22px; font-weight:800; opacity:.18;
}
.card.r1 .rank{color:var(--gold); opacity:.5;} .card.r2 .rank{color:var(--silver); opacity:.5;} .card.r3 .rank{color:var(--bronze); opacity:.5;}
.card .rankchip{
  display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px; border-radius:6px;
  background:var(--panel-2); font-size:12px; font-weight:700; color:var(--text-dim); margin-bottom:8px;
}
.card.r1 .rankchip{background:var(--gold); color:#3a2c00;}
.card.r2 .rankchip{background:var(--silver); color:#20232b;}
.card.r3 .rankchip{background:var(--bronze); color:#3a2200;}
.card .code{font-size:12px; color:var(--text-dim);}
.card .name{font-size:16px; font-weight:700; margin:2px 0 8px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.card .metric{font-size:20px; font-weight:800;}
.card .metric.up{color:var(--up);} .card .metric.down{color:var(--down);}
.card .price-row{display:flex; align-items:baseline; gap:6px; margin-top:6px; font-size:12.5px; color:var(--text-dim);}
.card .price-row .chg.up{color:var(--up);} .card .price-row .chg.down{color:var(--down);}
.table-scroll{overflow-x:auto; border-radius:12px; border:1px solid var(--border);}
table{width:100%; min-width:640px; border-collapse:collapse; background:var(--panel);}
thead th{
  text-align:left; font-size:12.5px; color:var(--text-dim); font-weight:600; padding:10px 14px;
  background:var(--panel-2); border-bottom:1px solid var(--border);
}
tbody td{padding:10px 14px; border-bottom:1px solid var(--border); font-size:14px;}
tbody tr:last-child td{border-bottom:none;}
tbody tr:hover{background:var(--panel-2);}
td.num{text-align:right; font-variant-numeric:tabular-nums;}
.up{color:var(--up);} .down{color:var(--down);}
.rank-cell{width:40px; color:var(--text-dim); font-weight:700;}
.rank-cell.r1{color:var(--gold);} .rank-cell.r2{color:var(--silver);} .rank-cell.r3{color:var(--bronze);}
.backlink{display:inline-block; margin-bottom:18px; font-size:14px;}
.cta{
  display:inline-flex; align-items:center; gap:6px; margin-top:6px; font-size:13.5px;
  padding:8px 14px; border-radius:8px; background:var(--panel-2); border:1px solid var(--border); color:var(--accent);
}
.cta:hover{border-color:var(--accent); text-decoration:none;}
footer{margin-top:56px; padding-top:20px; border-top:1px solid var(--border); color:var(--text-dim); font-size:12.5px; line-height:2;}

.clickable-stock{cursor:pointer;}
.card.clickable-stock .chart-hint{position:absolute; bottom:12px; right:12px; font-size:14px; opacity:.35;}
.card.clickable-stock:hover .chart-hint{opacity:.9;}
tr.clickable-stock:hover{background:var(--panel-2);}

.chart-overlay{
  position:fixed; inset:0; background:rgba(6,9,16,.72); backdrop-filter:blur(2px);
  display:flex; align-items:center; justify-content:center; z-index:1000; padding:16px;
}
.chart-overlay[hidden]{display:none;}
.chart-modal{
  width:min(980px,100%); max-height:92vh; overflow:auto; background:var(--panel);
  border:1px solid var(--border); border-radius:16px; padding:18px 20px 20px;
}
.chart-modal-head{display:flex; align-items:flex-start; justify-content:space-between; gap:12px;}
.chart-title{font-size:19px; font-weight:800;}
.chart-sub{font-size:12.5px; color:var(--text-dim); margin-top:2px;}
.chart-close{
  background:var(--panel-2); border:1px solid var(--border); color:var(--text); border-radius:8px;
  width:32px; height:32px; font-size:15px; cursor:pointer; flex:none;
}
.chart-close:hover{border-color:var(--accent);}
.chart-legend{margin-top:10px; font-size:12.5px; color:var(--text-dim);}
.chart-legend .lg-row{display:flex; flex-wrap:wrap; gap:12px; padding:4px 0;}
.chart-legend .lg-main span{color:var(--text-dim);}
.chart-legend .lg-main b{color:var(--text); font-size:14px;}
.chart-legend .lg-main .up{color:var(--up);} .chart-legend .lg-main .down{color:var(--down);}
.chart-legend .lg-sma span{font-weight:600;}
.chart-range-btns{display:flex; gap:6px; margin:10px 0 4px;}
.chart-range-btns button{
  background:var(--panel-2); border:1px solid var(--border); color:var(--text-dim); font-size:12px;
  padding:5px 12px; border-radius:999px; cursor:pointer;
}
.chart-range-btns button.active{color:var(--text); border-color:var(--accent); background:rgba(79,140,255,.15);}
.chart-container{width:100%; height:440px; margin-top:8px;}
.chart-note{margin-top:10px; font-size:11.5px; color:var(--text-dim);}
@media (max-width:640px){.chart-container{height:360px;} .chart-legend .lg-row{gap:8px; font-size:11.5px;}}
"""

SCRIPTS = """
<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script src="history_data.js"></script>
<script src="chart.js"></script>
<script src="live.js"></script>
<script>
document.addEventListener('click', function (e) {
  var el = e.target.closest('.clickable-stock');
  if (el) window.openStockChart(el.dataset.code, el.dataset.name);
});
</script>
"""


def fmt_int(n):
    return f"{n:,}"


def fmt_vol_lots(n):
    """成交股數轉「張」(1張=1000股),方便閱讀"""
    return f"{n/1000:,.0f} 張"


def chg_sign(d):
    return {"up": "+", "down": "-", "flat": ""}[d]


def chg_pct_str(it):
    """依收盤價與漲跌價差反推漲跌幅(%)"""
    close = float(str(it["close"]).replace(",", ""))
    amt = float(str(it["change_amt"]).replace(",", ""))
    d = it["change_dir"]
    if d == "flat" or amt == 0:
        return "0.00%"
    prev = close - amt if d == "up" else close + amt
    if prev <= 0:
        return "-"
    pct = amt / prev * 100
    return f"{chg_sign(d)}{pct:.2f}%"


def esc_attr(s):
    return str(s).replace("&", "&amp;").replace('"', "&quot;")


def stock_cards(items, limit=10):
    cards = []
    for it in items[:limit]:
        r = it["rank"]
        rclass = f"r{r}" if r <= 3 else ""
        cards.append(f"""
        <div class="card {rclass} clickable-stock" data-code="{it['code']}" data-name="{esc_attr(it['name'])}">
          <div class="rank">{r}</div>
          <div class="rankchip">{r}</div>
          <div class="code">{it['code']}</div>
          <div class="name">{it['name']}</div>
          <div class="metric">{fmt_vol_lots(it['volume'])}</div>
          <div class="price-row">
            <span>{it['close']} 元</span>
            <span class="chg {it['change_dir']}">{chg_pct_str(it)}</span>
          </div>
          <div class="chart-hint">📈</div>
        </div>""")
    return "\n".join(cards)


def ratio_table(items):
    rows = []
    for it in items:
        r = it["rank"]
        rclass = f"r{r}" if r <= 3 else ""
        rows.append(f"""
        <tr class="clickable-stock" data-code="{it['code']}" data-name="{esc_attr(it['name'])}">
          <td class="rank-cell {rclass}">{r}</td>
          <td>{it['code']}</td>
          <td>{it['name']}</td>
          <td class="num" style="color:var(--accent-2); font-weight:700;">{it['ratio']:.2f} 倍</td>
          <td class="num">{fmt_vol_lots(it['volume'])}</td>
          <td class="num">{fmt_vol_lots(it['prev3_sum'])}</td>
          <td class="num">{it['close']}</td>
          <td class="num {it['change_dir']}">{chg_pct_str(it)}</td>
        </tr>""")
    return "\n".join(rows)


def top100_rows(items):
    rows = []
    for it in items:
        r = it["rank"]
        rclass = f"r{r}" if r <= 3 else ""
        rows.append(f"""
        <tr class="clickable-stock" data-code="{it['code']}" data-name="{esc_attr(it['name'])}">
          <td class="rank-cell {rclass}">{r}</td>
          <td>{it['code']}</td>
          <td>{it['name']}</td>
          <td class="num">{fmt_vol_lots(it['volume'])}</td>
          <td class="num">{it['close']}</td>
          <td class="num {it['change_dir']}">{chg_pct_str(it)}</td>
        </tr>""")
    return "\n".join(rows)


INDEX_HTML = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>台股成交量分析</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <h1>📊 台股每日成交量分析</h1>
    <div class="sub">
      交易日:<b>{D['today']}</b> ・ 比較基準(近三個交易日):<b>{', '.join(D['prev_days'])}</b><br>
      資料來源:證交所每日收盤行情(MI_INDEX) ・ 共納入 <b>{D['total_stocks']}</b> 檔上市普通股 ・ 產生時間 {D['generated_at']}
    </div>
    <div id="liveStatus" class="live-status idle">⚪ 載入中…</div>
  </header>

  <div class="section">
    <div class="section-title">
      <h2>🏆 今日成交量 Top 10</h2>
      <span class="badge">單位:張(1張=1000股)</span>
    </div>
    <div class="card-grid" id="top10-cards">
      {stock_cards(D['top100_by_volume'], 10)}
    </div>
    <a class="cta" href="top100.html">查看今日成交量前 100 名 →</a>
  </div>

  <div class="section">
    <div class="section-title">
      <h2>🔥 爆量股 Top 10<span class="badge" style="margin-left:8px;">今日量 ÷ 近三日總量</span></h2>
      <span class="note">僅列今日成交量 ≥ {fmt_vol_lots(D['ratio_min_volume'])} 的股票,避免冷門股雜訊</span>
    </div>
    <div class="table-scroll">
    <table>
      <thead>
        <tr>
          <th>排名</th><th>代號</th><th>名稱</th><th style="text-align:right">爆量倍數</th>
          <th style="text-align:right">今日量</th><th style="text-align:right">前三日總量</th>
          <th style="text-align:right">收盤價</th><th style="text-align:right">漲跌幅</th>
        </tr>
      </thead>
      <tbody id="ratio-tbody">
        {ratio_table(D['top10_by_ratio'])}
      </tbody>
    </table>
    </div>
  </div>

  <footer>
    「爆量倍數」= 今日成交股數 ÷ (前一、前二、前三個交易日成交股數總和)。倍數越高代表今天的量相對近期突然放大越多。<br>
    資料每日收盤後才會更新,重新產生請依序執行 fetch_data.py 與 build_html.py。
  </footer>
</div>
{SCRIPTS}
</body>
</html>
"""

TOP100_HTML = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>今日成交量前100名</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <a class="backlink" href="index.html">← 回首頁</a>
  <header class="top">
    <h1>今日成交量 Top 100</h1>
    <div class="sub">交易日:<b>{D['today']}</b> ・ 資料來源:證交所每日收盤行情(MI_INDEX)</div>
    <div id="liveStatus" class="live-status idle">⚪ 載入中…</div>
  </header>
  <div class="table-scroll">
  <table>
    <thead>
      <tr>
        <th>排名</th><th>代號</th><th>名稱</th>
        <th style="text-align:right">成交量</th><th style="text-align:right">收盤價</th><th style="text-align:right">漲跌幅</th>
      </tr>
    </thead>
    <tbody id="top100-tbody">
      {top100_rows(D['top100_by_volume'])}
    </tbody>
  </table>
  </div>
  <footer>資料每日收盤後才會更新,重新產生請依序執行 fetch_data.py 與 build_html.py。</footer>
</div>
{SCRIPTS}
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(INDEX_HTML)
with open("top100.html", "w", encoding="utf-8") as f:
    f.write(TOP100_HTML)

print("已產生 index.html 與 top100.html")
