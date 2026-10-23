"""The vocabulary from the readings (stage 4 of docs/TRANSLATOR.md), the
last two items: the chords through each part of a song, and the melody's
phrase shapes, over a game's songs in the readings database.

    python -m bitcomposer.translate.phrases [--db PATH] [--game NAME] [--top N] [--games]
                                             [--against PACK ...] [--songs N] [--heard JSON]

The songs are the harmony counts' (vocab.py: on a beat, with a key, their
chord beats mostly fit), each once through, that have a form read (form.py
reads none from under four bars or sixteen notes). The parts are the form
reader's at the level of parts (the form table: a phrase; a short phrase
played again at once is two parts, which the sections level joins), and a
part that repeats an earlier one is left out of the progressions, since
its chords were counted in the one it repeats; the phrases are cut from
every part.

Progressions. The chord reader changes chord every beat over half the time
(FFVI: half its fit spans are a beat long), so counted beat by beat a part's
progression is buried in passing chords: a melody's passing note over a
held I reads as a beat of IV or ii. Each half bar (a bar of three whole)
takes the fit chord sounding most of it, the one sounding first at a tie:
the chords on the strong beats, which is where a progression's chords sit
and the bass's root changes; a whole bar would lose the change on the
third beat, the commonest place for one after the bar line (how many moves
each level keeps is printed). The chords are named by degree alone (I, IV,
bVII; the quality and shape dropped: I, I5 and Isus4 are one chord held
with its third coming and going, and vocab.py's moves showed the habit by
degree). A part's progression is its chords through its bars, runs of one
chord merged; where the sequence repeats a cycle (I IV V I IV V I) the
cycle is the progression. With it: every run of three chords, what chord a
part begins on, what it ends on and its cadence (V -> I, IV -> I, bVII -> I
with the natural minor's VII -> I, another chord to I, a half cadence
ending on V, elsewhere, or one chord throughout), what the song loops back
on (its last chord to the loop bar's first, classed the same way), and how
often the chord changes through a part (the reader's fit spans starting in
its first bar, its middle bars and its last: whether it speeds up into the
cadence).

Phrases. The melody over three lengths of phrase: the part, four bars and
two bars cut from the part's start (a leftover under half a phrase, or a
single bar, joins the phrase before). The tune is the melody voice's line
(of notes struck together, the highest); where the melody voice rests
through a phrase (fewer than MIN_NOTES notes), the counter-line's stands in,
since in FFVI the tune passes to a voice read as counter-line or
accompaniment in a fifth of the melody's bars, and a phrase with neither is
resting and left out (the shares are printed; the accompaniment does not
stand in, its line being the chord's top). A note's length is the time to
the next, as the rhythm counts take it. The contour is from the mean pitch
of the phrase's thirds by time: an arch where the middle sits LEVEL
semitones over both ends, a valley under both, rising or falling where the
ends differ by LEVEL, level otherwise. The peak is the first highest note,
placed in the phrase's quarters; the range the highest to the lowest; the
first note and the end note (the one held longest in the last bar, since
a phrase's last notes are often the pickup into the next) are named
against the key (the scale degree, or off the scale) and against the chord
read at their onset (which of its tones).
Against the phrase before it at the same length, in the same song:
repeated when SAME of the notes match in place and pitch, moved up or down
when they match shifted by a constant interval (a semitone's drift
allowed: a diatonic sequence shifts its intervals), answered when the
rhythm matches (SAME of the onsets) but the tune does not, new otherwise.
Whether a phrase ending a part ends on the tonic is counted apart, and the
song's last phrase before its loop.

against.py sets songs composed with a pack beside these counts (--phrases):
a composed song's parts are read by the same form reader over its notes
placed in time, since its plan records its sections' kinds but not their
lengths; games.py --phrases gives each game's headline numbers. --heard
scores the form reader's parts against parts marked by ear and counts the
marked songs on both."""
import argparse
import bisect
import json
import math
import os
import statistics
import sys
from array import array
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from types import SimpleNamespace

from . import form as form_mod, roles as R, store, vocab
from .rhythm import NEAR, START, Tally, _chord_at, _line, habit_of
from . import tables
from .vocab import FIT, Span, _beats_at, _median, _pct, tone_of

LENGTHS = ("part", 4, 2)             # the phrase lengths: the part, four bars, two bars
MIN_NOTES = 3                        # notes a phrase needs to have a shape
SAME = 0.75                          # the share of notes that must match for a repeat
LEVEL = 2.0                          # semitones a contour's thirds must differ by
AGREE = 0.75                         # bars a marked part start may sit from a read one
CONTOURS = ("rising", "falling", "arch", "valley", "level")
QUARTERS = ("first quarter", "second", "third", "last")
RELATIONS = ("repeated", "moved up", "moved down", "answered", "new", "first")
CADENCES = ("V -> I", "IV -> I", "bVII -> I", "another -> I", "half (on V)", "elsewhere", "one chord")
LOOPS = CADENCES[:-1] + ("the same chord",)
SPANS = ((1, "one chord"), (4, "2 to 4 chords"), (8, "5 to 8"), (1e9, "more"))
RANGES = ((8, "within a fifth"), (13, "an octave"), (1e9, "more"))
DEGREE_OF = {"major": {0: "1", 2: "2", 4: "3", 5: "4", 7: "5", 9: "6", 11: "7"},
             "minor": {0: "1", 2: "2", 3: "3", 5: "4", 7: "5", 8: "6", 10: "7"}}
KEY_NAMES = ("1", "3", "5", "another degree", "off the scale")
CHORD_NAMES = ("root", "third", "fifth", "another tone", "no chord")
SUBTONIC = {"bVII", "VII"}           # major's bVII and the natural minor's VII: the same chord
ROLES = (R.MELODY, R.COUNTER)


@dataclass
class Part:
    label: str
    bar: int                         # its first bar, an index into the song's bars
    bars: int
    of: int | None = None            # the earlier part it repeats


@dataclass
class Song:
    """What a song's reading gives the counts: its key, meter, bars (start,
    end in beats, the grid's, once through), chord spans, melody and
    counter-line notes (start, length, midi) and its parts."""
    title: str
    tonic: int
    mode: str
    meter: int
    bars: list
    chords: list
    notes: dict = field(default_factory=dict)
    parts: list = field(default_factory=list)
    loop_bar: int | None = None
    sid: str = ""                    # its id in the readings, and its game (the tables' split)
    game: str = ""


