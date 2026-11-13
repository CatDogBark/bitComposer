"""The lead by salience (round 64): which voice carries the tune, read from each voice rendered alone.

    python -m bitcomposer.translate.lead GAME SPC_FOLDER [--db PATH] [--window 9] [--dry-run] [--out DIR] [--workers N]

The readings pick a song's melody by variety and stepwise motion, with a voice's raw volume as the only loudness test (a
quarter of the loudest voice's, under a square root in the score). A buried voice with a wide line wins over an audible
one: in FFVI the labelled melody sits 9 dB or more under the whole in one song of seven, and the FFVI Lead Check
(2026-10-29), each voice heard alone, named another voice the tune in every one of those and agreed with the label in
every song where the melody was within 8 dB. So the lead is the labelled melody where it is heard, within LEAD_WINDOW
dB of the loudest tonal voice as each renders alone (K-weighted loudness over the first minute, the Song Check method),
else the most varied heard voice (pitch-class entropy, then loudness) among those that are present, not a bass and below
the tune's ceiling. The voice that was the melody becomes a counter-line, or an accompaniment where the song has a
counter already. The rule matched 12 of the Lead Check's 14 picks and relabels 9 FFVI songs of 66.

This pass renders each tonal voice of each song alone (the emulator and ffmpeg's libopenmpt needed), keeps every voice's
loudness as a readings feature (source "render", name "voice_lufs_<voice>"), and rewrites the voices' roles in the
readings; the roles it changed are kept too (source "lead", name "was_melody" / "now_melody"), so the pass is repeatable
and reversible. A song read again by a newer translator loses the relabel: run the pass again after a re-read, before
the tables are counted. `passed` says whether a game's readings have been through it, and the tables' source keeps the
answer (packtables.build), so a vocabulary counted without the pass says so.
"""
import argparse
import glob
import io
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import tempfile
from collections import Counter
from multiprocessing import Pool

from . import rhythm, store
from . import roles as R

LEAD_WINDOW = 9.0                     # dB: a labelled melody heard within this of the loudest tonal voice keeps the lead
LEAD_VARIETY = 2.0                    # pitch-class entropy a heard voice needs to be a tune
LEAD_PRESENT = 0.25                   # share of the song's beats a heard voice needs a note on
LEAD_CEILING = 84                     # the tune's highest median pitch (roles.MELODY_CEILING)
SECONDS = 60.0


