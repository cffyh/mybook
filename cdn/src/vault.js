const WIKI_KEY = (spaceId) => `wiki:${spaceId}`;
const HEAD_KEY = "wb:ref:HEAD";
const LOG_KEY = "wb:log";
const COMMIT_KEY = (sha) => `wb:commit:${sha}`;
const ID_RE = /^[a-zA-Z0-9._:-]{1,80}$/;
const WRITABLE = new Set(["workbench"]);

export function validId(id) {
  return ID_RE.test(String(id || ""));
}

export function assertWritable(spaceId) {
  if (!WRITABLE.has(spaceId)) {
    throw new Error("只有工作台可以改目录和正文；以小控大只读。");
  }
}

export async function listSpaces(env) {
  const res = await env.ASSETS.fetch(new URL("https://vault.local/spaces.json"));
  const data = await res.json();
  return data.spaces || [];
}

export async function loadWiki(env, spaceId) {
  if (!validId(spaceId)) throw new Error("无效的 space_id");
  const cached = await env.AUTH.get(WIKI_KEY(spaceId), "json");
  if (cached && cached.articles) {
    if (spaceId === "workbench") {
      const head = await env.AUTH.get(HEAD_KEY);
      if (!head) await commitWiki(env, cached, "seed existing kv");
    }
    return cached;
  }

  const url = new URL(`https://vault.local/s/${spaceId}/assets/content.js`);
  const res = await env.ASSETS.fetch(url);
  if (!res.ok) throw new Error(`空间 ${spaceId} 不存在`);
  const wiki = parseWikiJs(await res.text());
  await env.AUTH.put(WIKI_KEY(spaceId), JSON.stringify(wiki));
  if (spaceId === "workbench") {
    const head = await env.AUTH.get(HEAD_KEY);
    if (!head) await commitWiki(env, wiki, "seed from static content.js");
  }
  return wiki;
}

export async function saveWiki(env, spaceId, wiki, message) {
  if (spaceId === "workbench") {
    await commitWiki(env, wiki, message || "update");
    return wiki;
  }
  await env.AUTH.put(WIKI_KEY(spaceId), JSON.stringify(wiki));
  return wiki;
}

export async function commitWiki(env, wiki, message) {
  const body = JSON.stringify(wiki);
  const head = await env.AUTH.get(HEAD_KEY);
  const at = new Date().toISOString();
  const note = String(message || "update");
  const sha = await sha256Hex(
    JSON.stringify({ parent: head || null, message: note, at, wiki }),
  );
  if (head === sha) {
    await env.AUTH.put(WIKI_KEY("workbench"), body);
    return sha;
  }
  const commit = {
    sha,
    parent: head || null,
    message: note,
    at,
    wiki,
  };
  await env.AUTH.put(COMMIT_KEY(sha), JSON.stringify(commit));
  await env.AUTH.put(HEAD_KEY, sha);
  await env.AUTH.put(WIKI_KEY("workbench"), body);
  const log = (await env.AUTH.get(LOG_KEY, "json")) || [];
  log.unshift({ sha, parent: commit.parent, message: commit.message, at: commit.at });
  await env.AUTH.put(LOG_KEY, JSON.stringify(log.slice(0, 500)));
  return sha;
}

