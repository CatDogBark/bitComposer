"""
Procedural song composer.

Generates complete songs by combining music theory, instrument samples,
and pattern generation into playable Impulse Tracker modules.
"""

import random
import zlib

from . import __version__
from . import theory
from . import names
from . import samples as smp
from . import structure as struct
from .it_format import (
    ITSample, ITPattern, ITNote, midi_to_it_note, NOTE_CUT,
    write_it_file, bpm_to_it_tempo, it_tempo_to_bpm,
)
from . import pattern as pattern_mod
from .pattern import (
    CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP,
    CH_ECHO1, CH_ECHO2, CH_ECHO_HARMONY, CH_ECHO_ARP, CH_ECHO_ALL, CHANNEL_ROLES,
    NUM_CHANNELS, ROWS_PER_PATTERN, ROWS_PER_BAR, ROWS_PER_BEAT,
    humanize_volume, apply_notes_to_pattern, apply_vibrato,
    apply_portamento, apply_harmony_fade, apply_fade, apply_echo_taps, apply_echo_spill_taps,
    apply_sustain_safety_net, silence_inactive_channels,
    apply_chord_arpeggio, end_note,
)
from .drums import pick_grooves, pick_fill, render_drums
from .packs import PACKS, PACK_NAMES, pack_weights, pack_value
from .melody import (
    generate_motif, vary_motif, generate_melody,
    generate_counter_melody, add_melody_cuts,
)
from .harmony import generate_harmony_timeline
from .bass import generate_bass_timeline, pick_section_bass
from .arp import pick_figures, generate_arp


STYLES = ["chip", "snes", "genesis"]
# Chance that a snes song draws a style pack (packs.PACKS) when --pack random.
PACK_CHANCE = 0.5

# Echo, modelled on the SNES echo unit's result rather than its wiring:
# repeats on a beat fraction (three rows is a dotted eighth at four rows to
# the beat), each one quieter by the feedback and darker through a lowpass,
# one delay for the whole song, drums and bass dry. The hardware had one
# on/off bit per voice; we send each part at its own level: the lead wet,
# the harmony and arp lighter. A tap's channel may be shared (lead taps 1
# and 3; both harmony taps) and pattern.plan_echo lets the louder win.
ECHO_TAP_CUTOFF_HZ = (4000, 2000, 1000)   # two-pole lowpass on the sample each tap plays
# Per-song echo settings, drawn from their own stream (song_salt ^ 0xEC40) so
# a seed's arrangement does not move when they change. Delay in rows is picked
# for the tempo so the repeat stays a musical fraction in a 180-450 ms band:
# fast songs favour the dotted eighth and quarter, slow songs the eighth.
# "slap" is the Mega Man X echo: 48 ms, under a row, written as a tick delay
# (SDx) on the copy's note row instead of a pan, so it takes the channel's pan.
ECHO_DELAYS = {"eighth": 2, "dotted": 3, "quarter": 4, "slap": 0.5}
ECHO_DELAY_WEIGHTS = [        # (min bpm, {name: weight})
    (140, {"eighth": 1, "dotted": 5, "quarter": 4}),
    (100, {"eighth": 2, "dotted": 6, "quarter": 2}),
    (0,   {"eighth": 5, "dotted": 4, "quarter": 1}),
]
ECHO_FEEDBACK_RANGE = (0.3, 0.6)    # each further repeat relative to the last
ECHO_WET_WEIGHTS = {"light": 1, "normal": 2, "wet": 1}
# How the repeats sit in the stereo field. "bounce" alternates sides per tap,
# an effect the ear files as an effect. "centre" puts every repeat under its
# source, on the source's own side: the hardware's echo came back on both
# sides at once, behind the voice, and reads as a room. An earlier "spread"
# mode put every repeat hard on the far side of the part, and a copy arriving
# a quarter second late from another direction is heard as a second player
# coming in late (Sunlit Expanse, Veiled Meridian), so it is gone. Pans are
# IT Xxx values (0-255); the sources sit at melody 128, harmony 80/128/176,
# arp 160 (DEFAULT_CHANNEL_PANS, 0-64, times 4).
ECHO_STEREO_WEIGHTS = {"bounce": 3, "centre": 2}
ECHO_PANS = {
    "bounce": {"melody": (40, 215, 40), "harmony": ((200, 56), (56, 200), (56, 200)), "arp": (60, 200)},
    "centre": {"melody": (128, 128, 128), "harmony": ((80, 80), (128, 128), (176, 176)), "arp": (160, 160)},
}
# The hardware echoed at one level all song; we open it where the texture is
# thin and pull it back where the arp and harmony fill the space.
ECHO_SECTION_GAIN = {"intro": 1.3, "bridge": 1.3, "outro": 1.25, "verse": 1.0, "chorus": 0.7}
# Per sent role: first-repeat level (fraction of the part) and tap channels.
# Harmony has three source channels, one return channel each.
ECHO_SENDS = {
    "melody": (0.5, (CH_ECHO1, CH_ECHO2, CH_ECHO1)),
    "harmony": (0.3, None),                       # per voice: (ch, ch)
    "arp": (0.35, CH_ECHO_ARP),
}
# --echo-wet scales every send; "random" is "normal" until the per-song
# wetness pass (stage three) draws it.
ECHO_WETNESS = {"light": 0.6, "normal": 1.0, "wet": 1.5, "random": 1.0}
# Per-note send: the hardware echoed everything a voice played; we send held
# notes (>= 4 rows, a quarter note) and phrase endings (a rest of >= 2 rows
# follows) and leave fast runs dry, so the tail reads as a tail.
ECHO_SEND_HOLD = 4
ECHO_SEND_REST = 2
# The arp sends only its accented steps (strong and normal, not weak: arp.py
# writes them at 1.0 / 0.8 / 0.62 of the arp level), and the whole arp send
# tapers with tempo: full to ECHO_ARP_FULL_BPM, gone by ECHO_ARP_OFF_BPM. At
# 180 BPM a dotted-eighth repeat of an eighth-note pizzicato landed one row
# after every pluck and the arp turned into a stream of ticks.
ECHO_ARP_ACCENT = 0.7
ECHO_ARP_FULL_BPM = 130
ECHO_ARP_OFF_BPM = 170

# How harmony notes decay after their note-on, per voicing: (slide, rows to
# hold first). stabs and rhythmic are short hits, so a per-tick slide from
# the start is right. sustain is a pad: it holds for most of its 32-row
# interval and then takes a fine (per-row) slide down into the next hit.
HARMONY_FADE = {"stabs": (0x02, 0), "rhythmic": (0x03, 0), "sustain": (0xF2, 18),
                "ostinato": (0x03, 0), "pulse": (0x04, 0)}

