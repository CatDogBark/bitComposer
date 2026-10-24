"""A song's form: its parts (A, B, A again...) and its loop, from where it repeats itself.

A driver replays a part note for note: the same voices, the same pitches,
the same gaps, a fixed time later, whether a pattern played again or the
whole song looping back. So repeats are found in time, not on the beat
(a grid's sections shift its beats by one here and there, a loop of 70
bars being 278 beats in one place, 279 in another). The times between
notes alike (one voice, one pitch, or one unpitched sample) are counted,
and each common lag is tried: a note repeats at a lag when its like
sounds that lag before, within a few milliseconds; a run of repeating
notes two bars long or more, a few odd notes inside allowed (a fill), is
a repeat.

The loop is the lag whose repeat runs to the song's end and lasts a lag
(the whole loop heard twice): the longest such run, the shorter lag on a
tie (a loop of A A is a loop of A). The parts are read over the first
pass, on the bars: each bar's source is the earliest bar it repeats; a
part starts where a repeat starts or stops, in the copy and in what it
copies; a part repeating an earlier one gets its letter, new material a
new letter. A part under two bars joins the one before it."""
import bisect
from collections import Counter, defaultdict
from dataclasses import dataclass, field

NEAR = 0.015                         # seconds a repeated note may sit off its lag (AKAO places each note up to
                                     # 5 ms off its time, so two copies of it 10 ms apart)
DRIFT = 0.0007                       # and a part in 1400 of the lag more: a driver's timer runs a hair off the
                                     # clock, so a 45 s loop's second pass sits 30 ms off the first by its end
                                     # (Super Ghouls'n Ghosts' Sardius, read as no loop at 15 ms)
BIN = 0.01                           # seconds the lags are counted in
EARLY = 0.02                         # seconds early a note may be and be its half bar's
LAGS = 24                            # the most common lags tried
HELD = 0.85                          # the share of a stretch's notes that must repeat
ODD = 1                              # unrepeated half-bar cells in a row a repeat may hold (a fill)
SHORTEST = 2                         # bars a repeat must last
PART = 4                             # bars a part must last (shorter, it joins the one before; a riff
                                     # repeating every two bars is inside a part, not parts)
LOOP = 4                             # bars a loop must last
HEARD = 0.5                          # the share of a loop that must be heard again
SHIFT = 3                            # bars the lag may move by within a loop's second time through (an ending
                                     # longer or shorter the second time)
SHORT = 4                            # bars before the end a loop heard mostly (MOST of it) may stop
MOST = 0.75


@dataclass
class Part:
    label: str                       # A, B, ...; a part repeating an earlier one has its letter
    bar: int                         # its first bar, from 0
    bars: int
    start: float                     # seconds
    of: int | None = None            # the earlier part it repeats (index)


@dataclass
class Form:
    parts: list = field(default_factory=list)
    loop_bar: int | None = None      # the bar the loop goes back to (from 0); None: no loop heard
    loop_bars: int | None = None     # the loop's length in bars
    loop_seconds: float | None = None
    evidence: dict = field(default_factory=dict)

    @property
    def letters(self) -> str:
        return " ".join(p.label for p in self.parts)

    @property
    def sections(self) -> list:
        """The parts at a larger scale: a short phrase (PART bars or less)
        played again at once is one section with its repeat (Into the Thick
        of It's D D, its E E). Sections marked by ear keep a repeated longer
        part two (Terra's B B C twice) and a short intro its own."""
        out = []
        for p in self.parts:
            if out and out[-1].label == p.label and p.bars <= PART:
                out[-1] = Part(out[-1].label, out[-1].bar, out[-1].bars + p.bars, out[-1].start, out[-1].of)
            else:
                out.append(Part(p.label, p.bar, p.bars, p.start, p.of))
        return out


def _notes(song) -> list[tuple[float, tuple]]:
    out = []
    for p in song.notes:
        if p.level > 0:
            what = round(p.midi) if p.midi is not None else ("x", p.sample.key if p.sample else "noise")
            out.append((p.start, (p.voice, what)))
    out.sort(key=lambda x: x[0])
    return out


