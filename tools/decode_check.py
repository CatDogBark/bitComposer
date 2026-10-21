"""The readings against an independent decode of the same songs (phase 1 of docs/IDIOM.md).

VGMTrans reads a driver's sequence data to MIDI by code that shares nothing with the emulator or
the readers: the written tempo, the notes as written (onset, pitch, length), and, converted with
no repeat and with one, where the song loops. This tool matches those MIDIs to the songs as the
SNES chip played them (the decoder's notes) and to the readings (the beat, the loop), and says
where they agree and where they do not. A developer tool, like spc_check.py; the MIDIs and the
notes it caches stay on the machine with the readings.

    python tools/decode_check.py notes SPC_ROOT NOTES_DIR [--workers N]
        the decoder's notes of every song under SPC_ROOT (game folders), cached as JSON
    python tools/decode_check.py compare --notes NOTES_DIR --midi0 DIR --midi1 DIR --db READINGS.db
                                         --out REPORT.json [--tolerance 0.02]
        per song: the time offset between the two decodes, the tempo written and read, the loop's
        end and start both ways, the share of written notes matched by a played one, the pitch
        agreement after one offset per sample, and the written lengths against the played
    python tools/decode_check.py report REPORT.json [--game NAME] [--fails]
        the tables per game, and the songs outside the tolerances

MIDI0 and MIDI1 hold one MIDI per song, named like the SPC with .mid, under the same game folders,
converted with no loop repeat and with one.
"""
import argparse
import glob
import json
import math
import os
import sqlite3
import statistics
import struct
import sys
from array import array
from collections import Counter, defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TOLERANCE = 0.02                     # seconds: a written note and a played one are the same within this
LOOP_NOTES = 24                      # written notes of the repeat's tail aligned with the body to find the loop's start


# ── MIDI ──

def _varlen(data: bytes, i: int) -> tuple[int, int]:
    v = 0
    while True:
        b = data[i]
        i += 1
        v = (v << 7) | (b & 0x7F)
        if not b & 0x80:
            return v, i


def read_midi(path: str) -> dict:
    """A standard MIDI file as notes in seconds: {"notes": [(start, end, pitch, track, channel,
    velocity)], "tempos": [(seconds, bpm)], "markers": [(seconds, text)], "programs":
    {(track, channel): [program, ...]}, "end": seconds}."""
    data = open(path, "rb").read()
    if data[:4] != b"MThd":
        raise ValueError(f"{path}: not a MIDI file")
    length = struct.unpack(">I", data[4:8])[0]
    fmt, ntrk, division = struct.unpack(">HHH", data[8:14])
    if division & 0x8000:
        raise ValueError(f"{path}: SMPTE time division")
    pos = 8 + length
    tracks, tempos, markers = [], [], []
    for t in range(ntrk):
        if data[pos:pos + 4] != b"MTrk":
            break
        tlen = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        chunk = data[pos + 8:pos + 8 + tlen]
        pos += 8 + tlen
        i, tick, status = 0, 0, 0
        events = []
        while i < len(chunk):
            dt, i = _varlen(chunk, i)
            tick += dt
            b = chunk[i]
            if b == 0xFF:
                kind = chunk[i + 1]
                n, j = _varlen(chunk, i + 2)
                body = chunk[j:j + n]
                i = j + n
                if kind == 0x51 and n == 3:
                    tempos.append((tick, 60e6 / int.from_bytes(body, "big")))
                elif kind in (0x01, 0x06):
                    markers.append((tick, body.decode("latin-1", "replace")))
                elif kind == 0x2F:
                    events.append((tick, "end", None, None))
                continue
            if b in (0xF0, 0xF7):
                n, j = _varlen(chunk, i + 1)
                i = j + n
                continue
            if b & 0x80:
                status = b
                i += 1
            kind, ch = status & 0xF0, status & 0x0F
            if kind in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                d1, d2 = chunk[i], chunk[i + 1]
                i += 2
                if kind == 0x90 and d2 > 0:
                    events.append((tick, "on", ch, (d1, d2)))
                elif kind == 0x80 or kind == 0x90:
                    events.append((tick, "off", ch, (d1, 0)))
            elif kind in (0xC0, 0xD0):
                d1 = chunk[i]
                i += 1
                if kind == 0xC0:
                    events.append((tick, "program", ch, d1))
        tracks.append(events)
    tempos.sort()
    if not tempos or tempos[0][0] > 0:
        tempos.insert(0, (0, 120.0))

    def seconds(tick: int) -> float:                 # through the tempo map
        s, last_tick, bpm = 0.0, 0, tempos[0][1]
        for t_tick, t_bpm in tempos:
            if t_tick >= tick:
                break
            s += (t_tick - last_tick) * 60.0 / (bpm * division)
            last_tick, bpm = t_tick, t_bpm
        return s + (tick - last_tick) * 60.0 / (bpm * division)

    notes, programs, end = [], defaultdict(list), 0.0
    for k, events in enumerate(tracks):
        open_ = {}
        for tick, kind, ch, v in events:
            if kind == "on":
                pitch, vel = v
                if (ch, pitch) in open_:              # retriggered: the first ends here
                    t0, vel0 = open_.pop((ch, pitch))
                    notes.append((seconds(t0), seconds(tick), pitch, k, ch, vel0))
                open_[(ch, pitch)] = (tick, vel)
            elif kind == "off":
                pitch, _ = v
                if (ch, pitch) in open_:
                    t0, vel0 = open_.pop((ch, pitch))
                    notes.append((seconds(t0), seconds(tick), pitch, k, ch, vel0))
            elif kind == "program":
                programs[(k, ch)].append(v)
            elif kind == "end":
                end = max(end, seconds(tick))
        for (ch, pitch), (t0, vel0) in open_.items():
            notes.append((seconds(t0), seconds(end if end else t0), pitch, k, ch, vel0))
    notes.sort()
    return {"notes": notes, "tempos": [(seconds(t), b) for t, b in tempos],
            "markers": [(seconds(t), s) for t, s in markers], "programs": dict(programs),
            "end": max([end] + [n[1] for n in notes]) if notes else end}


