# -*- coding: utf-8 -*-
"""
針對 data.json 中出現過的每一檔股票(今日成交量Top100 + 爆量股Top10),
用 yfinance 抓約2年的日K資料,算出均線(SMA5/10/20/60/120/240)與均量(MA5/20),
輸出成 history_data.js(給網頁 <script> 直接載入,避免 file:// 開啟時的 CORS/fetch 限制)。

重新整理只要重跑這支腳本(建議在 fetch_data.py 之後執行)。
"""
import json
import time
import math
import pandas as pd
import yfinance as yf

PERIOD = "2y"
SMA_WINDOWS = [5, 10, 20, 60, 120, 240]
VOL_MA_WINDOWS = [5, 20]


def sma(series, window):
    return series.rolling(window).mean()


def _num(v):
    return float(str(v).replace(",", ""))


def patch_today_if_missing(df, today_str, official):
    """Yahoo Finance 有些冷門股當天收盤資料會晚幾小時甚至隔天才更新,
    如果抓到的歷史最後一天不是「今天」,就用證交所官方今日OHLCV補上這一根K棒,
    確保圖表一定看得到最新的交易日。"""
    if official is None:
        return df
    today_ts = pd.Timestamp(today_str)
    if not df.empty and df.index[-1] >= today_ts:
        return df
    row = pd.DataFrame(
        {
            "Open": [_num(official["open"])],
            "High": [_num(official["high"])],
            "Low": [_num(official["low"])],
            "Close": [_num(official["close"])],
            "Volume": [official["volume"]],
        },
        index=[today_ts],
    )
    return pd.concat([df, row])


def build_one(code, df, today_str=None, official=None):
    df = df.dropna(subset=["Close"]).copy()
    df = patch_today_if_missing(df, today_str, official)
    if df.empty:
        return None
    df["vol_ma5"] = sma(df["Volume"], VOL_MA_WINDOWS[0])
    df["vol_ma20"] = sma(df["Volume"], VOL_MA_WINDOWS[1])
    sma_cols = {}
    for w in SMA_WINDOWS:
        sma_cols[w] = sma(df["Close"], w)

    def clean(v):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        return round(float(v), 3)

    dates = [d.strftime("%Y-%m-%d") for d in df.index]
    record = {
        "t": dates,
        "o": [clean(v) for v in df["Open"]],
        "h": [clean(v) for v in df["High"]],
        "l": [clean(v) for v in df["Low"]],
        "c": [clean(v) for v in df["Close"]],
        "v": [int(v) if not math.isnan(v) else 0 for v in df["Volume"]],
        "sma": {str(w): [clean(v) for v in sma_cols[w]] for w in SMA_WINDOWS},
        "vma5": [clean(v) for v in df["vol_ma5"]],
        "vma20": [clean(v) for v in df["vol_ma20"]],
    }
    return record


def main():
    with open("data.json", "r", encoding="utf-8") as f:
        d = json.load(f)

    today_str = d["today"]
    official = {}
    for it in d["top100_by_volume"] + d["top10_by_ratio"]:
        official[it["code"]] = it
    codes = sorted(official.keys())
    print(f"需要抓歷史資料的股票數: {len(codes)}(今日交易日:{today_str})")

    tickers = [f"{c}.TW" for c in codes]
    result = {}

    # 分批抓,避免單次 request 太大或觸發 yfinance 內部限制
    batch_size = 20
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        print(f"抓取批次 {i//batch_size + 1}: {batch}")
        for attempt in range(3):
            try:
                df_all = yf.download(
                    batch, period=PERIOD, auto_adjust=False,
                    group_by="ticker", progress=False, threads=False,
                )
                break
            except Exception as e:
                print(f"  重試 ({attempt+1}/3): {e}")
                time.sleep(2)
        else:
            print(f"  批次失敗,略過: {batch}")
            continue

        for ticker in batch:
            code = ticker.replace(".TW", "")
            try:
                if len(batch) == 1:
                    sub = df_all
                else:
                    sub = df_all[ticker]
            except KeyError:
                print(f"  {ticker} 無資料")
                continue
            rec = build_one(code, sub, today_str=today_str, official=official.get(code))
            if rec:
                result[code] = rec
            else:
                print(f"  {ticker} 資料為空")
        time.sleep(1)

    print(f"成功取得 {len(result)}/{len(codes)} 檔股票的歷史資料")

    with open("history_data.js", "w", encoding="utf-8") as f:
        f.write("window.STOCK_HISTORY = ")
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    print("已寫入 history_data.js")


if __name__ == "__main__":
    main()
