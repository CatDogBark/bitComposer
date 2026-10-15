"""
Procedurally generated instrument samples.

Generates waveforms in memory as signed 16-bit PCM at a base frequency.
These get embedded directly into the IT file as sample data.
The tracker engine handles pitch-shifting to play different notes.
"""

import math
import random as _rng
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


def square_wave(duty: float = 0.5, cycles: int = 4) -> tuple[bytes, int]:
    """Generate a square/pulse wave. duty=0.5 is classic square."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        phase = (i % period) / period
        samples.append(1.0 if phase < duty else -1.0)
    data = _pack_samples(_normalize(samples))
    return data, length


def sawtooth_wave(cycles: int = 4) -> tuple[bytes, int]:
    """Generate a sawtooth wave — good for bass and pads."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        phase = (i % period) / period
        samples.append(2.0 * phase - 1.0)
    data = _pack_samples(_normalize(samples))
    return data, length


def triangle_wave(cycles: int = 4) -> tuple[bytes, int]:
    """Generate a triangle wave — soft, mellow tone."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        phase = (i % period) / period
        if phase < 0.25:
            val = phase * 4.0
        elif phase < 0.75:
            val = 2.0 - phase * 4.0
        else:
            val = phase * 4.0 - 4.0
        samples.append(val)
    data = _pack_samples(_normalize(samples))
    return data, length


def sine_wave(cycles: int = 4) -> tuple[bytes, int]:
    """Generate a sine wave — clean sub bass."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        phase = (i % period) / period
        samples.append(math.sin(2.0 * math.pi * phase))
    data = _pack_samples(_normalize(samples))
    return data, length


def noise_white(length: int = 4000) -> tuple[bytes, int]:
    """Generate white noise — hi-hats, snare body."""

    samples = [_rng.uniform(-1.0, 1.0) for _ in range(length)]
    data = _pack_samples(_normalize(samples, amplitude=0.8))
    return data, length


def noise_periodic(period: int = 32, length: int = 4000) -> tuple[bytes, int]:
    """Generate periodic noise (looped short noise) — metallic, NES-like."""

    one_period = [_rng.uniform(-1.0, 1.0) for _ in range(period)]
    samples = []
    for i in range(length):
        samples.append(one_period[i % period])
    data = _pack_samples(_normalize(samples, amplitude=0.7))
    return data, length


def kick_drum(length: int = 3000) -> tuple[bytes, int]:
    """Synthesize a kick drum — pitch-dropping sine with noise burst."""
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Pitch drops from 150Hz to 40Hz
        freq = 150.0 * math.exp(-30.0 * t) + 40.0
        phase = 2.0 * math.pi * freq * t
        # Envelope: quick attack, medium decay
        env = math.exp(-8.0 * t)
        val = math.sin(phase) * env
        # Add noise click at start
        if i < 200:
        
            val += _rng.uniform(-0.3, 0.3) * (1.0 - i / 200.0)
        samples.append(val)
    data = _pack_samples(_normalize(samples))
    return data, length


def snare_drum(length: int = 4000) -> tuple[bytes, int]:
    """Synthesize a snare — sine body + noise."""

    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Tone body at ~180Hz
        tone = math.sin(2.0 * math.pi * 180.0 * t) * math.exp(-20.0 * t)
        # Noise body
        noise = _rng.uniform(-1.0, 1.0) * math.exp(-10.0 * t)
        samples.append(tone * 0.4 + noise * 0.6)
    data = _pack_samples(_normalize(samples))
    return data, length


def hihat(length: int = 2000) -> tuple[bytes, int]:
    """Synthesize a hi-hat — filtered noise burst."""

    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        noise = _rng.uniform(-1.0, 1.0)
        env = math.exp(-40.0 * t)
        samples.append(noise * env)
    data = _pack_samples(_normalize(samples, amplitude=0.6))
    return data, length


def tom_drum(length: int = 3500) -> tuple[bytes, int]:
    """Synthesize a tom — pitched sine with medium decay."""
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Pitch drops from 200Hz to 80Hz
        freq = 200.0 * math.exp(-15.0 * t) + 80.0
        phase = 2.0 * math.pi * freq * t
        env = math.exp(-6.0 * t)
        val = math.sin(phase) * env
        samples.append(val)
    data = _pack_samples(_normalize(samples))
    return data, length


def crash_cymbal(length: int = 8000) -> tuple[bytes, int]:
    """Synthesize a crash cymbal — layered noise with long decay."""

    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Mix of noise frequencies for metallic character
        noise = _rng.uniform(-1.0, 1.0)
        shimmer = math.sin(2.0 * math.pi * 3200.0 * t) * 0.3
        env = math.exp(-4.0 * t)
        samples.append((noise * 0.7 + shimmer) * env)
    data = _pack_samples(_normalize(samples, amplitude=0.7))
    return data, length


def open_hihat(length: int = 5000) -> tuple[bytes, int]:
    """Synthesize an open hi-hat — noise with longer decay than closed."""

    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        noise = _rng.uniform(-1.0, 1.0)
        env = math.exp(-8.0 * t)
        samples.append(noise * env)
    data = _pack_samples(_normalize(samples, amplitude=0.55))
    return data, length


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


# ── Extended waveforms ──

