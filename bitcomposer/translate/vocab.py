"""The vocabulary from the readings (stage 4 of docs/TRANSLATOR.md), the
harmony half, counted: how one chord moves to the next, and how chords are
voiced, over a game's songs in the readings database.

    python -m bitcomposer.translate.vocab [--db PATH] [--game NAME] [--top N]

Each song is counted once through (to where it loops, as the measures are),
from its chord spans that fit (FIT: fewer than half a triad's tones sounding
reads under it). A song read in free time, with no key, or whose chord beats
are mostly unfit or silent is left out, and the tables say how many are in.

Moves. Each chord is a Roman numeral relative to the song's key, its shape
kept (I, ii7, V7, bVII, viidim). Degrees are the major scale's in a major
key, the natural minor's in a minor one; a root off the scale is named from
the degree above with a flat in major (bIII, bVI, bVII: the chords borrowed
from the parallel minor), and in minor from the degree below with a sharp
(#VI, #VII: the raised sixth and seventh), the Neapolitan bII in both. The
numerals mean different degrees in the two modes, so the moves are counted
by mode. A move is one chord span to the next with no silence or unfit span
between; its weight is counted once, and in the beats the chord moved to is
held.

Voicings. In each span, a pitch sounds when its notes cover a quarter of the
span (SOUNDS: an arp of four tones counts them all; a passing note in a
long chord does not), a struck note heard for an eighth at least however
short its envelope (STRUCK: FFVI's accompaniment keys off in a fifth of a
beat, and still sounds the chord). The chord's tones are taken from the bass, harmony, accompaniment and
arp (the parts that make the chord, as harmony.py weighs them): which of
root, third (a sus chord's second or fourth is "sus"), fifth, seventh and
others sound; the spread from the lowest sounding note to the highest, and
how many; the inversion from the lowest; then which tone each part holds,
by the beats its notes sound (the melody and counter-line too), and where
the melody sits above the bass and the chord's top. against.py sets songs
composed with a pack beside these counts."""
import argparse
import bisect
import math
import re
import statistics
import sys
from array import array
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from . import harmony, roles as R, store

FIT = 0.6                            # a chord span fitting under this is unfit
SOUNDS = 0.25                        # a pitch's notes covering this share of a span sound in it
STRUCK = 0.5                         # beats a struck note is heard for at least, however short
CHORD_ROLES = (R.BASS, R.HARMONY, R.ACCOMP, R.ARP)
ROLES = CHORD_ROLES + (R.COUNTER, R.MELODY)
DEGREES = {"major": "I bII II bIII III IV #IV V bVI VI bVII VII".split(),
           "minor": "I bII II III #III IV #IV V VI #VI VII #VII".split()}
MINOR_SHAPES = {"m": "", "m7": "7", "dim": "dim", "m7b5": "7b5"}   # lower-case numerals, the m dropped
TONES = ("root", "third", "sus", "fifth", "seventh", "other")
MARKS = dict(zip(TONES, ("R", "3", "sus", "5", "7", "+")))
INVERSIONS = {"root": "root position", "third": "first (the third lowest)", "sus": "first (the sus tone lowest)",
              "fifth": "second (the fifth lowest)", "seventh": "third (the seventh lowest)", "other": "a non-chord tone lowest"}
SPREADS = ((12, "under an octave"), (24, "one to two octaves"), (36, "two to three"), (1e9, "three and more"))


@dataclass
class Span:
    start: float
    end: float
    root: int | None
    shape: str
    fit: float

    @property
    def beats(self) -> float:
        return self.end - self.start


@dataclass
class Song:
    """What a song's reading gives the counts: its key, its chord spans and
    its pitched notes by part (start, length, midi; in beats), once through."""
    title: str
    tonic: int
    mode: str
    chords: list[Span]
    notes: dict = field(default_factory=dict)   # role -> [(start, length, midi), ...]

    def kept(self, span: Span) -> bool:
        """Whether a span counts: a chord, fitting what sounds."""
        return span.root is not None and span.fit >= FIT