def load(db, game: str | None = None, song: str | None = None) -> tuple[list[Song], dict]:
    """The songs to count (game: only that game's; song: only that id), and
    why the others were left out: {"free time": n, "no key": n, "unfit": n,
    "no form": n}."""
    songs, out = [], Counter()
    where, args = ("WHERE id = ?", (song,)) if song else ("WHERE game = ?", (game,)) if game else ("", ())
    for sid, title, bpm, meter, tonic, mode, seconds, loop_bar, loop_seconds, game_name in db.execute(
            f"SELECT id, title, bpm, meter, key_tonic, key_mode, seconds, loop_bar, loop_seconds, game FROM songs {where}", args):
        row = db.execute("SELECT beats, bars FROM beats WHERE song = ?", (sid,)).fetchone()
        if bpm is None or not row:
            out["free time"] += 1
            continue
        if tonic is None:
            out["no key"] += 1
            continue
        beats, bars = array("d"), array("d")
        beats.frombytes(row[0])
        bars.frombytes(row[1])
        end = _beats_at(beats, seconds)
        if loop_bar is not None and loop_seconds and loop_bar < len(bars):
            end = min(end, _beats_at(beats, bars[loop_bar] + loop_seconds))
        chords = [Span(a, min(b, end), root, shape, fit) for a, b, root, shape, fit in
                  db.execute("SELECT start, end, root, shape, fit FROM chords WHERE song = ? ORDER BY start", (sid,))
                  if a < end]
        total = sum(c.beats for c in chords)
        if not total or sum(c.beats for c in chords if c.root is not None and c.fit >= FIT) <= total / 2:
            out["unfit"] += 1
            continue
        parts = [Part(label, bar, n, of) for label, bar, n, of in db.execute(
            "SELECT label, bar, bars, [of] FROM form WHERE song = ? AND level = 'part' ORDER BY idx", (sid,))]
        if not parts:
            out["no form"] += 1
            continue
        lines = [_beats_at(beats, t) for t in bars]
        s = Song(title, tonic, mode, meter,                  # the bars to the loop's end, a last sliver under a beat dropped
                 [(a, min(b, end)) for a, b in zip(lines, lines[1:] + [lines[-1] + meter]) if a < end - (1 - NEAR)],
                 chords, parts=parts, loop_bar=loop_bar, sid=sid, game=game_name or "")
        for role, evidence, blob in db.execute("SELECT role, evidence, notes FROM voices WHERE song = ?", (sid,)):
            if role in ROLES and not (evidence and '"roll"' in evidence):
                s.notes.setdefault(role, []).extend(
                    (st, length, m) for st, length, m, level, _, _ in store.unpack(blob)
                    if st < end and level > 0 and not math.isnan(m))
        songs.append(s)
    return songs, dict(out)


def of_composed(song: dict, v: vocab.Song, r) -> Song:
    """A composed song (against.read's vocab and rhythm songs) with its parts
    read by the form reader over its notes placed in time."""
    from . import measures
    s = measures.of_composed(song)
    spb = 60 / s.bpm
    notes = [SimpleNamespace(start=n.beat * spb, end=None if n.beats is None else (n.beat + n.beats) * spb, midi=n.midi,
                             level=n.level, voice=n.voice, sample=SimpleNamespace(key=str(n.voice))) for n in s.notes]
    f = form_mod.read(SimpleNamespace(notes=notes), SimpleNamespace(bar_times=[a * spb for a, _ in r.bars]))
    return Song(v.title, v.tonic, v.mode, 4, list(r.bars), v.chords, {k: v.notes[k] for k in ROLES if k in v.notes},
                [Part(p.label, p.bar, p.bars, p.of) for p in f.parts])


# --- progressions ---

def _bars(song: Song, part: Part) -> list[tuple[float, float]]:
    """A part's bars (start, end), those of a beat or more."""
    return [song.bars[i] for i in range(part.bar, min(part.bar + part.bars, len(song.bars))) if song.bars[i][1] - song.bars[i][0] >= 1 - NEAR]


def cells(song: Song, part: Part, level: str = "half bar") -> list[tuple[float, float]]:
    """A part's cells at a level: its beats, its half bars (a bar of three
    whole, or of another length than the meter), or its bars."""
    out = []
    for a, b in _bars(song, part):
        n = round(b - a) if level == "beat" else 2 if level == "half bar" and round(b - a) == song.meter and song.meter % 2 == 0 else 1
        out += [(a + k * (b - a) / n, a + (k + 1) * (b - a) / n) for k in range(n)]
    return out


def chord_in(chords: list, a: float, b: float) -> Span | None:
    """The fit chord sounding most of [a, b), the one sounding first at a tie."""
    best = None
    for c in chords:
        if c.end <= a or c.start >= b or c.root is None or c.fit < FIT:
            continue
        cover = min(c.end, b) - max(c.start, a)
        if best is None or cover > best[0] + 1e-9:
            best = (cover, c)
    return best[1] if best else None


def degree_of(song: Song, c: Span) -> str:
    return vocab.degree(vocab.numeral(c.root, song.tonic, song.mode, c.shape))


def sequence(song: Song, spans: list) -> list[str]:
    """The chords through some cells, by degree, runs of one merged."""
    out = []
    for a, b in spans:
        c = chord_in(song.chords, a, b)
        if c is not None and (not out or out[-1] != degree_of(song, c)):
            out.append(degree_of(song, c))
    return out


def cycle(seq: list) -> tuple:
    """The progression a sequence is built on: the shortest cycle it repeats
    (half of it heard again at least), else the whole."""
    for p in range(1, len(seq)):
        if len(seq) - p >= p / 2 and all(seq[i] == seq[i + p] for i in range(len(seq) - p)):
            return tuple(seq[:p])
    return tuple(seq)


def cadence(seq: list) -> str:
    """How a chord sequence ends (CADENCES)."""
    if not seq:
        return "elsewhere"
    if len(seq) == 1:
        return "one chord"
    a, b = seq[-2], seq[-1]
    if b == "I":
        return "V -> I" if a == "V" else "IV -> I" if a == "IV" else "bVII -> I" if a in SUBTONIC else "another -> I"
    return "half (on V)" if b == "V" else "elsewhere"


