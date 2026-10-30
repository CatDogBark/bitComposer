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

from . import readings as readings_mod, chords as chords_mod, form as form_mod, arrangement as arrangement_mod   # noqa: E402  the package's other sections


# --- the melody's bar cells: a bar of the tune as its rhythm and intervals, what a tune repeats and returns to ---

ECHOES = ((1 / 3, "varied"), (2 / 3, "mixed"), (2, "repeating"))   # a song's share of tune bars that echo an earlier bar


def melody_cells(song: readings_mod.Song, role: str = None) -> list:
    """Each bar's cell of the tune (the melody's line, notes struck together
    the highest): its onsets in twelfths from the bar line and its
    intervals, as one key; None where the bar has no note."""
    role = role or R.MELODY
    line = sorted(arrangement_mod._line(song.notes.get(role, [])))
    out = []
    for a, b in song.bars:
        mine = [n for n in line if a - readings_mod.NEAR <= n[0] < b - readings_mod.NEAR]
        if not mine:
            out.append(None)
            continue
        ps = [round(n[2]) for n in mine]
        out.append(" ".join(str(round((n[0] - a) * 12)) for n in mine) + " | " + " ".join(f"{y - x:+d}" for x, y in zip(ps, ps[1:])))
    return out


HALF_CELL_NOTES = 2                  # notes a half bar needs to be a cell the band can take up
HANDOFF_PARTS = (R.COUNTER, R.ACCOMP, R.HARMONY, R.ARP, R.BASS)   # the parts a tune cell can pass to (their line voices)
HANDOFF_FAR = 8                      # bars: a hand-off further on is "far"


def half_cells(line: list, bars: list) -> list:
    """A line cut into half-bar cells: for each half of each bar (start, end, key, positions in beats from the half's start,
    pitches), the key the half's onsets in twelfths and its intervals as melody_cells keys a bar; None under HALF_CELL_NOTES
    notes. `line`: notes struck together as one (_line)."""
    out = []
    for a, b in bars:
        m = (a + b) / 2
        for lo, hi in ((a, m), (m, b)):
            mine = [n for n in line if lo - readings_mod.NEAR <= n[0] < hi - readings_mod.NEAR and not math.isnan(n[2])]
            if len(mine) < HALF_CELL_NOTES:
                out.append(None)
                continue
            ps = [round(n[2]) for n in mine]
            key = " ".join(str(round((n[0] - lo) * 12)) for n in mine) + " | " + " ".join(f"{y - x:+d}" for x, y in zip(ps, ps[1:]))
            out.append((lo, hi, key, [n[0] - lo for n in mine], ps))
    return out


def handoff_class(bars_on: int) -> str:
    return str(bars_on) if bars_on < HANDOFF_FAR else "far"


def cell_handoff_units(songs) -> list:
    """Each half-bar cell of a song's tune as a unit: its outcome the first other part to play the same cell in a later bar
    and how many bars on ("counter 2", "bass 1", "far" past HANDOFF_FAR bars; "none"), its values the part (melody), the
    song's echo habit (ECHOES) and the cell's place (theme: inside the tune's theme phrase, _theme_of; other). FFVI's band
    takes up the tune's cells: half its tune's half-bar cells in a themed song come back in the counter, the accompaniment
    or the bass in another bar (0.51; all songs 0.34), where the written songs had 0.05, each part faithful to its own
    word and none to the theme (round 37)."""
    out = []
    for s in songs:
        if R.MELODY not in s.notes:
            continue
        tune = sorted(arrangement_mod._line(s.notes[R.MELODY]))
        cells = half_cells(tune, s.bars)
        if sum(1 for c in cells if c) < 4:
            continue
        bar_keys = [c for c in melody_cells(s) if c]           # the song's echo habit, at the bar as the echo_habits word has it
        habit = readings_mod.habit_of(sum(1 for i, c in enumerate(bar_keys) if c in bar_keys[:i]) / max(1, len(bar_keys)), ECHOES)
        found = _theme_of(s)
        theme_bars = set(found[2]) if found else set()
        others = {}
        for role in HANDOFF_PARTS:
            notes = line_notes(s, role) or s.notes.get(role)
            if notes:
                others[role] = half_cells(sorted(arrangement_mod._line(notes)), s.bars)
        for i, c in enumerate(cells):
            if not c:
                continue
            bar = i // 2
            hit = None
            for j in range(i + 2 - (i % 2), len(cells)):      # the halves of later bars, nearest first
                for role, oc in others.items():
                    if j < len(oc) and oc[j] and oc[j][2] == c[2]:
                        hit = f"{role} {handoff_class(j // 2 - bar)}"
                        break
                if hit:
                    break
            out.append(tables.Unit(s.sid, s.game, hit or "none", {"part": R.MELODY, "habit": habit, "place": "theme" if bar in theme_bars else "other"}))
    return out


def half_recall_units(songs) -> list:
    """What each half-bar cell of a song's tune is to the tune so far (same: the half before's cell again; earlier: one
    played before; new), by part and echo habit: the tune writer's urn at the half bar (round 38). FFVI's tune reuses
    half-bar cells more than bar cells (0.50 of halves heard earlier, themed 0.63; bars 0.32 and 0.52): its cells are
    moved and re-intervalled inside the bar where a writer whose cell is the bar draws a whole new bar."""
    out = []
    for s in songs:
        if R.MELODY not in s.notes:
            continue
        cells = [c for c in half_cells(sorted(arrangement_mod._line(s.notes[R.MELODY])), s.bars) if c]
        if len(cells) < 4:
            continue
        keys = [c[2] for c in cells]
        bar_keys = [c for c in melody_cells(s) if c]
        habit = readings_mod.habit_of(sum(1 for i, c in enumerate(bar_keys) if c in bar_keys[:i]) / max(1, len(bar_keys)), ECHOES)
        seen, previous = set(), None
        for k in keys:
            kind = "same" if k == previous else "earlier" if k in seen else "new"
            out.append(tables.Unit(s.sid, s.game, kind, {"part": R.MELODY, "habit": habit}))
            seen.add(k)
            previous = k
    return out


def melody_cell_units(songs) -> list:
    """Each bar of each song's tune as a unit: its outcome the bar's cell
    (melody_cells), its values the part, the tempo band, the part's weight
    and the song's echo habit (ECHOES: how many of its tune's bars echo an
    earlier bar). The recall shares over these (tables.recall_units) are
    what a tune writer's urn runs on."""
    out = []
    for s in songs:
        cells = [c for c in melody_cells(s) if c]
        if len(cells) < 2:
            continue
        echo = sum(1 for i, c in enumerate(cells) if c in cells[:i]) / len(cells)
        habit = readings_mod.habit_of(echo, ECHOES)
        weight = readings_mod.part_weights(s).get(R.MELODY, "minor")
        for c in cells:
            out.append(tables.Unit(s.sid, s.game, c, {"part": R.MELODY, "tempo": readings_mod.band(s.bpm), "weight": weight, "habit": habit}))
    return out


PAIR = 2                             # bars: the group the tune's memory works at above the bar (pair_recall, round 40)
RECALL_SOURCES = ("section", "theme", "elsewhere")   # where an echo points: the section it is in, the theme phrase, another section


