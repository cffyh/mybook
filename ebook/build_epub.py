#!/usr/bin/env python3
"""Build a collected EPUB from the factory's mature articles."""

from __future__ import annotations

import html as html_lib
import re
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import unquote

import markdown
from lxml import etree, html as lhtml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
EBOOK_DIR = Path(__file__).resolve().parent
OUT_PATH = EBOOK_DIR / "以小控大——工厂文集.epub"
COVER_PATH = EBOOK_DIR / "cover.png"
CSS_PATH = EBOOK_DIR / "stylesheet.css"
FONT_PATH = Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")

BOOK_TITLE = "以小控大"
BOOK_AUTHOR = "cffyh"
LANGUAGE = "zh-CN"
BOOK_ID = "urn:uuid:7c3e9b1a-4f2d-4a8e-9c11-a6d0e8f4b210"
PUBLISHER = "mybook"

SKIP_DIRS = {".git", "backup", "example", "ebook", "wiki"}
SKIP_SUFFIXES = {".docx", ".zip", ".xlsx", ".pdf", ".png", ".DS_Store"}
SKIP_NAMES = {
    "书稿定位与查漏策略.md",
    "贵的知识——专家访谈需求素材库.html",
    ".DS_Store",
}
SKIP_RELATIVE = {
    "书稿1/总目录与编纂说明.md",
    "书稿1/09-3-战略.md",
    "书稿 3/README.md",
    "书稿 3/下篇-世界为何回应/第六章_小与大_重构大纲.md",
    "书稿 5/概念与技能——碎片分析底稿.md",
    "书稿 5/总论/2.5 工程技术.md",
    "书稿 5/走向真实的交易/4 工程技术.html",
}

REDIRECT_MARKERS = ("请改读", "本篇已迁", "本章已迁", "正文不再维护")

SHANGPIAN_ORDER = [
    "以有限应对无限-人类把握世界的方式.md",
    "逻辑-世界的自在之理与思维的同构之路.md",
    "实事求是-科学理想世界和日常现实世界的共同底层原则.md",
    "逻辑和实事求是---态度和方法的合一.md",
    "从继承到实战-当输出开始反向调动输入.md",
    "模仿-创造最谦卑的序章.md",
    "从需求到战略-动机如何升华又如何落地.md",
    "战略一词——古无专名，今须小心.md",
    "中间层——接通上下，递归抵达远处.md",
    "从临场到战略——在不确定中为未来铺路.md",
    "根据地-为什么不关心又做不到.md",
    "亲历求真与精准判断的稀缺价值.md",
]

XIA_PIAN_ORDER = [
    "第六章_小与大_草稿_引子与乐章一.md",
    "第六章_小与大_草稿_乐章二.md",
    "第六章_小与大_草稿_乐章三.md",
    "第六章_小与大_草稿_乐章四.md",
    "第六章_小与大_草稿_乐章五与收尾.md",
]

BOOK4_ORDER = [
    "导论.html",
    "第一章_知识.html",
    "第二章_理性.html",
    "第四章_思维的单元与层级.html",
    "第五章_思维如何运作.html",
    "第六章_从学习到实战.html",
    "第三章_生命的拼图.html",
]

BOOK2_ORDER = [
    "全书思想骨架-一页大纲.md",
    "互动-人与世界关系的底层形状.md",
    "互动与表达——人与世界关系的内核.md",
    "实事求是——被说滥，却极少被说中.md",
    "实事求是——核心与外延（含出处）.md",
    "实事求是的具体化.md",
    "学习论——把世界的结构长进自己.md",
    "学习论-主线展开.md",
    "观察、捕捉现象与灵感.md",
]