@dataclass
class Progressions:
    songs: int = 0
    parts: int = 0                                                        # parts seen
    counted: int = 0                                                      # new ones with a chord, counted
    built: dict = field(default_factory=lambda: defaultdict(Tally))       # mode -> cycle -> parts
    runs: dict = field(default_factory=lambda: defaultdict(Tally))        # mode -> three chords -> parts
    lengths: Counter = field(default_factory=Counter)                     # chords in the progression (SPANS)
    begins: Counter = field(default_factory=Counter)                      # the first chord
    ends: Counter = field(default_factory=Counter)                        # the last
    cadences: Counter = field(default_factory=Counter)
    loops: Counter = field(default_factory=Counter)                       # the loop's move (LOOPS)
    loops_on: Counter = field(default_factory=Counter)                    # the chord the loop lands on
    rates: list = field(default_factory=list)                             # (first bar, middle, last) chord changes a bar
    levels: Counter = field(default_factory=Counter)                      # moves at the beat / half bar / bar


def progressions(songs: list) -> Progressions:
    """The progressions by part over the songs (the module's account)."""
    p = Progressions(songs=len(songs))
    for s in songs:
        starts = [c.start for c in s.chords if c.root is not None and c.fit >= FIT]
        built, runs = [], []
        for part in s.parts:
            p.parts += 1
            if part.of is not None:
                continue
            seq = sequence(s, cells(s, part))
            if not seq:
                continue
            p.counted += 1
            prog = cycle(seq)
            built.append(prog)
            runs += [tuple(seq[i:i + 3]) for i in range(len(seq) - 2)]
            p.lengths[next(name for top, name in SPANS if len(prog) <= top)] += 1
            p.begins[seq[0]] += 1
            p.ends[seq[-1]] += 1
            p.cadences[cadence(seq)] += 1
            for level in ("beat", "half bar", "bar"):
                p.levels[level] += max(0, len(seq if level == "half bar" else sequence(s, cells(s, part, level))) - 1)
            bars = _bars(s, part)
            if len(bars) >= 3:
                changes = [bisect.bisect_left(starts, b - NEAR) - bisect.bisect_left(starts, a - NEAR) for a, b in bars]
                p.rates.append((changes[0], statistics.fmean(changes[1:-1]), changes[-1]))
        p.built[s.mode].add(built)
        p.runs[s.mode].add(runs)
        if s.loop_bar is not None and s.loop_bar < len(s.bars):
            last = sequence(s, cells(s, Part("", len(s.bars) - 1, 1)))
            first = sequence(s, cells(s, Part("", s.loop_bar, 1)))
            if last and first:
                p.loops["the same chord" if last[-1] == first[0] else cadence([last[-1], first[0]])] += 1
                p.loops_on[first[0]] += 1
    return p


# --- phrases ---

@dataclass
class Phrase:
    start: float                     # beats
    end: float
    line: list                       # (start, length, midi), the tune's notes
    source: str                      # melody, counter, or resting
    last_bar: float = 0.0            # where its last bar starts
    ends_part: bool = False
    last: bool = False               # the song's last phrase, before its loop

    @property
    def final(self) -> tuple:
        """The note the phrase ends on: the one held longest of its last
        bar's (the later at a tie), since the last notes of a phrase's bars
        are often the pickup into the next; its last note where none starts
        in the last bar."""
        held = [n for n in self.line if n[0] >= self.last_bar - NEAR]
        return max(held, key=lambda n: (n[1], n[0])) if held else self.line[-1]


def windows(song: Song, part: Part, length) -> list[tuple[int, int]]:
    """A part's phrases as bar ranges (first, past the last): the part, or
    `length` bars from its start, a leftover under half a phrase or a single
    bar joining the phrase before."""
    first, past = part.bar, min(part.bar + part.bars, len(song.bars))
    if past <= first:
        return []
    if length == "part":
        return [(first, past)]
    out = []
    for a in range(first, past, length):
        b = min(a + length, past)
        if out and (2 * (b - a) < length or b - a == 1):
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def tune(song: Song, a: float, b: float) -> tuple[list, str]:
    """The tune over [a, b): the melody's line, or the counter-line's where
    the melody rests; its notes' lengths the time to the next, to b."""
    for role in ROLES:
        notes = [n for n in song.notes.get(role, []) if a - NEAR <= n[0] < b - NEAR]
        line = _line(notes) if notes else []
        if len(line) >= MIN_NOTES:
            ends = [n[0] for n in line[1:]] + [b]
            return [(n[0], max(e - n[0], NEAR), n[2]) for n, e in zip(line, ends)], role
    return [], "resting"


def phrases(song: Song, length) -> list[Phrase]:
    """A song's phrases of one length, in order, with their tunes."""
    out = []
    for part in song.parts:
        ws = windows(song, part, length)
        for k, (i, j) in enumerate(ws):
            a, b = song.bars[i][0], song.bars[j - 1][1]
            line, source = tune(song, a, b)
            out.append(Phrase(a, b, line, source, song.bars[j - 1][0], ends_part=k == len(ws) - 1))
    if out:
        out[-1].last = song.loop_bar is not None
    return out


def contour(line: list, a: float, b: float) -> str:
    """The phrase's shape from the mean pitch of its thirds by time (CONTOURS)."""
    third = (b - a) / 3
    sums, weights = [0.0] * 3, [0.0] * 3
    for start, length, midi in line:
        for k in range(3):
            w = min(start + length, a + (k + 1) * third) - max(start, a + k * third)
            if w > 0:
                sums[k] += w * midi
                weights[k] += w
    means = [sums[k] / weights[k] if weights[k] else None for k in range(3)]
    for k in range(3):
        if means[k] is None:                          # an empty third takes its neighbour's
            means[k] = means[k - 1] if k else next(m for m in means if m is not None)
    x, y, z = means
    if y - max(x, z) >= LEVEL:
        return "arch"
    if min(x, z) - y >= LEVEL:
        return "valley"
    return "rising" if z - x >= LEVEL else "falling" if x - z >= LEVEL else "level"


def peak(line: list, a: float, b: float) -> str:
    """Where the first highest note falls (QUARTERS)."""
    top = max(line, key=lambda n: (n[2], -n[0]))
    return QUARTERS[min(3, int(4 * (top[0] - a) / (b - a)))]


