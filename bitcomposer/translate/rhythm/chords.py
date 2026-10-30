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

from . import readings as readings_mod, arrangement as arrangement_mod   # noqa: E402  the package's other sections


# --- harmony: the chords by degree, their rhythm in the bar, the cadences and the loop ---

VARIETY = ((1, "one chord"), (3, "few"), (6, "several"), (1e9, "many"))   # distinct chords a song plays
MOTION = ((1 / 3, "static"), (2 / 3, "mixed"), (2, "moving"))            # its share of bars that change chord
NO_CHORD = "(none)"                  # a bar's chord where none sounds


def tonic_sure(song: readings_mod.Song) -> bool:
    """Whether the key reader's tonic is also the chord root the song plays
    most: the harmony tables' gate (the ear round of 2026-10-22: this keeps
    eight right tonics of the labelled dozen and no wrong one)."""
    if song.tonic is None:
        return False
    time = Counter()
    for c in song.chords:
        if c.root is not None and c.fit >= FIT:
            time[c.root] += c.beats
    return bool(time) and max(time, key=time.get) == song.tonic


def chord_in(chords, a: float, b: float):
    """The fit chord sounding most of [a, b), the first at a tie; None when none."""
    best = None
    for c in chords:
        if c.root is None or c.fit < FIT or c.end <= a or c.start >= b:
            continue
        cover = min(c.end, b) - max(c.start, a)
        if best is None or cover > best[0] + 1e-9:
            best = (cover, c)
    return best[1] if best else None


def numeral_of(song: readings_mod.Song, c) -> str:
    """A chord as a numeral in the song's key, its shape kept (I, iv, V7, bVII)."""
    return vocab.numeral(c.root, song.tonic, song.mode, c.shape)


def bar_spans(song: readings_mod.Song) -> list:
    """Each bar's chord span (the one sounding most of it), None where none."""
    return [chord_in(song.chords, a, b) for a, b in song.bars]


def bar_chords(song: readings_mod.Song) -> list[str]:
    """Each bar's chord (the one sounding most of it) as a numeral, NO_CHORD where none."""
    return [numeral_of(song, c) if c is not None else NO_CHORD for c in bar_spans(song)]


BY = ("numeral", "degree", "shape")  # what a chord unit's outcome is: the numeral with its shape, the degree alone, the shape alone


def harmony_habits(names: list) -> tuple[str, str]:
    """A song's variety (distinct chords, VARIETY) and motion (the share of
    its bars changing chord from the bar before, MOTION) from its bars' chords."""
    played = [n for n in names if n != NO_CHORD]
    variety = next(name for top, name in VARIETY if len(set(played)) <= top)
    changes = sum(1 for x, y in zip(played, played[1:]) if x != y)
    motion = readings_mod.habit_of(changes / (len(played) - 1), MOTION) if len(played) > 1 else "static"
    return variety, motion


def form_place(song: readings_mod.Song, i: int) -> str:
    """A part's place in the form: the only, first, middle or last part."""
    n = len(song.parts)
    return "only" if n == 1 else "first" if i == 0 else "last" if i == n - 1 else "middle"


def _own_parts(song: readings_mod.Song):
    """The form's parts that are not repeats of an earlier one: (index, first bar number, bars)."""
    for i, (bar, n, *rest) in enumerate(song.parts):
        if not rest or rest[0] is None:
            yield i, bar, n


def chord_units(songs, sure_only: bool = True, by: str = "numeral") -> list:
    """Each bar of each part of the form (a part repeating an earlier one
    left out) as a table's unit: its outcome the bar's chord as a numeral in
    the song's key (the chord sounding most of the bar, its shape kept;
    NO_CHORD for a bar without one), or by BY its degree alone (I, IV, bVII)
    or its shape alone (major, m, 5, 7, sus4; then the degree is a value);
    its values the part (harmony), the mode, the meter, the tempo band, the
    outcome of the bar before and of the one before that (START at the
    part's first bar), the bar's place in its part, the part's place in the
    form, and the song's habits, its variety and its motion. Songs whose
    tonic is not the chord root they play most are left out (tonic_sure)
    unless `sure_only` is off."""
    out = []
    for s in songs:
        if s.tonic is None or (sure_only and not tonic_sure(s)):
            continue
        spans = bar_spans(s)
        names = [numeral_of(s, c) if c is not None else NO_CHORD for c in spans]
        degrees = [vocab.degree(x) if x != NO_CHORD else NO_CHORD for x in names]
        shapes_ = [(c.shape or "major") if c is not None else NO_CHORD for c in spans]
        outcomes = {"numeral": names, "degree": degrees, "shape": shapes_}[by]
        variety, motion = harmony_habits(names)
        index = {num: k for k, num in enumerate(s.numbers)}
        tempo = readings_mod.band(s.bpm)
        for i, bar, n in _own_parts(s):
            previous, before, form = readings_mod.START, readings_mod.START, form_place(s, i)
            for num in range(bar, bar + n):
                k = index.get(num)
                if k is None:
                    continue
                out.append(tables.Unit(s.sid, s.game, outcomes[k], {
                    "part": R.HARMONY, "mode": s.mode, "meter": s.meter, "tempo": tempo, "previous": previous,
                    "before": before, "place": readings_mod.place_in_part(s, num), "form": form, "habit": variety, "motion": motion,
                    "degree": degrees[k]}))
                before, previous = previous, outcomes[k]
    return out


