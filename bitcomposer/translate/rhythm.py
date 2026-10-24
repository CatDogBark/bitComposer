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

from . import drums as drums_mod, roles as R, store, tables, vocab
from .vocab import FIT, MARKS, SOUNDS, Span, _beats_at, _buckets, _median, _pct, _sounding, tone_of
from .vocab import TONES as CHORD_TONES

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
    parts: list = field(default_factory=list)     # the form's parts: (first bar number, bars, the earlier part repeated or None, letter)
    sections: list = field(default_factory=list)  # the form's sections (a short part played again at once joined), the same shape
    pieces: dict = field(default_factory=dict)    # sample key -> the piece the reading named it (drums.PIECES, "none")
    tonic: int | None = None                      # the key reader's tonic and mode (the harmony units' degrees)
    mode: str = "major"
    loop_bar: int | None = None                   # the bar number the loop returns to
    voices: list = field(default_factory=list)    # every voice the role reader named: (voice, role, of, evidence dict)
    bass_voices: dict = field(default_factory=dict)   # voice -> its notes, where the bass role holds two voices or more
    voice_notes: dict = field(default_factory=dict)   # voice -> (role, its notes), every part's voice (rolls left out)
    copies: dict = field(default_factory=dict)        # a planned song: role -> [(first bar, bars, the bar copied from)], the band
                                                      # coming back with the theme (the writers copy their own earlier bars there)
    periods: dict = field(default_factory=dict)       # a planned song: role -> {bar index: the lag in bars whose bar it plays again}
                                                      # (the plan's held bars of a backing part's period, period_units)
    feel: str | None = None                           # the song's feel, duple or triple (song_feel); a planned song's drawn once


def load(db, game: str | None = None) -> tuple[list[Song], dict]:
    """The songs to count (game: only that game's), and why the others were
    left out: {"free time": n, "mostly silent": n}; the harmony counts' songs."""
    songs, out = [], Counter()
    where, args = ("WHERE game = ?", (game,)) if game else ("", ())
    for sid, title, meter, division, seconds, loop_bar, loop_seconds, bpm, game_name, tonic, mode in db.execute(
            f"SELECT id, title, meter, division, seconds, loop_bar, loop_seconds, bpm, game, key_tonic, key_mode "
            f"FROM songs {where}", args):
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
                    parts=[(bar, n, of, label) for bar, n, of, label in db.execute(
                        "SELECT bar, bars, [of], label FROM form WHERE song = ? AND level = 'part' ORDER BY bar", (sid,))],
                    sections=[(bar, n, of, label) for bar, n, of, label in db.execute(
                        "SELECT bar, bars, [of], label FROM form WHERE song = ? AND level = 'section' ORDER BY bar", (sid,))],
                    tonic=tonic, mode=mode or "major", loop_bar=loop_bar)
        keys, song.pieces = {}, {}
        for idx, key, piece in db.execute("SELECT idx, key, piece FROM samples WHERE song = ?", (sid,)):
            keys[idx] = key
            song.pieces[key] = piece
        basses = {}
        for voice, role, of, evidence, blob in db.execute("SELECT voice, role, [of], evidence, notes FROM voices WHERE song = ?", (sid,)):
            try:
                song.voices.append((voice, role, of, json.loads(evidence) if evidence else {}))
            except ValueError:
                song.voices.append((voice, role, of, {}))
            if role in PARTS:
                into = song.rolls if evidence and '"roll"' in evidence else song.notes
                mine = [(s, length, m, keys.get(int(i), "noise")) for s, length, m, level, _, i in store.unpack(blob)
                        if s < end and level > 0 and (role == R.DRUMS or not math.isnan(m))]
                into.setdefault(role, []).extend(mine)
                if into is song.notes:
                    song.voice_notes[voice] = (role, mine)
                if role == R.BASS and into is song.notes:
                    basses[voice] = mine
        if len(basses) >= 2:
            song.bass_voices = basses
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


