"""The player's update check and its UPDATE button.

Releases are read from GitHub; a newer one is offered. The update itself
goes through whatever installed the player: pipx (the Linux path, and
Windows with Python) reinstalls the exact version and the player restarts;
the Windows executable downloads bitComposer-setup.exe from the release and
launches it, then quits so the installer can replace the files. A checkout
or a plain pip install is told what to run instead. A pre-release player
sees pre-releases; a release player sees releases only.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

RELEASES_URL = "https://api.github.com/repos/CatDogBark/bitComposer/releases?per_page=10"
RELEASES_PAGE = "https://github.com/CatDogBark/bitComposer/releases"
INSTALLER_NAME = "bitComposer-setup.exe"
PACKAGE = "bitcomposer"


def parse_version(text: str) -> tuple:
    """'1.2.3' -> (1, 2, 3, inf) and '1.2.3rc2' -> (1, 2, 3, 2): a release
    sorts above its own candidates, candidates by their number."""
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)(?:(?:rc|b|a)(\d+))?$", text.strip())
    if not m:
        return ()
    nums = tuple(int(x) for x in m.groups()[:3])
    pre = m.group(4)
    return nums + ((int(pre),) if pre is not None else (float("inf"),))


def is_prerelease(text: str) -> bool:
    v = parse_version(text)
    return bool(v) and v[3] != float("inf")


def newer_release(current: str, fetch=None) -> dict | None:
    """The newest release above `current`, as {"version", "tag", "page",
    "installer"} or None. fetch(url) -> bytes is replaceable for tests."""
    fetch = fetch or (lambda url: urllib.request.urlopen(url, timeout=6).read())
    try:
        releases = json.loads(fetch(RELEASES_URL).decode("utf-8"))
    except Exception:
        return None
    cur = parse_version(current)
    want_pre = is_prerelease(current)
    best = None
    for r in releases:
        if r.get("draft"):
            continue
        if r.get("prerelease") and not want_pre:
            continue
        v = parse_version(r.get("tag_name", ""))
        if not v or v <= cur:
            continue
        if best is None or v > parse_version(best["tag"]):
            installer = next((a.get("browser_download_url") for a in r.get("assets", []) if a.get("name") == INSTALLER_NAME), None)
            best = {"version": r["tag_name"].lstrip("v"), "tag": r["tag_name"], "page": r.get("html_url", RELEASES_PAGE),
                    "installer": installer}
    return best


def install_kind() -> str:
    """How this player was installed: "frozen" (the Windows executable),
    "pipx" (a pipx venv), or "other" (a checkout, a plain pip)."""
    if getattr(sys, "frozen", False):
        return "frozen"
    exe = Path(sys.executable).resolve()
    if "pipx" in exe.parts and "venvs" in exe.parts:
        return "pipx"
    return "other"


def pipx_command():
    import shutil
    pipx = shutil.which("pipx")
    if pipx:
        return [pipx]
    # pipx's own interpreter runs it as a module when the command is not on PATH
    home = Path.home()
    for cand in (home / ".local/bin/pipx", home / ".local/bin/pipx.exe"):
        if cand.exists():
            return [str(cand)]
    return None


def apply_update(release: dict, log, restart=None) -> bool:
    """Do the update. Returns True when the player should quit (an installer
    or a restart is taking over). log(str) reports progress."""
    kind = install_kind()
    if kind == "frozen":
        if not release.get("installer"):
            log(f"no installer on release {release['tag']}: {release['page']}")
            return False
        try:
            target = Path(tempfile.gettempdir()) / INSTALLER_NAME
            log(f"downloading {INSTALLER_NAME}…")
            urllib.request.urlretrieve(release["installer"], target)
            log("starting the installer")
            os.startfile(str(target))                 # noqa: S606 - the release's own installer
            return True
        except Exception as e:
            log(f"update failed: {e}; get it at {release['page']}")
            return False
    if kind == "pipx":
        cmd = pipx_command()
        if not cmd:
            log("pipx not found; run:  pipx install --force bitcomposer==" + release["version"])
            return False
        log(f"pipx install --force {PACKAGE}=={release['version']} …")
        proc = subprocess.run(cmd + ["install", "--force", f"{PACKAGE}=={release['version']}"],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            log("pipx failed: " + (proc.stderr or proc.stdout).strip().splitlines()[-1:][0] if (proc.stderr or proc.stdout).strip() else "pipx failed")
            return False
        log(f"updated to {release['version']}, restarting")
        if restart:
            restart()
        return True
    log(f"this copy was not installed by pipx or the installer; update it yourself: {release['page']}")
    return False


def restart_self() -> None:
    """Replace this process with a fresh one on the same command."""
    exe = Path(sys.argv[0])
    if exe.name.startswith("bitcomposer-player") and exe.exists():
        os.execv(str(exe), [str(exe)] + sys.argv[1:])
    os.execv(sys.executable, [sys.executable, "-m", "bitcomposer.player"] + sys.argv[1:])
