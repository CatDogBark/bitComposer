"""A part written from the tables into a real song, in place of the song's
own (phase 3's acceptance by ear, docs/idiom/phase-3-tables.md): the bass,
and the drums the same way (DrumManner, drums()): the drums' figures are
each hit's position and piece, written a limb at a time (rhythm.DRUM_GROUPS:
kick, snare and tom as one line, the hat as another, cymbals and the rest
each their own, since a whole kit's bar is too particular a figure for
any inventory to hold many of, and a kit is what its limbs do together),
each group from its own inventory over the readings, in the song's own
manner for that group (the positions it strikes, the pieces it has), the
envelope each bar's own piece by piece (a bar's strikes of each piece
stay within TIGHT of the song's own bar's, so a snare roll never stands
in for the hat), the spans and moments and locking as the bass's; a hit's voice, sample and
length are the harness's, from the song's own kit.

The song is one of the readings (rhythm.load's Song: its bars and chords
in beats, its parts' notes); the table is fitted on every other song in
the database, so the song never votes for its own bars; the habit is the
song's own, read from its bass (the generator's writer draws one from the
habits table); then bar by bar a figure is drawn as the song's own
mixture over the table (tables.Cache: the figure before again, one the
song played earlier, or a new one under the part, the meter, the habit
and the figure before, in that order, so a figure never seen after this
one backs off to the habit's own inventory, not the pooled one). A new
figure must be a bar some song played (the floor serves the likelihood,
not the writer: its invented bars were the runs the listener heard in
Terra) and must be in the song's own manner, read from its bass (Manner),
and within the song's own bar (envelope): striking between TIGHT times
as often as the song's bass does in that bar, and the downbeat where
that bar does (a song-wide window let Locke's one-note intro bars
license a one-note bar where its line starts walking, and its busiest
bar license sixteenths everywhere; density is the arrangement's, bar by
bar, like the rests and the volume); placed only on positions in the bar
the song's bass strikes in RARE of its strikes or more (its feel: Terra
strikes quarters and triplets, so a sixteenth pickup was the listener's
"burst"; The Decisive Battle's riff strikes the and-a before beats one
and three and never the and of two, so straight eighths were his "free
spirited"); and in the song's tones as much as its rhythm: no
octave-up roots where the song plays none, as many different tones in a
bar as the song's own bars have (Terra's one, Locke's one to four), the
roots' share of a bar and the roots and fifths' share each within the
song's own bars' range (by MARGIN; Terra's third span came back as a
pedal on the fifth under a bass that plays nothing but roots), and a bar
on one tone struck PEDAL times or more only where PEDAL_SHARE of the
song's own such bars are (Locke's walking bass came back as sixteen
fifths in a row). Where the song's own bass changes its rhythm bar to
bar (a bar in no span), the written bar changes its rhythm from the one
before too, since the song's mixture would otherwise bring one figure
back again and again.

A bass holds its figures over spans and changes with the music, which a
bar drawn at a time cannot do (the listener: "no section awareness, no
throughline"). Over the readings' 1,324 basses, 63 % of the bars sit in a
span repeating a rhythm with a period of one, two or four bars (spans of
6.6 bars on average), and a new span's rhythm is one an earlier span had
in 35 % of cases (EARLIER). So the writer reads the song's own spans from
its bass (by rhythm, marks dropped: a walking bass keeps its rhythm and
moves its tones) and writes a pattern a span: one of an earlier span's
patterns with EARLIER's chance (never the one just before), else as
many new figures as the span's period, their rhythms differing from one
another and from the pattern before (a span's figures alternate, and a
new span is a change, by construction), held through the span; where
the song's own span repeats its
figures exactly, the pattern repeats exactly, and where only the rhythm
repeats, each bar is drawn anew with the pattern's rhythm, so the tones
move, except that a bar on a chord an earlier bar of the span had takes
that bar's figure again with REUSE's chance (the readings' basses repeat
their figure on a repeated chord inside a span 53 % of the time walking,
59 % root-fifth, 73 % roots). A bar in no span is drawn on its own. A
new figure uses only the marks the song's own bass uses in RARE of its
notes or more (The Decisive Battle came back with sus tones it plays
once). The bars the song's own bass
rests through are left silent and never drawn for (the arrangement stays
the song's: which bars the bass plays is the arrangement table's, not
this one's), and a playing bar never draws a rest; so are the song's
moments: a bar the caller names in `hold` (the harness: a bar where the
other parts' energy drops under MOMENT of the song's median, The
Decisive Battle's regear at 18 s, which the written bass "blasted
through") keeps the song's own figure, since what a bass does in a break
is the song's choice (over the readings' breaks it keeps its figure in
35 %, rests in 32 %, thins in 27 %); and so is its locking to the band: at
a shared hit (a position where most of the other playing parts strike
together) the readings' basses strike too two times in three, and on a
stop (a beat no other part sounds in) they rest two times in three, so
where the song's own bass does either, the written one must (`lock`: a
bar's positions it must strike and beats it must leave). Each token
becomes a note:
its pitch the chord tone its mark names in the chord sounding at its
onset (R the root, r the root an octave up, 3 5 7 the chord's own, s the
sus tone, ? the root; no chord fitting, the last root, or the tonic),
in the octave nearest the note before it; a passing tone (+) passes: a
scale step from the note before toward the next note of the bar, or on
in the line's direction (over the readings' basses a passing tone is a
step from its neighbour far more often than the second over the root,
which is where the first writer put every one), the key's step above the
root with no note before;
within the song's own bass register (from the lowest tenth of its bass
notes up to REACH above it, the first note lowest), so a walking line
walks (placed in a fixed octave, Locke's leapt by thirds and fifths
where its own moves by step); its length to the next onset in
the bar or the bar's end, sounding the share of that the song's bass
sounds of its own gaps (the median, between SOUNDS). A bar of another
length than the meter's is written too, with the table's figures for
that many beats (the readings hold 3/4 and 2/4 songs) or, where nothing
fits, the song's own bar: the first writer left such bars silent, and
Johnny C. Bad's bass vanished for four bars the beat reader had put in
3/4 and came back in at the song's stop-time.
"""
from __future__ import annotations
import math
import random
from types import SimpleNamespace
import statistics
from collections import Counter
from fractions import Fraction

