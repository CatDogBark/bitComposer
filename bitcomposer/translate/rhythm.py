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
import argparse
import bisect
import math
import statistics
import sys
from array import array
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from fractions import Fraction

from . import drums as drums_mod, roles as R, store, tables
from .vocab import FIT, Span, _beats_at, _median, _pct, tone_of

NEAR = 0.06                          # beats: onsets this close are one, and this close to an eighth is on it
PARTS = (R.BASS, R.HARMONY, R.ACCOMP, R.ARP, R.COUNTER, R.MELODY, R.DRUMS)
PITCHED = PARTS[:-1]
DENSE = 6                            # hits a bar a drum sound plays, where it plays, to be the hat
PIECES = ("kick", "snare", "hat", "tom", "cymbal", "other")     # drums.PIECES; a sample named "none" is no drum
LETTERS = dict(zip(PIECES, "KShtco"))
SHORT = 0.75                         # a melody note sounding less of its length than this is detached
TONE_MARKS = {"root": "R", "third": "3", "sus": "s", "fifth": "5", "seventh": "7", "other": "+"}
SIZES = ((0, "repeat"), (2, "step"), (4, "third"), (5, "fourth"), (6, "tritone"), (7, "fifth"), (9, "sixth"),
         (11, "seventh"), (12, "octave"), (1e9, "more"))
VALUES = ((Fraction(1, 4), "a sixteenth"), (Fraction(1, 3), "a triplet eighth"), (Fraction(1, 2), "an eighth"),
          (Fraction(2, 3), "two triplet eighths"), (Fraction(3, 4), "a dotted eighth"), (Fraction(1), "a beat"),
          (Fraction(3, 2), "a beat and a half"), (Fraction(2), "two beats"), (Fraction(3), "three beats"),
          (Fraction(4), "four beats"), (Fraction(1e9), "longer"))
PLACES = ("beat", "eighth", "sixteenth", "triplet", "finer")
REST = "(rest)"
BANDS = ((85, "slow"), (130, "medium"), (1e9, "fast"))    # BPM: the readings' songs' tertiles (1562 songs, 2026-10-21)
START = "start"                      # the previous bar's pattern where there is none: the part's first bar, or after a gap


class Tally(Counter):
    """Bars by pattern, and in how many songs each pattern is heard."""

    def __init__(self):
        super().__init__()
        self.songs = Counter()

    def add(self, keys) -> None:
        """A song's bars' patterns."""
        self.update(keys)
        self.songs.update(set(keys))


@dataclass
class Song:
    """What a song's reading gives the counts: its meter, its grid's division,
    its bars (start, end in beats, once through), its chord spans and its
    notes by part (start, length, midi, sample key; in beats)."""
    title: str
    meter: int
    division: int
    bars: list
    chords: list
    notes: dict = field(default_factory=dict)   # role -> [(start, length, midi, sample), ...]
    rolls: dict = field(default_factory=dict)   # role -> notes of its roll voices, left out of the patterns
    bpm: float = 120.0                          # its tempo: how long a drum is held, in seconds
    sid: str = ""                               # its id in the readings
    game: str = ""
    numbers: list = field(default_factory=list)   # each bar's number in the reading (form's bars count them), beside `bars`
    parts: list = field(default_factory=list)     # the form's parts: (first bar number, bars)
    pieces: dict = field(default_factory=dict)    # sample key -> the piece the reading named it (drums.PIECES, "none")


