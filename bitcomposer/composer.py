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
from .echo import (ECHO_ARP_FULL_BPM, ECHO_ARP_OFF_BPM, ECHO_DELAYS, ECHO_DELAY_WEIGHTS, ECHO_FEEDBACK_RANGE, ECHO_STEREO_WEIGHTS, ECHO_WETNESS, ECHO_WET_WEIGHTS, _EchoBus, _echo_label)
from .instruments import (PALETTES, PULSE_DUTY, STRIKE_RULE_ROLES, _build_samples, _make_sample, _pick_instruments, _register_releases, _sample_from_inst, _weighted)
from .mix import (CHANNEL_VOLUMES, MASTER_GAIN, SUSTAINING_ARP_LEVEL, channel_volumes_for)
from .builder import (_chord_segments, _compose_pattern, _content_seed, _energy_tier, _pick_section_motif, plan_keys)




STYLES = ["chip", "snes", "genesis"]
# Chance that a snes song draws a style pack (packs.PACKS) when --pack random.
PACK_CHANCE = 0.5


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
    # The bass riff, when the song has one, from its own stream as well.
    riff_weights = pack_weights(pack, "riffs") or {"rock": 1}
    bass_riff = random.Random(song_salt ^ 0xB055).choices(list(riff_weights), list(riff_weights.values()))[0] \
        if bass_style == "riff" else None
    # A pack may ask for power chords everywhere (True) or only under some
    # harmony voices (a list): the chug plays fifths, the pad plays the chord.
    pc = pack_value(pack, "power_chords", False)
    power_chords = pc is True or (isinstance(pc, (list, tuple, set)) and instruments["harmony"] in pc)
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
                power_chords=power_chords, bass_riff=bass_riff,
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
        "bass_riff": bass_riff,
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
