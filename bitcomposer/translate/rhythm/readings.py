"""The vocabulary from the readings (stage 4 of docs/TRANSLATOR.md), the
rhythm half, counted: each part's rhythms bar by bar, the bass's and the
drums' figures as played, and the melody's intervals and lengths, over a
game's songs in the readings database.

    python -m bitcomposer.translate.rhythm [--db PATH] [--game NAME] [--top N] [--spc DIR]

The songs are the harmony counts' (vocab.py): each once through, to where
it loops; a song in free time, or whose chord beats are mostly unfit or
silent, is left out. A voice doubling another is left out as everywhere,
and so is a note at no volume; a voice read as a roll (notes on no grid of
the song's) is left out of the patterns, since it has none, but counted
where the onsets fall.

Rhythms. A bar is the song's own, from its bar lines, and only bars of the
song's meter are counted: a bar of another length is a grid section
restarting where its timing slipped (stage 1's known gap; most of Dancing
Mad's bars) or a meter changed for a bar, and is left out, the share said.
A part's onsets in a bar (its voices together; notes struck within NEAR of
each other are one onset, so a chord struck in three voices is one) are
placed on the song's grid, at the nearest multiple of its division
(sixteenths, triplets, both; a loose song's as it was read), as fractions of
a beat from the bar line. The bar's pattern is those positions drawn four
characters a beat: x on a quarter of the beat, t on a third, ~ finer than
either, at the nearest (so a roll of 32nds reads as sixteenths; the table of
where onsets fall says how much is finer). Patterns are counted per part
and per meter, with the share of the part's bars each covers and how many
songs it is heard in (one song's ostinato covers as many bars as a figure
forty songs share), a bar the part rests in counting as a rest. How dense each part plays is onsets a
bar, and where they fall: on the beat, an eighth, a sixteenth, a triplet (a
third or a sixth of a beat), or finer, which gives the share off the
eighths and, of those, on a triplet, as stage 2's measures count them
(measures.py), reckoned their way too for the comparison (every pitched
part together, within NEAR of an eighth, the median over songs; they count
a silent note, and a song with nothing off the eighths as none on a
triplet, so they read a little apart).

Bass figures. The bass's bar as its rhythm with the chord tone of each
note in its place, the chord from the song's chord spans at the note's
onset (R root, 3 third, s a sus chord's tone, 5 fifth, 7 seventh, + another
tone, ? no chord read or an unfit one), r a root an octave or more above
the bar's lowest bass note (the octave bass; the other tones are not told
apart by octave). Of notes struck together the lowest is the bass's line,
and its moves from note to note are counted by size, as the melody's.

Drum figures. The drums' bar as which sound plays where. The readings keep
each hit's sample, not what it is; a sound is named by its sound (drums.py:
kick, snare, hat or another) when the game's SPC files are at hand (--spc),
its hits settling only a bodiless burst between a hat and a cymbal. Without
them it is named by how the game plays it, over all its songs: one playing
DENSE hits a bar or more where it plays is the hat (hi-hats and rides keep
time); of the rest, one landing on the bar's first beat more than on its
backbeats is the kick, the other way the snare, as often one as the other
another sound; which misnames an open hat on the off-eighths a snare and a
cymbal held long a kick (FFVI's did, checked by ear 2026-10-20). The sounds
are listed with their profiles so the names can be judged. A bar's figure
is each sound's positions, drawn as the parts' are.

Melody. The melody as one line (of notes struck together, the highest, as
measures.py takes it), its moves from note to note in semitones by size
(a repeat, a step of one or two, a third, a fourth, a tritone, a fifth, a
sixth, a seventh, an octave, more) and direction, and the semitones
themselves; its notes' lengths as the time to the next note, in beats (the
value a score would write), on the song's grid, and how much of that the
note sounds (a note cut short of three quarters of it is detached).
against.py sets songs composed with a pack beside these counts."""
from __future__ import annotations
import argparse
import bisect
import json
import math
from fractions import Fraction
import statistics
import bisect
import statistics
import sys
from array import array
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from fractions import Fraction

from .. import drums as drums_mod, roles as R, store, tables, vocab
from ..vocab import FIT, MARKS, SOUNDS, Span, _beats_at, _buckets, _median, _pct, _sounding, tone_of
from ..vocab import TONES as CHORD_TONES

from . import cells as cells_mod, chords as chords_mod, arrangement as arrangement_mod   # noqa: E402  the package's other sections


NEAR = 0.06                          # beats: onsets this close are one, and this close to an eighth is on it
PARTS = (R.BASS, R.HARMONY, R.ACCOMP, R.ARP, R.COUNTER, R.MELODY, R.DRUMS)
PITCHED = PARTS[:-1]
DENSE = 6                            # hits a bar a drum sound plays, where it plays, to be the hat
PIECES = ("kick", "snare", "hat", "tom", "cymbal", "other")     # drums.PIECES; a sample named "none" is no drum
LETTERS = dict(zip(PIECES, "KShtco"))
SHORT = 0.75                         # a melody note sounding less of its length than this is detached
TONE_MARKS = {"root": "R", "third": "3", "sus": "s", "fifth": "5", "seventh": "7", "other": "+"}
SIZES = ((0, "repeat"), (2, "step"), (4, "third"), (5, "fourth"), (6, "tritone"), (7, "fifth"), (9, "sixth"),
         (11, "seventh"), (12, "octave"), (1e9, "more"))
VALUES = ((Fraction(1, 4), "a sixteenth"), (Fraction(1, 3), "a triplet eighth"), (Fraction(1, 2), "an eighth"),
          (Fraction(2, 3), "two triplet eighths"), (Fraction(3, 4), "a dotted eighth"), (Fraction(1), "a beat"),
          (Fraction(3, 2), "a beat and a half"), (Fraction(2), "two beats"), (Fraction(3), "three beats"),
          (Fraction(4), "four beats"), (Fraction(1e9), "longer"))
PLACES = ("beat", "eighth", "sixteenth", "triplet", "finer")
REST = "(rest)"
BANDS = ((85, "slow"), (130, "medium"), (1e9, "fast"))    # BPM: the readings' songs' tertiles (1562 songs, 2026-10-21)
START = "start"                      # the previous bar's pattern where there is none: the part's first bar, or after a gap


