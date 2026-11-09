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

from . import readings as readings_mod, cells as cells_mod, chords as chords_mod   # noqa: E402  the package's other sections


# --- the arrangement: which parts play in which bars, the band, the voices, doublings, layered basses ---

ARRANGEMENT = "arrangement"
SILENCE = "(rest)"
OTHERS = ("0", "1", "2", "3+")            # other parts sounding in a bar
PRESENCE = ((0.5, "sparse"), (0.9, "mostly"), (2, "always"))   # a part's share of its song's bars it sounds in
SUSTAIN = 1.0                           # beats a held note must sound into a bar to count the part as playing in it
ECHO = 0.02                             # seconds: a double delayed by more is an echo, else a unison double


def sounding_bars(song: readings_mod.Song, role: str) -> set:
    """The indices of the bars a part sounds in: a note struck in the bar, or
    held into it for SUSTAIN beats or more."""
    out = set()
    starts = [a for a, _ in song.bars]
    for st, length, _, _ in song.notes.get(role, ()):
        k = bisect.bisect_right(starts, st + readings_mod.NEAR) - 1
        if k >= 0 and st < song.bars[k][1] - readings_mod.NEAR:
            out.add(k)
        stop = st + (length if not math.isnan(length) else 0.25)
        j = k + 1
        while j < len(song.bars) and stop > song.bars[j][0] + SUSTAIN:
            out.add(j)
            j += 1
    return out


def _form_of_bars(song: readings_mod.Song) -> dict:
    """Bar number -> its part's place in the form (form_place), for bars inside a part."""
    out = {}
    for i, (bar, n, *_) in enumerate(song.parts):
        for num in range(bar, bar + n):
            out[num] = chords_mod.form_place(song, i)
    return out


def texture_units(songs) -> list:
    """Each bar of each song as a unit: its outcome the parts sounding in it
    (their names in order, SILENCE for none); its values the part
    (arrangement), the meter, the tempo band, the bar's place in its part
    and its part's in the form, the bar before's texture (START at a part's
    first bar and the song's) and the song's habit, its band (every part it
    has)."""
    out = []
    for s in songs:
        if not s.notes:
            continue
        plays = {role: sounding_bars(s, role) for role in s.notes}
        the_band = " ".join(sorted(s.notes))
        forms, tempo, previous = _form_of_bars(s), readings_mod.band(s.bpm), readings_mod.START
        for k, num in enumerate(s.numbers):
            where = readings_mod.place_in_part(s, num)
            if where == "first":
                previous = readings_mod.START
            texture = " ".join(sorted(role for role, bars in plays.items() if k in bars)) or SILENCE
            out.append(tables.Unit(s.sid, s.game, texture, {
                "part": ARRANGEMENT, "meter": s.meter, "tempo": tempo, "place": where, "form": forms.get(num, "none"),
                "previous": previous, "habit": the_band}))
            previous = texture
    return out


def presence_units(songs) -> list:
    """Each bar of each part of each song as a unit: its outcome whether the
    part plays in the bar or rests; its values the part, the meter, the
    tempo band, the bar's place in its part and its part's in the form, how
    many other parts sound in the bar (OTHERS), the part's outcome in the bar
    before (START at a part's first bar and the song's) and the part's habit
    in the song (PRESENCE: the share of the song's bars it sounds in)."""
    out = []
    for s in songs:
        if not s.notes or not s.bars:
            continue
        plays = {role: sounding_bars(s, role) for role in s.notes}
        forms, tempo = _form_of_bars(s), readings_mod.band(s.bpm)
        for role, bars in plays.items():
            habit = readings_mod.habit_of(len(bars) / len(s.bars), PRESENCE)
            previous = readings_mod.START
            for k, num in enumerate(s.numbers):
                where = readings_mod.place_in_part(s, num)
                if where == "first":
                    previous = readings_mod.START
                others = sum(1 for other, theirs in plays.items() if other != role and k in theirs)
                outcome = "plays" if k in bars else "rests"
                out.append(tables.Unit(s.sid, s.game, outcome, {
                    "part": role, "meter": s.meter, "tempo": tempo, "place": where, "form": forms.get(num, "none"),
                    "others": OTHERS[min(others, 3)], "previous": previous, "habit": habit}))
                previous = outcome
    return out


def band_units(songs) -> list:
    """Each song as a unit: its outcome its band, the parts it has (their
    names in order); its values the part (arrangement), the meter and the
    tempo band."""
    return [tables.Unit(s.sid, s.game, " ".join(sorted(s.notes)) or SILENCE,
                        {"part": ARRANGEMENT, "meter": s.meter, "tempo": readings_mod.band(s.bpm)}) for s in songs]


def voices_units(songs) -> list:
    """Each song as a unit: its outcome how many voices it uses (the role
    reader's, doubles and rolls included); its values the part (arrangement),
    the size of its band in parts, the meter and the tempo band."""
    return [tables.Unit(s.sid, s.game, str(len(s.voices)),
                        {"part": ARRANGEMENT, "band": min(len(s.notes), 5), "meter": s.meter, "tempo": readings_mod.band(s.bpm)})
            for s in songs if s.voices]


def double_units(songs) -> list:
    """Each song as a unit: its outcome what its double voices double and
    how (the role doubled, unison or echo, as "melody echo"; "none" where
    the song has no double); its values the part (arrangement) and the size
    of its band."""
    out = []
    for s in songs:
        roles = {voice: role for voice, role, _, _ in s.voices}
        kinds = set()
        for voice, role, of, evidence in s.voices:
            if role != R.DOUBLE:
                continue
            delay = evidence.get("echo_ms", 0) / 1000 or evidence.get("delay", 0) or evidence.get("lag_ms", 0) / 1000
            kinds.add(f"{roles.get(of, 'unknown')} {'echo' if delay > ECHO else 'unison'}")
        out.append(tables.Unit(s.sid, s.game, " / ".join(sorted(kinds)) or "none",
                               {"part": ARRANGEMENT, "band": min(len(s.notes), 5)}))
    return out


CHORDAL = (R.HARMONY, R.ACCOMP, R.ARP)   # the parts that state the harmony
PARTS_ASKED = (R.DRUMS, R.BASS, R.MELODY, R.COUNTER, "chordal", R.DOUBLE)   # what a song has or has not


def parts_units(songs) -> list:
    """Each song, for each part a song may have (PARTS_ASKED: the drums, the
    bass, the melody, the counter-line, a chordal part, a double voice), as a
    unit: its outcome whether the song has it (yes, no); its values the part
    asked and the size of the band otherwise. The coarse view of the band,
    where a game's habit shows (the band as one string is too fine to)."""
    out = []
    for s in songs:
        if not s.voices:
            continue
        roles = {role for _, role, _, _ in s.voices}
        for part in PARTS_ASKED:
            has = any(r in roles for r in CHORDAL) if part == "chordal" else part in roles
            out.append(tables.Unit(s.sid, s.game, "yes" if has else "no",
                                   {"part": part, "band": min(len(s.notes) - (part in s.notes), 4), "tempo": readings_mod.band(s.bpm)}))
    return out


ALL = "all"                           # a part's texture: every part of the band sounds


ENTRY_CAP = 8                        # bars: an entrance or exit further inside a section is counted as this
SECTION_LENGTHS = ((4, "short"), (8, "medium"), (1e9, "long"))   # a section's bars, the class an entrance is counted under


def section_length(bars: int) -> str:
    return next(name for top, name in SECTION_LENGTHS if bars <= top)


DENSITY_STEP = 1.5                   # a section's level or density over the part's song median counts as a step up at this, down at its
                                     # inverse (round 101: section_densities); readings.DENSITY_STEP is the same (a literal: readings is still
                                     # loading when this module is)


def level_step(ratio: float) -> str:
    """A section's level ratio (section_level_units) as the step the section_densities word conditions on (round 101): "up" at
    DENSITY_STEP and over, "down" at its inverse and under, "same" between."""
    return "up" if ratio >= DENSITY_STEP else "down" if ratio <= 1 / DENSITY_STEP else "same"


def section_density_units(songs) -> list:
    """Each part of each own section of a song's form as a unit (round 101): its outcome the section's density tier against the
    part's song density ("d+": the part's notes a bar in the section, over the bars it plays in, at DENSITY_STEP times its
    song median or more; "d-": at the inverse or less; "d=" between), its values the part and the step the section's level
    makes (level_step of the section_level_units ratio). FFVI: a level step up comes with a density or register change in 7
    of the accompaniment's 8 and is bare in 7 of the counter's 10; at level 1.0 the accompaniment changes density tier in a
    quarter of its sections (22 sparser, 17 denser of 176), the bass in a sixth; a tier up is 1.8 times at the median, a
    tier down 0.5. The written parts had kept one density all song, so a level step was a bare volume move (Inner River
    Crossing's accompaniment, Song Check 82)."""
    from bisect import bisect_right
    out = []
    for s in songs:
        if not s.notes or not s.parts or not s.note_levels:
            continue
        index = {num: k for k, num in enumerate(s.numbers)}
        starts = [a for a, _ in s.bars]
        for role, pairs in s.note_levels.items():
            if role == R.DRUMS or len(pairs) < 16:
                continue
            med = statistics.median(lv for _, lv in pairs)
            notes = [n for n in s.notes.get(role, []) if not math.isnan(n[2])]
            if med <= 0 or not notes:
                continue
            per_bar = Counter()
            for n in notes:
                k = bisect_right(starts, n[0] + readings_mod.NEAR) - 1
                if 0 <= k < len(s.bars) and n[0] < s.bars[k][1] - readings_mod.NEAR:
                    per_bar[k] += 1
            song_density = statistics.median(per_bar.values()) if per_bar else 0
            if not song_density:
                continue
            for i, bar, n in chords_mod._own_parts(s):
                ks = [index[num] for num in range(bar, bar + n) if num in index]
                if not ks:
                    continue
                a, b = s.bars[ks[0]][0], s.bars[ks[-1]][1]
                mine = [lv for st, lv in pairs if a - readings_mod.NEAR <= st < b - readings_mod.NEAR]
                played = [k for k in ks if per_bar.get(k)]
                if len(mine) < 4 or not played:
                    continue
                ratio = min(LEVEL_RATIO_CAP[1], max(LEVEL_RATIO_CAP[0], statistics.median(mine) / med))
                density = sum(per_bar[k] for k in played) / len(played) / song_density
                tier = "d+" if density >= DENSITY_STEP else "d-" if density <= 1 / DENSITY_STEP else "d="
                out.append(tables.Unit(s.sid, s.game, tier, {"part": role, "step": level_step(ratio)}))
    return out


def form_place_of(i: int, n: int) -> str:
    """A part's place in a form of n parts: the only, first, middle or last part (form_place, from the index alone)."""
    return "only" if n == 1 else "first" if i == 0 else "last" if i == n - 1 else "middle"


def entry_of(outcome: str) -> tuple:
    """A part_entries outcome as (bars after the section's start it enters, bars before its end it leaves)."""
    enters = leaves = 0
    for token in outcome.split():
        name, _, k = token.partition(":")
        if name == "enters" and k.isdigit():
            enters = int(k)
        elif name == "leaves" and k.isdigit():
            leaves = int(k)
    return enters, leaves


LEVEL_RATIO_CAP = (0.3, 2.0)         # a section's level over the part's song median is counted within this, in tenths


def section_level_units(songs) -> list:
    """Each part of each own section of a song's form as a unit: its outcome the part's median note level in the section
    over its median level in the whole song, in tenths within LEVEL_RATIO_CAP ("1.0": the part at its usual level; "0.5":
    half of it, an intro's bass; "1.5": a swell), its values the part and the section's place in the form. Dynamics by
    section (round 48, 2026-10-28): FFVI's parts hold one level at the median (the bar-level 90th/10th ratio 1.02) but a
    quarter move by 1.5 times or more across the song, the accompaniment and arp most, and 0.7 to 0.9 of a part's
    sections sit at 1.0, first sections under it (the bass's at 0.3 to 0.8 in a quarter); the written parts had played
    one level all song."""
    out = []
    for s in songs:
        if not s.notes or not s.parts or not s.note_levels:
            continue
        index = {num: k for k, num in enumerate(s.numbers)}
        n_parts = len(s.parts)
        for role, pairs in s.note_levels.items():
            if role == R.DRUMS or len(pairs) < 16:
                continue
            med = statistics.median(lv for _, lv in pairs)
            if med <= 0:
                continue
            for i, bar, n in chords_mod._own_parts(s):
                ks = [index[num] for num in range(bar, bar + n) if num in index]
                if not ks:
                    continue
                a, b = s.bars[ks[0]][0], s.bars[ks[-1]][1]
                mine = [lv for st, lv in pairs if a - readings_mod.NEAR <= st < b - readings_mod.NEAR]
                if len(mine) < 4:
                    continue
                ratio = min(LEVEL_RATIO_CAP[1], max(LEVEL_RATIO_CAP[0], statistics.median(mine) / med))
                out.append(tables.Unit(s.sid, s.game, f"{round(ratio, 1):.1f}", {"part": role, "form": form_place_of(i, n_parts)}))
    return out


NO_TIER = "-"                         # the entrance word's habit value for a part whose density tier it does not read (every part but the drums)


def part_entry_units(songs) -> list:
    """Each part present in each own section of a song's form as a unit: its outcome where inside the section it enters
    and leaves ("whole": from the section's first bar to its last; "enters:3": its first sounding bar three bars after
    the section's start; "leaves:1": its last one bar before the end; both; to ENTRY_CAP), its values the part, the
    section's place in the form and the section's length class (SECTION_LENGTHS), and for the drums the kit's density
    tier (round 59; NO_TIER for the other parts). Round 46 (2026-10-28): FFVI's parts
    join inside a section more often than at its edge (61 late entrances inside, 45 at a boundary), where a texture a
    section lets them join at its lines alone; the build of a song is where its parts come in."""
    out = []
    tier = {u.song: u.outcome.split()[0] for u in readings_mod.drum_habit_units(songs)}   # the kit's density tier (round 59: FFVI's dense kits play a
    for s in songs:                                                         # section whole in 101 of 106, its sparse kits in 20 of 27)
        if not s.notes or not s.parts:
            continue
        plays = {role: sounding_bars(s, role) for role in s.notes}
        index = {num: k for k, num in enumerate(s.numbers)}
        n_parts = len(s.parts)
        for i, bar, n in chords_mod._own_parts(s):
            ks = [index[num] for num in range(bar, bar + n) if num in index]
            if not ks:
                continue
            place, length = form_place_of(i, n_parts), section_length(len(ks))
            for role, bars in plays.items():
                mine = [k for k in ks if k in bars]
                if not mine:
                    continue
                enters, leaves = ks.index(mine[0]), len(ks) - 1 - ks.index(mine[-1])
                tokens = [x for x in (f"enters:{min(enters, ENTRY_CAP)}" if enters else "", f"leaves:{min(leaves, ENTRY_CAP)}" if leaves else "") if x]
                out.append(tables.Unit(s.sid, s.game, " ".join(tokens) or "whole",
                                       {"part": role, "habit": tier.get(s.sid, NO_TIER) if role == R.DRUMS else NO_TIER, "form": place, "length": length}))
    return out


def part_texture_units(songs) -> list:
    """Each part of each song's form (a repeat left out) as a unit: its
    outcome the texture most of its bars have, against the song's band:
    ALL where every part of the band sounds, else "no" and the parts of
    the band that rest ("no drums melody": an intro); its values the part
    (arrangement), the part's place in the form, its index and the
    outcome of the part before (START at the first). A part keeps one
    texture through nine bars in ten (the readings, 2026-10-23: the modal
    texture covers a median 100 % of a part's bars, a mean 91 %), so a
    song written with no original draws a texture a part, not a bar; and
    it draws it against its own band, so a band's parts are heard (the
    plain textures drawn a part had left a band's drums out of every
    part in a song of four). Round 59: the kit's density tier is a value too
    (NO_TIER where the song has no drums): FFVI's dense kits sit out a whole
    section in one bar of a hundred, its sparse kits in fifteen."""
    out = []
    tier = {u.song: u.outcome.split()[0] for u in readings_mod.drum_habit_units(songs)}
    for s in songs:
        if not s.notes or not s.parts:
            continue
        plays = {role: sounding_bars(s, role) for role in s.notes}
        index = {num: k for k, num in enumerate(s.numbers)}
        previous = readings_mod.START
        for i, bar, n in chords_mod._own_parts(s):
            ks = [index[num] for num in range(bar, bar + n) if num in index]
            if not ks:
                continue
            textures = Counter(frozenset(role for role, bars in plays.items() if k in bars) for k in ks)
            modal = textures.most_common(1)[0][0]
            resting = sorted(set(s.notes) - modal)
            outcome = ALL if not resting else "no " + " ".join(resting)
            out.append(tables.Unit(s.sid, s.game, outcome, {"part": ARRANGEMENT, "habit": tier.get(s.sid, NO_TIER) if R.DRUMS in s.notes else NO_TIER,
                                                            "form": chords_mod.form_place(s, i), "index": min(i + 1, 5), "previous": previous}))
            previous = outcome
    return out


