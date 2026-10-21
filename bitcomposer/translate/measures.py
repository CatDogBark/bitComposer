"""Measures in common: the yardsticks of ANALYSIS.md read from notes on
beats, not from the generator's channel layout, so a soundtrack's readings
and the generator's songs are measured alike, into one table (the readings
database's features: source "soundtrack" or "generator").

A score is notes in beats, each with its part's role, and the bars. A
reading gives one from its played notes (its first time through: up to
where it loops back), the generator from its patterns (a channel's role
from its layout). A doubling (an echo played by a voice, or the
generator's echo channels) is left out: it measures its source again.

    bpm                  the tempo
    seconds              the length, once through
    melody_per_beat      notes a beat, a voice of the part (bass_, harmony_, arp_ the same)
    drums_per_bar        drum hits a bar, all pieces
    mel_step_pct         melody moves of one or two semitones
    mel_leap_pct         moves of a fourth or more
    mel_same_pct         a note repeated
    mel_range            semitones from its 10th to its 90th percentile
    mel_motif_pct        interval 4-grams heard more than once
    ioi_kinds            gaps between melody notes, kinds carrying 2 % or more of them
    mel_bar_repeat_pct   bars of the melody heard before: a bar's length of it from an
                         earlier beat, the same rhythm and three quarters of the pitches
    mel_rhythm_reuse_pct bars whose rhythm was heard before, the same way
    mel_strong_fit_pct   notes on a bar's first or middle beat that are chord tones over the bass
    off_eighth_pct       pitched onsets off the eighths
    triplet_pct          of them, on a triplet
    chord_tones          pitch classes sounding a beat over the harmony, arp and counter-line
    bar_repeat_pct       bars of all the pitched parts heard before (three quarters of their notes)

A repeat is looked for from every earlier beat, not only from bar lines:
a bar line read a beat off, a pickup, or a beat read at double the tempo
(bars of half the length) would hide it.
"""
import bisect
import math
import statistics
from collections import Counter
from dataclasses import dataclass

from . import roles as R

MELODY, BASS, HARMONY, ARP, DRUMS = "melody", "bass", "harmony", "arp", "drums"
GROUPS = {R.MELODY: MELODY, R.BASS: BASS, R.HARMONY: HARMONY, R.ACCOMP: HARMONY,
          R.COUNTER: HARMONY, R.ARP: ARP, R.DRUMS: DRUMS}   # the generator's counter-line is on a harmony channel
NEAR = 0.06                          # beats: an onset this close to a grid point is on it
STEP = 12                            # onsets compared on twelfths of a beat (eighths, sixteenths, triplets)
CHORD_TONES = {0, 3, 4, 7, 10, 11}   # root, either third, fifth, either seventh
KINDS = 0.02
SAME = 0.75


@dataclass
class Note:
    beat: float                      # its start, in beats from the first
    beats: float | None              # its length in beats; None: still sounding at the end
    midi: float | None               # None: unpitched
    group: str                       # melody, bass, harmony, arp, drums
    voice: int
    level: float = 1.0               # its loudness, 0 to 1 (the chord reader weighs by it)


@dataclass
class Score:
    notes: list[Note]                # in order of their start
    bars: list[float]                # each bar's first beat
    end: float                       # beats, once through
    bpm: float
    seconds: float


def of_reading(r) -> Score | None:
    """A reading's notes in beats, once through; None for a song in free time."""
    g = r.grid
    if not g or len(g.bar_times) < 2:
        return None
    f = r.form
    end_t = r.song.seconds
    if f and f.loop_bar is not None and f.loop_seconds and f.loop_bar < len(g.bar_times):
        end_t = min(end_t, g.bar_times[f.loop_bar] + f.loop_seconds)
    group = {x.voice: GROUPS.get(x.role) for x in r.roles}
    notes = []
    for p in r.song.notes:
        if p.start >= end_t or not group.get(p.voice):
            continue
        b = g.beats(p.start)
        length = None if p.end is None else g.beats(p.end) - b
        notes.append(Note(b, length, None if group[p.voice] == DRUMS else p.midi, group[p.voice], p.voice))
    end = g.beats(end_t)
    bars = [g.beats(t) for t in g.bar_times if t < end_t]
    return Score(notes, bars, end, g.bpm, end_t - g.bar_times[0])


