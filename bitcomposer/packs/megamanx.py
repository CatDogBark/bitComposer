"""Mega Man X style pack: its voices (synthesised here) and the arrangement
habits that go with them. Registered on import by bitcomposer.packs.

Every voice is modelled on the game's own sample bank: 35 SPC snapshots, one
shared bank of about thirty samples, each profiled (steady-state harmonics,
centroid, attack, decay, loop) and traced to the voices that play it. Twenty
of the samples matched William Kage's named rips by exact length, which fixed
the names: the arp voice is the overdrive guitar, the soft lead the organ, the
bass the slap bass, the "string pad" a distortion guitar with a 155 ms swell.
The lead guitar is band-matched to the one bright instant-attack guitar in
every bank, which Kage leaves unnamed. Nothing from the game is copied; the
shapes are re-synthesised. The echo, from the DSP registers: 48 ms, feedback
0.53, the two sides inverted.
"""
import math

from ..samples.dsp import (
    _rng, BASE_NOTE_HZ, _lowpass, _highpass, SNES_RATE, SNES_PERIOD, _finish_snes, _sustained_voice, _decaying_voice, ENSEMBLE_DRY, _ensemble_voice, _drive,
)


# ── Guitars ──

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


def mmx_overdrive_guitar() -> tuple[bytes, int, dict]:
    """Overdrive guitar (Kage's name), in every bank: a bright one-cycle
    wave, fundamental and octave equal, the twelfth strong; the game's arp
    and riff voice, dry."""
    return _sustained_voice(
        steady={1: 1.0, 2: 1.0, 3: 0.74, 4: 0.23, 5: 0.19, 6: 0.27, 7: 0.17, 9: 0.1},
        attack_cycles=3, loop_cycles=1, amplitude=0.9)


def mmx_guitar_pad() -> tuple[bytes, int, dict]:
    """Distortion guitar (Kage's name), in 26 banks: a 155 ms swell into a
    tone carried by its fourth partial, the game's guitar pad, chorused."""
    return _ensemble_voice(
        steady={1: 0.2, 2: 0.38, 3: 0.43, 4: 1.0, 5: 0.13, 6: 0.48, 7: 0.24, 8: 0.18, 9: 0.2, 10: 0.1},
        periods=150, attack_cycles=41, detune_layers=2, lowpass=0.5, amplitude=0.85)