class Tally(Counter):
    """Bars by pattern, and in how many songs each pattern is heard."""

    def __init__(self):
        super().__init__()
        self.songs = Counter()

    def add(self, keys) -> None:
        """A song's bars' patterns."""
        self.update(keys)
        self.songs.update(set(keys))


@dataclass
class Song:
    """What a song's reading gives the counts: its meter, its grid's division,
    its bars (start, end in beats, once through), its chord spans and its
    notes by part (start, length, midi, sample key; in beats)."""
    title: str
    meter: int
    division: int
    bars: list
    chords: list
    notes: dict = field(default_factory=dict)   # role -> [(start, length, midi, sample), ...]
    rolls: dict = field(default_factory=dict)   # role -> notes of its roll voices, left out of the patterns
    bpm: float = 120.0                          # its tempo: how long a drum is held, in seconds
    sid: str = ""                               # its id in the readings
    game: str = ""
    numbers: list = field(default_factory=list)   # each bar's number in the reading (form's bars count them), beside `bars`
    parts: list = field(default_factory=list)     # the form's parts: (first bar number, bars, the earlier part repeated or None, letter)
    sections: list = field(default_factory=list)  # the form's sections (a short part played again at once joined), the same shape
    pieces: dict = field(default_factory=dict)    # sample key -> the piece the reading named it (drums.PIECES, "none")
    tonic: int | None = None                      # the key reader's tonic and mode (the harmony units' degrees)
    mode: str = "major"
    loop_bar: int | None = None                   # the bar number the loop returns to
    voices: list = field(default_factory=list)    # every voice the role reader named: (voice, role, of, evidence dict)
    bass_voices: dict = field(default_factory=dict)   # voice -> its notes, where the bass role holds two voices or more
    voice_notes: dict = field(default_factory=dict)   # voice -> (role, its notes), every part's voice (rolls left out)
    copies: dict = field(default_factory=dict)        # a planned song: role -> [(first bar, bars, the bar copied from)], the band
                                                      # coming back with the theme (the writers copy their own earlier bars there)
    periods: dict = field(default_factory=dict)       # a planned song: role -> {bar index: the lag in bars whose bar it plays again}
                                                      # (the plan's held bars of a backing part's period, period_units)
    feel: str | None = None                           # the song's feel, duple or triple (song_feel); a planned song's drawn once
    levels: dict = field(default_factory=dict)        # role -> the median level (0-1 of full) of its notes, as the readings heard them
    voice_levels: dict = field(default_factory=dict)  # voice -> the median level of its notes
    note_levels: dict = field(default_factory=dict)   # role -> [(start, level)] for every note the readings heard (section_levels, round 48)
    kit_levels: dict = field(default_factory=dict)    # a drum sample's key -> the median level of the notes struck on it (round 68: the kit's
                                      # level a piece, the part's one median being the hat's where the hat is the most frequent piece)
    loudness: float | None = None                    # the song's rendered loudness, RMS dBFS over its first minute through the player (the
                                      # readings' feature render/loudness_dbfs, round 59); None where it was not measured
    echo: tuple | None = None                        # the song's echo as the chip had it (round 70; the readings' features of source "echo",
                                      # reading.echo_of_notes): (volume of full, delay in ms, feedback); None where never read
    echo_sends: dict = field(default_factory=dict)   # voice -> the share of its notes that send to the echo
    vibrato: dict = field(default_factory=dict)      # voice -> its vibrato on its held notes (round 72; the readings' features of source
                                      # "vibrato", reading.vibrato_of_notes): {"held": [by length class], "vib": [by class], "depth",
                                      # "rate", "onset" (the last three where it carries any)}; empty where never read


LOUDNESS_REF = 0.25                  # -12 dBFS: the loudness a level of 1.0 means, a sample's loop body at RMS (the pack's median; round 56)
SAMPLE_LOUDNESS: dict = {}           # a pack's sample id ("s" + the key's first ten) -> its loop body's RMS, 0-1 (set_loudness); a drum's strike's
STRIKE_SECONDS = 0.15                # seconds of a percussion sample its loudness is read over (its strike)


SAMPLE_STRIKE: dict = {}             # a pack's sample id -> the RMS of its first STRIKE_SECONDS, 0-1 (set_loudness; round 65)


def heard_rms(strike: float, body: float, seconds: float) -> float:
    """The loudness a note of `seconds` hears from its sample: the strike's for STRIKE_SECONDS, the body's after, in power
    (round 65: a short chord on a struck sample is as loud as its attack, a long note on a slow one as its body)."""
    if seconds <= STRIKE_SECONDS or body <= 0:
        return strike if strike > 0 else body
    return math.sqrt((strike * strike * STRIKE_SECONDS + body * body * (seconds - STRIKE_SECONDS)) / seconds)


def loudness_factor(key, seconds: float | None = None) -> float:
    """What a note's level is multiplied by to be its loudness (round 56, 2026-10-29): its sample's own loudness over the
    reference, 1.0 for a sample the table does not know. The readings' level is a voice volume, set by the game's composer to
    balance that song's samples; a written song takes its levels from one song's token and its samples from the instrument
    word, and the pack's tonal samples span 19.8 dB in their own loudness, so a level without its sample had put a hot bass
    5 dB over its tune and a brass lead 7 dB under its bass (Song Check 43's Whole 68 and 70)."""
    if not SAMPLE_LOUDNESS or not isinstance(key, str):
        return 1.0
    sid = "s" + key[:10]
    rms = SAMPLE_LOUDNESS.get(sid)
    if not rms:
        return 1.0
    if seconds is not None and SAMPLE_STRIKE.get(sid):     # the note's own length: its strike, then the body (round 65)
        return heard_rms(SAMPLE_STRIKE[sid], rms, seconds) / LOUDNESS_REF
    return rms / LOUDNESS_REF


def set_loudness(table: dict, strikes: dict | None = None) -> None:
    SAMPLE_LOUDNESS.clear()
    SAMPLE_LOUDNESS.update(table)
    SAMPLE_STRIKE.clear()
    SAMPLE_STRIKE.update(strikes or getattr(table, "strikes", {}))


