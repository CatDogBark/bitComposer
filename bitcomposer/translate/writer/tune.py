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

from . import figures as figures_mod, upper as upper_mod, parts as parts_mod   # noqa: E402  the package's other sections


# --- the melody: phrases written free from the tables (phase 4, the melody slice) ---

PHRASE = 4                            # bars a phrase, as the phrase tables were counted
CONTOUR_STEP = 2.0                    # semitones a contour's thirds aim apart (phrases.LEVEL)
DETACHED = 0.5                        # the share of its gap a detached melody note sounds (the readings: under 0.75)
HELD = 0.95                           # and a held one
LENGTH_SLACK = 1.0                    # notes a line's held notes at a gap class may sit from its token song's share of them (round 141)
COPY_TRIES = 12                       # tunes drawn again when one copies a game's phrase (the reference set)
ARC_ABOVE = {"0": 0, "1-2": 2, "3-5": 4, "6+": 7}             # the summit table's classes, as semitones the climax may rise above the register
ARC_BELOW = {"0": 1, "1-2": 2, "3-5": 4, "6-9": 7, "10+": 11}   # the arc table's classes, as semitones a phrase's ceiling sits under the climax
ARC_ROOM = 7                          # semitones a phrase keeps above the register's floor whatever the arc says
BESIDE_SPAN = 24                      # semitones above its floor a second bass voice may sit when its pitch follows the line


TIER_SLACK = 0.5                      # onsets a bar a tune's running density may sit outside its tier's bounds (tier_bounds)
TIER_AFTER = 3                        # new rhythms drawn before the running density and grain are held to their words
GRAIN_SLACK = 0.1                     # how far a tune's running share of onsets off the beat may sit outside its grain's bounds


def grain_bounds(grain: str | None) -> tuple[float, float]:
    """The share of onsets off the beat a tune of this grain keeps its new rhythms to (rhythm.GRAINS: on-beat under 0.25,
    eighths to 0.5, fine over), GRAIN_SLACK either side; wide open without a grain."""
    if grain:
        low = 0.0
        for top, name in rhythm.GRAINS:
            if name == grain:
                return max(0.0, low - GRAIN_SLACK), min(1.0, top + GRAIN_SLACK)
            low = top
    return 0.0, 1.0


def offbeats(tokens: list) -> int:
    """How many of a figure's tokens sit off the beat."""
    return sum(1 for t in tokens if Fraction(t.partition(":")[0]).denominator != 1)


def tier_bounds(habit: str) -> tuple[float, float]:
    """The onsets a bar a part's tune keeps its running mean within, from its habit's density tier (rhythm.DENSITIES:
    sparse to 2, medium to 6, dense over), TIER_SLACK either side; wide open for a habit without a tier."""
    tier = (habit or "").split()[0] if habit else ""
    lo = 0.0
    for top, name in rhythm.DENSITIES:
        if name == tier:
            return max(0.0, lo - TIER_SLACK), (top + TIER_SLACK if top < 1e8 else 64.0)
        lo = top
    return 0.0, 64.0


def share_at(sounds, gap: float) -> float:
    """The share of a gap a note sounds: one share (a float), or the gap_sounds word's by the gap's class (a dict)."""
    if isinstance(sounds, dict):
        return float(sounds.get(rhythm.gap_class(gap), sounds.get(rhythm.GAP_CLASSES[0][1], 0.8)))
    return float(sounds)


def mask_figure(line_figure: str, mask: str) -> str:
    """A second bass voice's figure from the line's figure and a second_figures outcome (a mask over the line's onsets plus
    onsets of its own): the line's onsets it strikes with keep the line's marks (its pitch follows the line there,
    beside_pitch), its own onsets take the root mark and are re-pitched by its own move; REST where the mask rests."""
    if line_figure == figures_mod.REST or not line_figure or mask == "-":
        return figures_mod.REST
    toks = [(Fraction(t.partition(":")[0]), t.partition(":")[2] or "R") for t in rhythm._tokens(line_figure)]
    marks = {p: m for p, m in toks}
    positions = rhythm.apply_mask(rhythm.pattern(p for p, _ in toks), mask)
    if positions == "-" or not positions:
        return figures_mod.REST
    return " ".join(f"{p}:{marks.get(Fraction(p), 'R')}" for p in positions.split())


def first_onset(figures: list, bars: list, k: int) -> float | None:
    """When bar k's first note strikes, from its figure; None where it rests or there is no bar k. A bar's last note runs to
    it: the sounded share was counted against the gap to the voice's next onset, and a note ended at the bar line had
    dropped into a hole when the next bar began late (2026-10-24)."""
    if k >= len(figures) or k >= len(bars) or figures[k] == figures_mod.REST or not figures[k]:
        return None
    toks = rhythm._tokens(figures[k])
    return bars[k][0] + float(Fraction(toks[0].partition(":")[0])) if toks else None


def line_state(ref: float, scale: set) -> str:
    """The line note's state for the voice_intervals word: on the song's scale, or altered (off it)."""
    return "scale" if int(round(ref)) % 12 in scale else "altered"


def interval_entry(entry: str) -> tuple[str, int]:
    """A voice_intervals entry: ("steps", the scale steps) or ("semis", the semitones against an altered line note, "s-4")."""
    return ("semis", int(entry[1:])) if entry.startswith("s") else ("steps", int(entry))


def interval_pitch(entry: str, ref: float, scale: set) -> int:
    """The voice's note for an interval entry against the line's note: the scale steps from the line note's scale tone, or
    the semitones from the note itself (round 66: the counted steps had been put back on the scale, so a unison with the
    tune's leading tone came out a semitone under it)."""
    form, v = interval_entry(entry)
    return int(round(ref)) + v if form == "semis" else scale_pitch(scale_index(int(round(ref)), scale) + v, scale)


def interval_weights(t_iv, ctx: tuple, refused, ref: float, scale: set, t_mv=None, move_ctx: tuple | None = None, prev_midi: float | None = None,
                     span: tuple | None = None) -> dict:
    """{entry: weight} over the voice_intervals word's entries under `ctx` (its third value the line note's state, which
    picks the entries' form), within two octaves and off `refused`; with `t_mv` and the voice's last note, each weighed
    by the voice_moves word for the move the entry's note would make from it: the note both words agree on. `span`
    (round 143): the entries whose note the voice's span holds, alone: a note outside it is played an octave off
    (upper.in_register), so neither the interval it sounds nor the move it makes is the one weighed."""
    form = "semis" if ctx[2] == "altered" else "steps"
    out = {}
    for entry in sorted(t_iv.vocabulary, key=interval_entry):   # the vocabulary is a set: in a fixed order, or the draw rides the hash seed
        f, v = interval_entry(entry)
        if f != form or entry in refused or abs(v) > (rhythm.VOICE_SEMITONES if f == "semis" else rhythm.VOICE_STEPS):
            continue
        if span is not None and not span[0] <= interval_pitch(entry, ref, scale) <= span[1]:
            continue
        w = t_iv.p(entry, ctx)
        if t_mv is not None and prev_midi is not None:
            mv = str(scale_index(interval_pitch(entry, ref, scale), scale) - scale_index(int(round(prev_midi)), scale))
            if mv not in t_mv.vocabulary:
                continue
            w *= t_mv.p(mv, move_ctx)
        if w > 0:
            out[entry] = w
    return out


def beside_pitch(models: dict, role: str, kind: str, scale: set, rng: random.Random, ref: float | None, prev_steps: str,
                 prev_midi: float | None, moved: int = 0, refused=(), chord: set | None = None, chord_rate: float | None = None,
                 span: tuple | None = None) -> tuple[int | None, str | None]:
    """The note of a voice beside the line, as the voice_intervals and voice_moves words give it: with the line (`ref`, the
    line's note), the interval both words agree on, drawn from their product (the move the interval's note would make
    from the voice's last note; `moved`, the line's own move, is no longer needed and kept for the callers); alone, the
    voice's own move. `chord` and `chord_rate` (round 96): the chord's pitch classes and the line's drawn chord-tone
    share: the entries (or moves) landing on the chord take that share of the mass and the others the rest
    (hold_shares), as the melody's draw_move holds its tune. `span` (round 143, the counter-line's): the note is drawn
    among the notes the voice's span holds, the interval and the move weighed as they will sound; where the span holds
    none of them, as without it (the caller then moves the note an octave into the span). The words count the interval
    a voice sounds against the line and the move it makes: a note drawn outside the span and played an octave off
    sounded another interval and made another move, a seventh where a step was drawn (a span under an octave holds each
    pitch class once, so a line stepping over its top came back in at its bottom). (midi, the interval entry drawn, the
    chain's next `prev_steps`) or None; (None, None) where nothing can be drawn."""
    t_iv = models["voice_intervals"].table if hasattr(models["voice_intervals"], "table") else models["voice_intervals"]
    t_mv = models["voice_moves"].table if hasattr(models["voice_moves"], "table") else models["voice_moves"]

    def weighted(weights: dict):
        tot = sum(weights.values())
        if tot <= 0:
            return None
        x, acc = rng.random() * tot, 0.0
        for key_, w in weights.items():
            acc += w
            if x < acc:
                return key_
        return next(reversed(weights))
    if ref is not None:
        ctx = (role, kind, line_state(ref, scale), prev_steps)
        chained = prev_steps != rhythm.START and prev_midi is not None
        weights = interval_weights(t_iv, ctx, refused, ref, scale, t_mv if chained else None, (role, kind, "with"), prev_midi if chained else None, span) if span is not None else {}
        if not weights:                                     # no span, or none of the entries' notes inside it: every entry, as before round 143
            weights = interval_weights(t_iv, ctx, refused, ref, scale, t_mv if chained else None, (role, kind, "with"), prev_midi if chained else None)
        if chord and chord_rate is not None and weights:     # the chord's tones at the line's drawn share (round 96)
            entries = list(weights)
            held = hold_shares([weights[e] for e in entries], [([interval_pitch(e, ref, scale) % 12 in chord for e in entries], chord_rate)])
            weights = dict(zip(entries, held))
        entry = weighted(weights)
        return (interval_pitch(entry, ref, scale), entry) if entry is not None else (None, None)
    if prev_midi is None:
        return (None, None)
    moves = {c: t_mv.p(str(c), (role, kind, "alone")) for c in range(-rhythm.VOICE_STEPS, rhythm.VOICE_STEPS + 1)
             if c not in refused and str(c) in t_mv.vocabulary}
    at = scale_index(int(round(prev_midi)), scale)
    if span is not None:                                    # the moves that stay inside the span, where any does (round 143)
        inside = {c: w for c, w in moves.items() if span[0] <= scale_pitch(at + c, scale) <= span[1]}
        moves = inside if sum(inside.values()) > 0 else moves
    if chord and chord_rate is not None and moves:          # alone too: the chord's tones at the share (round 96)
        cs = list(moves)
        held = hold_shares([moves[c] for c in cs], [([scale_pitch(at + c, scale) % 12 in chord for c in cs], chord_rate)])
        moves = dict(zip(cs, held))
    move = weighted(moves)
    return (scale_pitch(at + move, scale), None) if move is not None else (None, None)


