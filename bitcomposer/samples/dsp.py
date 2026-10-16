"""Sample DSP and the voice builders every palette and pack is made from:
filters, drive, the BRR codec model, additive / ensemble / decaying / plucked
voices, release tails, and the chip waveform polish. Nothing in here names an
instrument; the registry (samples/__init__.py) and the palette and pack
modules do that.
"""
import math
import random
import struct
import zlib

# Noise for the samples comes from this stream, never from the global one:
# generate_instrument reseeds it per preset, so a sample is the same bytes
# whatever was generated before it, and changing a sample's recipe cannot
# move the song's arrangement (it used to: a longer shaker shifted every
# draw after it, titles included).
_rng = random.Random(0)

import struct

# Base sample rate for all generated waveforms
SAMPLE_RATE = 44100

# Base note for samples: C-5 (MIDI 60). The tracker transposes from here.
BASE_NOTE_HZ = 261.63  # C4 in concert pitch


def _pack_samples(samples: list[int]) -> bytes:
    """Pack a list of signed 16-bit integer samples to bytes."""
    return struct.pack(f"<{len(samples)}h", *samples)


def _normalize(samples: list[float], amplitude: float = 0.9) -> list[int]:
    """Normalize float samples to signed 16-bit range."""
    peak = max(abs(s) for s in samples) if samples else 1.0
    if peak == 0:
        peak = 1.0
    scale = 32767 * amplitude / peak
    return [max(-32768, min(32767, int(s * scale))) for s in samples]


# ── DSP utilities ──

def _lowpass(samples: list[float], cutoff_ratio: float = 0.3) -> list[float]:
    """Simple one-pole low-pass filter. cutoff_ratio 0.0-1.0 (lower = darker)."""
    alpha = max(0.001, min(1.0, cutoff_ratio))
    out = []
    prev = 0.0
    for s in samples:
        prev = prev + alpha * (s - prev)
        out.append(prev)
    return out


def _highpass(samples: list[float], cutoff_ratio: float = 0.3) -> list[float]:
    """Simple one-pole high-pass filter. cutoff_ratio 0.0-1.0 (higher = thinner)."""
    alpha = max(0.001, min(1.0, cutoff_ratio))
    out = []
    prev_in = 0.0
    prev_out = 0.0
    for s in samples:
        prev_out = (1.0 - alpha) * (prev_out + s - prev_in)
        prev_in = s
        out.append(prev_out)
    return out


def _lowpass_sweep(samples: list[float], start: float = 0.05,
                   end: float = 0.8) -> list[float]:
    """Low-pass filter with sweeping cutoff — opens up over time."""
    out = []
    prev = 0.0
    n = len(samples)
    for i, s in enumerate(samples):
        t = i / max(1, n - 1)
        alpha = start + (end - start) * t
        alpha = max(0.001, min(1.0, alpha))
        prev = prev + alpha * (s - prev)
        out.append(prev)
    return out


def _distort(samples: list[float], drive: float = 3.0) -> list[float]:
    """Waveshaping distortion — soft clipping with adjustable drive."""
    return [math.tanh(s * drive) for s in samples]


def _reverb_tail(samples: list[float], decay: float = 0.4,
                 delay_ms: float = 15.0) -> list[float]:
    """Simple comb-filter reverb tail for drums."""
    delay_samples = int(SAMPLE_RATE * delay_ms / 1000.0)
    out = list(samples)
    for i in range(delay_samples, len(out)):
        out[i] += out[i - delay_samples] * decay
    # Second tap for density
    delay2 = int(delay_samples * 1.37)
    for i in range(delay2, len(out)):
        out[i] += out[i - delay2] * decay * 0.5
    return out



# ── SNES-style sampled instruments ──
#
# The SPC700 did not synthesize anything. Every SNES voice was a short sample,
# usually stored at 8-16 kHz as 4-bit BRR ADPCM, with a loop point so a
# sustained note could ring for as long as the tracker held it, and the whole
# mix fed into a hardware echo. The palette below imitates that: instruments
# are rendered at SNES_RATE with an attack region followed by a looped sustain
# (or a decaying tail that loops quietly at the end), then run through a
# BRR-style encode/decode so they carry the codec's grain. The old waveform
# palette above stays as the "chip" style.