def against_key(midi: float, song: Song) -> str:
    """A note's scale degree in the song's key (KEY_NAMES)."""
    d = DEGREE_OF[song.mode].get((round(midi) - song.tonic) % 12)
    return d if d in ("1", "3", "5") else "another degree" if d else "off the scale"


def against_chord(midi: float, at: float, song: Song) -> str:
    """Which of the chord's tones a note is (CHORD_NAMES), the chord the one read at its onset."""
    c = _chord_at(song.chords, at)
    if c is None or c.root is None or c.fit < FIT:
        return "no chord"
    t = tone_of(round(midi) % 12, c.root, c.shape)
    return t if t in ("root", "third", "fifth") else "another tone"


def relation(before, here: Phrase) -> str:
    """How a phrase stands to the one before (RELATIONS)."""
    if before is None or not before.line:
        return "first"
    cells_of = lambda p: {(round((n[0] - p.start) * 12), round(n[2])) for n in p.line}
    x, y = cells_of(before), cells_of(here)
    n = max(len(x), len(y))
    if len(x & y) >= SAME * n:
        return "repeated"
    at = defaultdict(set)
    for pos, m in x:
        at[pos].add(m)
    matched = lambda k: sum(1 for pos, m in y if any(abs(m - k - m0) <= 1 for m0 in at.get(pos, ())))
    best = max((k for k in range(-12, 13) if k), key=lambda k: (matched(k), -abs(k)))
    if matched(best) >= SAME * n:
        return "moved up" if best > 0 else "moved down"
    if len({pos for pos, _ in x} & {pos for pos, _ in y}) >= SAME * n:
        return "answered"
    return "new"


@dataclass
class Shapes:
    phrases: int = 0
    source: Counter = field(default_factory=Counter)                      # melody / counter / resting
    contour: Counter = field(default_factory=Counter)
    peak: Counter = field(default_factory=Counter)
    ranges: list = field(default_factory=list)
    starts_key: Counter = field(default_factory=Counter)
    starts_chord: Counter = field(default_factory=Counter)
    ends_key: Counter = field(default_factory=Counter)
    ends_chord: Counter = field(default_factory=Counter)
    part_ends: Counter = field(default_factory=Counter)                   # (ends a part, on the tonic) -> phrases
    song_ends: Counter = field(default_factory=Counter)                   # the last phrase's end degree
    relation: Counter = field(default_factory=Counter)


def shapes(songs: list, length) -> Shapes:
    """The melody's phrase shapes over the songs, at one phrase length."""
    out = Shapes()
    for s in songs:
        before = None
        for ph in phrases(s, length):
            out.phrases += 1
            out.source[ph.source] += 1
            if not ph.line:
                continue
            out.contour[contour(ph.line, ph.start, ph.end)] += 1
            out.peak[peak(ph.line, ph.start, ph.end)] += 1
            pitches = [n[2] for n in ph.line]
            out.ranges.append(round(max(pitches) - min(pitches)))
            first, last = ph.line[0], ph.final
            out.starts_key[against_key(first[2], s)] += 1
            out.starts_chord[against_chord(first[2], first[0], s)] += 1
            end_key = against_key(last[2], s)
            out.ends_key[end_key] += 1
            out.ends_chord[against_chord(last[2], last[0], s)] += 1
            out.part_ends[ph.ends_part, end_key == "1"] += 1
            if ph.last:
                out.song_ends[end_key] += 1
            out.relation[relation(before, ph)] += 1
            before = ph
    return out


# --- the phrases as a table's units (phase 3, item 6) ---

REPEATS = ((1 / 3, "varied"), (2 / 3, "mixed"), (2, "repeating"))   # a song's share of phrases repeating or moving the one before
YES_NO = {True: "yes", False: "no"}


def _place(k: int, n: int) -> str:
    return "only" if n == 1 else "first" if k == 0 else "last" if k == n - 1 else "middle"


def phrase_rows(songs: list, length=4) -> list[list[dict]]:
    """Each song's phrases with a tune, at one length, as rows of what the
    tables take: the contour, the peak's quarter, the relation to the
    phrase before, the end note against the key (KEY_NAMES), whether the
    phrase ends its part and whether it is the song's last, its place in
    its part and its part's place in the form, its source (melody or
    counter-line), the mode, and the song's habit (REPEATS)."""
    out = []
    for s in songs:
        rows, before = [], None
        for pi, part in enumerate(s.parts):
            ws = windows(s, part, length)
            for k, (i, j) in enumerate(ws):
                a, b = s.bars[i][0], s.bars[j - 1][1]
                line, source = tune(s, a, b)
                if not line:
                    continue
                ph = Phrase(a, b, line, source, s.bars[j - 1][0], ends_part=k == len(ws) - 1)
                rows.append({"contour": contour(line, a, b), "peak": peak(line, a, b), "relation": relation(before, ph),
                             "ending": against_key(ph.final[2], s), "ends_part": YES_NO[ph.ends_part],
                             "place": _place(k, len(ws)), "form": _place(pi, len(s.parts)), "source": source,
                             "mode": s.mode, "last": "no"})
                before = ph
        if rows:
            if s.loop_bar is not None:
                rows[-1]["last"] = "yes"
            share = sum(1 for r in rows if r["relation"] in ("repeated", "moved up", "moved down")) / len(rows)
            habit = habit_of(share, REPEATS)
            for r in rows:
                r["habit"] = habit
            out.append((s, rows))
    return out


def _phrase_units(songs, outcome: str, length) -> list:
    out = []
    for s, rows in phrase_rows(songs, length):
        previous = START
        for r in rows:
            if outcome == "relation" and r["relation"] == "first":
                continue                              # the song's first phrase stands to nothing: no choice to count
            values = {"part": R.MELODY, "previous": previous}
            values.update((k, v) for k, v in r.items() if k != outcome)
            out.append(tables.Unit(s.sid, s.game, r[outcome], values))
            previous = r[outcome]
    return out


def contour_units(songs, length=4) -> list:
    """Each phrase as a unit, its outcome its contour (CONTOURS); the other
    rows' names its values, and the phrase before's contour."""
    return _phrase_units(songs, "contour", length)


def relation_units(songs, length=4) -> list:
    """Each phrase as a unit, its outcome how it stands to the phrase before (RELATIONS)."""
    return _phrase_units(songs, "relation", length)


def ending_units(songs, length=4) -> list:
    """Each phrase as a unit, its outcome the note it ends on against the key (KEY_NAMES)."""
    return _phrase_units(songs, "ending", length)


