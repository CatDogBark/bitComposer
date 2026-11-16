"""A voice from a recipe: a sound synthesised from a short description of it.

bitComposer's own voices (packs/bit_voices.py) are made here. A recipe is
numbers that describe a sound, measured once from a recording and kept in
place of it: the levels of a tone's harmonics in whole decibels, its level
at a few moments of its attack, how wide its chorus is and how much breath
it carries; for a struck sound, a few partials and the noise in half-octave
bands at four moments. A recipe is a description, never a recording: it
holds no wave, and every phase and every noise sample is drawn here, from
the recipe's seed. tests/test_bit_voices.py holds every recipe to that.

Two kinds:

  "tone"  a pitched voice that loops: an attack that crosses from the onset's
          harmonics to the steady ones under the measured level curve, then
          a loop of whole periods (one period, or many where the voice has a
          chorus or breath to carry).
  "hit"   a voice that plays once: partials that may glide, and banded
          noise, under the measured level curve.

render() returns the samples as floats with the loop and the pitch; voice()
returns what the sample registry takes.
"""
import math
import random
import struct

BAND_EDGES = (0, 106, 150, 212, 300, 424, 600, 849, 1200, 1697, 2400, 3394, 4800, 6788, 9600)   # the noise bands' lower edges, Hz (half octaves); the last runs to half the rate
OVERSAMPLE = 8                                             # a period's table is drawn this much finer than its frames, for a detuned layer's read
TRIES = 4                                                  # phase sets tried for a period; the one with the lowest peak is kept
FLOOR_DB = -66


