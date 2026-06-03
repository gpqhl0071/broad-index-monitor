/** 点击基金名称：弹出权威第三方详情页链接菜单 */
(function () {
  const menu = document.getElementById("fundLinkMenu");
  const menuTitle = document.getElementById("fundLinkMenuTitle");
  const menuList = document.getElementById("fundLinkMenuList");
  const tbody = document.getElementById("quoteBody");

  if (!menu || !menuList) return;

  function buildLinks({ code, exchange, kind, name }) {
    const ex = exchange || (code.startsWith("159") || code.startsWith("399") ? "sz" : "sh");
    const links = [];

    if (kind === "index") {
      links.push({
        label: "东方财富",
        url: `https://quote.eastmoney.com/zs${code}.html`,
      });
    } else {
      links.push({
        label: "东方财富",
        url: `https://quote.eastmoney.com/${ex}${code}.html`,
      });
      links.push({
        label: "天天基金",
        url: `https://fundf10.eastmoney.com/jbgk_${code}.html`,
      });
    }

    links.push(
      {
        label: "新浪财经",
        url: `https://finance.sina.com.cn/realstock/company/${ex}${code}/nc.shtml`,
      },
      {
        label: "腾讯财经",
        url: `https://gu.qq.com/${ex}${code}`,
      },
      {
        label: "同花顺",
        url: `https://stockpage.10jqka.com.cn/${code}/`,
      },
      {
        label: "雪球",
        url: `https://xueqiu.com/S/${ex.toUpperCase()}${code}`,
      }
    );

    return links;
  }

  function hideMenu() {
    menu.hidden = true;
    menu.classList.remove("is-visible");
    menu.setAttribute("aria-hidden", "true");
  }

  function positionMenu(anchor) {
    const rect = anchor.getBoundingClientRect();
    const margin = 8;
    menu.hidden = false;
    menu.style.visibility = "hidden";
    menu.classList.add("is-visible");
    menu.setAttribute("aria-hidden", "false");

    const mw = menu.offsetWidth;
    const mh = menu.offsetHeight;
    let left = rect.left;
    let top = rect.bottom + 6;
    if (left + mw > window.innerWidth - margin) {
      left = window.innerWidth - mw - margin;
    }
    if (top + mh > window.innerHeight - margin) {
      top = rect.top - mh - 6;
    }
    left = Math.max(margin, left);
    top = Math.max(margin, top);

    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
    menu.style.visibility = "";
  }

  function showMenu(anchor, row) {
    const code = anchor.dataset.code;
    const kind = anchor.dataset.kind;
    const exchange = anchor.dataset.exchange;
    const name = anchor.dataset.name || code;

    const links = buildLinks({ code, exchange, kind, name });
    menuTitle.textContent = `${name}（${code}）`;
    const esc = (s) =>
      String(s)
        .replace(/&/g, "&amp;")
        .replace(/"/g, "&quot;")
        .replace(/</g, "&lt;");
    menuList.innerHTML = links
      .map(
        (l) =>
          `<li><button type="button" class="fund-link-item" data-url="${esc(l.url)}">${esc(l.label)}</button></li>`
      )
      .join("");

    positionMenu(anchor);
  }

  menuList.addEventListener("click", (e) => {
    const btn = e.target.closest(".fund-link-item");
    if (!btn) return;
    const url = btn.dataset.url;
    if (url) window.open(url, "_blank", "noopener,noreferrer");
    hideMenu();
  });

  tbody.addEventListener("click", (e) => {
    const btn = e.target.closest(".fund-name-link");
    if (!btn) return;
    e.stopPropagation();
    const row = btn.closest("tr.quote-row");
    if (!row) return;
    if (menu.hidden) {
      showMenu(btn, row);
    } else {
      hideMenu();
    }
  });

  document.addEventListener("click", (e) => {
    if (!menu.hidden && !menu.contains(e.target) && !e.target.closest(".fund-name-link")) {
      hideMenu();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideMenu();
  });

  window.addEventListener("resize", hideMenu);
  window.addEventListener("scroll", hideMenu, true);

  window.FundLinks = { hideMenu };
})();
