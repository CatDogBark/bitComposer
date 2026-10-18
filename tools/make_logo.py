"""Write the bitComposer logo: the bit tile beside the [bit]Composer name, as
self-contained SVG (the letters are JetBrains Mono outlines, so the logo
needs no font wherever it is shown). Two variants: docs/images/logo-dark.svg
for dark backgrounds and docs/images/logo-light.svg for light ones; the
README picks one by the reader's colour scheme.

    python tools/make_logo.py        (needs fontTools: pip install fonttools)

The name style is the bit family's: [ and ] dim, bit bold mint, the
product name light (see the brand notes); the tile is the app icon.
"""
import re
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "bitcomposer" / "player" / "fonts"
ICON = ROOT / "bitcomposer" / "player" / "icons" / "bitcomposer.svg"
OUT = ROOT / "docs" / "images"

THEMES = {
    "dark": {"bracket": "#2f8f5f", "bit": "#00ff88", "name": "#b0ddcc"},
    "light": {"bracket": "#5a9a78", "bit": "#0b7a47", "name": "#0e1612"},
}
TILE = 256           # the icon's own units
GAP = 56             # tile to text
SIZE = 150           # font size in the same units
NAME = "Composer"


def glyph_path(font: TTFont, ch: str) -> tuple[str, int]:
    gs = font.getGlyphSet()
    name = font.getBestCmap()[ord(ch)]
    pen = SVGPathPen(gs)
    gs[name].draw(pen)
    return pen.getCommands(), gs[name].width


def run(text_parts, x0: float, baseline: float, scale: float) -> tuple[list[str], float]:
    """text_parts: (font, string, colour). Returns the <path>s and the end x."""
    out, x = [], x0
    for font, text, colour in text_parts:
        for ch in text:
            d, adv = glyph_path(font, ch)
            if d:
                out.append(f'<path fill="{colour}" transform="translate({x:.2f} {baseline:.2f}) scale({scale:.5f} {-scale:.5f})" d="{d}"/>')
            x += adv * scale
    return out, x


def main() -> int:
    regular = TTFont(FONTS / "JetBrainsMono-Regular.ttf")
    bold = TTFont(FONTS / "JetBrainsMono-Bold.ttf")
    upm = regular["head"].unitsPerEm
    cap = regular["OS/2"].sCapHeight
    scale = SIZE / upm
    baseline = TILE / 2 + cap * scale / 2          # caps centred on the tile
    icon = ICON.read_text()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", icon, re.S).group(1)
    inner = re.sub(r"<!--.*?-->", "", inner, flags=re.S).strip()
    OUT.mkdir(parents=True, exist_ok=True)
    for theme, c in THEMES.items():
        paths, end = run([(regular, "[", c["bracket"]), (bold, "bit", c["bit"]),
                          (regular, "]", c["bracket"]), (regular, NAME, c["name"])],
                         TILE + GAP, baseline, scale)
        width = round(end + 8)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{TILE}" viewBox="0 0 {width} {TILE}" '
               f'role="img" aria-label="bitComposer">\n'
               f'<title>bitComposer</title>\n'
               f'<g>{inner}</g>\n'                    # the tile, in its own 256 units
               + "\n".join(paths) + "\n</svg>\n")
        (OUT / f"logo-{theme}.svg").write_text(svg)
        print(f"wrote {OUT / f'logo-{theme}.svg'} ({width}x{TILE})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