def numbered_bars_of(song: Song, role: str, notes: list | None = None):
    """bars_of with each bar's number in the reading first: (number, start, [(position, [notes])]); `notes` in place of
    the part's (one voice's own)."""
    notes = song.notes.get(role, []) if notes is None else notes
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
    for bar, n, *_ in song.parts:
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
        weight = part_weights(s).get(R.BASS, "minor")
        for k, a, struck in numbered_bars_of(s, R.BASS, line_notes(s, R.BASS)):   # the line where the bass holds two voices
            if last is not None and k != last + 1:
                previous = START
            c = _chord_at(s.chords, a)
            drawn = figure(struck, a, s)
            mine.append(tables.Unit(s.sid, s.game, drawn, {
                "part": R.BASS, "meter": s.meter, "tempo": tempo, "weight": weight, "feel": song_feel(s),
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


WEIGHTS = ((0.2, "minor"), (0.5, "half"), (2, "main"))   # a pitched part's share of the band's pitched strikes


def part_weights(song: Song) -> dict:
    """Each pitched part's weight in the song (WEIGHTS): its share of the
    pitched parts' strikes. The density a part plays at follows it (an
    accompaniment that is the band's main part is dense in 76 % of songs,
    a minor one in 8 %), so a writer draws the habit given it."""
    counts = {role: len(ns) for role, ns in song.notes.items() if role != R.DRUMS}
    total = sum(counts.values()) or 1
    return {role: habit_of(n / total, WEIGHTS) for role, n in counts.items()}


def habits(units_) -> list:
    """The habits in units' values, one unit a song and part, with the tempo
    band and the part's weight beside where the units carry them: what a
    writer draws once a song, given those."""
    seen = {}
    for u in units_:
        values = {"part": u.values["part"]}
        for k in ("tempo", "weight"):
            if k in u.values:
                values[k] = u.values[k]
        seen.setdefault((u.song, u.values["part"]), tables.Unit(u.song, u.game, u.values["habit"], values))
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
                "part": R.DRUMS, "meter": s.meter, "tempo": tempo, "place": place_in_part(s, k), "previous": previous, "feel": song_feel(s)}))
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


DRUM_GROUPS = (("K", "S", "t"), ("h",), ("c",), ("o",))   # the kit's limbs: kick, snare and tom together; the hat; cymbals; the rest
UPPER = (R.HARMONY, R.ACCOMP, R.ARP)   # the parts whose tones voice a chord over the bass
WIDTHS = ((7, "close"), (14, "open"), (1e9, "wide"))   # semitones from the lowest upper note to the highest


def width_of(semitones: float) -> str:
    return next(name for top, name in WIDTHS if semitones <= top)


def voicing_units(songs) -> list:
    """Each chord span of each song, for each upper part sounding in it, as a
    table's unit: its outcome the chord tones the part holds in the span
    (vocab's marks, R 3 s 5 7 +, in order; a tone sounds when the part's
    notes on it cover SOUNDS of the span); its values the part, the chord's
    shape, the tone the bass holds under it (its lowest sounding tone, or
    none), the width of the whole upper voicing in the span (WIDTHS), the
    part's tones in the span before (START at its first), and the song's
    habit for the part (how many tones it holds a span, in thirds of the
    readings' range: thin, full, rich)."""
    out = []
    for s in songs:
        buckets = {role: _buckets([(a, b, m) for a, b, m, _ in ns]) for role, ns in s.notes.items()}
        if not any(role in buckets for role in UPPER):
            continue
        previous = {role: START for role in UPPER}
        mine = {role: [] for role in UPPER}
        for c in s.chords:
            if c.root is None or c.fit < FIT:
                continue
            shape = c.shape or "major"
            bass = "none"
            if R.BASS in buckets:
                low = [m for m, share in _sounding(buckets[R.BASS], c).items() if share >= SOUNDS - 1e-9]
                if low:
                    bass = MARKS[tone_of(min(low) % 12, c.root, c.shape)]
            upper = [m for role in UPPER if role in buckets for m, share in _sounding(buckets[role], c).items() if share >= SOUNDS - 1e-9]
            width = width_of(max(upper) - min(upper)) if upper else "none"
            for role in UPPER:
                if role not in buckets:
                    continue
                pitches = [m for m, share in _sounding(buckets[role], c).items() if share >= SOUNDS - 1e-9]
                if not pitches:
                    continue
                tones = {tone_of(m % 12, c.root, c.shape) for m in pitches}
                held = " ".join(MARKS[t] for t in CHORD_TONES if t in tones)
                mine[role].append(tables.Unit(s.sid, s.game, held, {
                    "part": role, "shape": shape, "bass": bass, "width": width, "previous": previous[role],
                    "count": min(4, len(tones))}))
                previous[role] = held
        for role, units_ in mine.items():
            if units_:
                _give_habit(units_, habit_of(statistics.mean(u.values["count"] for u in units_) / 4, RICHNESS))
                out += units_
    return out


RICHNESS = ((0.4, "thin"), (0.6, "full"), (2, "rich"))   # a part's mean tones a span, over four


def voicing_habit_units(songs) -> list:
    """The upper parts' richness habits, one unit a song and part (what a writer draws once a song)."""
    return habits(voicing_units(songs))


