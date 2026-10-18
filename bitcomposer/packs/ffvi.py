"""Final Fantasy VI style pack: its voices (synthesised here) and the arrangement
habits that go with them. Registered on import by bitcomposer.packs.

Every voice is modelled on the game's own sample bank: 82 SPC snapshots were
decoded (BRR), every unique sample profiled (steady-state harmonics, centroid,
attack, decay, loop), matched to the game's documented instrument table by its
exact BRR size, and traced to the voices that play it (sounding pitch, envelope,
echo). Each recipe below names the game instrument it targets and the measured
profile. Nothing from the game is copied; the shapes are re-synthesised. The
echo too: every snapshot runs 80 ms of delay with feedback 0.64, flat filter,
both sides the same sign, strings and leads sent, bass and kit dry.
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
    """Strings 1 ($0D), in 54 of 82 banks: a long chorused sample, a strong
    fourth partial, bright upper partials, a 180 ms swell."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.42, 3: 0.16, 4: 0.40, 5: 0.11, 6: 0.16, 7: 0.08, 8: 0.14, 9: 0.05, 10: 0.03},
        periods=160, attack_cycles=47, lowpass=0.8, amplitude=0.85)


def ffvi_flutes() -> tuple[bytes, int, dict]:
    """Flute 2 ($08), played in chords in 29 banks (under Locke, Edgar, Terra):
    the octave over a quiet fundamental, a 110 ms swell."""
    return _ensemble_voice(
        steady={1: 0.5, 2: 1.0, 3: 0.38, 4: 0.02, 5: 0.05, 6: 0.07},
        periods=140, attack_cycles=29, detune_layers=2, lowpass=0.5, amplitude=0.85)


def ffvi_flute() -> tuple[bytes, int, dict]:
    """Flute 1 ($07), in 29 banks: a soft flute with octave and twelfth under
    the fundamental, quick onset, a little breath."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.42, 3: 0.26, 4: 0.09, 5: 0.01},
        attack_cycles=8, loop_cycles=2, breath=0.1, amplitude=0.9)


def ffvi_pan_flute() -> tuple[bytes, int, dict]:
    """Pan flute ($03), Terra's lead: pure with a touch of third partial, a
    long 200 ms breathy onset."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.04, 3: 0.17, 4: 0.02, 5: 0.06},
        attack_cycles=54, loop_cycles=1, breath=0.3, amplitude=0.9)


def ffvi_wood_flute() -> tuple[bytes, int, dict]:
    """Pan flute 2 ($34), Cyan's shakuhachi: a near-pure tone with breath."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.03, 3: 0.03, 4: 0.03},
        attack_cycles=12, loop_cycles=1, breath=0.2, amplitude=0.9)


def ffvi_oboe() -> tuple[bytes, int, dict]:
    """Oboe ($0A), in 18 banks: the octave over the fundamental, a little
    fifth partial, 30 ms onset."""
    return _sustained_voice(
        steady={1: 0.5, 2: 1.0, 3: 0.27, 4: 0.04, 5: 0.17, 6: 0.09, 7: 0.04},
        attack_cycles=8, loop_cycles=2, breath=0.05, amplitude=0.85)


def ffvi_trumpet() -> tuple[bytes, int, dict]:
    """Trumpet ($0E), in 26 banks, the Battle and Fanfare brass: a full stack
    peaking on the third partial, bright onset, played in chords as often as
    alone."""
    return _sustained_voice(
        steady={1: 0.37, 2: 0.86, 3: 1.0, 4: 0.77, 5: 0.67, 6: 0.59, 7: 0.5, 8: 0.37, 9: 0.23, 10: 0.18},
        bright={1: 0.3, 2: 0.9, 3: 1.0, 4: 0.9, 5: 0.8, 6: 0.7, 7: 0.6, 8: 0.5, 9: 0.4, 10: 0.3},
        attack_cycles=10, loop_cycles=2, amplitude=0.9)


def ffvi_dist_guitar() -> tuple[bytes, int, dict]:
    """Distortion guitar ($1E), the Battle lead: fundamental and octave equal,
    the fourth partial strong, fast onset."""
    return _sustained_voice(
        steady={1: 1.0, 2: 1.0, 3: 0.1, 4: 0.6, 5: 0.3, 6: 0.1, 7: 0.08, 8: 0.06},
        bright={1: 0.7, 2: 1.0, 3: 0.6, 4: 0.9, 5: 0.7, 6: 0.5, 7: 0.4, 8: 0.3},
        attack_cycles=4, loop_cycles=2, amplitude=0.9)


def ffvi_trombone() -> tuple[bytes, int, dict]:
    """Trombone ($1A), in 9 banks, played low: the octave over the
    fundamental, a strong third, 90 ms onset."""
    return _sustained_voice(
        steady={1: 0.65, 2: 1.0, 3: 0.74, 4: 0.11, 5: 0.35, 6: 0.21},
        bright={1: 0.5, 2: 1.0, 3: 0.9, 4: 0.4, 5: 0.5, 6: 0.3},
        attack_cycles=24, loop_cycles=2, lowpass=0.5, amplitude=0.9)


def ffvi_synth_lead() -> tuple[bytes, int, dict]:
    """Synth 5 ($2C), the lead in 28 banks (Locke, Returners, Cyan, the
    Prelude): round and dark, a 140 ms onset, loud, always echoed."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.56, 3: 0.23, 4: 0.09, 5: 0.04},
        bright={1: 1.0, 2: 0.7, 3: 0.4, 4: 0.2, 5: 0.1},
        attack_cycles=37, loop_cycles=2, lowpass=0.6, amplitude=0.9)


