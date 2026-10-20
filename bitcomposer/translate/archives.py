"""A game's SPC files, wherever they are kept: a folder, a zip, or the
archives SPC sets come in (snesmusic.org's .rsn is a RAR archive; .rar
and .7z too).

A zip Python opens itself. The others are unpacked by an archive program
already on the machine, 7-Zip (7z, 7zz) or unar, found where it is
installed; bitComposer never ships one (decided 2026-10-20). Without
either, importing one says what to install.

Only SPC files are kept, each by its own name (two of one name get (2),
(3)), so nothing an archive names can land outside the folder it is
unpacked into; the program unpacks into a folder of its own first, and
only regular files found inside it are taken."""
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ZIP = (".zip",)
BY_PROGRAM = (".rsn", ".rar", ".7z")             # unpacked by 7-Zip or unar
SONGS = 2000                                    # SPC files an archive may hold: far more than any game's
SPC_BYTES = 1 << 20                             # a file bigger than this is no snapshot (one is 64 KB of RAM and a header)
UNPACKED_BYTES = 512 << 20                      # all an archive may unpack to
SECONDS = 300                                   # an archive program's time, at most
INSTALL = ("7-Zip or unar: on Debian or Ubuntu `sudo apt install 7zip` (or `unar`), "
           "on Windows 7-Zip from 7-zip.org")


def is_archive(path) -> bool:
    return Path(path).suffix.lower() in ZIP + BY_PROGRAM


def spc_files(paths, unpack_to: Path) -> list[Path]:
    """The SPC files to read: each file given, each folder's own (not its
    subfolders': a parent of several games would mix them), and every one
    in an archive, its folders too (an archive is one game's set),
    unpacked into unpack_to/<the archive's name>."""
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.suffix.lower() == ".spc" and f.is_file())
        elif p.suffix.lower() in ZIP:
            files += _unzip(p, unpack_to / p.stem)
        elif p.suffix.lower() in BY_PROGRAM:
            files += unpack(p, unpack_to / p.stem)
        else:
            files.append(p)
    return files


def _keep(name: str, into: Path) -> Path:
    """Where an SPC file of this name goes in `into`: its own name, or (2), (3)."""
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    target, n = into / name, 2
    while target.exists():
        target, n = into / f"{Path(name).stem} ({n}){Path(name).suffix}", n + 1
    return target


def _unzip(path: Path, into: Path) -> list[Path]:
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as e:
        raise ValueError(f"{path.name}: not a zip file ({e})") from None
    out = []
    with z:
        members = sorted((m for m in z.infolist() if not m.is_dir() and m.filename.lower().endswith(".spc")),
                         key=lambda m: m.filename.lower())
        if len(members) > SONGS:
            raise ValueError(f"{path.name}: {len(members)} SPC files, more than one game's")
        into.mkdir(parents=True, exist_ok=True)
        for m in members:
            if m.file_size > SPC_BYTES:
                continue
            target = _keep(m.filename, into)
            with z.open(m) as fin, open(target, "wb") as fout:
                shutil.copyfileobj(fin, fout)
            out.append(target)
    return out


def program() -> tuple[str, str] | None:
    """The archive program on this machine: ("7z", its path) or ("unar", its path)."""
    for name in ("7z", "7zz"):
        found = shutil.which(name)
        if found:
            return "7z", found
    if sys.platform.startswith("win"):
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            exe = Path(base) / "7-Zip" / "7z.exe" if base else None
            if exe and exe.is_file():
                return "7z", str(exe)
    unar, lsar = shutil.which("unar"), shutil.which("lsar")
    if unar and lsar:
        return "unar", unar
    return None


def _run(cmd: list[str], what: str) -> str:
    try:
        done = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=SECONDS)
    except subprocess.TimeoutExpired:
        raise ValueError(f"{what}: the archive program took too long") from None
    except OSError as e:
        raise ValueError(f"{what}: cannot run {cmd[0]} ({e})") from None
    if done.returncode != 0:
        lines = (done.stderr or done.stdout).strip().splitlines()
        raise ValueError(f"{what}: cannot unpack it ({lines[-1] if lines else 'exit ' + str(done.returncode)})")
    return done.stdout


def _size(kind: str, exe: str, path: Path) -> int:
    """What the archive unpacks to, in bytes, from its listing."""
    if kind == "7z":
        out = _run([exe, "l", "-slt", "-ba", "-pnone", str(path)], path.name)
        return sum(int(line.split("=", 1)[1]) for line in out.splitlines()
                   if line.startswith("Size = ") and line.split("=", 1)[1].strip().isdigit())
    lsar = str(Path(exe).with_name("lsar" + Path(exe).suffix))
    listing = json.loads(_run([lsar, "-j", str(path)], path.name) or "{}")
    return sum(int(e.get("XADFileSize") or 0) for e in listing.get("lsarContents", []))


def unpack(path: Path, into: Path, tool: tuple[str, str] | None = None) -> list[Path]:
    """An archive's SPC files, unpacked by the machine's archive program."""
    tool = tool or program()
    if not tool:
        raise ValueError(f"{path.name}: unpacking it needs an archive program, {INSTALL}")
    kind, exe = tool
    if _size(kind, exe, path) > UNPACKED_BYTES:
        raise ValueError(f"{path.name}: too big for one game's set")
    raw = into.parent / f".raw-{into.name}"
    shutil.rmtree(raw, ignore_errors=True)
    raw.mkdir(parents=True)
    try:
        if kind == "7z":                         # -pnone: a locked archive fails instead of asking
            _run([exe, "x", "-y", "-bd", "-pnone", f"-o{raw}", str(path)], path.name)
        else:
            _run([exe, "-q", "-f", "-D", "-p", "", "-o", str(raw), str(path)], path.name)
        root = raw.resolve()
        found = []
        for dirpath, dirs, names in os.walk(raw):          # no links followed
            for n in names:
                f = Path(dirpath) / n
                if n.lower().endswith(".spc") and f.is_file() and not f.is_symlink() \
                        and root in f.resolve().parents and f.stat().st_size <= SPC_BYTES:
                    found.append(f)
        if len(found) > SONGS:
            raise ValueError(f"{path.name}: {len(found)} SPC files, more than one game's")
        into.mkdir(parents=True, exist_ok=True)
        out = []
        for f in sorted(found, key=lambda f: str(f.relative_to(raw)).lower()):
            target = _keep(f.name, into)
            shutil.move(f, target)
            out.append(target)
        return out
    finally:
        shutil.rmtree(raw, ignore_errors=True)
