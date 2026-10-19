# Capcom: Super Ghouls'n Ghosts'

Capcom's driver in Super Ghouls'n Ghosts, named for its game here. It
shares almost none of its code with Mega Man X's ([capcom.md](capcom.md)):
0.03, against 0.26 and more among N-SPC's games. Not an earlier form of it.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Super Ghouls'n Ghosts | Mari Yamaguchi | 23 (23) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 125 Hz, key-ons anywhere in a tick (14 songs); 125 Hz, on its ticks (9) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 100 % (2.0 writes a note) |
| Pitch writes | 1.7 a note (90 %: 3.6) |
| Pitch modulation | in 0 of 23 songs |
| Noise | in 0 of 23 songs |
| Echo | 0 ms, feedback 0.0 (23 songs) |
| Echo volume | 0.0 (23 songs) |
| Echo sides inverted | in 0 of 23 songs |
| Echo filter at DC | 0.99 (23 songs) |
| Master volume | 127 (23 songs) |
| Density | 579 notes in a song's first minute; a note 0.24 s |
<!-- end generated -->

- **Clock**: 125 Hz, as Mega Man X's, faster than IT can run: modules use
  100 rows a second.
- **Envelopes**: ADSR at key-on, and two envelope writes as each note sounds
  (as Mega Man X's releases).
- **Echo**: none, in any song; the master full.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 23 | 0.96 (0.89) | 0.39 (0.66) | 0.97 (0.94-1.00) | 0.99 (0.98) |
<!-- end generated -->

## The converter

Nothing of its own.

## For generation

Dry, where Mega Man X's sound is its thin, wide echo: one company, two
drivers, two sounds.

## Open

Nothing found yet.
