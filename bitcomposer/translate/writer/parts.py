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

from . import figures as figures_mod, upper as upper_mod, tune as tune_mod   # noqa: E402  the package's other sections


LOCK_DRUMS = 2 / 3                    # the share of a bar's shared hits a drum group must strike (the readings' two in three)


def locked(figure: str, lock, share: float = 1.0) -> bool:
    """Whether a figure strikes `share` of the positions in lock[0] (all, by default) and none in the beats of lock[1]."""
    if not lock:
        return True
    must, rests = lock
    positions = {Fraction(t.partition(":")[0]) for t in rhythm._tokens(figure)}
    struck = len(must & positions)
    return struck >= share * len(must) - 1e-9 and not any(math.floor(p) in rests for p in positions)


FORM_PERIOD = 4                       # bars: the pattern a free-written part repeats through a part of the form


def form_spans(song: rhythm.Song, own: list) -> list[tuple]:
    """The spans of a part written with no original to follow: the form's
    parts, each a span with a FORM_PERIOD-bar pattern (shorter parts their
    length), a part that repeats an earlier one of the same length copying
    its figures (copy_of: the earlier span's first bar); bars in no part
    their own spans. [(start, length, period, copy_of)]."""
    index = {num: k for k, num in enumerate(song.numbers)}
    out, covered, starts = [], set(), {}
    for i, (bar, n, *rest) in enumerate(song.parts):
        ks = [index[num] for num in range(bar, bar + n) if num in index]
        if not ks:
            continue
        start, length = ks[0], len(ks)
        of = rest[0] if rest else None
        copy_of = starts.get(of) if of is not None and starts.get(of, (None, None))[1] == length else None
        starts[i] = (start, length)
        out.append((start, length, min(FORM_PERIOD, length), copy_of[0] if copy_of else None))
        covered |= set(ks)
    for k in range(len(own)):
        if k not in covered:
            out.append((k, 1, 1, None))
    return sorted(out)


THIN = 0.05                           # the band's energy (against its median) under which a free-written pitched part sits a bar out
BREAKDOWN = 0.5                       # under this share of the median the band is thin: the part thins with it and does not lock to it


def thinned(env: tuple, ratio: float) -> tuple:
    """A free envelope scaled to the band's energy in the bar: the strikes allowed shrink with the band, to one
    where the band is nearly gone (under THIN, the caller rests the bar)."""
    low, high, downbeat, meter = env
    r = min(1.0, max(0.0, ratio))
    return (max(1, round(low * r)), max(1, round(high * r)), downbeat, meter)


