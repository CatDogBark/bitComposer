"""The readings, kept: a SQLite database on the user's machine (never in
the repository: a game's notes are its music, its samples its files).

A song is kept by its snapshot's hash with the translator's version that
read it, so only what changed is read again. Its notes are kept a voice at
a time as packed arrays (a soundtrack is a few hundred thousand notes),
beside what was read from them: the beat, the key, each voice's part, the
chords, the form (its parts and loop), and features for the measures packs are made from and the
generator's songs are held against."""
import json
import os
import sqlite3
from array import array
from pathlib import Path

SCHEMA = 4                           # 2: songs.loose; 3: songs.loop_*, form; 4: form.level
VERSION = "6"                        # the translator's; a song read by another is read again

TABLES = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS songs (
    id TEXT PRIMARY KEY, file TEXT, folder TEXT, game TEXT, title TEXT, composer TEXT, driver TEXT,
    seconds REAL, version TEXT,
    bpm REAL, meter INTEGER, division INTEGER, on_grid REAL, swing REAL,
    key_tonic INTEGER, key_mode TEXT, key_fit REAL, loose INTEGER,
    loop_bar INTEGER, loop_bars INTEGER, loop_seconds REAL);
CREATE TABLE IF NOT EXISTS samples (
    song TEXT, idx INTEGER, key TEXT, start INTEGER, loop INTEGER, f0 REAL, offset REAL,
    frames INTEGER, loops INTEGER, PRIMARY KEY (song, idx));
CREATE TABLE IF NOT EXISTS voices (
    song TEXT, voice INTEGER, role TEXT, of INTEGER, evidence TEXT, notes BLOB, PRIMARY KEY (song, voice));
CREATE TABLE IF NOT EXISTS beats (song TEXT PRIMARY KEY, beats BLOB, bars BLOB);
CREATE TABLE IF NOT EXISTS chords (song TEXT, start REAL, end REAL, root INTEGER, shape TEXT, fit REAL);
CREATE TABLE IF NOT EXISTS features (song TEXT, source TEXT, name TEXT, value REAL, PRIMARY KEY (song, source, name));
CREATE TABLE IF NOT EXISTS form (song TEXT, idx INTEGER, label TEXT, bar INTEGER, bars INTEGER, start REAL, of INTEGER,
    level TEXT, PRIMARY KEY (song, idx));     -- level: 'part' (a phrase) or 'section' (a short phrase and its repeats)
CREATE INDEX IF NOT EXISTS chords_song ON chords (song);
"""
NOTE_FIELDS = 6                      # start and length in beats, midi (NaN: unpitched), level, pan, sample index (-1: noise)


def default_path() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return Path(base) / "bitcomposer" / "readings.db"


def connect(path=None) -> sqlite3.Connection:
    path = Path(path) if path else default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.executescript(TABLES)
    row = db.execute("SELECT value FROM meta WHERE key = 'schema'").fetchone()
    old = int(row[0]) if row else SCHEMA
    if old < 2:
        db.execute("ALTER TABLE songs ADD COLUMN loose INTEGER")   # a beat followed loosely, on no grid
    if old < 3:
        for column in ("loop_bar INTEGER", "loop_bars INTEGER", "loop_seconds REAL"):
            db.execute(f"ALTER TABLE songs ADD COLUMN {column}")
    if 3 <= old < 4:
        db.execute("ALTER TABLE form ADD COLUMN level TEXT")
    db.execute("INSERT OR REPLACE INTO meta VALUES ('schema', ?)", (str(SCHEMA),))
    db.commit()
    return db


def known(db, song_id: str) -> bool:
    """Whether the song is kept, read by this version."""
    row = db.execute("SELECT version FROM songs WHERE id = ?", (song_id,)).fetchone()
    return bool(row) and row[0] == VERSION


def pack(notes, grid, sample_index: dict) -> bytes:
    """A voice's notes as a packed array, NOTE_FIELDS a note."""
    a = array("f")
    nan = float("nan")
    for p in notes:
        start = grid.beats(p.start) if grid else p.start
        end = (grid.beats(p.end) if grid else p.end) if p.end is not None else nan
        a.extend((start, end - start, p.midi if p.midi is not None else nan, p.level, p.pan,
                  sample_index.get(p.sample.key, -1) if p.sample is not None else -1))
    return a.tobytes()


