"""Secret of Evermore style pack: its voices (synthesised here) and the arrangement
habits that go with them. Registered on import by bitcomposer.packs."""
import math
import random
import struct
import zlib

from ..samples.dsp import (
    _rng, SAMPLE_RATE, BASE_NOTE_HZ, _pack_samples, _normalize, _lowpass, _highpass, _lowpass_sweep, _distort, _reverb_tail, SNES_RATE, SNES_PERIOD, SNES_TUNED_RATE, _BRR_FILTERS, brr_roundtrip, _peak_normalize, _finish_snes, _additive_cycle, _sustained_voice, _decaying_voice, _karplus_strong, KS_TUNED_RATE, ENSEMBLE_DRY, _ensemble_voice, _drive, RELEASE, add_release, polish_waveform, WAVEFORM_TUNED_RATE, _rms,
)




# ── Secret of Evermore set ──
# Soule's palette: warm, slow and wide. Pads that swell, a breathy flute,
# tubular bells, a drone under everything, an "oo" choir, soft percussion.

def evm_pad() -> tuple[bytes, int, dict]:
    """Warm pad — rounded spectrum, slow swell, three detuned layers."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.5, 3: 0.3, 4: 0.2, 5: 0.12, 6: 0.07},
        periods=160, attack_cycles=60, detune_layers=2, lowpass=0.4, amplitude=0.85)


def evm_dark_pad() -> tuple[bytes, int, dict]:
    """Dark pad — hollow odd partials, slower still, darker."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.15, 3: 0.4, 5: 0.2, 7: 0.08},
        periods=180, attack_cycles=70, detune_layers=2, lowpass=0.32, amplitude=0.85)


def evm_drone() -> tuple[bytes, int, dict]:
    """Drone — a low, slow-beating fundamental for the bass role to hold."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.3, 3: 0.15, 4: 0.05},
        periods=200, attack_cycles=40, detune_layers=1, lowpass=0.25, amplitude=0.9)


def evm_breath_flute() -> tuple[bytes, int, dict]:
    """Breathy flute — more air than tone, soft onset."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.3, 3: 0.1, 4: 0.04},
        attack_cycles=14, loop_cycles=2, breath=0.45, lowpass=0.6, amplitude=0.85)


def evm_choir_oo() -> tuple[bytes, int, dict]:
    """Choir 'oo' — darker vowel than the 'ah' choir, slower attack."""
    formants = [(350.0, 100.0), (800.0, 120.0), (2400.0, 200.0)]
    harm = {}
    for k in range(1, 12):
        f = BASE_NOTE_HZ * k
        w = sum(math.exp(-((f - fc) / bw) ** 2) for fc, bw in formants)
        harm[k] = (0.12 + w) / k ** 0.7
    return _sustained_voice(harm, attack_cycles=40, loop_cycles=2,
                            lowpass=0.5, breath=0.03, amplitude=0.85)