def _free_figures(song: rhythm.Song, role: str, model: tables.Cache, manner, own: list, bars: list, habit: str,
                  rng: random.Random, hold=(), lock=None, envelope_of=None, within_of=None, lock_share: float = 1.0,
                  energy: list | None = None, extra_values: dict | None = None) -> list[str]:
    """The figures written for a part with no original to follow (the
    module, phase 4): bar by bar from the song's own mixture, whose recall
    shares carry the games' rate of repeating and returning, each bar in
    the manner, the habit's envelope and the band's lock; a part of the
    form that repeats an earlier one copies its figures; the bars the old
    part rests in rest (the arrangement is not this slice's); the song's
    moments and stops (`hold`) keep the old bar; `energy`, the band's
    energy a bar against its median, thins the part where the band thins
    (a breakdown) and rests it where the band is nearly gone (THIN)."""
    lock = lock or {}
    envelope_of = envelope_of or figures_mod.envelope
    within_of = within_of or figures_mod.within
    meters = [max(1, round(b - a)) for a, b, _ in bars]
    figures, played, previous = [figures_mod.REST] * len(bars), Counter(), None
    periods = getattr(song, "periods", {}).get(role, {})   # the part's period inside a part of the form: a held bar plays the bar a lag before
    for start, length, _, copy_of in form_spans(song, own):
        for i in range(length):
            k = start + i
            if own[k] == figures_mod.REST or (energy is not None and k < len(energy) and energy[k] < THIN):
                figures[k] = figures_mod.REST
                continue
            if copy_of is not None and figures[copy_of + i] != figures_mod.REST:
                figures[k] = figures[copy_of + i]
            elif k in periods and 0 <= k - periods[k] < k and figures[k - periods[k]] != figures_mod.REST:
                figures[k] = figures[k - periods[k]]
            elif k in hold:
                figures[k] = own[k]
            else:
                env = envelope_of(own[k], meters[k])
                thin = energy is not None and k < len(energy) and energy[k] < BREAKDOWN
                if thin:
                    env = thinned(env, energy[k])
                bar_lock = None if thin else lock.get(k)        # in a breakdown the band's hits are not the band: no lock
                values = {"part": role, "meter": meters[k], "previous": previous or rhythm.START, "habit": habit, "feel": rhythm.song_feel(song), "tempo": rhythm.band(song.bpm), **(extra_values or {})}
                unit = tables.Unit(song.sid, song.game, "", values)
                # the filters, loosened in turn where nothing passes: the manner, the envelope and the lock; then
                # without the lock (the band asks more strikes than the habit: the part keeps its density and locks
                # where it can); then without the envelope; then the manner alone. Never the song's own bar: a
                # free-written part copies nothing of the part it replaces.
                ladder = [lambda f, _l=bar_lock, _e=env: manner.fits(f) and within_of(f, _e) and locked(f, _l, lock_share),
                          lambda f, _e=env: manner.fits(f) and within_of(f, _e),
                          lambda f, _l=bar_lock: manner.fits(f) and locked(f, _l, lock_share),
                          manner.fits]
                figure = None
                for fit in ladder:
                    candidate = model.draw(unit, previous, played, rng, keep=fit)
                    for _ in range(figures_mod.TRIES):
                        if fit(candidate):
                            figure = candidate
                            break
                        candidate = model.table.draw(model.table.context(unit), rng, values, floored=False, floor_k=model.table.chain_floor)
                    if figure is not None:
                        break
                figures[k] = figure if figure is not None else last_resort(manner, model, unit, values, rng)
            played[figures[k]] += 1
            previous = figures[k]
    for start, length, copy_of in getattr(song, "copies", {}).get(role, []):   # the band back with the theme: the part's own bars again
        for i in range(length):
            k, src = start + i, copy_of + i
            if k < len(figures) and src < len(figures) and own[k] != figures_mod.REST and figures[src] != figures_mod.REST:
                figures[k] = figures[src]
    return figures


def last_resort(manner, model: tables.Cache, unit: tables.Unit, values: dict, rng: random.Random) -> str:
    """The figure for a bar no draw fits: on a kit (FreeManner with pieces),
    any bar the table knows that the kit can play, evenly (the vocabulary's
    even share, kept to the kit: a bar the plan has the kit in is never
    silent for want of a draw, round 58); else the table's own draw."""
    kit = getattr(manner, "kit", None)
    if kit is not None:
        fits = [f for f in sorted(manner.known) if f != figures_mod.REST and manner.fits(f)]
        if fits:
            return rng.choice(fits)
    return model.table.draw(model.table.context(unit), rng, values, floored=False, floor_k=model.table.chain_floor)


