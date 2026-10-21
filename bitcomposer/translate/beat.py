"""The beat and bar a song's notes sit on, from their onsets.

First the grid's unit (the tatum): the longest step that the gaps between
onsets are whole multiples of, within the jitter a driver's timer gives its
key-ons (AKAO's wander by 5 ms). Then locked to the song: the unit and its
phase fitted to the onsets' own times by least squares, over a window that
grows to the whole song (a unit fitted from neighbouring gaps can be 0.2 ms
off, which over a minute of FFVI's battle theme is a sixteenth). Then the
beat. The pulse first: the finest multiple of the unit that nearly every
point of has an onset. Above it the levels it groups into, by twos, or
with one three where the pulse repeats every three more than every two.
The beat is the level of those (or one finer, resting on some of its
points) a listener taps: the one the song's typical voice plays about one
note a beat at, at a tempo near the one listeners lean toward. Each choice
was tuned by ear, 22 songs of 9 games tapped (Kefka at 80, not 160; Kids
Run Through the City in threes at 110, not 73 in fours; The Phantom
Train's 12/8 at 54; Aquatic Ambiance at 75 under its arpeggio's 150). The bar: the beat count whose accents
repeat most strongly, its downbeat where they are loudest. Swing: where
the off-beat falls.

Before any of it, each voice's lag behind the others is taken out (a
driver keying a part a tick late, all song long), and a roll on no grid of
the song's (notes five to the eighth) is left out; reading.py leaves out a
voice echoing another, too.

A song keeps its tempo but not always its phase: a held note of an odd
length, a fermata, the loop's jump move the grid (FFVI's battle theme holds
its grid from 0 to 15 s and from 25 to 40, half a step off in between). So
the grid is followed onset by onset and taken again where three onsets in a
row miss it: a song is sections, each with its own grid, the beat counted
on across them."""
import bisect
import math
import statistics
from dataclasses import dataclass, field

SLOW, FAST = 40.0, 240.0             # BPM a beat may have
JITTER = 0.006                       # seconds an onset may sit off its grid point
TATUM_FIT = 0.75                     # the share of onset gaps the grid's unit must divide
FILLED = 0.85                        # the share of a pulse's points that have an onset
FREE = 0.8                           # under this share of onsets on a grid, a song is in free time
MULTIPLES = (1, 2, 3, 4, 6, 8, 9, 12, 16, 18, 24, 32, 36, 48)   # units a beat may be (Kakariko Village's 12/8: 18)


@dataclass
class Section:
    """A stretch of the song on one grid."""
    start: float                     # its first onset
    end: float                       # its last onset on its grid
    unit: float                      # seconds a grid step
    phase: float                     # a grid point's time
    first: float = 0.0               # its first beat's time
    meter: int = 4                   # beats a bar
    downbeat: int = 0                # its first bar's first beat, counted from `first`

    @property
    def period(self) -> float:
        return self.unit * self.division

    division: int = 1                # grid steps a beat (set with the song's beat)


@dataclass
class Grid:
    """A song's beat: its sections, and the beats and bars through them."""
    unit: float                      # seconds a grid step, over the song
    division: int                    # grid steps a beat (2: eighths, 3: triplets, 4: sixteenths, 12: both)
    sections: list
    beat_times: list                 # every beat, in order
    bar_times: list                  # every bar's first beat
    on_grid: float                   # the share of onsets, by loudness, on their section's grid
    swing: float                     # where the off-beat falls in the beat (0.5: straight)
    lags: dict = field(default_factory=dict)   # voice -> seconds it plays behind the others (a tick late)
    ornaments: set = field(default_factory=set)  # voices left out of the grid (rolls)
    loose: bool = False              # followed loosely, on no grid (beat_times then uneven)

    @property
    def bpm(self) -> float:
        """The tempo, the sections' weighted by their length."""
        total = sum(x.end - x.start for x in self.sections) or 1.0
        return sum(60 / x.period * (x.end - x.start) for x in self.sections) / total

    @property
    def meter(self) -> int:
        """The bar most of the song is in."""
        weights = {}
        for x in self.sections:
            weights[x.meter] = weights.get(x.meter, 0.0) + x.end - x.start
        return max(weights, key=weights.get) if weights else 4

    def period_at(self, t: float) -> float:
        """The beat's length at time t: its section's."""
        for x in self.sections:
            if t <= x.end:
                return x.period
        return self.sections[-1].period if self.sections else 0.5

    def beats(self, t: float) -> float:
        """A time in beats from the first beat (between two beats, the fraction of the way)."""
        b = self.beat_times
        if not b:
            return 0.0
        lo, hi = 0, len(b) - 1
        if t <= b[0]:
            return (t - b[0]) / (b[1] - b[0]) if len(b) > 1 else 0.0
        if t >= b[-1]:
            return hi + ((t - b[-1]) / (b[-1] - b[-2]) if len(b) > 1 else 0.0)
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if b[mid] <= t:
                lo = mid
            else:
                hi = mid
        return lo + (t - b[lo]) / (b[hi] - b[lo])


