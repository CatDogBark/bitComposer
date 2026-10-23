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
import math
import random
import statistics
from collections import Counter
from fractions import Fraction

from . import harmony, rhythm, roles as R, tables
from .vocab import FIT

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


FREE_STRIKES = {"sparse": (1, 3), "medium": (2, 6), "dense": (5, 16)}   # strikes a bar a free-written part allows, by its habit's density
FREE_HITS = (0, 16)                   # hits a bar a piece may take in a free-written drum bar


class FreeManner:
    """The manner of a part written with no original to follow (a generated
    song's, phase 4): any bar the table knows, on the song's grid, on the
    pieces the song has (drums); the density and the downbeat the habit's
    and the band's, not a bar's own."""

    def __init__(self, known: set, kit: set | None = None, division: int | None = None):
        self.known = known
        self.kit = kit
        self.division = division

    def fits(self, figure: str) -> bool:
        if figure == REST or figure not in self.known:
            return False
        if self.division is not None and not on_grid(figure, self.division):
            return False
        return self.kit is None or all(t.partition(":")[2] in self.kit for t in rhythm._tokens(figure))


def free_envelope(habit: str):
    """An envelope_of for a free-written part: strikes a bar by the habit's density, no downbeat demanded."""
    low, high = FREE_STRIKES.get(habit.split()[0], FREE_STRIKES["medium"])
    return lambda own, meter=None: (low, high, False, meter)


def free_drum_envelope(letters) -> object:
    """An envelope_of for a free-written drum group: any count a piece, no downbeat demanded."""
    pieces = {k: FREE_HITS for k in letters}
    return lambda own, meter=None: (pieces, False, meter)


# --- the upper parts: harmony, accompaniment and arp under the song's own chords (phase 4) ---

UPPER_LOW = 0.1                       # a voice's register: from this quantile of its own notes
UPPER_HIGH = 0.9                      # to this one; a written note is moved by octaves to sit inside it
TONE_MARKS = {"sus": "s"}             # the voicing table's marks as tone() reads them


def stack(marks: list, root: int, shape: str, scale: set, low: int, previous: float | None) -> list[int]:
    """A voicing's tones as midi notes, lowest first: the first mark placed in
    the register nearest the note before, each next the nearest above (a
    close stack; the spread between parts is their voices' own registers)."""
    if not marks:
        return []
    pcs = [tone(root, shape, TONE_MARKS.get(m, m), scale) for m in marks]
    out = [place(pcs[0], low, previous)]
    for pc in pcs[1:]:
        out.append(out[-1] + ((pc - out[-1]) % 12 or 12))
    return out


def in_register(midi: int, register: tuple) -> int:
    """The note moved by octaves into the voice's register (low, high); where the register is under an
    octave and no octave fits, the one just under its ceiling."""
    low, high = register
    while midi > high:
        midi -= 12
    while midi < low:
        midi += 12
    while midi > high:
        midi -= 12
    return midi


UPPER_LOCK = {R.HARMONY: 0.0, R.ACCOMP: 2 / 3, R.ARP: 2 / 3}   # the share of the band's shared hits an upper part strikes (a pad holds through)


MOTION_STEP = {"block": 0, "mixed": 0.5, "arpeggiated": 1}   # how far along the stack a voice moves a strike
CHORD_MARKS = {"R", "3", "5", "7", "sus"}   # a written voicing holds one of these at least: "+" alone is the chord reader's noise
CLASH = (1, 11)                       # semitones (mod 12) a written tone may not sit from a note the tune sounds at the same time


def voiced(outcome: str) -> bool:
    """Whether a voicing from the table may be written: it holds a chord tone (a non-chord tone only beside one)."""
    return bool(set(outcome.split()) & CHORD_MARKS)


def sounding_pcs(line: list, at: float) -> set:
    """The pitch classes a line (start, length, midi, ...) sounds at a time."""
    out = set()
    for n in line:
        length = n[1] if not math.isnan(n[1]) else 0.25
        if n[0] - rhythm.NEAR <= at < n[0] + length - rhythm.NEAR and not math.isnan(n[2]):
            out.add(round(n[2]) % 12)
    return out


