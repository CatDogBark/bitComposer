"""The readings against an independent decode of the same songs (phase 1 of docs/IDIOM.md).

VGMTrans reads a driver's sequence data to MIDI by code that shares nothing with the emulator or
the readers: the notes as written (onset, pitch, length), the tempo where its reader emits one,
and, converted with no repeat and with one, where the song loops. This tool matches those MIDIs to
the songs as the SNES chip played them (the decoder's notes) and to the readings (the beat, the
loop), and says where they agree and where they do not. A developer tool, like spc_check.py; the
MIDIs and the notes it caches stay on the machine with the readings.

    python tools/decode_check.py notes SPC_ROOT NOTES_DIR [--workers N]
        the decoder's notes of every song under SPC_ROOT (game folders), cached as JSON
    python tools/decode_check.py compare --notes NOTES_DIR --midi0 DIR --midi1 DIR --db READINGS.db
                                         --out REPORT.json [--tolerance 0.02] [--workers N]
        per song: the time map between the two decodes (a shift and a rate: the two clocks differ
        by parts in ten thousand), the share of written notes a played note matches, the pitch
        agreement after one offset per sample, the written onsets on the readings' beat grid, the
        tempo written and read, the loop's length, end and start both ways, and the written lengths
        against the played
    python tools/decode_check.py report REPORT.json [--game NAME] [--fails]
        the tables per game, and the songs outside the tolerances

MIDI0 and MIDI1 hold one MIDI per song, named like the SPC with .mid, under the same game folders,
converted with no loop repeat and with one (tools/vgmtrans_batch.py).
"""
import argparse
import bisect
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
COARSE = 0.06                        # the first, looser match the time map is fitted from
LOOP_NOTES = 24                      # written notes of the repeat's tail aligned with the body to find the loop's start
GRID = 1 / 16                        # beats: a written onset this near a sixteenth or a triplet eighth is on the grid


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
    velocity)], "tempos": [(seconds, bpm)], "markers": [(seconds, text)], "division": ticks a
    quarter, "end": seconds}."""
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
                i += 1
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

    notes, end = [], 0.0
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
            elif kind == "end":
                end = max(end, seconds(tick))
        for (ch, pitch), (t0, vel0) in open_.items():
            notes.append((seconds(t0), seconds(end if end else t0), pitch, k, ch, vel0))
    notes.sort()
    return {"notes": notes, "tempos": [(seconds(t), b) for t, b in tempos], "division": division,
            "markers": [(seconds(t), s) for t, s in markers],
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

class Played:
    """The played notes indexed by onset."""

    def __init__(self, notes: list):
        self.notes = sorted(notes, key=lambda n: n[1])
        self.starts = [n[1] for n in self.notes]
        self.used = set()

    def near(self, t: float, tol: float) -> list[int]:
        i = bisect.bisect_left(self.starts, t - tol)
        out = []
        while i < len(self.starts) and self.starts[i] <= t + tol:
            if i not in self.used:
                out.append(i)
            i += 1
        return out


def _shift(written: list, played: Played, tol: float) -> float:
    """The constant by which the played onsets run behind the written ones, before the rate is
    known: the shift of the written onsets that puts the most of the first stretch within tol of a
    played onset, tried over the shifts aligning any early written onset with any early played one."""
    w = sorted({round(n[0], 3) for n in written})[:60]
    p = sorted({round(s, 3) for s in played.starts})
    if not w or not p:
        return 0.0
    cands = {0.0} | {pp - ww for ww in w[:12] for pp in p[:60] if abs(pp - ww) < 8.0}
    best, best_n = 0.0, -1
    for d in sorted(cands):
        n = sum(1 for ww in w if played.near(ww + d, tol))
        if n > best_n or (n == best_n and abs(d) < abs(best)):
            best, best_n = d, n
    return best


WINDOW = 4.0                         # seconds of written time a local shift is found over
REACH = 0.5                          # seconds either side of the global shift a local shift may sit


class TimeMap:
    """played time as a function of written time, piecewise: the two decodes differ by a shift that
    drifts (clocks apart by parts in ten thousand) and sometimes jumps (one decode slips a note, or
    a stretch of the written song was never played, as an intro after a dump taken mid-song). Each
    window of written onsets gets the shift that puts the most of them within tol of a played
    onset; windows with too few agreeing onsets are unaligned and take their neighbours' shift."""

    def __init__(self, written: list, played: Played, shift0: float, tol: float):
        onsets = sorted({round(n[0], 4) for n in written})
        self.points = []                             # (written time, shift), aligned windows
        self.unaligned = 0                           # written onsets in windows no shift fits
        start = onsets[0] if onsets else 0.0
        while onsets and start <= onsets[-1]:
            group = [t for t in onsets if start <= t < start + WINDOW]
            start += WINDOW
            if len(group) < 3:
                self.unaligned += len(group)
                continue
            bins = Counter()
            for t in group:                          # every played onset within reach votes for its shift
                x = shift0 + t
                i = bisect.bisect_left(played.starts, x - REACH)
                while i < len(played.starts) and played.starts[i] <= x + REACH:
                    bins[round((played.starts[i] - x) / 0.004)] += 1
                    i += 1
            if not bins:
                self.unaligned += len(group)
                continue
            centre = bins.most_common(1)[0][0] * 0.004
            res = []
            for t in group:
                x = shift0 + t + centre
                i = bisect.bisect_left(played.starts, x)
                cands = [played.starts[j] - x for j in (i - 1, i) if 0 <= j < len(played.starts)]
                if cands and abs(min(cands, key=abs)) <= 2 * tol:
                    res.append(min(cands, key=abs))
            if len(res) < max(3, 0.5 * len(group)):
                self.unaligned += len(group)
                continue
            self.points.append((statistics.median(group), shift0 + centre + statistics.median(res)))
        if not self.points:
            self.points = [(0.0, shift0)]
        self.shift = self.points[0][1]
        shifts = [s for _, s in self.points]
        self.jumps = [(round(self.points[i][0], 1), round(shifts[i] - shifts[i - 1], 3))
                      for i in range(1, len(shifts)) if abs(shifts[i] - shifts[i - 1]) > 0.015]
        span = self.points[-1][0] - self.points[0][0]
        self.rate = 1.0 + (shifts[-1] - shifts[0]) / span if span > 20 and not self.jumps else 1.0

    def __call__(self, t: float) -> float:
        pts = self.points
        if t <= pts[0][0]:
            return t + pts[0][1]
        if t >= pts[-1][0]:
            return t + pts[-1][1]
        i = bisect.bisect_right([p[0] for p in pts], t) - 1
        (t0, s0), (t1, s1) = pts[i], pts[i + 1]
        return t + s0 + (s1 - s0) * (t - t0) / (t1 - t0)


