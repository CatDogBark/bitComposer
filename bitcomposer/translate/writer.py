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
from types import SimpleNamespace
import statistics
from collections import Counter
from fractions import Fraction

from . import harmony, phrases, rhythm, roles as R, tables
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
CHORD_MARKS = {"R", "3", "5", "7", "sus"}   # a written voicing holds one of these at least, and only these are realized: the
                                      # table's "+" is mostly the chord reader's noise (Terra's own accompaniment plays 4 % other)
CLASH = (1, 11)                       # semitones (mod 12) a written tone may not sit from a note the tune sounds at the same time


RICH_TONES = {"thin": 1, "full": 2, "rich": 3}   # chord tones a written voicing holds at least, by the richness habit
PEDAL_VOICE = 2                       # semitones: a voice whose own register is this narrow or narrower is a pedal and keeps its note


def voiced(outcome: str, tones: int = 1) -> bool:
    """Whether a voicing from the table may be written: it holds `tones` chord
    tones at least (the table's "+" counts for nothing: it is mostly the chord
    reader's noise, and realized it was a ninth in every strum)."""
    return len(set(outcome.split()) & CHORD_MARKS) >= tones


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
          motion: str = "block", energy: list | None = None, pedals: dict | None = None,
          plays: list | None = None, figures: list | None = None, shared: dict | None = None,
          tone_index: int = 0, kind: str | None = None) -> tuple[list, list, list]:
    """An upper part written for the song under its own chords (the module):
    the rhythm from the part's bar table (free of the song's own part), the
    chord tones a span from the voicings mixture, the spread from the widths
    mixture, laid onto the part's voices (lowest first; a lone arp voice
    cycles the tones). `voices`: the part's voices low to high; `registers`:
    voice -> its register (low, high); `pedals`: voice -> the note a pedal
    voice (a register PEDAL_VOICE semitones or narrower) holds; `models`:
    rhythm and voicings (Caches); `figures`: the bars given (a second line's,
    drawn under the line's own bars from the second_figures table) instead
    of drawn here; `shared`: the part's voicing at each (bar, position),
    filled by the line's call (tone_index 0) and read by a voice beside it
    (tone_index 1, 2...); `kind`: that voice's relation to the line (apart,
    alternating): with the voice_intervals and voice_moves tables it takes
    its interval to the line's note where they strike together and its own
    move where it strikes alone, drawn (the line's notes are in `shared`
    under ("line", (bar, position))); without them, the tone that many
    steps up the line's voicing.
    Returns the notes [(start, end in beats, midi, voice)], the figures and
    the voicings drawn a bar."""
    lock = lock or {}
    bars = [(a, b, struck) for _, a, b, struck in rhythm.all_bars_of(song, role)]
    own = plays_as_own(plays, bars) if plays is not None else [rhythm.pattern(p for p, _ in struck) if struck else REST for _, _, struck in bars]
    if figures is None:
        figures = _free_figures(song, role, models["rhythm"], FreeManner(models["rhythm"].table.vocabulary, division=song.division), own, bars,
                                habit, rng, hold, lock, envelope_of=free_envelope(habit), lock_share=UPPER_LOCK.get(role, 1.0), energy=energy)
    else:
        figures = [f if o != REST else REST for f, o in zip(figures, own)]
    step = MOTION_STEP.get(motion, 0)
    pedals = pedals or {}
    walked = 0.0                                            # how far along the stack the voices have moved (motion)
    tune_line = sorted(song.notes.get(R.MELODY, []) + song.notes.get(R.COUNTER, []))   # what the written part must not clash with
    tonic, mode = key if key else (0, "major")
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]}
    notes, voicings = [], []
    played_v, prev_v = Counter(), None
    last_chord, marks, previous_low = None, ["R", "3", "5"], None
    periods = getattr(song, "periods", {}).get(role, {})   # a held bar of the part's period takes its source bar's voicing too, on the same chord
    by_bar = {}
    own_tone = max(1, tone_index)                           # the tone a voice beside the line takes of the line's voicing (a span at a time with ANY_TONE)
    beside = bool(tone_index) and kind in VOICE_KINDS and "voice_intervals" in models and "voice_moves" in models and shared is not None
    prev_steps, prev_midi = rhythm.START, None              # a voice beside the line: its last interval with the line, its last note

    def line_before(k, p, strict=False):
        """The line's note last struck at or before (bar k, position p); `strict`: before it."""
        best = None
        for key_, m in shared.items():
            if isinstance(key_[0], str) and key_[0] == "line" and (key_[1] < (k, p) if strict else key_[1] <= (k, p)) and (best is None or key_[1] > best[0]):
                best = (key_[1], m)
        return best[1] if best else None

    def weighted(weights: dict):
        """One key drawn by its weight; None where nothing weighs."""
        total = sum(weights.values())
        if total <= 0:
            return None
        x, acc = rng.random() * total, 0.0
        for key_, w in weights.items():
            acc += w
            if x < acc:
                return key_
        return next(reversed(weights))
    in_bar = {}                                             # bar -> positions the line's voicing is known at (shared), for a voice beside it
    for k, ((a, b, _), figure) in enumerate(zip(bars, figures)):
        if figure == REST:
            voicings.append(REST)
            continue
        positions = [Fraction(t.partition(":")[0]) for t in rhythm._tokens(figure)]
        bar_voicing = []
        runs_to = first_onset(figures, bars, k + 1)        # the bar's last note runs to the next bar's first, as the share was counted
        for i, p in enumerate(positions):
            start = a + float(p)
            until = a + float(positions[i + 1]) if i + 1 < len(positions) else (runs_to if runs_to is not None and runs_to > b - rhythm.NEAR else b)
            c = rhythm._chord_at(song.chords, start)
            chord = (c.root, c.shape) if c is not None and c.root is not None and c.fit >= FIT else last_chord
            if chord is None:
                continue
            src = by_bar.get(k - periods[k], {}).get(i) if k in periods else None
            known = None
            if shared is not None and tone_index:           # a voice beside the line: the line's voicing at this onset, or the last before it
                at = shared.get((k, p))
                if at is None:
                    before = [q for (kk, q) in shared if kk == k and q <= p]
                    at = shared.get((k, max(before))) if before else None
                known = at if at is not None and at[0] == chord else None
            if known is not None:
                prev_v, marks = known[1], list(known[2])
                if chord != last_chord or not bar_voicing:      # a new span: the tone this voice takes of the line's voicing (ANY_TONE: drawn)
                    own_tone = rng.randrange(1, max(2, len(marks))) if tone_index == ANY_TONE else tone_index
                last_chord = chord
                if not bar_voicing or bar_voicing[-1] != prev_v:
                    bar_voicing.append(prev_v)
            elif src is not None and src[0] == chord and src[1] is not None and (chord != last_chord or not bar_voicing):
                prev_v, marks = src[1], src[2]                  # the period's bar again: its voicing with it
                last_chord = chord
                bar_voicing.append(prev_v)
            elif chord != last_chord or not bar_voicing:
                shape = chord[1] or "major"
                v_unit = tables.Unit(song.sid, song.game, "", {"part": role, "shape": shape, "habit": richness, "previous": prev_v or rhythm.START})
                need = min(RICH_TONES.get(richness, 2), max(1, len(voices)))   # a lone voice needs one tone, a trio up to three
                full = lambda o, _n=need: voiced(o, _n)   # noqa: E731
                drawn = models["voicings"].draw(v_unit, prev_v, played_v, rng, keep=full)
                for _ in range(TRIES):
                    if full(drawn):
                        break
                    drawn = models["voicings"].table.draw(models["voicings"].table.context(v_unit), rng, v_unit.values, floored=False, floor_k=models["voicings"].table.chain_floor)
                marks = [m for m in drawn.split() if m in CHORD_MARKS] if full(drawn) else (["R", "5"] if need > 1 else ["R"])
                played_v[drawn] += 1
                prev_v = drawn
                last_chord = chord
                bar_voicing.append(drawn)
            by_bar.setdefault(k, {})[i] = (chord, prev_v, list(marks))
            if shared is not None and not tone_index:
                shared[(k, p)] = (chord, prev_v, list(marks))
            pitches = stack(marks, chord[0], chord[1], scale, registers[voices[0]][0], previous_low)
            previous_low = float(pitches[0]) if pitches else previous_low
            tune = sounding_pcs(tune_line, start)
            if role == R.ARP and len(voices) == 1:
                midi = in_register(pitches[i % len(pitches)], registers[voices[0]])
                midi = unclashed(midi, [in_register(m, registers[voices[0]]) for m in pitches], tune)
                notes.append((start, start + (until - start) * share_at(sounds, until - start), float(midi), voices[0]))
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
                low_v, high_v = registers[v]
                if high_v - low_v <= PEDAL_VOICE:           # a pedal voice: the song's drone, struck on the figure
                    notes.append((start, start + (until - start) * share_at(sounds, until - start), float(pedals.get(v, low_v)), v))
                    continue
                taken = shared.setdefault(("taken", (k, p)), set()) if shared is not None else None   # the part's notes at this onset (a 2-tuple key: the voicing look-up unpacks every key)
                if beside and len(voices) == 1:            # a voice beside the line: with the line, its interval to the line's note (voice_intervals);
                    with_line = (k, p) in shared            # alone, its move from its own last note (voice_moves); both in scale steps, drawn
                    ref = (shared.get(("line", (k, p))) if with_line else line_before(k, p)) if with_line or prev_midi is None else None
                    if (with_line or prev_midi is None) and ref is None:
                        continue
                    t_iv = models["voice_intervals"].table if hasattr(models["voice_intervals"], "table") else models["voice_intervals"]
                    t_mv = models["voice_moves"].table if hasattr(models["voice_moves"], "table") else models["voice_moves"]
                    refused = set()
                    for _ in range(VOICE_TRIES):            # a pitch another voice of the part holds at this onset is drawn again (two copies of one
                        if ref is not None:                 # sample on one pitch phase); the onset is skipped when every try lands on one
                            ctx_iv = (role, kind, line_state(ref, scale), prev_steps)
                            chained = with_line and prev_steps != rhythm.START and prev_midi is not None
                            # the note both words agree on: its interval to the line's note (voice_intervals, chained on the interval
                            # before) and its own move from its last note (voice_moves); held out on FFVI the product beats either
                            # word alone (3.36 bits a unit against 3.87 and 3.71)
                            entry = weighted(interval_weights(t_iv, ctx_iv, refused, ref, scale, t_mv if chained else None, (role, kind, "with"), prev_midi if chained else None))
                            if entry is None:
                                break
                            steps = entry                   # the chain's next context
                            target = interval_pitch(entry, ref, scale)   # in semitones against a line note off the scale (round 66)
                        else:
                            steps = None
                            move = weighted({c: t_mv.p(str(c), (role, kind, "alone")) for c in range(-rhythm.VOICE_STEPS, rhythm.VOICE_STEPS + 1)
                                             if c not in refused and str(c) in t_mv.vocabulary})   # as a draw: never an interval or move the game never made
                            if move is None:
                                break
                            target = scale_pitch(scale_index(prev_midi, scale) + move, scale)
                        midi = in_register(target, registers[v])
                        if taken is None or midi not in taken:
                            break
                        refused.add(steps if steps is not None else move)
                    else:
                        continue
                    if taken is not None and midi in taken:
                        continue
                    if with_line and steps is not None:
                        prev_steps = str(steps)
                    prev_midi = midi
                elif tone_index and len(voices) == 1:      # no tables for it: a tone up the line's voicing (its rank's, or one drawn a span), walking with the motion
                    order = [(own_tone + int(walked) + d) % len(pitches) for d in range(len(pitches))]
                    free = [pitches[i] for i in order if taken is None or in_register(pitches[i], registers[v]) not in taken]
                    if not free:                            # every tone of the voicing already sounds in the part: the voice sits this onset out
                        continue
                    midi = in_register(free[0], registers[v])
                else:
                    midi = in_register(pitches[(j + offset) % len(pitches)] if offset else stacked[j], registers[v])
                    if shared is not None and not tone_index:
                        shared[("line", (k, p))] = midi     # the line's note here, for the voices beside it
                midi = unclashed(midi, [in_register(m, registers[v]) for m in pitches], tune)
                if taken is not None:
                    taken.add(int(round(midi)))
                notes.append((start, start + (until - start) * share_at(sounds, until - start), float(midi), v))
            walked += step
        voicings.append(" | ".join(bar_voicing) if bar_voicing else REST)
    return notes, figures, voicings


