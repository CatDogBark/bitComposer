"""Secret of Mana style pack: its voices (synthesised here) and the arrangement
habits that go with them. Registered on import by bitcomposer.packs.

Every voice is modelled on the game's own sample bank: 69 SPC snapshots were
decoded (BRR), every unique sample profiled (steady-state harmonics, centroid,
attack, decay, loop) and traced to the voices that play it (sounding pitch,
envelope, echo). Unlike FFVI there is no documented instrument table for this
game, so each recipe is named for the measured character and the role the
snapshots show, with the fan soundfont's vocabulary (strings, choir, brass,
marimba, vibraphone, fingered / electric / slap bass, hats, snares) as the
guide. Nothing from the game is copied; the shapes are re-synthesised.

The echo, from the DSP registers: on in 68 of 69 snapshots, delays spread
over 32-176 ms (96 and 176 ms the most common), feedback 0.31 on average,
echo level 0.34 of the main, both sides the same sign in 60 of 69.
"""
import math
import random
import struct
import zlib

from ..samples.dsp import (
    _rng, SAMPLE_RATE, BASE_NOTE_HZ, _pack_samples, _normalize, _lowpass, _highpass, _lowpass_sweep, _distort, _reverb_tail, SNES_RATE, SNES_PERIOD, SNES_TUNED_RATE, _BRR_FILTERS, brr_roundtrip, _peak_normalize, _finish_snes, _additive_cycle, _sustained_voice, _decaying_voice, _karplus_strong, KS_TUNED_RATE, ENSEMBLE_DRY, _ensemble_voice, _drive, RELEASE, add_release, polish_waveform, WAVEFORM_TUNED_RATE, _rms,
)


# ── Sustaining voices ──
# attack_cycles: one cycle is 3.8 ms, so 210 ms is 55 cycles.

def mana_strings() -> tuple[bytes, int, dict]:
    """Strings, in 43 of 69 banks: a long chorused sample, a 210 ms swell,
    bright, played in two or three voices at once."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.46, 3: 0.23, 4: 0.29, 5: 0.15, 6: 0.19, 7: 0.12, 8: 0.09, 9: 0.05},
        periods=160, attack_cycles=55, lowpass=0.8, amplitude=0.85)


def mana_flute() -> tuple[bytes, int, dict]:
    """Soft flute, in 44 banks, the game's most common voice: nearly pure, a
    slow 195 ms breath of an onset, quiet, echoed."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.13, 3: 0.11, 4: 0.01},
        attack_cycles=51, loop_cycles=1, breath=0.22, amplitude=0.9)


def mana_choir() -> tuple[bytes, int, dict]:
    """Choir 'ah', in 28 banks: the octave over half a fundamental, almost
    nothing above, 110 ms onset, loud, always echoed, chorused."""
    return _ensemble_voice(
        steady={1: 0.45, 2: 1.0, 3: 0.02, 4: 0.01, 5: 0.02},
        periods=150, attack_cycles=29, detune_layers=2, lowpass=0.6, amplitude=0.9)


def mana_whistle() -> tuple[bytes, int, dict]:
    """Whistle, in 21 banks, played high: fundamental with a little octave,
    quick 45 ms onset."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.23, 3: 0.05},
        attack_cycles=12, loop_cycles=1, breath=0.12, amplitude=0.9)


def mana_brass() -> tuple[bytes, int, dict]:
    """Soft brass, in 21 banks: a smooth rolloff, 110 ms onset, under the
    boss and travel themes."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.37, 3: 0.3, 4: 0.21, 5: 0.12, 6: 0.06, 7: 0.03},
        attack_cycles=29, loop_cycles=2, amplitude=0.9)


