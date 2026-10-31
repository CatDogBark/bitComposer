"""bitComposer's own sound set: the voices the writer plays on when no game of
yours is chosen (phase 6, 2.0rc2). Generic instruments, every one
synthesised here from a description (an additive spectrum, an envelope, a
strike), modelled on no game's bank and copied from nothing: a string
section, pads, a choir, an organ, brass, a horn, a reed, flutes, synth leads,
a piano and an electric piano, bells, plucks, a harp, marimba and kalimba,
six basses, and a kit.

The set is wide on purpose. The writer fits a voice to each part by the
part's register and its fastest bar (packs.profile gives every voice its
range, its speed and its shortest note), and the shipped vocabulary asks for
melodies anywhere from MIDI 40 to 92, counters 48 to 84, accompaniment 40
to 80 at two to twelve notes a second, basses 28 to 56: a pool with one
voice for each corner of that leaves a part on the wrong instrument. Each
pool here holds something slow and something quick in every register the
vocabulary reaches.

The four styled sets (FFVI, Mana, Evermore, Mega Man X) are Classic's and are
not changed by this one.
"""
import math

from ..samples.dsp import (
    _rng, BASE_NOTE_HZ, _lowpass, _highpass, SNES_RATE, _finish_snes, _sustained_voice, _decaying_voice, _ensemble_voice,
)