def _tune_groups(song: readings_mod.Song):
    """The tune's bars in the form's own parts as (part index, [bar indices]) phrase windows, with each window's bar pairs
    (PAIR bars each, a trailing odd bar on its own) and the theme window (the first phrase with a cell)."""
    windows = [(i, w) for i, w in phrase_windows(song) if i is not None]
    own = {i for i, _, _ in chords_mod._own_parts(song)}
    return windows, own


def _echo_habit(cells: list) -> str:
    keys = [c for c in cells if c]
    return readings_mod.habit_of(sum(1 for i, c in enumerate(keys) if c in keys[:i]) / max(1, len(keys)), ECHOES)


def pair_recall_units(songs) -> list:
    """What each two-bar group of a song's tune is to the tune so far (same: the group before's pair of cells again; earlier:
    a pair played before; new), by part and echo habit: the tune writer's urn at the pair (round 40, 2026-10-27). The groups
    are a phrase's halves (bars 1-2 and 3-4 of each phrase window); a pair needs both its bars' cells; only the form's own
    parts are counted, since the writer draws there and plays a repeated part again. FFVI's themed tunes bring two-bar
    pairs back 0.42 of the time and whole phrases 0.29 where the written tunes, drawing each bar alone, had 0.17 and 0.18."""
    out = []
    for s in songs:
        if R.MELODY not in s.notes:
            continue
        cells = melody_cells(s)
        habit = _echo_habit(cells)
        windows, own = _tune_groups(s)
        seen, previous = set(), None
        for i, w in windows:
            for j in range(0, len(w) - 1, PAIR):
                a, b = w[j], w[j + 1]
                if not (cells[a] and cells[b]):
                    previous = None
                    continue
                key = (cells[a], cells[b])
                if i in own:
                    kind = "same" if key == previous else "earlier" if key in seen else "new"
                    out.append(tables.Unit(s.sid, s.game, kind, {"part": R.MELODY, "habit": habit}))
                seen.add(key)
                previous = key
    return out


def pair_bar_recall_units(songs) -> list:
    """What each bar inside a NEW pair is to the tune so far (same, earlier, new), by part and echo habit: the bar urn the
    writer runs inside a pair the pair urn drew new (round 40). Counted over the bars of new pairs in the form's own parts
    only: the bar urn's shares over every bar (melody_recall) include the bars that come back as pairs, and running both
    would echo twice."""
    out = []
    for s in songs:
        if R.MELODY not in s.notes:
            continue
        cells = melody_cells(s)
        habit = _echo_habit(cells)
        windows, own = _tune_groups(s)
        seen_pairs, seen = set(), set()
        previous = None
        for i, w in windows:
            for j in range(0, len(w), PAIR):
                group = w[j:j + PAIR]
                key = tuple(cells[k] for k in group) if len(group) == PAIR and all(cells[k] for k in group) else None
                new_pair = key is None or key not in seen_pairs
                for k in group:
                    c = cells[k]
                    if c and i in own and new_pair:
                        out.append(tables.Unit(s.sid, s.game, "same" if c == previous else "earlier" if c in seen else "new", {"part": R.MELODY, "habit": habit}))
                    if c:
                        seen.add(c)
                    previous = c
                if key is not None:
                    seen_pairs.add(key)
    return out


def recall_source_units(songs) -> list:
    """Where each echo of a song's tune points (RECALL_SOURCES): a bar in the form's own parts whose cell was played before
    (not the bar before) is "section" where the cell was played earlier in the same part of the form, "theme" where it was
    played in the tune's first phrase, "elsewhere" otherwise; by part and echo habit (round 40). FFVI's sections share no
    tune cells at the median (a later section's cells found in an earlier, different section: 0.00; the written songs 0.21
    in themed ones), so a writer whose urn recalls from anywhere makes its B a reshuffle of its A."""
    out = []
    for s in songs:
        if R.MELODY not in s.notes:
            continue
        cells = melody_cells(s)
        habit = _echo_habit(cells)
        windows, own = _tune_groups(s)
        theme_w = next((w for i, w in windows if any(cells[k] for k in w)), [])
        where = {}                                           # cell -> the part indices it was played in so far
        previous = None
        for i, w in windows:
            for k in w:
                c = cells[k]
                if not c:
                    previous = None
                    continue
                if i in own and c != previous and c in where:
                    source = "section" if i in where[c] else "theme" if c in {cells[t] for t in theme_w} else "elsewhere"
                    out.append(tables.Unit(s.sid, s.game, source, {"part": R.MELODY, "habit": habit}))
                where.setdefault(c, set()).add(i)
                previous = c
    return out


CELL_RHYTHMS = ("new", "previous", "earlier")   # a new cell's rhythm: new to the tune, the bar before's, or an earlier one's


def new_cell_rhythm_units(songs) -> list:
    """Each new cell of each song's tune (a bar whose rhythm and intervals
    the tune has not played) as a unit: its outcome whether its rhythm is
    new to the tune too, the bar before's, or one played earlier
    (CELL_RHYTHMS); its value the part (melody). The readings: a new
    rhythm in 77 % of new cells, the bar before's 10 %, an earlier one 13 %
    (FFVI 79 / 7 / 14; 2026-10-23). What the melody writer draws a new
    cell's rhythm by: always new had the written tunes more various than
    the games' (16.5 distinct cells in 32 against 12.5), a second urn had
    them less (3.5 distinct rhythms against 9)."""
    out = []
    for s in songs:
        cells = [c for c in melody_cells(s) if c]
        if len(cells) < 8:
            continue
        seen_cells, seen_rhythms, previous = set(), set(), None
        for cell in cells:
            rhy = cell.split(" | ")[0]
            if cell not in seen_cells:
                kind = "previous" if rhy == previous else "earlier" if rhy in seen_rhythms else "new"
                out.append(tables.Unit(s.sid, s.game, kind, {"part": R.MELODY}))
            seen_cells.add(cell)
            seen_rhythms.add(rhy)
            previous = rhy
    return out


REGISTER_BIN = 4                     # semitones: a part's register (its notes' 10th and 90th percentiles) is kept to this grain
TEMPO_BIN = 5                        # beats a minute: a song's tempo is kept to this grain


def register_notes(song: readings_mod.Song, role: str) -> list | None:
    """A layered pitched part's line voice's notes (line_voice), for its register: a part's register is its line's, not
    the span of all its voices (FFVI's layered accompaniments span 16 semitones merged, the line 12; five of its songs span
    more than 30 merged, no line does; the merged span given to every voice had put one voice over four octaves and its
    sample far above where the game played it, 2026-10-23). None for a part of one voice."""
    if role == R.DRUMS:
        return None
    voices = part_voices(song, role)
    if len(voices) < 2:
        return None
    return voices[line_voice(voices, role)]


def register_units(songs) -> list:
    """Each pitched part of each song as a unit: its outcome the register it
    plays in, "low-high" (midi, the part's notes' 10th and 90th percentiles,
    REGISTER_BIN semitones a step; a layered part's line voice's,
    register_notes); its values the part. What a song written with no
    original draws a part's register from."""
    out = []
    for s in songs:
        for role, ns in s.notes.items():
            if role == R.DRUMS:
                continue
            ns = register_notes(s, role) or ns
            pitched = sorted(n[2] for n in ns if not math.isnan(n[2]))
            if len(pitched) < 8:
                continue
            if role == R.MELODY:                           # a tune uses its extremes: the melody writer's register is the whole ambitus
                low, high = pitched[0], pitched[-1]
            else:
                low, high = pitched[int(0.1 * (len(pitched) - 1))], pitched[int(0.9 * (len(pitched) - 1))]
            out.append(tables.Unit(s.sid, s.game, f"{int(round(low / REGISTER_BIN)) * REGISTER_BIN}-{int(round(high / REGISTER_BIN)) * REGISTER_BIN}",
                                   {"part": role}))
    return out


