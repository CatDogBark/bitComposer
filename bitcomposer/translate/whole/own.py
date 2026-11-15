"""The balance token's song's own answers to the once-a-song words, for the plan (round 172; rhythm.own counts them).

A plan draws its token, one song's, and then asks that song for every word in rhythm.OWN before the pool: `answer`
looks it up in the vocabulary's `song_answers` table, `take` puts the answers over a part's pooled draws. The pooled draw is
made all the same (the caller's), so no stream moves and a song with no answer keeps it. A vocabulary counted before
the round has no `song_answers` table and every word is the pooled draw, as it was.
"""
from __future__ import annotations

from .. import rhythm

TABLE = "song_answers"               # the table of every song's own answers (rhythm.own_units)
PLACES = ("strong", "weak")           # the beat a share is counted by, for the words kept by it (clashes, off_scale)


def answer(models: dict, song: str | None, word: str, context) -> str | None:
    """The song's own answer to a word under a context, from the `song_answers` table; None without the table, the song or an
    answer (or with two: a word a song answers twice under one context is not a once-a-song word there)."""
    t = (models or {}).get(TABLE)
    if t is None or not song:
        return None
    t = t.table if hasattr(t, "table") else t
    votes = t.votes.get((song, word, rhythm.own_context(context)))
    return next(iter(votes)) if votes and len(votes) == 1 else None


def take(models: dict, song: str | None, role: str, extras: dict | None, mode: str, log: list) -> None:
    """A part's pooled draws of the OWN words replaced by its token song's own answers where it has them: its share
    of notes a semitone from the parts under it (clashes) and off the key (off_scale) by the beat, and its share of
    chord tones on the beat (chord_tones). Says what it took, and what the draw had been."""
    if not extras or not song or TABLE not in (models or {}):
        return
    said = []
    for word, context in (("clashes", lambda pl: (role, pl)), ("off_scale", lambda pl: (role, mode, pl))):
        if isinstance(extras.get(word), dict):
            for pl in PLACES:
                own = answer(models, song, word, context(pl))
                if own is not None and float(own) != extras[word].get(pl):
                    said.append(f"{word} {pl} {float(own):.2f} (the draw {extras[word].get(pl):.2f})")
                    extras[word][pl] = float(own)
    if "chord_tones" in extras:
        own = answer(models, song, "chord_tones", (role,))
        if own is not None and float(own) != extras["chord_tones"]:
            said.append(f"chord_tones {float(own):.2f} (the draw {extras['chord_tones']:.2f})")
            extras["chord_tones"] = float(own)
    if said:
        log.append(f"{role}: the balance's song's own answers (round 172): " + ", ".join(said))
