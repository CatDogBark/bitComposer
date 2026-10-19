"""The part each voice plays, from its notes: drums, bass, melody, a
counter-line, harmony (held chords), arp (fast repeated chord tones),
accompaniment (chords struck in rhythm), or a doubling of another voice.

Each guess keeps its evidence (the measures it was made from), and a
correction overrides it. Drums first: noise, samples with no pitch, or one
sample struck at one or two pitches (FFVI's percussion plays at G#3, the
driver's own pitch). Then the pitched voices by register and motion: the
bass the lowest line, the melody the most varied line on top, held notes
harmony, fast cycling ones an arp; a voice playing another's notes (the same
pitches and rhythm, a delay or an octave apart) its doubling."""
import bisect
import math
import statistics
from collections import Counter
from dataclasses import dataclass, field

DRUMS, BASS, MELODY, COUNTER, HARMONY, ARP, ACCOMP, DOUBLE = (
    "drums", "bass", "melody", "counter", "harmony", "arp", "accompaniment", "double")


@dataclass
class Role:
    voice: int
    role: str
    of: int | None = None            # a doubling's voice
    evidence: dict = field(default_factory=dict)


def _features(notes, grid) -> dict:
    """What a voice's notes measure: how many, how pitched, where, how long, how they move."""
    pitched = [p for p in notes if p.midi is not None]
    mids = [p.midi for p in pitched]
    per_sample = {}
    for p in pitched:
        per_sample.setdefault(p.sample.key, set()).add(round(p.midi))
    lengths = [p.length for p in notes if p.length]
    beat = grid.period_at(notes[0].start) if grid else 0.5
    seq = [round(m) for m in mids]
    moves = [abs(b - a) for a, b in zip(seq, seq[1:])]
    span = (notes[-1].start - notes[0].start) or 1.0
    return {
        "notes": len(notes),
        "unpitched": sum(1 for p in notes if p.midi is None) / len(notes),
        "pitches_per_sample": max((len(v) for v in per_sample.values()), default=0),
        "distinct": len(set(seq)),
        "median": statistics.median(mids) if mids else None,
        "low": min(mids) if mids else None,
        "length_beats": statistics.median(lengths) / beat if lengths else 0.0,
        "per_beat": len(notes) / (span / beat) if beat else 0.0,
        "steps": sum(1 for m in moves if 0 < m <= 2) / len(moves) if moves else 0.0,
        "repeats": sum(1 for m in moves if m == 0) / len(moves) if moves else 0.0,
        "entropy": _entropy(Counter(seq)) if seq else 0.0,
        "level": statistics.median(p.level for p in notes),
    }


def _entropy(counts: Counter) -> float:
    total = sum(counts.values())
    return -sum(c / total * math.log2(c / total) for c in counts.values())


def _doubles(a, b, window: float = 0.5) -> tuple[float, float] | None:
    """Whether voice b plays voice a's notes: the share of a's notes b has
    (the same pitch class, a fixed delay within `window`), and the delay."""
    if len(a) < 8 or len(b) < 8:
        return None
    best = None
    starts_b = [(p.start, round(p.midi) % 12) for p in b if p.midi is not None]
    delays = Counter()
    for p in a:
        if p.midi is None:
            continue
        for t, pc in starts_b:
            d = t - p.start
            if -0.001 <= d <= window and pc == round(p.midi) % 12:
                delays[round(d, 2)] += 1
    if not delays:
        return None
    delay, hits = delays.most_common(1)[0]
    share = hits / len(a)
    if best is None or share > best[0]:
        best = (share, delay)
    return best


ECHO_DELAY = (0.025, 0.5)            # seconds an echo part may follow the part it copies
ECHO_HELD = 0.6                      # the share of its notes that must be copies, one delay apart