def key_units(songs) -> list:
    """Each song as a unit: its outcome its key, "tonic mode" (the tonic a pitch class)."""
    return [tables.Unit(s.sid, s.game, f"{s.tonic} {s.mode}", {"part": "song"}) for s in songs if s.tonic is not None]


def tempo_units(songs) -> list:
    """Each song as a unit: its outcome its tempo to TEMPO_BIN beats a minute, its value the band."""
    return [tables.Unit(s.sid, s.game, str(int(round(s.bpm / TEMPO_BIN)) * TEMPO_BIN), {"part": "song", "tempo": readings_mod.band(s.bpm)}) for s in songs if s.bpm]


def weight_units(songs) -> list:
    """Each pitched part of each song as a unit: its outcome its weight in the band (WEIGHTS), its value the part."""
    return [tables.Unit(s.sid, s.game, w, {"part": role}) for s in songs for role, w in readings_mod.part_weights(s).items()]


def form_size_units(songs) -> list:
    """Each song's form as a unit: its outcome how many parts it has (to 12), its value the part (form)."""
    return [tables.Unit(s.sid, s.game, str(min(len(s.parts), 12)), {"part": "form"}) for s in songs if s.parts]


SOUND_BIN = 0.1                      # the grain a part's sounded share is kept to


def sounded_share(notes) -> float | None:
    """The share of its gap to the next note a part's note sounds, the median
    over the part; None where no two notes stand apart."""
    line = sorted(n for n in notes if not math.isnan(n[1]))
    shares = [min(1.0, n[1] / (m[0] - n[0])) for n, m in zip(line, line[1:]) if m[0] - n[0] > readings_mod.NEAR]
    return statistics.median(shares) if shares else None


GAP_CLASSES = ((1.0, "<1"), (2.0, "1-2"), (4.0, "2-4"), (1e9, "4+"))   # beats to a voice's next onset: a note's sounded share depends on it


def gap_class(gap: float) -> str:
    return next(name for top, name in GAP_CLASSES if gap < top - readings_mod.NEAR)


def gap_sound_units(songs) -> list:
    """Each note of a chord part or the bass as a unit: its outcome the share of its gap it sounds (to SOUND_BIN), its values
    the part, the voice (only; line or second where the part has two) and the gap's class. FFVI's bass plays half its gap
    under two beats and nearly all of it from two beats on (one voice: 0.83 under a beat, 0.46 at one to two, 0.97 at two
    to four; the second voice of two: 0.50, 0.45, 0.97): one share a voice had left the slap bass a hole where the game
    holds (2026-10-24)."""
    out = []
    for s in songs:
        for role in readings_mod.UPPER + (R.BASS,):
            voices = part_voices(s, role)
            if not voices:
                continue
            fastest = part_fastest(s, role)             # the part's speed class (round 35): FFVI's string pad played fast sounds a
            speed = speed_tier(fastest if fastest is not None else 0.0)   # fifth to a third of its gap, played slow nearly all of it
            if len(voices) >= 2:
                line = line_voice(voices, role)
                streams = (("line", voices[line]), ("second", [n for v, x in voices.items() if v != line for n in x]))
            else:
                streams = (("only", next(iter(voices.values()))),)
            for which, ns in streams:
                line_ = sorted((n for n in ns if not math.isnan(n[1]) and not math.isnan(n[2])), key=lambda n: n[0])
                for n, m in zip(line_, line_[1:]):
                    gap = m[0] - n[0]
                    if gap > readings_mod.NEAR:
                        share = round(min(1.0, n[1] / gap) / SOUND_BIN) * SOUND_BIN
                        out.append(tables.Unit(s.sid, s.game, f"{share:.1f}", {"part": role, "voice": which, "speed": speed, "gap": gap_class(gap)}))
    return out


def sound_units(songs) -> list:
    """Each pitched part of each song as a unit: its outcome the share of its
    gap a note sounds (to SOUND_BIN), its value the part. What a song written
    with no original gives a part's note lengths."""
    out = []
    for s in songs:
        for role, ns in s.notes.items():
            if role == R.DRUMS:
                continue
            share = sounded_share(ns)
            if share is not None:
                out.append(tables.Unit(s.sid, s.game, f"{round(share / SOUND_BIN) * SOUND_BIN:.1f}", {"part": role}))
    return out


PHRASE = 4                           # bars a phrase, as the phrase tables were counted (writer.PHRASE)
THEME = "T"                          # a phrase opening with the song's theme head (the first phrase's opening bar: the hook)
AGAIN = "r"                          # a phrase opening with a bar an earlier phrase opened with, the theme's aside
NEW = "n"                            # a phrase opening with a bar no phrase opened with yet


def phrase_windows(song: readings_mod.Song, length: int = PHRASE) -> list:
    """The tune's phrases as windows of bar indices, a part of the form at a
    time (a short tail joins the window before it): [(part index, [bar
    indices])]; bars in no part are windows of their own."""
    index = {num: k for k, num in enumerate(song.numbers or range(len(song.bars)))}
    out, covered = [], set()
    for i, (bar, n, *_) in enumerate(song.parts):
        ks = [index[num] for num in range(bar, bar + n) if num in index]
        mine = []
        for j in range(0, len(ks), length):
            chunk = ks[j:j + length]
            if len(chunk) < length and mine and mine[-1][-1] + 1 == chunk[0]:
                mine[-1] = mine[-1] + chunk
            else:
                mine.append(chunk)
        out += [(i, w) for w in mine]
        covered |= set(ks)
    out += [(None, [k]) for k in range(len(song.bars)) if k not in covered]
    return sorted(out, key=lambda x: x[1][0])


def phrase_heads(song: readings_mod.Song, role: str = None) -> list:
    """Each phrase's head, the cell of its first sounding bar: [(part index, window, head or None)]."""
    cells = melody_cells(song, role)
    return [(i, w, next((cells[k] for k in w if cells[k]), None)) for i, w in phrase_windows(song)]


def phrase_letter_units(songs) -> list:
    """Each part of each song's form (a repeat left out) as a unit: its
    outcome the letters of its phrases, each THEME where the phrase opens
    with the song's theme head (the first sounding phrase's opening bar),
    AGAIN where it opens with a bar an earlier phrase opened with, NEW
    otherwise ("T n T n"); its values the part (melody), how many phrases
    the part has (to 5) and the part's place in the form. FFVI (2026-10-23):
    a later phrase opens with the theme head in 43 % of songs, and half the
    tune's echoes point at its first four bars; the written tunes echoed as
    much but anywhere, and the theme never headed a phrase again."""
    out = []
    for s in songs:
        heads = [(i, h) for i, w, h in phrase_heads(s) if i is not None]
        if sum(1 for _, h in heads if h) < 2:
            continue
        theme = next((h for _, h in heads if h), None)
        seen, by_part = set(), {}
        for i, h in heads:
            if h is None:
                continue
            letter = THEME if h == theme else AGAIN if h in seen else NEW
            seen.add(h)
            by_part.setdefault(i, []).append(letter)
        own = {i for i, bar, n in chords_mod._own_parts(s)}
        for i, letters in by_part.items():
            if i in own and len(letters) >= 1:
                out.append(tables.Unit(s.sid, s.game, " ".join(letters), {"part": R.MELODY, "phrases": str(min(len(letters), 5)), "form": chords_mod.form_place(s, i)}))
    return out