def counter(song: rhythm.Song, tune: list, tune_figures: list, masks: list, span: tuple, models: dict, rng: random.Random,
            kind: str, key: tuple | None = None, articulation: str = "mixed", register: tuple | None = None,
            role: str = R.COUNTER, spans_at=None, clash_rates: dict | None = None, chord_rate: float | None = None,
            tune_sounds: dict | None = None, shortest: float | None = None, lengths: dict | None = None,
            lengths_rng: random.Random | None = None, move_profile: dict | None = None) -> tuple[list, list, list]:
    """The counter-line written beside the tune (round 29): its bar from the tune's bar and a counter_figures mask
    (`masks`, one a bar, REST where the plan has it rest; rhythm.apply_mask: the tune's onsets it strikes with and its
    own, its own alone where the tune rests), its pitch by the voice words as the second bass voice's is
    (beside_pitch: with the tune, the interval both words agree on under `kind`, the sample relation; alone, its own
    move), kept in `span` by octaves (the tune's register widened by the layer offset's cap, as the chord parts' voices
    are: a drawn third below folded into the counter's own register had turned into a sixth above, round 23); its
    lengths from the values table under the song's articulation, as the melody's. `tune`: the tune's written notes
    [(start, end, midi, voice)]; `tune_figures`: its bars' patterns (REST where it rests); `register`: the counter's
    planned register, for a first note the tune leaves it alone with. On the tune's own sample a drawn unison is drawn
    again (two copies of one sample on one pitch), the onset skipped after VOICE_TRIES. FFVI's counter plays WITH the
    tune (0.67 of its onsets on the tune's, as loud, 2.5 semitones under); written as a second tune from the melody
    writer's own stream it had 0.43 of its onsets on the tune's, Whole 28 0.19 on one timbre in one register (2026-10-24).
    `spans_at`: bar -> the span the line is kept in there, where the token song's counter changes instrument by stretch
    (round 92). `clash_rates`: the clashes word's draw for the part ({"strong": share, "weak": share}): an interval drawn a
    semitone from a part written before this one (rhythm.clash_under) while the line is over its share for the beat is
    drawn again, VOICE_TRIES times, the last kept (round 94). `chord_rate`: the chord_tones word's draw for the line (round
    96): on a beat, while the line is not over the share, the interval or move entries landing on the chord take the share
    of the draw's mass (beside_pitch); the voice words know nothing of the landing, as the melody's moves table without
    the tone did, so the hold acts whenever the line is not over its rate. Since round 143 a note is drawn among the notes
    the bar's span holds (beside_pitch's `span`), and `move_profile`, the token song's counter-line's moves (round 130's
    field, plan.step_profiles), holds its far moves: while the line's share of moves of a fourth or more (FAR_MOVE) is
    over the song's line's, a note a fourth or more from the last is drawn again, as a clash is. Returns [(start, end,
    midi)], the bars' patterns and a log."""
    tonic, mode = key if key else (0, "major")
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]}
    bars = [(a, b) for _, a, b, _ in rhythm.all_bars_of(song, role)]
    at, line_times = {}, []                                 # the tune's note at (bar, position); its onsets in time
    for a_t, _, m, *rest in tune:
        if rest and rest[0] != 0:
            continue                                        # its line voice alone
        k = next((i for i, (a, b) in enumerate(bars) if a - rhythm.NEAR <= a_t < b - rhythm.NEAR), None)
        if k is not None:
            at.setdefault((k, rhythm.position(a_t - bars[k][0], song.division)), m)
            line_times.append((a_t, m))
    line_times.sort()
    figures, pitched = [figures_mod.REST] * len(bars), []
    prev_steps, prev_midi, last_with = rhythm.START, None, None
    with_tune = own = skipped = moved_in = 0
    under_line = sorted(n for r in rhythm.clash_under(role) for n in song.notes.get(r, [])) if clash_rates else []   # the parts written before this one (round 94)
    run = {"strong": [0, 0], "weak": [0, 0]}                # the line's onsets a semitone from one of them, and its onsets under one, so far
    chord_run = [0, 0]                                      # its strong-beat notes on the chord, and its strong-beat notes under a chord (round 96)
    far_rate = (move_profile or {}).get("far")              # the token song's line's share of moves of a fourth or more (round 143), or None
    far_run = [0, 0]                                        # the line's moves of a fourth or more, and its moves, so far

    def far_over(m: int) -> bool:
        """A note a fourth or more from the line's last while the line is over its song's share of such moves."""
        return (far_rate is not None and prev_midi is not None and abs(int(round(m)) - int(round(prev_midi))) >= FAR_MOVE
                and far_run[1] > 0 and far_run[0] / far_run[1] > far_rate)

    def chord_pcs(t: float):
        c = _chord_in_bar(song, t)
        return {(c[0] + i) % 12 for i in harmony.SHAPES.get(c[1], harmony.SHAPES[""])} if c else None

    def chord_hold(place: str, t: float):
        """The chord's pitch classes where the draw is held to the line's chord-tone share (round 96): on a beat, while the line
        is not over the share; None elsewhere."""
        if chord_rate is None or place != "strong" or (chord_run[1] and chord_run[0] / chord_run[1] > chord_rate):
            return None
        return chord_pcs(t)

    def over(place: str) -> bool:
        r = clash_rates.get(place) if clash_rates else None
        return r is not None and run[place][1] > 0 and run[place][0] / run[place][1] > r

    def clashing(m: int, t: float) -> bool:
        return any((int(round(m)) - pc) % 12 in upper_mod.CLASH for pc in upper_mod.sounding_pcs(under_line, t))
    for k, (a, b) in enumerate(bars):
        span_k = tuple(spans_at(k)) if spans_at is not None and spans_at(k) else span   # the bar's span where the line changes instrument (round 92)
        mask = masks[k] if k < len(masks) else figures_mod.REST
        if mask == figures_mod.REST or not mask:
            continue
        tune_pat = tune_figures[k] if k < len(tune_figures) and tune_figures[k] != figures_mod.REST else "-"
        positions = rhythm.apply_mask(tune_pat, mask)
        if positions == "-":
            continue
        figures[k] = positions
        for p in (Fraction(t) for t in positions.split()):
            ref = at.get((k, p))
            midi = steps = None
            octave = False                                  # the note drawn outside the bar's span and moved an octave into it
            t = a + float(p)
            place = "strong" if abs(float(p) - round(float(p))) < rhythm.NEAR else "weak"
            fallback = None                                 # the last pitch refused for a clash alone: kept when every try clashes (round 94)
            if ref is not None:
                moved = (scale_index(int(round(ref)), scale) - scale_index(int(round(last_with)), scale)) if last_with is not None else 0
                refused = set()
                for _ in range(figures_mod.VOICE_TRIES):
                    target, steps = beside_pitch(models, role, kind, scale, rng, ref, prev_steps, prev_midi, moved, refused,
                                                 chord=chord_hold(place, t), chord_rate=chord_rate, span=span_k)   # among the span's notes (round 143)
                    if target is None:
                        break
                    midi = upper_mod.in_register(target, span_k)
                    octave = midi != target
                    if kind == "same" and midi == int(round(ref)):
                        refused.add(steps)
                        midi = None
                        continue
                    if (clash_rates and over(place) and clashing(midi, t)) or far_over(midi):   # over the drawn share and a semitone from a part under
                        refused.add(steps)                  # it: drawn again; and a far move while the line is over its song's share of them
                        fallback, midi = midi, None         # (round 143)
                        continue
                    break
                if midi is None and fallback is not None:
                    midi = fallback
                if midi is None:
                    skipped += 1
                    continue
                prev_steps, last_with = str(steps), ref
                with_tune += 1
            else:
                refused = set()
                for _ in range(figures_mod.VOICE_TRIES):
                    target, _ = beside_pitch(models, role, kind, scale, rng, None, prev_steps, prev_midi, 0, refused,
                                             chord=chord_hold(place, t), chord_rate=chord_rate, span=span_k)
                    if target is None:                      # nothing before it: the chord's root nearest the counter's register
                        c = _chord_in_bar(song, t)
                        centre = sum(register) // 2 if register else sum(span_k) // 2
                        target = min((m for m in range(span_k[0], span_k[1] + 1) if m % 12 == ((c[0] if c else tonic) % 12)), key=lambda m: abs(m - centre), default=centre)
                        midi = upper_mod.in_register(target, span_k)
                        break
                    midi = upper_mod.in_register(target, span_k)
                    octave = midi != target
                    if (clash_rates and prev_midi is not None and over(place) and clashing(midi, t)) or far_over(midi):   # as with the tune: its own
                        refused.add(scale_index(int(round(target)), scale) - scale_index(int(round(prev_midi)), scale))   # move drawn again
                        fallback, midi = midi, None
                        continue
                    break
                if midi is None:
                    midi = fallback
                own += 1
            if under_line:
                pcs = upper_mod.sounding_pcs(under_line, t)
                if pcs:
                    run[place][1] += 1
                    run[place][0] += int(any((int(round(midi)) - pc) % 12 in upper_mod.CLASH for pc in pcs))
            if chord_rate is not None and place == "strong":   # the line's chord-tone share so far (round 96)
                pcs = chord_pcs(t)
                if pcs:
                    chord_run[1] += 1
                    chord_run[0] += int(int(round(midi)) % 12 in pcs)
            if prev_midi is not None:                       # the line's far moves so far (round 143)
                far_run[1] += 1
                far_run[0] += int(abs(int(round(midi)) - int(round(prev_midi))) >= FAR_MOVE)
            prev_midi = midi
            moved_in += octave
            pitched.append((k, p, float(midi)))
    length_run, lengths_rng = {}, lengths_rng or random.Random(f"{role}:note lengths")
    notes = []                                              # the lengths as the melody's: the values table under the articulation habit, whose
    for i, (k, p, m) in enumerate(pitched):                 # value is the gap to the next note across the bar line (a bar's last note runs to
        a, b = bars[k]                                      # the next bar's first onset, as the bass's does since round 26; at a rest bar the
        t = a + float(p)                                    # bar line stays)
        nxt = pitched[i + 1] if i + 1 < len(pitched) else None
        until = bars[nxt[0]][0] + float(nxt[1]) if nxt is not None and nxt[0] in (k, k + 1) else b
        gap = until - t
        if gap <= rhythm.NEAR:
            continue
        value = str(rhythm.position(gap, song.division))
        held = models["values"].draw((role, value, articulation), rng) if "values" in models else "held"
        share = None
        if lengths:                                         # held or detached as its token song's line is at the gap (round 141); the pooled
            held, share = own_length(lengths, gap, length_run, lengths_rng, tune_sounds)   # draw is made all the same, so the stream stands
        notes.append((t, t + sounded(gap, tune_sounds, held, shortest, share), m))   # the song's own shares (tune_sounds, round 98), no note under
                                                            # its token song's shortest usual one (round 136)
    log = [f"beside the tune on the {kind} sample: {sum(1 for f in figures if f != figures_mod.REST)} bars, {len(notes)} notes, {with_tune} with the tune's onsets, "
           f"{own} its own" + (f"; {skipped} onsets skipped (a unison on one sample)" if skipped else "") + f"; span {span}",
           f"notes drawn among the span's own: {len(pitched) - moved_in} of {len(pitched)}; {moved_in} moved an octave into it, the span holding none the words allow (round 143)"]
    if clash_rates and any(v[1] for v in run.values()):     # the clashes word's share held (round 94)
        log.append("a semitone from a part under it: " + ", ".join(f"{pl} {v[0]}/{v[1]} ({v[0] / v[1]:.2f}; the song's rate {clash_rates[pl]:.2f})" for pl, v in run.items() if v[1]))
    if chord_rate is not None and chord_run[1]:             # the chord_tones word's share held (round 96)
        log.append(f"chord tones on the beat: {chord_run[0]}/{chord_run[1]} ({chord_run[0] / chord_run[1]:.2f}; the song's rate {chord_rate:.2f})")
    if lengths and length_run:
        log.append(length_log(lengths, length_run))
    if far_rate is not None and far_run[1]:                 # the line's far moves against its token song's line's (round 143)
        log.append(f"moves of a fourth or more: {far_run[0]}/{far_run[1]} ({far_run[0] / far_run[1]:.2f}; the balance's song's line {far_rate:.2f}) (round 143)")
    return notes, figures, log
MOVED = {"moved up": 2, "moved down": -2}   # semitones a moved phrase shifts (a scale step; the scale then corrects each note)
DEGREE_PCS = {"1": (0,), "3": (3, 4), "5": (7,)}   # a phrase's ending degree -> intervals from the tonic it may land on
STRONG_SCALE = True                   # a note arriving on the beat sits in the scale


def contour_targets(shape: str, size: float | None = None) -> tuple:
    """Where a phrase's thirds sit against its start, by its contour
    (CONTOURS) and how far it goes (`size`, semitones: the contour-size
    table's draw; CONTOUR_STEP a third without one)."""
    if shape in ("rising", "falling"):
        far = size if size is not None else 2 * CONTOUR_STEP
        return (0, far / 2, far) if shape == "rising" else (0, -far / 2, -far)
    if shape in ("arch", "valley"):
        far = size if size is not None else CONTOUR_STEP
        return (0, far, 0) if shape == "arch" else (0, -far, 0)
    return (0, 0, 0)


class Tune:
    """The notes of one written phrase: (start, end in beats, midi), and its rhythm and intervals for the copy check."""

    def __init__(self, notes: list, a: float):
        self.notes = notes
        self.rhythm = [int(round((n[0] - a) * 12)) for n in notes]
        pitches = [int(round(n[2])) for n in notes]
        self.intervals = [y - x for x, y in zip(pitches, pitches[1:])]


CHORD_ON_BEAT = 0.65                  # the share of a tune's strong-beat notes that are chord tones (the games: 58 to 68 %)
REPEAT_RATE = {"rare": 0.02, "some": 0.12, "many": 0.35}   # a song's share of repeated notes by its repeat habit (the games: a
                                      # quarter of songs under 5 %, the median 13 %, a quarter over 30 %)
CONTOUR_RANGE = 5                     # semitones a line may stray from its contour's third before the draw is steered back
LEAP = 12                             # semitones: the moves table folds a move beyond an octave to LEAP + 1 (phrases.LEAP)
MOVES = [f"{m:+d}" if m else "0" for m in range(-LEAP - 1, LEAP + 2)]   # every move the moves table names
ECHO_SHARES = {"same": 0.3, "earlier": 0.3, "new": 0.4}   # the urn's shares where no recall table is given
CONTINUE = 0.8                        # when the bar before echoed an earlier bar, the share of "earlier" draws that go on with the bar after it
                                      # (the fallback without a recall_continues table, round 50)


