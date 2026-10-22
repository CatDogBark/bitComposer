"""The substitution harness: a part written from the tables into a real
song in place of the song's own, the rest as decoded, rendered through
the same back end (phase 3's acceptance by ear, docs/idiom/phase-3-tables.md).

The song is one of the readings; the table is fitted on every other song
in the database. The writer (writer.py) gives the part's figures and
notes in beats; this module chooses the song's voices for them and sets
each note in the voice's own sample, settings and register.

The bass: of the voices the readers call bass, the one with the longest
notes is the line, and its notes alone are the song's bass for the
writer. A second bass voice is one of three things beside it (measured
over the readings): DOUBLING it (sounding at the same events: it then
plays what the written line plays, at its own pitch offset, on its own
sample), ALTERNATING with it (the voices take turns so a note can ring
past the next strike: the pair is one part, the written line is read
from both and its notes ring as the pair's do, each going to the voice
that is free), or APART (a second part in the bass register with a
rhythm of its own: left as it is, the arrangement table's question and
the known limitation here). A written note takes the volume of the
song's own nearest bass note (a fade-in stays a fade-in) and the voice's
usual sample, envelope and echo (its most common, not its first note's).

The drums: every voice the readers call drums is the kit, one part; each
piece the song strikes (kick, snare, hat, tom, cymbal, other, the namer's
names on the samples) maps to the voice and samples the song strikes it
with, a hit taking the sample the song uses most at that position in the
bar (Searching for Friends' hat is an open sample on the beats and a
closed one between them, both named hat), with that sample's usual
settings and pitch register; a hit takes the volume of the song's
nearest hit of the same piece (Terra's
snare fades in with its bass and plays at four levels through the song)
and lasts its gap to the next hit on its voice times the piece's own
sounded share (a Terra snare hit sounds nearly to the next, its roll's
pickups do not); a written hit of a piece the song's kit lacks is
dropped, and two pieces on one voice at the same instant keep the one
the song strikes more.

The readings count a song once through to its loop, and the writers write
those bars; where the render runs past the first pass, the written notes
repeat as the song does, shifted by the loop's length from the bar it
loops back to (The Decisive Battle's first pass ends at 54.6 s of a
one-minute render, and both written parts fell silent there together).

The song's moments (bars where every part but the one written drops to
under MOMENT of the song's median energy, for at most MOMENT_BARS bars
in a row) keep the song's own figure, and so does a bar holding a stop
(a beat no other voice sounds in) that the song's own part plays
through: the band leaves a hole and the part answers it, Johnny C. Bad's
drummer with a roll of triplet sixteenths where the written drums kept
time. Its locking to the band (the shared hits its part strikes, the
stops it rests in) binds the written part. All of it read from the song
itself: the arrangement is the song's.
"""
import bisect
import math
import os
import random
import statistics
from array import array
from collections import Counter
from dataclasses import dataclass, field

from ..spc import convert
from . import harmony, reading, rhythm, store, writer
from . import roles as R
from . import roles as roles_mod

NEAR = 0.06                           # beats: onsets this close are one event
DOUBLING = 0.6                        # the share of the pair's events both voices sound at, for the second to double the first
ALTERNATING = 0.6                     # the share of single-voice events that change voice, for the pair to alternate
NOT_BOTH = 0.3                        # an alternating pair sounds together in under this share of its events
MOMENT = 0.65                         # a bar where the other parts' energy is under this share of the song's median is a moment
MOMENT_BARS = 2                       # for at most this many bars in a row: a longer drop is a section, written like any other
TOGETHER = 0.67                       # the share of the other playing parts striking a position together for it to be a shared hit
LETTERS = {v: k for k, v in rhythm.LETTERS.items()}   # a figure's letter -> the piece's name


@dataclass
class Context:
    """A song loaded for the harness: its reading, its score as decoded, and what the writers need of it."""
    db: object
    sid: str
    game: str
    title: str
    key: tuple | None
    song: rhythm.Song
    songs: list
    original: convert.Score
    events: dict                      # (voice, start rounded) -> the reading's note event, with its midi and sample key
    beats: array
    keys: dict                        # sample index -> key
    pieces: dict                      # sample key -> the piece the reading named it
    loop: tuple | None = None         # (the second the song loops back to, the loop's length in seconds), when heard
    by_voice: dict = field(default_factory=dict)   # voice -> (role, its notes as the store packs them)
    models: dict | None = None        # the tables to write from (a pack's, packtables.read), else fitted on `songs`
    generated: bool = False           # a song the generator composed: its old parts are no manner to keep (free writing)


