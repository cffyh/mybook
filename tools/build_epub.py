#!/usr/bin/env python3
"""把仓库里的文章编译成 EPUB 电子书。

只依赖 Python 3.10+ 标准库，不需要 pandoc、calibre 或任何 pip 包。

    python3 tools/build_epub.py                 # 精编版（各书稿＋关键文章＋札记）
    python3 tools/build_epub.py --edition full  # 全集（另附七百余篇原始笔记）
    python3 tools/build_epub.py --edition all   # 两个版本都出
    python3 tools/build_epub.py --check         # 构建后调 epubcheck 校验

分卷、篇目顺序、书名等等都在 tools/book.json 里配置，改结构不用改代码。
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from epubgen import cover as cover_mod
from epubgen import epub, structure
from epubgen.epub import Item, Metadata, NavPoint
from epubgen.mdconv import esc
from epubgen.structure import Article, Collector, Group, Renderer, Volume

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent


def build_timestamp() -> dt.datetime:
    """构建时间取最近一次提交的时间，而不是「现在」。

    这样同一份文稿反复构建会得到字节一致的 EPUB——重跑构建不会在 git 里留下
    一个只有时间戳变化的假 diff。`SOURCE_DATE_EPOCH` 可以覆盖它。
    """
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.strip().isdigit():
        return dt.datetime.fromtimestamp(int(epoch), dt.timezone.utc)
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "log", "-1", "--format=%cI"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return dt.datetime.fromisoformat(result.stdout.strip()).astimezone(dt.timezone.utc)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return dt.datetime.now(dt.timezone.utc)


# ---------------------------------------------------------------- 前后附页


def title_page(meta: Metadata, edition_note: str) -> str:
    lines = [
        f'<h1 class="book-title">{esc(meta.title)}</h1>',
    ]
    if meta.subtitle:
        lines.append(f'<p class="book-subtitle">{esc(meta.subtitle)}</p>')
    if meta.creator:
        lines.append(f'<p class="book-author">{esc(meta.creator)}</p>')
    lines.append(f'<p class="book-imprint">{esc(edition_note)}</p>')
    return "\n".join(lines)


def colophon_page(meta: Metadata, stats: dict[str, object]) -> str:
    rows = "\n".join(
        f"<dt>{esc(key)}</dt><dd>{esc(str(value))}</dd>" for key, value in stats.items()
    )
    return f"""<h1>编纂说明</h1>
