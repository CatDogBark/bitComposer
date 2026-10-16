"""Final Fantasy VI style pack: its voices (synthesised here) and the arrangement
habits that go with them. Registered on import by bitcomposer.packs.

Every voice is modelled on the game's own sample bank: 82 SPC snapshots were
decoded (BRR), every unique sample profiled (steady-state harmonics, centroid,
attack, decay, loop) and traced to the voices that play it (sounding pitch,
envelope, echo), so each recipe below carries the measured profile it targets.
Nothing from the game is copied; the shapes are re-synthesised. The echo too:
every snapshot runs 80 ms of delay with feedback 0.64, flat filter, both sides
the same sign, strings and leads sent, bass and kit dry.
"""
import math
import random
import struct
import zlib

from ..samples.dsp import (
    _rng, SAMPLE_RATE, BASE_NOTE_HZ, _pack_samples, _normalize, _lowpass, _highpass, _lowpass_sweep, _distort, _reverb_tail, SNES_RATE, SNES_PERIOD, SNES_TUNED_RATE, _BRR_FILTERS, brr_roundtrip, _peak_normalize, _finish_snes, _additive_cycle, _sustained_voice, _decaying_voice, _karplus_strong, KS_TUNED_RATE, ENSEMBLE_DRY, _ensemble_voice, _drive, RELEASE, add_release, polish_waveform, WAVEFORM_TUNED_RATE, _rms,
)


# ── Sustaining voices ──
# attack_cycles: one cycle is 3.8 ms, so 180 ms is 47 cycles.

def ffvi_strings() -> tuple[bytes, int, dict]:
    """String section — the bank's long chorused sample: fundamental, a strong
    fourth partial, bright upper partials, a 180 ms swell."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.42, 3: 0.16, 4: 0.40, 5: 0.11, 6: 0.16, 7: 0.08, 8: 0.14, 9: 0.05, 10: 0.03},
        periods=160, attack_cycles=47, lowpass=0.8, amplitude=0.85)


def ffvi_string_pad() -> tuple[bytes, int, dict]:
    """Slow string pad — the octave over a quiet fundamental, 110 ms swell;
    under Locke, Edgar and Terra."""
    return _ensemble_voice(
        steady={1: 0.5, 2: 1.0, 3: 0.38, 4: 0.02, 5: 0.05, 6: 0.07},
        periods=140, attack_cycles=29, detune_layers=2, lowpass=0.5, amplitude=0.85)


def ffvi_soft_pad() -> tuple[bytes, int, dict]:
    """Soft pad — near-sine chords under the Prelude and the Aria, quick."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.16, 3: 0.11, 4: 0.02},
        periods=120, attack_cycles=4, detune_layers=2, lowpass=0.6, amplitude=0.85)


def ffvi_choir() -> tuple[bytes, int, dict]:
    """Choir 'ah' — the Opening and Dancing Mad choir: octave over the
    fundamental, bright even partials, 40 ms onset."""
    return _ensemble_voice(
        steady={1: 0.48, 2: 1.0, 3: 0.32, 4: 0.27, 5: 0.02, 6: 0.38, 7: 0.01, 8: 0.36},
        periods=140, attack_cycles=11, detune_layers=2, lowpass=0.7, amplitude=0.85)


def ffvi_brass() -> tuple[bytes, int, dict]:
    """Brass section — the Battle and Fanfare chords: a full stack peaking on
    the third partial, bright onset."""
    return _sustained_voice(
        steady={1: 0.37, 2: 0.86, 3: 1.0, 4: 0.77, 5: 0.67, 6: 0.59, 7: 0.5, 8: 0.37, 9: 0.23, 10: 0.18},
        bright={1: 0.3, 2: 0.9, 3: 1.0, 4: 0.9, 5: 0.8, 6: 0.7, 7: 0.6, 8: 0.5, 9: 0.4, 10: 0.3},
        attack_cycles=10, loop_cycles=2, amplitude=0.9)


def ffvi_trumpet() -> tuple[bytes, int, dict]:
    """Trumpet — the Battle lead: fundamental and octave equal, the fourth
    partial strong, fast onset."""
    return _sustained_voice(
        steady={1: 1.0, 2: 1.0, 3: 0.1, 4: 0.6, 5: 0.3, 6: 0.1, 7: 0.08, 8: 0.06},
        bright={1: 0.7, 2: 1.0, 3: 0.6, 4: 0.9, 5: 0.7, 6: 0.5, 7: 0.4, 8: 0.3},
        attack_cycles=4, loop_cycles=2, amplitude=0.9)


