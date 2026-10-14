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
from .pattern import (
    CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP,
    CH_SNARE, CH_HIHAT, CH_CRASH, CH_ECHO1, CH_ECHO2,
    NUM_CHANNELS, ROWS_PER_PATTERN, ROWS_PER_BAR, ROWS_PER_BEAT,
    humanize_volume, apply_notes_to_pattern, apply_vibrato,
    apply_portamento, apply_harmony_fade, apply_fade, apply_echo, apply_echo_spill,
    apply_drums_to_pattern, generate_drums,
    apply_sustain_safety_net, silence_inactive_channels,
    apply_chord_arpeggio, apply_retrigger,
)
from .melody import (
    generate_motif, vary_motif, generate_melody,
    generate_counter_melody, add_melody_cuts,
)
from .harmony import generate_harmony_timeline
from .bass import generate_bass_timeline, generate_arpeggio_timeline, pick_section_bass


STYLES = ["chip", "snes", "genesis"]

# Echo taps, in rows and as a fraction of the lead's volume. Three rows is a
# dotted eighth at four rows to the beat — the classic tracker echo spacing —
# and the second tap at twice that is the feedback repeat.
ECHO_TAPS = [(CH_ECHO1, 3, 0.5), (CH_ECHO2, 6, 0.25)]

# How harmony notes decay after their note-on, per voicing: (slide, rows to
# hold first). stabs and rhythmic are short hits, so a per-tick slide from
# the start is right. sustain is a pad: it holds for most of its 32-row
# interval and then takes a fine (per-row) slide down into the next hit.
HARMONY_FADE = {"stabs": (0x02, 0), "rhythmic": (0x03, 0), "sustain": (0xF2, 18)}

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
                  "tom": "snes_tom", "crash": "snes_crash", "open_hihat": "snes_open_hat"},
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
                  "tom": "gen_tom", "crash": "gen_crash", "open_hihat": "gen_open_hat"},
    },
}


# Pulse duty per preset, so a chip arp never shares the lead's duty — two
# channels at the same duty were how the palette ended up sounding like one.
PULSE_DUTY = {
    "square_lead": 0.5, "square_pluck": 0.5, "square_bass": 0.5,
    "pulse_lead": 0.25, "pulse_pluck": 0.25,
    "pulse12_lead": 0.125, "pulse12_pluck": 0.125,
}


def _pick_instruments(style: str, bass_weight: str = "heavy") -> dict[str, str]:
    """Pick a random instrument set for the song from the style's palette."""
    pal = PALETTES[style]
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
            "tom": "tom", "crash": "crash", "open_hihat": "open_hihat",
        }

    return {"melody": lead, "harmony": harmony, "bass": bass, "arp": arp, **drums}


def _make_sample(name: str) -> ITSample:
    inst = smp.generate_instrument(name)
    return ITSample(
        name=name.replace("_", " ").title(),
        filename=name[:12],
        data=inst["data"],
        length=inst["length"],
        loop=inst["loop"],
        loop_start=inst["loop_start"],
        loop_end=inst["loop_end"],
        default_volume=inst["volume"],
        c5_speed=inst["rate"],
    )


def _build_samples(instruments: dict[str, str]) -> tuple[list[ITSample], dict[str, int]]:
    """Generate ITSample objects for all instruments.

    Returns (samples, sample_map) where sample_map maps an instrument role
    to a 1-based sample index; roles sharing a preset share a sample.
    """
    samples: list[ITSample] = []
    seen: dict[str, int] = {}
    sample_map: dict[str, int] = {}

    for key, name in instruments.items():
        if name in seen:
            sample_map[key] = seen[name]
            continue
        samples.append(_make_sample(name))
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


def _chord_segments(key: int, scale_name: str, scale_notes: list[int],
                    entry, next_entry, sec_type: str) -> list[tuple]:
    """Chord timeline for one pattern: [(start_row, end_row, root, type, notes)].

    Usually one chord for the whole pattern; with HALF_PATTERN_CHANGE odds the
    back two bars move to a related chord (see theory.secondary_chord), so the
    harmony has a two-bar pulse instead of sitting on one chord for four.
    """
    def seg(start, end, e):
        _, chord_type, _ = theory.unpack_chord(e)
        root = theory.chord_root_for(key, scale_notes, e)
        return (start, end, root, chord_type, theory.build_chord(root, chord_type))

    if random.random() < HALF_PATTERN_CHANGE.get(sec_type, 0.4):
        second = theory.secondary_chord(scale_name, entry, next_entry)
        half = ROWS_PER_PATTERN // 2
        return [seg(0, half, entry), seg(half, ROWS_PER_PATTERN, second)]
    return [seg(0, ROWS_PER_PATTERN, entry)]