@dataclass
class Written:
    """A part written into the song."""
    part: str
    notes: list                       # convert notes on the song's voices
    replaced: set                     # the voices they stand in for
    figures: list
    own: list
    log: list = field(default_factory=list)


def load(db, spc_path: str, seconds: float = 60.0) -> Context | None:
    """The song by its file name in the readings, decoded to `seconds`; None when it is not read."""
    from .. import spc
    row = db.execute("SELECT id, game, title, key_tonic, key_mode FROM songs WHERE file = ?", (os.path.basename(spc_path),)).fetchone()
    if not row:
        return None
    sid, game, title, tonic, mode = row
    songs, _ = rhythm.load(db)
    song = next((s for s in songs if s.sid == sid), None)
    if song is None:
        return None
    snap = spc.read(spc_path)
    original = convert.score_of(snap, seconds, fade=0.0)
    r = reading.of_score(original)
    events = {(p.voice, round(p.start, 4)): p for p in r.song.notes}
    beats = array("d")
    beats.frombytes(db.execute("SELECT beats FROM beats WHERE song = ?", (sid,)).fetchone()[0])
    keys, pieces = {}, {}
    for idx, key, piece in db.execute("SELECT idx, key, piece FROM samples WHERE song = ?", (sid,)):
        keys[idx] = key
        pieces[key] = piece
    ctx = Context(db, sid, game, title, (tonic, mode) if tonic is not None else None, song, songs, original, events, beats, keys, pieces)
    loop_bar, loop_seconds = db.execute("SELECT loop_bar, loop_seconds FROM songs WHERE id = ?", (sid,)).fetchone()
    bars = array("d")
    bars.frombytes(db.execute("SELECT beats, bars FROM beats WHERE song = ?", (sid,)).fetchone()[1])
    if loop_bar is not None and loop_seconds and loop_bar < len(bars):
        ctx.loop = (bars[loop_bar], loop_seconds)
    for voice, role, blob in db.execute("SELECT voice, role, notes FROM voices WHERE song = ?", (sid,)):
        ctx.by_voice[voice] = (role, [n for n in store.unpack(blob) if n[3] > 0])
    return ctx


def load_generated(song: dict, title: str, game: str, models: dict | None = None, seconds: float | None = None) -> Context | None:
    """A song the generator composed (compose_song's dict), read as a game's
    would be: its score (score.of_song), the readers over it, the reading kept
    in a database of its own, and the harness's view of it; None when the
    readers find no beat or no bass and no drums. `models`: the pack's tables
    (packtables.read) the writers draw from."""
    from .. import score as score_mod
    original = score_mod.of_song(song)
    if seconds is not None and seconds < original.seconds:
        original.notes = [n for n in original.notes if n.start < seconds]
        original.seconds = seconds
    return context_of(original, song, title, game, models)


def context_of(original: convert.Score, song: dict, title: str, game: str, models: dict | None = None) -> Context | None:
    """The harness's view of a score that stands on a generated song's grid
    (the song it was composed as, or that song with parts rewritten): read
    on the generator's own beat, the roles from its channels."""
    r = reading.of_score(original, game=game, title=title, grid=_generated_grid(song, original.seconds))
    if r.grid is None:
        return None
    r.file, r.folder = f"{title}.generated", game
    _pin_roles(r)
    db = store.connect(":memory:")
    store.keep(db, r)
    songs, _ = rhythm.load(db)
    if not songs:
        return None
    s = songs[0]
    events = {(p.voice, round(p.start, 4)): p for p in r.song.notes}
    beats = array("d")
    beats.frombytes(db.execute("SELECT beats FROM beats WHERE song = ?", (s.sid,)).fetchone()[0])
    keys, pieces = {}, {}
    for idx, key, piece in db.execute("SELECT idx, key, piece FROM samples WHERE song = ?", (s.sid,)):
        keys[idx] = key
        pieces[key] = piece
    key = (r.key[0], r.key[1]) if r.key else None
    ctx = Context(db, s.sid, game, title, key, s, songs, original, events, beats, keys, pieces, models=models, generated=True)
    if r.form and r.form.loop_bar is not None and r.form.loop_seconds and r.form.loop_bar < len(r.grid.bar_times):
        ctx.loop = (r.grid.bar_times[r.form.loop_bar], r.form.loop_seconds)
    for voice, role, blob in db.execute("SELECT voice, role, notes FROM voices WHERE song = ?", (s.sid,)):
        ctx.by_voice[voice] = (role, [n for n in store.unpack(blob) if n[3] > 0])
    return ctx


