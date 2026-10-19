# Square: Final Fantasy IV's

Square's driver in Final Fantasy IV, named for its game here. It shares
0.02 of its code at most with any other driver here, AKAO's
([akao.md](akao.md)) included: not an earlier AKAO in its code.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Final Fantasy IV | Nobuo Uematsu | 65 (65) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 222 Hz, key-ons anywhere in a tick (40 songs); 222 Hz, on its ticks (21); 62 Hz, key-ons anywhere in a tick (2) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 100 % (2.0 writes a note) |
| Pitch writes | 0.3 a note (90 %: 2.3) |
| Pitch modulation | in 0 of 65 songs |
| Noise | in 3 of 65 songs |
| Echo | 80 ms, feedback 0.55 (61 songs); 80 ms, feedback 0.78 (2); 80 ms, feedback 0.0 (1); 80 ms, feedback 0.66 (1) |
| Echo volume | 0.27 (62 songs); 0.0 (1) |
| Echo sides inverted | in 0 of 65 songs |
| Echo filter at DC | 0.99 (63 songs); 1.0 (2) |
| Master volume | 64 (65 songs) |
| Density | 521 notes in a song's first minute; a note 0.18 s |
<!-- end generated -->

- **Clock**: 222 Hz (as Secret of Mana's), key-ons anywhere in its ticks
  in most songs: modules use 100 rows a second.
- **Envelopes**: ADSR at key-on, and two envelope writes as each note
  sounds.
- **Echo**: 80 ms at 0.55 in nearly every song, at 0.27 of the voices; the
  master at 64; noise in 3 songs.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 65 | 0.96 (0.90) | 0.38 (0.55) | 1.00 (0.97-1.03) | 1.00 (0.99) |
<!-- end generated -->

## The converter

Nothing of its own.

## For generation

One echo for the whole game, 80 ms at 0.55, as FFVI's chooses 80 ms in
every song.

## Open

Nothing found yet (the worst song, Gysahl's Whistle, 1.2 dB off).
