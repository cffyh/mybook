"""HTML 成稿 → EPUB 可用的 XHTML。

`书稿 4/` 全部、以及另外几篇是直接写成 HTML 的。这些文件本身很干净（语义标签
＋一段内嵌 CSS），所以这里只做三件事：丢掉 head 与内嵌样式（统一由书的样式表
接管）、把标签规整成 XHTML、顺手把标题收集出来做目录。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from html.parser import HTMLParser

from .mdconv import Document, Heading, Slugger, esc

VOID = {"br", "hr", "img", "input", "meta", "link", "col", "area", "base", "source", "wbr"}

# EPUB 里放心用的标签。列表外的标签会被降级成 div/span，内容不丢。
ALLOWED = {
    "p", "div", "span", "a", "em", "strong", "b", "i", "u", "s", "del", "ins",
    "small", "sub", "sup", "code", "pre", "kbd", "samp", "var", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "dl", "dt", "dd",
    "blockquote", "figure", "figcaption", "img", "table", "thead", "tbody",
    "tfoot", "tr", "th", "td", "caption", "colgroup", "col", "section",
    "article", "aside", "nav", "header", "footer", "cite", "q", "abbr",
    "ruby", "rt", "rp", "mark", "time",
}
INLINE_FALLBACK = {"font", "big", "tt", "acronym", "center"}
DROP_CONTENT = {"script", "style", "head", "title", "template", "noscript"}

# 只保留有意义的属性；行内 style 与事件属性一概不要。
KEEP_ATTRS = {"href", "src", "alt", "title", "id", "class", "colspan", "rowspan", "lang", "datetime"}
BLOCK_TAGS = {
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table",
    "thead", "tbody", "tfoot", "tr", "blockquote", "section", "article", "nav",
    "header", "footer", "figure", "figcaption", "pre", "dl", "dt", "dd", "hr",
}


class _Converter(HTMLParser):
    def __init__(
        self,
        slugger: Slugger,
        resolve_link: Callable[[str], str | None] | None,
        resolve_image: Callable[[str], str | None] | None,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self.slugger = slugger
        self.resolve_link = resolve_link
        self.resolve_image = resolve_image
        self.out: list[str] = []
        self.headings: list[Heading] = []
        self.title: str | None = None
        self._in_body = False
        self._skip_depth = 0
        self._stack: list[str] = []
        self._heading: list[str] | None = None
        self._heading_level = 0
        self._heading_id: str | None = None
        self._first_h1_captured = False
        self._dropped_first_h1 = False

    # ---------- 辅助 ----------

    def _emit(self, chunk: str) -> None:
        if self._heading is not None:
            self._heading.append(chunk)
        else:
            self.out.append(chunk)

    def _attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        parts = []
        for name, value in attrs:
            name = name.lower()
            if name not in KEEP_ATTRS or value is None:
                continue
            if name == "href":
                value = self._href(value)
                if value is None:
                    continue
            elif name == "src" and tag == "img":
                resolved = self.resolve_image(value) if self.resolve_image else value
                if resolved is None:
                    continue
                value = resolved
            parts.append(f'{name}="{esc(value)}"')
        if tag == "img" and not any(p.startswith("alt=") for p in parts):
            parts.append('alt=""')
        return (" " + " ".join(parts)) if parts else ""

    def _href(self, value: str) -> str | None:
        value = value.strip()
        if value.startswith("#") or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value):
            return value
        if self.resolve_link is None:
            return value
        return self.resolve_link(value)

    # ---------- HTMLParser 回调 ----------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._skip_depth:
            if tag in DROP_CONTENT:
                self._skip_depth += 1
            return
        if tag in DROP_CONTENT:
            self._skip_depth = 1
            return
        if tag == "body":
            self._in_body = True
            return
        if tag in {"html", "meta", "link", "base"}:
            return
        if not self._in_body and tag not in ALLOWED:
            return

        if re.fullmatch(r"h[1-6]", tag):
            self._heading = []
            self._heading_level = int(tag[1])
            # 原稿标题上的 id 可能被同文件的目录锚点引用，必须留住。
            self._heading_id = next(
                (v for k, v in attrs if k.lower() == "id" and v), None
            )
            if self._heading_level == 1 and not self._first_h1_captured:
                # 篇名交给章页抬头渲染，正文里不重复。
                self._first_h1_captured = True
            self._stack.append(tag)
            return

        out_tag = tag if tag in ALLOWED else ("div" if tag in {"center"} else "span")
        if tag in INLINE_FALLBACK and tag != "center":
            out_tag = "span"
        rendered = self._attrs(out_tag, attrs)
        if out_tag in VOID:
            self._emit(f"<{out_tag}{rendered}/>")
            return
        self._stack.append(out_tag)
        self._emit(f"<{out_tag}{rendered}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._skip_depth or tag in DROP_CONTENT:
            return
        out_tag = tag if tag in ALLOWED else "span"
        rendered = self._attrs(out_tag, attrs)
        self._emit(f"<{out_tag}{rendered}/>" if out_tag in VOID else f"<{out_tag}{rendered}></{out_tag}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._skip_depth:
            if tag in DROP_CONTENT:
                self._skip_depth -= 1
            return
        if tag == "body":
            self._in_body = False
            return
        if self._heading is not None and re.fullmatch(r"h[1-6]", tag):
            self._close_heading()
            return
        out_tag = tag if tag in ALLOWED else "span"
        if out_tag in VOID:
            return
        if out_tag in self._stack:
            while self._stack:
                top = self._stack.pop()
                self._emit(f"</{top}>")
                if top == out_tag:
                    break

    def _close_heading(self) -> None:
        inner = "".join(self._heading or []).strip()
        level = self._heading_level
        source_id = self._heading_id
        self._heading = None
        self._heading_id = None
        if self._stack and re.fullmatch(r"h[1-6]", self._stack[-1]):
            self._stack.pop()
        plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", inner)).strip()
        if level == 1 and not self._dropped_first_h1:
            self._dropped_first_h1 = True
            if self.title is None:
                self.title = plain
            return
        # 与 Markdown 一致：篇名占了 h1，文中再出现的 h1 下沉到 h2。
        tag = f"h{max(level, 2)}"
        if source_id:
            anchor = source_id
            self.slugger.used.add(anchor)
        else:
            anchor = self.slugger.slug(plain)
        self.headings.append(Heading(level=level, text=plain, anchor=anchor))
        self.out.append(f'<{tag} id="{anchor}">{inner}</{tag}>')

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not data:
            return
        if not self._in_body and not self._stack and not data.strip():
            return
        self._emit(esc(data))

    def handle_comment(self, data: str) -> None:  # 注释一律丢掉
        return

    def close_all(self) -> None:
        while self._stack:
            self._emit(f"</{self._stack.pop()}>")


def convert(
    source: str,
    *,
    id_prefix: str = "sec",
    resolve_link: Callable[[str], str | None] | None = None,
    resolve_image: Callable[[str], str | None] | None = None,
) -> Document:
    doc_title = None
    m = re.search(r"<title[^>]*>(.*?)</title>", source, re.S | re.I)
    if m:
        doc_title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()

    parser = _Converter(Slugger(id_prefix), resolve_link, resolve_image)
    parser.feed(source)
    parser.close()
    parser.close_all()
    body = _tidy("".join(parser.out))
    return Document(body=body, title=parser.title or doc_title, headings=parser.headings)


_BLOCK_ALT = "|".join(sorted(BLOCK_TAGS, key=len, reverse=True))


def _tidy(body: str) -> str:
    body = re.sub(r"[ \t]*\n[ \t]*", "\n", body)
    # 只剩空白的段落不必留在书里。
    body = re.sub(r"<p\b[^>]*>(?:\s|<br/>)*</p>", "", body)
    body = re.sub(rf"<({_BLOCK_ALT})\b", r"\n<\1", body)
    body = re.sub(rf"</({_BLOCK_ALT})>", r"</\1>\n", body)
    body = re.sub(r"\n{2,}", "\n", body)
    return body.strip()