def mana_synth_brass() -> tuple[bytes, int, dict]:
    """Synth brass, in 13 banks (Danger, Meridian Dance): bright and buzzy,
    the third partial up, 45 ms onset."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.41, 3: 0.61, 4: 0.21, 5: 0.28, 6: 0.3, 7: 0.19, 8: 0.25, 9: 0.1, 10: 0.16},
        bright={1: 0.9, 2: 0.6, 3: 0.9, 4: 0.5, 5: 0.6, 6: 0.6, 7: 0.5, 8: 0.5, 9: 0.4, 10: 0.4},
        attack_cycles=12, loop_cycles=2, amplitude=0.9)


def mana_reed() -> tuple[bytes, int, dict]:
    """Reed, in 8 banks: the twelfth on top, hollow and bright, quick."""
    return _sustained_voice(
        steady={1: 0.47, 2: 0.54, 3: 1.0, 4: 0.19, 5: 0.25, 6: 0.08, 8: 0.16, 9: 0.14},
        attack_cycles=3, loop_cycles=2, amplitude=0.85)


def mana_accordion() -> tuple[bytes, int, dict]:
    """Accordion, under Dancing Animals and Distant Thunder: high drawbars
    over a quiet fundamental, a 115 ms bellows onset."""
    return _sustained_voice(
        steady={1: 0.5, 2: 1.0, 3: 0.5, 4: 0.28, 5: 0.18, 6: 0.22},
        attack_cycles=30, loop_cycles=2, breath=0.03, amplitude=0.85)


def mana_glass_pad() -> tuple[bytes, int, dict]:
    """Glass pad, under Ceremony, The Curse and The Oracle: fundamental and
    octave nearly equal and nothing else, a 90 ms swell, chorused."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.83, 3: 0.01},
        periods=140, attack_cycles=24, detune_layers=2, lowpass=0.7, amplitude=0.8)


def mana_sine_pad() -> tuple[bytes, int, dict]:
    """Sine pad: a pure wavetable with a slow envelope onset, quiet chords."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.01},
        periods=120, attack_cycles=20, detune_layers=1, lowpass=0.5, amplitude=0.8)


def mana_hollow_wave() -> tuple[bytes, int, dict]:
    """Hollow wave, in 16 banks: a one-cycle wavetable with the octave on top
    and the fifth partial, 35 ms onset."""
    return _sustained_voice(
        steady={1: 0.59, 2: 1.0, 3: 0.03, 4: 0.04, 5: 0.42},
        attack_cycles=9, loop_cycles=2, amplitude=0.85)


# ── Struck and plucked voices ──

def mana_marimba() -> tuple[bytes, int, dict]:
    """Marimba, in 16 banks (Into the Thick of It): a warm wavetable, the
    octave strong, decaying as the driver lets it."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.72), (3, 0.24), (4, 0.07), (5, 0.02)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph) * math.exp(-t * k / 4.0) for k, a in partials)
        return body + 0.3 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.003)
    return _decaying_voice(0.6, tone, amp_tau=0.22, tail_loop=True, amplitude=0.85)


def mana_vibraphone() -> tuple[bytes, int, dict]:
    """Vibraphone, in 19 banks: a pure sine with a slow decay, mid register."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return math.sin(ph) + 0.04 * math.sin(4.0 * ph) * math.exp(-t / 0.05)
    return _decaying_voice(1.0, tone, amp_tau=0.5, tail_loop=True, amplitude=0.85)


def mana_epiano() -> tuple[bytes, int, dict]:
    """Electric piano, in 6 banks, played mid: fundamental with a strong
    octave and twelfth, decaying."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.74), (3, 0.47), (4, 0.06), (6, 0.12)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        return sum(a * math.sin(k * ph) * math.exp(-t * k / 3.0) for k, a in partials)
    return _decaying_voice(0.9, tone, amp_tau=0.4, tail_loop=True, amplitude=0.85)


def mana_tubular_bell() -> tuple[bytes, int, dict]:
    """Tubular bell, under Distant Thunder and The Little Sprite: the sixth
    partial carries it over a soft fundamental, a long ring."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return (0.44 * math.sin(ph) + 0.47 * math.sin(3.0 * ph) * math.exp(-t / 0.4)
                + math.sin(6.0 * ph) * math.exp(-t / 0.5) + 0.2 * math.sin(2.0 * ph))
    return _decaying_voice(1.2, tone, amp_tau=0.6, tail_loop=True, amplitude=0.75)


def mana_bass() -> tuple[bytes, int, dict]:
    """Fingered bass, in 18 banks: the octave over the fundamental, a strong
    third, played 50-110 Hz with echo."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 0.82), (2, 1.0), (3, 0.72), (4, 0.49), (5, 0.23), (6, 0.09)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        return sum(a * math.sin(k * ph) * math.exp(-t * k / 6.0) for k, a in partials)
    return _decaying_voice(0.7, tone, amp_tau=0.5, tail_loop=True, amplitude=0.95)


