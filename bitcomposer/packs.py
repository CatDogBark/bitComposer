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
            "echo_stereo": {"bounce": 1, "centre": 2},
            "counter_line": 0.6,      # chance per chorus/bridge pattern (plain: 0.3)
            "section_rolls": True,    # timpani roll into the next section
        },
        # Channel trims by role, on top of the mix: the orchestra keeps the
        # kit's hats well back.
        "trims": {"hihat": 18, "openhat": 18},
    },
    "mana": {
        "palette": "snes",
        "label": "Secret of Mana",
        "voices": {
            "lead": ["mana_whistle", "mana_panflute", "mana_celesta", "mana_steel_drum",
                     "snes_flute", "mana_kalimba", "snes_bell"],
            "alt_lead": ["mana_panflute", "mana_whistle", "mana_celesta", "snes_flute",
                         "mana_steel_drum", "snes_epiano"],
            "harmony": ["mana_glass_pad", "mana_glass_pad", "snes_strings", "snes_choir",
                        "snes_epiano", "snes_organ"],
            "counter": ["mana_celesta", "mana_kalimba", "snes_flute", "mana_steel_drum"],
            "arp": ["mana_kalimba", "mana_celesta", "mana_chimes", "snes_marimba",
                    "mana_steel_drum", "snes_bell"],
            "bass_heavy": ["snes_slap_bass", "snes_pluck_bass", "snes_synth_bass"],
            "bass_medium": ["snes_slap_bass", "snes_slap_bass", "snes_pluck_bass"],
            "bass_light": ["snes_slap_bass", "snes_pizz", "snes_marimba"],
            "drums": {"kick": "snes_kick", "snare": "snes_snare", "hihat": "mana_shaker",
                      "tom": "mana_conga", "crash": "snes_crash",
                      "open_hihat": "mana_tambourine", "rim": "mana_woodblock"},
        },
        "habits": {
            "tempo": {"slow": 1, "medium": 3, "fast": 2},
            "energy": {"chill": 1, "normal": 3, "intense": 1},
            "scale_family": {"minor": 1, "major": 3, "pentatonic": 2},
            "harmony_voicing": {"full": 1, "thin": 2},
            "harmony_mode": {"pulse": 2, "rhythmic": 2, "stabs": 2, "sustain": 1, "ostinato": 0},
            "bass_weight": {"heavy": 1, "medium": 2, "light": 2},
            "bass_style": {"steady": 1, "walking": 2, "octave": 3, "driving": 1},
            "drum_density": {"sparse": 1, "normal": 3, "busy": 2},
            "drum_swing": {"off": 1, "light": 3, "heavy": 1},
            "arp_figures": {"classic_up": 3, "up_down": 3, "cascade": 2, "sync_push": 2,
                            "run16": 1, "quarter_up": 1, "broken_octave": 1},
            "echo": 0.8,
            "echo_wet": {"light": 1, "normal": 3, "wet": 1},
            "echo_stereo": {"bounce": 2, "centre": 1},
            "counter_line": 0.35,
            "section_rolls": False,
            "hat_stroke": 0.6,        # shaker: every second hit is the back stroke
        },
        # A lighter kit: the hand percussion carries the time, the kick and
        # snare sit back.
        "trims": {"kick": 28, "snare": 30, "hihat": 20, "openhat": 22},
    },
    "evermore": {
        "palette": "snes",
        "label": "Secret of Evermore",
        "voices": {
            "lead": ["evm_breath_flute", "evm_breath_flute", "snes_flute", "evm_choir_oo",
                     "evm_tubular_bell", "ffvi_oboe", "snes_epiano"],
            "alt_lead": ["evm_choir_oo", "snes_flute", "evm_breath_flute", "ffvi_clarinet",
                         "snes_epiano"],
            "harmony": ["evm_pad", "evm_pad", "evm_dark_pad", "evm_dark_pad", "evm_choir_oo",
                        "snes_strings"],
            "counter": ["evm_choir_oo", "snes_flute", "evm_breath_flute"],
            "arp": ["snes_harp", "mana_kalimba", "evm_tubular_bell", "ffvi_music_box",
                    "snes_epiano", "mana_glass_pad"],
            "bass_heavy": ["evm_drone", "evm_drone", "snes_pluck_bass"],
            "bass_medium": ["evm_drone", "snes_pluck_bass", "ffvi_contrabass"],
            "bass_light": ["evm_drone", "snes_pluck_bass"],
            "drums": {"kick": "ffvi_bassdrum", "snare": "evm_brush_snare", "hihat": "mana_shaker",
                      "tom": "evm_frame_drum", "crash": "evm_soft_cymbal",
                      "open_hihat": "mana_tambourine", "rim": "evm_click"},
        },
        "habits": {
            "tempo": {"slow": 4, "medium": 1, "fast": 0},
            "energy": {"chill": 3, "normal": 1, "intense": 0},
            "scale_family": {"minor": 4, "major": 1, "pentatonic": 1},
            "form": {"linear": 3, "standard": 1, "aaba": 1, "short": 1, "rondo": 0},
            "harmony_voicing": {"full": 2, "thin": 1},
            "harmony_mode": {"sustain": 5, "rhythmic": 1, "stabs": 0, "ostinato": 0, "pulse": 0},
            "bass_weight": {"heavy": 1, "medium": 2, "light": 2},
            "bass_style": {"drone": 3, "steady": 2, "walking": 1, "octave": 0, "driving": 0},
            "drum_density": {"sparse": 4, "normal": 1, "busy": 0},
            "drum_swing": {"off": 4, "light": 1, "heavy": 0},
            "drumless": 0.4,          # chance the whole song has no kit at all
            "arp_figures": {"sparse_pulse": 3, "quarter_up": 3, "pedal_bounce": 1, "classic_up": 1},
            "echo": 1.0,
            "echo_wet": {"light": 0, "normal": 1, "wet": 3},
            "echo_delay": {"eighth": 0, "dotted": 2, "quarter": 3},
            "echo_stereo": {"bounce": 1, "centre": 2},
            "counter_line": 0.2,
            "section_rolls": False,
            "hat_stroke": 0.6,
            "crash_chance": 0.35,     # a third of the phrase starts, never on fills
            "fill_crash": False,
        },
        "trims": {"kick": 26, "snare": 24, "hihat": 18, "openhat": 18, "tom": 30, "crash": 24},
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
