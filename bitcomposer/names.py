"""
Song titles.

Every generated module used to be titled "BitComposer - <key> <scale>", so a
playlist of twenty tracks was twenty near-identical lines and the only handle
on a song was a timestamp in its filename. A title is drawn here from the
song's own seeded random state, so it is as reproducible as the music.

The first version was one pattern, "<adjective> <place>", with the adjective
list leaning on the scale: 720 titles per mood, so a folder of a few hundred
songs repeated names. Now the title reads the song: the scale sets the mood
of the adjectives, the energy and tempo add their own words (a chill song can
be a Lullaby, an intense one a Siege), and the sound sets the places (a Mega
Man X song is set in a Reactor or a Fortress, an FFVI song in an Opera House
or a Kingdom, a Mana song in a Grove or a Spring). Eight patterns over lists of
thirty to sixty words give some tens of thousands of titles per sound and
mood, so repeats are rare in any folder a person would keep.
"""

import random

# ── Adjectives by mood ──
DARK = [
    "Ashen", "Hollow", "Crimson", "Obsidian", "Sunken", "Forsaken", "Iron",
    "Shadow", "Frozen", "Thorned", "Rusted", "Buried", "Silent", "Haunted",
    "Fallen", "Molten", "Veiled", "Bleak", "Grim", "Ember", "Broken", "Cold",
    "Dread", "Scorched", "Shattered", "Sullen", "Withered", "Nameless",
    "Blackened", "Lost",
]
BRIGHT = [
    "Neon", "Golden", "Emerald", "Azure", "Sunlit", "Crystal", "Silver",
    "Verdant", "Amber", "Coral", "Radiant", "Gilded", "Breezy", "Vivid",
    "Lucent", "Opal", "Saffron", "Skyward", "Bright", "Jade", "Blooming",
    "Clear", "Dawning", "Gleaming", "Ivory", "Pearl", "Shining", "Summer",
    "Warm", "Open",
]
NEUTRAL = [
    "Distant", "Drifting", "Wandering", "Quiet", "Rising", "Starlit",
    "Midnight", "Lunar", "Restless", "Hidden", "Northern", "Endless",
    "Second", "Outer", "Lower", "Upper", "Last", "First", "Twin", "Far",
    "Ancient", "Eastern", "Western", "Inner", "Old", "Secret", "Sleeping",
    "Still", "Waking", "Winding",
]
MOOD = {
    "natural_minor": DARK + NEUTRAL, "harmonic_minor": DARK + NEUTRAL, "phrygian": DARK + NEUTRAL,
    "minor_pentatonic": DARK + NEUTRAL,
    "dorian": NEUTRAL + DARK[:10] + BRIGHT[:10], "mixolydian": BRIGHT + NEUTRAL,
    "major": BRIGHT + NEUTRAL, "major_pentatonic": BRIGHT + NEUTRAL,
}

# ── Energy and tempo words ──
# Adjectives joined to the mood list, and nouns for the "<place> <noun>" and
# "<noun> of the <place>" patterns, so a fast intense song can be a Pursuit
# and a slow chill one a Lullaby.
ENERGY_ADJ = {
    "intense": ["Racing", "Blazing", "Relentless", "Charging", "Burning", "Furious",
                "Raging", "Striking"],
    "chill": ["Drowsy", "Gentle", "Hushed", "Mellow", "Slow", "Soft", "Tender", "Calm"],
}
ENERGY_NOUN = {
    "intense": ["Pursuit", "Siege", "Assault", "Onslaught", "Chase", "Charge", "Clash",
                "Rush", "Storm", "Strike"],
    "chill": ["Lullaby", "Reverie", "Vigil", "Rest", "Dream", "Drift", "Hymn", "Prayer",
              "Sleep", "Lament"],
    "normal": ["Theme", "March", "Dance", "Passage", "Crossing", "Journey", "Road",
               "Return", "Rite", "Song"],
}
TEMPO_NOUN = {
    "fast": ["Run", "Flight", "Sprint", "Escape"],
    "slow": ["Dusk", "Dawn", "Vigil", "Tide"],
}