# --- the melody: phrases written free from the tables (phase 4, the melody slice) ---

PHRASE = 4                            # bars a phrase, as the phrase tables were counted
CONTOUR_STEP = 2.0                    # semitones a contour's thirds aim apart (phrases.LEVEL)
DETACHED = 0.5                        # the share of its gap a detached melody note sounds (the readings: under 0.75)
HELD = 0.95                           # and a held one
COPY_TRIES = 12                       # tunes drawn again when one copies a game's phrase (the reference set)
ARC_ABOVE = {"0": 0, "1-2": 2, "3-5": 4, "6+": 7}             # the summit table's classes, as semitones the climax may rise above the register
ARC_BELOW = {"0": 1, "1-2": 2, "3-5": 4, "6-9": 7, "10+": 11}   # the arc table's classes, as semitones a phrase's ceiling sits under the climax
ARC_ROOM = 7                          # semitones a phrase keeps above the register's floor whatever the arc says
BESIDE_SPAN = 24                      # semitones above its floor a second bass voice may sit when its pitch follows the line


TIER_SLACK = 0.5                      # onsets a bar a tune's running density may sit outside its tier's bounds (tier_bounds)
TIER_AFTER = 3                        # new rhythms drawn before the running density and grain are held to their words
GRAIN_SLACK = 0.1                     # how far a tune's running share of onsets off the beat may sit outside its grain's bounds


def grain_bounds(grain: str | None) -> tuple[float, float]:
    """The share of onsets off the beat a tune of this grain keeps its new rhythms to (rhythm.GRAINS: on-beat under 0.25,
    eighths to 0.5, fine over), GRAIN_SLACK either side; wide open without a grain."""
    if grain:
        low = 0.0
        for top, name in rhythm.GRAINS:
            if name == grain:
                return max(0.0, low - GRAIN_SLACK), min(1.0, top + GRAIN_SLACK)
            low = top
    return 0.0, 1.0


def offbeats(tokens: list) -> int:
    """How many of a figure's tokens sit off the beat."""
    return sum(1 for t in tokens if Fraction(t.partition(":")[0]).denominator != 1)


def tier_bounds(habit: str) -> tuple[float, float]:
    """The onsets a bar a part's tune keeps its running mean within, from its habit's density tier (rhythm.DENSITIES:
    sparse to 2, medium to 6, dense over), TIER_SLACK either side; wide open for a habit without a tier."""
    tier = (habit or "").split()[0] if habit else ""
    lo = 0.0
    for top, name in rhythm.DENSITIES:
        if name == tier:
            return max(0.0, lo - TIER_SLACK), (top + TIER_SLACK if top < 1e8 else 64.0)
        lo = top
    return 0.0, 64.0


def share_at(sounds, gap: float) -> float:
    """The share of a gap a note sounds: one share (a float), or the gap_sounds word's by the gap's class (a dict)."""
    if isinstance(sounds, dict):
        return float(sounds.get(rhythm.gap_class(gap), sounds.get("<1", 0.8)))
    return float(sounds)


def mask_figure(line_figure: str, mask: str) -> str:
    """A second bass voice's figure from the line's figure and a second_figures outcome (a mask over the line's onsets plus
    onsets of its own): the line's onsets it strikes with keep the line's marks (its pitch follows the line there,
    beside_pitch), its own onsets take the root mark and are re-pitched by its own move; REST where the mask rests."""
    if line_figure == REST or not line_figure or mask == "-":
        return REST
    toks = [(Fraction(t.partition(":")[0]), t.partition(":")[2] or "R") for t in rhythm._tokens(line_figure)]
    marks = {p: m for p, m in toks}
    positions = rhythm.apply_mask(rhythm.pattern(p for p, _ in toks), mask)
    if positions == "-" or not positions:
        return REST
    return " ".join(f"{p}:{marks.get(Fraction(p), 'R')}" for p in positions.split())


def first_onset(figures: list, bars: list, k: int) -> float | None:
    """When bar k's first note strikes, from its figure; None where it rests or there is no bar k. A bar's last note runs to
    it: the sounded share was counted against the gap to the voice's next onset, and a note ended at the bar line had
    dropped into a hole when the next bar began late (2026-10-24)."""
    if k >= len(figures) or k >= len(bars) or figures[k] == REST or not figures[k]:
        return None
    toks = rhythm._tokens(figures[k])
    return bars[k][0] + float(Fraction(toks[0].partition(":")[0])) if toks else None


def line_state(ref: float, scale: set) -> str:
    """The line note's state for the voice_intervals word: on the song's scale, or altered (off it)."""
    return "scale" if int(round(ref)) % 12 in scale else "altered"


def interval_entry(entry: str) -> tuple[str, int]:
    """A voice_intervals entry: ("steps", the scale steps) or ("semis", the semitones against an altered line note, "s-4")."""
    return ("semis", int(entry[1:])) if entry.startswith("s") else ("steps", int(entry))


def interval_pitch(entry: str, ref: float, scale: set) -> int:
    """The voice's note for an interval entry against the line's note: the scale steps from the line note's scale tone, or
    the semitones from the note itself (round 66: the counted steps had been put back on the scale, so a unison with the
    tune's leading tone came out a semitone under it)."""
    form, v = interval_entry(entry)
    return int(round(ref)) + v if form == "semis" else scale_pitch(scale_index(int(round(ref)), scale) + v, scale)


def interval_weights(t_iv, ctx: tuple, refused, ref: float, scale: set, t_mv=None, move_ctx: tuple | None = None, prev_midi: float | None = None) -> dict:
    """{entry: weight} over the voice_intervals word's entries under `ctx` (its third value the line note's state, which
    picks the entries' form), within two octaves and off `refused`; with `t_mv` and the voice's last note, each weighed
    by the voice_moves word for the move the entry's note would make from it: the note both words agree on."""
    form = "semis" if ctx[2] == "altered" else "steps"
    out = {}
    for entry in t_iv.vocabulary:
        f, v = interval_entry(entry)
        if f != form or entry in refused or abs(v) > (rhythm.VOICE_SEMITONES if f == "semis" else rhythm.VOICE_STEPS):
            continue
        w = t_iv.p(entry, ctx)
        if t_mv is not None and prev_midi is not None:
            mv = str(scale_index(interval_pitch(entry, ref, scale), scale) - scale_index(int(round(prev_midi)), scale))
            if mv not in t_mv.vocabulary:
                continue
            w *= t_mv.p(mv, move_ctx)
        if w > 0:
            out[entry] = w
    return out


def beside_pitch(models: dict, role: str, kind: str, scale: set, rng: random.Random, ref: float | None, prev_steps: str,
                 prev_midi: float | None, moved: int = 0, refused=()) -> tuple[int | None, str | None]:
    """The note of a voice beside the line, as the voice_intervals and voice_moves words give it: with the line (`ref`, the
    line's note), the interval both words agree on, drawn from their product (the move the interval's note would make
    from the voice's last note; `moved`, the line's own move, is no longer needed and kept for the callers); alone, the
    voice's own move. (midi, the interval entry drawn, the chain's next `prev_steps`) or None; (None, None) where
    nothing can be drawn."""
    t_iv = models["voice_intervals"].table if hasattr(models["voice_intervals"], "table") else models["voice_intervals"]
    t_mv = models["voice_moves"].table if hasattr(models["voice_moves"], "table") else models["voice_moves"]

    def weighted(weights: dict):
        tot = sum(weights.values())
        if tot <= 0:
            return None
        x, acc = rng.random() * tot, 0.0
        for key_, w in weights.items():
            acc += w
            if x < acc:
                return key_
        return next(reversed(weights))
    if ref is not None:
        ctx = (role, kind, line_state(ref, scale), prev_steps)
        chained = prev_steps != rhythm.START and prev_midi is not None
        weights = interval_weights(t_iv, ctx, refused, ref, scale, t_mv if chained else None, (role, kind, "with"), prev_midi if chained else None)
        entry = weighted(weights)
        return (interval_pitch(entry, ref, scale), entry) if entry is not None else (None, None)
    if prev_midi is None:
        return (None, None)
    move = weighted({c: t_mv.p(str(c), (role, kind, "alone")) for c in range(-rhythm.VOICE_STEPS, rhythm.VOICE_STEPS + 1)
                     if c not in refused and str(c) in t_mv.vocabulary})
    return (scale_pitch(scale_index(int(round(prev_midi)), scale) + move, scale), None) if move is not None else (None, None)


def counter(song: rhythm.Song, tune: list, tune_figures: list, masks: list, span: tuple, models: dict, rng: random.Random,
            kind: str, key: tuple | None = None, articulation: str = "mixed", register: tuple | None = None,
            role: str = R.COUNTER) -> tuple[list, list, list]:
    """The counter-line written beside the tune (round 29): its bar from the tune's bar and a counter_figures mask
    (`masks`, one a bar, REST where the plan has it rest; rhythm.apply_mask: the tune's onsets it strikes with and its
    own, its own alone where the tune rests), its pitch by the voice words as the second bass voice's is
    (beside_pitch: with the tune, the interval both words agree on under `kind`, the sample relation; alone, its own
    move), kept in `span` by octaves (the tune's register widened by the layer offset's cap, as the chord parts' voices
    are: a drawn third below folded into the counter's own register had turned into a sixth above, round 23); its
    lengths from the values table under the song's articulation, as the melody's. `tune`: the tune's written notes
    [(start, end, midi, voice)]; `tune_figures`: its bars' patterns (REST where it rests); `register`: the counter's
    planned register, for a first note the tune leaves it alone with. On the tune's own sample a drawn unison is drawn
    again (two copies of one sample on one pitch), the onset skipped after VOICE_TRIES. FFVI's counter plays WITH the
    tune (0.67 of its onsets on the tune's, as loud, 2.5 semitones under); written as a second tune from the melody
    writer's own stream it had 0.43 of its onsets on the tune's, Whole 28 0.19 on one timbre in one register (2026-10-24).
    Returns [(start, end, midi)], the bars' patterns and a log."""
    tonic, mode = key if key else (0, "major")
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]}
    bars = [(a, b) for _, a, b, _ in rhythm.all_bars_of(song, role)]
    at, line_times = {}, []                                 # the tune's note at (bar, position); its onsets in time
    for a_t, _, m, *rest in tune:
        if rest and rest[0] != 0:
            continue                                        # its line voice alone
        k = next((i for i, (a, b) in enumerate(bars) if a - rhythm.NEAR <= a_t < b - rhythm.NEAR), None)
        if k is not None:
            at.setdefault((k, rhythm.position(a_t - bars[k][0], song.division)), m)
            line_times.append((a_t, m))
    line_times.sort()
    figures, pitched = [REST] * len(bars), []
    prev_steps, prev_midi, last_with = rhythm.START, None, None
    with_tune = own = skipped = 0
    for k, (a, b) in enumerate(bars):
        mask = masks[k] if k < len(masks) else REST
        if mask == REST or not mask:
            continue
        tune_pat = tune_figures[k] if k < len(tune_figures) and tune_figures[k] != REST else "-"
        positions = rhythm.apply_mask(tune_pat, mask)
        if positions == "-":
            continue
        figures[k] = positions
        for p in (Fraction(t) for t in positions.split()):
            ref = at.get((k, p))
            midi = steps = None
            if ref is not None:
                moved = (scale_index(int(round(ref)), scale) - scale_index(int(round(last_with)), scale)) if last_with is not None else 0
                refused = set()
                for _ in range(VOICE_TRIES):
                    target, steps = beside_pitch(models, role, kind, scale, rng, ref, prev_steps, prev_midi, moved, refused)
                    if target is None:
                        break
                    midi = in_register(target, span)
                    if kind == "same" and midi == int(round(ref)):
                        refused.add(steps)
                        midi = None
                        continue
                    break
                if midi is None:
                    skipped += 1
                    continue
                prev_steps, last_with = str(steps), ref
                with_tune += 1
            else:
                target, _ = beside_pitch(models, role, kind, scale, rng, None, prev_steps, prev_midi, 0)
                if target is None:                          # nothing before it: the chord's root nearest the counter's register
                    c = _chord_in_bar(song, a + float(p))
                    centre = sum(register) // 2 if register else sum(span) // 2
                    target = min((m for m in range(span[0], span[1] + 1) if m % 12 == ((c[0] if c else tonic) % 12)), key=lambda m: abs(m - centre), default=centre)
                midi = in_register(target, span)
                own += 1
            prev_midi = midi
            pitched.append((k, p, float(midi)))
    notes = []                                              # the lengths as the melody's: the values table under the articulation habit, whose
    for i, (k, p, m) in enumerate(pitched):                 # value is the gap to the next note across the bar line (a bar's last note runs to
        a, b = bars[k]                                      # the next bar's first onset, as the bass's does since round 26; at a rest bar the
        t = a + float(p)                                    # bar line stays)
        nxt = pitched[i + 1] if i + 1 < len(pitched) else None
        until = bars[nxt[0]][0] + float(nxt[1]) if nxt is not None and nxt[0] in (k, k + 1) else b
        gap = until - t
        if gap <= rhythm.NEAR:
            continue
        value = str(rhythm.position(gap, song.division))
        held = models["values"].draw((role, value, articulation), rng) if "values" in models else "held"
        notes.append((t, t + gap * (HELD if held == "held" else DETACHED), m))
    log = [f"beside the tune on the {kind} sample: {sum(1 for f in figures if f != REST)} bars, {len(notes)} notes, {with_tune} with the tune's onsets, "
           f"{own} its own" + (f"; {skipped} onsets skipped (a unison on one sample)" if skipped else "") + f"; span {span}"]
    return notes, figures, log