MOTIONS = ((1 / 3, "block"), (2 / 3, "mixed"), (2, "arpeggiated"))   # an upper part's share of strikes that change its pitches


def upper_motion(notes) -> float:
    """How an upper part moves through its tones: the share of its strike
    times (notes within NEAR of each other one strike) whose pitches differ
    from the strike before's. A chord restruck is 0, an arpeggio 1."""
    strikes, last = [], None
    for st, _, m, _ in sorted(n for n in notes if not math.isnan(n[2])):
        if last is not None and st - last < NEAR:
            strikes[-1].add(round(m))
        else:
            strikes.append({round(m)})
            last = st
    if len(strikes) < 2:
        return 0.0
    return sum(1 for a, b in zip(strikes, strikes[1:]) if a != b) / (len(strikes) - 1)


def upper_motion_units(songs) -> list:
    """Each upper part of each song as a unit: its outcome its motion
    (MOTIONS), its values the part and the tempo band; drawn once a song."""
    out = []
    for s in songs:
        for role in UPPER:
            if s.notes.get(role):
                out.append(tables.Unit(s.sid, s.game, habit_of(upper_motion(s.notes[role]), MOTIONS),
                                       {"part": role, "tempo": band(s.bpm)}))
    return out


def width_units(songs) -> list:
    """Each chord span as a unit: its outcome how the upper parts voice the
    chord as a whole, the number of distinct pitches sounding (to 6) and
    the width (WIDTHS); its values the shape, the parts present, the bass's
    tone, and the voicing before."""
    out = []
    for s in songs:
        buckets = {role: _buckets([(a, b, m) for a, b, m, _ in ns]) for role, ns in s.notes.items()}
        parts = "".join(role[0] for role in UPPER if role in buckets)
        if not parts:
            continue
        previous = START
        for c in s.chords:
            if c.root is None or c.fit < FIT:
                continue
            upper = sorted({m for role in UPPER if role in buckets for m, share in _sounding(buckets[role], c).items() if share >= SOUNDS - 1e-9})
            if not upper:
                continue
            bass = "none"
            if R.BASS in buckets:
                low = [m for m, share in _sounding(buckets[R.BASS], c).items() if share >= SOUNDS - 1e-9]
                if low:
                    bass = MARKS[tone_of(min(low) % 12, c.root, c.shape)]
            voicing = f"{min(6, len(upper))}:{width_of(upper[-1] - upper[0])}"
            out.append(tables.Unit(s.sid, s.game, voicing, {"part": "upper", "shape": c.shape or "major", "parts": parts,
                                                              "bass": bass, "previous": previous}))
            previous = voicing
    return out



def drum_group(figure: str, letters) -> str:
    """A drum figure's tokens on these pieces alone; "-" when none."""
    return " ".join(t for t in _tokens(figure) if t.partition(":")[2] in letters) or "-"


def drum_group_units(songs, letters) -> list:
    """drum_units for one group of pieces: each bar's figure on those pieces alone (its part "drums-" + the
    letters), with the group's own habit; a song without the group has no units."""
    name = "drums-" + "".join(letters)
    out = []
    by_song = {}
    for u in drum_units(songs):
        by_song.setdefault(u.song, []).append(u)
    for units_ in by_song.values():
        mine = []
        previous = START
        for u in units_:
            figure = drum_group(u.outcome, letters)
            values = dict(u.values)
            values["part"] = name
            values["previous"] = previous if u.values["previous"] != START else START
            mine.append(tables.Unit(u.song, u.game, figure, values))
            previous = figure
        if any(u.outcome != "-" for u in mine):
            _give_habit(mine, _rhythm_habit(mine))
            out += mine
    return out


def bass_habit_units(songs) -> list:
    return habits(bass_units(songs))


def drum_group_habit_units(songs) -> list:
    """Each drum group of each song as a unit: its outcome the group's own
    habit (the density and repetition of its bars, rests counted), its
    values the group (part) and the kit's habit. A kit written free draws
    each group's habit given the kit's: the cymbals and the other sounds
    are sparse under a dense kit (the readings, 2026-10-23), and a group's
    rest rate follows its own habit (sparse groups rest in six bars of ten)."""
    kit = {u.song: u.values["habit"] for u in drum_units(songs)}
    out = []
    for letters in DRUM_GROUPS:
        seen = set()
        for u in drum_group_units(songs, letters):
            if u.song in seen:
                continue
            seen.add(u.song)
            out.append(tables.Unit(u.song, u.game, u.values["habit"], {"part": u.values["part"], "habit": kit.get(u.song, "medium mixed")}))
    return out


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

    def to_json(self) -> dict:
        return {"kind": "cells", "table": self.table.to_json()}

    @classmethod
    def from_json(cls, d: dict) -> "BarCells":
        floor = cls.__new__(cls)
        floor.table = tables.Table.from_json(d["table"], "cells")
        return floor

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