def load_loudness(pack_dir) -> dict:
    """Each sample's loudness (0-1) from a pack folder's WAVs: a tonal sample's loop-body RMS, a percussion sample's
    strike RMS (its first STRIKE_SECONDS; round 63: a kit had played at the raw voice level as if its samples sat at
    the reference, and the pack's kit rendered 7 dB under what was counted); {pack id: rms}."""
    import json, wave, array
    from pathlib import Path
    pack_dir = Path(pack_dir)
    data = json.loads((pack_dir / "pack.json").read_text(encoding="utf-8"))
    out, strikes = {}, {}
    for sid, spec in data.get("samples", {}).items():
        if not spec.get("file"):
            continue
        try:
            w = wave.open(str(pack_dir / spec["file"]))
            rate = w.getframerate() or 32000
            x = array.array("h", w.readframes(w.getnframes()))
        except Exception:
            continue
        strike = x[:max(1, int(rate * STRIKE_SECONDS))]
        if spec.get("percussion"):
            body = strike
        else:
            lp = spec.get("loop")
            body = x[lp[0]:lp[1]] if lp and len(lp) == 2 and lp[1] > lp[0] else x
        if len(body):
            out[sid] = math.sqrt(sum(v * v for v in body) / len(body)) / 32768
            strikes[sid] = math.sqrt(sum(v * v for v in strike) / len(strike)) / 32768 if len(strike) else out[sid]
    out = _Loudness(out)
    out.strikes = strikes                                   # set_loudness reads them (round 65: a note hears its sample's strike, then its body)
    return out


class _Loudness(dict):
    """A loudness table with its samples' strikes beside it (.strikes)."""
    strikes: dict = {}


def load(db, game: str | None = None) -> tuple[list[Song], dict]:
    """The songs to count (game: only that game's), and why the others were
    left out: {"free time": n, "mostly silent": n}; the harmony counts' songs."""
    songs, out = [], Counter()
    where, args = ("WHERE game = ?", (game,)) if game else ("", ())
    for sid, title, meter, division, seconds, loop_bar, loop_seconds, bpm, game_name, tonic, mode in db.execute(
            f"SELECT id, title, meter, division, seconds, loop_bar, loop_seconds, bpm, game, key_tonic, key_mode "
            f"FROM songs {where}", args):
        row = db.execute("SELECT beats, bars FROM beats WHERE song = ?", (sid,)).fetchone()
        if division is None or not row:
            out["free time"] += 1
            continue
        beats, bars = array("d"), array("d")
        beats.frombytes(row[0])
        bars.frombytes(row[1])
        end = _beats_at(beats, seconds)
        if loop_bar is not None and loop_seconds and loop_bar < len(bars):
            end = min(end, _beats_at(beats, bars[loop_bar] + loop_seconds))
        chords = [Span(a, min(b, end), root, shape, fit) for a, b, root, shape, fit in
                  db.execute("SELECT start, end, root, shape, fit FROM chords WHERE song = ? ORDER BY start", (sid,))
                  if a < end]
        total = sum(c.beats for c in chords)
        if not total or sum(c.beats for c in chords if c.root is not None and c.fit >= FIT) <= total / 2:
            out["mostly silent"] += 1
            continue
        lines = [b for b in (_beats_at(beats, t) for t in bars) if b < end]
        ends = lines[1:] + [lines[-1] + meter] if lines else []
        kept = [(k, a, min(b, end)) for k, (a, b) in enumerate(zip(lines, ends)) if min(b, end) - a >= 1 - NEAR]
        song = Song(title, meter, division, [(a, b) for _, a, b in kept], chords, bpm=bpm or 120.0, sid=sid,
                    game=game_name or "", numbers=[k for k, _, _ in kept],
                    parts=[(bar, n, of, label) for bar, n, of, label in db.execute(
                        "SELECT bar, bars, [of], label FROM form WHERE song = ? AND level = 'part' ORDER BY bar", (sid,))],
                    sections=[(bar, n, of, label) for bar, n, of, label in db.execute(
                        "SELECT bar, bars, [of], label FROM form WHERE song = ? AND level = 'section' ORDER BY bar", (sid,))],
                    tonic=tonic, mode=mode or "major", loop_bar=loop_bar)
        keys, song.pieces = {}, {}
        for idx, key, piece in db.execute("SELECT idx, key, piece FROM samples WHERE song = ?", (sid,)):
            keys[idx] = key
            song.pieces[key] = piece
        basses = {}
        level_rows, kit_rows = {}, {}
        for voice, role, of, evidence, blob in db.execute("SELECT voice, role, [of], evidence, notes FROM voices WHERE song = ?", (sid,)):
            try:
                song.voices.append((voice, role, of, json.loads(evidence) if evidence else {}))
            except ValueError:
                song.voices.append((voice, role, of, {}))
            if role in PARTS:
                into = song.rolls if evidence and '"roll"' in evidence else song.notes
                rows = [r for r in store.unpack(blob) if r[0] < end and r[3] > 0 and (role == R.DRUMS or not math.isnan(r[2]))]
                if SAMPLE_LOUDNESS:                         # a level as loudness: the voice volume times its sample's own (round 56; the drums' too, round 63)
                    secs = 60.0 / (bpm or 120.0)                # the note's length in seconds: its strike, then its body (round 65)
                    rows = [(s, length, m, level * loudness_factor(keys.get(int(i), "noise"), length * secs), pan, i) for s, length, m, level, pan, i in rows]
                mine = [(s, length, m, keys.get(int(i), "noise")) for s, length, m, level, _, i in rows]
                into.setdefault(role, []).extend(mine)
                if into is song.notes:
                    song.voice_notes[voice] = (role, mine)
                    finite = [r[3] for r in rows if not math.isnan(r[3])]   # a kit's unread levels (NaN) are notes, not levels: a
                    if finite:                                                   # median over them was NaN, and three FFVI balance tokens
                        song.voice_levels[voice] = statistics.median(finite)   # carried "nan" for the drums, which a written song
                        level_rows.setdefault(role, []).extend(finite)         # played at full (2026-10-30)
                        song.note_levels.setdefault(role, []).extend((r[0], r[3]) for r in rows)
                    if role == R.DRUMS:                     # the kit's level a sample (round 68): the part's one median is the most
                        for r in rows:                      # frequent piece's, the hat's in a kick-snare-hat kit, and the kick plays near full
                            if not math.isnan(r[3]):
                                kit_rows.setdefault(keys.get(int(r[5]), "noise"), []).append(r[3])
                if role == R.BASS and into is song.notes:
                    basses[voice] = mine
        if len(basses) >= 2:
            song.bass_voices = basses
        song.levels = part_levels(song, {role: statistics.median(ls) for role, ls in level_rows.items()})
        song.kit_levels = {key: statistics.median(ls) for key, ls in kit_rows.items()}
        row = db.execute("SELECT value FROM features WHERE song = ? AND source = 'render' AND name = 'loudness_dbfs'", (sid,)).fetchone()
        song.loudness = float(row[0]) if row else None   # the song's rendered loudness (round 59)
        echo = dict(db.execute("SELECT name, value FROM features WHERE song = ? AND source = 'echo'", (sid,)).fetchall())   # the chip's echo
        if all(k in echo for k in ("volume", "delay_ms", "feedback")):                                                      # (round 70)
            song.echo = (float(echo["volume"]), float(echo["delay_ms"]), float(echo["feedback"]))
            song.echo_sends = {int(k[6:]): float(v) for k, v in echo.items() if k.startswith("voice_")}
        song.vibrato = vibrato_of_features(dict(db.execute("SELECT name, value FROM features WHERE song = ? AND source = 'vibrato'", (sid,)).fetchall()))
        songs.append(song)
    return songs, dict(out)


