"""Mega Man X style pack: its voices (synthesised here) and the arrangement
habits that go with them. Registered on import by bitcomposer.packs."""
import math
import random
import struct
import zlib

from ..samples.dsp import (
    _rng, SAMPLE_RATE, BASE_NOTE_HZ, _pack_samples, _normalize, _lowpass, _highpass, _lowpass_sweep, _distort, _reverb_tail, SNES_RATE, SNES_PERIOD, SNES_TUNED_RATE, _BRR_FILTERS, brr_roundtrip, _peak_normalize, _finish_snes, _additive_cycle, _sustained_voice, _decaying_voice, _karplus_strong, KS_TUNED_RATE, ENSEMBLE_DRY, _ensemble_voice, _drive, RELEASE, add_release, polish_waveform, WAVEFORM_TUNED_RATE, _rms,
)




def mmx_lead_guitar() -> tuple[bytes, int, dict]:
    """Distorted lead guitar, tuned by measurement against the game's own lead
    (power by harmonic band at the three sounding pitches of the melody
    range). A core with strong second and third partials is driven gently
    (tanh 2), then shaped like a cabinet: a cascaded lowpass for the body and
    a presence band from the highpassed drive. The chorus comes after the
    amp and keeps the dry signal in front (ENSEMBLE_DRY) of two detuned
    copies at different offsets: equal, symmetric layers summed together form
    a comb that nulls the odd partials once per beat cycle, which is what
    made the earlier versions collapse to a bare fundamental at the base
    pitch. A pick scrape opens each note.
    The first version was a full saw through a hard clip, a buzzer."""
    rate, period = SNES_RATE, SNES_PERIOD
    base = rate / period; periods, attack = 100, 5
    total = (attack + periods) * period
    weights = [1.0, 0.9, 0.7, 0.4, 0.3, 0.2, 0.12, 0.08]
    mono = [sum(w * math.sin(2.0 * math.pi * base * (k + 1) * i / rate) for k, w in enumerate(weights))
            for i in range(total)]
    driven = _drive(mono, 2.0)
    body = _lowpass(_lowpass(driven, 0.7), 0.7)
    presence = _lowpass(_highpass(driven, 0.4), 0.8)
    amp = [b + 1.2 * q for b, q in zip(body, presence)]
    dry, wet = ENSEMBLE_DRY, (1.0 - ENSEMBLE_DRY) / 2
    out = []
    for i in range(total):
        v = dry * amp[i % total]
        for r in ((periods + 1) / periods, (periods - 2) / periods):
            j = i * r; j0 = int(j) % total; j1 = (j0 + 1) % total; fr = j - int(j)
            v += wet * (amp[j0] * (1.0 - fr) + amp[j1] * fr)
        out.append(v * min(1.0, (i + 1) / (attack * period)))
    pick = int(rate * 0.012)
    for i in range(pick):
        out[i] += 0.3 * _rng.uniform(-1.0, 1.0) * (1.0 - i / pick)
    loop_start = attack * period
    return _finish_snes(out, 0.9, loop_start, len(out))


def mmx_rhythm_guitar() -> tuple[bytes, int, dict]:
    """Distorted rhythm guitar chug — a driven low tone with a scrape of noise
    on the pick, decaying fast; meant for stabs an octave or two down."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    n = int(SNES_RATE * 0.35)
    raw = []
    for i in range(n):
        t = i / SNES_RATE
        ph = w * i / SNES_RATE
        v = sum(math.sin(k * ph) / k for k in range(1, 9)) + 0.35 * math.sin(1.5 * ph)
        v += _rng.uniform(-0.6, 0.6) * math.exp(-t / 0.012)
        raw.append(v)
    raw = _drive(raw, 5.0)
    out = [v * math.exp(-t / 0.16) for v, t in zip(raw, (i / SNES_RATE for i in range(n)))]
    out = _lowpass(out, 0.35)
    period = SNES_PERIOD
    ls = n - 2 * period
    tail = out[ls:ls + period]
    out = out[:ls] + tail * 2
    return _finish_snes(out, 0.95, ls, len(out))


def mmx_pulse_lead() -> tuple[bytes, int, dict]:
    """Clean bright pulse synth — the arp and counter-line voice, dry."""
    return _sustained_voice(
        steady={1: 1.0, 2: 1.0, 3: 0.74, 4: 0.23, 5: 0.19, 6: 0.27, 7: 0.17, 9: 0.1},
        attack_cycles=3, loop_cycles=1, amplitude=0.9)


def mmx_synth_brass() -> tuple[bytes, int, dict]:
    """Synth brass — a bright overblown attack settling into a strong third
    and fourth partial."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.46, 3: 0.79, 4: 0.58, 5: 0.37, 6: 0.13, 7: 0.22, 8: 0.2},
        bright={1: 0.8, 2: 0.9, 3: 1.0, 4: 1.0, 5: 0.9, 6: 0.7, 7: 0.6, 8: 0.5, 9: 0.4},
        attack_cycles=7, loop_cycles=2, amplitude=0.9)


