"""Audio for the ear pages of phase 1 (docs/idiom/phase-1-readers.md): songs rendered from the
emulator's own output, once through, as Opus files the pages play, with a manifest the pages are
built from. A developer tool for the machine that holds the games; the files go to the listener.

    python tools/ear_sets.py chords SPC_ROOT READINGS.db OUT_DIR
        the Chord Change Check: the twelve songs below, the full mix once through (to the loop's
        end and a bar, at most 150 s), split into a development half and a held-out half by a
        fixed shuffle, with the readings' chord changes kept in the manifest for scoring (never
        shown on the page)
"""
import argparse
import json
import os
import random
import sqlite3
import subprocess
import sys
import wave
from array import array

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# game folder, file stem, why it is in: the reader's chord rate (changes a bar), decoded by
# VGMTrans or not, the beat tapped already or not, slow or fast, the key's fit
CHORD_SET = [
    ("ffvi-spc", "108 Kefka", "2.4/bar, decoded, tapped"),
    ("zelda-alttp", "08 Hyrule Field Main Theme", "1.9/bar, decoded, tapped, fast"),
    ("soul-blazer", "04 Underground Castle", "0.2/bar, decoded"),
    ("dkc", "07 Aquatic Ambiance", "0.6/bar, decoded, tapped, slow"),
    ("romancing-saga-3", "107 Harid's Theme", "3.8/bar, decoded"),
    ("mana-spc", "35 Still of the Night", "3.9/bar, decoded, slow"),
    ("super-metroid", "04 Crateria ~ The Space Pirates Appear", "3.7/bar, decoded, key fit 0.34"),
    ("evermore-spc", "38 Hall of Collosia", "3.7/bar, not decoded"),
    ("lufia2", "208 Four Gods", "0.3/bar, not decoded, key fit 0.39, slow"),
    ("super-turrican-2", "26 Psycho Spin", "0.2/bar, not decoded, key fit 0.46"),
    ("kirby-super-star", "26 Crash! Gourmet Race", "2.6/bar, decoded, tapped, fast"),
    ("earthbound", "045 Welcome to Your Sanctuary", "0.15/bar, slow"),
]
SPLIT_SEED = 20261020


def render(snap_path: str, seconds: float, out_wav: str) -> None:
    from bitcomposer import spc
    from bitcomposer.spc import emulate
    run = emulate.run(spc.read(snap_path), seconds, audio=True)
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(32000)
        w.writeframes(run.audio)


def to_opus(wav: str, out: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libopus", "-b:a", "112k", out], check=True)
    os.remove(wav)


def cmd_chords(a) -> int:
    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    os.makedirs(a.out_dir, exist_ok=True)
    order = list(range(len(CHORD_SET)))
    random.Random(SPLIT_SEED).shuffle(order)
    half = {i: ("development" if k % 2 == 0 else "held-out") for k, i in enumerate(order)}
    manifest = []
    for i, (folder, stem, why) in enumerate(CHORD_SET, 1):
        row = db.execute("SELECT id, game, title, bpm, meter, seconds, loop_bar, loop_seconds FROM songs WHERE folder = ? AND file = ?",
                         (folder, stem + ".spc")).fetchone()
        if row is None:
            print(f"not in the readings: {folder}/{stem}")
            continue
        beats, bars = array("d"), array("d")
        b = db.execute("SELECT beats, bars FROM beats WHERE song = ?", (row["id"],)).fetchone()
        if b:
            beats.frombytes(b[0])
            bars.frombytes(b[1])
        length = 90.0
        if row["loop_bar"] is not None and row["loop_seconds"] and row["loop_bar"] < len(bars):
            length = bars[row["loop_bar"]] + row["loop_seconds"] + (bars[1] - bars[0] if len(bars) > 1 else 2.0)
        length = min(150.0, length, row["seconds"])
        name = f"{i:02d} {row['game']} - {row['title']}"
        wav = os.path.join(a.out_dir, name + ".wav")
        ogg = os.path.join(a.out_dir, name + ".ogg")
        if not os.path.exists(ogg):
            render(os.path.join(a.spc_root, folder, stem + ".spc"), length, wav)
            to_opus(wav, ogg)
        changes = [round(c[0], 3) for c in db.execute(
            "SELECT start FROM chords WHERE song = ? AND root IS NOT NULL AND fit >= 0.6 ORDER BY start", (row["id"],))]
        # a chord's start in beats to seconds on the grid
        def at(beat: float) -> float:
            import bisect
            if len(beats) < 2:
                return beat
            if beat <= 0:
                return beats[0] + beat * (beats[1] - beats[0])
            k = int(beat)
            if k + 1 < len(beats):
                return beats[k] + (beat - k) * (beats[k + 1] - beats[k])
            return beats[-1] + (beat - (len(beats) - 1)) * (beats[-1] - beats[-2])
        manifest.append({"n": f"{i:02d}", "game": row["game"], "title": row["title"], "file": name + ".ogg", "folder": folder,
                         "stem": stem, "why": why, "half": half[i - 1], "seconds": round(length, 2), "bpm": round(row["bpm"], 1),
                         "meter": row["meter"], "bars": [round(x, 3) for x in bars if x <= length + 1],
                         "read_changes": [round(at(c), 3) for c in changes if at(c) <= length + 1]})
        print(f"{name}: {length:.0f} s, {half[i - 1]}, {len(manifest[-1]['read_changes'])} read changes")
    with open(os.path.join(a.out_dir, "chord-set.json"), "w") as f:
        json.dump(manifest, f, indent=0)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python tools/ear_sets.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("chords")
    p.add_argument("spc_root")
    p.add_argument("db")
    p.add_argument("out_dir")
    p.set_defaults(run=cmd_chords)
    a = ap.parse_args(argv)
    return a.run(a)


if __name__ == "__main__":
    sys.exit(main())