def lufs(path: str, seconds: float = SECONDS) -> float | None:
    """A module's K-weighted integrated loudness over its first `seconds` (ffmpeg's ebur128), or None."""
    o = subprocess.run(["ffmpeg", "-nostats", "-t", str(seconds), "-i", path, "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", o)
    return float(m.group(1)) if m else None


def features_of(notes: list, nbeats: int) -> dict:
    """What the lead rule asks of a voice's notes (start, length, midi, key): pitch-class entropy, presence, median pitch."""
    seq = [round(n[2]) for n in notes if not math.isnan(n[2])]
    counts = Counter(m % 12 for m in seq)
    total = sum(counts.values())
    pc = -sum(v / total * math.log2(v / total) for v in counts.values()) if total else 0.0
    return {"pc": pc, "presence": len({math.floor(n[0]) for n in notes}) / max(1, nbeats), "median": statistics.median(seq) if seq else None, "notes": len(notes)}


def lead_of(voices: dict, window: float = LEAD_WINDOW) -> tuple[int | None, str]:
    """The voice that carries the tune. `voices`: {voice: {"role", "lufs", "pc", "presence", "median"}} for the song's
    tonal voices (no drums, no doubles). Returns (voice, why): the labelled melody where heard, else the most varied heard
    voice ("relabel"), else the label ("nothing heard"); (None, "no melody") without a melody."""
    heard_all = {v: x for v, x in voices.items() if x.get("lufs") is not None}
    mel = next((v for v, x in voices.items() if x["role"] == R.MELODY and x.get("of") is None), None)   # a layer of the tune is never the lead (round 90)
    if mel is None:
        return None, "no melody"
    if not heard_all:
        return mel, "nothing rendered"
    loud = max(x["lufs"] for x in heard_all.values())
    if mel in heard_all and heard_all[mel]["lufs"] >= loud - window:
        return mel, "label kept"
    heard = [v for v, x in heard_all.items() if x["lufs"] >= loud - window and x["role"] != R.BASS and x.get("of") is None]
    varied = [v for v in heard if x_fits(heard_all[v])] or heard
    if not varied:
        return mel, "nothing heard"
    return max(varied, key=lambda v: (round(heard_all[v]["pc"], 1), heard_all[v]["lufs"])), "relabel"


def x_fits(x: dict) -> bool:
    return x["pc"] >= LEAD_VARIETY and x["presence"] >= LEAD_PRESENT and (x["median"] or 0) <= LEAD_CEILING


def relabel_plan(voices: dict, lead: int) -> dict:
    """{voice: new role} for a song whose lead is `lead`: the lead becomes the melody; the voice that was the melody
    becomes a counter-line, or an accompaniment where the song has a counter already."""
    mel = next((v for v, x in voices.items() if x["role"] == R.MELODY and x.get("of") is None), None)
    if lead is None or lead == mel:
        return {}
    has_counter = any(x["role"] == R.COUNTER for v, x in voices.items() if v != lead)
    plan = {lead: R.MELODY, mel: R.ACCOMP if has_counter else R.COUNTER}
    for v, x in voices.items():                              # the old tune's layers (round 90) go back to the parts they read as
        if x.get("of") == mel and x.get("was"):
            plan[v] = x["was"]
    return plan


def render_voices(spc_path: str, song, out_dir: str, seconds: float = SECONDS, keep: bool = True) -> dict:
    """Each tonal voice of the song rendered alone from its SPC: {voice: lufs}; the whole under "whole". The renders
    stay in `out_dir` when `keep`, else each is removed as soon as it is measured."""
    from .. import spc
    from ..spc import convert
    snap = spc.read(spc_path)
    score = convert.score_of(snap, seconds=seconds + 10.0, fade=0.0)

    def measured(part, path):
        try:
            convert.render(part, path)
            return lufs(path, seconds)
        finally:
            if not keep and os.path.exists(path):
                os.remove(path)

    out = {"whole": measured(score, os.path.join(out_dir, f"{song.sid}.it"))}
    for v, (role, ns) in song.voice_notes.items():
        if role in (R.DRUMS, R.DOUBLE) or not ns:
            continue
        notes = [n for n in score.notes if n.voice == v]
        if not notes:
            continue
        out[v] = measured(convert.Score(**{**score.__dict__, "notes": notes}), os.path.join(out_dir, f"{song.sid}-v{v}.it"))
    return out


class _Voices:
    """What render_voices asks of a song, small enough to hand to another process: its id, and each voice's role and
    whether it has notes."""

    def __init__(self, song):
        self.sid = song.sid
        self.voice_notes = {v: (role, bool(ns)) for v, (role, ns) in song.voice_notes.items()}


def _render(job):
    """One song's voices rendered in a process of the pool: ("ok", {voice: lufs}), or ("error", why) for a song the
    converter cannot score."""
    spc_path, voices, out_dir, keep = job
    try:
        return "ok", render_voices(spc_path, voices, out_dir, keep=keep)
    except Exception as e:                                  # noqa: BLE001  said by run(), in the song's turn
        return "error", str(e)


def run(db, game: str, spc_folder: str, window: float = LEAD_WINDOW, dry_run: bool = False, out_dir: str | None = None, say=print,
        progress=None, workers: int | None = None) -> dict:
    """The pass over a game's songs: render, decide, store. Returns {sid: (title, why, plan)}. The songs are rendered
    `workers` at a time (default: all the machine's cores but one), each in a process of its own, and decided and
    stored here in the readings' order, so the pass gives the same readings on any number of them.
    progress(done, total) after each song."""
    songs, _ = rhythm.load(db, game)
    files = {r[0]: r[1] for r in db.execute("SELECT id, file FROM songs WHERE game = ?", (game,)).fetchall()}
    result = {}
    keep = out_dir is not None
    work = out_dir or tempfile.mkdtemp(prefix="bitcomposer-lead-")
    os.makedirs(work, exist_ok=True)
    jobs = []                                               # a song's render, or None without its SPC file
    for s in songs:
        f = files.get(s.sid)
        found = glob.glob(os.path.join(spc_folder, "**", os.path.basename(f or "")), recursive=True) if f else []
        jobs.append((found[0], _Voices(s), work, keep) if found else None)
    todo = [j for j in jobs if j]
    count = min(workers or max(1, (os.cpu_count() or 2) - 1), len(todo))

    def settle(s, outcome):
        if outcome is None:
            say(f"  {s.title}: no SPC file under {spc_folder}")
            return
        if outcome[0] == "error":                           # a song the converter cannot score is left as read
            say(f"  {s.title}: not rendered ({outcome[1]})")
            return
        rendered = outcome[1]
        nbeats = int(s.bars[-1][1] - s.bars[0][0]) if s.bars else 1
        voices = {}
        evidence = {voice: ev for voice, _, _, ev in s.voices}
        for v, (role, ns) in s.voice_notes.items():
            if v in rendered and role not in (R.DRUMS, R.DOUBLE):
                voices[v] = {"role": role, "lufs": rendered[v], "of": s.voice_of.get(v), "was": (evidence.get(v) or {}).get("was"),
                             **features_of(sorted(ns), nbeats)}
        lead, why = lead_of(voices, window)
        plan = relabel_plan(voices, lead)
        result[s.sid] = (s.title, why, plan)
        say(f"  {s.title}: {why}" + (f"; voice {lead} ({voices[lead]['role']}, {voices[lead]['lufs'] - rendered['whole']:+.1f} dB) leads: " + ", ".join(f"v{v} -> {r}" for v, r in plan.items()) if plan else ""))
        if dry_run:
            return
        for v, l in rendered.items():
            if v != "whole" and l is not None:
                db.execute("INSERT OR REPLACE INTO features VALUES (?,?,?,?)", (s.sid, "render", f"voice_lufs_{v}", l))
        if plan:
            mel = next(v for v, x in voices.items() if x["role"] == R.MELODY and x.get("of") is None)
            db.execute("INSERT OR REPLACE INTO features VALUES (?,?,?,?)", (s.sid, "lead", "was_melody", float(mel)))
            db.execute("INSERT OR REPLACE INTO features VALUES (?,?,?,?)", (s.sid, "lead", "now_melody", float(lead)))
            for v, r in plan.items():
                db.execute("UPDATE voices SET role = ? WHERE song = ? AND voice = ?", (r, s.sid, v))
                if voices.get(v, {}).get("of") == mel:          # a layer of the old tune follows no voice now
                    db.execute("UPDATE voices SET [of] = NULL WHERE song = ? AND voice = ?", (s.sid, v))
        db.commit()

    if progress:
        progress(0, len(songs))
    pool = Pool(count) if count > 1 else None
    try:
        rendered = pool.imap(_render, todo) if pool else map(_render, todo)     # in the songs' order either way
        for i, (s, job) in enumerate(zip(songs, jobs)):
            settle(s, next(rendered) if job else None)
            if progress:
                progress(i + 1, len(songs))
    finally:
        if pool:
            pool.terminate()
            pool.join()
        if not keep:
            shutil.rmtree(work, ignore_errors=True)
    return result


def passed(db, game: str | None = None) -> dict:
    """Whether the pass has run on a game's readings as they are now (None: every game's): {"heard": the songs with a
    voice's loudness kept, "relabelled": the songs whose lead it moved}. Nothing heard: the pass has not run, or the
    game was read again since, and every song's tune is the reader's label."""
    game_is = " AND s.game = ?" if game else ""
    args = (game,) if game else ()
    def count(source: str, name: str) -> int:
        return db.execute("SELECT COUNT(DISTINCT f.song) FROM features f JOIN songs s ON s.id = f.song "
                          f"WHERE f.source = ? AND f.name LIKE ?{game_is}", (source, name) + args).fetchone()[0]
    return {"heard": count("render", "voice_lufs_%"), "relabelled": count("lead", "now_melody")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("game")
    ap.add_argument("spc_folder")
    ap.add_argument("--db")
    ap.add_argument("--window", type=float, default=LEAD_WINDOW)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", help="keep the renders here")
    ap.add_argument("--workers", type=int, help="songs rendered at a time (default: all the cores but one)")
    a = ap.parse_args(argv)
    db = store.connect(a.db) if a.db else store.connect()
    result = run(db, a.game, a.spc_folder, a.window, a.dry_run, a.out, workers=a.workers)
    kinds = Counter(why for _, why, _ in result.values())
    print(f"{len(result)} songs: {dict(kinds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
