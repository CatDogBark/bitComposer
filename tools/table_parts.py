"""A song's bass and drums (either or both) replaced by parts written from the tables (phase 3 of docs/IDIOM.md, the
acceptance by ear): the tables fitted on every other song in the readings, the figures drawn for the song's own
chords and bars, played on the song's own samples and voices, the rest of the song as decoded.

    python tools/table_parts.py FILE.spc --db READINGS.db -o OUT.it [--parts bass,drums] [--seed 1] [--seconds 60]
                                [--title T] [--figures OUT.json] [--stems DIR]

--stems writes, for a page that switches each part while the song plays: NAME rest.it (no written part's voices),
and for each part NAME <part> original.it and NAME <part> written.it. Prints what each writer did and what the
readers make of the original and the written song (bitcomposer/translate/harness.py).
"""
import argparse
import json
import os
import sys

from bitcomposer.spc import convert
from bitcomposer.translate import harness, store


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python tools/table_parts.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("spc")
    ap.add_argument("--db", required=True)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--parts", default="bass,drums", help="which parts to write, comma-separated (bass, drums, upper: the harmony, accompaniment and arp together, melody)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--title", help="the module's title (25 characters show in a player)")
    ap.add_argument("--figures", help="write each part's figures drawn and the song's own beside, as JSON")
    ap.add_argument("--stems", help="write the rest and each part's original and written as modules of their own here")
    ap.add_argument("--free", action="store_true", help="write free of the song's own part (phase 4): the habit drawn from the game's, any figure the table knows, bar by bar from the mixture")
    ap.add_argument("--label", default="written", help="the stems' name for the written part (default written; e.g. free)")
    a = ap.parse_args(argv)
    db = store.connect(a.db)
    ctx = harness.load(db, a.spc, a.seconds)
    if ctx is None:
        print(f"{a.spc}: not in the readings, or not counted", file=sys.stderr)
        return 1
    ctx.free = a.free
    wanted = [p.strip() for p in a.parts.split(",") if p.strip()]
    writers = {"bass": harness.write_bass, "drums": harness.write_drums, "upper": harness.write_upper, "melody": harness.write_melody}
    parts = []
    print(f"{ctx.title} ({ctx.game}):")
    for name in wanted:
        if name not in writers:
            print(f"  no writer for {name}", file=sys.stderr)
            continue
        w = writers[name](ctx, a.seed)
        if w is None:
            print(f"  {name}: nothing to write (no such part read, or no reference note)")
            continue
        parts.append(w)
        for line in w.log:
            print(f"  {name}: {line}")
        for i, (f, o) in enumerate(zip(w.figures, w.own)):
            print(f"    {name} bar {i:3d}  written {f:44.44}  own {o}")
    if not parts:
        return 1
    label = " + ".join(w.part for w in parts)
    swapped = harness.score_with(ctx, parts, a.title or f"{ctx.title} [table {label}]",
                                 [f"{ctx.title}: the {label} written from the tables (phase 3 of docs/IDIOM.md)",
                                  f"the tables fitted on every other song; seed {a.seed}; the rest as decoded"])
    info = convert.render(swapped, a.out)["info"]
    replaced = set().union(*(w.replaced for w in parts))
    print(f"{a.out}: {info['notes']} notes, {info['channels']} channels; voices {sorted(replaced)} written")
    print(f"  original: {harness.readings_of(ctx, ctx.original, replaced)}")
    print(f"  written:  {harness.readings_of(ctx, swapped, replaced)}")
    if a.figures:
        with open(a.figures, "w") as f:
            json.dump({"song": ctx.title, "game": ctx.game, "seed": a.seed,
                       "parts": {w.part: {"written": w.figures, "own": w.own, "voices": sorted(w.replaced)} for w in parts}}, f, indent=1)
    if a.stems:
        for path in harness.stems(ctx, parts, a.stems, label=a.label):
            print(f"  stem {os.path.basename(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
