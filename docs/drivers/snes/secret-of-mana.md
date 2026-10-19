# Square: Secret of Mana's

The driver of Secret of Mana, named for its game here.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Secret of Mana | Hiroki Kikuta | 69 (68) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 222 Hz, on its ticks (35 songs); 222 Hz, key-ons anywhere in a tick (28); none found (5) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 0 % (0.0 writes a note) |
| Pitch writes | 0.2 a note (90 %: 5.9) |
| Pitch modulation | in 8 of 69 songs |
| Noise | in 0 of 69 songs |
| Echo | 48 ms, feedback 0.0 (15 songs); 96 ms, feedback 0.0 (11); 176 ms, feedback 0.79 (10); 176 ms, feedback 0.72 (6) |
| Echo volume | 0.5 (43 songs); 0.25 (14) |
| Echo sides inverted | in 0 of 69 songs |
| Echo filter at DC | 0.99 (65 songs); 1.0 (4) |
| Master volume | 127 (69 songs) |
| Density | 504 notes in a song's first minute; a note 0.16 s |
<!-- end generated -->

- **Clock**: key-ons on its ticks in about half the songs; modules use 100
  rows a second.
- **Pitch**: few pitch writes in most voices, heavy vibrato in some (Fond
  Memories' voices write 150 to 370 times in 30 s, 2 to 5 cents deep).
- **Pitch modulation**: The Oracle on five voice pairs, some at 17 to 34 Hz;
  the Flammie jingles.
- **Echo**: chosen per song, and of two kinds: short and dry (48 or 96 ms,
  no feedback) or long and ringing (176 ms at 0.72 to 0.79, 96 ms at 0.81).
  A pass-through filter; all eight voices send in 31 songs.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 68 | 0.93 (0.76) | 0.76 (1.39) | 0.97 (0.94-1.04) | 0.99 (0.97) |
<!-- end generated -->

## The converter

Volumes side for side, the master volume as global volume (an IT player
pans linearly: these songs played at half their level before). The 176 ms
echo is 17.6 rows at 100 a second, so on a held, looped tone the repeats
stack as the hardware's only by chance: a held note's echo can come out
stronger or weaker than the original's, right on average (Fond Memories'
shimmer is this echo beating against the notes).

## For generation

A long echo with strong feedback under slow, held lines, a short dry one
under busy ones; vibrato reserved for a few voices. The `mana` pack's notes
average the two kinds of echo into one ([the packs table](README.md#the-style-packs-against-the-drivers-in-play)).

## Open

- 9a Flammie Coming (a pitch-modulated jingle): 2.0 dB off (14.5 before
  the twenty-game fixes), voices 2 and 3 at 0.49 and 0.61 of their level.
