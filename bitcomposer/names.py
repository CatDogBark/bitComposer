"""
Song titles.

Every generated module used to be titled "BitComposer - <key> <scale>", so a
playlist of twenty tracks was twenty near-identical lines and the only handle
on a song was a timestamp in its filename. A title is drawn here from the
song's own seeded random state, so it is as reproducible as the music, and the
word lists lean with the scale: minor and phrygian songs get the darker
adjectives, major and mixolydian the brighter ones.
"""

import random

DARK = [
    "Ashen", "Hollow", "Crimson", "Obsidian", "Sunken", "Forsaken", "Iron",
    "Shadow", "Frozen", "Thorned", "Rusted", "Buried", "Silent", "Haunted",
    "Fallen", "Molten", "Veiled", "Bleak", "Grim", "Ember",
]
BRIGHT = [
    "Neon", "Golden", "Emerald", "Azure", "Sunlit", "Crystal", "Silver",
    "Verdant", "Amber", "Coral", "Radiant", "Gilded", "Breezy", "Vivid",
    "Lucent", "Opal", "Saffron", "Skyward", "Bright", "Jade",
]
NEUTRAL = [
    "Distant", "Drifting", "Wandering", "Quiet", "Rising", "Starlit",
    "Midnight", "Lunar", "Restless", "Hidden", "Northern", "Endless",
    "Second", "Outer", "Lower", "Upper", "Last", "First", "Twin", "Far",
]
PLACES = [
    "Causeway", "Citadel", "Reactor", "Harbor", "Catacombs", "Skyway",
    "Foundry", "Grotto", "Bazaar", "Observatory", "Lagoon", "Ramparts",
    "Monorail", "Arcade", "Expanse", "Terminal", "Spire", "Orchard",
    "Cistern", "Meridian", "Aqueduct", "Outpost", "Caldera", "Archive",
    "Pavilion", "Tundra", "Bastion", "Canopy", "Depot", "Sanctum",
    "Gauntlet", "Overpass", "Frontier", "Cloister", "Dunes", "Vault",
]

MOOD = {
    "natural_minor": DARK, "harmonic_minor": DARK, "phrygian": DARK,
    "minor_pentatonic": DARK + NEUTRAL,
    "dorian": NEUTRAL, "mixolydian": BRIGHT + NEUTRAL,
    "major": BRIGHT, "major_pentatonic": BRIGHT,
}

MAX_TITLE = 25  # the IT song-name field holds 25 characters plus a terminator


def song_title(scale_name: str, rng: random.Random | None = None) -> str:
    """Two-word title fitting the scale's mood, drawn from `rng` (default: the
    module-level generator, which compose_song has already seeded)."""
    r = rng or random
    adjectives = MOOD.get(scale_name, NEUTRAL)
    for _ in range(20):
        title = f"{r.choice(adjectives)} {r.choice(PLACES)}"
        if len(title) <= MAX_TITLE:
            return title
    return title[:MAX_TITLE]
