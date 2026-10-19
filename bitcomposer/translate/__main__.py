"""Read SPC files as music and keep the readings.

    python -m bitcomposer.translate FILE.spc|FOLDER ... [--db PATH] [--show] [--workers N]

Each song's tempo, bar, key and the part each voice plays, one line a song;
--show adds its chords. The readings are kept in a database on this machine
(~/.local/share/bitcomposer/readings.db unless --db says), a song read
again only when the translator has changed. Needs the emulator.
"""
import argparse
import glob
import os
import sys
from multiprocessing import Pool

from .. import spc
from ..spc.emulate import EmulatorMissing
from . import harmony, reading, store


def _files(paths) -> list[str]:
    out = []
    for p in paths:
        out += sorted(glob.glob(os.path.join(p, "*.spc"))) if os.path.isdir(p) else [p]
    return out


def _read(path):
    try:
        return reading.read(spc.read(path))
    except EmulatorMissing as e:
        return e


def line(r) -> str:
    g = r.grid
    beat = f"{g.bpm:5.1f} BPM {g.meter}/4" if g else "free time   "
    key = f"{harmony.NAMES[r.key[0]]} {r.key[1]}" if r.key else "-"
    parts = " ".join(f"{x.voice}:{x.role}" + (f"({x.of})" if x.of is not None else "") for x in r.roles)
    return f"{r.file[:-4][:34]:34s}  {beat}  {key:9s}  {parts}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bitcomposer.translate", description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+", metavar="FILE.spc|FOLDER")
    ap.add_argument("--db", help="the readings database (default: ~/.local/share/bitcomposer/readings.db)")
    ap.add_argument("--show", action="store_true", help="each song's chords too")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args(argv)
    files = _files(args.paths)
    db = store.connect(args.db)
    todo = []
    for f in files:
        with open(f, "rb") as fh:
            import hashlib
            sid = hashlib.sha1(fh.read()).hexdigest()[:20]
        if not store.known(db, sid):
            todo.append(f)
    with Pool(args.workers) as pool:
        for r in pool.imap(_read, todo):
            if isinstance(r, EmulatorMissing):
                print(f"bitcomposer.translate: {r}", file=sys.stderr)
                return 1
            store.keep(db, r)
            print(line(r))
            if args.show:
                print("    " + " ".join(f"{c.name}[{c.end - c.start:g}]" for c in r.chords))
    print(f"{len(todo)} read, {len(files) - len(todo)} already kept ({args.db or store.default_path()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
