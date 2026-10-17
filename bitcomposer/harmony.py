"""
Harmony generation: chord voicings and multi-voice harmony parts.
"""


HARMONY_VOICINGS = {
    "stabs": {
        "description": "Short chord stabs every 16 rows",
        "interval": 16,
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


# Fixed register anchors for the harmony voices, roughly a fifth apart and an
# octave under the melody's 60-83 range.
VOICE_ANCHORS_BASE = 52
VOICE_ANCHOR_SPREAD = 7

# Playable window for harmony pitches. The ceiling keeps the top voice below
# the melody's 60-83 range so harmony stays underneath the lead.
HARMONY_LOW, HARMONY_HIGH = 45, 72


def voice_chord(chord_notes: list[int], num_voices: int, anchor_shift: int = 0) -> list[int]:
    """Place num_voices chord tones near fixed register anchors.

    Picking the chord tone nearest a constant anchor, rather than always
    stacking root position, is what produces voice leading: because the
    anchors do not move between chords, consecutive chords in a progression
    keep their common tones and shift the rest by a step or two. It also
    yields inversions for free, so a song stops being four root triads.
    """
    pitches = sorted({
        pc + 12 * octave
        for pc in {cn % 12 for cn in chord_notes}
        for octave in range(3, 7)
        if HARMONY_LOW <= pc + 12 * octave <= HARMONY_HIGH
    })
    if not pitches:
        return []

    chosen: list[int] = []
    for i in range(num_voices):
        target = VOICE_ANCHORS_BASE + anchor_shift + VOICE_ANCHOR_SPREAD * i
        remaining = [p for p in pitches if p not in chosen]
        if not remaining:
            break
        chosen.append(min(remaining, key=lambda p: abs(p - target)))
    return sorted(chosen)


def generate_harmony(chord_notes: list[int], rows: int,
                     voicing: str = "stabs",
                     num_voices: int = 2, anchor_shift: int = 0) -> list[list[tuple[int, int]]]:
    """
    Generate harmony parts for multiple channels.

    Returns a list of note lists, one per voice: [[(row, midi_note), ...], ...]
    Voice 0 = lowest, Voice N = highest.
    Note-cut events are included as (row, -1) tuples.
    """
    # Get voicing config
    config = HARMONY_VOICINGS.get(voicing, HARMONY_VOICINGS["stabs"])
    interval = config["interval"]
    cut_after = config["cut_after"]

    voice_notes = voice_chord(chord_notes, num_voices, anchor_shift)
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
                              num_voices: int = 2, anchor_shift: int = 0) -> list[list[tuple[int, int]]]:
    """generate_harmony over a chord timeline.

    segments is [(start_row, end_row, chord_notes), ...]. Each segment is
    voiced on its own, so a chord change mid-pattern restates the harmony on
    the new chord, and the fixed anchors in voice_chord still give smooth
    voice leading across the change.
    """
    voices: list[list[tuple[int, int]]] = []
    for start, end, chord_notes in segments:
        part = generate_harmony(chord_notes, end - start, voicing, num_voices, anchor_shift)
        for v_idx, notes in enumerate(part):
            while len(voices) <= v_idx:
                voices.append([])
            voices[v_idx].extend((start + row, note) for row, note in notes)
    return voices