def _generated_grid(song: dict, seconds: float):
    """The generator's own beat as the readers' grid: its tempo, four beats a
    bar from the first row, sixteenths."""
    from ..it_format import it_tempo_to_bpm
    from ..pattern import ROWS_PER_BEAT
    from . import beat
    bpm = it_tempo_to_bpm(song["tempo"], song["speed"], ROWS_PER_BEAT)
    period = 60.0 / bpm
    n = max(2, int(math.ceil(seconds / period)) + 1)
    beats = [k * period for k in range(n)]
    section = beat.Section(0.0, beats[-1], period / 4, 0.0, first=0.0, meter=4, downbeat=0, division=4)
    return beat.Grid(period / 4, 4, [section], beats, beats[::4], 1.0, 0.5)


GENERATED_DRUMS = {"kick": "kick", "snare": "snare", "hihat": "hat", "openhat": "hat", "tom": "tom", "crash": "cymbal"}
PITCHED = {"melody": R.MELODY, "bass": R.BASS, "arp": R.ARP}   # the generator's channels whose part is fixed
HARMONY_READS = {R.HARMONY, R.ACCOMP, R.COUNTER}               # what a generator harmony channel may read as


def _pin_roles(r) -> None:
    """A generated song's roles from its channels (pattern.CHANNEL_ROLES), not
    the role reader: the generator knows its parts; a harmony channel keeps
    the reader's call among harmony, accompaniment and counter-line; the
    drum channels' samples are named by their channel, the pitched ones
    unnamed, so a pitched sample is never a drum by sound."""
    from ..pattern import CHANNEL_ROLES
    read = {x.voice: x.role for x in r.roles}
    voices = sorted({p.voice for p in r.song.notes})
    roles = []
    for v in voices:
        name = CHANNEL_ROLES[v] if v < len(CHANNEL_ROLES) else "other"
        if name in PITCHED:
            role = PITCHED[name]
        elif name in GENERATED_DRUMS:
            role = R.DRUMS
        elif name == "harmony":
            role = read.get(v) if read.get(v) in HARMONY_READS else R.ACCOMP
        else:
            role = read.get(v, R.ACCOMP)
        roles.append(roles_mod.Role(v, role))
        piece = GENERATED_DRUMS.get(name, "none")
        for p in r.song.notes:
            if p.voice == v and p.sample is not None:
                p.sample.piece = piece
    r.roles = roles


def looped(ctx: Context, notes: list) -> list:
    """The written notes, repeated as the song loops until the render's end (the module)."""
    if not ctx.loop:
        return notes
    start, length = ctx.loop
    end = start + length
    out = list(notes)
    k = 1
    while start + k * length < ctx.original.seconds:
        for n in notes:
            if start - 1e-6 <= n.start < end - 1e-6 and n.start + k * length < ctx.original.seconds:
                m = convert.notes_mod.Note(n.voice, n.start + k * length, n.sample, n.pitch, n.volume, n.adsr, n.gain, n.echo,
                                           n.noise, brr=n.brr, echo_delay=n.echo_delay, echo_volume=n.echo_volume,
                                           echo_feedback=n.echo_feedback, echo_filter=n.echo_filter, echo_writes=n.echo_writes,
                                           end=None if n.end is None else min(n.end + k * length, ctx.original.seconds))
                out.append(m)
        k += 1
    return out


def seconds_at(beats: array, b: float) -> float:
    """A time in beats back to seconds on the beat times."""
    if len(beats) < 2:
        return b
    i = min(max(int(math.floor(b)), 0), len(beats) - 2)
    return beats[i] + (b - i) * (beats[i + 1] - beats[i])