def unclashed(midi: int, options: list, tune: set) -> int:
    """The note, or where it sits a semitone from the tune, the nearest of the voicing's other tones that does not."""
    if not tune or not any((midi - pc) % 12 in CLASH for pc in tune):
        return midi
    clear = [m for m in options if not any((m - pc) % 12 in CLASH for pc in tune)]
    return min(clear, key=lambda m: (abs(m - midi), m)) if clear else midi


def upper(song: rhythm.Song, role: str, voices: list, registers: dict, models: dict, rng: random.Random,
          habit: str, richness: str, sounds: float, key: tuple | None = None, hold=(), lock=None,
          motion: str = "block", energy: list | None = None) -> tuple[list, list, list]:
    """An upper part written for the song under its own chords (the module):
    the rhythm from the part's bar table (free of the song's own part), the
    chord tones a span from the voicings mixture, the spread from the widths
    mixture, laid onto the part's voices (lowest first; a lone arp voice
    cycles the tones). `voices`: the part's voices low to high; `registers`:
    voice -> its register (low, high); `models`: rhythm and voicings (Caches).
    Returns the notes [(start, end in beats, midi, voice)], the figures and
    the voicings drawn a bar."""
    lock = lock or {}
    bars = [(a, b, struck) for _, a, b, struck in rhythm.all_bars_of(song, role)]
    own = [rhythm.pattern(p for p, _ in struck) if struck else REST for _, _, struck in bars]
    figures = _free_figures(song, role, models["rhythm"], FreeManner(models["rhythm"].table.vocabulary, division=song.division), own, bars,
                            habit, rng, hold, lock, envelope_of=free_envelope(habit), lock_share=UPPER_LOCK.get(role, 1.0), energy=energy)
    step = MOTION_STEP.get(motion, 0)
    walked = 0.0                                            # how far along the stack the voices have moved (motion)
    tune_line = sorted(song.notes.get(R.MELODY, []) + song.notes.get(R.COUNTER, []))   # what the written part must not clash with
    tonic, mode = key if key else (0, "major")
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]}
    notes, voicings = [], []
    played_v, prev_v = Counter(), None
    last_chord, marks, previous_low = None, ["R", "3", "5"], None
    for k, ((a, b, _), figure) in enumerate(zip(bars, figures)):
        if figure == REST:
            voicings.append(REST)
            continue
        positions = [Fraction(t.partition(":")[0]) for t in rhythm._tokens(figure)]
        bar_voicing = []
        for i, p in enumerate(positions):
            start = a + float(p)
            until = a + float(positions[i + 1]) if i + 1 < len(positions) else b
            c = rhythm._chord_at(song.chords, start)
            chord = (c.root, c.shape) if c is not None and c.root is not None and c.fit >= FIT else last_chord
            if chord is None:
                continue
            if chord != last_chord or not bar_voicing:
                shape = chord[1] or "major"
                v_unit = tables.Unit(song.sid, song.game, "", {"part": role, "shape": shape, "habit": richness, "previous": prev_v or rhythm.START})
                drawn = models["voicings"].draw(v_unit, prev_v, played_v, rng, keep=voiced)
                for _ in range(TRIES):
                    if voiced(drawn):
                        break
                    drawn = models["voicings"].table.draw(models["voicings"].table.context(v_unit), rng, v_unit.values)
                marks = drawn.split() if voiced(drawn) else ["R", "5"]
                played_v[drawn] += 1
                prev_v = drawn
                last_chord = chord
                bar_voicing.append(drawn)
            pitches = stack(marks, chord[0], chord[1], scale, registers[voices[0]][0], previous_low)
            previous_low = float(pitches[0]) if pitches else previous_low
            tune = sounding_pcs(tune_line, start)
            if role == R.ARP and len(voices) == 1:
                midi = in_register(pitches[i % len(pitches)], registers[voices[0]])
                midi = unclashed(midi, [in_register(m, registers[voices[0]]) for m in pitches], tune)
                notes.append((start, start + (until - start) * sounds, float(midi), voices[0]))
                continue
            # the tones onto the voices, lowest first; spare voices double the stack an octave up; spare tones are dropped
            # from the middle; with motion, each voice walks along the stack a step a strike (the voices interlocking)
            stacked = list(pitches)
            while len(stacked) < len(voices):
                stacked.append(stacked[len(stacked) - len(pitches)] + 12)
            if len(stacked) > len(voices):
                stacked = [stacked[0]] + stacked[-(len(voices) - 1):] if len(voices) > 1 else [stacked[0]]
            offset = int(walked) if len(pitches) > 1 else 0
            for j, v in enumerate(voices):
                midi = in_register(pitches[(j + offset) % len(pitches)] if offset else stacked[j], registers[v])
                midi = unclashed(midi, [in_register(m, registers[v]) for m in pitches], tune)
                notes.append((start, start + (until - start) * sounds, float(midi), v))
            walked += step
        voicings.append(" | ".join(bar_voicing) if bar_voicing else REST)
    return notes, figures, voicings