CHORD_TONE_BIN = 0.1                 # the grain a tune's chord-tone share is kept to


CHORD_TONE_PARTS = (R.MELODY, R.COUNTER)   # the lines the chord_tones word is counted for and held on (the counter's since round 96)


def chord_tone_habit_units(songs) -> list:
    """Each song with a melody as a unit, and since round 96 each with a
    counter-line: its outcome the share of the line's notes on a beat that
    are tones of the chord sounding (to CHORD_TONE_BIN); its value the part.
    The melody writer holds its tune to the drawn share (FFVI's songs: a
    median 0.56; the writer's constant gave 0.75 in the first whole songs,
    2026-10-23); the counter writer holds its line (writer.counter: FFVI's
    counter-lines land on the chord on about half their strong beats; the
    written counter, its notes the voice words' intervals from the tune
    with no chord word, had sat at 0.37)."""
    out = []
    for s in songs:
        for role in CHORD_TONE_PARTS:
            line = _line(cells_mod.tune_line(s, role))
            hits, total = 0, 0
            for n in line:
                if abs(n[0] - round(n[0])) >= readings_mod.NEAR:
                    continue
                c = _chord_at(s.chords, n[0])
                if c is None or c.root is None or c.fit < FIT:
                    continue
                total += 1
                hits += vocab.tone_of(round(n[2]) % 12, c.root, c.shape) != "other"
            if total >= 8:
                out.append(tables.Unit(s.sid, s.game, f"{round(hits / total / CHORD_TONE_BIN) * CHORD_TONE_BIN:.1f}", {"part": role}))
    return out


TONE_FIGURE_PARTS = (R.HARMONY, R.ACCOMP, R.ARP)   # the chord parts (readings.UPPER, which this module cannot read at import): their line's tones against the chord (round 96)
CHORD_TONE, OFF_TONE = "c", "x"          # a tone figure's letters: a tone of the chord sounding, a tone off it
TONE_TIERS = ((0.1, "rare"), (0.3, "some"), (1.01, "many"))   # a song's share of a chord part's line onsets off the chord, as a tier (round 96:
                                     # FFVI's 58 accompaniments spread from none to 0.72, 10 under a tenth, 29 to 0.3, 19 over)


def tone_tier_of(share: float) -> str:
    """The tier a song's off-chord share falls in (TONE_TIERS)."""
    return next(name for top, name in TONE_TIERS if share < top)


def _tone_bars(songs):
    """Each chord part's line of each song as its bars' tone figures: [(song, part, [(bar start, struck, classes)])], the
    bars no chord fits left out (tone_figure_units, tone_tier_units, tone_degree_units)."""
    out = []
    for s in songs:
        for role in TONE_FIGURE_PARTS:
            line = cells_mod.tune_line(s, role)
            if len(line) < WORD_NOTES:
                continue
            bars = []
            for k, a, struck in readings_mod.numbered_bars_of(s, role, line):
                classes = tone_classes(struck, a, s.chords) if struck else None
                if classes:
                    bars.append((a, struck, classes))
            if bars:
                out.append((s, role, bars))
    return out


def _tone_share(bars) -> float:
    """The share of a part's line onsets off the chord over its bars."""
    return sum(c.count(OFF_TONE) for _, _, c in bars) / max(1, sum(len(c) for _, _, c in bars))


def tone_classes(struck, start: float, chords) -> list | None:
    """A bar's onsets ([(position, [notes])], readings.numbered_bars_of) as a tone figure's letters: the lowest note at each
    onset a tone of the chord sounding (CHORD_TONE) or off it (OFF_TONE); None where no chord fits an onset."""
    out = []
    for p, ns in struck:
        c = _chord_at(chords, start + float(p))
        pitched = [n[2] for n in ns if not math.isnan(n[2])]
        if c is None or c.root is None or c.fit < FIT or not pitched:
            return None
        out.append(CHORD_TONE if vocab.tone_of(round(min(pitched)) % 12, c.root, c.shape) != "other" else OFF_TONE)
    return out


def tone_tier_units(songs) -> list:
    """Each chord part's line of each song as a unit (round 96): its outcome the tier of its share of onsets off the chord
    sounding (tone_tier_of: rare under a tenth, some under 0.3, many), its value the part. Drawn once a song for each
    chord part on an own stream: the tier the part's tone figures are drawn under, so a song is pure or decorated as a
    whole, as FFVI's are (the first cut had drawn every bar from the pooled table, and every written song sat at the
    pooled 0.28 where FFVI's spread from none to 0.72)."""
    return [tables.Unit(s.sid, s.game, tone_tier_of(_tone_share(bars)), {"part": role}) for s, role, bars in _tone_bars(songs)]


def tone_figure_units(songs) -> list:
    """Each bar of a chord part's line as a unit (round 96): its outcome the line's onsets' tone classes against the chord
    sounding at each ("c c c x": CHORD_TONE a tone of the chord, OFF_TONE off it), its values the part, the song's tier
    (tone_tier_of, the part's own share over the song), the onset count and the line's own pattern. The upper writer draws
    it under the line's bar as a second voice's mask is drawn (backing off to the onset count under the tier) and plays
    the OFF_TONE onsets off the chord at the tone_degrees draws. FFVI's accompaniment line leaves the chord on a quarter
    of its notes (the songs' medians 0.12 to 0.38), in 762 of its 1,447 bars; the written line had held the voicing's
    tones alone (0.07 of its notes, and those from voicing marks the chord lacked)."""
    out = []
    for s, role, bars in _tone_bars(songs):
        tier = tone_tier_of(_tone_share(bars))
        for a, struck, classes in bars:
            out.append(tables.Unit(s.sid, s.game, " ".join(classes),
                                   {"part": role, "tier": tier, "onsets": str(len(struck)), "line": readings_mod.pattern(p for p, _ in struck)}))
    return out


def tone_degree_units(songs) -> list:
    """Each onset of a chord part's line off the chord sounding as a unit (round 96): its outcome the note's interval from
    the chord's root in semitones ("2" a ninth, "5" a fourth, "9" a sixth, "10" a seventh over a triad), its values the
    part, the chord's shape (which decides which degrees are off it; "major" for the plain triad, as the voicings word
    names it) and the degree of the bar's previous off-chord onset (START at the first). Drawn an off-chord onset, chained
    within the bar: FFVI keeps the degree from one off-chord onset to the next 0.52 of the time (an ostinato pecks one
    tone off the chord, a fill walks), and the line's onset takes the drawn degree nearest the voicing tone it replaces."""
    out = []
    for s, role, bars in _tone_bars(songs):
        for a, struck, classes in bars:
            previous = readings_mod.START
            for (p, ns), cls in zip(struck, classes):
                if cls != OFF_TONE:
                    continue
                c = _chord_at(s.chords, a + float(p))
                pc = round(min(n[2] for n in ns if not math.isnan(n[2]))) % 12
                degree = str((pc - c.root) % 12)
                out.append(tables.Unit(s.sid, s.game, degree, {"part": role, "shape": c.shape or "major", "previous": previous}))
                previous = degree
    return out


OFF_SCALE_BIN = 0.05                 # the off_scale word's grain (round 93): a part's share of notes off the song's natural scale
CLASH_BIN = 0.02                     # the clashes word's grain (round 93): the tune's share of onsets a semitone from a sounding part
OFF_SCALE_PARTS = (R.MELODY, R.COUNTER, R.BASS, R.ACCOMP, R.HARMONY, R.ARP)
WORD_NOTES = 16                      # notes a part needs in a place for an off_scale or clashes unit


def off_scale_units(songs) -> list:
    """Each pitched part of each song with a key, by the beat (strong: the onset on a beat; weak: off it), as a unit: its
    outcome the share of the part's notes whose pitch class lies off the song's natural scale (major, or natural minor;
    to OFF_SCALE_BIN), its values the part, the mode and the place; for the melody and the counter the line's notes
    (tune_line), since the writer holds the word on the line it writes and the voices beside it follow their relation
    words. FFVI (round 93): the melody 0.08 of its strong-beat notes in major and 0.20 in minor (0.10 and 0.24 off the
    beat), the counter 0.11 and 0.22, the bass 0.20 and 0.15, the accompaniment 0.07 and 0.13, the arp 0.13 and 0.42; a
    minor tune's off-scale notes spread over the flat second, the raised seventh and sixth, the raised fourth and the major
    third in near-equal shares, a major tune's lean to the flat seventh. The melody writer had barred every off-scale note
    on a beat (STRONG_SCALE), and the written minor tunes sat at 0.07; it holds the drawn share instead, in its draws and
    in placing its recalls (the melody's and the counter's own draws; the other parts' shares wait for their words)."""
    from .. import harmony
    out = []
    for s in songs:
        if s.tonic is None:
            continue
        mode = "major" if s.mode == "major" else "minor"
        scale = {(s.tonic + st) % 12 for st in harmony.MODES["major" if mode == "major" else "natural_minor"]}
        for role in OFF_SCALE_PARTS:
            by_place = {"strong": [0, 0], "weak": [0, 0]}
            notes = cells_mod.tune_line(s, role) if role in (R.MELODY, R.COUNTER) else s.notes.get(role, [])   # the line the writer
            for n in notes:                                 # holds the word on; its layer voices follow their relation words
                if math.isnan(n[2]):
                    continue
                place = "strong" if abs(n[0] - round(n[0])) < readings_mod.NEAR else "weak"
                by_place[place][1] += 1
                by_place[place][0] += round(n[2]) % 12 not in scale
            for place, (off, total) in by_place.items():
                if total >= WORD_NOTES:
                    out.append(tables.Unit(s.sid, s.game, f"{round(off / total / OFF_SCALE_BIN) * OFF_SCALE_BIN:.2f}", {"part": role, "mode": mode, "place": place}))
    return out


CLASH_ORDER = (R.BASS, R.HARMONY, R.ACCOMP, R.ARP, R.MELODY, R.COUNTER)   # the order whole.plan.write writes the pitched parts in (the bass, then
                                                                           # readings.UPPER, then the two lines): each part's
                                                                       # clashes word counts it against the parts before it, which its writer sees


def clash_under(role: str) -> tuple:
    """The parts written before `role` (CLASH_ORDER): the ones its clashes word counts it against and its writer holds the
    drawn share against; none for the bass, written first."""
    return CLASH_ORDER[:CLASH_ORDER.index(role)] if role in CLASH_ORDER else ()


def clash_units(songs) -> list:
    """Each pitched part of each song but the bass, by the beat, as a unit: its outcome the share of the part's onsets that
    fall under a sounding note of a part written before it (clash_under: the bass under the chord parts, those under the
    tune, all of them under the counter) and sit a semitone (1 or 11 mod 12) from it (to CLASH_BIN), its values the part
    and the place; the melody and the counter as their lines (tune_line), the chord parts every note. FFVI (round 94):
    the accompaniment 0.04 of its strong onsets and 0.04 of its weak ones, the tune 0.08 and 0.11, the counter 0.11 and
    0.20 (a song's share from none to 0.6); the written songs had sat at 0.10, 0.12 and 0.23 on the beat (round 93, when
    the tune alone held a share, counted against every other part). Each writer holds its part's drawn share against the
    parts under it: the melody writer in its draws and its recalls' placement, the counter writer in its interval draws,
    the upper writer in its voicings' tones."""
    out = []
    for s in songs:
        for role in CLASH_ORDER[1:]:
            mine = [n for n in (cells_mod.tune_line(s, role) if role in (R.MELODY, R.COUNTER) else s.notes.get(role, [])) if not math.isnan(n[2])]
            if len(mine) < WORD_NOTES:
                continue
            under = sorted((n[0], n[0] + n[1], round(n[2]) % 12) for r in clash_under(role) for n in s.notes.get(r, []) if not math.isnan(n[2]))
            if not under:
                continue
            by_place = {"strong": [0, 0], "weak": [0, 0]}
            for n in mine:
                t = n[0]
                sounding = {pc for a_, b_, pc in under if a_ - readings_mod.NEAR <= t < b_ - readings_mod.NEAR}
                if not sounding:
                    continue
                place = "strong" if abs(t - round(t)) < readings_mod.NEAR else "weak"
                by_place[place][1] += 1
                by_place[place][0] += any((round(n[2]) - pc) % 12 in (1, 11) for pc in sounding)
            for place, (hits, total) in by_place.items():
                if total >= WORD_NOTES:
                    out.append(tables.Unit(s.sid, s.game, f"{round(hits / total / CLASH_BIN) * CLASH_BIN:.2f}", {"part": role, "place": place}))
    return out


ROLL = 6                             # strikes a beat, a bar over: a roll or tremolo the reader kept as a figure, not a bar to write
ROLL_PIECE = 4                       # strikes a beat on one drum piece, a bar over: a roll on that piece


def is_roll(figure: str, meter: int) -> bool:
    """Whether a figure is a roll read as a bar: more than ROLL strikes a
    beat on a pitched part, or more than ROLL_PIECE a beat on one drum
    piece (the readings keep 17 such bass bars of FFVI's 715: a tremolo
    under a "sparse" habit wrote 44 notes in a bar, 2026-10-23)."""
    tokens = readings_mod._tokens(figure)
    if not tokens:
        return False
    marks = [t.partition(":")[2] for t in tokens]
    pieces = set(readings_mod.LETTERS.values())
    if marks and all(m in pieces for m in marks):
        return max(Counter(marks).values()) > ROLL_PIECE * max(1, meter)
    return len(tokens) > ROLL * max(1, meter)


REGISTER_NOTES = 8                   # pitched notes a part (or a stretch) needs for a register


def part_register(notes, ambitus: bool = False) -> tuple | None:
    """A part's register as the registers table keeps it: (low, high) midi to REGISTER_BIN, the notes' 10th and 90th
    percentiles, or the whole ambitus (`ambitus`: the melody's, a tune uses its extremes); None where the part has
    under REGISTER_NOTES pitched notes."""
    pitched = sorted(n[2] for n in notes if not math.isnan(n[2]))
    if len(pitched) < REGISTER_NOTES:
        return None
    low, high = (pitched[0], pitched[-1]) if ambitus else (pitched[int(0.1 * (len(pitched) - 1))], pitched[int(0.9 * (len(pitched) - 1))])
    return int(round(low / cells_mod.REGISTER_BIN)) * cells_mod.REGISTER_BIN, int(round(high / cells_mod.REGISTER_BIN)) * cells_mod.REGISTER_BIN


LAYER_LEVEL_CAP = 4.0                # a voice beside the line's level over the line's is counted up to this (layer_level_units' cap).
                                      # 1.5 until round 51 (2026-10-28): 27 of FFVI's 148 voices beside a line run past it (to 3.35),
                                      # and in every one the line is a quiet inner voice (0.42 of the song's loudest part) and the
                                      # voice beside it the part's melody-level voice (0.99); capped, it had played 4 dB under the
                                      # game. The note level's cap of full stands; this cap only keeps the unit's grain in tenths.


def voice_level_shares(song: readings_mod.Song, role: str) -> list | None:
    """A layered part's voices beyond the line (two voices or more with notes), in layer_units' rank order (the busiest
    first; the bass's line the voice with the longest notes, line_voice), each one's median level over the line voice's
    in tenths, capped at LAYER_LEVEL_CAP (the layer_levels unit: "1.0", "1.3"); None for a part of one voice or whose
    line has no level. The first entry is layer_level_units' outcome; the whole list is the balance token's sixth field."""
    voices = cells_mod.part_voices(song, role)
    if len(voices) < 2:
        return None
    line = cells_mod.line_voice(voices, role, song)
    a = song.voice_levels.get(line)
    if not a:
        return None
    others = sorted((v for v in voices if v != line), key=lambda v: (-len(voices[v]), v))
    if any(not song.voice_levels.get(v) for v in others):
        return None
    return [f"{min(LAYER_LEVEL_CAP, round(song.voice_levels[v] / a, 1)):.1f}" for v in others]


