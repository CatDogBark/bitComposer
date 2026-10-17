"""
Song structure definitions.

Defines song forms, section layer maps, energy curves, and ending styles.
Separating this from the composer makes it easy to add new song forms.
"""

import random


FORMS = ["standard", "aaba", "rondo", "short", "linear"]


def reuse_group(section_key: str) -> str:
    """Sections that should play the same music.

    Repeats of one formal section (verse1/verse2, chorus1/chorus2/chorus3,
    theme1/theme2) share a content group so the hook actually returns.
    Contrasting sections that merely share a prefix must NOT: rondo episodes
    are the B and C of A-B-A-C-A, and linear sections are through-composed by
    definition, so both keep their own identity.
    """
    for prefix in ("verse", "chorus", "theme"):
        if section_key.startswith(prefix):
            return prefix
    return section_key


def section_type(section_key: str) -> str:
    """Map detailed section keys (verse1, chorus2, etc.) to base types."""
    if section_key.startswith("verse"):
        return "verse"
    if section_key.startswith("chorus"):
        return "chorus"
    if section_key == "tag":
        return "outro"
    if section_key.startswith("theme"):
        return "chorus"  # themes act like choruses for motif/layer purposes
    if section_key.startswith("episode"):
        return "bridge"  # episodes act like bridges
    if section_key.startswith("section"):
        return "verse"  # linear sections act like verses
    return section_key


# ── Layer definitions ──
# Each section type maps to which instrument layers are active.

LAYERS = {
    "intro":       {"drums": False, "bass": True,  "melody": False, "arp": True,  "harmony": False},
    "verse":       {"drums": True,  "bass": True,  "melody": True,  "arp": False, "harmony": False},
    "verse_full":  {"drums": True,  "bass": True,  "melody": True,  "arp": True,  "harmony": True},
    "chorus":      {"drums": True,  "bass": True,  "melody": True,  "arp": True,  "harmony": True},
    "bridge":      {"drums": True,  "bass": True,  "melody": False, "arp": True,  "harmony": True},
    "bridge_mel":  {"drums": True,  "bass": True,  "melody": True,  "arp": False, "harmony": True},
    "outro":       {"drums": False, "bass": True,  "melody": True,  "arp": True,  "harmony": False},
    "tag":         {"drums": False, "bass": True,  "melody": True,  "arp": False, "harmony": True},
    # Rondo-specific
    "theme":       {"drums": True,  "bass": True,  "melody": True,  "arp": True,  "harmony": True},
    "episode":     {"drums": True,  "bass": True,  "melody": True,  "arp": False, "harmony": True},
    "episode_light": {"drums": True, "bass": True, "melody": True, "arp": False, "harmony": False},
}


# ── Intro templates ──
# The intro used to be the one section with nothing drawn in it: bass and a
# two-note pulse arp, fading up from silence, over the whole home progression,
# in every song of every pack. Now a song draws one of these. `enter` says the
# bar (0-3) each part comes in on in the first intro pattern; parts not listed
# stay out. A later intro pattern plays every listed part from its first bar.
# `fade_in` is the old swell from silence; a song that starts on a hit has none.
# `arp` is how the arp figure is chosen ("sparse" = the old pulse, "draw" = a
# light figure drawn per song); `bass` "song" keeps the song's bass style
# (a riff vamps alone), "calm" lets it drop to steady at intro energy;
# `groove` "song" plays the verse groove, "sparse" the intro one; `voicing`
# overrides the harmony voicing for the intro.
INTROS = {
    # The arp bed over the bass, swelling in. The old intro.
    "arp_bed":     {"enter": {"bass": 0, "arp": 0}, "fade_in": True,
                    "arp": "draw", "bass": "calm", "groove": "sparse"},
    # The bass riff vamps alone, the harmony lands on bar three, drums only
    # for the fill out. The Mega Man X opening.
    "riff_vamp":   {"enter": {"bass": 0, "harmony": 2, "drums": 3}, "fade_in": False,
                    "arp": "draw", "bass": "song", "groove": "song"},
    # The kit leads, the bass joins halfway, the band lands on the verse.
    "drum_pickup": {"enter": {"drums": 0, "bass": 2, "arp": 3}, "fade_in": False,
                    "arp": "draw", "bass": "song", "groove": "song"},
    # A sustained pad with the hook stated once over it, swelling in.
    "pad_hook":    {"enter": {"harmony": 0, "melody": 1, "bass": 3}, "fade_in": True,
                    "arp": "sparse", "bass": "calm", "groove": "sparse",
                    "voicing": "sustain"},
}
INTRO_WEIGHTS = {"arp_bed": 2, "riff_vamp": 2, "drum_pickup": 2, "pad_hook": 2}
# Intro length in patterns (four bars each) and its weights. The old intro ran
# the whole home progression: eight or sixteen bars before the song started.
INTRO_LENGTHS = {1: 2, 2: 3}


