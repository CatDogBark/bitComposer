"""A song's bass replaced by one written from the bass table (phase 3 of docs/IDIOM.md, the acceptance by ear):
the table fitted on every other song in the readings, the figures drawn bar by bar for the song's own chords,
played on the song's own bass sample in its own register, the rest of the song as decoded.

    python tools/table_bass.py FILE.spc --db READINGS.db -o OUT.it [--seed 1] [--seconds 60] [--title T] [--figures OUT.json]

Prints the figures drawn and what the readers make of the original and the written song.
"""
import argparse
import bisect
import json
import math
import os
import sys
from array import array
from collections import Counter

from bitcomposer import spc
from bitcomposer.spc import convert
from bitcomposer.translate import harmony, reading, rhythm, store, writer
import random


def seconds_at(beats: array, b: float) -> float:
    """A time in beats back to seconds on the beat times (vocab._beats_at's inverse)."""
    if len(beats) < 2:
        return b
    i = min(max(int(math.floor(b)), 0), len(beats) - 2)
    return beats[i] + (b - i) * (beats[i + 1] - beats[i])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python tools/table_bass.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("spc")
    ap.add_argument("--db", required=True)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--title", help="the module's title (25 characters show in a player)")
    ap.add_argument("--figures", help="write the figures drawn and the song's own beside, as JSON")
    a = ap.parse_args(argv)
    db = store.connect(a.db)
    row = db.execute("SELECT id, game, title, key_tonic, key_mode FROM songs WHERE file = ?", (os.path.basename(a.spc),)).fetchone()
    if not row:
        print(f"{a.spc}: not in the readings", file=sys.stderr)
        return 1
    sid, game, title, tonic, mode = row
    songs, _ = rhythm.load(db)
    song = next((s for s in songs if s.sid == sid), None)
    if song is None or rhythm.R.BASS not in song.notes:
        print(f"{title}: not counted, or no bass read", file=sys.stderr)
        return 1
    units = rhythm.bass_units(songs)
    table = writer.fit([u for u in units if u.song != sid])
    own = [u.outcome for u in units if u.song == sid]
    notes, figures = writer.bass(song, table, random.Random(a.seed), key=(tonic, mode) if tonic is not None else None)
    print(f"{title} ({game}): habit {rhythm.bass_units([song])[0].values['habit']}, {len(figures)} bars written, {len(notes)} notes")
    for i, (f, o) in enumerate(zip(figures, own)):
        print(f"  bar {i:3d}  written {f:40.40}  own {o}")
    # the song as decoded, its bass voice's notes swapped for the written ones
    snap = spc.read(a.spc)
    original = convert.score_of(snap, a.seconds, fade=0.0)
    r = reading.of_score(original)
    voices = Counter(n.voice for n in original.notes)
    v = max((x.voice for x in r.roles if x.role == rhythm.R.BASS), key=lambda x: voices[x], default=None)
    if v is None:
        print("no bass voice in the decoded song", file=sys.stderr)
        return 1
    events = {(p.voice, round(p.start, 4)): p for p in r.song.notes if p.midi is not None}
    like = pitch_ref = midi_ref = None
    for n in original.notes:
        p = events.get((n.voice, round(n.start, 4)))
        if n.voice == v and p is not None:
            like, pitch_ref, midi_ref = n, n.pitch, p.midi
            break
    if like is None:
        print("no reference note on the bass voice", file=sys.stderr)
        return 1
    beats = array("d")
    beats.frombytes(db.execute("SELECT beats FROM beats WHERE song = ?", (sid,)).fetchone()[0])
    new = []
    for start_b, end_b, midi in notes:
        start, end = seconds_at(beats, start_b), seconds_at(beats, end_b)
        if start >= original.seconds:
            continue
        pitch = max(1, min(0x3FFF, round(pitch_ref * 2 ** ((midi - midi_ref) / 12))))
        new.append(convert.notes_mod.Note(v, start, like.sample, pitch, like.volume, like.adsr, like.gain, like.echo, False,
                                          brr=like.brr, echo_delay=like.echo_delay, echo_volume=like.echo_volume,
                                          echo_feedback=like.echo_feedback, echo_filter=like.echo_filter,
                                          echo_writes=like.echo_writes, end=min(end, original.seconds)))
    kept = [n for n in original.notes if n.voice != v]
    swapped = convert.Score(kept + new, original.seconds, original.voices, original.master, original.fade,
                            (a.title or f"{title} [table bass]")[:25], original.game, original.artist, original.row_hz,
                            original.tempo, original.tick_hz, original.aligned, original.on_ticks, original.snap,
                            dict(original.pcm_of), dict(original.key_of),
                            message=[f"{title}: the bass written from the bass table (phase 3 of docs/IDIOM.md)",
                                     f"the table fitted on every other song; seed {a.seed}; the rest as decoded"])
    info = convert.render(swapped, a.out)["info"]
    print(f"{a.out}: {info['notes']} notes, {info['channels']} channels; bass voice {v}, {len(new)} written notes")
    for label, sc in (("original", original), ("written", swapped)):
        rr = reading.of_score(sc)
        role = next((x.role for x in rr.roles if x.voice == v), "-")
        key = f"{harmony.NAMES[rr.key[0]]} {rr.key[1]}" if rr.key else "-"
        print(f"  {label:9s} voice {v} read as {role:14s} key {key:10s} tempo {rr.grid.bpm if rr.grid else 0:6.1f} chords {len(rr.chords)}")
    if a.figures:
        with open(a.figures, "w") as f:
            json.dump({"song": title, "game": game, "seed": a.seed, "written": figures, "own": own}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