def theme_body_units(songs) -> list:
    """Each return of the theme (a later phrase opening with the theme head)
    as a unit: its outcome how many of its next bars (to three) are the
    theme phrase's bars again, in order ("0": the head alone comes back,
    "3": the whole phrase); its value the part (melody)."""
    out = []
    for s in songs:
        cells = melody_cells(s)
        heads = [(w, h) for i, w, h in phrase_heads(s) if i is not None and h]
        if len(heads) < 2:
            continue
        theme_w, theme = heads[0]
        theme_cells = [cells[k] for k in theme_w if cells[k]]
        for w, h in heads[1:]:
            if h != theme:
                continue
            mine = [cells[k] for k in w if cells[k]]
            same = 0
            for a, b in zip(mine[1:4], theme_cells[1:4]):
                if a != b:
                    break
                same += 1
            out.append(tables.Unit(s.sid, s.game, str(same), {"part": R.MELODY}))
    return out


RETURN_PARTS = ("chords", R.BASS, R.ACCOMP)   # what may come back with the tune's theme, as the readings showed it does
RETURN_SAME = 0.5                    # the share of a return's bars that are the theme's, for a part to count as back


def return_band_units(songs) -> list:
    """Each return of the theme in each song as a unit: its outcome which of
    the band comes back with it, "chords", "bass" and "accompaniment" in
    any set (the part's bars under the returning phrase the same as under
    the theme phrase in RETURN_SAME of them or more; "none" where nothing
    does, and a part the song has not is left out of the question); its
    value the part (return). FFVI (2026-10-23): all three come back in 17
    of 46 returns, one of them in 23, none in 4; the written songs' returns
    brought the tune back over new chords and a new accompaniment every
    time, and were not heard as returns."""
    out = []
    for s in songs:
        cells = melody_cells(s)
        heads = [(w, next((cells[k] for k in w if cells[k]), None)) for i, w in phrase_windows(s) if i is not None]
        heads = [(w, h) for w, h in heads if h]
        if len(heads) < 2:
            continue
        theme_w, theme = heads[0]
        names = chords_mod.bar_chords(s) if s.tonic is not None else None
        bass = [readings_mod.figure(struck, a, s) if struck else None for _, a, _, struck in readings_mod.all_bars_of(s, R.BASS)] if R.BASS in s.notes else None
        acc = [readings_mod.pattern(p for p, _ in struck) if struck else None for _, _, _, struck in readings_mod.all_bars_of(s, R.ACCOMP)] if R.ACCOMP in s.notes else None
        for w, h in heads[1:]:
            if h != theme:
                continue
            m = min(len(theme_w), len(w))
            back = []
            for key, seq in (("chords", names), (R.BASS, bass), (R.ACCOMP, acc)):
                if seq is None:
                    continue
                pairs = [(seq[a], seq[b]) for a, b in zip(theme_w[:m], w[:m]) if seq[a] is not None or seq[b] is not None]
                if pairs and sum(1 for x, y in pairs if x == y) / len(pairs) >= RETURN_SAME:
                    back.append(key)
            out.append(tables.Unit(s.sid, s.game, " ".join(back) or "none", {"part": "return"}))
    return out


def part_voices(song: readings_mod.Song, role: str) -> dict:
    """An upper part's voices with notes: voice -> its notes (the rolls left out)."""
    return {v: ns for v, (r, ns) in song.voice_notes.items() if r == role and ns}


def line_voice(voices: dict, role: str):
    """A layered part's line among its voices: the bass's the voice with the longest notes (its sustained voice under a
    busier one), another part's the voice with the most notes (layer_units' rule)."""
    if role == R.BASS:
        lengths = {v: statistics.median([n[1] for n in ns if not math.isnan(n[1])] or [0.0]) for v, ns in voices.items()}
        return max(lengths, key=lambda v: (lengths[v], -v))
    return max(voices, key=lambda v: (len(voices[v]), -v))


def line_notes(song: readings_mod.Song, role: str) -> list | None:
    """A layered part's own line where it holds two voices or more (an upper
    part or the bass): the line voice's notes (line_voice); None for every
    other part, whose bar is the part's. The figure table counts the line,
    not the voices merged: FFVI's two-voice accompaniments strike 7.3 times
    a bar together, the line 6.6 and the second voice 4.5, and a line
    written to the merged count with a second line beside it had struck
    10.3 (2026-10-23); its two-voice basses are a sustained line under a
    busy staccato voice in the same register."""
    if role not in readings_mod.UPPER + (R.BASS,):
        return None
    voices = part_voices(song, role)
    if len(voices) < 2:
        return None
    return voices[line_voice(voices, role)]




def second_figure_units(songs) -> list:
    """Each bar of each layered part (two voices or more: the chord parts and
    the bass) as a unit: its outcome the voices beside the line in that bar
    as a mask over the line's onsets, which of them they strike with and
    the onsets of their own (second_mask; "-" where they rest), its values
    the part, the song's feel, the tempo band, the line's onset count and
    the line's own pattern. Drawn under the line's bar, bar by bar, backing
    off to the onset count where the pattern is rare. FFVI's second
    accompaniment voice strikes 4.5 times a bar beside a line of 6.6, two
    of five of its onsets with the line's; its slap bass strikes with three
    quarters of the sustained line's notes and twice as often in all (a
    second bass drawn as a figure of its own, given the line's bar, had
    struck with 41 % of the line's notes: two basses, 2026-10-24)."""
    out = []
    for s in songs:
        for role in readings_mod.UPPER + (R.BASS,):
            voices = part_voices(s, role)
            if len(voices) < 2:
                continue
            line = line_voice(voices, role)
            others = [n for v, ns in voices.items() if v != line for n in ns]
            key = lambda struck, a: readings_mod.pattern(p for p, _ in struck)   # noqa: E731  (the line's positions; the bass's marks are the line's own)
            line_bars = {k: key(struck, a) for k, a, struck in readings_mod.numbered_bars_of(s, role, voices[line])}
            line_struck = {k: [p for p, _ in struck] for k, a, struck in readings_mod.numbered_bars_of(s, role, voices[line])}
            tempo, feel = readings_mod.band(s.bpm), song_feel(s)
            density = arrangement_mod.layer_share_class(len(others) / max(1, len(voices[line])))   # the voices beside the line: their notes over the line's (round 65)
            for k, a, struck in readings_mod.numbered_bars_of(s, role, others):
                if line_bars.get(k, "-") != "-":
                    outcome = second_mask(line_struck[k], [p for p, _ in struck])
                    out.append(tables.Unit(s.sid, s.game, outcome,                   # by the line's onset count: a mask is read onset by onset
                                           {"part": role, "layer": density, "feel": feel, "tempo": tempo, "onsets": str(len(line_bars[k].split())), "line": line_bars[k]}))
    return out


