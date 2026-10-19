# Square Soft US: Secret of Evermore's

The driver of Secret of Evermore (made by Square Soft's team in the United
States), named for its game here.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Secret of Evermore | Jeremy Soule | 72 (70) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 50 Hz, on its ticks (52 songs); 50 Hz, key-ons anywhere in a tick (14); none found (6) |
| Envelopes | ADSR at key-on: 0 % of notes; rewritten as they sound: 100 % (9.5 writes a note) |
| Pitch writes | 1.3 a note (90 %: 32.5) |
| Pitch modulation | in 0 of 72 songs |
| Noise | in 41 of 72 songs |
| Echo | 80 ms, feedback 0.16 (58 songs); 0 ms, feedback 0.0 (12); 48 ms, feedback 0.08 (2) |
| Echo volume | 0.39 (58 songs); 0.0 (12) |
| Echo sides inverted | in 0 of 72 songs |
| Echo filter at DC | -1.25 (58 songs); 0.0 (12) |
| Master volume | 127 (72 songs) |
| Density | 297 notes in a song's first minute; a note 0.27 s |
<!-- end generated -->

- **Clock**: key-ons on its ticks: modules run on the driver's own clock, 50
  rows a second.
- **Envelopes**: shaped by the driver itself. Notes key on with a GAIN
  setting, not ADSR, and every note's envelope is rewritten as it sounds
  (GAIN ramps and holds), the driver reading the level back to know when to
  switch.
- **Samples**: the driver writes a voice's directory entry just before
  keying it; the snapshot's directory holds placeholders.
- **Noise**: wind and ambience, often as steady beds. Bright, noisy samples
  played well below their rate (the wind at 0.12 of it).
- **Echo**: 80 ms with a little feedback and a strongly shaped filter (taps
  -8, -40, -80, -104, -120, 112, 80, 0); none in a sixth of the songs.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 70 | 0.93 (0.52) | 0.63 (1.31) | 0.99 (0.92-1.02) | 0.99 (0.97) |
<!-- end generated -->

## The converter

Samples found by the addresses the SNES chip read at each key-on; rewritten
envelopes carried whole in the volume column (the wind was silent until
then: its key-on level, 16 of 2047, rounds to nothing in an IT envelope),
their steps on the SNES chip's shared rate counter (counted from each note's
start, it drifted a step on most switches); samples softened as the SNES
chip's Gaussian interpolation softens them (the wind was three times too
strong above its own top). The low tenth percentile of contour is the
steady beds, whose gaps are small.

## For generation

The envelope is the composer's instrument here, not the sample's: swells and
holds written note by note. The `evermore` pack's notes (from snapshot
registers) give the echo off in 47 of 72; in play it is on in 60
([the packs table](README.md#the-style-packs-against-the-drivers-in-play)).

## Open

- Single voices at 0.2 to 0.3 of their level, 20 to 58 dB off over time,
  though their tone is right: Bugmuck Tar Pits (voice 3), The Professor's
  Room (2), Pirates of Crustacia (5), The Seashore (1), Dark Forest (1, 7),
  Underground Path (5).
- A hi-hat played faster than the output rate (Regal Castle, voice 2) loses
  its aliasing ([known limits](README.md#known-limits)).