BOOK5_ROOT_GROUPS = [
    (
        "表达与沟通",
        [
            "2如何说，比说什么更重要——表达是抽取，不是复印.md",
            "2.1想清楚之后——拆解、重建、再表达.md",
            "2.2为什么不能直来直去——沟通，是不确定里的迭代.md",
            "表达不为还原——面向目的与主体的行动.md",
            "表达的快解——重构既有洞察为各域共识语言，预写·背·用.md",
        ],
    ),
    (
        "学习与技能",
        [
            "庖丁解牛的三层——目无全牛·以无厚入有间·出神入化.md",
            "出神入化的祛魅——把化境讲成可判定的机制.md",
            "划小圈——局部何以体会整体.md",
            "技能的两手——在例子中学习与划小圈.md",
            "概念与技能——两种学习，同一种以小控大.md",
            "语言学习——听过的说，说过的读，读过的写.md",
            "跳出来认识本身——远看、近观、比较，与不跳出.md",
            "数学精神与科学方法.md",
        ],
    ),
    (
        "记忆与输出",
        [
            "背诵是输出——最简训练模型，与从复述到实时反应的三阶.md",
            "背诵的冷启动与迭代环——技巧不是捷径，是启动能.md",
            "记忆的两根轴——一钮·两标·四面·两肢.md",
            "输入是消化，输出是生成——内外有界，进来必须建联.md",
        ],
    ),
    (
        "根据地与合流",
        [
            "根据地的成立条件——李自成反例与三前提一时机.md",
            "毛泽东两段论述——实事求是·控制闭环·转化框架的合流.md",
        ],
    ),
]

JY_ROOT_ORDER = [
    "01-导论-其人与其书.md",
    "02-数学发现的本质-涨潮的海.md",
    "03-代数几何的革命.md",
    "04-思维方法论-相对观点与一般性.md",
    "05-孩童之心与创造力.md",
    "06-孤独冥想与工作方式.md",
    "07-决裂葬礼与启示.md",
]

MD = markdown.Markdown(
    extensions=["extra", "sane_lists", "toc"],
    output_format="xhtml",
)


@dataclass
class Chapter:
    path: Path | None
    title: str
    kind: str = "article"  # article | generated | volume
    html: str = ""
    filename: str = ""
    item_id: str = ""


