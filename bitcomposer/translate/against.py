"""The generator against a game (stage 4 of docs/TRANSLATOR.md): the
harmony and rhythm counts (vocab.py, rhythm.py) of songs composed with a
pack, beside the game's own from the readings database, side by side.

    python -m bitcomposer.translate.against --against PACK ... [--db PATH] [--game NAME]
                                             [--songs N] [--top N] [--spc DIR]

The packs and seeds are stage 2's (__main__.py --against): a pack's name or
a pack.json, --songs songs each, seeds 1 to N. Each table's rows are the
top ones of every column (the game's first), so a habit of either side
shows; a cell is the column's share, a pattern's with the songs it is heard
in after it.

Reading a composed song. The generator knows its parts, so they are its
channels' (measures.of_composed): the melody, the bass, the arp, and its
drums by name (its kick and snare, its hi-hats the hat, its toms and crash
another sound; each hit keeps its kit preset, so the drum namer, drums.py,
is scored on the kit as played beside them). The game's drums are named by
their sound too when its SPC files are given (--spc), else by how they are
played. Its three harmony channels carry held chords, struck
chords or, in a chorus or bridge, a counter-line, which the song does not
record, so each is named as the reader names a game's voices (roles.py's
rules, in their order): held harmony where its notes' median length is two
beats or more, an arp where it plays two notes a beat or more from eight
pitches or fewer and moves little by step, a counter-line where its line
varies and moves by step, accompaniment otherwise. Its chords and its key
are read as the game's are, from its notes with the parts weighed the same
(harmony.chords, harmony.key), not taken from its plan, so a difference in
the tables is the music's and not the reader's; what sounds in a span and
where an onset falls follow the same rules too. Its grid is the one it
writes on: four beats a bar, sixteenths and triplets (a swung hit's delay
lands between). Its key is one for the whole song, as the game's is, so a
chorus or bridge the generator moved to another key gives numerals in the
key read, as a game song's modulation does; how many songs' read key is
the generator's home key is said, and the moves tables carry the rest as
chords off the key. A composed song counts whole: it has no loop."""
import argparse
import math
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction

from . import drums as drums_mod, harmony, measures, rhythm, roles as R, store, vocab
from .rhythm import LETTERS, PARTS, PIECES, PLACES, REST, SIZES, VALUES
from .vocab import INVERSIONS, SPREADS, TONES, _median

DIVISION = 12                        # the generator's grid: sixteenths and triplets
DRUMS = {"kick": "kick", "snare": "snare", "hihat": "hat", "openhat": "hat", "tom": "other", "crash": "other"}
SLOTS = {"openhat": "open_hihat"}    # a drum channel's kit slot where the names differ
MINOR = {"natural_minor", "harmonic_minor", "dorian", "phrygian", "minor_pentatonic"}


@dataclass
class Played:
    """A composed note as the chord reader takes a decoded one."""
    start: float
    end: float | None
    midi: float | None
    level: float
    voice: int


class _Grid:
    """A grid already in beats: the generator's rows."""

    def __init__(self, beats: int):
        self.beat_times = list(range(beats))

    def beats(self, t: float) -> float:
        return t


def compose(pack: str, n: int) -> tuple[str, list[dict]]:
    """n songs composed with a pack (its name, or a pack.json), seeds 1 to n, and the pack's name."""
    from ..composer import compose_song
    name, how = pack, {"sound": pack}
    if pack.endswith(".json"):
        from ..packs.packfile import load_pack_file
        name = load_pack_file(pack)
        how = {"pack": name}
    return name, [compose_song(seed=seed, **how) for seed in range(1, n + 1)]


def _harmony_part(notes: list) -> str:
    """A harmony channel's part by the reader's rules (roles.assign, in their order)."""
    lengths = [n.beats for n in notes if n.beats]
    if lengths and statistics.median(lengths) >= 2.0:
        return R.HARMONY
    seq = [round(n.midi) for n in notes]
    moves = [abs(b - a) for a, b in zip(seq, seq[1:])]
    steps = sum(1 for m in moves if 0 < m <= 2) / len(moves) if moves else 0.0
    per_beat = len(notes) / ((notes[-1].beat - notes[0].beat) or 1.0)
    counts = Counter(seq)
    entropy = -sum(c / len(seq) * math.log2(c / len(seq)) for c in counts.values())
    if per_beat >= 2.0 and len(counts) <= 8 and steps < 0.5:
        return R.ARP
    return R.COUNTER if entropy >= 2.5 and steps >= 0.4 else R.ACCOMP


