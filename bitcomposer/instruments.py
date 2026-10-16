"""Palettes, the per-song instrument draw (with the contrast rule) and the
sample set a song carries."""
import random

from . import samples as smp
from .it_format import ITSample
from . import pattern as pattern_mod
from .packs import PACKS


# Per-style instrument pools. "chip" is the original waveform palette — square
# and triangle leads over synthesized drums, which is really a NES/Game Boy
# sound. "snes" is the sampled palette: strings, brass, choir, plucks and a
# gated drum kit, the way the SPC700 actually worked. "genesis" is FM.
PALETTES = {
    # Chip roles follow the hardware: pulse leads, triangle or thin pulse
    # underneath, decaying pulse blips for the arp at a different duty from
    # the lead (enforced in _pick_instruments), triangle or square bass.
    "chip": {
        "lead": ["square_lead", "pulse_lead", "pwm_lead", "filtered_lead"],
        "harmony": ["triangle_lead", "pulse12_lead", "filtered_lead"],
        "arp": ["pulse_pluck", "square_pluck", "pulse12_pluck", "tri_pluck"],
        "bass_heavy": ["triangle_bass", "sine_bass", "square_bass", "saw_bass", "filtered_bass"],
        "bass_medium": ["square_bass", "triangle_bass", "filtered_bass"],
        "bass_light": ["pluck_bass", "thin_bass", "bright_bass"],
        "alt_lead": ["square_lead", "pulse_lead", "triangle_lead", "pwm_lead", "filtered_lead"],
        "drums": None,  # chosen below: classic or layered kit
    },
    "snes": {
        "lead": ["snes_flute", "snes_brass", "snes_synth_lead", "snes_epiano",
                 "snes_strings", "snes_bell", "snes_choir"],
        "harmony": ["snes_strings", "snes_choir", "snes_organ", "snes_epiano", "snes_brass"],
        "arp": ["snes_pizz", "snes_harp", "snes_marimba", "snes_bell", "snes_epiano"],
        "bass_heavy": ["snes_pluck_bass", "snes_synth_bass", "snes_slap_bass"],
        "bass_medium": ["snes_pluck_bass", "snes_slap_bass", "snes_synth_bass"],
        "bass_light": ["snes_slap_bass", "snes_pizz", "snes_marimba"],
        "alt_lead": ["snes_flute", "snes_brass", "snes_synth_lead", "snes_epiano",
                     "snes_bell", "snes_strings"],
        "drums": {"kick": "snes_kick", "snare": "snes_snare", "hihat": "snes_hat",
                  "tom": "snes_tom", "crash": "snes_crash", "open_hihat": "snes_open_hat",
                  "rim": "snes_rim"},
    },
    # Genesis roles: feedback-FM leads and brass, FM pad or organ underneath
    # with the PSG square as an occasional thin voice, FM blips for arps,
    # slap/sub FM basses, and 8-bit DAC drums. See samples.py.
    "genesis": {
        "lead": ["gen_lead", "gen_saw_lead", "gen_brass", "gen_bell"],
        "harmony": ["gen_pad", "gen_pad", "gen_pad", "fm_organ", "psg_square"],
        "arp": ["gen_pluck", "gen_pluck", "gen_pluck", "gen_bell", "gen_bell", "psg_square"],
        "bass_heavy": ["gen_slap_bass", "gen_slap_bass", "gen_sub_bass", "fm_bass"],
        "bass_medium": ["gen_slap_bass", "gen_sub_bass", "fm_bass"],
        "bass_light": ["gen_pluck_bass", "gen_pluck_bass", "gen_sub_bass"],
        "alt_lead": ["gen_lead", "gen_saw_lead", "gen_brass", "gen_bell"],
        "drums": {"kick": "gen_kick", "snare": "gen_snare", "hihat": "gen_hat",
                  "tom": "gen_tom", "crash": "gen_crash", "open_hihat": "gen_open_hat",
                  "rim": "gen_rim"},
    },
}


# Pulse duty per preset, so a chip arp never shares the lead's duty — two
# channels at the same duty were how the palette ended up sounding like one.
PULSE_DUTY = {
    "square_lead": 0.5, "square_pluck": 0.5, "square_bass": 0.5,
    "pulse_lead": 0.25, "pulse_pluck": 0.25,
    "pulse12_lead": 0.125, "pulse12_pluck": 0.125,
}


def _weighted(choices: list[str], weights: dict | None) -> str:
    """random.choice, or a pack-weighted choice when the pack has an opinion.

    A pack's weights replace the plain pool outright (a drone bass is not in
    any plain pool), so the draw is over the names the pack weights above
    zero; a pack that weights everything at zero falls back to the plain pool.
    """
    if not weights:
        return random.choice(choices)
    pool = [c for c, w in weights.items() if w > 0]
    if not pool:
        return random.choice(choices)
    return random.choices(pool, [weights[c] for c in pool], k=1)[0]


