"""A song written from a vocabulary (docs/IDIOM.md, phase 6): the whole-song
writer of the idiom on a shipped vocabulary's tables and one of the built-in
sound sets, the way `tools/whole.py` writes for the Song Checks. Classic
(`composer.py`) stays the generator without a vocabulary."""
from __future__ import annotations

import random

from . import names, vocabularies
from .packs import PACKS

SOUND_SETS = ("ffvi", "mana", "evermore", "megamanx")   # the built-in SNES sound sets a written song may play on
MAX_BARS = 48                                            # as the Song Checks: forms longer are drawn again
MIN_BARS = 12                                            # and shorter (a game's jingles stay in its tables)
TAIL_BARS = 4                                            # the loop's first bars once more after the form, fading
FADE = 3.0


def sound_set(pack: str | None, rng: random.Random) -> str:
    """The sound set a written song plays on: the one named, or one of the SNES sets drawn ("random", "none" and
    the chip palette have no SNES samples to write on)."""
    return pack if pack in SOUND_SETS else rng.choice(SOUND_SETS)


def compose_written(vocabulary: str, pack: str | None = None, seed: int | None = None, carry_theme: bool = False,
                    band_returns: bool = False) -> dict:
    """One song from a shipped vocabulary: {"score", "title", "seed", "sounds", "vocabulary", "info"}; the score renders
    through the SNES back end (`spc.convert.render`). A seed names one song; without one, a seed is drawn."""
    seed = random.randrange(1, 1_000_000) if seed is None else int(seed)
    rng = random.Random(f"written:{seed}")
    sounds = sound_set(pack, rng)
    models = vocabularies.load(vocabulary)
    label = vocabularies.label(vocabulary)
    from .translate import harmony, whole
    out = whole.compose(models, PACKS[sounds], set(), sounds, seed, game=label, title=f"{label} {seed}", max_bars=MAX_BARS,
                        min_bars=MIN_BARS, tail_bars=TAIL_BARS, themed=carry_theme, band_returns=band_returns, read=False, fade=FADE,
                        loops=1)
    p, score = out["plan"], out["score"]
    key = f"{harmony.NAMES[p.tonic]} {p.mode}"
    title = names.song_title(key, rng=rng, sound=sounds, tempo=_tempo_word(p.bpm))[:names.MAX_TITLE]
    score.title = title
    layout = [None] * sum(p.voices[r] for r in out["first"])     # the window's channel names: each voice's part ("layout:" as Classic writes it)
    for role, start in out["first"].items():
        for v in range(p.voices[role]):
            layout[start + v] = role if v == 0 else f"{role} {v + 1}"
    score.message = [f"{title} - {key} - {p.bpm:.0f} BPM - form {p.letters}",
                     "layout: " + ", ".join(x or "" for x in layout),
                     f"Written by bitComposer from {label}'s vocabulary on the {sounds} sounds (seed {seed}; docs/IDIOM.md, phase 6):",
                     "the band, the figures, the tune and its balance as the game's own songs have them, none of their notes."] + list(score.message or [])[3:]
    info = {"title": title, "key": key, "tempo": int(round(p.bpm)), "form": p.letters, "bars": p.bars, "band": list(p.band),
            "seconds": int(round(score.seconds)), "vocabulary": label, "sounds": sounds, "seed": seed,
            "carry_theme": carry_theme, "band_returns": band_returns}
    return {"score": score, "title": title, "seed": seed, "sounds": sounds, "vocabulary": vocabulary, "info": info, "plan": p}


def _tempo_word(bpm: float) -> str:
    return "slow" if bpm < 95 else "fast" if bpm >= 140 else "medium"