def _figures(song: rhythm.Song, role: str, model: tables.Cache, manner, own: list, bars: list, habit: str,
             rng: random.Random, hold=(), lock=None, chord_at=None, reuse: float = 0.0,
             envelope_of=None, within_of=None, lock_share: float = 1.0) -> list[str]:
    """The figures written for a part, one a bar (the module): drawn as the
    song's own mixture, in its manner, each bar's envelope and lock, a
    pattern a span, the song's moments its own; `chord_at` and `reuse` let
    a bar on a chord its span had take that bar's figure again (the bass)."""
    lock = lock or {}
    envelope_of = envelope_of or figures_mod.envelope
    within_of = within_of or figures_mod.within
    meters = [max(1, round(b - a)) for a, b, _ in bars]
    state = {"previous": None, "played": Counter()}

    def draw(env, keep=None, fallback: str = "0:R", at: int | None = None) -> str:
        """One new figure from the song's mixture, in its manner, the bar's
        envelope and its lock (and passing `keep`), the chain and the urn
        moved on. Nothing passing in TRIES draws: one in the manner, envelope
        and lock alone, else the fallback (the song's own bar, where the
        caller gives it)."""
        previous = state["previous"]
        meter = env[-1] if env[-1] else song.meter
        fit = lambda f: manner.fits(f) and within_of(f, env) and locked(f, lock.get(at), lock_share)   # noqa: E731
        full = lambda f: fit(f) and (keep is None or keep(f))   # noqa: E731
        values = {"part": role, "meter": meter, "previous": previous or rhythm.START, "habit": habit, "feel": rhythm.song_feel(song), "tempo": rhythm.band(song.bpm)}
        unit = tables.Unit(song.sid, song.game, "", values)
        figure = model.draw(unit, None if previous == figures_mod.REST else previous, state["played"], rng, keep=full)
        nearly = None
        for _ in range(figures_mod.TRIES):                              # the urn or the floor may still hand back what is refused
            if full(figure):
                return figure
            if nearly is None and fit(figure):
                nearly = figure
            figure = model.table.draw(model.table.context(unit), rng, values, floored=False, floor_k=model.table.chain_floor)
        return nearly or fallback

    figures, patterns = [figures_mod.REST] * len(bars), []
    for start, length, period in figures_mod.spans([figures_mod.rhythm_of(f) for f in own]):
        if length == 1:
            if own[start] != figures_mod.REST:
                last = figures_mod.rhythm_of(figures[start - 1]) if start else None    # the song changes here: so does the written bar
                figures[start] = draw(envelope_of(own[start], meters[start]), keep=lambda f: figures_mod.rhythm_of(f) != last, fallback=own[start], at=start)
                state["played"][figures[start]] += 1
            state["previous"] = figures[start]
            continue
        exact = all(own[j] == own[j - period] for j in range(start + period, start + length))
        before = patterns[-1] if patterns else []
        earlier = [x for x in patterns[:-1] if x != before]
        if earlier and rng.random() < figures_mod.EARLIER:
            pattern = rng.choice(earlier)
        else:
            pattern = []
            for k in range(period):
                avoid = {figures_mod.rhythm_of(f) for f in before + pattern}
                pattern.append(draw(envelope_of(own[start + k], meters[start + k]), keep=lambda f: figures_mod.rhythm_of(f) not in avoid, fallback=own[start + k], at=start + k))
                state["previous"] = pattern[-1]
        patterns.append(pattern)
        seen = {}                                           # the span's chords -> the figure written on each
        for i in range(length):
            base = pattern[i % len(pattern)]
            chord = chord_at(start + i) if chord_at else None
            if own[start + i] == figures_mod.REST:
                figure = figures_mod.REST
            elif exact and locked(base, lock.get(start + i), lock_share):
                figure = base
            elif chord is not None and chord in seen and figures_mod.rhythm_of(seen[chord]) == figures_mod.rhythm_of(base) and locked(seen[chord], lock.get(start + i), lock_share) and rng.random() < reuse:
                figure = seen[chord]                        # the same chord again: the same figure, as the readings' basses do
            else:
                want = figures_mod.rhythm_of(base)
                figure = draw(envelope_of(own[start + i], meters[start + i]), keep=lambda f: figures_mod.rhythm_of(f) == want, fallback=own[start + i], at=start + i)
                if figures_mod.rhythm_of(figure) != want and locked(base, lock.get(start + i), lock_share):
                    figure = base
            if chord is not None and figure != figures_mod.REST:
                seen.setdefault(chord, figure)
            figures[start + i] = figure
            if figure != figures_mod.REST:
                state["played"][figure] += 1
            state["previous"] = figure
    for k in hold:                                          # the song's moments: its own bar
        if 0 <= k < len(figures) and own[k] != figures_mod.REST:
            figures[k] = own[k]
    return figures