# ── the decoder's notes ──

def _decode(args) -> tuple[str, str | None]:
    path, out = args
    try:
        from bitcomposer import spc
        from bitcomposer.translate import events
        song = events.play(spc.read(path))
        rows = [(p.voice, round(p.start, 5), None if p.end is None else round(p.end, 5),
                 None if p.midi is None else round(p.midi, 3),
                 p.sample.key if p.sample else None, round(p.level, 4)) for p in song.notes]
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            json.dump({"seconds": song.seconds, "notes": rows}, f)
        return path, None
    except Exception as e:                           # one song's failure is reported, the rest go on
        return path, f"{type(e).__name__}: {e}"


def cmd_notes(a) -> int:
    jobs = []
    for folder in sorted(glob.glob(os.path.join(a.spc_root, "*/"))):
        game = os.path.basename(folder.rstrip("/"))
        for path in sorted(glob.glob(os.path.join(folder, "*.spc"))):
            out = os.path.join(a.notes_dir, game, os.path.basename(path)[:-4] + ".json")
            if not os.path.exists(out):
                jobs.append((path, out))
    print(f"{len(jobs)} songs to decode")
    failed = 0
    with Pool(a.workers) as pool:
        for i, (path, err) in enumerate(pool.imap_unordered(_decode, jobs), 1):
            if err:
                failed += 1
                print(f"FAILED {path}: {err}")
            if i % 100 == 0:
                print(f"  {i} done", flush=True)
    print(f"{len(jobs) - failed} decoded, {failed} failed")
    return 0


# ── matching ──

def _offset(written: list, played: list, tol: float) -> float:
    """The constant by which the written notes run ahead of (+) or behind (-) the played ones: the
    shift of the written onsets that puts the most of them within tol of a played onset, tried over
    the shifts that align any of the first written onsets with any of the first played ones."""
    w = sorted({round(n[0], 3) for n in written})
    p = sorted({round(n[0], 3) for n in played})
    if not w or not p:
        return 0.0
    cands = {0.0} | {pp - ww for ww in w[:12] for pp in p[:40] if abs(pp - ww) < 8.0}
    best, best_n = 0.0, -1
    for d in sorted(cands):
        j, n = 0, 0
        for ww in w:
            t = ww + d
            while j < len(p) and p[j] < t - tol:
                j += 1
            if j < len(p) and abs(p[j] - t) <= tol:
                n += 1
        if n > best_n or (n == best_n and abs(d) < abs(best)):
            best, best_n = d, n
    return best


def _assign_tracks(written: list, played: list, shift: float, tol: float) -> dict:
    """Which played voice each written track is: the voice its onsets coincide with most."""
    by_voice = defaultdict(list)
    for n in played:
        by_voice[n[0]].append(n[1])
    for v in by_voice:
        by_voice[v].sort()
    out = {}
    for k in {n[3] for n in written}:
        onsets = sorted({round(n[0] + shift, 3) for n in written if n[3] == k})
        score = Counter()
        for v, starts in by_voice.items():
            j = 0
            for t in onsets:
                while j < len(starts) and starts[j] < t - tol:
                    j += 1
                if j < len(starts) and abs(starts[j] - t) <= tol:
                    score[v] += 1
        out[k] = score.most_common(1)[0][0] if score else None
    return out