def load(db, game: str | None = None) -> tuple[list[Song], dict]:
    """The songs to count (game: only that game's), and why the others were
    left out: {"free time": n, "mostly silent": n}; the harmony counts' songs."""
    songs, out = [], Counter()
    where, args = ("WHERE game = ?", (game,)) if game else ("", ())
    for sid, title, meter, division, seconds, loop_bar, loop_seconds, bpm, game_name in db.execute(
            f"SELECT id, title, meter, division, seconds, loop_bar, loop_seconds, bpm, game FROM songs {where}", args):
        row = db.execute("SELECT beats, bars FROM beats WHERE song = ?", (sid,)).fetchone()
        if division is None or not row:
            out["free time"] += 1
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
            out["mostly silent"] += 1
            continue
        lines = [b for b in (_beats_at(beats, t) for t in bars) if b < end]
        ends = lines[1:] + [lines[-1] + meter] if lines else []
        kept = [(k, a, min(b, end)) for k, (a, b) in enumerate(zip(lines, ends)) if min(b, end) - a >= 1 - NEAR]
        song = Song(title, meter, division, [(a, b) for _, a, b in kept], chords, bpm=bpm or 120.0, sid=sid,
                    game=game_name or "", numbers=[k for k, _, _ in kept],
                    parts=[(bar, n) for bar, n in db.execute(
                        "SELECT bar, bars FROM form WHERE song = ? AND level = 'part' ORDER BY bar", (sid,))])
        keys, song.pieces = {}, {}
        for idx, key, piece in db.execute("SELECT idx, key, piece FROM samples WHERE song = ?", (sid,)):
            keys[idx] = key
            song.pieces[key] = piece
        for role, evidence, blob in db.execute("SELECT role, evidence, notes FROM voices WHERE song = ?", (sid,)):
            if role in PARTS:
                into = song.rolls if evidence and '"roll"' in evidence else song.notes
                into.setdefault(role, []).extend(
                    (s, length, m, keys.get(int(i), "noise")) for s, length, m, level, _, i in store.unpack(blob)
                    if s < end and level > 0 and (role == R.DRUMS or not math.isnan(m)))
        songs.append(song)
    return songs, dict(out)


def position(offset: float, division: int) -> Fraction:
    """An onset's place in its bar, beats from the bar line, on the grid."""
    return Fraction(round(offset * division), division)


def place(p: Fraction) -> str:
    """Where a position falls (PLACES): on the beat, an eighth, a sixteenth, a triplet, or finer."""
    f = p - math.floor(p)
    return ("beat" if f == 0 else "eighth" if f.denominator == 2 else "sixteenth" if f.denominator == 4
            else "triplet" if f.denominator in (3, 6) else "finer")


def draw(positions, beats: int, marks: dict | None = None) -> str:
    """A bar's positions as text, four characters a beat: x on a quarter of
    the beat, t on a third, ~ finer than either, at the nearest; a position
    in `marks` draws as its mark instead. Nothing struck: REST."""
    cells = [["."] * 4 for _ in range(beats)]
    rank = {".": 0, "~": 1, "t": 2, "x": 3}
    for p in positions:
        b = math.floor(p)
        f = p - b
        if b >= beats:
            continue
        mark = "x" if f.denominator in (1, 2, 4) else "t" if f.denominator in (3, 6) else "~"
        i = min(3, round(f * 4))
        if rank[mark] > rank.get(cells[b][i], 3):
            cells[b][i] = (marks or {}).get(p, mark)
    return " ".join("".join(c) for c in cells) if positions else REST


def band(bpm: float) -> str:
    """The tempo band a tempo is in (BANDS)."""
    return next(name for top, name in BANDS if bpm < top)


def pattern(positions) -> str:
    """A bar's onset positions as a table's outcome: fractions of a beat
    from the bar line, space-separated; a bar rested through is "-"."""
    return " ".join(str(p) for p in positions) or "-"


def onsets(notes, start: float, end: float) -> list:
    """The notes struck in [start, end), grouped by onset: [(beat, [notes])],
    notes within NEAR of each other one onset at the first's time."""
    out = []
    for n in sorted(n for n in notes if start - NEAR <= n[0] < end - NEAR):
        if out and n[0] - out[-1][0] < NEAR:
            out[-1][1].append(n)
        else:
            out.append((n[0], [n]))
    return out


def bars_of(song: Song, role: str):
    """Each bar of the song's meter with the part's onsets in it: (the bar's
    start, [(position, [notes])])."""
    for _, a, struck in numbered_bars_of(song, role):
        yield a, struck


def numbered_bars_of(song: Song, role: str):
    """bars_of with each bar's number in the reading first: (number, start, [(position, [notes])])."""
    notes = song.notes.get(role, [])
    numbers = song.numbers or range(len(song.bars))
    for k, (a, b) in zip(numbers, song.bars):
        if round(b - a) != song.meter:
            continue
        seen = {}
        for t, ns in onsets(notes, a, b):
            p = position(t - a, song.division)
            if p < song.meter:
                seen.setdefault(p, []).extend(ns)
        yield k, a, sorted(seen.items())