def _lags(notes, shortest: float, near: tuple = (), loop: float = 0.0) -> list[float]:
    """The commonest times between notes alike, `shortest` seconds and more;
    and around each lag of `loop` seconds or more, the commonest within each
    of the `near` offsets (a part a bar longer the second time through moves
    the rest of the pass a bar: a lag too rare to be among the commonest)."""
    by = defaultdict(list)
    for t, k in notes:
        by[k].append(t)
    counts = Counter()
    for ts in by.values():
        for i, t in enumerate(ts):
            for u in ts[:i]:
                if t - u >= shortest:
                    counts[round((t - u) / BIN)] += 1
    # neighbouring bins are one lag (a lag between two bins splits its count)
    merged = Counter()
    for b, c in counts.items():
        merged[b] += c
        merged[b - 1] += c / 2
        merged[b + 1] += c / 2
    out = []
    for b, _ in merged.most_common():
        if all(abs(b - o) > 2 for o in out):
            out.append(b)
        if len(out) >= LAGS:
            break
    for b in [o for o in out if o * BIN >= loop > 0]:
        for d in near:
            centre = round((b * BIN + d) / BIN)
            span = max(3, round(abs(d) * 0.1 / BIN))
            best = max(range(centre - span, centre + span + 1), key=lambda x: merged.get(x, 0))
            if merged.get(best, 0) and all(abs(best - o) > 2 for o in out):
                out.append(best)
    return [b * BIN for b in out]


def _repeats(notes, by, lag: float, cells_of, shortest: int) -> list[tuple[int, int]]:
    """The stretches (first half bar, past the last) that repeat at `lag`:
    a half bar of the grid repeats where its voices' notes have their like
    sounding `lag` before, within NEAR, HELD of them on a voice's average
    (each voice its own share: a drum on every beat repeats at any lag, and
    would carry an intro's bar to a part's); a repeat is a run of such half
    bars (an empty one inside, a rest, and ODD unlike ones in a row, a
    fill, allowed), at least `shortest` half bars. Half bars of the grid, not
    of a mean bar: a song whose tempo drifts (Edgar and Sabin's) moves its
    repeats half a bar off a fixed cell by its ninth bar."""
    cells = {}
    near = NEAR + DRIFT * lag
    for (t, k), c in zip(notes, cells_of):
        ts = by[k]
        i = bisect.bisect_left(ts, t - lag - near)
        v = cells.setdefault(c, {}).setdefault(k[0], [0, 0])
        v[0] += i < len(ts) and ts[i] <= t - lag + near
        v[1] += 1
    out, start, end, odd = [], None, None, 0
    for c in range(max(cells) + 1):
        voices = cells.get(c)
        if not voices:
            continue                                 # a rest: neither repeats nor breaks a repeat
        if sum(h / n for h, n in voices.values()) >= HELD * len(voices):
            if start is None:
                start = c
            end, odd = c, 0
        elif start is not None:
            odd += 1
            if odd > ODD:
                if end - start + 1 >= shortest:
                    out.append((start, end + 1))
                start, odd = None, 0
    if start is not None and end - start + 1 >= shortest:
        out.append((start, end + 1))
    joined = []                                      # repeats a bar or less apart are one (a loop with two odd cells)
    for a, b in out:
        if joined and a - joined[-1][1] <= 2:
            joined[-1] = (joined[-1][0], b)
        else:
            joined.append((a, b))
    return joined


