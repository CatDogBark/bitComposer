"""The bar's phase: which beat is the one, from where the song repeats itself.

The accents (beat.find's rule) and the bass's landings (beat.rebar) put
the bar line where the composer's loop jumps back to in 64 % of songs,
75 % counting loops that start on a pickup, measured on the held-out half
of the independent decode's comparison (docs/idiom/phase-1-readers.md):
a backbeat snare is louder than beat one, and a root-and-fifth bass lands
on one and three alike. Where the music starts repeating itself is a
surer sign. The loop's second pass begins on the loop's first beat; a
riff or a part repeats from a phrase's first beat; a note held a whole
bar starts on the one. SIGNS gives each sign's share of its occurrences
that fall on the downbeat, measured on the development half (185 songs in
4/4, the composers' jumps as the truth, 2026-10-21); the beat of the bar
holding the most of them, each sign weighted, is the one. The same rule
on the held-out half: 74 % (84 % with a pickup). A two-level table (the
downbeat's share, the rest spread evenly) scored the same as the full
one there, and serves any meter.

A candidate phase scores, summed over the signs, weight x (the share of
the sign's occurrences on that beat x log(table share over chance) + the
rest x log(the remainder over chance)). The phase is set once for the
song and each section's downbeat follows it; a tie, or no sign at all,
leaves the bar as the accents and the bass read it. A grid followed
loosely is left alone (not measured).
"""
import bisect
import math

from . import form as form_mod

ON = 0.2                             # beats: an onset this near a beat is on it
LONG = 2.0                           # beats: a long note
WHOLE = 3.5                          # beats: a note held the bar
LOOP_FLOOR = 4                       # bars a repeat reaching the end must last to be the loop's second pass
#  sign -> (weight, the share of its occurrences on the downbeat)
SIGNS = {
    "loop": (1.0, 0.63),             # the loop's second pass starts: the longest repeat running to the end
    "repeats": (1.0, 0.57),          # a repeat of two bars or more starts, weighted by its length in bars
    "whole": (0.5, 0.65),            # a note held a whole bar starts
    "long": (0.5, 0.58),             # a note held two beats or more starts
    "accents": (0.25, 0.30),         # every onset, by its level: the accents the grid was read by
}


def find(grid, song) -> bool:
    """Set the grid's bar phase from where the song repeats, its long
    notes and its accents. Returns whether the bar moved."""
    if not grid or grid.loose or not grid.sections or len(grid.beat_times) < 8:
        return False
    m = grid.meter
    bt = grid.beat_times
    period = (bt[-1] - bt[0]) / (len(bt) - 1)
    bar_len = m * period
    occ = {k: [] for k in SIGNS}             # sign -> [(beat index, weight)]
    for p in song.notes:
        if p.level <= 0:
            continue
        b = grid.beats(p.start)
        i = round(b)
        if abs(b - i) > ON or i < 0:
            continue
        occ["accents"].append((i, p.level))
        if p.midi is not None and p.end is not None:
            held = grid.beats(p.end) - b
            if held >= LONG:
                occ["long"].append((i, 1.0))
            if held >= WHOLE:
                occ["whole"].append((i, 1.0))
    notes = form_mod._notes(song)
    if len(notes) >= 16:
        cells = [max(0, int(math.floor(grid.beats(t) + 0.1))) for t, _ in notes]
        by = {}
        for t, k in notes:
            by.setdefault(k, []).append(t)
        near = [k * bar_len for k in range(-form_mod.SHIFT, form_mod.SHIFT + 1) if k]
        last = max(cells)
        loop = None
        for lag in form_mod._lags(notes, form_mod.SHORTEST * bar_len * 0.95, near, form_mod.LOOP * bar_len * 0.95):
            for a, b in form_mod._repeats(notes, by, lag, cells, 2 * m):
                occ["repeats"].append((a, (b - a) / m))
                if lag >= form_mod.LOOP * bar_len * 0.95 and b >= last - 1.5 * m and b - a >= LOOP_FLOOR * m:
                    if loop is None or b - a > loop[0]:
                        loop = (b - a, a)
        if loop:
            occ["loop"].append((loop[1], 1.0))
    scores = [0.0] * m
    for name, (weight, share) in SIGNS.items():
        xs = occ[name]
        total = sum(w for _, w in xs)
        if total <= 0:
            continue
        on, off = math.log(share * m), math.log((1 - share) / (m - 1) * m)
        for phi in range(m):
            at = sum(w for i, w in xs if (i - phi) % m == 0) / total
            scores[phi] += weight * (at * on + (1 - at) * off)
    top = max(scores)
    if sum(1 for s in scores if s > top - 1e-9) != 1:
        return False
    phi = scores.index(top)
    # each section's downbeat so that its bars sit on the beats numbered phi (mod m) of the song's beat list
    moved, bars = False, []
    for x, (i0, i1) in zip(grid.sections, _spans(grid)):
        if x.meter == m:
            d = (phi - i0) % m
            moved = moved or d != x.downbeat % m
            x.downbeat = d
        bars += bt[i0 + x.downbeat % x.meter:i1:x.meter]
    if moved:
        grid.bar_times = bars
    return moved


def _spans(grid) -> list[tuple[int, int]]:
    """Each section's beats, as indices into the grid's beat list (as beat.rebar counts them)."""
    spans, bt = [], grid.beat_times
    for x in grid.sections:
        tol = 0.5 * x.period
        i0 = bisect.bisect_left(bt, x.first - tol)
        i1 = bisect.bisect_right(bt, x.end + tol)
        if spans and i0 < spans[-1][1]:
            i0 = spans[-1][1]
        spans.append((i0, max(i0, i1)))
    return spans
