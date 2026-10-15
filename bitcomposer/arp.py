"""
Arpeggio figures.

The arp used to be a direction — up, down, up-down or random — stepping
through the chord tones every eighth note for the whole song, one setting
per song, with random velocity jitter. That reads as a sequencer running in
the background. Game arps are *figures*: short rhythmic shapes with accents
and rests that recur with the section, climb, and leave room for the lead.

A figure is one bar of (row, degree, accent) steps. `degree` indexes a
ladder of chord tones that starts on the chord's root in octave 4 and
climbs through the chord — so 0 is the root, 1 the next chord tone up, and
for a triad 3 is the root an octave higher. Negative degrees reach below.
Steps are 16 rows to the bar; a figure can be sparser than that.
"""

import random

from .pattern import ROWS_PER_BAR

# Accent levels, as a fraction of the section's arp volume.
S, N, W = 1.0, 0.8, 0.62   # strong, normal, weak

FIGURES = {
    # name: {"steps": [(row, degree, accent), ...], "energy": (lo, hi), "climb": bool}
    "sparse_pulse": {
        "steps": [(0, 0, S), (8, 3, N)],
        "energy": (0.0, 0.55), "climb": False},
    "quarter_up": {
        "steps": [(0, 0, S), (4, 1, W), (8, 2, N), (12, 3, W)],
        "energy": (0.0, 0.7), "climb": False},
    "classic_up": {
        "steps": [(0, 0, S), (2, 1, W), (4, 2, N), (6, 3, W),
                  (8, 0, S), (10, 1, W), (12, 2, N), (14, 3, W)],
        "energy": (0.4, 1.0), "climb": True},
    "up_down": {
        "steps": [(0, 0, S), (2, 1, W), (4, 2, N), (6, 3, W),
                  (8, 2, S), (10, 1, W), (12, 0, N), (14, 1, W)],
        "energy": (0.4, 1.0), "climb": False},
    "broken_octave": {   # 1-5-8-5, the Mega Man figure
        "steps": [(0, 0, S), (2, 2, W), (4, 3, N), (6, 2, W),
                  (8, 0, S), (10, 2, W), (12, 3, N), (14, 2, W)],
        "energy": (0.5, 1.0), "climb": True},
    "pedal_bounce": {    # root pedal against the chord above it
        "steps": [(0, 0, S), (2, 3, W), (4, 0, N), (6, 4, W),
                  (8, 0, S), (10, 3, W), (12, 0, N), (14, 5, W)],
        "energy": (0.5, 1.0), "climb": False},
    "sync_push": {       # dotted-eighth push
        "steps": [(0, 0, S), (3, 2, W), (6, 3, N), (8, 0, S), (11, 2, W), (14, 3, N)],
        "energy": (0.5, 1.0), "climb": True},
    "offbeat_stabs": {   # chord tones on the "and"s, bass has the beat
        "steps": [(2, 3, N), (6, 2, N), (10, 3, S), (14, 4, N)],
        "energy": (0.5, 1.0), "climb": False},
    "gallop": {
        "steps": [(0, 0, S), (3, 0, W), (4, 2, N), (8, 0, S), (11, 0, W), (12, 3, N)],
        "energy": (0.7, 1.0), "climb": False},
    "run16": {           # sixteenth-note run over two octaves
        "steps": [(r, d, (S if r % 8 == 0 else (N if r % 4 == 0 else W)))
                  for r, d in zip(range(16), [0, 1, 2, 3, 4, 5, 4, 3, 2, 1, 0, 1, 2, 3, 4, 5])],
        "energy": (0.8, 1.0), "climb": False},
    "cascade": {         # falling from the top of the chord
        "steps": [(0, 5, S), (2, 4, W), (4, 3, N), (6, 2, W),
                  (8, 5, S), (10, 4, W), (12, 3, N), (14, 1, W)],
        "energy": (0.5, 1.0), "climb": False},
}


def pick_figures(energy_pref: str) -> dict[str, str]:
    """Choose a figure per section role for the song.

    Verse and chorus always differ, so the chorus arp is part of the hook
    rather than the same loop as everything else. The bridge gets a third
    figure; intros and outros use the sparse pulse.
    """
    if energy_pref == "chill":
        pool = ["quarter_up", "classic_up", "up_down", "pedal_bounce", "sparse_pulse"]
    elif energy_pref == "intense":
        pool = ["classic_up", "broken_octave", "sync_push", "gallop", "run16",
                "offbeat_stabs", "cascade"]
    else:
        pool = ["classic_up", "up_down", "broken_octave", "pedal_bounce", "sync_push",
                "offbeat_stabs", "cascade", "quarter_up"]
    # The chorus runs at the top of the energy curve, so its figure must be
    # one built for that; the verse and bridge can take anything in the pool.
    chorus_pool = [f for f in pool if FIGURES[f]["energy"][0] >= 0.4]
    chorus = random.choice(chorus_pool)
    rest = [f for f in pool if f != chorus]
    random.shuffle(rest)
    return {"verse": rest[0], "chorus": chorus, "bridge": rest[1] if len(rest) > 1 else rest[0],
            "intro": "sparse_pulse", "outro": "quarter_up"}


def _ladder(chord_notes: list[int], base_octave_root: int = 48) -> list[int]:
    """Chord tones from the root placed in octave 4, climbing three octaves."""
    pcs = sorted({n % 12 for n in chord_notes})
    root_pc = chord_notes[0] % 12
    pcs = pcs[pcs.index(root_pc):] + pcs[:pcs.index(root_pc)]   # start on the root
    root = base_octave_root + root_pc
    while root >= base_octave_root + 12:
        root -= 12
    ladder = []
    for octave in (-1, 0, 1, 2):
        for pc in pcs:
            n = root + ((pc - root_pc) % 12) + 12 * octave
            ladder.append(n)
    return ladder


def generate_arp(segments: list[tuple[int, int, list[int]]], figure_name: str,
                 energy: float, melody_rows: set[int] | None = None,
                 rows_per_bar: int = ROWS_PER_BAR) -> list[tuple[int, int, float]]:
    """Realise a figure over a chord timeline.

    segments is [(start_row, end_row, chord_notes), ...]. Returns
    [(row, midi_note, accent), ...]. A bar may rest at low energy (never at
    high); a climbing figure plays its even bars an octave up; and where the
    melody is busy in a bar (melody_rows carries its onsets) the figure's
    weak steps are dropped so the arp fills gaps rather than fighting the lead.
    """
    fig = FIGURES[figure_name]
    out = []
    total = segments[-1][1] if segments else 0
    bar_index = 0
    for bar_start in range(0, total, rows_per_bar):
        seg = next((s for s in segments if s[0] <= bar_start < s[1]), segments[0])
        chord = seg[2]
        ladder = _ladder(chord)
        base = len(ladder) // 4 * 1      # index of the root in octave 4
        per_octave = len(ladder) // 4
        if energy < 0.8 and random.random() > energy + 0.25:
            bar_index += 1
            continue   # this bar rests
        shift = per_octave if (fig["climb"] and bar_index % 2 == 1) else 0
        busy = False
        if melody_rows:
            onsets = sum(1 for r in melody_rows if bar_start <= r < bar_start + rows_per_bar)
            busy = onsets >= 5
        for row_off, degree, accent in fig["steps"]:
            if busy and accent == W:
                continue
            idx = base + degree + shift
            if not (0 <= idx < len(ladder)):
                continue
            row = bar_start + row_off
            if row < total:
                out.append((row, ladder[idx], accent))
        bar_index += 1
    return out
