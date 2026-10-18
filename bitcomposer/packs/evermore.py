"""Secret of Evermore style pack: its voices (synthesised here) and the arrangement
habits that go with them. Registered on import by bitcomposer.packs.

Every voice is modelled on the game's own sample bank: 72 SPC snapshots were
decoded (BRR), every unique sample profiled (steady-state harmonics, centroid,
attack, decay, loop) and traced to the voices that play it. Soule's driver
streams a small set per song, so the bank is 131 samples of which only about
thirty recur or carry an instrument; seven of those matched William Kage's
named rips by exact length (string, harp, bell, tinker, piano, bass, the
frame drum, kick and cymbal), the rest are named by measured character. The
pack keeps one unmeasured voice, the 'oo' choir, because Kage's set shows a
long vocal sample that none of these snapshots carries whole. Nothing from the
game is copied; the shapes are re-synthesised.

The echo, from the DSP registers: off in 47 of 72 snapshots; where on, 80 ms,
feedback under 0.16, a steep filter, the echo at an eighth of the main level.
The space in Evermore is in the samples (long swells, wind and drone
textures), not in the echo.
"""
import math
import random
import struct
import zlib

from ..samples.dsp import (
    _rng, SAMPLE_RATE, BASE_NOTE_HZ, _pack_samples, _normalize, _lowpass, _highpass, _lowpass_sweep, _distort, _reverb_tail, SNES_RATE, SNES_PERIOD, SNES_TUNED_RATE, _BRR_FILTERS, brr_roundtrip, _peak_normalize, _finish_snes, _additive_cycle, _sustained_voice, _decaying_voice, _karplus_strong, KS_TUNED_RATE, ENSEMBLE_DRY, _ensemble_voice, _drive, RELEASE, add_release, polish_waveform, WAVEFORM_TUNED_RATE, _rms,
)


# ── Sustaining voices ──
# attack_cycles: one cycle is 3.8 ms, so 325 ms is 85 cycles.

def evm_strings() -> tuple[bytes, int, dict]:
    """String (Kage's name), in 10 banks: a 325 ms swell into a bright
    fundamental-and-octave tone, loud, always echoed."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.64, 3: 0.08, 4: 0.03, 5: 0.01, 6: 0.02},
        periods=160, attack_cycles=85, detune_layers=2, lowpass=0.8, amplitude=0.85)


def evm_pad() -> tuple[bytes, int, dict]:
    """Warm pad, the game's most played voice (15 of the sounding voices in
    the set, as chords and as bass): fundamental and octave equal, little
    else, a 90 ms swell, always echoed."""
    return _ensemble_voice(
        steady={1: 0.81, 2: 1.0, 3: 0.03, 4: 0.02, 5: 0.04, 6: 0.07, 7: 0.04},
        periods=160, attack_cycles=24, detune_layers=2, lowpass=0.5, amplitude=0.85)


def evm_dark_pad() -> tuple[bytes, int, dict]:
    """Dark pad, under Bugmuck, the Volcano and Gothica: a dark loop with a
    strong octave, 75 ms onset, played mid, dry."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.76, 3: 0.17, 4: 0.05},
        periods=180, attack_cycles=20, detune_layers=2, lowpass=0.3, amplitude=0.85)


def evm_bell() -> tuple[bytes, int, dict]:
    """Bell (Kage's name): a pure tone that swells in over 130 ms and holds;
    a glass pad more than a struck bell."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.04, 3: 0.02},
        periods=140, attack_cycles=34, detune_layers=1, lowpass=0.6, amplitude=0.8)


def evm_breath_flute() -> tuple[bytes, int, dict]:
    """Breathy flute (Kage's wind2): nearly pure, a 65 ms onset, air on it."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.05, 3: 0.05, 4: 0.01},
        attack_cycles=17, loop_cycles=1, breath=0.4, lowpass=0.7, amplitude=0.85)


def evm_reed() -> tuple[bytes, int, dict]:
    """Reed, under Horace, Gothica and the Puppet Show: the octave over the
    fundamental, hollow, quick."""
    return _sustained_voice(
        steady={1: 0.66, 2: 1.0, 3: 0.15, 4: 0.04, 5: 0.09, 6: 0.02},
        attack_cycles=4, loop_cycles=2, breath=0.04, amplitude=0.85)