def evm_tubular_bell() -> tuple[bytes, int, dict]:
    """Tubular bell — inharmonic partials, a hum that outlasts the strike."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return (math.sin(ph) + 0.6 * math.sin(2.0 * ph) * math.exp(-t / 0.9)
                + 0.5 * math.sin(2.76 * ph) * math.exp(-t / 0.5)
                + 0.3 * math.sin(5.4 * ph) * math.exp(-t / 0.2)
                + 0.5 * math.sin(0.5 * ph))
    return _decaying_voice(1.8, tone, amp_tau=1.1, tail_loop=True, amplitude=0.8)


def evm_soft_cymbal() -> tuple[bytes, int, dict]:
    """A cymbal touched with a mallet: blooms over 80 ms, dark, gone in well
    under a second. For the crash slot of a quiet kit, where a hit-and-wash
    crash takes the whole phrase."""
    n = int(SNES_RATE * 0.7)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        env = min(1.0, t / 0.08) * math.exp(-max(0.0, t - 0.08) / 0.18)
        v = _rng.uniform(-1.0, 1.0) * 0.8 + 0.2 * math.sin(2.0 * math.pi * 1900.0 * t)
        out.append(v * env)
    return _finish_snes(_lowpass(_highpass(out, 0.25), 0.5), 0.5)


def evm_frame_drum() -> tuple[bytes, int, dict]:
    """Frame drum — a deep, soft hand drum with a long body."""
    n = int(SNES_RATE * 0.6)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 60.0 + 50.0 * math.exp(-t / 0.04)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = math.sin(ph) * math.exp(-t / 0.28)
        v += _rng.uniform(-0.2, 0.2) * math.exp(-t / 0.01)
        out.append(v)
    return _finish_snes(_lowpass(out, 0.35), 0.9)


def evm_brush_snare() -> tuple[bytes, int, dict]:
    """Brushed snare — a soft swish, no crack."""
    n = int(SNES_RATE * 0.22)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        env = min(1.0, t / 0.02) * math.exp(-max(0.0, t - 0.02) / 0.07)
        out.append(_rng.uniform(-1.0, 1.0) * env)
    return _finish_snes(_lowpass(_highpass(out, 0.3), 0.5), 0.5)


def evm_click() -> tuple[bytes, int, dict]:
    """A soft wooden click for the rim slot."""
    n = int(SNES_RATE * 0.05)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append(math.sin(2.0 * math.pi * 1400.0 * t) * math.exp(-t / 0.006)
                   + _rng.uniform(-0.3, 0.3) * math.exp(-t / 0.002))
    return _finish_snes(out, 0.6)


# Presets this pack adds to the registry: name -> (builder, kwargs, default volume)
PRESETS = {
    "evm_pad":        (evm_pad,        {},             54),
    "evm_dark_pad":   (evm_dark_pad,   {},             54),
    "evm_drone":      (evm_drone,      {},             60),
    "evm_breath_flute": (evm_breath_flute, {},         60),
    "evm_choir_oo":   (evm_choir_oo,   {},             56),
    "evm_tubular_bell": (evm_tubular_bell, {},         52),
    "evm_frame_drum": (evm_frame_drum, {},             62),
    "evm_soft_cymbal": (evm_soft_cymbal, {},           48),
    "evm_brush_snare": (evm_brush_snare, {},           56),
    "evm_click":      (evm_click,      {},             50),
}

# Release family per sustaining voice (see samples.dsp.RELEASE)
RELEASE = {
    "evm_pad": "pad", "evm_dark_pad": "pad", "evm_drone": "bass",
    "evm_breath_flute": "flute", "evm_choir_oo": "choir", "evm_tubular_bell": "keys",
}


PACK = {
        "palette": "snes",
        "label": "Secret of Evermore",
        "voices": {
            "lead": ["evm_breath_flute", "evm_breath_flute", "snes_flute", "evm_choir_oo",
                     "evm_tubular_bell", "ffvi_oboe"],
            "alt_lead": ["evm_choir_oo", "snes_flute", "evm_breath_flute", "ffvi_clarinet"],
            "harmony": ["evm_pad", "evm_pad", "evm_dark_pad", "evm_dark_pad", "evm_choir_oo",
                        "snes_strings"],
            "counter": ["evm_choir_oo", "snes_flute", "evm_breath_flute"],
            "arp": ["snes_harp", "mana_kalimba", "evm_tubular_bell", "ffvi_music_box",
                    "mana_glass_pad"],
            "bass_heavy": ["evm_drone", "evm_drone", "snes_pluck_bass"],
            "bass_medium": ["evm_drone", "snes_pluck_bass", "ffvi_contrabass"],
            "bass_light": ["evm_drone", "snes_pluck_bass"],
            "drums": {"kick": "ffvi_bassdrum", "snare": "evm_brush_snare", "hihat": "mana_shaker",
                      "tom": "evm_frame_drum", "crash": "evm_soft_cymbal",
                      "open_hihat": "mana_tambourine", "rim": "evm_click"},
        },
        "habits": {
            "tempo": {"slow": 4, "medium": 1, "fast": 0},
            "intro": {"pad_hook": 3, "arp_bed": 2, "drum_pickup": 2, "riff_vamp": 1},
            "energy": {"chill": 3, "normal": 1, "intense": 0},
            "scale_family": {"minor": 4, "major": 1, "pentatonic": 1},
            "form": {"linear": 3, "standard": 1, "aaba": 1, "short": 1, "rondo": 0},
            "harmony_voicing": {"full": 2, "thin": 1},
            "harmony_mode": {"sustain": 5, "rhythmic": 1, "stabs": 0, "ostinato": 0, "pulse": 0},
            "bass_weight": {"heavy": 1, "medium": 2, "light": 2},
            "bass_style": {"drone": 3, "steady": 2, "walking": 1, "octave": 0, "driving": 0},
            "drum_density": {"sparse": 4, "normal": 1, "busy": 0},
            "drum_swing": {"off": 4, "light": 1, "heavy": 0},
            "drumless": 0.4,          # chance the whole song has no kit at all
            "arp_figures": {"sparse_pulse": 3, "quarter_up": 3, "pedal_bounce": 1, "classic_up": 1},
            "echo": 1.0,
            "echo_wet": {"light": 0, "normal": 1, "wet": 3},
            "echo_delay": {"eighth": 0, "dotted": 2, "quarter": 3},
            "echo_stereo": {"bounce": 1, "centre": 2},
            "counter_line": 0.2,
            "section_rolls": False,
            "hat_stroke": 0.6,
            "crash_chance": 0.35,     # a third of the phrase starts, never on fills
            "fill_crash": False,
        },
        "trims": {"kick": 26, "snare": 24, "hihat": 18, "openhat": 18, "tom": 30, "crash": 24},
    }