def read(song, grid) -> Form:
    """The song's form, its parts on the bars of its beat (a grid from beat.find)."""
    if not grid or len(grid.bar_times) < 4:
        return Form()
    bars = list(grid.bar_times)
    bar_len = (bars[-1] - bars[0]) / (len(bars) - 1)
    shortest = SHORTEST * bar_len * 0.95
    notes = _notes(song)
    if len(notes) < 16:
        return Form()
    by = defaultdict(list)
    for t, k in notes:
        by[k].append(t)
    end = notes[-1][0]
    edges = bars + [bars[-1] + bar_len * k for k in range(1, int((end - bars[-1]) / bar_len) + 3)]
    def half_bar(t):                                 # the half bar of the grid a time falls in (a note a hair
        t += EARLY                                   # early is its next one's: AKAO's 5 ms)
        i = max(0, min(len(edges) - 2, bisect.bisect_right(edges, t) - 1))
        return 2 * i + (t >= (edges[i] + edges[i + 1]) / 2)
    at = lambda c: edges[c // 2] + (c % 2) * (edges[c // 2 + 1] - edges[c // 2]) / 2 if c // 2 + 1 < len(edges) else edges[-1]
    cells_of = [half_bar(t) for t, _ in notes]
    near = [k * bar_len for k in range(-SHIFT, SHIFT + 1) if k]
    repeats = {lag: [(at(a), at(b)) for a, b in _repeats(notes, by, lag, cells_of, 2 * SHORTEST)]
               for lag in _lags(notes, shortest, near, LOOP * bar_len * 0.95)}
    form = Form()
    # the loop: the second time through, repeats in a chain (the next starting within a bar of the last's end, at
    # a lag a few bars off: Kefka's C a bar longer the second time, everything after it a bar later) reaching the
    # end (the last bar may be fading out; four bars short, if it holds most of the loop: Athletic's recording
    # ends before its last bars come round), lasting half its first lag or more; the longest chain. The chain's
    # lag is the one its runs cover the most time at, not its first run's: a short run at a lag two bars under
    # the loop's would chain onto the loop's own run and, on the tie, win as the shorter lag (Snowman's Town,
    # Lostside Marshes and 42 more read two bars short).
    runs = sorted((a, b, lag) for lag, rs in repeats.items() if lag >= LOOP * bar_len * 0.95
                  for a, b in rs if b - a >= PART * bar_len * 0.95)
    loop = None
    for k, (a0, b0, lag0) in enumerate(runs):
        b_end = b0
        covered = {lag0: b0 - a0}
        for a, b, lag in runs[k + 1:]:
            if a > b_end + 2 * bar_len:              # the bar or two of the other ending repeats at neither lag
                break
            if b > b_end and abs(lag - lag0) <= SHIFT * bar_len:
                covered[lag] = covered.get(lag, 0.0) + (b - max(a, b_end))
                b_end = b
        lag0 = max(covered, key=covered.get)
        held = b_end - a0
        reaches = b_end >= end - 1.5 * bar_len or (b_end >= end - SHORT * bar_len
                                                   and held >= max(MOST * lag0, 4 * SHORT * bar_len))
        if reaches and held >= HEARD * lag0:
            if loop is None or held > loop[2] - loop[1] + 0.5 * bar_len or (abs(held - (loop[2] - loop[1])) <= 0.5 * bar_len and lag0 < loop[0]):
                loop = (lag0, a0, b_end)
    horizon = end + bar_len
    if loop:
        lag, a, b = loop
        form.loop_seconds = lag
        form.loop_bar = _bar_at(bars, a - lag, 0.5)     # a repeat a half bar early: a bar line's chance match
        form.loop_bars = max(1, round(lag / bar_len))
        form.evidence["loop"] = {"seconds": round(lag, 3), "repeated_from": round(a, 2), "to": round(b, 2)}
        horizon = a                                  # the parts are read over the first pass
    last_bar = min(len(bars), _bar_at(bars, horizon) + (0 if loop else 1))
    # the repeats as blocks of bars, (first, past the last, each bar's source): the longest lags first,
    # a shorter one only over bars no longer one holds (a riff repeating every two bars inside a part
    # repeated every four is the part's)
    whole = len(bars)                                # repeats are read over the whole song: a part's edges in the
    blocks, held = [], [False] * whole               # first pass may show only where a later pass repeats it
    for lag in sorted(repeats, reverse=True):
        if lag < PART * bar_len * 0.95:
            continue                                 # a riff: what repeats a bar or two on is inside a part
        for a, b in repeats[lag]:
            # a bar is the repeat's when its first half is (its last half may lead somewhere else: Terra's
            # phrases each end on a pickup into what follows)
            inside = [i for i in range(whole) if a - 1e-6 <= bars[i] and (bars[i] + edges[i + 1]) / 2 <= b + 1e-6]
            run = []
            for i in inside + [None]:
                if i is not None and not held[i] and (not run or i == run[-1] + 1):
                    run.append(i)
                    continue
                if len(run) >= PART:
                    # each bar's source by time: a source bar held long (Edgar and Sabin's seventh, a
                    # fermata) is two bars' worth of its copy
                    srcs = [_bar_at(bars, (bars[k] + edges[k + 1]) / 2 - lag) for k in run]
                    if srcs[0] < run[0]:
                        blocks.append((run[0], run[-1] + 1, srcs, lag))
                        for k in run:
                            held[k] = True
                run = [i] if i is not None and not held[i] else []
    # cuts where a block starts or stops, in it and in its source, and where new material changes
    # (novelty); a copy takes its source's cuts too (Terra's bars 21 to 36 copy 5 to 20 whole: B B C)
    novel = _novel(song, bars, bar_len, last_bar)
    cuts = {0} | novel
    # a later pass says one thing about the first's parts: where its copy of the first breaks off and picks up
    # again (Kefka's second C a bar longer: its D picks up a bar later), a part starts; the loop's own repeat
    # (the copy from where it starts over) says where the loop is, not where its parts are
    again = _bar_at(bars, loop[1]) if loop else None
    later = [(i, srcs[0]) for i, j, srcs, lag in blocks
             if loop and i >= last_bar and i != again and abs(lag - loop[0]) <= SHIFT * bar_len]
    blocks = [(i, j, srcs) for i, j, srcs, lag in blocks if i < last_bar]
    for i, j, srcs in blocks:
        cuts.update((i, j, srcs[0], srcs[-1] + 1))
    for i, src in later:
        cuts.add(src)
    for _ in range(4):                               # a cut copied into a copy may be copied again
        more = {i + n for i, j, srcs in blocks for c in cuts for n in range(1, j - i)
                if srcs[n] == c and srcs[n - 1] != c}
        if more <= cuts:
            break
        cuts |= more
    cuts = {c for c in cuts if c < last_bar}
    # a cut a repeat (or the loop) makes stands, a part beside it however short (an intro of two bars
    # before a part played again); one only the novelty makes needs PART bars from the last
    sure = (cuts - novel) | {0} | ({form.loop_bar} if loop else set())
    starts = []
    for c in sorted(c for c in cuts | sure if c < last_bar):
        gap = c - starts[-1] if starts else PART
        if gap < PART:
            if c not in sure:
                continue
            if starts[-1] not in sure:
                starts[-1] = c                       # a sure cut wins over a novelty beside it
                continue
            if gap < SHORTEST and not (loop and c == form.loop_bar):
                continue                             # sure cuts a bar apart: the repeats' edges differ by one
        starts.append(c)
    if len(starts) > 1 and last_bar - starts[-1] < SHORTEST:
        starts.pop()
    # letters: a part a block copies from an earlier part's start gets its letter
    letters = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    for k, b in enumerate(starts):
        nb = (starts[k + 1] if k + 1 < len(starts) else last_bar) - b
        of = None
        for i, j, srcs in blocks:
            if i <= b < j:
                s0 = srcs[b - i]
                of = next((m for m, p in enumerate(form.parts) if p.bar == s0), None)
                if of is not None:
                    break
        label = form.parts[of].label if of is not None else next(letters, "?")
        form.parts.append(Part(label, b, nb, bars[b], of))
    return form


NOVEL = 0.25                         # how much more alike bars are on each side of a change than across it
WIDE = 4                             # bars looked at on each side of a change


INSTRUMENTS = 0.4                    # how much more alike the instruments are on each side of a change than across it


def _novel(song, bars: list, bar_len: float, last_bar: int) -> set:
    """Where new material changes, in its notes or in its instruments (_changes)."""
    return _changes(song, bars, bar_len, last_bar) | _instrumented(song, bars, last_bar)


def _instrumented(song, bars: list, last_bar: int) -> set:
    """Where the instruments change: the samples sounding in each bar (which,
    not how often), alike on each side and unlike across, a peak INSTRUMENTS
    or more (Foote's novelty, WIDE bars a side). Checked against sections
    marked by ear: found 76 % of them, from 68."""
    used = [set() for _ in range(last_bar)]
    for p in song.notes:
        if p.level > 0:
            i = bisect.bisect_right(bars, p.start + 0.02) - 1
            if 0 <= i < last_bar:
                used[i].add(p.sample.key if p.sample else "noise")
    like = lambda i, j: len(used[i] & used[j]) / len(used[i] | used[j]) if used[i] | used[j] else 1.0
    return _peaks(like, last_bar, INSTRUMENTS)


def _peaks(like, last_bar: int, level: float) -> set:
    def mean(xs):
        xs = list(xs)
        return sum(xs) / len(xs) if xs else 0.0
    score = {}
    for c in range(WIDE, last_bar - WIDE + 1):
        before, after = range(c - WIDE, c), range(c, c + WIDE)
        within = (mean(like(i, j) for i in before for j in before if i < j)
                  + mean(like(i, j) for i in after for j in after if i < j)) / 2
        score[c] = within - mean(like(i, j) for i in before for j in after)
    return {c for c, v in score.items() if v >= level and all(v >= score.get(d, -1) for d in range(c - 2, c + 3))}


def _changes(song, bars: list, bar_len: float, last_bar: int) -> set:
    """Where new material changes: bars on each side alike among themselves
    and unlike across (Foote's novelty, WIDE bars a side), a peak NOVEL or
    more. Two new parts always played one after the other repeat as one, so
    only this tells them apart."""
    tokens = [defaultdict(Counter) for _ in range(last_bar)]
    for p in song.notes:
        if p.level <= 0:
            continue
        i = bisect.bisect_right(bars, p.start + 0.02) - 1
        if 0 <= i < last_bar:
            pos = round((p.start - bars[i]) / bar_len * 48)
            what = round(p.midi) if p.midi is not None else ("x", p.sample.key if p.sample else "noise")
            tokens[i][p.voice][(pos, what)] += 1

    def like(i, j):
        voices = set(tokens[i]) | set(tokens[j])
        if not voices:
            return 1.0
        total = 0.0
        for v in voices:
            a, b = tokens[i].get(v, Counter()), tokens[j].get(v, Counter())
            na, nb = sum(a.values()), sum(b.values())
            total += 2 * sum((a & b).values()) / (na + nb) if na + nb else 1.0
        return total / len(voices)

    return _peaks(like, last_bar, NOVEL)


def _bar_at(bars: list, t: float, near: float = 0.1) -> int:
    """The bar a time falls in (a bar line within `near` of a bar after it counts as its start)."""
    i = bisect.bisect_right(bars, t) - 1
    if i + 1 < len(bars) and bars[i + 1] - t <= near * (bars[i + 1] - bars[max(i, 0)]):
        i += 1
    return max(0, i)
