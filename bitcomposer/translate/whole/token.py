"""The balance token, read (the refactor after round 178; the record is docs/idiom/phase-4-writing.md).

A written song takes its skeleton from one song's balance token: one line of text, a field a part of the band and a
word for each fact of the song as a whole, written by `rhythm.balance_units` and kept as the `balance` table's outcome.
`read_token` reads that line into a Token: every fact under a name, as `plan._plan_once` goes on to use it. Until this
module the reading was three hundred lines in the middle of that function, each fact a local of it. The text is as it
was: a pack counted by an earlier version reads as it did, a word it lacks left at the value a song without it has.

The readers of single fields and words (`form_of`, `loops_of`, `relation_stretches` and the rest) are here too; the
plan imports them, and whoever took them from the plan still finds them there.
"""
from __future__ import annotations

import math
import re

from .. import harmony, rhythm
from .. import roles as R


class Token:
    """A balance token's facts, each an attribute under the name the plan uses for it: `band` the parts in the token's
    order, `token_song` the id of the song it is, `token_form` its form's letters, and so on, as read_token leaves
    them (its last statement lists every one). The names are attributes and never text here: a kept table's name as a
    string in the writer's source reads as a draw site to tools/vocab_map.py."""

    def __init__(self, **facts):
        self.__dict__.update(facts)


WHOLE_SONG = ""                       # onsets_of's key for a song with no letters: its onsets a bar the whole song through (round 153)
RELATION_PARTS = {"m": R.MELODY, "c": R.COUNTER, "a": R.ACCOMP, "h": R.HARMONY, "r": R.ARP, "b": R.BASS}   # the token's relation letters


def form_of(text: str) -> list | None:
    """The balance token's `form=` field read (round 113, arrangement.form_field): "A2B8C9B8D14" -> [("A", 2), ("B", 8), ("C", 9),
    ("B", 8), ("D", 14)]; None where it cannot be read or has fewer than FORM_PARTS parts."""
    if not re.fullmatch(r"(?:[A-Za-z]\d+)+", text):
        return None
    form = [(m.group(1).upper(), int(m.group(2))) for m in re.finditer(r"([A-Za-z])(\d+)", text)]
    return form if len(form) >= rhythm.FORM_PARTS and all(n > 0 for _, n in form) else None


def loops_of(text: str) -> dict:
    """A voice's loops read from the balance token (round 121, arrangement.loops_text): "B1~75!3.7+D2~100" -> {"B": (1, 0.75,
    (3, 7)), "D": (2, 1.0, ())}, by the form's letter the figure's bars, the share of the voice's bars on it and the bars off
    it counted from the part's first; {} where it cannot be read."""
    out = {}
    for item in text.split("+"):
        m = re.fullmatch(r"([A-Za-z])(\d+)~(\d+)(?:!(\d+(?:\.\d+)*))?", item)
        if not m or int(m.group(2)) < 1:
            return {}
        out[m.group(1).upper()] = (int(m.group(2)), int(m.group(3)) / 100, tuple(int(x) for x in m.group(4).split(".")) if m.group(4) else ())
    return out


def spans_of(text: str) -> dict:
    """The parts of the form a part sounds in, read from the balance token (round 124, arrangement.part_spans_field):
    "A+B2.0+D0.4" -> {"A": (0, 0), "B": (2, 0), "D": (0, 4)}, by the form's letter the bars after the part's start it
    enters and the bars before its end it leaves; {} where it cannot be read."""
    out = {}
    for item in text.split("+"):
        m = re.fullmatch(r"([A-Za-z])(?:(\d+)\.(\d+))?", item)
        if not m:
            return {}
        out[m.group(1).upper()] = (int(m.group(2) or 0), int(m.group(3) or 0))
    return out


def onsets_of(text: str) -> dict:
    """A voice's onsets a bar by the form's letters, read from the balance token (round 125, arrangement.section_onsets_text):
    "A6+B2!1+C4.5!7" -> {"A": (6.0, None), "B": (2.0, 1), "C": (4.5, 7)}, by the letter the median of its onsets a bar there
    and its onsets in the part's last bar where that is a fill or a thinning; a song with no letters says one number
    (round 153), "4" -> {WHOLE_SONG: (4.0, None)}; {} where it cannot be read."""
    whole = re.fullmatch(r"\d+(?:\.\d)?", text)
    if whole:
        return {WHOLE_SONG: (float(text), None)} if float(text) > 0 else {}
    out = {}
    for item in text.split("+"):
        m = re.fullmatch(r"([A-Za-z])(\d+(?:\.\d)?)(?:!(\d+))?", item)
        if not m or float(m.group(2)) <= 0:
            return {}
        out[m.group(1).upper()] = (float(m.group(2)), int(m.group(3)) if m.group(3) is not None else None)
    return out


def kit_onsets_of(text: str) -> dict:
    """The kit's pieces' hits a bar by the form's letters, read from the balance token (round 125, arrangement.kit_onsets_field):
    "AS28.5@100,c1@50+BS20@75" -> {"A": {"S": (28.5, 1.0), "c": (1.0, 0.5)}, "B": {"S": (20.0, 0.75)}}, by the letter each
    piece's median hits a bar over the bars it plays there and the share of the part's bars it plays in; {} where it cannot
    be read."""
    out = {}
    for item in text.split("+"):
        if not item or not (item[0].isalpha() or item[0] == rhythm.WHOLE_KIT):
            return {}
        pieces = {}
        for piece in item[1:].split(","):
            m = re.fullmatch(r"([A-Za-z])(\d+(?:\.\d)?)@(\d+)", piece)
            if not m:
                return {}
            pieces[m.group(1)] = (float(m.group(2)), int(m.group(3)) / 100)
        out[WHOLE_SONG if item[0] == rhythm.WHOLE_KIT else item[0].upper()] = pieces   # a song with no letters (round 155): "*K1@50" -> {WHOLE_SONG: ...}
    return out