def drums(song: rhythm.Song, models: dict, rng: random.Random, hold=(), locks=None, habit: str | None = None,
          free: bool = False, plays: list | None = None, kit_value: str | None = None) -> tuple[list[tuple[float, str]], list[str]]:
    """The drums written for the song, a group of pieces at a time (the
    module): `models` maps a group (a tuple of letters, rhythm.DRUM_GROUPS)
    to its Cache (a group of every letter: the whole kit, its table's part
    "drums"); `locks` a group to its lock; `hold` as bass(). `free`: no
    original to follow (FreeManner, free_drum_envelope), the `habit` given
    (drawn from a pack's table: the kit's, or {group: its own}) and the kit
    the song's pieces; with `plays` (a planned song's bars) a group may
    also draw a rested bar, at its table's rate; `kit_value` (the letters
    of the pieces the song's kit strikes, kit_pieces) conditions the draw
    and narrows the kit to them. Returns the hits (start in beats, piece
    letter) and the merged figures."""
    locks = locks or {}
    bars = [(a, b, struck) for _, a, b, struck in rhythm.all_bars_of(song, R.DRUMS)]
    whole = [rhythm.drum_figure(struck, song) if struck else figures_mod.REST for a, _, struck in bars]
    kit = {rhythm.LETTERS.get(piece, "o") for piece in song.pieces.values() if piece and piece != "none"}
    if kit_value:                                           # the pieces the song's kit strikes (kit_pieces, round 58): the manner keeps a figure
        kit &= set(kit_value)                               # on them alone, so a bar drawn from another kit's songs is one this kit can play
    merged = [[] for _ in bars]
    by_group = {}
    part_of = lambda letters: R.DRUMS if set(letters) >= set(rhythm.LETTERS.values()) else "drums-" + "".join(letters)   # noqa: E731
    for letters, model in models.items():
        own = plays_as_own(plays, bars) if plays is not None else [rhythm.drum_group(f, letters) for f in whole]
        if all(f == figures_mod.REST for f in own) and not (free and kit & set(letters)):
            continue
        if free:
            manner = figures_mod.FreeManner(model.table.vocabulary, kit & set(letters), song.division, rests=plays is not None)
            group_habit = (habit.get(letters) if isinstance(habit, dict) else habit) or "medium mixed"
            envelope_of = figures_mod.free_drum_envelope(kit & set(letters), figures_mod.group_caps(habit))
        else:
            manner = figures_mod.DrumManner(None, model.table.vocabulary, figures=[f for f in own if f != figures_mod.REST])
            mine = [u for u in rhythm.drum_group_units([song], letters)]
            group_habit = habit or (mine[0].values["habit"] if mine else "medium mixed")
            envelope_of = figures_mod.drum_envelope
        if free:
            figures = _free_figures(song, part_of(letters), model, manner, own, bars, group_habit, rng, hold,
                                    locks.get(letters), envelope_of=envelope_of, within_of=figures_mod.drum_within, lock_share=LOCK_DRUMS,
                                    extra_values={"kit": kit_value} if kit_value else None)   # the kit's pieces (round 58)
        else:
            figures = _figures(song, part_of(letters), model, manner, own, bars, group_habit, rng, hold, locks.get(letters),
                               envelope_of=envelope_of, within_of=figures_mod.drum_within, lock_share=LOCK_DRUMS)
        by_group[letters] = figures
        for k, f in enumerate(figures):
            merged[k] += [(Fraction(t.partition(":")[0]), t.partition(":")[2]) for t in rhythm._tokens(f)]
    if free and plays is not None and by_group:
        # a bar the plan has the drums in never rests whole: where every group drew a rest, the kit's main group (the
        # one playing the most bars) plays a figure of its own there, drawn without the rest
        main = max(by_group, key=lambda g: sum(1 for f in by_group[g] if f != figures_mod.REST))
        model = models[main]
        manner = figures_mod.FreeManner(model.table.vocabulary, kit & set(main), song.division, rests=False)
        group_habit = (habit.get(main) if isinstance(habit, dict) else habit) or "medium mixed"
        for k, (a, b, _) in enumerate(bars):
            if not (k < len(plays) and plays[k]) or merged[k]:
                continue
            before = by_group[main][k - 1] if k else figures_mod.REST
            values = {"part": part_of(main), "meter": max(1, round(b - a)), "previous": before if before != figures_mod.REST else rhythm.START, "habit": group_habit, **({"kit": kit_value} if kit_value else {}),
                      "feel": rhythm.song_feel(song), "tempo": rhythm.band(song.bpm)}
            unit = tables.Unit(song.sid, song.game, "", values)
            env = figures_mod.free_drum_envelope(kit & set(main))(None, values["meter"])
            f = None
            for _ in range(figures_mod.TRIES):
                f = model.table.draw(model.table.context(unit), rng, values, floored=False, floor_k=model.table.chain_floor)
                if manner.fits(f) and figures_mod.drum_within(f, env):
                    break
                f = None
            if f is None:                                   # nothing drawn fits the kit: any bar the kit can play (round 58)
                f = last_resort(manner, model, unit, values, rng)
            if f != figures_mod.REST:
                by_group[main][k] = f
                merged[k] += [(Fraction(t.partition(":")[0]), t.partition(":")[2]) for t in rhythm._tokens(f)]
    figures = [" ".join(f"{p}:{x}" for p, x in sorted(set(tokens))) or figures_mod.REST for tokens in merged]
    hits = []
    for (a, b, _), figure in zip(bars, figures):
        for t in rhythm._tokens(figure):
            at, _, letter = t.partition(":")
            if a + float(Fraction(at)) < b:
                hits.append((a + float(Fraction(at)), letter))
    return hits, figures