class Cell:
    """A bar of the tune as a motif: its onsets (beats from the bar line), its
    intervals, its first note's offset from the bar's chord root, and its
    moves as scale steps, so it can come back on another chord in the scale."""

    def __init__(self, positions: list, pitches: list, root: int, scale: set, chord=None):
        self.positions = list(positions)
        self.pitches = [int(round(m)) for m in pitches]
        self.intervals = [y - x for x, y in zip(self.pitches, self.pitches[1:])]
        self.entry = (self.pitches[0] - root) % 12 if self.pitches else 0
        self.root = root % 12                   # the chord root the cell was realized on, and the chord (root, shape) where
        self.chord = chord                      # one was found: a recall's move is drawn by whether the chord changed (round 100)
        self.steps = to_steps(self.pitches, scale)
        self.key = " ".join(str(Fraction(p)) for p in self.positions) + " | " + " ".join(f"{i:+d}" for i in self.intervals)


def _ranks(scale: set) -> list:
    return sorted(scale) or list(range(12))


def scale_index(midi: int, scale: set) -> int:
    """A pitch's place counted in scale tones (a pitch off the scale: the tone below it)."""
    ranks = _ranks(scale)
    pc = midi % 12
    below = max((r for r in ranks if r <= pc), default=None)
    pos = ranks.index(below) if below is not None else len(ranks) - 1
    octave = midi // 12 if below is not None else midi // 12 - 1
    return octave * len(ranks) + pos


