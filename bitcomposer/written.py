"""A song written from a vocabulary (docs/IDIOM.md, phase 6): the whole-song
writer of the idiom on a shipped vocabulary's tables and one of the built-in
sound sets, the way `tools/whole.py` writes for the Song Checks. Classic
(`composer.py`) stays the generator without a vocabulary."""
from __future__ import annotations

import random

from . import names, vocabularies
from .packs import PACKS

SOUND_SETS = ("bit", "ffvi", "mana", "evermore", "megamanx")   # the built-in sound sets a written song may play on
DEFAULT_SOUNDS = "bit"                                  # bitComposer's own (packs/bit.py): what it plays on unless a set or a game is named
MAX_BARS = 48                                            # as the Song Checks: forms longer are drawn again
MIN_BARS = 12                                            # and shorter (a game's jingles stay in its tables)
TAIL_BARS = 4                                            # the loop's first bars once more after the form, fading
FADE = 3.0


def sound_set(pack: str | None, rng: random.Random) -> str:
    """The sound set a written song plays on: the one named, else bitComposer's own ("random", "none" and the chip
    palette have no SNES samples to write on; the four styled sets are Classic's, and a written song takes one only by
    name). `rng` is kept for the signature's sake: the default is not drawn."""
    return pack if pack in SOUND_SETS else DEFAULT_SOUNDS


def pack_sounds(pack_file) -> tuple[str, set]:
    """An imported pack's samples as the sound set: its voices registered, its samples' loudness known to the writer;
    (the pack's name, its own sample ids)."""
    import json
    from pathlib import Path
    from .packs.packfile import load_pack_file
    from .translate import rhythm
    name = load_pack_file(str(pack_file))
    data = json.loads(Path(pack_file).read_text(encoding="utf-8"))
    rhythm.set_loudness(rhythm.load_loudness(Path(pack_file).parent))
    return name, set(data.get("samples") or {})


def compose_written(vocabulary: str = vocabularies.DEFAULT, pack: str | None = None, seed: int | None = None, carry_theme: bool = False,
                    band_returns: bool = False, pack_file=None) -> dict:
    """One song from a vocabulary (shipped, the library's, or an imported pack's): {"score", "title", "seed", "sounds",
    "vocabulary", "info", "plan"}; the score renders through the SNES back end (`spc.convert.render`). The sounds: the
    built-in set `pack` names, the imported pack `pack_file` names, else an imported pack's own samples for its own
    vocabulary, else one of the SNES sets the seed draws. A seed names one song; without one, a seed is drawn."""
    seed = random.randrange(1, 1_000_000) if seed is None else int(seed)
    rng = random.Random(f"written:{seed}")
    own = set()
    if pack_file is None and pack not in SOUND_SETS and vocabularies.pack_name(vocabulary):
        from .packs.library import pack_file as library_pack_file
        pack_file = library_pack_file(vocabularies.pack_name(vocabulary))
    if pack_file is not None:
        sounds, own = pack_sounds(pack_file)
    else:
        sounds = sound_set(pack, rng)
    models = vocabularies.load(vocabulary)
    label = vocabularies.label(vocabulary)
    from .translate import harmony, whole
    out = whole.compose(models, PACKS[sounds], own, sounds, seed, game=label, title=f"{label} {seed}", max_bars=MAX_BARS,
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
    if vocabulary == vocabularies.DEFAULT:
        source = "Written by bitComposer"
    elif vocabulary == vocabularies.LIBRARY:
        source = f"Written by bitComposer from your library ({vocabularies.songs(vocabulary)} songs)"
    else:
        source = f"Written by bitComposer from {label}'s songs"
    score.message = [f"{title} - {key} - {p.bpm:.0f} BPM - form {p.letters}",
                     "layout: " + ", ".join(x or "" for x in layout),
                     f"{source} on {'its own sounds' if sounds == DEFAULT_SOUNDS else 'the ' + sounds + ' sounds'} (seed {seed}; docs/IDIOM.md): the band, the figures, the tune and its",
                     "balance drawn from a vocabulary of counted habits, none of any song's notes."] + list(score.message or [])[3:]
    info = {"title": title, "key": key, "tempo": int(round(p.bpm)), "form": p.letters, "bars": p.bars, "band": list(p.band),
            "seconds": int(round(score.seconds)), "vocabulary": label, "sounds": sounds, "seed": seed,
            "carry_theme": carry_theme, "band_returns": band_returns}
    return {"score": score, "title": title, "seed": seed, "sounds": sounds, "vocabulary": vocabulary, "info": info, "plan": p,
            "written": out["written"]}


def _tempo_word(bpm: float) -> str:
    return "slow" if bpm < 95 else "fast" if bpm >= 140 else "medium"
