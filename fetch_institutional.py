# -*- coding: utf-8 -*-
"""抓取三大法人買賣超日報(來源:證交所 T86),計算四種法人動向排行:

  外資突然大買   今日外資買超創近 N 個交易日新高(且為正)
  投信突然大買   今日投信買超創近 N 個交易日新高(且為正)
  外資投信都買   今日外資、投信同時買超,依合計買超張數排序
  連續買超       外資+投信合計買超連續為正的天數最長者(至少連 3 日)

單位一律用「張」(1張=1000股),這是台股媒體慣用的單位,不需要另外換算金額。
只納入一般普通股(4碼、不以0開頭的代號),排除ETF與受益證券,
與 fetch_data.py 的股票池一致。

結果存成 institutional.json,給 build_html.py 讀取。
"""
import json
import datetime

import fetch_data as fd

T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"
LOOKBACK_DAYS = 10          # 抓幾個交易日的歷史,用來判斷「突然」與「連續」
SPIKE_MIN_LOTS = 50         # 買超張數低於此門檻不列入「突然大買」,避免小型股雜訊
STREAK_MIN_DAYS = 3         # 連續買超至少要幾天才列入排行
TOP_N = 10


def num(s):
    """T86 的數字欄位是千分位字串,轉成 float。"""
    s = (s or "0").replace(",", "").strip()
    return float(s) if s else 0.0


def fetch_t86_day(date_obj):
    """回傳 {code: {name, foreign_lots, trust_lots}},非交易日回傳 None。"""
    ds = date_obj.strftime("%Y%m%d")
    j = fd.fetch_json_with_fallback(T86_URL, {"date": ds, "selectType": "ALL", "response": "json"})
    if j.get("stat") != "OK" or not j.get("data"):
        return None

    out = {}
    for row in j["data"]:
        code = row[0]
        if not fd.STOCK_CODE_RE.match(code):
            continue
        name = row[1].strip()
        # 外資合計 = 外陸資買賣超(不含外資自營商,index 4) + 外資自營商買賣超(index 7)
        foreign_lots = (num(row[4]) + num(row[7])) / 1000
        trust_lots = num(row[10]) / 1000
        out[code] = {"name": name, "foreign_lots": foreign_lots, "trust_lots": trust_lots}
    return out


def find_recent_t86_days(n, start_date=None):
    """從 start_date(預設今天)往回找 n 個有資料的交易日,回傳 [(date_str, data), ...] 由新到舊。"""
    d = start_date or datetime.date.today()
    results = []
    tries = 0
    while len(results) < n and tries < 30:
        data = fetch_t86_day(d)
        if data:
            results.append((d.strftime("%Y-%m-%d"), data))
        d -= datetime.timedelta(days=1)
        tries += 1
    return results


def build_series(days):
    """把 [(date, {code:{...}}), ...] (新到舊) 轉成 {code: {name, foreign:[...], trust:[...]}} (舊到新)。"""
    days = list(reversed(days))  # 舊到新,方便算連續天數與新高
    series = {}
    for _, data in days:
        for code, info in data.items():
            s = series.setdefault(code, {"name": info["name"], "foreign": [], "trust": []})
            s["foreign"].append(info["foreign_lots"])
            s["trust"].append(info["trust_lots"])
    dates = [d for d, _ in days]
    return series, dates


def streak_len(values):
    """從陣列尾端(今天)往前數,連續 > 0 的天數。"""
    n = 0
    for v in reversed(values):
        if v > 0:
            n += 1
        else:
            break
    return n


def rank(items, key, limit=TOP_N):
    items = sorted(items, key=key, reverse=True)
    out = []
    for i, it in enumerate(items[:limit], start=1):
        out.append({"rank": i, **it})
    return out


def run():
    days = find_recent_t86_days(LOOKBACK_DAYS)
    if len(days) < 4:
        print(f"只抓到 {len(days)} 個交易日的法人資料,不足以計算,略過本次更新"
              "(保留昨天的 institutional.json 不動)")
        return

    series, dates = build_series(days)
    today = dates[-1]
    print(f"法人資料交易日: {dates[0]} ~ {today}(共 {len(dates)} 日)")

    foreign_spike, trust_spike, both_buying, streak_buying = [], [], [], []

    for code, s in series.items():
        f_hist, t_hist = s["foreign"], s["trust"]
        if len(f_hist) < 4:
            continue  # 資料太短(新股或近期才有交易),不列入判斷
        f_today, t_today = f_hist[-1], t_hist[-1]
        name = s["name"]

        # 外資突然大買:今日是近期新高,且過門檻
        if f_today >= SPIKE_MIN_LOTS and f_today == max(f_hist):
            foreign_spike.append({"code": code, "name": name,
                                  "lots": f_today, "trust_lots": t_today})
        # 投信突然大買
        if t_today >= SPIKE_MIN_LOTS and t_today == max(t_hist):
            trust_spike.append({"code": code, "name": name,
                                "lots": t_today, "foreign_lots": f_today})
        # 外資投信都買
        if f_today > 0 and t_today > 0:
            both_buying.append({"code": code, "name": name,
                                "foreign_lots": f_today, "trust_lots": t_today,
                                "combined_lots": f_today + t_today})
        # 連續買超(外資+投信合計)
        combined_hist = [a + b for a, b in zip(f_hist, t_hist)]
        streak = streak_len(combined_hist)
        if streak >= STREAK_MIN_DAYS:
            streak_buying.append({"code": code, "name": name, "streak_days": streak,
                                  "streak_total_lots": sum(combined_hist[-streak:]),
                                  "today_lots": combined_hist[-1]})

    output = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date": today,
        "lookback_days": len(dates),
        "spike_min_lots": SPIKE_MIN_LOTS,
        "streak_min_days": STREAK_MIN_DAYS,
        "foreign_spike": rank(foreign_spike, lambda x: x["lots"]),
        "trust_spike": rank(trust_spike, lambda x: x["lots"]),
        "both_buying": rank(both_buying, lambda x: x["combined_lots"]),
        "streak_buying": rank(streak_buying, lambda x: (x["streak_days"], x["streak_total_lots"])),
    }

    with open("institutional.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"已寫入 institutional.json:外資突然大買 {len(output['foreign_spike'])} 檔、"
          f"投信突然大買 {len(output['trust_spike'])} 檔、"
          f"外資投信都買 {len(output['both_buying'])} 檔、"
          f"連續買超 {len(output['streak_buying'])} 檔")


def main():
    """這個功能是附加的觀察工具,不是主流程(成交量分析、紙上交易)的必要條件。
    任何失敗(T86 格式改變、連線問題等)都只印警告、保留昨天的檔案,
    不讓整個每日更新工作流程因此中斷。"""
    try:
        run()
    except Exception as e:
        print(f"⚠ 三大法人動向更新失敗,略過(保留昨天的 institutional.json):{e}")


if __name__ == "__main__":
    main()
