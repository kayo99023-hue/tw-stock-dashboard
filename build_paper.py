# -*- coding: utf-8 -*-
"""把 paper.json 畫成每日分析報告網頁 paper.html(含融資版本,2026-09-22)。"""
import json
import html

IN_PATH = "paper.json"
OUT_PATH = "paper.html"

COLORS = {
    "00631L_margin_rule": "#4f8cff",
    "00631L_margin_bh":   "#ff5c5c",
    "00631L_rule":        "#a78bfa",
    "00631L_bh":          "#6b7590",
    "0050_margin_rule":   "#2fbf71",
    "0050_bh":            "#8b93ab",
}

CSS = """
:root{
  --bg:#0f1420; --panel:#161d2e; --panel-2:#1c2438; --border:#2a3350;
  --text:#e8ecf5; --text-dim:#8b93ab; --accent:#4f8cff; --accent-2:#a78bfa;
  --up:#ff5c5c; --down:#2fbf71; --gold:#ffc94d;
}
*{box-sizing:border-box;}
body{margin:0; background:linear-gradient(180deg,#0b0f18,#0f1420 400px); color:var(--text);
  font-family:"Segoe UI","PingFang TC","Microsoft JhengHei",sans-serif;}
.wrap{max-width:1080px; margin:0 auto; padding:32px 20px 80px;}
a{color:var(--accent); text-decoration:none;} a:hover{text-decoration:underline;}
header h1{font-size:27px; margin:0 0 6px; font-weight:800;}
header .sub{color:var(--text-dim); font-size:13.5px; line-height:1.9;}
header .sub b{color:var(--text);}
.section{margin-top:34px;}
.section h2{font-size:18px; margin:0 0 14px; display:flex; align-items:center; gap:9px;}
.section h2 .note{font-size:12.5px; color:var(--text-dim); font-weight:400;}
.panel{background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:18px 20px;}
.panel + .panel{margin-top:12px;}
.grid{display:grid; gap:12px;}
.g4{grid-template-columns:repeat(4,1fr);} .g3{grid-template-columns:repeat(3,1fr);}
.g2{grid-template-columns:repeat(2,1fr);}
@media (max-width:760px){.g4,.g3,.g2{grid-template-columns:repeat(2,1fr);}}
@media (max-width:460px){.g4,.g3,.g2{grid-template-columns:1fr;}}
.stat{background:var(--panel-2); border:1px solid var(--border); border-radius:12px; padding:13px 15px;}
.stat .k{font-size:12px; color:var(--text-dim); margin-bottom:5px;}
.stat .v{font-size:clamp(15px,2vw,20px); font-weight:800; letter-spacing:.3px; white-space:nowrap;}
.stat .x{font-size:11.5px; color:var(--text-dim); margin-top:4px; white-space:normal;}
.up{color:var(--up);} .down{color:var(--down);} .dim{color:var(--text-dim);} .gold{color:var(--gold);}
.hero{background:linear-gradient(135deg,rgba(79,140,255,.13),rgba(167,139,250,.07));
  border:1px solid rgba(79,140,255,.35);}
.hero .v{font-size:clamp(19px,2.6vw,28px); white-space:nowrap;}
.pill{display:inline-block; font-size:12px; padding:4px 12px; border-radius:999px;
  border:1px solid var(--border); background:var(--panel-2); color:var(--text-dim);}
.pill.hold{color:var(--up); border-color:rgba(255,92,92,.45); background:rgba(255,92,92,.1);}
.pill.out{color:var(--gold); border-color:rgba(255,201,77,.45); background:rgba(255,201,77,.1);}
.pill.safe{color:var(--down); border-color:rgba(47,191,113,.45); background:rgba(47,191,113,.1);}
.pill.warn{color:var(--gold); border-color:rgba(255,201,77,.45); background:rgba(255,201,77,.1);}
.pill.danger{color:var(--up); border-color:rgba(255,92,92,.45); background:rgba(255,92,92,.12);}
table{width:100%; border-collapse:collapse; font-size:13px;}
th,td{padding:9px 10px; text-align:right; border-bottom:1px solid var(--border); white-space:nowrap;}
th{color:var(--text-dim); font-weight:600; font-size:11.5px; text-align:right;}
th:first-child,td:first-child{text-align:left;}
tbody tr:hover{background:rgba(79,140,255,.06);}
tr.main td{background:rgba(79,140,255,.09); font-weight:700;}
tr.liq td{background:rgba(255,92,92,.1);}
.scroll{overflow-x:auto;}
.empty{color:var(--text-dim); font-size:13.5px; padding:6px 0;}
.foot{margin-top:40px; font-size:12.5px; color:var(--text-dim); line-height:2;
  border-top:1px solid var(--border); padding-top:18px;}
.foot b{color:var(--text);}
.bar{height:7px; border-radius:4px; background:var(--panel-2); overflow:hidden; margin-top:8px;}
.bar i{display:block; height:100%; background:linear-gradient(90deg,var(--accent),var(--accent-2));}
.bar.warn i{background:linear-gradient(90deg,var(--down),var(--gold));}
.bar.danger i{background:linear-gradient(90deg,var(--gold),var(--up));}
.warnbox{border:1px solid rgba(255,201,77,.4); background:rgba(255,201,77,.07);
  border-radius:12px; padding:14px 16px; font-size:13px; line-height:1.9; color:var(--text-dim);}
.warnbox b{color:var(--gold);}
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


def ratio_pill(ratio, call):
    if ratio is None:
        return '<span class="dim">未使用融資</span>'
    cls = "danger" if (call or ratio < 130) else ("warn" if ratio < 150 else "safe")
    return f'<span class="pill {cls}">{ratio:.1f}%</span>'


def equity_svg(accounts, keys, w=1000, h=200):
    series = {k: [p["equity"] for p in accounts[k]["history"]] for k in keys}
    n = max((len(v) for v in series.values()), default=0)
    if n < 2:
        return ('<div class="empty">尚不足兩個交易日,還沒有曲線可畫。'
                '從明天收盤起,這裡會開始畫出每個帳戶的淨值走勢。</div>')
    lo = min(min(v) for v in series.values())
    hi = max(max(v) for v in series.values())
    pad = (hi - lo) * 0.12 or 1000
    lo, hi = lo - pad, hi + pad
    paths = []
    for k, vals in series.items():
        pts = " ".join(f"{40 + i * (w - 60) / (n - 1):.1f},"
                       f"{h - 24 - (v - lo) / (hi - lo) * (h - 48):.1f}"
                       for i, v in enumerate(vals))
        wide = 2.8 if k == keys[0] else 1.4
        paths.append(f'<polyline points="{pts}" fill="none" stroke="{COLORS.get(k, "#888")}" '
                     f'stroke-width="{wide}" stroke-linejoin="round"/>')
    base_y = h - 24 - (1_000_000 - lo) / (hi - lo) * (h - 48)
    legend = " ".join(
        f'<span style="color:{COLORS.get(k, "#888")}">&#9632;</span> '
        f'<span class="dim">{html.escape(accounts[k]["label"])}</span>' for k in keys)
    return (f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto">'
            f'<line x1="40" y1="{base_y:.1f}" x2="{w - 20}" y2="{base_y:.1f}" '
            f'stroke="#2a3350" stroke-dasharray="4 4"/>'
            f'<text x="42" y="{base_y - 6:.1f}" fill="#8b93ab" font-size="11">100萬自備款</text>'
            + "".join(paths) + "</svg>"
            f'<div style="font-size:12px;margin-top:8px;display:flex;gap:14px;flex-wrap:wrap">{legend}</div>')


def build(d):
    cfg, sig = d["config"], d["signal"]
    a = d["accounts"]
    keys = list(a.keys())
    main_key = d.get("main", keys[0])
    started = d["started"]
    m = a[main_key]

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

    # ---- 主帳戶(融資 + 出場規則) ----
    if started:
        cur = m["history"][-1]
        mv, cash, debt = cur["market_value"], cur["cash"], cur["debt"]
        ratio, call = cur["margin_ratio"], cur["call"]
        pnl = m["equity"] - d["initial_capital"]
        drop_to_call = None
        if debt > 0 and mv > 0:
            trigger_mv = cfg["call_ratio_pct"] / 100 * debt
            if mv > trigger_mv:
                drop_to_call = (1 - trigger_mv / mv) * 100
        hero = f"""
