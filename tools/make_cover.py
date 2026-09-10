#!/usr/bin/env python3
"""生成封面位图 tools/assets/cover.png。

跑一次就够，产物随仓库提交；`build_epub.py` 直接用现成的 PNG，所以日常构建既不
需要 Pillow，也不需要中文字体。改书名或想换封面时再跑这个脚本。

    pip install pillow
    python3 tools/make_cover.py --font /path/to/NotoSerifSC-Bold.otf

`--font` 可省略：脚本会在常见的中文字体位置里找。找不到就会明确报错，而不是画出
一张满是方框的封面。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    sys.exit("需要 Pillow：pip install pillow")

WIDTH, HEIGHT = 1600, 2400
PAPER = (246, 243, 234)
INK = (31, 41, 51)
ACCENT = (140, 111, 74)
MUTED = (138, 132, 120)

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJKsc-Bold.otf",
    "/usr/share/fonts/truetype/noto/NotoSerifCJKsc-Bold.otf",
    "/System/Library/Fonts/Songti.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Songti.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/msyh.ttc",
]


def find_font(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            sys.exit(f"字体文件不存在：{path}")
        return path
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return Path(candidate)
    sys.exit(
        "找不到中文字体。请用 --font 指定一个（例如 Noto Serif CJK SC、思源宋体、宋体），"
        "否则封面上的汉字会画成方框。"
    )


def centered(draw: ImageDraw.ImageDraw, y: int, text: str, font, fill, spacing: int = 0) -> int:
    """居中画一行字，返回这行的底边。Pillow 不做字距，所以逐字排。"""
    if not text:
        return y
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = (WIDTH - total) / 2
    for ch, width in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += width + spacing
    box = draw.textbbox((0, 0), text, font=font)
    return y + (box[3] - box[1])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--font", help="中文字体文件（ttf/otf/ttc）")
    parser.add_argument("--config", default=str(Path(__file__).parent / "book.json"))
    parser.add_argument("--out", default=str(Path(__file__).parent / "assets" / "cover.png"))
    args = parser.parse_args()

    meta = json.loads(Path(args.config).read_text(encoding="utf-8"))["metadata"]
    font_path = find_font(args.font)

    def font(size: int):
        return ImageFont.truetype(str(font_path), size)

    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)

    draw.rectangle([90, 90, WIDTH - 90, HEIGHT - 90], outline=ACCENT, width=3)

    centered(draw, 560, meta["title"], font(190), INK, spacing=26)
    subtitle = meta.get("subtitle", "")
    if len(subtitle) > 18:  # 太长就断成两行，别顶到边框
        cut = subtitle.rfind("，", 0, 20) + 1 or len(subtitle) // 2
        centered(draw, 880, subtitle[:cut].rstrip("，"), font(50), MUTED, spacing=8)
        centered(draw, 960, subtitle[cut:], font(50), MUTED, spacing=8)
    else:
        centered(draw, 880, subtitle, font(50), MUTED, spacing=8)

    # 全书总纲里的那张「上极／下极／一根轴」草图，直接搬到封面上。
    bar_w, bar_h = 760, 150
    bar_x = (WIDTH - bar_w) // 2
    for top in (1300, 1670):
        draw.rectangle([bar_x, top, bar_x + bar_w, top + bar_h], outline=ACCENT, width=4)
    draw.line([WIDTH // 2, 1450, WIDTH // 2, 1670], fill=ACCENT, width=4)
    centered(draw, 1348, "上极 · 人如何变强", font(48), MUTED, spacing=10)
    centered(draw, 1718, "下极 · 世界的底层语法", font(48), MUTED, spacing=10)

    centered(draw, HEIGHT - 380, meta.get("creator", ""), font(60), INK, spacing=18)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, "PNG", optimize=True)
    print(f"封面已生成：{out}  ({out.stat().st_size / 1024:.0f} KB, {WIDTH}×{HEIGHT})")


if __name__ == "__main__":
    main()