def parts(score: measures.Score) -> dict[int, str]:
    """Each channel's part: the generator's, its harmony channels by the reader's rules."""
    from ..pattern import CHANNEL_ROLES
    by = defaultdict(list)
    for n in score.notes:
        by[n.voice].append(n)
    out = {}
    for v, notes in by.items():
        name = CHANNEL_ROLES[v]
        out[v] = R.DRUMS if name in DRUMS else _harmony_part(notes) if name == "harmony" else name
    return out


def kit(song: dict) -> dict:
    """A composed song's drum keys to the piece each is (DRUMS): its kit
    presets by slot (info.instruments), or its channels' names without."""
    inst = song.get("info", {}).get("instruments", {})
    return {inst.get(SLOTS.get(ch, ch), ch): piece for ch, piece in DRUMS.items()}


def read(song: dict) -> tuple[vocab.Song, rhythm.Song, tuple]:
    """A composed song read for the counts: its chords and key by the reader
    (the module's account), and the generator's home key (tonic, mode) beside."""
    from ..pattern import CHANNEL_ROLES
    s = measures.of_composed(song)
    inst = song.get("info", {}).get("instruments", {})
    role = parts(s)
    played = [Played(n.beat, s.end if n.beats is None else n.beat + n.beats, n.midi, n.level, n.voice) for n in s.notes]
    grid = _Grid(max(1, math.ceil(s.end)))
    rl = [R.Role(v, r) for v, r in role.items()]
    like = type("Song", (), {"notes": played})
    tonic, mode, _ = harmony.key(like, grid, rl)
    chords = [vocab.Span(c.start, c.end, c.root, c.shape, c.fit) for c in harmony.chords(like, grid, rl)]
    title = song.get("name", "")
    nan = float("nan")
    v = vocab.Song(title, tonic, mode, chords)
    r = rhythm.Song(title, 4, DIVISION, [(b, b + 4) for b in s.bars if b + 4 <= s.end + 1e-9], chords,
                    bpm=float(song.get("tempo") or 120))
    for n in s.notes:
        part = role[n.voice]
        length = nan if n.beats is None else n.beats
        if part in vocab.ROLES:
            v.notes.setdefault(part, []).append((n.beat, length, n.midi))
        if part in PARTS:
            ch = CHANNEL_ROLES[n.voice]
            key = inst.get(SLOTS.get(ch, ch), ch) if part == R.DRUMS else str(n.voice)
            r.notes.setdefault(part, []).append((n.beat, length, nan if n.midi is None else n.midi, key))
    scale = song.get("scale", "major")
    return v, r, (song["key"] % 12, "minor" if scale in MINOR else "major", scale)


def _keys(vs: list, homes: list) -> str:
    """How the songs' keys read against the generator's: its home key; the
    key whose notes its scale's are (a mixolydian or dorian tune read as the
    major a fifth or a tone off, a phrygian as a minor a fourth up: the
    profile knows major and minor only); another."""
    from ..theory import SCALES
    kinds = Counter()
    for s, (tonic, mode, scale) in zip(vs, homes):
        read_ = {(s.tonic + i) % 12 for i in (SCALES["major"] if s.mode == "major" else SCALES["natural_minor"])}
        own = {(tonic + i) % 12 for i in SCALES[scale]}
        kinds["home" if (s.tonic, s.mode) == (tonic, mode) else "parent" if own <= read_ else "other"] += 1
    return f"{kinds['home']} of {len(vs)} (the key its scale's notes spell {kinds['parent']}, another {kinds['other']})"


def _share(n: float, total: float) -> str:
    return f"{100 * n / total:.0f} %" if total else "-"


def _songs(n: int, of: int) -> str:
    return f"({n})" if of else ""


def _top(tally: Counter, total: int) -> list[tuple]:
    """A tally's rows: (label, share with the songs heard in, rank)."""
    songs = getattr(tally, "songs", {})
    return [(k, f"{_share(n, total)} {_songs(songs.get(k, 0), 1)}".strip() if songs else _share(n, total), n)
            for k, n in tally.items()]