# Chance that a pattern changes chord at its halfway point, by section type.
HALF_PATTERN_CHANGE = {
    "intro": 0.2, "verse": 0.5, "chorus": 0.55, "bridge": 0.6, "outro": 0.3,
}


def _content_seed(song_salt: int, group: str, chord_idx: int) -> int:
    """Stable per-(reuse group, chord) seed so repeats generate the same music.

    crc32 rather than hash() because str hashing is salted per process, which
    would make -s deterministic within a run but not across runs.
    """
    return song_salt ^ zlib.crc32(f"{group}:{chord_idx}".encode())


def _energy_tier(energy: float) -> int:
    """Bucket section energy to 0.2-wide tiers.

    Sections a hair apart on the energy curve (chorus at 0.85 and 0.90) render
    close enough to share a pattern; a final chorus at 1.0 lands in its own
    tier and gets its own louder copy of the same music.
    """
    return round(energy * 5)


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


def _echo_label(use_echo: bool, echo_wet: str) -> str:
    if not use_echo:
        return ""
    return " + echo" if echo_wet == "normal" else f" + echo ({echo_wet})"


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
    soft = ("pad", "strings", "choir")
    if not (smp.is_struck(lead) or smp.is_struck(arp) or smp.is_struck(harmony)) \
            and smp.PRESET_RELEASE.get(harmony) not in soft:
        contrast = [h for h in distinct(pal["harmony"])
                    if smp.is_struck(h) or smp.PRESET_RELEASE.get(h) in soft]
        if contrast:
            harmony = random.choice(contrast)
    out = {"melody": lead, "harmony": harmony, "bass": bass, "arp": arp, **drums}
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


class _EchoBus:
    """The song's echo: the sends, their taps and the darker samples they play.

    Each tap has its own lowpass cutoff, so each preset that passes through
    the echo gets one variant sample per distinct cutoff, made on first use
    (the alternate lead arrives mid-song). sends() yields what
    pattern.apply_echo_taps wants per source channel: (src, taps, hold, rest)
    with taps = [(channel, delay, level, {source instrument: variant})].
    """

    def __init__(self, samples: list[ITSample], wet: float = 1.0, delay: float = 3,
                 feedback: float = 0.5, stereo: str = "bounce", arp_scale: float = 1.0,
                 speed: int = 6):
        self.samples = samples
        self.wet, self.delay, self.feedback, self.stereo = wet, delay, feedback, stereo
        self.arp_scale, self.speed = arp_scale, speed
        self._variants: dict[tuple[str, float, bool], int] = {}
        self._maps: list[dict[int, int]] = [dict() for _ in ECHO_TAP_CUTOFF_HZ]

    def add_source(self, src_idx: int, preset: str, strike_rule: bool = False) -> None:
        if src_idx in self._maps[0]:
            return
        for k, cutoff in enumerate(ECHO_TAP_CUTOFF_HZ):
            key = (preset, cutoff, strike_rule)
            if key not in self._variants:
                inst = smp.echo_variant(preset, cutoff, strike_rule=strike_rule)
                self.samples.append(_sample_from_inst(f"{preset}_echo{int(cutoff) // 1000}k", inst))
                self._variants[key] = len(self.samples)
            self._maps[k][src_idx] = self._variants[key]
        _register_releases(self.samples)

    def _taps(self, level: float, channels, pans, gain: float = 1.0):
        taps = []
        for k, ch in enumerate(channels):
            lvl = min(1.0, level * self.wet * gain) * self.feedback ** k
            if lvl < 0.08:
                break                         # below this a repeat is not heard
            total = self.delay * (k + 1)
            rows = int(total)
            ticks = int(round((total - rows) * self.speed))
            if ticks >= self.speed:
                rows, ticks = rows + 1, 0
            if ticks:
                taps.append((ch, rows, lvl, self._maps[k], None, ticks))
            else:
                taps.append((ch, rows, lvl, self._maps[k], pans[k]))
        return taps

    def sends(self, sec_type: str = "verse") -> list[tuple[int, list, int, int, float]]:
        """(source channel, taps, hold, rest, accent) for every sent part in a section."""
        gain = ECHO_SECTION_GAIN.get(sec_type, 1.0)
        pans = ECHO_PANS[self.stereo]
        out = [(CH_MELODY, self._taps(*ECHO_SENDS["melody"], pans["melody"], gain),
                ECHO_SEND_HOLD, ECHO_SEND_REST, 0.0)]
        level, _ = ECHO_SENDS["harmony"]
        for v, (src, ret) in enumerate(zip((CH_HARMONY, CH_HARMONY2, CH_HARMONY3), CH_ECHO_HARMONY)):
            out.append((src, self._taps(level, (ret, ret), pans["harmony"][v], gain), 0, 0, 0.0))
        arp_level, arp_channels = ECHO_SENDS["arp"]
        out.append((CH_ARP, self._taps(arp_level * self.arp_scale, arp_channels, pans["arp"], gain),
                    0, 0, ECHO_ARP_ACCENT))
        return out

    def describe(self) -> str:
        name = next(n for n, rows in ECHO_DELAYS.items() if rows == self.delay)
        if name == "slap":
            return f"slap delay, feedback {self.feedback:.2f}, {self.stereo}"
        return f"{name} delay, feedback {self.feedback:.2f}, {self.stereo}"


def _pick_section_motif(sec_type: str, use_phrased: bool,
                        chorus_motif, verse_motif, bridge_motif,
                        rng: random.Random | None = None, scale_size: int = 7) -> dict | None:
    """Pick the appropriate motif for a section type."""
    if not use_phrased:
        return None
    if sec_type == "chorus":
        return chorus_motif
    elif sec_type == "verse":
        return verse_motif
    elif sec_type == "bridge":
        return bridge_motif
    else:
        # Outro/tag: a fresh motif on the melody's own stream, so its draws
        # never touch the arrangement.
        r = rng or random
        return generate_motif(length=r.choice([3, 4]), rng=rng, scale_size=scale_size)


# Related keys a section can move to, as (semitone shift, scale family).
# "relative" is the relative major of a minor key or the relative minor of a
# major one — the move game composers reach for at a chorus or a bridge; the
# old +1 semitone chorus was the truck-driver key change and is gone.
RELATIVE = {
    "natural_minor": (3, "major"), "harmonic_minor": (3, "major"), "dorian": (3, "major"),
    "phrygian": (3, "major"), "minor_pentatonic": (3, "major_pentatonic"),
    "major": (-3, "natural_minor"), "mixolydian": (-3, "natural_minor"),
    "major_pentatonic": (-3, "minor_pentatonic"),
}