<div class="grid g4">
  {stat("總資產(自備款+損益)", f'NT$ {money(m["equity"])}',
        f'自備 NT$ {money(d["initial_capital"])}', hero=True)}
  {stat("累積報酬", pct(m["total_return_pct"]), f'損益 NT$ {pnl:+,}')}
  {stat("持股市值", f'NT$ {money(mv)}', f'{m["shares"]:,} 股 @ {cur["close"]}')}
  {stat("可用現金", f'NT$ {money(cash)}', f'最大回撤 {m["max_drawdown_pct"]:.2f}%')}
</div>
<div class="grid g4" style="margin-top:12px">
  {stat("融資餘額", f'NT$ {money(debt)}' if debt else '<span class="dim">NT$ 0</span>',
        f'融資成數 {cfg["margin_ltv_pct"]:.0f}%,槓桿 {cfg["margin_leverage"]:g}×')}
  {stat("整戶維持率", ratio_pill(ratio, call),
        (f'還可再跌約 <b style="color:var(--text)">{drop_to_call:.1f}%</b> 觸發追繳'
         if drop_to_call is not None else f'追繳線 {cfg["call_ratio_pct"]:.0f}%'))}
  {stat("累積融資利息", f'NT$ {money(m["interest_sum"])}',
        f'年利率 {cfg["margin_annual_rate_pct"]:.2f}%,每日計提(含假日)')}
  {stat("斷頭次數", str(m["liquidations"]),
        "本策略被追繳出場的次數" if m["liquidations"] == 0 else
        '<span class="up">曾被強制斷頭,詳見下方交易紀錄</span>')}
