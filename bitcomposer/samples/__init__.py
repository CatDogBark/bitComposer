"""
Instrument registry. Every preset the generator can play, from the palette
modules (chip, snes, genesis) and the style packs (bitcomposer.packs, which
register their voices on import), with the loudness rules, the struck-voice
table and generate_instrument itself. Names are re-exported here so callers
keep writing samples.<name>.
"""
import math
import struct
import zlib

from .dsp import (
    _rng, SAMPLE_RATE, BASE_NOTE_HZ, _pack_samples, SNES_PERIOD, RELEASE, add_release, polish_waveform, WAVEFORM_TUNED_RATE, _rms,
)
from .chip import (
    square_wave, sawtooth_wave, triangle_wave, sine_wave, noise_white, kick_drum, snare_drum, hihat, tom_drum, crash_cymbal, open_hihat, pwm_sweep, supersaw, filtered_saw, sweep_pad, distorted_bass, pluck_bass_gen, thin_bass_gen, bright_bass_gen, kick_layered, snare_layered, hihat_metallic, pulse12_wave, square_pluck, pulse_pluck, pulse12_pluck, tri_pluck, rim_tick, WAVEFORM_POLISH, _ONE_SHOT_WAVEFORMS,
)
from .snes import (
    snes_strings, snes_brass, snes_choir, snes_flute, snes_organ, snes_synth_lead, snes_epiano, snes_bell, snes_marimba, snes_pizz, snes_harp, snes_pluck_bass, snes_slap_bass, snes_synth_bass, snes_orch_hit, snes_kick, snes_snare, snes_hat, snes_open_hat, snes_tom, snes_crash, snes_rim,
)
from .genesis import (
    fm_organ, fm_brass, fm_pad, fm_bell, fm_bass, fm_lead, fm_strings, fm_pluck, gen_lead, gen_saw_lead, gen_brass, gen_pad, gen_bell, gen_pluck, gen_slap_bass, gen_sub_bass, gen_pluck_bass, gen_kick, gen_snare, gen_hat, gen_open_hat, gen_tom, gen_crash, gen_rim,
)




# Which release each preset takes. Sustained voices only; a preset missing
# here keeps hard cuts (plucks, drums, and anything that already decays).
PRESET_RELEASE = {
    # SNES
    "snes_strings": "strings", "snes_choir": "choir", "snes_brass": "brass",
    "snes_flute": "flute", "snes_organ": "organ", "snes_synth_lead": "lead",
    "snes_epiano": "keys", "snes_bell": "keys", "snes_synth_bass": "bass",
    # Genesis
    "gen_lead": "lead", "gen_saw_lead": "lead", "gen_brass": "brass",
    "gen_pad": "pad", "gen_sub_bass": "bass", "gen_bell": "keys",
    "gen_slap_bass": "bass", "gen_pluck_bass": "bass", "gen_pluck": "lead",
    "fm_organ": "organ", "fm_pad": "pad", "fm_strings": "strings", "fm_bass": "bass",
    "fm_lead": "lead", "fm_brass": "brass", "fm_bell": "keys",
    # Chip
    "square_lead": "lead", "pulse_lead": "lead", "pulse12_lead": "lead",
    "triangle_lead": "lead", "pwm_lead": "lead", "filtered_lead": "lead",
    "saw_lead": "lead", "supersaw_lead": "pad", "sweep_lead": "pad",
    "psg_square": "psg",
    "saw_bass": "bass", "triangle_bass": "bass", "sine_bass": "bass",
    "square_bass": "bass", "distorted_bass": "bass", "filtered_bass": "bass",
    "supersaw_bass": "bass",
    "square_pluck": "lead", "pulse_pluck": "lead", "pulse12_pluck": "lead", "tri_pluck": "lead",
}


