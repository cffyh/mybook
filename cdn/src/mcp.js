import {
  applyToc,
  articleHtmlDoc,
  articlesHtml,
  assertWritable,
  createVolume,
  deleteArticle,
  getArticle,
  headingsFromHtml,
  listHistory,
  listSpaces,
  loadWiki,
  moveArticle,
  renameVolume,
  revertTo,
  saveWiki,
  spacesHtml,
  tocHtml,
  upsertArticle,
  validId,
} from "./vault.js";

const PROTOCOL = "2025-03-26";

const TOOLS = [
  {
    name: "list_spaces",
    description: "列出知识总库里的全部 space。返回 HTML。",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "list_articles",
    description: "列出一个 space 的目录树（与侧栏同构的 HTML）。",
    inputSchema: {
      type: "object",
      properties: {
        space_id: { type: "string", description: "例如 workbench 或 mybook" },
      },
      required: ["space_id"],
      additionalProperties: false,
    },
  },
  {
    name: "read_toc",
    description: "读取可编辑目录 HTML：nav > section[data-volume-id][title] > a[data-id]。",
    inputSchema: {
      type: "object",
      properties: { space_id: { type: "string" } },
      required: ["space_id"],
      additionalProperties: false,
    },
  },
  {
    name: "write_toc",
    description:
      "用目录 HTML 整页替换工作台侧栏顺序与分组。不删正文；未出现在目录里的篇会从侧栏消失但仍可用 id 读到。仅 workbench。",
    inputSchema: {
      type: "object",
      properties: {
        space_id: { type: "string" },
        html: { type: "string", description: "含 nav/section/a 的目录 HTML" },
      },
      required: ["space_id", "html"],
      additionalProperties: false,
    },
  },
  {
    name: "move_article",
    description: "把一篇移到指定分组，index 为组内位置（0 起，省略则追加）。仅 workbench。",
    inputSchema: {
      type: "object",
      properties: {
        space_id: { type: "string" },
        article_id: { type: "string" },
        volume: { type: "string", description: "volume id 或标题" },
        index: { type: "number" },
      },
      required: ["space_id", "article_id", "volume"],
      additionalProperties: false,
    },
  },
  {
    name: "create_volume",
    description: "新建侧栏分组。仅 workbench。",
    inputSchema: {
      type: "object",
      properties: {
        space_id: { type: "string" },
        volume_id: { type: "string" },
        title: { type: "string" },
      },
      required: ["space_id", "volume_id", "title"],
      additionalProperties: false,
    },
  },
  {
    name: "rename_volume",
    description: "重命名分组。仅 workbench。",
    inputSchema: {
      type: "object",
      properties: {
        space_id: { type: "string" },
        volume: { type: "string", description: "现有 id 或标题" },
        title: { type: "string" },
      },
      required: ["space_id", "volume", "title"],
      additionalProperties: false,
    },
  },
  {
    name: "delete_article",
    description: "从工作台删除一篇（正文从当前树去掉，历史里仍在）。仅 workbench。",
    inputSchema: {
      type: "object",
      properties: {
        space_id: { type: "string" },
        article_id: { type: "string" },
      },
      required: ["space_id", "article_id"],
      additionalProperties: false,
    },
  },
  {
    name: "list_history",
    description: "工作台 git 风格提交日志。返回 HTML。",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "revert_to",
    description: "把工作台回退到某一提交。会新增一条 revert 记录，旧 sha 仍可再回。",
    inputSchema: {
      type: "object",
      properties: {
        sha: { type: "string", description: "完整 sha 或唯一前缀" },
      },
      required: ["sha"],
      additionalProperties: false,
    },
  },
  {
    name: "read_article",
    description: "读取一篇正文。返回完整 HTML 文档（article 片段在 <article> 内）。",
    inputSchema: {
      type: "object",
      properties: {
        space_id: { type: "string" },
        article_id: { type: "string" },
      },
      required: ["space_id", "article_id"],
      additionalProperties: false,
    },
  },
  {
    name: "write_article",
    description:
      "创建或覆盖一篇。html 为文章正文 HTML。仅 workbench。每次写入记一笔版本。",
    inputSchema: {
      type: "object",
      properties: {
        space_id: { type: "string" },
        article_id: { type: "string" },
        title: { type: "string" },
        html: { type: "string", description: "文章正文 HTML" },
        volume: { type: "string", description: "侧栏分组名，默认沿用或用 space 标题" },
        trail: {
          type: "array",
          items: { type: "string" },
          description: "面包屑，可选",
        },
      },
      required: ["space_id", "article_id", "title", "html"],
      additionalProperties: false,
    },
  },
];