SNES_RATE = 16000

# Period of C-5 in samples at SNES_RATE. Rounding it to an integer is what lets
# single-cycle regions loop seamlessly; the tiny pitch error that rounding
# causes is undone by reporting the exact rate that period implies as the
# sample's C-5 speed, so every instrument plays in tune.
SNES_PERIOD = round(SNES_RATE / BASE_NOTE_HZ)          # 61
SNES_TUNED_RATE = round(SNES_PERIOD * BASE_NOTE_HZ)    # 15959


# The SPC700's four BRR prediction filters, as (coefficient of the previous
# sample, coefficient of the one before). Filters 2 and 3 are second order and
# predict smooth tonal content almost perfectly, which is why sustained SNES
# samples sound clean while noisy transients pick up the codec's grain.
_BRR_FILTERS = ((0.0, 0.0), (15 / 16, 0.0), (61 / 32, -15 / 16), (115 / 64, -13 / 16))


def brr_roundtrip(samples: list[float]) -> list[float]:
    """Run float samples (-1..1) through a BRR-style codec.

    BRR stores 16-sample blocks of 4-bit residuals with a per-block shift and
    one of four linear prediction filters. Each block tries all four filters
    with the shift the largest open-loop residual demands and keeps whichever
    decodes with the least error. The result is the characteristic SNES grain:
    quiet detail and noisy transients get quantised, while loud sustained
    tones pass almost untouched.
    """
    scale = 32767.0
    ints = [x * scale for x in samples]
    out: list[float] = []
    p1 = p2 = 0.0
    for b in range(0, len(ints), 16):
        block = ints[b:b + 16]
        best = None
        for c1, c2 in _BRR_FILTERS:
            # Open-loop residual estimate to pick the shift.
            a, bb = p1, p2
            max_res = 0.0
            for x in block:
                pred = c1 * a + c2 * bb
                max_res = max(max_res, abs(x - pred))
                a, bb = x, a
            shift = 0
            while shift < 12 and max_res / (1 << shift) > 7.5:
                shift += 1
            step = float(1 << shift)
            # Closed-loop quantisation.
            dec = []
            a, bb = p1, p2
            err = 0.0
            for x in block:
                pred = c1 * a + c2 * bb
                nib = max(-8, min(7, int(round((x - pred) / step))))
                y = max(-32768.0, min(32767.0, pred + nib * step))
                err += (x - y) * (x - y)
                dec.append(y)
                a, bb = y, a
            if best is None or err < best[0]:
                best = (err, dec)
        out.extend(best[1])
        p1, p2 = best[1][-1], (best[1][-2] if len(best[1]) > 1 else p1)
    return [y / scale for y in out]


def _peak_normalize(samples: list[float], amplitude: float = 0.9) -> list[float]:
    peak = max((abs(x) for x in samples), default=1.0) or 1.0
    k = amplitude / peak
    return [x * k for x in samples]


def _finish_snes(samples: list[float], amplitude: float = 0.9,
                 loop_start: int | None = None, loop_end: int | None = None,
                 rate: int = SNES_TUNED_RATE) -> tuple[bytes, int, dict]:
    """Normalise, BRR-grain, pack, and describe loop points for an SNES voice."""
    samples = brr_roundtrip(_peak_normalize(samples, amplitude))
    ints = [max(-32768, min(32767, int(round(x * 32767)))) for x in samples]
    meta = {"rate": rate, "loop": loop_start is not None}
    if loop_start is not None:
        meta["loop_start"] = loop_start
        meta["loop_end"] = loop_end if loop_end is not None else len(ints)
    return _pack_samples(ints), len(ints), meta


def _additive_cycle(harmonics: dict[int, float], period: int = SNES_PERIOD) -> list[float]:
    """One period of a tone built from weighted harmonics."""
    cycle = []
    for i in range(period):
        ph = 2.0 * math.pi * i / period
        cycle.append(sum(a * math.sin(k * ph) for k, a in harmonics.items()))
    return cycle


