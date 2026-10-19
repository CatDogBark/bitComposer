# Square: AKAO

Square's sound driver, known as AKAO.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Chrono Trigger | Yasunori Mitsuda, Nobuo Uematsu, Noriko Matsueda | 74 (74) |
| Final Fantasy VI | Nobuo Uematsu | 82 (82) |
| Romancing SaGa 3 | Kenji Ito | 74 (74) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 205 Hz, key-ons anywhere in a tick (108 songs); 205 Hz, on its ticks (42); 190 Hz, key-ons anywhere in a tick (37) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 0 % (0.0 writes a note) |
| Pitch writes | 0.9 a note (90 %: 17.7) |
| Pitch modulation | in 29 of 230 songs |
| Noise | in 10 of 230 songs |
| Echo | 80 ms, feedback 0.78 (48 songs); 80 ms, feedback 0.55 (30); 80 ms, feedback 0.62 (29); 80 ms, feedback 0.47 (12) |
| Echo volume | 0.2 (85 songs); 0.16 (48) |
| Echo sides inverted | in 0 of 230 songs |
| Echo filter at DC | 0.99 (221 songs); -0.01 (5) |
| Master volume | 64 (147 songs); 63 (82) |
| Density | 553 notes in a song's first minute; a note 0.19 s |
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
| 230 | 0.97 (0.85) | 0.48 (0.95) | 0.99 (0.96-1.03) | 1.00 (0.98) |
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