export async function handleMcp(request, env) {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (!checkToken(request, env)) {
    return new Response("Unauthorized", { status: 401, headers: corsHeaders() });
  }
  if (request.method === "GET") {
    return new Response("knowledge-vault MCP. POST JSON-RPC to this URL.", {
      status: 200,
      headers: { ...corsHeaders(), "Content-Type": "text/plain; charset=utf-8" },
    });
  }
  if (request.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405, headers: corsHeaders() });
  }

  let payload;
  try {
    payload = await request.json();
  } catch {
    return rpcError(null, -32700, "Parse error");
  }

  const batch = Array.isArray(payload);
  const messages = batch ? payload : [payload];
  const results = [];
  for (const msg of messages) {
    if (msg && msg.method && msg.id === undefined) continue;
    results.push(await dispatch(msg, env));
  }
  if (!results.length) {
    return new Response(null, { status: 202, headers: corsHeaders() });
  }

  const accept = request.headers.get("Accept") || "";
  const body = batch ? results : results[0];
  if (accept.includes("text/event-stream") && !accept.includes("application/json")) {
    const stream = results
      .map((r) => `event: message\ndata: ${JSON.stringify(r)}\n\n`)
      .join("");
    return new Response(stream, {
      headers: {
        ...corsHeaders(),
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
  }
  return new Response(JSON.stringify(body), {
    headers: {
      ...corsHeaders(),
      "Content-Type": "application/json",
    },
  });
}

function checkToken(request, env) {
  const expected = env.MCP_TOKEN;
  if (!expected) return false;
  const header = request.headers.get("Authorization") || "";
  const got = header.replace(/^Bearer\s+/i, "").trim();
  if (!got || got.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) diff |= got.charCodeAt(i) ^ expected.charCodeAt(i);
  return diff === 0;
}

async function dispatch(msg, env) {
  if (!msg || msg.jsonrpc !== "2.0") {
    return rpcErrObj(msg && msg.id, -32600, "Invalid Request");
  }
  const { id, method, params } = msg;
  try {
    if (method === "initialize") {
      return ok(id, {
        protocolVersion: PROTOCOL,
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: "knowledge-vault", version: "1.0.0" },
        instructions:
          "知识总库 Remote MCP。正文与目录都是 HTML。以小控大只读；工作台可写。改工作台会记 git 式提交，用 list_history / revert_to 任意回退。",
      });
    }
    if (method === "ping") return ok(id, {});
    if (method === "tools/list") return ok(id, { tools: TOOLS });
    if (method === "tools/call") {
      const name = params && params.name;
      const args = (params && params.arguments) || {};
      const html = await callTool(name, args, env);
      return ok(id, {
        content: [{ type: "text", text: html }],
      });
    }
    if (method === "resources/list") return ok(id, { resources: [] });
    if (method === "prompts/list") return ok(id, { prompts: [] });
    return rpcErrObj(id, -32601, `Method not found: ${method}`);
  } catch (err) {
    return ok(id, {
      content: [
        {
          type: "text",
          text: `<p class="error">${escapeHtml(err.message || String(err))}</p>`,
        },
      ],
      isError: true,
    });
  }
}

async function callTool(name, args, env) {
  if (name === "list_spaces") {
    return spacesHtml(await listSpaces(env));
  }
  if (name === "list_articles" || name === "read_toc") {
    const wiki = await loadWiki(env, args.space_id);
    return name === "read_toc"
      ? tocHtml(args.space_id, wiki)
      : articlesHtml(args.space_id, wiki);
  }
  if (name === "read_article") {
    const wiki = await loadWiki(env, args.space_id);
    const article = getArticle(wiki, args.article_id);
    if (!article) throw new Error(`找不到篇目 ${args.article_id}`);
    return articleHtmlDoc(args.space_id, article);
  }
  if (name === "write_article") {
    assertWritable(args.space_id);
    if (!validId(args.article_id) || !validId(args.space_id)) {
      throw new Error("space_id / article_id 格式无效");
    }
    const html = String(args.html || "");
    if (!html.includes("<")) {
      throw new Error("html 必须是 HTML 标签，不能只传纯文本");
    }
    const wiki = await loadWiki(env, args.space_id);
    const prev = getArticle(wiki, args.article_id) || {};
    const rec = {
      id: args.article_id,
      title: String(args.title),
      volume: args.volume || prev.volume || wiki.title || args.space_id,
      trail: Array.isArray(args.trail) ? args.trail : prev.trail || [],
      headings: headingsFromHtml(html),
      html,
    };
    upsertArticle(wiki, rec);
    await saveWiki(env, args.space_id, wiki, `write ${rec.id}`);
    return articleHtmlDoc(args.space_id, rec);
  }
  if (name === "write_toc") {
    assertWritable(args.space_id);
    const wiki = await loadWiki(env, args.space_id);
    applyToc(wiki, String(args.html || ""));
    await saveWiki(env, args.space_id, wiki, "write_toc");
    return tocHtml(args.space_id, wiki);
  }
  if (name === "move_article") {
    assertWritable(args.space_id);
    const wiki = await loadWiki(env, args.space_id);
    moveArticle(wiki, args.article_id, args.volume, args.index);
    await saveWiki(env, args.space_id, wiki, `move ${args.article_id}`);
    return tocHtml(args.space_id, wiki);
  }
  if (name === "create_volume") {
    assertWritable(args.space_id);
    const wiki = await loadWiki(env, args.space_id);
    createVolume(wiki, args.volume_id, args.title);
    await saveWiki(env, args.space_id, wiki, `create volume ${args.volume_id}`);
    return tocHtml(args.space_id, wiki);
  }
  if (name === "rename_volume") {
    assertWritable(args.space_id);
    const wiki = await loadWiki(env, args.space_id);
    renameVolume(wiki, args.volume, args.title);
    await saveWiki(env, args.space_id, wiki, `rename volume ${args.volume}`);
    return tocHtml(args.space_id, wiki);
  }
  if (name === "delete_article") {
    assertWritable(args.space_id);
    const wiki = await loadWiki(env, args.space_id);
    deleteArticle(wiki, args.article_id);
    await saveWiki(env, args.space_id, wiki, `delete ${args.article_id}`);
    return tocHtml(args.space_id, wiki);
  }
  if (name === "list_history") {
    await loadWiki(env, "workbench");
    return listHistory(env);
  }
  if (name === "revert_to") {
    const out = await revertTo(env, args.sha);
    return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>已回退</title></head><body><p>已回退到 <code>${out.restored.slice(0, 12)}</code>，新 HEAD <code>${out.sha.slice(0, 12)}</code>。</p></body></html>`;
  }
  throw new Error(`未知工具 ${name}`);
}

function ok(id, result) {
  return { jsonrpc: "2.0", id, result };
}

function rpcErrObj(id, code, message) {
  return { jsonrpc: "2.0", id: id ?? null, error: { code, message } };
}

function rpcError(id, code, message) {
  return new Response(JSON.stringify(rpcErrObj(id, code, message)), {
    status: 200,
    headers: { ...corsHeaders(), "Content-Type": "application/json" },
  });
}

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers":
      "Authorization, Content-Type, Accept, MCP-Protocol-Version",
    "Access-Control-Expose-Headers": "MCP-Protocol-Version",
    "MCP-Protocol-Version": PROTOCOL,
  };
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
