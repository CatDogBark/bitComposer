"""
The register plan: where the tonal parts sit in a song, decided once from
the drawn voices, in one place and in one order.

Before this (2026-10-18) each part placed itself from its own fixed numbers
and pairwise rules kept them apart: the lead from a window and section
energy, the chord from anchors per family with its top voice capped under
the lead's lower quartile, floored at label 60. Every register change then
moved the next part: lowering the lead a fifth (chosen by ear on a listening page)
dragged the brass chord under it back toward the 147-262 Hz band it had
been moved out of the day before. The plan states the order instead: the
chord sits in its family's register (harmony.REGISTERS, measured on the
17th); the lead's window is the lead voice's own range, its floor allowed
to dip a little under the chord's top anchor, and its phrases start above
that anchor. Nothing is pushed under anything after the fact. The bass and
the arp keep their own placement (bass windows by weight, arp figures over
the chord) and are not in the plan yet.

Lead ranges per voice come from the games: each pack's SPC traces record
the sounding pitch of every voice in every snapshot. Until a voice has its
range in LEAD_RANGES it takes LEAD_RANGE_DEFAULT, labels 53-76 (G3 to E5),
a fifth under the old 60-83 window, which is where the octave fix of the
17th had left every lead and where it was heard as piercing.
"""
from .harmony import anchors_for, family_register

# The lead's window when its voice has no measured range: a fifth under the
# old window. Medians across the sounds land at 349-453 Hz (F4-A4).
LEAD_RANGE_DEFAULT = (53, 76)

# Per preset, from the SPC traces (MIDI lo, hi). Empty until measured; a
# pack may also carry them as its "lead_ranges" habit.
LEAD_RANGES: dict[str, tuple[int, int]] = {}

# Which chord voice the lead's phrases start above: "top" (the highest
# anchor), "middle" (the median anchor) or None for no floor; and by how
# much. Chosen by measurement over the review set (see the module note).
LEAD_FLOOR_ANCHOR = "top"
LEAD_CLEARANCE = 2
# The lead's window may reach this far under the chord's top anchor (a
# phrase can dip into the chord's top, it does not live there).
LEAD_DIP = 4


def plan_registers(lead_preset: str | None, harmony_family: str | None,
                   num_harmony_voices: int, lead_shift: int = 0,
                   lead_ranges: dict | None = None) -> dict:
    """The plan for one song.

    Returns a dict: lead_window (lo, hi), lead_floor (the phrase start's
    lowest label), harmony_window (lo, hi), harmony_anchors (for the song's
    voice count; a pattern with fewer voices asks harmony.anchors_for), and
    counter_window (the lead's). lead_shift moves the lead's window after
    the voice's range is read, for a pack's fine tuning or a comparison.
    """
    ranges = dict(LEAD_RANGES)
    if lead_ranges:
        ranges.update(lead_ranges)
    lo, hi = ranges.get(lead_preset, LEAD_RANGE_DEFAULT)
    lo, hi = lo + lead_shift, hi + lead_shift
    anchors = anchors_for(harmony_family, num_harmony_voices)
    chord_top = max(anchors) if anchors else 0
    _, _, _, hlo, hhi = family_register(harmony_family)
    lead_lo = max(lo, chord_top - LEAD_DIP)
    lead_hi = max(hi, lead_lo + 12)
    if LEAD_FLOOR_ANCHOR == "top":
        floor = chord_top + LEAD_CLEARANCE
    elif LEAD_FLOOR_ANCHOR == "middle" and anchors:
        floor = sorted(anchors)[len(anchors) // 2] + LEAD_CLEARANCE
    else:
        floor = None
    return {
        "lead_window": (lead_lo, lead_hi),
        "lead_floor": floor,
        "harmony_window": (hlo, hhi),
        "harmony_anchors": anchors,
        "counter_window": (lead_lo, lead_hi),
    }
