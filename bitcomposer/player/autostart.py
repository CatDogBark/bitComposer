"""Start at login, minimised to the tray and not playing: the media keys
and the tray work from there, the way the companion daemon was always
there for the widget.

Linux: an XDG autostart entry (~/.config/autostart/bitcomposer-player.
desktop), which Plasma, GNOME and the other desktops read. Windows: the
per-user Run key. Only an installed copy can be started this way (the
pipx command, the frozen executable); a checkout run is told so.
"""
import os
import sys
from pathlib import Path

from . import desktop

ENTRY = "bitcomposer-player.desktop"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "bitComposer"


def _xdg_file() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "autostart" / ENTRY


def _windows_exe() -> str | None:
    if getattr(sys, "frozen", False):
        return sys.executable
    argv0 = Path(sys.argv[0])
    if argv0.name.lower() in ("bitcomposer-player.exe", "bitcomposer-player") and argv0.exists():
        return str(argv0.absolute())
    return None


def command() -> str | None:
    """What a login would run, or None when this copy cannot be started that way."""
    if os.environ.get("FLATPAK_ID"):
        return None                    # a Flatpak asks the Background portal instead (not yet)
    if sys.platform.startswith("win"):
        exe = _windows_exe()
        return f'"{exe}" --minimized' if exe else None
    if sys.platform.startswith("linux"):
        cmd = desktop.launch_command()
        return f'{desktop._quote(cmd)} --minimized' if cmd else None
    return None


def supported() -> bool:
    return command() is not None


def is_enabled() -> bool:
    if sys.platform.startswith("win"):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
                winreg.QueryValueEx(k, RUN_VALUE)
            return True
        except OSError:
            return False
    return _xdg_file().exists()


def set_enabled(on: bool) -> str:
    """Turn it on or off. Returns "" or what went wrong."""
    cmd = command()
    if on and cmd is None:
        return "start at login needs an installed copy (pipx or the installer)"
    try:
        if sys.platform.startswith("win"):
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                if on:
                    winreg.SetValueEx(k, RUN_VALUE, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(k, RUN_VALUE)
                    except FileNotFoundError:
                        pass
            return ""
        f = _xdg_file()
        if on:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(
                "[Desktop Entry]\nType=Application\nName=bitComposer\n"
                "Comment=bitComposer in the tray, for the media keys and the next song\n"
                f"Exec={cmd}\nIcon=bitcomposer\nTerminal=false\nX-GNOME-Autostart-enabled=true\n"
                f"{desktop.MARK}\n")
        elif f.exists():
            f.unlink()
        return ""
    except OSError as e:
        return f"could not change start at login: {e}"