def _sustained_voice(steady: dict[int, float], bright: dict[int, float] | None = None,
                     attack_cycles: int = 10, loop_cycles: int = 2,
                     lowpass: float | None = None, breath: float = 0.0,
                     amplitude: float = 0.9) -> tuple[bytes, int, dict]:
    """An attack region that ramps up (optionally crossfading from a brighter
    spectrum) followed by a seamless looped sustain of `loop_cycles` periods."""
    steady_cycle = _additive_cycle(steady)
    bright_cycle = _additive_cycle(bright) if bright else steady_cycle
    period = SNES_PERIOD
    samples: list[float] = []
    for c in range(attack_cycles):
        t = (c + 1) / attack_cycles          # 0..1 across the attack
        env = math.sin(0.5 * math.pi * t)    # smooth ramp
        for i in range(period):
            v = bright_cycle[i] * (1.0 - t) + steady_cycle[i] * t
            if breath:
                v += _rng.uniform(-1.0, 1.0) * breath * (1.0 - t)
            samples.append(v * env)
    loop_start = len(samples)
    for _ in range(loop_cycles):
        samples.extend(steady_cycle)
    if lowpass is not None:
        samples = _lowpass(samples, lowpass)
        # The filter has memory, so re-derive the loop region from the final
        # filtered cycle to keep the seam clean.
        last = samples[-period:]
        samples = samples[:loop_start] + last * loop_cycles
    return _finish_snes(samples, amplitude, loop_start, len(samples))


def _decaying_voice(seconds: float, tone, amp_tau: float,
                    tail_loop: bool = False, amplitude: float = 0.9,
                    extra=None) -> tuple[bytes, int, dict]:
    """A struck/plucked voice: tone(t_frozen, i) gives the raw waveform, an
    exponential envelope shapes it, and with tail_loop the last two periods
    are frozen in level so the note can sustain quietly if held."""
    n = int(SNES_RATE * seconds)
    period = SNES_PERIOD
    loop_start = n - 2 * period if tail_loop else None
    samples = []
    for i in range(n):
        j = min(i, loop_start) if loop_start is not None else i
        t = j / SNES_RATE
        env = math.exp(-t / amp_tau)
        # Phase must keep advancing through the frozen tail or the loop clicks.
        v = tone(t, i) * env
        if extra:
            v += extra(t, i)
        samples.append(v)
    if loop_start is not None:
        # Make the two tail cycles identical so the loop is seamless.
        tail = samples[loop_start:loop_start + period]
        samples = samples[:loop_start] + tail * 2
    return _finish_snes(samples, amplitude, loop_start,
                        len(samples) if loop_start is not None else None)


def _karplus_strong(seconds: float, decay: float = 0.996,
                    brightness: float = 1.0, period: int = SNES_PERIOD) -> list[float]:
    """Plucked string by the Karplus-Strong algorithm: a noise burst recirculating
    through a short averaging delay line. brightness < 1 pre-filters the burst."""
    burst = [_rng.uniform(-1.0, 1.0) for _ in range(period)]
    if brightness < 1.0:
        burst = _lowpass(burst, max(0.05, brightness))
    n = int(SNES_RATE * seconds)
    buf = list(burst)
    out = []
    for i in range(n):
        y = buf[i % period]
        nxt = decay * 0.5 * (y + buf[(i + 1) % period])
        out.append(y)
        buf[i % period] = nxt
    return out


# Karplus-Strong's averaging adds half a sample to the loop, so its pitch is
# SNES_RATE / (period + 0.5); report that rate so plucks are in tune too.
KS_TUNED_RATE = round((SNES_PERIOD + 0.5) * BASE_NOTE_HZ)


# ── FFVI orchestral set ──
# The voices Uematsu's SNES scores lean on: a string section with ensemble
# beating, horn and trumpet, oboe and clarinet, piano, music box, a pipe
# organ and a bowed bass. All built the same way as the base SNES set
# (additive or FM, 16 kHz, BRR model in _finish_snes).

