"""The counts across games (stage 4 of docs/TRANSLATOR.md): per game, the
headline numbers of the harmony and rhythm counts (vocab.py, rhythm.py),
then how far they spread across games, and whether a game's driver or its
composer explains the wide ones; which says whether the vocabulary should
be one for SNES music, or a game's, a composer's or a driver's own.

    python -m bitcomposer.translate.games [--db PATH] [--shuffles N]

Per game. The songs counted are the harmony and rhythm counts' (a song in
free time, with no key, or mostly unfit or silent is left out; the table
says how many, and how many of the counted were followed loosely, on no
grid, and the share of their bars of another length than the meter, which
is the grid restarting). Then, each once through: the tempo (the median),
the share of songs in minor keys, how often the chord changes (fit chord
spans a bar), the share of spans read as a bare fifth, the two cadences by
degree alone (IV -> I and V -> I, of all degree moves, both modes) and the
degree move counted most, the bass walking (its moves by step) against
bouncing octaves, the share of pitched onsets off the eighths and of those
on a triplet (the median song, as stage 2 counts them), the melody's
sixteenths, triplet eighths and notes a beat or longer, its steps, the
drums' onsets a bar, the share of songs without drums, and the share of
songs swung (the off-beat past SWUNG of the beat). These are the numbers
the FFVI paragraphs of the plan turned on, one or two from each table,
chosen because each is a habit a pack could set (a tempo, a mode, a chord
rate, a voicing, a cadence, a bass style, a grid, a melody's values, a
kit's density, a swing) rather than a pattern of one song's.

Spread. For each number, the median over games, the middle half, and the
games at either end; its spread is the middle half's width against its
median (or a floor, FLOOR, so a share near nought is not called wide for
moving a point): under SHARED, shared, SNES music's habit; over OWN, a
game's own; between, mixed. Each game counts once, however many songs.

Explained. For the driver and for the first-listed composer, over the
games that share theirs with another (a group of one explains nothing),
the share of the variance between games their group means take (eta
squared), against what shuffled labels take (the median of --shuffles
shufflings): a number the driver or the composer explains stands well
over its shuffled share. The games sharing a driver here are mostly
Nintendo's N-SPC (13 games) and Square's (akao, 3); the composers shared
are four pairs and a trio, so the composer's share is read from few."""
import argparse
import random
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from . import rhythm, roles as R, store, vocab

SWUNG = 0.6                          # a song's off-beat this far into the beat is swung (0.5 straight)
SHARED = 0.35                        # a spread under this: SNES music's habit
OWN = 0.7                            # over this: a game's own
FLOOR = {"%": 10.0, "bpm": 20.0, "n": 1.0}
MARGIN = 0.15                        # eta squared this far over its shuffled share: explained
# the headline numbers: key, label, kind (%: a share; bpm; n: a count a bar)
HEADS = (("tempo", "tempo", "bpm"), ("minor", "minor", "%"), ("chords", "chords a bar", "n"), ("fifths", "bare 5ths", "%"),
         ("iv_i", "IV->I", "%"), ("v_i", "V->I", "%"), ("bass_step", "bass step", "%"), ("bass_oct", "bass 8ve", "%"),
         ("off", "off 8ths", "%"), ("triplet", "triplet", "%"), ("mel16", "mel 16th", "%"), ("mel_trip", "mel trip", "%"),
         ("mel_long", "mel beat+", "%"), ("mel_step", "mel step", "%"), ("drums", "drums a bar", "n"),
         ("drumless", "drumless", "%"), ("swung", "swung", "%"))
LABELS = {k: label for k, label, _ in HEADS}
KINDS = {k: kind for k, _, kind in HEADS}


@dataclass
class Game:
    name: str
    composer: str
    driver: str
    counted: int = 0
    total: int = 0
    left_out: dict = field(default_factory=dict)
    loose: int = 0                   # counted songs followed loosely
    odd: float = 0.0                 # the share of their bars of another length than the meter
    numbers: dict = field(default_factory=dict)
    top_move: str = ""


def _share(n, total) -> float:
    return 100.0 * n / total if total else 0.0


