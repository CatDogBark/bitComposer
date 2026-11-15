"""Each song's own answers to the once-a-song words (round 172 of docs/idiom/phase-4-writing.md).

A word that says something of a song as a whole (how often its tune sits a semitone from the band, how far it leaves
the key) is counted a song at a time and kept as a table over every song: a pooled word. A song written on one
song's balance token then drew such a word from the pool, another song's answer more often than not, beside the two
hundred and more facts the token itself carries; and round after round a pooled word heard to disagree with the rest
of the song was moved onto the token by hand, a field at a time. Here the tables keep each song's own answer beside
the pooled counts: the `song_answers` table, by the song, the word and the word's context. The token says which song it is
(`song=`), and the plan asks that song first and the pool where it has no answer (a jingle with too few notes to
count). Which words go by the song is the list OWN.
"""
from __future__ import annotations

from .. import tables

OWN_SHAPE = ("song", "word", "context")   # the song_answers table's shape: the song's id, the word's table, its context joined (own_context)
OWN = {                               # the once-a-song words answered by the token's song first: table -> (the module its units are
    "clashes": ("rhythm", "clash_units", ("part", "place")),   # counted in, their builder, the table's shape), as packtables.KEPT has them
    "off_scale": ("rhythm", "off_scale_units", ("part", "mode", "place")),
    "chord_tones": ("rhythm", "chord_tone_habit_units", ("part",)),
    # round 173: the tune's and the counter-line's manner and their notes' lengths
    "articulation": ("rhythm", "habit_units", ("part",)),
    "echo_habits": ("rhythm", "echo_habit_units", ("part", "tempo", "weight")),
    "step_habits": ("phrases", "step_habit_units", ("part",)),
    "repeat_habits": ("phrases", "repeat_habit_units", ("part",)),
    "repeat_rates": ("phrases", "repeat_rate_units", ("part",)),
    "tune_grain": ("rhythm", "tune_grain_units", ("part", "habit")),
    "tune_sounds": ("rhythm", "tune_sound_units", ("part", "note")),
    # and the band's: what a voice beside a line does and how long its notes sound, the voicing, the samples' speed, the kit's
    # limbs' habits, how far the bass locks to the kit
    "layers": ("rhythm", "layer_units", ("part", "rank")),
    "layer_sounds": ("rhythm", "layer_sound_units", ("part", "voice")),
    "voicing_habits": ("rhythm", "voicing_habit_units", ("part",)),
    "part_speeds": ("rhythm", "part_speed_units", ("part", "habit")),
    "drum_group_habits": ("rhythm", "drum_group_habit_units", ("part", "classes", "habit")),
    "bass_locks": ("rhythm", "bass_lock_units", ("part",)),
    # round 174: how long a voice's notes sound by the gap to the next (a unit a note: the song's middle answer is taken), and
    # the vibrato the song is performed with
    "gap_sounds": ("rhythm", "gap_sound_units", ("part", "voice", "speed", "gap")),
    "vibrato": ("rhythm", "vibrato_units", ("part",)),
    # round 176: a kit piece's rate by its place in the bar. A word with no pooled table: only the song's own answer is kept
    "kit_rate_places": ("rhythm", "kit_rate_place_units", ("part", "place")),
    # round 177: the counter-line beside its tune by part of the form: its share of notes struck with a tune note, and its
    # intervals to the tune's note (many answers a place: the song's profile). No pooled table behind either
    "counter_with": ("rhythm", "counter_with_units", ("part", "place")),
    "counter_intervals": ("rhythm", "counter_interval_units", ("part", "place", "line")),
}


def own_context(values) -> str:
    """A word's context as the song_answers table keeps it: its values in the word's shape's order, joined by "|"."""
    return "|".join(str(v) for v in values)


def _package():
    """This package, whose sections' builders its names are (looked up when asked: it is not whole while this loads)."""
    import importlib
    return importlib.import_module(__package__)


def own_units(songs, module: str = "rhythm", builders=None) -> list:
    """Every song's own answer to each of the OWN words counted in `module` under each context it has one for, as a
    unit of the `song_answers` table: its outcome the answer, its values the song's id, the word and the context. A
    song with no unit of a word under a context (too few notes for a share) has no answer there, and a written song
    draws the pooled word. `builders`: the module the words' builders are in (this package's by default; the phrases
    words' are the phrases module's, and packtables counts those with the phrases' songs)."""
    out = []
    for word, (where, builder, shape) in OWN.items():
        if where != module:
            continue
        for u in getattr(builders if builders is not None else _package(), builder)(songs):
            out.append(tables.Unit(u.song, u.game, u.outcome, {"song": u.song, "word": word, "context": own_context(u.values[c] for c in shape)}))
    return out