def vibrato_of_features(rows: dict) -> dict:
    """The readings' vibrato features (reading.vibrato_of_notes's names) as {voice: {"held": [by class], "vib": [by class],
    "depth", "rate", "onset"}} (round 72)."""
    out = {}
    for name, value in rows.items():
        if not name.startswith("voice_"):
            continue
        parts = name.split("_")
        v = int(parts[1])
        d = out.setdefault(v, {"held": [0, 0, 0, 0], "vib": [0, 0, 0, 0]})
        if len(parts) == 4 and parts[2] in ("held", "vib"):
            d[parts[2]][int(parts[3])] = int(value)
        elif len(parts) == 3 and parts[2] in ("depth", "rate", "onset"):
            d[parts[2]] = float(value)
    return out


def part_levels(song: Song, pooled: dict) -> dict:
    """A part's level: its LINE voice's median level where the part holds two voices or more (the line as the layer
    words see it, cells.line_voice: the busiest voice, the bass's the one with the longest notes), the median over all
    its notes (`pooled`) for a part of one voice, for the drums (the kit's level is a piece's, round 68) and where the
    line's level was never read. Round 70 (2026-10-30): the part's one median had pooled every voice's notes, so where
    the voices differ in level the line landed off: Troops March on's counter line sits at 0.27 of the top and played
    at 0.40, its bass line at 0.62 and played at 1.0 with the second voice at 1.6 of that. The voices beside the line
    are counted against the line (voice_level_shares), so line × share now reproduces every voice."""
    out = dict(pooled)
    for role in PITCHED:
        if role not in out:
            continue
        voices = cells_mod.part_voices(song, role)
        if len(voices) < 2:
            continue
        level = song.voice_levels.get(cells_mod.line_voice(voices, role))
        if level is not None and math.isfinite(level):
            out[role] = level
    return out


def position(offset: float, division: int) -> Fraction:
    """An onset's place in its bar, beats from the bar line, on the grid."""
    return Fraction(round(offset * division), division)


def place(p: Fraction) -> str:
    """Where a position falls (PLACES): on the beat, an eighth, a sixteenth, a triplet, or finer."""
    f = p - math.floor(p)
    return ("beat" if f == 0 else "eighth" if f.denominator == 2 else "sixteenth" if f.denominator == 4
            else "triplet" if f.denominator in (3, 6) else "finer")


def draw(positions, beats: int, marks: dict | None = None) -> str:
    """A bar's positions as text, four characters a beat: x on a quarter of
    the beat, t on a third, ~ finer than either, at the nearest; a position
    in `marks` draws as its mark instead. Nothing struck: REST."""
    cells = [["."] * 4 for _ in range(beats)]
    rank = {".": 0, "~": 1, "t": 2, "x": 3}
    for p in positions:
        b = math.floor(p)
        f = p - b
        if b >= beats:
            continue
        mark = "x" if f.denominator in (1, 2, 4) else "t" if f.denominator in (3, 6) else "~"
        i = min(3, round(f * 4))
        if rank[mark] > rank.get(cells[b][i], 3):
            cells[b][i] = (marks or {}).get(p, mark)
    return " ".join("".join(c) for c in cells) if positions else REST


def band(bpm: float) -> str:
    """The tempo band a tempo is in (BANDS)."""
    return next(name for top, name in BANDS if bpm < top)


def pattern(positions) -> str:
    """A bar's onset positions as a table's outcome: fractions of a beat
    from the bar line, space-separated; a bar rested through is "-"."""
    return " ".join(str(p) for p in positions) or "-"


def onsets(notes, start: float, end: float) -> list:
    """The notes struck in [start, end), grouped by onset: [(beat, [notes])],
    notes within NEAR of each other one onset at the first's time."""
    out = []
    for n in sorted(n for n in notes if start - NEAR <= n[0] < end - NEAR):
        if out and n[0] - out[-1][0] < NEAR:
            out[-1][1].append(n)
        else:
            out.append((n[0], [n]))
    return out


def bars_of(song: Song, role: str):
    """Each bar of the song's meter with the part's onsets in it: (the bar's
    start, [(position, [notes])])."""
    for _, a, struck in numbered_bars_of(song, role):
        yield a, struck


def numbered_bars_of(song: Song, role: str, notes: list | None = None):
    """bars_of with each bar's number in the reading first: (number, start, [(position, [notes])]); `notes` in place of
    the part's (one voice's own)."""
    notes = song.notes.get(role, []) if notes is None else notes
    numbers = song.numbers or range(len(song.bars))
    for k, (a, b) in zip(numbers, song.bars):
        if round(b - a) != song.meter:
            continue
        seen = {}
        for t, ns in onsets(notes, a, b):
            p = position(t - a, song.division)
            if p < song.meter:
                seen.setdefault(p, []).extend(ns)
        yield k, a, sorted(seen.items())


def all_bars_of(song: Song, role: str):
    """Every bar of the song, whatever its length, with the part's onsets in
    it: (number, start, end, [(position, [notes])]); bars_of keeps the
    meter's bars only."""
    notes = song.notes.get(role, [])
    numbers = song.numbers or range(len(song.bars))
    for k, (a, b) in zip(numbers, song.bars):
        seen = {}
        for t, ns in onsets(notes, a, b):
            p = position(t - a, song.division)
            if p < b - a:
                seen.setdefault(p, []).extend(ns)
        yield k, a, b, sorted(seen.items())


