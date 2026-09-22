# -*- coding: utf-8 -*-
"""紙上交易帳本:用 100 萬實測 200MA +-2% 出場規則(2026-09-20 建立,2026-09-22 加入融資)。

策略(凍結)
  標的  : 00631L(元大台灣50正2)為主,0050 為對照
  預設  : 持有(這是一條「出場規則」,不做進場擇時)
  出場  : 加權指數收盤 < 200日均線 x 0.98
  回補  : 加權指數收盤 > 200日均線 x 1.02
  其餘  : 維持原狀(狀態機,避免在均線附近反覆進出)
  執行  : T 日收盤產生訊號,T+1 日「開盤價」成交(無前視偏誤)

融資規則(依台股信用交易實際制度)
  融資成數 6 成 -> 自備 4 成,自有資金槓桿 2.5 倍
  融資只能整張(1000股)交易,零股不得融資
  利息 = 融資金額 x 年利率 / 365 x 日曆天數(週末假日照算),每日計提
  整戶維持率 = 擔保品市值 / 融資金額;建倉時 1/0.6 = 166%
  維持率 < 130% -> 券商追繳;本模擬假設無法補錢,隔日開盤強制賣出(斷頭)
  斷頭後以剩餘權益重新建倉(訊號允許時),以呈現重複斷頭的複合傷害

成本
  手續費 0.1425% x 折扣,單筆最低 20 元,買賣都收
  證交稅 0.1%(ETF 稅率),只在賣出時收

輸出 paper.json 給 build_paper.py 產生網頁。
每次執行都從起算日重新完整重算,不做增量累加,避免長期累積誤差。
"""
import json
import datetime

import pandas as pd
import yfinance as yf

# ---------- 凍結設定 ----------
INCEPTION = "2026-09-21"       # 起算日:首次以當日開盤價建倉
INITIAL_CAPITAL = 1_000_000    # 每個帳戶自備款各 100 萬
MA_WIN = 200
BUFFER = 0.02

FEE_RATE = 0.001425            # 券商手續費率
FEE_DISCOUNT = 1.0             # 券商折扣(1.0=全額;若你有折扣改這裡並記錄變更日)
FEE_MIN = 20                   # 單筆最低手續費
TAX_RATE = 0.001               # ETF 賣出證交稅

MARGIN_LTV = 0.6               # 融資成數(上市股票與ETF上限 6 成)
MARGIN_ANNUAL_RATE = 0.065     # 融資年利率(市場行情 6%~7%)
MAINTENANCE_CALL = 1.30        # 追繳線:整戶維持率 130%
LOT = 1000                     # 融資必須整張

OUT_PATH = "paper.json"

# (key, 顯示名稱, 代號, 是否用出場規則, 融資成數)
ACCOUNTS = [
    ("00631L_margin_rule", "00631L 融資6成 + 出場規則", "00631L.TW", True,  MARGIN_LTV),
    ("00631L_margin_bh",   "00631L 融資6成 買進持有",   "00631L.TW", False, MARGIN_LTV),
    ("00631L_rule",        "00631L 現股 + 出場規則",    "00631L.TW", True,  0.0),
    ("00631L_bh",          "00631L 現股 買進持有",      "00631L.TW", False, 0.0),
    ("0050_margin_rule",   "0050 融資6成 + 出場規則",   "0050.TW",   True,  MARGIN_LTV),
    ("0050_bh",            "0050 現股 買進持有",        "0050.TW",   False, 0.0),
]
MAIN = "00631L_margin_rule"


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


def size_position(own_funds, price, ltv):
    """回傳 (股數, 融資金額, 自備支出含手續費)。融資須整張,現股可買零股。"""
    step = LOT if ltv > 0 else 1
    # 每 1 元成交金額需自備 (1-ltv) + 手續費率
    budget = own_funds / ((1 - ltv) + FEE_RATE * FEE_DISCOUNT)
    n = int(budget / (price * step)) * step
    while n > 0:
        amt = n * price
        debt = round(amt * ltv)
        need = amt - debt + buy_fee(amt)
        if need <= own_funds:
            return n, debt, need
        n -= step
    return 0, 0, 0


