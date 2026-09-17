/* 盤中即時更新:輪詢 Cloudflare Worker,盤中(9:00-13:30 台北時間,週一到週五)每分鐘刷新一次 */
(function () {
  // 部署 Worker 後,把這裡換成你自己的 Worker 網址
  const WORKER_URL = "https://tw-stock-live.kayo99023.workers.dev/";
  const POLL_MS = 60000;

  const UP = "up", DOWN = "down";

  function taipeiNow() {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Taipei", hour12: false,
      weekday: "short", hour: "2-digit", minute: "2-digit",
    }).formatToParts(new Date());
    const get = (t) => parts.find((p) => p.type === t).value;
    return { weekday: get("weekday"), hour: Number(get("hour")), minute: Number(get("minute")) };
  }

  function isMarketHours() {
    const { weekday, hour, minute } = taipeiNow();
    if (weekday === "Sat" || weekday === "Sun") return false;
    const mins = hour * 60 + minute;
    return mins >= 9 * 60 && mins <= 13 * 60 + 30;
  }

  function fmtVolLots(shares) {
    return `${Math.round(shares / 1000).toLocaleString("zh-Hant")} 張`;
  }

  function chgStr(dir, pct) {
    const sign = dir === UP ? "+" : dir === DOWN ? "-" : "";
    return `${sign}${Math.abs(pct).toFixed(2)}%`;
  }

  function escAttr(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;");
  }

  function cardHtml(it) {
    const r = it.rank;
    const rclass = r <= 3 ? `r${r}` : "";
    return `
      <div class="card ${rclass} clickable-stock" data-code="${it.code}" data-name="${escAttr(it.name)}">
        <div class="rank">${r}</div>
        <div class="rankchip">${r}</div>
        <div class="code">${it.code}</div>
        <div class="name">${it.name}</div>
        <div class="metric">${fmtVolLots(it.volume)}</div>
        <div class="price-row">
          <span>${it.close} 元</span>
          <span class="chg ${it.change_dir}">${chgStr(it.change_dir, it.change_pct)}</span>
        </div>
        <div class="chart-hint">📈</div>
      </div>`;
  }

  function ratioRowHtml(it) {
    const r = it.rank;
    const rclass = r <= 3 ? `r${r}` : "";
    return `
      <tr class="clickable-stock" data-code="${it.code}" data-name="${escAttr(it.name)}">
        <td class="rank-cell ${rclass}">${r}</td>
        <td>${it.code}</td>
        <td>${it.name}</td>
        <td class="num" style="color:var(--accent-2); font-weight:700;">${it.ratio.toFixed(2)} 倍</td>
        <td class="num">${fmtVolLots(it.volume)}</td>
        <td class="num">${fmtVolLots(it.prev3_sum)}</td>
        <td class="num">${it.close}</td>
        <td class="num ${it.change_dir}">${chgStr(it.change_dir, it.change_pct)}</td>
      </tr>`;
  }

  function top100RowHtml(it) {
    const r = it.rank;
    const rclass = r <= 3 ? `r${r}` : "";
    return `
      <tr class="clickable-stock" data-code="${it.code}" data-name="${escAttr(it.name)}">
        <td class="rank-cell ${rclass}">${r}</td>
        <td>${it.code}</td>
        <td>${it.name}</td>
        <td class="num">${fmtVolLots(it.volume)}</td>
        <td class="num">${it.close}</td>
        <td class="num ${it.change_dir}">${chgStr(it.change_dir, it.change_pct)}</td>
      </tr>`;
  }

  function setStatus(mode, text) {
    const el = document.getElementById("liveStatus");
    if (!el) return;
    el.className = `live-status ${mode}`;
    el.textContent = text;
  }

  async function doUpdate() {
    setStatus("loading", "🔄 更新中…");
    try {
      const resp = await fetch(WORKER_URL, { cache: "no-store" });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const data = await resp.json();

      const cardsEl = document.getElementById("top10-cards");
      if (cardsEl && data.top100_by_volume) {
        cardsEl.innerHTML = data.top100_by_volume.slice(0, 10).map(cardHtml).join("\n");
      }
      const ratioEl = document.getElementById("ratio-tbody");
      if (ratioEl && data.top10_by_ratio) {
        ratioEl.innerHTML = data.top10_by_ratio.map(ratioRowHtml).join("\n");
      }
      const top100El = document.getElementById("top100-tbody");
      if (top100El && data.top100_by_volume) {
        top100El.innerHTML = data.top100_by_volume.map(top100RowHtml).join("\n");
      }

      const now = new Intl.DateTimeFormat("zh-Hant", {
        timeZone: "Asia/Taipei", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
      }).format(new Date());
      setStatus("live", `🔴 盤中即時更新中 ・ 最後更新 ${now}(每分鐘刷新)`);
    } catch (e) {
      setStatus("error", "⚠️ 即時資料暫時無法取得,顯示為最近一次收盤資料");
      console.error("live update failed", e);
    }
  }

  function poll() {
    if (!isMarketHours()) {
      setStatus("idle", "⚪ 非盤中時段,以上為最近一次收盤資料(9:00-13:30 台北時間會自動即時更新)");
      return;
    }
    doUpdate();
  }

  document.addEventListener("DOMContentLoaded", () => {
    poll();
    setInterval(poll, POLL_MS);
  });

  // 手動測試用:在瀏覽器 Console 打 refreshLiveNow() 可以無視盤中時段限制,強制抓一次即時資料
  window.refreshLiveNow = doUpdate;
})();