</div>"""
        if call or (ratio is not None and ratio < 150):
            hero += (f'<div class="warnbox" style="margin-top:12px">'
                     f'<b>⚠ 維持率偏低({ratio:.1f}%)</b>:'
                     f'追繳線是 {cfg["call_ratio_pct"]:.0f}%,跌破後若未在期限內補錢,'
                     f'系統會在下一個交易日開盤自動假設你被強制斷頭賣出。'
                     f'這是模擬,實際帳戶請自行注意券商的追繳通知。</div>')
    else:
        p = d["plan"][main_key]
        debt_txt = f'融資 NT$ {money(p["debt"])}' if p["debt"] else "不使用融資"
        hero = f"""
<div class="grid g4">
  {stat("自備款", f'NT$ {money(d["initial_capital"])}', "尚未建倉", hero=True)}
  {stat("預定買進", f'{p["shares"]:,} 股', f'00631L 參考價 {p["price"]}')}
  {stat("預估總成交金額", f'NT$ {money(p["amount"])}', debt_txt)}
  {stat("剩餘現金", f'NT$ {money(p["cash_left"])}', f'手續費 NT$ {p["fee"]:,}')}
</div>
<div class="empty" style="margin-top:12px">
  起算日 <b style="color:var(--text)">{d['inception']}</b> 尚未到。
  當天開盤即以開盤價建倉,之後每個交易日 15:00 自動更新這份報告。
</div>"""

    # ---- 帳戶比較 ----
    rows = []
    for k in keys:
        v = a[k]
        cls = ' class="main"' if k == main_key else ""
        if started:
            debt_cell = f'NT$ {money(v["debt"])}' if v["debt"] else '<span class="dim">—</span>'
            ratio_cell = ratio_pill(v["margin_ratio"], v["call"]) if v["ltv"] else '<span class="dim">—</span>'
            if v.get("dead"):
                ratio_cell = '<span class="pill danger">已出局</span>'
            liq_cell = f'<span class="up">{v["liquidations"]}</span>' if v["liquidations"] else "0"
            cost = v["fee_sum"] + v["tax_sum"] + v["interest_sum"]
            rows.append(
                f'<tr{cls}><td>{html.escape(v["label"])}</td>'
                f'<td>NT$ {money(v["equity"])}</td><td>{pct(v["total_return_pct"])}</td>'
                f'<td class="dim">{v["max_drawdown_pct"]:.2f}%</td>'
                f'<td>{debt_cell}</td><td>{ratio_cell}</td><td>{liq_cell}</td>'
                f'<td class="dim">{len(v["trades"])}</td>'
                f'<td class="dim">NT$ {money(cost)}</td></tr>')
        else:
            rows.append(f'<tr{cls}><td>{html.escape(v["label"])}</td>'
                        f'<td class="dim" colspan="8">等待 {d["inception"]} 建倉</td></tr>')
    if started and d["twii_return_pct"] is not None:
        rows.append(f'<tr><td class="dim">加權指數(參考,無法直接買)</td>'
                    f'<td class="dim">—</td><td>{pct(d["twii_return_pct"])}</td>'
                    f'<td class="dim" colspan="6">—</td></tr>')
    compare = f"""
<div class="panel scroll"><table>
<thead><tr><th>帳戶</th><th>總資產</th><th>累積報酬</th><th>最大回撤</th>
<th>融資餘額</th><th>整戶維持率</th><th>斷頭</th><th>交易次數</th><th>累積成本</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>"""

    chart = f'<div class="panel">{equity_svg(a, keys)}</div>' if started else ""

    # ---- 成本與融資明細 ----
    fee = m["fee_sum"] if started else 0
    tax = m["tax_sum"] if started else 0
    interest = m["interest_sum"] if started else 0
    cost_html = f"""