def fits(figure: str, song: rhythm.Song, known: set, cap: int) -> bool:
    """Whether a new figure may be written into the song: a bar some song played, on the song's grid, no denser than cap (Manner refines it)."""
    return figure != REST and figure in known and on_grid(figure, song.division) and len(rhythm._tokens(figure)) <= cap


LOCK_DRUMS = 2 / 3                    # the share of a bar's shared hits a drum group must strike (the readings' two in three)


def locked(figure: str, lock, share: float = 1.0) -> bool:
    """Whether a figure strikes `share` of the positions in lock[0] (all, by default) and none in the beats of lock[1]."""
    if not lock:
        return True
    must, rests = lock
    positions = {Fraction(t.partition(":")[0]) for t in rhythm._tokens(figure)}
    struck = len(must & positions)
    return struck >= share * len(must) - 1e-9 and not any(math.floor(p) in rests for p in positions)


FORM_PERIOD = 4                       # bars: the pattern a free-written part repeats through a part of the form


def form_spans(song: rhythm.Song, own: list) -> list[tuple]:
    """The spans of a part written with no original to follow: the form's
    parts, each a span with a FORM_PERIOD-bar pattern (shorter parts their
    length), a part that repeats an earlier one of the same length copying
    its figures (copy_of: the earlier span's first bar); bars in no part
    their own spans. [(start, length, period, copy_of)]."""
    index = {num: k for k, num in enumerate(song.numbers)}
    out, covered, starts = [], set(), {}
    for i, (bar, n, *rest) in enumerate(song.parts):
        ks = [index[num] for num in range(bar, bar + n) if num in index]
        if not ks:
            continue
        start, length = ks[0], len(ks)
        of = rest[0] if rest else None
        copy_of = starts.get(of) if of is not None and starts.get(of, (None, None))[1] == length else None
        starts[i] = (start, length)
        out.append((start, length, min(FORM_PERIOD, length), copy_of[0] if copy_of else None))
        covered |= set(ks)
    for k in range(len(own)):
        if k not in covered:
            out.append((k, 1, 1, None))
    return sorted(out)


def form_spans_of(song: rhythm.Song):
    return lambda own: form_spans(song, own)


THIN = 0.05                           # the band's energy (against its median) under which a free-written pitched part sits a bar out


def thinned(env: tuple, ratio: float) -> tuple:
    """A free envelope scaled to the band's energy in the bar: the strikes allowed shrink with the band, to one
    where the band is nearly gone (under THIN, the caller rests the bar)."""
    low, high, downbeat, meter = env
    r = min(1.0, max(0.0, ratio))
    return (max(1, round(low * r)), max(1, round(high * r)), downbeat, meter)


