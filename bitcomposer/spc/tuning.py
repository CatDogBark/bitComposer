"""
What pitch a BRR sample sounds at its own rate (32 kHz, pitch 0x1000), so
that a voice's pitch register names a note.

A looped sample's loop usually holds a whole number of cycles, which pins
the period down: the shortest of the periods dividing the loop length that
repeats nearly perfectly is a whole number of cycles (its multiples repeat
too; its fractions do not), and the cycle is the shortest fraction of it
the wave repeats at, since a cycle is rarely a whole number of samples
(FFVI's bass loops hold 28 cycles of 169.14 samples: every 1184 repeats,
seven cycles). Loops that are not a whole number of clean cycles (an
ensemble, a chorus) and samples without a loop (a pluck) are measured by
autocorrelation over the periods a note can have, 25 Hz to 4 kHz, a
one-shot past its attack where it is steadiest. Either way a period only
counts once the waveform has stopped resembling itself (at a short enough
lag every smooth wave "repeats"), and a shorter period is judged on the
wave smoothed to its low harmonics, the ones the ear names a pitch by: the
noise riding on a plucked bass's cycles matches an octave down a little
better, but does not make a cycle two cycles long. When nothing repeats (a
drum, a noise burst) there is no pitch: None.
"""
import math

RATE = 32000
LONGEST = RATE // 25         # periods, in samples, a pitched note can have
SHORTEST = RATE // 4000
CLEAN = 0.95                 # how well a loop-dividing period must repeat
PITCHED = 0.6                # below this, nothing repeats: no pitch
APART = 0.5                  # a wave has moved on from itself once its similarity falls below this
NEARLY = 0.9                 # a shorter period repeating this well, against a longer one, is the period
HARMONICS = 8                # a shorter period is judged on the wave smoothed to this many of its harmonics


def _similarity(x, lag: int) -> float:
    """Normalised correlation of x with itself `lag` samples on."""
    n = len(x) - lag
    if n < 16:
        return 0.0
    a, b = x[:n], x[lag:]
    num = sum(p * q for p, q in zip(a, b))
    den = math.sqrt(sum(p * p for p in a) * sum(q * q for q in b))
    return num / den if den else 0.0


def _at(x, lag: float) -> float:
    """Similarity at a lag between whole samples, x interpolated."""
    i = int(lag)
    f = lag - i
    if f < 1e-6:
        return _similarity(x, i)
    n = len(x) - i - 1
    if n < 16:
        return 0.0
    a = x[:n]
    b = [(1 - f) * p + f * q for p, q in zip(x[i:i + n], x[i + 1:i + 1 + n])]
    num = sum(p * q for p, q in zip(a, b))
    den = math.sqrt(sum(p * p for p in a) * sum(q * q for q in b))
    return num / den if den else 0.0


def _smoothed(x, width: int) -> list:
    """x through a moving average `width` wide (its first null at the frequency of that period)."""
    if width <= 1:
        return x
    out, acc = [], 0.0
    for i, v in enumerate(x):
        acc += v
        if i >= width:
            acc -= x[i - width]
        if i >= width - 1:
            out.append(acc)
    return out


def _apart(x, hi: int) -> int | None:
    """The first lag at which x no longer resembles itself."""
    lag = SHORTEST
    while lag <= hi:
        if _similarity(x, lag) < APART:
            return lag
        lag += max(1, lag // 50)
    return None


def _cycle(x, period: float, lo: int) -> float:
    """The shortest whole fraction of `period` (down to lag `lo`) the wave
    repeats at nearly as well, each judged on the wave smoothed to HARMONICS
    of it. A fraction of a period is a period only if every fraction it
    divides is too, so only those are tried."""
    found = {1}
    k = 2
    while period / k >= max(lo, SHORTEST):
        q = period / k
        if all(k // d in found for d in range(2, k) if k % d == 0) and _similarity(x, round(q)) >= 0.5 * _at(x, period):
            s = _smoothed(x, round(q / HARMONICS))
            if _at(s, q) >= NEARLY * _at(s, period):
                found.add(k)
        k += 1
    return period / max(found)


def _autocorrelation(x, rate: int) -> tuple[float | None, float]:
    """The fundamental by autocorrelation, past the lag where the wave has
    moved on from itself: coarse lags first, then the region of the first
    one repeating nearly as well as the best (a longer one may be a
    multiple of it) at every lag, then any fraction of that it repeats at.
    With it, how well the wave repeats at best."""
    hi = min(LONGEST, len(x) // 2)
    start = _apart(x, hi) if hi > SHORTEST else None
    if start is None:
        return None, 0.0
    coarse, lag = [], start
    while lag <= hi:
        coarse.append((_similarity(x, lag), lag))
        lag += max(1, lag // 50)
    best = max(coarse, default=(0.0, 0))[0]
    if best < PITCHED:
        return None, best
    for s, lag in coarse:                      # the first region repeating nearly as well
        if s >= NEARLY * best:
            return rate / _cycle(x, _peak(x, lag, start, hi), start), best
    return None, best


def _peak(x, lag: int, lo: int, hi: int) -> float:
    """Climb from `lag` to the top of its similarity peak, then place the
    top between whole lags (a parabola through the three around it): a
    period is rarely a whole number of samples, and a whole-sample lag is
    off by several cents at the pitches notes have."""
    s = _similarity(x, lag)
    for step in (1, -1):
        while lo <= lag + step <= hi:
            t = _similarity(x, lag + step)
            if t <= s:
                break
            lag, s = lag + step, t
    a, c = _similarity(x, lag - 1), _similarity(x, lag + 1)
    bend = a - 2 * s + c
    return lag + (0.5 * (a - c) / bend if bend < 0 else 0.0)


def fundamental(sample, rate: int = RATE) -> float | None:
    """The sample's fundamental in Hz at `rate`, or None when it has none."""
    pcm = sample.pcm
    if sample.loops and sample.loop_end - sample.loop_start >= SHORTEST:
        loop = list(pcm[sample.loop_start:sample.loop_end])
        n = len(loop)
        x = (loop * (2 + 2 * LONGEST // n))[:max(2 * n, 2 * LONGEST + 256)]
        start = _apart(x, min(LONGEST, n)) or n
        periods = sorted({n // k for k in range(1, n // SHORTEST + 1) if n % k == 0 and start <= n // k <= LONGEST})
        for p in periods:
            if _similarity(x, p) >= CLEAN:
                return rate / _cycle(x, p, start)
        return _autocorrelation(x, rate)[0]
    # a one-shot: past its attack, from the place along it where it repeats best
    span = 2 * LONGEST + 256
    found = [_autocorrelation(list(pcm[a:a + span]), rate)
             for a in sorted({min(len(pcm) // 4, rate // 20), len(pcm) // 4, len(pcm) // 2})]
    return max(found, key=lambda f: (f[0] is not None, f[1]))[0] if found else None


NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def midi(f0: float, pitch: int) -> float:
    """The MIDI note (cents as the fraction) a sample with fundamental f0
    plays at pitch register `pitch`."""
    return 69 + 12 * math.log2(f0 * pitch / 0x1000 / 440)


def name(m: float) -> str:
    n = round(m)
    cents = round(100 * (m - n))
    return f"{NAMES[n % 12]}{n // 12 - 1}" + (f" {cents:+d}c" if cents else "")
