"""A part written from the tables into a real song, in place of the song's
own (phase 3's acceptance by ear, docs/idiom/phase-3-tables.md): the bass,
and the drums the same way (DrumManner, drums()): the drums' figures are
each hit's position and piece, written a limb at a time (rhythm.DRUM_GROUPS:
kick, snare and tom as one line, the hat as another, cymbals and the rest
each their own, since a whole kit's bar is too particular a figure for
any inventory to hold many of, and a kit is what its limbs do together),
each group from its own inventory over the readings, in the song's own
manner for that group (the positions it strikes, the pieces it has), the
envelope each bar's own piece by piece (a bar's strikes of each piece
stay within TIGHT of the song's own bar's, so a snare roll never stands
in for the hat), the spans and moments and locking as the bass's; a hit's voice, sample and
length are the harness's, from the song's own kit.

The song is one of the readings (rhythm.load's Song: its bars and chords
in beats, its parts' notes); the table is fitted on every other song in
the database, so the song never votes for its own bars; the habit is the
song's own, read from its bass (the generator's writer draws one from the
habits table); then bar by bar a figure is drawn as the song's own
mixture over the table (tables.Cache: the figure before again, one the
song played earlier, or a new one under the part, the meter, the habit
and the figure before, in that order, so a figure never seen after this
one backs off to the habit's own inventory, not the pooled one). A new
figure must be a bar some song played (the floor serves the likelihood,
not the writer: its invented bars were the runs the listener heard in
Terra) and must be in the song's own manner, read from its bass (Manner),
and within the song's own bar (envelope): striking between TIGHT times
as often as the song's bass does in that bar, and the downbeat where
that bar does (a song-wide window let Locke's one-note intro bars
license a one-note bar where its line starts walking, and its busiest
bar license sixteenths everywhere; density is the arrangement's, bar by
bar, like the rests and the volume); placed only on positions in the bar
the song's bass strikes in RARE of its strikes or more (its feel: Terra
strikes quarters and triplets, so a sixteenth pickup was the listener's
"burst"; The Decisive Battle's riff strikes the and-a before beats one
and three and never the and of two, so straight eighths were his "free
spirited"); and in the song's tones as much as its rhythm: no
octave-up roots where the song plays none, as many different tones in a
bar as the song's own bars have (Terra's one, Locke's one to four), the
roots' share of a bar and the roots and fifths' share each within the
song's own bars' range (by MARGIN; Terra's third span came back as a
pedal on the fifth under a bass that plays nothing but roots), and a bar
on one tone struck PEDAL times or more only where PEDAL_SHARE of the
song's own such bars are (Locke's walking bass came back as sixteen
fifths in a row). Where the song's own bass changes its rhythm bar to
bar (a bar in no span), the written bar changes its rhythm from the one
before too, since the song's mixture would otherwise bring one figure
back again and again.

A bass holds its figures over spans and changes with the music, which a
bar drawn at a time cannot do (the listener: "no section awareness, no
throughline"). Over the readings' 1,324 basses, 63 % of the bars sit in a
span repeating a rhythm with a period of one, two or four bars (spans of
6.6 bars on average), and a new span's rhythm is one an earlier span had
in 35 % of cases (EARLIER). So the writer reads the song's own spans from
its bass (by rhythm, marks dropped: a walking bass keeps its rhythm and
moves its tones) and writes a pattern a span: one of an earlier span's
patterns with EARLIER's chance (never the one just before), else as
many new figures as the span's period, their rhythms differing from one
another and from the pattern before (a span's figures alternate, and a
new span is a change, by construction), held through the span; where
the song's own span repeats its
figures exactly, the pattern repeats exactly, and where only the rhythm
repeats, each bar is drawn anew with the pattern's rhythm, so the tones
move, except that a bar on a chord an earlier bar of the span had takes
that bar's figure again with REUSE's chance (the readings' basses repeat
their figure on a repeated chord inside a span 53 % of the time walking,
59 % root-fifth, 73 % roots). A bar in no span is drawn on its own. A
new figure uses only the marks the song's own bass uses in RARE of its
notes or more (The Decisive Battle came back with sus tones it plays
once). The bars the song's own bass
rests through are left silent and never drawn for (the arrangement stays
the song's: which bars the bass plays is the arrangement table's, not
this one's), and a playing bar never draws a rest; so are the song's
moments: a bar the caller names in `hold` (the harness: a bar where the
other parts' energy drops under MOMENT of the song's median, The
Decisive Battle's regear at 18 s, which the written bass "blasted
through") keeps the song's own figure, since what a bass does in a break
is the song's choice (over the readings' breaks it keeps its figure in
35 %, rests in 32 %, thins in 27 %); and so is its locking to the band: at
a shared hit (a position where most of the other playing parts strike
together) the readings' basses strike too two times in three, and on a
stop (a beat no other part sounds in) they rest two times in three, so
where the song's own bass does either, the written one must (`lock`: a
bar's positions it must strike and beats it must leave). Each token
becomes a note:
its pitch the chord tone its mark names in the chord sounding at its
onset (R the root, r the root an octave up, 3 5 7 the chord's own, s the
sus tone, ? the root; no chord fitting, the last root, or the tonic),
in the octave nearest the note before it; a passing tone (+) passes: a
scale step from the note before toward the next note of the bar, or on
in the line's direction (over the readings' basses a passing tone is a
step from its neighbour far more often than the second over the root,
which is where the first writer put every one), the key's step above the
root with no note before;
within the song's own bass register (from the lowest tenth of its bass
notes up to REACH above it, the first note lowest), so a walking line
walks (placed in a fixed octave, Locke's leapt by thirds and fifths
where its own moves by step); its length to the next onset in
the bar or the bar's end, sounding the share of that the song's bass
sounds of its own gaps (the median, between SOUNDS). A bar of another
length than the meter's is written too, with the table's figures for
that many beats (the readings hold 3/4 and 2/4 songs) or, where nothing
fits, the song's own bar: the first writer left such bars silent, and
Johnny C. Bad's bass vanished for four bars the beat reader had put in
3/4 and came back in at the song's stop-time.
"""
from __future__ import annotations
import math
import random
from types import SimpleNamespace
import statistics
from collections import Counter
from fractions import Fraction