def _match(written: list, played: list, shift: float, tol: float, voices: dict) -> list:
    """Pairs (written, played) by onset within the written track's voice, each played note used
    once; written notes with no pair are paired with None."""
    by_voice = defaultdict(list)
    for n in played:
        by_voice[n[0]].append(n)
    used = set()
    pairs = []
    for w in written:
        v = voices.get(w[3])
        t = w[0] + shift
        best, best_d = None, tol + 1
        for idx, pnote in enumerate(by_voice.get(v, ())):
            if (v, idx) in used:
                continue
            d = abs(pnote[1] - t)
            if d < best_d:
                best, best_d = (v, idx), d
            elif pnote[1] > t + tol:
                break
        if best and best_d <= tol:
            used.add(best)
            pairs.append((w, by_voice[best[0]][best[1]]))
        else:
            pairs.append((w, None))
    return pairs


def _loop_start(body: list, tail: list, end: float) -> float | None:
    """Where the song goes back to: the time in the body the repeat's first notes line up with
    (the same pitches at the same spacings, on the same tracks)."""
    head = sorted(tail)[:LOOP_NOTES]
    if len(head) < 4:
        return None
    first = head[0]
    cands = [b for b in body if b[2] == first[2] and b[3] == first[3]]
    best, best_n = None, 0
    for c in cands:
        d = c[0] - first[0]                          # body time = tail time + d
        n = 0
        for h in head:
            t = h[0] + d
            if any(abs(b[0] - t) < 0.015 and b[2] == h[2] and b[3] == h[3] for b in body):
                n += 1
        if n > best_n:
            best, best_n = c[0], n
    return best if best_n >= max(4, len(head) * 0.6) else None


def _beats_at(beats: array, t: float) -> float:
    if len(beats) < 2:
        return 0.0
    import bisect
    if t <= beats[0]:
        return (t - beats[0]) / (beats[1] - beats[0])
    if t >= beats[-1]:
        return len(beats) - 1 + (t - beats[-1]) / (beats[-1] - beats[-2])
    i = bisect.bisect_right(beats, t) - 1
    return i + (t - beats[i]) / (beats[i + 1] - beats[i])


def _ratio_class(r: float) -> str:
    for name, x in (("same", 1), ("double", 2), ("half", 0.5), ("x4", 4), ("quarter", 0.25),
                    ("x3", 3), ("third", 1 / 3), ("x1.5", 1.5), ("x2/3", 2 / 3)):
        if abs(r / x - 1) < 0.03:
            return name
    return "other"


