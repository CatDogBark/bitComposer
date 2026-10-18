"""The player's command line: `bitcomposer-player` opens the window (Qt,
in app.py and qml/Main.qml); `--check` reports what it needs and exits;
`--install-desktop` and `--remove-desktop` write and remove the Linux
app-menu entry (the first launch adds it by itself); `--screenshot` renders
the window offscreen at a given screen size and scale and exits.
"""
import argparse
import sys

from .. import __version__
from .engine import default_music_dir
from .openmpt import LibraryMissing, lib as openmpt_lib
from .audio import make_output, OutputUnavailable
from . import desktop

QT_HINT = "PySide6 is missing: the player's window needs it. pipx install --force bitcomposer puts it back"


def check() -> int:
    """Report what the player needs and exit: Qt, libopenmpt, an audio output, the music folder."""
    ok = True
    try:
        import PySide6
        from PySide6 import QtQuick  # noqa: F401
        print(f"Qt (PySide6 {PySide6.__version__}): ok")
    except ImportError as e:
        print(f"Qt: MISSING ({QT_HINT}; {e})"); ok = False
    try:
        openmpt_lib()
        print("libopenmpt: ok")
    except LibraryMissing as e:
        print(f"libopenmpt: MISSING ({e})"); ok = False
    try:
        out = make_output(48000)
        print(f"audio output: ok ({type(out).__name__}{' via ' + out.command if hasattr(out, 'command') else ''})")
    except OutputUnavailable as e:
        print(f"audio output: MISSING ({e})"); ok = False
    print(f"music folder: {default_music_dir()}")
    print(f"bitcomposer {__version__}")
    return 0 if ok else 1


def install_desktop() -> int:
    """Write the app-menu entry and its icon (Linux). The first launch does
    this by itself (desktop.py); this is for putting a removed one back."""
    if not sys.platform.startswith("linux"):
        print("desktop entries are a Linux thing; on Windows the installer makes the Start menu entry")
        return 1
    cmd = desktop.launch_command() or f"{sys.executable} -m bitcomposer.player"
    entry = desktop.write_entry(f'"{cmd}"' if " " in cmd else cmd)
    desktop.announce_icons()
    print(f"wrote {entry} (runs {cmd})")
    return 0


def remove_desktop() -> int:
    gone = desktop.remove_entry()
    print("removed " + ", ".join(map(str, gone)) if gone else "no app-menu entry to remove")
    return 0


def _size(text: str) -> tuple[int, int]:
    try:
        w, h = text.lower().split("x")
        return int(w), int(h)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected WIDTHxHEIGHT in pixels, got {text!r}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="bitcomposer-player", description="bitComposer: the player")
    ap.add_argument("--check", action="store_true", help="report Qt, libopenmpt, the audio output and the music folder, then exit")
    ap.add_argument("--install-desktop", action="store_true", help="write the app-menu entry (Linux; the first launch does it by itself) and exit")
    ap.add_argument("--remove-desktop", action="store_true", help="remove the app-menu entry (Linux), e.g. before pipx uninstall, and exit")
    ap.add_argument("--music-dir", help="folder of songs (default: $BITCOMPOSER_MUSIC_DIR, ~/Music/Chiptune if it exists, else ~/Music/bitComposer)")
    ap.add_argument("--screenshot", metavar="PNG", help="render the window offscreen to PNG and exit (with a few fresh songs, nothing played)")
    ap.add_argument("--screen", type=_size, default=(1920, 1080), metavar="WxH", help="with --screenshot: the screen in physical pixels (default 1920x1080)")
    ap.add_argument("--scale", type=float, default=1.0, help="with --screenshot: the display scaling, 1.5 for 150%% (default 1)")
    ap.add_argument("--panels", default="", help="with --screenshot: panels to open, comma-separated: settings, mix")
    ap.add_argument("--version", action="version", version=f"bitcomposer {__version__}")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    if args.install_desktop:
        return install_desktop()
    if args.remove_desktop:
        return remove_desktop()
    try:
        openmpt_lib()
    except LibraryMissing as e:
        print(e, file=sys.stderr)
        return 1
    try:
        from .app import run
    except ImportError as e:
        print(f"{QT_HINT} ({e})", file=sys.stderr)
        return 1
    return run(args.music_dir, screenshot=args.screenshot, screen=args.screen, scale=args.scale, panels=args.panels)


if __name__ == "__main__":
    sys.exit(main())