def ffvi_choir() -> tuple[bytes, int, dict]:
    """Choir ($06), the Prelude's and Phantom Forest's: fundamental with half
    an octave, a 170 ms swell."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.47, 3: 0.05, 4: 0.02},
        periods=150, attack_cycles=45, detune_layers=2, lowpass=0.5, amplitude=0.85)


def ffvi_organ() -> tuple[bytes, int, dict]:
    """Pipe organ ($25), the Opening and Dancing Mad: octave over the
    fundamental, bright even partials, 40 ms onset."""
    return _ensemble_voice(
        steady={1: 0.48, 2: 1.0, 3: 0.32, 4: 0.27, 5: 0.02, 6: 0.38, 7: 0.01, 8: 0.36},
        periods=140, attack_cycles=11, detune_layers=1, lowpass=0.7, amplitude=0.85)


def ffvi_rock_organ() -> tuple[bytes, int, dict]:
    """Rock organ ($0B), the Decisive Battle organ: the twelfth drawbar on
    top, a quiet fundamental."""
    return _sustained_voice(
        steady={1: 0.12, 2: 0.38, 3: 1.0, 4: 0.07, 5: 0.01, 6: 0.24, 8: 0.08},
        attack_cycles=3, loop_cycles=2, amplitude=0.85)


def ffvi_voice() -> tuple[bytes, int, dict]:
    """Female voice ($3A), the Aria's soprano: fundamental and a little
    octave, 25 ms onset."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.42, 6: 0.04},
        attack_cycles=7, loop_cycles=1, breath=0.03, amplitude=0.85)


def ffvi_cello() -> tuple[bytes, int, dict]:
    """Cello 1 ($05), Gau's lead: octave over the fundamental, a fourth
    partial, a 265 ms swell, loud, echoed."""
    return _ensemble_voice(
        steady={1: 0.57, 2: 1.0, 3: 0.16, 4: 0.37, 5: 0.1, 6: 0.25},
        periods=140, attack_cycles=60, detune_layers=1, lowpass=0.5, amplitude=0.9)


def ffvi_male_voice() -> tuple[bytes, int, dict]:
    """Male voice 1 ($38), in 8 banks (the Opening, Dancing Mad): a dark
    'ah', fundamental with a little octave and twelfth, 55 ms onset."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.22, 3: 0.19, 4: 0.03},
        periods=140, attack_cycles=14, detune_layers=2, lowpass=0.45, amplitude=0.85)


def ffvi_strings2() -> tuple[bytes, int, dict]:
    """Strings 2 ($31), Dark World and Epitaph: a thinner section with the
    fourth and fifth partials up, instant onset."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.09, 3: 0.19, 4: 0.28, 5: 0.22, 6: 0.03},
        periods=150, attack_cycles=6, detune_layers=2, lowpass=0.7, amplitude=0.85)