def shape_profile_of(text: str) -> dict | None:
    """The balance token's `shapes=` field read (round 112, arrangement.chord_shape_profile): "maj7:45/5:17/maj:3" -> {"maj7":
    0.45, "5": 0.17, "": 0.03}; None where it cannot be read."""
    out = {}
    for part in text.split("/"):
        name, _, pct = part.partition(":")
        shape = "" if name == "maj" else name
        if shape not in harmony.SHAPES or not pct.isdigit():
            return None
        out[shape] = int(pct) / 100
    return out or None


def quals_of(text: str) -> dict:
    """The balance token's `quals=` field read (round 127, arrangement.chord_degree_shapes): "1~maj7:86+0~5:45/sus4:25" ->
    {1: [("maj7", 0.86)], 0: [("5", 0.45), ("sus4", 0.25)]}, by a degree's semitones over the tonic the qualities its song
    gives it with their share of the degree's beats, the most heard first; {} where it cannot be read."""
    out = {}
    for item in text.split("+"):
        offset, _, shapes = item.partition("~")
        pairs = [x.partition(":") for x in shapes.split("/")] if shapes else []
        if not offset.isdigit() or not 0 <= int(offset) < 12 or not pairs or any((n != "maj" and n not in harmony.SHAPES) or not pct.isdigit() for n, _, pct in pairs):
            return {}
        out[int(offset)] = [("" if n == "maj" else n, int(pct) / 100) for n, _, pct in pairs]
    return out


def section_levels_of(text: str) -> list:
    """A part's level in each part of its song's form, read from the balance token (round 150, arrangement.section_levels_field):
    "vA1.0+B0.4+C-" -> [("A", 1.0), ("B", 0.4), ("C", None)], the form's own parts in its order, None where the song's part
    has no count; [] where it cannot be read."""
    if not text.startswith("v"):
        return []
    out = []
    for item in text[1:].split("+"):
        m = re.fullmatch(r"([A-Za-z])(\d\.\d|-)", item)
        if not m:
            return []
        out.append((m.group(1).upper(), None if m.group(2) == "-" else float(m.group(2))))
    return out


def lengths_of(text: str) -> dict:
    """A tune's note lengths as its token's twenty-sixth field carries them (round 141, rhythm.tune_lengths_field, without
    the "h"): {rhythm.LENGTH_WHOLE or a gap class: (the share of the notes held, the share of its gap a held note sounds, a
    detached one; None where the line has none of the kind)}, a class the field leaves out ("-") left out; {} where the
    text is not the field's."""
    names = [rhythm.LENGTH_WHOLE] + [name for _, name in rhythm.GAP_CLASSES]
    entries = text.split("/")
    if len(entries) != len(names):
        return {}
    out = {}
    for name, e in zip(names, entries):
        if e == "-":
            continue
        m = re.fullmatch(r"(\d+)~([\d.]+|-)~([\d.]+|-)", e)
        if not m:
            return {}
        out[name] = (int(m.group(1)) / 100, None if m.group(2) == "-" else float(m.group(2)), None if m.group(3) == "-" else float(m.group(3)))
    return out if rhythm.LENGTH_WHOLE in out else {}


def layer_of(extras: dict) -> tuple:
    """A part's second voice as the plan drew it: ("apart", offset, density), ("doubling", interval) or ("alternating",)."""
    words = (extras or {}).get("layer", "").split()
    if not words:
        return ("stack",)
    if words[0] == "apart" and len(words) >= 3:
        return ("apart", int(words[1]), words[2])
    if words[0] == "doubling" and len(words) >= 2:
        return ("doubling", int(words[1]))
    return (words[0],)


def struck_values_of(text: str) -> dict | None:
    """The balance token's struck sub-field (round 108, arrangement._struck_text) read: "w0.82~0.2~0.3~1.0~0.6~-~4.9~0.53" ->
    {"share": 0.82, "sounds": {gap class: share, or None where the token lacks it}, "longest": 4.9 beats, or None, "sounding":
    0.53 (round 115: the beats the voice sounds over the beats of the bars it strikes in), or None, "cell": 0.72 (round 116: of
    its notes with a note at the same position of the bar before, the share on that note's pitch again), or None}; None where
    it cannot be read."""
    parts = text.split("~")
    n = len(rhythm.GAP_CLASSES)
    if len(parts) not in (2 + n, 3 + n, 4 + n) or not parts[0].startswith("w"):
        return None
    try:
        share, longest = float(parts[0][1:]), float(parts[1 + n])
        sounds = {name: (float(x) if x != "-" else None) for (_, name), x in zip(rhythm.GAP_CLASSES, parts[1:1 + n])}
        sounding = float(parts[2 + n]) if len(parts) >= 3 + n and parts[2 + n] != "-" else None   # the voice's sounding share (round 115)
        cell = float(parts[3 + n]) if len(parts) >= 4 + n and parts[3 + n] != "-" else None       # its cell's repeats (round 116)
    except ValueError:
        return None
    return {"share": share, "sounds": sounds, "longest": longest if longest > 0 else None, "sounding": sounding, "cell": cell}


def struck_places_of(text: str) -> dict:
    """The balance token's `struck=` word (round 159, arrangement.struck_places_field) read: "a3~45:A-+B0.6.18.24" ->
    {the accompaniment: {2: (0.45, {"A": [], "B": [0, 6, 18, 24]})}}: a chord part's voice beside its line (the part's
    relation letter and the voice's number, the line 1; here by the writer's index, the line 0), its median note length
    in beats, and for each letter of the token song's form the places it strikes at in its usual bar there, in twelfths
    of a beat from the bar's start, none where it rests. A voice that cannot be read is left out."""
    out = {}
    for entry in (text or "").split(","):
        head, _, body = entry.partition(":")
        who, _, length = head.partition("~")
        role = RELATION_PARTS.get(who[:1])
        try:
            v, beats = int(who[1:]) - 1, int(length) / 100
            letters = {w[:1]: ([] if w[1:].partition("/")[0] == "-" else [int(x) for x in w[1:].partition("/")[0].split(".")])
                       for w in body.split("+") if w}       # the usual bar; what follows a "/" is voice_places_of's (round 166)
        except ValueError:
            continue
        if role and v > 0 and beats > 0 and letters and all(k.isalpha() for k in letters):
            out.setdefault(role, {})[v] = (beats, letters)
    return out