def all_bars_of(song: Song, role: str):
    """Every bar of the song, whatever its length, with the part's onsets in
    it: (number, start, end, [(position, [notes])]); bars_of keeps the
    meter's bars only."""
    notes = song.notes.get(role, [])
    numbers = song.numbers or range(len(song.bars))
    for k, (a, b) in zip(numbers, song.bars):
        seen = {}
        for t, ns in onsets(notes, a, b):
            p = position(t - a, song.division)
            if p < b - a:
                seen.setdefault(p, []).extend(ns)
        yield k, a, b, sorted(seen.items())


def place_in_part(song: Song, number: int) -> str:
    """Where a bar sits in its part of the form: first, middle, last; none when no part holds it."""
    for bar, n in song.parts:
        if bar <= number < bar + n:
            return "first" if number == bar else "last" if number == bar + n - 1 else "middle"
    return "none"


def chord_change(song: Song, a: float, b: float) -> str:
    """Whether the chord changes in the bar [a, b): "on" its first beat only,
    "inside" it (on a later beat), or "same" (no change)."""
    out = "same"
    for i, c in enumerate(song.chords):
        if c.root is None or c.fit < FIT or not (a - NEAR <= c.start < b - NEAR):
            continue
        before = song.chords[i - 1] if i else None
        if before is not None and (before.root, before.shape) == (c.root, c.shape):
            continue
        out = "inside" if c.start >= a + NEAR else "on" if out == "same" else out
    return out


def cells(drawn: str, meter: int) -> list[str]:
    """A bar's pattern (pattern(), or a figure's "position:mark" tokens) as
    one cell a beat: the onset positions within the beat as fractions of
    it, their marks kept, space-separated; an empty beat "-"."""
    out = [[] for _ in range(meter)]
    for x in ([] if drawn == "-" else drawn.split()):
        at, _, mark = x.partition(":")
        p = Fraction(at)
        b = math.floor(p)
        if b < meter:
            out[b].append(f"{p - b}:{mark}" if mark else str(p - b))
    return [" ".join(c) or "-" for c in out]


def pattern_of_cells(cells_: list[str]) -> str:
    """The bar's pattern back from its cells."""
    tokens = []
    for b, c in enumerate(cells_):
        for x in ([] if c == "-" else c.split()):
            at, _, mark = x.partition(":")
            tokens.append(f"{b + Fraction(at)}:{mark}" if mark else str(b + Fraction(at)))
    return " ".join(tokens) or "-"


def figure(struck, start: float, song: Song) -> str:
    """A bass bar's figure as a table's outcome: each onset's position and
    the chord tone of its lowest note (TONE_MARKS, ? where no chord fits;
    r a root an octave or more over the bar's lowest note), as
    "position:mark" tokens; a bar rested through "-"."""
    low = [min(n[2] for n in ns) for _, ns in struck]
    lowest = min(low, default=0.0)
    tokens = []
    for (p, _), midi in zip(struck, low):
        c = _chord_at(song.chords, start + p)
        mark = "?" if c is None or c.root is None or c.fit < FIT else TONE_MARKS[tone_of(round(midi) % 12, c.root, c.shape)]
        tokens.append(f"{p}:{'r' if mark == 'R' and midi >= lowest + 11.5 else mark}")
    return " ".join(tokens) or "-"


def bass_units(songs) -> list:
    """Every bar of the bass as a table's unit: its outcome the bar's
    figure (figure()); its values the part, the meter, the tempo band, the
    shape of the chord at the bar's start (harmony's names; ? none fits),
    whether the chord changes in this bar and in the next (chord_change),
    the figure before it (START where none), and the song's bass habit
    (_bass_habit: its density, its tones, its octaves)."""
    out = []
    for s in songs:
        if R.BASS not in s.notes:
            continue
        tempo, previous, last, mine = band(s.bpm), START, None, []
        for k, a, struck in numbered_bars_of(s, R.BASS):
            if last is not None and k != last + 1:
                previous = START
            c = _chord_at(s.chords, a)
            drawn = figure(struck, a, s)
            mine.append(tables.Unit(s.sid, s.game, drawn, {
                "part": R.BASS, "meter": s.meter, "tempo": tempo,
                "shape": "?" if c is None or c.root is None or c.fit < FIT else (c.shape or "major"),
                "chord": chord_change(s, a, a + s.meter), "next": chord_change(s, a + s.meter, a + 2 * s.meter),
                "previous": previous}))
            previous, last = drawn, k
        if mine:
            _give_habit(mine, _bass_habit(mine))
            out += mine
    return out


