"""Final Fantasy VI style pack: its voices (synthesised here) and the arrangement
habits that go with them. Registered on import by bitcomposer.packs."""
import math
import random
import struct
import zlib

from ..samples.dsp import (
    _rng, SAMPLE_RATE, BASE_NOTE_HZ, _pack_samples, _normalize, _lowpass, _highpass, _lowpass_sweep, _distort, _reverb_tail, SNES_RATE, SNES_PERIOD, SNES_TUNED_RATE, _BRR_FILTERS, brr_roundtrip, _peak_normalize, _finish_snes, _additive_cycle, _sustained_voice, _decaying_voice, _karplus_strong, KS_TUNED_RATE, ENSEMBLE_DRY, _ensemble_voice, _drive, RELEASE, add_release, polish_waveform, WAVEFORM_TUNED_RATE, _rms,
)




def ffvi_strings() -> tuple[bytes, int, dict]:
    """String section — softened saw spectrum with ensemble beating."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.55, 3: 0.4, 4: 0.3, 5: 0.22, 6: 0.16, 7: 0.1, 8: 0.07},
        periods=160, attack_cycles=36, lowpass=0.55, amplitude=0.85)


def ffvi_contrabass() -> tuple[bytes, int, dict]:
    """Bowed double basses — dark, slow, a little ensemble spread."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.6, 3: 0.35, 4: 0.2, 5: 0.1},
        periods=120, attack_cycles=14, detune_layers=1, lowpass=0.3, amplitude=0.9)


def ffvi_horn() -> tuple[bytes, int, dict]:
    """French horn — round, dark brass with a soft onset; enough second and
    third partial to carry a counter-line."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.65, 3: 0.42, 4: 0.22, 5: 0.1, 6: 0.05},
        bright={1: 0.9, 2: 0.7, 3: 0.5, 4: 0.35, 5: 0.2, 6: 0.1},
        attack_cycles=12, loop_cycles=2, lowpass=0.5, amplitude=0.9)


def ffvi_trumpet() -> tuple[bytes, int, dict]:
    """Trumpet — bright, strong upper partials, fast overblown onset."""
    return _sustained_voice(
        steady={1: 0.8, 2: 1.0, 3: 0.9, 4: 0.7, 5: 0.55, 6: 0.4, 7: 0.3, 8: 0.2, 9: 0.12},
        bright={1: 0.5, 2: 0.8, 3: 1.0, 4: 1.0, 5: 0.9, 6: 0.8, 7: 0.7, 8: 0.6, 9: 0.5, 10: 0.4},
        attack_cycles=5, loop_cycles=2, amplitude=0.9)


def ffvi_oboe() -> tuple[bytes, int, dict]:
    """Oboe — reedy, the second and fourth partials over the fundamental."""
    return _sustained_voice(
        steady={1: 0.6, 2: 1.0, 3: 0.8, 4: 0.9, 5: 0.5, 6: 0.35, 7: 0.25, 8: 0.15},
        attack_cycles=8, loop_cycles=2, breath=0.08, amplitude=0.85)


def ffvi_clarinet() -> tuple[bytes, int, dict]:
    """Clarinet — odd partials only, hollow and smooth."""
    return _sustained_voice(
        steady={1: 1.0, 3: 0.6, 5: 0.35, 7: 0.2, 9: 0.1, 11: 0.05},
        attack_cycles=10, loop_cycles=2, amplitude=0.85)


def ffvi_organ() -> tuple[bytes, int, dict]:
    """Pipe organ — principal with octaves and a fifth, a little wind."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.8, 3: 0.4, 4: 0.6, 6: 0.3, 8: 0.35, 12: 0.15},
        attack_cycles=3, loop_cycles=1, breath=0.03, amplitude=0.85)


def ffvi_piano() -> tuple[bytes, int, dict]:
    """Piano — a stretched partial stack, bright strike dying into the body."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.6), (3, 0.35), (4, 0.25), (5, 0.15), (6, 0.1), (7, 0.06)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph * (1.0 + 0.0004 * k * k)) * math.exp(-t * k / 1.6)
                   for k, a in partials)
        strike = 0.4 * math.sin(9.0 * ph) * math.exp(-t / 0.04)
        return body + strike
    return _decaying_voice(1.4, tone, amp_tau=0.7, tail_loop=True, amplitude=0.9)


def ffvi_music_box() -> tuple[bytes, int, dict]:
    """Music box — a tine: fundamental with inharmonic high partials, short."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return (math.sin(ph) + 0.5 * math.sin(4.2 * ph) * math.exp(-t / 0.12)
                + 0.25 * math.sin(7.6 * ph) * math.exp(-t / 0.06))
    return _decaying_voice(0.8, tone, amp_tau=0.3, tail_loop=True, amplitude=0.8)


def ffvi_timpani() -> tuple[bytes, int, dict]:
    """Timpani — a low drum with a pitch that settles, long ring, felt attack."""
    n = int(SNES_RATE * 0.9)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 70.0 + 40.0 * math.exp(-t / 0.05)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = math.sin(ph) * math.exp(-t / 0.35) + 0.3 * math.sin(2.4 * ph) * math.exp(-t / 0.12)
        v += _rng.uniform(-0.25, 0.25) * math.exp(-t / 0.015)
        out.append(v)
    return _finish_snes(_lowpass(out, 0.5), 0.95)


def ffvi_bassdrum() -> tuple[bytes, int, dict]:
    """Orchestral bass drum — deeper and longer than the kit kick, soft beater."""
    n = int(SNES_RATE * 0.5)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 40.0 + 60.0 * math.exp(-t / 0.05)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = math.sin(ph) * math.exp(-t / 0.22)
        v += _rng.uniform(-0.3, 0.3) * math.exp(-t / 0.012)
        out.append(v)
    return _finish_snes(_lowpass(out, 0.4), 0.95)