def ffvi_horn() -> tuple[bytes, int, dict]:
    """French horn — the Locke and Returners lead: round and dark, a 140 ms
    onset, always sent to the echo."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.56, 3: 0.23, 4: 0.09, 5: 0.04},
        bright={1: 1.0, 2: 0.7, 3: 0.4, 4: 0.2, 5: 0.1},
        attack_cycles=37, loop_cycles=2, lowpass=0.6, amplitude=0.9)


def ffvi_oboe() -> tuple[bytes, int, dict]:
    """Oboe / reed — the octave over the fundamental, a little fifth partial;
    the Wild West harmonica is the same reed."""
    return _sustained_voice(
        steady={1: 0.5, 2: 1.0, 3: 0.27, 4: 0.04, 5: 0.17, 6: 0.09, 7: 0.04},
        attack_cycles=8, loop_cycles=2, breath=0.05, amplitude=0.85)


def ffvi_clarinet() -> tuple[bytes, int, dict]:
    """Clarinet — odd partials only, the Celes lead."""
    return _sustained_voice(
        steady={1: 1.0, 3: 0.66, 5: 0.46, 7: 0.1, 9: 0.04},
        attack_cycles=3, loop_cycles=2, amplitude=0.85)


def ffvi_flute() -> tuple[bytes, int, dict]:
    """Flute — the Cyan shakuhachi: a near-pure tone with breath on it."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.03, 3: 0.03, 4: 0.03},
        attack_cycles=12, loop_cycles=1, breath=0.2, amplitude=0.9)


def ffvi_pan_flute() -> tuple[bytes, int, dict]:
    """Pan flute — Terra's lead: pure with a touch of third partial, a long
    200 ms breathy onset."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.04, 3: 0.17, 4: 0.02, 5: 0.06},
        attack_cycles=54, loop_cycles=1, breath=0.3, amplitude=0.9)


def ffvi_organ() -> tuple[bytes, int, dict]:
    """Pipe organ — Dancing Mad's: a flute stop, fundamental and octave only."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.42, 6: 0.04},
        attack_cycles=7, loop_cycles=1, breath=0.02, amplitude=0.85)


def ffvi_contrabass() -> tuple[bytes, int, dict]:
    """Bowed double basses — the octave over the fundamental, 90 ms onset."""
    return _ensemble_voice(
        steady={1: 0.65, 2: 1.0, 3: 0.74, 4: 0.11, 5: 0.35, 6: 0.21},
        periods=120, attack_cycles=24, detune_layers=1, lowpass=0.35, amplitude=0.9)


# ── Struck and plucked voices ──

def ffvi_bass() -> tuple[bytes, int, dict]:
    """Fingered bass — the bank's looped bass: fundamental and octave equal,
    instant onset, the driver's slow decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.97), (3, 0.42), (4, 0.34), (5, 0.05), (6, 0.15)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        return sum(a * math.sin(k * ph) * math.exp(-t * k / 6.0) for k, a in partials)
    return _decaying_voice(0.7, tone, amp_tau=0.5, tail_loop=True, amplitude=0.95)


def ffvi_piano() -> tuple[bytes, int, dict]:
    """Piano — Spinach Rag's: a dull body (fundamental, a third of octave),
    a short bright strike, a slow decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.32), (3, 0.04)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph) * math.exp(-t * k / 4.0) for k, a in partials)
        strike = 0.35 * (math.sin(4.0 * ph) + 0.5 * math.sin(6.0 * ph)) * math.exp(-t / 0.03)
        return body + strike
    return _decaying_voice(1.2, tone, amp_tau=0.8, tail_loop=True, amplitude=0.9)


def ffvi_harp() -> tuple[bytes, int, dict]:
    """Harp — the Prelude's arpeggio voice: a soft bright wavetable (octave
    and twelfth under the fundamental) with the driver's half-second decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.42), (3, 0.26), (4, 0.09), (5, 0.01)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        return sum(a * math.sin(k * ph) * math.exp(-t * k / 7.0) for k, a in partials)
    return _decaying_voice(0.9, tone, amp_tau=0.45, tail_loop=True, amplitude=0.85)


def ffvi_pizz() -> tuple[bytes, int, dict]:
    """Pizzicato — the plucked string of Mt. Koltz and the Wild West: bright
    attack, fundamental and octave, gone in a third of a second."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.68), (3, 0.08), (4, 0.06), (5, 0.06)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph) * math.exp(-t * k / 0.5) for k, a in partials)
        return body + 0.5 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.004)
    return _decaying_voice(0.35, tone, amp_tau=0.09, tail_loop=False, amplitude=0.9)