def mana_bass_elec() -> tuple[bytes, int, dict]:
    """Electric bass, in 16 banks: fundamental on top, the twelfth strong,
    rounder than the fingered one."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.52), (3, 0.74), (4, 0.28), (5, 0.09), (6, 0.08)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        return sum(a * math.sin(k * ph) * math.exp(-t * k / 6.0) for k, a in partials)
    return _decaying_voice(0.7, tone, amp_tau=0.5, tail_loop=True, amplitude=0.95)


def mana_slap_bass() -> tuple[bytes, int, dict]:
    """Slap bass (Danger, In the Dead of the Night): bright, the fourth
    partial on top, a hard snap."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 0.26), (2, 0.55), (3, 0.83), (4, 1.0), (5, 0.53), (6, 0.16)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph) * math.exp(-t * k / 4.0) for k, a in partials)
        return body + 0.5 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.004)
    return _decaying_voice(0.6, tone, amp_tau=0.4, tail_loop=True, amplitude=0.95)


# ── Kit ──
# Snare: 118 ms, bright, in 23 banks. Crash: 250 ms, bright, loud. Hat: a
# 62 ms gated noise. Open hat: 312 ms, ringing. Tom: a 150 ms pitched drum.
# Castanet: a 125 ms click that is over in 15. The kick is the one piece
# the snapshots do not settle (the common low loop plays too slow to read),
# so it is a deep, round kick in the game's manner.

def mana_kick() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.22)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 48.0 + 90.0 * math.exp(-t / 0.025)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = math.sin(ph) * math.exp(-t / 0.09)
        v += _rng.uniform(-0.25, 0.25) * math.exp(-t / 0.005)
        out.append(v)
    return _finish_snes(_lowpass(out, 0.4), 0.95)


def mana_snare() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.13)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        tone = math.sin(2.0 * math.pi * 190.0 * t) * math.exp(-t / 0.025)
        out.append(0.35 * tone + _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.04))
    return _finish_snes(_highpass(out, 0.25), 0.9)


def mana_hat() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.065)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.015) for i in range(n)]
    return _finish_snes(_highpass(out, 0.5), 0.7)


def mana_open_hat() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.32)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append((_rng.uniform(-1.0, 1.0) * 0.8 + 0.3 * math.sin(2.0 * math.pi * 3300.0 * t)) * math.exp(-t / 0.1))
    return _finish_snes(_highpass(out, 0.45), 0.6)


def mana_crash() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.6)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append((_rng.uniform(-1.0, 1.0) + 0.25 * math.sin(2.0 * math.pi * 2600.0 * t)) * math.exp(-t / 0.18))
    return _finish_snes(_highpass(out, 0.45), 0.65)


def mana_tom() -> tuple[bytes, int, dict]:
    """Tom / hand drum: a settling pitch, 150 ms, a slap of noise."""
    n = int(SNES_RATE * 0.2)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 170.0 + 130.0 * math.exp(-t / 0.02)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = (math.sin(ph) + 0.25 * math.sin(2.0 * ph)) * math.exp(-t / 0.06)
        v += _rng.uniform(-0.4, 0.4) * math.exp(-t / 0.006)
        out.append(v)
    return _finish_snes(out, 0.9)


def mana_castanet() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.04)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append(math.sin(2.0 * math.pi * 2200.0 * t) * math.exp(-t / 0.006)
                   + 0.6 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.003))
    return _finish_snes(_highpass(out, 0.3), 0.8)


