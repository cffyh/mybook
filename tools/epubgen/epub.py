"""EPUB 3 打包。

只用标准库拼出一个合规的 EPUB 3 容器：mimetype、container.xml、package.opf、
nav.xhtml，外加一份 toc.ncx——NCX 在 EPUB 3 里已是旧物，但不少老阅读器（含
Kindle 的转换链路）只认它，留着不亏。

打包结果是可复现的：条目顺序固定，时间戳固定，同样的输入两次构建字节一致。
"""

from __future__ import annotations

import posixpath
import zipfile
from dataclasses import dataclass, field

MEDIA_TYPES = {
    ".xhtml": "application/xhtml+xml",
    ".html": "application/xhtml+xml",
    ".css": "text/css",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ncx": "application/x-dtbncx+xml",
}

# 固定时间戳，让同样的输入总是产出字节一致的 EPUB。
FIXED_TIME = (2026, 1, 1, 0, 0, 0)

XHTML_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}">
<head>
<meta charset="utf-8"/>
<title>{title}</title>
<link rel="stylesheet" type="text/css" href="{css}"/>
</head>
<body{body_attr}>
{body}
</body>
</html>
"""


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def media_type_for(path: str) -> str:
    ext = posixpath.splitext(path)[1].lower()
    return MEDIA_TYPES.get(ext, "application/octet-stream")


@dataclass
class Item:
    """package.opf manifest 里的一项。"""

    id: str
    href: str  # 相对 EPUB/ 目录
    data: bytes
    media_type: str = ""
    properties: str = ""
    in_spine: bool = False
    linear: bool = True

    def __post_init__(self) -> None:
        if not self.media_type:
            self.media_type = media_type_for(self.href)


@dataclass
class NavPoint:
    title: str
    href: str | None = None
    children: list["NavPoint"] = field(default_factory=list)


@dataclass
class Metadata:
    title: str
    language: str = "zh-CN"
    identifier: str = ""
    creator: str = ""
    subtitle: str = ""
    description: str = ""
    publisher: str = ""
    date: str = ""
    modified: str = ""
    subjects: list[str] = field(default_factory=list)


class EpubWriter:
    def __init__(self, metadata: Metadata, *, css_href: str = "styles/main.css") -> None:
        self.metadata = metadata
        self.css_href = css_href
        self.items: list[Item] = []
        self.nav: list[NavPoint] = []
        self.cover_image_id: str | None = None
        self._ids: set[str] = set()

    # ---------- 组装 ----------

    def _unique_id(self, base: str) -> str:
        candidate = base
        n = 1
        while candidate in self._ids:
            n += 1
            candidate = f"{base}-{n}"
        self._ids.add(candidate)
        return candidate

    def add_item(self, item_id: str, href: str, data: bytes, **kwargs) -> Item:
        item = Item(id=self._unique_id(item_id), href=href, data=data, **kwargs)
        self.items.append(item)
        return item

    def add_page(
        self,
        item_id: str,
        href: str,
        title: str,
        body: str,
        *,
        body_class: str = "",
        in_spine: bool = True,
        properties: str = "",
        linear: bool = True,
    ) -> Item:
        depth = href.count("/")
        css = "../" * depth + self.css_href
        html = XHTML_TEMPLATE.format(
            lang=_esc(self.metadata.language),
            title=_esc(title or self.metadata.title),
            css=_esc(css),
            body_attr=f' class="{_esc(body_class)}"' if body_class else "",
            body=body,
        )
        return self.add_item(
            item_id,
            href,
            html.encode("utf-8"),
            media_type="application/xhtml+xml",
            in_spine=in_spine,
            properties=properties,
            linear=linear,
        )

    def set_cover_image(self, item: Item) -> None:
        item.properties = " ".join(filter(None, [item.properties, "cover-image"]))
        self.cover_image_id = item.id

    # ---------- 各类 XML ----------

    def _package_opf(self) -> str:
        md = self.metadata
        lines = [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<package xmlns="http://www.idpf.org/2007/opf" version="3.0"'
            f' unique-identifier="book-id" xml:lang="{_esc(md.language)}">',
            '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">',
            f'    <dc:identifier id="book-id">{_esc(md.identifier)}</dc:identifier>',
            f'    <dc:title id="main-title">{_esc(md.title)}</dc:title>',
            '    <meta refines="#main-title" property="title-type">main</meta>',
            f"    <dc:language>{_esc(md.language)}</dc:language>",
        ]
        if md.subtitle:
            lines += [
                f'    <dc:title id="subtitle">{_esc(md.subtitle)}</dc:title>',
                '    <meta refines="#subtitle" property="title-type">subtitle</meta>',
            ]
        if md.creator:
            lines += [
                f'    <dc:creator id="creator">{_esc(md.creator)}</dc:creator>',
                '    <meta refines="#creator" property="role" scheme="marc:relators">aut</meta>',
                f'    <meta refines="#creator" property="file-as">{_esc(md.creator)}</meta>',
            ]
        if md.publisher:
            lines.append(f"    <dc:publisher>{_esc(md.publisher)}</dc:publisher>")
        if md.description:
            lines.append(f"    <dc:description>{_esc(md.description)}</dc:description>")
        if md.date:
            lines.append(f"    <dc:date>{_esc(md.date)}</dc:date>")
        for subject in md.subjects:
            lines.append(f"    <dc:subject>{_esc(subject)}</dc:subject>")
        lines.append(f'    <meta property="dcterms:modified">{_esc(md.modified)}</meta>')
        if self.cover_image_id:
            # 旧阅读器只认这条 legacy meta 来找封面。
            lines.append(f'    <meta name="cover" content="{_esc(self.cover_image_id)}"/>')
        lines.append("  </metadata>")

        lines.append("  <manifest>")
        for item in self.items:
            props = f' properties="{_esc(item.properties)}"' if item.properties else ""
            lines.append(
                f'    <item id="{_esc(item.id)}" href="{_esc(item.href)}"'
                f' media-type="{_esc(item.media_type)}"{props}/>'
            )
        lines.append('    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
        lines.append("  </manifest>")

        lines.append('  <spine toc="ncx">')
        for item in self.items:
            if item.in_spine:
                linear = "" if item.linear else ' linear="no"'
                lines.append(f'    <itemref idref="{_esc(item.id)}"{linear}/>')
        lines.append("  </spine>")
        lines.append("</package>")
        return "\n".join(lines) + "\n"

    def _nav_list(self, points: list[NavPoint], depth: int = 2) -> list[str]:
        pad = "  " * depth
        lines = [f"{pad}<ol>"]
        for point in points:
            label = _esc(point.title)
            body = f'<a href="{_esc(point.href)}">{label}</a>' if point.href else f"<span>{label}</span>"
            if point.children:
                lines.append(f"{pad}  <li>{body}")
                lines += self._nav_list(point.children, depth + 2)
                lines.append(f"{pad}  </li>")
            else:
                lines.append(f"{pad}  <li>{body}</li>")
        lines.append(f"{pad}</ol>")
        return lines

    def _nav_document(self, *, cover_href: str | None) -> str:
        body = ['<section class="toc">', f"<h1>目录</h1>", '<nav epub:type="toc" id="toc" role="doc-toc">']
        body += self._nav_list(self.nav, 0)
        body.append("</nav>")
        landmarks = ['<nav epub:type="landmarks" id="landmarks" hidden="hidden">', "<h2>导航</h2>", "<ol>"]
        if cover_href:
            landmarks.append(f'<li><a epub:type="cover" href="{_esc(cover_href)}">封面</a></li>')
        landmarks.append('<li><a epub:type="toc" href="nav.xhtml">目录</a></li>')
        first = next((i.href for i in self.items if i.in_spine and i.href.startswith("text/")), None)
        if first:
            landmarks.append(f'<li><a epub:type="bodymatter" href="{_esc(first)}">正文开始</a></li>')
        landmarks += ["</ol>", "</nav>"]
        body += landmarks
        body.append("</section>")
        return XHTML_TEMPLATE.format(
            lang=_esc(self.metadata.language),
            title="目录",
            css=_esc(self.css_href),
            body_attr=' class="nav-page"',
            body="\n".join(body),
        )

    def _ncx(self) -> str:
        node_count = [0]
        play_order: dict[str, int] = {}

        def order_of(href: str) -> int:
            """NCX 要求指向同一目标的条目共用一个 playOrder。辑本身没有页面，
            它借用了辑内第一篇的地址，因此必须和那一篇同号。"""
            if href not in play_order:
                play_order[href] = len(play_order) + 1
            return play_order[href]

        def first_href(point: NavPoint) -> str | None:
            for child in point.children:
                if child.href:
                    return child.href
                found = first_href(child)
                if found:
                    return found
            return None

        def emit(points: list[NavPoint], indent: str) -> list[str]:
            lines: list[str] = []
            for point in points:
                node_count[0] += 1
                href = point.href or first_href(point) or "nav.xhtml"
                order = order_of(href)
                lines.append(f'{indent}<navPoint id="np-{node_count[0]}" playOrder="{order}">')
                lines.append(f"{indent}  <navLabel><text>{_esc(point.title)}</text></navLabel>")
                lines.append(f'{indent}  <content src="{_esc(href)}"/>')
                lines += emit(point.children, indent + "  ")
                lines.append(f"{indent}</navPoint>")
            return lines

        lines = [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">',
            f'<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="{_esc(self.metadata.language)}">',
            "  <head>",
            f'    <meta name="dtb:uid" content="{_esc(self.metadata.identifier)}"/>',
            '    <meta name="dtb:depth" content="3"/>',
            '    <meta name="dtb:totalPageCount" content="0"/>',
            '    <meta name="dtb:maxPageNumber" content="0"/>',
            "  </head>",
            f"  <docTitle><text>{_esc(self.metadata.title)}</text></docTitle>",
        ]
        if self.metadata.creator:
            lines.append(f"  <docAuthor><text>{_esc(self.metadata.creator)}</text></docAuthor>")
        lines.append("  <navMap>")
        lines += emit(self.nav, "    ")
        lines += ["  </navMap>", "</ncx>"]
        return "\n".join(lines) + "\n"

    # ---------- 输出 ----------

    def write(self, out_path, *, cover_href: str | None = None) -> None:
        nav_item = Item(
            id="nav",
            href="nav.xhtml",
            data=self._nav_document(cover_href=cover_href).encode("utf-8"),
            media_type="application/xhtml+xml",
            properties="nav",
            in_spine=True,
        )
        self._ids.add("nav")
        # 目录页排在封面之后、正文之前。
        insert_at = 1 if self.items and self.items[0].href.startswith("cover") else 0
        self.items.insert(insert_at, nav_item)

        container = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
            "  <rootfiles>\n"
            '    <rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/>\n'
            "  </rootfiles>\n"
            "</container>\n"
        )

        with zipfile.ZipFile(out_path, "w") as archive:
            # mimetype 必须是第一个条目且不压缩。
            info = zipfile.ZipInfo("mimetype", date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, b"application/epub+zip")
            self._write(archive, "META-INF/container.xml", container.encode("utf-8"))
            self._write(archive, "EPUB/package.opf", self._package_opf().encode("utf-8"))
            self._write(archive, "EPUB/toc.ncx", self._ncx().encode("utf-8"))
            for item in self.items:
                self._write(archive, f"EPUB/{item.href}", item.data)

    @staticmethod
    def _write(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
        info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, data)
