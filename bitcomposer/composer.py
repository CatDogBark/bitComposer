"""
Procedural song composer.

Generates complete songs by combining music theory, instrument samples,
and pattern generation into playable Impulse Tracker modules.
"""

import random
import zlib

from . import theory
from . import samples as smp
from . import structure as struct
from .it_format import (
    ITSample, ITPattern, ITNote, midi_to_it_note, NOTE_CUT, NOTE_OFF,
    write_it_file, bpm_to_it_tempo, it_tempo_to_bpm,
    FX_VIBRATO, FX_PORTAMENTO, FX_VOLUME_SLIDE, FX_TREMOLO, FX_SET_TEMPO,
)
from .pattern import (
    CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP,
    CH_KICK, CH_SNARE, CH_HIHAT, CH_TOM, CH_CRASH, CH_OPEN_HAT,
    NUM_CHANNELS, ROWS_PER_PATTERN, ROWS_PER_BAR, ROWS_PER_BEAT,
    humanize_volume, apply_notes_to_pattern, apply_vibrato,
    apply_portamento, apply_harmony_fade, apply_fade,
    apply_drums_to_pattern, generate_drums,
    apply_sustain_safety_net, silence_inactive_channels,
)
from .melody import (
    generate_motif, vary_motif, generate_melody,
    generate_counter_melody, add_melody_cuts,
)
from .harmony import generate_harmony
from .bass import generate_bass, generate_arpeggio, pick_section_bass


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


def _pick_instruments(prefer_fm: bool | None = None,
                      bass_weight: str = "heavy") -> dict[str, str]:
    """Pick a random instrument set for the song."""
    # Harmony uses thin, focused waveforms that sit behind the melody
    harmony_choices = ["triangle_lead", "pulse_lead", "sine_bass", "filtered_lead"]
    if prefer_fm is True:
        lead_choices = ["fm_lead", "fm_lead", "fm_bell", "filtered_lead"]
        harmony_choices = ["triangle_lead", "pulse_lead", "fm_bell", "filtered_lead"]
        bass_heavy = ["fm_bass", "fm_bass", "distorted_bass", "filtered_bass"]
        bass_medium = ["fm_bass", "filtered_bass", "saw_bass"]
        bass_light = ["pluck_bass", "thin_bass", "bright_bass"]
        arp_choices = ["fm_bell", "fm_lead", "fm_brass"]
    elif prefer_fm is False:
        lead_choices = ["square_lead", "pulse_lead", "triangle_lead",
                        "pwm_lead", "filtered_lead"]
        harmony_choices = ["triangle_lead", "pulse_lead", "filtered_lead"]
        bass_heavy = ["triangle_bass", "sine_bass", "square_bass", "saw_bass",
                      "filtered_bass"]
        bass_medium = ["square_bass", "triangle_bass", "filtered_bass"]
        bass_light = ["pluck_bass", "thin_bass", "bright_bass"]
        arp_choices = ["square_lead", "pulse_lead", "triangle_lead", "pwm_lead"]
    else:
        lead_choices = ["square_lead", "pulse_lead", "fm_lead", "fm_bell",
                        "pwm_lead", "filtered_lead"]
        harmony_choices = ["triangle_lead", "pulse_lead", "fm_bell", "filtered_lead"]
        bass_heavy = ["saw_bass", "triangle_bass", "fm_bass", "sine_bass",
                      "square_bass", "distorted_bass", "filtered_bass", "supersaw_bass"]
        bass_medium = ["saw_bass", "fm_bass", "square_bass", "filtered_bass"]
        bass_light = ["pluck_bass", "thin_bass", "bright_bass"]
        arp_choices = ["square_lead", "pulse_lead", "fm_bell", "triangle_lead",
                       "pwm_lead", "fm_brass"]

    # Pick bass timbre based on weight
    if bass_weight == "light":
        bass_choices = bass_light
    elif bass_weight == "medium":
        bass_choices = bass_medium
    else:
        bass_choices = bass_heavy

    lead = random.choice(lead_choices)
    harmony = random.choice([h for h in harmony_choices if h != lead] or harmony_choices)
    bass = random.choice(bass_choices)
    arp = random.choice([a for a in arp_choices if a != lead] or arp_choices)

    # Enhanced drums: 40% chance of using layered drums
    use_layered_drums = random.random() < 0.4

    return {
        "melody": lead,
        "harmony": harmony,
        "bass": bass,
        "arp": arp,
        "kick": "kick_layered" if use_layered_drums else "kick",
        "snare": "snare_layered" if use_layered_drums else "snare",
        "hihat": "hihat_metallic" if use_layered_drums else "hihat",
        "tom": "tom",
        "crash": "crash",
        "open_hihat": "open_hihat",
    }


