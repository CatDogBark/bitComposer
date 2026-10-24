"""
Pack files: a style pack as data, so a pack can be added without touching
the code (and, later, made by the SPC importer; see docs/SPC-IMPORT.md).

A pack file is JSON, which the standard library reads on every Python the
package supports (tomllib needs 3.11). It holds the table a built-in pack
module keeps as PACK (palette, label, voices per role, habits, trims) and
the pack's own voices as WAV files beside it. docs/PACKS.md is the format.
Data only, never code: a pack someone sends cannot run anything.

load_pack_file() checks the file, registers its voices with the sample
registry and the pack in PACKS, and returns the pack's name; the composer
then takes it like a built-in pack. It is not added to PACK_NAMES, so
SOUND's random draw never picks it (decided 2026-10-18).

The built-in packs stay Python: their tables carry the comments that record
where each number came from, which JSON cannot. to_data() writes any pack in
this format, and a test reads every built-in pack back through it, so the
format can say everything the built-in packs say.
"""
import array
import json
import math
import re
import sys
import wave
from pathlib import Path

from .. import arp, bass, echo, samples as smp, structure
from ..drums import KIT_NOTE
from ..instruments import PALETTES
from ..mix import CHANNEL_ROLES
from . import PACKS, PACK_NAMES

FORMAT = 1                        # the format a pack without tables is written in
TABLED = 2                        # the format that carries the tables (translate.packtables) beside the voices
FORMATS = (FORMAT, TABLED)
KEY = "bitcomposer_pack"          # the key that marks a file as one, holding FORMAT or TABLED
TABLES = "tables"                 # the format 2 field: {"source": {...}, "tables": {name: {"what", "shape", "mixture", "units", "songs", "model"}}}

# The habits a pack may set: weighted draws over these names (the plain
# pools and the names only packs use), chances from 0 to 1, switches, and a
# few with shapes of their own (see _habit).
WEIGHTED = {
    "tempo": ("slow", "medium", "fast"),
    "energy": ("chill", "normal", "intense"),
    "scale_family": ("minor", "major", "pentatonic"),
    "harmony_voicing": ("full", "thin"),
    "harmony_mode": ("stabs", "sustain", "rhythmic", "ostinato", "pulse",
                     "chug_sync", "chug_offbeat", "chug_gallop"),
    "bass_weight": ("heavy", "medium", "light"),
    "bass_style": ("steady", "walking", "octave", "driving", "drone", "riff"),
    "drum_density": ("sparse", "normal", "busy"),
    "drum_swing": ("off", "light", "heavy"),
    "form": tuple(structure.FORMS),
    "intro": tuple(structure.INTROS),
    "arp_figures": tuple(arp.FIGURES),
    "riffs": tuple(bass.RIFFS),
    "echo_wet": tuple(echo.ECHO_WET_WEIGHTS),
    "echo_delay": tuple(echo.ECHO_DELAYS),
    "echo_stereo": tuple(echo.ECHO_STEREO_WEIGHTS),
}
CHANCES = ("echo", "counter_line", "drumless", "crash_chance")
FLAGS = ("section_rolls", "fill_crash")
OTHER_HABITS = ("hat_stroke", "lead_shift", "echo_feedback", "power_chords", "lead_ranges")

POOLS = ("lead", "alt_lead", "harmony", "counter", "arp", "bass_heavy", "bass_medium", "bass_light")
KIT = ("kick", "snare", "hihat", "tom", "crash", "open_hihat", "rim")
RESERVED = {"random", "none", *PALETTES}

MAX_FRAMES = 2_000_000             # 45 s at 44.1 kHz: the loudness pass holds a sample as a list
_NAME = re.compile(r"^[a-z][a-z0-9_]{0,23}$")

# The voices the package itself has (palettes and built-in packs), the only
# names a pack file may borrow; its own are its "samples".
BUILTIN_VOICES = frozenset(smp.INSTRUMENT_PRESETS)

_loaded: dict[str, list[str]] = {}          # pack name -> the voices it registered
_seen: dict[str, tuple] = {}                # pack name -> (path, mtime, size) last loaded


class PackError(ValueError):
    """A pack file that cannot be used, with where and why."""