def _struck(partials, seconds: float, tau: float, strike: float = 0.0, strike_tau: float = 0.003, k_decay: float = 4.0,
            amplitude: float = 0.9, ring=None):
    """A struck or plucked voice: `partials` [(k, amplitude)] with the upper ones dying faster (k_decay), a noise strike
    of `strike` over strike_tau, an optional ring(ph, t) added, the whole under an exponential of `tau`."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        v = sum(a * math.sin(k * ph) * math.exp(-t * k / k_decay) for k, a in partials)
        if strike:
            v += strike * _rng.uniform(-1.0, 1.0) * math.exp(-t / strike_tau)
        if ring:
            v += ring(ph, t)
        return v
    return _decaying_voice(seconds, tone, amp_tau=tau, tail_loop=True, amplitude=amplitude)


# ── Leads ──

def bit_square():
    """A hollow square: odd partials, a quick attack."""
    return _sustained_voice({1: 1.0, 3: 0.33, 5: 0.2, 7: 0.14, 9: 0.11, 11: 0.09}, attack_cycles=2, lowpass=0.7)


def bit_pulse():
    """A narrow pulse: every partial, the evens softer, a nasal edge."""
    return _sustained_voice({1: 1.0, 2: 0.55, 3: 0.3, 4: 0.45, 5: 0.2, 6: 0.12, 7: 0.25, 8: 0.1, 9: 0.12}, attack_cycles=2, lowpass=0.75)


def bit_saw_lead():
    """A filtered saw: every partial at 1/k, a bright first few cycles."""
    return _sustained_voice({k: 1.0 / k for k in range(1, 11)}, bright={k: 1.0 / math.sqrt(k) for k in range(1, 13)},
                            attack_cycles=3, lowpass=0.6)


def bit_sine_flute():
    """A soft flute: the fundamental with a little octave and breath."""
    return _sustained_voice({1: 1.0, 2: 0.15, 3: 0.05}, attack_cycles=8, breath=0.15, lowpass=0.5)


def bit_ocarina():
    """An ocarina: nearly a sine, a slow bloom."""
    return _sustained_voice({1: 1.0, 2: 0.08, 3: 0.02}, attack_cycles=12, lowpass=0.4, amplitude=0.85)


def bit_brass():
    """A bright brass: the second and third partials strong, a bite that settles."""
    return _sustained_voice({1: 0.9, 2: 1.0, 3: 0.8, 4: 0.6, 5: 0.45, 6: 0.35, 7: 0.25, 8: 0.2},
                            bright={1: 0.6, 2: 1.0, 3: 1.0, 4: 0.9, 5: 0.8, 6: 0.7, 7: 0.6, 8: 0.5, 9: 0.4},
                            attack_cycles=12, lowpass=0.8)


def bit_horn():
    """A horn: dark, round, a slow 75 ms swell."""
    return _sustained_voice({1: 1.0, 2: 0.5, 3: 0.3, 4: 0.15, 5: 0.1, 6: 0.05}, attack_cycles=20, lowpass=0.5)


def bit_reed():
    """A reed (an oboe's cousin): the third and fifth partials over a thin fundamental."""
    return _sustained_voice({1: 0.6, 2: 0.3, 3: 1.0, 4: 0.4, 5: 0.6, 6: 0.2, 7: 0.3, 8: 0.1}, attack_cycles=5, lowpass=0.7)


def bit_synth_voice():
    """A vowel-like synth: a formant around the third partial, two detuned layers."""
    return _ensemble_voice({1: 1.0, 2: 0.3, 3: 0.55, 4: 0.2, 5: 0.1, 6: 0.05}, periods=140, attack_cycles=24, lowpass=0.6)


def bit_violin():
    """A solo violin: a full spectrum, ensemble shimmer, a 110 ms bow."""
    return _ensemble_voice({1: 1.0, 2: 0.6, 3: 0.45, 4: 0.35, 5: 0.3, 6: 0.2, 7: 0.15, 8: 0.1}, periods=160, attack_cycles=30, lowpass=0.8)


def bit_cello():
    """A cello: darker than the violin, a 150 ms bow."""
    return _ensemble_voice({1: 1.0, 2: 0.7, 3: 0.5, 4: 0.3, 5: 0.2, 6: 0.15}, periods=160, attack_cycles=40, lowpass=0.6)


# ── Struck and plucked ──

def bit_piano():
    """A piano: a bright strike over a warm body."""
    return _struck([(1, 1.0), (2, 0.45), (3, 0.2), (4, 0.1)], 1.2, 0.8, k_decay=4.0,
                   ring=lambda ph, t: 0.3 * (math.sin(4.0 * ph) + 0.5 * math.sin(6.0 * ph)) * math.exp(-t / 0.03))


def bit_epiano():
    """An electric piano: a tine's bell over a soft body."""
    return _struck([(1, 1.0), (2, 0.25), (3, 0.08), (4, 0.12)], 1.2, 0.9, k_decay=3.0,
                   ring=lambda ph, t: 0.35 * math.sin(3.0 * ph) * math.exp(-t / 0.08))


def bit_bell():
    """A bell: an inharmonic pair over the fundamental, a long ring."""
    return _struck([(1, 1.0)], 1.4, 0.9, amplitude=0.8,
                   ring=lambda ph, t: 0.5 * math.sin(2.76 * ph) * math.exp(-t / 0.5) + 0.25 * math.sin(5.4 * ph) * math.exp(-t / 0.2))


def bit_music_box():
    """A music box: a pure tine, a short ring."""
    return _struck([(1, 1.0)], 0.7, 0.35, amplitude=0.8,
                   ring=lambda ph, t: 0.3 * math.sin(4.0 * ph) * math.exp(-t / 0.1))


def bit_pluck():
    """A synth pluck: a quick burst, a short body."""
    return _struck([(1, 1.0), (2, 0.5), (3, 0.25), (4, 0.12)], 0.7, 0.3, strike=0.4, k_decay=3.0)


def bit_harp():
    """A harp: nearly a sine, a half-second decay."""
    return _struck([(1, 1.0), (2, 0.2), (3, 0.1)], 0.9, 0.45, strike=0.15, strike_tau=0.002, k_decay=5.0, amplitude=0.85)


def bit_nylon():
    """A nylon guitar: a warm pluck with the fourth partial."""
    return _struck([(1, 1.0), (2, 0.5), (3, 0.15), (4, 0.3), (5, 0.05)], 1.0, 0.5, strike=0.3, k_decay=4.0)


def bit_marimba():
    """A marimba: a sine with a brief fourth partial, a short decay."""
    return _struck([(1, 1.0)], 0.5, 0.12, amplitude=0.85, ring=lambda ph, t: 0.1 * math.sin(4.0 * ph) * math.exp(-t / 0.04))


def bit_kalimba():
    """A kalimba: a sine with a metallic sixth, a fifth of a second."""
    return _struck([(1, 1.0)], 0.6, 0.2, amplitude=0.85, ring=lambda ph, t: 0.08 * math.sin(6.3 * ph) * math.exp(-t / 0.05))


# ── Pads and sections ──

def bit_strings():
    """A string section: ensemble beating, a 150 ms swell."""
    return _ensemble_voice({1: 1.0, 2: 0.45, 3: 0.2, 4: 0.3, 5: 0.1, 6: 0.12, 7: 0.06, 8: 0.08}, periods=160, attack_cycles=40, lowpass=0.75)


def bit_low_strings():
    """The section's low end: darker, a slower swell."""
    return _ensemble_voice({1: 1.0, 2: 0.5, 3: 0.25, 4: 0.2, 5: 0.08}, periods=160, attack_cycles=44, lowpass=0.5)


def bit_warm_pad():
    """A warm pad: three detuned layers, few partials, a slow bloom."""
    return _ensemble_voice({1: 1.0, 2: 0.35, 3: 0.12, 4: 0.08}, periods=180, attack_cycles=60, detune_layers=3, lowpass=0.5)


def bit_glass_pad():
    """A glass pad: the octave over the fundamental, bright and thin."""
    return _ensemble_voice({1: 0.6, 2: 1.0, 3: 0.2, 4: 0.5, 6: 0.2, 8: 0.15}, periods=160, attack_cycles=50, lowpass=0.8)


def bit_choir():
    """A choir: a vowel formant, three layers, a 140 ms swell."""
    return _ensemble_voice({1: 1.0, 2: 0.4, 3: 0.55, 4: 0.25, 5: 0.15, 6: 0.1}, periods=160, attack_cycles=36, detune_layers=3, lowpass=0.6)


def bit_organ():
    """A drawbar organ: the octaves and the twelfth, an instant attack."""
    return _sustained_voice({1: 1.0, 2: 0.8, 3: 0.5, 4: 0.6, 6: 0.3, 8: 0.4}, attack_cycles=3, lowpass=0.85)


def bit_brass_pad():
    """A brass section: bright, two layers, a 110 ms swell."""
    return _ensemble_voice({1: 0.8, 2: 1.0, 3: 0.7, 4: 0.5, 5: 0.35, 6: 0.25}, periods=160, attack_cycles=30, lowpass=0.7)


def bit_wind_choir():
    """Breathy voices: a soft spectrum with air in the attack."""
    return _sustained_voice({1: 1.0, 2: 0.25, 3: 0.3, 4: 0.1}, attack_cycles=24, breath=0.2, lowpass=0.5)


# ── Basses ──

def bit_sub_bass():
    """A sub bass: the fundamental and a little octave, held."""
    return _struck([(1, 1.0), (2, 0.3)], 0.8, 0.6, k_decay=6.0, amplitude=0.95)


def bit_picked_bass():
    """A picked bass: a strong octave, a pick's click."""
    return _struck([(1, 1.0), (2, 0.9), (3, 0.4), (4, 0.3), (5, 0.1)], 0.8, 0.45, strike=0.3, k_decay=5.0, amplitude=0.95)


def bit_synth_bass():
    """A synth bass: a saw's partials closing down over the note."""
    return _struck([(1, 1.0), (2, 0.6), (3, 0.5), (4, 0.35), (5, 0.25), (6, 0.15)], 0.8, 0.5, k_decay=5.0, amplitude=0.95)


def bit_fretless():
    """A fretless bass: a soft swell into a round tone, held."""
    return _sustained_voice({1: 1.0, 2: 0.5, 3: 0.2, 4: 0.1}, attack_cycles=6, lowpass=0.4, amplitude=0.95)


def bit_slap_bass():
    """A slap bass: a hard strike, the octave over the fundamental."""
    return _struck([(1, 0.8), (2, 1.0), (3, 0.6), (4, 0.5), (5, 0.3), (6, 0.2)], 0.7, 0.3, strike=0.6, strike_tau=0.004, k_decay=4.0, amplitude=0.95)


def bit_bowed_bass():
    """A bowed bass: the section's floor, a slow bow."""
    return _ensemble_voice({1: 1.0, 2: 0.6, 3: 0.4, 4: 0.2}, periods=160, attack_cycles=44, lowpass=0.45, amplitude=0.9)


# ── Kit ──

def bit_kick():
    n = int(SNES_RATE * 0.14)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 50.0 + 90.0 * math.exp(-t / 0.025)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = (math.sin(ph) + 0.5 * math.sin(2.0 * ph)) * math.exp(-t / 0.04)
        v += _rng.uniform(-0.25, 0.25) * math.exp(-t / 0.005)
        out.append(v)
    return _finish_snes(_lowpass(out, 0.5), 0.95)


def bit_snare():
    n = int(SNES_RATE * 0.16)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        tone = math.sin(2.0 * math.pi * 185.0 * t) * math.exp(-t / 0.03)
        out.append(0.35 * tone + _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.05))
    return _finish_snes(_highpass(out, 0.25), 0.9)