def _free_figures(song: rhythm.Song, role: str, model: tables.Cache, manner, own: list, bars: list, habit: str,
                  rng: random.Random, hold=(), lock=None, envelope_of=None, within_of=None, lock_share: float = 1.0,
                  energy: list | None = None) -> list[str]:
    """The figures written for a part with no original to follow (the
    module, phase 4): bar by bar from the song's own mixture, whose recall
    shares carry the games' rate of repeating and returning, each bar in
    the manner, the habit's envelope and the band's lock; a part of the
    form that repeats an earlier one copies its figures; the bars the old
    part rests in rest (the arrangement is not this slice's); the song's
    moments and stops (`hold`) keep the old bar; `energy`, the band's
    energy a bar against its median, thins the part where the band thins
    (a breakdown) and rests it where the band is nearly gone (THIN)."""
    lock = lock or {}
    envelope_of = envelope_of or envelope
    within_of = within_of or within
    meters = [max(1, round(b - a)) for a, b, _ in bars]
    figures, played, previous = [REST] * len(bars), Counter(), None
    for start, length, _, copy_of in form_spans(song, own):
        for i in range(length):
            k = start + i
            if own[k] == REST or (energy is not None and k < len(energy) and energy[k] < THIN):
                figures[k] = REST
                continue
            if copy_of is not None and figures[copy_of + i] != REST:
                figures[k] = figures[copy_of + i]
            elif k in hold:
                figures[k] = own[k]
            else:
                env = envelope_of(own[k], meters[k])
                if energy is not None and k < len(energy) and energy[k] < 1.0:
                    env = thinned(env, energy[k])
                values = {"part": role, "meter": meters[k], "previous": previous or rhythm.START, "habit": habit}
                unit = tables.Unit(song.sid, song.game, "", values)
                # the filters, loosened in turn where nothing passes: the manner, the envelope and the lock; then
                # without the envelope (the band asks more strikes than the habit); then the manner alone. Never the
                # song's own bar: a free-written part copies nothing of the part it replaces.
                ladder = [lambda f, _k=k, _e=env: manner.fits(f) and within_of(f, _e) and locked(f, lock.get(_k), lock_share),
                          lambda f, _k=k: manner.fits(f) and locked(f, lock.get(_k), lock_share),
                          lambda f, _e=env: manner.fits(f) and within_of(f, _e),
                          manner.fits]
                figure = None
                for fit in ladder:
                    candidate = model.draw(unit, previous, played, rng, keep=fit)
                    for _ in range(TRIES):
                        if fit(candidate):
                            figure = candidate
                            break
                        candidate = model.table.draw(model.table.context(unit), rng, values)
                    if figure is not None:
                        break
                figures[k] = figure if figure is not None else model.table.draw(model.table.context(unit), rng, values)
            played[figures[k]] += 1
            previous = figures[k]
    return figures