def _match(written: list, played: Played, tmap, tol: float) -> list:
    """Pairs (written, played) by onset, any voice, each played note used once. Where more than one
    played note is within tol, the one whose pitch stands at the offset its sample has shown so
    far (a whole number of semitones apart) is taken, else the nearest in time. Two passes: the
    unambiguous pairs first, which teach each sample's offset."""
    offsets = defaultdict(Counter)                   # sample key -> rounded offset -> count
    pairs = [None] * len(written)
    order = sorted(range(len(written)), key=lambda i: written[i][0])
    ambiguous = []
    for i in order:
        w = written[i]
        c = played.near(tmap(w[0]), tol)
        if len(c) == 1:
            j = c[0]
            played.used.add(j)
            p = played.notes[j]
            pairs[i] = p
            if p[3] is not None:
                offsets[p[4]][round(p[3] - w[2])] += 1
        elif c:
            ambiguous.append(i)
    for i in ambiguous:
        w = written[i]
        t = tmap(w[0])
        c = played.near(t, tol)
        if not c:
            continue

        def score(j):
            p = played.notes[j]
            fit = 1.0
            if p[3] is not None and offsets.get(p[4]):
                mode = offsets[p[4]].most_common(1)[0][0]
                fit = 0.0 if abs((p[3] - w[2]) - mode) < 0.5 else 1.0
            elif p[3] is not None:
                frac = abs((p[3] - w[2]) - round(p[3] - w[2]))
                fit = 0.3 if frac < 0.3 else 1.0
            return (fit, abs(played.starts[j] - t))

        j = min(c, key=score)
        played.used.add(j)
        p = played.notes[j]
        pairs[i] = p
        if p[3] is not None:
            offsets[p[4]][round(p[3] - w[2])] += 1
    return [(w, p) for w, p in zip(written, pairs)]