def plays_as_own(plays, bars: list) -> list:
    """A part's own bars for a planned song: "0" where the plan has it play, REST where it rests."""
    return ["0" if (k < len(plays) and plays[k]) else figures_mod.REST for k in range(len(bars))]


def bass(song: rhythm.Song, model: tables.Cache, rng: random.Random, habit: str | None = None,
         key: tuple | None = None, hold=(), lock=None, free: bool = False, energy: list | None = None,
         plays: list | None = None, register: int | None = None, sounds=None,
         figures: list | None = None, shared: dict | None = None, kind: str | None = None,
         models: dict | None = None, lock_share: float = 1.0, ceiling: int | None = None) -> tuple[list[tuple[float, float, float]], list[str]]:
    """The bass written for the song: its notes (start, end in beats, midi)
    and the figures drawn, one a bar; the bars in `hold` (indices among the
    song's bars) keep the song's own figure; `lock` maps a bar's index to
    (positions a figure must strike, beats it must leave), the song's own
    locking to the band. `free`: no original to follow (FreeManner,
    free_envelope by the habit, which the caller then gives). `plays`: a
    planned song's bars the part plays in (no original: the bars the plan
    has it play, playing anything), with `register` (the midi floor) and
    `sounds` (the share of its gap a note sounds) given instead of read."""
    lock = lock or {}
    own = song.notes.get(R.BASS, [])
    if habit is None:
        mine = rhythm.bass_units([song])
        habit = mine[0].values["habit"] if mine else "medium roots no-octaves"
    manner = figures_mod.FreeManner(model.table.vocabulary, division=song.division) if free else figures_mod.Manner(song, R.BASS, model.table.vocabulary)
    pitched = sorted(n[2] for n in own if not math.isnan(n[2]))
    low = register if register is not None else round(pitched[int(figures_mod.LOW * (len(pitched) - 1))]) if pitched else 36
    high = ceiling if ceiling is not None else low + figures_mod.REACH      # the register's ceiling: where the game plays the sample (round 34)
    sounds = sounds if sounds is not None else sounded(own)
    tonic, mode = key if key else (0, "major")
    scale = {(tonic + i) % 12 for i in harmony.MODES["major" if mode == "major" else "natural_minor"]}
    bars = [(a, b, struck) for _, a, b, struck in rhythm.all_bars_of(song, R.BASS)]
    own = plays_as_own(plays, bars) if plays is not None else [rhythm.figure(struck, a, song) if struck else figures_mod.REST for a, _, struck in bars]

    def chord_at(k):
        c = rhythm._chord_at(song.chords, bars[k][0])
        return (c.root, c.shape) if c is not None and c.root is not None and c.fit >= FIT else None

    words = habit.split()
    if figures is not None:                                 # a second line's figures given (the second_figures table, under the line's own)
        figures = [f if o != figures_mod.REST else figures_mod.REST for f, o in zip(figures, own)]
    elif free:
        figures = _free_figures(song, R.BASS, model, manner, own, bars, habit, rng, hold, lock, envelope_of=figures_mod.free_envelope(habit), energy=energy,
                                lock_share=lock_share)
    else:
        figures = _figures(song, R.BASS, model, manner, own, bars, habit, rng, hold, lock,
                           chord_at=chord_at, reuse=figures_mod.REUSE.get(words[1] if len(words) > 1 else "", 0.5))
    notes, last_root, previous = [], tonic, None
    beside = kind in figures_mod.VOICE_KINDS and shared is not None and models is not None and "voice_intervals" in models and "voice_moves" in models
    prev_steps, prev_midi, last_with = rhythm.START, None, None   # a second voice following the line: its last interval with it, its last note
    for k, ((a, b, _), figure) in enumerate(zip(bars, figures)):
        new, last_root, previous = realize(figure, a, b, song, low, sounds, scale, last_root, previous, runs_to=tune_mod.first_onset(figures, bars, k + 1), high=high)
        if shared is not None and not beside:               # the line: its notes for the voice beside it
            for start, _, midi in new:
                shared[("line", (k, rhythm.position(start - a, song.division)))] = midi
        elif beside:                                        # the second voice: with the line, the note both words agree on; alone, its own
            repitched = []                                  # move (voice_intervals, voice_moves, counted on the bass too: FFVI's second bass
            for start, end, midi in new:                    # plays the line's pitch class at 78 % of their shared onsets; drawn apart, 31 %)
                p = rhythm.position(start - a, song.division)
                ref = shared.get(("line", (k, p)))
                if ref is not None:
                    moved = (tune_mod.scale_index(int(round(ref)), scale) - tune_mod.scale_index(int(round(last_with)), scale)) if last_with is not None else 0
                    target, steps = tune_mod.beside_pitch(models, R.BASS, kind, scale, rng, ref, prev_steps, prev_midi, moved)
                    if target is not None:
                        prev_steps, last_with = str(steps), ref
                else:
                    target, _ = tune_mod.beside_pitch(models, R.BASS, kind, scale, rng, None, prev_steps, prev_midi, 0)
                if target is not None:
                    midi = float(upper_mod.in_register(target, (low, high)))
                prev_midi = midi
                repitched.append((start, end, midi))
            new = repitched
            previous = new[-1][2] if new else previous
        notes += new
    return notes, figures