def unpack(blob: bytes) -> list[tuple]:
    a = array("f")
    a.frombytes(blob)
    return [tuple(a[i:i + NOTE_FIELDS]) for i in range(0, len(a), NOTE_FIELDS)]


def keep(db, reading) -> None:
    """Keep a song's reading, replacing an older one."""
    r = reading
    sid = r.id
    for table in ("songs", "samples", "voices", "beats", "chords", "form"):
        db.execute(f"DELETE FROM {table} WHERE {'id' if table == 'songs' else 'song'} = ?", (sid,))
    db.execute("DELETE FROM features WHERE song = ? AND source = 'soundtrack'", (sid,))
    g = r.grid
    f = r.form
    db.execute("INSERT INTO songs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        sid, r.file, r.folder, r.game, r.title, r.composer, r.driver, r.song.seconds, VERSION,
        g.bpm if g else None, g.meter if g else None, g.division if g else None, g.on_grid if g else None,
        g.swing if g else None, r.key[0] if r.key else None, r.key[1] if r.key else None, r.key[2] if r.key else None,
        int(g.loose) if g else None, f.loop_bar if f else None, f.loop_bars if f else None,
        f.loop_seconds if f else None))
    index = {}
    for i, s in enumerate(r.song.samples.values()):
        index[s.key] = i
        db.execute("INSERT INTO samples VALUES (?,?,?,?,?,?,?,?,?)",
                   (sid, i, s.key, s.addr[0], s.addr[1], s.f0, s.offset, s.frames, int(s.loops)))
    by_voice = {}
    for p in r.song.notes:
        by_voice.setdefault(p.voice, []).append(p)
    roles = {x.voice: x for x in r.roles}
    for v, notes in by_voice.items():
        x = roles.get(v)
        evidence = dict(x.evidence) if x else {}
        if g and v in g.lags:
            evidence["lag_ms"] = round(g.lags[v] * 1000, 1)     # keyed this far behind the others
        if g and v in g.ornaments:
            evidence["roll"] = True                             # left out of the grid
        db.execute("INSERT INTO voices VALUES (?,?,?,?,?,?)", (
            sid, v, x.role if x else None, x.of if x else None, json.dumps(evidence) if evidence else None,
            pack(notes, g, index)))
    if g:
        db.execute("INSERT INTO beats VALUES (?,?,?)", (sid, array("d", g.beat_times).tobytes(),
                                                       array("d", g.bar_times).tobytes()))
    for c in r.chords:
        db.execute("INSERT INTO chords VALUES (?,?,?,?,?,?)", (sid, c.start, c.end, c.root, c.shape, c.fit))
    rows = [(p, "part") for p in (f.parts if f else [])] + [(p, "section") for p in (f.sections if f else [])]
    for i, (p, level) in enumerate(rows):
        db.execute("INSERT INTO form VALUES (?,?,?,?,?,?,?,?)", (sid, i, p.label, p.bar, p.bars, p.start, p.of, level))
    db.executemany("INSERT INTO features VALUES (?,?,?,?)",
                   [(sid, "soundtrack", k, float(v)) for k, v in r.measures.items()])
    db.commit()


def features(db, songs, source: str = "soundtrack") -> dict:
    """The measures kept for these songs: name -> their values."""
    out = {}
    for sid in songs:
        for name, value in db.execute("SELECT name, value FROM features WHERE song = ? AND source = ?",
                                      (sid, source)):
            out.setdefault(name, []).append(value)
    return out