def mmx_string_pad() -> tuple[bytes, int, dict]:
    """String pad — slow swell, the fourth partial on top, chorused."""
    return _ensemble_voice(
        steady={1: 0.3, 2: 0.4, 3: 0.5, 4: 1.0, 5: 0.2, 6: 0.5, 7: 0.3, 8: 0.2},
        periods=150, attack_cycles=55, detune_layers=2, lowpass=0.5, amplitude=0.85)


def mmx_soft_lead() -> tuple[bytes, int, dict]:
    """Soft lead — the octave partial on top of a quiet fundamental, slow."""
    return _sustained_voice(
        steady={1: 0.15, 2: 1.0, 3: 0.5, 4: 0.33, 6: 0.08},
        attack_cycles=14, loop_cycles=2, lowpass=0.6, amplitude=0.85)


def mmx_bass() -> tuple[bytes, int, dict]:
    """Synth bass — a snap of brightness into a round octave-heavy sustain."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = 0.34 * math.sin(ph) + 1.0 * math.sin(2.0 * ph) + 0.41 * math.sin(3.0 * ph) + 0.24 * math.sin(4.0 * ph)
        snap = (0.8 * math.sin(6.0 * ph) + 0.5 * math.sin(9.0 * ph)) * math.exp(-t / 0.03)
        return body + snap
    return _decaying_voice(0.7, tone, amp_tau=0.5, tail_loop=True, amplitude=0.95)


def mmx_kick() -> tuple[bytes, int, dict]:
    """Tight kick — fast pitch drop, a click on top, 80 ms body."""
    n = int(SNES_RATE * 0.2)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 50.0 + 130.0 * math.exp(-t / 0.025)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = math.sin(ph) * math.exp(-t / 0.08)
        v += 0.5 * math.sin(2.0 * math.pi * 2200.0 * t) * math.exp(-t / 0.004)
        out.append(v)
    return _finish_snes(out, 0.95)


def mmx_snare() -> tuple[bytes, int, dict]:
    """Bright snare — a hard crack, a short bright rattle, built to take the echo."""
    n = int(SNES_RATE * 0.2)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        tone = math.sin(2.0 * math.pi * 210.0 * t) * math.exp(-t / 0.03)
        noise = _rng.uniform(-1.0, 1.0)
        out.append(0.45 * tone + 0.8 * noise * math.exp(-t / 0.06))
    return _finish_snes(_highpass(out, 0.2), 0.9)


def mmx_tom() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.3)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 110.0 + 100.0 * math.exp(-t / 0.05)
        ph += 2.0 * math.pi * f / SNES_RATE
        out.append(math.sin(ph) * math.exp(-t / 0.12) + _rng.uniform(-0.3, 0.3) * math.exp(-t / 0.008))
    return _finish_snes(out, 0.9)


def mmx_hat() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.06)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.015) for i in range(n)]
    return _finish_snes(_highpass(out, 0.55), 0.7)


def mmx_open_hat() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.25)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.08) for i in range(n)]
    return _finish_snes(_highpass(out, 0.5), 0.6)


def mmx_crash() -> tuple[bytes, int, dict]:
    """Short bright crash — the game's cymbals are loops cut short, not washes."""
    n = int(SNES_RATE * 0.45)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append((_rng.uniform(-1.0, 1.0) * 0.8 + 0.2 * math.sin(2.0 * math.pi * 3100.0 * t)) * math.exp(-t / 0.15))
    return _finish_snes(_highpass(out, 0.35), 0.7)