def _figures(song: rhythm.Song, role: str, model: tables.Cache, manner, own: list, bars: list, habit: str,
             rng: random.Random, hold=(), lock=None, chord_at=None, reuse: float = 0.0,
             envelope_of=None, within_of=None, lock_share: float = 1.0) -> list[str]:
    """The figures written for a part, one a bar (the module): drawn as the
    song's own mixture, in its manner, each bar's envelope and lock, a
    pattern a span, the song's moments its own; `chord_at` and `reuse` let
    a bar on a chord its span had take that bar's figure again (the bass)."""
    lock = lock or {}
    envelope_of = envelope_of or envelope
    within_of = within_of or within
    meters = [max(1, round(b - a)) for a, b, _ in bars]
    state = {"previous": None, "played": Counter()}

    def draw(env, keep=None, fallback: str = "0:R", at: int | None = None) -> str:
        """One new figure from the song's mixture, in its manner, the bar's
        envelope and its lock (and passing `keep`), the chain and the urn
        moved on. Nothing passing in TRIES draws: one in the manner, envelope
        and lock alone, else the fallback (the song's own bar, where the
        caller gives it)."""
        previous = state["previous"]
        meter = env[-1] if env[-1] else song.meter
        fit = lambda f: manner.fits(f) and within_of(f, env) and locked(f, lock.get(at), lock_share)   # noqa: E731
        full = lambda f: fit(f) and (keep is None or keep(f))   # noqa: E731
        values = {"part": role, "meter": meter, "previous": previous or rhythm.START, "habit": habit}
        unit = tables.Unit(song.sid, song.game, "", values)
        figure = model.draw(unit, None if previous == REST else previous, state["played"], rng, keep=full)
        nearly = None
        for _ in range(TRIES):                              # the urn or the floor may still hand back what is refused
            if full(figure):
                return figure
            if nearly is None and fit(figure):
                nearly = figure
            figure = model.table.draw(model.table.context(unit), rng, values)
        return nearly or fallback

    figures, patterns = [REST] * len(bars), []
    for start, length, period in spans([rhythm_of(f) for f in own]):
        if length == 1:
            if own[start] != REST:
                last = rhythm_of(figures[start - 1]) if start else None    # the song changes here: so does the written bar
                figures[start] = draw(envelope_of(own[start], meters[start]), keep=lambda f: rhythm_of(f) != last, fallback=own[start], at=start)
                state["played"][figures[start]] += 1
            state["previous"] = figures[start]
            continue
        exact = all(own[j] == own[j - period] for j in range(start + period, start + length))
        before = patterns[-1] if patterns else []
        earlier = [x for x in patterns[:-1] if x != before]
        if earlier and rng.random() < EARLIER:
            pattern = rng.choice(earlier)
        else:
            pattern = []
            for k in range(period):
                avoid = {rhythm_of(f) for f in before + pattern}
                pattern.append(draw(envelope_of(own[start + k], meters[start + k]), keep=lambda f: rhythm_of(f) not in avoid, fallback=own[start + k], at=start + k))
                state["previous"] = pattern[-1]
        patterns.append(pattern)
        seen = {}                                           # the span's chords -> the figure written on each
        for i in range(length):
            base = pattern[i % len(pattern)]
            chord = chord_at(start + i) if chord_at else None
            if own[start + i] == REST:
                figure = REST
            elif exact and locked(base, lock.get(start + i), lock_share):
                figure = base
            elif chord is not None and chord in seen and rhythm_of(seen[chord]) == rhythm_of(base) and locked(seen[chord], lock.get(start + i), lock_share) and rng.random() < reuse:
                figure = seen[chord]                        # the same chord again: the same figure, as the readings' basses do
            else:
                want = rhythm_of(base)
                figure = draw(envelope_of(own[start + i], meters[start + i]), keep=lambda f: rhythm_of(f) == want, fallback=own[start + i], at=start + i)
                if rhythm_of(figure) != want and locked(base, lock.get(start + i), lock_share):
                    figure = base
            if chord is not None and figure != REST:
                seen.setdefault(chord, figure)
            figures[start + i] = figure
            if figure != REST:
                state["played"][figure] += 1
            state["previous"] = figure
    for k in hold:                                          # the song's moments: its own bar
        if 0 <= k < len(figures) and own[k] != REST:
            figures[k] = own[k]
    return figures