def numeral(root: int, tonic: int, mode: str, shape: str) -> str:
    """A chord as a Roman numeral in the key, its shape kept."""
    name = DEGREES[mode][(root - tonic) % 12]
    return name.lower() + MINOR_SHAPES[shape] if shape in MINOR_SHAPES else name + shape


def degree(numeral: str) -> str:
    """A numeral's degree alone, its shape and case dropped (ii7 -> II)."""
    m = re.match(r"([b#]?)([ivIV]+)", numeral)
    return m.group(1) + m.group(2).upper()


def tone_of(pc: int, root: int, shape: str) -> str:
    """Which of the chord's tones a pitch class is (TONES)."""
    i = (pc - root) % 12
    if i not in harmony.SHAPES[shape]:
        return "other"
    return {0: "root", 2: "sus", 3: "third", 4: "third", 5: "sus", 6: "fifth", 7: "fifth", 8: "fifth",
            10: "seventh", 11: "seventh"}[i]


def _beats_at(times, t: float) -> float:
    """A time in beats on a list of beat times (Grid.beats, from the store's)."""
    if len(times) < 2:
        return 0.0
    if t <= times[0]:
        return (t - times[0]) / (times[1] - times[0])
    if t >= times[-1]:
        return len(times) - 1 + (t - times[-1]) / (times[-1] - times[-2])
    i = bisect.bisect_right(times, t) - 1
    return i + (t - times[i]) / (times[i + 1] - times[i])


def load(db, game: str | None = None) -> tuple[list[Song], dict]:
    """The songs to count from the database (game: only that game's), and
    why the others were left out: {"free time": n, "no key": n, "unfit": n}."""
    songs, out = [], Counter()
    where, args = ("WHERE game = ?", (game,)) if game else ("", ())
    for sid, title, bpm, tonic, mode, seconds, loop_bar, loop_seconds in db.execute(
            f"SELECT id, title, bpm, key_tonic, key_mode, seconds, loop_bar, loop_seconds FROM songs {where}", args):
        if bpm is None:
            out["free time"] += 1
            continue
        if tonic is None:
            out["no key"] += 1
            continue
        end = math.inf
        row = db.execute("SELECT beats, bars FROM beats WHERE song = ?", (sid,)).fetchone()
        if row and loop_bar is not None and loop_seconds:
            beats, bars = array("d"), array("d")
            beats.frombytes(row[0])
            bars.frombytes(row[1])
            if loop_bar < len(bars):
                end = _beats_at(beats, min(seconds, bars[loop_bar] + loop_seconds))
        chords = [Span(a, min(b, end), root, shape, fit) for a, b, root, shape, fit in
                  db.execute("SELECT start, end, root, shape, fit FROM chords WHERE song = ? ORDER BY start", (sid,))
                  if a < end]
        song = Song(title, tonic, mode, chords)
        total = sum(c.beats for c in chords)
        if not total or sum(c.beats for c in chords if song.kept(c)) <= total / 2:
            out["unfit"] += 1
            continue
        for role, blob in db.execute("SELECT role, notes FROM voices WHERE song = ?", (sid,)):
            if role in ROLES:
                song.notes.setdefault(role, []).extend(
                    (s, length, m) for s, length, m, _, _, _ in store.unpack(blob)
                    if s < end and not math.isnan(m))
        songs.append(song)
    return songs, dict(out)


def moves(songs) -> list[tuple]:
    """How one chord moves to the next, by mode: rows of (mode, from, to,
    count, beats the chord moved to was held, the median of them), the most
    counted first."""
    count, beats, held = Counter(), Counter(), defaultdict(list)
    for s in songs:
        before = None
        for c in s.chords:
            if not s.kept(c):
                before = None
                continue
            here = numeral(c.root, s.tonic, s.mode, c.shape)
            if before:
                k = (s.mode, before, here)
                count[k] += 1
                beats[k] += c.beats
                held[k].append(c.beats)
            before = here
    return sorted(((m, a, b, n, beats[m, a, b], statistics.median(held[m, a, b])) for (m, a, b), n in count.items()),
                  key=lambda r: (-r[3], -r[4], r[0], r[1], r[2]))