def _loop_start(body: list, tail: list) -> float | None:
    """Where the song goes back to: the time in the body the repeat's first notes line up with
    (the same pitches at the same spacings, on the same tracks)."""
    head = sorted(tail)[:LOOP_NOTES]
    if len(head) < 4:
        return None
    index = defaultdict(list)                        # (pitch, track) -> onsets, sorted
    for b in body:
        index[(b[2], b[3])].append(b[0])
    for k in index:
        index[k].sort()

    def hit(h, t: float) -> bool:
        onsets = index.get((h[2], h[3]), ())
        i = bisect.bisect_left(onsets, t - 0.015)
        return i < len(onsets) and onsets[i] < t + 0.015

    first = head[0]
    best, best_n = None, 0
    for start in index.get((first[2], first[3]), ()):
        d = start - first[0]                         # body time = tail time + d
        n = sum(1 for h in head if hit(h, h[0] + d))
        if n > best_n:
            best, best_n = start, n
    return best if best_n >= max(4, len(head) * 0.6) else None


def _beat_at(beats: list, t: float) -> float:
    if len(beats) < 2:
        return 0.0
    if t <= beats[0]:
        return (t - beats[0]) / (beats[1] - beats[0])
    if t >= beats[-1]:
        return len(beats) - 1 + (t - beats[-1]) / (beats[-1] - beats[-2])
    i = bisect.bisect_right(beats, t) - 1
    return i + (t - beats[i]) / (beats[i + 1] - beats[i])


def _grid(onsets: list, beats: list) -> dict:
    """Where the written onsets fall on the readings' beat grid: the share on a beat, within GRID of
    a sixteenth, of a triplet eighth, and off both."""
    out = Counter()
    for t in onsets:
        b = _beat_at(beats, t)
        f = b - math.floor(b)
        d16 = min(abs(f - k / 4) for k in range(5))
        d12 = min(abs(f - k / 3) for k in range(4))
        if min(f, 1 - f) <= GRID:
            out["beat"] += 1
        elif d16 <= GRID:
            out["sixteenth"] += 1
        elif d12 <= GRID:
            out["triplet"] += 1
        else:
            out["off"] += 1
    n = sum(out.values()) or 1
    return {k: out[k] / n for k in ("beat", "sixteenth", "triplet", "off")} | {"onsets": n}


def _ratio_class(r: float | None) -> str | None:
    if r is None:
        return None
    for name, x in (("same", 1), ("double", 2), ("half", 0.5), ("x4", 4), ("quarter", 0.25),
                    ("x3", 3), ("third", 1 / 3), ("x1.5", 1.5), ("x2/3", 2 / 3), ("x4/3", 4 / 3), ("x3/4", 0.75)):
        if abs(r / x - 1) < 0.03:
            return name
    return "other"