def drums(song: rhythm.Song, models: dict, rng: random.Random, hold=(), locks=None, habit: str | None = None,
          free: bool = False) -> tuple[list[tuple[float, str]], list[str]]:
    """The drums written for the song, a group of pieces at a time (the
    module): `models` maps a group (a tuple of letters, rhythm.DRUM_GROUPS)
    to its Cache; `locks` a group to its lock; `hold` as bass(). `free`: no
    original to follow (FreeManner, free_drum_envelope), the `habit` given
    (drawn from a pack's table) and the kit the song's pieces. Returns the
    hits (start in beats, piece letter) and the merged figures."""
    locks = locks or {}
    bars = [(a, b, struck) for _, a, b, struck in rhythm.all_bars_of(song, R.DRUMS)]
    whole = [rhythm.drum_figure(struck, song) if struck else REST for a, _, struck in bars]
    kit = {rhythm.LETTERS.get(piece, "o") for piece in song.pieces.values() if piece and piece != "none"}
    merged = [[] for _ in bars]
    for letters, model in models.items():
        own = [rhythm.drum_group(f, letters) for f in whole]
        if all(f == REST for f in own) and not (free and kit & set(letters)):
            continue
        if free:
            manner = FreeManner(model.table.vocabulary, kit & set(letters), song.division)
            group_habit = habit or "medium mixed"
            envelope_of = free_drum_envelope(kit & set(letters))
        else:
            manner = DrumManner(None, model.table.vocabulary, figures=[f for f in own if f != REST])
            mine = [u for u in rhythm.drum_group_units([song], letters)]
            group_habit = habit or (mine[0].values["habit"] if mine else "medium mixed")
            envelope_of = drum_envelope
        if free:
            figures = _free_figures(song, "drums-" + "".join(letters), model, manner, own, bars, group_habit, rng, hold,
                                    locks.get(letters), envelope_of=envelope_of, within_of=drum_within, lock_share=LOCK_DRUMS)
        else:
            figures = _figures(song, "drums-" + "".join(letters), model, manner, own, bars, group_habit, rng, hold, locks.get(letters),
                               envelope_of=envelope_of, within_of=drum_within, lock_share=LOCK_DRUMS)
        for k, f in enumerate(figures):
            merged[k] += [(Fraction(t.partition(":")[0]), t.partition(":")[2]) for t in rhythm._tokens(f)]
    figures = [" ".join(f"{p}:{x}" for p, x in sorted(set(tokens))) or REST for tokens in merged]
    hits = []
    for (a, b, _), figure in zip(bars, figures):
        for t in rhythm._tokens(figure):
            at, _, letter = t.partition(":")
            if a + float(Fraction(at)) < b:
                hits.append((a + float(Fraction(at)), letter))
    return hits, figures


def bass(song: rhythm.Song, model: tables.Cache, rng: random.Random, habit: str | None = None,
         key: tuple | None = None, hold=(), lock=None, free: bool = False, energy: list | None = None) -> tuple[list[tuple[float, float, float]], list[str]]:
    """The bass written for the song: its notes (start, end in beats, midi)
    and the figures drawn, one a bar; the bars in `hold` (indices among the
    song's bars) keep the song's own figure; `lock` maps a bar's index to
    (positions a figure must strike, beats it must leave), the song's own
    locking to the band. `free`: no original to follow (FreeManner,
    free_envelope by the habit, which the caller then gives)."""
    lock = lock or {}
    own = song.notes.get(R.BASS, [])
    if habit is None:
        mine = rhythm.bass_units([song])
        habit = mine[0].values["habit"] if mine else "medium roots no-octaves"
    manner = FreeManner(model.table.vocabulary, division=song.division) if free else Manner(song, R.BASS, model.table.vocabulary)
    pitched = sorted(n[2] for n in own if not math.isnan(n[2]))
    low = round(pitched[int(LOW * (len(pitched) - 1))]) if pitched else 36
    sounds = sounded(own)
    tonic, mode = key if key else (0, "major")
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]}
    bars = [(a, b, struck) for _, a, b, struck in rhythm.all_bars_of(song, R.BASS)]
    own = [rhythm.figure(struck, a, song) if struck else REST for a, _, struck in bars]

    def chord_at(k):
        c = rhythm._chord_at(song.chords, bars[k][0])
        return (c.root, c.shape) if c is not None and c.root is not None and c.fit >= FIT else None

    words = habit.split()
    if free:
        figures = _free_figures(song, R.BASS, model, manner, own, bars, habit, rng, hold, lock, envelope_of=free_envelope(habit), energy=energy)
    else:
        figures = _figures(song, R.BASS, model, manner, own, bars, habit, rng, hold, lock,
                           chord_at=chord_at, reuse=REUSE.get(words[1] if len(words) > 1 else "", 0.5))
    notes, last_root, previous = [], tonic, None
    for (a, b, _), figure in zip(bars, figures):
        new, last_root, previous = realize(figure, a, b, song, low, sounds, scale, last_root, previous)
        notes += new
    return notes, figures


