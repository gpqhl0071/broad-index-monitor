/** 右上角天气预报：浏览器定位 → /api/weather，展开查看 7 日 */

const WEATHER_REFRESH_MS = 30 * 60 * 1000;

/** WMO code → 图标类型 */
function iconTypeFromCode(code) {
  const c = code == null ? -1 : Number(code);
  if (c <= 1) return "sunny";
  if (c === 2) return "partly";
  if (c === 3) return "cloudy";
  if (c === 45 || c === 48) return "fog";
  if (c >= 51 && c <= 57) return "drizzle";
  if ((c >= 61 && c <= 67) || (c >= 80 && c <= 82)) return "rain";
  if ((c >= 71 && c <= 77) || (c >= 85 && c <= 86)) return "snow";
  if (c >= 95) return "thunder";
  return "cloudy";
}

const ICON_SVGS = {
  sunny: '<circle cx="12" cy="12" r="4.5" fill="#f5c542"/><g stroke="#f5c542" stroke-width="1.6" stroke-linecap="round"><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="2" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="22" y2="12"/><line x1="4.9" y1="4.9" x2="7" y2="7"/><line x1="17" y1="17" x2="19.1" y2="19.1"/><line x1="4.9" y1="19.1" x2="7" y2="17"/><line x1="17" y1="7" x2="19.1" y2="4.9"/></g>',
  partly:
    '<circle cx="16" cy="8" r="3.2" fill="#f5c542"/><path d="M7 18h11a5 5 0 0 0 .2-10 5.8 5.8 0 0 0-10.8 2.6A4.2 4.2 0 0 0 7 18z" fill="#8b9cb3"/>',
  cloudy:
    '<path d="M7 17h12a4.5 4.5 0 0 0 .2-9 5.2 5.2 0 0 0-9.8 2.3A3.8 3.8 0 0 0 7 17z" fill="#8b9cb3"/>',
  fog: '<path d="M5 10h14M5 14h14M5 18h10" stroke="#8b9cb3" stroke-width="1.8" stroke-linecap="round"/>',
  drizzle:
    '<path d="M8 11h10a3.5 3.5 0 0 0 .1-7 4 4 0 0 0-7.6 1.8A3 3 0 0 0 8 11z" fill="#8b9cb3"/><g stroke="#5eb3ff" stroke-width="1.5" stroke-linecap="round"><line x1="9" y1="15" x2="8" y2="18"/><line x1="13" y1="15" x2="12" y2="18"/><line x1="17" y1="15" x2="16" y2="18"/></g>',
  rain: '<path d="M7 10h12a4 4 0 0 0 .1-8 4.6 4.6 0 0 0-8.6 2A3.4 3.4 0 0 0 7 10z" fill="#8b9cb3"/><g stroke="#3d8bfd" stroke-width="1.8" stroke-linecap="round"><line x1="8" y1="14" x2="6.5" y2="19"/><line x1="12" y1="14" x2="10.5" y2="19"/><line x1="16" y1="14" x2="14.5" y2="19"/><line x1="20" y1="14" x2="18.5" y2="19"/></g>',
  snow: '<path d="M7 9h12a4 4 0 0 0 .1-8 4.6 4.6 0 0 0-8.6 2A3.4 3.4 0 0 0 7 9z" fill="#8b9cb3"/><g fill="#b8d4f0"><circle cx="9" cy="16" r="1.2"/><circle cx="13" cy="18" r="1.2"/><circle cx="17" cy="16" r="1.2"/><circle cx="20" cy="19" r="1.2"/></g>',
  thunder:
    '<path d="M7 9h12a4 4 0 0 0 .1-8 4.6 4.6 0 0 0-8.6 2A3.4 3.4 0 0 0 7 9z" fill="#6a7d96"/><path d="M13 13l-2.5 5h3l-1.5 4 5-7h-3.2L16 13z" fill="#f5c542"/>',
};