def degree_units(songs, sure_only: bool = True) -> list:
    """chord_units by degree alone: the progression without the chords' shapes."""
    return chord_units(songs, sure_only, by="degree")


def shape_units(songs, sure_only: bool = True) -> list:
    """chord_units by shape alone, the degree a value: the chord's shape given its degree."""
    return chord_units(songs, sure_only, by="shape")


def change_units(songs) -> list:
    """Each bar of each song as a unit for the harmonic rhythm: its outcome
    where in the bar the chord changes (beats from the bar line on the half
    beat, "none" when it does not); its values the part (harmony), the
    meter, the mode, the tempo band, the bar's place in its part, the bar
    before's outcome (START at a part's first bar and the song's) and the
    song's motion (MOTION). Every song counts: no tonic is needed."""
    out = []
    for s in songs:
        names = bar_chords(s)
        _, motion = harmony_habits(names)
        tempo = readings_mod.band(s.bpm)
        starts = []
        for i, c in enumerate(s.chords):
            if c.root is None or c.fit < FIT:
                continue
            earlier = s.chords[i - 1] if i else None
            if earlier is None or (earlier.root, earlier.shape) != (c.root, c.shape):
                starts.append(c.start)
        previous = readings_mod.START
        for k, (a, b) in enumerate(s.bars):
            where = readings_mod.place_in_part(s, s.numbers[k])
            if where == "first":
                previous = readings_mod.START
            inside = sorted({readings_mod.position(t - a, 2) for t in starts if a - readings_mod.NEAR <= t < b - readings_mod.NEAR})
            outcome = " ".join(str(p) for p in inside) or "none"
            out.append(tables.Unit(s.sid, s.game, outcome, {
                "part": R.HARMONY, "meter": s.meter, "mode": s.mode, "tempo": tempo, "place": where,
                "previous": previous, "habit": motion}))
            previous = outcome
    return out


def cadence_units(songs, sure_only: bool = True) -> list:
    """Each part of the form (repeats left out) of each sure song as a unit:
    its outcome how the part's chord sequence ends (phrases.CADENCES); its
    values the part (harmony), the mode, the part's place in the form, the
    length of the progression it is built on (phrases.SPANS) and the song's
    variety."""
    from .. import phrases                                  # phrases imports this module
    out = []
    for s in songs:
        if s.tonic is None or (sure_only and not tonic_sure(s)):
            continue
        names = bar_chords(s)
        variety, _ = harmony_habits(names)
        index = {num: k for k, num in enumerate(s.numbers)}
        for i, bar, n in _own_parts(s):
            seq = []
            for num in range(bar, bar + n):
                k = index.get(num)
                if k is None or names[k] == NO_CHORD:
                    continue
                d = vocab.degree(names[k])
                if not seq or seq[-1] != d:
                    seq.append(d)
            if not seq:
                continue
            length = next(name for top, name in phrases.SPANS if len(phrases.cycle(seq)) <= top)
            out.append(tables.Unit(s.sid, s.game, phrases.cadence(seq), {
                "part": R.HARMONY, "mode": s.mode, "form": form_place(s, i), "length": length, "habit": variety}))
    return out


def loop_units(songs, sure_only: bool = True) -> list:
    """Each sure song's loop as a unit: its outcome the chord the loop returns
    to (the numeral at its first bar); its values the part (harmony), the
    mode and the chord of the song's last bar (together, the loop's move)."""
    out = []
    for s in songs:
        if s.tonic is None or s.loop_bar is None or (sure_only and not tonic_sure(s)):
            continue
        names = bar_chords(s)
        index = {num: k for k, num in enumerate(s.numbers)}
        k = index.get(s.loop_bar)
        if k is None or not names:
            continue
        out.append(tables.Unit(s.sid, s.game, names[k], {"part": R.HARMONY, "mode": s.mode, "last": names[-1]}))
    return out