export async function listHistory(env) {
  const head = await env.AUTH.get(HEAD_KEY);
  const log = (await env.AUTH.get(LOG_KEY, "json")) || [];
  const items = log
    .map((c) => {
      const current = c.sha === head ? " data-head=\"true\"" : "";
      return `<li data-sha="${escapeHtml(c.sha)}"${current}><code>${escapeHtml(c.sha.slice(0, 12))}</code> ${escapeHtml(c.at)} — ${escapeHtml(c.message)}</li>`;
    })
    .join("");
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>工作台版本</title></head><body><h1>工作台 git 日志</h1><p>HEAD <code>${escapeHtml((head || "").slice(0, 12))}</code>。用 revert_to 回退到任意 sha，会再记一笔 revert，旧提交仍在。</p><ol>${items}</ol></body></html>`;
}

export async function revertTo(env, sha) {
  const full = await resolveSha(env, sha);
  const commit = await env.AUTH.get(COMMIT_KEY(full), "json");
  if (!commit || !commit.wiki) throw new Error("版本不存在");
  const newSha = await commitWiki(
    env,
    commit.wiki,
    `revert to ${full.slice(0, 12)}`,
  );
  return { sha: newSha, restored: full, wiki: commit.wiki };
}

async function resolveSha(env, sha) {
  const raw = String(sha || "").trim();
  if (!raw) throw new Error("缺少 sha");
  if (await env.AUTH.get(COMMIT_KEY(raw))) return raw;
  const log = (await env.AUTH.get(LOG_KEY, "json")) || [];
  const hits = log.filter((c) => c.sha.startsWith(raw));
  if (hits.length === 1) return hits[0].sha;
  if (hits.length > 1) throw new Error("sha 前缀不唯一");
  throw new Error("版本不存在");
}

export function parseWikiJs(text) {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start < 0 || end < start) throw new Error("无法解析 content.js");
  return JSON.parse(text.slice(start, end + 1));
}

export function headingsFromHtml(html) {
  const out = [];
  const re = /<h2\b([^>]*)>([\s\S]*?)<\/h2>/gi;
  let m;
  while ((m = re.exec(html))) {
    const attrs = m[1] || "";
    const text = String(m[2] || "")
      .replace(/<[^>]+>/g, "")
      .replace(/\s+/g, " ")
      .trim();
    const idMatch = attrs.match(/\bid=["']([^"']+)["']/i);
    if (text) out.push({ id: idMatch ? idMatch[1] : "", text });
  }
  return out;
}

export function getArticle(wiki, articleId) {
  return (wiki.articles || []).find((a) => a.id === articleId) || null;
}

export function upsertArticle(wiki, rec) {
  const articles = wiki.articles || [];
  const i = articles.findIndex((a) => a.id === rec.id);
  if (i >= 0) articles[i] = { ...articles[i], ...rec };
  else articles.push(rec);
  wiki.articles = articles;
  if (!Array.isArray(wiki.order)) wiki.order = [];
  if (!wiki.order.includes(rec.id)) wiki.order.push(rec.id);
  const home = (wiki.volumes || []).find((v) =>
    (v.tree || []).some((n) => n.id === rec.id),
  );
  if (home && home.title === rec.volume) {
    home.tree = home.tree.map((n) =>
      n.id === rec.id
        ? { ...n, title: rec.title, headings: rec.headings || [] }
        : n,
    );
  } else {
    moveArticle(wiki, rec.id, rec.volume, -1);
  }
  return wiki;
}

export function moveArticle(wiki, articleId, volumeRef, index) {
  const art = getArticle(wiki, articleId);
  if (!art) throw new Error(`找不到篇目 ${articleId}`);
  const volumes = wiki.volumes || [];
  for (const vol of volumes) {
    vol.tree = (vol.tree || []).filter((n) => n.id !== articleId);
  }
  let vol =
    volumes.find((v) => v.id === volumeRef) ||
    volumes.find((v) => v.title === volumeRef);
  if (!vol) {
    const id = slugId(volumeRef);
    vol = { id, title: volumeRef, tree: [] };
    volumes.push(vol);
    wiki.volumes = volumes;
  }
  art.volume = vol.title;
  const node = {
    type: "article",
    id: art.id,
    title: art.title,
    headings: art.headings || [],
  };
  const tree = vol.tree || [];
  const at = index === undefined || index === null || index < 0 ? tree.length : Math.min(index, tree.length);
  tree.splice(at, 0, node);
  vol.tree = tree;
  wiki.order = orderFromTrees(wiki);
  return wiki;
}

export function createVolume(wiki, id, title) {
  if (!validId(id)) throw new Error("volume id 无效");
  if (!wiki.volumes) wiki.volumes = [];
  if (wiki.volumes.some((v) => v.id === id)) throw new Error("volume 已存在");
  wiki.volumes.push({ id, title: title || id, tree: [] });
  return wiki;
}

export function renameVolume(wiki, volumeRef, title) {
  const vol =
    (wiki.volumes || []).find((v) => v.id === volumeRef) ||
    (wiki.volumes || []).find((v) => v.title === volumeRef);
  if (!vol) throw new Error("找不到分组");
  const old = vol.title;
  vol.title = title;
  for (const a of wiki.articles || []) {
    if (a.volume === old) a.volume = title;
  }
  return wiki;
}

export function deleteArticle(wiki, articleId) {
  wiki.articles = (wiki.articles || []).filter((a) => a.id !== articleId);
  wiki.order = (wiki.order || []).filter((id) => id !== articleId);
  for (const vol of wiki.volumes || []) {
    vol.tree = (vol.tree || []).filter((n) => n.id !== articleId);
  }
  return wiki;
}

export function tocHtml(spaceId, wiki) {
  const sections = (wiki.volumes || [])
    .map((vol) => {
      const links = (vol.tree || [])
        .filter((n) => n.id)
        .map(
          (n) =>
            `  <a data-id="${escapeHtml(n.id)}">${escapeHtml(n.title)}</a>`,
        )
        .join("\n");
      return `<section data-volume-id="${escapeHtml(vol.id)}" title="${escapeHtml(vol.title)}">\n${links}\n</section>`;
    })
    .join("\n");
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>${escapeHtml(wiki.title || spaceId)} · 目录</title></head>
<body>
<nav data-space="${escapeHtml(spaceId)}">
${sections}
</nav>
</body>
</html>`;
}

