"""
Drums.

The old drums were one 16-step bar tiled four times per pattern, three
pieces (kick, snare, hat), every kick and snare at full volume, one fill per
song. Measured over twenty songs: five distinct bar shapes a song, 82% of
bars identical to the one before, the open hat never played. A drum machine
with its variation switched off.

A groove here is a one-bar *main* with an *alt* bar and a *lift* bar, played
as a four-bar phrase (main, main, alt, main+lift). Steps carry velocity:
'.' rest, 'g' ghost, 'x' normal, 'X' accent. Ghost snares play on a rim
sample when the palette has one. Hats take their accent from position (beat,
eighth, sixteenth). Fills come from a library by length and weight, chosen by
what the next section is. Bridges may drop the kick and snare for a bar.
Hats thin to eighths above FAST_BPM.
"""

import random

from .it_format import ITNote, midi_to_it_note, FX_RETRIGGER, FX_SPECIAL, S_NOTE_DELAY
from .pattern import (CH_KICK, CH_SNARE, CH_HIHAT, CH_TOM, CH_CRASH, CH_OPEN_HAT,
                      ROWS_PER_BAR, ROWS_PER_BEAT)

FAST_BPM = 140

# Velocity per step character, per piece.
VEL = {
    "kick":  {"g": 30, "x": 54, "X": 64},
    "snare": {"g": 22, "x": 50, "X": 64},
    "tom":   {"g": 30, "x": 52, "X": 62},
    "ohat":  {"g": 24, "x": 38, "X": 46},
    "crash": {"g": 30, "x": 48, "X": 58},
}
# Hats: by position in the beat, unless the step is an accent.
HAT_VEL = {0: 52, 2: 40, 1: 28, 3: 28}

CHANNEL = {"kick": CH_KICK, "snare": CH_SNARE, "hat": CH_HIHAT, "tom": CH_TOM,
           "crash": CH_CRASH, "ohat": CH_OPEN_HAT}

# One-bar maps are 16 characters, one per sixteenth. `alt` and `lift` give
# only the pieces that change. hat16 says the groove's hats are sixteenths
# (so they thin at speed, and swing lands on the odd rows).
GROOVES = {
    "rock8": {
        "energy": (0.35, 0.85), "hat16": False,
        "main": {"kick": "X...x...X...x...", "snare": "....X.......X...", "hat": "x.x.x.x.x.x.x.x."},
        "alt":  {"kick": "X...x..x..X.x...", "snare": "....X.......X..g"},
        "lift": {"ohat": "..............x.", "snare": "....X......gX...", "hat": "x.x.x.x.x.x.x..."},
    },
    "rock16": {
        "energy": (0.5, 1.0), "hat16": True,
        "main": {"kick": "X...x...X...x...", "snare": "....X.......X...", "hat": "xxxxxxxxxxxxxxxx"},
        "alt":  {"kick": "X...x.x.X...x...", "snare": "....X....g..X..g"},
        "lift": {"ohat": "..............x.", "snare": "....X.......X.gx", "hat": "xxxxxxxxxxxxxx.."},
    },
    "driving": {
        "energy": (0.6, 1.0), "hat16": True,
        "main": {"kick": "X..x..X.X..x..X.", "snare": "....X.......X...", "hat": "xxxxxxxxxxxxxxxx"},
        "alt":  {"kick": "X..x..X.X.x...X.", "snare": "....X....g..X..g"},
        "lift": {"ohat": "......x.......x.", "snare": "....X.......X.xx"},
    },
    "funk": {
        "energy": (0.5, 1.0), "hat16": True,
        "main": {"kick": "X.....x.x..x....", "snare": "....X..g..g.X..g", "hat": "xxxxxxxxxxxxxxxx"},
        "alt":  {"kick": "X.....x...x..x..", "snare": "....X..g.g..X.g."},
        "lift": {"ohat": "......x.........", "snare": "....X..g..g.Xgxg", "tom": "..............x."},
    },
    "breakbeat": {
        "energy": (0.55, 1.0), "hat16": False,
        "main": {"kick": "X.....x...X.....", "snare": "....X.......X...", "hat": "x.x.x.x.x.x.x.x."},
        "alt":  {"kick": "X.....x..x......", "snare": "....X......gX.g."},
        "lift": {"ohat": "..............x.", "snare": "....X.......Xg.x", "kick": "X.....x...X...x."},
    },
    "halftime": {
        "energy": (0.3, 0.75), "hat16": False,
        "main": {"kick": "X.......x.......", "snare": "........X.......", "hat": "x.x.x.x.x.x.x.x."},
        "alt":  {"kick": "X.......x..x....", "snare": "........X......g"},
        "lift": {"ohat": "..............x.", "snare": "........X....g.x"},
    },
    "halftime16": {
        "energy": (0.45, 0.95), "hat16": True,
        "main": {"kick": "X.......x.x.....", "snare": "........X.......", "hat": "xxxxxxxxxxxxxxxx"},
        "alt":  {"kick": "X....x..x.......", "snare": "........X.....g."},
        "lift": {"ohat": "..............x.", "snare": "........X...g.gx", "hat": "xxxxxxxxxxxx...."},
    },
    "fourfloor": {
        "energy": (0.6, 1.0), "hat16": False,
        "main": {"kick": "X...X...X...X...", "snare": "....X.......X...", "hat": "..x...x...x...x.", "ohat": "..x...x...x...x."},
        "alt":  {"snare": "....X.......X..g", "ohat": "..x...x...x...xx"},
        "lift": {"snare": "....X.......Xxxx", "crash": "................"},
    },
    "toms": {
        "energy": (0.45, 0.95), "hat16": False,
        "main": {"kick": "X.......X.......", "snare": "....X.......X...", "hat": "x...x...x...x...", "tom": "..x.x.....x.x..."},
        "alt":  {"tom": "..x...x...x...x.", "kick": "X.......X....x.."},
        "lift": {"tom": "..x.x...x.x.xxxx", "ohat": "............x..."},
    },
    "sparse": {
        "energy": (0.0, 0.5), "hat16": False,
        "main": {"kick": "X...............", "snare": "........X.......", "hat": "x...x...x...x..."},
        "alt":  {"kick": "X.........x.....", "snare": "........X......."},
        "lift": {"snare": "........X.....g.", "ohat": "..............x."},
    },
    "sparse2": {
        "energy": (0.0, 0.55), "hat16": False,
        "main": {"kick": "X.......X.......", "snare": "........X.......", "hat": "x.x...x.x.x...x."},
        "alt":  {"kick": "X......xX......."},
        "lift": {"ohat": "..............x.", "snare": "........X...g..."},
    },
}

