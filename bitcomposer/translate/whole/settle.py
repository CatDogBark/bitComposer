"""The chord parts' lines and voices settled once every part is written, and a tune or a counter-line taken with a
chord that leaves the key (rounds 158 to 171 of docs/idiom/phase-4-writing.md). Moved out of plan.py as they stood:
plan.write calls settle_chord_parts last and follow_chords as each line is written. What each pass holds a part to
rides the balance token and is read in plan.py (the token's words) into the Plan these take."""
from __future__ import annotations
import math
import random
from collections import Counter

from .. import harmony, rhythm, vocab, writer
from .. import roles as R
from .plan import NEAR, Plan, STEP_MARGIN, WHOLE_SONG, _draw, follow_pair, relation_stretches, relation_word, stretch_spans   # noqa: E402  the plan's own names: the Plan, its tolerances, the relation words' reading


HEAR_REACH = 6                        # semitones either way a voice's note may move off a semitone with its own part (a tritone)


def _on_chord(plan: Plan, bar: int, midi: int) -> bool:
    """Whether a pitch is a tone of the plan's chord in a bar; False in a bar without one."""
    c = plan.chords[bar] if 0 <= bar < len(plan.chords) else None
    return c is not None and c[0] is not None and vocab.tone_of(int(round(midi)) % 12, c[0], c[1]) != "other"


def _repeats_follow(plan: Plan, old: list, new: list, meter: int) -> int:
    """A part of the form that played an earlier part again note for note plays that part's moved notes too: where a
    note of `old` in a repeating part had the pitch of the note at the same place and voice of the part it repeats,
    its place in `new` takes that note's new pitch. Returns the notes set."""
    index = {(round(n[0], 3), n[3]): i for i, n in enumerate(old)}
    done = 0
    for bar, n_bars, of, _ in plan.parts:
        if of is None:
            continue
        shift = (bar - plan.parts[of][0]) * meter
        for i, n in enumerate(old):
            if not (bar * meter - NEAR <= n[0] < (bar + n_bars) * meter - NEAR):
                continue
            j = index.get((round(n[0] - shift, 3), n[3]))
            if j is not None and int(round(old[j][2])) == int(round(n[2])) and new[i][2] != new[j][2]:
                new[i] = new[i][:2] + (new[j][2],) + tuple(new[i][3:])
                done += 1
    return done


TURNS_STREAM = "accpatch:D3"          # the turns' stream (with the seed and the part): the one the round was heard on, as a pass over written
                                      # songs before it was built; another name deals other bars to each turn


