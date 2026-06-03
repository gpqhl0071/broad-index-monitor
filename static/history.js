/** 行悬停：右侧展示最近 7 个交易日行情 */
(function () {
  const SHOW_DELAY = 180;
  const HIDE_DELAY = 120;
  const DAYS = 7;

  const popup = document.getElementById("historyPopup");
  const titleEl = document.getElementById("historyTitle");
  const subEl = document.getElementById("historySub");
  const bodyEl = document.getElementById("historyBody");
  const tbody = document.getElementById("quoteBody");
  const analysisSection = document.getElementById("analysisSection");
  const analysisSignal = document.getElementById("analysisSignal");
  const analysisRisk = document.getElementById("analysisRisk");
  const analysisSummary = document.getElementById("analysisSummary");
  const analysisDetails = document.getElementById("analysisDetails");

  const cache = new Map();
  const analysisCache = new Map();
  let showTimer = null;
  let hideTimer = null;
  let activeRow = null;
  let activeCode = null;
  let loadingCode = null;
  let loadingAnalysisCode = null;

  const fmtPrice = (v, kind) => {
    if (v == null) return "—";
    const digits = kind === "index" ? 2 : 3;
    return Number(v).toFixed(digits);
  };

  const fmtPct = (v) => {
    if (v == null) return "—";
    const n = Number(v);
    const sign = n > 0 ? "+" : "";
    return `${sign}${n.toFixed(2)}%`;
  };

  const fmtVol = (v) => {
    if (v == null) return "—";
    const n = Number(v);
    if (n >= 1e8) return `${(n / 1e8).toFixed(2)}亿`;
    if (n >= 1e4) return `${(n / 1e4).toFixed(2)}万`;
    return n.toFixed(0);
  };

  const pctClass = (v) => {
    if (v == null) return "flat";
    const n = Number(v);
    if (n > 0) return "up";
    if (n < 0) return "down";
    return "flat";
  };

  function clearTimers() {
    if (showTimer) {
      clearTimeout(showTimer);
      showTimer = null;
    }
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
  }

  function positionPopup(anchor) {
    const rect = anchor.getBoundingClientRect();
    const gap = 12;
    const margin = 8;
    popup.hidden = false;
    popup.style.visibility = "hidden";
    popup.classList.add("is-visible");
    const pw = popup.offsetWidth;
    const ph = popup.offsetHeight;

    let left = rect.right + gap;
    let top = rect.top + (rect.height - ph) / 2;
    if (left + pw > window.innerWidth - margin) {
      left = rect.left - gap - pw;
    }
    top = Math.max(margin, Math.min(top, window.innerHeight - ph - margin));
    left = Math.max(margin, Math.min(left, window.innerWidth - pw - margin));

    popup.style.top = `${top}px`;
    popup.style.left = `${left}px`;
    popup.style.visibility = "";
  }

  function renderLoading(name) {
    titleEl.textContent = name || "—";
    subEl.textContent = `最近 ${DAYS} 个交易日`;
    bodyEl.innerHTML = '<div class="history-loading">加载中…</div>';
    analysisSection.hidden = true;
    analysisSignal.textContent = "—";
    analysisRisk.textContent = "—";
    analysisSummary.textContent = "—";
    analysisDetails.innerHTML = "";
  }

  function renderAnalysis(data) {
    if (!data || !data.signal) {
      analysisSection.hidden = true;
      return;
    }
    const riskText = { low: "低风险", medium: "中风险", high: "高风险", unknown: "—" };
    analysisSignal.textContent = `${data.icon || ""} ${data.signal_text || "—"}`;
    analysisRisk.textContent = riskText[data.risk] || "—";
    analysisRisk.className = "analysis-risk risk-" + (data.risk || "unknown");
    analysisSummary.textContent = data.summary || "—";
    const details = data.details || [];
    if (details.length) {
      analysisDetails.innerHTML = details.map((d) => `<li>${d}</li>`).join("");
    } else {
      analysisDetails.innerHTML = '<li class="analysis-muted">历史数据不足，仅基于当日行情判断</li>';
    }
    analysisSection.hidden = false;
  }

  function renderTable(data) {
    const kind = data.kind || "fund";
    titleEl.textContent = `${data.name}（${data.code}）`;
    subEl.textContent = `最近 ${DAYS} 个交易日 · ${data.index_name || ""}`;

    const rows = data.items || [];
    if (!rows.length) {
      bodyEl.innerHTML = '<div class="history-loading">暂无数据</div>';
      return;
    }

    const head = `
      <table class="history-table">
        <thead>
          <tr>
            <th>日期</th>
            <th class="num">收盘</th>
            <th class="num">涨跌幅</th>
            <th class="num">成交量</th>
          </tr>
        </thead>
        <tbody>
    `;
    const body = rows
      .map((d) => {
        const cls = pctClass(d.change_pct);
        const date = d.date ? d.date.slice(5) : "—";
        return `
          <tr>
            <td>${date}</td>
            <td class="num">${fmtPrice(d.close, kind)}</td>
            <td class="num ${cls}">${fmtPct(d.change_pct)}</td>
            <td class="num">${fmtVol(d.volume)}</td>
          </tr>
        `;
      })
      .join("");
    bodyEl.innerHTML = head + body + "</tbody></table>";
  }

  function showPopup(row) {
    clearTimers();
    activeRow = row;
    const code = row.dataset.code;
    const name = row.dataset.name;
    activeCode = code;

    renderLoading(name);
    positionPopup(row);
    popup.setAttribute("aria-hidden", "false");

    // 加载历史数据
    const cached = cache.get(code);
    if (cached) {
      renderTable(cached);
    } else if (loadingCode !== code) {
      loadingCode = code;
      fetch(`/api/history?code=${encodeURIComponent(code)}&days=${DAYS}`, { cache: "no-store" })
        .then(async (res) => {
          if (!res.ok) throw Object.assign(new Error(`HTTP ${res.status}`), { status: res.status });
          return res.json();
        })
        .then((data) => {
          cache.set(code, data);
          if (activeCode === code && activeRow) {
            renderTable(data);
            positionPopup(activeRow);
          }
        })
        .catch((err) => {
          if (activeCode !== code) return;
          const msg = err?.status === 404 ? "历史接口未就绪，请重启服务（./restart.sh）" : "加载失败，请稍后重试";
          bodyEl.innerHTML = `<div class="history-loading history-error">${msg}</div>`;
        })
        .finally(() => {
          if (loadingCode === code) loadingCode = null;
        });
    }

    // 加载深度分析
    const cachedAnalysis = analysisCache.get(code);
    if (cachedAnalysis) {
      renderAnalysis(cachedAnalysis);
      positionPopup(row);
    } else if (loadingAnalysisCode !== code) {
      loadingAnalysisCode = code;
      fetch(`/api/analyze?code=${encodeURIComponent(code)}`, { cache: "no-store" })
        .then(async (res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          analysisCache.set(code, data);
          if (activeCode === code && activeRow) {
            renderAnalysis(data);
            positionPopup(activeRow);
          }
        })
        .catch(() => {
          if (activeCode === code) renderAnalysis(null);
        })
        .finally(() => {
          if (loadingAnalysisCode === code) loadingAnalysisCode = null;
        });
    }
  }

  function hidePopup() {
    clearTimers();
    activeRow = null;
    activeCode = null;
    popup.classList.remove("is-visible");
    popup.setAttribute("aria-hidden", "true");
    hideTimer = setTimeout(() => {
      popup.hidden = true;
      hideTimer = null;
    }, 220);
  }

  function scheduleShow(row) {
    if (activeRow === row && popup.classList.contains("is-visible")) return;
    clearTimers();
    hideTimer = null;
    showTimer = setTimeout(() => showPopup(row), SHOW_DELAY);
  }

  function scheduleHide() {
    clearTimers();
    showTimer = null;
    hideTimer = setTimeout(hidePopup, HIDE_DELAY);
  }

  function onRowEnter(e) {
    const row = e.target.closest("tr.quote-row");
    if (!row || !tbody.contains(row)) return;
    scheduleShow(row);
  }

  function onRowLeave(e) {
    const row = e.target.closest("tr.quote-row");
    if (!row) return;
    const related = e.relatedTarget;
    if (!related) {
      scheduleHide();
      return;
    }
    if (row.contains(related) || popup.contains(related)) return;
    if (related.closest?.("tr.quote-row")) return;
    scheduleHide();
  }

  function onPopupEnter() {
    clearTimers();
    hideTimer = null;
  }

  function onPopupLeave(e) {
    const related = e.relatedTarget;
    if (related && activeRow && activeRow.contains(related)) return;
    scheduleHide();
  }

  tbody.addEventListener("mouseover", onRowEnter);
  tbody.addEventListener("mouseout", onRowLeave);
  popup.addEventListener("mouseenter", onPopupEnter);
  popup.addEventListener("mouseleave", onPopupLeave);
  window.addEventListener(
    "scroll",
    () => {
      if (activeRow && popup.classList.contains("is-visible")) positionPopup(activeRow);
    },
    true
  );
  window.addEventListener("resize", () => {
    if (activeRow && popup.classList.contains("is-visible")) positionPopup(activeRow);
  });

  window.HistoryPanel = {
    bindRows() {
      if (activeRow && !document.body.contains(activeRow)) hidePopup();
    },
  };
})();
