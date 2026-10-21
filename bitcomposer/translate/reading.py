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
    chords: list = field(default_factory=list)
    form: form_mod.Form | None = None   # its parts and loop
    measures: dict = field(default_factory=dict)   # the yardsticks it shares with the generator's songs


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
    echoed = roles_mod.echoes(song)          # an echo's notes sit off the grid: left out of the beat
    grid = beat.find([(p.start, p.level, p.voice) for p in song.notes if p.voice not in echoed])
    roles = roles_mod.assign(song, grid, echoed)
    if grid:
        bass = {x.voice for x in roles if x.role == roles_mod.BASS}
        beat.rebar(grid, [grid.beats(p.start) for p in song.notes if p.voice in bass])
        phase_mod.find(grid, song)
    return grid, roles


def read(snap, seconds: float | None = None, song: events.Song | None = None) -> Reading:
    """Read a snapshot as music (song: its notes, if already played)."""
    song = song or events.play(snap, seconds)
    grid, roles = beat_and_parts(song)
    folder = os.path.basename(os.path.dirname(os.path.abspath(snap.source))) if snap.source else ""
    m = manifest(os.path.dirname(os.path.abspath(snap.source))) if snap.source else {}
    t = snap.tags
    r = Reading(hashlib.sha1(snap.raw).hexdigest()[:20], os.path.basename(snap.source or ""), folder,
                m.get("game") or t.game or folder, t.title or "", m.get("composer") or t.artist or "",
                m.get("driver"), song, grid, roles)
    if grid:
        r.key = harmony.key(song, grid, roles)
        r.chords = harmony.chords(song, grid, roles)
        r.form = form_mod.read(song, grid)
        score = measures_mod.of_reading(r)
        r.measures = measures_mod.measure(score) if score else {}
    return r
