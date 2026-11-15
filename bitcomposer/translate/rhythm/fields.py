"""A part's fields of the balance token, by name (the refactor after round 178).

The balance token is a line of text: for each part of the band `part=` and its fields joined by ":", then a word for
each fact of the song as a whole. A part's fields were known by their place alone: the builder laid thirty-one values
out in a list, in order, and the reader took `fields[13]`. Here the places have names, in one list, and both sides go
by it: `part_fields_text` writes a part's fields from named values, `PartFields` reads them back by name. The text is
what it was, field for field, so a token counted by any earlier version reads as it did.
"""
from __future__ import annotations

PART_FIELDS = (                       # a part's fields in the token's order; the round that added each is in rhythm.balance_units
    "weight",                         # the part's weight in the band (minor, half, main); a kit has none
    "register",                       # the register its line plays in, low-high
    "sounds",                         # the share of its gap a note sounds, and after an "@" the share by gap class
    "voices",                         # how many voices it holds; for the kit, its channels' pieces
    "level",                          # its level as a share of the song's loudest part's
    "layers",                         # the voices beyond the line, each with its level, sample, relation word and the rest
    "kind",                           # the counter-line's kind: on the tune's sample or another
    "sample",                         # the part's own sample and the range the song plays it over; for the kit, its pieces
    "habit",                          # its density habit
    "pans",                           # its voices' pans
    "stretches",                      # the line's instrument by stretch
    "motion",                         # a chord part's line motion
    "tone_tier",                      # and its off-chord tier
    "period",                         # the part's own period and its hold share
    "rides",                          # how far a chord part's line rides the bass
    "tones",                          # the line's chord-tone profile
    "continuity",                     # the bass line's pitch continuity
    "steps",                          # the line's step profile
    "loops",                          # the line's loops by the form's letters; the kit's
    "company",                        # where a chord part's line doubles the bass or runs parallel to it
    "spans",                          # the parts of the form the part sounds in, with its entrances
    "onsets",                         # its line's onsets a bar by the form's letters; the kit's pieces'
    "downbeat",                       # how often the bass roots a bar's first beat
    "first",                          # how often the part strikes a bar's first beat
    "shortest",                       # a tune's shortest usual note
    "lengths",                        # how a tune sounds its notes, by the gap
    "tones_kept",                     # how often a chord part sounds a chord's tones again
    "together",                       # how often the part comes back with its lead
    "places",                         # where in the beat its notes fall
    "with_kit",                       # how often its notes are struck with the kit
    "section_levels",                 # its level in each part of the form
)


class PartFields:
    """A part's fields as the token carries them (`text`, what follows `part=`), each under its name (PART_FIELDS); a
    field the token does not reach, or leaves empty, is the empty string."""
    __slots__ = PART_FIELDS

    def __init__(self, text: str = ""):
        values = text.split(":")
        for i, name in enumerate(PART_FIELDS):
            setattr(self, name, values[i] if i < len(values) else "")


def part_fields_text(**named: str) -> str:
    """A part's fields as the token carries them, from named values (PART_FIELDS; a name left out is an empty field):
    in the list's order, joined by ":", the fields a song lacks left off the end, not left empty."""
    unknown = sorted(set(named) - set(PART_FIELDS))
    if unknown:
        raise TypeError(f"not fields of a part: {', '.join(unknown)}")
    fields = [named.get(name, "") for name in PART_FIELDS]
    while fields and not fields[-1]:
        fields.pop()
    return ":".join(fields)
