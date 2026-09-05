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
    [0, 4, 12, 14, 16],               # Gap then flurry
]

# Contour shapes: relative direction for each note in a motif
# Values are scale steps from starting note — wider intervals = more melodic movement
CONTOURS = {
    # Cumulative: each value is a step from current position
    "arch":        [0, 2, 2, -2, -2],       # Rise then fall
    "descent":     [0, -1, -2, -2, 1],      # Stepwise fall, partial recover
    "climb":       [0, 1, 2, 2, -1],        # Gradual rise, step back
    "valley":      [0, -2, -2, 2, 2],       # Dip then return
    "leap_return": [0, 4, -1, -1, -2],      # Big jump, walk back down
    "zigzag":      [0, 3, -4, 3, -2],       # Alternating leaps
    "cascade":     [0, -3, 2, -3, 1],       # Falling with rebounds
    "soar":        [0, 2, 3, 1, -2],        # Big climb then relax
}


def generate_motif(length: int = 4) -> dict:
    """Generate a rhythmic+melodic motif template."""
    rhythm = random.choice(RHYTHM_TEMPLATES)
    # Trim or extend to match length
    if len(rhythm) > length:
        rhythm = rhythm[:length]
    elif len(rhythm) < length:
        # Add notes at end
        last = rhythm[-1]
        while len(rhythm) < length:
            last += random.choice([2, 4])
            rhythm.append(last)

    contour_name = random.choice(list(CONTOURS.keys()))
    contour = CONTOURS[contour_name]

    # Scale contour to motif length
    if len(contour) != len(rhythm):
        # Interpolate contour to match rhythm length
        scaled = []
        for i in range(len(rhythm)):
            src = i * (len(contour) - 1) / max(1, len(rhythm) - 1)
            lo = int(src)
            hi = min(lo + 1, len(contour) - 1)
            frac = src - lo
            val = contour[lo] * (1 - frac) + contour[hi] * frac
            scaled.append(round(val))
        contour = scaled

    return {
        "rhythm": rhythm,
        "contour": contour,
        "contour_name": contour_name,
    }


def vary_motif(motif: dict, amount: float = 0.3) -> dict:
    """Create a variation of a motif — small rhythmic/melodic changes."""
    rhythm = list(motif["rhythm"])
    contour = list(motif["contour"])

    for i in range(len(rhythm)):
        if random.random() < amount:
            # Slight rhythmic shift
            rhythm[i] = max(0, rhythm[i] + random.choice([-2, 0, 2]))

    for i in range(len(contour)):
        if random.random() < amount:
            contour[i] += random.choice([-1, 0, 1])

    # Keep rhythm sorted and non-negative
    rhythm.sort()
    rhythm[0] = 0

    return {"rhythm": rhythm, "contour": contour, "contour_name": motif["contour_name"]}


def _realize_motif(motif: dict, scale_notes: list[int],
                   chord_notes: list[int], start_row: int,
                   start_note_idx: int, resolve_to_chord: bool = False,
                   rows: int = 64) -> tuple[list[tuple[int, int]], int]:
    """
    Realize a motif into actual notes.

    Returns (note_list, ending_note_idx) where note_list is [(row, midi_note), ...].
    If resolve_to_chord is True, the last note snaps to a chord tone.
    """
    melody_notes = [n for n in scale_notes if 60 <= n <= 83]
    if not melody_notes:
        melody_notes = [n + 12 for n in scale_notes if 48 <= n <= 71]
    if not melody_notes:
        return [], start_note_idx

    chord_in_range = [n for n in chord_notes if n in melody_notes]

    notes = []
    current_idx = max(0, min(len(melody_notes) - 1, start_note_idx))

    for i, (row_offset, direction) in enumerate(zip(motif["rhythm"], motif["contour"])):
        row = start_row + row_offset
        if row >= rows:
            break

        # Contour is cumulative — each step moves from current position
        target_idx = current_idx + direction
        target_idx = max(0, min(len(melody_notes) - 1, target_idx))

        # If we hit a boundary and would repeat the same note, nudge the other way
        if target_idx == current_idx and direction != 0:
            nudge = 1 if current_idx < len(melody_notes) // 2 else -1
            target_idx = max(0, min(len(melody_notes) - 1, current_idx + nudge))

        # Last note: resolve to chord tone if requested
        if resolve_to_chord and i == len(motif["rhythm"]) - 1 and chord_in_range:
            # Find nearest chord tone
            closest = min(chord_in_range, key=lambda n: abs(melody_notes.index(n) - target_idx)
                         if n in melody_notes else 999)
            if closest in melody_notes:
                target_idx = melody_notes.index(closest)

        current_idx = target_idx
        notes.append((row, melody_notes[current_idx]))

    return notes, current_idx