def of_composed(song: dict) -> Score:
    """A composed song's notes (compose_song's dict), by its channel layout.
    A note's level is its loudness as the player sets it (the volume column
    or the sample's default, the sample's global volume, the channel's), the
    loudest pitched note's 1, as a decoded note's volume is 0 to 1."""
    from ..it_format import FX_SPECIAL, S_NOTE_DELAY, it_tempo_to_bpm
    from ..pattern import CHANNEL_ROLES, ROWS_PER_BEAT, ROWS_PER_BAR
    drum = {"kick", "snare", "hihat", "tom", "crash", "openhat"}
    group = {ch: DRUMS if role in drum else role for ch, role in enumerate(CHANNEL_ROLES)
             if role in drum or role in (MELODY, BASS, HARMONY, ARP)}
    speed = song["speed"]
    samples = song.get("samples", [])
    if song.get("info"):
        from ..mix import channel_volumes_for
        channel = channel_volumes_for(song["info"])
    else:
        channel = [64] * len(CHANNEL_ROLES)

    def level(cell, ch: int) -> float:
        s = samples[cell.instrument - 1] if 0 < cell.instrument <= len(samples) else None
        column = cell.volume if cell.volume <= 64 else (s.default_volume if s else 64)
        return column / 64 * (s.global_volume / 64 if s else 1.0) * channel[ch] / 64

    notes, open_ = [], {}
    row0 = 0
    for o in song["orders"]:
        if o >= len(song["patterns"]):
            continue
        pat = song["patterns"][o]
        for r, row in enumerate(pat.data):
            for ch, g in group.items():
                if ch >= len(row):
                    continue
                cell = row[ch]
                if not cell.note:
                    continue
                at = row0 + r
                if cell.effect == FX_SPECIAL and cell.effect_val & 0xF0 == S_NOTE_DELAY:
                    at += (cell.effect_val & 0x0F) / speed
                beat = at / ROWS_PER_BEAT
                if ch in open_:                  # a new note, a cut or an off ends the one before
                    before = open_.pop(ch)
                    before.beats = beat - before.beat
                if cell.note < 120 and cell.volume != 0:
                    n = Note(beat, None, None if g == DRUMS else float(cell.note), g, ch, level(cell, ch))
                    notes.append(n)
                    open_[ch] = n
        row0 += pat.rows
    loudest = max((n.level for n in notes if n.midi is not None), default=1.0) or 1.0
    for n in notes:
        n.level /= loudest
    notes.sort(key=lambda n: n.beat)
    end = row0 / ROWS_PER_BEAT
    bpm = it_tempo_to_bpm(song["tempo"], speed)
    return Score(notes, [b / ROWS_PER_BEAT for b in range(0, row0, ROWS_PER_BAR)], end, bpm, end * 60 / bpm)


def _on(beat: float, step: float) -> bool:
    x = beat / step
    return abs(x - round(x)) * step < NEAR


def _line(notes: list[Note]) -> list[Note]:
    """The melody as one line: of notes struck together, the highest."""
    out = []
    for n in notes:
        if out and n.beat - out[-1].beat < NEAR:
            if n.midi > out[-1].midi:
                out[-1] = n
            continue
        out.append(n)
    return out


def _bar_of(bars: list, beat: float) -> int:
    lo, hi = 0, len(bars) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if bars[mid] <= beat:
            lo = mid
        else:
            hi = mid - 1
    return lo


def _bar_length(s: Score) -> float:
    """The bar most of the song is in, in beats."""
    lengths = Counter(round(b - a) for a, b in zip(s.bars, s.bars[1:]))
    return float(max(lengths, key=lengths.get)) if lengths else 4.0


def _windows(s: Score, length: float):
    """Each bar line, with the beats a bar's length from which have ended since the bar before's
    (from the first note's beat: a pickup before the first bar line comes back too)."""
    if not s.bars:
        return
    k = math.floor(min([s.bars[0]] + [n.beat for n in s.notes[:1]]) + NEAR)
    for at in s.bars:
        earlier = []
        while k + length <= at + NEAR:
            earlier.append(k)
            k += 1
        yield at, earlier


def _cell(notes: list, starts: list, at: float, length: float, what) -> list:
    """The notes (starts: their beats) from `at` for `length` beats: (onset in twelfths of a beat
    from `at`, what(note)), in order."""
    lo = bisect.bisect_left(starts, at - NEAR)
    hi = bisect.bisect_left(starts, at + length - NEAR)
    return [(round((n.beat - at) * STEP), what(n)) for n in notes[lo:hi]]


def _pct(n: int, total: int) -> float:
    return 100.0 * n / total if total else 0.0