def pwm_sweep(cycles: int = 8) -> tuple[bytes, int]:
    """Pulse width modulation sweep — duty cycle oscillates for rich movement."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        phase = (i % period) / period
        # Duty sweeps from 0.15 to 0.50 over the sample
        t = i / length
        duty = 0.15 + 0.35 * (0.5 + 0.5 * math.sin(2.0 * math.pi * 2.0 * t))
        samples.append(1.0 if phase < duty else -1.0)
    data = _pack_samples(_normalize(samples))
    return data, length


def supersaw(cycles: int = 4, num_saws: int = 5,
             detune: float = 0.015) -> tuple[bytes, int]:
    """Stacked detuned sawtooth waves — thick, chorus-like pad sound."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    # Create slightly detuned frequencies
    freqs = []
    for j in range(num_saws):
        offset = (j - num_saws // 2) * detune
        freqs.append(BASE_NOTE_HZ * (1.0 + offset))
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        val = 0.0
        for freq in freqs:
            phase = (t * freq) % 1.0
            val += 2.0 * phase - 1.0
        samples.append(val / num_saws)
    data = _pack_samples(_normalize(samples))
    return data, length


def filtered_saw(cycles: int = 4, cutoff: float = 0.25) -> tuple[bytes, int]:
    """Low-pass filtered sawtooth — warm, muted tone."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    raw = []
    for i in range(length):
        phase = (i % period) / period
        raw.append(2.0 * phase - 1.0)
    samples = _lowpass(raw, cutoff)
    data = _pack_samples(_normalize(samples))
    return data, length


def sweep_pad(cycles: int = 8) -> tuple[bytes, int]:
    """Sawtooth with filter sweep — opens up over the sample duration."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    raw = []
    for i in range(length):
        phase = (i % period) / period
        raw.append(2.0 * phase - 1.0)
    samples = _lowpass_sweep(raw, start=0.03, end=0.6)
    data = _pack_samples(_normalize(samples))
    return data, length


def distorted_bass(cycles: int = 4, drive: float = 4.0) -> tuple[bytes, int]:
    """Overdriven sawtooth bass — gritty Genesis-style."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    raw = []
    for i in range(length):
        phase = (i % period) / period
        raw.append(2.0 * phase - 1.0)
    samples = _distort(raw, drive)
    # Roll off the harshest highs
    samples = _lowpass(samples, 0.5)
    data = _pack_samples(_normalize(samples))
    return data, length


def pluck_bass_gen(cycles: int = 2) -> tuple[bytes, int]:
    """Short plucky bass — filtered saw with fast decay and high-pass to thin lows."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    raw = []
    for i in range(length):
        phase = (i % period) / period
        # Quick amplitude decay
        env = max(0.0, 1.0 - (i / length) * 1.5)
        raw.append((2.0 * phase - 1.0) * env)
    samples = _lowpass(raw, 0.4)
    samples = _highpass(samples, 0.15)
    data = _pack_samples(_normalize(samples))
    return data, length


def thin_bass_gen(cycles: int = 2) -> tuple[bytes, int]:
    """Thin narrow-pulse bass — minimal low-end, sharp attack."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    raw = []
    for i in range(length):
        phase = (i % period) / period
        env = max(0.0, 1.0 - (i / length) * 1.2)
        raw.append((1.0 if phase < 0.15 else -1.0) * env)
    samples = _highpass(raw, 0.2)
    data = _pack_samples(_normalize(samples))
    return data, length


def bright_bass_gen(cycles: int = 2) -> tuple[bytes, int]:
    """Bright punchy bass — triangle with high-pass, almost mid-range."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    raw = []
    for i in range(length):
        phase = (i % period) / period
        env = max(0.0, 1.0 - (i / length) * 1.3)
        tri = 4.0 * abs(phase - 0.5) - 1.0
        raw.append(tri * env)
    samples = _highpass(raw, 0.2)
    data = _pack_samples(_normalize(samples))
    return data, length


def fm_organ(cycles: int = 6) -> tuple[bytes, int]:
    """3-operator FM — warm organ-like tone (algorithm: parallel modulators)."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        # Op1: modulator at 2x (bright partial)
        mod1 = 1.5 * math.sin(2.0 * phase)
        # Op2: modulator at 3x (bell partial)
        mod2 = 0.8 * math.sin(3.0 * phase)
        # Carrier with both modulators summed
        carrier = math.sin(phase + mod1 + mod2)
        samples.append(carrier)
    data = _pack_samples(_normalize(samples))
    return data, length


def fm_brass(cycles: int = 30) -> tuple[bytes, int]:
    """3-operator FM brass — punchy attack, mellows out."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        # High modulation at attack, decays quickly
        mod_env = 6.0 * math.exp(-12.0 * t) + 1.0
        mod1 = mod_env * math.sin(1.0 * phase)
        mod2 = (mod_env * 0.5) * math.sin(3.0 * phase)
        carrier = math.sin(phase + mod1 + mod2)
        samples.append(carrier)
    data = _pack_samples(_normalize(samples))
    return data, length


def fm_pad(cycles: int = 10) -> tuple[bytes, int]:
    """4-operator FM pad — lush, evolving texture."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        # Slow LFO modulates the modulation depth
        lfo = 0.5 + 0.5 * math.sin(2.0 * math.pi * 3.0 * t)
        mod1 = (1.0 + lfo) * math.sin(2.0 * phase)
        mod2 = 0.6 * math.sin(3.0 * phase + mod1 * 0.3)
        mod3 = 0.4 * math.sin(5.0 * phase) * lfo
        carrier = math.sin(phase + mod1 + mod2 + mod3)
        samples.append(carrier)
    data = _pack_samples(_normalize(samples))
    return data, length


# ── Enhanced drums ──

def kick_layered(length: int = 3500) -> tuple[bytes, int]:
    """Layered kick — sine body + click transient + sub."""
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Sub body: deep sine that drops
        freq = 160.0 * math.exp(-35.0 * t) + 35.0
        sub = math.sin(2.0 * math.pi * freq * t) * math.exp(-7.0 * t)
        # Click transient: short burst of higher harmonics
        click = 0.0
        if i < 150:
            click_env = (1.0 - i / 150.0) ** 2
            click = math.sin(2.0 * math.pi * 2500.0 * t) * click_env * 0.4
            click += math.sin(2.0 * math.pi * 4000.0 * t) * click_env * 0.2
        # Noise punch
        noise = 0.0
        if i < 100:
            noise = _rng.uniform(-0.25, 0.25) * (1.0 - i / 100.0)
        samples.append(sub + click + noise)
    data = _pack_samples(_normalize(samples))
    return data, length


def snare_layered(length: int = 5000) -> tuple[bytes, int]:
    """Layered snare — body + noise + wire rattle."""
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # Tone body: two pitches for thickness
        tone1 = math.sin(2.0 * math.pi * 185.0 * t) * math.exp(-22.0 * t)
        tone2 = math.sin(2.0 * math.pi * 330.0 * t) * math.exp(-30.0 * t) * 0.3
        # Noise body
        noise = _rng.uniform(-1.0, 1.0) * math.exp(-9.0 * t)
        # Wire rattle: filtered noise with slower decay
        wire = _rng.uniform(-0.5, 0.5) * math.exp(-5.0 * t) * 0.3
        samples.append(tone1 * 0.35 + tone2 * 0.15 + noise * 0.5 + wire)
    # Add reverb tail
    float_samples = [s for s in samples]
    float_samples = _reverb_tail(float_samples, decay=0.25, delay_ms=12.0)
    data = _pack_samples(_normalize(float_samples))
    return data, len(float_samples)


def hihat_metallic(length: int = 2200) -> tuple[bytes, int]:
    """Metallic hi-hat — ring-modulated squares for the shimmer, under noise.

    The first version was the three raw squares alone, full-band at 44.1 kHz:
    a buzz with aliasing on top, and at the kit's level it was rough enough
    that it got turned down by two thirds by ear. Now the metallic product is
    one layer under filtered noise, low-passed, and the preset is quieter.
    """
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        s1 = 1.0 if math.sin(2.0 * math.pi * 4500.0 * t) > 0 else -1.0
        s2 = 1.0 if math.sin(2.0 * math.pi * 6000.0 * t) > 0 else -1.0
        s3 = 1.0 if math.sin(2.0 * math.pi * 7800.0 * t) > 0 else -1.0
        metallic = s1 * s2 * s3
        noise = _rng.uniform(-1.0, 1.0)
        env = math.exp(-45.0 * t)
        samples.append((0.35 * metallic + 0.65 * noise) * env)
    samples = _highpass(_lowpass(samples, 0.6), 0.3)
    data = _pack_samples(_normalize(samples, amplitude=0.6))
    return data, length


# FM synthesis — the Genesis sound
def fm_bell(cycles: int = 8) -> tuple[bytes, int]:
    """FM synthesis bell tone — classic Genesis/YM2612 sound."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    mod_ratio = 3.0  # Modulator frequency ratio
    mod_index = 2.5  # Modulation depth
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        modulator = mod_index * math.sin(mod_ratio * phase)
        carrier = math.sin(phase + modulator)
        # Gentle decay
        env = math.exp(-1.5 * t)
        samples.append(carrier * env)
    data = _pack_samples(_normalize(samples))
    return data, length


def fm_bass(cycles: int = 4) -> tuple[bytes, int]:
    """FM synthesis bass — punchy Genesis bass sound."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    mod_ratio = 1.0
    mod_index = 5.0
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        # Modulation index decays for punch
        mod_env = mod_index * math.exp(-8.0 * t)
        modulator = mod_env * math.sin(mod_ratio * phase)
        carrier = math.sin(phase + modulator)
        samples.append(carrier)
    data = _pack_samples(_normalize(samples))
    return data, length


def fm_lead(cycles: int = 40) -> tuple[bytes, int]:
    """FM synthesis lead — bright attack settling into a rounder sustain.

    The YM2612 gave every operator its own envelope, so a lead's modulator
    (its brightness) decayed after the attack. A constant index of 3 for the
    whole note was the buzz that made the palette abrasive."""
    period = int(SAMPLE_RATE / BASE_NOTE_HZ)
    length = period * cycles
    samples = []
    mod_ratio = 2.0
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        mod_index = 1.3 + 1.7 * math.exp(-t / 0.05)
        modulator = mod_index * math.sin(mod_ratio * phase)
        samples.append(math.sin(phase + modulator))
    data = _pack_samples(_normalize(samples))
    return data, length



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


def snes_strings() -> tuple[bytes, int, dict]:
    """Slow-bowed string section — softened saw spectrum, long attack."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.55, 3: 0.4, 4: 0.3, 5: 0.22, 6: 0.16, 7: 0.1, 8: 0.07},
        attack_cycles=36, loop_cycles=2, lowpass=0.55, amplitude=0.85)