def ffvi_music_box() -> tuple[bytes, int, dict]:
    """Music box — the bank's bell ping: a pure tone with a quick decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return math.sin(ph) + 0.04 * math.sin(3.0 * ph) * math.exp(-t / 0.05)
    return _decaying_voice(0.5, tone, amp_tau=0.15, tail_loop=True, amplitude=0.8)


# ── Kit ──
# Measured: bass drum a 68 ms thud; snare 125 ms of bright rattle; hat 40 ms;
# ride wash 240 ms; crash 270 ms; tom 250 ms with a strong octave; timpani
# played at about a quarter speed: 130 Hz, 700 ms, 430 ms to silence.

def ffvi_timpani() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.8)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 130.0 + 60.0 * math.exp(-t / 0.03)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = math.sin(ph) * math.exp(-t / 0.3) + 0.35 * math.sin(2.1 * ph) * math.exp(-t / 0.15)
        v += _rng.uniform(-0.4, 0.4) * math.exp(-t / 0.02)
        out.append(v)
    return _finish_snes(_lowpass(out, 0.6), 0.95)


def ffvi_bassdrum() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.12)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 55.0 + 80.0 * math.exp(-t / 0.02)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = (math.sin(ph) + 0.72 * math.sin(2.0 * ph)) * math.exp(-t / 0.03)
        v += _rng.uniform(-0.3, 0.3) * math.exp(-t / 0.006)
        out.append(v)
    return _finish_snes(_lowpass(out, 0.5), 0.95)


def ffvi_snare() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.14)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        tone = math.sin(2.0 * math.pi * 200.0 * t) * math.exp(-t / 0.02)
        out.append(0.3 * tone + _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.045))
    return _finish_snes(_highpass(out, 0.3), 0.9)


def ffvi_cymbal() -> tuple[bytes, int, dict]:
    """Crash — bright and short, as the bank's is."""
    n = int(SNES_RATE * 0.35)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.1) for i in range(n)]
    return _finish_snes(_highpass(out, 0.5), 0.7)


def ffvi_hat() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.045)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.012) for i in range(n)]
    return _finish_snes(_highpass(out, 0.6), 0.7)


def ffvi_open_hat() -> tuple[bytes, int, dict]:
    """Ride wash — the bank's looped cymbal with its release."""
    n = int(SNES_RATE * 0.3)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append((_rng.uniform(-1.0, 1.0) + 0.2 * math.sin(2.0 * math.pi * 3000.0 * t)) * math.exp(-t / 0.09))
    return _finish_snes(_highpass(out, 0.5), 0.6)


def ffvi_tom() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.3)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 150.0 + 120.0 * math.exp(-t / 0.04)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = math.sin(ph) * math.exp(-t / 0.1) + 0.9 * math.sin(2.0 * ph) * math.exp(-t / 0.06)
        v += _rng.uniform(-0.4, 0.4) * math.exp(-t / 0.01)
        out.append(v)
    return _finish_snes(out, 0.9)


def ffvi_rim() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.03)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append(_rng.uniform(-1.0, 1.0) * math.exp(-t / 0.004)
                   + 0.5 * math.sin(2.0 * math.pi * 1200.0 * t) * math.exp(-t / 0.008))
    return _finish_snes(_highpass(out, 0.5), 0.8)


# Presets this pack adds to the registry: name -> (builder, kwargs, default volume)
PRESETS = {
    "ffvi_strings":    (ffvi_strings,    {}, 60),
    "ffvi_string_pad": (ffvi_string_pad, {}, 58),
    "ffvi_soft_pad":   (ffvi_soft_pad,   {}, 56),
    "ffvi_choir":      (ffvi_choir,      {}, 58),
    "ffvi_brass":      (ffvi_brass,      {}, 58),
    "ffvi_trumpet":    (ffvi_trumpet,    {}, 58),
    "ffvi_horn":       (ffvi_horn,       {}, 60),
    "ffvi_oboe":       (ffvi_oboe,       {}, 58),
    "ffvi_clarinet":   (ffvi_clarinet,   {}, 58),
    "ffvi_flute":      (ffvi_flute,      {}, 58),
    "ffvi_pan_flute":  (ffvi_pan_flute,  {}, 58),
    "ffvi_organ":      (ffvi_organ,      {}, 56),
    "ffvi_contrabass": (ffvi_contrabass, {}, 64),
    "ffvi_bass":       (ffvi_bass,       {}, 64),
    "ffvi_piano":      (ffvi_piano,      {}, 60),
    "ffvi_harp":       (ffvi_harp,       {}, 56),
    "ffvi_pizz":       (ffvi_pizz,       {}, 58),
    "ffvi_music_box":  (ffvi_music_box,  {}, 52),
    "ffvi_timpani":    (ffvi_timpani,    {}, 64),
    "ffvi_bassdrum":   (ffvi_bassdrum,   {}, 64),
    "ffvi_snare":      (ffvi_snare,      {}, 62),
    "ffvi_cymbal":     (ffvi_cymbal,     {}, 52),
    "ffvi_hat":        (ffvi_hat,        {}, 50),
    "ffvi_open_hat":   (ffvi_open_hat,   {}, 48),
    "ffvi_tom":        (ffvi_tom,        {}, 62),
    "ffvi_rim":        (ffvi_rim,        {}, 56),
}