def ffvi_organ_pedal() -> tuple[bytes, int, dict]:
    """Pipe organ 2 ($3B), Dancing Mad's pedal: the organ's stack played low,
    100 ms onset."""
    return _sustained_voice(
        steady={1: 0.59, 2: 1.0, 3: 0.39, 4: 0.43, 5: 0.03, 6: 0.53, 7: 0.01, 8: 0.42},
        attack_cycles=26, loop_cycles=2, lowpass=0.5, amplitude=0.9)


def ffvi_bottle() -> tuple[bytes, int, dict]:
    """Bottle blow ($36), the Kids Run Through the City lead: nearly pure,
    a 65 ms breathy onset."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.13, 3: 0.11, 4: 0.02, 6: 0.04},
        attack_cycles=17, loop_cycles=1, breath=0.25, amplitude=0.9)


# ── Struck and plucked voices ──

def ffvi_bass() -> tuple[bytes, int, dict]:
    """Bass guitar 2 ($1C), in 21 banks: fundamental and octave equal,
    instant onset, the driver's slow decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.97), (3, 0.42), (4, 0.34), (5, 0.05), (6, 0.15)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        return sum(a * math.sin(k * ph) * math.exp(-t * k / 6.0) for k, a in partials)
    return _decaying_voice(0.7, tone, amp_tau=0.5, tail_loop=True, amplitude=0.95)


def ffvi_piano() -> tuple[bytes, int, dict]:
    """Piano ($0C), Spinach Rag's: a dull body (fundamental, a third of
    octave), a short bright strike, a slow decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.32), (3, 0.04)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph) * math.exp(-t * k / 4.0) for k, a in partials)
        strike = 0.35 * (math.sin(4.0 * ph) + 0.5 * math.sin(6.0 * ph)) * math.exp(-t / 0.03)
        return body + strike
    return _decaying_voice(1.2, tone, amp_tau=0.8, tail_loop=True, amplitude=0.9)


def ffvi_harp() -> tuple[bytes, int, dict]:
    """Harp ($1B), in 21 banks, the Prelude's arpeggio: a dull pluck, nearly
    a sine, the driver's half-second decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.16), (3, 0.11), (4, 0.02)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph) * math.exp(-t * k / 5.0) for k, a in partials)
        return body + 0.25 * math.sin(5.0 * ph) * math.exp(-t / 0.02)
    return _decaying_voice(0.9, tone, amp_tau=0.4, tail_loop=True, amplitude=0.85)


def ffvi_picked() -> tuple[bytes, int, dict]:
    """Picked string 3 ($1D), under Terra and Relm: a bright nylon pluck with
    the octave and double octave strong."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 0.47), (2, 1.0), (3, 0.48), (4, 0.76), (5, 0.15), (6, 0.1)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph) * math.exp(-t * k / 3.0) for k, a in partials)
        return body + 0.4 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.003)
    return _decaying_voice(0.8, tone, amp_tau=0.35, tail_loop=True, amplitude=0.9)


def ffvi_guitar() -> tuple[bytes, int, dict]:
    """Acoustic guitar 2 ($32), in 11 banks: a warm pluck, octave and fourth
    partial, slow decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.56), (3, 0.1), (4, 0.38), (5, 0.06)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph) * math.exp(-t * k / 4.0) for k, a in partials)
        return body + 0.3 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.003)
    return _decaying_voice(1.0, tone, amp_tau=0.5, tail_loop=True, amplitude=0.9)


def ffvi_dark_bass() -> tuple[bytes, int, dict]:
    """Bass ($18), in 5 banks: a dark bass with the fourth and sixth partials
    up, instant onset, held."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.38), (3, 0.15), (4, 0.47), (5, 0.13), (6, 0.36), (7, 0.21)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        return sum(a * math.sin(k * ph) * math.exp(-t * k / 8.0) for k, a in partials)
    return _decaying_voice(0.7, tone, amp_tau=0.6, tail_loop=True, amplitude=0.95)


def ffvi_sitar() -> tuple[bytes, int, dict]:
    """Sitar ($04), Mog's and Strago's: a bright buzzing pluck, the twelfth
    and double octave strong, a long sympathetic ring."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 0.52), (2, 0.16), (3, 1.0), (4, 0.61), (5, 0.46), (6, 0.19), (7, 0.04)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph) * math.exp(-t * k / 5.0) for k, a in partials)
        return body + 0.3 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.004)
    return _decaying_voice(1.0, tone, amp_tau=0.5, tail_loop=True, amplitude=0.85)