# Instrument presets: (name, generator_func, kwargs, default_volume)
INSTRUMENT_PRESETS = {
    # Melodic — classic
    "square_lead":    (square_wave,    {"duty": 0.5},  64),
    "pulse_lead":     (square_wave,    {"duty": 0.25}, 64),
    "saw_lead":       (sawtooth_wave,  {},             58),
    "triangle_lead":  (triangle_wave,  {},             64),
    "fm_bell":        (fm_bell,        {},             50),
    "fm_lead":        (fm_lead,        {},             58),
    # Melodic — extended
    "pwm_lead":       (pwm_sweep,      {},             60),
    "supersaw_lead":  (supersaw,       {},             52),
    "filtered_lead":  (filtered_saw,   {"cutoff": 0.4}, 58),
    "sweep_lead":     (sweep_pad,      {},             48),
    "fm_organ":       (fm_organ,       {},             52),
    "fm_brass":       (fm_brass,       {},             58),
    "fm_pad":         (fm_pad,         {},             44),
    "fm_strings":     (fm_strings,     {},             46),
    # Genesis — feedback FM voices, DAC drums, PSG square
    "gen_lead":       (gen_lead,       {},             56),
    "gen_saw_lead":   (gen_saw_lead,   {},             54),
    "gen_brass":      (gen_brass,      {},             56),
    "gen_pad":        (gen_pad,        {},             48),
    "gen_bell":       (gen_bell,       {},             54),
    "gen_pluck":      (gen_pluck,      {},             58),
    "gen_slap_bass":  (gen_slap_bass,  {},             64),
    "gen_sub_bass":   (gen_sub_bass,   {},             64),
    "gen_pluck_bass": (gen_pluck_bass, {},             60),
    "gen_kick":       (gen_kick,       {},             64),
    "gen_snare":      (gen_snare,      {},             58),
    "gen_hat":        (gen_hat,        {},             38),
    "gen_open_hat":   (gen_open_hat,   {},             36),
    "gen_tom":        (gen_tom,        {},             56),
    "gen_crash":      (gen_crash,      {},             46),
    "psg_square":     (square_wave,    {"duty": 0.5},  40),
    "rim":            (rim_tick,       {},             44),
    "snes_rim":       (snes_rim,       {},             44),
    "gen_rim":        (gen_rim,        {},             44),
    "fm_pluck":       (fm_pluck,       {},             56),
    # Chip — role voices
    "pulse12_lead":   (pulse12_wave,   {},             58),
    "square_pluck":   (square_pluck,   {},             60),
    "pulse_pluck":    (pulse_pluck,    {},             60),
    "pulse12_pluck":  (pulse12_pluck,  {},             58),
    "tri_pluck":      (tri_pluck,      {},             64),
    # Bass — classic
    "saw_bass":       (sawtooth_wave,  {},             64),
    "triangle_bass":  (triangle_wave,  {},             64),
    "sine_bass":      (sine_wave,      {},             64),
    "fm_bass":        (fm_bass,        {},             64),
    "square_bass":    (square_wave,    {"duty": 0.5},  58),
    # Bass — extended
    "distorted_bass": (distorted_bass, {},             62),
    "filtered_bass":  (filtered_saw,   {"cutoff": 0.2}, 64),
    "supersaw_bass":  (supersaw,       {"detune": 0.008}, 58),
    # Bass — light (high-passed, short decay, minimal low-end)
    "pluck_bass":     (pluck_bass_gen, {},              56),
    "thin_bass":      (thin_bass_gen,  {},              52),
    "bright_bass":    (bright_bass_gen, {},             50),
    # Drums — classic
    "kick":           (kick_drum,      {},             64),
    "snare":          (snare_drum,     {},             56),
    "hihat":          (hihat,          {},             40),
    "tom":            (tom_drum,       {},             56),
    "crash":          (crash_cymbal,   {},             48),
    "open_hihat":     (open_hihat,     {},             38),
    "noise":          (noise_white,    {},             32),
    # Drums — enhanced
    "kick_layered":   (kick_layered,   {},             64),
    "snare_layered":  (snare_layered,  {},             56),
    "hihat_metallic": (hihat_metallic, {},             22),
    # SNES — sampled palette (see the section above)
    "snes_strings":   (snes_strings,   {},             60),
    "snes_brass":     (snes_brass,     {},             64),
    "snes_choir":     (snes_choir,     {},             57),
    "snes_flute":     (snes_flute,     {},             64),
    "snes_organ":     (snes_organ,     {},             57),
    "snes_synth_lead": (snes_synth_lead, {},           64),
    "snes_epiano":    (snes_epiano,    {},             64),
    "snes_bell":      (snes_bell,      {},             62),
    "snes_marimba":   (snes_marimba,   {},             64),
    "snes_pizz":      (snes_pizz,      {},             64),
    "snes_harp":      (snes_harp,      {},             62),
    "snes_pluck_bass": (snes_pluck_bass, {},           64),
    "snes_slap_bass": (snes_slap_bass, {},             64),
    "snes_synth_bass": (snes_synth_bass, {},           64),
    "snes_orch_hit":  (snes_orch_hit,  {},             64),
    # FFVI orchestral set
    # Secret of Mana set
    # Secret of Evermore set
    # Mega Man X set
    "snes_kick":      (snes_kick,      {},             64),
    "snes_snare":     (snes_snare,     {},             64),
    "snes_hat":       (snes_hat,       {},             46),
    "snes_open_hat":  (snes_open_hat,  {},             44),
    "snes_tom":       (snes_tom,       {},             64),
    "snes_crash":     (snes_crash,     {},             53),
}


