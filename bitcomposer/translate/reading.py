"""A song read: its notes, beat, parts, key, chords and form, from its snapshot."""
import hashlib
import json
import math
import os
import statistics
from dataclasses import dataclass, field

from . import beat, events, form as form_mod, harmony, measures as measures_mod, phase as phase_mod, roles as roles_mod


@dataclass
class Reading:
    id: str                          # the snapshot's hash
    file: str
    folder: str
    game: str
    title: str
    composer: str
    driver: str | None
    song: events.Song
    grid: beat.Grid | None           # None: free time
    roles: list = field(default_factory=list)
    key: tuple | None = None         # (tonic pitch class, "major"/"minor", fit)
    scale: tuple | None = None       # (tonic pitch class, the scale's name in harmony.MODES, fit)
    chords: list = field(default_factory=list)
    form: form_mod.Form | None = None   # its parts and loop
    measures: dict = field(default_factory=dict)   # the yardsticks it shares with the generator's songs
    echo: dict = field(default_factory=dict)       # the song's echo as the chip had it at key-on (echo_of_notes): volume, delay_ms, feedback,
                                                   # and each voice's share of notes that send (voice_N); kept as features of source "echo"
    vibrato: dict = field(default_factory=dict)    # each voice's vibrato on its held notes (vibrato_of_notes, round 72); features of source "vibrato"


ECHO_FIELDS = ("volume", "delay_ms", "feedback")

# Vibrato (round 72): a note HELD this long or more may carry it (the player's old rule's threshold, kept as the count's);
# it CARRIES vibrato when its pitch writes swing back and forth through VIBRATO_CYCLES full cycles or more, each swing
# VIBRATO_MIN_DEPTH cents or more about the centre (a slide is monotonic, a one-off bend is one swing); a swing of
# VIBRATO_TRILL cents or more is a trill, counted apart. The length classes the word's shares are counted by, in seconds.
VIBRATO_HOLD = 0.35
VIBRATO_CYCLES = 1.5
VIBRATO_MIN_DEPTH = 3.0
VIBRATO_TRILL = 90.0
VIBRATO_CLASSES = ((0.35, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, float("inf")))


def vibrato_class(seconds: float) -> int | None:
    """Which length class a held note falls in (0 to 3), None under the hold."""
    for k, (lo, hi) in enumerate(VIBRATO_CLASSES):
        if lo <= seconds < hi:
            return k
    return None


def note_vibrato(note) -> dict | None:
    """What a decoded note (spc.notes.Note: its key-on pitch register and its `bends`, (time, register) while it
    sounds) carries of periodic pitch modulation: None where none, else {"depth": cents either side of the centre (the
    median half swing), "rate": Hz (one cycle per two swings), "onset": seconds from key-on to the modulation's start
    (the first extreme less a quarter cycle), "rise": the first swing's depth over the median (1.0: no rise),
    "trill": whether the swings are a trill's (VIBRATO_TRILL cents or more)}."""
    p0 = note.pitch
    if p0 <= 0 or len(note.bends) < 3:
        return None
    series = [(0.0, 0.0)] + [(t - note.start, 1200.0 * math.log2(p / p0)) for t, p in note.bends if p > 0]
    ext, n, i = [], len(series), 1
    while i < n - 1:                                       # local extremes, a plateau's first point, the ends left out
        t, c = series[i]
        j = i
        while j + 1 < n and series[j + 1][1] == c:
            j += 1
        if j >= n - 1:
            break
        prev, nxt = series[i - 1][1], series[j + 1][1]
        if (c > prev and c > nxt) or (c < prev and c < nxt):
            ext.append((t, c))
        i = j + 1
    swings = [(t0, t1, abs(c1 - c0) / 2.0) for (t0, c0), (t1, c1) in zip(ext, ext[1:])]
    best, run = [], []                                     # the longest run of consecutive swings deep enough
    for s in swings:
        if s[2] >= VIBRATO_MIN_DEPTH:
            run.append(s)
        else:
            best, run = (run if len(run) > len(best) else best), []
    best = run if len(run) > len(best) else best
    if len(best) < 2 * VIBRATO_CYCLES:
        return None
    periods = [b[1] - a[1] for a, b in zip(best, best[2:])]
    if not periods or min(periods) <= 0:
        return None
    depth = statistics.median(s[2] for s in best)
    rate = 1.0 / statistics.median(periods)
    return {"depth": depth, "rate": rate, "onset": max(0.0, best[0][0] - 0.25 / rate), "rise": best[0][2] / depth if depth else 1.0,
            "trill": depth >= VIBRATO_TRILL}