HABITS = ((1 / 3, "detached"), (2 / 3, "mixed"), (2, "held"))   # a song's share of held notes -> its habit
REPEATS = ((1 / 3, "varied"), (2 / 3, "mixed"), (2, "repeating"))   # its share of bars repeating the one before
DENSITIES = ((2, "sparse"), (6, "medium"), (1e9, "dense"))        # its onsets a bar
TONES = ((0.8, "roots", "Rr"), (0.8, "root-fifth", "Rr5"), (0, "walking", ""))   # the share of its bass notes on these marks
OCTAVES = 0.2                        # the share of a bass's notes an octave up (r) for it to play octaves


def habit_of(share: float, scale=HABITS) -> str:
    """A song's habit from one of its shares (HABITS, REPEATS) or its density a bar (DENSITIES)."""
    return next(name for top, name in scale if share < top)


def _tokens(drawn: str) -> list[str]:
    return [] if drawn == "-" else drawn.split()


def _give_habit(mine: list, habit: str) -> None:
    for u in mine:
        u.values["habit"] = habit


def _rhythm_habit(mine: list) -> str:
    """A song's habit for a part from its bars: how dense, and how much it repeats itself."""
    density = sum(len(_tokens(u.outcome)) for u in mine) / len(mine)
    repeats = sum(1 for u in mine if u.outcome == u.values["previous"]) / len(mine)
    return f"{habit_of(density, DENSITIES)} {habit_of(repeats, REPEATS)}"


def _bass_habit(mine: list) -> str:
    """A song's bass habit from its figures: how dense, which tones (TONES), whether it plays octaves."""
    marks = [t.partition(":")[2] for u in mine for t in _tokens(u.outcome)]
    density = len(marks) / len(mine)
    tones = "walking"
    for floor_, name, on in TONES:
        if marks and sum(1 for m in marks if m in on) / len(marks) >= floor_:
            tones = name
            break
    octaves = "octaves" if marks and sum(1 for m in marks if m == "r") / len(marks) >= OCTAVES else "no-octaves"
    return f"{habit_of(density, DENSITIES)} {tones} {octaves}"


def habits(units_) -> list:
    """The habits in units' values, one unit a song and part: what a writer draws once a song."""
    seen = {}
    for u in units_:
        seen.setdefault((u.song, u.values["part"]), tables.Unit(u.song, u.game, u.values["habit"], {"part": u.values["part"]}))
    return list(seen.values())


def rhythm_habit_units(songs) -> list:
    return habits(units(songs))


def drum_figure(struck, song: Song) -> str:
    """A drum bar's figure as a table's outcome: each hit's position and
    its piece's letter (LETTERS; a sample the reading named no drum, o),
    "position:letter" tokens, two pieces struck together two tokens; a
    bar rested through "-"."""
    tokens = set()
    for p, ns in struck:
        for n in ns:
            tokens.add((p, LETTERS.get(song.pieces.get(n[3]), "o")))
    return " ".join(f"{p}:{letter}" for p, letter in sorted(tokens)) or "-"


def _kit(mine: list) -> str:
    """The pieces a song's drums strike at all, as their letters in LETTERS' order."""
    letters = {t.partition(":")[2] for u in mine for t in _tokens(u.outcome)}
    return "".join(x for x in LETTERS.values() if x in letters) or "-"


def drum_units(songs) -> list:
    """Every bar of the drums as a table's unit: its outcome the bar's
    figure by piece (drum_figure()); its values the part, the meter, the
    tempo band, the bar's place in its part of the form (fills land on the
    last), the figure before it (START where none), the kit (which pieces
    the song strikes at all) and the song's habit (_rhythm_habit: density
    and repetition)."""
    out = []
    for s in songs:
        if R.DRUMS not in s.notes:
            continue
        tempo, previous, last, mine = band(s.bpm), START, None, []
        for k, a, struck in numbered_bars_of(s, R.DRUMS):
            if last is not None and k != last + 1:
                previous = START
            drawn = drum_figure(struck, s)
            mine.append(tables.Unit(s.sid, s.game, drawn, {
                "part": R.DRUMS, "meter": s.meter, "tempo": tempo, "place": place_in_part(s, k), "previous": previous}))
            previous, last = drawn, k
        if mine:
            kit = _kit(mine)
            _give_habit(mine, _rhythm_habit(mine))
            for u in mine:
                u.values["kit"] = kit
            out += mine
    return out


