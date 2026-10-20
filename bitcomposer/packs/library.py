"""The packs on this machine, for the player's PACKS panel: imported from a
game's SPC files (the translator's thin pack, docs/TRANSLATOR.md), or added
from a pack folder or an exported pack. Each is a folder of its own in the
user's data folder, named as the pack: pack.json, its WAVs and, for an
imported one, translator.json (why each sample is where it is).

Importing a game again starts fresh: the pack is made anew, and changes
made to the old one go with it (decided 2026-10-20). To keep them, export
the pack first, one zip file of its folder, and add it back.

A pack is data only (packfile.py); a pack added from a zip is checked like
any pack file, and the zip itself may hold nothing but plain files, no
paths out of it."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
from pathlib import Path

from .packfile import KIT, POOLS, PackError, check_name, parse, unload, _NAME

PACK = "pack.json"
WHY = "translator.json"              # translate.pack.WHY, kept beside an imported pack
PARTS = ("lead", "alt_lead", "harmony", "counter", "arp", "bass")   # as the panel shows them
BASS = ("bass_heavy", "bass_medium", "bass_light")                   # one part, three pools
OUT = "out"                          # in the pack, in no part
STAGE = ".import-"                   # a pack being imported, beside the others until it is done
MAX_UNZIPPED = 256 * 1024 * 1024     # bytes an exported pack may unpack to
MAX_FILES = 600


class Exists(PackError):
    """A pack of that name is here already (add it again with replace)."""

    def __init__(self, name: str):
        super().__init__(f"a pack named {name} is here already")
        self.name = name


def data_dir() -> Path:
    """The user's data folder for bitComposer (BITCOMPOSER_DATA_DIR overrides it)."""
    env = os.environ.get("BITCOMPOSER_DATA_DIR")
    if env:
        return Path(env).expanduser()
    if sys.platform.startswith("win"):
        return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "bitComposer"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "bitcomposer"


def packs_dir() -> Path:
    return data_dir() / "packs"


def pack_file(name: str) -> Path:
    return packs_dir() / name / PACK


def _load(name: str) -> dict:
    path = pack_file(name)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise PackError(f"{name}: cannot read its pack file ({e})") from None


def _save(name: str, data: dict) -> None:
    """Write a pack's pack.json in place, once it checks."""
    folder = packs_dir() / name
    parse(data, folder, source=name)
    tmp = folder / (PACK + ".tmp")
    tmp.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, folder / PACK)
    unload(name)


def parts(data: dict) -> tuple[dict, dict, list]:
    """A pack's voices as the panel shows them: {part: [voice, ...]} (each
    once, most drawn first; the three bass pools as one), {piece: voice},
    and the pack's own samples in neither."""
    voices = data.get("voices") or {}
    out = {}
    for part in PARTS:
        drawn = {}
        for pool in BASS if part == "bass" else (part,):
            for v in voices.get(pool) or []:
                drawn[v] = drawn.get(v, 0) + 1
        if drawn:
            out[part] = sorted(drawn, key=lambda v: -drawn[v])
    kit = dict(voices.get("drums") or {})
    used = {v for vs in out.values() for v in vs} | set(kit.values())
    return out, kit, [v for v in data.get("samples") or {} if v not in used]


def is_drum(spec: dict) -> bool:
    return bool(spec.get("percussion")) or ("note" not in spec and "hz" not in spec)


