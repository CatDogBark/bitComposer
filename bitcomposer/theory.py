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
# Each tuple is (degree, chord_type) where chord_type is "major", "minor", "power".
# These are common progressions that sound good in game music.
PROGRESSIONS = {
    "minor_pentatonic": [
        [(0, "power"), (3, "power"), (4, "power"), (0, "power")],
        [(0, "power"), (2, "power"), (3, "power"), (4, "power")],
        [(0, "power"), (4, "power"), (3, "power"), (2, "power")],
    ],
    "natural_minor": [
        [(0, "minor"), (5, "major"), (3, "major"), (4, "minor")],  # i-VI-IV-v
        [(0, "minor"), (3, "major"), (5, "major"), (4, "power")],  # i-iv-VI-v
        [(0, "minor"), (4, "minor"), (5, "major"), (6, "major")],  # i-v-VI-VII
        [(0, "minor"), (6, "major"), (5, "major"), (4, "minor")],  # i-VII-VI-v
    ],
    "dorian": [
        [(0, "minor"), (1, "minor"), (2, "major"), (4, "minor")],
        [(0, "minor"), (3, "major"), (1, "minor"), (4, "minor")],
    ],
    "major": [
        [(0, "major"), (3, "major"), (4, "major"), (0, "major")],  # I-IV-V-I
        [(0, "major"), (4, "minor"), (3, "major"), (4, "major")],  # I-vi-IV-V
        [(0, "major"), (2, "minor"), (3, "major"), (4, "major")],  # I-iii-IV-V
    ],
    "mixolydian": [
        [(0, "major"), (6, "major"), (3, "major"), (0, "major")],
        [(0, "major"), (4, "minor"), (6, "major"), (3, "major")],
    ],
    "harmonic_minor": [
        [(0, "minor"), (4, "major"), (3, "major"), (0, "minor")],  # i-V-iv-i
        [(0, "minor"), (3, "major"), (4, "major"), (0, "minor")],  # i-iv-V-i
    ],
    "phrygian": [
        [(0, "minor"), (1, "major"), (0, "minor"), (6, "minor")],
        [(0, "minor"), (1, "major"), (4, "minor"), (3, "major")],
    ],
}

# Default to natural_minor for scales without explicit progressions
for scale in SCALES:
    if scale not in PROGRESSIONS:
        PROGRESSIONS[scale] = PROGRESSIONS["natural_minor"]

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

# Drum pattern templates (16 steps, 1 = hit, 0 = rest)
# Each is a dict of {drum_name: pattern}
DRUM_PATTERNS = [
    {  # Standard rock
        "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hat":   [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    },
    {  # Driving
        "kick":  [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hat":   [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    },
    {  # Syncopated
        "kick":  [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0],
        "hat":   [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    },
    {  # Double-time
        "kick":  [1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "hat":   [1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1],
    },
    {  # Half-time heavy
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        "hat":   [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    },
    {  # Funky
        "kick":  [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1],
        "hat":   [1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0],
    },
]

# Sparse variants for breakdowns and low-density sections (less busy).
# These keep a half-time backbeat on beat 3: intro and outro sections disable
# drums entirely via LAYERS, so anything reaching here is a main section that
# still needs a pulse. Leaving the snare row empty gave whole songs no snare.
DRUM_PATTERNS_SPARSE = [
    {
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        "hat":   [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    },
    {
        "kick":  [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        "snare": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        "hat":   [1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0],
    },
]

# Busy variants for choruses/intense sections
DRUM_PATTERNS_BUSY = [
    {
        "kick":  [1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0],
        "hat":   [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    },
    {
        "kick":  [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0],
        "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1],
        "hat":   [1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],
    },
]

# Fill patterns (16 steps) — played at section transitions
DRUM_FILLS = [
    {  # Snare roll
        "kick":  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1],
        "hat":   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "tom":   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "crash": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
    {  # Tom cascade
        "kick":  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        "hat":   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "tom":   [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1],
        "crash": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
    {  # Build to crash
        "kick":  [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        "snare": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1],
        "hat":   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "tom":   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "crash": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    },
    {  # Kick snare flurry
        "kick":  [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0],
        "snare": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1],
        "hat":   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "tom":   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "crash": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
]


def random_drum_fill() -> dict[str, list[int]]:
    """Pick a random drum fill pattern."""
    return random.choice(DRUM_FILLS)


def random_drum_pattern_for_section(section: str, base_pattern: dict,
                                     density: str = "normal") -> dict:
    """Pick a drum pattern appropriate for the section and density."""
    if density == "sparse" or section in ("intro", "outro"):
        return random.choice(DRUM_PATTERNS_SPARSE)
    elif density == "busy" or section == "chorus":
        return random.choice(DRUM_PATTERNS_BUSY)
    elif section == "bridge":
        # Bridge can go either way
        return random.choice([base_pattern] + DRUM_PATTERNS_SPARSE)
    return base_pattern


def note_name(midi_note: int) -> str:
    """Convert MIDI note number to name like C-5, D#3."""
    octave = (midi_note // 12) - 1
    name = NOTE_NAMES[midi_note % 12]
    return f"{name}{octave}"


def note_from_name(name: str) -> int:
    """Convert note name like 'C5' or 'D#3' to MIDI note number."""
    for i, n in enumerate(NOTE_NAMES):
        if name.startswith(n) and name[len(n):].lstrip("-").isdigit():
            octave = int(name[len(n):])
            return (octave + 1) * 12 + i
    raise ValueError(f"Invalid note name: {name}")


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


def get_chord_for_degree(scale_notes: list[int], degree: int,
                         chord_type: str, octave_root: int) -> list[int]:
    """Get chord notes for a scale degree."""
    if degree < len(scale_notes):
        root = octave_root + (scale_notes[degree] - scale_notes[0])
    else:
        root = octave_root
    return build_chord(root, chord_type)


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


def passing_chord(chord_root: int, next_root: int, chord_type: str) -> tuple[int, str]:
    """Generate a passing/transitional chord between two chord roots."""
    # Chromatic approach: half step below the target
    if abs(next_root - chord_root) > 2:
        passing_root = next_root - 1 if next_root > chord_root else next_root + 1
        return (passing_root, "dim")  # Diminished passing chord
    # Otherwise use a sus4 on the current root
    return (chord_root, "sus4")


def random_drum_pattern() -> dict[str, list[int]]:
    """Pick a random drum pattern."""
    return random.choice(DRUM_PATTERNS)


def random_tempo() -> int:
    """Pick a random tempo appropriate for game music (100-160 BPM)."""
    return random.randint(100, 160)
