"""封面。

优先用 `tools/assets/cover.png`（由 `tools/make_cover.py` 生成并随仓库提交，
这样日常构建不需要装 Pillow、也不需要下载中文字体）。找不到这张图时，退回一张
纯文字的 SVG 封面——阅读器一样能显示，只是书架缩略图不如位图好看。
"""

from __future__ import annotations

from pathlib import Path

WIDTH, HEIGHT = 1600, 2400
PAPER = "#f6f3ea"
INK = "#1f2933"
ACCENT = "#8c6f4a"
MUTED = "#8a8478"

SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect width="{w}" height="{h}" fill="{paper}"/>
  <rect x="90" y="90" width="{inner_w}" height="{inner_h}" fill="none" stroke="{accent}" stroke-width="3"/>
  <g font-family="Source Han Serif SC, Noto Serif CJK SC, Songti SC, serif" text-anchor="middle">
    <text x="{cx}" y="760" font-size="190" fill="{ink}" letter-spacing="26">{title}</text>
    <text x="{cx}" y="900" font-size="52" fill="{muted}" letter-spacing="10">{subtitle}</text>
    <text x="{cx}" y="{author_y}" font-size="60" fill="{ink}" letter-spacing="18">{author}</text>
  </g>
  <g stroke="{accent}" stroke-width="4" fill="none">
    <rect x="{bar_x}" y="1240" width="{bar_w}" height="150"/>
    <rect x="{bar_x}" y="1610" width="{bar_w}" height="150"/>
    <line x1="{cx}" y1="1390" x2="{cx}" y2="1610"/>
  </g>
  <g font-family="Source Han Sans SC, Noto Sans CJK SC, sans-serif" text-anchor="middle" fill="{muted}" font-size="46">
    <text x="{cx}" y="1332" letter-spacing="12">{upper}</text>
    <text x="{cx}" y="1702" letter-spacing="12">{lower}</text>
  </g>
</svg>
"""


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_cover(title: str, subtitle: str, author: str) -> bytes:
    bar_w = 760
    return SVG_TEMPLATE.format(
        w=WIDTH,
        h=HEIGHT,
        inner_w=WIDTH - 180,
        inner_h=HEIGHT - 180,
        cx=WIDTH // 2,
        paper=PAPER,
        ink=INK,
        accent=ACCENT,
        muted=MUTED,
        title=_esc(title),
        subtitle=_esc(subtitle),
        author=_esc(author),
        author_y=HEIGHT - 300,
        bar_x=(WIDTH - bar_w) // 2,
        bar_w=bar_w,
        upper=_esc("上极 · 人如何变强"),
        lower=_esc("下极 · 世界的底层语法"),
    ).encode("utf-8")


def load(assets_dir: Path, title: str, subtitle: str, author: str) -> tuple[str, bytes]:
    """返回 (文件名, 数据)。"""
    png = assets_dir / "cover.png"
    if png.is_file():
        return "cover.png", png.read_bytes()
    jpg = assets_dir / "cover.jpg"
    if jpg.is_file():
        return "cover.jpg", jpg.read_bytes()
    return "cover.svg", svg_cover(title, subtitle, author)