def mmx_clean_guitar() -> tuple[bytes, int, dict]:
    """Acoustic guitar (Kage's name), in 7 banks: a clean pluck, nearly a
    sine with a little octave and double octave."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    partials = [(1, 1.0), (2, 0.14), (3, 0.08), (4, 0.08), (5, 0.04)]

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = sum(a * math.sin(k * ph) * math.exp(-t * k / 4.0) for k, a in partials)
        return body + 0.4 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.003)
    return _decaying_voice(0.8, tone, amp_tau=0.35, tail_loop=True, amplitude=0.9)


# ── Synths ──

def mmx_synth_brass() -> tuple[bytes, int, dict]:
    """Synth brass (Kage's name), in every bank: a bright overblown attack
    settling into a strong third and fourth partial."""
    # The game's sample has no brighter onset (its centroid is flat from the
    # first block to the loop); the overblown attack here was invented and,
    # retriggered on every stab, was a burst. Gone.
    return _sustained_voice(
        steady={1: 1.0, 2: 0.46, 3: 0.79, 4: 0.58, 5: 0.37, 6: 0.13, 7: 0.22, 8: 0.2},
        attack_cycles=7, loop_cycles=2, amplitude=0.9)


def mmx_strings() -> tuple[bytes, int, dict]:
    """Strings (Kage's name), in every bank: a 95 ms swell, fundamental over
    a third of octave and a fourth partial, chorused."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.37, 3: 0.16, 4: 0.31, 5: 0.11, 6: 0.1, 7: 0.09, 8: 0.03},
        periods=150, attack_cycles=25, detune_layers=2, lowpass=0.7, amplitude=0.85)


def mmx_saw_pad() -> tuple[bytes, int, dict]:
    """Saw wave (Kage's name), in 7 banks: a 160 ms swell into a soft saw,
    the partials falling evenly."""
    return _ensemble_voice(
        steady={1: 1.0, 2: 0.83, 3: 0.53, 4: 0.29, 5: 0.19, 6: 0.14, 7: 0.1, 8: 0.07, 9: 0.05},
        periods=150, attack_cycles=42, detune_layers=2, lowpass=0.6, amplitude=0.85)


def mmx_organ() -> tuple[bytes, int, dict]:
    """Organ (Kage's bell organ), in 25 banks: the octave carries it over a
    quiet fundamental, with the twelfth and double octave, a 50 ms onset."""
    return _sustained_voice(
        steady={1: 0.15, 2: 1.0, 3: 0.5, 4: 0.33, 6: 0.08},
        attack_cycles=14, loop_cycles=2, lowpass=0.6, amplitude=0.85)


def mmx_synth_lead() -> tuple[bytes, int, dict]:
    """Synth lead (Kage's boomer lead), in every bank: a one-cycle wave with
    the partials falling smoothly, instant, bright."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.49, 3: 0.37, 4: 0.29, 5: 0.21, 6: 0.15, 7: 0.13, 8: 0.12, 9: 0.09, 10: 0.08},
        attack_cycles=2, loop_cycles=1, amplitude=0.9)


def mmx_square() -> tuple[bytes, int, dict]:
    """Square wave (Kage's name), in every bank: odd partials, the
    twelfth strong, instant."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.06, 3: 0.31, 4: 0.12, 5: 0.2, 7: 0.22, 9: 0.22},
        attack_cycles=2, loop_cycles=1, amplitude=0.9)


def mmx_bright_lead() -> tuple[bytes, int, dict]:
    """Synth lead 2 (Kage's harmonica), in every bank: a buzzing one-cycle
    wave with every partial up to the fifth near full, instant."""
    return _sustained_voice(
        steady={1: 0.94, 2: 1.0, 3: 0.89, 4: 0.77, 5: 0.58, 6: 0.39, 7: 0.15, 8: 0.07, 9: 0.23, 10: 0.33},
        attack_cycles=2, loop_cycles=1, amplitude=0.9)


def mmx_hollow() -> tuple[bytes, int, dict]:
    """Hollow wave, in every bank: fundamental and twelfth, almost nothing
    else; a clarinet-like synth."""
    return _sustained_voice(
        steady={1: 1.0, 2: 0.12, 3: 0.95, 5: 0.1},
        attack_cycles=3, loop_cycles=1, amplitude=0.9)


def mmx_bell() -> tuple[bytes, int, dict]:
    """Bell synth (Kage's vibraphone), in 9 banks: a pure tone with a
    double-octave partial, played with the driver's decay."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        return math.sin(ph) + 0.39 * math.sin(4.0 * ph) * math.exp(-t / 0.25) + 0.06 * math.sin(2.0 * ph)
    return _decaying_voice(0.9, tone, amp_tau=0.4, tail_loop=True, amplitude=0.85)


def mmx_orch_hit() -> tuple[bytes, int, dict]:
    """Orchestra hit (Kage's name), in every bank: a 140 ms chord stab, every
    partial strong, bright. The game's stab voice."""
    w = 2.0 * math.pi * BASE_NOTE_HZ
    n = int(SNES_RATE * 0.18)
    out = []
    for i in range(n):
        t = i / SNES_RATE
        ph = w * i / SNES_RATE
        v = (math.sin(ph) + 0.85 * math.sin(2.0 * ph) + 0.55 * math.sin(3.0 * ph) + 0.5 * math.sin(4.0 * ph)
             + 0.67 * math.sin(5.0 * ph) + 0.7 * math.sin(1.5 * ph) + 0.5 * math.sin(2.5 * ph))
        v += 0.5 * _rng.uniform(-1.0, 1.0) * math.exp(-t / 0.01)
        out.append(v * min(1.0, t / 0.004) * math.exp(-t / 0.05))
    return _finish_snes(_highpass(out, 0.1), 0.95)


# ── Basses ──

def mmx_slap_bass() -> tuple[bytes, int, dict]:
    """Slap bass (Kage's name), in 21 banks: a snap of brightness into a
    round octave-heavy sustain."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = 0.34 * math.sin(ph) + 1.0 * math.sin(2.0 * ph) + 0.41 * math.sin(3.0 * ph) + 0.24 * math.sin(4.0 * ph)
        snap = (0.8 * math.sin(6.0 * ph) + 0.5 * math.sin(9.0 * ph)) * math.exp(-t / 0.03)
        return body + snap
    return _decaying_voice(0.7, tone, amp_tau=0.5, tail_loop=True, amplitude=0.95)


def mmx_synth_bass() -> tuple[bytes, int, dict]:
    """Synth bass (Kage's name), in 13 banks, and the top of the slap line:
    the fundamental and the second partial carry the body, so that played an
    octave above the low sample it stays as full as the root under it."""
    w = 2.0 * math.pi * BASE_NOTE_HZ

    def tone(t, i):
        ph = w * i / SNES_RATE
        body = 1.0 * math.sin(ph) + 0.74 * math.sin(2.0 * ph) + 0.14 * math.sin(3.0 * ph) + 0.18 * math.sin(5.0 * ph)
        snap = (0.5 * math.sin(5.0 * ph) + 0.3 * math.sin(8.0 * ph)) * math.exp(-t / 0.03)
        return body + snap
    return _decaying_voice(0.6, tone, amp_tau=0.4, tail_loop=True, amplitude=0.95)


# ── Kit ──
# Kage's kick is a 125 ms hit with its energy on the third partial; the snare
# 188 ms, bright; the tom 94 ms with a 45 ms bloom; the open hat an 80 ms
# loop; the crash a loop with an 80 ms swell (he calls it reverse cymbal);
# the closed hat an 18 ms bright noise loop.

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
    """Closed hat: the bank's 18 ms bright noise loop, cut as a tick."""
    n = int(SNES_RATE * 0.03)
    out = [_rng.uniform(-1.0, 1.0) * math.exp(-(i / SNES_RATE) / 0.007) for i in range(n)]
    return _finish_snes(_highpass(out, 0.6), 0.7)


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
    "mmx_lead_guitar":      (mmx_lead_guitar,      {}, 58),
    "mmx_rhythm_guitar":    (mmx_rhythm_guitar,    {}, 60),
    "mmx_overdrive_guitar": (mmx_overdrive_guitar, {}, 58),
    "mmx_guitar_pad":       (mmx_guitar_pad,       {}, 54),
    "mmx_clean_guitar":     (mmx_clean_guitar,     {}, 56),
    "mmx_synth_brass":      (mmx_synth_brass,      {}, 58),
    "mmx_strings":          (mmx_strings,          {}, 56),
    "mmx_saw_pad":          (mmx_saw_pad,          {}, 54),
    "mmx_organ":            (mmx_organ,            {}, 58),
    "mmx_synth_lead":       (mmx_synth_lead,       {}, 58),
    "mmx_square":           (mmx_square,           {}, 56),
    "mmx_bright_lead":      (mmx_bright_lead,      {}, 56),
    "mmx_hollow":           (mmx_hollow,           {}, 56),
    "mmx_bell":             (mmx_bell,             {}, 52),
    "mmx_orch_hit":         (mmx_orch_hit,         {}, 60),
    "mmx_slap_bass":        (mmx_slap_bass,        {}, 64),
    "mmx_synth_bass":       (mmx_synth_bass,       {}, 64),
    "mmx_kick":             (mmx_kick,             {}, 64),
    "mmx_snare":            (mmx_snare,            {}, 62),
    "mmx_tom":              (mmx_tom,              {}, 62),
    "mmx_hat":              (mmx_hat,              {}, 50),
    "mmx_open_hat":         (mmx_open_hat,         {}, 48),
    "mmx_crash":            (mmx_crash,            {}, 52),
}

# Release family per sustaining voice (see samples.dsp.RELEASE)
RELEASE = {
    "mmx_lead_guitar": "lead", "mmx_rhythm_guitar": "lead", "mmx_overdrive_guitar": "lead",
    "mmx_guitar_pad": "strings", "mmx_clean_guitar": "keys", "mmx_synth_brass": "brass",
    "mmx_strings": "strings", "mmx_saw_pad": "pad", "mmx_organ": "organ",
    "mmx_synth_lead": "lead", "mmx_square": "lead", "mmx_bright_lead": "lead",
    "mmx_hollow": "lead", "mmx_bell": "keys", "mmx_slap_bass": "bass", "mmx_synth_bass": "bass",
}


PACK = {
        "palette": "snes",
        "label": "Mega Man X",
        # Every voice is the pack's own, built from the game's bank. Pool
        # weights follow the bank: the lead guitar, overdrive guitar, synth
        # brass, strings and organ are in nearly every song.
        "voices": {
            "lead": ["mmx_lead_guitar", "mmx_lead_guitar", "mmx_lead_guitar", "mmx_synth_brass",
                     "mmx_synth_brass", "mmx_synth_lead", "mmx_bright_lead", "mmx_square",
                     "mmx_organ", "mmx_overdrive_guitar"],
            "alt_lead": ["mmx_synth_brass", "mmx_lead_guitar", "mmx_synth_lead", "mmx_organ",
                         "mmx_bright_lead"],
            "harmony": ["mmx_rhythm_guitar", "mmx_rhythm_guitar", "mmx_guitar_pad", "mmx_strings",
                        "mmx_strings", "mmx_synth_brass", "mmx_synth_brass", "mmx_saw_pad",
                        "mmx_orch_hit", "mmx_organ", "mmx_hollow"],
            "counter": ["mmx_overdrive_guitar", "mmx_overdrive_guitar", "mmx_synth_brass",
                        "mmx_square", "mmx_synth_lead", "mmx_organ"],
            "arp": ["mmx_overdrive_guitar", "mmx_overdrive_guitar", "mmx_square", "mmx_bell",
                    "mmx_clean_guitar", "mmx_hollow"],
            "bass_heavy": ["mmx_slap_bass"],
            "bass_medium": ["mmx_slap_bass"],
            "bass_light": ["mmx_slap_bass"],
            "bass_hi": "mmx_synth_bass",
            "drums": {"kick": "mmx_kick", "snare": "mmx_snare", "hihat": "mmx_hat",
                      "tom": "mmx_tom", "crash": "mmx_crash", "open_hihat": "mmx_open_hat",
                      "rim": "snes_rim"},
        },
        "habits": {
            "tempo": {"slow": 0, "medium": 3, "fast": 3},
            "energy": {"chill": 0, "normal": 2, "intense": 3},
            "scale_family": {"minor": 3, "major": 2, "pentatonic": 1},
            "form": {"standard": 2, "aaba": 2, "short": 1, "linear": 1, "rondo": 1},
            "intro": {"riff_vamp": 4, "drum_pickup": 3, "arp_bed": 1, "pad_hook": 1},
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
