"""The vocabulary from the readings (stage 4 of docs/TRANSLATOR.md), the
rhythm half, counted: each part's rhythms bar by bar, the bass's and the
drums' figures as played, and the melody's intervals and lengths, over a
game's songs in the readings database.

    python -m bitcomposer.translate.rhythm [--db PATH] [--game NAME] [--top N] [--spc DIR]

The songs are the harmony counts' (vocab.py): each once through, to where
it loops; a song in free time, or whose chord beats are mostly unfit or
silent, is left out. A voice doubling another is left out as everywhere,
and so is a note at no volume; a voice read as a roll (notes on no grid of
the song's) is left out of the patterns, since it has none, but counted
where the onsets fall.

Rhythms. A bar is the song's own, from its bar lines, and only bars of the
song's meter are counted: a bar of another length is a grid section
restarting where its timing slipped (stage 1's known gap; most of Dancing
Mad's bars) or a meter changed for a bar, and is left out, the share said.
A part's onsets in a bar (its voices together; notes struck within NEAR of
each other are one onset, so a chord struck in three voices is one) are
placed on the song's grid, at the nearest multiple of its division
(sixteenths, triplets, both; a loose song's as it was read), as fractions of
a beat from the bar line. The bar's pattern is those positions drawn four
characters a beat: x on a quarter of the beat, t on a third, ~ finer than
either, at the nearest (so a roll of 32nds reads as sixteenths; the table of
where onsets fall says how much is finer). Patterns are counted per part
and per meter, with the share of the part's bars each covers and how many
songs it is heard in (one song's ostinato covers as many bars as a figure
forty songs share), a bar the part rests in counting as a rest. How dense each part plays is onsets a
bar, and where they fall: on the beat, an eighth, a sixteenth, a triplet (a
third or a sixth of a beat), or finer, which gives the share off the
eighths and, of those, on a triplet, as stage 2's measures count them
(measures.py), reckoned their way too for the comparison (every pitched
part together, within NEAR of an eighth, the median over songs; they count
a silent note, and a song with nothing off the eighths as none on a
triplet, so they read a little apart).

Bass figures. The bass's bar as its rhythm with the chord tone of each
note in its place, the chord from the song's chord spans at the note's
onset (R root, 3 third, s a sus chord's tone, 5 fifth, 7 seventh, + another
tone, ? no chord read or an unfit one), r a root an octave or more above
the bar's lowest bass note (the octave bass; the other tones are not told
apart by octave). Of notes struck together the lowest is the bass's line,
and its moves from note to note are counted by size, as the melody's.

Drum figures. The drums' bar as which sound plays where. The readings keep
each hit's sample, not what it is; a sound is named by its sound (drums.py:
kick, snare, hat or another) when the game's SPC files are at hand (--spc),
its hits settling only a bodiless burst between a hat and a cymbal. Without
them it is named by how the game plays it, over all its songs: one playing
DENSE hits a bar or more where it plays is the hat (hi-hats and rides keep
time); of the rest, one landing on the bar's first beat more than on its
backbeats is the kick, the other way the snare, as often one as the other
another sound; which misnames an open hat on the off-eighths a snare and a
cymbal held long a kick (FFVI's did, checked by ear 2026-10-20). The sounds
are listed with their profiles so the names can be judged. A bar's figure
is each sound's positions, drawn as the parts' are.

Melody. The melody as one line (of notes struck together, the highest, as
measures.py takes it), its moves from note to note in semitones by size
(a repeat, a step of one or two, a third, a fourth, a tritone, a fifth, a
sixth, a seventh, an octave, more) and direction, and the semitones
themselves; its notes' lengths as the time to the next note, in beats (the
value a score would write), on the song's grid, and how much of that the
note sounds (a note cut short of three quarters of it is detached).
against.py sets songs composed with a pack beside these counts."""
from __future__ import annotations
import argparse
import bisect
import json
import math
from fractions import Fraction
import statistics
import bisect
import statistics
import sys
from array import array
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from fractions import Fraction

from .. import drums as drums_mod, roles as R, store, tables, vocab
from ..vocab import FIT, MARKS, SOUNDS, Span, _beats_at, _buckets, _median, _pct, _sounding, tone_of
from ..vocab import TONES as CHORD_TONES