from .. import harmony, phrases, rhythm, roles as R, tables
from ..vocab import FIT

from . import figures as figures_mod, tune as tune_mod, parts as parts_mod   # noqa: E402  the package's other sections


# --- the upper parts: harmony, accompaniment and arp under the song's own chords (phase 4) ---

UPPER_LOW = 0.1                       # a voice's register: from this quantile of its own notes
UPPER_HIGH = 0.9                      # to this one; a written note is moved by octaves to sit inside it
TONE_MARKS = {"sus": "s"}             # the voicing table's marks as tone() reads them


def stack(marks: list, root: int, shape: str, scale: set, low: int, previous: float | None) -> list[int]:
    """A voicing's tones as midi notes, lowest first: the first mark placed in
    the register nearest the note before, each next the nearest above (a
    close stack; the spread between parts is their voices' own registers)."""
    if not marks:
        return []
    pcs = [parts_mod.tone(root, shape, TONE_MARKS.get(m, m), scale) for m in marks]
    out = [parts_mod.place(pcs[0], low, previous)]
    for pc in pcs[1:]:
        out.append(out[-1] + ((pc - out[-1]) % 12 or 12))
    return out


def in_register(midi: int, register: tuple) -> int:
    """The note moved by octaves into the voice's register (low, high); where the register is under an
    octave and no octave fits, the one just under its ceiling."""
    low, high = register
    while midi > high:
        midi -= 12
    while midi < low:
        midi += 12
    while midi > high:
        midi -= 12
    return midi


UPPER_LOCK = {R.HARMONY: 0.0, R.ACCOMP: 2 / 3, R.ARP: 2 / 3}   # the share of the band's shared hits an upper part strikes (a pad holds through)


MOTION_STEP = {"block": 0, "mixed": 0.5, "arpeggiated": 1}   # how far along the stack a voice moves a strike
CHORD_MARKS = {"R", "3", "5", "7", "sus"}   # a written voicing holds one of these at least, and only these are realized: the
                                      # table's "+" is mostly the chord reader's noise (Terra's own accompaniment plays 4 % other)
CLASH = (1, 11)                       # semitones (mod 12) a written tone may not sit from a note the tune sounds at the same time


RICH_TONES = {"thin": 1, "full": 2, "rich": 3}   # chord tones a written voicing holds at least, by the richness habit
PEDAL_VOICE = 2                       # semitones: a voice whose own register is this narrow or narrower is a pedal and keeps its note


def voiced(outcome: str, tones: int = 1) -> bool:
    """Whether a voicing from the table may be written: it holds `tones` chord
    tones at least (the table's "+" counts for nothing: it is mostly the chord
    reader's noise, and realized it was a ninth in every strum)."""
    return len(set(outcome.split()) & CHORD_MARKS) >= tones


