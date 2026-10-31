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


def chord_tone_habit_units(songs) -> list:
    """Each song with a melody as a unit: its outcome the share of the tune's
    notes on a beat that are tones of the chord sounding (to
    CHORD_TONE_BIN); its value the part (melody). The melody writer holds
    its tune to the drawn share (FFVI's songs: a median 0.56; the writer's
    constant gave 0.75 in the first whole songs, 2026-10-23)."""
    out = []
    for s in songs:
        line = _line(s.notes.get(R.MELODY, []))
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
            out.append(tables.Unit(s.sid, s.game, f"{round(hits / total / CHORD_TONE_BIN) * CHORD_TONE_BIN:.1f}", {"part": R.MELODY}))
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


def part_register(notes, ambitus: bool = False) -> tuple | None:
    """A part's register as the registers table keeps it: (low, high) midi to REGISTER_BIN, the notes' 10th and 90th
    percentiles, or the whole ambitus (`ambitus`: the melody's, a tune uses its extremes); None where the part has
    under eight pitched notes."""
    pitched = sorted(n[2] for n in notes if not math.isnan(n[2]))
    if len(pitched) < 8:
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
    line = cells_mod.line_voice(voices, role)
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
    ones had taken the line's sample and played 0.84-1.15 of its notes, a sparse pad in the game a busy riff over the tune."""
    shares = voice_level_shares(song, role)
    if shares is None:
        return None
    voices = cells_mod.part_voices(song, role)
    line = cells_mod.line_voice(voices, role)
    others = sorted((v for v in voices if v != line), key=lambda v: (-len(voices[v]), v))
    out = []
    for share, v in zip(shares, others):
        keys = Counter(n[3] for n in voices[v] if isinstance(n[3], str))
        key = keys.most_common(1)[0][0] if keys else ""
        sid = ("s" + key[:10] if len(key) >= 10 else key) if key else ""
        out.append(f"{share}@{sid}@{min(9.0, len(voices[v]) / max(1, len(voices[line]))):.2f}")
    return out


