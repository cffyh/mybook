#!/usr/bin/env python3
"""Build an offline wiki (static SPA) from the factory articles."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
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


BOOK1_PARTS = {
    1: "导论",
    2: "第一部 · 世界如何运转",
    3: "第二部 · 认识",
    4: "第三部 · 数学与科学",
    5: "第四部 · 物质图景",
    6: "第五部 · 技术",
    7: "第六部 · 学习",
    8: "第七部 · 表达",
    9: "第八部 · 做事",
    10: "第九部 · 心力",
    11: "第十部 · 社会生态",
}

BOOK5_FILE_GROUP = {
    name: group for group, names in ep.BOOK5_ROOT_GROUPS for name in names
}

NOTE_GROUPS = [
    (
        "全书拆解",
        ("全书拆解", "学习之道", "技术的本质", "工程控制论", "思维科学",
         "控制论与科学方法论", "论系统工程", "钱学森", "星际航行"),
    ),
    (
        "胶球 · OSR · 量子比特海",
        ("胶球", "弦网", "哲学能干什么"),
    ),
    (
        "综合案例",
        ("宁德时代", "ServiceTitan", "孤独不是姿态"),
    ),
]


def section_trail(ch: ep.Chapter, vol: ep.Volume) -> list[str]:
    if ch.kind == "volume" or ch.path is None:
        return []
    rel = ch.path.relative_to(ROOT).as_posix()
    name = ch.path.name
    stem = ch.path.stem

    if vol.key == "book3":
        if "上篇-人怎么做" in rel:
            return ["上篇 · 人怎么做"]
        if "接缝-实践" in rel:
            return ["接缝 · 实践"]
        if "下篇-世界为何回应" in rel:
            return ["下篇 · 小与大"]
        return []

    if vol.key == "book4":
        if "知识" in name:
            return ["知识与理性"]
        if "理性" in name:
            return ["知识与理性"]
        if "思维" in name:
            return ["思维"]
        if "学习" in name:
            return ["从学习到实战"]
        if "生命" in name:
            return ["生命的拼图"]
        return []

    if vol.key == "book2":
        if "骨架" in stem:
            return ["骨架"]
        if "互动" in stem:
            return ["互动"]
        if "实事求是" in stem:
            return ["实事求是"]
        if "学习" in stem:
            return ["学习论"]
        if "观察" in stem:
            return ["观察"]
        return []

    if vol.key == "book5":
        if "/总论/" in rel:
            return ["总论"]
        if name in {
            "从小与大到以小控大——底层视角如何闭环.md",
            "工程技术——着地、积累、外衣与内核.md",
        }:
            return ["着地"]
        if "/点/" in rel:
            return ["点"]
        if "/演绎/" in rel:
            return ["演绎"]
        if "/知识/" in rel:
            return ["知识"]
        if name in BOOK5_FILE_GROUP:
            return [BOOK5_FILE_GROUP[name]]
        if "/走向真实的交易/" in rel:
            m = re.match(r"^(\d+)", stem)
            if m:
                return [
                    {
                        "1": "生存空间",
                        "2": "需求、目标与差距",
                        "3": "复杂现实",
                        "4": "创新与浪潮",
                        "5": "工作模型",
                    }.get(m.group(1), "控制论与机制")
                ]
            return ["控制论与机制"]
        return []

    if vol.key == "book1":
        m = re.match(r"^(\d+)", stem)
        if m:
            part = BOOK1_PARTS.get(int(m.group(1)))
            return [part] if part else []
        return []

    if vol.key == "key":
        if "/逻辑/" in rel:
            return ["逻辑"]
        if "格罗滕迪克" in rel:
            return ["学科", "格罗滕迪克"]
        if "/数学精神/" in rel or "数学精神与科学方法" in name:
            return ["学科", "数学精神"]
        if "/学科/" in rel:
            return ["学科"]
        return ["单篇"]

    if vol.key == "notes":
        for group, keys in NOTE_GROUPS:
            if any(k in stem or k in name for k in keys):
                return [group]
        return ["概念钉"]

    if vol.key == "appendix":
        return ["素材"]
    return []


BOOK5_GROUP_ORDER = [
    "总论",
    "着地",
    "控制论与机制",
    "生存空间",
    "需求、目标与差距",
    "复杂现实",
    "创新与浪潮",
    "工作模型",
    "点",
    "演绎",
    "知识",
    "表达与沟通",
    "学习与技能",
    "记忆与输出",
    "根据地与合流",
]

NOTE_GROUP_ORDER = [
    "全书拆解",
    "胶球 · OSR · 量子比特海",
    "综合案例",
    "概念钉",
]


def order_groups(tree: list[dict], preferred: list[str]) -> list[dict]:
    rank = {title: i for i, title in enumerate(preferred)}
    groups = [n for n in tree if n.get("type") == "group"]
    rest = [n for n in tree if n.get("type") != "group"]
    groups.sort(key=lambda n: rank.get(n["title"], 80 + len(preferred)))
    return rest + groups


def nest_tree(items: list[dict]) -> list[dict]:
    root: list[dict] = []
    buckets: dict[tuple[str, ...], list[dict]] = {(): root}

    def children_of(trail: list[str]) -> list[dict]:
        key = tuple(trail)
        if key in buckets:
            return buckets[key]
        parent = children_of(trail[:-1])
        node = {"type": "group", "title": trail[-1], "children": []}
        parent.append(node)
        buckets[key] = node["children"]
        return node["children"]

    for item in items:
        dest = children_of(item.get("trail") or [])
        dest.append(
            {
                "type": "article",
                "id": item["id"],
                "title": item["title"],
                "headings": item["headings"],
            }
        )
    return root


def cards_from_tree(nodes: list[dict]) -> str:
    chunks: list[str] = []
    for node in nodes:
        if node["type"] == "group":
            kids = "".join(
                f'<a class="card" href="#/{html_lib.escape(c["id"])}">'
                f"<b>{html_lib.escape(c['title'])}</b></a>"
                for c in node["children"]
                if c["type"] == "article"
            )
            nested = cards_from_tree(
                [c for c in node["children"] if c["type"] == "group"]
            )
            chunks.append(
                f"<h3>{html_lib.escape(node['title'])}</h3>"
                f"<div class='cards'>{kids}</div>{nested}"
            )
        else:
            chunks.append(
                f'<a class="card" href="#/{html_lib.escape(node["id"])}">'
                f"<b>{html_lib.escape(node['title'])}</b></a>"
            )
    if nodes and all(n["type"] == "article" for n in nodes):
        return f"<div class='cards'>{''.join(chunks)}</div>"
    return "".join(chunks)


def volume_html(vol: ep.Volume, tree: list[dict]) -> str:
    blurb = (
        f"<p class='no-indent'>{html_lib.escape(vol.blurb)}</p>" if vol.blurb else ""
    )
    return (
        f'<div class="home-hero"><h1>{html_lib.escape(vol.title)}</h1></div>'
        f"{blurb}{cards_from_tree(tree)}"
    )


def chapter_html(
    ch: ep.Chapter,
    path_map: dict[str, str],
    dir_map: dict[str, str],
    today: str,
) -> str:
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


def heading_items(html: str) -> list[dict]:
    try:
        doc = ep.lhtml.fromstring(f"<div>{html}</div>")
    except Exception:
        return []
    out = []
    for h in doc.xpath(".//h2"):
        text = " ".join((h.text_content() or "").split())
        hid = h.get("id") or ""
        if text:
            out.append({"id": hid, "text": text})
    return out


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
        vol_page = next(ch for ch in vol.chapters if ch.kind == "volume")
        leaf_items: list[dict] = []
        for ch in vol.chapters:
            if ch.kind == "volume":
                continue
            html = chapter_html(ch, path_map, dir_map, today)
            heads = heading_items(html)
            rec = {
                "id": ch.item_id,
                "title": ch.title,
                "volume": vol.title,
                "trail": section_trail(ch, vol),
                "html": html,
                "headings": heads,
            }
            articles.append(rec)
            leaf_items.append(
                {
                    "id": ch.item_id,
                    "title": ch.title,
                    "headings": heads,
                    "trail": rec["trail"],
                }
            )
            order.append(ch.item_id)
        tree = nest_tree(leaf_items)
        if vol.key == "book5":
            tree = order_groups(tree, BOOK5_GROUP_ORDER)
        elif vol.key == "notes":
            tree = order_groups(tree, NOTE_GROUP_ORDER)
        articles.append(
            {
                "id": vol_page.item_id,
                "title": vol.title,
                "volume": vol.title,
                "trail": [],
                "html": volume_html(vol, tree),
                "headings": [],
            }
        )
        nav_volumes.append(
            {
                "id": vol_page.item_id,
                "title": vol.title,
                "tree": tree,
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
    for vol in payload["volumes"]:
        groups = [n["title"] for n in vol["tree"] if n.get("type") == "group"]
        leaves = sum(1 for n in vol["tree"] if n.get("type") == "article")
        print(f"  {vol['title']}: groups={groups or '-'} top-leaves={leaves}")
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