def pick_intro(weights: dict | None, drumless: bool, rng: random.Random) -> tuple[str, int]:
    """Draw the intro template and length. Drumless songs never lead with the kit."""
    w = dict(weights or INTRO_WEIGHTS)
    if drumless:
        w["drum_pickup"] = 0
    names = [n for n in INTROS if w.get(n, 0) > 0] or ["arp_bed"]
    name = rng.choices(names, [w.get(n, 1) for n in names])[0]
    length = rng.choices(list(INTRO_LENGTHS), list(INTRO_LENGTHS.values()))[0]
    return name, length


def intro_layers(name: str) -> dict:
    """The layer map an intro template needs on."""
    enter = INTROS[name]["enter"]
    return {part: part in enter for part in ("drums", "bass", "melody", "arp", "harmony")}


def _build_layers(structure: list[str]) -> dict[str, dict]:
    """Build per-section layer map from a structure list.

    Numbered sections resolve to their own base entry before falling back to
    the broader section type. Without that step episode1/episode2 resolved via
    section_type() to "bridge", which carries no melody, so every rondo lost
    its lead through both episodes — 12 of 20 patterns silent in one measured
    song. It also left LAYERS["episode"], ["episode_light"] and ["bridge_mel"]
    unreachable despite existing precisely to carry a melody there.
    """
    layers = {}
    verse_count = 0
    for section in structure:
        st = section_type(section)
        base = section.rstrip("0123456789")

        if st == "verse":
            verse_count += 1
            key = "verse_full" if verse_count > 1 else "verse"
        elif base == "bridge":
            # Dropping the lead for a whole bridge is a real arrangement
            # device, but not every time — that is a lot of dead air.
            key = random.choice(["bridge", "bridge_mel", "bridge_mel"])
        elif base in LAYERS:
            key = base
        elif section in LAYERS:
            key = section
        else:
            key = st if st in LAYERS else "verse"

        layers[section] = dict(LAYERS[key])
    return layers


def _build_energy(structure: list[str], curve_template: dict[str, float]) -> dict[str, float]:
    """Build per-section energy map, assigning values from the curve template."""
    energy = {}
    for section in structure:
        if section in curve_template:
            energy[section] = curve_template[section]
        else:
            st = section_type(section)
            if st in curve_template:
                energy[section] = curve_template[st]
            else:
                energy[section] = 0.7
    return energy


# ── Song forms ──

def _form_standard() -> tuple[list[str], dict[str, float]]:
    """Standard verse-chorus form: intro V C V C B C outro."""
    structure = ["intro", "verse1", "chorus1", "verse2", "chorus2",
                 "bridge", "chorus3", "outro"]
    curve = {
        "intro": 0.5, "verse1": 0.65, "chorus1": 0.85,
        "verse2": 0.75, "chorus2": 0.90,
        "bridge": 0.60, "chorus3": 1.0, "outro": 0.60,
    }
    if random.random() < 0.5:
        idx = structure.index("bridge")
        structure.insert(idx + 1, "bridge")
    return structure, curve


def _form_aaba() -> tuple[list[str], dict[str, float]]:
    """AABA form: verse verse bridge verse. No chorus, classic and compact."""
    structure = ["intro", "verse1", "verse2", "bridge", "verse3", "outro"]
    curve = {
        "intro": 0.45, "verse1": 0.65, "verse2": 0.80,
        "bridge": 0.70, "verse3": 0.90, "outro": 0.55,
    }
    # Sometimes repeat the whole form (AABA AABA) for a longer piece
    if random.random() < 0.35:
        structure = ["intro", "verse1", "verse2", "bridge", "verse3",
                     "verse4", "verse5", "bridge", "verse6", "outro"]
        curve.update({
            "verse4": 0.70, "verse5": 0.85,
            "verse6": 1.0,
        })
    return structure, curve