def peak_units(songs, length=4) -> list:
    """Each phrase as a unit, its outcome where its first highest note falls (QUARTERS)."""
    return _phrase_units(songs, "peak", length)


# --- the melody's moves as a table's units (phase 4, the melody slice) ---

LEAP = 12                            # semitones: a move beyond an octave either way is one outcome ("+13" / "-13")
STEPS = ((0.5, "leaping"), (0.75, "mixed"), (2, "stepwise"))   # a song's share of melody moves that are steps or repeats (2 semitones or less)
STRONG = {"beat": "strong", "eighth": "weak", "sixteenth": "weak", "triplet": "weak", "finer": "weak"}


def move_units(songs: list, length=4) -> list:
    """Each move of the tune, note to note within a phrase, as a table's
    unit: its outcome the interval in semitones, signed, beyond an octave
    folded to LEAP + 1 ("+13", "-13"); its values the part (melody), the
    mode, where the arriving note falls in its beat (STRONG: on the beat
    or off it), the tone the note left stands on against the chord
    (CHORD_NAMES), the phrase's contour (CONTOURS) and the quarter of the
    phrase the move lands in (QUARTERS), the move before (START at the
    phrase's first move), and the song's habit (STEPS: how stepwise its
    tune is, drawn once a song)."""
    from .rhythm import START, habit_of, place as place_of, position
    out = []
    for s in songs:
        mine = []
        for ph in phrases(s, length):
            if len(ph.line) < 2:
                continue
            shape = contour(ph.line, ph.start, ph.end)
            previous = START
            for a, b in zip(ph.line, ph.line[1:]):
                move = round(b[2]) - round(a[2])
                move = max(-LEAP - 1, min(LEAP + 1, move))
                outcome = f"{move:+d}" if move else "0"
                beat_pos = position(b[0] - math.floor(b[0]), 12)
                quarter = QUARTERS[min(3, int(4 * (b[0] - ph.start) / (ph.end - ph.start)))]
                mine.append(tables.Unit(s.sid, s.game, outcome, {
                    "part": R.MELODY, "mode": s.mode, "place": STRONG[place_of(beat_pos)], "tone": against_chord(a[2], a[0], s),
                    "contour": shape, "quarter": quarter, "previous": previous}))
                previous = outcome
        if mine:
            steps = sum(1 for u in mine if abs(int(u.outcome)) <= 2) / len(mine)
            habit = habit_of(steps, STEPS)
            for u in mine:
                u.values["habit"] = habit
            out += mine
    return out


def step_habit_units(songs: list, length=4) -> list:
    """Each song's stepwise habit for its tune (STEPS), one unit a song, the tempo band beside."""
    from .rhythm import band, habits
    units = move_units(songs, length)
    for u in units:
        u.values["tempo"] = band(next((s.bpm for s in songs if s.sid == u.song), 120.0)) if hasattr(songs[0], "bpm") else "medium"
    return habits(units)


# --- reports ---

def _band(x: float) -> str:
    return next(name for top, name in RANGES if x < top)


def report(songs: list, left_out: dict, top: int = 10, game: str = "") -> str:
    """Both tables as text: the progressions by part, then the phrases at each length."""
    total = len(songs) + sum(left_out.values())
    head = f"progressions and phrases of {game + ': ' if game else ''}{len(songs)} songs"
    out = [head + (f" of {total} (" + ", ".join(f"{n} {why}" for why, n in left_out.items()) + ")" if left_out else "")]
    p = progressions(songs)
    out.append(f"\nprogressions by part (the half bar's fit chord, by degree; {p.counted} parts counted of {p.parts},"
               f" the rest repeats of an earlier part or without a chord)")
    out.append("  chord moves within the parts at the beat / the half bar / the bar: "
               + " / ".join(f"{p.levels[k]}" for k in ("beat", "half bar", "bar"))
               + f" (the half bar keeps {_pct(p.levels['half bar'], p.levels['beat']).strip()} of the beat's, the bar"
               f" {_pct(p.levels['bar'], p.levels['beat']).strip()})")
    out.append("  built on " + ", ".join(f"{name} {_pct(p.lengths[name], p.counted).strip()}" for _, name in SPANS))
    for mode in ("major", "minor"):
        t = p.built.get(mode)
        if t:
            n = sum(t.values())
            out.append(f"  {mode} keys ({n} parts in {sum(1 for s in songs if s.mode == mode)} songs; the cycle a part repeats, or its whole)")
            out += [f"    {' '.join(k)[:40]:40s} {_pct(c, n)}  {c:4d} parts {t.songs[k]:3d} songs" for k, c in t.most_common(top)]
    for mode in ("major", "minor"):
        t = p.runs.get(mode)
        if t:
            n = sum(t.values())
            out.append(f"  three-chord runs, {mode} ({n}): " + ", ".join(f"{' '.join(k)} {_pct(c, n).strip()}" for k, c in t.most_common(top)))
    out.append("  a part begins on: " + ", ".join(f"{k} {_pct(c, p.counted).strip()}" for k, c in p.begins.most_common(8)))
    out.append("  a part ends on: " + ", ".join(f"{k} {_pct(c, p.counted).strip()}" for k, c in p.ends.most_common(8)))
    out.append("  its cadence: " + ", ".join(f"{k} {_pct(p.cadences[k], p.counted).strip()}" for k in CADENCES))
    n = sum(p.loops.values())
    out.append(f"  the song loops back ({n} songs with a loop and a chord at both ends): "
               + ", ".join(f"{k} {_pct(p.loops[k], n).strip()}" for k in LOOPS if p.loops[k])
               + "; onto " + ", ".join(f"{k} {_pct(c, n).strip()}" for k, c in p.loops_on.most_common(5)))
    if p.rates:
        up = sum(1 for _, m, z in p.rates if z > m)
        down = sum(1 for _, m, z in p.rates if z < m)
        out.append(f"  chord changes a bar through a part ({len(p.rates)} parts of three bars or more): its first bar"
                   f" {_median([a for a, _, _ in p.rates])}, middle bars {_median([m for _, m, _ in p.rates])}, last bar"
                   f" {_median([z for _, _, z in p.rates])}; the last bar changes more than the middle in {_pct(up, len(p.rates)).strip()}"
                   f" of parts, less in {_pct(down, len(p.rates)).strip()}")
    out.append("\nthe melody's phrases (the melody voice's line, or the counter-line's where it rests)")
    cols = {length: shapes(songs, length) for length in LENGTHS}
    names = {"part": "the part", 4: "4 bars", 2: "2 bars"}
    out.append(f"  {'':44s}" + "".join(f" {names[k]:>14s}" for k in LENGTHS))
    row = lambda label, cell: out.append(f"  {label:44s}" + "".join(f" {cell(cols[k]):>14s}" for k in LENGTHS))
    row("phrases", lambda c: str(c.phrases))
    for src, label in ((R.MELODY, "from the melody"), (R.COUNTER, "from the counter-line"), ("resting", "resting (left out)")):
        row(label, lambda c, src=src: _pct(c.source[src], c.phrases))
    for name in CONTOURS:
        row(f"contour: {name}", lambda c, name=name: _pct(c.contour[name], sum(c.contour.values())))
    for name in QUARTERS:
        row(f"the peak in the {name}", lambda c, name=name: _pct(c.peak[name], sum(c.peak.values())))
    row("range (semitones)", lambda c: _median(c.ranges))
    for _, name in RANGES:
        row(f"  {name}", lambda c, name=name: _pct(sum(1 for x in c.ranges if _band(x) == name), len(c.ranges)))
    for what, key in (("starts", "starts_key"), ("ends", "ends_key")):
        for name in KEY_NAMES:
            row(f"{what} on the key's {name}", lambda c, name=name, key=key: _pct(getattr(c, key)[name], sum(getattr(c, key).values())))
    for what, key in (("starts", "starts_chord"), ("ends", "ends_chord")):
        for name in CHORD_NAMES:
            row(f"{what} on the chord's {name}", lambda c, name=name, key=key: _pct(getattr(c, key)[name], sum(getattr(c, key).values())))
    row("a phrase ending a part ends on the tonic", lambda c: _pct(c.part_ends[True, True], c.part_ends[True, True] + c.part_ends[True, False]))
    row("  one inside a part", lambda c: _pct(c.part_ends[False, True], c.part_ends[False, True] + c.part_ends[False, False]))
    row("the song's last phrase, before its loop", lambda c: _pct(c.song_ends["1"], sum(c.song_ends.values())))
    for name in RELATIONS:
        row(f"against the one before: {name}", lambda c, name=name: _pct(c.relation[name], sum(c.relation.values())))
    return "\n".join(out)