def snes_brass() -> tuple[bytes, int, dict]:
    """Brass section — bright overblown onset settling into a rounder tone."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.8, 3: 0.6, 4: 0.45, 5: 0.3, 6: 0.2, 7: 0.12},
        bright={1: 0.7, 2: 0.9, 3: 0.9, 4: 0.8, 5: 0.7, 6: 0.6, 7: 0.5, 8: 0.4, 9: 0.3},
        attack_cycles=8, loop_cycles=2, amplitude=0.9)


def snes_choir() -> tuple[bytes, int, dict]:
    """Choir 'ah' — harmonics weighted by vowel formants, slow attack.

    The formants are baked into the sample, so they shift with pitch exactly
    the way they did on the real hardware."""
    formants = [(700.0, 130.0), (1200.0, 160.0), (2600.0, 220.0)]
    harm = {}
    for k in range(1, 14):
        f = BASE_NOTE_HZ * k
        w = sum(math.exp(-((f - fc) / bw) ** 2) for fc, bw in formants)
        harm[k] = (0.15 + w) / k ** 0.5
    return _sustained_voice(harm, attack_cycles=28, loop_cycles=2,
                            lowpass=0.7, breath=0.04, amplitude=0.85)


def snes_flute() -> tuple[bytes, int, dict]:
    """Flute — near-sine with a breath-noise chiff on the attack."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.22, 3: 0.08, 4: 0.03},
        attack_cycles=6, loop_cycles=1, breath=0.25, amplitude=0.9)


def snes_organ() -> tuple[bytes, int, dict]:
    """Drawbar organ — instant attack, pure harmonic stack."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.7, 3: 0.45, 4: 0.5, 6: 0.3, 8: 0.25},
        attack_cycles=1, loop_cycles=1, amplitude=0.85)


def snes_synth_lead() -> tuple[bytes, int, dict]:
    """Sampled analog-style lead — saw and narrow pulse, lightly filtered."""
    period = SNES_PERIOD
    cycle = []
    for i in range(period):
        ph = i / period
        saw = 2.0 * ph - 1.0
        pulse = 1.0 if ph < 0.3 else -1.0
        cycle.append(0.6 * saw + 0.4 * pulse)
    samples = _lowpass(cycle * 4, 0.5)
    last = samples[-period:]
    return _finish_snes(last * 2, 0.9, 0, 2 * period)


def snes_epiano() -> tuple[bytes, int, dict]:
    """Electric piano — two-operator FM with a decaying index and a tine partial."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        idx = 2.2 * math.exp(-t / 0.18) + 0.15
        body = math.sin(ph + idx * math.sin(ph))
        tine = 0.18 * math.sin(4.0 * ph) * math.exp(-t / 0.08)
        return body + tine
    return _decaying_voice(1.1, tone, amp_tau=0.55, tail_loop=True)


def snes_bell() -> tuple[bytes, int, dict]:
    """Glockenspiel / music-box bell — FM with a 3:1 ratio, long clean decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        idx = 1.6 * math.exp(-t / 0.3) + 0.1
        return math.sin(ph + idx * math.sin(3.0 * ph))
    return _decaying_voice(1.0, tone, amp_tau=0.45, tail_loop=True, amplitude=0.8)


def snes_marimba() -> tuple[bytes, int, dict]:
    """Marimba — fundamental with a quickly-dying fourth harmonic."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return math.sin(ph) + 0.35 * math.sin(4.0 * ph) * math.exp(-t / 0.05)
    return _decaying_voice(0.4, tone, amp_tau=0.11, tail_loop=False)


def snes_pizz() -> tuple[bytes, int, dict]:
    """Pizzicato strings — short Karplus-Strong pluck."""
    return _finish_snes(_karplus_strong(0.35, decay=0.992, brightness=0.6),
                        0.9, rate=KS_TUNED_RATE)


