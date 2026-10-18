"""The base SNES palette: sampled-style voices and the gated kit."""
import math
import struct

from .dsp import (
    _rng, BASE_NOTE_HZ, _lowpass, _highpass, SNES_RATE, SNES_PERIOD, _finish_snes, _sustained_voice, _decaying_voice, _karplus_strong, KS_TUNED_RATE,
)




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
    """Flute — near-sine with a breath-noise chiff on the attack; a little
    second and third partial so it carries as a lead (centroid ~1.4x f0)."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.38, 3: 0.16, 4: 0.06, 5: 0.03},
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


def snes_rim() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.05); out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append(math.sin(2.0 * math.pi * 760.0 * t) * math.exp(-t / 0.012) * 0.6
                   + _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.005) * 0.7)
    return _finish_snes(_highpass(out, 0.3), 0.8)
