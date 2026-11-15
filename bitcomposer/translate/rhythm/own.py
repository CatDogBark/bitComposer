"""Each song's own answers to the once-a-song words (round 172 of docs/idiom/phase-4-writing.md).

A word that says something of a song as a whole (how often its tune sits a semitone from the band, how far it leaves
the key) is counted a song at a time and kept as a table over every song: a pooled word. A song written on one
song's balance token then drew such a word from the pool, another song's answer more often than not, beside the two
hundred and more facts the token itself carries; and round after round a pooled word heard to disagree with the rest
of the song was moved onto the token by hand, a field at a time. Here the tables keep each song's own answer beside
the pooled counts: the `song_answers` table, by the song, the word and the word's context. The token says which song it is
(`song=`), and the plan asks that song first and the pool where it has no answer (a jingle with too few notes to
count). Which words go by the song is the list OWN.
"""
from __future__ import annotations

from .. import tables
from . import arrangement as arrangement_mod

OWN_SHAPE = ("song", "word", "context")   # the song_answers table's shape: the song's id, the word's table, its context joined (own_context)
OWN = {                               # the once-a-song words answered by the token's song first: table -> (its units' builder, its shape)
    "clashes": ("clash_units", ("part", "place")),
    "off_scale": ("off_scale_units", ("part", "mode", "place")),
    "chord_tones": ("chord_tone_habit_units", ("part",)),
}


def own_context(values) -> str:
    """A word's context as the song_answers table keeps it: its values in the word's shape's order, joined by "|"."""
    return "|".join(str(v) for v in values)


def own_units(songs) -> list:
    """Every song's own answer to each of the OWN words under each context it has one for, as a unit of the
    `song_answers` table: its outcome the answer, its values the song's id, the word and the context. A song with no unit of a word
    under a context (too few notes for a share) has no answer there, and a written song draws the pooled word."""
    out = []
    for word, (builder, shape) in OWN.items():
        for u in getattr(arrangement_mod, builder)(songs):
            out.append(tables.Unit(u.song, u.game, u.outcome, {"song": u.song, "word": word, "context": own_context(u.values[c] for c in shape)}))
    return out
