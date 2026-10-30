"""The vocabularies the player ships: a game's tables, fitted on its songs'
readings (docs/IDIOM.md, phase 6). Each is one gzipped JSON file beside this
module, the `tables` of a format 2 pack file (`packs/packfile.py`): the
statistics of how a game's music is put together, none of its samples. The
writer draws a whole song from one (`bitcomposer --vocabulary ffvi`); a
vocabulary fitted on the listener's own imports lives in the data folder
instead (phase 6's library)."""
from __future__ import annotations

import gzip
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_cache: dict[str, dict] = {}


def names() -> list[str]:
    """The shipped vocabularies' names, as `--vocabulary` takes them."""
    return sorted(f[:-len(".json.gz")] for f in os.listdir(HERE) if f.endswith(".json.gz"))


def path(name: str) -> str:
    p = os.path.join(HERE, f"{name}.json.gz")
    if not os.path.exists(p):
        raise KeyError(f"no shipped vocabulary {name!r} (have {', '.join(names())})")
    return p


def raw(name: str) -> dict:
    """The file as written: {"source": {...}, "tables": {name: entry}}."""
    if name not in _cache:
        with gzip.open(path(name), "rt", encoding="utf-8") as f:
            _cache[name] = json.load(f)
    return _cache[name]


def source(name: str) -> dict:
    return dict(raw(name).get("source") or {})


def label(name: str) -> str:
    """What the vocabulary is called in a song's message and the window: the game's name."""
    s = source(name)
    return s.get("label") or s.get("game") or name


def load(name: str) -> dict:
    """The vocabulary's tables as the writer draws from them (packtables.read)."""
    from ..translate import packtables
    return packtables.read(raw(name))
