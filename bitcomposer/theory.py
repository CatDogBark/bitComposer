"""
Music theory primitives: notes, scales, chords, progressions.

All note values are MIDI note numbers (C-5 = 60).
"""

import random

# Note name to semitone offset from C
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Scale intervals (semitones from root)
SCALES = {
    "minor_pentatonic": [0, 3, 5, 7, 10],
    "major_pentatonic": [0, 2, 4, 7, 9],
    "natural_minor":    [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor":   [0, 2, 3, 5, 7, 8, 11],
    "dorian":           [0, 2, 3, 5, 7, 9, 10],
    "mixolydian":       [0, 2, 4, 5, 7, 9, 10],
    "major":            [0, 2, 4, 5, 7, 9, 11],
    "phrygian":         [0, 1, 3, 5, 7, 8, 10],
}

# Chord progressions as scale degree offsets (0-indexed).
#
# Each entry is (degree, chord_type) or (degree, chord_type, semitones): the
# optional third element shifts the chord root chromatically, which is how
# borrowed chords and secondary dominants are spelled. In major, degree 6 is
# the leading tone, so (6, "major", -1) is bVII and (5, "major", -1) is bVI —
# the two chords game music leans on hardest and that a purely diatonic table
# could never produce. (1, "major") in major is II, i.e. V of V.
#
# Pentatonic scales have five degrees, so their tables index only 0-4. The old
# fallback gave major_pentatonic the natural-minor table, whose degrees 5 and 6
# wrapped into the next octave and whose minor chords sat on a major scale.
PROGRESSIONS = {
    "minor_pentatonic": [
        [(0, "power"), (3, "power"), (4, "power"), (0, "power")],   # i-v-VII-i
        [(0, "power"), (2, "power"), (3, "power"), (4, "power")],   # i-iv-v-VII
        [(0, "power"), (4, "power"), (3, "power"), (2, "power")],   # i-VII-v-iv
        [(0, "minor"), (1, "major"), (2, "minor"), (4, "major")],   # i-III-iv-VII
    ],
    "major_pentatonic": [
        [(0, "power"), (3, "power"), (4, "power"), (0, "power")],   # I-V-vi-I
        [(0, "major"), (4, "minor"), (1, "minor"), (3, "major")],   # I-vi-ii-V
        [(0, "major"), (3, "major"), (4, "minor"), (3, "major")],   # I-V-vi-V
        [(0, "power"), (1, "power"), (3, "power"), (0, "power")],   # I-ii-V-I
    ],
    "natural_minor": [
        [(0, "minor"), (5, "major"), (3, "minor"), (4, "minor")],   # i-VI-iv-v
        [(0, "minor"), (3, "minor"), (5, "major"), (4, "power")],   # i-iv-VI-v
        [(0, "minor"), (4, "minor"), (5, "major"), (6, "major")],   # i-v-VI-VII
        [(0, "minor"), (6, "major"), (5, "major"), (4, "minor")],   # i-VII-VI-v
        [(0, "minor"), (5, "major"), (2, "major"), (6, "major")],   # i-VI-III-VII
        [(0, "minor"), (6, "major"), (5, "major"), (4, "major")],   # i-VII-VI-V  (Andalusian)
        [(0, "minor"), (3, "minor"), (4, "major"), (0, "minor")],   # i-iv-V-i    (V borrowed)
    ],
    "dorian": [
        [(0, "minor"), (1, "minor"), (2, "major"), (4, "minor")],   # i-ii-III-v
        [(0, "minor"), (3, "major"), (1, "minor"), (4, "minor")],   # i-IV-ii-v
        [(0, "minor"), (3, "major"), (0, "minor"), (6, "major")],   # i-IV-i-VII
    ],
    "major": [
        [(0, "major"), (3, "major"), (4, "major"), (0, "major")],   # I-IV-V-I
        [(0, "major"), (5, "minor"), (3, "major"), (4, "major")],   # I-vi-IV-V
        [(0, "major"), (2, "minor"), (3, "major"), (4, "major")],   # I-iii-IV-V
        [(0, "major"), (4, "major"), (5, "minor"), (3, "major")],   # I-V-vi-IV
        [(0, "major"), (6, "major", -1), (3, "major"), (0, "major")],      # I-bVII-IV-I
        [(0, "major"), (5, "major", -1), (6, "major", -1), (0, "major")],  # I-bVI-bVII-I
        [(0, "major"), (1, "major"), (4, "major"), (0, "major")],          # I-II(V/V)-V-I
        [(0, "major"), (2, "major"), (5, "minor"), (3, "major")],          # I-III(V/vi)-vi-IV
    ],
    "mixolydian": [
        [(0, "major"), (6, "major"), (3, "major"), (0, "major")],   # I-VII-IV-I
        [(0, "major"), (4, "minor"), (6, "major"), (3, "major")],   # I-v-VII-IV
        [(0, "major"), (3, "major"), (6, "major"), (0, "major")],   # I-IV-VII-I
    ],
    "harmonic_minor": [
        [(0, "minor"), (4, "major"), (3, "minor"), (0, "minor")],   # i-V-iv-i
        [(0, "minor"), (3, "minor"), (4, "major"), (0, "minor")],   # i-iv-V-i
        [(0, "minor"), (5, "major"), (4, "major"), (0, "minor")],   # i-VI-V-i
    ],
    "phrygian": [
        [(0, "minor"), (1, "major"), (0, "minor"), (6, "minor")],   # i-II-i-vii
        [(0, "minor"), (1, "major"), (4, "minor"), (3, "minor")],   # i-II-v-iv
        [(0, "minor"), (6, "minor"), (1, "major"), (0, "minor")],   # i-vii-II-i
    ],
}

# Default to natural_minor for scales without explicit progressions
for scale in SCALES:
    if scale not in PROGRESSIONS:
        PROGRESSIONS[scale] = PROGRESSIONS["natural_minor"]


def unpack_chord(entry) -> tuple[int, str, int]:
    """Normalise a progression entry to (degree, chord_type, semitone_shift)."""
    if len(entry) == 2:
        return entry[0], entry[1], 0
    return entry[0], entry[1], entry[2]


def chord_root_for(key: int, scale_notes: list[int], entry) -> int:
    """MIDI root of a progression entry in the given key and scale."""
    degree, _, shift = unpack_chord(entry)
    if degree < len(scale_notes):
        return key + (scale_notes[degree] - scale_notes[0]) + shift
    return key + shift


def secondary_chord(scale_name: str, entry, next_entry):
    """Pick a chord for the back half of a pattern.

    Each pattern carried one chord for four bars, so a four-chord progression
    took sixteen bars to come round — a harmonic rhythm nothing in game music
    uses. The back two bars now move: either anticipate the next chord of the
    progression, step to the chord a fourth above (the plagal neighbour), or
    lean on the dominant of the current chord. All of them resolve naturally
    into the next pattern. Returns a progression entry.
    """
    degree, chord_type, shift = unpack_chord(entry)
    n = len(SCALES[scale_name])
    intervals = SCALES[scale_name]

    def diatonic_quality(deg: int) -> str:
        """Major or minor as the scale spells the triad on that degree."""
        root = intervals[deg % n]
        third = intervals[(deg + 2) % n] - root
        if third < 0:
            third += 12
        if third == 4:
            return "major"
        if third == 3:
            return "minor"
        return "power"

    options = []
    if next_entry is not None and unpack_chord(next_entry)[:2] != (degree, chord_type):
        options.append(("next", next_entry))
    # A fourth above: three scale steps up in a seven-note scale, two in a
    # five-note one. Keep the chromatic shift so a borrowed chord's neighbour
    # stays in its world.
    up = (degree + (3 if n == 7 else 2)) % n
    options.append(("plagal", (up, diatonic_quality(up), shift)))
    if n == 7:
        # Dominant of the current chord: four scale steps up, forced major.
        dom = (degree + 4) % n
        options.append(("dominant", (dom, "major", shift)))

    _, chosen = random.choice(options)
    return chosen

# Chord intervals from root
CHORD_INTERVALS = {
    "major": [0, 4, 7],
    "minor": [0, 3, 7],
    "power": [0, 7],
    "dim":   [0, 3, 6],
    "aug":   [0, 4, 8],
    "sus4":  [0, 5, 7],
    "7th":   [0, 4, 7, 10],
}

def add_chord_color(progression: list[tuple[int, str]],
                    chance: float = 0.4) -> list[tuple[int, str]]:
    """Enrich some triads into 7ths and sus4s.

    PROGRESSIONS only ever spelled major, minor and power, so 7th, sus4, dim
    and aug were defined in CHORD_INTERVALS and reached the output never. The
    turnaround chord takes a 7th, which is where a dominant seventh belongs;
    elsewhere a sus4 stands in occasionally, and it sits over either quality
    because it has no third.
    """
    if not progression:
        return progression

    out = []
    last = len(progression) - 1
    for i, entry in enumerate(progression):
        degree, chord_type, shift = unpack_chord(entry)
        if random.random() < chance:
            if i == last and chord_type == "major":
                chord_type = "7th"
            elif chord_type in ("major", "minor"):
                chord_type = "sus4"
        out.append((degree, chord_type, shift) if shift else (degree, chord_type))
    return out


def note_name(midi_note: int) -> str:
    """Convert MIDI note number to name like C-5, D#3."""
    octave = (midi_note // 12) - 1
    name = NOTE_NAMES[midi_note % 12]
    return f"{name}{octave}"



def build_scale(root: int, scale_name: str, octaves: int = 2) -> list[int]:
    """Build a scale across multiple octaves from a root MIDI note."""
    intervals = SCALES[scale_name]
    notes = []
    for octave in range(octaves):
        for interval in intervals:
            note = root + interval + (octave * 12)
            if note <= 127:
                notes.append(note)
    return notes


def build_chord(root: int, chord_type: str) -> list[int]:
    """Build a chord from a root note."""
    return [root + i for i in CHORD_INTERVALS[chord_type] if root + i <= 127]



def random_key() -> int:
    """Pick a random root note in octave 4 (MIDI 48-59)."""
    return 48 + random.randint(0, 11)


def random_scale() -> str:
    """Pick a random scale weighted toward game-music-friendly ones."""
    weights = {
        "minor_pentatonic": 20,
        "natural_minor": 15,
        "dorian": 15,
        "major_pentatonic": 10,
        "harmonic_minor": 10,
        "mixolydian": 10,
        "major": 10,
        "phrygian": 10,
    }
    names = list(weights.keys())
    w = [weights[n] for n in names]
    return random.choices(names, weights=w, k=1)[0]


def random_progression(scale_name: str) -> list[tuple[int, str]]:
    """Pick a random chord progression for the given scale."""
    progs = PROGRESSIONS.get(scale_name, PROGRESSIONS["natural_minor"])
    return random.choice(progs)


def random_alternate_progression(scale_name: str,
                                  main_prog: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Pick an alternate progression different from the main one, for verse/chorus contrast."""
    progs = PROGRESSIONS.get(scale_name, PROGRESSIONS["natural_minor"])
    alternates = [p for p in progs if p != main_prog]
    if alternates:
        return random.choice(alternates)
    # If no alternate, rotate the main progression
    return main_prog[1:] + main_prog[:1]



def random_tempo() -> int:
    """Pick a random tempo appropriate for game music (100-160 BPM)."""
    return random.randint(100, 160)