def load_pack_file(path) -> str:
    """Check a pack file, register its voices and the pack, return its name.
    Loading the same unchanged file again is free."""
    path = Path(path).expanduser().resolve()
    try:
        st = path.stat()
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise PackError(f"{path}: cannot read it ({e.strerror or e})") from None
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise PackError(f"{path}: not a JSON file ({e})") from None
    name = data.get("name") if isinstance(data, dict) else None
    stamp = (str(path), st.st_mtime_ns, st.st_size)
    if name in _loaded and _seen.get(name) == stamp:
        return name
    pack, voices = parse(data, path.parent, source=str(path))
    name = check_name(pack["name"], source=str(path))
    unload(name)
    registered = []
    for key, v in voices.items():
        voice = f"{name}_{key}"
        smp.register_sample_voice(voice, v["data"], v["length"], v["meta"], v["volume"],
                                  release=v["release"], percussion=v["percussion"])
        registered.append(voice)
    PACKS[name] = pack["table"]
    _loaded[name], _seen[name] = registered, stamp
    return name


def unload(name: str) -> None:
    """Take a pack file's pack and voices out again (built-in packs stay)."""
    for voice in _loaded.pop(name, []):
        smp.unregister_voice(voice)
    _seen.pop(name, None)
    if name not in PACK_NAMES:
        PACKS.pop(name, None)


def check_name(name: str, source: str = "pack") -> str:
    if name in PACK_NAMES or name in RESERVED:
        raise PackError(f"{source}: name: {name!r} is a built-in sound; give the pack its own name")
    return name


def parse(data, base: Path, source: str = "pack") -> tuple[dict, dict]:
    """Check pack file data. Returns ({"name", "table"}, the pack's own
    voices read from their files), registering nothing. table is what PACKS
    holds for a built-in pack."""
    def fail(where, problem):
        raise PackError(f"{source}: {where}: {problem}")

    if not isinstance(data, dict):
        fail("file", "a pack file is one JSON object")
    if data.get(KEY) not in FORMATS:
        fail(KEY, f"must be {FORMAT} or {TABLED} (this is how a file says it is a bitComposer pack, "
                  f"and which version of the format)")
    known = {KEY, "name", "label", "palette", "voices", "habits", "trims", "samples"}
    if data[KEY] == TABLED:
        known.add(TABLES)
    for k in data:
        if k not in known:
            fail(k, f"not a pack field (fields: {', '.join(sorted(known))})")
    name = data.get("name")
    if not isinstance(name, str) or not _NAME.match(name):
        fail("name", "lower-case letters, digits and _, starting with a letter, at most 24 characters")
    palette = data.get("palette")
    if palette not in PALETTES:
        fail("palette", f"one of {', '.join(PALETTES)}")
    label = data.get("label", name)
    if not isinstance(label, str) or not label.strip():
        fail("label", "a short name to show for the pack")

    samples = data.get("samples", {})
    if not isinstance(samples, dict):
        fail("samples", "an object of the pack's own voices, by name")
    kit_voices = set()
    raw_voices = data.get("voices", {})
    if isinstance(raw_voices, dict) and isinstance(raw_voices.get("drums"), dict):
        kit_voices = {v for v in raw_voices["drums"].values() if isinstance(v, str)}
    own = {}
    for key, spec in samples.items():
        if not isinstance(key, str) or not _NAME.match(key):
            fail(f"samples.{key}", "voice names are lower-case letters, digits and _")
        if key in BUILTIN_VOICES:
            fail(f"samples.{key}", "a built-in voice has this name; give the pack's voice its own")
        own[key] = _sample(spec, base, f"samples.{key}", key in kit_voices, fail)

    def voice_name(v, where):
        if v in own:
            return f"{name}_{v}"
        if v in BUILTIN_VOICES:
            return v
        fail(where, f"{v!r} is neither one of the pack's samples nor a built-in voice")

    voices = {}
    if not isinstance(raw_voices, dict):
        fail("voices", "an object of roles")
    for role, pool in raw_voices.items():
        where = f"voices.{role}"
        if role in POOLS:
            if not isinstance(pool, list) or not pool or not all(isinstance(v, str) for v in pool):
                fail(where, "a list of voice names (repeat a name to draw it more often)")
            voices[role] = [voice_name(v, f"{where}[{i}]") for i, v in enumerate(pool)]
        elif role == "bass_hi":
            if not isinstance(pool, str):
                fail(where, "one voice name: the bass line's upper-register sample")
            voices[role] = voice_name(pool, where)
        elif role == "drums":
            if not isinstance(pool, dict):
                fail(where, f"an object of kit pieces: {', '.join(KIT)}")
            kit = dict(PALETTES[palette]["drums"] or {})
            for piece, v in pool.items():
                if piece not in KIT:
                    fail(f"{where}.{piece}", f"not a kit piece ({', '.join(KIT)})")
                if not isinstance(v, str):
                    fail(f"{where}.{piece}", "a voice name")
                kit[piece] = voice_name(v, f"{where}.{piece}")
            missing = [p for p in KIT if p not in kit]
            if missing:
                fail(where, f"the {palette} palette has no kit to fill in from; give {', '.join(missing)}")
            voices[role] = kit
        else:
            fail(where, f"not a role ({', '.join(POOLS + ('bass_hi', 'drums'))})")
    if "alt_lead" not in voices:
        # The composer swaps the lead for the bridge from this pool.
        voices["alt_lead"] = list(voices.get("lead") or PALETTES[palette]["alt_lead"])

    habits_in = data.get("habits", {})
    if not isinstance(habits_in, dict):
        fail("habits", "an object of habits")
    habits = {h: _habit(h, v, f"habits.{h}", voice_name, fail) for h, v in habits_in.items()}

    trims_in = data.get("trims", {})
    if not isinstance(trims_in, dict):
        fail("trims", "an object of channel roles and their volumes")
    trims = {}
    for role, vol in trims_in.items():
        if role not in CHANNEL_ROLES:
            fail(f"trims.{role}", f"not a channel role ({', '.join(sorted(set(CHANNEL_ROLES)))})")
        if not _is_int(vol) or not 0 <= vol <= 64:
            fail(f"trims.{role}", "a channel volume from 0 to 64")
        trims[role] = vol

    table = {"palette": palette, "label": label, "voices": voices, "habits": habits, "trims": trims}
    if data[KEY] == TABLED:
        table[TABLES] = _tables(data.get(TABLES), fail)
    return {"name": name, "table": table}, own