from .. import harmony, phrases, rhythm, roles as R, tables
from ..vocab import FIT

from . import upper as upper_mod, tune as tune_mod, parts as parts_mod   # noqa: E402  the package's other sections


SHAPE = ("part", "meter", "habit", "previous")   # the bass table's shape, the habit before the chain (the module)
REST = "-"
DISCOUNT = 0.75
LOW = 0.1                             # the register's floor: this quantile of the song's own bass notes
REACH = 16                            # semitones above the floor a note may go (an octave and a third)
SLACK = 1                             # strikes: how far outside the middle half of the song's own bars (Manner's window, reported)
TIGHT = (0.5, 1.5)                    # a written bar strikes between these multiples of the song's own bar (envelope)
DOWNBEAT = 0.9                        # the song's bass striking the one in this share of its bars: a new figure must too
ANCHORS = {"R", "r", "5"}             # the marks that anchor a bar: roots and fifths
ROOTS = {"R", "r"}
MARGIN = 0.15                         # how far a figure's anchor share may stray outside the song's own bars' range
PEDAL = 4                             # strikes: a bar on one tone this long is a pedal
PEDAL_SHARE = 0.25                    # the song's own bars of PEDAL strikes or more that are pedals, for a new one to be
RARE = 0.02                           # a mark under this share of the song's own notes is not the song's: a new figure leaves it out
REUSE = {"walking": 0.53, "root-fifth": 0.59, "roots": 0.73}   # the chance a bar on a chord its span had takes that bar's figure
PERIODS = (1, 2, 4)                   # bars: the periods a span may repeat with
EARLIER = 0.35                        # a new span's chance of taking a pattern an earlier span had (the readings' basses, by rhythm)
TRIES = 40                            # draws before the writer gives up on a constraint
SOUNDS = (0.3, 1.0)                   # the sounded share of a note's gap is kept within these


