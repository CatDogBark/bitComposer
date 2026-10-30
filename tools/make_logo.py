"""Write the bitComposer logo: the bit tile beside the [BIT]Composer name, as
self-contained SVG (the letters are font outlines, so the logo needs no font
wherever it is shown). Two variants: docs/images/logo-dark.svg for dark
backgrounds and docs/images/logo-light.svg for light ones; the README picks
one by the reader's colour scheme.

    python tools/make_logo.py        (needs fontTools: pip install fonttools)

The name (2026-10-30) is cut from the window's own material, as the tile is:
chrome brackets in JetBrains Mono Bold, the left in the window's bevel light
and the right in its edge grey, with a bevel-dark drop on the dark logo;
BIT in Silkscreen Bold, the player's pixel face, in the brand's pink; then
Composer in JetBrains Mono Bold in the text colour. The tile is the app icon.
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
    "dark": {"left": "#8a8898", "right": "#5a5968", "drop": "#0a0a0e", "bit": "#ff0055", "name": "#e8e6f0"},
    "light": {"left": "#5a5968", "right": "#3a3946", "drop": None, "bit": "#d8004a", "name": "#1a1c22"},
}
TILE = 256           # the icon's own units
GAP = 56             # tile to text
SIZE = 150           # the mono's font size in the same units
PIXEL = 0.94         # the pixel face's size against the mono's: its caps sit a little under the mono's, as in the window
DROP = 0.06          # the brackets' drop shadow on the dark logo, of SIZE (the window's own label is flat)
NAME = "Composer"


def glyph_path(font: TTFont, ch: str) -> tuple[str, int]:
    gs = font.getGlyphSet()
    name = font.getBestCmap()[ord(ch)]
    pen = SVGPathPen(gs)
    gs[name].draw(pen)
    return pen.getCommands(), gs[name].width


def run(text_parts, x0: float, baseline: float) -> tuple[list[str], float]:
    """text_parts: (font, string, colour, scale, drop colour or None). Returns the <path>s and the end x; a drop
    is the same glyph first, in its colour, offset down and right by DROP of SIZE."""
    out, x = [], x0
    for font, text, colour, scale, drop in text_parts:
        for ch in text:
            d, adv = glyph_path(font, ch)
            if d and drop:
                out.append(f'<path fill="{drop}" transform="translate({x + DROP * SIZE:.2f} {baseline + DROP * SIZE:.2f}) '
                           f'scale({scale:.5f} {-scale:.5f})" d="{d}"/>')
            if d:
                out.append(f'<path fill="{colour}" transform="translate({x:.2f} {baseline:.2f}) scale({scale:.5f} {-scale:.5f})" d="{d}"/>')
            x += adv * scale
    return out, x


def main() -> int:
    bold = TTFont(FONTS / "JetBrainsMono-Bold.ttf")
    pixel = TTFont(FONTS / "Silkscreen-Bold.ttf")
    upm = bold["head"].unitsPerEm
    cap = bold["OS/2"].sCapHeight
    scale = SIZE / upm
    pixel_scale = PIXEL * SIZE / pixel["head"].unitsPerEm
    baseline = TILE / 2 + cap * scale / 2          # the mono's caps centred on the tile; BIT sits on the same baseline
    icon = ICON.read_text()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", icon, re.S).group(1)
    inner = re.sub(r"<!--.*?-->", "", inner, flags=re.S).strip()
    OUT.mkdir(parents=True, exist_ok=True)
    for theme, c in THEMES.items():
        paths, end = run([(bold, "[", c["left"], scale, c["drop"]), (pixel, "BIT", c["bit"], pixel_scale, None),
                          (bold, "]", c["right"], scale, c["drop"]), (bold, NAME, c["name"], scale, None)],
                         TILE + GAP, baseline)
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
