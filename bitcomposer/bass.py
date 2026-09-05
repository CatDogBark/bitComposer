"""
Bass and arpeggio generation.
"""

import random

from . import theory
from .pattern import ROWS_PER_BAR, ROWS_PER_BEAT


def generate_bass(root: int, chord_type: str,
                  rows: int, style: str = "steady",
                  weight: str = "heavy",
                  density: float = 1.0) -> list[tuple[int, int]]:
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

    if density < 1.0:
        notes = [
            (row, note) for row, note in notes
            if row % ROWS_PER_BAR == 0 or random.random() < density
        ]

    return notes


def generate_arpeggio(chord_notes: list[int], rows: int,
                      style: str = "up",
                      density: float = 1.0) -> list[tuple[int, int]]:
    """Generate an arpeggio pattern. Returns [(row, midi_note), ...].

    density (0..1) controls how much of the pattern the arp actually plays.
    It previously ran flat out on every row of every pattern regardless of
    section, which made it roughly four times denser than the melody it is
    meant to sit behind — the arp became the track and the melody decoration.
    Gating whole bars keeps the figure recognisable while letting it breathe.
    """
    # Arp in octave 4-5
    arp_notes = []
    for n in chord_notes:
        for octave_shift in [0, 12]:
            note = n + octave_shift
            if 48 <= note <= 84:
                arp_notes.append(note)
    arp_notes.sort()

    if not arp_notes:
        return []

    if style == "down":
        seq = list(reversed(arp_notes))
    elif style == "updown" and len(arp_notes) > 2:
        seq = arp_notes + list(reversed(arp_notes[1:-1]))
    else:
        seq = arp_notes

    density = max(0.0, min(1.0, density))
    # Eighths only when there is energy for them; quarters when there is not.
    step = 2 if density > 0.6 else 4

    notes = []
    idx = 0
    for bar_start in range(0, rows, ROWS_PER_BAR):
        if random.random() > density:
            continue  # this bar rests
        # Even in a busy bar, drop the last beat often enough that the figure
        # has somewhere to land instead of running continuously into the next.
        bar_len = ROWS_PER_BAR
        if random.random() < 0.35:
            bar_len -= ROWS_PER_BEAT
        for offset in range(0, bar_len, step):
            row = bar_start + offset
            if row >= rows:
                break
            if style == "random":
                notes.append((row, random.choice(arp_notes)))
            else:
                notes.append((row, seq[idx % len(seq)]))
                idx += 1

    return notes


def pick_section_bass(bass_weight: str, section_energy: float,
                      bass_style: str) -> str:
    """Choose bass style for a section based on weight and energy."""
    if bass_weight == "light":
        if section_energy > 0.85:
            return random.choice(["steady", "walking"])
        return random.choice(["steady", "steady", "walking"])
    elif section_energy < 0.5:
        return random.choice(["steady", "steady"])
    elif section_energy > 0.85:
        return random.choice(["driving", "octave", bass_style])
    return bass_style
