"""Whole songs written from a pack's tables (phase 4 of docs/IDIOM.md, the integration), rendered as modules, read back
and measured.

    python tools/whole.py --pack PACK.json --seeds 1-20 -o DIR [--max-bars 48] [--loops 1] [--fade 3] [--game NAME]
                          [--db READINGS.db] [--tables TABLES.json] [--title-prefix Whole] [--no-read]

--pack a pack file (format 2, its tables inside) or a built-in pack's name (then --tables gives the tables). Writes
DIR/<title>.it (the form once, then the loop --loops - 1 times more, fading at the end) and DIR/<title>.json (the plan,
each part's log and figures, the measures of the song read back). Prints each song's plan and, at the end, the measures over the seeds; with --db
(the readings) and --game, the game's own songs' numbers beside them.
"""
import argparse
import json
import os
import statistics
import sys

from bitcomposer.packs import PACKS, packfile
from bitcomposer.spc import convert
from bitcomposer.translate import harness, packtables, rhythm, store, whole


def seeds_of(text: str) -> list[int]:
    out = []
    for piece in text.split(","):
        a, _, b = piece.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def load_pack(arg: str, tables_path: str | None):
    """(the pack's table, its own sample names, its name, the models)."""
    if arg.endswith(".json"):
        name = packfile.load_pack_file(arg)
        with open(arg, encoding="utf-8") as f:
            data = json.load(f)
        own = set(data.get("samples") or {})
        models = packtables.read(data.get(packfile.TABLES) or {})
        if tables_path:
            with open(tables_path, encoding="utf-8") as f:
                models = packtables.read(json.load(f))
        return PACKS[name], own, name, models, data.get("label") or name
    if arg not in PACKS:
        raise SystemExit(f"{arg}: no such pack (a pack file ends in .json; the built-in packs are {', '.join(PACKS)})")
    models = {}
    if tables_path:
        with open(tables_path, encoding="utf-8") as f:
            models = packtables.read(json.load(f))
    return PACKS[arg], set(), arg, models, PACKS[arg].get("label") or arg


def _quartiles(values: list) -> str:
    if not values:
        return "-"
    if len(values) < 4:
        return "/".join(f"{v:.2f}" for v in sorted(values))
    q = statistics.quantiles(values, n=4)
    return f"{q[0]:.2f}/{q[1]:.2f}/{q[2]:.2f}"


def table(rows: list[dict], title: str) -> str:
    """The measures over songs: each number's quartiles (a quarter of the songs under / the median / three quarters)."""
    keys = {}
    for m in rows:
        for k, v in m.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    keys.setdefault(f"{k}.{kk}", []).append(vv)
            elif isinstance(v, (int, float)):
                keys.setdefault(k, []).append(v)
    lines = [f"{title} ({len(rows)} songs): a quarter under / the median / three quarters"]
    for k in sorted(keys):
        lines.append(f"  {k:28s} {_quartiles(keys[k])}   (n {len(keys[k])})")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python tools/whole.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--pack", required=True)
    ap.add_argument("--tables", help="a tables file (packtables --out) for a built-in pack, or to replace a pack file's")
    ap.add_argument("--seeds", default="1")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--max-bars", type=int, default=48, help="forms longer than this are drawn again (default 48)")
    ap.add_argument("--loops", type=int, default=1, help="how many times the loop plays in all (default 1: the form once)")
    ap.add_argument("--fade", type=float, default=3.0, help="seconds the module fades over at its end")
    ap.add_argument("--game", help="the game the songs are written as (the title's game; default the pack's label)")
    ap.add_argument("--title-prefix", default="Whole")
    ap.add_argument("--db", help="the readings: with --game, the game's own songs' measures beside the written songs'")
    ap.add_argument("--no-read", action="store_true", help="do not read the songs back (no measures)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    pack, own, name, models, label = load_pack(a.pack, a.tables)
    game = a.game or label
    if not models:
        print(f"{a.pack}: no tables (a format 1 pack; give --tables)", file=sys.stderr)
        return 1
    os.makedirs(a.out, exist_ok=True)
    print(f"{label}: {len(models)} tables; writing seeds {a.seeds} as {game}")
    reference = harness.reference_index()
    rows = []
    for seed in seeds_of(a.seeds):
        title = f"{a.title_prefix} {seed:02d}"
        out = whole.compose(models, pack, own, name, seed, game, title, max_bars=a.max_bars, loops=a.loops, reference=reference, read=not a.no_read, fade=a.fade)
        p = out["plan"]
        path = os.path.join(a.out, f"{title}.it")
        convert.render(out["score"], path)
        record = {"plan": p.to_json(), "echo": out["echo"], "voices": out["first"],
                  "samples": {r: (s[0] if isinstance(s, tuple) else {k: v[0] for k, v in s.items()}) for r, s in out["samples"].items()},
                  "parts": {r: {"log": w.log, "figures": w.figures} for r, w in out["written"].items()},
                  "measures": out["measures"], "seconds": out["score"].seconds}
        with open(os.path.join(a.out, f"{title}.json"), "w", encoding="utf-8") as f:
            json.dump(record, f, indent=1)
        print(f"{title}: {p.letters} ({p.bars} bars, {out['score'].seconds:.0f} s), {harmony_name(p)} {p.bpm:.0f} BPM, band "
              + " ".join(f"{r}={p.weights[r]}" if r in p.weights else r for r in p.band)
              + (f"; echo {out['echo']['delay']}" if out["echo"] else "; dry"))
        if not a.quiet:
            for line in p.log:
                print(f"    {line}")
            for role, w in out["written"].items():
                print(f"    {role}: {w.log[0]}")
        if out["measures"]:
            rows.append(out["measures"])
        elif not a.no_read:
            print("    (not read back)")
    if rows:
        print(table(rows, f"written ({label})"))
    if a.db and a.game:
        db = store.connect(a.db)
        songs, _ = rhythm.load(db, a.game)
        print(table([whole.measures(s) for s in songs], f"{a.game}'s own songs"))
    return 0


def harmony_name(p) -> str:
    from bitcomposer.translate import harmony
    return f"{harmony.NAMES[p.tonic]} {p.mode}"


if __name__ == "__main__":
    sys.exit(main())