def snes_harp() -> tuple[bytes, int, dict]:
    """Harp — longer, brighter pluck."""
    return _finish_snes(_karplus_strong(0.9, decay=0.9975, brightness=0.9),
                        0.85, rate=KS_TUNED_RATE)


def snes_pluck_bass() -> tuple[bytes, int, dict]:
    """Fingered bass — dark pluck."""
    return _finish_snes(_karplus_strong(0.6, decay=0.997, brightness=0.25),
                        0.95, rate=KS_TUNED_RATE)


def snes_slap_bass() -> tuple[bytes, int, dict]:
    """Slap bass — bright pluck with a hard transient."""
    ks = _karplus_strong(0.5, decay=0.995, brightness=1.0)
    for i in range(min(120, len(ks))):
        ks[i] += 0.6 * (1.0 - i / 120.0) * (1.0 if (i // 3) % 2 else -1.0)
    return _finish_snes(ks, 0.95, rate=KS_TUNED_RATE)


def snes_synth_bass() -> tuple[bytes, int, dict]:
    """Filtered saw bass with a decaying envelope, quiet sustain loop."""
    period = SNES_PERIOD

    def tone(t, i):
        ph = (i % period) / period
        return 2.0 * ph - 1.0
    data, length, meta = _decaying_voice(0.8, tone, amp_tau=0.4, tail_loop=True)
    # Darken after the fact: unpack, filter, repack keeping the loop points.
    ints = struct.unpack(f"<{length}h", data)
    filt = _lowpass([x / 32767.0 for x in ints], 0.35)
    ls = meta["loop_start"]
    tail = filt[ls:ls + period]
    filt = filt[:ls] + tail * 2
    return _finish_snes(filt, 0.95, ls, len(filt))


def snes_orch_hit() -> tuple[bytes, int, dict]:
    """Orchestra hit — stacked saws on root, fifth and octave plus a noise burst."""
    n = int(SNES_RATE * 0.5)
    freqs = [BASE_NOTE_HZ, BASE_NOTE_HZ * 1.5, BASE_NOTE_HZ * 2.0, BASE_NOTE_HZ * 0.5]
    out = []
    for i in range(n):
        t = i / SNES_RATE
        v = sum((2.0 * ((t * f) % 1.0) - 1.0) / len(freqs) for f in freqs)
        v += _rng.uniform(-0.5, 0.5) * math.exp(-t / 0.03)
        out.append(v * math.exp(-t / 0.22))
    return _finish_snes(_lowpass(out, 0.6), 0.95)


def snes_kick() -> tuple[bytes, int, dict]:
    """Tight sampled kick — fast pitch drop, short body."""
    n = int(SNES_RATE * 0.25)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 45.0 + 110.0 * math.exp(-t / 0.035)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = math.sin(ph) * math.exp(-t / 0.11)
        if i < 60:
            v += _rng.uniform(-0.5, 0.5) * (1.0 - i / 60.0)
        out.append(v)
    return _finish_snes(out, 0.95)


def snes_snare() -> tuple[bytes, int, dict]:
    """Gated snare — the big early-90s room sound, closed off by a gate.

    The room is a decaying reverb-like noise tail, not a flat block: a
    constant-level burst that stopped dead read as a glitch, not a gate.
    """
    n = int(SNES_RATE * 0.22)
    gate = int(SNES_RATE * 0.15)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        tone = math.sin(2.0 * math.pi * 190.0 * t) * math.exp(-t / 0.04)
        noise = _rng.uniform(-1.0, 1.0)
        room = noise * 0.45 * math.exp(-t / 0.09) if i < gate else 0.0
        hit = noise * math.exp(-t / 0.025)
        v = 0.5 * tone + 0.6 * hit + room
        if i >= gate:
            # 12 ms gate close, so the tail ends with a quick fall, not a click.
            v = noise * 0.45 * math.exp(-gate / SNES_RATE / 0.09) * math.exp(-(i - gate) / (SNES_RATE * 0.012))
        out.append(v)
    return _finish_snes(_lowpass(out, 0.75), 0.9)


def snes_hat() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.08)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.02) for i in range(n)]
    return _finish_snes(_highpass(out, 0.5), 0.7)


def snes_open_hat() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.35)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.1) for i in range(n)]
    return _finish_snes(_highpass(out, 0.45), 0.6)


def snes_tom() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.4)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 85.0 + 90.0 * math.exp(-t / 0.06)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = math.sin(ph) * math.exp(-t / 0.16)
        v += _rng.uniform(-0.3, 0.3) * math.exp(-t / 0.01)
        out.append(v)
    return _finish_snes(out, 0.9)


def snes_crash() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 1.0)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        v = _rng.uniform(-1.0, 1.0) * 0.7 + 0.3 * math.sin(2.0 * math.pi * 2900.0 * t)
        out.append(v * math.exp(-t / 0.35))
    return _finish_snes(_highpass(out, 0.3), 0.7)


# ── Chip plucks and extra duty cycles ──
#
# Real 8-bit hardware forced variety on a composer: two pulse channels set to
# different duty cycles (12.5% thin and nasal, 25% hollow, 50% full), the
# triangle for bass, and arpeggios played as short decaying blips rather than
# held tones. The palette had five shades of one sound; these give it the
# missing characters. Plucks carry their own envelope and loop a quiet tail,
# so they bypass polish_waveform's attack retiling.

CHIP_PERIOD = int(SAMPLE_RATE / BASE_NOTE_HZ)   # 168


def _chip_decay(cycle: list[float], seconds: float, tau: float,
                lowpass: float, amplitude: float = 0.9) -> tuple[bytes, int, dict]:
    """A single-cycle waveform under an exponential decay, low-passed, with
    the last two cycles frozen in level so a held note sustains quietly."""
    period = len(cycle)
    n = int(SAMPLE_RATE * seconds) // period * period
    loop_start = n - 2 * period
    out = []
    for i in range(n):
        j = min(i, loop_start)
        env = math.exp(-(j / SAMPLE_RATE) / tau)
        out.append(cycle[i % period] * env)
    out = _lowpass(out, lowpass)
    tail = out[loop_start:loop_start + period]
    out = out[:loop_start] + tail * 2
    ints = _normalize(out, amplitude)
    return _pack_samples(ints), len(ints), {
        "rate": WAVEFORM_TUNED_RATE, "loop": True,
        "loop_start": loop_start, "loop_end": len(ints)}


def _pulse_cycle(duty: float) -> list[float]:
    return [1.0 if i / CHIP_PERIOD < duty else -1.0 for i in range(CHIP_PERIOD)]


def _triangle_cycle() -> list[float]:
    return [4.0 * abs((i / CHIP_PERIOD + 0.75) % 1.0 - 0.5) - 1.0 for i in range(CHIP_PERIOD)]


