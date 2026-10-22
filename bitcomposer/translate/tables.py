"""Tables: outcomes counted under a context, over songs; what the generator
will play from (docs/idiom/phase-3-tables.md, the framework).

An outcome is a value drawn as a string (a bar's rhythm as its positions,
a chord's voicing); a context is a tuple of conditioning values (the part,
the meter, the tempo band, the game). A table counts, under each context,
the songs playing each outcome, each song's votes summing to one: once
for each distinct outcome it plays under the context ("songs"), so one
song's ostinato is one vote and a figure forty songs share is forty, or
the share of its units each outcome is ("shares"), which keeps how much a
song repeats itself; the unit counts (bars, events) are kept beside for
the report. The probability of an outcome under a context interpolates
the votes with the next coarser context's (the tuple without its last
value, down to no context at all, and below that the floor: an even share
for every outcome the table knows and one slot for the ones it does not,
or a model given for it, such as the bar as a chain of beat cells, so an
outcome never counted still has a likelihood and can be drawn),
Witten-Bell's way: the coarser estimate gets the weight t / (n + t), t the
distinct outcomes seen under the context and n its votes, so a context
seen in few songs, or one whose songs all play something different, leans
on the broader one; or by absolute discounting (a discount D given): each
outcome gives up D of its votes, or all of them if it has fewer, and what
is given up goes to the coarser estimate, so an outcome one song played a
little gives up nearly everything and one forty songs play keeps nearly
all (the better fit where most outcomes are one song's). A per-game table is the shared context with the game
last, backing off to the shared one; a conditioning proposed is tried by
adding it.

Shapes (which conditionings, in what backoff order) are compared by the
mean log-likelihood, in bits per unit, of the held-out units under a
table fitted on the development ones, the games split in half (half():
the split phase 1 used) or, to try a per-game table, the songs within
each game (a held-out game is never seen, so its context backs off whole);
the shape predicting the unseen songs best is kept, and the table then
fitted on every song. Beside the fit, simulate() draws what the table
would play for the held-out songs and measures its spread against theirs:
how many different outcomes a song gets, and how much of it is the song's
most common one (its ostinato), since a table that predicted well by
playing the mode would make every song the same. A draw returns from the
whole distribution with a seed, never the mode.

    python -m bitcomposer.translate.tables rhythm [--db PATH] [--split game|song] [--votes songs|shares] [--floor none|cells]
"""
import argparse
import hashlib
import itertools
import math
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field

GAME = "game"                        # the conditioning that is the song's game (a per-game table)
UNSEEN = "\x00"                      # the slot every outcome the table has not seen shares
DEVELOPMENT, HELD_OUT = "development", "held-out"
SONGS, SHARES = "songs", "shares"    # how a song votes (the module)
BY_GAME, BY_SONG = "game", "song"    # how the halves are split


def half(game: str) -> str:
    """Which half a game's songs are in: fitted on, or held out to score (phase 1's split)."""
    return DEVELOPMENT if int(hashlib.sha1(game.encode()).hexdigest(), 16) % 2 == 0 else HELD_OUT


def half_of(unit, split: str = BY_GAME) -> str:
    """The unit's half: its game's, or by its song within the game."""
    return half(unit.game) if split == BY_GAME else half(unit.song)


@dataclass
class Unit:
    """One thing counted (a song's bar, an event): its outcome, and the
    values it might be conditioned on by name."""
    song: str
    game: str
    outcome: str
    values: dict = field(default_factory=dict)