@dataclass
class Voicings:
    songs: int = 0
    spans: int = 0                                                       # fit spans counted
    tones: Counter = field(default_factory=Counter)                      # "R 3 5" -> spans
    inversion: Counter = field(default_factory=Counter)                  # the lowest note's tone -> spans
    spread: list = field(default_factory=list)                           # semitones, lowest to highest, a span
    spread_upper: list = field(default_factory=list)                     # the same without the bass
    sounding: list = field(default_factory=list)                         # pitches sounding, a span
    by_role: dict = field(default_factory=lambda: defaultdict(Counter))  # role -> tone -> beats
    above_bass: list = field(default_factory=list)                       # the melody's semitones over the lowest note
    above_top: list = field(default_factory=list)                        # and over the chord's highest


def _buckets(notes) -> dict:
    """Notes by each whole beat they sound in (a span's notes are its beats' together)."""
    out = defaultdict(list)
    for n in notes:
        start, length, _ = n
        stop = start + length if not math.isnan(length) else start + 1
        for b in range(math.floor(start), math.ceil(stop)):
            out[b].append(n)
    return out


def _sounding(buckets: dict, span: Span) -> dict:
    """What sounds in a span: rounded midi -> the share of the span its notes cover."""
    cover = Counter()
    seen = set()
    for b in range(math.floor(span.start), math.ceil(span.end)):
        for n in buckets.get(b, ()):
            if id(n) in seen:
                continue
            seen.add(id(n))
            start, length, midi = n
            stop = start + length if not math.isnan(length) else math.inf
            overlap = min(stop, span.end) - max(start, span.start)
            if start >= span.start:                  # struck in the span: heard for an eighth at least
                overlap = max(overlap, min(STRUCK, span.end - start))
            if overlap > 0:
                cover[round(midi)] += overlap / span.beats
    return cover


def voicings(songs) -> Voicings:
    """The voicings over the songs' fit spans (the module's account)."""
    v = Voicings(songs=len(songs))
    for s in songs:
        buckets = {role: _buckets(ns) for role, ns in s.notes.items()}
        for c in s.chords:
            if not s.kept(c):
                continue
            v.spans += 1
            chord, upper = Counter(), Counter()
            for role in CHORD_ROLES:
                if role in buckets:
                    chord.update(_sounding(buckets[role], c))
                    if role != R.BASS:
                        upper.update(_sounding(buckets[role], c))
            pitches = sorted(m for m, share in chord.items() if share >= SOUNDS - 1e-9)
            tones = {tone_of(m % 12, c.root, c.shape) for m in pitches}
            v.tones[" ".join(MARKS[t] for t in TONES if t in tones)] += 1
            v.sounding.append(len(pitches))
            if pitches:
                v.inversion[tone_of(pitches[0] % 12, c.root, c.shape)] += 1
                v.spread.append(pitches[-1] - pitches[0])
            top = [m for m, share in upper.items() if share >= SOUNDS - 1e-9]
            if top:
                v.spread_upper.append(max(top) - min(top))
            for role, by in buckets.items():
                for m, share in _sounding(by, c).items():
                    v.by_role[role][tone_of(m % 12, c.root, c.shape)] += share * c.beats
            if pitches and R.MELODY in buckets:
                mel = _sounding(buckets[R.MELODY], c)
                if mel:
                    at = sum(m * w for m, w in mel.items()) / sum(mel.values())   # its pitch, weighted by time
                    v.above_bass.append(at - pitches[0])
                    v.above_top.append(at - pitches[-1])
    return v


def _pct(n: float, total: float) -> str:
    return f"{100 * n / total:3.0f} %" if total else "  - "


def _median(values: list, unit: str = "") -> str:
    if not values:
        return "-"
    if len(values) < 4:
        return f"{statistics.median(values):.3g}{unit}"
    q = statistics.quantiles(values, n=4)
    return f"{q[1]:.3g}{unit} [{q[0]:.3g}-{q[2]:.3g}]"