def pulse12_wave(cycles: int = 4) -> tuple[bytes, int]:
    """12.5% pulse — the thin, nasal NES duty."""
    return square_wave(duty=0.125, cycles=cycles)


def square_pluck() -> tuple[bytes, int, dict]:
    return _chip_decay(_pulse_cycle(0.5), 0.5, 0.14, 0.55)


def pulse_pluck() -> tuple[bytes, int, dict]:
    return _chip_decay(_pulse_cycle(0.25), 0.5, 0.14, 0.55)


def pulse12_pluck() -> tuple[bytes, int, dict]:
    return _chip_decay(_pulse_cycle(0.125), 0.5, 0.12, 0.6)


def tri_pluck() -> tuple[bytes, int, dict]:
    return _chip_decay(_triangle_cycle(), 0.6, 0.18, 0.8)


# FM voices to separate the Genesis roles: a pad for harmony and a pluck for arps.
def fm_strings(cycles: int = 40) -> tuple[bytes, int]:
    """Low-index 1:1 FM with a slow swell — a YM2612 string pad."""
    period = CHIP_PERIOD
    length = period * cycles
    samples = []
    for i in range(length):
        t = i / SAMPLE_RATE
        phase = 2.0 * math.pi * BASE_NOTE_HZ * t
        swell = min(1.0, t / 0.08)
        idx = 0.6 + 0.6 * swell
        samples.append(math.sin(phase + idx * math.sin(phase) + 0.3 * math.sin(2.0 * phase)) * (0.3 + 0.7 * swell))
    return _pack_samples(_normalize(samples)), length


def fm_pluck() -> tuple[bytes, int, dict]:
    """2:1 FM with the index and level both falling fast — an FM arp blip."""
    period = CHIP_PERIOD
    cycle_fn = lambda t, ph: math.sin(ph + (2.8 * math.exp(-t / 0.06) + 0.2) * math.sin(2.0 * ph))
    n = int(SAMPLE_RATE * 0.45) // period * period
    loop_start = n - 2 * period
    out = []
    for i in range(n):
        j = min(i, loop_start)
        t = j / SAMPLE_RATE
        ph = 2.0 * math.pi * BASE_NOTE_HZ * i / SAMPLE_RATE
        out.append(cycle_fn(t, ph) * math.exp(-t / 0.16))
    tail = out[loop_start:loop_start + period]
    out = out[:loop_start] + tail * 2
    ints = _normalize(out, 0.9)
    return _pack_samples(ints), len(ints), {
        "rate": WAVEFORM_TUNED_RATE, "loop": True,
        "loop_start": loop_start, "loop_end": len(ints)}


# ── Genesis: feedback FM and DAC drums ──
#
# The YM2612's signature is operator feedback: the first operator modulates
# itself, which turns a sine into a buzzy, saw-like tone, and that is where
# the Sonic / Streets of Rage brass and leads come from. The chip also gave
# every operator its own envelope, so brightness moves after the attack.
# Drums were usually crunchy 8-bit samples played through the DAC at a low
# rate, and a separate PSG square-wave chip filled in thin arps and harmony.
# The earlier "genesis" presets were plain two-operator sine FM with no
# feedback, which at sustain depth sounds like a filtered triangle — i.e.
# like the chip palette. Everything here is built to sound like the chip.

GEN_PERIOD = CHIP_PERIOD   # 168 samples at 44.1 kHz


def _fm_render(n: int, mod_ratio: float, feedback: float, index_fn,
               amp_fn, freeze_at: int | None = None,
               mod2_ratio: float = 0.0, mod2_index: float = 0.0) -> list[float]:
    """Render n samples of carrier <- modulator(with self-feedback) FM.

    index_fn(t) and amp_fn(t) shape modulation depth and level over time;
    with freeze_at, t stops advancing at that sample so the tail is periodic
    and can loop. Feedback follows the YM convention of averaging the last
    two modulator outputs.
    """
    w = 2.0 * math.pi * BASE_NOTE_HZ / SAMPLE_RATE
    y1 = y2 = 0.0
    out = []
    for i in range(n):
        j = i if freeze_at is None else min(i, freeze_at)
        t = j / SAMPLE_RATE
        ph = w * i
        mod = math.sin(mod_ratio * ph + feedback * 0.5 * (y1 + y2))
        y2, y1 = y1, mod
        v = index_fn(t) * mod
        if mod2_index:
            v += mod2_index * math.sin(mod2_ratio * ph)
        out.append(math.sin(ph + v) * amp_fn(t))
    return out