# Release family per sustaining voice (see samples.dsp.RELEASE)
RELEASE = {
    "ffvi_strings": "strings", "ffvi_string_pad": "strings", "ffvi_soft_pad": "pad",
    "ffvi_contrabass": "strings", "ffvi_choir": "choir", "ffvi_brass": "brass",
    "ffvi_horn": "brass", "ffvi_trumpet": "brass", "ffvi_oboe": "flute",
    "ffvi_clarinet": "flute", "ffvi_flute": "flute", "ffvi_pan_flute": "flute",
    "ffvi_organ": "organ", "ffvi_piano": "keys", "ffvi_harp": "keys",
    "ffvi_music_box": "keys", "ffvi_bass": "bass",
}


PACK = {
        "palette": "snes",
        "label": "FFVI orchestral",
        # Every voice is the pack's own, built from the game's bank.
        "voices": {
            "lead": ["ffvi_trumpet", "ffvi_horn", "ffvi_oboe", "ffvi_flute", "ffvi_pan_flute",
                     "ffvi_clarinet", "ffvi_piano", "ffvi_strings"],
            "alt_lead": ["ffvi_horn", "ffvi_flute", "ffvi_clarinet", "ffvi_choir",
                         "ffvi_trumpet", "ffvi_pan_flute"],
            "harmony": ["ffvi_strings", "ffvi_strings", "ffvi_strings", "ffvi_string_pad",
                        "ffvi_choir", "ffvi_brass", "ffvi_organ", "ffvi_soft_pad"],
            "counter": ["ffvi_horn", "ffvi_horn", "ffvi_trumpet", "ffvi_clarinet", "ffvi_choir",
                        "ffvi_flute"],
            "arp": ["ffvi_harp", "ffvi_harp", "ffvi_pizz", "ffvi_music_box", "ffvi_piano"],
            "bass_heavy": ["ffvi_bass", "ffvi_bass", "ffvi_contrabass"],
            "bass_medium": ["ffvi_bass", "ffvi_contrabass", "ffvi_pizz"],
            "bass_light": ["ffvi_pizz", "ffvi_bass"],
            "drums": {"kick": "ffvi_bassdrum", "snare": "ffvi_snare", "hihat": "ffvi_hat",
                      "tom": "ffvi_timpani", "crash": "ffvi_cymbal",
                      "open_hihat": "ffvi_open_hat", "rim": "ffvi_rim"},
        },
        # Weighted draws for the composer's habits. A habit missing here is
        # drawn the way plain snes draws it.
        "habits": {
            "tempo": {"slow": 2, "medium": 3, "fast": 1},
            "intro": {"pad_hook": 4, "arp_bed": 3, "riff_vamp": 1, "drum_pickup": 1},
            "energy": {"chill": 1, "normal": 2, "intense": 1},
            "scale_family": {"minor": 3, "major": 2, "pentatonic": 0},
            "harmony_voicing": {"full": 3, "thin": 1},
            "harmony_mode": {"ostinato": 3, "sustain": 3, "pulse": 1, "stabs": 1, "rhythmic": 0},
            "bass_weight": {"heavy": 2, "medium": 2, "light": 1},
            "bass_style": {"steady": 3, "walking": 2, "octave": 2, "driving": 1},
            "drum_density": {"sparse": 2, "normal": 2, "busy": 1},
            "drum_swing": {"off": 5, "light": 1, "heavy": 0},
            # The game's echo: on in every snapshot, 80 ms (the slap, half a
            # row at these tempos), feedback 0.64, both sides the same sign.
            "echo": 1.0,
            "echo_wet": {"light": 0, "normal": 2, "wet": 3},
            "echo_delay": {"slap": 3, "eighth": 2, "dotted": 1, "quarter": 0},
            "echo_feedback": (0.55, 0.7),
            "echo_stereo": {"bounce": 0, "centre": 1},
            "counter_line": 0.6,      # chance per chorus/bridge pattern (plain: 0.3)
            "section_rolls": True,    # timpani roll into the next section
        },
        # Channel trims by role, on top of the mix: the orchestra keeps the
        # kit's hats well back.
        "trims": {"hihat": 18, "openhat": 18},
    }