@dataclass
class Volume:
    key: str
    title: str
    blurb: str
    chapters: list[Chapter] = field(default_factory=list)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_skipped(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return True
    if path.name in SKIP_NAMES or path.suffix.lower() in SKIP_SUFFIXES:
        return True
    if rel(path) in SKIP_RELATIVE:
        return True
    return False


def discover_sources() -> list[Path]:
    files: list[Path] = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or is_skipped(p):
            continue
        if p.suffix.lower() in {".md", ".html"}:
            files.append(p)
    return files


def looks_like_redirect(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    body = re.sub(r"\[[^\]]*\]\([^)]*\)", "", text)
    body = re.sub(r"^#.*$", "", body, flags=re.M)
    compact = re.sub(r"\s+", "", body)
    if len(compact) < 80 and any(m in text for m in REDIRECT_MARKERS):
        return True
    if any(m in text for m in REDIRECT_MARKERS) and len(text) < 600:
        return True
    return False


def ordered_existing(directory: Path, names: list[str]) -> list[Path]:
    out = []
    for name in names:
        p = directory / name
        if p.exists():
            out.append(p)
    return out


def numeric_key(path: Path) -> tuple:
    name = path.stem
    m = re.match(r"^(\d+(?:[.\-]\d+)*)", name)
    if not m:
        return (1, (9999,), name)
    parts = tuple(int(x) for x in re.split(r"[.\-]", m.group(1)) if x.isdigit())
    return (0, parts, name)


def first_heading(text: str) -> str | None:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", text, flags=re.S | re.I)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1))
    m = re.search(r"^#\s+(.+)$", text, flags=re.M)
    if m:
        return m.group(1).strip()
    return None


def clean_title(raw: str, fallback: str) -> str:
    title = html_lib.unescape(raw or "")
    title = re.sub(r"\s+", " ", title).strip()
    title = title.replace("　", "")
    for prefix in ("已迁",):
        if title.endswith(f"（{prefix}）") or title.endswith(f"({prefix})"):
            title = re.sub(r"[（(]" + prefix + r"[）)]", "", title).strip()
    return title or fallback


def title_from_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    heading = first_heading(text)
    fallback = path.stem
    fallback = re.sub(r"^\d+(?:[.\-]\d+)*\s*", "", fallback)
    fallback = re.sub(r"_独立成文|_重构稿|_草稿", "", fallback)
    return clean_title(heading or fallback, fallback)


def protect_math(text: str) -> tuple[str, list[tuple[str, str]]]:
    slots: list[tuple[str, str]] = []

    def save(kind: str, body: str) -> str:
        slots.append((kind, body))
        return f"@@MATH{len(slots) - 1}@@"

    text = re.sub(
        r"\$\$(.+?)\$\$",
        lambda m: save("display", m.group(1)),
        text,
        flags=re.S,
    )
    text = re.sub(
        r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)",
        lambda m: save("inline", m.group(1)),
        text,
        flags=re.S,
    )
    return text, slots


def restore_math(html: str, slots: list[tuple[str, str]]) -> str:
    def repl(m: re.Match) -> str:
        kind, body = slots[int(m.group(1))]
        escaped = html_lib.escape(body)
        tag = "span"
        cls = "math display" if kind == "display" else "math"
        return f'<{tag} class="{cls}">{escaped}</{tag}>'

    return re.sub(r"@@MATH(\d+)@@", repl, html)


def md_to_html(text: str) -> str:
    if text.startswith("---"):
        text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
    protected, slots = protect_math(text)
    MD.reset()
    html = MD.convert(protected)
    return restore_math(html, slots)


def html_file_to_fragment(text: str) -> str:
    doc = lhtml.fromstring(text)
    body = doc.xpath("//body")
    node = body[0] if body else doc
    for bad in node.xpath(".//script|.//style"):
        parent = bad.getparent()
        if parent is not None:
            parent.remove(bad)
    parts = []
    for child in node:
        parts.append(
            etree.tostring(child, method="xml", encoding="unicode", with_tail=True)
        )
    if node.text and node.text.strip():
        parts.insert(0, html_lib.escape(node.text))
    return "".join(parts)


def source_to_fragment(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".html":
        return html_file_to_fragment(text)
    return md_to_html(text)


def fragment_to_xml(fragment: str) -> etree._Element:
    wrapped = (
        f'<div xmlns="{XHTML_NS}" xmlns:epub="{EPUB_NS}">{fragment}</div>'
    )
    try:
        return etree.fromstring(wrapped.encode("utf-8"))
    except etree.XMLSyntaxError:
        doc = lhtml.fromstring(f"<div>{fragment}</div>")
        xml = etree.tostring(doc, method="xml", encoding="unicode")
        xml = xml.replace(
            "<div>",
            f'<div xmlns="{XHTML_NS}" xmlns:epub="{EPUB_NS}">',
            1,
        )
        return etree.fromstring(xml.encode("utf-8"))


XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"
H_NS = {"h": XHTML_NS}


def _format_href(dest: str, frag: str, link_kind: str) -> str:
    if link_kind == "hash":
        dest = dest.replace(".xhtml", "").replace(".html", "")
        href = "#/" + dest.lstrip("#/")
        if frag:
            href += "/" + frag.lstrip("#")
        return href
    if frag:
        return dest + "#" + frag
    return dest


def rewrite_links(
    root_el: etree._Element,
    src: Path,
    path_map: dict[str, str],
    dir_map: dict[str, str],
    link_kind: str = "file",
) -> None:
    for a in root_el.xpath(".//h:a", namespaces=H_NS):
        href = a.get("href")
        if not href:
            continue
        href = unquote(html_lib.unescape(href)).strip()
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part, _, frag = href.partition("#")
        if not path_part:
            continue
        try:
            candidates = [
                (src.parent / path_part).resolve(),
                (ROOT / path_part).resolve(),
            ]
        except OSError:
            candidates = []
        target_file = None
        target_dir = None
        for cand in candidates:
            if str(cand) in path_map:
                target_file = cand
                break
            if str(cand) in dir_map:
                target_dir = cand
        if target_file is not None:
            new = _format_href(path_map[str(target_file)], frag, link_kind)
            a.set("href", new)
        elif target_dir is not None:
            a.set("href", _format_href(dir_map[str(target_dir)], "", link_kind))
        elif path_part.endswith((".md", ".html", ".htm", ".docx")) or path_part.endswith("/"):
            a.attrib.pop("href", None)
            a.tag = f"{{{XHTML_NS}}}span"
            cls = a.get("class")
            a.set("class", (cls + " internal-ref").strip() if cls else "internal-ref")


def inner_html(root_el: etree._Element) -> str:
    parts: list[str] = []
    if root_el.text:
        parts.append(html_lib.escape(root_el.text))
    for child in root_el:
        parts.append(
            etree.tostring(child, method="html", encoding="unicode", with_tail=True)
        )
    html = "".join(parts)
    html = re.sub(r'\sxmlns(?::[a-z]+)?="[^"]*"', "", html)
    return html


def serialize_xhtml(html_el: etree._Element) -> str:
    xml = etree.tostring(
        html_el,
        encoding="unicode",
        method="xml",
        pretty_print=True,
    )
    return '<?xml version="1.0" encoding="utf-8"?>\n' + xml


def xhtml_document(
    title: str, body_inner: str, body_class: str = "", body_epub_type: str = ""
) -> str:
    html = etree.Element(
        f"{{{XHTML_NS}}}html",
        nsmap={None: XHTML_NS, "epub": EPUB_NS},
    )
    html.set("{http://www.w3.org/XML/1998/namespace}lang", LANGUAGE)
    html.set("lang", LANGUAGE)
    head = etree.SubElement(html, f"{{{XHTML_NS}}}head")
    title_el = etree.SubElement(head, f"{{{XHTML_NS}}}title")
    title_el.text = title
    link = etree.SubElement(head, f"{{{XHTML_NS}}}link")
    link.set("rel", "stylesheet")
    link.set("type", "text/css")
    link.set("href", "../styles/stylesheet.css")
    body = etree.SubElement(html, f"{{{XHTML_NS}}}body")
    if body_class:
        body.set("class", body_class)
    if body_epub_type:
        body.set(f"{{{EPUB_NS}}}type", body_epub_type)
    fragment = fragment_to_xml(body_inner)
    if fragment.text:
        body.text = (body.text or "") + fragment.text
    for child in list(fragment):
        body.append(child)
    return serialize_xhtml(html)


PREFACE_MD = """# 前言

这一本电子书，把工厂里已经写成文章的稿子收成一部可翻的书。

文章数量多、题材跨度大——从量子与信息、控制论与目的论，到课堂、谈判、根据地、宁德时代。骨架只有一句：

**往下追到世界的最底层与人的思维底层；往上接到人如何在现实里变得厉害；两端之间，始终是同一套最底层、最通用的机制在不同域显影。**

不是百科，不是领域技巧合集。杂是表象，通用是本体。

## 这部文集怎么读

工厂里其实有三种切法，不是三套世界观：

1. **知识论**（卷一）：人如何认识、思考、安顿。文风最平实，适合当入口。
2. **理性与实干**（卷二）：渺小的人凭什么在宏大世界里有效存在、甚至创造。上篇讲人怎么做，接缝是实践，下篇讲世界为何回应。
3. **转化框架**（卷三）：世界以结构/关系为本体，靠转化演进。骨架最清楚，篇幅最短。
4. **走向真实的交易**（卷四）：当前主写区。把通用机制接到立足、成交、变强，并收总论、点、演绎与着地篇。
5. **认识与行动**（卷五）：把原始笔记熔成「认识→行动」十部草稿，求全，不是文风基准。
6. **关键文章 / 札记**（卷六、卷七）：进不了某书也不丢的单篇，以及拆书与压轴案例。

后卷与前卷会有主题回响。同一条机制被不同角度切过，不是重复粘贴目录。

## 四条路径

- **先立合题**：卷一可略读；进卷二《以有限应对无限》→《逻辑》→《实事求是》→《实践》→《小与大》乐章三、四。需要尖刀时进卷四的目标—差距—控制与「点」。
- **先立思维与学习**：卷一导论→知识→理性→思维两章→从学习到实战；旁路用卷四总论《知识体系》与知识簇。
- **直接走向交易**：卷四《控制论的奠基》→需求、目标与差距→《点是面向目标的投影》→生存空间；压轴对照札记《宁德时代曾毓群》。
- **从小与大走进闭环**：根目录那篇《从小与大到以小控大》在卷四着地部分。

## 关于版本

电子书由仓库文稿自动编成。内部工作流、原始互链笔记、访谈素材库不进书。转址残篇（正文已迁走的）也不进书，以免目录里出现空壳。

编成日期：{today}。
"""


def collect_volumes(sources: list[Path]) -> tuple[list[Volume], list[Path]]:
    remaining = {p.resolve() for p in sources}

    def take(path: Path) -> Path | None:
        rp = path.resolve()
        if rp in remaining:
            remaining.remove(rp)
            return path
        return None

    def take_many(paths: list[Path]) -> list[Chapter]:
        chapters = []
        for p in paths:
            got = take(p)
            if got is None:
                continue
            if looks_like_redirect(got):
                continue
            chapters.append(Chapter(path=got, title=title_from_file(got)))
        return chapters

    volumes: list[Volume] = []

    volumes.append(
        Volume(
            "front",
            "卷首",
            "这部文集的读法、分卷与路径。",
            [
                Chapter(path=None, title="前言", kind="generated", html=""),
            ],
        )
    )
    zonggang = ROOT / "全书总纲.md"
    if zonggang.exists():
        volumes[0].chapters.append(
            Chapter(path=zonggang, title=title_from_file(zonggang))
        )
        take(zonggang)

    volumes.append(
        Volume(
            "book4",
            "卷一　知识论",
            "人如何认识、思考、生活，以及如何与自然和他人相处。由内而外：知识与理性，思维，生命的拼图。文风平实，是工厂里最接近完书的一册。",
            take_many(ordered_existing(ROOT / "书稿 4", BOOK4_ORDER)),
        )
    )

    shang = ordered_existing(
        ROOT / "书稿 5" / "走向真实的交易" / "上篇-人怎么做",
        SHANGPIAN_ORDER,
    )
    jiefeng = ordered_existing(
        ROOT / "书稿 3" / "接缝-实践",
        ["实践-渺小与宏大之间的纽带_独立成文.md"],
    )
    xia = ordered_existing(ROOT / "书稿 3" / "下篇-世界为何回应", XIA_PIAN_ORDER)
    volumes.append(
        Volume(
            "book3",
            "卷二　理性与实干",
            "渺小的人，凭什么能在宏大的世界里有效地存在，甚至创造？先读上篇「人怎么做」，再读接缝《实践》，最后进入《小与大》。上篇文稿现收在书稿 5，下篇与接缝在书稿 3。",
            take_many(shang + jiefeng + xia),
        )
    )

    volumes.append(
        Volume(
            "book2",
            "卷三　转化框架",
            "世界以结构/关系为本体，靠转化演进；人据此认识与实践。三母题贯穿：系统—结构—作用力、转化、相似相异。六卷意向尚未铺满，这里收已经写成的专论。",
            take_many(ordered_existing(ROOT / "书稿2", BOOK2_ORDER)),
        )
    )

    zonglun_dir = ROOT / "书稿 5" / "总论"
    zonglun_files = sorted(
        [p for p in zonglun_dir.glob("*") if p.suffix.lower() in {".md", ".html"}],
        key=numeric_key,
    )
    dizhe = [
        ROOT / "从小与大到以小控大——底层视角如何闭环.md",
        ROOT / "工程技术——着地、积累、外衣与内核.md",
    ]
    trade_dir = ROOT / "书稿 5" / "走向真实的交易"
    trade_files = []
    for p in sorted(trade_dir.glob("*"), key=numeric_key):
        if p.is_file() and p.suffix.lower() in {".md", ".html"}:
            trade_files.append(p)
    point_dir = ROOT / "书稿 5" / "点"
    point_files = sorted(point_dir.glob("*"), key=lambda p: p.name)
    yan_dir = ROOT / "书稿 5" / "演绎"
    yan_files = [
        yan_dir / "演绎三部曲·上篇——概念的层次演绎.md",
        yan_dir / "演绎三部曲·中篇——一个矛盾生一串需求.md",
        yan_dir / "演绎三部曲·下篇——把骨演绎成尖刀.md",
    ]
    zhi_dir = ROOT / "书稿 5" / "知识"
    zhi_files = sorted(zhi_dir.glob("*.md"), key=numeric_key)
    extra_root: list[Path] = []
    for _group, names in BOOK5_ROOT_GROUPS:
        extra_root.extend(ordered_existing(ROOT / "书稿 5", names))

    volumes.append(
        Volume(
            "book5",
            "卷四　走向真实的交易",
            "当前主写区。总论立门：人安身靠两极——理性照清世界，互动嵌入真实。随后是着地两篇、生存与交易、点与演绎、学习与表达。把通用机制写成可判定、可落地的尖刀。",
            take_many(
                zonglun_files
                + dizhe
                + trade_files
                + list(point_files)
                + yan_files
                + zhi_files
                + extra_root
            ),
        )
    )

    book1 = sorted(
        [p for p in (ROOT / "书稿1").glob("*.md")],
        key=lambda p: p.name,
    )
    volumes.append(
        Volume(
            "book1",
            "卷五　认识与行动",
            "把原始互链笔记按「认识—行动」叙事弧熔成十部。求全对照，文风不如卷一平实，却是查漏与通读世界图景的全集。战略章已迁至卷二，此处不收空壳。",
            take_many(book1),
        )
    )

    key_dir = ROOT / "关键文章"
    key_chapters: list[Path] = []
    root_key = sorted(
        [p for p in key_dir.glob("*.md")],
        key=lambda p: p.name,
    )
    key_chapters.extend(root_key)
    logic_dir = key_dir / "逻辑"
    key_chapters.extend(sorted(logic_dir.glob("*.md"), key=lambda p: p.name))
    subj = key_dir / "学科"
    key_chapters.append(subj / "数学精神与科学方法·总纲完整版.md")
    key_chapters.append(subj / "数学精神与科学方法.md")
    math_dir = subj / "数学精神"
    key_chapters.extend(
        ordered_existing(
            math_dir,
            [
                "article1.md",
                "article2.md",
                "article3.md",
                "article4.md",
                "article5.md",
                "物理与数学.md",
                "数学与其他学科.md",
                "数学思想如何在工业界算法实践中产生质的飞跃.md",
            ],
        )
    )
    groth = subj / "格罗滕迪克-收获与播种"
    key_chapters.append(groth / "README.md")
    key_chapters.extend(ordered_existing(groth, JY_ROOT_ORDER))
    for extra in sorted(subj.glob("*.md"), key=lambda p: p.name):
        if extra.name not in {
            "数学精神与科学方法·总纲完整版.md",
            "数学精神与科学方法.md",
        }:
            key_chapters.append(extra)
    volumes.append(
        Volume(
            "key",
            "卷六　关键文章",
            "抽出来的重要单篇。进不了某一本成品书，也不丢掉。学科眼镜、逻辑、历史镜子与若干独立判断都在这里。",
            take_many(key_chapters),
        )
    )

    notes = sorted((ROOT / "札记").glob("*.md"), key=lambda p: p.name)
    volumes.append(
        Volume(
            "notes",
            "卷七　札记",
            "全书拆解与综合案例。控制论、系统工程、学习之道、技术的本质；宁德时代、ServiceTitan；胶球、OSR 与量子比特海。素材与压轴例，不是文风基准。",
            take_many(notes),
        )
    )

    leftover_paths = sorted(remaining, key=lambda p: rel(p))
    leftover_ok = []
    for p in leftover_paths:
        if looks_like_redirect(p):
            remaining.discard(p)
            continue
        leftover_ok.append(p)
    appendix_files = leftover_ok
    volumes.append(
        Volume(
            "appendix",
            "附录",
            "素材与未被前七卷点名、但仍是成文的篇目。",
            take_many(appendix_files),
        )
    )

    volumes.append(
        Volume(
            "end",
            "卷末",
            "",
            [Chapter(path=None, title="版权与编纂说明", kind="generated")],
        )
    )
    return volumes, leftover_ok


def make_cover() -> None:
    w, h = 1600, 2560
    img = Image.new("RGB", (w, h), "#1c1915")
    draw = ImageDraw.Draw(img)
    font_title = ImageFont.truetype(str(FONT_PATH), 168)
    font_sub = ImageFont.truetype(str(FONT_PATH), 42)
    font_small = ImageFont.truetype(str(FONT_PATH), 36)

    draw.rectangle([90, 90, w - 90, h - 90], outline="#c4b89a", width=3)
    draw.rectangle([110, 110, w - 110, h - 110], outline="#7a7263", width=1)

    title = BOOK_TITLE
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) / 2, 860), title, font=font_title, fill="#f4efe4")

    draw.line([(w * 0.35, 1120), (w * 0.65, 1120)], fill="#c4b89a", width=2)

    sub = BOOK_SUBTITLE
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    sw = bbox[2] - bbox[0]
    draw.text(((w - sw) / 2, 1180), sub, font=font_sub, fill="#d9d1c0")

    author = BOOK_AUTHOR
    bbox = draw.textbbox((0, 0), author, font=font_small)
    aw = bbox[2] - bbox[0]
    draw.text(((w - aw) / 2, 2100), author, font=font_small, fill="#a39886")
    year = "二〇二六"
    bbox = draw.textbbox((0, 0), year, font=font_small)
    yw = bbox[2] - bbox[0]
    draw.text(((w - yw) / 2, 2180), year, font=font_small, fill="#8a8a7a")
    img.save(COVER_PATH, "PNG")