# Presets this pack adds to the registry: name -> (builder, kwargs, default volume)
PRESETS = {
    "mmx_lead_guitar": (mmx_lead_guitar, {},           58),
    "mmx_rhythm_guitar": (mmx_rhythm_guitar, {},       60),
    "mmx_pulse_lead": (mmx_pulse_lead, {},             58),
    "mmx_synth_brass": (mmx_synth_brass, {},           58),
    "mmx_string_pad": (mmx_string_pad, {},             54),
    "mmx_soft_lead":  (mmx_soft_lead,  {},             58),
    "mmx_bass":       (mmx_bass,       {},             64),
    "mmx_kick":       (mmx_kick,       {},             64),
    "mmx_snare":      (mmx_snare,      {},             62),
    "mmx_tom":        (mmx_tom,        {},             62),
    "mmx_hat":        (mmx_hat,        {},             50),
    "mmx_open_hat":   (mmx_open_hat,   {},             48),
    "mmx_crash":      (mmx_crash,      {},             52),
}

# Release family per sustaining voice (see samples.dsp.RELEASE)
RELEASE = {
    "mmx_lead_guitar": "lead", "mmx_rhythm_guitar": "lead", "mmx_pulse_lead": "lead",
    "mmx_synth_brass": "brass", "mmx_string_pad": "strings", "mmx_soft_lead": "lead",
    "mmx_bass": "bass",
}


PACK = {
        "palette": "snes",
        "label": "Mega Man X",
        "voices": {
            "lead": ["mmx_lead_guitar", "mmx_lead_guitar", "mmx_synth_brass", "mmx_synth_brass",
                     "mmx_pulse_lead", "mmx_soft_lead"],
            "alt_lead": ["mmx_synth_brass", "mmx_lead_guitar", "mmx_pulse_lead", "mmx_soft_lead"],
            "harmony": ["mmx_rhythm_guitar", "mmx_rhythm_guitar", "mmx_string_pad", "mmx_synth_brass",
                        "mmx_synth_brass"],
            "counter": ["mmx_pulse_lead", "mmx_pulse_lead", "mmx_synth_brass", "mmx_soft_lead"],
            "arp": ["mmx_pulse_lead", "mmx_pulse_lead", "mmx_soft_lead"],
            "bass_heavy": ["mmx_bass"],
            "bass_medium": ["mmx_bass"],
            "bass_light": ["mmx_bass"],
            "drums": {"kick": "mmx_kick", "snare": "mmx_snare", "hihat": "mmx_hat",
                      "tom": "mmx_tom", "crash": "mmx_crash", "open_hihat": "mmx_open_hat",
                      "rim": "snes_rim"},
        },
        "habits": {
            "tempo": {"slow": 0, "medium": 3, "fast": 3},
            "energy": {"chill": 0, "normal": 2, "intense": 3},
            "scale_family": {"minor": 3, "major": 2, "pentatonic": 1},
            "form": {"standard": 2, "aaba": 2, "short": 1, "linear": 1, "rondo": 1},
            "harmony_voicing": {"full": 1, "thin": 3},
            "harmony_mode": {"stabs": 2, "rhythmic": 2, "pulse": 2, "sustain": 1, "ostinato": 1,
                             "chug_sync": 2, "chug_offbeat": 1, "chug_gallop": 2},
            "power_chords": ["mmx_rhythm_guitar"],       # fifths under the chug, real chords elsewhere
            "bass_weight": {"heavy": 3, "medium": 2, "light": 0},
            "bass_style": {"riff": 4, "driving": 2, "octave": 2, "walking": 1, "steady": 0},
            "riffs": {"rock": 2, "gallop": 2, "funk": 2, "pedal_push": 1, "octaves": 1,
                      "fifth_bounce": 1, "drop": 1},
            "drum_density": {"sparse": 0, "normal": 2, "busy": 3},
            "drum_swing": {"off": 5, "light": 0, "heavy": 0},
            "arp_figures": {"broken_octave": 2, "sync_push": 2, "gallop": 2, "classic_up": 1,
                            "run16": 1, "offbeat_stabs": 1, "cascade": 1, "up_down": 1},
            "echo": 1.0,
            "echo_wet": {"light": 1, "normal": 3, "wet": 1},
            "echo_delay": {"slap": 4, "eighth": 2, "dotted": 1, "quarter": 0},
            "echo_stereo": {"bounce": 3, "centre": 1},
            "counter_line": 0.5,
            "section_rolls": False,
            "fill_crash": True,
        },
        "trims": {"kick": 40, "snare": 40, "hihat": 30},
    }