def plan_keys(scale_name: str, keys: str = "moving") -> dict[str, tuple[int, str]]:
    """Per section type: (semitone shift from the home key, scale name).

    Verses and themes stay home. A chorus stays home half the time, goes to
    the relative key a third of the time, or lifts to the subdominant. A
    bridge most often moves — that is what a bridge is for — to the relative
    key or the subdominant.

    keys="home" pins every section to the home key. The moving plan trades
    consistency for the chance of a striking song, which is right for a
    generator you browse; a loop that has to sit under a game scene for ten
    minutes, a track that must match a fixed-key stinger, or an A/B test of
    anything else in the engine all want the stable version.
    """
    rel_shift, rel_scale = RELATIVE.get(scale_name, (0, scale_name))
    home = (0, scale_name)
    # Draw either way, so a seed makes the same song with the keys pinned
    # apart from the key moves themselves.
    chorus = random.choices([home, (rel_shift, rel_scale), (5, scale_name)], weights=[50, 32, 18], k=1)[0]
    bridge = random.choices([home, (rel_shift, rel_scale), (5, scale_name)], weights=[40, 35, 25], k=1)[0]
    if keys == "home":
        chorus = bridge = home
    return {"verse": home, "chorus": chorus, "bridge": bridge, "intro": home, "outro": home}


def _chord_segments(key: int, scale_name: str, scale_notes: list[int],
                    entries: list, next_entry, sec_type: str,
                    cadence_root: int | None = None) -> list[tuple]:
    """Chord timeline for one pattern: [(start_row, end_row, root, type, notes)].

    `entries` holds one chord (normal harmonic rhythm) or two (compact, two
    bars each). With one chord, HALF_PATTERN_CHANGE odds move the back two
    bars to a related chord (theory.secondary_chord). With cadence_root set
    — the root the next section opens on — the back half becomes that
    root's dominant instead, so the section ends with a V that resolves into
    the next one.
    """
    def seg(start, end, e):
        _, chord_type, _ = theory.unpack_chord(e)
        root = theory.chord_root_for(key, scale_notes, e)
        return (start, end, root, chord_type, theory.build_chord(root, chord_type))

    half = ROWS_PER_PATTERN // 2
    if cadence_root is not None:
        dom = cadence_root + 7
        while dom > key + 12:
            dom -= 12
        ctype = "power" if "pentatonic" in scale_name else "major"
        return [seg(0, half, entries[0]), (half, ROWS_PER_PATTERN, dom, ctype, theory.build_chord(dom, ctype))]
    if len(entries) >= 2:
        return [seg(0, half, entries[0]), seg(half, ROWS_PER_PATTERN, entries[1])]
    entry = entries[0]
    if random.random() < HALF_PATTERN_CHANGE.get(sec_type, 0.4):
        second = theory.secondary_chord(scale_name, entry, next_entry)
        return [seg(0, half, entry), seg(half, ROWS_PER_PATTERN, second)]
    return [seg(0, ROWS_PER_PATTERN, entry)]


