"""A thin pack from a game's songs (the translator's stage 2, docs/TRANSLATOR.md):
the game's own samples as the generator's voices, and only the habits its
readings give directly, in today's pack format (docs/PACKS.md).

- Voices. Each part the readings found (the melody, harmony and
  accompaniment, the counter-line, the arp, the bass, the drums) takes the
  samples the game plays it with most, weighted by how many notes each
  plays in it, over every song. A sample is written once, as WAV, as the
  SNES chip's interpolation colours it, its loop kept, its pitch from its
  measured tuning (a drum at the pitch the game plays it most). A held
  voice's release is its part's (a lead's, the strings' under harmony,
  keys' for an arp, the bass's).
- The kit. Drum samples go to kit pieces by the drum namer's names
  (translate/drums.py, on the sample as the game plays it): each piece the
  game's most-played sample so named (kick, snare, hat, tom, cymbal), a
  second hat the open hat, the most-played "other" sound the rim. Without
  names, by what they sound like: the dullest the kick, the brightest
  short one the hi-hat, the brightest long one the crash, one between them
  the snare. Pieces left out keep the SNES palette's. (By sound alone,
  FFVI's kit had held a hat in the snare's slot and no cymbal: its cymbal,
  in 22 of its 67 songs, is struck too rarely to rank among the six
  most-played drums the brightness kit chose from; 2026-10-23.)
- Habits. Tempo (slow, medium, fast, as the generator draws them) from
  each song's beat; the scale family from each song's key; how many songs
  have no drums; echo from what the driver set: how many songs have it, its delay in the generator's
  terms at each song's tempo, its feedback, how wet (the echo's volume
  over the main volume).

Nothing more: no habit the readings do not give straight, no classifier
for categories stage 4's vocabulary is to replace."""
import json
import math
import re
import statistics
import tempfile
import wave
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import archives, roles as R

RATE = 32000                         # a sample plays at its own rate at pitch 0x1000
VOICES = 64                          # the most samples a part draws from: every tonal sample the part's songs play (round 51,
                                      # 2026-10-28; six had left FFVI's parts 17 of their line instruments, 0.12 to 0.14 of the
                                      # songs a part, which the part_samples word then could not draw)
SHARE = 0.0                          # a sample playing less of a part's notes than this is left out (none: a part's rarest
                                      # instrument is still the one a song of the game gave it)
REPEATS = 4                          # a pool repeats its most used sample this many times, the rest by their share
LONG = 0.5                           # seconds: a drum ringing this long is a cymbal
KIT_HITS = 30                        # drum-role hits a named drum sample needs to go into the pack beyond the kit's slots (round 63)
WHY = "translator.json"              # beside pack.json: the songs read, and why each sample is where it is

# the generator's pools each part fills
POOLS = {R.MELODY: ("lead",), R.HARMONY: ("harmony",), R.ACCOMP: ("harmony",), R.COUNTER: ("counter",),
         R.ARP: ("arp",), R.BASS: ("bass_heavy", "bass_medium", "bass_light")}
RELEASE = {"lead": "lead", "harmony": "strings", "counter": "lead", "arp": "keys",
           "bass_heavy": "bass", "bass_medium": "bass", "bass_light": "bass"}
# the generator's tempos (composer: slow 80-110, medium 110-140, fast 140-180) and echo delays in rows
TEMPOS = ((110, "slow"), (140, "medium"), (1e9, "fast"))
DELAYS = {"slap": 0.5, "row": 1, "eighth": 2, "dotted": 3, "quarter": 4}
ROWS_PER_BEAT = 4
WET = ((0.35, "light"), (0.7, "normal"), (1e9, "wet"))