class Table:
    """Outcomes counted under contexts, each song voting once for each
    distinct outcome it plays under a context (see the module)."""

    def __init__(self, conditionings=(), name: str = "", votes: str = SONGS, floor=None, discount: float | None = None):
        self.conditionings = tuple(conditionings)
        self.name = name
        self.by = votes                  # SONGS or SHARES (the module)
        self.floor = floor               # below the root: None (an even share), or a model with p(outcome, values) and draw(values, rng)
        self.discount = discount         # None: Witten-Bell; else absolute discounting by this much a vote
        self._mass: dict = {}            # context -> (the votes kept at its level, the votes given to the coarser one)
        self.votes: dict = {}            # context -> {outcome: songs voting for it}
        self.songs: Counter = Counter()  # context -> songs counted under it
        self.units: Counter = Counter()  # context -> units counted under it
        self.vocabulary: set = set()
        self._dist: dict = {}            # context -> its votes laid out for draws (_level)

    def context(self, unit: Unit) -> tuple:
        return tuple(unit.game if c == GAME else unit.values.get(c, "?") for c in self.conditionings)

    def fit(self, units) -> "Table":
        """Count the units; the table before was empty."""
        played = defaultdict(Counter)                  # context -> (song, outcome) -> units
        for u in units:
            ctx = self.context(u)
            self.vocabulary.add(u.outcome)
            for k in range(len(ctx) + 1):              # the context and every coarser one
                c = ctx[:k]
                played[c][u.song, u.outcome] += 1
                self.units[c] += 1
        for c, counts in played.items():
            totals = Counter()
            for (song, _), n in counts.items():
                totals[song] += n
            votes = defaultdict(float)
            for (song, outcome), n in counts.items():
                votes[outcome] += n / totals[song] if self.by == SHARES else 1
            self.votes[c] = dict(votes)
            self.songs[c] = len(totals)
        self._weigh()
        return self

    def _weigh(self) -> None:
        """Each context's mass kept at its level and given to the coarser one (the module's two smoothings)."""
        self._mass.clear()
        self._dist.clear()
        for c, votes in self.votes.items():
            n = sum(votes.values())
            if self.discount is None:
                self._mass[c] = (n, len(votes))
            else:
                given = sum(min(v, self.discount) for v in votes.values())
                self._mass[c] = (n - given, given)

    def p(self, outcome: str, context: tuple, values: dict | None = None) -> float:
        """The outcome's probability under the context (see the module);
        `values` are the unit's, for a floor model that conditions on them."""
        if self.floor is None:
            o = outcome if outcome in self.vocabulary else UNSEEN
            prob = 1.0 / (len(self.vocabulary) + 1)
        else:
            o = outcome
            prob = self.floor.p(outcome, values or {})
        for k in range(len(context) + 1):
            c = context[:k]
            votes = self.votes.get(c)
            if not votes:
                continue                                # a context never seen: the coarser estimate stands
            kept, given = self._mass[c]
            own = votes.get(o, 0) if self.discount is None else max(votes.get(o, 0) - self.discount, 0)
            prob = (own + given * prob) / (kept + given)
        return prob

    def score(self, units) -> float:
        """The mean log-likelihood of the units, in bits a unit (higher is better)."""
        units = list(units)
        if not units:
            return float("nan")
        return sum(math.log2(self.p(u.outcome, self.context(u), u.values)) for u in units) / len(units)

    def _level(self, context: tuple):
        """A context's own votes, for draws: (outcomes, their cumulative
        weights, the mass kept at this level, the mass given to the coarser
        one), or None where the context was never seen or keeps nothing."""
        if context not in self._dist:
            votes = self.votes.get(context)
            level = None
            if votes:
                weights = {o: v if self.discount is None else max(v - self.discount, 0) for o, v in votes.items()}
                outcomes = [o for o, w in weights.items() if w > 0]
                if outcomes:
                    cum = list(itertools.accumulate(weights[o] for o in outcomes))
                    level = (outcomes, cum) + self._mass[context]
            self._dist[context] = level
        return self._dist[context]

    def draw(self, context: tuple, rng: random.Random, values: dict | None = None) -> str:
        """An outcome drawn from the whole distribution under the context:
        from the finest level down, the level's own votes with the weight
        n / (n + t) else the coarser level's; below the root, the floor
        model's draw, or any known outcome evenly (the unseen slot's share
        redrawn)."""
        for k in range(len(context), -1, -1):
            level = self._level(context[:k])
            if level is None:
                continue
            outcomes, cum, kept, given = level
            if rng.random() * (kept + given) < kept:
                return rng.choices(outcomes, cum_weights=cum)[0]
        if self.floor is not None:
            return self.floor.draw(values or {}, rng)
        if "" not in self._dist:
            self._dist[""] = sorted(self.vocabulary)
        return rng.choice(self._dist[""])

    def entries(self) -> int:
        """How many (context, outcome) counts the table holds at its finest level."""
        return sum(len(v) for c, v in self.votes.items() if len(c) == len(self.conditionings))

    def to_json(self) -> dict:
        return {"conditionings": list(self.conditionings), "votes_by": self.by, "discount": self.discount,
                "vocabulary": sorted(self.vocabulary),
                "contexts": [{"context": list(c), "songs": self.songs[c], "units": self.units[c], "votes": v}
                             for c, v in sorted(self.votes.items(), key=lambda cv: (len(cv[0]), [str(x) for x in cv[0]]))]}

    @classmethod
    def from_json(cls, d: dict, name: str = "") -> "Table":
        t = cls(d["conditionings"], name, d.get("votes_by", SONGS), discount=d.get("discount"))
        t.vocabulary = set(d["vocabulary"])
        for row in d["contexts"]:
            c = tuple(row["context"])
            t.votes[c] = dict(row["votes"])
            t.songs[c] = row["songs"]
            t.units[c] = row.get("units", 0)
        t._weigh()
        return t