tables.FLOORS["cells"] = BarCells.from_json


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
        weights = part_weights(s)
        for role in PARTS:
            if role not in s.notes:
                continue
            previous, last, mine = START, None, []
            for k, a, struck in numbered_bars_of(s, role, line_notes(s, role)):
                if last is not None and k != last + 1:
                    previous = START                      # a bar of another length between: the chain breaks
                drawn = pattern(p for p, _ in struck)
                mine.append(tables.Unit(s.sid, s.game, drawn, {
                    "part": role, "meter": s.meter, "tempo": tempo, "previous": previous, "weight": weights.get(role, "minor"), "feel": song_feel(s),
                    "place": place_in_part(s, k), "chord": chord_change(s, a, a + s.meter)}))
                previous, last = drawn, k
            if mine:
                _give_habit(mine, _rhythm_habit(mine))
                out += mine
    return out


# --- the melody's bar cells: a bar of the tune as its rhythm and intervals, what a tune repeats and returns to ---

ECHOES = ((1 / 3, "varied"), (2 / 3, "mixed"), (2, "repeating"))   # a song's share of tune bars that echo an earlier bar


def melody_cells(song: Song, role: str = None) -> list:
    """Each bar's cell of the tune (the melody's line, notes struck together
    the highest): its onsets in twelfths from the bar line and its
    intervals, as one key; None where the bar has no note."""
    role = role or R.MELODY
    line = sorted(_line(song.notes.get(role, [])))
    out = []
    for a, b in song.bars:
        mine = [n for n in line if a - NEAR <= n[0] < b - NEAR]
        if not mine:
            out.append(None)
            continue
        ps = [round(n[2]) for n in mine]
        out.append(" ".join(str(round((n[0] - a) * 12)) for n in mine) + " | " + " ".join(f"{y - x:+d}" for x, y in zip(ps, ps[1:])))
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
        habit = habit_of(echo, ECHOES)
        weight = part_weights(s).get(R.MELODY, "minor")
        for c in cells:
            out.append(tables.Unit(s.sid, s.game, c, {"part": R.MELODY, "tempo": band(s.bpm), "weight": weight, "habit": habit}))
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


def register_units(songs) -> list:
    """Each pitched part of each song as a unit: its outcome the register it
    plays in, "low-high" (midi, the part's notes' 10th and 90th percentiles,
    REGISTER_BIN semitones a step); its values the part. What a song written
    with no original draws a part's register from."""
    out = []
    for s in songs:
        for role, ns in s.notes.items():
            if role == R.DRUMS:
                continue
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
    return [tables.Unit(s.sid, s.game, str(int(round(s.bpm / TEMPO_BIN)) * TEMPO_BIN), {"part": "song", "tempo": band(s.bpm)}) for s in songs if s.bpm]


def weight_units(songs) -> list:
    """Each pitched part of each song as a unit: its outcome its weight in the band (WEIGHTS), its value the part."""
    return [tables.Unit(s.sid, s.game, w, {"part": role}) for s in songs for role, w in part_weights(s).items()]


def form_size_units(songs) -> list:
    """Each song's form as a unit: its outcome how many parts it has (to 12), its value the part (form)."""
    return [tables.Unit(s.sid, s.game, str(min(len(s.parts), 12)), {"part": "form"}) for s in songs if s.parts]


SOUND_BIN = 0.1                      # the grain a part's sounded share is kept to


def sounded_share(notes) -> float | None:
    """The share of its gap to the next note a part's note sounds, the median
    over the part; None where no two notes stand apart."""
    line = sorted(n for n in notes if not math.isnan(n[1]))
    shares = [min(1.0, n[1] / (m[0] - n[0])) for n, m in zip(line, line[1:]) if m[0] - n[0] > NEAR]
    return statistics.median(shares) if shares else None


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


def phrase_windows(song: Song, length: int = PHRASE) -> list:
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


def phrase_heads(song: Song, role: str = None) -> list:
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
        own = {i for i, bar, n in _own_parts(s)}
        for i, letters in by_part.items():
            if i in own and len(letters) >= 1:
                out.append(tables.Unit(s.sid, s.game, " ".join(letters), {"part": R.MELODY, "phrases": str(min(len(letters), 5)), "form": form_place(s, i)}))
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
        names = bar_chords(s) if s.tonic is not None else None
        bass = [figure(struck, a, s) if struck else None for _, a, _, struck in all_bars_of(s, R.BASS)] if R.BASS in s.notes else None
        acc = [pattern(p for p, _ in struck) if struck else None for _, _, _, struck in all_bars_of(s, R.ACCOMP)] if R.ACCOMP in s.notes else None
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