def vibrato_of_notes(notes) -> dict:
    """Each voice's vibrato over its held notes (VIBRATO_HOLD or longer), from the decoded notes, round 72:
    {"voice_N_held": how many notes it held, "voice_N_vib": how many of them carry vibrato (trills left out),
    "voice_N_held_K" and "voice_N_vib_K": the same by length class K (VIBRATO_CLASSES), "voice_N_depth",
    "voice_N_rate", "voice_N_onset": the medians over its vibrato notes (cents, Hz, seconds)}; a voice with no held
    note has no entries. FFVI (80 songs, round 72's count): the tune's held notes carry vibrato in 0.19 of cases, the
    counter's in 0.10, the other parts' in 0.02 to 0.08; the depth's median 30 cents on the tune (quartiles 16 to 45),
    19 on the counter; the rate 5.7 Hz in most songs and 15 to 19 Hz in a third of them; the onset a median 0.5 s from
    key-on, so a note held under half a second carries it in 0.01 of cases, one held over a second in 0.3."""
    held, vib, depths, rates, onsets = {}, {}, {}, {}, {}
    for n in notes:
        if n.end is None or getattr(n, "noise", False) or n.pitch <= 0:
            continue
        k = vibrato_class(n.end - n.start)
        if k is None:
            continue
        v = n.voice
        held.setdefault(v, [0, 0, 0, 0])[k] += 1
        r = note_vibrato(n)
        if r is None or r["trill"]:
            continue
        vib.setdefault(v, [0, 0, 0, 0])[k] += 1
        depths.setdefault(v, []).append(r["depth"])
        rates.setdefault(v, []).append(r["rate"])
        onsets.setdefault(v, []).append(r["onset"])
    out = {}
    for v in sorted(held):
        out[f"voice_{v}_held"] = float(sum(held[v]))
        out[f"voice_{v}_vib"] = float(sum(vib.get(v, [0, 0, 0, 0])))
        for k in range(len(VIBRATO_CLASSES)):
            out[f"voice_{v}_held_{k}"] = float(held[v][k])
            out[f"voice_{v}_vib_{k}"] = float(vib.get(v, [0, 0, 0, 0])[k])
        if v in depths:
            out[f"voice_{v}_depth"] = statistics.median(depths[v])
            out[f"voice_{v}_rate"] = statistics.median(rates[v])
            out[f"voice_{v}_onset"] = statistics.median(onsets[v])
    return out


def echo_of_notes(notes) -> dict:
    """The song's echo from its decoded notes (spc.notes.Note: the echo registers as they stood at key-on), round 70:
    {"volume": the echo volume of full (EVOL, the louder side's magnitude, the median over the notes that send),
    "delay_ms": the delay (EDL x 16 ms, the most common), "feedback": the feedback's magnitude (EFB, the median), and
    "voice_N": each voice's share of its notes that send (EON with echo writes on and a delay)}; the three zero where
    no note sends. FFVI's echo volume is 0.20 of full in 70 of its 82 songs (round 69: quartiles 0.20..0.20), its
    delay 80 ms in every one, its feedback 0.78 at the median (0.55..0.78); the written songs sent at score.ECHO_WET
    0.4 with a "slap" delay of 48-144 ms, 6 dB wetter than the game ever plays on every sending voice, which the owner
    heard as vibrato and blur."""
    import statistics
    from collections import Counter
    by_voice, sending = {}, []
    for n in notes:
        send = bool(n.echo and n.echo_writes and n.echo_delay > 0)
        by_voice.setdefault(n.voice, []).append(send)
        if send:
            sending.append(n)
    out = {f"voice_{v}": sum(sends) / len(sends) for v, sends in sorted(by_voice.items())}
    if sending:
        out["volume"] = statistics.median(max(abs(x) for x in n.echo_volume) for n in sending)
        out["delay_ms"] = float(Counter(round(n.echo_delay * 1000) for n in sending).most_common(1)[0][0])
        out["feedback"] = statistics.median(abs(n.echo_feedback) for n in sending)
    else:
        out.update(volume=0.0, delay_ms=0.0, feedback=0.0)
    return out