def _form_rondo() -> tuple[list[str], dict[str, float]]:
    """Rondo form: A B A C A. Theme keeps returning between contrasting episodes."""
    structure = ["intro", "theme1", "episode1", "theme2", "episode2", "theme3", "outro"]
    curve = {
        "intro": 0.45, "theme1": 0.75, "episode1": 0.60,
        "theme2": 0.85, "episode2": 0.70, "theme3": 1.0, "outro": 0.55,
    }
    return structure, curve


def _form_short() -> tuple[list[str], dict[str, float]]:
    """Short form: 2-3 sections, compact. Great for game level music."""
    variant = random.choice(["ab", "aab", "aba"])
    if variant == "ab":
        structure = ["verse1", "chorus1", "verse2", "chorus2"]
        curve = {"verse1": 0.65, "chorus1": 0.85, "verse2": 0.75, "chorus2": 1.0}
    elif variant == "aab":
        structure = ["verse1", "verse2", "bridge", "verse3"]
        curve = {"verse1": 0.65, "verse2": 0.80, "bridge": 0.70, "verse3": 0.95}
    else:  # aba
        structure = ["verse1", "chorus1", "verse2"]
        curve = {"verse1": 0.70, "chorus1": 0.90, "verse2": 0.75}
    return structure, curve


def _form_linear() -> tuple[list[str], dict[str, float]]:
    """Linear/through-composed: each section is different, no repeats."""
    num_sections = random.choice([4, 5, 6])
    structure = ["intro"]
    for i in range(1, num_sections + 1):
        structure.append(f"section{i}")
    structure.append("outro")

    # Energy builds gradually then winds down
    curve = {"intro": 0.45, "outro": 0.55}
    for i in range(1, num_sections + 1):
        # Peak around 2/3 through
        peak_pos = num_sections * 0.67
        dist = abs(i - peak_pos) / num_sections
        energy = 1.0 - dist * 0.5
        curve[f"section{i}"] = round(energy, 2)
    return structure, curve


_FORM_FUNCS = {
    "standard": _form_standard,
    "aaba": _form_aaba,
    "rondo": _form_rondo,
    "short": _form_short,
    "linear": _form_linear,
}


# ── Ending variations ──

def apply_ending(structure: list[str], layers: dict, energy: dict) -> str:
    """Apply an ending style to the structure. Returns the ending style name."""
    ending = random.choices(["fadeout", "tag", "abrupt"], weights=[45, 40, 15], k=1)[0]

    # Short form doesn't get tag endings — just fade or abrupt
    has_outro = "outro" in structure
    if not has_outro:
        ending = random.choice(["fadeout", "abrupt"])

    if ending == "tag" and has_outro:
        structure.append("tag")
        layers["tag"] = dict(LAYERS["tag"])
        energy["tag"] = 0.35
    elif ending == "abrupt":
        if has_outro:
            structure.remove("outro")
    return ending


# ── Public API ──