def _fm_sustained(mod_ratio, feedback, idx_attack, idx_sustain, idx_tau,
                  attack_s, lowpass=0.6, amplitude=0.9, loop_cycles=2,
                  mod2_ratio=0.0, mod2_index=0.0) -> tuple[bytes, int, dict]:
    """A feedback-FM voice: attack region, then a seamless looped sustain."""
    period = GEN_PERIOD
    # Half-integer ratios repeat every two cycles.
    if abs(mod_ratio * 2 - round(mod_ratio * 2)) < 1e-9 and abs(mod_ratio - round(mod_ratio)) > 1e-9:
        loop_cycles = max(loop_cycles, 2) * 2 // 2 * 2
    body = max(int(SAMPLE_RATE * (attack_s + 0.12)) // period * period, 8 * period)
    n = body + loop_cycles * period
    freeze = body
    index_fn = lambda t: idx_sustain + (idx_attack - idx_sustain) * math.exp(-t / idx_tau)
    amp_fn = lambda t: min(1.0, t / attack_s) if attack_s > 0 else 1.0
    out = _fm_render(n, mod_ratio, feedback, index_fn, amp_fn, freeze_at=freeze,
                     mod2_ratio=mod2_ratio, mod2_index=mod2_index)
    out = _lowpass(out, lowpass)
    tail = out[body:body + loop_cycles * period]
    # Make the loop exactly periodic (the filter has memory).
    cyc = loop_cycles * period
    out = out[:body] + tail
    ints = _normalize(out, amplitude)
    return _pack_samples(ints), len(ints), {
        "rate": WAVEFORM_TUNED_RATE, "loop": True,
        "loop_start": body, "loop_end": body + cyc}


def _fm_decaying(mod_ratio, feedback, idx0, idx_tau, amp_tau, seconds,
                 lowpass=0.65, amplitude=0.9, sustain_level=None) -> tuple[bytes, int, dict]:
    """A struck feedback-FM voice with a quiet looped tail."""
    period = GEN_PERIOD
    cycles = 2 if abs(mod_ratio - round(mod_ratio)) > 1e-9 else 1
    n = int(SAMPLE_RATE * seconds) // period * period
    loop_start = n - 2 * cycles * period
    index_fn = lambda t: 0.15 + (idx0 - 0.15) * math.exp(-t / idx_tau)
    amp_fn = lambda t: math.exp(-t / amp_tau)
    out = _fm_render(n, mod_ratio, feedback, index_fn, amp_fn, freeze_at=loop_start)
    out = _lowpass(out, lowpass)
    tail = out[loop_start:loop_start + cycles * period]
    out = out[:loop_start] + tail * 2
    ints = _normalize(out, amplitude)
    return _pack_samples(ints), len(ints), {
        "rate": WAVEFORM_TUNED_RATE, "loop": True,
        "loop_start": loop_start, "loop_end": len(ints)}


def gen_lead() -> tuple[bytes, int, dict]:
    """Cutting FM lead — 2:1 with feedback, bright attack settling back."""
    return _fm_sustained(2.0, 0.7, 3.2, 1.5, 0.05, 0.012, lowpass=0.65)


def gen_saw_lead() -> tuple[bytes, int, dict]:
    """Feedback-saw lead — 1:1 with heavy feedback, the classic buzz."""
    return _fm_sustained(1.0, 1.35, 2.2, 1.6, 0.08, 0.01, lowpass=0.6)


def gen_brass() -> tuple[bytes, int, dict]:
    """FM brass — feedback saw with a swelling index, the Sonic horn."""
    return _fm_sustained(1.0, 1.0, 1.2, 2.0, 0.06, 0.035, lowpass=0.6,
                         mod2_ratio=2.0, mod2_index=0.25)


def gen_pad() -> tuple[bytes, int, dict]:
    """FM strings/pad — gentle feedback, slow swell, a 2nd modulator for air."""
    return _fm_sustained(1.0, 0.45, 0.6, 1.3, 0.15, 0.12, lowpass=0.5,
                         amplitude=0.85, mod2_ratio=3.0, mod2_index=0.12)


def gen_bell() -> tuple[bytes, int, dict]:
    """FM bell — 3.5:1 ratio, index and level both ringing down."""
    return _fm_decaying(3.5, 0.0, 2.4, 0.25, 0.6, 1.1, lowpass=0.7, amplitude=0.85)


def gen_pluck() -> tuple[bytes, int, dict]:
    """FM arp blip — fast index and level decay."""
    return _fm_decaying(2.0, 0.5, 3.0, 0.05, 0.14, 0.45, lowpass=0.65)


def gen_slap_bass() -> tuple[bytes, int, dict]:
    """FM slap bass — the hard bright transient that softens into a thump."""
    return _fm_decaying(1.0, 1.1, 4.5, 0.035, 0.5, 0.8, lowpass=0.5, amplitude=0.95)


def gen_sub_bass() -> tuple[bytes, int, dict]:
    """Round FM bass — low index, little feedback, mostly fundamental."""
    return _fm_sustained(1.0, 0.3, 1.4, 0.8, 0.05, 0.006, lowpass=0.45, amplitude=0.95)


def gen_pluck_bass() -> tuple[bytes, int, dict]:
    """Short plucked FM bass for the light setting."""
    return _fm_decaying(1.0, 0.8, 2.5, 0.04, 0.22, 0.5, lowpass=0.55, amplitude=0.9)


# DAC drums: synthesized at 11 kHz and quantised to 8 bits, the way the
# Genesis actually played drum samples.
DAC_RATE = 11025


def _dac_finish(samples: list[float], amplitude: float = 0.9) -> tuple[bytes, int, dict]:
    pk = max((abs(x) for x in samples), default=1.0) or 1.0
    ints = []
    for x in samples:
        q = round(x / pk * amplitude * 127) / 127.0   # 8-bit steps
        ints.append(max(-32768, min(32767, int(q * 32767))))
    return _pack_samples(ints), len(ints), {"rate": DAC_RATE, "loop": False}


def gen_kick() -> tuple[bytes, int, dict]:
    n = int(DAC_RATE * 0.22); out = []; ph = 0.0
    for i in range(n):
        t = i / DAC_RATE
        f = 50.0 + 130.0 * math.exp(-t / 0.03)
        ph += 2.0 * math.pi * f / DAC_RATE
        v = math.sin(ph) * math.exp(-t / 0.09)
        if i < 40:
            v += _rng.uniform(-0.6, 0.6) * (1.0 - i / 40.0)
        out.append(v)
    return _dac_finish(out, 0.95)


def gen_snare() -> tuple[bytes, int, dict]:
    n = int(DAC_RATE * 0.2); out = []
    for i in range(n):
        t = i / DAC_RATE
        tone = math.sin(2.0 * math.pi * 200.0 * t) * math.exp(-t / 0.035)
        noise = _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.07)
        out.append(0.45 * tone + 0.8 * noise)
    return _dac_finish(_lowpass(out, 0.8), 0.9)


def gen_hat() -> tuple[bytes, int, dict]:
    n = int(DAC_RATE * 0.06)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / DAC_RATE) / 0.015) for i in range(n)]
    return _dac_finish(_highpass(out, 0.5), 0.65)


def gen_open_hat() -> tuple[bytes, int, dict]:
    n = int(DAC_RATE * 0.3)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / DAC_RATE) / 0.09) for i in range(n)]
    return _dac_finish(_highpass(out, 0.45), 0.55)


def gen_tom() -> tuple[bytes, int, dict]:
    n = int(DAC_RATE * 0.3); out = []; ph = 0.0
    for i in range(n):
        t = i / DAC_RATE
        f = 95.0 + 100.0 * math.exp(-t / 0.05)
        ph += 2.0 * math.pi * f / DAC_RATE
        out.append(math.sin(ph) * math.exp(-t / 0.13) + _rng.uniform(-0.3, 0.3) * math.exp(-t / 0.008))
    return _dac_finish(out, 0.9)


def gen_crash() -> tuple[bytes, int, dict]:
    n = int(DAC_RATE * 0.9); out = []
    for i in range(n):
        t = i / DAC_RATE
        out.append((_rng.uniform(-1.0, 1.0) * 0.75 + 0.25 * math.sin(2.0 * math.pi * 2700.0 * t)) * math.exp(-t / 0.3))
    return _dac_finish(_highpass(out, 0.3), 0.65)


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


