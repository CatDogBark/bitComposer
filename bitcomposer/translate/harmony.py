"""The chords under a song, bar by bar, and its key.

A chord lasts bars, and a listener hears it change where the ground moves:
the bass settles on another root, or the chordal voices sound another set
of pitch classes. On the chord check (twelve songs, docs/idiom/phase-1-
readers.md) a reader that relabelled every beat made 1.4 to 39 times the
changes the listener marked, flipping on each note of an arpeggio, each
step of a bass figure, and each time the texture thinned or filled; the
bass's most-sounded pitch class in the bar and the chordal voices' pitch
set, compared bar to bar, matched the marks on most songs. So: each bar's
pitch classes are gathered (each note weighted by its loudness, how much
of the bar it sounds and its part: the bass twice, held and struck chords
one and a half, the melody and counter-line a half, drums and doublings
left out); a bar starts a new chord where its bass root differs from the
last sounding bar's or its chordal set has changed by half (Jaccard); a
bar where nothing tonal sounds carries the chord on, so a chord that stops
and restarts is one chord. Each span's chord is the shape on the root
fitting its pooled pitch classes best, a root the bass holds preferred; a
span with no chordal voice sounding is an implied chord (stated False).
The key is the major or minor profile (Krumhansl and Kessler's) the whole
song's pitch classes (every tonal voice alike, weighted by part they
skewed it: Locke's G major read as G minor) correlate with best."""
import bisect
import math
from dataclasses import dataclass

from . import roles as roles_mod

NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
SHAPES = {                           # intervals from the root
    "": (0, 4, 7), "m": (0, 3, 7), "dim": (0, 3, 6), "aug": (0, 4, 8),
    "sus4": (0, 5, 7), "sus2": (0, 2, 7), "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11),
    "m7": (0, 3, 7, 10), "m7b5": (0, 3, 6, 10), "5": (0, 7),
}
# simpler chords first where two fit alike (a triad over its seventh, a fifth over its triad)
PLAIN = {"": 1.0, "m": 1.0, "5": 0.9, "7": 0.92, "m7": 0.92, "maj7": 0.9, "dim": 0.9, "sus4": 0.88,
         "sus2": 0.86, "m7b5": 0.86, "aug": 0.84}
MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)
QUIET = 0.15                         # a beat with less sounding than this (summed loudness x share) has no chord
SOUNDING = 0.2                       # a bar with tonal notes through less of it than this (in beats a beat) is quiet
SET_SHARE = 0.15                     # a pitch class with this share of the chordal voices' sounding in a bar is in its set
SET_CHANGE = 0.5                     # the Jaccard distance between two bars' sets that is a new chord
BASS_ROOT = 1.1                      # the fit's lift for the root the bass holds
HALF_BARS = False                    # read the chords on half bars (an experiment's switch)


@dataclass
class Chord:
    start: float                     # in beats
    end: float
    root: int | None                 # pitch class; None: no chord
    shape: str
    fit: float                       # how well the shape fits what sounds, 0-1
    stated: bool = True              # a chordal voice sounds it; False: implied by the bass and the tune alone

    @property
    def name(self) -> str:
        return "N" if self.root is None else NAMES[self.root] + self.shape


WEIGHTS = {roles_mod.BASS: 2.0, roles_mod.HARMONY: 1.5, roles_mod.ACCOMP: 1.5, roles_mod.ARP: 1.5,
           roles_mod.MELODY: 0.5, roles_mod.COUNTER: 0.5}


def _tonal(song, roles) -> tuple[list, dict]:
    weight = {r.voice: WEIGHTS.get(r.role, 1.0) for r in roles if r.role not in (roles_mod.DRUMS, roles_mod.DOUBLE)}
    return [p for p in song.notes if p.voice in weight and p.midi is not None], weight


def profiles(song, grid, roles, by_part: bool = True) -> list[list[float]]:
    """Each beat's pitch-class weights (by_part: weighted by part, for chords;
    else every tonal voice alike, for the key)."""
    notes, weight = _tonal(song, roles)
    if not by_part:
        weight = {v: 1.0 for v in weight}
    n = len(grid.beat_times)
    out = [[0.0] * 12 for _ in range(n)]
    for p in notes:
        b0 = grid.beats(p.start)
        b1 = grid.beats(p.end) if p.end is not None else b0 + 1
        w = p.level * weight[p.voice]
        for b in range(max(0, math.floor(b0)), min(n, math.ceil(b1))):
            share = min(b1, b + 1) - max(b0, b)
            if share > 0:
                out[b][round(p.midi) % 12] += w * share
    return out


def _fit(pcs: list[float], root: int, shape: str) -> float:
    iv = SHAPES[shape]
    norm = math.sqrt(sum(x * x for x in pcs))
    return sum(pcs[(root + i) % 12] for i in iv) / (norm * math.sqrt(len(iv))) if norm else 0.0


def _match(pcs: list[float]) -> tuple[int | None, str, float]:
    if sum(pcs) < QUIET:
        return None, "", 0.0
    best = (None, "", 0.0)
    for root in range(12):
        for shape in SHAPES:
            fit = _fit(pcs, root, shape)
            if fit * PLAIN[shape] > best[2] * PLAIN.get(best[1], 1.0):
                best = (root, shape, fit)
    return best