# Share of an ensemble voice that is the dry tone; the two detuned copies
# share the rest. At 0.8 the deepest dip of any partial is about -3 dB and
# the fundamental's share of power moves by under 20 points across the loop
# (it moved 60-90 with equal layers); the beating is a shimmer, not a sweep.
ENSEMBLE_DRY = 0.8


def _ensemble_voice(steady: dict[int, float], periods: int = 160,
                    attack_cycles: int = 36, detune_layers: int = 2,
                    lowpass: float | None = None, amplitude: float = 0.85
                    ) -> tuple[bytes, int, dict]:
    """A sustained voice with section chorusing baked in.

    A single-cycle loop cannot beat, so the loop is `periods` cycles long and
    carries the base tone plus detuned copies that are periodic over it: one
    a cycle sharp (f * (periods + 1) / periods) and one two cycles flat, so
    they beat at about f / periods and 2 f / periods and are never in
    antiphase to the dry tone at the same moment. The dry tone leads the mix
    (ENSEMBLE_DRY): equal layers summed together form a comb that cancels
    the odd partials outright once per beat cycle, which measured as the
    fundamental's share of power swinging by 60-90 points across the loop
    on every pad and string voice. The attack ramps over the first
    attack_cycles periods on the same phases, so the loop seam is
    continuous for every layer."""
    rate, period = SNES_RATE, SNES_PERIOD
    base = rate / period
    # Any chorus at all means both copies: a single copy against the dry
    # tone still swings the odd partials by 40 points over the loop.
    layers = [(1.0, ENSEMBLE_DRY if detune_layers else 1.0)]
    if detune_layers:
        layers.append(((periods + 1) / periods, (1.0 - ENSEMBLE_DRY) / 2))
        layers.append(((periods - 2) / periods, (1.0 - ENSEMBLE_DRY) / 2))
    total = (attack_cycles + periods) * period
    out = []
    for i in range(total):
        t = i / rate
        v = 0.0
        for r, w in layers:
            for k, a in steady.items():
                v += w * a * math.sin(2.0 * math.pi * base * r * k * t)
        env = math.sin(0.5 * math.pi * min(1.0, (i + 1) / (attack_cycles * period)))
        out.append(v * env)
    loop_start = attack_cycles * period
    if lowpass is not None:
        alpha = max(0.001, min(1.0, lowpass))
        head, st = [], 0.0
        for v in out[:loop_start]:
            st += alpha * (v - st); head.append(st)
        for v in out[loop_start:]:                 # warm-up pass over the loop
            st += alpha * (v - st)
        loop = []
        for v in out[loop_start:]:
            st += alpha * (v - st); loop.append(st)
        out = head + loop
    return _finish_snes(out, amplitude, loop_start, len(out))


# ── Mega Man X set ──
# Read off the game's own sample bank (SPC snapshots): a chorused distorted
# lead that goes through the echo everywhere, a clean bright pulse synth
# that does not, a slow string pad, a punchy synth bass, a synth brass with
# an overblown attack, a noise-like distorted rhythm guitar played low, and
# a tight kit. Everything here is synthesised from scratch to those shapes.

def _drive(samples: list[float], amount: float) -> list[float]:
    """Soft clipping; the distortion in the guitars."""
    return [math.tanh(v * amount) / math.tanh(amount) for v in samples]


# ── Release tails ──
#
# A note that is let go should die away, not stop between one frame and the
# next. The tracker gives us the mechanism for free: a *sustain loop* is
# looped while the note is held, and a note-off (===) exits it and plays
# whatever follows. So every sustained voice gets its loop region marked as
# the sustain loop and a tail appended after it: the same cycle, decaying
# over the voice's release time. The generator then writes note-off instead
# of note-cut for these voices (see pattern.end_note), and each family
# releases at its own pace — strings long, flute short, organ almost none.
#
# Release lengths in seconds, by family. A new sustained voice picks one of
# these (or overrides it); plucks and drums end on their own and get none.
RELEASE = {
    "strings": 0.30, "choir": 0.35, "pad": 0.40, "brass": 0.15, "flute": 0.08,
    "organ": 0.03, "lead": 0.08, "keys": 0.15, "bass": 0.05, "psg": 0.03,
}