def _compose_pattern(*, scale_notes, segments, layers, sec_type, section_energy,
                     section_density, section_bass, sample_map,
                     melody_sample, use_phrased, section_motif, melody_rng,
                     chord_idx, is_answer,
                     voicing_style, num_harmony_voices,
                     vibrato_speed, vibrato_depth,
                     bass_weight, use_bass_porta, porta_speed,
                     arp_figure, arp_colour, groove, drum_fill, breakdown,
                     n_patterns, is_ending, ending_style,
                     swing_amount, speed, bpm, is_intro, echo_sends,
                     pickup_root=None, counter_chance=0.3, hat_stroke=1.0,
                     crash_chance=1.0, fill_crash=True, kit_rng=None,
                     power_chords=False) -> ITPattern:
    """Compose a single pattern with all layers."""
    pat = ITPattern(rows=ROWS_PER_PATTERN, channels=NUM_CHANNELS)
    melody = []

    # The timeline in the shapes each generator wants.
    chord_notes = segments[0][4]                       # the pattern's main chord
    melody_timeline = [(s, notes) for s, _, _, _, notes in segments]
    harmony_segments = [(s, e, notes) for s, e, _, _, notes in segments]
    if power_chords:
        # Root, fifth, octave: the guitarist's chord, no third.
        harmony_segments = [(s, e, [root, root + 7, root + 12]) for s, e, root, _, _ in segments]
    bass_segments = [(s, e, root, ctype) for s, e, root, ctype, _ in segments]

    # Scale volumes by section energy
    melody_vol = int(42 * section_energy)
    harmony_vol = int(22 * section_energy)
    arp_vol = int(36 * section_energy)
    harmony_fade, harmony_hold = HARMONY_FADE.get(voicing_style, (0x02, 0))

    # ── Melody ──
    if layers["melody"]:
        # The melody has its own random stream, seeded from the pattern's
        # content seed, so the arrangement around it does not move when the
        # melody code changes. Register follows section energy: verses low,
        # choruses high.
        melody = generate_melody(
            scale_notes, chord_notes, ROWS_PER_PATTERN, section_density,
            motif=section_motif, is_answer=is_answer, phrased=use_phrased,
            chord_timeline=melody_timeline, rng=melody_rng,
            register=0.2 + 0.7 * max(0.0, min(1.0, (section_energy - 0.5) / 0.5)),
        )
        apply_notes_to_pattern(
            pat, CH_MELODY, melody, melody_sample,
            volume=melody_vol, humanize=True, rng=melody_rng,
        )
        apply_vibrato(pat, CH_MELODY, melody,
                      speed=vibrato_speed, depth=vibrato_depth)

    # ── Harmony ──
    if layers["harmony"]:
        harmony_channels = [CH_HARMONY, CH_HARMONY2, CH_HARMONY3]

        if melody and sec_type in ("chorus", "bridge") and random.random() < counter_chance:
            counter = generate_counter_melody(
                scale_notes, chord_notes, melody, ROWS_PER_PATTERN, rng=melody_rng)
            counter = add_melody_cuts(counter, ROWS_PER_PATTERN, max_sustain=8)
            apply_notes_to_pattern(
                pat, CH_HARMONY, counter, sample_map.get("counter", sample_map["harmony"]),
                volume=int(20 * section_energy), humanize=True, rng=melody_rng,
            )
            apply_harmony_fade(pat, CH_HARMONY, counter, fade_rate=harmony_fade,
                               hold_rows=harmony_hold)
            voices = generate_harmony_timeline(
                harmony_segments, voicing=voicing_style,
                num_voices=min(2, num_harmony_voices),
            )
            for v_idx, voice_notes in enumerate(voices):
                if v_idx + 1 < len(harmony_channels):
                    ch = harmony_channels[v_idx + 1]
                    apply_notes_to_pattern(
                        pat, ch, voice_notes,
                        sample_map["harmony"],
                        volume=humanize_volume(int(18 * section_energy), 4),
                        humanize=True,
                    )
                    apply_harmony_fade(pat, ch, voice_notes, fade_rate=harmony_fade,
                                       hold_rows=harmony_hold)
        else:
            voices = generate_harmony_timeline(
                harmony_segments, voicing=voicing_style,
                num_voices=num_harmony_voices,
            )
            for v_idx, voice_notes in enumerate(voices):
                if v_idx < len(harmony_channels):
                    ch = harmony_channels[v_idx]
                    vol = harmony_vol if v_idx == 0 else int(18 * section_energy)
                    apply_notes_to_pattern(
                        pat, ch, voice_notes,
                        sample_map["harmony"],
                        volume=humanize_volume(vol, 4),
                        humanize=True,
                    )
                    # A lone voice cannot state a chord on its own, so let J
                    # arpeggiate it into one. With three voices the real
                    # stack already does the job.
                    if num_harmony_voices == 1:
                        for s, e, notes in harmony_segments:
                            apply_chord_arpeggio(
                                pat, ch, [(r, n) for r, n in voice_notes if s <= r < e],
                                notes)
                    apply_harmony_fade(pat, ch, voice_notes, fade_rate=harmony_fade,
                                       hold_rows=harmony_hold)

    # ── Bass ──
    if layers["bass"]:
        # Keep the bass present but not relentless: even at full energy a few
        # off-beats drop out, and quiet sections thin further.
        bass = generate_bass_timeline(bass_segments, section_bass,
                                      weight=bass_weight,
                                      density=0.6 + 0.35 * section_energy)
        # Volume-column values are 0-64. The old 150/100 for medium/light were
        # not volumes at all: in the IT volume column 150 is a pan command and
        # 100 a volume slide down, which left light basses nearly silent.
        bass_vol = {"heavy": 255, "medium": 52, "light": 44}.get(bass_weight, 255)
        if use_bass_porta and len(bass) > 1:
            apply_portamento(
                pat, CH_BASS, bass, sample_map["bass"],
                volume=bass_vol, porta_speed=porta_speed, humanize=False,
            )
        else:
            apply_notes_to_pattern(
                pat, CH_BASS, bass, sample_map["bass"],
                volume=bass_vol if bass_vol < 255 else 255,
                humanize=True,
            )
        if pickup_root is not None and bass:
            # Walk up into the next section's root over the last two beats:
            # the fifth below, a step, then the leading tone — the pickup a
            # bass player plays into a chorus.
            target = pickup_root
            lo = min(n for _, n in bass)
            while target - 12 >= lo:
                target -= 12
            while target < 36:
                target += 12
            walk = [(ROWS_PER_PATTERN - 8, target - 5), (ROWS_PER_PATTERN - 4, target - 2),
                    (ROWS_PER_PATTERN - 2, target - 1)]
            for row in range(ROWS_PER_PATTERN - 8, ROWS_PER_PATTERN):
                pat.data[row][CH_BASS] = ITNote()
            apply_notes_to_pattern(pat, CH_BASS, walk, sample_map["bass"],
                                   volume=bass_vol if bass_vol < 255 else 255)
            bass = [b for b in bass if b[0] < ROWS_PER_PATTERN - 8] + walk
        if bass_weight in ("light", "medium"):
            cut_after = 2 if bass_weight == "light" else 4
            for row, _ in bass:
                cut_row = row + cut_after
                if cut_row < ROWS_PER_PATTERN:
                    if pat.data[cut_row][CH_BASS].note == 0:
                        pat.data[cut_row][CH_BASS] = ITNote(note=end_note(sample_map["bass"]))

    # ── Arpeggio ──
    if layers["arp"]:
        # A figure with accents and rests, chosen per section role, that
        # thins where the lead is busy; see arp.py.
        arp = generate_arp(harmony_segments, arp_figure, section_energy,
                           melody_rows={r for r, n in melody if n != -1},
                           scale_notes=scale_notes, colour=arp_colour)
        apply_notes_to_pattern(
            pat, CH_ARP, [(r, n) for r, n, _ in arp], sample_map["arp"],
            volume=arp_vol, humanize=False,
        )
        # Accents are the figure's own shape; no jitter on top, or every bar
        # is unique again and the ear reads it as a sequencer.
        for r, _, accent in arp:
            pat.data[r][CH_ARP].volume = max(1, min(64, int(round(arp_vol * accent))))

    # ── Drums ──
    if layers["drums"]:
        # A four-bar phrase from the section's groove, with its fill (if any)
        # in the last bar, a crash on the first beat of every other pattern
        # and on section starts; see drums.py.
        render_drums(pat, groove, sample_map=sample_map, energy=section_energy,
                     bpm=bpm, swing=swing_amount, speed=speed, fill=drum_fill,
                     hat_stroke=hat_stroke, crash_chance=crash_chance,
                     fill_crash=fill_crash, kit_rng=kit_rng,
                     breakdown=breakdown,
                     crash_on_one=(chord_idx == 0 and sec_type in ("chorus", "bridge"))
                                  or (chord_idx % 2 == 0 and section_energy >= 0.8))

    # ── Echo returns ──
    # After every sent part is written: the lead per note, harmony and arp
    # whole. The safety net below bounds the returns like any tonal channel.
    if echo_sends:
        for src, taps, hold, rest, accent in echo_sends:
            if taps:
                apply_echo_taps(pat, src, taps, hold, rest, accent)

    # ── Sustain safety net ──
    apply_sustain_safety_net(pat)

    # ── Section transitions ──
    if is_intro and chord_idx == 0:
        for ch in [CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP,
                   *CH_ECHO_ALL]:
            apply_fade(pat, ch, fade_in=True, rows_count=16)

    if is_ending and chord_idx == n_patterns - 1:
        if ending_style in ("fadeout", "tag"):
            for ch in range(NUM_CHANNELS):
                apply_fade(pat, ch, fade_out=True, rows_count=24)

    return pat


