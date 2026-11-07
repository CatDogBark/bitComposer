"""The part each voice plays, from its notes: drums, bass, melody, a
counter-line, harmony (held chords), arp (fast repeated chord tones),
accompaniment (chords struck in rhythm), or a doubling of another voice.

Each guess keeps its evidence (the measures it was made from), and a
correction overrides it. Drums first: noise, samples with no pitch, or one
sample struck at one or two pitches (FFVI's percussion plays at G#3, the
driver's own pitch), or whose samples the drum namer calls drums (drums.py,
named as a reading names its samples: a tom played at several pitches is a
drum, a bass pumping one note on an instrument held is not, and nor is a
pitched pad held two beats or more on a sample the namer took for a kick,
round 89). Then the pitched voices by register and motion: the
bass the lowest line, held notes harmony, fast cycling ones an arp; a
voice playing another's notes (the same pitches and rhythm, a delay or an
octave apart) its doubling. The melody is the most varied line among the
voices that are heard: on the tune check (ten songs, docs/idiom/phase-1-
readers.md) the most varied line outright was a voice playing six notes in
a song or a quiet high line under a louder one in two songs of three, so a
candidate must sound on a quarter of the beats, at a quarter of the loudest
voice's level, with its median below C6 (Jungle's noises sit above), and
its variety is weighed by how much it is heard.

A channel is one voice, except where it plays two things: a tune on a drum
channel (split_melodic_pieces, round 83), and on a channel under the tune
a second instrument in a register of its own (split_second_instruments,
round 89), each get a voice of their own before the parts are read; a
tune's or counter's second instrument is the line changing colour and
stays on its voice."""
import bisect
import math
import statistics
from collections import Counter
from dataclasses import dataclass, field

DRUMS, BASS, MELODY, COUNTER, HARMONY, ARP, ACCOMP, DOUBLE = (
    "drums", "bass", "melody", "counter", "harmony", "arp", "accompaniment", "double")
DRUM_PIECES = {"kick", "snare", "hat", "tom", "cymbal"}   # the drum namer's pieces that make a voice a drum voice
BY_SOUND = 0.8                        # the share of a voice's notes on drum samples (or on instruments held) that decides
FEW_PITCHES = 4                       # pitches a sample a drum voice plays at most: a bass on a low sample plays many
                                      # (728 bass voices became drums without this, the namer calling their samples toms)
DRUM_HOLD = 2.0                       # beats: a voice on a tonal sample taken for a drum by how it plays (one or two pitches, eight
                                      # notes or more) holds its notes under this at the median. FFVI's 109 drum voices on percussion
                                      # samples hold a median 0.45 beats, three quarters under 0.95, only cymbal swells two or more;
                                      # of its 31 drum voices on tonal samples eight held two beats or more, pads and a lead
                                      # (Another World of Beasts' bowed strings for seven beats, The Phantom Forest's lead for twelve),
                                      # and a kit written from them struck a pad once a bar (round 77, from Song Check 63)