# Fills: `beats` of the bar they replace (counted from the end), a weight,
# and 16-step maps. Steps outside the last `beats` beats are ignored.
FILLS = [
    {"name": "snare pickup", "beats": 1, "weight": "light", "snare": "............x.xX"},
    {"name": "kick-snare", "beats": 1, "weight": "light", "kick": "............x...", "snare": "..............xX"},
    {"name": "ghost run", "beats": 2, "weight": "light", "snare": "........g.g.gxgX", "hat": "........x.x.x.x."},
    {"name": "tom step", "beats": 2, "weight": "light", "tom": "........x.x.....", "snare": "............x.xX"},
    {"name": "snare roll", "beats": 2, "weight": "big", "snare": "........x.x.xxxX", "roll": True},
    {"name": "tom cascade", "beats": 4, "weight": "big", "tom": "x.x.x.x.x.x.....", "snare": "............xxxX", "kick": "X..............."},
    {"name": "build to crash", "beats": 4, "weight": "big", "kick": "X...X...X.X.X.X.", "snare": "..x...x...x.xxXX", "crash": "...............X"},
    {"name": "flam march", "beats": 4, "weight": "big", "snare": "x.xxx.xxx.xxxxxX", "kick": "X.......X......."},
    # Orchestral: a timpani roll swelling into the next section, cymbal on the
    # downbeat after. Packs that ask for it (packs.py "section_rolls") get it
    # for most big fills; the tom slot is the timpani in those kits.
    {"name": "timpani roll", "beats": 2, "weight": "big", "tom": "........xxxxxxxX", "roll": True, "orchestral": True},
    {"name": "timpani cascade", "beats": 4, "weight": "big", "tom": "x...x...x.x.xxxX", "snare": "............xxxX", "roll": True, "orchestral": True},
]


def pick_grooves(energy_pref: str, density: str) -> dict[str, str]:
    """One groove per section role for the song.

    density is the CLI's sparse/normal/busy. Verse and chorus differ, the
    chorus taking the more energetic of the two, so the chorus lifts.
    """
    names = list(GROOVES)
    if density == "sparse":
        pool = ["sparse", "sparse2", "halftime", "rock8"]
    elif density == "busy":
        pool = ["rock16", "driving", "funk", "breakbeat", "fourfloor", "halftime16", "toms"]
    else:
        pool = ["rock8", "rock16", "breakbeat", "funk", "halftime", "halftime16", "toms", "driving"]
    if energy_pref == "chill":
        pool = [g for g in pool if GROOVES[g]["energy"][0] <= 0.5] or pool
    elif energy_pref == "intense":
        pool = [g for g in pool if GROOVES[g]["energy"][1] >= 0.95] or pool
    # The chorus groove must reach the top of the energy curve, but not from
    # a pool of one: a chill song used to get rock8 for every chorus.
    chorus_pool = [g for g in pool if GROOVES[g]["energy"][1] >= 0.85]
    if len(chorus_pool) < 2:
        chorus_pool = [g for g in pool if GROOVES[g]["energy"][1] >= 0.75] or pool
    chorus = random.choice(chorus_pool)
    verse_pool = [g for g in pool if g != chorus and GROOVES[g]["energy"][0] <= GROOVES[chorus]["energy"][0] + 0.1] or [g for g in pool if g != chorus] or pool
    verse = random.choice(verse_pool)
    bridge = random.choice([g for g in names if g not in (verse, chorus) and GROOVES[g]["energy"][0] <= 0.6] or [verse])
    return {"verse": verse, "chorus": chorus, "bridge": bridge, "intro": "sparse", "outro": "sparse2"}


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    out.update(over)
    return out