def _tables(t, fail) -> dict:
    """The format 2 tables, checked for shape only (their contents are read
    by translate.packtables when a writer draws from them)."""
    where = TABLES
    if not isinstance(t, dict) or not isinstance(t.get("source"), dict) or not isinstance(t.get("tables"), dict):
        fail(where, "an object with \"source\" (the game, its songs) and \"tables\" (the tables by name)")
    for name, entry in t["tables"].items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            fail(f"{where}.tables.{name}", "a table is an object")
        for k in ("what", "shape", "mixture", "units", "songs", "model"):
            if k not in entry:
                fail(f"{where}.tables.{name}", f"missing {k}")
        model = entry["model"]
        inner = model.get("table") if entry["mixture"] else model
        if not isinstance(inner, dict) or not isinstance(inner.get("contexts"), list) or "vocabulary" not in inner:
            fail(f"{where}.tables.{name}.model", "a table as translate.tables writes it (conditionings, vocabulary, contexts)")
    return t


def _habit(h, v, where, voice_name, fail):
    if h in WEIGHTED:
        if not isinstance(v, dict) or not v:
            fail(where, f"weights by name, e.g. {{\"{WEIGHTED[h][0]}\": 2}}")
        for k, w in v.items():
            if k not in WEIGHTED[h]:
                fail(f"{where}.{k}", f"not one of {', '.join(WEIGHTED[h])}")
            if not _is_number(w) or w < 0:
                fail(f"{where}.{k}", "a weight of 0 or more")
        return dict(v)
    if h in CHANCES:
        if not _is_number(v) or not 0 <= v <= 1:
            fail(where, "a chance from 0 to 1")
        return v
    if h in FLAGS:
        if not isinstance(v, bool):
            fail(where, "true or false")
        return v
    if h == "hat_stroke":
        if not _is_number(v) or not 0 <= v <= 1:
            fail(where, "the level of every second hi-hat hit (the back stroke), from 0 to 1; 1 plays them alike")
        return v
    if h == "lead_shift":
        if not _is_int(v) or not -24 <= v <= 24:
            fail(where, "semitones from -24 to 24")
        return v
    if h == "echo_feedback":
        if (not isinstance(v, list) or len(v) != 2 or not all(_is_number(x) for x in v)
                or not 0 <= v[0] <= v[1] < 1):
            fail(where, "[low, high], each repeat relative to the last, from 0 to under 1")
        return tuple(v)
    if h == "power_chords":
        if isinstance(v, bool):
            return v
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            fail(where, "true, false, or a list of the harmony voices that play fifths")
        return [voice_name(x, f"{where}[{i}]") for i, x in enumerate(v)]
    if h == "lead_ranges":
        if not isinstance(v, dict):
            fail(where, "lead voices and their [lowest, highest] MIDI notes")
        out = {}
        for k, r in v.items():
            if not isinstance(r, list) or len(r) != 2 or not all(_is_int(x) for x in r) or not 0 <= r[0] < r[1] <= 127:
                fail(f"{where}.{k}", "[lowest, highest] MIDI notes")
            out[voice_name(k, f"{where}.{k}")] = tuple(r)
        return out
    every = sorted([*WEIGHTED, *CHANCES, *FLAGS, *OTHER_HABITS])
    fail(where, f"not a habit ({', '.join(every)})")