def drum_habit_units(songs) -> list:
    return habits(drum_units(songs))


def bass_habit_units(songs) -> list:
    return habits(bass_units(songs))


def cell_units(units_) -> list:
    """Each beat of each bar unit as a unit of its own: the cell its outcome;
    its values the part, the meter, the beat (from 0) and the cell before
    it in the bar (START at the first beat)."""
    out = []
    for u in units_:
        previous = START
        for i, c in enumerate(cells(u.outcome, u.values["meter"])):
            out.append(tables.Unit(u.song, u.game, c, {"part": u.values["part"], "meter": u.values["meter"],
                                                         "beat": i, "previous": previous}))
            previous = c
    return out


class BarCells:
    """The floor under a bar-pattern table: the bar as a chain of beat
    cells, each cell's table conditioned on the part, the meter, the beat
    and the cell before it; so a bar never counted whole still has a
    likelihood (the product of its cells') and can be drawn (cell by cell)."""
    SHAPE = ("part", "meter", "beat", "previous")
    COVERS = ("part", "meter")           # what a bar table over this floor need not back off below

    def __init__(self, units_):
        self.table = tables.Table(self.SHAPE, "cells", votes=tables.SHARES).fit(cell_units(units_))

    def p(self, drawn: str, values: dict) -> float:
        prob, previous = 1.0, START
        for i, c in enumerate(cells(drawn, values["meter"])):
            prob *= self.table.p(c, (values["part"], values["meter"], i, previous))
            previous = c
        return prob

    def draw(self, values: dict, rng) -> str:
        out, previous = [], START
        for i in range(values["meter"]):
            previous = self.table.draw((values["part"], values["meter"], i, previous), rng)
            out.append(previous)
        return pattern_of_cells(out)


def value_units(songs) -> list:
    """Every note of the melody's and the counter's line (of notes struck
    together, the highest) as a table's unit: its outcome whether the note
    is held (sounding SHORT of the way to the next note or more) or
    detached; its values the part, the value (beats to the next note on
    the song's grid, what a score would write), the meter, the tempo band,
    the note's place in its bar (PLACES), its beat in the bar (from 0), the
    articulation before it (START at the line's first note) and the song's
    habit for the part (HABITS: its share of held notes, which a writer
    would draw once a song). The values themselves follow from the bars'
    patterns (the onsets), so they condition this table rather than being
    drawn from one."""
    out = []
    for s in songs:
        tempo, starts = band(s.bpm), [a for a, _ in s.bars]
        for role in (R.MELODY, R.COUNTER):
            if role not in s.notes:
                continue
            line, previous, mine = _line(s.notes[role]), START, []
            for n, after in zip(line, line[1:]):
                gap = after[0] - n[0]
                value = position(gap, s.division)
                i = bisect.bisect_right(starts, n[0] + NEAR) - 1
                if value == 0 or math.isnan(n[1]) or i < 0 or n[0] >= s.bars[i][1] - NEAR:
                    continue
                at = position(n[0] - s.bars[i][0], s.division)
                held = "held" if n[1] / gap >= SHORT else "detached"
                mine.append(tables.Unit(s.sid, s.game, held, {
                    "part": role, "value": str(value), "meter": s.meter, "tempo": tempo, "place": place(at),
                    "beat": math.floor(at), "previous": previous}))
                previous = held
            if mine:
                _give_habit(mine, habit_of(sum(1 for u in mine if u.outcome == "held") / len(mine)))
                out += mine
    return out


def habit_units(songs) -> list:
    """Each song's articulation habit for the melody and the counter (value_units'), one unit a song and part."""
    return habits(value_units(songs))


def units(songs) -> list:
    """Every bar of every part as a table's unit (tables.Unit): its outcome
    the bar's pattern, its values the part, the meter, the tempo band, the
    previous bar's pattern of the part (START where none), the bar's place
    in its part of the form, whether the chord changes in it, and the
    song's habit for the part (_rhythm_habit: its density and how much it
    repeats itself, which a writer would draw once a song)."""
    out = []
    for s in songs:
        tempo = band(s.bpm)
        for role in PARTS:
            if role not in s.notes:
                continue
            previous, last, mine = START, None, []
            for k, a, struck in numbered_bars_of(s, role):
                if last is not None and k != last + 1:
                    previous = START                      # a bar of another length between: the chain breaks
                drawn = pattern(p for p, _ in struck)
                mine.append(tables.Unit(s.sid, s.game, drawn, {
                    "part": role, "meter": s.meter, "tempo": tempo, "previous": previous,
                    "place": place_in_part(s, k), "chord": chord_change(s, a, a + s.meter)}))
                previous, last = drawn, k
            if mine:
                _give_habit(mine, _rhythm_habit(mine))
                out += mine
    return out