def voice_rubs_of(text: str) -> dict:
    """The balance token's `rubs=` word (round 165, arrangement.voice_rubs_field) read: "a2~25,a3~0" -> {the
    accompaniment: {1: 0.25, 2: 0.0}}: for a chord part's voice beside its line (the part's relation letter and the
    voice's number, the line 1; here by the writer's index, the line 0), the share of its token voice's notes that sit
    a semitone from a voice of its own part before it. A voice that cannot be read is left out. The `keeps=` word
    (round 167, arrangement.voice_keeps_field) is written the same way and read here too: the share of a voice's
    strikes, where the line keeps its note, on which the voice keeps its own."""
    out = {}
    for entry in (text or "").split(","):
        who, _, share = entry.partition("~")
        role = RELATION_PARTS.get(who[:1])
        try:
            v, got = int(who[1:]) - 1, int(share) / 100
        except ValueError:
            continue
        if role and v > 0 and 0 <= got <= 1:
            out.setdefault(role, {})[v] = got
    return out


def voice_places_of(text: str) -> dict:
    """The places a voice beside a line plays at, from the balance token's `struck=` word (round 166): "a3~45:A-+B0.6,
    a2~30:A-/0.24" -> {the accompaniment: {2: {"B": [0, 6]}, 1: {"A": [0, 24]}}}: for a chord part's voice (by the
    writer's index, the line 0) and each letter of the token song's form, the places of the bar it plays there, in
    twelfths of a beat: its usual bar, or where that is a rest the bar after the "/"; a part it rests through is left
    out. A song with no form says one bar with no letter, kept under WHOLE_SONG. A voice that cannot be read is left
    out."""
    out = {}
    for entry in (text or "").split(","):
        head, _, body = entry.partition(":")
        role = RELATION_PARTS.get(head[:1])
        try:
            v = int(head.partition("~")[0][1:]) - 1
            letters = {}
            for w in body.split("+"):
                letter, rest = (w[:1], w[1:]) if w[:1].isalpha() else (WHOLE_SONG, w)
                bar = rest.partition("/")[2] or rest
                if bar and bar != "-":
                    letters[letter] = [int(x) for x in bar.split(".")]
        except ValueError:
            continue
        if role and v > 0 and letters:
            out.setdefault(role, {})[v] = letters
    return out


def line_pulse_of(text: str) -> dict:
    """The balance token's `pulse=` word (round 161, arrangement.line_pulse_field) read: "a6~73~70~26/68/7" -> {the
    accompaniment: (6, 0.73, 0.70, {"same": 0.26, "step": 0.68, "leap": 0.07})}: a chord part's moving line's pulse (its
    grid in twelfths of a beat), the share of its notes off the pulse that are their bar's one pitch, how often that
    pitch is the bar before's, and the step profile of its notes on the pulse; None for one the word leaves out ("-").
    A part that cannot be read is left out."""
    out = {}
    for entry in (text or "").split(","):
        role, fields = RELATION_PARTS.get(entry[:1]), entry[1:].split("~")
        if not role or len(fields) != 4:
            continue
        try:
            grid = int(fields[0])
            pedal, carry = (None if x == "-" else int(x) / 100 for x in fields[1:3])
            profile = None if fields[3] == "-" else {k: int(x) / 100 for k, x in zip(rhythm.STEP_CLASSES, fields[3].split("/"), strict=True)}
        except ValueError:
            continue
        if grid > 0 and (pedal is not None or profile is not None):
            out[role] = (grid, pedal, carry, profile)
    return out


def line_turns_of(text: str) -> dict:
    """The balance token's `turns=` word (round 160, arrangement.line_turns_field) read: "a-/24/12.42" -> {the
    accompaniment: [[], [24], [12, 42]]}: for a chord part's block line, bar by bar in the token song's order, the
    places at which its note changes, in twelfths of a beat from the bar's start. Since round 168 a place carries the
    move made there ("24+3": line_turn_moves_of reads those); here the places alone. A part that cannot be read is
    left out."""
    return {role: [[place for place, _ in bar] for bar in bars] for role, bars in line_turn_moves_of(text).items()}


def line_turn_moves_of(text: str) -> dict:
    """The balance token's `turns=` word with its moves (round 168): "a-/24+3/12-2.42+2" -> {the accompaniment: [[],
    [(24, 3)], [(12, -2), (42, 2)]]}: for a chord part's block line, bar by bar in the token song's order, the places
    at which its note changes and the move it makes there in semitones; None for a place with no move said (a
    vocabulary counted before the round: "24"). A part that cannot be read is left out."""
    out = {}
    for entry in (text or "").split(","):
        role = RELATION_PARTS.get(entry[:1])
        bars = []
        for w in (entry[1:].split("/") if entry[1:] else []):
            got = [re.fullmatch(r"(\d+)([+-]\d+)?", x) for x in w.split(".")] if w != "-" else []
            if not all(got):
                bars = []
                break
            bars.append([(int(m.group(1)), int(m.group(2)) if m.group(2) else None) for m in got])
        if role and bars:
            out[role] = bars
    return out


def step_profile_of(text: str) -> dict | None:
    """The balance token's step profile field (round 117, arrangement.line_step_profile) read: "j63/24/13" -> {"same": 0.63,
    "step": 0.24, "leap": 0.13}; None where it cannot be read."""
    m = re.fullmatch(r"j(\d+)/(\d+)/(\d+)", text or "")
    if not m:
        m = re.fullmatch(r"j(\d+)/(\d+)/(\d+)/(\d+)", text or "")   # a tune's, of four classes (round 130, arrangement.tune_step_profile)
        return {k: int(v) / 100 for k, v in zip(rhythm.TUNE_MOVES, m.groups())} if m else None
    return {k: int(v) / 100 for k, v in zip(rhythm.STEP_CLASSES, m.groups())}


