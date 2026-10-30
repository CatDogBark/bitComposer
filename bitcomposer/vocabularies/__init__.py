"""The vocabularies a song may be written from (docs/IDIOM.md, phase 6): a
game's tables, fitted on its songs' readings, the statistics of how its music
is put together and none of its samples.

Three kinds, one namespace (`names()`):
- shipped: one gzipped JSON file beside this module, the `tables` of a format
  2 pack file (`packs/packfile.py`); Final Fantasy VI's is the default;
- `library`: fitted over every song the listener has imported, all games
  together, kept as `vocabularies/library.json` in the data folder and
  counted again after each import;
- `pack:<name>`: an imported pack's own tables (a format 2 pack), the game's
  vocabulary beside its samples.

A vocabulary is `ready()` with MIN_SONGS songs behind it (measured 2026-10-30:
fitted on fewer than 40 of FFVI's songs the written drums are not the game's);
a shipped one always is."""
from __future__ import annotations

import gzip
import json
import os
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY = "library"                   # the vocabulary over everything imported
PACK_PREFIX = "pack:"                 # an imported pack's own tables
MIN_SONGS = 40                        # songs a library or pack vocabulary needs before the window offers it
_shipped: dict[str, dict] = {}


def shipped() -> list[str]:
    return sorted(f[:-len(".json.gz")] for f in os.listdir(HERE) if f.endswith(".json.gz"))


def library_dir() -> Path:
    from ..packs.library import data_dir
    return data_dir() / "vocabularies"


def library_path() -> Path:
    return library_dir() / f"{LIBRARY}.json"


def pack_name(name: str) -> str | None:
    """The pack an imported-pack vocabulary belongs to, else None."""
    return name[len(PACK_PREFIX):] if name.startswith(PACK_PREFIX) else None


def _tabled_packs() -> dict[str, dict]:
    """{pack name: its pack file's data} for the packs in the library that carry tables."""
    from ..packs import library, packfile
    out = {}
    try:
        for p in library.listing():
            try:
                data = json.loads(Path(p["path"]).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(data.get(packfile.TABLES), dict) and data[packfile.TABLES].get("tables"):
                out[p["name"]] = data
    except OSError:
        pass
    return out


def names() -> list[str]:
    """Every vocabulary on this machine: the shipped ones, the library's where it exists, each tabled pack's."""
    out = shipped()
    if library_path().is_file():
        out.append(LIBRARY)
    out += [PACK_PREFIX + n for n in sorted(_tabled_packs())]
    return out


def path(name: str) -> str:
    """A shipped vocabulary's file."""
    p = os.path.join(HERE, f"{name}.json.gz")
    if not os.path.exists(p):
        raise KeyError(f"no shipped vocabulary {name!r} (have {', '.join(shipped())})")
    return p


def raw(name: str) -> dict:
    """The vocabulary as written: {"source": {...}, "tables": {name: entry}}."""
    if name in shipped():
        if name not in _shipped:
            with gzip.open(path(name), "rt", encoding="utf-8") as f:
                _shipped[name] = json.load(f)
        return _shipped[name]
    if name == LIBRARY:
        if not library_path().is_file():
            raise KeyError("no library vocabulary yet: import a game first")
        return json.loads(library_path().read_text(encoding="utf-8"))
    pn = pack_name(name)
    if pn:
        from ..packs import packfile
        packs = _tabled_packs()
        if pn not in packs:
            raise KeyError(f"no imported pack {pn!r} with tables")
        return packs[pn][packfile.TABLES]
    raise KeyError(f"no vocabulary {name!r} (have {', '.join(names())})")


def source(name: str) -> dict:
    return dict(raw(name).get("source") or {})


def songs(name: str) -> int:
    """How many songs the vocabulary was fitted on."""
    return int(source(name).get("songs") or 0)


def label(name: str) -> str:
    """What the vocabulary is called in a song's message and the window."""
    if name == LIBRARY:
        return "My library"
    pn = pack_name(name)
    if pn:
        data = _tabled_packs().get(pn) or {}
        return data.get("label") or pn
    s = source(name)
    return s.get("label") or s.get("game") or name


def ready(name: str) -> bool:
    """Whether the window offers it: a shipped vocabulary always, a fitted one with MIN_SONGS songs behind it."""
    return name in shipped() or songs(name) >= MIN_SONGS


def load(name: str) -> dict:
    """The vocabulary's tables as the writer draws from them (packtables.read)."""
    from ..translate import packtables
    return packtables.read(raw(name))


def listing() -> list[dict]:
    """[{name, label, songs, ready, kind}] for the window and the command line."""
    out = []
    for n in names():
        kind = "shipped" if n in shipped() else "library" if n == LIBRARY else "pack"
        try:
            out.append({"name": n, "label": label(n), "songs": songs(n), "ready": ready(n), "kind": kind})
        except (KeyError, OSError, ValueError):
            continue
    return out


def refit_library(db=None, say=lambda *a: None) -> Path | None:
    """The library vocabulary counted again over every song in the readings, all games together, with every imported
    pack's samples' loudness known to the count; written to library_path(). None where the readings hold no song."""
    from ..packs import library
    from ..translate import packtables, rhythm, store
    db = db or store.connect()
    loud, strikes = {}, {}
    for p in library.listing():
        try:
            t = rhythm.load_loudness(Path(p["path"]).parent)
            loud.update(t)
            strikes.update(getattr(t, "strikes", {}) or {})
        except (OSError, ValueError):
            continue
    rhythm.set_loudness(loud, strikes)
    data = packtables.build(db, None, say=say)
    n = int(data.get("source", {}).get("songs") or 0)
    if not n:
        return None
    games = sorted({r[0] for r in db.execute("SELECT DISTINCT game FROM songs")})
    data["source"].update({"game": LIBRARY, "label": "My library", "songs": n, "games": games})
    library_dir().mkdir(parents=True, exist_ok=True)
    library_path().write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
    say(f"{library_path()}: the library vocabulary over {n} songs of {len(games)} games")
    return library_path()