def compose_song(seed: int | None = None, tempo_pref: str = "random",
                 energy_pref: str = "random", scale_pref: str = "random",
                 style_pref: str = "random", drum_density: str = "random",
                 drum_fills: bool = True, drum_swing: str = "random",
                 melody_style: str = "random",
                 harmony_voicing: str = "random",
                 harmony_mode: str = "random",
                 bass_weight: str = "random",
                 song_form: str = "random",
                 echo: str = "random", echo_wet: str = "random",
                 echo_delay: str = "random", echo_stereo: str = "random",
                 keys: str = "moving", pack: str = "random") -> dict:
    """Compose a complete procedural song. Returns a dict for write_it_file."""
    if seed is not None:
        random.seed(seed)

    # Resolve "random" for all settings
    if style_pref not in STYLES:
        style_pref = random.choices(STYLES, weights=[1, 2, 1], k=1)[0]
    # A pack narrows every draw below to the habits of the scores it imitates.
    if pack == "random":
        candidates = [p for p in PACK_NAMES if PACKS[p]["palette"] == style_pref]
        pack = random.choice(candidates) if candidates and random.random() < PACK_CHANCE else None
    elif pack in ("none", "", None):
        pack = None
    elif pack not in PACKS:
        raise ValueError(f"Unknown pack: {pack}")
    elif PACKS[pack]["palette"] != style_pref:
        style_pref = PACKS[pack]["palette"]
    if tempo_pref == "random" and pack_weights(pack, "tempo"):
        tempo_pref = _weighted(["slow", "medium", "fast"], pack_weights(pack, "tempo"))
    if energy_pref == "random" and pack_weights(pack, "energy"):
        energy_pref = _weighted(["chill", "normal", "intense"], pack_weights(pack, "energy"))
    if scale_pref == "random" and pack_weights(pack, "scale_family"):
        scale_pref = _weighted(["minor", "major", "pentatonic"], pack_weights(pack, "scale_family"))
    if drum_density == "random":
        drum_density = _weighted(["sparse", "normal", "busy"], pack_weights(pack, "drum_density"))
    if drum_swing == "random":
        drum_swing = _weighted(["off", "light", "heavy"], pack_weights(pack, "drum_swing"))
    if melody_style == "random":
        # Weighted toward phrased: it is the path with motifs, so it is the one
        # that produces a recognisable hook. simple is an unstructured random
        # walk, which is what "noodling" sounds like. Both stay available
        # explicitly via --melody.
        melody_style = random.choices(["phrased", "simple"], weights=[3, 1], k=1)[0]
    if harmony_voicing == "random":
        harmony_voicing = _weighted(["full", "thin"], pack_weights(pack, "harmony_voicing"))
    if harmony_mode == "random":
        harmony_mode = _weighted(["stabs", "sustain", "rhythmic", "ostinato", "pulse"],
                                 pack_weights(pack, "harmony_mode") or
                                 {"stabs": 1, "sustain": 1, "rhythmic": 1})
    if bass_weight == "random":
        bass_weight = _weighted(["heavy", "medium", "light"], pack_weights(pack, "bass_weight"))
    if echo == "random":
        # The SNES S-DSP had a hardware echo send that most, not all, tracks
        # used, so snes draws it most of the time. The NES and the YM2612
        # had no echo unit, so chip and genesis stay dry unless asked.
        echo_chance = {"snes": 0.7, "chip": 0.0, "genesis": 0.0}[style_pref]
        use_echo = random.random() < pack_value(pack, "echo", echo_chance)
    else:
        use_echo = echo == "on"

    # ── Musical choices ──
    key = theory.random_key()

    if scale_pref == "minor":
        scale_name = random.choice(["natural_minor", "harmonic_minor", "dorian", "phrygian"])
    elif scale_pref == "major":
        scale_name = random.choice(["major", "mixolydian"])
    elif scale_pref == "pentatonic":
        scale_name = random.choice(["minor_pentatonic", "major_pentatonic"])
    else:
        scale_name = theory.random_scale()

    progression = theory.random_progression(scale_name)

    if tempo_pref == "slow":
        target_bpm = random.randint(80, 110)
    elif tempo_pref == "medium":
        target_bpm = random.randint(110, 140)
    elif tempo_pref == "fast":
        target_bpm = random.randint(140, 180)
    else:
        target_bpm = theory.random_tempo()

    scale_notes = theory.build_scale(key, scale_name, octaves=4)

    # Ticks per row. Higher means more ticks for per-tick effects (vibrato,
    # volume slides) to run in, so they sound smoother.
    speed = random.choice([4, 5, 6])

    # Derive the stored tempo from the target BPM and the chosen speed. Picking
    # both independently scaled the song by up to 1.5x, so a "slow" song at
    # speed 4 ran at 165 BPM and a "fast" one reached 270.
    tempo = bpm_to_it_tempo(target_bpm, speed, ROWS_PER_BEAT)

    # ── Instruments ──
    instruments = _pick_instruments(style_pref, bass_weight=bass_weight, pack=pack)
    samples, sample_map, struck_roles = _build_samples(instruments)
    _register_releases(samples)
    echo_bus = None                      # built once song_salt exists

    # ── Energy / style ──
    if energy_pref == "chill":
        bass_style = _weighted(["steady", "steady", "walking"], pack_weights(pack, "bass_style"))
        melody_density = random.uniform(0.40, 0.50)
    elif energy_pref == "intense":
        bass_style = _weighted(["driving", "driving", "octave"], pack_weights(pack, "bass_style"))
        melody_density = random.uniform(0.55, 0.75)
    else:
        bass_style = _weighted(["steady", "octave", "walking", "driving"], pack_weights(pack, "bass_style"))
        melody_density = random.uniform(0.45, 0.65)
    arp_figures = pick_figures(energy_pref, pack_weights(pack, "arp_figures"))

    # ── Song structure (from structure module) ──
    if song_form == "random" and pack_weights(pack, "form"):
        song_form = _weighted(struct.FORMS, pack_weights(pack, "form"))
    song_structure, section_layers_map, energy_curve, ending_style, form_name = \
        struct.generate_structure(form=song_form)
    # Some packs play without a kit at all: pads, drone and lead carry it.
    drumless = random.random() < pack_value(pack, "drumless", 0.0)
    if drumless:
        section_layers_map = {k: {**v, "drums": False} for k, v in section_layers_map.items()}

    # ── Motifs ──
    use_phrased = melody_style == "phrased"
    # Motifs draw from their own stream (seeded from the global one), so
    # the motif grammar can change without moving the rest of the song.
    motif_rng = random.Random(random.randrange(2 ** 31))
    if use_phrased:
        scale_size = len(theory.SCALES[scale_name])
        chorus_motif = generate_motif(length=motif_rng.choice([4, 5]), rng=motif_rng, scale_size=scale_size)
        verse_motif = vary_motif(chorus_motif, 0.4, rng=motif_rng)
        bridge_motif = generate_motif(length=motif_rng.choice([3, 4]), rng=motif_rng, scale_size=scale_size)
    else:
        chorus_motif = verse_motif = bridge_motif = None

    # ── Harmony config ──
    num_harmony_voices = 3 if harmony_voicing == "full" else 1
    voicing_style = harmony_mode

    # ── Progression variation ──
    alt_progression = theory.random_alternate_progression(scale_name, progression)
    # Colour the triads so 7ths and sus4s actually reach the output.
    progression = theory.add_chord_color(progression)
    alt_progression = theory.add_chord_color(alt_progression)
    use_alt_chorus = random.random() < 0.5
    # Key relations and harmonic rhythm. A section that moves key takes a
    # progression from its own scale's table, coloured like the home one.
    # Draw the moving plan and its progressions regardless of `keys`, so a
    # seed pinned to the home key is the same song minus the key moves.
    drawn_plan = plan_keys(scale_name, "moving")
    section_progs = {}
    for sec, (shift, sname) in drawn_plan.items():
        if sname != scale_name:
            section_progs[sec] = theory.add_chord_color(theory.random_progression(sname))
    key_plan = drawn_plan if keys != "home" else {k: (0, scale_name) for k in drawn_plan}
    if keys == "home":
        section_progs = {}
    compact = random.random() < (0.6 if target_bpm >= 130 else 0.35)
    modulate_chorus = key_plan["chorus"][0] != 0

    # ── Effects ──
    vibrato_speed = random.choice([3, 4, 5])
    vibrato_depth = random.choice([2, 3, 4])
    porta_speed = random.choice([16, 24, 32, 48])
    use_bass_porta = bass_style in ("walking", "steady", "drone")
    swing_amount = {"off": 0, "light": 1, "heavy": 2}.get(drum_swing, 0)
    grooves = pick_grooves(energy_pref, drum_density)
    bpm_value = it_tempo_to_bpm(tempo, speed, ROWS_PER_BEAT)

    # ── Instrument swaps ──
    alt_pool = PACKS[pack]["voices"]["alt_lead"] if pack else PALETTES[style_pref]["alt_lead"]
    alt_lead = random.choice([n for n in alt_pool if n != instruments["melody"]] or alt_pool)
    alt_lead_sample_idx = None

    # ── Generate patterns ──
    # Content is keyed by reuse group, so every chorus draws the same melody,
    # harmony and bass from the same seed and the hook comes back. Rendering
    # (energy, layers, lead instrument) still varies, and where those happen to
    # match as well the order list points at a single shared pattern.
    patterns = []
    pattern_cache = {}       # render identity -> pattern index
    pattern_index_for = {}   # (section, pattern_idx) -> pattern index
    pattern_counts = {}      # section -> patterns in it
    song_salt = random.randrange(2 ** 31)

    # ── Echo settings ──
    # Their own stream: a seed's arrangement must not move when the echo
    # options change, and a --keys or --echo-wet switch must not reshuffle it.
    echo_rng = random.Random(song_salt ^ 0xEC40)
    bpm_for_echo = it_tempo_to_bpm(tempo, speed, ROWS_PER_BEAT)
    if echo_wet == "random":
        w = pack_weights(pack, "echo_wet") or ECHO_WET_WEIGHTS
        echo_wet = echo_rng.choices(list(w), list(w.values()))[0]
    if echo_delay == "random":
        weights = pack_weights(pack, "echo_delay") or \
            next(w for floor, w in ECHO_DELAY_WEIGHTS if bpm_for_echo >= floor)
        echo_delay = echo_rng.choices(list(weights), list(weights.values()))[0]
    echo_feedback = round(echo_rng.uniform(*ECHO_FEEDBACK_RANGE), 2)
    if echo_stereo == "random":
        w = pack_weights(pack, "echo_stereo") or ECHO_STEREO_WEIGHTS
        echo_stereo = echo_rng.choices(list(w), list(w.values()))[0]
    arp_scale = max(0.0, min(1.0, (ECHO_ARP_OFF_BPM - bpm_for_echo)
                                  / (ECHO_ARP_OFF_BPM - ECHO_ARP_FULL_BPM)))
    echo_bus = _EchoBus(samples, ECHO_WETNESS[echo_wet], ECHO_DELAYS[echo_delay],
                        echo_feedback, echo_stereo, arp_scale, speed)
    pattern_sec: dict[int, str] = {}     # pattern index -> section type, for the spill
    # Kit decisions a pack adds (which phrases get a crash) draw from their own
    # stream so they never move the parts composed after the drums.
    kit_rng = random.Random(song_salt ^ 0x0D12)
    half_changes = 0

    for section in song_structure:
        layers = section_layers_map.get(section, section_layers_map.get("verse1"))
        sec_type = struct.section_type(section)
        group = struct.reuse_group(section)
        layers_key = tuple(sorted(layers.items()))
        is_intro = section == "intro"
        is_ending = section in ("outro", "tag")
        base_energy = energy_curve.get(section, 0.7)

        shift, sec_scale_name = key_plan.get(sec_type, (0, scale_name))
        section_key = key + shift
        section_scale = theory.build_scale(section_key, sec_scale_name, octaves=4)
        if sec_type in section_progs:
            section_prog = section_progs[sec_type]
        else:
            section_prog = struct.get_section_progression(
                section, progression, alt_progression, use_alt_chorus)
        plan = struct.pattern_plan(section_prog, compact)
        num_patterns = len(plan)
        pattern_counts[section] = num_patterns

        # What the next section opens on, in its own key, for the cadence
        # and the bass pickup into it.
        sec_pos = song_structure.index(section)
        next_section = song_structure[sec_pos + 1] if sec_pos + 1 < len(song_structure) else None
        next_sec = struct.section_type(next_section) if next_section else None
        next_root = None
        if next_sec and next_sec != "outro":
            n_shift, n_scale_name = key_plan.get(next_sec, (0, scale_name))
            n_prog = section_progs.get(next_sec) or struct.get_section_progression(
                next_section, progression, alt_progression, use_alt_chorus)
            next_root = theory.chord_root_for(
                key + n_shift, theory.build_scale(key + n_shift, n_scale_name, octaves=4), n_prog[0])

        for chord_idx, entries in enumerate(plan):
            # Graduated fadeout: ramp energy down across outro patterns
            if section == "outro" and ending_style == "fadeout" and num_patterns > 1:
                fade_progress = chord_idx / (num_patterns - 1)  # 0.0 to 1.0
                section_energy = base_energy * (1.0 - fade_progress * 0.7)
            else:
                section_energy = base_energy

            # Snap energy to its tier before anything downstream reads it, so
            # two sections sharing a cache key render byte-identically instead
            # of differing by a volume point. The curve still shapes the song,
            # just in 0.2 steps; apply_fade does the fine-grained work.
            energy_tier = _energy_tier(section_energy)
            section_energy = energy_tier / 5

            # Floor the density. melody_density starts at 0.40 and the energy
            # tier can be 0.4, which multiplied out to 0.16 — under one note a
            # bar, so the section read as empty rather than sparse.
            section_density = max(0.35, melody_density * section_energy)
            if is_ending:
                section_density = max(section_density, 0.45)

            # Instrument swap for verse2/chorus3
            melody_sample = sample_map["melody"]
            if section in ("verse2", "chorus3"):
                if alt_lead_sample_idx is None:
                    samples.append(_make_sample(alt_lead))
                    alt_lead_sample_idx = len(samples)
                    _register_releases(samples)
                melody_sample = alt_lead_sample_idx
            if use_echo:
                echo_bus.add_source(melody_sample,
                                    alt_lead if melody_sample == alt_lead_sample_idx
                                    else instruments["melody"])
                echo_bus.add_source(sample_map["harmony"], instruments["harmony"])
                echo_bus.add_source(sample_map["arp"], instruments["arp"],
                                    strike_rule="arp" in STRIKE_RULE_ROLES)

            # Two sections render to the same bytes only if the group, the
            # chord, the dynamics tier, the active layers and the lead all
            # agree — then they can share one pattern outright.
            cache_key = (group, chord_idx, energy_tier, layers_key, melody_sample)
            if cache_key in pattern_cache:
                pattern_index_for[(section, chord_idx)] = pattern_cache[cache_key]
                continue

            # Reseed per content group so a returning chorus is the same music,
            # not a fresh roll of the dice.
            content_seed = _content_seed(song_salt, group, chord_idx)
            random.seed(content_seed)
            melody_rng = random.Random(content_seed ^ 0x5EED)

            next_entries = plan[(chord_idx + 1) % num_patterns]
            is_section_end = chord_idx == num_patterns - 1 and not is_ending and next_root is not None
            # Cadence: the last pattern of a section ends on the dominant of
            # what comes next, most of the time; the bass walks up into it.
            cadence = is_section_end and random.random() < 0.85
            segments = _chord_segments(section_key, sec_scale_name, section_scale,
                                       entries, next_entries[0], sec_type,
                                       cadence_root=next_root if cadence else None)
            pickup_root = next_root if cadence else None

            # Drums for this pattern: the section's groove; a fill at the end
            # of the section sized for what follows, a light one halfway; a
            # two-bar drop at the top of a bridge sometimes.
            if is_section_end:
                fill_pos = "section_end"
            elif num_patterns >= 4 and chord_idx == num_patterns // 2 - 1:
                fill_pos = "mid"
            else:
                fill_pos = "none"
            drum_fill = pick_fill(next_sec, fill_pos, drum_fills,
                                  orchestral=bool(pack_value(pack, "section_rolls", False)))
            breakdown = sec_type == "bridge" and chord_idx == 0 and random.random() < 0.4
            half_changes += len(segments) - 1

            section_bass = pick_section_bass(bass_weight, section_energy, bass_style)
            section_motif = _pick_section_motif(
                sec_type, use_phrased, chorus_motif, verse_motif, bridge_motif, rng=melody_rng,
                scale_size=len(theory.SCALES[sec_scale_name]))

            pat = _compose_pattern(
                scale_notes=section_scale, segments=segments,
                layers=layers, sec_type=sec_type,
                section_energy=section_energy, section_density=section_density,
                section_bass=section_bass, sample_map=sample_map,
                melody_sample=melody_sample, use_phrased=use_phrased,
                section_motif=section_motif, melody_rng=melody_rng, chord_idx=chord_idx,
                is_answer=(chord_idx % 2 == 1),
                voicing_style=voicing_style, num_harmony_voices=num_harmony_voices,
                vibrato_speed=vibrato_speed, vibrato_depth=vibrato_depth,
                bass_weight=bass_weight, use_bass_porta=use_bass_porta,
                porta_speed=porta_speed,
                arp_figure=arp_figures.get(sec_type, arp_figures["verse"]),
                arp_colour=(style_pref == "snes"),
                groove=grooves.get(sec_type, grooves["verse"]), drum_fill=drum_fill,
                breakdown=breakdown, n_patterns=num_patterns, pickup_root=pickup_root,
                is_ending=is_ending, ending_style=ending_style,
                swing_amount=swing_amount, speed=speed, bpm=bpm_value,
                is_intro=is_intro, echo_sends=echo_bus.sends(sec_type) if use_echo else None,
                counter_chance=pack_value(pack, "counter_line", 0.3),
                hat_stroke=pack_value(pack, "hat_stroke", 1.0),
                crash_chance=pack_value(pack, "crash_chance", 1.0),
                fill_crash=pack_value(pack, "fill_crash", True),
                kit_rng=kit_rng,
                power_chords=bool(pack_value(pack, "power_chords", False)),
            )

            pattern_cache[cache_key] = len(patterns)
            pattern_index_for[(section, chord_idx)] = len(patterns)
            pattern_sec[len(patterns)] = sec_type
            patterns.append(pat)

    # ── Build orders ──
    orders = struct.build_orders(song_structure, pattern_index_for, pattern_counts)

    # ── Echo tails across pattern boundaries ──
    # Where a pattern is only ever preceded by one other, its first rows can
    # carry the echo of that pattern's last notes.
    if use_echo:
        preds: dict[int, set[int]] = {}
        for a, b in zip(orders, orders[1:]):
            preds.setdefault(b, set()).add(a)
        done = set()
        for a, b in zip(orders, orders[1:]):
            if (a, b) in done or len(preds[b]) != 1 or a == b:
                continue
            done.add((a, b))
            for src, taps, hold, rest, accent in echo_bus.sends(pattern_sec.get(a, "verse")):
                if taps:
                    apply_echo_spill_taps(patterns[a], patterns[b], src, taps, hold, rest, accent)

    # ── Silence channels at section boundaries ──
    silence_inactive_channels(orders, patterns)

    # ── Song info ──
    key_name = theory.NOTE_NAMES[key % 12]
    scale_label = scale_name.replace("_", " ")
    # Title from the song's own random state: as reproducible as the music,
    # and finally something other than "BitComposer - C Dorian" twenty times.
    # Its own stream: the title must not depend on how many random draws the
    # arrangement happened to make, so a seed keeps its name across options
    # like --keys home.
    song_name = names.song_title(scale_name, rng=random.Random(song_salt ^ 0x7A1E))
    display_structure = [struct.section_type(s) for s in song_structure]
    bpm = round(it_tempo_to_bpm(tempo, speed, ROWS_PER_BEAT))
    message = "\n".join([
        song_name,
        f"{key_name} {scale_label} - {bpm} BPM",
        f"{style_pref}{f' ({pack})' if pack else ''}{_echo_label(use_echo, echo_wet)} - {form_name} form",
        f"{instruments['melody']} / {instruments['harmony']} / {instruments['bass']}",
        f"seed {seed if seed is not None else 'none'} - bitcomposer {__version__}",
        *([f"echo: {echo_bus.describe()}, {echo_wet}"] if use_echo else []),
        "layout: " + ",".join(CHANNEL_ROLES),
    ])

    info = {
        "title": song_name,
        "key": key_name,
        "scale": scale_name,
        # The audible tempo, not the raw IT field — reporting the field as BPM
        # is what hid the speed/tempo interaction for so long.
        "tempo": bpm,
        "it_tempo": tempo,
        "speed": speed,
        "style": style_pref,
        "pack": pack,
        "echo": use_echo,
        "echo_wet": echo_wet if use_echo else None,
        "echo_delay": echo_delay if use_echo else None,
        "echo_feedback": echo_feedback if use_echo else None,
        "echo_stereo": echo_stereo if use_echo else None,
        "bass_style": bass_style,
        "drumless": drumless,
        "bass_weight": bass_weight,
        "arp_figures": {k: arp_figures[k] for k in ("verse", "chorus", "bridge")},
        "grooves": {k: grooves[k] for k in ("verse", "chorus", "bridge")},
        "melody_density": round(melody_density, 2),
        "melody_style": melody_style,
        "melody_contour": chorus_motif["contour_name"] if use_phrased and chorus_motif else "n/a",
        "harmony_voicing": harmony_voicing,
        "harmony_mode": harmony_mode,
        "chorus_modulated": modulate_chorus,
        "key_plan": {k: (v[0], v[1]) for k, v in key_plan.items() if k in ("chorus", "bridge")},
        "harmonic_rhythm": "2 bars" if compact else "4 bars",
        "chorus_alt_prog": use_alt_chorus,
        "ending_style": ending_style,
        "song_form": form_name,
        "alt_lead": alt_lead if alt_lead_sample_idx else None,
        "instruments": instruments,
        "struck": struck_roles,
        "progression": [tuple(e) for e in progression],
        "half_pattern_changes": half_changes,
        "structure": display_structure,
        "num_patterns": len(patterns),
        "num_orders": len(orders),
    }

    return {
        "name": song_name[:names.MAX_TITLE],
        "message": message,
        "key": key,
        "scale": scale_name,
        "tempo": tempo,
        "speed": speed,
        "samples": samples,
        "patterns": patterns,
        "orders": orders,
        "info": info,
    }


