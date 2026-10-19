"""
The SNES chip's sound as SPC to IT models it: what its envelopes,
interpolation, echo and noise do to a sample or a note, from the register
values a note carries. Arithmetic on samples and registers only: what an
IT module can carry of it is convert.py's question, and how is it_song.py's.

The emulator (emu/src/dsp.rs) plays the SNES chip; this is the same
hardware described for a converter, which needs answers the emulator's
output does not give on its own: an envelope as a curve, a sample as the
chip reads it, the echo's gain over one note, its colour after k trips.
"""
import cmath
import math
from array import array

from . import RATE
from .notes import KEY_ON_DELAY

RELEASE = 256                         # samples a released SNES voice takes to fall silent
# The SNES chip reads every sample through a 4-point Gaussian interpolation, a lowpass in
# the sample's own terms: -0.6 dB at a tenth of its rate, -4 dB at a quarter, -10.5 dB at
# 0.4, -15 dB at the top (computed from the hardware table in emu/src/dsp.rs, averaged over
# the interpolation's 256 positions). An IT player interpolates almost ideally, so the
# samples are filtered with this response first: the half of a symmetric 9-tap filter,
# within 0.4 dB of it. Without it, bright samples played low came out up to 3 times too
# strong above their own top (Secret of Evermore's wind), and every instrument too bright.
GAUSS_RESPONSE = (0.615783, 0.199155, -0.010345, 0.004865, -0.002367)

# The SNES chip's envelope rates: samples between steps (rate 0 never steps).
RATE_PERIOD = [0, 2048, 1536, 1280, 1024, 768, 640, 512, 384, 320, 256, 192, 160, 128, 96, 80,
               64, 48, 40, 32, 24, 20, 16, 12, 10, 8, 6, 5, 4, 3, 2, 1]
# Where each rate's steps fall on the SNES chip's one counter, shared by all eight voices:
# a rate steps in sample s (counting from the snapshot, the first being 1) when
# s % period == phase % period (every period divides the counter's range, 30720).
RATE_PHASE = [1, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536,
              0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 0, 0]


# Envelopes -------------------------------------------------------------------

def _rule(adsr1: int, adsr2: int, gain: int, mode: str):
    """What the SNES chip's envelope does next under these registers in this
    phase: (rate, step, sustain boundary). step: an int added (attack),
    None for the exponential decrease, ("set", level) for direct GAIN, or
    ("gain", kind) for GAIN's four slopes."""
    if adsr1 & 0x80:
        if mode == "attack":
            rate = (adsr1 & 0x0F) * 2 + 1
            return rate, 0x400 if rate == 31 else 0x20, adsr2 >> 5
        if mode == "decay":
            return ((adsr1 >> 4) & 7) * 2 + 16, None, adsr2 >> 5
        return adsr2 & 0x1F, None, adsr2 >> 5
    if not gain & 0x80:
        return 31, ("set", (gain & 0x7F) << 4), gain >> 5
    return gain & 0x1F, ("gain", (gain >> 5) & 3), gain >> 5


def _advance(env: int, mode: str, hidden: int, step, boundary: int) -> tuple[int, str, int]:
    """One envelope step: (level, phase, the level before clamping)."""
    if step is None:
        env -= 1
        env -= env >> 8
    elif isinstance(step, int):
        env += step
    elif step[0] == "set":
        env = step[1]
    else:
        g = step[1]
        if g == 0:
            env -= 0x20
        elif g == 1:
            env -= 1
            env -= env >> 8
        elif g == 2:
            env += 0x20
        else:
            env += 0x20 if hidden < 0x600 else 8
    if mode == "decay" and (env >> 8) == boundary:
        mode = "sustain"
    hidden = env
    if env > 0x7FF or env < 0:
        env = 0 if env < 0 else 0x7FF
        if mode == "attack":
            mode = "decay"
    return env, mode, hidden


def envelope_ticks(adsr1: int, adsr2: int, gain: int, tick_hz: float, top: int, seconds: float = 20.0) -> list[int]:
    """The SNES chip's envelope for these registers from a key-on, tick by
    tick at `tick_hz`: each tick's RMS level on a scale of 0 to `top`. It
    stops once the envelope has gone, or has held one level (at that scale)
    for a second; the level holds after the last."""
    env, mode, hidden = 0, "attack", 0
    levels = []
    per_tick = RATE / tick_hz
    next_tick, n = per_tick, 0
    acc = count = 0
    limit = int(RATE * seconds)
    stable = 0
    while n < limit:
        rate, step, boundary = _rule(adsr1, adsr2, gain, mode)
        period = RATE_PERIOD[rate]
        if period and n % period == 0:
            env, mode, hidden = _advance(env, mode, hidden, step, boundary)
        acc += env * env
        count += 1
        if n + 1 >= next_tick:              # each tick carries its window's RMS: an IT envelope holds
            levels.append(round(top * math.sqrt(acc / count) / 0x7FF))   # nothing finer than a tick, and a
            # fast decay's mean would lose the energy of its peak
            acc = count = 0
            next_tick += per_tick
            stable = stable + 1 if len(levels) > 1 and levels[-1] == levels[-2] else 0
            if (env == 0 and mode != "attack") or stable > tick_hz:      # gone, or held for a second
                break
        n += 1
    return levels