def headline(vs: list, rs: list, bpms: list, swings: list) -> tuple[dict, str]:
    """A game's headline numbers from its harmony songs, rhythm songs, and
    its songs' tempos and swings; with the degree move counted most."""
    out = {}
    out["tempo"] = statistics.median(bpms) if bpms else 0.0
    out["minor"] = _share(sum(1 for s in vs if s.mode == "minor"), len(vs))
    spans = [c for s in rs for c in s.chords if c.root is not None and c.fit >= vocab.FIT]
    beats = sum(c.beats for c in spans)
    meter = statistics.median([s.meter for s in rs]) if rs else 4
    out["chords"] = len(spans) * meter / beats if beats else 0.0
    out["fifths"] = _share(sum(1 for c in spans if c.shape == "5"), len(spans))
    by_degree = Counter()
    for _, a, b, count, _, _ in vocab.moves(vs):
        if vocab.degree(a) != vocab.degree(b):
            by_degree[vocab.degree(a) + " -> " + vocab.degree(b)] += count
    n = sum(by_degree.values())
    out["iv_i"], out["v_i"] = _share(by_degree["IV -> I"], n), _share(by_degree["V -> I"], n)
    top = by_degree.most_common(1)
    top_move = f"{top[0][0]} {_share(top[0][1], n):.0f} %" if top else "-"
    b = rhythm.bass(rs)
    moves = sum(b.moves.values())
    out["bass_step"] = _share(sum(c for (sz, _), c in b.moves.items() if sz == "step"), moves)
    out["bass_oct"] = _share(sum(c for (sz, _), c in b.moves.items() if sz == "octave"), moves)
    r = rhythm.rhythms(rs)
    out["off"] = statistics.median(r.off_eighths) if r.off_eighths else 0.0
    out["triplet"] = statistics.median(r.triplets) if r.triplets else 0.0
    m = rhythm.melody(rs)
    values = Counter()
    for length, count in m.lengths.items():
        values[rhythm.value(length)] += count
    n = sum(values.values())
    out["mel16"] = _share(values["a sixteenth"], n)
    out["mel_trip"] = _share(values["a triplet eighth"], n)
    out["mel_long"] = _share(sum(c for v, c in values.items() if v not in ("a sixteenth", "a triplet eighth", "an eighth",
                                                                          "two triplet eighths", "a dotted eighth")), n)
    moves = sum(m.moves.values())
    out["mel_step"] = _share(sum(c for (sz, _), c in m.moves.items() if sz == "step"), moves)
    out["drums"] = r.onsets[R.DRUMS] / r.bars[R.DRUMS] if r.bars[R.DRUMS] else 0.0
    out["drumless"] = _share(sum(1 for s in rs if R.DRUMS not in s.notes and R.DRUMS not in s.rolls), len(rs))
    out["swung"] = _share(sum(1 for x in swings if x is not None and x >= SWUNG), len(swings))
    return out, top_move


def games(db) -> list[Game]:
    """Each game's headline numbers over the database, by game name."""
    out = []
    rows = db.execute("SELECT game, composer, driver, COUNT(*) FROM songs GROUP BY game ORDER BY game").fetchall()
    for name, composer, driver, total in rows:
        g = Game(name, composer or "", driver or "", total=total)
        vs, left = vocab.load(db, name)
        rs, _ = rhythm.load(db, name)
        titles = {s.title for s in rs}
        g.counted, g.left_out = len(vs), left
        bpms, swings = [], []
        for title, bpm, swing, loose in db.execute("SELECT title, bpm, swing, loose FROM songs WHERE game = ?", (name,)):
            if title in titles:
                bpms.append(bpm)
                swings.append(swing)
                g.loose += loose or 0
        bars = [(a, b, s.meter) for s in rs for a, b in s.bars]
        g.odd = _share(sum(1 for a, b, meter in bars if round(b - a) != meter), len(bars))
        if vs and rs:
            g.numbers, g.top_move = headline(vs, rs, bpms, swings)
        out.append(g)
    return out


def spread(table: list[Game]) -> list[tuple]:
    """Each number's spread over the games: (key, median, q1, q3, (low game,
    its value), (high game, its value), spread, verdict)."""
    out = []
    for key in LABELS:
        have = [(g.numbers[key], g.name) for g in table if g.numbers]
        if len(have) < 4:
            continue
        values = sorted(x for x, _ in have)
        q1, med, q3 = statistics.quantiles(values, n=4)
        width = (q3 - q1) / max(abs(med), FLOOR[KINDS[key]])
        verdict = "shared" if width < SHARED else "own" if width >= OWN else "mixed"
        out.append((key, med, q1, q3, min(have), max(have), width, verdict))
    return out


def composer_of(g: Game) -> str:
    """The first-listed composer, the one a game is credited to foremost."""
    return g.composer.split(",")[0].strip()


def _eta(values: list, labels: list) -> float:
    """The share of the variance between the values their groups' means take."""
    mean = statistics.fmean(values)
    total = sum((v - mean) ** 2 for v in values)
    if not total:
        return 0.0
    by = defaultdict(list)
    for v, label in zip(values, labels):
        by[label].append(v)
    return sum(len(vs) * (statistics.fmean(vs) - mean) ** 2 for vs in by.values()) / total


