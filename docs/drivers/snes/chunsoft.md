# Chunsoft

Chunsoft's sound driver, in Dragon Quest V.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Dragon Quest V | Koichi Sugiyama | 50 (50) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 200 Hz, key-ons anywhere in a tick (42 songs); 200 Hz, on its ticks (6); none found (2) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 99 % (1.0 writes a note) |
| Pitch writes | 0.0 a note (90 %: 8.1) |
| Pitch modulation | in 0 of 50 songs |
| Noise | in 0 of 50 songs |
| Echo | 80 ms, feedback 0.09 (46 songs); 80 ms, feedback 0.0 (4) |
| Echo volume | 0.16 (46 songs); 0.5 (4) |
| Echo sides inverted | in 46 of 50 songs |
| Echo filter at DC | 1.03 (50 songs) |
| Master volume | 92 (46 songs); 77 (4) |
| Density | 167 notes in a song's first minute; a note 0.28 s |
<!-- end generated -->

- **Clock**: 200 Hz, key-ons anywhere in its ticks: modules use 100 rows a
  second.
- **Envelopes**: ADSR at key-on, and one envelope write as each note sounds.
- **Pitch**: hardly any pitch writes.
- **Echo**: 80 ms with little feedback (0.09), its sides of opposite signs in
  46 of 50 songs (a widening trick, as Capcom's), through a filter that
  boosts a little (1.03 at DC).
- **Density**: the sparsest driver here, 167 notes in a song's first minute, a note
  0.28 s.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 50 | 0.97 (0.93) | 0.45 (0.99) | 1.01 (0.98-1.06) | 1.00 (0.99) |
<!-- end generated -->

## The converter

Nothing of its own: surround for the opposite signs on voices near the
middle, as for Capcom's.

## For generation

Sparse, held, orchestral lines in a wide, short echo; little vibrato.

## Open

- Mystical Realm of the Faeries: voice 5 the wrong tone (0.43) at 1.76 of
  its level; Intermezzo's voice 5 (0.78, at 0.62).