def part_voices(song: Song, role: str) -> dict:
    """An upper part's voices with notes: voice -> its notes (the rolls left out)."""
    return {v: ns for v, (r, ns) in song.voice_notes.items() if r == role and ns}


def line_voice(voices: dict, role: str):
    """A layered part's line among its voices: the bass's the voice with the longest notes (its sustained voice under a
    busier one), another part's the voice with the most notes (layer_units' rule)."""
    if role == R.BASS:
        lengths = {v: statistics.median([n[1] for n in ns if not math.isnan(n[1])] or [0.0]) for v, ns in voices.items()}
        return max(lengths, key=lambda v: (lengths[v], -v))
    return max(voices, key=lambda v: (len(voices[v]), -v))


def line_notes(song: Song, role: str) -> list | None:
    """A layered part's own line where it holds two voices or more (an upper
    part or the bass): the line voice's notes (line_voice); None for every
    other part, whose bar is the part's. The figure table counts the line,
    not the voices merged: FFVI's two-voice accompaniments strike 7.3 times
    a bar together, the line 6.6 and the second voice 4.5, and a line
    written to the merged count with a second line beside it had struck
    10.3 (2026-10-23); its two-voice basses are a sustained line under a
    busy staccato voice in the same register."""
    if role not in UPPER + (R.BASS,):
        return None
    voices = part_voices(song, role)
    if len(voices) < 2:
        return None
    return voices[line_voice(voices, role)]


DENSITY_BINS = ((3, "1-3"), (6, "4-6"), (9, "7-9"), (1e9, "10+"))   # a bar's onsets, for the second line's draw under the line's bar


def density_bin(onsets: int) -> str:
    """A bar's onset count as a class (DENSITY_BINS)."""
    return next(name for top, name in DENSITY_BINS if onsets <= top)


def second_figure_units(songs) -> list:
    """Each bar of each upper part holding two voices or more as a unit: its
    outcome the bar's pattern of the voices beside the line (the second
    line; "-" where they rest), its values the part, the line's density
    class in the bar (DENSITY_BINS) and the line's own pattern. The second
    line is drawn under the line's bar, bar by bar, the pattern backing off
    to the density class where the pattern is rare: FFVI's second
    accompaniment voice strikes 4.5 times a bar beside a line of 6.6, two
    of five of its onsets with the line's."""
    out = []
    for s in songs:
        for role in UPPER + (R.BASS,):
            voices = part_voices(s, role)
            if len(voices) < 2:
                continue
            line = line_voice(voices, role)
            others = [n for v, ns in voices.items() if v != line for n in ns]
            key = (lambda struck, a: figure(struck, a, s)) if role == R.BASS else (lambda struck, a: pattern(p for p, _ in struck))
            line_bars = {k: key(struck, a) for k, a, struck in numbered_bars_of(s, role, voices[line])}
            line_struck = {k: [p for p, _ in struck] for k, a, struck in numbered_bars_of(s, role, voices[line])}
            tempo, feel = band(s.bpm), song_feel(s)
            for k, a, struck in numbered_bars_of(s, role, others):
                if line_bars.get(k, "-") != "-":
                    # the bass's second voice as its own figure (its chord-tone marks realize it); an upper part's beside the line's
                    # onsets: which of them it strikes with, and the onsets of its own (second_mask)
                    outcome = (key(struck, a) if struck else "-") if role == R.BASS else second_mask(line_struck[k], [p for p, _ in struck])
                    out.append(tables.Unit(s.sid, s.game, outcome,                   # by the line's onset count: a mask is read onset by onset
                                           {"part": role, "feel": feel, "tempo": tempo, "onsets": str(len(line_bars[k].split())), "line": line_bars[k]}))
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
    own = [p for p in other_positions if p not in on]
    return flags + (" | " + " ".join(str(p) for p in own) if own else "")


