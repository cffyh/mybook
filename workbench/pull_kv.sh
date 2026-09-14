#!/bin/sh
# Pull KV workbench history into this standalone git repo.
# Each KV commit becomes a local git commit tagged [kv:<sha>].
# After this you can: git log / git checkout <git-sha> -- .
set -e
cd "$(dirname "$0")"
NS="${WORKBENCH_KV_NS:-37a6220378264cb28ab8d1e3b52bfdde}"

if [ ! -d .git ]; then
  git init
  git checkout -B workbench
fi

wrangler kv key get --namespace-id "$NS" --remote wiki:workbench > snapshot.json
wrangler kv key get --namespace-id "$NS" --remote wb:log > history.json || echo '[]' > history.json

python3 snapshot.py --replay-history

git add -A
if git diff --cached --quiet; then
  echo "working tree already matches HEAD snapshot"
else
  git commit -m "sync working tree from KV HEAD $(date -u +%Y-%m-%dT%H:%MZ)"
fi
git log -8 --oneline
echo
echo "任意回退（只动本仓库）：  git checkout <commit> -- ."
echo "任意回退（线上 KV）：     MCP revert_to { sha }"
