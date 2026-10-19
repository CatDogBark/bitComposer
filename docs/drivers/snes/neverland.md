# Neverland

Neverland's sound driver, in Lufia II.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Lufia II | Yasunori Shiono | 63 (62) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 64 Hz, key-ons anywhere in a tick (41 songs); 64 Hz, on its ticks (5); 116 Hz, key-ons anywhere in a tick (2) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 0 % (0.0 writes a note) |
| Pitch writes | 0.0 a note (90 %: 3.5) |
| Pitch modulation | in 0 of 63 songs |
| Noise | in 0 of 63 songs |
| Echo | 80 ms, feedback 0.81 (22 songs); 64 ms, feedback 0.81 (14); 80 ms, feedback 0.56 (6); 48 ms, feedback 0.56 (3) |
| Echo volume | 0.18 (31 songs); 0.16 (12) |
| Echo sides inverted | in 0 of 63 songs |
| Echo filter at DC | 0.99 (63 songs) |
| Master volume | 112 (63 songs) |
| Density | 491 notes in a song's first minute; a note 0.21 s |
<!-- end generated -->

- **Clock**: 64 Hz, key-ons anywhere in its ticks in most songs: modules use
  100 rows a second.
- **Envelopes**: the instrument's ADSR at key-on, left alone.
- **Pitch**: hardly any pitch writes.
- **Echo**: long and ringing (64 to 80 ms at 0.81 feedback in 36 songs) but
  quiet (0.16 to 0.18 of the voices).

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 62 | 0.95 (0.86) | 0.48 (0.93) | 1.01 (0.98-1.04) | 1.00 (0.99) |
<!-- end generated -->

## The converter

Nothing of its own.

## For generation

A long, ringing echo kept low under plain, steady notes.

## Open

Nothing found yet.