from . import readings as readings_mod, cells as cells_mod, arrangement as arrangement_mod   # noqa: E402  the package's other sections


# --- the form: the parts' letters and lengths ---

FORM_SIZES = ((1, "one part"), (4, "a few"), (8, "several"), (1e9, "many"))   # parts a song has
PART_LENGTHS = ((4, "short"), (8, "medium"), (1e9, "long"))                 # a song's median part length, in bars
LONG = 32                            # bars: a part this long or longer is one outcome
KINDS = ("new", "again", "back")     # a part: new material, the part before once more, an earlier part returning
LEVELS = ("part", "section")


def level_parts(song: readings_mod.Song, level: str = "part") -> list:
    return song.parts if level == "part" else song.sections


def part_kind(parts: list, i: int) -> str:
    """What a part is to the ones before (KINDS)."""
    bar, n, of, label = parts[i]
    if of is None:
        return "new"
    return "again" if parts[i - 1][3] == label else "back"


def _length_name(n: int) -> str:
    return str(n) if n < LONG else f"{LONG}+"


def form_units(songs, level: str = "part") -> list:
    """Each part of each song's form (at a level, LEVELS) as a unit: its
    outcome what it is to the parts before (KINDS); its values the part
    (form), the meter, the tempo band, its index in the form (1 to 5+), how
    many letters came before it (0 to 4+), the kind of the part before
    (START at the first) and the song's size in parts (FORM_SIZES)."""
    out = []
    for s in songs:
        parts = level_parts(s, level)
        if not parts:
            continue
        size = next(name for top, name in FORM_SIZES if len(parts) <= top)
        tempo, previous, seen = readings_mod.band(s.bpm), readings_mod.START, set()
        for i, (bar, n, of, label) in enumerate(parts):
            kind = part_kind(parts, i)
            out.append(tables.Unit(s.sid, s.game, kind, {
                "part": "form", "meter": s.meter, "tempo": tempo, "index": min(i + 1, 5), "letters": min(len(seen), 4),
                "previous": previous, "habit": size}))
            seen.add(label)
            previous = kind
    return out


def length_units(songs, level: str = "part") -> list:
    """Each part of each song's form as a unit: its outcome its length in
    bars (LONG and over one outcome); its values the part (form), the
    meter, the tempo band, its kind (KINDS), its index, the length of the
    part before (START at the first) and the song's habit, its median part
    length (PART_LENGTHS)."""
    out = []
    for s in songs:
        parts = level_parts(s, level)
        if not parts:
            continue
        habit = next(name for top, name in PART_LENGTHS if statistics.median(p[1] for p in parts) <= top)
        tempo, previous = readings_mod.band(s.bpm), readings_mod.START
        for i, (bar, n, of, label) in enumerate(parts):
            out.append(tables.Unit(s.sid, s.game, _length_name(n), {
                "part": "form", "meter": s.meter, "tempo": tempo, "kind": part_kind(parts, i), "index": min(i + 1, 5),
                "previous": previous, "habit": habit}))
            previous = _length_name(n)
    return out


def length_habit_units(songs, level: str = "part") -> list:
    """Each song's form as a unit: its outcome its part-length habit (PART_LENGTHS: the median part's length), its value the part (form)."""
    out = []
    for s in songs:
        parts = level_parts(s, level)
        if parts:
            out.append(tables.Unit(s.sid, s.game, next(name for top, name in PART_LENGTHS if statistics.median(p[1] for p in parts) <= top),
                                   {"part": "form"}))
    return out


def letters_units(songs, level: str = "part") -> list:
    """Each song's form as one unit: its outcome the parts' letters in order
    (A B B C B B C D D E); its values the part (form), the meter, the tempo
    band and the song's size in parts (FORM_SIZES)."""
    out = []
    for s in songs:
        parts = level_parts(s, level)
        if not parts:
            continue
        size = next(name for top, name in FORM_SIZES if len(parts) <= top)
        out.append(tables.Unit(s.sid, s.game, " ".join(p[3] for p in parts),
                               {"part": "form", "meter": s.meter, "tempo": readings_mod.band(s.bpm), "parts": size}))
    return out
