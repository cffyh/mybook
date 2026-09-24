---
name: publish-mybook
description: >-
  Rebuild the mybook wiki, commit and push to origin, then deploy the
  knowledge vault to Cloudflare. Use when the user asks to 更新 git、更新 wiki、
  发布到 Cloudflare、发布文集, or to sync i.fotira.com.br / knowledge-vault
  after article changes.
---

# 发布文集

按顺序做完三步：重建 wiki、提交并推送 git、部署 Cloudflare。用户说「更新 git、wiki 和 Cloudflare」时，三步都做，不要只做其中一步。

仓库根目录：本项目根（含 `ebook/`、`wiki/`、`cdn/`）。

## 1. 重建 wiki

系统 `python3` 没有 `markdown`。用文集虚拟环境：

```bash
ebook/.venv/bin/python ebook/build_wiki.py --sync-cdn
```

这会写出 `wiki/assets/content.js`（进 git），并复制到 `cdn/public/s/mybook/assets/content.js`（被 `.gitignore` 忽略，只供部署）。

确认新篇在目录里：`content.js` 的卷四分组与篇名对得上刚改的文章。篇数变了要看构建日志，不要把 `workbench/`、`素材/`、`cdn/**/*.html` 的 leftover 当成漏收。

## 2. Git

先看 `git status`、`git diff`、`git log -5`。只提交这次文集改动：文章、总纲互链、`ebook/build_*.py`、`wiki/assets/content.js`、以及本技能。不要提交 `.env`、密钥、`ebook/.venv/`。

`cdn/public/s/mybook/assets/content.js` 不进 git，这是预期。

提交说明用一两句中文，写为什么改，风格跟近期提交一致。用 HEREDOC 提交。然后 `git push origin HEAD`。本地若已领先远程，把未推的提交一起推上去。

## 3. Cloudflare

在 `cdn/` 下部署。沙箱写不了 wrangler 登录目录，也读不到本机 OAuth，必须在沙箱外执行：

```bash
cd cdn && wrangler deploy
```

成功时输出里有 `https://i.fotira.com.br` 与 `knowledge-vault.*.workers.dev`。

线上 `/s/mybook/assets/content.js` 由 Worker 从静态资源读，不再优先 KV 的 `wiki:mybook`（见 `cdn/src/vault.js` 里只读空间那一支）。部署前确认 `cdn/public/s/mybook/assets/content.js` 与 `wiki/assets/content.js` 是同一份。不要把 mybook 写回 KV。工作台仍以 KV 为真相，发布文集时不要动 `wiki:workbench`。

若线上目录仍是旧的：先确认 `loadWiki` 对非 workbench 空间仍走 `ASSETS` 的 `content.js`；若有人又改回 KV 优先，删掉远程键 `wiki:mybook`（namespace 在 `cdn/wrangler.jsonc` 的 `AUTH`）后再部署。