def place_in_part(song: Song, number: int) -> str:
    """Where a bar sits in its part of the form: first, middle, last; none when no part holds it."""
    for bar, n, *_ in song.parts:
        if bar <= number < bar + n:
            return "first" if number == bar else "last" if number == bar + n - 1 else "middle"
    return "none"


def chord_change(song: Song, a: float, b: float) -> str:
    """Whether the chord changes in the bar [a, b): "on" its first beat only,
    "inside" it (on a later beat), or "same" (no change)."""
    out = "same"
    for i, c in enumerate(song.chords):
        if c.root is None or c.fit < FIT or not (a - NEAR <= c.start < b - NEAR):
            continue
        before = song.chords[i - 1] if i else None
        if before is not None and (before.root, before.shape) == (c.root, c.shape):
            continue
        out = "inside" if c.start >= a + NEAR else "on" if out == "same" else out
    return out


def cells(drawn: str, meter: int) -> list[str]:
    """A bar's pattern (pattern(), or a figure's "position:mark" tokens) as
    one cell a beat: the onset positions within the beat as fractions of
    it, their marks kept, space-separated; an empty beat "-"."""
    out = [[] for _ in range(meter)]
    for x in ([] if drawn == "-" else drawn.split()):
        at, _, mark = x.partition(":")
        p = Fraction(at)
        b = math.floor(p)
        if b < meter:
            out[b].append(f"{p - b}:{mark}" if mark else str(p - b))
    return [" ".join(c) or "-" for c in out]


def pattern_of_cells(cells_: list[str]) -> str:
    """The bar's pattern back from its cells."""
    tokens = []
    for b, c in enumerate(cells_):
        for x in ([] if c == "-" else c.split()):
            at, _, mark = x.partition(":")
            tokens.append(f"{b + Fraction(at)}:{mark}" if mark else str(b + Fraction(at)))
    return " ".join(tokens) or "-"


def figure(struck, start: float, song: Song) -> str:
    """A bass bar's figure as a table's outcome: each onset's position and
    the chord tone of its lowest note (TONE_MARKS, ? where no chord fits;
    r a root an octave or more over the bar's lowest note), as
    "position:mark" tokens; a bar rested through "-"."""
    low = [min(n[2] for n in ns) for _, ns in struck]
    lowest = min(low, default=0.0)
    tokens = []
    for (p, _), midi in zip(struck, low):
        c = arrangement_mod._chord_at(song.chords, start + p)
        mark = "?" if c is None or c.root is None or c.fit < FIT else TONE_MARKS[tone_of(round(midi) % 12, c.root, c.shape)]
        tokens.append(f"{p}:{'r' if mark == 'R' and midi >= lowest + 11.5 else mark}")
    return " ".join(tokens) or "-"


def bass_units(songs) -> list:
    """Every bar of the bass as a table's unit: its outcome the bar's
    figure (figure()); its values the part, the meter, the tempo band, the
    shape of the chord at the bar's start (harmony's names; ? none fits),
    whether the chord changes in this bar and in the next (chord_change),
    the figure before it (START where none), and the song's bass habit
    (_bass_habit: its density, its tones, its octaves)."""
    out = []
    for s in songs:
        if R.BASS not in s.notes:
            continue
        tempo, previous, last, mine = band(s.bpm), START, None, []
        weight = part_weights(s).get(R.BASS, "minor")
        for k, a, struck in numbered_bars_of(s, R.BASS, cells_mod.line_notes(s, R.BASS)):   # the line where the bass holds two voices
            if last is not None and k != last + 1:
                previous = START
            c = arrangement_mod._chord_at(s.chords, a)
            drawn = figure(struck, a, s)
            mine.append(tables.Unit(s.sid, s.game, drawn, {
                "part": R.BASS, "meter": s.meter, "tempo": tempo, "weight": weight, "feel": cells_mod.song_feel(s),
                "shape": "?" if c is None or c.root is None or c.fit < FIT else (c.shape or "major"),
                "chord": chord_change(s, a, a + s.meter), "next": chord_change(s, a + s.meter, a + 2 * s.meter),
                "previous": previous}))
            previous, last = drawn, k
        if mine:
            _give_habit(mine, _bass_habit(mine))
            out += mine
    return out


HABITS = ((1 / 3, "detached"), (2 / 3, "mixed"), (2, "held"))   # a song's share of held notes -> its habit
REPEATS = ((1 / 3, "varied"), (2 / 3, "mixed"), (2, "repeating"))   # its share of bars repeating the one before
DENSITIES = ((2, "sparse"), (6, "medium"), (1e9, "dense"))        # its onsets a bar
TONES = ((0.8, "roots", "Rr"), (0.8, "root-fifth", "Rr5"), (0, "walking", ""))   # the share of its bass notes on these marks
OCTAVES = 0.2                        # the share of a bass's notes an octave up (r) for it to play octaves


def habit_of(share: float, scale=HABITS) -> str:
    """A song's habit from one of its shares (HABITS, REPEATS) or its density a bar (DENSITIES)."""
    return next(name for top, name in scale if share < top)


def _tokens(drawn: str) -> list[str]:
    return [] if drawn == "-" else drawn.split()


def _give_habit(mine: list, habit: str) -> None:
    for u in mine:
        u.values["habit"] = habit


def _rhythm_habit(mine: list) -> str:
    """A song's habit for a part from its bars: how dense, and how much it repeats itself."""
    density = sum(len(_tokens(u.outcome)) for u in mine) / len(mine)
    repeats = sum(1 for u in mine if u.outcome == u.values["previous"]) / len(mine)
    return f"{habit_of(density, DENSITIES)} {habit_of(repeats, REPEATS)}"


def _bass_habit(mine: list) -> str:
    """A song's bass habit from its figures: how dense, which tones (TONES), whether it plays octaves."""
    marks = [t.partition(":")[2] for u in mine for t in _tokens(u.outcome)]
    density = len(marks) / len(mine)
    tones = "walking"
    for floor_, name, on in TONES:
        if marks and sum(1 for m in marks if m in on) / len(marks) >= floor_:
            tones = name
            break
    octaves = "octaves" if marks and sum(1 for m in marks if m == "r") / len(marks) >= OCTAVES else "no-octaves"
    return f"{habit_of(density, DENSITIES)} {tones} {octaves}"