def fit(units, floor_cls=rhythm.BarCells, shape=SHAPE, name: str = "bass") -> tables.Cache:
    """The model the writer draws from, fitted on these units (the song written for left out by the caller)."""
    units = list(units)
    return tables.Cache.fit(units, shape, name=name, votes=tables.SHARES, floor=floor_cls(units), discount=DISCOUNT,
                            covers=len(floor_cls.COVERS))


def on_grid(figure: str, division: int) -> bool:
    """Whether a figure's positions all sit on a grid of this many steps a beat."""
    return all(division % Fraction(t.partition(":")[0]).denominator == 0 for t in rhythm._tokens(figure))


class Manner:
    """The song's own manner in a part, read from its bars (the module):
    the strikes a bar it allows a new figure (low, high), whether the
    figure must strike the downbeat, the subdivisions of the beat it may
    use (feel), and its tones: whether it plays octave-up roots, how many
    different tones a bar (tones), the share of a bar's strikes on roots
    (roots) and on roots and fifths (anchors), and whether a bar may sit
    on one tone (pedal)."""

    def __init__(self, song: rhythm.Song, role: str, known: set, figure_of=None):
        self.known = known
        figure_of = figure_of or rhythm.figure
        bars = [(a, struck) for a, struck in rhythm.bars_of(song, role) if struck]
        counts = [len(struck) for _, struck in bars]
        q1, _, q3 = statistics.quantiles(counts, n=4) if len(counts) >= 2 else (counts[0], counts[0], counts[0]) if counts else (4, 4, 4)
        self.low = max(1, math.ceil(q1) - SLACK)
        self.high = max(self.low, math.floor(q3) + SLACK)
        self.downbeat = bool(bars) and sum(1 for _, struck in bars if struck[0][0] == 0) / len(bars) >= DOWNBEAT
        struck_at = Counter(p for _, struck in bars for p, _ in struck)
        strikes = sum(struck_at.values())
        self.feel = {p for p, c in struck_at.items() if c / strikes >= RARE} | {Fraction(0)} if strikes else set()
        marks = [[t.partition(":")[2] for t in rhythm._tokens(figure_of(struck, a, song))] for a, struck in bars]
        full = [m for m in marks if len(m) >= 2]
        self.octaves = any("r" in m for m in marks)
        self.tones = (min(len(set(m)) for m in full), max(len(set(m)) for m in full)) if full else (1, 4)
        shares = [sum(1 for x in m if x in ANCHORS) / len(m) for m in full]
        self.anchors = (min(shares), max(shares)) if shares else (0.0, 1.0)
        shares = [sum(1 for x in m if x in ROOTS) / len(m) for m in full]
        self.roots = (min(shares), max(shares)) if shares else (0.0, 1.0)
        long = [m for m in marks if len(m) >= PEDAL]
        self.pedal = not long or sum(1 for m in long if len(set(m)) == 1) / len(long) >= PEDAL_SHARE
        counts = Counter(x for m in marks for x in m)
        total = sum(counts.values())
        self.marks = ({x for x, c in counts.items() if c / total >= RARE} | {"R"}) if total else {"R", "r", "3", "5", "7", "s", "+", "?"}

    def fits(self, figure: str) -> bool:
        """Whether a new figure is in the song's manner (the module): a bar some
        song played, in the song's feel and tones (its density and downbeat
        are the bar's own: envelope and within)."""
        if figure == REST or figure not in self.known:
            return False
        tokens = [t.partition(":") for t in rhythm._tokens(figure)]
        positions = [Fraction(t[0]) for t in tokens]
        marks = [t[2] for t in tokens]
        if not all(p in self.feel for p in positions):
            return False
        if not self.octaves and "r" in marks:
            return False
        if any(m not in self.marks for m in marks):
            return False
        distinct = len(set(marks))
        if len(marks) >= 2 and not (self.tones[0] <= distinct <= self.tones[1]):
            return False
        for which, span in ((ANCHORS, self.anchors), (ROOTS, self.roots)):
            share = sum(1 for m in marks if m in which) / len(marks)
            if len(marks) >= 2 and not (span[0] - MARGIN <= share <= span[1] + MARGIN):
                return False
        return self.pedal or len(marks) < PEDAL or distinct > 1