function weatherIconHtml(code, size) {
  const type = iconTypeFromCode(code);
  const inner = ICON_SVGS[type] || ICON_SVGS.cloudy;
  const label = type === "sunny" ? "晴" : type;
  return `<span class="weather-icon weather-icon--${type}" style="width:${size}px;height:${size}px" role="img" aria-label="${label}"><svg viewBox="0 0 24 24" width="${size}" height="${size}" aria-hidden="true">${inner}</svg></span>`;
}

function formatTempRange(day) {
  const hi = day.temp_max;
  const lo = day.temp_min;
  if (hi == null && lo == null) return "—";
  if (lo == null) return `${hi}°`;
  if (hi == null) return `${lo}°`;
  return `${hi}°/${lo}°`;
}

/** 与展开面板「今天」同源：日预报 daily[0]，避免与 current 实况不一致 */
function getTodayDay(data) {
  const days = data.days || [];
  return days.find((d) => d.is_today) || days[0] || null;
}

function renderSummaryHtml(data) {
  const today = getTodayDay(data);
  if (today) {
    const icon = weatherIconHtml(today.code, 18);
    const temps = formatTempRange(today);
    const label = today.label || "—";
    return `${icon}<span class="weather-summary-text">${data.city || "—"} ${temps} ${label}</span>`;
  }
  const cur = data.current || {};
  const t = cur.temperature != null ? `${cur.temperature}°` : "—";
  const label = cur.label || "—";
  const icon = weatherIconHtml(cur.code, 18);
  return `${icon}<span class="weather-summary-text">${data.city || "—"} ${t} ${label}</span>`;
}

function renderDays(data) {
  const container = document.getElementById("weatherDays");
  const days = (data.days || []).slice(0, 8);
  if (!days.length) {
    container.innerHTML = '<span class="weather-muted">暂无预报</span>';
    return;
  }
  container.innerHTML = days
    .map((d) => {
      const title = d.is_today ? "今天" : d.weekday;
      const icon = weatherIconHtml(d.code, 26);
      return `
        <div class="weather-day${d.is_today ? " is-today" : ""}">
          <span class="weather-day-title">${title}</span>
          ${icon}
          <span class="weather-day-label">${d.label}</span>
          <span class="weather-day-temp">${formatTempRange(d)}</span>
        </div>
      `;
    })
    .join("");
}

function setSummary(html, isError) {
  const el = document.getElementById("weatherSummary");
  if (isError) {
    el.textContent = html;
  } else {
    el.innerHTML = html;
  }
  el.classList.toggle("weather-error", !!isError);
}

async function fetchWeather(lat, lon) {
  const qs = lat != null && lon != null ? `?lat=${lat}&lon=${lon}` : "";
  const res = await fetch(`/api/weather${qs}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function getCoords() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null);
      return;
    }
    const timer = setTimeout(() => resolve(null), 6000);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        clearTimeout(timer);
        resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude });
      },
      () => {
        clearTimeout(timer);
        resolve(null);
      },
      { enableHighAccuracy: false, timeout: 5000, maximumAge: 600000 }
    );
  });
}

async function loadWeather() {
  try {
    const coords = await getCoords();
    const data = await fetchWeather(coords?.lat, coords?.lon);
    setSummary(renderSummaryHtml(data), false);
    renderDays(data);
  } catch (e) {
    setSummary("天气加载失败", true);
    document.getElementById("weatherDays").innerHTML =
      '<span class="weather-muted">请稍后重试</span>';
  }
}

function initWeatherWidget() {
  const toggle = document.getElementById("weatherToggle");
  const panel = document.getElementById("weatherPanel");
  const widget = document.getElementById("weatherWidget");

  toggle.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = panel.hidden;
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    widget.classList.toggle("is-open", open);
  });

  document.addEventListener("click", (e) => {
    if (!widget.contains(e.target)) {
      panel.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      widget.classList.remove("is-open");
    }
  });

  loadWeather();
  setInterval(loadWeather, WEATHER_REFRESH_MS);
}

initWeatherWidget();
