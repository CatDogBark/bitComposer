"""Read SPC files as music and keep the readings.

    python -m bitcomposer.translate FILE.spc|FOLDER ... [--db PATH] [--show] [--workers N]
                                    [--against PACK ...] [--songs N]

Each song's tempo, bar, key and the part each voice plays, one line a song
(~ before the tempo: followed loosely, on no grid); --show adds its chords
and form (its parts, each a letter and its bars, and where it loops; its
sections, a short part and its repeats as one). The readings are kept in a database on this machine
(~/.local/share/bitcomposer/readings.db unless --db says), a song read
again only when the translator has changed. Needs the emulator.

--against PACK (a pack's name, or a pack.json; more than one allowed)
composes --songs songs with it (seeds 1 to N) and measures them beside the
songs read, the same yardsticks from notes on both sides (measures.py): a
table of medians, the middle half of the songs in brackets. The generated
songs' measures are kept in the database too.
"""
import argparse
import glob
import hashlib
import os
import statistics
import sys
from multiprocessing import Pool

from .. import spc
from ..spc.emulate import EmulatorMissing
from . import harmony, measures, reading, store


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
    except Exception as e:                   # one song's failure is reported, the rest read on
        return RuntimeError(f"{path}: {type(e).__name__}: {e}")


def line(r) -> str:
    g = r.grid
    beat = f"{'~' if g.loose else ' '}{g.bpm:5.1f} BPM {g.meter}/4" if g else " free time   "
    key = f"{harmony.NAMES[r.key[0]]} {r.key[1]}" if r.key else "-"
    parts = " ".join(f"{x.voice}:{x.role}" + (f"({x.of})" if x.of is not None else "") for x in r.roles)
    return f"{r.file[:-4][:34]:34s}  {beat}  {key:9s}  {parts}"


def _composed(db, pack: str, n: int) -> tuple[str, dict]:
    """Measures of n songs composed with a pack (its name, or a pack.json), kept as the generator's."""
    from ..composer import compose_song
    name, how = pack, {"sound": pack}
    if pack.endswith(".json"):
        from ..packs.packfile import load_pack_file
        name = load_pack_file(pack)
        how = {"pack": name}
    out = {}
    for seed in range(1, n + 1):
        values = measures.measure(measures.of_composed(compose_song(seed=seed, **how)))
        measures.keep(db, f"{name}/{seed}", "generator", values)
        for k, v in values.items():
            out.setdefault(k, []).append(v)
    return name, out


def _cell(values: list) -> str:
    if not values:
        return "-"
    if len(values) < 4:
        return f"{statistics.median(values):.3g}"
    q = statistics.quantiles(values, n=4)
    return f"{q[1]:.3g} [{q[0]:.3g}-{q[2]:.3g}]"


def table(columns: dict) -> str:
    """Medians a measure a row, a column each: the soundtrack, then each pack (rows in measure()'s order)."""
    names = list(dict.fromkeys(k for c in list(columns.values())[1:] + list(columns.values())[:1] for k in c))
    width = max(20, *(len(c) for c in columns))
    rows = [f"{'':20s}" + "".join(f"  {c:>{width}s}" for c in columns)]
    for k in names:
        rows.append(f"{k:20s}" + "".join(f"  {_cell(c.get(k, [])):>{width}s}" for c in columns.values()))
    return "\n".join(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bitcomposer.translate", description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+", metavar="FILE.spc|FOLDER")
    ap.add_argument("--db", help="the readings database (default: ~/.local/share/bitcomposer/readings.db)")
    ap.add_argument("--show", action="store_true", help="each song's chords too")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--against", action="append", default=[], metavar="PACK",
                    help="measure songs composed with PACK (a name or a pack.json) beside the songs read")
    ap.add_argument("--songs", type=int, default=20, help="songs composed for each --against (default 20)")
    args = ap.parse_args(argv)
    files = _files(args.paths)
    db = store.connect(args.db)
    todo, ids = [], []
    for f in files:
        with open(f, "rb") as fh:
            sid = hashlib.sha1(fh.read()).hexdigest()[:20]
        ids.append(sid)
        if not store.known(db, sid):
            todo.append(f)
    failed = 0
    with Pool(args.workers) as pool:
        for r in pool.imap(_read, todo):
            if isinstance(r, EmulatorMissing):
                print(f"bitcomposer.translate: {r}", file=sys.stderr)
                return 1
            if isinstance(r, RuntimeError):
                print(f"bitcomposer.translate: {r}", file=sys.stderr)
                failed += 1
                continue
            store.keep(db, r)
            print(line(r), flush=True)
            if args.show:
                print("    " + " ".join(f"{c.name}[{c.end - c.start:g}]" for c in r.chords))
                if r.form and r.form.parts:
                    loop = (f", loops to bar {r.form.loop_bar + 1} ({r.form.loop_bars} bars)"
                            if r.form.loop_bar is not None else ", no loop heard")
                    print("    form " + " ".join(f"{p.label}{p.bars}" for p in r.form.parts) + loop)
                    print("    sections " + " ".join(f"{p.label}{p.bars}" for p in r.form.sections))
    print(f"{len(todo) - failed} read, {len(files) - len(todo)} already kept, {failed} failed"
          f" ({args.db or store.default_path()})")
    if args.against:
        columns = {"soundtrack": store.features(db, ids)}
        for pack in args.against:
            name, values = _composed(db, pack, args.songs)
            columns[name] = values
        print(table(columns))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