def report(songs: list, left_out: dict, top: int = 25, game: str = "") -> str:
    """Both tables as text: the moves by mode (top rows each), then the voicings."""
    total = len(songs) + sum(left_out.values())
    out = [f"harmony of {game + ': ' if game else ''}{len(songs)} songs of {total} ("
           + ", ".join(f"{n} {why}" for why, n in left_out.items()) + ")" if left_out else
           f"harmony of {game + ': ' if game else ''}{len(songs)} songs"]
    rows = moves(songs)
    for mode in ("major", "minor"):
        here = [r for r in rows if r[0] == mode]
        n = sum(r[3] for r in here)
        k = sum(1 for s in songs if s.mode == mode)
        out.append(f"\nchord moves, {mode} keys ({k} songs, {n} moves)")
        out.append(f"  {'move':20s} {'count':>6s} {'share':>6s} {'beats':>6s}  held")
        for _, a, b, count, beats, held in here[:top]:
            out.append(f"  {a + ' -> ' + b:20s} {count:6d} {_pct(count, n):>6s} {beats:6.0f}  {held:g}")
        if len(here) > top:
            out.append(f"  ... {len(here) - top} more")
        by_degree = Counter()
        for _, a, b, count, _, _ in here:
            if degree(a) != degree(b):
                by_degree[degree(a) + " -> " + degree(b)] += count
        same = n - sum(by_degree.values())
        out.append(f"  by degree alone ({same} moves to the same root's other shape left out): "
                   + ", ".join(f"{k} {100 * c / sum(by_degree.values()):.0f} %" for k, c in by_degree.most_common(8)))
    v = voicings(songs)
    out.append(f"\nvoicings ({v.songs} songs, {v.spans} chord spans; a pitch sounds when its notes cover a quarter of the span)")
    out.append("  tones sounding, of the bass, harmony, accompaniment and arp"
               " (R root, 3 third, sus a sus chord's 2nd or 4th, 5 fifth, 7 seventh, + another)")
    for tones, n in v.tones.most_common(top):
        out.append(f"    {tones or '(none)':16s} {_pct(n, v.spans)}")
    out.append("  the lowest note sounding")
    for tone in TONES:
        if v.inversion[tone]:
            out.append(f"    {INVERSIONS[tone]:28s} {_pct(v.inversion[tone], sum(v.inversion.values()))}")
    out.append("  spread, the lowest to the highest")
    bands = Counter(next(name for top_, name in SPREADS if x < top_) for x in v.spread)
    for _, name in SPREADS:
        out.append(f"    {name:28s} {_pct(bands[name], len(v.spread))}")
    out.append(f"    pitches sounding: {_median(v.sounding)}; semitones: {_median(v.spread)};"
               f" without the bass: {_median(v.spread_upper)}")
    out.append("  which tone each part holds, by the beats its notes sound in the spans")
    out.append(f"    {'part':14s} {'beats':>7s}" + "".join(f" {t:>8s}" for t in TONES))
    for role in ROLES:
        c = v.by_role.get(role)
        if c:
            n = sum(c.values())
            out.append(f"    {role:14s} {n:7.0f}" + "".join(f" {_pct(c[t], n):>8s}" for t in TONES))
    out.append(f"  the melody above the lowest note: {_median(v.above_bass, ' semitones')};"
               f" above the chord's top: {_median(v.above_top)}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bitcomposer.translate.vocab", description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", help="the readings database (default: ~/.local/share/bitcomposer/readings.db)")
    ap.add_argument("--game", help="only this game's songs (the songs table's game)")
    ap.add_argument("--top", type=int, default=25, help="rows of each moves table (default 25)")
    args = ap.parse_args(argv)
    db = store.connect(args.db)
    songs, left_out = load(db, args.game)
    if not songs:
        print("bitcomposer.translate.vocab: no songs on a beat with a key to count", file=sys.stderr)
        return 1
    games = [g for g, in db.execute("SELECT DISTINCT game FROM songs")]
    print(report(songs, left_out, args.top, args.game or (games[0] if len(games) == 1 else "")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