MOVED = {"moved up": 2, "moved down": -2}   # semitones a moved phrase shifts (a scale step; the scale then corrects each note)
DEGREE_PCS = {"1": (0,), "3": (3, 4), "5": (7,)}   # a phrase's ending degree -> intervals from the tonic it may land on
STRONG_SCALE = True                   # a note arriving on the beat sits in the scale


def contour_targets(shape: str, size: float | None = None) -> tuple:
    """Where a phrase's thirds sit against its start, by its contour
    (CONTOURS) and how far it goes (`size`, semitones: the contour-size
    table's draw; CONTOUR_STEP a third without one)."""
    if shape in ("rising", "falling"):
        far = size if size is not None else 2 * CONTOUR_STEP
        return (0, far / 2, far) if shape == "rising" else (0, -far / 2, -far)
    if shape in ("arch", "valley"):
        far = size if size is not None else CONTOUR_STEP
        return (0, far, 0) if shape == "arch" else (0, -far, 0)
    return (0, 0, 0)


class Tune:
    """The notes of one written phrase: (start, end in beats, midi), and its rhythm and intervals for the copy check."""

    def __init__(self, notes: list, a: float):
        self.notes = notes
        self.rhythm = [int(round((n[0] - a) * 12)) for n in notes]
        pitches = [int(round(n[2])) for n in notes]
        self.intervals = [y - x for x, y in zip(pitches, pitches[1:])]


CHORD_ON_BEAT = 0.65                  # the share of a tune's strong-beat notes that are chord tones (the games: 58 to 68 %)
REPEAT_RATE = {"rare": 0.02, "some": 0.12, "many": 0.35}   # a song's share of repeated notes by its repeat habit (the games: a
                                      # quarter of songs under 5 %, the median 13 %, a quarter over 30 %)
CONTOUR_RANGE = 5                     # semitones a line may stray from its contour's third before the draw is steered back
LEAP = 12                             # semitones: the moves table folds a move beyond an octave to LEAP + 1 (phrases.LEAP)
MOVES = [f"{m:+d}" if m else "0" for m in range(-LEAP - 1, LEAP + 2)]   # every move the moves table names
ECHO_SHARES = {"same": 0.3, "earlier": 0.3, "new": 0.4}   # the urn's shares where no recall table is given
CONTINUE = 0.8                        # when the bar before echoed an earlier bar, the share of "earlier" draws that go on with the bar after it
                                      # (the fallback without a recall_continues table, round 50)


class Cell:
    """A bar of the tune as a motif: its onsets (beats from the bar line), its
    intervals, its first note's offset from the bar's chord root, and its
    moves as scale steps, so it can come back on another chord in the scale."""

    def __init__(self, positions: list, pitches: list, root: int, scale: set):
        self.positions = list(positions)
        self.pitches = [int(round(m)) for m in pitches]
        self.intervals = [y - x for x, y in zip(self.pitches, self.pitches[1:])]
        self.entry = (self.pitches[0] - root) % 12 if self.pitches else 0
        self.steps = to_steps(self.pitches, scale)
        self.key = " ".join(str(Fraction(p)) for p in self.positions) + " | " + " ".join(f"{i:+d}" for i in self.intervals)


def _ranks(scale: set) -> list:
    return sorted(scale) or list(range(12))


def scale_index(midi: int, scale: set) -> int:
    """A pitch's place counted in scale tones (a pitch off the scale: the tone below it)."""
    ranks = _ranks(scale)
    pc = midi % 12
    below = max((r for r in ranks if r <= pc), default=None)
    pos = ranks.index(below) if below is not None else len(ranks) - 1
    octave = midi // 12 if below is not None else midi // 12 - 1
    return octave * len(ranks) + pos