<div class="panel">
  <div class="grid g4">
    {stat("累積手續費(主帳戶)", f"NT$ {fee:,}",
          f'費率 {cfg["fee_rate_pct"]:.4f}% × 折扣 {cfg["fee_discount"]:g},最低 {cfg["fee_min"]} 元')}
    {stat("累積證交稅(主帳戶)", f"NT$ {tax:,}", f'ETF 稅率 {cfg["tax_rate_pct"]:.2f}%,僅賣出時收')}
    {stat("累積融資利息(主帳戶)", f"NT$ {interest:,}",
          f'{cfg["margin_annual_rate_pct"]:.2f}% ÷ 365 × 融資金額 × 天數,含週末假日')}
    {stat("融資成數 / 槓桿", f'{cfg["margin_ltv_pct"]:.0f}% / {cfg["margin_leverage"]:g}×',
          f'自備 {100 - cfg["margin_ltv_pct"]:.0f}%,融資 {cfg["margin_ltv_pct"]:.0f}%')}
  </div>
  <div class="dim" style="font-size:12.5px;margin-top:14px;line-height:1.9">
    <b style="color:var(--text)">融資規則:</b>
    建倉時整戶維持率為 <b style="color:var(--text)">{cfg["initial_ratio_pct"]:.1f}%</b>
    (= 1 ÷ {cfg["margin_ltv_pct"]/100:.0%});
    維持率跌破 <b style="color:var(--text)">{cfg["call_ratio_pct"]:.0f}%</b> 觸發追繳,
    本模擬假設你不補錢,隔日開盤系統會自動全數斷頭賣出還款。
    融資只能整張({cfg["lot"]} 股)交易,零股不得融資。<br>
    <b style="color:var(--text)">00631L 融資帳戶的實際曝險是 2 × {cfg["margin_leverage"]:g} ≈
    {2 * cfg["margin_leverage"]:.1f} 倍指數</b>——這代表大盤(不是00631L)只要跌約
    {100 * (1 - cfg["call_ratio_pct"] / cfg["initial_ratio_pct"]) / 2:.0f}% 左右,
    00631L 融資帳戶就可能被追繳,遠比現股 00631L 脆弱。
    這也是為什麼這個帳戶特別需要出場規則保護,而不只是槓桿本身有沒有用。
  </div>
