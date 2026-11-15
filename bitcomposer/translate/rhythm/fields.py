"""A part's fields of the balance token, by name (the refactor after round 178).

The balance token is a line of text: for each part of the band `part=` and its fields joined by ":", then a word for
each fact of the song as a whole. A part's fields were known by their place alone: the builder laid thirty-one values
out in a list, in order, and the reader took `fields[13]`. Here the places have names, in one list, and both sides go
by it: `part_fields_text` writes a part's fields from named values, `PartFields` reads them back by name. The text is
what it was, field for field, so a token counted by any earlier version reads as it did.

The words of the song as a whole go the same way: `SONG_WORDS` is their list in the token's order, `song_words_text`
writes the ones a song says, and `token_words` splits a token into its parts and its words.
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


SONG_WORDS = (                        # the words of the song as a whole, in the token's order, after its parts
    "echo",                      # the song's echo word (round 82)
    "key",                       # its key (round 79)
    "holds",                     # its chord-hold share (round 106)
    "shapes",                    # its chord shapes (round 112)
    "quals",                     # the qualities each degree has (round 127)
    "form",                      # its form's letters and their bars (round 113)
    "loop",                      # the part of the form its loop returns to (round 132)
    "cycle",                     # its harmony's loops by the form's letters (round 121)
    "beat",                      # 2 where it is counted in double time (round 131)
    "feel",                      # its feel where not duple (round 147)
    "top",                       # its loudest part's level of full (round 59)
    "loud",                      # its rendered loudness (round 59; not written since round 152)
    "tempo",                     # its tempo class and its own tempo (rounds 54, 137)
    "struck",                    # where its voices strike in the bar (rounds 159, 166)
    "turns",                     # where its block lines turn, and by what move (rounds 160, 168)
    "pulse",                     # its moving lines by their place in the beat (round 161)
    "rubs",                      # how often a voice sits a semitone from its part (round 165)
    "keeps",                     # how often a voice keeps its note with its line (round 167)
    "follows",                   # how far its tune and counter go with a chord off the key (round 171)
    "song",                      # which song it is (round 172): last, so no token's place among the outcomes moves
)


class SongWords:
    """The words of the song as a whole that a token says, each under its name (SONG_WORDS): its text, the empty string
    for a word said with nothing after it, None for a word the token does not say."""
    __slots__ = SONG_WORDS

    def __init__(self):
        for name in SONG_WORDS:
            setattr(self, name, None)


def token_words(text: str) -> tuple:
    """A balance token split: ([(a part, its fields' text)] in the token's order, its SongWords). Whatever is not one of
    SONG_WORDS is a part, as the token has always been read; a word said twice keeps the later."""
    parts, said = [], SongWords()
    for token in text.split():
        name, _, rest = token.partition("=")
        if name in SONG_WORDS:
            setattr(said, name, rest)
        else:
            parts.append((name, rest))
    return parts, said


def song_words_text(**named: str) -> list:
    """The words of the song as a whole as the token carries them, from named values (SONG_WORDS; a name left out, or
    given None, is a word the song does not say): ["key=9:minor", ...] in the list's order."""
    unknown = sorted(set(named) - set(SONG_WORDS))
    if unknown:
        raise TypeError(f"not words of a song: {', '.join(unknown)}")
    return [f"{name}={named[name]}" for name in SONG_WORDS if named.get(name) is not None]