def compare_song(game: str, name: str, notes_path: str, midi0: str, midi1: str | None, row: dict,
                 beats: list | None, bars: list | None, tol: float) -> dict:
    played_doc = json.load(open(notes_path))
    played = Played([tuple(n) for n in played_doc["notes"]])
    m0 = read_midi(midi0)
    written = m0["notes"]
    out = {"game": game, "song": name, "written": len(written), "played": len(played.notes)}
    if not written:
        out["status"] = "no notes written"
        return out
    shift0 = _shift(written, played, COARSE)
    tmap = TimeMap(written, played, shift0, tol)
    pairs = _match(written, played, tmap, tol)
    matched = [(w, p) for w, p in pairs if p is not None]
    rate = tmap.rate
    out.update(shift=round(tmap.shift, 4), rate=round(rate, 6), jumps=tmap.jumps,
               unaligned_share=round(tmap.unaligned / len(written), 3),
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
        samples[key] = {"notes": len(offs), "offset": mode, "fraction": round(frac, 3), "agree": round(ok / len(offs), 3)}
    out.update(pitch_pairs=total, pitch_agree=(agree / total) if total else None, samples=samples)
    # lengths: played against written, where both are known and the written is not a grace note
    ratios = [((p[2] - p[1]) / ((w[1] - w[0]) * rate)) for w, p in matched if p[2] is not None and w[1] - w[0] > 0.02]
    out["length_ratio_median"] = round(statistics.median(ratios), 3) if ratios else None
    # the written onsets on the readings' grid
    if beats is not None and len(beats) > 1:
        out["grid"] = _grid([tmap(w[0]) for w in written], beats)
        out["beat_seconds"] = round(statistics.median(beats[i + 1] - beats[i] for i in range(len(beats) - 1)), 4)
    # tempo: the written meta (where the reader emits a real one) against the read
    tempos = m0["tempos"]
    spans = [(tempos[i][1], (tempos[i + 1][0] if i + 1 < len(tempos) else m0["end"]) - tempos[i][0]) for i in range(len(tempos))]
    spans = [(b, d) for b, d in spans if d > 0]
    written_bpm = max(spans, key=lambda x: x[1])[0] if spans else None
    out["tempo_written"] = round(written_bpm, 2) if written_bpm else None
    out["tempo_changes"] = len({round(b, 1) for b, _ in spans})
    out["tempo_read"] = row["bpm"]
    if row["bpm"] and written_bpm:
        out["tempo_ratio"] = round(row["bpm"] / written_bpm, 3)
        out["tempo_class"] = _ratio_class(out["tempo_ratio"])
    # the written unit: the commonest written length, in seconds of played time
    lengths = Counter(round((w[1] - w[0]) * rate, 3) for w in written if w[1] - w[0] > 0.01)
    if lengths:
        unit = lengths.most_common(1)[0][0]
        out["written_unit"] = unit
        if out.get("beat_seconds"):
            out["beat_over_unit"] = round(out["beat_seconds"] / unit, 2)
    # loop: the end from MIDI0, the start from MIDI1's tail, in played time
    end_w = tmap(m0["end"]) if m0["end"] else None
    out["loop_end_written"] = round(end_w, 3) if end_w else None
    out["loops"] = None
    if midi1 and os.path.exists(midi1):
        m1 = read_midi(midi1)
        if m1["end"] > m0["end"] + 0.5:
            tail = [n for n in m1["notes"] if n[0] >= m0["end"] - 0.005]
            body = [n for n in m1["notes"] if n[0] < m0["end"] - 0.005]
            s = _loop_start(body, tail)
            out["loops"] = True
            if s is not None:
                out["loop_start_written"] = round(tmap(s), 3)
                out["loop_len_written"] = round(tmap(m0["end"]) - tmap(s), 3)
        else:
            out["loops"] = False
    if row["loop_bar"] is not None and row["loop_seconds"] and bars is not None and row["loop_bar"] < len(bars):
        start = bars[row["loop_bar"]]
        out["loop_start_read"] = round(start, 3)
        out["loop_len_read"] = round(row["loop_seconds"], 3)
        out["loop_end_read"] = round(start + row["loop_seconds"], 3)
    if out.get("loop_end_written") and out.get("loop_end_read"):
        out["loop_end_diff"] = round(out["loop_end_read"] - out["loop_end_written"], 3)
    if out.get("loop_start_written") is not None and out.get("loop_start_read") is not None:
        out["loop_start_diff"] = round(out["loop_start_read"] - out["loop_start_written"], 3)
    if out.get("loop_len_written") and out.get("loop_len_read"):
        out["loop_len_class"] = _ratio_class(out["loop_len_read"] / out["loop_len_written"])
    elif out["loops"] and out.get("loop_len_read") is None:
        out["loop_len_class"] = "none read"
    elif out["loops"] is False and out.get("loop_len_read"):
        out["loop_len_class"] = "none written"
    out["status"] = "ok"
    return out


def _compare_job(args) -> dict:
    game, name, notes_path, midi0, midi1, row, beats, bars, tol = args
    try:
        return compare_song(game, name, notes_path, midi0, midi1, row, beats, bars, tol)
    except Exception as e:
        return {"game": game, "song": name, "status": f"error: {type(e).__name__}: {e}"}


def cmd_compare(a) -> int:
    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    rows = {}
    for r in db.execute("SELECT id, folder, file, bpm, meter, loop_bar, loop_seconds, seconds FROM songs"):
        rows[(os.path.basename(r["folder"].rstrip("/")), r["file"])] = dict(r)
    grids = {}
    for sid, b, r in db.execute("SELECT song, beats, bars FROM beats"):
        beats, bars = array("d"), array("d")
        beats.frombytes(b)
        bars.frombytes(r)
        grids[sid] = (list(beats), list(bars))
    results, jobs = [], []
    for notes_path in sorted(glob.glob(os.path.join(a.notes, "*", "*.json"))):
        game = os.path.basename(os.path.dirname(notes_path))
        name = os.path.basename(notes_path)[:-5]
        midi0 = os.path.join(a.midi0, game, name + ".mid")
        midi1 = os.path.join(a.midi1, game, name + ".mid") if a.midi1 else None
        row = rows.get((game, name + ".spc"))
        if not os.path.exists(midi0):
            results.append({"game": game, "song": name, "status": "not converted"})
            continue
        if row is None:
            results.append({"game": game, "song": name, "status": "not in the readings"})
            continue
        beats, bars = grids.get(row["id"], (None, None))
        jobs.append((game, name, notes_path, midi0, midi1, row, beats, bars, a.tolerance))
    with Pool(a.workers) as pool:
        for i, r in enumerate(pool.imap_unordered(_compare_job, jobs), 1):
            results.append(r)
            if i % 200 == 0:
                print(f"  {i} compared", flush=True)
    results.sort(key=lambda r: (r["game"], r["song"]))
    with open(a.out, "w") as f:
        json.dump(results, f, indent=0)
    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f"{len(results)} songs, {ok} compared, {sum(1 for r in results if r.get('status') == 'not converted')} not converted")
    return 0