# Sustain-region RMS (of full scale) every looped sustaining preset is scaled
# to. 0.45 is where the sustaining SNES voices sit (strings, organ, synth
# lead 0.44; flute 0.63; brass 0.38), so that palette keeps its level; a
# square wave (0.89) comes down ~6 dB and the FM lead (0.80) ~5 dB.
LOUDNESS_TARGET = 0.45

# Struck voices (plucks, bells, e-piano, pizz, harp, marimba) carry their
# energy in the attack and loop a quiet tail, so the sustain rule sees them
# as quiet and leaves them alone (the peak cap stops the scale-up). On an
# arp, where every note is a strike, that left the SNES bell 7 dB over the
# pizz. With strike_rule=True a struck voice is scaled on the RMS of its
# first STRIKE_WINDOW seconds instead, to STRIKE_TARGET. The composer asks
# for it on the arp only: a struck lead or harmony holds notes and lives on
# its decay, and taking 4-7 dB off a bell lead would bury it, while its
# attack is already at full scale so nothing could give that back in-sample.
STRIKE_TARGET = 0.25
STRIKE_WINDOW = 0.15
# A preset is struck when its loop region is this much quieter than its
# strike, or when it does not loop at all (the SNES pizz, harp, marimba and
# plucked basses are one-shots).
STRUCK_RATIO = 0.8

# Tonal presets whose energy is in the attack (loop quieter than the strike,
# or no loop), as generate_instrument classifies them. Kept as a table so the
# composer can ask without rendering a sample; a test checks it against the
# classifier for every preset in the palettes and packs.
STRUCK_PRESETS = {
    "evm_bass",
    "evm_harp",
    "evm_kalimba",
    "evm_piano",
    "evm_pluck",
    "evm_tinker",
    "ffvi_bass",
    "ffvi_dark_bass",
    "ffvi_guitar",
    "ffvi_harp",
    "ffvi_piano",
    "ffvi_picked",
    "ffvi_sitar",
    "ffvi_tubular_bell",
    "ffvi_xylophone",
    "gen_bell",
    "gen_pluck",
    "gen_pluck_bass",
    "gen_slap_bass",
    "mana_bass",
    "mana_bass_elec",
    "mana_epiano",
    "mana_marimba",
    "mana_slap_bass",
    "mana_tubular_bell",
    "mana_vibraphone",
    "mmx_bell",
    "mmx_clean_guitar",
    "mmx_orch_hit",
    "mmx_rhythm_guitar",
    "mmx_slap_bass",
    "mmx_synth_bass",
    "pulse12_pluck",
    "pulse_pluck",
    "snes_bell",
    "snes_epiano",
    "snes_harp",
    "snes_marimba",
    "snes_pizz",
    "snes_pluck_bass",
    "snes_slap_bass",
    "snes_synth_bass",
    "square_pluck",
    "tri_pluck",
}


def is_struck(name: str) -> bool:
    return name in STRUCK_PRESETS


def harmony_family(name: str) -> str | None:
    """The family the harmony voices and levels a preset by: its release
    family, or "struck" for a struck voice that has none (the orchestra
    hit, the rhythm guitar), None for anything else."""
    fam = PRESET_RELEASE.get(name)
    if fam is None and is_struck(name):
        return "struck"
    if fam == "lead" and is_struck(name):
        return "struck"
    return fam


