# -*- coding: utf-8 -*-
"""
抓取台股每日成交資訊(來源:證交所 MI_INDEX),計算:
  1. 今日成交量 Top 100
  2. 今日成交量 / 近三個交易日成交量總和 的比值 Top 10 (爆量股)
並把結果算好存成 data.json,給 build_html.py 讀取產生網頁。

重新整理資料只要重跑這支腳本,再跑 build_html.py 即可。
"""
import re
import json
import datetime
import requests

TWSE_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
PROXY_URL = "https://tw-stock-live.kayo99023.workers.dev/proxy"
STOCK_CODE_RE = re.compile(r"^[1-9][0-9]{3}$")  # 一般普通股:4碼數字、不以0開頭(排除ETF/受益證券)
RATIO_MIN_VOLUME = 1_000_000  # 爆量排名的最低今日成交股數門檻,避免冷門股雜訊


def fetch_json_with_fallback(url, params):
    """直接連證交所;某些雲端主機(如 GitHub Actions)的 IP 會被證交所擋掉/逾時,
    這種情況改走 Cloudflare Worker 代理(該 IP 範圍證交所不會擋)。"""
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"  直接連線失敗({e}),改用代理重試...")
        full_url = requests.Request("GET", url, params=params).prepare().url
        resp = requests.get(PROXY_URL, params={"url": full_url}, timeout=30)
        resp.raise_for_status()
        return resp.json()


def fetch_day(date_obj):
    """回傳 {code: {name, volume, close, change_dir, change_amt}},失敗或非交易日回傳 None"""
    ds = date_obj.strftime("%Y%m%d")
    j = fetch_json_with_fallback(TWSE_URL, {"date": ds, "type": "ALL", "response": "json"})
    if j.get("stat") != "OK":
        return None

    table = None
    for t in j.get("tables", []):
        if "每日收盤行情(全部)" in (t.get("title") or ""):
            table = t
            break
    if table is None or not table.get("data"):
        return None

    out = {}
    for row in table["data"]:
        code = row[0]
        if not STOCK_CODE_RE.match(code):
            continue
        name = row[1]
        volume = int(row[2].replace(",", "") or 0)
        close = row[8]
        change_dir = "up" if "color:red" in row[9] else ("down" if "color:green" in row[9] else "flat")
        change_amt = row[10]
        out[code] = {
            "name": name,
            "volume": volume,
            "open": row[5],
            "high": row[6],
            "low": row[7],
            "close": close,
            "change_dir": change_dir,
            "change_amt": change_amt,
        }
    return out


def find_recent_trading_days(n, start_date=None):
    """從 start_date(預設今天)往回找 n 個有資料的交易日,回傳 [(date_str, data_dict), ...] 由新到舊"""
    d = start_date or datetime.date.today()
    results = []
    tries = 0
    while len(results) < n and tries < 30:
        data = fetch_day(d)
        if data:
            results.append((d.strftime("%Y-%m-%d"), data))
        d -= datetime.timedelta(days=1)
        tries += 1
    return results


def main():
    days = find_recent_trading_days(4)
    if len(days) < 4:
        raise SystemExit(f"只抓到 {len(days)} 個交易日,資料不足以計算三日均量")

    today_str, today_data = days[0]
    prev_days = days[1:4]
    print(f"今日交易日: {today_str}")
    print(f"前三交易日: {[d for d, _ in prev_days]}")

    # 前三日成交量總和
    prev3_sum = {}
    for _, data in prev_days:
        for code, info in data.items():
            prev3_sum[code] = prev3_sum.get(code, 0) + info["volume"]

    # 今日成交量排行
    volume_rank = sorted(today_data.items(), key=lambda kv: kv[1]["volume"], reverse=True)
    top100 = []
    for rank, (code, info) in enumerate(volume_rank[:100], start=1):
        top100.append({"rank": rank, "code": code, **info})

    # 爆量比排行:今日量 / 前三日總量
    ratio_list = []
    for code, info in today_data.items():
        if info["volume"] < RATIO_MIN_VOLUME:
            continue
        base = prev3_sum.get(code, 0)
        if base <= 0:
            continue
        ratio = info["volume"] / base
        ratio_list.append({"code": code, "ratio": ratio, "prev3_sum": base, **info})
    ratio_list.sort(key=lambda x: x["ratio"], reverse=True)
    top10_ratio = []
    for rank, item in enumerate(ratio_list[:10], start=1):
        top10_ratio.append({"rank": rank, **item})

    output = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "today": today_str,
        "prev_days": [d for d, _ in prev_days],
        "top100_by_volume": top100,
        "top10_by_ratio": top10_ratio,
        "ratio_min_volume": RATIO_MIN_VOLUME,
        "total_stocks": len(today_data),
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"完成,共 {len(today_data)} 檔股票,已寫入 data.json")

    # baseline.json:給盤中即時代理(Cloudflare Worker)用的「最近三個已收盤交易日」總量,
    # 涵蓋全部股票(不只Top100),做為明天盤中「爆量比」的分母基準。
    day1_data = prev_days[0][1] if len(prev_days) > 0 else {}
    day2_data = prev_days[1][1] if len(prev_days) > 1 else {}
    baseline = {}
    for code, info in today_data.items():
        total = info["volume"]
        total += day1_data.get(code, {}).get("volume", 0)
        total += day2_data.get(code, {}).get("volume", 0)
        baseline[code] = {"name": info["name"], "prev3_sum": total}

    baseline_output = {
        "as_of": today_str,
        "days_included": [today_str] + [d for d, _ in prev_days[:2]],
        "ratio_min_volume": RATIO_MIN_VOLUME,
        "baseline": baseline,
    }
    with open("baseline.json", "w", encoding="utf-8") as f:
        json.dump(baseline_output, f, ensure_ascii=False, separators=(",", ":"))

    print(f"已寫入 baseline.json(供隔天盤中即時使用),涵蓋 {len(baseline)} 檔股票")


if __name__ == "__main__":
    main()