def ffvi_tubular_bell() -> tuple[bytes, int, dict]:
    """Tubular bell ($24), the Opening's and Dancing Mad's: the double octave
    carries it, with a little octave and a long ring."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return (math.sin(4.0 * ph) + 0.19 * math.sin(2.0 * ph) * math.exp(-t / 0.3)
                + 0.1 * math.sin(5.4 * ph) * math.exp(-t / 0.15))
    return _decaying_voice(1.2, tone, amp_tau=0.6, tail_loop=True, amplitude=0.8)


def ffvi_xylophone() -> tuple[bytes, int, dict]:
    """Xylophone ($3E): a pure tone, quick decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return math.sin(ph) + 0.04 * math.sin(3.0 * ph) * math.exp(-t / 0.05)
    return _decaying_voice(0.5, tone, amp_tau=0.15, tail_loop=True, amplitude=0.8)


# ── Kit ──
# Kick ($22): a 68 ms thud. Snare 1 ($14): 125 ms of bright rattle. Closed
# hat ($0F): 40 ms. Open hat ($11): 270 ms, bright. Cymbal ($12): a looped
# wash with a release. Timpani ($16), played at about a quarter speed:
# 130 Hz, 700 ms, 430 ms to silence. Wood block ($30): a 3 kHz ping.

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


def ffvi_hat() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.045)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.012) for i in range(n)]
    return _finish_snes(_highpass(out, 0.6), 0.7)


def ffvi_open_hat() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.35)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.1) for i in range(n)]
    return _finish_snes(_highpass(out, 0.5), 0.7)


def ffvi_cymbal() -> tuple[bytes, int, dict]:
    """Cymbal ($12): the bank loops a wash and lets the release end it; here
    a 0.6 s wash with a slow decay, for the crash slot."""
    n = int(SNES_RATE * 0.7)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append((_rng.uniform(-1.0, 1.0) + 0.2 * math.sin(2.0 * math.pi * 3000.0 * t)) * math.exp(-t / 0.22))
    return _finish_snes(_highpass(out, 0.5), 0.65)


def ffvi_woodblock() -> tuple[bytes, int, dict]:
    n = int(SNES_RATE * 0.05)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        out.append(math.sin(2.0 * math.pi * 3000.0 * t) * math.exp(-t / 0.012)
                   + 0.5 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.003))
    return _finish_snes(_highpass(out, 0.3), 0.8)


# Presets this pack adds to the registry: name -> (builder, kwargs, default volume)
PRESETS = {
    "ffvi_strings":      (ffvi_strings,      {}, 60),
    "ffvi_flutes":       (ffvi_flutes,       {}, 58),
    "ffvi_flute":        (ffvi_flute,        {}, 58),
    "ffvi_pan_flute":    (ffvi_pan_flute,    {}, 58),
    "ffvi_wood_flute":   (ffvi_wood_flute,   {}, 58),
    "ffvi_oboe":         (ffvi_oboe,         {}, 58),
    "ffvi_trumpet":      (ffvi_trumpet,      {}, 58),
    "ffvi_dist_guitar":  (ffvi_dist_guitar,  {}, 58),
    "ffvi_trombone":     (ffvi_trombone,     {}, 60),
    "ffvi_synth_lead":   (ffvi_synth_lead,   {}, 60),
    "ffvi_choir":        (ffvi_choir,        {}, 58),
    "ffvi_organ":        (ffvi_organ,        {}, 56),
    "ffvi_rock_organ":   (ffvi_rock_organ,   {}, 56),
    "ffvi_voice":        (ffvi_voice,        {}, 58),
    "ffvi_cello":        (ffvi_cello,        {}, 60),
    "ffvi_male_voice":   (ffvi_male_voice,   {}, 58),
    "ffvi_strings2":     (ffvi_strings2,     {}, 58),
    "ffvi_organ_pedal":  (ffvi_organ_pedal,  {}, 62),
    "ffvi_bottle":       (ffvi_bottle,       {}, 58),
    "ffvi_dark_bass":    (ffvi_dark_bass,    {}, 64),
    "ffvi_sitar":        (ffvi_sitar,        {}, 56),
    "ffvi_bass":         (ffvi_bass,         {}, 64),
    "ffvi_piano":        (ffvi_piano,        {}, 60),
    "ffvi_harp":         (ffvi_harp,         {}, 56),
    "ffvi_picked":       (ffvi_picked,       {}, 58),
    "ffvi_guitar":       (ffvi_guitar,       {}, 58),
    "ffvi_tubular_bell": (ffvi_tubular_bell, {}, 52),
    "ffvi_xylophone":    (ffvi_xylophone,    {}, 52),
    "ffvi_timpani":      (ffvi_timpani,      {}, 64),
    "ffvi_bassdrum":     (ffvi_bassdrum,     {}, 64),
    "ffvi_snare":        (ffvi_snare,        {}, 62),
    "ffvi_hat":          (ffvi_hat,          {}, 50),
    "ffvi_open_hat":     (ffvi_open_hat,     {}, 48),
    "ffvi_cymbal":       (ffvi_cymbal,       {}, 52),
    "ffvi_woodblock":    (ffvi_woodblock,    {}, 56),
}