def place(pc: int, low: int, previous: float | None, octave_up: bool = False, high: int | None = None) -> int:
    """The midi note of a pitch class in the register: the octave nearest the
    note before (the lower when as near), the lowest with no note before;
    an octave up (r) is the lowest placing raised an octave. `high`: the
    register's ceiling (the range the game plays the bass's sample in, round
    34); the floor plus REACH without one."""
    bottom = low + (pc - low) % 12
    if octave_up:
        return bottom + 12 if high is None or bottom + 12 <= high else bottom   # no room for the octave: the plain placing
    if previous is None:
        return bottom
    options = [m for m in range(bottom, (high if high is not None else low + figures_mod.REACH) + 1, 12)] or [bottom]
    return min(options, key=lambda m: (abs(m - previous), m))


def passing(previous: float | None, toward: int | None, scale: set, low: int, root: int) -> int:
    """A passing tone: a scale step from the note before, toward the next
    note where there is one (a semitone where the scale has no step that
    way), else on in the line's last direction; the step above the root
    where nothing came before."""
    if previous is None:
        return place(tone(root, "", "+", scale), low, None)
    direction = 1 if toward is None or toward >= previous else -1
    for d in (1, 2):
        m = round(previous) + direction * d
        if m % 12 in scale:
            return m
    return round(previous) + direction