# Presets this pack adds to the registry: name -> (builder, kwargs, default volume)
PRESETS = {
    "mana_strings":      (mana_strings,      {}, 58),
    "mana_flute":        (mana_flute,        {}, 58),
    "mana_choir":        (mana_choir,        {}, 58),
    "mana_whistle":      (mana_whistle,      {}, 60),
    "mana_brass":        (mana_brass,        {}, 58),
    "mana_synth_brass":  (mana_synth_brass,  {}, 56),
    "mana_reed":         (mana_reed,         {}, 56),
    "mana_accordion":    (mana_accordion,    {}, 56),
    "mana_glass_pad":    (mana_glass_pad,    {}, 52),
    "mana_sine_pad":     (mana_sine_pad,     {}, 52),
    "mana_hollow_wave":  (mana_hollow_wave,  {}, 54),
    "mana_marimba":      (mana_marimba,      {}, 56),
    "mana_vibraphone":   (mana_vibraphone,   {}, 56),
    "mana_epiano":       (mana_epiano,       {}, 56),
    "mana_tubular_bell": (mana_tubular_bell, {}, 48),
    "mana_bass":         (mana_bass,         {}, 64),
    "mana_bass_elec":    (mana_bass_elec,    {}, 64),
    "mana_slap_bass":    (mana_slap_bass,    {}, 64),
    "mana_kick":         (mana_kick,         {}, 64),
    "mana_snare":        (mana_snare,        {}, 62),
    "mana_hat":          (mana_hat,          {}, 50),
    "mana_open_hat":     (mana_open_hat,     {}, 48),
    "mana_crash":        (mana_crash,        {}, 52),
    "mana_tom":          (mana_tom,          {}, 60),
    "mana_castanet":     (mana_castanet,     {}, 56),
}

# Release family per sustaining voice (see samples.dsp.RELEASE)
RELEASE = {
    "mana_strings": "strings", "mana_flute": "flute", "mana_choir": "choir",
    "mana_whistle": "flute", "mana_brass": "brass", "mana_synth_brass": "brass",
    "mana_reed": "flute", "mana_accordion": "organ", "mana_glass_pad": "pad",
    "mana_sine_pad": "pad", "mana_hollow_wave": "lead", "mana_marimba": "keys",
    "mana_vibraphone": "keys", "mana_epiano": "keys", "mana_tubular_bell": "keys",
    "mana_bass": "bass", "mana_bass_elec": "bass", "mana_slap_bass": "bass",
}


PACK = {
        "palette": "snes",
        "label": "Secret of Mana",
        # Every voice is the pack's own, built from the game's bank. Pool
        # weights follow how often the bank carries each voice: the flute is
        # in 44 banks, the strings in 43, the choir in 28, the marimba in 16.
        "voices": {
            "lead": ["mana_flute", "mana_flute", "mana_whistle", "mana_whistle", "mana_brass",
                     "mana_marimba", "mana_vibraphone", "mana_synth_brass", "mana_reed",
                     "mana_accordion", "mana_epiano"],
            "alt_lead": ["mana_whistle", "mana_flute", "mana_brass", "mana_marimba",
                         "mana_vibraphone", "mana_reed", "mana_choir"],
            "harmony": ["mana_strings", "mana_strings", "mana_strings", "mana_choir", "mana_choir",
                        "mana_glass_pad", "mana_sine_pad", "mana_hollow_wave", "mana_brass",
                        "mana_vibraphone"],
            "counter": ["mana_flute", "mana_whistle", "mana_marimba", "mana_brass", "mana_choir"],
            "arp": ["mana_marimba", "mana_marimba", "mana_vibraphone", "mana_epiano",
                    "mana_tubular_bell", "mana_hollow_wave"],
            "bass_heavy": ["mana_bass", "mana_bass_elec", "mana_slap_bass"],
            "bass_medium": ["mana_bass", "mana_bass", "mana_bass_elec", "mana_slap_bass"],
            "bass_light": ["mana_bass_elec", "mana_bass", "mana_marimba"],
            "drums": {"kick": "mana_kick", "snare": "mana_snare", "hihat": "mana_hat",
                      "tom": "mana_tom", "crash": "mana_crash",
                      "open_hihat": "mana_open_hat", "rim": "mana_castanet"},
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
            # The game's echo: on in 68 of 69 snapshots, 96 and 176 ms the
            # most common delays (one row at these tempos), feedback 0.31,
            # wet (echo at a third of the main level), both sides the same sign.
            "echo": 0.95,
            "echo_wet": {"light": 1, "normal": 2, "wet": 2},
            "echo_delay": {"slap": 2, "row": 3, "eighth": 1, "dotted": 0, "quarter": 0},
            "echo_feedback": (0.2, 0.45),
            "echo_stereo": {"bounce": 1, "centre": 3},
            "counter_line": 0.35,
            "section_rolls": False,
            "hat_stroke": 0.6,        # every second hat hit is the back stroke
        },
        # A lighter kit: the hand percussion carries the time, the kick and
        # snare sit back.
        "trims": {"kick": 28, "snare": 30, "hihat": 20, "openhat": 22},
    }
