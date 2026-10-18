"""Render the app icon (bitcomposer/player/icons/bitcomposer.svg) into a
Windows .ico for the executable and the installer, at the sizes Explorer and
the taskbar ask for. The .ico is built, not kept: the SVG is the source.

    python tools/windows/make_icon.py build/bitcomposer.ico
"""
import os
import struct
import sys
from pathlib import Path

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
SVG = Path(__file__).resolve().parents[2] / "bitcomposer" / "player" / "icons" / "bitcomposer.svg"


def main(out: str) -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
    from PySide6.QtGui import QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    app = QGuiApplication([])  # noqa: F841  (QPainter wants one)
    renderer = QSvgRenderer(str(SVG))
    if not renderer.isValid():
        print(f"cannot read {SVG}", file=sys.stderr)
        return 1
    pngs = []
    for size in SIZES:
        img = QImage(size, size, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        renderer.render(p)
        p.end()
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QIODevice.WriteOnly)
        img.save(buf, "PNG")
        pngs.append((size, bytes(data)))
    # ICONDIR, one ICONDIRENTRY per size, then the PNGs (Vista+ reads PNG entries).
    head = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, blobs = b"", b""
    for size, png in pngs:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        blobs += png
        offset += len(png)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(head + entries + blobs)
    print(f"wrote {out} ({', '.join(str(s) for s in SIZES)} px)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "build/bitcomposer.ico"))
