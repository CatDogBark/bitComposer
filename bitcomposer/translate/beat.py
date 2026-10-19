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
The beat is the level of those a listener taps: the one holding about as
many notes as a tapped beat does, at a tempo near the one listeners lean
toward. Each choice was tuned by ear: eleven FFVI songs tapped (Kefka at
80, not 160; Kids Run Through the City in threes at 110, not 73 in fours;
The Phantom Train's 12/8 at 54). The bar: the beat count whose accents
repeat most strongly, its downbeat where they are loudest. Swing: where
the off-beat falls.

Before any of it, each voice's lag behind the others is taken out (a
driver keying a part a tick late, all song long), and a roll on no grid of
the song's (notes five to the eighth) is left out.

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
MULTIPLES = (1, 2, 3, 4, 6, 8, 12, 16, 24)   # units a beat may be


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


def tatum(onsets) -> float | None:
    """The grid's unit: the longest step (400 ms down to 20) that three onset
    gaps in four are whole multiples of, within jitter."""
    times = sorted({round(t, 3) for t, _ in onsets})
    return _unit([b - a for a, b in zip(times, times[1:]) if 0.018 <= b - a <= 3.0])


def _unit(gaps: list) -> float | None:
    if len(gaps) < 6:
        return None
    for ms in range(400, 19, -1):
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


REPEATS = (2, 3, 4, 6, 8, 12, 16, 24)   # pulses a bar's pattern may repeat after
ALIKE = 0.9                          # a shorter repeat this nearly as strong as the strongest is the period
SURE = 0.3                           # a repeat weaker than this is no period (by twos then)


def _period(keep, pulse: int) -> int:
    """The pulses the song's pattern repeats after: the shortest repeat nearly
    as strong as any (every multiple of the period repeats too)."""
    reps = {lag: _repeats(keep, pulse, lag) for lag in REPEATS}
    best = max(reps.values())
    return min(lag for lag, r in reps.items() if r >= ALIKE * best) if best >= SURE else 4


def _levels(keep, pulse: int) -> list[tuple[int, int]]:
    """The pulse and the levels it groups into, each with the grouping that
    made it (steps, 1/2/3): by twos, unless the pulse's pattern repeats
    after a three of them (Kids Run Through the City's, every twelve
    eighths: 0.76, against 0.18 every eight); then one three, first if the
    pulse's own off-beats group by threes (6/8, 12/8: The Phantom Train),
    else second (3/4). The repeats over a bar, not the off-beats alone, tell
    twos from threes: The Decisive Battle's bass, three sixteenths, three
    and two, groups its eighths by threes up close."""
    if _period(keep, pulse) % 3 == 0:
        steps = (3, 2, 2, 2) if _offbeats(keep, pulse, 3) < _offbeats(keep, pulse, 2) else (2, 3, 2, 2)
    else:
        steps = (2, 2, 2, 2)
    out = [(pulse, 1)]
    for g in steps:
        out.append((out[-1][0] * g, g))
    return out


DENSE, BUSY = 3.5, 2.0               # onsets, and the busiest voice's notes, a beat as a listener taps it
PREFER, LEAN = 110.0, 1.0            # the tempo listeners lean toward, and how much (per octave away)


def _crowding(rates: tuple, period: float, group: int) -> float:
    """How far a beat of `period` seconds is from the beat a listener taps:
    about three and a half onsets and two of the busiest voice's notes (half
    as many again in a beat of three), at a tempo near PREFER. Kefka's
    quarter at 160 holds 1.9 onsets, its half note 3.9: heard at 80.
    Terra's, at 160, 3.9. The lean keeps a sparse song off a beat of 45
    (Umaro, Gogo: an octave too slow without it)."""
    dense, busy = (DENSE * 1.5, BUSY * 1.5) if group == 3 else (DENSE, BUSY)
    return (abs(math.log2(rates[0] * period / dense)) + abs(math.log2(rates[1] * period / busy))
            + LEAN * abs(math.log2(60 / period / PREFER)))


def find(onsets) -> Grid | None:
    """The beat of onsets [(time, weight)] or [(time, weight, voice)] (each
    voice's lag then taken out first, its rolls left out); None when they keep
    to no grid, or too few of them to one (free time)."""
    lags, left, busiest = {}, set(), None
    if onsets and len(onsets[0]) == 3:
        left = ornaments(onsets)
        counts = {}
        for t, w, v in onsets:
            if w > 0 and v not in left:
                counts[v] = counts.get(v, 0) + 1
        busiest = max(counts.values(), default=0)
        onsets, lags = align([o for o in onsets if o[2] not in left])
    onsets = [(t, w) for t, w in onsets if w > 0]
    unit = tatum(onsets) if len(onsets) >= 8 else None
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
    # the beat: of the pulse and the levels it groups into, the one with as many notes a beat as a listener's
    times = sorted(t for t, _ in onsets)
    span = (times[-1] - times[0]) or 1.0
    distinct = sum(1 for a, b in zip(times, times[1:]) if b - a > 0.010) + 1
    rates = (distinct / span, (busiest or distinct) / span)
    levels = [(k, g) for k, g in _levels(keep, pulse) if SLOW <= 60 / (k * mean_unit) <= FAST] or [(pulse, 1)]
    k = min(levels, key=lambda kg: _crowding(rates, kg[0] * mean_unit, kg[1]))[0]
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
                _swing(onsets, keep[0][0].period, keep[0][0].first), {v: x for v, x in lags.items() if x}, left)


BASS_LIFT = 1.4                      # how much more than chance the bass must land on a bar's first beat


def rebar(grid: Grid, bass_beats: list[float]) -> bool:
    """The bar again from where the bass lands: on the first of three beats
    in a waltz (oom-pah-pah), of two or four otherwise. Its notes falling on
    one beat of m more often than chance (1/m) by BASS_LIFT or more set the
    bar and its downbeat; else the accents' bar stays. The Wedding Waltz's
    bass lands on the first of three 87 % of the time, its accents had read
    four. Returns whether the bar changed."""
    on = [round(b) for b in bass_beats if abs(b - round(b)) < 0.15 and b >= -0.15]
    if len(on) < 8:
        return False
    best = None
    for m in (4, 3, 2):
        counts = [sum(1 for b in on if b % m == d) for d in range(m)]
        lift = max(counts) / len(on) * m
        if best is None or lift > best[0] * (1.0 if m != 2 else 1.1):
            best = (lift, m, counts.index(max(counts)))
    lift, m, d = best
    if lift < BASS_LIFT:
        return False
    for x in grid.sections:
        x.meter = m
    grid.bar_times = grid.beat_times[d::m]
    return True


def _meter(slots: dict, k: int, first: float) -> tuple[int, int]:
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
    for m in (4, 3, 2):
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
