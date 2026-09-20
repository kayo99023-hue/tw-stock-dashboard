# -*- coding: utf-8 -*-
"""紙上交易帳本:用 100 萬實測 200MA +-2% 出場規則(2026-09-20 建立)。

策略(凍結,不得更改;任何更動都會讓已累積的前進測試紀錄失去意義)
  標的  : 00631L(元大台灣50正2)為主帳戶,0050 為對照
  預設  : 持有(這是一條「出場規則」,不做進場擇時)
  出場  : 加權指數收盤 < 200日均線 x 0.98
  回補  : 加權指數收盤 > 200日均線 x 1.02
  其餘  : 維持原狀(狀態機,避免在均線附近反覆進出)
  執行  : T 日收盤產生訊號,T+1 日「開盤價」成交(無前視偏誤)
  槓桿  : 不使用融資。槓桿只來自 00631L 本身的 2 倍設計。

成本(台股實際費率)
  手續費 0.1425% x 券商折扣,單筆最低 20 元,買賣都收
  證交稅 0.1%(ETF 稅率),只在賣出時收
  融資利息 年 6.5%,本策略融資餘額為 0,故利息為 0(欄位保留供對照)

輸出 paper.json 給 build_paper.py 產生網頁。
每次執行都從起算日重新完整重算,不做增量累加,避免長期累積誤差。
"""
import json
import datetime

import pandas as pd
import yfinance as yf

# ---------- 凍結設定 ----------
INCEPTION = "2026-09-21"       # 起算日:首次以當日開盤價建倉
INITIAL_CAPITAL = 1_000_000    # 每個帳戶各 100 萬
MA_WIN = 200
BUFFER = 0.02

FEE_RATE = 0.001425            # 券商手續費率
FEE_DISCOUNT = 1.0             # 券商折扣(1.0=全額;若你有折扣改這裡並記錄變更日)
FEE_MIN = 20                   # 單筆最低手續費
TAX_RATE = 0.001               # ETF 賣出證交稅

MARGIN_RATIO = 0.0             # 融資成數,0 = 不使用融資(使用者指定)
MARGIN_ANNUAL_RATE = 0.065     # 融資年利率(未動用,僅供對照)

OUT_PATH = "paper.json"
ACCOUNTS = [
    ("00631L_strategy", "00631L + 200MA出場規則", "00631L.TW", True),
    ("00631L_bh",       "00631L 買進持有",        "00631L.TW", False),
    ("0050_strategy",   "0050 + 200MA出場規則",   "0050.TW",   True),
    ("0050_bh",         "0050 買進持有",          "0050.TW",   False),
]


