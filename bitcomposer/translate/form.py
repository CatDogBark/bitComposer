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
BIN = 0.01                           # seconds the lags are counted in
LAGS = 24                            # the most common lags tried
HELD = 0.85                          # the share of a stretch's notes that must repeat
ODD = 1                              # unrepeated half-bar cells in a row a repeat may hold (a fill)
SHORTEST = 2                         # bars a repeat must last
PART = 4                             # bars a part must last (shorter, it joins the one before; a riff
                                     # repeating every two bars is inside a part, not parts)
LOOP = 4                             # bars a loop must last
HEARD = 0.5                          # the share of a loop that must be heard again


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


def _notes(song) -> list[tuple[float, tuple]]:
    out = []
    for p in song.notes:
        if p.level > 0:
            what = round(p.midi) if p.midi is not None else ("x", p.sample.key if p.sample else "noise")
            out.append((p.start, (p.voice, what)))
    out.sort(key=lambda x: x[0])
    return out


def _lags(notes, shortest: float) -> list[float]:
    """The commonest times between notes alike, `shortest` seconds and more."""
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
    return [b * BIN for b in out]


def _repeats(notes, by, lag: float, cell: float, shortest: float) -> list[tuple[float, float]]:
    """The stretches (start, end) that repeat at `lag`: cut into cells of
    `cell` seconds (half a bar), a cell repeats where its voices' notes have
    their like sounding `lag` before, within NEAR, HELD of them on a voice's
    average (each voice its own share: a drum on every beat repeats at any
    lag, and would carry an intro's bar to a part's); a repeat is a run of such
    cells (an empty one inside, a rest, and ODD unlike ones in a row, a fill,
    allowed), at least `shortest` long. Cells, not a run of notes: a part
    that repeats at any lag (a drum on every beat) would carry a run of
    notes from one repeat to the next."""
    t0 = notes[0][0]
    cells = {}
    for t, k in notes:
        ts = by[k]
        i = bisect.bisect_left(ts, t - lag - NEAR)
        c = cells.setdefault(int((t - t0) / cell), {}).setdefault(k[0], [0, 0])
        c[0] += i < len(ts) and ts[i] <= t - lag + NEAR
        c[1] += 1
    out, start, end, odd = [], None, None, 0
    for c in range(max(cells) + 1):
        voices = cells.get(c)
        if not voices:
            continue                                 # a rest: neither repeats nor breaks a repeat
        # each voice's share alike: a drum repeating at any lag is one voice, not most of the notes
        if sum(h / n for h, n in voices.values()) >= HELD * len(voices):
            if start is None:
                start = c
            end, odd = c, 0
        elif start is not None:
            odd += 1
            if odd > ODD:
                if (end - start + 1) * cell >= shortest:
                    out.append((t0 + start * cell, t0 + (end + 1) * cell))
                start, odd = None, 0
    if start is not None and (end - start + 1) * cell >= shortest:
        out.append((t0 + start * cell, t0 + (end + 1) * cell))
    joined = []                                      # repeats a bar or less apart are one (a loop with two odd cells)
    for a, b in out:
        if joined and a - joined[-1][1] <= 2.5 * cell:
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
    repeats = {lag: _repeats(notes, by, lag, bar_len / 2, shortest) for lag in _lags(notes, shortest)}
    form = Form()
    # the loop: the lag whose repeat reaches the end (the last bar may be fading out) and lasts a lag
    loop = None
    for lag, rs in repeats.items():
        for a, b in rs:
            if b >= end - 1.5 * bar_len and b - a >= HEARD * lag and lag >= LOOP * bar_len * 0.95:
                if loop is None or b - a > loop[2] - loop[1] + 0.5 * bar_len or (abs((b - a) - (loop[2] - loop[1])) <= 0.5 * bar_len and lag < loop[0]):
                    loop = (lag, a, b)
    horizon = end + bar_len
    if loop:
        lag, a, b = loop
        form.loop_seconds = lag
        form.loop_bar = _bar_at(bars, a - lag, 0.5)     # a repeat a half bar early: a bar line's chance match
        form.loop_bars = max(1, round(lag / bar_len))
        form.evidence["loop"] = {"seconds": round(lag, 3), "repeated_from": round(a, 2), "to": round(b, 2)}
        horizon = a                                  # the parts are read over the first pass
    last_bar = min(len(bars), _bar_at(bars, horizon) + (0 if loop else 1))
    # the repeats as blocks of bars, (first, past the last, the first's source): the longest lags first,
    # a shorter one only over bars no longer one holds (a riff repeating every two bars inside a part
    # repeated every four is the part's)
    blocks, held = [], [False] * last_bar
    for lag in sorted(repeats, reverse=True):
        for a, b in repeats[lag]:
            inside = [i for i in range(last_bar) if a <= bars[i] + bar_len / 2 <= b]
            run = []
            for i in inside + [None]:
                if i is not None and not held[i] and (not run or i == run[-1] + 1):
                    run.append(i)
                    continue
                if len(run) >= PART:
                    src = _bar_at(bars, bars[run[0]] + bar_len / 2 - lag)
                    if src < run[0]:
                        blocks.append((run[0], run[-1] + 1, src))
                        for k in run:
                            held[k] = True
                run = [i] if i is not None and not held[i] else []
    # cuts where a block starts or stops, in it and in its source, and where new material changes
    # (novelty); a copy takes its source's cuts too (Terra's bars 21 to 36 copy 5 to 20 whole: B B C)
    novel = _novel(song, bars, bar_len, last_bar)
    cuts = {0} | novel
    for i, j, src in blocks:
        cuts.update((i, j, src, src + (j - i)))
    for _ in range(4):                               # a cut copied into a copy may be copied again
        more = {i + (c - src) for i, j, src in blocks for c in cuts if src < c < src + (j - i)}
        if more <= cuts:
            break
        cuts |= more
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
        for i, j, src in blocks:
            if i <= b < j:
                s0 = src + (b - i)
                of = next((m for m, p in enumerate(form.parts) if p.bar == s0), None)
                if of is not None:
                    break
        label = form.parts[of].label if of is not None else next(letters, "?")
        form.parts.append(Part(label, b, nb, bars[b], of))
    return form


NOVEL = 0.25                         # how much more alike bars are on each side of a change than across it
WIDE = 4                             # bars looked at on each side of a change


def _novel(song, bars: list, bar_len: float, last_bar: int) -> set:
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

    def mean(xs):
        xs = list(xs)
        return sum(xs) / len(xs) if xs else 0.0

    score = {}
    for c in range(WIDE, last_bar - WIDE + 1):
        before, after = range(c - WIDE, c), range(c, c + WIDE)
        within = (mean(like(i, j) for i in before for j in before if i < j)
                  + mean(like(i, j) for i in after for j in after if i < j)) / 2
        score[c] = within - mean(like(i, j) for i in before for j in after)
    return {c for c, v in score.items()
            if v >= NOVEL and all(v >= score.get(d, -1) for d in range(c - 2, c + 3))}


def _bar_at(bars: list, t: float, near: float = 0.1) -> int:
    """The bar a time falls in (a bar line within `near` of a bar after it counts as its start)."""
    i = bisect.bisect_right(bars, t) - 1
    if i + 1 < len(bars) and bars[i + 1] - t <= near * (bars[i + 1] - bars[max(i, 0)]):
        i += 1
    return max(0, i)