@dataclass
class Comparison:
    """One shape's showing: fitted on the development half, scored on the held-out."""
    shape: tuple
    bits: float                      # held-out mean log-likelihood, bits a unit
    by: dict                         # a part (or whatever `by` names) -> its bits
    contexts: int                    # contexts at the finest level
    entries: int
    spread: tuple | None = None      # (distinct drawn, distinct real, ostinato share drawn, real), means over held-out songs


def shapes(base: tuple, extras=(), game: bool = True) -> list[tuple]:
    """The standard shapes to compare: no context, each prefix of the base
    chain, the chain with each extra conditioning added, and each of those
    a game (the game last, backing off to the shared table)."""
    out = [()] + [base[:k] for k in range(1, len(base) + 1)] + [base + (e,) for e in extras]
    if game:
        out += [s + (GAME,) for s in out]
    return out


FLOOR = ("floor",)                   # the shape that is the floor model alone, for the comparison


def compare(units, shape_list, by: str | None = None, rng_seed: int = 1, split: str = BY_GAME,
            votes: str = SONGS, floor=None, discount: float | None = None) -> list[Comparison]:
    """Fit each shape on the development half, score it on the held-out
    half (overall and by the value of `by`), and measure the spread of what
    it draws; best first. `floor`: a function of the development units
    giving the floor model, fitted once for every shape and scored alone
    too (FLOOR)."""
    units = list(units)
    dev = [u for u in units if half_of(u, split) == DEVELOPMENT]
    held = [u for u in units if half_of(u, split) == HELD_OUT]
    groups = defaultdict(list)
    for u in held:
        groups[u.values.get(by, "") if by else ""].append(u)
    bottom = floor(dev) if floor else None
    out = []
    for shape in list(shape_list) + ([FLOOR] if bottom else []):
        if shape == FLOOR:
            t = Table((), floor=bottom)                # nothing counted: the floor's own likelihood and draws
        else:
            t = Table(shape, votes=votes, floor=bottom, discount=discount).fit(dev)
        out.append(Comparison(shape, t.score(held), {k: t.score(v) for k, v in groups.items()},
                              sum(1 for c in t.votes if len(c) == len(shape)), t.entries(),
                              simulate(t, held, random.Random(rng_seed))))
    out.sort(key=lambda c: -c.bits)
    return out