def cover_xhtml() -> str:
    inner = """
<div class="cover-page">
<h1 class="cover-title">以小控大</h1>
<p class="cover-subtitle">工厂文集：从世界底层到人如何变强</p>
<hr class="cover-rule"/>
<p class="cover-meta">cffyh</p>
</div>
"""
    return xhtml_document("封面", inner, "cover", "cover")


def colophon_html() -> str:
    today = date.today().isoformat()
    inner = f"""
<div class="colophon">
<h1>版权与编纂说明</h1>
<p>《{BOOK_TITLE}》</p>
<p>{BOOK_SUBTITLE}</p>
<p>作者　{BOOK_AUTHOR}</p>
<p>来源仓库　github.com/cffyh/mybook</p>
<p>电子书由文稿自动编成　{today}</p>
<p>收录书稿 4、理性与实干、转化框架、书稿 5、认识与行动十部、关键文章与札记。</p>
<p>不收录 backup 原始笔记、访谈素材库、转址残篇与作者工作流文件。</p>
</div>
"""
    return inner


def assign_filenames(volumes: list[Volume]) -> None:
    n = 0
    for vol in volumes:
        n += 1
        vol_name = f"vol-{n:02d}.xhtml"
        vol_id = f"vol-{n:02d}"
        # volume title page is injected later; chapters get files
        for ch in vol.chapters:
            n += 1
            ch.filename = f"ch-{n:03d}.xhtml"
            ch.item_id = f"ch-{n:03d}"
        # store volume page names on first chapter via side channel
        vol.chapters.insert(
            0,
            Chapter(
                path=None,
                title=vol.title,
                kind="volume",
                filename=vol_name,
                item_id=vol_id,
            ),
        )