def bit_hat():
    n = int(SNES_RATE * 0.05)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.014) for i in range(n)]
    return _finish_snes(_highpass(out, 0.6), 0.7)


def bit_open_hat():
    n = int(SNES_RATE * 0.3)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.09) for i in range(n)]
    return _finish_snes(_highpass(out, 0.5), 0.7)


def bit_tom():
    n = int(SNES_RATE * 0.4)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SNES_RATE
        f = 110.0 + 70.0 * math.exp(-t / 0.04)
        ph += 2.0 * math.pi * f / SNES_RATE
        v = math.sin(ph) * math.exp(-t / 0.18) + 0.3 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.015)
        out.append(v)
    return _finish_snes(_lowpass(out, 0.6), 0.95)


def bit_crash():
    n = int(SNES_RATE * 0.8)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append((_rng.uniform(-1.0, 1.0) + 0.15 * math.sin(2.0 * math.pi * 3400.0 * t)) * math.exp(-t / 0.25))
    return _finish_snes(_highpass(out, 0.5), 0.65)


def bit_rim():
    n = int(SNES_RATE * 0.05)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append(math.sin(2.0 * math.pi * 2600.0 * t) * math.exp(-t / 0.01) + 0.5 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.003))
    return _finish_snes(_highpass(out, 0.3), 0.8)