LAYER_SHARES = ((0.4, "sparse"), (0.8, "half"), (float("inf"), "full"))   # a voice beyond the line: its notes over the line's (layer_tokens, round 65)


def layer_share_class(share: float) -> str:
    return next(name for top, name in LAYER_SHARES if share < top)


def layer_tokens(song: readings_mod.Song, role: str) -> list | None:
    """The balance token's sixth field (round 65): each voice beyond the line, in voice_level_shares' order, as
    `level share@sample@note share` ("3.2@s5a1fa4d5d3@0.12": its level over the line's, the pack id of the sample it
    plays most, its notes over the line's). FFVI's extra voices are on another sample than the line in 45 of 73
    accompaniments, 27 of 42 counters and 15 of 15 basses, and play 0.5-0.7 of the line's notes; drawn apart, the written
    ones had taken the line's sample and played 0.84-1.15 of its notes, a sparse pad in the game a busy riff over the tune.
    Since round 86 a fourth sub-field, where the song plays the voice's sample; since round 90 a fifth, what the voice does
    beside which part stretch by stretch (relation_words: "ox9>dm-12x14>o"); since round 92 a sixth, its instrument by
    stretch (stretch_word with "~": "s605f200105~56-72x14>sf89f5aedfd~60-68")."""
    shares = voice_level_shares(song, role)
    if shares is None:
        return None
    voices = cells_mod.part_voices(song, role)
    line = cells_mod.line_voice(voices, role, song)
    others = sorted((v for v in voices if v != line), key=lambda v: (-len(voices[v]), v))
    relations = relation_words(song)                        # what each voice does beside the others, stretch by stretch (round 90)
    out = []
    for share, v in zip(shares, others):
        keys = Counter(n[3] for n in voices[v] if isinstance(n[3], str))
        key = keys.most_common(1)[0][0] if keys else ""
        sid = ("s" + key[:10] if len(key) >= 10 else key) if key else ""
        rng = sample_range_in(voices[v], key) if key else ""    # where the token song plays this voice's sample (round 86)
        subs = [share, sid, f"{min(9.0, len(voices[v]) / max(1, len(voices[line]))):.2f}", rng, relations.get(v, ""),
                stretch_word(song, voices[v], "~")]        # and its instrument by stretch (round 92; "~" keeps "@" for the sub-fields)
        while subs and not subs[-1]:                        # a sub-field a voice lacks is left off the end
            subs.pop()
        out.append("@".join(subs))
    return out


RELATION_LETTERS = {R.MELODY: "m", R.COUNTER: "c", R.ACCOMP: "a", R.HARMONY: "h", R.ARP: "r", R.BASS: "b"}   # a relation's target part
RELATION_KINDS = {"double": "d", "parallel": "p", "own": "o"}


def bar_index(song: readings_mod.Song, t: float) -> int:
    """The index in song.bars of the bar beat `t` falls in (the last bar past the end, the first before the start)."""
    for k, (a, b) in enumerate(song.bars):
        if a - readings_mod.NEAR <= t < b - readings_mod.NEAR:
            return k
    return len(song.bars) - 1 if song.bars and t >= song.bars[-1][1] - readings_mod.NEAR else 0


RELATION_EDGE_BARS = 2               # a double or parallel stretch's first or last bars that read as the voice's own line, this many or
                                     # more and R.STRETCH_NOTES notes, are a stretch of their own (round 96)


def _split_own_edges(song: readings_mod.Song, rows: list, pitched: dict, v) -> list:
    """A relation stretch read whole over a sample run (roles.stretches_of) split where its edge bars are the voice's own
    line (round 96): at either end, a run of RELATION_EDGE_BARS bars or more whose notes, bar by bar, follow nothing
    (roles.stretch_relation against the voice the stretch follows), carrying R.STRETCH_NOTES notes or more, becomes an own
    stretch, RELATION_EDGE_BARS bars of the relation or more left between. Umaro's accompaniment voice doubles the tune two
    octaves up for five bars and then plays a chromatic run of its own on the same sample; read whole, the run was the
    double (First Meridian Return's accompaniment at midi 112, round 95). FFVI: 9 of 166 such stretches split, 138 notes."""
    out = []
    for row in rows:
        a, b, key, kind, of, semi, n = row
        if kind == "own" or of is None or of not in pitched:
            out.append(row)
            continue
        by_bar = {}
        for x in pitched[v]:
            if a - readings_mod.NEAR <= x[0] <= b + readings_mod.NEAR:
                by_bar.setdefault(bar_index(song, x[0]), []).append(x)
        keys = sorted(by_bar)
        own = {k: R.stretch_relation({"notes": by_bar[k], "a": by_bar[k][0][0], "b": by_bar[k][-1][0]}, {of: pitched[of]})[0] == "own" for k in keys}
        head = 0
        while head < len(keys) and own[keys[head]]:
            head += 1
        tail = 0
        while tail < len(keys) - head and own[keys[-1 - tail]]:
            tail += 1
        count = lambda ks: sum(len(by_bar[k]) for k in ks)   # noqa: E731
        head_ks = keys[:head] if head >= RELATION_EDGE_BARS and count(keys[:head]) >= R.STRETCH_NOTES else []
        tail_ks = keys[len(keys) - tail:] if tail >= RELATION_EDGE_BARS and count(keys[len(keys) - tail:]) >= R.STRETCH_NOTES else []
        middle = [k for k in keys if k not in head_ks and k not in tail_ks]
        if (not head_ks and not tail_ks) or len(middle) < RELATION_EDGE_BARS:
            out.append(row)
            continue
        row_of = lambda ks, kind_, of_, semi_: ((ns := [x for k in ks for x in by_bar[k]])[0][0], ns[-1][0], key, kind_, of_, semi_, len(ns))   # noqa: E731
        if head_ks:
            out.append(row_of(head_ks, "own", None, None))
        out.append(row_of(middle, kind, of, semi))
        if tail_ks:
            out.append(row_of(tail_ks, "own", None, None))
    return out


PARALLEL_SEMITONES = 24              # a parallel voice's interval to its line is counted within two octaves (round 97)
LEAD_ORDER = (R.MELODY, R.COUNTER, R.HARMONY, R.ACCOMP, R.ARP, R.BASS)   # who leads when two lines run parallel: the tune, then the counter, then the
                                     # chord parts, then the bass; the voice further down follows (parallel_interval_units counts each pair once)


def parallel_interval_units(songs) -> list:
    """Each shared onset of a parallel stretch (a voice's relation word's "p": roles.stretch_relation, its own edge bars
    split off) as a unit (round 97): its outcome where the voice's note sits against the chord sounding, the chord tone
    it lands on (root, third, fifth, seventh, sus: the writer places that tone of the written chord nearest the nominal
    interval, so a third over a major chord's third is its fifth at +3 and over a minor chord's +4) or, off the chord,
    its semitones from the line's note (`+4`, `-8`); its values the stretch's nominal interval in scale steps
    (roles.generic of the word's semitones: 2 a third up, -5 a sixth down), the tone class of the line's note against
    the chord (root, third, fifth, seventh, sus, other), the voice's part and the outcome before it in the stretch
    (START at the first). The voice followed is a part's line voice, as the
    writer's parallel voice follows a line; a line that reads as parallel to its own harmony voice is no unit, and two
    lines parallel to each other count once, the one further from the lead following (LEAD_ORDER: the tune leads, then
    the counter, the chord parts, the bass). The writer follows a parallel stretch by it
    (whole.parallel): FFVI's parallel voice sits at its nominal semitones on 0.61 of its shared onsets and on a chord
    tone on 0.62 (123 stretches, 10,057 onsets), where the line again in the scale, as the writer had it, matches the
    game's note on 0.31 of them and lands on the chord on 0.42: over the chord's third a third up is a major third or a
    minor sixth (the root), over the fifth a fourth (the root again) or a minor third (the seventh); a parallel voice is
    a harmony voice, not a shifted copy."""
    out = []
    for s in songs:
        pitched = {v: sorted((n[0], n[2], n[3]) for n in ns if n[2] is not None and not math.isnan(n[2]))
                   for v, (role, ns) in s.voice_notes.items() if role != R.DRUMS}
        pitched = {v: ns for v, ns in pitched.items() if ns}
        roles_of = {v: role for v, (role, _) in s.voice_notes.items()}
        lines = set()                                       # each part's line voice: the writer's parallel voice follows a line
        for role in set(roles_of.values()):
            voices = cells_mod.part_voices(s, role)
            if voices:
                lines.add(cells_mod.line_voice(voices, role, s))
        lead = {r: i for i, r in enumerate(LEAD_ORDER)}
        for v, rows in R.voice_relations(pitched).items():
            if len(pitched[v]) < R.SECOND_NOTES:
                continue
            for a, b, key, kind, of, semi, n in _split_own_edges(s, rows, pitched, v):
                if kind != "parallel" or of is None or of not in pitched or of not in lines or semi is None:
                    continue
                if v in lines and lead.get(roles_of.get(v), 9) <= lead.get(roles_of.get(of), 9):
                    continue                                # two lines parallel to each other: the one further from the lead follows (once)
                line = pitched[of]
                starts = [x[0] for x in line]
                nominal, previous = str(R.generic(semi)), readings_mod.START
                for t, m, _ in pitched[v]:
                    if t < a - R.STRETCH_NEAR or t > b + R.STRETCH_NEAR:
                        continue
                    lo, hi = bisect.bisect_left(starts, t - R.STRETCH_NEAR), bisect.bisect_right(starts, t + R.STRETCH_NEAR)
                    if lo == hi:
                        continue
                    k = min(range(lo, hi), key=lambda i: abs(starts[i] - t))
                    iv = int(round(m - line[k][1]))
                    c = _chord_at(s.chords, t)
                    if abs(iv) > PARALLEL_SEMITONES or c is None or c.root is None or c.fit < FIT:
                        continue
                    landing = vocab.tone_of(int(round(m)) % 12, c.root, c.shape)
                    outcome = landing if landing != "other" else f"{iv:+d}"
                    out.append(tables.Unit(s.sid, s.game, outcome, {"interval": nominal, "tone": vocab.tone_of(round(line[k][1]) % 12, c.root, c.shape),
                                                                     "part": roles_of.get(v, "?"), "previous": previous}))
                    previous = outcome
    return out


def relation_words(song: readings_mod.Song) -> dict:
    """Each pitched voice's relation stretches as the balance token has them (round 90): "ox9>dm-12x14>o". In each
    stretch (roles.stretches_of: a run of notes on one sample, blips folded) what the voice does beside another voice
    (roles.stretch_relation: a double at so many semitones, "d"; parallel at one generic interval, "p"; or its own line,
    "o"), the voice followed as its part's letter (RELATION_LETTERS; a voice with no part letter, a double or a drum, reads
    as own), then the stretch's bars counted from the song's first bar as round 85's pan word counts them, the last stretch
    open; stretches alike in kind, target and interval run together, and a voice of one own stretch, or of fewer than
    roles.SECOND_NOTES notes, has no word (the layers table's stands: a three-note voice's word would have the writer
    play a whole parallel line). Kefka's channel 1: "ox9>dm-12x14>o", its own line for nine bars, the tune an octave under
    for fourteen, its own again. The writer follows the word stretch by stretch (plan.stretched_notes)."""
    pitched = {v: sorted((n[0], n[2], n[3]) for n in ns if n[2] is not None and not math.isnan(n[2]))
               for v, (role, ns) in song.voice_notes.items() if role != R.DRUMS}
    roles_of = {v: role for v, (role, _) in song.voice_notes.items()}
    out = {}
    for v, rows in R.voice_relations({v: ns for v, ns in pitched.items() if ns}).items():
        if len(pitched[v]) < R.SECOND_NOTES:
            continue
        rows = _split_own_edges(song, rows, pitched, v)     # a stretch's own edge bars as stretches of their own (round 96)
        words = []
        for a, b, key, kind, of, semi, n in rows:
            letter = RELATION_LETTERS.get(roles_of.get(of)) if of is not None else None
            word = f"{RELATION_KINDS[kind]}{letter}{semi:+d}" if kind != "own" and letter else "o"
            end = bar_index(song, b)
            if words and words[-1][0] == word:
                words[-1][1] = end
            else:
                words.append([word, end])
        if len(words) == 1 and words[0][0] == "o":
            continue
        parts, prev = [], -1
        for i, (word, end) in enumerate(words):
            parts.append(word if i == len(words) - 1 else f"{word}x{max(1, end - prev)}")
            prev = max(prev, end)
        out[v] = ">".join(parts)
    return out


TUNED_SHARE = 0.5                    # a kit sample is tuned to the key where no one struck rate holds more than this share of the songs
                                     # that strike it (two or more), and its rate then moves with the written key (round 79): a crash at
                                     # -12 in 21 of 22 songs and a hat at 0 in 11 of 12 are sounds; a "snare" at +3, -4, +2, +3 and -17,
                                     # a tom at -20, -17 and -22, a sizzle at -2, +12 and -5 and a pad at -21 and -18 are tuned


def tuned_samples(songs) -> frozenset:
    """The kit samples the game tunes to the key (round 79): struck in two songs or more, with no one rate in more than
    TUNED_SHARE of them. FFVI: four of its kit samples, the pitch-bent snare, the tonal tom, Cyan's sizzle and the pad
    the namer took for a kick; one outlier among many (The Phantom Train's hat an octave up) makes no tuning."""
    rates = {}
    for s in songs:
        for key, rate in (getattr(s, "kit_rates", None) or {}).items():
            rates.setdefault("s" + key[:10] if len(key) >= 10 else key, []).append(rate)
    return frozenset(sid for sid, rs in rates.items() if len(rs) >= 2 and Counter(rs).most_common(1)[0][1] <= TUNED_SHARE * len(rs))


def kit_slot_samples(counts: Counter, levels: dict) -> dict:
    """The slot's pick (round 80), counted in readings since round 81 (readings.kit_slot_samples, SLOT_SHARE, SLOT_TIE_DB): the
    figures lean on the slots too."""
    return readings_mod.kit_slot_samples(counts, levels)


def kit_degree(s, pitch: int) -> str:
    """A tonal kit piece's struck note as a degree of the song's key (round 79): scale steps from the tonic (`d9`, 7 an
    octave, from the tonic's note in the fourth octave) where the note is on the song's scale, semitones (`c-3`) where it
    is off it, the voice words' own convention; the absolute note where the song has no key. FFVI strikes its tonal kit
    pieces in the song's scale in 10 of 12, and a written song's key is drawn apart from its balance token (40 of 45 sat
    in another key than the token's song), so Cyan's sizzle on the minor sixth had landed on the leading tone."""
    from .. import harmony
    from ..writer.tune import scale_index
    if s.tonic is None:
        return str(int(pitch))
    scale = {(s.tonic + i) % 12 for i in harmony.MODES["major" if s.mode == "major" else "natural_minor"]}
    tonic4 = 60 + s.tonic
    if int(pitch) % 12 in scale:
        return f"d{scale_index(int(pitch), scale) - scale_index(tonic4, scale)}"
    return f"c{int(pitch) - tonic4}"