def rhythm_of(figure: str) -> str:
    """A figure's rhythm alone: its positions, the marks dropped."""
    return " ".join(t.partition(":")[0] for t in rhythm._tokens(figure)) or REST


def spans(keys: list) -> list[tuple[int, int, int]]:
    """Maximal runs where the keys repeat with the smallest period in PERIODS
    that fits (at least two periods long): [(start, length, period)]; a bar
    in no run is its own span of length 1."""
    out, i, n = [], 0, len(keys)
    while i < n:
        best = None
        for p in PERIODS:
            if i + p > n:
                break
            j = i + p
            while j < n and keys[j] == keys[j - p]:
                j += 1
            if j - i >= 2 * p and (best is None or j - i > best[1]):
                best = (p, j - i)
        if best is None:
            out.append((i, 1, 1))
            i += 1
        else:
            out.append((i, best[1], best[0]))
            i += best[1]
    return out


def envelope(own: str, meter: int | None = None) -> tuple:
    """What the song's own bar allows a written one: strikes between TIGHT
    times its own, the downbeat where it strikes it, and (meter given)
    positions inside the bar's length."""
    n = len(rhythm._tokens(own))
    return (max(1, math.ceil(TIGHT[0] * n)), max(1, math.floor(TIGHT[1] * n)), own.startswith("0:") or own == "0", meter)


def drum_envelope(own: str, meter: int | None = None) -> tuple:
    """What the song's own drum bar allows a written one: each piece's strikes
    between TIGHT times its own (a piece the bar lacks: none), the downbeat
    where it strikes it, positions inside the bar."""
    counts = Counter(t.partition(":")[2] for t in rhythm._tokens(own))
    return ({k: (max(1, math.ceil(TIGHT[0] * c)), max(1, math.floor(TIGHT[1] * c))) for k, c in counts.items()},
            own.startswith("0:"), meter)


def drum_within(figure: str, env: tuple) -> bool:
    """Whether a drum figure is within the bar's envelope, piece by piece."""
    pieces, downbeat, meter = env
    tokens = [t.partition(":") for t in rhythm._tokens(figure)]
    counts = Counter(t[2] for t in tokens)
    if any(k not in pieces for k in counts) or any(not (lo <= counts.get(k, 0) <= hi) for k, (lo, hi) in pieces.items()):
        return False
    if downbeat and not any(t[0] == "0" for t in tokens):
        return False
    return meter is None or all(Fraction(t[0]) < meter for t in tokens)


def within(figure: str, env: tuple) -> bool:
    """Whether a figure is within the bar's envelope."""
    tokens = rhythm._tokens(figure)
    low, high, downbeat, meter = (env + (None,))[:4]
    if not (low <= len(tokens) <= high and (not downbeat or (bool(tokens) and tokens[0].partition(":")[0] == "0"))):
        return False
    return meter is None or all(Fraction(t.partition(":")[0]) < meter for t in tokens)


