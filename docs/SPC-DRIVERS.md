# SPC music drivers

The record of every game the SPC import has been tested against, by music
driver: who wrote the music, what the driver does with the SNES chip
(measured, not assumed), how closely the converted module matches the
original, and what is still off. It is the converter's reference, and the
start of the generator's: a driver's and a composer's habits, measured here,
are what a pack is made of (`SPC-IMPORT.md`, `VISION.md`).

A game's music driver matters more than the game. Many games share a
driver, and a driver's habits (how it keys notes, shapes envelopes, uses the
echo) are what the converter has to understand; the composer's are what the
generator can learn from.

Numbers are from 2026-10-19: all 258 songs of the four games below, the
converter as of the SNES-chip fidelity work (interpolation, envelope clock,
echo, endings). To rerun them, `tools/spc_check.py` (CONTRIBUTING.md,
"Checking the SPC converter"):

```bash
python3 tools/spc_check.py traits ~/spc traits.json          # what each driver does, per game
python3 tools/spc_check.py sweep ~/spc /tmp/sweep             # conversions against the emulator
python3 tools/spc_check.py report /tmp/sweep/results.jsonl    # the scores, by music driver
```

## The corpus

| Game | Composer (as the SPC tags credit) | Music driver | Songs (scored) |
|---|---|---|---|
| Final Fantasy VI | Nobuo Uematsu | Square: AKAO | 82 (79) |
| Secret of Mana | Hiroki Kikuta | Square: Secret of Mana's | 69 (68) |
| Secret of Evermore | Jeremy Soule | Square Soft US: Secret of Evermore's | 72 (70) |
| Mega Man X | "Setsuo, Tomozou, Sato, Yuko, Kir" (the tag's 32 characters, cut off) | Capcom | 35 (35) |

Composers are as the tags give them; a cut-off or missing credit is left as
it is rather than filled in from memory. Driver names are given only where
they are well established; otherwise a driver is named for its game. The six
songs not scored are near-silent in their first 30 s (sound effects: FFVI's
Rumbling, Strong Wind and a Grand Finale part, Mana's Cannon Travel Launch,
Evermore's Applause and Takeoff!).

## How it is measured

Each song is converted at its full length (to catch failures and IT's
limits), then its first 30 s are compared with the emulator's own output,
the whole mix and each voice alone (the emulator can leave voices out; the
converted song says which of its channels carry each voice). The emulator is
the reference: against libgme it correlates at 0.93 to 0.98 sample for
sample, and listened to side by side it sounds the same.

- **contour**: how the loudness moves (50 ms windows, each side the
  original sounds on). A steady sound, such as a wind bed, scores low even
  when it matches, so read it with the gap.
- **gap**: the median distance in dB between the two loudness contours.
- **level**: the module's RMS over the original's.
- **tone**: the two averaged spectra, correlated. A wrong timbre at the
  right loudness shows here and only voice by voice (The Phantom Train's
  noise-shaken tone came out a steady beep; the whole mix hid it).

## Scores by driver

| Driver | Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|---|
| Square: AKAO (FFVI) | 79 | 0.98 (0.93) | 0.40 (0.74) | 0.99 (0.95-1.02) | 1.00 (0.99) |
| Square: Secret of Mana's | 68 | 0.93 (0.72) | 0.76 (1.43) | 0.97 (0.92-1.03) | 0.99 (0.97) |
| Square Soft US: Secret of Evermore's | 70 | 0.93 (0.52) | 0.63 (1.31) | 0.99 (0.92-1.02) | 0.99 (0.97) |
| Capcom (Mega Man X) | 35 | 0.94 (0.61) | 0.48 (0.95) | 0.99 (0.88-1.01) | 1.00 (0.98) |
| **All** | 252 | 0.95 (0.76) | 0.58 (1.22) | 0.99 (0.93-1.02) | 0.99 (0.98) |

Voice tone is over the voices that carry at least 5 % of their song's
loudest voice (1,739 voices). Evermore's and Mega Man X's low tenth
percentiles of contour are steady sounds (wind beds, ambience) whose gaps
are small; none failed to convert, and none reached an IT limit (the most a
song needed: 104 samples, 96 instruments).

## The drivers

What each driver does, over each song's first minute (medians across the
game's songs unless said), what the converter does about it, and what it
means for generation.

### Square: AKAO, Final Fantasy VI (Nobuo Uematsu)

- **Clock**: a 205 Hz timer. Key-ons land anywhere in a tick in most songs
  (on it in 28 of 82), so modules use IT's finest grid, 100 rows a second.
- **Envelopes**: the instrument's ADSR at key-on; not rewritten while a note
  sounds.
- **Pitch**: 3.2 pitch writes a note (90 %: 24): vibrato and slides.
- **Pitch modulation** in 11 songs, for effects and timbres: The Phantom
  Train's steam is a 667 Hz tone whose pitch a noise voice shakes into a
  hiss; New Continent's are FM timbres (287 notes, 28 recordings). Noise in
  4 songs.
- **Echo**: 80 ms in every song, feedback set per song (0.78 in 42, 0.55 in
  27, 0.62 in 7), echo volume 0.20; the filter is a single tap seven samples
  back (it passes everything, but each trip round the echo is seven samples
  longer than the delay). Four to seven voices send.
- **Master volume** 63 of 128 in every song: the voices play loud and the
  master halves them. The echo is not halved (the SNES chip leaves it out
  of the master volume).
- **Density**: 655 notes in a song's first minute, a note 0.17 s; 32 samples
  a converted song.
- **Converter**: pitch-modulated notes kept as the emulator played them; the
  echo raised past the master volume; each repeat with the filter's span per
  trip (without it, Dark World's held organ chords stacked a third brighter
  and up to 15 % louder: heard as the organ going up in pitch).
- **For generation**: the long, strong 80 ms echo against a halved master is
  the sound; feedback is chosen per song, not fixed (the `ffvi` pack's notes,
  read from snapshot registers, give 0.64 everywhere).

### Square: Secret of Mana's (Hiroki Kikuta)

- **Clock**: a 222 Hz timer, key-ons on it in about half the songs (35 of
  69); 100 rows a second.
- **Envelopes**: ADSR at key-on, not rewritten.
- **Pitch**: few pitch writes in most voices (0.2 a note), heavy vibrato in
  some (90 %: 5.9; Fond Memories' voices write 150 to 370 times in 30 s, 2 to
  5 cents deep).
- **Pitch modulation** in 8 songs (The Oracle on five voice pairs, some at
  17 to 34 Hz; the Flammie jingles). No noise.
- **Echo**: chosen per song: 48 ms without feedback (15 songs), 96 ms without
  (11), 176 ms with 0.72 to 0.79 (16), 96 ms with 0.81 (4); echo volume 0.5;
  a pass-through filter. All eight voices send in 31 songs.
- **Master volume** 127.
- **Density**: 504 notes in the first minute, a note 0.16 s; 24 samples.
- **Converter**: the 176 ms echo is 17.6 rows at 100 a second, so on a held,
  looped tone the repeats stack as the hardware's only by chance: a held
  note's echo can come out stronger or weaker than the original's, right on
  average (Fond Memories' shimmer is this echo beating against the notes).
- **For generation**: a long echo with strong feedback under slow, held
  lines, a short dry one under busy ones; vibrato reserved for a few voices.

### Square Soft US: Secret of Evermore's (Jeremy Soule)

- **Clock**: a 50 Hz timer, key-ons on it (52 of 72 songs): modules run on
  the driver's own clock, 50 rows a second.
- **Envelopes**: shaped by the driver itself. Notes key on with a GAIN
  setting, not ADSR, and every note's envelope is rewritten as it sounds
  (9.5 writes a note: GAIN ramps and holds), the driver reading the level
  back to know when to switch. The SNES chip steps envelopes on one counter
  shared by all voices, and the converter follows it (counted from each
  note's start, it drifted a step on most switches).
- **Samples**: the driver writes a voice's directory entry just before
  keying it; the snapshot's directory holds placeholders, so samples are
  found by the addresses the SNES chip read at each key-on.
- **Noise** in 41 of 72 songs: wind and ambience, often as steady beds.
  Bright, noisy samples played well below their rate (the wind at 0.12 of
  it).
- **Echo**: 80 ms with feedback 0.16 in 58 songs (none in 12), echo volume
  0.39, a strongly shaped filter (taps -8, -40, -80, -104, -120, 112, 80, 0;
  -1.25 at DC).
- **Master volume** 127.
- **Density**: 297 notes in the first minute, a note 0.27 s; 17 samples.
- **Converter**: rewritten envelopes carried whole in the volume column (the
  wind was silent until then: its key-on level, 16 of 2047, rounds to
  nothing in an IT envelope); samples softened as the SNES chip's Gaussian
  interpolation softens them (the wind was three times too strong above its
  own top).
- **For generation**: the envelope is the composer's instrument here, not the
  sample's: swells and holds written note by note. The `evermore` pack's notes
  (from snapshot registers) give the echo off in 47 of 72; in play it is on in
  58.

### Capcom: Mega Man X

- **Clock**: 125 Hz, faster than IT can run (102 ticks a second at most), so
  100 rows a second.
- **Envelopes**: every note keys on with a held ADSR and is released with a
  GAIN fade a moment before the next, never with a key-off (2.2 envelope
  writes a note). Without carrying those writes every note rang on into the
  next.
- **Arrangement**: the score doubles its melody with a delayed copy on
  another voice, panned the other way (Spark Mandrill: 0.12 s behind).
- **Echo**: the same in all 35 songs: 48 ms, feedback 0.53, echo volume 0.56
  with the sides of opposite signs (a widening trick), and a band-pass filter
  (taps 52, 51, 0, -39, -27, 1, -4, -21: 0.10 at DC, about 1 from 2 to 8 kHz).
  No pitch modulation, no noise.
- **Master volume** 92.
- **Density**: 1,258 notes in the first minute, a note 0.19 s; 42 samples and
  64 instruments, the most of the four.
- **Converter**: the GAIN releases; echo repeats from copies coloured by the
  filter (a full-range copy at the echo's level sounded like a second
  instrument); surround for the opposite signs, on voices near the middle.
- **For generation**: short notes, dense; the thin, bright, wide echo is part
  of the sound; staccato comes from the driver's release, not the samples.

## What the converter carries, across drivers

The SNES chip's behaviours the converter carries, and where each was found
(`SPC-IMPORT.md` has the details):

| Behaviour | Found in |
|---|---|
| Samples by the addresses read at key-on | Secret of Evermore |
| Envelopes rewritten while a note sounds, in the volume column | Mega Man X, Secret of Evermore |
| Envelope steps on the shared rate counter | Secret of Evermore |
| Volumes side for side, the master volume as global volume | Secret of Mana (played at half its level before) |
| The Gaussian interpolation's softness, in the samples | Secret of Evermore |
| The hardware's noise, held at its clock | FFVI, Secret of Evermore |
| Pitch modulation, kept as played | FFVI, Secret of Mana |
| The echo: coloured repeats until -30 dB, past the master volume, the filter's span each trip | Mega Man X, FFVI |
| A song's end: the tag's length and fade | FFVI |

Known limits:

- **Held tones on echo delays that miss whole rows** (Mana's 176 ms): the
  repeats stack or cancel by chance. IT places notes no finer than a tick,
  and players round their ticks differently.
- **Samples played faster than the output rate**: the SNES chip aliases
  them (nothing filters them), libopenmpt filters; such a voice loses that
  energy (a hi-hat in Evermore's Regal Castle; some FFVI voices' top octave).
- **IT's volume ceiling**: a voice needing more than 64 is held at 64 (in
  the songs checked, at most 0.3 % of notes: Evermore's Southern Jungle).
- **The noise generator's position** is not in an SPC file: noise matches in
  level and colour, not sample for sample.

## Open

Found by the sweep, not yet looked into:

- **Secret of Mana, 9a Flammie Coming** (a pitch-modulated jingle): 14.5 dB
  off in loudness, its voices 24 to 32 dB.
- **Secret of Evermore**: single voices at 0.2 to 0.3 of their level, 20 to
  58 dB off over time, though their tone is right: Bugmuck Tar Pits (voice
  3), The Professor's Room (2), Pirates of Crustacia (5), The Seashore (1),
  Dark Forest (1, 7), Underground Path (5).
- **FFVI's sound-effect tracks** (999 Blazing Fire voice 2, 999 Train voice
  5): the wrong tone.
- **The style packs' habits** were read from snapshot registers before the
  emulator ran the drivers; in play the drivers set them differently (the
  echo above). Measure them again from played songs.

## Adding a game

1. Its `.spc` files in a folder of their own beside the others (the folder is
   the game's name in the results).
2. Its music driver in `drivers.json` beside the folders (`{"<folder>":
   "<driver family>"}`): a known family where it is one, so its results pool
   with the others; else named for the game.
3. `traits`, `sweep` and `report`, as above.
4. Here: the game in the corpus table, its driver's section (a new one, or
   the existing one's numbers updated), and anything the sweep found to Open.