def volume_page_html(vol: Volume) -> str:
    blurb = html_lib.escape(vol.blurb) if vol.blurb else ""
    blurb_p = f'<p class="volume-blurb">{blurb}</p>' if blurb else ""
    inner = f"""
<div class="volume-page">
<p class="volume-kicker">工厂文集</p>
<h1 class="volume-title">{html_lib.escape(vol.title)}</h1>
{blurb_p}
</div>
"""
    return inner


def build_nav(volumes: list[Volume]) -> str:
    items = [
        '<li><a href="cover.xhtml">封面</a></li>',
    ]
    first_body = None
    for vol in volumes:
        vol_page = next(ch for ch in vol.chapters if ch.kind == "volume")
        if first_body is None:
            first_body = vol_page.filename
        kids = []
        for ch in vol.chapters:
            if ch.kind == "volume":
                continue
            kids.append(
                f'<li><a href="{ch.filename}">{html_lib.escape(ch.title)}</a></li>'
            )
        inner = ""
        if kids:
            inner = "<ol>\n" + "\n".join(kids) + "\n</ol>"
        items.append(
            f'<li><a href="{vol_page.filename}">{html_lib.escape(vol.title)}</a>{inner}</li>'
        )
    ol = "<ol>\n" + "\n".join(items) + "\n</ol>"
    landmarks = f"""
<nav epub:type="landmarks" id="landmarks" hidden="hidden">
<ol>
<li><a epub:type="cover" href="cover.xhtml">封面</a></li>
<li><a epub:type="toc" href="nav.xhtml">目录</a></li>
<li><a epub:type="bodymatter" href="{first_body or 'cover.xhtml'}">正文</a></li>
</ol>
</nav>
"""
    inner = f'<nav epub:type="toc" id="toc">\n<h1>目录</h1>\n{ol}\n</nav>\n{landmarks}'
    return xhtml_document("目录", inner)