def run_account(px, want, dates, use_rule, ltv):
    """模擬單一帳戶。T 日的部位由 T-1 日訊號決定,以 T 日開盤價成交。"""
    cash, shares, debt = float(INITIAL_CAPITAL), 0, 0
    fee_sum = tax_sum = interest_sum = 0
    trades, history = [], []
    forced = False          # 前一日收盤已觸發追繳 -> 今日開盤斷頭
    dead = False            # 買進持有+融資 一旦斷頭就永久出局(沒有重新進場規則)
    liquidations = 0
    prev_date = None

    for d in dates:
        o, c = float(px.at[d, "Open"]), float(px.at[d, "Close"])

        # --- 融資利息:上一個交易日到今日的日曆天數,週末假日照算。
        #     未償還的利息計入融資本金(複利),不會讓現金變成負數 ---
        if debt > 0 and prev_date is not None:
            days = (d - prev_date).days
            it = debt * MARGIN_ANNUAL_RATE * days / 365
            debt += it
            interest_sum += it
        prev_date = d

        prev = want.index[want.index < d]
        target = bool(want.loc[prev[-1]]) if (use_rule and len(prev)) else True

        # --- 賣出:斷頭優先於訊號。斷頭與買進可能同一天發生,兩筆都要記錄 ---
        if shares > 0 and (forced or not target):
            amt = shares * o
            f, t = sell_cost(amt)
            cash += amt - f - t - debt
            trades.append({"date": d.strftime("%Y-%m-%d"),
                          "side": "斷頭賣出" if forced else "賣出", "shares": shares,
                          "price": round(o, 2), "amount": round(amt), "fee": f, "tax": t,
                          "debt_repaid": round(debt), "forced": forced})
            fee_sum += f
            tax_sum += t
            shares, debt = 0, 0
            if forced:
                liquidations += 1
                if not use_rule and ltv > 0:
                    dead = True  # 買進持有+融資 沒有重新進場的規則,斷頭後永久出局
            forced = False

        # --- 買進:訊號允許、目前空手、且未因斷頭出局 ---
        if target and shares == 0 and cash > 0 and not dead:
            n, dt, need = size_position(cash, o, ltv)
            if n > 0:
                amt = n * o
                f = buy_fee(amt)
                cash -= need
                shares, debt = n, dt
                fee_sum += f
                trades.append({"date": d.strftime("%Y-%m-%d"),
                              "side": "買進", "shares": n, "price": round(o, 2),
                              "amount": round(amt), "fee": f, "tax": 0,
                              "debt_taken": dt, "forced": False})

        # --- 收盤評價與維持率 ---
        mv = shares * c
        ratio = (mv / debt * 100) if debt > 0 else None
        if ratio is not None and ratio < MAINTENANCE_CALL * 100:
            forced = True   # 隔日開盤斷頭
        history.append({"date": d.strftime("%Y-%m-%d"), "close": round(c, 2),
                        "shares": shares, "cash": round(cash),
                        "market_value": round(mv), "debt": round(debt),
                        "equity": round(cash + mv - debt),
                        "margin_ratio": round(ratio, 1) if ratio is not None else None,
                        "call": bool(forced), "in_market": shares > 0})

    eq = [h["equity"] for h in history]
    peak, mdd = eq[0] if eq else 0, 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    last = history[-1] if history else None
    return {"history": history, "trades": trades,
            "cash": round(cash), "shares": shares, "debt": round(debt),
            "fee_sum": round(fee_sum), "tax_sum": round(tax_sum),
            "interest_sum": round(interest_sum),
            "margin_ratio": last["margin_ratio"] if last else None,
            "call": bool(last["call"]) if last else False,
            "liquidations": liquidations,
            "dead": dead,
            "equity": eq[-1] if eq else INITIAL_CAPITAL,
            "total_return_pct": round((eq[-1] / INITIAL_CAPITAL - 1) * 100, 2) if eq else 0.0,
            "max_drawdown_pct": round(mdd * 100, 2),
            "ltv": ltv}