def explained(table: list[Game], by, shuffles: int = 200, seed: int = 1) -> dict:
    """What a grouping (by: Game -> label) explains of each number over the
    games sharing a label: {key: (eta squared, the shuffled median, games,
    groups)}."""
    counts = Counter(by(g) for g in table if g.numbers)
    kept = [g for g in table if g.numbers and counts[by(g)] >= 2]
    labels = [by(g) for g in kept]
    rng = random.Random(seed)
    out = {}
    for key in LABELS:
        values = [g.numbers[key] for g in kept]
        if len(set(labels)) < 2:
            continue
        chance = []
        for _ in range(shuffles):
            shuffled = labels[:]
            rng.shuffle(shuffled)
            chance.append(_eta(values, shuffled))
        out[key] = (_eta(values, labels), statistics.median(chance), len(kept), len(set(labels)))
    return out


def _cell(key: str, x: float) -> str:
    return f"{x:.0f}" if KINDS[key] != "n" else f"{x:.1f}"


def report(table: list[Game], shuffles: int = 200) -> str:
    """The per-game table, the spread of each number, and what the driver and the composer explain."""
    out = [f"{len(table)} games, {sum(g.counted for g in table)} songs counted of {sum(g.total for g in table)}",
           f"\n{'game':24s} {'songs':>7s} {'free':>4s} {'unfit':>5s} {'loose':>5s} {'odd':>4s}"
           + "".join(f" {LABELS[k]:>{max(5, len(LABELS[k]))}s}" for k in LABELS) + "  top move"]
    for g in table:
        unfit = g.left_out.get("unfit", 0) + g.left_out.get("no key", 0)
        out.append(f"{g.name[:24]:24s} {g.counted:3d}/{g.total:<3d} {g.left_out.get('free time', 0):4d} {unfit:5d} {g.loose:5d} {g.odd:3.0f}%"
                   + "".join(f" {_cell(k, g.numbers[k]) if g.numbers else '-':>{max(5, len(LABELS[k]))}s}" for k in LABELS)
                   + f"  {g.top_move}")
    left = Counter()
    for g in table:
        left.update(g.left_out)
    out.append("left out: " + ", ".join(f"{n} {why}" for why, n in left.most_common())
               + "; loose: counted songs followed on no grid; odd: the share of their bars of another length than the meter")
    out.append(f"\nspread over the games (each game once; the middle half's width against the median, or a floor:"
               f" shared under {SHARED:g}, a game's own over {OWN:g})")
    out.append(f"  {'number':12s} {'median':>7s} {'middle half':>14s} {'spread':>6s}  verdict  lowest / highest")
    for key, med, q1, q3, lo, hi, width, verdict in spread(table):
        out.append(f"  {LABELS[key]:12s} {_cell(key, med):>7s} {_cell(key, q1):>6s} - {_cell(key, q3):<6s} {width:6.2f}  {verdict:7s}"
                   f"  {lo[1]} ({_cell(key, lo[0])}) / {hi[1]} ({_cell(key, hi[0])})")
    groupings = (("driver", lambda g: g.driver), ("composer", composer_of))
    exp = {name: explained(table, by, shuffles) for name, by in groupings}
    out.append(f"\nexplained by the driver and by the first-listed composer (eta squared over the games sharing one,"
               f" against the median of {shuffles} shufflings; * where it stands {MARGIN:g} over)")
    cover = ", ".join(f"{name}: {next(iter(e.values()))[2]} games in {next(iter(e.values()))[3]} groups" for name, e in exp.items() if e)
    out.append(f"  {'number':12s}" + "".join(f" {name:>18s}" for name in exp) + f"    ({cover})")
    for key in LABELS:
        cells = []
        for name, e in exp.items():
            if key in e:
                eta, chance, _, _ = e[key]
                cells.append(f"{eta:.2f} ({chance:.2f}){'*' if eta - chance >= MARGIN else ' '}")
            else:
                cells.append("-")
        out.append(f"  {LABELS[key]:12s}" + "".join(f" {c:>18s}" for c in cells))
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bitcomposer.translate.games", description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", help="the readings database (default: ~/.local/share/bitcomposer/readings.db)")
    ap.add_argument("--shuffles", type=int, default=200, help="shufflings of the labels for the chance share (default 200)")
    args = ap.parse_args(argv)
    table = games(store.connect(args.db))
    if not any(g.numbers for g in table):
        print("bitcomposer.translate.games: no songs on a beat with a key to count", file=sys.stderr)
        return 1
    print(report(table, args.shuffles))
    return 0


if __name__ == "__main__":
    sys.exit(main())
