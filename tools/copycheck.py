"""The tune-copy check on songs written from a vocabulary, as the product writes them (no reference set at hand, so no
phrase is drawn again): every four-bar window of each tune, from every bar, against the games' four-bar phrases
(translate/reference.py, the reference set kept outside the repository: ~/diags/bitcomposer/idiom/phase3/reference/).

    python tools/copycheck.py --seeds 1-100 [--reference PATH] [--pack ffvi]

A release check, run on a machine that holds the reference set, before a vocabulary ships: a phrase whose rhythm and
intervals both equal a game phrase's is a copy; rhythm-only and intervals-only matches are reported beside it."""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from bitcomposer.translate import harness, reference  # noqa: E402
from bitcomposer.written import compose_written  # noqa: E402

BAR = 4                               # beats a bar (whole.METER)


def seeds_of(spec: str) -> list[int]:
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def windows(notes: list, bars: int, length: int = 4):
    """Each `length`-bar window from every bar: (start beat, the tune's line notes inside it)."""
    line = sorted(tuple(n) for n in notes if len(n) < 4 or n[3] == 0)   # the tune's line voice: (start, end, midi[, voice])
    for k in range(0, max(1, bars - length + 1)):
        start = k * BAR
        inside = [n for n in line if start <= n[0] < start + length * BAR]
        if len(inside) >= 4:
            yield start, inside


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--vocabulary", default="default")
    ap.add_argument("--pack", default=None, help="the sound set (default: the seed's draw)")
    ap.add_argument("--seeds", default="1-50")
    ap.add_argument("--reference", default=harness.REFERENCE)
    ap.add_argument("--carry-theme", action="store_true")
    ap.add_argument("--band-returns", action="store_true")
    a = ap.parse_args(argv)
    if not os.path.exists(a.reference):
        print(f"{a.reference}: no reference set on this machine", file=sys.stderr)
        return 2
    index = reference.Index(reference.load(a.reference))
    print(f"reference: {len(index.rows)} phrases; writing {a.seeds} from {a.vocabulary}")
    probed = copies = rhythm_only = intervals_only = 0
    songs_copying = []
    for seed in seeds_of(a.seeds):
        out = compose_written(a.vocabulary, a.pack, seed, carry_theme=a.carry_theme, band_returns=a.band_returns)
        tune = out["written"].get("melody")
        if tune is None:
            continue
        hits = []
        for start, inside in windows(tune.notes, out["plan"].bars):
            rhythm, intervals = reference.of_line(inside, start)
            probed += 1
            both = index.matches(rhythm, intervals)
            if both:
                copies += 1
                hits.append((start // BAR, both[0]["title"], both[0].get("bar")))
            else:
                rhythm_only += bool(index.matches(rhythm, intervals, "rhythm"))
                intervals_only += bool(index.matches(rhythm, intervals, "intervals"))
        if hits:
            songs_copying.append((seed, out["title"], hits))
            print(f"  seed {seed} ({out['title']}): " + "; ".join(f"bar {b} copies {t} bar {rb}" for b, t, rb in hits))
    n = len(seeds_of(a.seeds))
    print(f"{n} songs, {probed} four-bar windows probed: {copies} copy a game phrase (rhythm and intervals) in {len(songs_copying)} songs; "
          f"{rhythm_only} share only a rhythm, {intervals_only} only the intervals")
    return 1 if copies else 0


if __name__ == "__main__":
    raise SystemExit(main())
