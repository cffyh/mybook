# 工作台 · 独立 git

这份目录是**单独的 git 仓库**（`workbench` 分支），只版本化工作台，不跟 mybook 文集绑在一起。

线上真相在 Cloudflare KV（`wiki:workbench` + `wb:commit:*`）。MCP 改目录或正文都会记一笔提交。

## 任意回退（线上）

Remote MCP：

- `list_history` — 提交日志
- `revert_to` `{ "sha": "前缀或完整 hash" }` — 回退，并再记一笔 revert（旧 sha 仍在）

以小控大只读；`write_*` / `move_article` / 改目录只能打工作台。

## 任意回退（本仓库）

```bash
cd workbench
./pull_kv.sh          # 把 KV 全量历史写成本地 git
git log
./rollback.sh <commit>   # 或 git checkout <commit> -- .
```

本地 `checkout` / `rollback.sh` 只改磁盘。线上树要用 `revert_to`。commit message 里的 `[kv:…]` 就是线上 sha。

## 目录

MCP 用 HTML 改侧栏：`read_toc` / `write_toc` / `move_article`。