def settings_of(mine, events, sample_key=None):
    """A voice's usual settings (sample, brr, volume, envelope, echo: its most
    common) and a reference note on that sample: (usual, like, pitch_ref,
    midi_ref); with `sample_key`, among its notes on that sample of the
    reading's; None when there is no such note. midi_ref is None for an
    unpitched sample."""
    if sample_key is not None:
        mine = [n for n in mine if (p := events.get((n.voice, round(n.start, 4)))) is not None
                and p.sample is not None and p.sample.key == sample_key]
    usual = Counter((n.sample, n.brr, n.volume, n.adsr, n.gain, n.echo, n.echo_delay, n.echo_volume, n.echo_feedback,
                     n.echo_filter, n.echo_writes) for n in mine).most_common(1)
    for n in mine:
        p = events.get((n.voice, round(n.start, 4)))
        if p is not None and usual and (n.sample, n.brr) == usual[0][0][:2]:
            return usual[0][0], n, n.pitch, p.midi
    return None


def note_like(voice, start, end, usual, like, pitch, volume=None):
    """A note on the voice in its usual settings at this pitch register (volume: the usual's unless given)."""
    _, _, usual_volume, adsr, gain, echo, e_delay, e_volume, e_feedback, e_filter, e_writes = usual
    return convert.notes_mod.Note(voice, start, like.sample, max(1, min(0x3FFF, round(pitch))), volume or usual_volume, adsr,
                                  gain, echo, False, brr=like.brr, echo_delay=e_delay, echo_volume=e_volume,
                                  echo_feedback=e_feedback, echo_filter=e_filter, echo_writes=e_writes, end=end)


def pitch_for(midi: float, pitch_ref: int, midi_ref: float) -> float:
    """The SNES pitch register for a midi note, from a reference note on the same sample."""
    return pitch_ref * 2 ** ((midi - midi_ref) / 12)


def relation(line, other) -> tuple:
    """What a second bass voice does beside the line (the module): ("doubling", semitones above the line),
    ("alternating",) or ("apart",)."""
    onsets = sorted([(n[0], 0, n) for n in line] + [(n[0], 1, n) for n in other])
    events = []
    for t, who, n in onsets:
        if events and t - events[-1][0] < NEAR:
            events[-1][1][who] = n
        else:
            events.append((t, {who: n}))
    both = sum(1 for _, d in events if len(d) == 2) / max(1, len(events))
    singles = [next(iter(d)) for _, d in events if len(d) == 1]
    alternation = sum(1 for a, b in zip(singles, singles[1:]) if a != b) / max(1, len(singles) - 1)
    if both >= DOUBLING:
        return ("doubling", round(statistics.median([d[1][2] - d[0][2] for _, d in events if len(d) == 2])))
    if alternation >= ALTERNATING and both < NOT_BOTH:
        return ("alternating",)
    return ("apart",)


def moments(ctx: Context, part_voices: set) -> set:
    """The song's moments: bars (indices among the song's bars, every length) where every voice but the part's drops
    to under MOMENT of the song's median energy (level x sounded length), for a run of at most MOMENT_BARS bars."""
    others = [n for voice, (_, ns) in ctx.by_voice.items() if voice not in part_voices for n in ns]
    energy = []
    for a, b in ctx.song.bars:
        e = 0.0
        for n in others:
            length = n[1] if not math.isnan(n[1]) else 0.25
            lo, hi = max(a, n[0]), min(b, n[0] + length)
            if hi > lo:
                e += n[3] * (hi - lo)
        energy.append(e)
    if not energy:
        return set()
    median = statistics.median(energy)
    low = [e < MOMENT * median for e in energy]
    out, k = set(), 0
    while k < len(low):
        if low[k]:
            j = k
            while j < len(low) and low[j]:
                j += 1
            if j - k <= MOMENT_BARS:
                out.update(range(k, j))
            k = j
        else:
            k += 1
    return out


def stops(ctx: Context, part_voices: set, part_notes) -> set:
    """The bars (indices among the song's bars) holding a beat no voice but the part's sounds in, that the part plays
    through: the band's holes the part answers."""
    parts = {voice: ns for voice, (_, ns) in ctx.by_voice.items() if voice not in part_voices}
    out = set()
    for k, (a, b) in enumerate(ctx.song.bars):
        for beat in range(int(round(b - a))):
            t0, t1 = a + beat, a + beat + 1
            if not any(n[0] < t1 - NEAR and n[0] + (n[1] if not math.isnan(n[1]) else 0.25) > t0 + NEAR for ns in parts.values() for n in ns):
                if any(n[0] < t1 - NEAR and n[0] + (n[1] if not math.isnan(n[1]) else 0.25) > t0 + NEAR for n in part_notes):
                    out.add(k)
                    break
    return out