def _pick_instruments(style: str, bass_weight: str = "heavy",
                      pack: str | None = None) -> dict[str, str]:
    """Pick a random instrument set for the song from the style's palette,
    or from the pack's voices when the song has a pack."""
    pal = dict(PALETTES[style])
    if pack:
        pal.update(PACKS[pack]["voices"])
    bass_choices = pal.get(f"bass_{bass_weight}", pal["bass_heavy"])

    lead = random.choice(pal["lead"])
    lead_duty = PULSE_DUTY.get(lead)

    def distinct(pool):
        out = [n for n in pool if n != lead
               and not (lead_duty is not None and PULSE_DUTY.get(n) == lead_duty)]
        return out or pool

    harmony = random.choice(distinct(pal["harmony"]))
    bass = random.choice(bass_choices)
    # The arp must also differ from the harmony, or two of the three upper
    # parts share one timbre — the thin PSG square on both was the usual case.
    arp = random.choice([a for a in distinct(pal["arp"]) if a != harmony]
                        or distinct(pal["arp"]))

    if pal["drums"]:
        drums = dict(pal["drums"])
    else:
        # Enhanced drums: 40% chance of using layered drums
        layered = random.random() < 0.4
        drums = {
            "kick": "kick_layered" if layered else "kick",
            "snare": "snare_layered" if layered else "snare",
            "hihat": "hihat_metallic" if layered else "hihat",
            "tom": "tom", "crash": "crash", "open_hihat": "open_hihat", "rim": "rim",
        }

    # Contrast: three sustaining voices in overlapping registers (lead, chord
    # tones, arp) mask each other, and a pack's borrowed organ under a synth
    # lead and a pulse arp was the clearest case. If none of the three is
    # struck and the harmony is not a pad-like family, redraw the harmony
    # from the pool's struck or pad-like voices when it has any.
    soft = ("pad", "strings", "choir", "brass")     # brass stabs cut through on their own
    if not (smp.is_struck(lead) or smp.is_struck(arp) or smp.is_struck(harmony)) \
            and smp.PRESET_RELEASE.get(harmony) not in soft:
        contrast = [h for h in distinct(pal["harmony"])
                    if smp.is_struck(h) or smp.PRESET_RELEASE.get(h) in soft]
        if contrast:
            harmony = random.choice(contrast)
    out = {"melody": lead, "harmony": harmony, "bass": bass, "arp": arp, **drums}
    if isinstance(pal.get("bass_hi"), str):
        out["bass_hi"] = pal["bass_hi"]          # the bass line's upper-register sample
    if pal.get("counter"):
        out["counter"] = random.choice([c for c in pal["counter"] if c != harmony]
                                       or pal["counter"])
    return out


def _make_sample(name: str, strike_rule: bool = False) -> ITSample:
    return _sample_from_inst(name, smp.generate_instrument(name, strike_rule=strike_rule))


def _sample_from_inst(name: str, inst: dict) -> ITSample:
    return ITSample(
        name=name.replace("_", " ").title(),
        filename=name[:12],
        data=inst["data"],
        length=inst["length"],
        loop=inst["loop"],
        loop_start=inst["loop_start"],
        loop_end=inst["loop_end"],
        sus_loop=inst.get("sus_loop", False),
        sus_loop_start=inst["loop_start"],
        sus_loop_end=inst["loop_end"],
        default_volume=inst["volume"],
        c5_speed=inst["rate"],
    )


def _register_releases(samples: list[ITSample]) -> None:
    """Tell the pattern layer which samples end with a release (note-off)."""
    pattern_mod.RELEASE_INSTRUMENTS.clear()
    pattern_mod.RELEASE_INSTRUMENTS.update(
        i + 1 for i, smp in enumerate(samples) if smp.sus_loop)


# Roles whose struck voices are normalised on their attack rather than left
# at their natural level: the arp, where every note is a strike.
STRIKE_RULE_ROLES = {"arp"}


def _build_samples(instruments: dict[str, str]
                   ) -> tuple[list[ITSample], dict[str, int], dict[str, bool]]:
    """Generate ITSample objects for all instruments.

    Returns (samples, sample_map, struck): sample_map maps an instrument role
    to a 1-based sample index, roles sharing a preset (and the same loudness
    rule) share a sample; struck says per role whether the voice is a struck
    one (the mix needs it for the arp).
    """
    samples: list[ITSample] = []
    seen: dict[tuple[str, bool], tuple[int, bool]] = {}
    sample_map: dict[str, int] = {}
    struck: dict[str, bool] = {}

    for key, name in instruments.items():
        rule = key in STRIKE_RULE_ROLES
        if (name, rule) not in seen:
            inst = smp.generate_instrument(name, strike_rule=rule)
            samples.append(_sample_from_inst(name, inst))
            seen[(name, rule)] = (len(samples), bool(inst.get("struck")))  # 1-based
        sample_map[key], struck[key] = seen[(name, rule)]

    return samples, sample_map, struck