def evm_choir_oo() -> tuple[bytes, int, dict]:
    """Choir 'oo' — the one voice not measured: Kage's set carries a long
    vocal sample none of these snapshots holds whole. A dark vowel, slow."""
    formants = [(350.0, 100.0), (800.0, 120.0), (2400.0, 200.0)]
    harm = {}
    for k in range(1, 12):
        f = BASE_NOTE_HZ * k
        w = sum(math.exp(-((f - fc) / bw) ** 2) for fc, bw in formants)
        harm[k] = (0.12 + w) / k ** 0.7
    return _sustained_voice(harm, attack_cycles=40, loop_cycles=2,
                            lowpass=0.5, breath=0.03, amplitude=0.85)


def evm_drone() -> tuple[bytes, int, dict]:
    """Drone: the bank's bright textured loop played at a fiftieth of its
    speed, loud, echoed, under the Tar Pits, Thraxx and the Arena. Here a low
    tone with a slow grain of noise on it."""
    n = int(SNES_RATE * 1.0)
    w = 2.0 * math.pi * BASE_NOTE_HZ
    out = []
    for i in range(n):
        t = i / SNES_RATE
        ph = w * i / SNES_RATE
        tone = math.sin(ph) + 0.5 * math.sin(2.0 * ph) + 0.2 * math.sin(3.0 * ph)
        out.append(tone * (0.85 + 0.15 * math.sin(2.0 * math.pi * 0.7 * t)) + 0.08 * _rng.uniform(-1.0, 1.0))
    out = _lowpass(out, 0.3)
    period = SNES_PERIOD
    loop_start = n - 8 * period
    tail = out[loop_start:loop_start + period]
    out = out[:loop_start] + tail * 8
    return _finish_snes(out, 0.9, loop_start, len(out))


def evm_wind() -> tuple[bytes, int, dict]:
    """Wind: the bank's noise loop played very slow (Tar Pits, Volcano,
    Gothica, Racing Pigs); a band of noise that breathes, for the harmony
    slot as texture."""
    n = int(SNES_RATE * 1.2)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append(_rng.uniform(-1.0, 1.0) * (0.88 + 0.12 * math.sin(2.0 * math.pi * 0.8 * t)))
    out = _lowpass(_highpass(out, 0.08), 0.25)
    loop_start = int(SNES_RATE * 0.2)
    return _finish_snes(out, 0.5, loop_start, len(out))


# ── Struck and plucked voices ──