# Presets this set adds to the registry: name -> (builder, kwargs, default volume)
PRESETS = {
    "bit_square":       (bit_square,       {}, 58),
    "bit_pulse":        (bit_pulse,        {}, 58),
    "bit_saw_lead":     (bit_saw_lead,     {}, 58),
    "bit_sine_flute":   (bit_sine_flute,   {}, 58),
    "bit_ocarina":      (bit_ocarina,      {}, 58),
    "bit_brass":        (bit_brass,        {}, 58),
    "bit_horn":         (bit_horn,         {}, 60),
    "bit_reed":         (bit_reed,         {}, 58),
    "bit_synth_voice":  (bit_synth_voice,  {}, 58),
    "bit_violin":       (bit_violin,       {}, 58),
    "bit_cello":        (bit_cello,        {}, 60),
    "bit_piano":        (bit_piano,        {}, 60),
    "bit_epiano":       (bit_epiano,       {}, 58),
    "bit_bell":         (bit_bell,         {}, 52),
    "bit_music_box":    (bit_music_box,    {}, 52),
    "bit_pluck":        (bit_pluck,        {}, 56),
    "bit_harp":         (bit_harp,         {}, 56),
    "bit_nylon":        (bit_nylon,        {}, 58),
    "bit_marimba":      (bit_marimba,      {}, 54),
    "bit_kalimba":      (bit_kalimba,      {}, 54),
    "bit_strings":      (bit_strings,      {}, 60),
    "bit_low_strings":  (bit_low_strings,  {}, 60),
    "bit_warm_pad":     (bit_warm_pad,     {}, 56),
    "bit_glass_pad":    (bit_glass_pad,    {}, 54),
    "bit_choir":        (bit_choir,        {}, 58),
    "bit_organ":        (bit_organ,        {}, 56),
    "bit_brass_pad":    (bit_brass_pad,    {}, 58),
    "bit_wind_choir":   (bit_wind_choir,   {}, 56),
    "bit_sub_bass":     (bit_sub_bass,     {}, 64),
    "bit_picked_bass":  (bit_picked_bass,  {}, 64),
    "bit_synth_bass":   (bit_synth_bass,   {}, 64),
    "bit_fretless":     (bit_fretless,     {}, 62),
    "bit_slap_bass":    (bit_slap_bass,    {}, 64),
    "bit_bowed_bass":   (bit_bowed_bass,   {}, 62),
    "bit_kick":         (bit_kick,         {}, 64),
    "bit_snare":        (bit_snare,        {}, 62),
    "bit_hat":          (bit_hat,          {}, 50),
    "bit_open_hat":     (bit_open_hat,     {}, 48),
    "bit_tom":          (bit_tom,          {}, 62),
    "bit_crash":        (bit_crash,        {}, 52),
    "bit_rim":          (bit_rim,          {}, 56),
}