def _sample(spec, base: Path, where: str, in_kit: bool, fail) -> dict:
    if not isinstance(spec, dict):
        fail(where, "an object: file, note (or hz), and optionally loop, release, percussion, volume, envelope")
    allowed = {"file", "note", "hz", "loop", "release", "percussion", "volume", "envelope"}
    for k in spec:
        if k not in allowed:
            fail(f"{where}.{k}", f"not a sample field ({', '.join(sorted(allowed))})")
    file = spec.get("file")
    if not isinstance(file, str) or not file.lower().endswith(".wav"):
        fail(f"{where}.file", "a .wav file, named relative to the pack file")
    data, frames, rate = read_wav(base / file, f"{where}.file", fail)
    percussion = spec.get("percussion", in_kit)
    if not isinstance(percussion, bool):
        fail(f"{where}.percussion", "true for a kit voice (left at its level), false for a tonal one")
    if "note" in spec and "hz" in spec:
        fail(where, "give note or hz, not both")
    if "hz" in spec:
        hz = spec["hz"]
        if not _is_number(hz) or not 8 <= hz <= 20000:
            fail(f"{where}.hz", "the recording's pitch in Hz")
        note = 69 + 12 * math.log2(hz / 440)
    elif "note" in spec:
        note = spec["note"]
        if not _is_number(note) or not 0 <= note <= 127:
            fail(f"{where}.note", "the MIDI note the recording sounds at (60 is middle C; fractions are cents)")
    elif percussion:
        note = KIT_NOTE            # the kit plays every piece at this note: as recorded
    else:
        fail(where, "a tonal voice needs its pitch: note (MIDI) or hz")
    # IT plays a sample at its C5Speed on C-5, which this package writes as
    # MIDI 60 (middle C), so a recording that sounds `note` at its own rate
    # plays in tune at rate * 2^((60 - note) / 12).
    c5 = round(rate * 2 ** ((60 - note) / 12))
    if not 1000 <= c5 <= 9_999_999:
        fail(where, f"that pitch puts the playback rate at {c5} Hz, out of range")
    loop = spec.get("loop")
    meta = {"rate": c5, "loop": False, "loop_start": 0, "loop_end": frames}
    if loop is not None:
        if not isinstance(loop, list) or len(loop) != 2 or not all(_is_int(x) for x in loop):
            fail(f"{where}.loop", "[start, end] in sample frames")
        start, end = loop
        if not 0 <= start < end <= frames:
            fail(f"{where}.loop", f"start and end inside the sample's {frames} frames, start first")
        meta.update(loop=True, loop_start=start, loop_end=end)
    envelope = spec.get("envelope")
    if envelope is not None:                                # the SNES chip envelope the game plays the sample with (format 2 packs)
        ok = isinstance(envelope, dict) and (("adsr" in envelope) != ("gain" in envelope)) and set(envelope) <= {"adsr", "gain"}
        if ok and "adsr" in envelope:
            ok = isinstance(envelope["adsr"], list) and len(envelope["adsr"]) == 2 and all(_is_int(x) and 0 <= x <= 255 for x in envelope["adsr"])
        if ok and "gain" in envelope:
            ok = _is_int(envelope["gain"]) and 0 <= envelope["gain"] <= 255
        if not ok:
            fail(f"{where}.envelope", 'the SNES chip envelope the game plays the sample with: {"adsr": [ADSR1, ADSR2]} or {"gain": GAIN}, bytes 0 to 255')
        meta["envelope"] = envelope
    release = spec.get("release")
    if release is not None:
        if release not in smp.RELEASE:
            fail(f"{where}.release", f"one of {', '.join(smp.RELEASE)}")
        if loop is None:
            fail(f"{where}.release", "a release fades a held note out of its loop; give the voice a loop")
    volume = spec.get("volume", 60)
    if not _is_int(volume) or not 1 <= volume <= 64:
        fail(f"{where}.volume", "the default note volume, from 1 to 64")
    return {"data": data, "length": frames, "meta": meta, "volume": volume,
            "release": release, "percussion": percussion}


