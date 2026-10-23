"""The tables a pack carries in the format's second version (docs/PACKS.md,
"The tables"): the shapes phase 3 kept (docs/idiom/phase-3-tables.md, the
record), fitted on one game's readings, written as JSON beside the voices
and read back as the models the writers draw from.

    python -m bitcomposer.translate.packtables --db PATH --game NAME [--out tables.json] [--into pack.json]

`--out` writes the tables alone; `--into` adds them to a pack file (the
importer's, docs/TRANSLATOR.md stage 2) and marks it format 2. Every kept
table is counted with share votes and absolute discounting (DISCOUNT); the
figure tables stand on the bar-cell floor and, like most, are drawn as the
song's own mixture (tables.Cache: the recall table beside the table)."""
import argparse
import json
import sys
from pathlib import Path

from . import phrases, rhythm, tables

VERSION = 1                          # of the tables' layout inside a pack
VOTES = tables.SHARES
DISCOUNT = 0.75
FIGURE = ("part", "meter", "habit", "previous")   # the figure tables' shape: the habit before the chain (writer.SHAPE)

# name -> (where the units come from, the builder, its keyword arguments, the shape, on the cell floor, as the song's
# mixture, what the table says), in the record's order
KEPT = {
    "rhythm": ("rhythm", "units", {}, FIGURE, True, True, "a part's bar as an onset pattern"),
    "values": ("rhythm", "value_units", {}, ("part", "value", "habit"), False, False, "a melody note held or detached, by its value"),
    "habits": ("rhythm", "rhythm_habit_units", {}, ("part",), False, False, "a part's articulation and repetition habit, drawn once a song"),
    "bass": ("rhythm", "bass_units", {}, FIGURE, True, True, "the bass's bar as a figure: positions with chord-tone marks"),
    "bass_habits": ("rhythm", "bass_habit_units", {}, ("part",), False, False, "the bass's habit (density, tones, octaves), drawn once a song"),
    "drums-KSt": ("rhythm", "drum_group_units", {"letters": ("K", "S", "t")}, FIGURE, True, True, "the kick, snare and toms' bar"),
    "drums-h": ("rhythm", "drum_group_units", {"letters": ("h",)}, FIGURE, True, True, "the hat's bar"),
    "drums-c": ("rhythm", "drum_group_units", {"letters": ("c",)}, FIGURE, True, True, "the cymbals' bar"),
    "drums-o": ("rhythm", "drum_group_units", {"letters": ("o",)}, FIGURE, True, True, "the other drum sounds' bar"),
    "drum_habits": ("rhythm", "drum_habit_units", {}, ("part",), False, False, "the drums' density habit, drawn once a song"),
    "voicings": ("rhythm", "voicing_units", {}, ("part", "shape", "habit"), False, True, "which chord tones an upper part holds in a span"),
    "widths": ("rhythm", "width_units", {}, ("part", "shape", "previous"), False, True, "how wide the upper voicing sits"),
    "voicing_habits": ("rhythm", "voicing_habit_units", {}, ("part",), False, False, "an upper part's richness habit, drawn once a song"),
    "chords": ("rhythm", "chord_units", {}, ("part", "mode", "previous"), False, True, "a bar's chord as a numeral in the key, after the bar before's"),
    "changes": ("rhythm", "change_units", {}, ("part", "meter", "habit"), False, False, "where in the bar the chord changes, by the song's motion"),
    "cadences": ("rhythm", "cadence_units", {}, ("part", "mode", "length"), False, False, "how a part's progression ends"),
    "loops": ("rhythm", "loop_units", {}, ("part",), False, False, "the chord the loop returns to"),
    "form": ("rhythm", "form_units", {}, ("part", "meter", "index"), False, False, "a part of the form: new, again or back, by its index"),
    "lengths": ("rhythm", "length_units", {}, ("part", "meter", "habit"), False, False, "a part's length in bars, by the song's habit"),
    "contours": ("phrases", "contour_units", {}, ("part", "mode"), False, True, "a four-bar phrase's contour"),
    "peaks": ("phrases", "peak_units", {}, ("part", "mode", "contour"), False, False, "where a phrase peaks, by its contour"),
    "endings": ("phrases", "ending_units", {}, ("part", "mode"), False, True, "the note a phrase ends on, against the key"),
    "relations": ("phrases", "relation_units", {}, ("part", "mode", "habit"), False, True, "how a phrase stands to the one before"),
    "texture": ("rhythm", "texture_units", {}, ("part", "meter", "previous"), False, True, "which parts sound in a bar, after the bar before's"),
    "presence": ("rhythm", "presence_units", {}, ("part", "meter", "previous"), False, True, "a part playing or resting in a bar"),
    "parts": ("rhythm", "parts_units", {}, ("part", "band"), False, False, "whether a song has each part, by the band's size"),
    "voices": ("rhythm", "voices_units", {}, ("part", "band"), False, False, "how many voices a song uses"),
    "doubles": ("rhythm", "double_units", {}, ("part",), False, False, "what a song's double voices double, and how"),
    "layers": ("rhythm", "layer_units", {}, ("part",), False, False, "what a second bass voice does beside the line"),
}
MODULES = {"rhythm": rhythm, "phrases": phrases}