# Release family per sustaining voice (see samples.dsp.RELEASE)
RELEASE = {
    "bit_square": "lead", "bit_pulse": "lead", "bit_saw_lead": "lead", "bit_sine_flute": "flute", "bit_ocarina": "flute",
    "bit_brass": "brass", "bit_horn": "brass", "bit_reed": "flute", "bit_synth_voice": "choir", "bit_violin": "strings",
    "bit_cello": "strings", "bit_piano": "keys", "bit_epiano": "keys", "bit_bell": "keys", "bit_music_box": "keys",
    "bit_pluck": "keys", "bit_harp": "keys", "bit_nylon": "keys", "bit_marimba": "keys", "bit_kalimba": "keys",
    "bit_strings": "strings", "bit_low_strings": "strings", "bit_warm_pad": "pad", "bit_glass_pad": "pad",
    "bit_choir": "choir", "bit_organ": "organ", "bit_brass_pad": "brass", "bit_wind_choir": "choir",
    "bit_sub_bass": "bass", "bit_picked_bass": "bass", "bit_synth_bass": "bass", "bit_fretless": "bass",
    "bit_slap_bass": "bass", "bit_bowed_bass": "strings",
}

# The SNES chip envelope each pitched voice is played with (samples.SAMPLE_ENVELOPES, the place a pack's sample keeps
# its game's; whole/render.py's `put` plays it with no new code path), round 72. Before it every note on this set went
# out flat at full gain and cut hard, where a game's samples come with the game's ADSR. In FFVI's own terms (round 71:
# every sample plays attack 15, decay 7, sustain level 7, then a sustain rate of 0 to hold or 12 to 16 to fall;
# ADSR1 0xFF, ADSR2 0xE0 | rate) every voice here takes attack 15, decay 7 to level 7 and sustain rate 0: the
# sustaining voices because they hold (a string, a pad, a horn, an organ, a lead, the bowed and fretless basses), the
# struck and plucked voices because their decay is already in their data (the _struck recipe shapes the whole sample
# under an exponential and freezes its last two periods at the decayed level: the piano's tail sits at 0.22 of its
# strike, the e-piano's 0.26, the bell's 0.21, the harp's and nylon's 0.135, the pluck's and slap bass's 0.10, the
# kalimba's 0.05, the marimba's 0.016, the sub, picked and synth basses' 0.26, 0.17 and 0.20; a decaying rate on top
# would double the fall), so a held struck note keeps sounding at its tail's level as it did. The kit's one-shots
# carry none (flat, as every game's drums here).
_HOLD = {"adsr": [0xFF, 0xE0]}        # attack 15, decay 7, sustain level 7, sustain rate 0
ENVELOPES = {name: dict(_HOLD) for name in RELEASE}

# Where each pitched voice sounds right, MIDI low to high: the writer fits a
# voice to a part's register and speed by this (packs.profile). The tops were
# placed by the owner's ear on 2026-10-31 (the Bit Voice Range Check: every
# lead-capable voice at C4, F#4, C5, F#5, C6 and F#6, each note at the same
# measured loudness the writer gives it): the pitch above which the voice stops
# sounding right as a line. The bright single-period leads (square, pulse, saw,
# brass, reed) had ranged to 86-96 and carried the tune at C6 in Song Check 58,
# where they read as "exploding"; the pulse, saw, brass and reed now stop at
# C5, the square at F#5, and the high registers go to the flute, ocarina, horn
# and the keys. A voice he found fine up to F#6 keeps a top already above it.
RANGES = {
    "bit_square": (55, 78), "bit_pulse": (55, 72), "bit_saw_lead": (52, 72), "bit_sine_flute": (60, 84),
    "bit_ocarina": (65, 98), "bit_brass": (50, 72), "bit_horn": (41, 84), "bit_reed": (58, 72),
    "bit_synth_voice": (50, 78), "bit_violin": (55, 78), "bit_cello": (36, 78),
    "bit_piano": (36, 96), "bit_epiano": (36, 96), "bit_bell": (72, 108), "bit_music_box": (72, 104),
    "bit_pluck": (48, 91), "bit_harp": (36, 96), "bit_nylon": (40, 90), "bit_marimba": (48, 96), "bit_kalimba": (60, 96),
    "bit_strings": (48, 84), "bit_low_strings": (36, 90), "bit_warm_pad": (48, 90), "bit_glass_pad": (60, 78),
    "bit_choir": (48, 78), "bit_organ": (36, 78), "bit_brass_pad": (48, 78), "bit_wind_choir": (55, 78),
    "bit_sub_bass": (24, 48), "bit_picked_bass": (28, 55), "bit_synth_bass": (28, 55), "bit_fretless": (28, 57),
    "bit_slap_bass": (28, 55), "bit_bowed_bass": (28, 52),
}