_PERCUSSION_WORDS = {"kick", "snare", "hat", "hihat", "tom", "crash", "rim", "noise",
                     "clap", "perc", "shaker", "cowbell", "hit", "timpani", "bassdrum", "cymbal",
                     "conga", "tambourine", "woodblock", "drum", "click", "brush", "castanet", "ping", "wash"}


# Kit voices from pack files (bitcomposer.packs.packfile), whose names are
# the pack author's and need not carry a percussion word.
PERCUSSION_PRESETS: set[str] = set()


def is_percussion(name: str) -> bool:
    """Whole name parts only: "rim" must not catch the marimba."""
    return name in PERCUSSION_PRESETS or any(part in _PERCUSSION_WORDS for part in name.split("_"))


def echo_variant(name: str, cutoff_hz: float, poles: int = 2,
                 strike_rule: bool = False) -> dict:
    """A darker copy of a preset for an echo tap.

    The SNES ran its echo repeats through a filter on every pass, so each one
    came back duller than the last. A tracker has no send effects, so a tap
    is a note copy on another channel, and the darkening lives in the sample
    it plays: a lowpass at cutoff_hz over the whole instrument, `poles`
    one-pole stages in cascade (two by default: 12 dB per octave, since one
    stage barely shades a bright brass sample).

    The loop region is filtered as a cycle (a warm-up pass, then the pass
    that is kept) so the seam stays seamless; the attack before it and the
    release tail after it are filtered in sequence from the matching state.
    Level is not restored: the filter's loss is part of the repeat's decay.
    """
    inst = generate_instrument(name, strike_rule=strike_rule)
    ints = list(struct.unpack(f"<{inst['length']}h", inst["data"]))
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff_hz / inst["rate"])
    alpha = max(0.001, min(1.0, alpha))

    def run(seg, state):
        state = list(state) if state else [0.0] * poles
        out = []
        for v in seg:
            for i in range(poles):
                state[i] += alpha * (v - state[i])
                v = state[i]
            out.append(v)
        return out, state

    looped = inst["loop"] or inst.get("sus_loop")
    ls, le = inst["loop_start"], inst["loop_end"]
    if looped and 0 <= ls < le <= len(ints):
        head, state = run(ints[:ls], None)
        _, state = run(ints[ls:le], state)          # warm up to the cycle's steady state
        loop, state = run(ints[ls:le], state)
        tail, _ = run(ints[le:], state)
        out = head + loop + tail
    else:
        out, _ = run(ints, None)
    variant = dict(inst)
    variant["data"] = _pack_samples([max(-32768, min(32767, int(round(v)))) for v in out])
    return variant