def kit_channels(s) -> str:
    """The kit's channels as the drums token's fourth field (round 87): the slot letters each game channel plays, the
    channels in the song's order and the letters in LETTERS' order, joined by "|" ("KS|h": the kick and snare on one
    channel, the hat on another; "S|c"; "K"). A slot's channel is the one its sample is struck on most. The writer had put
    every kit on two voices by a fixed split (plan.DRUM_VOICES: kick, snare and toms on one, hat, cymbals and the rest on
    the other): FFVI puts 19 of its 47 kits on one channel, 20 on two, 8 on three or more, and 73 of its 90 kit channels
    carry one piece, the snare and the cymbal apart (8 songs) the commonest pair; the fixed two had cost a pitched voice
    in 14 of 48 kit songs (allot trims the band past eight) and dropped 2.2 % of the kit's hits where a kick struck under a
    snare the game had on its own channel."""
    counts, by_voice = Counter(), {}
    for v, (role, ns) in s.voice_notes.items():
        if role != R.DRUMS:
            continue
        for n in ns:
            key = n[3] if isinstance(n[3], str) else None
            piece = (s.pieces or {}).get(key)
            if key and piece in readings_mod.LETTERS:
                counts[(readings_mod.LETTERS[piece], key)] += 1
                by_voice.setdefault(key, Counter())[v] += 1
    if not counts:
        return ""
    best = kit_slot_samples(counts, getattr(s, "kit_levels", None) or {})
    channel_of = {letter: by_voice[key].most_common(1)[0][0] for letter, key in best.items() if key in by_voice}
    groups = {}
    for letter in readings_mod.LETTERS.values():
        if letter in channel_of:
            groups.setdefault(channel_of[letter], []).append(letter)
    return "|".join("".join(groups[v]) for v in sorted(groups))


def kit_second_units(songs) -> list:
    """Each hit of a kit letter the song strikes on two samples (readings.kit_second_samples) as a unit (round 99): its
    outcome whether the hit is on the letter's second sample ("second") or its slot's ("main"), its values the letter and
    the hit's place in the beat (readings.place: on the beat, an eighth, a sixteenth, a triplet, finer). The writer draws
    it a hit for a letter whose token carries a second, holding the letter's hits to the token's share for the second.
    FFVI's hats take the open hat on 0.50 of their eighth-note hits and 0.31 of their beats; its second snares take 0.86 of
    the sixteenths (the Battle Theme's rattle) and 0.59 of the beats."""
    out = []
    for s in songs:
        slots, seconds = readings_mod.kit_slots(s), readings_mod.kit_second_samples(s)
        if not seconds:
            continue
        for n in s.notes.get(R.DRUMS, []):
            key = n[3] if isinstance(n[3], str) else None
            letter = readings_mod.LETTERS.get((s.pieces or {}).get(key))
            if letter not in seconds or key not in (slots[letter], seconds[letter]):
                continue
            a = s.bars[bar_index(s, n[0])][0]
            out.append(tables.Unit(s.sid, s.game, "second" if key == seconds[letter] else "main",
                                   {"part": letter, "place": readings_mod.place(readings_mod.position(n[0] - a, s.division))}))
    return out


def kit_token(s, top: float = 0.0, tuned: frozenset = frozenset()) -> str:
    """The song's kit as a token field (round 63): each piece letter with the pack id of the sample the song's kit leans on
    for it (round 80, kit_slot_samples: the loudest of the samples struck a fifth of the letter's hits or more; the most
    struck until then), (`K=sbfe716b9b6,S=s1279e119a1`), in LETTERS' order; "" without drums. A song's kit is its own samples (FFVI:
    a median two drum samples a song, 31 over the game, and 17 of its 47 kits inside the pack's one kit of seven slots).
    Since round 68 each piece carries its own level too, where the readings heard one: the median level of the notes
    struck on that sample (Song.kit_levels, the loudness factor applied as the part's level has it) as a share of the
    song's loudest part's level `top` (`K=sbfe716b9b6@1.70,S=s1279e119a1@0.70,h=sd1c4c7ce33@0.20`; in hundredths since
    round 70, tenths before and still read: 163's snare at 0.14 kept as 0.1 had cost 2.9 dB on a quiet piece). The part's
    one level is the median over every note of every drum voice, which is the most frequent piece's: FFVI's hat is the
    most frequent and its strike the quietest, so Blackjack's token said drums at 0.2 of the top where its kick plays
    at 1.7 and its snare at 0.7, and the written kit was brought to one heard loudness a piece, the kick as quiet as
    a hat (Song Check 54's Whole 169: the kit 16 dB under Blackjack's). A piece without a level keeps the old form.
    Since round 75 each piece carries the note the song strikes it at most, after the level's slot, where the reading
    heard one (`o=sf89f5aedfd@0.38@62`; `o=sid@@62` without a level): FFVI's "other" pieces are tonal samples in ten
    tokens of eleven (a lead struck as an accent once in eight bars in The Phantom Forest, bells, pads), and the
    written kit had hammered them at the kit's one note two octaves under. A piece the namer called a drum carries the
    chip's rate instead, as a note with an r (`c=s3bfa4539ca@0.96@r48`: 60 as recorded, 48 an octave under; round 78: FFVI
    plays its crash an octave down in all 22 songs that use it, and a pad the namer took for a kick keeps its pitch through
    the rate, its own rate's note plus the offset). Since round 77 each piece carries the median
    length the song keys it for, in beats, after the note's slot (`o=sf89f5aedfd@0.38@62@0.25`; `K=s48bab384c7@1.00@27@6.95`
    a pad the namer took for a kick, held seven beats; `h=sd1c4c7ce33@0.20@@0.07` a hat): the writer gives a piece on a
    sustaining sample that hold where it had given every piece a one-beat hit, a tap of 69 ms held half a beat (The
    Unforgiven's "o", 9 dB out in front of the game's) and a seven-beat drone struck once (Another World of Beasts', Song
    Check 63); a percussion sample is a one-shot whatever its hit's length, so its hold is counted and not played. Since
    round 81 each slot carries its strike class after the hold (`h=s4135fb64a7@0.77@r67@0.95@a`: readings.SLOT_CLASSES,
    the sample's hits a bar in this song as rare under half, an accent under one, sparse to two, medium to six, dense over), and the drum
    figure tables condition on the kit's classes: the figure a letter plays had come from the pool at the kit's habit
    tier whatever the slot's sample did in its own song, so Strago's click, struck on beat two every other bar, played
    the hat's eighths (Song Check 65: "a smacking noise"), and Wild West's pitched blip, two a bar there, five a bar.
    Since round 82 a slot the game sends to echo carries an e after the class (`o=s5d5fe2fd48@1.21@d4@0.23@m@e`,
    kit_echo): the chip's echo is per channel, and the written kit had sent every piece or none by the echo word's
    one say for the drums part, drawn from another song; Wild West's blip is wet in the game and its kick dry. Since round 84 each slot carries its pan after the mark
    (`K=s48bab384c7@1.00@27@6.95@m@@0.45`: the median right-side share of the hits struck on the sample, PAN_BIN), so the kit
    sits in the stereo field where the game's did; FFVI pans a kit voice 0.1 or more off centre in 37 of 115. Since round
    99 a slot whose letter the song strikes on a second sample (readings.kit_second_samples: another sample with eight
    hits or more) carries that sample after a "+", with its level, its note or rate, its hold and its share of the
    letter's hits (`h=sd1c4c7ce33@0.14@r60@0.43@d@@0.50+s831784ce4b@0.14@r60@0.44@0.14`): the written kit had played one
    sample a letter, where FFVI's hats are a closed and an open hat in 12 of 16 kits."""
    counts = Counter()
    for n in s.notes.get(R.DRUMS, []):
        key = n[3] if isinstance(n[3], str) else None
        piece = (s.pieces or {}).get(key)
        if key and piece in readings_mod.LETTERS:
            counts[(readings_mod.LETTERS[piece], key)] += 1
    levels = getattr(s, "kit_levels", None) or {}
    best = kit_slot_samples(counts, levels)
    seconds = readings_mod.kit_second_samples(s)                 # each letter's second sample (round 99)
    classes = readings_mod.kit_classes(s)                        # each slot's strike class (round 81; over both samples since round 99)
    echo_marks = kit_echo(s)                                     # the slots the game sends to echo (round 82)
    pitches = getattr(s, "kit_pitches", None) or {}
    rates = getattr(s, "kit_rates", None) or {}               # a piece the namer called a drum: the chip's rate as a note, "r48" (round 78)
    holds = getattr(s, "kit_holds", None) or {}
    pans = getattr(s, "kit_pans", None) or {}                 # where each piece sits in the stereo field (round 84)
    out = []
    for letter in readings_mod.LETTERS.values():
        if letter not in best:
            continue
        key = best[letter]
        field = f"{letter}=" + ("s" + key[:10] if len(key) >= 10 else key)
        level = levels.get(key)
        with_level = top > 0 and level is not None and math.isfinite(level)   # never a "nan" share: the part's level stands in
        pitch, rate = pitches.get(key), rates.get(key)
        hold = holds.get(key)                                        # how long the song keys the piece for (round 77)
        sid = "s" + key[:10] if len(key) >= 10 else key
        slots = [f"{round(level / top, 2):.2f}" if with_level else "",                       # in hundredths since round 70: tenths cost 2.9 dB
                 (f"r{int(rate)}" + ("t" if sid in tuned else "")) if rate is not None       # on a snare at 0.14 kept as 0.1; a tuned rate (round 79)
                 else kit_degree(s, pitch) if pitch is not None else "",                     # a tonal piece's note as a degree of the key (round 79)
                 f"{hold:.2f}" if hold is not None and math.isfinite(hold) and hold > 0 else "",
                 classes.get(letter, ""),                                                  # the slot's strike class (round 81)
                 "e" if letter in echo_marks else "",                                      # the slot sends to echo (round 82)
                 f"{round(pans[key] / PAN_BIN) * PAN_BIN:.2f}" if key in pans and math.isfinite(pans[key]) else ""]   # its pan (round 84)
        while slots and not slots[-1]:                               # the old forms stand: a piece without a note or a hold ends at its level
            slots.pop()
        second = seconds.get(letter)
        if second:                                                   # the letter's second sample (round 99): its id, level, note, hold, share
            s2 = "s" + second[:10] if len(second) >= 10 else second
            level2, rate2, pitch2, hold2 = levels.get(second), rates.get(second), pitches.get(second), holds.get(second)
            share = counts[(letter, second)] / max(1, counts[(letter, key)] + counts[(letter, second)])
            subs = [s2, f"{round(level2 / top, 2):.2f}" if top > 0 and level2 is not None and math.isfinite(level2) else "",
                    (f"r{int(rate2)}" + ("t" if s2 in tuned else "")) if rate2 is not None else kit_degree(s, pitch2) if pitch2 is not None else "",
                    f"{hold2:.2f}" if hold2 is not None and math.isfinite(hold2) and hold2 > 0 else "", f"{share:.2f}"]
            field += "".join(f"@{x}" for x in slots) + "+" + "@".join(subs)
            out.append(field)
            continue
        out.append(field + "".join(f"@{x}" for x in slots))
    return ",".join(out)


def sample_range_in(notes, key: str) -> str:
    """The whole range a set of notes plays sample `key` over, as the registers word writes one ("32-52": part_register's
    grain, the ambitus); "" with fewer than eight pitched notes on it (round 86)."""
    reg = part_register([n for n in notes if n[3] == key], ambitus=True)
    return f"{reg[0]}-{reg[1]}" if reg else ""


def part_sample_field(s, role: str) -> str:
    """The balance token's eighth field (round 60's sample id) with, since round 86, the range the song plays that sample
    over in the part's line voice after an "@" (`s1d296a2572@32-52`): the voice written on the token's sample is bound to
    where the token song played it, not to a range drawn from the other songs that share the sample (FFVI shares 13 of
    its 17 bass samples, their per-song centres 15 semitones apart; the pooled draw had bound 11 of 27 written basses
    narrower than their planned register by 12 semitones at the median, and one an octave above it)."""
    sid = part_sample_id(s, role)
    if not sid or role == R.DRUMS:
        return sid
    notes = s.notes.get(role, [])
    voices = cells_mod.part_voices(s, role)
    if len(voices) >= 2:
        notes = voices[cells_mod.line_voice(voices, role, s)]
    keys = [n[3] for n in notes if isinstance(n[3], str) and n[3] and ("s" + n[3][:10] if len(n[3]) >= 10 else n[3]) == sid]
    rng = sample_range_in(notes, keys[0]) if keys else ""
    return f"{sid}@{rng}" if rng else sid


def own_sample_notes(notes: list) -> list:
    """A line's notes without the blips of another sample folded into its stretches (roles.stretches_of): a grace or an
    effect on another instrument is not where the line plays, so it widens neither the line's register (the balance
    token's second field) nor a stretch's range (round 104; Techno de Chocobo's tune read 28-79 from its effect notes
    where the tune plays 62-79). The notes as given where fewer than REGISTER_NOTES pitched ones would remain."""
    pitched = sorted((n[0], n[2], n[3]) for n in notes if isinstance(n[3], str) and n[3] and n[2] is not None and not math.isnan(n[2]))
    if len(pitched) < R.STRETCH_NOTES:
        return notes
    folded = {(t, m, k) for st in R.stretches_of(pitched) for t, m, k in st["notes"] if k != st["key"]}
    if not folded:
        return notes
    kept = [n for n in notes if not (isinstance(n[3], str) and (n[0], n[2], n[3]) in folded)]
    return kept if sum(1 for n in kept if n[2] is not None and not math.isnan(n[2])) >= REGISTER_NOTES else notes


def stretch_word(s, notes, sep: str = "@") -> str:
    """A voice's instrument by stretch as the balance token writes it (rounds 91 and 92): its pitched notes' stretches
    (roles.stretches_of, blips folded; consecutive stretches on one sample run together), each as its sample's pack id,
    `sep`, the range the voice plays it over there (the ambitus of the stretch's own sample's notes, part_register's grain;
    since round 104 a blip folded in from another sample does not widen it: Battle Theme's lead stretch had read 40-80
    from one synth note at 42 before bar 1 where the lead plays 64-79, and the written tune sat an octave under the lead)
    and its bars from the song's first bar as the pan word counts them, the last stretch open
    (`s77ca10e2568@52-64x6>sf89f5aedfd@60-80`); "" for a voice on one instrument or under roles.SECOND_NOTES notes."""
    pitched = sorted((n[0], n[2], n[3]) for n in notes if isinstance(n[3], str) and n[3] and n[2] is not None and not math.isnan(n[2]))
    if len(pitched) < R.SECOND_NOTES:
        return ""
    runs = []
    for st in R.stretches_of(pitched):
        sid = "s" + st["key"][:10] if len(st["key"]) >= 10 else st["key"]
        own = [(t, 0.0, m, k) for t, m, k in st["notes"] if k == st["key"]]    # the stretch's own sample's notes (round 104): a
        reg = part_register(own if len(own) >= REGISTER_NOTES else [(t, 0.0, m, k) for t, m, k in st["notes"]], ambitus=True)   # folded blip is not where it plays
        end = bar_index(s, st["b"])
        if runs and runs[-1][0] == sid:
            prev = runs[-1]
            both = (min(prev[1][0], reg[0]), max(prev[1][1], reg[1])) if prev[1] and reg else (prev[1] or reg)
            runs[-1] = (sid, both, end)
        else:
            runs.append((sid, reg, end))
    if len(runs) < 2:
        return ""
    parts, prev = [], -1
    for i, (sid, reg, end) in enumerate(runs):
        word = sid + (f"{sep}{reg[0]}-{reg[1]}" if reg else "")
        parts.append(word if i == len(runs) - 1 else f"{word}x{max(1, end - prev)}")
        prev = max(prev, end)
    return ">".join(parts)


RIDE_NOTES = 32                      # notes a chord part's line and the bass line need for the rides field (round 106)
RIDE_NEAR = 0.13                     # beats: an onset this near a bass onset strikes with it (half a sixteenth)
CHORD_NEAR = 0.3                     # beats: a chord span starting this near a bar line changes the chord there (round 106)