def rows(songs: list) -> dict:
    """The counts as against.py's columns: section -> [(row, cell, rank)]."""
    out = defaultdict(list)
    p = progressions(songs)
    sec = "progressions by part (the half bar's chord by degree)"
    out[sec] += [("parts counted / seen", f"{p.counted} / {p.parts}", None),
                 ("moves kept at the half bar, of the beat's", _pct(p.levels["half bar"], p.levels["beat"]).strip(), None)]
    out[sec] += [(f"built on {name}", _pct(p.lengths[name], p.counted).strip(), None) for _, name in SPANS]
    for mode in ("major", "minor"):
        t = p.built.get(mode, Tally())
        out[f"progressions, {mode} keys (parts, songs)"] += [(" ".join(k), f"{_pct(c, sum(t.values())).strip()} ({t.songs[k]})", c)
                                                             for k, c in t.items()]
    out["a part begins on"] += [(k, _pct(c, p.counted).strip(), c) for k, c in p.begins.items()]
    out["a part ends on"] += [(k, _pct(c, p.counted).strip(), c) for k, c in p.ends.items()]
    out["a part's cadence"] += [(k, _pct(p.cadences[k], p.counted).strip(), None) for k in CADENCES]
    n = sum(p.loops.values())
    out["the song loops back (songs with a loop)"] += [(k, _pct(p.loops[k], n).strip(), None) for k in LOOPS]
    if p.rates:
        out["chord changes a bar through a part"] += [
            ("first bar / middle / last", " / ".join(f"{statistics.median([r[i] for r in p.rates]):.3g}" for i in range(3)), None),
            ("the last bar changes more than the middle", _pct(sum(1 for _, m, z in p.rates if z > m), len(p.rates)).strip(), None)]
    for length in (4, "part"):
        c = shapes(songs, length)
        sec = f"the melody's phrases of {'four bars' if length == 4 else 'a part'}"
        out[sec] += [("phrases: from the melody / the counter-line / resting",
                      f"{c.phrases}: {_pct(c.source[R.MELODY], c.phrases).strip()} / {_pct(c.source[R.COUNTER], c.phrases).strip()}"
                      f" / {_pct(c.source['resting'], c.phrases).strip()}", None)]
        out[sec] += [(f"contour: {k}", _pct(c.contour[k], sum(c.contour.values())).strip(), None) for k in CONTOURS]
        out[sec] += [(f"the peak in the {k}", _pct(c.peak[k], sum(c.peak.values())).strip(), None) for k in QUARTERS]
        out[sec] += [("range (semitones)", _median(c.ranges), None)]
        out[sec] += [(f"starts on the key's {k}", _pct(c.starts_key[k], sum(c.starts_key.values())).strip(), None) for k in KEY_NAMES[:3]]
        out[sec] += [(f"ends on the key's {k}", _pct(c.ends_key[k], sum(c.ends_key.values())).strip(), None) for k in KEY_NAMES[:3]]
        out[sec] += [(f"ends on the chord's {k}", _pct(c.ends_chord[k], sum(c.ends_chord.values())).strip(), None) for k in CHORD_NAMES[:3]]
        out[sec] += [("a phrase ending a part ends on the tonic",
                      _pct(c.part_ends[True, True], c.part_ends[True, True] + c.part_ends[True, False]).strip(), None)]
        out[sec] += [(f"against the one before: {k}", _pct(c.relation[k], sum(c.relation.values())).strip(), None) for k in RELATIONS]
    return dict(out)


# --- the games ---

HEADS = (("parts", "parts", "n"), ("short", "<=4 chords", "%"), ("begin_i", "begins I", "%"), ("end_i", "ends I", "%"),
         ("v_i", "V->I", "%"), ("iv_i", "IV->I", "%"), ("vii_i", "bVII->I", "%"), ("half", "half", "%"),
         ("loop_i", "loops to I", "%"), ("faster", "faster end", "%"), ("arch", "arch", "%"), ("rising", "rising", "%"),
         ("falling", "falling", "%"), ("level", "level", "%"), ("peak_late", "peak late", "%"), ("range", "range", "n"),
         ("tonic_end", "part ends 1", "%"), ("repeated", "repeated", "%"), ("moved", "moved", "%"), ("answered", "answered", "%"),
         ("new", "new", "%"))
