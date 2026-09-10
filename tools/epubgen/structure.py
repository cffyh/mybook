"""把仓库里的文件组织成「卷 → 辑 → 篇」的书稿结构。

三件事：按配置收集并排序篇目、把每篇转换成 XHTML、把篇与篇之间的相对链接改写
成书内跳转。配置放在 tools/book.json，改目录顺序不用改代码。
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

from . import docxconv, htmlconv, mdconv
from .mdconv import Document, Heading

TEXT_SUFFIXES = {".md", ".markdown", ".html", ".htm", ".docx"}

# 目录里这些东西不是文章。
SKIP_NAMES = {".DS_Store", ".gitignore", "_manifest.txt"}
SKIP_DIRS = {".git", ".github", "node_modules", "__pycache__", "tools", "dist"}

CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "壹": 1, "贰": 2, "叁": 3,
}
# 排序时把序数词换成数字，只影响先后，不影响显示。
ORDINAL_WORDS = {"引子": 0, "上篇": 1, "中篇": 2, "下篇": 3, "上": 1, "中": 2, "下": 3}
RE_ORDINAL = re.compile(r"(第|乐章|其)([零〇一二三四五六七八九十百]+)")
RE_NUM_RUN = re.compile(r"\d+(?:\.\d+)*")

# 文件名里用于排序的编号前缀，以及标示稿件状态的后缀。
RE_STEM_PREFIX = re.compile(r"^\d+(?:\.\d+)*[-_\s]*")
RE_STEM_SUFFIX = re.compile(r"[_-](?:独立成文|重构稿|成文稿|完整版|草稿|底稿|全文)$")

# 「本篇已迁走，正文不再维护」这类占位文件，进书只会变成断头路。
RE_STUB = re.compile(r"(请改读|不再维护|已迁入|已迁出|见新文|转址|本文件只留)")
STUB_MAX_CHARS = 700


def cn_to_int(text: str) -> int:
    """把「六」「十二」「二十一」这类中文数字读成整数。"""
    total, section = 0, 0
    for ch in text:
        if ch in CN_DIGITS:
            section = section * 10 + CN_DIGITS[ch] if section and CN_DIGITS[ch] else CN_DIGITS[ch]
        elif ch == "十":
            section = (section or 1) * 10
        elif ch == "百":
            total += (section or 1) * 100
            section = 0
    return total + section


def sort_key(name: str) -> tuple:
    """自然排序键。

    两条规则合在一起，正好复现作者的编号习惯：

    - 整数部分按数值比，所以 `第二章` 在 `第十章` 之前、`9` 在 `10` 之前；
    - 小数部分按字符串比。作者用 `1.21` 表示 `1.2` 的细化、用 `3.15` 表示 `3.1`
      的细化，因此顺序应是 1.1 → 1.2 → 1.21 → 1.3，而不是把它们读成小数。
    - 中文序数（第六章、乐章五）先折算成数字再比。
    """
    text = RE_ORDINAL.sub(lambda m: f"{m.group(1)}{cn_to_int(m.group(2)):04d}", name)
    for word, value in ORDINAL_WORDS.items():
        if text.startswith(word):
            text = f"{value:04d}{text[len(word):]}"
            break
    parts: list[tuple[int, str]] = []
    pos = 0
    for m in RE_NUM_RUN.finditer(text):
        if m.start() > pos:
            parts.append((1, text[pos:m.start()]))
        head, dot, tail = m.group(0).partition(".")
        parts.append((0, f"{int(head):06d}{dot}{tail}"))
        pos = m.end()
    if pos < len(text):
        parts.append((1, text[pos:]))
    return tuple(parts)


def gh_slug(text: str) -> str:
    """GitHub 风格的标题锚点，用来认出正文里 `文件.md#某标题` 这类链接。"""
    text = unicodedata.normalize("NFKC", text).strip().lower()
    text = re.sub(r"[ \t]+", "-", text)
    return re.sub(r"[^\w\u3400-\u9fff\-]+", "", text, flags=re.UNICODE)


@dataclass
class Article:
    """书里的一篇。"""

    path: Path
    title: str
    doc: Document
    item_id: str
    href: str
    volume_title: str = ""
    group_title: str = ""

    @property
    def headings(self) -> list[Heading]:
        return self.doc.headings


@dataclass
class Group:
    """卷内的一辑（通常对应一个子目录）。"""

    title: str
    articles: list[Article] = field(default_factory=list)
    groups: list["Group"] = field(default_factory=list)

    def walk(self) -> Iterable[Article]:
        yield from self.articles
        for group in self.groups:
            yield from group.walk()


@dataclass
class Volume:
    """一卷。"""

    vol_id: str
    title: str
    subtitle: str = ""
    intro: str = ""
    articles: list[Article] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    href: str = ""

    def walk(self) -> Iterable[Article]:
        yield from self.articles
        for group in self.groups:
            yield from group.walk()


@dataclass
class SourceSpec:
    path: str
    title: str | None = None
    recursive: bool = True
    order: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)

    @classmethod
    def parse(cls, raw) -> "SourceSpec":
        if isinstance(raw, str):
            return cls(path=raw)
        return cls(
            path=raw["path"],
            title=raw.get("title"),
            recursive=raw.get("recursive", True),
            order=raw.get("order", []),
            exclude=raw.get("exclude", []),
        )


class Collector:
    """遍历配置里列出的来源，产出有序的卷/辑/篇结构。"""

    def __init__(self, root: Path, *, skip_stubs: bool = True, verbose: bool = False) -> None:
        self.root = root
        self.skip_stubs = skip_stubs
        self.verbose = verbose
        self.claimed: set[Path] = set()
        self.skipped_stubs: list[Path] = []
        self.duplicates: list[tuple[Path, Path]] = []
        self.warnings: list[str] = []
        self._by_digest: dict[str, Path] = {}

    # ---------- 收集 ----------

    def collect(self, volume_specs: list[dict]) -> list[Volume]:
        volumes: list[Volume] = []
        for spec in volume_specs:
            volume = Volume(
                vol_id=spec["id"],
                title=spec["title"],
                subtitle=spec.get("subtitle", ""),
                intro=spec.get("intro", ""),
            )
            for raw_source in spec.get("sources", []):
                source = SourceSpec.parse(raw_source)
                target = self.root / source.path
                if not target.exists():
                    self.warnings.append(f"来源不存在，已跳过：{source.path}")
                    continue
                if target.is_file():
                    articles = self._to_articles([target])
                    subgroups: list[Group] = []
                else:
                    files, subdirs = self._scan_dir(target, source)
                    articles = self._to_articles(self._ordered(files, source.order))
                    subgroups = [
                        group
                        for subdir in subdirs
                        if (group := self._build_group(subdir, source)) and list(group.walk())
                    ]
                if not articles and not subgroups:
                    continue
                if source.title:
                    # 给了标题，就把这个来源整体收成卷内的一辑。
                    volume.groups.append(Group(title=source.title, articles=articles, groups=subgroups))
                else:
                    volume.articles.extend(articles)
                    volume.groups.extend(subgroups)
            volumes.append(volume)
        return volumes

    def _scan_dir(self, directory: Path, source: SourceSpec) -> tuple[list[Path], list[Path]]:
        files: list[Path] = []
        subdirs: list[Path] = []
        for child in sorted(directory.iterdir(), key=lambda p: sort_key(p.name)):
            if child.name in SKIP_NAMES or child.name.startswith("."):
                continue
            rel = child.relative_to(self.root).as_posix()
            if any(pattern in rel for pattern in source.exclude):
                continue
            if child.is_dir():
                if child.name in SKIP_DIRS:
                    continue
                if source.recursive:
                    subdirs.append(child)
            elif child.suffix.lower() in TEXT_SUFFIXES:
                files.append(child)
        return files, subdirs

    def _build_group(self, directory: Path, source: SourceSpec) -> Group | None:
        files, subdirs = self._scan_dir(directory, source)
        group = Group(title=clean_group_title(directory.name))
        group.articles = self._to_articles(self._ordered(files, source.order))
        for subdir in subdirs:
            child = self._build_group(subdir, source)
            if child and list(child.walk()):
                group.groups.append(child)
        return group

    @staticmethod
    def _ordered(files: list[Path], order: list[str]) -> list[Path]:
        """按 order 里给的前缀排在最前，其余自然排序。README 永远第一——它是导读。"""

        def key(path: Path) -> tuple:
            if path.stem.upper().startswith("README"):
                return (0, 0, ())
            for index, hint in enumerate(order):
                if path.name.startswith(hint):
                    return (1, index, sort_key(path.name))
            return (2, 0, sort_key(path.name))

        return sorted(files, key=key)

    def _to_articles(self, files: list[Path]) -> list[Article]:
        """先只登记路径。正文转换要等篇目全集就位，因为链接改写需要知道全书有哪些篇。"""
        result = []
        for path in files:
            if path in self.claimed:
                continue
            if self.skip_stubs and self._is_stub(path):
                self.skipped_stubs.append(path)
                continue
            # backup/ 下有若干与正式目录一字不差的副本，同一篇不必在书里出现两次。
            digest = hashlib.sha1(path.read_bytes()).hexdigest()
            if digest in self._by_digest:
                self.duplicates.append((path, self._by_digest[digest]))
                continue
            self._by_digest[digest] = path
            self.claimed.add(path)
            result.append(
                Article(
                    path=path,
                    title=fallback_title(path),
                    doc=Document(body=""),
                    item_id="",
                    href="",
                )
            )
        return result

    @staticmethod
    def _is_stub(path: Path) -> bool:
        if path.suffix.lower() not in {".md", ".markdown"}:
            return False
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        return len(text) <= STUB_MAX_CHARS and RE_STUB.search(text) is not None

    def unclaimed(self) -> list[Path]:
        """仓库里符合条件、却没有被任何一卷收进去的文件。"""
        missing = []
        for path in sorted(self.root.rglob("*"), key=lambda p: p.as_posix()):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            rel_parts = path.relative_to(self.root).parts
            if any(part in SKIP_DIRS for part in rel_parts) or any(part.startswith(".") for part in rel_parts):
                continue
            if path in self.claimed or path in self.skipped_stubs:
                continue
            if any(path == duplicate for duplicate, _ in self.duplicates):
                continue
            missing.append(path)
        return missing


def clean_group_title(name: str) -> str:
    """目录名 → 辑名。去掉排序用的数字前缀，把连接符换成间隔号。"""
    title = re.sub(r"^[0-9]+[-_.\s]*", "", name)
    title = title.replace("_", "·").replace("-", "·")
    return title.strip("·") or name


def fallback_title(path: Path) -> str:
    """文件名 → 篇名。"""
    stem = path.stem
    stem = re.sub(r"^\d+(\.\d+)*[-_\s]*", "", stem)
    stem = stem.replace("_", " ").strip()
    return stem or path.stem


def stem_keys(stem: str) -> list[str]:
    """一个文件名可能被别处以哪几种写法引用。"""
    keys = [stem.strip()]
    trimmed = RE_STEM_PREFIX.sub("", keys[0]).strip()
    keys.append(trimmed)
    keys.append(RE_STEM_SUFFIX.sub("", trimmed).strip())
    seen: list[str] = []
    for key in keys:
        if key and key not in seen:
            seen.append(key)
    return seen


class Renderer:
    """把已排好序的篇目转成 XHTML，并把篇间链接接上。"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.by_path: dict[Path, Article] = {}
        self.by_stem: dict[str, list[Article]] = {}
        self.anchor_index: dict[Path, dict[str, str]] = {}
        self.dropped_links: list[tuple[str, str]] = []
        self.recovered_links: list[tuple[str, str, str]] = []
        self.missing_images: list[tuple[str, str]] = []

    def assign_ids(self, volumes: list[Volume]) -> None:
        for volume in volumes:
            volume.href = f"text/{volume.vol_id}-000.xhtml"
            for index, article in enumerate(volume.walk(), start=1):
                article.item_id = f"{volume.vol_id}-{index:03d}"
                article.href = f"text/{article.item_id}.xhtml"
                article.volume_title = volume.title
                self.by_path[article.path] = article
                for key in stem_keys(article.path.stem):
                    self.by_stem.setdefault(key, []).append(article)

    def render(self, volumes: list[Volume]) -> None:
        for volume in volumes:
            self._render_group(volume.articles, volume.title, "")
            for group in volume.groups:
                self._render_group_tree(group, volume.title)

    def _render_group_tree(self, group: Group, volume_title: str) -> None:
        self._render_group(group.articles, volume_title, group.title)
        for child in group.groups:
            self._render_group_tree(child, volume_title)

    def _render_group(self, articles: list[Article], volume_title: str, group_title: str) -> None:
        for article in articles:
            article.volume_title = volume_title
            article.group_title = group_title
            self._render_one(article)

    def _render_one(self, article: Article) -> None:
        suffix = article.path.suffix.lower()
        prefix = article.item_id  # 形如 book4-003，本身就是稳定且唯一的 id 前缀

        def resolve_link(dest: str) -> str | None:
            return self._resolve_link(article, dest)

        def resolve_image(dest: str) -> str | None:
            return self._resolve_image(article, dest)

        if suffix == ".docx":
            doc = docxconv.convert(article.path, id_prefix=prefix)
        elif suffix in {".html", ".htm"}:
            doc = htmlconv.convert(
                article.path.read_text(encoding="utf-8", errors="replace"),
                id_prefix=prefix,
                resolve_link=resolve_link,
                resolve_image=resolve_image,
            )
        else:
            converter = mdconv.MarkdownConverter(
                prefix, resolve_link=resolve_link, resolve_image=resolve_image
            )
            doc = converter.convert(article.path.read_text(encoding="utf-8", errors="replace"))
        article.doc = doc
        if doc.title:
            article.title = doc.title
        self.anchor_index[article.path] = {gh_slug(h.text): h.anchor for h in doc.headings}

    # ---------- 链接 ----------

    def _resolve_target(self, article: Article, dest: str) -> tuple[Path | None, str]:
        raw, _, fragment = dest.partition("#")
        raw = unquote(raw.strip())
        if not raw:
            return article.path, fragment
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw) or raw.startswith("//"):
            return None, fragment
        candidate = (article.path.parent / raw).resolve()
        try:
            candidate.relative_to(self.root.resolve())
        except ValueError:
            return None, fragment
        return candidate, fragment

    def _resolve_link(self, article: Article, dest: str) -> str | None:
        raw = dest.strip()
        if not raw:
            return None
        if re.match(r"^(https?|ftp|mailto):", raw):
            return raw
        if raw.startswith("#"):
            anchor = self.anchor_index.get(article.path, {}).get(gh_slug(unquote(raw[1:])))
            return f"#{anchor}" if anchor else None
        target, fragment = self._resolve_target(article, raw)
        if target is None:
            self.dropped_links.append((article.path.name, dest))
            return None
        found = self.by_path.get(target)
        if found is None and target.is_dir():
            # 目录链接：退回该目录下第一篇。
            found = next(
                (a for path, a in self.by_path.items() if target in path.parents), None
            )
        if found is None:
            found = self._by_filename(article, target)
            if found is not None:
                self.recovered_links.append((article.path.name, dest, found.title))
        if found is None:
            self.dropped_links.append((article.path.name, dest))
            return None
        href = found.href.split("/")[-1]
        if fragment:
            anchor = self.anchor_index.get(found.path, {}).get(gh_slug(unquote(fragment)))
            if anchor:
                href = f"{href}#{anchor}"
        return href

    def _by_filename(self, article: Article, target: Path) -> Article | None:
        """按文件名找回目标。

        仓库里不少互链是历史遗留：篇目改过名、挪过目录，或者链接里漏掉了排序用的
        数字前缀，照路径找必然落空。只按文件名（去掉编号前缀与「_独立成文」这类
        后缀）再找一次，能把大部分交叉引用接回来。同名多篇时，优先同一顶层目录下
        的那一篇；仍分不清就放弃，宁可退化成纯文字，也不乱指。
        """
        if target.suffix.lower() not in TEXT_SUFFIXES:
            return None
        for key in stem_keys(target.stem):
            candidates = [a for a in self.by_stem.get(key, []) if a.path != article.path]
            if not candidates:
                continue
            if len(candidates) == 1:
                return candidates[0]
            top = article.path.relative_to(self.root).parts[0]
            same_area = [
                a for a in candidates if a.path.relative_to(self.root).parts[0] == top
            ]
            if len(same_area) == 1:
                return same_area[0]
            return None
        return None

    def _resolve_image(self, article: Article, dest: str) -> str | None:
        target, _ = self._resolve_target(article, dest)
        if target is None or not target.is_file():
            self.missing_images.append((article.path.name, dest))
            return None
        return None  # 仓库里目前没有随文图片；真出现时在此登记资源即可


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