def ffvi_snare() -> tuple[bytes, int, dict]:
    """Orchestral snare — crisp, bright rattle, no gate, a touch of hall."""
    n = int(SNES_RATE * 0.3)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        tone = math.sin(2.0 * math.pi * 220.0 * t) * math.exp(-t / 0.03)
        noise = _rng.uniform(-1.0, 1.0)
        rattle = noise * math.exp(-t / 0.06)
        hall = noise * 0.25 * math.exp(-t / 0.14)
        out.append(0.4 * tone + 0.7 * rattle + hall)
    return _finish_snes(_highpass(out, 0.15), 0.9)


def ffvi_cymbal() -> tuple[bytes, int, dict]:
    """Suspended cymbal — long, washy, darker than the kit crash."""
    n = int(SNES_RATE * 1.4)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        v = _rng.uniform(-1.0, 1.0) * 0.75 + 0.25 * math.sin(2.0 * math.pi * 2300.0 * t)
        out.append(v * math.exp(-t / 0.55))
    return _finish_snes(_lowpass(_highpass(out, 0.25), 0.8), 0.65)


# Presets this pack adds to the registry: name -> (builder, kwargs, default volume)
PRESETS = {
    "ffvi_strings":   (ffvi_strings,   {},             60),
    "ffvi_contrabass": (ffvi_contrabass, {},           64),
    "ffvi_horn":      (ffvi_horn,      {},             60),
    "ffvi_trumpet":   (ffvi_trumpet,   {},             58),
    "ffvi_oboe":      (ffvi_oboe,      {},             58),
    "ffvi_clarinet":  (ffvi_clarinet,  {},             58),
    "ffvi_organ":     (ffvi_organ,     {},             56),
    "ffvi_piano":     (ffvi_piano,     {},             60),
    "ffvi_music_box": (ffvi_music_box, {},             52),
    "ffvi_timpani":   (ffvi_timpani,   {},             64),
    "ffvi_bassdrum":  (ffvi_bassdrum,  {},             64),
    "ffvi_snare":     (ffvi_snare,     {},             62),
    "ffvi_cymbal":    (ffvi_cymbal,    {},             52),
}

# Release family per sustaining voice (see samples.dsp.RELEASE)
RELEASE = {
    "ffvi_strings": "strings", "ffvi_contrabass": "strings", "ffvi_horn": "brass",
    "ffvi_trumpet": "brass", "ffvi_oboe": "flute", "ffvi_clarinet": "flute",
    "ffvi_organ": "organ", "ffvi_piano": "keys", "ffvi_music_box": "keys",
}


PACK = {
        "palette": "snes",
        "label": "FFVI orchestral",
        "voices": {
            "lead": ["ffvi_oboe", "ffvi_trumpet", "ffvi_horn", "snes_flute",
                     "ffvi_piano", "ffvi_strings", "ffvi_clarinet"],
            "alt_lead": ["ffvi_horn", "ffvi_oboe", "snes_flute", "ffvi_clarinet",
                         "snes_choir", "ffvi_trumpet"],
            "harmony": ["ffvi_strings", "ffvi_strings", "ffvi_strings", "snes_choir",
                        "ffvi_horn", "ffvi_organ"],
            "counter": ["ffvi_horn", "ffvi_horn", "ffvi_trumpet", "ffvi_clarinet", "snes_choir"],
            "arp": ["snes_harp", "snes_harp", "snes_pizz", "ffvi_music_box", "ffvi_piano"],
            "bass_heavy": ["ffvi_contrabass", "ffvi_contrabass", "snes_pluck_bass"],
            "bass_medium": ["ffvi_contrabass", "snes_pluck_bass", "snes_pizz"],
            "bass_light": ["snes_pizz", "ffvi_contrabass"],
            "drums": {"kick": "ffvi_bassdrum", "snare": "ffvi_snare", "hihat": "snes_hat",
                      "tom": "ffvi_timpani", "crash": "ffvi_cymbal",
                      "open_hihat": "snes_open_hat", "rim": "snes_rim"},
        },
        # Weighted draws for the composer's habits. A habit missing here is
        # drawn the way plain snes draws it.
        "habits": {
            "tempo": {"slow": 2, "medium": 3, "fast": 1},
            "energy": {"chill": 1, "normal": 2, "intense": 1},
            "scale_family": {"minor": 3, "major": 2, "pentatonic": 0},
            "harmony_voicing": {"full": 3, "thin": 1},
            "harmony_mode": {"ostinato": 3, "sustain": 3, "pulse": 1, "stabs": 1, "rhythmic": 0},
            "bass_weight": {"heavy": 2, "medium": 2, "light": 1},
            "bass_style": {"steady": 3, "walking": 2, "octave": 2, "driving": 1},
            "drum_density": {"sparse": 2, "normal": 2, "busy": 1},
            "drum_swing": {"off": 5, "light": 1, "heavy": 0},
            "echo": 0.85,
            "echo_wet": {"light": 1, "normal": 3, "wet": 2},
            "echo_stereo": {"bounce": 1, "centre": 2},
            "counter_line": 0.6,      # chance per chorus/bridge pattern (plain: 0.3)
            "section_rolls": True,    # timpani roll into the next section
        },
        # Channel trims by role, on top of the mix: the orchestra keeps the
        # kit's hats well back.
        "trims": {"hihat": 18, "openhat": 18},
    }