# Channel mix — tuned by ear via the widget's master panel. Order matches
# bitcomposer.pattern: melody, harmony x3, bass, arp, six drums, two echo taps.
# The echo channels sit at the melody's level; the taps are already quieter
# through their volume columns.
#
# Measured by rendering each part alone (2026-10-14, 60 s, dBFS): melody sits
# 6-14 dB under the drums and the arp 1-4 dB under the melody on every palette.
CHANNEL_VOLUMES = [
    13,              # melody
    25, 25, 25,      # harmony
    8,               # bass
    33,              # arp
    36, 36, 36, 36, 36, 36,  # kick, snare, hihat, tom, crash, open hat
    13, 13,          # lead echo — at the melody's level; the sends set the wetness
    25, 25, 25,      # harmony echo — at the harmony's level
    33, 33,          # arp echo — at the arp's level
]
# Levels no longer differ by palette: samples.generate_instrument normalises
# sustaining voices to one loop loudness and, on the arp, struck voices to
# one strike loudness, so a pluck, bell or pizz hits the arp at the same
# level whatever the song drew. The arp channel's 33 was set for struck
# voices, which peak and die within the step; a sustaining voice on the arp
# (the genesis PSG square, the Mega Man X pulse synth) holds full level for
# the whole step and came out 3-6 dB over the melody, so it takes this
# level instead (set by ear for the PSG square, Lower Cistern, 2026-10-13).
SUSTAINING_ARP_LEVEL = 17