PACK = {
    "palette": "snes",
    "label": "bitComposer",
    # The pools the writer draws a part's voice from, then fits by range and speed; a name twice weighs twice.
    "voices": {
        "lead": ["bit_square", "bit_pulse", "bit_saw_lead", "bit_sine_flute", "bit_ocarina", "bit_brass",
                 "bit_reed", "bit_synth_voice", "bit_violin", "bit_cello", "bit_horn", "bit_epiano", "bit_piano",
                 "bit_pluck", "bit_nylon", "bit_bell"],
        "alt_lead": ["bit_pulse", "bit_reed", "bit_horn", "bit_sine_flute", "bit_violin", "bit_synth_voice", "bit_brass",
                     "bit_cello", "bit_marimba"],
        "harmony": ["bit_strings", "bit_strings", "bit_strings", "bit_warm_pad", "bit_warm_pad", "bit_glass_pad",
                    "bit_choir", "bit_choir", "bit_organ", "bit_brass_pad", "bit_wind_choir", "bit_low_strings", "bit_square"],
        "counter": ["bit_horn", "bit_reed", "bit_cello", "bit_violin", "bit_synth_voice", "bit_sine_flute", "bit_pulse",
                    "bit_brass", "bit_wind_choir"],
        "arp": ["bit_pluck", "bit_pluck", "bit_harp", "bit_harp", "bit_epiano", "bit_marimba", "bit_kalimba",
                "bit_music_box", "bit_bell", "bit_nylon", "bit_piano"],
        "bass_heavy": ["bit_sub_bass", "bit_sub_bass", "bit_synth_bass", "bit_picked_bass", "bit_bowed_bass"],
        "bass_medium": ["bit_picked_bass", "bit_picked_bass", "bit_synth_bass", "bit_fretless", "bit_slap_bass"],
        "bass_light": ["bit_fretless", "bit_picked_bass", "bit_nylon", "bit_harp", "bit_sub_bass"],
        "drums": {"kick": "bit_kick", "snare": "bit_snare", "hihat": "bit_hat", "tom": "bit_tom", "crash": "bit_crash",
                  "open_hihat": "bit_open_hat", "rim": "bit_rim"},
    },
    # Classic's habits on this set, where Classic is asked to play on it: nothing leaning any game's way.
    "habits": {
        "tempo": {"slow": 1, "medium": 2, "fast": 1},
        "intro": {"pad_hook": 2, "arp_bed": 2, "riff_vamp": 1, "drum_pickup": 1},
        "energy": {"chill": 1, "normal": 2, "intense": 1},
        "scale_family": {"minor": 2, "major": 2, "pentatonic": 1},
        "harmony_voicing": {"full": 2, "thin": 1},
        "harmony_mode": {"ostinato": 2, "sustain": 3, "pulse": 1, "stabs": 1, "rhythmic": 1},
        "bass_weight": {"heavy": 1, "medium": 2, "light": 1},
        "bass_style": {"steady": 2, "walking": 2, "octave": 2, "driving": 1},
        "drum_density": {"sparse": 1, "normal": 2, "busy": 1},
        "drum_swing": {"off": 4, "light": 1, "heavy": 0},
        # The echo on every song: the SNES era's room. A dry song on this set sounded empty beside Classic
        # (the owner's ear, 2.0rc2); the slap and the eighth, as the games most often have it.
        "echo": 1.0,
        "echo_wet": {"light": 0, "normal": 2, "wet": 2},
        "echo_delay": {"slap": 3, "eighth": 2, "dotted": 1, "quarter": 0},
        "echo_feedback": (0.55, 0.7),
        "echo_stereo": {"bounce": 1, "centre": 1},
        "counter_line": 0.4,
        "section_rolls": True,
    },
    "trims": {"hihat": 14, "openhat": 14},
}