def _tolerance(unit: float) -> float:
    return max(JITTER, min(0.3 * unit, 0.015))


FLAM = 0.020                         # seconds within which onsets are one: a flam, a strum, a grace note


def tatum(onsets) -> float | None:
    """The grid's unit: the longest step (400 ms down to 18: Hyrule Field's
    32nds against its triplets share a 24th of a beat; finer, any onsets fit
    by chance) that three onset gaps in four are whole multiples of, within
    jitter. Onsets within FLAM of each other are one, at their middle:
    Corneria's flams, a part 8 to 16 ms off the rest, left no unit at all."""
    times, cluster = [], []
    for t in sorted(t for t, _ in onsets):
        if cluster and t - cluster[0] > FLAM:
            times.append(statistics.median(cluster))
            cluster = []
        cluster.append(t)
    if cluster:
        times.append(statistics.median(cluster))
    return _unit([b - a for a, b in zip(times, times[1:]) if 0.018 <= b - a <= 3.0])


def _unit(gaps: list) -> float | None:
    if len(gaps) < 6:
        return None
    for ms in range(400, 17, -1):
        u = ms / 1000
        tol = max(JITTER, 0.12 * u)
        fits = [(d, m) for d in gaps if 1 <= (m := round(d / u)) <= 24 and abs(d - m * u) <= tol]
        if len(fits) >= TATUM_FIT * len(gaps):
            return sum(d * m for d, m in fits) / sum(m * m for _, m in fits)
    return None


LATTICE = (2, 3, 4, 6, 8, 9, 12, 16, 18, 24, 32, 36, 48)   # a grid's steps in another's, by twos and threes


def ornaments(onsets) -> set:
    """Voices left out of the grid: a roll or tremolo, notes far faster than
    the song's and on no grid of its twos and threes (The Phantom Train's
    wheels, five to the eighth, put a 23 ms unit under the whole song). A
    voice's own unit is the one its own gaps share; the song's, the voices'
    median."""
    by = {}
    for t, w, v in onsets:
        if w > 0:
            by.setdefault(v, []).append(t)
    own = {}
    for v, ts in by.items():
        ts.sort()
        u = _unit([b - a for a, b in zip(ts, ts[1:]) if 0.018 <= b - a <= 3.0])
        if u:
            own[v] = u
    if len(own) < 3:
        return set()
    main = statistics.median(own.values())
    return {v for v, u in own.items()
            if u < 0.5 * main and not any(abs(main / u / n - 1) < 0.03 for n in LATTICE)}


LATE = 0.05                          # seconds a voice may play behind the others and be heard with them
MATCHED = 12                         # notes a voice must share with the others for its lag to be measured
HELD = 0.6                           # the share of those that must sit at its lag


def align(onsets) -> tuple[list, dict]:
    """Each voice's lag behind the others, and the onsets with it taken out.

    A driver may key a voice a tick or two after the rest, all song long (Wild
    West's two lowest voices, 18 and 20 ms: a band playing loose), which puts
    an onset between every two of the grid's and leaves no unit. The lag is
    measured against the voices already aligned (the busiest first): the
    median of each note's nearest neighbour there, if most of them sit at it.
    The window is under half the unit each voice's own gaps share, so a part
    a grid step after another is its rhythm, not a lag."""
    by = {}
    for t, w, v in onsets:
        if w > 0:
            by.setdefault(v, []).append(t)
    for ts in by.values():
        ts.sort()
    unit = _unit([b - a for ts in by.values() for a, b in zip(ts, ts[1:]) if 0.018 <= b - a <= 3.0])
    lags = {v: 0.0 for v in by}
    if unit is None or len(by) < 2:
        return [(t, w) for t, w, _ in onsets], lags
    window = min(LATE, 0.4 * unit)
    first = max(by, key=lambda v: len(by[v]))
    pool, todo = list(by[first]), [v for v in by if v != first]

    def nearest(ts):
        out = []
        for t in ts:
            i = bisect.bisect_left(pool, t - window)
            near = [t - o for o in pool[i:i + 16] if abs(t - o) <= window]
            if near:
                out.append(min(near, key=abs))
        return out

    while todo:
        found = {v: nearest(by[v]) for v in todo}
        v = max(todo, key=lambda u: len(found[u]))
        ds = found[v]
        if len(ds) < MATCHED:
            break                            # the rest share too little with the others: left as they are
        lag = statistics.median(ds)
        if abs(lag) >= 0.004 and sum(1 for d in ds if abs(d - lag) <= JITTER) >= HELD * len(ds):
            lags[v] = lag
        pool = sorted(pool + [t - lags[v] for t in by[v]])
        todo.remove(v)
    return [(t - lags.get(v, 0.0), w) for t, w, v in onsets], lags


