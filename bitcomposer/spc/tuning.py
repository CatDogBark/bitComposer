"""
What pitch a BRR sample sounds at its own rate (32 kHz, pitch 0x1000), so
that a voice's pitch register names a note.

A looped sample's loop usually holds a whole number of cycles, which pins
the period down: the shortest of the periods dividing the loop length that
repeats nearly perfectly is the fundamental (its multiples repeat too; its
fractions do not). Loops that are not a whole number of clean cycles (an
ensemble, a chorus) and samples without a loop (a pluck) are measured by
autocorrelation over the periods a note can have, 25 Hz to 4 kHz. Either
way a period only counts once the waveform has stopped resembling itself
(at a short enough lag every smooth wave "repeats"). When nothing repeats
(a drum, a noise burst) there is no pitch: None.
"""
import math

RATE = 32000
LONGEST = RATE // 25         # periods, in samples, a pitched note can have
SHORTEST = RATE // 4000
CLEAN = 0.95                 # how well a loop-dividing period must repeat
PITCHED = 0.6                # below this, nothing repeats: no pitch
APART = 0.5                  # a wave has moved on from itself once its similarity falls below this


def _similarity(x, lag: int) -> float:
    """Normalised correlation of x with itself `lag` samples on."""
    n = len(x) - lag
    if n < 16:
        return 0.0
    a, b = x[:n], x[lag:]
    num = sum(p * q for p, q in zip(a, b))
    den = math.sqrt(sum(p * p for p in a) * sum(q * q for q in b))
    return num / den if den else 0.0


def _apart(x, hi: int) -> int | None:
    """The first lag at which x no longer resembles itself."""
    lag = SHORTEST
    while lag <= hi:
        if _similarity(x, lag) < APART:
            return lag
        lag += max(1, lag // 50)
    return None


def _autocorrelation(x, rate: int) -> float | None:
    """The fundamental by autocorrelation, past the lag where the wave has
    moved on from itself: coarse lags first, then the region of the first
    one repeating nearly as well as the best (a longer one may be a
    multiple of it) at every lag."""
    hi = min(LONGEST, len(x) // 2)
    start = _apart(x, hi) if hi > SHORTEST else None
    if start is None:
        return None
    coarse, lag = [], start
    while lag <= hi:
        coarse.append((_similarity(x, lag), lag))
        lag += max(1, lag // 50)
    best = max(coarse, default=(0.0, 0))[0]
    if best < PITCHED:
        return None
    for s, lag in coarse:                      # the first region repeating nearly as well
        if s >= 0.9 * best:
            return rate / _peak(x, lag, start, hi)
    return None


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
                return rate / p
        return _autocorrelation(x, rate)
    start = min(len(pcm) // 4, rate // 20)          # past the attack
    return _autocorrelation(list(pcm[start:start + 2 * LONGEST + 256]), rate)


NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def midi(f0: float, pitch: int) -> float:
    """The MIDI note (cents as the fraction) a sample with fundamental f0
    plays at pitch register `pitch`."""
    return 69 + 12 * math.log2(f0 * pitch / 0x1000 / 440)


def name(m: float) -> str:
    n = round(m)
    cents = round(100 * (m - n))
    return f"{NAMES[n % 12]}{n // 12 - 1}" + (f" {cents:+d}c" if cents else "")