</div>"""

    # ---- 交易紀錄(主帳戶) ----
    trades = m["trades"] if started else []
    if trades:
        trows = []
        for t in reversed(trades):
            forced = t.get("forced")
            rowcls = ' class="liq"' if forced else ""
            side = f'<span class="up">{t["side"]}</span>' if t["side"].startswith("賣") or forced \
                else f'<span class="down">{t["side"]}</span>'
            debt_txt = "—"
            if "debt_taken" in t and t["debt_taken"]:
                debt_txt = f'借 NT$ {money(t["debt_taken"])}'
            elif "debt_repaid" in t and t["debt_repaid"]:
                debt_txt = f'還 NT$ {money(t["debt_repaid"])}'
            trows.append(
                f'<tr{rowcls}><td>{t["date"]}</td><td>{side}</td>'
                f'<td>{t["shares"]:,}</td><td>{t["price"]}</td>'
                f'<td>NT$ {money(t["amount"])}</td><td class="dim">{debt_txt}</td>'
                f'<td class="dim">NT$ {t["fee"]:,}</td><td class="dim">NT$ {t["tax"]:,}</td></tr>')
        trade_html = (f'<div class="panel scroll"><table><thead><tr><th>日期</th><th>方向</th>'
                      f'<th>股數</th><th>成交價</th><th>金額</th><th>融資</th><th>手續費</th>'
                      f'<th>交易稅</th></tr></thead><tbody>{"".join(trows)}</tbody></table></div>')
    else:
        trade_html = ('<div class="panel"><div class="empty">尚無交易。'
                      '這條規則九年只出場 4 次,長時間沒有動作是正常的。</div></div>')

    # ---- 每日淨值(主帳戶) ----
    hist = m["history"][-30:] if started else []
    if hist:
        base = len(m["history"]) - len(hist)
        hrows = []
        for j in range(len(hist) - 1, -1, -1):
            x, idx = hist[j], base + j
            day = (x["equity"] / m["history"][idx - 1]["equity"] - 1) * 100 if idx else 0.0
            r_cell = ratio_pill(x["margin_ratio"], x["call"])
            hrows.append(
                f'<tr><td>{x["date"]}</td><td>{x["close"]}</td>'
                f'<td>{x["shares"]:,}</td><td>NT$ {money(x["market_value"])}</td>'
                f'<td>NT$ {money(x["debt"])}</td><td>{r_cell}</td>'
                f'<td>NT$ {money(x["equity"])}</td><td>{pct(day)}</td></tr>')
        daily_html = (f'<div class="panel scroll"><table><thead><tr><th>日期</th>'
                      f'<th>收盤</th><th>持股</th><th>市值</th><th>融資餘額</th>'
                      f'<th>維持率</th><th>總資產</th><th>當日</th></tr></thead>'
                      f'<tbody>{"".join(hrows)}</tbody></table></div>')
    else:
        daily_html = '<div class="panel"><div class="empty">起算後每個交易日都會新增一列。</div></div>'

    days = d["trading_days"]
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>100萬紙上交易實測 | 融資 + 200MA 出場規則</title>
<style>{CSS}</style></head><body><div class="wrap">
<header>
  <h1>100 萬紙上交易實測(含融資)</h1>
  <div class="sub">
    主帳戶:<b>00631L 融資 {cfg["margin_ltv_pct"]:.0f}%(槓桿 {cfg["margin_leverage"]:g}×)
    + 加權指數跌破 200 日均線 2% 即全數出場</b><br>
    起算日 <b>{d['inception']}</b>・已測試 <b>{days}</b> 個交易日・
    資料日 <b>{d['last_data_date'] or '—'}</b>・更新於 {d['generated_at']}<br>
    <a href="index.html">← 回成交量分析</a>
  </div>
</header>

<div class="section"><h2>今日訊號 <span class="note">T 日收盤判斷,T+1 開盤成交</span></h2>{sig_html}</div>
<div class="section"><h2>主帳戶 <span class="note">00631L 融資 + 出場規則</span></h2>{hero}</div>
<div class="section"><h2>帳戶比較 <span class="note">6 個帳戶,自備款皆 100 萬,同時起算</span></h2>{chart}{compare}</div>
<div class="section"><h2>成本與融資明細</h2>{cost_html}</div>
<div class="section"><h2>交易紀錄 <span class="note">主帳戶,紅底列為強制斷頭</span></h2>{trade_html}</div>
<div class="section"><h2>每日淨值 <span class="note">主帳戶,最近 30 個交易日</span></h2>{daily_html}</div>

<div class="foot">
  <b>規則全文(已凍結)</b><br>
  預設持有 00631L。加權指數收盤跌破 200 日均線 ×0.98 → 隔日開盤全數賣出;
  收盤站回 200 日均線 ×1.02 → 隔日開盤全數買回;其餘維持原狀。<br>
  主帳戶另外疊加融資 {cfg["margin_ltv_pct"]:.0f}% 成數(自備 {100-cfg["margin_ltv_pct"]:.0f}%),
  年利率 {cfg["margin_annual_rate_pct"]:.2f}%,追繳線 {cfg["call_ratio_pct"]:.0f}%,
  觸發追繳且未補款時隔日開盤強制斷頭。<br><br>
  <b>回測參考(00631L 現股,2018-2026,含成本)</b><br>
  買進持有 +2194%、最大回撤 -55%、2022 年 -38%;
  套用出場規則後 +2112%、最大回撤 -37%、2022 年 -19%,九年僅出場 4 次。
  180~250 日均線、緩衝 0~5% 的所有組合回撤都落在同一水準,顯示結果不是靠挑參數挑出來的。<br><br>
  <b>融資疊加後必須知道的風險</b><br>
  融資把 00631L 的曝險再放大到約 {2*cfg["margin_leverage"]:.1f} 倍指數,
  出場規則的反應速度(等指數收盤跌破 200MA 才動作)追不上單日暴跌或跳空,
  歷史測試顯示無出場規則的融資帳戶在 2026 年這種 -30% 級回檔中會被直接斷頭出場,
  本金一次性大幅虧損且無法參與之後的反彈,這是現股帳戶不會遇到的風險。
  斷頭後本模擬會用剩餘資金按規則重新進場,實際券商可能要求你補繳保證金或直接砍倉並收取違約費用,細節依券商而定。<br><br>
  回測只涵蓋 9 年、其中只有 2018 與 2022 兩個空頭,樣本很薄;
  這條規則針對的是「空頭」,對 2026 年這種盤中回檔完全不會提前反應。<br><br>
  本頁為紙上模擬,不是實際下單,未考慮滑價、零股流動性與券商個別追繳寬限期。
  所有數字僅供研究,不構成投資建議。
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
