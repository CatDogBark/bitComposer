"""
Harmony generation: chord voicings and multi-voice harmony parts.

The 2026-10-17 rework (the 1.0.0 blocker): a thin harmony is two real voices
rather than one voice arpeggiated with the J effect; each voice family has
its own register, with the top voice kept under the lead's line; a stab's
length comes from the voice's attack and the row length, with no volume
slide on it; and the level is a property of the family, measured.
"""


HARMONY_VOICINGS = {
    "stabs": {
        "description": "Short chord stabs every 16 rows",
        "interval": 16,
        # The default; the builder sets the real length per voice with
        # stab_rows (a brass stab is two rows, a pad's most of the bar).
        "cut_after": 6,
    },
    "sustain": {
        "description": "Sustained pad chords, held across the pattern",
        "interval": 32,
        # Hold almost to the next hit; the fade in the composer takes the
        # last rows down so the re-attack is a swell, not a gap.
        "cut_after": 30,
    },
    "rhythmic": {
        "description": "Rhythmic chord hits synced to groove",
        "interval": 8,
        "cut_after": 4,
    },
    # Ostinatos: the chord tones restruck in a repeating rhythmic cell, the
    # way an orchestral string section carries a theme. "steps" are the rows
    # hit inside each cell of "cell" rows.
    "ostinato": {
        "description": "3+3+2 ostinato (dotted eighths), every voice together",
        "cell": 8, "steps": [0, 3, 6], "interval": 8, "cut_after": 2,
    },
    "pulse": {
        "description": "Straight eighths, lower voice on the beat, upper voices between",
        "cell": 8, "steps": [0, 2, 4, 6], "interval": 8, "cut_after": 1,
        "offset_upper": 2,
    },
    # Chug rhythms: a rhythm guitar's one-bar patterns, every voice together.
    "chug_sync": {
        "description": "Syncopated chug: 1, the and of 1, the and of 2, 3, the and of 4",
        "cell": 16, "steps": [0, 3, 6, 8, 14], "interval": 16, "cut_after": 2,
    },
    "chug_offbeat": {
        "description": "Chug on the off-beats only",
        "cell": 16, "steps": [2, 6, 10, 14], "interval": 16, "cut_after": 2,
    },
    "chug_gallop": {
        "description": "Gallop: a dotted push into every beat",
        "cell": 8, "steps": [0, 3, 4], "interval": 8, "cut_after": 1,
    },
}


# ── Register ──
# Per voice family: (anchor of the lowest voice, anchor spread with three
# voices, anchor spread with two, window low, window high), in MIDI. The
# anchors are fixed so consecutive chords keep their common tones (see
# voice_chord). Derived 2026-10-17 with the note conversion exact and the
# lead's median at 554-620 Hz (label 73-75): pads and strings low and wide
# (the lowest voice at C3-D3, 131-147 Hz, an octave over the bass's median,
# the top a tenth up), brass and guitars mid and close (a close triad at
# 196-330 Hz, where the games stab their brass), keys and chip voices
# between. The two-voice spread is wider on the soft families (a tenth, the
# open two-voice pad) and a sixth on the hard ones.
REGISTERS = {
    "pad": (48, 7, 12, 43, 69),
    "strings": (50, 7, 12, 45, 69),
    "choir": (50, 7, 12, 45, 69),
    "organ": (52, 5, 9, 45, 69),
    "flute": (57, 4, 6, 50, 72),
    "brass": (57, 4, 6, 50, 72),
    "lead": (55, 5, 7, 48, 70),
    "psg": (57, 5, 7, 50, 72),
    "keys": (55, 5, 7, 48, 72),
    "struck": (55, 4, 6, 48, 72),
}
DEFAULT_REGISTER = (52, 7, 9, 45, 72)

# The old fixed anchors, kept for callers that pass none.
VOICE_ANCHORS_BASE = 52
VOICE_ANCHOR_SPREAD = 7

# Playable window for harmony pitches when no family is known. The ceiling
# keeps the top voice below the melody's 60-83 range.
HARMONY_LOW, HARMONY_HIGH = 45, 72

# The top voice never sits above the lead's line: the window's ceiling in a
# pattern is the lead's lower quartile, but never under this, so two voices
# always have room.
WINDOW_FLOOR_HIGH = 60


def family_register(family: str | None) -> tuple:
    return REGISTERS.get(family, DEFAULT_REGISTER)


def anchors_for(family: str | None, num_voices: int) -> list[int]:
    """Fixed register anchors for num_voices voices of this family."""
    base, spread3, spread2, _, _ = family_register(family)
    if num_voices <= 2:
        return [base, base + spread2][:num_voices]
    return [base + spread3 * i for i in range(num_voices)]