def _bars(grid) -> list[int]:
    """The bar lines as beat indices, from the first beat to past the last."""
    n = len(grid.beat_times)
    lines = sorted({min(n, max(0, round(grid.beats(t)))) for t in grid.bar_times})
    if not lines or lines[0] > 0:
        lines = [0] + lines
    if lines[-1] < n:
        lines.append(n)
    lines = [x for i, x in enumerate(lines) if i == 0 or x > lines[i - 1]]
    if HALF_BARS:
        halves = [(a + b) // 2 for a, b in zip(lines, lines[1:]) if b - a >= 4]
        lines = sorted(set(lines) | set(halves))
    return lines


def chords(song, grid, roles) -> list[Chord]:
    """The chords bar by bar: a bar starts a new chord where the bass's root
    (its most-sounded pitch class) differs from the last sounding bar's or the
    chordal voices' pitch-class set has changed by SET_CHANGE; a bar where
    nothing tonal sounds carries the chord on. Each span's chord is the
    shape fitting its pooled pitch classes best, the bass's root preferred."""
    notes, weight = _tonal(song, roles)
    bass = {r.voice for r in roles if r.role == roles_mod.BASS}
    chordal = {r.voice for r in roles if r.role in (roles_mod.HARMONY, roles_mod.ACCOMP, roles_mod.ARP)}
    edges = _bars(grid)
    nb = len(edges) - 1
    if nb < 1:
        return []
    prof = [[0.0] * 12 for _ in range(nb)]
    sounding = [0.0] * nb                             # beats of tonal notes in the bar (voices summed)
    bass_dur = [[0.0] * 12 for _ in range(nb)]
    set_dur = [[0.0] * 12 for _ in range(nb)]
    for p in notes:
        b0 = grid.beats(p.start)
        b1 = grid.beats(p.end) if p.end is not None else b0 + 1
        pc = round(p.midi) % 12
        i = max(0, bisect.bisect_right(edges, b0) - 1)
        while i < nb and edges[i] < b1:
            share = min(b1, edges[i + 1]) - max(b0, edges[i])
            if share > 0:
                prof[i][pc] += p.level * weight[p.voice] * share
                sounding[i] += share
                if p.voice in bass:
                    bass_dur[i][pc] += share
                if p.voice in chordal:
                    set_dur[i][pc] += share
            i += 1
    def root_of(d):
        return max(range(12), key=d.__getitem__) if sum(d) > 0 else None
    def set_of(d):
        total = sum(d)
        return frozenset(k for k in range(12) if total and d[k] / total >= SET_SHARE)
    spans = []                                        # [first bar, past the last]
    last = None                                       # the last sounding bar's (root, set)
    for i in range(nb):
        if sounding[i] < SOUNDING * (edges[i + 1] - edges[i]):
            if spans:
                spans[-1][1] = i + 1
            else:
                spans.append([i, i + 1])
            continue
        root, pcs = root_of(bass_dur[i]), set_of(set_dur[i])
        new = not spans
        if last is not None:
            if root is not None and last[0] is not None and root != last[0]:
                new = True                            # the bass settles on another root
            if pcs and last[1] and 1 - len(pcs & last[1]) / len(pcs | last[1]) >= SET_CHANGE:
                new = True                            # the chordal voices sound another set
        if new:
            spans.append([i, i + 1])
        else:
            spans[-1][1] = i + 1
        last = (root, pcs)
    out = []
    for a, b in spans:
        pooled = [sum(prof[i][k] for i in range(a, b)) for k in range(12)]
        if sum(sounding[a:b]) < SOUNDING * (edges[b] - edges[a]):
            c = Chord(edges[a], edges[b], None, "", 0.0)
        else:
            root, shape, fit = _match(pooled)
            held = root_of([sum(bass_dur[i][k] for i in range(a, b)) for k in range(12)])
            if held is not None and root != held:
                shape_h = max(SHAPES, key=lambda sh: _fit(pooled, held, sh) * PLAIN[sh])
                fit_h = _fit(pooled, held, shape_h)
                if fit_h * PLAIN[shape_h] * BASS_ROOT >= fit * PLAIN[shape]:
                    root, shape, fit = held, shape_h, fit_h
            stated = any(sum(set_dur[i]) > 0 for i in range(a, b))
            c = Chord(edges[a], edges[b], root, shape, fit, stated)
        if out and out[-1].root == c.root and out[-1].shape == c.shape:
            out[-1].end = c.end
            out[-1].fit = max(out[-1].fit, c.fit)
            out[-1].stated = out[-1].stated or c.stated
        else:
            out.append(c)
    return out


def key(song, grid, roles) -> tuple[int, str, float]:
    """The key: (tonic pitch class, "major" or "minor", how well its profile correlates)."""
    total = [0.0] * 12
    for pcs in profiles(song, grid, roles, by_part=False):
        for i, x in enumerate(pcs):
            total[i] += x
    best = (0, "major", -1.0)
    for tonic in range(12):
        for mode, prof in (("major", MAJOR), ("minor", MINOR)):
            r = _corr(total, [prof[(i - tonic) % 12] for i in range(12)])
            if r > best[2]:
                best = (tonic, mode, r)
    return best


def _corr(x, y) -> float:
    mx, my = sum(x) / 12, sum(y) / 12
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else 0.0
