"""One pattern at a time: the chord timeline, the key plan, and every layer
(melody, harmony, bass, arp, drums, echo returns) written into it."""
import random
import zlib

from . import theory
from .it_format import ITPattern, ITNote
from .pattern import CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP, CH_KICK, CH_SNARE, CH_HIHAT, CH_TOM, CH_CRASH, CH_OPEN_HAT, CH_ECHO_ALL, NUM_CHANNELS, ROWS_PER_PATTERN, ROWS_PER_BAR, humanize_volume, apply_notes_to_pattern, apply_vibrato, apply_portamento, apply_harmony_fade, apply_fade, apply_echo_taps, apply_sustain_safety_net, apply_chord_arpeggio, end_note, apply_strum, STRUM_ROW, STRUM_TICKS
from .drums import render_drums
from .melody import generate_motif, generate_melody, generate_counter_melody, add_melody_cuts
from .harmony import generate_harmony_timeline
from .bass import generate_bass_timeline, floor_bass
from .arp import generate_arp


# How harmony notes decay after their note-on, per voicing: (slide, rows to
# hold first). stabs and rhythmic are short hits, so a per-tick slide from
# the start is right. sustain is a pad: it holds for most of its 32-row
# interval and then takes a fine (per-row) slide down into the next hit.
# The channels each part writes, for the intro entries.
PART_CHANNELS = {
    "melody": (CH_MELODY,), "harmony": (CH_HARMONY, CH_HARMONY2, CH_HARMONY3),
    "bass": (CH_BASS,), "arp": (CH_ARP,),
    "drums": (CH_KICK, CH_SNARE, CH_HIHAT, CH_TOM, CH_CRASH, CH_OPEN_HAT),
}

HARMONY_FADE = {"stabs": (0x02, 0), "rhythmic": (0x03, 0), "sustain": (0xF2, 18),
                "ostinato": (0x03, 0), "pulse": (0x04, 0),
                "chug_sync": (0x03, 0), "chug_offbeat": (0x03, 0), "chug_gallop": (0x04, 0)}

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
    elif sec_type == "intro":
        return chorus_motif or verse_motif
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
                     pickup_root=None, intro=None, counter_chance=0.3, hat_stroke=1.0,
                     crash_chance=1.0, fill_crash=True, kit_rng=None,
                     power_chords=False, bass_riff=None) -> ITPattern:
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
                    if voicing_style == "rhythmic" and v_idx > 0:
                        apply_strum(pat, ch, voice_notes, STRUM_ROW, STRUM_TICKS)
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
                                      density=0.6 + 0.35 * section_energy, riff=bass_riff,
                                      scale_notes=scale_notes)
        bass = floor_bass(bass)
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
            # A pack may carry a second bass sample for the top of the line
            # (an octave pop on a heavy bass thins out on the low sample).
            # Every note picks its sample by pitch; the channel is the same.
            # Label space, an octave above the old values: with the bass floor
            # at label 48 the whole line sat above the old heavy ceiling and
            # the low sample never played.
            ceiling = {"heavy": 60, "medium": 66, "light": 72}.get(bass_weight, 60)
            hi = sample_map.get("bass_hi")
            groups = [(sample_map["bass"], [n for n in bass if hi is None or n[1] < ceiling])]
            if hi is not None:
                groups.append((hi, [n for n in bass if n[1] >= ceiling]))
            for inst, notes_ in groups:
                apply_notes_to_pattern(
                    pat, CH_BASS, notes_, inst,
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
            walk = floor_bass([(ROWS_PER_PATTERN - 8, target - 5), (ROWS_PER_PATTERN - 4, target - 2),
                               (ROWS_PER_PATTERN - 2, target - 1)])
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

    # ── Intro entries ──
    # In the first intro pattern each part waits for its bar (structure.INTROS);
    # before the echo returns, so nothing is sent from a bar a part is not in.
    if intro and chord_idx == 0:
        for part, bar in intro["enter"].items():
            for ch in PART_CHANNELS[part]:
                for row in range(min(bar * ROWS_PER_BAR, ROWS_PER_PATTERN)):
                    pat.data[row][ch] = ITNote()

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
    if is_intro and chord_idx == 0 and (intro is None or intro["fade_in"]):
        for ch in [CH_MELODY, CH_HARMONY, CH_HARMONY2, CH_HARMONY3, CH_BASS, CH_ARP,
                   *CH_ECHO_ALL]:
            apply_fade(pat, ch, fade_in=True, rows_count=16)

    if is_ending and chord_idx == n_patterns - 1:
        if ending_style in ("fadeout", "tag"):
            for ch in range(NUM_CHANNELS):
                apply_fade(pat, ch, fade_out=True, rows_count=24)

    return pat