def apply_mask(line_pattern: str, outcome: str) -> str:
    """The second voice's bar (a pattern) from the line's bar and a second_mask outcome: the line's onsets it strikes with (a
    mask shorter or longer than the line's onsets is read around it) and its own onsets; "-" where it rests."""
    if outcome == "-" or line_pattern in ("-", ""):
        return "-"
    line = [Fraction(t.partition(":")[0]) for t in line_pattern.split()]
    flags, _, own = outcome.partition("|")
    bits = flags.split()
    if not bits or all(b not in ("0", "1") for b in bits):
        return outcome if ":" not in outcome else "-"          # an old-style absolute pattern: as it stands
    positions = {line[i] for i in range(len(line)) if bits[i % len(bits)] == "1"}
    positions |= {Fraction(p) for p in own.split()}
    return pattern(sorted(positions))


def sample_id(key: str) -> str:
    """A reading's sample key as a pack names the sample (pack.voice_of): "s" and its first ten characters."""
    return "s" + key[:10]


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
        for role in UPPER + (R.BASS,):
            voices = part_voices(s, role)
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
        for role in UPPER + (R.BASS,):
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


def _theme_of(song: Song):
    """The tune's cells, its phrase windows (the live ones) and its theme: the head cell of its first sounding phrase
    and that phrase's window; (cells, windows, theme window, theme) or None without two sounding phrases."""
    cells = melody_cells(song)
    windows = [(w, next((cells[k] for k in w if cells[k]), None)) for i, w in phrase_windows(song) if i is not None]
    heads = [(w, h) for w, h in windows if h]
    if len(heads) < 2:
        return None
    return cells, windows, heads[0][0], heads[0][1]


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
        tune = sorted(_line(s.notes.get(R.MELODY, [])))
        others = {role: (melody_cells(s, role), sorted(_line(s.notes[role]))) for role in THEME_PARTS if s.notes.get(role)}
        for k, c in enumerate(cells):
            if c != theme:
                continue
            a = s.bars[k][0]
            t0 = next((n for n in tune if n[0] >= a - NEAR), None)
            tokens = []
            for role, (oc, line) in others.items():
                if k < len(oc) and oc[k] == theme:
                    o0 = next((n for n in line if n[0] >= a - NEAR), None)
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


def song_feel(song: Song) -> str:
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
            k = bisect.bisect_right([a for a, _ in song.bars], n[0] + NEAR) - 1
            if k < 0:
                continue
            p = position(n[0] - song.bars[k][0], song.division)
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
PART_LENGTHS = ((4, "short"), (8, "medium"), (1e9, "long"))   # a part of the form by its bars, for the period's draw


def part_length(n: int) -> str:
    """A part of the form's length as a class (PART_LENGTHS)."""
    return next(name for top, name in PART_LENGTHS if n <= top)


def block_key(song: Song, role: str, a: float, b: float):
    """A backing part's bar as the writers draw it: the bass's figure
    (positions with chord-tone marks), the drums' pieces by position, an
    upper part's onset pattern; a riff that moves with the chord keeps its
    key. () where the part rests."""
    struck = {}
    for n in song.notes.get(role, []):
        if a - NEAR <= n[0] < b - NEAR:
            struck.setdefault(position(n[0] - a, song.division), []).append(n)
    struck = sorted(struck.items())
    if not struck:
        return ()
    if role == R.BASS:
        return figure(struck, a, song)
    if role == R.DRUMS:
        return tuple(sorted((p, str(n[3])) for p, ns in struck for n in ns))
    return pattern(p for p, _ in struck)


def _blocks(song: Song):
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
        tempo = band(s.bpm)
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


def melody_recall_units(songs) -> list:
    """What each tune bar is to its song so far (same, earlier, new): the urn's shares, by part and echo habit."""
    return tables.recall_units(melody_cell_units(songs))


def echo_habit_units(songs) -> list:
    """Each song's echo habit for the tune, one unit a song, with the tempo band and the melody's weight beside."""
    return habits(melody_cell_units(songs))


# --- harmony: the chords by degree, their rhythm in the bar, the cadences and the loop ---

VARIETY = ((1, "one chord"), (3, "few"), (6, "several"), (1e9, "many"))   # distinct chords a song plays
MOTION = ((1 / 3, "static"), (2 / 3, "mixed"), (2, "moving"))            # its share of bars that change chord
NO_CHORD = "(none)"                  # a bar's chord where none sounds


def tonic_sure(song: Song) -> bool:
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


def numeral_of(song: Song, c) -> str:
    """A chord as a numeral in the song's key, its shape kept (I, iv, V7, bVII)."""
    return vocab.numeral(c.root, song.tonic, song.mode, c.shape)


def bar_spans(song: Song) -> list:
    """Each bar's chord span (the one sounding most of it), None where none."""
    return [chord_in(song.chords, a, b) for a, b in song.bars]