@dataclass
class Gathered:
    """What a game's songs give a pack."""
    game: str = ""
    songs: int = 0
    uses: dict = field(default_factory=lambda: defaultdict(Counter))       # part -> sample key -> notes
    songs_in: dict = field(default_factory=lambda: defaultdict(Counter))   # part -> sample key -> songs
    where: dict = field(default_factory=dict)                             # sample key -> (snapshot path, (start, loop))
    f0: dict = field(default_factory=dict)                                # sample key -> Hz at its own rate
    pitches: dict = field(default_factory=lambda: defaultdict(Counter))   # sample key -> pitch registers played
    tempos: Counter = field(default_factory=Counter)
    modes: Counter = field(default_factory=Counter)
    echo: list = field(default_factory=list)                              # (on, delay rows, feedback, wet) a song
    drumless: int = 0                                                     # songs with no drum voice
    names: dict = field(default_factory=dict)                             # drum sample key -> the drum namer's name (kit_by_name)
    held: dict = field(default_factory=lambda: defaultdict(list))         # drum sample key -> seconds the game holds each hit
    envelopes: dict = field(default_factory=lambda: defaultdict(Counter))  # sample key -> the envelope at key-on, ("adsr", ADSR1, ADSR2) or ("gain", GAIN) -> notes
    other: Counter = field(default_factory=Counter)                       # sample key -> drum-role notes the namer called "other" in their song


def gather(readings, snaps) -> Gathered:
    """Count a game's readings (from reading.read) and their snapshots."""
    g = Gathered()
    for r, snap in zip(readings, snaps):
        g.songs += 1
        g.game = g.game or r.game
        part = {x.voice: x.role for x in r.roles}
        heard = set()
        for p in r.song.notes:
            role = part.get(p.voice)
            if role is None or p.sample is None or role == R.DOUBLE:
                continue
            k = p.sample.key
            g.uses[role][k] += 1
            heard.add((role, k))
            if p.note is not None:
                g.envelopes[k][("adsr", p.note.adsr[0], p.note.adsr[1]) if p.note.adsr[0] & 0x80 else ("gain", p.note.gain)] += 1
            if role == R.DRUMS and p.sample.piece == "other":
                g.other[k] += 1
            if role == R.DRUMS and p.length is not None:
                g.held[k].append(p.length)
            g.where.setdefault(k, (snap.source, p.sample.addr))
            if p.sample.f0:
                g.f0.setdefault(k, p.sample.f0)
            if p.note is not None and p.note.pitch:
                g.pitches[k][p.note.pitch] += 1
        if r.grid:
            g.tempos[next(name for top, name in TEMPOS if r.grid.bpm < top)] += 1
        if r.key:
            g.modes[r.key[1]] += 1
        g.drumless += not any(x.role == R.DRUMS for x in r.roles)
        for role, k in heard:
            g.songs_in[role][k] += 1
        e = snap.echo
        main = max(abs(x) for x in snap.main_volume) or 1.0
        on = bool(e.voices) and e.writes and e.delay_ms > 0 and max(abs(x) for x in e.volume) > 0
        rows = e.delay_ms / 1000 / (60 / r.grid.bpm) * ROWS_PER_BEAT if (on and r.grid) else None
        g.echo.append((on, rows, abs(e.feedback), max(abs(x) for x in e.volume) / main))
    return g


def pools(g: Gathered) -> dict:
    """Each pool's samples, most used first, a name repeated by its share."""
    out = {}
    for role, names in POOLS.items():
        counts = g.uses.get(role)
        if not counts:
            continue
        for name in names:
            merged = out.setdefault(name, Counter())
            merged.update(counts)
    # a sample the game plays mostly as a drum is a drum, not a tonal voice, where a reading called it
    # otherwise (Terra's hi-hat, played at a few pitches, read as an arp in a song or two)
    drum = g.uses.get(R.DRUMS, Counter())
    tonal = Counter()
    for role in POOLS:
        tonal.update(g.uses.get(role, Counter()))
    chosen = {}
    for name, counts in out.items():
        counts = Counter({k: n for k, n in counts.items() if drum.get(k, 0) < tonal[k]})
        total = sum(counts.values())
        top = [(k, n) for k, n in counts.most_common(VOICES) if n >= SHARE * total]
        if top:
            most = top[0][1]
            chosen[name] = [k for k, n in top for _ in range(max(1, round(REPEATS * n / most)))]
    return chosen


