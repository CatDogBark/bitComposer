"""The reference set for the tune-copy check (docs/idiom/phase-3-tables.md):
every four-bar phrase the games play, as its rhythm and its intervals, so
phase 4 can ask whether a written phrase is one of theirs. Kept on the
machine, never in the repository.

    python -m bitcomposer.translate.reference --db PATH --out phrases.json [--length 4]

A phrase is phrases.py's: the tune over the window (the melody's line, or
the counter-line's where the melody rests). Its rhythm is its onsets in
twelfths of a beat from the phrase's start; its intervals the semitone
steps between its notes in order. A written phrase matches a reference
phrase when both agree (a copy), or when the intervals alone agree
(the tune on another rhythm) or the rhythm alone (phase 4 decides which
it asks)."""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from . import phrases

GRID = 12                            # twelfths of a beat


def of_line(line: list, start: float) -> tuple[list, list]:
    """A tune's rhythm (onsets in twelfths from `start`) and intervals (semitone steps)."""
    rhythm = [int(round((n[0] - start) * GRID)) for n in line]
    pitches = [int(round(n[2])) for n in line]
    return rhythm, [b - a for a, b in zip(pitches, pitches[1:])]


def phrases_of(songs: list, length=4) -> list[dict]:
    """Every phrase with a tune over the songs, as rows: song, game, title, the
    bar it starts at, its rhythm and intervals."""
    out = []
    for s in songs:
        bar_of = {round(a, 6): k for k, (a, _) in enumerate(s.bars)}
        for ph in phrases.phrases(s, length):
            if not ph.line:
                continue
            rhythm, intervals = of_line(ph.line, ph.start)
            out.append({"song": s.sid, "game": s.game, "title": s.title, "bar": bar_of.get(round(ph.start, 6)),
                        "rhythm": rhythm, "intervals": intervals})
    return out


def make(db, out, length=4, game: str | None = None) -> dict:
    """The reference set from the readings, written to `out` (JSON)."""
    songs, left = phrases.load(db, game)
    rows = phrases_of(songs, length)
    data = {"about": f"the games' {length}-bar phrases as rhythm (twelfths of a beat) and intervals (semitones); "
                     f"{len(rows)} phrases of {len(songs)} songs; for the tune-copy check; not for the repository",
            "length": length, "songs": len(songs), "left_out": left, "phrases": rows}
    Path(out).write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
    return data


def load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Index:
    """The set indexed for lookups: by rhythm and intervals together, by each alone."""

    def __init__(self, data: dict):
        self.rows = data["phrases"]
        self.both, self.by_rhythm, self.by_intervals = defaultdict(list), defaultdict(list), defaultdict(list)
        for i, r in enumerate(self.rows):
            self.both[(tuple(r["rhythm"]), tuple(r["intervals"]))].append(i)
            self.by_rhythm[tuple(r["rhythm"])].append(i)
            self.by_intervals[tuple(r["intervals"])].append(i)

    def matches(self, rhythm: list, intervals: list, how: str = "both") -> list[dict]:
        """The reference phrases a phrase copies: `how` both, rhythm or intervals."""
        key = {"both": (tuple(rhythm), tuple(intervals)), "rhythm": tuple(rhythm), "intervals": tuple(intervals)}[how]
        table = {"both": self.both, "rhythm": self.by_rhythm, "intervals": self.by_intervals}[how]
        return [self.rows[i] for i in table.get(key, ())]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="write the reference set for the tune-copy check")
    ap.add_argument("--db", help="the readings database (default: the product's)")
    ap.add_argument("--out", required=True, help="the JSON file to write (keep it out of the repository)")
    ap.add_argument("--length", type=int, default=4, help="the phrase length in bars (default 4)")
    ap.add_argument("--game", help="only this game's songs")
    args = ap.parse_args(argv)
    from . import store
    data = make(store.connect(args.db), args.out, args.length, args.game)
    print(f"{args.out}: {len(data['phrases'])} phrases of {data['songs']} songs", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