def second_mask(line_positions: list, other_positions: list) -> str:
    """An upper part's second voice's bar beside the line's: a flag an onset of the line (1: the voice strikes with it, 0:
    not), then, after a bar, the voice's own onsets off the line's ("1 0 1 0 | 7/2"); "-" where it rests. FFVI's voices
    beside an arpeggiated line strike with two thirds of their onsets on the line's, at 0.6 of its density (2026-10-23):
    a pattern drawn on its own had fallen with the line's a seventh of the time, four unrelated lines in one register."""
    if not other_positions:
        return "-"
    on = set(line_positions)
    flags = " ".join("1" if p in other_positions else "0" for p in line_positions)
    own = " ".join(str(p) for p in other_positions if p not in on)
    if not flags:                                           # the line rests through the bar: the voice's own onsets alone (the
        return "| " + own                                   # counter-line fills 0.61 of the tune's resting time in FFVI)
    return flags + (" | " + own if own else "")


def apply_mask(line_pattern: str, outcome: str) -> str:
    """The second voice's bar (a pattern) from the line's bar and a second_mask outcome: the line's onsets it strikes with (a
    mask shorter or longer than the line's onsets is read around it) and its own onsets; "-" where it rests. Where the
    line rests ("-") the voice's own onsets stand alone (the counter-line under a resting tune; the chord parts' voices
    never meet this: their mask is drawn under a playing line only)."""
    if outcome == "-" or not outcome:
        return "-"
    flags, bar, own = outcome.partition("|")
    bits = flags.split()
    if bits and not bar and all(b not in ("0", "1") for b in bits):
        return outcome if ":" not in outcome else "-"          # an old-style absolute pattern: as it stands
    line = [] if line_pattern in ("-", "") else [Fraction(t.partition(":")[0]) for t in line_pattern.split()]
    positions = {line[i] for i in range(len(line)) if bits and bits[i % len(bits)] == "1"}
    positions |= {Fraction(p) for p in own.split()}
    return readings_mod.pattern(sorted(positions))


COUNTER_KINDS = ("same", "other")    # the counter-line beside the tune: on the tune's own sample, or on another


def tune_line(song: readings_mod.Song, role: str) -> list:
    """The tune's line for the melody or the counter-line: the voice with the most notes where the part holds two or more
    (line_voice), else the part's notes; [] where the song has no such part."""
    voices = part_voices(song, role)
    if len(voices) >= 2:
        return voices[line_voice(voices, role)]
    return song.notes.get(role, [])


def main_sample(notes) -> str | None:
    """The sample most of a line's notes play on; None where none is known."""
    c = Counter(n[3] for n in notes if n[3])
    return c.most_common(1)[0][0] if c else None


def counter_kind(song: readings_mod.Song) -> str | None:
    """How a song's counter-line stands to its tune in timbre (COUNTER_KINDS): "same" where it plays the tune's sample,
    "other" where not; None where the song lacks either part. FFVI's counter plays the tune's sample in 18 songs of 52,
    and there it is a harmony line in thirds (36 % of their shared strikes a third off); on another sample it sits at
    octaves and unisons (37 %) and plays 1.57 times the tune's notes (2026-10-24)."""
    mel, ctr = tune_line(song, R.MELODY), tune_line(song, R.COUNTER)
    if not mel or not ctr:
        return None
    return "same" if main_sample(mel) == main_sample(ctr) else "other"


def counter_figure_units(songs) -> list:
    """Each bar of a song's counter-line beside its tune as a unit (second_figure_units' shape, the tune's line as the
    line): its outcome the counter's bar as a mask over the tune's onsets, which of them it strikes with and the onsets of
    its own (second_mask; "-" where it rests under the tune, its own onsets alone where the tune rests), its values the
    part, the song's feel, the tempo band, the tune's onset count and its pattern ("-" and 0 where the tune rests). A bar
    both rest in is the texture's, not counted. FFVI's counter plays WITH the tune, not in its rests: 0.67 of its onsets
    on the tune's, 0.82 of its sounding time under the tune's notes, 1.42 times the tune's notes, and it fills 0.61 of
    the tune's resting time; the written counter, a second tune from the melody writer's own stream, had 0.43 of its
    onsets on the tune's and Whole 28 0.19, two tunes interleaved on one timbre (2026-10-24)."""
    out = []
    for s in songs:
        mel, ctr = tune_line(s, R.MELODY), tune_line(s, R.COUNTER)
        if not mel or not ctr:
            continue
        tempo, feel = readings_mod.band(s.bpm), song_feel(s)
        weight = readings_mod.part_weights(s).get(R.COUNTER, "minor")   # the counter's weight in the band (round 47): FFVI's minor counter plays 0.74
        tune_bars = {k: [p for p, _ in struck] for k, a, struck in readings_mod.numbered_bars_of(s, R.MELODY, mel)}   # of the tune's notes a bar, its
        for k, a, struck in readings_mod.numbered_bars_of(s, R.COUNTER, ctr):                                       # half one 0.91, its main one 1.45;
            line, mine = tune_bars.get(k, []), [p for p, _ in struck]                                   # the mask drawn without it had every
            if not line and not mine:                                                                   # written counter at six notes a bar
                continue
            out.append(tables.Unit(s.sid, s.game, second_mask(line, mine),
                                   {"part": R.COUNTER, "weight": weight, "feel": feel, "tempo": tempo, "onsets": str(len(line)), "line": readings_mod.pattern(line)}))
    return out


def counter_sample_units(songs) -> list:
    """Each song with a tune and a counter-line as a unit: its outcome whether the counter plays the tune's sample
    (counter_kind: same, other), its value the part. Drawn once a song: the kind the counter's interval and move words
    are drawn under, and whether the rendering gives it the tune's sample (18 of FFVI's 52; the written songs had 3 of
    14 by the pool's choice, and Whole 28 the tune's sample and register with 0.19 of its onsets on the tune's)."""
    out = []
    for s in songs:
        kind = counter_kind(s)
        if kind is not None:
            out.append(tables.Unit(s.sid, s.game, kind, {"part": R.COUNTER}))
    return out


TUNE_SHARES = ((0.65, "<0.7"), (0.85, "0.7-0.8"), (1e9, "0.9+"))   # the tune's share of the loudest part, in tenths: FFVI's terciles over
                                                                      # its 52 songs with a counter (20, 15 and 17 songs; 2026-10-24)


def tune_share_band(share: float) -> str:
    """The band the tune's share of the loudest part falls in (TUNE_SHARES): the context the counter's level is drawn under."""
    return next(name for top, name in TUNE_SHARES if share < top)


def counter_share_units(songs) -> list:
    """Each song with a tune and a counter-line, both with a level, as a unit: the counter's median level as a share of the
    song's loudest part's, in tenths (level_units' unit), its values the part and the band the tune's own share falls in
    (tune_share_band). Drawn once a song after the tune's `levels` draw, under that draw's band: FFVI's counter is never
    above the loudest part (its share 0.60 at the median, 0.9 or more in 6 of 52), and its four counters louder than the
    tune sit on tunes at 0.59 of the loudest. The word before (counter_levels: the counter over the tune in tenths, drawn
    apart from the tune's share and multiplied into it) let the product pass the loudest part in 0.037 of plans and reach
    0.9 in 0.240; Whole 28 drew 1.5 on a tune at 0.7, the counter at 1.05 of the loudest, +3.5 dB over the tune by level
    alone. A share of the loudest never passes 1.0 (2026-10-24, round 31)."""
    out = []
    for s in songs:
        a, b = s.levels.get(R.MELODY), s.levels.get(R.COUNTER)
        if a and b and counter_kind(s) is not None:
            top = max(s.levels.values())
            out.append(tables.Unit(s.sid, s.game, f"{round(b / top, 1):.1f}", {"part": R.COUNTER, "tune": tune_share_band(round(a / top, 1))}))
    return out


