"""Whole songs written from a pack's tables (phase 4 of docs/IDIOM.md, the
integration): no original to follow, every part free, on a skeleton the
tables give.

    python tools/whole.py --pack PACK.json --seeds 1-20 -o DIR

The plan comes first, each draw from the pack's tables, once a song: the
key and the tempo; the form, part by part (new, again or back by index,
each new part's length by the song's length habit, a repeat as long as the
part it repeats) and the bar the loop returns to (after an intro: a first
part the form never comes back to); the band with each part's weight (one
of the game's songs' balances); the chords, bar by bar from the chord
mixture (a repeated part keeps its chords; the loop's first bar from the
loops table); the texture a part of the form (which parts sound through
it, among the band's: the part-textures table, a part keeping one texture
through nine bars in ten in the readings); each part's register, sounded
share and habits, the drums' each group's own. Then the parts are written
in turn by the free writers on a Song built from the plan: the drums, the
bass, the upper parts (harmony, accompaniment, arp), the melody and the
counter-line, each reading the band written before it (its shared hits
to lock to, counted against the band the plan has playing in the bar; its
sounding tones to stay clear of), as a part substituted into a game's
song reads the song. The band's energy is not read here: the texture is
the arrangement, and a part the plan has play alone plays. Last the notes
become a score on the pack's samples, rendered by the converter's back
end as a game's song is (spc.convert.render), and the score is read back
by the readers for the measures.

What is hand-set here is the rendering, not the writing: the voices'
levels and pans (LEVELS, PANS), how the eight voices are shared out
(WANTS, allot) and the pool a part's sample comes from (POOLS); the echo
follows the pack's own echo habits as the generator's did (score.of_song).
"""
from __future__ import annotations
import math
import random
from fractions import Fraction
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field

from .. import harmony, harness, rhythm, tables, vocab, writer
from ..writer import scale_index, scale_pitch
from .. import roles as R
from ..vocab import Span

from . import plan as plan_mod, render as render_mod   # noqa: E402  the package's other sections


# --- the measures: the same numbers over a written song read back and over a game's songs ---

SPAN = 32                             # bars the distinct figures are counted over (tools/slice1.py)


def tune_measures(song: rhythm.Song) -> dict:
    """The tune's numbers: chord tones on the beat, repeated notes, steps and leaps among its moves, distinct bar
    cells over SPAN bars, bars echoing an earlier bar, its range."""
    line = rhythm._line(song.notes.get(R.MELODY, []))
    if not line:
        return {}
    strong = [n for n in line if abs(n[0] - round(n[0])) < plan_mod.NEAR]
    on_chord = 0
    for n in strong:
        c = rhythm._chord_at(song.chords, n[0])
        if c is not None and c.root is not None and c.fit >= vocab.FIT:
            if round(n[2]) % 12 in {(c.root + i) % 12 for i in harmony.SHAPES.get(c.shape, harmony.SHAPES[""])}:
                on_chord += 1
    moves = [round(b[2] - a[2]) for a, b in zip(line, line[1:])]
    moving = [m for m in moves if m]
    cells = []
    for _, a, b, struck in rhythm.all_bars_of(song, R.MELODY):
        if struck:
            ms = [max(ns, key=lambda x: x[2])[2] for _, ns in struck]
            cells.append((tuple(float(p) for p, _ in struck), tuple(round(y - x) for x, y in zip(ms, ms[1:]))))
    heads = [h for i, w, h in rhythm.phrase_heads(song) if i is not None and h]
    theme_back = sum(1 for h in heads[1:] if h == heads[0]) / max(1, len(heads) - 1) if heads else 0.0
    live = [c for c in rhythm.melody_cells(song) if c]
    echoes_at = [i for i in range(len(live)) if live[i] in live[:i]]
    of_opening = sum(1 for i in echoes_at if live[i] in set(live[:4])) / max(1, len(echoes_at))
    return {"chord_tones": on_chord / max(1, len(strong)), "repeats": (len(moves) - len(moving)) / max(1, len(moves)),
            "steps": sum(1 for m in moving if abs(m) <= 2) / max(1, len(moving)), "leaps": sum(1 for m in moving if abs(m) >= 7) / max(1, len(moving)),
            "distinct": len(set(cells[:SPAN])), "echoes": sum(1 for i, c in enumerate(cells) if c in cells[:i]) / max(1, len(cells)),
            "range": max(n[2] for n in line) - min(n[2] for n in line),
            "theme_heads": theme_back, "theme_returns": int(theme_back > 0), "echoes_of_opening": of_opening}


