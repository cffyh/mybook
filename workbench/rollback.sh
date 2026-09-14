#!/bin/sh
# Restore this repo's files to any local git commit. Does not touch live KV.
# Live rollback: MCP revert_to { "sha": "<kv sha>" }
set -e
cd "$(dirname "$0")"
if [ -z "$1" ]; then
  echo "usage: ./rollback.sh <git-commit>"
  echo
  git log --oneline -20
  exit 1
fi
git checkout "$1" -- snapshot.json toc.html articles
echo "working tree now matches $1"
echo "只是本地文件。线上回退请用 MCP revert_to，sha 见 commit 里的 [kv:...]"