LABELS = {k: label for k, label, _ in HEADS}
KINDS = {k: kind for k, _, kind in HEADS}
HABITS = {k: kind for k, kind in KINDS.items() if k != "parts"}   # the numbers whose spread is read (a count is no habit)


def _share(n, total) -> float:
    return 100.0 * n / total if total else 0.0


def headline(songs: list) -> dict:
    """A game's headline numbers: the progressions' and the four-bar phrases'."""
    p, c = progressions(songs), shapes(songs, 4)
    n = p.counted
    out = {"parts": float(n), "short": _share(p.lengths["one chord"] + p.lengths["2 to 4 chords"], n),
           "begin_i": _share(p.begins["I"], n), "end_i": _share(p.ends["I"], n),
           "v_i": _share(p.cadences["V -> I"], n), "iv_i": _share(p.cadences["IV -> I"], n),
           "vii_i": _share(p.cadences["bVII -> I"], n), "half": _share(p.cadences["half (on V)"], n),
           "loop_i": _share(p.loops_on["I"], sum(p.loops.values())),
           "faster": _share(sum(1 for _, m, z in p.rates if z > m), len(p.rates))}
    shaped = sum(c.contour.values())
    for k in ("arch", "rising", "falling", "level"):
        out[k] = _share(c.contour[k], shaped)
    out["peak_late"] = _share(c.peak["third"] + c.peak["last"], shaped)
    out["range"] = float(statistics.median(c.ranges)) if c.ranges else 0.0
    out["tonic_end"] = _share(c.part_ends[True, True], c.part_ends[True, True] + c.part_ends[True, False])
    rel = sum(c.relation.values()) - c.relation["first"]
    out["repeated"] = _share(c.relation["repeated"], rel)
    out["moved"] = _share(c.relation["moved up"] + c.relation["moved down"], rel)
    out["answered"] = _share(c.relation["answered"], rel)
    out["new"] = _share(c.relation["new"], rel)
    return out


@dataclass
class Game:
    name: str
    composer: str = ""
    driver: str = ""
    counted: int = 0
    total: int = 0
    numbers: dict = field(default_factory=dict)


def games(db) -> list[Game]:
    """Each game's headline numbers over the database."""
    out = []
    for name, composer, driver, total in db.execute("SELECT game, composer, driver, COUNT(*) FROM songs GROUP BY game ORDER BY game"):
        songs, _ = load(db, name)
        g = Game(name, composer or "", driver or "", len(songs), total)
        if songs:
            g.numbers = headline(songs)
        out.append(g)
    return out


def _cell(key: str, x: float) -> str:
    return f"{x:.1f}" if key == "range" else f"{x:.0f}"


def games_report(table: list[Game], shuffles: int = 200) -> str:
    """The per-game table, each number's spread and what the driver and the composer explain (games.py's way)."""
    from . import games as games_mod
    out = [f"{len(table)} games, {sum(g.counted for g in table)} songs with a form counted of {sum(g.total for g in table)}",
           f"\n{'game':24s} {'songs':>7s}" + "".join(f" {LABELS[k]:>{max(5, len(LABELS[k]))}s}" for k in LABELS)]
    for g in table:
        out.append(f"{g.name[:24]:24s} {g.counted:3d}/{g.total:<3d}"
                   + "".join(f" {_cell(k, g.numbers[k]) if g.numbers else '-':>{max(5, len(LABELS[k]))}s}" for k in LABELS))
    out.append("parts: new parts counted; <=4 chords: built on a progression of four chords or fewer; half: a half cadence;"
               " faster end: the last bar changes chord more than the middle bars; the phrase columns are four-bar phrases:"
               " peak late, in the second half; part ends 1, a phrase ending a part ends on the tonic; repeated to new, against the one before")
    out.append(f"\nspread over the games (each game once; the middle half's width against the median, or a floor:"
               f" shared under {games_mod.SHARED:g}, a game's own over {games_mod.OWN:g})")
    out.append(f"  {'number':12s} {'median':>7s} {'middle half':>14s} {'spread':>6s}  verdict  lowest / highest")
    for key, med, q1, q3, lo, hi, width, verdict in games_mod.spread(table, HABITS):
        out.append(f"  {LABELS[key]:12s} {_cell(key, med):>7s} {_cell(key, q1):>6s} - {_cell(key, q3):<6s} {width:6.2f}  {verdict:7s}"
                   f"  {lo[1]} ({_cell(key, lo[0])}) / {hi[1]} ({_cell(key, hi[0])})")
    groupings = (("driver", lambda g: g.driver), ("composer", games_mod.composer_of))
    exp = {name: games_mod.explained(table, by, shuffles, keys=HABITS) for name, by in groupings}
    out.append(f"\nexplained by the driver and by the first-listed composer (eta squared over the games sharing one,"
               f" against the median of {shuffles} shufflings; * where it stands {games_mod.MARGIN:g} over)")
    out.append(f"  {'number':12s}" + "".join(f" {name:>18s}" for name in exp))
    for key in HABITS:
        marks = []
        for name, e in exp.items():
            if key in e:
                eta, chance, _, _ = e[key]
                marks.append(f"{eta:.2f} ({chance:.2f}){'*' if eta - chance >= games_mod.MARGIN else ' '}")
            else:
                marks.append("-")
        out.append(f"  {LABELS[key]:12s}" + "".join(f" {c:>18s}" for c in marks))
    return "\n".join(out)


# --- the owner's ears ---

def marked(path: str) -> dict:
    """The parts marked by ear (heard-form.json): (file name, level) ->
    {"folder", "parts": [(label, seconds)], "over": the time the song starts
    over, or None}. Set 1's marks are bars on the bar lines read at the
    time, turned to seconds on those; set 2's are in seconds; set 1b's,
    marked again at the scale of sections, are the section level; a song
    whose parts were marked unsure is left out."""
    with open(path) as fh:
        heard_ = json.load(fh)
    out = {}
    for key, h in heard_.items():
        if key == "_about" or h.get("parts_unsure"):
            continue
        folder, file = key.split(":", 1)[-1].split("/", 1)
        if "marks_s" in h:
            parts, over = [(l, t) for l, t in h["marks_s"]], h.get("starts_over_s")
        else:
            at = lambda b: h["bar_times"][min(b, len(h["bar_times"])) - 1]
            parts, over = [(l, at(b)) for l, b in h["marks"]], at(h["starts_over"])
        out[file, "section" if key.startswith("again:") else "part"] = {"folder": folder, "parts": parts, "over": over}
    return out