def read_wav(path: Path, where: str = "file", fail=None) -> tuple[bytes, int, int]:
    """A PCM WAV as 16-bit mono little-endian data: (data, frames, rate).
    8, 16, 24 and 32-bit integer samples; channels are averaged."""
    def bad(problem):
        if fail:
            fail(where, problem)
        raise PackError(f"{path}: {problem}")
    try:
        with wave.open(str(path), "rb") as w:
            ch, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(frames)
    except FileNotFoundError:
        bad(f"no such file: {path}")
    except (wave.Error, EOFError, OSError) as e:
        bad(f"{path.name} is not a PCM WAV file the standard library reads ({e})")
    if frames < 16:
        bad(f"{path.name} is too short to be a voice ({frames} frames)")
    if frames > MAX_FRAMES:
        bad(f"{path.name} is {frames} frames; a voice is at most {MAX_FRAMES}")
    if width not in (1, 2, 3, 4):
        bad(f"{path.name}: {8 * width}-bit samples are not supported")
    if width == 2:
        # The usual case, in bulk: WAV data is little-endian like ours.
        pcm = array.array("h", raw[:2 * ch * frames])
        if sys.byteorder != "little":
            pcm.byteswap()
        if ch > 1:
            pcm = array.array("h", (max(-32768, min(32767, round(sum(pcm[i * ch:(i + 1) * ch]) / ch)))
                                    for i in range(frames)))
        if sys.byteorder != "little":
            pcm.byteswap()
        return pcm.tobytes(), frames, rate
    step = width * ch
    out = bytearray(2 * frames)
    for i in range(frames):
        total = 0
        for c in range(ch):
            o = i * step + c * width
            if width == 1:
                v = (raw[o] - 128) << 8
            else:
                v = int.from_bytes(raw[o:o + width], "little", signed=True) >> (8 * (width - 2))
            total += v
        v = max(-32768, min(32767, round(total / ch)))
        out[2 * i:2 * i + 2] = v.to_bytes(2, "little", signed=True)
    return bytes(out), frames, rate


def to_data(name: str) -> dict:
    """A registered pack as pack file data (without sample files: a built-in
    pack's voices are code, named here as built-in voices)."""
    t = PACKS[name]

    def plain(v):
        if isinstance(v, (tuple, list)):
            return [plain(x) for x in v]
        if isinstance(v, dict):
            return {k: plain(x) for k, x in v.items()}
        return v
    out = {KEY: FORMAT, "name": name, "label": t["label"], "palette": t["palette"],
           "voices": plain(t["voices"]), "habits": plain(t["habits"])}
    if t.get("trims"):
        out["trims"] = plain(t["trims"])
    return out


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)
