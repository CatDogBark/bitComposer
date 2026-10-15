"""
Melody generation: motifs, contours, counter-melody, and note-cuts.
"""

import random

from .pattern import ROWS_PER_BAR


# ── Motif-based melody system ──

# Rhythmic templates: row offsets within a single bar. Placed once per bar by
# _generate_melody_phrased — see the note there about why.
RHYTHM_TEMPLATES = [
    [0, 4, 8, 12],                     # Quarter notes
    [0, 4, 8, 14],                     # Dotted ending
    [0, 4, 6, 8, 12],                  # Eighth note pickup
    [0, 2, 8, 12, 16],                 # Syncopated
    [0, 8, 12, 14],                    # Long-short-short
    [0, 4, 8, 10, 12],                 # Running then rest
    [0, 6, 8, 12, 14],                 # Off-beat accent
    [0, 4, 12, 14, 16],                # Gap then flurry
    # Sixteenth-note figures. Every template above sits on even rows, so no
    # note could ever land a sixteenth ahead of or behind the beat — the
    # single most common device in game melodies, and 0.3% of onsets had it.
    [0, 3, 6, 8, 12],                  # Dotted-eighth push
    [0, 4, 7, 8, 12],                  # Anticipated third beat
    [0, 4, 8, 11, 12],                 # Pickup into beat four
    [0, 2, 3, 8, 11],                  # Skip and anticipation
    [0, 6, 7, 8, 14],                  # Flam into the beat
    [0, 3, 4, 8, 12, 15],              # Pushed, then pickup to the next bar
]

# ── Motif grammar ──
#
# A motif used to be a rhythm template plus a "contour", a list of scale
# steps drawn from a shape (arch, zigzag) with no idea which intervals sound
# like a tune. Tunes are mostly steps, with leaps in a few sanctioned places
# — a fourth or fifth to launch a phrase, an octave for drama — answered by
# steps back; tension tones resolve (the seventh up to the root, the fourth
# down to the third); and the rhythm is the phrase's identity, repeated bar
# to bar while pitches move inside it. The grammar below builds motifs from
# cells with those properties. Moves are in scale steps between successive
# notes.

CELLS = [
    # (name, moves, weight)
    ("step up",        [1],        22),
    ("step down",      [-1],       22),
    ("repeat",         [0],        10),
    ("neighbour up",   [1, -1],    10),
    ("neighbour down", [-1, 1],    10),
    ("third up",       [2],         8),
    ("third down",     [-2],        8),
    ("run up",         [1, 1],      5),
    ("run down",       [-1, -1],    5),
]
LAUNCHES = [("fourth", 3, 50), ("fifth", 4, 35), ("octave", 7, 15)]


def generate_motif(length: int = 4, rng: random.Random | None = None) -> dict:
    """A one-bar motif: a rhythm and a list of moves (scale steps) per note.

    The first move is 0. A launch leap is allowed on the first move only,
    and is always answered by a step down. Everything else comes from CELLS.
    Form says how the phrase treats it: a *sentence* (statement, sequence,
    development, cadence) or a *period* (a cell, its answer, the cell again,
    the answer closed) — the two shapes most hooks take.
    """
    r = rng or random
    rhythm = list(r.choice(RHYTHM_TEMPLATES))
    if len(rhythm) > length:
        rhythm = rhythm[:length]
    while len(rhythm) < length:
        rhythm.append(min(15, rhythm[-1] + r.choice([2, 4])))
    rhythm = sorted(set(rhythm))

    moves = [0]
    if r.random() < 0.35:                               # a launch leap
        _, leap, _ = r.choices(LAUNCHES, weights=[w for _, _, w in LAUNCHES], k=1)[0]
        moves += [leap, -1]
    while len(moves) < len(rhythm):
        _, cell, _ = r.choices(CELLS, weights=[w for _, _, w in CELLS], k=1)[0]
        moves += cell
    moves = moves[:len(rhythm)]
    return {"rhythm": rhythm, "contour": moves,
            "form": "period" if r.random() < 0.5 else "sentence",
            "contour_name": "period" if False else ("launch" if len(moves) > 1 and moves[1] >= 3 else "stepwise")}


