"""
Bass generation. (Arpeggios live in arp.py.)
"""

import random

from . import theory
from .pattern import ROWS_PER_BAR, ROWS_PER_BEAT


# Riffs: (row in bar, interval from the root) of a one-bar figure that
# repeats. Intervals stay chord-safe (root, fifth, octave, seventh), so a riff
# fits major and minor alike. One riff per song, drawn by the composer from
# the pack's weights; a stage theme has its own riff, not the game's.
RIFFS = {
    "rock":         [(0, 0), (2, 0), (4, 12), (6, 0), (8, 0), (10, 7), (12, 12), (14, 7)],
    "gallop":       [(0, 0), (3, 0), (4, 0), (6, 12), (8, 0), (11, 0), (12, 0), (14, 7)],
    "funk":         [(0, 0), (3, 12), (6, 0), (10, 7), (12, 0), (14, 10)],
    "pedal_push":   [(0, 0), (2, 0), (4, 0), (6, 0), (7, 12), (8, 0), (10, 0), (12, 0), (14, 12)],
    "octaves":      [(0, 0), (2, 12), (4, 0), (6, 12), (8, 0), (10, 12), (12, 7), (14, 12)],
    "fifth_bounce": [(0, 0), (2, 7), (4, 0), (6, 7), (8, 12), (10, 7), (12, 0), (14, 7)],
    "drop":         [(0, 0), (2, 0), (6, 0), (8, 12), (10, 10), (12, 7), (14, 0)],
}
RIFF = RIFFS["rock"]


def generate_bass(root: int, chord_type: str,
                  rows: int, style: str = "steady",
                  weight: str = "heavy",
                  density: float = 1.0, riff: str | None = None,
                  scale_notes: list[int] | None = None) -> list[tuple[int, int]]:
    """Generate a bass line. Returns [(row, midi_note), ...].

    density (0..1) thins the off-beat notes. The line previously played every
    slot its style produced, unconditionally, for every pattern in the song —
    the same "never rests" problem the arp had. Bar downbeats are always kept,
    since the bass has to state the chord.
    """
    # Register depends on weight
    if weight == "light":
        # Octave 3-4 (MIDI 48-71) — punchier, more melodic
        bass_root = root
        while bass_root >= 60:
            bass_root -= 12
        while bass_root < 48:
            bass_root += 12
    elif weight == "medium":
        # Octave 3 (MIDI 42-59) — middle ground
        bass_root = root
        while bass_root >= 54:
            bass_root -= 12
        while bass_root < 42:
            bass_root += 12
    else:
        # Octave 2-3 (MIDI 36-59) — deep and heavy
        bass_root = root
        while bass_root >= 48:
            bass_root -= 12
        while bass_root < 36:
            bass_root += 12

    chord = theory.build_chord(bass_root, chord_type)
    notes = []

    # Sparser step sizes for lighter weights
    if weight == "light":
        step_scale = 2  # half as many notes
    elif weight == "medium":
        step_scale = 1.5
    else:
        step_scale = 1

    if style == "steady":
        step = int(8 * step_scale)
        for row in range(0, rows, step):
            notes.append((row, bass_root))
    elif style == "octave":
        step = int(4 * step_scale)
        for i, row in enumerate(range(0, rows, step)):
            if i % 2 == 0:
                notes.append((row, bass_root))
            else:
                notes.append((row, bass_root + 12))
    elif style == "walking":
        step = int(4 * step_scale)
        for i, row in enumerate(range(0, rows, step)):
            note = chord[i % len(chord)]
            notes.append((row, note))
    elif style == "driving":
        step = int(2 * step_scale)
        for row in range(0, rows, step):
            notes.append((row, bass_root))
    elif style == "drone":
        # One note per chord, held for the whole segment; the composer slides
        # between roots (porta) so the drone moves without restriking.
        notes.append((0, bass_root))
    elif style == "riff":
        # A one-bar riff that repeats: root on the beat, the octave and the
        # fifth pushing between, the way a rock bass carries a stage theme.
        figure = RIFFS.get(riff or "rock", RIFF)
        # A riff's seventh is only in key for minor, dorian, mixolydian and
        # minor pentatonic; in a major key it sat a semitone under the
        # melody's note. Snap every interval to the nearest scale tone at or
        # below it, so the seventh becomes the sixth where that is the key's
        # note and stays a seventh where it is.
        classes = {n % 12 for n in scale_notes} if scale_notes else None
        for bar in range(0, rows, ROWS_PER_BAR):
            for off, iv in figure:
                if bar + off >= rows:
                    continue
                note = bass_root + iv
                if classes and note % 12 not in classes:
                    while note % 12 not in classes and note > bass_root - 12:
                        note -= 1
                notes.append((bar + off, note))

    # A riff is a figure and repeats exactly; the thinning that lets the
    # other styles rest would make it stumble from bar to bar.
    if density < 1.0 and style != "riff":
        notes = [
            (row, note) for row, note in notes
            if row % ROWS_PER_BAR == 0 or random.random() < density
        ]

    return notes


def pick_section_bass(bass_weight: str, section_energy: float,
                      bass_style: str) -> str:
    """Choose bass style for a section based on weight and energy."""
    if bass_style in ("drone", "riff"):
        return bass_style              # a drone or a riff does not lift with the section
    if bass_weight == "light":
        if section_energy > 0.85:
            return random.choice(["steady", "walking"])
        return random.choice(["steady", "steady", "walking"])
    elif section_energy < 0.5:
        return random.choice(["steady", "steady"])
    elif section_energy > 0.85:
        return random.choice(["driving", "octave", bass_style])
    return bass_style


def generate_bass_timeline(segments: list[tuple[int, int, int, str]],
                           style: str = "steady", weight: str = "heavy",
                           density: float = 1.0,
                           riff: str | None = None,
                           scale_notes: list[int] | None = None) -> list[tuple[int, int]]:
    """generate_bass over [(start_row, end_row, root, chord_type), ...]."""
    notes = []
    for start, end, root, chord_type in segments:
        part = generate_bass(root, chord_type, end - start, style, weight, density, riff=riff,
                             scale_notes=scale_notes)
        notes.extend((start + row, note) for row, note in part)
    return notes