NAMED_SLOTS = (("kick", "kick"), ("snare", "snare"), ("hihat", "hat"), ("tom", "tom"), ("crash", "cymbal"), ("rim", "other"))


def kit_from_names(uses: Counter, labels: dict) -> dict:
    """Kit pieces from the drum namer's names: {slot: sample key}, each slot
    the most-played sample named for it (NAMED_SLOTS), a second hat the
    open hat; {} where no kick or snare is named."""
    by = defaultdict(list)
    for k in sorted(uses, key=lambda k: (-uses[k], k)):
        if labels.get(k) and labels[k] != "none":
            by[labels[k]].append(k)
    out = {slot: by[label][0] for slot, label in NAMED_SLOTS if by.get(label)}
    if len(by.get("hat", [])) >= 2:
        out["open_hihat"] = by["hat"][1]
    return out if "kick" in out and "snare" in out else {}


def drum_uses(g: Gathered) -> Counter:
    """The samples the game plays as drums more than not: {sample key: drum-role notes} for those whose drum-role notes
    are at least half their notes over every role. A sample the namer could not place ("other") is a drum only if the
    game treats it as one: FFVI's mallet sample, a melody instrument in sixteen songs with a few drum-role notes, had
    taken the kit's rim slot as the busiest "other"."""
    drum = g.uses.get(R.DRUMS, Counter())
    total = Counter()
    for counts in g.uses.values():
        total.update(counts)
    return Counter({k: n for k, n in drum.items() if 2 * n >= total[k]})


def envelope_of(g: Gathered, k: str) -> dict | None:
    """The envelope the game plays a sample with most, as the pack file
    carries it: {"adsr": [ADSR1, ADSR2]} or {"gain": GAIN}; None where none
    was seen. The whole-song render had played every note flat at full
    level and cut it dead; FFVI plays every note through ADSR, a third of
    its accompaniment notes and half its bass notes decaying while held,
    its pads swelling in over 640 ms (2026-10-24)."""
    c = g.envelopes.get(k)
    if not c:
        return None
    kind, *vals = c.most_common(1)[0][0]
    return {"adsr": [vals[0], vals[1]]} if kind == "adsr" else {"gain": vals[0]}


def other_slot(g: Gathered, sounds: dict) -> str | None:
    """The sample for the kit's "other" slot (the figure letter o): the one
    carrying most of the game's drum strikes the namer called other in their
    song, among the sounds the pack holds. In FFVI that is the snare sample
    itself, heard differently in some songs; the busiest sample NAMED other
    had been a melody instrument (round 17) and then a one-song orchestral
    hit (round 24, Song Check 18's Whole 29)."""
    ks = [k for k in g.other if k in sounds]
    return max(ks, key=lambda k: (g.other[k], k)) if ks else None


def kit_by_name(g: Gathered, sounds: dict) -> dict:
    """The kit from the drum namer's names of the game's drum samples (as
    the game plays them: `sounds`), kit_from_names over the samples the
    game plays as drums (drum_uses); a slot the names leave empty the pack
    format fills from its palette; {} where it names too few."""
    from . import drums
    labels = {}
    for k, (pcm, rate, *more) in sounds.items():
        loop = more[0] if more else None
        held = more[1] if len(more) > 1 else None
        try:                                                # the sample as the game plays it: at its pitch, its loop held as long as the game holds it
            labels[k] = drums.name(drums.measure(pcm, rate, loop, held))
        except Exception:                                   # a sound the namer cannot measure is left unnamed
            labels[k] = "none"
    g.names = labels
    out = kit_from_names(drum_uses(g), labels)
    if out:
        rim = other_slot(g, sounds)
        if rim is not None:
            out["rim"] = rim
        else:
            out.pop("rim", None)
    return out


