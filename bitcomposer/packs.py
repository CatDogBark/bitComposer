"""
Style packs: an instrument set paired with the arrangement habits of the
game scores it imitates. A pack sits inside a palette (the sound chip) and
narrows what the composer draws: which voice plays each role, how the
harmony moves, how the bass behaves, which drum kit, how wet the echo is.
Everything here is data; the composer reads it through pack_weights().
"""

PACKS = {
    "ffvi": {
        "palette": "snes",
        "label": "FFVI orchestral",
        "voices": {
            "lead": ["ffvi_oboe", "ffvi_trumpet", "ffvi_horn", "snes_flute",
                     "ffvi_piano", "ffvi_strings", "ffvi_clarinet"],
            "alt_lead": ["ffvi_horn", "ffvi_oboe", "snes_flute", "ffvi_clarinet",
                         "snes_choir", "ffvi_trumpet"],
            "harmony": ["ffvi_strings", "ffvi_strings", "ffvi_strings", "snes_choir",
                        "ffvi_horn", "ffvi_organ"],
            "counter": ["ffvi_horn", "ffvi_horn", "ffvi_trumpet", "ffvi_clarinet", "snes_choir"],
            "arp": ["snes_harp", "snes_harp", "snes_pizz", "ffvi_music_box", "ffvi_piano"],
            "bass_heavy": ["ffvi_contrabass", "ffvi_contrabass", "snes_pluck_bass"],
            "bass_medium": ["ffvi_contrabass", "snes_pluck_bass", "snes_pizz"],
            "bass_light": ["snes_pizz", "ffvi_contrabass"],
            "drums": {"kick": "ffvi_bassdrum", "snare": "ffvi_snare", "hihat": "snes_hat",
                      "tom": "ffvi_timpani", "crash": "ffvi_cymbal",
                      "open_hihat": "snes_open_hat", "rim": "snes_rim"},
        },
        # Weighted draws for the composer's habits. A habit missing here is
        # drawn the way plain snes draws it.
        "habits": {
            "tempo": {"slow": 2, "medium": 3, "fast": 1},
            "energy": {"chill": 1, "normal": 2, "intense": 1},
            "scale_family": {"minor": 3, "major": 2, "pentatonic": 0},
            "harmony_voicing": {"full": 3, "thin": 1},
            "harmony_mode": {"ostinato": 3, "sustain": 3, "pulse": 1, "stabs": 1, "rhythmic": 0},
            "bass_weight": {"heavy": 2, "medium": 2, "light": 1},
            "bass_style": {"steady": 3, "walking": 2, "octave": 2, "driving": 1},
            "drum_density": {"sparse": 2, "normal": 2, "busy": 1},
            "drum_swing": {"off": 5, "light": 1, "heavy": 0},
            "echo": 0.85,
            "echo_wet": {"light": 1, "normal": 3, "wet": 2},
            "echo_stereo": {"bounce": 1, "spread": 2},
            "counter_line": 0.6,      # chance per chorus/bridge pattern (plain: 0.3)
            "section_rolls": True,    # timpani roll into the next section
        },
        # Channel trims by role, on top of the mix: the orchestra keeps the
        # kit's hats well back.
        "trims": {"hihat": 18, "openhat": 18},
    },
}

PACK_NAMES = list(PACKS)


def pack_weights(pack: str | None, habit: str):
    """The pack's weights for a habit, or None to draw the plain way."""
    if not pack:
        return None
    return PACKS[pack]["habits"].get(habit)


def pack_value(pack: str | None, habit: str, default):
    if not pack:
        return default
    return PACKS[pack]["habits"].get(habit, default)
