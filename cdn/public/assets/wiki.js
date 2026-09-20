(function () {
  function contentSrc() {
    const m = location.pathname.match(/\/s\/([^/]+)/);
    if (m) return `/s/${m[1]}/assets/content.js`;
    return new URL("assets/content.js", location.href).href;
  }

  function fail(msg) {
    const el = document.getElementById("article");
    if (el) el.textContent = msg || "文集数据未载入。";
  }

  function loadWikiData() {
    if (window.WIKI) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = contentSrc();
      s.onload = () => (window.WIKI ? resolve() : reject(new Error("empty")));
      s.onerror = () => reject(new Error("load"));
      document.head.appendChild(s);
    });
  }

  function startWiki() {
  const W = window.WIKI;
  if (!W) {
    fail();
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

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function nodeText(node) {
    if (node.type === "article") {
      const heads = (node.headings || []).map((h) => h.text).join(" ");
      return (node.title + " " + heads).toLowerCase();
    }
    return (node.children || []).some((c) => nodeText(c).includes) ? "" : "";
  }

  function matches(node, needle) {
    if (!needle) return true;
    if (node.type === "article") {
      return nodeText(node).includes(needle);
    }
    return (node.children || []).some((c) => matches(c, needle));
  }

  function containsId(node, id) {
    if (!id) return false;
    if (node.type === "article") return node.id === id;
    return (node.children || []).some((c) => containsId(c, id));
  }

  function renderArticle(node, current) {
    const cls = node.id === current ? "active" : "";
    let html = `<li><a class="${cls}" href="#/${node.id}">${escapeHtml(node.title)}</a>`;
    if (node.id === current && node.headings && node.headings.length) {
      html += '<ul class="heads">';
      for (const h of node.headings) {
        const href = h.id ? `#/${node.id}/${encodeURIComponent(h.id)}` : `#/${node.id}`;
        html += `<li><a class="head" href="${href}">${escapeHtml(h.text)}</a></li>`;
      }
      html += "</ul>";
    }
    html += "</li>";
    return html;
  }

  function renderChildren(nodes, needle, current) {
    const parts = [];
    const leaves = [];
    const flush = () => {
      if (!leaves.length) return;
      parts.push("<ul>");
      parts.push(leaves.join(""));
      parts.push("</ul>");
      leaves.length = 0;
    };
    for (const node of nodes || []) {
      if (!matches(node, needle)) continue;
      if (node.type === "group") {
        flush();
        parts.push(renderGroup(node, needle, current));
      } else {
        leaves.push(renderArticle(node, current));
      }
    }
    flush();
    return parts.join("");
  }

  function renderGroup(node, needle, current) {
    const open = !!(needle || containsId(node, current));
    const cls = open ? "tree-group" : "tree-group collapsed";
    return (
      `<div class="${cls}">` +
      `<div class="group-head">` +
        `<button type="button" class="twist" aria-label="展开或收起"></button>` +
        `<span>${escapeHtml(node.title)}</span>` +
      `</div>` +
      `<div class="group-body">${renderChildren(node.children, needle, current)}</div>` +
      "</div>"
    );
  }

  function renderTree(filter) {
    const needle = (filter || "").trim().toLowerCase();
    const current = parseHash().id;
    const html = [];
    for (const vol of W.volumes) {
      if (needle && !matches({ type: "group", children: vol.tree }, needle) && vol.id !== current) {
        continue;
      }
      const open = !!(needle || containsId({ type: "group", children: vol.tree }, current) || vol.id === current);
      html.push(`<div class="vol${open ? "" : " collapsed"}" data-vol="${vol.id}">`);
      html.push(
        `<div class="vol-head">` +
          `<button type="button" class="twist" aria-label="展开或收起"></button>` +
          `<a class="${vol.id === current ? "active" : ""}" href="#/${vol.id}">${escapeHtml(vol.title)}</a>` +
        `</div>`
      );
      html.push(`<div class="vol-body">${renderChildren(vol.tree, needle, current)}</div>`);
      html.push("</div>");
    }
    tree.innerHTML = html.join("") || '<p class="empty">没有匹配的篇目</p>';
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
        if (el === "prev" || el === "next") {
          node.textContent = el === "prev" ? "上一篇" : "下一篇";
          node.title = t.title;
        } else if (el === "prev2") {
          node.textContent = "← " + t.title;
        } else {
          node.textContent = t.title + " →";
        }
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
    const trail = (a.trail || []).join("  /  ");
    crumb.textContent = [a.volume, trail, a.title].filter(Boolean).join("  /  ");
    document.title = a.title + " · " + W.title;
    setPager(id);
    renderTree(q.value);
    const active = tree.querySelector("a.active");
    if (active) active.scrollIntoView({ block: "nearest" });
    if (heading) {
      const decoded = decodeURIComponent(heading);
      const el =
        document.getElementById(decoded) ||
        article.querySelector("#" + CSS.escape(decoded));
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
    const twist = e.target.closest(".twist");
    if (twist) {
      e.preventDefault();
      const wrap = twist.closest(".vol, .tree-group");
      if (wrap) wrap.classList.toggle("collapsed");
      return;
    }
    if (e.target.closest("a[href]")) closeOverlayNav();
  });

  q.addEventListener("input", () => renderTree(q.value));

  const overlayNav = window.matchMedia("(max-width: 860px)");
  const toggleBtn = $("toggle-sidebar");
  const scrim = $("nav-scrim");
  const navClose = $("nav-close");
  const topBar = document.querySelector(".top");

  function isOverlayNav() {
    const bar = $("sidebar");
    return !!(bar && getComputedStyle(bar).position === "fixed");
  }

  function syncTopH() {
    if (!topBar) return;
    document.documentElement.style.setProperty(
      "--top-h",
      `${Math.ceil(topBar.getBoundingClientRect().height)}px`,
    );
  }

  function overlayNavOpen() {
    return isOverlayNav() && app.classList.contains("nav-open");
  }

  function setOverlayNav(open) {
    app.classList.toggle("nav-open", open);
    if (scrim) {
      scrim.hidden = !open;
      scrim.setAttribute("aria-hidden", open ? "false" : "true");
    }
    if (toggleBtn) {
      toggleBtn.setAttribute("aria-expanded", open ? "true" : "false");
      toggleBtn.textContent = open && isOverlayNav() ? "关闭" : "目录";
    }
    const bar = $("sidebar");
    if (bar && isOverlayNav()) bar.toggleAttribute("inert", !open);
    syncTopH();
  }

  function closeOverlayNav() {
    setOverlayNav(false);
  }

  function bindTap(el, fn) {
    if (!el) return;
    el.addEventListener("click", (e) => {
      e.preventDefault();
      fn(e);
    });
  }

  bindTap(toggleBtn, () => {
    if (isOverlayNav()) {
      setOverlayNav(!app.classList.contains("nav-open"));
      return;
    }
    app.classList.toggle("sidebar-hidden");
  });

  bindTap(scrim, closeOverlayNav);
  bindTap(navClose, closeOverlayNav);

  overlayNav.addEventListener("change", () => {
    closeOverlayNav();
    if (isOverlayNav()) app.classList.remove("sidebar-hidden");
    syncTopH();
  });
  window.addEventListener("resize", syncTopH);
  syncTopH();

  document.addEventListener("keydown", (e) => {
    const typing =
      e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA";
    if (e.key === "/" && !typing) {
      e.preventDefault();
      q.focus();
      q.select();
      return;
    }
    if (e.key === "Escape" && overlayNavOpen()) {
      e.preventDefault();
      closeOverlayNav();
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

  function mountVaultChrome() {
    const m = location.pathname.match(/\/s\/([^/]+)/);
    if (!m) return;
    const spaceId = m[1];
    const brand = document.querySelector(".brand");
    if (!brand) return;
    const nav = document.createElement("div");
    nav.className = "space-nav";
    nav.innerHTML = '<a href="/">全部空间</a>';
    brand.appendChild(nav);
    fetch("/spaces.json")
      .then((r) => r.json())
      .then((data) => {
        const space = (data.spaces || []).find((s) => s.id === spaceId);
        const sub = brand.querySelector(".sub");
        if (space && sub) {
          sub.textContent = space.subtitle || "空间";
        }
      })
      .catch(() => {});
  }

  window.addEventListener("hashchange", () => {
    closeOverlayNav();
    route();
  });
  mountVaultChrome();
  renderTree("");
  route();
  }

  loadWikiData().then(startWiki).catch(() => fail());
})();