def line_rides_field(s, role: str) -> str:
    """The balance token's fifteenth field for a chord part (round 106): how far its line rides the bass line, the share
    of its onsets struck with a bass onset and, of those, the share at the bass's pitch class, in hundredths (`b75/70`:
    Battle Theme's guitar riff on its bass); "" where either line has under RIDE_NOTES pitched notes. The layer words'
    relation reader (roles.stretch_relation) asks for 0.8 of a stretch's notes with the other voice's and calls three
    FFVI chord lines a double or a parallel of the bass; Battle Theme's riff, 0.75 with the bass and 0.70 at its pitch
    class, is neither, and the writer had drawn its line's figures and tones apart from the bass it rides in the game."""
    if R.BASS not in s.notes or role not in s.notes:
        return ""
    line = [n for n in cells_mod.tune_line(s, role) if n[2] is not None and not math.isnan(n[2])]
    bass = sorted((n for n in cells_mod.tune_line(s, R.BASS) if n[2] is not None and not math.isnan(n[2])), key=lambda n: n[0])
    if len(line) < RIDE_NOTES or len(bass) < RIDE_NOTES:
        return ""
    starts = [n[0] for n in bass]
    both = same = 0
    for n in line:
        i = bisect.bisect_left(starts, n[0] - RIDE_NEAR)
        near = []
        while i < len(starts) and starts[i] <= n[0] + RIDE_NEAR:
            near.append(bass[i][2])
            i += 1
        if near:
            both += 1
            same += any(round(m) % 12 == round(n[2]) % 12 for m in near)
    return f"b{round(100 * both / len(line)):02d}/{round(100 * same / both) if both else 0:02d}"


def part_period_field(s, role: str) -> str:
    """The balance token's fourteenth field for a backing part (round 106): the part's own period, the lag in bars at
    which its bars repeat through the parts of the form that have one (cells.period_of, the periods word's own reading;
    the lag the most bars have), with the share of the bars inside it that play the bar a lag before again, in
    hundredths (`p2/83`: Battle Theme's bass, a two-bar riff held 0.83 of the time in its riff section); "" where no
    part of the form has a period. The writer had drawn a backing part's period and its holds from the pooled tables by
    the part of the form's length, so the riff under a Battle Theme song ran at the tables' lags and holds, not the
    song's."""
    if not getattr(s, "parts", None) or any(len(part) != 4 for part in s.parts):   # a song without a read form has no period
        return ""
    weight, held, total = Counter(), Counter(), Counter()
    for idx, n, keys in cells_mod._blocks(s):
        ks = keys.get(role)
        if ks is None or sum(1 for k in idx if ks[k]) < 2:
            continue
        lag = cells_mod.period_of(ks, idx)
        if not lag:
            continue
        weight[lag] += len(idx)
        for k in idx[lag:]:
            if ks[k] or ks[k - lag]:
                total[lag] += 1
                held[lag] += ks[k] == ks[k - lag]
    if not weight:
        return ""
    lag = weight.most_common(1)[0][0]
    return f"p{lag}/{round(100 * held[lag] / max(1, total[lag])):02d}"


def chord_hold_share(s) -> float | None:
    """The share of a song's bar lines that keep the chord sounding (round 106): the lines between its bars of the meter's
    length, after the first, that no chord span starts within CHORD_NEAR of; None under eight such lines or without
    chords. Battle Theme 0.53 (the chord reader hears its riff's chromatic neighbours as chords, so a riff song's share
    sits under what the ear holds). The chord chain had held a chord at its pooled rate alone."""
    if not getattr(s, "chords", None):
        return None
    bars = [b for b in s.bars if abs((b[1] - b[0]) - s.meter) < 0.01]
    lines = [lo for lo, hi in bars[1:]]
    if len(lines) < 8:
        return None
    starts = sorted(c.start for c in s.chords if c.start > 0)
    changes = sum(1 for t in lines if any(abs(a - t) < CHORD_NEAR for a in starts))
    return 1 - changes / len(lines)


def line_stretches(s, role: str) -> str:
    """The balance token's eleventh field (round 91): the line voice's instrument by stretch (stretch_word), where it has
    two or more; "" for a line on one instrument (the eighth field's sample and range stand). FFVI: 63 of 249 line voices
    change instrument (25 tunes, 19 counter-lines, 12 chord lines, 6 basses), two in three with the next stretch in another
    register (centres 7 semitones apart at the median), a stretch ten bars long at the median. Since round 92 the writers
    write the line in each stretch's register (a register a bar); the render plays each note on its stretch's sample
    (render.sample_of); the eighth field's sample stays the line's default."""
    if role == R.DRUMS:
        return ""
    notes = s.notes.get(role, [])
    voices = cells_mod.part_voices(s, role)
    if len(voices) >= 2:
        notes = voices[cells_mod.line_voice(voices, role, s)]
    return stretch_word(s, notes, "@")

def part_sample_id(s, role: str) -> str:
    """The pack's id of the sample a part plays most (its notes' sample key, `s` and the key's first ten characters as
    the pack names it); "" without notes. Round 60 (2026-10-29): FFVI puts 224 of its 1326 possible sample pairs
    together, a lead sample has a median one bass partner, and a song's pairs are seen in another of its songs 0.80 of
    the time; the written songs' pairs, each part's sample drawn apart, 0.55, under chance (0.67): the balance token's
    song lends its instruments with its levels, which were counted on those very samples. Since round 70 the LINE
    voice's sample where the part holds two voices or more (cells.line_voice): the most-played over all voices was the
    busier second voice's, and Troops March on's and Overture's bass lines on sa692eac0a6 under a second voice on
    s1d296a2572 had put both written voices on s1d296a2572 (the layer token carries the second's)."""
    notes = s.notes.get(role, [])
    if role != R.DRUMS:
        voices = cells_mod.part_voices(s, role)
        if len(voices) >= 2:
            notes = voices[cells_mod.line_voice(voices, role, s)]
    c = Counter(n[3] for n in notes if isinstance(n[3], str) and n[3])
    if not c:
        return ""
    key = c.most_common(1)[0][0]
    return "s" + key[:10] if len(key) >= 10 else key


PAN_BIN = 0.05                       # a voice's pan, the right side's share, kept to twentieths (round 84; readings.PAN_BIN, which this package imports around)


def pan_word(song: readings_mod.Song, voice) -> str:
    """One voice's entry in the balance token's tenth field: its pan ("0.50"); since round 85 its two places where it
    has them (readings.pan_moves): "0.60x5|0.45x13" back and forth, A for 5 bars then B for 13 and again, or
    "0.35x4>0.65" moving once, A for 4 bars then B for the rest."""
    moves = (getattr(song, "voice_pan_moves", None) or {}).get(voice)
    if moves:
        a, na, b, nb = moves
        return f"{a:.2f}x{na}>{b:.2f}" if nb is None else f"{a:.2f}x{na}|{b:.2f}x{nb}"
    return f"{round(song.voice_pans[voice] / PAN_BIN) * PAN_BIN:.2f}"


def pan_field(song: readings_mod.Song, role: str) -> str:
    """The balance token's tenth field (round 84): the pan of each of a pitched part's voices, the line voice first and
    the voices beyond it in voice_level_shares' order, each the median right-side share of its notes kept to PAN_BIN
    ("0.50"; "0.35/0.65"); "" where the readings hold no pan for the line, and the line's alone where a voice beyond it
    has none (the ranks must line up with the sixth field's). The writer had panned every song alike (plan.PANS: the
    tune at centre, the counter at 0.6, the accompaniment's voices 0.6 and 0.4), where FFVI sits half its voices 0.1 or
    more off centre (the melody in 37 of 76, the counter 63 of 111, the accompaniment 72 of 153) and a part's voices
    0.15 to 0.18 apart at the median; with the field a song's stereo picture is one FFVI song's, with its levels."""
    pans = getattr(song, "voice_pans", None) or {}
    voices = cells_mod.part_voices(song, role)
    if not voices:
        return ""
    line = cells_mod.line_voice(voices, role, song)
    if line not in pans or not math.isfinite(pans[line]):
        return ""
    others = sorted((v for v in voices if v != line), key=lambda v: (-len(voices[v]), v))
    order = [line] + others if all(v in pans and math.isfinite(pans[v]) for v in others) else [line]
    return "/".join(pan_word(song, v) for v in order)


def line_motion(s, role: str, line_notes=None) -> str:
    """A chord part's line voice's motion as the balance token carries it (round 103): the share of its strikes whose pitch
    differs from the strike before's, as MOTIONS' class (block under a third, mixed, arpeggiated over two thirds;
    readings.upper_motion on the line alone, where the motions word counts the whole part's strikes); "" under WORD_NOTES
    notes. FFVI's Battle Theme: the guitar riff moves on 0.37 of its strikes under two arpeggiating string voices, and the
    pooled motions draw had arpeggiated the guitar in a written song."""
    notes = line_notes if line_notes is not None else cells_mod.tune_line(s, role)
    pitched = [n for n in notes if not math.isnan(n[2])]
    if len(pitched) < WORD_NOTES:
        return ""
    return readings_mod.habit_of(readings_mod.upper_motion(pitched), readings_mod.MOTIONS)


def line_tone_tier(s, role: str) -> str:
    """A chord part's line's off-chord tier as the balance token carries it (round 103): tone_tier_of its share of onsets
    off the chord sounding over its bars (_tone_bars, the tone_tiers word's own measure for the song); "" where the line
    is under WORD_NOTES notes or no chord fits."""
    for _, r, bars in _tone_bars([s]):
        if r == role:
            return tone_tier_of(_tone_share(bars))
    return ""


def balance_units(songs) -> list:
    """Each song as a unit: its outcome its band with, for each pitched
    part, its weight, its register, the share of its gap a note sounds,
    its voices, its level as a share of the song's loudest part's in
    tenths (level_units' unit; the loudest part "1.0") and, where it holds
    two voices or more, each voice beyond the line's level over the line
    voice's in tenths (voice_level_shares, the layer_levels unit, the
    busiest voice first, joined by "/")
    and, for the counter, whether it plays the tune's sample (counter_kind,
    a seventh field: "counter=minor:56-72:0.9:1:1.0::other")
    ("accompaniment=main:56-68:0.8:2:0.7:1.3 bass=half:28-40:0.9:1:1.0
    drums=::::0.8 melody=half:64-84:0.9:1:0.8"; the drums, which carry no
    weight, register or sounded share, keep their level in the same fifth
    field); its value the part (arrangement). What a song written with no
    original draws its band, balance and layout from, as one of the
    game's songs has them together: drawn a part at a time, a bass sat
    above the accompaniment and a counter-line two octaves under its
    instrument (the Song Check's notes, 2026-10-23). The levels joined the
    token in round 32 (2026-10-24): drawn a part at a time from `levels`,
    the accompaniment had landed strictly above the tune in 0.30 of plans
    against FFVI's 0.17 (its band-themed songs 0.06) and at 1.2 times the
    tune or more in 0.24 against 0.12 (0.00), and the same product awaited
    the harmony and the bass; as a field of the token, a song's level
    layout is one of the game's songs' whole, as its registers, sounds and
    voice counts already were, and the game's joint holds by construction.
    The second voices' levels joined it in round 33 (2026-10-25): a part's
    second voice at a `layer_levels` draw of its own on a line whose level
    was the token's had stacked 1.5 on lines at the tune's level or more
    (Whole 03's accompaniment 1.8 times the tune, Whole 15's 1.96 at the
    cap of full), where FFVI's loud second voices (1.5 or more, 12 of 43
    layered accompaniments) sit on lines at 0.59 of the tune and reach 1.21
    times it at the median; with the field, the line and the voices beside
    it are one song's together. One share a voice beyond the line, since
    the token's voice count is the song's and a third or later voice's
    share differs from the second's in 23 of FFVI's 52 (in 19 of its 40
    parts with three voices or more: Gau 1.5 then 3.2 before the cap,
    Dancing Mad's bass 1.1 then 2.0). The counter's kind joined it in round
    39 (2026-10-27): a seventh field on the counter's token, whether it
    plays the tune's sample (counter_kind: same, other). The level had been
    the token's and the kind a draw of its own (counter_samples), so Whole
    33 took The Serpent Trench's level, the one FFVI counter at 1.78 times
    its tune (28 held notes on another sample in 14 of the tune's 33 bars),
    and played it as a doubling on the tune's sample at the tune's onsets
    (+4.4 dB over the tune, the stems' median); FFVI's counters on the
    tune's sample at its onsets sit at 1.0 times the tune in 13 of 16 and
    never above 1.21, and its 7 counters louder than the tune are, bar one,
    on another sample. With the field, what the counter is and how loud it
    is are one song's together. The song's tempo class joined it in round
    54 (2026-10-29), a last token `tempo=slow` (band), and the loudest
    part's level of full in round 59 (`top=0.30`, TOP_LEVEL_BIN; the
    top_levels word stays as the fallback for a token without it) with the
    song's rendered loudness (`loud=-24`, Song.loudness, RMS dBFS; the
    written song's master volume holds its own to it), and in round 60 each
    part's own sample as an eighth field (part_sample_id: the song's
    instruments come with its levels), and in round 62 each part's habit
    as a ninth (`dense+varied`, the kit's too), so the song's density tiers
    come together (drawn apart, 54 % of written songs had exactly one dense
    part against FFVI's 38 %, a busy accompaniment under a medium tune):
    the tempo drawn
    apart had put Relm's band (70) at 160 beats a minute and Slam
    Shuffle's (114) at 70, and only 14 of 45 plans sat in their token
    song's class; the `tempos` word is drawn again under the class where
    the plan's draw falls outside it. Since round 70 (2026-10-30) the
    fifth field is the LINE voice's median level (readings.part_levels)
    and the eighth the line voice's sample (part_sample_id), so that the
    line times each sixth-field share reproduces every voice of the part
    and the voices beside the line play the samples the token names for
    them (Troops March on's counter line had played at 0.40 of the top
    where it sits at 0.27, its bass line on the second voice's sample). The
    pans joined it in round 84 (2026-11-06): a tenth field a pitched part
    (pan_field: each voice's right-side share, the line first) and a slot
    field a kit piece (kit_token), where the writer's fixed pans had given
    every written song one stereo picture; and in round 85 a voice's two
    places where it has them (pan_word: "0.60x5|0.45x13", "0.35x4>0.65"). Since
    round 91 an eleventh field a pitched part whose line changes instrument
    (line_stretches: `s77ca10e2568@52-64x6>sf89f5aedfd@60-80`, each stretch's
    sample, range and bars), so the written line changes colour and register
    where its song's did."""
    habit_of_part = {}                                    # (song, part) -> the part's habit (round 62: the song's density tiers ride the token)
    for u in readings_mod.habits(readings_mod.units(songs)) + readings_mod.habits(readings_mod.bass_units(songs)):
        habit_of_part[(u.song, u.values["part"])] = u.outcome
    for u in readings_mod.drum_habit_units(songs):
        habit_of_part[(u.song, R.DRUMS)] = u.outcome
    tuned = tuned_samples(songs)                             # the kit samples the game tunes to the key (round 79), over the game
    out = []
    for s in songs:
        if not s.notes:
            continue
        weights = readings_mod.part_weights(s)
        voices = Counter(role for role, _ in s.voice_notes.values())
        finite = {role: lv for role, lv in s.levels.items() if math.isfinite(lv)}   # never a "nan" field: the plan's draw stands in
        top = max(finite.values()) if finite else 0.0
        levels = {role: f"{round(lv / top, 1):.1f}" for role, lv in finite.items()} if top > 0 else {}
        tokens = []
        for role in sorted(s.notes):
            if role not in weights:
                dh = habit_of_part.get((s.sid, role), "").replace(" ", "+")   # the kit's habit as the ninth field (round 62)
                fields = ["", "", "", kit_channels(s), levels.get(role, ""), "", "", kit_token(s, top, tuned), dh]   # and its kit as the eighth (round 63; each
                                                                                             # channel's pieces as the fourth, round 87;
                                                                                             # piece's own level beside its sample, round 68)
                while fields and not fields[-1]:
                    fields.pop()
                tokens.append(role + ("=" + ":".join(fields) if fields else ""))
                continue
            reg = part_register(own_sample_notes(cells_mod.register_notes(s, role) or s.notes[role]), ambitus=role == R.MELODY)   # blips of another sample left out (round 104)
            line_notes = cells_mod.tune_line(s, role)       # the line voice's notes where the part has two or more (round 95: the part's merged
            share = cells_mod.sounded_share(line_notes)     # voices had put the gap to the other voice's note under a note's length, 0.8 for
            by_gap = cells_mod.gap_shares(line_notes) if role in readings_mod.UPPER + (R.BASS,) else None   # Umaro's 0.4 pecks)
            beside = layer_tokens(s, role) if role in levels else None   # each voice beyond the line: level, sample, note share (round 65)
            kind = cells_mod.counter_kind(s) if role == R.COUNTER and role in levels else None
            fields = [weights[role], f"{reg[0]}-{reg[1]}" if reg else "",
                      (f"{round(share / cells_mod.SOUND_BIN) * cells_mod.SOUND_BIN:.1f}" if share is not None else "")
                      + ("@" + "/".join(f"{x:.1f}" if x is not None else "-" for _, g in cells_mod.GAP_CLASSES for x in (by_gap[g],)) if by_gap and any(x is not None for x in by_gap.values()) else ""),   # the line's share by gap class (round 95)
                      str(max(1, voices.get(role, 1))), levels.get(role, ""), "/".join(beside) if beside else "", kind or "",
                      part_sample_field(s, role),             # the part's own sample (round 60) and where the song plays it (round 86)
                      habit_of_part.get((s.sid, role), "").replace(" ", "+"),   # and its habit (round 62): the song's density tiers together
                      pan_field(s, role),                     # and its voices' pans (round 84): the song's stereo picture together
                      line_stretches(s, role),                # and the line's instrument by stretch (round 91)
                      line_motion(s, role, line_notes) if role in readings_mod.UPPER else "",   # a chord part's line motion (round 103)
                      line_tone_tier(s, role) if role in readings_mod.UPPER else "",           # and its off-chord tier (round 103)
                      part_period_field(s, role) if role in cells_mod.BACKING and role != R.DRUMS else "",   # the part's own period and holds (round 106)
                      line_rides_field(s, role) if role in readings_mod.UPPER else ""]         # and how far the line rides the bass (round 106)
            while fields and not fields[-1]:                 # a field a song lacks is left off the end, not left empty
                fields.pop()
            tokens.append(f"{role}=" + ":".join(fields))
        if s.echo is not None:                               # the song's echo word (round 82): the written song sits in its token song's room
            tokens.append("echo=" + echo_outcome(s))
        if s.tonic is not None:                              # the song's key (round 79): what the kit's degrees and tuned rates are read against
            tokens.append(f"key={s.tonic}:{'major' if s.mode == 'major' else 'minor'}")
        holds = chord_hold_share(s)                          # the song's chord-hold share (round 106): how long its chords sit
        if holds is not None:
            tokens.append(f"holds={holds:.2f}")
        if s.bpm:                                            # the song's tempo class (round 54): the band comes with the pace it was made for
            if s.levels:                                    # the song's loudest part's level of full (round 59): with its own levels, a song whose
                top = max(s.levels.values())                # three parts share the top has a lower top (FFVI: 0.30 with one part there, 0.22 with
                tokens.append(f"top={round(top / TOP_LEVEL_BIN) * TOP_LEVEL_BIN:.2f}")   # three, 0.10 with four); drawn apart, four at the top played at 0.68
            if s.loudness is not None:                      # and the song's rendered loudness (round 59): what the written song's master holds
                tokens.append(f"loud={round(s.loudness / MIX_BIN) * MIX_BIN:.0f}")   # its own to
            tokens.append(f"tempo={readings_mod.band(s.bpm)}")
        out.append(tables.Unit(s.sid, s.game, " ".join(tokens), {"part": ARRANGEMENT}))
    return out