class DrumManner:
    """The song's own manner in its drums (or one group of them): the
    positions it strikes (feel) and the pieces it has (kit), each in RARE of
    its hits or more; from the song, or from a list of its own figures."""

    def __init__(self, song: rhythm.Song | None, known: set, figures=None):
        self.known = known
        if figures is None:
            figures = [rhythm.drum_figure(struck, song) for _, struck in rhythm.bars_of(song, R.DRUMS) if struck]
        tokens = [t.partition(":") for f in figures for t in rhythm._tokens(f)]
        n = len(tokens)
        at = Counter(Fraction(t[0]) for t in tokens)
        pieces = Counter(t[2] for t in tokens)
        self.feel = ({p for p, c in at.items() if c / n >= RARE} | {Fraction(0)}) if n else set()
        self.kit = {x for x, c in pieces.items() if c / n >= RARE} if n else set()

    def fits(self, figure: str) -> bool:
        """Whether a new figure is in the song's manner: a bar some song played, on the song's positions, with its pieces."""
        if figure == REST or figure not in self.known:
            return False
        tokens = [t.partition(":") for t in rhythm._tokens(figure)]
        return all(Fraction(t[0]) in self.feel and t[2] in self.kit for t in tokens)


FREE_STRIKES = (1, 64)                # strikes a bar a free-written part allows: any bar the table gives (the habit conditions the
                                      # table already; a second envelope by the habit's density, sparse 1-3 / medium 2-6 / dense 5-16,
                                      # had cut a dense-habit accompaniment to three distinct bars in 32 where the table alone gives
                                      # five to nine, FFVI's eight: docs/idiom/phase-4-writing.md, the integration)
FREE_HITS = (0, 16)                   # hits a bar a piece may take in a free-written drum bar


class FreeManner:
    """The manner of a part written with no original to follow (a generated
    song's, phase 4): any bar the table knows, on the song's grid, on the
    pieces the song has (drums); the density and the downbeat the habit's
    and the band's, not a bar's own."""

    def __init__(self, known: set, kit: set | None = None, division: int | None = None, rests: bool = False):
        self.known = known
        self.kit = kit
        self.division = division
        self.rests = rests                                  # a rested bar may be drawn (a drum group of a planned song rests at its own rate)

    def fits(self, figure: str) -> bool:
        if figure == REST:
            return self.rests
        if figure not in self.known:
            return False
        if self.division is not None and not on_grid(figure, self.division):
            return False
        return self.kit is None or all(t.partition(":")[2] in self.kit for t in rhythm._tokens(figure))


def free_envelope(habit: str):
    """An envelope_of for a free-written part: any strikes a bar (FREE_STRIKES: the habit conditions the table), no downbeat demanded."""
    low, high = FREE_STRIKES
    return lambda own, meter=None: (low, high, False, meter)


ANY_TONE = -1                         # upper(tone_index=ANY_TONE): a voice beside the line takes any tone of the line's voicing but its own, drawn a span
VOICE_KINDS = ("apart", "alternating")   # the relations of a voice beside the line whose pitches the voice_intervals/voice_moves tables give
VOICE_TRIES = 4                       # draws a voice beside the line gets before an onset whose every pitch another voice holds is skipped
DENSITY_CAPS = {"sparse": 2, "medium": 6, "dense": FREE_HITS[1]}   # a drum group's hits a bar at its density tier's top (rhythm.DENSITIES)


def group_caps(habit) -> dict:
    """Per-letter hit caps from a plan's drum group habits ({group letters: "sparse mixed", ...}): a group of one letter
    (the hat, the cymbals, the rest) caps its letter at its density tier's top. The kit drawn as one figure had drawn
    its bars under the kit's habit alone, and a plan's "sparse" cymbals came up as a ride in sixteenths in five
    songs of twenty (FFVI: four of 67)."""
    caps = {}
    if isinstance(habit, dict):
        for letters, h in habit.items():
            if len(letters) == 1 and isinstance(h, str) and h.split():
                caps[letters[0]] = DENSITY_CAPS.get(h.split()[0], FREE_HITS[1])
    return caps


def free_drum_envelope(letters, caps: dict | None = None) -> object:
    """An envelope_of for a free-written drum group: any count a piece (or the cap the group's habit sets), no downbeat
    demanded."""
    pieces = {k: (0, (caps or {}).get(k, FREE_HITS[1])) for k in letters}
    return lambda own, meter=None: (pieces, False, meter)