def _bar_places(notes: list, v: int, meter: int) -> dict:
    """A voice's notes by bar: {bar: [(its place in twelfths of a beat, its index in `notes`)], in the bar's order}."""
    by = {}
    for i, n in enumerate(notes):
        if n[3] == v:
            k = int((n[0] + NEAR) // meter)
            by.setdefault(k, []).append((round((n[0] - k * meter) * 12), i))
    return {k: sorted(x) for k, x in by.items()}


def follows_own_line(plan: Plan, role: str, v: int, bars: int) -> set:
    """The bars in which a part's voice `v` doubles its own part's line, runs parallel to it or is struck with it by its
    token's relation word (rounds 90 and 107): there a note of it moves with the line's note it is struck with."""
    word = relation_word(plan, role, v)
    return {k for kind, target, _, a, b in (stretch_spans(relation_stretches(word), bars) if word else [])
            if kind in ("double", "parallel", "with") and (target == ("line",) or target == role) for k in range(a, b)}


def hold_pulse(plan: Plan, meter: int, role: str, notes: list, bars: int) -> tuple:
    """A moving chord line held to its token song's line by its place in the beat (round 161). The step profile holds
    the line's moves in the order they come (round 117), and of a line that is two kinds of note in turn it says
    little: Johnny C. Bad's piano steps up and back on the beat and its half over one note between them, which reads
    as a leap on 0.65 of its moves, and the written lines on its token leaped as often and anywhere (of their notes
    off the pulse 0.47 were their bar's one pitch, the game's 0.73; of their moves on the pulse 0.49 were a step or
    less, the game's 0.93). Here, once every part is written, a line with the token's `pulse=` word
    (`plan.line_pulse`) is taken as its two lines, on the token's grid:
    the notes on the pulse, in time order, are held to the token's step profile as hold_line_steps holds the whole
    line: a move whose class, the move counted, is over its share by STEP_MARGIN gives way to the class most under
    its own, "same" playing the on-pulse note before again and "step" the tone of the bar's chord within a whole tone
    of it (the scale's where the chord has none), a leap never forced;
    the notes off the pulse are held to the pedal: each bar with two or more has one pedal pitch, its own where it
    has one (the pitch it strikes most off the pulse, twice or more, where that is a tone of the bar's chord or half
    the bar's off-pulse notes), else the bar before's where that keeps the token's carry and is a tone of this bar's
    chord, else the one of its off-pulse pitches on the chord it strikes most (not the one its on-pulse notes play
    most, where another serves; the chord's tone nearest where none is on it);
    and a note off the pedal moves to it while the share on it, the note counted off it, would be under the token's
    by STEP_MARGIN. A bar's own pedal is never traded for another.
    Nothing is drawn. A note of a voice beside the line that is struck with a moved line note, in a bar where the
    voice follows its own part's line (follows_own_line) or sounds it in octaves, moves as far, and on to the nearest
    tone of the scale where that leaves it; a part of the form that repeats another still does. Returns (the notes, a
    log line or "")."""
    word = plan.line_pulse.get(role)
    if not word or plan.line_turns.get(role):               # a block line is laid out by its turns (round 160)
        return notes, ""
    grid, pedal_share, carry_share, profile = word
    old, new = list(notes), list(notes)
    scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
    rows = _bar_places(old, 0, meter)
    line = [int(round(old[i][2])) for row in rows.values() for _, i in row]
    if len(line) < 2:
        return notes, ""
    low, high = min(line), max(line)
    pitch = lambda i: int(round(new[i][2]))                 # noqa: E731
    chord_pcs = lambda k: ({(plan.chords[k][0] + x) % 12 for x in harmony.SHAPES.get(plan.chords[k][1], harmony.SHAPES[""])}   # noqa: E731
                           if 0 <= k < len(plan.chords) and plan.chords[k] is not None and plan.chords[k][0] is not None else set())

    def put(i, midi):
        new[i] = new[i][:2] + (float(midi),) + tuple(new[i][3:])

    stepped = 0
    if profile:                                             # the notes on the pulse, as a line of their own
        counts, before = Counter(), None
        for k in sorted(rows):
            for at, i in rows[k]:
                if at % grid:
                    continue
                midi = pitch(i)
                if before is not None:
                    cls = rhythm.step_class(midi - before)
                    total = sum(counts.values())
                    if (counts[cls] + 1) / (total + 1) > profile.get(cls, 0.0) + STEP_MARGIN:
                        room = {c: profile.get(c, 0.0) - counts[c] / (total + 1) for c in rhythm.STEP_CLASSES if c != cls}
                        best = max(room, key=lambda c: (room[c], c == "same"))
                        if room[best] > 0 and best != "leap":
                            near = [before] if best == "same" else [before + d for d in (1, -1, 2, -2) if low <= before + d <= high]
                            pcs = chord_pcs(k)
                            to = next((m for m in near if m % 12 in pcs), None) or next((m for m in near if m % 12 in scale), None) or (near[0] if near else None)
                            if best == "same":
                                to = before
                            if to is not None and to != midi:
                                put(i, to)
                                midi, stepped = to, stepped + 1
                            cls = rhythm.step_class(midi - before)
                    counts[cls] += 1
                before = midi
    pedalled = carried = pairs = on_pedal = seen = 0
    if pedal_share is not None:                             # the notes off the pulse, on the bar's pedal
        last = None
        for k in sorted(rows):
            offs = [i for at, i in rows[k] if at % grid]
            if len(offs) < 2:
                last = None
                continue
            pcs = chord_pcs(k)
            struck = Counter(pitch(i) for i in offs)
            ons = Counter(pitch(i) for at, i in rows[k] if at % grid == 0)
            top_on = ons.most_common(1)[0][0] if ons else None
            most = min(struck, key=lambda m: (-struck[m], m))
            if struck[most] >= 2 and (most % 12 in pcs or 2 * struck[most] >= len(offs)):   # the bar has a pedal of its own: a pitch struck twice
                pedal = most                                # or more off the pulse that is on the chord, or is half the bar's off-pulse notes
            else:                                           # it has none: one of its off-pulse pitches on the chord, the most struck, and the bar
                pedal = min((m for m in struck if m % 12 in pcs), key=lambda m: (-struck[m], m == top_on, m), default=None)   # before's where the carry asks
                if pedal is None:                           # none of them is on the chord: the chord's tone nearest the lowest
                    pedal = min((most + d for d in range(-6, 7) if (most + d) % 12 in pcs and low <= most + d <= high), key=lambda m: (abs(m - most), m), default=most)
                if (last is not None and pedal != last and carry_share is not None and carried / (pairs + 1) < carry_share - STEP_MARGIN
                        and (not pcs or last % 12 in pcs)):
                    pedal = last
            if last is not None:
                pairs += 1
                carried += pedal == last
            for i in offs:
                if pitch(i) != pedal and on_pedal / (seen + 1) < pedal_share - STEP_MARGIN:
                    put(i, pedal)
                    pedalled += 1
                seen += 1
                on_pedal += pitch(i) == pedal
            last = pedal
    if not stepped and not pedalled:
        return notes, ""
    with_it = 0
    moved = {round(old[i][0], 3): (int(round(old[i][2])), pitch(i)) for row in rows.values() for _, i in row if pitch(i) != int(round(old[i][2]))}
    for v in sorted({n[3] for n in old} - {0}):
        own = follows_own_line(plan, role, v, bars)
        for i, n in enumerate(old):
            got = moved.get(round(n[0], 3)) if n[3] == v else None
            if got is None:
                continue
            was, now = got
            m = int(round(n[2]))
            if (m - was) % 12 == 0:                         # the line in octaves: the line's new note in octaves
                to = m + now - was
            elif int((n[0] + NEAR) // meter) in own:        # a voice that follows the line: as far, and on to the scale
                to = m + now - was
                if to % 12 not in scale:
                    to += 1 if now > was else -1
                    if to % 12 not in scale:
                        to += 1 if now > was else -1
            else:
                continue
            if to != m:
                put(i, to)
                with_it += 1
    again = _repeats_follow(plan, old, new, meter)
    return new, (f"the line by its place in the beat, as its token song's (round 161; a pulse every {grid} twelfths of a beat): {stepped} notes on the pulse moved "
                 f"to the song's steps, {pedalled} off it to the bar's pedal (on it {on_pedal} of {seen}, the token's {'-' if pedal_share is None else format(pedal_share, '.2f')}; "
                 f"carried over {carried} of {pairs} bar lines)" + (f", {with_it} notes of the voices beside it with them" if with_it else "")
                 + (f"; {again} notes of the form's repeats with them" if again else ""))


def lay_turns(plan: Plan, meter: int, role: str, notes: list, seed: int, same: list, leave: dict | None = None) -> tuple:
    """A block line's note changes where its token song's line's does (round 160). The step profile holds how often a
    chord part's line repeats its note (round 117), a share over the line, and the changes fell wherever the share
    let them: on The Day After's token, whose tremolo strikes 24 times a bar, the written line stayed on a pitch three
    strikes at the median and turned between beats on three turns in four, where the game's stays six and turns on the
    first or the third beat on half. Here each bar of a line with the token's turns (`plan.line_turns`, the `turns=`
    word) draws the places of one of the token song's bars, on a stream of its own (TURNS_STREAM), and is laid out
    between them, each note taking the pitch of the stretch it falls in. Since round 168 the pitches go by the token
    bar's moves (`plan.line_turn_moves`): the first stretch keeps the note the bar was written to open on, and at each
    turn the line goes to the one of the bar's other written pitches whose distance from the note it is on is
    nearest the move the token song's line makes there, the earlier written of equals; a bar written on one pitch
    holds it, and so does a bar that draws a token bar with no turn: the note it opens on. A stretch may sit on a
    note off the bar's chord while the line's share of strikes off the chord, the stretch's counted, is within its
    token line's (the tone profile's "other", round 111, which the line was drawn to and the layout would undo: a
    passing note struck once in the bar as written is held half a bar); over it, the stretch takes the nearest of the
    bar's pitches that are on the chord, the opening the first of them written. Until then (and still for a vocabulary whose turns carry no moves) a bar kept as many of its written
    pitches as the places make stretches, those on the bar's chord before the ones it struck most, in the order they
    were written: an order set by hand. A voice beside the line on the line's own sample (`same`) is laid out with it: for each stretch, a note
    it had under that line pitch in the bar as written (one on the chord first, then on the scale, then the one it
    had most), held through the stretch; not in the bars where it follows another part's line (`leave`). A part of
    the form that repeats another still does. Returns (the notes, a log line or "")."""
    turns = plan.line_turns.get(role)
    if not turns:
        return notes, ""
    bars_moves = (getattr(plan, "line_turn_moves", None) or {}).get(role) or [[(place, None) for place in bar] for bar in turns]
    with_moves = all(move is not None for bar in bars_moves for _, move in bar)   # a vocabulary counted before round 168 says places alone
    other = ((getattr(plan, "tone_profiles", None) or {}).get(role) or {}).get("other")   # the token line's share of notes off the chord (round 111)
    counted = off_chord = 0                                 # the line's strikes laid out so far in bars with a chord, and those off it
    old, new = list(notes), list(notes)
    rng = random.Random(f"{TURNS_STREAM}:{seed}:{role}")
    scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
    line, moved, with_it = _bar_places(old, 0, meter), 0, 0
    beside = {v: _bar_places(old, v, meter) for v in same}
    for k in sorted(line):
        row = line[k]
        pitches = [int(round(old[i][2])) for _, i in row]
        count, first = Counter(pitches), {}
        for j, m in enumerate(pitches):
            first.setdefault(m, j)
        drawn = sorted(rng.choice(bars_moves))                 # one of the token song's bars: its turns' places and the moves made there
        starts = [0] + [place for place, _ in drawn]
        if with_moves:                                      # round 168: by the token bar's moves, from the note the bar opens on
            chorded = 0 <= k < len(plan.chords) and plan.chords[k] is not None and plan.chords[k][0] is not None
            sizes = Counter(max((j for j, s0 in enumerate(starts) if s0 <= at + 0.5), default=0) for at, _ in row)   # the strikes of each stretch

            def admit(m, n, done, off):                     # may a stretch of n strikes sit on m: on the chord, or within the token
                return (other is None or not chorded or not n or _on_chord(plan, k, m)   # noqa: B023  line's share of notes off it (its tone
                        or (off + n) / (done + n) <= other + 1e-9)                         # profile, round 111), the stretch counted
            done, off = counted, off_chord
            opening = pitches[0] if admit(pitches[0], sizes[0], done, off) else next((m for m in first if _on_chord(plan, k, m)), pitches[0])
            keep = [opening]
            done, off = done + sizes[0], off + sizes[0] * (not _on_chord(plan, k, opening))
            for j, (_, move) in enumerate(drawn, start=1):
                others = [m for m in first if m != keep[-1]]
                if not others:
                    break
                within = [m for m in others if admit(m, sizes[j], done, off)] or others
                keep.append(min(within, key=lambda m: (abs(m - keep[-1] - move), first[m])))   # noqa: B023
                done, off = done + sizes[j], off + sizes[j] * (not _on_chord(plan, k, keep[-1]))
            if len(keep) == 1:                              # a bar on one pitch: every strike of it
                done, off = counted + len(row), off_chord + len(row) * (not _on_chord(plan, k, opening))
            if chorded and other is not None:
                counted, off_chord = done, off
        else:                                               # no moves said: the bar's pitches by the hand order of round 160
            keep = sorted(sorted(count, key=lambda m: (not _on_chord(plan, k, m), -count[m], first[m]))[:len(starts)], key=lambda m: first[m])
        starts = starts[:len(keep)]
        stretch = lambda at: max(j for j, s0 in enumerate(starts) if s0 <= at + 0.5) if at + 0.5 >= starts[0] else 0   # noqa: E731,B023
        for at, i in row:
            m = keep[stretch(at)]
            if m != int(round(old[i][2])):
                new[i] = old[i][:2] + (float(m),) + tuple(old[i][3:])
                moved += 1
        was = {at: int(round(old[i][2])) for at, i in row}   # the line's written pitch at each place
        for v in same:
            if leave and k in leave.get(v, ()):
                continue
            under = {}                                      # the voice's written notes under each of the line's written pitches
            for at, i in beside[v].get(k, []):
                if at in was:
                    under.setdefault(was[at], Counter())[int(round(old[i][2]))] += 1
            for at, i in beside[v].get(k, []):
                had = under.get(keep[stretch(at)])
                if at in was and had:
                    m = min(had, key=lambda q: (not _on_chord(plan, k, q), q % 12 not in scale, -had[q], q))   # noqa: B023
                    if m != int(round(old[i][2])):
                        new[i] = old[i][:2] + (float(m),) + tuple(old[i][3:])
                        with_it += 1
    if not moved and not with_it:
        return notes, ""
    again = _repeats_follow(plan, old, new, meter)
    return new, (f"the line's note changes where its token song's line's does (round 160): {len(line)} bars laid out, {moved} of the line's notes moved"
                 + (f", {with_it} of the voices' on its sample with them" if with_it else "") + (f"; {again} notes of the form's repeats with them" if again else ""))


def hold_with_line(plan: Plan, meter: int, notes: list, v: int, leave: set | None = None, share: float = 0.0) -> tuple:
    """A voice keeps its note where the line keeps its own, as often as its token voice does (rounds 160 and 167). A voice that runs
    parallel to its line has each note's landing drawn anew (`parallel`: by the line's tone against the chord and the
    landing before), so under a line that repeats its note the voice flickered between chord tones: where the line
    repeated its pitch a voice beside it repeated its own on 0.51 of its strikes, FFVI's on 0.83, and FFVI's voices on
    the line's own sample, an instrument struck as a chord, on 0.97. Here, in time order, where the line's note at
    the voice's strike is the one it had at the voice's strike before, the voice takes its own note of that strike
    again, while the share of such strikes kept so far, this one counted, is within `share`: its token voice's (the
    `keeps=` word, round 167; until then a hand share of 1.0 less a margin, for the voices on the line's own sample and
    no other). A voice over its token's share is not made to move.
    Strikes with no line note at them are not counted, nor the bars where the voice follows another part's line
    (`leave`). A part of the form that repeats another still does. Returns (the notes, a log line or "")."""
    old, new = list(notes), list(notes)
    line = sorted((n[0], int(round(n[2]))) for n in old if n[3] == 0)
    at, before, kept, seen, moved = 0, None, 0, 0, 0
    for i in sorted((i for i, x in enumerate(old) if x[3] == v), key=lambda i: old[i][0]):
        t, m = old[i][0], int(round(old[i][2]))
        while at + 1 < len(line) and line[at + 1][0] <= t + NEAR:
            at += 1
        if not line or abs(line[at][0] - t) > NEAR:
            continue
        if before is not None and before[0] == line[at][1]:
            if m != before[1] and (kept + 1) / (seen + 1) <= share + 1e-9 and not (leave and int((t + NEAR) // meter) in leave):
                m = before[1]
                new[i] = old[i][:2] + (float(m),) + tuple(old[i][3:])
                moved += 1
            seen += 1
            kept += m == before[1]
        before = (line[at][1], m)
    if not moved:
        return notes, ""
    again = _repeats_follow(plan, old, new, meter)
    return new, (f"voice {v + 1} keeps its note where the line keeps its own (round 160), to its token voice's share (round 167: {share:.2f}): "
                 f"{moved} notes moved, {kept} of {seen} such strikes kept" + (f"; {again} notes of the form's repeats with them" if again else ""))


STRUCK_OVER = 0.15                    # a struck voice left this far over its token's share once its masks are drawn, with a bar no mask thinned


def strike_where_token_does(plan: Plan, meter: int, role: str, notes: list) -> tuple:
    """A voice struck with another strikes where its token voice does, where no mask could thin it (round 159). The
    struck facts say what share of the followed voice's onsets the voice strikes (round 108), and struck_with holds a
    drawn second_figures mask toward it: under the share a bar strikes every followed onset, over it a mask that thins
    nothing is drawn again. Where the word has no mask that thins the bar the hold has nothing to draw: under The Day
    After's tremolo, 24 strikes a bar, the word's one mask is every strike, and the plucked voice that plays seven
    notes a bar in the game, and rests through the first eight bars, was written on all 24 in every bar (0.93 of the
    followed onsets against the token's 0.29). Here, once every part is written, a voice whose strikes over the
    followed onsets (extras["struck_counts"], kept as struck_with wrote it) are STRUCK_OVER or more over its token's
    share, and that the hold could not thin in a bar or more (extras["struck_bars"]: a bar in which every draw of the
    mask struck every followed onset; round 162: a voice over the margin whose masks thinned every bar asked is the
    masks' own drift, and was taken for this, 233 of 303 notes of a piano's lower voice taken out),
    strikes at its token voice's places (`plan.struck_places`, the `struck=` word: its usual bar in each part of
    the form by the form's letters, carried only where the form is the token song's): in each bar the note nearest
    each place, within a twelfth of a beat, is kept and the voice's other notes are taken out; in a part it rests in,
    every note. A note kept sounds the token voice's median length, or to the voice's next note, the shorter (until
    round 166 a hand share of that gap, 0.9: a voice plays one note at a time, and the gap is its bound). A part of the form whose letter the word does not have is left. Returns (the notes, a log line or "")."""
    out, lines = list(notes), []
    counts = (plan.extras.get(role) or {}).get("struck_counts") or {}
    for v, (length, by_letter) in sorted((plan.struck_places.get(role) or {}).items()):
        struck, thinned, share = counts.get(v) or (0, 0, None)
        asked, unthinned = ((plan.extras.get(role) or {}).get("struck_bars") or {}).get(v) or ((), ())
        if share is None or not struck or struck / (struck + thinned) <= share + STRUCK_OVER or not unthinned:
            continue                                        # within its share, or over it with masks that thinned every bar asked (round 162)
        keep, rested = set(), 0
        for bar, n_bars, _, letter in plan.parts:
            places = by_letter.get(letter)
            if places is None:
                keep |= {i for i, x in enumerate(out) if x[3] == v and bar * meter - NEAR <= x[0] < (bar + n_bars) * meter - NEAR}
                continue
            for k in range(bar, bar + n_bars):
                row = [(round((x[0] - k * meter) * 12), i) for i, x in enumerate(out) if x[3] == v and k * meter - NEAR <= x[0] < (k + 1) * meter - NEAR]
                rested += bool(row) and not places
                for place in places:
                    near = min(row, key=lambda r: abs(r[0] - place), default=None)
                    if near is not None and abs(near[0] - place) <= 1:
                        keep.add(near[1])
        before = sum(1 for x in out if x[3] == v)
        out = [x for i, x in enumerate(out) if x[3] != v or i in keep]
        own = [i for i, x in enumerate(out) if x[3] == v]
        for i, j in zip(own, own[1:] + [None]):
            gap = (out[j][0] - out[i][0]) if j is not None else 1.0
            out[i] = (out[i][0], out[i][0] + min(length, gap)) + tuple(out[i][2:])
        lines.append(f"voice {v + 1} strikes where its token voice does (round 159): it struck {struck / (struck + thinned):.2f} of the followed onsets "
                     f"against the token's {share:.2f} and no mask thinned {len(set(unthinned))} of the {len(set(asked))} bars asked (round 162); "
                     f"{before - len(own)} of its {before} notes taken out, {rested} bars rested, "
                     f"its notes {length:.2f} beats at the most")
    return (out, "; ".join(lines)) if lines else (notes, "")


def keep_voice_pace(plan: Plan, meter: int, role: str, notes: list, bars: int) -> tuple:
    """A voice beside a line keeps within its token voice's notes a bar in the bars that are its own (round 164). The
    token says each voice's onsets a bar by the form's letters (round 125: the ninth sub-field of its entry), and the
    writers hold a line's bar within TIGHT of its own; a voice beside the line was held to nothing, its own bars
    written beside the line's at the line's pace: on Johnny C. Bad's token the guitar's low voice, one note a bar
    through the fifteen bars in which the piano is out, was written at eight to fourteen, runs under the tune and the
    bass. Here, once every part is written, in each bar of a voice that is its own (a stretch of its own by its
    relation word, or a voice with no word; not a bar where it follows a line: follows_another_part,
    follows_own_line) with more notes than TIGHT's upper multiple of its token voice's for the part of the form (the
    part's last bar by its own count where the token gives one; one note at the least), the notes nearest the
    places its token voice plays at in its bar there are kept (`plan.voice_places`, the `struck=` word since round
    166), as many as that, and the others taken out: a note by how far it is from the nearest of those places, the
    earlier of equals. Until round 166 the notes kept were the ones on the bar's strong beats, by a hand order (the
    first beat, the middle beat, the other beats, the half beats). Nothing is drawn or moved. A part of the form the
    token says nothing of for the voice, its notes a bar or its places, is left. Returns (the notes, a log line
    or "")."""
    out, lines = list(notes), []
    for v, said in sorted((plan.layer_onsets.get(role) or {}).items()):
        if not any(n[3] == v for n in out):
            continue
        led = follows_another_part(plan, role, v, bars) | follows_own_line(plan, role, v, bars)
        where = (plan.voice_places.get(role) or {}).get(v) or {}
        taken, thinned = 0, 0
        for bar, n_bars, _, letter in plan.parts:
            got = said.get(letter) or said.get(WHOLE_SONG)
            places = where.get(letter) or where.get(WHOLE_SONG)   # where its token voice plays in its bar there (round 166)
            if not got or not places:
                continue
            for k in range(bar, bar + n_bars):
                if k in led:
                    continue
                own = got[1] if got[1] is not None and k == bar + n_bars - 1 else got[0]
                most = max(1, math.floor(writer.TIGHT[1] * own))
                idx = [i for i, n in enumerate(out) if n[3] == v and k * meter - NEAR <= n[0] < (k + 1) * meter - NEAR]
                if len(idx) <= most:
                    continue

                def far(i, k=k, places=places):
                    at = (out[i][0] - k * meter) * 12
                    return (round(min(abs(at - p) for p in places), 3), out[i][0])
                keep = set(sorted(idx, key=far)[:most])
                out = [n for i, n in enumerate(out) if i not in idx or i in keep]
                taken, thinned = taken + len(idx) - most, thinned + 1
        if taken:
            lines.append(f"voice {v + 1} within its token voice's notes a bar in its own bars (round 164): {taken} notes taken out of {thinned} bars")
    return (out, "; ".join(lines)) if lines else (notes, "")


def follow_share(plan: Plan, role: str, models: dict | None, seed: int, log: list | None = None) -> tuple | None:
    """How far a tune or a counter-line goes with a chord that leaves the key (round 171): its token song's line's two
    shares (`plan.chord_follows`, the `follows=` word), else a draw from the pooled `chord_follows` word on a stream
    of its own; None where the vocabulary has neither (one counted before the round: the line stays on the key)."""
    if role in plan.chord_follows:
        return plan.chord_follows[role]
    if models and "chord_follows" in models:
        pair = follow_pair(_draw(models, "chord_follows", (role,), random.Random(f"whole:{seed}:chord_follows:{role}")))
        if log is not None and pair:
            log.append(f"the token gives the {role} no shares of notes on a chord's tone off the key; drawn from the pooled word (round 171): "
                       + "/".join("-" if x is None else f"{x:.2f}" for x in pair))
        return pair
    return None


def follow_chords(plan: Plan, meter: int, notes: list, shares: tuple | None) -> tuple:
    """A line goes with a chord that leaves the key (round 171). The tune and the counter-line are drawn on the key's
    scale, their notes off it held to a share over the song (round 93), whatever the bar's chord: over a chord with a
    tone off the key (a major chord on the key's seventh degree: two of its three tones) the band played the chord
    and the tune the key, a semitone from it on over half its notes. Here a note on the key's tone that gives way to
    such a tone of its bar's chord (rhythm.given_way: the key's tone a semitone over it, or under it) takes the
    chord's tone, a semitone off, while the line's share of notes on the chord's tone, of those on it or on the key's
    tone on that side of it, this one counted, is within its token song's line's share for the side (`shares`: over,
    under; None for a side not held). Each voice of the part by its own count, in time order; a note keeps its
    place, its length and its voice. Nothing is drawn. `notes`: (start, end, midi) or (start, end, midi, voice).
    Returns (the notes, how many moved, how many are on a chord's tone off the key, how many stay on a key's tone
    that gives way)."""
    if not shares:
        return notes, 0, 0, 0
    scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
    ways, offs = {}, {}
    for k, c in enumerate(plan.chords):
        if c is not None and c[0] is not None:
            tones = {(c[0] + x) % 12 for x in harmony.SHAPES.get(c[1], harmony.SHAPES[""])}
            way = rhythm.given_way(scale, tones)
            if way:
                ways[k], offs[k] = way, tones - scale
    if not ways:
        return notes, 0, 0, 0
    held = dict(zip(rhythm.FOLLOW_SIDES, shares))
    out, moved, followed, stayed = list(notes), 0, 0, 0
    for v in sorted({(n[3] if len(n) > 3 else 0) for n in notes}):
        on, stay = 0, Counter()
        for i in sorted((i for i, n in enumerate(notes) if (n[3] if len(n) > 3 else 0) == v), key=lambda i: notes[i][0]):
            k = int((notes[i][0] + NEAR) // meter)
            way = ways.get(k)
            if not way:
                continue
            m = int(round(notes[i][2]))
            if m % 12 in offs[k]:
                on += 1
            elif m % 12 in way:
                to, side = way[m % 12]
                if held.get(side) is not None and (on + 1) / (on + stay[side] + 1) <= held[side] + 1e-9:
                    out[i] = notes[i][:2] + (float(m + (-1 if side == rhythm.FOLLOW_SIDES[0] else 1)),) + tuple(notes[i][3:])
                    on, moved = on + 1, moved + 1
                else:
                    stay[side] += 1
        followed, stayed = followed + on, stayed + sum(stay.values())
    return out, moved, followed, stayed


def follows_another_part(plan: Plan, role: str, v: int, bars: int) -> set:
    """The bars in which a part's voice `v` doubles another part's line or runs parallel to it by its token's relation
    word (round 90): there its notes are that line's again, and are not the part's own to move."""
    word = relation_word(plan, role, v)
    return {k for kind, target, _, a, b in (stretch_spans(relation_stretches(word), bars) if word else [])
            if kind in ("double", "parallel") and isinstance(target, str) and target != role for k in range(a, b)}


def hear_own_voices(plan: Plan, meter: int, notes: list, others: list, leave: dict | None = None, shares: dict | None = None) -> tuple:
    """A chord part's voices beside its line hear the part's other voices (round 158). The line and each voice beside it
    are placed against the chord and the line (`parallel`, the voice words), and a voice's clashes word counts it
    against the parts written before its part, never against its own part's voices: two voices a third over one line
    landed on the major third and the minor at once, and the more voices a part had the more it clashed with itself
    (over 400 songs a semitone sounded between two voices of the accompaniment at 0.06 of its onsets with two voices,
    0.15 with three, 0.22 with four, 0.41 with five; FFVI's own accompaniments 0.01 at the median, 0.22 at the most).
    Here, once every part is written, the voices are taken in order, the line never moved: a note a semitone by pitch
    class from a note that a lower-numbered voice of its part sounds while it sounds (at its onset alone where no
    pitch clears the whole of it) moves to the nearest pitch within HEAR_REACH that is not, a tone of the bar's chord
    before a tone of the key's scale before any other; among those one not a semitone from another part's note at its
    onset, then one that is not a unison with its own part, then the nearer, then the lower. A note with no such pitch
    stays, and a part of the form that repeats another still does (_repeats_follow). A voice's notes in the bars where
    it doubles another part's line or runs parallel to it (`leave`: voice -> those bars, follows_another_part) are that
    line's and are left; the voices after it hear them all the same, and since round 163 the voices before it do too:
    a note left where it stands is heard by every other voice of the part, whatever its number (a piano's lower voice
    sat a semitone from the voice under it, which follows the tune and is left, and nothing moved either).
    Since round 165 a voice keeps its token voice's share of such notes (`shares`: voice -> the share, the `rubs=`
    word): in time order, a note that sits a semitone from its part stays where the voice's share of them so far, this
    one counted, is within the token's, and moves where it would be over; a voice the token says nothing of keeps
    none, as every voice did before the word. `notes`: the part's, (start, end, midi, voice);
    `others`: the other pitched parts' notes. Returns (the notes, a log line or "")."""
    old, new = list(notes), list(notes)
    scale = {(plan.tonic + i) % 12 for i in harmony.MODES["major" if plan.mode == "major" else "natural_minor"]}
    pc = lambda m: int(round(m)) % 12                       # noqa: E731
    # what a voice hears of its part: the voices before it, settled already, and (round 163) a later voice's notes in the bars
    # where that voice is left, another part's line again: they will not move, so it is for this voice to stand clear of them
    heard = lambda x, v: x[3] < v or (x[3] > v and bool(leave) and int((x[0] + NEAR) // meter) in leave.get(x[3], ()))   # noqa: E731
    moved, stuck, tiers, kept = 0, 0, [0, 0, 0], {}
    for v in sorted({n[3] for n in old})[1:]:
        share, rubs, seen = (shares or {}).get(v, 0.0), 0, 0   # the token voice's share of notes a semitone from its part (round 165)
        for i in sorted((i for i, n in enumerate(old) if n[3] == v), key=lambda i: old[i][0]):
            a, b, m = new[i][0], new[i][1], int(round(new[i][2]))
            if leave and int((a + NEAR) // meter) in leave.get(v, ()):
                continue                                    # another part's line again here: not this part's to move
            over = {pc(x[2]) for x in new if heard(x, v) and x[0] < b - NEAR and x[1] > a + NEAR}
            seen += 1
            if not any((m - q) % 12 in writer.CLASH for q in over):
                continue
            if (rubs + 1) / seen <= share + 1e-9:           # within its token voice's share, this one counted: it stays (round 165)
                rubs += 1
                kept[v] = kept.get(v, 0) + 1
                continue
            at_on = [x for x in new if heard(x, v) and x[0] <= a + NEAR and x[1] > a + NEAR]
            own = {int(round(x[2])) for x in at_on}
            other = {pc(x[2]) for x in others if x[0] <= a + NEAR and x[1] > a + NEAR}
            k = int((a + NEAR) // meter)
            best = None
            for held in (over, {pc(x[2]) for x in at_on}):
                free = [m + d for step in range(1, HEAR_REACH + 1) for d in (-step, step) if not any((m + d - q) % 12 in writer.CLASH for q in held)]
                if free:
                    best = min(free, key=lambda c: (0 if _on_chord(plan, k, c) else 1 if c % 12 in scale else 2,
                                                    any((c - q) % 12 in writer.CLASH for q in other), c in own, abs(c - m), c))
                    break
            if best is None:
                stuck += 1
                rubs += 1
                continue
            tiers[0 if _on_chord(plan, k, best) else 1 if best % 12 in scale else 2] += 1
            new[i] = new[i][:2] + (float(best),) + tuple(new[i][3:])
            moved += 1
    said = ("; left a semitone from their part, within the token voices' shares (round 165): "
            + ", ".join(f"voice {v + 1} {n} (the token's {(shares or {}).get(v, 0.0):.2f})" for v, n in sorted(kept.items()))) if kept else ""
    if not moved:
        return notes, (f"voices beside the line a semitone from their own part (round 158): none moved{said}" if kept else "")
    again = _repeats_follow(plan, old, new, meter)
    return new, (f"voices beside the line off a semitone with their own part (round 158): {moved} notes moved, {tiers[0]} to a tone of the chord, "
                 f"{tiers[1]} to a tone of the scale, {tiers[2]} to another" + (f"; {stuck} with no pitch free left" if stuck else "")
                 + (f"; {again} notes of the form's repeats with them" if again else "") + said)


def settle_chord_parts(plan: Plan, song: rhythm.Song, written: dict, seed: int = 0, models: dict | None = None) -> bool:
    """The chord parts' voices settled once every part is written: after the tune and the counter-line, so they stand as
    they were written over the parts (a chord part changed before the tune is written re-writes the tune). Round 161:
    a moving line is held to its token song's line by its place in the beat, the pedal off the pulse and the steps on
    it (hold_pulse). Round 160:
    a block line's note changes where its token song's does (lay_turns), and a voice keeps its note where the line
    keeps its own (hold_with_line), since round 167 as often as its token voice does (the `keeps=` word), or by a
    draw from the pooled `voice_keeps` word where the token gives the voice no share (`models`). Round 159: a voice struck with another that no mask could
    thin strikes where its token voice does (strike_where_token_does). Round 164: a voice beside the line keeps within
    its token voice's notes a bar in the bars that are its own (keep_voice_pace).
    Round 158: a voice beside the line hears its own part's voices (hear_own_voices), and since round 165 keeps its
    token voice's share of notes a semitone from them (the `rubs=` word). Returns whether a note changed."""
    any_moved = False
    for role in rhythm.UPPER:
        part = written.get(role)
        if part is None or not part.notes:
            continue
        notes = list(part.notes)
        beside = plan.layer_samples.get(role) or []
        same = [v for v in sorted({n[3] for n in notes} - {0}) if v - 1 < len(beside) and beside[v - 1] and beside[v - 1] == plan.token_samples.get(role)]
        follows = {v: follows_another_part(plan, role, v, len(song.bars)) for v in same}
        notes, line = hold_pulse(plan, song.meter, role, notes, len(song.bars))   # round 161: a moving line by its place in the beat
        if line:
            part.log.append(line)
        notes, line = lay_turns(plan, song.meter, role, notes, seed, same, follows)   # round 160: the line first, and the voices on its sample
        if line:
            part.log.append(line)
        keeps = dict(plan.voice_keeps.get(role) or {})      # round 167: every voice by its token voice's share, and a voice the
        if models and "voice_keeps" in models:              # token gives none by a draw from the pooled word, on its own stream
            for v in sorted({n[3] for n in notes} - {0} - set(keeps)):
                keeps[v] = float(_draw(models, "voice_keeps", (rhythm.KEEP_SAMPLES[0 if v in same else 1],), random.Random(f"whole:{seed}:voice_keeps:{role}:{v}")))
                among = "the line's sample" if v in same else "another sample"
                part.log.append(f"voice {v + 1}: the token gives no share of notes kept with the line; drawn from the voices on "
                                f"{among} (round 167): {keeps[v]:.2f}")
        for v, share in sorted(keeps.items()):
            if any(n[3] == v for n in notes):
                notes, line = hold_with_line(plan, song.meter, notes, v, follows.get(v) or follows_another_part(plan, role, v, len(song.bars)), share)
                if line:
                    part.log.append(line)
        notes, line = strike_where_token_does(plan, song.meter, role, notes)   # round 159: before the voices hear each other
        if line:
            part.log.append(line)
        notes, line = keep_voice_pace(plan, song.meter, role, notes, len(song.bars))   # round 164: a voice's own bars at its token voice's pace
        if line:
            part.log.append(line)
        if len({n[3] for n in notes}) > 1:
            others = [n for r, p in written.items() if r != role and r != R.DRUMS for n in p.notes]
            leave = {v: follows_another_part(plan, role, v, len(song.bars)) for v in sorted({n[3] for n in notes})[1:]}
            notes, line = hear_own_voices(plan, song.meter, notes, others, leave, plan.voice_rubs.get(role))
            if line:
                part.log.append(line)
        if notes != part.notes:
            part.notes[:] = notes
            song.notes[role] = sorted([(a, b - a, m, role) for a, b, m, *_ in notes], key=lambda x: x[0])
            any_moved = True
    return any_moved