def compare_song(game: str, name: str, notes_path: str, midi0: str, midi1: str | None, row, beats, bars,
                 tol: float) -> dict:
    played_doc = json.load(open(notes_path))
    played = [tuple(n) for n in played_doc["notes"]]
    m0 = read_midi(midi0)
    written = m0["notes"]
    out = {"game": game, "song": name, "written": len(written), "played": len(played)}
    if not written:
        out["status"] = "no notes written"
        return out
    shift = _offset(written, played, tol)
    voices = _assign_tracks(written, played, shift, tol)
    pairs = _match(written, played, shift, tol, voices)
    matched = [(w, p) for w, p in pairs if p is not None]
    out.update(shift=round(shift, 3), tracks={str(k): v for k, v in voices.items()},
               matched=len(matched), matched_share=len(matched) / len(written))
    # pitch: one constant offset per played sample
    by_sample = defaultdict(list)
    for w, p in matched:
        if p[3] is not None and p[4] is not None:
            by_sample[p[4]].append(p[3] - w[2])
    agree = total = 0
    samples = {}
    for key, offs in by_sample.items():
        mode = Counter(round(o) for o in offs).most_common(1)[0][0]
        frac = statistics.median(o - mode for o in offs)
        ok = sum(1 for o in offs if abs(o - mode) < 0.5)
        agree += ok
        total += len(offs)
        samples[key] = {"notes": len(offs), "offset": mode, "fraction": round(frac, 3), "agree": ok / len(offs)}
    out.update(pitch_pairs=total, pitch_agree=(agree / total) if total else None, samples=samples)
    # lengths: played against written, where both are known
    ratios = [((p[2] - p[1]) / (w[1] - w[0])) for w, p in matched if p[2] is not None and w[1] - w[0] > 0.02]
    out["length_ratio_median"] = round(statistics.median(ratios), 3) if ratios else None
    # tempo
    tempos = m0["tempos"]
    spans = [(tempos[i][1], (tempos[i + 1][0] if i + 1 < len(tempos) else m0["end"]) - tempos[i][0]) for i in range(len(tempos))]
    spans = [(b, d) for b, d in spans if d > 0]
    written_bpm = max(spans, key=lambda x: x[1])[0] if spans else None    # the tempo held longest
    out["tempo_written"] = round(written_bpm, 2) if written_bpm else None
    out["tempo_changes"] = len({round(b, 1) for b, _ in spans})
    read_bpm = row["bpm"]
    out["tempo_read"] = read_bpm
    if read_bpm and written_bpm:
        r = read_bpm / written_bpm
        out["tempo_ratio"] = round(r, 3)
        out["tempo_class"] = _ratio_class(r)
    # loop: the end from MIDI0, the start from MIDI1's tail
    out["loop_end_written"] = round(m0["end"] - shift, 3) if m0["end"] else None   # in played time
    if midi1 and os.path.exists(midi1):
        m1 = read_midi(midi1)
        if m1["end"] > m0["end"] + 0.5:
            tail = [n for n in m1["notes"] if n[0] >= m0["end"] - 0.005]
            body = [n for n in m1["notes"] if n[0] < m0["end"] - 0.005]
            s = _loop_start(body, tail, m0["end"])
            out["loop_start_written"] = round(s - shift, 3) if s is not None else None
            out["loops"] = True
        else:
            out["loops"] = False
    if row["loop_bar"] is not None and row["loop_seconds"] and bars is not None and row["loop_bar"] < len(bars):
        start = bars[row["loop_bar"]]
        out["loop_start_read"] = round(start, 3)
        out["loop_end_read"] = round(start + row["loop_seconds"], 3)
    if out.get("loop_end_written") and out.get("loop_end_read"):
        out["loop_end_diff"] = round(out["loop_end_read"] - out["loop_end_written"], 3)
    if out.get("loop_start_written") is not None and out.get("loop_start_read") is not None:
        out["loop_start_diff"] = round(out["loop_start_read"] - out["loop_start_written"], 3)
    if beats is not None and len(beats) > 1:
        out["beat_seconds"] = round(statistics.median(beats[i + 1] - beats[i] for i in range(len(beats) - 1)), 4)
    out["status"] = "ok"
    return out


def cmd_compare(a) -> int:
    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    rows = {(r["folder"], r["file"]): r for r in db.execute("SELECT id, folder, file, bpm, meter, loop_bar, loop_seconds, seconds FROM songs")}
    grids = {}
    for sid, b, r in db.execute("SELECT song, beats, bars FROM beats"):
        beats, bars = array("d"), array("d")
        beats.frombytes(b)
        bars.frombytes(r)
        grids[sid] = (beats, bars)
    results = []
    for notes_path in sorted(glob.glob(os.path.join(a.notes, "*", "*.json"))):
        game = os.path.basename(os.path.dirname(notes_path))
        name = os.path.basename(notes_path)[:-5]
        midi0 = os.path.join(a.midi0, game, name + ".mid")
        midi1 = os.path.join(a.midi1, game, name + ".mid") if a.midi1 else None
        row = rows.get((game, name + ".spc"))
        if row is None:
            folder_rows = [r for (f, _), r in rows.items() if f == game and r["file"] == name + ".spc"]
            row = folder_rows[0] if folder_rows else None
        if not os.path.exists(midi0):
            results.append({"game": game, "song": name, "status": "not converted"})
            continue
        if row is None:
            results.append({"game": game, "song": name, "status": "not in the readings"})
            continue
        beats, bars = grids.get(row["id"], (None, None))
        try:
            results.append(compare_song(game, name, notes_path, midi0, midi1, row, beats, bars, a.tolerance))
        except Exception as e:
            results.append({"game": game, "song": name, "status": f"error: {type(e).__name__}: {e}"})
    with open(a.out, "w") as f:
        json.dump(results, f, indent=0)
    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f"{len(results)} songs, {ok} compared, {sum(1 for r in results if r.get('status') == 'not converted')} not converted")
    return 0


# ── report ──

def _pct(n, d) -> str:
    return f"{100 * n / d:3.0f} %" if d else "  - "