def locks(ctx: Context, part_voices: set, part_notes) -> dict:
    """The song's own locking to the band, a bar at a time: the shared hits (positions where TOGETHER of the other
    voices playing in the bar strike within NEAR) the part strikes too, and the stops (beats no other voice sounds
    in) the part rests in; {bar index: (positions to strike, beats to leave)}."""
    parts = {voice: ns for voice, (_, ns) in ctx.by_voice.items() if voice not in part_voices}
    starts = sorted(n[0] for n in part_notes)
    out = {}
    for k, (a, b) in enumerate(ctx.song.bars):
        playing = [ns for ns in parts.values() if any(a - NEAR <= n[0] < b - NEAR for n in ns)]
        must, rests = set(), set()
        if len(playing) >= 2:
            for step in range(int(round(b - a)) * 4):
                t = a + step / 4
                if sum(1 for ns in playing if any(abs(n[0] - t) < NEAR for n in ns)) >= TOGETHER * len(playing):
                    i = bisect.bisect_left(starts, t - NEAR)
                    if i < len(starts) and starts[i] <= t + NEAR:
                        must.add(rhythm.position(t - a, ctx.song.division))
        for beat in range(int(round(b - a))):
            t0, t1 = a + beat, a + beat + 1
            if not any(n[0] < t1 - NEAR and n[0] + (n[1] if not math.isnan(n[1]) else 0.25) > t0 + NEAR for ns in parts.values() for n in ns):
                if not any(n[0] < t1 - NEAR and n[0] + (n[1] if not math.isnan(n[1]) else 0.25) > t0 + NEAR for n in part_notes):
                    rests.add(beat)
        if must or rests:
            out[k] = (must, rests)
    return out


