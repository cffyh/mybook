(function () {
  const W = window.WIKI;
  if (!W) {
    document.getElementById("article").textContent = "文集数据未载入。";
    return;
  }

  const $ = (id) => document.getElementById(id);
  const app = $("app");
  const tree = $("tree");
  const article = $("article");
  const crumb = $("crumb");
  const q = $("q");
  const scroll = $("scroll");

  const theme = localStorage.getItem("wiki-theme") || "light";
  document.documentElement.setAttribute("data-theme", theme);

  const articles = W.articles;
  const order = W.order;
  const byId = Object.fromEntries(articles.map((a) => [a.id, a]));

  function parseHash() {
    const raw = location.hash || "#/";
    if (!raw.startsWith("#/")) {
      return { type: "heading-only", heading: raw.slice(1) };
    }
    const rest = raw.slice(2);
    if (!rest) return { type: "home" };
    const slash = rest.indexOf("/");
    if (slash === -1) return { type: "id", id: decodeURIComponent(rest) };
    return {
      type: "id",
      id: decodeURIComponent(rest.slice(0, slash)),
      heading: rest.slice(slash + 1),
    };
  }

  function renderTree(filter) {
    const needle = (filter || "").trim().toLowerCase();
    const current = parseHash().id;
    const html = [];
    for (const vol of W.volumes) {
      const items = vol.articles.filter((a) => {
        if (!needle) return true;
        const hay = (a.title + " " + (a.headings || "")).toLowerCase();
        return hay.includes(needle);
      });
      if (needle && items.length === 0) continue;
      const open =
        needle ||
        vol.articles.some((a) => a.id === current) ||
        vol.id === current;
      html.push(`<div class="vol${open ? "" : " collapsed"}" data-vol="${vol.id}">`);
      html.push(
        `<button type="button" class="vol-btn">${escapeHtml(vol.title)}</button>`
      );
      html.push("<ul>");
      for (const a of items) {
        const cls = a.id === current ? "active" : "";
        html.push(
          `<li><a class="${cls}" href="#/${a.id}">${escapeHtml(a.title)}</a></li>`
        );
      }
      html.push("</ul></div>");
    }
    tree.innerHTML = html.join("") || '<p class="empty">没有匹配的篇目</p>';
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setPager(id) {
    const i = order.indexOf(id);
    const prev = i > 0 ? order[i - 1] : null;
    const next = i >= 0 && i < order.length - 1 ? order[i + 1] : null;
    for (const [el, target] of [
      ["prev", prev],
      ["prev2", prev],
      ["next", next],
      ["next2", next],
    ]) {
      const node = $(el);
      if (!target) {
        node.setAttribute("aria-disabled", "true");
        node.href = "#/";
        node.textContent = el.startsWith("prev") ? "上一篇" : "下一篇";
      } else {
        node.removeAttribute("aria-disabled");
        node.href = "#/" + target;
        const t = byId[target];
        node.textContent = (el.startsWith("prev") ? "← " : "") + t.title + (el.startsWith("next") ? " →" : "");
        if (el === "prev" || el === "prev2") node.textContent = "← " + t.title;
        if (el === "next" || el === "next2") node.textContent = t.title + " →";
      }
    }
  }

  function showHome() {
    article.innerHTML = W.homeHtml;
    crumb.textContent = "文集首页";
    document.title = W.title + " · 离线文集";
    setPager(null);
    renderTree(q.value);
    scroll.scrollTop = 0;
  }

  function showArticle(id, heading) {
    const a = byId[id];
    if (!a) {
      showHome();
      return;
    }
    article.innerHTML = a.html;
    crumb.textContent = a.volume + "  /  " + a.title;
    document.title = a.title + " · " + W.title;
    setPager(id);
    renderTree(q.value);
    const active = tree.querySelector("a.active");
    if (active) active.scrollIntoView({ block: "nearest" });
    if (heading) {
      const el = document.getElementById(heading) || article.querySelector("#" + CSS.escape(heading));
      if (el) el.scrollIntoView({ block: "start" });
      else scroll.scrollTop = 0;
    } else {
      scroll.scrollTop = 0;
    }
  }

  function route() {
    const p = parseHash();
    if (p.type === "home") {
      showHome();
      return;
    }
    if (p.type === "heading-only") {
      const el = document.getElementById(p.heading);
      if (el) el.scrollIntoView({ block: "start" });
      return;
    }
    showArticle(p.id, p.heading);
  }

  tree.addEventListener("click", (e) => {
    const btn = e.target.closest(".vol-btn");
    if (btn) {
      btn.parentElement.classList.toggle("collapsed");
    }
  });

  q.addEventListener("input", () => renderTree(q.value));

  $("theme").addEventListener("click", () => {
    const next =
      document.documentElement.getAttribute("data-theme") === "dark"
        ? "light"
        : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("wiki-theme", next);
  });

  $("toggle-sidebar").addEventListener("click", () => {
    if (window.matchMedia("(max-width: 860px)").matches) {
      app.classList.toggle("drawer-open");
    } else {
      app.classList.toggle("sidebar-hidden");
    }
  });

  document.addEventListener("keydown", (e) => {
    const typing =
      e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA";
    if (e.key === "/" && !typing) {
      e.preventDefault();
      q.focus();
      q.select();
      return;
    }
    if (e.key === "Escape" && document.activeElement === q) {
      q.value = "";
      q.blur();
      renderTree("");
      return;
    }
    if (typing) return;
    const p = parseHash();
    const i = order.indexOf(p.id);
    if ((e.key === "j" || e.key === "J" || e.key === "ArrowRight") && i >= 0 && i < order.length - 1) {
      location.hash = "#/" + order[i + 1];
    }
    if ((e.key === "k" || e.key === "K" || e.key === "ArrowLeft") && i > 0) {
      location.hash = "#/" + order[i - 1];
    }
  });

  window.addEventListener("hashchange", route);
  renderTree("");
  route();
})();
