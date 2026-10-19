# Rare

Rare's sound driver, in Donkey Kong Country 2.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Donkey Kong Country | Dave Wise, Eveline Fischer, Robin Beanland | 29 (29) |
| Donkey Kong Country 2 | Dave Wise | 109 (109) |
| Donkey Kong Country 3 | Eveline Fischer, Dave Wise | 77 (77) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 80 Hz, on its ticks (208 songs); 80 Hz, key-ons anywhere in a tick (4); 133 Hz, key-ons anywhere in a tick (2) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 0 % (0.0 writes a note) |
| Pitch writes | 0.9 a note (90 %: 3.9) |
| Pitch modulation | in 0 of 215 songs |
| Noise | in 0 of 215 songs |
| Echo | 0 ms, feedback 0.43 (65 songs); 32 ms, feedback 0.39 (16); 64 ms, feedback 0.47 (14); 64 ms, feedback 0.45 (9) |
| Echo volume | 0.25 (80 songs); 0.18 (38) |
| Echo sides inverted | in 0 of 215 songs |
| Echo filter at DC | 1.0 (92 songs); 1.12 (42) |
| Master volume | 60 (201 songs); 51 (4) |
| Density | 360 notes in a song's first minute; a note 0.14 s |
<!-- end generated -->

- **Clock**: 80 Hz, key-ons on its ticks in all but one song: modules run on
  the driver's own clock (IT runs 80 rows a second exactly).
- **Envelopes**: the instrument's ADSR at key-on, left alone.
- **Echo**: short (32 to 64 ms) with moderate feedback, set per song,
  through a filter that boosts a little (1.05 to 1.12 at DC). In 14 songs
  (Stickerbrush Symphony's, Crocodile Cacophony's, the Token Tango's) a
  delay of 0: the echo then a tone control on every voice that sends, its
  loop a sample long.
- **Volumes**: a master of 60 with voices up to 123: the loudness is in the
  voices, past IT's 64.
- **Bass**: samples played five octaves under their own rate (pitch 0x0080).

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 215 | 0.99 (0.94) | 0.38 (0.76) | 1.01 (0.98-1.04) | 0.99 (0.96) |
<!-- end generated -->

## The converter

Voices over IT's 64 under a master that leaves room: the global volume
raised and every channel's volume lowered as far (they played at half; one
song from a 5.1 dB gap to 0.2). Samples played far under their rate get
their C5Speed octaves down, so their notes land on IT's keys (a cell cannot
write C-0, and the bass fell silent in stretches). An echo of delay 0 as one
copy of each note at its own row, coloured by every trip round the loop
(left out, Stickerbrush Symphony was 1.9 dB off; now 0.4).

## For generation

Loud voices under a low master, a short echo, and deep basses played
far below their samples' rate.

## Open

- Dixie Clear (Jib Jig): voice 4 33 dB off over time at its right level.
- Player Down (In a Snow-Bound Land): voice 6 at twice its level.
- The deep bass's tone (0.86 in Dixie Clear (Snakey Chantey), voice 1): at
  a 32nd of its rate the module is brighter from 0.7 to 5.6 kHz and darker
  above, the SNES chip's interpolation and libopenmpt's resampling parting.