def main():
    twii_close = load("^TWII")["Close"]
    want, ma = signal_series(twii_close)
    inc = pd.Timestamp(INCEPTION)

    prices = {tk: load(tk) for tk in {a[2] for a in ACCOUNTS}}
    # 交易日以「標的」為準,不與指數取交集:Yahoo 的指數資料常比 ETF 晚一天,
    # 而訊號只需要前一個已知的指數收盤,不需要當日指數。
    dates = None
    for df in prices.values():
        idx = df.index[df.index >= inc]
        dates = idx if dates is None else dates.intersection(idx)
    dates = dates.sort_values()

    accounts = {}
    for key, label, tk, use_rule, ltv in ACCOUNTS:
        r = run_account(prices[tk], want, dates, use_rule, ltv)
        r.update({"label": label, "ticker": tk, "use_rule": use_rule})
        accounts[key] = r

    last_sig = twii_close.index[-1]
    cur_ma, cur_px = float(ma.loc[last_sig]), float(twii_close.loc[last_sig])
    exit_line = cur_ma * (1 - BUFFER)

    twii_ret = None
    if len(dates):
        base_idx = twii_close.index[twii_close.index <= dates[0]]
        if len(base_idx):
            twii_ret = round((cur_px / float(twii_close.loc[base_idx[-1]]) - 1) * 100, 2)

    data = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "inception": INCEPTION,
        "initial_capital": INITIAL_CAPITAL,
        "main": MAIN,
        "started": bool(len(dates)),
        "trading_days": int(len(dates)),
        "last_data_date": dates[-1].strftime("%Y-%m-%d") if len(dates) else None,
        "signal": {
            "date": last_sig.strftime("%Y-%m-%d"),
            "twii_close": round(cur_px, 2),
            "ma200": round(cur_ma, 2),
            "exit_line": round(exit_line, 2),
            "entry_line": round(cur_ma * (1 + BUFFER), 2),
            "distance_to_exit_pct": round((cur_px / exit_line - 1) * 100, 2),
            "hold": bool(want.loc[last_sig]),
            "next_action": "維持持有" if want.loc[last_sig] else "出場(空手)",
        },
        "twii_return_pct": twii_ret,
        "accounts": accounts,
        "config": {
            "ma": MA_WIN, "buffer_pct": BUFFER * 100,
            "fee_rate_pct": FEE_RATE * 100, "fee_discount": FEE_DISCOUNT,
            "fee_min": FEE_MIN, "tax_rate_pct": TAX_RATE * 100,
            "margin_ltv_pct": MARGIN_LTV * 100,
            "margin_leverage": round(1 / (1 - MARGIN_LTV), 2),
            "margin_annual_rate_pct": MARGIN_ANNUAL_RATE * 100,
            "initial_ratio_pct": round(100 / MARGIN_LTV, 1),
            "call_ratio_pct": MAINTENANCE_CALL * 100,
            "lot": LOT,
            "execution": "T日收盤訊號,T+1日開盤成交",
        },
    }
    if not data["started"]:
        last_px = {tk: float(df["Close"].iloc[-1]) for tk, df in prices.items()}
        data["plan"] = {}
        for key, label, tk, use_rule, ltv in ACCOUNTS:
            p = last_px[tk]
            n, dt, need = size_position(INITIAL_CAPITAL, p, ltv)
            data["plan"][key] = {"label": label, "price": round(p, 2), "shares": n,
                                 "amount": round(n * p), "debt": dt,
                                 "fee": buy_fee(n * p),
                                 "cash_left": round(INITIAL_CAPITAL - need)}

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if data["started"]:
        a = accounts[MAIN]
        print(f"帳本已更新 {OUT_PATH}:第 {len(dates)} 個交易日({dates[-1].date()}),"
              f"主帳戶權益 {a['equity']:,} 元({a['total_return_pct']:+.2f}%),"
              f"維持率 {a['margin_ratio']}%")
    else:
        print(f"帳本已建立 {OUT_PATH}:起算日 {INCEPTION} 尚未到,顯示建倉計畫")


if __name__ == "__main__":
    main()