def cmd_report(a) -> int:
    results = json.load(open(a.report))
    if a.game:
        results = [r for r in results if r["game"] == a.game]
    games = defaultdict(list)
    for r in results:
        games[r["game"]].append(r)
    print(f"{'game':24s} {'songs':>5s} {'conv':>5s} {'tempo same/2x/½/other':>22s} {'loop end ≤1 beat':>16s} {'start ≤1 bar':>12s} {'notes matched':>13s} {'pitch agree':>11s} {'len ratio':>9s}")
    tot = Counter()
    for game, rs in sorted(games.items()):
        ok = [r for r in rs if r.get("status") == "ok"]
        tc = Counter(r.get("tempo_class") for r in ok if r.get("tempo_class"))
        loop_end = [r for r in ok if r.get("loop_end_diff") is not None]
        end_ok = sum(1 for r in loop_end if abs(r["loop_end_diff"]) <= r.get("beat_seconds", 0.5))
        loop_start = [r for r in ok if r.get("loop_start_diff") is not None]
        start_ok = sum(1 for r in loop_start if abs(r["loop_start_diff"]) <= 4 * r.get("beat_seconds", 0.5))
        notes_share = statistics.median(r["matched_share"] for r in ok) if ok else None
        pitch = [r["pitch_agree"] for r in ok if r.get("pitch_agree") is not None]
        lens = [r["length_ratio_median"] for r in ok if r.get("length_ratio_median")]
        print(f"{game[:24]:24s} {len(rs):5d} {len(ok):5d} "
              f"{tc['same']:5d}/{tc['double'] + tc['x4']:3d}/{tc['half'] + tc['quarter']:3d}/{sum(tc.values()) - tc['same'] - tc['double'] - tc['x4'] - tc['half'] - tc['quarter']:3d}"
              f"{'':6s}{end_ok:4d}/{len(loop_end):<4d}{'':5s}{start_ok:4d}/{len(loop_start):<4d}"
              f"{'':3s}{(100 * notes_share if notes_share is not None else 0):8.1f} %  {(100 * statistics.median(pitch) if pitch else 0):8.1f} %  {(statistics.median(lens) if lens else 0):8.2f}")
        tot.update(songs=len(rs), ok=len(ok), end_ok=end_ok, end_n=len(loop_end), start_ok=start_ok, start_n=len(loop_start))
        tot.update({f"tempo_{k}": v for k, v in tc.items()})
    print(f"\n{tot['ok']} of {tot['songs']} songs compared; tempo same {tot['tempo_same']}, double {tot['tempo_double']}, half {tot['tempo_half']}, "
          f"other {tot['ok'] - tot['tempo_same'] - tot['tempo_double'] - tot['tempo_half'] - tot['tempo_x4'] - tot['tempo_quarter']}; "
          f"loop end within a beat {tot['end_ok']}/{tot['end_n']}, start within a bar {tot['start_ok']}/{tot['start_n']}")
    if a.fails:
        print("\nsongs outside the tolerances:")
        for r in results:
            if r.get("status") != "ok":
                if r.get("status") not in ("not converted",):
                    print(f"  {r['game']}/{r['song']}: {r['status']}")
                continue
            why = []
            if r.get("tempo_class") not in (None, "same", "double", "half"):
                why.append(f"tempo {r['tempo_read']} read vs {r['tempo_written']} written")
            if r["matched_share"] < 0.98:
                why.append(f"notes matched {100 * r['matched_share']:.0f} %")
            if r.get("pitch_agree") is not None and r["pitch_agree"] < 0.99:
                why.append(f"pitch {100 * r['pitch_agree']:.0f} %")
            if r.get("loop_end_diff") is not None and abs(r["loop_end_diff"]) > r.get("beat_seconds", 0.5):
                why.append(f"loop end off {r['loop_end_diff']:+.2f} s")
            if r.get("loop_start_diff") is not None and abs(r["loop_start_diff"]) > 4 * r.get("beat_seconds", 0.5):
                why.append(f"loop start off {r['loop_start_diff']:+.2f} s")
            if why:
                print(f"  {r['game']}/{r['song']}: " + "; ".join(why))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python tools/decode_check.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("notes")
    p.add_argument("spc_root")
    p.add_argument("notes_dir")
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    p.set_defaults(run=cmd_notes)
    p = sub.add_parser("compare")
    p.add_argument("--notes", required=True)
    p.add_argument("--midi0", required=True)
    p.add_argument("--midi1")
    p.add_argument("--db", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--tolerance", type=float, default=TOLERANCE)
    p.set_defaults(run=cmd_compare)
    p = sub.add_parser("report")
    p.add_argument("report")
    p.add_argument("--game")
    p.add_argument("--fails", action="store_true")
    p.set_defaults(run=cmd_report)
    a = ap.parse_args(argv)
    return a.run(a)


if __name__ == "__main__":
    sys.exit(main())