def _amp(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _phases(levels: list, period: int, rnd: random.Random) -> list:
    """A phase for each harmonic of a period. The phases are drawn; of TRIES draws the set that gives the flattest
    wave is kept, so a bright spectrum is not a row of spikes."""
    count = min(len(levels), max(1, (period - 1) // 2))
    best = None
    for _ in range(TRIES):
        phases = [rnd.uniform(0.0, 2.0 * math.pi) for _ in range(count)]
        table = _period_table(levels, period, phases, fine=1)
        peak = max(abs(v) for v in table)
        if best is None or peak < best[0]:
            best = (peak, phases)
    return best[1]


def _period_table(levels: list, period: int, phases: list, fine: int = OVERSAMPLE) -> list:
    """One period of the tone whose harmonics sit at `levels` (dB) on `phases`, `fine` points a frame, at unit RMS."""
    count = min(len(levels), len(phases), max(1, (period - 1) // 2))
    amps = [_amp(d) if d > FLOOR_DB else 0.0 for d in levels[:count]]
    size = period * fine
    sin = [math.sin(2.0 * math.pi * i / size) for i in range(size)]
    cos = [math.cos(2.0 * math.pi * i / size) for i in range(size)]
    table = [0.0] * size
    for k, (a, ph) in enumerate(zip(amps, phases), start=1):
        if a <= 0.0:
            continue
        c, s = a * math.cos(ph), a * math.sin(ph)
        j = 0
        for i in range(size):
            table[i] += c * sin[j] + s * cos[j]
            j += k
            if j >= size:
                j -= size
    rms = math.sqrt(sum(v * v for v in table) / size) or 1.0
    return [v / rms for v in table]


def _set_levels(out: list, rate: int, points: list, win: int, end: int) -> None:
    """Put a measured level curve ([ms, dB] points) over the first `end` frames of what was drawn: each point's own
    level is read over `win` frames and set right, straight lines of gain between the points, and no change from
    `end` on where the sound goes on past it (a tone's loop, which is the level the curve is measured against)."""
    marks = []
    for ms, db in points:
        at = int(rate * ms / 1000.0)
        seg = out[at: min(end, at + win)]
        if at >= end or not seg:
            break
        have = math.sqrt(sum(v * v for v in seg) / len(seg))
        marks.append((at + len(seg) / 2.0, max(0.003, min(8.0, _amp(db) / have)) if have > 0 else 1.0))
    if not marks:
        return
    if end < len(out):
        marks.append((float(end), 1.0))
    m = 0
    for i in range(end):
        while m + 1 < len(marks) and i > marks[m + 1][0]:
            m += 1
        if i <= marks[0][0]:
            k = marks[0][1]
        elif m + 1 >= len(marks):
            k = marks[-1][1]
        else:
            (x0, k0), (x1, k1) = marks[m], marks[m + 1]
            k = k0 + (k1 - k0) * (i - x0) / (x1 - x0) if x1 > x0 else k1
        out[i] *= k
    rise = min(end // 4, max(4, int(rate * 0.0005)))        # half a millisecond up from nothing: a sample must not start on a step
    for x in range(rise):
        out[x] *= (x + 1) / (rise + 1)


def _biquad(samples: list, b0: float, b1: float, b2: float, a1: float, a2: float) -> list:
    out = []
    x1 = x2 = y1 = y2 = 0.0
    for x in samples:
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, x, y1, y
        out.append(y)
    return out


def _pass(samples: list, rate: int, hz: float, high: bool) -> list:
    """A two-pole Butterworth low-pass (or high-pass) at hz, run three times: 36 dB an octave."""
    w = 2.0 * math.pi * hz / rate
    alpha = math.sin(w) / (2.0 * 0.7071)
    c = math.cos(w)
    a0 = 1.0 + alpha
    if high:
        coeffs = ((1 + c) / 2 / a0, -(1 + c) / a0, (1 + c) / 2 / a0, -2 * c / a0, (1 - alpha) / a0)
    else:
        coeffs = ((1 - c) / 2 / a0, (1 - c) / a0, (1 - c) / 2 / a0, -2 * c / a0, (1 - alpha) / a0)
    return _biquad(_biquad(_biquad(samples, *coeffs), *coeffs), *coeffs)


def _band(samples: list, rate: int, lo: float, hi: float) -> list:
    """What lies between lo and hi Hz: a high-pass at lo (none from 0) and a low-pass at hi (none at half the rate)."""
    nyq = rate / 2.0
    if lo > 0:
        samples = _pass(samples, rate, min(lo, nyq * 0.95), True)
    if hi < nyq * 0.98:
        samples = _pass(samples, rate, hi, False)
    return samples


def _unit(samples: list) -> list:
    rms = math.sqrt(sum(v * v for v in samples) / len(samples)) if samples else 0.0
    return [v / rms for v in samples] if rms > 0 else list(samples)


def _coloured(count: int, rate: int, hz: float, rnd: random.Random) -> list:
    """`count` frames of noise an octave and a half wide around hz, at unit RMS."""
    white = [rnd.uniform(-1.0, 1.0) for _ in range(count)]
    hz = max(40.0, min(hz, rate * 0.4))
    return _unit(_band(white, rate, hz / 1.7, min(hz * 1.7, rate * 0.45)))


# How far a tone's fundamental swings over its loop (dB, 5th to 95th percentile of its level) against the dry tone's
# share of a three-layer chorus, measured on these layers: the dry share falls as the swing grows, and under an even
# half the swing stops growing.
SWING_TO_DRY = ((3.7, 0.8), (6.4, 0.7), (10.2, 0.6), (17.0, 0.5))


def _layers(recipe: dict) -> list:
    """A tone's layers as (extra cycles over the loop, weight): the dry tone alone, or with a chorus the dry tone and
    two detuned copies that each fit the loop a whole number of times, so the loop closes on every one of them. The
    dry tone's share follows how far the measured fundamental swings (SWING_TO_DRY); the copies' detune follows the
    measured spread, one of them a cycle further off than the other so the two are never both against the dry tone
    for long."""
    chorus = recipe.get("chorus")
    periods = recipe["periods"]
    if not chorus or periods < 8:
        return [(0, 1.0)]
    swing = chorus["swing"]
    table = SWING_TO_DRY
    if swing <= table[0][0]:
        dry = table[0][1]
    elif swing >= table[-1][0]:
        dry = table[-1][1]
    else:
        dry = next(d0 + (d1 - d0) * (swing - s0) / (s1 - s0) for (s0, d0), (s1, d1) in zip(table, table[1:]) if swing <= s1)
    step = max(1, int(round(chorus["cents"] * periods / 1731.0 / math.sqrt(1.0 - dry))))
    return [(0, dry), (step, (1.0 - dry) / 2.0), (-(step + 1), (1.0 - dry) / 2.0)]


def _tone(recipe: dict, rnd: random.Random) -> tuple:
    rate, period, periods = recipe["rate"], recipe["period"], recipe["periods"]
    attack = int(recipe.get("attack", 0))
    breath, strike = recipe.get("breath"), recipe.get("strike")
    layers = _layers(recipe)
    if len(layers) == 1 and not breath:
        periods = 1                                         # nothing moves over the loop: one period is the whole of it
    loop = period * periods
    total = attack + loop
    fine = OVERSAMPLE if len(layers) > 1 else 1             # a lone layer reads its table a whole point a frame: no finer table needed
    size = period * fine
    widest = recipe["steady"] if len(recipe["steady"]) >= len(recipe.get("onset") or ()) else recipe["onset"]
    phases = [_phases(widest, period, rnd) for _ in layers]   # one set of phases a layer for both tables: the attack crosses between
    steady = [_period_table(recipe["steady"], period, ph, fine) for ph in phases]            # two spectra, never between two waves out of step
    onset = [_period_table(recipe["onset"], period, ph, fine) for ph in phases] if recipe.get("onset") and attack else None
    out = [0.0] * total
    for li, (extra, weight) in enumerate(layers):
        step = fine * (periods + extra) / periods           # table points a frame: this layer runs (periods + extra) cycles over the loop
        table, first = steady[li], onset[li] if onset else None
        pos = (-attack * step) % size                       # so the loop starts on the table's first point for every layer
        for i in range(total):
            j = int(pos)
            frac = pos - j
            k = j + 1 if j + 1 < size else 0
            v = table[j] + (table[k] - table[j]) * frac
            if first is not None and i < attack:
                u = i / attack
                u = u * u * (3.0 - 2.0 * u)
                v = (first[j] + (first[k] - first[j]) * frac) * (1.0 - u) + v * u
            out[i] += weight * v
            pos += step
            if pos >= size:
                pos -= size
    body = out[attack:]
    level = math.sqrt(sum(v * v for v in body) / len(body)) or 1.0
    out = [v / level for v in out]                          # the loop at unit RMS; the noise below is levelled against it
    if breath:
        fade = min(loop // 2, max(period, int(rate * 0.02)), attack) if attack else 0
        noise = _coloured(total, rate, breath["hz"], rnd)
        for x in range(fade):                               # the loop's last frames cross into what came just before its start: the seam closes
            w = (x + 1) / (fade + 1)
            noise[total - fade + x] = noise[total - fade + x] * (1.0 - w) + noise[attack - fade + x] * w
        k = _amp(breath["db"])
        out = [v + k * n for v, n in zip(out, noise)]
    if strike and attack:
        count = min(attack, int(rate * strike["ms"] * 1.5 / 1000.0))
        noise = _coloured(count, rate, strike["hz"], rnd)
        k = _amp(min(0.0, strike["db"]))
        for i in range(count):
            out[i] += k * noise[i] * (1.0 - i / count)
    if attack:
        _set_levels(out, rate, recipe.get("env") or [], max(int(rate * 0.004), 2 * period), attack)
    scale = recipe.get("rms", 0.25)
    peak = max(abs(v) for v in out) * scale
    if peak > 0.98:
        scale *= 0.98 / peak
    hz = rate / period
    return [v * scale for v in out], (attack, total), 69.0 + 12.0 * math.log2(hz / 440.0)


def _quarters(levels: list, count: int):
    """A level given at the four quarters of a sound (dB): gain at a frame, straight lines between the quarters' middles."""
    mids = [count * (2 * q + 1) / 8.0 for q in range(4)]

    def gain(i: int) -> float:
        if i <= mids[0]:
            return _amp(levels[0])
        for q in range(3):
            if i <= mids[q + 1]:
                return _amp(levels[q] + (levels[q + 1] - levels[q]) * (i - mids[q]) / (mids[q + 1] - mids[q]))
        return _amp(levels[3])
    return gain


def level_window(rate: int, partials) -> int:
    """The frames a hit's level is read over: four milliseconds, or a period and a half of its lowest partial where
    that is longer (a kick's level read over less than a period follows the wave, not the sound)."""
    lowest = min((min(p["hz"]) for p in partials or ()), default=0.0)
    return max(int(rate * 0.004), 16, int(1.5 * rate / lowest) if lowest > 0 else 0)


def _hit(recipe: dict, rnd: random.Random) -> tuple:
    rate, count = recipe["rate"], recipe["frames"]
    out = [0.0] * count
    for partial in recipe.get("partials", ()):
        f0, f1 = partial["hz"]
        gain = _quarters(partial["db"], count)
        phase = rnd.uniform(0.0, 2.0 * math.pi)
        for i in range(count):
            out[i] += math.sqrt(2.0) * gain(i) * math.sin(phase)
            phase += 2.0 * math.pi * (f0 + (f1 - f0) * i / count) / rate
    rows = recipe.get("noise") or []
    if rows:
        for b in range(len(rows[0])):
            levels = [row[b] for row in rows]
            if max(levels) <= -60:
                continue
            lo = BAND_EDGES[b]
            hi = BAND_EDGES[b + 1] if b + 1 < len(BAND_EDGES) else rate / 2.0
            white = [rnd.uniform(-1.0, 1.0) for _ in range(count)]   # noise of its own for each band: one noise through every filter
            band = _unit(_band(white, rate, lo, min(hi, rate / 2.0)))   # cancels where two bands meet, the filters turning its phase apart
            gain = _quarters(levels, count)
            for i in range(count):
                out[i] += gain(i) * band[i]
    _set_levels(out, rate, recipe.get("env") or [], level_window(rate, recipe.get("partials")), count)
    fade = min(count // 4, max(8, int(rate * 0.002)))       # the last two milliseconds to nothing: an unlooped sample must not end on a step
    for x in range(fade):
        out[count - fade + x] *= 1.0 - (x + 1) / fade
    peak = max(abs(v) for v in out) or 1.0
    scale = recipe.get("peak", 0.9) / peak
    return [v * scale for v in out], None, recipe.get("note")


def render(recipe: dict, seed: int) -> tuple:
    """A voice's samples: (floats -1..1, (loop start, loop end) or None, the MIDI note it sounds at its rate or None
    for an unpitched hit). The same recipe and seed give the same samples on every run; the seed is the voice's own
    (its data keeps it), so a voice's name can change and its sound stay."""
    rnd = random.Random(seed)
    if recipe["kind"] == "tone":
        return _tone(recipe, rnd)
    if recipe["kind"] == "hit":
        return _hit(recipe, rnd)
    raise ValueError(f"not a recipe kind: {recipe['kind']!r}")


def voice(recipe: dict, seed: int) -> tuple:
    """A voice as the sample registry takes one: (16-bit data, frames, the rate it was drawn at, (loop start, loop
    end) or None, the MIDI note it sounds at that rate or None)."""
    samples, loop, note = render(recipe, seed)
    ints = [max(-32768, min(32767, int(round(v * 32767.0)))) for v in samples]
    return struct.pack(f"<{len(ints)}h", *ints), len(ints), recipe["rate"], loop, note