def place(pc: int, low: int, previous: float | None, octave_up: bool = False) -> int:
    """The midi note of a pitch class in the register: the octave nearest the
    note before (the lower when as near), the lowest with no note before;
    an octave up (r) is the lowest placing raised an octave."""
    bottom = low + (pc - low) % 12
    if octave_up:
        return bottom + 12
    if previous is None:
        return bottom
    options = [m for m in range(bottom, low + REACH + 1, 12)] or [bottom]
    return min(options, key=lambda m: (abs(m - previous), m))


def passing(previous: float | None, toward: int | None, scale: set, low: int, root: int) -> int:
    """A passing tone: a scale step from the note before, toward the next
    note where there is one (a semitone where the scale has no step that
    way), else on in the line's last direction; the step above the root
    where nothing came before."""
    if previous is None:
        return place(tone(root, "", "+", scale), low, None)
    direction = 1 if toward is None or toward >= previous else -1
    for d in (1, 2):
        m = round(previous) + direction * d
        if m % 12 in scale:
            return m
    return round(previous) + direction


def realize(figure: str, a: float, b: float, song: rhythm.Song, low: int, sounds: float, scale: set,
            last_root: int, previous: float | None = None) -> tuple[list, int, float | None]:
    """A figure's tokens as notes in the bar [a, b) (see the module); returns
    them, the last chord root used and the last note's midi."""
    tokens = [(Fraction(t.partition(":")[0]), t.partition(":")[2]) for t in rhythm._tokens(figure)]
    chords = []
    for p, _ in tokens:
        c = rhythm._chord_at(song.chords, a + float(p))
        if c is not None and c.root is not None and c.fit >= FIT:
            last_root, shape = c.root, c.shape
        else:
            shape = ""
        chords.append((last_root, shape))
    out, direction = [], 1
    for i, (p, mark) in enumerate(tokens):
        start = a + float(p)
        until = a + float(tokens[i + 1][0]) if i + 1 < len(tokens) else b
        if until <= start:
            continue
        root, shape = chords[i]
        if mark == "+":
            toward = None
            for j in range(i + 1, len(tokens)):                 # the next note of the bar that is not itself passing
                if tokens[j][1] != "+":
                    toward = place(tone(chords[j][0], chords[j][1], tokens[j][1], scale), low, previous, tokens[j][1] == "r")
                    break
            if toward is None and previous is not None:
                toward = round(previous) + direction * 2
            midi = passing(previous, toward, scale, low, root)
        else:
            midi = place(tone(root, shape, mark, scale), low, previous, mark == "r")
        if previous is not None and midi != previous:
            direction = 1 if midi > previous else -1
        out.append((start, start + (until - start) * sounds, float(midi)))
        previous = float(midi)
    return out, last_root, previous


def tone(root: int, shape: str, mark: str, scale: set) -> int:
    """The pitch class a figure's mark names in a chord (the module)."""
    ivs = harmony.SHAPES.get(shape, harmony.SHAPES[""])
    pick = lambda options, default: next((i for i in options if i in ivs), default)   # noqa: E731
    if mark == "3":
        i = pick((3, 4), 4)
    elif mark == "5":
        i = pick((7, 6, 8), 7)
    elif mark == "7":
        i = pick((10, 11), 10)
    elif mark == "s":
        i = pick((5, 2), 5)
    elif mark == "+":
        i = 2 if (root + 2) % 12 in scale else 10 if (root + 10) % 12 in scale else 2
    else:                                                   # R, r, ?
        i = 0
    return (root + i) % 12


def sounded(notes) -> float:
    """The share of its gap to the next note a part's note sounds, the median over the part (within SOUNDS)."""
    line = sorted(n for n in notes if not math.isnan(n[1]))
    shares = [min(1.0, n[1] / (m[0] - n[0])) for n, m in zip(line, line[1:]) if m[0] - n[0] > rhythm.NEAR]
    return min(SOUNDS[1], max(SOUNDS[0], statistics.median(shares))) if shares else 0.8