def write_bass(ctx: Context, seed: int = 1) -> Written | None:
    """The bass written into the song (the module)."""
    song, original, events, beats = ctx.song, ctx.original, ctx.events, ctx.beats
    by_voice = {v: [n for n in ns if not math.isnan(n[2])] for v, (role, ns) in ctx.by_voice.items() if role == R.BASS}
    by_voice = {v: ns for v, ns in by_voice.items() if ns}
    if not by_voice:
        return None
    log = []
    length_of = {v: statistics.median([n[1] for n in ns if not math.isnan(n[1])] or [0.0]) for v, ns in by_voice.items()}
    v = max(by_voice, key=lambda voice: (length_of[voice], len(by_voice[voice])))
    end = song.bars[-1][1] if song.bars else math.inf
    kinds = {t: relation(by_voice[v], by_voice[t]) for t in by_voice if t != v}
    partners = [t for t, k in kinds.items() if k[0] == "alternating"]
    doublings = [t for t, k in kinds.items() if k[0] == "doubling"]
    part = sorted(n for t in [v] + partners for n in by_voice[t])          # the line: one part across an alternating pair
    song.notes[R.BASS] = [(n[0], n[1], n[2], ctx.keys.get(int(n[5]), "noise")) for n in part if n[0] < end]
    log.append(f"bass voices {sorted(by_voice)}; the line on {v} (notes {length_of[v]:.2f} beats)"
               + "".join(f"; voice {t} {k[0]}" + (f" {k[1]:+d} semitones" if k[0] == "doubling" else "") for t, k in kinds.items()))
    habit, free = None, False
    if ctx.models and "bass" in ctx.models:
        model = ctx.models["bass"]                                  # the pack's table
        if ctx.generated and "bass_habits" in ctx.models:           # and its habit, drawn once a song: the old part is no manner
            habit = ctx.models["bass_habits"].draw((R.BASS,), random.Random(seed * 7 + 1))
            free = True
            log.append(f"free writing: the habit drawn from the pack, {habit}")
    else:
        units = rhythm.bass_units(ctx.songs)
        model = writer.fit([u for u in units if u.song != ctx.sid])
    own = [rhythm.figure(struck, a, song) if struck else "-" for _, a, _, struck in rhythm.all_bars_of(song, R.BASS)]
    held = moments(ctx, set(by_voice))
    answered = stops(ctx, set(by_voice), part)
    lock = locks(ctx, set(by_voice), part)
    notes, figures = writer.bass(song, model, random.Random(seed), habit=habit, key=ctx.key, hold=held | answered, lock=lock, free=free)
    mine_units = rhythm.bass_units([song])
    log.append(f"habit {mine_units[0].values['habit'] if mine_units else '-'}, {len(figures)} bars written, {len(notes)} notes"
               + (f"; moments kept as the song's own: bars {sorted(held)}" if held else "")
               + (f"; the band's stops answered with the song's own: bars {sorted(answered)}" if answered else "")
               + f"; locked to the band in {len(lock)} bars ({sum(len(m) for m, _ in lock.values())} shared hits, "
                 f"{sum(len(r) for _, r in lock.values())} stop beats)")
    # the written line onto the song's voices: the line voice, an alternating partner when the line is still ringing,
    # a doubling voice at every note; an apart voice is left as it is
    pair = [v] + partners
    settings = {t: settings_of([n for n in original.notes if n.voice == t], events) for t in pair + doublings}
    pair = [t for t in pair if settings[t] is not None]
    doublings = [t for t in doublings if settings[t] is not None]
    if not pair:
        log.append("no reference note on the bass voice")
        return None
    mine = [n for n in original.notes if n.voice == v]
    starts = [n.start for n in mine]
    ring = statistics.median([n[1] for n in part if not math.isnan(n[1])]) if partners else None   # beats a note of the pair rings
    free = {t: -1.0 for t in pair}
    new = []
    for start_b, end_b, midi in notes:
        start = seconds_at(beats, start_b)
        if start >= original.seconds:
            continue
        stop = min(seconds_at(beats, max(end_b, start_b + ring) if ring else end_b), original.seconds)
        idle = [t for t in pair if free[t] <= start + 0.001]
        voice = v if v in idle else (idle[0] if idle else min(pair, key=lambda t: free[t]))
        i = bisect.bisect_left(starts, start)
        near = min((mine[j] for j in (i - 1, i) if 0 <= j < len(mine)), key=lambda n: abs(n.start - start), default=None)
        at = near.volume if near is not None and abs(near.start - start) < 4.0 else None
        usual, like, pitch_ref, midi_ref = settings[voice]
        new.append(note_like(voice, start, stop, usual, like, pitch_for(midi, pitch_ref, midi_ref), at if voice == v else None))
        free[voice] = stop
        for t in doublings:
            usual, like, pitch_ref, midi_ref = settings[t]
            new.append(note_like(t, start, stop, usual, like, pitch_for(midi + kinds[t][1], pitch_ref, midi_ref)))
    replaced = set(pair) | set(doublings)
    if partners or doublings:
        log.append(f"written onto voices {sorted(replaced)}: {len(new)} notes" + (f", ringing {ring:.2f} beats" if ring else ""))
    new = looped(ctx, new)
    return Written(R.BASS, new, replaced, figures, own, log)


