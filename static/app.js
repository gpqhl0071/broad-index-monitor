const REFRESH_MS = 10_000;

const GROUP_LABELS = { sh: "上证", sz: "深证", kc: "科创", us: "美股", hk: "港股" };
const GROUP_ORDER = ["sh", "sz", "kc", "us", "hk"];

const fmtPrice = (v, kind) => {
  if (v == null || v === "-") return "—";
  const digits = kind === "index" ? 2 : 3;
  return Number(v).toFixed(digits);
};
const fmtPct = (v) => {
  if (v == null || v === "-") return "—";
  const n = Number(v);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
};
const fmtAmt = (v, kind) => {
  if (v == null || v === "-") return "—";
  const n = Number(v);
  const sign = n > 0 ? "+" : "";
  const digits = kind === "index" ? 2 : 3;
  return `${sign}${n.toFixed(digits)}`;
};
const fmtAmount = (v) => {
  if (v == null) return "—";
  const n = Number(v);
  if (n >= 1e8) return `${(n / 1e8).toFixed(2)}亿`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(2)}万`;
  return n.toFixed(0);
};

function pctClass(v) {
  if (v == null) return "flat";
  const n = Number(v);
  if (n > 0) return "up";
  if (n < 0) return "down";
  return "flat";
}

function renderRow(row) {
  const cls = pctClass(row.change_pct);
  const isIndex = row.kind === "index";
  const rowCls = isIndex ? "row-index" : "";
  const typeLabel = isIndex ? "大盘指数" : "场内ETF";
  return `
    <tr class="quote-row ${rowCls}" data-code="${row.code}" data-kind="${row.kind}" data-name="${row.name}">
      <td><span class="type-tag ${isIndex ? "tag-index" : "tag-fund"}">${typeLabel}</span> ${row.index_name}</td>
      <td title="${row.full_name || ""}">${row.name}</td>
      <td>${row.code}</td>
      <td class="num ${cls}">${fmtPct(row.change_pct)}</td>
      <td class="num ${cls}">${fmtPrice(row.price, row.kind)}</td>
      <td class="num ${cls}">${fmtAmt(row.change_amt, row.kind)}</td>
      <td class="num">${fmtPrice(row.open, row.kind)}</td>
      <td class="num">${fmtPrice(row.pre_close, row.kind)}</td>
      <td class="num">${fmtAmount(row.amount)}</td>
      <td class="num">${row.amplitude != null ? Number(row.amplitude).toFixed(2) + "%" : "—"}</td>
    </tr>
  `;
}

function renderRows(items) {
  const tbody = document.getElementById("quoteBody");
  if (!items.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="loading">暂无数据</td></tr>';
    return;
  }

  const byGroup = Object.fromEntries(GROUP_ORDER.map((g) => [g, []]));
  for (const row of items) {
    const g = row.group || "sh";
    (byGroup[g] ??= []).push(row);
  }

  let html = "";
  for (const g of GROUP_ORDER) {
    const rows = byGroup[g];
    if (!rows?.length) continue;
    const label = GROUP_LABELS[g] || g;
    const count = rows.length;
    html += `<tr class="group-header group-${g}"><td colspan="10">${label}<span class="group-count">${count} 只</span></td></tr>`;
    html += rows.map(renderRow).join("");
  }
  tbody.innerHTML = html;
  if (window.HistoryPanel) window.HistoryPanel.bindRows();
}

function updateStatus(data, err) {
  const dot = document.getElementById("statusDot");
  const live = document.getElementById("statusLive");
  const liveLabel = document.getElementById("statusLiveLabel");
  const updatedAt = document.getElementById("statusUpdatedAt");
  const source = document.getElementById("statusSource");
  const interval = document.getElementById("statusInterval");
  const meta = document.getElementById("fetchMeta");

  if (err) {
    dot.className = "status-dot warn";
    live.className = "status-live is-warn";
    liveLabel.textContent = "连接异常";
    updatedAt.textContent = "—";
    source.textContent = err;
    return;
  }

  dot.className = data.last_error ? "status-dot warn" : "status-dot ok";
  live.className = data.last_error ? "status-live is-warn" : "status-live is-ok";
  liveLabel.textContent = data.last_error ? "部分异常" : "实时连接";

  updatedAt.textContent = data.updated_at
    ? new Date(data.updated_at).toLocaleString("zh-CN", { hour12: false })
    : "—";

  const src = data.last_provider_label || data.last_provider || "—";
  const fb = data.used_fallback ? "（备用源）" : "";
  source.textContent = `${src}${fb}`;
  source.title = data.last_error ? `上游异常：${data.last_error}` : "";

  const sec = data.refresh_interval_sec || 10;
  interval.textContent = `每 ${sec} 秒`;

  const ps = data.provider_stats;
  const providerHint = ps?.providers
    ? `轮询源：${ps.providers.map((p) => (ps.provider_labels?.[p] || p)).join(" / ")}`
    : "";
  meta.textContent = [
    `成功 ${data.fetch_count ?? 0} 次 · 失败 ${data.error_count ?? 0} 次`,
    providerHint,
  ].filter(Boolean).join(" · ");
}

let manualRefreshing = false;

async function loadQuotes({ force = false } = {}) {
  if (force && manualRefreshing) return;
  const btn = document.getElementById("statusRefreshBtn");
  if (force) {
    manualRefreshing = true;
    btn.disabled = true;
    btn.classList.add("refreshing");
  }
  try {
    const url = force ? "/api/quotes/refresh" : "/api/quotes";
    const res = await fetch(url, {
      cache: "no-store",
      method: force ? "POST" : "GET",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderRows(data.items || []);
    updateStatus(data, null);
  } catch (e) {
    updateStatus({}, e.message);
  } finally {
    if (force) {
      manualRefreshing = false;
      btn.disabled = false;
      btn.classList.remove("refreshing");
    }
  }
}

document.getElementById("statusRefreshBtn").addEventListener("click", () => {
  loadQuotes({ force: true });
});

loadQuotes();
setInterval(() => loadQuotes(), REFRESH_MS);
