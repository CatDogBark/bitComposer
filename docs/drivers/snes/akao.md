# Square: AKAO

Square's sound driver, known as AKAO.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Final Fantasy VI | Nobuo Uematsu | 82 (79) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 205 Hz, key-ons anywhere in a tick (49 songs); 205 Hz, on its ticks (28); none found (3) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 0 % (0.0 writes a note) |
| Pitch writes | 3.2 a note (90 %: 23.8) |
| Pitch modulation | in 11 of 82 songs |
| Noise | in 4 of 82 songs |
| Echo | 80 ms, feedback 0.78 (42 songs); 80 ms, feedback 0.55 (27); 80 ms, feedback 0.62 (7); 80 ms, feedback 0.47 (2) |
| Echo volume | 0.2 (68 songs); 0.27 (5) |
| Echo sides inverted | in 0 of 82 songs |
| Echo filter at DC | 0.99 (78 songs); 1.0 (2) |
| Master volume | 63 (82 songs) |
| Density | 655 notes in a song's first minute; a note 0.17 s |
<!-- end generated -->

- **Clock**: key-ons land anywhere in a tick in most songs, so modules use
  IT's finest grid, 100 rows a second.
- **Envelopes**: the instrument's ADSR at key-on, left alone while it sounds.
- **Pitch**: vibrato and slides.
- **Pitch modulation**, for effects and timbres: The Phantom Train's steam is
  a 667 Hz tone whose pitch a noise voice shakes into a hiss; New
  Continent's are FM timbres (287 notes, 28 recordings).
- **Echo**: 80 ms in every song, feedback set per song. The filter is a
  single tap seven samples back: it passes everything, but each trip round
  the echo is seven samples longer than the delay. Four to seven voices send.
- **Master volume**: the voices play loud and the master halves them; the
  echo is not halved (the SNES chip leaves it out of the master volume).

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 79 | 0.98 (0.93) | 0.40 (0.74) | 0.99 (0.95-1.02) | 1.00 (0.99) |
<!-- end generated -->

## The converter

Pitch-modulated notes kept as the emulator played them; the echo raised
past the master volume; each repeat with the filter's span per trip
(without it, Dark World's held organ chords stacked a third brighter and up
to 15 % louder: heard as the organ going up in pitch); a song's end at the
tag's length and fade (rounded up to a whole pattern, Dark World's held
notes rang on past the end with their echo stacked).

## For generation

The long, strong 80 ms echo against a halved master is the sound; feedback
is chosen per song, not fixed (the `ffvi` pack's notes, read from snapshot
registers, give 0.64 everywhere: [the packs table](README.md#the-style-packs-against-the-drivers-in-play)).

## Open

- Sound-effect tracks (999 Blazing Fire voice 2, 999 Train voice 5): the
  wrong tone.