def lock(onsets, unit: float) -> tuple[float, float]:
    """The unit and its phase fitted to the onsets' times: least squares over
    the onsets on the grid, in a window grown from the first eight seconds to
    the whole song, each pass placing onsets on the grid the last one found."""
    times = sorted(t for t, _ in onsets)
    t0, u = times[0], unit
    tol = _tolerance(unit)
    end = t0 + 8.0
    while True:
        pts = []
        for t in times:
            if t > end:
                break
            i = round((t - t0) / u)
            if abs(t - t0 - i * u) <= tol:
                pts.append((i, t))
        n = len(pts)
        si = sum(i for i, _ in pts)
        sii = sum(i * i for i, _ in pts)
        st = sum(t for _, t in pts)
        sit = sum(i * t for i, t in pts)
        den = n * sii - si * si
        if n >= 4 and den:
            u = (n * sit - si * st) / den
            t0 = (st - u * si) / n
        if end >= times[-1]:
            return u, t0
        end = min(times[-1], t0 + (end - t0) * 1.6)


MISSES = 3                           # onsets in a row off the grid that end a section
LOCK_WINDOW = 6.0                    # seconds a section's phase is first taken from
LONG = 6.0                           # seconds a section must last to have a unit of its own


def _residual(t: float, unit: float, phase: float) -> float:
    return (t - phase + unit / 2) % unit - unit / 2


def _follow(times: list, onsets, unit: float) -> list[Section]:
    """Sections on a grid of one unit: each one's phase taken from its first
    onsets (the grid through whichever holds most of its first seconds),
    followed until MISSES onsets in a row miss it."""
    tol = _tolerance(unit)
    out, i = [], 0
    while i < len(times):
        start = times[i]
        first = [t for t in times[i:] if t < start + LOCK_WINDOW]
        ph = max(first[:8], key=lambda p: sum(1 for t in first if abs(_residual(t, unit, p)) <= tol))
        j, misses, last = i, 0, i
        while j < len(times) and misses < MISSES:
            if abs(_residual(times[j], unit, ph)) <= tol:
                misses, last = 0, j
            else:
                misses += 1
            j += 1
        out.append(Section(start, times[last], unit, ph))
        i = last + 1
    return out


def _common_unit(secs: list, times: list) -> float:
    """One unit for every section, each keeping its own phase: least squares
    with a shared slope."""
    num = den = 0.0
    for x in secs:
        pts = [(round((t - x.phase) / x.unit), t) for t in times if x.start <= t <= x.end
               and abs(_residual(t, x.unit, x.phase)) <= _tolerance(x.unit)]
        if len(pts) < 2:
            continue
        mi = sum(i for i, _ in pts) / len(pts)
        mt = sum(t for _, t in pts) / len(pts)
        num += sum((i - mi) * (t - mt) for i, t in pts)
        den += sum((i - mi) ** 2 for i, _ in pts)
    return num / den if den else secs[0].unit


def sections(onsets, unit: float) -> list[Section]:
    """The song in sections, each on a grid of its own phase: found with one
    unit for the song, the unit fitted again over all of them (a section
    locked on its own first half-second came out 1 % off, and every section
    after it drifted), twice; a section of LONG seconds or more then gets its
    own unit, so a song may change tempo."""
    times = []
    for t in sorted(t for t, _ in onsets):
        if not times or t - times[-1] > 0.003:      # a chord's notes are one onset
            times.append(t)
    secs = _follow(times, onsets, unit)
    for _ in range(2):
        unit = _common_unit(secs, times)
        secs = _follow(times, onsets, unit)
    for x in secs:
        if x.end - x.start >= LONG:
            held = [(t, w) for t, w in onsets if x.start <= t <= x.end
                    and abs(_residual(t, x.unit, x.phase)) <= _tolerance(x.unit)]
            if len(held) >= 8:
                x.unit, x.phase = lock(held, x.unit)
    return secs


def _section_slots(onsets, x: Section) -> dict:
    tol = _tolerance(x.unit)
    out = {}
    for t, w in onsets:
        if x.start - tol <= t <= x.end + tol:
            i = round((t - x.phase) / x.unit)
            if abs(t - x.phase - i * x.unit) <= tol:
                out[i] = out.get(i, 0.0) + w
    return out