def vary_motif(motif: dict, amount: float = 0.3, rng: random.Random | None = None) -> dict:
    """Create a variation of a motif — small rhythmic/melodic changes."""
    random_ = rng or random
    rhythm = list(motif["rhythm"])
    contour = list(motif["contour"])

    # The rhythm is the motif's identity: vary it rarely and by a single
    # nudge, so a verse and chorus built on one motif still share a pulse.
    if random_.random() < amount * 0.4:
        i = random_.randrange(len(rhythm))
        rhythm[i] = max(0, rhythm[i] + random_.choice([-1, 1]))

    for i in range(1, len(contour)):
        if random_.random() < amount:
            contour[i] = max(-2, min(2, contour[i] + random_.choice([-1, 1])))

    # Keep rhythm sorted and non-negative
    rhythm.sort()
    rhythm[0] = 0

    return {"rhythm": rhythm, "contour": contour, "contour_name": motif["contour_name"],
            "form": motif.get("form", "sentence")}


def _generate_melody_simple(scale_notes: list[int], chord_notes: list[int],
                            rows: int, density: float = 0.5) -> list[tuple[int, int]]:
    """Generate a simple random-walk melody. Returns [(row, midi_note), ...]."""
    random_ = random
    notes = []
    melody_notes = [n for n in scale_notes if 60 <= n <= 83]
    if not melody_notes:
        melody_notes = [n + 12 for n in scale_notes if 48 <= n <= 71]
    if not melody_notes:
        return notes

    chord_in_range = [n for n in chord_notes if n in melody_notes]
    current = random_.choice(chord_in_range) if chord_in_range else random_.choice(melody_notes)

    row = 0
    while row < rows:
        if random_.random() < density:
            idx = melody_notes.index(current) if current in melody_notes else 0
            step = random_.choices([-2, -1, 0, 1, 2], weights=[10, 25, 15, 25, 10], k=1)[0]
            new_idx = max(0, min(len(melody_notes) - 1, idx + step))
            current = melody_notes[new_idx]
            if random_.random() < 0.2 and chord_in_range:
                current = random_.choice(chord_in_range)
            duration = random_.choice([2, 4, 4, 4, 8])
            notes.append((row, current))
            row += duration
        else:
            row += random_.choice([2, 4])

    return notes


def chord_at(timeline, row: int, default: list[int]) -> list[int]:
    """Chord notes sounding at `row` in a [(start_row, chord_notes), ...] list."""
    if not timeline:
        return default
    current = default
    for start, notes in timeline:
        if start <= row:
            current = notes
        else:
            break
    return current


# ── Phrase engine ──
#
# A pattern is four bars, and a melody over it is a *sentence*: a statement,
# a sequence of it (the same shape a step higher or lower), a development
# that carries the phrase's highest note, and a cadence that lands on a held
# note — off the tonic for a question phrase, on it for the answer. Chord
# tones sit on the strong beats and leaps are answered by steps. The old
# generator varied one bar four times with a random nudge each time, which
# is what "noodling in motif clothes" sounds like.

STRONG_ROWS = (0, 8)          # beats 1 and 3 of a 16-row bar
LEAP = 4                      # scale steps that count as a leap


