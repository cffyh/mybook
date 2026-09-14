import { handleMcp } from "./mcp.js";
import { serveWikiJs } from "./vault.js";

const COOKIE = "vault_session";
const SESSION_TTL = 60 * 60 * 24 * 30;
const OTP_TTL = 60 * 10;
const OTP_COOLDOWN = 60;
const OTP_MAX_ATTEMPTS = 5;

const PUBLIC_PATHS = new Set([
  "/login",
  "/login.html",
  "/assets/vault.css",
  "/assets/login.js",
]);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path === "/mcp") {
      return handleMcp(request, env);
    }
    if (request.method === "OPTIONS" && path === "/mcp") {
      return handleMcp(request, env);
    }

    if (path === "/api/auth/request" && request.method === "POST") {
      return requestCode(request, env);
    }
    if (path === "/api/auth/verify" && request.method === "POST") {
      return verifyCode(request, env);
    }
    if (path === "/api/auth/logout" && request.method === "POST") {
      return logout(request, env);
    }
    if (path === "/api/auth/me") {
      const session = await readSession(request, env);
      return json({ ok: true, authed: !!session });
    }

    const session = await readSession(request, env);
    const publicPage = PUBLIC_PATHS.has(path);

    if (!session && !publicPage) {
      if (wantsHtml(request) || path === "/" || path.startsWith("/s/")) {
        return redirect(new URL("/login", url));
      }
      return new Response("Unauthorized", { status: 401 });
    }

    if (session && (path === "/login" || path === "/login.html")) {
      return redirect(new URL("/", url));
    }

    const wikiJs = path.match(/^\/s\/([^/]+)\/assets\/content\.js$/);
    if (wikiJs) {
      const over = await serveWikiJs(env, wikiJs[1], null);
      if (over) return over;
    }

    const asset = await env.ASSETS.fetch(request);
    const headers = new Headers(asset.headers);
    if (isPrivateAsset(path)) {
      headers.set("Cache-Control", "private, no-store");
    }
    headers.set("Referrer-Policy", "same-origin");
    headers.set("X-Content-Type-Options", "nosniff");
    return new Response(asset.body, {
      status: asset.status,
      statusText: asset.statusText,
      headers,
    });
  },
};

function isPrivateAsset(path) {
  return (
    path === "/" ||
    path.endsWith(".html") ||
    path.endsWith(".js") ||
    path.endsWith(".json") ||
    path.startsWith("/s/")
  );
}

function wantsHtml(request) {
  return (request.headers.get("Accept") || "").includes("text/html");
}

function redirect(url) {
  return Response.redirect(url.toString(), 302);
}

function json(data, status = 200, headers) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...headers,
    },
  });
}

function clientIp(request) {
  return request.headers.get("CF-Connecting-IP") || "unknown";
}

function cookieValue(request, name) {
  const raw = request.headers.get("Cookie") || "";
  for (const part of raw.split(";")) {
    const [k, ...rest] = part.trim().split("=");
    if (k === name) return rest.join("=");
  }
  return "";
}

function sessionCookie(token, maxAge) {
  const parts = [
    `${COOKIE}=${token}`,
    "Path=/",
    "HttpOnly",
    "Secure",
    "SameSite=Lax",
    `Max-Age=${maxAge}`,
  ];
  return parts.join("; ");
}

async function sha256Hex(text) {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function randomDigits(n) {
  const buf = new Uint32Array(n);
  crypto.getRandomValues(buf);
  let out = "";
  for (const n32 of buf) out += String(n32 % 10);
  return out;
}

function randomToken() {
  const buf = new Uint8Array(32);
  crypto.getRandomValues(buf);
  return [...buf].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function readSession(request, env) {
  const token = cookieValue(request, COOKIE);
  if (!token) return null;
  const raw = await env.AUTH.get(`session:${token}`);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

async function requestCode(request, env) {
  const ip = clientIp(request);
  const coolKey = `cool:${ip}`;
  if (await env.AUTH.get(coolKey)) {
    return json({ ok: false, error: "验证码发送过于频繁，请稍后再试。" }, 429);
  }

  const code = randomDigits(6);
  const hash = await sha256Hex(code);
  await env.AUTH.put(
    "otp:current",
    JSON.stringify({ hash, attempts: 0 }),
    { expirationTtl: OTP_TTL },
  );
  await env.AUTH.put(coolKey, "1", { expirationTtl: OTP_COOLDOWN });

  const minutes = Math.floor(OTP_TTL / 60);
  const text = `知识总库登录验证码：${code}\n${minutes} 分钟内有效。若不是你本人操作，请忽略。`;
  const html = `<p>知识总库登录验证码：</p><p style="font-size:28px;letter-spacing:0.2em;font-family:monospace"><b>${code}</b></p><p>${minutes} 分钟内有效。若不是你本人操作，请忽略。</p>`;

  try {
    await env.EMAIL.send({
      to: env.AUTH_EMAIL,
      from: { email: env.MAIL_FROM, name: env.MAIL_FROM_NAME || "知识总库" },
      subject: `登录验证码 ${code}`,
      text,
      html,
    });
  } catch (err) {
    console.error("email send failed", err && err.code, err && err.message);
    return json({ ok: false, error: "验证码发送失败，请稍后重试。" }, 502);
  }

  return json({ ok: true, sent: true, ttl: OTP_TTL });
}

async function verifyCode(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "请求无效。" }, 400);
  }
  const code = String(body.code || "").replace(/\s+/g, "");
  if (!/^\d{6}$/.test(code)) {
    return json({ ok: false, error: "请输入 6 位验证码。" }, 400);
  }

  const raw = await env.AUTH.get("otp:current");
  if (!raw) {
    return json({ ok: false, error: "验证码无效或已过期，请重新发送。" }, 400);
  }
  const rec = JSON.parse(raw);
  if ((rec.attempts || 0) >= OTP_MAX_ATTEMPTS) {
    await env.AUTH.delete("otp:current");
    return json({ ok: false, error: "尝试次数过多，请重新发送验证码。" }, 400);
  }

  const hash = await sha256Hex(code);
  if (hash !== rec.hash) {
    rec.attempts = (rec.attempts || 0) + 1;
    await env.AUTH.put("otp:current", JSON.stringify(rec), {
      expirationTtl: OTP_TTL,
    });
    return json({ ok: false, error: "验证码不正确。" }, 400);
  }

  await env.AUTH.delete("otp:current");
  const token = randomToken();
  await env.AUTH.put(
    `session:${token}`,
    JSON.stringify({ email: env.AUTH_EMAIL, at: Date.now() }),
    { expirationTtl: SESSION_TTL },
  );

  return json({ ok: true }, 200, {
    "Set-Cookie": sessionCookie(token, SESSION_TTL),
  });
}

async function logout(request, env) {
  const token = cookieValue(request, COOKIE);
  if (token) await env.AUTH.delete(`session:${token}`);
  return json({ ok: true }, 200, {
    "Set-Cookie": sessionCookie("", 0),
  });
}
