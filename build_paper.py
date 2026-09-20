# -*- coding: utf-8 -*-
"""把 paper.json 畫成每日分析報告網頁 paper.html。"""
import json
import html

IN_PATH = "paper.json"
OUT_PATH = "paper.html"
MAIN = "00631L_strategy"

CSS = """
:root{
  --bg:#0f1420; --panel:#161d2e; --panel-2:#1c2438; --border:#2a3350;
  --text:#e8ecf5; --text-dim:#8b93ab; --accent:#4f8cff; --accent-2:#a78bfa;
  --up:#ff5c5c; --down:#2fbf71; --gold:#ffc94d;
}
*{box-sizing:border-box;}
body{margin:0; background:linear-gradient(180deg,#0b0f18,#0f1420 400px); color:var(--text);
  font-family:"Segoe UI","PingFang TC","Microsoft JhengHei",sans-serif;}
.wrap{max-width:1040px; margin:0 auto; padding:32px 20px 80px;}
a{color:var(--accent); text-decoration:none;} a:hover{text-decoration:underline;}
header h1{font-size:27px; margin:0 0 6px; font-weight:800;}
header .sub{color:var(--text-dim); font-size:13.5px; line-height:1.9;}
header .sub b{color:var(--text);}
.section{margin-top:34px;}
.section h2{font-size:18px; margin:0 0 14px; display:flex; align-items:center; gap:9px;}
.section h2 .note{font-size:12.5px; color:var(--text-dim); font-weight:400;}
.panel{background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:18px 20px;}
.grid{display:grid; gap:12px;}
.g4{grid-template-columns:repeat(4,1fr);} .g3{grid-template-columns:repeat(3,1fr);}
.g2{grid-template-columns:repeat(2,1fr);}
@media (max-width:760px){.g4,.g3,.g2{grid-template-columns:repeat(2,1fr);}}
@media (max-width:460px){.g4,.g3,.g2{grid-template-columns:1fr;}}
.stat{background:var(--panel-2); border:1px solid var(--border); border-radius:12px; padding:13px 15px;}
.stat .k{font-size:12px; color:var(--text-dim); margin-bottom:5px;}
.stat .v{font-size:clamp(16px,2vw,21px); font-weight:800; letter-spacing:.3px; white-space:nowrap;}
.stat .v.sm{font-size:17px;}
.stat .x{font-size:11.5px; color:var(--text-dim); margin-top:4px;}
.up{color:var(--up);} .down{color:var(--down);} .dim{color:var(--text-dim);}
.hero{background:linear-gradient(135deg,rgba(79,140,255,.13),rgba(167,139,250,.07));
  border:1px solid rgba(79,140,255,.35);}
.hero .v{font-size:clamp(20px,2.6vw,30px); white-space:nowrap;}
.pill{display:inline-block; font-size:12px; padding:4px 12px; border-radius:999px;
  border:1px solid var(--border); background:var(--panel-2); color:var(--text-dim);}
.pill.hold{color:var(--up); border-color:rgba(255,92,92,.45); background:rgba(255,92,92,.1);}
.pill.out{color:var(--gold); border-color:rgba(255,201,77,.45); background:rgba(255,201,77,.1);}
table{width:100%; border-collapse:collapse; font-size:13.5px;}
th,td{padding:9px 11px; text-align:right; border-bottom:1px solid var(--border); white-space:nowrap;}
th{color:var(--text-dim); font-weight:600; font-size:12px; text-align:right;}
th:first-child,td:first-child{text-align:left;}
tbody tr:hover{background:rgba(79,140,255,.06);}
tr.main td{background:rgba(79,140,255,.09); font-weight:700;}
.scroll{overflow-x:auto;}
.empty{color:var(--text-dim); font-size:13.5px; padding:6px 0;}
.foot{margin-top:40px; font-size:12.5px; color:var(--text-dim); line-height:2;
  border-top:1px solid var(--border); padding-top:18px;}
.foot b{color:var(--text);}
.bar{height:7px; border-radius:4px; background:var(--panel-2); overflow:hidden; margin-top:8px;}
.bar i{display:block; height:100%; background:linear-gradient(90deg,var(--accent),var(--accent-2));}
"""


def money(n):
    return f"{round(n):,}"


def pct(v, sign=True):
    if v is None:
        return "—"
    cls = "up" if v > 0 else ("down" if v < 0 else "dim")
    return f'<span class="{cls}">{v:+.2f}%</span>' if sign else f"{v:.2f}%"


