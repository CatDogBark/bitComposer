# Konami

Konami's own sound driver, in Axelay and Contra III (the two share 0.71 of
their driver code). Konami's Super Castlevania IV runs Nintendo's N-SPC
instead ([n-spc.md](n-spc.md)).

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Axelay | Taro Kudou, M. C. Ada | 21 (21) |
| Contra III: The Alien Wars | "Miki Yanagisawa, Masanori Adachi" (cut off) | 15 (15) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 250 Hz, key-ons anywhere in a tick (30 songs); 250 Hz, on its ticks (5); none found (1) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 0 % (0.0 writes a note) |
| Pitch writes | 2.6 a note (90 %: 21.6) |
| Pitch modulation | in 0 of 36 songs |
| Noise | in 0 of 36 songs |
| Echo | 80 ms, feedback 0.55 (8 songs); 80 ms, feedback 0.47 (7); 80 ms, feedback 0.66 (6); 80 ms, feedback 0.39 (3) |
| Echo volume | 0.62 (8 songs); 0.55 (4) |
| Echo sides inverted | in 0 of 36 songs |
| Echo filter at DC | 1.0 (36 songs) |
| Master volume | 127 (36 songs) |
| Density | 1168 notes in a song's first minute; a note 0.11 s |
<!-- end generated -->

- **Clock**: 250 Hz, key-ons anywhere in its ticks: modules use 100 rows a
  second.
- **Envelopes**: the instrument's ADSR at key-on, left alone.
- **Echo**: 80 ms in every song, its feedback set per song (0.39 to 0.66),
  and loud: 0.55 to 0.62 of the voices, under a master at full.
- **Density**: 1168 notes in a song's first minute, a note 0.11 s.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 36 | 0.95 (0.87) | 0.55 (0.96) | 0.99 (0.94-1.03) | 0.99 (0.97) |
<!-- end generated -->

## The converter

Nothing of its own.

## For generation

Fast, short notes in a strong 80 ms echo, its feedback chosen song by
song.

## Open

- Axelay's The Moment of Rest: 2.1 dB off, at 0.75 of its level.
