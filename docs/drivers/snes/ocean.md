# Ocean

Ocean's sound driver, in Jurassic Park Part 2.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Jurassic Park Part 2 | Dean Evans, Jonathan Dunn | 16 (16) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 49 Hz, on its ticks (15 songs); none found (1) |
| Envelopes | ADSR at key-on: 0 % of notes; rewritten as they sound: 36 % (0.4 writes a note) |
| Pitch writes | 8.0 a note (90 %: 29.6) |
| Pitch modulation | in 1 of 16 songs |
| Noise | in 0 of 16 songs |
| Echo | 0 ms, feedback 0.0 (14 songs); 0 ms, feedback -0.47 (1); 0 ms, feedback 0.47 (1) |
| Echo volume | 0.0 (15 songs); 0.4 (1) |
| Echo sides inverted | in 0 of 16 songs |
| Echo filter at DC | 0.99 (14 songs); 0.1 (1) |
| Master volume | 104 (16 songs) |
| Density | 441 notes in a song's first minute; a note 0.22 s |
<!-- end generated -->

- **Clock**: 49.38 Hz (a timer of 162), key-ons on its ticks. IT cannot run
  it exactly (49.2 rows a second, up to 2 s behind over a song), so modules
  use 100 rows a second.
- **Envelopes**: GAIN at key-on (no ADSR), rewritten as a third of the notes
  sound.
- **Pitch**: many pitch writes (8 a note): slides and vibrato.
- **Echo**: none in 15 of 16 songs; pitch modulation in one.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 16 | 0.98 (0.93) | 0.38 (0.47) | 1.00 (0.99-1.02) | 1.00 (0.99) |
<!-- end generated -->

## The converter

Rows on the driver's clock lost the beat over a song until the converter
checked that IT keeps pace.

## For generation

Dry, with moving pitch.

## Open

Nothing found yet.