ECHO_PART = "echo"                   # the echo word's part value (a song-level word, as the balance's ARRANGEMENT is)
ECHO_SEND = 0.5                      # a voice sends when this share of its notes or more do; a part when half its voices or more send


def echo_units(songs) -> list:
    """Each song whose echo the readings hold (Song.echo, round 70) as a unit: its outcome the echo's volume of full, its
    delay in ms, its feedback, the parts that send to it and the parts that stay dry
    ("0.20:80:0.78:accompaniment+counter+melody:bass+drums"; a part sends when half its voices or more send ECHO_SEND
    of their notes or more; "-" where no part does, or none stays dry); its value the part (echo). Drawn once a song on
    its own stream, in place of the generator's constant and delay names (score.ECHO_WET 0.4, "slap"): FFVI's echo
    volume is 0.20 of full in 70 of 82 songs, its delay 80 ms in every one, its feedback 0.78 at the median, and the
    tune sends in 74 of 75 songs, the counter in 55 of 58, the accompaniment in 56 of 69, the bass in 45 of 72, the
    drums in 17 of 52 (round 69); the written songs had sent every upper part at 0.4 (6 dB wetter) with a 48-144 ms
    delay, which the owner heard as vibrato and blur (Song Check 54's Whole 166). The sends ride the word so the song's
    joint holds; a written part named in neither list (the word's song lacked it) keeps the writer's old rule."""
    return [tables.Unit(s.sid, s.game, echo_outcome(s), {"part": ECHO_PART}) for s in songs if s.echo is not None]


def echo_outcome(s) -> str:
    """A song's echo word as the echo table's outcome ("0.20:80:0.78:accompaniment+melody:bass+drums"; see echo_units): the
    volume of full, the delay in ms, the feedback, the parts that send, the parts that stay dry. Since round 82 the
    balance token carries it too (`echo=...`), so a written song sits in its token song's room."""
    by_role = {}
    for v, (role, ns) in s.voice_notes.items():
        if role in readings_mod.PARTS and ns and v in s.echo_sends:
            by_role.setdefault(role, []).append(s.echo_sends[v] >= ECHO_SEND)
    sends = sorted(role for role, flags in by_role.items() if sum(flags) * 2 >= len(flags))
    dry = sorted(role for role in by_role if role not in sends)
    volume, ms, feedback = s.echo
    return f"{volume:.2f}:{ms:.0f}:{feedback:.2f}:{'+'.join(sends) or '-'}:{'+'.join(dry) or '-'}"


def kit_echo(s) -> set:
    """The kit slots the game sends to echo (round 82): the letters whose slot's sample has ECHO_SEND of its hits or more on
    drum voices that send (Song.echo_sends, the chip's per-voice send at key-on). FFVI's echo is per channel, so a kit's
    pieces split: Wild West sends its pitched blip and keeps its kick, hat and toms dry; Cyan sends its sizzle. {} where
    the readings hold no sends."""
    sends = getattr(s, "echo_sends", None) or {}
    by_sample = getattr(s, "echo_sample_sends", None) or {}   # the sample's own share where the readings hold it (the chip toggles
    if not sends and not by_sample:                          # echo note by note: Wild West's channel 4 holds its hat dry, its blip wet)
        return set()
    slots = readings_mod.kit_slots(s)
    hits, wet = Counter(), Counter()
    for v, (role, ns) in s.voice_notes.items():
        if role != R.DRUMS:
            continue
        for n in ns:
            if isinstance(n[3], str):
                hits[n[3]] += 1
                if sends.get(v, 0.0) >= ECHO_SEND:
                    wet[n[3]] += 1
    return {letter for letter, key in slots.items()
            if (by_sample[key] >= ECHO_SEND if key in by_sample else hits[key] and wet[key] >= ECHO_SEND * hits[key])}


VIBRATO_DEPTH_BIN = 5.0              # cents the word's depth is kept to
VIBRATO_RATE_BIN = 0.5               # Hz
VIBRATO_ONSET_BIN = 0.1              # seconds
VIBRATO_SHARE_BIN = 0.1              # a class's share of held notes, in tenths


def vibrato_units(songs) -> list:
    """Each pitched part of each song whose vibrato the readings hold (Song.vibrato, round 72) as a unit: its outcome
    the share of the part's held notes that carry vibrato in each length class (VIBRATO_CLASSES: 0.35-0.5 s, 0.5-1,
    1-2, 2 and over; in tenths, "-" for a class the song held no note in), then the depth in cents either side, the
    rate in Hz and the onset in seconds from key-on ("0.0/0.1/0.3/0.3:30:5.5:0.5"; "0.0/0.0/-/-:0:0:0" for a part
    with no vibrato at all); its value the part. One unit a part a song, so the shares and the shape ride together;
    the shape is the busiest vibrato voice's. Drawn once a song a part by the player's performance (not the writer:
    vibrato is a performance of the written score) on its own stream, in place of a fixed rule (10 cents at 5.5 Hz
    on every note over 0.35 s): FFVI's tunes carry it on a fifth of their held notes, deeper and later."""
    out = []
    for s in songs:
        if not s.vibrato:
            continue
        for role in readings_mod.PITCHED:
            voices = [v for v, (r, ns) in s.voice_notes.items() if r == role and v in s.vibrato]
            if not voices:
                continue
            held = [sum(s.vibrato[v]["held"][k] for v in voices) for k in range(4)]
            vib = [sum(s.vibrato[v]["vib"][k] for v in voices) for k in range(4)]
            if not sum(held):
                continue
            shares = "/".join(f"{round(vib[k] / held[k] / VIBRATO_SHARE_BIN) * VIBRATO_SHARE_BIN:.1f}" if held[k] else "-" for k in range(4))
            busiest = max(voices, key=lambda v: sum(s.vibrato[v]["vib"]))
            d = s.vibrato[busiest]
            if sum(d["vib"]) and "depth" in d:
                shape = (f"{round(d['depth'] / VIBRATO_DEPTH_BIN) * VIBRATO_DEPTH_BIN:.0f}:{round(d['rate'] / VIBRATO_RATE_BIN) * VIBRATO_RATE_BIN:.1f}"
                         f":{round(d['onset'] / VIBRATO_ONSET_BIN) * VIBRATO_ONSET_BIN:.1f}")
            else:
                shape = "0:0:0"
            out.append(tables.Unit(s.sid, s.game, f"{shares}:{shape}", {"part": role}))
    return out


def vibrato_word(outcome: str) -> dict | None:
    """A vibrato unit's outcome read back: {"shares": [a class's share or None], "depth", "rate", "onset"}; None for
    a malformed one."""
    fields = outcome.split(":")
    if len(fields) != 4:
        return None
    try:
        shares = [None if x == "-" else float(x) for x in fields[0].split("/")]
        if len(shares) != 4:
            return None
        return {"shares": shares, "depth": float(fields[1]), "rate": float(fields[2]), "onset": float(fields[3])}
    except ValueError:
        return None


SAMPLE_PARTS = (R.MELODY, R.BASS, R.ACCOMP, R.HARMONY, R.ARP)   # the parts whose sample the part_samples word gives (the counter's is
                                                                # counter_samples/counter_pairs', a second voice's layer_samples')


def part_sample_units(songs) -> list:
    """Each pitched part of each song (SAMPLE_PARTS) as a unit: its outcome the sample its line plays most, as a pack
    names it ("s" and the key's first ten characters); its values the part and the speed class of the part's fastest
    bar (speed_tier). Which instrument a part plays (round 42, 2026-10-28): chosen by a pool rule (the best range fit),
    0.73 of the written tunes had played one string pad, which FFVI gives 0.31 of its tunes, spreading the rest over
    eight instruments and more; the pack's range and speed words then bound the writing to where the game plays it."""
    out = []
    for s in songs:
        for role in SAMPLE_PARTS:
            if not s.notes.get(role):
                continue
            key = cells_mod.main_sample(cells_mod.tune_line(s, role) or s.notes[role])
            if not key or not isinstance(key, str):
                continue
            fastest = cells_mod.part_fastest(s, role)
            values = {"part": role}
            if fastest is not None:
                values["speed"] = cells_mod.speed_tier(fastest)
            out.append(tables.Unit(s.sid, s.game, "s" + key[:10], values))
    return out


ATTACK_STRUCK = 2.0                   # a sample whose strike is this many times its loop body (6 dB) decays: struck


def attack_units(songs) -> list:
    """Each pitched part of each song (SAMPLE_PARTS) as a unit: whether the sample its line plays most is struck (its
    first STRIKE_SECONDS more than ATTACK_STRUCK times its loop body: a sound that decays after the attack) or
    sustaining, its value the part. The samples' loudness is what set_loudness holds (readings.SAMPLE_LOUDNESS and
    SAMPLE_STRIKE), so a count without it yields no units. Round 73 (2026-10-31): FFVI's tunes ride a struck sample in
    3 of 66 songs (Awakening, Spinach Rag, Good Night), while a built-in set's keys, 14 to 20 dB struck, took 6 of 10
    default tunes once the bright leads' ranges were capped, and a tune that fades between its notes reads weak at any
    measured level (Song Checks 59 and 60). A built-in set's pool rule matches the drawn class (render.best_sample)."""
    out = []
    for s in songs:
        for role in SAMPLE_PARTS:
            if not s.notes.get(role):
                continue
            key = cells_mod.main_sample(cells_mod.tune_line(s, role) or s.notes[role])
            if not key or not isinstance(key, str):
                continue
            sid = "s" + key[:10]
            body, strike = readings_mod.SAMPLE_LOUDNESS.get(sid), readings_mod.SAMPLE_STRIKE.get(sid)
            if not body or not strike:
                continue
            out.append(tables.Unit(s.sid, s.game, "struck" if strike > ATTACK_STRUCK * body else "sustaining", {"part": role}))
    return out


def kit_rate_units(songs) -> list:
    """Each percussion kit sample a song strikes, as a unit: its outcome the rate the chip strikes it at most, as a note
    (60 as recorded, 48 an octave under; Song.kit_rates), its values the sample's id as a pack names it and the piece
    the namer called it (round 88). The wall a tuned slot's moved rate stays inside: round 79 moves a tuned sample's rate
    with the written key, by up to a tritone, and over FFVI's tuned slots and the twelve keys a written song can land in
    the moved rate fell outside the rates the game ever struck the sample at as that piece in 77 of 132 cases. Fanfare's
    pitched snare, struck at -4 there and -4 to +3 wherever FFVI uses it as a snare, had been moved to -10 for a song in
    C# minor, where its 220 Hz tone fell to B2 and rang twice as long: a guitar, the owner heard (Song Check 70)."""
    out = []
    for s in songs:
        for key, rate in (getattr(s, "kit_rates", None) or {}).items():
            letter = readings_mod.LETTERS.get((s.pieces or {}).get(key))
            if letter:
                out.append(tables.Unit(s.sid, s.game, str(int(rate)), {"part": "s" + key[:10] if len(key) >= 10 else key, "piece": letter}))
    return out


def sample_ambitus_units(songs) -> list:
    """Each sample a song plays pitched, as a unit: its outcome the whole range the song played it in, lowest note to
    highest (part_register's grain, ambitus=True), its value the sample's id as a pack names it. The tune's bound
    (round 43, 2026-10-28): the ranges word is the sample's home band (the notes' 10th to 90th percentiles, 16
    semitones for FFVI's string pad), and bounding the tune by it had held the written tunes to 15 semitones where
    FFVI's span 21.5 (22 on that pad): a tune leaves its home band for its climax, and its bound is where the game
    took the sample at all."""
    out = []
    for s in songs:
        by_key = {}
        for role, ns in s.notes.items():
            if role == R.DRUMS:
                continue
            for n in ns:
                by_key.setdefault(n[3], []).append(n)
        for key, ns in by_key.items():
            reg = part_register(ns, ambitus=True)
            if reg is not None and isinstance(key, str):
                out.append(tables.Unit(s.sid, s.game, f"{reg[0]}-{reg[1]}", {"part": "s" + key[:10]}))
    return out


def sample_range_units(songs) -> list:
    """Each sample a song plays pitched, as a unit: its outcome the register
    the song played it in (part_register's grain), its value the sample's
    id as a pack names it ("s" and the key's first ten characters). What a
    planned song picks a part's sample by: one the game played in the
    part's register, never a flute four octaves under its recording."""
    out = []
    for s in songs:
        by_key = {}
        for role, ns in s.notes.items():
            if role == R.DRUMS:
                continue
            for n in ns:
                by_key.setdefault(n[3], []).append(n)
        for key, ns in by_key.items():
            reg = part_register(ns)
            if reg is not None and isinstance(key, str):
                out.append(tables.Unit(s.sid, s.game, f"{reg[0]}-{reg[1]}", {"part": "s" + key[:10]}))
        for role, ns in s.notes.items():                     # and by the part that plays it (round 55): a sample shared by parts sits 9
            if role == R.DRUMS:                              # semitones apart by part at the median, a bass sample 54 (bass 32, accompaniment 86)
                continue
            for key in {n[3] for n in ns if isinstance(n[3], str)}:
                reg = part_register([n for n in ns if n[3] == key])
                if reg is not None:
                    out.append(tables.Unit(s.sid, s.game, f"{reg[0]}-{reg[1]}", {"part": "s" + key[:10], "role": role}))
    return out