def tone_profile_of(text: str) -> dict | None:
    """The balance token's chord-tone profile field (round 111, arrangement.line_tone_profile) read: "t45/2/9/30/2/12" -> {"root":
    0.45, "third": 0.02, "fifth": 0.09, "seventh": 0.30, "sus": 0.02, "other": 0.12}; None where it cannot be read."""
    m = re.fullmatch(r"t(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)", text)
    if not m:
        return None
    return {k: int(x) / 100 for k, x in zip(rhythm.TONE_PROFILE_CLASSES, m.groups())}


def relation_stretches(word: str) -> list:
    """A layer voice's relation word (round 90) as stretches: "ox9>dm-12x14>o" -> [("own", None, None, 9), ("double",
    melody, -12, 14), ("own", None, None, None)]: the kind, the part followed, the semitones, the bars (None: to the end).
    A stretch the writer cannot read is its own."""
    out = []
    for part in word.split(">"):
        body, _, n = part.partition("x")
        bars = int(n) if n.isdigit() else None
        kind = {"d": "double", "p": "parallel", "w": "with"}.get(body[:1])
        target = RELATION_PARTS.get(body[1:2])
        if body[1:2] == "l":                                # the part's own line (round 107)
            target = ("line",)
        elif body[1:2].isdigit():                           # a sibling voice, by its rank among the part's voices beside the line (round 107)
            target = ("voice", int(body[1:2]))
        try:
            semi = int(body[2:])
        except ValueError:
            semi = None
        out.append((kind, target, semi, bars) if kind and target and semi is not None else ("own", None, None, bars))
    return out


def line_stretch_list(word: str) -> list:
    """The balance token's eleventh field (round 91) as stretches: "s77ca10e2568@52-64x6>sf89f5aedfd@60-80" ->
    [("s77ca10e2568", (52, 64), 6), ("sf89f5aedfd", (60, 80), None)]: each stretch's sample, the range it is played over
    (None unknown), its bars (None: to the end)."""
    out = []
    for part in word.split(">"):
        body, _, n = part.partition("x")
        sid, _, rng = body.partition("@")
        played = None
        if "-" in rng:
            try:
                lo, hi = (int(x) for x in rng.split("-"))
                played = (lo, hi)
            except ValueError:
                played = None
        out.append((sid, played, int(n) if n.isdigit() else None))
    return out


def follow_pair(text: str, scale: float = 1.0) -> tuple | None:
    """The chord_follows word's two shares read (round 171): "85/60" -> (0.85, 0.60) with `scale` 100, "0.85/-" ->
    (0.85, None); None where it cannot be read or says neither."""
    parts = text.split("/")
    if len(parts) != 2:
        return None
    try:
        pair = tuple(None if x == "-" else float(x) / scale for x in parts)
    except ValueError:
        return None
    return pair if any(x is not None for x in pair) and all(x is None or 0 <= x <= 1 for x in pair) else None