def _transform(motif: dict, kind: str, shift: int = 0) -> dict:
    """A motif transformation: repeat, sequence (shift start), invert, fragment."""
    rhythm, contour = list(motif["rhythm"]), list(motif["contour"])
    if kind == "invert":
        contour = [contour[0]] + [-c for c in contour[1:]]
    elif kind == "fragment":
        n = max(2, len(rhythm) // 2)
        head_r, head_c = rhythm[:n], contour[:n]
        span = max(8, head_r[-1] + 2)
        rhythm = head_r + [r + span for r in head_r if r + span < 16]
        contour = head_c + [1] + head_c[1:len(rhythm) - n]
        contour = contour[:len(rhythm)]
    return {"rhythm": rhythm, "contour": contour, "shift": shift,
            "contour_name": motif.get("contour_name", "")}


def _cadence_from(motif: dict) -> dict:
    """A cadence bar in the motif's own rhythm: its first onsets, then a held
    note on the next strong beat. Keeps the phrase's rhythmic identity to
    the end instead of switching to a stock figure."""
    head = [r for r in motif["rhythm"] if r < 8][:3] or [0]
    land = 8 if head[-1] < 8 else 12
    rhythm = head + [land]
    return {"rhythm": rhythm, "contour": [0] + [-1] * (len(rhythm) - 1), "shift": 0, "cadence": True}


def _plan_sentence(motif: dict, rng: random.Random, density: float) -> list[dict | None]:
    """Four bars of transformations.

    A *period*: the cell, its answer (same rhythm, new pitches), the cell
    again exactly, the answer closed on a cadence — the most repetitive
    shape and the most hummable. A *sentence*: statement, the same shape a
    step up (or repeated exactly), a development carrying the climax, a
    cadence. Either way the rhythm holds across the bars.
    """
    if motif.get("form") == "period":
        # The answer rises, so the period peaks in its second bar on purpose.
        answer = _transform(motif, "repeat", shift=rng.choice([1, 2]))
        answer["contour"] = [0] + [max(-2, min(2, c + rng.choice([-1, 0, 0, 1]))) for c in motif["contour"][1:]]
        plan = [motif, answer, _transform(motif, "repeat", shift=0), _cadence_from(motif)]
        if density < 0.45:
            plan[1] = None
        return plan
    # The sentence rises: bar two a step up or an exact repeat, bar three two
    # steps up, so the peak comes late.
    second = _transform(motif, "repeat", shift=1 if rng.random() < 0.6 else 0)
    third_kind = rng.choice(["fragment", "fragment", "repeat", "repeat", "invert"])
    third = _transform(motif, third_kind, shift=2 if third_kind != "invert" else 1)
    cadence = _cadence_from(motif)
    plan = [motif, second, third, cadence]
    # Sparse phrases drop the sequence bar first and keep the development,
    # which carries the climax; only the sparsest drop both.
    if density < 0.45:
        plan[1] = None
    if density < 0.35:
        plan[2] = None
    return plan


def _snap_to_chord(idx: int, melody_notes: list[int], chord: list[int], reach: int = 2,
                   avoid: int | None = None, direction: int = 0) -> int:
    """Nearest chord-tone index within `reach` scale steps of idx, else idx.

    `avoid` is the index the line just left: when it was moving, snapping
    straight back onto that note froze the melody on one pitch (63 63 63),
    so a different chord tone is preferred, searched first in the line's
    direction of travel.
    """
    pcs = {n % 12 for n in chord}
    order = (1, -1) if direction >= 0 else (-1, 1)
    fallback = None
    for d in range(0, reach + 1):
        for sign in order:
            cand = idx + sign * d
            if 0 <= cand < len(melody_notes) and melody_notes[cand] % 12 in pcs:
                if cand != avoid:
                    return cand
                fallback = fallback if fallback is not None else cand
    return idx if fallback is None else fallback


def _realize_bar(bar_motif: dict, melody_notes: list[int], chord: list[int],
                 start_row: int, cur_idx: int, rows: int,
                 target_pc: int | None = None, key_root: int | None = None) -> tuple[list[tuple[int, int]], int]:
    """Realise one bar of a sentence from the current scale index.

    Strong beats take chord tones; a leap is followed by a step back the
    other way; tension tones resolve (the seventh rises to the root, the
    fourth falls to the third) when the next move is a step; a cadence bar
    walks to target_pc and holds it.
    """
    notes = []
    idx = max(0, min(len(melody_notes) - 1, cur_idx + bar_motif.get("shift", 0)))
    steps = list(zip(bar_motif["rhythm"], bar_motif["contour"]))
    last_leap = 0
    for i, (off, step) in enumerate(steps):
        row = start_row + off
        if row >= rows or off >= 16:
            break
        prev_idx = idx
        if i > 0:
            if last_leap and (step == 0 or (step > 0) == (last_leap > 0)):
                step = -1 if last_leap > 0 else 1          # answer the leap with a step back
            elif key_root is not None and abs(step) == 1:
                degree = (melody_notes[idx] - key_root) % 12
                if degree == 11:
                    step = 1                                # leading tone rises
                elif degree == 5:
                    step = -1                               # the fourth falls
            idx = max(0, min(len(melody_notes) - 1, idx + step))
            last_leap = step if abs(step) >= 3 else 0
        if bar_motif.get("cadence") and i == len(steps) - 1 and target_pc is not None:
            # Land on the target pitch class nearest to where we are.
            cands = [k for k, n in enumerate(melody_notes) if n % 12 == target_pc]
            if cands:
                idx = min(cands, key=lambda k: abs(k - idx))
        elif off % 16 in STRONG_ROWS:
            moved = idx - prev_idx
            idx = _snap_to_chord(idx, melody_notes, chord, reach=3,
                                 avoid=prev_idx if (i > 0 and moved) else None,
                                 direction=moved)
        notes.append((row, melody_notes[idx]))
    return notes, idx


def _generate_melody_phrased(scale_notes: list[int], chord_notes: list[int],
                              rows: int, density: float = 0.5,
                              motif: dict | None = None,
                              is_answer: bool = False,
                              chord_timeline=None,
                              rng: random.Random | None = None,
                              register: float = 0.5) -> list[tuple[int, int]]:
    """A four-bar sentence over the pattern. See the phrase-engine note above.

    register (0..1) places the phrase low or high in the melody range — the
    composer drives it from section energy, so verses sit low and choruses
    lift. rng is the melody's own stream, so the rest of the arrangement does
    not shift when the melody code changes.
    """
    r = rng or random
    melody_notes = [n for n in scale_notes if 60 <= n <= 83]
    if not melody_notes:
        melody_notes = [n + 12 for n in scale_notes if 48 <= n <= 71]
    if not melody_notes:
        return []
    if motif is None:
        motif = generate_motif(length=r.choice([4, 5]), rng=r)

    bars = max(1, rows // ROWS_PER_BAR)
    first_chord = chord_at(chord_timeline, 0, chord_notes)
    # Start near the register centre, on a chord tone, with room to climb.
    centre = int(round(register * (len(melody_notes) - 1)))
    centre = max(1, min(len(melody_notes) - 4, centre + r.randint(-1, 1)))
    cur_idx = _snap_to_chord(centre, melody_notes, first_chord, reach=3)

    plan = _plan_sentence(motif, r, density)
    all_notes: list[tuple[int, int]] = []
    phrase_start = cur_idx
    for bar in range(min(bars, 4)):
        bar_plan = plan[bar]
        if bar_plan is None:
            continue
        start_row = bar * ROWS_PER_BAR
        chord = chord_at(chord_timeline, start_row, chord_notes)
        target_pc = None
        if bar_plan.get("cadence"):
            root = chord[0] % 12
            # Answer phrases land on the root; questions on the fifth or third.
            target_pc = root if is_answer else (chord[2] % 12 if len(chord) > 2 and r.random() < 0.6 else chord[1 % len(chord)] % 12)
            entry = cur_idx                   # the cadence falls from where the phrase is
        else:
            # A sequence is the statement's shape transposed: start each bar
            # from the phrase's starting pitch plus the bar's shift, not from
            # wherever the previous bar happened to end — a falling motif
            # would otherwise drift down a bar at a time and peak in bar one.
            entry = phrase_start
        bar_notes, cur_idx = _realize_bar(bar_plan, melody_notes, chord, start_row, entry, rows, target_pc,
                                          key_root=scale_notes[0] % 12)
        all_notes.extend(bar_notes)

    # Keep the climax late: if the highest note still sits in bar 1 (chord
    # snapping can undo a step), lift bars 2-3 until they clear it. Not for
    # a period, whose third bar is the first bar again on purpose.
    if all_notes and len(all_notes) > 4 and motif.get("form") != "period":
        bar1 = [n for r, n in all_notes if r < ROWS_PER_BAR]
        mid = [n for r, n in all_notes if ROWS_PER_BAR <= r < 3 * ROWS_PER_BAR]
        if bar1 and mid and max(bar1) >= max(mid):
            need = melody_notes.index(max(bar1)) - melody_notes.index(max(mid)) + 1 \
                if max(bar1) in melody_notes and max(mid) in melody_notes else 2
            lifted = []
            for row, note in all_notes:
                if ROWS_PER_BAR <= row < 3 * ROWS_PER_BAR and note in melody_notes:
                    k = min(len(melody_notes) - 1, melody_notes.index(note) + need)
                    note = melody_notes[k]
                lifted.append((row, note))
            all_notes = lifted

    seen = {}
    for row, note in all_notes:
        seen[row] = note
    return sorted(seen.items())


def add_melody_cuts(notes: list[tuple[int, int]], rows: int,
                    max_sustain: int = 8) -> list[tuple[int, int]]:
    """Add note-cut events so notes don't ring indefinitely.

    Each note gets a cut after max_sustain rows, unless the next note
    arrives sooner (which naturally replaces it).
    """
    if not notes:
        return notes
    result = []
    sorted_notes = sorted(notes, key=lambda x: x[0])
    for i, (row, midi_note) in enumerate(sorted_notes):
        result.append((row, midi_note))
        # Find when the next note starts
        next_row = sorted_notes[i + 1][0] if i + 1 < len(sorted_notes) else rows
        gap = next_row - row
        # Only add cut if the note would ring longer than max_sustain
        if gap > max_sustain:
            cut_row = row + max_sustain
            if cut_row < rows:
                result.append((cut_row, -1))
    return result


def generate_melody(scale_notes: list[int], chord_notes: list[int],
                    rows: int, density: float = 0.5,
                    motif: dict | None = None,
                    is_answer: bool = False,
                    phrased: bool = True,
                    chord_timeline=None,
                    rng: random.Random | None = None,
                    register: float = 0.5) -> list[tuple[int, int]]:
    """Generate a melody line. Returns [(row, midi_note), ...]."""
    if phrased:
        notes = _generate_melody_phrased(
            scale_notes, chord_notes, rows, density, motif, is_answer,
            chord_timeline=chord_timeline, rng=rng, register=register)
    else:
        notes = _generate_melody_simple(scale_notes, chord_notes, rows, density)
    return add_melody_cuts(min_note_length(notes), rows, max_sustain=16)


def min_note_length(notes: list[tuple[int, int]], rows: int = 2) -> list[tuple[int, int]]:
    """Drop any note that would be cut off within `rows` by the next one.

    A rhythm template's push a sixteenth before the beat was followed by
    the beat note itself, so the lead played a one-row blip into the
    downbeat: on a sustained voice that is an attack, a release and another
    attack inside 100 ms, heard as a stutter. A push replaces the downbeat
    in real playing, so the later note goes and the push holds.
    """
    notes = sorted(notes)
    out = []
    for i, (row, note) in enumerate(notes):
        if out and row - out[-1][0] < rows:
            continue
        out.append((row, note))
    return out


def generate_counter_melody(scale_notes: list[int], chord_notes: list[int],
                             melody_notes_list: list[tuple[int, int]],
                             rows: int, rng: random.Random | None = None) -> list[tuple[int, int]]:
    """
    Generate a counter-melody that fills gaps in the main melody.

    Moves in contrary motion and plays in the rests between melody phrases.
    Draws from `rng` (the melody's stream): how many numbers it draws depends
    on the melody, so on the global stream it shifted every part after it.
    """
    random_ = rng or random
    melody_range = [n for n in scale_notes if 60 <= n <= 83]
    if not melody_range:
        melody_range = [n + 12 for n in scale_notes if 48 <= n <= 71]
    if not melody_range:
        return []

    chord_in_range = [n for n in chord_notes if n in melody_range]

    # Find gaps in the melody (rows where melody is silent)
    melody_rows = {row for row, _ in melody_notes_list}
    # Extend occupied rows to include duration estimates
    occupied = set()
    sorted_melody = sorted(melody_notes_list, key=lambda x: x[0])
    for i, (row, _) in enumerate(sorted_melody):
        next_row = sorted_melody[i + 1][0] if i + 1 < len(sorted_melody) else rows
        duration = min(next_row - row, 8)  # Assume max 8 row duration
        for r in range(row, row + duration):
            occupied.add(r)

    # Generate counter notes in the gaps
    notes = []
    # Start from a chord tone in the upper register
    if chord_in_range:
        current = random_.choice(chord_in_range)
    else:
        current = melody_range[len(melody_range) // 2]

    row = 0
    while row < rows:
        if row not in occupied and random_.random() < 0.4:
            # Find direction: move opposite to where melody was heading
            nearest_melody = None
            for mr, mn in sorted_melody:
                if mr > row:
                    nearest_melody = mn
                    break

            idx = melody_range.index(current) if current in melody_range else len(melody_range) // 2

            if nearest_melody and nearest_melody in melody_range:
                melody_idx = melody_range.index(nearest_melody)
                # Contrary motion: if melody goes up, counter goes down
                if melody_idx > idx:
                    step = random_.choice([-1, -2])
                else:
                    step = random_.choice([1, 2])
            else:
                step = random_.choice([-1, 0, 1])

            new_idx = max(0, min(len(melody_range) - 1, idx + step))
            current = melody_range[new_idx]

            # Snap to chord tone occasionally
            if random_.random() < 0.3 and chord_in_range:
                closest = min(chord_in_range,
                             key=lambda n: abs(melody_range.index(n) - new_idx)
                             if n in melody_range else 999)
                if closest in melody_range:
                    current = closest

            notes.append((row, current))
            row += random_.choice([4, 4, 8])
        else:
            row += 2

    return notes