def _best_phase(slots: dict, k: int) -> tuple[int, float]:
    """The grid point a beat of k steps starts on, and how much more loudness
    its points hold than the grid's points on average."""
    lo, hi = min(slots), max(slots)
    mean = sum(slots.values()) / (hi - lo + 1)
    best = (lo, 0.0)
    for ph in range(k):
        on = [slots.get(i, 0.0) for i in range(lo + ph, hi + 1, k)]
        c = (sum(on) / len(on)) / mean if on and mean else 0.0
        if c > best[1]:
            best = (lo + ph, c)
    return best


def _fill(keep, k: int) -> float:
    """The share of a beat of k steps' points that have an onset, over the sections."""
    filled = total = 0.0
    for x, sl in keep:
        first, _ = _best_phase(sl, k)
        points = range(first, max(sl) + 1, k)
        filled += sum(1 for i in points if sl.get(i)) * (x.end - x.start)
        total += len(points) * (x.end - x.start)
    return filled / total if total else 0.0


def _repeats(keep, k: int, lag: int) -> float:
    """How alike the loudness on a pulse of k steps is `lag` pulses apart
    (its autocorrelation), over the sections."""
    num = den = 0.0
    for x, sl in keep:
        first, _ = _best_phase(sl, k)
        xs = [sl.get(i, 0.0) for i in range(first, max(sl) + 1, k)]
        if len(xs) < 2 * lag + 2:
            continue
        m = sum(xs) / len(xs)
        d = [v - m for v in xs]
        num += sum(d[i] * d[i + lag] for i in range(len(d) - lag))
        den += sum(v * v for v in d[:len(d) - lag])
    return num / den if den else 0.0