LAYER_DENSITY = ((0.5, "sparser"), (2.0, "like"), (1e9, "denser"))   # a second voice's strikes against the line's
LAYER_OFFSET = 24                    # semitones: a second voice's register against the line's is kept within this, to REGISTER_BIN


VOICE_STEPS = 14                     # scale steps: a voice beside the line's interval or move is counted within two octaves
VOICE_SEMITONES = 24                 # semitones: a voice's interval against a line note off the scale, within two octaves (round 66)


def _beside_lines(songs):
    """Every voice beside a line in an upper part with two voices or more (apart or alternating; a doubling voice follows
    the line), the bass's and, since round 76, the counter's own voices beside its line (part counter, kind apart or
    alternating: FFVI's layered counters hold two to four voices in 11 of the 46 kit tokens' songs, block chords and
    parallel lines under the counter's line, and the writer had left every one of them silent beside a counter that
    follows the tune, "no word yet"), and the counter-line beside the tune (part counter; its kind the sample relation,
    counter_kind, which splits FFVI's intervals: thirds on the tune's sample, octaves and unisons on another; the two
    never share a context, the kinds differ): (song, part, kind, the voice's notes, the line's notes, the song's scale),
    sorted in time."""
    from .. import harmony, harness                         # harness imports this module
    pitched = lambda ns: sorted((n for n in ns if not math.isnan(n[2])), key=lambda n: n[0])   # noqa: E731
    for s in songs:
        scale = {((s.tonic or 0) + i) % 12 for i in harmony.MODES["major" if s.mode == "major" else "natural_minor"]}
        for role in readings_mod.UPPER + (R.BASS, R.COUNTER):             # the bass too: its second voice plays the line's pitch class at 78 % of
            voices = cells_mod.part_voices(s, role)                   # their shared onsets in FFVI; written apart it had at 31 % (2026-10-24)
            if len(voices) < 2:
                continue
            line = cells_mod.line_voice(voices, role, s)
            lns = pitched(voices[line])
            for other in sorted((v for v in voices if v != line), key=lambda v: (-len(voices[v]), v)):
                kind = harness.relation(voices[line], voices[other])[0]
                if kind == "doubling" or not lns:
                    continue
                yield s, role, kind, pitched(voices[other]), lns, scale
        kind = cells_mod.counter_kind(s)                              # the counter-line beside the tune's line (round 29)
        if kind is not None:
            lns, cns = pitched(cells_mod.tune_line(s, R.MELODY)), pitched(cells_mod.tune_line(s, R.COUNTER))
            if lns and cns:
                yield s, R.COUNTER, kind, cns, lns, scale


def _voice_walk(songs):
    """Each onset of a voice beside a line: (song, part, kind, with the line?, steps from the line's note struck or last
    struck, the voice's move in steps from its own previous note or None, the interval at its previous onset with the
    line or START, the line note's state (scale or altered: off the song's scale) and the interval as the word's outcome
    (the steps, or "s" and the semitones against an altered line note)."""
    from .. import writer                                   # writer imports this module
    for s, role, kind, notes, lns, scale in _beside_lines(songs):
        prev_with, prev_midi, li = readings_mod.START, None, 0
        for n in notes:
            t, m = n[0], int(round(n[2]))
            while li + 1 < len(lns) and lns[li + 1][0] <= t + readings_mod.NEAR:
                li += 1
            if lns[li][0] > t + readings_mod.NEAR:
                prev_midi = m
                continue
            lm = int(round(lns[li][2]))
            steps = writer.scale_index(m, scale) - writer.scale_index(lm, scale)
            move = writer.scale_index(m, scale) - writer.scale_index(prev_midi, scale) if prev_midi is not None else None
            with_line = abs(lns[li][0] - t) < readings_mod.NEAR
            altered = lm % 12 not in scale                     # the line's note off the song's scale (a leading tone in minor): the voice's
            outcome = f"s{m - lm}" if altered else str(steps)  # interval is then counted in semitones from the note itself (round 66)
            yield s, role, kind, with_line, steps, move, prev_with, "altered" if altered else "scale", outcome
            if with_line:
                prev_with = outcome
            prev_midi = m


def voice_interval_units(songs) -> list:
    """Each onset a voice beside the line strikes WITH the line as a unit: its outcome the interval from the line's note
    in scale steps (7 an octave, 2 a third; signed), its values the part, the voice's relation (apart, alternating) and
    the interval at its previous onset with the line (the chain). FFVI's voice beside an arpeggiated line sits a third
    below it most (-2, 12 %), an octave off in 13 % of these onsets, on the same pitch in 5 %, and keeps its interval
    from one onset to the next 37 % of the time; the writing had put it a tone up the line's voicing, never at the
    octave, holding its interval 54 % (2026-10-24). Held out, the chain conditioning is worth 0.7 bits a unit; the
    layer word and the line note's chord role add nothing to it. The counter-line is counted beside the tune the same
    way (part counter, the kind its sample relation: thirds on the tune's sample, octaves and unisons on another). The
    interval is counted in scale steps between the two notes' scale tones (a note off the scale: the tone below it)
    where the line's note is on the song's scale, and in semitones from the note itself ("s-4") where it is off it
    (the value "line": scale or altered; round 66): the writer had put the counted steps back on the scale, so a
    unison with the tune's leading tone came out a semitone under it. FFVI's tune is off its key's scale at 0.23 of
    the counter's onsets with it; the actual intervals there are "other" (seconds, tritones, sevenths) in 0.15, as the
    writer realized the counted steps in 0.41 (Song Check 52's seeds: 0.54 against an off-scale tune note, 0.12 in
    scale, FFVI 0.12). A voice note off the scale against a scale note is kept as its scale tone: marking it had put
    alterations against notes they never follow (the written "other" rose to 0.22 against scale notes)."""
    out = []
    for s, role, kind, with_line, steps, move, prev_with, line, outcome in _voice_walk(songs):
        if with_line and (abs(steps) <= VOICE_STEPS if line == "scale" else abs(int(outcome[1:])) <= VOICE_SEMITONES):
            out.append(tables.Unit(s.sid, s.game, outcome, {"part": role, "kind": kind, "line": line, "previous": prev_with}))
    return out


def voice_move_units(songs) -> list:
    """Each onset of a voice beside the line as a unit: its outcome the voice's move from its own previous note in scale
    steps, its values the part, the relation and the place (with the line, or alone where the line is silent). FFVI's
    voice is a melody of its own: with the line it repeats its note 37 % of the time and moves a step 21 %, two steps
    17 %, five or more 11 %; alone it repeats 29 % and steps 37 %. Held out, its move is surer than its interval to the
    line (3.4 against 3.9 bits a unit with the line, 3.3 against 4.5 alone), and the two words' product surer than
    either (3.4 bits): the writer draws the note both agree on (2026-10-24; a voice placed against the line alone had
    leapt five steps or more at 43 % of its onsets, FFVI 11 %). The counter-line beside the tune is counted too (part
    counter, kind same or other), its place with the tune or alone in the tune's rests."""
    out = []
    for s, role, kind, with_line, steps, move, prev_with, _, _ in _voice_walk(songs):
        if move is not None and abs(move) <= VOICE_STEPS:
            out.append(tables.Unit(s.sid, s.game, str(move), {"part": role, "kind": kind, "place": "with" if with_line else "alone"}))
    return out


def kit_accents(drum_notes, bars, division: int) -> dict:
    """The kit's accents a bar: the positions where two or more drum pieces strike together, {bar index: set of positions};
    a bar with none is left out."""
    out = {}
    for k, (a, b) in enumerate(bars):
        at = Counter()
        for n in drum_notes:
            if a - readings_mod.NEAR <= n[0] < b - readings_mod.NEAR:
                at[readings_mod.position(n[0] - a, division)] += 1
        strong = {p for p, c in at.items() if c >= 2}
        if strong:
            out[k] = strong
    return out


def bass_lock_units(songs) -> list:
    """Each song with a bass and drums as a unit: its outcome the share of the kit's accents (two pieces together) that
    carry a bass note, in tenths, its value the part. FFVI's bass sits on 0.94 of the kit's accents at the median and
    strikes with some drum at three quarters of its notes; written locked to nothing (the writer's lock had counted the
    whole planned band, which the bass, written second, never met) it had sat on 0.67 and 0.44 (2026-10-24)."""
    out = []
    for s in songs:
        if R.BASS not in s.notes or R.DRUMS not in s.notes:
            continue
        voices = cells_mod.part_voices(s, R.BASS)
        line = voices[cells_mod.line_voice(voices, R.BASS)] if len(voices) >= 2 else s.notes[R.BASS]
        bs = sorted(n[0] for n in line if not math.isnan(n[2]))
        accents = kit_accents(s.notes[R.DRUMS], s.bars, s.division)
        total = sum(len(v) for v in accents.values())
        if not bs or not total:
            continue
        hit = sum(1 for k, ps in accents.items() for p in ps if any(abs(t - (s.bars[k][0] + float(p))) < readings_mod.NEAR for t in bs))
        out.append(tables.Unit(s.sid, s.game, f"{round(hit / total, 1):.1f}", {"part": R.BASS}))
    return out


TOP_LEVEL_BIN = 0.05                 # the grain the loudest part's level of full is counted to (top_level_units)
MIX_BIN = 1.0                        # dB: the grain a song's mix level is counted to (mix_level)
MIX_FRAME = 0.25                     # beats: the frame mix_level sums the sounding notes' perceived levels over
MIX_NOTE_BEATS = 2.0                 # beats a note counts for at most in the mix level (a pad held eight bars is heard at its first beats)


def mix_level(notes) -> float | None:
    """A song's mix level in dB (round 59): each note's perceived level
    squared (the level the ear hears, a voice's level over its sample's
    loudness, as the readings count it since round 56), summed over every
    quarter-beat frame it sounds in (MIX_FRAME; at most MIX_NOTE_BEATS of
    it), the mean over the frames anything sounds in, in dB; None with no
    note. `notes`: (start in beats, length in beats, perceived level). Over
    FFVI's 66 converted songs this estimate meets the rendered loudness
    with a correlation of 0.47 and a residual spread (quartiles) of 2.6 dB;
    over 20 written songs 0.77 and 3.8 dB: it tells a thick held mix from a
    thin one, which is what the written songs had got wrong (four of
    fourteen rendered louder than any FFVI song)."""
    frames = {}
    for start, length, level in notes:
        if not (start == start and length == length):      # a note with no start or length
            continue
        a, b = start, start + min(max(length, 0.0), MIX_NOTE_BEATS)
        for f in range(int(a / MIX_FRAME), int(b / MIX_FRAME) + 1):
            frames[f] = frames.get(f, 0.0) + level * level
    live = [v for v in frames.values() if v > 0]
    return 10 * math.log10(statistics.mean(live)) if live else None


def song_mix_level(s) -> float | None:
    """mix_level over a read song's notes at their perceived levels (note_levels by the note's time, else the part's level)."""
    out = []
    nl = s.note_levels if isinstance(s.note_levels, dict) else {}
    for role, ns in s.notes.items():
        lv = sorted(nl.get(role) or [])
        ts = [t for t, _ in lv]
        for n in ns:
            if lv:
                level = lv[max(0, bisect.bisect_right(ts, n[0] + 1e-6) - 1)][1]
            else:
                level = (s.levels or {}).get(role, 0.0)
            out.append((n[0], n[1], level))
    return mix_level(out)


def top_level_units(songs) -> list:
    """Each song as a unit: its loudest part's median note level, of full (the readings' scale: the SNES chip's voice volume
    over 128, the sum of the two sides over 128 at the converter), to TOP_LEVEL_BIN; its value the part (arrangement).
    Round 52 (2026-10-28): the written songs had played their loudest part at a constant 0.85 of full, and rendered through
    the same player as FFVI's converted songs they sat 5 dB hotter (-19.6 against -24.5 dBFS over the first minute); FFVI's
    loudest part sits at 0.2 to 0.4 of full."""
    out = []
    for s in songs:
        if not s.levels:
            continue
        top = max(s.levels.values())
        out.append(tables.Unit(s.sid, s.game, f"{round(top / TOP_LEVEL_BIN) * TOP_LEVEL_BIN:.2f}", {"part": ARRANGEMENT}))
    return out


def level_units(songs) -> list:
    """Each part of each song as a unit: its outcome its notes' median level as a share of the song's loudest part's, in
    tenths ("1.0" the loudest part, "0.7"), its value the part. FFVI's parts sit close, the bass loudest (0.28 of full),
    the tune 0.22, the chord parts and the counter-line 0.19, the harmony 0.18; the writer's hand-set levels had the
    tune at 1.4 times the accompaniment and the pads at 0.6 of it, a lead over a backing (2026-10-24)."""
    out = []
    for s in songs:
        if not s.levels:
            continue
        top = max(s.levels.values())
        if top <= 0:
            continue
        for role, lv in s.levels.items():
            out.append(tables.Unit(s.sid, s.game, f"{round(lv / top, 1):.1f}", {"part": role}))
    return out


def layer_level_units(songs) -> list:
    """Each layered part (two voices or more) of each song as a unit: its second voice's (the busiest beside the line)
    median level against its line voice's, in tenths (capped at LAYER_LEVEL_CAP; voice_level_shares' first entry), its
    value the part. Since round 33 the balance token carries the same shares for every voice beyond the line, and the
    plan draws this word only for a part the token lacks or has as one voice."""
    out = []
    for s in songs:
        for role in readings_mod.UPPER + (R.COUNTER, R.MELODY, R.BASS):
            shares = voice_level_shares(s, role)
            if shares:
                out.append(tables.Unit(s.sid, s.game, shares[0], {"part": role}))
    return out


def layer_units(songs) -> list:
    """Each part of each song that holds two voices or more (the drums left
    out) as a unit: its outcome what the second voice does beside the line
    (the voice with the most notes; the bass's, with the longest notes):
    "doubling +4" (harness.relation's interval), "alternating", or "apart"
    with how far its register sits from the line's (to REGISTER_BIN,
    within LAYER_OFFSET) and how dense it is against it (LAYER_DENSITY);
    its value the part. FFVI's second accompaniment voice is apart in 65 %
    of its songs with two, its second counter-line in 79 % (2026-10-23):
    the orchestration a song written whole was missing."""
    from .. import harness                                  # harness imports this module
    out = []
    for s in songs:
        by_role = {}
        for v, (role, ns) in s.voice_notes.items():
            if role != R.DRUMS and ns:
                by_role.setdefault(role, {})[v] = ns
        for role, voices in by_role.items():
            if len(voices) < 2:
                continue
            line = cells_mod.line_voice(voices, role, s)         # the bass's the voice with the longest notes, the melody's the heard tune (round 90)
            extras = sorted((v for v in voices if v != line), key=lambda v: (-len(voices[v]), v))
            for rank, other in enumerate(extras, start=2):      # every voice beside the line, the busiest first, its own relation
                kind = harness.relation(voices[line], voices[other])
                if kind[0] == "doubling":
                    outcome = f"doubling {kind[1]:+d}"
                elif kind[0] == "alternating":
                    outcome = "alternating"
                else:
                    a, b = part_register(voices[line]), part_register(voices[other])
                    if a is None or b is None:
                        continue
                    offset = int(round(((b[0] + b[1]) - (a[0] + a[1])) / 2 / cells_mod.REGISTER_BIN)) * cells_mod.REGISTER_BIN
                    offset = max(-LAYER_OFFSET, min(LAYER_OFFSET, offset))
                    density = readings_mod.habit_of(len(voices[other]) / max(1, len(voices[line])), LAYER_DENSITY)
                    outcome = f"apart {offset:+d} {density}"
                out.append(tables.Unit(s.sid, s.game, outcome, {"part": role, "rank": str(min(rank, 4))}))
    return out


@dataclass
class Rhythms:
    songs: Counter = field(default_factory=Counter)                       # role -> songs with the part
    bars: Counter = field(default_factory=Counter)                        # role -> bars of those songs
    onsets: Counter = field(default_factory=Counter)                      # role -> onsets in them
    places: dict = field(default_factory=lambda: defaultdict(Counter))    # role -> place -> onsets (rolls too)
    patterns: dict = field(default_factory=lambda: defaultdict(readings_mod.Tally))    # (role, meter) -> drawn -> bars
    meters: Counter = field(default_factory=Counter)                      # meter -> songs
    odd: Counter = field(default_factory=Counter)                         # meter -> bars of another length
    off_eighths: list = field(default_factory=list)                       # a song's share, as measures.py counts
    triplets: list = field(default_factory=list)                          # and of those, on a triplet


