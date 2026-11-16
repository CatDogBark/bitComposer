"""bitComposer's own voices: the bit set's sounds that stand for a game's samples.

A written song names its instruments by the sample ids of the game its vocabulary was counted from: the token's
instrument for a part, its kit, the ranges and speeds the tables hold are all said of those ids. bitComposer's first
own set (packs/bit.py) has other names, so on it none of those words had an answer and a handful of hand-set tables
stood in for them. A voice here is a sound of bitComposer's own, synthesised from a recipe (samples/recipe.py), that
says which game samples it stands for; registered in the bit set under those ids, it is what the writer finds when a
song asks for one, and the counted words answer for it as they do on the game's own samples. Its own name is for the
people working on the sounds (the data, docs/VOICES.md); a song's module names its samples as every written song does. No game audio is held or
shipped: a recipe is a description (bit_voices_data.py, docs/VOICES.md).

`use(game)` is what a written song takes: the set's table for the writer (the pools each part draws from, the kit,
the habits) and the sample ids the set answers for. The voices are synthesised and registered the first time they
are asked for, once a process, and the writer is told their loudness each time (another sound set's may have been
in its place since).

One game today (Final Fantasy VI, the shipped vocabulary's). A voice may stand for samples of more than one game;
a game's block in the data says which of its samples each part draws from."""
from __future__ import annotations

from .. import samples as smp
from ..samples import recipe
from . import bit_voices_data as data

SET = "bit"                           # the sound set the voices belong to: a voice is registered as bit_<sample id>
DEFAULT_GAME = "ffvi"
_built: dict = {}                     # game -> {"table", "own", "loudness", "strikes"}, once synthesised and registered


def names() -> list:
    """The voices' names."""
    return list(data.VOICES)


def stands(game: str = DEFAULT_GAME) -> dict:
    """{a game's sample id: the name of the voice that stands for it}."""
    out = {}
    for name, v in data.VOICES.items():
        for sid in v["stands_for"].get(game, ()):
            if sid in out:
                raise ValueError(f"{sid}: {out[sid]} and {name} both stand for it")
            out[sid] = name
    return out


def rendered(game: str = DEFAULT_GAME) -> dict:
    """Each of the game's samples as its voice sounds: {sample id: (16-bit mono data, frames, rate, (loop start, loop end)
    or None, the MIDI note it sounds at that rate or None)}, synthesised from the recipes."""
    by = stands(game)
    out = {}
    for sid in data.GAMES[game]["samples"]:
        v = data.VOICES[by[sid]]
        out[sid] = recipe.voice(v["recipe"], v["seed"])
    return out


def pack_data(game: str = DEFAULT_GAME, sounds: dict | None = None) -> dict:
    """The set for one game in a pack file's shape (packfile.parse reads it): the game's samples by id with the facts
    they are played by, the pools and the kit by id, the habits of the game's scores. A tone's pitch and loop are its
    recipe's (`sounds`: rendered(game), made here when not given); a kit voice the game also plays as a line takes them
    as its tonal reading."""
    g = data.GAMES[game]
    sounds = sounds if sounds is not None else rendered(game)
    by = stands(game)
    samples = {}
    for sid, spec in g["samples"].items():
        spec = dict(spec, file=f"{sid}.wav")
        _, _, _, loop, note = sounds[sid]
        if data.VOICES[by[sid]]["recipe"]["kind"] == "tone":
            fact = {"note": round(note, 2), "loop": list(loop)}
            if spec.get("percussion"):
                spec["tonal"] = dict(spec.get("tonal") or {}, **fact)
            else:
                spec.update(fact)
        samples[sid] = spec
    return {"bitcomposer_pack": 1, "name": SET, "label": "bitComposer", "palette": "snes",
            "voices": dict(g["pools"], drums=dict(g["kit"])), "habits": dict(g["habits"]), "samples": samples}


def audio(game: str = DEFAULT_GAME, sounds: dict | None = None) -> dict:
    """The game's samples as pack-file audio, {"<id>.wav": (16-bit mono data, frames, rate)}, synthesised."""
    sounds = sounds if sounds is not None else rendered(game)
    return {f"{sid}.wav": (pcm, frames, rate) for sid, (pcm, frames, rate, _, _) in sounds.items()}


def _build(game: str) -> dict:
    import array
    from ..translate.rhythm import readings
    from . import packfile
    made = rendered(game)
    sounds = audio(game, made)
    shaped = pack_data(game, made)
    pack, voices = packfile.parse(shaped, None, source="bitComposer's own voices", audio=sounds)
    for key, v in voices.items():
        smp.register_sample_voice(f"{SET}_{key}", v["data"], v["length"], v["meta"], v["volume"], release=v["release"], percussion=v["percussion"])
    for key, v in voices.items():                           # a kit voice's tonal reading, registered beside it (as a pack file's is)
        if v.get("view_of"):
            smp.TONAL_VIEWS[f"{SET}_{v['view_of']}"] = f"{SET}_{key}"
    loud, strikes = {}, {}
    for sid, spec in shaped["samples"].items():
        pcm, frames, rate = sounds[spec["file"]]
        got = readings.sample_loudness(array.array("h", pcm), rate, spec)
        if got is not None:
            loud[sid], strikes[sid] = got
    return {"table": pack["table"], "own": set(shaped["samples"]), "loudness": loud, "strikes": strikes}


def use(game: str = DEFAULT_GAME) -> tuple:
    """(the set's table for the writer, the sample ids it answers for): the voices registered if they were not yet,
    and their loudness told to the writer."""
    from ..translate import rhythm
    if game not in _built:
        _built[game] = _build(game)
    b = _built[game]
    rhythm.set_loudness(dict(b["loudness"]), dict(b["strikes"]))
    return b["table"], set(b["own"])
