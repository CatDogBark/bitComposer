"""The readings' bar phase against the composers' loop jumps (phase 1 of docs/IDIOM.md).

A song's driver jumps back to its loop on a bar line, or onto a pickup a beat before one. The
independent decode (tools/decode_check.py compare) gives that jump in played time; a readings
database gives the bar lines read. Where the jump falls inside the read bar says whether the bar
phase is right: on the line (or a beat before it) is right, a half bar off is the phase flipped.

    python tools/bar_phase_check.py COMPARE.json READINGS.db [--split development|held-out] [--game NAME] [--songs]

The games are split in two by a fixed rule (the hash of the game's folder), a development half to
tune a reader on and a held-out half to score it; without --split both are shown.
"""
import argparse
import bisect
import hashlib
import json
import os
import sqlite3
import sys
from array import array
from collections import Counter, defaultdict

NEAR = 0.12                          # of a bar: a jump this near a bar line is on it
PICKUP = 0.12                        # of a bar: a jump this near a beat before the line is a pickup


def half_of(game: str) -> str:
    return "development" if int(hashlib.sha1(game.encode()).hexdigest(), 16) % 2 == 0 else "held-out"


def place(t: float, bars: list, meter: int) -> tuple[float, str] | None:
    """Where t falls in its read bar (0 at the line) and the verdict: on, pickup, half, other."""
    i = bisect.bisect_right(bars, t) - 1
    if i < 0 or i + 1 >= len(bars):
        return None
    f = (t - bars[i]) / (bars[i + 1] - bars[i])
    d = min(f, 1 - f)
    if d <= NEAR:
        return f, "on"
    if abs((1 - f) - 1 / meter) <= PICKUP:
        return f, "pickup"
    if abs(f - 0.5) <= 0.12:
        return f, "half"
    return f, "other"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python tools/bar_phase_check.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("compare")
    ap.add_argument("db")
    ap.add_argument("--split", choices=["development", "held-out"])
    ap.add_argument("--game")
    ap.add_argument("--songs", action="store_true", help="one line a song")
    a = ap.parse_args(argv)
    results = [x for x in json.load(open(a.compare)) if x.get("status") == "ok" and x.get("loop_end_written")]
    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    rows = {(os.path.basename(x["folder"].rstrip("/")), x["file"][:-4]): x for x in db.execute("SELECT id, folder, file, meter, loose FROM songs")}
    grids = {}
    for sid, bars in db.execute("SELECT song, bars FROM beats"):
        g = array("d")
        g.frombytes(bars)
        grids[sid] = list(g)
    by_game = defaultdict(Counter)
    verdicts = Counter()
    eighths = Counter()
    n = 0
    for x in results:
        if a.game and x["game"] != a.game:
            continue
        if a.split and half_of(x["game"]) != a.split:
            continue
        row = rows.get((x["game"], x["song"]))
        if row is None or row["loose"] or row["id"] not in grids:
            continue
        p = place(x["loop_end_written"], grids[row["id"]], row["meter"] or 4)
        if p is None:
            continue
        f, verdict = p
        n += 1
        verdicts[verdict] += 1
        eighths[round(f * 8) % 8] += 1
        by_game[x["game"]][verdict] += 1
        if a.songs:
            print(f"{x['game'][:22]:22s} {x['song'][:36]:36s} {f:.2f} {verdict}")
    if not n:
        print("no songs")
        return 1
    right = verdicts["on"] + verdicts["pickup"]
    print(f"{n} steady songs with a jump inside the read bars{' (' + a.split + ' half)' if a.split else ''}: "
          f"bar phase right {right} ({100 * right / n:.0f} %): on the line {verdicts['on']}, a pickup {verdicts['pickup']}; "
          f"a half bar off {verdicts['half']} ({100 * verdicts['half'] / n:.0f} %); elsewhere {verdicts['other']}")
    print("the jump's place in the read bar, in eighths (0 = the line):", [eighths[k] for k in range(8)])
    print(f"\n{'game':24s} {'half':>5s} {'songs':>5s} {'right':>6s} {'half off':>8s}")
    for g, c in sorted(by_game.items()):
        t = sum(c.values())
        print(f"{g[:24]:24s} {half_of(g)[:4]:>5s} {t:5d} {100 * (c['on'] + c['pickup']) / t:5.0f} % {100 * c['half'] / t:7.0f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