def window_for(family: str | None, lead_notes: list[int] | None = None) -> tuple[int, int]:
    """The family's window, its ceiling pulled under the lead's line.

    lead_notes are the melody's pitches in the pattern; the ceiling becomes
    their lower quartile less one, so the harmony's top voice stays under
    where the lead mostly plays rather than under a fixed label.
    """
    _, _, _, lo, hi = family_register(family)
    if lead_notes:
        ordered = sorted(lead_notes)
        q25 = ordered[len(ordered) // 4]
        hi = max(WINDOW_FLOOR_HIGH, min(hi, q25 - 1))
    return lo, hi


def voice_chord(chord_notes: list[int], num_voices: int, anchor_shift: int = 0,
                anchors: list[int] | None = None,
                window: tuple[int, int] = (HARMONY_LOW, HARMONY_HIGH)) -> list[int]:
    """Place num_voices chord tones near fixed register anchors.

    Picking the chord tone nearest a constant anchor, rather than always
    stacking root position, is what produces voice leading: because the
    anchors do not move between chords, consecutive chords in a progression
    keep their common tones and shift the rest by a step or two. It also
    yields inversions for free, so a song stops being four root triads.

    Two rules on top of nearest-to-anchor keep the chord a chord: a voice
    does not double a pitch class while a chord tone is still missing, and
    the last voice carries the chord's colour tone (its third, or the
    fourth of a sus4) when no other voice has it. Without them a two-voice
    pad was a bare fifth and a wide three-voice one root-fifth-octave.
    """
    lo, hi = window
    if anchors is None:
        anchors = [VOICE_ANCHORS_BASE + anchor_shift + VOICE_ANCHOR_SPREAD * i
                   for i in range(num_voices)]
    pcs = [cn % 12 for cn in chord_notes]
    colour = None
    if len(pcs) > 1 and (pcs[1] - pcs[0]) % 12 in (3, 4, 5):
        colour = pcs[1]
    pitches = sorted({
        pc + 12 * octave
        for pc in set(pcs)
        for octave in range(2, 8)
        if lo <= pc + 12 * octave <= hi
    })
    if not pitches:
        return []

    chosen: list[int] = []
    for i in range(num_voices):
        target = anchors[i] if i < len(anchors) else anchors[-1] + 7 * (i - len(anchors) + 1)
        remaining = [p for p in pitches if p not in chosen]
        if not remaining:
            break
        covered = {p % 12 for p in chosen}
        missing = set(pcs) - covered
        last = i == num_voices - 1

        def cost(p: int) -> int:
            c = abs(p - target)
            if p % 12 in covered and missing:
                c += 5
            if last and colour is not None and colour not in covered and p % 12 != colour:
                c += 4
            return c
        chosen.append(min(remaining, key=cost))
    return sorted(chosen)


# ── Stab length ──
# How long a stab holds, in ms, per family: the hard voices gated short the
# way the games do it, the slow ones long enough to finish their swell and
# speak. Before, every stab was cut after six rows whatever the voice, and
# the per-tick volume slide under it had the note gone in 250 ms anyway:
# Strike of the Factory's strings swelled for 100 ms and were silent by
# 260 (measured on the rendered part): the quack heard on the release listen.
STAB_MS = {
    "brass": 180, "lead": 150, "psg": 150, "keys": 170, "organ": 170, "struck": 150,
    "flute": 350, "strings": 700, "choir": 700, "pad": 900,
}
STAB_MS_DEFAULT = 250


def stab_rows(family: str | None, onset_ms: float, row_ms: float, interval: int = 16) -> int:
    """Rows a stab holds: the family's length or three times the voice's
    attack, whichever is longer, in rows, never under an eighth note (two
    rows: at 102 BPM a one-row brass stab was a 147 ms blip and then two
    seconds of nothing), leaving two rows before the next hit."""
    ms = max(STAB_MS.get(family, STAB_MS_DEFAULT), 3.0 * onset_ms)
    return max(2, min(interval - 2, round(ms / row_ms)))


# ── Level ──
# Harmony level per family, relative to a pad's. Measured 2026-10-17 by
# rendering every harmony-pool preset on one three-voice figure (C4 E4 G4 at
# volume 22, held and as 200 ms stabs) and reading ebur128: held chords land
# within 1.5 dB across every sustaining family (the sample normalisation
# already equalises K-weighted loudness), so those sit at 1.0. Brass keeps
# a 2 dB trim by ear (it was 3 against a strings stab the volume slide
# killed in 250 ms): at equal loudness it still reads forward, its energy
# being in the presence band. Struck voices measured 1-3 dB under the
# strings on a stab (their energy is in the attack); the orchestra hit, a
# one-shot left at its natural level, measured 12 dB under everything.
FAMILY_LEVEL = {"brass": 0.8, "keys": 1.15, "struck": 1.15}
PRESET_LEVEL = {"mmx_orch_hit": 2.5}
# Per-voice scale by voice count, so a two- or three-voice chord sums to
# about the level of one voice (a chord's voices add in power).
VOICES_LEVEL = {1: 1.0, 2: 0.8, 3: 0.68}
# A hit shorter than the ear's integration time (about 200 ms) is heard
# under its written level, by the square root of the ratio: a chug's
# one-row hit at 180 BPM (83 ms) is written up 1.55, a brass stab of two
# rows barely, a held chord not at all. Capped at 1.6. Northern Dawn's
# gallop, written flat, measured 12 dB under the lead where the review
# set's stabs and pads sat at six to ten.
EAR_MS = 200.0
HIT_LEVEL_CAP = 1.6


def hit_level(hold_ms: float) -> float:
    if hold_ms <= 0 or hold_ms >= EAR_MS:
        return 1.0
    return min(HIT_LEVEL_CAP, (EAR_MS / hold_ms) ** 0.5)


def harmony_level(family: str | None, preset: str | None, num_voices: int,
                  hold_ms: float = EAR_MS) -> float:
    return (FAMILY_LEVEL.get(family, 1.0) * PRESET_LEVEL.get(preset, 1.0)
            * VOICES_LEVEL.get(num_voices, 0.68) * hit_level(hold_ms))


def generate_harmony(chord_notes: list[int], rows: int,
                     voicing: str = "stabs",
                     num_voices: int = 2, anchor_shift: int = 0,
                     anchors: list[int] | None = None,
                     window: tuple[int, int] = (HARMONY_LOW, HARMONY_HIGH),
                     cut_after: int | None = None) -> list[list[tuple[int, int]]]:
    """
    Generate harmony parts for multiple channels.

    Returns a list of note lists, one per voice: [[(row, midi_note), ...], ...]
    Voice 0 = lowest, Voice N = highest.
    Note-cut events are included as (row, -1) tuples.
    cut_after overrides the voicing's hold (the builder sets a stab's from
    the voice).
    """
    # Get voicing config
    config = HARMONY_VOICINGS.get(voicing, HARMONY_VOICINGS["stabs"])
    interval = config["interval"]
    if cut_after is None:
        cut_after = config["cut_after"]

    voice_notes = voice_chord(chord_notes, num_voices, anchor_shift, anchors, window)
    if not voice_notes:
        return []

    # Generate note events for each voice
    result = []
    if "steps" in config:
        # Ostinato: every cell restates the chord tone on the cell's steps.
        cell, steps = config["cell"], config["steps"]
        offset_upper = config.get("offset_upper", 0)
        for voice_idx, base_note in enumerate(voice_notes):
            notes = []
            shift = offset_upper if voice_idx > 0 else 0
            hits = [r + st + shift for r in range(0, rows, cell) for st in steps
                    if r + st + shift < rows]
            for n, row in enumerate(hits):
                notes.append((row, base_note))
                nxt = hits[n + 1] if n + 1 < len(hits) else rows
                cut_row = row + cut_after
                if cut_row < nxt and cut_row < rows:
                    notes.append((cut_row, -1))
            result.append(notes)
        return result
    for voice_idx, base_note in enumerate(voice_notes):
        notes = []
        for row in range(0, rows, interval):
            # The strum of the rhythmic voicing used to be a one-row offset
            # on the upper voices (a tenth of a second at 144 BPM: a flam,
            # not a strum). The voices now share the row and the builder
            # delays the upper ones by a tick with the note-delay effect.
            actual_row = row

            notes.append((actual_row, base_note))

            # Add note-cut so notes don't ring indefinitely
            cut_row = actual_row + cut_after
            if cut_row < rows and cut_row < actual_row + interval:
                notes.append((cut_row, -1))  # -1 signals note-cut
        result.append(notes)

    return result


def generate_harmony_timeline(segments: list[tuple[int, int, list[int]]],
                              voicing: str = "stabs",
                              num_voices: int = 2, anchor_shift: int = 0,
                              anchors: list[int] | None = None,
                              window: tuple[int, int] = (HARMONY_LOW, HARMONY_HIGH),
                              cut_after: int | None = None) -> list[list[tuple[int, int]]]:
    """generate_harmony over a chord timeline.

    segments is [(start_row, end_row, chord_notes), ...]. Each segment is
    voiced on its own, so a chord change mid-pattern restates the harmony on
    the new chord, and the fixed anchors in voice_chord still give smooth
    voice leading across the change.
    """
    voices: list[list[tuple[int, int]]] = []
    for start, end, chord_notes in segments:
        part = generate_harmony(chord_notes, end - start, voicing, num_voices, anchor_shift,
                                anchors, window, cut_after)
        for v_idx, notes in enumerate(part):
            while len(voices) <= v_idx:
                voices.append([])
            voices[v_idx].extend((start + row, note) for row, note in notes)
    return voices
