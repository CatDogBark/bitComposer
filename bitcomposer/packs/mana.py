"""Secret of Mana style pack: its voices (synthesised here) and the arrangement
habits that go with them. Registered on import by bitcomposer.packs."""
import math
import random
import struct
import zlib

from ..samples.dsp import (
    _rng, SAMPLE_RATE, BASE_NOTE_HZ, _pack_samples, _normalize, _lowpass, _highpass, _lowpass_sweep, _distort, _reverb_tail, SNES_RATE, SNES_PERIOD, SNES_TUNED_RATE, _BRR_FILTERS, brr_roundtrip, _peak_normalize, _finish_snes, _additive_cycle, _sustained_voice, _decaying_voice, _karplus_strong, KS_TUNED_RATE, ENSEMBLE_DRY, _ensemble_voice, _drive, RELEASE, add_release, polish_waveform, WAVEFORM_TUNED_RATE, _rms,
)




# ── Secret of Mana set ──
# Kikuta's palette: bright mallets and air. Celesta, kalimba, steel drum,
# wind chimes, a whistle and a pan flute, a glassy pad, and hand percussion.

def mana_celesta() -> tuple[bytes, int, dict]:
    """Celesta — a bright bell-bar: fundamental, a strong fourth-ish partial, quick."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return (math.sin(ph) + 0.45 * math.sin(4.0 * ph) * math.exp(-t / 0.18)
                + 0.2 * math.sin(6.8 * ph) * math.exp(-t / 0.07))
    return _decaying_voice(0.9, tone, amp_tau=0.4, tail_loop=True, amplitude=0.85)


def mana_kalimba() -> tuple[bytes, int, dict]:
    """Kalimba — a plucked tine: near-sine with a fast metallic click on top."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return math.sin(ph) + 0.35 * math.sin(6.2 * ph) * math.exp(-t / 0.03) + 0.15 * math.sin(2.0 * ph) * math.exp(-t / 0.15)
    return _decaying_voice(0.6, tone, amp_tau=0.22, tail_loop=True, amplitude=0.85)


def mana_steel_drum() -> tuple[bytes, int, dict]:
    """Steel pan — fundamental with a strong octave and a slightly detuned twelfth
    that wobbles as it rings."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return (math.sin(ph) + 0.7 * math.sin(2.0 * ph) * math.exp(-t / 0.35)
                + 0.3 * math.sin(3.02 * ph) * math.exp(-t / 0.2)
                + 0.15 * math.sin(4.0 * ph) * math.exp(-t / 0.1))
    return _decaying_voice(1.0, tone, amp_tau=0.45, tail_loop=True, amplitude=0.85)


def mana_chimes() -> tuple[bytes, int, dict]:
    """Wind chimes — a high inharmonic cluster with a long clean ring; an arp
    voice, not a lead."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return (math.sin(2.0 * ph) + 0.6 * math.sin(4.8 * ph) * math.exp(-t / 0.5)
                + 0.4 * math.sin(7.8 * ph) * math.exp(-t / 0.3))
    return _decaying_voice(1.2, tone, amp_tau=0.6, tail_loop=True, amplitude=0.7)


def mana_whistle() -> tuple[bytes, int, dict]:
    """Whistle — purer than the flute, a little breath, quick to speak."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.25, 3: 0.08, 4: 0.03},
        attack_cycles=4, loop_cycles=1, breath=0.15, amplitude=0.9)


def mana_panflute() -> tuple[bytes, int, dict]:
    """Pan flute — breathy, hollow, a slower chiff than the flute."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.5, 3: 0.3, 4: 0.14, 5: 0.07},
        attack_cycles=10, loop_cycles=2, breath=0.35, lowpass=0.7, amplitude=0.85)