def envelope_track(adsr1: int, adsr2: int, gain: int, changes, length: int,
                   start: int | None = None) -> list[tuple[int, int]]:
    """The SNES chip's envelope through a note of `length` samples, the
    registers replaced by `changes` [(sample, ADSR1, ADSR2, GAIN)] as they
    come: [(sample, level 0-0x7FF)], each level holding until the next
    listed. Only the envelope's steps are visited (a held level is jumped
    over), so a long note costs its steps, not its samples.

    `start` is the sample (from the snapshot) of the envelope's first run:
    with it, steps fall where the hardware's shared counter puts them;
    without it, every `period` samples from the note's start (as an IT
    instrument's envelope, which starts with its note, must). A driver that
    shapes notes itself, switching GAIN ramps and holds hundreds of times a
    note (Secret of Evermore's), drifts a step on most switches without it."""
    env, mode, hidden, n = 0, "attack", 0, 0
    track = [(0, 0)]
    changes = sorted(changes)
    regs, ci = (adsr1, adsr2, gain), 0
    while n < length:
        while ci < len(changes) and changes[ci][0] <= n:
            regs, ci = changes[ci][1:], ci + 1
        upto = changes[ci][0] if ci < len(changes) else length
        rate, step, boundary = _rule(*regs, mode)
        period = RATE_PERIOD[rate]
        if not period:
            at = n
        elif start is None:
            at = n if n % period == 0 else (n // period + 1) * period
        else:
            at = n + (RATE_PHASE[rate] - (start + n)) % period
        if not period or at >= upto:
            n = upto
            continue
        state = _advance(env, mode, hidden, step, boundary)
        if state == (env, mode, hidden):     # held: nothing moves until the registers do
            n = upto
            continue
        env, mode, hidden = state
        if env != track[-1][1]:
            track.append((at, env)) if at > track[-1][0] else track.__setitem__(-1, (at, env))
        n = at + 1
    return track


def seen(t: float) -> int:
    """The sample (from the snapshot, the first being 1) in which the SNES
    chip sees what was written at time t: a write made in sample k's 32
    cycles is seen from sample k + 1."""
    return math.floor(t * RATE + 1e-6) + 1


def envelope_start(start: float) -> int:
    """The sample in which a note starting at `start` (as notes.decode times
    it) first runs its envelope: its key-on is taken on an odd sample, and
    the envelope first runs four samples later."""
    kon = seen(start - KEY_ON_DELAY)
    return (kon if kon % 2 else kon + 1) + 4


# Samples ---------------------------------------------------------------------

def snes_interpolated(pcm, loop) -> array:
    """A sample as the SNES chip's interpolation colours it (GAUSS_RESPONSE),
    for an IT player that interpolates cleanly. `loop` is (start, end) or
    None; a loop is filtered as it repeats, its own end before its start."""
    norm = GAUSS_RESPONSE[0] + 2 * sum(GAUSS_RESPONSE[1:])
    taps = [h / norm for h in GAUSS_RESPONSE]
    n, k_max = len(pcm), len(taps) - 1
    ls, le = loop if loop else (None, n)

    def at(i: int, looping: bool) -> int:
        if loop and (i >= le or (looping and i < ls)):
            i = ls + (i - ls) % (le - ls)
        return pcm[i] if 0 <= i < n else 0

    out = array("h")
    for i in range(le if loop else n):
        looping = bool(loop) and i >= ls
        v = taps[0] * pcm[i] + sum(taps[k] * (at(i - k, looping) + at(i + k, looping)) for k in range(1, k_max + 1))
        out.append(max(-32768, min(32767, round(v))))
    return out


def noise(rate: int) -> list[int]:
    """The SNES chip's noise at noise clock `rate`, as it comes out: a second
    of 32 kHz, each step of the 15-bit shift register held until the next
    (RATE_PERIOD[rate] samples). Read as a signed number, each step is half
    the last plus a new top bit, so the level and the tilt toward the bass
    are the hardware's; held rather than interpolated, so are its highs."""
    n, out, per = 0x4000, [], RATE_PERIOD[rate]
    while len(out) < RATE:
        n = (n >> 1) | (((n << 14) ^ (n << 13)) & 0x4000)
        v = (n << 17) & 0xFFFFFFFF                       # the emulator's ((n << 17) >> 16) & !1, in i32
        out.extend([((v - (1 << 32) if v & 0x80000000 else v) >> 16) & ~1] * per)
    return out[:RATE]


# The echo --------------------------------------------------------------------

def echo_filter_peak(taps) -> float:
    """The echo filter's strongest gain at any pitch (FIR0..FIR7, -128..127):
    what one trip round the echo can at most hand back."""
    return max(abs(sum(c / 128 * cmath.exp(-2j * math.pi * f / 64 * k) for k, c in enumerate(taps))) for f in range(33))


def echo_gains(pcm, loop, pitch: int, taps, repeats: int, n: int = 1024) -> list[float]:
    """How much of a note the echo hands back on each of its repeats: the
    filter's gain over the note's own spectrum, which is what a repeat
    sounds at (a filter can pass almost nothing at DC and everything at
    3 kHz, as Mega Man X's does). The sample is played at its pitch, as the
    voice reads it, then filtered once per repeat; each entry is the RMS
    ratio after that many passes. `loop` is (start, end) or None for a
    one-shot; `pcm` None is noise, whose spectrum is flat. `taps` are
    FIR0..FIR7; FIR0 weighs the oldest of eight samples."""
    c = [t / 128 for t in taps]
    if pcm is None:
        flat = math.sqrt(sum(x * x for x in c))
        return [flat ** k for k in range(1, repeats + 1)]
    step, pos, x = pitch / 0x1000, 0.0, []
    end = (loop[1] if loop else len(pcm)) - 1
    while len(x) < n:
        if pos >= end:
            if loop is None or end <= loop[0]:
                break
            pos = loop[0] + (pos - end) % (end - loop[0])
        i = int(pos)
        x.append(pcm[i] + (pcm[i + 1] - pcm[i]) * (pos - i))
        pos += step
    energy = lambda v: sum(s * s for s in v[8 * repeats:])        # noqa: E731
    base = energy(x)
    if len(x) <= 8 * repeats + 16 or not base:
        return [abs(sum(c)) ** k for k in range(1, repeats + 1)]
    gains = []
    for _ in range(repeats):
        x = [sum(c[j] * x[i - 7 + j] for j in range(8)) if i >= 7 else 0.0 for i in range(len(x))]
        gains.append(math.sqrt(energy(x) / base))
    return gains


def echo_coloured(pcm, loop, ratio: float, taps, passes: int = 1) -> tuple[array, float]:
    """The sample as the echo hands it back after `passes` trips round its
    loop, when the voice plays it at `ratio` times its own rate. Each trip
    goes through the echo filter, whose taps are 1/32000 s apart at the
    output (so `ratio` samples apart in the sample), and so is coloured by
    it and delayed by its span: a repeat comes passes x (echo delay + the
    filter's span) late, where rows alone give passes x the delay. FFVI's
    Dark World has one tap, 7 samples back; repeats 7 samples a trip early
    stacked differently on its held organ chords, a third brighter than the
    original's. The filter is applied `passes` times as one (its taps
    convolved), so the sample is interpolated once. A loop is filtered as it
    repeats. Returns the 16-bit data and the factor it was scaled down by to
    fit (1.0 when it did)."""
    one = [0.0] * 8                          # the filter by delay in output samples: FIR0 weighs the oldest of eight
    for k, t in enumerate(taps):
        one[7 - k] = t / 128
    h = [1.0]
    for _ in range(passes):
        h = [sum(h[i] * one[j - i] for i in range(max(0, j - 7), min(len(h), j + 1))) for j in range(len(h) + 7)]
    terms = [(d * ratio, c) for d, c in enumerate(h) if c]
    span = max((d for d, _ in terms), default=0.0)
    if loop:
        ls, le = loop
        ext = list(pcm[:le]) + list(pcm[ls:le]) * (1 + math.ceil(span / max(1, le - ls)))
    else:
        ext = list(pcm)
    n = len(ext)

    def at(x: float) -> float:
        if x < 0:
            return 0.0
        i = int(x)
        return ext[i] + (ext[i + 1] - ext[i]) * (x - i) if i + 1 < n else (ext[i] if i < n else 0.0)

    y = [sum(c * at(i - d) for d, c in terms) for i in range(n)]
    if loop:                                 # the attack as it first plays, the loop as it repeats (its last pass)
        y = y[:loop[0]] + y[n - (loop[1] - loop[0]):]
    peak = max((abs(v) for v in y), default=0.0)
    fit = min(1.0, 32767 / peak) if peak else 1.0
    return array("h", (round(v * fit) for v in y)), fit