def get_section_progression(section: str, progression: list, alt_progression: list,
                            use_alt_chorus: bool) -> list:
    """Get the chord progression for a given section."""
    is_ending = section in ("outro", "tag")
    st = section_type(section)
    if section == "tag":
        return progression[:max(1, len(progression) // 2)]
    if section == "outro":
        return progression
    elif use_alt_chorus and st == "chorus":
        return alt_progression
    return progression


def pattern_plan(section_prog: list, compact: bool) -> list[list]:
    """Group a section's progression entries into patterns.

    Normal harmonic rhythm is one chord per four-bar pattern; compact is two
    chords per pattern (two bars each), so a four-chord progression is an
    eight-bar section instead of sixteen — the length a verse or chorus
    usually has, and at a fast tempo the difference between a loop and a
    slog. A lone trailing entry keeps a pattern of its own.
    """
    if not compact:
        return [[e] for e in section_prog]
    plan = [section_prog[i:i + 2] for i in range(0, len(section_prog), 2)]
    return plan or [[]]


# Song length, in seconds. Over sixty random seeds the median was two minutes
# with a tail each way: three in ten songs under 1:30 (the short form, a
# quarter of draws, at speed) and two in ten over 3:00 (a long form with its
# whole AABA repeated at 80 BPM, up to six minutes). The spread is right for
# a player that cycles sounds; the tails are not. Below the floor the last
# body section plays again; above the ceiling the latest repeat of a section
# group is dropped, the first of every group kept, intro and ending kept.
LENGTH_FLOOR_SEC = 75
LENGTH_CEILING_SEC = 210


def clamp_length(structure: list[str], pattern_index_for: dict,
                 pattern_counts: dict[str, int], pattern_seconds: float
                 ) -> tuple[list[int], list[str], str | None]:
    """The order list clamped to the length band. Returns (orders, the
    section list as played, a note on what moved or None)."""
    blocks = [(s, [pattern_index_for[(s, i)] for i in range(pattern_counts[s])]) for s in structure]
    ending = {"intro", "outro", "tag"}

    def total():
        return sum(len(b) for _, b in blocks) * pattern_seconds
    note = None
    # Under the floor: the whole body (everything between the intro and the
    # ending) plays again once, as a level loop would; then, if still short,
    # the last section up to twice more. Repeating only the last section was
    # the first version: a 43 s short form became one verse three times over.
    body = [i for i, (sec, _) in enumerate(blocks) if sec not in ending]
    if body and total() < LENGTH_FLOOR_SEC:
        blocks[body[-1] + 1:body[-1] + 1] = [blocks[i] for i in body]
        note = "played the body twice"
    repeats = 0
    while total() < LENGTH_FLOOR_SEC and repeats < 2:
        body = [i for i, (sec, _) in enumerate(blocks) if sec not in ending]
        if not body:
            break
        idx = body[-1]
        blocks.insert(idx + 1, blocks[idx])
        repeats += 1
        note = f"played the body twice, then the last {section_type(blocks[idx][0])} again"
    while total() > LENGTH_CEILING_SEC:
        groups: dict[str, list[int]] = {}
        for i, (sec, _) in enumerate(blocks):
            if sec not in ending:
                groups.setdefault(reuse_group(sec), []).append(i)
        candidates = [idxs[-1] for idxs in groups.values() if len(idxs) > 1]
        if candidates:
            drop = max(candidates)
            note = f"dropped a repeat of the {section_type(blocks[drop][0])}"
        else:
            # Through-composed (linear): nothing repeats, so the last body
            # section goes, as long as two remain.
            body = [i for i, (sec, _) in enumerate(blocks) if sec not in ending]
            if len(body) <= 2:
                break
            drop = body[-1]
            note = f"dropped the last {section_type(blocks[drop][0])}"
        del blocks[drop]
    return [p for _, b in blocks for p in b], [sec for sec, _ in blocks], note


def build_orders(structure: list[str], pattern_index_for: dict,
                 pattern_counts: dict[str, int]) -> list[int]:
    """Build the order list from the song structure.

    pattern_index_for maps (section, pattern_idx) to a pattern index and
    pattern_counts says how many patterns each section has. Sections that
    share content and rendering map to the same index, so the order list
    replays one pattern instead of carrying a near-duplicate.
    """
    orders = []
    for section in structure:
        for idx in range(pattern_counts[section]):
            orders.append(pattern_index_for[(section, idx)])
    return orders


def generate_structure(form: str = "random") -> tuple[list[str], dict[str, dict], dict[str, float], str, str]:
    """
    Generate a complete song structure.

    Args:
        form: "standard", "aaba", "rondo", "short", "linear", or "random"

    Returns:
        (structure, layers_map, energy_curve, ending_style, form_name)
    """
    if form == "random" or form not in _FORM_FUNCS:
        form = random.choice(FORMS)

    form_func = _FORM_FUNCS[form]
    structure, curve = form_func()
    layers = _build_layers(structure)
    energy = _build_energy(structure, curve)
    ending = apply_ending(structure, layers, energy)
    return structure, layers, energy, ending, form