def rows(vs: list, rs: list, homes: list | None = None, names: dict | None = None, bank=None) -> dict:
    """One column's tables: section -> [(row, cell, rank)], a rank of None
    meaning every row is kept in its order, a number the top ones (homes:
    the generator's home keys, a composed column; names: its drums', the
    namer scored against them; bank: a game's samples, drums.Bank, its
    drums named by their sound)."""
    out = defaultdict(list)
    spans = sum(1 for s in vs for c in s.chords if s.kept(c))
    out["songs"] += [("songs counted", str(len(vs)), None), ("chord spans", str(spans), None)]
    if homes:
        out["songs"].append(("the key read is the generator's home key", _keys(vs, homes), None))
    moves = vocab.moves(vs)
    for mode in ("major", "minor"):
        here = [m for m in moves if m[0] == mode]
        n = sum(m[3] for m in here)
        sec = f"chord moves, {mode} keys"
        out[sec].append(("songs / moves", f"{sum(1 for s in vs if s.mode == mode)} / {n}", None))
        by_degree, same = Counter(), 0
        for _, a, b, count, _, _ in here:
            if vocab.degree(a) != vocab.degree(b):
                by_degree[vocab.degree(a) + " -> " + vocab.degree(b)] += count
            else:
                same += count
        out[sec].append(("to the same root's other shape", _share(same, n), None))
        out[f"chord moves by degree alone, {mode} keys"] += [(k, _share(c, sum(by_degree.values())), c)
                                                            for k, c in by_degree.items()]
        out[f"chord moves with the shape kept, {mode} keys"] += [(a + " -> " + b, _share(c, n), c)
                                                                for _, a, b, c, _, _ in here]
        held = Counter()
        for s in vs:
            if s.mode == mode:
                for c in s.chords:
                    if s.kept(c):
                        held[vocab.numeral(c.root, s.tonic, s.mode, c.shape)] += c.beats
        out[f"chords held, {mode} keys (beats)"] += [(k, _share(b, sum(held.values())), b) for k, b in held.items()]
    shapes = Counter(c.shape for s in vs for c in s.chords if s.kept(c))
    out["chord shapes read (share of spans)"] += [(k or "major", _share(n, spans), n) for k, n in shapes.items()]
    v = vocab.voicings(vs)
    out["the chord's tones sounding (R root, 3 third, 5 fifth, 7 seventh, + another)"] += [
        (k or "(none)", _share(n, v.spans), n) for k, n in v.tones.items()]
    inv = sum(v.inversion.values())
    out["the lowest note sounding"] += [(INVERSIONS[t], _share(v.inversion[t], inv), None) for t in TONES]
    bands = Counter(next(name for top, name in SPREADS if x < top) for x in v.spread)
    out["spread, the lowest to the highest"] += [(name, _share(bands[name], len(v.spread)), None) for _, name in SPREADS]
    out["spread, the lowest to the highest"] += [("pitches sounding a span", _median(v.sounding), None),
                                                 ("semitones", _median(v.spread), None),
                                                 ("semitones without the bass", _median(v.spread_upper), None)]
    for role in vocab.ROLES:
        c = v.by_role.get(role)
        if c:
            n = sum(c.values())
            out["which tone each part holds (of its beats)"] += [
                (f"{role}: {t}", _share(c[t], n), None) for t in TONES if role != R.MELODY or t in ("root", "third", "fifth", "other")]
    out["which tone each part holds (of its beats)"] += [
        ("the melody above the lowest note (semitones)", _median(v.above_bass), None),
        ("the melody above the chord's top", _median(v.above_top), None)]
    r = rhythm.rhythms(rs)
    sec = "onsets a bar | off the eighths | of them on a triplet"
    for role in PARTS:
        if r.bars[role]:
            n = sum(r.places[role].values())
            off = n - r.places[role]["beat"] - r.places[role]["eighth"]
            out[sec].append((f"{role} (songs with it)", f"{r.onsets[role] / r.bars[role]:.1f} | {_share(off, n)} | "
                             f"{_share(r.places[role]['triplet'], off)} ({r.songs[role]})", None))
    out[sec].append(("as stage 2 counts them, the median song", f"{_median(r.off_eighths, ' %')} | {_median(r.triplets, ' %')}", None))
    out[sec].append(("bars of the song's meter / of another length",
                     f"{sum(1 for s in rs for a, b in s.bars if round(b - a) == s.meter)} / {sum(r.odd.values())}", None))
    for role in PARTS:
        c = r.patterns.get((role, 4))
        if c:
            out[f"rhythms of the {role}, bars of 4 beats (share of its bars, songs)"] += _top(c, sum(c.values()))
    b = rhythm.bass(rs)
    c = b.figures.get(4)
    if c:
        n = sum(c.values())
        out["bass figures (R root, 3 third, 5 fifth, 7 seventh, + another, ? no chord, r the root an octave up)"] += _top(c, n)
        out["the bass's bars"] += [("a root an octave up", _share(sum(x for k, x in c.items() if "r" in k), n), None),
                                   ("a non-chord tone", _share(sum(x for k, x in c.items() if "+" in k), n), None)]
    out["the bass's bars"] += _moves(b.moves, "the bass moves: ")
    d = rhythm.drums(rs, names, bank)
    byname = defaultdict(list)
    for k, c in d.sounds.items():
        byname[c["name"]].append(k)
    sec = "drum sounds, named by their sound (the generator's as it names them)"
    for piece in PIECES:
        keys = byname.get(piece, [])
        out[sec].append((f"named {piece}", ", ".join(sorted(keys)) if names else f"{len(keys)} samples", None))
    if not names:
        how = Counter(c["how"] for c in d.sounds.values())
        out[sec].append(("named by their sound / by how they are played", f"{how['sound']} / {how['play']}", None))
    else:
        rule = rhythm.sounds(rs, bank=drums_mod.Kit())
        differ = [f"{k} {c['name']}" for k, c in sorted(rule.items()) if c["name"] != names.get(k)]
        out[sec].append(("the namer names the generator's as they are", f"{len(rule) - len(differ)} of {len(rule)}"
                         + (f" (the namer: {', '.join(differ)})" if differ else ""), None))
    c = d.figures.get(4)
    if c:
        n = sum(c.values())
        out["drum figures, bars of 4 beats (K kick, S snare, h hat, o another)"] += [
            ("\n".join(f"{LETTERS[piece]} {drawn}" for piece, drawn in fig) if fig else REST,
             f"{_share(x, n)} {_songs(c.songs[fig], 1)}", x) for fig, x in c.items()]
    m = rhythm.melody(rs)
    out["the melody's moves"] += [("songs / notes", f"{m.songs} / {m.notes}", None)] + _moves(m.moves, "")
    total = sum(m.lengths.values())
    values = Counter()
    for length, count in m.lengths.items():
        values[rhythm.value(length)] += count
    out["the melody's lengths, to the next note"] += [(name, _share(values[name], total), None) for _, name in VALUES]
    out["the melody's lengths, to the next note"] += [
        ("the note sounds for this much of it", _median(m.sounded), None),
        ("detached (under 0.75)", _share(sum(1 for x in m.sounded if x < rhythm.SHORT), len(m.sounded)), None)]
    return dict(out)