WEIGHTS = ((0.2, "minor"), (0.5, "half"), (2, "main"))   # a pitched part's share of the band's pitched strikes


def part_weights(song: Song) -> dict:
    """Each pitched part's weight in the song (WEIGHTS): its share of the
    pitched parts' strikes. The density a part plays at follows it (an
    accompaniment that is the band's main part is dense in 76 % of songs,
    a minor one in 8 %), so a writer draws the habit given it."""
    counts = {role: len(ns) for role, ns in song.notes.items() if role != R.DRUMS}
    total = sum(counts.values()) or 1
    return {role: habit_of(n / total, WEIGHTS) for role, n in counts.items()}


def habits(units_) -> list:
    """The habits in units' values, one unit a song and part, with the tempo
    band and the part's weight beside where the units carry them: what a
    writer draws once a song, given those."""
    seen = {}
    for u in units_:
        values = {"part": u.values["part"]}
        for k in ("tempo", "weight"):
            if k in u.values:
                values[k] = u.values[k]
        seen.setdefault((u.song, u.values["part"]), tables.Unit(u.song, u.game, u.values["habit"], values))
    return list(seen.values())


def rhythm_habit_units(songs) -> list:
    return habits(units(songs))


GRAINS = ((0.25, "on-beat"), (0.5, "eighths"), (1.01, "fine"))   # a tune's grain: its share of onsets off the beat (tune_grain_units)
GRAIN_NOTES = 8                      # onsets a line needs to count a grain


def tune_grain_units(songs) -> list:
    """Each song's tune and counter-line as a unit: its outcome the line's
    grain (GRAINS: the share of its onsets off the beat, on-beat under
    0.25, eighths to 0.5, fine over), its values the part and its habit's
    density tier (the tier alone: under the whole habit the draw backed
    off to the part and gave a dense tune "on-beat", which no dense tune
    of FFVI is); drawn once a song and held by the melody writer from its
    first new rhythm on, as the density tier is after TIER_AFTER (round 66). FFVI's medium tunes sit at
    0.33-0.51 off the beat (quartiles; a median gap of half a beat) and
    4 of the 7 medium tunes of Song Check 52 at 0.15-0.21, where 5 of
    FFVI's 39 are: the bar chain, conditioned on the bar before, had
    locked a tune into the on-beat grain of its first draws."""
    out = []
    tiers = {(u.song, u.values["part"]): u.outcome for u in habits(units(songs))}
    for s in songs:
        for role in (R.MELODY, R.COUNTER):
            if (s.sid, role) not in tiers:
                continue
            on = [p for _, struck in bars_of(s, role) if struck for p, _ in struck]
            if len(on) < GRAIN_NOTES:
                continue
            share = sum(1 for p in on if Fraction(p).denominator != 1) / len(on)
            out.append(tables.Unit(s.sid, s.game, habit_of(share, GRAINS), {"part": role, "habit": tiers[(s.sid, role)].split()[0]}))
    return out


def drum_figure(struck, song: Song) -> str:
    """A drum bar's figure as a table's outcome: each hit's position and
    its piece's letter (LETTERS; a sample the reading named no drum, o),
    "position:letter" tokens, two pieces struck together two tokens; a
    bar rested through "-"."""
    tokens = set()
    for p, ns in struck:
        for n in ns:
            tokens.add((p, LETTERS.get(song.pieces.get(n[3]), "o")))
    return " ".join(f"{p}:{letter}" for p, letter in sorted(tokens)) or "-"


def _kit(mine: list) -> str:
    """The pieces a song's drums strike at all, as their letters in LETTERS' order."""
    letters = {t.partition(":")[2] for u in mine for t in _tokens(u.outcome)}
    return "".join(x for x in LETTERS.values() if x in letters) or "-"


def drum_units(songs) -> list:
    """Every bar of the drums as a table's unit: its outcome the bar's
    figure by piece (drum_figure()); its values the part, the meter, the
    tempo band, the bar's place in its part of the form (fills land on the
    last), the figure before it (START where none), the kit (which pieces
    the song strikes at all) and the song's habit (_rhythm_habit: density
    and repetition)."""
    out = []
    for s in songs:
        if R.DRUMS not in s.notes:
            continue
        tempo, previous, last, mine = band(s.bpm), START, None, []
        for k, a, struck in numbered_bars_of(s, R.DRUMS):
            if last is not None and k != last + 1:
                previous = START
            drawn = drum_figure(struck, s)
            mine.append(tables.Unit(s.sid, s.game, drawn, {
                "part": R.DRUMS, "meter": s.meter, "tempo": tempo, "place": place_in_part(s, k), "previous": previous, "feel": cells_mod.song_feel(s)}))
            previous, last = drawn, k
        if mine:
            kit = _kit(mine)
            _give_habit(mine, _rhythm_habit(mine))
            for u in mine:
                u.values["kit"] = kit
            out += mine
    return out


def drum_habit_units(songs) -> list:
    return habits(drum_units(songs))


DRUM_GROUPS = (("K", "S", "t"), ("h",), ("c",), ("o",))   # the kit's limbs: kick, snare and tom together; the hat; cymbals; the rest
UPPER = (R.HARMONY, R.ACCOMP, R.ARP)   # the parts whose tones voice a chord over the bass
WIDTHS = ((7, "close"), (14, "open"), (1e9, "wide"))   # semitones from the lowest upper note to the highest


def width_of(semitones: float) -> str:
    return next(name for top, name in WIDTHS if semitones <= top)