def counter_pair_units(songs) -> list:
    """Each song with a tune and a counter-line on another sample (counter_kind "other") as a unit: its outcome the
    counter's sample as the pack names it (sample_id of the line's main sample), its values the part and the tune's
    sample. Drawn once a song at the rendering, under the tune's sample, where the pack holds the drawn sample and it
    reaches the register the counter was written in; the part's level, the counter's sample over all tunes, is the
    back-off and still a count; the pool rule by register and speed only where nothing counted fits (whole.counter_pair_for).
    FFVI's counter sample is darker than the tune's in 17 of the 23 pairs the pack holds; the pool rule had given Whole
    28's counter sdbd05ab4d5 beside a tune on sf89f5aedfd, a sample 4.2 dB louder in its body and nearly twice as bright,
    which FFVI never plays as a counter against another tune sample (2026-10-24)."""
    out = []
    for s in songs:
        if counter_kind(s) != "other":
            continue
        tm, tc = main_sample(tune_line(s, R.MELODY)), main_sample(tune_line(s, R.COUNTER))
        if tm and tc:
            out.append(tables.Unit(s.sid, s.game, sample_id(tc), {"part": R.COUNTER, "tune": sample_id(tm)}))
    return out


def sample_id(key: str) -> str:
    """A reading's sample key as a pack names the sample (pack.voice_of): "s" and its first ten characters."""
    return "s" + key[:10]


LENGTH_BINS = (40, 60, 80, 120, 160, 240, 400, 1e9)   # ms: the shortest note a sample is played at, to the bin's top ("long" past 400)
SPEED_BINS = (2, 3, 4, 6, 8, 12, 24, 1e9)              # notes a second: the fastest bars a sample is played in ("faster" past 24)


def _bin(value: float, bins: tuple, last: str) -> str:
    top = next(b for b in bins if value <= b)
    return str(top) if top < 1e9 else last


def _sample_plays(songs):
    """Per song and tonal sample: its notes' lengths (ms) and its bars' rates (notes a second), over every pitched part."""
    for s in songs:
        beat = 60 / s.bpm
        lengths, rates = defaultdict(list), defaultdict(list)
        for role, ns in s.notes.items():
            if role == R.DRUMS:
                continue
            for n in ns:
                if isinstance(n[3], str) and n[1] == n[1]:
                    lengths[sample_id(n[3])].append(n[1] * beat * 1000)
            for _, a, b, struck in readings_mod.all_bars_of(s, role):
                counts = Counter(sample_id(n[3]) for _, group in struck for n in group if isinstance(n[3], str))
                for key, c in counts.items():
                    rates[key].append(c / max(1e-9, (b - a) * beat))
        for key in lengths:
            if len(lengths[key]) >= 8:
                yield s, key, sorted(lengths[key]), sorted(rates.get(key, [0.0]))


def sample_length_units(songs) -> list:
    """Each tonal sample of each song as a unit: its outcome the shortest note
    the game plays it at there (the tenth percentile of its notes' lengths,
    in ms to LENGTH_BINS' tops), its value the sample (as the pack names
    it). A sample's floor: a note shorter than the game ever plays a sample
    never reaches its body (a one-second pad with a 39 ms attack had been
    played at 50 ms sixteenths, Song Check 14's Whole 02; FFVI plays it at
    65 ms at the shortest)."""
    out = []
    for s, key, lengths, rates in _sample_plays(songs):
        speed = speed_tier(rates[int(0.9 * (len(rates) - 1))])   # the sample's speed class in the song (round 36): a floor drawn from a
        out.append(tables.Unit(s.sid, s.game, _bin(lengths[int(0.1 * (len(lengths) - 1))], LENGTH_BINS, "long"), {"part": key, "speed": speed}))   # slow song had raised a fast part's notes
    return out


def sample_speed_units(songs) -> list:
    """Each tonal sample of each song as a unit: its outcome the fastest bars
    the game plays it in there (the 90th percentile of its bars' notes a
    second, to SPEED_BINS' tops), its value the sample. What the sample's
    choice weighs beside the part's register: the part's fastest bar against
    the speeds the game plays each sample at (FFVI keeps its slow-attack pad
    under six notes a second; a written part had it at eight)."""
    out = []
    for s, key, _, rates in _sample_plays(songs):
        out.append(tables.Unit(s.sid, s.game, _bin(rates[int(0.9 * (len(rates) - 1))], SPEED_BINS, "faster"), {"part": key}))
    return out


SPEED_TIERS = ((3.0, "slow"), (6.0, "medium"), (1e9, "fast"))   # a part's fastest bar, notes a second: the class its note lengths are counted under


def speed_tier(rate: float) -> str:
    """The class of a part's fastest bar (SPEED_TIERS), as gap_sounds is conditioned on it (round 35)."""
    return next(name for top, name in SPEED_TIERS if rate <= top)


def _part_rates(s: readings_mod.Song, role: str) -> tuple:
    """A part's line bar by bar: (onset counts, notes a second), every bar of the song."""
    beat = 60.0 / s.bpm
    ns = s.notes.get(role) or []
    mine = {(n[0], n[2]) for n in (line_notes(s, role) or ns)}
    counts, rates = [], []
    for _, a, b, struck in readings_mod.all_bars_of(s, role):
        c = sum(1 for _, group in struck for n in group if (n[0], n[2]) in mine)
        counts.append(c)
        rates.append(c / max(1e-9, (b - a) * beat))
    return counts, rates


def part_fastest(s: readings_mod.Song, role: str) -> float | None:
    """A part's fastest bar: the 90th percentile of its line's bars' notes a second, over the bars it plays; None under four bars."""
    counts, rates = _part_rates(s, role)
    played = sorted(r for r, c in zip(rates, counts) if c)
    if len(counts) < 4 or not played:
        return None
    return played[int(0.9 * (len(played) - 1))]


def part_speed_units(songs) -> list:
    """Each pitched part of each song as a unit: its outcome the part's
    fastest bars (the 90th percentile of its line's bars' notes a second, to
    SPEED_BINS' tops), its values the part and its habit's density tier
    (habit_of over the line's onsets a bar, as _rhythm_habit and _bass_habit
    bin it). What a planned part's sample is fitted to for speed before the
    part is written (round 34): the fit had read the speed off the written
    notes, so the sample came after the writing and a voice's register could
    not come from the sample it plays."""
    out = []
    for s in songs:
        for role, ns in s.notes.items():
            if role == R.DRUMS or not ns:
                continue
            counts, _ = _part_rates(s, role)
            fastest = part_fastest(s, role)
            if fastest is None:
                continue
            tier = readings_mod.habit_of(sum(counts) / len(counts), readings_mod.DENSITIES)
            out.append(tables.Unit(s.sid, s.game, _bin(fastest, SPEED_BINS, "faster"), {"part": role, "habit": tier}))
    return out