def load(tk, start="2024-06-01"):
    """抓日線並濾掉非交易日。yfinance 盤中/假日會給一列暫定資料,必須剔除。"""
    df = yf.download(tk, start=start, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    return df[df.index.dayofweek < 5]


def buy_fee(amount):
    return max(FEE_MIN, round(amount * FEE_RATE * FEE_DISCOUNT))


def sell_cost(amount):
    """回傳 (手續費, 證交稅)。"""
    return max(FEE_MIN, round(amount * FEE_RATE * FEE_DISCOUNT)), round(amount * TAX_RATE)


def signal_series(twii_close):
    """回傳每個交易日收盤後的目標狀態(True=該持有)。預設持有。"""
    ma = twii_close.rolling(MA_WIN).mean()
    exit_ = (twii_close < ma * (1 - BUFFER)).fillna(False).to_numpy()
    enter = (twii_close > ma * (1 + BUFFER)).fillna(False).to_numpy()
    out, hold = [], True
    for x, e in zip(exit_, enter):
        if hold and x:
            hold = False
        elif not hold and e:
            hold = True
        out.append(hold)
    return pd.Series(out, index=twii_close.index), ma


def run_account(px, want, dates, use_rule):
    """模擬單一帳戶。px 需含 Open/Close。want 為「T日收盤後的目標狀態」。
    T 日的部位由 T-1 日訊號決定,以 T 日開盤價成交。"""
    cash, shares = float(INITIAL_CAPITAL), 0
    fee_sum = tax_sum = interest_sum = 0
    trades, history = [], []

    for d in dates:
        o, c = float(px.at[d, "Open"]), float(px.at[d, "Close"])
        prev = want.index[want.index < d]
        target = bool(want.loc[prev[-1]]) if (use_rule and len(prev)) else True
        action = None

        if target and shares == 0:
            n = int(cash // (o * (1 + FEE_RATE * FEE_DISCOUNT)))
            if n > 0:
                amt = n * o
                f = buy_fee(amt)
                cash -= amt + f
                shares = n
                fee_sum += f
                action = {"side": "買進", "shares": n, "price": round(o, 2),
                          "amount": round(amt), "fee": f, "tax": 0}
        elif not target and shares > 0:
            amt = shares * o
            f, t = sell_cost(amt)
            cash += amt - f - t
            action = {"side": "賣出", "shares": shares, "price": round(o, 2),
                      "amount": round(amt), "fee": f, "tax": t}
            shares = 0
            fee_sum += f
            tax_sum += t

        if action:
            action["date"] = d.strftime("%Y-%m-%d")
            trades.append(action)

        mv = shares * c
        history.append({"date": d.strftime("%Y-%m-%d"), "close": round(c, 2),
                        "shares": shares, "cash": round(cash),
                        "market_value": round(mv), "equity": round(cash + mv),
                        "in_market": shares > 0})

    eq = [h["equity"] for h in history]
    peak, mdd = eq[0] if eq else 0, 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    return {"history": history, "trades": trades,
            "cash": round(cash), "shares": shares,
            "fee_sum": fee_sum, "tax_sum": tax_sum, "interest_sum": interest_sum,
            "margin_balance": 0,
            "equity": eq[-1] if eq else INITIAL_CAPITAL,
            "total_return_pct": round((eq[-1] / INITIAL_CAPITAL - 1) * 100, 2) if eq else 0.0,
            "max_drawdown_pct": round(mdd * 100, 2)}


def main():
    twii = load("^TWII")
    px_close = twii["Close"]
    want, ma = signal_series(px_close)
    inc = pd.Timestamp(INCEPTION)

    prices = {tk: load(tk) for tk in {a[2] for a in ACCOUNTS}}
    # 只模擬所有標的都有資料、且 >= 起算日的交易日
    dates = px_close.index[px_close.index >= inc]
    for df in prices.values():
        dates = dates.intersection(df.index)
    dates = dates.sort_values()

    accounts = {}
    for key, label, tk, use_rule in ACCOUNTS:
        r = run_account(prices[tk], want, dates, use_rule)
        r.update({"label": label, "ticker": tk, "use_rule": use_rule})
        accounts[key] = r

    last = px_close.index[-1]
    twii_ret = None
    if len(dates):
        base = float(px_close.loc[dates[0]])
        twii_ret = round((float(px_close.loc[dates[-1]]) / base - 1) * 100, 2)

    cur_ma = float(ma.loc[last])
    cur_px = float(px_close.loc[last])
    data = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "inception": INCEPTION,
        "initial_capital": INITIAL_CAPITAL,
        "started": bool(len(dates)),
        "trading_days": int(len(dates)),
        "last_data_date": last.strftime("%Y-%m-%d"),
        "signal": {
            "date": last.strftime("%Y-%m-%d"),
            "twii_close": round(cur_px, 2),
            "ma200": round(cur_ma, 2),
            "exit_line": round(cur_ma * (1 - BUFFER), 2),
            "entry_line": round(cur_ma * (1 + BUFFER), 2),
            "distance_to_exit_pct": round((cur_px / (cur_ma * (1 - BUFFER)) - 1) * 100, 2),
            "hold": bool(want.loc[last]),
            "next_action": "維持持有" if want.loc[last] else "出場(空手)",
        },
        "prices": {tk: {"close": round(float(df["Close"].loc[last]), 2)}
                   for tk, df in prices.items() if last in df.index},
        "twii_return_pct": twii_ret,
        "accounts": accounts,
        "config": {
            "ma": MA_WIN, "buffer_pct": BUFFER * 100,
            "fee_rate_pct": FEE_RATE * 100, "fee_discount": FEE_DISCOUNT,
            "fee_min": FEE_MIN, "tax_rate_pct": TAX_RATE * 100,
            "margin_ratio": MARGIN_RATIO, "margin_annual_rate_pct": MARGIN_ANNUAL_RATE * 100,
            "execution": "T日收盤訊號,T+1日開盤成交",
        },
    }
    # 尚未開始:用最後收盤價估算建倉規模,讓報告仍有可看的內容
    if not data["started"]:
        plan = {}
        for key, label, tk, use_rule in ACCOUNTS:
            p = float(prices[tk]["Close"].loc[last])
            n = int(INITIAL_CAPITAL // (p * (1 + FEE_RATE * FEE_DISCOUNT)))
            plan[key] = {"label": label, "price": round(p, 2), "shares": n,
                         "amount": round(n * p), "fee": buy_fee(n * p),
                         "cash_left": round(INITIAL_CAPITAL - n * p - buy_fee(n * p))}
        data["plan"] = plan

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if data["started"]:
        a = accounts["00631L_strategy"]
        print(f"帳本已更新 {OUT_PATH}:第 {len(dates)} 個交易日,"
              f"主帳戶淨值 {a['equity']:,} 元({a['total_return_pct']:+.2f}%)")
    else:
        print(f"帳本已建立 {OUT_PATH}:起算日 {INCEPTION} 尚未到,顯示建倉計畫")


if __name__ == "__main__":
    main()