def voicing_units(songs) -> list:
    """Each chord span of each song, for each upper part sounding in it, as a
    table's unit: its outcome the chord tones the part holds in the span
    (vocab's marks, R 3 s 5 7 +, in order; a tone sounds when the part's
    notes on it cover SOUNDS of the span); its values the part, the chord's
    shape, the tone the bass holds under it (its lowest sounding tone, or
    none), the width of the whole upper voicing in the span (WIDTHS), the
    part's tones in the span before (START at its first), and the song's
    habit for the part (how many tones it holds a span, in thirds of the
    readings' range: thin, full, rich)."""
    out = []
    for s in songs:
        buckets = {role: _buckets([(a, b, m) for a, b, m, _ in ns]) for role, ns in s.notes.items()}
        if not any(role in buckets for role in UPPER):
            continue
        previous = {role: START for role in UPPER}
        mine = {role: [] for role in UPPER}
        for c in s.chords:
            if c.root is None or c.fit < FIT:
                continue
            shape = c.shape or "major"
            bass = "none"
            if R.BASS in buckets:
                low = [m for m, share in _sounding(buckets[R.BASS], c).items() if share >= SOUNDS - 1e-9]
                if low:
                    bass = MARKS[tone_of(min(low) % 12, c.root, c.shape)]
            upper = [m for role in UPPER if role in buckets for m, share in _sounding(buckets[role], c).items() if share >= SOUNDS - 1e-9]
            width = width_of(max(upper) - min(upper)) if upper else "none"
            for role in UPPER:
                if role not in buckets:
                    continue
                pitches = [m for m, share in _sounding(buckets[role], c).items() if share >= SOUNDS - 1e-9]
                if not pitches:
                    continue
                tones = {tone_of(m % 12, c.root, c.shape) for m in pitches}
                held = " ".join(MARKS[t] for t in CHORD_TONES if t in tones)
                mine[role].append(tables.Unit(s.sid, s.game, held, {
                    "part": role, "shape": shape, "bass": bass, "width": width, "previous": previous[role],
                    "count": min(4, len(tones))}))
                previous[role] = held
        for role, units_ in mine.items():
            if units_:
                _give_habit(units_, habit_of(statistics.mean(u.values["count"] for u in units_) / 4, RICHNESS))
                out += units_
    return out


RICHNESS = ((0.4, "thin"), (0.6, "full"), (2, "rich"))   # a part's mean tones a span, over four


def voicing_habit_units(songs) -> list:
    """The upper parts' richness habits, one unit a song and part (what a writer draws once a song)."""
    return habits(voicing_units(songs))


MOTIONS = ((1 / 3, "block"), (2 / 3, "mixed"), (2, "arpeggiated"))   # an upper part's share of strikes that change its pitches


def upper_motion(notes) -> float:
    """How an upper part moves through its tones: the share of its strike
    times (notes within NEAR of each other one strike) whose pitches differ
    from the strike before's. A chord restruck is 0, an arpeggio 1."""
    strikes, last = [], None
    for st, _, m, _ in sorted(n for n in notes if not math.isnan(n[2])):
        if last is not None and st - last < NEAR:
            strikes[-1].add(round(m))
        else:
            strikes.append({round(m)})
            last = st
    if len(strikes) < 2:
        return 0.0
    return sum(1 for a, b in zip(strikes, strikes[1:]) if a != b) / (len(strikes) - 1)


def upper_motion_units(songs) -> list:
    """Each upper part of each song as a unit: its outcome its motion
    (MOTIONS), its values the part and the tempo band; drawn once a song."""
    out = []
    for s in songs:
        for role in UPPER:
            if s.notes.get(role):
                out.append(tables.Unit(s.sid, s.game, habit_of(upper_motion(s.notes[role]), MOTIONS),
                                       {"part": role, "tempo": band(s.bpm)}))
    return out


def width_units(songs) -> list:
    """Each chord span as a unit: its outcome how the upper parts voice the
    chord as a whole, the number of distinct pitches sounding (to 6) and
    the width (WIDTHS); its values the shape, the parts present, the bass's
    tone, and the voicing before."""
    out = []
    for s in songs:
        buckets = {role: _buckets([(a, b, m) for a, b, m, _ in ns]) for role, ns in s.notes.items()}
        parts = "".join(role[0] for role in UPPER if role in buckets)
        if not parts:
            continue
        previous = START
        for c in s.chords:
            if c.root is None or c.fit < FIT:
                continue
            upper = sorted({m for role in UPPER if role in buckets for m, share in _sounding(buckets[role], c).items() if share >= SOUNDS - 1e-9})
            if not upper:
                continue
            bass = "none"
            if R.BASS in buckets:
                low = [m for m, share in _sounding(buckets[R.BASS], c).items() if share >= SOUNDS - 1e-9]
                if low:
                    bass = MARKS[tone_of(min(low) % 12, c.root, c.shape)]
            voicing = f"{min(6, len(upper))}:{width_of(upper[-1] - upper[0])}"
            out.append(tables.Unit(s.sid, s.game, voicing, {"part": "upper", "shape": c.shape or "major", "parts": parts,
                                                              "bass": bass, "previous": previous}))
            previous = voicing
    return out



def drum_group(figure: str, letters) -> str:
    """A drum figure's tokens on these pieces alone; "-" when none."""
    return " ".join(t for t in _tokens(figure) if t.partition(":")[2] in letters) or "-"


def drum_group_units(songs, letters) -> list:
    """drum_units for one group of pieces: each bar's figure on those pieces alone (its part "drums-" + the
    letters), with the group's own habit; a song without the group has no units."""
    name = "drums-" + "".join(letters)
    out = []
    by_song = {}
    for u in drum_units(songs):
        by_song.setdefault(u.song, []).append(u)
    for units_ in by_song.values():
        mine = []
        previous = START
        for u in units_:
            figure = drum_group(u.outcome, letters)
            values = dict(u.values)
            values["part"] = name
            values["previous"] = previous if u.values["previous"] != START else START
            mine.append(tables.Unit(u.song, u.game, figure, values))
            previous = figure
        if any(u.outcome != "-" for u in mine):
            _give_habit(mine, _rhythm_habit(mine))
            out += mine
    return out


def bass_habit_units(songs) -> list:
    return habits(bass_units(songs))


def kit_piece_units(songs) -> list:
    """Each song with drums as a unit: its outcome the kit pieces its drums strike, as letters in LETTERS' order ("KSh": kick,
    snare, hat), its values the part (drums) and the kit's habit tier. Round 58 (2026-10-29): FFVI plays a hat in 17 of its
    47 drum songs, cymbals in 23, toms in 7, where every written song had all seven pieces of the pack's kit; and a kit drawn
    as one figure (one song's bar, hat and all) had its hat, cymbals and other sounds capped by group habits drawn from
    other songs, which left a dense kit at 8 hits a bar against the game's 12.8."""
    tier = {u.song: u.outcome.split()[0] for u in drum_habit_units(songs)}
    order = "".join(LETTERS.values())
    out = []
    for s in songs:
        ns = s.notes.get(R.DRUMS)
        if not ns:
            continue
        letters = {LETTERS.get(s.pieces.get(n[3], n[3]), "o") for n in ns if isinstance(n[3], str)}
        outcome = "".join(x for x in order if x in letters)
        if outcome:
            out.append(tables.Unit(s.sid, s.game, outcome, {"part": R.DRUMS, "habit": tier.get(s.sid, "medium")}))
    return out


