"""Markdown → XHTML，针对本仓库实际用到的语法。

覆盖：ATX 标题、段落、有序/无序列表（含嵌套）、引用块、围栏代码、GFM 表格、
分隔线、行内代码、粗体、斜体、删除线、链接、图片、行内与行间公式。

有意不支持的：setext 标题（全仓库为零）、下划线强调（`_x_` 在中文文件名里全是
误报）、脚注、Markdown 里的内联 HTML（也为零）。少支持一点，换来的是不会把
正文里的普通字符错认成标记。
"""

from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field

from . import texmath

ESCAPABLE = set("\\`*_{}[]()#+-.!|~<>$\"'")

RE_ATX = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
RE_FENCE = re.compile(r"^(\s{0,3})(`{3,}|~{3,})\s*([^\s`]*)\s*$")
RE_HR = re.compile(r"^\s{0,3}((?:-\s*){3,}|(?:\*\s*){3,}|(?:_\s*){3,})$")
RE_UL = re.compile(r"^(\s*)([-*+])\s+(.*)$")
RE_OL = re.compile(r"^(\s*)(\d{1,9})[.)]\s+(.*)$")
RE_QUOTE = re.compile(r"^\s{0,3}>\s?(.*)$")
RE_TABLE_DELIM = re.compile(r"^\s*\|?(\s*:?-+:?\s*\|)+\s*:?-*:?\s*\|?\s*$")
RE_ENTITY = re.compile(r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")
RE_AUTOLINK = re.compile(r"<((?:https?|ftp|mailto):[^>\s]+)>")
RE_BARE_URL = re.compile(r"https?://[^\s<>()\[\]（）「」【】，。；：、“”\"']+")
RE_CMD = re.compile(r"\\([A-Za-z]+|.)")

# 单个 `*` 作强调时的最大跨度。中文正文里 `*` 也可能是乘号或占位符，
# 限长可以避免把半篇文章误包进 <em>。
MAX_EM_SPAN = 120


@dataclass
class Heading:
    """一条正文标题，用于生成目录与锚点。"""

    level: int
    text: str
    anchor: str


@dataclass
class Document:
    body: str
    title: str | None = None
    headings: list[Heading] = field(default_factory=list)


class Slugger:
    """生成稳定、唯一且合法的 XML id。

    中文直接写进 id 会让个别阅读器的锚点跳转失效，所以非 ASCII 一律折叠掉，
    再靠计数器保证唯一。
    """

    def __init__(self, prefix: str = "sec") -> None:
        self.prefix = prefix
        self.used: set[str] = set()

    def slug(self, text: str) -> str:
        norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
        ascii_part = re.sub(r"[^a-zA-Z0-9]+", "-", norm).strip("-").lower()
        base = f"{self.prefix}-{ascii_part}"[:48].rstrip("-") if ascii_part else self.prefix
        # 逐个试到不重复为止。只靠计数器不行：中文标题折叠后 base 就是 prefix，
        # 而某个含数字的标题恰好也能生成 "prefix-2"，两者会撞在一起。
        candidate = base
        counter = 1
        while candidate in self.used:
            counter += 1
            candidate = f"{base}-x{counter}"
        self.used.add(candidate)
        return candidate


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def strip_markup(text: str) -> str:
    """取标题的纯文本形态，供目录使用。"""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\$([^$]*)\$", r"\1", text)
    text = text.replace("**", "").replace("~~", "").replace("*", "")
    return re.sub(r"\s+", " ", text).strip()


def split_row(row: str) -> list[str]:
    """按未转义的 `|` 切分表格行；行内代码里的竖线不算分隔符。"""
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    cells: list[str] = []
    buf: list[str] = []
    in_code = False
    i = 0
    while i < len(row):
        ch = row[i]
        if ch == "\\" and i + 1 < len(row) and row[i + 1] == "|":
            buf.append("\\|")
            i += 2
            continue
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    return cells


def _alignment(spec: str) -> str:
    spec = spec.strip()
    if spec.startswith(":") and spec.endswith(":"):
        return "center"
    if spec.endswith(":"):
        return "right"
    if spec.startswith(":"):
        return "left"
    return ""


class MarkdownConverter:
    """把一份 Markdown 文稿转成一段 XHTML 正文。

    `resolve_link` / `resolve_image` 由调用方提供，用来把仓库内的相对路径改写成
    书内跳转。返回 None 表示这个目标在书里不存在：链接退化成纯文本，图片退化成
    图注，都不会留下断链。
    """

    def __init__(
        self,
        id_prefix: str = "sec",
        *,
        resolve_link: Callable[[str], str | None] | None = None,
        resolve_image: Callable[[str], str | None] | None = None,
    ) -> None:
        self.slugger = Slugger(id_prefix)
        self.resolve_link = resolve_link
        self.resolve_image = resolve_image
        self.headings: list[Heading] = []
        # 渲染链接文字时置位：XHTML 不允许 <a> 嵌套 <a>。
        self._in_link = False

    # ---------- 对外入口 ----------

    def convert(self, text: str, *, extract_title: bool = True) -> Document:
        self.headings = []
        lines = text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
        lines = lines.expandtabs(4).split("\n")
        title = None
        if extract_title:
            title, lines = self._take_title(lines)
        body = self._blocks(lines)
        return Document(body=body, title=title, headings=self.headings)

    def _take_title(self, lines: list[str]) -> tuple[str | None, list[str]]:
        """摘掉开头的一级标题——它由章页的抬头负责渲染，正文里不必重复。"""
        for idx, line in enumerate(lines):
            if not line.strip():
                continue
            if RE_HR.match(line):
                continue
            m = RE_ATX.match(line)
            if m and len(m.group(1)) == 1:
                return strip_markup(m.group(2)), lines[:idx] + lines[idx + 1:]
            return None, lines
        return None, lines

    # ---------- 块级 ----------

    def _blocks(self, lines: list[str]) -> str:
        out: list[str] = []
        i, n = 0, len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            if RE_FENCE.match(line):
                i = self._fence(lines, i, out)
            elif RE_ATX.match(line):
                self._heading(RE_ATX.match(line), out)
                i += 1
            elif self._is_table(lines, i):
                i = self._table(lines, i, out)
            elif RE_HR.match(line):
                out.append("<hr/>")
                i += 1
            elif RE_QUOTE.match(line):
                i = self._quote(lines, i, out)
            elif RE_UL.match(line) or RE_OL.match(line):
                i = self._list(lines, i, out)
            else:
                i = self._paragraph(lines, i, out)
        return "\n".join(out)

    def _is_block_start(self, lines: list[str], i: int) -> bool:
        line = lines[i]
        return bool(
            RE_FENCE.match(line)
            or RE_ATX.match(line)
            or RE_HR.match(line)
            or RE_QUOTE.match(line)
            or RE_UL.match(line)
            or RE_OL.match(line)
            or self._is_table(lines, i)
        )

    @staticmethod
    def _is_table(lines: list[str], i: int) -> bool:
        return (
            "|" in lines[i]
            and i + 1 < len(lines)
            and "|" in lines[i + 1]
            and RE_TABLE_DELIM.match(lines[i + 1]) is not None
            and len(split_row(lines[i])) == len(split_row(lines[i + 1]))
        )

    def _heading(self, m: re.Match[str], out: list[str]) -> None:
        level = len(m.group(1))
        raw = m.group(2).strip()
        plain = strip_markup(raw)
        anchor = self.slugger.slug(plain)
        self.headings.append(Heading(level=level, text=plain, anchor=anchor))
        # 篇名已提出来占了 h1，所以 `##` 正好落在 h2；文中若再出现 `#`，下沉到 h2。
        tag = f"h{max(level, 2)}"
        out.append(f'<{tag} id="{anchor}">{self.inline(raw)}</{tag}>')

    def _fence(self, lines: list[str], i: int, out: list[str]) -> int:
        m = RE_FENCE.match(lines[i])
        assert m
        marker, lang = m.group(2), (m.group(3) or "").strip()
        i += 1
        buf: list[str] = []
        while i < len(lines):
            close = RE_FENCE.match(lines[i])
            if close and close.group(2)[0] == marker[0] and len(close.group(2)) >= len(marker) and not close.group(3):
                i += 1
                break
            buf.append(lines[i])
            i += 1
        code = "\n".join(buf)
        if lang == "math":
            out.append(texmath.block(code))
        else:
            # `other` 在仓库里是「没标语言」的占位写法，不是真的语言名。
            attr = f' class="language-{esc(lang)}"' if lang and lang != "other" else ""
            out.append(f"<pre><code{attr}>{esc(code)}</code></pre>")
        return i

    def _quote(self, lines: list[str], i: int, out: list[str]) -> int:
        buf: list[str] = []
        n = len(lines)
        while i < n:
            m = RE_QUOTE.match(lines[i])
            if m:
                buf.append(m.group(1))
                i += 1
            elif lines[i].strip() and not self._is_block_start(lines, i):
                buf.append(lines[i])  # 懒续行
                i += 1
            else:
                break
        out.append("<blockquote>" + self._blocks(buf) + "</blockquote>")
        return i

    def _list(self, lines: list[str], i: int, out: list[str]) -> int:
        n = len(lines)
        first_ol = RE_OL.match(lines[i])
        first = first_ol or RE_UL.match(lines[i])
        assert first
        ordered = first_ol is not None
        base = len(first.group(1))
        start_no = int(first_ol.group(2)) if first_ol else 1
        items: list[list[str]] = []
        loose = False
        blank = False
        while i < n:
            line = lines[i]
            if not line.strip():
                blank = True
                i += 1
                continue
            m_ol = RE_OL.match(line)
            m = m_ol or RE_UL.match(line)
            indent = len(line) - len(line.lstrip())
            if m and len(m.group(1)) == base:
                if items and (m_ol is not None) != ordered:
                    break  # 标记类型变了，交给下一个列表处理
                if blank and items:
                    loose = True
                    items[-1].append("")
                items.append([m.group(3)])
                blank = False
                i += 1
            elif items and indent > base:
                if blank:
                    loose = True
                    items[-1].append("")
                items[-1].append(line[min(indent, base + 2):])
                blank = False
                i += 1
            elif items and not blank and not m and indent >= base:
                items[-1].append(line.strip())  # 懒续行
                i += 1
            else:
                break
        rendered = []
        for item in items:
            inner = self._blocks(item)
            if not loose:
                inner = self._unwrap_paragraph(inner)
            rendered.append(f"<li>{inner}</li>")
        tag = "ol" if ordered else "ul"
        attr = f' start="{start_no}"' if ordered and start_no != 1 else ""
        out.append(f"<{tag}{attr}>" + "".join(rendered) + f"</{tag}>")
        return i

    @staticmethod
    def _unwrap_paragraph(inner: str) -> str:
        """紧凑列表项里只有一段文字时，去掉多余的 <p> 包裹。"""
        if inner.startswith("<p>") and inner.endswith("</p>") and "<p>" not in inner[3:]:
            return inner[3:-4]
        return inner

    def _table(self, lines: list[str], i: int, out: list[str]) -> int:
        header = split_row(lines[i])
        aligns = [_alignment(c) for c in split_row(lines[i + 1])]
        i += 2
        n = len(lines)
        rows: list[list[str]] = []
        while i < n and lines[i].strip() and "|" in lines[i] and not RE_ATX.match(lines[i]):
            rows.append(split_row(lines[i]))
            i += 1

        def cell(tag: str, value: str, col: int) -> str:
            style = f' class="ta-{aligns[col]}"' if col < len(aligns) and aligns[col] else ""
            return f"<{tag}{style}>{self.inline(value)}</{tag}>"

        width = len(header)
        parts = ["<table>", "<thead><tr>"]
        parts += [cell("th", value, col) for col, value in enumerate(header)]
        parts.append("</tr></thead>")
        if rows:
            parts.append("<tbody>")
            for row in rows:
                row = (row + [""] * width)[:width]
                parts.append("<tr>" + "".join(cell("td", v, c) for c, v in enumerate(row)) + "</tr>")
            parts.append("</tbody>")
        parts.append("</table>")
        out.append('<div class="table-wrap">' + "".join(parts) + "</div>")
        return i

    def _paragraph(self, lines: list[str], i: int, out: list[str]) -> int:
        buf: list[str] = []
        n = len(lines)
        while i < n and lines[i].strip() and not (buf and self._is_block_start(lines, i)):
            buf.append(lines[i].strip())
            i += 1
            if i < n and self._is_block_start(lines, i):
                break
        text = "\n".join(buf).strip()
        if text:
            out.append("<p>" + self.inline(text) + "</p>")
        return i

    # ---------- 行内 ----------

    def inline(self, text: str) -> str:
        out: list[str] = []
        i, n = 0, len(text)
        while i < n:
            ch = text[i]
            if ch == "\\":
                if i + 1 < n and text[i + 1] in ESCAPABLE:
                    out.append(esc(text[i + 1]))
                    i += 2
                    continue
                if i + 1 < n and text[i + 1] == "\n":
                    out.append("<br/>\n")
                    i += 2
                    continue
                out.append("\\")
                i += 1
            elif ch == "`":
                i = self._code_span(text, i, out)
            elif ch == "$":
                i = self._math(text, i, out)
            elif ch == "!" and text.startswith("![", i):
                i = self._bracketed(text, i + 1, out, image=True, fallback="!")
            elif ch == "[" and not self._in_link:
                i = self._bracketed(text, i, out, image=False, fallback="[")
            elif text.startswith("**", i):
                i = self._wrap(text, i, out, "**", "strong")
            elif ch == "*":
                i = self._wrap(text, i, out, "*", "em")
            elif text.startswith("~~", i):
                i = self._wrap(text, i, out, "~~", "del")
            elif ch == "<":
                m = RE_AUTOLINK.match(text, i)
                if m and not self._in_link:
                    out.append(f'<a href="{esc(m.group(1))}">{esc(m.group(1))}</a>')
                    i = m.end()
                elif m:
                    out.append(esc(m.group(1)))
                    i = m.end()
                else:
                    out.append("&lt;")
                    i += 1
            elif ch == "&":
                m = RE_ENTITY.match(text, i)
                if m:
                    # 只有 XML 预定义实体在 EPUB 里合法，其余先解码再转义。
                    out.append(esc(html.unescape(m.group(0))))
                    i = m.end()
                else:
                    out.append("&amp;")
                    i += 1
            elif ch in "hH" and (m := RE_BARE_URL.match(text, i)):
                url = m.group(0).rstrip(".,;:!?")
                out.append(esc(url) if self._in_link else f'<a href="{esc(url)}">{esc(url)}</a>')
                i += len(url)
            elif ch == "\n":
                out.append("\n")
                i += 1
            else:
                out.append(esc(ch))
                i += 1
        return "".join(out)

    def _code_span(self, text: str, i: int, out: list[str]) -> int:
        j = i
        while j < len(text) and text[j] == "`":
            j += 1
        fence = text[i:j]
        end = text.find(fence, j)
        if end == -1:
            out.append(esc(fence))
            return j
        code = text[j:end]
        if len(code) > 2 and code[0] == " " and code[-1] == " " and code.strip():
            code = code[1:-1]
        out.append(f"<code>{esc(code)}</code>")
        return end + len(fence)

    def _math(self, text: str, i: int, out: list[str]) -> int:
        if text.startswith("$$", i):
            end = text.find("$$", i + 2)
            if end != -1:
                out.append(texmath.inline(text[i + 2:end]))
                return end + 2
        else:
            m = re.compile(r"\$(?![\s$])((?:[^$\n\\]|\\.)+?)(?<![\s\\])\$").match(text, i)
            if m:
                out.append(texmath.inline(m.group(1)))
                return m.end()
        out.append("$")
        return i + 1

    def _wrap(self, text: str, i: int, out: list[str], marker: str, tag: str) -> int:
        start = i + len(marker)
        limit = MAX_EM_SPAN if marker == "*" else None
        end = self._find_close(text, start, marker, limit)
        if end != -1 and text[start:end].strip():
            out.append(f"<{tag}>{self.inline(text[start:end])}</{tag}>")
            return end + len(marker)
        out.append(esc(marker))
        return i + len(marker)

    @staticmethod
    def _find_close(text: str, start: int, marker: str, limit: int | None) -> int:
        if start >= len(text) or text[start].isspace():
            return -1
        n = len(text)
        stop = n if limit is None else min(n, start + limit)
        i = start
        while i < stop:
            ch = text[i]
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                j = i
                while j < n and text[j] == "`":
                    j += 1
                end = text.find(text[i:j], j)
                i = j if end == -1 else end + (j - i)
                continue
            if text.startswith(marker, i):
                if marker == "*" and text.startswith("**", i):
                    i += 2
                    continue
                if not text[i - 1].isspace():
                    return i
                i += len(marker)
                continue
            i += 1
        return -1

    def _bracketed(self, text: str, pos: int, out: list[str], *, image: bool, fallback: str) -> int:
        parsed = self._parse_link(text, pos)
        if parsed is None:
            out.append(esc(fallback))
            return pos if image else pos + 1
        label, dest, title, end = parsed
        if image:
            src = self.resolve_image(dest) if self.resolve_image else dest
            alt = strip_markup(label)
            if src is None:
                # 图片文件不在仓库里，只留一行图注，不留断链。
                out.append(f'<span class="figure-missing">［图：{esc(alt)}］</span>' if alt else "")
            else:
                attr = f' title="{esc(title)}"' if title else ""
                out.append(f'<img src="{esc(src)}" alt="{esc(alt)}"{attr}/>')
            return end
        href = self.resolve_link(dest) if self.resolve_link else dest
        was_in_link = self._in_link
        # 只有真要输出 <a> 时才禁止内层链接；这条链接被丢掉时，标签里嵌套的链接
        # 仍该正常成链，否则读者只会看到一串裸的 Markdown 记号。
        self._in_link = was_in_link or href is not None
        inner = self.inline(label)
        self._in_link = was_in_link
        if href is None:
            # 目标不在这本书里：保留文字，去掉链接。
            out.append(f'<span class="link-plain">{inner}</span>')
        else:
            attr = f' title="{esc(title)}"' if title else ""
            out.append(f'<a href="{esc(href)}"{attr}>{inner}</a>')
        return end

    @staticmethod
    def _parse_link(text: str, pos: int) -> tuple[str, str, str, int] | None:
        """解析 `[label](dest "title")`，返回 (label, dest, title, 结束位置)。"""
        n = len(text)
        depth = 0
        i = pos
        while i < n:
            if text[i] == "\\":
                i += 2
                continue
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    break
            elif text[i] == "\n" and i + 1 < n and not text[i + 1].strip():
                return None
            i += 1
        if i >= n or text[i] != "]" or i + 1 >= n or text[i + 1] != "(":
            return None
        label = text[pos + 1:i]
        j = i + 2
        depth = 1
        while j < n:
            if text[j] == "\\":
                j += 2
                continue
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            elif text[j] == "\n":
                return None
            j += 1
        if j >= n:
            return None
        raw = text[i + 2:j].strip()
        m = re.match(r'^(<[^>]*>|\S*)(?:\s+["\'(]\s*(.*?)\s*["\')])?$', raw, re.S)
        if not m:
            dest, title = raw, ""
        else:
            dest, title = m.group(1), m.group(2) or ""
        if dest.startswith("<") and dest.endswith(">"):
            dest = dest[1:-1]
        return label, dest.strip(), title, j + 1