def layer_sample_units(songs) -> list:
    """Each layered part of each song (two voices or more, the drums left
    out) as a unit: its outcome the samples its line and its second voice
    play, as a pair of the pack's sample names ("sa692eac0a6 sb34cb55c14"),
    each voice's the sample it plays most; its value the part. Drawn once
    a song: FFVI's two-voice bass is a long sustained sample under a short
    one, the same long sample in ten of its thirteen songs; on one sample
    for both, the busy voice had played on the long bass (2026-10-23)."""
    out = []
    for s in songs:
        for role in readings_mod.UPPER + (R.COUNTER, R.MELODY, R.BASS):   # every part the plan gives layers (the counter-line had no pairs of its
            voices = part_voices(s, role)                   # own, and a draw for it fell through to the root: an accompaniment pair)
            if len(voices) < 2:
                continue
            line = line_voice(voices, role)
            other = max((v for v in voices if v != line), key=lambda v: (len(voices[v]), -v))
            keys = []
            for v in (line, other):
                played = Counter(n[3] for n in voices[v] if isinstance(n[3], str))
                if not played:
                    break
                keys.append(sample_id(played.most_common(1)[0][0]))
            if len(keys) == 2:
                out.append(tables.Unit(s.sid, s.game, " ".join(keys), {"part": role}))
    return out


def layer_sound_units(songs) -> list:
    """Each layered part of each song (two voices or more; the drums left
    out) as two units: the share of its gap a note sounds (sound_units'
    grain) for the line and for the voices beside it; the values the part
    and the voice (line, second). FFVI's second bass voice is the staccato
    one under a sustained line; the part's one share had given both lines
    the same lengths."""
    out = []
    for s in songs:
        for role in readings_mod.UPPER + (R.BASS,):
            voices = part_voices(s, role)
            if len(voices) < 2:
                continue
            line = line_voice(voices, role)
            for which, ns in (("line", voices[line]), ("second", [n for v, x in voices.items() if v != line for n in x])):
                share = sounded_share(ns)
                if share is not None:
                    out.append(tables.Unit(s.sid, s.game, f"{round(share / SOUND_BIN) * SOUND_BIN:.1f}", {"part": role, "voice": which}))
    return out


THEME_PARTS = (R.COUNTER, R.BASS, R.ACCOMP, R.HARMONY)   # the parts that double or carry the tune's theme


def _theme_of(song: readings_mod.Song):
    """The tune's cells, its phrase windows (the live ones) and its theme: the head cell of its first sounding phrase
    and that phrase's window; (cells, windows, theme window, theme) or None without two sounding phrases."""
    cells = melody_cells(song)
    windows = [(w, next((cells[k] for k in w if cells[k]), None)) for i, w in phrase_windows(song) if i is not None]
    heads = [(w, h) for w, h in windows if h]
    if len(heads) < 2:
        return None
    return cells, windows, heads[0][0], heads[0][1]


def tune_doubling_units(songs) -> list:
    """Each bar in which a song's tune plays a cell that is NOT its theme cell as a unit: its outcome which other parts
    (THEME_PARTS) play the same cell in that bar and how far from the tune (theme_doubling_units' token: "bass:-24
    counter:+0"; "none"), its values the part (tune) and the place (other). The theme's bars are theme_doubling's. Round
    44 (2026-10-28): FFVI doubles the tune's onsets at the same pitch class 0.40 of the time, its half-bar cells at once
    0.24, by the accompaniment, the bass and the counter an octave or two under and in the tune's octave; the written
    songs 0.22 and 0.03, the theme cell being the only one a word doubled."""
    out = []
    for s in songs:
        found = _theme_of(s)
        if found is None:
            continue
        cells, _, theme_w, theme = found
        tune = sorted(arrangement_mod._line(s.notes.get(R.MELODY, [])))
        others = {role: (melody_cells(s, role), sorted(arrangement_mod._line(s.notes[role]))) for role in THEME_PARTS if s.notes.get(role)}
        for k, c in enumerate(cells):
            if not c or c == theme:
                continue
            a = s.bars[k][0]
            t0 = next((n for n in tune if n[0] >= a - readings_mod.NEAR), None)
            tokens = []
            for role, (oc, line) in others.items():
                if k < len(oc) and oc[k] == c:
                    o0 = next((n for n in line if n[0] >= a - readings_mod.NEAR), None)
                    if t0 is not None and o0 is not None:
                        tokens.append(f"{role}:{round(o0[2] - t0[2]):+d}")
            out.append(tables.Unit(s.sid, s.game, " ".join(sorted(tokens)) or "none", {"part": "tune", "place": "other"}))
    return out


def theme_doubling_units(songs) -> list:
    """Each bar in which a song's tune plays its theme cell (the head of its
    first sounding phrase: its statement, and its echoes later) as a unit:
    its outcome which other parts play the same cell in that bar and how
    far from the tune ("counter:+0 bass:-24"; "none"), its values the part
    (theme) and the place (statement: inside the theme's own phrase;
    later). FFVI (2026-10-23): where another part plays the theme's cell,
    the tune is playing it too in three places of four, the counter in the
    tune's octave, the bass two below: the hook doubled by a second
    instrument, a bar at a time, in a quarter of the songs."""
    out = []
    for s in songs:
        found = _theme_of(s)
        if found is None:
            continue
        cells, _, theme_w, theme = found
        tune = sorted(arrangement_mod._line(s.notes.get(R.MELODY, [])))
        others = {role: (melody_cells(s, role), sorted(arrangement_mod._line(s.notes[role]))) for role in THEME_PARTS if s.notes.get(role)}
        for k, c in enumerate(cells):
            if c != theme:
                continue
            a = s.bars[k][0]
            t0 = next((n for n in tune if n[0] >= a - readings_mod.NEAR), None)
            tokens = []
            for role, (oc, line) in others.items():
                if k < len(oc) and oc[k] == theme:
                    o0 = next((n for n in line if n[0] >= a - readings_mod.NEAR), None)
                    if t0 is not None and o0 is not None:
                        tokens.append(f"{role}:{round(o0[2] - t0[2]):+d}")
            out.append(tables.Unit(s.sid, s.game, " ".join(sorted(tokens)) or "none",
                                   {"part": "theme", "place": "statement" if k in theme_w else "later"}))
    return out


def theme_carrier_units(songs) -> list:
    """Each phrase of a song's tune after its theme phrase whose head is not
    the theme (the tune resting through it too) as a unit: its outcome the
    part that carries the theme phrase there instead, its bars the theme
    phrase's from the phrase's first bar, two or more (the bass, the
    counter or the accompaniment), "none" where no part does; its value
    the part (carrier). FFVI (2026-10-23): the bass carries four bars of
    the theme in nine places, the counter a few; a hand-off a fifth of the
    songs make once."""
    out = []
    for s in songs:
        found = _theme_of(s)
        if found is None:
            continue
        cells, windows, theme_w, theme = found
        theme_cells = [cells[k] for k in theme_w]
        need = min(2, sum(1 for c in theme_cells if c))
        others = {role: melody_cells(s, role) for role in (R.BASS, R.COUNTER, R.ACCOMP) if s.notes.get(role)}
        for w, h in windows:
            if w[0] <= theme_w[0] or h == theme:
                continue
            carrier = "none"
            for role, oc in others.items():
                run = 0
                while run < len(theme_cells) and w[0] + run < len(oc) and theme_cells[run] is not None and oc[w[0] + run] == theme_cells[run]:
                    run += 1
                if run >= need:
                    carrier = role
                    break
            out.append(tables.Unit(s.sid, s.game, carrier, {"part": "carrier"}))
    return out