def heard(db, path: str) -> tuple[list[str], list[Song], list[Song]]:
    """The form reader's parts against the marked ones in the songs the
    database has: lines of agreement per song and in all (a start agreeing
    within AGREE bars, over the first pass, the song's own start left out),
    the marked songs as loaded, and the same with the marked parts in place
    of the read ones (the loop kept the reader's)."""
    lines, read_songs, marked_songs = [], [], []
    tot = defaultdict(lambda: [0, 0, 0])
    for (file, level), h in marked(path).items():
        found = db.execute("SELECT id, folder FROM songs WHERE file = ?", (file,)).fetchall()
        if not found:
            continue
        sid = next((r[0] for r in found if r[1] == h["folder"]), found[0][0])
        row = db.execute("SELECT bars FROM beats WHERE song = ?", (sid,)).fetchone()
        if not row:
            lines.append(f"{file[:-4][:30]:30s} {level:7s} free time")
            continue
        bars = array("d")
        bars.frombytes(row[0])
        bar = (bars[-1] - bars[0]) / (len(bars) - 1)
        loop = db.execute("SELECT loop_bar, loop_seconds FROM songs WHERE id = ?", (sid,)).fetchone()
        mine_over = bars[loop[0]] + loop[1] if loop[0] is not None and loop[1] else None
        over = h["over"] if h["over"] is not None else mine_over if mine_over is not None else math.inf
        theirs = [t for _, t in h["parts"] if bars[0] + bar < t < over - 0.5 * bar]
        read = [t for (t,) in db.execute("SELECT start FROM form WHERE song = ? AND level = ? ORDER BY idx", (sid, level))
                if bars[0] + bar < t < over - 0.5 * bar]
        hit = sum(1 for t in theirs if any(abs(t - m) <= AGREE * bar for m in read))
        for i, x in enumerate((hit, len(theirs), len(read))):
            tot[level][i] += x
        lines.append(f"{file[:-4][:30]:30s} {level:7s} {hit} of {len(theirs)} marked starts read, {len(read)} read"
                     + ("" if mine_over is None or h["over"] is None else f"; starts over at {mine_over:.1f} s, marked {h['over']:.1f}"))
        songs, _ = load(db, song=sid) if level == "part" else ([], {})
        if not songs:
            continue
        s = songs[0]
        read_songs.append(s)
        starts = []
        for label, t in h["parts"]:
            if t >= over - 0.5 * bar:
                break
            i = bisect.bisect_left(bars, t - 0.5 * bar)
            if i < len(s.bars) and (not starts or i > starts[-1][1]):
                starts.append((label, i))
        if not starts or starts[0][1] != 0:
            starts.insert(0, (starts[0][0] if starts else "A", 0))
        parts = [Part(label, i, max(1, (starts[k + 1][1] if k + 1 < len(starts) else len(s.bars)) - i),
                      next((m for m, (l, _) in enumerate(starts[:k]) if l == label), None))
                 for k, (label, i) in enumerate(starts)]
        marked_songs.append(Song(s.title, s.tonic, s.mode, s.meter, s.bars, s.chords, s.notes, parts, s.loop_bar))
    for level, (hit, theirs, read) in tot.items():
        lines.append(f"{level}s: {hit} of {theirs} marked starts read (recall {hit / theirs:.2f}), {read} read (precision {hit / read:.2f})"
                     if theirs and read else f"{level}s: none")
    return lines, read_songs, marked_songs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bitcomposer.translate.phrases", description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", help="the readings database (default: ~/.local/share/bitcomposer/readings.db)")
    ap.add_argument("--game", help="only this game's songs (the songs table's game)")
    ap.add_argument("--top", type=int, default=10, help="rows of each progressions table (default 10)")
    ap.add_argument("--games", action="store_true", help="each game's headline numbers, their spread and what explains them")
    ap.add_argument("--against", action="append", default=[], metavar="PACK", help="a pack's name or a pack.json: songs composed with it beside")
    ap.add_argument("--songs", type=int, default=20, help="songs composed for each pack (default 20)")
    ap.add_argument("--heard", metavar="JSON", help="parts marked by ear (heard-form.json): the reader's parts scored, the marked songs counted both ways")
    args = ap.parse_args(argv)
    db = store.connect(args.db)
    songs, left_out = load(db, args.game)
    if not songs and not args.games:
        print("bitcomposer.translate.phrases: no songs on a beat with a key and a form to count", file=sys.stderr)
        return 1
    names = [g for g, in db.execute("SELECT DISTINCT game FROM songs")]
    game = args.game or (names[0] if len(names) == 1 else "")
    if songs:
        print(report(songs, left_out, args.top, game))
    if args.games:
        print()
        print(games_report(games(db)))
    if args.against:
        from . import against
        columns = {game or "the games": rows(songs)}
        for pack in args.against:
            name, composed = against.compose(pack, args.songs)
            ps = [of_composed(c, *against.read(c)[:2]) for c in composed]
            columns[name] = rows(ps)
            columns[name]["progressions by part (the half bar's chord by degree)"].insert(0, (
                "parts read / sections in the generator's plan",
                f"{sum(len(p.parts) for p in ps)} / {sum(len(c['info']['structure']) for c in composed)}", None))
        print()
        print(against.table(columns, args.top))
    if args.heard:
        lines, read_songs, marked_songs = heard(db, args.heard)
        print("\nthe form reader's parts against those marked by ear (" + os.path.basename(args.heard) + ")")
        print("\n".join("  " + line for line in lines))
        if read_songs:
            print(f"  the {len(read_songs)} marked songs counted on the reader's parts and on the marked ones:")
            print(f"  {'':8s}" + "".join(f" {LABELS[k]:>11s}" for k in LABELS))
            for name, nums in (("read", headline(read_songs)), ("marked", headline(marked_songs))):
                print(f"  {name:8s}" + "".join(f" {_cell(k, nums[k]):>11s}" for k in LABELS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