def measure(s: Score) -> dict:
    """The yardsticks of a score (the module's list)."""
    out = {"bpm": s.bpm, "seconds": s.seconds}
    first = s.bars[0] if s.bars else 0.0
    span = max(s.end - first, 1.0)
    by = {}
    for n in s.notes:
        if n.beat >= first:
            by.setdefault(n.group, []).append(n)
    for g in (MELODY, BASS, HARMONY, ARP):
        notes = by.get(g, [])
        voices = len({n.voice for n in notes}) or 1
        out[f"{g}_per_beat"] = len(notes) / span / voices
    out["drums_per_bar"] = len(by.get(DRUMS, [])) / max(len(s.bars), 1)

    line = _line([n for n in by.get(MELODY, []) if n.midi is not None])
    pitches = [round(n.midi) for n in line]
    moves = [b - a for a, b in zip(pitches, pitches[1:])]
    out["mel_step_pct"] = _pct(sum(1 for m in moves if 1 <= abs(m) <= 2), len(moves))
    out["mel_leap_pct"] = _pct(sum(1 for m in moves if abs(m) >= 5), len(moves))
    out["mel_same_pct"] = _pct(sum(1 for m in moves if m == 0), len(moves))
    if len(pitches) >= 10:
        q = statistics.quantiles(pitches, n=10)
        out["mel_range"] = q[-1] - q[0]
    else:
        out["mel_range"] = float(max(pitches) - min(pitches)) if pitches else 0.0
    grams = Counter(tuple(moves[i:i + 4]) for i in range(len(moves) - 3))
    out["mel_motif_pct"] = _pct(sum(c for c in grams.values() if c > 1), sum(grams.values()))
    gaps = Counter(round((b.beat - a.beat) * STEP) for a, b in zip(line, line[1:]))
    out["ioi_kinds"] = float(sum(1 for c in gaps.values() if c >= KINDS * sum(gaps.values())))

    # Bars of the melody heard before: each bar's notes (onsets in twelfths of a beat, pitches)
    # against a bar's length of the melody from every earlier beat, so a bar line read a beat
    # off, or a pickup, does not hide a repeat.
    length = _bar_length(s)
    whole = _line([n for n in s.notes if n.group == MELODY and n.midi is not None])   # a pickup too
    at_line = [n.beat for n in whole]
    rhythms, repeat, reuse, heard = {}, 0, 0, 0
    for at, earlier in _windows(s, length):
        cell = _cell(whole, at_line, at, length, lambda n: round(n.midi))
        for k in earlier:
            e = _cell(whole, at_line, k, length, lambda n: round(n.midi))
            if e:
                rhythms.setdefault(tuple(x[0] for x in e), []).append(tuple(x[1] for x in e))
        if not cell:
            continue
        heard += 1
        rhythm, tune = tuple(x[0] for x in cell), tuple(x[1] for x in cell)
        reuse += rhythm in rhythms
        repeat += any(sum(a == b for a, b in zip(tune, t)) >= SAME * len(tune) for t in rhythms.get(rhythm, ()))
    out["mel_bar_repeat_pct"] = _pct(repeat, heard)
    out["mel_rhythm_reuse_pct"] = _pct(reuse, heard)

    # On a bar's first and middle beats: a chord tone over the bass struck last in the bar?
    bass = [n for n in by.get(BASS, []) if n.midi is not None]
    starts = [n.beat for n in bass]
    strong = fit = 0
    for n in line:
        i = _bar_of(s.bars, n.beat)
        span_i = (s.bars[i + 1] if i + 1 < len(s.bars) else s.end) - s.bars[i]
        at = n.beat - s.bars[i]
        if not (abs(at) < NEAR or (round(span_i) % 2 == 0 and abs(at - span_i / 2) < NEAR)):
            continue
        k = bisect.bisect_right(starts, n.beat + NEAR) - 1
        if k < 0 or starts[k] < s.bars[i] - NEAR:
            continue
        strong += 1
        fit += (round(n.midi) - round(bass[k].midi)) % 12 in CHORD_TONES
    out["mel_strong_fit_pct"] = _pct(fit, strong)

    pitched = [n for n in s.notes if n.midi is not None and n.beat >= first]
    off = [n for n in pitched if not _on(n.beat - first, 0.5)]
    out["off_eighth_pct"] = _pct(len(off), len(pitched))
    out["triplet_pct"] = _pct(sum(1 for n in off if _on(n.beat - first, 1 / 3)), len(off))

    # Pitch classes sounding each beat over the parts between the melody and the bass.
    inner = [n for g in (HARMONY, ARP) for n in by.get(g, []) if n.midi is not None]
    beats = {}
    for n in inner:
        stop = n.beat + (n.beats if n.beats is not None else s.end - n.beat)
        for b in range(math.floor(n.beat - first), math.ceil(stop - first)):
            if b < span:
                beats.setdefault(b, set()).add(round(n.midi) % 12)
    out["chord_tones"] = statistics.mean(len(v) for v in beats.values()) if beats else 0.0

    # Bars repeated, all pitched parts: three quarters of a bar's notes a bar's length from an earlier beat.
    index, sizes, repeat, heard = {}, [], 0, 0
    sounded = [n for n in s.notes if n.midi is not None]
    at_pitched = [n.beat for n in sounded]
    for at, earlier in _windows(s, length):
        for k in earlier:
            notes = set(_cell(sounded, at_pitched, k, length, lambda n: (n.group, round(n.midi))))
            for x in notes:
                index.setdefault(x, []).append(len(sizes))
            sizes.append(len(notes))
        notes = set(_cell(sounded, at_pitched, at, length, lambda n: (n.group, round(n.midi))))
        if not notes:
            continue
        heard += 1
        shared = Counter(w for x in notes for w in index.get(x, ()))
        repeat += any(c >= SAME * max(len(notes), sizes[w]) for w, c in shared.items())
    out["bar_repeat_pct"] = _pct(repeat, heard)
    return out


def keep(db, song: str, source: str, values: dict) -> None:
    """A song's measures into the features table (source: soundtrack or generator)."""
    db.execute("DELETE FROM features WHERE song = ? AND source = ?", (song, source))
    db.executemany("INSERT INTO features VALUES (?,?,?,?)",
                   [(song, source, k, float(v)) for k, v in values.items()])
    db.commit()
