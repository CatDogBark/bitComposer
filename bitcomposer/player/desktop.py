"""The Linux app-menu entry for the player.

pip and pipx cannot run anything at install time, and a pipx venv's own
share/ is not where menus look, so the player adds its entry itself: the
first launch of an installed copy writes ~/.local/share/applications/
bitcomposer-player.desktop and the icon, and later launches repair the
entry if the program it names has moved. An entry the user removed stays
removed (`--install-desktop` brings it back), and one that is not marked
as ours (written by hand, or edited and the mark dropped) is left alone.
Nothing happens on Windows (the installer makes the Start menu entry), in
a frozen build or inside a Flatpak (the package ships its own).
"""
import os
import shutil
import sys
from pathlib import Path

from .engine import state_file

HERE = Path(__file__).resolve().parent
ENTRY_NAME = "bitcomposer-player.desktop"   # also the window's app id (app.py)
MARK = "X-bitComposer-Managed=true"


def _paths() -> tuple[Path, Path]:
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return data / "applications" / ENTRY_NAME, data / "icons" / "hicolor" / "scalable" / "apps" / "bitcomposer.svg"


def _flag() -> Path:
    """Exists once the player has written an entry, so a missing entry
    afterwards means the user removed it."""
    return state_file().parent / "desktop-entry"


def launch_command() -> str | None:
    """What the entry should run: the `bitcomposer-player` this process was
    started as, through PATH when PATH finds the same program (pipx's
    ~/.local/bin link survives a reinstall; the venv path behind it is an
    implementation detail). None for `python -m bitcomposer.player` from a
    checkout, which a menu cannot start."""
    argv0 = Path(sys.argv[0])
    if argv0.name != "bitcomposer-player" or not argv0.exists():
        return None
    shim = shutil.which("bitcomposer-player")
    if shim and Path(shim).resolve() == argv0.resolve():
        return shim
    return str(argv0.absolute())


def _quote(cmd: str) -> str:
    return f'"{cmd}"' if " " in cmd else cmd


def write_entry(cmd: str) -> Path:
    entry, icon = _paths()
    entry.parent.mkdir(parents=True, exist_ok=True)
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / "icons" / "bitcomposer.svg", icon)
    entry.write_text(
        "[Desktop Entry]\nType=Application\nName=bitComposer\nGenericName=Music generator\n"
        "Comment=Procedural 16-bit game music: plays and generates\n"
        f"Exec={cmd}\nIcon=bitcomposer\nTerminal=false\nCategories=AudioVideo;Audio;Music;\n"
        "Keywords=chiptune;tracker;music;generator;snes;\nStartupWMClass=bitcomposer-player\n"
        f"{MARK}\n")
    flag = _flag()
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text(str(entry) + "\n")
    return entry


def _exec_target(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("Exec="):
            value = line[5:].strip()
            if value.startswith('"'):
                return value[1:].split('"', 1)[0]
            return value.split(" ", 1)[0]
    return ""


def ensure_entry() -> str:
    """Called on every launch: "added" the first time, "repaired" when the
    entry named a program that is gone, "icon" when the installed icon is
    an older one, "" otherwise."""
    if not sys.platform.startswith("linux") or getattr(sys, "frozen", False) or os.environ.get("FLATPAK_ID"):
        return ""
    cmd = launch_command()
    if cmd is None:
        return ""
    entry, icon = _paths()
    if not entry.exists():
        if _flag().exists():
            return ""
        write_entry(_quote(cmd))
        return "added"
    text = entry.read_text(errors="replace")
    if MARK not in text:
        return ""
    target = _exec_target(text)
    if not target or not (Path(target).exists() or shutil.which(target)):
        write_entry(_quote(cmd))
        return "repaired"
    src = HERE / "icons" / "bitcomposer.svg"
    if not icon.exists() or icon.read_bytes() != src.read_bytes():
        icon.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, icon)          # a new icon in a new version reaches the menu too
        return "icon"
    return ""


def announce_icons() -> None:
    """Tell running KDE programs (the task manager, the menu) to look at
    icons again. The first launch creates hicolor/scalable/apps, and a
    theme directory that appears while plasmashell runs is not seen until
    it is told, so the window showed a "?" in the taskbar for that session.
    The same signal the icon settings page sends; nothing listens elsewhere."""
    try:
        from PySide6.QtCore import QCoreApplication
        from PySide6.QtDBus import QDBusConnection, QDBusMessage
    except ImportError:
        return
    app = QCoreApplication.instance() or QCoreApplication([])  # noqa: F841  (the bus wants one)
    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        return
    msg = QDBusMessage.createSignal("/KIconLoader", "org.kde.KIconLoader", "iconChanged")
    msg.setArguments([0])
    bus.send(msg)


def remove_entry() -> list[Path]:
    """The entry and the icon, before `pipx uninstall`. Returns what went."""
    gone = []
    for p in _paths():
        if p.exists():
            p.unlink()
            gone.append(p)
    return gone