def evm_harp() -> tuple[bytes, int, dict]:
    """Harp (Kage's name), in 10 banks: fundamental with a third of octave
    and a quarter of twelfth, instant, the driver's decay, echoed."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.35), (3, 0.25), (4, 0.02)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph) * math.exp(-t * k / 5.0) for k, a in partials)
        return body + 0.2 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.003)
    return _decaying_voice(0.9, tone, amp_tau=0.45, tail_loop=True, amplitude=0.85)


def evm_tinker() -> tuple[bytes, int, dict]:
    """Tinker (Kage's name), the music box in 7 banks: a pure sine, instant,
    ringing."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return math.sin(ph) + 0.05 * math.sin(4.0 * ph) * math.exp(-t / 0.04)
    return _decaying_voice(0.9, tone, amp_tau=0.4, tail_loop=True, amplitude=0.8)


def evm_piano() -> tuple[bytes, int, dict]:
    """Piano (Kage's name), the Deserted Castle's: the octave carries it
    over a soft fundamental, a 65 ms bloom, a slow decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 0.44), (2, 1.0), (3, 0.08), (4, 0.05)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        return sum(a * math.sin(k * ph) * math.exp(-t * k / 3.0) for k, a in partials) * min(1.0, t / 0.03)
    return _decaying_voice(1.2, tone, amp_tau=0.8, tail_loop=True, amplitude=0.9)


def evm_pluck() -> tuple[bytes, int, dict]:
    """Pluck, under Storekeepers, Horace, the Castle and Queen Bluegarden: a
    pure tone that dies in 400 ms, dry."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return math.sin(ph) + 0.06 * math.sin(2.0 * ph) + 0.08 * math.sin(3.0 * ph) * math.exp(-t / 0.1)
    return _decaying_voice(0.6, tone, amp_tau=0.17, tail_loop=True, amplitude=0.85)


def evm_kalimba() -> tuple[bytes, int, dict]:
    """Kalimba ping, under the Tar Pits and Thraxx: the octave carries it,
    a little fifth partial, over in 100 ms."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return math.sin(2.0 * ph) + 0.14 * math.sin(3.0 * ph) + 0.28 * math.sin(5.0 * ph) * math.exp(-t / 0.03)
    return _decaying_voice(0.3, tone, amp_tau=0.05, tail_loop=False, amplitude=0.85)


def evm_bass() -> tuple[bytes, int, dict]:
    """Bass (Kage's bass1): dark, the octave on top with a strong third,
    25 ms onset."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 0.46), (2, 1.0), (3, 0.75), (4, 0.38), (5, 0.41), (6, 0.19)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        return sum(a * math.sin(k * ph) * math.exp(-t * k / 8.0) for k, a in partials) * min(1.0, t / 0.02)
    return _decaying_voice(0.8, tone, amp_tau=0.7, tail_loop=True, amplitude=0.95)


# ── Kit ──
# Kage's drum sfx 002 is a 146 ms soft thud (the kick), 001 a 278 ms frame
# drum with the twelfth up, 003 a 398 ms cymbal. The bank has no snare: the
# brushed swish is the pack's own stand-in. Hats are 6 ms noise bursts.

def evm_kick() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.16)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 55.0 + 70.0 * math.exp(-t / 0.03)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = (math.sin(ph) + 0.35 * math.sin(2.0 * ph)) * min(1.0, t / 0.01) * math.exp(-t / 0.05)
        v += _rng.uniform(-0.15, 0.15) * math.exp(-t / 0.008)
        out.append(v)
    return _finish_snes(_lowpass(out, 0.4), 0.95)


def evm_frame_drum() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.3)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 80.0 + 60.0 * math.exp(-t / 0.04)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = (0.5 * math.sin(ph) + 0.67 * math.sin(2.0 * ph) + math.sin(3.0 * ph) * math.exp(-t / 0.08)) * math.exp(-t / 0.12)
        v += _rng.uniform(-0.3, 0.3) * math.exp(-t / 0.008)
        out.append(v)
    return _finish_snes(_lowpass(out, 0.5), 0.9)


def evm_cymbal() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.45)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        env = min(1.0, t / 0.025) * math.exp(-max(0.0, t - 0.025) / 0.14)
        out.append((_rng.uniform(-1.0, 1.0) * 0.8 + 0.2 * math.sin(2.0 * math.pi * 2400.0 * t)) * env)
    return _finish_snes(_lowpass(_highpass(out, 0.3), 0.7), 0.55)


def evm_brush_snare() -> tuple[bytes, int, dict]:
    """Brushed snare — a soft swish, no crack; the bank has no snare."""
    n = int(SNES_RATE * 0.22)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        env = min(1.0, t / 0.02) * math.exp(-max(0.0, t - 0.02) / 0.07)
        out.append(_rng.uniform(-1.0, 1.0) * env)
    return _finish_snes(_lowpass(_highpass(out, 0.3), 0.5), 0.5)


def evm_hat() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.03)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.006) for i in range(n)]
    return _finish_snes(_highpass(out, 0.55), 0.6)


def evm_wash() -> tuple[bytes, int, dict]:
    """A short cymbal wash for the open-hat slot."""
    n = int(SNES_RATE * 0.25)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.08) for i in range(n)]
    return _finish_snes(_lowpass(_highpass(out, 0.35), 0.7), 0.5)


def evm_wood_ping() -> tuple[bytes, int, dict]:
    """A pure 110 ms ping (Thraxx, Nobilia, the Arena), for the rim slot."""
    n = int(SNES_RATE * 0.11)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append(math.sin(2.0 * math.pi * 980.0 * t) * math.exp(-t / 0.03)
                   + 0.3 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.002))
    return _finish_snes(out, 0.7)