# Which release each preset takes. Sustained voices only; a preset missing
# here keeps hard cuts (plucks, drums, and anything that already decays).
PRESET_RELEASE = {
    # SNES
    "snes_strings": "strings", "snes_choir": "choir", "snes_brass": "brass",
    "snes_flute": "flute", "snes_organ": "organ", "snes_synth_lead": "lead",
    "snes_epiano": "keys", "snes_bell": "keys", "snes_synth_bass": "bass",
    # Genesis
    "gen_lead": "lead", "gen_saw_lead": "lead", "gen_brass": "brass",
    "gen_pad": "pad", "gen_sub_bass": "bass", "gen_bell": "keys",
    "gen_slap_bass": "bass", "gen_pluck_bass": "bass", "gen_pluck": "lead",
    "fm_organ": "organ", "fm_pad": "pad", "fm_strings": "strings", "fm_bass": "bass",
    "fm_lead": "lead", "fm_brass": "brass", "fm_bell": "keys",
    # Chip
    "square_lead": "lead", "pulse_lead": "lead", "pulse12_lead": "lead",
    "triangle_lead": "lead", "pwm_lead": "lead", "filtered_lead": "lead",
    "saw_lead": "lead", "supersaw_lead": "pad", "sweep_lead": "pad",
    "psg_square": "psg",
    "saw_bass": "bass", "triangle_bass": "bass", "sine_bass": "bass",
    "square_bass": "bass", "distorted_bass": "bass", "filtered_bass": "bass",
    "supersaw_bass": "bass",
    "square_pluck": "lead", "pulse_pluck": "lead", "pulse12_pluck": "lead", "tri_pluck": "lead",
}


# ── Rim / ghost-note samples ──
# Ghost snares (the quiet hits between backbeats) play on these when the
# palette has one: a short tick with a little tone, so a ghost reads as a
# touch on the drum rather than a quiet copy of the main hit.

def rim_tick(length: int = 1400) -> tuple[bytes, int]:
    out = []
    for i in range(length):
        t = i / SAMPLE_RATE
        tone = math.sin(2.0 * math.pi * 820.0 * t) * math.exp(-t / 0.012)
        noise = _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.006)
        out.append(0.6 * tone + 0.7 * noise)
    return _pack_samples(_normalize(_highpass(out, 0.3), 0.8)), length


def snes_rim() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.05); out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append(math.sin(2.0 * math.pi * 760.0 * t) * math.exp(-t / 0.012) * 0.6
                   + _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.005) * 0.7)
    return _finish_snes(_highpass(out, 0.3), 0.8)


def gen_rim() -> tuple[bytes, int, dict]:
    n = int(DAC_RATE * 0.05); out = []
    for i in range(n):
        t = i / DAC_RATE
        out.append(math.sin(2.0 * math.pi * 900.0 * t) * math.exp(-t / 0.01) * 0.6
                   + _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.005) * 0.7)
    return _dac_finish(_highpass(out, 0.3), 0.8)


# ── Console output polish for the waveform and FM palettes ──
#
# These presets were raw, full-bandwidth single cycles at 44.1 kHz with no
# envelope: a square lead slammed on at full level with every harmonic the
# sample rate allowed, and stayed flat until cut. No console sounded like
# that — the DAC and the television rolled the top off, and the chips had
# envelopes. polish_waveform() applies a one-pole low-pass (a console output
# stage), ramps a short attack region, and loops the filter's steady state.
# (cutoff, attack_cycles); cutoff is the one-pole alpha at 44.1 kHz, where
# 0.6 is about 6 kHz and 0.4 about 3.5 kHz.
WAVEFORM_POLISH = {
    "square_lead": (0.55, 8), "pulse_lead": (0.55, 8), "saw_lead": (0.5, 8),
    "triangle_lead": (0.5, 6), "fm_bell": (0.65, 2), "fm_lead": (0.6, 4),
    "pwm_lead": (0.5, 0), "supersaw_lead": (0.45, 0), "filtered_lead": (0.5, 8),
    "sweep_lead": (0.6, 0), "fm_organ": (0.6, 3), "fm_brass": (0.6, 6),
    "fm_pad": (0.5, 0), "fm_strings": (0.5, 4), "pulse12_lead": (0.45, 6),
    "psg_square": (0.45, 4),
    "saw_bass": (0.35, 2), "triangle_bass": (0.6, 2), "sine_bass": (0.8, 2),
    "fm_bass": (0.45, 2), "square_bass": (0.4, 2), "distorted_bass": (0.4, 2),
    "filtered_bass": (0.6, 2), "supersaw_bass": (0.35, 0),
    "pluck_bass": (0.6, 0), "thin_bass": (0.5, 0), "bright_bass": (0.6, 0),
}


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


