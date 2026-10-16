"""The Genesis palette: feedback-FM voices and 8-bit DAC drums, plus the FM
waveforms the chip palette borrows."""
import math
import random
import struct
import zlib

from .dsp import (
    _rng, SAMPLE_RATE, BASE_NOTE_HZ, _pack_samples, _normalize, _lowpass, _highpass, _lowpass_sweep, _distort, _reverb_tail, SNES_RATE, SNES_PERIOD, SNES_TUNED_RATE, _BRR_FILTERS, brr_roundtrip, _peak_normalize, _finish_snes, _additive_cycle, _sustained_voice, _decaying_voice, _karplus_strong, KS_TUNED_RATE, ENSEMBLE_DRY, _ensemble_voice, _drive, RELEASE, add_release, polish_waveform, WAVEFORM_TUNED_RATE, _rms,
)
from .chip import (CHIP_PERIOD)




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


def gen_rim() -> tuple[bytes, int, dict]:
    n = int(DAC_RATE * 0.05); out = []
    for i in range(n):
        t = i / DAC_RATE
        out.append(math.sin(2.0 * math.pi * 900.0 * t) * math.exp(-t / 0.01) * 0.6
                   + _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.005) * 0.7)
    return _dac_finish(_highpass(out, 0.3), 0.8)