def sounding_pcs(line: list, at: float) -> set:
    """The pitch classes a line (start, length, midi, ...) sounds at a time."""
    out = set()
    for n in line:
        length = n[1] if not math.isnan(n[1]) else 0.25
        if n[0] - rhythm.NEAR <= at < n[0] + length - rhythm.NEAR and not math.isnan(n[2]):
            out.add(round(n[2]) % 12)
    return out


def unclashed(midi: int, options: list, tune: set) -> int:
    """The note, or where it sits a semitone from the tune, the nearest of the voicing's other tones that does not."""
    if not tune or not any((midi - pc) % 12 in CLASH for pc in tune):
        return midi
    clear = [m for m in options if not any((m - pc) % 12 in CLASH for pc in tune)]
    return min(clear, key=lambda m: (abs(m - midi), m)) if clear else midi


def upper(song: rhythm.Song, role: str, voices: list, registers: dict, models: dict, rng: random.Random,
          habit: str, richness: str, sounds: float, key: tuple | None = None, hold=(), lock=None,
          motion: str = "block", energy: list | None = None, pedals: dict | None = None,
          plays: list | None = None, figures: list | None = None, shared: dict | None = None,
          tone_index: int = 0, kind: str | None = None) -> tuple[list, list, list]:
    """An upper part written for the song under its own chords (the module):
    the rhythm from the part's bar table (free of the song's own part), the
    chord tones a span from the voicings mixture, the spread from the widths
    mixture, laid onto the part's voices (lowest first; a lone arp voice
    cycles the tones). `voices`: the part's voices low to high; `registers`:
    voice -> its register (low, high); `pedals`: voice -> the note a pedal
    voice (a register PEDAL_VOICE semitones or narrower) holds; `models`:
    rhythm and voicings (Caches); `figures`: the bars given (a second line's,
    drawn under the line's own bars from the second_figures table) instead
    of drawn here; `shared`: the part's voicing at each (bar, position),
    filled by the line's call (tone_index 0) and read by a voice beside it
    (tone_index 1, 2...); `kind`: that voice's relation to the line (apart,
    alternating): with the voice_intervals and voice_moves tables it takes
    its interval to the line's note where they strike together and its own
    move where it strikes alone, drawn (the line's notes are in `shared`
    under ("line", (bar, position))); without them, the tone that many
    steps up the line's voicing.
    Returns the notes [(start, end in beats, midi, voice)], the figures and
    the voicings drawn a bar."""
    lock = lock or {}
    bars = [(a, b, struck) for _, a, b, struck in rhythm.all_bars_of(song, role)]
    own = parts_mod.plays_as_own(plays, bars) if plays is not None else [rhythm.pattern(p for p, _ in struck) if struck else figures_mod.REST for _, _, struck in bars]
    if figures is None:
        figures = parts_mod._free_figures(song, role, models["rhythm"], figures_mod.FreeManner(models["rhythm"].table.vocabulary, division=song.division), own, bars,
                                habit, rng, hold, lock, envelope_of=figures_mod.free_envelope(habit), lock_share=UPPER_LOCK.get(role, 1.0), energy=energy)
    else:
        figures = [f if o != figures_mod.REST else figures_mod.REST for f, o in zip(figures, own)]
    step = MOTION_STEP.get(motion, 0)
    pedals = pedals or {}
    walked = 0.0                                            # how far along the stack the voices have moved (motion)
    tune_line = sorted(song.notes.get(R.MELODY, []) + song.notes.get(R.COUNTER, []))   # what the written part must not clash with
    tonic, mode = key if key else (0, "major")
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]}
    notes, voicings = [], []
    played_v, prev_v = Counter(), None
    last_chord, marks, previous_low = None, ["R", "3", "5"], None
    periods = getattr(song, "periods", {}).get(role, {})   # a held bar of the part's period takes its source bar's voicing too, on the same chord
    by_bar = {}
    own_tone = max(1, tone_index)                           # the tone a voice beside the line takes of the line's voicing (a span at a time with ANY_TONE)
    beside = bool(tone_index) and kind in figures_mod.VOICE_KINDS and "voice_intervals" in models and "voice_moves" in models and shared is not None
    prev_steps, prev_midi = rhythm.START, None              # a voice beside the line: its last interval with the line, its last note

    def line_before(k, p, strict=False):
        """The line's note last struck at or before (bar k, position p); `strict`: before it."""
        best = None
        for key_, m in shared.items():
            if isinstance(key_[0], str) and key_[0] == "line" and (key_[1] < (k, p) if strict else key_[1] <= (k, p)) and (best is None or key_[1] > best[0]):
                best = (key_[1], m)
        return best[1] if best else None

    def weighted(weights: dict):
        """One key drawn by its weight; None where nothing weighs."""
        total = sum(weights.values())
        if total <= 0:
            return None
        x, acc = rng.random() * total, 0.0
        for key_, w in weights.items():
            acc += w
            if x < acc:
                return key_
        return next(reversed(weights))
    in_bar = {}                                             # bar -> positions the line's voicing is known at (shared), for a voice beside it
    for k, ((a, b, _), figure) in enumerate(zip(bars, figures)):
        if figure == figures_mod.REST:
            voicings.append(figures_mod.REST)
            continue
        positions = [Fraction(t.partition(":")[0]) for t in rhythm._tokens(figure)]
        bar_voicing = []
        runs_to = tune_mod.first_onset(figures, bars, k + 1)        # the bar's last note runs to the next bar's first, as the share was counted
        for i, p in enumerate(positions):
            start = a + float(p)
            until = a + float(positions[i + 1]) if i + 1 < len(positions) else (runs_to if runs_to is not None and runs_to > b - rhythm.NEAR else b)
            c = rhythm._chord_at(song.chords, start)
            chord = (c.root, c.shape) if c is not None and c.root is not None and c.fit >= FIT else last_chord
            if chord is None:
                continue
            src = by_bar.get(k - periods[k], {}).get(i) if k in periods else None
            known = None
            if shared is not None and tone_index:           # a voice beside the line: the line's voicing at this onset, or the last before it
                at = shared.get((k, p))
                if at is None:
                    before = [q for (kk, q) in shared if kk == k and q <= p]
                    at = shared.get((k, max(before))) if before else None
                known = at if at is not None and at[0] == chord else None
            if known is not None:
                prev_v, marks = known[1], list(known[2])
                if chord != last_chord or not bar_voicing:      # a new span: the tone this voice takes of the line's voicing (ANY_TONE: drawn)
                    own_tone = rng.randrange(1, max(2, len(marks))) if tone_index == figures_mod.ANY_TONE else tone_index
                last_chord = chord
                if not bar_voicing or bar_voicing[-1] != prev_v:
                    bar_voicing.append(prev_v)
            elif src is not None and src[0] == chord and src[1] is not None and (chord != last_chord or not bar_voicing):
                prev_v, marks = src[1], src[2]                  # the period's bar again: its voicing with it
                last_chord = chord
                bar_voicing.append(prev_v)
            elif chord != last_chord or not bar_voicing:
                shape = chord[1] or "major"
                v_unit = tables.Unit(song.sid, song.game, "", {"part": role, "shape": shape, "habit": richness, "previous": prev_v or rhythm.START})
                need = min(RICH_TONES.get(richness, 2), max(1, len(voices)))   # a lone voice needs one tone, a trio up to three
                full = lambda o, _n=need: voiced(o, _n)   # noqa: E731
                drawn = models["voicings"].draw(v_unit, prev_v, played_v, rng, keep=full)
                for _ in range(figures_mod.TRIES):
                    if full(drawn):
                        break
                    drawn = models["voicings"].table.draw(models["voicings"].table.context(v_unit), rng, v_unit.values, floored=False, floor_k=models["voicings"].table.chain_floor)
                marks = [m for m in drawn.split() if m in CHORD_MARKS] if full(drawn) else (["R", "5"] if need > 1 else ["R"])
                played_v[drawn] += 1
                prev_v = drawn
                last_chord = chord
                bar_voicing.append(drawn)
            by_bar.setdefault(k, {})[i] = (chord, prev_v, list(marks))
            if shared is not None and not tone_index:
                shared[(k, p)] = (chord, prev_v, list(marks))
            pitches = stack(marks, chord[0], chord[1], scale, registers[voices[0]][0], previous_low)
            previous_low = float(pitches[0]) if pitches else previous_low
            tune = sounding_pcs(tune_line, start)
            if role == R.ARP and len(voices) == 1:
                midi = in_register(pitches[i % len(pitches)], registers[voices[0]])
                midi = unclashed(midi, [in_register(m, registers[voices[0]]) for m in pitches], tune)
                notes.append((start, start + (until - start) * tune_mod.share_at(sounds, until - start), float(midi), voices[0]))
                continue
            # the tones onto the voices, lowest first; spare voices double the stack an octave up; spare tones are dropped
            # from the middle; with motion, each voice walks along the stack a step a strike (the voices interlocking)
            stacked = list(pitches)
            while len(stacked) < len(voices):
                stacked.append(stacked[len(stacked) - len(pitches)] + 12)
            if len(stacked) > len(voices):
                stacked = [stacked[0]] + stacked[-(len(voices) - 1):] if len(voices) > 1 else [stacked[0]]
            offset = int(walked) if len(pitches) > 1 else 0
            for j, v in enumerate(voices):
                low_v, high_v = registers[v]
                if high_v - low_v <= PEDAL_VOICE:           # a pedal voice: the song's drone, struck on the figure
                    notes.append((start, start + (until - start) * tune_mod.share_at(sounds, until - start), float(pedals.get(v, low_v)), v))
                    if shared is not None and not tone_index:   # the line's note here, for the voices beside it (round 70: a pedal line had
                        shared[("line", (k, p))] = float(pedals.get(v, low_v))   # shared none, and Whole 167's apart voice wrote 0 notes)
                    continue
                taken = shared.setdefault(("taken", (k, p)), set()) if shared is not None else None   # the part's notes at this onset (a 2-tuple key: the voicing look-up unpacks every key)
                if beside and len(voices) == 1:            # a voice beside the line: with the line, its interval to the line's note (voice_intervals);
                    with_line = (k, p) in shared            # alone, its move from its own last note (voice_moves); both in scale steps, drawn
                    ref = (shared.get(("line", (k, p))) if with_line else line_before(k, p)) if with_line or prev_midi is None else None
                    if (with_line or prev_midi is None) and ref is None:
                        continue
                    t_iv = models["voice_intervals"].table if hasattr(models["voice_intervals"], "table") else models["voice_intervals"]
                    t_mv = models["voice_moves"].table if hasattr(models["voice_moves"], "table") else models["voice_moves"]
                    refused = set()
                    for _ in range(figures_mod.VOICE_TRIES):            # a pitch another voice of the part holds at this onset is drawn again (two copies of one
                        if ref is not None:                 # sample on one pitch phase); the onset is skipped when every try lands on one
                            ctx_iv = (role, kind, tune_mod.line_state(ref, scale), prev_steps)
                            chained = with_line and prev_steps != rhythm.START and prev_midi is not None
                            # the note both words agree on: its interval to the line's note (voice_intervals, chained on the interval
                            # before) and its own move from its last note (voice_moves); held out on FFVI the product beats either
                            # word alone (3.36 bits a unit against 3.87 and 3.71)
                            entry = weighted(tune_mod.interval_weights(t_iv, ctx_iv, refused, ref, scale, t_mv if chained else None, (role, kind, "with"), prev_midi if chained else None))
                            if entry is None:
                                break
                            steps = entry                   # the chain's next context
                            target = tune_mod.interval_pitch(entry, ref, scale)   # in semitones against a line note off the scale (round 66)
                        else:
                            steps = None
                            move = weighted({c: t_mv.p(str(c), (role, kind, "alone")) for c in range(-rhythm.VOICE_STEPS, rhythm.VOICE_STEPS + 1)
                                             if c not in refused and str(c) in t_mv.vocabulary})   # as a draw: never an interval or move the game never made
                            if move is None:
                                break
                            target = tune_mod.scale_pitch(tune_mod.scale_index(prev_midi, scale) + move, scale)
                        midi = in_register(target, registers[v])
                        if taken is None or midi not in taken:
                            break
                        refused.add(steps if steps is not None else move)
                    else:
                        continue
                    if taken is not None and midi in taken:
                        continue
                    if with_line and steps is not None:
                        prev_steps = str(steps)
                    prev_midi = midi
                elif tone_index and len(voices) == 1:      # no tables for it: a tone up the line's voicing (its rank's, or one drawn a span), walking with the motion
                    order = [(own_tone + int(walked) + d) % len(pitches) for d in range(len(pitches))]
                    free = [pitches[i] for i in order if taken is None or in_register(pitches[i], registers[v]) not in taken]
                    if not free:                            # every tone of the voicing already sounds in the part: the voice sits this onset out
                        continue
                    midi = in_register(free[0], registers[v])
                else:
                    midi = in_register(pitches[(j + offset) % len(pitches)] if offset else stacked[j], registers[v])
                    if shared is not None and not tone_index:
                        shared[("line", (k, p))] = midi     # the line's note here, for the voices beside it
                midi = unclashed(midi, [in_register(m, registers[v]) for m in pitches], tune)
                if taken is not None:
                    taken.add(int(round(midi)))
                notes.append((start, start + (until - start) * tune_mod.share_at(sounds, until - start), float(midi), v))
            walked += step
        voicings.append(" | ".join(bar_voicing) if bar_voicing else figures_mod.REST)
    return notes, figures, voicings
