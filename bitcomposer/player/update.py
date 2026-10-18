"""The player's update check and its UPDATE button.

Releases are read from GitHub; a newer one is offered. The update itself
goes through whatever installed the player: pipx (the Linux path, and
Windows with Python) reinstalls the exact version and the player restarts;
the Windows executable downloads bitComposer-setup.exe from the release and
runs it quietly, then quits so the installer can replace the files and
start the new player. A checkout
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


def local_release(path: str, current: str) -> dict:
    """A stand-in newer release made from a file on this machine, for trying
    the UPDATE button without publishing a release: a setup.exe for the
    Windows build (`bitComposer.exe --try-update setup.exe`, downloaded as a
    file:// URL like any other), or a wheel for a pipx install
    (`bitcomposer-player --try-update bitcomposer-X.whl`, installed by spec)."""
    p = Path(path).expanduser().resolve()
    # a wheel's name carries its version (bitcomposer-1.0.0-py3-none-any.whl)
    parts = p.name.split("-")
    version = parts[1] if p.suffix.lower() == ".whl" and len(parts) > 2 else current
    rel = {"version": f"{version} (test)", "tag": "local", "page": p.parent.as_uri(), "installer": None}
    if p.suffix.lower() == ".exe":
        rel["installer"] = p.as_uri()
    else:
        rel["spec"] = str(p)
    return rel


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
    "pipx" (a pipx venv), or "other" (a checkout, a plain pip). pipx is told
    by the metadata file it keeps at its venv's root: the venv's python is a
    link to the system one, so where the interpreter lives says nothing
    (that check, through resolve(), called every pipx install "other")."""
    if getattr(sys, "frozen", False):
        return "frozen"
    if (Path(sys.prefix) / "pipx_metadata.json").exists():
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


# pipx --verbose prefixes its own log lines with the function they came from;
# the update screen shows the message. Pictographs are dropped too: the
# window's font has none.
_PIPX_PREFIX = re.compile(r"^pipx >\([\w.]+:\d+\): ")
_PICTOGRAPHS = re.compile("[\u2600-\u27bf\ufe0f\U0001f000-\U0001ffff]")


def clean_line(line: str) -> str:
    return _PICTOGRAPHS.sub("", _PIPX_PREFIX.sub("", line.rstrip())).rstrip()


def apply_update(release: dict, report, restart=None) -> bool:
    """Do the update. report(text, progress) gives the update screen a log
    line and, when known, how far along it is (0 to 1; None: still going).
    Returns True when the player should quit (an installer or a restart is
    taking over)."""
    kind = install_kind()
    if kind == "frozen":
        url = release.get("installer")
        if not url:
            report(f"no installer on release {release['tag']}: {release['page']}", None)
            return False
        try:
            target = Path(tempfile.gettempdir()) / INSTALLER_NAME
            report(f"downloading {url}", 0.0)
            shown = [-1]

            def hook(blocks, block_size, total):
                if total > 0:
                    got = min(total, blocks * block_size)
                    pct = int(got * 100 / total)
                    if pct >= shown[0] + 5 or pct == 100:
                        shown[0] = pct
                        report(f"  {pct:3d}%   {got / 1e6:5.1f} of {total / 1e6:.1f} MB", got / total)
            urllib.request.urlretrieve(url, target, reporthook=hook)
            report("starting the installer: it shows its own progress, then reopens bitComposer", 1.0)
            # Quietly (a progress window, no questions), closing this player,
            # then starting the new one (installer.iss). startfile, not Popen:
            # an all-users install needs the elevation prompt, which only the
            # shell raises.
            os.startfile(str(target), "open", "/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RELAUNCH=1")  # noqa: S606
            return True
        except Exception as e:
            report(f"update failed: {e}", None)
            report(f"get it at {release['page']}", None)
            return False
    if kind == "pipx":
        cmd = pipx_command()
        spec = release.get("spec") or f"{PACKAGE}=={release['version']}"
        if not cmd:
            report(f"pipx not found; run:  pipx install --force {spec}", None)
            return False
        report("$ pipx install --force " + spec, None)
        code, missing = _pipx_install(cmd, spec, report)
        if code and missing:
            # pip keeps PyPI's list of versions for a while, and a list saved
            # before this release went up does not have it: on 1.0.0 the
            # player saw the release on GitHub while pip's saved list ended
            # at rc6. Once more without pip's saved copies. Not every time:
            # they are also what spares an update downloading Qt again.
            report("pip's saved list of PyPI's versions is older than this release; asking PyPI again", None)
            report("$ PIP_NO_CACHE_DIR=1 pipx install --force " + spec, None)
            code, missing = _pipx_install(cmd, spec, report, PIP_NO_CACHE_DIR="1")
        if code is None:
            return False
        if code != 0:
            if missing:
                report(f"PyPI does not list {release['version']} yet; that can take a few minutes after a release, "
                       "so try UPDATE again later", None)
            report(f"pipx exited with {code}; the player is unchanged", None)
            return False
        report(f"updated to {release['version']}; restarting", 1.0)
        if restart:
            restart()
        return True
    report("this copy was not installed by pipx or the installer (a checkout, or a plain pip),", None)
    report(f"so update it the way it was installed. The release: {release['page']}", None)
    return False


# What pip says when the index it read has no such version.
_NO_SUCH_VERSION = re.compile(r"No matching distribution found for|Could not find a version that satisfies the requirement")


def _pipx_install(cmd: list[str], spec: str, report, **env) -> tuple[int | None, bool]:
    """pipx install --force spec, its output to report line by line. Returns
    pipx's exit code (None: it would not start) and whether pip said the
    index has no such version."""
    missing = False
    try:
        proc = subprocess.Popen(cmd + ["install", "--force", "--verbose", spec], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1,
                                env=dict(os.environ, PYTHONUNBUFFERED="1", **env))
        for raw in proc.stdout:
            text = clean_line(raw)
            if text:
                missing = missing or bool(_NO_SUCH_VERSION.search(text))
                report(text, None)
        return proc.wait(), missing
    except OSError as e:
        report(f"could not run pipx: {e}", None)
        return None, False


def restart_self() -> None:
    """Replace this process with a fresh one on the same command, less the
    options that only made sense once: a test release (it would be offered
    again) and a hidden start (the window was open for the update)."""
    args, rest = [], iter(sys.argv[1:])
    for a in rest:
        if a == "--try-update":
            next(rest, None)
        elif not a.startswith("--try-update=") and a != "--minimized":
            args.append(a)
    exe = Path(sys.argv[0])
    if exe.name.startswith("bitcomposer-player") and exe.exists():
        os.execv(str(exe), [str(exe)] + args)
    os.execv(sys.executable, [sys.executable, "-m", "bitcomposer.player"] + args)