def kit_token(s, top: float = 0.0) -> str:
    """The song's kit as a token field (round 63): each piece letter with the pack id of the sample the song strikes it
    with most (`K=sbfe716b9b6,S=s1279e119a1`), in LETTERS' order; "" without drums. A song's kit is its own samples (FFVI:
    a median two drum samples a song, 31 over the game, and 17 of its 47 kits inside the pack's one kit of seven slots).
    Since round 68 each piece carries its own level too, where the readings heard one: the median level of the notes
    struck on that sample (Song.kit_levels, the loudness factor applied as the part's level has it) as a share of the
    song's loudest part's level `top` (`K=sbfe716b9b6@1.70,S=s1279e119a1@0.70,h=sd1c4c7ce33@0.20`; in hundredths since
    round 70, tenths before and still read: 163's snare at 0.14 kept as 0.1 had cost 2.9 dB on a quiet piece). The part's
    one level is the median over every note of every drum voice, which is the most frequent piece's: FFVI's hat is the
    most frequent and its strike the quietest, so Blackjack's token said drums at 0.2 of the top where its kick plays
    at 1.7 and its snare at 0.7, and the written kit was brought to one heard loudness a piece, the kick as quiet as
    a hat (Song Check 54's Whole 169: the kit 16 dB under Blackjack's). A piece without a level keeps the old form."""
    counts = Counter()
    for n in s.notes.get(R.DRUMS, []):
        key = n[3] if isinstance(n[3], str) else None
        piece = (s.pieces or {}).get(key)
        if key and piece in readings_mod.LETTERS:
            counts[(readings_mod.LETTERS[piece], key)] += 1
    best = {}
    for (letter, key), n in counts.most_common():
        best.setdefault(letter, key)
    levels = getattr(s, "kit_levels", None) or {}
    out = []
    for letter in readings_mod.LETTERS.values():
        if letter not in best:
            continue
        key = best[letter]
        field = f"{letter}=" + ("s" + key[:10] if len(key) >= 10 else key)
        level = levels.get(key)
        if top > 0 and level is not None and math.isfinite(level):   # never a "nan" share: the part's level stands in
            field += f"@{round(level / top, 2):.2f}"                 # in hundredths since round 70: tenths cost 2.9 dB on a snare at 0.14 kept as 0.1
        out.append(field)
    return ",".join(out)


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
            notes = voices[cells_mod.line_voice(voices, role)]
    c = Counter(n[3] for n in notes if isinstance(n[3], str) and n[3])
    if not c:
        return ""
    key = c.most_common(1)[0][0]
    return "s" + key[:10] if len(key) >= 10 else key


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
    where it sits at 0.27, its bass line on the second voice's sample)."""
    habit_of_part = {}                                    # (song, part) -> the part's habit (round 62: the song's density tiers ride the token)
    for u in readings_mod.habits(readings_mod.units(songs)) + readings_mod.habits(readings_mod.bass_units(songs)):
        habit_of_part[(u.song, u.values["part"])] = u.outcome
    for u in readings_mod.drum_habit_units(songs):
        habit_of_part[(u.song, R.DRUMS)] = u.outcome
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
                fields = ["", "", "", "", levels.get(role, ""), "", "", kit_token(s, top), dh]   # and its kit as the eighth (round 63; each
                                                                                             # piece's own level beside its sample, round 68)
                while fields and not fields[-1]:
                    fields.pop()
                tokens.append(role + ("=" + ":".join(fields) if fields else ""))
                continue
            reg, share = part_register(cells_mod.register_notes(s, role) or s.notes[role], ambitus=role == R.MELODY), cells_mod.sounded_share(s.notes[role])
            beside = layer_tokens(s, role) if role in levels else None   # each voice beyond the line: level, sample, note share (round 65)
            kind = cells_mod.counter_kind(s) if role == R.COUNTER and role in levels else None
            fields = [weights[role], f"{reg[0]}-{reg[1]}" if reg else "", f"{round(share / cells_mod.SOUND_BIN) * cells_mod.SOUND_BIN:.1f}" if share is not None else "",
                      str(max(1, voices.get(role, 1))), levels.get(role, ""), "/".join(beside) if beside else "", kind or "",
                      part_sample_id(s, role),                # the part's own sample (round 60): a song's instruments are one song's
                      habit_of_part.get((s.sid, role), "").replace(" ", "+")]   # and its habit (round 62): the song's density tiers together
            while fields and not fields[-1]:                 # a field a song lacks is left off the end, not left empty
                fields.pop()
            tokens.append(f"{role}=" + ":".join(fields))
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
    out = []
    for s in songs:
        if s.echo is None:
            continue
        by_role = {}
        for v, (role, ns) in s.voice_notes.items():
            if role in readings_mod.PARTS and ns and v in s.echo_sends:
                by_role.setdefault(role, []).append(s.echo_sends[v] >= ECHO_SEND)
        sends = sorted(role for role, flags in by_role.items() if sum(flags) * 2 >= len(flags))
        dry = sorted(role for role in by_role if role not in sends)
        volume, ms, feedback = s.echo
        out.append(tables.Unit(s.sid, s.game, f"{volume:.2f}:{ms:.0f}:{feedback:.2f}:{'+'.join(sends) or '-'}:{'+'.join(dry) or '-'}",
                               {"part": ECHO_PART}))
    return out


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
    the line), and the counter-line beside the tune (part counter; its kind the sample relation, counter_kind, which
    splits FFVI's intervals: thirds on the tune's sample, octaves and unisons on another): (song, part, kind, the
    voice's notes, the line's notes, the song's scale), sorted in time."""
    from .. import harmony, harness                         # harness imports this module
    pitched = lambda ns: sorted((n for n in ns if not math.isnan(n[2])), key=lambda n: n[0])   # noqa: E731
    for s in songs:
        scale = {((s.tonic or 0) + i) % 12 for i in harmony.MODES["major" if s.mode == "major" else "natural_minor"]}
        for role in readings_mod.UPPER + (R.BASS,):                       # the bass too: its second voice plays the line's pitch class at 78 % of
            voices = cells_mod.part_voices(s, role)                   # their shared onsets in FFVI; written apart it had at 31 % (2026-10-24)
            if len(voices) < 2:
                continue
            line = cells_mod.line_voice(voices, role)
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
            if role == R.BASS:
                lengths = {v: statistics.median([n[1] for n in ns if not math.isnan(n[1])] or [0.0]) for v, ns in voices.items()}
                line = max(lengths, key=lambda v: (lengths[v], -v))
            else:
                line = max(voices, key=lambda v: (len(voices[v]), -v))
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
        line = _line(s.notes[R.MELODY])
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
