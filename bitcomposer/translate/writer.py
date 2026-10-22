"""A part written from the tables into a real song, in place of the song's
own (phase 3's acceptance by ear, docs/idiom/phase-3-tables.md): the bass.

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
Terra), must sit on the song's own grid, and may not strike more than
DENSER times the song's own bass does in a bar (its median over the bars
it plays, or its busiest bar). The bars the song's own bass
rests through are left silent and never drawn for (the arrangement stays
the song's: which bars the bass plays is the arrangement table's, not
this one's), and a playing bar never draws a rest. Each token becomes a
note:
its pitch the chord tone its mark names in the chord sounding at its
onset (R the root, r the root an octave up, 3 5 7 the chord's own, s the
sus tone, + a passing tone: the key's scale step above the root, or the
step below where the scale has none, ? the root; no chord fitting, the
last root, or the tonic), in the song's own bass register (the octave up
from the lowest tenth of its bass notes); its length to the next onset in
the bar or the bar's end, sounding the share of that the song's bass
sounds of its own gaps (the median, between SOUNDS). A bar of another
length than the meter's is left silent.
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
DENSER = 1.5                          # a new figure strikes at most this many times the song's own median a bar
SOUNDS = (0.3, 1.0)                   # the sounded share of a note's gap is kept within these


def fit(units, floor_cls=rhythm.BarCells) -> tables.Cache:
    """The model the writer draws from, fitted on these units (the song written for left out by the caller)."""
    units = list(units)
    return tables.Cache.fit(units, SHAPE, name="bass", votes=tables.SHARES, floor=floor_cls(units), discount=DISCOUNT,
                            covers=len(floor_cls.COVERS))


def on_grid(figure: str, division: int) -> bool:
    """Whether a figure's positions all sit on a grid of this many steps a beat."""
    return all(division % Fraction(t.partition(":")[0]).denominator == 0 for t in rhythm._tokens(figure))


def fits(figure: str, song: rhythm.Song, known: set, cap: int) -> bool:
    """Whether a new figure may be written into the song (the module): a bar some song played, on the song's grid, no denser than cap."""
    return figure != REST and figure in known and on_grid(figure, song.division) and len(rhythm._tokens(figure)) <= cap


def bass(song: rhythm.Song, model: tables.Cache, rng: random.Random, habit: str | None = None,
         key: tuple | None = None) -> tuple[list[tuple[float, float, float]], list[str]]:
    """The bass written for the song: its notes (start, end in beats, midi) and the figures drawn, one a bar."""
    own = song.notes.get(R.BASS, [])
    playing = [len(struck) for _, struck in rhythm.bars_of(song, R.BASS) if struck]
    cap = max(max(playing), round(DENSER * statistics.median(playing))) if playing else 8
    if habit is None:
        mine = rhythm.bass_units([song])
        habit = mine[0].values["habit"] if mine else "medium roots no-octaves"
    pitched = sorted(n[2] for n in own if not math.isnan(n[2]))
    low = round(pitched[int(LOW * (len(pitched) - 1))]) if pitched else 36
    sounds = sounded(own)
    tonic, mode = key if key else (0, "major")
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]}
    rests = {round(a, 6) for a, struck in rhythm.bars_of(song, R.BASS) if not struck}
    notes, figures, previous, last_root, played = [], [], None, tonic, Counter()
    for a, b in song.bars:
        if round(b - a) != song.meter:
            continue
        if round(a, 6) in rests:
            figures.append(REST)
            previous = REST
            continue
        values = {"part": R.BASS, "meter": song.meter, "previous": previous or rhythm.START, "habit": habit}
        unit = tables.Unit(song.sid, song.game, "", values)
        figure = model.draw(unit, None if previous == REST else previous, played, rng,
                            keep=lambda f: fits(f, song, model.table.vocabulary, cap))
        for _ in range(40):                                 # the urn or the floor may still hand back what fits() refuses
            if fits(figure, song, model.table.vocabulary, cap):
                break
            figure = model.table.draw(model.table.context(unit), rng, values)
        else:
            figure = "0:R"                                  # nothing fit: the root on the one
        new, last_root = realize(figure, a, b, song, low, sounds, scale, last_root)
        notes += new
        figures.append(figure)
        played[figure] += 1
        previous = figure
    return notes, figures


def realize(figure: str, a: float, b: float, song: rhythm.Song, low: int, sounds: float, scale: set,
            last_root: int) -> tuple[list, int]:
    """A figure's tokens as notes in the bar [a, b) (see the module); returns them and the last chord root used."""
    tokens = [(Fraction(t.partition(":")[0]), t.partition(":")[2]) for t in rhythm._tokens(figure)]
    out = []
    for i, (p, mark) in enumerate(tokens):
        start = a + float(p)
        until = a + float(tokens[i + 1][0]) if i + 1 < len(tokens) else b
        if until <= start:
            continue
        c = rhythm._chord_at(song.chords, start)
        if c is not None and c.root is not None and c.fit >= FIT:
            last_root, shape = c.root, c.shape
        else:
            shape = ""
        pc = tone(last_root, shape, mark, scale)
        midi = low + (pc - low) % 12 + (12 if mark == "r" else 0)
        out.append((start, start + (until - start) * sounds, float(midi)))
    return out, last_root


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
