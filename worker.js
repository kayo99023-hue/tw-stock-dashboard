/**
 * 台股盤中即時成交量代理(Cloudflare Worker)
 *
 * 用途:GitHub Pages 是純靜態網站,沒有後端,沒辦法直接呼叫證交所的盤中報價 API
 * (會被瀏覽器 CORS 擋掉)。這支 Worker 負責:
 *   1. 讀取 GitHub Pages 上每天收盤後產生的 baseline.json(近三個交易日總量基準)
 *   2. 向證交所 MIS 盤中報價 API 批次查詢目前所有股票的即時成交量
 *   3. 算出「今日成交量 Top10/Top100」與「爆量比 Top10」
 *   4. 回傳 JSON,並加上 CORS header 給網頁用
 *
 * 部署方式:Cloudflare Dashboard → Workers & Pages → Create Worker → 貼上這份程式碼 → Deploy。
 */

const BASELINE_URL = "https://kayo99023-hue.github.io/tw-stock-dashboard/baseline.json";
const RATIO_MIN_VOLUME_FALLBACK = 1000000;
const CACHE_SECONDS = 55; // 避免每個訪客都觸發一次證交所查詢,同一分鐘內共用結果
const BATCH_SIZE = 100;

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Content-Type": "application/json; charset=utf-8",
  };
}

async function fetchBaseline() {
  const r = await fetch(BASELINE_URL, { cf: { cacheTtl: 30, cacheEverything: true } });
  if (!r.ok) throw new Error(`baseline.json 取得失敗: ${r.status}`);
  return r.json();
}

function chunk(arr, size) {
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

async function fetchLiveBatch(codes) {
  const q = codes.map((c) => `tse_${c}.tw`).join("|");
  const url = `https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=${encodeURIComponent(q)}&json=1&delay=0`;
  const r = await fetch(url, {
    headers: {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      Referer: "https://mis.twse.com.tw/stock/index.jsp",
    },
  });
  if (!r.ok) return [];
  const j = await r.json().catch(() => null);
  return (j && j.msgArray) || [];
}

async function fetchAllLive(codes) {
  const batches = chunk(codes, BATCH_SIZE);
  const results = await Promise.all(batches.map(fetchLiveBatch));
  const map = {};
  for (const arr of results) {
    for (const item of arr) {
      map[item.c] = item;
    }
  }
  return map;
}

function buildPayload(baselineDoc, liveMap) {
  const baseline = baselineDoc.baseline || {};
  const ratioMin = baselineDoc.ratio_min_volume || RATIO_MIN_VOLUME_FALLBACK;

  const rows = [];
  for (const code of Object.keys(baseline)) {
    const live = liveMap[code];
    if (!live) continue;
    const volLots = parseFloat(live.v);
    if (!volLots || volLots <= 0) continue;
    const volume = volLots * 1000; // 張 -> 股,跟每日收盤資料的單位一致
    const z = parseFloat(live.z);
    const y = parseFloat(live.y);
    let change_dir = "flat";
    let change_pct = 0;
    if (z && y) {
      const diff = z - y;
      change_dir = diff > 0 ? "up" : diff < 0 ? "down" : "flat";
      change_pct = y ? (diff / y) * 100 : 0;
    }
    rows.push({
      code,
      name: baseline[code].name,
      volume,
      close: isFinite(z) ? z.toFixed(2) : "-",
      change_dir,
      change_pct: Number(change_pct.toFixed(2)),
      prev3_sum: baseline[code].prev3_sum || 0,
      time: live.t || live["%"] || "",
    });
  }

  const byVolume = [...rows].sort((a, b) => b.volume - a.volume);
  const top100 = byVolume.slice(0, 100).map((r, i) => ({ rank: i + 1, ...r }));

  const ratioRows = rows
    .filter((r) => r.volume >= ratioMin && r.prev3_sum > 0)
    .map((r) => ({ ...r, ratio: r.volume / r.prev3_sum }))
    .sort((a, b) => b.ratio - a.ratio)
    .slice(0, 10)
    .map((r, i) => ({ rank: i + 1, ...r }));

  return {
    updated_at: new Date().toISOString(),
    market_date: baselineDoc.as_of,
    total_matched: rows.length,
    top100_by_volume: top100,
    top10_by_ratio: ratioRows,
    ratio_min_volume: ratioMin,
  };
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    const cacheKey = new Request(new URL(request.url).origin + "/live-cache", request);
    const cache = caches.default;
    let cached = await cache.match(cacheKey);
    if (cached) return cached;

    try {
      const baselineDoc = await fetchBaseline();
      const codes = Object.keys(baselineDoc.baseline || {});
      const liveMap = await fetchAllLive(codes);
      const payload = buildPayload(baselineDoc, liveMap);

      const resp = new Response(JSON.stringify(payload), { headers: corsHeaders() });
      resp.headers.set("Cache-Control", `public, max-age=${CACHE_SECONDS}`);
      ctx.waitUntil(cache.put(cacheKey, resp.clone()));
      return resp;
    } catch (err) {
      return new Response(JSON.stringify({ error: String(err) }), {
        status: 500,
        headers: corsHeaders(),
      });
    }
  },
};