LOW_PIECES = {"kick", "tom"}          # the pieces a bass sample can pass for; a voice on them is a drum voice only
SPARSE = 0.5                          # where it sounds on under this share of the beats (fills), a bass playing on


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
    pieces = Counter(p.sample.piece for p in notes if p.sample is not None)   # the drum namer's name of each note's sample
    lengths = [p.length for p in notes if p.length]
    beat = grid.period_at(notes[0].start) if grid else 0.5
    seq = [round(m) for m in mids]
    moves = [abs(b - a) for a, b in zip(seq, seq[1:])]
    span = (notes[-1].start - notes[0].start) or 1.0
    if grid and grid.beat_times:
        presence = len({math.floor(grid.beats(p.start)) for p in notes}) / len(grid.beat_times)
    else:
        presence = min(1.0, len(notes) / max(1.0, span / beat))
    return {
        "notes": len(notes),
        "unpitched": sum(1 for p in notes if p.midi is None) / len(notes),
        "drum_sound": sum(c for k, c in pieces.items() if k in DRUM_PIECES) / len(notes),   # notes on a drum sample
        "low_sound": sum(c for k, c in pieces.items() if k in LOW_PIECES) / len(notes),     # on a kick or a tom
        "no_drum_sound": sum(c for k, c in pieces.items() if k == "none") / len(notes),    # notes on an instrument held
        "pitches_per_sample": max((len(v) for v in per_sample.values()), default=0),
        "distinct": len(set(seq)),
        "median": statistics.median(mids) if mids else None,
        "low": min(mids) if mids else None,
        "length_beats": statistics.median(lengths) / beat if lengths else 0.0,
        "per_beat": len(notes) / (span / beat) if beat else 0.0,
        "steps": sum(1 for m in moves if 0 < m <= 2) / len(moves) if moves else 0.0,
        "leaps": sum(1 for m in moves if m >= 5) / len(moves) if moves else 0.0,
        "repeats": sum(1 for m in moves if m == 0) / len(moves) if moves else 0.0,
        "presence": presence,            # the share of the song's beats the voice has a note on
        "entropy": _entropy(Counter(seq)) if seq else 0.0,
        "pc_entropy": _entropy(Counter(m % 12 for m in seq)) if seq else 0.0,   # of pitch classes: an arpeggio
                                                                                # over octaves is not a varied line
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


MELODY_PRESENT = 0.25                # the share of the song's beats a melody candidate has a note on
MELODY_HEARD = 0.25                  # and of the loudest pitched voice's level it has
MELODY_CEILING = 84                  # the highest median pitch a tune sits at (C6)
ECHO_DELAY = (0.025, 0.5)            # seconds an echo part may follow the part it copies
ECHO_HELD = 0.6                      # the share of its notes that must be copies, one delay apart
ECHO_SPREAD = 0.03                   # seconds the delay may wobble around its commonest value (Gang-Plank Galleon's
                                     # echo voice follows 150 to 200 ms behind, by the driver's timer)
ECHO_SHARP = 0.008                   # and within this of it, ECHO_FOCUS of the notes must still fall: a dense voice
ECHO_FOCUS = 0.3                     # repeating a few pitches matches any delay by chance, spread evenly
ECHO_SELF = 0.5                      # a voice repeating its own pitches at the delay (a pumping bass, every eighth)
                                     # is matched by any voice sharing them: no echo
ECHO_SURE = 0.004                    # seconds: the share within this of the delay is the echo's sureness (the
                                     # detector's old rule; the beat trusts an echo sure to ECHO_HELD)
MELODY_DENSE = 2.0                   # notes a beat beyond which a line is figuration more than tune
HELD_SPARSE = 0.25                   # held notes (HARMONY) on fewer of the beats than this are a pad; a line held
PAD_VARIETY = 2.3                    # on more and over this pitch-class entropy is a slow tune, not harmony


def echoes(song) -> dict:
    """Voices playing another's notes a fixed delay later, all song long:
    voice -> (the voice it copies, the delay, the share of its notes within
    ECHO_SURE of that delay). A driver's echo made of a
    spare voice (Star Fox's Corneria: one part copying another 1.4 steps of
    its grid later, 246 ms, every note off the grid). A copy is a note of
    the same pitch class; the delay is the one most of them share, within
    ECHO_SPREAD of its commonest value, ECHO_FOCUS of them within ECHO_SHARP
    (chance matches in a dense voice spread evenly over the window), and the
    copied voice not repeating itself at that delay (Gang-Plank Galleon's
    bass and its doubling pump the same note every eighth, 236 ms, and
    would each be the other's echo). Of two voices each the other's echo,
    the quieter is the echo. The beat trusts only an echo whose share within
    ECHO_SURE reaches ECHO_HELD (the detector's old rule); the looser ones
    serve the parts (see reading.beat_and_parts)."""
    by, levels = {}, {}
    for p in song.notes:
        if p.midi is not None and p.level > 0:
            by.setdefault(p.voice, []).append((p.start, round(p.midi) % 12))
            levels[p.voice] = levels.get(p.voice, 0.0) + p.level
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
            share = sum(1 for ds in delays if any(abs(d - mode) <= ECHO_SPREAD for d in ds)) / len(notes)
            focus = sum(1 for ds in delays if any(abs(d - mode) <= ECHO_SHARP for d in ds)) / len(notes)
            if share < ECHO_HELD or focus < ECHO_FOCUS or (best is not None and share <= best[0]):
                continue
            own = 0
            for t, pc in theirs:
                lo = bisect.bisect_left(starts, t - mode - ECHO_SHARP)
                hi = bisect.bisect_right(starts, t - mode + ECHO_SHARP)
                own += any(q == pc for _, q in theirs[lo:hi])
            if own / len(theirs) >= ECHO_SELF:
                continue
            sure = sum(1 for ds in delays if any(abs(d - mode) <= ECHO_SURE for d in ds)) / len(notes)
            best = (share, u, mode, sure)
        if best:
            out[v] = (best[1], best[2], best[3])
    for v in list(out):
        if v not in out:
            continue
        u = out[v][0]
        if u in out and out[u][0] == v:
            del out[v if levels.get(v, 0) / len(by[v]) >= levels.get(u, 0) / len(by[u]) else u]
    return out


SPLIT_BASE = 100                      # a melodic kit piece's own voice (split_melodic_pieces): SPLIT_BASE + its channel; a channel is 0 to 7
MELODIC_PITCHES = 3                   # pitches a tonal sample on a drum voice is struck on to be a tune there (Wild West's blip: 15)
MELODIC_SHARE = 0.5                   # and no one pitch holds this share of its notes (a bell on one note is a drum, however many its notes)
MELODIC_NOTES = 8                     # notes it needs
TUNE_FLOOR = 55                       # midi: a split voice at or over this is a counter-line, under it a bass (the register the bass rule reads)
SECOND_BASE = 200                     # a channel's second instrument's own voice (split_second_instruments, round 89): SECOND_BASE + its channel, + 10 for a
                                      # third (the channel stays readable in the id: (voice - SECOND_BASE) % 10)
UNDER_THE_TUNE = (BASS, HARMONY, ARP, ACCOMP)   # the parts whose channels are split so: a tune's or counter's second instrument is the line changing colour
SECOND_SHARE = 0.1                    # the share of a channel's pitched notes a second sample carries to be a part of its own,
SECOND_NOTES = 16                     # and the notes it needs (the echo reader's floor for a voice): an eight-note pedal or effect stays on its channel
SECOND_APART = 12                     # semitones between the two samples' median pitches that make the second's register its own where the
                                      # registers (each sample's 10th to 90th percentile pitches) overlap; disjoint registers are two at any distance


def drum_clause(f: dict) -> str | None:
    """Which of assign's two drum clauses a voice's features meet: "sound" (a drum voice by what its samples are: the namer
    called them drums, struck at few pitches, and not a kick or tom sample sounding on half the beats, a bass passing for one),
    "play" (by how it plays them: noise, or one sample at one or two pitches, eight notes or more, held under DRUM_HOLD), or
    None. A voice whose samples are instruments held (named "none") is no drum however it plays them (a bass pumping one
    note). A voice on drum-named samples whose notes are pitched and held DRUM_HOLD or more at the median is a pad the namer
    took for a kick (round 89: The Empire Gestahl's and Another World of Beasts' bowed strings, three and two pitches held
    eight and seven beats; FFVI's thirteen cymbal voices held two beats or more are unpitched and stay drums)."""
    if (f["drum_sound"] >= BY_SOUND and f["pitches_per_sample"] <= FEW_PITCHES and (f["low_sound"] < BY_SOUND or f["presence"] < SPARSE)
            and not (f["unpitched"] < 0.5 and f["length_beats"] >= DRUM_HOLD)):
        return "sound"
    if f["no_drum_sound"] < BY_SOUND and (f["unpitched"] >= 0.5 or (f["pitches_per_sample"] <= 2 and f["notes"] >= 8 and f["distinct"] <= 2
                                                                     and f["length_beats"] < DRUM_HOLD)):
        return "play"
    return None


def is_drum_voice(f: dict) -> bool:
    """assign's two drum clauses on a voice's features: a drum voice by what its samples are, or by how it plays them."""
    return drum_clause(f) is not None


def _register(mids) -> tuple:
    """A sample's register on a channel: its notes' 10th and 90th percentile pitches."""
    s = sorted(mids)
    return s[int(0.1 * (len(s) - 1))], s[int(0.9 * (len(s) - 1))]


def split_second_instruments(song, roles, grid=None) -> dict:
    """A second instrument in its own register on a channel under the tune is a part of its own (round 89): on each voice
    whose part (`roles`, assign's first reading of the whole channels) is a bass or a chord part (UNDER_THE_TUNE), the notes
    on a sample other than the one most of its pitched notes are on, carrying SECOND_SHARE of them and SECOND_NOTES or more,
    whose register is its own (median pitches SECOND_APART apart, or registers that do not overlap), move to a voice of
    their own (SECOND_BASE + the channel, + 10 for a third), their chip notes with them (so the echo and vibrato readers see
    the voice); the channel keeps its main instrument, and assign reads the parts again, the second never setting the song's
    floor nor taking the lead. The readings keep the second's voice beside the counts (readings.Song.second_voices), not in
    them: the band a token describes is the channels' main instruments, and the second instrument's stretches await a word
    of their own (a voice's instrument by stretch), since a voice of its own would ask the writer for a ninth chip voice in
    the eight-channel songs that time-share one. FFVI changes instrument on 108 of
    its 381 pitched channels and in 61 of them the second plays in a register of its own; on a bass or chord channel that
    is a second function (Wild West's bass 28 to 80: a bass, then chords two octaves up), and the register word had spanned
    both. A tune's or counter's second instrument is the line changing colour (47 of 56 take the line over for stretches,
    a third of the notes, 19 an octave apart) and stays on its voice. Returns {new voice: (channel, sample key, part)}."""
    parts = {r.voice: r.role for r in roles}
    by_voice = {}
    for p in song.notes:
        by_voice.setdefault(p.voice, []).append(p)
    out = {}
    for v, ns in sorted(by_voice.items()):
        if v >= SPLIT_BASE or parts.get(v) not in UNDER_THE_TUNE:
            continue
        by_sample = {}
        for p in ns:
            if p.sample is not None and p.midi is not None:
                by_sample.setdefault(p.sample.key, []).append(p)
        if len(by_sample) < 2:
            continue
        total = sum(len(mine) for mine in by_sample.values())
        main = max(sorted(by_sample), key=lambda key: len(by_sample[key]))
        main_mids = [p.midi for p in by_sample[main]]
        main_low, main_high = _register(main_mids)
        k = 0
        for key, mine in sorted(by_sample.items()):
            if key == main or len(mine) < max(SECOND_NOTES, SECOND_SHARE * total):
                continue
            mids = [p.midi for p in mine]
            low, high = _register(mids)
            if abs(statistics.median(mids) - statistics.median(main_mids)) < SECOND_APART and min(high, main_high) - max(low, main_low) > 0:
                continue                                    # the same register: one line on two instruments
            new = SECOND_BASE + v + 10 * k
            k += 1
            for p in ns:
                if p.sample is not None and p.sample.key == key:
                    p.voice = new
                    if p.note is not None:
                        p.note.voice = new
            out[new] = (v, key, parts[v])
    return out


def split_melodic_pieces(song, grid=None) -> dict:
    """A tune on the drum channel is a part (round 83): on each voice that would be a drum voice, the notes on a sample the
    namer called "other" (a tonal sample, no drum) struck on MELODIC_PITCHES pitches or more with no pitch holding
    MELODIC_SHARE of them, MELODIC_NOTES notes or more, move to a voice of their own (SPLIT_BASE + the channel, + 1 for a
    second such sample), their chip notes with them (so the echo and vibrato readers see the voice); the drum voice keeps
    its drums. FFVI: Wild West's blip on fifteen pitches beside its hat, Dancing Mad (part 5)'s rim on sixteen, Kefka's on
    eight, The Decisive Battle's on nine; the written kit had struck each on one note (round 75's most struck, round 79's
    degree). Returns {new voice: (channel, sample key, pitches)}."""
    by_voice = {}
    for p in song.notes:
        by_voice.setdefault(p.voice, []).append(p)
    out = {}
    for v, ns in sorted(by_voice.items()):
        if v >= SPLIT_BASE or not ns or not is_drum_voice(_features(ns, grid)):
            continue
        by_sample = {}
        for p in ns:
            if p.sample is not None and p.sample.piece == "other" and p.midi is not None:
                by_sample.setdefault(p.sample.key, []).append(p)
        k = 0
        for key, mine in sorted(by_sample.items()):
            pitches = Counter(round(p.midi) for p in mine)
            if len(mine) >= MELODIC_NOTES and len(pitches) >= MELODIC_PITCHES and pitches.most_common(1)[0][1] < MELODIC_SHARE * len(mine):
                new = SPLIT_BASE + v + k
                k += 1
                for p in mine:
                    p.voice = new
                    if p.note is not None:
                        p.note.voice = new
                out[new] = (v, key, len(pitches))
    return out


def assign(song, grid, echoed: dict | None = None) -> list[Role]:
    """Each voice's part over the song (echoed: voices found to be another's
    echo, by echoes(), each that voice's double). A voice split from a drum
    channel (split_melodic_pieces, round 83) is a counter-line, or a bass
    where it sits low: a tune on the drum channel, never the song's lead."""
    by_voice = {}
    for p in song.notes:
        by_voice.setdefault(p.voice, []).append(p)
    feats = {v: _features(ns, grid) for v, ns in by_voice.items() if ns}
    roles = {}
    for v, f in feats.items():
        if v >= SECOND_BASE:                                # a second instrument split from a channel under the tune (round 89): a pitched part
            continue
        if v >= SPLIT_BASE:                                 # a melodic kit piece, split from its channel (round 83)
            roles[v] = Role(v, BASS if f["median"] is not None and f["median"] < TUNE_FLOOR else COUNTER,
                            evidence={"melodic_piece": v - SPLIT_BASE, "distinct": f["distinct"], "median": round(f["median"], 1) if f["median"] is not None else None})
            continue
        # a voice is a drum voice by what its samples are (the namer: a tom at several pitches is a drum), and
        # only otherwise by how it plays them (noise, or one sample at one or two pitches); a voice whose samples
        # are instruments held (named "none") is no drum however it plays them (a bass pumping one note), and a
        # pitched pad held like a pad on a sample the namer took for a kick is none either (drum_clause, round 89)
        clause = drum_clause(f)
        if clause == "sound":
            roles[v] = Role(v, DRUMS, evidence={"by_sound": round(f["drum_sound"], 2), "distinct": f["distinct"], "presence": round(f["presence"], 2)})
        elif clause == "play":                              # held like a drum, not a pad (round 77)
            roles[v] = Role(v, DRUMS, evidence={k: f[k] for k in ("unpitched", "distinct")} | {"length_beats": round(f["length_beats"], 2)})
    for v, (u, delay, *_) in (echoed or {}).items():
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
    loudest = max(feats[v]["level"] for v in tonal)
    floor = [v for v in tonal if v < SECOND_BASE] or tonal     # a second instrument never sets the song's floor (round 89: an eight-note
    lowest = min(floor, key=lambda v: feats[v]["median"])      # pedal split from a chord channel had taken the bass from a 137-note line)
    for v in tonal:
        f = feats[v]
        if f["median"] <= feats[lowest]["median"] + 3 and f["median"] < 55:
            roles[v] = Role(v, BASS, evidence={"median": round(f["median"], 1)})
    rest = [v for v in tonal if v not in roles]
    # held chords: notes of two beats and more, unless the line is present and varied (a slow tune: on the
    # generator's own songs a melody of half notes read as harmony and its arpeggio as the melody)
    for v in rest:
        f = feats[v]
        if f["length_beats"] >= 2.0 and (f["presence"] < HELD_SPARSE or f["pc_entropy"] < PAD_VARIETY):
            roles[v] = Role(v, HARMONY, evidence={"length_beats": round(f["length_beats"], 2)})
    rest = [v for v in rest if v not in roles]
    # the melody: of the lines heard (present, loud enough, below the ceiling), the most varied, weighed by how
    # much it is heard and held back where it runs over MELODY_DENSE notes a beat (figuration: Super Mario World's
    # Overworld had a louder, busier accompaniment outscore its tune); none heard, no melody (a song of drums
    # and bass, or noises where a tune would be)
    def melodic(v):
        f = feats[v]
        return (f["pc_entropy"] * (1 + f["steps"]) * (1 - f["leaps"]) * math.sqrt(f["presence"] * f["level"])
                * min(1.0, MELODY_DENSE / max(f["per_beat"], 1e-9)))
    heard = [v for v in rest if feats[v]["presence"] >= MELODY_PRESENT and feats[v]["level"] >= MELODY_HEARD * loudest
             and feats[v]["median"] <= MELODY_CEILING and v < SECOND_BASE]   # a second instrument split from a channel under the tune is never the lead
    if heard:
        top = max(heard, key=melodic)
        roles[top] = Role(top, MELODY, evidence={k: round(feats[top][k], 2) for k in ("pc_entropy", "steps", "leaps", "presence", "level", "median")})
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