def channel_volumes_for(info: dict) -> list[int]:
    vols = list(CHANNEL_VOLUMES)
    for role, vol in (PACKS[info["pack"]].get("trims", {}) if info.get("pack") else {}).items():
        for ch, r in enumerate(CHANNEL_ROLES):
            if r == role:
                vols[ch] = vol
    if not info.get("struck", {}).get("arp", True):
        for ch in (CH_ARP, *CH_ECHO_ARP):
            vols[ch] = SUSTAINING_ARP_LEVEL
    return vols


def save_song(song: dict, filepath: str) -> None:
    """Write a composed song (from compose_song) to an .it file."""
    write_it_file(
        filepath=filepath,
        song_name=song["name"],
        samples=song["samples"],
        patterns=song["patterns"],
        orders=song["orders"],
        tempo=song["tempo"],
        speed=song["speed"],
        num_channels=NUM_CHANNELS,
        channel_volumes=channel_volumes_for(song["info"]),
        message=song["message"],
    )


def unique_path(directory: str, stem: str, suffix: str = "", ext: str = ".it") -> str:
    """`<directory>/<stem><suffix><ext>`, with " 2", " 3", ... inserted before
    the suffix if that name is taken. Titles are drawn from a finite list, so
    two songs can share one."""
    import os
    candidate = os.path.join(directory, f"{stem}{suffix}{ext}")
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{stem} {n}{suffix}{ext}")
        n += 1
    return candidate