def drum_group_habit_units(songs) -> list:
    """Each drum group of each song as a unit: its outcome the group's own
    habit (the density and repetition of its bars, rests counted), its
    values the group (part) and the kit's habit. A kit written free draws
    each group's habit given the kit's: the cymbals and the other sounds
    are sparse under a dense kit (the readings, 2026-10-23), and a group's
    rest rate follows its own habit (sparse groups rest in six bars of ten)."""
    kit = {u.song: u.values["habit"] for u in drum_units(songs)}
    out = []
    for letters in DRUM_GROUPS:
        seen = set()
        for u in drum_group_units(songs, letters):
            if u.song in seen:
                continue
            seen.add(u.song)
            out.append(tables.Unit(u.song, u.game, u.values["habit"], {"part": u.values["part"], "habit": kit.get(u.song, "medium mixed")}))
    return out


def cell_units(units_) -> list:
    """Each beat of each bar unit as a unit of its own: the cell its outcome;
    its values the part, the meter, the beat (from 0) and the cell before
    it in the bar (START at the first beat)."""
    out = []
    for u in units_:
        previous = START
        for i, c in enumerate(cells(u.outcome, u.values["meter"])):
            out.append(tables.Unit(u.song, u.game, c, {"part": u.values["part"], "meter": u.values["meter"],
                                                         "beat": i, "previous": previous}))
            previous = c
    return out


class BarCells:
    """The floor under a bar-pattern table: the bar as a chain of beat
    cells, each cell's table conditioned on the part, the meter, the beat
    and the cell before it; so a bar never counted whole still has a
    likelihood (the product of its cells') and can be drawn (cell by cell)."""
    SHAPE = ("part", "meter", "beat", "previous")
    COVERS = ("part", "meter")           # what a bar table over this floor need not back off below

    def __init__(self, units_):
        self.table = tables.Table(self.SHAPE, "cells", votes=tables.SHARES).fit(cell_units(units_))

    def to_json(self) -> dict:
        return {"kind": "cells", "table": self.table.to_json()}

    @classmethod
    def from_json(cls, d: dict) -> "BarCells":
        floor = cls.__new__(cls)
        floor.table = tables.Table.from_json(d["table"], "cells")
        return floor

    def p(self, drawn: str, values: dict) -> float:
        prob, previous = 1.0, START
        for i, c in enumerate(cells(drawn, values["meter"])):
            prob *= self.table.p(c, (values["part"], values["meter"], i, previous))
            previous = c
        return prob

    def draw(self, values: dict, rng) -> str:
        out, previous = [], START
        for i in range(values["meter"]):
            previous = self.table.draw((values["part"], values["meter"], i, previous), rng)
            out.append(previous)
        return pattern_of_cells(out)


tables.FLOORS["cells"] = BarCells.from_json


def value_units(songs) -> list:
    """Every note of the melody's and the counter's line (of notes struck
    together, the highest) as a table's unit: its outcome whether the note
    is held (sounding SHORT of the way to the next note or more) or
    detached; its values the part, the value (beats to the next note on
    the song's grid, what a score would write), the meter, the tempo band,
    the note's place in its bar (PLACES), its beat in the bar (from 0), the
    articulation before it (START at the line's first note) and the song's
    habit for the part (HABITS: its share of held notes, which a writer
    would draw once a song). The values themselves follow from the bars'
    patterns (the onsets), so they condition this table rather than being
    drawn from one."""
    out = []
    for s in songs:
        tempo, starts = band(s.bpm), [a for a, _ in s.bars]
        for role in (R.MELODY, R.COUNTER):
            if role not in s.notes:
                continue
            line, previous, mine = arrangement_mod._line(s.notes[role]), START, []
            for n, after in zip(line, line[1:]):
                gap = after[0] - n[0]
                value = position(gap, s.division)
                i = bisect.bisect_right(starts, n[0] + NEAR) - 1
                if value == 0 or math.isnan(n[1]) or i < 0 or n[0] >= s.bars[i][1] - NEAR:
                    continue
                at = position(n[0] - s.bars[i][0], s.division)
                held = "held" if n[1] / gap >= SHORT else "detached"
                mine.append(tables.Unit(s.sid, s.game, held, {
                    "part": role, "value": str(value), "meter": s.meter, "tempo": tempo, "place": place(at),
                    "beat": math.floor(at), "previous": previous}))
                previous = held
            if mine:
                _give_habit(mine, habit_of(sum(1 for u in mine if u.outcome == "held") / len(mine)))
                out += mine
    return out


def habit_units(songs) -> list:
    """Each song's articulation habit for the melody and the counter (value_units'), one unit a song and part."""
    return habits(value_units(songs))


def units(songs) -> list:
    """Every bar of every part as a table's unit (tables.Unit): its outcome
    the bar's pattern, its values the part, the meter, the tempo band, the
    previous bar's pattern of the part (START where none), the bar's place
    in its part of the form, whether the chord changes in it, and the
    song's habit for the part (_rhythm_habit: its density and how much it
    repeats itself, which a writer would draw once a song)."""
    out = []
    for s in songs:
        tempo = band(s.bpm)
        weights = part_weights(s)
        for role in PARTS:
            if role not in s.notes:
                continue
            previous, last, mine = START, None, []
            for k, a, struck in numbered_bars_of(s, role, cells_mod.line_notes(s, role)):
                if last is not None and k != last + 1:
                    previous = START                      # a bar of another length between: the chain breaks
                drawn = pattern(p for p, _ in struck)
                mine.append(tables.Unit(s.sid, s.game, drawn, {
                    "part": role, "meter": s.meter, "tempo": tempo, "previous": previous, "weight": weights.get(role, "minor"), "feel": cells_mod.song_feel(s),
                    "place": place_in_part(s, k), "chord": chord_change(s, a, a + s.meter)}))
                previous, last = drawn, k
            if mine:
                _give_habit(mine, _rhythm_habit(mine))
                out += mine
    return out
