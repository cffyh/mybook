#!/usr/bin/env python3
"""Build an offline wiki (static SPA) from the factory articles."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import sys
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

EBOOK_DIR = Path(__file__).resolve().parent
ROOT = EBOOK_DIR.parent
WIKI_DIR = ROOT / "wiki"
sys.path.insert(0, str(EBOOK_DIR))

import build_epub as ep  # noqa: E402


def find_id(articles: list[dict], *needles: str) -> str:
    for needle in needles:
        for a in articles:
            if needle in a["title"]:
                return a["id"]
    return articles[0]["id"] if articles else ""


def volume_html(vol: ep.Volume) -> str:
    cards = []
    for ch in vol.chapters:
        if ch.kind == "volume":
            continue
        cards.append(
            f'<a class="card" href="#/{html_lib.escape(ch.item_id)}">'
            f"<b>{html_lib.escape(ch.title)}</b></a>"
        )
    blurb = f"<p class='no-indent'>{html_lib.escape(vol.blurb)}</p>" if vol.blurb else ""
    return (
        f'<div class="home-hero"><h1>{html_lib.escape(vol.title)}</h1></div>'
        f"{blurb}<div class='cards'>{''.join(cards)}</div>"
    )


def chapter_html(
    ch: ep.Chapter,
    vol: ep.Volume,
    path_map: dict[str, str],
    dir_map: dict[str, str],
    today: str,
) -> str:
    if ch.kind == "volume":
        return volume_html(vol)
    if ch.kind == "generated" and ch.title == "前言":
        fragment = ep.md_to_html(ep.PREFACE_MD.format(today=today))
        return ep.inner_html(ep.fragment_to_xml(fragment))
    if ch.kind == "generated":
        return ep.inner_html(ep.fragment_to_xml(ep.colophon_html()))
    assert ch.path is not None
    fragment = ep.source_to_fragment(ch.path)
    root = ep.fragment_to_xml(fragment)
    ep.rewrite_links(root, ch.path, path_map, dir_map, link_kind="hash")
    return ep.inner_html(root)


def headings_of(html: str) -> str:
    try:
        doc = ep.lhtml.fromstring(f"<div>{html}</div>")
        bits = [
            (h.text_content() or "").strip()
            for h in doc.xpath(".//h2|.//h3|.//h4")
        ]
        return " ".join(b for b in bits if b)
    except Exception:
        return ""


def home_html(articles: list[dict]) -> str:
    p1 = find_id(articles, "以有限应对无限")
    p2 = find_id(articles, "导 论", "导论")
    p3 = find_id(articles, "控制论的奠基")
    p4 = find_id(articles, "从小与大到以小控大")
    return f"""
<div class="home-hero">
  <h1>以小控大</h1>
  <p>工厂文集的离线阅读页。侧栏点一篇即达，不必翻页；J / K 相邻篇，/ 搜索。</p>
</div>
<p class="no-indent">往下追到世界与思维的底层，往上接到人如何在现实里变强。两端之间是同一套机制在不同域显影。</p>
<h2>四条入口</h2>
<div class="cards">
  <a class="card" href="#/{p1}"><b>先立合题</b><span>以有限应对无限 → 逻辑 → 实事求是 → 实践 → 小与大</span></a>
  <a class="card" href="#/{p2}"><b>先立思维与学习</b><span>知识论导论 → 知识 → 理性 → 思维</span></a>
  <a class="card" href="#/{p3}"><b>直接走向交易</b><span>控制论奠基 → 目标差距 → 点 → 生存空间</span></a>
  <a class="card" href="#/{p4}"><b>从小与大走进闭环</b><span>底层视角如何闭环，再着地到工程技术</span></a>
</div>
<p class="no-indent">三本成品书是同一批素材的三种切法。后卷与前卷会有主题回响，用侧栏搜篇名即可。</p>
"""


def build_payload(volumes: list[ep.Volume]) -> dict:
    today = date.today().isoformat()
    path_map: dict[str, str] = {}
    dir_map: dict[str, str] = {}
    vol_page_by_key: dict[str, str] = {}
    for vol in volumes:
        vol_page = next(ch for ch in vol.chapters if ch.kind == "volume")
        vol_page_by_key[vol.key] = vol_page.item_id
        for ch in vol.chapters:
            if ch.path is not None:
                path_map[str(ch.path.resolve())] = ch.item_id
                dir_map.setdefault(str(ch.path.parent.resolve()), ch.item_id)
    for folder, key in (
        ("书稿 4", "book4"),
        ("书稿 3", "book3"),
        ("书稿2", "book2"),
        ("书稿1", "book1"),
        ("书稿 5", "book5"),
        ("关键文章", "key"),
        ("札记", "notes"),
        ("素材", "appendix"),
    ):
        if key in vol_page_by_key:
            dir_map[str((ROOT / folder).resolve())] = vol_page_by_key[key]

    articles: list[dict] = []
    nav_volumes: list[dict] = []
    order: list[str] = []
    for vol in volumes:
        nav_arts = []
        for ch in vol.chapters:
            html = chapter_html(ch, vol, path_map, dir_map, today)
            rec = {
                "id": ch.item_id,
                "title": ch.title,
                "volume": vol.title,
                "html": html,
                "headings": headings_of(html),
            }
            articles.append(rec)
            nav_arts.append(
                {"id": ch.item_id, "title": ch.title, "headings": rec["headings"]}
            )
            if ch.kind != "volume":
                order.append(ch.item_id)
        nav_volumes.append(
            {
                "id": next(c.item_id for c in vol.chapters if c.kind == "volume"),
                "title": vol.title,
                "articles": nav_arts,
            }
        )
    return {
        "title": ep.BOOK_TITLE,
        "homeHtml": home_html(articles),
        "volumes": nav_volumes,
        "articles": articles,
        "order": order,
    }


def write_wiki() -> None:
    sources = ep.discover_sources()
    volumes, leftovers = ep.collect_volumes(sources)
    ep.assign_filenames(volumes)
    payload = build_payload(volumes)
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    (WIKI_DIR / "assets").mkdir(exist_ok=True)
    js = "window.WIKI = " + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"
    out = WIKI_DIR / "assets" / "content.js"
    out.write_text(js, encoding="utf-8")
    print(f"sources {len(sources)}, articles {len(payload['articles'])}")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    if leftovers:
        print("leftovers:")
        for p in leftovers:
            print(" ", ep.rel(p))


def serve(port: int) -> None:
    class WikiHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(WIKI_DIR), **kwargs)

    httpd = ThreadingHTTPServer(("127.0.0.1", port), WikiHandler)
    print(f"wiki at http://127.0.0.1:{port}/")
    httpd.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build offline wiki")
    parser.add_argument("--serve", action="store_true", help="build then serve on :8765")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()
    if not args.no_build:
        write_wiki()
    if args.serve:
        serve(args.port)


if __name__ == "__main__":
    main()
