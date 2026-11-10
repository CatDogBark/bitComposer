#!/usr/bin/env python3
"""Give an existing pack file's kit voices their tonal readings (round 119).

A pack file registers each sample once, as a tonal voice (its note, its loop) or as a kit voice (as recorded). A game may
do both with one recording: Final Fantasy VI strikes its rhythm guitar as a drum in some songs and plays it as the riff's
line or the bass in five. The pack builder now writes such a kit voice's `tonal` reading (translate.pack.build); this
tool adds the readings to a pack built before it, from the readings database, without rebuilding the pack:

    python tools/pack_tonal.py PACK.json --db readings.db --game "Final Fantasy VI"            # says what it would add
    python tools/pack_tonal.py PACK.json --db readings.db --game "Final Fantasy VI" --write    # and writes the file

A sample counts as played pitched where a voice of any part but the drums plays it on NOTES notes or more in some song;
its pitch is the readings' f0 for it (the median over those songs), its loop the SNES chip's where the readings saw one.
"""
import argparse
import json
import sqlite3
import statistics
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bitcomposer.translate import pack as pack_mod  # noqa: E402
from bitcomposer.translate.rhythm import readings as readings_mod  # noqa: E402

NOTES = 8                            # notes a pitched voice plays on a sample for the song to count


def pitched_readings(db, game: str) -> dict:
    """{voice: (f0 at the readings' rate, loop (start, end) in frames or None, frames)} for the samples the game plays pitched."""
    songs, _ = readings_mod.load(db, game)
    seen = {}
    for s in songs:
        for _, (part, notes) in (getattr(s, "voice_notes", None) or {}).items():
            if part == "drums":
                continue
            counts = {}
            for n in notes:
                if len(n) > 3 and isinstance(n[3], str) and n[2] == n[2]:
                    counts[n[3]] = counts.get(n[3], 0) + 1
            for key, c in counts.items():
                if c < NOTES:
                    continue
                row = db.execute("select f0, frames, loops, start, loop from samples where song = ? and key = ?", (s.sid, key)).fetchone()
                if row and row[0]:
                    f0, frames, loops, start, loop = row
                    seen.setdefault(pack_mod.voice_of(key), []).append((f0, ((loop - start) // 9 * 16, frames) if loops else None, frames))
    out = {}
    for v, rows in seen.items():
        loops = [r[1] for r in rows if r[1]]
        out[v] = (statistics.median(r[0] for r in rows), loops[0] if loops else None, rows[0][2])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pack"); ap.add_argument("--db", required=True); ap.add_argument("--game", required=True)
    ap.add_argument("--write", action="store_true", help="write the pack file (it is only read without)")
    args = ap.parse_args(argv)
    path = Path(args.pack)
    data = json.loads(path.read_text(encoding="utf-8"))
    readings = pitched_readings(sqlite3.connect(args.db), args.game)
    rates = {}
    for v, spec in (data.get("samples") or {}).items():
        if spec.get("percussion") and v in readings:
            with wave.open(str(path.parent / spec["file"]), "rb") as w:
                rates[v] = (w.getframerate(), w.getnframes())
    changed = pack_mod.add_tonal_readings(data, rates, readings)
    for v in changed:
        print(f"{v} ({data['samples'][v].get('piece', 'kit voice')}): tonal {data['samples'][v]['tonal']} (its file at {rates[v][0]} Hz, {rates[v][1]} frames)")
    if not changed:
        print("nothing to add: no kit voice of this pack is played pitched, or every one has its reading")
    elif args.write:
        path.write_text(json.dumps(data, indent=1), encoding="utf-8")
        print(f"written: {path}")
    else:
        print("not written (--write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