def mana_glass_pad() -> tuple[bytes, int, dict]:
    """Glass pad — hollow, octaves and a twelfth, slow swell, lightly chorused."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.4, 3: 0.15, 4: 0.3, 6: 0.1, 8: 0.15},
        periods=140, attack_cycles=30, detune_layers=1, lowpass=0.6, amplitude=0.8)


def mana_conga() -> tuple[bytes, int, dict]:
    """Conga — a hand drum: a settling pitch, short, a slap of noise."""
    n = int(SNES_RATE * 0.3)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 190.0 + 120.0 * math.exp(-t / 0.02)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = math.sin(ph) * math.exp(-t / 0.09)
        v += _rng.uniform(-0.4, 0.4) * math.exp(-t / 0.006)
        out.append(v)
    return _finish_snes(out, 0.9)


def mana_shaker() -> tuple[bytes, int, dict]:
    """Shaker — one stroke: band-limited noise (a "shh" between about 2 and
    6 kHz, not a full-band burst), a 12 ms swell of grains and a tail that
    fades over the rest. The first version was white noise with a symmetric
    envelope and read as a kit piece; a shaker is a texture under the kit."""
    n = int(SNES_RATE * 0.11)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        env = min(1.0, t / 0.012) * math.exp(-max(0.0, t - 0.012) / 0.035)
        out.append(_rng.uniform(-1.0, 1.0) * env)
    out = _lowpass(_highpass(out, 0.35), 0.45)
    return _finish_snes(out, 0.3)


def mana_tambourine() -> tuple[bytes, int, dict]:
    """Tambourine — jingles: bright noise with a ringing metallic partial."""
    n = int(SNES_RATE * 0.25)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        v = _rng.uniform(-1.0, 1.0) * 0.7 * math.exp(-t / 0.08)
        v += 0.3 * math.sin(2.0 * math.pi * 3400.0 * t) * math.exp(-t / 0.12)
        out.append(v)
    return _finish_snes(_highpass(out, 0.4), 0.6)


def mana_woodblock() -> tuple[bytes, int, dict]:
    """Woodblock — a dry tick with one short pitched resonance."""
    n = int(SNES_RATE * 0.08)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        v = math.sin(2.0 * math.pi * 900.0 * t) * math.exp(-t / 0.012)
        v += _rng.uniform(-0.5, 0.5) * math.exp(-t / 0.003)
        out.append(v)
    return _finish_snes(out, 0.8)


# Presets this pack adds to the registry: name -> (builder, kwargs, default volume)
PRESETS = {
    "mana_celesta":   (mana_celesta,   {},             56),
    "mana_kalimba":   (mana_kalimba,   {},             56),
    "mana_steel_drum": (mana_steel_drum, {},           56),
    "mana_chimes":    (mana_chimes,    {},             48),
    "mana_whistle":   (mana_whistle,   {},             60),
    "mana_panflute":  (mana_panflute,  {},             60),
    "mana_glass_pad": (mana_glass_pad, {},             52),
    "mana_conga":     (mana_conga,     {},             60),
    "mana_shaker":    (mana_shaker,    {},             54),
    "mana_tambourine": (mana_tambourine, {},           50),
    "mana_woodblock": (mana_woodblock, {},             56),
}

# Release family per sustaining voice (see samples.dsp.RELEASE)
RELEASE = {
    "mana_celesta": "keys", "mana_kalimba": "keys", "mana_steel_drum": "keys",
    "mana_chimes": "keys", "mana_whistle": "flute", "mana_panflute": "flute",
    "mana_glass_pad": "pad",
}


PACK = {
        "palette": "snes",
        "label": "Secret of Mana",
        "voices": {
            "lead": ["mana_whistle", "mana_panflute", "mana_celesta", "mana_steel_drum",
                     "snes_flute", "mana_kalimba", "snes_bell"],
            "alt_lead": ["mana_panflute", "mana_whistle", "mana_celesta", "snes_flute",
                         "mana_steel_drum", "snes_epiano"],
            "harmony": ["mana_glass_pad", "mana_glass_pad", "snes_choir", "snes_epiano"],
            "counter": ["mana_celesta", "mana_kalimba", "snes_flute", "mana_steel_drum"],
            "arp": ["mana_kalimba", "mana_celesta", "mana_chimes", "snes_marimba",
                    "mana_steel_drum", "snes_bell"],
            "bass_heavy": ["snes_slap_bass", "snes_pluck_bass", "snes_synth_bass"],
            "bass_medium": ["snes_slap_bass", "snes_slap_bass", "snes_pluck_bass"],
            "bass_light": ["snes_slap_bass", "snes_pizz", "snes_marimba"],
            "drums": {"kick": "snes_kick", "snare": "snes_snare", "hihat": "mana_shaker",
                      "tom": "mana_conga", "crash": "snes_crash",
                      "open_hihat": "mana_tambourine", "rim": "mana_woodblock"},
        },
        "habits": {
            "tempo": {"slow": 1, "medium": 3, "fast": 2},
            "intro": {"arp_bed": 3, "pad_hook": 3, "drum_pickup": 1, "riff_vamp": 1},
            "energy": {"chill": 1, "normal": 3, "intense": 1},
            "scale_family": {"minor": 1, "major": 3, "pentatonic": 2},
            "harmony_voicing": {"full": 1, "thin": 2},
            "harmony_mode": {"pulse": 2, "rhythmic": 2, "stabs": 2, "sustain": 1, "ostinato": 0},
            "bass_weight": {"heavy": 1, "medium": 2, "light": 2},
            "bass_style": {"steady": 1, "walking": 2, "octave": 3, "driving": 1},
            "drum_density": {"sparse": 1, "normal": 3, "busy": 2},
            "drum_swing": {"off": 1, "light": 3, "heavy": 1},
            "arp_figures": {"classic_up": 3, "up_down": 3, "cascade": 2, "sync_push": 2,
                            "run16": 1, "quarter_up": 1, "broken_octave": 1},
            "echo": 0.8,
            "echo_wet": {"light": 1, "normal": 3, "wet": 1},
            "echo_stereo": {"bounce": 2, "centre": 1},
            "counter_line": 0.35,
            "section_rolls": False,
            "hat_stroke": 0.6,        # shaker: every second hit is the back stroke
        },
        # A lighter kit: the hand percussion carries the time, the kick and
        # snare sit back.
        "trims": {"kick": 28, "snare": 30, "hihat": 20, "openhat": 22},
    }