def manifest(folder: str) -> dict:
    """The game folder's entry in a drivers.json beside it (spc_check's), if any."""
    parent, name = os.path.split(os.path.abspath(folder))
    path = os.path.join(parent, "drivers.json")
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        entry = json.load(fh).get(name, {})
    return entry if isinstance(entry, dict) else {"driver": entry}


def beat_and_parts(song) -> tuple:
    """The song's beat (None: free time) and each voice's part, the bar set
    again from the bass and its phase from where the song repeats itself;
    a voice echoing another is left out of the beat."""
    echoed = roles_mod.echoes(song)          # an echo's notes sit off the grid: a sure one is left out of the beat
    sure = {v for v, (u, delay, sureness) in echoed.items() if sureness >= roles_mod.ECHO_HELD}
    # (an echo found by the looser rule names a doubling but stays in the beat: which voices the beat is read
    #  from moves its level and its grid in dozens of songs, an open item of docs/idiom/phase-1-readers.md)
    grid = beat.find([(p.start, p.level, p.voice) for p in song.notes if p.voice not in sure])
    roles = roles_mod.assign(song, grid, echoed)
    if grid:
        bass = {x.voice for x in roles if x.role == roles_mod.BASS}
        beat.rebar(grid, [grid.beats(p.start) for p in song.notes if p.voice in bass])
        phase_mod.find(grid, song)
    return grid, roles


def read(snap, seconds: float | None = None, song: events.Song | None = None) -> Reading:
    """Read a snapshot as music (song: its notes, if already played)."""
    song = song or events.play(snap, seconds)
    return _read(song, snap)


def of_score(score, song: events.Song | None = None, id: str | None = None, game: str = "", title: str = "",
             composer: str = "", driver: str | None = None, grid: beat.Grid | None = None) -> Reading:
    """Read a score (spc.convert.Score) as music, through the readers a
    snapshot goes through: a snapshot's score names itself; a generated one
    is named by the arguments, and may bring its own beat (`grid`: the
    generator's, which it knows), the beat reader then left out."""
    song = song or events.of_score(score)
    if score.snap is not None:
        return _read(song, score.snap, grid)
    r = _read(song, None, grid)
    r.id = id or hashlib.sha1(repr([(p.voice, round(p.start, 4), p.midi) for p in song.notes]).encode()).hexdigest()[:20]
    r.game, r.title, r.composer, r.driver = game or score.game, title or score.title, composer or score.artist, driver
    return r


def _read(song: events.Song, snap, grid: beat.Grid | None = None) -> Reading:
    if grid is None:
        grid, roles = beat_and_parts(song)
    else:
        roles = roles_mod.assign(song, grid, roles_mod.echoes(song))
    source = snap.source if snap is not None else ""
    folder = os.path.basename(os.path.dirname(os.path.abspath(source))) if source else ""
    m = manifest(os.path.dirname(os.path.abspath(source))) if source else {}
    t = snap.tags if snap is not None else None
    r = Reading(hashlib.sha1(snap.raw).hexdigest()[:20] if snap is not None else "", os.path.basename(source), folder,
                m.get("game") or (t.game if t else "") or folder, (t.title if t else "") or "",
                m.get("composer") or (t.artist if t else "") or "", m.get("driver"), song, grid, roles)
    r.echo = echo_of_notes([p.note for p in song.notes if p.note is not None])
    r.vibrato = vibrato_of_notes([p.note for p in song.notes if p.note is not None])
    if grid:
        r.chords = harmony.chords(song, grid, roles)
        r.scale = harmony.scale(song, grid, roles, r.chords)       # (tonic, the scale's name, fit)
        r.key = (r.scale[0], "major" if r.scale[1] in harmony.MAJOR_MODES else "minor", r.scale[2])
        r.form = form_mod.read(song, grid)
        score = measures_mod.of_reading(r)
        r.measures = measures_mod.measure(score) if score else {}
    return r