def stat(k, v, x="", hero=False):
    return (f'<div class="stat{" hero" if hero else ""}"><div class="k">{k}</div>'
            f'<div class="v">{v}</div>{f"<div class=x>{x}</div>" if x else ""}</div>')


def equity_svg(accounts, keys, w=980, h=190):
    """四個帳戶的淨值曲線(以 100 萬為基準的百分比)。"""
    series = {k: [p["equity"] for p in accounts[k]["history"]] for k in keys}
    n = max((len(v) for v in series.values()), default=0)
    if n < 2:
        return ""
    lo = min(min(v) for v in series.values())
    hi = max(max(v) for v in series.values())
    pad = (hi - lo) * 0.12 or 1000
    lo, hi = lo - pad, hi + pad
    colors = {"00631L_strategy": "#4f8cff", "00631L_bh": "#8b93ab",
              "0050_strategy": "#a78bfa", "0050_bh": "#5a6b85"}
    paths = []
    for k, vals in series.items():
        pts = " ".join(f"{40 + i * (w - 60) / (n - 1):.1f},"
                       f"{h - 24 - (v - lo) / (hi - lo) * (h - 48):.1f}"
                       for i, v in enumerate(vals))
        wide = 2.6 if k == MAIN else 1.5
        paths.append(f'<polyline points="{pts}" fill="none" stroke="{colors[k]}" '
                     f'stroke-width="{wide}" stroke-linejoin="round"/>')
    base_y = h - 24 - (1_000_000 - lo) / (hi - lo) * (h - 48)
    legend = " ".join(
        f'<span style="color:{colors[k]}">&#9632;</span> '
        f'<span class="dim">{html.escape(accounts[k]["label"])}</span>' for k in keys)
    return (f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto">'
            f'<line x1="40" y1="{base_y:.1f}" x2="{w - 20}" y2="{base_y:.1f}" '
            f'stroke="#2a3350" stroke-dasharray="4 4"/>'
            f'<text x="42" y="{base_y - 6:.1f}" fill="#8b93ab" font-size="11">100萬</text>'
            + "".join(paths) + "</svg>"
            f'<div style="font-size:12px;margin-top:8px;display:flex;gap:16px;flex-wrap:wrap">{legend}</div>')


