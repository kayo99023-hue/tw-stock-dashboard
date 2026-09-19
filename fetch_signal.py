# -*- coding: utf-8 -*-
"""大盤擇時訊號(樸素設定,2026-09-19凍結)。結果存成 signal.json 給 build_html.py 使用。

設定(凍結,不得更改。任何更動都會讓已累積的前進測試紀錄失去意義):
  進場:加權指數收盤 > 200日均線 x 1.02
  出場:加權指數收盤 < 200日均線 x 0.98
  其餘:維持原狀(狀態機,避免在均線附近反覆進出)
  部位:在場內時,20日實現波動率 < 過去252日中位數 -> 1.7倍;否則 1.0倍;不在場內 -> 空手

回測結果(僅供參考,非保證):
  2018-2023(開發期) 累積+107% vs 大盤+67%,最大回撤-17%,2018與2022兩個空頭年虧損皆小於大盤一半
  2024-2025(驗證期) 累積+85% vs 大盤+62%
  2026年初至9/18(封存測試) +73% vs 大盤+61%,但該期間為單邊多頭,防守機制完全未被觸發
"""
import json
import datetime

import numpy as np
import pandas as pd
import yfinance as yf

SYMBOL = "^TWII"
MA_WIN = 200
BUFFER = 0.02
BOOST = 1.7
BASE = 1.0
VOL_WIN = 20
VOL_MEDIAN_WIN = 252
COST = 0.0003
INCEPTION = "2026-09-19"   # 前進測試起算日
OUT_PATH = "signal.json"


def state_machine(enter, exit_):
    """進場條件成立才進,出場條件成立才出,其餘維持原狀。"""
    out, on = [], False
    for e, x in zip(enter, exit_):
        if not on and e:
            on = True
        elif on and x:
            on = False
        out.append(on)
    return np.array(out)


def main():
    print("抓取加權指數歷史資料...")
    tw = yf.download(SYMBOL, start="2016-06-01", auto_adjust=True, progress=False)
    if isinstance(tw.columns, pd.MultiIndex):
        tw.columns = tw.columns.get_level_values(0)
    px = tw["Close"].dropna()
    if len(px) < MA_WIN + VOL_MEDIAN_WIN:
        raise RuntimeError("歷史資料不足,無法計算訊號")

    ma = px.rolling(MA_WIN).mean()
    rv = px.pct_change().rolling(VOL_WIN).std() * np.sqrt(252)
    rv_med = rv.rolling(VOL_MEDIAN_WIN).median()
    calm = (rv < rv_med).fillna(False)
    gate = state_machine((px > ma * (1 + BUFFER)).to_numpy(),
                         (px < ma * (1 - BUFFER)).to_numpy())
    pos = pd.Series(np.where(gate & calm.to_numpy(), BOOST, np.where(gate, BASE, 0.0)),
                    index=px.index)

    # 前進測試績效(訊號在T日產生,吃T->T+1報酬)
    fwd = px.index >= pd.Timestamp(INCEPTION)
    perf = None
    if fwd.sum() >= 2:
        p = pos[fwd]
        c = px[fwd]
        ret = c.pct_change().shift(-1)
        turn = p.diff().abs().fillna(p.abs())
        eq = (1 + (p * ret - turn * COST).fillna(0)).cumprod()
        s = float(eq.iloc[-1] - 1)
        m = float(c.iloc[-1] / c.iloc[0] - 1)
        perf = {
            "days": int(fwd.sum()),
            "start": c.index[0].strftime("%Y-%m-%d"),
            "strategy_return": round(s * 100, 2),
            "market_return": round(m * 100, 2),
            "ratio": round(s / m, 2) if m != 0 else None,
            "max_drawdown": round(float((eq / eq.cummax() - 1).min()) * 100, 2),
        }

    i = -1
    prev_pos = float(pos.iloc[-2]) if len(pos) > 1 else 0.0
    cur_pos = float(pos.iloc[i])
    data = {
        "date": px.index[i].strftime("%Y-%m-%d"),
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "close": round(float(px.iloc[i]), 2),
        "ma200": round(float(ma.iloc[i]), 2),
        "entry_line": round(float(ma.iloc[i] * (1 + BUFFER)), 2),
        "exit_line": round(float(ma.iloc[i] * (1 - BUFFER)), 2),
        "distance_to_exit_pct": round(float(px.iloc[i] / (ma.iloc[i] * (1 - BUFFER)) - 1) * 100, 2),
        "rv20": round(float(rv.iloc[i]) * 100, 2),
        "rv_median": round(float(rv_med.iloc[i]) * 100, 2),
        "is_calm": bool(calm.iloc[i]),
        "in_market": bool(gate[i]),
        "position": cur_pos,
        "prev_position": prev_pos,
        "changed": cur_pos != prev_pos,
        "forward_test": perf,
        "config": {"ma": MA_WIN, "buffer_pct": BUFFER * 100, "boost": BOOST,
                   "inception": INCEPTION},
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"訊號已存 {OUT_PATH}:{data['date']} 部位 {cur_pos} 倍"
          f"({'在場內' if data['in_market'] else '空手'})")


if __name__ == "__main__":
    main()