# Presets this pack adds to the registry: name -> (builder, kwargs, default volume)
PRESETS = {
    "evm_strings":      (evm_strings,      {}, 58),
    "evm_pad":          (evm_pad,          {}, 56),
    "evm_dark_pad":     (evm_dark_pad,     {}, 56),
    "evm_bell":         (evm_bell,         {}, 54),
    "evm_breath_flute": (evm_breath_flute, {}, 58),
    "evm_reed":         (evm_reed,         {}, 56),
    "evm_choir_oo":     (evm_choir_oo,     {}, 56),
    "evm_drone":        (evm_drone,        {}, 62),
    "evm_wind":         (evm_wind,         {}, 44),
    "evm_harp":         (evm_harp,         {}, 56),
    "evm_tinker":       (evm_tinker,       {}, 52),
    "evm_piano":        (evm_piano,        {}, 58),
    "evm_pluck":        (evm_pluck,        {}, 56),
    "evm_kalimba":      (evm_kalimba,      {}, 54),
    "evm_bass":         (evm_bass,         {}, 64),
    "evm_kick":         (evm_kick,         {}, 62),
    "evm_frame_drum":   (evm_frame_drum,   {}, 60),
    "evm_cymbal":       (evm_cymbal,       {}, 50),
    "evm_brush_snare":  (evm_brush_snare,  {}, 52),
    "evm_hat":          (evm_hat,          {}, 46),
    "evm_wash":         (evm_wash,         {}, 44),
    "evm_wood_ping":    (evm_wood_ping,    {}, 54),
}

# Release family per sustaining voice (see samples.dsp.RELEASE)
RELEASE = {
    "evm_strings": "strings", "evm_pad": "pad", "evm_dark_pad": "pad", "evm_bell": "pad",
    "evm_breath_flute": "flute", "evm_reed": "flute", "evm_choir_oo": "choir",
    "evm_drone": "pad", "evm_wind": "pad", "evm_harp": "keys", "evm_tinker": "keys",
    "evm_piano": "keys", "evm_pluck": "keys", "evm_bass": "bass",
}


PACK = {
        "palette": "snes",
        "label": "Secret of Evermore",
        # Every voice is the pack's own, built from the game's bank.
        "voices": {
            "lead": ["evm_breath_flute", "evm_breath_flute", "evm_bell", "evm_tinker",
                     "evm_harp", "evm_piano", "evm_reed", "evm_strings", "evm_choir_oo"],
            "alt_lead": ["evm_bell", "evm_breath_flute", "evm_tinker", "evm_choir_oo", "evm_reed"],
            "harmony": ["evm_pad", "evm_pad", "evm_pad", "evm_strings", "evm_strings",
                        "evm_dark_pad", "evm_choir_oo", "evm_bell", "evm_wind"],
            "counter": ["evm_breath_flute", "evm_bell", "evm_reed", "evm_strings"],
            "arp": ["evm_harp", "evm_harp", "evm_tinker", "evm_pluck", "evm_kalimba",
                    "evm_wood_ping", "evm_piano"],
            "bass_heavy": ["evm_drone", "evm_drone", "evm_bass"],
            "bass_medium": ["evm_bass", "evm_drone", "evm_pluck"],
            "bass_light": ["evm_bass", "evm_pluck", "evm_harp"],
            "drums": {"kick": "evm_kick", "snare": "evm_brush_snare", "hihat": "evm_hat",
                      "tom": "evm_frame_drum", "crash": "evm_cymbal",
                      "open_hihat": "evm_wash", "rim": "evm_wood_ping"},
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
            # The game's echo: off in two thirds of the snapshots; where on,
            # 80 ms, feedback under 0.16, light. The space is in the samples.
            "echo": 0.4,
            "echo_wet": {"light": 2, "normal": 2, "wet": 0},
            "echo_delay": {"slap": 4, "row": 1, "eighth": 0, "dotted": 0, "quarter": 0},
            "echo_feedback": (0.05, 0.2),
            "echo_stereo": {"bounce": 0, "centre": 1},
            "counter_line": 0.2,
            "section_rolls": False,
            "hat_stroke": 0.6,
            "crash_chance": 0.35,     # a third of the phrase starts, never on fills
            "fill_crash": False,
        },
        "trims": {"kick": 26, "snare": 24, "hihat": 18, "openhat": 18, "tom": 30, "crash": 24},
    }