def build(d):
    cfg, sig = d["config"], d["signal"]
    a = d["accounts"]
    started = d["started"]
    m = a[MAIN]

    # ---- 今日訊號 ----
    hold = sig["hold"]
    pill = (f'<span class="pill {"hold" if hold else "out"}">'
            f'{"持有中" if hold else "空手中"}</span>')
    dist = sig["distance_to_exit_pct"]
    sig_html = f"""
<div class="panel">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
    <div style="font-size:15px;font-weight:700">{sig['date']} 收盤訊號 {pill}</div>
    <div class="dim" style="font-size:13px">下一個交易日動作:<b style="color:var(--text)">{sig['next_action']}</b></div>
  </div>
  <div class="grid g4">
    {stat("加權指數收盤", f"{sig['twii_close']:,.0f}")}
    {stat("200日均線", f"{sig['ma200']:,.0f}")}
    {stat("出場線 (200MA×0.98)", f"{sig['exit_line']:,.0f}", "跌破此線 → 隔日開盤全數賣出")}
    {stat("距離出場線", f'<span class="up">+{dist:.1f}%</span>',
          "指數還要再跌這麼多才觸發出場")}
  </div>
  <div class="bar"><i style="width:{min(100, max(2, 100 - dist * 2)):.0f}%"></i></div>
  <div class="dim" style="font-size:11.5px;margin-top:6px">
    進度條:滿格代表已貼近出場線。目前距離 {dist:.1f}%,屬於安全區。</div>
</div>"""

    # ---- 主帳戶 ----
    if started:
        mv, cash = m["history"][-1]["market_value"], m["history"][-1]["cash"]
        pnl = m["equity"] - d["initial_capital"]
        hero = f"""
<div class="grid g4">
  {stat("總資產", f'NT$ {money(m["equity"])}',
        f'起始 NT$ {money(d["initial_capital"])}', hero=True)}
  {stat("累積報酬", pct(m["total_return_pct"]),
        f'損益 NT$ {pnl:+,}')}
  {stat("持股市值", f'NT$ {money(mv)}',
        f'{m["shares"]:,} 股 @ {m["history"][-1]["close"]}')}
  {stat("可用現金", f'NT$ {money(cash)}', f'最大回撤 {m["max_drawdown_pct"]:.2f}%')}
</div>"""
    else:
        p = d["plan"][MAIN]
        hero = f"""
<div class="grid g4">
  {stat("帳戶資金", f'NT$ {money(d["initial_capital"])}', "尚未建倉", hero=True)}
  {stat("預定買進", f'{p["shares"]:,} 股', f'00631L 參考價 {p["price"]}')}
  {stat("預估成交金額", f'NT$ {money(p["amount"])}', f'手續費 NT$ {p["fee"]:,}')}
  {stat("剩餘現金", f'NT$ {money(p["cash_left"])}', "零股全額投入")}
</div>
<div class="empty" style="margin-top:12px">
  起算日 <b style="color:var(--text)">{d['inception']}</b> 尚未到。
  當天開盤即以開盤價建倉,之後每個交易日 15:00 自動更新這份報告。
</div>"""

    # ---- 帳戶比較 ----
    rows = []
    for k, v in a.items():
        cls = ' class="main"' if k == MAIN else ""
        if started:
            rows.append(
                f'<tr{cls}><td>{html.escape(v["label"])}</td>'
                f'<td>NT$ {money(v["equity"])}</td><td>{pct(v["total_return_pct"])}</td>'
                f'<td class="dim">{v["max_drawdown_pct"]:.2f}%</td>'
                f'<td>{"持有" if v["shares"] else "空手"}</td>'
                f'<td class="dim">{len(v["trades"])}</td>'
                f'<td class="dim">NT$ {money(v["fee_sum"] + v["tax_sum"])}</td></tr>')
        else:
            rows.append(f'<tr{cls}><td>{html.escape(v["label"])}</td>'
                        f'<td class="dim" colspan="6">等待 {d["inception"]} 建倉</td></tr>')
    if started and d["twii_return_pct"] is not None:
        rows.append(f'<tr><td class="dim">加權指數(參考,無法直接買)</td>'
                    f'<td class="dim">—</td><td>{pct(d["twii_return_pct"])}</td>'
                    f'<td class="dim" colspan="4">—</td></tr>')
    compare = f"""
<div class="panel scroll"><table>
<thead><tr><th>帳戶</th><th>總資產</th><th>累積報酬</th><th>最大回撤</th>
<th>目前部位</th><th>交易次數</th><th>累積成本</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>"""

    # ---- 成本與融資 ----
    fee = m["fee_sum"] if started else 0
    tax = m["tax_sum"] if started else 0
    cost_html = f"""
<div class="panel">
  <div class="grid g4">
    {stat("累積手續費", f"NT$ {fee:,}",
          f'費率 {cfg["fee_rate_pct"]:.4f}% × 折扣 {cfg["fee_discount"]:g},最低 {cfg["fee_min"]} 元')}
    {stat("累積證交稅", f"NT$ {tax:,}", f'ETF 稅率 {cfg["tax_rate_pct"]:.2f}%,僅賣出時收')}
    {stat("融資餘額", '<span class="dim">NT$ 0</span>', "策略設定為不使用融資")}
    {stat("累積融資利息", '<span class="dim">NT$ 0</span>',
          f'年利率 {cfg["margin_annual_rate_pct"]:.2f}%(未動用)')}
  </div>
  <div class="dim" style="font-size:12.5px;margin-top:14px;line-height:1.9">
    <b style="color:var(--text)">為什麼融資是 0:</b>
    你指定不使用融資,因此帳戶資金上限就是 100 萬,不借款、不付利息、沒有斷頭風險。
    00631L 本身是每日重設的 2 倍槓桿 ETF,槓桿由發行商在基金內部用期貨達成,
    這部分的成本已經反映在它的淨值裡(不會另外向你收利息)。
    單邊來回總成本約 <b style="color:var(--text)">{(cfg["fee_rate_pct"] * cfg["fee_discount"] * 2 + cfg["tax_rate_pct"]):.3f}%</b>。
  </div>
</div>"""

    # ---- 交易紀錄 ----
    trades = m["trades"] if started else []
    if trades:
        trows = "".join(
            f'<tr><td>{t["date"]}</td>'
            f'<td><span class="{"up" if t["side"] == "買進" else "down"}">{t["side"]}</span></td>'
            f'<td>{t["shares"]:,}</td><td>{t["price"]}</td>'
            f'<td>NT$ {money(t["amount"])}</td><td class="dim">NT$ {t["fee"]:,}</td>'
            f'<td class="dim">NT$ {t["tax"]:,}</td></tr>' for t in reversed(trades))
        trade_html = (f'<div class="panel scroll"><table><thead><tr><th>日期</th><th>方向</th>'
                      f'<th>股數</th><th>成交價</th><th>金額</th><th>手續費</th><th>交易稅</th>'
                      f'</tr></thead><tbody>{trows}</tbody></table></div>')
    else:
        trade_html = ('<div class="panel"><div class="empty">尚無交易。'
                      '這條規則九年只出場 4 次,長時間沒有動作是正常的。</div></div>')

    # ---- 每日淨值 ----
    hist = m["history"][-30:] if started else []
    if hist:
        base = len(m["history"]) - len(hist)
        hrows = []
        for j in range(len(hist) - 1, -1, -1):
            x, idx = hist[j], base + j
            day = (x["equity"] / m["history"][idx - 1]["equity"] - 1) * 100 if idx else 0.0
            hrows.append(
                f'<tr><td>{x["date"]}</td><td>{x["close"]}</td>'
                f'<td>{x["shares"]:,}</td><td>NT$ {money(x["market_value"])}</td>'
                f'<td>NT$ {money(x["cash"])}</td><td>NT$ {money(x["equity"])}</td>'
                f'<td>{pct(day)}</td></tr>')
        daily_html = (f'<div class="panel scroll"><table><thead><tr><th>日期</th>'
                      f'<th>收盤</th><th>持股</th><th>市值</th><th>現金</th>'
                      f'<th>總資產</th><th>當日</th></tr></thead>'
                      f'<tbody>{"".join(hrows)}</tbody></table></div>')
        chart = f'<div class="panel" style="margin-bottom:12px">{equity_svg(a, list(a.keys()))}</div>'
    else:
        daily_html = '<div class="panel"><div class="empty">起算後每個交易日都會新增一列。</div></div>'
        chart = ""

    days = d["trading_days"]
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>100萬紙上交易實測 | 200MA 出場規則</title>
<style>{CSS}</style></head><body><div class="wrap">
<header>
  <h1>100 萬紙上交易實測</h1>
  <div class="sub">
    策略:<b>00631L 長期持有 + 加權指數跌破 200 日均線 2% 即全數出場</b><br>
    起算日 <b>{d['inception']}</b>・已測試 <b>{days}</b> 個交易日・
    資料日 <b>{d['last_data_date']}</b>・更新於 {d['generated_at']}<br>
    <a href="index.html">← 回成交量分析</a>
  </div>
