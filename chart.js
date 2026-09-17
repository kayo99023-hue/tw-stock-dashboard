/* 技術分析彈出視窗:K線 + 均線(5/10/20/60/120/240) + 成交量 + 均量(5/20) */
(function () {
  const SMA_COLORS = {
    5: "#f5a623",
    10: "#58d1ff",
    20: "#b57bff",
    60: "#cfd6e6",
    120: "#ff5ca8",
    240: "#ffb27a",
  };
  const VMA_COLORS = { 5: "#ffd54f", 20: "#58d1ff" };
  const UP = "#ff5c5c";
  const DOWN = "#2fbf71";

  let chart = null;
  let overlayEl, closeBtn, titleEl, subEl, containerEl, legendEl, rangeBtnsEl;
  let currentCode = null;
  let fullRange = null; // {from, to}

  function injectModal() {
    const div = document.createElement("div");
    div.innerHTML = `
    <div id="chartOverlay" class="chart-overlay" hidden>
      <div class="chart-modal">
        <div class="chart-modal-head">
          <div>
            <div id="chartTitle" class="chart-title"></div>
            <div id="chartSub" class="chart-sub"></div>
          </div>
          <button id="chartClose" class="chart-close" aria-label="關閉">✕</button>
        </div>
        <div id="chartLegend" class="chart-legend"></div>
        <div id="chartRangeBtns" class="chart-range-btns">
          <button data-range="3m">3個月</button>
          <button data-range="6m">6個月</button>
          <button data-range="1y">1年</button>
          <button data-range="all" class="active">全部</button>
        </div>
        <div id="chartContainer" class="chart-container"></div>
        <div class="chart-note">資料來源:Yahoo Finance 日K ・ 均線:SMA5/10/20/60/120/240 ・ 均量:MA5/20(僅供參考,非投資建議)</div>
      </div>
    </div>`;
    document.body.appendChild(div.firstElementChild);
    overlayEl = document.getElementById("chartOverlay");
    closeBtn = document.getElementById("chartClose");
    titleEl = document.getElementById("chartTitle");
    subEl = document.getElementById("chartSub");
    containerEl = document.getElementById("chartContainer");
    legendEl = document.getElementById("chartLegend");
    rangeBtnsEl = document.getElementById("chartRangeBtns");

    closeBtn.addEventListener("click", closeChart);
    overlayEl.addEventListener("click", (e) => {
      if (e.target === overlayEl) closeChart();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeChart();
    });
    rangeBtnsEl.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-range]");
      if (!btn) return;
      [...rangeBtnsEl.children].forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      applyRange(btn.dataset.range);
    });
    window.addEventListener("resize", () => {
      if (chart && overlayEl && !overlayEl.hidden) {
        chart.resize(containerEl.clientWidth, containerEl.clientHeight);
      }
    });
  }

  function fmt(n) {
    if (n === null || n === undefined || isNaN(n)) return "-";
    return n.toLocaleString("zh-Hant", { maximumFractionDigits: 2 });
  }

  function buildSeries(rec) {
    const candles = [];
    const volumes = [];
    for (let i = 0; i < rec.t.length; i++) {
      if (rec.o[i] == null || rec.c[i] == null) continue;
      candles.push({ time: rec.t[i], open: rec.o[i], high: rec.h[i], low: rec.l[i], close: rec.c[i] });
      const up = rec.c[i] >= rec.o[i];
      volumes.push({ time: rec.t[i], value: rec.v[i], color: up ? UP : DOWN });
    }
    const smaLines = {};
    for (const w of Object.keys(rec.sma)) {
      const arr = [];
      for (let i = 0; i < rec.t.length; i++) {
        const v = rec.sma[w][i];
        if (v == null) continue;
        arr.push({ time: rec.t[i], value: v });
      }
      smaLines[w] = arr;
    }
    const vma = { 5: [], 20: [] };
    for (let i = 0; i < rec.t.length; i++) {
      if (rec.vma5[i] != null) vma[5].push({ time: rec.t[i], value: rec.vma5[i] });
      if (rec.vma20[i] != null) vma[20].push({ time: rec.t[i], value: rec.vma20[i] });
    }
    return { candles, volumes, smaLines, vma };
  }

  function renderLegend(rec, idx) {
    idx = idx == null ? rec.t.length - 1 : idx;
    const o = rec.o[idx], h = rec.h[idx], l = rec.l[idx], c = rec.c[idx], v = rec.v[idx];
    const prevC = idx > 0 ? rec.c[idx - 1] : null;
    const chg = prevC != null ? c - prevC : null;
    const pct = prevC ? (chg / prevC) * 100 : null;
    const dir = chg > 0 ? "up" : chg < 0 ? "down" : "";
    const arrow = chg > 0 ? "▲" : chg < 0 ? "▼" : "";
    let html = `<div class="lg-row lg-main">
      <span>${rec.t[idx]}</span>
      <span>開 ${fmt(o)}</span><span>高 ${fmt(h)}</span><span>低 ${fmt(l)}</span>
      <span>收 <b>${fmt(c)}</b></span>
      <span class="${dir}">${arrow} ${pct != null ? fmt(Math.abs(pct)) : "-"}%</span>
      <span>量 ${fmt(v / 1000)} 張</span>
    </div><div class="lg-row lg-sma">`;
    for (const w of [5, 10, 20, 60, 120, 240]) {
      const val = rec.sma[String(w)][idx];
      html += `<span style="color:${SMA_COLORS[w]}">SMA${w} ${val != null ? fmt(val) : "-"}</span>`;
    }
    html += `</div>`;
    legendEl.innerHTML = html;
  }

  function applyRange(range) {
    if (!chart || !fullRange) return;
    if (range === "all") {
      chart.timeScale().setVisibleRange(fullRange);
      return;
    }
    const months = { "3m": 3, "6m": 6, "1y": 12 }[range] || 12;
    const to = new Date(fullRange.to);
    const from = new Date(to);
    from.setMonth(from.getMonth() - months);
    const fromStr = from.toISOString().slice(0, 10);
    chart.timeScale().setVisibleRange({ from: fromStr < fullRange.from ? fullRange.from : fromStr, to: fullRange.to });
  }

  function openChart(code, name) {
    const rec = window.STOCK_HISTORY && window.STOCK_HISTORY[code];
    if (!overlayEl) injectModal();
    if (!rec) {
      overlayEl.hidden = false;
      titleEl.textContent = `${code} ${name || ""}`;
      subEl.textContent = "沒有這檔股票的歷史資料";
      legendEl.innerHTML = "";
      containerEl.innerHTML = "";
      return;
    }
    currentCode = code;
    overlayEl.hidden = false;
    titleEl.textContent = `${code} ${name || ""}`;
    subEl.textContent = "";
    containerEl.innerHTML = "";

    if (chart) {
      chart.remove();
      chart = null;
    }

    chart = LightweightCharts.createChart(containerEl, {
      layout: { background: { color: "transparent" }, textColor: "#c9d2e0" },
      grid: { vertLines: { color: "#232c45" }, horzLines: { color: "#232c45" } },
      rightPriceScale: { borderColor: "#2a3350" },
      timeScale: { borderColor: "#2a3350" },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      width: containerEl.clientWidth,
      height: containerEl.clientHeight || 480,
    });

    const { candles, volumes, smaLines, vma } = buildSeries(rec);

    const candleSeries = chart.addCandlestickSeries({
      upColor: UP, downColor: DOWN, borderVisible: false,
      wickUpColor: UP, wickDownColor: DOWN,
    });
    candleSeries.setData(candles);
    chart.priceScale("right").applyOptions({ scaleMargins: { top: 0.06, bottom: 0.32 } });

    for (const w of [5, 10, 20, 60, 120, 240]) {
      if (!smaLines[w] || !smaLines[w].length) continue;
      const s = chart.addLineSeries({
        color: SMA_COLORS[w], lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
      });
      s.setData(smaLines[w]);
    }

    const volSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" }, priceScaleId: "volume", color: UP,
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.72, bottom: 0.02 } });
    volSeries.setData(volumes);

    for (const w of [5, 20]) {
      if (!vma[w].length) continue;
      const s = chart.addLineSeries({
        color: VMA_COLORS[w], lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
        priceScaleId: "volume",
      });
      s.setData(vma[w]);
    }

    fullRange = { from: rec.t[0], to: rec.t[rec.t.length - 1] };
    [...rangeBtnsEl.children].forEach((b) => b.classList.remove("active"));
    rangeBtnsEl.children[1].classList.add("active"); // 預設顯示6個月
    applyRange("6m");

    renderLegend(rec);
    chart.subscribeCrosshairMove((param) => {
      if (!param || !param.time) {
        renderLegend(rec);
        return;
      }
      const idx = rec.t.indexOf(param.time);
      if (idx >= 0) renderLegend(rec, idx);
    });
  }

  function closeChart() {
    if (overlayEl) overlayEl.hidden = true;
  }

  window.openStockChart = openChart;
})();