# ── report ──

def _med(values, unit: str = "") -> str:
    values = [v for v in values if v is not None]
    return f"{statistics.median(values):.{2 if unit == '' else 0}f}{unit}" if values else "-"


def cmd_report(a) -> int:
    results = json.load(open(a.report))
    if a.game:
        results = [r for r in results if r["game"] == a.game]
    games = defaultdict(list)
    for r in results:
        games[r["game"]].append(r)
    # a reader whose written tempo is one value for most of a game's songs emits a default, not a tempo
    default_tempo = {}
    for game, rs in games.items():
        ts = [round(r["tempo_written"]) for r in rs if r.get("tempo_written")]
        if ts:
            top, n = Counter(ts).most_common(1)[0]
            default_tempo[game] = n / len(ts) > 0.5 and len(ts) >= 6
    print(f"{'game':22s} {'songs':>5s} {'cmp':>4s} {'notes':>6s} {'pitch':>6s} {'grid: beat/16th/trip/off':>24s}"
          f" {'tempo same/2x/½/other':>22s} {'loop len same/sub/other/none':>28s} {'end≤beat':>8s} {'len':>5s}")
    tot = Counter()
    for game, rs in sorted(games.items()):
        ok = [r for r in rs if r.get("status") == "ok"]
        notes = statistics.median(r["matched_share"] for r in ok) if ok else None
        pitch = [r["pitch_agree"] for r in ok if r.get("pitch_agree") is not None]
        grids = [r["grid"] for r in ok if r.get("grid")]
        g = {k: statistics.median(x[k] for x in grids) for k in ("beat", "sixteenth", "triplet", "off")} if grids else None
        tc = Counter(r.get("tempo_class") for r in ok if r.get("tempo_class"))
        same, dbl, half = tc["same"], tc["double"] + tc["x4"], tc["half"] + tc["quarter"]
        other = sum(tc.values()) - same - dbl - half
        lc = Counter(r.get("loop_len_class") for r in ok if r.get("loop_len_class"))
        l_same = lc["same"]
        l_sub = lc["half"] + lc["third"] + lc["quarter"]
        l_none = lc["none read"]
        l_other = sum(lc.values()) - l_same - l_sub - l_none - lc["none written"]
        loop_end = [r for r in ok if r.get("loop_end_diff") is not None and r.get("beat_seconds")]
        end_ok = sum(1 for r in loop_end if abs(r["loop_end_diff"]) <= r["beat_seconds"])
        lens = [r["length_ratio_median"] for r in ok if r.get("length_ratio_median")]
        flag = "*" if default_tempo.get(game) else " "
        print(f"{game[:22]:22s} {len(rs):5d} {len(ok):4d} {_med([notes]) if notes is not None else '-':>6s} {_med(pitch):>6s} "
              + (f"{g['beat']:5.2f}/{g['sixteenth']:4.2f}/{g['triplet']:4.2f}/{g['off']:4.2f}" if g else f"{'-':>22s}")
              + f"   {same:4d}/{dbl:3d}/{half:3d}/{other:3d}{flag}"
              + f"   {l_same:5d}/{l_sub:3d}/{l_other:5d}/{l_none:4d}{'':5s}{end_ok:3d}/{len(loop_end):<4d}{_med(lens):>5s}")
        tot.update(songs=len(rs), ok=len(ok), end_ok=end_ok, end_n=len(loop_end), l_same=l_same, l_sub=l_sub, l_other=l_other, l_none=l_none,
                   t_same=same, t_dbl=dbl, t_half=half, t_other=other)
    print(f"\n{tot['ok']} of {tot['songs']} songs compared. Tempo (* = the reader emits one default tempo for the game, not a measure): "
          f"same {tot['t_same']}, double {tot['t_dbl']}, half {tot['t_half']}, other {tot['t_other']}. "
          f"Loop length: same {tot['l_same']}, a sub-period of the written {tot['l_sub']}, other {tot['l_other']}, none read where one is written {tot['l_none']}; "
          f"end within a beat {tot['end_ok']}/{tot['end_n']}.")
    if a.fails:
        print("\nsongs outside the tolerances:")
        for r in results:
            if r.get("status") != "ok":
                if r.get("status") != "not converted":
                    print(f"  {r['game']}/{r['song']}: {r['status']}")
                continue
            why = []
            if r["matched_share"] < 0.98:
                why.append(f"notes matched {100 * r['matched_share']:.0f} %")
            if r.get("pitch_agree") is not None and r["pitch_agree"] < 0.99:
                why.append(f"pitch {100 * r['pitch_agree']:.0f} %")
            if r.get("grid") and r["grid"]["off"] > 0.1:
                why.append(f"off the grid {100 * r['grid']['off']:.0f} %")
            if r.get("tempo_class") not in (None, "same", "double", "half") and not default_tempo.get(r["game"]):
                why.append(f"tempo {r['tempo_read']:.0f} read vs {r['tempo_written']:.0f} written")
            if r.get("loop_len_class") not in (None, "same", "none written"):
                why.append(f"loop {r['loop_len_class']} (read {r.get('loop_len_read')} s, written {r.get('loop_len_written')} s)")
            elif r.get("loop_end_diff") is not None and r.get("beat_seconds") and abs(r["loop_end_diff"]) > r["beat_seconds"]:
                why.append(f"loop end off {r['loop_end_diff']:+.2f} s")
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
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
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
