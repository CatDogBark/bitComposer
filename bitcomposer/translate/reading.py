"""A song read: its notes, beat, parts, key, chords and form, from its snapshot."""
import hashlib
import json
import os
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


ECHO_FIELDS = ("volume", "delay_ms", "feedback")


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
    if grid:
        r.chords = harmony.chords(song, grid, roles)
        r.scale = harmony.scale(song, grid, roles, r.chords)       # (tonic, the scale's name, fit)
        r.key = (r.scale[0], "major" if r.scale[1] in harmony.MAJOR_MODES else "minor", r.scale[2])
        r.form = form_mod.read(song, grid)
        score = measures_mod.of_reading(r)
        r.measures = measures_mod.measure(score) if score else {}
    return r