def realize(figure: str, a: float, b: float, song: rhythm.Song, low: int, sounds, scale: set,
            last_root: int, previous: float | None = None, runs_to: float | None = None, high: int | None = None) -> tuple[list, int, float | None]:
    """A figure's tokens as notes in the bar [a, b) (see the module); returns
    them, the last chord root used and the last note's midi."""
    tokens = [(Fraction(t.partition(":")[0]), t.partition(":")[2]) for t in rhythm._tokens(figure)]
    chords = []
    for p, _ in tokens:
        c = rhythm._chord_at(song.chords, a + float(p))
        if c is not None and c.root is not None and c.fit >= FIT:
            last_root, shape = c.root, c.shape
        else:
            shape = ""
        chords.append((last_root, shape))
    out, direction = [], 1
    for i, (p, mark) in enumerate(tokens):
        start = a + float(p)
        until = a + float(tokens[i + 1][0]) if i + 1 < len(tokens) else (runs_to if runs_to is not None and runs_to > b - rhythm.NEAR else b)
        if until <= start:
            continue
        root, shape = chords[i]
        if mark == "+":
            toward = None
            for j in range(i + 1, len(tokens)):                 # the next note of the bar that is not itself passing
                if tokens[j][1] != "+":
                    toward = place(tone(chords[j][0], chords[j][1], tokens[j][1], scale), low, previous, tokens[j][1] == "r", high=high)
                    break
            if toward is None and previous is not None:
                toward = round(previous) + direction * 2
            midi = passing(previous, toward, scale, low, root)
            if high is not None and not low <= midi <= high:        # a run of passing tones turns at the register's edge instead of
                direction = -direction                              # climbing out of where the game plays the sample (round 34: a bass
                midi = upper_mod.in_register(midi, (low, high))               # of bars all "+" had walked from 42 to 79 on a 32-40 sample)
        else:
            midi = place(tone(root, shape, mark, scale), low, previous, mark == "r", high=high)
        if previous is not None and midi != previous:
            direction = 1 if midi > previous else -1
        out.append((start, start + (until - start) * tune_mod.share_at(sounds, until - start), float(midi)))
        previous = float(midi)
    return out, last_root, previous


def tone(root: int, shape: str, mark: str, scale: set) -> int:
    """The pitch class a figure's mark names in a chord (the module)."""
    ivs = harmony.SHAPES.get(shape, harmony.SHAPES[""])
    pick = lambda options, default: next((i for i in options if i in ivs), default)   # noqa: E731
    if mark == "3":
        i = pick((3, 4), 4)
    elif mark == "5":
        i = pick((7, 6, 8), 7)
    elif mark == "7":
        i = pick((10, 11), 10)
    elif mark == "s":
        i = pick((5, 2), 5)
    elif mark == "+":
        i = 2 if (root + 2) % 12 in scale else 10 if (root + 10) % 12 in scale else 2
    else:                                                   # R, r, ?
        i = 0
    return (root + i) % 12


def sounded(notes) -> float:
    """The share of its gap to the next note a part's note sounds, the median over the part (within SOUNDS)."""
    share = rhythm.sounded_share(notes)
    return min(figures_mod.SOUNDS[1], max(figures_mod.SOUNDS[0], share)) if share is not None else 0.8