def bar_chords(song: Song) -> list[str]:
    """Each bar's chord (the one sounding most of it) as a numeral, NO_CHORD where none."""
    return [numeral_of(song, c) if c is not None else NO_CHORD for c in bar_spans(song)]


BY = ("numeral", "degree", "shape")  # what a chord unit's outcome is: the numeral with its shape, the degree alone, the shape alone


def harmony_habits(names: list) -> tuple[str, str]:
    """A song's variety (distinct chords, VARIETY) and motion (the share of
    its bars changing chord from the bar before, MOTION) from its bars' chords."""
    played = [n for n in names if n != NO_CHORD]
    variety = next(name for top, name in VARIETY if len(set(played)) <= top)
    changes = sum(1 for x, y in zip(played, played[1:]) if x != y)
    motion = habit_of(changes / (len(played) - 1), MOTION) if len(played) > 1 else "static"
    return variety, motion


def form_place(song: Song, i: int) -> str:
    """A part's place in the form: the only, first, middle or last part."""
    n = len(song.parts)
    return "only" if n == 1 else "first" if i == 0 else "last" if i == n - 1 else "middle"


def _own_parts(song: Song):
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
        tempo = band(s.bpm)
        for i, bar, n in _own_parts(s):
            previous, before, form = START, START, form_place(s, i)
            for num in range(bar, bar + n):
                k = index.get(num)
                if k is None:
                    continue
                out.append(tables.Unit(s.sid, s.game, outcomes[k], {
                    "part": R.HARMONY, "mode": s.mode, "meter": s.meter, "tempo": tempo, "previous": previous,
                    "before": before, "place": place_in_part(s, num), "form": form, "habit": variety, "motion": motion,
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
        tempo = band(s.bpm)
        starts = []
        for i, c in enumerate(s.chords):
            if c.root is None or c.fit < FIT:
                continue
            earlier = s.chords[i - 1] if i else None
            if earlier is None or (earlier.root, earlier.shape) != (c.root, c.shape):
                starts.append(c.start)
        previous = START
        for k, (a, b) in enumerate(s.bars):
            where = place_in_part(s, s.numbers[k])
            if where == "first":
                previous = START
            inside = sorted({position(t - a, 2) for t in starts if a - NEAR <= t < b - NEAR})
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
    from . import phrases                                  # phrases imports this module
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


# --- the form: the parts' letters and lengths ---

FORM_SIZES = ((1, "one part"), (4, "a few"), (8, "several"), (1e9, "many"))   # parts a song has
PART_LENGTHS = ((4, "short"), (8, "medium"), (1e9, "long"))                 # a song's median part length, in bars
LONG = 32                            # bars: a part this long or longer is one outcome
KINDS = ("new", "again", "back")     # a part: new material, the part before once more, an earlier part returning
LEVELS = ("part", "section")


def level_parts(song: Song, level: str = "part") -> list:
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
        tempo, previous, seen = band(s.bpm), START, set()
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
        tempo, previous = band(s.bpm), START
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
                               {"part": "form", "meter": s.meter, "tempo": band(s.bpm), "parts": size}))
    return out


# --- the arrangement: which parts play in which bars, the band, the voices, doublings, layered basses ---

ARRANGEMENT = "arrangement"
SILENCE = "(rest)"
OTHERS = ("0", "1", "2", "3+")            # other parts sounding in a bar
PRESENCE = ((0.5, "sparse"), (0.9, "mostly"), (2, "always"))   # a part's share of its song's bars it sounds in
SUSTAIN = 1.0                           # beats a held note must sound into a bar to count the part as playing in it
ECHO = 0.02                             # seconds: a double delayed by more is an echo, else a unison double


def sounding_bars(song: Song, role: str) -> set:
    """The indices of the bars a part sounds in: a note struck in the bar, or
    held into it for SUSTAIN beats or more."""
    out = set()
    starts = [a for a, _ in song.bars]
    for st, length, _, _ in song.notes.get(role, ()):
        k = bisect.bisect_right(starts, st + NEAR) - 1
        if k >= 0 and st < song.bars[k][1] - NEAR:
            out.add(k)
        stop = st + (length if not math.isnan(length) else 0.25)
        j = k + 1
        while j < len(song.bars) and stop > song.bars[j][0] + SUSTAIN:
            out.add(j)
            j += 1
    return out


def _form_of_bars(song: Song) -> dict:
    """Bar number -> its part's place in the form (form_place), for bars inside a part."""
    out = {}
    for i, (bar, n, *_) in enumerate(song.parts):
        for num in range(bar, bar + n):
            out[num] = form_place(song, i)
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
        forms, tempo, previous = _form_of_bars(s), band(s.bpm), START
        for k, num in enumerate(s.numbers):
            where = place_in_part(s, num)
            if where == "first":
                previous = START
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
        forms, tempo = _form_of_bars(s), band(s.bpm)
        for role, bars in plays.items():
            habit = habit_of(len(bars) / len(s.bars), PRESENCE)
            previous = START
            for k, num in enumerate(s.numbers):
                where = place_in_part(s, num)
                if where == "first":
                    previous = START
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
                        {"part": ARRANGEMENT, "meter": s.meter, "tempo": band(s.bpm)}) for s in songs]