def scale_pitch(index: int, scale: set) -> int:
    ranks = _ranks(scale)
    return 12 * (index // len(ranks)) + ranks[index % len(ranks)]


def to_steps(pitches: list, scale: set) -> list:
    idx = [scale_index(m, scale) for m in pitches]
    return [y - x for x, y in zip(idx, idx[1:])]


def from_intervals(first: int, intervals: list) -> list:
    """A line from its first pitch and its intervals in semitones (a cell moved whole)."""
    out = [first]
    for iv in intervals:
        out.append(out[-1] + iv)
    return out


def fold_cell(pitches: list, register: tuple) -> list:
    """A cell moved whole by octaves into the register (low, high) where an octave fits it; its notes clamped to the
    register only where none does (a cell wider than the register), so a cell that comes back keeps its intervals."""
    if not pitches:
        return pitches
    low, high = register
    lo_, hi_ = min(pitches), max(pitches)
    shift = 0
    while hi_ + shift > high and lo_ + shift - 12 >= low:
        shift -= 12
    while lo_ + shift < low and hi_ + shift + 12 <= high:
        shift += 12
    return [min(high, max(low, m + shift)) for m in pitches]


def from_steps(first: int, steps: list, scale: set) -> list:
    """A line from its first pitch and its scale steps (a diatonic sequence)."""
    out, i = [first], scale_index(first, scale)
    for st in steps:
        i += st
        out.append(scale_pitch(i, scale))
    return out


def cell_pitches(pitches: list, source_root: int, root: int, scale: set, bound: tuple, previous: float | None) -> list:
    """A tune cell's pitches as another part plays them: its first note at the cell's offset from its own bar's chord root
    (`source_root`), on the new bar's root, in the part's register nearest the part's last note, and its moves as scale
    steps from there (a sequence lands as a player's does, again() for the tune's own echoes); every note folded into
    the register."""
    cell = Cell([0.0] * len(pitches), pitches, source_root, scale)
    pc = (root + cell.entry) % 12
    low, high = bound
    anchor = previous if previous is not None else (low + high) / 2
    first = min((m for m in range(low, high + 1) if m % 12 == pc), key=lambda m: (abs(m - anchor), m), default=int(round(anchor)))
    return [upper_mod.in_register(m, bound) for m in from_steps(first, cell.steps, scale)]


class Urn:
    """The tune writer's urn at the bar level: same (the bar before's cell again),
    earlier (one the song played before, by how often) or new, at the shares
    a recall table gives for the song's echo habit."""

    def __init__(self, recall, habit: str):
        self.recall, self.habit = recall, habit

    def shares(self, previous, played: Counter) -> dict:
        if self.recall is not None:
            ctx = tuple({"part": R.MELODY, "habit": self.habit}.get(c, "?") for c in self.recall.conditionings)
            raw = {k: self.recall.p(k, ctx) for k in tables.RECALL}
        else:
            raw = dict(ECHO_SHARES)
        total = sum(raw.values()) or 1.0
        same, earlier, new = (raw[k] / total for k in tables.RECALL)
        pool = sum(played.values()) - (played.get(previous.key, 0) if previous else 0)
        if previous is None:
            new, same = new + same, 0.0
        if pool <= 0:
            new, earlier = new + earlier, 0.0
        return {"same": same, "earlier": earlier, "new": new}

    def choose(self, rng: random.Random, previous, played: Counter) -> str:
        shares = self.shares(previous, played)
        x = rng.random()
        for k in ("same", "earlier", "new"):
            x -= shares[k]
            if x < 0:
                return k
        return "new"


def _weighted(rng: random.Random, options: list, weights: list):
    total = sum(weights)
    x = rng.random() * total
    for o, w in zip(options, weights):
        x -= w
        if x < 0:
            return o
    return options[-1]


def hold_shares(weights: list, holds: list, rounds: int = 8) -> list:
    """The fitting moves' weights rescaled so that each hold's marked moves take its share of the mass and the others the
    rest: `holds` pairs a mark per move with a share (the chord tones and the song's chord-tone rate; the off-scale moves
    and the off_scale word's draw; the clashing moves and the clashes word's). One hold is exact; several are fitted in
    turn and again (iterative proportional fitting) until they stand together as near as the moves allow (a chord tone off
    the scale, the raised seventh on a minor key's dominant, counts for both). A hold that marks every move or none, or
    whose sides have no mass (the repeated note at a rate of none), leaves the weights as they are (round 93)."""
    live = [(marks, min(1.0, max(0.0, r))) for marks, r in holds if any(marks) and not all(marks)]
    for _ in range(rounds if len(live) > 1 else 1):
        for marks, r in live:
            m_in = sum(w for w, k in zip(weights, marks) if k)
            m_out = sum(w for w, k in zip(weights, marks) if not k)
            if m_in > 0 and m_out > 0:
                weights = [w * (r / m_in if k else (1 - r) / m_out) for w, k in zip(weights, marks)]
    return weights


FAR_MOVE = 5                          # semitones from which a tune's move is far (round 130; rhythm.FAR_MOVE)
THIRD_MOVE = 3                        # and from which it is a third


def draw_move(moves_table, previous: str, mode: str, midi: float, rng: random.Random, register: tuple, scale: set,
              strong: bool, chord, tune: set, aim: float | None, habit: str | None = None, repeats: str = "some",
              chord_rate: float = CHORD_ON_BEAT, repeat_rate: float | None = None, over_repeats: bool = False,
              over_chord: bool = False, tone: str = "no chord", under_chord: bool = False,
              off_rate: float | None = None, off_over: bool = False, clash_rate: float | None = None, clash_over: bool = False,
              far_over: bool = False, third_over: bool = False) -> int:
    """One move of the tune from the moves table, drawn among the moves that
    fit (the register; off the chords' semitones; steered toward the
    contour when the line strays CONTOUR_RANGE from it), the fitting moves
    weighted by the table and, on a strong beat, the chord's tones given
    `chord_rate` of the mass (the song's chord-tone share, CHORD_ON_BEAT
    without one) unless the tune is already over its share (`over_chord`);
    the repeated note given `repeat_rate` of the mass (the song's, else
    the habit's tier) and none while the tune is over it (`over_repeats`).
    Since round 93 a move onto a note off the scale is barred on a beat
    only without the off_scale word (`off_rate` None, STRONG_SCALE); with
    it the off-scale moves take `off_rate` of the mass and none while the
    tune is over the share (`off_over`), on and off the beat; a move onto
    a semitone against a sounding part is barred only without the clashes
    word (`clash_rate` None, CLASH), else takes `clash_rate` of the mass
    and none while over (`clash_over`). Since round 130 no move of a
    fourth or more (FAR_MOVE) is drawn while the tune is over its token
    song's tune's share of them (`far_over`), and no third (THIRD_MOVE)
    while over its share of thirds (`third_over`), where a move of
    another class fits: under its shares the table's moves fall as the
    table and the chord's share have them. Returns the move in
    semitones."""
    low, high = register
    values = {"part": R.MELODY, "mode": mode, "previous": previous or rhythm.START, "habit": habit or "mixed",
              "place": "strong" if strong else "weak", "tone": tone}          # the landing: the beat arrived on, the tone left
    ctx = tuple(values.get(c, "?") for c in moves_table.conditionings)
    chord_pcs = set()
    if chord is not None:
        root, shape = chord
        chord_pcs = {(root + i) % 12 for i in harmony.SHAPES.get(shape, harmony.SHAPES[""])}
    options, weights, on_chord, offs, clashes = [], [], [], [], []
    for o in MOVES:
        step = int(o)
        m = midi + step
        if not (low <= m <= high):
            continue
        pc = int(round(m)) % 12
        clashing = any((pc - t) % 12 in upper_mod.CLASH for t in tune)
        if clashing and (clash_rate is None or clash_over):   # a semitone against a sounding part: barred without the clashes word (CLASH),
            continue                                        # and while the tune is over its drawn share (round 93)
        off = pc not in scale
        if off and ((off_rate is None and strong and STRONG_SCALE) or (off_rate is not None and off_over)):
            continue                                        # off the scale: barred on a beat without the off_scale word, and while over the share
        if aim is not None and abs(midi - aim) > CONTOUR_RANGE and (step == 0 or (step > 0) != (aim > midi)):
            continue                                        # steered back toward the contour: standing still is no move toward it
        w = moves_table.p(o, ctx)
        if w <= 0:
            continue
        options.append(step)
        weights.append(w)
        on_chord.append(pc in chord_pcs)
        offs.append(off)
        clashes.append(clashing)
    if not options:
        return 0
    for lo, hi, over in ((FAR_MOVE, 128, far_over), (THIRD_MOVE, FAR_MOVE, third_over)):
        kept = [not lo <= abs(st) < hi for st in options]   # the tune is over its token song's share of far moves, or of thirds (round 130):
        if over and any(kept) and not all(kept):            # none of that class, where a move of another fits
            options, weights, on_chord, offs, clashes = ([x for x, k in zip(xs, kept) if k] for xs in (options, weights, on_chord, offs, clashes))
    if 0 in options and len(options) > 1:
        # the repeated note passes every filter every time, and the chain feeds on itself after one; its share among
        # the fitting moves is held to the song's repeat rate, so the filters never funnel the line onto one pitch,
        # and it is left out while the tune (its echoed cells too) is over the rate
        if over_repeats:
            kept = [st != 0 for st in options]
            options, weights, on_chord, offs, clashes = ([x for x, k in zip(xs, kept) if k] for xs in (options, weights, on_chord, offs, clashes))
        else:
            r = repeat_rate if repeat_rate is not None else REPEAT_RATE.get(repeats, REPEAT_RATE["some"])
            r = min(0.95, max(0.0, r))
            rest = sum(w for st, w in zip(options, weights) if st != 0)
            weights = [w if st != 0 else r * rest / (1 - r) for st, w in zip(options, weights)]
    holds = []                                              # the counted shares the fitting moves' mass is held to, together (hold_shares)
    knows_landing = "tone" in moves_table.conditionings
    if strong and chord_pcs and (under_chord if knows_landing else not over_chord):
        # the chord weighting holds the song's chord-tone rate (a counted habit): for a moves table that knows nothing of
        # the landing, whenever the tune is not over its rate; for a table drawn by the beat and the tone left, which
        # carries the game's own approach to the chord (by step, in FFVI), only while the tune is under its rate (the
        # filters shift the chain's balance a little: 0.48 against FFVI's 0.56 with no weighting at all)
        holds.append((on_chord, chord_rate))
    if off_rate is not None:                                # the off-scale and the clashing moves' mass held to the song's drawn shares (round
        holds.append((offs, off_rate))                      # 93), as the chord tones' is: the game's own rates, not bans. Held together with the
    if clash_rate is not None:                              # chord's share, not before it: fitted first, the chord weighting had thinned the
        holds.append((clashes, clash_rate))                 # off-scale moves again (a tune drawn at 0.30 off the scale on the beat reached 0.10)
    return _weighted(rng, options, hold_shares(weights, holds))


def recall_anchor(cell, chord_now, move: str, register: tuple, near: float) -> int:
    """Where a recalled cell's first note sits for the recall_moves word's draw (round 100): at the cell's own pitch ("0"),
    moved by the chord root's motion from the cell's chord to this bar's ("root"), or by the drawn semitones ("+2", "-5",
    "6"); kept in the register by octaves, the octave nearest the cell's pitch, then the line's last note. FFVI's recalled
    cells come back at pitch in 0.70 of the earlier recalls (0.53 of the immediate ones), with the root in a quarter of the
    chord changes and by a step in most of the rest; the writer had re-rooted every recall on the new chord, so a passage
    recalled over a chord a fourth away came back a fourth away, where FFVI's stays or steps."""
    first = int(cell.pitches[0])
    if move == "root":
        root_now = chord_now[0] if chord_now else cell.root
        first += ((root_now - cell.root + 6) % 12) - 6
    elif move != "0":
        first += 6 if move == "6" else int(move)
    low, high = int(register[0]), int(register[1])
    options = [m for m in range(low, high + 1) if m % 12 == first % 12]
    if options:
        return min(options, key=lambda m: (abs(m - first), abs(m - near), m))
    return min(range(low, high + 1), key=lambda m: (abs(m - first), m), default=first)


def _chord_in_bar(song: rhythm.Song, t: float):
    c = rhythm._chord_at(song.chords, t)
    return (c.root, c.shape) if c is not None and c.root is not None and c.fit >= FIT else None


def sounded(gap: float, tune_sounds: dict | None, held: str, shortest: float | None = None, share: float | None = None) -> float:
    """How long a tune note sounds, in beats: its gap's share for a held or a detached note (sounded_share; `share`, round
    141: the token song's own share for the note, own_length's, in place of the pooled draw's), and since round 136 no
    shorter than the token song's tune's shortest usual note (`shortest`, in beats at the song's tempo) where the gap
    leaves room: a detached eighth at 0.3 of its gap had sounded 62 ms at 145 beats a minute."""
    length = gap * (share if share is not None else sounded_share(tune_sounds, held))
    return max(length, min(gap, shortest)) if shortest else length


def own_length(own: dict, gap: float, run: dict, rng: random.Random, tune_sounds: dict | None = None) -> tuple[str, float]:
    """A tune note's kind (held, detached) and the share of its gap it sounds, by its token song's own note lengths (round
    141; `own`: Plan.tune_lengths for the line: the whole line's entry under rhythm.LENGTH_WHOLE and each gap class's, the
    share of the notes held, the share of its gap a held note sounds and a detached one). The note is held at the song's
    rate for its gap's class (the whole line's where the song has too few notes of the class), drawn on the lengths' own
    stream, and the class's held notes so far are kept within LENGTH_SLACK notes of the song's share of them (`run`: class
    -> [held, notes], counted on here). It sounds the song's share for its kind at the class; where the song has no
    note of the kind at the class, its share at the nearest class that has one (the longer of two as near: a held note
    stops a little short of the next whatever its gap and a cut one is a stab whatever its gap, so either's share of a
    gap between two classes sits nearer the longer's; the game's Terra plays eighths and long notes, held 0.80 and 0.95
    of their gaps, and no quarter); the whole line's where no class has one; the pooled tune_sounds draw's where the
    song has none of the kind at all."""
    names = [n for _, n in rhythm.GAP_CLASSES]
    name = rhythm.gap_class(gap)
    whole = own[rhythm.LENGTH_WHOLE]
    rate = (own.get(name) or whole)[0]
    seen = run.setdefault(name, [0, 0])
    held = rng.random() < rate
    if held and seen[0] + 1 - rate * (seen[1] + 1) >= LENGTH_SLACK:
        held = False                                        # a held note more would put the class a note over the song's share
    elif not held and rate * (seen[1] + 1) - seen[0] >= LENGTH_SLACK:
        held = True                                         # a detached one more, a note under it
    seen[0] += held
    seen[1] += 1
    kind, i = ("held", 1) if held else ("detached", 2)
    k = names.index(name)
    near = min(((abs(j - k), -j, own[n][i]) for j, n in enumerate(names) if n in own and own[n][i] is not None), default=None)
    share = near[2] if near is not None else whole[i] if whole[i] is not None else sounded_share(tune_sounds, kind)
    return kind, share


def length_log(own: dict, run: dict) -> str:
    """The log line for a line written by its token song's note lengths (round 141): its notes held, whole and by the gap."""
    held, n = sum(v[0] for v in run.values()), sum(v[1] for v in run.values())
    return (f"note lengths from the balance's song (round 141): {held} of {n} notes held ({held / n:.2f}; the song's line {own[rhythm.LENGTH_WHOLE][0]:.2f}), by the gap: "
            + ", ".join(f"{name} {run[name][0]}/{run[name][1]}" + (f" ({own[name][0]:.2f})" if name in own else " (the whole line's share)")
                        for _, name in rhythm.GAP_CLASSES if name in run))


def sounded_share(tune_sounds: dict | None, held: str) -> float:
    """The share of its gap a tune note sounds: the song's own share for a held or a detached note (the tune_sounds word's
    draws, round 98), HELD or DETACHED without one."""
    default = HELD if held == "held" else DETACHED
    return float((tune_sounds or {}).get(held, default))


def melody(song: rhythm.Song, voice_notes: list, register: tuple, models: dict, rng: random.Random, habit: str,
           key: tuple | None = None, hold=(), reference=None, articulation: str = "mixed", echo_habit: str = "mixed",
           recall=None, step_habit: str = "mixed", repeat_habit: str = "some", plays: list | None = None,
           role: str = R.MELODY, chord_rate: float | None = None, repeat_rate: float | None = None,
           letters: dict | None = None, theme_body=None, grain: str | None = None, bounds_at=None, tune_sounds: dict | None = None,
           off_scale: dict | None = None, clash_rates: dict | None = None, recall_moves=None, moves_rng: random.Random | None = None,
           habit_at=None, envelope_at=None, move_profile: dict | None = None, shortest: float | None = None,
           lengths: dict | None = None, lengths_rng: random.Random | None = None) -> tuple[list, list, list]:
    """The melody written for the song (the module): bar by bar through the
    urn, as the bass and drums are. A bar's cell is its rhythm and its
    intervals; the urn keeps the bar before's cell, returns to an earlier
    one or makes a new one (the song's echo habit sets the shares); a cell
    that comes back is re-rooted on the bar's chord and its moves are scale
    steps, a sequence. A new cell's rhythm comes from the melody's bar
    table and its notes from the moves table, each move drawn among the
    moves that fit (the register, the phrase's contour), chord tones on
    the beat at the song's rate and, since round 93, notes off the scale
    and a semitone from a sounding part at the song's drawn shares (the
    `off_scale` and `clash_rates` words, by the beat; bans without them),
    the shares held together. Over the bars, phrases of PHRASE bars on the form: their
    relation (repeated, moved, answered, new), contour and ending drawn;
    the last note of a phrase lands on the ending's degree; a phrase that
    copies a game's (the reference set) is drawn again. Lengths from the
    articulation table. `role`: the melody, or the counter-line written
    the same way after it (the phrase tables count both lines as the
    tune's), clear of the melody as well as the upper parts; `chord_rate`:
    the song's share of strong-beat notes on the chord (the chord-tones
    table's draw), held by the moves drawn and by what an echoed cell's
    beats are snapped to; `repeat_rate`: the song's share of moves that
    repeat the note (the repeat-rates table's draw; the habit's tier
    without one), held the same way. A phrase after the first sits where
    the phrase-shifts table puts it against the one before (a moved
    phrase moved that far; a new one starting that far from where the
    last left off). `letters`: {part index: the part's phrases as
    letters} (rhythm.THEME, AGAIN, NEW; the plan's draw from the
    phrase-letters table): a THEME phrase after the first opens with the
    theme's head again and keeps as many of its next bars as the
    theme-body table draws (`theme_body`), then goes on new; an AGAIN
    phrase brings back the last phrase whose head was not the theme's; a
    NEW phrase is new, or answers the one before. Without letters the
    phrases stand only to the one before (the relations table). Where the
    bars have their token song's own onsets (`envelope_at` marked `own`,
    round 138) a phrase, a bar or a half bar comes back only where the
    bars keep within them, and the theme is stated anew where its head
    does not (`keeps`).
    `bounds_at`: bar -> the register the line is written in there, where
    the token song's line changes instrument by stretch (round 92); the
    line enters a new stretch's register by octaves and every move, recall
    and ending is drawn inside it. `off_scale`: {"strong": share, "weak":
    share}, the song's share of tune notes off the natural scale by the
    beat (the off_scale word, round 93), held by draw_move in place of the
    STRONG_SCALE ban; `clash_rates`: the same for onsets a semitone from a
    sounding part (the clashes word), in place of the CLASH ban, the bass
    counted among the sounding parts. `move_profile`: the token song's
    tune's moves by class (round 130, rhythm.TUNE_MOVES: {"same", "step",
    "third", "far"} as shares): the written tune's thirds and its moves
    of a fourth or more are kept to the song's shares (no drawn move of a
    class the tune is over; a bar played again entering by one weighed in
    its move within a third) and the repeated note takes the song's own
    share. `shortest` (round 136): the token song's tune's shortest usual
    note in beats at the song's tempo; no note sounds shorter where its
    gap leaves room. A note's gap runs to the next note, a bar's last
    note's to the next bar's first onset where the tune plays on in it
    (round 140), so a note held before a bar that opens with a rest
    sounds over the bar line. `lengths` (round 141): how the token
    song's tune sounds its notes by the gap (Plan.tune_lengths); a note
    is then held or detached at the song's own rate for its gap, drawn
    on `lengths_rng`, and sounds the song's own share (own_length), in
    place of the pooled values and tune_sounds draws. Returns [(start,
    end, midi)], the bars' rhythms and a log."""
    tonic, mode = key if key else (0, "major")
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]}
    bars = [(a, b, struck) for _, a, b, struck in rhythm.all_bars_of(song, role)]
    own = parts_mod.plays_as_own(plays, bars) if plays is not None else [rhythm.pattern(p for p, _ in struck) if struck else figures_mod.REST for _, _, struck in bars]
    meters = [max(1, round(b - a)) for a, b, _ in bars]
    manner = figures_mod.FreeManner(models["rhythm"].table.vocabulary, division=song.division)
    envelope_of = figures_mod.free_envelope(habit)
    clear_of = rhythm.UPPER + ((R.MELODY, R.COUNTER) if role != R.MELODY else ())   # a second counter-line stays clear of the first too
    tune_line = sorted(n for r in clear_of for n in song.notes.get(r, []))
    clash_line = sorted(n for r in clear_of + (R.BASS,) for n in song.notes.get(r, [])) if clash_rates else tune_line   # with the clashes word the
    off_run = {"strong": [0, 0], "weak": [0, 0]}          # bass counts too (round 93); the tune's notes off the scale by the beat, and all of them
    clash_run = {"strong": [0, 0], "weak": [0, 0]}        # its onsets a semitone from a sounding part, and its onsets under one, so far
    recall_moves = recall_moves.table if hasattr(recall_moves, "table") else recall_moves   # the recall_moves word (round 100), drawn on
    moves_rng = moves_rng if moves_rng is not None else rng                                  # an own stream; the moves drawn, for the log
    moves_drawn = Counter()

    def rate_for(rates, strong: bool):
        return rates.get("strong" if strong else "weak") if rates else None

    def over_rate(run, rates, strong: bool) -> bool:
        pl = "strong" if strong else "weak"
        r = rates.get(pl) if rates else None
        return r is not None and run[pl][1] > 0 and run[pl][0] / run[pl][1] > r

    def would_pass(run, rates, pl: str) -> bool:
        """Whether one more such note would put the run's share over the song's word: the share as a budget (round 100)."""
        r = rates.get(pl) if rates else None
        return r is not None and (run[pl][0] + 1) / (run[pl][1] + 1) > r

    def adds_over(a: float, positions: list, pitches: list) -> int:
        """How many of a recalled cell's notes, placed so, would put a share the tune holds over its word (round 93): a note
        off the scale where the off-scale share with it in would pass the song's for its beat, an onset a semitone from a
        sounding part where the clash share with it in would pass the song's; none without the words. A recall's placement
        keeps these down. Until round 100 a note counted only once the share was already over, so a song's first recalls
        clashed freely and the hold ran a bar behind the share it held: the recalled bars sat a semitone from the band on
        0.15 of their strong beats (FFVI 0.10) with a clean shift a third away untaken in half the cases."""
        n = 0
        for p, m in zip(positions, pitches):
            pl = "strong" if abs(p - round(p)) < rhythm.NEAR else "weak"
            if off_scale and int(round(m)) % 12 not in scale and would_pass(off_run, off_scale, pl):
                n += 1
            if clash_rates and any((int(round(m)) - pc) % 12 in upper_mod.CLASH for pc in upper_mod.sounding_pcs(clash_line, a + p)) and would_pass(clash_run, clash_rates, pl):
                n += 1
        return n
    def ending_pick(options: list, last: Cell, a: float) -> int:
        """The phrase ending's note among the drawn degree's options: the nearest that adds least to a share the tune is over
        (round 100: the ending had taken the nearest option whatever sounded under it, a semitone from the band on 0.17 of
        the phrase ends against FFVI's 0.06)."""
        want = last.pitches[-1]
        p = [last.positions[-1]] if last.positions else []
        return min(options, key=lambda m: (adds_over(a, p, [m]) if p else 0, abs(m - want), m))
    rate = chord_rate if chord_rate is not None else CHORD_ON_BEAT
    on_beat = [0, 0]                                        # the tune's strong-beat notes on the chord, and all of them, so far
    moves_table = models["moves"].table if hasattr(models["moves"], "table") else models["moves"]
    urn = Urn(recall, echo_habit)
    half_kinds = {}                       # bar -> its halves' urn kinds (new_cell_halves), for the log
    index = {num: k for k, num in enumerate(song.numbers)}
    windows, by_part = [], {}                               # the phrase windows, a part of the form at a time (a phrase ends with its part)
    for i, (bar, n, *rest) in enumerate(song.parts):
        ks = [index[num] for num in range(bar, bar + n) if num in index]
        mine = []
        for j in range(0, len(ks), PHRASE):
            chunk = ks[j:j + PHRASE]
            if len(chunk) < PHRASE and mine and mine[-1][-1] + 1 == chunk[0]:
                mine[-1] = mine[-1] + chunk
            else:
                mine.append(chunk)
        by_part[i] = (mine, rest[0] if rest else None, len(ks))
        windows += mine
    copies = {}                                             # a window's first bar -> the earlier window it plays again (a part the form repeats)
    for mine, of, n in by_part.values():
        if of is not None and of in by_part and by_part[of][2] == n and len(by_part[of][0]) == len(mine):
            for w, src in zip(mine, by_part[of][0]):
                if w and src:
                    copies[w[0]] = src[0]
    covered = {k for w in windows for k in w}
    windows += [[k] for k in range(len(bars)) if k not in covered]
    windows.sort()
    register0 = register                                    # the part's register; `register` is rebound a phrase at a time to its room in the arc

    def reg_of(k: int) -> tuple:
        """The register bar k is written in: its stretch's bound where the token song's line changes instrument there
        (`bounds_at`, round 92: samples_for's stretch bounds, a bar at a time), else the phrase's room under the arc
        (`register`, rebound a phrase at a time)."""
        b = bounds_at(k) if bounds_at is not None else None
        return tuple(b) if b else register

    tops = {}                                               # a window's first bar -> the phrase's ceiling: the arc (climax, arc, summit tables)
    if role == R.MELODY and all(k in models for k in ("climax", "arc", "summit")) and windows:
        from .. import phrases as phrases_mod
        place_at = {w[0]: phrases_mod.place_of(i, len(windows)) for i, w in enumerate(windows)}
        above = models["summit"].draw((R.MELODY,), rng, floored=False, floor_k=1)
        peak_top = min(120, register0[1] + ARC_ABOVE.get(above, 0))
        want = models["climax"].draw((R.MELODY,), rng, floored=False, floor_k=1)
        climax_w = next((w[0] for w in windows if place_at[w[0]] == want), windows[len(windows) // 2][0])
        for w in windows:
            if w[0] == climax_w:
                tops[w[0]] = peak_top
            else:
                below = models["arc"].draw((R.MELODY, place_at[w[0]]), rng, floored=False, floor_k=1)
                tops[w[0]] = max(register0[0] + ARC_ROOM, peak_top - ARC_BELOW.get(below, 2))
        arc_line = (f"arc: the climax {want} at bar {climax_w}, top {peak_top} (the register's {register0[1]}); the phrases' tops "
                    + " ".join(f"{w[0]}:{tops[w[0]]}" for w in windows))
    else:
        arc_line = None
    room_high = max(tops.values()) if tops else register0[1]    # the part's ceiling over the song: where a recalled cell may reach (round 49)
    figures = [figures_mod.REST] * len(bars)
    cells = {}                                              # bar index -> Cell
    played, by_key = Counter(), {}                          # the urn: cell key -> times played; key -> a Cell
    source = {}                                             # bar index -> the earlier bar it echoed (a passage recalled goes on)
    choices = {}                                            # bar index -> how the bar came (same, earlier, new, answered, copy)
    prev_cell, last_midi, last_move = None, float((register[0] + register[1]) // 2), rhythm.START
    last_time = None                                        # when the tune's last note fell: the note a move leaves, for its tone against the chord
    rhythm_played, rhythm_prev = Counter(), None
    new_strikes = []                                        # onsets of each new rhythm drawn: the tune's running density (tier_bounds)
    new_offs = []                                           # of them, the onsets off the beat: the tune's running grain (grain_bounds)
    draws = {k: (Counter(), None) for k in ("contours", "endings", "relations")}
    log, prev_phrase, prev_phrase_start = ([arc_line] if arc_line else []), None, None
    written_windows = {}                                    # a window's first bar -> (its live bars, their cells), for the form's repeats
    part_of_window = {}                                     # a window's first bar -> (its part's index, its place among the part's windows
    for i, (mine, _, _) in by_part.items():                 # the tune plays in: the letters count sounding phrases, as the counts did)
        j = 0
        for w in mine:
            if w and any(own[k] != figures_mod.REST for k in w):
                part_of_window[w[0]] = (i, j)
                j += 1
    themes = []                                             # the theme's statements, their cells: the first phrase the letters name the theme,
                                                            # and since round 138 any later one written new (see keeps), latest last
    theme_bars = set()                                      # the theme's statements' bars: where an echo may point (recall_sources)
    others = []                                             # the phrases written whose head is not the theme's, latest last
    part_of = {k: i for i, (mine, _, _) in by_part.items() for w_ in mine for k in w_}   # a bar -> its part of the form (its section)
    pair_urn = Urn(models["pair_recall"], echo_habit) if "pair_recall" in models else None   # the urn at the pair (round 40)
    bar_urn = Urn(models["pair_bar_recall"], echo_habit) if pair_urn is not None and "pair_bar_recall" in models else urn   # the bar urn inside a new pair
    pairs_played, pair_cells = Counter(), {}                # the pairs: (key, key) -> times played; a pair's first bar -> (cell, cell)
    prev_pair, prev_pair_key, prev_pair_at = None, None, None   # the pair before (its cells, its key, its first bar)
    pair_kinds, source_kinds = Counter(), Counter()         # for the log: the pair urn's draws, where the echoes pointed
    sources_table = models.get("recall_sources")

    def source_shares() -> dict | None:
        """Where an echo points (recall_sources: the section, the theme, elsewhere), the word's shares for the song's echo habit."""
        if sources_table is None:
            return None
        ctx = tuple({"part": R.MELODY, "habit": echo_habit}.get(c_, "?") for c_ in sources_table.conditionings)
        return {src: sources_table.p(src, ctx) for src in rhythm.RECALL_SOURCES}

    def by_source(k: int, pool: list) -> list:
        """A pool of earlier bars (j, thing) cut to where the drawn source says an echo of bar k points: the bars of bar k's own
        section, the theme phrase's, or another section's; a source with nothing in it gives its share to the others."""
        shares_ = source_shares()
        if not pool or shares_ is None:
            return pool
        groups = {src: [] for src in rhythm.RECALL_SOURCES}
        for j, thing in pool:
            groups["section" if part_of.get(j) == part_of.get(k) else "theme" if j in theme_bars else "elsewhere"].append((j, thing))
        live_ = {src: p for src, p in shares_.items() if groups[src]}
        total = sum(live_.values()) or 1.0
        x = rng.random() * total
        for src in rhythm.RECALL_SOURCES:
            if src in live_:
                x -= live_[src]
                if x < 0:
                    source_kinds[src] += 1
                    return groups[src]
        src = next(src for src in rhythm.RECALL_SOURCES if src in live_)
        source_kinds[src] += 1
        return groups[src]

    def continues() -> bool:
        """Whether a passage recalled goes on with the bar after its source (recall_continues, round 50: FFVI's share by the
        song's echo habit; the CONTINUE constant before it)."""
        t = models.get("recall_continues")
        if t is None:
            return rng.random() < CONTINUE
        ctx = tuple({"part": R.MELODY, "habit": echo_habit}.get(c_, "?") for c_ in t.conditionings)
        return t.draw(ctx, rng, floored=False) == "yes"

    def note_pair(live_: list, cells_: list, i: int) -> None:
        """Bars i-1 and i of a phrase just written as a pair the tune has played: the pair urn's memory."""
        nonlocal prev_pair, prev_pair_key, prev_pair_at
        if i % rhythm.PAIR != rhythm.PAIR - 1 or i >= len(cells_):
            return
        pr = (cells_[i - 1], cells_[i])
        prev_pair, prev_pair_key, prev_pair_at = pr, (pr[0].key, pr[1].key), live_[i - 1]
        pairs_played[prev_pair_key] += 1
        pair_cells[prev_pair_at] = pr

    def letter_of(w0: int) -> str | None:
        if not letters or w0 not in part_of_window:
            return None
        i, j = part_of_window[w0]
        mine = letters.get(i) or letters.get(str(i))
        if not mine:
            return None
        mine = mine.split() if isinstance(mine, str) else list(mine)
        return mine[j] if j < len(mine) else mine[-1]

    def end_phrase(cells_: list):
        """The writer's state after a phrase copied whole or in part."""
        nonlocal prev_cell, last_midi, last_move
        if not cells_:
            return
        prev_cell = cells_[-1]
        if prev_cell.pitches:
            last_midi = float(prev_cell.pitches[-1])
            if len(prev_cell.pitches) >= 2:
                d = prev_cell.pitches[-1] - prev_cell.pitches[-2]
                last_move = f"{d:+d}" if d else "0"
    phrase_size = None                                      # how far the phrase's contour goes (contour_targets)
    moves_seen = [0, 0, None]                               # the tune's repeated moves, all its moves, the last pitch written, so far
    rep_rate = repeat_rate if repeat_rate is not None else REPEAT_RATE.get(repeat_habit, REPEAT_RATE["some"])
    far_rate = (move_profile or {}).get("far")              # the token song's tune's share of moves of a fourth or more (round 130), or None
    if far_rate is not None and "same" in move_profile:     # and of repeated notes: the song's own, over the pooled repeat_rates draw
        rep_rate = move_profile["same"]
    third_rate = (move_profile or {}).get("third") if far_rate is not None else None
    far_seen = [0, 0, 0]                                    # the tune's far moves so far, the recalled cells moved to enter by another move, its thirds

    def over_far() -> bool:
        return far_rate is not None and moves_seen[1] > 0 and far_seen[0] / moves_seen[1] > far_rate

    def over_third() -> bool:
        return third_rate is not None and moves_seen[1] > 0 and far_seen[2] / moves_seen[1] > third_rate

    def over_move(semitones: float) -> int:
        """Whether a move of this size is of a class the tune is over its token song's share of (round 130): a third, a fourth or more."""
        d = abs(int(round(semitones)))
        return int((d >= FAR_MOVE and over_far()) or (THIRD_MOVE <= d < FAR_MOVE and over_third()))

    def over_repeats() -> bool:
        return moves_seen[1] > 0 and moves_seen[0] / moves_seen[1] > rep_rate

    def over_chord() -> bool:
        return on_beat[1] > 0 and on_beat[0] / on_beat[1] > rate

    def shift_of(relation: str) -> float:
        """How far the phrase sits from the one before, by their relation: the table's draw, else MOVED."""
        t = models.get("phrase_shifts")
        return float(t.draw((R.MELODY, mode, relation), rng)) if t is not None else float(MOVED.get(relation, 0))

    def wants_chord() -> bool:
        """Whether an echoed cell's beat is snapped onto the chord: while the tune's share so far is under the song's."""
        return on_beat[1] == 0 or on_beat[0] / on_beat[1] < rate

    def size_of(shape: str):
        t = models.get("contour_sizes")
        return float(t.draw((R.MELODY, mode, shape), rng)) if t is not None and shape != "level" else None

    def draw_shape(name, extra):
        played_, prev_ = draws[name]
        unit = tables.Unit(song.sid, song.game, "", {"part": R.MELODY, "mode": mode, **extra})
        out = models[name].draw(unit, prev_, played_, rng)
        played_[out] += 1
        draws[name] = (played_, out)
        return out

    own_onsets = envelope_at if getattr(envelope_at, "own", False) else None   # the token song's own onsets a bar for the tune's parts of the form
    own_new = [0, 0, 0]                                     # (round 138); the new bars drawn within them, those among the table's bars that fit, those none fit

    def keeps(k: int, n: int) -> bool:
        """Whether a bar of n notes is within bar k's own onsets (round 138: the token song's for its part of the form,
        half to one and a half times them); True for a bar without them. A bar that comes back, a half that comes back
        and a phrase answered keep within them as a new bar does: the urns' recalls had brought a busy part of the
        form's bars into a thin one's, and a recalled half gave a new bar notes its drawn rhythm had not (with the new
        bars' draws alone held, the tune was still out of range in 30 of 193 parts of the form). So do the letters' and the
        relation's phrases: the theme comes back as its latest statement whose head keeps within the phrase's first
        bar, bar by bar while its bars keep, and where no statement's head does the phrase is written new and stands
        as the theme's statement for the phrases after it (a theme first played over a part of the form of one note a
        bar had come back as a note a bar through a part of three: 31 bars of whole notes in a song on Searching for
        Friends); an earlier phrase comes back, and a phrase is repeated or moved, where every bar keeps, else the
        phrase is new. The form's repeat plays its own part of the form's bars, which keep already."""
        e = own_onsets(k) if own_onsets is not None else None
        return e is None or e[0] <= n <= e[1]

    def new_rhythm(k: int) -> list:
        """A new bar's onsets for a new cell: by the cell-rhythms table's draw
        (rhythm.new_cell_rhythm_units: new to the tune in 77 % of the games'
        new cells, the bar before's in 10 %, an earlier one's in 13 %), a
        rhythm new to the tune from the melody's bar table (in the manner
        and the habit's envelope), the bar before's, or one the tune played;
        the rhythm table's own urn is not run again (it had given new cells
        old rhythms: three distinct rhythms in 32 bars against FFVI's nine;
        always new gave 16.5 distinct cells against 12.5)."""
        nonlocal rhythm_prev
        env = envelope_of(own[k], meters[k])
        shifted = envelope_at(k, statistics.median(new_strikes) if len(new_strikes) >= 2 else None) if envelope_at is not None else None   # the section's
                                                            # density tier shift as the bar's envelope, from the tune's own running density (round 101)
        if shifted is not None:
            env = (shifted[0], shifted[1], False, meters[k])
        own_env = shifted is not None and own_onsets is not None   # the token song's own onsets a bar for this part of the form (round 138):
                                                            # the bar's density is theirs, not the tier's running mean
        h = habit_at(k) if habit_at is not None else habit   # the bar's habit: its density tier shifted where the section says (round 101)
        values = {"part": role, "meter": meters[k], "previous": rhythm_prev or rhythm.START, "habit": h, "feel": rhythm.song_feel(song), "tempo": rhythm.band(song.bpm)}
        unit = tables.Unit(song.sid, song.game, "", values)
        lo, hi = tier_bounds(h)                         # the tune keeps to its tier's density and its drawn grain over the song (round 66):
        g_lo, g_hi = grain_bounds(grain)                    # the bar chain, conditioned on the bar before, had locked a "medium" tune into one
        def tier_ok(f):                                     # game song's grain, 2.9 onsets a bar in one song and 12.2 in another (FFVI's medium
                                                            # tunes: 3.4 to 5.1 a bar), and 4 of 7 medium tunes on the beat (0.15-0.21 of their
                                                            # onsets off it; FFVI's medium tunes 0.33-0.51, the tune_grain word's draw)
            if own_env:                                     # a bar with the song's own onsets is asked neither (round 138): its density is the
                return True                                 # song's, and the grain is a share over the tune that a bar's density decides more
                                                            # than the tune does (FFVI's one-note bars strike off the beat in 0.10 of cases, its
                                                            # five-to-eight-note bars in 0.51). With every bar the song's own no running share
                                                            # was left, and the grain held to a bar by itself refused every one-note bar (0 or 1
                                                            # off the beat, never 0.33-0.51) and put one of each two-note bar's notes off the beat
            toks = rhythm._tokens(f)
            n = sum(new_strikes) + len(toks)
            off = (sum(new_offs) + offbeats(toks)) / max(1, n)
            if not g_lo <= off <= g_hi:                     # the grain from the first draw: a tune of few new rhythms is its first ones echoed
                return False
            return len(new_strikes) < TIER_AFTER or lo <= n / (len(new_strikes) + 1) <= hi
        fit = lambda f: manner.fits(f) and figures_mod.within(f, env) and tier_ok(f)   # noqa: E731
        kind = models["cell_rhythms"].draw((R.MELODY,), rng, floored=False) if "cell_rhythms" in models else "new"
        figure = None
        if kind == "previous" and rhythm_prev is not None and fit(rhythm_prev):
            figure = rhythm_prev
        elif kind == "earlier":
            pool = {f: n for f, n in rhythm_played.items() if f != rhythm_prev and fit(f)}
            if pool:
                figure = rng.choices(list(pool), list(pool.values()))[0]
        if figure is None:
            figure = models["rhythm"].draw_new(unit, rhythm_played, rng, keep=fit) if hasattr(models["rhythm"], "draw_new") else models["rhythm"].draw(unit, rhythm_prev, rhythm_played, rng, keep=fit)
        for _ in range(figures_mod.TRIES):
            if fit(figure):
                break
            figure = models["rhythm"].table.draw(models["rhythm"].table.context(unit), rng, values, floored=False, floor_k=models["rhythm"].table.chain_floor)
        else:
            drawn = figure
            figure = next((f for f in rhythm_played if fit(f)), None)
            if figure is None and own_env:                  # a bar asked what its context's bars seldom play (round 138): among the bars the
                figure = parts_mod.among(manner, models["rhythm"], unit, rng, fit)   # table knows that fit, by its own probabilities here
                own_new[1] += figure is not None                                     # (parts.among, round 133), before a bar that does not
            if figure is None:
                figure = drawn if manner.fits(drawn) else "0"
                own_new[2] += own_env
        own_new[0] += own_env
        rhythm_played[figure] += 1
        rhythm_prev = figure
        if shifted is None:                                 # a shifted section's bars are the word's, not the tune's running tier (round 101)
            new_strikes.append(len(rhythm._tokens(figure)))
            new_offs.append(offbeats(rhythm._tokens(figure)))
        return [float(Fraction(t.partition(":")[0])) for t in rhythm._tokens(figure)]

    def realize(k: int, positions: list, pitches: list) -> Cell:
        nonlocal last_time
        a, b, _ = bars[k]
        if positions:
            last_time = a + positions[-1]
        chord = _chord_in_bar(song, a)
        cell = Cell(positions, pitches, chord[0] if chord else tonic, scale, chord=chord)
        figures[k] = " ".join(str(Fraction(p)) for p in positions)
        cells[k] = cell
        for m in pitches:
            if moves_seen[2] is not None:
                moves_seen[1] += 1
                moves_seen[0] += int(round(m)) == int(round(moves_seen[2]))
                far_seen[0] += abs(int(round(m)) - int(round(moves_seen[2]))) >= FAR_MOVE
                far_seen[2] += THIRD_MOVE <= abs(int(round(m)) - int(round(moves_seen[2]))) < FAR_MOVE
            moves_seen[2] = m
        for p, m in zip(positions, pitches):
            here = _chord_in_bar(song, a + p) if abs(p - round(p)) < rhythm.NEAR else None
            if here is not None:
                on_beat[1] += 1
                on_beat[0] += int(round(m)) % 12 in {(here[0] + i) % 12 for i in harmony.SHAPES.get(here[1], harmony.SHAPES[""])}
            place = "strong" if abs(p - round(p)) < rhythm.NEAR else "weak"   # the running shares the words are held to (round 93)
            off_run[place][1] += 1
            off_run[place][0] += int(round(m)) % 12 not in scale
            pcs = upper_mod.sounding_pcs(clash_line, a + p)
            if pcs:
                clash_run[place][1] += 1
                clash_run[place][0] += any((int(round(m)) - pc) % 12 in upper_mod.CLASH for pc in pcs)
        return cell

    def new_cell(k: int, positions: list, shape: str, phrase_start_midi: float | None, a0: float, b0: float) -> Cell:
        """A new cell for bar k: the notes from the moves table under the phrase's contour."""
        nonlocal last_midi, last_move, last_time
        a, b, _ = bars[k]
        reg = reg_of(k)
        targets = contour_targets(shape, phrase_size)
        pitches, midi, move, t_from = [], last_midi, last_move, last_time
        if not reg[0] <= midi <= reg[1]:
            midi = float(upper_mod.in_register(int(round(midi)), reg))   # the line enters its stretch's register by octaves (round 92)
        for p in positions:
            t = a + p
            third = min(2, int(3 * (t - a0) / max(1e-9, b0 - a0)))
            aim = (phrase_start_midi + targets[third]) if phrase_start_midi is not None else None
            strong = abs(p - round(p)) < rhythm.NEAR
            tone = phrases.against_chord(midi, t_from, song) if t_from is not None else "no chord"
            step = draw_move(moves_table, move, mode, midi, rng, reg, scale, strong, _chord_in_bar(song, t), upper_mod.sounding_pcs(clash_line, t), aim,
                             step_habit, repeat_habit, rate, repeat_rate=rep_rate, over_repeats=over_repeats(), over_chord=over_chord(), tone=tone,
                             under_chord=wants_chord(), off_rate=rate_for(off_scale, strong), off_over=over_rate(off_run, off_scale, strong),
                             clash_rate=rate_for(clash_rates, strong), clash_over=over_rate(clash_run, clash_rates, strong),
                             far_over=over_far(), third_over=over_third())
            midi = midi + step
            move = f"{step:+d}" if step else "0"
            pitches.append(midi)
            t_from = t
        last_midi, last_move = midi, move
        return realize(k, positions, pitches)

    def new_cell_halves(k: int, positions: list, shape: str, phrase_start_midi: float | None, a0: float, b0: float) -> Cell:
        """A new bar a half at a time (round 38): each half same (the half before's cell again), earlier (one the tune
        played before, by how often) or new, at the half_recall word's shares for the song's echo habit. A recalled half
        comes back re-rooted on the bar's chord in the register, its intervals exact (as again() brings a bar back, round 41);
        a new half takes the drawn rhythm's onsets with new moves. FFVI's tune reuses half-bar cells (0.50 heard earlier,
        themed 0.63) where a bar-grain urn drew a whole new bar (0.39). A half the drawn rhythm gives fewer than
        HALF_CELL_NOTES notes is no cell and stays as drawn (round 47, 2026-10-28): the word counts halves of two notes
        and more, and the urn run on every half had replaced the tune's held halves with recalled two-note ones, so the
        written medium tune had 0.11 of its bars at one or two notes where FFVI's has 0.27, and sat a note a bar denser
        at every habit tier (sparse 2.7 against 2.0, medium 5.1 against 4.1, dense 8.2 against 7.0)."""
        nonlocal last_midi, last_move, last_time
        a, b, _ = bars[k]
        reg = reg_of(k)
        half = meters[k] / 2.0
        chord = _chord_in_bar(song, a)
        root = chord[0] if chord else tonic

        def half_key(ps: list, ms: list) -> str:
            return " ".join(str(round(p * 12)) for p in ps) + " | " + " ".join(f"{y - x:+d}" for x, y in zip(ms, ms[1:]))

        pool, plays = {}, Counter()                         # the tune's half-bar cells so far: key -> (positions, entry, steps)
        for j, c in sorted(cells.items()):
            if j >= k:
                continue
            cj = _chord_in_bar(song, bars[j][0])
            rj, hj = (cj[0] if cj else tonic), meters[j] / 2.0
            for h in (0, 1):
                idx = [i for i, p in enumerate(c.positions) if (p < hj) == (h == 0)]
                if len(idx) < rhythm.HALF_CELL_NOTES:
                    continue
                ps, ms = [c.positions[i] - h * hj for i in idx], [c.pitches[i] for i in idx]
                key_ = half_key(ps, ms)
                pool.setdefault(key_, (ps, (ms[0] - rj) % 12, [y - x for x, y in zip(ms, ms[1:])], ms[0], cj))   # its intervals, exact (round 41);
                                                                                                                # its first pitch and chord (round 100)
                plays[key_] += 1
        prev_key = None
        if k - 1 in cells:                                  # the half before: the bar before's second half
            c, hj = cells[k - 1], meters[k - 1] / 2.0
            idx = [i for i, p in enumerate(c.positions) if p >= hj]
            if len(idx) >= rhythm.HALF_CELL_NOTES:
                prev_key = half_key([c.positions[i] - hj for i in idx], [c.pitches[i] for i in idx])
        ctx = tuple({"part": R.MELODY, "habit": echo_habit}.get(c_, "?") for c_ in models["half_recall"].conditionings)
        raw = {kd: models["half_recall"].p(kd, ctx) for kd in tables.RECALL}
        all_pos, all_pitches, kinds = [], [], []
        midi, move, t_from = last_midi, last_move, last_time
        if not reg[0] <= midi <= reg[1]:
            midi = float(upper_mod.in_register(int(round(midi)), reg))   # the line enters its stretch's register by octaves (round 92)
        targets = contour_targets(shape, phrase_size)
        for h in (0, 1):
            lo = h * half
            shares = dict(raw)
            beside = len(all_pos) if h else sum(1 for p in positions if p >= half)   # the bar's notes beside this half: the half before's as
            back = lambda kk: keeps(k, beside + len(pool[kk][0]))   # noqa: E731     # written, the half after's as drawn; a half comes back
                                                                                      # where the bar stays within its own onsets (round 138)
            if sum(1 for p in positions if (p < half) == (h == 0)) < rhythm.HALF_CELL_NOTES:
                shares = {"new": 1.0, "same": 0.0, "earlier": 0.0}   # a half the drawn rhythm gives fewer notes than a cell is no cell: it stays as
            if prev_key not in pool or not back(prev_key):            # drawn (round 47: the word counts halves of HALF_CELL_NOTES and more, and the urn
                shares["new"], shares["same"] = shares["new"] + shares["same"], 0.0   # run on every half had turned the tune's one-note
            earlier = {kk: n for kk, n in plays.items() if kk != prev_key and back(kk)}
            if not earlier:
                shares["new"], shares["earlier"] = shares["new"] + shares["earlier"], 0.0
            total = sum(shares.values()) or 1.0
            x, kind = rng.random() * total, "new"
            for kd in tables.RECALL:
                x -= shares[kd]
                if x < 0:
                    kind = kd
                    break
            key_ = prev_key if kind == "same" else (_weighted(rng, list(earlier), list(earlier.values())) if kind == "earlier" else None)
            if key_ is not None:
                ps, entry, steps, src_first, src_chord = pool[key_]
                low, high = reg
                anchor_ = midi if midi is not None else (low + high) / 2
                if recall_moves is not None:                # the half comes back where the word says (round 100): at pitch, with the root, by a step
                    move = recall_moves.draw((R.MELODY, kind, "same" if chord == src_chord else "other"), moves_rng, floored=False, floor_k=1)
                    moves_drawn[move] += 1
                    first = recall_anchor(SimpleNamespace(pitches=[src_first], root=(src_chord[0] if src_chord else tonic) % 12), chord, move, (low, high), anchor_)
                else:
                    pc = (root + entry) % 12
                    first = min((m for m in range(low, high + 1) if m % 12 == pc), key=lambda m: (abs(m - anchor_), m), default=int(round(anchor_)))
                pos_h = [lo + p for p in ps]
                if adds_over(a, pos_h, from_intervals(first, steps)):   # over a word's share: the half moved within a third, as a bar is (round 93)
                    first = max((x for x in range(first - 4, first + 5) if low <= x <= high and (x == first or x % 12 in scale)),
                                key=lambda x: (-adds_over(a, pos_h, from_intervals(x, steps)), -abs(x - first), -x), default=first)
                ms = fold_cell(from_intervals(first, steps), reg)   # the half's intervals exact (round 41), the whole half folded in
            else:
                pos_h, ms = [p for p in positions if (p < half) == (h == 0)], []
                for p in pos_h:
                    t = a + p
                    third = min(2, int(3 * (t - a0) / max(1e-9, b0 - a0)))
                    aim = (phrase_start_midi + targets[third]) if phrase_start_midi is not None else None
                    strong = abs(p - round(p)) < rhythm.NEAR
                    tone = phrases.against_chord(midi, t_from, song) if t_from is not None else "no chord"
                    step = draw_move(moves_table, move, mode, midi, rng, reg, scale, strong, _chord_in_bar(song, t), upper_mod.sounding_pcs(clash_line, t), aim,
                                     step_habit, repeat_habit, rate, repeat_rate=rep_rate, over_repeats=over_repeats(), over_chord=over_chord(), tone=tone,
                                     under_chord=wants_chord(), off_rate=rate_for(off_scale, strong), off_over=over_rate(off_run, off_scale, strong),
                             clash_rate=rate_for(clash_rates, strong), clash_over=over_rate(clash_run, clash_rates, strong),
                             far_over=over_far(), third_over=over_third())
                    midi = midi + step
                    move = f"{step:+d}" if step else "0"
                    ms.append(midi)
                    t_from = t
            if ms:
                if key_ is not None:
                    step_ = int(round(ms[-1] - midi))
                    move = f"{step_:+d}" if step_ else "0"
                    midi, t_from = float(ms[-1]), a + pos_h[-1]
                prev_key = half_key([p - lo for p in pos_h], [int(round(m)) for m in ms]) if len(ms) >= rhythm.HALF_CELL_NOTES else None
            kinds.append(kind if ms else "rest")
            all_pos += pos_h
            all_pitches += ms
        last_midi, last_move = midi, move
        half_kinds[k] = kinds
        return realize(k, all_pos, all_pitches)

    def again(k: int, cell: Cell, kind: str = "earlier") -> Cell:
        """An earlier cell in bar k: where the recall_moves word has a say
        (round 100) its first note sits where the word's draw puts it (at
        the cell's pitch, moved with the chord root, or by a step: FFVI's
        recalls stay at pitch in 0.7 of cases), else re-rooted on the bar's
        chord; its intervals exact; the whole cell then moved within a third
        where the tune wants its beats on the chord or the cell adds to a
        share the tune is over (the chord-tone, off-scale and clash holds
        weighed together since round 100: the chord had come first, and a
        clean shift a third away was passed over for one more chord tone);
        and the whole cell folded by octaves into the register. `kind`: the
        word's recall (same: the bar before's cell; earlier). Its intervals are kept exact
        rather than as scale steps (round 41, 2026-10-28): rebuilt by steps,
        with each note clamped to the register, 0.46 of the written recalls
        (theme returns, pairs and bars alike) had come back as a cell the
        tune never played, which the ear hears as a rhythm with new notes;
        FFVI's cells that come back moved keep their intervals (moved 0.20 of
        bars, a rhythm with other intervals 0.06)."""
        nonlocal last_midi, last_move
        a, b, _ = bars[k]
        chord = _chord_in_bar(song, a)
        root = chord[0] if chord else tonic
        low, high = reg_of(k)
        if recall_moves is not None and cell.pitches:
            move = recall_moves.draw((R.MELODY, kind, "same" if chord == cell.chord else "other"), moves_rng, floored=False, floor_k=1)
            moves_drawn[move] += 1
            first = recall_anchor(cell, chord, move, (low, high), last_midi)
        else:
            pc = (root + cell.entry) % 12
            first = min((m for m in range(low, high + 1) if m % 12 == pc), key=lambda m: (abs(m - last_midi), m), default=int(round(last_midi)))

        def build(start: int) -> list:
            """The cell from its first note with its intervals exact."""
            out = [start]
            for iv in cell.intervals:
                out.append(out[-1] + iv)
            return out

        def on_chord(pitches: list) -> int:
            """How many of the cell's strong-beat notes land on their beat's chord."""
            n = 0
            for p, m in zip(cell.positions, pitches):
                here = _chord_in_bar(song, a + p)
                if here is not None and abs(p - round(p)) < rhythm.NEAR:
                    n += int(m % 12 in {(here[0] + i) % 12 for i in harmony.SHAPES.get(here[1], harmony.SHAPES[""])})
            return n

        def enters_far(x: int) -> int:
            """Whether the cell begun on x enters by a move of a class the tune is over its share of (round 130)."""
            return over_move(x - moves_seen[2]) if moves_seen[2] is not None else 0

        pitches = build(first)
        snap = wants_chord() and any(_chord_in_bar(song, a + p) is not None and abs(p - round(p)) < rhythm.NEAR for p in cell.positions)
        if snap or adds_over(a, cell.positions, pitches) or enters_far(first):
            # the sequence lands its beats on the new chord as a player's does: the whole cell moved to the nearest scale
            # note within a third that puts the most strong beats on the chord. No single note is bent, so the cell's
            # intervals, and with them the tune's steps, stay what the table drew (bending one note had cost the melody
            # a point of steps and the counter-line eleven). Since round 93 the same move, after the chord, keeps the cell
            # from adding to a share the tune is over: off the scale, or a semitone from a sounding part (the words' draws).
            # Since round 130 an entrance by a third or by a fourth or more, while the tune is over its share of those, is weighed with them, one for one.
            best = max((x for x in range(first - 4, first + 5) if low <= x <= high and (x == first or x % 12 in scale)),
                       key=lambda x: ((on_chord(build(x)) if snap else 0) - adds_over(a, cell.positions, build(x)) - enters_far(x), -abs(x - first), -x), default=first)
            far_seen[1] += enters_far(first) and not enters_far(best)
            pitches = build(best)
        pitches = fold_cell(pitches, (low, max(high, room_high) if bounds_at is None else high))   # the part's whole room (round 49): folded into the phrase's room under the
        last_midi = float(pitches[-1]) if pitches else last_midi    # arc, a wider recalled cell had been clamped and bent
        last_move = f"{pitches[-1] - pitches[-2]:+d}" if len(pitches) >= 2 and pitches[-1] != pitches[-2] else ("0" if len(pitches) >= 2 else last_move)
        return realize(k, cell.positions, pitches)

    for w in windows:
        a0, b0 = bars[w[0]][0], bars[w[-1]][1]
        live = [k for k in w if own[k] != figures_mod.REST]
        if not live:
            continue
        register = (register0[0], tops.get(w[0], register0[1]))   # this phrase's room: up to its ceiling in the arc (new_cell, again and
        reg_w = register                                    # draw_move read `register` as the phrase is written)
        src0 = copies.get(w[0])
        if src0 is not None and src0 in written_windows and len(written_windows[src0][0]) == len(live):
            phrase_cells = [realize(k, c.positions, list(c.pitches)) for k, c in zip(live, written_windows[src0][1])]   # the part's tune again
            for i, (k, c) in enumerate(zip(live, phrase_cells)):
                choices[k] = "form"
                played[c.key] += 1
                by_key.setdefault(c.key, c)
                note_pair(live, phrase_cells, i)
            end_phrase(phrase_cells)
            prev_phrase, prev_phrase_start = phrase_cells, a0
            written_windows[w[0]] = (live, phrase_cells)
            log.append(f"bar {w[0]}: the form's repeat of bar {src0}, its tune again")
            continue
        letter = letter_of(w[0])
        stated = next((t for t in reversed(themes) if keeps(live[0], len(t[0].positions))), None) if letter == rhythm.THEME else None   # the theme's
                                                            # latest statement whose head keeps within this phrase's first bar's own onsets (round 138)
        if stated is not None:                              # the hook comes back: its head, as much of its body as the table says, then on
            keep = 1 + (int(theme_body.draw((R.MELODY,), rng, floored=False)) if theme_body is not None else 0)
            shape = draw_shape("contours", {})
            phrase_size = size_of(shape)
            ending = draw_shape("endings", {})
            phrase_cells, start_midi = [], None
            for i, k in enumerate(live):
                if i < keep and i < len(stated) and keeps(k, len(stated[i].positions)):
                    cell = again(k, stated[i])
                    choices[k] = "theme"
                else:
                    cell = (new_cell_halves if "half_recall" in models else new_cell)(k, new_rhythm(k), shape, start_midi, a0, b0)
                    choices[k] = "new"
                if start_midi is None and cell.pitches:
                    start_midi = float(cell.pitches[0])
                played[cell.key] += 1
                by_key.setdefault(cell.key, cell)
                prev_cell = cell
                phrase_cells.append(cell)
                note_pair(live, phrase_cells, i)
            if keep < len(live) and ending in DEGREE_PCS and phrase_cells and phrase_cells[-1].pitches:
                want = {(tonic + i) % 12 for i in DEGREE_PCS[ending]}
                last = phrase_cells[-1]
                reg_e = reg_of(live[-1])
                options = [m for m in range(reg_e[0], reg_e[1] + 1) if m % 12 in want]
                if options:
                    last.pitches[-1] = ending_pick(options, last, bars[live[-1]][0])
            end_phrase(phrase_cells)
            prev_phrase, prev_phrase_start = phrase_cells, a0
            written_windows[w[0]] = (live, phrase_cells)
            back = min(keep, len(live)) if own_onsets is None else sum(1 for k in live if choices.get(k) == "theme")
            log.append(f"bar {w[0]}: the theme again, {back} of its bars, then {shape}, ends {ending}")
            continue
        src_phrase = (next((ph for ph in reversed(others) if all(keeps(k, len(ph[i % len(ph)].positions)) for i, k in enumerate(live))), None)
                      if letter == rhythm.AGAIN else None)   # the last whose bars keep within these bars' own onsets (round 138); none: a new phrase
        if src_phrase is not None:                          # an earlier phrase again, the last whose head was not the theme's
            phrase_cells = [again(k, src_phrase[i % len(src_phrase)]) for i, k in enumerate(live)]
            for i, (k, c) in enumerate(zip(live, phrase_cells)):
                choices[k] = "again"
                played[c.key] += 1
                by_key.setdefault(c.key, c)
                note_pair(live, phrase_cells, i)
            end_phrase(phrase_cells)
            prev_phrase, prev_phrase_start = phrase_cells, a0
            written_windows[w[0]] = (live, phrase_cells)
            log.append(f"bar {w[0]}: an earlier phrase again")
            continue
        relation = "first" if prev_phrase is None else draw_shape("relations", {"habit": habit_rel(models)})
        if relation == "first" and prev_phrase is not None:
            relation = "new"
        if letter is not None and relation in ("repeated", "moved up", "moved down"):
            relation = "new"                                # the letters said a new head: the phrase is new, or answers the one before
        shape = draw_shape("contours", {})
        phrase_size = size_of(shape)
        ending = draw_shape("endings", {})
        phrase_cells = []
        if (relation in ("repeated", "moved up", "moved down") and prev_phrase
                and not all(keeps(k, len(prev_phrase[i % len(prev_phrase)].positions)) for i, k in enumerate(live))):
            relation = "new"                                # a bar of the phrase before would not keep within this bar's own onsets (round 138)
        if relation in ("repeated", "moved up", "moved down") and prev_phrase:
            shift = int(round(shift_of(relation))) if relation != "repeated" else 0
            for i, k in enumerate(live):
                src = prev_phrase[i % len(prev_phrase)]
                if shift:
                    src = Cell(src.positions, [m + shift for m in src.pitches], 0, scale)
                    src.entry = (src.entry + shift) % 12
                phrase_cells.append(again(k, src))
                choices[k] = "copy"
                note_pair(live, phrase_cells, i)
        else:
            # the new phrase sits where the shift table puts it against the last (the table counts mean pitches): the line
            # is steered there over the phrase's first third by draw_move's contour aim, not jumped there in one move
            # (FFVI's phrase-start moves are half steps; the jump had made them a quarter)
            reg_a = reg_of(live[0])
            aim0 = float(min(reg_a[1], max(reg_a[0], last_midi + shift_of(relation)))) if prev_phrase is not None else None
            for attempt in range(COPY_TRIES):
                phrase_cells, start_midi = [], aim0
                snapshot = (dict(played), dict(by_key), last_midi, last_move, dict(rhythm_played), rhythm_prev, prev_cell, dict(source), dict(choices), list(on_beat), list(moves_seen),
                            Counter(pairs_played), dict(pair_cells), prev_pair, prev_pair_key, prev_pair_at, Counter(pair_kinds), Counter(source_kinds),
                            {pl: list(v) for pl, v in off_run.items()}, {pl: list(v) for pl, v in clash_run.items()}, list(far_seen))
                group_plan = None
                for i, k in enumerate(live):
                    if i % rhythm.PAIR == 0:                # a new pair: the pair urn (round 40) says the pair before's again, an earlier pair, or new
                        group_plan = None
                        if pair_urn is not None and i + rhythm.PAIR <= len(live):
                            kind_ = pair_urn.choose(rng, SimpleNamespace(key=prev_pair_key) if prev_pair_key else None, pairs_played)
                            pair_keeps = lambda pr: all(keeps(live[i + x], len(pr[x].positions)) for x in range(rhythm.PAIR))   # noqa: E731 -- a pair
                            if kind_ == "same" and prev_pair is not None and pair_keeps(prev_pair):   # comes back where both bars keep (round 138)
                                group_plan = ("pair same", prev_pair, prev_pair_at)
                            elif kind_ == "earlier":
                                pool_ = by_source(k, [(j, pr) for j, pr in pair_cells.items() if j < k and (pr[0].key, pr[1].key) != prev_pair_key and pair_keeps(pr)])
                                if pool_:
                                    j_, pr = _weighted(rng, pool_, [pairs_played.get((pr[0].key, pr[1].key), 1) for _, pr in pool_])
                                    group_plan = ("pair earlier", pr, j_)
                            pair_kinds[group_plan[0][5:] if group_plan else "new"] += 1
                    if group_plan is not None:
                        kind_, pr, j_ = group_plan
                        cell = again(k, pr[i % rhythm.PAIR], kind_.split()[-1])
                        choices[k] = kind_
                        source[k] = j_ + i % rhythm.PAIR if j_ + i % rhythm.PAIR in cells else None
                    elif relation == "answered" and prev_phrase and i < len(prev_phrase) and keeps(k, len(prev_phrase[i].positions)):
                        cell = new_cell(k, prev_phrase[i].positions, shape, start_midi, a0, b0)
                        choices[k] = "answered"
                    else:
                        choice = bar_urn.choose(rng, prev_cell, played)
                        before = k - 1 if k - 1 in cells else None
                        if choice == "same" and prev_cell is not None and not keeps(k, len(prev_cell.positions)):
                            choice = "new"                  # the bar before's cell is not within this bar's own onsets (round 138): a new bar
                        if choice == "same" and prev_cell is not None:
                            cell = again(k, prev_cell, "same")
                            source[k] = source.get(before, before) if before is not None else None
                        elif choice == "earlier":
                            follow = source.get(before)
                            if follow is not None and follow + 1 in cells and follow + 1 < k and keeps(k, len(cells[follow + 1].positions)) and continues():
                                cell = again(k, cells[follow + 1])      # the passage recalled goes on with its next bar
                                source[k] = follow + 1
                            else:
                                pool = by_source(k, [(j, c) for j, c in cells.items() if j < k and (prev_cell is None or c.key != prev_cell.key)
                                                     and keeps(k, len(c.positions))])
                                if pool:
                                    j, c = _weighted(rng, pool, [played.get(c.key, 1) for _, c in pool])
                                    cell = again(k, c)
                                    source[k] = j
                                else:
                                    cell = (new_cell_halves if "half_recall" in models else new_cell)(k, new_rhythm(k), shape, start_midi, a0, b0)
                                    choice = "new"
                        else:
                            cell = (new_cell_halves if "half_recall" in models else new_cell)(k, new_rhythm(k), shape, start_midi, a0, b0)
                        choices[k] = choice
                    if start_midi is None and cell.pitches:
                        start_midi = float(cell.pitches[0])
                    played[cell.key] += 1
                    by_key.setdefault(cell.key, cell)
                    prev_cell = cell
                    phrase_cells.append(cell)
                    note_pair(live, phrase_cells, i)
                if reference is None:
                    break
                notes_ = [(bars[k][0] + p, 0, m) for k, c in zip(live, phrase_cells) for p, m in zip(c.positions, c.pitches)]
                probe = Tune(notes_, a0)
                if not [r for r in reference.matches(probe.rhythm, probe.intervals) if r.get("song") != song.sid]:
                    break
                played, by_key, last_midi, last_move, rhythm_played, rhythm_prev, prev_cell = (Counter(snapshot[0]), dict(snapshot[1]), snapshot[2], snapshot[3], Counter(snapshot[4]), snapshot[5], snapshot[6])
                source, choices = dict(snapshot[7]), dict(snapshot[8])
                on_beat[:] = snapshot[9]
                moves_seen[:] = snapshot[10]
                pairs_played, pair_cells, prev_pair, prev_pair_key, prev_pair_at = Counter(snapshot[11]), dict(snapshot[12]), snapshot[13], snapshot[14], snapshot[15]
                pair_kinds, source_kinds = Counter(snapshot[16]), Counter(snapshot[17])
                for pl in off_run:
                    off_run[pl][:] = snapshot[18][pl]
                    clash_run[pl][:] = snapshot[19][pl]
                far_seen[:] = snapshot[20]
            else:
                log.append(f"phrase at bar {w[0]}: a game's phrase drawn {COPY_TRIES} times running; the last kept")
        # the ending: the phrase's last note onto the drawn degree, where the last bar is a new cell (round 49: a recalled last
        # bar keeps its cell, as FFVI's recalled bars are identical by the word's count; the ending moved onto a recall had
        # made 33 of 76 bent recalls, differing from their source in the last interval alone)
        if ending in DEGREE_PCS and phrase_cells and phrase_cells[-1].pitches and choices.get(live[-1]) in ("new", "answered"):
            want = {(tonic + i) % 12 for i in DEGREE_PCS[ending]}
            last = phrase_cells[-1]
            reg_e = reg_of(live[-1])
            options = [m for m in range(reg_e[0], reg_e[1] + 1) if m % 12 in want]
            if options:
                last.pitches[-1] = min(options, key=lambda m: (abs(m - last.pitches[-1]), m))
                last_midi = float(last.pitches[-1])
        prev_phrase, prev_phrase_start = phrase_cells, a0
        written_windows[w[0]] = (live, phrase_cells)
        if letters is not None and phrase_cells:
            if letter_of(w[0]) == rhythm.THEME:             # a phrase the letters name the theme, written new: the song's theme (the first so
                themes.append(list(phrase_cells))           # named), or the theme stated again where no statement's head kept (round 138)
                theme_bars |= set(live)
            elif letter_of(w[0]) == rhythm.NEW:
                others.append(list(phrase_cells))
        log.append(f"bar {w[0]}: {relation}, {shape}" + (f" {phrase_size:.0f}" if phrase_size is not None else "") + f", ends {ending}, bars {[choices.get(k, '-') for k in live]}")
    if on_beat[1]:
        log.append(f"strong-beat notes on the chord: {on_beat[0]}/{on_beat[1]} ({on_beat[0] / on_beat[1]:.2f}; the song's rate {rate:.2f})")
    if moves_seen[1]:
        log.append(f"repeated notes: {moves_seen[0]}/{moves_seen[1]} ({moves_seen[0] / moves_seen[1]:.2f}; the song's rate {rep_rate:.2f})")
        if far_rate is not None:                            # the tune's far moves against its token song's (round 130)
            log.append(f"moves of a fourth or more: {far_seen[0]}/{moves_seen[1]} ({far_seen[0] / moves_seen[1]:.2f}; the balance's song's tune {far_rate:.2f}), "
                       f"of a third: {far_seen[2]}/{moves_seen[1]} ({far_seen[2] / moves_seen[1]:.2f}; {third_rate or 0.0:.2f}); "
                       f"{far_seen[1]} recalled cells moved to enter by another move (round 130)")
    if moves_drawn:
        log.append("recalls placed (recall_moves): " + ", ".join(f"{'at pitch' if k == '0' else 'with the root' if k == 'root' else k} {v}" for k, v in moves_drawn.most_common()))
    for name, run, rates in (("off the scale", off_run, off_scale), ("a semitone from a sounding part", clash_run, clash_rates)):
        if rates and any(v[1] for v in run.values()):          # the words' shares held (round 93)
            log.append(f"{name}: " + ", ".join(f"{pl} {v[0]}/{v[1]} ({v[0] / v[1]:.2f}; the song's rate {rates[pl]:.2f})" for pl, v in run.items() if v[1]))
    # the notes, with their lengths from the articulation table: the value is the gap to the next note across the bar line (round
    # 140: a bar's last note runs to the next bar's first onset where the tune plays on in it, as the counter's has since round 29
    # and the bass's since round 26, and as the values and tune_sounds words count a gap; at a rest bar the bar line stays). The
    # gap had ended at the bar line: a note before a bar that opens with a rest stopped there, where the game's is held to the
    # next note (the game's Terra sounds 0.24 of its tune's notes past their bar's end, the written one none)
    notes, onward = [], 0
    length_run, lengths_rng = {}, lengths_rng or random.Random(f"{role}:note lengths")
    for k in sorted(cells):
        a, b, _ = bars[k]
        cell = cells[k]
        after = cells.get(k + 1)
        nxt = bars[k + 1][0] + after.positions[0] if after is not None and after.positions and k + 1 < len(bars) else b
        for i, (p, m) in enumerate(zip(cell.positions, cell.pitches)):
            t = a + p
            until = a + cell.positions[i + 1] if i + 1 < len(cell.positions) else nxt
            onward += until > b + rhythm.NEAR
            gap = until - t
            if gap <= rhythm.NEAR:
                continue
            value = str(rhythm.position(gap, song.division))
            held = models["values"].draw((role, value, articulation), rng) if "values" in models else "held"
            share = None
            if lengths:                                     # held or detached as its token song's tune is at the gap (round 141); the pooled
                held, share = own_length(lengths, gap, length_run, lengths_rng, tune_sounds)   # draw is made all the same, so the stream stands
            notes.append((t, t + sounded(gap, tune_sounds, held, shortest, share), float(m)))   # the song's own shares (tune_sounds, round 98), no
                                                            # note under its token song's shortest usual one (round 136)
    if onward:
        log.append(f"{onward} bars' last notes measured to the next bar's first onset, past the bar line (round 140)")
    if lengths and length_run:
        log.append(length_log(lengths, length_run))
    if own_new[0]:                                          # the tune's bars by its part of the form's own onsets (round 138)
        log.append(f"new bars drawn within the balance's song's own onsets for their part of the form (round 138): {own_new[0] - own_new[2]} of {own_new[0]}"
                   + (f", {own_new[1]} among the table's bars that fit" if own_new[1] else "") + "; a bar or a half that comes back and a phrase answered keep within them too")
    if half_kinds:
        c = Counter(kd for ks in half_kinds.values() for kd in ks)
        log.append("halves (half_recall): " + ", ".join(f"{kd} {c[kd]}" for kd in ("same", "earlier", "new", "rest") if c[kd]) + f" over {len(half_kinds)} new bars")
    if pair_kinds:
        log.append("pairs (pair_recall): " + ", ".join(f"{kd} {pair_kinds[kd]}" for kd in tables.RECALL if pair_kinds[kd]) + f" over {sum(pair_kinds.values())} pairs drawn"
                   + ("; echoes point (recall_sources): " + ", ".join(f"{src} {source_kinds[src]}" for src in rhythm.RECALL_SOURCES if source_kinds[src]) if source_kinds else ""))
    return notes, figures, log


def habit_rel(models: dict) -> str:
    """The relation table's habit value a song draws under: its commonest, where it has one."""
    t = models["relations"].table if hasattr(models["relations"], "table") else models["relations"]
    habits = Counter()
    for c, votes in t.votes.items():
        if len(c) == len(t.conditionings) and "habit" in t.conditionings:
            habits[c[t.conditionings.index("habit")]] += sum(votes.values())
    return habits.most_common(1)[0][0] if habits else "mixed"


def fits(figure: str, song: rhythm.Song, known: set, cap: int) -> bool:
    """Whether a new figure may be written into the song: a bar some song played, on the song's grid, no denser than cap (Manner refines it)."""
    return figure != figures_mod.REST and figure in known and figures_mod.on_grid(figure, song.division) and len(rhythm._tokens(figure)) <= cap