def echoes(song) -> dict:
    """Voices playing another's notes a fixed delay later, all song long:
    voice -> (the voice it copies, the delay). A driver's echo made of a
    spare voice (Star Fox's Corneria: one part copying another 1.4 steps of
    its grid later, 246 ms, every note off the grid). A copy is a note of
    the same pitch class; the delay is the one most of them share, to 4 ms."""
    by = {}
    for p in song.notes:
        if p.midi is not None and p.level > 0:
            by.setdefault(p.voice, []).append((p.start, round(p.midi) % 12))
    out = {}
    for v, notes in by.items():
        if len(notes) < 16:
            continue
        best = None
        for u, theirs in by.items():
            if u == v:
                continue
            starts = [t for t, _ in theirs]
            delays = []
            for t, pc in notes:
                i = bisect.bisect_left(starts, t - ECHO_DELAY[1])
                delays.append([t - s for s, q in theirs[i:bisect.bisect_right(starts, t - ECHO_DELAY[0])] if q == pc])
            flat = Counter(round(d * 500) for ds in delays for d in ds)     # 2 ms bins
            if not flat:
                continue
            mode = flat.most_common(1)[0][0] / 500
            share = sum(1 for ds in delays if any(abs(d - mode) <= 0.004 for d in ds)) / len(notes)
            if share >= ECHO_HELD and (best is None or share > best[0]):
                best = (share, u, mode)
        if best:
            out[v] = (best[1], best[2])
    return out


def assign(song, grid, echoed: dict | None = None) -> list[Role]:
    """Each voice's part over the song (echoed: voices found to be another's
    echo, by echoes(), each that voice's double)."""
    by_voice = {}
    for p in song.notes:
        by_voice.setdefault(p.voice, []).append(p)
    feats = {v: _features(ns, grid) for v, ns in by_voice.items() if ns}
    roles = {}
    for v, f in feats.items():
        if f["unpitched"] >= 0.5 or (f["pitches_per_sample"] <= 2 and f["notes"] >= 8 and f["distinct"] <= 2):
            roles[v] = Role(v, DRUMS, evidence={k: f[k] for k in ("unpitched", "distinct")})
    for v, (u, delay) in (echoed or {}).items():
        if v in feats and v not in roles:
            roles[v] = Role(v, DOUBLE, of=u, evidence={"echo_ms": round(delay * 1000, 1)})
    tonal = [v for v in feats if v not in roles and feats[v]["median"] is not None]
    # doublings: a voice playing another's notes a fixed delay (or an octave) apart is that voice's double
    for v in tonal:
        for u in tonal:
            if u == v or u in roles or v in roles:
                continue
            d = _doubles(by_voice[u], by_voice[v])
            if d and d[0] >= 0.8 and feats[v]["notes"] <= feats[u]["notes"] * 1.2 and (d[1] > 0.02 or v > u):
                roles[v] = Role(v, DOUBLE, of=u, evidence={"share": round(d[0], 2), "delay": d[1]})
    tonal = [v for v in tonal if v not in roles]
    if not tonal:
        return sorted(roles.values(), key=lambda r: r.voice)
    lowest = min(tonal, key=lambda v: feats[v]["median"])
    for v in tonal:
        f = feats[v]
        if f["median"] <= feats[lowest]["median"] + 3 and f["median"] < 55:
            roles[v] = Role(v, BASS, evidence={"median": round(f["median"], 1)})
    rest = [v for v in tonal if v not in roles]
    # held chords: notes of two beats and more
    for v in rest:
        if feats[v]["length_beats"] >= 2.0:
            roles[v] = Role(v, HARMONY, evidence={"length_beats": round(feats[v]["length_beats"], 2)})
    rest = [v for v in rest if v not in roles]
    # the melody: the most varied line, leaning toward the top
    def melodic(v):
        f = feats[v]
        return f["entropy"] * (1 + f["steps"]) * (1 - f["repeats"]) + (f["median"] - 60) / 24
    if rest:
        top = max(rest, key=melodic)
        roles[top] = Role(top, MELODY, evidence={k: round(feats[top][k], 2) for k in ("entropy", "steps", "median")})
    for v in rest:
        if v in roles:
            continue
        f = feats[v]
        if f["per_beat"] >= 2.0 and f["distinct"] <= 8 and f["steps"] < 0.5:
            roles[v] = Role(v, ARP, evidence={"per_beat": round(f["per_beat"], 2), "distinct": f["distinct"]})
        elif f["entropy"] >= 2.5 and f["steps"] >= 0.4:
            roles[v] = Role(v, COUNTER, evidence={"entropy": round(f["entropy"], 2), "steps": round(f["steps"], 2)})
        else:
            roles[v] = Role(v, ACCOMP, evidence={"per_beat": round(f["per_beat"], 2), "distinct": f["distinct"]})
    return sorted(roles.values(), key=lambda r: r.voice)