def kit(g: Gathered, sounds: dict) -> dict:
    """Drum samples to kit pieces: by the drum namer's names (kit_by_name),
    else by brightness (zero crossings a second, at the pitch the game
    plays them) and length: {piece: sample key}."""
    named = kit_by_name(g, sounds)
    if named:
        return named
    drums = [k for k, n in g.uses.get(R.DRUMS, Counter()).most_common(VOICES) if k in sounds]
    if not drums:
        return {}
    feat = {}
    for k in drums:
        pcm, rate = sounds[k][:2]
        crossings = sum(1 for a, b in zip(pcm, pcm[1:]) if (a < 0) != (b < 0))
        feat[k] = (crossings / (len(pcm) / rate), _length(pcm) / rate)
    by_bright = sorted(drums, key=lambda k: feat[k][0])
    out = {"kick": by_bright[0]}
    rest = by_bright[1:]
    for piece, long in (("hihat", False), ("crash", True)):
        fits = [k for k in rest if (feat[k][1] >= LONG) == long]
        if fits and len(rest) >= 2:          # a kick and one more: that one is the snare
            out[piece] = fits[-1]
            rest.remove(fits[-1])
    if rest:
        out["snare"] = rest[len(rest) // 2]
    return out


def _length(pcm) -> int:
    """Frames until the sound has fallen 40 dB under its peak for good."""
    peak = max((abs(x) for x in pcm), default=0) or 1
    floor = peak / 100
    for i in range(len(pcm) - 1, -1, -1):
        if abs(pcm[i]) > floor:
            return i + 1
    return 0


def habits(g: Gathered) -> dict:
    """The habits the readings give straight."""
    out = {}
    if g.tempos:
        out["tempo"] = {name: g.tempos.get(name, 0) for _, name in TEMPOS}
    if g.modes:
        out["scale_family"] = {"minor": g.modes.get("minor", 0), "major": g.modes.get("major", 0), "pentatonic": 0}
    if g.songs:
        out["drumless"] = round(g.drumless / g.songs, 2)
    if g.echo:
        on = [e for e in g.echo if e[0]]
        out["echo"] = round(len(on) / len(g.echo), 2)
        delays = Counter(min(DELAYS, key=lambda d: abs(math.log2(rows / DELAYS[d]))) for _, rows, _, _ in on if rows)
        if delays:
            out["echo_delay"] = {d: delays.get(d, 0) for d in DELAYS}
        fb = sorted(f for _, _, f, _ in on)
        if fb:
            lo, hi = fb[len(fb) // 4], fb[(3 * len(fb)) // 4]
            out["echo_feedback"] = [round(min(lo, 0.9), 2), round(min(max(hi, lo), 0.9), 2)]
        wet = Counter(next(name for top, name in WET if w < top) for _, _, _, w in on)
        if wet:
            out["echo_wet"] = {name: wet.get(name, 0) for _, name in WET}
    return out


def voice_of(key: str) -> str:
    """A sample's voice name in the pack, from its BRR data's hash."""
    return "s" + key[:10]


def build(g: Gathered, decode, name: str, label: str | None = None) -> tuple[dict, dict]:
    """The pack file's data, and its samples to write: {voice: (pcm, rate)}.
    decode(key) gives a sample's (pcm, loop (start, end) or None) as the SNES
    chip's interpolation colours it."""
    chosen = pools(g)
    used = {k for ks in chosen.values() for k in ks} | set(g.uses.get(R.DRUMS, Counter()))
    decoded = {k: decode(k) for k in used}
    decoded = {k: d for k, d in decoded.items() if d is not None}
    sounds = {}
    for k in g.uses.get(R.DRUMS, Counter()):
        if k in decoded and g.pitches.get(k):
            pitch = g.pitches[k].most_common(1)[0][0]
            held = statistics.median(g.held[k]) if g.held.get(k) else None
            sounds[k] = (decoded[k][0], max(1000, round(RATE * pitch / 0x1000)), decoded[k][1], held)
    pieces = kit(g, sounds)
    samples, files = {}, {}
    release_of = {}
    for pool, ks in chosen.items():
        for k in ks:
            release_of.setdefault(k, RELEASE[pool])
    for pool, ks in list(chosen.items()):
        kept = []
        for k in ks:
            if k not in decoded or not g.f0.get(k):
                continue                                 # no pitch found: not a tonal voice
            pcm, loop = decoded[k]
            v = voice_of(k)
            if v not in samples:
                spec = {"file": f"{v}.wav", "note": round(69 + 12 * math.log2(g.f0[k] / 440), 2), "volume": 58}
                if loop:
                    spec["loop"] = [loop[0], loop[1]]
                    spec["release"] = release_of[k]
                if envelope_of(g, k):
                    spec["envelope"] = envelope_of(g, k)
                samples[v], files[v] = spec, (pcm, RATE)
            kept.append(v)
        if kept:
            chosen[pool] = kept
        else:
            del chosen[pool]
    drums = {}
    for piece, k in pieces.items():
        v = voice_of(k)
        if v not in samples:
            samples[v] = {"file": f"{v}.wav", "percussion": True}
            if envelope_of(g, k):
                samples[v]["envelope"] = envelope_of(g, k)
            files[v] = sounds[k][:2]
        drums[piece] = v
    uses = g.uses.get(R.DRUMS, Counter())                   # every drum the game plays as one and the namer could name (round 63): a song's
    for k, n in uses.most_common():                         # own kit rides its balance token, so the pack holds the game's kits, not one
        name_ = g.names.get(k, "none")
        if n < KIT_HITS or name_ in ("none", "other") or k not in sounds or 2 * n < sum(c.get(k, 0) for c in g.uses.values()):
            continue
        v = voice_of(k)
        if v in samples and not samples[v].get("percussion"):
            continue                                        # a tonal voice the game also strikes: it stays a voice
        if v not in samples:
            samples[v] = {"file": f"{v}.wav", "percussion": True}
            if envelope_of(g, k):
                samples[v]["envelope"] = envelope_of(g, k)
            files[v] = sounds[k][:2]
        samples[v]["piece"] = name_
    voices = dict(chosen)
    if drums:
        voices["drums"] = drums
    data = {"bitcomposer_pack": 1, "name": name, "label": label or f"{g.game} (from its SPC files)"[:60],
            "palette": "snes", "voices": voices, "habits": habits(g), "samples": samples}
    return data, files


def why(g: Gathered, data: dict) -> dict:
    """Why each of the pack's samples is where it is: the parts the readings
    found it playing, in how many songs and how many notes, most first.
    {voice: [[part, songs, notes], ...]}; the player's PACKS panel shows it."""
    key_of = {voice_of(k): k for k in g.where}
    out = {}
    for v in data["samples"]:
        k = key_of.get(v)
        rows = [[role, g.songs_in[role][k], counts[k]] for role, counts in g.uses.items() if k in counts]
        out[v] = sorted(rows, key=lambda x: -x[2])
    return out


def write(data: dict, files: dict, out: Path, reasons: dict | None = None, songs: int | None = None, game: str | None = None) -> Path:
    """The pack file and its WAVs into `out`, with why its samples are where
    they are (WHY: the songs read, and why()'s reasons) when given."""
    out.mkdir(parents=True, exist_ok=True)
    for v, (pcm, rate) in files.items():
        with wave.open(str(out / f"{v}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm.tobytes())
    if reasons is not None:
        (out / WHY).write_text(json.dumps({"songs": songs, "game": game, "why": reasons}, indent=1) + "\n", encoding="utf-8")
    path = out / "pack.json"
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    return path


def name_for(folder: str) -> str:
    """A pack name from a folder's: lower-case letters, digits and _, a letter first."""
    n = re.sub(r"[^a-z0-9]+", "_", folder.lower()).strip("_") or "game"
    if not n[0].isalpha():
        n = "g" + n
    n = n[:20]
    return n if n.endswith("_spc") or len(n) > 20 else (n + "_spc")[:24]


def _read(path):
    from .. import spc
    from . import reading
    try:
        snap = spc.read(path)
        return reading.read(snap), snap
    except Exception as e:                   # one song's failure is reported, the rest read on
        return RuntimeError(f"{path}: {type(e).__name__}: {e}"), None


def make(paths, out, name: str | None = None, workers: int | None = None, say=print, progress=None) -> Path:
    """Read a game's SPC files (folders read whole, archives unpacked:
    archives.py) and write a thin pack of them into `out`: pack.json, its
    samples' WAVs and why each is where it is (WHY). Returns the pack file.
    progress(done, total) after each song."""
    with tempfile.TemporaryDirectory(prefix="bitcomposer-spc-") as unpack:
        return _make(archives.spc_files(paths, Path(unpack)), paths, out, name, workers, say, progress)


def _make(files, paths, out, name, workers, say, progress) -> Path:
    import os
    from multiprocessing import Pool
    from .. import spc
    from ..spc import brr, snes_chip
    if not files:
        raise ValueError("no SPC files to read")
    readings, snaps = [], []
    with Pool(workers or max(1, (os.cpu_count() or 2) - 1)) as pool:
        for i, (r, snap) in enumerate(pool.imap(_read, [str(f) for f in files])):
            if progress:
                progress(i + 1, len(files))
            if isinstance(r, RuntimeError):
                say(f"  skipped: {r}")
                continue
            readings.append(r)
            snaps.append(snap)
    if not readings:
        raise ValueError("no SPC file could be read")
    from . import store
    db = store.connect()                                    # the readings kept (phase 6): a vocabulary is fitted over them
    for r in readings:
        if not store.known(db, r.id):
            store.keep(db, r)
    game = Counter(r.game for r in readings).most_common(1)[0][0]
    g = gather(readings, snaps)
    cache = {}

    def decode(key):
        source, (start, loop) = g.where[key]
        if source not in cache:
            cache[source] = spc.read(source)
        s = brr.decode(cache[source].ram, start, loop) if 0 < start < 0xFFC0 else None
        if s is None or len(s) < 16:
            return None
        lp = (s.loop_start, s.loop_end) if s.loops and s.loop_end > s.loop_start else None
        return snes_chip.snes_interpolated(s.pcm, lp), lp

    first = Path(paths[0])
    folder = first.name if first.is_dir() else first.stem if archives.is_archive(first) else first.parent.name
    data, wavs = build(g, decode, name or name_for(folder))
    path = write(data, wavs, Path(out), why(g, data), len(readings), game=game)
    v = data["voices"]
    say(f"{path}: {len(readings)} songs read, {len(wavs)} samples; " +
        ", ".join(f"{pool} {len(set(ks))}" for pool, ks in v.items() if pool != "drums") +
        (f", kit: {', '.join(v['drums'])}" if "drums" in v else ""))
    if g.names:
        uses = g.uses.get(R.DRUMS, Counter())
        say("  drums named: " + ", ".join(f"{k[:10]} {g.names[k]} ({uses[k]} hits)" for k in sorted(g.names, key=lambda k: -uses[k])))
    if progress:
        progress(len(files), len(files))
    try:                                                    # the lead by what is heard (round 64): each voice rendered alone, the melody label moved
        from . import lead                                  # where another voice carries the tune; before the tables, which count on the lead
        folder = os.path.commonpath([os.path.dirname(os.path.abspath(str(f))) for f in files])
        lead.run(db, game, folder, say=say)
    except Exception as e:                                  # the readings stand as read; the error is said, not raised
        say(f"  the lead pass did not run: {type(e).__name__}: {e}")
    try:                                                    # the game's vocabulary beside its samples (format 2), then the library's over everything
        from . import packtables
        from .. import vocabularies
        packtables.into(db, game, path, say=say)
        vocabularies.refit_library(db, say=say)
    except Exception as e:                                  # the pack stands without its tables; the error is said, not raised
        say(f"  the vocabulary was not counted: {type(e).__name__}: {e}")
    return path