def _build_samples(instruments: dict[str, str]) -> list[ITSample]:
    """Generate ITSample objects for all instruments."""
    samples = []
    seen = {}
    sample_map = {}  # instrument_key -> sample index (1-based)

    for key, name in instruments.items():
        if name in seen:
            sample_map[key] = seen[name]
            continue

        data, length, vol = smp.generate_instrument(name)

        # Drums don't loop
        is_drum = key in ("kick", "snare", "hihat", "tom", "crash", "open_hihat")

        it_sample = ITSample(
            name=name.replace("_", " ").title(),
            filename=name[:12],
            data=data,
            length=length,
            loop=not is_drum,
            loop_start=0,
            loop_end=length,
            default_volume=vol,
            c5_speed=smp.SAMPLE_RATE,
        )
        samples.append(it_sample)
        idx = len(samples)  # 1-based
        seen[name] = idx
        sample_map[key] = idx

    return samples, sample_map


def _pick_section_motif(sec_type: str, use_phrased: bool,
                        chorus_motif, verse_motif, bridge_motif) -> dict | None:
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
        return generate_motif(length=random.choice([3, 4]))


def _compose_pattern(*, scale_notes, chord_root, chord_type, chord_notes,
                     layers, sec_type, section, section_energy, section_density,
                     section_bass, sample_map, samples,
                     melody_sample, use_phrased, section_motif,
                     chord_idx, is_answer,
                     voicing_style, num_harmony_voices,
                     vibrato_speed, vibrato_depth,
                     bass_weight, use_bass_porta, porta_speed,
                     arp_style, drum_pattern, drum_density,
                     fill_pattern, section_prog, is_ending, ending_style,
                     swing_amount, is_intro) -> ITPattern:
    """Compose a single pattern with all layers."""
    pat = ITPattern(rows=ROWS_PER_PATTERN, channels=NUM_CHANNELS)
    melody = []

    # Scale volumes by section energy
    melody_vol = int(42 * section_energy)
    harmony_vol = int(22 * section_energy)
    arp_vol = int(36 * section_energy)

    # ── Melody ──
    if layers["melody"]:
        melody = generate_melody(
            scale_notes, chord_notes, ROWS_PER_PATTERN, section_density,
            motif=section_motif, is_answer=is_answer, phrased=use_phrased,
        )
        apply_notes_to_pattern(
            pat, CH_MELODY, melody, melody_sample,
            volume=melody_vol, humanize=True,
        )
        apply_vibrato(pat, CH_MELODY, melody,
                      speed=vibrato_speed, depth=vibrato_depth)

    # ── Harmony ──
    if layers["harmony"]:
        harmony_channels = [CH_HARMONY, CH_HARMONY2, CH_HARMONY3]

        if melody and sec_type in ("chorus", "bridge") and random.random() < 0.3:
            counter = generate_counter_melody(
                scale_notes, chord_notes, melody, ROWS_PER_PATTERN)
            counter = add_melody_cuts(counter, ROWS_PER_PATTERN, max_sustain=8)
            apply_notes_to_pattern(
                pat, CH_HARMONY, counter, sample_map["harmony"],
                volume=int(20 * section_energy), humanize=True,
            )
            apply_harmony_fade(pat, CH_HARMONY, counter)
            voices = generate_harmony(
                chord_notes, ROWS_PER_PATTERN,
                voicing=voicing_style,
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
                    apply_harmony_fade(pat, ch, voice_notes)
        else:
            voices = generate_harmony(
                chord_notes, ROWS_PER_PATTERN,
                voicing=voicing_style,
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
                    apply_harmony_fade(pat, ch, voice_notes)

    # ── Bass ──
    if layers["bass"]:
        bass = generate_bass(chord_root, chord_type, ROWS_PER_PATTERN, section_bass,
                             weight=bass_weight)
        bass_vol = {"heavy": 255, "medium": 150, "light": 100}.get(bass_weight, 255)
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
        if bass_weight in ("light", "medium"):
            cut_after = 2 if bass_weight == "light" else 4
            for row, _ in bass:
                cut_row = row + cut_after
                if cut_row < ROWS_PER_PATTERN:
                    if pat.data[cut_row][CH_BASS].note == 0:
                        pat.data[cut_row][CH_BASS] = ITNote(note=NOTE_CUT)

    # ── Arpeggio ──
    if layers["arp"]:
        # Tie arp density to section energy so it thins out in verses and
        # intros instead of running at full tilt through the whole song.
        arp = generate_arpeggio(chord_notes, ROWS_PER_PATTERN, arp_style,
                                density=section_energy)
        apply_notes_to_pattern(
            pat, CH_ARP, arp, sample_map["arp"],
            volume=arp_vol, humanize=True,
        )

    # ── Drums ──
    if layers["drums"]:
        section_drum = theory.random_drum_pattern_for_section(
            sec_type, drum_pattern, drum_density)
        drum_hits = generate_drums(section_drum, ROWS_PER_PATTERN)

        is_last_chord = chord_idx == len(section_prog) - 1
        if fill_pattern and is_last_chord and not is_ending:
            # A fill replaces the groove for the final bar only, so the
            # preceding bars keep their pattern and the fill reads as a
            # one-bar lead-in to the next section.
            fill_start = ROWS_PER_PATTERN - ROWS_PER_BAR
            fill_hits = generate_drums(fill_pattern, ROWS_PER_BAR)
            for drum_name in set(drum_hits) | set(fill_hits):
                kept = [h for h in drum_hits.get(drum_name, []) if h < fill_start]
                added = [fill_start + h for h in fill_hits.get(drum_name, [])]
                drum_hits[drum_name] = kept + added

        apply_drums_to_pattern(pat, drum_hits, sample_map, swing=swing_amount)

        for r in range(pat.rows):
            note = pat.data[r][CH_HIHAT]
            if note.note != 0:
                note.volume = humanize_volume(38, 8)

        if chord_idx == 0 and sec_type in ("chorus", "bridge"):
            crash_inst = sample_map.get("crash")
            if crash_inst:
                pat.data[0][CH_CRASH] = ITNote(
                    note=midi_to_it_note(60),
                    instrument=crash_inst,
                    volume=int(52 * section_energy),
                )

    # ── Sustain safety net ──
    apply_sustain_safety_net(pat)

    # ── Section transitions ──
    if is_intro and chord_idx == 0:
        for ch in [CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP]:
            apply_fade(pat, ch, fade_in=True, rows_count=16)

    if is_ending and chord_idx == len(section_prog) - 1:
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
                  song_form: str = "random") -> dict:
    """Compose a complete procedural song. Returns a dict for write_it_file."""
    if seed is not None:
        random.seed(seed)

    # Resolve "random" for all settings
    if drum_density == "random":
        drum_density = random.choice(["sparse", "normal", "busy"])
    if drum_swing == "random":
        drum_swing = random.choice(["off", "light", "heavy"])
    if melody_style == "random":
        melody_style = random.choice(["phrased", "simple"])
    if harmony_voicing == "random":
        harmony_voicing = random.choice(["full", "thin"])
    if harmony_mode == "random":
        harmony_mode = random.choice(["stabs", "sustain", "rhythmic"])
    if bass_weight == "random":
        bass_weight = random.choice(["heavy", "medium", "light"])

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
    drum_pattern = theory.random_drum_pattern()

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
    if style_pref == "genesis":
        instruments = _pick_instruments(prefer_fm=True, bass_weight=bass_weight)
    elif style_pref == "snes":
        instruments = _pick_instruments(prefer_fm=False, bass_weight=bass_weight)
    else:
        instruments = _pick_instruments(bass_weight=bass_weight)
    samples, sample_map = _build_samples(instruments)

    # ── Energy / style ──
    if energy_pref == "chill":
        bass_style = random.choice(["steady", "steady", "walking"])
        arp_style = random.choice(["up", "down", "updown"])
        melody_density = random.uniform(0.40, 0.50)
    elif energy_pref == "intense":
        bass_style = random.choice(["driving", "driving", "octave"])
        arp_style = random.choice(["updown", "random", "up"])
        melody_density = random.uniform(0.55, 0.75)
    else:
        bass_style = random.choice(["steady", "octave", "walking", "driving"])
        arp_style = random.choice(["up", "down", "updown", "random"])
        melody_density = random.uniform(0.45, 0.65)

    # ── Song structure (from structure module) ──
    song_structure, section_layers_map, energy_curve, ending_style, form_name = struct.generate_structure(form=song_form)

    # ── Motifs ──
    use_phrased = melody_style == "phrased"
    if use_phrased:
        chorus_motif = generate_motif(length=random.choice([4, 5]))
        verse_motif = vary_motif(chorus_motif, 0.4)
        bridge_motif = generate_motif(length=random.choice([3, 4]))
    else:
        chorus_motif = verse_motif = bridge_motif = None

    # ── Harmony config ──
    num_harmony_voices = 3 if harmony_voicing == "full" else 1
    voicing_style = harmony_mode

    # ── Progression variation ──
    alt_progression = theory.random_alternate_progression(scale_name, progression)
    use_alt_chorus = random.random() < 0.5
    modulate_chorus = random.random() < 0.25
    modulation_semitones = 1 if modulate_chorus else 0

    # ── Effects ──
    vibrato_speed = random.choice([3, 4, 5])
    vibrato_depth = random.choice([2, 3, 4])
    porta_speed = random.choice([16, 24, 32, 48])
    use_bass_porta = bass_style in ("walking", "steady")
    swing_amount = {"off": 0, "light": 1, "heavy": 2}.get(drum_swing, 0)
    fill_pattern = theory.random_drum_fill() if drum_fills else None

    # ── Instrument swaps ──
    alt_lead = random.choice([n for n in (
        ["square_lead", "pulse_lead", "fm_lead", "fm_bell", "triangle_lead", "filtered_lead"]
    ) if n != instruments["melody"]])
    alt_lead_sample_idx = None

    # ── Generate patterns ──
    # Content is keyed by reuse group, so every chorus draws the same melody,
    # harmony and bass from the same seed and the hook comes back. Rendering
    # (energy, layers, lead instrument) still varies, and where those happen to
    # match as well the order list points at a single shared pattern.
    patterns = []
    pattern_cache = {}       # render identity -> pattern index
    pattern_index_for = {}   # (section, chord_idx) -> pattern index
    song_salt = random.randrange(2 ** 31)

    for section in song_structure:
        layers = section_layers_map.get(section, section_layers_map.get("verse1"))
        sec_type = struct.section_type(section)
        group = struct.reuse_group(section)
        layers_key = tuple(sorted(layers.items()))
        is_intro = section == "intro"
        is_ending = section in ("outro", "tag")
        base_energy = energy_curve.get(section, 0.7)

        section_prog = struct.get_section_progression(
            section, progression, alt_progression, use_alt_chorus)
        num_chords = len(section_prog)

        for chord_idx, (degree, chord_type) in enumerate(section_prog):
            # Graduated fadeout: ramp energy down across outro patterns
            if section == "outro" and ending_style == "fadeout" and num_chords > 1:
                fade_progress = chord_idx / (num_chords - 1)  # 0.0 to 1.0
                section_energy = base_energy * (1.0 - fade_progress * 0.7)
            else:
                section_energy = base_energy

            # Snap energy to its tier before anything downstream reads it, so
            # two sections sharing a cache key render byte-identically instead
            # of differing by a volume point. The curve still shapes the song,
            # just in 0.2 steps; apply_fade does the fine-grained work.
            energy_tier = _energy_tier(section_energy)
            section_energy = energy_tier / 5

            section_density = melody_density * section_energy
            if is_ending:
                section_density = max(section_density, 0.45)

            chord_root = key + (scale_notes[degree] - scale_notes[0]) if degree < len(scale_notes) else key
            if modulate_chorus and sec_type == "chorus":
                chord_root += modulation_semitones
            chord_notes = theory.build_chord(chord_root, chord_type)

            # Instrument swap for verse2/chorus3
            melody_sample = sample_map["melody"]
            if section in ("verse2", "chorus3"):
                if alt_lead_sample_idx is None:
                    data, length, vol = smp.generate_instrument(alt_lead)
                    it_sample = ITSample(
                        name=alt_lead.replace("_", " ").title(),
                        filename=alt_lead[:12],
                        data=data, length=length,
                        loop=True, loop_start=0, loop_end=length,
                        default_volume=vol, c5_speed=smp.SAMPLE_RATE,
                    )
                    samples.append(it_sample)
                    alt_lead_sample_idx = len(samples)
                melody_sample = alt_lead_sample_idx

            # Two sections render to the same bytes only if the group, the
            # chord, the dynamics tier, the active layers and the lead all
            # agree — then they can share one pattern outright.
            cache_key = (group, chord_idx, energy_tier, layers_key, melody_sample)
            if cache_key in pattern_cache:
                pattern_index_for[(section, chord_idx)] = pattern_cache[cache_key]
                continue

            # Reseed per content group so a returning chorus is the same music,
            # not a fresh roll of the dice.
            random.seed(_content_seed(song_salt, group, chord_idx))

            section_bass = pick_section_bass(bass_weight, section_energy, bass_style)
            section_motif = _pick_section_motif(
                sec_type, use_phrased, chorus_motif, verse_motif, bridge_motif)

            pat = _compose_pattern(
                scale_notes=scale_notes, chord_root=chord_root,
                chord_type=chord_type, chord_notes=chord_notes,
                layers=layers, sec_type=sec_type, section=section,
                section_energy=section_energy, section_density=section_density,
                section_bass=section_bass, sample_map=sample_map, samples=samples,
                melody_sample=melody_sample, use_phrased=use_phrased,
                section_motif=section_motif, chord_idx=chord_idx,
                is_answer=(chord_idx % 2 == 1),
                voicing_style=voicing_style, num_harmony_voices=num_harmony_voices,
                vibrato_speed=vibrato_speed, vibrato_depth=vibrato_depth,
                bass_weight=bass_weight, use_bass_porta=use_bass_porta,
                porta_speed=porta_speed, arp_style=arp_style,
                drum_pattern=drum_pattern, drum_density=drum_density,
                fill_pattern=fill_pattern, section_prog=section_prog,
                is_ending=is_ending, ending_style=ending_style,
                swing_amount=swing_amount, is_intro=is_intro,
            )

            pattern_cache[cache_key] = len(patterns)
            pattern_index_for[(section, chord_idx)] = len(patterns)
            patterns.append(pat)

    # ── Build orders ──
    orders = struct.build_orders(
        song_structure, pattern_index_for, progression, alt_progression,
        use_alt_chorus)

    # ── Silence channels at section boundaries ──
    silence_inactive_channels(orders, patterns)

    # ── Song info ──
    key_name = theory.NOTE_NAMES[key % 12]
    song_name = f"BitComposer - {key_name} {scale_name.replace('_', ' ').title()}"
    display_structure = [struct.section_type(s) for s in song_structure]

    info = {
        "key": key_name,
        "scale": scale_name,
        # The audible tempo, not the raw IT field — reporting the field as BPM
        # is what hid the speed/tempo interaction for so long.
        "tempo": round(it_tempo_to_bpm(tempo, speed, ROWS_PER_BEAT)),
        "it_tempo": tempo,
        "speed": speed,
        "bass_style": bass_style,
        "bass_weight": bass_weight,
        "arp_style": arp_style,
        "melody_density": round(melody_density, 2),
        "melody_style": melody_style,
        "melody_contour": chorus_motif["contour_name"] if use_phrased and chorus_motif else "n/a",
        "harmony_voicing": harmony_voicing,
        "harmony_mode": harmony_mode,
        "chorus_modulated": modulate_chorus,
        "chorus_alt_prog": use_alt_chorus,
        "ending_style": ending_style,
        "song_form": form_name,
        "alt_lead": alt_lead if alt_lead_sample_idx else None,
        "instruments": instruments,
        "progression": [(d, t) for d, t in progression],
        "structure": display_structure,
        "num_patterns": len(patterns),
        "num_orders": len(orders),
    }

    return {
        "name": song_name[:25],
        "key": key,
        "scale": scale_name,
        "tempo": tempo,
        "speed": speed,
        "samples": samples,
        "patterns": patterns,
        "orders": orders,
        "info": info,
    }


def compose_and_save(filepath: str, seed: int | None = None,
                     tempo: str = "random", energy: str = "random",
                     scale: str = "random", style: str = "random",
                     drum_density: str = "random", drum_fills: bool = True,
                     drum_swing: str = "random",
                     melody_style: str = "random",
                     harmony_voicing: str = "random",
                     harmony_mode: str = "random",
                     bass_weight: str = "random",
                     song_form: str = "random") -> dict:
    """Compose a song and save it as an IT file. Returns song info."""
    song = compose_song(seed=seed, tempo_pref=tempo, energy_pref=energy,
                        scale_pref=scale, style_pref=style,
                        drum_density=drum_density, drum_fills=drum_fills,
                        drum_swing=drum_swing, melody_style=melody_style,
                        harmony_voicing=harmony_voicing,
                        harmony_mode=harmony_mode,
                        bass_weight=bass_weight,
                        song_form=song_form)
    # Channel mix — tuned by ear via master panel
    #   0=melody, 1-3=harmony, 4=bass, 5=arp, 6-11=drums
    channel_volumes = [
        13,  # CH_MELODY
        25,  # CH_HARMONY
        25,  # CH_HARMONY2
        25,  # CH_HARMONY3
         8,  # CH_BASS
        33,  # CH_ARP
        36,  # CH_KICK
        36,  # CH_SNARE
        36,  # CH_HIHAT
        36,  # CH_TOM
        36,  # CH_CRASH
        36,  # CH_OPEN_HAT
    ]
    write_it_file(
        filepath=filepath,
        song_name=song["name"],
        samples=song["samples"],
        patterns=song["patterns"],
        orders=song["orders"],
        tempo=song["tempo"],
        speed=song["speed"],
        num_channels=NUM_CHANNELS,
        channel_volumes=channel_volumes,
    )
    return song["info"]