def compose_and_save(filepath: str, seed: int | None = None,
                     tempo: str = "random", energy: str = "random",
                     scale: str = "random", style: str = "random",
                     drum_density: str = "random", drum_fills: bool = True,
                     drum_swing: str = "random",
                     melody_style: str = "random",
                     harmony_voicing: str = "random",
                     harmony_mode: str = "random",
                     bass_weight: str = "random",
                     song_form: str = "random",
                     echo: str = "random", echo_wet: str = "random",
                     echo_delay: str = "random", echo_stereo: str = "random",
                     keys: str = "moving", pack: str = "random") -> dict:
    """Compose a song and save it as an IT file. Returns song info."""
    song = compose_song(seed=seed, tempo_pref=tempo, energy_pref=energy,
                        scale_pref=scale, style_pref=style,
                        drum_density=drum_density, drum_fills=drum_fills,
                        drum_swing=drum_swing, melody_style=melody_style,
                        harmony_voicing=harmony_voicing,
                        harmony_mode=harmony_mode,
                        bass_weight=bass_weight,
                        song_form=song_form,
                        echo=echo, echo_wet=echo_wet, echo_delay=echo_delay,
                        echo_stereo=echo_stereo, keys=keys, pack=pack)
    save_song(song, filepath)
    return song["info"]
