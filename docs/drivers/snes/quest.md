# Quest

Quest's sound driver, in Ogre Battle.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Ogre Battle | Masaharu Iwata, Hitoshi Sakimoto, Hayato Matsuo | 26 (26) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 111 Hz, on its ticks (2 songs); 127 Hz, key-ons anywhere in a tick (2); 145 Hz, key-ons anywhere in a tick (2) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 0 % (0.0 writes a note) |
| Pitch writes | 0.0 a note (90 %: 2.0) |
| Pitch modulation | in 0 of 26 songs |
| Noise | in 0 of 26 songs |
| Echo | 0 ms, feedback 0.0 (26 songs) |
| Echo volume | 0.0 (26 songs) |
| Echo sides inverted | in 0 of 26 songs |
| Echo filter at DC | 0.0 (26 songs) |
| Master volume | 96 (26 songs) |
| Density | 1509 notes in a song's first minute; a note 0.11 s |
<!-- end generated -->

- **Clock**: a timer set per song (111 to 145 Hz): modules use 100 rows a
  second.
- **Envelopes**: the instrument's ADSR at key-on, left alone.
- **Echo**: none, in any song.
- **Density**: the densest driver here, 1505 notes in a song's first minute, a note
  0.11 s.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 26 | 0.97 (0.92) | 0.36 (0.54) | 1.00 (0.99-1.02) | 1.00 (0.99) |
<!-- end generated -->

## The converter

Nothing of its own.

## For generation

Dense and dry, plain envelopes, the tempo in the timer.

## Open

Nothing found yet.