def add_release(data: bytes, length: int, meta: dict, seconds: float,
                rate: int | None = None) -> tuple[bytes, int, dict]:
    """Turn a looped sample into sustain-loop + decaying tail.

    The loop region becomes the sustain loop; after it, the same region is
    repeated and faded with an exponential whose time constant is a third
    of `seconds`, so the tail is ~5% at its end. Continuity across the
    seam is exact because the tail is the loop region itself.
    """
    if not meta.get("loop") or seconds <= 0:
        return data, length, meta
    rate = rate or meta.get("rate", SAMPLE_RATE)
    ints = list(struct.unpack(f"<{length}h", data))
    ls, le = meta["loop_start"], meta["loop_end"]
    region = ints[ls:le]
    if not region:
        return data, length, meta
    n_tail = int(rate * seconds)
    tau = seconds / 4.0                       # ~1.8% at the end of the tail
    fade = max(1, int(rate * 0.003))          # and a 3 ms linear fade to zero
    tail = []
    for i in range(n_tail):
        env = math.exp(-(i / rate) / tau)
        if i >= n_tail - fade:
            env *= (n_tail - i) / fade
        tail.append(int(region[i % len(region)] * env))
    out = ints[:le] + tail
    new_meta = dict(meta)
    new_meta.update({"loop": False, "sus_loop": True,
                     "loop_start": ls, "loop_end": le, "release": seconds})
    return _pack_samples(out), len(out), new_meta


def polish_waveform(data: bytes, length: int, cutoff: float,
                    attack_cycles: int) -> tuple[bytes, int, int, int]:
    """Filter, add an attack, and set loop points on a packed waveform.

    Returns (data, length, loop_start, loop_end). With attack_cycles > 0 the
    waveform must be periodic at the C-5 period: the result is the ramped
    attack followed by two cycles of the filter's steady state, which loop
    seamlessly. With attack_cycles == 0 (sweeps, detuned stacks) the whole
    filtered buffer loops as before.
    """
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    raw = [v / 32767.0 for v in struct.unpack(f"<{length}h", data)]
    if attack_cycles and length % period == 0:
        # Enough cycles for the filter to settle before the loop region. A
        # preset that already evolves over its length (an FM lead whose
        # brightness decays) is used as is, so its last cycle — the settled
        # timbre — becomes the loop; a plain single cycle is tiled.
        total = max(length, (attack_cycles + 6) * period)
        buf = list(raw) if length >= (attack_cycles + 6) * period \
            else (raw[:period] * (total // period))[:total]
        attack_len = attack_cycles * period
        for i in range(attack_len):
            buf[i] *= math.sin(0.5 * math.pi * (i + 1) / attack_len)
        filt = _lowpass(buf, cutoff)
        steady = filt[-period:]
        out = filt[:total - 2 * period] + steady * 2
        loop_start = total - 2 * period
    else:
        out = _lowpass(raw * 2, cutoff)[length:]   # second pass = settled filter
        # Detuned stacks and sweeps are not periodic, so crossfade the loop
        # seam: blend the tail into the head over 64 samples.
        k = min(64, len(out) // 4)
        for i in range(k):
            w = (i + 1) / (k + 1)
            out[len(out) - k + i] = out[len(out) - k + i] * (1 - w) + out[i] * w
        loop_start = 0
    ints = _normalize(out)
    return _pack_samples(ints), len(ints), loop_start, len(ints)

# Single-cycle waveforms are built on an integer period, so their true pitch is
# SAMPLE_RATE / period rather than BASE_NOTE_HZ. Reporting the rate that the
# period implies makes them play exactly in tune; at 44.1 kHz the old value was
# about six cents sharp.
WAVEFORM_TUNED_RATE = round(int(SAMPLE_RATE / BASE_NOTE_HZ) * BASE_NOTE_HZ)


def _rms(values) -> float:
    values = list(values)
    return math.sqrt(sum(v * v for v in values) / len(values)) / 32767.0 if values else 0.0