def _bar_maps(groove: dict, bar: int) -> dict:
    """Maps for bar 0..3 of the phrase: main, main, alt, main+lift."""
    m = groove["main"]
    if bar == 2:
        return _merge(m, groove.get("alt", {}))
    if bar == 3:
        return _merge(m, groove.get("lift", {}))
    return dict(m)


def _thin_hats(hat: str) -> str:
    """Sixteenth hats to eighths."""
    return "".join(c if i % 2 == 0 else "." for i, c in enumerate(hat))


def render_drums(pat, groove_name: str, *, sample_map: dict, energy: float, bpm: float,
                 swing: int, speed: int, fill: dict | None, breakdown: bool,
                 crash_on_one: bool, bars: int = 4) -> dict:
    """Write a four-bar drum phrase into `pat`. Returns counts per piece."""
    groove = GROOVES[groove_name]
    rows_per_bar = ROWS_PER_BAR
    counts: dict[str, int] = {}
    swung_rows = (lambda r: r % 2 == 1) if groove["hat16"] else (lambda r: r % ROWS_PER_BEAT == 2)
    delay = max(1, min(speed - 1, round(speed * swing / 3))) if swing else 0

    def put(piece: str, row: int, vel: int, extra_fx=(0, 0), instrument_key: str | None = None):
        ch = CHANNEL[piece]
        inst = sample_map.get(instrument_key or ("hihat" if piece == "hat" else
                              "open_hihat" if piece == "ohat" else piece))
        if inst is None or not (0 <= row < pat.rows):
            return
        fx, fxv = extra_fx
        if piece == "hat" and swing and swung_rows(row % rows_per_bar):
            fx, fxv = FX_SPECIAL, S_NOTE_DELAY | delay
        pat.data[row][ch] = ITNote(note=midi_to_it_note(60), instrument=inst,
                                   volume=max(1, min(64, vel)), effect=fx, effect_val=fxv)
        counts[piece] = counts.get(piece, 0) + 1

    for bar in range(bars):
        maps = _bar_maps(groove, bar % 4)
        base = bar * rows_per_bar
        hat = maps.get("hat", "." * 16)
        if groove["hat16"] and bpm > FAST_BPM:
            hat = _thin_hats(hat)
        maps = _merge(maps, {"hat": hat})
        drop = breakdown and bar < 2        # bridge drop: hats only for two bars
        fill_here = fill if (bar == bars - 1 and fill) else None
        fill_from = 16 - 4 * fill["beats"] if fill_here else 16

        for piece in ("kick", "snare", "tom", "ohat", "crash", "hat"):
            steps = maps.get(piece, "." * 16)
            for i, c in enumerate(steps):
                if c == "." or i >= fill_from:
                    continue
                if drop and piece not in ("hat", "ohat"):
                    continue
                row = base + i
                if piece == "hat":
                    vel = 60 if c == "X" else HAT_VEL[i % 4]
                    put(piece, row, vel + random.randint(-3, 3))
                elif piece == "snare" and c == "g" and sample_map.get("rim"):
                    put("snare", row, VEL["snare"]["g"] + 8, instrument_key="rim")
                else:
                    put(piece, row, VEL[piece][c] + (random.randint(-2, 2) if c != "X" else 0))

        if fill_here:
            for piece in ("kick", "snare", "tom", "crash", "hat"):
                steps = fill_here.get(piece)
                if not steps:
                    continue
                for i, c in enumerate(steps):
                    if c == "." or i < fill_from:
                        continue
                    row = base + i
                    fx = (FX_RETRIGGER, 3) if (fill_here.get("roll") and piece in ("snare", "tom") and c == "x") else (0, 0)
                    if piece == "hat":
                        put(piece, row, HAT_VEL[i % 4])
                    else:
                        put(piece, row, VEL[piece][c], extra_fx=fx)

    if crash_on_one and not breakdown:
        put("crash", 0, int(VEL["crash"]["X"] * max(0.6, energy)))
    return counts


def pick_fill(next_section: str | None, position: str, enabled: bool,
              orchestral: bool = False) -> dict | None:
    """Fill for the end of a pattern.

    position: "section_end" (into next_section), "mid" (halfway through a
    section) or "none". Into a chorus or theme: a big fill. Into a verse or
    bridge: a light one. Mid-section: a light one-beat fill, half the time.
    """
    if not enabled or position == "none":
        return None
    if position == "mid":
        return random.choice([f for f in FILLS if f["beats"] == 1]) if random.random() < 0.5 else None
    if next_section in ("chorus",):
        big = [f for f in FILLS if f["weight"] == "big"]
        if orchestral and random.random() < 0.7:
            big = [f for f in big if f.get("orchestral")] or big
        else:
            big = [f for f in big if not f.get("orchestral")] or big
        return random.choice(big)
    return random.choice([f for f in FILLS if f["weight"] == "light"])