export function applyToc(wiki, html) {
  const sectionRe = /<section\b([^>]*)>([\s\S]*?)<\/section>/gi;
  const volumes = [];
  const order = [];
  const seen = new Set();
  let m;
  while ((m = sectionRe.exec(html))) {
    const attrs = m[1] || "";
    const idMatch = attrs.match(/data-volume-id=["']([^"']+)["']/i);
    const titleMatch = attrs.match(/\btitle=["']([^"']+)["']/i);
    const title = titleMatch ? titleMatch[1] : "";
    const id = idMatch ? idMatch[1] : slugId(title || `vol-${volumes.length + 1}`);
    if (!validId(id)) throw new Error(`无效 volume id: ${id}`);
    const tree = [];
    const aRe = /<a\b([^>]*)>([\s\S]*?)<\/a>/gi;
    let a;
    while ((a = aRe.exec(m[2] || ""))) {
      const aidMatch = a[1].match(/data-id=["']([^"']+)["']/i);
      const aid = aidMatch && aidMatch[1];
      if (!aid) continue;
      const art = getArticle(wiki, aid);
      if (!art) throw new Error(`目录引用了不存在的篇 ${aid}`);
      art.volume = title || art.volume;
      tree.push({
        type: "article",
        id: aid,
        title: art.title,
        headings: art.headings || [],
      });
      if (!seen.has(aid)) {
        seen.add(aid);
        order.push(aid);
      }
    }
    volumes.push({ id, title: title || id, tree });
  }
  if (!volumes.length) throw new Error("目录里没有 section，拒绝空写");
  wiki.volumes = volumes;
  wiki.order = order;
  return wiki;
}

function orderFromTrees(wiki) {
  const ids = [];
  for (const vol of wiki.volumes || []) {
    for (const n of vol.tree || []) {
      if (n.id && !ids.includes(n.id)) ids.push(n.id);
    }
  }
  return ids;
}

function slugId(title) {
  const s = String(title || "")
    .toLowerCase()
    .replace(/[^a-z0-9:_-]+/g, "-")
    .replace(/^-|-$/g, "");
  return s.slice(0, 40) || `vol-${Date.now().toString(36)}`;
}

export function articleHtmlDoc(spaceId, article) {
  const trail = (article.trail || []).join(" / ");
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>${escapeHtml(article.title)} · ${escapeHtml(spaceId)}</title>
</head>
<body>
<article data-space="${escapeHtml(spaceId)}" data-id="${escapeHtml(article.id)}" data-volume="${escapeHtml(article.volume || "")}">
<header>
<p class="meta">${escapeHtml([article.volume, trail].filter(Boolean).join(" · "))}</p>
</header>
${article.html || ""}
</article>
</body>
</html>`;
}

export function spacesHtml(spaces) {
  const items = spaces
    .map(
      (s) =>
        `<li data-space="${escapeHtml(s.id)}"><a href="/s/${escapeHtml(s.id)}/"><b>${escapeHtml(s.title)}</b></a> — ${escapeHtml(s.blurb || s.subtitle || "")}</li>`,
    )
    .join("");
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>知识总库 · 空间</title></head><body><h1>知识总库</h1><ul>${items}</ul></body></html>`;
}

export function articlesHtml(spaceId, wiki) {
  return tocHtml(spaceId, wiki);
}

async function sha256Hex(text) {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export async function serveWikiJs(env, spaceId, fallback) {
  const cached = await env.AUTH.get(WIKI_KEY(spaceId));
  if (!cached) return fallback;
  const body = `window.WIKI = ${cached};\n`;
  return new Response(body, {
    headers: {
      "Content-Type": "application/javascript; charset=utf-8",
      "Cache-Control": "private, no-store",
    },
  });
}
