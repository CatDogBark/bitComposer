# Hudson

Hudson's sound driver, in Super Bomberman 4.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Super Bomberman 4 | Jun Chiki Chikuma | 26 (26) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 250 Hz, key-ons anywhere in a tick (19 songs); 62 Hz, key-ons anywhere in a tick (3); 250 Hz, on its ticks (2) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 100 % (3.0 writes a note) |
| Pitch writes | 2.3 a note (90 %: 14.4) |
| Pitch modulation | in 0 of 26 songs |
| Noise | in 0 of 26 songs |
| Echo | 16 ms, feedback 0.0 (5 songs); 16 ms, feedback 0.31 (2); 112 ms, feedback 0.81 (1); 128 ms, feedback 0.31 (1) |
| Echo volume | 0.27 (8 songs); 0.0 (6) |
| Echo sides inverted | in 0 of 26 songs |
| Echo filter at DC | 0.99 (16 songs); 1.0 (10) |
| Master volume | 96 (26 songs) |
| Density | 1183 notes in a song's first minute; a note 0.11 s |
<!-- end generated -->

- **Clock**: 250 Hz (62 in three songs), key-ons anywhere in its ticks:
  modules use 100 rows a second.
- **Envelopes**: ADSR at key-on, rewritten as notes sound (3.0 writes a note).
- **Echo**: set per song, 16 to 128 ms, off in six.
- **Density**: 1183 notes in a song's first minute, a note 0.11 s.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 26 | 0.97 (0.88) | 0.38 (0.93) | 0.99 (0.96-1.01) | 0.99 (0.97) |
<!-- end generated -->

## The converter

Nothing of its own. Its songs showed a measuring fault instead: a
snapshot's echo buffer holds the echo of what played before it, and every
voice alone played that tail (six silent voices measured alike); a voice
alone is now measured without it.

## For generation

Fast and busy, the echo chosen song by song.

## Open

Nothing found yet.
