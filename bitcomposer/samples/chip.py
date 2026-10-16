"""The chip palette: NES / Game Boy style waveforms, plucks, basses and the
synthesised drum kits (classic and layered)."""
import math
import random
import struct
import zlib

from .dsp import (
    _rng, SAMPLE_RATE, BASE_NOTE_HZ, _pack_samples, _normalize, _lowpass, _highpass, _lowpass_sweep, _distort, _reverb_tail, SNES_RATE, SNES_PERIOD, SNES_TUNED_RATE, _BRR_FILTERS, brr_roundtrip, _peak_normalize, _finish_snes, _additive_cycle, _sustained_voice, _decaying_voice, _karplus_strong, KS_TUNED_RATE, ENSEMBLE_DRY, _ensemble_voice, _drive, RELEASE, add_release, polish_waveform, WAVEFORM_TUNED_RATE, _rms,
)




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

_ONE_SHOT_WAVEFORMS = {
    "kick", "snare", "hihat", "tom", "crash", "open_hihat", "noise", "rim",
    "kick_layered", "snare_layered", "hihat_metallic",
}
