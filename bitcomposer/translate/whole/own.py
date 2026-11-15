"""The balance token's song's own answers to the once-a-song words, for the plan (round 172; rhythm.own counts them).

A plan draws its token, one song's, and then asks that song for every word in rhythm.OWN before the pool: `answer`
looks it up in the vocabulary's `song_answers` table, and the plan's own draw (plan._draw, its `own`) takes the answer
over the pooled draw, which is made all the same, so no stream moves and a song with no answer keeps it. A vocabulary counted before
the round has no `song_answers` table and every word is the pooled draw, as it was.
"""
from __future__ import annotations

from .. import rhythm

TABLE = "song_answers"               # the table of every song's own answers (rhythm.own_units)


def answer(models: dict, song: str | None, word: str, context) -> str | None:
    """The song's own answer to a word under a context, from the `song_answers` table; None without the table, the song or an
    answer (or with two: a word a song answers twice under one context is not a once-a-song word there)."""
    t = (models or {}).get(TABLE)
    if t is None or not song:
        return None
    t = t.table if hasattr(t, "table") else t
    votes = t.votes.get((song, word, rhythm.own_context(context)))
    return next(iter(votes)) if votes and len(votes) == 1 else None