def _offbeats(keep, k: int, m: int) -> float:
    """The loudness on a pulse of k steps' points between those of a level m
    times coarser, over the loudness on them: low, the pulse groups by m."""
    on = off = n_on = n_off = 0.0
    for x, sl in keep:
        first, _ = _best_phase(sl, m * k)
        for i in range(first - ((first - min(sl)) // k) * k, max(sl) + 1, k):
            w = sl.get(i, 0.0)
            if (i - first) % (m * k) == 0:
                on, n_on = on + w, n_on + 1
            else:
                off, n_off = off + w, n_off + 1
    return (off / n_off) / (on / n_on) if n_on and n_off and on else 1.0


REPEATS = (2, 3, 4, 6, 8, 12, 16)    # pulses a bar's pattern may repeat after (longer: a phrase's, Johnny C. Bad's
                                     # three bars of 4/4 read as a three)
ALIKE = 0.9                          # a shorter repeat this nearly as strong as the strongest is the period
SURE = 0.3                           # a repeat weaker than this is no period (by twos then)


def _period(keep, pulse: int) -> int:
    """The pulses the song's pattern repeats after: the shortest repeat nearly
    as strong as any (every multiple of the period repeats too)."""
    reps = {lag: _repeats(keep, pulse, lag) for lag in REPEATS}
    best = max(reps.values())
    return min(lag for lag, r in reps.items() if r >= ALIKE * best) if best >= SURE else 4


def _levels(keep, pulse: int) -> list[int]:
    """The pulse and the levels it groups into, in steps: by twos, unless
    the pulse's pattern repeats after a three of them (Kids Run Through the
    City's, every six eighths: 0.75, against 0.18 every eight); then one
    three, first if the pulse's own off-beats group by threes (6/8, 12/8:
    The Phantom Train), else second (3/4). The repeats over a bar, not the
    off-beats alone, tell twos from threes: The Decisive Battle's bass,
    three sixteenths, three and two, groups its eighths by threes up close."""
    if _period(keep, pulse) % 3 == 0:
        steps = (3, 2, 2, 2) if _offbeats(keep, pulse, 3) < _offbeats(keep, pulse, 2) else (2, 3, 2, 2)
    else:
        steps = (2, 2, 2, 2)
    out = [pulse]
    for g in steps:
        out.append(out[-1] * g)
    return out


TYPICAL = 1.1                        # notes a beat the song's typical voice plays, as listeners tap it
PREFER, LEAN = 95.0, 1.0             # the tempo listeners lean toward, and how much (per octave away)
RESTED = 0.5                         # a beat finer than the pulse may rest on up to half its points


def _distance(rate: float, period: float) -> float:
    """How far a beat of `period` seconds is from the beat a listener taps:
    the typical voice (the median of the voices' notes a second) playing
    about TYPICAL notes in it, at a tempo near PREFER. Tuned by ear on 22
    songs of 9 games: Kefka's typical voice plays 1.3 notes a beat at 80
    (heard), 0.6 at 160; Aquatic Ambiance's 1.1 at 75 (heard), its
    arpeggio twice that; Battle Theme's 1.5 at 167 (heard), 2.9 at 83."""
    return abs(math.log2(rate * period / TYPICAL)) + LEAN * abs(math.log2(60 / period / PREFER))


def find(onsets) -> Grid | None:
    """The beat of onsets [(time, weight)] or [(time, weight, voice)] (each
    voice's lag then taken out first, its rolls left out); None when they keep
    to no beat (free time). On a grid first; where none holds, or only one so
    fine it holds anything (under FINEST), loosely (loose())."""
    lags, left, counts = {}, set(), {}
    if onsets and len(onsets[0]) == 3:
        left = ornaments(onsets)
        for t, w, v in onsets:
            if w > 0 and v not in left:
                counts[v] = counts.get(v, 0) + 1
        onsets, lags = align([o for o in onsets if o[2] not in left])
    onsets = [(t, w) for t, w in onsets if w > 0]
    if len(onsets) < 8:
        return None
    times = sorted(t for t, _ in onsets)
    span = (times[-1] - times[0]) or 1.0
    distinct = sum(1 for x, y in zip(times, times[1:]) if y - x > 0.010) + 1
    rate = statistics.median(counts.values()) / span if counts else distinct / span     # no voices: one
    grid = _gridded(onsets, rate)
    if grid is None or grid.unit < FINEST:
        grid = loose(onsets, rate) or grid
    if grid:
        grid.lags, grid.ornaments = {v: x for v, x in lags.items() if x}, left
    return grid


def _gridded(onsets, rate: float) -> Grid | None:
    """The beat on a grid of one unit (sections of it), the typical voice
    playing `rate` notes a second; None when the onsets keep to none."""
    unit = tatum(onsets)
    if unit is None:
        return None
    secs = [x for x in sections(onsets, unit) if x.end > x.start]
    slots = [_section_slots(onsets, x) for x in secs]
    keep = [(x, sl) for x, sl in zip(secs, slots) if sl]
    if not keep:
        return None
    total = sum(w for _, w in onsets)
    on_grid = sum(sum(sl.values()) for _, sl in keep) / total if total else 0.0
    mean_unit = sum(x.unit * (x.end - x.start) for x, _ in keep) / (sum(x.end - x.start for x, _ in keep) or 1.0)
    if on_grid < FREE:
        return None                          # free time: FFVI's opening organ, held and released at will
    fills = {k: _fill(keep, k) for k in MULTIPLES if 60 / 400 <= k * mean_unit <= 60 / SLOW}
    if not fills:
        return None
    # the pulse: the finest multiple of the grid's step that nearly every point of has an onset (FILLED,
    # or nearly the most any level has where rests fall on beats: Kefka's, 0.82)
    enough = min(FILLED, max(fills.values()) - 0.05)
    pulse = min(k for k, f in fills.items() if f >= enough)
    # the beat: of the pulse, the levels it groups into and the ones it divides into (a beat resting on some
    # of its points: The Empire Gestahl's, at 90, under a pulse at 45), the one nearest a listener's
    finer = [pulse // d for d in (2, 3) if pulse % d == 0 and _fill(keep, pulse // d) >= RESTED]
    levels = [k for k in _levels(keep, pulse) + finer if SLOW <= 60 / (k * mean_unit) <= FAST] or [pulse]
    k = min(levels, key=lambda k: _distance(rate, k * mean_unit))
    beat_times, bar_times = [], []
    for x, sl in keep:
        x.division = k
        first_slot, _ = _best_phase(sl, k)
        x.first = x.phase + first_slot * x.unit
        x.first -= math.floor((x.first - x.start + _tolerance(x.unit)) / x.period) * x.period
        x.meter, x.downbeat = _meter(sl, k, (x.first - x.phase) / x.unit)
        n = int((x.end - x.first) / x.period + 1e-9) + 1
        for m in range(n):
            t = x.first + m * x.period
            if beat_times and t <= beat_times[-1] + 0.5 * x.period:
                continue                     # the last section's last beat, or one too close to it
            beat_times.append(t)
            if (m - x.downbeat) % x.meter == 0:
                bar_times.append(t)
    return Grid(mean_unit, k, [x for x, _ in keep], beat_times, bar_times, on_grid,
                _swing(onsets, keep[0][0].period, keep[0][0].first))


# The loose beat, for a song no grid holds: a swing between straight and
# triplet (Swanky's Swing, 62:38), off-beats placed by hand note by note
# (Snakey Chantey), timing that drifts all song (Yoshi's Island's Athletic).
# Its onsets make an envelope of strength in time; the envelope's repeats
# give the beat's length (the finest strong one, and its multiples by twos,
# or threes where those repeat more, the one nearest a listener's beat as
# on a grid); the beats are then followed through the song by dynamic
# programming (Ellis's), each one where onsets are strong and its gap
# near the beat's length. The grid's beat is the surer, so it comes first;
# loosely alone, 22 of the 25 songs heard by ear with a steady beat read as
# heard, the three loose ones among them.

FRAME = 0.01                         # seconds a frame of the envelope
FINEST = 0.025                       # a grid's unit under this is doubted (Swanky's Swing fitted one of 19 ms, its swing
                                     # held at the wrong tempo): the loose beat is tried, and kept if it holds
TIGHT = 100.0                        # how hard the loose beat holds its length (Ellis's tightness)
REPEAT = 0.35                        # the envelope's repeat at the beat's length a loose beat needs
SPREAD = 0.06                        # the most its beats' gaps may vary (the spread of their logs)
COVERED = 0.7                        # the share of its beats with an onset within a tenth of a beat


def _envelope(onsets) -> list[float]:
    """Onset strength a frame: each onset's weight, spread by a gaussian of
    two frames, less the mean."""
    n = int(max(t for t, _ in onsets) / FRAME) + 8
    raw = [0.0] * n
    for t, w in onsets:
        raw[int(t / FRAME)] += w
    kernel = [math.exp(-0.5 * (i / 2) ** 2) for i in range(-6, 7)]
    env = [0.0] * n
    for i, x in enumerate(raw):
        if x:
            for j, k in enumerate(kernel):
                if 0 <= i + j - 6 < n:
                    env[i + j - 6] += x * k
    mean = sum(env) / n
    return [x - mean for x in env]


def _autocorrelation(env: list, lo: int, hi: int) -> dict:
    den = sum(x * x for x in env) or 1.0
    return {lag: sum(env[i] * env[i + lag] for i in range(len(env) - lag)) / den for lag in range(lo, hi + 1)}


def _peak_near(acf: dict, lag: float) -> tuple | None:
    """The repeat's strongest lag within 8 % of `lag` (frames), refined by a
    parabola through its neighbours: (seconds, strength)."""
    lo, hi = max(min(acf), int(lag * 0.92)), min(max(acf), int(lag * 1.08) + 1)
    if lo > hi:
        return None
    m = max(range(lo, hi + 1), key=lambda x: acf[x])
    d = 0.0
    if m - 1 in acf and m + 1 in acf:
        y0, y1, y2 = acf[m - 1], acf[m], acf[m + 1]
        if y0 - 2 * y1 + y2:
            d = max(-0.5, min(0.5, (y0 - y2) / (2 * (y0 - 2 * y1 + y2))))
    return (m + d) * FRAME, acf[m]


def _track(env: list, period: float) -> list[float]:
    """The beats through the envelope: each frame's score its strength plus
    the best earlier beat's score, less TIGHT times the squared log of the
    gap over the beat's length; traced back from the best of the last beat."""
    P = period / FRAME
    sd = statistics.pstdev(env) or 1.0
    o = [x / sd for x in env]
    lo, hi = max(1, int(round(P / 2))), int(round(2 * P))
    penalty = [0.0] * (hi + 1)
    for d in range(lo, hi + 1):
        penalty[d] = -TIGHT * math.log(d / P) ** 2
    score, back = [0.0] * len(o), [-1] * len(o)
    for t in range(len(o)):
        best, at = 0.0, -1
        for d in range(lo, min(hi, t) + 1):
            v = score[t - d] + penalty[d]
            if v > best:
                best, at = v, t - d
        score[t], back[t] = o[t] + best, at
    t = max(range(max(0, len(o) - int(P) - 1), len(o)), key=score.__getitem__)
    beats = []
    while t >= 0:
        beats.append(t * FRAME)
        t = back[t]
    return beats[::-1]


def loose(onsets, rate: float) -> Grid | None:
    """The beat of onsets no grid holds, followed loosely (see above); None
    when they do not repeat, or the beats followed are not steady (free)."""
    env = _envelope(onsets)
    acf = _autocorrelation(env, 15, int(60 / SLOW / FRAME) * 2)
    peaks = [(v, lag) for lag, v in acf.items() if acf.get(lag - 1, -9) < v >= acf.get(lag + 1, -9) and v >= REPEAT]
    if not peaks:
        return None
    top = max(v for v, _ in peaks)
    finest = min(lag for v, lag in peaks if v >= 0.6 * top)
    near = lambda m: _peak_near(acf, finest * m) or (finest * m * FRAME, -1.0)
    # by twos, unless the shortest repeat nearly as strong as any holds a three (as on a grid: Snakey
    # Chantey repeats alike every two and every three, 0.78 and 0.79, and is in twos)
    reps = {m: near(m)[1] for m in (2, 3, 4, 6, 8, 12)}
    best = max(reps.values())
    threes = best > 0 and min(m for m, v in reps.items() if v >= ALIKE * best) % 3 == 0
    lengths = [near(m) for m in ((1, 2, 3, 6) if threes else (1, 2, 4, 8))]
    lengths = [(sec, v) for sec, v in lengths if SLOW <= 60 / sec <= FAST and v >= REPEAT]
    if not lengths:
        return None
    period = min((sec for sec, _ in lengths), key=lambda sec: _distance(rate, sec))
    beats = _track(env, period)
    gaps = [b - a for a, b in zip(beats, beats[1:])]
    if len(gaps) < 8 or statistics.pstdev(math.log(g / period) for g in gaps) > SPREAD:
        return None
    times = sorted(t for t, _ in onsets)
    covered = sum(1 for b in beats if (i := bisect.bisect_left(times, b - 0.1 * period)) < len(times)
                  and times[i] <= b + 0.1 * period) / len(beats)
    if covered < COVERED:
        return None
    # the beat's length from a line through all its beats: a gap is a whole number of frames, their median
    # a tempo of 125.0 or 142.9
    n = len(beats)
    mean_i, mean_t = (n - 1) / 2, sum(beats) / n
    period = sum((i - mean_i) * (t - mean_t) for i, t in enumerate(beats)) / sum((i - mean_i) ** 2 for i in range(n))
    division = max(1, round(period / (finest * FRAME)))
    # the bar from the accents on the beats, as on a grid; swing from where the off-beats fall between them
    accents, offs = {}, []
    for t, w in onsets:
        i = bisect.bisect_right(beats, t) - 1
        if 0 <= i < len(beats) - 1:
            f = (t - beats[i]) / (beats[i + 1] - beats[i])
            if f < 0.1 or f > 0.9:
                j = i if f < 0.1 else i + 1
                accents[j] = accents.get(j, 0.0) + w
            elif 0.3 < f < 0.8:
                offs.append((f, w))
    # a bar of three only where the repeats hold a three (Mini Boss Confrontation's accents read three of
    # its half notes, where it repeats every two and four of its quarters, hardly every six)
    meter, downbeat = _meter(accents, 1, 0, (4, 3, 2) if threes else (4, 2)) if accents else (4, 0)
    section = Section(times[0], times[-1], period / division, beats[0], beats[0], meter, downbeat, division)
    swing = sum(f * w for f, w in offs) / sum(w for _, w in offs) if offs else 0.5
    return Grid(period / division, division, [section], beats, beats[downbeat::meter], covered, swing, loose=True)


BASS_LIFT = 1.4                      # how much more than chance the bass must land on a bar's first beat


def rebar(grid: Grid, bass_beats: list[float]) -> bool:
    """The bar again from where the bass lands: on the first of three beats
    in a waltz (oom-pah-pah), of two or four otherwise. Its notes falling on
    one beat of m more often than chance (1/m) by BASS_LIFT or more set the
    bar, and each section's downbeat where its own bass lands most (a
    section's beats restart where a held note moved the grid: Edgar and
    Sabin's second section starts half a bar into a bar of the first's); a
    bar the accents had read already stays as they read it. The Wedding
    Waltz's bass lands on the first of three 87 % of the time, its accents
    had read four. Returns whether the bar changed."""
    on = [round(b) for b in bass_beats if abs(b - round(b)) < 0.15 and b >= -0.15]
    if len(on) < 8:
        return False
    # each section's beats, as indices into beat_times
    spans, bt = [], grid.beat_times
    for x in grid.sections:
        tol = 0.5 * x.period
        i0 = bisect.bisect_left(bt, x.first - tol)
        i1 = bisect.bisect_right(bt, x.end + tol)
        if spans and i0 < spans[-1][1]:
            i0 = spans[-1][1]
        spans.append((i0, max(i0, i1)))
    def section_of(b):
        for k, (i0, i1) in enumerate(spans):
            if i0 <= b < i1:
                return k
        return None
    best = None
    for m in (4, 3, 2):
        counts = [[0] * m for _ in spans]
        for b in on:
            k = section_of(b)
            if k is not None:
                counts[k][(b - spans[k][0]) % m] += 1
        placed = sum(sum(c) for c in counts)
        if not placed:
            continue
        lift = sum(max(c) for c in counts) / placed * m
        if best is None or lift > best[0] * (1.0 if m != 2 else 1.1):
            best = (lift, m, [c.index(max(c)) if sum(c) else 0 for c in counts])
    if best is None:
        return False
    lift, m, downbeats = best
    if lift < BASS_LIFT or all(x.meter == m for x in grid.sections):
        return False
    bars = []
    for x, (i0, i1), d in zip(grid.sections, spans, downbeats):
        x.meter, x.downbeat = m, d
        bars += bt[i0 + d:i1:m]
    grid.bar_times = bars
    return True


REPHASE_LIFT = 1.3                   # how much more of the bass's landings a bar line must hold to move the bar


def rephase(grid: Grid, bass_notes: list[tuple[float, float]]) -> bool:
    """The bar's phase again from where the bass lands on a new pitch: a
    chord changes on the bar line far more often than mid-bar, where a
    root-and-fifth bass hits beats one and three alike and a backbeat
    snare is louder than beat one, which had both the accents and the
    bass's hits set the bar a half bar off. For each section, the beat of
    its meter the bass's pitch classes change on most takes the downbeat,
    where it holds REPHASE_LIFT times the changes the current one does;
    the bar stays otherwise. bass_notes: (beat, midi) of the bass voices'
    notes. Returns whether the bar moved."""
    if not grid.sections or not grid.bar_times:
        return False
    spans, bt = [], grid.beat_times
    for x in grid.sections:
        tol = 0.5 * x.period
        i0 = bisect.bisect_left(bt, x.first - tol)
        i1 = bisect.bisect_right(bt, x.end + tol)
        if spans and i0 < spans[-1][1]:
            i0 = spans[-1][1]
        spans.append((i0, max(i0, i1)))
    # the bass's pitch class on each beat: of the notes starting on it, the lowest
    on_beat = {}
    for b, midi in bass_notes:
        if abs(b - round(b)) < 0.2 and b >= -0.2:
            i = round(b)
            if i not in on_beat or midi < on_beat[i]:
                on_beat[i] = midi
    if len(on_beat) < 8:
        return False
    landings = []                            # beats where the bass's pitch class differs from its last
    last = None
    for i in sorted(on_beat):
        pc = round(on_beat[i]) % 12
        if last is not None and pc != last:
            landings.append(i)
        last = pc
    if len(landings) < 4:
        return False
    moved = False
    bars = []
    for x, (i0, i1) in zip(grid.sections, spans):
        m = x.meter
        counts = [0] * m
        for i in landings:
            if i0 <= i < i1:
                counts[(i - i0) % m] += 1
        d = x.downbeat % m
        if sum(counts) >= 4:
            best = max(range(m), key=lambda j: counts[j])
            if best != d and counts[best] >= REPHASE_LIFT * max(1, counts[d]):
                x.downbeat = best
                moved = True
        bars += bt[i0 + x.downbeat % m:i1:m]
    if moved:
        grid.bar_times = bars
    return moved


def _meter(slots: dict, k: int, first: float, choices=(4, 3, 2)) -> tuple[int, int]:
    """Beats a bar, 2, 3 or 4, and the downbeat's place among them: the count
    whose accents repeat most strongly, the place where they are loudest."""
    start = round(first)
    beats = {}
    for i, w in slots.items():
        if (i - start) % k == 0:
            beats[(i - start) // k] = beats.get((i - start) // k, 0.0) + w
    if not beats:
        return 4, 0
    n = max(beats) + 1
    acc = [beats.get(b, 0.0) for b in range(n)]
    best = (4, 0, -1.0)
    for m in choices:
        if n < 2 * m:
            continue
        sums = [sum(acc[j::m]) for j in range(m)]
        mean = sum(sums) / m
        contrast = max(sums) / mean if mean else 0.0
        # a bar of 4 holds a bar of 2's pattern too: a shorter bar must beat it clearly
        if contrast > best[2] * (1.0 if m == 4 else 1.08):
            best = (m, sums.index(max(sums)), contrast)
    return best[0], best[1]


def _swing(onsets, period: float, first: float) -> float:
    """Where the off-beat falls within the beat, by loudness (0.5: halfway,
    straight; 0.67: a triplet's long-short)."""
    offs = []
    for t, w in onsets:
        f = ((t - first) / period) % 1.0
        if 0.3 < f < 0.8:
            offs.append((f, w))
    if not offs:
        return 0.5
    return sum(f * w for f, w in offs) / sum(w for _, w in offs)