<p>{esc(meta.description)}</p>
<p>本书由仓库中的 Markdown、HTML 与 Word 文稿自动编译而成，每一篇的末尾都标注了它在
仓库里的原始路径，便于回查与订正。分卷次序、篇目取舍与卷首语出自仓库自带的
《全书总纲》与《书稿定位与查漏策略》，未改动任何一篇的正文。</p>
<dl>
{rows}
</dl>
<p class="book-imprint">重新构建：<code>python3 tools/build_epub.py</code></p>
"""


def volume_page(volume: Volume) -> str:
    lines = ['<p class="volume-label">卷</p>', f'<h1 class="volume-title">{esc(volume.title)}</h1>']
    if volume.subtitle:
        lines.append(f'<p class="volume-subtitle">{esc(volume.subtitle)}</p>')
    if volume.intro:
        lines.append(f'<p class="volume-intro">{esc(volume.intro)}</p>')
    lines.append('<div class="volume-contents">')
    lines.append(_contents_list(volume.articles, volume.groups))
    lines.append("</div>")
    return "\n".join(lines)


def _contents_list(articles: list[Article], groups: list[Group]) -> str:
    parts = ["<ol>"]
    for article in articles:
        href = article.href.split("/")[-1]
        parts.append(f'<li><a href="{esc(href)}">{esc(article.title)}</a></li>')
    parts.append("</ol>")
    for group in groups:
        parts.append(f'<p class="group-name">{esc(group.title)}</p>')
        parts.append(_contents_list(group.articles, group.groups))
    return "\n".join(parts)


def article_page(article: Article) -> str:
    lines = []
    label = " · ".join(filter(None, [article.volume_title, article.group_title]))
    if label:
        lines.append(f'<p class="article-meta">{esc(label)}</p>')
    lines.append(f'<h1 class="article-title">{esc(article.title)}</h1>')
    lines.append(article.doc.body)
    rel = article.path.relative_to(REPO_ROOT).as_posix()
    lines.append(f'<p class="article-source">原文：{esc(rel)}</p>')
    return "\n".join(lines)


# ---------------------------------------------------------------- 目录树


def build_nav(volumes: list[Volume], *, deep: bool) -> list[NavPoint]:
    points = []
    for volume in volumes:
        point = NavPoint(title=volume.title, href=volume.href)
        point.children = [_article_nav(a, deep) for a in volume.articles]
        point.children += [_group_nav(g, deep) for g in volume.groups]
        points.append(point)
    return points


def _group_nav(group: Group, deep: bool) -> NavPoint:
    point = NavPoint(title=group.title, href=None)
    point.children = [_article_nav(a, deep) for a in group.articles]
    point.children += [_group_nav(g, deep) for g in group.groups]
    if point.children and point.children[0].href:
        # 辑本身没有页面，指向辑内第一篇，免得点上去没反应。
        point.href = point.children[0].href
    return point


def _article_nav(article: Article, deep: bool) -> NavPoint:
    href = article.href
    point = NavPoint(title=article.title, href=href)
    if deep:
        top = min((h.level for h in article.headings), default=2)
        point.children = [
            NavPoint(title=h.text, href=f"{href}#{h.anchor}")
            for h in article.headings
            if h.level == top
        ]
    return point


# ---------------------------------------------------------------- 构建


def build(
    config: dict,
    edition_name: str,
    *,
    deep_toc: bool = False,
    keep_stubs: bool = False,
    verbose: bool = False,
) -> Path:
    editions = config["editions"]
    if edition_name not in editions:
        raise SystemExit(f"未知的版本 {edition_name!r}，可选：{', '.join(editions)}")
    edition = editions[edition_name]
    volumes_by_id = {v["id"]: v for v in config["volumes"]}
    specs = []
    for vol_id in edition["volumes"]:
        if vol_id not in volumes_by_id:
            raise SystemExit(f"book.json 的 volumes 里没有 id 为 {vol_id!r} 的卷")
        specs.append(volumes_by_id[vol_id])

    collector = Collector(REPO_ROOT, skip_stubs=not keep_stubs)
    volumes = collector.collect(specs)
    volumes = [v for v in volumes if list(v.walk())]
    if not volumes:
        raise SystemExit("没有收集到任何文章，请检查 tools/book.json 的 sources 配置")

    renderer = Renderer(REPO_ROOT)
    renderer.assign_ids(volumes)
    renderer.render(volumes)

    raw_meta = dict(config["metadata"])
    now = build_timestamp()
    meta = Metadata(
        title=edition.get("title", raw_meta["title"]),
        subtitle=edition.get("subtitle", raw_meta.get("subtitle", "")),
        creator=raw_meta.get("creator", ""),
        language=raw_meta.get("language", "zh-CN"),
        identifier=edition.get("identifier", raw_meta["identifier"]),
        description=raw_meta.get("description", ""),
        publisher=raw_meta.get("publisher", ""),
        subjects=raw_meta.get("subjects", []),
        date=now.strftime("%Y-%m-%d"),
        modified=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    writer = epub.EpubWriter(meta)

    cover_name, cover_data = cover_mod.load(
        TOOLS_DIR / "assets", meta.title, meta.subtitle, meta.creator
    )
    cover_item = writer.add_item("cover-image", f"images/{cover_name}", cover_data)
    writer.set_cover_image(cover_item)
    cover_page = writer.add_page(
        "cover",
        "cover.xhtml",
        "封面",
        f'<div class="cover-figure"><img src="images/{esc(cover_name)}" alt="{esc(meta.title)}"/></div>',
        body_class="cover-page",
        properties="",
    )
    # 封面页必须排在最前，nav 才会被插到它后面。
    writer.items.remove(cover_page)
    writer.items.insert(0, cover_page)

    writer.add_item("style", "styles/main.css", (TOOLS_DIR / "assets" / "style.css").read_bytes())

    article_count = sum(len(list(v.walk())) for v in volumes)
    edition_note = edition.get("note", f"{meta.date} 自动编纂 · 共 {len(volumes)} 卷 {article_count} 篇")
    writer.add_page("titlepage", "text/000-title.xhtml", meta.title, title_page(meta, edition_note), body_class="title-page")

    for volume in volumes:
        writer.add_page(volume.vol_id + "-vol", volume.href, volume.title, volume_page(volume), body_class="volume-page")
        for article in volume.walk():
            writer.add_page(article.item_id, article.href, article.title, article_page(article))

    words = sum(len(a.doc.body) for v in volumes for a in v.walk())
    stats = {
        "卷数": len(volumes),
        "篇数": article_count,
        "正文规模": f"约 {words // 10000} 万字符",
        "编纂日期": meta.date,
        "版本": edition_name,
        "来源": "本仓库全部书稿、关键文章与札记",
    }
    writer.add_page("colophon", "text/999-colophon.xhtml", "编纂说明", colophon_page(meta, stats), body_class="colophon-page")

    writer.nav = build_nav(volumes, deep=deep_toc)

    out_path = REPO_ROOT / edition["output"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer.write(out_path, cover_href="cover.xhtml")

    _report(
        out_path,
        volumes,
        collector,
        renderer,
        edition.get("ignore", []),
        verbose=verbose,
    )
    return out_path


def _report(
    out_path: Path,
    volumes: list[Volume],
    collector: Collector,
    renderer: Renderer,
    ignore: list[str],
    *,
    verbose: bool,
) -> None:
    size = out_path.stat().st_size / 1024 / 1024
    print(f"\n已生成 {out_path.relative_to(REPO_ROOT)}  ({size:.1f} MB)")
    for volume in volumes:
        count = len(list(volume.walk()))
        print(f"  {volume.title}  {count} 篇")
    if collector.duplicates:
        print(f"\n去重 {len(collector.duplicates)} 篇：内容与已收录的篇目完全相同。")
        if verbose:
            for duplicate, original in collector.duplicates:
                print(
                    f"  - {duplicate.relative_to(REPO_ROOT)}"
                    f"  ≡  {original.relative_to(REPO_ROOT)}"
                )
    if collector.skipped_stubs:
        print(f"\n跳过 {len(collector.skipped_stubs)} 篇转址占位文件（正文已迁往别处）：")
        for path in collector.skipped_stubs:
            print(f"  - {path.relative_to(REPO_ROOT)}")
    for warning in collector.warnings:
        print(f"注意：{warning}")

    missing = [
        path
        for path in collector.unclaimed()
        if not any(pattern in path.relative_to(REPO_ROOT).as_posix() for pattern in ignore)
    ]
    if missing:
        print(f"\n以下 {len(missing)} 个文稿没有进入本书，可在 tools/book.json 里补上：")
        for path in missing:
            print(f"  - {path.relative_to(REPO_ROOT)}")
    else:
        print("\n覆盖检查：仓库中所有在编纂范围内的文稿都已收录。")

    if renderer.recovered_links:
        print(
            f"\n{len(renderer.recovered_links)} 处链接的路径已失效（改过名或挪过目录），"
            "按文件名找回了目标。"
        )
        if verbose:
            for name, dest, title in renderer.recovered_links:
                print(f"  - {name} → {dest}  ⇒ 《{title}》")
    if renderer.dropped_links:
        print(f"\n{len(renderer.dropped_links)} 处链接的目标不在本书内，已降级为纯文字。")
        if verbose:
            for name, dest in renderer.dropped_links:
                print(f"  - {name} → {dest}")


# ---------------------------------------------------------------- 校验


def run_epubcheck(path: Path) -> bool:
    """有 epubcheck 就跑一遍。没有则说明怎么装，不当作失败。"""
    candidates = [
        TOOLS_DIR / "epubcheck" / "epubcheck.jar",
        Path("/opt/epubcheck/epubcheck.jar"),
        Path.home() / "epubcheck" / "epubcheck.jar",
    ]
    if os.environ.get("EPUBCHECK_JAR"):
        candidates.insert(0, Path(os.environ["EPUBCHECK_JAR"]))
    jar = next((c for c in candidates if c.is_file()), None)
    if jar is None and shutil.which("epubcheck"):
        command = ["epubcheck", str(path)]
    elif jar is not None and shutil.which("java"):
        command = ["java", "-jar", str(jar), str(path)]
    else:
        print(
            "\n未找到 epubcheck，跳过校验。装法：从"
            " https://github.com/w3c/epubcheck/releases 下载后解压到 tools/epubcheck/，"
            "或用 EPUBCHECK_JAR 指向 jar 文件。"
        )
        return True
    print(f"\n校验 {path.name} …")
    result = subprocess.run(command, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    print(output or "(无输出)")
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--edition", default="main", help="要构建的版本，或 all 表示全部（默认 main）")
    parser.add_argument("--config", default=str(TOOLS_DIR / "book.json"))
    parser.add_argument("--check", action="store_true", help="构建后调用 epubcheck 校验")
    parser.add_argument("--deep-toc", action="store_true", help="目录里连每篇的一级小标题一起列出")
    parser.add_argument("--keep-stubs", action="store_true", help="保留「正文已迁走」的转址占位文件")
    parser.add_argument("-v", "--verbose", action="store_true", help="打印被降级的链接等细节")
    args = parser.parse_args()

    config = structure.load_config(Path(args.config))
    names = list(config["editions"]) if args.edition == "all" else [args.edition]

    ok = True
    for name in names:
        path = build(
            config,
            name,
            deep_toc=args.deep_toc,
            keep_stubs=args.keep_stubs,
            verbose=args.verbose,
        )
        if args.check:
            ok = run_epubcheck(path) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