def rhythms(songs) -> Rhythms:
    """The parts' rhythms, bar by bar (the module's account)."""
    r = Rhythms()
    for s in songs:
        r.meters[s.meter] += 1
        r.odd[s.meter] += sum(1 for a, b in s.bars if round(b - a) != s.meter)
        for role in readings_mod.PARTS:
            if role not in s.notes and role not in s.rolls:
                continue
            r.songs[role] += 1
            drawn = []
            for a, struck in readings_mod.bars_of(s, role):
                r.bars[role] += 1
                r.onsets[role] += len(struck)
                drawn.append(readings_mod.draw([p for p, _ in struck], s.meter))
                r.places[role].update(readings_mod.place(p) for p, _ in struck)
                r.places[role].update(readings_mod.place(readings_mod.position(t - a, s.division)) for t, _ in readings_mod.onsets(s.rolls.get(role, []), a, a + s.meter))
            r.patterns[role, s.meter].add(drawn)
        first = s.bars[0][0] if s.bars else 0.0
        pitched = [n[0] - first for role in readings_mod.PITCHED for n in s.notes.get(role, []) + s.rolls.get(role, []) if n[0] >= first]
        off = [t for t in pitched if abs(t * 2 - round(t * 2)) / 2 >= readings_mod.NEAR]
        if pitched:
            r.off_eighths.append(100 * len(off) / len(pitched))
        if off:
            r.triplets.append(100 * sum(1 for t in off if abs(t * 3 - round(t * 3)) / 3 < readings_mod.NEAR) / len(off))
    return r


def _chord_at(chords, t: float) -> Span | None:
    i = bisect.bisect_right([c.start for c in chords], t + readings_mod.NEAR) - 1
    return chords[i] if 0 <= i < len(chords) and chords[i].end > t + readings_mod.NEAR else None


def _line(notes, lowest: bool = False) -> list:
    """Notes struck together as one: the highest, or the lowest."""
    pick = min if lowest else max
    return [pick(ns, key=lambda n: n[2]) for _, ns in readings_mod.onsets(notes, -math.inf, math.inf)]


def _sizes(moves) -> Counter:
    """Moves by size (SIZES) and direction: (size, "up"/"down"/"") -> count."""
    out = Counter()
    for m in moves:
        size = next(name for top, name in readings_mod.SIZES if abs(m) <= top)
        out[size, "up" if m > 0 else "down" if m < 0 else ""] += 1
    return out


@dataclass
class Bass:
    songs: int = 0
    bars: int = 0
    figures: dict = field(default_factory=lambda: defaultdict(readings_mod.Tally))     # meter -> drawn with tones -> bars
    moves: Counter = field(default_factory=Counter)                       # (size, direction) -> moves
    semitones: Counter = field(default_factory=Counter)


def bass(songs) -> Bass:
    """The bass's figures over the bars, and its moves."""
    b = Bass()
    for s in songs:
        if R.BASS not in s.notes:
            continue
        b.songs += 1
        drawn = []
        for start, struck in readings_mod.bars_of(s, R.BASS):
            b.bars += 1
            low = [min(n[2] for n in ns) for _, ns in struck]
            floor = min(low, default=0.0)
            marks = {}
            for (p, _), midi in zip(struck, low):
                c = _chord_at(s.chords, start + p)
                mark = "?" if c is None or c.root is None or c.fit < FIT else readings_mod.TONE_MARKS[tone_of(round(midi) % 12, c.root, c.shape)]
                marks[p] = "r" if mark == "R" and midi >= floor + 11.5 else mark
            drawn.append(readings_mod.draw(list(marks), s.meter, marks))
        b.figures[s.meter].add(drawn)
        line = [round(n[2]) for n in _line(s.notes[R.BASS], lowest=True)]
        moves = [y - x for x, y in zip(line, line[1:])]
        b.moves.update(_sizes(moves))
        b.semitones.update(moves)
    return b


@dataclass
class Drums:
    songs: int = 0
    bars: int = 0
    sounds: dict = field(default_factory=dict)                            # sample key -> its profile and name
    figures: dict = field(default_factory=lambda: defaultdict(readings_mod.Tally))     # meter -> ((piece, drawn), ...) -> bars


def _name(profile: dict) -> str:
    """A drum sound's piece from its profile (the module's rule)."""
    if profile["a_bar"] >= readings_mod.DENSE:
        return "hat"
    return "kick" if profile["one"] > profile["back"] else "snare" if profile["back"] > profile["one"] else "other"


def sounds(songs, names: dict | None = None, bank=None) -> dict:
    """Each drum sample's profile over the songs, and its name: {key: {songs,
    hits, a_bar (hits a bar where it plays), one, three, back, eighth, finer
    (hits there), length (beats), held (seconds), midi (the pitch it plays
    at most, or None), name, how}}. The name: known beforehand (names: by
    key, as the generator's drums are), else by its sound (bank: drums.Bank
    or drums.Kit, where it has the sample), else by how it is played
    (_name); `how` says which."""
    out = defaultdict(lambda: Counter(songs=0, hits=0, one=0, three=0, back=0, eighth=0, finer=0))
    bars, lengths, held, midis = defaultdict(set), defaultdict(list), defaultdict(list), defaultdict(Counter)
    for s in songs:
        seen = set()
        for i, (_, struck) in enumerate(readings_mod.bars_of(s, R.DRUMS)):
            for p, ns in struck:
                for n in ns:
                    k = n[3]
                    seen.add(k)
                    bars[k].add((id(s), i))
                    out[k]["hits"] += 1
                    out[k]["one" if p == 0 else "three" if s.meter == 4 and p == 2 else "back" if p.denominator == 1
                           else "eighth" if p.denominator == 2 else "finer"] += 1
                    if not math.isnan(n[1]):
                        lengths[k].append(n[1])
                        held[k].append(n[1] * 60 / s.bpm)
                    if not math.isnan(n[2]):
                        midis[k][round(n[2])] += 1
        for k in seen:
            out[k]["songs"] += 1
    for k, c in out.items():
        c["a_bar"] = c["hits"] / len(bars[k])
        c["length"] = statistics.median(lengths[k]) if lengths[k] else 0.0
        c["held"] = statistics.median(held[k]) if held[k] else None
        c["midi"] = midis[k].most_common(1)[0][0] if midis[k] else None
    by_sound = drums_mod.names(bank, out) if bank else {}
    for k, c in out.items():
        c["name"], c["how"] = ((names[k], "known") if names and k in names else (by_sound[k], "sound") if k in by_sound
                               else (_name(c), "play"))
    return dict(out)


def drums(songs, names: dict | None = None, bank=None) -> Drums:
    """The drums' figures over the bars, the sounds named as sounds() names them."""
    d = Drums(sounds=sounds(songs, names, bank))
    for s in songs:
        if R.DRUMS not in s.notes:
            continue
        d.songs += 1
        drawn = []
        for _, struck in readings_mod.bars_of(s, R.DRUMS):
            d.bars += 1
            by = defaultdict(set)
            for p, ns in struck:
                for n in ns:
                    by[d.sounds[n[3]]["name"]].add(p)
            drawn.append(tuple((piece, readings_mod.draw(sorted(by[piece]), s.meter)) for piece in readings_mod.PIECES if piece in by))
        d.figures[s.meter].add(drawn)
    return d


@dataclass
class Melody:
    songs: int = 0
    notes: int = 0
    moves: Counter = field(default_factory=Counter)                       # (size, direction) -> moves
    semitones: Counter = field(default_factory=Counter)
    lengths: Counter = field(default_factory=Counter)                     # beats to the next note -> notes
    sounded: list = field(default_factory=list)                           # the share of that each note sounds


def melody(songs) -> Melody:
    """The melody's moves and its notes' lengths."""
    m = Melody()
    for s in songs:
        if R.MELODY not in s.notes:
            continue
        m.songs += 1
        line = _line(cells_mod.tune_line(s, R.MELODY))
        m.notes += len(line)
        pitches = [round(n[2]) for n in line]
        moves = [y - x for x, y in zip(pitches, pitches[1:])]
        m.moves.update(_sizes(moves))
        m.semitones.update(moves)
        for n, after in zip(line, line[1:]):
            gap = after[0] - n[0]
            m.lengths[readings_mod.position(gap, s.division)] += 1
            if not math.isnan(n[1]):
                m.sounded.append(min(1.0, n[1] / gap))
    return m


def value(length: Fraction) -> str:
    """A length's name (VALUES): the shortest value it fits in."""
    return next(name for top, name in readings_mod.VALUES if length <= top)


def _moves_table(moves: Counter, semitones: Counter) -> list[str]:
    total = sum(moves.values()) or 1
    out = [f"    {'move':10s} {'share':>6s} {'up':>6s} {'down':>6s}"]
    for _, size in readings_mod.SIZES:
        n = sum(c for (sz, _), c in moves.items() if sz == size)
        if n:
            up, down = moves[size, "up"], moves[size, "down"]
            out.append(f"    {size:10s} {_pct(n, total):>6s} " +
                       (f"{_pct(up, n):>6s} {_pct(down, n):>6s}" if size != "repeat" else ""))
    out.append("    semitones: " + ", ".join(f"{m:+d} {100 * c / total:.0f} %" if m else f"0 {100 * c / total:.0f} %"
                                            for m, c in semitones.most_common(12)))
    return out


def report(songs: list, left_out: dict, top: int = 10, game: str = "", bank=None) -> str:
    """The three tables as text: the rhythms per part and bar, the bass's and
    the drums' figures, the melody's moves and lengths (bank: the game's
    samples, drums.Bank, to name the drums by their sound)."""
    total = len(songs) + sum(left_out.values())
    head = f"rhythm of {game + ': ' if game else ''}{len(songs)} songs"
    out = [head + (f" of {total} (" + ", ".join(f"{n} {why}" for why, n in left_out.items()) + ")" if left_out else "")]
    r = rhythms(songs)
    meters = [k for k, _ in r.meters.most_common()]
    out.append("\nonsets a bar, and where they fall (a chord struck in several voices is one onset)")
    out.append(f"  {'part':14s} {'songs':>5s} {'bars':>6s} {'a bar':>6s}" + "".join(f" {p:>9s}" for p in readings_mod.PLACES)
               + f" {'off 8ths':>9s} {'triplet':>8s}")
    for role in readings_mod.PARTS:
        if r.bars[role]:
            n = sum(r.places[role].values())
            off = n - r.places[role]["beat"] - r.places[role]["eighth"]
            out.append(f"  {role:14s} {r.songs[role]:5d} {r.bars[role]:6d} {r.onsets[role] / r.bars[role]:6.1f}"
                       + "".join(f" {_pct(r.places[role][p], n):>9s}" for p in readings_mod.PLACES)
                       + f" {_pct(off, n):>9s} {_pct(r.places[role]['triplet'], off):>8s}")
    out.append(f"  as stage 2 counts them (pitched parts, a song's share, the median): off the eighths "
               f"{_median(r.off_eighths, ' %')}, of them on a triplet {_median(r.triplets, ' %')}")
    out.append("  songs by meter: " + ", ".join(f"{k} beats {r.meters[k]}" for k in meters)
               + f"; bars of another length left out: {sum(r.odd.values())}")
    for meter in meters:
        out.append(f"\nrhythms, bars of {meter} beats ({r.meters[meter]} songs; x on a quarter of the beat, t on a third,"
                   " ~ finer; the share of the part's bars)")
        for role in readings_mod.PARTS:
            c = r.patterns.get((role, meter))
            if not c:
                continue
            n = sum(c.values())
            out.append(f"  {role} ({n} bars, {sum(1 for k in c if k != readings_mod.REST)} patterns)")
            for pattern, count in c.most_common(top):
                out.append(f"    {pattern:{5 * meter}s} {_pct(count, n)}  {c.songs[pattern]:3d} songs")
    b = bass(songs)
    out.append(f"\nbass figures ({b.songs} songs, {b.bars} bars; R root, 3 third, s sus, 5 fifth, 7 seventh, + another,"
               " ? no chord; r the root an octave up)")
    for meter in meters:
        c = b.figures.get(meter)
        if not c:
            continue
        n = sum(c.values())
        out.append(f"  bars of {meter} beats ({n} bars, {sum(1 for k in c if k != readings_mod.REST)} figures)")
        for figure, count in c.most_common(top):
            out.append(f"    {figure:{5 * meter}s} {_pct(count, n)}  {c.songs[figure]:3d} songs")
    out.append("  the bass moves")
    out += _moves_table(b.moves, b.semitones)
    d = drums(songs, bank=bank)
    how = Counter(c["how"] for c in d.sounds.values())
    out.append(f"\ndrum sounds ({d.songs} songs with drums), by sample, named "
               + (f"by their sound ({how['sound']} of {len(d.sounds)}; the rest by how they are played)" if how["sound"]
                  else "by how they are played (no SPC files given: --spc)"))
    out.append(f"  {'sound':10s} {'songs':>5s} {'hits':>6s} {'a bar':>5s} {'one':>5s} {'three':>5s} {'back':>5s}"
               f" {'8th':>5s} {'finer':>5s} {'beats':>6s}  named")
    for k, c in sorted(d.sounds.items(), key=lambda kv: -kv[1]["hits"])[:top + 2]:
        out.append(f"  {k[:10]:10s} {c['songs']:5d} {c['hits']:6d} {c['a_bar']:5.1f}"
                   + "".join(f" {_pct(c[w], c['hits']):>5s}" for w in ("one", "three", "back", "eighth", "finer"))
                   + f" {c['length']:6.2f}  {c['name']}" + ("" if c["how"] == "sound" else f" (by {c['how']})"))
    out.append("  named: " + ", ".join(f"{p} {n}" for p, n in Counter(c["name"] for c in d.sounds.values()).most_common()))
    out.append(f"\ndrum figures ({d.bars} bars; K kick, S snare, h hat, t tom, c cymbal, o another sound)")
    for meter in meters:
        c = d.figures.get(meter)
        if not c:
            continue
        n = sum(c.values())
        out.append(f"  bars of {meter} beats ({n} bars, {sum(1 for k in c if k)} figures)")
        for figure, count in c.most_common(top):
            for i, (piece, drawn) in enumerate(figure or (("", readings_mod.REST),)):
                out.append(f"    {readings_mod.LETTERS.get(piece, ' ')} {drawn:{5 * meter - 2}s} "
                           + (f"{_pct(count, n)}  {c.songs[figure]:3d} songs" if i == 0 else ""))
    m = melody(songs)
    out.append(f"\nmelody ({m.songs} songs, {m.notes} notes): its moves")
    out += _moves_table(m.moves, m.semitones)
    out.append("  its notes' lengths, to the next note")
    n = sum(m.lengths.values()) or 1
    values = Counter()
    for length, count in m.lengths.items():
        values[value(length)] += count
    for _, name in readings_mod.VALUES:
        if values[name]:
            out.append(f"    {name:22s} {_pct(values[name], n)}")
    detached = sum(1 for x in m.sounded if x < readings_mod.SHORT)
    out.append(f"    the note sounds for {_median(m.sounded)} of it; detached (under {readings_mod.SHORT:g}): {_pct(detached, len(m.sounded))}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bitcomposer.translate.rhythm", description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", help="the readings database (default: ~/.local/share/bitcomposer/readings.db)")
    ap.add_argument("--game", help="only this game's songs (the songs table's game)")
    ap.add_argument("--top", type=int, default=10, help="rows of each patterns table (default 10)")
    ap.add_argument("--spc", metavar="DIR", help="the game folders' root, or one game's folder: the drums named by their sound")
    args = ap.parse_args(argv)
    db = store.connect(args.db)
    songs, left_out = readings_mod.load(db, args.game)
    if not songs:
        print("bitcomposer.translate.rhythm: no songs on a beat to count", file=sys.stderr)
        return 1
    games = [g for g, in db.execute("SELECT DISTINCT game FROM songs")]
    print(report(songs, left_out, args.top, args.game or (games[0] if len(games) == 1 else ""),
                 drums_mod.Bank(db, args.spc) if args.spc else None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