def generate_instrument(name: str, strike_rule: bool = False) -> dict:
    """Generate a named instrument.

    strike_rule: normalise a struck voice on its attack (see STRIKE_TARGET);
    off, struck voices keep their natural peak-capped level.

    Returns {"data", "length", "volume", "rate", "loop", "loop_start",
    "loop_end"} — everything an ITSample needs. Waveform presets loop over
    their whole length; one-shots do not loop; SNES voices carry their own
    loop points.
    """
    if name not in INSTRUMENT_PRESETS:
        raise ValueError(f"Unknown instrument: {name}")
    func, kwargs, vol = INSTRUMENT_PRESETS[name]
    _rng.seed(zlib.crc32(name.encode()))
    result = func(**kwargs)
    if len(result) == 3:
        data, length, meta = result
        meta = dict(meta)
        meta.setdefault("loop_start", 0); meta.setdefault("loop_end", length)
    else:
        data, length = result
        one_shot = name in _ONE_SHOT_WAVEFORMS
        loop_start, loop_end = 0, length
        if not one_shot and name in WAVEFORM_POLISH:
            cutoff, attack = WAVEFORM_POLISH[name]
            data, length, loop_start, loop_end = polish_waveform(data, length, cutoff, attack)
        meta = {"rate": SAMPLE_RATE if one_shot else WAVEFORM_TUNED_RATE,
                "loop": not one_shot, "loop_start": loop_start, "loop_end": loop_end}
    family = PRESET_RELEASE.get(name)
    gain, struck, onset_ms = 1.0, False, 0.0
    if not is_percussion(name):
        # Equal loudness: scale the sample data so like voices sit at like
        # levels. Sustaining voices (loop as loud as the attack) go by their
        # loop RMS to LOUDNESS_TARGET; struck voices, when asked, by the RMS
        # of their first STRIKE_WINDOW to STRIKE_TARGET. The data is scaled
        # (not the default volume) because a volume column on a note
        # overrides the default. Scaling up stops where the peak would clip,
        # which is what leaves a struck voice alone under the sustain rule.
        ints = list(struct.unpack(f"<{length}h", data))
        peak = max(abs(v) for v in ints) / 32767.0
        strike = _rms(ints[:max(1, int(meta["rate"] * STRIKE_WINDOW))])
        loop_rms = _rms(ints[meta["loop_start"]:meta["loop_end"]] or ints)
        struck = (not meta.get("loop")) or loop_rms < STRUCK_RATIO * strike
        onset_ms = _onset_ms(ints, meta["rate"])
        if struck and strike_rule:
            target, rms = STRIKE_TARGET, strike
        elif meta.get("loop"):
            target, rms = LOUDNESS_TARGET, loop_rms
        else:
            target, rms = 1.0, 0.0            # one-shot, left as drawn
        if rms > 1e-4 and peak > 0:
            k = min(target / rms, 0.98 / peak)
            if abs(k - 1.0) > 0.02:
                data = _pack_samples([max(-32768, min(32767, int(v * k))) for v in ints])
                gain = k
    if family and meta.get("loop"):
        data, length, meta = add_release(data, length, meta, RELEASE[family])
    return {
        "data": data, "length": length, "volume": vol,
        "rate": meta["rate"], "loop": meta.get("loop", False),
        "loop_start": meta.get("loop_start", 0), "loop_end": meta.get("loop_end", length),
        "sus_loop": meta.get("sus_loop", False), "release": meta.get("release", 0.0),
        "gain": gain, "struck": struck, "onset_ms": onset_ms,
    }


def _onset_ms(ints, rate: int, window_s: float = 0.004, span_s: float = 0.5) -> float:
    """The voice's attack: time to reach 80% of its loudest 4 ms window in
    the first half second. A struck voice reads 0; a string swell its swell.
    The harmony sets a stab's length from it (harmony.stab_rows)."""
    win = max(1, int(rate * window_s))
    span = min(len(ints), int(rate * span_s))
    levels = [_rms(ints[i:i + win]) for i in range(0, max(win, span - win + 1), win)]
    if not levels:
        return 0.0
    top = max(levels)
    for k, lvl in enumerate(levels):
        if lvl >= 0.8 * top:
            return 1000.0 * k * win / rate
    return 0.0


def register_presets(presets: dict, releases: dict) -> None:
    """A style pack adds its voices on import (see bitcomposer.packs)."""
    INSTRUMENT_PRESETS.update(presets)
    PRESET_RELEASE.update(releases)


def register_sample_voice(name: str, data: bytes, length: int, meta: dict, volume: int,
                          release: str | None = None, percussion: bool = False) -> dict:
    """A voice from a sample file (a pack file's own voice): 16-bit mono
    data with its rate (C5Speed) and loop in meta. It joins the tables the
    composer asks without rendering: the release family, the kit voices,
    and STRUCK_PRESETS, from the same classifier generate_instrument uses.
    Returns its generate_instrument result."""
    meta = dict(meta)
    INSTRUMENT_PRESETS[name] = (lambda: (data, length, dict(meta)), {}, volume)
    if release:
        PRESET_RELEASE[name] = release
    else:
        PRESET_RELEASE.pop(name, None)
    if percussion:
        PERCUSSION_PRESETS.add(name)
    else:
        PERCUSSION_PRESETS.discard(name)
    STRUCK_PRESETS.discard(name)
    inst = generate_instrument(name)
    if inst["struck"]:
        STRUCK_PRESETS.add(name)
    return inst


def unregister_voice(name: str) -> None:
    for table in (INSTRUMENT_PRESETS, PRESET_RELEASE):
        table.pop(name, None)
    PERCUSSION_PRESETS.discard(name)
    STRUCK_PRESETS.discard(name)