def measures(song: rhythm.Song) -> dict:
    """A song's numbers, part by part: the share of bars it plays, strikes a bar, bars repeating the bar before,
    distinct bars over SPAN; the band, the form, the tune's (tune_measures)."""
    out = {"bars": len(song.bars), "parts": len(song.parts), "band": len(song.notes), "seconds": len(song.bars) * song.meter * 60.0 / song.bpm}
    for role in rhythm.PARTS:
        if role not in song.notes:
            continue
        bars = list(rhythm.all_bars_of(song, role))
        patterns = [rhythm.pattern(p for p, _ in struck) if struck else None for _, _, _, struck in bars]
        live = [p for p in patterns if p]
        if not live:
            continue
        out[role] = {"plays": len(live) / max(1, len(bars)), "strikes": statistics.mean(len(p.split()) for p in live),
                     "repeats": sum(1 for x, y in zip(live, live[1:]) if x == y) / max(1, len(live) - 1), "distinct": len(set(live[:SPAN]))}
    if R.MELODY in song.notes:
        out["tune"] = tune_measures(song)
    return out


def compose(models: dict, pack: dict, own: set, pack_name: str, seed: int, game: str = "", title: str | None = None,
            max_bars: int | None = None, loops: int = 2, reference=None, read: bool = True, fade: float = 2.0,
            min_bars: int | None = None, tail_bars: int = 0, themed: bool = False, band_returns: bool = False) -> dict:
    """One whole song: the plan, the parts written, the score (and {role: first voice}), the song read back and its
    measures; {"plan", "song", "written", "score", "first", "samples", "echo", "read", "measures"}."""
    p = plan_mod.plan(models, seed, game, title, max_bars, min_bars, themed=themed, band_returns=band_returns)
    kit = (pack.get("voices") or {}).get("drums") or {}
    song = plan_mod.song_of(p, kit)
    rng = random.Random(f"whole:{seed}:render")
    samples = render_mod.samples_for(p, pack, own, pack_name, rng, models)   # before the writing: every voice writes where the game plays its sample
    written = plan_mod.write(p, song, models, seed, reference)
    echo = render_mod.echo_of(pack.get("habits") or {}, p.bpm, rng)
    samples["floors"] = render_mod.floors_for(p, written, samples, models, pack_name, random.Random(f"whole:{seed}:floors"))   # by the written speed
    score, first = render_mod.score_of(p, written, samples, loops=loops, fade=fade, echo=echo, tail_bars=tail_bars, pack_name=pack_name)
    out = {"plan": p, "song": song, "written": written, "score": score, "first": first, "samples": samples, "echo": echo, "read": None, "measures": None}
    if read:
        once, _ = render_mod.score_of(p, written, samples, loops=1, fade=0.0, echo=echo, pack_name=pack_name)
        back = render_mod.read_back(once, p, first, samples)
        out["read"] = back
        out["measures"] = measures(back) if back is not None else None
        if out["measures"] is not None:                      # the reader's form, heard as a player hears it: with the loop
            twice, _ = render_mod.score_of(p, written, samples, loops=2, fade=0.0, echo=echo, pack_name=pack_name)
            looped = render_mod.read_back(twice, p, first, samples)
            out["measures"]["parts"] = len(looped.parts) if looped is not None else 0
            out["measures"]["loop_heard"] = int(looped is not None and looped.loop_bar is not None)
    return out