def simulate(table: Table, units, rng: random.Random, previous: str = "previous") -> tuple:
    """Draw an outcome for each unit, song by song in order (a conditioning
    named `previous` fed the last draw), and set the spread of the draws
    beside the songs' own: (distinct outcomes a song drawn, real; the
    share of its units that are its most common outcome drawn, real), means."""
    by_song = defaultdict(list)
    for u in units:
        by_song[u.song, u.values.get("part", "")].append(u)
    chained = previous in table.conditionings
    distinct, ostinato = [], []
    for us in by_song.values():
        drawn, last = [], "start"
        for u in us:
            values = dict(u.values)
            if chained:
                values[previous] = last
            last = table.draw(table.context(Unit(u.song, u.game, u.outcome, values)), rng, values)
            drawn.append(last)
        real = [u.outcome for u in us]
        distinct.append((len(set(drawn)), len(set(real))))
        ostinato.append((Counter(drawn).most_common(1)[0][1] / len(us), Counter(real).most_common(1)[0][1] / len(us)))
    if not distinct:
        return (0.0, 0.0, 0.0, 0.0)
    n = len(distinct)
    return (sum(a for a, _ in distinct) / n, sum(b for _, b in distinct) / n,
            sum(a for a, _ in ostinato) / n, sum(b for _, b in ostinato) / n)


def report(comparisons, columns=(), title: str = "") -> str:
    """The comparison as text: each shape's held-out bits a unit (and the
    gain over no context), its bits by column, its size and its spread."""
    base = next((c.bits for c in comparisons if c.shape == ()), None)
    w = max(12, max(len(_shape(c.shape)) for c in comparisons))
    head = f"{'shape':{w}} {'bits':>6} {'gain':>6} " + " ".join(f"{str(col)[:7]:>7}" for col in columns) + \
        f" {'ctx':>6} {'entries':>7}  distinct drawn/real  ostinato drawn/real"
    lines = [title, head] if title else [head]
    for c in comparisons:
        gain = f"{c.bits - base:+.3f}" if base is not None else ""
        cols = " ".join(f"{c.by.get(col, float('nan')):7.3f}" for col in columns)
        s = c.spread or (0, 0, 0, 0)
        lines.append(f"{_shape(c.shape):{w}} {c.bits:6.3f} {gain:>6} {cols} {c.contexts:6d} {c.entries:7d}"
                     f"  {s[0]:6.1f} / {s[1]:<6.1f}     {s[2]:5.2f} / {s[3]:<5.2f}")
    return "\n".join(lines)


def _shape(shape: tuple) -> str:
    return "+".join(shape) if shape else "(none)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="compare the shapes of a table on the readings")
    ap.add_argument("table", choices=("rhythm",))
    ap.add_argument("--db", help="the readings database (default: the product's)")
    ap.add_argument("--game", help="only this game's songs")
    ap.add_argument("--parts", help="only these parts, comma-separated")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--split", choices=(BY_GAME, BY_SONG), default=BY_GAME)
    ap.add_argument("--votes", choices=(SONGS, SHARES), default=SONGS)
    ap.add_argument("--floor", choices=("none", "cells"), default="none")
    ap.add_argument("--discount", type=float, default=0.0, help="absolute discounting by this much a vote; 0: Witten-Bell")
    ap.add_argument("--base", default="part,meter", help="the chain every shape starts from")
    ap.add_argument("--extras", default="tempo,previous,place,chord", help="each tried on the chain's end")
    ap.add_argument("--no-game", action="store_true", help="leave out the per-game shapes")
    args = ap.parse_args(argv)
    from . import rhythm, store
    db = store.connect(args.db)
    songs, left = rhythm.load(db, args.game)
    print(f"{len(songs)} songs counted, left out: {left}", file=sys.stderr)
    units = rhythm.units(songs)
    if args.parts:
        keep = set(args.parts.split(","))
        units = [u for u in units if u.values["part"] in keep]
    parts = [p for p in rhythm.PARTS if any(u.values["part"] == p for u in units)]
    base = tuple(x for x in args.base.split(",") if x)
    extras = tuple(x for x in args.extras.split(",") if x)
    floor = rhythm.BarCells if args.floor == "cells" else None
    cs = compare(units, shapes(base, extras, not args.no_game), by="part", rng_seed=args.seed, split=args.split,
                 votes=args.votes, floor=floor, discount=args.discount or None)
    dev = sum(1 for u in units if half_of(u, args.split) == DEVELOPMENT)
    print(report(cs, parts, f"rhythm: {len(units)} bars, {dev} development, {len(units) - dev} held-out; "
                            f"split by {args.split}, votes {args.votes}, floor {args.floor}, "
                            f"{'discount ' + str(args.discount) if args.discount else 'Witten-Bell'}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
