"""从 .docx 里抽出正文。

仓库里还有几篇只存在 Word 版本的文稿。docx 本质是个 zip，正文在
`word/document.xml`，用标准库的 zipfile ＋ ElementTree 就够读了——不为排版，
只为把文字、标题层级、粗体和列表带进书里。
"""

from __future__ import annotations

import re
import zipfile
from collections.abc import Callable
from xml.etree import ElementTree

from .mdconv import Document, Heading, Slugger, esc

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _text_of(node: ElementTree.Element) -> str:
    """一个 run 的可见文字，含制表符与换行。"""
    parts: list[str] = []
    for child in node.iter():
        tag = child.tag
        if tag == f"{W}t":
            parts.append(child.text or "")
        elif tag == f"{W}tab":
            parts.append("\t")
        elif tag in {f"{W}br", f"{W}cr"}:
            parts.append("\n")
    return "".join(parts)


def _run_html(run: ElementTree.Element) -> str:
    text = esc(_text_of(run)).replace("\n", "<br/>")
    if not text:
        return ""
    props = run.find(f"{W}rPr")
    if props is not None:
        if props.find(f"{W}b") is not None:
            text = f"<strong>{text}</strong>"
        if props.find(f"{W}i") is not None:
            text = f"<em>{text}</em>"
    return text


def _heading_level(style: str) -> int | None:
    m = re.fullmatch(r"(?:Heading|heading|标题)\s*([1-6])", style.strip())
    if m:
        return int(m.group(1))
    if style.strip() in {"Title", "标题"}:
        return 1
    return None


def convert(
    path,
    *,
    id_prefix: str = "sec",
    resolve_link: Callable[[str], str | None] | None = None,
    resolve_image: Callable[[str], str | None] | None = None,
) -> Document:
    del resolve_link, resolve_image  # docx 里的链接与图片不在本书范围内
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    body = root.find(f"{W}body")
    if body is None:
        return Document(body="", title=None, headings=[])

    slugger = Slugger(id_prefix)
    out: list[str] = []
    headings: list[Heading] = []
    title: str | None = None
    list_open = False

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            out.append("</ul>")
            list_open = False

    for para in body.iter(f"{W}p"):
        props = para.find(f"{W}pPr")
        style = ""
        if props is not None:
            style_node = props.find(f"{W}pStyle")
            if style_node is not None:
                style = style_node.get(f"{W}val") or ""
        inner = "".join(_run_html(run) for run in para.findall(f"{W}r")).strip()
        if not inner:
            continue
        plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", inner)).strip()
        level = _heading_level(style)
        if level is not None:
            close_list()
            if level == 1 and title is None:
                title = plain
                continue
            anchor = slugger.slug(plain)
            headings.append(Heading(level=level, text=plain, anchor=anchor))
            tag = f"h{max(level, 2)}"
            out.append(f'<{tag} id="{anchor}">{inner}</{tag}>')
            continue
        if props is not None and props.find(f"{W}numPr") is not None:
            if not list_open:
                out.append("<ul>")
                list_open = True
            out.append(f"<li>{inner}</li>")
            continue
        close_list()
        out.append(f"<p>{inner}</p>")
    close_list()
    return Document(body="\n".join(out), title=title, headings=headings)
