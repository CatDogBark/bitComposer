# Nintendo: Pilotwings'

Nintendo's driver in Pilotwings, named for its game here. It shares only
0.05 of its code with N-SPC's ([n-spc.md](n-spc.md)), but has a note-length
table close to EarthBound's N-SPC one (33 66 80 99 against 33 66 7F 99): an
earlier driver of Nintendo's, or an early N-SPC.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Pilotwings | Soyo Oka | 21 (21) |
| Super Mario World | Koji Kondo | 66 (66) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 500 Hz, key-ons anywhere in a tick (81 songs); none found (4); 500 Hz, on its ticks (2) |
| Envelopes | ADSR at key-on: 80 % of notes; rewritten as they sound: 0 % (0.0 writes a note) |
| Pitch writes | 3.7 a note (90 %: 23.3) |
| Pitch modulation | in 0 of 87 songs |
| Noise | in 0 of 87 songs |
| Echo | 64 ms, feedback 0.84 (35 songs); 32 ms, feedback 0.75 (30); 64 ms, feedback 0.31 (16); 64 ms, feedback 0.39 (5) |
| Echo volume | 0.0 (56 songs); 0.25 (15) |
| Echo sides inverted | in 1 of 87 songs |
| Echo filter at DC | 1.03 (56 songs); 0.0 (24) |
| Master volume | 127 (86 songs); 96 (1) |
| Density | 590 notes in a song's first minute; a note 0.12 s |
<!-- end generated -->

- **Clock**: 500 Hz, key-ons anywhere in its ticks, as N-SPC's: modules use
  100 rows a second.
- **Envelopes**: ADSR at key-on for most notes, GAIN for the rest, left
  alone while they sound.
- **Echo**: 64 ms at 0.31 to 0.39 feedback in every song, through a filter
  that boosts a little (1.03 at DC); the master full.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 87 | 0.98 (0.94) | 0.42 (0.63) | 1.00 (0.99-1.02) | 0.99 (0.97) |
<!-- end generated -->

## The converter

Nothing of its own: the converter as for N-SPC's games.

## For generation

One echo for the whole game, moderate and short; vibrato and slides
(6.9 pitch writes a note).

## Open

Nothing found yet (the worst song, Bad Points, 1.6 dB off).