def read_token(text: str, log: list) -> Token:
    """The balance token `text` read: a Token. `log`: the plan's log, which the reading adds its lines to."""
    from .plan import BASS_LAYER_KINDS, LOOP_CHORDS         # noqa: PLC0415  the plan imports this module: its two constants are looked up when asked
    band, weights, layout, shares, counts, token_levels, token_layers, token_kinds, token_samples, token_habits = [], {}, {}, {}, {}, {}, {}, {}, {}, {}
    token_kit, token_kit_levels, token_kit_pitches, token_kit_rates, token_kit_holds, token_layer_samples, token_layer_shares = {}, {}, {}, {}, {}, {}, {}
    token_kit_degrees, token_kit_tuned, token_key, token_kit_classes = {}, set(), None, {}
    token_kit_seconds = {}                                  # each kit letter's second sample (round 99)
    token_kit_echo, token_echo, token_pans, token_kit_pans = set(), None, {}, {}
    token_sample_ranges, token_layer_ranges = {}, {}       # where the token song plays its own samples (round 86)
    token_layer_relations = {}                              # what each voice beyond a line does beside which part, by stretch (round 90)
    token_stretches = {}                                    # the line's instrument by stretch (round 91)
    token_motions, token_tone_tiers = {}, {}                # a chord part's line motion and off-chord tier (round 103): the song's own
    token_profiles = {}                                     # a backing line's chord-tone profile (round 111)
    token_steps = {}                                        # a backing line's step profile (round 117)
    token_shapes = None                                     # the token song's chord-shape profile (round 112)
    token_quals = {}                                        # the qualities each degree has in the token song (round 127)
    token_form = None                                       # the token song's form letters (round 113)
    token_continuity = None                                 # the token song's bass line pitch continuity (round 114)
    token_downbeat = None                                   # how often the token song's bass roots a bar's first beat (round 129)
    token_first = {}                                        # and how often it strikes it (round 133), and a chord part (round 135)
    token_shortest = {}                                     # a tune's shortest usual note in the token song, in milliseconds (round 136)
    token_lengths = {}                                      # and how it sounds its notes, by the gap to the next (round 141)
    token_tones = {}                                        # how often a chord part sounds a chord's tones again in the token song (round 142)
    token_together = {}                                     # and how often a part comes back with its lead (round 144)
    token_tune_together = {}                                # the tune's with the bass, and how often its bars come back at all (round 146)
    token_places = {}                                       # where in the beat a tune's notes fall in the token song (round 147)
    token_with_kit = {}                                     # how often the bass's and the tune's notes are struck with the kit there (round 149)
    token_section_levels = {}                               # a part's level in each part of the token song's form, by its letters (round 150)
    token_loops = {}                                        # each voice's loops by the form's letters, the harmony's among them (round 121)
    token_spans = {}                                        # the parts of the form each part sounds in, with its entrances (round 124)
    token_onsets, token_kit_onsets, token_layer_onsets = {}, {}, {}   # each line's onsets a bar by the form's letters, the kit's pieces', each
                                                            # voice beside a line's (round 125)
    token_layer_words = {}                                  # the bass's voices beside its line: what each does, the layers word's outcome (round 126)
    token_line_company = {}                                 # where a chord part's line doubles the bass or runs parallel to it, by stretch (round 123)
    token_periods, token_rides, token_holds = {}, {}, None   # a backing part's own period and holds, how far a chord part's line rides the
                                                            # bass, the song's chord-hold share (round 106): the riff as the song's own
    token_layer_stretches = {}                              # each voice beyond a line's instrument by stretch (round 92)
    token_layer_struck = {}                                 # how each voice struck with another strikes (round 108)
    token_struck_places = {}                                # and where in the bar it does, by the form's letters (round 159)
    token_voice_places = {}                                 # where each voice beside a line plays in its bar, by the form's letters (round 166)
    token_turns = {}                                        # where a block line's note changes in the token song, bar by bar (round 160)
    token_turn_moves = {}                                   # and the move it makes there (round 168)
    token_pulse = {}                                        # a moving line by its place in the beat in the token song (round 161)
    token_rubs = {}                                         # how often a voice sits a semitone from its own part in the token song (round 165)
    token_keeps = {}                                        # how often a voice keeps its note where its line keeps its own (round 167)
    token_follows = {}                                      # how far the tune and the counter go with a chord off the key (round 171)
    token_song = ""                                         # the token's song's id (round 172)
    token_gap_shares = {}                                   # a chord part's or the bass's line: the share a note sounds by its gap class (round 95)
    token_kit_channels = []                                # the kit's channels, each one's pieces (round 87)
    token_class, token_top, token_loud = None, None, None
    token_tempo = None                                      # the token's song's own tempo, where the token carries it (round 137)
    token_beat = 1                                          # 2 where the token's song is counted in double time (round 131)
    token_feel = rhythm.FEELS[0]                            # the token's song's feel (round 147): duple where the token does not say
    token_loop = None                                       # the part of its form the token's song's loop returns to (round 132)
    parts, spoken = rhythm.token_words(text)                # the parts' fields in the token's order, and the song's words by name
    for role, rest in parts:
        band.append(role)
        if rest:
            f = rhythm.PartFields(rest)                     # the part's fields by name (rhythm.PART_FIELDS)
            if f.weight:
                weights[role] = f.weight
            if "-" in f.register:        # the song's layout, note lengths, voices and levels a part come with its balance
                lo, hi = f.register.split("-")
                layout[role] = (int(lo), int(hi))
            if f.sounds:
                head, _, by_gap = f.sounds.partition("@")   # the line voice's sounded share, and since round 95 its share by gap class
                shares[role] = float(head)
                if by_gap:
                    token_gap_shares[role] = {g: (float(x) if x not in ("", "-") else None) for (_, g), x in zip(rhythm.GAP_CLASSES, by_gap.split("/"))}
            if f.voices:
                if role == R.DRUMS:                         # the kit's channels (round 87): the pieces each game channel plays, "KS|h"
                    token_kit_channels = f.voices.split("|")
                else:
                    counts[role] = int(f.voices)
            if f.level and math.isfinite(float(f.level)):   # a "nan" level (tables counted before the
                token_levels[role] = float(f.level)                             # readings skipped a kit's unread levels) falls to the levels draw
            if f.layers:               # the voices beyond the line, the busiest first, each over the line's level; since
                parts_ = [x.split("@") for x in f.layers.split("/")]   # round 65 with each one's sample and its notes over the line's
                token_layers[role] = [float(x[0]) for x in parts_]
                if any(len(x) > 1 and x[1] for x in parts_):
                    token_layer_samples[role] = [x[1] if len(x) > 1 else "" for x in parts_]
                if any(len(x) > 2 for x in parts_):
                    token_layer_shares[role] = [float(x[2]) if len(x) > 2 and x[2] else 1.0 for x in parts_]
                if any(len(x) > 3 and "-" in x[3] for x in parts_):   # each voice's range on its own sample in the token song (round 86)
                    token_layer_ranges[role] = [tuple(int(y) for y in x[3].split("-")) if len(x) > 3 and "-" in x[3] else None for x in parts_]
                if any(len(x) > 4 and x[4] for x in parts_):   # and what each does beside which part, stretch by stretch (round 90)
                    token_layer_relations[role] = [x[4] if len(x) > 4 and x[4] else None for x in parts_]
                if any(len(x) > 5 and x[5] for x in parts_):   # and each one's instrument by stretch (round 92; "~" between a sample and its range)
                    token_layer_stretches[role] = [line_stretch_list(x[5].replace("~", "@")) if len(x) > 5 and x[5] else None for x in parts_]
                if any(len(x) > 6 and x[6] for x in parts_):   # and how a voice struck with another strikes (round 108): its share of the
                    token_layer_struck[role] = [struck_values_of(x[6]) if len(x) > 6 and x[6] else None for x in parts_]   # followed onsets, its
                for i, x in enumerate(parts_, start=1):     # and each one's loops by the form's letters (round 121): "lB1~75!3.7"
                    if len(x) > 7 and x[7].startswith("l") and loops_of(x[7][1:]):
                        token_loops[f"{role}:{i}"] = loops_of(x[7][1:])
                    if len(x) > 8 and x[8].startswith("n") and onsets_of(x[8][1:]):   # and its onsets a bar by them (round 125)
                        token_layer_onsets.setdefault(role, {})[i] = onsets_of(x[8][1:])
                    if len(x) > 9 and x[9].startswith("v") and layer_of({"layer": x[9][1:].replace("_", " ")})[0] in BASS_LAYER_KINDS:   # and what a
                        token_layer_words.setdefault(role, {})[i] = x[9][1:].replace("_", " ")   # bass's voice does beside the line (round 126)
                                                                                                                        # lengths by the line's gap, its longest
            if f.kind:               # the counter's kind: on the tune's sample or another (round 39)
                token_kinds[role] = f.kind
            if f.sample and role == R.DRUMS:   # the song's kit (round 63): a piece letter and its sample, by the comma;
                for x in f.sample.split(","):                       # since round 68 each piece's own level after an "@", where its song read one
                    if "=" not in x:
                        continue
                    letter, _, value = x.partition("=")
                    value, _, second_text = value.partition("+")   # the letter's second sample after a "+" (round 99)
                    sid, _, rest = value.partition("@")
                    level, _, rest = rest.partition("@")    # since round 75 the note the piece is struck at follows the level's slot,
                    pitch, _, rest = rest.partition("@")    # since round 77 a tonal piece's hold in beats follows the note's,
                    hold, _, rest = rest.partition("@")     # since round 81 the slot's strike class the hold's (a/s/m/d),
                    cls, _, rest = rest.partition("@")      # since round 82 an e where the game sends the piece to echo,
                    mark, _, pan = rest.partition("@")      # since round 84 the piece's pan after the mark (the right side's share)
                    token_kit[letter] = sid
                    if cls and cls[0] in rhythm.SLOT_NAMES:
                        token_kit_classes[letter] = cls[0]
                    if mark.startswith("e"):
                        token_kit_echo.add(letter)
                    if pan and math.isfinite(float(pan)):
                        token_kit_pans[letter] = float(pan)
                    if level and math.isfinite(float(level)):
                        token_kit_levels[letter] = float(level)
                    if pitch.startswith("r"):               # the chip's rate as a note (round 78), for a piece the namer called a drum;
                        if pitch.endswith("t"):              # "t": the game tunes this sample to the key (round 79)
                            token_kit_tuned.add(letter)
                        token_kit_rates[letter] = int(round(float(pitch[1:].rstrip("t"))))
                    elif pitch.startswith(("d", "c")):      # a degree of the token song's key (round 79): scale steps, or semitones off it
                        token_kit_degrees[letter] = (pitch[0], int(pitch[1:]))
                    elif pitch:                             # the absolute note (round 75's form, read still)
                        token_kit_pitches[letter] = int(round(float(pitch)))
                    if hold and float(hold) > 0:
                        token_kit_holds[letter] = float(hold)
                    if second_text:                         # the second sample's id, level, note or rate, hold and share (round 99)
                        s2, l2, n2, h2, sh2 = (second_text.split("@") + [""] * 5)[:5]
                        try:
                            share2 = float(sh2)
                        except ValueError:
                            share2 = None
                        if s2 and share2 is not None:
                            second = {"sample": s2, "share": share2, "level": float(l2) if l2 and math.isfinite(float(l2)) else None,
                                      "hold": float(h2) if h2 and float(h2) > 0 else None, "rate": None, "degree": None, "pitch": None, "tuned": False}
                            if n2.startswith("r"):
                                second["rate"] = int(round(float(n2[1:].rstrip("t"))))
                                second["tuned"] = n2.endswith("t")
                            elif n2.startswith(("d", "c")):
                                second["degree"] = (n2[0], int(n2[1:]))
                            elif n2:
                                second["pitch"] = int(round(float(n2)))
                            token_kit_seconds[letter] = second
            elif f.sample:             # the part's own sample (round 60): the song's instruments with its levels,
                sid, _, played = f.sample.partition("@")   # and since round 86 the range the song plays it over ("s1d296a2572@32-52")
                token_samples[role] = sid
                if "-" in played:
                    token_sample_ranges[role] = tuple(int(x) for x in played.split("-"))
            if f.habit:               # the part's habit (round 62): the song's density tiers together
                token_habits[role] = f.habit.replace("+", " ")
            if f.pans:               # the part's voices' pans (round 84): the line's first, then the voices beyond it;
                token_pans[role] = [float(x) if re.fullmatch(r"[0-9.]+", x) else x for x in f.pans.split("/")]   # a voice's two
                                                            # places kept as written, "0.60x5|0.45x13" or "0.35x4>0.65" (round 85, render.pan_of)
            if f.stretches:             # the line's instrument by stretch (round 91): each stretch's sample, range and bars
                token_stretches[role] = line_stretch_list(f.stretches)
            if f.motion:             # the line's motion (round 103): block, mixed or arpeggiated, the token song's own
                token_motions[role] = f.motion
            if f.tone_tier:             # the line's off-chord tier (round 103): rare, some or many, the token song's own
                token_tone_tiers[role] = f.tone_tier
            if f.period:             # the part's own period and hold share (round 106): `p2/83`
                m_ = re.fullmatch(r"p(\d+)/(\d+)", f.period)
                if m_:
                    token_periods[role] = (int(m_.group(1)), int(m_.group(2)) / 100)
            if f.rides:             # how far the line rides the bass (round 106): `b75/70`, onsets with it / at its pitch class
                m_ = re.fullmatch(r"b(\d+)/(\d+)", f.rides)
                if m_:
                    token_rides[role] = (int(m_.group(1)) / 100, int(m_.group(2)) / 100)
            if f.continuity and role == R.BASS:   # the bass line's pitch continuity (round 114): `k58`
                m_ = re.fullmatch(r"k(\d+)", f.continuity)
                if m_:
                    token_continuity = int(m_.group(1)) / 100
                    log.append(f"the bass keeps its pitch class across {token_continuity:.2f} of its bar lines in the balance's song")
            if f.tones:             # the line's chord-tone profile (round 111): `t45/2/9/30/2/12`
                prof = tone_profile_of(f.tones)
                if prof:
                    token_profiles[role] = prof
                    log.append(f"{role}'s line plays the balance's song's chord tones: " + " ".join(f"{k} {v:.2f}" for k, v in prof.items()))
            if f.steps:             # the line's step profile (round 117): `j63/24/13`
                steps = step_profile_of(f.steps)
                if steps:
                    token_steps[role] = steps
                    log.append(f"{role}'s line moves as the balance's song's: " + " ".join(f"{k} {v:.2f}" for k, v in steps.items()))
            if f.loops.startswith("l") and loops_of(f.loops[1:]):   # the line's loops, the kit's (round 121): `lB1~100`
                token_loops[role] = loops_of(f.loops[1:])
            if f.company.startswith("r") and any(st[0] != "own" for st in relation_stretches(f.company[1:])):   # where the line
                token_line_company[role] = f.company[1:]   # doubles the bass, by stretch (round 123): `rdb+12x2>ox8>db+12`
            if f.spans.startswith("e") and spans_of(f.spans[1:]):   # the parts of the form the part sounds
                token_spans[role] = spans_of(f.spans[1:])   # in, with its entrances (round 124): `eA+B2.0+D0.4`
            if role == R.BASS and re.fullmatch(r"d\d+", f.downbeat):   # how often the bass strikes a bar's first beat on the
                token_downbeat = int(f.downbeat[1:]) / 100   # chord's root (round 129): `d73`
                log.append(f"the bass strikes a bar's first beat on the chord's root in {token_downbeat:.2f} of its bars in the balance's song")
            if role in rhythm.UPPER + (R.BASS,) and re.fullmatch(r"f\d+", f.first):   # how often the part strikes a
                token_first[role] = int(f.first[1:]) / 100   # bar's first beat: the bass (round 133), a chord part (round 135): `f93`
                log.append(f"the {role} strikes a bar's first beat in {token_first[role]:.2f} of its bars in the balance's song")
            if role in (R.MELODY, R.COUNTER) and re.fullmatch(r"m\d+", f.shortest) and int(f.shortest[1:]) > 0:   # a tune's
                token_shortest[role] = int(f.shortest[1:])  # shortest usual note (round 136): `m150`
                log.append(f"the {role}'s shortest usual note sounds {token_shortest[role]} ms in the balance's song")
            if role in (R.MELODY, R.COUNTER) and f.lengths.startswith("h") and lengths_of(f.lengths[1:]):   # how the tune
                token_lengths[role] = lengths_of(f.lengths[1:])   # sounds its notes, by the gap (round 141): `h50~0.90~0.40/-/26~0.90~0.55/...`
                log.append(f"the {role} holds {token_lengths[role][rhythm.LENGTH_WHOLE][0]:.2f} of its notes in the balance's song; its note lengths by the gap (round 141): {f.lengths[1:]}")
            if role in rhythm.UPPER and re.fullmatch(r"c\d+/\d+", f.tones_kept):   # how often a chord part sounds again
                token_tones[role] = tuple(int(x) / 100 for x in f.tones_kept[1:].split("/"))   # the pitch classes it played on a chord before, and
                log.append(f"the {role} sounds an earlier bar's pitch classes on a chord again in {token_tones[role][0]:.2f} of such bars in the balance's song, "   # how often the bar before's
                           f"the bar before's in {token_tones[role][1]:.2f} of those (round 142)")   # (round 142): `c60/47`
            if role in rhythm.UPPER + (R.COUNTER,) and re.fullmatch(r"w\d+", f.together):   # how often it plays an earlier bar
                token_together[role] = int(f.together[1:]) / 100   # again where its lead does (round 144): `w66`
                log.append(f"the {role} plays an earlier bar again where the {'tune' if role == R.COUNTER else 'bass'} does in {token_together[role]:.2f} of such bars in the balance's song (round 144)")
            if role in (R.MELODY, R.COUNTER) and re.fullmatch(r"w(\d+|-)/(\d+|-)/\d+", f.together):   # the tune: how often it
                token_tune_together[role] = tuple(None if x == "-" else int(x) / 100 for x in f.together[1:].split("/"))   # plays an earlier bar again
                far, near, overall = token_tune_together[role]   # where the bass brings one back from further off, where it stands on the bar before,
                said = lambda x: "by no count (under four such bars)" if x is None else f"in {x:.2f} of such bars"   # noqa: E731    # and how often
                log.append(f"the {role} plays an earlier bar again where the bass plays one from further back again {said(far)} in the balance's song, "   # at all (round
                           f"where it plays the bar before again {said(near)}, and an earlier bar again in {overall:.2f} of its bars (round 146)")   # 146): `w48/-/29`
            if role in rhythm.PLACE_PARTS and re.fullmatch(r"p\d+/\d+/\d+(/\d+)?", f.places):   # where in the beat a tune's
                token_places[role] = tuple(int(x) / 100 for x in f.places[1:].split("/"))   # notes fall (round 147): `p12/0/3`, and since round 169
                log.append(f"the {role} plays {token_places[role][0]:.2f} of its notes on a quarter of the beat in the balance's song, {token_places[role][1]:.2f} on a third, "   # the half
                           f"{token_places[role][2]:.2f} finer (round 147)"                                                                                                   # beat: `p12/0/3/20`
                           + (f", {token_places[role][3]:.2f} on the half beat (round 169)" if len(token_places[role]) > 3 else ""))
            if re.fullmatch(r"x\d+/\d+" if role == R.BASS else r"x\d+", f.with_kit) and role in rhythm.KIT_PARTS:   # how often its
                token_with_kit[role] = tuple(int(x) / 100 for x in f.with_kit[1:].split("/"))   # notes are struck with the kit (round 149): `x100/84`, `x91`
                log.append(f"the {role} strikes {token_with_kit[role][0]:.2f} of its notes with a kit hit in the balance's song"
                           + (f", and {token_with_kit[role][1]:.2f} of the kit's hits carry a bass note" if role == R.BASS else "") + " (round 149)")
            if role != R.DRUMS and section_levels_of(f.section_levels):   # its level in each part of the form over its level in
                token_section_levels[role] = section_levels_of(f.section_levels)   # the song (round 150): `vA1.0+B0.4`
            if f.onsets.startswith("n"):   # how busy it is in each (round 125): the line's onsets a bar `nA6+B2!1`,
                if role == R.DRUMS:                         # the kit's pieces' hits a bar `nAS28.5@100,c1@50`
                    token_kit_onsets = kit_onsets_of(f.onsets[1:])
                elif onsets_of(f.onsets[1:]):
                    token_onsets[role] = onsets_of(f.onsets[1:])
    if spoken.echo is not None:                             # the token's song's echo word (round 82): the written song sits in its room
        token_echo = spoken.echo
    if spoken.key is not None:                              # the token's song's key (round 79): the kit's degrees and tuned rates read against it
        t, _, m = spoken.key.partition(":")
        token_key = (int(t), m or "major")
    if spoken.holds is not None:                            # the token's song's chord-hold share (round 106), not a part
        token_holds = float(spoken.holds)
    if spoken.shapes is not None:                           # the token's song's chord shapes (round 112), not a part
        token_shapes = shape_profile_of(spoken.shapes)
        if token_shapes:
            log.append("the balance's song's chord shapes: " + " ".join(f"{sh or 'maj'} {v:.2f}" for sh, v in token_shapes.items()))
    if spoken.quals is not None:                            # the qualities each degree has in the token's song (round 127), not a part
        token_quals = quals_of(spoken.quals)
    if spoken.form is not None:                             # the token's song's form (round 113), not a part
        token_form = form_of(spoken.form)
        if token_form:
            log.append("the balance's song's form: " + " ".join(f"{l}{n}" for l, n in token_form))
    if spoken.loop is not None:                             # the part of its form the token's song's loop returns to (round 132), not a part
        token_loop = int(spoken.loop) if spoken.loop.isdigit() else None
    if spoken.cycle is not None:                            # the token's song's harmony's loops (round 121), not a part
        got = loops_of(spoken.cycle)
        if got:
            token_loops[LOOP_CHORDS] = got
    if spoken.beat is not None:                             # the token's song is counted in double time (round 131), not a part
        token_beat = int(spoken.beat) if spoken.beat.isdigit() and int(spoken.beat) > 0 else 1
    if spoken.feel is not None:                             # the token's song's feel (round 147), not a part
        token_feel = spoken.feel if spoken.feel in rhythm.FEELS else rhythm.FEELS[0]
    if spoken.top is not None:                              # the token's song's loudest part, of full (round 59), not a part
        token_top = float(spoken.top)
    if spoken.loud is not None:                             # the token's song's rendered loudness in dBFS (round 59), not a part
        token_loud = float(spoken.loud)
    if spoken.tempo is not None:                            # the token's song's tempo class (round 54) and its own tempo (round 137:
        token_class, _, own = spoken.tempo.partition(":")       # `fast:140`), not a part
        token_tempo = float(own) if own.replace(".", "", 1).isdigit() and float(own) > 0 else None
    if spoken.struck is not None:                           # where the token's song's struck voices strike (round 159), not a part
        token_struck_places = struck_places_of(spoken.struck)
        token_voice_places = voice_places_of(spoken.struck)      # the same word: every voice beside a line (round 166)
    if spoken.turns is not None:                            # where the token's song's block lines turn (round 160), not a part
        token_turns = line_turns_of(spoken.turns)
        token_turn_moves = line_turn_moves_of(spoken.turns)
    if spoken.pulse is not None:                            # the token's song's moving lines by their place in the beat (round 161), not a part
        token_pulse = line_pulse_of(spoken.pulse)
    if spoken.rubs is not None:                             # how often the token's song's voices sit a semitone from their own part (round 165)
        token_rubs = voice_rubs_of(spoken.rubs)
    if spoken.keeps is not None:                            # how often the token's song's voices keep their note with their line (round 167)
        token_keeps = voice_rubs_of(spoken.keeps)
    if spoken.follows is not None:                          # how far the token's song's tune and counter go with a chord off the key (round 171)
        by = {v: k for k, v in rhythm.FOLLOW_LETTERS.items()}
        for w in spoken.follows.split(","):
            pair = follow_pair(w[1:], 100)
            if w[:1] in by and pair:
                token_follows[by[w[:1]]] = pair
    if spoken.song is not None:                             # which song the token is (round 172), not a part
        token_song = spoken.song
    return Token(
        band=band, counts=counts, layout=layout, shares=shares, token_beat=token_beat, token_class=token_class, token_continuity=token_continuity,
        token_downbeat=token_downbeat, token_echo=token_echo, token_feel=token_feel, token_first=token_first, token_follows=token_follows,
        token_form=token_form, token_gap_shares=token_gap_shares, token_habits=token_habits, token_holds=token_holds, token_keeps=token_keeps,
        token_key=token_key, token_kinds=token_kinds, token_kit=token_kit, token_kit_channels=token_kit_channels,
        token_kit_classes=token_kit_classes, token_kit_degrees=token_kit_degrees, token_kit_echo=token_kit_echo, token_kit_holds=token_kit_holds,
        token_kit_levels=token_kit_levels, token_kit_onsets=token_kit_onsets, token_kit_pans=token_kit_pans, token_kit_pitches=token_kit_pitches,
        token_kit_rates=token_kit_rates, token_kit_seconds=token_kit_seconds, token_kit_tuned=token_kit_tuned, token_layer_onsets=token_layer_onsets,
        token_layer_ranges=token_layer_ranges, token_layer_relations=token_layer_relations, token_layer_samples=token_layer_samples,
        token_layer_shares=token_layer_shares, token_layer_stretches=token_layer_stretches, token_layer_struck=token_layer_struck,
        token_layer_words=token_layer_words, token_layers=token_layers, token_lengths=token_lengths, token_levels=token_levels,
        token_line_company=token_line_company, token_loop=token_loop, token_loops=token_loops, token_loud=token_loud, token_motions=token_motions,
        token_onsets=token_onsets, token_pans=token_pans, token_periods=token_periods, token_places=token_places, token_profiles=token_profiles,
        token_pulse=token_pulse, token_quals=token_quals, token_rides=token_rides, token_rubs=token_rubs, token_sample_ranges=token_sample_ranges,
        token_samples=token_samples, token_section_levels=token_section_levels, token_shapes=token_shapes, token_shortest=token_shortest,
        token_song=token_song, token_spans=token_spans, token_steps=token_steps, token_stretches=token_stretches,
        token_struck_places=token_struck_places, token_tempo=token_tempo, token_together=token_together, token_tone_tiers=token_tone_tiers,
        token_tones=token_tones, token_top=token_top, token_tune_together=token_tune_together, token_turn_moves=token_turn_moves,
        token_turns=token_turns, token_voice_places=token_voice_places, token_with_kit=token_with_kit, weights=weights,
    )