</header>

<div class="section"><h2>今日訊號 <span class="note">T 日收盤判斷,T+1 開盤成交</span></h2>{sig_html}</div>
<div class="section"><h2>主帳戶 <span class="note">00631L + 出場規則</span></h2>{hero}</div>
<div class="section"><h2>帳戶比較 <span class="note">四個帳戶各 100 萬,同時起算</span></h2>{chart}{compare}</div>
<div class="section"><h2>成本與融資明細</h2>{cost_html}</div>
<div class="section"><h2>交易紀錄 <span class="note">主帳戶</span></h2>{trade_html}</div>
<div class="section"><h2>每日淨值 <span class="note">最近 30 個交易日</span></h2>{daily_html}</div>

<div class="foot">
  <b>規則全文(已凍結,不會再調整)</b><br>
  預設持有 00631L。加權指數收盤跌破 200 日均線 ×0.98 → 隔日開盤全數賣出;
  收盤站回 200 日均線 ×1.02 → 隔日開盤全數買回;其餘維持原狀。不使用融資。<br><br>
  <b>回測參考(2018-2026,含成本)</b><br>
  00631L 買進持有 +2194%、最大回撤 -55%、2022 年 -38%;
  套用本規則後 +2112%、最大回撤 -37%、2022 年 -19%,九年僅出場 4 次。
  180~250 日均線、緩衝 0~5% 的所有組合回撤都落在同一水準,顯示結果不是靠挑參數挑出來的。<br><br>
  <b>必須知道的限制</b><br>
  回測只涵蓋 9 年、其中只有 2018 與 2022 兩個空頭,樣本很薄;
  -37% 的回撤仍然很大,這條規則只把最壞情況從腰斬降到回撤三分之一,不是保護傘;
  它針對的是「空頭」,對 2026 年這種 -16% 的回檔完全不會反應。<br><br>
  本頁為紙上模擬,不是實際下單,未考慮滑價與零股流動性。所有數字僅供研究,不構成投資建議。
</div>
</div></body></html>"""


def main():
    with open(IN_PATH, encoding="utf-8") as f:
        d = json.load(f)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(build(d))
    print(f"已產生 {OUT_PATH}({'已起算' if d['started'] else '等待起算'},"
          f"{d['trading_days']} 個交易日)")


if __name__ == "__main__":
    main()