def build_opf(volumes: list[Volume], chapter_files: list[tuple[str, str]]) -> str:
    today = date.today().isoformat()
    manifest = [
        '<item id="nav" href="text/nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="css" href="styles/stylesheet.css" media-type="text/css"/>',
        '<item id="cover-image" href="images/cover.png" media-type="image/png" properties="cover-image"/>',
        '<item id="cover" href="text/cover.xhtml" media-type="application/xhtml+xml"/>',
    ]
    spine = ['<itemref idref="cover"/>', '<itemref idref="nav"/>']
    for item_id, href in chapter_files:
        manifest.append(
            f'<item id="{item_id}" href="{href}" media-type="application/xhtml+xml"/>'
        )
        spine.append(f'<itemref idref="{item_id}"/>')
    manifest_xml = "\n    ".join(manifest)
    spine_xml = "\n    ".join(spine)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="pub-id" version="3.0" xml:lang="{LANGUAGE}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">{BOOK_ID}</dc:identifier>
    <dc:title>{html_lib.escape(BOOK_TITLE)}——{html_lib.escape(BOOK_SUBTITLE)}</dc:title>
    <dc:creator>{html_lib.escape(BOOK_AUTHOR)}</dc:creator>
    <dc:language>{LANGUAGE}</dc:language>
    <dc:publisher>{html_lib.escape(PUBLISHER)}</dc:publisher>
    <dc:date>{today}</dc:date>
    <dc:description>{html_lib.escape(BOOK_SUBTITLE)}。据 cffyh/mybook 工厂文稿自动编成的 EPUB 文集。</dc:description>
    <meta property="dcterms:modified">{today}T00:00:00Z</meta>
    <meta name="cover" content="cover-image"/>
  </metadata>
  <manifest>
    {manifest_xml}
  </manifest>
  <spine>
    {spine_xml}
  </spine>