def _generate_melody_simple(scale_notes: list[int], chord_notes: list[int],
                            rows: int, density: float = 0.5) -> list[tuple[int, int]]:
    """Generate a simple random-walk melody. Returns [(row, midi_note), ...]."""
    notes = []
    melody_notes = [n for n in scale_notes if 60 <= n <= 83]
    if not melody_notes:
        melody_notes = [n + 12 for n in scale_notes if 48 <= n <= 71]
    if not melody_notes:
        return notes

    chord_in_range = [n for n in chord_notes if n in melody_notes]
    current = random.choice(chord_in_range) if chord_in_range else random.choice(melody_notes)

    row = 0
    while row < rows:
        if random.random() < density:
            idx = melody_notes.index(current) if current in melody_notes else 0
            step = random.choices([-2, -1, 0, 1, 2], weights=[10, 25, 15, 25, 10], k=1)[0]
            new_idx = max(0, min(len(melody_notes) - 1, idx + step))
            current = melody_notes[new_idx]
            if random.random() < 0.2 and chord_in_range:
                current = random.choice(chord_in_range)
            duration = random.choice([2, 4, 4, 4, 8])
            notes.append((row, current))
            row += duration
        else:
            row += random.choice([2, 4])

    return notes


def _generate_melody_phrased(scale_notes: list[int], chord_notes: list[int],
                              rows: int, density: float = 0.5,
                              motif: dict | None = None,
                              is_answer: bool = False) -> list[tuple[int, int]]:
    """
    Generate a melody using motif-based phrase structure.

    Uses question-answer phrasing: first half is the "question" (ends on tension),
    second half is the "answer" (resolves to chord tone).
    """
    melody_notes = [n for n in scale_notes if 60 <= n <= 83]
    if not melody_notes:
        melody_notes = [n + 12 for n in scale_notes if 48 <= n <= 71]
    if not melody_notes:
        return []

    if motif is None:
        motif = generate_motif(length=random.choice([4, 5]))

    chord_in_range = [n for n in chord_notes if n in melody_notes]

    # Pick starting note — vary the register to avoid always landing on same note
    # Spread across the range: sometimes start high, sometimes low
    range_third = len(melody_notes) // 3
    register = random.choice(["low", "mid", "high"])
    if register == "low":
        candidates = melody_notes[:range_third + 1]
    elif register == "high":
        candidates = melody_notes[-(range_third + 1):]
    else:
        candidates = melody_notes[range_third:2 * range_third + 1]

    # Prefer chord tones within the chosen register
    register_chord = [n for n in chord_in_range if n in candidates]
    if register_chord:
        start_note = random.choice(register_chord)
    elif candidates:
        start_note = random.choice(candidates)
    else:
        start_note = random.choice(melody_notes)
    start_idx = melody_notes.index(start_note)

    # State the motif once per bar rather than once per half-phrase.
    #
    # The rhythm templates are commented as spanning a 32-row half-phrase, but
    # their offsets stop at 16 — they are one-bar figures. Placing one in each
    # 32-row half therefore left the back bar of each half silent, and the
    # melody averaged 1.7 notes per bar with two-bar holes in the middle.
    #
    # Four bars gives the classic antecedent/consequent shape: statement,
    # variation, statement, variation resolving to a chord tone.
    all_notes = []
    bars = max(1, rows // ROWS_PER_BAR)
    cur_idx = start_idx

    for bar in range(bars):
        is_last = bar == bars - 1

        # Continuation bars are the ones that thin out first, so a low-density
        # section keeps the original sparse call-and-response feel.
        if bar % 2 == 1 and not is_last and random.random() > density + 0.3:
            continue

        if bar == 0:
            bar_motif = motif if not is_answer else vary_motif(motif, 0.2)
        else:
            # Odd bars answer the statement, so they vary more.
            bar_motif = vary_motif(motif, 0.35 if bar % 2 else 0.2)

        bar_notes, cur_idx = _realize_motif(
            bar_motif, scale_notes, chord_notes,
            start_row=bar * ROWS_PER_BAR, start_note_idx=cur_idx,
            resolve_to_chord=is_last, rows=rows,
        )
        all_notes.extend(bar_notes)

    # A motif offset of 16 lands on the next bar's downbeat, where that bar's
    # own opening note replaces it. Drop the duplicates so note counts and
    # cut placement stay honest.
    seen_rows = {}
    for row, note in all_notes:
        seen_rows[row] = note
    all_notes = sorted(seen_rows.items())

    # Add passing tones between phrases based on density
    if density > 0.5 and len(all_notes) > 0:
        # Fill sparse gaps with occasional passing notes
        filled = list(all_notes)
        for i in range(len(all_notes) - 1):
            row_a, note_a = all_notes[i]
            row_b, note_b = all_notes[i + 1]
            gap_rows = row_b - row_a
            if gap_rows >= 8 and random.random() < density - 0.3:
                # Insert a passing note halfway
                mid_row = row_a + gap_rows // 2
                if note_a in melody_notes and note_b in melody_notes:
                    idx_a = melody_notes.index(note_a)
                    idx_b = melody_notes.index(note_b)
                    mid_idx = (idx_a + idx_b) // 2
                    mid_idx = max(0, min(len(melody_notes) - 1, mid_idx))
                    filled.append((mid_row, melody_notes[mid_idx]))
        all_notes = sorted(filled, key=lambda x: x[0])

    return all_notes


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
                    phrased: bool = True) -> list[tuple[int, int]]:
    """Generate a melody line. Returns [(row, midi_note), ...]."""
    if phrased:
        notes = _generate_melody_phrased(
            scale_notes, chord_notes, rows, density, motif, is_answer)
    else:
        notes = _generate_melody_simple(scale_notes, chord_notes, rows, density)
    return add_melody_cuts(notes, rows, max_sustain=16)


def generate_counter_melody(scale_notes: list[int], chord_notes: list[int],
                             melody_notes_list: list[tuple[int, int]],
                             rows: int) -> list[tuple[int, int]]:
    """
    Generate a counter-melody that fills gaps in the main melody.

    Moves in contrary motion and plays in the rests between melody phrases.
    """
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
        current = random.choice(chord_in_range)
    else:
        current = melody_range[len(melody_range) // 2]

    row = 0
    while row < rows:
        if row not in occupied and random.random() < 0.4:
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
                    step = random.choice([-1, -2])
                else:
                    step = random.choice([1, 2])
            else:
                step = random.choice([-1, 0, 1])

            new_idx = max(0, min(len(melody_range) - 1, idx + step))
            current = melody_range[new_idx]

            # Snap to chord tone occasionally
            if random.random() < 0.3 and chord_in_range:
                closest = min(chord_in_range,
                             key=lambda n: abs(melody_range.index(n) - new_idx)
                             if n in melody_range else 999)
                if closest in melody_range:
                    current = closest

            notes.append((row, current))
            row += random.choice([4, 4, 8])
        else:
            row += 2

    return notes
