"""The chords under a song, beat by beat, and its key.

On each beat, the pitch classes sounding (each note weighted by its
loudness, how much of the beat it sounds and its part: the bass twice, since
it most often holds the root, held and struck chords one and a half, the
melody and counter-line a half, since their passing notes are not the
chord; drums and doublings left out) are matched against chord shapes on
every root. A beat then keeps its neighbour's chord where that fits it
nearly as well as its own best (a melody's passing note had split a bar of
C into C, Csus4, C), and runs of one chord are its span. The key
is the major or minor profile (Krumhansl and Kessler's) the whole song's
pitch classes correlate with best."""
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


@dataclass
class Chord:
    start: float                     # in beats
    end: float
    root: int | None                 # pitch class; None: no chord
    shape: str
    fit: float                       # how well the shape fits what sounds, 0-1

    @property
    def name(self) -> str:
        return "N" if self.root is None else NAMES[self.root] + self.shape


WEIGHTS = {roles_mod.BASS: 2.0, roles_mod.HARMONY: 1.5, roles_mod.ACCOMP: 1.5, roles_mod.ARP: 1.5,
           roles_mod.MELODY: 0.5, roles_mod.COUNTER: 0.5}
KEEP = 0.9                           # a neighbour's chord kept on a beat it fits this nearly as well


def _tonal(song, roles) -> tuple[list, dict]:
    weight = {r.voice: WEIGHTS.get(r.role, 1.0) for r in roles if r.role not in (roles_mod.DRUMS, roles_mod.DOUBLE)}
    return [p for p in song.notes if p.voice in weight and p.midi is not None], weight


def profiles(song, grid, roles) -> list[list[float]]:
    """Each beat's pitch-class weights."""
    notes, weight = _tonal(song, roles)
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


def chords(song, grid, roles) -> list[Chord]:
    """The chords, beat by beat, a beat keeping its neighbour's where that fits
    it nearly as well, runs of one merged."""
    pcs_all = profiles(song, grid, roles)
    best = [_match(pcs) for pcs in pcs_all]
    for _ in range(2):                   # each pass lets a run grow by a beat either way
        for b in range(len(best)):
            here = best[b]
            if here[0] is None:
                continue
            for nb in (b - 1, b + 1):
                if 0 <= nb < len(best) and best[nb][0] is not None and best[nb][:2] != here[:2]:
                    fit = _fit(pcs_all[b], best[nb][0], best[nb][1])
                    if fit * PLAIN[best[nb][1]] >= KEEP * here[2] * PLAIN[here[1]]:
                        here = (best[nb][0], best[nb][1], fit)
            best[b] = here
    out = []
    for b, (root, shape, fit) in enumerate(best):
        if out and out[-1].root == root and out[-1].shape == shape:
            out[-1].end = b + 1
            out[-1].fit = max(out[-1].fit, fit)
        else:
            out.append(Chord(b, b + 1, root, shape, fit))
    return out


def key(song, grid, roles) -> tuple[int, str, float]:
    """The key: (tonic pitch class, "major" or "minor", how well its profile correlates)."""
    total = [0.0] * 12
    for pcs in profiles(song, grid, roles):
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
