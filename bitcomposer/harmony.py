"""
Harmony generation: chord voicings and multi-voice harmony parts.
"""

import random


HARMONY_VOICINGS = {
    "stabs": {
        "description": "Short chord stabs every 16 rows",
        "interval": 16,
        "cut_after": 6,
    },
    "sustain": {
        "description": "Sustained pad chords, held across the pattern",
        "interval": 32,
        "cut_after": 24,
    },
    "rhythmic": {
        "description": "Rhythmic chord hits synced to groove",
        "interval": 8,
        "cut_after": 4,
    },
}


# Fixed register anchors for the harmony voices, roughly a fifth apart and an
# octave under the melody's 60-83 range.
VOICE_ANCHORS_BASE = 52
VOICE_ANCHOR_SPREAD = 7

# Playable window for harmony pitches. The ceiling keeps the top voice below
# the melody's 60-83 range so harmony stays underneath the lead.
HARMONY_LOW, HARMONY_HIGH = 45, 72


def voice_chord(chord_notes: list[int], num_voices: int) -> list[int]:
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
        target = VOICE_ANCHORS_BASE + VOICE_ANCHOR_SPREAD * i
        remaining = [p for p in pitches if p not in chosen]
        if not remaining:
            break
        chosen.append(min(remaining, key=lambda p: abs(p - target)))
    return sorted(chosen)


def generate_harmony(chord_notes: list[int], rows: int,
                     voicing: str = "stabs",
                     num_voices: int = 2) -> list[list[tuple[int, int]]]:
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

    voice_notes = voice_chord(chord_notes, num_voices)
    if not voice_notes:
        return []

    # Generate note events for each voice
    result = []
    for voice_idx, base_note in enumerate(voice_notes):
        notes = []
        for row in range(0, rows, interval):
            # Add slight variation in timing for rhythmic feel
            actual_row = row
            if voicing == "rhythmic" and voice_idx > 0 and row % 16 == 8:
                # Offset higher voices slightly for strum effect
                actual_row = min(row + 1, rows - 1)

            notes.append((actual_row, base_note))

            # Add note-cut so notes don't ring indefinitely
            cut_row = actual_row + cut_after
            if cut_row < rows and cut_row < actual_row + interval:
                notes.append((cut_row, -1))  # -1 signals note-cut
        result.append(notes)

    return result