def _compose_pattern(*, scale_notes, segments, layers, sec_type, section_energy,
                     section_density, section_bass, sample_map,
                     melody_sample, use_phrased, section_motif,
                     chord_idx, is_answer,
                     voicing_style, num_harmony_voices,
                     vibrato_speed, vibrato_depth,
                     bass_weight, use_bass_porta, porta_speed,
                     arp_style, drum_pattern, drum_density,
                     fill_pattern, section_prog, is_ending, ending_style,
                     swing_amount, speed, is_intro, use_echo) -> ITPattern:
    """Compose a single pattern with all layers."""
    pat = ITPattern(rows=ROWS_PER_PATTERN, channels=NUM_CHANNELS)
    melody = []

    # The timeline in the shapes each generator wants.
    chord_notes = segments[0][4]                       # the pattern's main chord
    melody_timeline = [(s, notes) for s, _, _, _, notes in segments]
    harmony_segments = [(s, e, notes) for s, e, _, _, notes in segments]
    bass_segments = [(s, e, root, ctype) for s, e, root, ctype, _ in segments]

    # Scale volumes by section energy
    melody_vol = int(42 * section_energy)
    harmony_vol = int(22 * section_energy)
    arp_vol = int(36 * section_energy)
    harmony_fade, harmony_hold = HARMONY_FADE.get(voicing_style, (0x02, 0))

    # ── Melody ──
    if layers["melody"]:
        melody = generate_melody(
            scale_notes, chord_notes, ROWS_PER_PATTERN, section_density,
            motif=section_motif, is_answer=is_answer, phrased=use_phrased,
            chord_timeline=melody_timeline,
        )
        apply_notes_to_pattern(
            pat, CH_MELODY, melody, melody_sample,
            volume=melody_vol, humanize=True,
        )
        apply_vibrato(pat, CH_MELODY, melody,
                      speed=vibrato_speed, depth=vibrato_depth)
        if use_echo:
            for ch, delay, level in ECHO_TAPS:
                apply_echo(pat, CH_MELODY, ch, delay, level)

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
        arp = generate_arpeggio_timeline(harmony_segments, arp_style,
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

        apply_drums_to_pattern(pat, drum_hits, sample_map, swing=swing_amount,
                               speed=speed)

        # Retrigger the fill's snares into a roll — what Q is for.
        if fill_pattern and is_last_chord and not is_ending:
            apply_retrigger(pat, CH_SNARE,
                            [r for r in drum_hits.get("snare", [])
                             if r >= ROWS_PER_PATTERN - ROWS_PER_BAR])

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
        for ch in [CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP,
                   CH_ECHO1, CH_ECHO2]:
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
                 song_form: str = "random",
                 echo: str = "random") -> dict:
    """Compose a complete procedural song. Returns a dict for write_it_file."""
    if seed is not None:
        random.seed(seed)

    # Resolve "random" for all settings
    if drum_density == "random":
        drum_density = random.choice(["sparse", "normal", "busy"])
    if drum_swing == "random":
        drum_swing = random.choice(["off", "light", "heavy"])
    if melody_style == "random":
        # Weighted toward phrased: it is the path with motifs, so it is the one
        # that produces a recognisable hook. simple is an unstructured random
        # walk, which is what "noodling" sounds like. Both stay available
        # explicitly via --melody.
        melody_style = random.choices(["phrased", "simple"], weights=[3, 1], k=1)[0]
    if harmony_voicing == "random":
        harmony_voicing = random.choice(["full", "thin"])
    if harmony_mode == "random":
        harmony_mode = random.choice(["stabs", "sustain", "rhythmic"])
    if bass_weight == "random":
        bass_weight = random.choice(["heavy", "medium", "light"])
    if style_pref not in STYLES:
        style_pref = random.choices(STYLES, weights=[1, 2, 1], k=1)[0]
    if echo == "random":
        # The SNES always had its echo on; the others borrow it sometimes.
        echo_chance = {"snes": 1.0, "chip": 0.5, "genesis": 0.25}[style_pref]
        use_echo = random.random() < echo_chance
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
    instruments = _pick_instruments(style_pref, bass_weight=bass_weight)
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
    song_structure, section_layers_map, energy_curve, ending_style, form_name = \
        struct.generate_structure(form=song_form)

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
    # Colour the triads so 7ths and sus4s actually reach the output.
    progression = theory.add_chord_color(progression)
    alt_progression = theory.add_chord_color(alt_progression)
    use_alt_chorus = random.random() < 0.5
    modulate_chorus = random.random() < 0.25
    modulation_semitones = 1 if modulate_chorus else 0
    # The chorus modulates as a whole: chords AND the scale the melody draws
    # from. Shifting only the chord roots left the tune a semitone under its
    # own harmony for every chorus.
    chorus_scale = theory.build_scale(key + modulation_semitones, scale_name, octaves=4)

    # ── Effects ──
    vibrato_speed = random.choice([3, 4, 5])
    vibrato_depth = random.choice([2, 3, 4])
    porta_speed = random.choice([16, 24, 32, 48])
    use_bass_porta = bass_style in ("walking", "steady")
    swing_amount = {"off": 0, "light": 1, "heavy": 2}.get(drum_swing, 0)
    fill_pattern = theory.random_drum_fill() if drum_fills else None

    # ── Instrument swaps ──
    alt_lead = random.choice(
        [n for n in PALETTES[style_pref]["alt_lead"] if n != instruments["melody"]]
        or PALETTES[style_pref]["alt_lead"])
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
    half_changes = 0

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

        modulated = modulate_chorus and sec_type == "chorus"
        section_key = key + (modulation_semitones if modulated else 0)
        section_scale = chorus_scale if modulated else scale_notes

        for chord_idx, entry in enumerate(section_prog):
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

            next_entry = section_prog[(chord_idx + 1) % num_chords]
            segments = _chord_segments(section_key, scale_name, section_scale,
                                       entry, next_entry, sec_type)
            half_changes += len(segments) - 1

            section_bass = pick_section_bass(bass_weight, section_energy, bass_style)
            section_motif = _pick_section_motif(
                sec_type, use_phrased, chorus_motif, verse_motif, bridge_motif)

            pat = _compose_pattern(
                scale_notes=section_scale, segments=segments,
                layers=layers, sec_type=sec_type,
                section_energy=section_energy, section_density=section_density,
                section_bass=section_bass, sample_map=sample_map,
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
                swing_amount=swing_amount, speed=speed, is_intro=is_intro,
                use_echo=use_echo,
            )

            pattern_cache[cache_key] = len(patterns)
            pattern_index_for[(section, chord_idx)] = len(patterns)
            patterns.append(pat)

    # ── Build orders ──
    orders = struct.build_orders(
        song_structure, pattern_index_for, progression, alt_progression,
        use_alt_chorus)

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
            for ch, delay, level in ECHO_TAPS:
                apply_echo_spill(patterns[a], patterns[b], CH_MELODY, ch, delay, level)

    # ── Silence channels at section boundaries ──
    silence_inactive_channels(orders, patterns)

    # ── Song info ──
    key_name = theory.NOTE_NAMES[key % 12]
    scale_label = scale_name.replace("_", " ")
    # Title from the song's own random state: as reproducible as the music,
    # and finally something other than "BitComposer - C Dorian" twenty times.
    song_name = names.song_title(scale_name)
    display_structure = [struct.section_type(s) for s in song_structure]
    bpm = round(it_tempo_to_bpm(tempo, speed, ROWS_PER_BEAT))
    message = "\n".join([
        song_name,
        f"{key_name} {scale_label} - {bpm} BPM",
        f"{style_pref}{' + echo' if use_echo else ''} - {form_name} form",
        f"{instruments['melody']} / {instruments['harmony']} / {instruments['bass']}",
        f"seed {seed if seed is not None else 'none'} - bitcomposer {__version__}",
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
        "echo": use_echo,
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
# The arp level depends on the palette. A held chip pulse arp balanced by ear
# at 17 (Lower Cistern, 2026-10-13) where 33 buried the chorus. Chip arps are
# now decaying pulse blips, which average ~0.55x a held pulse over an 8th-note
# step, so 28 puts them at the level that 17 gave the held tone. SNES and
# Genesis arps are decaying plucks and bells and sit in that band at 33.
CHANNEL_VOLUMES = [
    13,              # melody
    25, 25, 25,      # harmony
    8,               # bass
    33,              # arp
    36, 36, 36, 36, 36, 36,  # kick, snare, hihat, tom, crash, open hat
    13, 13,          # echo taps
]
PALETTE_MIX = {
    "chip": {CH_ARP: 28},
}


def channel_volumes_for(style: str) -> list[int]:
    vols = list(CHANNEL_VOLUMES)
    for ch, v in PALETTE_MIX.get(style, {}).items():
        vols[ch] = v
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
        channel_volumes=channel_volumes_for(song["info"]["style"]),
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
                     echo: str = "random") -> dict:
    """Compose a song and save it as an IT file. Returns song info."""
    song = compose_song(seed=seed, tempo_pref=tempo, energy_pref=energy,
                        scale_pref=scale, style_pref=style,
                        drum_density=drum_density, drum_fills=drum_fills,
                        drum_swing=drum_swing, melody_style=melody_style,
                        harmony_voicing=harmony_voicing,
                        harmony_mode=harmony_mode,
                        bass_weight=bass_weight,
                        song_form=song_form,
                        echo=echo)
    save_song(song, filepath)
    return song["info"]