@dataclass
class Rhythms:
    songs: Counter = field(default_factory=Counter)                       # role -> songs with the part
    bars: Counter = field(default_factory=Counter)                        # role -> bars of those songs
    onsets: Counter = field(default_factory=Counter)                      # role -> onsets in them
    places: dict = field(default_factory=lambda: defaultdict(Counter))    # role -> place -> onsets (rolls too)
    patterns: dict = field(default_factory=lambda: defaultdict(Tally))    # (role, meter) -> drawn -> bars
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
        for role in PARTS:
            if role not in s.notes and role not in s.rolls:
                continue
            r.songs[role] += 1
            drawn = []
            for a, struck in bars_of(s, role):
                r.bars[role] += 1
                r.onsets[role] += len(struck)
                drawn.append(draw([p for p, _ in struck], s.meter))
                r.places[role].update(place(p) for p, _ in struck)
                r.places[role].update(place(position(t - a, s.division)) for t, _ in onsets(s.rolls.get(role, []), a, a + s.meter))
            r.patterns[role, s.meter].add(drawn)
        first = s.bars[0][0] if s.bars else 0.0
        pitched = [n[0] - first for role in PITCHED for n in s.notes.get(role, []) + s.rolls.get(role, []) if n[0] >= first]
        off = [t for t in pitched if abs(t * 2 - round(t * 2)) / 2 >= NEAR]
        if pitched:
            r.off_eighths.append(100 * len(off) / len(pitched))
        if off:
            r.triplets.append(100 * sum(1 for t in off if abs(t * 3 - round(t * 3)) / 3 < NEAR) / len(off))
    return r


def _chord_at(chords, t: float) -> Span | None:
    i = bisect.bisect_right([c.start for c in chords], t + NEAR) - 1
    return chords[i] if 0 <= i < len(chords) and chords[i].end > t + NEAR else None


def _line(notes, lowest: bool = False) -> list:
    """Notes struck together as one: the highest, or the lowest."""
    pick = min if lowest else max
    return [pick(ns, key=lambda n: n[2]) for _, ns in onsets(notes, -math.inf, math.inf)]


def _sizes(moves) -> Counter:
    """Moves by size (SIZES) and direction: (size, "up"/"down"/"") -> count."""
    out = Counter()
    for m in moves:
        size = next(name for top, name in SIZES if abs(m) <= top)
        out[size, "up" if m > 0 else "down" if m < 0 else ""] += 1
    return out


@dataclass
class Bass:
    songs: int = 0
    bars: int = 0
    figures: dict = field(default_factory=lambda: defaultdict(Tally))     # meter -> drawn with tones -> bars
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
        for start, struck in bars_of(s, R.BASS):
            b.bars += 1
            low = [min(n[2] for n in ns) for _, ns in struck]
            floor = min(low, default=0.0)
            marks = {}
            for (p, _), midi in zip(struck, low):
                c = _chord_at(s.chords, start + p)
                mark = "?" if c is None or c.root is None or c.fit < FIT else TONE_MARKS[tone_of(round(midi) % 12, c.root, c.shape)]
                marks[p] = "r" if mark == "R" and midi >= floor + 11.5 else mark
            drawn.append(draw(list(marks), s.meter, marks))
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
    figures: dict = field(default_factory=lambda: defaultdict(Tally))     # meter -> ((piece, drawn), ...) -> bars


def _name(profile: dict) -> str:
    """A drum sound's piece from its profile (the module's rule)."""
    if profile["a_bar"] >= DENSE:
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
        for i, (_, struck) in enumerate(bars_of(s, R.DRUMS)):
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
        for _, struck in bars_of(s, R.DRUMS):
            d.bars += 1
            by = defaultdict(set)
            for p, ns in struck:
                for n in ns:
                    by[d.sounds[n[3]]["name"]].add(p)
            drawn.append(tuple((piece, draw(sorted(by[piece]), s.meter)) for piece in PIECES if piece in by))
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
            m.lengths[position(gap, s.division)] += 1
            if not math.isnan(n[1]):
                m.sounded.append(min(1.0, n[1] / gap))
    return m