# ── Places by sound ──
# The generic list plus a flavour per sound: a pack's songs are set where its
# game was set.
PLACES = [
    "Causeway", "Citadel", "Reactor", "Harbor", "Catacombs", "Skyway",
    "Foundry", "Grotto", "Bazaar", "Observatory", "Lagoon", "Ramparts",
    "Monorail", "Arcade", "Expanse", "Terminal", "Spire", "Orchard",
    "Cistern", "Meridian", "Aqueduct", "Outpost", "Caldera", "Archive",
    "Pavilion", "Tundra", "Bastion", "Canopy", "Depot", "Sanctum",
    "Gauntlet", "Overpass", "Frontier", "Cloister", "Dunes", "Vault",
    "Bridge", "Canyon", "Coast", "Crossing", "Gate", "Gorge", "Glacier",
    "Island", "Lighthouse", "Market", "Pass", "Plateau", "Quarry", "Ridge",
    "River", "Shore", "Steppe", "Tower", "Valley", "Wharf",
]
SOUND_PLACES = {
    "bit": ["Terminal", "Signal", "Lattice", "Relay", "Circuit", "Harbor", "Observatory", "Orchard",
            "Beacon", "Cinder", "Hollow", "Meadow", "Summit", "Tidepool", "Foundry", "Lantern", "Causeway", "Grove"],
    "megamanx": ["Fortress", "Highway", "Factory", "Power Plant", "Airport", "Mine",
                 "Tower", "Hangar", "Launch Pad", "Sky Dock", "Armory", "Reactor Core",
                 "Gallery", "Scrapyard", "Snowfield", "Stage", "Sector", "Skyline"],
    "ffvi": ["Opera House", "Cathedral", "Kingdom", "Castle", "Airship", "Coliseum",
             "Ruins", "Chapel", "Throne", "Phantom Wood", "Veldt", "Mines", "Tower",
             "Imperial Camp", "Gardens", "Cave", "Falls", "Mountain"],
    "mana": ["Grove", "Glade", "Spring", "Falls", "Shrine", "Village", "Meadow",
             "Isle", "Forest", "Fountain", "Marsh", "Pure Land", "Sea", "Cave",
             "Lighthouse", "Palace", "Temple", "Woods"],
    "evermore": ["Pyramid", "Jungle", "Marsh", "Swamp", "Tar Pits", "Arena",
                 "Greenhouse", "Volcano", "Dungeon", "Graveyard", "Castle", "Hall",
                 "Plateau", "Seashore", "Waterfall", "Fountain", "Tower", "Omnitopia"],
    "genesis": ["Circuit", "Grid", "Arena", "Speedway", "Zone", "Sector", "Uplink",
                "Mainframe", "Station", "Skyline", "Dockyard", "Chrome City"],
    "chip": ["Castle", "Cave", "Sky", "Zone", "Stage", "World", "Fortress", "Tower",
             "Field", "Forest", "Dungeon", "Pipe Maze"],
    "snes": ["Castle", "Cave", "Village", "Tower", "Forest", "Temple", "Shrine", "Ruins"],
}

# ── Abstract nouns for "<place> of <noun>" and "<adjective> <noun>" ──
NOUNS = [
    "Glass", "Steel", "Ash", "Dust", "Thunder", "Rain", "Dawn", "Dusk", "Embers",
    "Echoes", "Wires", "Sparks", "Bells", "Stone", "Ice", "Fire", "Smoke", "Light",
    "Shadows", "Static", "Salt", "Snow", "Sand", "Stars", "Tides", "Wind", "Mist",
    "Thorns", "Brass", "Copper", "Silk", "Lanterns", "Mirrors", "Rust", "Petals",
]

MAX_TITLE = 25  # the IT song-name field holds 25 characters plus a terminator


def _pool(scale_name: str, energy: str | None) -> list[str]:
    adjectives = list(MOOD.get(scale_name, NEUTRAL))
    adjectives += ENERGY_ADJ.get(energy or "", [])
    return adjectives


def song_title(scale_name: str, rng: random.Random | None = None,
               sound: str | None = None, energy: str | None = None,
               tempo: str | None = None) -> str:
    """A title that reads the song, drawn from `rng` (default: the module-level
    generator, which compose_song has already seeded).

    scale_name sets the mood of the adjectives; energy ("chill", "normal",
    "intense") and tempo ("slow", "medium", "fast") add their words; sound (a
    palette or pack name) sets where the song is set. Eight patterns, weighted
    toward the plain "<adjective> <place>" so a playlist still reads evenly.
    """
    r = rng or random
    adjectives = _pool(scale_name, energy)
    places = PLACES + SOUND_PLACES.get(sound or "", []) * 2     # the flavour weighs double
    nouns = NOUNS
    e_noun = ENERGY_NOUN.get(energy or "normal", ENERGY_NOUN["normal"]) + TEMPO_NOUN.get(tempo or "", [])
    patterns = [
        (5, lambda: f"{r.choice(adjectives)} {r.choice(places)}"),
        (3, lambda: f"The {r.choice(adjectives)} {r.choice(places)}"),
        (3, lambda: f"{r.choice(places)} of {r.choice(nouns)}"),
        (2, lambda: f"{r.choice(adjectives)} {r.choice(nouns)}"),
        (1, lambda: f"{r.choice(places)} {r.choice(e_noun)}"),
        (1, lambda: f"{r.choice(e_noun)} of the {r.choice(places)}"),
        # Three words where they fit: "Ashen Harbor Lullaby", "Neon Grid Pursuit".
        (3, lambda: f"{r.choice(adjectives)} {r.choice(places)} {r.choice(e_noun)}"),
        (2, lambda: f"The {r.choice(places)} of {r.choice(nouns)}"),
    ]
    weights = [w for w, _ in patterns]
    title = ""
    for _ in range(20):
        make = r.choices(patterns, weights)[0][1]
        title = make()
        if len(title) <= MAX_TITLE:
            return title
    return title[:MAX_TITLE]
