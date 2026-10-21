"""Audio for the ear pages of phase 1 (docs/idiom/phase-1-readers.md): songs rendered from the
emulator's own output, once through, as Opus files the pages play, with a manifest the pages are
built from. A developer tool for the machine that holds the games; the files go to the listener.

    python tools/ear_sets.py chords SPC_ROOT READINGS.db OUT_DIR
        the Chord Change Check: the twelve songs below, the full mix once through (to the loop's
        end and a bar, at most 150 s), split into a development half and a held-out half by a
        fixed shuffle, with the readings' chord changes kept in the manifest for scoring (never
        shown on the page)
    python tools/ear_sets.py drums SPC_ROOT READINGS.db DRAW.json OUT_DIR
        the Drum Name Check: for each drawn sample, a stretch of the song that hits it most, the
        voice alone and the full mix, a few seconds each; the namer's name kept in the manifest
    python tools/ear_sets.py tune SPC_ROOT READINGS.db OUT_DIR
        the Tune Check: the ten songs below, the full mix once through and each voice alone; the
        readings' part for each voice kept in the manifest
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
# songs whose melody voice rests in most bars (the tune passes to other voices, or the roles read it
# wrong): game, title, as the readings have them
TUNE_SET = [
    ("Super Mario World", "Overworld (Yoshi)"),
    ("Yoshi's Island", "Overworld"),
    ("Romancing SaGa 3", "Jungle"),
    ("EarthBound", "Escargo Express at Your Service!"),
    ("Final Fantasy VI", "Celes"),
    ("Axelay", "Toughness (part 1)"),
    ("Top Gear", "Title"),
    ("Super Ghouls'n Ghosts", "Ghouls' Stomach"),
    ("Chrono Trigger", "Chrono Trigger"),
    ("Donkey Kong Country", "Gang-Plank Galleon"),
]
RATE = 32000
FRAME = 4                            # bytes a stereo 16-bit frame


def render(snap_path: str, seconds: float, out_wav: str, mute: int = 0, crop: tuple | None = None) -> None:
    """The emulator's own output to a WAV: the whole run, or crop=(from, to) seconds of it;
    mute leaves voices out (bit n, voice n)."""
    from bitcomposer import spc
    from bitcomposer.spc import emulate
    run = emulate.run(spc.read(snap_path), seconds, audio=True, mute=mute)
    pcm = run.audio
    if crop:
        a, b = (max(0, int(crop[0] * RATE)) * FRAME, int(crop[1] * RATE) * FRAME)
        pcm = pcm[a:b]
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)


def beat_seconds(beats, beat: float) -> float:
    """A time in beats to seconds on a list of beat times."""
    if len(beats) < 2:
        return beat
    if beat <= 0:
        return beats[0] + beat * (beats[1] - beats[0])
    k = int(beat)
    if k + 1 < len(beats):
        return beats[k] + (beat - k) * (beats[k + 1] - beats[k])
    return beats[-1] + (beat - (len(beats) - 1)) * (beats[-1] - beats[-2])


def _song_grid(db, sid):
    beats, bars = array("d"), array("d")
    b = db.execute("SELECT beats, bars FROM beats WHERE song = ?", (sid,)).fetchone()
    if b:
        beats.frombytes(b[0])
        bars.frombytes(b[1])
    return beats, bars


def cmd_drums(a) -> int:
    from bitcomposer.translate import store
    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    draw = json.load(open(a.draw))
    os.makedirs(a.out_dir, exist_ok=True)
    manifest = []
    for i, d in enumerate(draw, 1):
        key = d["key"]
        # the song and voice that hit this sample most, on a grid where one exists
        places = db.execute("SELECT v.song, v.voice, v.notes, s.idx, g.folder, g.file, g.game, g.title, g.bpm FROM samples s "
                            "JOIN voices v ON v.song = s.song JOIN songs g ON g.id = s.song WHERE s.key = ? AND v.role = 'drums'",
                            (key,)).fetchall()
        best = None
        for p in places:
            notes = [n for n in store.unpack(p["notes"]) if int(n[5]) == p["idx"]]
            if len(notes) >= 3 and (best is None or (p["bpm"] is not None, len(notes)) > (best[0]["bpm"] is not None, len(best[1]))):
                best = (p, notes)
        if best is None:
            print(f"d{i:02d}: no place with three hits for {key[:10]}")
            continue
        p, notes = best
        beats, _ = _song_grid(db, p["song"])
        others = [n for n in store.unpack(p["notes"]) if int(n[5]) != p["idx"]]
        # the 4 s window (in the song's seconds) with the most hits of this sample and none of others
        times = sorted(beat_seconds(beats, n[0]) if len(beats) > 1 else n[0] for n in notes)
        other_times = sorted(beat_seconds(beats, n[0]) if len(beats) > 1 else n[0] for n in others)
        best_w = None
        for t0 in times:
            inside = [t for t in times if t0 <= t < t0 + 4.0]
            clash = sum(1 for t in other_times if t0 - 0.05 <= t < t0 + 4.0)
            score = (clash == 0, len(inside), -t0)
            if best_w is None or score > best_w[0]:
                best_w = (score, t0, len(inside), clash)
        _, t0, hits, clash = best_w
        start, end = max(0.0, t0 - 0.25), t0 + 4.5
        snap = os.path.join(a.spc_root, p["folder"], p["file"])
        name = f"d{i:02d}"
        solo = os.path.join(a.out_dir, f"{name} alone.ogg")
        mix = os.path.join(a.out_dir, f"{name} in the song.ogg")
        if not os.path.exists(solo):
            wav = os.path.join(a.out_dir, f"{name}-solo.wav")
            render(snap, end, wav, mute=0xFF & ~(1 << p["voice"]), crop=(start, end))
            to_opus(wav, solo)
        if not os.path.exists(mix):
            wav = os.path.join(a.out_dir, f"{name}-mix.wav")
            render(snap, end, wav, crop=(start, end))
            to_opus(wav, mix)
        manifest.append({"n": name, "key": key, "game": p["game"], "title": p["title"], "voice": p["voice"], "from": round(start, 2),
                         "to": round(end, 2), "hits_in_clip": hits, "other_sounds_in_clip": clash, "hits_total": d["hits"],
                         "alone": os.path.basename(solo), "in_song": os.path.basename(mix)})
        print(f"{name}: {p['game']} / {p['title']} voice {p['voice']} at {start:.1f} s, {hits} hits" + (f", {clash} other sounds" if clash else ""))
    with open(os.path.join(a.out_dir, "drum-set.json"), "w") as f:
        json.dump(manifest, f, indent=0)
    return 0


def cmd_tune(a) -> int:
    from bitcomposer.translate import store
    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    os.makedirs(a.out_dir, exist_ok=True)
    manifest = []
    for i, (game, title) in enumerate(TUNE_SET, 1):
        row = db.execute("SELECT id, folder, file, bpm, meter, seconds, loop_bar, loop_seconds FROM songs WHERE game = ? AND title = ?",
                         (game, title)).fetchone()
        if row is None:
            print(f"not in the readings: {game} / {title}")
            continue
        beats, bars = _song_grid(db, row["id"])
        length = 90.0
        if row["loop_bar"] is not None and row["loop_seconds"] and row["loop_bar"] < len(bars):
            length = bars[row["loop_bar"]] + row["loop_seconds"] + (bars[1] - bars[0] if len(bars) > 1 else 2.0)
        length = min(120.0, length, row["seconds"])
        voices = {}
        for v in db.execute("SELECT voice, role, of, notes FROM voices WHERE song = ? ORDER BY voice", (row["id"],)):
            n = len(store.unpack(v["notes"]))
            if n:
                voices[v["voice"]] = {"role": v["role"], "of": v["of"], "notes": n}
        name = f"t{i:02d} {game} - {title}"
        snap = os.path.join(a.spc_root, row["folder"], row["file"])
        files = {}
        mix = os.path.join(a.out_dir, f"{name} - mix.ogg")
        if not os.path.exists(mix):
            wav = os.path.join(a.out_dir, f"{name}-mix.wav")
            render(snap, length, wav)
            to_opus(wav, mix)
        files["mix"] = os.path.basename(mix)
        for v in sorted(voices):
            out = os.path.join(a.out_dir, f"{name} - voice {v + 1}.ogg")
            if not os.path.exists(out):
                wav = os.path.join(a.out_dir, f"{name}-v{v}.wav")
                render(snap, length, wav, mute=0xFF & ~(1 << v))
                to_opus(wav, out)
            files[str(v + 1)] = os.path.basename(out)
        manifest.append({"n": f"{i:02d}", "game": game, "title": title, "seconds": round(length, 2), "bpm": round(row["bpm"] or 0, 1),
                         "files": files, "voices": {str(v + 1): voices[v] for v in sorted(voices)}})
        print(f"{name}: {length:.0f} s, voices {sorted(v + 1 for v in voices)}")
    with open(os.path.join(a.out_dir, "tune-set.json"), "w") as f:
        json.dump(manifest, f, indent=0)
    return 0


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
        # the harmony alone: the voices the readings call the tune, the counter-line and the drums
        # muted (and a voice doubling one of those), so the chords can be heard on their own
        roles = {v: (r, of) for v, r, of in db.execute("SELECT voice, role, of FROM voices WHERE song = ?", (row["id"],))}
        quiet = {v for v, (r, _) in roles.items() if r in ("melody", "counter", "drums")}
        quiet |= {v for v, (r, of) in roles.items() if r == "double" and of in quiet}
        harmony = os.path.join(a.out_dir, name + " - harmony.ogg")
        if not os.path.exists(harmony):
            wav_h = os.path.join(a.out_dir, name + "-harmony.wav")
            render(os.path.join(a.spc_root, folder, stem + ".spc"), length, wav_h, mute=sum(1 << v for v in quiet))
            to_opus(wav_h, harmony)
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
        manifest.append({"n": f"{i:02d}", "game": row["game"], "title": row["title"], "file": name + ".ogg",
                         "harmony_file": name + " - harmony.ogg", "muted_voices": sorted(quiet), "folder": folder,
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
    p = sub.add_parser("drums")
    p.add_argument("spc_root")
    p.add_argument("db")
    p.add_argument("draw")
    p.add_argument("out_dir")
    p.set_defaults(run=cmd_drums)
    p = sub.add_parser("tune")
    p.add_argument("spc_root")
    p.add_argument("db")
    p.add_argument("out_dir")
    p.set_defaults(run=cmd_tune)
    a = ap.parse_args(argv)
    return a.run(a)


if __name__ == "__main__":
    sys.exit(main())