def _moves(moves: Counter, prefix: str) -> list[tuple]:
    total = sum(moves.values())
    return [(prefix + size, _share(sum(c for (sz, _), c in moves.items() if sz == size), total), None)
            for _, size in SIZES]


def table(columns: dict, top: int = 8) -> str:
    """The columns' tables as text: each section's rows, the first column's top ones then the others'."""
    out = []
    for sec in dict.fromkeys(k for c in columns.values() for k in c):
        labels = []
        for c in columns.values():
            here = c.get(sec, [])
            keep = here if any(x[2] is None for x in here) else sorted(here, key=lambda x: -x[2])[:top]
            labels += [x[0] for x in keep if x[0] not in labels]
        cells = {name: {x[0]: x[1] for x in c.get(sec, [])} for name, c in columns.items()}
        width = max([20] + [len(line) for label in labels for line in label.split("\n")])
        widths = {name: max([len(name)] + [len(cells[name].get(label, "-")) for label in labels]) for name in columns}
        out.append(f"\n{sec}")
        out.append(f"  {'':{width}s}" + "".join(f"  {name:>{widths[name]}s}" for name in columns))
        for label in labels:
            lines = label.split("\n")
            out.append(f"  {lines[0]:{width}s}" + "".join(f"  {cells[name].get(label, '-'):>{widths[name]}s}" for name in columns))
            out += [f"  {line}" for line in lines[1:]]
    return "\n".join(out).lstrip("\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bitcomposer.translate.against", description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", help="the readings database (default: ~/.local/share/bitcomposer/readings.db)")
    ap.add_argument("--game", help="only this game's songs (the songs table's game)")
    ap.add_argument("--against", action="append", default=[], metavar="PACK", required=True,
                    help="a pack's name or a pack.json; more than one allowed")
    ap.add_argument("--songs", type=int, default=20, help="songs composed for each pack (default 20)")
    ap.add_argument("--top", type=int, default=8, help="rows of each column in the pattern and move tables (default 8)")
    ap.add_argument("--spc", metavar="DIR", help="the game folders' root, or one game's folder: its drums named by their sound")
    args = ap.parse_args(argv)
    db = store.connect(args.db)
    vs, left = vocab.load(db, args.game)
    if not vs:
        print("bitcomposer.translate.against: no songs on a beat with a key to count", file=sys.stderr)
        return 1
    rs, _ = rhythm.load(db, args.game)
    games = [g for g, in db.execute("SELECT DISTINCT game FROM songs")]
    game = args.game or (games[0] if len(games) == 1 else "the games")
    columns = {game: rows(vs, rs, bank=drums_mod.Bank(db, args.spc) if args.spc else None)}
    columns[game]["songs"][0] = ("songs counted", f"{len(vs)} of {len(vs) + sum(left.values())}", None)
    for pack in args.against:
        name, songs = compose(pack, args.songs)
        read_ = [read(s) for s in songs]
        names = {}
        for s in songs:
            names.update(kit(s))
        columns[name] = rows([v for v, _, _ in read_], [r for _, r, _ in read_], [h for _, _, h in read_], names)
    print(table(columns, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