# Release family per sustaining voice (see samples.dsp.RELEASE)
RELEASE = {
    "ffvi_strings": "strings", "ffvi_flutes": "flute", "ffvi_flute": "flute",
    "ffvi_pan_flute": "flute", "ffvi_wood_flute": "flute", "ffvi_oboe": "flute",
    "ffvi_trumpet": "brass", "ffvi_dist_guitar": "lead", "ffvi_trombone": "brass",
    "ffvi_synth_lead": "lead", "ffvi_choir": "choir", "ffvi_organ": "organ",
    "ffvi_rock_organ": "organ", "ffvi_voice": "choir", "ffvi_cello": "strings",
    "ffvi_bass": "bass", "ffvi_piano": "keys", "ffvi_harp": "keys", "ffvi_picked": "keys",
    "ffvi_guitar": "keys", "ffvi_tubular_bell": "keys", "ffvi_xylophone": "keys",
    "ffvi_male_voice": "choir", "ffvi_strings2": "strings", "ffvi_organ_pedal": "organ",
    "ffvi_bottle": "flute", "ffvi_dark_bass": "bass", "ffvi_sitar": "keys",
}


PACK = {
        "palette": "snes",
        "label": "FFVI orchestral",
        # Every voice is the pack's own, built from the game's bank. Pool
        # weights follow how often the bank carries each instrument: the synth
        # lead is in 28 banks, the strings in 54, the harp in 21.
        "voices": {
            "lead": ["ffvi_synth_lead", "ffvi_synth_lead", "ffvi_trumpet", "ffvi_oboe",
                     "ffvi_pan_flute", "ffvi_wood_flute", "ffvi_flute", "ffvi_dist_guitar",
                     "ffvi_cello", "ffvi_voice", "ffvi_piano", "ffvi_bottle", "ffvi_sitar"],
            "alt_lead": ["ffvi_trumpet", "ffvi_oboe", "ffvi_flute", "ffvi_voice", "ffvi_cello",
                         "ffvi_synth_lead", "ffvi_pan_flute", "ffvi_bottle"],
            "harmony": ["ffvi_strings", "ffvi_strings", "ffvi_strings", "ffvi_flutes", "ffvi_flutes",
                        "ffvi_organ", "ffvi_choir", "ffvi_trumpet", "ffvi_harp", "ffvi_rock_organ",
                        "ffvi_male_voice", "ffvi_strings2"],
            "counter": ["ffvi_trumpet", "ffvi_trombone", "ffvi_oboe", "ffvi_flute", "ffvi_voice",
                        "ffvi_cello", "ffvi_male_voice"],
            "arp": ["ffvi_harp", "ffvi_harp", "ffvi_harp", "ffvi_picked", "ffvi_guitar",
                    "ffvi_piano", "ffvi_xylophone", "ffvi_tubular_bell", "ffvi_sitar"],
            "bass_heavy": ["ffvi_bass", "ffvi_bass", "ffvi_dark_bass", "ffvi_trombone", "ffvi_organ_pedal"],
            "bass_medium": ["ffvi_bass", "ffvi_dark_bass", "ffvi_guitar", "ffvi_trombone"],
            "bass_light": ["ffvi_guitar", "ffvi_harp", "ffvi_bass"],
            "drums": {"kick": "ffvi_bassdrum", "snare": "ffvi_snare", "hihat": "ffvi_hat",
                      "tom": "ffvi_timpani", "crash": "ffvi_cymbal",
                      "open_hihat": "ffvi_open_hat", "rim": "ffvi_woodblock"},
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