def write_drums(ctx: Context, seed: int = 1) -> Written | None:
    """The drums written into the song (the module)."""
    song, original, events, beats = ctx.song, ctx.original, ctx.events, ctx.beats
    kit_voices = {v for v, (role, ns) in ctx.by_voice.items() if role == R.DRUMS and ns}
    if not kit_voices or R.DRUMS not in song.notes:
        return None
    log = []
    # each piece's voices and samples: every one the song strikes it with, by how often, and at which positions in
    # the bar; each sample's sounded share: of the gap to the next hit on its voice, how much the song's hits sound
    strikes, at, shares = Counter(), {}, {}
    bar_starts = [a for a, _ in song.bars]
    for v in kit_voices:
        notes_v = sorted(ctx.by_voice[v][1])
        for i, n in enumerate(notes_v):
            key = ctx.keys.get(int(n[5]))
            letter = rhythm.LETTERS.get(ctx.pieces.get(key), "o")
            strikes[(letter, v, key)] += 1
            k = bisect.bisect_right(bar_starts, n[0] + NEAR) - 1
            if k >= 0:
                at.setdefault(letter, {}).setdefault(rhythm.position(n[0] - bar_starts[k], song.division), Counter())[(v, key)] += 1
            if i + 1 < len(notes_v) and notes_v[i + 1][0] - n[0] > NEAR and not math.isnan(n[1]):
                shares.setdefault((letter, v, key), []).append(min(1.0, n[1] / (notes_v[i + 1][0] - n[0])))
    options = {}                                            # (letter, voice, key) -> (settings, share, mine)
    for (letter, v, key), c in strikes.most_common():
        found = settings_of([n for n in original.notes if n.voice == v], events, key)
        if found is None:
            continue
        mine = sorted((n for n in original.notes if n.voice == v
                       and (p := events.get((n.voice, round(n.start, 4)))) is not None
                       and p.sample is not None and p.sample.key == key), key=lambda n: n.start)
        options[(letter, v, key)] = (found, statistics.median(shares[(letter, v, key)]) if shares.get((letter, v, key)) else 0.8, mine)
    where = {}                                              # letter -> (voice, settings, share, weight, mine): the piece's usual
    for (letter, v, key), c in strikes.most_common():
        if letter not in where and (letter, v, key) in options:
            found, share, mine = options[(letter, v, key)]
            where[letter] = (v, found, share, c, mine)

    def choice(letter, position):
        """The piece's voice and settings for a hit at this position: the sample the song uses most there, else its usual."""
        for (v, key), _ in (at.get(letter, {}).get(position, Counter())).most_common():
            if (letter, v, key) in options:
                found, share, mine = options[(letter, v, key)]
                return v, found, share, strikes[(letter, v, key)], mine
        return where[letter]
    several = {LETTERS.get(k, k): len({(v, key) for (l, v, key) in options if l == k}) for k in where}
    several = {k: n for k, n in several.items() if n > 1}
    log.append(f"kit on voices {sorted(kit_voices)}: " + ", ".join(f"{LETTERS.get(k, k)} on {v}" for k, (v, *_) in sorted(where.items())))
    own = [rhythm.drum_figure(struck, song) if struck else "-" for _, _, _, struck in rhythm.all_bars_of(song, R.DRUMS)]
    held = moments(ctx, kit_voices)
    answered = stops(ctx, kit_voices, song.notes[R.DRUMS])
    models, group_locks = {}, {}
    for letters in rhythm.DRUM_GROUPS:
        if all(rhythm.drum_group(f, letters) == "-" for f in own):
            continue
        name = "drums-" + "".join(letters)
        if ctx.models and name in ctx.models:
            models[letters] = ctx.models[name]                      # the pack's table
        else:
            units = rhythm.drum_group_units(ctx.songs, letters)
            models[letters] = writer.fit([u for u in units if u.song != ctx.sid], name=name)
        notes_g = [n for n in song.notes[R.DRUMS] if rhythm.LETTERS.get(song.pieces.get(n[3]), "o") in letters]
        group_locks[letters] = locks(ctx, kit_voices, notes_g)
    habit, free = None, False
    if ctx.models and ctx.generated and "drum_habits" in ctx.models:
        habit = ctx.models["drum_habits"].draw((R.DRUMS,), random.Random(seed * 7 + 2))
        free = True
        log.append(f"free writing: the habit drawn from the pack, {habit}")
    hits, figures = writer.drums(song, models, random.Random(seed), hold=held | answered, locks=group_locks, habit=habit, free=free)
    mine_units = rhythm.drum_units([song])
    log.append(f"habit {mine_units[0].values['habit'] if mine_units else '-'}, kit {mine_units[0].values['kit'] if mine_units else '-'}, "
               f"groups {['+'.join(g) for g in models]}, {len(figures)} bars written, {len(hits)} hits"
               + (f"; moments kept as the song's own: bars {sorted(held)}" if held else "")
               + (f"; the band's stops answered with the song's own: bars {sorted(answered)}" if answered else ""))
    placed, taken, dropped = {}, {}, Counter()        # (voice, start rounded) -> (letter, start, the sample's choice)
    for start_b, letter in hits:
        if letter not in where:
            dropped[letter] += 1
            continue
        k = bisect.bisect_right(bar_starts, start_b + NEAR) - 1
        position = rhythm.position(start_b - bar_starts[k], song.division) if k >= 0 else None
        v, found, share, weight, mine = choice(letter, position)
        start = seconds_at(beats, start_b)
        if start >= original.seconds:
            continue
        slot = (v, round(start, 3))
        if slot in taken and taken[slot] >= weight:         # two pieces on one voice at once: the one the song strikes more
            dropped[letter] += 1
            continue
        taken[slot] = weight
        placed[slot] = (letter, start, (found, share, mine))
    new = []
    by_voice_starts = {}
    for (v, _), (letter, start, _) in placed.items():
        by_voice_starts.setdefault(v, []).append(start)
    gaps = {v: sorted(starts) for v, starts in by_voice_starts.items()}
    for (v, _), (letter, start, (found, share, mine)) in sorted(placed.items(), key=lambda kv: kv[1][1]):
        usual, like, pitch_ref, _ = found
        starts = gaps[v]
        i = bisect.bisect_right(starts, start + 1e-6)
        typical = statistics.median([b - a for a, b in zip(starts, starts[1:])]) if len(starts) > 1 else 0.5
        gap = starts[i] - start if i < len(starts) else typical
        j = bisect.bisect_left([n.start for n in mine], start)
        near = min((mine[k] for k in (j - 1, j) if 0 <= k < len(mine)), key=lambda n: abs(n.start - start), default=None)
        volume = near.volume if near is not None and abs(near.start - start) < 4.0 else None
        new.append(note_like(v, start, min(start + share * gap, original.seconds), usual, like, pitch_ref, volume))
    if dropped:
        log.append("dropped hits: " + ", ".join(f"{LETTERS.get(k, k)} {c}" for k, c in dropped.most_common()))
    log.append("hits sound " + ", ".join(f"{LETTERS.get(k, k)} {w[2]:.2f}" for k, w in sorted(where.items())) + " of their gaps, at the song's own volumes"
               + ("; samples chosen by position for " + ", ".join(f"{k} ({n})" for k, n in several.items()) if several else ""))
    new = looped(ctx, new)
    return Written(R.DRUMS, new, set(kit_voices), figures, own, log)