FEELS = ("duple", "triple")
TRIPLE_SHARE = 0.25                   # the share of a song's onsets on triplet positions from which its feel is triple


def song_feel(song: readings_mod.Song) -> str:
    """A song's feel: "triple" where TRIPLE_SHARE of its onsets or more fall
    on triplet positions (thirds, sixths, twelfths of a beat: 6/8 read on a
    4/4 grid, a shuffle), "duple" otherwise. Counted once a song; every
    figure table is conditioned on it, so a written song draws one feel and
    all its parts' bars in that feel. FFVI (2026-10-23): bass bars on
    triplet positions, 18 % of its bars, came only from its compound and
    shuffle songs; drawn unconditioned into a straight song they stumbled
    against straight drums (Song Check 8's Whole 10)."""
    if song.feel:
        return song.feel
    total, triple = 0, 0
    for role, ns in song.notes.items():
        for n in ns:
            k = bisect.bisect_right([a for a, _ in song.bars], n[0] + readings_mod.NEAR) - 1
            if k < 0:
                continue
            p = readings_mod.position(n[0] - song.bars[k][0], song.division)
            total += 1
            triple += Fraction(p).denominator in (3, 6, 12)
    song.feel = "triple" if total and triple / total >= TRIPLE_SHARE else "duple"
    return song.feel


def feel_units(songs) -> list:
    """Each song's feel (song_feel) as a unit, one a song; its value the part (song)."""
    return [tables.Unit(s.sid, s.game, song_feel(s), {"part": "song"}) for s in songs]


BACKING = (R.DRUMS, R.BASS, R.ACCOMP, R.HARMONY, R.ARP)   # the parts under the tune: a riff's parts
PERIODS = (1, 2, 4, 8)                # bars: the lags a backing part's bars are tried at inside a part of the form
PERIOD_HELD = 0.6                     # the share of a part's bars that must play the bar a lag before for the lag to be its period


def part_length(n: int) -> str:
    """A part of the form's length as a class (PART_LENGTHS)."""
    return next(name for top, name in form_mod.PART_LENGTHS if n <= top)


def block_key(song: readings_mod.Song, role: str, a: float, b: float):
    """A backing part's bar as the writers draw it: the bass's figure
    (positions with chord-tone marks), the drums' pieces by position, an
    upper part's onset pattern; a riff that moves with the chord keeps its
    key. () where the part rests."""
    struck = {}
    for n in song.notes.get(role, []):
        if a - readings_mod.NEAR <= n[0] < b - readings_mod.NEAR:
            struck.setdefault(readings_mod.position(n[0] - a, song.division), []).append(n)
    struck = sorted(struck.items())
    if not struck:
        return ()
    if role == R.BASS:
        return readings_mod.figure(struck, a, song)
    if role == R.DRUMS:
        return tuple(sorted((p, str(n[3])) for p, ns in struck for n in ns))
    return readings_mod.pattern(p for p, _ in struck)


def _blocks(song: readings_mod.Song):
    """Each new part of a song's form (a repeat left out) with its bars' indices, its length and, per backing part the
    song has, that part's bar keys (block_key)."""
    index = {num: k for k, num in enumerate(song.numbers or range(len(song.bars)))}
    keys = {role: [block_key(song, role, a, b) for a, b in song.bars] for role in BACKING if song.notes.get(role)}
    for bar, n, of, label in song.parts:
        if of is not None:
            continue
        idx = [index[num] for num in range(bar, bar + n) if num in index]
        if len(idx) >= 2 and keys:
            yield idx, n, keys


def period_of(keys: list, idx: list):
    """The lag (PERIODS, the shortest first) at which a part's bars repeat through a part of the form, PERIOD_HELD of
    them or more; None where none does or the part sounds in fewer than two bars."""
    if sum(1 for k in idx if keys[k]) < 2:
        return None
    for lag in PERIODS:
        if lag >= len(idx):
            return None
        pairs = [(k, k - lag) for k in idx[lag:] if keys[k] or keys[k - lag]]
        if pairs and sum(1 for k, j in pairs if keys[k] == keys[j]) / len(pairs) >= PERIOD_HELD:
            return lag
    return None


def period_units(songs) -> list:
    """Each backing part of each new part of each song's form as a unit:
    its outcome the part's period there, the lag in bars at which its bars
    repeat (1, 2, 4, 8) or "none"; its values the part, the part of the
    form's length (short, medium, long) and the tempo band. The riff under
    the tune, a bass or a kit playing the same two bars through a part,
    which the parts' mixtures (a bar the same as the one before, an earlier
    one, new) do not do at a fixed lag. FFVI (2026-10-23, held 0.75): a
    third of its bass and accompaniment parts and two fifths of its drum
    parts have one; the same across 39 games."""
    out = []
    for s in songs:
        tempo = readings_mod.band(s.bpm)
        for idx, n, keys in _blocks(s):
            for role, ks in keys.items():
                if sum(1 for k in idx if ks[k]) < 2:
                    continue
                lag = period_of(ks, idx)
                out.append(tables.Unit(s.sid, s.game, str(lag) if lag else "none", {"part": role, "length": part_length(n), "tempo": tempo}))
    return out


def period_hold_units(songs) -> list:
    """Each bar inside a backing part's period (period_units) as a unit:
    its outcome "held" where the bar plays the bar a period before again,
    "varied" where it does not (a fill, a turnaround); its values the part
    and the period."""
    out = []
    for s in songs:
        for idx, n, keys in _blocks(s):
            for role, ks in keys.items():
                lag = period_of(ks, idx)
                if lag is None:
                    continue
                for k in idx[lag:]:
                    if ks[k] or ks[k - lag]:
                        out.append(tables.Unit(s.sid, s.game, "held" if ks[k] == ks[k - lag] else "varied", {"part": role, "period": str(lag)}))
    return out


def recall_continue_units(songs) -> list:
    """Each echo of a song's tune that has a bar after it as a unit: whether the next bar goes on with the bar after the
    echo's source ("yes": the passage recalled continues; "no"), by part and echo habit. Round 50 (2026-10-28): the writer
    had carried a recalled passage on with a constant share (CONTINUE 0.8); this is FFVI's. An echo is a bar whose cell
    was played earlier and is not the bar before's; its sources are every earlier bar with that cell."""
    out = []
    for s in songs:
        if R.MELODY not in s.notes:
            continue
        cells = melody_cells(s)
        habit = _echo_habit(cells)
        for k in range(len(cells) - 1):
            c, nxt = cells[k], cells[k + 1]
            if not c or not nxt or (k and cells[k - 1] == c) or c not in cells[:k]:
                continue
            sources = [j for j in range(k) if cells[j] == c and j + 1 < k and cells[j + 1]]
            if not sources:
                continue
            out.append(tables.Unit(s.sid, s.game, "yes" if any(cells[j + 1] == nxt for j in sources) else "no", {"part": R.MELODY, "habit": habit}))
    return out


def melody_recall_units(songs) -> list:
    """What each tune bar is to its song so far (same, earlier, new): the urn's shares, by part and echo habit."""
    return tables.recall_units(melody_cell_units(songs))


def echo_habit_units(songs) -> list:
    """Each song's echo habit for the tune, one unit a song, with the tempo band and the melody's weight beside."""
    return readings_mod.habits(melody_cell_units(songs))