def scale_pitch(index: int, scale: set) -> int:
    ranks = _ranks(scale)
    return 12 * (index // len(ranks)) + ranks[index % len(ranks)]


def to_steps(pitches: list, scale: set) -> list:
    idx = [scale_index(m, scale) for m in pitches]
    return [y - x for x, y in zip(idx, idx[1:])]


def from_intervals(first: int, intervals: list) -> list:
    """A line from its first pitch and its intervals in semitones (a cell moved whole)."""
    out = [first]
    for iv in intervals:
        out.append(out[-1] + iv)
    return out


def fold_cell(pitches: list, register: tuple) -> list:
    """A cell moved whole by octaves into the register (low, high) where an octave fits it; its notes clamped to the
    register only where none does (a cell wider than the register), so a cell that comes back keeps its intervals."""
    if not pitches:
        return pitches
    low, high = register
    lo_, hi_ = min(pitches), max(pitches)
    shift = 0
    while hi_ + shift > high and lo_ + shift - 12 >= low:
        shift -= 12
    while lo_ + shift < low and hi_ + shift + 12 <= high:
        shift += 12
    return [min(high, max(low, m + shift)) for m in pitches]


def from_steps(first: int, steps: list, scale: set) -> list:
    """A line from its first pitch and its scale steps (a diatonic sequence)."""
    out, i = [first], scale_index(first, scale)
    for st in steps:
        i += st
        out.append(scale_pitch(i, scale))
    return out


def cell_pitches(pitches: list, source_root: int, root: int, scale: set, bound: tuple, previous: float | None) -> list:
    """A tune cell's pitches as another part plays them: its first note at the cell's offset from its own bar's chord root
    (`source_root`), on the new bar's root, in the part's register nearest the part's last note, and its moves as scale
    steps from there (a sequence lands as a player's does, again() for the tune's own echoes); every note folded into
    the register."""
    cell = Cell([0.0] * len(pitches), pitches, source_root, scale)
    pc = (root + cell.entry) % 12
    low, high = bound
    anchor = previous if previous is not None else (low + high) / 2
    first = min((m for m in range(low, high + 1) if m % 12 == pc), key=lambda m: (abs(m - anchor), m), default=int(round(anchor)))
    return [in_register(m, bound) for m in from_steps(first, cell.steps, scale)]


class Urn:
    """The tune writer's urn at the bar level: same (the bar before's cell again),
    earlier (one the song played before, by how often) or new, at the shares
    a recall table gives for the song's echo habit."""

    def __init__(self, recall, habit: str):
        self.recall, self.habit = recall, habit

    def shares(self, previous, played: Counter) -> dict:
        if self.recall is not None:
            ctx = tuple({"part": R.MELODY, "habit": self.habit}.get(c, "?") for c in self.recall.conditionings)
            raw = {k: self.recall.p(k, ctx) for k in tables.RECALL}
        else:
            raw = dict(ECHO_SHARES)
        total = sum(raw.values()) or 1.0
        same, earlier, new = (raw[k] / total for k in tables.RECALL)
        pool = sum(played.values()) - (played.get(previous.key, 0) if previous else 0)
        if previous is None:
            new, same = new + same, 0.0
        if pool <= 0:
            new, earlier = new + earlier, 0.0
        return {"same": same, "earlier": earlier, "new": new}

    def choose(self, rng: random.Random, previous, played: Counter) -> str:
        shares = self.shares(previous, played)
        x = rng.random()
        for k in ("same", "earlier", "new"):
            x -= shares[k]
            if x < 0:
                return k
        return "new"


def _weighted(rng: random.Random, options: list, weights: list):
    total = sum(weights)
    x = rng.random() * total
    for o, w in zip(options, weights):
        x -= w
        if x < 0:
            return o
    return options[-1]


def draw_move(moves_table, previous: str, mode: str, midi: float, rng: random.Random, register: tuple, scale: set,
              strong: bool, chord, tune: set, aim: float | None, habit: str | None = None, repeats: str = "some",
              chord_rate: float = CHORD_ON_BEAT, repeat_rate: float | None = None, over_repeats: bool = False,
              over_chord: bool = False, tone: str = "no chord", under_chord: bool = False) -> int:
    """One move of the tune from the moves table, drawn among the moves that
    fit (the register; off the chords' semitones; steered toward the
    contour when the line strays CONTOUR_RANGE from it), the fitting moves
    weighted by the table and, on a strong beat, the chord's tones given
    `chord_rate` of the mass (the song's chord-tone share, CHORD_ON_BEAT
    without one) unless the tune is already over its share (`over_chord`);
    the repeated note given `repeat_rate` of the mass (the song's, else
    the habit's tier) and none while the tune is over it (`over_repeats`).
    Returns the move in semitones."""
    low, high = register
    values = {"part": R.MELODY, "mode": mode, "previous": previous or rhythm.START, "habit": habit or "mixed",
              "place": "strong" if strong else "weak", "tone": tone}          # the landing: the beat arrived on, the tone left
    ctx = tuple(values.get(c, "?") for c in moves_table.conditionings)
    chord_pcs = set()
    if chord is not None:
        root, shape = chord
        chord_pcs = {(root + i) % 12 for i in harmony.SHAPES.get(shape, harmony.SHAPES[""])}
    options, weights, on_chord = [], [], []
    for o in MOVES:
        step = int(o)
        m = midi + step
        if not (low <= m <= high):
            continue
        pc = int(round(m)) % 12
        if any((pc - t) % 12 in CLASH for t in tune):
            continue
        if strong and STRONG_SCALE and pc not in scale:
            continue
        if aim is not None and abs(midi - aim) > CONTOUR_RANGE and (step == 0 or (step > 0) != (aim > midi)):
            continue                                        # steered back toward the contour: standing still is no move toward it
        w = moves_table.p(o, ctx)
        if w <= 0:
            continue
        options.append(step)
        weights.append(w)
        on_chord.append(pc in chord_pcs)
    if not options:
        return 0
    if 0 in options and len(options) > 1:
        # the repeated note passes every filter every time, and the chain feeds on itself after one; its share among
        # the fitting moves is held to the song's repeat rate, so the filters never funnel the line onto one pitch,
        # and it is left out while the tune (its echoed cells too) is over the rate
        if over_repeats:
            kept = [st != 0 for st in options]
            options, weights, on_chord = ([x for x, k in zip(xs, kept) if k] for xs in (options, weights, on_chord))
        else:
            r = repeat_rate if repeat_rate is not None else REPEAT_RATE.get(repeats, REPEAT_RATE["some"])
            r = min(0.95, max(0.0, r))
            rest = sum(w for st, w in zip(options, weights) if st != 0)
            weights = [w if st != 0 else r * rest / (1 - r) for st, w in zip(options, weights)]
    knows_landing = "tone" in moves_table.conditionings
    if strong and chord_pcs and any(on_chord) and not all(on_chord) and (under_chord if knows_landing else not over_chord):
        # the chord weighting holds the song's chord-tone rate (a counted habit): for a moves table that knows nothing of
        # the landing, whenever the tune is not over its rate; for a table drawn by the beat and the tone left, which
        # carries the game's own approach to the chord (by step, in FFVI), only while the tune is under its rate (the
        # filters shift the chain's balance a little: 0.48 against FFVI's 0.56 with no weighting at all)
        mc = sum(w for w, c in zip(weights, on_chord) if c)
        mo = sum(w for w, c in zip(weights, on_chord) if not c)
        if mc > 0 and mo > 0:                                # a side with no mass (the repeated note at a rate of none) is left as it is
            weights = [w * (chord_rate / mc if c else (1 - chord_rate) / mo) for w, c in zip(weights, on_chord)]
    return _weighted(rng, options, weights)


def _chord_in_bar(song: rhythm.Song, t: float):
    c = rhythm._chord_at(song.chords, t)
    return (c.root, c.shape) if c is not None and c.root is not None and c.fit >= FIT else None


def melody(song: rhythm.Song, voice_notes: list, register: tuple, models: dict, rng: random.Random, habit: str,
           key: tuple | None = None, hold=(), reference=None, articulation: str = "mixed", echo_habit: str = "mixed",
           recall=None, step_habit: str = "mixed", repeat_habit: str = "some", plays: list | None = None,
           role: str = R.MELODY, chord_rate: float | None = None, repeat_rate: float | None = None,
           letters: dict | None = None, theme_body=None, grain: str | None = None) -> tuple[list, list, list]:
    """The melody written for the song (the module): bar by bar through the
    urn, as the bass and drums are. A bar's cell is its rhythm and its
    intervals; the urn keeps the bar before's cell, returns to an earlier
    one or makes a new one (the song's echo habit sets the shares); a cell
    that comes back is re-rooted on the bar's chord and its moves are scale
    steps, a sequence. A new cell's rhythm comes from the melody's bar
    table and its notes from the moves table, each move drawn among the
    moves that fit: the register, the scale on the beat, off the chords'
    semitones, chord tones on the beat at the games' rate, the phrase's
    contour. Over the bars, phrases of PHRASE bars on the form: their
    relation (repeated, moved, answered, new), contour and ending drawn;
    the last note of a phrase lands on the ending's degree; a phrase that
    copies a game's (the reference set) is drawn again. Lengths from the
    articulation table. `role`: the melody, or the counter-line written
    the same way after it (the phrase tables count both lines as the
    tune's), clear of the melody as well as the upper parts; `chord_rate`:
    the song's share of strong-beat notes on the chord (the chord-tones
    table's draw), held by the moves drawn and by what an echoed cell's
    beats are snapped to; `repeat_rate`: the song's share of moves that
    repeat the note (the repeat-rates table's draw; the habit's tier
    without one), held the same way. A phrase after the first sits where
    the phrase-shifts table puts it against the one before (a moved
    phrase moved that far; a new one starting that far from where the
    last left off). `letters`: {part index: the part's phrases as
    letters} (rhythm.THEME, AGAIN, NEW; the plan's draw from the
    phrase-letters table): a THEME phrase after the first opens with the
    theme's head again and keeps as many of its next bars as the
    theme-body table draws (`theme_body`), then goes on new; an AGAIN
    phrase brings back the last phrase whose head was not the theme's; a
    NEW phrase is new, or answers the one before. Without letters the
    phrases stand only to the one before (the relations table). Returns
    [(start, end, midi)], the bars' rhythms and a log."""
    tonic, mode = key if key else (0, "major")
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]}
    bars = [(a, b, struck) for _, a, b, struck in rhythm.all_bars_of(song, role)]
    own = plays_as_own(plays, bars) if plays is not None else [rhythm.pattern(p for p, _ in struck) if struck else REST for _, _, struck in bars]
    meters = [max(1, round(b - a)) for a, b, _ in bars]
    manner = FreeManner(models["rhythm"].table.vocabulary, division=song.division)
    envelope_of = free_envelope(habit)
    clear_of = rhythm.UPPER + ((R.MELODY, R.COUNTER) if role != R.MELODY else ())   # a second counter-line stays clear of the first too
    tune_line = sorted(n for r in clear_of for n in song.notes.get(r, []))
    rate = chord_rate if chord_rate is not None else CHORD_ON_BEAT
    on_beat = [0, 0]                                        # the tune's strong-beat notes on the chord, and all of them, so far
    moves_table = models["moves"].table if hasattr(models["moves"], "table") else models["moves"]
    urn = Urn(recall, echo_habit)
    half_kinds = {}                       # bar -> its halves' urn kinds (new_cell_halves), for the log
    index = {num: k for k, num in enumerate(song.numbers)}
    windows, by_part = [], {}                               # the phrase windows, a part of the form at a time (a phrase ends with its part)
    for i, (bar, n, *rest) in enumerate(song.parts):
        ks = [index[num] for num in range(bar, bar + n) if num in index]
        mine = []
        for j in range(0, len(ks), PHRASE):
            chunk = ks[j:j + PHRASE]
            if len(chunk) < PHRASE and mine and mine[-1][-1] + 1 == chunk[0]:
                mine[-1] = mine[-1] + chunk
            else:
                mine.append(chunk)
        by_part[i] = (mine, rest[0] if rest else None, len(ks))
        windows += mine
    copies = {}                                             # a window's first bar -> the earlier window it plays again (a part the form repeats)
    for mine, of, n in by_part.values():
        if of is not None and of in by_part and by_part[of][2] == n and len(by_part[of][0]) == len(mine):
            for w, src in zip(mine, by_part[of][0]):
                if w and src:
                    copies[w[0]] = src[0]
    covered = {k for w in windows for k in w}
    windows += [[k] for k in range(len(bars)) if k not in covered]
    windows.sort()
    register0 = register                                    # the part's register; `register` is rebound a phrase at a time to its room in the arc
    tops = {}                                               # a window's first bar -> the phrase's ceiling: the arc (climax, arc, summit tables)
    if role == R.MELODY and all(k in models for k in ("climax", "arc", "summit")) and windows:
        from . import phrases as phrases_mod
        place_at = {w[0]: phrases_mod.place_of(i, len(windows)) for i, w in enumerate(windows)}
        above = models["summit"].draw((R.MELODY,), rng, floored=False, floor_k=1)
        peak_top = min(120, register0[1] + ARC_ABOVE.get(above, 0))
        want = models["climax"].draw((R.MELODY,), rng, floored=False, floor_k=1)
        climax_w = next((w[0] for w in windows if place_at[w[0]] == want), windows[len(windows) // 2][0])
        for w in windows:
            if w[0] == climax_w:
                tops[w[0]] = peak_top
            else:
                below = models["arc"].draw((R.MELODY, place_at[w[0]]), rng, floored=False, floor_k=1)
                tops[w[0]] = max(register0[0] + ARC_ROOM, peak_top - ARC_BELOW.get(below, 2))
        arc_line = (f"arc: the climax {want} at bar {climax_w}, top {peak_top} (the register's {register0[1]}); the phrases' tops "
                    + " ".join(f"{w[0]}:{tops[w[0]]}" for w in windows))
    else:
        arc_line = None
    room_high = max(tops.values()) if tops else register0[1]    # the part's ceiling over the song: where a recalled cell may reach (round 49)
    figures = [REST] * len(bars)
    cells = {}                                              # bar index -> Cell
    played, by_key = Counter(), {}                          # the urn: cell key -> times played; key -> a Cell
    source = {}                                             # bar index -> the earlier bar it echoed (a passage recalled goes on)
    choices = {}                                            # bar index -> how the bar came (same, earlier, new, answered, copy)
    prev_cell, last_midi, last_move = None, float((register[0] + register[1]) // 2), rhythm.START
    last_time = None                                        # when the tune's last note fell: the note a move leaves, for its tone against the chord
    rhythm_played, rhythm_prev = Counter(), None
    new_strikes = []                                        # onsets of each new rhythm drawn: the tune's running density (tier_bounds)
    new_offs = []                                           # of them, the onsets off the beat: the tune's running grain (grain_bounds)
    draws = {k: (Counter(), None) for k in ("contours", "endings", "relations")}
    log, prev_phrase, prev_phrase_start = ([arc_line] if arc_line else []), None, None
    written_windows = {}                                    # a window's first bar -> (its live bars, their cells), for the form's repeats
    part_of_window = {}                                     # a window's first bar -> (its part's index, its place among the part's windows
    for i, (mine, _, _) in by_part.items():                 # the tune plays in: the letters count sounding phrases, as the counts did)
        j = 0
        for w in mine:
            if w and any(own[k] != REST for k in w):
                part_of_window[w[0]] = (i, j)
                j += 1
    theme = None                                            # the theme phrase's cells (the first phrase's), once written
    theme_bars = set()                                      # the theme phrase's bars: where an echo may point (recall_sources)
    others = []                                             # the phrases written whose head is not the theme's, latest last
    part_of = {k: i for i, (mine, _, _) in by_part.items() for w_ in mine for k in w_}   # a bar -> its part of the form (its section)
    pair_urn = Urn(models["pair_recall"], echo_habit) if "pair_recall" in models else None   # the urn at the pair (round 40)
    bar_urn = Urn(models["pair_bar_recall"], echo_habit) if pair_urn is not None and "pair_bar_recall" in models else urn   # the bar urn inside a new pair
    pairs_played, pair_cells = Counter(), {}                # the pairs: (key, key) -> times played; a pair's first bar -> (cell, cell)
    prev_pair, prev_pair_key, prev_pair_at = None, None, None   # the pair before (its cells, its key, its first bar)
    pair_kinds, source_kinds = Counter(), Counter()         # for the log: the pair urn's draws, where the echoes pointed
    sources_table = models.get("recall_sources")

    def source_shares() -> dict | None:
        """Where an echo points (recall_sources: the section, the theme, elsewhere), the word's shares for the song's echo habit."""
        if sources_table is None:
            return None
        ctx = tuple({"part": R.MELODY, "habit": echo_habit}.get(c_, "?") for c_ in sources_table.conditionings)
        return {src: sources_table.p(src, ctx) for src in rhythm.RECALL_SOURCES}

    def by_source(k: int, pool: list) -> list:
        """A pool of earlier bars (j, thing) cut to where the drawn source says an echo of bar k points: the bars of bar k's own
        section, the theme phrase's, or another section's; a source with nothing in it gives its share to the others."""
        shares_ = source_shares()
        if not pool or shares_ is None:
            return pool
        groups = {src: [] for src in rhythm.RECALL_SOURCES}
        for j, thing in pool:
            groups["section" if part_of.get(j) == part_of.get(k) else "theme" if j in theme_bars else "elsewhere"].append((j, thing))
        live_ = {src: p for src, p in shares_.items() if groups[src]}
        total = sum(live_.values()) or 1.0
        x = rng.random() * total
        for src in rhythm.RECALL_SOURCES:
            if src in live_:
                x -= live_[src]
                if x < 0:
                    source_kinds[src] += 1
                    return groups[src]
        src = next(src for src in rhythm.RECALL_SOURCES if src in live_)
        source_kinds[src] += 1
        return groups[src]

    def continues() -> bool:
        """Whether a passage recalled goes on with the bar after its source (recall_continues, round 50: FFVI's share by the
        song's echo habit; the CONTINUE constant before it)."""
        t = models.get("recall_continues")
        if t is None:
            return rng.random() < CONTINUE
        ctx = tuple({"part": R.MELODY, "habit": echo_habit}.get(c_, "?") for c_ in t.conditionings)
        return t.draw(ctx, rng, floored=False) == "yes"

    def note_pair(live_: list, cells_: list, i: int) -> None:
        """Bars i-1 and i of a phrase just written as a pair the tune has played: the pair urn's memory."""
        nonlocal prev_pair, prev_pair_key, prev_pair_at
        if i % rhythm.PAIR != rhythm.PAIR - 1 or i >= len(cells_):
            return
        pr = (cells_[i - 1], cells_[i])
        prev_pair, prev_pair_key, prev_pair_at = pr, (pr[0].key, pr[1].key), live_[i - 1]
        pairs_played[prev_pair_key] += 1
        pair_cells[prev_pair_at] = pr

    def letter_of(w0: int) -> str | None:
        if not letters or w0 not in part_of_window:
            return None
        i, j = part_of_window[w0]
        mine = letters.get(i) or letters.get(str(i))
        if not mine:
            return None
        mine = mine.split() if isinstance(mine, str) else list(mine)
        return mine[j] if j < len(mine) else mine[-1]

    def end_phrase(cells_: list):
        """The writer's state after a phrase copied whole or in part."""
        nonlocal prev_cell, last_midi, last_move
        if not cells_:
            return
        prev_cell = cells_[-1]
        if prev_cell.pitches:
            last_midi = float(prev_cell.pitches[-1])
            if len(prev_cell.pitches) >= 2:
                d = prev_cell.pitches[-1] - prev_cell.pitches[-2]
                last_move = f"{d:+d}" if d else "0"
    phrase_size = None                                      # how far the phrase's contour goes (contour_targets)
    moves_seen = [0, 0, None]                               # the tune's repeated moves, all its moves, the last pitch written, so far
    rep_rate = repeat_rate if repeat_rate is not None else REPEAT_RATE.get(repeat_habit, REPEAT_RATE["some"])

    def over_repeats() -> bool:
        return moves_seen[1] > 0 and moves_seen[0] / moves_seen[1] > rep_rate

    def over_chord() -> bool:
        return on_beat[1] > 0 and on_beat[0] / on_beat[1] > rate

    def shift_of(relation: str) -> float:
        """How far the phrase sits from the one before, by their relation: the table's draw, else MOVED."""
        t = models.get("phrase_shifts")
        return float(t.draw((R.MELODY, mode, relation), rng)) if t is not None else float(MOVED.get(relation, 0))

    def wants_chord() -> bool:
        """Whether an echoed cell's beat is snapped onto the chord: while the tune's share so far is under the song's."""
        return on_beat[1] == 0 or on_beat[0] / on_beat[1] < rate

    def size_of(shape: str):
        t = models.get("contour_sizes")
        return float(t.draw((R.MELODY, mode, shape), rng)) if t is not None and shape != "level" else None

    def draw_shape(name, extra):
        played_, prev_ = draws[name]
        unit = tables.Unit(song.sid, song.game, "", {"part": R.MELODY, "mode": mode, **extra})
        out = models[name].draw(unit, prev_, played_, rng)
        played_[out] += 1
        draws[name] = (played_, out)
        return out

    def new_rhythm(k: int) -> list:
        """A new bar's onsets for a new cell: by the cell-rhythms table's draw
        (rhythm.new_cell_rhythm_units: new to the tune in 77 % of the games'
        new cells, the bar before's in 10 %, an earlier one's in 13 %), a
        rhythm new to the tune from the melody's bar table (in the manner
        and the habit's envelope), the bar before's, or one the tune played;
        the rhythm table's own urn is not run again (it had given new cells
        old rhythms: three distinct rhythms in 32 bars against FFVI's nine;
        always new gave 16.5 distinct cells against 12.5)."""
        nonlocal rhythm_prev
        env = envelope_of(own[k], meters[k])
        values = {"part": role, "meter": meters[k], "previous": rhythm_prev or rhythm.START, "habit": habit, "feel": rhythm.song_feel(song), "tempo": rhythm.band(song.bpm)}
        unit = tables.Unit(song.sid, song.game, "", values)
        lo, hi = tier_bounds(habit)                         # the tune keeps to its tier's density and its drawn grain over the song (round 66):
        g_lo, g_hi = grain_bounds(grain)                    # the bar chain, conditioned on the bar before, had locked a "medium" tune into one
        def tier_ok(f):                                     # game song's grain, 2.9 onsets a bar in one song and 12.2 in another (FFVI's medium
                                                            # tunes: 3.4 to 5.1 a bar), and 4 of 7 medium tunes on the beat (0.15-0.21 of their
                                                            # onsets off it; FFVI's medium tunes 0.33-0.51, the tune_grain word's draw)
            toks = rhythm._tokens(f)
            n = sum(new_strikes) + len(toks)
            off = (sum(new_offs) + offbeats(toks)) / max(1, n)
            if not g_lo <= off <= g_hi:                     # the grain from the first draw: a tune of few new rhythms is its first ones echoed
                return False
            return len(new_strikes) < TIER_AFTER or lo <= n / (len(new_strikes) + 1) <= hi
        fit = lambda f: manner.fits(f) and within(f, env) and tier_ok(f)   # noqa: E731
        kind = models["cell_rhythms"].draw((R.MELODY,), rng, floored=False) if "cell_rhythms" in models else "new"
        figure = None
        if kind == "previous" and rhythm_prev is not None and fit(rhythm_prev):
            figure = rhythm_prev
        elif kind == "earlier":
            pool = {f: n for f, n in rhythm_played.items() if f != rhythm_prev and fit(f)}
            if pool:
                figure = rng.choices(list(pool), list(pool.values()))[0]
        if figure is None:
            figure = models["rhythm"].draw_new(unit, rhythm_played, rng, keep=fit) if hasattr(models["rhythm"], "draw_new") else models["rhythm"].draw(unit, rhythm_prev, rhythm_played, rng, keep=fit)
        for _ in range(TRIES):
            if fit(figure):
                break
            figure = models["rhythm"].table.draw(models["rhythm"].table.context(unit), rng, values, floored=False, floor_k=models["rhythm"].table.chain_floor)
        else:
            figure = next((f for f in rhythm_played if fit(f)), figure if manner.fits(figure) else "0")
        rhythm_played[figure] += 1
        rhythm_prev = figure
        new_strikes.append(len(rhythm._tokens(figure)))
        new_offs.append(offbeats(rhythm._tokens(figure)))
        return [float(Fraction(t.partition(":")[0])) for t in rhythm._tokens(figure)]

    def realize(k: int, positions: list, pitches: list) -> Cell:
        nonlocal last_time
        a, b, _ = bars[k]
        if positions:
            last_time = a + positions[-1]
        chord = _chord_in_bar(song, a)
        cell = Cell(positions, pitches, chord[0] if chord else tonic, scale)
        figures[k] = " ".join(str(Fraction(p)) for p in positions)
        cells[k] = cell
        for m in pitches:
            if moves_seen[2] is not None:
                moves_seen[1] += 1
                moves_seen[0] += int(round(m)) == int(round(moves_seen[2]))
            moves_seen[2] = m
        for p, m in zip(positions, pitches):
            here = _chord_in_bar(song, a + p) if abs(p - round(p)) < rhythm.NEAR else None
            if here is not None:
                on_beat[1] += 1
                on_beat[0] += int(round(m)) % 12 in {(here[0] + i) % 12 for i in harmony.SHAPES.get(here[1], harmony.SHAPES[""])}
        return cell

    def new_cell(k: int, positions: list, shape: str, phrase_start_midi: float | None, a0: float, b0: float) -> Cell:
        """A new cell for bar k: the notes from the moves table under the phrase's contour."""
        nonlocal last_midi, last_move, last_time
        a, b, _ = bars[k]
        targets = contour_targets(shape, phrase_size)
        pitches, midi, move, t_from = [], last_midi, last_move, last_time
        for p in positions:
            t = a + p
            third = min(2, int(3 * (t - a0) / max(1e-9, b0 - a0)))
            aim = (phrase_start_midi + targets[third]) if phrase_start_midi is not None else None
            strong = abs(p - round(p)) < rhythm.NEAR
            tone = phrases.against_chord(midi, t_from, song) if t_from is not None else "no chord"
            step = draw_move(moves_table, move, mode, midi, rng, register, scale, strong, _chord_in_bar(song, t), sounding_pcs(tune_line, t), aim,
                             step_habit, repeat_habit, rate, repeat_rate=rep_rate, over_repeats=over_repeats(), over_chord=over_chord(), tone=tone,
                             under_chord=wants_chord())
            midi = midi + step
            move = f"{step:+d}" if step else "0"
            pitches.append(midi)
            t_from = t
        last_midi, last_move = midi, move
        return realize(k, positions, pitches)

    def new_cell_halves(k: int, positions: list, shape: str, phrase_start_midi: float | None, a0: float, b0: float) -> Cell:
        """A new bar a half at a time (round 38): each half same (the half before's cell again), earlier (one the tune
        played before, by how often) or new, at the half_recall word's shares for the song's echo habit. A recalled half
        comes back re-rooted on the bar's chord in the register, its intervals exact (as again() brings a bar back, round 41);
        a new half takes the drawn rhythm's onsets with new moves. FFVI's tune reuses half-bar cells (0.50 heard earlier,
        themed 0.63) where a bar-grain urn drew a whole new bar (0.39). A half the drawn rhythm gives fewer than
        HALF_CELL_NOTES notes is no cell and stays as drawn (round 47, 2026-10-28): the word counts halves of two notes
        and more, and the urn run on every half had replaced the tune's held halves with recalled two-note ones, so the
        written medium tune had 0.11 of its bars at one or two notes where FFVI's has 0.27, and sat a note a bar denser
        at every habit tier (sparse 2.7 against 2.0, medium 5.1 against 4.1, dense 8.2 against 7.0)."""
        nonlocal last_midi, last_move, last_time
        a, b, _ = bars[k]
        half = meters[k] / 2.0
        chord = _chord_in_bar(song, a)
        root = chord[0] if chord else tonic

        def half_key(ps: list, ms: list) -> str:
            return " ".join(str(round(p * 12)) for p in ps) + " | " + " ".join(f"{y - x:+d}" for x, y in zip(ms, ms[1:]))

        pool, plays = {}, Counter()                         # the tune's half-bar cells so far: key -> (positions, entry, steps)
        for j, c in sorted(cells.items()):
            if j >= k:
                continue
            cj = _chord_in_bar(song, bars[j][0])
            rj, hj = (cj[0] if cj else tonic), meters[j] / 2.0
            for h in (0, 1):
                idx = [i for i, p in enumerate(c.positions) if (p < hj) == (h == 0)]
                if len(idx) < rhythm.HALF_CELL_NOTES:
                    continue
                ps, ms = [c.positions[i] - h * hj for i in idx], [c.pitches[i] for i in idx]
                key_ = half_key(ps, ms)
                pool.setdefault(key_, (ps, (ms[0] - rj) % 12, [y - x for x, y in zip(ms, ms[1:])]))   # its intervals, exact (round 41)
                plays[key_] += 1
        prev_key = None
        if k - 1 in cells:                                  # the half before: the bar before's second half
            c, hj = cells[k - 1], meters[k - 1] / 2.0
            idx = [i for i, p in enumerate(c.positions) if p >= hj]
            if len(idx) >= rhythm.HALF_CELL_NOTES:
                prev_key = half_key([c.positions[i] - hj for i in idx], [c.pitches[i] for i in idx])
        ctx = tuple({"part": R.MELODY, "habit": echo_habit}.get(c_, "?") for c_ in models["half_recall"].conditionings)
        raw = {kd: models["half_recall"].p(kd, ctx) for kd in tables.RECALL}
        all_pos, all_pitches, kinds = [], [], []
        midi, move, t_from = last_midi, last_move, last_time
        targets = contour_targets(shape, phrase_size)
        for h in (0, 1):
            lo = h * half
            shares = dict(raw)
            if sum(1 for p in positions if (p < half) == (h == 0)) < rhythm.HALF_CELL_NOTES:
                shares = {"new": 1.0, "same": 0.0, "earlier": 0.0}   # a half the drawn rhythm gives fewer notes than a cell is no cell: it stays as
            if prev_key not in pool:                                  # drawn (round 47: the word counts halves of HALF_CELL_NOTES and more, and the urn
                shares["new"], shares["same"] = shares["new"] + shares["same"], 0.0   # run on every half had turned the tune's one-note
            earlier = {kk: n for kk, n in plays.items() if kk != prev_key}
            if not earlier:
                shares["new"], shares["earlier"] = shares["new"] + shares["earlier"], 0.0
            total = sum(shares.values()) or 1.0
            x, kind = rng.random() * total, "new"
            for kd in tables.RECALL:
                x -= shares[kd]
                if x < 0:
                    kind = kd
                    break
            key_ = prev_key if kind == "same" else (_weighted(rng, list(earlier), list(earlier.values())) if kind == "earlier" else None)
            if key_ is not None:
                ps, entry, steps = pool[key_]
                pc = (root + entry) % 12
                low, high = register
                anchor_ = midi if midi is not None else (low + high) / 2
                first = min((m for m in range(low, high + 1) if m % 12 == pc), key=lambda m: (abs(m - anchor_), m), default=int(round(anchor_)))
                ms = fold_cell(from_intervals(first, steps), register)   # the half's intervals exact (round 41), the whole half folded in
                pos_h = [lo + p for p in ps]
            else:
                pos_h, ms = [p for p in positions if (p < half) == (h == 0)], []
                for p in pos_h:
                    t = a + p
                    third = min(2, int(3 * (t - a0) / max(1e-9, b0 - a0)))
                    aim = (phrase_start_midi + targets[third]) if phrase_start_midi is not None else None
                    strong = abs(p - round(p)) < rhythm.NEAR
                    tone = phrases.against_chord(midi, t_from, song) if t_from is not None else "no chord"
                    step = draw_move(moves_table, move, mode, midi, rng, register, scale, strong, _chord_in_bar(song, t), sounding_pcs(tune_line, t), aim,
                                     step_habit, repeat_habit, rate, repeat_rate=rep_rate, over_repeats=over_repeats(), over_chord=over_chord(), tone=tone,
                                     under_chord=wants_chord())
                    midi = midi + step
                    move = f"{step:+d}" if step else "0"
                    ms.append(midi)
                    t_from = t
            if ms:
                if key_ is not None:
                    step_ = int(round(ms[-1] - midi))
                    move = f"{step_:+d}" if step_ else "0"
                    midi, t_from = float(ms[-1]), a + pos_h[-1]
                prev_key = half_key([p - lo for p in pos_h], [int(round(m)) for m in ms]) if len(ms) >= rhythm.HALF_CELL_NOTES else None
            kinds.append(kind if ms else "rest")
            all_pos += pos_h
            all_pitches += ms
        last_midi, last_move = midi, move
        half_kinds[k] = kinds
        return realize(k, all_pos, all_pitches)

    def again(k: int, cell: Cell) -> Cell:
        """An earlier cell in bar k: re-rooted on the bar's chord with its
        intervals exact, the whole cell moved to land its strong beats on the
        bar's chord tones (as a player's sequence does), and the whole cell
        folded by octaves into the register. Its intervals are kept exact
        rather than as scale steps (round 41, 2026-10-28): rebuilt by steps,
        with each note clamped to the register, 0.46 of the written recalls
        (theme returns, pairs and bars alike) had come back as a cell the
        tune never played, which the ear hears as a rhythm with new notes;
        FFVI's cells that come back moved keep their intervals (moved 0.20 of
        bars, a rhythm with other intervals 0.06)."""
        nonlocal last_midi, last_move
        a, b, _ = bars[k]
        chord = _chord_in_bar(song, a)
        root = chord[0] if chord else tonic
        pc = (root + cell.entry) % 12
        low, high = register
        first = min((m for m in range(low, high + 1) if m % 12 == pc), key=lambda m: (abs(m - last_midi), m), default=int(round(last_midi)))

        def build(start: int) -> list:
            """The cell from its first note with its intervals exact."""
            out = [start]
            for iv in cell.intervals:
                out.append(out[-1] + iv)
            return out

        def on_chord(pitches: list) -> int:
            """How many of the cell's strong-beat notes land on their beat's chord."""
            n = 0
            for p, m in zip(cell.positions, pitches):
                here = _chord_in_bar(song, a + p)
                if here is not None and abs(p - round(p)) < rhythm.NEAR:
                    n += int(m % 12 in {(here[0] + i) % 12 for i in harmony.SHAPES.get(here[1], harmony.SHAPES[""])})
            return n

        pitches = build(first)
        if wants_chord() and any(_chord_in_bar(song, a + p) is not None and abs(p - round(p)) < rhythm.NEAR for p in cell.positions):
            # the sequence lands its beats on the new chord as a player's does: the whole cell moved to the nearest scale
            # note within a third that puts the most strong beats on the chord. No single note is bent, so the cell's
            # intervals, and with them the tune's steps, stay what the table drew (bending one note had cost the melody
            # a point of steps and the counter-line eleven).
            best = max((x for x in range(first - 4, first + 5) if low <= x <= high and x % 12 in scale),
                       key=lambda x: (on_chord(build(x)), -abs(x - first), -x), default=first)
            pitches = build(best)
        pitches = fold_cell(pitches, (low, max(high, room_high)))   # the part's whole room (round 49): folded into the phrase's room under the
        last_midi = float(pitches[-1]) if pitches else last_midi    # arc, a wider recalled cell had been clamped and bent
        last_move = f"{pitches[-1] - pitches[-2]:+d}" if len(pitches) >= 2 and pitches[-1] != pitches[-2] else ("0" if len(pitches) >= 2 else last_move)
        return realize(k, cell.positions, pitches)

    for w in windows:
        a0, b0 = bars[w[0]][0], bars[w[-1]][1]
        live = [k for k in w if own[k] != REST]
        if not live:
            continue
        register = (register0[0], tops.get(w[0], register0[1]))   # this phrase's room: up to its ceiling in the arc (new_cell, again and
        reg_w = register                                    # draw_move read `register` as the phrase is written)
        src0 = copies.get(w[0])
        if src0 is not None and src0 in written_windows and len(written_windows[src0][0]) == len(live):
            phrase_cells = [realize(k, c.positions, list(c.pitches)) for k, c in zip(live, written_windows[src0][1])]   # the part's tune again
            for i, (k, c) in enumerate(zip(live, phrase_cells)):
                choices[k] = "form"
                played[c.key] += 1
                by_key.setdefault(c.key, c)
                note_pair(live, phrase_cells, i)
            end_phrase(phrase_cells)
            prev_phrase, prev_phrase_start = phrase_cells, a0
            written_windows[w[0]] = (live, phrase_cells)
            log.append(f"bar {w[0]}: the form's repeat of bar {src0}, its tune again")
            continue
        letter = letter_of(w[0])
        if letter == rhythm.THEME and theme is not None:   # the hook comes back: its head, as much of its body as the table says, then on
            keep = 1 + (int(theme_body.draw((R.MELODY,), rng, floored=False)) if theme_body is not None else 0)
            shape = draw_shape("contours", {})
            phrase_size = size_of(shape)
            ending = draw_shape("endings", {})
            phrase_cells, start_midi = [], None
            for i, k in enumerate(live):
                if i < keep and i < len(theme):
                    cell = again(k, theme[i])
                    choices[k] = "theme"
                else:
                    cell = (new_cell_halves if "half_recall" in models else new_cell)(k, new_rhythm(k), shape, start_midi, a0, b0)
                    choices[k] = "new"
                if start_midi is None and cell.pitches:
                    start_midi = float(cell.pitches[0])
                played[cell.key] += 1
                by_key.setdefault(cell.key, cell)
                prev_cell = cell
                phrase_cells.append(cell)
                note_pair(live, phrase_cells, i)
            if keep < len(live) and ending in DEGREE_PCS and phrase_cells and phrase_cells[-1].pitches:
                want = {(tonic + i) % 12 for i in DEGREE_PCS[ending]}
                last = phrase_cells[-1]
                options = [m for m in range(reg_w[0], reg_w[1] + 1) if m % 12 in want]
                if options:
                    last.pitches[-1] = min(options, key=lambda m: (abs(m - last.pitches[-1]), m))
            end_phrase(phrase_cells)
            prev_phrase, prev_phrase_start = phrase_cells, a0
            written_windows[w[0]] = (live, phrase_cells)
            log.append(f"bar {w[0]}: the theme again, {min(keep, len(live))} of its bars, then {shape}, ends {ending}")
            continue
        if letter == rhythm.AGAIN and others:               # an earlier phrase again, the last whose head was not the theme's
            src_phrase = others[-1]
            phrase_cells = [again(k, src_phrase[i % len(src_phrase)]) for i, k in enumerate(live)]
            for i, (k, c) in enumerate(zip(live, phrase_cells)):
                choices[k] = "again"
                played[c.key] += 1
                by_key.setdefault(c.key, c)
                note_pair(live, phrase_cells, i)
            end_phrase(phrase_cells)
            prev_phrase, prev_phrase_start = phrase_cells, a0
            written_windows[w[0]] = (live, phrase_cells)
            log.append(f"bar {w[0]}: an earlier phrase again")
            continue
        relation = "first" if prev_phrase is None else draw_shape("relations", {"habit": habit_rel(models)})
        if relation == "first" and prev_phrase is not None:
            relation = "new"
        if letter is not None and relation in ("repeated", "moved up", "moved down"):
            relation = "new"                                # the letters said a new head: the phrase is new, or answers the one before
        shape = draw_shape("contours", {})
        phrase_size = size_of(shape)
        ending = draw_shape("endings", {})
        phrase_cells = []
        if relation in ("repeated", "moved up", "moved down") and prev_phrase:
            shift = int(round(shift_of(relation))) if relation != "repeated" else 0
            for i, k in enumerate(live):
                src = prev_phrase[i % len(prev_phrase)]
                if shift:
                    src = Cell(src.positions, [m + shift for m in src.pitches], 0, scale)
                    src.entry = (src.entry + shift) % 12
                phrase_cells.append(again(k, src))
                choices[k] = "copy"
                note_pair(live, phrase_cells, i)
        else:
            # the new phrase sits where the shift table puts it against the last (the table counts mean pitches): the line
            # is steered there over the phrase's first third by draw_move's contour aim, not jumped there in one move
            # (FFVI's phrase-start moves are half steps; the jump had made them a quarter)
            aim0 = float(min(reg_w[1], max(reg_w[0], last_midi + shift_of(relation)))) if prev_phrase is not None else None
            for attempt in range(COPY_TRIES):
                phrase_cells, start_midi = [], aim0
                snapshot = (dict(played), dict(by_key), last_midi, last_move, dict(rhythm_played), rhythm_prev, prev_cell, dict(source), dict(choices), list(on_beat), list(moves_seen),
                            Counter(pairs_played), dict(pair_cells), prev_pair, prev_pair_key, prev_pair_at, Counter(pair_kinds), Counter(source_kinds))
                group_plan = None
                for i, k in enumerate(live):
                    if i % rhythm.PAIR == 0:                # a new pair: the pair urn (round 40) says the pair before's again, an earlier pair, or new
                        group_plan = None
                        if pair_urn is not None and i + rhythm.PAIR <= len(live):
                            kind_ = pair_urn.choose(rng, SimpleNamespace(key=prev_pair_key) if prev_pair_key else None, pairs_played)
                            if kind_ == "same" and prev_pair is not None:
                                group_plan = ("pair same", prev_pair, prev_pair_at)
                            elif kind_ == "earlier":
                                pool_ = by_source(k, [(j, pr) for j, pr in pair_cells.items() if j < k and (pr[0].key, pr[1].key) != prev_pair_key])
                                if pool_:
                                    j_, pr = _weighted(rng, pool_, [pairs_played.get((pr[0].key, pr[1].key), 1) for _, pr in pool_])
                                    group_plan = ("pair earlier", pr, j_)
                            pair_kinds[group_plan[0][5:] if group_plan else "new"] += 1
                    if group_plan is not None:
                        kind_, pr, j_ = group_plan
                        cell = again(k, pr[i % rhythm.PAIR])
                        choices[k] = kind_
                        source[k] = j_ + i % rhythm.PAIR if j_ + i % rhythm.PAIR in cells else None
                    elif relation == "answered" and prev_phrase and i < len(prev_phrase):
                        cell = new_cell(k, prev_phrase[i].positions, shape, start_midi, a0, b0)
                        choices[k] = "answered"
                    else:
                        choice = bar_urn.choose(rng, prev_cell, played)
                        before = k - 1 if k - 1 in cells else None
                        if choice == "same" and prev_cell is not None:
                            cell = again(k, prev_cell)
                            source[k] = source.get(before, before) if before is not None else None
                        elif choice == "earlier":
                            follow = source.get(before)
                            if follow is not None and follow + 1 in cells and follow + 1 < k and continues():
                                cell = again(k, cells[follow + 1])      # the passage recalled goes on with its next bar
                                source[k] = follow + 1
                            else:
                                pool = by_source(k, [(j, c) for j, c in cells.items() if j < k and (prev_cell is None or c.key != prev_cell.key)])
                                if pool:
                                    j, c = _weighted(rng, pool, [played.get(c.key, 1) for _, c in pool])
                                    cell = again(k, c)
                                    source[k] = j
                                else:
                                    cell = (new_cell_halves if "half_recall" in models else new_cell)(k, new_rhythm(k), shape, start_midi, a0, b0)
                                    choice = "new"
                        else:
                            cell = (new_cell_halves if "half_recall" in models else new_cell)(k, new_rhythm(k), shape, start_midi, a0, b0)
                        choices[k] = choice
                    if start_midi is None and cell.pitches:
                        start_midi = float(cell.pitches[0])
                    played[cell.key] += 1
                    by_key.setdefault(cell.key, cell)
                    prev_cell = cell
                    phrase_cells.append(cell)
                    note_pair(live, phrase_cells, i)
                if reference is None:
                    break
                notes_ = [(bars[k][0] + p, 0, m) for k, c in zip(live, phrase_cells) for p, m in zip(c.positions, c.pitches)]
                probe = Tune(notes_, a0)
                if not [r for r in reference.matches(probe.rhythm, probe.intervals) if r.get("song") != song.sid]:
                    break
                played, by_key, last_midi, last_move, rhythm_played, rhythm_prev, prev_cell = (Counter(snapshot[0]), dict(snapshot[1]), snapshot[2], snapshot[3], Counter(snapshot[4]), snapshot[5], snapshot[6])
                source, choices = dict(snapshot[7]), dict(snapshot[8])
                on_beat[:] = snapshot[9]
                moves_seen[:] = snapshot[10]
                pairs_played, pair_cells, prev_pair, prev_pair_key, prev_pair_at = Counter(snapshot[11]), dict(snapshot[12]), snapshot[13], snapshot[14], snapshot[15]
                pair_kinds, source_kinds = Counter(snapshot[16]), Counter(snapshot[17])
            else:
                log.append(f"phrase at bar {w[0]}: a game's phrase drawn {COPY_TRIES} times running; the last kept")
        # the ending: the phrase's last note onto the drawn degree, where the last bar is a new cell (round 49: a recalled last
        # bar keeps its cell, as FFVI's recalled bars are identical by the word's count; the ending moved onto a recall had
        # made 33 of 76 bent recalls, differing from their source in the last interval alone)
        if ending in DEGREE_PCS and phrase_cells and phrase_cells[-1].pitches and choices.get(live[-1]) in ("new", "answered"):
            want = {(tonic + i) % 12 for i in DEGREE_PCS[ending]}
            last = phrase_cells[-1]
            options = [m for m in range(reg_w[0], reg_w[1] + 1) if m % 12 in want]
            if options:
                last.pitches[-1] = min(options, key=lambda m: (abs(m - last.pitches[-1]), m))
                last_midi = float(last.pitches[-1])
        prev_phrase, prev_phrase_start = phrase_cells, a0
        written_windows[w[0]] = (live, phrase_cells)
        if letters is not None and phrase_cells:
            if theme is None and letter_of(w[0]) == rhythm.THEME:
                theme = list(phrase_cells)                  # the song's theme: the first phrase the letters name so
                theme_bars = set(live)
            elif letter_of(w[0]) == rhythm.NEW:
                others.append(list(phrase_cells))
        log.append(f"bar {w[0]}: {relation}, {shape}" + (f" {phrase_size:.0f}" if phrase_size is not None else "") + f", ends {ending}, bars {[choices.get(k, '-') for k in live]}")
    if on_beat[1]:
        log.append(f"strong-beat notes on the chord: {on_beat[0]}/{on_beat[1]} ({on_beat[0] / on_beat[1]:.2f}; the song's rate {rate:.2f})")
    if moves_seen[1]:
        log.append(f"repeated notes: {moves_seen[0]}/{moves_seen[1]} ({moves_seen[0] / moves_seen[1]:.2f}; the song's rate {rep_rate:.2f})")
    # the notes, with their lengths from the articulation table
    notes = []
    for k in sorted(cells):
        a, b, _ = bars[k]
        cell = cells[k]
        for i, (p, m) in enumerate(zip(cell.positions, cell.pitches)):
            t = a + p
            until = a + cell.positions[i + 1] if i + 1 < len(cell.positions) else b
            gap = until - t
            if gap <= rhythm.NEAR:
                continue
            value = str(rhythm.position(gap, song.division))
            held = models["values"].draw((role, value, articulation), rng) if "values" in models else "held"
            notes.append((t, t + gap * (HELD if held == "held" else DETACHED), float(m)))
    if half_kinds:
        c = Counter(kd for ks in half_kinds.values() for kd in ks)
        log.append("halves (half_recall): " + ", ".join(f"{kd} {c[kd]}" for kd in ("same", "earlier", "new", "rest") if c[kd]) + f" over {len(half_kinds)} new bars")
    if pair_kinds:
        log.append("pairs (pair_recall): " + ", ".join(f"{kd} {pair_kinds[kd]}" for kd in tables.RECALL if pair_kinds[kd]) + f" over {sum(pair_kinds.values())} pairs drawn"
                   + ("; echoes point (recall_sources): " + ", ".join(f"{src} {source_kinds[src]}" for src in rhythm.RECALL_SOURCES if source_kinds[src]) if source_kinds else ""))
    return notes, figures, log


def habit_rel(models: dict) -> str:
    """The relation table's habit value a song draws under: its commonest, where it has one."""
    t = models["relations"].table if hasattr(models["relations"], "table") else models["relations"]
    habits = Counter()
    for c, votes in t.votes.items():
        if len(c) == len(t.conditionings) and "habit" in t.conditionings:
            habits[c[t.conditionings.index("habit")]] += sum(votes.values())
    return habits.most_common(1)[0][0] if habits else "mixed"


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
BREAKDOWN = 0.5                       # under this share of the median the band is thin: the part thins with it and does not lock to it


def thinned(env: tuple, ratio: float) -> tuple:
    """A free envelope scaled to the band's energy in the bar: the strikes allowed shrink with the band, to one
    where the band is nearly gone (under THIN, the caller rests the bar)."""
    low, high, downbeat, meter = env
    r = min(1.0, max(0.0, ratio))
    return (max(1, round(low * r)), max(1, round(high * r)), downbeat, meter)


def _free_figures(song: rhythm.Song, role: str, model: tables.Cache, manner, own: list, bars: list, habit: str,
                  rng: random.Random, hold=(), lock=None, envelope_of=None, within_of=None, lock_share: float = 1.0,
                  energy: list | None = None, extra_values: dict | None = None) -> list[str]:
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
    periods = getattr(song, "periods", {}).get(role, {})   # the part's period inside a part of the form: a held bar plays the bar a lag before
    for start, length, _, copy_of in form_spans(song, own):
        for i in range(length):
            k = start + i
            if own[k] == REST or (energy is not None and k < len(energy) and energy[k] < THIN):
                figures[k] = REST
                continue
            if copy_of is not None and figures[copy_of + i] != REST:
                figures[k] = figures[copy_of + i]
            elif k in periods and 0 <= k - periods[k] < k and figures[k - periods[k]] != REST:
                figures[k] = figures[k - periods[k]]
            elif k in hold:
                figures[k] = own[k]
            else:
                env = envelope_of(own[k], meters[k])
                thin = energy is not None and k < len(energy) and energy[k] < BREAKDOWN
                if thin:
                    env = thinned(env, energy[k])
                bar_lock = None if thin else lock.get(k)        # in a breakdown the band's hits are not the band: no lock
                values = {"part": role, "meter": meters[k], "previous": previous or rhythm.START, "habit": habit, "feel": rhythm.song_feel(song), "tempo": rhythm.band(song.bpm), **(extra_values or {})}
                unit = tables.Unit(song.sid, song.game, "", values)
                # the filters, loosened in turn where nothing passes: the manner, the envelope and the lock; then
                # without the lock (the band asks more strikes than the habit: the part keeps its density and locks
                # where it can); then without the envelope; then the manner alone. Never the song's own bar: a
                # free-written part copies nothing of the part it replaces.
                ladder = [lambda f, _l=bar_lock, _e=env: manner.fits(f) and within_of(f, _e) and locked(f, _l, lock_share),
                          lambda f, _e=env: manner.fits(f) and within_of(f, _e),
                          lambda f, _l=bar_lock: manner.fits(f) and locked(f, _l, lock_share),
                          manner.fits]
                figure = None
                for fit in ladder:
                    candidate = model.draw(unit, previous, played, rng, keep=fit)
                    for _ in range(TRIES):
                        if fit(candidate):
                            figure = candidate
                            break
                        candidate = model.table.draw(model.table.context(unit), rng, values, floored=False, floor_k=model.table.chain_floor)
                    if figure is not None:
                        break
                figures[k] = figure if figure is not None else last_resort(manner, model, unit, values, rng)
            played[figures[k]] += 1
            previous = figures[k]
    for start, length, copy_of in getattr(song, "copies", {}).get(role, []):   # the band back with the theme: the part's own bars again
        for i in range(length):
            k, src = start + i, copy_of + i
            if k < len(figures) and src < len(figures) and own[k] != REST and figures[src] != REST:
                figures[k] = figures[src]
    return figures


def last_resort(manner, model: tables.Cache, unit: tables.Unit, values: dict, rng: random.Random) -> str:
    """The figure for a bar no draw fits: on a kit (FreeManner with pieces),
    any bar the table knows that the kit can play, evenly (the vocabulary's
    even share, kept to the kit: a bar the plan has the kit in is never
    silent for want of a draw, round 58); else the table's own draw."""
    kit = getattr(manner, "kit", None)
    if kit is not None:
        fits = [f for f in sorted(manner.known) if f != REST and manner.fits(f)]
        if fits:
            return rng.choice(fits)
    return model.table.draw(model.table.context(unit), rng, values, floored=False, floor_k=model.table.chain_floor)


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
        values = {"part": role, "meter": meter, "previous": previous or rhythm.START, "habit": habit, "feel": rhythm.song_feel(song), "tempo": rhythm.band(song.bpm)}
        unit = tables.Unit(song.sid, song.game, "", values)
        figure = model.draw(unit, None if previous == REST else previous, state["played"], rng, keep=full)
        nearly = None
        for _ in range(TRIES):                              # the urn or the floor may still hand back what is refused
            if full(figure):
                return figure
            if nearly is None and fit(figure):
                nearly = figure
            figure = model.table.draw(model.table.context(unit), rng, values, floored=False, floor_k=model.table.chain_floor)
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
          free: bool = False, plays: list | None = None, kit_value: str | None = None) -> tuple[list[tuple[float, str]], list[str]]:
    """The drums written for the song, a group of pieces at a time (the
    module): `models` maps a group (a tuple of letters, rhythm.DRUM_GROUPS)
    to its Cache (a group of every letter: the whole kit, its table's part
    "drums"); `locks` a group to its lock; `hold` as bass(). `free`: no
    original to follow (FreeManner, free_drum_envelope), the `habit` given
    (drawn from a pack's table: the kit's, or {group: its own}) and the kit
    the song's pieces; with `plays` (a planned song's bars) a group may
    also draw a rested bar, at its table's rate; `kit_value` (the letters
    of the pieces the song's kit strikes, kit_pieces) conditions the draw
    and narrows the kit to them. Returns the hits (start in beats, piece
    letter) and the merged figures."""
    locks = locks or {}
    bars = [(a, b, struck) for _, a, b, struck in rhythm.all_bars_of(song, R.DRUMS)]
    whole = [rhythm.drum_figure(struck, song) if struck else REST for a, _, struck in bars]
    kit = {rhythm.LETTERS.get(piece, "o") for piece in song.pieces.values() if piece and piece != "none"}
    if kit_value:                                           # the pieces the song's kit strikes (kit_pieces, round 58): the manner keeps a figure
        kit &= set(kit_value)                               # on them alone, so a bar drawn from another kit's songs is one this kit can play
    merged = [[] for _ in bars]
    by_group = {}
    part_of = lambda letters: R.DRUMS if set(letters) >= set(rhythm.LETTERS.values()) else "drums-" + "".join(letters)   # noqa: E731
    for letters, model in models.items():
        own = plays_as_own(plays, bars) if plays is not None else [rhythm.drum_group(f, letters) for f in whole]
        if all(f == REST for f in own) and not (free and kit & set(letters)):
            continue
        if free:
            manner = FreeManner(model.table.vocabulary, kit & set(letters), song.division, rests=plays is not None)
            group_habit = (habit.get(letters) if isinstance(habit, dict) else habit) or "medium mixed"
            envelope_of = free_drum_envelope(kit & set(letters), group_caps(habit))
        else:
            manner = DrumManner(None, model.table.vocabulary, figures=[f for f in own if f != REST])
            mine = [u for u in rhythm.drum_group_units([song], letters)]
            group_habit = habit or (mine[0].values["habit"] if mine else "medium mixed")
            envelope_of = drum_envelope
        if free:
            figures = _free_figures(song, part_of(letters), model, manner, own, bars, group_habit, rng, hold,
                                    locks.get(letters), envelope_of=envelope_of, within_of=drum_within, lock_share=LOCK_DRUMS,
                                    extra_values={"kit": kit_value} if kit_value else None)   # the kit's pieces (round 58)
        else:
            figures = _figures(song, part_of(letters), model, manner, own, bars, group_habit, rng, hold, locks.get(letters),
                               envelope_of=envelope_of, within_of=drum_within, lock_share=LOCK_DRUMS)
        by_group[letters] = figures
        for k, f in enumerate(figures):
            merged[k] += [(Fraction(t.partition(":")[0]), t.partition(":")[2]) for t in rhythm._tokens(f)]
    if free and plays is not None and by_group:
        # a bar the plan has the drums in never rests whole: where every group drew a rest, the kit's main group (the
        # one playing the most bars) plays a figure of its own there, drawn without the rest
        main = max(by_group, key=lambda g: sum(1 for f in by_group[g] if f != REST))
        model = models[main]
        manner = FreeManner(model.table.vocabulary, kit & set(main), song.division, rests=False)
        group_habit = (habit.get(main) if isinstance(habit, dict) else habit) or "medium mixed"
        for k, (a, b, _) in enumerate(bars):
            if not (k < len(plays) and plays[k]) or merged[k]:
                continue
            before = by_group[main][k - 1] if k else REST
            values = {"part": part_of(main), "meter": max(1, round(b - a)), "previous": before if before != REST else rhythm.START, "habit": group_habit, **({"kit": kit_value} if kit_value else {}),
                      "feel": rhythm.song_feel(song), "tempo": rhythm.band(song.bpm)}
            unit = tables.Unit(song.sid, song.game, "", values)
            env = free_drum_envelope(kit & set(main))(None, values["meter"])
            f = None
            for _ in range(TRIES):
                f = model.table.draw(model.table.context(unit), rng, values, floored=False, floor_k=model.table.chain_floor)
                if manner.fits(f) and drum_within(f, env):
                    break
                f = None
            if f is None:                                   # nothing drawn fits the kit: any bar the kit can play (round 58)
                f = last_resort(manner, model, unit, values, rng)
            if f != REST:
                by_group[main][k] = f
                merged[k] += [(Fraction(t.partition(":")[0]), t.partition(":")[2]) for t in rhythm._tokens(f)]
    figures = [" ".join(f"{p}:{x}" for p, x in sorted(set(tokens))) or REST for tokens in merged]
    hits = []
    for (a, b, _), figure in zip(bars, figures):
        for t in rhythm._tokens(figure):
            at, _, letter = t.partition(":")
            if a + float(Fraction(at)) < b:
                hits.append((a + float(Fraction(at)), letter))
    return hits, figures


def plays_as_own(plays, bars: list) -> list:
    """A part's own bars for a planned song: "0" where the plan has it play, REST where it rests."""
    return ["0" if (k < len(plays) and plays[k]) else REST for k in range(len(bars))]


def bass(song: rhythm.Song, model: tables.Cache, rng: random.Random, habit: str | None = None,
         key: tuple | None = None, hold=(), lock=None, free: bool = False, energy: list | None = None,
         plays: list | None = None, register: int | None = None, sounds=None,
         figures: list | None = None, shared: dict | None = None, kind: str | None = None,
         models: dict | None = None, lock_share: float = 1.0, ceiling: int | None = None) -> tuple[list[tuple[float, float, float]], list[str]]:
    """The bass written for the song: its notes (start, end in beats, midi)
    and the figures drawn, one a bar; the bars in `hold` (indices among the
    song's bars) keep the song's own figure; `lock` maps a bar's index to
    (positions a figure must strike, beats it must leave), the song's own
    locking to the band. `free`: no original to follow (FreeManner,
    free_envelope by the habit, which the caller then gives). `plays`: a
    planned song's bars the part plays in (no original: the bars the plan
    has it play, playing anything), with `register` (the midi floor) and
    `sounds` (the share of its gap a note sounds) given instead of read."""
    lock = lock or {}
    own = song.notes.get(R.BASS, [])
    if habit is None:
        mine = rhythm.bass_units([song])
        habit = mine[0].values["habit"] if mine else "medium roots no-octaves"
    manner = FreeManner(model.table.vocabulary, division=song.division) if free else Manner(song, R.BASS, model.table.vocabulary)
    pitched = sorted(n[2] for n in own if not math.isnan(n[2]))
    low = register if register is not None else round(pitched[int(LOW * (len(pitched) - 1))]) if pitched else 36
    high = ceiling if ceiling is not None else low + REACH      # the register's ceiling: where the game plays the sample (round 34)
    sounds = sounds if sounds is not None else sounded(own)
    tonic, mode = key if key else (0, "major")
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]}
    bars = [(a, b, struck) for _, a, b, struck in rhythm.all_bars_of(song, R.BASS)]
    own = plays_as_own(plays, bars) if plays is not None else [rhythm.figure(struck, a, song) if struck else REST for a, _, struck in bars]

    def chord_at(k):
        c = rhythm._chord_at(song.chords, bars[k][0])
        return (c.root, c.shape) if c is not None and c.root is not None and c.fit >= FIT else None

    words = habit.split()
    if figures is not None:                                 # a second line's figures given (the second_figures table, under the line's own)
        figures = [f if o != REST else REST for f, o in zip(figures, own)]
    elif free:
        figures = _free_figures(song, R.BASS, model, manner, own, bars, habit, rng, hold, lock, envelope_of=free_envelope(habit), energy=energy,
                                lock_share=lock_share)
    else:
        figures = _figures(song, R.BASS, model, manner, own, bars, habit, rng, hold, lock,
                           chord_at=chord_at, reuse=REUSE.get(words[1] if len(words) > 1 else "", 0.5))
    notes, last_root, previous = [], tonic, None
    beside = kind in VOICE_KINDS and shared is not None and models is not None and "voice_intervals" in models and "voice_moves" in models
    prev_steps, prev_midi, last_with = rhythm.START, None, None   # a second voice following the line: its last interval with it, its last note
    for k, ((a, b, _), figure) in enumerate(zip(bars, figures)):
        new, last_root, previous = realize(figure, a, b, song, low, sounds, scale, last_root, previous, runs_to=first_onset(figures, bars, k + 1), high=high)
        if shared is not None and not beside:               # the line: its notes for the voice beside it
            for start, _, midi in new:
                shared[("line", (k, rhythm.position(start - a, song.division)))] = midi
        elif beside:                                        # the second voice: with the line, the note both words agree on; alone, its own
            repitched = []                                  # move (voice_intervals, voice_moves, counted on the bass too: FFVI's second bass
            for start, end, midi in new:                    # plays the line's pitch class at 78 % of their shared onsets; drawn apart, 31 %)
                p = rhythm.position(start - a, song.division)
                ref = shared.get(("line", (k, p)))
                if ref is not None:
                    moved = (scale_index(int(round(ref)), scale) - scale_index(int(round(last_with)), scale)) if last_with is not None else 0
                    target, steps = beside_pitch(models, R.BASS, kind, scale, rng, ref, prev_steps, prev_midi, moved)
                    if target is not None:
                        prev_steps, last_with = str(steps), ref
                else:
                    target, _ = beside_pitch(models, R.BASS, kind, scale, rng, None, prev_steps, prev_midi, 0)
                if target is not None:
                    midi = float(in_register(target, (low, high)))
                prev_midi = midi
                repitched.append((start, end, midi))
            new = repitched
            previous = new[-1][2] if new else previous
        notes += new
    return notes, figures


