#!/usr/bin/env python3
"""Write workbench snapshot.json into toc.html + articles/*.html for git diffs.

  python3 snapshot.py                 # expand current snapshot.json
  python3 snapshot.py --replay-history  # also replay history.json into git
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ART = ROOT / "articles"
NS = os.environ.get("WORKBENCH_KV_NS", "37a6220378264cb28ab8d1e3b52bfdde")


def write_tree(wiki: dict) -> None:
    ART.mkdir(exist_ok=True)
    for old in ART.glob("*.html"):
        old.unlink()
    for a in wiki.get("articles") or []:
        aid = a["id"]
        (ART / f"{aid}.html").write_text(
            f"<!-- {a.get('title', '')} | {a.get('volume', '')} -->\n{a.get('html', '')}\n",
            encoding="utf-8",
        )
    sections = []
    for vol in wiki.get("volumes") or []:
        links = "\n".join(
            f'  <a data-id="{n["id"]}">{n["title"]}</a>'
            for n in (vol.get("tree") or [])
            if n.get("id")
        )
        sections.append(
            f'<section data-volume-id="{vol["id"]}" title="{vol["title"]}">\n{links}\n</section>'
        )
    toc = (
        '<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="utf-8">'
        f'<title>{wiki.get("title", "工作台")} · 目录</title></head><body>\n'
        '<nav data-space="workbench">\n'
        + "\n".join(sections)
        + "\n</nav>\n</body></html>\n"
    )
    (ROOT / "toc.html").write_text(toc, encoding="utf-8")
    (ROOT / "snapshot.json").write_text(
        json.dumps(wiki, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"articles {len(list(ART.glob('*.html')))} toc.html snapshot.json")


def known_kv_shas() -> set[str]:
    if not (ROOT / ".git").exists():
        return set()
    try:
        out = subprocess.check_output(
            ["git", "log", "--pretty=%B"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return set()
    found = set()
    for line in out.splitlines():
        if "[kv:" in line:
            start = line.index("[kv:") + 4
            end = line.find("]", start)
            if end > start:
                found.add(line[start:end])
    return found


def kv_get(key: str) -> str:
    return subprocess.check_output(
        [
            "wrangler",
            "kv",
            "key",
            "get",
            "--namespace-id",
            NS,
            "--remote",
            key,
        ],
        cwd=ROOT,
        text=True,
    )


def replay_history() -> None:
    raw = (ROOT / "history.json").read_text(encoding="utf-8").strip() or "[]"
    log = json.loads(raw)
    if not isinstance(log, list):
        log = []
    have = known_kv_shas()
    # KV log is newest-first; skip duplicate content-addressed shas
    pending = []
    seen = set(have)
    for c in reversed(log):
        sha = c.get("sha")
        if not sha or sha in seen:
            continue
        seen.add(sha)
        pending.append(c)
    if not pending:
        print("history already in git")
        wiki = json.loads((ROOT / "snapshot.json").read_text(encoding="utf-8"))
        write_tree(wiki)
        return
    for c in pending:
        sha = c["sha"]
        blob = json.loads(kv_get(f"wb:commit:{sha}"))
        wiki = blob.get("wiki")
        if not wiki:
            print(f"skip {sha[:12]} (no wiki)")
            continue
        write_tree(wiki)
        subprocess.check_call(["git", "add", "-A"], cwd=ROOT)
        empty = subprocess.call(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        msg = f"{blob.get('message') or c.get('message') or 'kv'} [kv:{sha}]"
        env = os.environ.copy()
        at = blob.get("at") or c.get("at")
        if at:
            env["GIT_AUTHOR_DATE"] = at
            env["GIT_COMMITTER_DATE"] = at
        if empty == 0:
            # same tree as previous; still record the kv sha
            subprocess.check_call(
                ["git", "commit", "--allow-empty", "-m", msg],
                cwd=ROOT,
                env=env,
            )
        else:
            subprocess.check_call(["git", "commit", "-m", msg], cwd=ROOT, env=env)
        print(f"committed {sha[:12]}")


def main() -> None:
    if "--replay-history" in sys.argv:
        # snapshot.json is live HEAD; keep a copy so we can restore after replay
        live_raw = (ROOT / "snapshot.json").read_text(encoding="utf-8")
        replay_history()
        live = json.loads(live_raw)
        write_tree(live)
        return
    wiki = json.loads((ROOT / "snapshot.json").read_text(encoding="utf-8"))
    write_tree(wiki)


if __name__ == "__main__":
    main()
