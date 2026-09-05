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


def _build_layers(structure: list[str]) -> dict[str, dict]:
    """Build per-section layer map from a structure list."""
    layers = {}
    verse_count = 0
    for section in structure:
        st = section_type(section)
        if st == "verse":
            verse_count += 1
            if verse_count > 1:
                layers[section] = dict(LAYERS["verse_full"])
            else:
                layers[section] = dict(LAYERS["verse"])
        elif section in LAYERS:
            layers[section] = dict(LAYERS[section])
        else:
            layers[section] = dict(LAYERS.get(st, LAYERS["verse"]))
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


def build_orders(structure: list[str], pattern_index_for: dict,
                 progression: list, alt_progression: list,
                 use_alt_chorus: bool) -> list[int]:
    """Build the order list from the song structure.

    pattern_index_for maps (section, chord_idx) to a pattern index. Sections
    that share content and rendering map to the same index, so the order list
    replays one pattern instead of carrying a near-duplicate.
    """
    orders = []
    for section in structure:
        section_prog = get_section_progression(
            section, progression, alt_progression, use_alt_chorus)
        for chord_idx in range(len(section_prog)):
            orders.append(pattern_index_for[(section, chord_idx)])
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
