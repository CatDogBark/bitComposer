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
DISCOUNT = None                      # Witten-Bell for every table a pack carries: a pack's tables are drawn from, not scored
                                     # (phase 3 chose absolute discounting at 0.75 a vote for held-out bits), and under
                                     # absolute discounting a draw left the data: a one-vote-an-outcome table (registers,
                                     # balances) gave 56 % of its draws to the vocabulary evenly, and the figure tables gave
                                     # their long tail (a bar one song played) wholly to the cell floor, whose runs the
                                     # manner refuses, so a "new" bar was mostly a common bar again (the whole songs'
                                     # rounds 1 to 3, docs/idiom/phase-4-writing.md)
FIGURE = ("part", "meter", "habit", "feel", "previous")   # the figure tables' shape: the habit, then the song's feel, before the chain (writer.SHAPE);
                                                           # a floor stepping down from a one-song context lets the feel go first and keeps the habit

# name -> (where the units come from, the builder, its keyword arguments, the shape, on the cell floor, as the song's
# mixture, what the table says), in the record's order
KEPT = {
    "rhythm": ("rhythm", "units", {}, FIGURE, True, True, "a part's bar as an onset pattern (an upper part's own line where it holds two voices or more)"),
    "values": ("rhythm", "value_units", {}, ("part", "value", "habit"), False, False, "a melody note held or detached, by its value"),
    "habits": ("rhythm", "rhythm_habit_units", {}, ("part", "tempo", "weight"), False, False, "a part's density and repetition habit, drawn once a song given the tempo and the part's weight in the band"),
    "bass": ("rhythm", "bass_units", {}, FIGURE, True, True, "the bass's bar as a figure: positions with chord-tone marks"),
    "bass_habits": ("rhythm", "bass_habit_units", {}, ("part", "tempo", "weight"), False, False, "the bass's habit (density, tones, octaves), drawn once a song given the tempo and its weight"),
    "drums": ("rhythm", "drum_units", {}, FIGURE, True, True, "the kit's bar as one figure, every piece: what a song written whole repeats and varies as a kit does"),
    "drums-KSt": ("rhythm", "drum_group_units", {"letters": ("K", "S", "t")}, FIGURE, True, True, "the kick, snare and toms' bar"),
    "drums-h": ("rhythm", "drum_group_units", {"letters": ("h",)}, FIGURE, True, True, "the hat's bar"),
    "drums-c": ("rhythm", "drum_group_units", {"letters": ("c",)}, FIGURE, True, True, "the cymbals' bar"),
    "drums-o": ("rhythm", "drum_group_units", {"letters": ("o",)}, FIGURE, True, True, "the other drum sounds' bar"),
    "drum_habits": ("rhythm", "drum_habit_units", {}, ("part",), False, False, "the drums' density habit, drawn once a song"),
    "voicings": ("rhythm", "voicing_units", {}, ("part", "shape", "habit"), False, True, "which chord tones an upper part holds in a span"),
    "widths": ("rhythm", "width_units", {}, ("part", "shape", "previous"), False, True, "how wide the upper voicing sits"),
    "voicing_habits": ("rhythm", "voicing_habit_units", {}, ("part",), False, False, "an upper part's richness habit, drawn once a song"),
    "motions": ("rhythm", "upper_motion_units", {}, ("part",), False, False, "how an upper part moves through its tones (block, mixed, arpeggiated), drawn once a song"),
    "chords": ("rhythm", "chord_units", {}, ("part", "mode", "previous"), False, True, "a bar's chord as a numeral in the key, after the bar before's"),
    "changes": ("rhythm", "change_units", {}, ("part", "meter", "habit"), False, False, "where in the bar the chord changes, by the song's motion"),
    "cadences": ("rhythm", "cadence_units", {}, ("part", "mode", "length"), False, False, "how a part's progression ends"),
    "loops": ("rhythm", "loop_units", {}, ("part",), False, False, "the chord the loop returns to"),
    "form": ("rhythm", "form_units", {}, ("part", "meter", "index"), False, False, "a part of the form: new, again or back, by its index"),
    "lengths": ("rhythm", "length_units", {}, ("part", "meter", "habit"), False, False, "a part's length in bars, by the song's habit"),
    "letters": ("rhythm", "letters_units", {}, ("part",), False, False, "a song's form as its parts' letters in order (A B A B C), drawn whole"),
    "phrase_letters": ("rhythm", "phrase_letter_units", {}, ("part", "phrases", "form"), False, False, "a part's phrases as letters: the theme head again, an earlier head again, or new"),
    "theme_body": ("rhythm", "theme_body_units", {}, ("part",), False, False, "how much of the theme phrase comes back with its head"),
    "return_band": ("rhythm", "return_band_units", {}, ("part",), False, False, "which of the chords, the bass and the accompaniment come back with the theme"),
    "theme_doubling": ("rhythm", "theme_doubling_units", {}, ("part", "place"), False, False, "which other parts double the theme's cell where the tune plays it, and how far from the tune, at its statement or later"),
    "theme_carrier": ("rhythm", "theme_carrier_units", {}, ("part",), False, False, "the part that carries the theme phrase where the tune's phrase is not the theme: the bass, the counter, the accompaniment, or none"),
    "contours": ("phrases", "contour_units", {}, ("part", "mode"), False, True, "a four-bar phrase's contour"),
    "peaks": ("phrases", "peak_units", {}, ("part", "mode", "contour"), False, False, "where a phrase peaks, by its contour"),
    "endings": ("phrases", "ending_units", {}, ("part", "mode"), False, True, "the note a phrase ends on, against the key"),
    "relations": ("phrases", "relation_units", {}, ("part", "mode", "habit"), False, True, "how a phrase stands to the one before"),
    "moves": ("phrases", "move_units", {}, ("part", "mode", "habit", "place", "tone", "previous"), False, True, "the tune's move note to note, under the song's stepwise habit, by where the arriving note falls in its beat and the tone the note left stands on against the chord, after the move before"),
    "step_habits": ("phrases", "step_habit_units", {}, ("part",), False, False, "how stepwise a song's tune is (leaping, mixed, stepwise), drawn once a song"),
    "repeat_habits": ("phrases", "repeat_habit_units", {}, ("part",), False, False, "how often a song's tune repeats a note (rare, some, many), drawn once a song"),
    "melody_recall": ("rhythm", "melody_recall_units", {}, ("part", "habit"), False, False, "the tune's urn: a bar the same as the one before, an earlier one again, or new, by the song's echo habit"),
    "cell_rhythms": ("rhythm", "new_cell_rhythm_units", {}, ("part",), False, False, "a new cell's rhythm: new to the tune, the bar before's, or an earlier one's"),
    "echo_habits": ("rhythm", "echo_habit_units", {}, ("part", "tempo", "weight"), False, False, "how much of its tune a song echoes bar by bar, drawn once a song"),
    "texture": ("rhythm", "texture_units", {}, ("part", "meter", "previous"), False, True, "which parts sound in a bar, after the bar before's"),
    "presence": ("rhythm", "presence_units", {}, ("part", "meter", "previous"), False, True, "a part playing or resting in a bar"),
    "parts": ("rhythm", "parts_units", {}, ("part", "band"), False, False, "whether a song has each part, by the band's size"),
    "voices": ("rhythm", "voices_units", {}, ("part", "band"), False, False, "how many voices a song uses"),
    "doubles": ("rhythm", "double_units", {}, ("part",), False, False, "what a song's double voices double, and how"),
    "layers": ("rhythm", "layer_units", {}, ("part", "rank"), False, False, "what each voice of a part beside its line does, by its rank: doubling at an interval, alternating, or apart (how far off, how dense)"),
    "feels": ("rhythm", "feel_units", {}, ("part",), False, False, "a song's feel, duple or triple (a quarter of its onsets or more on triplet positions), drawn once a song; every figure table is drawn by it"),
    "layer_sounds": ("rhythm", "layer_sound_units", {}, ("part", "voice"), False, False, "the share of its gap a note sounds for a layered part's line and for its second voice"),
    "periods": ("rhythm", "period_units", {}, ("part", "length", "tempo"), False, False, "a backing part's period inside a part of the form: the lag in bars at which its bars repeat (1, 2, 4, 8) or none, by the part's length and the tempo"),
    "period_holds": ("rhythm", "period_hold_units", {}, ("part", "period"), False, False, "inside a backing part's period, a bar playing the bar a period before again (held) or not (varied)"),
    "second_figures": ("rhythm", "second_figure_units", {}, ("part", "feel", "tempo", "onsets", "line"), False, False, "a layered part's second line (an upper part's pattern, the bass's figure) under the line's own bar, by the song's feel and tempo band, where the part holds two voices or more"),
    "layer_samples": ("rhythm", "layer_sample_units", {}, ("part",), False, False, "the samples a layered part's line and its second voice play, as a pair, drawn once a song"),
    "voice_intervals": ("rhythm", "voice_interval_units", {}, ("part", "kind", "previous"), False, False, "a voice beside the line's interval to the line's note where they strike together, in scale steps (7 an octave), by the part, the relation (the counter-line's: same sample as the tune, or other) and its interval before"),
    "voice_moves": ("rhythm", "voice_move_units", {}, ("part", "kind", "place"), False, False, "a voice beside the line's move from its own last note, in scale steps, by the part, the relation and whether it strikes with the line or alone"),
    "counter_figures": ("rhythm", "counter_figure_units", {}, ("part", "feel", "tempo", "onsets", "line"), False, False, "the counter-line's bar as a mask over the tune's bar: which of the tune's onsets it strikes with and its own, by the song's feel and tempo band, the tune's onset count and pattern (its own onsets alone where the tune rests)"),
    "counter_samples": ("rhythm", "counter_sample_units", {}, ("part",), False, False, "whether a song's counter-line plays the tune's sample (same) or another (other), drawn once a song: the kind its interval and move words are drawn under, and its sample at the rendering"),
    "counter_shares": ("rhythm", "counter_share_units", {}, ("part", "tune"), False, False, "the counter-line's level as a share of the song's loudest part's, in tenths, by the band the tune's own share falls in, drawn once a song after the tune's"),
    "counter_pairs": ("rhythm", "counter_pair_units", {}, ("part", "tune"), False, False, "the counter-line's sample where it plays another than the tune's, by the tune's sample (the pack's ids), drawn once a song at the rendering"),
    "sample_lengths": ("rhythm", "sample_length_units", {}, ("part",), False, False, "the shortest note a sample is played at (ms, a class), by the sample: a note's floor on it"),
    "sample_speeds": ("rhythm", "sample_speed_units", {}, ("part",), False, False, "the fastest bars a sample is played in (notes a second, a class), by the sample: weighed in its choice for a part"),
    "registers": ("rhythm", "register_units", {}, ("part",), False, False, "the register a part plays in (midi low-high)"),
    "keys": ("rhythm", "key_units", {}, ("part",), False, False, "a song's key, tonic and mode"),
    "tempos": ("rhythm", "tempo_units", {}, ("part",), False, False, "a song's tempo, to five beats a minute"),
    "weights": ("rhythm", "weight_units", {}, ("part",), False, False, "a part's weight in the band (minor, half, main)"),
    "sizes": ("rhythm", "form_size_units", {}, ("part",), False, False, "how many parts a song's form has"),
    "length_habits": ("rhythm", "length_habit_units", {}, ("part",), False, False, "a song's part-length habit (short, medium, long), drawn once a song"),
    "balance": ("rhythm", "balance_units", {}, ("part",), False, False, "a song's band with each part's weight, register, sounded share, voices and level (a share of the loudest part's, in tenths) in it, drawn once a song as one unit"),
    "sounds": ("rhythm", "sound_units", {}, ("part",), False, False, "the share of its gap a part's note sounds"),
    "gap_sounds": ("rhythm", "gap_sound_units", {}, ("part", "voice", "gap"), False, False, "the share of its gap a note sounds, by the voice and the gap's length (under a beat, one to two, two to four, a bar or more)"),
    "bass_locks": ("rhythm", "bass_lock_units", {}, ("part",), False, False, "the share of the kit's accents (two pieces together) the bass strikes with, in tenths"),
    "levels": ("rhythm", "level_units", {}, ("part",), False, False, "a part's level as a share of the song's loudest part's, in tenths"),
    "layer_levels": ("rhythm", "layer_level_units", {}, ("part",), False, False, "a layered part's second voice's level against its line's, in tenths"),
    "climax": ("phrases", "climax_units", {}, ("part",), False, False, "the place among a song's tune phrases of the one holding the tune's highest note"),
    "arc": ("phrases", "arc_units", {}, ("part", "place"), False, False, "how far a tune phrase's top sits under the song's, by the phrase's place"),
    "summit": ("phrases", "summit_units", {}, ("part",), False, False, "how far the tune's highest note sits above its register's top"),
    "ranges": ("rhythm", "sample_range_units", {}, ("part",), False, False, "the register a sample is played in, by the sample"),
    "articulation": ("rhythm", "habit_units", {}, ("part",), False, False, "the tune's articulation habit (detached, mixed, held), drawn once a song"),
    "part_textures": ("rhythm", "part_texture_units", {}, ("part", "form", "previous"), False, False, "the texture a part of the form keeps (which parts sound), by its place in the form and the part before's"),
    "drum_group_habits": ("rhythm", "drum_group_habit_units", {}, ("part", "habit"), False, False, "a drum group's own habit given the kit's, drawn once a song"),
    "chord_tones": ("rhythm", "chord_tone_habit_units", {}, ("part",), False, False, "the share of the tune's notes on a beat that are chord tones, drawn once a song"),
    "contour_sizes": ("phrases", "contour_size_units", {}, ("part", "mode", "contour"), False, False, "how far a phrase's contour goes, in semitones, by its shape"),
    "phrase_shifts": ("phrases", "phrase_shift_units", {}, ("part", "mode", "relation"), False, False, "how far a phrase sits above or below the one before, in semitones, by its relation to it"),
    "repeat_rates": ("phrases", "repeat_rate_units", {}, ("part",), False, False, "the share of the tune's moves that repeat the note, drawn once a song"),
}
MODULES = {"rhythm": rhythm, "phrases": phrases}


def fit(name: str, units) -> dict | None:
    """One kept table fitted on its units, as the JSON entry a pack holds;
    None where there are no units."""
    units = list(units)
    _, _, _, shape, on_floor, mixture, what = KEPT[name]
    if on_floor:                                            # a figure table: rolls the reader kept as bars are no bars to write
        units = [u for u in units if not rhythm.is_roll(u.outcome, u.values.get("meter", 4))]
    if not units:
        return None
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
