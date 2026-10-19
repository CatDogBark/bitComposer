# Capcom: Mega Man X's

Capcom's driver in Mega Man X. Super Ghouls'n Ghosts runs another, sharing
almost none of its code ([super-ghouls-ghosts.md](super-ghouls-ghosts.md)).

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Mega Man X | "Setsuo, Tomozou, Sato, Yuko, Kir" (cut off) | 35 (35) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 125 Hz, key-ons anywhere in a tick (31 songs); 125 Hz, on its ticks (4) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 100 % (2.2 writes a note) |
| Pitch writes | 2.9 a note (90 %: 8.7) |
| Pitch modulation | in 0 of 35 songs |
| Noise | in 0 of 35 songs |
| Echo | 48 ms, feedback 0.53 (35 songs) |
| Echo volume | 0.56 (35 songs) |
| Echo sides inverted | in 35 of 35 songs |
| Echo filter at DC | 0.1 (35 songs) |
| Master volume | 92 (35 songs) |
| Density | 1261 notes in a song's first minute; a note 0.19 s |
<!-- end generated -->

- **Clock**: 125 Hz is faster than IT can run (102 ticks a second at most),
  so modules use 100 rows a second.
- **Envelopes**: every note keys on with a held ADSR and is released with a
  GAIN fade a moment before the next, never with a key-off.
- **Arrangement**: the score doubles its melody with a delayed copy on
  another voice, panned the other way (Spark Mandrill: 0.12 s behind).
- **Echo**: the same in every song, the sides of opposite signs (a widening
  trick), and a band-pass filter (taps 52, 51, 0, -39, -27, 1, -4, -21:
  0.10 at DC, about 1 from 2 to 8 kHz).
- **Density**: the busiest of the four, and the most samples and
  instruments a converted song (42 and 64).

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 35 | 0.94 (0.86) | 0.46 (0.83) | 0.98 (0.96-1.01) | 1.00 (0.98) |
<!-- end generated -->

## The converter

The GAIN releases, carried in the volume column (without them every note
rang on into the next, and Spark Mandrill's melody blurred into its delayed
copy: from 0.54 to 0.94 voice by voice); echo repeats from copies coloured
by the filter (a full-range copy at the echo's level sounded like a second
instrument); surround for the opposite signs, on voices near the middle
(surround plays centred).

## For generation

Short notes, dense; the thin, bright, wide echo is part of the sound;
staccato comes from the driver's release, not the samples; the melody
doubled late on the other side. The `megamanx` pack has the echo right and
not the release or the doubling ([the packs table](README.md#the-style-packs-against-the-drivers-in-play)).

## Open

Nothing found yet.
