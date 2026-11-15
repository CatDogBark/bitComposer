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
    """The song's own answer to a word under a context, from the `song_answers` table; None without the table, the song
    or an answer. A word the song answers many times under one context (round 174: a unit a note, as the voices' note
    lengths are counted) is answered by its middle answer where the answers are numbers, the one at the half of its
    votes in their order; where they are not numbers there is no one answer, and None."""
    t = (models or {}).get(TABLE)
    if t is None or not song:
        return None
    t = t.table if hasattr(t, "table") else t
    votes = t.votes.get((song, word, rhythm.own_context(context)))
    if not votes:
        return None
    if len(votes) == 1:
        return next(iter(votes))
    try:
        ranked = sorted(votes.items(), key=lambda kv: float(kv[0]))
    except ValueError:
        return None
    half, run = sum(v for _, v in ranked) / 2, 0.0
    for outcome, v in ranked:
        run += v
        if run >= half - 1e-12:
            return outcome
    return ranked[-1][0]