def score_with(ctx: Context, parts: list, title: str, message: list) -> convert.Score:
    """The song as decoded, the written parts in place of the voices they stand in for."""
    replaced = set().union(*(w.replaced for w in parts)) if parts else set()
    kept = [n for n in ctx.original.notes if n.voice not in replaced]
    new = [n for w in parts for n in w.notes]
    o = ctx.original
    return convert.Score(kept + new, o.seconds, o.voices, o.master, o.fade, title[:25], o.game, o.artist, o.row_hz, o.tempo,
                         o.tick_hz, o.aligned, o.on_ticks, o.snap, dict(o.pcm_of), dict(o.key_of), message=message)


def stems(ctx: Context, parts: list, out_dir: str) -> list[str]:
    """Modules for a page that switches each part while the song plays: the rest (no written part's voices), and
    each part as the song plays it and as written. Returns the paths."""
    os.makedirs(out_dir, exist_ok=True)
    replaced = set().union(*(w.replaced for w in parts)) if parts else set()
    o = ctx.original
    sets = [("rest", [n for n in o.notes if n.voice not in replaced])]
    for w in parts:
        sets.append((f"{w.part} original", [n for n in o.notes if n.voice in w.replaced]))
        sets.append((f"{w.part} written", w.notes))
    paths = []
    for label, notes in sets:
        sc = convert.Score(notes, o.seconds, o.voices, o.master, o.fade, f"{ctx.title} {label}"[:25], o.game, o.artist, o.row_hz,
                           o.tempo, o.tick_hz, o.aligned, o.on_ticks, o.snap, dict(o.pcm_of), dict(o.key_of),
                           message=[f"{ctx.title}: {label} (a stem for the Substitution Check)"])
        path = os.path.join(out_dir, f"{ctx.title} {label}.it")
        convert.render(sc, path)
        paths.append(path)
    return paths


def readings_of(ctx: Context, score: convert.Score, voices: set) -> str:
    """What the readers make of a score: the roles of these voices, the key, the tempo, the chords."""
    rr = reading.of_score(score)
    roles = {x.voice: x.role for x in rr.roles}
    key = f"{harmony.NAMES[rr.key[0]]} {rr.key[1]}" if rr.key else "-"
    return (" ".join(f"voice {v} {roles.get(v, '-')}" for v in sorted(voices)) +
            f"; key {key}; tempo {rr.grid.bpm if rr.grid else 0:.1f}; chords {len(rr.chords)}")