def listing() -> list[dict]:
    """The packs here, by name: what the panel shows of each."""
    root = packs_dir()
    out = []
    for folder in sorted(root.iterdir()) if root.is_dir() else []:
        if folder.name.startswith(".") or not (folder / PACK).is_file():
            continue
        try:
            data = _load(folder.name)
        except PackError:
            continue
        why = {}
        if (folder / WHY).is_file():
            try:
                why = json.loads((folder / WHY).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                why = {}
        tonal, kit, left = parts(data)
        samples = data.get("samples") or {}
        out.append({"name": folder.name, "label": data.get("label", folder.name), "path": str(folder / PACK),
                    "songs": why.get("songs"), "samples": len(samples), "parts": tonal, "kit": kit, "out": left,
                    "drums": [v for v, s in samples.items() if is_drum(s)], "why": why.get("why", {})})
    return out


def move(name: str, voice: str, to: str) -> None:
    """Put one of a pack's samples in another part (a pitched sample), kit
    piece (a drum) or OUT. A kit piece holds one drum: the one it held goes
    out. A sample keeps how often its part drew it."""
    data = _load(name)
    samples = data.get("samples") or {}
    if voice not in samples:
        raise PackError(f"{name}: {voice} is not one of the pack's samples")
    drum = is_drum(samples[voice])
    allowed = (KIT if drum else PARTS) + (OUT,)
    if to not in allowed:
        raise PackError(f"{voice} is {'a drum' if drum else 'a pitched sample'}: it goes to {', '.join(allowed)}")
    voices = data.setdefault("voices", {})
    weight = 1
    for pool in POOLS:
        if voice in (voices.get(pool) or []):
            weight = max(weight, voices[pool].count(voice))
            voices[pool] = [v for v in voices[pool] if v != voice]
            if not voices[pool]:
                del voices[pool]
    kit = voices.get("drums") or {}
    for piece in [p for p, v in kit.items() if v == voice]:
        del kit[piece]
    if to in KIT:
        kit[to] = voice
    elif to != OUT:
        for pool in BASS if to == "bass" else (to,):
            voices.setdefault(pool, []).extend([voice] * weight)
    if kit:
        voices["drums"] = kit
    else:
        voices.pop("drums", None)
    _save(name, data)


def rename(name: str, new: str) -> None:
    if not _NAME.match(new or ""):
        raise PackError("a pack's name is lower-case letters, digits and _, starting with a letter, at most 24")
    check_name(new, source=new)
    if (packs_dir() / new).exists():
        raise Exists(new)
    data = _load(name)
    data["name"] = new
    _save(name, data)
    os.replace(packs_dir() / name, packs_dir() / new)
    unload(name)


def delete(name: str) -> None:
    folder = packs_dir() / name
    if not (folder / PACK).is_file() or folder.parent != packs_dir():
        raise PackError(f"no pack named {name}")
    unload(name)
    shutil.rmtree(folder)


def _files(base: Path, data: dict) -> list[str]:
    """The files a pack is: its pack file, its samples' WAVs and why they are where they are."""
    names = [PACK] + ([WHY] if (base / WHY).is_file() else [])
    for key, spec in (data.get("samples") or {}).items():
        f = spec.get("file") if isinstance(spec, dict) else None
        if not isinstance(f, str) or Path(f).is_absolute() or ".." in Path(f).parts or "\\" in f:
            raise PackError(f"samples.{key}.file: a file beside the pack file, in it or a folder under it")
        names.append(f)
    return list(dict.fromkeys(names))


def export(name: str, dest) -> Path:
    """The pack as one zip file of its folder's files, for ADD to bring back."""
    folder = packs_dir() / name
    dest = Path(dest)
    if dest.suffix.lower() != ".zip":
        dest = dest.with_name(dest.name + ".zip")
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for f in _files(folder, _load(name)):
            z.write(folder / f, f)
    return dest


def _unzip(src: Path, into: Path) -> Path:
    """An exported pack's files (plain names, nothing outside the zip), and
    the folder its pack file is in (the zip's top, or one folder down)."""
    with zipfile.ZipFile(src) as z:
        members = [m for m in z.infolist() if not m.is_dir()]
        if len(members) > MAX_FILES or sum(m.file_size for m in members) > MAX_UNZIPPED:
            raise PackError(f"{src.name}: too big for a pack")
        for m in members:
            parts_ = Path(m.filename).parts
            if Path(m.filename).is_absolute() or ".." in parts_ or "\\" in m.filename:
                raise PackError(f"{src.name}: {m.filename}: not a file a pack holds")
            target = into.joinpath(*parts_)
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(m) as fin, open(target, "wb") as fout:
                shutil.copyfileobj(fin, fout)
    if (into / PACK).is_file():
        return into
    found = [p.parent for p in into.glob(f"*/{PACK}")]
    if len(found) == 1:
        return found[0]
    raise PackError(f"{src.name}: no {PACK} in it")


def add(src, replace: bool = False) -> str:
    """Bring a pack in: an exported pack (a zip), a pack's folder, or its
    pack file. Checked whole before anything is copied; returns its name."""
    src = Path(src).expanduser()
    root = packs_dir()
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root, prefix=".add-") as tmp:
        tmp = Path(tmp)
        if src.is_dir():
            base, file = src, src / PACK
        elif src.suffix.lower() == ".zip":
            base = _unzip(src, tmp / "in")
            file = base / PACK
        else:
            base, file = src.parent, src
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise PackError(f"{src}: not a pack ({e})") from None
        pack, _ = parse(data, base, source=str(src))
        name = check_name(pack["name"], source=str(src))
        target = root / name
        if target.exists() and not replace:
            raise Exists(name)
        stage = tmp / "pack"
        for f in _files(base, data):
            (stage / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(base / (f if f != PACK else file.name), stage / f)
        if target.exists():
            shutil.rmtree(target)
        os.replace(stage, target)
    unload(name)
    return name


def can_import() -> bool:
    """Whether this machine has the SNES emulator an import runs on."""
    from ..spc import emulate
    return emulate.available()


class Import:
    """A game's SPC files (a folder of them, a zip, an .rsn, .rar or .7z) made into a pack in a
    process of its own (it is the emulator's work, a minute or so for a
    whole soundtrack), the pack made anew in its place when it is done.

    on_progress(done, total) and on_done(name, error) are called from the
    reading thread."""

    def __init__(self, source, name: str | None = None, on_progress=None, on_done=None):
        from ..translate.archives import is_archive
        from ..translate.pack import name_for
        self.source = Path(source)
        self.name = name or name_for(self.source.stem if is_archive(self.source) else self.source.name)
        check_name(self.name)
        self.stage = packs_dir() / (STAGE + self.name)
        self.on_progress = on_progress or (lambda done, total: None)
        self.on_done = on_done or (lambda name, error: None)
        self.done = self.total = 0
        self.proc = None
        self._cancelled = False

    def start(self) -> None:
        from ..translate import archives
        if not can_import():
            from ..spc.emulate import INSTALL
            raise PackError(f"importing needs the SNES emulator, bitcomposer-emu: {INSTALL}")
        if self.source.suffix.lower() in archives.BY_PROGRAM and not archives.program():
            raise PackError(f"{self.source.name}: unpacking it needs an archive program, {archives.INSTALL}")
        packs_dir().mkdir(parents=True, exist_ok=True)
        shutil.rmtree(self.stage, ignore_errors=True)
        package = Path(__file__).resolve().parents[2]     # the folder holding this bitcomposer, for the child
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(
            [str(package)] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])))
        self.proc = subprocess.Popen(self.command(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        threading.Thread(target=self._follow, daemon=True).start()

    def command(self) -> list[str]:
        return [sys.executable, "-m", "bitcomposer.spc", "--pack", str(self.stage), "--name", self.name,
                "--progress", str(self.source)]

    def _follow(self) -> None:
        for line in self.proc.stdout:
            words = line.split()
            if len(words) == 3 and words[0] == "progress":
                self.done, self.total = int(words[1]), int(words[2])
                self.on_progress(self.done, self.total)
        err = self.proc.stderr.read().strip().splitlines()
        self.proc.stdout.close()
        self.proc.stderr.close()
        code = self.proc.wait()
        if self._cancelled:
            shutil.rmtree(self.stage, ignore_errors=True)
            self.on_done(None, "cancelled")
        elif code != 0 or not (self.stage / PACK).is_file():
            shutil.rmtree(self.stage, ignore_errors=True)
            self.on_done(None, (err[-1] if err else f"the import stopped (exit {code})").removeprefix("bitcomposer.spc: "))
        else:
            target = packs_dir() / self.name
            unload(self.name)
            shutil.rmtree(target, ignore_errors=True)
            os.replace(self.stage, target)
            self.on_done(self.name, None)

    def cancel(self) -> None:
        if self.proc and self.proc.poll() is None:
            self._cancelled = True
            self.proc.kill()


def preview(name: str, voice: str, part: str, path) -> Path:
    """A short phrase of one of a pack's voices as an IT module, in the
    register of the part it is in: a run up and a held note (a held chord
    for harmony, a quick arpeggio for an arp, a bass figure low), four hits
    for a drum."""
    from ..instruments import _make_sample
    from ..it_format import ITNote, ITPattern, NOTE_OFF, write_it_file
    from .packfile import load_pack_file
    data = _load(name)
    load_pack_file(pack_file(name))
    own = voice in (data.get("samples") or {})
    sample = _make_sample(f"{name}_{voice}" if own else voice)
    pat = ITPattern(rows=32, channels=4)

    def put(row, ch, note):
        pat.data[row][ch] = ITNote(note=note, instrument=1 if note < 120 else 0, volume=64 if note < 120 else 255)

    if part in KIT or (own and is_drum(data["samples"][voice])):
        for row in (0, 4, 8, 12):
            put(row, 0, 60)
    elif part == "harmony":
        for ch, n in enumerate((60, 64, 67)):
            put(0, ch, n)
            put(16, ch, NOTE_OFF)
    elif part == "arp":
        for row in range(16):
            put(row, 0, (72, 76, 79, 84)[row % 4])
        put(16, 0, NOTE_OFF)
    else:
        low = part == "bass"
        run = (36, 43, 48, 43) if low else (72, 76, 79, 84)
        for i, n in enumerate(run):
            put(2 * i, 0, n)
        put(8, 0, run[0] if low else 84)
        put(20, 0, NOTE_OFF)
    write_it_file(str(path), f"{name} {voice}", [sample], [pat], [0], tempo=125, speed=6, num_channels=4)
    return Path(path)