def place(pc: int, low: int, previous: float | None, octave_up: bool = False, high: int | None = None) -> int:
    """The midi note of a pitch class in the register: the octave nearest the
    note before (the lower when as near), the lowest with no note before;
    an octave up (r) is the lowest placing raised an octave. `high`: the
    register's ceiling (the range the game plays the bass's sample in, round
    34); the floor plus REACH without one."""
    bottom = low + (pc - low) % 12
    if octave_up:
        return bottom + 12 if high is None or bottom + 12 <= high else bottom   # no room for the octave: the plain placing
    if previous is None:
        return bottom
    options = [m for m in range(bottom, (high if high is not None else low + REACH) + 1, 12)] or [bottom]
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


def realize(figure: str, a: float, b: float, song: rhythm.Song, low: int, sounds, scale: set,
            last_root: int, previous: float | None = None, runs_to: float | None = None, high: int | None = None) -> tuple[list, int, float | None]:
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
        until = a + float(tokens[i + 1][0]) if i + 1 < len(tokens) else (runs_to if runs_to is not None and runs_to > b - rhythm.NEAR else b)
        if until <= start:
            continue
        root, shape = chords[i]
        if mark == "+":
            toward = None
            for j in range(i + 1, len(tokens)):                 # the next note of the bar that is not itself passing
                if tokens[j][1] != "+":
                    toward = place(tone(chords[j][0], chords[j][1], tokens[j][1], scale), low, previous, tokens[j][1] == "r", high=high)
                    break
            if toward is None and previous is not None:
                toward = round(previous) + direction * 2
            midi = passing(previous, toward, scale, low, root)
            if high is not None and not low <= midi <= high:        # a run of passing tones turns at the register's edge instead of
                direction = -direction                              # climbing out of where the game plays the sample (round 34: a bass
                midi = in_register(midi, (low, high))               # of bars all "+" had walked from 42 to 79 on a 32-40 sample)
        else:
            midi = place(tone(root, shape, mark, scale), low, previous, mark == "r", high=high)
        if previous is not None and midi != previous:
            direction = 1 if midi > previous else -1
        out.append((start, start + (until - start) * share_at(sounds, until - start), float(midi)))
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
    share = rhythm.sounded_share(notes)
    return min(SOUNDS[1], max(SOUNDS[0], share)) if share is not None else 0.8