def fit(name: str, units) -> dict | None:
    """One kept table fitted on its units, as the JSON entry a pack holds;
    None where there are no units."""
    units = list(units)
    if not units:
        return None
    _, _, _, shape, on_floor, mixture, what = KEPT[name]
    floor = rhythm.BarCells(units) if on_floor else None
    covers = len(rhythm.BarCells.COVERS) if on_floor else 0
    if mixture:
        model = tables.Cache.fit(units, shape, name=name, votes=VOTES, floor=floor, discount=DISCOUNT, covers=covers)
    else:
        model = tables.Table(shape, name, votes=VOTES, floor=floor, discount=DISCOUNT, covers=covers).fit(units)
    return {"what": what, "shape": list(shape), "mixture": mixture, "units": len(units),
            "songs": len({u.song for u in units}), "model": model.to_json()}


def build(db, game: str, say=lambda *a: None) -> dict:
    """The tables for one game from its readings: {"source": ..., "tables": {name: entry}}."""
    songs = {"rhythm": rhythm.load(db, game)[0], "phrases": phrases.load(db, game)[0]}
    out = {"source": {"game": game, "songs": len(songs["rhythm"]), "version": VERSION,
                      "votes": VOTES, "discount": DISCOUNT}, "tables": {}}
    for name, (module, builder, kwargs, *_) in KEPT.items():
        entry = fit(name, getattr(MODULES[module], builder)(songs[module], **kwargs))
        if entry is None:
            say(f"  {name}: no units, left out")
            continue
        out["tables"][name] = entry
        say(f"  {name}: {entry['units']} units of {entry['songs']} songs")
    return out


def read(d: dict) -> dict:
    """The tables back as models: {name: Table or Cache}."""
    out = {}
    for name, entry in d.get("tables", {}).items():
        model = tables.Cache if entry.get("mixture") else tables.Table
        out[name] = model.from_json(entry["model"], name)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="write a game's tables for a pack's second format")
    ap.add_argument("--db", help="the readings database (default: the product's)")
    ap.add_argument("--game", required=True, help="the game's name in the readings")
    ap.add_argument("--out", help="write the tables alone to this JSON file")
    ap.add_argument("--into", help="add the tables to this pack file and mark it format 2")
    args = ap.parse_args(argv)
    from . import store
    from ..packs import packfile
    db = store.connect(args.db)
    print(f"{args.game}: counting the kept tables", file=sys.stderr)
    data = build(db, args.game, say=lambda line: print(line, file=sys.stderr))
    text = json.dumps(data, separators=(",", ":")) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"{args.out}: {len(data['tables'])} tables, {len(text) / 1e6:.1f} MB", file=sys.stderr)
    if args.into:
        path = Path(args.into)
        pack = json.loads(path.read_text(encoding="utf-8"))
        pack[packfile.KEY] = packfile.TABLED
        pack[packfile.TABLES] = data
        packfile.parse(pack, path.parent, source=path.name)       # it must still check before it is written
        path.write_text(json.dumps(pack, indent=1) + "\n", encoding="utf-8")
        print(f"{path}: format {packfile.TABLED}, {len(data['tables'])} tables", file=sys.stderr)
    if not args.out and not args.into:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