# Instrument presets: (name, generator_func, kwargs, default_volume)
INSTRUMENT_PRESETS = {
    # Melodic — classic
    "square_lead":    (square_wave,    {"duty": 0.5},  64),
    "pulse_lead":     (square_wave,    {"duty": 0.25}, 64),
    "saw_lead":       (sawtooth_wave,  {},             58),
    "triangle_lead":  (triangle_wave,  {},             64),
    "fm_bell":        (fm_bell,        {},             50),
    "fm_lead":        (fm_lead,        {},             58),
    # Melodic — extended
    "pwm_lead":       (pwm_sweep,      {},             60),
    "supersaw_lead":  (supersaw,       {},             52),
    "filtered_lead":  (filtered_saw,   {"cutoff": 0.4}, 58),
    "sweep_lead":     (sweep_pad,      {},             48),
    "fm_organ":       (fm_organ,       {},             52),
    "fm_brass":       (fm_brass,       {},             58),
    "fm_pad":         (fm_pad,         {},             44),
    "fm_strings":     (fm_strings,     {},             46),
    # Genesis — feedback FM voices, DAC drums, PSG square
    "gen_lead":       (gen_lead,       {},             56),
    "gen_saw_lead":   (gen_saw_lead,   {},             54),
    "gen_brass":      (gen_brass,      {},             56),
    "gen_pad":        (gen_pad,        {},             48),
    "gen_bell":       (gen_bell,       {},             54),
    "gen_pluck":      (gen_pluck,      {},             58),
    "gen_slap_bass":  (gen_slap_bass,  {},             64),
    "gen_sub_bass":   (gen_sub_bass,   {},             64),
    "gen_pluck_bass": (gen_pluck_bass, {},             60),
    "gen_kick":       (gen_kick,       {},             64),
    "gen_snare":      (gen_snare,      {},             58),
    "gen_hat":        (gen_hat,        {},             38),
    "gen_open_hat":   (gen_open_hat,   {},             36),
    "gen_tom":        (gen_tom,        {},             56),
    "gen_crash":      (gen_crash,      {},             46),
    "psg_square":     (square_wave,    {"duty": 0.5},  40),
    "rim":            (rim_tick,       {},             44),
    "snes_rim":       (snes_rim,       {},             44),
    "gen_rim":        (gen_rim,        {},             44),
    "fm_pluck":       (fm_pluck,       {},             56),
    # Chip — role voices
    "pulse12_lead":   (pulse12_wave,   {},             58),
    "square_pluck":   (square_pluck,   {},             60),
    "pulse_pluck":    (pulse_pluck,    {},             60),
    "pulse12_pluck":  (pulse12_pluck,  {},             58),
    "tri_pluck":      (tri_pluck,      {},             64),
    # Bass — classic
    "saw_bass":       (sawtooth_wave,  {},             64),
    "triangle_bass":  (triangle_wave,  {},             64),
    "sine_bass":      (sine_wave,      {},             64),
    "fm_bass":        (fm_bass,        {},             64),
    "square_bass":    (square_wave,    {"duty": 0.5},  58),
    # Bass — extended
    "distorted_bass": (distorted_bass, {},             62),
    "filtered_bass":  (filtered_saw,   {"cutoff": 0.2}, 64),
    "supersaw_bass":  (supersaw,       {"detune": 0.008}, 58),
    # Bass — light (high-passed, short decay, minimal low-end)
    "pluck_bass":     (pluck_bass_gen, {},              56),
    "thin_bass":      (thin_bass_gen,  {},              52),
    "bright_bass":    (bright_bass_gen, {},             50),
    # Drums — classic
    "kick":           (kick_drum,      {},             64),
    "snare":          (snare_drum,     {},             56),
    "hihat":          (hihat,          {},             40),
    "tom":            (tom_drum,       {},             56),
    "crash":          (crash_cymbal,   {},             48),
    "open_hihat":     (open_hihat,     {},             38),
    "noise":          (noise_white,    {},             32),
    # Drums — enhanced
    "kick_layered":   (kick_layered,   {},             64),
    "snare_layered":  (snare_layered,  {},             56),
    "hihat_metallic": (hihat_metallic, {},             22),
    # SNES — sampled palette (see the section above)
    "snes_strings":   (snes_strings,   {},             60),
    "snes_brass":     (snes_brass,     {},             64),
    "snes_choir":     (snes_choir,     {},             57),
    "snes_flute":     (snes_flute,     {},             64),
    "snes_organ":     (snes_organ,     {},             57),
    "snes_synth_lead": (snes_synth_lead, {},           64),
    "snes_epiano":    (snes_epiano,    {},             64),
    "snes_bell":      (snes_bell,      {},             62),
    "snes_marimba":   (snes_marimba,   {},             64),
    "snes_pizz":      (snes_pizz,      {},             64),
    "snes_harp":      (snes_harp,      {},             62),
    "snes_pluck_bass": (snes_pluck_bass, {},           64),
    "snes_slap_bass": (snes_slap_bass, {},             64),
    "snes_synth_bass": (snes_synth_bass, {},           64),
    "snes_orch_hit":  (snes_orch_hit,  {},             64),
    "snes_kick":      (snes_kick,      {},             64),
    "snes_snare":     (snes_snare,     {},             64),
    "snes_hat":       (snes_hat,       {},             46),
    "snes_open_hat":  (snes_open_hat,  {},             44),
    "snes_tom":       (snes_tom,       {},             64),
    "snes_crash":     (snes_crash,     {},             53),
}

# Single-cycle waveforms are built on an integer period, so their true pitch is
# SAMPLE_RATE / period rather than BASE_NOTE_HZ. Reporting the rate that the
# period implies makes them play exactly in tune; at 44.1 kHz the old value was
# about six cents sharp.
WAVEFORM_TUNED_RATE = round(int(SAMPLE_RATE / BASE_NOTE_HZ) * BASE_NOTE_HZ)

_ONE_SHOT_WAVEFORMS = {
    "kick", "snare", "hihat", "tom", "crash", "open_hihat", "noise", "rim",
    "kick_layered", "snare_layered", "hihat_metallic",
}


# Sustain-region RMS (of full scale, after the default volume) every looped
# tonal preset is normalised to. 0.18 is where the SNES flute and brass
# landed before normalisation, so the SNES palette keeps its level.
LOUDNESS_TARGET = 0.18


def generate_instrument(name: str) -> dict:
    """Generate a named instrument.

    Returns {"data", "length", "volume", "rate", "loop", "loop_start",
    "loop_end"} — everything an ITSample needs. Waveform presets loop over
    their whole length; one-shots do not loop; SNES voices carry their own
    loop points.
    """
    if name not in INSTRUMENT_PRESETS:
        raise ValueError(f"Unknown instrument: {name}")
    func, kwargs, vol = INSTRUMENT_PRESETS[name]
    result = func(**kwargs)
    if len(result) == 3:
        data, length, meta = result
        meta = dict(meta)
        meta.setdefault("loop_start", 0); meta.setdefault("loop_end", length)
    else:
        data, length = result
        one_shot = name in _ONE_SHOT_WAVEFORMS
        loop_start, loop_end = 0, length
        if not one_shot and name in WAVEFORM_POLISH:
            cutoff, attack = WAVEFORM_POLISH[name]
            data, length, loop_start, loop_end = polish_waveform(data, length, cutoff, attack)
        meta = {"rate": SAMPLE_RATE if one_shot else WAVEFORM_TUNED_RATE,
                "loop": not one_shot, "loop_start": loop_start, "loop_end": loop_end}
    family = PRESET_RELEASE.get(name)
    if meta.get("loop"):
        # Equal loudness: scale the sample data so its sustain region sits at
        # LOUDNESS_TARGET RMS. A square wave sustains at full level and a
        # bell at a fraction, so at the same written volume one was 6-8 dB
        # louder than the other and the mix table chased samples. The data
        # is scaled (not the default volume) because a volume column on a
        # note overrides the default. Scaling up stops where the peak would
        # clip, so percussive voices with a quiet tail keep their shape.
        ints = list(struct.unpack(f"<{length}h", data))
        region = ints[meta["loop_start"]:meta["loop_end"]] or ints
        rms = math.sqrt(sum(v * v for v in region) / len(region)) / 32767.0
        peak = max(abs(v) for v in ints) / 32767.0
        if rms > 1e-4 and peak > 0:
            k = min(LOUDNESS_TARGET / rms, 0.98 / peak)
            if abs(k - 1.0) > 0.02:
                data = _pack_samples([max(-32768, min(32767, int(v * k))) for v in ints])
    if family and meta.get("loop"):
        data, length, meta = add_release(data, length, meta, RELEASE[family])
    return {
        "data": data, "length": length, "volume": vol,
        "rate": meta["rate"], "loop": meta.get("loop", False),
        "loop_start": meta.get("loop_start", 0), "loop_end": meta.get("loop_end", length),
        "sus_loop": meta.get("sus_loop", False), "release": meta.get("release", 0.0),
    }