</package>
"""


CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def render_chapter(
    ch: Chapter, path_map: dict[str, str], dir_map: dict[str, str], today: str
) -> str:
    if ch.kind == "volume":
        return ""
    if ch.kind == "generated" and ch.title == "前言":
        html = md_to_html(PREFACE_MD.format(today=today))
        return xhtml_document(ch.title, html)
    if ch.kind == "generated" and ch.title == "版权与编纂说明":
        return xhtml_document(ch.title, colophon_html())
    assert ch.path is not None
    fragment = source_to_fragment(ch.path)
    doc = xhtml_document(ch.title, fragment)
    html_el = etree.fromstring(doc.encode("utf-8"))
    rewrite_links(html_el, ch.path, path_map, dir_map)
    return serialize_xhtml(html_el)


def write_epub(volumes: list[Volume]) -> None:
    today = date.today().isoformat()
    css = CSS_PATH.read_text(encoding="utf-8")
    make_cover()

    path_map: dict[str, str] = {}
    dir_map: dict[str, str] = {}
    vol_page_by_key: dict[str, str] = {}
    for vol in volumes:
        vol_page = next(ch for ch in vol.chapters if ch.kind == "volume")
        vol_page_by_key[vol.key] = vol_page.filename
        for ch in vol.chapters:
            if ch.path is not None:
                path_map[str(ch.path.resolve())] = ch.filename
                dir_map.setdefault(str(ch.path.parent.resolve()), ch.filename)
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

    files: dict[str, bytes] = {}
    files["OEBPS/styles/stylesheet.css"] = css.encode("utf-8")
    files["OEBPS/images/cover.png"] = COVER_PATH.read_bytes()
    files["OEBPS/text/cover.xhtml"] = cover_xhtml().encode("utf-8")
    chapter_files: list[tuple[str, str]] = []
    files["OEBPS/text/nav.xhtml"] = build_nav(volumes).encode("utf-8")
    for vol in volumes:
        for ch in vol.chapters:
            if ch.kind == "volume":
                body = volume_page_html(vol)
                doc = xhtml_document(ch.title, body, "cover")
            else:
                doc = render_chapter(ch, path_map, dir_map, today)
            files[f"OEBPS/text/{ch.filename}"] = doc.encode("utf-8")
            chapter_files.append((ch.item_id, f"text/{ch.filename}"))

    files["OEBPS/content.opf"] = build_opf(volumes, chapter_files).encode("utf-8")
    files["META-INF/container.xml"] = CONTAINER_XML.encode("utf-8")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_PATH, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, data in files.items():
            zf.writestr(
                name, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )


def main() -> None:
    sources = discover_sources()
    volumes, leftovers = collect_volumes(sources)
    assign_filenames(volumes)
    article_count = sum(
        1
        for vol in volumes
        for ch in vol.chapters
        if ch.kind in {"article", "generated"} and ch.title not in {"封面"}
    )
    print(f"sources discovered: {len(sources)}")
    print(f"volumes: {len(volumes)}")
    for vol in volumes:
        arts = [c for c in vol.chapters if c.kind != "volume"]
        print(f"  {vol.title}: {len(arts)} 篇")
    if leftovers:
        print("appendix leftovers:")
        for p in leftovers:
            print("   ", rel(p))
    write_epub(volumes)
    size = OUT_PATH.stat().st_size
    print(f"wrote {OUT_PATH} ({size} bytes), chapters≈{article_count}")


if __name__ == "__main__":
    main()