def value(length: Fraction) -> str:
    """A length's name (VALUES): the shortest value it fits in."""
    return next(name for top, name in VALUES if length <= top)


def _moves_table(moves: Counter, semitones: Counter) -> list[str]:
    total = sum(moves.values()) or 1
    out = [f"    {'move':10s} {'share':>6s} {'up':>6s} {'down':>6s}"]
    for _, size in SIZES:
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
    out.append(f"  {'part':14s} {'songs':>5s} {'bars':>6s} {'a bar':>6s}" + "".join(f" {p:>9s}" for p in PLACES)
               + f" {'off 8ths':>9s} {'triplet':>8s}")
    for role in PARTS:
        if r.bars[role]:
            n = sum(r.places[role].values())
            off = n - r.places[role]["beat"] - r.places[role]["eighth"]
            out.append(f"  {role:14s} {r.songs[role]:5d} {r.bars[role]:6d} {r.onsets[role] / r.bars[role]:6.1f}"
                       + "".join(f" {_pct(r.places[role][p], n):>9s}" for p in PLACES)
                       + f" {_pct(off, n):>9s} {_pct(r.places[role]['triplet'], off):>8s}")
    out.append(f"  as stage 2 counts them (pitched parts, a song's share, the median): off the eighths "
               f"{_median(r.off_eighths, ' %')}, of them on a triplet {_median(r.triplets, ' %')}")
    out.append("  songs by meter: " + ", ".join(f"{k} beats {r.meters[k]}" for k in meters)
               + f"; bars of another length left out: {sum(r.odd.values())}")
    for meter in meters:
        out.append(f"\nrhythms, bars of {meter} beats ({r.meters[meter]} songs; x on a quarter of the beat, t on a third,"
                   " ~ finer; the share of the part's bars)")
        for role in PARTS:
            c = r.patterns.get((role, meter))
            if not c:
                continue
            n = sum(c.values())
            out.append(f"  {role} ({n} bars, {sum(1 for k in c if k != REST)} patterns)")
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
        out.append(f"  bars of {meter} beats ({n} bars, {sum(1 for k in c if k != REST)} figures)")
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
            for i, (piece, drawn) in enumerate(figure or (("", REST),)):
                out.append(f"    {LETTERS.get(piece, ' ')} {drawn:{5 * meter - 2}s} "
                           + (f"{_pct(count, n)}  {c.songs[figure]:3d} songs" if i == 0 else ""))
    m = melody(songs)
    out.append(f"\nmelody ({m.songs} songs, {m.notes} notes): its moves")
    out += _moves_table(m.moves, m.semitones)
    out.append("  its notes' lengths, to the next note")
    n = sum(m.lengths.values()) or 1
    values = Counter()
    for length, count in m.lengths.items():
        values[value(length)] += count
    for _, name in VALUES:
        if values[name]:
            out.append(f"    {name:22s} {_pct(values[name], n)}")
    detached = sum(1 for x in m.sounded if x < SHORT)
    out.append(f"    the note sounds for {_median(m.sounded)} of it; detached (under {SHORT:g}): {_pct(detached, len(m.sounded))}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bitcomposer.translate.rhythm", description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", help="the readings database (default: ~/.local/share/bitcomposer/readings.db)")
    ap.add_argument("--game", help="only this game's songs (the songs table's game)")
    ap.add_argument("--top", type=int, default=10, help="rows of each patterns table (default 10)")
    ap.add_argument("--spc", metavar="DIR", help="the game folders' root, or one game's folder: the drums named by their sound")
    args = ap.parse_args(argv)
    db = store.connect(args.db)
    songs, left_out = load(db, args.game)
    if not songs:
        print("bitcomposer.translate.rhythm: no songs on a beat to count", file=sys.stderr)
        return 1
    games = [g for g, in db.execute("SELECT DISTINCT game FROM songs")]
    print(report(songs, left_out, args.top, args.game or (games[0] if len(games) == 1 else ""),
                 drums_mod.Bank(db, args.spc) if args.spc else None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