def voices_units(songs) -> list:
    """Each song as a unit: its outcome how many voices it uses (the role
    reader's, doubles and rolls included); its values the part (arrangement),
    the size of its band in parts, the meter and the tempo band."""
    return [tables.Unit(s.sid, s.game, str(len(s.voices)),
                        {"part": ARRANGEMENT, "band": min(len(s.notes), 5), "meter": s.meter, "tempo": band(s.bpm)})
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
                                   {"part": part, "band": min(len(s.notes) - (part in s.notes), 4), "tempo": band(s.bpm)}))
    return out


ALL = "all"                           # a part's texture: every part of the band sounds


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
    part in a song of four)."""
    out = []
    for s in songs:
        if not s.notes or not s.parts:
            continue
        plays = {role: sounding_bars(s, role) for role in s.notes}
        index = {num: k for k, num in enumerate(s.numbers)}
        previous = START
        for i, bar, n in _own_parts(s):
            ks = [index[num] for num in range(bar, bar + n) if num in index]
            if not ks:
                continue
            textures = Counter(frozenset(role for role, bars in plays.items() if k in bars) for k in ks)
            modal = textures.most_common(1)[0][0]
            resting = sorted(set(s.notes) - modal)
            outcome = ALL if not resting else "no " + " ".join(resting)
            out.append(tables.Unit(s.sid, s.game, outcome, {"part": ARRANGEMENT, "form": form_place(s, i), "index": min(i + 1, 5), "previous": previous}))
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
            if abs(n[0] - round(n[0])) >= NEAR:
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
    tokens = _tokens(figure)
    if not tokens:
        return False
    marks = [t.partition(":")[2] for t in tokens]
    pieces = set(LETTERS.values())
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
    return int(round(low / REGISTER_BIN)) * REGISTER_BIN, int(round(high / REGISTER_BIN)) * REGISTER_BIN


def balance_units(songs) -> list:
    """Each song as a unit: its outcome its band with, for each pitched
    part, its weight, its register and the share of its gap a note sounds
    ("accompaniment=main:56-68:0.8 bass=half:28-40:0.9 drums
    melody=half:64-84:0.9"); its value the part (arrangement). What a song
    written with no original draws its band, balance and layout from, as
    one of the game's songs has them together: drawn a part at a time, a
    bass sat above the accompaniment and a counter-line two octaves under
    its instrument (the Song Check's notes, 2026-10-23)."""
    out = []
    for s in songs:
        if not s.notes:
            continue
        weights = part_weights(s)
        voices = Counter(role for role, _ in s.voice_notes.values())
        tokens = []
        for role in sorted(s.notes):
            if role not in weights:
                tokens.append(role)
                continue
            reg, share = part_register(s.notes[role], ambitus=role == R.MELODY), sounded_share(s.notes[role])
            tokens.append(f"{role}={weights[role]}" + (f":{reg[0]}-{reg[1]}" if reg else ":") + (f":{round(share / SOUND_BIN) * SOUND_BIN:.1f}" if share is not None else ":")
                          + f":{max(1, voices.get(role, 1))}")
        out.append(tables.Unit(s.sid, s.game, " ".join(tokens), {"part": ARRANGEMENT}))
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
    return out


LAYER_DENSITY = ((0.5, "sparser"), (2.0, "like"), (1e9, "denser"))   # a second voice's strikes against the line's
LAYER_OFFSET = 24                    # semitones: a second voice's register against the line's is kept within this, to REGISTER_BIN


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
    from . import harness                                  # harness imports this module
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
                    offset = int(round(((b[0] + b[1]) - (a[0] + a[1])) / 2 / REGISTER_BIN)) * REGISTER_BIN
                    offset = max(-LAYER_OFFSET, min(LAYER_OFFSET, offset))
                    density = habit_of(len(voices[other]) / max(1, len(voices[line])), LAYER_DENSITY)
                    outcome = f"apart {offset:+d} {density}"
                out.append(tables.Unit(s.sid, s.game, outcome, {"part": role, "rank": str(min(rank, 4))}))
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
